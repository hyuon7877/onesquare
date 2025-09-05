/**
 * OneSquare PWA - 실시간 알림 시스템
 * Notion 기반 알림의 실시간 표시 및 푸시 알림 관리
 */

class NotificationSystem {
    constructor() {
        this.apiEndpoint = '/dashboard/api/notifications/';
        this.websocketUrl = null; // WebSocket 대신 폴링 사용
        this.pollingInterval = 30000; // 30초
        this.pollingTimer = null;
        this.isPolling = false;
        this.notifications = [];
        this.unreadCount = 0;
        
        // 브라우저 알림 권한
        this.pushPermission = 'default';
        
        this.init();
    }
    
    async init() {
        console.log('🔔 Notification System initializing...');
        
        try {
            // 브라우저 푸시 알림 권한 요청
            await this.requestNotificationPermission();
            
            // DOM 준비 후 초기화
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.initializeDOM());
            } else {
                this.initializeDOM();
            }
            
            // 초기 알림 로드
            await this.loadNotifications();
            
            // 실시간 폴링 시작
            this.startPolling();
            
            console.log('✅ Notification System initialized');
            
        } catch (error) {
            console.error('❌ Failed to initialize notification system:', error);
        }
    }
    
    initializeDOM() {
        // 알림 패널 생성
        this.createNotificationPanel();
        
        // 알림 벨 아이콘 생성 또는 찾기
        this.initNotificationBell();
        
        // 페이지 가시성 변경 감지
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.loadNotifications(); // 페이지 다시 보일 때 알림 새로고침
            }
        });
    }
    
    createNotificationPanel() {
        // 기존 패널 제거
        const existingPanel = document.getElementById('notification-panel');
        if (existingPanel) {
            existingPanel.remove();
        }
        
        const panel = document.createElement('div');
        panel.id = 'notification-panel';
        panel.className = 'notification-panel';
        panel.innerHTML = `
            <div class="notification-header">
                <h6><i class="fas fa-bell"></i> 알림</h6>
                <button class="btn-close" onclick="notificationSystem.closePanel()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="notification-filters">
                <button class="filter-btn active" data-filter="all">전체</button>
                <button class="filter-btn" data-filter="unread">읽지않음</button>
                <button class="filter-btn" data-filter="urgent">긴급</button>
            </div>
            <div class="notification-list" id="notification-list">
                <div class="loading">
                    <i class="fas fa-spinner fa-spin"></i> 알림을 불러오는 중...
                </div>
            </div>
            <div class="notification-footer">
                <button onclick="notificationSystem.markAllAsRead()" class="btn-mark-all">
                    모두 읽음 처리
                </button>
            </div>
        `;
        
        document.body.appendChild(panel);
        
        // 필터 이벤트 추가
        panel.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                panel.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.filterNotifications(e.target.dataset.filter);
            });
        });
    }
    
    initNotificationBell() {
        let bellIcon = document.getElementById('notification-bell');
        
        if (!bellIcon) {
            // 네비게이션 바에서 적절한 위치 찾기
            const navbar = document.querySelector('.navbar, .header, .top-nav');
            if (navbar) {
                bellIcon = document.createElement('div');
                bellIcon.id = 'notification-bell';
                bellIcon.className = 'notification-bell';
                bellIcon.innerHTML = `
                    <i class="fas fa-bell"></i>
                    <span class="badge" id="notification-badge">0</span>
                `;
                navbar.appendChild(bellIcon);
            }
        }
        
        if (bellIcon) {
            bellIcon.addEventListener('click', () => this.togglePanel());
        }
    }
    
    async requestNotificationPermission() {
        if ('Notification' in window) {
            const permission = await Notification.requestPermission();
            this.pushPermission = permission;
            
            if (permission === 'granted') {
                console.log('✅ Push notification permission granted');
            } else {
                console.log('⚠️ Push notification permission denied');
            }
        }
    }
    
    async loadNotifications() {
        try {
            const response = await fetch(this.apiEndpoint, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.updateNotifications(data.notifications || []);
            this.updateStats(data.stats || {});
            
        } catch (error) {
            console.error('Failed to load notifications:', error);
            this.showErrorMessage('알림을 불러올 수 없습니다.');
        }
    }
    
    updateNotifications(newNotifications) {
        const prevUnreadCount = this.unreadCount;
        this.notifications = newNotifications;
        this.unreadCount = newNotifications.filter(n => !n.is_read).length;
        
        // 새 알림이 있으면 푸시 알림 표시
        if (this.unreadCount > prevUnreadCount) {
            const newNotifications = newNotifications.filter(n => !n.is_read).slice(0, this.unreadCount - prevUnreadCount);
            newNotifications.forEach(notification => {
                this.showPushNotification(notification);
            });
        }
        
        this.renderNotifications();
        this.updateBadge();
    }
    
    updateStats(stats) {
        this.stats = stats;
        // 통계 정보가 필요한 곳에 업데이트
    }
    
    renderNotifications() {
        const listElement = document.getElementById('notification-list');
        if (!listElement) return;
        
        if (this.notifications.length === 0) {
            listElement.innerHTML = `
                <div class="no-notifications">
                    <i class="fas fa-bell-slash"></i>
                    <p>새로운 알림이 없습니다.</p>
                </div>
            `;
            return;
        }
        
        const html = this.notifications.map(notification => this.renderNotificationItem(notification)).join('');
        listElement.innerHTML = html;
    }
    
    renderNotificationItem(notification) {
        const createdAt = new Date(notification.created_at);
        const timeAgo = this.getTimeAgo(createdAt);
        
        const priorityClass = this.getPriorityClass(notification.priority);
        const typeIcon = this.getTypeIcon(notification.type);
        
        return `
            <div class="notification-item ${notification.is_read ? 'read' : 'unread'} ${priorityClass}" 
                 data-id="${notification.id}" data-priority="${notification.priority}" data-type="${notification.type}">
                <div class="notification-icon">
                    <i class="fas ${typeIcon}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${this.escapeHtml(notification.title)}</div>
                    <div class="notification-message">${this.escapeHtml(notification.message)}</div>
                    <div class="notification-meta">
                        <span class="notification-time">${timeAgo}</span>
                        ${notification.priority === 'critical' ? '<span class="priority-badge critical">긴급</span>' : ''}
                        ${notification.priority === 'high' ? '<span class="priority-badge high">높음</span>' : ''}
                    </div>
                </div>
                <div class="notification-actions">
                    ${!notification.is_read ? '<button class="btn-mark-read" onclick="notificationSystem.markAsRead(\'' + notification.id + '\')"><i class="fas fa-check"></i></button>' : ''}
                    ${notification.action_url ? '<button class="btn-action" onclick="notificationSystem.handleAction(\'' + notification.action_url + '\')"><i class="fas fa-external-link-alt"></i></button>' : ''}
                </div>
            </div>
        `;
    }
    
    getPriorityClass(priority) {
        const classes = {
            'critical': 'priority-critical',
            'high': 'priority-high',
            'medium': 'priority-medium',
            'low': 'priority-low'
        };
        return classes[priority] || 'priority-medium';
    }
    
    getTypeIcon(type) {
        const icons = {
            'info': 'fa-info-circle',
            'warning': 'fa-exclamation-triangle',
            'error': 'fa-times-circle',
            'success': 'fa-check-circle',
            'urgent': 'fa-bell'
        };
        return icons[type] || 'fa-bell';
    }
    
    updateBadge() {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            badge.textContent = this.unreadCount;
            badge.style.display = this.unreadCount > 0 ? 'inline' : 'none';
        }
    }
    
    togglePanel() {
        const panel = document.getElementById('notification-panel');
        if (panel) {
            panel.classList.toggle('active');
            
            if (panel.classList.contains('active')) {
                this.loadNotifications(); // 패널 열 때 새로고침
            }
        }
    }
    
    closePanel() {
        const panel = document.getElementById('notification-panel');
        if (panel) {
            panel.classList.remove('active');
        }
    }
    
    filterNotifications(filter) {
        const items = document.querySelectorAll('.notification-item');
        
        items.forEach(item => {
            let show = true;
            
            switch (filter) {
                case 'unread':
                    show = item.classList.contains('unread');
                    break;
                case 'urgent':
                    show = item.dataset.priority === 'critical' || item.dataset.priority === 'high';
                    break;
                case 'all':
                default:
                    show = true;
                    break;
            }
            
            item.style.display = show ? 'block' : 'none';
        });
    }
    
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/dashboard/notification/${notificationId}/read/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.getCSRFToken(),
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                // UI 업데이트
                const item = document.querySelector(`[data-id="${notificationId}"]`);
                if (item) {
                    item.classList.remove('unread');
                    item.classList.add('read');
                    
                    // 액션 버튼 제거
                    const markReadBtn = item.querySelector('.btn-mark-read');
                    if (markReadBtn) {
                        markReadBtn.remove();
                    }
                }
                
                this.unreadCount = Math.max(0, this.unreadCount - 1);
                this.updateBadge();
            }
            
        } catch (error) {
            console.error('Failed to mark notification as read:', error);
        }
    }
    
    async markAllAsRead() {
        const unreadItems = document.querySelectorAll('.notification-item.unread');
        const promises = Array.from(unreadItems).map(item => 
            this.markAsRead(item.dataset.id)
        );
        
        await Promise.all(promises);
    }
    
    handleAction(actionUrl) {
        if (actionUrl) {
            if (actionUrl.startsWith('http')) {
                window.open(actionUrl, '_blank');
            } else {
                window.location.href = actionUrl;
            }
            this.closePanel();
        }
    }
    
    showPushNotification(notification) {
        if (this.pushPermission === 'granted' && 'Notification' in window) {
            const options = {
                body: notification.message,
                icon: '/static/images/notification-icon.png',
                badge: '/static/images/badge-icon.png',
                tag: notification.id,
                data: {
                    notificationId: notification.id,
                    actionUrl: notification.action_url
                },
                requireInteraction: notification.priority === 'critical'
            };
            
            const pushNotification = new Notification(notification.title, options);
            
            pushNotification.onclick = () => {
                window.focus();
                this.togglePanel();
                if (notification.action_url) {
                    this.handleAction(notification.action_url);
                }
                pushNotification.close();
            };
            
            // 자동 닫기 (긴급하지 않은 경우)
            if (notification.priority !== 'critical') {
                setTimeout(() => pushNotification.close(), 5000);
            }
        }
    }
    
    startPolling() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.pollingTimer = setInterval(() => {
            if (!document.hidden) { // 탭이 활성화된 경우에만 폴링
                this.loadNotifications();
            }
        }, this.pollingInterval);
        
        console.log('🔄 Notification polling started');
    }
    
    stopPolling() {
        if (this.pollingTimer) {
            clearInterval(this.pollingTimer);
            this.pollingTimer = null;
        }
        this.isPolling = false;
        
        console.log('⏹️ Notification polling stopped');
    }
    
    showErrorMessage(message) {
        const listElement = document.getElementById('notification-list');
        if (listElement) {
            listElement.innerHTML = `
                <div class="notification-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>${message}</p>
                    <button onclick="notificationSystem.loadNotifications()">다시 시도</button>
                </div>
            `;
        }
    }
    
    getTimeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return '방금 전';
        if (diffMins < 60) return `${diffMins}분 전`;
        if (diffHours < 24) return `${diffHours}시간 전`;
        if (diffDays < 7) return `${diffDays}일 전`;
        
        return date.toLocaleDateString();
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        // meta 태그에서 찾기
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }
}

// 전역 인스턴스 생성
let notificationSystem;

// DOM 로드 후 초기화
document.addEventListener('DOMContentLoaded', () => {
    notificationSystem = new NotificationSystem();
});

// 서비스 워커 등록 (푸시 알림용)
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/js/sw.js')
        .then(registration => {
            console.log('✅ Service Worker registered for notifications');
        })
        .catch(error => {
            console.error('❌ Service Worker registration failed:', error);
        });
}

export default NotificationSystem;