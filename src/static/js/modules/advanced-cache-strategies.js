/**
 * OneSquare 고급 캐싱 전략
 * 
 * 우선순위 기반 캐싱, 적응형 TTL, 예측 캐싱, 성능 기반 전략 선택
 */

class AdvancedCacheStrategies {
    constructor() {
        this.strategies = new Map();
        this.performanceMetrics = new Map();
        this.cacheHitRates = new Map();
        this.adaptiveConfig = {
            ttlMultipliers: new Map(),
            strategyPerformance: new Map(),
            networkConditions: 'good' // good, slow, offline
        };
        
        this.initStrategies();
        this.initPerformanceTracking();
    }

    /**
     * 캐싱 전략 초기화
     */
    initStrategies() {
        // 우선순위 기반 Cache First
        this.strategies.set('priority-cache-first', this.priorityCacheFirst.bind(this));
        
        // 적응형 Stale While Revalidate
        this.strategies.set('adaptive-swr', this.adaptiveStaleWhileRevalidate.bind(this));
        
        // 네트워크 조건 기반 전략
        this.strategies.set('network-aware', this.networkAwareStrategy.bind(this));
        
        // 시간 기반 캐시 (Time-based Cache)
        this.strategies.set('time-based', this.timeBasedStrategy.bind(this));
        
        // 사용량 기반 캐시 (Usage-based Cache)
        this.strategies.set('usage-based', this.usageBasedStrategy.bind(this));
        
        // 예측 캐시 (Predictive Cache)
        this.strategies.set('predictive', this.predictiveStrategy.bind(this));
        
        console.log('[AdvancedCache] Advanced caching strategies initialized');
    }

    /**
     * 성능 추적 초기화
     */
    initPerformanceTracking() {
        // 전략별 성능 메트릭 초기화
        this.strategies.forEach((_, strategyName) => {
            this.performanceMetrics.set(strategyName, {
                requests: 0,
                hits: 0,
                misses: 0,
                avgResponseTime: 0,
                errorCount: 0,
                totalResponseTime: 0
            });
        });
    }

    /**
     * 최적 전략 선택
     */
    selectOptimalStrategy(request) {
        const url = new URL(request.url);
        const resourceType = this.getResourceType(url);
        const priority = this.getResourcePriority(request);
        const networkCondition = this.getNetworkCondition();

        // 리소스 타입별 기본 전략
        let strategy = this.getDefaultStrategy(resourceType, priority);
        
        // 네트워크 조건에 따른 전략 조정
        strategy = this.adjustStrategyForNetwork(strategy, networkCondition);
        
        // 성능 기반 전략 최적화
        strategy = this.optimizeStrategyByPerformance(strategy, resourceType);
        
        return strategy;
    }

    /**
     * 기본 전략 선택
     */
    getDefaultStrategy(resourceType, priority) {
        const strategies = {
            'critical': {
                'css': 'priority-cache-first',
                'js': 'priority-cache-first',
                'image': 'priority-cache-first',
                'api': 'network-aware',
                'font': 'priority-cache-first'
            },
            'high': {
                'css': 'adaptive-swr',
                'js': 'adaptive-swr',
                'image': 'time-based',
                'api': 'network-aware',
                'font': 'priority-cache-first'
            },
            'normal': {
                'css': 'adaptive-swr',
                'js': 'adaptive-swr',
                'image': 'usage-based',
                'api': 'adaptive-swr',
                'font': 'time-based'
            },
            'low': {
                'css': 'time-based',
                'js': 'usage-based',
                'image': 'usage-based',
                'api': 'predictive',
                'font': 'time-based'
            }
        };

        return strategies[priority]?.[resourceType] || 'adaptive-swr';
    }

    /**
     * 우선순위 기반 Cache First 전략
     */
    async priorityCacheFirst(request, cacheType = 'static') {
        const startTime = performance.now();
        const cacheName = this.getCacheName(cacheType);
        const priority = this.getResourcePriority(request);
        
        try {
            const cache = await caches.open(cacheName);
            
            // 우선순위가 높은 리소스는 더 긴 TTL
            const ttlMultiplier = this.getTTLMultiplier(priority);
            const cachedResponse = await cache.match(request);
            
            if (cachedResponse && this.isCacheValid(cachedResponse, cacheType, ttlMultiplier)) {
                this.recordCacheHit('priority-cache-first', performance.now() - startTime);
                return cachedResponse;
            }

            // 캐시 미스 또는 만료된 경우 네트워크 요청
            const networkResponse = await fetch(request);
            
            if (networkResponse.ok) {
                // 우선순위에 따른 캐시 저장 전략
                await this.priorityAwareCachePut(cache, request, networkResponse.clone(), priority);
            }
            
            this.recordCacheMiss('priority-cache-first', performance.now() - startTime);
            return networkResponse;
            
        } catch (error) {
            // 네트워크 오류 시 오래된 캐시라도 반환
            const cache = await caches.open(cacheName);
            const staleResponse = await cache.match(request);
            
            if (staleResponse) {
                console.warn('[AdvancedCache] Serving stale content due to network error');
                return staleResponse;
            }
            
            throw error;
        }
    }

    /**
     * 적응형 Stale While Revalidate 전략
     */
    async adaptiveStaleWhileRevalidate(request, cacheType = 'dynamic') {
        const startTime = performance.now();
        const cacheName = this.getCacheName(cacheType);
        const cache = await caches.open(cacheName);
        
        // 현재 네트워크 조건에 따른 TTL 조정
        const networkSpeed = this.getNetworkSpeed();
        const adaptiveTTL = this.calculateAdaptiveTTL(cacheType, networkSpeed);
        
        const cachedResponse = await cache.match(request);
        
        // 백그라운드 재검증 로직
        const revalidatePromise = fetch(request)
            .then(async (networkResponse) => {
                if (networkResponse.ok) {
                    await this.adaptiveCachePut(cache, request, networkResponse.clone(), adaptiveTTL);
                }
                return networkResponse;
            })
            .catch(error => {
                console.warn('[AdvancedCache] Revalidation failed:', error);
                return null;
            });

        // 캐시가 있고 유효하면 즉시 반환
        if (cachedResponse && this.isCacheValid(cachedResponse, cacheType, 1, adaptiveTTL)) {
            // 백그라운드 재검증 시작 (Promise를 기다리지 않음)
            revalidatePromise;
            
            this.recordCacheHit('adaptive-swr', performance.now() - startTime);
            return cachedResponse;
        }
        
        // 캐시가 없거나 만료된 경우 네트워크 응답 대기
        const networkResponse = await revalidatePromise;
        this.recordCacheMiss('adaptive-swr', performance.now() - startTime);
        
        return networkResponse || cachedResponse || new Response('Offline', { status: 503 });
    }

    /**
     * 네트워크 조건 기반 전략
     */
    async networkAwareStrategy(request, cacheType = 'api') {
        const networkCondition = this.getNetworkCondition();
        const startTime = performance.now();
        
        switch (networkCondition) {
            case 'offline':
                return this.cacheOnlyStrategy(request, cacheType);
                
            case 'slow':
                return this.cacheFirstWithQuickFallback(request, cacheType);
                
            case 'good':
            default:
                return this.networkFirstWithCache(request, cacheType);
        }
    }

    /**
     * 시간 기반 캐시 전략
     */
    async timeBasedStrategy(request, cacheType = 'dynamic') {
        const cacheName = this.getCacheName(cacheType);
        const cache = await caches.open(cacheName);
        const timeOfDay = new Date().getHours();
        const dayOfWeek = new Date().getDay();
        
        // 시간대별 캐시 TTL 조정
        const timeTTL = this.getTimeBasedTTL(timeOfDay, dayOfWeek, cacheType);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse && this.isCacheValid(cachedResponse, cacheType, 1, timeTTL)) {
            return cachedResponse;
        }
        
        try {
            const networkResponse = await fetch(request);
            
            if (networkResponse.ok) {
                await this.timeAwareCachePut(cache, request, networkResponse.clone(), timeTTL);
            }
            
            return networkResponse;
            
        } catch (error) {
            return cachedResponse || new Response('Network Error', { status: 503 });
        }
    }

    /**
     * 사용량 기반 캐시 전략
     */
    async usageBasedStrategy(request, cacheType = 'dynamic') {
        const cacheName = this.getCacheName(cacheType);
        const cache = await caches.open(cacheName);
        const usageScore = await this.getResourceUsageScore(request.url);
        
        // 사용 빈도에 따른 캐시 우선순위 조정
        const usageTTL = this.calculateUsageBasedTTL(usageScore, cacheType);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse && this.isCacheValid(cachedResponse, cacheType, 1, usageTTL)) {
            // 사용량 증가 기록
            await this.incrementUsageScore(request.url);
            return cachedResponse;
        }
        
        try {
            const networkResponse = await fetch(request);
            
            if (networkResponse.ok) {
                // 사용량 스코어에 따른 캐시 우선순위 결정
                await this.usageAwareCachePut(cache, request, networkResponse.clone(), usageScore);
            }
            
            await this.incrementUsageScore(request.url);
            return networkResponse;
            
        } catch (error) {
            return cachedResponse || new Response('Network Error', { status: 503 });
        }
    }

    /**
     * 예측 캐시 전략
     */
    async predictiveStrategy(request, cacheType = 'dynamic') {
        const cacheName = this.getCacheName(cacheType);
        const cache = await caches.open(cacheName);
        const predictionScore = await this.getPredictionScore(request.url);
        
        // 예측 점수가 높은 리소스는 더 오래 캐시
        const predictiveTTL = this.calculatePredictiveTTL(predictionScore, cacheType);
        
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse && this.isCacheValid(cachedResponse, cacheType, 1, predictiveTTL)) {
            // 예측 정확도 업데이트
            await this.updatePredictionAccuracy(request.url, true);
            return cachedResponse;
        }
        
        try {
            const networkResponse = await fetch(request);
            
            if (networkResponse.ok) {
                await this.predictiveAwareCachePut(cache, request, networkResponse.clone(), predictionScore);
            }
            
            await this.updatePredictionAccuracy(request.url, false);
            return networkResponse;
            
        } catch (error) {
            return cachedResponse || new Response('Network Error', { status: 503 });
        }
    }

    /**
     * 캐시 전용 전략 (오프라인)
     */
    async cacheOnlyStrategy(request, cacheType) {
        const cacheName = this.getCacheName(cacheType);
        const cache = await caches.open(cacheName);
        const cachedResponse = await cache.match(request);
        
        return cachedResponse || new Response('Offline - No cached version available', { 
            status: 503,
            headers: { 'Content-Type': 'text/plain' }
        });
    }

    /**
     * 빠른 폴백을 포함한 Cache First
     */
    async cacheFirstWithQuickFallback(request, cacheType, timeout = 3000) {
        const cacheName = this.getCacheName(cacheType);
        const cache = await caches.open(cacheName);
        const cachedResponse = await cache.match(request);
        
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // 타임아웃을 포함한 네트워크 요청
        const networkPromise = fetch(request);
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Network timeout')), timeout);
        });
        
        try {
            const networkResponse = await Promise.race([networkPromise, timeoutPromise]);
            
            if (networkResponse.ok) {
                await cache.put(request, networkResponse.clone());
            }
            
            return networkResponse;
            
        } catch (error) {
            return new Response('Network timeout', { status: 503 });
        }
    }

    /**
     * 캐시를 포함한 Network First
     */
    async networkFirstWithCache(request, cacheType, timeout = 5000) {
        const cacheName = this.getCacheName(cacheType);
        
        try {
            const networkPromise = fetch(request);
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('Network timeout')), timeout);
            });
            
            const networkResponse = await Promise.race([networkPromise, timeoutPromise]);
            
            if (networkResponse.ok) {
                const cache = await caches.open(cacheName);
                await cache.put(request, networkResponse.clone());
            }
            
            return networkResponse;
            
        } catch (error) {
            // 네트워크 실패 시 캐시에서 찾기
            const cache = await caches.open(cacheName);
            const cachedResponse = await cache.match(request);
            
            return cachedResponse || new Response('Network and cache unavailable', { status: 503 });
        }
    }

    /**
     * 리소스 타입 식별
     */
    getResourceType(url) {
        const pathname = url.pathname.toLowerCase();
        
        if (pathname.endsWith('.css')) return 'css';
        if (pathname.endsWith('.js')) return 'js';
        if (pathname.match(/\.(png|jpg|jpeg|gif|webp|svg)$/)) return 'image';
        if (pathname.match(/\.(woff|woff2|ttf|eot)$/)) return 'font';
        if (pathname.startsWith('/api/')) return 'api';
        
        return 'other';
    }

    /**
     * 리소스 우선순위 결정
     */
    getResourcePriority(request) {
        const url = new URL(request.url);
        const fetchPriority = request.headers.get('fetchpriority');
        const isCritical = request.headers.get('data-critical');
        
        // 명시적 우선순위가 있으면 사용
        if (fetchPriority) {
            return fetchPriority;
        }
        
        // Critical 리소스 확인
        if (isCritical === 'true') {
            return 'critical';
        }
        
        // URL 패턴 기반 우선순위
        const criticalPaths = [
            '/static/css/common.css',
            '/static/js/common.js',
            '/static/js/pwa-manager.js',
            '/api/auth/status/',
            '/api/dashboard/data/'
        ];
        
        if (criticalPaths.some(path => url.pathname.includes(path))) {
            return 'critical';
        }
        
        const highPriorityPaths = [
            '/static/js/modules/dashboard-realtime.js',
            '/static/css/',
            '/api/notifications/'
        ];
        
        if (highPriorityPaths.some(path => url.pathname.includes(path))) {
            return 'high';
        }
        
        const lowPriorityPaths = [
            '/static/images/',
            '/api/analytics/',
            '/static/fonts/'
        ];
        
        if (lowPriorityPaths.some(path => url.pathname.includes(path))) {
            return 'low';
        }
        
        return 'normal';
    }

    /**
     * 네트워크 조건 확인
     */
    getNetworkCondition() {
        if (!navigator.onLine) {
            return 'offline';
        }
        
        if ('connection' in navigator) {
            const connection = navigator.connection;
            
            if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
                return 'slow';
            }
            
            if (connection.rtt > 500 || connection.downlink < 1.5) {
                return 'slow';
            }
        }
        
        return 'good';
    }

    /**
     * 네트워크 속도 측정
     */
    getNetworkSpeed() {
        if ('connection' in navigator) {
            return navigator.connection.downlink || 1; // Mbps
        }
        
        // 기본값
        return 1;
    }

    /**
     * TTL 배수 계산
     */
    getTTLMultiplier(priority) {
        const multipliers = {
            'critical': 3.0,
            'high': 2.0,
            'normal': 1.0,
            'low': 0.5
        };
        
        return multipliers[priority] || 1.0;
    }

    /**
     * 적응형 TTL 계산
     */
    calculateAdaptiveTTL(cacheType, networkSpeed) {
        const baseTTL = {
            'static': 7 * 24 * 60 * 60 * 1000,    // 7일
            'dynamic': 24 * 60 * 60 * 1000,       // 1일
            'api': 5 * 60 * 1000,                 // 5분
            'images': 30 * 24 * 60 * 60 * 1000,   // 30일
            'fonts': 30 * 24 * 60 * 60 * 1000     // 30일
        };
        
        const base = baseTTL[cacheType] || baseTTL.dynamic;
        
        // 네트워크 속도에 따른 TTL 조정
        if (networkSpeed < 1) {
            return base * 2; // 느린 네트워크에서는 더 오래 캐시
        } else if (networkSpeed > 10) {
            return base * 0.5; // 빠른 네트워크에서는 더 자주 갱신
        }
        
        return base;
    }

    /**
     * 시간 기반 TTL 계산
     */
    getTimeBasedTTL(hour, dayOfWeek, cacheType) {
        const baseTTL = this.calculateAdaptiveTTL(cacheType, 1);
        
        // 업무시간 (9-18시, 평일)에는 더 짧은 TTL
        const isBusinessHour = hour >= 9 && hour <= 18 && dayOfWeek >= 1 && dayOfWeek <= 5;
        
        if (isBusinessHour) {
            return baseTTL * 0.5;
        }
        
        // 야간/주말에는 더 긴 TTL
        return baseTTL * 1.5;
    }

    /**
     * 사용량 기반 TTL 계산
     */
    calculateUsageBasedTTL(usageScore, cacheType) {
        const baseTTL = this.calculateAdaptiveTTL(cacheType, 1);
        
        // 사용량이 높을수록 더 오래 캐시
        const multiplier = Math.min(3, 1 + (usageScore / 10));
        
        return baseTTL * multiplier;
    }

    /**
     * 예측 기반 TTL 계산
     */
    calculatePredictiveTTL(predictionScore, cacheType) {
        const baseTTL = this.calculateAdaptiveTTL(cacheType, 1);
        
        // 예측 점수가 높을수록 더 오래 캐시
        const multiplier = 1 + (predictionScore * 2);
        
        return baseTTL * multiplier;
    }

    /**
     * 캐시 이름 생성
     */
    getCacheName(cacheType) {
        const version = '1.1.0';
        return `onesquare-${cacheType}-${version}`;
    }

    /**
     * 캐시 유효성 검사 (고급)
     */
    isCacheValid(response, cacheType, ttlMultiplier = 1, customTTL = null) {
        const cacheTimestamp = response.headers.get('cache-timestamp');
        
        if (!cacheTimestamp) {
            return true; // 타임스탬프가 없으면 유효하다고 가정
        }
        
        const age = Date.now() - parseInt(cacheTimestamp);
        const ttl = customTTL || (this.calculateAdaptiveTTL(cacheType, 1) * ttlMultiplier);
        
        return age < ttl;
    }

    /**
     * 우선순위 기반 캐시 저장
     */
    async priorityAwareCachePut(cache, request, response, priority) {
        // 우선순위가 높은 리소스는 특별한 헤더 추가
        const responseToCache = new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: {
                ...response.headers,
                'cache-timestamp': Date.now().toString(),
                'cache-priority': priority,
                'cache-strategy': 'priority-cache-first'
            }
        });
        
        await cache.put(request, responseToCache);
    }

    /**
     * 적응형 캐시 저장
     */
    async adaptiveCachePut(cache, request, response, ttl) {
        const responseToCache = new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: {
                ...response.headers,
                'cache-timestamp': Date.now().toString(),
                'cache-ttl': ttl.toString(),
                'cache-strategy': 'adaptive-swr'
            }
        });
        
        await cache.put(request, responseToCache);
    }

    /**
     * 시간 인식 캐시 저장
     */
    async timeAwareCachePut(cache, request, response, ttl) {
        const responseToCache = new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: {
                ...response.headers,
                'cache-timestamp': Date.now().toString(),
                'cache-ttl': ttl.toString(),
                'cache-strategy': 'time-based',
                'cached-time-of-day': new Date().getHours().toString()
            }
        });
        
        await cache.put(request, responseToCache);
    }

    /**
     * 사용량 인식 캐시 저장
     */
    async usageAwareCachePut(cache, request, response, usageScore) {
        const responseToCache = new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: {
                ...response.headers,
                'cache-timestamp': Date.now().toString(),
                'cache-usage-score': usageScore.toString(),
                'cache-strategy': 'usage-based'
            }
        });
        
        await cache.put(request, responseToCache);
    }

    /**
     * 예측 인식 캐시 저장
     */
    async predictiveAwareCachePut(cache, request, response, predictionScore) {
        const responseToCache = new Response(response.body, {
            status: response.status,
            statusText: response.statusText,
            headers: {
                ...response.headers,
                'cache-timestamp': Date.now().toString(),
                'cache-prediction-score': predictionScore.toString(),
                'cache-strategy': 'predictive'
            }
        });
        
        await cache.put(request, responseToCache);
    }

    /**
     * 리소스 사용량 점수 조회
     */
    async getResourceUsageScore(url) {
        const usage = await this.getFromIndexedDB('resource-usage', url);
        return usage?.score || 0;
    }

    /**
     * 사용량 점수 증가
     */
    async incrementUsageScore(url) {
        const current = await this.getResourceUsageScore(url);
        await this.saveToIndexedDB('resource-usage', url, {
            score: current + 1,
            lastUsed: Date.now()
        });
    }

    /**
     * 예측 점수 조회
     */
    async getPredictionScore(url) {
        const prediction = await this.getFromIndexedDB('predictions', url);
        return prediction?.score || 0.5;
    }

    /**
     * 예측 정확도 업데이트
     */
    async updatePredictionAccuracy(url, wasHit) {
        const current = await this.getPredictionScore(url);
        const newScore = wasHit ? Math.min(1, current + 0.1) : Math.max(0, current - 0.1);
        
        await this.saveToIndexedDB('predictions', url, {
            score: newScore,
            lastUpdate: Date.now()
        });
    }

    /**
     * 캐시 히트 기록
     */
    recordCacheHit(strategy, responseTime) {
        const metrics = this.performanceMetrics.get(strategy);
        if (metrics) {
            metrics.requests++;
            metrics.hits++;
            metrics.totalResponseTime += responseTime;
            metrics.avgResponseTime = metrics.totalResponseTime / metrics.requests;
        }
    }

    /**
     * 캐시 미스 기록
     */
    recordCacheMiss(strategy, responseTime) {
        const metrics = this.performanceMetrics.get(strategy);
        if (metrics) {
            metrics.requests++;
            metrics.misses++;
            metrics.totalResponseTime += responseTime;
            metrics.avgResponseTime = metrics.totalResponseTime / metrics.requests;
        }
    }

    /**
     * IndexedDB 헬퍼 - 저장
     */
    async saveToIndexedDB(storeName, key, data) {
        try {
            const db = await this.openIndexedDB();
            const transaction = db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            await store.put(data, key);
        } catch (error) {
            console.warn('[AdvancedCache] IndexedDB save failed:', error);
        }
    }

    /**
     * IndexedDB 헬퍼 - 조회
     */
    async getFromIndexedDB(storeName, key) {
        try {
            const db = await this.openIndexedDB();
            const transaction = db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            return await store.get(key);
        } catch (error) {
            console.warn('[AdvancedCache] IndexedDB get failed:', error);
            return null;
        }
    }

    /**
     * IndexedDB 열기
     */
    openIndexedDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('OneSquareAdvancedCache', 1);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                if (!db.objectStoreNames.contains('resource-usage')) {
                    db.createObjectStore('resource-usage');
                }
                
                if (!db.objectStoreNames.contains('predictions')) {
                    db.createObjectStore('predictions');
                }
            };
        });
    }

    /**
     * 성능 통계 조회
     */
    getPerformanceStats() {
        const stats = {};
        
        this.performanceMetrics.forEach((metrics, strategy) => {
            stats[strategy] = {
                ...metrics,
                hitRate: metrics.requests > 0 ? (metrics.hits / metrics.requests) : 0,
                errorRate: metrics.requests > 0 ? (metrics.errorCount / metrics.requests) : 0
            };
        });
        
        return stats;
    }

    /**
     * 전략 실행
     */
    async executeStrategy(request) {
        const strategy = this.selectOptimalStrategy(request);
        const strategyFunction = this.strategies.get(strategy);
        
        if (!strategyFunction) {
            console.warn('[AdvancedCache] Unknown strategy:', strategy);
            return this.adaptiveStaleWhileRevalidate(request);
        }
        
        try {
            return await strategyFunction(request);
        } catch (error) {
            console.error('[AdvancedCache] Strategy execution failed:', error);
            // 폴백 전략
            return this.cacheOnlyStrategy(request, 'dynamic');
        }
    }
}

// Service Worker 환경에서만 인스턴스 생성
if (typeof self !== 'undefined' && self.constructor.name === 'ServiceWorkerGlobalScope') {
    self.advancedCacheStrategies = new AdvancedCacheStrategies();
}

// 모듈 내보내기
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdvancedCacheStrategies;
} else if (typeof window !== 'undefined') {
    window.AdvancedCacheStrategies = AdvancedCacheStrategies;
}