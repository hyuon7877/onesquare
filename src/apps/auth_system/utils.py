"""
OneSquare 사용자 인증 시스템 - 유틸리티 함수들

OTP 생성, 전송, 검증 및 사용자 권한 체크 등의 유틸리티 함수
"""

import random
import string
import hashlib
import hmac
from datetime import datetime, timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth.models import Group
from .models import CustomUser, OTPCode, UserSession, UserType
import logging

logger = logging.getLogger(__name__)


class OTPGenerator:
    """OTP 코드 생성 및 관리 클래스"""
    
    @staticmethod
    def generate_code(length=6):
        """6자리 OTP 코드 생성"""
        return ''.join(random.choices(string.digits, k=length))
    
    @staticmethod
    def create_otp_for_user(user, delivery_method='sms', delivery_target=None):
        """
        사용자를 위한 OTP 코드 생성 및 저장
        
        Args:
            user: CustomUser 객체
            delivery_method: 'sms' 또는 'email'
            delivery_target: 전송 대상 (전화번호 또는 이메일)
        
        Returns:
            OTPCode 객체 또는 None
        """
        try:
            # 기존 미사용 OTP 코드들 만료 처리
            OTPCode.objects.filter(
                user=user,
                is_used=False,
                delivery_method=delivery_method
            ).update(is_used=True)
            
            # 전송 대상 설정
            if not delivery_target:
                if delivery_method == 'sms':
                    delivery_target = user.phone_number
                elif delivery_method == 'email':
                    delivery_target = user.email
                else:
                    raise ValueError("유효하지 않은 전송 방법입니다.")
            
            if not delivery_target:
                raise ValueError(f"{delivery_method} 전송을 위한 정보가 없습니다.")
            
            # 새 OTP 코드 생성
            code = OTPGenerator.generate_code()
            
            otp_code = OTPCode.objects.create(
                user=user,
                code=code,
                delivery_method=delivery_method,
                delivery_target=delivery_target
            )
            
            logger.info(f"OTP 코드 생성됨 - 사용자: {user.username}, 방법: {delivery_method}")
            return otp_code
            
        except Exception as e:
            logger.error(f"OTP 코드 생성 실패: {e}")
            return None
    
    @staticmethod
    def verify_otp(user, code, delivery_method='sms'):
        """
        OTP 코드 검증
        
        Args:
            user: CustomUser 객체
            code: 입력받은 OTP 코드
            delivery_method: 'sms' 또는 'email'
        
        Returns:
            bool: 검증 성공 여부
        """
        try:
            otp_code = OTPCode.objects.filter(
                user=user,
                code=code,
                delivery_method=delivery_method,
                is_used=False
            ).first()
            
            if not otp_code:
                logger.warning(f"OTP 코드를 찾을 수 없음 - 사용자: {user.username}")
                return False
            
            if otp_code.is_expired:
                logger.warning(f"만료된 OTP 코드 - 사용자: {user.username}")
                return False
            
            # 검증 성공 - 사용됨으로 표시
            otp_code.mark_as_used()
            logger.info(f"OTP 검증 성공 - 사용자: {user.username}")
            return True
            
        except Exception as e:
            logger.error(f"OTP 검증 실패: {e}")
            return False


class SMSService:
    """SMS 발송 서비스 (추후 실제 SMS API 연동)"""
    
    @staticmethod
    def send_otp_sms(phone_number, code):
        """
        OTP SMS 발송
        
        Args:
            phone_number: 전화번호
            code: OTP 코드
        
        Returns:
            bool: 발송 성공 여부
        """
        try:
            # 개발 환경에서는 로그로 출력
            if settings.DEBUG:
                logger.info(f"📱 SMS 발송 (개발모드): {phone_number} - 인증코드: {code}")
                print(f"📱 SMS 발송 - {phone_number}: OneSquare 인증코드는 {code} 입니다.")
                return True
            
            # 실제 환경에서는 SMS API 연동
            # 예: AWS SNS, Twilio, 알리고 등
            # 여기에 실제 SMS 발송 로직 구현
            
            logger.info(f"SMS 발송 완료: {phone_number}")
            return True
            
        except Exception as e:
            logger.error(f"SMS 발송 실패: {e}")
            return False


class EmailService:
    """이메일 발송 서비스"""
    
    @staticmethod
    def send_otp_email(email, code, user_name=None):
        """
        OTP 이메일 발송
        
        Args:
            email: 이메일 주소
            code: OTP 코드
            user_name: 사용자 이름
        
        Returns:
            bool: 발송 성공 여부
        """
        try:
            subject = 'OneSquare 인증코드'
            
            # 개발 환경에서는 간단한 메시지
            if settings.DEBUG:
                message = f"""
                안녕하세요{', ' + user_name if user_name else ''}!
                
                OneSquare 로그인을 위한 인증코드는 다음과 같습니다:
                
                인증코드: {code}
                
                이 코드는 5분 후에 만료됩니다.
                
                OneSquare 팀 드림
                """
                
                send_mail(
                    subject=subject,
                    message=message.strip(),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                
                logger.info(f"OTP 이메일 발송 완료: {email}")
                return True
            
            # 실제 환경에서는 HTML 템플릿 사용
            html_message = render_to_string('auth_system/otp_email.html', {
                'user_name': user_name,
                'otp_code': code,
                'expires_in': 5,  # 5분
            })
            
            send_mail(
                subject=subject,
                message='',
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            logger.info(f"OTP 이메일 발송 완료: {email}")
            return True
            
        except Exception as e:
            logger.error(f"OTP 이메일 발송 실패: {e}")
            return False


class UserPermissionChecker:
    """사용자 권한 체크 유틸리티"""
    
    @staticmethod
    def has_dashboard_access(user):
        """대시보드 접근 권한 확인"""
        if not user.is_authenticated:
            return False
        
        try:
            user_group = user.groups.first()
            if user_group:
                user_group_info = user_group.usergroup
                return user_group_info.can_access_dashboard
        except:
            pass
        
        return user.is_staff or user.is_superuser
    
    @staticmethod
    def can_manage_users(user):
        """사용자 관리 권한 확인"""
        if not user.is_authenticated:
            return False
        
        try:
            user_group = user.groups.first()
            if user_group:
                user_group_info = user_group.usergroup
                return user_group_info.can_manage_users
        except:
            pass
        
        return user.is_superuser
    
    @staticmethod
    def can_view_reports(user):
        """리포트 조회 권한 확인"""
        if not user.is_authenticated:
            return False
        
        try:
            user_group = user.groups.first()
            if user_group:
                user_group_info = user_group.usergroup
                return user_group_info.can_view_reports
        except:
            pass
        
        return user.is_staff or user.is_superuser
    
    @staticmethod
    def can_access_field_reports(user):
        """현장 리포트 접근 권한 확인"""
        if not user.is_authenticated:
            return False
        
        try:
            user_group = user.groups.first()
            if user_group:
                user_group_info = user_group.usergroup
                return user_group_info.can_access_field_reports
        except:
            pass
        
        # 파트너, 도급사는 기본적으로 현장 리포트 접근 가능
        return user.is_partner or user.is_contractor or user.is_staff


class SessionManager:
    """사용자 세션 관리 유틸리티"""
    
    @staticmethod
    def cleanup_expired_sessions():
        """만료된 세션들 정리"""
        try:
            # 2시간 이상 비활성 세션들을 비활성화
            cutoff_time = timezone.now() - timedelta(hours=2)
            
            expired_count = UserSession.objects.filter(
                last_activity__lt=cutoff_time,
                is_active=True
            ).update(is_active=False)
            
            logger.info(f"만료된 세션 {expired_count}개 정리 완료")
            return expired_count
            
        except Exception as e:
            logger.error(f"세션 정리 실패: {e}")
            return 0
    
    @staticmethod
    def get_active_sessions_for_user(user):
        """사용자의 활성 세션 목록 조회"""
        try:
            return UserSession.objects.filter(
                user=user,
                is_active=True
            ).exclude(
                last_activity__lt=timezone.now() - timedelta(hours=2)
            )
        except Exception as e:
            logger.error(f"활성 세션 조회 실패: {e}")
            return UserSession.objects.none()
    
    @staticmethod
    def terminate_user_sessions(user, except_session_key=None):
        """사용자의 모든 세션 종료 (특정 세션 제외)"""
        try:
            sessions = UserSession.objects.filter(user=user, is_active=True)
            
            if except_session_key:
                sessions = sessions.exclude(session_key=except_session_key)
            
            terminated_count = sessions.update(is_active=False)
            logger.info(f"사용자 {user.username}의 {terminated_count}개 세션 종료")
            return terminated_count
            
        except Exception as e:
            logger.error(f"세션 종료 실패: {e}")
            return 0


def get_user_type_display_name(user_type):
    """사용자 타입의 한국어 표시명 반환"""
    type_mapping = {
        UserType.SUPER_ADMIN: '최고관리자',
        UserType.MANAGER: '중간관리자',
        UserType.TEAM_MEMBER: '팀원',
        UserType.PARTNER: '파트너',
        UserType.CONTRACTOR: '도급사',
        UserType.CUSTOM: '커스텀',
    }
    return type_mapping.get(user_type, user_type)


def is_strong_password(password):
    """
    강한 패스워드인지 확인
    
    조건:
    - 최소 8자리
    - 영문 대소문자, 숫자, 특수문자 중 3종류 이상
    """
    if len(password) < 8:
        return False, "비밀번호는 최소 8자리 이상이어야 합니다."
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    score = sum([has_upper, has_lower, has_digit, has_special])
    
    if score < 3:
        return False, "영문 대소문자, 숫자, 특수문자 중 3종류 이상을 포함해야 합니다."
    
    return True, "사용 가능한 비밀번호입니다."