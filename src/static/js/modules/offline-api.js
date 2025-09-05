/**
 * OneSquare PWA - 오프라인 API 래퍼
 * 
 * 클라이언트에서 오프라인 기능을 쉽게 사용할 수 있는 API 제공
 */

import offlineDB from './offline-database.js';
import syncManager from './offline-sync.js';

class OfflineAPI {
    constructor() {
        this.isInitialized = false;
        this.serviceWorker = null;
        this.setupServiceWorkerConnection();
    }

    /**
     * Service Worker 연결 설정
     */
    async setupServiceWorkerConnection() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.ready;
                this.serviceWorker = registration.active;
                console.log('[OfflineAPI] Service Worker connected');
            } catch (error) {
                console.error('[OfflineAPI] Service Worker connection failed:', error);
            }
        }
    }

    /**
     * 초기화
     */
    async init() {
        if (this.isInitialized) return;
        
        try {
            await offlineDB.init();
            this.isInitialized = true;
            console.log('[OfflineAPI] Initialized successfully');
        } catch (error) {
            console.error('[OfflineAPI] Initialization failed:', error);
            throw error;
        }
    }

    /**
     * Notion 페이지 생성 (오프라인 지원)
     */
    async createNotionPage(databaseId, properties, options = {}) {
        await this.ensureInitialized();
        
        const pageData = {
            parent: { database_id: databaseId },
            properties: properties,
            ...options
        };

        if (navigator.onLine && !options.forceOffline) {
            try {
                const response = await fetch('/api/notion/pages/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify(pageData)
                });

                if (response.ok) {
                    const result = await response.json();
                    await offlineDB.saveNotionPage(result);
                    return { success: true, data: result, source: 'online' };
                }
            } catch (error) {
                console.warn('[OfflineAPI] Online create failed, queuing for offline:', error);
            }
        }

        // 오프라인 모드 또는 온라인 실패 시
        const tempId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const offlinePageData = {
            pageId: tempId,
            databaseId: databaseId,
            title: this.extractTitleFromProperties(properties),
            properties: properties,
            lastEditedTime: new Date().toISOString(),
            createdTime: new Date().toISOString(),
            status: 'pending',
            offline: true
        };

        await offlineDB.saveNotionPage(offlinePageData);
        await syncManager.addOfflineOperation({
            type: 'create',
            endpoint: '/api/notion/pages/',
            method: 'POST',
            data: pageData,
            priority: 'normal',
            tempId: tempId
        });

        return { success: true, data: offlinePageData, source: 'offline' };
    }

    /**
     * Notion 페이지 업데이트 (오프라인 지원)
     */
    async updateNotionPage(pageId, properties, options = {}) {
        await this.ensureInitialized();
        
        const updateData = { properties };

        if (navigator.onLine && !options.forceOffline) {
            try {
                const response = await fetch(`/api/notion/pages/${pageId}/`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken()
                    },
                    body: JSON.stringify(updateData)
                });

                if (response.ok) {
                    const result = await response.json();
                    await offlineDB.saveNotionPage(result);
                    return { success: true, data: result, source: 'online' };
                }
            } catch (error) {
                console.warn('[OfflineAPI] Online update failed, queuing for offline:', error);
            }
        }

        // 오프라인 업데이트
        const localPage = await offlineDB.getData(offlineDB.stores.notionPages, pageId);
        if (localPage) {
            localPage.properties = { ...localPage.properties, ...properties };
            localPage.lastEditedTime = new Date().toISOString();
            localPage.offline = true;
            localPage.status = 'pending';
            
            await offlineDB.saveNotionPage(localPage);
        }

        await syncManager.addOfflineOperation({
            type: 'update',
            endpoint: `/api/notion/pages/${pageId}/`,
            method: 'PATCH',
            data: updateData,
            priority: 'normal'
        });

        return { success: true, data: localPage, source: 'offline' };
    }

    /**
     * Notion 페이지 조회 (오프라인 우선)
     */
    async getNotionPage(pageId, options = {}) {
        await this.ensureInitialized();
        
        // 로컬에서 먼저 조회
        const localPage = await offlineDB.getData(offlineDB.stores.notionPages, pageId);
        
        if (options.offlineOnly || !navigator.onLine) {
            return localPage ? { success: true, data: localPage, source: 'offline' } 
                             : { success: false, error: 'Page not found offline' };
        }

        // 온라인 상태에서 최신 데이터 가져오기
        try {
            const response = await fetch(`/api/notion/pages/${pageId}/`);
            if (response.ok) {
                const result = await response.json();
                await offlineDB.saveNotionPage(result);
                return { success: true, data: result, source: 'online' };
            }
        } catch (error) {
            console.warn('[OfflineAPI] Online fetch failed, using cached data:', error);
        }

        // 온라인 실패 시 로컬 데이터 반환
        return localPage ? { success: true, data: localPage, source: 'offline' } 
                         : { success: false, error: 'Page not found' };
    }

    /**
     * 데이터베이스 쿼리 (오프라인 지원)
     */
    async queryDatabase(databaseId, filter = {}, options = {}) {
        await this.ensureInitialized();
        
        if (options.offlineOnly || !navigator.onLine) {
            const localPages = await offlineDB.getDataByIndex(
                offlineDB.stores.notionPages, 
                'databaseId', 
                databaseId
            );
            return { success: true, data: { results: localPages }, source: 'offline' };
        }

        // 온라인 쿼리 시도
        try {
            const response = await fetch(`/api/notion/databases/${databaseId}/query/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(filter)
            });

            if (response.ok) {
                const result = await response.json();
                
                // 결과를 로컬에 저장
                for (const page of result.results || []) {
                    await offlineDB.saveNotionPage(page);
                }
                
                return { success: true, data: result, source: 'online' };
            }
        } catch (error) {
            console.warn('[OfflineAPI] Online query failed, using cached data:', error);
        }

        // 오프라인 폴백
        const localPages = await offlineDB.getDataByIndex(
            offlineDB.stores.notionPages, 
            'databaseId', 
            databaseId
        );
        return { success: true, data: { results: localPages }, source: 'offline' };
    }

    /**
     * 페이지 검색
     */
    async searchPages(query, options = {}) {
        await this.ensureInitialized();
        
        if (options.offlineOnly || !navigator.onLine) {
            const results = await offlineDB.searchPages(query);
            return { success: true, data: results, source: 'offline' };
        }

        // 온라인 검색 (구현 예정)
        // 현재는 로컬 검색만 지원
        const results = await offlineDB.searchPages(query);
        return { success: true, data: results, source: 'offline' };
    }

    /**
     * 동기화 상태 확인
     */
    async getSyncStatus() {
        await this.ensureInitialized();
        
        const offlineQueue = await offlineDB.getOfflineQueue();
        const lastSync = await offlineDB.getSetting('last_sync_time');
        
        return {
            isOnline: navigator.onLine,
            pendingOperations: offlineQueue.length,
            lastSyncTime: lastSync,
            syncInProgress: syncManager.syncInProgress
        };
    }

    /**
     * 수동 동기화 실행
     */
    async performSync() {
        if (!navigator.onLine) {
            throw new Error('Cannot sync while offline');
        }
        
        await syncManager.syncWithNotion();
        await offlineDB.setSetting('last_sync_time', new Date().toISOString());
        
        return { success: true, message: 'Sync completed' };
    }

    /**
     * 오프라인 통계
     */
    async getOfflineStats() {
        await this.ensureInitialized();
        
        const stats = await offlineDB.getStats();
        const syncStatus = await this.getSyncStatus();
        
        return {
            storage: stats,
            sync: syncStatus,
            lastCleanup: await offlineDB.getSetting('last_cleanup_time')
        };
    }

    /**
     * Service Worker에 메시지 전송
     */
    async sendMessageToSW(action, data = null) {
        if (!this.serviceWorker) {
            await this.setupServiceWorkerConnection();
        }

        return new Promise((resolve, reject) => {
            const messageChannel = new MessageChannel();
            
            messageChannel.port1.onmessage = (event) => {
                resolve(event.data);
            };

            if (this.serviceWorker) {
                this.serviceWorker.postMessage(
                    { action, data },
                    [messageChannel.port2]
                );
            } else {
                reject(new Error('Service Worker not available'));
            }

            // 5초 타임아웃
            setTimeout(() => {
                reject(new Error('Service Worker response timeout'));
            }, 5000);
        });
    }

    /**
     * 캐시 정리
     */
    async clearCache(type = null) {
        return await this.sendMessageToSW('CLEAR_CACHE', { type });
    }

    /**
     * 오프라인 데이터 정리
     */
    async clearOfflineData(type = null) {
        await this.ensureInitialized();
        
        if (type) {
            const storeName = offlineDB.stores[type];
            if (storeName) {
                const allData = await offlineDB.getAllData(storeName);
                for (const item of allData) {
                    await offlineDB.deleteData(storeName, item.id || item.pageId || item.key);
                }
            }
        } else {
            await offlineDB.cleanup(0); // 모든 데이터 삭제
        }
        
        await offlineDB.setSetting('last_cleanup_time', new Date().toISOString());
        return { success: true, message: 'Offline data cleared' };
    }

    /**
     * 네트워크 상태 리스너 추가
     */
    addNetworkListener(callback) {
        const onlineHandler = () => callback(true);
        const offlineHandler = () => callback(false);
        
        window.addEventListener('online', onlineHandler);
        window.addEventListener('offline', offlineHandler);
        
        // 리스너 제거 함수 반환
        return () => {
            window.removeEventListener('online', onlineHandler);
            window.removeEventListener('offline', offlineHandler);
        };
    }

    /**
     * 헬퍼 메서드들
     */
    async ensureInitialized() {
        if (!this.isInitialized) {
            await this.init();
        }
    }

    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    extractTitleFromProperties(properties) {
        for (const [key, prop] of Object.entries(properties)) {
            if (prop.type === 'title' && prop.title?.length > 0) {
                return prop.title[0].plain_text || prop.title[0].text?.content || 'Untitled';
            }
        }
        return 'Untitled';
    }
}

// 전역 인스턴스
const offlineAPI = new OfflineAPI();

// 자동 초기화
offlineAPI.init().catch(error => {
    console.error('[OfflineAPI] Auto initialization failed:', error);
});

export default offlineAPI;