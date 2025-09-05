/**
 * OneSquare 오프라인 대시보드 UI/UX 최적화
 * 
 * 오프라인 상태에서도 원활한 사용자 경험을 제공하는 UI 컴포넌트
 * 네트워크 상태 표시, 오프라인 모드 안내, 데이터 동기화 상태 표시
 */

class OfflineDashboardUI {
    constructor(config = {}) {
        this.config = {
            showOfflineIndicator: config.showOfflineIndicator !== false,
            showSyncStatus: config.showSyncStatus !== false,
            showDataFreshness: config.showDataFreshness !== false,
            offlineMessageDuration: config.offlineMessageDuration || 3000,
            enableOfflineToasts: config.enableOfflineToasts !== false,
            enableOfflineGuide: config.enableOfflineGuide !== false,
            offlineTheme: config.offlineTheme || 'muted',
            ...config
        };

        this.isOffline = !navigator.onLine;
        this.offlineStartTime = null;
        this.syncInProgress = false;
        this.lastSyncTime = null;
        this.offlineCapabilities = null;
        
        // UI 요소들
        this.elements = {
            offlineIndicator: null,
            syncStatus: null,
            offlineGuide: null,
            dataFreshnessIndicators: new Map(),
            offlineToast: null
        };

        this.init();
    }

    /**
     * UI 초기화
     */
    async init() {
        try {
            console.log('[OfflineDashboardUI] Initializing offline dashboard UI...');
            
            await this.createUIElements();
            await this.setupEventListeners();
            await this.updateOfflineCapabilities();
            await this.initializeOfflineFeatures();
            
            // 현재 네트워크 상태에 따라 UI 업데이트
            this.updateNetworkStatus(navigator.onLine);
            
            console.log('[OfflineDashboardUI] Offline dashboard UI initialized successfully');
            
        } catch (error) {
            console.error('[OfflineDashboardUI] Initialization failed:', error);
        }
    }

    /**
     * UI 요소들 생성
     */
    async createUIElements() {
        // 오프라인 표시기 생성
        if (this.config.showOfflineIndicator) {
            this.createOfflineIndicator();
        }

        // 동기화 상태 표시기 생성
        if (this.config.showSyncStatus) {
            this.createSyncStatusIndicator();
        }

        // 오프라인 가이드 생성
        if (this.config.enableOfflineGuide) {
            this.createOfflineGuide();
        }

        // 데이터 신선도 표시기들 생성
        if (this.config.showDataFreshness) {
            this.createDataFreshnessIndicators();
        }

        // 오프라인 전용 스타일 추가
        this.injectOfflineStyles();
    }

    /**
     * 오프라인 표시기 생성
     */
    createOfflineIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'offline-indicator';
        indicator.className = 'offline-indicator';
        indicator.innerHTML = `
            <div class="offline-indicator-content">
                <i class="fas fa-wifi-slash offline-icon"></i>
                <span class="offline-text">오프라인</span>
                <span class="offline-duration">0s</span>
            </div>
        `;

        // 페이지 상단에 고정
        document.body.appendChild(indicator);
        this.elements.offlineIndicator = indicator;
    }

    /**
     * 동기화 상태 표시기 생성
     */
    createSyncStatusIndicator() {
        const syncStatus = document.createElement('div');
        syncStatus.id = 'sync-status';
        syncStatus.className = 'sync-status';
        syncStatus.innerHTML = `
            <div class="sync-status-content">
                <i class="fas fa-sync sync-icon"></i>
                <span class="sync-text">동기화됨</span>
                <span class="sync-time"></span>
            </div>
        `;

        // 대시보드 헤더에 추가
        const dashboardHeader = document.querySelector('.dashboard-header') || document.querySelector('header') || document.body;
        dashboardHeader.appendChild(syncStatus);
        this.elements.syncStatus = syncStatus;
    }

    /**
     * 오프라인 가이드 생성
     */
    createOfflineGuide() {
        const guide = document.createElement('div');
        guide.id = 'offline-guide';
        guide.className = 'offline-guide';
        guide.innerHTML = `
            <div class="offline-guide-content">
                <div class="offline-guide-header">
                    <i class="fas fa-info-circle"></i>
                    <h5>오프라인 모드</h5>
                    <button type="button" class="btn-close" onclick="this.parentElement.parentElement.parentElement.style.display='none'"></button>
                </div>
                <div class="offline-guide-body">
                    <p>네트워크 연결이 없어도 다음 기능들을 사용할 수 있습니다:</p>
                    <ul id="offline-capabilities-list">
                        <li>✅ 대시보드 통계 조회</li>
                        <li>✅ 최근 알림 확인</li>
                        <li>✅ 사용자 설정</li>
                        <li>✅ 최근 활동 내역</li>
                        <li>⏳ 일부 기능은 제한될 수 있습니다</li>
                    </ul>
                    <div class="offline-guide-actions">
                        <button class="btn btn-primary btn-sm" onclick="location.reload()">
                            <i class="fas fa-refresh"></i> 새로고침
                        </button>
                        <small class="text-muted d-block mt-2">
                            네트워크 연결이 복구되면 자동으로 동기화됩니다.
                        </small>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(guide);
        this.elements.offlineGuide = guide;
        
        // 기본적으로 숨김
        guide.style.display = 'none';
    }

    /**
     * 데이터 신선도 표시기들 생성
     */
    createDataFreshnessIndicators() {
        // 위젯들에 데이터 신선도 표시기 추가
        const widgets = document.querySelectorAll('[data-widget-id]');
        
        widgets.forEach(widget => {
            const widgetId = widget.dataset.widgetId;
            const indicator = document.createElement('div');
            indicator.className = 'data-freshness-indicator';
            indicator.innerHTML = `
                <small class="text-muted">
                    <i class="fas fa-clock"></i>
                    <span class="freshness-text">실시간</span>
                </small>
            `;
            
            // 위젯 헤더나 적절한 위치에 추가
            const header = widget.querySelector('.widget-header') || widget.querySelector('.card-header');
            if (header) {
                header.appendChild(indicator);
                this.elements.dataFreshnessIndicators.set(widgetId, indicator);
            }
        });
    }

    /**
     * 오프라인 전용 CSS 스타일 주입
     */
    injectOfflineStyles() {
        const styles = `
            <style id="offline-dashboard-styles">
                /* 오프라인 표시기 */
                .offline-indicator {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    background: linear-gradient(135deg, #ff6b6b, #ee5a24);
                    color: white;
                    padding: 8px 16px;
                    text-align: center;
                    z-index: 9999;
                    font-size: 14px;
                    font-weight: 500;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    transform: translateY(-100%);
                    transition: transform 0.3s ease-in-out;
                    display: none;
                }
                
                .offline-indicator.show {
                    display: block;
                    transform: translateY(0);
                }
                
                .offline-indicator-content {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 8px;
                }
                
                .offline-icon {
                    font-size: 16px;
                }
                
                .offline-duration {
                    background: rgba(255,255,255,0.2);
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 12px;
                }

                /* 동기화 상태 표시기 */
                .sync-status {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 4px 12px;
                    background: #e8f5e8;
                    border-radius: 20px;
                    font-size: 12px;
                    color: #28a745;
                    border: 1px solid #c3e6c3;
                }
                
                .sync-status.syncing {
                    background: #fff3cd;
                    color: #856404;
                    border-color: #ffeaa7;
                }
                
                .sync-status.error {
                    background: #f8d7da;
                    color: #721c24;
                    border-color: #f5c6cb;
                }
                
                .sync-icon {
                    font-size: 12px;
                }
                
                .sync-status.syncing .sync-icon {
                    animation: spin 1s linear infinite;
                }
                
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }

                /* 오프라인 가이드 */
                .offline-guide {
                    position: fixed;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    width: 90%;
                    max-width: 480px;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.15);
                    z-index: 10000;
                    animation: fadeInScale 0.3s ease-out;
                }
                
                @keyframes fadeInScale {
                    from {
                        opacity: 0;
                        transform: translate(-50%, -50%) scale(0.9);
                    }
                    to {
                        opacity: 1;
                        transform: translate(-50%, -50%) scale(1);
                    }
                }
                
                .offline-guide-content {
                    padding: 0;
                }
                
                .offline-guide-header {
                    display: flex;
                    align-items: center;
                    padding: 16px 20px;
                    background: #f8f9fa;
                    border-radius: 12px 12px 0 0;
                    border-bottom: 1px solid #dee2e6;
                }
                
                .offline-guide-header i {
                    color: #007bff;
                    margin-right: 8px;
                    font-size: 18px;
                }
                
                .offline-guide-header h5 {
                    margin: 0;
                    flex: 1;
                    color: #495057;
                }
                
                .offline-guide-body {
                    padding: 20px;
                }
                
                .offline-guide-body ul {
                    list-style: none;
                    padding: 0;
                    margin: 16px 0;
                }
                
                .offline-guide-body li {
                    padding: 6px 0;
                    display: flex;
                    align-items: center;
                }
                
                .offline-guide-actions {
                    margin-top: 20px;
                    text-align: center;
                }

                /* 데이터 신선도 표시기 */
                .data-freshness-indicator {
                    margin-left: auto;
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }
                
                .data-freshness-indicator.stale .freshness-text {
                    color: #ffc107;
                }
                
                .data-freshness-indicator.very-stale .freshness-text {
                    color: #dc3545;
                }

                /* 오프라인 모드 시 위젯 스타일 조정 */
                body.offline-mode .widget-header {
                    background: #f8f9fa;
                    border-bottom: 1px solid #dee2e6;
                }
                
                body.offline-mode [data-widget-id] {
                    position: relative;
                }
                
                body.offline-mode [data-widget-id]::after {
                    content: "";
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 2px;
                    background: linear-gradient(90deg, transparent, #ffc107, transparent);
                    opacity: 0.7;
                }

                /* 오프라인 토스트 */
                .offline-toast {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: #343a40;
                    color: white;
                    padding: 12px 20px;
                    border-radius: 8px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    z-index: 9999;
                    transform: translateY(100px);
                    transition: transform 0.3s ease-in-out;
                    max-width: 300px;
                }
                
                .offline-toast.show {
                    transform: translateY(0);
                }
                
                .offline-toast .toast-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 8px;
                    font-weight: 500;
                }
                
                .offline-toast .toast-body {
                    font-size: 14px;
                    opacity: 0.9;
                }

                /* 로딩 스켈레톤 (오프라인용) */
                .offline-skeleton {
                    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                    background-size: 200% 100%;
                    animation: loading 1.5s infinite;
                }
                
                @keyframes loading {
                    0% { background-position: 200% 0; }
                    100% { background-position: -200% 0; }
                }

                /* 반응형 조정 */
                @media (max-width: 768px) {
                    .offline-guide {
                        width: 95%;
                        margin: 0 2.5%;
                    }
                    
                    .offline-indicator-content {
                        font-size: 12px;
                    }
                    
                    .offline-toast {
                        right: 10px;
                        bottom: 10px;
                        max-width: calc(100vw - 20px);
                    }
                }
            </style>
        `;

        document.head.insertAdjacentHTML('beforeend', styles);
    }

    /**
     * 이벤트 리스너 설정
     */
    async setupEventListeners() {
        // 네트워크 상태 변경 감지
        window.addEventListener('online', () => {
            this.updateNetworkStatus(true);
        });

        window.addEventListener('offline', () => {
            this.updateNetworkStatus(false);
        });

        // 오프라인 저장소 상태 변경 감지
        window.addEventListener('offlineStatusChange', (event) => {
            this.handleOfflineStatusChange(event.detail);
        });

        // 동기화 이벤트 감지
        window.addEventListener('syncStart', () => {
            this.showSyncStatus('syncing');
        });

        window.addEventListener('syncComplete', (event) => {
            this.showSyncStatus('success', event.detail);
        });

        window.addEventListener('syncError', (event) => {
            this.showSyncStatus('error', event.detail);
        });

        // 위젯 데이터 업데이트 감지
        document.addEventListener('widgetDataUpdated', (event) => {
            this.updateDataFreshness(event.detail.widgetId, event.detail.timestamp);
        });

        // 키보드 단축키 (Ctrl+Shift+O: 오프라인 가이드 토글)
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey && event.shiftKey && event.key === 'O') {
                this.toggleOfflineGuide();
            }
        });
    }

    /**
     * 네트워크 상태 업데이트
     */
    async updateNetworkStatus(isOnline) {
        this.isOffline = !isOnline;

        if (!isOnline) {
            this.offlineStartTime = Date.now();
            this.showOfflineIndicator();
            this.showOfflineMode();
            
            if (this.config.enableOfflineToasts) {
                this.showOfflineToast('네트워크 연결이 끊어졌습니다. 오프라인 모드로 전환합니다.');
            }
            
        } else {
            if (this.offlineStartTime) {
                const offlineDuration = Date.now() - this.offlineStartTime;
                console.log(`[OfflineDashboardUI] Online after ${Math.round(offlineDuration / 1000)}s offline`);
                this.offlineStartTime = null;
            }
            
            this.hideOfflineIndicator();
            this.showOnlineMode();
            
            if (this.config.enableOfflineToasts) {
                this.showOfflineToast('네트워크 연결이 복구되었습니다. 데이터를 동기화하는 중...', 'success');
            }
        }

        // 오프라인 기능 상태 업데이트
        await this.updateOfflineCapabilities();
    }

    /**
     * 오프라인 표시기 표시
     */
    showOfflineIndicator() {
        if (!this.elements.offlineIndicator) return;

        this.elements.offlineIndicator.classList.add('show');
        
        // 오프라인 지속 시간 업데이트
        this.updateOfflineDuration();
    }

    /**
     * 오프라인 표시기 숨김
     */
    hideOfflineIndicator() {
        if (!this.elements.offlineIndicator) return;

        this.elements.offlineIndicator.classList.remove('show');
    }

    /**
     * 오프라인 지속 시간 업데이트
     */
    updateOfflineDuration() {
        if (!this.isOffline || !this.offlineStartTime || !this.elements.offlineIndicator) return;

        const durationElement = this.elements.offlineIndicator.querySelector('.offline-duration');
        if (!durationElement) return;

        const updateDuration = () => {
            if (!this.isOffline) return;

            const duration = Math.floor((Date.now() - this.offlineStartTime) / 1000);
            const minutes = Math.floor(duration / 60);
            const seconds = duration % 60;
            
            if (minutes > 0) {
                durationElement.textContent = `${minutes}m ${seconds}s`;
            } else {
                durationElement.textContent = `${seconds}s`;
            }
        };

        updateDuration();
        
        // 1초마다 업데이트
        this.offlineDurationInterval = setInterval(updateDuration, 1000);
    }

    /**
     * 오프라인 모드 UI 활성화
     */
    showOfflineMode() {
        document.body.classList.add('offline-mode');
        
        // 오프라인 가이드 표시 (첫 번째 오프라인 시)
        const hasSeenOfflineGuide = localStorage.getItem('hasSeenOfflineGuide');
        if (!hasSeenOfflineGuide && this.config.enableOfflineGuide) {
            setTimeout(() => {
                this.showOfflineGuide();
                localStorage.setItem('hasSeenOfflineGuide', 'true');
            }, 2000);
        }
        
        // 위젯들을 오프라인 모드로 업데이트
        this.updateWidgetsForOfflineMode();
    }

    /**
     * 온라인 모드 UI 활성화
     */
    showOnlineMode() {
        document.body.classList.remove('offline-mode');
        
        if (this.offlineDurationInterval) {
            clearInterval(this.offlineDurationInterval);
            this.offlineDurationInterval = null;
        }
        
        // 위젯들을 온라인 모드로 업데이트
        this.updateWidgetsForOnlineMode();
    }

    /**
     * 동기화 상태 표시
     */
    showSyncStatus(status, details = {}) {
        if (!this.elements.syncStatus) return;

        const syncStatus = this.elements.syncStatus;
        const icon = syncStatus.querySelector('.sync-icon');
        const text = syncStatus.querySelector('.sync-text');
        const time = syncStatus.querySelector('.sync-time');

        // 기존 클래스 제거
        syncStatus.classList.remove('syncing', 'error');

        switch (status) {
            case 'syncing':
                syncStatus.classList.add('syncing');
                icon.className = 'fas fa-sync sync-icon';
                text.textContent = '동기화 중...';
                this.syncInProgress = true;
                break;

            case 'success':
                icon.className = 'fas fa-check sync-icon';
                text.textContent = '동기화됨';
                time.textContent = this.formatSyncTime(Date.now());
                this.lastSyncTime = Date.now();
                this.syncInProgress = false;
                break;

            case 'error':
                syncStatus.classList.add('error');
                icon.className = 'fas fa-exclamation-triangle sync-icon';
                text.textContent = '동기화 실패';
                time.textContent = details.error || '오류 발생';
                this.syncInProgress = false;
                break;
        }
    }

    /**
     * 동기화 시간 포맷
     */
    formatSyncTime(timestamp) {
        const now = Date.now();
        const diff = now - timestamp;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) {
            return `${hours}시간 전`;
        } else if (minutes > 0) {
            return `${minutes}분 전`;
        } else if (seconds > 10) {
            return `${seconds}초 전`;
        } else {
            return '방금 전';
        }
    }

    /**
     * 데이터 신선도 업데이트
     */
    updateDataFreshness(widgetId, timestamp) {
        const indicator = this.elements.dataFreshnessIndicators.get(widgetId);
        if (!indicator) return;

        const now = Date.now();
        const age = now - timestamp;
        const freshnessText = indicator.querySelector('.freshness-text');

        // 클래스 초기화
        indicator.classList.remove('stale', 'very-stale');

        if (age < 5 * 60 * 1000) { // 5분 미만
            freshnessText.textContent = '실시간';
        } else if (age < 30 * 60 * 1000) { // 30분 미만
            freshnessText.textContent = `${Math.floor(age / 60 / 1000)}분 전`;
            indicator.classList.add('stale');
        } else if (age < 24 * 60 * 60 * 1000) { // 24시간 미만
            const hours = Math.floor(age / 60 / 60 / 1000);
            freshnessText.textContent = `${hours}시간 전`;
            indicator.classList.add('very-stale');
        } else { // 24시간 이상
            const days = Math.floor(age / 24 / 60 / 60 / 1000);
            freshnessText.textContent = `${days}일 전`;
            indicator.classList.add('very-stale');
        }
    }

    /**
     * 오프라인 토스트 표시
     */
    showOfflineToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = 'offline-toast';
        
        const icons = {
            info: 'fa-info-circle',
            success: 'fa-check-circle',
            warning: 'fa-exclamation-triangle',
            error: 'fa-exclamation-circle'
        };

        toast.innerHTML = `
            <div class="toast-header">
                <i class="fas ${icons[type] || icons.info}"></i>
                <span>알림</span>
            </div>
            <div class="toast-body">${message}</div>
        `;

        document.body.appendChild(toast);

        // 애니메이션으로 표시
        requestAnimationFrame(() => {
            toast.classList.add('show');
        });

        // 자동 제거
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, this.config.offlineMessageDuration);
    }

    /**
     * 오프라인 가이드 표시/숨김
     */
    showOfflineGuide() {
        if (!this.elements.offlineGuide) return;
        
        this.elements.offlineGuide.style.display = 'block';
        this.updateOfflineCapabilitiesList();
    }

    hideOfflineGuide() {
        if (!this.elements.offlineGuide) return;
        
        this.elements.offlineGuide.style.display = 'none';
    }

    toggleOfflineGuide() {
        if (!this.elements.offlineGuide) return;
        
        const isVisible = this.elements.offlineGuide.style.display !== 'none';
        if (isVisible) {
            this.hideOfflineGuide();
        } else {
            this.showOfflineGuide();
        }
    }

    /**
     * 오프라인 기능 목록 업데이트
     */
    async updateOfflineCapabilitiesList() {
        const list = document.getElementById('offline-capabilities-list');
        if (!list || !this.offlineCapabilities) return;

        const features = this.offlineCapabilities.features || {};
        const capabilities = [
            { key: 'dashboardStats', label: '대시보드 통계 조회', available: features.dashboardStats },
            { key: 'notifications', label: '최근 알림 확인', available: features.notifications },
            { key: 'userSettings', label: '사용자 설정', available: features.userSettings },
            { key: 'recentActivities', label: '최근 활동 내역', available: features.recentActivities },
            { key: 'basicFunctionality', label: '기본 내비게이션', available: features.basicFunctionality }
        ];

        list.innerHTML = capabilities.map(cap => `
            <li>
                ${cap.available ? '✅' : '❌'} ${cap.label}
                ${cap.available ? '' : '<small class="text-muted">(데이터 없음)</small>'}
            </li>
        `).join('');
    }

    /**
     * 위젯들을 오프라인 모드로 업데이트
     */
    async updateWidgetsForOfflineMode() {
        const widgets = document.querySelectorAll('[data-widget-id]');
        
        for (const widget of widgets) {
            const widgetId = widget.dataset.widgetId;
            
            // 오프라인 데이터가 있는지 확인
            let hasOfflineData = false;
            if (window.offlineDashboardStorage) {
                try {
                    const data = await window.offlineDashboardStorage.getOfflineWidgetData(widgetId);
                    hasOfflineData = !!data;
                } catch (error) {
                    console.warn(`[OfflineDashboardUI] Failed to check offline data for ${widgetId}:`, error);
                }
            }

            // 위젯에 오프라인 상태 표시
            if (!hasOfflineData) {
                this.addOfflineNoDataIndicator(widget);
            } else {
                this.updateDataFreshness(widgetId, Date.now() - 30 * 60 * 1000); // 30분 전으로 설정
            }
        }
    }

    /**
     * 위젯들을 온라인 모드로 업데이트
     */
    updateWidgetsForOnlineMode() {
        const widgets = document.querySelectorAll('[data-widget-id]');
        
        widgets.forEach(widget => {
            const widgetId = widget.dataset.widgetId;
            
            // 오프라인 표시기 제거
            const noDataIndicator = widget.querySelector('.offline-no-data-indicator');
            if (noDataIndicator) {
                noDataIndicator.remove();
            }

            // 데이터 신선도를 실시간으로 업데이트
            this.updateDataFreshness(widgetId, Date.now());
        });
    }

    /**
     * 오프라인 데이터 없음 표시기 추가
     */
    addOfflineNoDataIndicator(widget) {
        // 이미 있으면 추가하지 않음
        if (widget.querySelector('.offline-no-data-indicator')) return;

        const indicator = document.createElement('div');
        indicator.className = 'offline-no-data-indicator alert alert-warning';
        indicator.innerHTML = `
            <i class="fas fa-exclamation-triangle"></i>
            오프라인 상태에서는 이 위젯의 데이터를 사용할 수 없습니다.
            <small class="d-block mt-1">네트워크 연결 시 최신 데이터가 표시됩니다.</small>
        `;

        // 위젯 내용 위에 삽입
        widget.insertBefore(indicator, widget.firstChild);
    }

    /**
     * 오프라인 기능 상태 업데이트
     */
    async updateOfflineCapabilities() {
        if (window.offlineDashboardStorage && window.offlineDashboardStorage.isInitialized) {
            try {
                this.offlineCapabilities = await window.offlineDashboardStorage.getOfflineCapabilities();
            } catch (error) {
                console.warn('[OfflineDashboardUI] Failed to get offline capabilities:', error);
                this.offlineCapabilities = { available: false, reason: error.message };
            }
        } else {
            this.offlineCapabilities = { available: false, reason: 'Offline storage not initialized' };
        }

        // UI 업데이트
        if (this.isOffline) {
            this.updateOfflineCapabilitiesList();
        }
    }

    /**
     * 오프라인 상태 변경 처리
     */
    handleOfflineStatusChange(detail) {
        console.log('[OfflineDashboardUI] Offline status changed:', detail);
        
        // UI 업데이트는 updateNetworkStatus에서 처리됨
        if (detail.isOnline) {
            this.showSyncStatus('syncing');
        }
    }

    /**
     * 현재 상태 조회
     */
    getStatus() {
        return {
            isOffline: this.isOffline,
            offlineStartTime: this.offlineStartTime,
            offlineDuration: this.offlineStartTime ? Date.now() - this.offlineStartTime : 0,
            syncInProgress: this.syncInProgress,
            lastSyncTime: this.lastSyncTime,
            offlineCapabilities: this.offlineCapabilities,
            config: this.config
        };
    }

    /**
     * 수동 동기화 트리거
     */
    async triggerManualSync() {
        if (!navigator.onLine) {
            this.showOfflineToast('네트워크 연결이 필요합니다.', 'warning');
            return;
        }

        if (this.syncInProgress) {
            this.showOfflineToast('이미 동기화가 진행 중입니다.', 'info');
            return;
        }

        try {
            this.showSyncStatus('syncing');
            
            if (window.offlineDashboardStorage) {
                await window.offlineDashboardStorage.performSync();
                this.showSyncStatus('success');
                this.showOfflineToast('동기화가 완료되었습니다.', 'success');
            }
        } catch (error) {
            console.error('[OfflineDashboardUI] Manual sync failed:', error);
            this.showSyncStatus('error', { error: error.message });
            this.showOfflineToast('동기화에 실패했습니다.', 'error');
        }
    }

    /**
     * 정리
     */
    destroy() {
        // 타이머 정리
        if (this.offlineDurationInterval) {
            clearInterval(this.offlineDurationInterval);
        }

        // UI 요소들 제거
        Object.values(this.elements).forEach(element => {
            if (element && element.parentNode) {
                element.parentNode.removeChild(element);
            }
        });

        // 스타일 제거
        const styles = document.getElementById('offline-dashboard-styles');
        if (styles && styles.parentNode) {
            styles.parentNode.removeChild(styles);
        }

        // 클래스 제거
        document.body.classList.remove('offline-mode');

        console.log('[OfflineDashboardUI] Offline dashboard UI destroyed');
    }
}

// 전역으로 내보내기
window.OfflineDashboardUI = OfflineDashboardUI;

// 자동 초기화
window.addEventListener('DOMContentLoaded', () => {
    if (window.oneSquareConfig?.enableOfflineUI !== false) {
        window.offlineDashboardUI = new OfflineDashboardUI();
    }
});