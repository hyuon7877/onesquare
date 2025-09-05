/**
 * OneSquare 오프라인 대시보드 통합 관리자
 * 
 * 모든 오프라인 대시보드 컴포넌트들을 통합하고 조율하는 중앙 관리 시스템
 * 저장소, UI, 동기화, 가이드 시스템을 하나로 연결하여 일관된 오프라인 경험 제공
 */

class OfflineDashboardOrchestrator {
    constructor(config = {}) {
        this.config = {
            enableStorage: config.enableStorage !== false,
            enableUI: config.enableUI !== false,
            enableSync: config.enableSync !== false,
            enableGuide: config.enableGuide !== false,
            enableTesting: config.enableTesting !== false,
            debugMode: config.debugMode || false,
            autoInit: config.autoInit !== false,
            ...config
        };

        // 컴포넌트 인스턴스들
        this.components = {
            storage: null,
            ui: null,
            sync: null,
            guide: null
        };

        // 상태 관리
        this.state = {
            isInitialized: false,
            isOffline: !navigator.onLine,
            componentsReady: {
                storage: false,
                ui: false,
                sync: false,
                guide: false
            },
            lastHealthCheck: null,
            errors: [],
            metrics: {
                initTime: null,
                offlineEvents: 0,
                syncEvents: 0,
                storageOperations: 0
            }
        };

        // 이벤트 시스템
        this.eventBus = new EventTarget();

        if (this.config.autoInit) {
            this.init();
        }
    }

    /**
     * 오프라인 대시보드 시스템 초기화
     */
    async init() {
        const startTime = performance.now();
        
        try {
            console.log('[OfflineDashboardOrchestrator] Initializing offline dashboard system...');
            
            // 1. 환경 체크
            await this.checkEnvironment();
            
            // 2. 컴포넌트들 순차 초기화
            await this.initializeComponents();
            
            // 3. 컴포넌트 간 연결 설정
            await this.connectComponents();
            
            // 4. 이벤트 리스너 설정
            await this.setupEventListeners();
            
            // 5. 헬스 체크 시작
            await this.startHealthCheck();
            
            // 6. 초기 데이터 로드
            await this.loadInitialData();
            
            this.state.isInitialized = true;
            this.state.metrics.initTime = performance.now() - startTime;
            
            console.log(`[OfflineDashboardOrchestrator] System initialized successfully in ${this.state.metrics.initTime.toFixed(2)}ms`);
            
            // 초기화 완료 이벤트 발생
            this.emit('systemReady', {
                initTime: this.state.metrics.initTime,
                components: Object.keys(this.components).filter(key => this.components[key])
            });
            
        } catch (error) {
            console.error('[OfflineDashboardOrchestrator] Initialization failed:', error);
            this.state.errors.push({
                type: 'initialization',
                error: error.message,
                timestamp: Date.now()
            });
            throw error;
        }
    }

    /**
     * 환경 체크
     */
    async checkEnvironment() {
        const checks = {
            indexedDB: 'indexedDB' in window,
            serviceWorker: 'serviceWorker' in navigator,
            localStorage: 'localStorage' in window,
            fetch: 'fetch' in window,
            customEvents: 'CustomEvent' in window
        };

        const failed = Object.entries(checks).filter(([, supported]) => !supported);
        
        if (failed.length > 0) {
            throw new Error(`Unsupported features: ${failed.map(([name]) => name).join(', ')}`);
        }

        console.log('[OfflineDashboardOrchestrator] Environment check passed');
    }

    /**
     * 컴포넌트들 초기화
     */
    async initializeComponents() {
        console.log('[OfflineDashboardOrchestrator] Initializing components...');

        // 1. 저장소 초기화 (우선순위 1)
        if (this.config.enableStorage) {
            try {
                this.components.storage = new OfflineDashboardStorage({
                    ...this.config.storage,
                    debugMode: this.config.debugMode
                });
                await this.waitForComponentReady('storage', this.components.storage);
                this.state.componentsReady.storage = true;
                console.log('✅ Storage component ready');
            } catch (error) {
                console.error('❌ Storage component failed:', error);
                this.state.errors.push({ type: 'storage', error: error.message, timestamp: Date.now() });
            }
        }

        // 2. 동기화 관리자 초기화 (우선순위 2)
        if (this.config.enableSync && this.components.storage) {
            try {
                this.components.sync = new OfflineSyncManager({
                    ...this.config.sync,
                    debugMode: this.config.debugMode
                });
                this.state.componentsReady.sync = true;
                console.log('✅ Sync component ready');
            } catch (error) {
                console.error('❌ Sync component failed:', error);
                this.state.errors.push({ type: 'sync', error: error.message, timestamp: Date.now() });
            }
        }

        // 3. UI 컴포넌트 초기화 (우선순위 3)
        if (this.config.enableUI) {
            try {
                this.components.ui = new OfflineDashboardUI({
                    ...this.config.ui,
                    debugMode: this.config.debugMode
                });
                this.state.componentsReady.ui = true;
                console.log('✅ UI component ready');
            } catch (error) {
                console.error('❌ UI component failed:', error);
                this.state.errors.push({ type: 'ui', error: error.message, timestamp: Date.now() });
            }
        }

        // 4. 가이드 시스템 초기화 (우선순위 4)
        if (this.config.enableGuide) {
            try {
                this.components.guide = new OfflineGuideSystem({
                    ...this.config.guide,
                    debugMode: this.config.debugMode
                });
                this.state.componentsReady.guide = true;
                console.log('✅ Guide component ready');
            } catch (error) {
                console.error('❌ Guide component failed:', error);
                this.state.errors.push({ type: 'guide', error: error.message, timestamp: Date.now() });
            }
        }
    }

    /**
     * 컴포넌트 준비 대기
     */
    async waitForComponentReady(name, component, maxWait = 10000) {
        const startTime = Date.now();
        
        while (!component.isInitialized && Date.now() - startTime < maxWait) {
            await new Promise(resolve => setTimeout(resolve, 100));
        }
        
        if (!component.isInitialized) {
            throw new Error(`Component ${name} failed to initialize within ${maxWait}ms`);
        }
    }

    /**
     * 컴포넌트 간 연결 설정
     */
    async connectComponents() {
        console.log('[OfflineDashboardOrchestrator] Connecting components...');

        // 저장소와 동기화 관리자 연결
        if (this.components.storage && this.components.sync) {
            // 동기화 데이터를 저장소에 저장하도록 연결
            this.components.sync.setStorageProvider(this.components.storage);
        }

        // UI와 저장소 연결
        if (this.components.ui && this.components.storage) {
            // 저장소 상태를 UI에 반영
            this.components.ui.setStorageProvider(this.components.storage);
        }

        // 동기화와 UI 연결
        if (this.components.sync && this.components.ui) {
            // 동기화 상태를 UI에 표시
            this.components.ui.setSyncProvider(this.components.sync);
        }

        // 가이드와 다른 컴포넌트들 연결
        if (this.components.guide) {
            if (this.components.storage) {
                this.components.guide.setStorageProvider(this.components.storage);
            }
            if (this.components.ui) {
                this.components.guide.setUIProvider(this.components.ui);
            }
        }
    }

    /**
     * 통합 이벤트 리스너 설정
     */
    async setupEventListeners() {
        // 네트워크 상태 변경
        window.addEventListener('online', () => this.handleNetworkChange(true));
        window.addEventListener('offline', () => this.handleNetworkChange(false));

        // 컴포넌트별 이벤트 통합
        if (this.components.storage) {
            this.setupStorageEventListeners();
        }
        
        if (this.components.sync) {
            this.setupSyncEventListeners();
        }
        
        if (this.components.ui) {
            this.setupUIEventListeners();
        }
        
        if (this.components.guide) {
            this.setupGuideEventListeners();
        }

        // 전역 이벤트 리스너
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.performHealthCheck();
            }
        });

        // 에러 핸들링
        window.addEventListener('error', (event) => {
            this.handleGlobalError(event.error);
        });

        window.addEventListener('unhandledrejection', (event) => {
            this.handleGlobalError(event.reason);
        });
    }

    /**
     * 저장소 이벤트 리스너 설정
     */
    setupStorageEventListeners() {
        // 저장소 작업 통계
        this.components.storage.addEventListener?.('dataStored', () => {
            this.state.metrics.storageOperations++;
        });

        this.components.storage.addEventListener?.('dataRetrieved', () => {
            this.state.metrics.storageOperations++;
        });

        // 저장소 오류
        this.components.storage.addEventListener?.('storageError', (event) => {
            this.handleComponentError('storage', event.detail);
        });
    }

    /**
     * 동기화 이벤트 리스너 설정
     */
    setupSyncEventListeners() {
        // 동기화 이벤트 통계
        window.addEventListener('syncStart', () => {
            this.state.metrics.syncEvents++;
            this.emit('syncStatusChanged', { status: 'syncing' });
        });

        window.addEventListener('syncComplete', (event) => {
            this.emit('syncStatusChanged', { status: 'success', details: event.detail });
        });

        window.addEventListener('syncError', (event) => {
            this.handleComponentError('sync', event.detail);
            this.emit('syncStatusChanged', { status: 'error', details: event.detail });
        });
    }

    /**
     * UI 이벤트 리스너 설정
     */
    setupUIEventListeners() {
        // UI 상태 변경
        window.addEventListener('offlineStatusChange', (event) => {
            this.emit('offlineStatusChanged', event.detail);
        });

        // 수동 동기화 요청
        window.addEventListener('manualSyncRequested', async () => {
            if (this.components.sync) {
                try {
                    await this.components.sync.triggerManualSync();
                } catch (error) {
                    this.handleComponentError('sync', error);
                }
            }
        });
    }

    /**
     * 가이드 이벤트 리스너 설정
     */
    setupGuideEventListeners() {
        // 가이드 시스템 이벤트는 자체적으로 처리되므로 필요시 추가 연결
        window.addEventListener('guideCompleted', (event) => {
            this.emit('guideCompleted', event.detail);
        });
    }

    /**
     * 네트워크 상태 변경 처리
     */
    async handleNetworkChange(isOnline) {
        const wasOffline = this.state.isOffline;
        this.state.isOffline = !isOnline;

        console.log(`[OfflineDashboardOrchestrator] Network ${isOnline ? 'connected' : 'disconnected'}`);

        if (!wasOffline && !isOnline) {
            // 오프라인 전환
            this.state.metrics.offlineEvents++;
            this.emit('offlineMode', { duration: 0 });
            
            // 모든 컴포넌트에 오프라인 상태 알림
            await this.notifyComponentsOffline();
            
        } else if (wasOffline && isOnline) {
            // 온라인 복구
            this.emit('onlineMode', { wasOffline: true });
            
            // 모든 컴포넌트에 온라인 상태 알림
            await this.notifyComponentsOnline();
            
            // 자동 동기화 트리거
            if (this.components.sync) {
                setTimeout(() => {
                    this.components.sync.performSync();
                }, 1000);
            }
        }
    }

    /**
     * 컴포넌트들에 오프라인 상태 알림
     */
    async notifyComponentsOffline() {
        const notifications = [];

        Object.entries(this.components).forEach(([name, component]) => {
            if (component && typeof component.handleOffline === 'function') {
                notifications.push(
                    component.handleOffline().catch(error => {
                        console.warn(`[OfflineDashboardOrchestrator] ${name} offline handling failed:`, error);
                    })
                );
            }
        });

        await Promise.allSettled(notifications);
    }

    /**
     * 컴포넌트들에 온라인 상태 알림
     */
    async notifyComponentsOnline() {
        const notifications = [];

        Object.entries(this.components).forEach(([name, component]) => {
            if (component && typeof component.handleOnline === 'function') {
                notifications.push(
                    component.handleOnline().catch(error => {
                        console.warn(`[OfflineDashboardOrchestrator] ${name} online handling failed:`, error);
                    })
                );
            }
        });

        await Promise.allSettled(notifications);
    }

    /**
     * 헬스 체크 시작
     */
    async startHealthCheck() {
        // 주기적 헬스 체크 (5분마다)
        setInterval(() => {
            this.performHealthCheck();
        }, 5 * 60 * 1000);

        // 초기 헬스 체크
        await this.performHealthCheck();
    }

    /**
     * 헬스 체크 수행
     */
    async performHealthCheck() {
        const healthReport = {
            timestamp: Date.now(),
            components: {},
            overall: 'healthy',
            issues: []
        };

        // 각 컴포넌트의 상태 체크
        for (const [name, component] of Object.entries(this.components)) {
            if (component) {
                try {
                    const status = await this.checkComponentHealth(name, component);
                    healthReport.components[name] = status;
                    
                    if (status.status !== 'healthy') {
                        healthReport.issues.push({
                            component: name,
                            issue: status.message
                        });
                        
                        if (status.status === 'critical') {
                            healthReport.overall = 'critical';
                        } else if (healthReport.overall === 'healthy') {
                            healthReport.overall = 'warning';
                        }
                    }
                    
                } catch (error) {
                    healthReport.components[name] = {
                        status: 'error',
                        message: error.message
                    };
                    healthReport.issues.push({
                        component: name,
                        issue: error.message
                    });
                    healthReport.overall = 'critical';
                }
            }
        }

        this.state.lastHealthCheck = healthReport;
        
        if (this.config.debugMode) {
            console.log('[OfflineDashboardOrchestrator] Health check:', healthReport);
        }

        // 헬스 체크 완료 이벤트
        this.emit('healthCheckCompleted', healthReport);

        // 문제가 있으면 자동 복구 시도
        if (healthReport.overall !== 'healthy') {
            await this.attemptAutoRecovery(healthReport);
        }
    }

    /**
     * 컴포넌트 헬스 체크
     */
    async checkComponentHealth(name, component) {
        // 컴포넌트별 상태 확인 로직
        switch (name) {
            case 'storage':
                return await this.checkStorageHealth(component);
            case 'sync':
                return this.checkSyncHealth(component);
            case 'ui':
                return this.checkUIHealth(component);
            case 'guide':
                return this.checkGuideHealth(component);
            default:
                return { status: 'unknown', message: 'Unknown component' };
        }
    }

    /**
     * 저장소 헬스 체크
     */
    async checkStorageHealth(storage) {
        try {
            const status = storage.getStorageStatus();
            
            if (!status.isInitialized) {
                return { status: 'critical', message: 'Storage not initialized' };
            }
            
            if (status.storageQuota.percentage > 90) {
                return { status: 'warning', message: 'Storage quota nearly full' };
            }
            
            // 간단한 읽기/쓰기 테스트
            const testKey = `health_check_${Date.now()}`;
            const testData = { timestamp: Date.now() };
            
            await storage.updateMetadata(testKey, testData);
            const retrieved = await storage.getMetadata(testKey);
            
            if (!retrieved || retrieved.timestamp !== testData.timestamp) {
                return { status: 'critical', message: 'Storage read/write failed' };
            }

            return { status: 'healthy', message: 'Storage working normally' };
            
        } catch (error) {
            return { status: 'critical', message: `Storage error: ${error.message}` };
        }
    }

    /**
     * 동기화 헬스 체크
     */
    checkSyncHealth(sync) {
        const stats = sync.getSyncStats();
        
        if (stats.failedSyncAttempts >= 3) {
            return { status: 'critical', message: 'Multiple sync failures' };
        }
        
        if (stats.queueSize > 50) {
            return { status: 'warning', message: 'Large sync queue' };
        }
        
        return { status: 'healthy', message: 'Sync working normally' };
    }

    /**
     * UI 헬스 체크
     */
    checkUIHealth(ui) {
        const status = ui.getStatus();
        
        if (status.offlineDuration > 24 * 60 * 60 * 1000) { // 24시간
            return { status: 'warning', message: 'Long offline duration' };
        }
        
        return { status: 'healthy', message: 'UI working normally' };
    }

    /**
     * 가이드 헬스 체크
     */
    checkGuideHealth(guide) {
        const status = guide.getStatus();
        
        // 가이드 시스템은 주로 UI 관련이므로 간단한 체크
        return { status: 'healthy', message: 'Guide system working normally' };
    }

    /**
     * 자동 복구 시도
     */
    async attemptAutoRecovery(healthReport) {
        console.log('[OfflineDashboardOrchestrator] Attempting auto recovery...');

        for (const issue of healthReport.issues) {
            try {
                await this.recoverComponent(issue.component, issue.issue);
            } catch (error) {
                console.error(`[OfflineDashboardOrchestrator] Recovery failed for ${issue.component}:`, error);
            }
        }
    }

    /**
     * 컴포넌트 복구
     */
    async recoverComponent(componentName, issue) {
        const component = this.components[componentName];
        
        if (!component) return;

        switch (componentName) {
            case 'storage':
                if (issue.includes('quota')) {
                    await component.cleanupOldData();
                }
                break;
                
            case 'sync':
                if (issue.includes('failures')) {
                    component.clearSyncQueue();
                }
                break;
                
            case 'ui':
                // UI 문제는 주로 새로고침으로 해결
                if (issue.includes('offline')) {
                    await component.updateNetworkStatus(navigator.onLine);
                }
                break;
        }
    }

    /**
     * 초기 데이터 로드
     */
    async loadInitialData() {
        if (this.components.storage && navigator.onLine) {
            try {
                await this.components.storage.performInitialSync();
            } catch (error) {
                console.warn('[OfflineDashboardOrchestrator] Initial data load failed:', error);
            }
        }
    }

    /**
     * 컴포넌트 에러 처리
     */
    handleComponentError(componentName, error) {
        this.state.errors.push({
            type: componentName,
            error: typeof error === 'string' ? error : error.message,
            timestamp: Date.now()
        });

        console.error(`[OfflineDashboardOrchestrator] Component error (${componentName}):`, error);

        // 에러 이벤트 발생
        this.emit('componentError', {
            component: componentName,
            error: error
        });
    }

    /**
     * 전역 에러 처리
     */
    handleGlobalError(error) {
        this.state.errors.push({
            type: 'global',
            error: error.message || String(error),
            timestamp: Date.now()
        });

        console.error('[OfflineDashboardOrchestrator] Global error:', error);
    }

    /**
     * 이벤트 발생
     */
    emit(eventType, data) {
        const event = new CustomEvent(eventType, { detail: data });
        this.eventBus.dispatchEvent(event);
        window.dispatchEvent(event);
    }

    /**
     * 이벤트 리스너 추가
     */
    on(eventType, callback) {
        this.eventBus.addEventListener(eventType, callback);
    }

    /**
     * 이벤트 리스너 제거
     */
    off(eventType, callback) {
        this.eventBus.removeEventListener(eventType, callback);
    }

    /**
     * 오프라인 기능 상태 조회
     */
    async getOfflineCapabilities() {
        const capabilities = {
            storage: false,
            sync: false,
            ui: false,
            guide: false,
            overall: 0
        };

        let totalScore = 0;
        let maxScore = 0;

        // 각 컴포넌트의 기능 평가
        if (this.components.storage?.isInitialized) {
            const storageCapabilities = await this.components.storage.getOfflineCapabilities();
            capabilities.storage = storageCapabilities.available;
            totalScore += storageCapabilities.coverage || 0;
            maxScore += 85; // 저장소는 85% 가중치
        }

        if (this.components.sync) {
            capabilities.sync = true;
            totalScore += 10; // 동기화는 10% 가중치
            maxScore += 10;
        }

        if (this.components.ui) {
            capabilities.ui = true;
            totalScore += 3; // UI는 3% 가중치
            maxScore += 3;
        }

        if (this.components.guide) {
            capabilities.guide = true;
            totalScore += 2; // 가이드는 2% 가중치
            maxScore += 2;
        }

        capabilities.overall = maxScore > 0 ? Math.round((totalScore / maxScore) * 100) : 0;

        return capabilities;
    }

    /**
     * 시스템 상태 조회
     */
    getSystemStatus() {
        return {
            isInitialized: this.state.isInitialized,
            isOffline: this.state.isOffline,
            components: {
                ...this.state.componentsReady,
                instances: Object.keys(this.components).reduce((acc, key) => {
                    acc[key] = !!this.components[key];
                    return acc;
                }, {})
            },
            health: this.state.lastHealthCheck,
            metrics: { ...this.state.metrics },
            errors: this.state.errors.slice(-10), // 최근 10개 에러만
            config: this.config
        };
    }

    /**
     * 통계 조회
     */
    getMetrics() {
        const baseMetrics = { ...this.state.metrics };
        
        // 컴포넌트별 통계 추가
        if (this.components.sync) {
            baseMetrics.sync = this.components.sync.getSyncStats();
        }
        
        if (this.components.storage) {
            baseMetrics.storage = this.components.storage.getStorageStatus();
        }
        
        return baseMetrics;
    }

    /**
     * 수동 동기화 트리거
     */
    async triggerSync() {
        if (!this.components.sync) {
            throw new Error('Sync component not available');
        }
        
        if (!navigator.onLine) {
            throw new Error('No network connection');
        }
        
        return await this.components.sync.triggerManualSync();
    }

    /**
     * 저장소 정리
     */
    async cleanupStorage() {
        if (!this.components.storage) {
            throw new Error('Storage component not available');
        }
        
        return await this.components.storage.cleanupOldData();
    }

    /**
     * 시스템 재시작
     */
    async restart() {
        console.log('[OfflineDashboardOrchestrator] Restarting system...');
        
        await this.destroy();
        await new Promise(resolve => setTimeout(resolve, 1000));
        await this.init();
    }

    /**
     * 개발/테스트 모드 토글
     */
    toggleDebugMode() {
        this.config.debugMode = !this.config.debugMode;
        
        // 모든 컴포넌트에 디버그 모드 설정
        Object.values(this.components).forEach(component => {
            if (component && component.setDebugMode) {
                component.setDebugMode(this.config.debugMode);
            }
        });
        
        console.log(`[OfflineDashboardOrchestrator] Debug mode ${this.config.debugMode ? 'enabled' : 'disabled'}`);
    }

    /**
     * 정리
     */
    async destroy() {
        console.log('[OfflineDashboardOrchestrator] Destroying offline dashboard system...');
        
        // 컴포넌트들 정리
        const destroyPromises = Object.entries(this.components).map(async ([name, component]) => {
            if (component && typeof component.destroy === 'function') {
                try {
                    await component.destroy();
                    console.log(`✅ ${name} component destroyed`);
                } catch (error) {
                    console.error(`❌ Failed to destroy ${name} component:`, error);
                }
            }
        });

        await Promise.allSettled(destroyPromises);

        // 상태 초기화
        this.state.isInitialized = false;
        this.state.componentsReady = {
            storage: false,
            ui: false,
            sync: false,
            guide: false
        };
        this.components = {
            storage: null,
            ui: null,
            sync: null,
            guide: null
        };

        console.log('[OfflineDashboardOrchestrator] System destroyed');
    }
}

// 전역으로 내보내기
window.OfflineDashboardOrchestrator = OfflineDashboardOrchestrator;

// 전역 설정 객체 초기화
window.oneSquareConfig = window.oneSquareConfig || {};

// 자동 초기화
window.addEventListener('DOMContentLoaded', () => {
    if (window.oneSquareConfig?.disableOfflineDashboard !== true) {
        window.offlineDashboard = new OfflineDashboardOrchestrator(window.oneSquareConfig?.offlineDashboard || {});
    }
});