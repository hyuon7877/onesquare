/**
 * OneSquare 대시보드 성능 최적화 시스템
 * 
 * 위젯 최적화, 렌더링 최적화, 메모리 관리, 로딩 전략 통합
 * 목표: 3초 이내 대시보드 완전 로딩
 */

class DashboardPerformanceOptimizer {
    constructor(config = {}) {
        this.config = {
            targetLoadTime: config.targetLoadTime || 3000, // 3초
            widgetLoadBudget: config.widgetLoadBudget || 500, // 위젯당 500ms
            criticalWidgets: config.criticalWidgets || ['stats-overview', 'notifications'],
            enableProgressiveLoading: config.enableProgressiveLoading !== false,
            enableWidgetPrioritization: config.enableWidgetPrioritization !== false,
            enableMemoryOptimization: config.enableMemoryOptimization !== false,
            maxConcurrentWidgets: config.maxConcurrentWidgets || 3,
            ...config
        };

        this.loadingQueue = [];
        this.loadedWidgets = new Set();
        this.loadingWidgets = new Set();
        this.widgetMetrics = new Map();
        this.renderQueue = [];
        this.isOptimizing = false;
        
        this.performanceBudget = {
            totalLoadTime: this.config.targetLoadTime,
            criticalPath: this.config.targetLoadTime * 0.4, // 40%를 크리티컬 패스에 할당
            widgetLoading: this.config.targetLoadTime * 0.5, // 50%를 위젯 로딩에 할당
            rendering: this.config.targetLoadTime * 0.1     // 10%를 렌더링에 할당
        };
        
        this.init();
    }

    /**
     * 대시보드 성능 최적화 초기화
     */
    async init() {
        console.log('[DashboardOptimizer] Initializing dashboard performance optimizer...');

        try {
            // 성능 모니터링 시작
            this.startPerformanceMonitoring();
            
            // 위젯 우선순위 시스템 초기화
            this.initWidgetPrioritization();
            
            // 프로그레시브 로딩 설정
            if (this.config.enableProgressiveLoading) {
                this.initProgressiveLoading();
            }
            
            // 메모리 최적화 설정
            if (this.config.enableMemoryOptimization) {
                this.initMemoryOptimization();
            }
            
            // 렌더링 최적화 설정
            this.initRenderingOptimization();
            
            // 이벤트 리스너 설정
            this.setupEventListeners();
            
            // 자동 최적화 트리거 설정
            this.setupAutoOptimization();
            
            console.log('[DashboardOptimizer] Dashboard performance optimizer initialized');
            
        } catch (error) {
            console.error('[DashboardOptimizer] Initialization failed:', error);
        }
    }

    /**
     * 성능 모니터링 시작
     */
    startPerformanceMonitoring() {
        this.dashboardStartTime = performance.now();
        this.loadingMetrics = {
            startTime: this.dashboardStartTime,
            firstWidgetTime: null,
            criticalWidgetsTime: null,
            allWidgetsTime: null,
            renderingTime: null
        };

        // Performance Observer 설정
        if ('PerformanceObserver' in window) {
            this.setupPerformanceObservers();
        }
    }

    /**
     * Performance Observer 설정
     */
    setupPerformanceObservers() {
        try {
            // Long Task 감지
            const longTaskObserver = new PerformanceObserver((entryList) => {
                entryList.getEntries().forEach(entry => {
                    console.warn('[DashboardOptimizer] Long task detected:', {
                        duration: entry.duration,
                        startTime: entry.startTime,
                        name: entry.name
                    });
                    
                    // Long Task가 발생하면 최적화 트리거
                    this.handleLongTask(entry);
                });
            });
            longTaskObserver.observe({ entryTypes: ['longtask'] });

            // Layout Shift 감지
            const layoutShiftObserver = new PerformanceObserver((entryList) => {
                entryList.getEntries().forEach(entry => {
                    if (entry.value > 0.1) { // CLS 임계값
                        console.warn('[DashboardOptimizer] Layout shift detected:', entry.value);
                        this.handleLayoutShift(entry);
                    }
                });
            });
            layoutShiftObserver.observe({ entryTypes: ['layout-shift'] });
            
        } catch (error) {
            console.warn('[DashboardOptimizer] Performance observers setup failed:', error);
        }
    }

    /**
     * 위젯 우선순위 시스템 초기화
     */
    initWidgetPrioritization() {
        // 모든 위젯을 우선순위별로 분류
        const widgets = document.querySelectorAll('[data-widget-id]');
        const priorityQueues = {
            critical: [],
            high: [],
            normal: [],
            low: []
        };

        widgets.forEach(widget => {
            const widgetId = widget.dataset.widgetId;
            const priority = this.getWidgetPriority(widgetId, widget);
            
            widget.setAttribute('data-priority', priority);
            priorityQueues[priority].push({
                element: widget,
                id: widgetId,
                priority: priority
            });
        });

        // 로딩 큐 설정 (우선순위 순)
        this.loadingQueue = [
            ...priorityQueues.critical,
            ...priorityQueues.high,
            ...priorityQueues.normal,
            ...priorityQueues.low
        ];

        console.log('[DashboardOptimizer] Widget prioritization:', {
            critical: priorityQueues.critical.length,
            high: priorityQueues.high.length,
            normal: priorityQueues.normal.length,
            low: priorityQueues.low.length
        });
    }

    /**
     * 위젯 우선순위 결정
     */
    getWidgetPriority(widgetId, element) {
        // Critical 위젯 (즉시 로딩 필요)
        if (this.config.criticalWidgets.includes(widgetId)) {
            return 'critical';
        }
        
        // Above-the-fold 위젯은 high 우선순위
        if (this.isAboveFold(element)) {
            return 'high';
        }
        
        // 데이터 소스별 우선순위
        const dataSource = element.dataset.dataSource;
        if (dataSource === 'realtime' || dataSource === 'notifications') {
            return 'high';
        }
        
        // 사용자 상호작용이 많은 위젯
        const widgetType = element.dataset.widgetType;
        if (['button', 'form', 'interactive'].includes(widgetType)) {
            return 'high';
        }
        
        // 리포트나 분석 위젯은 낮은 우선순위
        if (['analytics', 'report', 'chart'].includes(widgetType)) {
            return 'low';
        }
        
        return 'normal';
    }

    /**
     * Above-the-fold 확인
     */
    isAboveFold(element) {
        const rect = element.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        
        return rect.top < viewportHeight && rect.bottom > 0;
    }

    /**
     * 프로그레시브 로딩 초기화
     */
    initProgressiveLoading() {
        // 크리티컬 위젯 우선 로딩
        this.loadCriticalWidgets();
        
        // 나머지 위젯들 순차 로딩
        requestIdleCallback(() => {
            this.loadRemainingWidgets();
        });
        
        // Intersection Observer로 지연 로딩
        this.setupLazyWidgetLoading();
    }

    /**
     * 크리티컬 위젯 로딩
     */
    async loadCriticalWidgets() {
        const criticalWidgets = this.loadingQueue.filter(w => w.priority === 'critical');
        
        if (criticalWidgets.length === 0) {
            this.loadingMetrics.criticalWidgetsTime = performance.now();
            return;
        }

        console.log('[DashboardOptimizer] Loading critical widgets:', criticalWidgets.length);
        
        const startTime = performance.now();
        const loadPromises = criticalWidgets.map(widget => this.loadWidget(widget));
        
        try {
            await Promise.all(loadPromises);
            
            this.loadingMetrics.criticalWidgetsTime = performance.now();
            const loadTime = this.loadingMetrics.criticalWidgetsTime - startTime;
            
            console.log(`[DashboardOptimizer] Critical widgets loaded in ${loadTime.toFixed(2)}ms`);
            
            // 크리티컬 위젯 로딩이 예산을 초과했는지 확인
            if (loadTime > this.performanceBudget.criticalPath) {
                console.warn('[DashboardOptimizer] Critical widgets exceeded budget');
                this.triggerCriticalPathOptimization();
            }
            
        } catch (error) {
            console.error('[DashboardOptimizer] Critical widgets loading failed:', error);
        }
    }

    /**
     * 나머지 위젯 로딩
     */
    async loadRemainingWidgets() {
        const remainingWidgets = this.loadingQueue.filter(w => 
            w.priority !== 'critical' && !this.loadedWidgets.has(w.id)
        );

        console.log('[DashboardOptimizer] Loading remaining widgets:', remainingWidgets.length);
        
        // 배치 로딩 (동시에 최대 maxConcurrentWidgets개만)
        for (let i = 0; i < remainingWidgets.length; i += this.config.maxConcurrentWidgets) {
            const batch = remainingWidgets.slice(i, i + this.config.maxConcurrentWidgets);
            
            const loadPromises = batch.map(widget => this.loadWidget(widget));
            
            try {
                await Promise.allSettled(loadPromises);
                
                // 배치 간 짧은 지연 (UI 블로킹 방지)
                if (i + this.config.maxConcurrentWidgets < remainingWidgets.length) {
                    await this.sleep(50);
                }
                
            } catch (error) {
                console.error('[DashboardOptimizer] Batch loading failed:', error);
            }
        }
        
        this.loadingMetrics.allWidgetsTime = performance.now();
        this.checkLoadingComplete();
    }

    /**
     * 개별 위젯 로딩
     */
    async loadWidget(widgetConfig) {
        const { element, id, priority } = widgetConfig;
        
        if (this.loadedWidgets.has(id) || this.loadingWidgets.has(id)) {
            return;
        }

        this.loadingWidgets.add(id);
        const startTime = performance.now();

        try {
            // 위젯별 로딩 예산 체크
            const budget = this.getWidgetLoadingBudget(priority);
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('Widget loading timeout')), budget);
            });

            // 실제 위젯 로딩 로직
            const loadPromise = this.executeWidgetLoading(element, id);
            
            // 타임아웃과 경쟁
            await Promise.race([loadPromise, timeoutPromise]);
            
            const loadTime = performance.now() - startTime;
            this.recordWidgetMetric(id, 'loadTime', loadTime);
            
            this.loadedWidgets.add(id);
            this.loadingWidgets.delete(id);
            
            element.setAttribute('data-loaded', 'true');
            element.setAttribute('data-load-time', loadTime.toFixed(2));
            
            // 첫 번째 위젯 로딩 시간 기록
            if (!this.loadingMetrics.firstWidgetTime) {
                this.loadingMetrics.firstWidgetTime = performance.now();
            }
            
            console.log(`[DashboardOptimizer] Widget ${id} loaded in ${loadTime.toFixed(2)}ms`);
            
        } catch (error) {
            console.error(`[DashboardOptimizer] Widget ${id} loading failed:`, error);
            this.handleWidgetLoadingError(element, id, error);
            this.loadingWidgets.delete(id);
        }
    }

    /**
     * 위젯 로딩 실행
     */
    async executeWidgetLoading(element, widgetId) {
        const widgetType = element.dataset.widgetType || 'default';
        const dataSource = element.dataset.dataSource;

        // 로딩 스피너 표시
        this.showWidgetLoading(element);

        // 위젯 타입별 로딩 전략
        switch (widgetType) {
            case 'chart':
                return this.loadChartWidget(element, dataSource);
            case 'stats':
                return this.loadStatsWidget(element, dataSource);
            case 'table':
                return this.loadTableWidget(element, dataSource);
            case 'notifications':
                return this.loadNotificationWidget(element);
            default:
                return this.loadGenericWidget(element, dataSource);
        }
    }

    /**
     * 차트 위젯 로딩
     */
    async loadChartWidget(element, dataSource) {
        try {
            // 차트 데이터 가져오기
            const data = await this.fetchWidgetData(dataSource, 'chart');
            
            // SVG 차트 렌더링 (지연 실행)
            requestAnimationFrame(() => {
                const chart = new SVGCharts(element.id);
                const chartType = element.dataset.chartType || 'bar';
                
                switch (chartType) {
                    case 'pie':
                        chart.createPieChart(data.chartData, data.options);
                        break;
                    case 'line':
                        chart.createLineChart(data.chartData, data.options);
                        break;
                    default:
                        chart.createBarChart(data.chartData, data.options);
                }
            });
            
        } catch (error) {
            throw new Error(`Chart widget loading failed: ${error.message}`);
        }
    }

    /**
     * 통계 위젯 로딩
     */
    async loadStatsWidget(element, dataSource) {
        try {
            const data = await this.fetchWidgetData(dataSource, 'stats');
            
            requestAnimationFrame(() => {
                const chart = new SVGCharts(element.id);
                chart.createStatsCard(data, {
                    title: element.dataset.title || 'Statistics',
                    icon: element.dataset.icon || 'chart-line'
                });
            });
            
        } catch (error) {
            throw new Error(`Stats widget loading failed: ${error.message}`);
        }
    }

    /**
     * 테이블 위젯 로딩
     */
    async loadTableWidget(element, dataSource) {
        try {
            const data = await this.fetchWidgetData(dataSource, 'table');
            
            requestAnimationFrame(() => {
                element.innerHTML = `
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    ${(data.headers || []).map(h => `<th>${h}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${(data.rows || []).map(row => `
                                    <tr>
                                        ${row.map(cell => `<td>${cell}</td>`).join('')}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
            });
            
        } catch (error) {
            throw new Error(`Table widget loading failed: ${error.message}`);
        }
    }

    /**
     * 알림 위젯 로딩
     */
    async loadNotificationWidget(element) {
        try {
            const notifications = await this.fetchNotifications();
            
            requestAnimationFrame(() => {
                element.innerHTML = `
                    <div class="notifications-widget">
                        <h5>최근 알림</h5>
                        <ul class="list-unstyled">
                            ${notifications.map(n => `
                                <li class="notification-item ${n.priority}">
                                    <small class="text-muted">${new Date(n.timestamp).toLocaleString()}</small>
                                    <div>${n.message}</div>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                `;
            });
            
        } catch (error) {
            throw new Error(`Notification widget loading failed: ${error.message}`);
        }
    }

    /**
     * 일반 위젯 로딩
     */
    async loadGenericWidget(element, dataSource) {
        try {
            const data = await this.fetchWidgetData(dataSource, 'generic');
            
            requestAnimationFrame(() => {
                element.innerHTML = `
                    <div class="generic-widget">
                        <h5>${data.title || 'Widget'}</h5>
                        <div class="widget-content">
                            ${data.content || JSON.stringify(data, null, 2)}
                        </div>
                    </div>
                `;
            });
            
        } catch (error) {
            throw new Error(`Generic widget loading failed: ${error.message}`);
        }
    }

    /**
     * 위젯 데이터 가져오기 (캐시 우선)
     */
    async fetchWidgetData(dataSource, widgetType) {
        const cacheKey = `widget-${dataSource}-${widgetType}`;
        
        // 캐시 확인
        const cachedData = this.getFromCache(cacheKey);
        if (cachedData) {
            return cachedData;
        }

        // API 요청
        const response = await fetch(`/api/dashboard/widgets/${dataSource}/`, {
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`API request failed: ${response.status}`);
        }

        const data = await response.json();
        
        // 캐시 저장 (5분 TTL)
        this.saveToCache(cacheKey, data, 5 * 60 * 1000);
        
        return data;
    }

    /**
     * 알림 데이터 가져오기
     */
    async fetchNotifications() {
        const cacheKey = 'notifications';
        const cached = this.getFromCache(cacheKey);
        
        if (cached) {
            return cached;
        }

        const response = await fetch('/api/notifications/', {
            headers: { 'Accept': 'application/json' }
        });

        if (!response.ok) {
            return [];
        }

        const notifications = await response.json();
        this.saveToCache(cacheKey, notifications, 2 * 60 * 1000); // 2분 캐시
        
        return notifications.slice(0, 5); // 최근 5개만
    }

    /**
     * 지연 위젯 로딩 설정
     */
    setupLazyWidgetLoading() {
        const lazyWidgets = document.querySelectorAll('[data-widget-lazy="true"]');
        
        if ('IntersectionObserver' in window && lazyWidgets.length > 0) {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const widgetId = entry.target.dataset.widgetId;
                        
                        if (!this.loadedWidgets.has(widgetId)) {
                            const widgetConfig = {
                                element: entry.target,
                                id: widgetId,
                                priority: 'low'
                            };
                            
                            this.loadWidget(widgetConfig);
                        }
                        
                        observer.unobserve(entry.target);
                    }
                });
            }, {
                rootMargin: '50px'
            });

            lazyWidgets.forEach(widget => {
                observer.observe(widget);
            });
        }
    }

    /**
     * 메모리 최적화 초기화
     */
    initMemoryOptimization() {
        // 주기적 메모리 정리
        setInterval(() => {
            this.performMemoryCleanup();
        }, 5 * 60 * 1000); // 5분마다

        // 페이지 가시성 변경 시 메모리 정리
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.performMemoryCleanup();
            }
        });
    }

    /**
     * 메모리 정리 수행
     */
    performMemoryCleanup() {
        // 캐시 정리
        this.cleanupCache();
        
        // 사용하지 않는 위젯 정리
        this.cleanupUnusedWidgets();
        
        // DOM 정리
        this.cleanupDOM();
        
        console.log('[DashboardOptimizer] Memory cleanup performed');
    }

    /**
     * 렌더링 최적화 초기화
     */
    initRenderingOptimization() {
        // RAF를 사용한 렌더링 큐 설정
        this.setupRenderQueue();
        
        // 레이아웃 쓰래싱 방지
        this.preventLayoutThrashing();
    }

    /**
     * 렌더링 큐 설정
     */
    setupRenderQueue() {
        let rafId = null;
        
        this.scheduleRender = (callback) => {
            this.renderQueue.push(callback);
            
            if (!rafId) {
                rafId = requestAnimationFrame(() => {
                    this.processRenderQueue();
                    rafId = null;
                });
            }
        };
    }

    /**
     * 렌더링 큐 처리
     */
    processRenderQueue() {
        const startTime = performance.now();
        
        while (this.renderQueue.length > 0 && (performance.now() - startTime) < 16) {
            const callback = this.renderQueue.shift();
            try {
                callback();
            } catch (error) {
                console.error('[DashboardOptimizer] Render callback failed:', error);
            }
        }
        
        // 남은 작업이 있으면 다음 프레임에서 계속
        if (this.renderQueue.length > 0) {
            requestAnimationFrame(() => this.processRenderQueue());
        }
    }

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        // 페이지 언로드 시 메트릭 저장
        window.addEventListener('beforeunload', () => {
            this.savePerformanceMetrics();
        });

        // 네트워크 상태 변경 감지
        window.addEventListener('online', () => {
            this.handleNetworkChange(true);
        });

        window.addEventListener('offline', () => {
            this.handleNetworkChange(false);
        });
    }

    /**
     * 자동 최적화 트리거 설정
     */
    setupAutoOptimization() {
        // 페이지 로드 완료 후 최적화 분석
        window.addEventListener('load', () => {
            setTimeout(() => {
                this.analyzeAndOptimize();
            }, 1000);
        });

        // 주기적 성능 체크
        setInterval(() => {
            this.performPerformanceCheck();
        }, 30 * 1000); // 30초마다
    }

    /**
     * Long Task 처리
     */
    handleLongTask(entry) {
        console.warn('[DashboardOptimizer] Long task detected:', entry);
        
        // Long Task가 발생한 경우 위젯 로딩 전략 조정
        this.config.maxConcurrentWidgets = Math.max(1, this.config.maxConcurrentWidgets - 1);
        
        // 다음 위젯 로딩을 지연
        setTimeout(() => {
            if (this.loadingQueue.length > 0) {
                this.loadRemainingWidgets();
            }
        }, 100);
    }

    /**
     * Layout Shift 처리
     */
    handleLayoutShift(entry) {
        console.warn('[DashboardOptimizer] Layout shift detected:', entry);
        
        // 레이아웃 시프트가 발생한 요소들 분석
        entry.sources?.forEach(source => {
            const element = source.node;
            if (element && element.dataset?.widgetId) {
                this.optimizeWidgetLayout(element);
            }
        });
    }

    /**
     * 위젯 레이아웃 최적화
     */
    optimizeWidgetLayout(element) {
        // 고정 높이 설정으로 레이아웃 시프트 방지
        if (!element.style.minHeight) {
            element.style.minHeight = '200px';
        }
        
        // 스켈레톤 로더 추가
        if (!element.querySelector('.skeleton-loader')) {
            this.addSkeletonLoader(element);
        }
    }

    /**
     * 스켈레톤 로더 추가
     */
    addSkeletonLoader(element) {
        const skeleton = document.createElement('div');
        skeleton.className = 'skeleton-loader';
        skeleton.innerHTML = `
            <div class="skeleton-header"></div>
            <div class="skeleton-content">
                <div class="skeleton-line"></div>
                <div class="skeleton-line"></div>
                <div class="skeleton-line"></div>
            </div>
        `;
        
        element.appendChild(skeleton);
    }

    /**
     * 위젯 로딩 예산 계산
     */
    getWidgetLoadingBudget(priority) {
        const budgets = {
            'critical': this.config.widgetLoadBudget * 0.5, // 250ms
            'high': this.config.widgetLoadBudget * 0.8,     // 400ms
            'normal': this.config.widgetLoadBudget,         // 500ms
            'low': this.config.widgetLoadBudget * 1.5      // 750ms
        };
        
        return budgets[priority] || budgets.normal;
    }

    /**
     * 위젯 로딩 스피너 표시
     */
    showWidgetLoading(element) {
        if (element.querySelector('.widget-loading')) return;
        
        const loader = document.createElement('div');
        loader.className = 'widget-loading';
        loader.innerHTML = `
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        `;
        
        element.appendChild(loader);
    }

    /**
     * 위젯 로딩 에러 처리
     */
    handleWidgetLoadingError(element, widgetId, error) {
        element.innerHTML = `
            <div class="widget-error alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                위젯 로딩 실패
                <small class="d-block mt-1">${error.message}</small>
                <button class="btn btn-sm btn-outline-primary mt-2" onclick="dashboardOptimizer.retryWidgetLoading('${widgetId}')">
                    다시 시도
                </button>
            </div>
        `;
    }

    /**
     * 위젯 로딩 재시도
     */
    async retryWidgetLoading(widgetId) {
        const element = document.querySelector(`[data-widget-id="${widgetId}"]`);
        if (!element) return;

        const widgetConfig = {
            element: element,
            id: widgetId,
            priority: element.dataset.priority || 'normal'
        };

        this.loadedWidgets.delete(widgetId);
        await this.loadWidget(widgetConfig);
    }

    /**
     * 로딩 완료 체크
     */
    checkLoadingComplete() {
        if (this.loadingMetrics.allWidgetsTime && !this.loadingMetrics.renderingTime) {
            this.loadingMetrics.renderingTime = performance.now();
            
            const totalLoadTime = this.loadingMetrics.renderingTime - this.loadingMetrics.startTime;
            
            console.log(`[DashboardOptimizer] Dashboard loading completed in ${totalLoadTime.toFixed(2)}ms`);
            
            // 성능 목표 달성 여부 확인
            if (totalLoadTime <= this.config.targetLoadTime) {
                console.log('✅ [DashboardOptimizer] Performance target achieved!');
            } else {
                console.warn('⚠️ [DashboardOptimizer] Performance target missed');
                this.triggerPerformanceOptimization();
            }
            
            // 성능 메트릭 저장
            this.savePerformanceMetrics();
        }
    }

    /**
     * 성능 최적화 트리거
     */
    triggerPerformanceOptimization() {
        if (this.isOptimizing) return;
        
        this.isOptimizing = true;
        
        // 최적화 전략들 실행
        setTimeout(() => {
            this.optimizeCriticalPath();
            this.optimizeWidgetLoading();
            this.optimizeRendering();
            
            this.isOptimizing = false;
        }, 100);
    }

    /**
     * 크리티컬 패스 최적화 트리거
     */
    triggerCriticalPathOptimization() {
        // 크리티컬 리소스 사전 로딩
        this.preloadCriticalResources();
        
        // DNS prefetch 추가
        this.addDnsPrefetch();
    }

    /**
     * 캐시 헬퍼 메서드들
     */
    getFromCache(key) {
        const item = sessionStorage.getItem(`dashboard_cache_${key}`);
        if (!item) return null;

        try {
            const parsed = JSON.parse(item);
            if (parsed.expires < Date.now()) {
                sessionStorage.removeItem(`dashboard_cache_${key}`);
                return null;
            }
            return parsed.data;
        } catch {
            return null;
        }
    }

    saveToCache(key, data, ttl) {
        try {
            const item = {
                data: data,
                expires: Date.now() + ttl
            };
            sessionStorage.setItem(`dashboard_cache_${key}`, JSON.stringify(item));
        } catch (error) {
            console.warn('[DashboardOptimizer] Cache save failed:', error);
        }
    }

    cleanupCache() {
        const keys = Object.keys(sessionStorage).filter(key => 
            key.startsWith('dashboard_cache_')
        );
        
        keys.forEach(key => {
            const item = sessionStorage.getItem(key);
            try {
                const parsed = JSON.parse(item);
                if (parsed.expires < Date.now()) {
                    sessionStorage.removeItem(key);
                }
            } catch {
                sessionStorage.removeItem(key);
            }
        });
    }

    /**
     * 위젯 메트릭 기록
     */
    recordWidgetMetric(widgetId, metric, value) {
        if (!this.widgetMetrics.has(widgetId)) {
            this.widgetMetrics.set(widgetId, {});
        }
        
        this.widgetMetrics.get(widgetId)[metric] = value;
    }

    /**
     * 성능 메트릭 저장
     */
    savePerformanceMetrics() {
        const metrics = {
            ...this.loadingMetrics,
            widgetMetrics: Object.fromEntries(this.widgetMetrics),
            timestamp: Date.now(),
            url: location.href
        };
        
        // 로컬 저장소에 저장
        localStorage.setItem('dashboard_performance_metrics', JSON.stringify(metrics));
        
        // 서버에 전송 (선택적)
        if (navigator.sendBeacon) {
            navigator.sendBeacon('/api/performance/metrics/', JSON.stringify(metrics));
        }
    }

    /**
     * 유틸리티 메서드들
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    cleanupUnusedWidgets() {
        // 뷰포트 밖의 로우 우선순위 위젯들 정리
        const lowPriorityWidgets = document.querySelectorAll('[data-priority="low"]');
        
        lowPriorityWidgets.forEach(widget => {
            const rect = widget.getBoundingClientRect();
            const isVisible = rect.top < window.innerHeight + 1000 && rect.bottom > -1000;
            
            if (!isVisible && widget.innerHTML.length > 1000) {
                widget.innerHTML = '<div class="widget-placeholder">위젯이 정리되었습니다.</div>';
            }
        });
    }

    cleanupDOM() {
        // 사용하지 않는 DOM 요소들 정리
        const cleanupSelectors = [
            '.tooltip',
            '.modal-backdrop',
            '[data-cleanup="true"]',
            '.temp-element'
        ];
        
        cleanupSelectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => el.remove());
        });
    }

    preventLayoutThrashing() {
        // DOM 읽기와 쓰기를 배치로 처리
        this.domReads = [];
        this.domWrites = [];
        
        this.batchDOMRead = (callback) => {
            this.domReads.push(callback);
            this.scheduleDOMUpdate();
        };
        
        this.batchDOMWrite = (callback) => {
            this.domWrites.push(callback);
            this.scheduleDOMUpdate();
        };
    }

    scheduleDOMUpdate() {
        if (!this.domUpdateScheduled) {
            this.domUpdateScheduled = true;
            
            requestAnimationFrame(() => {
                // 모든 읽기 작업 먼저 수행
                this.domReads.forEach(callback => {
                    try {
                        callback();
                    } catch (error) {
                        console.error('[DashboardOptimizer] DOM read failed:', error);
                    }
                });
                
                // 그 다음 쓰기 작업 수행
                this.domWrites.forEach(callback => {
                    try {
                        callback();
                    } catch (error) {
                        console.error('[DashboardOptimizer] DOM write failed:', error);
                    }
                });
                
                this.domReads = [];
                this.domWrites = [];
                this.domUpdateScheduled = false;
            });
        }
    }

    analyzeAndOptimize() {
        const totalLoadTime = (this.loadingMetrics.renderingTime || Date.now()) - this.loadingMetrics.startTime;
        
        console.log('[DashboardOptimizer] Performance analysis:', {
            totalLoadTime: totalLoadTime,
            target: this.config.targetLoadTime,
            achieved: totalLoadTime <= this.config.targetLoadTime
        });
    }

    performPerformanceCheck() {
        if ('memory' in performance) {
            const memory = performance.memory;
            const usageRate = memory.usedJSHeapSize / memory.jsHeapSizeLimit;
            
            if (usageRate > 0.8) {
                console.warn('[DashboardOptimizer] High memory usage detected');
                this.performMemoryCleanup();
            }
        }
    }

    handleNetworkChange(isOnline) {
        if (isOnline) {
            // 온라인 복구 시 실패한 위젯들 재시도
            this.retryFailedWidgets();
        } else {
            // 오프라인 시 불필요한 네트워크 요청 중단
            this.pauseNetworkRequests();
        }
    }

    retryFailedWidgets() {
        const failedWidgets = document.querySelectorAll('.widget-error');
        failedWidgets.forEach(widget => {
            const widgetId = widget.parentElement.dataset.widgetId;
            if (widgetId) {
                this.retryWidgetLoading(widgetId);
            }
        });
    }

    pauseNetworkRequests() {
        // 진행 중인 위젯 로딩 일시 중지
        this.loadingWidgets.clear();
    }

    preloadCriticalResources() {
        const criticalResources = [
            '/static/css/common.css',
            '/static/js/common.js',
            '/api/dashboard/critical-data/'
        ];
        
        criticalResources.forEach(resource => {
            const link = document.createElement('link');
            link.rel = 'prefetch';
            link.href = resource;
            document.head.appendChild(link);
        });
    }

    addDnsPrefetch() {
        const domains = ['api.example.com', 'cdn.example.com'];
        
        domains.forEach(domain => {
            const link = document.createElement('link');
            link.rel = 'dns-prefetch';
            link.href = `//${domain}`;
            document.head.appendChild(link);
        });
    }

    optimizeCriticalPath() {
        console.log('[DashboardOptimizer] Optimizing critical path...');
        this.preloadCriticalResources();
    }

    optimizeWidgetLoading() {
        console.log('[DashboardOptimizer] Optimizing widget loading...');
        // 로딩 전략 조정
        this.config.maxConcurrentWidgets = Math.max(1, this.config.maxConcurrentWidgets - 1);
    }

    optimizeRendering() {
        console.log('[DashboardOptimizer] Optimizing rendering...');
        // 렌더링 성능 향상을 위한 최적화
        this.scheduleRender(() => {
            document.body.style.willChange = 'auto';
        });
    }

    /**
     * 성능 통계 조회
     */
    getPerformanceStats() {
        return {
            config: this.config,
            loadingMetrics: this.loadingMetrics,
            widgetMetrics: Object.fromEntries(this.widgetMetrics),
            loadedWidgets: this.loadedWidgets.size,
            loadingWidgets: this.loadingWidgets.size,
            loadingQueue: this.loadingQueue.length,
            renderQueue: this.renderQueue.length,
            performanceBudget: this.performanceBudget
        };
    }

    /**
     * 정리
     */
    destroy() {
        // 타이머들 정리
        if (this.memoryCleanupInterval) {
            clearInterval(this.memoryCleanupInterval);
        }
        
        if (this.performanceCheckInterval) {
            clearInterval(this.performanceCheckInterval);
        }
        
        // 큐 정리
        this.loadingQueue.length = 0;
        this.renderQueue.length = 0;
        this.loadedWidgets.clear();
        this.loadingWidgets.clear();
        this.widgetMetrics.clear();
        
        console.log('[DashboardOptimizer] Dashboard performance optimizer destroyed');
    }
}

// 전역으로 내보내기
window.DashboardPerformanceOptimizer = DashboardPerformanceOptimizer;

// 자동 초기화
window.addEventListener('DOMContentLoaded', () => {
    window.dashboardOptimizer = new DashboardPerformanceOptimizer({
        targetLoadTime: 3000,
        enableProgressiveLoading: true,
        enableWidgetPrioritization: true,
        enableMemoryOptimization: true
    });
});