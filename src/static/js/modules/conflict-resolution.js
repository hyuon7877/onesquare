/**
 * OneSquare 데이터 충돌 해결 시스템
 * 오프라인/온라인 데이터 동기화 시 발생하는 충돌을 감지하고 해결
 */

import offlineDB from './offline-database.js';

class ConflictResolutionManager {
    constructor() {
        this.conflictStrategies = {
            SERVER_WINS: 'server-wins',
            CLIENT_WINS: 'client-wins',
            MERGE: 'merge',
            MANUAL: 'manual'
        };
        
        this.defaultStrategy = this.conflictStrategies.SERVER_WINS;
        this.conflictQueue = [];
        this.isResolvingConflicts = false;
        
        this.setupConflictHandlers();
        this.loadUserPreferences();
    }
    
    /**
     * 충돌 핸들러 설정
     */
    setupConflictHandlers() {
        // 커스텀 이벤트 리스너 등록
        window.addEventListener('data-conflict', (event) => {
            this.handleDataConflict(event.detail);
        });
        
        // Service Worker 메시지 리스너
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', (event) => {
                if (event.data.type === 'CONFLICT_DETECTED') {
                    this.handleDataConflict(event.data.conflict);
                }
            });
        }
    }
    
    /**
     * 사용자 환경 설정 로드
     */
    async loadUserPreferences() {
        try {
            const strategy = await offlineDB.getSetting('conflict_resolution_strategy');
            if (strategy) {
                this.defaultStrategy = strategy;
            }
            
            const autoResolve = await offlineDB.getSetting('auto_resolve_conflicts');
            this.autoResolveEnabled = autoResolve !== false; // 기본값 true
            
        } catch (error) {
            console.warn('[ConflictResolution] 사용자 설정 로드 실패:', error);
        }
    }
    
    /**
     * 데이터 충돌 감지 및 분석
     */
    async detectConflicts(localData, serverData, entityType, entityId) {
        const conflict = {
            id: this.generateConflictId(),
            entityType,
            entityId,
            localData: { ...localData },
            serverData: { ...serverData },
            detectedAt: new Date().toISOString(),
            status: 'pending',
            conflictType: this.analyzeConflictType(localData, serverData),
            severity: this.calculateConflictSeverity(localData, serverData)
        };
        
        // IndexedDB에 충돌 기록
        await offlineDB.saveData(offlineDB.stores.conflicts, conflict);
        
        console.log('[ConflictResolution] 충돌 감지됨:', conflict);
        
        // 자동 해결이 활성화되어 있으면 즉시 처리
        if (this.autoResolveEnabled && conflict.severity !== 'critical') {
            await this.resolveConflictAutomatically(conflict);
        } else {
            // 수동 해결을 위해 UI 알림
            this.notifyConflictToUser(conflict);
        }
        
        return conflict;
    }
    
    /**
     * 충돌 유형 분석
     */
    analyzeConflictType(localData, serverData) {
        const localTime = new Date(localData.updated_at || localData.last_edited_time || 0);
        const serverTime = new Date(serverData.updated_at || serverData.last_edited_time || 0);
        
        if (Math.abs(localTime - serverTime) < 60000) { // 1분 이내
            return 'concurrent'; // 동시 수정
        } else if (localTime > serverTime) {
            return 'local-newer'; // 로컬이 더 최신
        } else {
            return 'server-newer'; // 서버가 더 최신
        }
    }
    
    /**
     * 충돌 심각도 계산
     */
    calculateConflictSeverity(localData, serverData) {
        let conflictCount = 0;
        let criticalFields = 0;
        
        // 중요 필드 목록
        const criticalFieldNames = ['status', 'amount', 'quantity', 'price', 'active', 'deleted'];
        
        // 필드별 비교
        for (const key in localData) {
            if (localData[key] !== serverData[key]) {
                conflictCount++;
                
                if (criticalFieldNames.includes(key)) {
                    criticalFields++;
                }
            }
        }
        
        // 심각도 결정
        if (criticalFields > 0) {
            return 'critical';
        } else if (conflictCount > 5) {
            return 'high';
        } else if (conflictCount > 2) {
            return 'medium';
        } else {
            return 'low';
        }
    }
    
    /**
     * 자동 충돌 해결
     */
    async resolveConflictAutomatically(conflict) {
        try {
            console.log('[ConflictResolution] 자동 해결 시작:', conflict.id);
            
            let resolvedData;
            let resolutionStrategy;
            
            switch (this.defaultStrategy) {
                case this.conflictStrategies.SERVER_WINS:
                    resolvedData = conflict.serverData;
                    resolutionStrategy = 'server-wins';
                    break;
                    
                case this.conflictStrategies.CLIENT_WINS:
                    resolvedData = conflict.localData;
                    resolutionStrategy = 'client-wins';
                    break;
                    
                case this.conflictStrategies.MERGE:
                    resolvedData = await this.mergeData(conflict.localData, conflict.serverData);
                    resolutionStrategy = 'merge';
                    break;
                    
                default:
                    throw new Error('Unsupported auto-resolution strategy');
            }
            
            await this.applyResolution(conflict, resolvedData, resolutionStrategy);
            
        } catch (error) {
            console.error('[ConflictResolution] 자동 해결 실패:', error);
            // 자동 해결 실패 시 수동 해결로 전환
            await this.escalateToManualResolution(conflict, error);
        }
    }
    
    /**
     * 데이터 병합 (스마트 머지)
     */
    async mergeData(localData, serverData) {
        const merged = { ...serverData }; // 서버 데이터를 기본으로
        
        // 타임스탬프 비교하여 최신 값 선택
        const localTime = new Date(localData.updated_at || localData.last_edited_time || 0);
        const serverTime = new Date(serverData.updated_at || serverData.last_edited_time || 0);
        
        // 각 필드별로 더 최신 값 사용
        for (const key in localData) {
            if (key === 'updated_at' || key === 'last_edited_time') {
                continue; // 타임스탬프 필드는 건너뛰기
            }
            
            // 로컬 값이 더 최신이고 서버와 다르면 로컬 값 사용
            if (localData[key] !== serverData[key] && localTime > serverTime) {
                merged[key] = localData[key];
            }
            
            // 배열 필드 병합
            if (Array.isArray(localData[key]) && Array.isArray(serverData[key])) {
                merged[key] = this.mergeArrays(localData[key], serverData[key]);
            }
            
            // 객체 필드 재귀 병합
            if (this.isObject(localData[key]) && this.isObject(serverData[key])) {
                merged[key] = await this.mergeData(localData[key], serverData[key]);
            }
        }
        
        // 병합 메타데이터 추가
        merged.merged_at = new Date().toISOString();
        merged.merge_source = 'auto-merge';
        
        return merged;
    }
    
    /**
     * 배열 병합
     */
    mergeArrays(localArray, serverArray) {
        // 고유 값들을 합치기
        const mergedSet = new Set([...localArray, ...serverArray]);
        return Array.from(mergedSet);
    }
    
    /**
     * 객체 타입 체크
     */
    isObject(item) {
        return item && typeof item === 'object' && !Array.isArray(item) && !(item instanceof Date);
    }
    
    /**
     * 해결책 적용
     */
    async applyResolution(conflict, resolvedData, strategy) {
        try {
            // 1. 로컬 데이터베이스 업데이트
            await this.updateLocalData(conflict, resolvedData);
            
            // 2. 서버와 동기화 (필요한 경우)
            if (strategy === 'client-wins' || strategy === 'merge') {
                await this.syncToServer(conflict, resolvedData);
            }
            
            // 3. 충돌 상태 업데이트
            conflict.status = 'resolved';
            conflict.resolution = strategy;
            conflict.resolvedData = resolvedData;
            conflict.resolvedAt = new Date().toISOString();
            
            await offlineDB.saveData(offlineDB.stores.conflicts, conflict);
            
            // 4. 해결 완료 로그
            await offlineDB.logSync('conflict-resolution', 'success', {
                conflictId: conflict.id,
                strategy,
                entityType: conflict.entityType,
                entityId: conflict.entityId
            });
            
            console.log('[ConflictResolution] 충돌 해결 완료:', conflict.id, strategy);
            
            // 5. UI에 알림
            this.notifyResolutionComplete(conflict, strategy);
            
        } catch (error) {
            console.error('[ConflictResolution] 해결책 적용 실패:', error);
            await this.handleResolutionFailure(conflict, error);
            throw error;
        }
    }
    
    /**
     * 로컬 데이터 업데이트
     */
    async updateLocalData(conflict, resolvedData) {
        const storeName = this.getStoreNameByEntityType(conflict.entityType);
        
        if (storeName) {
            await offlineDB.saveData(storeName, {
                ...resolvedData,
                id: conflict.entityId,
                conflict_resolved: true,
                resolved_at: new Date().toISOString()
            });
        }
    }
    
    /**
     * 서버 동기화
     */
    async syncToServer(conflict, resolvedData) {
        const endpoint = this.getApiEndpoint(conflict.entityType, conflict.entityId);
        
        await offlineDB.addToOfflineQueue({
            type: 'update',
            endpoint,
            method: 'PATCH',
            data: resolvedData,
            priority: 'high',
            metadata: {
                conflictResolution: true,
                conflictId: conflict.id
            }
        });
    }
    
    /**
     * 수동 해결로 에스컬레이션
     */
    async escalateToManualResolution(conflict, error) {
        conflict.status = 'manual-required';
        conflict.autoResolutionError = error.message;
        conflict.escalatedAt = new Date().toISOString();
        
        await offlineDB.saveData(offlineDB.stores.conflicts, conflict);
        
        // 사용자에게 수동 해결 필요 알림
        this.notifyManualResolutionRequired(conflict);
    }
    
    /**
     * 사용자에게 충돌 알림
     */
    notifyConflictToUser(conflict) {
        // 커스텀 이벤트 발생
        const event = new CustomEvent('conflict-notification', {
            detail: {
                type: 'conflict-detected',
                conflict,
                severity: conflict.severity,
                requiresAttention: conflict.severity === 'critical'
            }
        });
        window.dispatchEvent(event);
        
        // 브라우저 알림 (권한이 있는 경우)
        if (Notification.permission === 'granted' && conflict.severity === 'critical') {
            new Notification('OneSquare - 데이터 충돌 감지', {
                body: `${conflict.entityType} 데이터에서 충돌이 감지되었습니다. 수동 해결이 필요합니다.`,
                icon: '/static/images/icon-warning.png',
                requireInteraction: true
            });
        }
    }
    
    /**
     * 해결 완료 알림
     */
    notifyResolutionComplete(conflict, strategy) {
        const event = new CustomEvent('conflict-notification', {
            detail: {
                type: 'conflict-resolved',
                conflict,
                strategy,
                message: `데이터 충돌이 ${strategy} 전략으로 해결되었습니다.`
            }
        });
        window.dispatchEvent(event);
    }
    
    /**
     * 수동 해결 필요 알림
     */
    notifyManualResolutionRequired(conflict) {
        const event = new CustomEvent('conflict-notification', {
            detail: {
                type: 'manual-resolution-required',
                conflict,
                message: '자동 해결에 실패했습니다. 수동 해결이 필요합니다.'
            }
        });
        window.dispatchEvent(event);
    }
    
    /**
     * 수동 충돌 해결 인터페이스
     */
    async resolveConflictManually(conflictId, userChoice, customData = null) {
        const conflict = await offlineDB.getData(offlineDB.stores.conflicts, conflictId);
        
        if (!conflict) {
            throw new Error(`Conflict ${conflictId} not found`);
        }
        
        let resolvedData;
        let strategy;
        
        switch (userChoice) {
            case 'keep-local':
                resolvedData = conflict.localData;
                strategy = 'user-chose-local';
                break;
                
            case 'keep-server':
                resolvedData = conflict.serverData;
                strategy = 'user-chose-server';
                break;
                
            case 'merge':
                resolvedData = await this.mergeData(conflict.localData, conflict.serverData);
                strategy = 'user-requested-merge';
                break;
                
            case 'custom':
                if (!customData) {
                    throw new Error('Custom data required for manual resolution');
                }
                resolvedData = customData;
                strategy = 'user-custom-data';
                break;
                
            default:
                throw new Error(`Invalid user choice: ${userChoice}`);
        }
        
        await this.applyResolution(conflict, resolvedData, strategy);
        return conflict;
    }
    
    /**
     * 미해결 충돌 조회
     */
    async getPendingConflicts() {
        const allConflicts = await offlineDB.getAllData(offlineDB.stores.conflicts);
        return allConflicts.filter(conflict => 
            conflict.status === 'pending' || conflict.status === 'manual-required'
        ).sort((a, b) => {
            // 심각도별 정렬 (critical > high > medium > low)
            const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
            return severityOrder[b.severity] - severityOrder[a.severity];
        });
    }
    
    /**
     * 충돌 통계 조회
     */
    async getConflictStatistics() {
        const allConflicts = await offlineDB.getAllData(offlineDB.stores.conflicts);
        
        const stats = {
            total: allConflicts.length,
            pending: 0,
            resolved: 0,
            failed: 0,
            bySeverity: { critical: 0, high: 0, medium: 0, low: 0 },
            byStrategy: {},
            recentConflicts: []
        };
        
        allConflicts.forEach(conflict => {
            // 상태별 집계
            if (conflict.status === 'pending' || conflict.status === 'manual-required') {
                stats.pending++;
            } else if (conflict.status === 'resolved') {
                stats.resolved++;
            } else {
                stats.failed++;
            }
            
            // 심각도별 집계
            stats.bySeverity[conflict.severity]++;
            
            // 해결 전략별 집계
            if (conflict.resolution) {
                stats.byStrategy[conflict.resolution] = (stats.byStrategy[conflict.resolution] || 0) + 1;
            }
        });
        
        // 최근 충돌 (7일 이내)
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        
        stats.recentConflicts = allConflicts
            .filter(conflict => new Date(conflict.detectedAt) > sevenDaysAgo)
            .sort((a, b) => new Date(b.detectedAt) - new Date(a.detectedAt))
            .slice(0, 10);
        
        return stats;
    }
    
    // === 유틸리티 메소드 ===
    
    /**
     * 충돌 ID 생성
     */
    generateConflictId() {
        return 'conflict_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    /**
     * 엔티티 타입별 스토어명 반환
     */
    getStoreNameByEntityType(entityType) {
        const storeMap = {
            'work_session': offlineDB.stores.workSessions,
            'photo': offlineDB.stores.photos,
            'inventory_item': offlineDB.stores.inventoryItems,
            'inventory_check': offlineDB.stores.inventoryChecks,
            'field_site': offlineDB.stores.fieldSites,
            'notion_page': offlineDB.stores.notionPages
        };
        
        return storeMap[entityType];
    }
    
    /**
     * API 엔드포인트 생성
     */
    getApiEndpoint(entityType, entityId) {
        const endpointMap = {
            'work_session': `/api/field-report/sessions/${entityId}/`,
            'photo': `/api/field-report/photos/${entityId}/`,
            'inventory_item': `/api/field-report/inventory/${entityId}/`,
            'inventory_check': `/api/field-report/inventory-checks/${entityId}/`,
            'notion_page': `/api/notion/pages/${entityId}/`
        };
        
        return endpointMap[entityType] || `/api/${entityType}/${entityId}/`;
    }
    
    /**
     * 해결 실패 처리
     */
    async handleResolutionFailure(conflict, error) {
        conflict.status = 'failed';
        conflict.resolutionError = error.message;
        conflict.failedAt = new Date().toISOString();
        
        await offlineDB.saveData(offlineDB.stores.conflicts, conflict);
        
        await offlineDB.logSync('conflict-resolution', 'failed', {
            conflictId: conflict.id,
            error: error.message,
            entityType: conflict.entityType,
            entityId: conflict.entityId
        });
    }
    
    /**
     * 충돌 해결 전략 설정
     */
    async setResolutionStrategy(strategy) {
        if (!Object.values(this.conflictStrategies).includes(strategy)) {
            throw new Error(`Invalid strategy: ${strategy}`);
        }
        
        this.defaultStrategy = strategy;
        await offlineDB.setSetting('conflict_resolution_strategy', strategy);
        
        console.log('[ConflictResolution] 해결 전략 변경:', strategy);
    }
    
    /**
     * 자동 해결 활성화/비활성화
     */
    async setAutoResolve(enabled) {
        this.autoResolveEnabled = enabled;
        await offlineDB.setSetting('auto_resolve_conflicts', enabled);
        
        console.log('[ConflictResolution] 자동 해결:', enabled ? '활성화' : '비활성화');
    }
}

// 전역 인스턴스 생성
const conflictResolver = new ConflictResolutionManager();

// 전역 함수로 노출
window.resolveConflict = (conflictId, choice, customData) => {
    return conflictResolver.resolveConflictManually(conflictId, choice, customData);
};

window.getConflictStats = () => {
    return conflictResolver.getConflictStatistics();
};

export default conflictResolver;