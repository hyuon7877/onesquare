/**
 * OneSquare PWA - 향상된 알림 데모 시스템
 * 
 * 오프라인 대시보드와 통합된 실시간 알림 데모
 * 다양한 시나리오에 따른 알림 시뮬레이션
 */

class EnhancedNotificationDemo {
    constructor() {
        this.isEnabled = false;
        this.demoIntervals = [];
        this.notificationQueue = [];
        this.scenarios = this.initializeScenarios();
        this.pushManager = null;
        this.notificationSystem = null;
        
        this.init();
    }
    
    async init() {
        console.log('🎬 Enhanced Notification Demo initializing...');
        
        try {
            // Push Manager 연결
            if (window.pushManager) {
                this.pushManager = window.pushManager;
            }
            
            // Notification System 연결
            if (window.notificationSystem) {
                this.notificationSystem = window.notificationSystem;
            }
            
            // 오프라인 대시보드 이벤트 연결
            this.connectOfflineDashboardEvents();
            
            console.log('✅ Enhanced Notification Demo initialized');
            
        } catch (error) {
            console.error('❌ Failed to initialize notification demo:', error);
        }
    }
    
    initializeScenarios() {
        return {
            // Notion 동기화 시나리오
            notionSync: {
                name: 'Notion 동기화',
                enabled: true,
                interval: 60000, // 1분
                notifications: [
                    {
                        type: 'info',
                        title: 'Notion 동기화 시작',
                        message: '최신 데이터를 동기화하고 있습니다...',
                        priority: 'medium',
                        duration: 3000
                    },
                    {
                        type: 'success',
                        title: 'Notion 동기화 완료',
                        message: '12개의 페이지가 성공적으로 동기화되었습니다.',
                        priority: 'medium',
                        duration: 5000,
                        delay: 15000
                    }
                ]
            },
            
            // 오프라인 동기화 시나리오
            offlineSync: {
                name: '오프라인 동기화',
                enabled: true,
                interval: 180000, // 3분
                notifications: [
                    {
                        type: 'warning',
                        title: '오프라인 데이터 감지',
                        message: '3개의 오프라인 작업이 대기 중입니다.',
                        priority: 'high',
                        duration: 4000
                    },
                    {
                        type: 'success',
                        title: '오프라인 동기화 완료',
                        message: '모든 오프라인 데이터가 성공적으로 동기화되었습니다.',
                        priority: 'medium',
                        duration: 5000,
                        delay: 20000
                    }
                ]
            },
            
            // 매출 알림 시나리오
            revenueAlert: {
                name: '매출 알림',
                enabled: true,
                interval: 300000, // 5분
                notifications: [
                    {
                        type: 'success',
                        title: '일일 매출 목표 달성',
                        message: '오늘 매출이 1,500,000원을 달성했습니다! 🎉',
                        priority: 'high',
                        duration: 6000,
                        actions: [
                            { action: 'view', title: '매출 보기', url: '/revenue/' }
                        ]
                    }
                ]
            },
            
            // 시스템 상태 알림
            systemHealth: {
                name: '시스템 상태',
                enabled: true,
                interval: 240000, // 4분
                notifications: [
                    {
                        type: 'warning',
                        title: '높은 API 응답 시간',
                        message: 'Notion API 응답 시간이 평소보다 높습니다 (2.3초)',
                        priority: 'medium',
                        duration: 4000
                    },
                    {
                        type: 'info',
                        title: '시스템 상태 정상화',
                        message: 'API 응답 시간이 정상 수준으로 회복되었습니다.',
                        priority: 'low',
                        duration: 3000,
                        delay: 30000
                    }
                ]
            },
            
            // 긴급 알림 시나리오
            urgentAlert: {
                name: '긴급 알림',
                enabled: false, // 기본적으로 비활성화
                interval: 600000, // 10분
                notifications: [
                    {
                        type: 'error',
                        title: '중요: 데이터베이스 연결 오류',
                        message: 'Notion 데이터베이스에 연결할 수 없습니다. 즉시 확인이 필요합니다.',
                        priority: 'critical',
                        duration: 0, // 수동으로 닫을 때까지 표시
                        requireInteraction: true,
                        actions: [
                            { action: 'check', title: '상태 확인', url: '/dashboard/status/' },
                            { action: 'contact', title: '지원팀 연락', url: 'mailto:support@example.com' }
                        ]
                    }
                ]
            }
        };
    }
    
    connectOfflineDashboardEvents() {
        // 오프라인 대시보드 이벤트 리스너 등록
        document.addEventListener('dashboard:dataSync', (event) => {
            this.handleDataSyncEvent(event.detail);
        });
        
        document.addEventListener('dashboard:offlineMode', (event) => {
            this.handleOfflineModeEvent(event.detail);
        });
        
        document.addEventListener('dashboard:performanceWarning', (event) => {
            this.handlePerformanceWarning(event.detail);
        });
        
        document.addEventListener('dashboard:errorOccurred', (event) => {
            this.handleErrorEvent(event.detail);
        });
    }
    
    handleDataSyncEvent(detail) {
        const notification = {
            type: detail.success ? 'success' : 'error',
            title: detail.success ? 'Notion 동기화 완료' : 'Notion 동기화 실패',
            message: detail.message || (detail.success ? 
                '최신 데이터가 성공적으로 동기화되었습니다.' : 
                '데이터 동기화 중 오류가 발생했습니다.'),
            priority: detail.success ? 'medium' : 'high',
            duration: 4000,
            timestamp: new Date().toISOString()
        };
        
        this.showNotification(notification);
    }
    
    handleOfflineModeEvent(detail) {
        const notification = {
            type: 'warning',
            title: detail.isOffline ? '오프라인 모드 활성화' : '온라인 모드 복구',
            message: detail.isOffline ? 
                '네트워크 연결이 끊어졌습니다. 오프라인 기능을 사용하여 계속 작업할 수 있습니다.' :
                '네트워크 연결이 복구되었습니다. 오프라인 데이터를 동기화합니다.',
            priority: detail.isOffline ? 'high' : 'medium',
            duration: detail.isOffline ? 6000 : 4000,
            timestamp: new Date().toISOString()
        };
        
        this.showNotification(notification);
    }
    
    handlePerformanceWarning(detail) {
        const notification = {
            type: 'warning',
            title: '성능 경고',
            message: detail.message || '시스템 성능이 저하되었습니다.',
            priority: 'medium',
            duration: 4000,
            timestamp: new Date().toISOString(),
            actions: [
                { action: 'optimize', title: '최적화 실행', url: '/dashboard/optimize/' }
            ]
        };
        
        this.showNotification(notification);
    }
    
    handleErrorEvent(detail) {
        const notification = {
            type: 'error',
            title: '오류 발생',
            message: detail.message || '시스템 오류가 발생했습니다.',
            priority: detail.critical ? 'critical' : 'high',
            duration: detail.critical ? 0 : 5000,
            requireInteraction: detail.critical,
            timestamp: new Date().toISOString()
        };
        
        this.showNotification(notification);
    }
    
    startDemo() {
        if (this.isEnabled) {
            console.warn('Notification demo is already running');
            return;
        }
        
        this.isEnabled = true;
        console.log('🎬 Starting notification demo...');
        
        // 각 시나리오별 간격으로 데모 실행
        Object.entries(this.scenarios).forEach(([key, scenario]) => {
            if (scenario.enabled) {
                this.startScenario(key, scenario);
            }
        });
        
        // 환영 메시지 표시
        setTimeout(() => {
            this.showNotification({
                type: 'info',
                title: '알림 데모 시작',
                message: '다양한 알림 시나리오를 체험해보세요. 설정에서 언제든지 비활성화할 수 있습니다.',
                priority: 'low',
                duration: 5000
            });
        }, 1000);
    }
    
    stopDemo() {
        if (!this.isEnabled) {
            console.warn('Notification demo is not running');
            return;
        }
        
        this.isEnabled = false;
        console.log('⏹️ Stopping notification demo...');
        
        // 모든 인터벌 정리
        this.demoIntervals.forEach(intervalId => {
            clearInterval(intervalId);
        });
        this.demoIntervals = [];
        
        // 큐 정리
        this.notificationQueue = [];
        
        // 종료 메시지
        this.showNotification({
            type: 'info',
            title: '알림 데모 종료',
            message: '알림 데모가 중지되었습니다.',
            priority: 'low',
            duration: 3000
        });
    }
    
    startScenario(scenarioKey, scenario) {
        console.log(`🎭 Starting scenario: ${scenario.name}`);
        
        const intervalId = setInterval(() => {
            if (!this.isEnabled) {
                clearInterval(intervalId);
                return;
            }
            
            this.executeScenario(scenario);
        }, scenario.interval);
        
        this.demoIntervals.push(intervalId);
        
        // 첫 실행 (5초 후)
        setTimeout(() => {
            if (this.isEnabled) {
                this.executeScenario(scenario);
            }
        }, Math.random() * 5000 + 5000);
    }
    
    executeScenario(scenario) {
        scenario.notifications.forEach((notification, index) => {
            const delay = notification.delay || (index * 1000);
            
            setTimeout(() => {
                if (this.isEnabled) {
                    this.showNotification({
                        ...notification,
                        timestamp: new Date().toISOString()
                    });
                }
            }, delay);
        });
    }
    
    async showNotification(notification) {
        try {
            // 브라우저 푸시 알림 (권한이 있는 경우)
            if (this.pushManager && Notification.permission === 'granted') {
                await this.pushManager.showLocalNotification(notification.title, {
                    body: notification.message,
                    icon: '/static/images/icons/icon-192x192.png',
                    badge: '/static/images/icons/badge-72x72.png',
                    tag: `demo-${Date.now()}`,
                    requireInteraction: notification.requireInteraction || false,
                    actions: notification.actions || []
                });
            }
            
            // 인앱 알림 시스템
            if (this.notificationSystem) {
                // 가상의 알림 데이터 생성
                const mockNotification = {
                    id: `demo-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                    title: notification.title,
                    message: notification.message,
                    type: notification.type || 'info',
                    priority: notification.priority || 'medium',
                    is_read: false,
                    created_at: notification.timestamp || new Date().toISOString(),
                    action_url: notification.actions?.[0]?.url || null
                };
                
                // 알림 시스템에 추가
                this.notificationSystem.notifications.unshift(mockNotification);
                this.notificationSystem.unreadCount++;
                this.notificationSystem.renderNotifications();
                this.notificationSystem.updateBadge();
                
                // 벨 아이콘 애니메이션
                const bellIcon = document.getElementById('notification-bell');
                if (bellIcon) {
                    bellIcon.classList.add('ringing');
                    setTimeout(() => {
                        bellIcon.classList.remove('ringing');
                    }, 500);
                }
            }
            
            // 콘솔 로그
            console.log(`🔔 [${notification.type.toUpperCase()}] ${notification.title}: ${notification.message}`);
            
        } catch (error) {
            console.error('Failed to show notification:', error);
        }
    }
    
    // 특정 시나리오 토글
    toggleScenario(scenarioKey, enabled) {
        if (this.scenarios[scenarioKey]) {
            this.scenarios[scenarioKey].enabled = enabled;
            
            if (this.isEnabled) {
                // 실행 중인 경우 재시작
                this.stopDemo();
                setTimeout(() => this.startDemo(), 1000);
            }
        }
    }
    
    // 즉시 테스트 알림 발송
    async sendTestNotification(type = 'info') {
        const testNotifications = {
            info: {
                type: 'info',
                title: '정보 알림 테스트',
                message: '이것은 정보 알림 테스트입니다.',
                priority: 'medium'
            },
            success: {
                type: 'success',
                title: '성공 알림 테스트',
                message: '작업이 성공적으로 완료되었습니다! ✅',
                priority: 'medium'
            },
            warning: {
                type: 'warning',
                title: '경고 알림 테스트',
                message: '주의가 필요한 상황이 발생했습니다. ⚠️',
                priority: 'high'
            },
            error: {
                type: 'error',
                title: '오류 알림 테스트',
                message: '시스템 오류가 발생했습니다. 확인이 필요합니다. ❌',
                priority: 'critical'
            }
        };
        
        const notification = testNotifications[type] || testNotifications.info;
        await this.showNotification(notification);
    }
    
    // 통계 정보 조회
    getStats() {
        return {
            isEnabled: this.isEnabled,
            activeScenarios: Object.values(this.scenarios).filter(s => s.enabled).length,
            totalScenarios: Object.keys(this.scenarios).length,
            queueLength: this.notificationQueue.length,
            runningIntervals: this.demoIntervals.length
        };
    }
    
    // 설정 내보내기/가져오기
    exportSettings() {
        return {
            scenarios: this.scenarios,
            isEnabled: this.isEnabled
        };
    }
    
    importSettings(settings) {
        if (settings.scenarios) {
            this.scenarios = { ...this.scenarios, ...settings.scenarios };
        }
        
        if (settings.isEnabled && !this.isEnabled) {
            this.startDemo();
        } else if (!settings.isEnabled && this.isEnabled) {
            this.stopDemo();
        }
    }
}

// 전역 인스턴스 생성
let notificationDemo;

// DOM 로드 후 초기화
document.addEventListener('DOMContentLoaded', () => {
    notificationDemo = new EnhancedNotificationDemo();
    
    // 전역 접근을 위해 window 객체에 등록
    window.notificationDemo = notificationDemo;
});

// 전역 함수들 (테스트 및 디버깅용)
window.startNotificationDemo = () => notificationDemo?.startDemo();
window.stopNotificationDemo = () => notificationDemo?.stopDemo();
window.testNotification = (type) => notificationDemo?.sendTestNotification(type);
window.getNotificationStats = () => notificationDemo?.getStats();

export default EnhancedNotificationDemo;