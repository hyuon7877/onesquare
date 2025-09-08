"""
User related serializers
사용자 관련 시리얼라이저
"""

from rest_framework import serializers
from ..models import CustomUser, UserType, AuthMethod
from ..utils import is_strong_password


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