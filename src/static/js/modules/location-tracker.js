/**
 * OneSquare - GPS 위치 추적 모듈
 * 
 * 업무 시간 기록을 위한 정확한 GPS 위치 추적 및 검증
 */

class LocationTracker {
    constructor() {
        this.currentPosition = null;
        this.watchId = null;
        this.locationHistory = [];
        this.isTracking = false;
        this.accuracy = null;
        
        // 설정값
        this.config = {
            enableHighAccuracy: true,
            timeout: 30000, // 30초
            maximumAge: 60000, // 1분
            minAccuracy: 100, // 100m 이내
            locationHistoryLimit: 100, // 최대 위치 기록 수
            trackingInterval: 30000, // 30초마다 위치 업데이트
            geofenceRadius: 200 // 지오펜스 반경 (미터)
        };
        
        this.callbacks = {
            locationUpdate: [],
            locationError: [],
            accuracyImproved: [],
            geofenceEnter: [],
            geofenceExit: []
        };
        
        this.init();
    }

    /**
     * 초기화
     */
    async init() {
        console.log('[LocationTracker] Initializing location tracker...');
        
        // 지리적 위치 API 지원 확인
        if (!this.isGeolocationSupported()) {
            console.error('[LocationTracker] Geolocation not supported');
            return false;
        }
        
        // 권한 요청
        const permissionGranted = await this.requestLocationPermission();
        if (!permissionGranted) {
            console.warn('[LocationTracker] Location permission denied');
            return false;
        }
        
        console.log('[LocationTracker] Location tracker initialized successfully');
        return true;
    }

    /**
     * 지리적 위치 API 지원 여부 확인
     */
    isGeolocationSupported() {
        return 'geolocation' in navigator;
    }

    /**
     * 위치 권한 요청
     */
    async requestLocationPermission() {
        if (!navigator.permissions) {
            // permissions API가 지원되지 않는 경우, 직접 위치 요청
            return this.testGeolocation();
        }

        try {
            const permission = await navigator.permissions.query({ name: 'geolocation' });
            
            switch (permission.state) {
                case 'granted':
                    console.log('[LocationTracker] Location permission already granted');
                    return true;
                    
                case 'denied':
                    console.warn('[LocationTracker] Location permission denied');
                    this.triggerCallback('locationError', {
                        code: 1,
                        message: '위치 권한이 거부되었습니다. 브라우저 설정에서 위치 권한을 허용해주세요.'
                    });
                    return false;
                    
                case 'prompt':
                    console.log('[LocationTracker] Requesting location permission...');
                    return this.testGeolocation();
                    
                default:
                    return this.testGeolocation();
            }
        } catch (error) {
            console.warn('[LocationTracker] Permission API error:', error);
            return this.testGeolocation();
        }
    }

    /**
     * 지리적 위치 테스트 (권한 확인용)
     */
    testGeolocation() {
        return new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    console.log('[LocationTracker] Location permission granted via test');
                    this.currentPosition = position;
                    resolve(true);
                },
                (error) => {
                    console.warn('[LocationTracker] Location test failed:', error);
                    this.handleLocationError(error);
                    resolve(false);
                },
                {
                    enableHighAccuracy: false,
                    timeout: 10000,
                    maximumAge: 300000
                }
            );
        });
    }

    /**
     * 위치 추적 시작
     */
    startTracking() {
        if (this.isTracking) {
            console.warn('[LocationTracker] Already tracking location');
            return;
        }

        console.log('[LocationTracker] Starting location tracking...');
        this.isTracking = true;

        // 정확한 위치 추적 시작
        this.watchId = navigator.geolocation.watchPosition(
            this.handleLocationUpdate.bind(this),
            this.handleLocationError.bind(this),
            {
                enableHighAccuracy: this.config.enableHighAccuracy,
                timeout: this.config.timeout,
                maximumAge: this.config.maximumAge
            }
        );

        // 주기적 위치 업데이트 (watchPosition 백업)
        this.trackingTimer = setInterval(() => {
            this.getCurrentPosition().then(position => {
                if (position) {
                    this.handleLocationUpdate(position);
                }
            });
        }, this.config.trackingInterval);
    }

    /**
     * 위치 추적 중지
     */
    stopTracking() {
        if (!this.isTracking) {
            console.warn('[LocationTracker] Not currently tracking location');
            return;
        }

        console.log('[LocationTracker] Stopping location tracking...');
        this.isTracking = false;

        if (this.watchId !== null) {
            navigator.geolocation.clearWatch(this.watchId);
            this.watchId = null;
        }

        if (this.trackingTimer) {
            clearInterval(this.trackingTimer);
            this.trackingTimer = null;
        }
    }

    /**
     * 현재 위치 가져오기 (일회성)
     */
    getCurrentPosition() {
        return new Promise((resolve, reject) => {
            if (!this.isGeolocationSupported()) {
                reject(new Error('Geolocation not supported'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    this.currentPosition = position;
                    resolve(position);
                },
                (error) => {
                    this.handleLocationError(error);
                    reject(error);
                },
                {
                    enableHighAccuracy: this.config.enableHighAccuracy,
                    timeout: this.config.timeout,
                    maximumAge: this.config.maximumAge
                }
            );
        });
    }

    /**
     * 위치 업데이트 핸들러
     */
    handleLocationUpdate(position) {
        const coords = position.coords;
        const timestamp = new Date(position.timestamp);

        // 정확도 체크
        if (coords.accuracy > this.config.minAccuracy) {
            console.warn(`[LocationTracker] Low accuracy: ${coords.accuracy}m`);
        }

        // 이전 정확도와 비교
        if (this.accuracy === null || coords.accuracy < this.accuracy) {
            this.accuracy = coords.accuracy;
            this.triggerCallback('accuracyImproved', {
                accuracy: coords.accuracy,
                position: position
            });
        }

        // 현재 위치 업데이트
        this.currentPosition = position;

        // 위치 기록 추가
        const locationData = {
            latitude: coords.latitude,
            longitude: coords.longitude,
            accuracy: coords.accuracy,
            altitude: coords.altitude,
            heading: coords.heading,
            speed: coords.speed,
            timestamp: timestamp
        };

        this.addLocationToHistory(locationData);

        // 지오펜스 체크
        this.checkGeofences(locationData);

        // 콜백 실행
        this.triggerCallback('locationUpdate', {
            position: position,
            locationData: locationData,
            isHighAccuracy: coords.accuracy <= this.config.minAccuracy
        });

        console.log(`[LocationTracker] Location updated: ${coords.latitude.toFixed(6)}, ${coords.longitude.toFixed(6)} (±${coords.accuracy}m)`);
    }

    /**
     * 위치 오류 핸들러
     */
    handleLocationError(error) {
        let errorMessage = '';
        
        switch (error.code) {
            case error.PERMISSION_DENIED:
                errorMessage = '위치 권한이 거부되었습니다.';
                break;
            case error.POSITION_UNAVAILABLE:
                errorMessage = '위치 정보를 사용할 수 없습니다.';
                break;
            case error.TIMEOUT:
                errorMessage = '위치 요청 시간이 초과되었습니다.';
                break;
            default:
                errorMessage = '알 수 없는 위치 오류가 발생했습니다.';
                break;
        }

        console.error('[LocationTracker] Location error:', errorMessage, error);
        
        this.triggerCallback('locationError', {
            code: error.code,
            message: errorMessage,
            originalError: error
        });
    }

    /**
     * 위치 기록에 추가
     */
    addLocationToHistory(locationData) {
        this.locationHistory.push(locationData);
        
        // 기록 수 제한
        if (this.locationHistory.length > this.config.locationHistoryLimit) {
            this.locationHistory.shift();
        }
    }

    /**
     * 지오펜스 체크
     */
    checkGeofences(currentLocation) {
        // 여기에 지오펜스 로직 구현
        // 현재는 기본 구현만 제공
    }

    /**
     * 두 지점 간 거리 계산 (Haversine 공식)
     */
    calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371000; // 지구 반지름 (미터)
        const dLat = this.toRadians(lat2 - lat1);
        const dLon = this.toRadians(lon2 - lon1);
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(this.toRadians(lat1)) * Math.cos(this.toRadians(lat2)) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    /**
     * 도를 라디안으로 변환
     */
    toRadians(degrees) {
        return degrees * Math.PI / 180;
    }

    /**
     * 위치 검증 (현장과의 거리 체크)
     */
    verifyLocationAtSite(siteLatitude, siteLongitude, toleranceMeters = 200) {
        if (!this.currentPosition) {
            return {
                verified: false,
                reason: '현재 위치를 확인할 수 없습니다.'
            };
        }

        const currentCoords = this.currentPosition.coords;
        const distance = this.calculateDistance(
            currentCoords.latitude,
            currentCoords.longitude,
            siteLatitude,
            siteLongitude
        );

        const verified = distance <= toleranceMeters;
        
        return {
            verified: verified,
            distance: Math.round(distance),
            tolerance: toleranceMeters,
            accuracy: currentCoords.accuracy,
            reason: verified ? 
                '위치가 확인되었습니다.' : 
                `현장으로부터 ${Math.round(distance)}m 떨어져 있습니다. (허용범위: ${toleranceMeters}m)`
        };
    }

    /**
     * 이동 거리 계산
     */
    getTotalDistanceTraveled() {
        if (this.locationHistory.length < 2) {
            return 0;
        }

        let totalDistance = 0;
        for (let i = 1; i < this.locationHistory.length; i++) {
            const prev = this.locationHistory[i - 1];
            const curr = this.locationHistory[i];
            totalDistance += this.calculateDistance(
                prev.latitude, prev.longitude,
                curr.latitude, curr.longitude
            );
        }

        return totalDistance;
    }

    /**
     * 위치 정확도 품질 평가
     */
    getLocationQuality() {
        if (!this.currentPosition) {
            return 'unknown';
        }

        const accuracy = this.currentPosition.coords.accuracy;
        
        if (accuracy <= 5) return 'excellent';
        if (accuracy <= 20) return 'good';
        if (accuracy <= 50) return 'fair';
        if (accuracy <= 100) return 'poor';
        return 'very_poor';
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
                    console.error(`[LocationTracker] Error in ${event} callback:`, error);
                }
            });
        }
    }

    /**
     * 위치 정보 내보내기 (백업용)
     */
    exportLocationData() {
        return {
            currentPosition: this.currentPosition,
            locationHistory: this.locationHistory,
            totalDistance: this.getTotalDistanceTraveled(),
            quality: this.getLocationQuality(),
            exportTime: new Date().toISOString()
        };
    }

    /**
     * 배터리 최적화 모드
     */
    enableBatterySaver() {
        this.config.enableHighAccuracy = false;
        this.config.timeout = 60000; // 1분
        this.config.maximumAge = 300000; // 5분
        this.config.trackingInterval = 120000; // 2분
        
        console.log('[LocationTracker] Battery saver mode enabled');
        
        // 추적 중이라면 재시작
        if (this.isTracking) {
            this.stopTracking();
            setTimeout(() => this.startTracking(), 1000);
        }
    }

    /**
     * 고정밀 모드
     */
    enableHighPrecision() {
        this.config.enableHighAccuracy = true;
        this.config.timeout = 15000; // 15초
        this.config.maximumAge = 30000; // 30초
        this.config.trackingInterval = 15000; // 15초
        
        console.log('[LocationTracker] High precision mode enabled');
        
        // 추적 중이라면 재시작
        if (this.isTracking) {
            this.stopTracking();
            setTimeout(() => this.startTracking(), 1000);
        }
    }

    /**
     * 상태 정보 반환
     */
    getStatus() {
        return {
            isTracking: this.isTracking,
            isSupported: this.isGeolocationSupported(),
            currentPosition: this.currentPosition,
            accuracy: this.accuracy,
            locationHistory: this.locationHistory.length,
            quality: this.getLocationQuality(),
            config: this.config
        };
    }
}

// 전역 인스턴스 생성
const locationTracker = new LocationTracker();

// 모듈 내보내기
window.LocationTracker = LocationTracker;
window.locationTracker = locationTracker;