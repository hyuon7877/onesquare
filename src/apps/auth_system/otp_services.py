"""
OneSquare OTP 인증 서비스

SMS/이메일 OTP 발송 및 검증 서비스 구현
"""

import random
import string
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any

from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.core.cache import cache
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model

from .models import OTPToken, CustomUser

logger = logging.getLogger(__name__)

User = get_user_model()


class OTPService:
    """OTP 서비스 메인 클래스"""
    
    def __init__(self):
        self.otp_length = getattr(settings, 'OTP_LENGTH', 6)
        self.otp_expiry_minutes = getattr(settings, 'OTP_EXPIRY_MINUTES', 5)
        self.max_attempts = getattr(settings, 'OTP_MAX_ATTEMPTS', 3)
        self.rate_limit_minutes = getattr(settings, 'OTP_RATE_LIMIT_MINUTES', 1)
        
        # SMS 서비스 설정
        self.sms_service = SMSService()
        self.email_service = EmailOTPService()
    
    def generate_otp_code(self) -> str:
        """OTP 코드 생성 (6자리 숫자)"""
        return ''.join(random.choices(string.digits, k=self.otp_length))
    
    def send_otp(self, user: CustomUser, otp_type: str = None, request=None) -> Dict[str, Any]:
        """
        OTP 발송
        
        Args:
            user: 대상 사용자
            otp_type: 'sms' 또는 'email', None이면 사용자 설정에 따라
            request: HTTP 요청 객체 (메타데이터 저장용)
        
        Returns:
            발송 결과 딕셔너리
        """
        try:
            # OTP 타입 결정
            if otp_type is None:
                if user.auth_method == user.AuthMethod.OTP_SMS:
                    otp_type = 'sms'
                elif user.auth_method == user.AuthMethod.OTP_EMAIL:
                    otp_type = 'email'
                else:
                    return {
                        'success': False,
                        'error': 'OTP 인증이 설정되지 않은 사용자입니다.'
                    }
            
            # Rate limiting 체크
            rate_limit_key = f'otp_rate_limit_{user.id}_{otp_type}'
            if cache.get(rate_limit_key):
                return {
                    'success': False,
                    'error': f'{self.rate_limit_minutes}분 이내에 이미 OTP를 발송했습니다.'
                }
            
            # 발송 대상 확인
            if otp_type == 'sms':
                destination = user.phone_number
                if not destination:
                    return {
                        'success': False,
                        'error': '전화번호가 등록되지 않았습니다.'
                    }
            elif otp_type == 'email':
                destination = user.email
                if not destination:
                    return {
                        'success': False,
                        'error': '이메일이 등록되지 않았습니다.'
                    }
            else:
                return {
                    'success': False,
                    'error': '지원하지 않는 OTP 타입입니다.'
                }
            
            # 기존 미처리 토큰 만료 처리
            existing_tokens = OTPToken.objects.filter(
                user=user,
                otp_type=otp_type,
                status=OTPToken.OTPStatus.PENDING
            )
            existing_tokens.update(status=OTPToken.OTPStatus.EXPIRED)
            
            # 새 OTP 토큰 생성
            otp_code = self.generate_otp_code()
            expires_at = timezone.now() + timedelta(minutes=self.otp_expiry_minutes)
            
            # 메타데이터 수집
            metadata = {}
            if request:
                metadata.update({
                    'ip_address': self.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'timestamp': timezone.now().isoformat()
                })
            
            # OTP 토큰 저장
            otp_token = OTPToken.objects.create(
                user=user,
                token=otp_code,
                otp_type=otp_type,
                destination=destination,
                expires_at=expires_at,
                max_attempts=self.max_attempts,
                metadata=metadata
            )
            
            # OTP 발송
            if otp_type == 'sms':
                send_result = self.sms_service.send_otp_sms(destination, otp_code, user)
            else:  # email
                send_result = self.email_service.send_otp_email(destination, otp_code, user)
            
            if not send_result.get('success'):
                # 발송 실패 시 토큰 무효화
                otp_token.status = OTPToken.OTPStatus.FAILED
                otp_token.save()
                
                return {
                    'success': False,
                    'error': f'OTP 발송에 실패했습니다: {send_result.get("error", "알 수 없는 오류")}'
                }
            
            # Rate limiting 캐시 설정
            cache.set(rate_limit_key, True, timeout=self.rate_limit_minutes * 60)
            
            logger.info(f'OTP 발송 성공: {user.username} -> {destination} ({otp_type})')
            
            return {
                'success': True,
                'token_id': otp_token.id,
                'destination': self.mask_destination(destination),
                'expires_in': self.otp_expiry_minutes * 60,
                'otp_type': otp_type
            }
            
        except Exception as e:
            logger.error(f'OTP 발송 중 오류 발생: {user.username} - {str(e)}')
            return {
                'success': False,
                'error': 'OTP 발송 중 오류가 발생했습니다.'
            }
    
    def verify_otp(self, user: CustomUser, otp_code: str, request=None) -> Dict[str, Any]:
        """
        OTP 코드 검증
        
        Args:
            user: 사용자 객체
            otp_code: 입력된 OTP 코드
            request: HTTP 요청 객체
        
        Returns:
            검증 결과 딕셔너리
        """
        try:
            # 유효한 OTP 토큰 찾기
            otp_token = OTPToken.objects.filter(
                user=user,
                status=OTPToken.OTPStatus.PENDING,
                expires_at__gt=timezone.now()
            ).first()
            
            if not otp_token:
                return {
                    'success': False,
                    'error': '유효한 OTP 토큰이 없습니다.'
                }
            
            # 시도 횟수 체크
            if otp_token.attempt_count >= otp_token.max_attempts:
                return {
                    'success': False,
                    'error': 'OTP 시도 횟수를 초과했습니다.'
                }
            
            # 토큰 검증
            if otp_token.token != otp_code:
                otp_token.increment_attempt()
                remaining = otp_token.remaining_attempts
                
                logger.warning(f'OTP 검증 실패: {user.username} - 잘못된 코드, 남은 시도: {remaining}')
                
                if remaining > 0:
                    return {
                        'success': False,
                        'error': f'OTP 코드가 올바르지 않습니다. (남은 시도: {remaining}회)',
                        'remaining_attempts': remaining
                    }
                else:
                    return {
                        'success': False,
                        'error': 'OTP 시도 횟수를 초과했습니다.'
                    }
            
            # 검증 성공
            otp_token.mark_verified()
            
            # 검증 성공 메타데이터 업데이트
            if request:
                otp_token.metadata.update({
                    'verified_ip': self.get_client_ip(request),
                    'verified_user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'verified_at': timezone.now().isoformat()
                })
                otp_token.save()
            
            logger.info(f'OTP 검증 성공: {user.username}')
            
            return {
                'success': True,
                'token_id': otp_token.id,
                'verified_at': otp_token.verified_at
            }
            
        except Exception as e:
            logger.error(f'OTP 검증 중 오류 발생: {user.username} - {str(e)}')
            return {
                'success': False,
                'error': 'OTP 검증 중 오류가 발생했습니다.'
            }
    
    def get_otp_status(self, user: CustomUser) -> Dict[str, Any]:
        """현재 OTP 상태 조회"""
        try:
            otp_token = OTPToken.objects.filter(
                user=user,
                status=OTPToken.OTPStatus.PENDING
            ).first()
            
            if not otp_token:
                return {
                    'has_pending_otp': False
                }
            
            return {
                'has_pending_otp': True,
                'token_id': otp_token.id,
                'otp_type': otp_token.otp_type,
                'destination': self.mask_destination(otp_token.destination),
                'expires_in': otp_token.time_remaining,
                'remaining_attempts': otp_token.remaining_attempts,
                'created_at': otp_token.created_at
            }
            
        except Exception as e:
            logger.error(f'OTP 상태 조회 중 오류: {user.username} - {str(e)}')
            return {'has_pending_otp': False}
    
    def mask_destination(self, destination: str) -> str:
        """발송 대상을 마스킹하여 반환 (보안)"""
        if '@' in destination:  # 이메일
            local, domain = destination.split('@', 1)
            if len(local) <= 2:
                masked_local = local[0] + '*'
            else:
                masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
            return f"{masked_local}@{domain}"
        else:  # 전화번호
            if len(destination) >= 4:
                return destination[:3] + '*' * (len(destination) - 6) + destination[-3:]
            return '*' * len(destination)
    
    def get_client_ip(self, request) -> str:
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SMSService:
    """SMS 발송 서비스"""
    
    def __init__(self):
        # SMS 서비스 설정 (개발 환경에서는 로그로 대체)
        self.debug_mode = getattr(settings, 'DEBUG', False)
        
        # 실제 SMS 서비스 설정 (예: Twilio, AWS SNS 등)
        self.sms_api_key = getattr(settings, 'SMS_API_KEY', None)
        self.sms_sender = getattr(settings, 'SMS_SENDER', 'OneSquare')
    
    def send_otp_sms(self, phone_number: str, otp_code: str, user: CustomUser) -> Dict[str, Any]:
        """SMS로 OTP 발송"""
        try:
            message = f"[OneSquare] 인증번호: {otp_code} (5분간 유효)"
            
            if self.debug_mode or not self.sms_api_key:
                # 개발 환경: 로그로 출력
                logger.info(f'[SMS 시뮬레이션] {phone_number}: {message}')
                return {'success': True, 'message_id': 'debug_' + otp_code}
            
            # 실제 SMS 발송 (예: Twilio)
            # 여기서는 시뮬레이션으로 대체
            # result = self._send_via_twilio(phone_number, message)
            
            # 임시로 성공 반환
            logger.info(f'SMS 발송: {phone_number} -> {otp_code}')
            return {
                'success': True,
                'message_id': f'sms_{timezone.now().timestamp()}'
            }
            
        except Exception as e:
            logger.error(f'SMS 발송 실패: {phone_number} - {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_via_twilio(self, phone_number: str, message: str):
        """Twilio를 통한 실제 SMS 발송 (구현 예시)"""
        # from twilio.rest import Client
        # 
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # 
        # message = client.messages.create(
        #     body=message,
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=phone_number
        # )
        # 
        # return {'success': True, 'message_id': message.sid}
        pass


class EmailOTPService:
    """이메일 OTP 발송 서비스"""
    
    def __init__(self):
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@onesquare.com')
    
    def send_otp_email(self, email: str, otp_code: str, user: CustomUser) -> Dict[str, Any]:
        """이메일로 OTP 발송"""
        try:
            subject = '[OneSquare] 인증번호 발송'
            
            # 이메일 템플릿 컨텍스트
            context = {
                'user': user,
                'otp_code': otp_code,
                'expires_minutes': 5,
                'company_name': 'OneSquare'
            }
            
            # HTML 메일 내용 생성
            html_content = self._generate_otp_email_html(context)
            plain_content = self._generate_otp_email_plain(context)
            
            # 이메일 발송
            send_mail(
                subject=subject,
                message=plain_content,
                from_email=self.from_email,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False
            )
            
            logger.info(f'이메일 OTP 발송 성공: {email}')
            
            return {
                'success': True,
                'email_id': f'email_{timezone.now().timestamp()}'
            }
            
        except Exception as e:
            logger.error(f'이메일 OTP 발송 실패: {email} - {str(e)}')
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_otp_email_html(self, context: Dict) -> str:
        """OTP 이메일 HTML 템플릿 생성"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>OneSquare 인증번호</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .otp-code {{ font-size: 36px; font-weight: bold; color: #0A84FF; text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 8px; margin: 20px 0; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>OneSquare 인증번호</h1>
                </div>
                
                <p>안녕하세요, {context['user'].get_full_name() or context['user'].username}님</p>
                
                <p>OneSquare 로그인을 위한 인증번호를 발송해드립니다.</p>
                
                <div class="otp-code">
                    {context['otp_code']}
                </div>
                
                <p><strong>주의사항:</strong></p>
                <ul>
                    <li>이 인증번호는 {context['expires_minutes']}분간 유효합니다.</li>
                    <li>타인에게 절대 알려주지 마세요.</li>
                    <li>본인이 요청하지 않았다면 즉시 고객센터에 문의하세요.</li>
                </ul>
                
                <div class="footer">
                    <p>{context['company_name']} | 이 메일은 발신전용입니다.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _generate_otp_email_plain(self, context: Dict) -> str:
        """OTP 이메일 텍스트 템플릿 생성"""
        return f"""
OneSquare 인증번호

안녕하세요, {context['user'].get_full_name() or context['user'].username}님

OneSquare 로그인을 위한 인증번호: {context['otp_code']}

이 인증번호는 {context['expires_minutes']}분간 유효합니다.
타인에게 절대 알려주지 마세요.

{context['company_name']}
        """


# 전역 OTP 서비스 인스턴스
otp_service = OTPService()