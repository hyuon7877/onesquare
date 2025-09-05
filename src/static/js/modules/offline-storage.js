/**
 * OneSquare - 오프라인 데이터 저장 및 동기화 모듈
 * 
 * 네트워크 연결이 불안정한 현장에서도 안정적인 업무 시간 기록
 */

class OfflineStorage {
    constructor() {
        this.dbName = 'OneSquareOfflineDB';
        this.version = 1;
        this.db = null;
        this.syncQueue = [];
        this.isOnline = navigator.onLine;
        
        this.init();
        this.setupEventListeners();
    }

    /**
     * IndexedDB 초기화
     */
    async init() {
        try {
            this.db = await this.openDatabase();
            console.log('[OfflineStorage] Database initialized successfully');
            
            // 페이지 로드 시 자동 동기화 시도
            if (this.isOnline) {
                setTimeout(() => this.syncPendingData(), 2000);
            }
        } catch (error) {
            console.error('[OfflineStorage] Database initialization failed:', error);
        }
    }

    /**
     * 네트워크 상태 이벤트 리스너 설정
     */
    setupEventListeners() {
        // 온라인 상태 변경 감지
        window.addEventListener('online', () => {
            console.log('[OfflineStorage] Network connection restored');
            this.isOnline = true;
            this.syncPendingData();
        });

        window.addEventListener('offline', () => {
            console.log('[OfflineStorage] Network connection lost - switching to offline mode');
            this.isOnline = false;
        });

        // 페이지 언로드 전 마지막 동기화 시도
        window.addEventListener('beforeunload', () => {
            if (this.isOnline && this.syncQueue.length > 0) {
                this.syncPendingData();
            }
        });
    }

    /**
     * IndexedDB 데이터베이스 열기
     */
    openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);

            request.onerror = () => {
                reject(new Error('Failed to open database'));
            };

            request.onsuccess = (event) => {
                resolve(event.target.result);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // 시간 기록 저장소
                if (!db.objectStoreNames.contains('timeRecords')) {
                    const timeStore = db.createObjectStore('timeRecords', { 
                        keyPath: 'localId', 
                        autoIncrement: true 
                    });
                    timeStore.createIndex('sessionId', 'sessionId', { unique: false });
                    timeStore.createIndex('timestamp', 'timestamp', { unique: false });
                    timeStore.createIndex('syncStatus', 'syncStatus', { unique: false });
                }

                // 위치 데이터 저장소
                if (!db.objectStoreNames.contains('locationData')) {
                    const locationStore = db.createObjectStore('locationData', { 
                        keyPath: 'localId', 
                        autoIncrement: true 
                    });
                    locationStore.createIndex('sessionId', 'sessionId', { unique: false });
                    locationStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                // 동기화 큐 저장소
                if (!db.objectStoreNames.contains('syncQueue')) {
                    const syncStore = db.createObjectStore('syncQueue', { 
                        keyPath: 'localId', 
                        autoIncrement: true 
                    });
                    syncStore.createIndex('type', 'type', { unique: false });
                    syncStore.createIndex('priority', 'priority', { unique: false });
                }
            };
        });
    }

    /**
     * 업무 시간 기록 저장 (오프라인/온라인 모두 지원)
     */
    async saveTimeRecord(sessionData) {
        const record = {
            sessionId: sessionData.sessionId || this.generateSessionId(),
            userId: sessionData.userId,
            siteId: sessionData.siteId,
            action: sessionData.action, // 'start', 'end', 'pause', 'resume'
            timestamp: new Date().toISOString(),
            location: {
                latitude: sessionData.latitude,
                longitude: sessionData.longitude,
                accuracy: sessionData.accuracy
            },
            verified: sessionData.locationVerified || false,
            syncStatus: this.isOnline ? 'pending' : 'offline',
            createdAt: Date.now()
        };

        try {
            // 로컬에 저장
            const localId = await this.saveToIndexedDB('timeRecords', record);
            record.localId = localId;

            // 온라인이면 즉시 동기화 시도
            if (this.isOnline) {
                this.addToSyncQueue({
                    type: 'timeRecord',
                    data: record,
                    priority: 1,
                    attempts: 0
                });
            }

            console.log(`[OfflineStorage] Time record saved locally: ${record.action}`);
            return { success: true, localId: localId, data: record };

        } catch (error) {
            console.error('[OfflineStorage] Failed to save time record:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * 위치 데이터 저장
     */
    async saveLocationData(locationData) {
        const record = {
            sessionId: locationData.sessionId,
            latitude: locationData.latitude,
            longitude: locationData.longitude,
            accuracy: locationData.accuracy,
            speed: locationData.speed,
            heading: locationData.heading,
            timestamp: new Date().toISOString(),
            createdAt: Date.now()
        };

        try {
            const localId = await this.saveToIndexedDB('locationData', record);
            return { success: true, localId: localId };
        } catch (error) {
            console.error('[OfflineStorage] Failed to save location data:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * IndexedDB에 데이터 저장
     */
    saveToIndexedDB(storeName, data) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.add(data);

            request.onsuccess = () => {
                resolve(request.result);
            };

            request.onerror = () => {
                reject(new Error(`Failed to save to ${storeName}`));
            };
        });
    }

    /**
     * 동기화 큐에 항목 추가
     */
    async addToSyncQueue(item) {
        const queueItem = {
            ...item,
            createdAt: Date.now(),
            lastAttempt: null
        };

        try {
            await this.saveToIndexedDB('syncQueue', queueItem);
            this.syncQueue.push(queueItem);
            
            // 즉시 동기화 시도
            setTimeout(() => this.processSyncQueue(), 1000);
        } catch (error) {
            console.error('[OfflineStorage] Failed to add to sync queue:', error);
        }
    }

    /**
     * 대기 중인 데이터 동기화
     */
    async syncPendingData() {
        if (!this.isOnline) {
            console.log('[OfflineStorage] Cannot sync - offline mode');
            return;
        }

        console.log('[OfflineStorage] Starting data synchronization...');

        try {
            // 동기화 큐에서 대기 중인 항목들 가져오기
            const pendingItems = await this.getPendingItemsFromQueue();
            
            if (pendingItems.length === 0) {
                console.log('[OfflineStorage] No items to sync');
                return;
            }

            console.log(`[OfflineStorage] Found ${pendingItems.length} items to sync`);

            // 우선순위별로 정렬하여 동기화
            pendingItems.sort((a, b) => a.priority - b.priority);

            for (const item of pendingItems) {
                await this.syncSingleItem(item);
            }

        } catch (error) {
            console.error('[OfflineStorage] Sync process failed:', error);
        }
    }

    /**
     * 개별 항목 동기화
     */
    async syncSingleItem(item) {
        try {
            let endpoint = '';
            let method = 'POST';

            switch (item.type) {
                case 'timeRecord':
                    endpoint = '/api/field-report/time-tracking/';
                    break;
                default:
                    console.warn(`[OfflineStorage] Unknown sync type: ${item.type}`);
                    return;
            }

            const response = await fetch(endpoint, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(item.data)
            });

            if (response.ok) {
                const result = await response.json();
                
                // 동기화 성공 - 큐에서 제거
                await this.removeFromSyncQueue(item.localId);
                
                // 원본 레코드의 동기화 상태 업데이트
                await this.updateSyncStatus(item.data.localId, 'synced', result.id);
                
                console.log(`[OfflineStorage] Successfully synced ${item.type}:`, result.id);
                
            } else {
                // 동기화 실패 - 재시도 카운트 증가
                item.attempts = (item.attempts || 0) + 1;
                item.lastAttempt = Date.now();
                
                if (item.attempts >= 3) {
                    console.error(`[OfflineStorage] Max retry attempts reached for ${item.type}`);
                    await this.markAsFailed(item);
                } else {
                    console.warn(`[OfflineStorage] Sync failed, will retry. Attempt ${item.attempts}/3`);
                }
            }

        } catch (error) {
            console.error(`[OfflineStorage] Error syncing ${item.type}:`, error);
            item.attempts = (item.attempts || 0) + 1;
            item.lastAttempt = Date.now();
        }
    }

    /**
     * 동기화 큐 처리
     */
    async processSyncQueue() {
        if (!this.isOnline || this.syncQueue.length === 0) {
            return;
        }

        // 현재 큐의 복사본 생성
        const currentQueue = [...this.syncQueue];
        this.syncQueue = [];

        for (const item of currentQueue) {
            await this.syncSingleItem(item);
        }
    }

    /**
     * 대기 중인 동기화 항목 조회
     */
    getPendingItemsFromQueue() {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['syncQueue'], 'readonly');
            const store = transaction.objectStore('syncQueue');
            const request = store.getAll();

            request.onsuccess = () => {
                resolve(request.result);
            };

            request.onerror = () => {
                reject(new Error('Failed to get pending items'));
            };
        });
    }

    /**
     * 동기화 큐에서 항목 제거
     */
    removeFromSyncQueue(localId) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            const request = store.delete(localId);

            request.onsuccess = () => {
                resolve();
            };

            request.onerror = () => {
                reject(new Error('Failed to remove from sync queue'));
            };
        });
    }

    /**
     * 동기화 상태 업데이트
     */
    updateSyncStatus(localId, status, serverId = null) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['timeRecords'], 'readwrite');
            const store = transaction.objectStore('timeRecords');
            const request = store.get(localId);

            request.onsuccess = () => {
                const record = request.result;
                if (record) {
                    record.syncStatus = status;
                    if (serverId) {
                        record.serverId = serverId;
                    }
                    record.syncedAt = new Date().toISOString();
                    
                    const updateRequest = store.put(record);
                    updateRequest.onsuccess = () => resolve();
                    updateRequest.onerror = () => reject();
                }
            };
        });
    }

    /**
     * 세션 ID 생성
     */
    generateSessionId() {
        return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * CSRF 토큰 가져오기
     */
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    /**
     * 실패한 항목 처리
     */
    async markAsFailed(item) {
        try {
            await this.updateSyncStatus(item.data.localId, 'failed');
            await this.removeFromSyncQueue(item.localId);
            console.error(`[OfflineStorage] Item marked as failed:`, item);
        } catch (error) {
            console.error('[OfflineStorage] Failed to mark item as failed:', error);
        }
    }

    /**
     * 오프라인 데이터 통계
     */
    async getOfflineStats() {
        const timeRecords = await this.getAllFromStore('timeRecords');
        const locationData = await this.getAllFromStore('locationData');
        const syncQueue = await this.getAllFromStore('syncQueue');

        const stats = {
            totalTimeRecords: timeRecords.length,
            syncedRecords: timeRecords.filter(r => r.syncStatus === 'synced').length,
            pendingRecords: timeRecords.filter(r => r.syncStatus === 'pending').length,
            failedRecords: timeRecords.filter(r => r.syncStatus === 'failed').length,
            locationPoints: locationData.length,
            queuedItems: syncQueue.length,
            lastSync: this.getLastSyncTime(timeRecords)
        };

        return stats;
    }

    /**
     * 스토어에서 모든 데이터 가져오기
     */
    getAllFromStore(storeName) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.getAll();

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(new Error(`Failed to get data from ${storeName}`));
        });
    }

    /**
     * 마지막 동기화 시간 계산
     */
    getLastSyncTime(records) {
        const syncedRecords = records.filter(r => r.syncedAt);
        if (syncedRecords.length === 0) return null;
        
        return syncedRecords
            .map(r => new Date(r.syncedAt))
            .sort((a, b) => b - a)[0];
    }

    /**
     * 데이터베이스 정리 (오래된 데이터 삭제)
     */
    async cleanupOldData(daysToKeep = 30) {
        const cutoffTime = Date.now() - (daysToKeep * 24 * 60 * 60 * 1000);
        
        try {
            await this.cleanupStore('timeRecords', cutoffTime);
            await this.cleanupStore('locationData', cutoffTime);
            console.log(`[OfflineStorage] Cleaned up data older than ${daysToKeep} days`);
        } catch (error) {
            console.error('[OfflineStorage] Failed to cleanup old data:', error);
        }
    }

    /**
     * 특정 스토어에서 오래된 데이터 삭제
     */
    cleanupStore(storeName, cutoffTime) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.getAll();

            request.onsuccess = () => {
                const records = request.result;
                const toDelete = records.filter(record => 
                    record.createdAt < cutoffTime && 
                    record.syncStatus === 'synced'
                );

                let deleteCount = 0;
                toDelete.forEach(record => {
                    const deleteRequest = store.delete(record.localId);
                    deleteRequest.onsuccess = () => {
                        deleteCount++;
                        if (deleteCount === toDelete.length) {
                            resolve();
                        }
                    };
                });

                if (toDelete.length === 0) {
                    resolve();
                }
            };

            request.onerror = () => reject();
        });
    }
}

// 전역 인스턴스 생성
const offlineStorage = new OfflineStorage();

// 모듈 내보내기
window.OfflineStorage = OfflineStorage;
window.offlineStorage = offlineStorage;