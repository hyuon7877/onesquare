"""
OneSquare 사용자 인증 시스템 - 모델 정의

6개 사용자 그룹별 인증 시스템:
- 최고관리자 (Super Admin)
- 중간관리자 (Manager) 
- 팀원 (Team Member)
- 파트너 (Partner)
- 도급사 (Contractor)
- 커스텀 (Custom)
"""

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta
from .permissions import PermissionManager, SystemModule, PermissionLevel


class UserType(models.TextChoices):
    """사용자 타입 선택지"""
    SUPER_ADMIN = 'super_admin', '최고관리자'
    MANAGER = 'manager', '중간관리자'
    TEAM_MEMBER = 'team_member', '팀원'
    PARTNER = 'partner', '파트너'
    CONTRACTOR = 'contractor', '도급사'
    CUSTOM = 'custom', '커스텀'


class AuthMethod(models.TextChoices):
    """인증 방식 선택지"""
    EMAIL_PASSWORD = 'email_password', '이메일+비밀번호'
    OTP_SMS = 'otp_sms', 'SMS OTP'
    OTP_EMAIL = 'otp_email', '이메일 OTP'


class CustomUser(AbstractUser):
    """
    OneSquare 커스텀 사용자 모델
    Django AbstractUser를 확장하여 필요한 필드 추가
    """
    
    # 사용자 타입 (6개 그룹)
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.TEAM_MEMBER,
        verbose_name='사용자 타입'
    )
    
    # 인증 방식
    auth_method = models.CharField(
        max_length=20,
        choices=AuthMethod.choices,
        default=AuthMethod.EMAIL_PASSWORD,
        verbose_name='인증 방식'
    )
    
    # 전화번호 (OTP 인증용)
    phone_regex = RegexValidator(
        regex=r'^01[0-9]-?\d{3,4}-?\d{4}$',
        message="전화번호 형식: 010-1234-5678 또는 01012345678"
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=15,
        blank=True,
        null=True,
        verbose_name='전화번호'
    )
    
    # 프로필 이미지
    profile_image = models.ImageField(
        upload_to='profiles/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='프로필 이미지'
    )
    
    # 회사/소속
    company = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='회사/소속'
    )
    
    # 부서
    department = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='부서'
    )
    
    # 직책
    position = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='직책'
    )
    
    # 계정 활성화 여부 (관리자가 수동으로 활성화)
    is_approved = models.BooleanField(
        default=False,
        verbose_name='계정 승인 여부'
    )
    
    # 마지막 로그인 IP
    last_login_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name='마지막 로그인 IP'
    )
    
    # 생성일/수정일
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자들'
        db_table = 'auth_custom_user'
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    @property
    def is_partner(self):
        """파트너 사용자인지 확인"""
        return self.user_type == UserType.PARTNER
    
    @property
    def is_contractor(self):
        """도급사 사용자인지 확인"""
        return self.user_type == UserType.CONTRACTOR
    
    @property
    def is_admin_level(self):
        """관리자급 사용자인지 확인"""
        return self.user_type in [UserType.SUPER_ADMIN, UserType.MANAGER]
    
    @property
    def requires_otp(self):
        """OTP 인증이 필요한 사용자인지 확인"""
        return self.auth_method in [AuthMethod.OTP_SMS, AuthMethod.OTP_EMAIL]

    def get_otp_destination(self):
        """OTP 발송 대상 반환 (전화번호 또는 이메일)"""
        if self.auth_method == AuthMethod.OTP_SMS:
            return self.phone_number
        elif self.auth_method == AuthMethod.OTP_EMAIL:
            return self.email
        return None

    # 권한 관련 메서드
    def has_system_permission(self, module, level=PermissionLevel.READ_ONLY):
        """시스템 모듈 권한 확인"""
        return PermissionManager.has_module_permission(self, module, level)
    
    def has_custom_permission(self, permission_code):
        """커스텀 권한 코드 확인"""
        return PermissionManager.has_permission(self, permission_code)
    
    def get_filtered_queryset(self, queryset, permission_code):
        """권한에 따른 쿼리셋 필터링"""
        return PermissionManager.filter_queryset_by_permission(self, queryset, permission_code)
    
    def assign_user_type_permissions(self):
        """사용자 타입에 따른 권한 그룹 할당"""
        from .management.commands.setup_permissions import setup_user_permissions
        setup_user_permissions(self)
    
    def get_accessible_modules(self):
        """접근 가능한 시스템 모듈 목록 반환"""
        accessible_modules = []
        for module in SystemModule:
            if self.has_system_permission(module):
                accessible_modules.append(module)
        return accessible_modules
    
    def get_permission_summary(self):
        """사용자 권한 요약 정보"""
        summary = {
            'user_type': self.user_type,
            'user_type_display': self.get_user_type_display(),
            'is_admin_level': self.is_admin_level,
            'accessible_modules': [module.value for module in self.get_accessible_modules()],
            'is_approved': self.is_approved,
            'requires_otp': self.requires_otp
        }
        return summary


class OTPToken(models.Model):
    """
    OTP 토큰 관리 모델
    SMS/이메일 OTP 인증을 위한 임시 토큰 저장
    """
    
    class OTPType(models.TextChoices):
        SMS = 'sms', 'SMS'
        EMAIL = 'email', '이메일'
    
    class OTPStatus(models.TextChoices):
        PENDING = 'pending', '대기 중'
        VERIFIED = 'verified', '인증 완료'
        EXPIRED = 'expired', '만료됨'
        FAILED = 'failed', '실패'
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='otp_tokens',
        verbose_name='사용자'
    )
    
    token = models.CharField(
        max_length=6,
        verbose_name='OTP 토큰'
    )
    
    otp_type = models.CharField(
        max_length=10,
        choices=OTPType.choices,
        verbose_name='OTP 타입'
    )
    
    destination = models.CharField(
        max_length=100,
        verbose_name='발송 대상',
        help_text='전화번호 또는 이메일 주소'
    )
    
    status = models.CharField(
        max_length=10,
        choices=OTPStatus.choices,
        default=OTPStatus.PENDING,
        verbose_name='상태'
    )
    
    # 시도 횟수 (무차별 대입 방지)
    attempt_count = models.IntegerField(
        default=0,
        verbose_name='시도 횟수'
    )
    
    # 최대 시도 횟수
    max_attempts = models.IntegerField(
        default=3,
        verbose_name='최대 시도 횟수'
    )
    
    # 만료 시간
    expires_at = models.DateTimeField(
        verbose_name='만료 시간'
    )
    
    # 인증 완료 시간
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='인증 완료 시간'
    )
    
    # 생성일/수정일
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    # 추가 메타데이터 (IP, User-Agent 등)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='메타데이터'
    )
    
    class Meta:
        verbose_name = 'OTP 토큰'
        verbose_name_plural = 'OTP 토큰들'
        db_table = 'auth_otp_token'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['token', 'expires_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_otp_type_display()} OTP"
    
    @property
    def is_expired(self):
        """만료 여부 확인"""
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """유효한 토큰인지 확인"""
        return (
            self.status == self.OTPStatus.PENDING 
            and not self.is_expired 
            and self.attempt_count < self.max_attempts
        )
    
    @property
    def is_verified(self):
        """인증 완료 여부"""
        return self.status == self.OTPStatus.VERIFIED
    
    @property
    def remaining_attempts(self):
        """남은 시도 횟수"""
        return max(0, self.max_attempts - self.attempt_count)
    
    @property
    def time_remaining(self):
        """남은 시간 (초)"""
        if self.is_expired:
            return 0
        return max(0, int((self.expires_at - timezone.now()).total_seconds()))
    
    def increment_attempt(self):
        """시도 횟수 증가"""
        self.attempt_count += 1
        if self.attempt_count >= self.max_attempts:
            self.status = self.OTPStatus.FAILED
        self.save(update_fields=['attempt_count', 'status', 'updated_at'])
    
    def mark_verified(self):
        """인증 완료로 표시"""
        self.status = self.OTPStatus.VERIFIED
        self.verified_at = timezone.now()
        self.save(update_fields=['status', 'verified_at', 'updated_at'])
    
    def mark_expired(self):
        """만료로 표시"""
        self.status = self.OTPStatus.EXPIRED
        self.save(update_fields=['status', 'updated_at'])
    
    @classmethod
    def cleanup_expired_tokens(cls):
        """만료된 토큰 정리 (관리 명령어에서 사용)"""
        expired_tokens = cls.objects.filter(
            expires_at__lt=timezone.now(),
            status=cls.OTPStatus.PENDING
        )
        count = expired_tokens.count()
        expired_tokens.update(status=cls.OTPStatus.EXPIRED)
        return count


class UserSession(models.Model):
    """
    사용자 세션 관리 모델
    중복 로그인 방지 및 세션 추적용
    """
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='user_sessions',
        verbose_name='사용자'
    )
    
    session_key = models.CharField(
        max_length=40,
        unique=True,
        verbose_name='세션 키'
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name='IP 주소'
    )
    
    user_agent = models.TextField(
        verbose_name='User Agent'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 상태'
    )
    
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name='마지막 활동'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    
    class Meta:
        verbose_name = '사용자 세션'
        verbose_name_plural = '사용자 세션들'
        db_table = 'auth_user_session'
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"
    
    @classmethod
    def cleanup_inactive_sessions(cls, inactive_hours=24):
        """비활성 세션 정리"""
        cutoff_time = timezone.now() - timedelta(hours=inactive_hours)
        inactive_sessions = cls.objects.filter(
            last_activity__lt=cutoff_time
        )
        count = inactive_sessions.count()
        inactive_sessions.delete()
        return count


class OTPCode(models.Model):
    """
    OTP 인증 코드 관리
    파트너 및 도급사용 SMS/이메일 OTP 코드 저장
    """
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='사용자'
    )
    
    code = models.CharField(
        max_length=6,
        verbose_name='OTP 코드'
    )
    
    # OTP 전송 방법
    delivery_method = models.CharField(
        max_length=10,
        choices=[('sms', 'SMS'), ('email', '이메일')],
        verbose_name='전송 방법'
    )
    
    # 전송 대상 (전화번호 또는 이메일)
    delivery_target = models.CharField(
        max_length=100,
        verbose_name='전송 대상'
    )
    
    # 생성 시간
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')
    
    # 사용 여부
    is_used = models.BooleanField(default=False, verbose_name='사용 여부')
    
    # 사용 시간
    used_at = models.DateTimeField(blank=True, null=True, verbose_name='사용 시간')
    
    class Meta:
        verbose_name = 'OTP 코드'
        verbose_name_plural = 'OTP 코드들'
        db_table = 'auth_otp_code'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.code} ({self.delivery_method})"
    
    @property
    def is_expired(self):
        """OTP 코드가 만료되었는지 확인 (5분 만료)"""
        return timezone.now() > self.created_at + timedelta(minutes=5)
    
    @property
    def is_valid(self):
        """OTP 코드가 유효한지 확인"""
        return not self.is_used and not self.is_expired
    
    def mark_as_used(self):
        """OTP 코드를 사용됨으로 표시"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])


class UserSession(models.Model):
    """
    사용자 세션 관리
    중복 로그인 방지 및 세션 추적용
    """
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='사용자'
    )
    
    session_key = models.CharField(
        max_length=40,
        unique=True,
        verbose_name='세션 키'
    )
    
    ip_address = models.GenericIPAddressField(verbose_name='접속 IP')
    
    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name='User Agent'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성 시간')
    last_activity = models.DateTimeField(auto_now=True, verbose_name='마지막 활동')
    
    is_active = models.BooleanField(default=True, verbose_name='활성 상태')
    
    class Meta:
        verbose_name = '사용자 세션'
        verbose_name_plural = '사용자 세션들'
        db_table = 'auth_user_session'
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"
    
    @property
    def is_expired(self):
        """세션이 만료되었는지 확인 (2시간 비활성)"""
        return timezone.now() > self.last_activity + timedelta(hours=2)


class UserGroup(models.Model):
    """
    사용자 그룹 확장 정보
    Django Group과 연결하여 추가 정보 저장
    """
    
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        verbose_name='Django 그룹'
    )
    
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        unique=True,
        verbose_name='사용자 타입'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='그룹 설명'
    )
    
    # 권한 관련 설정
    can_access_dashboard = models.BooleanField(default=False, verbose_name='대시보드 접근')
    can_manage_users = models.BooleanField(default=False, verbose_name='사용자 관리')
    can_view_reports = models.BooleanField(default=False, verbose_name='리포트 조회')
    can_manage_calendar = models.BooleanField(default=False, verbose_name='캘린더 관리')
    can_access_field_reports = models.BooleanField(default=False, verbose_name='현장 리포트 접근')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    
    class Meta:
        verbose_name = '사용자 그룹 정보'
        verbose_name_plural = '사용자 그룹 정보들'
        db_table = 'auth_user_group_info'
    
    def __str__(self):
        return f"{self.group.name} ({self.get_user_type_display()})"