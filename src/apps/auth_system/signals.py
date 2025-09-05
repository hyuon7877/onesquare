"""
OneSquare 사용자 인증 시스템 - Django Signals

사용자 관련 이벤트 처리:
- 사용자 생성 시 그룹 자동 할당
- 로그인 시 세션 정보 저장
- 사용자 타입 변경 시 그룹 업데이트
"""

from django.db.models.signals import post_save, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import CustomUser, UserSession, UserGroup, UserType
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=CustomUser)
def assign_user_to_group(sender, instance, created, **kwargs):
    """
    사용자 생성 시 user_type에 따라 그룹 자동 할당
    """
    if created or 'user_type' in kwargs.get('update_fields', []):
        try:
            # 기존 그룹에서 제거
            instance.groups.clear()
            
            # user_type에 해당하는 그룹 찾기
            user_group_info = UserGroup.objects.filter(user_type=instance.user_type).first()
            
            if user_group_info:
                # 해당 그룹에 사용자 추가
                instance.groups.add(user_group_info.group)
                logger.info(f"사용자 {instance.username}를 {user_group_info.group.name} 그룹에 추가")
            else:
                logger.warning(f"사용자 타입 {instance.user_type}에 해당하는 그룹을 찾을 수 없습니다.")
        
        except Exception as e:
            logger.error(f"사용자 그룹 할당 중 오류 발생: {e}")


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """
    사용자 로그인 시 세션 정보 저장 및 로그인 IP 업데이트
    """
    try:
        # 클라이언트 IP 주소 가져오기
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        # User Agent 정보
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # 사용자의 마지막 로그인 IP 업데이트
        user.last_login_ip = ip_address
        user.save(update_fields=['last_login_ip'])
        
        # 기존 활성 세션들 비활성화 (중복 로그인 방지)
        UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
        
        # 새 세션 정보 저장
        UserSession.objects.create(
            user=user,
            session_key=request.session.session_key,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True
        )
        
        logger.info(f"사용자 {user.username} 로그인 - IP: {ip_address}")
        
    except Exception as e:
        logger.error(f"로그인 정보 저장 중 오류 발생: {e}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """
    사용자 로그아웃 시 세션 비활성화
    """
    if user and request.session.session_key:
        try:
            # 해당 세션을 비활성화
            UserSession.objects.filter(
                user=user,
                session_key=request.session.session_key,
                is_active=True
            ).update(is_active=False)
            
            logger.info(f"사용자 {user.username} 로그아웃")
            
        except Exception as e:
            logger.error(f"로그아웃 정보 저장 중 오류 발생: {e}")


@receiver(pre_save, sender=CustomUser)
def validate_user_data(sender, instance, **kwargs):
    """
    사용자 데이터 저장 전 유효성 검증
    """
    try:
        # 파트너/도급사는 OTP 인증 필수
        if instance.user_type in [UserType.PARTNER, UserType.CONTRACTOR]:
            if instance.auth_method not in ['otp_sms', 'otp_email']:
                # 기본적으로 SMS OTP로 설정
                instance.auth_method = 'otp_sms'
        
        # OTP 인증을 사용하는 경우 전화번호 또는 이메일 필수
        if instance.auth_method == 'otp_sms' and not instance.phone_number:
            raise ValueError("SMS OTP 인증을 위해서는 전화번호가 필요합니다.")
        
        if instance.auth_method == 'otp_email' and not instance.email:
            raise ValueError("이메일 OTP 인증을 위해서는 이메일이 필요합니다.")
            
    except ValueError as e:
        logger.error(f"사용자 데이터 유효성 검증 실패: {e}")
        raise
    except Exception as e:
        logger.error(f"사용자 데이터 검증 중 오류 발생: {e}")


def create_default_groups():
    """
    기본 사용자 그룹들을 생성하는 유틸리티 함수
    데이터 마이그레이션이나 관리 명령에서 호출
    """
    group_configs = [
        {
            'name': '최고관리자',
            'user_type': UserType.SUPER_ADMIN,
            'description': '시스템 전체 관리 권한',
            'permissions': {
                'can_access_dashboard': True,
                'can_manage_users': True,
                'can_view_reports': True,
                'can_manage_calendar': True,
                'can_access_field_reports': True,
            }
        },
        {
            'name': '중간관리자',
            'user_type': UserType.MANAGER,
            'description': '부서/팀 관리 권한',
            'permissions': {
                'can_access_dashboard': True,
                'can_manage_users': False,
                'can_view_reports': True,
                'can_manage_calendar': True,
                'can_access_field_reports': True,
            }
        },
        {
            'name': '팀원',
            'user_type': UserType.TEAM_MEMBER,
            'description': '기본 직원 권한',
            'permissions': {
                'can_access_dashboard': True,
                'can_manage_users': False,
                'can_view_reports': False,
                'can_manage_calendar': False,
                'can_access_field_reports': False,
            }
        },
        {
            'name': '파트너',
            'user_type': UserType.PARTNER,
            'description': '외부 파트너 권한',
            'permissions': {
                'can_access_dashboard': False,
                'can_manage_users': False,
                'can_view_reports': False,
                'can_manage_calendar': False,
                'can_access_field_reports': True,
            }
        },
        {
            'name': '도급사',
            'user_type': UserType.CONTRACTOR,
            'description': '도급업체 권한',
            'permissions': {
                'can_access_dashboard': False,
                'can_manage_users': False,
                'can_view_reports': False,
                'can_manage_calendar': False,
                'can_access_field_reports': True,
            }
        },
        {
            'name': '커스텀',
            'user_type': UserType.CUSTOM,
            'description': '맞춤 권한 그룹',
            'permissions': {
                'can_access_dashboard': False,
                'can_manage_users': False,
                'can_view_reports': False,
                'can_manage_calendar': False,
                'can_access_field_reports': False,
            }
        },
    ]
    
    created_groups = []
    for config in group_configs:
        # Django Group 생성 또는 가져오기
        group, group_created = Group.objects.get_or_create(
            name=config['name']
        )
        
        # UserGroup 정보 생성 또는 업데이트
        user_group, ug_created = UserGroup.objects.get_or_create(
            group=group,
            defaults={
                'user_type': config['user_type'],
                'description': config['description'],
                **config['permissions']
            }
        )
        
        if not ug_created:
            # 기존 그룹 권한 업데이트
            for key, value in config['permissions'].items():
                setattr(user_group, key, value)
            user_group.description = config['description']
            user_group.save()
        
        created_groups.append(user_group)
        logger.info(f"그룹 {'생성' if ug_created else '업데이트'}: {group.name}")
    
    return created_groups