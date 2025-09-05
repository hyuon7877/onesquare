/**
 * OneSquare PWA Performance Optimizer
 * 
 * PWA 성능 최적화 전문 모듈:
 * - Critical Rendering Path 최적화
 * - Resource Preloading & Prefetching
 * - Bundle Splitting & Lazy Loading
 * - Image Optimization & WebP Conversion
 * - Performance Monitoring & Metrics
 */

class PWAPerformanceOptimizer {
    constructor(options = {}) {
        this.version = '2.1.0';
        this.isInitialized = false;
        
        this.config = {
            // 성능 목표 설정
            targetMetrics: {
                firstContentfulPaint: 1800,    // 1.8초
                largestContentfulPaint: 2500,  // 2.5초
                firstInputDelay: 100,          // 100ms
                cumulativeLayoutShift: 0.1     // 0.1
            },
            
            // 리소스 최적화 설정
            resourceOptimization: {
                enableImageOptimization: true,
                enableLazyLoading: true,
                enableResourceHints: true,
                enableCriticalCSS: true,
                enableJSMinification: true
            },
            
            // 네트워크 적응 설정
            adaptiveLoading: {
                enableDataSaver: true,
                enableNetworkAdaptation: true,
                enableBatteryOptimization: true
            },
            
            // 캐시 전략
            cacheStrategy: {
                enablePersistentStorage: true,
                enablePreloadCache: true,
                enableSmartPrefetch: true
            },
            
            ...options
        };
        
        this.performanceObserver = null;
        this.resourceLoadTimes = new Map();
        this.criticalResources = new Set();
        this.performanceMetrics = {};
        this.networkInfo = {};
        this.deviceInfo = {};
        
        this.init();
    }
    
    /**
     * 성능 최적화 모듈 초기화
     */
    async init() {
        if (this.isInitialized) return;
        
        console.log('[PWA-Optimizer] Initializing performance optimization...');
        
        try {
            // 디바이스 및 네트워크 정보 수집
            await this.detectEnvironment();
            
            // Critical Rendering Path 최적화
            await this.optimizeCriticalRenderingPath();
            
            // 성능 모니터링 설정
            await this.setupPerformanceMonitoring();
            
            // 리소스 최적화 설정
            await this.setupResourceOptimization();
            
            // 적응형 로딩 설정
            await this.setupAdaptiveLoading();
            
            // 성능 메트릭 수집 시작
            this.startPerformanceTracking();
            
            this.isInitialized = true;
            console.log('[PWA-Optimizer] Performance optimization initialized successfully');
            
        } catch (error) {
            console.error('[PWA-Optimizer] Initialization failed:', error);
        }
    }
    
    /**
     * 환경 정보 감지 (네트워크, 디바이스, 배터리)
     */
    async detectEnvironment() {
        // 네트워크 정보 수집
        if ('connection' in navigator) {
            this.networkInfo = {
                effectiveType: navigator.connection.effectiveType,
                downlink: navigator.connection.downlink,
                rtt: navigator.connection.rtt,
                saveData: navigator.connection.saveData
            };
        }
        
        // 디바이스 정보 수집
        this.deviceInfo = {
            memory: navigator.deviceMemory || 4,
            hardwareConcurrency: navigator.hardwareConcurrency || 2,
            userAgent: navigator.userAgent,
            platform: navigator.platform
        };
        
        // 배터리 정보 수집 (지원되는 경우)
        if ('getBattery' in navigator) {
            try {
                const battery = await navigator.getBattery();
                this.deviceInfo.battery = {
                    level: battery.level,
                    charging: battery.charging
                };
            } catch (error) {
                console.warn('[PWA-Optimizer] Battery API not supported');
            }
        }
        
        console.log('[PWA-Optimizer] Environment detected:', {
            network: this.networkInfo,
            device: this.deviceInfo
        });
    }
    
    /**
     * Critical Rendering Path 최적화
     */
    async optimizeCriticalRenderingPath() {
        console.log('[PWA-Optimizer] Optimizing Critical Rendering Path...');
        
        // Critical CSS 인라인 삽입
        if (this.config.resourceOptimization.enableCriticalCSS) {
            await this.inlineCriticalCSS();
        }
        
        // 중요하지 않은 CSS 지연 로딩
        await this.deferNonCriticalCSS();
        
        // 폰트 최적화
        await this.optimizeFontLoading();
        
        // JavaScript 지연 실행
        await this.deferNonCriticalJS();
        
        // 이미지 지연 로딩 설정
        if (this.config.resourceOptimization.enableLazyLoading) {
            await this.setupLazyLoading();
        }
    }
    
    /**
     * Critical CSS 인라인 삽입
     */
    async inlineCriticalCSS() {
        const criticalCSS = `
            /* Critical CSS - Above the fold content */
            body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
            .container { max-width: 1200px; margin: 0 auto; padding: 0 20px; }
            .header { background: #2c3e50; color: white; padding: 1rem 0; position: sticky; top: 0; z-index: 1000; }
            .nav { display: flex; align-items: center; justify-content: between; }
            .logo { font-size: 1.5rem; font-weight: bold; }
            .loading { display: flex; align-items: center; justify-content: center; min-height: 200px; }
            .btn-primary { background: #3498db; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 4px; cursor: pointer; }
            .alert { padding: 0.75rem; border-radius: 4px; margin-bottom: 1rem; }
            .alert-error { background: #e74c3c; color: white; }
            .alert-success { background: #27ae60; color: white; }
            .hidden { display: none !important; }
            .fade-in { animation: fadeIn 0.3s ease-in; }
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            
            /* Mobile First Responsive */
            @media (max-width: 768px) {
                .container { padding: 0 15px; }
                .header { padding: 0.5rem 0; }
                .nav { flex-direction: column; gap: 0.5rem; }
            }
        `;
        
        // Critical CSS를 head에 인라인으로 삽입
        const style = document.createElement('style');
        style.textContent = criticalCSS;
        style.setAttribute('data-critical', 'true');
        document.head.insertBefore(style, document.head.firstChild);
        
        console.log('[PWA-Optimizer] Critical CSS inlined');
    }
    
    /**
     * Non-critical CSS 지연 로딩
     */
    async deferNonCriticalCSS() {
        const nonCriticalLinks = document.querySelectorAll('link[rel="stylesheet"]:not([data-critical])');
        
        nonCriticalLinks.forEach(link => {
            // 미디어 속성을 이용한 지연 로딩
            link.setAttribute('media', 'print');
            link.addEventListener('load', () => {
                link.setAttribute('media', 'all');
            });
        });
        
        console.log(`[PWA-Optimizer] Deferred ${nonCriticalLinks.length} non-critical CSS files`);
    }
    
    /**
     * 폰트 로딩 최적화
     */
    async optimizeFontLoading() {
        // 폰트 미리 로드
        const fontPreloads = [
            { href: '/static/fonts/noto-sans-kr.woff2', family: 'Noto Sans KR' },
            { href: '/static/fonts/roboto.woff2', family: 'Roboto' }
        ];
        
        fontPreloads.forEach(font => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.href = font.href;
            link.as = 'font';
            link.type = 'font/woff2';
            link.crossOrigin = 'anonymous';
            document.head.appendChild(link);
        });
        
        // 폰트 display: swap CSS 추가
        const fontCSS = `
            @font-face {
                font-family: 'Noto Sans KR';
                font-display: swap;
                src: url('/static/fonts/noto-sans-kr.woff2') format('woff2');
            }
            @font-face {
                font-family: 'Roboto';
                font-display: swap;
                src: url('/static/fonts/roboto.woff2') format('woff2');
            }
        `;
        
        const style = document.createElement('style');
        style.textContent = fontCSS;
        document.head.appendChild(style);
        
        console.log('[PWA-Optimizer] Font loading optimized');
    }
    
    /**
     * Non-critical JavaScript 지연 실행
     */
    async deferNonCriticalJS() {
        const nonCriticalScripts = document.querySelectorAll('script[src]:not([data-critical])');
        
        // Intersection Observer로 뷰포트에 진입할 때 로드
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const script = entry.target;
                    if (script.dataset.src) {
                        script.src = script.dataset.src;
                        script.removeAttribute('data-src');
                        observer.unobserve(script);
                    }
                }
            });
        });
        
        nonCriticalScripts.forEach(script => {
            const src = script.src;
            script.dataset.src = src;
            script.removeAttribute('src');
            observer.observe(script);
        });
        
        console.log(`[PWA-Optimizer] Deferred ${nonCriticalScripts.length} non-critical JavaScript files`);
    }
    
    /**
     * 이미지 지연 로딩 설정
     */
    async setupLazyLoading() {
        // 네이티브 lazy loading 지원 확인
        const supportsNativeLazyLoading = 'loading' in HTMLImageElement.prototype;
        
        if (supportsNativeLazyLoading) {
            // 네이티브 lazy loading 사용
            document.querySelectorAll('img:not([loading])').forEach(img => {
                img.loading = 'lazy';
            });
            console.log('[PWA-Optimizer] Native lazy loading enabled');
        } else {
            // Intersection Observer 기반 lazy loading
            this.setupIntersectionObserverLazyLoading();
        }
        
        // WebP 지원 확인 및 이미지 최적화
        await this.setupImageOptimization();
    }
    
    /**
     * Intersection Observer 기반 지연 로딩
     */
    setupIntersectionObserverLazyLoading() {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img.dataset.src) {
                        img.src = img.dataset.src;
                        img.classList.add('fade-in');
                        img.removeAttribute('data-src');
                        observer.unobserve(img);
                    }
                }
            });
        }, {
            rootMargin: '50px 0px', // 50px 먼저 로드
            threshold: 0.01
        });
        
        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
        
        console.log('[PWA-Optimizer] Intersection Observer lazy loading enabled');
    }
    
    /**
     * 이미지 최적화 설정
     */
    async setupImageOptimization() {
        if (!this.config.resourceOptimization.enableImageOptimization) return;
        
        // WebP 지원 확인
        const supportsWebP = await this.checkWebPSupport();
        
        if (supportsWebP) {
            // 이미지를 WebP로 변환
            document.querySelectorAll('img').forEach(img => {
                const src = img.src || img.dataset.src;
                if (src && !src.includes('.webp')) {
                    const webpSrc = this.convertToWebP(src);
                    if (img.src) {
                        img.src = webpSrc;
                    } else if (img.dataset.src) {
                        img.dataset.src = webpSrc;
                    }
                }
            });
            
            console.log('[PWA-Optimizer] WebP optimization enabled');
        }
        
        // 반응형 이미지 설정
        this.setupResponsiveImages();
    }
    
    /**
     * WebP 지원 확인
     */
    checkWebPSupport() {
        return new Promise(resolve => {
            const webp = new Image();
            webp.onload = webp.onerror = () => {
                resolve(webp.height === 2);
            };
            webp.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
        });
    }
    
    /**
     * WebP 이미지 경로 생성
     */
    convertToWebP(originalSrc) {
        // 서버에 WebP 변환 엔드포인트가 있다고 가정
        if (originalSrc.includes('/api/') || originalSrc.startsWith('data:')) {
            return originalSrc;
        }
        
        const url = new URL(originalSrc, window.location.origin);
        url.searchParams.set('format', 'webp');
        return url.toString();
    }
    
    /**
     * 반응형 이미지 설정
     */
    setupResponsiveImages() {
        document.querySelectorAll('img:not([srcset])').forEach(img => {
            const src = img.src || img.dataset.src;
            if (src && src.includes('/static/images/')) {
                const srcset = this.generateResponsiveSrcset(src);
                const sizes = '(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw';
                
                if (img.src) {
                    img.srcset = srcset;
                    img.sizes = sizes;
                } else if (img.dataset.src) {
                    img.dataset.srcset = srcset;
                    img.dataset.sizes = sizes;
                }
            }
        });
        
        console.log('[PWA-Optimizer] Responsive images configured');
    }
    
    /**
     * 반응형 이미지 srcset 생성
     */
    generateResponsiveSrcset(originalSrc) {
        const sizes = [320, 640, 960, 1280];
        const srcsets = sizes.map(size => {
            const url = new URL(originalSrc, window.location.origin);
            url.searchParams.set('w', size.toString());
            return `${url.toString()} ${size}w`;
        });
        
        return srcsets.join(', ');
    }
    
    /**
     * 성능 모니터링 설정
     */
    async setupPerformanceMonitoring() {
        if ('PerformanceObserver' in window) {
            // Core Web Vitals 모니터링
            this.observeCoreWebVitals();
            
            // 리소스 로딩 모니터링
            this.observeResourceLoading();
            
            // 네비게이션 타이밍 모니터링
            this.observeNavigationTiming();
        }
        
        // 커스텀 성능 메트릭 수집
        this.startCustomMetrics();
        
        console.log('[PWA-Optimizer] Performance monitoring enabled');
    }
    
    /**
     * Core Web Vitals 모니터링
     */
    observeCoreWebVitals() {
        // Largest Contentful Paint (LCP)
        new PerformanceObserver(entryList => {
            const entries = entryList.getEntries();
            const lastEntry = entries[entries.length - 1];
            
            this.performanceMetrics.lcp = lastEntry.startTime;
            console.log('[PWA-Optimizer] LCP:', lastEntry.startTime.toFixed(2) + 'ms');
            
            if (lastEntry.startTime > this.config.targetMetrics.largestContentfulPaint) {
                console.warn('[PWA-Optimizer] LCP exceeds target:', lastEntry.startTime.toFixed(2) + 'ms');
                this.optimizeLCP();
            }
        }).observe({ entryTypes: ['largest-contentful-paint'] });
        
        // First Input Delay (FID)
        new PerformanceObserver(entryList => {
            entryList.getEntries().forEach(entry => {
                this.performanceMetrics.fid = entry.processingStart - entry.startTime;
                console.log('[PWA-Optimizer] FID:', this.performanceMetrics.fid.toFixed(2) + 'ms');
                
                if (this.performanceMetrics.fid > this.config.targetMetrics.firstInputDelay) {
                    console.warn('[PWA-Optimizer] FID exceeds target:', this.performanceMetrics.fid.toFixed(2) + 'ms');
                    this.optimizeFID();
                }
            });
        }).observe({ entryTypes: ['first-input'], buffered: true });
        
        // Cumulative Layout Shift (CLS)
        let cumulativeLayoutShift = 0;
        new PerformanceObserver(entryList => {
            entryList.getEntries().forEach(entry => {
                if (!entry.hadRecentInput) {
                    cumulativeLayoutShift += entry.value;
                }
            });
            
            this.performanceMetrics.cls = cumulativeLayoutShift;
            console.log('[PWA-Optimizer] CLS:', cumulativeLayoutShift.toFixed(3));
            
            if (cumulativeLayoutShift > this.config.targetMetrics.cumulativeLayoutShift) {
                console.warn('[PWA-Optimizer] CLS exceeds target:', cumulativeLayoutShift.toFixed(3));
                this.optimizeCLS();
            }
        }).observe({ entryTypes: ['layout-shift'] });
    }
    
    /**
     * 리소스 로딩 모니터링
     */
    observeResourceLoading() {
        new PerformanceObserver(entryList => {
            entryList.getEntries().forEach(entry => {
                this.resourceLoadTimes.set(entry.name, {
                    duration: entry.duration,
                    size: entry.transferSize || 0,
                    startTime: entry.startTime
                });
                
                // 느린 리소스 감지
                if (entry.duration > 1000) {
                    console.warn('[PWA-Optimizer] Slow resource detected:', entry.name, entry.duration.toFixed(2) + 'ms');
                    this.optimizeSlowResource(entry);
                }
            });
        }).observe({ entryTypes: ['resource'] });
    }
    
    /**
     * 네비게이션 타이밍 모니터링
     */
    observeNavigationTiming() {
        new PerformanceObserver(entryList => {
            entryList.getEntries().forEach(entry => {
                this.performanceMetrics.navigation = {
                    domContentLoaded: entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart,
                    loadComplete: entry.loadEventEnd - entry.loadEventStart,
                    firstContentfulPaint: this.getFirstContentfulPaint()
                };
                
                console.log('[PWA-Optimizer] Navigation metrics:', this.performanceMetrics.navigation);
            });
        }).observe({ entryTypes: ['navigation'] });
    }
    
    /**
     * First Contentful Paint 측정
     */
    getFirstContentfulPaint() {
        const fcpEntry = performance.getEntriesByName('first-contentful-paint')[0];
        return fcpEntry ? fcpEntry.startTime : 0;
    }
    
    /**
     * 커스텀 성능 메트릭 수집
     */
    startCustomMetrics() {
        // 페이지 로드 완료 시점 측정
        window.addEventListener('load', () => {
            this.performanceMetrics.pageLoadTime = performance.now();
            console.log('[PWA-Optimizer] Page load time:', this.performanceMetrics.pageLoadTime.toFixed(2) + 'ms');
        });
        
        // 첫 번째 사용자 상호작용 시점 측정
        ['click', 'touchstart', 'keydown'].forEach(eventType => {
            document.addEventListener(eventType, () => {
                if (!this.performanceMetrics.firstInteraction) {
                    this.performanceMetrics.firstInteraction = performance.now();
                    console.log('[PWA-Optimizer] First interaction:', this.performanceMetrics.firstInteraction.toFixed(2) + 'ms');
                }
            }, { once: true });
        });
    }
    
    /**
     * 리소스 최적화 설정
     */
    async setupResourceOptimization() {
        if (this.config.resourceOptimization.enableResourceHints) {
            await this.setupResourceHints();
        }
        
        if (this.config.cacheStrategy.enableSmartPrefetch) {
            await this.setupSmartPrefetching();
        }
        
        // 번들 분할 및 동적 import 설정
        await this.setupModularLoading();
        
        console.log('[PWA-Optimizer] Resource optimization configured');
    }
    
    /**
     * 리소스 힌트 설정 (preload, prefetch, preconnect)
     */
    async setupResourceHints() {
        // API 엔드포인트 preconnect
        const apiOrigins = [
            window.location.origin,
            'https://api.notion.com'
        ];
        
        apiOrigins.forEach(origin => {
            const link = document.createElement('link');
            link.rel = 'preconnect';
            link.href = origin;
            document.head.appendChild(link);
        });
        
        // 중요한 리소스 preload
        const criticalResources = [
            { href: '/static/css/common.css', as: 'style' },
            { href: '/static/js/common.js', as: 'script' },
            { href: '/static/js/pwa-manager.js', as: 'script' }
        ];
        
        criticalResources.forEach(resource => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.href = resource.href;
            link.as = resource.as;
            document.head.appendChild(link);
            
            this.criticalResources.add(resource.href);
        });
        
        console.log('[PWA-Optimizer] Resource hints configured');
    }
    
    /**
     * 스마트 프리페칭 설정
     */
    async setupSmartPrefetching() {
        // 사용자 행동 패턴 기반 예측 프리페치
        const prefetchCandidates = await this.analyzePrefetchCandidates();
        
        // Idle 시간에 프리페치 수행
        if ('requestIdleCallback' in window) {
            requestIdleCallback(() => {
                this.performSmartPrefetch(prefetchCandidates);
            });
        } else {
            // 폴백: setTimeout 사용
            setTimeout(() => {
                this.performSmartPrefetch(prefetchCandidates);
            }, 2000);
        }
    }
    
    /**
     * 프리페치 후보 분석
     */
    async analyzePrefetchCandidates() {
        // 현재 페이지 기반 예측
        const currentPath = window.location.pathname;
        const candidates = [];
        
        // 라우트 기반 예측
        const routePredictions = {
            '/': ['/dashboard/', '/auth/login/'],
            '/auth/login/': ['/dashboard/', '/auth/register/'],
            '/dashboard/': ['/reports/', '/calendar/', '/notifications/'],
            '/reports/': ['/reports/field/', '/reports/analytics/'],
            '/calendar/': ['/calendar/events/', '/calendar/schedule/']
        };
        
        const predicted = routePredictions[currentPath] || [];
        candidates.push(...predicted);
        
        // 링크 hover 기반 예측 추가
        this.setupHoverPrefetch();
        
        return [...new Set(candidates)]; // 중복 제거
    }
    
    /**
     * Hover 기반 프리페치 설정
     */
    setupHoverPrefetch() {
        document.addEventListener('mouseover', (e) => {
            const link = e.target.closest('a[href]');
            if (link && this.shouldPrefetchLink(link)) {
                this.prefetchResource(link.href);
            }
        });
    }
    
    /**
     * 링크 프리페치 여부 판단
     */
    shouldPrefetchLink(link) {
        const href = link.getAttribute('href');
        
        // 외부 링크 제외
        if (href.startsWith('http') && !href.includes(window.location.origin)) {
            return false;
        }
        
        // 이미 프리페치된 링크 제외
        if (link.dataset.prefetched) {
            return false;
        }
        
        // 파일 다운로드 링크 제외
        if (href.match(/\.(pdf|zip|exe|dmg)$/)) {
            return false;
        }
        
        return true;
    }
    
    /**
     * 스마트 프리페치 수행
     */
    async performSmartPrefetch(candidates) {
        for (const url of candidates) {
            // 네트워크 조건 확인
            if (this.networkInfo.saveData || this.networkInfo.effectiveType === '2g') {
                break; // 데이터 절약 모드에서는 프리페치 중단
            }
            
            await this.prefetchResource(url);
            
            // 과부하 방지를 위한 지연
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        console.log(`[PWA-Optimizer] Smart prefetch completed: ${candidates.length} resources`);
    }
    
    /**
     * 리소스 프리페치
     */
    async prefetchResource(url) {
        try {
            const link = document.createElement('link');
            link.rel = 'prefetch';
            link.href = url;
            document.head.appendChild(link);
            
            console.log(`[PWA-Optimizer] Prefetched: ${url}`);
        } catch (error) {
            console.warn(`[PWA-Optimizer] Prefetch failed for ${url}:`, error);
        }
    }
    
    /**
     * 모듈형 로딩 설정 (동적 import)
     */
    async setupModularLoading() {
        // Route-based code splitting
        if ('IntersectionObserver' in window) {
            this.setupRouteBasedSplitting();
        }
        
        // Feature-based lazy loading
        this.setupFeatureBasedLoading();
    }
    
    /**
     * 라우트 기반 코드 분할
     */
    setupRouteBasedSplitting() {
        const routeModules = {
            '/dashboard/': () => import('/static/js/modules/dashboard-performance-optimizer.js'),
            '/reports/': () => import('/static/js/modules/report-system.js'),
            '/calendar/': () => import('/static/js/modules/calendar-system.js'),
            '/notifications/': () => import('/static/js/modules/notification-system.js')
        };
        
        const currentPath = window.location.pathname;
        const moduleLoader = routeModules[currentPath];
        
        if (moduleLoader) {
            // Idle 시간에 모듈 로드
            if ('requestIdleCallback' in window) {
                requestIdleCallback(() => {
                    moduleLoader().then(module => {
                        console.log(`[PWA-Optimizer] Route module loaded: ${currentPath}`);
                    });
                });
            }
        }
    }
    
    /**
     * 기능 기반 지연 로딩
     */
    setupFeatureBasedLoading() {
        // 특정 기능이 필요할 때만 로드
        const featureLoaders = {
            camera: () => import('/static/js/modules/camera-capture.js'),
            charts: () => import('/static/js/modules/charts/chart-engine.js'),
            analytics: () => import('/static/js/modules/analytics-dashboard.js'),
            location: () => import('/static/js/modules/location-tracker.js')
        };
        
        // data-feature 속성을 가진 요소 감지
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const feature = entry.target.dataset.feature;
                    const loader = featureLoaders[feature];
                    
                    if (loader) {
                        loader().then(module => {
                            console.log(`[PWA-Optimizer] Feature module loaded: ${feature}`);
                            if (typeof module.default === 'function') {
                                module.default(entry.target);
                            }
                        });
                        observer.unobserve(entry.target);
                    }
                }
            });
        });
        
        document.querySelectorAll('[data-feature]').forEach(element => {
            observer.observe(element);
        });
    }
    
    /**
     * 적응형 로딩 설정
     */
    async setupAdaptiveLoading() {
        // 네트워크 조건에 따른 적응
        this.adaptToNetworkConditions();
        
        // 배터리 상태에 따른 적응
        if (this.config.adaptiveLoading.enableBatteryOptimization) {
            this.adaptToBatteryConditions();
        }
        
        // 디바이스 성능에 따른 적응
        this.adaptToDevicePerformance();
        
        console.log('[PWA-Optimizer] Adaptive loading configured');
    }
    
    /**
     * 네트워크 조건 적응
     */
    adaptToNetworkConditions() {
        if ('connection' in navigator) {
            const updateLoadingStrategy = () => {
                const connection = navigator.connection;
                
                if (connection.saveData || connection.effectiveType === '2g') {
                    // 데이터 절약 모드
                    this.enableDataSaverMode();
                } else if (connection.effectiveType === '3g') {
                    // 중간 품질 모드
                    this.enableMediumQualityMode();
                } else {
                    // 고품질 모드
                    this.enableHighQualityMode();
                }
            };
            
            // 초기 설정
            updateLoadingStrategy();
            
            // 네트워크 변경 시 업데이트
            navigator.connection.addEventListener('change', updateLoadingStrategy);
        }
    }
    
    /**
     * 데이터 절약 모드 활성화
     */
    enableDataSaverMode() {
        console.log('[PWA-Optimizer] Data saver mode enabled');
        
        // 이미지 품질 낮추기
        document.querySelectorAll('img').forEach(img => {
            if (img.src && !img.dataset.lowQuality) {
                const url = new URL(img.src, window.location.origin);
                url.searchParams.set('quality', '60');
                url.searchParams.set('format', 'webp');
                img.dataset.lowQuality = 'true';
                img.src = url.toString();
            }
        });
        
        // 애니메이션 비활성화
        document.body.classList.add('reduce-motion');
        
        // 자동 업데이트 비활성화
        this.config.adaptiveLoading.enableAutoUpdate = false;
    }
    
    /**
     * 중간 품질 모드 활성화
     */
    enableMediumQualityMode() {
        console.log('[PWA-Optimizer] Medium quality mode enabled');
        
        // 적당한 이미지 품질
        document.querySelectorAll('img').forEach(img => {
            if (img.src) {
                const url = new URL(img.src, window.location.origin);
                url.searchParams.set('quality', '80');
                img.src = url.toString();
            }
        });
    }
    
    /**
     * 고품질 모드 활성화
     */
    enableHighQualityMode() {
        console.log('[PWA-Optimizer] High quality mode enabled');
        
        // 최고 품질 이미지
        document.querySelectorAll('img').forEach(img => {
            if (img.src) {
                const url = new URL(img.src, window.location.origin);
                url.searchParams.set('quality', '95');
                img.src = url.toString();
            }
        });
        
        // 고급 애니메이션 활성화
        document.body.classList.remove('reduce-motion');
    }
    
    /**
     * 배터리 조건 적응
     */
    adaptToBatteryConditions() {
        if ('getBattery' in navigator) {
            navigator.getBattery().then(battery => {
                const updateBatteryStrategy = () => {
                    if (!battery.charging && battery.level < 0.2) {
                        // 배터리 절약 모드
                        this.enableBatterySaverMode();
                    } else if (battery.level < 0.5) {
                        // 절전 모드
                        this.enablePowerSavingMode();
                    } else {
                        // 일반 모드
                        this.enableNormalPowerMode();
                    }
                };
                
                // 초기 설정
                updateBatteryStrategy();
                
                // 배터리 상태 변경 시 업데이트
                battery.addEventListener('levelchange', updateBatteryStrategy);
                battery.addEventListener('chargingchange', updateBatteryStrategy);
            });
        }
    }
    
    /**
     * 배터리 절약 모드 활성화
     */
    enableBatterySaverMode() {
        console.log('[PWA-Optimizer] Battery saver mode enabled');
        
        // 백그라운드 동기화 중단
        this.config.adaptiveLoading.enableBackgroundSync = false;
        
        // 애니메이션 비활성화
        document.body.classList.add('reduce-motion');
        
        // 자동 새로고침 비활성화
        this.config.adaptiveLoading.enableAutoRefresh = false;
    }
    
    /**
     * 절전 모드 활성화
     */
    enablePowerSavingMode() {
        console.log('[PWA-Optimizer] Power saving mode enabled');
        
        // 백그라운드 동기화 간격 늘리기
        this.config.adaptiveLoading.backgroundSyncInterval *= 2;
    }
    
    /**
     * 일반 전력 모드 활성화
     */
    enableNormalPowerMode() {
        console.log('[PWA-Optimizer] Normal power mode enabled');
        
        // 모든 기능 정상 작동
        this.config.adaptiveLoading.enableBackgroundSync = true;
        this.config.adaptiveLoading.enableAutoRefresh = true;
        document.body.classList.remove('reduce-motion');
    }
    
    /**
     * 디바이스 성능 적응
     */
    adaptToDevicePerformance() {
        const isLowEndDevice = this.deviceInfo.memory < 4 || 
                               this.deviceInfo.hardwareConcurrency < 4;
        
        if (isLowEndDevice) {
            console.log('[PWA-Optimizer] Low-end device optimization enabled');
            
            // 복잡한 애니메이션 비활성화
            document.body.classList.add('low-end-device');
            
            // 동시 네트워크 요청 제한
            this.config.adaptiveLoading.maxConcurrentRequests = 2;
            
            // 캐시 크기 제한
            this.config.cacheStrategy.maxCacheSize = 50 * 1024 * 1024; // 50MB
        }
    }
    
    /**
     * 성능 추적 시작
     */
    startPerformanceTracking() {
        // 정기적으로 성능 리포트 전송
        setInterval(() => {
            this.reportPerformanceMetrics();
        }, 60000); // 1분마다
        
        // 페이지 언로드 시 최종 리포트
        window.addEventListener('beforeunload', () => {
            this.reportPerformanceMetrics(true);
        });
    }
    
    /**
     * 성능 메트릭 리포트
     */
    reportPerformanceMetrics(isFinal = false) {
        const report = {
            timestamp: Date.now(),
            url: window.location.href,
            userAgent: navigator.userAgent,
            metrics: this.performanceMetrics,
            networkInfo: this.networkInfo,
            deviceInfo: this.deviceInfo,
            isFinal
        };
        
        // 서버로 전송 (백그라운드)
        if ('navigator' in window && 'sendBeacon' in navigator) {
            navigator.sendBeacon('/api/performance/metrics/', JSON.stringify(report));
        } else {
            // 폴백: fetch 사용
            fetch('/api/performance/metrics/', {
                method: 'POST',
                body: JSON.stringify(report),
                headers: { 'Content-Type': 'application/json' }
            }).catch(error => {
                console.warn('[PWA-Optimizer] Failed to send performance metrics:', error);
            });
        }
    }
    
    /**
     * LCP 최적화
     */
    optimizeLCP() {
        console.log('[PWA-Optimizer] Optimizing LCP...');
        
        // 가장 큰 컨텐츠 요소 최적화
        const lcpElement = this.findLCPElement();
        if (lcpElement) {
            // 우선순위 높이기
            lcpElement.setAttribute('fetchpriority', 'high');
            
            // 이미지인 경우 preload
            if (lcpElement.tagName === 'IMG') {
                const preload = document.createElement('link');
                preload.rel = 'preload';
                preload.as = 'image';
                preload.href = lcpElement.src || lcpElement.dataset.src;
                document.head.appendChild(preload);
            }
        }
    }
    
    /**
     * FID 최적화
     */
    optimizeFID() {
        console.log('[PWA-Optimizer] Optimizing FID...');
        
        // 메인 스레드 블로킹 감소
        this.reduceMainThreadBlocking();
        
        // 이벤트 리스너 최적화
        this.optimizeEventListeners();
    }
    
    /**
     * CLS 최적화
     */
    optimizeCLS() {
        console.log('[PWA-Optimizer] Optimizing CLS...');
        
        // 레이아웃 시프트 방지
        this.preventLayoutShifts();
        
        // 폰트 로딩 최적화
        this.optimizeFontLoading();
    }
    
    /**
     * LCP 요소 찾기
     */
    findLCPElement() {
        // 뷰포트에서 가장 큰 요소 찾기
        const elements = document.querySelectorAll('img, video, div, section, main');
        let largestElement = null;
        let largestSize = 0;
        
        elements.forEach(element => {
            const rect = element.getBoundingClientRect();
            const size = rect.width * rect.height;
            
            if (size > largestSize && rect.top < window.innerHeight) {
                largestSize = size;
                largestElement = element;
            }
        });
        
        return largestElement;
    }
    
    /**
     * 메인 스레드 블로킹 감소
     */
    reduceMainThreadBlocking() {
        // 긴 작업을 작은 청크로 분할
        if ('scheduler' in window && 'postTask' in scheduler) {
            // 네이티브 스케줄러 사용
            this.useNativeScheduler();
        } else {
            // 폴백: MessageChannel 사용
            this.useMessageChannelScheduling();
        }
    }
    
    /**
     * 네이티브 스케줄러 사용
     */
    useNativeScheduler() {
        window.yieldToMain = () => {
            return new Promise(resolve => {
                scheduler.postTask(resolve, { priority: 'user-blocking' });
            });
        };
    }
    
    /**
     * MessageChannel 스케줄링
     */
    useMessageChannelScheduling() {
        const channel = new MessageChannel();
        const callbacks = [];
        
        channel.port2.onmessage = () => {
            const callback = callbacks.shift();
            if (callback) callback();
        };
        
        window.yieldToMain = () => {
            return new Promise(resolve => {
                callbacks.push(resolve);
                channel.port1.postMessage(null);
            });
        };
    }
    
    /**
     * 이벤트 리스너 최적화
     */
    optimizeEventListeners() {
        // 패시브 이벤트 리스너 사용
        const passiveEvents = ['touchstart', 'touchmove', 'scroll', 'wheel'];
        
        passiveEvents.forEach(eventType => {
            document.addEventListener(eventType, () => {}, { passive: true });
        });
        
        // 이벤트 위임 사용
        this.setupEventDelegation();
    }
    
    /**
     * 이벤트 위임 설정
     */
    setupEventDelegation() {
        document.addEventListener('click', (e) => {
            const button = e.target.closest('[data-action]');
            if (button) {
                const action = button.dataset.action;
                this.handleDelegatedAction(action, button, e);
            }
        });
    }
    
    /**
     * 위임된 액션 처리
     */
    handleDelegatedAction(action, element, event) {
        // 액션별 처리 로직
        const actions = {
            'toggle': () => element.classList.toggle('active'),
            'submit': () => element.closest('form')?.submit(),
            'close': () => element.closest('[data-closable]')?.remove()
        };
        
        const handler = actions[action];
        if (handler) {
            handler();
        }
    }
    
    /**
     * 레이아웃 시프트 방지
     */
    preventLayoutShifts() {
        // 이미지에 aspect-ratio 설정
        document.querySelectorAll('img:not([style*="aspect-ratio"])').forEach(img => {
            if (img.width && img.height) {
                const aspectRatio = img.width / img.height;
                img.style.aspectRatio = aspectRatio.toString();
            }
        });
        
        // 폰트 로딩 중 크기 유지
        document.fonts.ready.then(() => {
            document.body.classList.add('fonts-loaded');
        });
    }
    
    /**
     * 느린 리소스 최적화
     */
    optimizeSlowResource(entry) {
        const resourceUrl = new URL(entry.name);
        
        // 이미지 최적화
        if (entry.name.match(/\.(png|jpg|jpeg)$/)) {
            this.optimizeImage(entry.name);
        }
        
        // JavaScript 최적화
        if (entry.name.match(/\.js$/)) {
            this.optimizeJavaScript(entry.name);
        }
        
        // CSS 최적화
        if (entry.name.match(/\.css$/)) {
            this.optimizeCSS(entry.name);
        }
    }
    
    /**
     * 이미지 최적화 권장사항
     */
    optimizeImage(imageUrl) {
        console.warn(`[PWA-Optimizer] Image optimization needed: ${imageUrl}`);
        
        // 최적화 권장사항 저장
        const recommendations = {
            url: imageUrl,
            suggestions: [
                'Convert to WebP format',
                'Add responsive srcset',
                'Implement lazy loading',
                'Optimize compression'
            ],
            timestamp: Date.now()
        };
        
        this.saveOptimizationRecommendation('image', recommendations);
    }
    
    /**
     * JavaScript 최적화 권장사항
     */
    optimizeJavaScript(jsUrl) {
        console.warn(`[PWA-Optimizer] JavaScript optimization needed: ${jsUrl}`);
        
        const recommendations = {
            url: jsUrl,
            suggestions: [
                'Enable code splitting',
                'Remove unused code',
                'Minify and compress',
                'Use dynamic imports'
            ],
            timestamp: Date.now()
        };
        
        this.saveOptimizationRecommendation('javascript', recommendations);
    }
    
    /**
     * CSS 최적화 권장사항
     */
    optimizeCSS(cssUrl) {
        console.warn(`[PWA-Optimizer] CSS optimization needed: ${cssUrl}`);
        
        const recommendations = {
            url: cssUrl,
            suggestions: [
                'Remove unused CSS',
                'Critical CSS inlining',
                'Minify and compress',
                'Use CSS containment'
            ],
            timestamp: Date.now()
        };
        
        this.saveOptimizationRecommendation('css', recommendations);
    }
    
    /**
     * 최적화 권장사항 저장
     */
    saveOptimizationRecommendation(type, recommendation) {
        const key = `optimization_${type}_${Date.now()}`;
        
        try {
            localStorage.setItem(key, JSON.stringify(recommendation));
        } catch (error) {
            console.warn('[PWA-Optimizer] Failed to save optimization recommendation:', error);
        }
    }
    
    /**
     * 성능 통계 조회
     */
    getPerformanceStats() {
        return {
            version: this.version,
            isInitialized: this.isInitialized,
            metrics: this.performanceMetrics,
            networkInfo: this.networkInfo,
            deviceInfo: this.deviceInfo,
            criticalResources: Array.from(this.criticalResources),
            resourceLoadTimes: Object.fromEntries(this.resourceLoadTimes),
            config: this.config
        };
    }
    
    /**
     * 최적화 상태 리포트
     */
    generateOptimizationReport() {
        const report = {
            timestamp: Date.now(),
            performance: this.getPerformanceStats(),
            recommendations: this.getOptimizationRecommendations(),
            coreWebVitals: this.getCoreWebVitalsScore(),
            lighthouse: this.estimateLighthouseScore()
        };
        
        console.log('[PWA-Optimizer] Optimization Report:', report);
        return report;
    }
    
    /**
     * 최적화 권장사항 조회
     */
    getOptimizationRecommendations() {
        const recommendations = [];
        
        // LocalStorage에서 저장된 권장사항 조회
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.startsWith('optimization_')) {
                try {
                    const recommendation = JSON.parse(localStorage.getItem(key));
                    recommendations.push(recommendation);
                } catch (error) {
                    console.warn('[PWA-Optimizer] Failed to parse recommendation:', error);
                }
            }
        }
        
        return recommendations.sort((a, b) => b.timestamp - a.timestamp);
    }
    
    /**
     * Core Web Vitals 점수 계산
     */
    getCoreWebVitalsScore() {
        const lcp = this.performanceMetrics.lcp || 0;
        const fid = this.performanceMetrics.fid || 0;
        const cls = this.performanceMetrics.cls || 0;
        
        // 점수 계산 (0-100)
        const lcpScore = lcp < 2500 ? 100 : Math.max(0, 100 - ((lcp - 2500) / 25));
        const fidScore = fid < 100 ? 100 : Math.max(0, 100 - (fid - 100));
        const clsScore = cls < 0.1 ? 100 : Math.max(0, 100 - ((cls - 0.1) * 1000));
        
        return {
            lcp: { value: lcp, score: Math.round(lcpScore) },
            fid: { value: fid, score: Math.round(fidScore) },
            cls: { value: cls, score: Math.round(clsScore) },
            overall: Math.round((lcpScore + fidScore + clsScore) / 3)
        };
    }
    
    /**
     * Lighthouse 점수 추정
     */
    estimateLighthouseScore() {
        const coreWebVitals = this.getCoreWebVitalsScore();
        const resourceCount = this.resourceLoadTimes.size;
        const criticalResourcesOptimized = this.criticalResources.size > 0;
        
        // 기본 점수에서 시작
        let score = 50;
        
        // Core Web Vitals 기반 점수 조정
        score += (coreWebVitals.overall * 0.4);
        
        // 리소스 최적화 상태 반영
        if (criticalResourcesOptimized) score += 10;
        if (resourceCount < 20) score += 10;
        if (this.config.resourceOptimization.enableLazyLoading) score += 5;
        if (this.config.resourceOptimization.enableImageOptimization) score += 5;
        
        // 네트워크 적응 반영
        if (this.config.adaptiveLoading.enableNetworkAdaptation) score += 5;
        
        return Math.min(100, Math.round(score));
    }
}

// 전역 인스턴스 생성 및 내보내기
if (typeof window !== 'undefined') {
    window.PWAPerformanceOptimizer = PWAPerformanceOptimizer;
    
    // 자동 초기화 (옵션)
    document.addEventListener('DOMContentLoaded', () => {
        if (!window.pwaOptimizer) {
            window.pwaOptimizer = new PWAPerformanceOptimizer();
        }
    });
}

export default PWAPerformanceOptimizer;