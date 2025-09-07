"""OneSquare 보안 검증 시스템
분할된 검증 모듈 통합
"""

from .password import ComplexPasswordValidator
from .input import InputSanitizationValidator
from .patterns import (
    XSS_PATTERNS,
    SQL_INJECTION_PATTERNS,
    DANGEROUS_EXTENSIONS,
    COMMON_PASSWORD_PATTERNS,
    DANGEROUS_URL_SCHEMES,
    DANGEROUS_FILENAME_PATTERNS,
)
from .utils import (
    is_safe_string,
    normalize_whitespace,
    validate_korean_phone,
    validate_korean_business_number,
    sanitize_for_log,
    get_validation_errors,
)

__all__ = [
    # Password
    'ComplexPasswordValidator',
    
    # Input
    'InputSanitizationValidator',
    
    # Patterns
    'XSS_PATTERNS',
    'SQL_INJECTION_PATTERNS',
    'DANGEROUS_EXTENSIONS',
    'COMMON_PASSWORD_PATTERNS',
    'DANGEROUS_URL_SCHEMES',
    'DANGEROUS_FILENAME_PATTERNS',
    
    # Utils
    'is_safe_string',
    'normalize_whitespace',
    'validate_korean_phone',
    'validate_korean_business_number',
    'sanitize_for_log',
    'get_validation_errors',
]

# 버전 정보
__version__ = '1.0.0'
__author__ = 'OneSquare Team'
