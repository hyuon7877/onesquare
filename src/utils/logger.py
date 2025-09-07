"""
로깅 관련 공통 유틸리티
31개 모듈에서 사용되는 logging 기능 통합
"""

import logging
import os
from datetime import datetime
from django.conf import settings
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class ColoredFormatter(logging.Formatter):
    """컬러 출력을 위한 포맷터"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def get_logger(name, level=None, log_file=None):
    """커스텀 로거 생성"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # 로그 레벨 설정
        if level is None:
            level = logging.DEBUG if settings.DEBUG else logging.INFO
        logger.setLevel(level)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        # 포맷 설정
        if settings.DEBUG:
            formatter = ColoredFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # 파일 핸들러 (옵션)
        if log_file:
            file_handler = get_file_handler(log_file, level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    
    return logger


def get_file_handler(log_file, level=logging.INFO):
    """파일 핸들러 생성"""
    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_path = os.path.join(log_dir, log_file)
    
    # 10MB 단위로 로테이션
    handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    handler.setLevel(level)
    return handler


def get_daily_logger(name):
    """일별 로그 파일 생성 로거"""
    logger = logging.getLogger(f"{name}_daily")
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        log_dir = os.path.join(settings.BASE_DIR, 'logs', 'daily')
        os.makedirs(log_dir, exist_ok=True)
        
        # 매일 자정에 로테이션
        handler = TimedRotatingFileHandler(
            os.path.join(log_dir, f"{name}.log"),
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def log_function_call(func):
    """함수 호출 로깅 데코레이터"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        func_name = func.__name__
        logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func_name} returned: {result}")
            return result
        except Exception as e:
            logger.error(f"{func_name} raised exception: {e}")
            raise
    
    return wrapper


def log_performance(func):
    """성능 측정 로깅 데코레이터"""
    def wrapper(*args, **kwargs):
        import time
        logger = get_logger(func.__module__)
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.info(f"{func.__name__} took {elapsed:.3f} seconds")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.3f} seconds: {e}")
            raise
    
    return wrapper


def log_user_action(user, action, details=None):
    """사용자 액션 로깅"""
    logger = get_daily_logger('user_actions')
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'user': str(user),
        'action': action,
    }
    
    if details:
        log_entry['details'] = details
    
    logger.info(log_entry)


def log_api_request(request, response=None, error=None):
    """API 요청/응답 로깅"""
    logger = get_daily_logger('api_requests')
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'method': request.method,
        'path': request.path,
        'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
    }
    
    if response:
        log_entry['status_code'] = response.status_code
    
    if error:
        log_entry['error'] = str(error)
    
    logger.info(log_entry)


def log_notion_sync(operation, data=None, error=None):
    """Notion 동기화 로깅"""
    logger = get_daily_logger('notion_sync')
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'operation': operation,
    }
    
    if data:
        log_entry['data'] = data
    
    if error:
        log_entry['error'] = str(error)
        logger.error(log_entry)
    else:
        logger.info(log_entry)


def log_error_with_context(error, context=None):
    """컨텍스트 포함 에러 로깅"""
    logger = get_logger('errors')
    
    error_entry = {
        'timestamp': datetime.now().isoformat(),
        'error_type': type(error).__name__,
        'error_message': str(error),
    }
    
    if context:
        error_entry['context'] = context
    
    import traceback
    error_entry['traceback'] = traceback.format_exc()
    
    logger.error(error_entry)


def get_log_level(level_string):
    """문자열을 로그 레벨로 변환"""
    levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL,
    }
    return levels.get(level_string.upper(), logging.INFO)