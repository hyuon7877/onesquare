/**
 * OneSquare PWA - IndexedDB 오프라인 저장소 관리
 * 
 * 오프라인 데이터 저장, 동기화, 검색 기능 제공
 */

class OfflineDatabase {
    constructor() {
        this.dbName = 'OneSquareOfflineDB';
        this.version = 1;
        this.db = null;
        this.stores = {
            userData: 'user_data',
            notionPages: 'notion_pages',
            notionDatabases: 'notion_databases',
            offlineQueue: 'offline_queue',
            settings: 'settings',
            syncLog: 'sync_log'
        };
    }

    /**
     * 데이터베이스 초기화 및 연결
     */
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);

            request.onerror = () => {
                console.error('IndexedDB 초기화 실패:', request.error);
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                console.log('IndexedDB 초기화 완료');
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                this.createStores(db);
            };
        });
    }

    /**
     * 오브젝트 스토어 생성
     */
    createStores(db) {
        // 사용자 데이터 스토어
        if (!db.objectStoreNames.contains(this.stores.userData)) {
            const userStore = db.createObjectStore(this.stores.userData, { 
                keyPath: 'id', 
                autoIncrement: true 
            });
            userStore.createIndex('userId', 'userId', { unique: false });
            userStore.createIndex('lastModified', 'lastModified', { unique: false });
        }

        // Notion 페이지 스토어
        if (!db.objectStoreNames.contains(this.stores.notionPages)) {
            const pagesStore = db.createObjectStore(this.stores.notionPages, { 
                keyPath: 'pageId' 
            });
            pagesStore.createIndex('databaseId', 'databaseId', { unique: false });
            pagesStore.createIndex('title', 'title', { unique: false });
            pagesStore.createIndex('lastEditedTime', 'lastEditedTime', { unique: false });
            pagesStore.createIndex('status', 'status', { unique: false });
        }

        // Notion 데이터베이스 스토어
        if (!db.objectStoreNames.contains(this.stores.notionDatabases)) {
            const dbStore = db.createObjectStore(this.stores.notionDatabases, { 
                keyPath: 'databaseId' 
            });
            dbStore.createIndex('title', 'title', { unique: false });
            dbStore.createIndex('lastEditedTime', 'lastEditedTime', { unique: false });
        }

        // 오프라인 큐 스토어
        if (!db.objectStoreNames.contains(this.stores.offlineQueue)) {
            const queueStore = db.createObjectStore(this.stores.offlineQueue, { 
                keyPath: 'id', 
                autoIncrement: true 
            });
            queueStore.createIndex('timestamp', 'timestamp', { unique: false });
            queueStore.createIndex('type', 'type', { unique: false });
            queueStore.createIndex('priority', 'priority', { unique: false });
        }

        // 설정 스토어
        if (!db.objectStoreNames.contains(this.stores.settings)) {
            db.createObjectStore(this.stores.settings, { keyPath: 'key' });
        }

        // 동기화 로그 스토어
        if (!db.objectStoreNames.contains(this.stores.syncLog)) {
            const syncStore = db.createObjectStore(this.stores.syncLog, { 
                keyPath: 'id', 
                autoIncrement: true 
            });
            syncStore.createIndex('timestamp', 'timestamp', { unique: false });
            syncStore.createIndex('status', 'status', { unique: false });
        }
    }

    /**
     * 데이터 저장
     */
    async saveData(storeName, data) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            
            // 타임스탬프 추가
            data.lastModified = new Date().toISOString();
            
            const request = store.put(data);
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * 데이터 조회
     */
    async getData(storeName, key) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.get(key);
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * 모든 데이터 조회
     */
    async getAllData(storeName) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.getAll();
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * 인덱스를 사용한 데이터 조회
     */
    async getDataByIndex(storeName, indexName, value) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const index = store.index(indexName);
            const request = index.getAll(value);
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * 데이터 삭제
     */
    async deleteData(storeName, key) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.delete(key);
            
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Notion 페이지 저장
     */
    async saveNotionPage(pageData) {
        const processedData = {
            pageId: pageData.id,
            databaseId: pageData.parent?.database_id || null,
            title: this.extractTitle(pageData.properties),
            properties: pageData.properties,
            content: pageData.content || null,
            lastEditedTime: pageData.last_edited_time,
            createdTime: pageData.created_time,
            status: 'synced',
            offline: false
        };
        
        return this.saveData(this.stores.notionPages, processedData);
    }

    /**
     * 오프라인 큐에 작업 추가
     */
    async addToOfflineQueue(operation) {
        const queueItem = {
            type: operation.type, // 'create', 'update', 'delete'
            endpoint: operation.endpoint,
            data: operation.data,
            method: operation.method || 'POST',
            timestamp: new Date().toISOString(),
            priority: operation.priority || 'normal', // 'high', 'normal', 'low'
            retryCount: 0,
            maxRetries: 3
        };
        
        return this.saveData(this.stores.offlineQueue, queueItem);
    }

    /**
     * 오프라인 큐 조회
     */
    async getOfflineQueue() {
        const queue = await this.getAllData(this.stores.offlineQueue);
        return queue.sort((a, b) => {
            // 우선순위별 정렬
            const priorityOrder = { 'high': 3, 'normal': 2, 'low': 1 };
            if (priorityOrder[a.priority] !== priorityOrder[b.priority]) {
                return priorityOrder[b.priority] - priorityOrder[a.priority];
            }
            // 타임스탬프별 정렬
            return new Date(a.timestamp) - new Date(b.timestamp);
        });
    }

    /**
     * 오프라인 큐에서 작업 제거
     */
    async removeFromOfflineQueue(id) {
        return this.deleteData(this.stores.offlineQueue, id);
    }

    /**
     * 동기화 로그 기록
     */
    async logSync(operation, status, details = null) {
        const logEntry = {
            operation: operation,
            status: status, // 'success', 'failed', 'pending'
            details: details,
            timestamp: new Date().toISOString()
        };
        
        return this.saveData(this.stores.syncLog, logEntry);
    }

    /**
     * 검색 기능
     */
    async searchPages(query) {
        const pages = await this.getAllData(this.stores.notionPages);
        const lowercaseQuery = query.toLowerCase();
        
        return pages.filter(page => {
            const title = page.title?.toLowerCase() || '';
            const content = JSON.stringify(page.properties).toLowerCase();
            return title.includes(lowercaseQuery) || content.includes(lowercaseQuery);
        });
    }

    /**
     * 데이터베이스 정리 (오래된 데이터 삭제)
     */
    async cleanup(daysToKeep = 30) {
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - daysToKeep);
        const cutoffISO = cutoffDate.toISOString();
        
        // 오래된 동기화 로그 삭제
        const syncLogs = await this.getAllData(this.stores.syncLog);
        for (const log of syncLogs) {
            if (log.timestamp < cutoffISO) {
                await this.deleteData(this.stores.syncLog, log.id);
            }
        }
        
        console.log(`${daysToKeep}일 이전 데이터 정리 완료`);
    }

    /**
     * 저장소 통계
     */
    async getStats() {
        const stats = {};
        
        for (const [key, storeName] of Object.entries(this.stores)) {
            const data = await this.getAllData(storeName);
            stats[key] = {
                count: data.length,
                size: new Blob([JSON.stringify(data)]).size
            };
        }
        
        return stats;
    }

    /**
     * 설정 저장/조회
     */
    async setSetting(key, value) {
        return this.saveData(this.stores.settings, { key, value });
    }
    
    async getSetting(key, defaultValue = null) {
        const setting = await this.getData(this.stores.settings, key);
        return setting ? setting.value : defaultValue;
    }

    /**
     * 제목 추출 헬퍼 함수
     */
    extractTitle(properties) {
        for (const [key, prop] of Object.entries(properties)) {
            if (prop.type === 'title' && prop.title.length > 0) {
                return prop.title[0].plain_text;
            }
        }
        return 'Untitled';
    }

    /**
     * 데이터베이스 연결 종료
     */
    close() {
        if (this.db) {
            this.db.close();
            this.db = null;
        }
    }
}

// 전역 인스턴스 생성
const offlineDB = new OfflineDatabase();

// 초기화
offlineDB.init().catch(error => {
    console.error('OfflineDatabase 초기화 실패:', error);
});

export default offlineDB;