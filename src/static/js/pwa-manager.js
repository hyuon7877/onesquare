/**
 * PWA Manager - Progressive Web App 기능 관리
 * 
 * 기능:
 * - Service Worker 등록 및 관리
 * - 앱 설치 프롬프트 처리
 * - 오프라인/온라인 상태 관리
 * - 푸시 알림 설정
 */

class PWAManager {
    constructor() {
        this.serviceWorkerPath = '/static/js/sw.js';
        this.deferredPrompt = null;
        this.isOnline = navigator.onLine;
        this.init();
    }

    async init() {
        // Service Worker 등록
        await this.registerServiceWorker();
        
        // 이벤트 리스너 설정
        this.setupEventListeners();
        
        // 네트워크 상태 모니터링
        this.monitorNetworkStatus();
        
        // 앱 설치 상태 체크
        this.checkInstallation();
    }

    async registerServiceWorker() {
        if (!('serviceWorker' in navigator)) {
            console.log('Service Worker를 지원하지 않는 브라우저입니다.');
            return;
        }

        try {
            const registration = await navigator.serviceWorker.register(this.serviceWorkerPath, {
                scope: '/'
            });
            
            console.log('Service Worker 등록 성공:', registration);
            
            // 업데이트 체크
            registration.addEventListener('updatefound', () => {
                const newWorker = registration.installing;
                
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        // 새 버전 사용 가능
                        this.showUpdateNotification();
                    }
                });
            });
            
            // 주기적으로 업데이트 체크 (1시간마다)
            setInterval(() => {
                registration.update();
            }, 3600000);
            
        } catch (error) {
            console.error('Service Worker 등록 실패:', error);
        }
    }

    setupEventListeners() {
        // 앱 설치 프롬프트
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallButton();
        });
        
        // 앱 설치 완료
        window.addEventListener('appinstalled', () => {
            console.log('PWA 설치 완료');
            this.deferredPrompt = null;
            this.hideInstallButton();
            this.showToast('OneSquare가 성공적으로 설치되었습니다!', 'success');
        });
        
        // 네트워크 상태 변경
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
        
        // Service Worker 메시지
        navigator.serviceWorker.addEventListener('message', (event) => {
            this.handleServiceWorkerMessage(event);
        });
        
        // 페이지 가시성 변경
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.syncData();
            }
        });
    }

    monitorNetworkStatus() {
        const indicator = document.getElementById('network-indicator');
        const statusText = document.getElementById('network-status-text');
        
        if (!indicator) return;
        
        const updateStatus = () => {
            if (this.isOnline) {
                indicator.className = 'network-indicator online';
                statusText.textContent = '온라인';
                indicator.style.display = 'none'; // 온라인일 때는 숨김
            } else {
                indicator.className = 'network-indicator offline';
                statusText.textContent = '오프라인';
                indicator.style.display = 'block';
            }
        };
        
        updateStatus();
    }

    handleOnline() {
        this.isOnline = true;
        this.monitorNetworkStatus();
        this.showToast('인터넷 연결이 복구되었습니다.', 'success');
        
        // 오프라인 동안 대기 중인 데이터 동기화
        this.syncOfflineData();
    }

    handleOffline() {
        this.isOnline = false;
        this.monitorNetworkStatus();
        this.showToast('오프라인 모드로 전환되었습니다.', 'warning');
    }

    async syncOfflineData() {
        if (!('sync' in self.registration)) return;
        
        try {
            await self.registration.sync.register('offline-sync');
            console.log('오프라인 데이터 동기화 시작');
        } catch (error) {
            console.error('동기화 실패:', error);
        }
    }

    checkInstallation() {
        // 독립 실행 모드 체크
        const isStandalone = window.matchMedia('(display-mode: standalone)').matches || 
                           window.navigator.standalone || 
                           document.referrer.includes('android-app://');
        
        if (isStandalone) {
            console.log('PWA가 설치된 상태로 실행 중');
            // GA나 다른 분석 도구로 설치 상태 추적
            this.trackInstallation();
        }
    }

    showInstallButton() {
        const banner = document.getElementById('pwa-install-banner');
        const dismissed = localStorage.getItem('pwa-install-dismissed');
        
        if (banner && dismissed !== 'true') {
            setTimeout(() => {
                banner.style.display = 'block';
                banner.classList.add('show');
            }, 3000); // 3초 후 표시
        }
    }

    hideInstallButton() {
        const banner = document.getElementById('pwa-install-banner');
        if (banner) {
            banner.style.display = 'none';
        }
    }

    async installApp() {
        if (!this.deferredPrompt) {
            console.log('설치 프롬프트를 사용할 수 없습니다.');
            return;
        }
        
        // 설치 프롬프트 표시
        this.deferredPrompt.prompt();
        
        // 사용자 응답 대기
        const { outcome } = await this.deferredPrompt.userChoice;
        console.log('사용자 선택:', outcome);
        
        if (outcome === 'accepted') {
            console.log('사용자가 PWA 설치를 수락했습니다.');
        } else {
            console.log('사용자가 PWA 설치를 거부했습니다.');
        }
        
        this.deferredPrompt = null;
    }

    showUpdateNotification() {
        const updateBanner = `
            <div class="update-banner" id="update-banner">
                <div class="update-content">
                    <p>새로운 버전이 있습니다. 업데이트하시겠습니까?</p>
                    <button onclick="window.pwaManager.updateApp()" class="btn-update">업데이트</button>
                    <button onclick="document.getElementById('update-banner').remove()" class="btn-later">나중에</button>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', updateBanner);
    }

    updateApp() {
        window.location.reload();
    }

    handleServiceWorkerMessage(event) {
        const { type, data } = event.data;
        
        switch (type) {
            case 'CACHE_UPDATED':
                console.log('캐시가 업데이트되었습니다:', data);
                break;
            case 'SYNC_COMPLETE':
                this.showToast('데이터 동기화 완료', 'success');
                break;
            case 'NOTIFICATION':
                this.showNotification(data);
                break;
            default:
                console.log('Service Worker 메시지:', event.data);
        }
    }

    showNotification(data) {
        if (!('Notification' in window)) return;
        
        if (Notification.permission === 'granted') {
            new Notification(data.title, {
                body: data.body,
                icon: '/static/images/icons/icon-192x192.png',
                badge: '/static/images/icons/icon-72x72.png',
                vibrate: [200, 100, 200],
                data: data
            });
        }
    }

    async requestNotificationPermission() {
        if (!('Notification' in window)) {
            console.log('이 브라우저는 알림을 지원하지 않습니다.');
            return false;
        }
        
        if (Notification.permission === 'granted') {
            return true;
        }
        
        if (Notification.permission !== 'denied') {
            const permission = await Notification.requestPermission();
            return permission === 'granted';
        }
        
        return false;
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container') || this.createToastContainer();
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">${this.getToastIcon(type)}</div>
            <div class="toast-message">${message}</div>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        container.appendChild(toast);
        
        // 애니메이션
        setTimeout(() => toast.classList.add('show'), 10);
        
        // 자동 제거
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    createToastContainer() {
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    }

    getToastIcon(type) {
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        return icons[type] || icons.info;
    }

    async syncData() {
        // Notion 데이터 동기화
        if (this.isOnline && navigator.serviceWorker.controller) {
            navigator.serviceWorker.controller.postMessage({
                type: 'SYNC_NOTION_DATA'
            });
        }
    }

    trackInstallation() {
        // 설치 추적 (Google Analytics 등)
        if (typeof gtag !== 'undefined') {
            gtag('event', 'pwa_installed', {
                event_category: 'engagement',
                event_label: 'PWA Installation'
            });
        }
    }

    // 캐시 관리
    async clearCache() {
        if ('caches' in window) {
            const cacheNames = await caches.keys();
            await Promise.all(
                cacheNames.map(cacheName => caches.delete(cacheName))
            );
            this.showToast('캐시가 초기화되었습니다.', 'success');
        }
    }

    // 캐시 크기 확인
    async getCacheSize() {
        if ('storage' in navigator && 'estimate' in navigator.storage) {
            const estimate = await navigator.storage.estimate();
            const usage = (estimate.usage / 1024 / 1024).toFixed(2);
            const quota = (estimate.quota / 1024 / 1024).toFixed(2);
            
            console.log(`캐시 사용량: ${usage}MB / ${quota}MB`);
            return { usage, quota };
        }
        return null;
    }
}

// 전역 인스턴스 생성
window.pwaManager = new PWAManager();

// Toast 스타일 추가
const style = document.createElement('style');
style.textContent = `
    .toast {
        display: flex;
        align-items: center;
        background: white;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
        min-width: 300px;
        max-width: 500px;
    }
    
    .toast.show {
        opacity: 1;
        transform: translateX(0);
    }
    
    .toast-icon {
        width: 24px;
        height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-right: 12px;
        font-weight: bold;
    }
    
    .toast-success .toast-icon {
        background: #d4edda;
        color: #155724;
    }
    
    .toast-error .toast-icon {
        background: #f8d7da;
        color: #721c24;
    }
    
    .toast-warning .toast-icon {
        background: #fff3cd;
        color: #856404;
    }
    
    .toast-info .toast-icon {
        background: #d1ecf1;
        color: #0c5460;
    }
    
    .toast-message {
        flex: 1;
        color: #333;
    }
    
    .toast-close {
        background: none;
        border: none;
        font-size: 24px;
        color: #999;
        cursor: pointer;
        padding: 0;
        margin-left: 12px;
    }
    
    .toast-close:hover {
        color: #333;
    }
    
    .update-banner {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: #0A84FF;
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 1002;
    }
    
    .update-content {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .btn-update, .btn-later {
        padding: 8px 16px;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
    }
    
    .btn-update {
        background: white;
        color: #0A84FF;
    }
    
    .btn-later {
        background: transparent;
        color: white;
        border: 1px solid rgba(255,255,255,0.3);
    }
`;
document.head.appendChild(style);