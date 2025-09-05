"""
OneSquare Notion API 연동 - 재시도 유틸리티

API 호출 실패 시 재시도 로직과 백오프 전략을 제공합니다.
"""

import time
import random
import logging
import functools
from typing import Callable, Any, Optional, Tuple, List, Type, Union
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .exceptions import (
    NotionAPIError, NotionRateLimitError, NotionServerError, 
    NotionNetworkError, NotionTimeoutError, NotionAuthenticationError,
    NotionPermissionError
)


logger = logging.getLogger(__name__)


class BackoffStrategy:
    """백오프 전략 기본 클래스"""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def get_delay(self, attempt: int) -> float:
        """재시도 시도 횟수에 따른 지연 시간 계산"""
        raise NotImplementedError


class ExponentialBackoff(BackoffStrategy):
    """지수 백오프 전략"""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, multiplier: float = 2.0):
        super().__init__(base_delay, max_delay)
        self.multiplier = multiplier
    
    def get_delay(self, attempt: int) -> float:
        delay = self.base_delay * (self.multiplier ** (attempt - 1))
        return min(delay, self.max_delay)


class LinearBackoff(BackoffStrategy):
    """선형 백오프 전략"""
    
    def get_delay(self, attempt: int) -> float:
        delay = self.base_delay * attempt
        return min(delay, self.max_delay)


class JitteredExponentialBackoff(ExponentialBackoff):
    """지터가 있는 지수 백오프 전략"""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, 
                 multiplier: float = 2.0, jitter_ratio: float = 0.1):
        super().__init__(base_delay, max_delay, multiplier)
        self.jitter_ratio = jitter_ratio
    
    def get_delay(self, attempt: int) -> float:
        base_delay = super().get_delay(attempt)
        jitter = base_delay * self.jitter_ratio * random.random()
        return base_delay + jitter


class RetryConfig:
    """재시도 설정"""
    
    def __init__(
        self,
        max_retries: int = 3,
        backoff_strategy: Optional[BackoffStrategy] = None,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        non_retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        retry_on_status_codes: Optional[List[int]] = None,
        timeout: Optional[float] = None
    ):
        self.max_retries = max_retries
        self.backoff_strategy = backoff_strategy or JitteredExponentialBackoff()
        self.retryable_exceptions = retryable_exceptions or (
            NotionServerError,
            NotionNetworkError, 
            NotionTimeoutError,
            NotionRateLimitError
        )
        self.non_retryable_exceptions = non_retryable_exceptions or (
            NotionAuthenticationError,
            NotionPermissionError
        )
        self.retry_on_status_codes = retry_on_status_codes or [500, 502, 503, 504, 429]
        self.timeout = timeout
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """재시도 여부 판단"""
        if attempt >= self.max_retries:
            return False
        
        if isinstance(exception, self.non_retryable_exceptions):
            return False
        
        if isinstance(exception, self.retryable_exceptions):
            return True
        
        if isinstance(exception, NotionAPIError):
            return exception.status_code in self.retry_on_status_codes
        
        return False


class RetryResult:
    """재시도 결과"""
    
    def __init__(
        self, 
        success: bool, 
        result: Any = None, 
        exception: Optional[Exception] = None,
        attempts: int = 0,
        total_duration: float = 0.0,
        attempt_details: Optional[List[dict]] = None
    ):
        self.success = success
        self.result = result
        self.exception = exception
        self.attempts = attempts
        self.total_duration = total_duration
        self.attempt_details = attempt_details or []
    
    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'attempts': self.attempts,
            'total_duration': self.total_duration,
            'final_exception': self.exception.to_dict() if hasattr(self.exception, 'to_dict') else str(self.exception),
            'attempt_details': self.attempt_details
        }


class RetryExecutor:
    """재시도 실행기"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def execute(self, func: Callable, *args, **kwargs) -> RetryResult:
        """함수를 재시도 로직과 함께 실행"""
        start_time = time.time()
        attempt_details = []
        last_exception = None
        
        for attempt in range(1, self.config.max_retries + 2):  # +1 for initial attempt
            attempt_start = time.time()
            
            try:
                logger.debug(f"Attempting {func.__name__} (attempt {attempt}/{self.config.max_retries + 1})")
                result = func(*args, **kwargs)
                
                attempt_duration = time.time() - attempt_start
                attempt_details.append({
                    'attempt': attempt,
                    'success': True,
                    'duration': attempt_duration
                })
                
                total_duration = time.time() - start_time
                logger.info(f"Function {func.__name__} succeeded on attempt {attempt}")
                
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempt,
                    total_duration=total_duration,
                    attempt_details=attempt_details
                )
            
            except Exception as e:
                attempt_duration = time.time() - attempt_start
                last_exception = e
                
                attempt_details.append({
                    'attempt': attempt,
                    'success': False,
                    'duration': attempt_duration,
                    'exception': str(e),
                    'exception_type': type(e).__name__
                })
                
                logger.warning(f"Attempt {attempt} failed for {func.__name__}: {str(e)}")
                
                # 재시도 여부 확인
                if not self.config.should_retry(e, attempt):
                    logger.error(f"Not retrying {func.__name__} after {attempt} attempts")
                    break
                
                # Rate limit 처리
                if isinstance(e, NotionRateLimitError) and e.retry_after:
                    delay = e.retry_after
                    logger.info(f"Rate limited, waiting {delay} seconds before retry")
                else:
                    delay = self.config.backoff_strategy.get_delay(attempt)
                    logger.info(f"Waiting {delay:.2f} seconds before retry {attempt + 1}")
                
                time.sleep(delay)
        
        total_duration = time.time() - start_time
        
        return RetryResult(
            success=False,
            exception=last_exception,
            attempts=len(attempt_details),
            total_duration=total_duration,
            attempt_details=attempt_details
        )


def with_retry(config: Optional[RetryConfig] = None):
    """재시도 데코레이터"""
    
    def decorator(func: Callable) -> Callable:
        executor = RetryExecutor(config)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = executor.execute(func, *args, **kwargs)
            
            if result.success:
                return result.result
            else:
                # 최종 실패 시 마지막 예외 발생
                raise result.exception
        
        # 재시도 결과를 포함한 래퍼 생성
        @functools.wraps(func)
        def wrapper_with_result(*args, **kwargs):
            return executor.execute(func, *args, **kwargs)
        
        wrapper.with_result = wrapper_with_result
        wrapper.executor = executor
        
        return wrapper
    
    return decorator


class CircuitBreaker:
    """서킷 브레이커 패턴 구현"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
        name: Optional[str] = None
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name or "circuit_breaker"
        
        # 캐시 키들
        self.failure_count_key = f"cb_failures_{self.name}"
        self.last_failure_time_key = f"cb_last_failure_{self.name}"
        self.state_key = f"cb_state_{self.name}"
    
    @property
    def failure_count(self) -> int:
        return cache.get(self.failure_count_key, 0)
    
    @property
    def last_failure_time(self) -> Optional[datetime]:
        timestamp = cache.get(self.last_failure_time_key)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp else None
    
    @property
    def state(self) -> str:
        return cache.get(self.state_key, 'closed')
    
    def _set_state(self, state: str):
        cache.set(self.state_key, state, timeout=3600)
    
    def _increment_failure(self):
        current_count = self.failure_count + 1
        cache.set(self.failure_count_key, current_count, timeout=3600)
        cache.set(self.last_failure_time_key, time.time(), timeout=3600)
    
    def _reset_failure_count(self):
        cache.delete(self.failure_count_key)
        cache.delete(self.last_failure_time_key)
    
    def can_execute(self) -> bool:
        """실행 가능 여부 확인"""
        current_state = self.state
        
        if current_state == 'closed':
            return True
        elif current_state == 'open':
            # 복구 시간이 지났는지 확인
            last_failure = self.last_failure_time
            if last_failure and (timezone.now() - last_failure).total_seconds() >= self.recovery_timeout:
                self._set_state('half-open')
                return True
            return False
        elif current_state == 'half-open':
            return True
        
        return False
    
    def record_success(self):
        """성공 기록"""
        if self.state == 'half-open':
            self._reset_failure_count()
            self._set_state('closed')
            logger.info(f"Circuit breaker {self.name} recovered and closed")
    
    def record_failure(self, exception: Exception):
        """실패 기록"""
        if isinstance(exception, self.expected_exception):
            self._increment_failure()
            
            current_count = self.failure_count
            current_state = self.state
            
            if current_state == 'half-open':
                self._set_state('open')
                logger.warning(f"Circuit breaker {self.name} opened due to failure in half-open state")
            elif current_count >= self.failure_threshold:
                self._set_state('open')
                logger.warning(f"Circuit breaker {self.name} opened due to {current_count} failures")
    
    def __call__(self, func: Callable) -> Callable:
        """데코레이터로 사용"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.can_execute():
                raise NotionAPIError(f"Circuit breaker {self.name} is open")
            
            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure(e)
                raise
        
        return wrapper


# 기본 설정들
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=getattr(settings, 'NOTION_MAX_RETRIES', 3),
    backoff_strategy=JitteredExponentialBackoff(
        base_delay=getattr(settings, 'NOTION_RETRY_DELAY', 1.0),
        max_delay=60.0,
        multiplier=2.0,
        jitter_ratio=0.1
    )
)

# 전역 재시도 실행기
retry_executor = RetryExecutor(DEFAULT_RETRY_CONFIG)

# 기본 서킷 브레이커
notion_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=300,  # 5분
    expected_exception=NotionAPIError,
    name="notion_api"
)