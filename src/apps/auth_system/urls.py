"""
OneSquare 사용자 인증 시스템 - URL 패턴

이 모듈은 인증 시스템의 모든 API 엔드포인트를 정의합니다.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'auth_system'

# Template URL 패턴들 (UI)
urlpatterns = [
    # 템플릿 뷰
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('otp-login/', views.OTPLoginView.as_view(), name='otp_login'),
    
    # API 엔드포인트
    # 기본 상태 확인
    path('api/status/', views.auth_status, name='auth_status'),
    
    # 사용자 등록 및 관리
    path('api/register/', views.UserRegistrationView.as_view(), name='user_register'),
    path('api/profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('api/change-password/', views.PasswordChangeView.as_view(), name='change_password'),
    
    # OTP 인증 (파트너/도급사용)
    path('api/otp/request/', views.OTPRequestView.as_view(), name='otp_request'),
    path('api/otp/verify/', views.OTPVerificationView.as_view(), name='otp_verify'),
    path('api/otp/status/', views.OTPStatusView.as_view(), name='otp_status'),
    path('api/otp/resend/', views.OTPResendView.as_view(), name='otp_resend'),
    
    # 로그인 및 로그아웃
    path('api/login/email/', views.EmailPasswordLoginView.as_view(), name='email_login'),
    path('api/logout/', views.LogoutView.as_view(), name='logout'),
    
    # 세션 관리
    path('api/sessions/', views.UserSessionListView.as_view(), name='user_sessions'),
    path('api/sessions/terminate/', views.TerminateSessionView.as_view(), name='terminate_session'),
    
    # 관리자용 API
    path('api/admin/users/', views.AdminUserListView.as_view(), name='admin_user_list'),
    path('api/admin/users/approval/', views.AdminUserApprovalView.as_view(), name='admin_user_approval'),
    path('api/admin/sessions/cleanup/', views.admin_cleanup_sessions, name='admin_cleanup_sessions'),
]