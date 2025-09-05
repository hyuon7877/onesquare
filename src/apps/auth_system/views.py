"""
OneSquare 사용자 인증 시스템 - API Views

이 모듈은 Django REST Framework를 사용한 인증 관련 API 뷰들을 제공합니다.
- 사용자 등록 (파트너/도급사 포함)
- OTP 인증 (SMS/이메일)
- 이메일+비밀번호 로그인
- 사용자 프로필 관리
- 세션 관리
"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView, ListAPIView
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
import logging

from .models import CustomUser, OTPCode, UserSession, UserType, AuthMethod, OTPToken
from .serializers import (
    UserRegistrationSerializer,
    OTPRequestSerializer, 
    OTPVerificationSerializer,
    EmailPasswordLoginSerializer,
    UserProfileSerializer,
    PasswordChangeSerializer,
    UserListSerializer
)
from .utils import (
    OTPGenerator, 
    SMSService, 
    EmailService, 
    UserPermissionChecker,
    SessionManager
)
from .otp_services import OTPService
from .permissions import PermissionManager, SystemModule, PermissionLevel
from .decorators import (
    permission_required,
    user_type_required
)

logger = logging.getLogger(__name__)


class PermissionRequiredMixin:
    """권한 확인 믹스인 - Django CBV용"""
    
    required_permissions = []  # 필요한 권한 코드 목록
    required_module = None     # 필요한 시스템 모듈
    required_level = PermissionLevel.READ_ONLY  # 필요한 권한 레벨
    required_user_types = []   # 허용된 사용자 타입 목록
    
    def dispatch(self, request, *args, **kwargs):
        """권한 확인 후 뷰 실행"""
        from django.core.exceptions import PermissionDenied
        
        if not request.user.is_authenticated:
            raise PermissionDenied("로그인이 필요합니다.")
        
        # 계정 승인 확인
        if not request.user.is_approved:
            raise PermissionDenied("계정 승인 대기 중입니다. 관리자에게 문의하세요.")
        
        # 사용자 타입 확인
        if self.required_user_types and request.user.user_type not in self.required_user_types:
            raise PermissionDenied("접근 권한이 없습니다.")
        
        # 시스템 모듈 권한 확인
        if self.required_module:
            if not request.user.has_system_permission(self.required_module, self.required_level):
                raise PermissionDenied(f"{self.required_module.value} 모듈에 대한 권한이 없습니다.")
        
        # 개별 권한 확인
        for permission in self.required_permissions:
            if not request.user.has_custom_permission(permission):
                raise PermissionDenied(f"'{permission}' 권한이 없습니다.")
        
        return super().dispatch(request, *args, **kwargs)


@api_view(['GET'])
def auth_status(request):
    """인증 시스템 상태 확인"""
    return Response({
        'message': 'OneSquare 인증 시스템이 정상 작동 중입니다',
        'status': 'success',
        'timestamp': timezone.now(),
        'user_authenticated': request.user.is_authenticated,
        'user_id': request.user.id if request.user.is_authenticated else None
    })


class UserRegistrationView(APIView):
    """
    사용자 등록 API
    
    - 일반 직원, 파트너, 도급사 등록 지원
    - 파트너/도급사는 승인 대기 상태로 생성
    - OTP 인증 방법 자동 설정
    """
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    
                    logger.info(f"새 사용자 등록: {user.username} ({user.get_user_type_display()})")
                    
                    # 파트너/도급사인 경우 승인 대기 메시지
                    if user.user_type in [UserType.PARTNER, UserType.CONTRACTOR]:
                        return Response({
                            'message': '등록이 완료되었습니다. 관리자 승인 후 로그인 가능합니다.',
                            'user_id': user.id,
                            'username': user.username,
                            'user_type': user.get_user_type_display(),
                            'approval_required': True
                        }, status=status.HTTP_201_CREATED)
                    else:
                        return Response({
                            'message': '등록이 완료되었습니다.',
                            'user_id': user.id,
                            'username': user.username,
                            'user_type': user.get_user_type_display(),
                            'approval_required': False
                        }, status=status.HTTP_201_CREATED)
                        
            except ValidationError as e:
                return Response({
                    'error': '등록 중 오류가 발생했습니다.',
                    'details': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OTPRequestView(APIView):
    """
    OTP 코드 요청 API
    
    - SMS 또는 이메일로 OTP 코드 발송
    - 파트너/도급사 전용 (승인된 사용자만)
    """
    
    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            username = serializer.validated_data['username']
            delivery_method = serializer.validated_data.get('delivery_method', 'sms')
            
            try:
                user = CustomUser.objects.get(username=username)
                
                # 사용자 권한 확인 (파트너/도급사만)
                if user.user_type not in [UserType.PARTNER, UserType.CONTRACTOR]:
                    return Response({
                        'error': 'OTP 인증은 파트너/도급사만 사용할 수 있습니다.'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # 승인된 사용자만 OTP 사용 가능
                if not user.is_approved:
                    return Response({
                        'error': '승인되지 않은 사용자입니다. 관리자에게 문의하세요.'
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # OTP 서비스를 통한 OTP 발송
                otp_service = OTPService()
                result = otp_service.send_otp(user, delivery_method, request)
                
                if result['success']:
                    return Response({
                        'message': result['message'],
                        'delivery_method': delivery_method,
                        'expires_in': result.get('expires_in', 300)  # 5분
                    })
                else:
                    return Response({
                        'error': result['error']
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except CustomUser.DoesNotExist:
                return Response({
                    'error': '존재하지 않는 사용자입니다.'
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error(f"OTP 요청 오류: {e}")
                return Response({
                    'error': 'OTP 요청 처리 중 오류가 발생했습니다.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OTPVerificationView(APIView):
    """
    OTP 코드 검증 및 로그인 API
    
    - OTP 코드로 사용자 인증
    - 성공 시 세션 생성 및 토큰 발급
    """
    
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        
        if serializer.is_valid():
            username = serializer.validated_data['username']
            otp_code = serializer.validated_data['otp_code']
            delivery_method = serializer.validated_data.get('delivery_method', 'sms')
            
            try:
                user = CustomUser.objects.get(username=username)
                
                # OTP 서비스를 통한 코드 검증
                otp_service = OTPService()
                result = otp_service.verify_otp(user, otp_code, delivery_method)
                
                if result['success']:
                    # 로그인 처리
                    login(request, user)
                    
                    # 세션 생성
                    user_session = UserSession.objects.create(
                        user=user,
                        session_key=request.session.session_key,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
                    
                    # 토큰 생성 또는 가져오기
                    token, created = Token.objects.get_or_create(user=user)
                    
                    logger.info(f"OTP 로그인 성공: {user.username} ({delivery_method})")
                    
                    return Response({
                        'message': '로그인 성공',
                        'token': token.key,
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'email': user.email,
                            'user_type': user.get_user_type_display(),
                            'full_name': user.get_full_name(),
                        },
                        'session_id': user_session.id,
                        'permissions': {
                            'can_access_dashboard': UserPermissionChecker.has_dashboard_access(user),
                            'can_view_reports': UserPermissionChecker.can_view_reports(user),
                            'can_access_field_reports': UserPermissionChecker.can_access_field_reports(user)
                        }
                    })
                else:
                    return Response({
                        'error': result['error']
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except CustomUser.DoesNotExist:
                return Response({
                    'error': '존재하지 않는 사용자입니다.'
                }, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error(f"OTP 검증 오류: {e}")
                return Response({
                    'error': 'OTP 검증 처리 중 오류가 발생했습니다.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmailPasswordLoginView(APIView):
    """
    이메일+비밀번호 로그인 API
    
    - 관리자, 팀원용 로그인
    - OTP 필요 시 OTP 요구 응답
    """
    
    def post(self, request):
        serializer = EmailPasswordLoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # 로그인 처리
            login(request, user)
            
            # 세션 생성
            user_session = UserSession.objects.create(
                user=user,
                session_key=request.session.session_key,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # 토큰 생성 또는 가져오기
            token, created = Token.objects.get_or_create(user=user)
            
            logger.info(f"이메일 로그인 성공: {user.username}")
            
            return Response({
                'message': '로그인 성공',
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'user_type': user.get_user_type_display(),
                    'full_name': user.get_full_name(),
                },
                'session_id': user_session.id,
                'permissions': {
                    'can_access_dashboard': UserPermissionChecker.has_dashboard_access(user),
                    'can_manage_users': UserPermissionChecker.can_manage_users(user),
                    'can_view_reports': UserPermissionChecker.can_view_reports(user),
                    'can_access_field_reports': UserPermissionChecker.can_access_field_reports(user)
                }
            })
        
        # OTP 필요한 경우 특별 처리
        if 'otp_required' in serializer.errors:
            return Response(serializer.errors, status=status.HTTP_200_OK)  # 200으로 반환하여 클라이언트가 OTP 화면으로 이동할 수 있도록
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(RetrieveUpdateAPIView):
    """
    사용자 프로필 조회 및 수정 API
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get_object(self):
        return self.request.user


class PasswordChangeView(APIView):
    """
    비밀번호 변경 API
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = request.user
            new_password = serializer.validated_data['new_password']
            
            # 비밀번호 변경
            user.set_password(new_password)
            user.save()
            
            # 기존 세션들 종료 (보안상 이유)
            SessionManager.terminate_user_sessions(user, except_session_key=request.session.session_key)
            
            # 기존 토큰 삭제 (새로운 로그인 강제)
            Token.objects.filter(user=user).delete()
            
            logger.info(f"비밀번호 변경: {user.username}")
            
            return Response({
                'message': '비밀번호가 성공적으로 변경되었습니다. 다시 로그인해주세요.',
                'logout_required': True
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    로그아웃 API
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def post(self, request):
        try:
            # 현재 세션 비활성화
            UserSession.objects.filter(
                user=request.user,
                session_key=request.session.session_key
            ).update(is_active=False)
            
            # 토큰 삭제
            Token.objects.filter(user=request.user).delete()
            
            # Django 로그아웃
            logout(request)
            
            logger.info(f"로그아웃: {request.user.username}")
            
            return Response({
                'message': '로그아웃되었습니다.'
            })
            
        except Exception as e:
            logger.error(f"로그아웃 오류: {e}")
            return Response({
                'message': '로그아웃되었습니다.'  # 오류가 있어도 성공으로 처리
            })


class UserSessionListView(APIView):
    """
    사용자 세션 목록 조회 API (본인 세션만)
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get(self, request):
        sessions = SessionManager.get_active_sessions_for_user(request.user)
        
        session_data = []
        for session in sessions:
            session_data.append({
                'id': session.id,
                'ip_address': session.ip_address,
                'user_agent': session.user_agent,
                'login_time': session.login_time,
                'last_activity': session.last_activity,
                'is_current': session.session_key == request.session.session_key
            })
        
        return Response({
            'sessions': session_data,
            'total_count': len(session_data)
        })


class TerminateSessionView(APIView):
    """
    특정 세션 종료 API
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def post(self, request):
        session_id = request.data.get('session_id')
        
        if not session_id:
            return Response({
                'error': 'session_id가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 본인의 세션인지 확인
            user_session = UserSession.objects.get(
                id=session_id,
                user=request.user,
                is_active=True
            )
            
            # 세션 종료
            user_session.is_active = False
            user_session.save()
            
            # 현재 세션을 종료하는 경우 로그아웃 처리
            if user_session.session_key == request.session.session_key:
                Token.objects.filter(user=request.user).delete()
                logout(request)
                
                return Response({
                    'message': '현재 세션이 종료되었습니다. 다시 로그인해주세요.',
                    'logout_required': True
                })
            
            return Response({
                'message': '세션이 종료되었습니다.'
            })
            
        except UserSession.DoesNotExist:
            return Response({
                'error': '존재하지 않는 세션이거나 접근 권한이 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)


# 관리자용 뷰들

def is_admin_user(user):
    """관리자 권한 확인 (데코레이터용)"""
    return UserPermissionChecker.can_manage_users(user)


class AdminUserListView(ListAPIView):
    """
    관리자용 사용자 목록 조회 API
    """
    serializer_class = UserListSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    @method_decorator(user_passes_test(is_admin_user))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_queryset(self):
        queryset = CustomUser.objects.all().select_related().prefetch_related('groups')
        
        # 필터링 옵션
        user_type = self.request.query_params.get('user_type')
        is_approved = self.request.query_params.get('is_approved')
        is_active = self.request.query_params.get('is_active')
        
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        
        if is_approved is not None:
            queryset = queryset.filter(is_approved=is_approved.lower() == 'true')
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.order_by('-date_joined')


class AdminUserApprovalView(APIView):
    """
    관리자용 사용자 승인/거부 API
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    @method_decorator(user_passes_test(is_admin_user))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        user_id = request.data.get('user_id')
        action = request.data.get('action')  # 'approve' 또는 'reject'
        
        if not user_id or action not in ['approve', 'reject']:
            return Response({
                'error': 'user_id와 action(approve/reject)이 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(id=user_id)
            
            if action == 'approve':
                user.is_approved = True
                user.save()
                
                logger.info(f"사용자 승인: {user.username} (관리자: {request.user.username})")
                
                return Response({
                    'message': f'{user.username} 사용자가 승인되었습니다.',
                    'user_id': user.id,
                    'is_approved': True
                })
            
            else:  # reject
                user.is_approved = False
                user.is_active = False  # 거부 시 비활성화
                user.save()
                
                logger.info(f"사용자 거부: {user.username} (관리자: {request.user.username})")
                
                return Response({
                    'message': f'{user.username} 사용자가 거부되었습니다.',
                    'user_id': user.id,
                    'is_approved': False
                })
                
        except CustomUser.DoesNotExist:
            return Response({
                'error': '존재하지 않는 사용자입니다.'
            }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@user_passes_test(is_admin_user)
def admin_cleanup_sessions(request):
    """
    관리자용 만료된 세션 정리 API
    """
    try:
        cleaned_count = SessionManager.cleanup_expired_sessions()
        
        return Response({
            'message': f'{cleaned_count}개의 만료된 세션이 정리되었습니다.',
            'cleaned_count': cleaned_count
        })
        
    except Exception as e:
        logger.error(f"세션 정리 오류: {e}")
        return Response({
            'error': '세션 정리 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OTPStatusView(APIView):
    """
    OTP 상태 확인 API
    
    - 현재 활성화된 OTP 토큰 상태 조회
    - 만료 시간, 시도 횟수 등 확인
    """
    
    def get(self, request):
        username = request.query_params.get('username')
        otp_type = request.query_params.get('otp_type', 'login')
        
        if not username:
            return Response({
                'error': 'username 파라미터가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(username=username)
            
            # 활성화된 OTP 토큰 조회
            active_token = OTPToken.objects.filter(
                user=user,
                otp_type=otp_type,
                status='pending',
                expires_at__gt=timezone.now()
            ).first()
            
            if active_token:
                remaining_time = (active_token.expires_at - timezone.now()).total_seconds()
                return Response({
                    'has_active_token': True,
                    'expires_in': int(remaining_time),
                    'attempt_count': active_token.attempt_count,
                    'max_attempts': active_token.max_attempts,
                    'remaining_attempts': active_token.max_attempts - active_token.attempt_count,
                    'delivery_method': active_token.delivery_method,
                    'created_at': active_token.created_at
                })
            else:
                return Response({
                    'has_active_token': False,
                    'message': '활성화된 OTP 토큰이 없습니다.'
                })
                
        except CustomUser.DoesNotExist:
            return Response({
                'error': '존재하지 않는 사용자입니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"OTP 상태 확인 오류: {e}")
            return Response({
                'error': 'OTP 상태 확인 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OTPResendView(APIView):
    """
    OTP 재발송 API
    
    - 기존 OTP가 있으면 무효화하고 새 OTP 발송
    - Rate Limiting 적용
    """
    
    def post(self, request):
        username = request.data.get('username')
        delivery_method = request.data.get('delivery_method', 'sms')
        
        if not username:
            return Response({
                'error': 'username이 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(username=username)
            
            # 사용자 권한 확인
            if user.user_type not in [UserType.PARTNER, UserType.CONTRACTOR]:
                return Response({
                    'error': 'OTP 인증은 파트너/도급사만 사용할 수 있습니다.'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # OTP 서비스를 통한 재발송
            otp_service = OTPService()
            result = otp_service.resend_otp(user, delivery_method, request)
            
            if result['success']:
                return Response({
                    'message': result['message'],
                    'delivery_method': delivery_method,
                    'expires_in': result.get('expires_in', 300)
                })
            else:
                return Response({
                    'error': result['error']
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except CustomUser.DoesNotExist:
            return Response({
                'error': '존재하지 않는 사용자입니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"OTP 재발송 오류: {e}")
            return Response({
                'error': 'OTP 재발송 처리 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Template Views (UI)

class LoginView(TemplateView):
    """로그인 페이지"""
    template_name = 'auth/login.html'
    
    def dispatch(self, request, *args, **kwargs):
        # 이미 로그인된 사용자는 대시보드로 리다이렉트
        if request.user.is_authenticated:
            return redirect('/dashboard/')
        return super().dispatch(request, *args, **kwargs)


class RegisterView(TemplateView):
    """회원가입 페이지"""
    template_name = 'auth/register.html'
    
    def dispatch(self, request, *args, **kwargs):
        # 이미 로그인된 사용자는 대시보드로 리다이렉트
        if request.user.is_authenticated:
            return redirect('/dashboard/')
        return super().dispatch(request, *args, **kwargs)


class OTPLoginView(TemplateView):
    """OTP 로그인 페이지"""
    template_name = 'auth/otp_login.html'
    
    def dispatch(self, request, *args, **kwargs):
        # 이미 로그인된 사용자는 대시보드로 리다이렉트
        if request.user.is_authenticated:
            return redirect('/dashboard/')
        return super().dispatch(request, *args, **kwargs)


# 권한 기반 뷰 예제들

class DashboardView(PermissionRequiredMixin, TemplateView):
    """대시보드 페이지 - 권한 확인"""
    template_name = 'dashboard/main.html'
    required_module = SystemModule.DASHBOARD
    required_level = PermissionLevel.READ_ONLY
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context.update({
            'user_permissions': user.get_permission_summary(),
            'accessible_modules': user.get_accessible_modules(),
            'user_type_display': user.get_user_type_display(),
        })
        
        return context


class UserManagementView(PermissionRequiredMixin, TemplateView):
    """사용자 관리 페이지 - 관리자만 접근 가능"""
    template_name = 'auth/user_management.html'
    required_module = SystemModule.USER_MANAGEMENT
    required_level = PermissionLevel.READ_ONLY
    required_user_types = [UserType.SUPER_ADMIN, UserType.MANAGER]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # 권한에 따른 사용자 목록 필터링
        if user.user_type == UserType.SUPER_ADMIN:
            users = CustomUser.objects.all()
        elif user.user_type == UserType.MANAGER:
            # 관리자는 최고관리자를 제외한 사용자만 볼 수 있음
            users = CustomUser.objects.exclude(user_type=UserType.SUPER_ADMIN)
        else:
            users = CustomUser.objects.none()
        
        context.update({
            'users': users.order_by('-created_at'),
            'user_types': UserType.choices,
            'can_manage_users': user.has_system_permission(
                SystemModule.USER_MANAGEMENT, 
                PermissionLevel.READ_WRITE
            )
        })
        
        return context


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_permissions_api(request):
    """사용자 권한 정보 조회 API"""
    user = request.user
    
    return Response({
        'user_info': {
            'username': user.username,
            'email': user.email,
            'user_type': user.user_type,
            'user_type_display': user.get_user_type_display(),
            'is_approved': user.is_approved,
        },
        'permissions': user.get_permission_summary(),
        'accessible_modules': [module.value for module in user.get_accessible_modules()],
        'has_admin_access': user.is_admin_level
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@permission_required('auth.change_user')
def update_user_permissions_api(request, user_id):
    """사용자 권한 업데이트 API - 관리자만 가능"""
    try:
        target_user = CustomUser.objects.get(id=user_id)
        
        # 최고관리자는 다른 최고관리자를 수정할 수 없음
        if (target_user.user_type == UserType.SUPER_ADMIN and 
            request.user.user_type != UserType.SUPER_ADMIN):
            return Response({
                'error': '최고관리자 권한이 필요합니다.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # 권한 업데이트 로직
        new_user_type = request.data.get('user_type')
        if new_user_type and new_user_type in [choice[0] for choice in UserType.choices]:
            target_user.user_type = new_user_type
            target_user.assign_user_type_permissions()  # 권한 그룹 재할당
            target_user.save()
            
            logger.info(f"User permissions updated: {target_user.username} -> {new_user_type} by {request.user.username}")
            
            return Response({
                'success': True,
                'message': '사용자 권한이 업데이트되었습니다.',
                'user_permissions': target_user.get_permission_summary()
            })
        else:
            return Response({
                'error': '유효하지 않은 사용자 타입입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except CustomUser.DoesNotExist:
        return Response({
            'error': '존재하지 않는 사용자입니다.'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Permission update error: {e}")
        return Response({
            'error': '권한 업데이트 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_module_permission_api(request, module_name):
    """특정 모듈 권한 확인 API"""
    try:
        module = SystemModule(module_name.upper())
        user = request.user
        
        permissions_check = {
            'module': module.value,
            'module_display': module.value.replace('_', ' ').title(),
            'has_read': user.has_system_permission(module, PermissionLevel.READ_ONLY),
            'has_write': user.has_system_permission(module, PermissionLevel.READ_WRITE),
            'has_full': user.has_system_permission(module, PermissionLevel.FULL),
        }
        
        return Response(permissions_check)
        
    except ValueError:
        return Response({
            'error': f'유효하지 않은 모듈명입니다: {module_name}'
        }, status=status.HTTP_400_BAD_REQUEST)