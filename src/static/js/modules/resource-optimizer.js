/**
 * OneSquare 리소스 최적화 시스템
 * 
 * 지연 로딩, 예측 캐싱, 이미지 최적화, 중요 경로 최적화
 */

class ResourceOptimizer {
    constructor(config = {}) {
        this.config = {
            enableLazyLoading: config.enableLazyLoading !== false,
            enablePredictiveCaching: config.enablePredictiveCaching !== false,
            enableImageOptimization: config.enableImageOptimization !== false,
            lazyThreshold: config.lazyThreshold || '100px',
            prefetchThreshold: config.prefetchThreshold || 0.7, // 70% 확률 이상
            maxPrefetchRequests: config.maxPrefetchRequests || 3,
            imageQuality: config.imageQuality || 85,
            ...config
        };

        this.observers = new Map();
        this.prefetchQueue = [];
        this.loadingResources = new Set();
        this.userPatterns = new Map();
        this.criticalResources = new Set();
        
        this.init();
    }

    /**
     * 리소스 최적화 시스템 초기화
     */
    async init() {
        console.log('[ResourceOptimizer] Initializing resource optimizer...');

        try {
            // Critical Resource Path 최적화
            this.optimizeCriticalPath();
            
            // 지연 로딩 초기화
            if (this.config.enableLazyLoading) {
                this.initLazyLoading();
            }
            
            // 예측 캐싱 초기화
            if (this.config.enablePredictiveCaching) {
                this.initPredictiveCaching();
            }
            
            // 이미지 최적화 초기화
            if (this.config.enableImageOptimization) {
                this.initImageOptimization();
            }
            
            // 사용자 패턴 분석 시작
            this.startUserPatternAnalysis();
            
            // 리소스 힌트 최적화
            this.optimizeResourceHints();
            
            // 폰트 최적화
            this.optimizeFonts();
            
            console.log('[ResourceOptimizer] Resource optimizer initialized');
            
        } catch (error) {
            console.error('[ResourceOptimizer] Initialization failed:', error);
        }
    }

    /**
     * 크리티컬 패스 최적화
     */
    optimizeCriticalPath() {
        // 크리티컬 CSS 인라인화 (이미 인라인된 경우 스킵)
        this.inlineCriticalCSS();
        
        // 크리티컬 JavaScript 우선 로딩
        this.prioritizeCriticalJS();
        
        // Above-the-fold 콘텐츠 우선순위 설정
        this.prioritizeAboveFoldContent();
    }

    /**
     * 크리티컬 CSS 인라인화
     */
    async inlineCriticalCSS() {
        const criticalCSS = [
            '/static/css/common.css'
        ];

        for (const cssPath of criticalCSS) {
            try {
                // 이미 인라인된 CSS 확인
                if (document.querySelector(`style[data-inline-css="${cssPath}"]`)) {
                    continue;
                }

                const response = await fetch(cssPath);
                if (response.ok) {
                    const cssContent = await response.text();
                    
                    // Above-the-fold에 필요한 CSS만 추출 (간단한 구현)
                    const criticalRules = this.extractCriticalCSS(cssContent);
                    
                    if (criticalRules.length > 0) {
                        const style = document.createElement('style');
                        style.setAttribute('data-inline-css', cssPath);
                        style.textContent = criticalRules;
                        document.head.appendChild(style);
                        
                        // 원본 CSS를 지연 로딩으로 전환
                        const link = document.querySelector(`link[href="${cssPath}"]`);
                        if (link) {
                            link.setAttribute('media', 'print');
                            link.onload = function() {
                                this.media = 'all';
                            };
                        }
                        
                        console.log(`[ResourceOptimizer] Inlined critical CSS: ${cssPath}`);
                    }
                }
            } catch (error) {
                console.warn(`[ResourceOptimizer] Failed to inline CSS ${cssPath}:`, error);
            }
        }
    }

    /**
     * 크리티컬 CSS 추출 (간단한 구현)
     */
    extractCriticalCSS(cssContent) {
        const criticalSelectors = [
            'body', 'html', '.container', '.navbar', '.dashboard',
            '.widget', '.card', '.btn', '.alert', '.spinner'
        ];
        
        const rules = cssContent.split('}');
        const criticalRules = [];
        
        for (const rule of rules) {
            if (criticalSelectors.some(selector => rule.includes(selector))) {
                criticalRules.push(rule + '}');
            }
        }
        
        return criticalRules.join('\n');
    }

    /**
     * 크리티컬 JavaScript 우선순위 설정
     */
    prioritizeCriticalJS() {
        const criticalScripts = [
            '/static/js/common.js',
            '/static/js/pwa-manager.js'
        ];

        criticalScripts.forEach(scriptSrc => {
            const script = document.querySelector(`script[src="${scriptSrc}"]`);
            if (script) {
                // 높은 우선순위 설정 (Chrome 지원)
                script.setAttribute('fetchpriority', 'high');
                this.criticalResources.add(scriptSrc);
            }
        });
    }

    /**
     * Above-the-fold 콘텐츠 우선순위 설정
     */
    prioritizeAboveFoldContent() {
        // 뷰포트 내 이미지들을 우선 로딩
        const viewportHeight = window.innerHeight;
        const images = document.querySelectorAll('img[src]');
        
        images.forEach(img => {
            const rect = img.getBoundingClientRect();
            if (rect.top < viewportHeight + 100) { // 100px 마진
                img.setAttribute('fetchpriority', 'high');
                img.setAttribute('data-critical', 'true');
            }
        });
    }

    /**
     * 지연 로딩 초기화
     */
    initLazyLoading() {
        // 이미지 지연 로딩
        this.setupLazyImages();
        
        // 위젯 지연 로딩
        this.setupLazyWidgets();
        
        // iframe 지연 로딩
        this.setupLazyIframes();
        
        console.log('[ResourceOptimizer] Lazy loading initialized');
    }

    /**
     * 이미지 지연 로딩 설정
     */
    setupLazyImages() {
        const lazyImages = document.querySelectorAll('img[data-src]');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        this.loadLazyImage(img);
                        imageObserver.unobserve(img);
                    }
                });
            }, {
                root: null,
                rootMargin: this.config.lazyThreshold,
                threshold: 0.1
            });

            lazyImages.forEach(img => {
                imageObserver.observe(img);
            });
            
            this.observers.set('lazyImages', imageObserver);
        } else {
            // Fallback for older browsers
            lazyImages.forEach(img => this.loadLazyImage(img));
        }
    }

    /**
     * 지연 이미지 로드
     */
    async loadLazyImage(img) {
        try {
            img.classList.add('loading');
            
            // WebP 지원 확인 후 최적화된 이미지 로드
            const optimizedSrc = await this.getOptimizedImageSrc(img.dataset.src);
            
            const tempImg = new Image();
            tempImg.onload = () => {
                img.src = optimizedSrc;
                img.classList.remove('loading');
                img.classList.add('loaded');
                img.removeAttribute('data-src');
            };
            tempImg.onerror = () => {
                img.src = img.dataset.src; // 원본으로 폴백
                img.classList.remove('loading');
                img.classList.add('error');
            };
            tempImg.src = optimizedSrc;
            
        } catch (error) {
            console.warn('[ResourceOptimizer] Failed to load lazy image:', error);
            img.src = img.dataset.src;
            img.classList.remove('loading');
        }
    }

    /**
     * 위젯 지연 로딩 설정
     */
    setupLazyWidgets() {
        const lazyWidgets = document.querySelectorAll('[data-widget-lazy="true"]');
        
        if ('IntersectionObserver' in window && lazyWidgets.length > 0) {
            const widgetObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const widget = entry.target;
                        this.loadLazyWidget(widget);
                        widgetObserver.unobserve(widget);
                    }
                });
            }, {
                rootMargin: '50px'
            });

            lazyWidgets.forEach(widget => {
                widgetObserver.observe(widget);
            });
            
            this.observers.set('lazyWidgets', widgetObserver);
        }
    }

    /**
     * 지연 위젯 로드
     */
    async loadLazyWidget(widget) {
        try {
            const widgetId = widget.dataset.widgetId;
            const widgetType = widget.dataset.widgetType;
            
            widget.innerHTML = '<div class="widget-loading">로딩 중...</div>';
            
            // 위젯 데이터 로드
            if (window.dashboard && window.dashboard.loadWidgetData) {
                await window.dashboard.loadWidgetData(widgetId, false);
            }
            
            widget.setAttribute('data-loaded', 'true');
            console.log(`[ResourceOptimizer] Lazy widget loaded: ${widgetId}`);
            
        } catch (error) {
            console.error('[ResourceOptimizer] Failed to load lazy widget:', error);
            widget.innerHTML = '<div class="widget-error">로딩 실패</div>';
        }
    }

    /**
     * iframe 지연 로딩 설정
     */
    setupLazyIframes() {
        const lazyIframes = document.querySelectorAll('iframe[data-src]');
        
        if ('IntersectionObserver' in window && lazyIframes.length > 0) {
            const iframeObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const iframe = entry.target;
                        iframe.src = iframe.dataset.src;
                        iframe.removeAttribute('data-src');
                        iframeObserver.unobserve(iframe);
                    }
                });
            });

            lazyIframes.forEach(iframe => {
                iframeObserver.observe(iframe);
            });
            
            this.observers.set('lazyIframes', iframeObserver);
        }
    }

    /**
     * 예측 캐싱 초기화
     */
    initPredictiveCaching() {
        // 링크 호버 시 프리페치
        this.setupHoverPrefetch();
        
        // 사용자 패턴 기반 예측 캐싱
        this.setupPatternBasedPrefetch();
        
        // 네트워크 유휴 시간 활용
        this.setupIdlePrefetch();
        
        console.log('[ResourceOptimizer] Predictive caching initialized');
    }

    /**
     * 호버 프리페치 설정
     */
    setupHoverPrefetch() {
        let prefetchTimer = null;
        
        document.addEventListener('mouseover', (event) => {
            const link = event.target.closest('a[href]');
            if (link && this.shouldPrefetchLink(link)) {
                prefetchTimer = setTimeout(() => {
                    this.prefetchResource(link.href, 'hover');
                }, 65); // 65ms 지연 (의도적인 호버 감지)
            }
        });
        
        document.addEventListener('mouseout', () => {
            if (prefetchTimer) {
                clearTimeout(prefetchTimer);
                prefetchTimer = null;
            }
        });
    }

    /**
     * 패턴 기반 프리페치 설정
     */
    setupPatternBasedPrefetch() {
        // 페이지 방문 패턴 분석 후 다음 페이지 예측
        const currentPath = location.pathname;
        const patterns = this.getUserPatterns();
        
        const predictedPaths = patterns.get(currentPath);
        if (predictedPaths) {
            predictedPaths.forEach((probability, path) => {
                if (probability >= this.config.prefetchThreshold) {
                    this.scheduleDelayedPrefetch(path, 'pattern');
                }
            });
        }
    }

    /**
     * 유휴 시간 프리페치 설정
     */
    setupIdlePrefetch() {
        if ('requestIdleCallback' in window) {
            requestIdleCallback(() => {
                this.processPrefetchQueue();
            });
        } else {
            // Fallback
            setTimeout(() => {
                this.processPrefetchQueue();
            }, 2000);
        }
    }

    /**
     * 프리페치 대상 판단
     */
    shouldPrefetchLink(link) {
        const href = link.href;
        
        // 같은 도메인만 프리페치
        if (!href.startsWith(location.origin)) {
            return false;
        }
        
        // 이미 캐시된 리소스는 스킵
        if (this.loadingResources.has(href)) {
            return false;
        }
        
        // 파일 다운로드 링크는 스킵
        if (href.match(/\.(pdf|zip|exe|dmg)$/i)) {
            return false;
        }
        
        return true;
    }

    /**
     * 리소스 프리페치
     */
    async prefetchResource(url, reason = 'unknown') {
        if (this.loadingResources.has(url)) {
            return;
        }
        
        this.loadingResources.add(url);
        
        try {
            const link = document.createElement('link');
            link.rel = 'prefetch';
            link.href = url;
            link.setAttribute('data-prefetch-reason', reason);
            
            document.head.appendChild(link);
            
            console.log(`[ResourceOptimizer] Prefetched: ${url} (${reason})`);
            
            // 성공 후 일정 시간 후 제거
            setTimeout(() => {
                if (link.parentNode) {
                    link.remove();
                }
                this.loadingResources.delete(url);
            }, 30000);
            
        } catch (error) {
            console.warn(`[ResourceOptimizer] Prefetch failed: ${url}`, error);
            this.loadingResources.delete(url);
        }
    }

    /**
     * 지연된 프리페치 스케줄링
     */
    scheduleDelayedPrefetch(url, reason) {
        this.prefetchQueue.push({ url, reason, timestamp: Date.now() });
        
        // 큐 크기 제한
        if (this.prefetchQueue.length > this.config.maxPrefetchRequests) {
            this.prefetchQueue.shift();
        }
    }

    /**
     * 프리페치 큐 처리
     */
    async processPrefetchQueue() {
        while (this.prefetchQueue.length > 0 && this.loadingResources.size < this.config.maxPrefetchRequests) {
            const item = this.prefetchQueue.shift();
            await this.prefetchResource(item.url, item.reason);
            
            // 요청 간 간격 두기 (서버 부하 방지)
            await this.sleep(500);
        }
    }

    /**
     * 이미지 최적화 초기화
     */
    initImageOptimization() {
        // 기존 이미지 최적화
        this.optimizeExistingImages();
        
        // 새로 추가되는 이미지 최적화
        this.observeNewImages();
        
        // WebP 지원 확인 및 전환
        this.setupWebPSupport();
        
        console.log('[ResourceOptimizer] Image optimization initialized');
    }

    /**
     * 기존 이미지 최적화
     */
    optimizeExistingImages() {
        const images = document.querySelectorAll('img[src]:not([data-optimized])');
        
        images.forEach(async (img) => {
            await this.optimizeImage(img);
        });
    }

    /**
     * 새 이미지 관찰
     */
    observeNewImages() {
        if ('MutationObserver' in window) {
            const imageObserver = new MutationObserver((mutations) => {
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            const images = node.tagName === 'IMG' ? [node] : node.querySelectorAll('img');
                            images.forEach(img => this.optimizeImage(img));
                        }
                    });
                });
            });
            
            imageObserver.observe(document.body, {
                childList: true,
                subtree: true
            });
            
            this.observers.set('newImages', imageObserver);
        }
    }

    /**
     * 이미지 최적화
     */
    async optimizeImage(img) {
        if (img.getAttribute('data-optimized')) return;
        
        try {
            // 원본 이미지 정보 수집
            const originalSrc = img.src || img.dataset.src;
            if (!originalSrc) return;
            
            // 최적화된 이미지 URL 생성
            const optimizedSrc = await this.getOptimizedImageSrc(originalSrc);
            
            if (optimizedSrc !== originalSrc) {
                // 최적화된 이미지로 교체
                if (img.src) {
                    img.src = optimizedSrc;
                } else {
                    img.dataset.src = optimizedSrc;
                }
            }
            
            // 레이지 로딩 속성 추가 (viewport 밖의 이미지)
            if (!img.getAttribute('data-critical')) {
                const rect = img.getBoundingClientRect();
                if (rect.top > window.innerHeight + 100) {
                    img.setAttribute('loading', 'lazy');
                }
            }
            
            img.setAttribute('data-optimized', 'true');
            
        } catch (error) {
            console.warn('[ResourceOptimizer] Image optimization failed:', error);
        }
    }

    /**
     * 최적화된 이미지 소스 생성
     */
    async getOptimizedImageSrc(originalSrc) {
        // WebP 지원 확인
        const supportsWebP = await this.checkWebPSupport();
        
        if (supportsWebP && !originalSrc.endsWith('.webp')) {
            // WebP 버전 URL 생성
            const webpSrc = originalSrc.replace(/\.(jpg|jpeg|png)$/i, '.webp');
            
            // WebP 버전 존재 확인
            if (await this.checkImageExists(webpSrc)) {
                return webpSrc;
            }
        }
        
        // 품질 파라미터 추가
        if (originalSrc.includes('?')) {
            return `${originalSrc}&q=${this.config.imageQuality}`;
        } else {
            return `${originalSrc}?q=${this.config.imageQuality}`;
        }
    }

    /**
     * WebP 지원 확인
     */
    checkWebPSupport() {
        return new Promise((resolve) => {
            const webP = new Image();
            webP.onload = webP.onerror = () => {
                resolve(webP.height === 2);
            };
            webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
        });
    }

    /**
     * 이미지 존재 확인
     */
    checkImageExists(src) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => resolve(true);
            img.onerror = () => resolve(false);
            img.src = src;
        });
    }

    /**
     * WebP 지원 설정
     */
    setupWebPSupport() {
        this.checkWebPSupport().then(supported => {
            if (supported) {
                document.documentElement.classList.add('webp');
                console.log('[ResourceOptimizer] WebP support enabled');
            } else {
                document.documentElement.classList.add('no-webp');
            }
        });
    }

    /**
     * 사용자 패턴 분석 시작
     */
    startUserPatternAnalysis() {
        // 페이지 방문 기록
        this.recordPageVisit();
        
        // 클릭 패턴 분석
        this.analyzeClickPatterns();
        
        // 스크롤 패턴 분석
        this.analyzeScrollPatterns();
    }

    /**
     * 페이지 방문 기록
     */
    recordPageVisit() {
        const currentPath = location.pathname;
        const timestamp = Date.now();
        
        // localStorage에서 방문 기록 가져오기
        const visits = JSON.parse(localStorage.getItem('page_visits') || '[]');
        
        // 새 방문 추가
        visits.push({ path: currentPath, timestamp });
        
        // 최근 100개만 유지
        if (visits.length > 100) {
            visits.splice(0, visits.length - 100);
        }
        
        localStorage.setItem('page_visits', JSON.stringify(visits));
        
        // 패턴 분석 업데이트
        this.updateNavigationPatterns(visits);
    }

    /**
     * 네비게이션 패턴 업데이트
     */
    updateNavigationPatterns(visits) {
        const patterns = new Map();
        
        for (let i = 0; i < visits.length - 1; i++) {
            const current = visits[i].path;
            const next = visits[i + 1].path;
            
            if (!patterns.has(current)) {
                patterns.set(current, new Map());
            }
            
            const nextPages = patterns.get(current);
            const count = nextPages.get(next) || 0;
            nextPages.set(next, count + 1);
        }
        
        // 확률로 변환
        patterns.forEach((nextPages, currentPage) => {
            const total = Array.from(nextPages.values()).reduce((a, b) => a + b, 0);
            nextPages.forEach((count, nextPage) => {
                nextPages.set(nextPage, count / total);
            });
        });
        
        this.userPatterns = patterns;
    }

    /**
     * 클릭 패턴 분석
     */
    analyzeClickPatterns() {
        document.addEventListener('click', (event) => {
            const target = event.target.closest('a[href]');
            if (target) {
                // 클릭된 링크의 특성 분석
                this.recordLinkClick(target);
            }
        });
    }

    /**
     * 링크 클릭 기록
     */
    recordLinkClick(link) {
        const linkData = {
            href: link.href,
            text: link.textContent.trim(),
            className: link.className,
            timestamp: Date.now()
        };
        
        const clicks = JSON.parse(localStorage.getItem('link_clicks') || '[]');
        clicks.push(linkData);
        
        // 최근 50개만 유지
        if (clicks.length > 50) {
            clicks.splice(0, clicks.length - 50);
        }
        
        localStorage.setItem('link_clicks', JSON.stringify(clicks));
    }

    /**
     * 스크롤 패턴 분석
     */
    analyzeScrollPatterns() {
        let scrollTimer = null;
        let maxScroll = 0;
        
        window.addEventListener('scroll', () => {
            const scrollPercent = window.scrollY / (document.body.scrollHeight - window.innerHeight);
            maxScroll = Math.max(maxScroll, scrollPercent);
            
            // 스크롤 정지 후 패턴 기록
            clearTimeout(scrollTimer);
            scrollTimer = setTimeout(() => {
                this.recordScrollPattern(maxScroll);
            }, 1000);
        });
    }

    /**
     * 스크롤 패턴 기록
     */
    recordScrollPattern(scrollPercent) {
        const patterns = JSON.parse(localStorage.getItem('scroll_patterns') || '[]');
        patterns.push({
            path: location.pathname,
            maxScroll: scrollPercent,
            timestamp: Date.now()
        });
        
        // 최근 30개만 유지
        if (patterns.length > 30) {
            patterns.splice(0, patterns.length - 30);
        }
        
        localStorage.setItem('scroll_patterns', JSON.stringify(patterns));
    }

    /**
     * 리소스 힌트 최적화
     */
    optimizeResourceHints() {
        // DNS prefetch 추가
        this.addDnsPrefetch([
            'fonts.googleapis.com',
            'cdnjs.cloudflare.com'
        ]);
        
        // Preconnect 추가
        this.addPreconnect([
            'https://fonts.gstatic.com'
        ]);
        
        console.log('[ResourceOptimizer] Resource hints optimized');
    }

    /**
     * DNS prefetch 추가
     */
    addDnsPrefetch(domains) {
        domains.forEach(domain => {
            if (!document.querySelector(`link[rel="dns-prefetch"][href*="${domain}"]`)) {
                const link = document.createElement('link');
                link.rel = 'dns-prefetch';
                link.href = `//${domain}`;
                document.head.appendChild(link);
            }
        });
    }

    /**
     * Preconnect 추가
     */
    addPreconnect(urls) {
        urls.forEach(url => {
            if (!document.querySelector(`link[rel="preconnect"][href="${url}"]`)) {
                const link = document.createElement('link');
                link.rel = 'preconnect';
                link.href = url;
                link.crossOrigin = 'anonymous';
                document.head.appendChild(link);
            }
        });
    }

    /**
     * 폰트 최적화
     */
    optimizeFonts() {
        // 폰트 display swap 설정
        const fontLinks = document.querySelectorAll('link[href*="fonts"]');
        fontLinks.forEach(link => {
            if (!link.href.includes('display=swap')) {
                link.href += link.href.includes('?') ? '&display=swap' : '?display=swap';
            }
        });
        
        console.log('[ResourceOptimizer] Font optimization applied');
    }

    /**
     * 사용자 패턴 조회
     */
    getUserPatterns() {
        return this.userPatterns;
    }

    /**
     * 최적화 통계 조회
     */
    getOptimizationStats() {
        return {
            observersActive: this.observers.size,
            prefetchQueueSize: this.prefetchQueue.length,
            loadingResources: this.loadingResources.size,
            userPatternsCount: this.userPatterns.size,
            criticalResourcesCount: this.criticalResources.size,
            config: this.config
        };
    }

    /**
     * 유틸리티: 슬립
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
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
        
        // 큐 정리
        this.prefetchQueue.length = 0;
        this.loadingResources.clear();
        this.userPatterns.clear();
        this.criticalResources.clear();
        
        console.log('[ResourceOptimizer] Resource optimizer destroyed');
    }
}

// 전역으로 내보내기
window.ResourceOptimizer = ResourceOptimizer;

// 자동 초기화
window.addEventListener('DOMContentLoaded', () => {
    window.resourceOptimizer = new ResourceOptimizer({
        enableLazyLoading: true,
        enablePredictiveCaching: true,
        enableImageOptimization: true
    });
});