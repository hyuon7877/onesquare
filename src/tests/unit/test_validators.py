"""Validators 모듈 단위 테스트"""

import pytest
from django.core.exceptions import ValidationError
from apps.security.validators import (
    ComplexPasswordValidator,
    InputSanitizationValidator
)


class TestComplexPasswordValidator:
    """복잡한 패스워드 검증기 테스트"""
    
    def setup_method(self):
        self.validator = ComplexPasswordValidator()
    
    def test_valid_password(self):
        """유효한 패스워드 테스트"""
        # 모든 요구사항을 충족하는 패스워드
        valid_password = "TestPassword123!@#"
        
        # 예외가 발생하지 않아야 함
        try:
            self.validator.validate(valid_password)
        except ValidationError:
            pytest.fail("유효한 패스워드가 거부됨")
    
    def test_short_password(self):
        """짧은 패스워드 테스트"""
        short_password = "Test1!"
        
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(short_password)
        
        assert "최소" in str(exc_info.value)
    
    def test_no_uppercase(self):
        """대문자 없는 패스워드 테스트"""
        password = "testpassword123!"
        
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(password)
        
        assert "대문자" in str(exc_info.value)
    
    def test_no_lowercase(self):
        """소문자 없는 패스워드 테스트"""
        password = "TESTPASSWORD123!"
        
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(password)
        
        assert "소문자" in str(exc_info.value)
    
    def test_no_numbers(self):
        """숫자 없는 패스워드 테스트"""
        password = "TestPassword!"
        
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(password)
        
        assert "숫자" in str(exc_info.value)
    
    def test_sequential_characters(self):
        """연속된 문자 테스트"""
        password = "Abc123!@#def"
        
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(password)
        
        assert "연속" in str(exc_info.value)
    
    def test_repetitive_characters(self):
        """반복 문자 테스트"""
        password = "Tesssst123!"
        
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(password)
        
        assert "반복" in str(exc_info.value)


class TestInputSanitizationValidator:
    """입력 데이터 살균 검증기 테스트"""
    
    def test_sanitize_string_removes_html(self):
        """HTML 태그 제거 테스트"""
        dirty_string = "<script>alert('xss')</script>Hello"
        clean_string = InputSanitizationValidator.sanitize_string(dirty_string)
        
        assert "<script>" not in clean_string
        assert "alert" not in clean_string
    
    def test_validate_sql_injection(self):
        """SQL 인젝션 공격 패턴 감지 테스트"""
        # 정상 입력
        assert InputSanitizationValidator.validate_sql_injection("normal input") == True
        
        # SQL 인젝션 시도
        assert InputSanitizationValidator.validate_sql_injection("'; DROP TABLE users--") == False
        assert InputSanitizationValidator.validate_sql_injection("' OR 1=1--") == False
    
    def test_validate_xss(self):
        """XSS 공격 패턴 감지 테스트"""
        # 정상 입력
        assert InputSanitizationValidator.validate_xss("normal text") == True
        
        # XSS 시도
        assert InputSanitizationValidator.validate_xss("<script>alert('xss')</script>") == False
        assert InputSanitizationValidator.validate_xss("javascript:void(0)") == False
    
    def test_validate_file_upload(self):
        """파일 업로드 검증 테스트"""
        # 안전한 파일명
        assert InputSanitizationValidator.validate_file_upload("image.jpg") == True
        assert InputSanitizationValidator.validate_file_upload("document.pdf") == True
        
        # 위험한 확장자
        assert InputSanitizationValidator.validate_file_upload("malware.exe") == False
        assert InputSanitizationValidator.validate_file_upload("script.php") == False
        
        # 경로 탐색 시도
        assert InputSanitizationValidator.validate_file_upload("../../etc/passwd") == False
    
    def test_validate_url(self):
        """URL 검증 테스트"""
        # 안전한 URL
        assert InputSanitizationValidator.validate_url("https://example.com") == True
        assert InputSanitizationValidator.validate_url("http://localhost:8000") == True
        
        # 위험한 URL 스키마
        assert InputSanitizationValidator.validate_url("javascript:alert(1)") == False
        assert InputSanitizationValidator.validate_url("data:text/html,<script>alert(1)</script>") == False
    
    def test_validate_email(self):
        """이메일 검증 테스트"""
        # 유효한 이메일
        assert InputSanitizationValidator.validate_email("user@example.com") == True
        assert InputSanitizationValidator.validate_email("test.user+tag@domain.co.kr") == True
        
        # 무효한 이메일
        assert InputSanitizationValidator.validate_email("not-an-email") == False
        assert InputSanitizationValidator.validate_email("@example.com") == False
        assert InputSanitizationValidator.validate_email("user@") == False