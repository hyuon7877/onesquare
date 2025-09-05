/**
 * OneSquare - 카메라 촬영 및 이미지 처리 모듈
 * 
 * 모바일 최적화된 카메라 촬영, 이미지 압축, 썸네일 생성
 */

class CameraCapture {
    constructor() {
        this.stream = null;
        this.video = null;
        this.canvas = null;
        this.ctx = null;
        this.isCapturing = false;
        this.facingMode = 'environment'; // 후면 카메라 기본값
        
        // 압축 설정
        this.compressionConfig = {
            maxWidth: 1920,
            maxHeight: 1080,
            quality: 0.85,
            thumbnailSize: 150,
            thumbnailQuality: 0.7,
            maxFileSize: 2 * 1024 * 1024 // 2MB
        };
        
        // 지원되는 이미지 형식
        this.supportedFormats = ['image/jpeg', 'image/png', 'image/webp'];
        
        this.callbacks = {
            photoTaken: [],
            error: [],
            streamReady: [],
            compressionComplete: []
        };
        
        this.init();
    }

    /**
     * 초기화
     */
    async init() {
        console.log('[CameraCapture] Initializing camera capture module...');
        
        // 미디어 API 지원 확인
        if (!this.isMediaSupported()) {
            console.error('[CameraCapture] Media API not supported');
            return false;
        }
        
        // Canvas 초기화
        this.setupCanvas();
        
        console.log('[CameraCapture] Camera capture module initialized');
        return true;
    }

    /**
     * 미디어 API 지원 여부 확인
     */
    isMediaSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    /**
     * Canvas 설정
     */
    setupCanvas() {
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
    }

    /**
     * 카메라 스트림 시작
     */
    async startCamera(videoElement, options = {}) {
        try {
            // 기존 스트림이 있으면 정지
            if (this.stream) {
                this.stopCamera();
            }

            // 카메라 제약 조건 설정
            const constraints = {
                video: {
                    facingMode: options.facingMode || this.facingMode,
                    width: { ideal: 1920, max: 1920 },
                    height: { ideal: 1080, max: 1080 },
                    frameRate: { ideal: 30, max: 30 }
                },
                audio: false
            };

            // 카메라 스트림 획득
            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            
            // 비디오 엘리먼트에 스트림 연결
            if (videoElement) {
                this.video = videoElement;
                this.video.srcObject = this.stream;
                this.video.autoplay = true;
                this.video.playsInline = true;
                this.video.muted = true;
                
                // 스트림 준비 완료 대기
                await new Promise((resolve) => {
                    this.video.onloadedmetadata = () => {
                        resolve();
                    };
                });
            }

            this.isCapturing = true;
            this.triggerCallback('streamReady', { stream: this.stream });
            
            console.log('[CameraCapture] Camera stream started successfully');
            return true;

        } catch (error) {
            console.error('[CameraCapture] Failed to start camera:', error);
            this.handleError(error);
            return false;
        }
    }

    /**
     * 카메라 스트림 중지
     */
    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => {
                track.stop();
            });
            this.stream = null;
        }

        if (this.video) {
            this.video.srcObject = null;
        }

        this.isCapturing = false;
        console.log('[CameraCapture] Camera stream stopped');
    }

    /**
     * 사진 촬영
     */
    async capturePhoto(options = {}) {
        if (!this.isCapturing || !this.video) {
            throw new Error('카메라가 활성화되지 않았습니다.');
        }

        try {
            // 캔버스 크기 설정
            const videoWidth = this.video.videoWidth;
            const videoHeight = this.video.videoHeight;
            
            this.canvas.width = videoWidth;
            this.canvas.height = videoHeight;

            // 비디오 프레임을 캔버스에 그리기
            this.ctx.drawImage(this.video, 0, 0, videoWidth, videoHeight);

            // 이미지 데이터 추출
            const imageData = this.canvas.toDataURL('image/jpeg', 0.95);
            
            // 메타데이터 수집
            const metadata = await this.collectMetadata();
            
            // 원본 이미지 객체 생성
            const originalImage = {
                dataUrl: imageData,
                blob: await this.dataUrlToBlob(imageData),
                width: videoWidth,
                height: videoHeight,
                size: this.calculateDataUrlSize(imageData),
                capturedAt: new Date().toISOString(),
                metadata: metadata
            };

            // 이미지 압축 및 썸네일 생성
            const processedImages = await this.processImage(originalImage, options);
            
            this.triggerCallback('photoTaken', processedImages);
            
            console.log('[CameraCapture] Photo captured and processed successfully');
            return processedImages;

        } catch (error) {
            console.error('[CameraCapture] Failed to capture photo:', error);
            this.handleError(error);
            throw error;
        }
    }

    /**
     * 이미지 처리 (압축 및 썸네일 생성)
     */
    async processImage(originalImage, options = {}) {
        const config = { ...this.compressionConfig, ...options };
        
        try {
            // 압축된 이미지 생성
            const compressedImage = await this.compressImage(originalImage, config);
            
            // 썸네일 생성
            const thumbnail = await this.generateThumbnail(originalImage, config);
            
            const processedImages = {
                original: originalImage,
                compressed: compressedImage,
                thumbnail: thumbnail,
                compressionRatio: this.calculateCompressionRatio(originalImage.size, compressedImage.size)
            };

            this.triggerCallback('compressionComplete', processedImages);
            
            return processedImages;

        } catch (error) {
            console.error('[CameraCapture] Failed to process image:', error);
            throw error;
        }
    }

    /**
     * 이미지 압축
     */
    async compressImage(originalImage, config) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                // 압축 후 크기 계산
                const scale = Math.min(
                    config.maxWidth / img.width,
                    config.maxHeight / img.height,
                    1
                );
                
                const compressedWidth = Math.floor(img.width * scale);
                const compressedHeight = Math.floor(img.height * scale);
                
                // 압축 캔버스 생성
                const compressCanvas = document.createElement('canvas');
                const compressCtx = compressCanvas.getContext('2d');
                
                compressCanvas.width = compressedWidth;
                compressCanvas.height = compressedHeight;
                
                // 고품질 압축을 위한 설정
                compressCtx.imageSmoothingEnabled = true;
                compressCtx.imageSmoothingQuality = 'high';
                
                // 이미지 그리기
                compressCtx.drawImage(img, 0, 0, compressedWidth, compressedHeight);
                
                // 압축된 이미지 데이터 추출
                const compressedDataUrl = compressCanvas.toDataURL('image/jpeg', config.quality);
                
                resolve({
                    dataUrl: compressedDataUrl,
                    width: compressedWidth,
                    height: compressedHeight,
                    size: this.calculateDataUrlSize(compressedDataUrl),
                    quality: config.quality
                });
            };
            
            img.src = originalImage.dataUrl;
        });
    }

    /**
     * 썸네일 생성
     */
    async generateThumbnail(originalImage, config) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                const thumbnailSize = config.thumbnailSize;
                const aspectRatio = img.width / img.height;
                
                let thumbWidth, thumbHeight;
                
                if (aspectRatio > 1) {
                    // 가로가 더 긴 경우
                    thumbWidth = thumbnailSize;
                    thumbHeight = thumbnailSize / aspectRatio;
                } else {
                    // 세로가 더 긴 경우
                    thumbWidth = thumbnailSize * aspectRatio;
                    thumbHeight = thumbnailSize;
                }
                
                // 썸네일 캔버스 생성
                const thumbCanvas = document.createElement('canvas');
                const thumbCtx = thumbCanvas.getContext('2d');
                
                thumbCanvas.width = thumbWidth;
                thumbCanvas.height = thumbHeight;
                
                // 고품질 썸네일을 위한 설정
                thumbCtx.imageSmoothingEnabled = true;
                thumbCtx.imageSmoothingQuality = 'high';
                
                // 썸네일 그리기
                thumbCtx.drawImage(img, 0, 0, thumbWidth, thumbHeight);
                
                // 썸네일 데이터 추출
                const thumbnailDataUrl = thumbCanvas.toDataURL('image/jpeg', config.thumbnailQuality);
                
                resolve({
                    dataUrl: thumbnailDataUrl,
                    width: thumbWidth,
                    height: thumbHeight,
                    size: this.calculateDataUrlSize(thumbnailDataUrl)
                });
            };
            
            img.src = originalImage.dataUrl;
        });
    }

    /**
     * 카메라 전환 (전면/후면)
     */
    async switchCamera() {
        const newFacingMode = this.facingMode === 'environment' ? 'user' : 'environment';
        this.facingMode = newFacingMode;
        
        if (this.isCapturing && this.video) {
            await this.startCamera(this.video, { facingMode: newFacingMode });
        }
        
        return newFacingMode;
    }

    /**
     * 사용 가능한 카메라 목록 조회
     */
    async getAvailableCameras() {
        try {
            const devices = await navigator.mediaDevices.enumerateDevices();
            const cameras = devices.filter(device => device.kind === 'videoinput');
            
            return cameras.map(camera => ({
                deviceId: camera.deviceId,
                label: camera.label || `Camera ${camera.deviceId.substr(0, 8)}`,
                facingMode: this.guessFacingMode(camera.label)
            }));
            
        } catch (error) {
            console.error('[CameraCapture] Failed to get available cameras:', error);
            return [];
        }
    }

    /**
     * 특정 카메라로 전환
     */
    async switchToCamera(deviceId) {
        if (this.isCapturing && this.video) {
            await this.startCamera(this.video, { deviceId: { exact: deviceId } });
        }
    }

    /**
     * 메타데이터 수집 (위치, 시간 등)
     */
    async collectMetadata() {
        const metadata = {
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            deviceMemory: navigator.deviceMemory,
            hardwareConcurrency: navigator.hardwareConcurrency
        };

        // 위치 정보 추가 (위치 추적기가 활성화된 경우)
        if (window.locationTracker && locationTracker.currentPosition) {
            const coords = locationTracker.currentPosition.coords;
            metadata.location = {
                latitude: coords.latitude,
                longitude: coords.longitude,
                accuracy: coords.accuracy,
                altitude: coords.altitude,
                heading: coords.heading,
                speed: coords.speed
            };
        }

        // 화면 방향 정보
        if (screen.orientation) {
            metadata.orientation = {
                angle: screen.orientation.angle,
                type: screen.orientation.type
            };
        }

        return metadata;
    }

    /**
     * Data URL에서 Blob 변환
     */
    async dataUrlToBlob(dataUrl) {
        return new Promise((resolve) => {
            const arr = dataUrl.split(',');
            const mime = arr[0].match(/:(.*?);/)[1];
            const bstr = atob(arr[1]);
            let n = bstr.length;
            const u8arr = new Uint8Array(n);
            
            while (n--) {
                u8arr[n] = bstr.charCodeAt(n);
            }
            
            resolve(new Blob([u8arr], { type: mime }));
        });
    }

    /**
     * Data URL 크기 계산
     */
    calculateDataUrlSize(dataUrl) {
        const base64 = dataUrl.split(',')[1];
        return Math.round((base64.length * 3) / 4);
    }

    /**
     * 압축률 계산
     */
    calculateCompressionRatio(originalSize, compressedSize) {
        return Math.round((1 - compressedSize / originalSize) * 100);
    }

    /**
     * 카메라 방향 추측
     */
    guessFacingMode(label) {
        const frontKeywords = ['front', 'user', 'selfie', '전면'];
        const backKeywords = ['back', 'rear', 'environment', '후면'];
        
        const lowerLabel = label.toLowerCase();
        
        if (frontKeywords.some(keyword => lowerLabel.includes(keyword))) {
            return 'user';
        } else if (backKeywords.some(keyword => lowerLabel.includes(keyword))) {
            return 'environment';
        }
        
        return 'unknown';
    }

    /**
     * 오류 처리
     */
    handleError(error) {
        let errorMessage = '';
        
        if (error.name === 'NotAllowedError') {
            errorMessage = '카메라 권한이 거부되었습니다.';
        } else if (error.name === 'NotFoundError') {
            errorMessage = '사용 가능한 카메라가 없습니다.';
        } else if (error.name === 'NotReadableError') {
            errorMessage = '카메라를 사용할 수 없습니다.';
        } else if (error.name === 'OverconstrainedError') {
            errorMessage = '요청된 카메라 설정을 지원하지 않습니다.';
        } else {
            errorMessage = '카메라 오류가 발생했습니다.';
        }
        
        console.error('[CameraCapture] Camera error:', errorMessage, error);
        this.triggerCallback('error', { message: errorMessage, originalError: error });
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
                    console.error(`[CameraCapture] Error in ${event} callback:`, error);
                }
            });
        }
    }

    /**
     * 리소스 정리
     */
    cleanup() {
        this.stopCamera();
        this.callbacks = {
            photoTaken: [],
            error: [],
            streamReady: [],
            compressionComplete: []
        };
        
        if (this.canvas) {
            this.canvas = null;
            this.ctx = null;
        }
        
        console.log('[CameraCapture] Resources cleaned up');
    }

    /**
     * 상태 정보 반환
     */
    getStatus() {
        return {
            isCapturing: this.isCapturing,
            isSupported: this.isMediaSupported(),
            facingMode: this.facingMode,
            hasStream: !!this.stream,
            compressionConfig: this.compressionConfig
        };
    }
}

// 전역 인스턴스 생성
const cameraCapture = new CameraCapture();

// 모듈 내보내기
window.CameraCapture = CameraCapture;
window.cameraCapture = cameraCapture;