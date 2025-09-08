"""
Authentication related serializers
인증 관련 시리얼라이저
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from ..models import CustomUser
from ..utils import is_strong_password


class EmailPasswordLoginSerializer(serializers.Serializer):
    """이메일+비밀번호 로그인 Serializer"""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """로그인 검증"""
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError("이메일과 비밀번호를 모두 입력해주세요.")
        
        user = self._authenticate_user(email, password)
        
        if not user:
            raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")
        
        self._validate_user_status(user)
        
        attrs['user'] = user
        return attrs
    
    def _authenticate_user(self, email, password):
        """사용자 인증 시도"""
        request = self.context.get('request')
        
        # 먼저 이메일을 username으로 시도
        user = authenticate(request=request, username=email, password=password)
        
        if not user:
            # 이메일로 사용자를 찾아서 username으로 재시도
            try:
                user_obj = CustomUser.objects.get(email=email)
                user = authenticate(
                    request=request,
                    username=user_obj.username,
                    password=password
                )
            except CustomUser.DoesNotExist:
                pass
        
        return user
    
    def _validate_user_status(self, user):
        """사용자 상태 검증"""
        if not user.is_approved:
            raise serializers.ValidationError("승인되지 않은 계정입니다. 관리자에게 문의하세요.")
        
        if not user.is_active:
            raise serializers.ValidationError("비활성화된 계정입니다.")
        
        # OTP 인증 필요한 사용자인지 확인
        if user.requires_otp:
            raise serializers.ValidationError({
                'otp_required': True,
                'message': 'OTP 인증이 필요합니다.',
                'user_id': user.id
            })


class PasswordChangeSerializer(serializers.Serializer):
    """비밀번호 변경 Serializer"""
    
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate_old_password(self, value):
        """기존 비밀번호 검증"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("기존 비밀번호가 올바르지 않습니다.")
        return value
    
    def validate_new_password(self, value):
        """새 비밀번호 유효성 검증"""
        is_valid, message = is_strong_password(value)
        if not is_valid:
            raise serializers.ValidationError(message)
        return value
    
    def validate(self, attrs):
        """전체 데이터 검증"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("새 비밀번호가 일치하지 않습니다.")
        
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError("새 비밀번호는 기존 비밀번호와 달라야 합니다.")
        
        return attrs