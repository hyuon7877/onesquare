/**
 * OneSquare 로그인 페이지 JavaScript
 * 
 * 기능:
 * - 이메일/비밀번호 로그인
 * - OTP 인증 (SMS/이메일)
 * - 폼 검증 및 사용자 피드백
 */

class LoginManager {
    constructor() {
        this.init();
        this.otpTimer = null;
        this.otpTimeLeft = 300; // 5분
    }

    init() {
        this.bindEvents();
        this.loadSavedCredentials();
        this.setupCSRF();
    }

    bindEvents() {
        // 탭 전환
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // 이메일 로그인
        document.getElementById('email-login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleEmailLogin();
        });

        // OTP 요청
        document.getElementById('request-otp-btn').addEventListener('click', () => {
            this.handleOTPRequest();
        });

        // OTP 검증
        document.getElementById('otp-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleOTPVerification();
        });

        // OTP 재전송
        document.getElementById('resend-otp-btn').addEventListener('click', () => {
            this.handleOTPRequest(true);
        });

        // OTP 코드 입력 시 자동 포맷팅
        document.getElementById('otp-code').addEventListener('input', (e) => {
            e.target.value = e.target.value.replace(/[^0-9]/g, '');
        });
    }

    setupCSRF() {
        // CSRF 토큰 설정
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || 
                         this.getCookie('csrftoken');
        
        this.csrfToken = csrfToken;
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    switchTab(tabName) {
        // 탭 버튼 활성화
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // 폼 표시/숨김
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.remove('active');
        });
        document.getElementById(`${tabName === 'email' ? 'email-login' : 'otp'}-form`).classList.add('active');

        // OTP 폼 초기화
        if (tabName === 'otp') {
            this.resetOTPForm();
        }
    }

    loadSavedCredentials() {
        const savedEmail = localStorage.getItem('savedEmail');
        if (savedEmail) {
            document.getElementById('email').value = savedEmail;
            document.getElementById('remember-me').checked = true;
        }
    }

    async handleEmailLogin() {
        const form = document.getElementById('email-login-form');
        const btn = document.getElementById('email-login-btn');
        const formData = new FormData(form);

        // 버튼 로딩 상태
        this.setButtonLoading(btn, true);

        try {
            const response = await fetch('/api/auth/login/email/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email: formData.get('email'),
                    password: formData.get('password')
                })
            });

            const data = await response.json();

            if (response.ok) {
                // 로그인 성공
                this.showToast('로그인 성공!', 'success');

                // 이메일 저장 (기억하기 체크된 경우)
                if (document.getElementById('remember-me').checked) {
                    localStorage.setItem('savedEmail', formData.get('email'));
                } else {
                    localStorage.removeItem('savedEmail');
                }

                // 토큰 저장
                localStorage.setItem('authToken', data.token);
                localStorage.setItem('userInfo', JSON.stringify(data.user));

                // 리다이렉트
                setTimeout(() => {
                    window.location.href = data.redirect_url || '/dashboard/';
                }, 1000);

            } else if (data.otp_required) {
                // OTP 인증 필요
                this.showToast('OTP 인증이 필요합니다.', 'info');
                this.switchTab('otp');
                document.getElementById('otp-username').value = data.username;
                
            } else {
                // 로그인 실패
                this.showToast(data.error || '로그인에 실패했습니다.', 'error');
            }

        } catch (error) {
            console.error('Login error:', error);
            this.showToast('네트워크 오류가 발생했습니다.', 'error');
        }

        this.setButtonLoading(btn, false);
    }

    async handleOTPRequest(isResend = false) {
        const username = document.getElementById('otp-username').value;
        const deliveryMethod = document.querySelector('input[name="delivery_method"]:checked').value;
        const btn = document.getElementById('request-otp-btn');

        if (!username.trim()) {
            this.showToast('사용자명을 입력해주세요.', 'warning');
            return;
        }

        this.setButtonLoading(btn, true);

        try {
            const response = await fetch('/api/auth/otp/request/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    delivery_method: deliveryMethod
                })
            });

            const data = await response.json();

            if (response.ok) {
                // OTP 요청 성공
                this.showToast(data.message, 'success');
                this.showOTPVerifyStep(deliveryMethod, data.delivery_target || username);
                this.startOTPTimer();

            } else {
                this.showToast(data.error || 'OTP 요청에 실패했습니다.', 'error');
            }

        } catch (error) {
            console.error('OTP request error:', error);
            this.showToast('네트워크 오류가 발생했습니다.', 'error');
        }

        this.setButtonLoading(btn, false);
    }

    async handleOTPVerification() {
        const username = document.getElementById('otp-username').value;
        const otpCode = document.getElementById('otp-code').value;
        const deliveryMethod = document.querySelector('input[name="delivery_method"]:checked').value;
        const btn = document.getElementById('verify-otp-btn');

        if (!otpCode || otpCode.length !== 6) {
            this.showToast('6자리 인증코드를 입력해주세요.', 'warning');
            return;
        }

        this.setButtonLoading(btn, true);

        try {
            const response = await fetch('/api/auth/otp/verify/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    otp_code: otpCode,
                    delivery_method: deliveryMethod
                })
            });

            const data = await response.json();

            if (response.ok) {
                // 인증 성공
                this.showToast('인증 성공!', 'success');
                
                // 토큰 저장
                localStorage.setItem('authToken', data.token);
                localStorage.setItem('userInfo', JSON.stringify(data.user));

                // 타이머 중지
                this.stopOTPTimer();

                // 리다이렉트
                setTimeout(() => {
                    window.location.href = '/dashboard/';
                }, 1000);

            } else {
                this.showToast(data.error || '인증에 실패했습니다.', 'error');
            }

        } catch (error) {
            console.error('OTP verification error:', error);
            this.showToast('네트워크 오류가 발생했습니다.', 'error');
        }

        this.setButtonLoading(btn, false);
    }

    showOTPVerifyStep(deliveryMethod, target) {
        document.getElementById('otp-request-step').style.display = 'none';
        document.getElementById('otp-verify-step').style.display = 'block';
        
        const methodText = deliveryMethod === 'sms' ? 'SMS' : '이메일';
        document.getElementById('otp-target').textContent = `${target} (${methodText})`;
        
        // 코드 입력 필드에 포커스
        document.getElementById('otp-code').focus();
    }

    startOTPTimer() {
        this.otpTimeLeft = 300; // 5분
        this.updateTimerDisplay();

        this.otpTimer = setInterval(() => {
            this.otpTimeLeft--;
            this.updateTimerDisplay();

            if (this.otpTimeLeft <= 0) {
                this.stopOTPTimer();
                this.showToast('인증코드가 만료되었습니다. 다시 요청해주세요.', 'warning');
            }
        }, 1000);
    }

    stopOTPTimer() {
        if (this.otpTimer) {
            clearInterval(this.otpTimer);
            this.otpTimer = null;
        }
    }

    updateTimerDisplay() {
        const minutes = Math.floor(this.otpTimeLeft / 60);
        const seconds = this.otpTimeLeft % 60;
        const timerText = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        document.getElementById('timer-countdown').textContent = timerText;

        // 30초 이하일 때 색상 변경
        if (this.otpTimeLeft <= 30) {
            document.getElementById('timer-countdown').style.color = 'var(--error-color)';
        } else {
            document.getElementById('timer-countdown').style.color = 'var(--warning-color)';
        }
    }

    resetOTPForm() {
        document.getElementById('otp-request-step').style.display = 'block';
        document.getElementById('otp-verify-step').style.display = 'none';
        document.getElementById('otp-code').value = '';
        this.stopOTPTimer();
    }

    setButtonLoading(button, isLoading) {
        if (isLoading) {
            button.classList.add('loading');
            button.disabled = true;
        } else {
            button.classList.remove('loading');
            button.disabled = false;
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        // 자동 제거
        setTimeout(() => {
            toast.remove();
        }, 5000);

        // 클릭으로 제거
        toast.addEventListener('click', () => {
            toast.remove();
        });
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    new LoginManager();
});