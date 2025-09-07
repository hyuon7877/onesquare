from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import Comment, Activity, Notification, Presence
from field_reports.models import FieldReport
import json

@login_required
def collaboration_home(request):
    """협업 메인 페이지"""
    context = {
        'activities': Activity.objects.filter(user=request.user).order_by('-timestamp')[:10],
        'notifications': Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5],
        'recent_comments': Comment.objects.filter(author=request.user).order_by('-created_at')[:5],
    }
    return render(request, 'collaboration/home.html', context)

@login_required
@require_http_methods(["GET", "POST"])
def comment_list(request, content_type_id, object_id):
    """댓글 목록 조회 및 작성"""
    content_type = get_object_or_404(ContentType, id=content_type_id)
    
    if request.method == 'GET':
        comments = Comment.objects.filter(
            content_type=content_type,
            object_id=object_id,
            parent__isnull=True,  # 최상위 댓글만
            is_deleted=False
        ).select_related('author').prefetch_related('replies', 'mentioned_users')
        
        comments_data = []
        for comment in comments:
            comment_data = {
                'id': comment.id,
                'author': {
                    'id': comment.author.id,
                    'username': comment.author.username,
                    'full_name': comment.author.get_full_name() or comment.author.username,
                },
                'content': comment.content,
                'is_edited': comment.is_edited,
                'created_at': comment.created_at.isoformat(),
                'updated_at': comment.updated_at.isoformat(),
                'mentioned_users': comment.get_mentioned_usernames(),
                'replies': []
            }
            
            # 답글 추가
            for reply in comment.get_replies():
                reply_data = {
                    'id': reply.id,
                    'author': {
                        'id': reply.author.id,
                        'username': reply.author.username,
                        'full_name': reply.author.get_full_name() or reply.author.username,
                    },
                    'content': reply.content,
                    'is_edited': reply.is_edited,
                    'created_at': reply.created_at.isoformat(),
                    'updated_at': reply.updated_at.isoformat(),
                    'mentioned_users': reply.get_mentioned_usernames(),
                }
                comment_data['replies'].append(reply_data)
            
            comments_data.append(comment_data)
        
        return JsonResponse({'comments': comments_data})
    
    else:  # POST
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        parent_id = data.get('parent_id')
        
        if not content:
            return JsonResponse({'error': '댓글 내용을 입력하세요.'}, status=400)
        
        comment = Comment.objects.create(
            content_type=content_type,
            object_id=object_id,
            author=request.user,
            content=content,
            parent_id=parent_id if parent_id else None
        )
        
        # 활동 기록
        Activity.objects.create(
            user=request.user,
            activity_type='comment_added',
            content_type=content_type,
            object_id=object_id,
            description=f"{content[:50]}..."
        )
        
        # 멘션 알림 생성
        for mentioned_user in comment.mentioned_users.all():
            if mentioned_user != request.user:
                Notification.objects.create(
                    recipient=mentioned_user,
                    sender=request.user,
                    notification_type='mention',
                    title='멘션 알림',
                    message=f'{request.user.get_full_name() or request.user.username}님이 댓글에서 멘션했습니다.',
                    content_type=content_type,
                    object_id=object_id,
                    action_url=f'#{comment.id}'
                )
        
        # 답글인 경우 원 댓글 작성자에게 알림
        if comment.parent and comment.parent.author != request.user:
            Notification.objects.create(
                recipient=comment.parent.author,
                sender=request.user,
                notification_type='reply',
                title='답글 알림',
                message=f'{request.user.get_full_name() or request.user.username}님이 답글을 달았습니다.',
                content_type=content_type,
                object_id=object_id,
                action_url=f'#{comment.id}'
            )
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'author': {
                    'id': comment.author.id,
                    'username': comment.author.username,
                    'full_name': comment.author.get_full_name() or comment.author.username,
                },
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'mentioned_users': comment.get_mentioned_usernames(),
            }
        })


@login_required
@require_http_methods(["PUT", "DELETE"])
def comment_detail(request, comment_id):
    """댓글 수정 및 삭제"""
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    
    if request.method == 'PUT':
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'error': '댓글 내용을 입력하세요.'}, status=400)
        
        comment.content = content
        comment.is_edited = True
        comment.save()
        
        # 활동 기록
        Activity.objects.create(
            user=request.user,
            activity_type='comment_edited',
            content_type=comment.content_type,
            object_id=comment.object_id,
            description=f"{content[:50]}..."
        )
        
        return JsonResponse({'success': True, 'message': '댓글이 수정되었습니다.'})
    
    else:  # DELETE
        comment.is_deleted = True
        comment.save()
        
        # 활동 기록
        Activity.objects.create(
            user=request.user,
            activity_type='comment_deleted',
            content_type=comment.content_type,
            object_id=comment.object_id
        )
        
        return JsonResponse({'success': True, 'message': '댓글이 삭제되었습니다.'})


@login_required
def activity_feed(request):
    """활동 피드"""
    # 필터링
    filter_type = request.GET.get('type', 'all')
    user_id = request.GET.get('user_id')
    
    activities = Activity.objects.select_related('user').prefetch_related('related_users')
    
    if filter_type != 'all':
        activities = activities.filter(activity_type=filter_type)
    
    if user_id:
        activities = activities.filter(Q(user_id=user_id) | Q(related_users__id=user_id))
    
    # 페이지네이션
    page = request.GET.get('page', 1)
    paginator = Paginator(activities, 20)
    page_obj = paginator.get_page(page)
    
    activities_data = []
    for activity in page_obj:
        activity_data = {
            'id': activity.id,
            'user': {
                'id': activity.user.id,
                'username': activity.user.username,
                'full_name': activity.user.get_full_name() or activity.user.username,
            },
            'type': activity.activity_type,
            'type_display': activity.get_activity_type_display(),
            'icon': activity.get_icon(),
            'message': activity.get_message(),
            'description': activity.description,
            'created_at': activity.created_at.isoformat(),
            'metadata': activity.metadata,
        }
        activities_data.append(activity_data)
    
    return JsonResponse({
        'activities': activities_data,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })


@login_required
def notification_list(request):
    """알림 목록"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender')
    
    # 읽지 않은 알림만 필터링
    unread_only = request.GET.get('unread_only', 'false') == 'true'
    if unread_only:
        notifications = notifications.filter(is_read=False)
    
    # 페이지네이션
    page = request.GET.get('page', 1)
    paginator = Paginator(notifications, 10)
    page_obj = paginator.get_page(page)
    
    notifications_data = []
    for notification in page_obj:
        notification_data = {
            'id': notification.id,
            'type': notification.notification_type,
            'type_display': notification.get_notification_type_display(),
            'icon': notification.get_icon(),
            'title': notification.title,
            'message': notification.message,
            'is_read': notification.is_read,
            'action_url': notification.action_url,
            'created_at': notification.created_at.isoformat(),
            'read_at': notification.read_at.isoformat() if notification.read_at else None,
        }
        
        if notification.sender:
            notification_data['sender'] = {
                'id': notification.sender.id,
                'username': notification.sender.username,
                'full_name': notification.sender.get_full_name() or notification.sender.username,
            }
        
        notifications_data.append(notification_data)
    
    # 읽지 않은 알림 개수
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'notifications': notifications_data,
        'unread_count': unread_count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
    })


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """알림 읽음 처리"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )
    notification.mark_as_read()
    
    return JsonResponse({'success': True, 'message': '알림을 읽음으로 표시했습니다.'})


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """모든 알림 읽음 처리"""
    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return JsonResponse({'success': True, 'message': '모든 알림을 읽음으로 표시했습니다.'})


@login_required
@require_http_methods(["POST"])
def update_presence(request):
    """사용자 상태 업데이트"""
    data = json.loads(request.body)
    
    presence, created = Presence.objects.get_or_create(user=request.user)
    
    # 상태 업데이트
    status = data.get('status')
    if status and status in dict(Presence.STATUS_CHOICES):
        presence.status = status
    
    # 현재 페이지 업데이트
    current_page = data.get('current_page')
    if current_page:
        presence.current_page = current_page
    
    # 타이핑 상태 업데이트
    is_typing = data.get('is_typing', False)
    typing_in = data.get('typing_in', '')
    presence.set_typing(is_typing, typing_in)
    
    presence.update_activity()
    
    return JsonResponse({
        'success': True,
        'status': presence.status,
        'last_seen': presence.last_seen.isoformat()
    })


@login_required
def get_online_users(request):
    """온라인 사용자 목록"""
    # 최근 5분 이내 활동한 사용자
    five_minutes_ago = timezone.now() - timezone.timedelta(minutes=5)
    
    online_users = Presence.objects.filter(
        last_seen__gte=five_minutes_ago
    ).exclude(
        status='offline'
    ).select_related('user')
    
    users_data = []
    for presence in online_users:
        user_data = {
            'id': presence.user.id,
            'username': presence.user.username,
            'full_name': presence.user.get_full_name() or presence.user.username,
            'status': presence.status,
            'status_display': presence.get_status_display(),
            'current_page': presence.current_page,
            'is_typing': presence.is_typing,
            'typing_in': presence.typing_in,
            'last_seen': presence.last_seen.isoformat(),
        }
        users_data.append(user_data)
    
    return JsonResponse({
        'online_users': users_data,
        'count': len(users_data)
    })


@login_required
def search_users(request):
    """사용자 검색 (멘션용)"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'users': []})
    
    from django.contrib.auth.models import User
    
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id)[:10]
    
    users_data = []
    for user in users:
        user_data = {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
        }
        users_data.append(user_data)
    
    return JsonResponse({'users': users_data})
