"""캘린더 쿼리 최적화를 위한 인덱스 추가"""
from django.db import migrations, models


class Migration(migrations.Migration):
    
    dependencies = [
        ('calendar_tasks', '0001_initial'),
    ]
    
    operations = [
        # Event 모델 인덱스 최적화
        migrations.AddIndex(
            model_name='event',
            index=models.Index(
                fields=['calendar', 'start_date', 'end_date'],
                name='cal_date_range_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(
                fields=['is_task', 'status', 'end_date'],
                name='task_status_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(
                fields=['creator', 'start_date'],
                name='creator_date_idx'
            ),
        ),
        
        # Calendar 모델 인덱스
        migrations.AddIndex(
            model_name='calendar',
            index=models.Index(
                fields=['owner', 'is_default'],
                name='owner_default_idx'
            ),
        ),
        
        # RecurringEvent 인덱스
        migrations.AddIndex(
            model_name='recurringevent',
            index=models.Index(
                fields=['event', 'frequency'],
                name='recur_freq_idx'
            ),
        ),
        
        # Task 인덱스
        migrations.AddIndex(
            model_name='task',
            index=models.Index(
                fields=['event', 'completed_at'],
                name='task_complete_idx'
            ),
        ),
        
        # EventReminder 인덱스
        migrations.AddIndex(
            model_name='eventreminder',
            index=models.Index(
                fields=['user', 'remind_at', 'is_sent'],
                name='reminder_user_idx'
            ),
        ),
    ]