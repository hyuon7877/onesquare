/**
 * OneSquare PWA - 푸시 알림 관리자
 * 
 * 푸시 알림 권한 요청, 구독, 발송 처리
 */

class PushNotificationManager {
    constructor() {
        this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
        this.subscription = null;
        this.vapidPublicKey = null; // 서버에서 설정
        this.registration = null;
        
        this.init();
    }

    /**
     * 초기화
     */
    async init() {
        if (!this.isSupported) {
            console.warn('[PushManager] Push notifications not supported');
            return;
        }

        try {
            // Service Worker 등록 대기
            this.registration = await navigator.serviceWorker.ready;
            
            // 기존 구독 확인
            this.subscription = await this.registration.pushManager.getSubscription();
            
            // VAPID 공개키 가져오기
            await this.loadVAPIDKey();
            
            console.log('[PushManager] Initialized successfully');
        } catch (error) {
            console.error('[PushManager] Initialization failed:', error);
        }
    }

    /**
     * VAPID 공개키 로드
     */
    async loadVAPIDKey() {
        try {
            const response = await fetch('/api/pwa/vapid-key/');
            if (response.ok) {
                const data = await response.json();
                this.vapidPublicKey = data.publicKey;
            }
        } catch (error) {
            console.warn('[PushManager] Failed to load VAPID key:', error);
            // 개발용 기본키 (실제 운영에서는 서버에서 제공)
            this.vapidPublicKey = 'BEl62iUYgUivxIkv69yViEuiBIa40HI80NqIUHngOiZhgUq-dS-bWlzlVYfVjkCDKuP14k6RVEiPUY-BqBjPFSY';
        }
    }

    /**
     * 알림 권한 요청
     */
    async requestPermission() {
        if (!this.isSupported) {
            throw new Error('Push notifications not supported');
        }

        const permission = await Notification.requestPermission();
        
        if (permission === 'granted') {
            console.log('[PushManager] Notification permission granted');
            return true;
        } else if (permission === 'denied') {
            console.warn('[PushManager] Notification permission denied');
            return false;
        } else {
            console.warn('[PushManager] Notification permission dismissed');
            return false;
        }
    }

    /**
     * 푸시 구독
     */
    async subscribe() {
        if (!this.isSupported || !this.registration) {
            throw new Error('Push notifications not supported or service worker not ready');
        }

        // 권한 확인
        if (Notification.permission !== 'granted') {
            const granted = await this.requestPermission();
            if (!granted) {
                throw new Error('Notification permission required');
            }
        }

        try {
            // 푸시 구독 생성
            this.subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
            });

            // 서버에 구독 정보 전송
            await this.sendSubscriptionToServer(this.subscription);
            
            console.log('[PushManager] Subscription successful');
            return this.subscription;

        } catch (error) {
            console.error('[PushManager] Subscription failed:', error);
            throw error;
        }
    }

    /**
     * 푸시 구독 해제
     */
    async unsubscribe() {
        if (!this.subscription) {
            console.warn('[PushManager] No active subscription to unsubscribe');
            return false;
        }

        try {
            const successful = await this.subscription.unsubscribe();
            
            if (successful) {
                // 서버에 구독 해제 알림
                await this.removeSubscriptionFromServer(this.subscription);
                this.subscription = null;
                console.log('[PushManager] Unsubscribed successfully');
            }
            
            return successful;

        } catch (error) {
            console.error('[PushManager] Unsubscribe failed:', error);
            return false;
        }
    }

    /**
     * 서버에 구독 정보 전송
     */
    async sendSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/api/pwa/push/subscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    subscription: subscription.toJSON(),
                    user_agent: navigator.userAgent,
                    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const result = await response.json();
            console.log('[PushManager] Subscription sent to server:', result);

        } catch (error) {
            console.error('[PushManager] Failed to send subscription to server:', error);
            throw error;
        }
    }

    /**
     * 서버에서 구독 제거
     */
    async removeSubscriptionFromServer(subscription) {
        try {
            const response = await fetch('/api/pwa/push/unsubscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    endpoint: subscription.endpoint
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

        } catch (error) {
            console.error('[PushManager] Failed to remove subscription from server:', error);
        }
    }

    /**
     * 테스트 알림 전송
     */
    async sendTestNotification() {
        if (!this.subscription) {
            throw new Error('Not subscribed to push notifications');
        }

        try {
            const response = await fetch('/api/pwa/push/test/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify({
                    title: 'OneSquare 테스트 알림',
                    message: '푸시 알림이 정상적으로 작동합니다!',
                    url: '/'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            console.log('[PushManager] Test notification sent');

        } catch (error) {
            console.error('[PushManager] Failed to send test notification:', error);
            throw error;
        }
    }

    /**
     * 로컬 알림 표시 (개발/테스트용)
     */
    async showLocalNotification(title, options = {}) {
        if (Notification.permission !== 'granted') {
            console.warn('[PushManager] Notification permission not granted');
            return;
        }

        const defaultOptions = {
            body: 'OneSquare에서 새로운 업데이트가 있습니다.',
            icon: '/static/images/icons/icon-192x192.png',
            badge: '/static/images/icons/badge-72x72.png',
            tag: 'onesquare-notification',
            requireInteraction: false,
            actions: [
                { action: 'open', title: '열기' },
                { action: 'close', title: '닫기' }
            ]
        };

        const notification = new Notification(title, { ...defaultOptions, ...options });

        notification.onclick = (event) => {
            event.preventDefault();
            window.focus();
            notification.close();
        };

        // 5초 후 자동 닫기
        setTimeout(() => {
            notification.close();
        }, 5000);

        return notification;
    }

    /**
     * 알림 설정 관리
     */
    async getNotificationSettings() {
        try {
            const response = await fetch('/api/pwa/push/settings/');
            if (response.ok) {
                return await response.json();
            }
            
            // 기본 설정 반환
            return {
                enabled: true,
                types: {
                    notion_sync: true,
                    task_updates: true,
                    system_updates: false
                },
                quiet_hours: {
                    enabled: false,
                    start: '22:00',
                    end: '08:00'
                }
            };

        } catch (error) {
            console.error('[PushManager] Failed to get notification settings:', error);
            return null;
        }
    }

    /**
     * 알림 설정 업데이트
     */
    async updateNotificationSettings(settings) {
        try {
            const response = await fetch('/api/pwa/push/settings/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(settings)
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();

        } catch (error) {
            console.error('[PushManager] Failed to update notification settings:', error);
            throw error;
        }
    }

    /**
     * 알림 통계 조회
     */
    async getNotificationStats() {
        try {
            const response = await fetch('/api/pwa/push/stats/');
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('[PushManager] Failed to get notification stats:', error);
        }
        return null;
    }

    /**
     * 구독 상태 확인
     */
    getSubscriptionStatus() {
        return {
            isSupported: this.isSupported,
            permission: Notification.permission,
            isSubscribed: !!this.subscription,
            subscription: this.subscription,
            hasVAPIDKey: !!this.vapidPublicKey
        };
    }

    /**
     * 알림 권한 상태 확인
     */
    static checkPermissionStatus() {
        if (!('Notification' in window)) {
            return 'unsupported';
        }
        return Notification.permission;
    }

    /**
     * 브라우저별 호환성 체크
     */
    static getBrowserSupport() {
        const userAgent = navigator.userAgent.toLowerCase();
        
        return {
            pushSupported: 'serviceWorker' in navigator && 'PushManager' in window,
            notificationSupported: 'Notification' in window,
            browser: {
                chrome: userAgent.includes('chrome') && !userAgent.includes('edg'),
                firefox: userAgent.includes('firefox'),
                safari: userAgent.includes('safari') && !userAgent.includes('chrome'),
                edge: userAgent.includes('edg'),
            },
            mobile: /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
        };
    }

    /**
     * 유틸리티 메서드들
     */
    
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }

    /**
     * 이벤트 리스너
     */
    onPermissionChange(callback) {
        // 권한 상태 변경 감지 (폴링 방식)
        let lastPermission = Notification.permission;
        
        const checkPermission = () => {
            const currentPermission = Notification.permission;
            if (currentPermission !== lastPermission) {
                lastPermission = currentPermission;
                callback(currentPermission);
            }
        };

        const intervalId = setInterval(checkPermission, 1000);
        
        // 정리 함수 반환
        return () => clearInterval(intervalId);
    }

    onSubscriptionChange(callback) {
        // 구독 상태 변경 감지
        let lastSubscribed = !!this.subscription;
        
        const checkSubscription = () => {
            const currentSubscribed = !!this.subscription;
            if (currentSubscribed !== lastSubscribed) {
                lastSubscribed = currentSubscribed;
                callback(currentSubscribed, this.subscription);
            }
        };

        const intervalId = setInterval(checkSubscription, 2000);
        return () => clearInterval(intervalId);
    }
}

// 전역 인스턴스
const pushManager = new PushNotificationManager();

export default pushManager;