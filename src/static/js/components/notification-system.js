/**
 * 실시간 알림 시스템
 * 알림 표시, 읽음 처리, 실시간 업데이트
 */
class NotificationSystem {
    constructor() {
        this.notifications = [];
        this.unreadCount = 0;
        this.notificationContainer = null;
        this.notificationBell = null;
        this.notificationDropdown = null;
        this.pollInterval = null;
        
        this.init();
    }
    
    init() {
        this.createNotificationUI();
        this.attachEventListeners();
        this.loadNotifications();
        this.startPolling();
        this.requestNotificationPermission();
    }
    
    createNotificationUI() {
        // 알림 벨 아이콘 (헤더에 추가)
        const bellHTML = `
            <div class="notification-bell-wrapper">
                <button class="notification-bell" aria-label="알림">
                    <i class="bi bi-bell"></i>
                    <span class="notification-badge" style="display: none;">0</span>
                </button>
                
                <!-- 알림 드롭다운 -->
                <div class="notification-dropdown" style="display: none;">
                    <div class="notification-header">
                        <h6>알림</h6>
                        <div class="notification-actions">
                            <button class="btn-mark-all-read" title="모두 읽음">
                                <i class="bi bi-check-all"></i>
                            </button>
                            <button class="btn-notification-settings" title="설정">
                                <i class="bi bi-gear"></i>
                            </button>
                        </div>
                    </div>
                    <div class="notification-list">
                        <div class="loading-notifications">
                            <div class="spinner-border spinner-border-sm" role="status">
                                <span class="visually-hidden">로딩 중...</span>
                            </div>
                        </div>
                    </div>
                    <div class="notification-footer">
                        <a href="/notifications/" class="view-all-notifications">
                            모든 알림 보기 <i class="bi bi-arrow-right"></i>
                        </a>
                    </div>
                </div>
            </div>
        `;
        
        // 헤더에 알림 벨 추가
        const header = document.querySelector('.navbar-nav') || document.querySelector('header');
        if (header) {
            const li = document.createElement('li');
            li.className = 'nav-item notification-item';
            li.innerHTML = bellHTML;
            header.appendChild(li);
        }
        
        // 토스트 컨테이너 (화면 우측 상단)
        const toastContainer = document.createElement('div');
        toastContainer.className = 'notification-toast-container';
        toastContainer.setAttribute('aria-live', 'polite');
        toastContainer.setAttribute('aria-atomic', 'true');
        document.body.appendChild(toastContainer);
        
        // 요소 참조
        this.notificationBell = document.querySelector('.notification-bell');
        this.notificationBadge = document.querySelector('.notification-badge');
        this.notificationDropdown = document.querySelector('.notification-dropdown');
        this.notificationList = document.querySelector('.notification-list');
        this.toastContainer = toastContainer;
    }
    
    attachEventListeners() {
        // 알림 벨 클릭
        if (this.notificationBell) {
            this.notificationBell.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleDropdown();
            });
        }
        
        // 드롭다운 외부 클릭 시 닫기
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.notification-bell-wrapper')) {
                this.closeDropdown();
            }
        });
        
        // 모두 읽음 처리
        document.querySelector('.btn-mark-all-read')?.addEventListener('click', () => {
            this.markAllAsRead();
        });
        
        // 설정
        document.querySelector('.btn-notification-settings')?.addEventListener('click', () => {
            this.openSettings();
        });
        
        // 키보드 단축키 (Alt+N)
        document.addEventListener('keydown', (e) => {
            if (e.altKey && e.key === 'n') {
                this.toggleDropdown();
            }
        });
    }
    
    async loadNotifications() {
        try {
            const response = await fetch('/collaboration/notifications/');
            const data = await response.json();
            
            this.notifications = data.notifications;
            this.unreadCount = data.unread_count;
            
            this.renderNotifications();
            this.updateBadge();
        } catch (error) {
            console.error('알림 로드 실패:', error);
            this.showError();
        }
    }
    
    renderNotifications() {
        if (this.notifications.length === 0) {
            this.notificationList.innerHTML = `
                <div class="no-notifications">
                    <i class="bi bi-bell-slash"></i>
                    <p>새로운 알림이 없습니다</p>
                </div>
            `;
            return;
        }
        
        const html = this.notifications.map(notification => 
            this.renderNotificationItem(notification)
        ).join('');
        
        this.notificationList.innerHTML = html;
        
        // 개별 알림 클릭 이벤트
        this.notificationList.querySelectorAll('.notification-item').forEach(item => {
            item.addEventListener('click', () => {
                const id = item.dataset.notificationId;
                this.handleNotificationClick(id);
            });
        });
    }
    
    renderNotificationItem(notification) {
        const icon = this.getNotificationIcon(notification.type);
        const timeAgo = this.formatTimeAgo(notification.created_at);
        
        return `
            <div class="notification-item ${!notification.is_read ? 'unread' : ''}" 
                 data-notification-id="${notification.id}"
                 data-action-url="${notification.action_url || '#'}">
                <div class="notification-icon ${notification.type}">
                    ${icon}
                </div>
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-time">
                        <i class="bi bi-clock"></i> ${timeAgo}
                    </div>
                </div>
                ${!notification.is_read ? '<div class="unread-dot"></div>' : ''}
            </div>
        `;
    }
    
    getNotificationIcon(type) {
        const icons = {
            'comment': '<i class="bi bi-chat-dots"></i>',
            'mention': '<i class="bi bi-at"></i>',
            'reply': '<i class="bi bi-reply"></i>',
            'approval': '<i class="bi bi-check-circle"></i>',
            'rejection': '<i class="bi bi-x-circle"></i>',
            'assignment': '<i class="bi bi-person-plus"></i>',
            'system': '<i class="bi bi-info-circle"></i>'
        };
        
        return icons[type] || '<i class="bi bi-bell"></i>';
    }
    
    async handleNotificationClick(notificationId) {
        const notification = this.notifications.find(n => n.id == notificationId);
        if (!notification) return;
        
        // 읽음 처리
        if (!notification.is_read) {
            await this.markAsRead(notificationId);
        }
        
        // 액션 URL로 이동
        if (notification.action_url && notification.action_url !== '#') {
            window.location.href = notification.action_url;
        }
        
        this.closeDropdown();
    }
    
    async markAsRead(notificationId) {
        try {
            const response = await fetch(`/collaboration/notifications/${notificationId}/read/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            if (response.ok) {
                // 로컬 상태 업데이트
                const notification = this.notifications.find(n => n.id == notificationId);
                if (notification) {
                    notification.is_read = true;
                    this.unreadCount = Math.max(0, this.unreadCount - 1);
                    this.updateBadge();
                    this.renderNotifications();
                }
            }
        } catch (error) {
            console.error('알림 읽음 처리 실패:', error);
        }
    }
    
    async markAllAsRead() {
        try {
            const response = await fetch('/collaboration/notifications/read-all/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            if (response.ok) {
                // 모든 알림 읽음 처리
                this.notifications.forEach(n => n.is_read = true);
                this.unreadCount = 0;
                this.updateBadge();
                this.renderNotifications();
                
                this.showToast('모든 알림을 읽음으로 표시했습니다');
            }
        } catch (error) {
            console.error('알림 읽음 처리 실패:', error);
        }
    }
    
    updateBadge() {
        if (this.notificationBadge) {
            if (this.unreadCount > 0) {
                this.notificationBadge.textContent = this.unreadCount > 99 ? '99+' : this.unreadCount;
                this.notificationBadge.style.display = 'block';
                
                // 파비콘 업데이트
                this.updateFavicon(true);
            } else {
                this.notificationBadge.style.display = 'none';
                this.updateFavicon(false);
            }
        }
    }
    
    updateFavicon(hasNotification) {
        const link = document.querySelector("link[rel*='icon']") || document.createElement('link');
        link.type = 'image/x-icon';
        link.rel = 'shortcut icon';
        link.href = hasNotification ? '/static/favicon-notification.ico' : '/static/favicon.ico';
        document.getElementsByTagName('head')[0].appendChild(link);
    }
    
    showNewNotification(notification) {
        // 토스트 알림 표시
        const toast = document.createElement('div');
        toast.className = 'notification-toast show';
        toast.innerHTML = `
            <div class="toast-header">
                <strong class="me-auto">${notification.title}</strong>
                <small>${this.formatTimeAgo(notification.created_at)}</small>
                <button type="button" class="btn-close" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${notification.message}
            </div>
        `;
        
        this.toastContainer.appendChild(toast);
        
        // 클릭 이벤트
        toast.addEventListener('click', () => {
            this.handleNotificationClick(notification.id);
            toast.remove();
        });
        
        // 닫기 버튼
        toast.querySelector('.btn-close').addEventListener('click', (e) => {
            e.stopPropagation();
            toast.remove();
        });
        
        // 5초 후 자동 제거
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
        
        // 브라우저 알림
        if (this.hasNotificationPermission()) {
            this.showBrowserNotification(notification);
        }
        
        // 사운드 재생
        this.playNotificationSound();
    }
    
    showBrowserNotification(notification) {
        if ('Notification' in window && Notification.permission === 'granted') {
            const browserNotification = new Notification(notification.title, {
                body: notification.message,
                icon: '/static/images/notification-icon.png',
                badge: '/static/images/badge-icon.png',
                tag: `notification-${notification.id}`,
                requireInteraction: false
            });
            
            browserNotification.onclick = () => {
                window.focus();
                this.handleNotificationClick(notification.id);
                browserNotification.close();
            };
        }
    }
    
    playNotificationSound() {
        const audio = new Audio('/static/sounds/notification.mp3');
        audio.volume = 0.5;
        audio.play().catch(e => console.log('사운드 재생 실패:', e));
    }
    
    requestNotificationPermission() {
        if ('Notification' in window && Notification.permission === 'default') {
            setTimeout(() => {
                Notification.requestPermission().then(permission => {
                    if (permission === 'granted') {
                        this.showToast('알림이 활성화되었습니다');
                    }
                });
            }, 3000);
        }
    }
    
    hasNotificationPermission() {
        return 'Notification' in window && Notification.permission === 'granted';
    }
    
    startPolling() {
        // 30초마다 새 알림 확인
        this.pollInterval = setInterval(() => {
            this.checkNewNotifications();
        }, 30000);
    }
    
    async checkNewNotifications() {
        try {
            const response = await fetch('/collaboration/notifications/?unread_only=true');
            const data = await response.json();
            
            // 새 알림 확인
            const newNotifications = data.notifications.filter(n => 
                !this.notifications.find(existing => existing.id === n.id)
            );
            
            // 새 알림 추가
            newNotifications.forEach(notification => {
                this.notifications.unshift(notification);
                this.showNewNotification(notification);
            });
            
            if (newNotifications.length > 0) {
                this.unreadCount = data.unread_count;
                this.updateBadge();
                this.renderNotifications();
            }
        } catch (error) {
            console.error('새 알림 확인 실패:', error);
        }
    }
    
    toggleDropdown() {
        if (this.notificationDropdown.style.display === 'none') {
            this.openDropdown();
        } else {
            this.closeDropdown();
        }
    }
    
    openDropdown() {
        this.notificationDropdown.style.display = 'block';
        this.notificationBell.classList.add('active');
        this.loadNotifications(); // 최신 알림 로드
    }
    
    closeDropdown() {
        this.notificationDropdown.style.display = 'none';
        this.notificationBell.classList.remove('active');
    }
    
    openSettings() {
        // 알림 설정 모달 열기
        const modal = new NotificationSettingsModal();
        modal.show();
    }
    
    formatTimeAgo(datetime) {
        const date = new Date(datetime);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);
        
        if (diff < 60) return '방금 전';
        if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
        if (diff < 604800) return `${Math.floor(diff / 86400)}일 전`;
        
        return date.toLocaleDateString('ko-KR');
    }
    
    showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `notification-toast show ${type}`;
        toast.innerHTML = `
            <div class="toast-body">
                <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
                ${message}
            </div>
        `;
        
        this.toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    showError() {
        this.notificationList.innerHTML = `
            <div class="notification-error">
                <i class="bi bi-exclamation-triangle"></i>
                <p>알림을 불러올 수 없습니다</p>
                <button class="btn btn-sm btn-primary" onclick="notificationSystem.loadNotifications()">
                    다시 시도
                </button>
            </div>
        `;
    }
    
    destroy() {
        // 폴링 중지
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
    }
}

// 알림 설정 모달
class NotificationSettingsModal {
    constructor() {
        this.modal = null;
    }
    
    show() {
        const modalHTML = `
            <div class="modal fade" id="notificationSettingsModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">알림 설정</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="notification-settings">
                                <div class="setting-item">
                                    <div class="setting-label">
                                        <strong>댓글 알림</strong>
                                        <p class="text-muted">내 게시물에 댓글이 달렸을 때</p>
                                    </div>
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" id="commentNotification" checked>
                                    </div>
                                </div>
                                
                                <div class="setting-item">
                                    <div class="setting-label">
                                        <strong>멘션 알림</strong>
                                        <p class="text-muted">누군가 나를 멘션했을 때</p>
                                    </div>
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" id="mentionNotification" checked>
                                    </div>
                                </div>
                                
                                <div class="setting-item">
                                    <div class="setting-label">
                                        <strong>답글 알림</strong>
                                        <p class="text-muted">내 댓글에 답글이 달렸을 때</p>
                                    </div>
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" id="replyNotification" checked>
                                    </div>
                                </div>
                                
                                <div class="setting-item">
                                    <div class="setting-label">
                                        <strong>브라우저 알림</strong>
                                        <p class="text-muted">데스크톱 알림 표시</p>
                                    </div>
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" id="browserNotification">
                                    </div>
                                </div>
                                
                                <div class="setting-item">
                                    <div class="setting-label">
                                        <strong>알림음</strong>
                                        <p class="text-muted">알림 사운드 재생</p>
                                    </div>
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" id="soundNotification" checked>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">취소</button>
                            <button type="button" class="btn btn-primary" onclick="this.saveSettings()">저장</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 모달 추가
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // Bootstrap 모달 초기화
        this.modal = new bootstrap.Modal(document.getElementById('notificationSettingsModal'));
        this.modal.show();
    }
    
    saveSettings() {
        // 설정 저장 로직
        const settings = {
            comment: document.getElementById('commentNotification').checked,
            mention: document.getElementById('mentionNotification').checked,
            reply: document.getElementById('replyNotification').checked,
            browser: document.getElementById('browserNotification').checked,
            sound: document.getElementById('soundNotification').checked
        };
        
        localStorage.setItem('notificationSettings', JSON.stringify(settings));
        
        // 브라우저 알림 권한 요청
        if (settings.browser && !notificationSystem.hasNotificationPermission()) {
            Notification.requestPermission();
        }
        
        this.modal.hide();
        notificationSystem.showToast('알림 설정이 저장되었습니다');
    }
}

// 전역 인스턴스 생성
let notificationSystem;
document.addEventListener('DOMContentLoaded', () => {
    notificationSystem = new NotificationSystem();
});