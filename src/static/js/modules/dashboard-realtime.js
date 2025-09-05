/**
 * OneSquare 실시간 대시보드 관리자
 * 실시간 데이터 업데이트, PWA 캐싱, 오프라인 지원
 */

class DashboardManager {
    constructor(config = {}) {
        this.config = {
            refreshInterval: config.refreshInterval || 300000, // 5분
            apiEndpoint: config.apiEndpoint || '/dashboard/api/',
            enableOffline: config.enableOffline !== false,
            enableNotifications: config.enableNotifications !== false,
            retryAttempts: config.retryAttempts || 3,
            retryDelay: config.retryDelay || 2000,
            ...config
        };

        this.widgets = new Map();
        this.refreshTimers = new Map();
        this.isOnline = navigator.onLine;
        this.cache = new Map();
        
        // 이벤트 바인딩
        this.bindEvents();
        
        // PWA 관련 초기화
        if (this.config.enableOffline) {
            this.initializeOfflineSupport();
        }
        
        if (this.config.enableNotifications) {
            this.initializeNotifications();
        }

        console.log('✅ Dashboard Manager initialized');
    }

    /**
     * 이벤트 바인딩
     */
    bindEvents() {
        // 온라인/오프라인 상태 감지
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.showConnectionStatus('온라인 상태로 변경되었습니다.', 'success');
            this.syncOfflineData();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.showConnectionStatus('오프라인 모드입니다.', 'warning');
        });

        // 페이지 가시성 변경 감지
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseRefresh();
            } else {
                this.resumeRefresh();
            }
        });

        // 페이지 언로드 시 정리
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    /**
     * 위젯 등록
     */
    registerWidget(widgetId, config) {
        const widgetConfig = {
            type: config.type || 'stats_card',
            dataSource: config.dataSource || 'revenue',
            refreshInterval: config.refreshInterval || this.config.refreshInterval,
            container: config.container || widgetId,
            autoRefresh: config.autoRefresh !== false,
            cacheable: config.cacheable !== false,
            ...config
        };

        this.widgets.set(widgetId, widgetConfig);
        
        // 초기 데이터 로드
        this.loadWidgetData(widgetId);
        
        // 자동 새로고침 설정
        if (widgetConfig.autoRefresh) {
            this.startWidgetRefresh(widgetId);
        }

        console.log(`📊 Widget registered: ${widgetId}`);
    }

    /**
     * 위젯 데이터 로드
     */
    async loadWidgetData(widgetId, useCache = true) {
        const widget = this.widgets.get(widgetId);
        if (!widget) {
            console.error(`Widget not found: ${widgetId}`);
            return;
        }

        const cacheKey = `widget_${widgetId}`;
        
        // 캐시된 데이터 확인
        if (useCache && this.cache.has(cacheKey) && !this.isOnline) {
            const cachedData = this.cache.get(cacheKey);
            this.renderWidget(widgetId, cachedData);
            return;
        }

        try {
            // 로딩 상태 표시
            this.showWidgetLoading(widgetId);

            const response = await this.fetchWithRetry(`${this.config.apiEndpoint}data/`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                params: {
                    widget_type: widget.type,
                    data_source: widget.dataSource,
                    time_range: widget.timeRange || '7d'
                }
            });

            if (response.ok) {
                const data = await response.json();
                
                // 캐시 저장
                if (widget.cacheable) {
                    this.cache.set(cacheKey, {
                        ...data,
                        cachedAt: Date.now()
                    });
                }

                // 위젯 렌더링
                this.renderWidget(widgetId, data);
            } else {
                this.handleWidgetError(widgetId, 'Failed to load data');
            }

        } catch (error) {
            console.error(`Widget data load failed: ${widgetId}`, error);
            
            // 오프라인 상태에서는 캐시된 데이터 사용
            if (!this.isOnline && this.cache.has(cacheKey)) {
                const cachedData = this.cache.get(cacheKey);
                this.renderWidget(widgetId, cachedData, true);
            } else {
                this.handleWidgetError(widgetId, error.message);
            }
        }
    }

    /**
     * 위젯 렌더링
     */
    renderWidget(widgetId, data, fromCache = false) {
        const widget = this.widgets.get(widgetId);
        const container = document.getElementById(widget.container);
        
        if (!container) {
            console.error(`Container not found: ${widget.container}`);
            return;
        }

        try {
            // 차트 렌더링
            const chart = new SVGCharts(widget.container);
            
            switch (widget.type) {
                case 'chart_pie':
                    chart.createPieChart(data.chartData || [], widget.chartOptions);
                    break;
                    
                case 'chart_bar':
                    chart.createBarChart(data.chartData || [], widget.chartOptions);
                    break;
                    
                case 'chart_line':
                    chart.createLineChart(data.chartData || [], widget.chartOptions);
                    break;
                    
                case 'stats_card':
                    chart.createStatsCard(data, widget.chartOptions);
                    break;
                    
                case 'table':
                    this.renderTable(container, data);
                    break;
                    
                default:
                    this.renderGenericWidget(container, data);
            }

            // 캐시 상태 표시
            if (fromCache) {
                this.showCacheIndicator(container);
            }

            // 마지막 업데이트 시간 표시
            this.updateLastRefreshTime(widgetId);

        } catch (error) {
            console.error(`Widget render failed: ${widgetId}`, error);
            this.handleWidgetError(widgetId, 'Render failed');
        }
    }

    /**
     * 테이블 렌더링
     */
    renderTable(container, data) {
        const tableHtml = `
            <div class="table-widget">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                ${(data.headers || []).map(header => `<th>${header}</th>`).join('')}
                            </tr>
                        </thead>
                        <tbody>
                            ${(data.rows || []).map(row => `
                                <tr>
                                    ${row.map(cell => `<td>${cell}</td>`).join('')}
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        
        container.innerHTML = tableHtml;
    }

    /**
     * 일반 위젯 렌더링
     */
    renderGenericWidget(container, data) {
        container.innerHTML = `
            <div class="generic-widget">
                <h4>${data.title || 'Widget'}</h4>
                <div class="widget-content">
                    ${JSON.stringify(data, null, 2)}
                </div>
            </div>
        `;
    }

    /**
     * 위젯 자동 새로고침 시작
     */
    startWidgetRefresh(widgetId) {
        const widget = this.widgets.get(widgetId);
        if (!widget || this.refreshTimers.has(widgetId)) return;

        const timer = setInterval(() => {
            if (this.isOnline && !document.hidden) {
                this.loadWidgetData(widgetId, false); // 강제 새로고침
            }
        }, widget.refreshInterval);

        this.refreshTimers.set(widgetId, timer);
    }

    /**
     * 위젯 새로고침 중지
     */
    stopWidgetRefresh(widgetId) {
        const timer = this.refreshTimers.get(widgetId);
        if (timer) {
            clearInterval(timer);
            this.refreshTimers.delete(widgetId);
        }
    }

    /**
     * 모든 새로고침 일시 중단
     */
    pauseRefresh() {
        this.refreshTimers.forEach((timer, widgetId) => {
            clearInterval(timer);
        });
        console.log('🔄 Dashboard refresh paused');
    }

    /**
     * 새로고침 재개
     */
    resumeRefresh() {
        this.refreshTimers.clear();
        this.widgets.forEach((widget, widgetId) => {
            if (widget.autoRefresh) {
                this.startWidgetRefresh(widgetId);
            }
        });
        console.log('▶️ Dashboard refresh resumed');
    }

    /**
     * 수동 새로고침
     */
    refreshAll() {
        this.widgets.forEach((widget, widgetId) => {
            this.loadWidgetData(widgetId, false);
        });
        
        this.showNotification('대시보드를 새로고침했습니다.', 'info');
    }

    /**
     * 재시도가 포함된 fetch
     */
    async fetchWithRetry(url, options = {}, attempt = 1) {
        try {
            // URL 파라미터 처리
            if (options.params) {
                const params = new URLSearchParams(options.params);
                url += (url.includes('?') ? '&' : '?') + params.toString();
                delete options.params;
            }

            const response = await fetch(url, options);
            return response;
            
        } catch (error) {
            if (attempt < this.config.retryAttempts) {
                console.log(`Retrying request (${attempt}/${this.config.retryAttempts}):`, url);
                await this.sleep(this.config.retryDelay * attempt);
                return this.fetchWithRetry(url, options, attempt + 1);
            }
            throw error;
        }
    }

    /**
     * 알림 시스템
     */
    async initializeNotifications() {
        if ('Notification' in window) {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                console.log('📱 Notifications enabled');
            }
        }

        // 서버로부터 알림 데이터 가져오기
        this.loadNotifications();
        
        // 주기적 알림 확인
        setInterval(() => {
            this.loadNotifications();
        }, 60000); // 1분마다
    }

    /**
     * 알림 로드
     */
    async loadNotifications() {
        try {
            const response = await fetch('/dashboard/api/notifications/');
            if (response.ok) {
                const data = await response.json();
                this.processNotifications(data.notifications || []);
            }
        } catch (error) {
            console.error('Notifications load failed:', error);
        }
    }

    /**
     * 알림 처리
     */
    processNotifications(notifications) {
        notifications.forEach(notification => {
            if (!notification.is_read && notification.send_push) {
                this.showPushNotification(notification);
            }
        });

        // 알림 배지 업데이트
        const unreadCount = notifications.filter(n => !n.is_read).length;
        this.updateNotificationBadge(unreadCount);
    }

    /**
     * 푸시 알림 표시
     */
    showPushNotification(notification) {
        if (Notification.permission === 'granted') {
            const pushNotification = new Notification(notification.title, {
                body: notification.message,
                icon: '/static/images/logo-notification.png',
                badge: '/static/images/badge.png',
                tag: notification.id,
                requireInteraction: notification.priority === 'high'
            });

            pushNotification.onclick = () => {
                if (notification.action_url) {
                    window.open(notification.action_url, '_blank');
                }
                pushNotification.close();
            };

            // 자동 닫기
            if (notification.auto_dismiss_seconds) {
                setTimeout(() => {
                    pushNotification.close();
                }, notification.auto_dismiss_seconds * 1000);
            }
        }
    }

    /**
     * 오프라인 지원 초기화
     */
    initializeOfflineSupport() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/js/sw.js')
                .then(registration => {
                    console.log('🔧 Service Worker registered:', registration);
                })
                .catch(error => {
                    console.error('Service Worker registration failed:', error);
                });
        }

        // IndexedDB 초기화
        this.initializeIndexedDB();
    }

    /**
     * IndexedDB 초기화
     */
    async initializeIndexedDB() {
        try {
            this.db = await this.openIndexedDB('OneSquareDashboard', 1);
            console.log('💾 IndexedDB initialized');
        } catch (error) {
            console.error('IndexedDB initialization failed:', error);
        }
    }

    /**
     * IndexedDB 열기
     */
    openIndexedDB(name, version) {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(name, version);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // 위젯 데이터 저장소
                if (!db.objectStoreNames.contains('widgetData')) {
                    const store = db.createObjectStore('widgetData', { keyPath: 'id' });
                    store.createIndex('timestamp', 'timestamp');
                }
                
                // 오프라인 큐 저장소
                if (!db.objectStoreNames.contains('offlineQueue')) {
                    db.createObjectStore('offlineQueue', { keyPath: 'id', autoIncrement: true });
                }
            };
        });
    }

    /**
     * 오프라인 데이터 동기화
     */
    async syncOfflineData() {
        if (!this.db) return;

        try {
            const transaction = this.db.transaction(['offlineQueue'], 'readonly');
            const store = transaction.objectStore('offlineQueue');
            const request = store.getAll();

            request.onsuccess = async () => {
                const offlineActions = request.result;
                
                for (const action of offlineActions) {
                    try {
                        // 오프라인 중에 저장된 액션들을 서버로 전송
                        await this.processOfflineAction(action);
                        
                        // 성공적으로 처리된 액션 삭제
                        await this.removeOfflineAction(action.id);
                        
                    } catch (error) {
                        console.error('Offline action sync failed:', action, error);
                    }
                }
                
                if (offlineActions.length > 0) {
                    this.showNotification(`${offlineActions.length}개의 오프라인 작업이 동기화되었습니다.`, 'success');
                }
            };
        } catch (error) {
            console.error('Offline sync failed:', error);
        }
    }

    /**
     * UI 헬퍼 메서드들
     */
    showWidgetLoading(widgetId) {
        const widget = this.widgets.get(widgetId);
        const container = document.getElementById(widget.container);
        if (container) {
            container.innerHTML = `
                <div class="widget-loading">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p class="mt-2">데이터를 불러오는 중...</p>
                </div>
            `;
        }
    }

    handleWidgetError(widgetId, error) {
        const widget = this.widgets.get(widgetId);
        const container = document.getElementById(widget.container);
        if (container) {
            container.innerHTML = `
                <div class="widget-error alert alert-danger">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>오류:</strong> ${error}
                    <button class="btn btn-sm btn-outline-danger mt-2" onclick="dashboard.loadWidgetData('${widgetId}', false)">
                        다시 시도
                    </button>
                </div>
            `;
        }
    }

    showConnectionStatus(message, type = 'info') {
        this.showNotification(message, type);
    }

    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} dashboard-notification`;
        notification.innerHTML = `
            <i class="fas fa-info-circle"></i>
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            min-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;

        document.body.appendChild(notification);

        // 자동 제거
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, duration);
    }

    showCacheIndicator(container) {
        const indicator = document.createElement('div');
        indicator.className = 'cache-indicator';
        indicator.innerHTML = '<i class="fas fa-database"></i> 캐시된 데이터';
        indicator.style.cssText = `
            position: absolute;
            top: 5px;
            right: 5px;
            background: rgba(108, 117, 125, 0.8);
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
        `;
        
        container.style.position = 'relative';
        container.appendChild(indicator);

        setTimeout(() => {
            if (indicator.parentElement) {
                indicator.remove();
            }
        }, 2000);
    }

    updateLastRefreshTime(widgetId) {
        const widget = this.widgets.get(widgetId);
        const container = document.getElementById(widget.container);
        
        let timeIndicator = container.querySelector('.last-refresh-time');
        if (!timeIndicator) {
            timeIndicator = document.createElement('div');
            timeIndicator.className = 'last-refresh-time';
            timeIndicator.style.cssText = `
                position: absolute;
                bottom: 5px;
                right: 5px;
                background: rgba(0,0,0,0.1);
                padding: 2px 6px;
                border-radius: 8px;
                font-size: 10px;
                color: #666;
            `;
            container.style.position = 'relative';
            container.appendChild(timeIndicator);
        }
        
        timeIndicator.textContent = `업데이트: ${new Date().toLocaleTimeString()}`;
    }

    updateNotificationBadge(count) {
        const badge = document.querySelector('.notification-badge');
        if (badge) {
            badge.textContent = count;
            badge.style.display = count > 0 ? 'inline' : 'none';
        }
    }

    /**
     * 유틸리티 메서드들
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    cleanup() {
        // 모든 타이머 정리
        this.refreshTimers.forEach(timer => clearInterval(timer));
        this.refreshTimers.clear();
        
        // 캐시 정리
        this.cache.clear();
        
        console.log('🧹 Dashboard Manager cleaned up');
    }
}

// 전역으로 내보내기
window.DashboardManager = DashboardManager;