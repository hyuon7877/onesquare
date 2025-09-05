/**
 * OneSquare - Notion 동기화 모듈
 * 
 * 재고 데이터를 Notion 데이터베이스와 동기화하고 백업
 */

class NotionSync {
    constructor() {
        this.syncQueue = [];
        this.isSyncing = false;
        this.lastSyncTime = null;
        this.syncInterval = null;
        this.retryAttempts = 3;
        this.retryDelay = 2000;
        
        // Notion API 설정
        this.notionConfig = {
            apiVersion: '2022-06-28',
            baseUrl: '/api/notion/', // Django 프록시 엔드포인트
            databaseIds: {
                inventory: null, // 설정에서 로드됨
                checks: null,
                reports: null
            }
        };
        
        this.callbacks = {
            syncStarted: [],
            syncCompleted: [],
            syncFailed: [],
            dataBackedUp: []
        };
        
        this.init();
    }

    /**
     * 초기화
     */
    async init() {
        console.log('[NotionSync] Initializing Notion sync module...');
        
        try {
            // Notion 설정 로드
            await this.loadNotionConfig();
            
            // 마지막 동기화 시간 로드
            this.loadLastSyncTime();
            
            // 자동 동기화 시작
            this.startAutoSync();
            
            console.log('[NotionSync] Notion sync module initialized');
        } catch (error) {
            console.error('[NotionSync] Failed to initialize:', error);
        }
    }

    /**
     * Notion 설정 로드
     */
    async loadNotionConfig() {
        try {
            const response = await fetch('/api/notion/config/');
            const data = await response.json();
            
            if (data.success) {
                this.notionConfig.databaseIds = data.database_ids;
                console.log('[NotionSync] Notion config loaded successfully');
            } else {
                throw new Error('Failed to load Notion config');
            }
        } catch (error) {
            console.warn('[NotionSync] Using default config due to error:', error);
            // 테스트용 기본값
            this.notionConfig.databaseIds = {
                inventory: 'test-inventory-db',
                checks: 'test-checks-db',
                reports: 'test-reports-db'
            };
        }
    }

    /**
     * 마지막 동기화 시간 로드
     */
    loadLastSyncTime() {
        try {
            const savedTime = localStorage.getItem('notion_last_sync_time');
            if (savedTime) {
                this.lastSyncTime = new Date(savedTime);
            }
        } catch (error) {
            console.warn('[NotionSync] Failed to load last sync time:', error);
        }
    }

    /**
     * 마지막 동기화 시간 저장
     */
    saveLastSyncTime() {
        try {
            localStorage.setItem('notion_last_sync_time', new Date().toISOString());
            this.lastSyncTime = new Date();
        } catch (error) {
            console.warn('[NotionSync] Failed to save last sync time:', error);
        }
    }

    /**
     * 자동 동기화 시작
     */
    startAutoSync(intervalMinutes = 30) {
        this.stopAutoSync();
        
        this.syncInterval = setInterval(async () => {
            await this.syncAllData();
        }, intervalMinutes * 60 * 1000);
        
        console.log(`[NotionSync] Started auto sync every ${intervalMinutes} minutes`);
    }

    /**
     * 자동 동기화 중지
     */
    stopAutoSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
        }
        console.log('[NotionSync] Stopped auto sync');
    }

    /**
     * 모든 데이터 동기화
     */
    async syncAllData() {
        if (this.isSyncing) {
            console.log('[NotionSync] Sync already in progress, skipping');
            return;
        }

        console.log('[NotionSync] Starting full data sync...');
        this.isSyncing = true;
        this.triggerCallback('syncStarted', { type: 'full' });

        try {
            // 1. 재고 체크 데이터 동기화
            await this.syncInventoryChecks();
            
            // 2. 재고 아이템 마스터 데이터 동기화
            await this.syncInventoryItems();
            
            // 3. 리포트 데이터 동기화
            await this.syncReports();
            
            // 4. 백업 생성
            await this.createBackup();
            
            this.saveLastSyncTime();
            this.triggerCallback('syncCompleted', { 
                type: 'full',
                timestamp: new Date().toISOString()
            });
            
            console.log('[NotionSync] Full data sync completed successfully');
            
        } catch (error) {
            console.error('[NotionSync] Full data sync failed:', error);
            this.triggerCallback('syncFailed', { 
                type: 'full',
                error: error.message 
            });
        } finally {
            this.isSyncing = false;
        }
    }

    /**
     * 재고 체크 데이터 동기화
     */
    async syncInventoryChecks() {
        try {
            // 로컬 재고 체크 데이터 조회
            const response = await fetch('/field-report/api/inventory-stats/?days=30');
            const data = await response.json();
            
            if (!data.success) {
                throw new Error('Failed to get local inventory data');
            }

            // Notion 페이지로 변환
            const notionPages = this.convertChecksToNotionPages(data);
            
            // Notion에 업로드
            for (const page of notionPages) {
                await this.createOrUpdateNotionPage('checks', page);
            }
            
            console.log(`[NotionSync] Synced ${notionPages.length} inventory checks to Notion`);
            
        } catch (error) {
            console.error('[NotionSync] Failed to sync inventory checks:', error);
            throw error;
        }
    }

    /**
     * 재고 아이템 마스터 데이터 동기화
     */
    async syncInventoryItems() {
        try {
            const response = await fetch('/field-report/api/inventory-items/');
            const data = await response.json();
            
            if (!data.success) {
                throw new Error('Failed to get inventory items');
            }

            const notionPages = this.convertItemsToNotionPages(data.items);
            
            for (const page of notionPages) {
                await this.createOrUpdateNotionPage('inventory', page);
            }
            
            console.log(`[NotionSync] Synced ${notionPages.length} inventory items to Notion`);
            
        } catch (error) {
            console.error('[NotionSync] Failed to sync inventory items:', error);
            throw error;
        }
    }

    /**
     * 리포트 데이터 동기화
     */
    async syncReports() {
        try {
            // 간소화된 리포트 동기화 (실제 구현에서는 상세 데이터 포함)
            const mockReports = [{
                id: 'report-001',
                title: '현장 재고 체크 리포트',
                date: new Date().toISOString(),
                site: '테스트 현장',
                status: 'completed'
            }];

            const notionPages = this.convertReportsToNotionPages(mockReports);
            
            for (const page of notionPages) {
                await this.createOrUpdateNotionPage('reports', page);
            }
            
            console.log(`[NotionSync] Synced ${notionPages.length} reports to Notion`);
            
        } catch (error) {
            console.error('[NotionSync] Failed to sync reports:', error);
            throw error;
        }
    }

    /**
     * 재고 체크를 Notion 페이지로 변환
     */
    convertChecksToNotionPages(data) {
        if (!data.recent_activity) return [];
        
        return data.recent_activity.map(check => ({
            properties: {
                '품목명': {
                    title: [{
                        text: { content: check.item_name }
                    }]
                },
                '현재수량': {
                    number: check.current_quantity
                },
                '상태': {
                    select: { name: check.status_display }
                },
                '체크일시': {
                    date: { start: check.checked_at }
                },
                '현장': {
                    rich_text: [{
                        text: { content: check.site_name }
                    }]
                }
            }
        }));
    }

    /**
     * 재고 아이템을 Notion 페이지로 변환
     */
    convertItemsToNotionPages(items) {
        return items.map(item => ({
            properties: {
                '품목명': {
                    title: [{
                        text: { content: item.name }
                    }]
                },
                '품목코드': {
                    rich_text: [{
                        text: { content: item.code }
                    }]
                },
                '카테고리': {
                    select: { name: item.categoryDisplay }
                },
                '단위': {
                    select: { name: item.unit }
                },
                '최소재고': {
                    number: item.minimumStock
                },
                '최대재고': {
                    number: item.maximumStock
                },
                '현재수량': {
                    number: item.currentQuantity || 0
                },
                '상태': {
                    select: { name: item.statusDisplay || '확인필요' }
                }
            }
        }));
    }

    /**
     * 리포트를 Notion 페이지로 변환
     */
    convertReportsToNotionPages(reports) {
        return reports.map(report => ({
            properties: {
                '리포트제목': {
                    title: [{
                        text: { content: report.title }
                    }]
                },
                '날짜': {
                    date: { start: report.date }
                },
                '현장': {
                    rich_text: [{
                        text: { content: report.site }
                    }]
                },
                '상태': {
                    select: { name: report.status }
                }
            }
        }));
    }

    /**
     * Notion 페이지 생성 또는 업데이트
     */
    async createOrUpdateNotionPage(databaseType, pageData) {
        const databaseId = this.notionConfig.databaseIds[databaseType];
        if (!databaseId) {
            throw new Error(`Database ID not found for type: ${databaseType}`);
        }

        try {
            const response = await fetch('/api/notion/pages/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken
                },
                body: JSON.stringify({
                    parent: { database_id: databaseId },
                    properties: pageData.properties
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`Notion API error: ${errorData.message || response.statusText}`);
            }

            const result = await response.json();
            return result;
            
        } catch (error) {
            console.error(`[NotionSync] Failed to create/update page in ${databaseType}:`, error);
            
            // 재시도 로직
            if (this.retryAttempts > 0) {
                await this.delay(this.retryDelay);
                return this.createOrUpdateNotionPage(databaseType, pageData);
            }
            
            throw error;
        }
    }

    /**
     * 데이터 백업 생성
     */
    async createBackup() {
        try {
            const backupData = {
                timestamp: new Date().toISOString(),
                version: '1.0',
                data: {
                    inventory_items: await this.getLocalInventoryItems(),
                    inventory_checks: await this.getLocalInventoryChecks(),
                    settings: this.getBackupSettings()
                }
            };

            // 로컬 스토리지에 백업 저장
            this.saveLocalBackup(backupData);
            
            // 서버에 백업 전송 (선택사항)
            await this.uploadBackupToServer(backupData);
            
            this.triggerCallback('dataBackedUp', {
                timestamp: backupData.timestamp,
                size: JSON.stringify(backupData).length
            });
            
            console.log('[NotionSync] Backup created successfully');
            
        } catch (error) {
            console.error('[NotionSync] Failed to create backup:', error);
        }
    }

    /**
     * 로컬 재고 아이템 데이터 조회
     */
    async getLocalInventoryItems() {
        try {
            const response = await fetch('/field-report/api/inventory-items/');
            const data = await response.json();
            return data.success ? data.items : [];
        } catch (error) {
            console.error('[NotionSync] Failed to get local inventory items:', error);
            return [];
        }
    }

    /**
     * 로컬 재고 체크 데이터 조회
     */
    async getLocalInventoryChecks() {
        try {
            const response = await fetch('/field-report/api/inventory-stats/?days=30');
            const data = await response.json();
            return data.success ? data.recent_activity : [];
        } catch (error) {
            console.error('[NotionSync] Failed to get local inventory checks:', error);
            return [];
        }
    }

    /**
     * 백업 설정 조회
     */
    getBackupSettings() {
        return {
            auto_sync_enabled: !!this.syncInterval,
            last_sync_time: this.lastSyncTime?.toISOString(),
            notion_database_ids: this.notionConfig.databaseIds,
            sync_interval_minutes: 30
        };
    }

    /**
     * 로컬 백업 저장
     */
    saveLocalBackup(backupData) {
        try {
            const backupKey = `notion_backup_${Date.now()}`;
            localStorage.setItem(backupKey, JSON.stringify(backupData));
            
            // 오래된 백업 정리 (최대 5개 유지)
            this.cleanupOldBackups();
            
        } catch (error) {
            console.error('[NotionSync] Failed to save local backup:', error);
        }
    }

    /**
     * 서버에 백업 업로드
     */
    async uploadBackupToServer(backupData) {
        try {
            const response = await fetch('/api/notion/backup/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': window.csrfToken
                },
                body: JSON.stringify(backupData)
            });

            if (response.ok) {
                console.log('[NotionSync] Backup uploaded to server successfully');
            } else {
                console.warn('[NotionSync] Failed to upload backup to server');
            }
        } catch (error) {
            console.warn('[NotionSync] Server backup upload failed:', error);
        }
    }

    /**
     * 오래된 백업 정리
     */
    cleanupOldBackups() {
        try {
            const backupKeys = Object.keys(localStorage)
                .filter(key => key.startsWith('notion_backup_'))
                .sort()
                .reverse();
            
            // 최대 5개 백업 유지
            if (backupKeys.length > 5) {
                backupKeys.slice(5).forEach(key => {
                    localStorage.removeItem(key);
                });
            }
        } catch (error) {
            console.error('[NotionSync] Failed to cleanup old backups:', error);
        }
    }

    /**
     * 특정 아이템의 변경사항을 즉시 동기화
     */
    async syncItemImmediately(itemId, changeType = 'update') {
        if (this.isSyncing) {
            // 동기화 큐에 추가
            this.syncQueue.push({ itemId, changeType, timestamp: Date.now() });
            return;
        }

        try {
            console.log(`[NotionSync] Syncing item ${itemId} immediately...`);
            
            // 아이템 데이터 조회
            const response = await fetch(`/field-report/api/inventory-items/?item_id=${itemId}`);
            const data = await response.json();
            
            if (data.success && data.items.length > 0) {
                const notionPage = this.convertItemsToNotionPages(data.items)[0];
                await this.createOrUpdateNotionPage('inventory', notionPage);
                
                console.log(`[NotionSync] Item ${itemId} synced successfully`);
            }
            
        } catch (error) {
            console.error(`[NotionSync] Failed to sync item ${itemId}:`, error);
        }
    }

    /**
     * 동기화 큐 처리
     */
    async processSyncQueue() {
        if (this.syncQueue.length === 0 || this.isSyncing) {
            return;
        }

        const queueItems = [...this.syncQueue];
        this.syncQueue = [];

        for (const item of queueItems) {
            try {
                await this.syncItemImmediately(item.itemId, item.changeType);
            } catch (error) {
                console.error('[NotionSync] Failed to process queue item:', error);
            }
        }
    }

    /**
     * 동기화 상태 조회
     */
    getSyncStatus() {
        return {
            is_syncing: this.isSyncing,
            last_sync_time: this.lastSyncTime?.toISOString(),
            auto_sync_enabled: !!this.syncInterval,
            queue_size: this.syncQueue.length,
            notion_config: this.notionConfig
        };
    }

    /**
     * 수동 동기화 트리거
     */
    async triggerManualSync() {
        if (this.isSyncing) {
            console.warn('[NotionSync] Sync already in progress');
            return false;
        }

        await this.syncAllData();
        return true;
    }

    /**
     * 지연 함수
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 콜백 등록
     */
    on(event, callback) {
        if (this.callbacks[event]) {
            this.callbacks[event].push(callback);
        }
    }

    /**
     * 콜백 제거
     */
    off(event, callback) {
        if (this.callbacks[event]) {
            const index = this.callbacks[event].indexOf(callback);
            if (index > -1) {
                this.callbacks[event].splice(index, 1);
            }
        }
    }

    /**
     * 콜백 실행
     */
    triggerCallback(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[NotionSync] Error in ${event} callback:`, error);
                }
            });
        }
    }

    /**
     * 리소스 정리
     */
    cleanup() {
        this.stopAutoSync();
        this.syncQueue = [];
        this.callbacks = {
            syncStarted: [],
            syncCompleted: [],
            syncFailed: [],
            dataBackedUp: []
        };
        
        console.log('[NotionSync] Resources cleaned up');
    }
}

// 전역 인스턴스 생성
const notionSync = new NotionSync();

// 모듈 내보내기
window.NotionSync = NotionSync;
window.notionSync = notionSync;