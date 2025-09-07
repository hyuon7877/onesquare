/**
 * WebSocket 매니저 - 실시간 통신 관리
 */
class WebSocketManager {
    constructor() {
        this.sockets = {};
        this.reconnectAttempts = {};
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // 1초
        this.heartbeatInterval = 30000; // 30초
        this.heartbeatTimers = {};
    }

    /**
     * WebSocket 연결 생성
     */
    connect(name, url, handlers = {}) {
        if (this.sockets[name]) {
            console.warn(`WebSocket ${name} already exists`);
            return this.sockets[name];
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}${url}`;
        
        const socket = new WebSocket(wsUrl);
        this.sockets[name] = socket;
        this.reconnectAttempts[name] = 0;

        // 연결 열림
        socket.onopen = (event) => {
            console.log(`WebSocket ${name} connected`);
            this.reconnectAttempts[name] = 0;
            
            // 하트비트 시작
            this.startHeartbeat(name);
            
            if (handlers.onOpen) {
                handlers.onOpen(event);
            }
        };

        // 메시지 수신
        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                console.log(`WebSocket ${name} received:`, data);
                
                if (data.type === 'heartbeat_ack') {
                    // 하트비트 응답 처리
                    return;
                }
                
                if (handlers.onMessage) {
                    handlers.onMessage(data);
                }
                
                // 메시지 타입별 핸들러
                if (handlers[data.type]) {
                    handlers[data.type](data);
                }
            } catch (error) {
                console.error(`WebSocket ${name} message parse error:`, error);
            }
        };

        // 연결 닫힘
        socket.onclose = (event) => {
            console.log(`WebSocket ${name} closed`);
            delete this.sockets[name];
            
            // 하트비트 중지
            this.stopHeartbeat(name);
            
            if (handlers.onClose) {
                handlers.onClose(event);
            }
            
            // 자동 재연결
            if (!event.wasClean && this.reconnectAttempts[name] < this.maxReconnectAttempts) {
                this.reconnect(name, url, handlers);
            }
        };

        // 에러 발생
        socket.onerror = (error) => {
            console.error(`WebSocket ${name} error:`, error);
            
            if (handlers.onError) {
                handlers.onError(error);
            }
        };

        return socket;
    }

    /**
     * 메시지 전송
     */
    send(name, data) {
        const socket = this.sockets[name];
        
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            console.error(`WebSocket ${name} is not connected`);
            return false;
        }
        
        socket.send(JSON.stringify(data));
        return true;
    }

    /**
     * 연결 종료
     */
    disconnect(name) {
        const socket = this.sockets[name];
        
        if (socket) {
            this.stopHeartbeat(name);
            socket.close();
            delete this.sockets[name];
        }
    }

    /**
     * 재연결 시도
     */
    reconnect(name, url, handlers) {
        this.reconnectAttempts[name]++;
        
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts[name] - 1);
        
        console.log(`WebSocket ${name} reconnecting in ${delay}ms (attempt ${this.reconnectAttempts[name]})`);
        
        setTimeout(() => {
            this.connect(name, url, handlers);
        }, delay);
    }

    /**
     * 하트비트 시작
     */
    startHeartbeat(name) {
        this.stopHeartbeat(name);
        
        this.heartbeatTimers[name] = setInterval(() => {
            this.send(name, { type: 'heartbeat' });
        }, this.heartbeatInterval);
    }

    /**
     * 하트비트 중지
     */
    stopHeartbeat(name) {
        if (this.heartbeatTimers[name]) {
            clearInterval(this.heartbeatTimers[name]);
            delete this.heartbeatTimers[name];
        }
    }

    /**
     * 모든 연결 종료
     */
    disconnectAll() {
        Object.keys(this.sockets).forEach(name => {
            this.disconnect(name);
        });
    }
}

// 전역 WebSocket 매니저 인스턴스
const wsManager = new WebSocketManager();

/**
 * 댓글 WebSocket 연결
 */
function connectCommentWebSocket(contentType, objectId) {
    const url = `/ws/comments/${contentType}/${objectId}/`;
    
    return wsManager.connect('comments', url, {
        onOpen: () => {
            console.log('댓글 WebSocket 연결됨');
        },
        
        onMessage: (data) => {
            switch (data.type) {
                case 'initial_comments':
                    // 초기 댓글 목록 렌더링
                    renderComments(data.comments);
                    break;
                    
                case 'new_comment':
                    // 새 댓글 추가
                    addComment(data.comment);
                    break;
                    
                case 'comment_updated':
                    // 댓글 수정
                    updateComment(data.comment);
                    break;
                    
                case 'comment_deleted':
                    // 댓글 삭제
                    removeComment(data.comment_id);
                    break;
            }
        },
        
        onClose: () => {
            console.log('댓글 WebSocket 연결 종료');
        },
        
        onError: (error) => {
            console.error('댓글 WebSocket 에러:', error);
        }
    });
}

/**
 * 알림 WebSocket 연결
 */
function connectNotificationWebSocket() {
    const url = '/ws/notifications/';
    
    return wsManager.connect('notifications', url, {
        onOpen: () => {
            console.log('알림 WebSocket 연결됨');
        },
        
        onMessage: (data) => {
            switch (data.type) {
                case 'initial_notifications':
                    // 초기 알림 목록
                    updateNotificationBadge(data.unread_count);
                    renderNotifications(data.notifications);
                    break;
                    
                case 'new_notification':
                    // 새 알림
                    showNotification(data.notification);
                    incrementNotificationBadge();
                    break;
            }
        }
    });
}

/**
 * Presence WebSocket 연결
 */
function connectPresenceWebSocket() {
    const url = '/ws/presence/';
    
    return wsManager.connect('presence', url, {
        onOpen: () => {
            console.log('Presence WebSocket 연결됨');
        },
        
        onMessage: (data) => {
            switch (data.type) {
                case 'online_users':
                    // 온라인 사용자 목록
                    updateOnlineUsers(data.users);
                    break;
                    
                case 'user_status_changed':
                    // 사용자 상태 변경
                    updateUserStatus(data.user_id, data.status);
                    break;
                    
                case 'user_status_updated':
                    // 사용자 상태 메시지 업데이트
                    updateUserStatusMessage(data.user_id, data.status_message);
                    break;
            }
        }
    });
}

/**
 * 활동 피드 WebSocket 연결
 */
function connectActivityWebSocket() {
    const url = '/ws/activity/';
    
    return wsManager.connect('activity', url, {
        onOpen: () => {
            console.log('활동 WebSocket 연결됨');
        },
        
        onMessage: (data) => {
            switch (data.type) {
                case 'initial_activities':
                    // 초기 활동 목록
                    renderActivities(data.activities);
                    break;
                    
                case 'new_activity':
                    // 새 활동
                    addActivity(data.activity);
                    break;
                    
                case 'more_activities':
                    // 추가 활동 로드
                    appendActivities(data.activities);
                    break;
            }
        }
    });
}

// UI 업데이트 함수들 (다른 컴포넌트와 연동)

function renderComments(comments) {
    // comment-system.js의 렌더링 함수 호출
    if (window.commentSystem) {
        window.commentSystem.renderComments(comments);
    }
}

function addComment(comment) {
    if (window.commentSystem) {
        window.commentSystem.addComment(comment);
    }
}

function updateComment(comment) {
    if (window.commentSystem) {
        window.commentSystem.updateComment(comment);
    }
}

function removeComment(commentId) {
    if (window.commentSystem) {
        window.commentSystem.removeComment(commentId);
    }
}

function showNotification(notification) {
    // notification-system.js의 알림 표시 함수 호출
    if (window.notificationSystem) {
        window.notificationSystem.showNotification(notification);
    }
}

function updateNotificationBadge(count) {
    if (window.notificationSystem) {
        window.notificationSystem.updateBadge(count);
    }
}

function incrementNotificationBadge() {
    if (window.notificationSystem) {
        window.notificationSystem.incrementBadge();
    }
}

function renderNotifications(notifications) {
    if (window.notificationSystem) {
        window.notificationSystem.renderNotifications(notifications);
    }
}

function updateOnlineUsers(users) {
    // 온라인 사용자 목록 업데이트
    const onlineList = document.querySelector('.online-users-list');
    if (onlineList) {
        onlineList.innerHTML = users.map(user => `
            <div class="online-user" data-user-id="${user.id}">
                <span class="status-indicator online"></span>
                <span class="username">${user.username}</span>
                ${user.status_message ? `<span class="status-message">${user.status_message}</span>` : ''}
            </div>
        `).join('');
    }
}

function updateUserStatus(userId, status) {
    const userElement = document.querySelector(`.online-user[data-user-id="${userId}"]`);
    if (userElement) {
        const indicator = userElement.querySelector('.status-indicator');
        indicator.className = `status-indicator ${status}`;
    }
}

function updateUserStatusMessage(userId, statusMessage) {
    const userElement = document.querySelector(`.online-user[data-user-id="${userId}"]`);
    if (userElement) {
        let messageElement = userElement.querySelector('.status-message');
        if (statusMessage) {
            if (!messageElement) {
                messageElement = document.createElement('span');
                messageElement.className = 'status-message';
                userElement.appendChild(messageElement);
            }
            messageElement.textContent = statusMessage;
        } else if (messageElement) {
            messageElement.remove();
        }
    }
}

function renderActivities(activities) {
    const activityFeed = document.querySelector('.activity-feed');
    if (activityFeed) {
        activityFeed.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-user">${activity.user.username}</div>
                <div class="activity-description">${activity.description}</div>
                <div class="activity-time">${formatTime(activity.created_at)}</div>
            </div>
        `).join('');
    }
}

function addActivity(activity) {
    const activityFeed = document.querySelector('.activity-feed');
    if (activityFeed) {
        const activityHtml = `
            <div class="activity-item new">
                <div class="activity-user">${activity.user.username}</div>
                <div class="activity-description">${activity.description}</div>
                <div class="activity-time">${formatTime(activity.created_at)}</div>
            </div>
        `;
        activityFeed.insertAdjacentHTML('afterbegin', activityHtml);
        
        // 애니메이션 효과
        setTimeout(() => {
            activityFeed.querySelector('.activity-item.new').classList.remove('new');
        }, 100);
    }
}

function appendActivities(activities) {
    const activityFeed = document.querySelector('.activity-feed');
    if (activityFeed) {
        const activitiesHtml = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-user">${activity.user.username}</div>
                <div class="activity-description">${activity.description}</div>
                <div class="activity-time">${formatTime(activity.created_at)}</div>
            </div>
        `).join('');
        activityFeed.insertAdjacentHTML('beforeend', activitiesHtml);
    }
}

function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return '방금 전';
    if (minutes < 60) return `${minutes}분 전`;
    if (hours < 24) return `${hours}시간 전`;
    if (days < 7) return `${days}일 전`;
    
    return date.toLocaleDateString();
}

// 페이지 종료 시 WebSocket 연결 정리
window.addEventListener('beforeunload', () => {
    wsManager.disconnectAll();
});

// Export for use in other modules
window.wsManager = wsManager;
window.connectCommentWebSocket = connectCommentWebSocket;
window.connectNotificationWebSocket = connectNotificationWebSocket;
window.connectPresenceWebSocket = connectPresenceWebSocket;
window.connectActivityWebSocket = connectActivityWebSocket;