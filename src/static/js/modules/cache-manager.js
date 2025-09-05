/**
 * OneSquare 캐시 관리자
 * 
 * 다양한 캐싱 전략과 캐시 관리 기능 제공
 */

class CacheManager {
  constructor() {
    this.cacheNames = {
      static: 'onesquare-static-v1.0.0',
      dynamic: 'onesquare-dynamic-v1.0.0',
      api: 'onesquare-api-v1.0.0',
      images: 'onesquare-images-v1.0.0',
      fonts: 'onesquare-fonts-v1.0.0'
    };
    
    this.maxAge = {
      static: 7 * 24 * 60 * 60 * 1000,    // 7일
      dynamic: 24 * 60 * 60 * 1000,       // 1일
      api: 5 * 60 * 1000,                 // 5분
      images: 30 * 24 * 60 * 60 * 1000,   // 30일
      fonts: 30 * 24 * 60 * 60 * 1000     // 30일
    };
    
    this.maxEntries = {
      static: 50,
      dynamic: 100,
      api: 200,
      images: 100,
      fonts: 20
    };
  }

  /**
   * Cache First 전략
   * 캐시에서 먼저 찾고, 없으면 네트워크에서 가져와 캐시
   */
  async cacheFirst(request, cacheType = 'static') {
    const cacheName = this.cacheNames[cacheType];
    const cache = await caches.open(cacheName);
    
    // 캐시에서 찾기
    const cachedResponse = await cache.match(request);
    if (cachedResponse && this.isCacheValid(cachedResponse, cacheType)) {
      console.log('[Cache] Cache hit (Cache First):', request.url);
      return cachedResponse;
    }
    
    try {
      // 네트워크에서 가져오기
      console.log('[Cache] Cache miss, fetching:', request.url);
      const networkResponse = await fetch(request);
      
      if (networkResponse.ok) {
        // 캐시에 저장
        await this.putInCache(cache, request, networkResponse.clone(), cacheType);
      }
      
      return networkResponse;
      
    } catch (error) {
      console.warn('[Cache] Network failed, returning stale cache:', request.url);
      // 네트워크 실패 시 오래된 캐시라도 반환
      return cachedResponse || new Response('Offline', { status: 503 });
    }
  }

  /**
   * Network First 전략
   * 네트워크를 우선하고, 실패 시 캐시 사용
   */
  async networkFirst(request, cacheType = 'dynamic') {
    const cacheName = this.cacheNames[cacheType];
    const cache = await caches.open(cacheName);
    
    try {
      console.log('[Cache] Network first attempt:', request.url);
      const networkResponse = await fetch(request);
      
      if (networkResponse.ok) {
        // 성공한 응답은 캐시에 저장
        await this.putInCache(cache, request, networkResponse.clone(), cacheType);
      }
      
      return networkResponse;
      
    } catch (error) {
      console.log('[Cache] Network failed, trying cache:', request.url);
      
      const cachedResponse = await cache.match(request);
      if (cachedResponse) {
        return cachedResponse;
      }
      
      // 캐시도 없으면 오프라인 응답
      return this.createOfflineResponse(request);
    }
  }

  /**
   * Stale While Revalidate 전략
   * 캐시된 응답을 즉시 반환하고 백그라운드에서 업데이트
   */
  async staleWhileRevalidate(request, cacheType = 'dynamic') {
    const cacheName = this.cacheNames[cacheType];
    const cache = await caches.open(cacheName);
    
    // 캐시된 응답 확인
    const cachedResponse = await cache.match(request);
    
    // 백그라운드에서 네트워크 요청 (Promise를 반환하지 않음)
    const fetchPromise = fetch(request)
      .then(networkResponse => {
        if (networkResponse.ok) {
          this.putInCache(cache, request, networkResponse.clone(), cacheType);
        }
        return networkResponse;
      })
      .catch(error => {
        console.warn('[Cache] Background fetch failed:', error);
      });
    
    // 캐시가 있으면 즉시 반환
    if (cachedResponse && this.isCacheValid(cachedResponse, cacheType)) {
      console.log('[Cache] Stale while revalidate (cached):', request.url);
      return cachedResponse;
    }
    
    // 캐시가 없거나 만료되었으면 네트워크 응답 대기
    console.log('[Cache] Stale while revalidate (network):', request.url);
    return await fetchPromise;
  }

  /**
   * API 전용 캐싱 전략
   * 짧은 TTL과 조건부 요청 지원
   */
  async apiCacheStrategy(request) {
    const cache = await caches.open(this.cacheNames.api);
    const cachedResponse = await cache.match(request);
    
    // 캐시가 있고 유효하면 조건부 요청
    if (cachedResponse && this.isCacheValid(cachedResponse, 'api')) {
      const etag = cachedResponse.headers.get('etag');
      const lastModified = cachedResponse.headers.get('last-modified');
      
      if (etag || lastModified) {
        const conditionalRequest = new Request(request.url, {
          method: request.method,
          headers: {
            ...Object.fromEntries(request.headers),
            ...(etag && { 'If-None-Match': etag }),
            ...(lastModified && { 'If-Modified-Since': lastModified })
          }
        });
        
        try {
          const networkResponse = await fetch(conditionalRequest);
          
          if (networkResponse.status === 304) {
            // Not Modified - 캐시된 응답 반환
            console.log('[Cache] API not modified (304):', request.url);
            return cachedResponse;
          } else if (networkResponse.ok) {
            // 새로운 응답 - 캐시 업데이트
            console.log('[Cache] API updated:', request.url);
            await this.putInCache(cache, request, networkResponse.clone(), 'api');
            return networkResponse;
          }
        } catch (error) {
          console.warn('[Cache] API conditional request failed:', error);
        }
      }
    }
    
    // 일반적인 네트워크 우선 전략
    return this.networkFirst(request, 'api');
  }

  /**
   * 캐시에 응답 저장
   */
  async putInCache(cache, request, response, cacheType) {
    // 상태 코드 확인
    if (!response.ok) {
      return;
    }
    
    // Content-Type 확인 (필요한 경우)
    const contentType = response.headers.get('content-type');
    if (cacheType === 'images' && !this.isImageContent(contentType)) {
      return;
    }
    
    // 캐시 크기 제한 확인
    await this.enforceMaxEntries(cache, cacheType);
    
    // 메타데이터와 함께 저장
    const responseToCache = response.clone();
    responseToCache.headers.set('cache-timestamp', Date.now().toString());
    responseToCache.headers.set('cache-type', cacheType);
    
    await cache.put(request, responseToCache);
    console.log(`[Cache] Stored in ${cacheType} cache:`, request.url);
  }

  /**
   * 캐시 유효성 확인
   */
  isCacheValid(cachedResponse, cacheType) {
    const cacheTimestamp = cachedResponse.headers.get('cache-timestamp');
    if (!cacheTimestamp) {
      return true; // 타임스탬프가 없으면 유효하다고 가정
    }
    
    const age = Date.now() - parseInt(cacheTimestamp);
    const maxAge = this.maxAge[cacheType] || this.maxAge.dynamic;
    
    return age < maxAge;
  }

  /**
   * 캐시 크기 제한 강제
   */
  async enforceMaxEntries(cache, cacheType) {
    const maxEntries = this.maxEntries[cacheType] || this.maxEntries.dynamic;
    const keys = await cache.keys();
    
    if (keys.length >= maxEntries) {
      // 가장 오래된 항목들 삭제 (LRU 방식)
      const entriesToDelete = keys.length - maxEntries + 1;
      
      // 타임스탬프 기준으로 정렬
      const keysByAge = await this.sortKeysByAge(cache, keys);
      
      for (let i = 0; i < entriesToDelete; i++) {
        await cache.delete(keysByAge[i]);
        console.log(`[Cache] Evicted old entry:`, keysByAge[i].url);
      }
    }
  }

  /**
   * 키를 나이순으로 정렬
   */
  async sortKeysByAge(cache, keys) {
    const keyAges = await Promise.all(
      keys.map(async key => {
        const response = await cache.match(key);
        const timestamp = response.headers.get('cache-timestamp');
        return {
          key,
          timestamp: timestamp ? parseInt(timestamp) : 0
        };
      })
    );
    
    return keyAges
      .sort((a, b) => a.timestamp - b.timestamp)
      .map(item => item.key);
  }

  /**
   * 이미지 콘텐츠 타입 확인
   */
  isImageContent(contentType) {
    return contentType && contentType.startsWith('image/');
  }

  /**
   * 오프라인 응답 생성
   */
  createOfflineResponse(request) {
    const url = new URL(request.url);
    
    if (request.headers.get('accept').includes('text/html')) {
      // HTML 요청에 대한 오프라인 페이지
      return new Response('오프라인 상태입니다.', {
        status: 503,
        headers: { 'Content-Type': 'text/html; charset=utf-8' }
      });
    } else if (url.pathname.startsWith('/api/')) {
      // API 요청에 대한 오프라인 응답
      return new Response(JSON.stringify({
        error: 'offline',
        message: '오프라인 상태입니다. 네트워크 연결을 확인해주세요.',
        offline: true
      }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      });
    } else {
      // 기본 오프라인 응답
      return new Response('오프라인 상태입니다.', {
        status: 503,
        statusText: 'Service Unavailable'
      });
    }
  }

  /**
   * 모든 캐시 정리
   */
  async clearAllCaches() {
    const results = [];
    
    for (const [type, cacheName] of Object.entries(this.cacheNames)) {
      try {
        const deleted = await caches.delete(cacheName);
        results.push({ type, cacheName, deleted });
        console.log(`[Cache] Cleared ${type} cache:`, cacheName);
      } catch (error) {
        console.error(`[Cache] Failed to clear ${type} cache:`, error);
        results.push({ type, cacheName, deleted: false, error: error.message });
      }
    }
    
    return results;
  }

  /**
   * 특정 캐시 정리
   */
  async clearCache(cacheType) {
    const cacheName = this.cacheNames[cacheType];
    if (!cacheName) {
      throw new Error(`Unknown cache type: ${cacheType}`);
    }
    
    try {
      const deleted = await caches.delete(cacheName);
      console.log(`[Cache] Cleared ${cacheType} cache:`, cacheName);
      return { type: cacheType, cacheName, deleted };
    } catch (error) {
      console.error(`[Cache] Failed to clear ${cacheType} cache:`, error);
      throw error;
    }
  }

  /**
   * 캐시 통계 조회
   */
  async getCacheStats() {
    const stats = {};
    
    for (const [type, cacheName] of Object.entries(this.cacheNames)) {
      try {
        const cache = await caches.open(cacheName);
        const keys = await cache.keys();
        
        // 캐시 크기 계산 (근사값)
        let totalSize = 0;
        let validEntries = 0;
        let expiredEntries = 0;
        
        for (const key of keys) {
          const response = await cache.match(key);
          const contentLength = response.headers.get('content-length');
          
          if (contentLength) {
            totalSize += parseInt(contentLength);
          }
          
          if (this.isCacheValid(response, type)) {
            validEntries++;
          } else {
            expiredEntries++;
          }
        }
        
        stats[type] = {
          cacheName,
          totalEntries: keys.length,
          validEntries,
          expiredEntries,
          approximateSize: totalSize,
          maxEntries: this.maxEntries[type],
          maxAge: this.maxAge[type]
        };
      } catch (error) {
        stats[type] = {
          cacheName,
          error: error.message
        };
      }
    }
    
    return stats;
  }

  /**
   * 만료된 캐시 항목 정리
   */
  async cleanupExpiredEntries() {
    const results = [];
    
    for (const [type, cacheName] of Object.entries(this.cacheNames)) {
      try {
        const cache = await caches.open(cacheName);
        const keys = await cache.keys();
        let cleanedCount = 0;
        
        for (const key of keys) {
          const response = await cache.match(key);
          
          if (!this.isCacheValid(response, type)) {
            await cache.delete(key);
            cleanedCount++;
          }
        }
        
        results.push({
          type,
          cacheName,
          cleanedCount,
          remainingEntries: keys.length - cleanedCount
        });
        
        console.log(`[Cache] Cleaned ${cleanedCount} expired entries from ${type} cache`);
        
      } catch (error) {
        console.error(`[Cache] Failed to clean ${type} cache:`, error);
        results.push({
          type,
          cacheName,
          error: error.message
        });
      }
    }
    
    return results;
  }

  /**
   * 캐시 워밍업 (사전 로드)
   */
  async warmupCache(urls, cacheType = 'static') {
    const cache = await caches.open(this.cacheNames[cacheType]);
    const results = [];
    
    for (const url of urls) {
      try {
        const response = await fetch(url);
        if (response.ok) {
          await this.putInCache(cache, new Request(url), response, cacheType);
          results.push({ url, success: true });
          console.log(`[Cache] Warmed up:`, url);
        } else {
          results.push({ url, success: false, status: response.status });
        }
      } catch (error) {
        console.warn(`[Cache] Warmup failed for ${url}:`, error);
        results.push({ url, success: false, error: error.message });
      }
    }
    
    return results;
  }

  /**
   * 캐시 전략 선택기
   */
  selectStrategy(request) {
    const url = new URL(request.url);
    const pathname = url.pathname.toLowerCase();
    const extension = this.getFileExtension(pathname);
    
    // API 요청
    if (pathname.startsWith('/api/')) {
      return { strategy: 'api', type: 'api' };
    }
    
    // 정적 리소스 (Cache First)
    if (['js', 'css', 'woff', 'woff2', 'ttf', 'eot'].includes(extension)) {
      return { 
        strategy: 'cacheFirst', 
        type: extension === 'js' || extension === 'css' ? 'static' : 'fonts' 
      };
    }
    
    // 이미지 (Cache First)
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'ico'].includes(extension)) {
      return { strategy: 'cacheFirst', type: 'images' };
    }
    
    // HTML 페이지 (Network First)
    if (extension === 'html' || extension === '') {
      return { strategy: 'networkFirst', type: 'dynamic' };
    }
    
    // 기타 (Stale While Revalidate)
    return { strategy: 'staleWhileRevalidate', type: 'dynamic' };
  }

  /**
   * 파일 확장자 추출
   */
  getFileExtension(pathname) {
    const parts = pathname.split('.');
    return parts.length > 1 ? parts.pop().toLowerCase() : '';
  }

  /**
   * 캐시 전략 실행
   */
  async executeStrategy(request) {
    const { strategy, type } = this.selectStrategy(request);
    
    switch (strategy) {
      case 'cacheFirst':
        return this.cacheFirst(request, type);
      case 'networkFirst':
        return this.networkFirst(request, type);
      case 'staleWhileRevalidate':
        return this.staleWhileRevalidate(request, type);
      case 'api':
        return this.apiCacheStrategy(request);
      default:
        return this.networkFirst(request, type);
    }
  }
}

// 전역 인스턴스 (Service Worker에서 사용)
if (typeof self !== 'undefined' && self.constructor.name === 'ServiceWorkerGlobalScope') {
  self.cacheManager = new CacheManager();
}

// 모듈 내보내기 (일반 웹 페이지에서 사용)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CacheManager;
} else if (typeof window !== 'undefined') {
  window.CacheManager = CacheManager;
}