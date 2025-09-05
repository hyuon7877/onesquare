"""
OneSquare 통합 캘린더 시스템 - Django Forms
"""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    CalendarEvent, CalendarCategory, EventAttendee, 
    CalendarSettings, CustomUser
)

User = get_user_model()


class CalendarEventForm(forms.ModelForm):
    """캘린더 이벤트 생성/수정 폼"""
    
    # 참석자 선택을 위한 다중 선택 필드
    attendee_users = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='참석자'
    )
    
    class Meta:
        model = CalendarEvent
        fields = [
            'title', 'description', 'category', 'start_datetime', 'end_datetime',
            'is_all_day', 'event_type', 'priority', 'location', 'url',
            'recurrence_type', 'recurrence_end_date', 'reminder_minutes'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '이벤트 제목을 입력하세요'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '이벤트 설명을 입력하세요'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'start_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'is_all_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '장소를 입력하세요'
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://'
            }),
            'recurrence_type': forms.Select(attrs={'class': 'form-select'}),
            'recurrence_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'reminder_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 1440  # 24시간
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 사용자가 접근할 수 있는 카테고리만 표시
        if self.user:
            accessible_categories = []
            for category in CalendarCategory.objects.filter(is_active=True):
                if category.can_access(self.user):
                    accessible_categories.append(category.id)
            
            self.fields['category'].queryset = CalendarCategory.objects.filter(
                id__in=accessible_categories
            )
            
            # 같은 조직의 사용자만 참석자로 선택 가능
            if self.user.user_type in ['SUPER_ADMIN', 'MANAGER']:
                # 관리자는 모든 사용자 선택 가능
                attendee_queryset = CustomUser.objects.filter(is_active=True)
            elif self.user.user_type == 'TEAM_MEMBER':
                # 팀원은 같은 회사 사용자만
                attendee_queryset = CustomUser.objects.filter(
                    is_active=True,
                    user_type__in=['SUPER_ADMIN', 'MANAGER', 'TEAM_MEMBER']
                )
            else:
                # 파트너/도급사는 관련 사용자만
                attendee_queryset = CustomUser.objects.filter(
                    is_active=True,
                    user_type__in=['SUPER_ADMIN', 'MANAGER']
                )
            
            self.fields['attendee_users'].queryset = attendee_queryset.exclude(id=self.user.id)
        
        # 기존 이벤트 수정 시 참석자 정보 로드
        if self.instance.pk:
            self.fields['attendee_users'].initial = self.instance.attendees.all()
    
    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        is_all_day = cleaned_data.get('is_all_day')
        recurrence_type = cleaned_data.get('recurrence_type')
        recurrence_end_date = cleaned_data.get('recurrence_end_date')
        
        # 시작일시 검증
        if start_datetime and start_datetime < timezone.now():
            if not self.instance.pk:  # 새 이벤트인 경우만
                raise ValidationError('과거 시간으로는 일정을 생성할 수 없습니다.')
        
        # 종료일시 검증
        if start_datetime and end_datetime:
            if end_datetime <= start_datetime:
                raise ValidationError('종료일시는 시작일시보다 늦어야 합니다.')
            
            # 종일 일정이 아닌 경우 최소 15분 간격
            if not is_all_day:
                duration = (end_datetime - start_datetime).total_seconds() / 60
                if duration < 15:
                    raise ValidationError('일정은 최소 15분 이상이어야 합니다.')
        
        # 반복 일정 검증
        if recurrence_type and recurrence_type != CalendarEvent.RecurrenceType.NONE:
            if not recurrence_end_date:
                raise ValidationError('반복 일정은 종료일을 설정해야 합니다.')
            
            if start_datetime and recurrence_end_date < start_datetime.date():
                raise ValidationError('반복 종료일은 시작일 이후여야 합니다.')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # 작성자 설정
        if not instance.pk and self.user:
            instance.creator = self.user
        
        if commit:
            instance.save()
            
            # 참석자 설정
            attendee_users = self.cleaned_data.get('attendee_users', [])
            
            # 기존 참석자 삭제 (작성자 제외)
            EventAttendee.objects.filter(
                event=instance
            ).exclude(user=instance.creator).delete()
            
            # 새 참석자 추가
            for user in attendee_users:
                EventAttendee.objects.get_or_create(
                    event=instance,
                    user=user,
                    defaults={'status': EventAttendee.Status.PENDING}
                )
            
            # 작성자도 참석자로 추가 (자동 수락 상태)
            EventAttendee.objects.get_or_create(
                event=instance,
                user=instance.creator,
                defaults={'status': EventAttendee.Status.ACCEPTED}
            )
        
        return instance


class QuickEventForm(forms.ModelForm):
    """빠른 이벤트 생성 폼 (최소 필드)"""
    
    class Meta:
        model = CalendarEvent
        fields = ['title', 'start_datetime', 'end_datetime', 'is_all_day']
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '이벤트 제목'
            }),
            'start_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'is_all_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.user:
            instance.creator = self.user
        
        # 기본값 설정
        instance.event_type = CalendarEvent.EventType.WORK
        instance.priority = CalendarEvent.Priority.MEDIUM
        
        if commit:
            instance.save()
            
            # 작성자를 참석자로 추가
            EventAttendee.objects.get_or_create(
                event=instance,
                user=instance.creator,
                defaults={'status': EventAttendee.Status.ACCEPTED}
            )
        
        return instance


class EventAttendeeResponseForm(forms.ModelForm):
    """참석자 응답 폼"""
    
    class Meta:
        model = EventAttendee
        fields = ['status', 'notes']
        
        widgets = {
            'status': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': '메모를 입력하세요 (선택사항)'
            }),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.response_at = timezone.now()
        
        if commit:
            instance.save()
        
        return instance


class CalendarSettingsForm(forms.ModelForm):
    """캘린더 설정 폼"""
    
    class Meta:
        model = CalendarSettings
        fields = [
            'default_view', 'work_start_time', 'work_end_time',
            'default_reminder_minutes', 'email_notifications', 
            'push_notifications', 'show_weekends', 'show_declined_events'
        ]
        
        widgets = {
            'default_view': forms.Select(attrs={'class': 'form-select'}),
            'work_start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'work_end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'default_reminder_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 1440
            }),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_weekends': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_declined_events': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        work_start_time = cleaned_data.get('work_start_time')
        work_end_time = cleaned_data.get('work_end_time')
        
        if work_start_time and work_end_time:
            if work_end_time <= work_start_time:
                raise ValidationError('업무 종료시간은 시작시간보다 늦어야 합니다.')
        
        return cleaned_data


class CalendarCategoryForm(forms.ModelForm):
    """캘린더 카테고리 폼 (관리자용)"""
    
    class Meta:
        model = CalendarCategory
        fields = ['name', 'color', 'description', 'accessible_user_types', 'is_active']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '카테고리 이름'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'accessible_user_types': forms.CheckboxSelectMultiple(
                choices=[
                    ('SUPER_ADMIN', '최고관리자'),
                    ('MANAGER', '중간관리자'),
                    ('TEAM_MEMBER', '팀원'),
                    ('PARTNER', '파트너'),
                    ('CONTRACTOR', '도급사'),
                    ('CUSTOM', '커스텀'),
                ]
            ),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_accessible_user_types(self):
        """사용자 타입 검증 및 변환"""
        user_types = self.cleaned_data.get('accessible_user_types')
        if isinstance(user_types, str):
            # 문자열인 경우 리스트로 변환
            return [user_types] if user_types else []
        return list(user_types) if user_types else []


class CalendarFilterForm(forms.Form):
    """캘린더 필터 폼"""
    
    category = forms.ModelChoiceField(
        queryset=CalendarCategory.objects.filter(is_active=True),
        required=False,
        empty_label="모든 카테고리",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    event_type = forms.ChoiceField(
        choices=[('', '모든 타입')] + list(CalendarEvent.EventType.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        choices=[('', '모든 우선순위')] + list(CalendarEvent.Priority.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    creator = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True),
        required=False,
        empty_label="모든 작성자",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # 사용자가 접근 가능한 카테고리만 표시
            accessible_categories = []
            for category in CalendarCategory.objects.filter(is_active=True):
                if category.can_access(user):
                    accessible_categories.append(category.id)
            
            self.fields['category'].queryset = CalendarCategory.objects.filter(
                id__in=accessible_categories
            )
            
            # 작성자 필터도 권한에 따라 제한
            if user.user_type in ['SUPER_ADMIN', 'MANAGER']:
                creator_queryset = CustomUser.objects.filter(is_active=True)
            else:
                # 일반 사용자는 자신과 관련된 사용자만
                creator_queryset = CustomUser.objects.filter(
                    id=user.id,
                    is_active=True
                )
            
            self.fields['creator'].queryset = creator_queryset
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError('시작일이 종료일보다 늦을 수 없습니다.')
        
        return cleaned_data


class EventSearchForm(forms.Form):
    """이벤트 검색 폼"""
    
    query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '제목, 설명, 장소에서 검색...'
        })
    )
    
    search_type = forms.ChoiceField(
        choices=[
            ('all', '전체'),
            ('title', '제목'),
            ('description', '설명'),
            ('location', '장소'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    def clean_query(self):
        query = self.cleaned_data.get('query')
        if query:
            return query.strip()
        return query