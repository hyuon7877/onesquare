/**
 * OneSquare 성능 모니터링 시스템
 * 
 * 실시간 성능 지표 수집, 분석, 최적화 제안
 * 목표: 3초 이내 대시보드 로딩 보장
 */

class PerformanceMonitor {
    constructor(config = {}) {
        this.config = {
            enableMetrics: config.enableMetrics !== false,
            enableProfiling: config.enableProfiling !== false,
            sampleRate: config.sampleRate || 0.1, // 10% 샘플링
            reportEndpoint: config.reportEndpoint || '/api/performance/',
            thresholds: {
                fcp: 1800,      // First Contentful Paint (1.8s)
                lcp: 2500,      // Largest Contentful Paint (2.5s)
                fid: 100,       // First Input Delay (100ms)
                cls: 0.1,       // Cumulative Layout Shift (0.1)
                ttfb: 800,      // Time to First Byte (0.8s)
                dashboardLoad: 3000  // Dashboard complete load (3s)
            },
            ...config
        };

        this.metrics = new Map();
        this.observers = new Map();
        this.performanceEntries = [];
        this.isReporting = false;
        
        this.init();
    }

    /**
     * 성능 모니터 초기화
     */
    async init() {
        console.log('[Performance] Initializing performance monitor...');

        try {
            // Core Web Vitals 측정
            this.initWebVitals();
            
            // Resource timing 모니터링
            this.initResourceTiming();
            
            // Navigation timing 측정
            this.initNavigationTiming();
            
            // Dashboard 특화 메트릭
            this.initDashboardMetrics();
            
            // 메모리 사용량 모니터링
            this.initMemoryMonitoring();
            
            // 네트워크 품질 측정
            this.initNetworkMonitoring();
            
            // 정기 리포트 스케줄링
            this.scheduleReporting();
            
            console.log('[Performance] Performance monitor initialized');
            
        } catch (error) {
            console.error('[Performance] Monitor initialization failed:', error);
        }
    }

    /**
     * Core Web Vitals 측정
     */
    initWebVitals() {
        // First Contentful Paint (FCP)
        if ('PerformanceObserver' in window) {
            try {
                const fcpObserver = new PerformanceObserver((entryList) => {
                    for (const entry of entryList.getEntries()) {
                        if (entry.name === 'first-contentful-paint') {
                            this.recordMetric('fcp', entry.startTime, {
                                timestamp: Date.now(),
                                url: location.href,
                                threshold: this.config.thresholds.fcp
                            });
                        }
                    }
                });
                fcpObserver.observe({ entryTypes: ['paint'] });
                this.observers.set('fcp', fcpObserver);
            } catch (error) {
                console.warn('[Performance] FCP observer failed:', error);
            }

            // Largest Contentful Paint (LCP)
            try {
                const lcpObserver = new PerformanceObserver((entryList) => {
                    const entries = entryList.getEntries();
                    const lastEntry = entries[entries.length - 1];
                    
                    this.recordMetric('lcp', lastEntry.startTime, {
                        timestamp: Date.now(),
                        url: location.href,
                        element: lastEntry.element?.tagName || 'unknown',
                        threshold: this.config.thresholds.lcp
                    });
                });
                lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
                this.observers.set('lcp', lcpObserver);
            } catch (error) {
                console.warn('[Performance] LCP observer failed:', error);
            }

            // First Input Delay (FID)
            try {
                const fidObserver = new PerformanceObserver((entryList) => {
                    for (const entry of entryList.getEntries()) {
                        this.recordMetric('fid', entry.processingStart - entry.startTime, {
                            timestamp: Date.now(),
                            url: location.href,
                            eventType: entry.name,
                            threshold: this.config.thresholds.fid
                        });
                    }
                });
                fidObserver.observe({ entryTypes: ['first-input'], buffered: true });
                this.observers.set('fid', fidObserver);
            } catch (error) {
                console.warn('[Performance] FID observer failed:', error);
            }

            // Cumulative Layout Shift (CLS)
            try {
                let clsValue = 0;
                const clsObserver = new PerformanceObserver((entryList) => {
                    for (const entry of entryList.getEntries()) {
                        if (!entry.hadRecentInput) {
                            clsValue += entry.value;
                        }
                    }
                    
                    this.recordMetric('cls', clsValue, {
                        timestamp: Date.now(),
                        url: location.href,
                        threshold: this.config.thresholds.cls
                    });
                });
                clsObserver.observe({ entryTypes: ['layout-shift'], buffered: true });
                this.observers.set('cls', clsObserver);
            } catch (error) {
                console.warn('[Performance] CLS observer failed:', error);
            }
        }
    }

    /**
     * 리소스 타이밍 모니터링
     */
    initResourceTiming() {
        if ('PerformanceObserver' in window) {
            try {
                const resourceObserver = new PerformanceObserver((entryList) => {
                    for (const entry of entryList.getEntries()) {
                        this.analyzeResourceTiming(entry);
                    }
                });
                resourceObserver.observe({ entryTypes: ['resource'] });
                this.observers.set('resource', resourceObserver);
            } catch (error) {
                console.warn('[Performance] Resource observer failed:', error);
            }
        }

        // 페이지 로드 완료 시 기존 리소스 분석
        window.addEventListener('load', () => {
            const resources = performance.getEntriesByType('resource');
            resources.forEach(entry => this.analyzeResourceTiming(entry));
        });
    }

    /**
     * 리소스 타이밍 분석
     */
    analyzeResourceTiming(entry) {
        const resourceType = this.getResourceType(entry.name);
        const loadTime = entry.responseEnd - entry.startTime;
        const size = entry.transferSize || 0;

        // 크리티컬 리소스 식별
        const isCritical = this.isCriticalResource(entry.name);
        
        // 성능 임계값 체크
        const thresholds = {
            css: 500,
            js: 1000,
            image: 2000,
            api: 1500,
            font: 800
        };

        const threshold = thresholds[resourceType] || 2000;
        const isSlowLoading = loadTime > threshold;

        if (isSlowLoading || isCritical) {
            this.recordResourceMetric(entry.name, {
                type: resourceType,
                loadTime: loadTime,
                size: size,
                isCritical: isCritical,
                isSlowLoading: isSlowLoading,
                cacheHit: entry.transferSize === 0,
                timestamp: Date.now()
            });
        }
    }

    /**
     * 네비게이션 타이밍 측정
     */
    initNavigationTiming() {
        window.addEventListener('load', () => {
            const navigation = performance.getEntriesByType('navigation')[0];
            if (navigation) {
                // Time to First Byte
                const ttfb = navigation.responseStart - navigation.requestStart;
                this.recordMetric('ttfb', ttfb, {
                    timestamp: Date.now(),
                    url: location.href,
                    threshold: this.config.thresholds.ttfb
                });

                // DOM Content Loaded
                const dcl = navigation.domContentLoadedEventEnd - navigation.navigationStart;
                this.recordMetric('dcl', dcl, {
                    timestamp: Date.now(),
                    url: location.href
                });

                // Page Load Complete
                const loadComplete = navigation.loadEventEnd - navigation.navigationStart;
                this.recordMetric('load_complete', loadComplete, {
                    timestamp: Date.now(),
                    url: location.href
                });

                console.log('[Performance] Navigation timing:', {
                    ttfb: ttfb,
                    dcl: dcl,
                    loadComplete: loadComplete
                });
            }
        });
    }

    /**
     * 대시보드 특화 메트릭
     */
    initDashboardMetrics() {
        // 대시보드 위젯 로딩 시간 측정
        this.dashboardStartTime = performance.now();
        
        // 위젯 로딩 완료 감지
        const checkDashboardComplete = () => {
            const widgets = document.querySelectorAll('[data-widget-id]');
            const loadedWidgets = document.querySelectorAll('[data-widget-id][data-loaded="true"]');
            
            if (widgets.length > 0 && widgets.length === loadedWidgets.length) {
                const dashboardLoadTime = performance.now() - this.dashboardStartTime;
                
                this.recordMetric('dashboard_load', dashboardLoadTime, {
                    timestamp: Date.now(),
                    url: location.href,
                    widgetCount: widgets.length,
                    threshold: this.config.thresholds.dashboardLoad
                });

                // 임계값 초과 시 최적화 제안
                if (dashboardLoadTime > this.config.thresholds.dashboardLoad) {
                    this.generateOptimizationSuggestions('dashboard_load', dashboardLoadTime);
                }
            }
        };

        // MutationObserver로 위젯 로딩 상태 감지
        const observer = new MutationObserver(checkDashboardComplete);
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['data-loaded']
        });

        // 타임아웃 안전장치
        setTimeout(checkDashboardComplete, 10000);
    }

    /**
     * 메모리 사용량 모니터링
     */
    initMemoryMonitoring() {
        if ('memory' in performance) {
            const checkMemory = () => {
                const memory = performance.memory;
                this.recordMetric('memory_usage', memory.usedJSHeapSize, {
                    total: memory.totalJSHeapSize,
                    limit: memory.jsHeapSizeLimit,
                    timestamp: Date.now(),
                    utilizationRate: memory.usedJSHeapSize / memory.jsHeapSizeLimit
                });

                // 메모리 사용률 80% 초과 시 경고
                if (memory.usedJSHeapSize / memory.jsHeapSizeLimit > 0.8) {
                    console.warn('[Performance] High memory usage detected:', memory);
                    this.triggerMemoryCleanup();
                }
            };

            checkMemory();
            setInterval(checkMemory, 30000); // 30초마다 체크
        }
    }

    /**
     * 네트워크 품질 측정
     */
    initNetworkMonitoring() {
        if ('connection' in navigator) {
            const connection = navigator.connection;
            
            this.recordMetric('network_info', 0, {
                effectiveType: connection.effectiveType,
                downlink: connection.downlink,
                rtt: connection.rtt,
                saveData: connection.saveData,
                timestamp: Date.now()
            });

            // 네트워크 상태 변경 감지
            connection.addEventListener('change', () => {
                this.recordMetric('network_change', 0, {
                    effectiveType: connection.effectiveType,
                    downlink: connection.downlink,
                    rtt: connection.rtt,
                    timestamp: Date.now()
                });

                // 저속 네트워크에서 최적화 모드 활성화
                if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
                    this.enableSlowNetworkOptimizations();
                }
            });
        }
    }

    /**
     * 메트릭 기록
     */
    recordMetric(name, value, metadata = {}) {
        if (!this.config.enableMetrics) return;

        const metric = {
            name: name,
            value: value,
            metadata: metadata,
            timestamp: Date.now(),
            url: location.href,
            userAgent: navigator.userAgent
        };

        // 메트릭 저장
        if (!this.metrics.has(name)) {
            this.metrics.set(name, []);
        }
        this.metrics.get(name).push(metric);

        // 성능 임계값 체크
        if (metadata.threshold && value > metadata.threshold) {
            this.handlePerformanceViolation(name, value, metadata.threshold);
        }

        console.log(`[Performance] ${name}: ${value}ms`, metadata);
    }

    /**
     * 리소스 메트릭 기록
     */
    recordResourceMetric(url, data) {
        const resourceMetrics = this.metrics.get('resources') || [];
        resourceMetrics.push({
            url: url,
            ...data
        });
        this.metrics.set('resources', resourceMetrics);
    }

    /**
     * 성능 임계값 위반 처리
     */
    handlePerformanceViolation(metric, value, threshold) {
        console.warn(`[Performance] Threshold violation: ${metric} = ${value}ms (threshold: ${threshold}ms)`);
        
        // 성능 알림 표시
        this.showPerformanceAlert(metric, value, threshold);
        
        // 자동 최적화 트리거
        this.triggerOptimization(metric, value);
    }

    /**
     * 리소스 타입 식별
     */
    getResourceType(url) {
        const extension = url.split('.').pop().toLowerCase();
        
        if (['css'].includes(extension)) return 'css';
        if (['js'].includes(extension)) return 'js';
        if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(extension)) return 'image';
        if (['woff', 'woff2', 'ttf', 'eot'].includes(extension)) return 'font';
        if (url.includes('/api/')) return 'api';
        
        return 'other';
    }

    /**
     * 크리티컬 리소스 판단
     */
    isCriticalResource(url) {
        const criticalPaths = [
            '/static/css/common.css',
            '/static/js/common.js',
            '/static/js/pwa-manager.js',
            '/static/js/modules/dashboard-realtime.js',
            '/api/auth/status/',
            '/api/dashboard/data/'
        ];

        return criticalPaths.some(path => url.includes(path));
    }

    /**
     * 최적화 제안 생성
     */
    generateOptimizationSuggestions(metric, value) {
        const suggestions = [];

        switch (metric) {
            case 'dashboard_load':
                if (value > 5000) {
                    suggestions.push('위젯 지연 로딩 구현 고려');
                    suggestions.push('대시보드 초기 렌더링 최적화');
                }
                if (value > 8000) {
                    suggestions.push('서버 사이드 렌더링 검토');
                    suggestions.push('데이터베이스 쿼리 최적화');
                }
                break;
                
            case 'lcp':
                suggestions.push('이미지 최적화 및 지연 로딩');
                suggestions.push('크리티컬 CSS 인라인화');
                break;
                
            case 'fid':
                suggestions.push('JavaScript 번들 크기 줄이기');
                suggestions.push('Long Task 분할 고려');
                break;
        }

        if (suggestions.length > 0) {
            console.log(`[Performance] Optimization suggestions for ${metric}:`, suggestions);
        }
    }

    /**
     * 성능 알림 표시
     */
    showPerformanceAlert(metric, value, threshold) {
        if (this.config.enableProfiling) {
            const alert = document.createElement('div');
            alert.className = 'performance-alert';
            alert.innerHTML = `
                <div style="
                    position: fixed;
                    top: 10px;
                    right: 10px;
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    padding: 10px;
                    max-width: 300px;
                    font-size: 12px;
                    z-index: 10001;
                ">
                    <strong>Performance Warning</strong><br>
                    ${metric}: ${value}ms (threshold: ${threshold}ms)
                    <button onclick="this.parentElement.parentElement.remove()" style="float: right;">&times;</button>
                </div>
            `;
            
            document.body.appendChild(alert);
            
            setTimeout(() => {
                if (alert.parentElement) {
                    alert.remove();
                }
            }, 5000);
        }
    }

    /**
     * 자동 최적화 트리거
     */
    triggerOptimization(metric, value) {
        switch (metric) {
            case 'memory_usage':
                this.triggerMemoryCleanup();
                break;
                
            case 'dashboard_load':
                this.optimizeDashboardLoading();
                break;
                
            case 'lcp':
                this.optimizeImageLoading();
                break;
        }
    }

    /**
     * 메모리 정리
     */
    triggerMemoryCleanup() {
        // 캐시 정리
        if (window.pwaManager) {
            window.pwaManager.clearCache();
        }

        // 사용하지 않는 DOM 요소 정리
        const unusedElements = document.querySelectorAll('[data-cleanup="true"]');
        unusedElements.forEach(el => el.remove());

        console.log('[Performance] Memory cleanup triggered');
    }

    /**
     * 대시보드 로딩 최적화
     */
    optimizeDashboardLoading() {
        // 낮은 우선순위 위젯들을 지연 로딩으로 전환
        const widgets = document.querySelectorAll('[data-widget-priority="low"]');
        widgets.forEach(widget => {
            widget.style.display = 'none';
            
            // Intersection Observer로 뷰포트 진입 시 로딩
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.display = '';
                        observer.unobserve(entry.target);
                    }
                });
            });
            observer.observe(widget);
        });

        console.log('[Performance] Dashboard loading optimized');
    }

    /**
     * 이미지 로딩 최적화
     */
    optimizeImageLoading() {
        const images = document.querySelectorAll('img[src]:not([data-optimized])');
        
        images.forEach(img => {
            // WebP 지원 확인 후 변환
            if (this.supportsWebP()) {
                const webpSrc = img.src.replace(/\.(jpg|jpeg|png)$/, '.webp');
                
                // WebP 버전이 존재하는지 확인
                const testImg = new Image();
                testImg.onload = () => {
                    img.src = webpSrc;
                };
                testImg.onerror = () => {
                    // WebP 버전이 없으면 원본 유지
                };
                testImg.src = webpSrc;
            }
            
            img.setAttribute('data-optimized', 'true');
        });
    }

    /**
     * WebP 지원 확인
     */
    supportsWebP() {
        return new Promise(resolve => {
            const webP = new Image();
            webP.onload = webP.onerror = () => {
                resolve(webP.height === 2);
            };
            webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
        });
    }

    /**
     * 저속 네트워크 최적화 활성화
     */
    enableSlowNetworkOptimizations() {
        console.log('[Performance] Enabling slow network optimizations');
        
        // 이미지 품질 낮춤
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            if (img.src.includes('?')) {
                img.src += '&quality=60';
            } else {
                img.src += '?quality=60';
            }
        });
        
        // 자동 새로고침 간격 늘리기
        if (window.dashboard) {
            window.dashboard.config.refreshInterval *= 2;
        }
    }

    /**
     * 정기 리포트 스케줄링
     */
    scheduleReporting() {
        // 5분마다 성능 데이터 서버로 전송
        setInterval(() => {
            if (Math.random() < this.config.sampleRate) {
                this.reportMetrics();
            }
        }, 300000); // 5분

        // 페이지 언로드 시 최종 리포트
        window.addEventListener('beforeunload', () => {
            this.reportMetrics(true);
        });
    }

    /**
     * 성능 메트릭 서버 리포트
     */
    async reportMetrics(isUnloading = false) {
        if (this.isReporting || this.metrics.size === 0) return;
        
        this.isReporting = true;
        
        try {
            const reportData = {
                url: location.href,
                timestamp: Date.now(),
                sessionId: this.getSessionId(),
                metrics: Object.fromEntries(this.metrics),
                userAgent: navigator.userAgent,
                viewport: {
                    width: window.innerWidth,
                    height: window.innerHeight
                },
                connection: navigator.connection ? {
                    effectiveType: navigator.connection.effectiveType,
                    downlink: navigator.connection.downlink,
                    rtt: navigator.connection.rtt
                } : null
            };

            if (isUnloading && 'sendBeacon' in navigator) {
                // 페이지 언로드 시 beacon 사용
                navigator.sendBeacon(
                    this.config.reportEndpoint,
                    JSON.stringify(reportData)
                );
            } else {
                // 일반적인 fetch 요청
                await fetch(this.config.reportEndpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(reportData)
                });
            }

            // 리포트 후 메트릭 초기화 (메모리 절약)
            this.metrics.clear();
            
            console.log('[Performance] Metrics reported to server');
            
        } catch (error) {
            console.error('[Performance] Failed to report metrics:', error);
        } finally {
            this.isReporting = false;
        }
    }

    /**
     * 성능 통계 조회
     */
    getPerformanceStats() {
        const stats = {
            metricsCount: this.metrics.size,
            observersActive: this.observers.size,
            memoryUsage: performance.memory ? {
                used: performance.memory.usedJSHeapSize,
                total: performance.memory.totalJSHeapSize,
                limit: performance.memory.jsHeapSizeLimit
            } : null
        };

        // 각 메트릭별 통계 계산
        this.metrics.forEach((values, name) => {
            if (values.length > 0) {
                const numericValues = values
                    .map(v => v.value)
                    .filter(v => typeof v === 'number');
                
                if (numericValues.length > 0) {
                    stats[name] = {
                        count: numericValues.length,
                        avg: numericValues.reduce((a, b) => a + b, 0) / numericValues.length,
                        min: Math.min(...numericValues),
                        max: Math.max(...numericValues),
                        latest: values[values.length - 1].value
                    };
                }
            }
        });

        return stats;
    }

    /**
     * 세션 ID 생성
     */
    getSessionId() {
        let sessionId = sessionStorage.getItem('performance_session_id');
        if (!sessionId) {
            sessionId = Date.now().toString() + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('performance_session_id', sessionId);
        }
        return sessionId;
    }

    /**
     * 정리
     */
    destroy() {
        // 모든 observer 해제
        this.observers.forEach(observer => {
            observer.disconnect();
        });
        this.observers.clear();
        
        // 메트릭 데이터 정리
        this.metrics.clear();
        
        console.log('[Performance] Performance monitor destroyed');
    }
}

// 전역으로 내보내기
window.PerformanceMonitor = PerformanceMonitor;

// 자동 초기화 (개발 환경에서만)
if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
    window.addEventListener('DOMContentLoaded', () => {
        window.performanceMonitor = new PerformanceMonitor({
            enableProfiling: true,
            sampleRate: 1.0 // 개발환경에서는 100% 샘플링
        });
    });
}