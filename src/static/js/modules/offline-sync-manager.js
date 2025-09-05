/**
 * OneSquare 오프라인 동기화 및 충돌 해결 관리자
 * 
 * 네트워크 복구 시 자동 데이터 동기화 및 충돌 상황 처리
 * 오프라인 중 발생한 변경사항과 서버 데이터 간 충돌 해결
 */

class OfflineSyncManager {
    constructor(config = {}) {
        this.config = {
            syncInterval: config.syncInterval || 30000, // 30초
            maxRetryAttempts: config.maxRetryAttempts || 3,
            retryDelay: config.retryDelay || 5000, // 5초
            conflictResolution: config.conflictResolution || 'merge', // 'merge', 'server', 'client', 'manual'
            enableBackgroundSync: config.enableBackgroundSync !== false,
            syncBatchSize: config.syncBatchSize || 10,
            prioritySyncTypes: config.prioritySyncTypes || ['notifications', 'criticalData'],
            ...config
        };

        this.syncInProgress = false;
        this.syncQueue = new Map();
        this.conflictQueue = [];
        this.syncHistory = [];
        this.lastSuccessfulSync = null;
        this.failedSyncAttempts = 0;
        
        // 동기화 상태
        this.syncStats = {
            totalSyncs: 0,
            successfulSyncs: 0,
            failedSyncs: 0,
            conflictsResolved: 0,
            lastSyncDuration: 0
        };

        // 충돌 해결 전략
        this.conflictResolvers = new Map();
        this.setupDefaultConflictResolvers();

        this.init();
    }

    /**
     * 동기화 관리자 초기화
     */
    async init() {
        try {
            console.log('[OfflineSyncManager] Initializing offline sync manager...');

            await this.loadSyncQueue();
            await this.setupEventListeners();
            await this.startBackgroundSync();
            await this.registerServiceWorkerSync();

            // 네트워크가 사용 가능하면 초기 동기화 수행
            if (navigator.onLine) {
                setTimeout(() => this.performSync(), 1000);
            }

            console.log('[OfflineSyncManager] Offline sync manager initialized successfully');

        } catch (error) {
            console.error('[OfflineSyncManager] Initialization failed:', error);
        }
    }

    /**
     * 기본 충돌 해결자 설정
     */
    setupDefaultConflictResolvers() {
        // 알림 데이터 충돌 해결
        this.conflictResolvers.set('notifications', (clientData, serverData) => {
            // 서버가 더 최신이면 서버 데이터 사용
            if (serverData.timestamp > clientData.timestamp) {
                return { resolution: 'server', data: serverData };
            }
            // 클라이언트가 더 최신이면 병합
            return { 
                resolution: 'merge', 
                data: { ...serverData, ...clientData, timestamp: Math.max(clientData.timestamp, serverData.timestamp) }
            };
        });

        // 사용자 설정 충돌 해결
        this.conflictResolvers.set('userSettings', (clientData, serverData) => {
            // 사용자 설정은 클라이언트 우선
            return { resolution: 'client', data: clientData };
        });

        // 대시보드 통계 충돌 해결
        this.conflictResolvers.set('dashboardStats', (clientData, serverData) => {
            // 통계는 서버가 항상 우선
            return { resolution: 'server', data: serverData };
        });

        // 일반적인 충돌 해결 (타임스탬프 기준)
        this.conflictResolvers.set('default', (clientData, serverData) => {
            const clientTime = clientData.timestamp || clientData.modified || 0;
            const serverTime = serverData.timestamp || serverData.modified || 0;

            if (serverTime > clientTime) {
                return { resolution: 'server', data: serverData };
            } else if (clientTime > serverTime) {
                return { resolution: 'client', data: clientData };
            } else {
                // 같은 시간이면 병합
                return {
                    resolution: 'merge',
                    data: { ...serverData, ...clientData }
                };
            }
        });
    }

    /**
     * 이벤트 리스너 설정
     */
    async setupEventListeners() {
        // 네트워크 상태 변경 감지
        window.addEventListener('online', () => {
            this.handleNetworkReconnection();
        });

        window.addEventListener('offline', () => {
            this.handleNetworkDisconnection();
        });

        // 페이지 가시성 변경 감지
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && navigator.onLine) {
                this.performSync();
            }
        });

        // 데이터 변경 감지
        window.addEventListener('dataChanged', (event) => {
            this.queueForSync(event.detail);
        });

        // Service Worker 메시지 감지
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', (event) => {
                this.handleServiceWorkerMessage(event);
            });
        }
    }

    /**
     * 백그라운드 동기화 시작
     */
    async startBackgroundSync() {
        if (!this.config.enableBackgroundSync) return;

        // 주기적 동기화
        setInterval(async () => {
            if (navigator.onLine && !this.syncInProgress) {
                await this.performSync();
            }
        }, this.config.syncInterval);

        // 아이들 타임에 동기화
        if ('requestIdleCallback' in window) {
            const scheduleIdleSync = () => {
                requestIdleCallback(async (deadline) => {
                    if (deadline.timeRemaining() > 0 && navigator.onLine && !this.syncInProgress) {
                        await this.performSync();
                    }
                    scheduleIdleSync();
                }, { timeout: 60000 }); // 최대 1분 대기
            };
            scheduleIdleSync();
        }
    }

    /**
     * Service Worker 백그라운드 동기화 등록
     */
    async registerServiceWorkerSync() {
        if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
            try {
                const registration = await navigator.serviceWorker.ready;
                await registration.sync.register('background-sync');
                console.log('[OfflineSyncManager] Background sync registered');
            } catch (error) {
                console.warn('[OfflineSyncManager] Background sync registration failed:', error);
            }
        }
    }

    /**
     * 네트워크 재연결 처리
     */
    async handleNetworkReconnection() {
        console.log('[OfflineSyncManager] Network reconnected, starting sync...');
        
        // 실패 카운터 리셋
        this.failedSyncAttempts = 0;
        
        // 즉시 동기화 수행
        await this.performSync();
        
        // 동기화 완료 알림
        window.dispatchEvent(new CustomEvent('networkReconnected', {
            detail: { syncPerformed: true }
        }));
    }

    /**
     * 네트워크 연결 끊김 처리
     */
    handleNetworkDisconnection() {
        console.log('[OfflineSyncManager] Network disconnected');
        
        // 진행 중인 동기화 중단
        if (this.syncInProgress) {
            console.log('[OfflineSyncManager] Cancelling ongoing sync due to network disconnection');
            this.syncInProgress = false;
        }
    }

    /**
     * 메인 동기화 수행
     */
    async performSync() {
        if (this.syncInProgress || !navigator.onLine) {
            return;
        }

        this.syncInProgress = true;
        const syncStartTime = Date.now();
        
        try {
            console.log('[OfflineSyncManager] Starting sync process...');
            
            // 동기화 시작 이벤트 발생
            window.dispatchEvent(new CustomEvent('syncStart'));

            // 1. 우선순위 데이터 동기화
            await this.syncPriorityData();

            // 2. 동기화 큐 처리
            await this.processSyncQueue();

            // 3. 서버에서 최신 데이터 가져오기
            await this.pullServerData();

            // 4. 충돌 해결
            await this.resolveConflicts();

            // 5. 동기화 완료 처리
            this.lastSuccessfulSync = Date.now();
            this.syncStats.successfulSyncs++;
            this.syncStats.totalSyncs++;
            this.syncStats.lastSyncDuration = Date.now() - syncStartTime;

            console.log(`[OfflineSyncManager] Sync completed in ${this.syncStats.lastSyncDuration}ms`);

            // 동기화 완료 이벤트 발생
            window.dispatchEvent(new CustomEvent('syncComplete', {
                detail: {
                    duration: this.syncStats.lastSyncDuration,
                    stats: this.syncStats
                }
            }));

        } catch (error) {
            console.error('[OfflineSyncManager] Sync failed:', error);
            
            this.failedSyncAttempts++;
            this.syncStats.failedSyncs++;
            this.syncStats.totalSyncs++;

            // 동기화 실패 이벤트 발생
            window.dispatchEvent(new CustomEvent('syncError', {
                detail: {
                    error: error.message,
                    attempts: this.failedSyncAttempts
                }
            }));

            // 재시도 로직
            if (this.failedSyncAttempts < this.config.maxRetryAttempts) {
                console.log(`[OfflineSyncManager] Scheduling retry (attempt ${this.failedSyncAttempts + 1}/${this.config.maxRetryAttempts})`);
                setTimeout(() => {
                    this.performSync();
                }, this.config.retryDelay * this.failedSyncAttempts);
            }

        } finally {
            this.syncInProgress = false;
        }
    }

    /**
     * 우선순위 데이터 동기화
     */
    async syncPriorityData() {
        console.log('[OfflineSyncManager] Syncing priority data...');
        
        for (const dataType of this.config.prioritySyncTypes) {
            try {
                await this.syncDataType(dataType, true);
            } catch (error) {
                console.warn(`[OfflineSyncManager] Priority sync failed for ${dataType}:`, error);
            }
        }
    }

    /**
     * 동기화 큐 처리
     */
    async processSyncQueue() {
        if (this.syncQueue.size === 0) {
            return;
        }

        console.log(`[OfflineSyncManager] Processing ${this.syncQueue.size} items in sync queue`);

        const queueItems = Array.from(this.syncQueue.values());
        const batches = this.createBatches(queueItems, this.config.syncBatchSize);

        for (const batch of batches) {
            try {
                await this.processSyncBatch(batch);
            } catch (error) {
                console.error('[OfflineSyncManager] Batch sync failed:', error);
                // 실패한 항목들을 다시 큐에 추가
                batch.forEach(item => {
                    item.retryCount = (item.retryCount || 0) + 1;
                    if (item.retryCount < this.config.maxRetryAttempts) {
                        this.syncQueue.set(item.id, item);
                    }
                });
            }
        }
    }

    /**
     * 동기화 배치 처리
     */
    async processSyncBatch(batch) {
        const promises = batch.map(item => this.processSyncItem(item));
        const results = await Promise.allSettled(promises);

        results.forEach((result, index) => {
            const item = batch[index];
            
            if (result.status === 'fulfilled') {
                // 성공한 항목은 큐에서 제거
                this.syncQueue.delete(item.id);
            } else {
                // 실패한 항목은 재시도 카운트 증가
                item.retryCount = (item.retryCount || 0) + 1;
                if (item.retryCount >= this.config.maxRetryAttempts) {
                    console.error(`[OfflineSyncManager] Max retries exceeded for item ${item.id}`);
                    this.syncQueue.delete(item.id);
                }
            }
        });
    }

    /**
     * 개별 동기화 항목 처리
     */
    async processSyncItem(item) {
        const { operation, endpoint, data, dataType } = item;

        const options = {
            method: operation.toUpperCase(),
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        };

        if (operation !== 'GET' && data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(endpoint, options);

        if (!response.ok) {
            throw new Error(`Sync operation failed: ${response.status} ${response.statusText}`);
        }

        const responseData = await response.json();

        // 응답 데이터가 있으면 로컬 저장소 업데이트
        if (responseData && window.offlineDashboardStorage) {
            await this.updateLocalStorage(dataType, responseData);
        }

        return responseData;
    }

    /**
     * 서버 데이터 가져오기
     */
    async pullServerData() {
        console.log('[OfflineSyncManager] Pulling server data...');

        const lastSync = this.lastSuccessfulSync || 0;
        const endpoints = [
            { url: `/api/dashboard/sync/?since=${lastSync}`, dataType: 'dashboard' },
            { url: `/api/notifications/sync/?since=${lastSync}`, dataType: 'notifications' },
            { url: `/api/activities/sync/?since=${lastSync}`, dataType: 'activities' }
        ];

        for (const { url, dataType } of endpoints) {
            try {
                const response = await fetch(url, {
                    headers: { 'Accept': 'application/json' }
                });

                if (response.ok) {
                    const serverData = await response.json();
                    await this.handleServerData(dataType, serverData);
                }
            } catch (error) {
                console.warn(`[OfflineSyncManager] Failed to pull ${dataType} data:`, error);
            }
        }
    }

    /**
     * 서버 데이터 처리
     */
    async handleServerData(dataType, serverData) {
        if (!window.offlineDashboardStorage) return;

        // 로컬 데이터와 비교
        const localData = await this.getLocalData(dataType);
        
        if (localData) {
            // 충돌 감지 및 해결
            const conflicts = this.detectConflicts(localData, serverData, dataType);
            if (conflicts.length > 0) {
                this.conflictQueue.push(...conflicts);
            }
        }

        // 충돌이 없는 데이터는 바로 저장
        const nonConflictingData = this.filterNonConflictingData(serverData, dataType);
        if (nonConflictingData.length > 0) {
            await this.updateLocalStorage(dataType, nonConflictingData);
        }
    }

    /**
     * 충돌 감지
     */
    detectConflicts(localData, serverData, dataType) {
        const conflicts = [];

        serverData.forEach(serverItem => {
            const localItem = localData.find(local => local.id === serverItem.id);
            
            if (localItem) {
                const localModified = localItem.modified || localItem.timestamp || 0;
                const serverModified = serverItem.modified || serverItem.timestamp || 0;
                
                // 로컬과 서버 모두 수정된 경우 충돌
                if (localModified !== serverModified && localItem.locallyModified) {
                    conflicts.push({
                        id: `${dataType}_${serverItem.id}`,
                        dataType: dataType,
                        clientData: localItem,
                        serverData: serverItem,
                        conflictType: 'modification'
                    });
                }
            }
        });

        return conflicts;
    }

    /**
     * 충돌 해결
     */
    async resolveConflicts() {
        if (this.conflictQueue.length === 0) return;

        console.log(`[OfflineSyncManager] Resolving ${this.conflictQueue.length} conflicts`);

        for (const conflict of this.conflictQueue) {
            try {
                const resolution = await this.resolveConflict(conflict);
                await this.applyConflictResolution(conflict, resolution);
                this.syncStats.conflictsResolved++;
            } catch (error) {
                console.error(`[OfflineSyncManager] Failed to resolve conflict ${conflict.id}:`, error);
            }
        }

        // 처리된 충돌들 제거
        this.conflictQueue = [];
    }

    /**
     * 개별 충돌 해결
     */
    async resolveConflict(conflict) {
        const { dataType, clientData, serverData } = conflict;
        
        // 충돌 해결 전략에 따라 처리
        switch (this.config.conflictResolution) {
            case 'server':
                return { resolution: 'server', data: serverData };

            case 'client':
                return { resolution: 'client', data: clientData };

            case 'manual':
                return await this.requestManualResolution(conflict);

            case 'merge':
            default:
                // 데이터 타입별 충돌 해결자 사용
                const resolver = this.conflictResolvers.get(dataType) || this.conflictResolvers.get('default');
                return resolver(clientData, serverData);
        }
    }

    /**
     * 수동 충돌 해결 요청
     */
    async requestManualResolution(conflict) {
        return new Promise((resolve) => {
            // 사용자에게 충돌 해결 UI 표시
            const event = new CustomEvent('conflictResolutionRequired', {
                detail: {
                    conflict: conflict,
                    resolve: resolve
                }
            });
            window.dispatchEvent(event);
        });
    }

    /**
     * 충돌 해결 적용
     */
    async applyConflictResolution(conflict, resolution) {
        const { dataType } = conflict;
        const { resolution: strategy, data } = resolution;

        console.log(`[OfflineSyncManager] Applying ${strategy} resolution for ${conflict.id}`);

        // 로컬 저장소 업데이트
        await this.updateLocalStorage(dataType, [data]);

        // 클라이언트 우선이면 서버로 전송
        if (strategy === 'client' || strategy === 'merge') {
            await this.queueForSync({
                dataType: dataType,
                operation: 'PUT',
                data: data,
                endpoint: this.getEndpointForDataType(dataType, data.id)
            });
        }

        // 충돌 해결 완료 이벤트
        window.dispatchEvent(new CustomEvent('conflictResolved', {
            detail: {
                conflictId: conflict.id,
                resolution: strategy,
                data: data
            }
        }));
    }

    /**
     * 동기화 큐에 항목 추가
     */
    async queueForSync(syncItem) {
        const id = syncItem.id || `${syncItem.dataType}_${Date.now()}_${Math.random()}`;
        
        const queueItem = {
            id: id,
            timestamp: Date.now(),
            retryCount: 0,
            ...syncItem
        };

        this.syncQueue.set(id, queueItem);
        
        // 큐를 저장소에 지속
        await this.saveSyncQueue();

        console.log(`[OfflineSyncManager] Queued item for sync: ${id}`);

        // 온라인이면 즉시 동기화 시도
        if (navigator.onLine && !this.syncInProgress) {
            setTimeout(() => this.performSync(), 100);
        }
    }

    /**
     * 특정 데이터 타입 동기화
     */
    async syncDataType(dataType, isPriority = false) {
        const endpoint = this.getEndpointForDataType(dataType);
        
        try {
            const response = await fetch(endpoint, {
                headers: { 'Accept': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`Failed to sync ${dataType}: ${response.status}`);
            }

            const data = await response.json();
            await this.updateLocalStorage(dataType, data);

            console.log(`[OfflineSyncManager] ${dataType} synced successfully${isPriority ? ' (priority)' : ''}`);

        } catch (error) {
            console.error(`[OfflineSyncManager] Failed to sync ${dataType}:`, error);
            throw error;
        }
    }

    /**
     * 로컬 저장소 업데이트
     */
    async updateLocalStorage(dataType, data) {
        if (!window.offlineDashboardStorage) return;

        switch (dataType) {
            case 'notifications':
                await window.offlineDashboardStorage.storeNotifications(data);
                break;
            case 'dashboard':
            case 'dashboardStats':
                await window.offlineDashboardStorage.storeDashboardStats(data);
                break;
            case 'activities':
                await window.offlineDashboardStorage.storeRecentActivities(data);
                break;
            case 'userSettings':
                await window.offlineDashboardStorage.storeUserSettings(data);
                break;
            case 'criticalData':
                await window.offlineDashboardStorage.storeCriticalData(data);
                break;
            case 'widgets':
                await window.offlineDashboardStorage.storeWidgetData(data);
                break;
            default:
                console.warn(`[OfflineSyncManager] Unknown data type: ${dataType}`);
        }

        // 데이터 업데이트 이벤트 발생
        window.dispatchEvent(new CustomEvent('dataUpdated', {
            detail: { dataType, data }
        }));
    }

    /**
     * 로컬 데이터 조회
     */
    async getLocalData(dataType) {
        if (!window.offlineDashboardStorage) return null;

        switch (dataType) {
            case 'notifications':
                return await window.offlineDashboardStorage.getOfflineNotifications();
            case 'dashboard':
            case 'dashboardStats':
                return await window.offlineDashboardStorage.getOfflineDashboardStats();
            case 'activities':
                return await window.offlineDashboardStorage.getOfflineData('recentActivities');
            case 'userSettings':
                return await window.offlineDashboardStorage.getOfflineData('userSettings');
            case 'criticalData':
                return await window.offlineDashboardStorage.getOfflineData('criticalData');
            case 'widgets':
                return await window.offlineDashboardStorage.getOfflineData('widgetData');
            default:
                return null;
        }
    }

    /**
     * 데이터 타입별 엔드포인트 생성
     */
    getEndpointForDataType(dataType, id = null) {
        const endpoints = {
            'notifications': '/api/notifications/',
            'dashboard': '/api/dashboard/stats/',
            'dashboardStats': '/api/dashboard/stats/',
            'activities': '/api/activities/recent/',
            'userSettings': '/api/user/settings/',
            'criticalData': '/api/dashboard/critical-data/',
            'widgets': '/api/dashboard/widgets/data/'
        };

        const baseEndpoint = endpoints[dataType] || '/api/sync/';
        return id ? `${baseEndpoint}${id}/` : baseEndpoint;
    }

    /**
     * 비충돌 데이터 필터링
     */
    filterNonConflictingData(serverData, dataType) {
        // 구현에 따라 충돌하지 않는 데이터만 반환
        // 현재는 모든 데이터를 반환 (간단한 구현)
        return Array.isArray(serverData) ? serverData : [serverData];
    }

    /**
     * 배치 생성
     */
    createBatches(items, batchSize) {
        const batches = [];
        for (let i = 0; i < items.length; i += batchSize) {
            batches.push(items.slice(i, i + batchSize));
        }
        return batches;
    }

    /**
     * 동기화 큐 저장
     */
    async saveSyncQueue() {
        try {
            const queueData = Array.from(this.syncQueue.values());
            localStorage.setItem('offlineSyncQueue', JSON.stringify(queueData));
        } catch (error) {
            console.warn('[OfflineSyncManager] Failed to save sync queue:', error);
        }
    }

    /**
     * 동기화 큐 로드
     */
    async loadSyncQueue() {
        try {
            const queueData = localStorage.getItem('offlineSyncQueue');
            if (queueData) {
                const items = JSON.parse(queueData);
                items.forEach(item => {
                    this.syncQueue.set(item.id, item);
                });
                console.log(`[OfflineSyncManager] Loaded ${items.length} items from sync queue`);
            }
        } catch (error) {
            console.warn('[OfflineSyncManager] Failed to load sync queue:', error);
        }
    }

    /**
     * Service Worker 메시지 처리
     */
    handleServiceWorkerMessage(event) {
        const { type, data } = event.data;

        switch (type) {
            case 'BACKGROUND_SYNC':
                console.log('[OfflineSyncManager] Background sync triggered by service worker');
                this.performSync();
                break;
                
            case 'SYNC_COMPLETE':
                console.log('[OfflineSyncManager] Background sync completed');
                break;
                
            default:
                // 알 수 없는 메시지 타입
                break;
        }
    }

    /**
     * 수동 동기화 트리거
     */
    async triggerManualSync() {
        if (!navigator.onLine) {
            throw new Error('No network connection available');
        }

        return await this.performSync();
    }

    /**
     * 동기화 통계 조회
     */
    getSyncStats() {
        return {
            ...this.syncStats,
            queueSize: this.syncQueue.size,
            conflictQueueSize: this.conflictQueue.length,
            lastSuccessfulSync: this.lastSuccessfulSync,
            syncInProgress: this.syncInProgress,
            failedSyncAttempts: this.failedSyncAttempts
        };
    }

    /**
     * 동기화 기록 조회
     */
    getSyncHistory(limit = 10) {
        return this.syncHistory.slice(-limit);
    }

    /**
     * 특정 데이터 강제 동기화
     */
    async forceSyncDataType(dataType) {
        if (!navigator.onLine) {
            throw new Error('No network connection available');
        }

        await this.syncDataType(dataType);
        console.log(`[OfflineSyncManager] Force sync completed for ${dataType}`);
    }

    /**
     * 동기화 큐 초기화
     */
    clearSyncQueue() {
        this.syncQueue.clear();
        this.saveSyncQueue();
        console.log('[OfflineSyncManager] Sync queue cleared');
    }

    /**
     * 충돌 큐 초기화
     */
    clearConflictQueue() {
        this.conflictQueue = [];
        console.log('[OfflineSyncManager] Conflict queue cleared');
    }

    /**
     * 정리
     */
    destroy() {
        // 진행 중인 동기화 중단
        this.syncInProgress = false;
        
        // 큐 저장
        this.saveSyncQueue();
        
        // 큐 초기화
        this.syncQueue.clear();
        this.conflictQueue = [];
        this.syncHistory = [];

        console.log('[OfflineSyncManager] Offline sync manager destroyed');
    }
}

// 전역으로 내보내기
window.OfflineSyncManager = OfflineSyncManager;

// 자동 초기화
window.addEventListener('DOMContentLoaded', () => {
    if (window.oneSquareConfig?.enableOfflineSync !== false) {
        window.offlineSyncManager = new OfflineSyncManager();
    }
});