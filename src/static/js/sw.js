/**
 * OneSquare PWA Service Worker
 * 
 * 기능:
 * - 오프라인 캐싱
 * - 백그라운드 동기화  
 * - 푸시 알림
 * - 네트워크 요청 가로채기
 */

const CACHE_NAME = 'onesquare-v1.0.0';
const OFFLINE_URL = '/offline/';

// 캐시할 필수 리소스들
const CACHE_URLS = [
  '/',
  '/static/css/common.css',
  '/static/css/auth.css',
  '/static/js/common.js',
  '/static/js/auth/login.js',
  '/static/images/logo.png',
  '/offline/'
];

// API 캐시 설정
const API_CACHE_NAME = 'onesquare-api-v1.0.0';
const API_CACHE_URLS = [
  '/api/auth/status/',
  '/api/notion/status/'
];

// 캐시 전략 설정
const CACHE_STRATEGIES = {
  // Cache First: 정적 리소스 (CSS, JS, 이미지)
  CACHE_FIRST: ['css', 'js', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'],
  
  // Network First: 동적 데이터 (API, HTML)
  NETWORK_FIRST: ['api', 'html'],
  
  // Stale While Revalidate: 자주 변경되는 리소스
  STALE_WHILE_REVALIDATE: ['fonts', 'json']
};

/**
 * Service Worker 설치 이벤트
 * 필수 리소스들을 캐시에 저장
 */
self.addEventListener('install', event => {
  console.log('[SW] Install event triggered');
  
  event.waitUntil(
    (async () => {
      try {
        // 메인 캐시 생성
        const cache = await caches.open(CACHE_NAME);
        await cache.addAll(CACHE_URLS);
        
        // API 캐시 생성
        const apiCache = await caches.open(API_CACHE_NAME);
        await apiCache.addAll(API_CACHE_URLS);
        
        console.log('[SW] All resources cached successfully');
        
        // 즉시 활성화
        await self.skipWaiting();
        
      } catch (error) {
        console.error('[SW] Cache installation failed:', error);
      }
    })()
  );
});

/**
 * Service Worker 활성화 이벤트
 * 이전 버전 캐시 정리
 */
self.addEventListener('activate', event => {
  console.log('[SW] Activate event triggered');
  
  event.waitUntil(
    (async () => {
      try {
        // 기존 캐시 정리
        const cacheNames = await caches.keys();
        const oldCaches = cacheNames.filter(cacheName => {
          return cacheName !== CACHE_NAME && cacheName !== API_CACHE_NAME;
        });
        
        await Promise.all(
          oldCaches.map(cacheName => caches.delete(cacheName))
        );
        
        console.log('[SW] Old caches cleaned up:', oldCaches);
        
        // 모든 클라이언트 제어
        await self.clients.claim();
        
      } catch (error) {
        console.error('[SW] Activation failed:', error);
      }
    })()
  );
});

/**
 * Fetch 이벤트 - 네트워크 요청 가로채기
 * 캐시 전략에 따라 응답 처리
 */
self.addEventListener('fetch', event => {
  // POST/PUT/DELETE 요청은 캐시하지 않음
  if (event.request.method !== 'GET') {
    return;
  }
  
  const url = new URL(event.request.url);
  
  // 외부 도메인 요청은 처리하지 않음
  if (url.origin !== location.origin) {
    return;
  }
  
  event.respondWith(
    (async () => {
      try {
        return await handleFetchRequest(event.request);
      } catch (error) {
        console.error('[SW] Fetch failed:', error);
        return await handleOfflineResponse(event.request);
      }
    })()
  );
});

/**
 * 요청 처리 로직
 */
async function handleFetchRequest(request) {
  const url = new URL(request.url);
  const extension = getFileExtension(url.pathname);
  
  // API 요청 처리
  if (url.pathname.startsWith('/api/')) {
    return await handleApiRequest(request);
  }
  
  // 정적 리소스 처리 (Cache First)
  if (CACHE_STRATEGIES.CACHE_FIRST.includes(extension)) {
    return await cacheFirst(request);
  }
  
  // HTML 페이지 처리 (Network First)
  if (extension === 'html' || extension === '') {
    return await networkFirst(request);
  }
  
  // 기타 리소스 처리 (Stale While Revalidate)
  return await staleWhileRevalidate(request);
}

/**
 * Cache First 전략
 * 캐시에서 먼저 찾고, 없으면 네트워크 요청
 */
async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  
  if (cached) {
    console.log('[SW] Cache hit:', request.url);
    return cached;
  }
  
  console.log('[SW] Cache miss, fetching:', request.url);
  const response = await fetch(request);
  
  if (response.status === 200) {
    cache.put(request, response.clone());
  }
  
  return response;
}

/**
 * Network First 전략
 * 네트워크 우선, 실패 시 캐시 사용
 */
async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  
  try {
    console.log('[SW] Network first:', request.url);
    const response = await fetch(request);
    
    if (response.status === 200) {
      cache.put(request, response.clone());
    }
    
    return response;
    
  } catch (error) {
    console.log('[SW] Network failed, using cache:', request.url);
    const cached = await cache.match(request);
    
    if (cached) {
      return cached;
    }
    
    // 오프라인 페이지 반환
    return await cache.match(OFFLINE_URL);
  }
}

/**
 * Stale While Revalidate 전략
 * 캐시된 응답을 즉시 반환하고 백그라운드에서 업데이트
 */
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  
  // 백그라운드에서 리소스 업데이트
  const fetchPromise = fetch(request).then(response => {
    if (response.status === 200) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(error => {
    console.warn('[SW] Background fetch failed:', error);
  });
  
  // 캐시된 응답 우선 반환
  if (cached) {
    console.log('[SW] Stale while revalidate (cached):', request.url);
    return cached;
  }
  
  // 캐시가 없으면 네트워크 응답 대기
  console.log('[SW] Stale while revalidate (network):', request.url);
  return await fetchPromise;
}

/**
 * API 요청 처리
 * 네트워크 우선, 오프라인 시 캐시된 응답 반환
 */
async function handleApiRequest(request) {
  const cache = await caches.open(API_CACHE_NAME);
  
  try {
    console.log('[SW] API request:', request.url);
    const response = await fetch(request);
    
    // 성공한 GET 요청만 캐시
    if (response.status === 200 && request.method === 'GET') {
      cache.put(request, response.clone());
    }
    
    return response;
    
  } catch (error) {
    console.log('[SW] API offline, using cache:', request.url);
    const cached = await cache.match(request);
    
    if (cached) {
      return cached;
    }
    
    // API 오프라인 응답
    return new Response(JSON.stringify({
      error: 'offline',
      message: '오프라인 상태입니다. 네트워크 연결을 확인해주세요.'
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * 오프라인 응답 처리
 */
async function handleOfflineResponse(request) {
  const cache = await caches.open(CACHE_NAME);
  const url = new URL(request.url);
  
  // HTML 페이지 요청 시 오프라인 페이지 반환
  if (request.headers.get('accept').includes('text/html')) {
    const offlinePage = await cache.match(OFFLINE_URL);
    if (offlinePage) {
      return offlinePage;
    }
  }
  
  // 캐시된 버전 찾기
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }
  
  // 기본 오프라인 응답
  return new Response('오프라인 상태입니다.', {
    status: 503,
    statusText: 'Service Unavailable'
  });
}

/**
 * 백그라운드 동기화
 */
self.addEventListener('sync', event => {
  console.log('[SW] Background sync triggered:', event.tag);
  
  if (event.tag === 'notion-sync') {
    event.waitUntil(syncNotionData());
  } else if (event.tag === 'auth-refresh') {
    event.waitUntil(refreshAuthToken());
  }
});

/**
 * Notion 데이터 동기화
 */
async function syncNotionData() {
  try {
    console.log('[SW] Syncing Notion data...');
    
    // IndexedDB 초기화
    if (typeof self.offlineDB === 'undefined') {
      const OfflineDatabase = (await import('/static/js/modules/offline-database.js')).default;
      self.offlineDB = new OfflineDatabase();
      await self.offlineDB.init();
    }
    
    // 오프라인 큐에서 대기 중인 작업 처리
    const offlineQueue = await self.offlineDB.getOfflineQueue();
    let processedCount = 0;
    
    for (const queueItem of offlineQueue) {
      try {
        // API 요청 실행
        const response = await fetch(queueItem.endpoint, {
          method: queueItem.method,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': await getStoredAuthToken()
          },
          body: queueItem.data ? JSON.stringify(queueItem.data) : undefined
        });
        
        if (response.ok) {
          const result = await response.json();
          
          // 성공한 작업 큐에서 제거
          await self.offlineDB.removeFromOfflineQueue(queueItem.id);
          
          // 동기화 로그 기록
          await self.offlineDB.logSync(`${queueItem.type}-sync`, 'success', {
            endpoint: queueItem.endpoint,
            method: queueItem.method,
            timestamp: new Date().toISOString()
          });
          
          // 결과가 페이지 데이터인 경우 로컬 저장소 업데이트
          if (result.id && queueItem.type !== 'delete') {
            await self.offlineDB.saveNotionPage(result);
          }
          
          processedCount++;
          console.log('[SW] Synced offline action:', queueItem.type, queueItem.endpoint);
          
        } else {
          // 실패한 경우 재시도 카운트 증가
          queueItem.retryCount = (queueItem.retryCount || 0) + 1;
          
          if (queueItem.retryCount >= queueItem.maxRetries) {
            await self.offlineDB.removeFromOfflineQueue(queueItem.id);
            await self.offlineDB.logSync(`${queueItem.type}-sync`, 'failed', 
              `최대 재시도 초과: ${response.status} ${response.statusText}`);
            console.error('[SW] Max retries exceeded for:', queueItem.endpoint);
          } else {
            await self.offlineDB.saveData(self.offlineDB.stores.offlineQueue, queueItem);
            console.warn('[SW] Retrying sync for:', queueItem.endpoint, `(${queueItem.retryCount}/${queueItem.maxRetries})`);
          }
        }
        
      } catch (error) {
        // 네트워크 오류 등의 경우 재시도
        queueItem.retryCount = (queueItem.retryCount || 0) + 1;
        
        if (queueItem.retryCount >= queueItem.maxRetries) {
          await self.offlineDB.removeFromOfflineQueue(queueItem.id);
          await self.offlineDB.logSync(`${queueItem.type}-sync`, 'failed', error.message);
        } else {
          await self.offlineDB.saveData(self.offlineDB.stores.offlineQueue, queueItem);
        }
        
        console.warn('[SW] Sync error for:', queueItem.endpoint, error);
      }
      
      // API 레이트 리미트 방지를 위한 지연
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    
    // 최신 Notion 데이터 가져와서 로컬 동기화
    if (processedCount > 0) {
      await fetchLatestNotionData();
    }
    
    // 최신 데이터 캐시 업데이트
    await updateApiCache();
    
    console.log(`[SW] Notion sync completed - ${processedCount}/${offlineQueue.length} items processed`);
    
    // 동기화 완료 알림
    await self.offlineDB.logSync('full-sync', 'success', {
      processedItems: processedCount,
      totalItems: offlineQueue.length,
      timestamp: new Date().toISOString()
    });
    
  } catch (error) {
    console.error('[SW] Notion sync failed:', error);
    
    if (self.offlineDB) {
      await self.offlineDB.logSync('full-sync', 'failed', error.message);
    }
  }
}

/**
 * 인증 토큰 갱신
 */
async function refreshAuthToken() {
  try {
    console.log('[SW] Refreshing auth token...');
    
    const response = await fetch('/api/auth/refresh/', {
      method: 'POST',
      credentials: 'include'
    });
    
    if (response.ok) {
      console.log('[SW] Auth token refreshed');
      
      // 캐시된 인증 상태 업데이트
      const apiCache = await caches.open(API_CACHE_NAME);
      apiCache.put('/api/auth/status/', response.clone());
    }
    
  } catch (error) {
    console.error('[SW] Token refresh failed:', error);
  }
}

/**
 * 푸시 알림 처리
 */
self.addEventListener('push', event => {
  console.log('[SW] Push notification received');
  
  let notificationData = {
    title: 'OneSquare 알림',
    body: '새로운 업데이트가 있습니다.',
    icon: '/static/images/icon-192.png',
    badge: '/static/images/badge-72.png',
    data: { url: '/' }
  };
  
  if (event.data) {
    try {
      notificationData = { ...notificationData, ...event.data.json() };
    } catch (error) {
      console.warn('[SW] Push data parsing failed:', error);
    }
  }
  
  event.waitUntil(
    self.registration.showNotification(notificationData.title, {
      body: notificationData.body,
      icon: notificationData.icon,
      badge: notificationData.badge,
      data: notificationData.data,
      actions: [
        { action: 'open', title: '열기' },
        { action: 'close', title: '닫기' }
      ]
    })
  );
});

/**
 * 알림 클릭 처리
 */
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification clicked:', event.action);
  
  event.notification.close();
  
  if (event.action === 'close') {
    return;
  }
  
  const url = event.notification.data?.url || '/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then(clientList => {
      // 이미 열린 창이 있으면 포커스
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      
      // 새 창 열기
      if (clients.openWindow) {
        return clients.openWindow(url);
      }
    })
  );
});

/**
 * 메시지 처리 (클라이언트와 통신)
 */
self.addEventListener('message', event => {
  console.log('[SW] Message received:', event.data);
  
  const { action, data } = event.data;
  
  switch (action) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'GET_CACHE_STATUS':
      getCacheStatus().then(status => {
        event.ports[0]?.postMessage(status);
      });
      break;
      
    case 'CLEAR_CACHE':
      clearAllCaches().then(result => {
        event.ports[0]?.postMessage(result);
      });
      break;
      
    case 'ADD_TO_OFFLINE_QUEUE':
      addToOfflineQueue(data).then(result => {
        event.ports[0]?.postMessage(result);
      });
      break;
  }
});

/**
 * 유틸리티 함수들
 */

function getFileExtension(pathname) {
  const parts = pathname.split('.');
  return parts.length > 1 ? parts.pop().toLowerCase() : '';
}

async function getCacheStatus() {
  const cacheNames = await caches.keys();
  const status = {};
  
  for (const cacheName of cacheNames) {
    const cache = await caches.open(cacheName);
    const keys = await cache.keys();
    status[cacheName] = keys.length;
  }
  
  return status;
}

async function clearAllCaches() {
  try {
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map(name => caches.delete(name)));
    return { success: true, message: 'All caches cleared' };
  } catch (error) {
    return { success: false, error: error.message };
  }
}

async function updateApiCache() {
  const apiCache = await caches.open(API_CACHE_NAME);
  
  for (const url of API_CACHE_URLS) {
    try {
      const response = await fetch(url);
      if (response.ok) {
        await apiCache.put(url, response);
      }
    } catch (error) {
      console.warn('[SW] Failed to update cache for:', url);
    }
  }
}

// 성능 최적화 모듈 통합
self.importScripts('/static/js/modules/cache-manager.js');
self.importScripts('/static/js/modules/offline-database.js');
self.importScripts('/static/js/modules/advanced-cache-strategies.js');

/**
 * 고급 캐싱 전략 사용
 */
async function handleEnhancedFetch(request) {
  try {
    // AdvancedCacheStrategies 사용
    if (self.advancedCacheStrategies) {
      return await self.advancedCacheStrategies.executeStrategy(request);
    }
    
    // 폴백: CacheManager 사용
    return await self.cacheManager.executeStrategy(request);
  } catch (error) {
    console.error('[SW] Advanced caching failed:', error);
    // 기본 캐싱 로직으로 폴백
    return await handleFetchRequest(request);
  }
}

/**
 * 캐시 정리 작업 (주기적 실행)
 */
async function performCacheMaintenance() {
  try {
    console.log('[SW] Starting cache maintenance...');
    
    // 만료된 항목 정리
    const cleanupResults = await self.cacheManager.cleanupExpiredEntries();
    console.log('[SW] Cache cleanup results:', cleanupResults);
    
    // 캐시 통계 로그
    const stats = await self.cacheManager.getCacheStats();
    console.log('[SW] Cache statistics:', stats);
    
    console.log('[SW] Cache maintenance completed');
    
  } catch (error) {
    console.error('[SW] Cache maintenance failed:', error);
  }
}

/**
 * 캐시 워밍업 (설치 시 실행)
 */
async function warmupCriticalResources() {
  const criticalUrls = [
    '/static/css/common.css',
    '/static/js/common.js',
    '/static/js/pwa-manager.js',
    '/api/auth/status/',
    '/offline/'
  ];
  
  try {
    const results = await self.cacheManager.warmupCache(criticalUrls, 'static');
    console.log('[SW] Cache warmup results:', results);
  } catch (error) {
    console.error('[SW] Cache warmup failed:', error);
  }
}

// Fetch 이벤트 리스너 업데이트 (향상된 캐싱 사용)
self.addEventListener('fetch', event => {
  // POST/PUT/DELETE 요청은 캐시하지 않음
  if (event.request.method !== 'GET') {
    return;
  }
  
  const url = new URL(event.request.url);
  
  // 외부 도메인 요청은 처리하지 않음
  if (url.origin !== location.origin) {
    return;
  }
  
  event.respondWith(
    (async () => {
      try {
        // 향상된 캐싱 전략 사용
        return await handleEnhancedFetch(event.request);
      } catch (error) {
        console.error('[SW] Enhanced fetch failed:', error);
        return await handleOfflineResponse(event.request);
      }
    })()
  );
});

// 설치 이벤트에 캐시 워밍업 추가
self.addEventListener('install', event => {
  console.log('[SW] Install event triggered');
  
  event.waitUntil(
    (async () => {
      try {
        // 메인 캐시 생성
        const cache = await caches.open(CACHE_NAME);
        await cache.addAll(CACHE_URLS);
        
        // API 캐시 생성
        const apiCache = await caches.open(API_CACHE_NAME);
        await apiCache.addAll(API_CACHE_URLS);
        
        // 캐시 워밍업
        await warmupCriticalResources();
        
        console.log('[SW] All resources cached successfully');
        
        // 즉시 활성화
        await self.skipWaiting();
        
      } catch (error) {
        console.error('[SW] Cache installation failed:', error);
      }
    })()
  );
});

// 주기적 캐시 정리 (24시간마다)
self.addEventListener('sync', event => {
  console.log('[SW] Background sync triggered:', event.tag);
  
  if (event.tag === 'notion-sync') {
    event.waitUntil(syncNotionData());
  } else if (event.tag === 'auth-refresh') {
    event.waitUntil(refreshAuthToken());
  } else if (event.tag === 'cache-maintenance') {
    event.waitUntil(performCacheMaintenance());
  }
});

// 메시지 처리에 캐시 관리 기능 추가
self.addEventListener('message', event => {
  console.log('[SW] Message received:', event.data);
  
  const { action, data } = event.data;
  
  switch (action) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'GET_CACHE_STATUS':
      self.cacheManager.getCacheStats().then(stats => {
        event.ports[0]?.postMessage(stats);
      });
      break;
      
    case 'CLEAR_CACHE':
      if (data && data.type) {
        // 특정 캐시 타입 정리
        self.cacheManager.clearCache(data.type).then(result => {
          event.ports[0]?.postMessage(result);
        });
      } else {
        // 모든 캐시 정리
        self.cacheManager.clearAllCaches().then(result => {
          event.ports[0]?.postMessage(result);
        });
      }
      break;
      
    case 'CLEANUP_EXPIRED':
      self.cacheManager.cleanupExpiredEntries().then(result => {
        event.ports[0]?.postMessage(result);
      });
      break;
      
    case 'WARMUP_CACHE':
      if (data && data.urls) {
        self.cacheManager.warmupCache(data.urls, data.type || 'static').then(result => {
          event.ports[0]?.postMessage(result);
        });
      }
      break;
      
    case 'ADD_TO_OFFLINE_QUEUE':
      addToOfflineQueue(data).then(result => {
        event.ports[0]?.postMessage(result);
      });
      break;
  }
});

// 오프라인 큐 관리 (IndexedDB 연동)
async function getOfflineQueue() {
  try {
    if (typeof self.offlineDB === 'undefined') {
      // 동적으로 OfflineDatabase 인스턴스 생성
      const OfflineDatabase = (await import('/static/js/modules/offline-database.js')).default;
      self.offlineDB = new OfflineDatabase();
      await self.offlineDB.init();
    }
    
    return await self.offlineDB.getOfflineQueue();
  } catch (error) {
    console.error('[SW] Failed to get offline queue:', error);
    return [];
  }
}

async function addToOfflineQueue(item) {
  try {
    if (typeof self.offlineDB === 'undefined') {
      const OfflineDatabase = (await import('/static/js/modules/offline-database.js')).default;
      self.offlineDB = new OfflineDatabase();
      await self.offlineDB.init();
    }
    
    await self.offlineDB.addToOfflineQueue(item);
    return { success: true, message: 'Added to offline queue' };
  } catch (error) {
    console.error('[SW] Failed to add to offline queue:', error);
    return { success: false, error: error.message };
  }
}

async function removeFromOfflineQueue(id) {
  try {
    if (typeof self.offlineDB === 'undefined') {
      const OfflineDatabase = (await import('/static/js/modules/offline-database.js')).default;
      self.offlineDB = new OfflineDatabase();
      await self.offlineDB.init();
    }
    
    await self.offlineDB.removeFromOfflineQueue(id);
    return { success: true, message: 'Removed from offline queue' };
  } catch (error) {
    console.error('[SW] Failed to remove from offline queue:', error);
    return { success: false, error: error.message };
  }
}

// 캐시 정리 타이머 설정 (24시간마다)
setInterval(() => {
  if ('serviceWorker' in navigator && navigator.serviceWorker.ready) {
    navigator.serviceWorker.ready.then(registration => {
      if (registration.sync) {
        registration.sync.register('cache-maintenance');
      } else {
        performCacheMaintenance();
      }
    });
  }
}, 24 * 60 * 60 * 1000);

/**
 * IndexedDB 헬퍼 함수들
 */

// 최신 Notion 데이터 가져오기
async function fetchLatestNotionData() {
  try {
    console.log('[SW] Fetching latest Notion data...');
    
    // 데이터베이스 목록 가져오기
    const dbResponse = await fetch('/api/notion/databases/', {
      headers: { 'Authorization': await getStoredAuthToken() }
    });
    
    if (dbResponse.ok) {
      const databases = await dbResponse.json();
      
      for (const db of databases.results || []) {
        await self.offlineDB.saveData(self.offlineDB.stores.notionDatabases, {
          databaseId: db.id,
          title: extractNotionTitle(db.title),
          properties: db.properties,
          lastEditedTime: db.last_edited_time,
          createdTime: db.created_time
        });
        
        // 각 데이터베이스의 페이지들도 가져오기
        await fetchPagesFromDatabase(db.id);
        
        // API 레이트 리미트 방지
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
    
  } catch (error) {
    console.error('[SW] Failed to fetch latest Notion data:', error);
  }
}

// 특정 데이터베이스의 페이지 가져오기
async function fetchPagesFromDatabase(databaseId) {
  try {
    const response = await fetch(`/api/notion/databases/${databaseId}/query/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': await getStoredAuthToken()
      },
      body: JSON.stringify({ page_size: 50 })
    });
    
    if (response.ok) {
      const result = await response.json();
      
      for (const page of result.results || []) {
        await self.offlineDB.saveNotionPage(page);
      }
      
      console.log(`[SW] Fetched ${result.results?.length || 0} pages from database ${databaseId}`);
    }
    
  } catch (error) {
    console.error(`[SW] Failed to fetch pages from database ${databaseId}:`, error);
  }
}

// 저장된 인증 토큰 가져오기
async function getStoredAuthToken() {
  try {
    // IndexedDB에서 저장된 토큰 조회
    if (self.offlineDB) {
      const token = await self.offlineDB.getSetting('auth_token');
      if (token) return `Bearer ${token}`;
    }
    
    // 캐시에서 인증 상태 확인
    const apiCache = await caches.open(API_CACHE_NAME);
    const authResponse = await apiCache.match('/api/auth/status/');
    
    if (authResponse) {
      const authData = await authResponse.json();
      if (authData.token) {
        return `Bearer ${authData.token}`;
      }
    }
    
    return '';
    
  } catch (error) {
    console.error('[SW] Failed to get stored auth token:', error);
    return '';
  }
}

// Notion 제목 추출 헬퍼
function extractNotionTitle(titleArray) {
  if (Array.isArray(titleArray) && titleArray.length > 0) {
    return titleArray[0].plain_text || titleArray[0].text?.content || 'Untitled';
  }
  return 'Untitled';
}

// 메시지 처리에 IndexedDB 기능 추가
self.addEventListener('message', event => {
  console.log('[SW] Message received:', event.data);
  
  const { action, data } = event.data;
  
  switch (action) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'GET_CACHE_STATUS':
      self.cacheManager.getCacheStats().then(stats => {
        event.ports[0]?.postMessage(stats);
      });
      break;
      
    case 'CLEAR_CACHE':
      if (data && data.type) {
        self.cacheManager.clearCache(data.type).then(result => {
          event.ports[0]?.postMessage(result);
        });
      } else {
        self.cacheManager.clearAllCaches().then(result => {
          event.ports[0]?.postMessage(result);
        });
      }
      break;
      
    case 'CLEANUP_EXPIRED':
      self.cacheManager.cleanupExpiredEntries().then(result => {
        event.ports[0]?.postMessage(result);
      });
      break;
      
    case 'WARMUP_CACHE':
      if (data && data.urls) {
        self.cacheManager.warmupCache(data.urls, data.type || 'static').then(result => {
          event.ports[0]?.postMessage(result);
        });
      }
      break;
      
    case 'ADD_TO_OFFLINE_QUEUE':
      addToOfflineQueue(data).then(result => {
        event.ports[0]?.postMessage(result);
      });
      break;
      
    case 'GET_OFFLINE_STATS':
      getOfflineStats().then(stats => {
        event.ports[0]?.postMessage(stats);
      });
      break;
      
    case 'SEARCH_OFFLINE_PAGES':
      if (data && data.query) {
        searchOfflinePages(data.query).then(results => {
          event.ports[0]?.postMessage(results);
        });
      }
      break;
      
    case 'CLEAR_OFFLINE_DATA':
      clearOfflineData(data?.type).then(result => {
        event.ports[0]?.postMessage(result);
      });
      break;
  }
});

// 오프라인 통계 조회
async function getOfflineStats() {
  try {
    if (!self.offlineDB) {
      const OfflineDatabase = (await import('/static/js/modules/offline-database.js')).default;
      self.offlineDB = new OfflineDatabase();
      await self.offlineDB.init();
    }
    
    const stats = await self.offlineDB.getStats();
    const queueLength = (await self.offlineDB.getOfflineQueue()).length;
    
    return {
      ...stats,
      offlineQueue: { count: queueLength },
      isOnline: navigator.onLine,
      lastSync: await self.offlineDB.getSetting('last_sync_time')
    };
    
  } catch (error) {
    console.error('[SW] Failed to get offline stats:', error);
    return { error: error.message };
  }
}

// 오프라인 페이지 검색
async function searchOfflinePages(query) {
  try {
    if (!self.offlineDB) {
      const OfflineDatabase = (await import('/static/js/modules/offline-database.js')).default;
      self.offlineDB = new OfflineDatabase();
      await self.offlineDB.init();
    }
    
    return await self.offlineDB.searchPages(query);
    
  } catch (error) {
    console.error('[SW] Failed to search offline pages:', error);
    return [];
  }
}

// 오프라인 데이터 정리
async function clearOfflineData(type = null) {
  try {
    if (!self.offlineDB) {
      const OfflineDatabase = (await import('/static/js/modules/offline-database.js')).default;
      self.offlineDB = new OfflineDatabase();
      await self.offlineDB.init();
    }
    
    if (type) {
      // 특정 타입만 정리
      const storeName = self.offlineDB.stores[type];
      if (storeName) {
        const allData = await self.offlineDB.getAllData(storeName);
        for (const item of allData) {
          await self.offlineDB.deleteData(storeName, item.id || item.pageId || item.key);
        }
        return { success: true, message: `Cleared ${type} data` };
      }
    } else {
      // 모든 오프라인 데이터 정리 (설정 제외)
      for (const [key, storeName] of Object.entries(self.offlineDB.stores)) {
        if (key !== 'settings') {
          const allData = await self.offlineDB.getAllData(storeName);
          for (const item of allData) {
            await self.offlineDB.deleteData(storeName, item.id || item.pageId || item.key);
          }
        }
      }
      return { success: true, message: 'Cleared all offline data' };
    }
    
  } catch (error) {
    console.error('[SW] Failed to clear offline data:', error);
    return { success: false, error: error.message };
  }
}

console.log('[SW] Enhanced Service Worker with IndexedDB loaded successfully');