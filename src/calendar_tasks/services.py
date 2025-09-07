"""캘린더 데이터 프리페칭 및 최적화 서비스"""
from django.db.models import Q, Prefetch, Count, F
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta, date
import logging
from typing import Dict, List, Optional, Tuple

from .models import Calendar, Event, RecurringEvent, Task, EventReminder

logger = logging.getLogger(__name__)


class CalendarPrefetchService:
    """캘린더 데이터 프리페칭 및 캐싱 서비스"""
    
    CACHE_TTL = {
        'weekly': 600,    # 10분
        'daily': 300,     # 5분
        'summary': 60,    # 1분
        'upcoming': 120,  # 2분
    }
    
    @classmethod
    def prefetch_user_calendars(cls, user) -> 'QuerySet':
        """사용자 캘린더 최적화 조회"""
        return Calendar.objects.filter(
            Q(owner=user) | Q(shared_with=user)
        ).distinct().select_related('owner').prefetch_related(
            'shared_with',
            'shares'
        )
    
    @classmethod
    def prefetch_events_for_range(cls, calendars, start_date: datetime, end_date: datetime) -> 'QuerySet':
        """날짜 범위에 대한 이벤트 최적화 조회"""
        return Event.objects.filter(
            calendar__in=calendars,
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related(
            'calendar',
            'creator'
        ).prefetch_related(
            'attendees',
            Prefetch('task_detail', 
                queryset=Task.objects.select_related('completed_by')
            ),
            Prefetch('reminders',
                queryset=EventReminder.objects.filter(is_sent=False).order_by('remind_at')
            ),
            Prefetch('recurrence',
                queryset=RecurringEvent.objects.all()
            )
        ).order_by('start_date', 'priority')
    
    @classmethod
    def get_week_boundaries(cls, target_date: date) -> Tuple[datetime, datetime]:
        """주의 시작과 끝 시간 계산"""
        week_start = target_date - timedelta(days=target_date.weekday())
        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        return (
            timezone.make_aware(datetime.combine(week_start, datetime.min.time())),
            timezone.make_aware(datetime.combine(week_end.date(), datetime.max.time()))
        )
    
    @classmethod
    def get_day_boundaries(cls, target_date: date) -> Tuple[datetime, datetime]:
        """일의 시작과 끝 시간 계산"""
        return (
            timezone.make_aware(datetime.combine(target_date, datetime.min.time())),
            timezone.make_aware(datetime.combine(target_date, datetime.max.time()))
        )
    
    @classmethod
    def batch_cache_events(cls, user, date_range: str = 'week'):
        """이벤트 일괄 캐싱"""
        try:
            today = date.today()
            
            if date_range == 'week':
                start, end = cls.get_week_boundaries(today)
                cache_key_prefix = f'batch_week_{user.id}'
            else:  # day
                start, end = cls.get_day_boundaries(today)
                cache_key_prefix = f'batch_day_{user.id}'
            
            # 캘린더 조회
            calendars = cls.prefetch_user_calendars(user)
            
            # 이벤트 조회
            events = cls.prefetch_events_for_range(calendars, start, end)
            
            # 캐시 저장
            cache_data = {
                'calendars': list(calendars.values('id', 'name', 'color', 'is_default')),
                'events': list(events.values(
                    'id', 'title', 'description', 'location',
                    'start_date', 'end_date', 'all_day',
                    'is_task', 'priority', 'status', 'progress',
                    'calendar__id', 'calendar__name', 'calendar__color',
                    'creator__username'
                )),
                'cached_at': timezone.now().isoformat()
            }
            
            ttl = cls.CACHE_TTL.get(date_range, 300)
            cache.set(cache_key_prefix, cache_data, ttl)
            
            logger.info(f"Batch cached {len(cache_data['events'])} events for user {user.id}")
            return cache_data
            
        except Exception as e:
            logger.error(f"Batch cache error: {str(e)}")
            return None
    
    @classmethod
    def warmup_cache(cls, user):
        """캐시 워밍업 - 자주 사용되는 데이터 미리 로드"""
        try:
            # 이번 주 데이터
            cls.batch_cache_events(user, 'week')
            
            # 오늘 데이터
            cls.batch_cache_events(user, 'day')
            
            # 다가오는 이벤트
            cls.cache_upcoming_events(user)
            
            logger.info(f"Cache warmed up for user {user.id}")
            
        except Exception as e:
            logger.error(f"Cache warmup error: {str(e)}")
    
    @classmethod
    def cache_upcoming_events(cls, user, days: int = 7):
        """다가오는 이벤트 캐싱"""
        cache_key = f'upcoming_events_{user.id}_{days}'
        
        calendars = cls.prefetch_user_calendars(user)
        end_date = timezone.now() + timedelta(days=days)
        
        events = Event.objects.filter(
            calendar__in=calendars,
            start_date__gte=timezone.now(),
            start_date__lte=end_date
        ).select_related('calendar').order_by('start_date')[:20]
        
        events_data = [{
            'id': event.id,
            'title': event.title,
            'start': event.start_date.isoformat(),
            'calendar': event.calendar.name,
            'is_task': event.is_task,
            'priority': event.priority
        } for event in events]
        
        cache.set(cache_key, events_data, cls.CACHE_TTL['upcoming'])
        return events_data
    
    @classmethod
    def invalidate_cache(cls, user, scope: str = 'all'):
        """캐시 무효화"""
        patterns = []
        
        if scope in ['all', 'weekly']:
            patterns.append(f'weekly_calendar_{user.id}_*')
            patterns.append(f'batch_week_{user.id}')
        
        if scope in ['all', 'daily']:
            patterns.append(f'daily_calendar_{user.id}_*')
            patterns.append(f'batch_day_{user.id}')
        
        if scope in ['all', 'upcoming']:
            patterns.append(f'upcoming_events_{user.id}_*')
        
        for pattern in patterns:
            cache.delete_pattern(pattern)
        
        logger.info(f"Cache invalidated for user {user.id}, scope: {scope}")


class CalendarErrorRecovery:
    """캘린더 에러 복구 서비스"""
    
    @staticmethod
    def safe_get_events(calendars, start_date, end_date, fallback_days: int = 7):
        """안전한 이벤트 조회 with 폴백"""
        try:
            return Event.objects.filter(
                calendar__in=calendars,
                start_date__lte=end_date,
                end_date__gte=start_date
            ).select_related('calendar', 'creator')
            
        except Exception as e:
            logger.error(f"Event query failed: {str(e)}")
            
            # 폴백: 더 작은 범위로 재시도
            try:
                fallback_end = start_date + timedelta(days=fallback_days)
                return Event.objects.filter(
                    calendar__in=calendars,
                    start_date__lte=fallback_end,
                    end_date__gte=start_date
                ).select_related('calendar')[:100]  # 제한된 수만 반환
                
            except Exception as fallback_error:
                logger.critical(f"Fallback query also failed: {str(fallback_error)}")
                return Event.objects.none()
    
    @staticmethod
    def handle_recurring_events_safely(recurring_events, start_date, end_date, max_occurrences: int = 100):
        """안전한 반복 이벤트 처리"""
        all_occurrences = []
        
        for recurrence in recurring_events:
            try:
                occurrences = recurrence.generate_occurrences(start_date, end_date)
                
                # 무한 반복 방지
                if len(occurrences) > max_occurrences:
                    logger.warning(f"Too many occurrences for event {recurrence.event.id}, limiting to {max_occurrences}")
                    occurrences = occurrences[:max_occurrences]
                
                all_occurrences.extend(occurrences)
                
            except Exception as e:
                logger.error(f"Failed to generate occurrences for event {recurrence.event.id}: {str(e)}")
                continue
        
        return all_occurrences
    
    @staticmethod
    def validate_event_data(event_data: Dict) -> Dict:
        """이벤트 데이터 유효성 검증 및 수정"""
        required_fields = ['title', 'start', 'end']
        
        for field in required_fields:
            if field not in event_data:
                logger.warning(f"Missing required field '{field}' in event data")
                
                # 기본값 설정
                if field == 'title':
                    event_data[field] = 'Untitled Event'
                elif field in ['start', 'end']:
                    event_data[field] = timezone.now().isoformat()
        
        # 날짜 유효성 검증
        try:
            start = datetime.fromisoformat(event_data['start'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(event_data['end'].replace('Z', '+00:00'))
            
            if end < start:
                logger.warning(f"Invalid date range for event: end before start")
                event_data['end'] = event_data['start']
                
        except (ValueError, KeyError) as e:
            logger.error(f"Date validation failed: {str(e)}")
        
        return event_data
    
    @staticmethod
    def create_error_response(error_msg: str, detail: str = None) -> Dict:
        """표준화된 에러 응답 생성"""
        response = {
            'success': False,
            'error': error_msg,
            'timestamp': timezone.now().isoformat()
        }
        
        if detail:
            response['detail'] = detail
        
        return response