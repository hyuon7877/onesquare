/**
 * OneSquare - 재고 부족 알림 시스템
 * 
 * 실시간 재고 부족 알림, 경고, 푸시 알림 관리
 */

class InventoryAlerts {
    constructor() {
        this.alerts = [];
        this.alertThresholds = {
            critical: 0,     // 품절
            warning: 0.2,    // 최소 재고의 20% 이하
            low: 0.5         // 최소 재고의 50% 이하
        };
        
        this.notificationPermission = 'default';
        this.isAlertSystemActive = false;
        this.checkInterval = null;
        
        this.callbacks = {
            alertTriggered: [],
            alertResolved: [],
            notificationShown: []
        };
        
        this.init();
    }

    /**
     * 초기화
     */
    async init() {
        console.log('[InventoryAlerts] Initializing inventory alert system...');
        
        // 알림 권한 요청
        await this.requestNotificationPermission();
        
        // 기존 알림 로드
        await this.loadExistingAlerts();
        
        // 주기적 체크 시작
        this.startPeriodicCheck();
        
        console.log('[InventoryAlerts] Inventory alert system initialized');
    }

    /**
     * 알림 권한 요청
     */
    async requestNotificationPermission() {
        if (!('Notification' in window)) {
            console.warn('[InventoryAlerts] Browser does not support notifications');
            return false;
        }

        if (Notification.permission === 'granted') {
            this.notificationPermission = 'granted';
            return true;
        }

        if (Notification.permission === 'denied') {
            console.warn('[InventoryAlerts] Notification permission denied');
            this.notificationPermission = 'denied';
            return false;
        }

        try {
            const permission = await Notification.requestPermission();
            this.notificationPermission = permission;
            
            if (permission === 'granted') {
                console.log('[InventoryAlerts] Notification permission granted');
                return true;
            } else {
                console.warn('[InventoryAlerts] Notification permission denied by user');
                return false;
            }
        } catch (error) {
            console.error('[InventoryAlerts] Failed to request notification permission:', error);
            return false;
        }
    }

    /**
     * 기존 알림 로드
     */
    async loadExistingAlerts() {
        try {
            const response = await fetch('/field-report/api/low-stock-alerts/');
            const data = await response.json();
            
            if (data.success) {
                this.alerts = data.alerts;
                this.processNewAlerts();
                console.log(`[InventoryAlerts] Loaded ${this.alerts.length} existing alerts`);
            }
        } catch (error) {
            console.error('[InventoryAlerts] Failed to load existing alerts:', error);
        }
    }

    /**
     * 주기적 알림 체크 시작
     */
    startPeriodicCheck(intervalMinutes = 5) {
        this.stopPeriodicCheck();
        
        this.checkInterval = setInterval(async () => {
            await this.checkForNewAlerts();
        }, intervalMinutes * 60 * 1000);
        
        this.isAlertSystemActive = true;
        console.log(`[InventoryAlerts] Started periodic check every ${intervalMinutes} minutes`);
    }

    /**
     * 주기적 체크 중지
     */
    stopPeriodicCheck() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
        this.isAlertSystemActive = false;
        console.log('[InventoryAlerts] Stopped periodic check');
    }

    /**
     * 새로운 알림 체크
     */
    async checkForNewAlerts() {
        try {
            const response = await fetch('/field-report/api/low-stock-alerts/');
            const data = await response.json();
            
            if (data.success) {
                const newAlerts = this.findNewAlerts(data.alerts);
                
                if (newAlerts.length > 0) {
                    console.log(`[InventoryAlerts] Found ${newAlerts.length} new alerts`);
                    this.alerts = data.alerts;
                    this.processNewAlerts(newAlerts);
                }
            }
        } catch (error) {
            console.error('[InventoryAlerts] Failed to check for new alerts:', error);
        }
    }

    /**
     * 새로운 알림 찾기
     */
    findNewAlerts(currentAlerts) {
        const existingAlertIds = new Set(this.alerts.map(alert => alert.id));
        return currentAlerts.filter(alert => !existingAlertIds.has(alert.id));
    }

    /**
     * 새 알림 처리
     */
    processNewAlerts(newAlerts = null) {
        const alertsToProcess = newAlerts || this.alerts;
        
        alertsToProcess.forEach(alert => {
            // 알림 우선순위 결정
            const alertLevel = this.determineAlertLevel(alert);
            
            // 콜백 실행
            this.triggerCallback('alertTriggered', {
                alert: alert,
                level: alertLevel,
                timestamp: new Date().toISOString()
            });
            
            // 브라우저 알림 표시
            if (this.shouldShowNotification(alert, alertLevel)) {
                this.showBrowserNotification(alert, alertLevel);
            }
            
            // 시각적 알림 표시
            this.showVisualAlert(alert, alertLevel);
        });
    }

    /**
     * 알림 레벨 결정
     */
    determineAlertLevel(alert) {
        if (alert.status === 'out_of_stock') {
            return 'critical';
        }
        
        if (alert.priority <= 2) {
            return 'warning';
        }
        
        return 'low';
    }

    /**
     * 브라우저 알림 표시 여부 결정
     */
    shouldShowNotification(alert, alertLevel) {
        if (this.notificationPermission !== 'granted') {
            return false;
        }
        
        // 중요한 알림만 브라우저 알림으로 표시
        return alertLevel === 'critical' || alertLevel === 'warning';
    }

    /**
     * 브라우저 알림 표시
     */
    showBrowserNotification(alert, alertLevel) {
        try {
            const title = this.getNotificationTitle(alert, alertLevel);
            const options = {
                body: this.getNotificationBody(alert),
                icon: this.getNotificationIcon(alertLevel),
                badge: '/static/images/logo-badge.png',
                tag: `inventory-${alert.id}`,
                requireInteraction: alertLevel === 'critical',
                actions: [
                    {
                        action: 'view',
                        title: '확인하기',
                        icon: '/static/images/view-icon.png'
                    },
                    {
                        action: 'dismiss',
                        title: '닫기',
                        icon: '/static/images/dismiss-icon.png'
                    }
                ],
                data: {
                    alertId: alert.id,
                    itemId: alert.item_id,
                    alertLevel: alertLevel
                }
            };
            
            const notification = new Notification(title, options);
            
            notification.onclick = () => {
                this.handleNotificationClick(alert);
                notification.close();
            };
            
            // 자동 닫기 (중요한 알림은 더 오래 유지)
            const autoCloseDelay = alertLevel === 'critical' ? 10000 : 5000;
            setTimeout(() => {
                notification.close();
            }, autoCloseDelay);
            
            this.triggerCallback('notificationShown', {
                alert: alert,
                level: alertLevel,
                notification: notification
            });
            
            console.log(`[InventoryAlerts] Browser notification shown for ${alert.item_name}`);
            
        } catch (error) {
            console.error('[InventoryAlerts] Failed to show browser notification:', error);
        }
    }

    /**
     * 알림 제목 생성
     */
    getNotificationTitle(alert, alertLevel) {
        switch (alertLevel) {
            case 'critical':
                return '🚨 재고 품절 알림';
            case 'warning':
                return '⚠️ 재고 부족 경고';
            default:
                return '📦 재고 확인 필요';
        }
    }

    /**
     * 알림 내용 생성
     */
    getNotificationBody(alert) {
        if (alert.status === 'out_of_stock') {
            return `${alert.item_name}이(가) 품절되었습니다.`;
        } else {
            return `${alert.item_name} 재고가 ${alert.current_quantity}${alert.unit}로 부족합니다. (최소: ${alert.minimum_stock}${alert.unit})`;
        }
    }

    /**
     * 알림 아이콘 선택
     */
    getNotificationIcon(alertLevel) {
        switch (alertLevel) {
            case 'critical':
                return '/static/images/alert-critical.png';
            case 'warning':
                return '/static/images/alert-warning.png';
            default:
                return '/static/images/alert-info.png';
        }
    }

    /**
     * 알림 클릭 처리
     */
    handleNotificationClick(alert) {
        // 재고 체크 페이지로 이동하고 해당 아이템에 포커스
        const url = `/field-report/inventory-check/?focus=${alert.id}`;
        
        if (window.focus) {
            window.focus();
        }
        
        // 페이지가 이미 열려있으면 해당 아이템으로 스크롤
        if (window.location.pathname.includes('inventory-check')) {
            this.focusOnItem(alert.id);
        } else {
            window.location.href = url;
        }
    }

    /**
     * 시각적 알림 표시 (페이지 내)
     */
    showVisualAlert(alert, alertLevel) {
        // 페이지가 재고 체크 페이지인 경우에만 시각적 알림 표시
        if (!window.location.pathname.includes('inventory-check')) {
            return;
        }
        
        const alertElement = this.createVisualAlertElement(alert, alertLevel);
        this.displayVisualAlert(alertElement);
    }

    /**
     * 시각적 알림 엘리먼트 생성
     */
    createVisualAlertElement(alert, alertLevel) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `inventory-visual-alert alert-${alertLevel}`;
        alertDiv.dataset.alertId = alert.id;
        
        const iconClass = alertLevel === 'critical' ? 'bi-exclamation-triangle-fill' : 
                         alertLevel === 'warning' ? 'bi-exclamation-triangle' : 'bi-info-circle';
        
        alertDiv.innerHTML = `
            <div class="alert-content">
                <div class="alert-icon">
                    <i class="bi ${iconClass}"></i>
                </div>
                <div class="alert-message">
                    <div class="alert-title">${this.getNotificationTitle(alert, alertLevel)}</div>
                    <div class="alert-body">${this.getNotificationBody(alert)}</div>
                    <div class="alert-time">${new Date().toLocaleTimeString('ko-KR')}</div>
                </div>
                <div class="alert-actions">
                    <button class="alert-btn view-btn" onclick="inventoryAlerts.viewAlert('${alert.id}')">
                        <i class="bi bi-eye"></i> 확인
                    </button>
                    <button class="alert-btn dismiss-btn" onclick="inventoryAlerts.dismissAlert('${alert.id}')">
                        <i class="bi bi-x"></i>
                    </button>
                </div>
            </div>
        `;
        
        return alertDiv;
    }

    /**
     * 시각적 알림 표시
     */
    displayVisualAlert(alertElement) {
        let alertContainer = document.getElementById('inventory-alerts-container');
        
        if (!alertContainer) {
            alertContainer = document.createElement('div');
            alertContainer.id = 'inventory-alerts-container';
            alertContainer.className = 'inventory-alerts-container';
            document.body.appendChild(alertContainer);
        }
        
        alertContainer.appendChild(alertElement);
        
        // 애니메이션 효과
        setTimeout(() => {
            alertElement.classList.add('show');
        }, 100);
        
        // 자동 제거 (중요한 알림은 더 오래 유지)
        const autoRemoveDelay = alertElement.classList.contains('alert-critical') ? 15000 : 8000;
        setTimeout(() => {
            this.removeVisualAlert(alertElement);
        }, autoRemoveDelay);
    }

    /**
     * 시각적 알림 제거
     */
    removeVisualAlert(alertElement) {
        alertElement.classList.add('hide');
        setTimeout(() => {
            if (alertElement.parentNode) {
                alertElement.parentNode.removeChild(alertElement);
            }
        }, 300);
    }

    /**
     * 알림 확인 처리
     */
    viewAlert(alertId) {
        const alert = this.alerts.find(a => a.id === alertId);
        if (alert) {
            this.focusOnItem(alert.item_id);
        }
        
        // 시각적 알림 제거
        const alertElement = document.querySelector(`[data-alert-id="${alertId}"]`);
        if (alertElement) {
            this.removeVisualAlert(alertElement);
        }
    }

    /**
     * 알림 해제 처리
     */
    dismissAlert(alertId) {
        // 시각적 알림만 제거 (실제 재고 문제는 해결되지 않음)
        const alertElement = document.querySelector(`[data-alert-id="${alertId}"]`);
        if (alertElement) {
            this.removeVisualAlert(alertElement);
        }
    }

    /**
     * 특정 아이템에 포커스
     */
    focusOnItem(itemId) {
        const itemElement = document.querySelector(`[data-item-id="${itemId}"]`);
        if (itemElement) {
            itemElement.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
            
            // 하이라이트 효과
            itemElement.classList.add('highlight');
            setTimeout(() => {
                itemElement.classList.remove('highlight');
            }, 3000);
        }
    }

    /**
     * 수동으로 재고 체크하여 알림 생성
     */
    async checkInventoryItem(itemId, currentQuantity, minimumStock) {
        const alertData = {
            id: `manual-${Date.now()}`,
            item_id: itemId,
            current_quantity: currentQuantity,
            minimum_stock: minimumStock,
            status: currentQuantity === 0 ? 'out_of_stock' : 
                   currentQuantity < minimumStock ? 'low_stock' : 'sufficient',
            priority: currentQuantity === 0 ? 1 : 
                     currentQuantity < minimumStock * 0.5 ? 2 : 3,
            item_name: `품목 ${itemId}`, // 실제 구현에서는 아이템 이름 조회
            unit: 'ea',
            shortage_amount: Math.max(0, minimumStock - currentQuantity)
        };
        
        if (alertData.status !== 'sufficient') {
            this.processNewAlerts([alertData]);
        }
    }

    /**
     * 알림 통계 조회
     */
    getAlertStats() {
        const stats = {
            total_alerts: this.alerts.length,
            critical_alerts: this.alerts.filter(a => a.alert_level === 'critical').length,
            warning_alerts: this.alerts.filter(a => a.alert_level === 'warning').length,
            low_alerts: this.alerts.filter(a => a.alert_level === 'low').length,
            latest_alert: this.alerts.length > 0 ? this.alerts[0].last_checked : null,
            notification_permission: this.notificationPermission,
            alert_system_active: this.isAlertSystemActive
        };
        
        return stats;
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
                    console.error(`[InventoryAlerts] Error in ${event} callback:`, error);
                }
            });
        }
    }

    /**
     * 리소스 정리
     */
    cleanup() {
        this.stopPeriodicCheck();
        this.alerts = [];
        this.callbacks = {
            alertTriggered: [],
            alertResolved: [],
            notificationShown: []
        };
        
        // 시각적 알림 컨테이너 제거
        const alertContainer = document.getElementById('inventory-alerts-container');
        if (alertContainer) {
            alertContainer.remove();
        }
        
        console.log('[InventoryAlerts] Resources cleaned up');
    }
}

// CSS 스타일 추가
const alertStyles = `
<style>
.inventory-alerts-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 10000;
    max-width: 400px;
}

.inventory-visual-alert {
    background: white;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.12);
    margin-bottom: 15px;
    overflow: hidden;
    transform: translateX(100%);
    opacity: 0;
    transition: all 0.3s ease;
}

.inventory-visual-alert.show {
    transform: translateX(0);
    opacity: 1;
}

.inventory-visual-alert.hide {
    transform: translateX(100%);
    opacity: 0;
}

.inventory-visual-alert.alert-critical {
    border-left: 4px solid #dc3545;
}

.inventory-visual-alert.alert-warning {
    border-left: 4px solid #ffc107;
}

.inventory-visual-alert.alert-low {
    border-left: 4px solid #17a2b8;
}

.alert-content {
    display: flex;
    align-items: flex-start;
    padding: 15px;
}

.alert-icon {
    margin-right: 12px;
    font-size: 1.2rem;
}

.alert-critical .alert-icon {
    color: #dc3545;
}

.alert-warning .alert-icon {
    color: #ffc107;
}

.alert-low .alert-icon {
    color: #17a2b8;
}

.alert-message {
    flex: 1;
}

.alert-title {
    font-weight: bold;
    font-size: 0.9rem;
    margin-bottom: 4px;
}

.alert-body {
    font-size: 0.8rem;
    color: #6c757d;
    margin-bottom: 4px;
}

.alert-time {
    font-size: 0.7rem;
    color: #adb5bd;
}

.alert-actions {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.alert-btn {
    padding: 4px 8px;
    border: none;
    border-radius: 4px;
    font-size: 0.7rem;
    cursor: pointer;
    transition: all 0.3s ease;
}

.view-btn {
    background: #007bff;
    color: white;
}

.view-btn:hover {
    background: #0056b3;
}

.dismiss-btn {
    background: #6c757d;
    color: white;
}

.dismiss-btn:hover {
    background: #5a6268;
}

.inventory-item.highlight {
    animation: highlight-pulse 3s ease-in-out;
}

@keyframes highlight-pulse {
    0%, 100% { 
        background: transparent; 
        border-color: #e9ecef;
    }
    50% { 
        background: rgba(0, 123, 255, 0.1);
        border-color: #007bff;
        transform: scale(1.02);
    }
}
</style>
`;

// 스타일 주입
if (!document.getElementById('inventory-alerts-styles')) {
    const styleElement = document.createElement('div');
    styleElement.id = 'inventory-alerts-styles';
    styleElement.innerHTML = alertStyles;
    document.head.appendChild(styleElement);
}

// 전역 인스턴스 생성
const inventoryAlerts = new InventoryAlerts();

// 모듈 내보내기
window.InventoryAlerts = InventoryAlerts;
window.inventoryAlerts = inventoryAlerts;