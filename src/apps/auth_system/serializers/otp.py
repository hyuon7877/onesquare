"""
OTP related serializers
OTP 관련 시리얼라이저
"""

from rest_framework import serializers
from ..models import CustomUser


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
            self._validate_user_status(user)
            return value
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 사용자입니다.")
    
    def _validate_user_status(self, user):
        """사용자 상태 검증"""
        if not user.is_approved:
            raise serializers.ValidationError("승인되지 않은 계정입니다.")
        if not user.is_active:
            raise serializers.ValidationError("비활성화된 계정입니다.")


class OTPVerificationSerializer(serializers.Serializer):
    """OTP 검증 Serializer"""
    
    username = serializers.CharField(max_length=150)
    otp_code = serializers.CharField(max_length=6, min_length=6)
    delivery_method = serializers.ChoiceField(
        choices=[('sms', 'SMS'), ('email', '이메일')],
        default='sms'
    )
    
    def validate_otp_code(self, value):
        """OTP 코드 형식 검증"""
        if not value.isdigit():
            raise serializers.ValidationError("OTP 코드는 6자리 숫자여야 합니다.")
        return value