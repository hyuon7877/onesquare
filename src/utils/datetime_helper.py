"""
날짜/시간 관련 공통 유틸리티
46개 모듈에서 사용되는 datetime 기능 통합
"""

from datetime import datetime, timedelta, timezone
from django.utils import timezone as dj_timezone
from django.conf import settings
import pytz


def get_now():
    """현재 시간 반환 (타임존 적용)"""
    return dj_timezone.now()


def get_today():
    """오늘 날짜 반환 (타임존 적용)"""
    return get_now().date()


def get_local_now():
    """로컬 타임존 기준 현재 시간"""
    return dj_timezone.localtime(get_now())


def parse_date(date_string, format='%Y-%m-%d'):
    """문자열을 날짜로 파싱"""
    try:
        return datetime.strptime(date_string, format).date()
    except (ValueError, TypeError):
        return None


def parse_datetime(datetime_string, format='%Y-%m-%d %H:%M:%S'):
    """문자열을 날짜시간으로 파싱"""
    try:
        naive_dt = datetime.strptime(datetime_string, format)
        return dj_timezone.make_aware(naive_dt)
    except (ValueError, TypeError):
        return None


def format_date(date_obj, format='%Y-%m-%d'):
    """날짜를 문자열로 포맷"""
    if not date_obj:
        return ''
    return date_obj.strftime(format)


def format_datetime(datetime_obj, format='%Y-%m-%d %H:%M:%S'):
    """날짜시간을 문자열로 포맷"""
    if not datetime_obj:
        return ''
    local_dt = dj_timezone.localtime(datetime_obj)
    return local_dt.strftime(format)


def format_korean_date(date_obj):
    """한국식 날짜 포맷 (2025년 9월 5일)"""
    if not date_obj:
        return ''
    return f"{date_obj.year}년 {date_obj.month}월 {date_obj.day}일"


def format_korean_datetime(datetime_obj):
    """한국식 날짜시간 포맷"""
    if not datetime_obj:
        return ''
    local_dt = dj_timezone.localtime(datetime_obj)
    return f"{local_dt.year}년 {local_dt.month}월 {local_dt.day}일 {local_dt.hour:02d}:{local_dt.minute:02d}"


def add_days(date_obj, days):
    """날짜에 일수 더하기"""
    return date_obj + timedelta(days=days)


def add_hours(datetime_obj, hours):
    """날짜시간에 시간 더하기"""
    return datetime_obj + timedelta(hours=hours)


def get_date_range(start_date, end_date):
    """두 날짜 사이의 모든 날짜 리스트"""
    days = (end_date - start_date).days + 1
    return [start_date + timedelta(days=i) for i in range(days)]


def get_weekday_korean(date_obj):
    """요일을 한국어로 반환"""
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    return weekdays[date_obj.weekday()]


def get_month_range(year, month):
    """특정 월의 시작일과 종료일"""
    import calendar
    first_day = datetime(year, month, 1).date()
    last_day = datetime(year, month, calendar.monthrange(year, month)[1]).date()
    return first_day, last_day


def get_quarter(date_obj):
    """분기 반환 (1, 2, 3, 4)"""
    return (date_obj.month - 1) // 3 + 1


def is_weekend(date_obj):
    """주말 여부 확인"""
    return date_obj.weekday() >= 5


def is_business_day(date_obj):
    """영업일 여부 확인 (주말 제외)"""
    return date_obj.weekday() < 5


def calculate_age(birth_date):
    """나이 계산"""
    today = get_today()
    age = today.year - birth_date.year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    return age


def get_time_difference(start, end, unit='seconds'):
    """두 시간 사이의 차이 계산"""
    diff = end - start
    if unit == 'seconds':
        return diff.total_seconds()
    elif unit == 'minutes':
        return diff.total_seconds() / 60
    elif unit == 'hours':
        return diff.total_seconds() / 3600
    elif unit == 'days':
        return diff.days
    return diff


def format_duration(seconds):
    """초를 읽기 좋은 형식으로 변환"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}시간 {minutes}분"
    elif minutes > 0:
        return f"{minutes}분 {secs}초"
    else:
        return f"{secs}초"


def get_notion_datetime_format(datetime_obj):
    """Notion API용 날짜시간 포맷"""
    if not datetime_obj:
        return None
    return datetime_obj.isoformat()


def parse_notion_datetime(notion_datetime):
    """Notion API 날짜시간 파싱"""
    if not notion_datetime:
        return None
    try:
        return datetime.fromisoformat(notion_datetime.replace('Z', '+00:00'))
    except:
        return None