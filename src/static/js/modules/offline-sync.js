/**
 * OneSquare PWA - 오프라인 동기화 관리자
 * 
 * Notion API와 IndexedDB 간의 데이터 동기화 처리
 */

import offlineDB from './offline-database.js';

class OfflineSyncManager {
    constructor() {
        this.isOnline = navigator.onLine;
        this.syncInProgress = false;
        this.syncQueue = [];
        this.conflictResolution = 'server-wins'; // 'server-wins', 'client-wins', 'manual'
        
        this.setupNetworkListeners();
        this.startPeriodicSync();
    }

    /**
     * 네트워크 상태 리스너 설정
     */
    setupNetworkListeners() {
        window.addEventListener('online', async () => {
            console.log('네트워크 연결됨 - 동기화 시작');
            this.isOnline = true;
            await this.syncWhenOnline();
        });

        window.addEventListener('offline', () => {
            console.log('네트워크 연결 끊김 - 오프라인 모드');
            this.isOnline = false;
        });
    }

    /**
     * 주기적 동기화 시작 (5분마다)
     */
    startPeriodicSync() {
        setInterval(async () => {
            if (this.isOnline && !this.syncInProgress) {
                await this.syncWithNotion();
            }
        }, 5 * 60 * 1000); // 5분
    }

    /**
     * 온라인 상태일 때 즉시 동기화
     */
    async syncWhenOnline() {
        if (!this.isOnline || this.syncInProgress) return;
        
        try {
            await this.syncWithNotion();
            await this.processOfflineQueue();
        } catch (error) {
            console.error('온라인 동기화 실패:', error);
            await offlineDB.logSync('auto-sync', 'failed', error.message);
        }
    }

    /**
     * Notion과 전체 동기화
     */
    async syncWithNotion() {
        if (this.syncInProgress) {
            console.log('동기화가 이미 진행 중입니다');
            return;
        }

        this.syncInProgress = true;
        
        try {
            console.log('Notion 동기화 시작...');
            await offlineDB.logSync('full-sync', 'pending');
            
            // 1. Notion에서 데이터베이스 목록 가져오기
            await this.syncNotionDatabases();
            
            // 2. 각 데이터베이스의 페이지 동기화
            await this.syncNotionPages();
            
            // 3. 충돌 해결
            await this.resolveConflicts();
            
            await offlineDB.logSync('full-sync', 'success');
            console.log('Notion 동기화 완료');
            
        } catch (error) {
            console.error('Notion 동기화 실패:', error);
            await offlineDB.logSync('full-sync', 'failed', error.message);
        } finally {
            this.syncInProgress = false;
        }
    }

    /**
     * Notion 데이터베이스 동기화
     */
    async syncNotionDatabases() {
        try {
            const response = await fetch('/api/notion/databases/', {
                headers: {
                    'Authorization': `Bearer ${await this.getAuthToken()}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const databases = await response.json();
            
            for (const db of databases.results || []) {
                await offlineDB.saveData(offlineDB.stores.notionDatabases, {
                    databaseId: db.id,
                    title: this.extractTitle(db.title),
                    properties: db.properties,
                    lastEditedTime: db.last_edited_time,
                    createdTime: db.created_time
                });
            }
            
            console.log(`${databases.results?.length || 0}개 데이터베이스 동기화 완료`);
            
        } catch (error) {
            console.error('데이터베이스 동기화 실패:', error);
            throw error;
        }
    }

    /**
     * Notion 페이지 동기화
     */
    async syncNotionPages() {
        try {
            const databases = await offlineDB.getAllData(offlineDB.stores.notionDatabases);
            
            for (const database of databases) {
                await this.syncPagesFromDatabase(database.databaseId);
                await this.sleep(100); // API 레이트 리미트 방지
            }
            
        } catch (error) {
            console.error('페이지 동기화 실패:', error);
            throw error;
        }
    }

    /**
     * 특정 데이터베이스의 페이지 동기화
     */
    async syncPagesFromDatabase(databaseId) {
        try {
            const response = await fetch(`/api/notion/databases/${databaseId}/query/`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${await this.getAuthToken()}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    page_size: 100
                })
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const result = await response.json();
            const pages = result.results || [];
            
            for (const page of pages) {
                await this.syncSinglePage(page);
            }
            
            console.log(`데이터베이스 ${databaseId}: ${pages.length}개 페이지 동기화`);
            
        } catch (error) {
            console.error(`데이터베이스 ${databaseId} 동기화 실패:`, error);
        }
    }

    /**
     * 단일 페이지 동기화
     */
    async syncSinglePage(notionPage) {
        const localPage = await offlineDB.getData(offlineDB.stores.notionPages, notionPage.id);
        
        // 로컬에 없거나 서버가 더 최신이면 업데이트
        if (!localPage || new Date(notionPage.last_edited_time) > new Date(localPage.lastEditedTime)) {
            await offlineDB.saveNotionPage(notionPage);
        }
        // 충돌 감지 (로컬이 더 최신이고 오프라인 수정이 있는 경우)
        else if (localPage.offline && new Date(localPage.lastModified) > new Date(notionPage.last_edited_time)) {
            await this.handleConflict(localPage, notionPage);
        }
    }

    /**
     * 오프라인 큐 처리
     */
    async processOfflineQueue() {
        const queue = await offlineDB.getOfflineQueue();
        
        for (const item of queue) {
            try {
                await this.processQueueItem(item);
                await offlineDB.removeFromOfflineQueue(item.id);
                await offlineDB.logSync(`queue-${item.type}`, 'success', `처리됨: ${item.endpoint}`);
                
            } catch (error) {
                console.error('큐 아이템 처리 실패:', item, error);
                
                // 재시도 횟수 증가
                item.retryCount = (item.retryCount || 0) + 1;
                
                if (item.retryCount >= item.maxRetries) {
                    await offlineDB.removeFromOfflineQueue(item.id);
                    await offlineDB.logSync(`queue-${item.type}`, 'failed', `최대 재시도 초과: ${error.message}`);
                } else {
                    await offlineDB.saveData(offlineDB.stores.offlineQueue, item);
                    await offlineDB.logSync(`queue-${item.type}`, 'retry', `재시도 ${item.retryCount}/${item.maxRetries}`);
                }
            }
            
            await this.sleep(200); // API 레이트 리미트 방지
        }
        
        console.log(`${queue.length}개 오프라인 작업 처리 완료`);
    }

    /**
     * 개별 큐 아이템 처리
     */
    async processQueueItem(item) {
        const response = await fetch(item.endpoint, {
            method: item.method,
            headers: {
                'Authorization': `Bearer ${await this.getAuthToken()}`,
                'Content-Type': 'application/json'
            },
            body: item.data ? JSON.stringify(item.data) : undefined
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // 성공 시 로컬 데이터 업데이트
        if (item.type === 'create' || item.type === 'update') {
            if (result.id) {
                const pageData = await this.fetchPageContent(result.id);
                await offlineDB.saveNotionPage(pageData);
            }
        } else if (item.type === 'delete') {
            await offlineDB.deleteData(offlineDB.stores.notionPages, item.pageId);
        }
        
        return result;
    }

    /**
     * 충돌 처리
     */
    async handleConflict(localPage, serverPage) {
        console.warn('데이터 충돌 감지:', localPage.pageId);
        
        switch (this.conflictResolution) {
            case 'server-wins':
                await offlineDB.saveNotionPage(serverPage);
                await offlineDB.logSync('conflict-resolution', 'success', `서버 우선: ${localPage.pageId}`);
                break;
                
            case 'client-wins':
                await this.pushLocalChanges(localPage);
                await offlineDB.logSync('conflict-resolution', 'success', `클라이언트 우선: ${localPage.pageId}`);
                break;
                
            case 'manual':
                // 충돌 UI 표시를 위한 이벤트 발생
                this.notifyConflict(localPage, serverPage);
                break;
        }
    }

    /**
     * 로컬 변경사항을 서버로 푸시
     */
    async pushLocalChanges(localPage) {
        await offlineDB.addToOfflineQueue({
            type: 'update',
            endpoint: `/api/notion/pages/${localPage.pageId}/`,
            method: 'PATCH',
            data: {
                properties: localPage.properties
            },
            priority: 'high'
        });
    }

    /**
     * 오프라인 작업 추가 (외부에서 호출)
     */
    async addOfflineOperation(operation) {
        await offlineDB.addToOfflineQueue(operation);
        
        // 온라인 상태면 즉시 처리 시도
        if (this.isOnline && !this.syncInProgress) {
            setTimeout(() => this.processOfflineQueue(), 1000);
        }
    }

    /**
     * 페이지 콘텐츠 가져오기
     */
    async fetchPageContent(pageId) {
        const response = await fetch(`/api/notion/pages/${pageId}/`, {
            headers: {
                'Authorization': `Bearer ${await this.getAuthToken()}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    }

    /**
     * 인증 토큰 가져오기
     */
    async getAuthToken() {
        // Django 세션 또는 저장된 토큰 사용
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    /**
     * 제목 추출 헬퍼
     */
    extractTitle(titleArray) {
        if (Array.isArray(titleArray) && titleArray.length > 0) {
            return titleArray[0].plain_text || titleArray[0].text?.content || 'Untitled';
        }
        return 'Untitled';
    }

    /**
     * 충돌 알림
     */
    notifyConflict(localPage, serverPage) {
        const event = new CustomEvent('notion-conflict', {
            detail: { localPage, serverPage }
        });
        window.dispatchEvent(event);
    }

    /**
     * 동기화 상태 가져오기
     */
    getSyncStatus() {
        return {
            isOnline: this.isOnline,
            syncInProgress: this.syncInProgress,
            queueLength: this.syncQueue.length
        };
    }

    /**
     * 지연 함수
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// 전역 인스턴스 생성
const syncManager = new OfflineSyncManager();

export default syncManager;