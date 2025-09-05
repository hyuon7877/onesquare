/**
 * OneSquare - 터치 제스처 관리 모듈
 * 
 * 모바일 터치 인터페이스 최적화 및 제스처 지원
 */

class TouchGestureManager {
    constructor() {
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchEndX = 0;
        this.touchEndY = 0;
        
        this.swipeThreshold = 50; // 스와이프 최소 거리
        this.tapDelay = 300; // 더블탭 감지 시간
        this.longPressDelay = 500; // 롱프레스 감지 시간
        
        this.lastTapTime = 0;
        this.longPressTimer = null;
        
        this.callbacks = {
            swipeLeft: [],
            swipeRight: [],
            swipeUp: [],
            swipeDown: [],
            doubleTap: [],
            longPress: [],
            pinch: []
        };
        
        this.init();
    }

    /**
     * 초기화
     */
    init() {
        console.log('[TouchGesture] Initializing touch gesture manager...');
        
        // 기본 터치 이벤트 등록
        this.setupBasicTouchEvents();
        
        // 핀치 줌 이벤트 등록
        this.setupPinchEvents();
        
        // 터치 피드백 개선
        this.improveTouchFeedback();
        
        console.log('[TouchGesture] Touch gesture manager initialized');
    }

    /**
     * 기본 터치 이벤트 설정
     */
    setupBasicTouchEvents() {
        document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
    }

    /**
     * 터치 시작 핸들러
     */
    handleTouchStart(e) {
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            this.touchStartX = touch.clientX;
            this.touchStartY = touch.clientY;
            
            // 롱프레스 타이머 시작
            this.longPressTimer = setTimeout(() => {
                this.triggerCallback('longPress', {
                    x: this.touchStartX,
                    y: this.touchStartY,
                    target: e.target
                });
            }, this.longPressDelay);
        }
    }

    /**
     * 터치 이동 핸들러
     */
    handleTouchMove(e) {
        // 터치 이동 시 롱프레스 취소
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }
        
        // 스크롤 방향 감지 및 최적화
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            const deltaX = Math.abs(touch.clientX - this.touchStartX);
            const deltaY = Math.abs(touch.clientY - this.touchStartY);
            
            // 수평 스와이프가 더 큰 경우 세로 스크롤 방지
            if (deltaX > deltaY && deltaX > 20) {
                e.preventDefault();
            }
        }
    }

    /**
     * 터치 종료 핸들러
     */
    handleTouchEnd(e) {
        // 롱프레스 타이머 취소
        if (this.longPressTimer) {
            clearTimeout(this.longPressTimer);
            this.longPressTimer = null;
        }
        
        if (e.changedTouches.length === 1) {
            const touch = e.changedTouches[0];
            this.touchEndX = touch.clientX;
            this.touchEndY = touch.clientY;
            
            const deltaX = this.touchEndX - this.touchStartX;
            const deltaY = this.touchEndY - this.touchStartY;
            const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
            
            // 스와이프 감지
            if (distance > this.swipeThreshold) {
                if (Math.abs(deltaX) > Math.abs(deltaY)) {
                    // 수평 스와이프
                    if (deltaX > 0) {
                        this.triggerCallback('swipeRight', { deltaX, deltaY, target: e.target });
                    } else {
                        this.triggerCallback('swipeLeft', { deltaX, deltaY, target: e.target });
                    }
                } else {
                    // 수직 스와이프
                    if (deltaY > 0) {
                        this.triggerCallback('swipeDown', { deltaX, deltaY, target: e.target });
                    } else {
                        this.triggerCallback('swipeUp', { deltaX, deltaY, target: e.target });
                    }
                }
            } else {
                // 탭 감지
                const currentTime = Date.now();
                if (currentTime - this.lastTapTime < this.tapDelay) {
                    // 더블탭
                    this.triggerCallback('doubleTap', {
                        x: this.touchEndX,
                        y: this.touchEndY,
                        target: e.target
                    });
                }
                this.lastTapTime = currentTime;
            }
        }
    }

    /**
     * 핀치 줌 이벤트 설정
     */
    setupPinchEvents() {
        let initialDistance = 0;
        let currentDistance = 0;
        
        document.addEventListener('touchstart', (e) => {
            if (e.touches.length === 2) {
                initialDistance = this.getDistance(e.touches[0], e.touches[1]);
            }
        }, { passive: true });
        
        document.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2) {
                currentDistance = this.getDistance(e.touches[0], e.touches[1]);
                const scale = currentDistance / initialDistance;
                
                this.triggerCallback('pinch', {
                    scale: scale,
                    center: this.getCenter(e.touches[0], e.touches[1]),
                    target: e.target
                });
            }
        }, { passive: true });
    }

    /**
     * 두 터치 포인트 간 거리 계산
     */
    getDistance(touch1, touch2) {
        const dx = touch1.clientX - touch2.clientX;
        const dy = touch1.clientY - touch2.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    /**
     * 두 터치 포인트의 중심점 계산
     */
    getCenter(touch1, touch2) {
        return {
            x: (touch1.clientX + touch2.clientX) / 2,
            y: (touch1.clientY + touch2.clientY) / 2
        };
    }

    /**
     * 터치 피드백 개선
     */
    improveTouchFeedback() {
        // 버튼 터치 피드백 강화
        document.querySelectorAll('button, .btn, [role="button"]').forEach(button => {
            button.addEventListener('touchstart', () => {
                button.style.transform = 'scale(0.98)';
                button.style.transition = 'transform 0.1s ease';
            }, { passive: true });
            
            button.addEventListener('touchend', () => {
                setTimeout(() => {
                    button.style.transform = '';
                }, 100);
            }, { passive: true });
        });

        // 카드 터치 피드백
        document.querySelectorAll('.card, .list-group-item').forEach(card => {
            card.addEventListener('touchstart', () => {
                card.style.backgroundColor = 'var(--bs-gray-100)';
                card.style.transition = 'background-color 0.1s ease';
            }, { passive: true });
            
            card.addEventListener('touchend', () => {
                setTimeout(() => {
                    card.style.backgroundColor = '';
                }, 150);
            }, { passive: true });
        });

        // 입력 필드 포커스 개선
        document.querySelectorAll('input, textarea, select').forEach(input => {
            input.addEventListener('touchstart', () => {
                // iOS에서 줌 방지
                input.style.fontSize = '16px';
            }, { passive: true });
        });
    }

    /**
     * 제스처 콜백 등록
     */
    on(gesture, callback) {
        if (this.callbacks[gesture]) {
            this.callbacks[gesture].push(callback);
        }
    }

    /**
     * 제스처 콜백 제거
     */
    off(gesture, callback) {
        if (this.callbacks[gesture]) {
            const index = this.callbacks[gesture].indexOf(callback);
            if (index > -1) {
                this.callbacks[gesture].splice(index, 1);
            }
        }
    }

    /**
     * 콜백 실행
     */
    triggerCallback(gesture, data) {
        if (this.callbacks[gesture]) {
            this.callbacks[gesture].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[TouchGesture] Error in ${gesture} callback:`, error);
                }
            });
        }
    }

    /**
     * 햅틱 피드백 (지원되는 경우)
     */
    hapticFeedback(type = 'light') {
        if (navigator.vibrate) {
            switch (type) {
                case 'light':
                    navigator.vibrate(10);
                    break;
                case 'medium':
                    navigator.vibrate(20);
                    break;
                case 'heavy':
                    navigator.vibrate(50);
                    break;
                case 'success':
                    navigator.vibrate([10, 10, 10]);
                    break;
                case 'error':
                    navigator.vibrate([50, 50, 50]);
                    break;
            }
        }
    }

    /**
     * 가상 키보드 대응
     */
    handleVirtualKeyboard() {
        const viewport = document.querySelector('meta[name="viewport"]');
        
        document.addEventListener('focusin', (e) => {
            if (e.target.matches('input, textarea')) {
                // 키보드가 나타날 때 뷰포트 조정
                setTimeout(() => {
                    if (viewport) {
                        viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, user-scalable=no, viewport-fit=cover');
                    }
                    
                    // 입력 필드를 보이는 영역으로 스크롤
                    e.target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'center'
                    });
                }, 300);
            }
        });
        
        document.addEventListener('focusout', () => {
            // 키보드가 사라질 때 뷰포트 복원
            setTimeout(() => {
                if (viewport) {
                    viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, user-scalable=no');
                }
            }, 300);
        });
    }
}

// 전역 인스턴스 생성
const touchGestureManager = new TouchGestureManager();

// 모듈 내보내기
window.TouchGestureManager = TouchGestureManager;
window.touchGestureManager = touchGestureManager;