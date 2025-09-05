"""
OneSquare Notion API 연동 - 예외 처리

Notion API 관련 커스텀 예외 클래스들을 정의합니다.
"""

from typing import Optional, Dict, Any


class NotionAPIError(Exception):
    """Notion API 기본 예외"""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)
    
    def __str__(self):
        return f"NotionAPIError: {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리 형태로 변환"""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'status_code': self.status_code,
            'response_data': self.response_data
        }


class NotionAuthenticationError(NotionAPIError):
    """Notion 인증 오류"""
    pass


class NotionPermissionError(NotionAPIError):
    """Notion 권한 오류"""
    pass


class NotionRateLimitError(NotionAPIError):
    """Notion API Rate Limit 오류"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['retry_after'] = self.retry_after
        return data


class NotionValidationError(NotionAPIError):
    """Notion 데이터 검증 오류"""
    
    def __init__(self, message: str, validation_errors: Optional[Dict] = None, **kwargs):
        self.validation_errors = validation_errors or {}
        super().__init__(message, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['validation_errors'] = self.validation_errors
        return data


class NotionNotFoundError(NotionAPIError):
    """Notion 리소스를 찾을 수 없음"""
    pass


class NotionServerError(NotionAPIError):
    """Notion 서버 오류 (5xx)"""
    pass


class NotionNetworkError(NotionAPIError):
    """네트워크 연결 오류"""
    pass


class NotionTimeoutError(NotionAPIError):
    """요청 시간 초과 오류"""
    pass


class NotionSyncError(Exception):
    """동기화 관련 오류"""
    
    def __init__(
        self, 
        message: str, 
        sync_id: Optional[str] = None,
        database_id: Optional[str] = None,
        page_errors: Optional[list] = None
    ):
        self.message = message
        self.sync_id = sync_id
        self.database_id = database_id
        self.page_errors = page_errors or []
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'sync_id': self.sync_id,
            'database_id': self.database_id,
            'page_errors': self.page_errors
        }


class NotionConcurrentSyncError(NotionSyncError):
    """동시 동기화 오류"""
    pass


class NotionSchemaError(NotionSyncError):
    """스키마 불일치 오류"""
    pass


class NotionConfigurationError(Exception):
    """설정 오류"""
    pass


def get_exception_from_response(response) -> NotionAPIError:
    """HTTP 응답에서 적절한 예외 생성"""
    status_code = getattr(response, 'status_code', None)
    
    try:
        response_data = response.json() if hasattr(response, 'json') else {}
    except:
        response_data = {}
    
    error_code = response_data.get('code', '')
    message = response_data.get('message', f'HTTP {status_code} Error')
    
    # 상태 코드별 예외 매핑
    if status_code == 401:
        return NotionAuthenticationError(message, error_code, status_code, response_data)
    elif status_code == 403:
        return NotionPermissionError(message, error_code, status_code, response_data)
    elif status_code == 404:
        return NotionNotFoundError(message, error_code, status_code, response_data)
    elif status_code == 400:
        validation_errors = response_data.get('validation_errors', {})
        return NotionValidationError(message, validation_errors, error_code=error_code, status_code=status_code, response_data=response_data)
    elif status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        return NotionRateLimitError(message, retry_after, error_code=error_code, status_code=status_code, response_data=response_data)
    elif status_code >= 500:
        return NotionServerError(message, error_code, status_code, response_data)
    else:
        return NotionAPIError(message, error_code, status_code, response_data)