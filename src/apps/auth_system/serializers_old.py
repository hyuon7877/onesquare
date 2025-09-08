"""
OneSquare 사용자 인증 시스템 - DRF Serializers
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import CustomUser, OTPCode, UserType, AuthMethod
from .utils import OTPGenerator, is_strong_password


class UserRegistrationSerializer(serializers.ModelSerializer):
    """사용자 등록 Serializer"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'user_type', 'auth_method',
            'phone_number', 'company', 'department', 'position'
        ]
    
    def validate_password(self, value):
        """비밀번호 유효성 검증"""
        is_valid, message = is_strong_password(value)
        if not is_valid:
            raise serializers.ValidationError(message)
        return value
    
    def validate(self, attrs):
        """전체 데이터 유효성 검증"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")
        
        # OTP 인증 사용자는 전화번호 또는 이메일 필수
        if attrs.get('auth_method') == AuthMethod.OTP_SMS:
            if not attrs.get('phone_number'):
                raise serializers.ValidationError("SMS OTP 인증을 위해서는 전화번호가 필요합니다.")
        
        if attrs.get('auth_method') == AuthMethod.OTP_EMAIL:
            if not attrs.get('email'):
                raise serializers.ValidationError("이메일 OTP 인증을 위해서는 이메일이 필요합니다.")
        
        return attrs
    
    def create(self, validated_data):
        """사용자 생성"""
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')
        
        # 파트너/도급사는 기본적으로 승인 대기 상태
        if validated_data.get('user_type') in [UserType.PARTNER, UserType.CONTRACTOR]:
            validated_data['is_approved'] = False
            if not validated_data.get('auth_method'):
                validated_data['auth_method'] = AuthMethod.OTP_SMS
        
        user = CustomUser.objects.create_user(
            password=password,
            **validated_data
        )
        
        return user


class OTPRequestSerializer(serializers.Serializer):
    """OTP 요청 Serializer"""
    
    username = serializers.CharField(max_length=150)
    delivery_method = serializers.ChoiceField(
        choices=[('sms', 'SMS'), ('email', '이메일')],
        default='sms'
    )
    
    def validate_username(self, value):
        """사용자명 검증"""
        try:
            user = CustomUser.objects.get(username=value)
            if not user.is_approved:
                raise serializers.ValidationError("승인되지 않은 계정입니다.")
            if not user.is_active:
                raise serializers.ValidationError("비활성화된 계정입니다.")
            return value
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 사용자입니다.")


class OTPVerificationSerializer(serializers.Serializer):
    """OTP 검증 Serializer"""
    
    username = serializers.CharField(max_length=150)
    otp_code = serializers.CharField(max_length=6, min_length=6)
    delivery_method = serializers.ChoiceField(
        choices=[('sms', 'SMS'), ('email', '이메일')],
        default='sms'
    )


class EmailPasswordLoginSerializer(serializers.Serializer):
    """이메일+비밀번호 로그인 Serializer"""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """로그인 검증"""
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
            
            if not user:
                # 이메일로 사용자를 찾아서 username으로 재시도
                try:
                    user_obj = CustomUser.objects.get(email=email)
                    user = authenticate(
                        request=self.context.get('request'),
                        username=user_obj.username,
                        password=password
                    )
                except CustomUser.DoesNotExist:
                    pass
            
            if not user:
                raise serializers.ValidationError("이메일 또는 비밀번호가 올바르지 않습니다.")
            
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
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError("이메일과 비밀번호를 모두 입력해주세요.")


class UserProfileSerializer(serializers.ModelSerializer):
    """사용자 프로필 Serializer"""
    
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    auth_method_display = serializers.CharField(source='get_auth_method_display', read_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'user_type', 'user_type_display', 'auth_method', 'auth_method_display',
            'phone_number', 'company', 'department', 'position',
            'profile_image', 'is_approved', 'last_login', 'date_joined'
        ]
        read_only_fields = ['id', 'username', 'user_type', 'auth_method', 'is_approved', 'last_login', 'date_joined']


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


class UserListSerializer(serializers.ModelSerializer):
    """사용자 목록용 Serializer (관리자용)"""
    
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    groups_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'user_type', 'user_type_display', 'groups_display',
            'company', 'is_approved', 'is_active', 'last_login', 'date_joined'
        ]
    
    def get_groups_display(self, obj):
        """사용자 그룹 표시"""
        return [group.name for group in obj.groups.all()]