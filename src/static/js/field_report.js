/**
 * OneSquare 현장 리포트 시스템 - 메인 JavaScript
 * 
 * 업무 시간 기록, GPS 추적, 오프라인 지원 등
 */

class FieldReportManager {
    constructor() {
        this.currentSession = null;
        this.locationWatcher = null;
        this.sessionTimer = null;
        this.offlineQueue = [];
        
        this.init();
    }

    /**
     * 초기화
     */
    async init() {
        console.log('[FieldReport] Initializing Field Report Manager...');
        
        try {
            // 현재 세션 상태 확인
            await this.checkCurrentSession();
            
            // GPS 권한 요청
            await this.requestLocationPermission();
            
            // 오프라인 큐 초기화
            await this.initOfflineQueue();
            
            // 이벤트 리스너 설정
            this.setupEventListeners();
            
            console.log('[FieldReport] Initialization complete');
            
        } catch (error) {
            console.error('[FieldReport] Initialization failed:', error);
        }
    }

    /**
     * 현재 세션 상태 확인
     */
    async checkCurrentSession() {
        try {
            const response = await fetch('/field-report/api/session-status/');
            const data = await response.json();
            
            if (data.has_active_session) {
                this.currentSession = {
                    id: data.session_id,
                    siteName: data.site_name,
                    status: data.status,
                    startTime: new Date(data.start_time),
                    durationHours: data.duration_hours
                };
                
                console.log('[FieldReport] Active session found:', this.currentSession);
                this.startSessionTimer();
            } else {
                this.currentSession = null;
            }
            
        } catch (error) {
            console.error('[FieldReport] Session status check failed:', error);
        }
    }

    /**
     * GPS 권한 요청
     */
    async requestLocationPermission() {
        if (!navigator.geolocation) {
            console.warn('[FieldReport] Geolocation not supported');
            return false;
        }

        return new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                position => {
                    console.log('[FieldReport] Location permission granted');
                    resolve(true);
                },
                error => {
                    console.warn('[FieldReport] Location permission denied:', error);
                    resolve(false);
                },
                {
                    enableHighAccuracy: false,
                    timeout: 5000,
                    maximumAge: 300000
                }
            );
        });
    }

    /**
     * 세션 타이머 시작
     */
    startSessionTimer() {
        if (!this.currentSession || this.sessionTimer) return;
        
        this.sessionTimer = setInterval(() => {
            this.updateSessionDisplay();
        }, 1000);
        
        // 즉시 한 번 업데이트
        this.updateSessionDisplay();
    }

    /**
     * 세션 표시 업데이트
     */
    updateSessionDisplay() {
        if (!this.currentSession) return;
        
        const timerElement = document.getElementById('work-timer');
        if (timerElement) {
            const now = new Date();
            const diff = now - this.currentSession.startTime;
            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);
            
            timerElement.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }

    /**
     * 세션 타이머 중지
     */
    stopSessionTimer() {
        if (this.sessionTimer) {
            clearInterval(this.sessionTimer);
            this.sessionTimer = null;
        }
    }

    /**
     * 현재 위치 가져오기
     */
    getCurrentLocation(options = {}) {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('Geolocation not supported'));
                return;
            }

            const defaultOptions = {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 60000
            };

            navigator.geolocation.getCurrentPosition(
                position => {
                    resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                        timestamp: new Date(position.timestamp)
                    });
                },
                error => {
                    console.error('[FieldReport] GPS error:', error);
                    reject(error);
                },
                { ...defaultOptions, ...options }
            );
        });
    }

    /**
     * 위치 추적 시작
     */
    startLocationTracking() {
        if (!navigator.geolocation || this.locationWatcher) return;

        this.locationWatcher = navigator.geolocation.watchPosition(
            position => {
                const location = {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    accuracy: position.coords.accuracy,
                    timestamp: new Date()
                };
                
                console.log('[FieldReport] Location update:', location);
                this.handleLocationUpdate(location);
            },
            error => {
                console.warn('[FieldReport] Location tracking error:', error);
            },
            {
                enableHighAccuracy: true,
                timeout: 30000,
                maximumAge: 60000
            }
        );
    }

    /**
     * 위치 추적 중지
     */
    stopLocationTracking() {
        if (this.locationWatcher) {
            navigator.geolocation.clearWatch(this.locationWatcher);
            this.locationWatcher = null;
        }
    }

    /**
     * 위치 업데이트 처리
     */
    handleLocationUpdate(location) {
        // 현재 세션이 있는 경우 위치 정보 저장
        if (this.currentSession) {
            this.saveLocationToOfflineStorage(location);
        }
    }

    /**
     * 오프라인 저장소에 위치 정보 저장
     */
    async saveLocationToOfflineStorage(location) {
        try {
            // IndexedDB에 위치 정보 저장
            if (window.offlineAPI) {
                await window.offlineAPI.saveLocationUpdate({
                    sessionId: this.currentSession.id,
                    ...location
                });
            }
        } catch (error) {
            console.error('[FieldReport] Location save failed:', error);
        }
    }

    /**
     * 업무 시작
     */
    async startWork(siteId, location = null) {
        try {
            showLoading(true);
            
            // GPS 위치 가져오기 (제공되지 않은 경우)
            if (!location) {
                try {
                    location = await this.getCurrentLocation();
                    console.log('[FieldReport] GPS location obtained:', location);
                } catch (error) {
                    console.warn('[FieldReport] GPS failed, continuing without location');
                    location = null;
                }
            }

            const requestData = {
                site_id: siteId,
                latitude: location?.latitude,
                longitude: location?.longitude,
                accuracy: location?.accuracy
            };

            let response;
            
            if (navigator.onLine) {
                // 온라인: 즉시 서버에 전송
                response = await fetch('/field-report/session/start/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.csrfToken
                    },
                    body: JSON.stringify(requestData)
                });

                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.error || '업무 시작에 실패했습니다');
                }

                this.currentSession = {
                    id: result.session_id,
                    siteName: result.site_name,
                    startTime: new Date(result.start_time),
                    status: 'started'
                };

                this.startSessionTimer();
                this.startLocationTracking();

                showToast(result.message, 'success');
                return result;
                
            } else {
                // 오프라인: 큐에 저장
                await this.addToOfflineQueue({
                    type: 'start_session',
                    data: requestData,
                    timestamp: new Date().toISOString()
                });

                // 임시 세션 생성
                this.currentSession = {
                    id: `temp_${Date.now()}`,
                    siteName: '선택된 현장',
                    startTime: new Date(),
                    status: 'started',
                    offline: true
                };

                this.startSessionTimer();
                this.startLocationTracking();

                showToast('오프라인 모드로 업무를 시작했습니다', 'warning');
                return { success: true, offline: true };
            }

        } catch (error) {
            console.error('[FieldReport] Start work failed:', error);
            showToast(error.message, 'error');
            throw error;
        } finally {
            showLoading(false);
        }
    }

    /**
     * 업무 종료
     */
    async endWork(notes = '') {
        if (!this.currentSession) {
            throw new Error('진행 중인 업무가 없습니다');
        }

        try {
            showLoading(true);
            
            // GPS 위치 가져오기
            let location = null;
            try {
                location = await this.getCurrentLocation();
            } catch (error) {
                console.warn('[FieldReport] End location failed:', error);
            }

            const requestData = {
                latitude: location?.latitude,
                longitude: location?.longitude,
                notes: notes
            };

            if (navigator.onLine && !this.currentSession.offline) {
                // 온라인: 즉시 서버에 전송
                const response = await fetch(`/field-report/session/${this.currentSession.id}/end/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.csrfToken
                    },
                    body: JSON.stringify(requestData)
                });

                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.error || '업무 종료에 실패했습니다');
                }

                showToast(`업무 완료! (총 ${result.duration_hours.toFixed(1)}시간)`, 'success');
                
            } else {
                // 오프라인 또는 임시 세션: 큐에 저장
                await this.addToOfflineQueue({
                    type: 'end_session',
                    sessionId: this.currentSession.id,
                    data: requestData,
                    timestamp: new Date().toISOString()
                });

                const duration = (new Date() - this.currentSession.startTime) / (1000 * 60 * 60);
                showToast(`업무 완료! (총 ${duration.toFixed(1)}시간) - 온라인 시 동기화됩니다`, 'warning');
            }

            // 세션 정리
            this.stopSessionTimer();
            this.stopLocationTracking();
            this.currentSession = null;

            return { success: true };

        } catch (error) {
            console.error('[FieldReport] End work failed:', error);
            showToast(error.message, 'error');
            throw error;
        } finally {
            showLoading(false);
        }
    }

    /**
     * 업무 일시 중지
     */
    async pauseWork() {
        if (!this.currentSession) return;

        try {
            if (navigator.onLine && !this.currentSession.offline) {
                const response = await fetch(`/field-report/session/${this.currentSession.id}/pause/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': window.csrfToken
                    }
                });

                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.error);
                }
            } else {
                await this.addToOfflineQueue({
                    type: 'pause_session',
                    sessionId: this.currentSession.id,
                    timestamp: new Date().toISOString()
                });
            }

            this.currentSession.status = 'paused';
            this.stopLocationTracking();
            
            showToast('업무가 일시 중지되었습니다', 'info');

        } catch (error) {
            console.error('[FieldReport] Pause work failed:', error);
            showToast(error.message, 'error');
        }
    }

    /**
     * 업무 재개
     */
    async resumeWork() {
        if (!this.currentSession) return;

        try {
            if (navigator.onLine && !this.currentSession.offline) {
                const response = await fetch(`/field-report/session/${this.currentSession.id}/resume/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': window.csrfToken
                    }
                });

                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.error);
                }
            } else {
                await this.addToOfflineQueue({
                    type: 'resume_session',
                    sessionId: this.currentSession.id,
                    timestamp: new Date().toISOString()
                });
            }

            this.currentSession.status = 'resumed';
            this.startLocationTracking();
            
            showToast('업무가 재개되었습니다', 'info');

        } catch (error) {
            console.error('[FieldReport] Resume work failed:', error);
            showToast(error.message, 'error');
        }
    }

    /**
     * 오프라인 큐 초기화
     */
    async initOfflineQueue() {
        try {
            // IndexedDB에서 오프라인 큐 로드
            if (window.offlineAPI) {
                this.offlineQueue = await window.offlineAPI.getOfflineQueue() || [];
                console.log('[FieldReport] Offline queue loaded:', this.offlineQueue.length, 'items');
            }
        } catch (error) {
            console.error('[FieldReport] Offline queue init failed:', error);
            this.offlineQueue = [];
        }
    }

    /**
     * 오프라인 큐에 추가
     */
    async addToOfflineQueue(item) {
        try {
            this.offlineQueue.push({
                id: Date.now(),
                ...item
            });

            // IndexedDB에 저장
            if (window.offlineAPI) {
                await window.offlineAPI.addOfflineOperation(item);
            }

            console.log('[FieldReport] Added to offline queue:', item.type);
        } catch (error) {
            console.error('[FieldReport] Add to offline queue failed:', error);
        }
    }

    /**
     * 오프라인 큐 처리
     */
    async processOfflineQueue() {
        if (!navigator.onLine || this.offlineQueue.length === 0) return;

        console.log('[FieldReport] Processing offline queue:', this.offlineQueue.length, 'items');
        
        try {
            // PWA 동기화 매니저 사용
            if (window.offlineAPI) {
                await window.offlineAPI.performSync();
            }

            // 큐 정리
            this.offlineQueue = [];
            showToast('오프라인 데이터가 동기화되었습니다', 'success');

        } catch (error) {
            console.error('[FieldReport] Offline queue processing failed:', error);
            showToast('일부 데이터 동기화에 실패했습니다', 'warning');
        }
    }

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        // 네트워크 상태 변경 감지
        window.addEventListener('online', () => {
            console.log('[FieldReport] Network online - processing offline queue');
            this.processOfflineQueue();
        });

        window.addEventListener('offline', () => {
            console.log('[FieldReport] Network offline - switching to offline mode');
        });

        // 페이지 언로드 시 정리
        window.addEventListener('beforeunload', () => {
            this.stopLocationTracking();
            this.stopSessionTimer();
        });

        // Visibility API - 앱이 백그라운드로 가거나 포그라운드로 올 때
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                // 포그라운드로 복귀 시 세션 상태 확인
                this.checkCurrentSession();
            }
        });
    }

    /**
     * 세션 통계 가져오기
     */
    async getSessionStats() {
        try {
            const response = await fetch('/field-report/api/reports-summary/');
            return await response.json();
        } catch (error) {
            console.error('[FieldReport] Get session stats failed:', error);
            return null;
        }
    }

    /**
     * 현재 세션 정보 반환
     */
    getCurrentSession() {
        return this.currentSession;
    }

    /**
     * 오프라인 큐 상태 반환
     */
    getOfflineQueueStatus() {
        return {
            count: this.offlineQueue.length,
            items: this.offlineQueue
        };
    }
}

// 전역 인스턴스
let fieldReportManager = null;

// DOM 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    fieldReportManager = new FieldReportManager();
    window.fieldReportManager = fieldReportManager;
});

// 유틸리티 함수들
function showLoading(show) {
    const spinner = document.getElementById('loading-spinner');
    if (spinner) {
        spinner.classList.toggle('d-none', !show);
    }
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;

    const toastBody = toast.querySelector('.toast-body');
    const toastHeader = toast.querySelector('.toast-header');
    
    // 아이콘 및 색상 설정
    const icons = {
        success: 'bi-check-circle text-success',
        error: 'bi-exclamation-circle text-danger',
        warning: 'bi-exclamation-triangle text-warning',
        info: 'bi-info-circle text-primary'
    };
    
    const icon = toastHeader.querySelector('i');
    icon.className = `bi ${icons[type] || icons.info} me-2`;
    
    toastBody.textContent = message;
    
    const bsToast = new bootstrap.Toast(toast, {
        autohide: type !== 'error',
        delay: type === 'error' ? 10000 : 5000
    });
    
    bsToast.show();
}

function showConfirm(message) {
    return new Promise((resolve) => {
        const modal = document.getElementById('confirmModal');
        const messageElement = document.getElementById('confirm-message');
        const okButton = document.getElementById('confirm-ok');
        
        messageElement.textContent = message;
        
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        const handleOk = () => {
            bsModal.hide();
            okButton.removeEventListener('click', handleOk);
            resolve(true);
        };
        
        const handleHide = () => {
            modal.removeEventListener('hidden.bs.modal', handleHide);
            resolve(false);
        };
        
        okButton.addEventListener('click', handleOk);
        modal.addEventListener('hidden.bs.modal', handleHide);
    });
}