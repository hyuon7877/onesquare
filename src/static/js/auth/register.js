/**
 * OneSquare 회원가입 페이지 JavaScript
 * 
 * 기능:
 * - 회원가입 폼 검증
 * - 비밀번호 강도 확인
 * - 사용자 타입별 필드 표시/숨김
 * - 실시간 유효성 검사
 */

class RegisterManager {
    constructor() {
        this.passwordRequirements = {
            length: false,
            complexity: false
        };
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupCSRF();
    }

    bindEvents() {
        // 폼 제출
        document.getElementById('register-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegistration();
        });

        // 사용자 타입 변경
        document.getElementById('user_type').addEventListener('change', (e) => {
            this.handleUserTypeChange(e.target.value);
        });

        // 비밀번호 강도 체크
        document.getElementById('password').addEventListener('input', (e) => {
            this.checkPasswordStrength(e.target.value);
        });

        // 비밀번호 확인
        document.getElementById('password_confirm').addEventListener('input', (e) => {
            this.checkPasswordMatch();
        });

        // 사용자명 유효성 검사
        document.getElementById('username').addEventListener('blur', (e) => {
            this.validateUsername(e.target.value);
        });

        // 이메일 유효성 검사
        document.getElementById('email').addEventListener('blur', (e) => {
            this.validateEmail(e.target.value);
        });

        // 전화번호 포맷팅
        document.getElementById('phone_number').addEventListener('input', (e) => {
            this.formatPhoneNumber(e.target);
        });

        // 모달 관련
        document.querySelectorAll('.terms-link, .privacy-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const modalId = e.target.classList.contains('terms-link') ? 'terms-modal' : 'privacy-modal';
                this.showModal(modalId);
            });
        });

        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.closeModal(e.target.closest('.modal'));
            });
        });

        // 모달 배경 클릭 시 닫기
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal(modal);
                }
            });
        });
    }

    setupCSRF() {
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

    handleUserTypeChange(userType) {
        const phoneGroup = document.getElementById('phone-group');
        const companyFields = document.querySelector('.company-fields');
        const phoneInput = document.getElementById('phone_number');

        if (userType === 'PARTNER' || userType === 'CONTRACTOR') {
            // 파트너/도급사 - 전화번호와 회사 정보 필수
            phoneGroup.style.display = 'block';
            companyFields.style.display = 'block';
            phoneInput.required = true;
            
            // 회사 정보 필수로 설정
            document.getElementById('company').required = true;
            
        } else {
            // 일반 직원 - 전화번호와 회사 정보 선택사항
            phoneGroup.style.display = 'block';
            companyFields.style.display = 'block';
            phoneInput.required = false;
            document.getElementById('company').required = false;
        }
    }

    checkPasswordStrength(password) {
        const strengthBar = document.querySelector('.strength-fill');
        const strengthText = document.querySelector('.strength-text');
        const strengthContainer = document.querySelector('.password-strength');
        
        // 길이 체크
        this.passwordRequirements.length = password.length >= 8;
        
        // 복잡도 체크 (대소문자, 숫자, 특수문자 중 3종류 이상)
        const hasUpper = /[A-Z]/.test(password);
        const hasLower = /[a-z]/.test(password);
        const hasDigit = /\d/.test(password);
        const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};:,.<>?]/.test(password);
        
        const complexityScore = [hasUpper, hasLower, hasDigit, hasSpecial].filter(Boolean).length;
        this.passwordRequirements.complexity = complexityScore >= 3;
        
        // 전체 강도 계산
        let strength = 0;
        if (this.passwordRequirements.length) strength += 1;
        if (this.passwordRequirements.complexity) strength += 2;
        
        // UI 업데이트
        strengthContainer.className = 'password-strength';
        
        if (strength === 0) {
            strengthContainer.classList.add('strength-weak');
            strengthText.textContent = '매우 약함';
        } else if (strength === 1) {
            strengthContainer.classList.add('strength-weak');
            strengthText.textContent = '약함';
        } else if (strength === 2) {
            strengthContainer.classList.add('strength-medium');
            strengthText.textContent = '보통';
        } else {
            strengthContainer.classList.add('strength-strong');
            strengthText.textContent = '강함';
        }
        
        // 요구사항 체크 표시
        document.getElementById('req-length').classList.toggle('valid', this.passwordRequirements.length);
        document.getElementById('req-complexity').classList.toggle('valid', this.passwordRequirements.complexity);
        
        // 비밀번호 확인 재검사
        this.checkPasswordMatch();
    }

    checkPasswordMatch() {
        const password = document.getElementById('password').value;
        const passwordConfirm = document.getElementById('password_confirm').value;
        const matchDiv = document.querySelector('.password-match');
        
        if (passwordConfirm === '') {
            matchDiv.style.display = 'none';
            return;
        }
        
        matchDiv.style.display = 'block';
        
        if (password === passwordConfirm) {
            matchDiv.className = 'password-match match';
            matchDiv.textContent = '✓ 비밀번호가 일치합니다';
        } else {
            matchDiv.className = 'password-match no-match';
            matchDiv.textContent = '✗ 비밀번호가 일치하지 않습니다';
        }
    }

    async validateUsername(username) {
        if (username.length < 3) {
            this.showFieldError('username', '사용자명은 3자 이상이어야 합니다.');
            return false;
        }
        
        if (!/^[a-zA-Z0-9_]+$/.test(username)) {
            this.showFieldError('username', '영문, 숫자, 밑줄(_)만 사용 가능합니다.');
            return false;
        }
        
        try {
            // 서버에서 중복 검사 (API 구현 필요)
            // const response = await fetch(`/api/auth/check-username/?username=${username}`);
            // const data = await response.json();
            // if (!data.available) {
            //     this.showFieldError('username', '이미 사용 중인 사용자명입니다.');
            //     return false;
            // }
        } catch (error) {
            console.warn('Username validation error:', error);
        }
        
        this.clearFieldError('username');
        return true;
    }

    validateEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            this.showFieldError('email', '유효한 이메일 주소를 입력해주세요.');
            return false;
        }
        
        this.clearFieldError('email');
        return true;
    }

    formatPhoneNumber(input) {
        let value = input.value.replace(/[^0-9]/g, '');
        
        if (value.length >= 11) {
            value = value.replace(/(\d{3})(\d{4})(\d{4})/, '$1-$2-$3');
        } else if (value.length >= 7) {
            value = value.replace(/(\d{3})(\d{3,4})(\d*)/, '$1-$2-$3');
        } else if (value.length >= 3) {
            value = value.replace(/(\d{3})(\d*)/, '$1-$2');
        }
        
        input.value = value;
    }

    async handleRegistration() {
        const form = document.getElementById('register-form');
        const btn = document.getElementById('register-btn');
        
        // 폼 유효성 검사
        if (!this.validateForm()) {
            return;
        }
        
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        this.setButtonLoading(btn, true);
        
        try {
            const response = await fetch('/api/auth/register/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                // 회원가입 성공
                this.showToast('회원가입이 완료되었습니다!', 'success');
                
                if (result.approval_required) {
                    this.showToast('관리자 승인 후 로그인 가능합니다.', 'info');
                }
                
                // 로그인 페이지로 리다이렉트
                setTimeout(() => {
                    window.location.href = '/auth/login/';
                }, 2000);
                
            } else {
                // 회원가입 실패
                this.handleRegistrationErrors(result);
            }

        } catch (error) {
            console.error('Registration error:', error);
            this.showToast('네트워크 오류가 발생했습니다.', 'error');
        }

        this.setButtonLoading(btn, false);
    }

    validateForm() {
        let isValid = true;
        
        // 필수 필드 검사
        const requiredFields = ['username', 'email', 'first_name', 'last_name', 'user_type', 'password', 'password_confirm'];
        
        requiredFields.forEach(fieldName => {
            const field = document.getElementById(fieldName);
            if (!field.value.trim()) {
                this.showFieldError(fieldName, '필수 입력 항목입니다.');
                isValid = false;
            }
        });
        
        // 사용자 타입별 필수 필드
        const userType = document.getElementById('user_type').value;
        if (userType === 'PARTNER' || userType === 'CONTRACTOR') {
            const phoneNumber = document.getElementById('phone_number').value;
            const company = document.getElementById('company').value;
            
            if (!phoneNumber.trim()) {
                this.showFieldError('phone_number', '파트너/도급사는 전화번호가 필수입니다.');
                isValid = false;
            }
            
            if (!company.trim()) {
                this.showFieldError('company', '회사명을 입력해주세요.');
                isValid = false;
            }
        }
        
        // 비밀번호 검사
        if (!this.passwordRequirements.length || !this.passwordRequirements.complexity) {
            this.showToast('비밀번호가 요구사항을 충족하지 않습니다.', 'error');
            isValid = false;
        }
        
        const password = document.getElementById('password').value;
        const passwordConfirm = document.getElementById('password_confirm').value;
        if (password !== passwordConfirm) {
            this.showFieldError('password_confirm', '비밀번호가 일치하지 않습니다.');
            isValid = false;
        }
        
        // 약관 동의 확인
        if (!document.getElementById('agree-terms').checked) {
            this.showToast('이용약관에 동의해주세요.', 'warning');
            isValid = false;
        }
        
        return isValid;
    }

    handleRegistrationErrors(result) {
        if (typeof result === 'object') {
            // 필드별 오류 표시
            for (const [field, errors] of Object.entries(result)) {
                if (Array.isArray(errors)) {
                    this.showFieldError(field, errors[0]);
                } else if (typeof errors === 'string') {
                    this.showFieldError(field, errors);
                }
            }
        } else {
            this.showToast(result.error || '회원가입에 실패했습니다.', 'error');
        }
    }

    showFieldError(fieldName, message) {
        const field = document.getElementById(fieldName);
        if (!field) return;
        
        // 기존 에러 메시지 제거
        this.clearFieldError(fieldName);
        
        // 에러 메시지 추가
        const errorDiv = document.createElement('div');
        errorDiv.className = 'field-error';
        errorDiv.textContent = message;
        errorDiv.style.color = 'var(--error-color)';
        errorDiv.style.fontSize = '12px';
        errorDiv.style.marginTop = '4px';
        
        field.parentNode.appendChild(errorDiv);
        field.style.borderColor = 'var(--error-color)';
    }

    clearFieldError(fieldName) {
        const field = document.getElementById(fieldName);
        if (!field) return;
        
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
        
        field.style.borderColor = 'var(--border-color)';
    }

    showModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'block';
        }
    }

    closeModal(modal) {
        if (modal) {
            modal.style.display = 'none';
        }
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
    new RegisterManager();
});