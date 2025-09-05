/**
 * OneSquare PWA 관리자
 * 
 * Service Worker 등록, PWA 설치, 오프라인 상태 관리
 */

class PWAManager {
  constructor() {
    this.swRegistration = null;
    this.isOnline = navigator.onLine;
    this.installPrompt = null;
    this.pushSubscription = null;
    this.vapidPublicKey = null;
    
    this.init();
  }

  /**
   * PWA 초기화
   */
  async init() {
    console.log('[PWA] Initializing PWA Manager...');
    
    try {
      // Service Worker 지원 확인
      if (!('serviceWorker' in navigator)) {
        console.warn('[PWA] Service Worker not supported');
        return;
      }
      
      // Service Worker 등록
      await this.registerServiceWorker();
      
      // 이벤트 리스너 설정
      this.setupEventListeners();
      
      // PWA 설치 버튼 설정
      this.setupInstallButton();
      
      // 온라인/오프라인 상태 표시
      this.updateOnlineStatus();
      
      // 캐시 상태 확인
      await this.checkCacheStatus();
      
      // 푸시 알림 초기화
      await this.initializePushNotifications();
      
      console.log('[PWA] PWA Manager initialized successfully');
      
    } catch (error) {
      console.error('[PWA] Initialization failed:', error);
    }
  }

  /**
   * Service Worker 등록
   */
  async registerServiceWorker() {
    try {
      console.log('[PWA] Registering Service Worker...');
      
      this.swRegistration = await navigator.serviceWorker.register('/static/js/sw.js', {
        scope: '/'
      });
      
      console.log('[PWA] Service Worker registered:', this.swRegistration);
      
      // Service Worker 업데이트 확인
      this.swRegistration.addEventListener('updatefound', () => {
        console.log('[PWA] Service Worker update found');
        this.handleSwUpdate(this.swRegistration.installing);
      });
      
      // 즉시 활성화된 Service Worker 확인
      if (this.swRegistration.active) {
        console.log('[PWA] Service Worker already active');
      }
      
      return this.swRegistration;
      
    } catch (error) {
      console.error('[PWA] Service Worker registration failed:', error);
      throw error;
    }
  }

  /**
   * Service Worker 업데이트 처리
   */
  handleSwUpdate(installingWorker) {
    console.log('[PWA] Service Worker installing...');
    
    installingWorker.addEventListener('statechange', () => {
      console.log('[PWA] Service Worker state:', installingWorker.state);
      
      if (installingWorker.state === 'installed') {
        if (navigator.serviceWorker.controller) {
          // 기존 SW가 있고 새로운 SW가 설치됨
          this.showUpdateAvailable();
        } else {
          // 첫 설치
          console.log('[PWA] Service Worker installed for the first time');
          this.showInstallComplete();
        }
      }
    });
  }

  /**
   * 이벤트 리스너 설정
   */
  setupEventListeners() {
    // 온라인/오프라인 상태 변경
    window.addEventListener('online', () => {
      console.log('[PWA] Back online');
      this.isOnline = true;
      this.updateOnlineStatus();
      this.triggerSync();
    });
    
    window.addEventListener('offline', () => {
      console.log('[PWA] Gone offline');
      this.isOnline = false;
      this.updateOnlineStatus();
    });
    
    // PWA 설치 이벤트
    window.addEventListener('beforeinstallprompt', (event) => {
      console.log('[PWA] Install prompt available');
      event.preventDefault();
      this.installPrompt = event;
      this.showInstallButton();
    });
    
    // PWA 설치 완료
    window.addEventListener('appinstalled', () => {
      console.log('[PWA] App installed successfully');
      this.hideInstallButton();
      this.showToast('OneSquare가 성공적으로 설치되었습니다!', 'success');
    });
    
    // Service Worker 메시지 처리
    navigator.serviceWorker.addEventListener('message', (event) => {
      console.log('[PWA] Message from SW:', event.data);
      this.handleServiceWorkerMessage(event.data);
    });
  }

  /**
   * Service Worker 메시지 처리
   */
  handleServiceWorkerMessage(data) {
    const { type, payload } = data;
    
    switch (type) {
      case 'CACHE_UPDATED':
        this.showToast('앱이 업데이트되었습니다', 'info');
        break;
        
      case 'OFFLINE_READY':
        this.showToast('오프라인 모드 준비 완료', 'success');
        break;
        
      case 'SYNC_COMPLETE':
        this.showToast('데이터 동기화 완료', 'success');
        break;
        
      case 'SYNC_FAILED':
        this.showToast('데이터 동기화 실패', 'error');
        break;
    }
  }

  /**
   * PWA 설치 버튼 설정
   */
  setupInstallButton() {
    const installBtn = document.getElementById('pwa-install-btn');
    
    if (installBtn) {
      installBtn.addEventListener('click', () => {
        this.installPWA();
      });
    }
    
    // 이미 설치된 경우 버튼 숨기기
    if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) {
      this.hideInstallButton();
    }
  }

  /**
   * PWA 설치 실행
   */
  async installPWA() {
    if (!this.installPrompt) {
      console.warn('[PWA] Install prompt not available');
      return;
    }
    
    try {
      console.log('[PWA] Showing install prompt...');
      
      const result = await this.installPrompt.prompt();
      console.log('[PWA] Install prompt result:', result);
      
      if (result.outcome === 'accepted') {
        console.log('[PWA] User accepted install');
      } else {
        console.log('[PWA] User declined install');
      }
      
      // 프롬프트 초기화
      this.installPrompt = null;
      this.hideInstallButton();
      
    } catch (error) {
      console.error('[PWA] Install failed:', error);
    }
  }

  /**
   * 설치 버튼 표시
   */
  showInstallButton() {
    const installBtn = document.getElementById('pwa-install-btn');
    if (installBtn) {
      installBtn.style.display = 'block';
    }
  }

  /**
   * 설치 버튼 숨기기
   */
  hideInstallButton() {
    const installBtn = document.getElementById('pwa-install-btn');
    if (installBtn) {
      installBtn.style.display = 'none';
    }
  }

  /**
   * 온라인 상태 업데이트
   */
  updateOnlineStatus() {
    const statusIndicator = document.getElementById('online-status');
    const offlineMessage = document.getElementById('offline-message');
    
    if (statusIndicator) {
      statusIndicator.className = this.isOnline ? 'online' : 'offline';
      statusIndicator.textContent = this.isOnline ? '온라인' : '오프라인';
    }
    
    if (offlineMessage) {
      offlineMessage.style.display = this.isOnline ? 'none' : 'block';
    }
    
    // 바디에 오프라인 클래스 추가/제거
    document.body.classList.toggle('offline-mode', !this.isOnline);
  }

  /**
   * 백그라운드 동기화 트리거
   */
  async triggerSync() {
    if (!this.swRegistration || !('sync' in window.ServiceWorkerRegistration.prototype)) {
      console.warn('[PWA] Background sync not supported');
      return;
    }
    
    try {
      console.log('[PWA] Triggering background sync...');
      await this.swRegistration.sync.register('notion-sync');
      console.log('[PWA] Background sync registered');
    } catch (error) {
      console.error('[PWA] Background sync failed:', error);
    }
  }

  /**
   * 캐시 상태 확인
   */
  async checkCacheStatus() {
    if (!this.swRegistration || !this.swRegistration.active) {
      return;
    }
    
    try {
      const channel = new MessageChannel();
      
      // 응답 처리
      channel.port1.onmessage = (event) => {
        console.log('[PWA] Cache status:', event.data);
        this.updateCacheStatusUI(event.data);
      };
      
      // Service Worker에 캐시 상태 요청
      this.swRegistration.active.postMessage({
        action: 'GET_CACHE_STATUS'
      }, [channel.port2]);
      
    } catch (error) {
      console.error('[PWA] Cache status check failed:', error);
    }
  }

  /**
   * 캐시 상태 UI 업데이트
   */
  updateCacheStatusUI(cacheStatus) {
    const statusElement = document.getElementById('cache-status');
    
    if (statusElement) {
      const totalCached = Object.values(cacheStatus).reduce((sum, count) => sum + count, 0);
      statusElement.textContent = `캐시된 항목: ${totalCached}개`;
    }
  }

  /**
   * 캐시 삭제
   */
  async clearCache() {
    if (!this.swRegistration || !this.swRegistration.active) {
      console.warn('[PWA] Service Worker not available for cache clearing');
      return;
    }
    
    try {
      console.log('[PWA] Clearing cache...');
      
      const channel = new MessageChannel();
      
      channel.port1.onmessage = (event) => {
        const result = event.data;
        if (result.success) {
          console.log('[PWA] Cache cleared successfully');
          this.showToast('캐시가 삭제되었습니다', 'success');
          this.checkCacheStatus(); // 상태 갱신
        } else {
          console.error('[PWA] Cache clear failed:', result.error);
          this.showToast('캐시 삭제에 실패했습니다', 'error');
        }
      };
      
      this.swRegistration.active.postMessage({
        action: 'CLEAR_CACHE'
      }, [channel.port2]);
      
    } catch (error) {
      console.error('[PWA] Cache clear failed:', error);
      this.showToast('캐시 삭제 중 오류가 발생했습니다', 'error');
    }
  }

  /**
   * 오프라인 큐에 작업 추가
   */
  async addToOfflineQueue(url, options, action) {
    if (!this.swRegistration || !this.swRegistration.active) {
      console.warn('[PWA] Service Worker not available for offline queue');
      return false;
    }
    
    try {
      const channel = new MessageChannel();
      
      channel.port1.onmessage = (event) => {
        const result = event.data;
        if (result.success) {
          console.log('[PWA] Added to offline queue:', action);
        } else {
          console.error('[PWA] Failed to add to offline queue:', result.error);
        }
      };
      
      this.swRegistration.active.postMessage({
        action: 'ADD_TO_OFFLINE_QUEUE',
        data: {
          id: Date.now().toString(),
          url,
          options,
          action,
          timestamp: new Date().toISOString()
        }
      }, [channel.port2]);
      
      return true;
      
    } catch (error) {
      console.error('[PWA] Offline queue add failed:', error);
      return false;
    }
  }

  /**
   * Service Worker 업데이트 알림 표시
   */
  showUpdateAvailable() {
    const updateBtn = this.createUpdateButton();
    document.body.appendChild(updateBtn);
    
    this.showToast('새로운 업데이트가 있습니다', 'info');
  }

  /**
   * 업데이트 버튼 생성
   */
  createUpdateButton() {
    const button = document.createElement('button');
    button.id = 'pwa-update-btn';
    button.textContent = '업데이트';
    button.className = 'pwa-update-button';
    button.style.cssText = `
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 1000;
      padding: 10px 20px;
      background: #007bff;
      color: white;
      border: none;
      border-radius: 5px;
      cursor: pointer;
    `;
    
    button.addEventListener('click', () => {
      this.applyUpdate();
      button.remove();
    });
    
    return button;
  }

  /**
   * Service Worker 업데이트 적용
   */
  async applyUpdate() {
    if (!this.swRegistration || !this.swRegistration.waiting) {
      return;
    }
    
    // 새 Service Worker 활성화
    this.swRegistration.waiting.postMessage({ action: 'SKIP_WAITING' });
    
    // 페이지 새로고침
    window.location.reload();
  }

  /**
   * 설치 완료 알림
   */
  showInstallComplete() {
    this.showToast('OneSquare가 설치되었습니다!', 'success');
  }

  /**
   * 토스트 메시지 표시
   */
  showToast(message, type = 'info') {
    // 기존 토스트 제거
    const existingToast = document.getElementById('pwa-toast');
    if (existingToast) {
      existingToast.remove();
    }
    
    // 새 토스트 생성
    const toast = document.createElement('div');
    toast.id = 'pwa-toast';
    toast.className = `pwa-toast pwa-toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 1001;
      padding: 12px 20px;
      border-radius: 5px;
      color: white;
      font-weight: 500;
      animation: slideInFromRight 0.3s ease;
    `;
    
    // 타입별 배경색
    const colors = {
      success: '#28a745',
      error: '#dc3545',
      warning: '#ffc107',
      info: '#17a2b8'
    };
    toast.style.backgroundColor = colors[type] || colors.info;
    
    document.body.appendChild(toast);
    
    // 3초 후 자동 제거
    setTimeout(() => {
      if (toast.parentNode) {
        toast.remove();
      }
    }, 3000);
    
    // 클릭 시 제거
    toast.addEventListener('click', () => {
      toast.remove();
    });
  }

  /**
   * 푸시 알림 권한 요청
   */
  async requestNotificationPermission() {
    if (!('Notification' in window)) {
      console.warn('[PWA] Notifications not supported');
      return false;
    }
    
    if (Notification.permission === 'granted') {
      console.log('[PWA] Notification permission already granted');
      return true;
    }
    
    if (Notification.permission === 'denied') {
      console.log('[PWA] Notification permission denied');
      return false;
    }
    
    try {
      const permission = await Notification.requestPermission();
      console.log('[PWA] Notification permission:', permission);
      return permission === 'granted';
    } catch (error) {
      console.error('[PWA] Notification permission request failed:', error);
      return false;
    }
  }

  /**
   * 푸시 구독 설정
   */
  async setupPushSubscription(vapidKey) {
    if (!this.swRegistration) {
      console.warn('[PWA] Service Worker not registered');
      return null;
    }
    
    try {
      const subscription = await this.swRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(vapidKey)
      });
      
      console.log('[PWA] Push subscription created:', subscription);
      return subscription;
      
    } catch (error) {
      console.error('[PWA] Push subscription failed:', error);
      return null;
    }
  }

  /**
   * VAPID 키 변환
   */
  urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/\-/g, '+')
      .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    
    return outputArray;
  }

  /**
   * 푸시 알림 초기화
   */
  async initializePushNotifications() {
    if (!('Notification' in window) || !('PushManager' in window)) {
      console.warn('[PWA] Push notifications not supported');
      return;
    }

    try {
      // VAPID 공개키 로드
      await this.loadVAPIDKey();
      
      // 기존 구독 확인
      if (this.swRegistration) {
        this.pushSubscription = await this.swRegistration.pushManager.getSubscription();
        console.log('[PWA] Existing push subscription:', this.pushSubscription);
      }

      // 푸시 알림 설정 버튼 이벤트 연결
      this.setupPushNotificationButtons();

    } catch (error) {
      console.error('[PWA] Push notification initialization failed:', error);
    }
  }

  /**
   * VAPID 공개키 로드
   */
  async loadVAPIDKey() {
    try {
      const response = await fetch('/pwa/api/vapid-key/');
      if (response.ok) {
        const data = await response.json();
        this.vapidPublicKey = data.publicKey;
        console.log('[PWA] VAPID key loaded');
      }
    } catch (error) {
      console.error('[PWA] Failed to load VAPID key:', error);
    }
  }

  /**
   * 푸시 알림 버튼 설정
   */
  setupPushNotificationButtons() {
    // 푸시 알림 활성화 버튼
    const enablePushBtn = document.getElementById('enable-push-btn');
    if (enablePushBtn) {
      enablePushBtn.addEventListener('click', () => {
        this.enablePushNotifications();
      });
      
      // 이미 구독된 경우 버튼 상태 업데이트
      this.updatePushButtonState();
    }

    // 푸시 알림 비활성화 버튼
    const disablePushBtn = document.getElementById('disable-push-btn');
    if (disablePushBtn) {
      disablePushBtn.addEventListener('click', () => {
        this.disablePushNotifications();
      });
    }

    // 테스트 알림 버튼
    const testPushBtn = document.getElementById('test-push-btn');
    if (testPushBtn) {
      testPushBtn.addEventListener('click', () => {
        this.sendTestNotification();
      });
    }
  }

  /**
   * 푸시 알림 활성화
   */
  async enablePushNotifications() {
    try {
      // 알림 권한 요청
      const hasPermission = await this.requestNotificationPermission();
      if (!hasPermission) {
        this.showToast('알림 권한이 필요합니다', 'warning');
        return;
      }

      // 푸시 구독 생성
      if (!this.vapidPublicKey) {
        await this.loadVAPIDKey();
      }

      this.pushSubscription = await this.setupPushSubscription(this.vapidPublicKey);
      
      if (this.pushSubscription) {
        // 서버에 구독 정보 전송
        await this.sendSubscriptionToServer(this.pushSubscription);
        this.showToast('푸시 알림이 활성화되었습니다', 'success');
        this.updatePushButtonState();
      }

    } catch (error) {
      console.error('[PWA] Push notification enable failed:', error);
      this.showToast('푸시 알림 활성화에 실패했습니다', 'error');
    }
  }

  /**
   * 푸시 알림 비활성화
   */
  async disablePushNotifications() {
    if (!this.pushSubscription) {
      this.showToast('푸시 알림이 이미 비활성화되어 있습니다', 'info');
      return;
    }

    try {
      // 서버에 구독 해제 알림
      await this.removeSubscriptionFromServer();
      
      // 로컬 구독 해제
      const successful = await this.pushSubscription.unsubscribe();
      
      if (successful) {
        this.pushSubscription = null;
        this.showToast('푸시 알림이 비활성화되었습니다', 'success');
        this.updatePushButtonState();
      }

    } catch (error) {
      console.error('[PWA] Push notification disable failed:', error);
      this.showToast('푸시 알림 비활성화에 실패했습니다', 'error');
    }
  }

  /**
   * 서버에 구독 정보 전송
   */
  async sendSubscriptionToServer(subscription) {
    try {
      const response = await fetch('/pwa/api/push/subscribe/', {
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
      console.log('[PWA] Subscription sent to server:', result);

    } catch (error) {
      console.error('[PWA] Failed to send subscription to server:', error);
      throw error;
    }
  }

  /**
   * 서버에서 구독 제거
   */
  async removeSubscriptionFromServer() {
    if (!this.pushSubscription) return;

    try {
      const response = await fetch('/pwa/api/push/unsubscribe/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify({
          endpoint: this.pushSubscription.endpoint
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

    } catch (error) {
      console.error('[PWA] Failed to remove subscription from server:', error);
    }
  }

  /**
   * 테스트 알림 전송
   */
  async sendTestNotification() {
    if (!this.pushSubscription) {
      this.showToast('푸시 알림을 먼저 활성화해주세요', 'warning');
      return;
    }

    try {
      const response = await fetch('/pwa/api/push/test/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify({
          title: 'OneSquare 테스트 알림',
          message: '푸시 알림이 정상적으로 작동합니다! 🎉',
          url: '/'
        })
      });

      if (response.ok) {
        this.showToast('테스트 알림을 전송했습니다', 'success');
      } else {
        throw new Error(`HTTP ${response.status}`);
      }

    } catch (error) {
      console.error('[PWA] Test notification failed:', error);
      this.showToast('테스트 알림 전송에 실패했습니다', 'error');
    }
  }

  /**
   * 푸시 버튼 상태 업데이트
   */
  updatePushButtonState() {
    const enableBtn = document.getElementById('enable-push-btn');
    const disableBtn = document.getElementById('disable-push-btn');
    const testBtn = document.getElementById('test-push-btn');
    const statusIndicator = document.getElementById('push-status');

    const isSubscribed = !!this.pushSubscription;
    const permission = Notification.permission;

    if (enableBtn) {
      enableBtn.style.display = isSubscribed ? 'none' : 'block';
      enableBtn.disabled = permission === 'denied';
    }

    if (disableBtn) {
      disableBtn.style.display = isSubscribed ? 'block' : 'none';
    }

    if (testBtn) {
      testBtn.style.display = isSubscribed ? 'block' : 'none';
    }

    if (statusIndicator) {
      let statusText = '';
      let statusClass = '';

      if (permission === 'denied') {
        statusText = '푸시 알림 권한이 거부됨';
        statusClass = 'status-denied';
      } else if (isSubscribed) {
        statusText = '푸시 알림 활성화됨';
        statusClass = 'status-active';
      } else {
        statusText = '푸시 알림 비활성화됨';
        statusClass = 'status-inactive';
      }

      statusIndicator.textContent = statusText;
      statusIndicator.className = `push-status ${statusClass}`;
    }
  }

  /**
   * 로컬 알림 표시 (개발/테스트용)
   */
  showLocalNotification(title, options = {}) {
    if (Notification.permission !== 'granted') {
      console.warn('[PWA] Notification permission not granted');
      return;
    }

    const defaultOptions = {
      body: 'OneSquare에서 새로운 업데이트가 있습니다.',
      icon: '/static/images/icons/icon-192x192.png',
      badge: '/static/images/icons/badge-72x72.png',
      tag: 'onesquare-notification',
      requireInteraction: false
    };

    const notification = new Notification(title, { ...defaultOptions, ...options });

    notification.onclick = (event) => {
      event.preventDefault();
      window.focus();
      notification.close();
      
      // URL이 제공된 경우 해당 페이지로 이동
      if (options.data && options.data.url) {
        window.location.href = options.data.url;
      }
    };

    // 5초 후 자동 닫기
    setTimeout(() => {
      notification.close();
    }, 5000);

    return notification;
  }

  /**
   * 푸시 알림 설정 조회
   */
  async getPushSettings() {
    try {
      const response = await fetch('/pwa/api/push/settings/');
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('[PWA] Failed to get push settings:', error);
    }
    return null;
  }

  /**
   * 푸시 알림 설정 업데이트
   */
  async updatePushSettings(settings) {
    try {
      const response = await fetch('/pwa/api/push/settings/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCSRFToken()
        },
        body: JSON.stringify(settings)
      });

      if (response.ok) {
        const result = await response.json();
        this.showToast('알림 설정이 저장되었습니다', 'success');
        return result;
      } else {
        throw new Error(`HTTP ${response.status}`);
      }

    } catch (error) {
      console.error('[PWA] Failed to update push settings:', error);
      this.showToast('알림 설정 저장에 실패했습니다', 'error');
      throw error;
    }
  }

  /**
   * CSRF 토큰 가져오기
   */
  getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  }

  /**
   * 푸시 알림 상태 조회
   */
  getPushNotificationStatus() {
    return {
      isSupported: 'Notification' in window && 'PushManager' in window,
      permission: Notification.permission,
      isSubscribed: !!this.pushSubscription,
      hasVAPIDKey: !!this.vapidPublicKey,
      subscription: this.pushSubscription
    };
  }
}

// PWA Manager 전역 인스턴스
let pwaManager = null;

// DOM 로드 완료 시 PWA Manager 초기화
document.addEventListener('DOMContentLoaded', () => {
  pwaManager = new PWAManager();
  
  // 전역 접근을 위해 window에 할당
  window.pwaManager = pwaManager;
});

// CSS 애니메이션 추가
const style = document.createElement('style');
style.textContent = `
  @keyframes slideInFromRight {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  
  .offline-mode {
    filter: grayscale(20%);
  }
  
  .offline-mode .online-only {
    opacity: 0.5;
    pointer-events: none;
  }
  
  .pwa-update-button:hover {
    background: #0056b3 !important;
  }
`;
document.head.appendChild(style);