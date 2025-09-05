from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.leave_management.models import LeaveType, LeaveBalance, Holiday
from apps.auth_system.models import CustomUser
import datetime

User = get_user_model()


class Command(BaseCommand):
    help = '연차 관리 시스템 초기 데이터 설정'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=timezone.now().year,
            help='설정할 연도 (기본: 현재 연도)'
        )
    
    def handle(self, *args, **options):
        year = options['year']
        
        self.stdout.write(f'{year}년 연차 관리 시스템 설정을 시작합니다...')
        
        # 1. 연차 유형 생성
        self.setup_leave_types()
        
        # 2. 사용자별 연차 잔여일수 설정
        self.setup_user_balances(year)
        
        # 3. 기본 공휴일 설정
        self.setup_holidays(year)
        
        self.stdout.write(
            self.style.SUCCESS(f'{year}년 연차 관리 시스템 설정이 완료되었습니다!')
        )
    
    def setup_leave_types(self):
        """연차 유형 설정"""
        leave_types = [
            ('annual', '연차', 15, True),
            ('sick', '병가', 30, False),
            ('special', '특별휴가', 5, True),
            ('half_day', '반차', None, True),
            ('replacement', '대체휴무', None, True),
        ]
        
        for code, name, max_days, requires_approval in leave_types:
            leave_type, created = LeaveType.objects.get_or_create(
                name=code,
                defaults={
                    'description': f'{name} 설명',
                    'max_days': max_days,
                    'requires_approval': requires_approval,
                }
            )
            
            if created:
                self.stdout.write(f'✓ 연차 유형 생성: {name}')
            else:
                self.stdout.write(f'- 연차 유형 존재: {name}')
    
    def setup_user_balances(self, year):
        """사용자별 연차 잔여일수 설정"""
        users = CustomUser.objects.filter(is_active=True)
        
        for user in users:
            # 사용자 그룹에 따른 연차 할당
            if user.groups.filter(name='최고관리자').exists():
                total_days = 20.0
            elif user.groups.filter(name='중간관리자').exists():
                total_days = 18.0
            elif user.groups.filter(name='팀원').exists():
                total_days = 15.0
            else:
                # 파트너, 도급사는 연차 시스템 사용 안함
                continue
            
            balance, created = LeaveBalance.objects.get_or_create(
                user=user,
                year=year,
                defaults={
                    'total_annual_days': total_days,
                    'remaining_annual_days': total_days,
                }
            )
            
            if created:
                self.stdout.write(f'✓ {user.username} 연차 설정: {total_days}일')
            else:
                self.stdout.write(f'- {user.username} 연차 존재: {balance.total_annual_days}일')
    
    def setup_holidays(self, year):
        """기본 공휴일 설정"""
        holidays = [
            (1, 1, '신정'),
            (3, 1, '삼일절'),
            (5, 5, '어린이날'),
            (6, 6, '현충일'),
            (8, 15, '광복절'),
            (10, 3, '개천절'),
            (10, 9, '한글날'),
            (12, 25, '크리스마스'),
        ]
        
        # 추석, 설날 등 음력 공휴일은 매년 수동 설정 필요
        lunar_holidays = [
            # 예시: 2024년 기준
            (2, 9, '설날 연휴'),
            (2, 10, '설날'),
            (2, 11, '설날 연휴'),
            (2, 12, '설날 대체휴일'),
            (4, 10, '국회의원선거일'),
            (5, 15, '부처님오신날'),
            (9, 16, '추석 연휴'),
            (9, 17, '추석'),
            (9, 18, '추석 연휴'),
        ]
        
        all_holidays = holidays + (lunar_holidays if year == 2024 else [])
        
        for month, day, name in all_holidays:
            try:
                date = datetime.date(year, month, day)
                holiday, created = Holiday.objects.get_or_create(
                    date=date,
                    defaults={
                        'name': name,
                        'is_public_holiday': True,
                    }
                )
                
                if created:
                    self.stdout.write(f'✓ 공휴일 생성: {date} {name}')
                else:
                    self.stdout.write(f'- 공휴일 존재: {date} {name}')
                    
            except ValueError:
                # 잘못된 날짜는 건너뜀
                self.stdout.write(f'⚠ 잘못된 날짜: {year}-{month:02d}-{day:02d}')
    
    def setup_workflow_rules(self):
        """승인 워크플로우 규칙 설정"""
        # 추후 구현: 자동 승인 규칙, 다단계 승인 등
        pass