/**
 * Dashboard JavaScript
 * 실시간 데이터 페칭 및 차트 관리
 */

let charts = {};
let refreshInterval;
let notificationCount = 0;

/**
 * 대시보드 초기화
 */
async function initDashboard() {
    showLoading(true);
    
    try {
        // 데이터 로드
        await Promise.all([
            loadStatistics(),
            loadRecentActivities(),
            loadNotifications(),
            initCharts()
        ]);
        
        // 실시간 업데이트 시작 (30초마다)
        startAutoRefresh();
        
        // 시간 업데이트 (1분마다)
        setInterval(updateTime, 60000);
        
    } catch (error) {
        console.error('대시보드 초기화 실패:', error);
        showToast('대시보드 로드 중 오류가 발생했습니다.', 'error');
    } finally {
        showLoading(false);
    }
}

/**
 * 통계 데이터 로드
 */
async function loadStatistics() {
    try {
        const response = await fetch('/dashboard/api/statistics/');
        const data = await response.json();
        
        // 통계 카드 업데이트
        document.getElementById('stat-users').textContent = formatNumber(data.total_users);
        document.getElementById('stat-projects').textContent = formatNumber(data.active_projects);
        document.getElementById('stat-tasks').textContent = formatNumber(data.completed_tasks);
        document.getElementById('stat-reports').textContent = formatNumber(data.pending_reports);
        
        // 애니메이션 효과
        animateNumbers();
        
    } catch (error) {
        console.error('통계 로드 실패:', error);
    }
}

/**
 * 최근 활동 로드
 */
async function loadRecentActivities() {
    try {
        const response = await fetch('/dashboard/api/activities/');
        const data = await response.json();
        
        const activityList = document.getElementById('activity-list');
        activityList.innerHTML = '';
        
        data.activities.forEach(activity => {
            const activityItem = createActivityItem(activity);
            activityList.appendChild(activityItem);
        });
        
    } catch (error) {
        console.error('활동 로드 실패:', error);
    }
}

/**
 * 활동 아이템 생성
 */
function createActivityItem(activity) {
    const item = document.createElement('div');
    item.className = 'activity-item';
    
    const iconColor = getActivityIconColor(activity.type);
    
    item.innerHTML = `
        <div class="activity-icon" style="background: ${iconColor};">
            ${getActivityIcon(activity.icon)}
        </div>
        <div class="activity-content">
            <div class="user">${activity.user}</div>
            <div class="description">${activity.description}</div>
            <div class="timestamp">${formatTimeAgo(activity.timestamp)}</div>
        </div>
    `;
    
    return item;
}

/**
 * 알림 로드
 */
async function loadNotifications() {
    try {
        const response = await fetch('/dashboard/api/notifications/');
        const data = await response.json();
        
        notificationCount = data.unread_count;
        updateNotificationBadge();
        
        const notificationList = document.getElementById('notification-list');
        notificationList.innerHTML = '';
        
        if (data.notifications.length === 0) {
            notificationList.innerHTML = '<p style="text-align: center; color: #999;">알림이 없습니다</p>';
            return;
        }
        
        data.notifications.forEach(notification => {
            const notificationItem = createNotificationItem(notification);
            notificationList.appendChild(notificationItem);
        });
        
    } catch (error) {
        console.error('알림 로드 실패:', error);
    }
}

/**
 * 알림 아이템 생성
 */
function createNotificationItem(notification) {
    const item = document.createElement('div');
    item.className = `notification-item ${notification.unread ? 'unread' : ''}`;
    item.onclick = () => markNotificationAsRead(notification.id);
    
    item.innerHTML = `
        <div class="title">${notification.title}</div>
        <div class="message">${notification.message}</div>
        <div class="time">${formatTimeAgo(notification.timestamp)}</div>
    `;
    
    return item;
}

/**
 * 차트 초기화
 */
async function initCharts() {
    // 라인 차트
    await initLineChart();
    
    // 파이 차트
    await initPieChart();
    
    // 바 차트
    await initBarChart();
}

/**
 * 라인 차트 초기화
 */
async function initLineChart() {
    try {
        const response = await fetch('/dashboard/api/chart/?type=line');
        const data = await response.json();
        
        const ctx = document.getElementById('lineChart').getContext('2d');
        
        if (charts.line) {
            charts.line.destroy();
        }
        
        charts.line = new Chart(ctx, {
            type: 'line',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('라인 차트 로드 실패:', error);
    }
}

/**
 * 파이 차트 초기화
 */
async function initPieChart() {
    try {
        const response = await fetch('/dashboard/api/chart/?type=pie');
        const data = await response.json();
        
        const ctx = document.getElementById('pieChart').getContext('2d');
        
        if (charts.pie) {
            charts.pie.destroy();
        }
        
        charts.pie = new Chart(ctx, {
            type: 'doughnut',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('파이 차트 로드 실패:', error);
    }
}

/**
 * 바 차트 초기화
 */
async function initBarChart() {
    try {
        const response = await fetch('/dashboard/api/chart/?type=bar');
        const data = await response.json();
        
        const ctx = document.getElementById('barChart').getContext('2d');
        
        if (charts.bar) {
            charts.bar.destroy();
        }
        
        charts.bar = new Chart(ctx, {
            type: 'bar',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('바 차트 로드 실패:', error);
    }
}

/**
 * 대시보드 새로고침
 */
async function refreshDashboard() {
    const refreshIcon = document.querySelector('.refresh-icon');
    refreshIcon.style.transform = 'rotate(360deg)';
    
    await Promise.all([
        loadStatistics(),
        loadRecentActivities(),
        loadNotifications()
    ]);
    
    showToast('대시보드가 새로고침되었습니다.', 'success');
    
    setTimeout(() => {
        refreshIcon.style.transform = 'rotate(0deg)';
    }, 500);
}

/**
 * 자동 새로고침 시작
 */
function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        loadStatistics();
        loadRecentActivities();
        loadNotifications();
    }, 30000); // 30초마다
}

/**
 * 자동 새로고침 중지
 */
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
}

/**
 * 알림 토글
 */
function toggleNotifications() {
    const panel = document.getElementById('notification-panel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

/**
 * 알림 읽음 처리
 */
async function markNotificationAsRead(notificationId) {
    try {
        const response = await fetch('/dashboard/api/notification/read/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ id: notificationId })
        });
        
        if (response.ok) {
            await loadNotifications();
        }
        
    } catch (error) {
        console.error('알림 읽음 처리 실패:', error);
    }
}

/**
 * 모든 알림 읽음 처리
 */
async function clearAllNotifications() {
    // 모든 알림을 읽음 처리하는 로직
    showToast('모든 알림을 읽음 처리했습니다.', 'success');
    await loadNotifications();
}

/**
 * 알림 배지 업데이트
 */
function updateNotificationBadge() {
    const badge = document.getElementById('notification-count');
    badge.textContent = notificationCount;
    badge.style.display = notificationCount > 0 ? 'block' : 'none';
}

/**
 * 차트 변경
 */
function changeChart(chartType, period) {
    // 차트 기간 변경 로직
    console.log(`차트 변경: ${chartType}, 기간: ${period}`);
}

/**
 * 차트 새로고침
 */
async function refreshChart(chartType) {
    if (chartType === 'line') {
        await initLineChart();
    } else if (chartType === 'pie') {
        await initPieChart();
    } else if (chartType === 'bar') {
        await initBarChart();
    }
}

/**
 * 활동 차트 전환
 */
function switchActivityChart(period) {
    const tabs = document.querySelectorAll('.chart-tabs .tab-btn');
    tabs.forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');
    
    // 차트 데이터 업데이트
    console.log(`활동 차트 전환: ${period}`);
}

/**
 * 빠른 작업 함수들
 */
function createNewProject() {
    // 즉시 페이지 이동
    window.location.href = '/field-reports/create/';
}

function createTask() {
    // 즉시 페이지 이동
    window.location.href = '/collaboration/';
}

function generateReport() {
    // 즉시 페이지 이동
    window.location.href = '/field-reports/';
}

function viewCalendar() {
    // 캘린더/일정 페이지로 이동
    window.location.href = '/calendar/';
}

function teamManagement() {
    // 팀 관리 페이지로 이동
    window.location.href = '/dashboard/team/';
}

function viewSettings() {
    // 즉시 페이지 이동
    window.location.href = '/admin/';
}

/**
 * 유틸리티 함수들
 */
function formatNumber(num) {
    return new Intl.NumberFormat('ko-KR').format(num);
}

function formatTimeAgo(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return '방금 전';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}분 전`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}시간 전`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}일 전`;
    
    return date.toLocaleDateString('ko-KR');
}

function updateTime() {
    const timeElement = document.getElementById('current-time');
    const now = new Date();
    timeElement.textContent = now.toLocaleString('ko-KR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getActivityIcon(icon) {
    const icons = {
        'check-circle': '✅',
        'document': '📄',
        'user-plus': '👤',
        'trophy': '🏆'
    };
    return icons[icon] || '📌';
}

function getActivityIconColor(type) {
    const colors = {
        'task_completed': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'report_submitted': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'user_joined': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        'milestone_reached': 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)'
    };
    return colors[type] || 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
}

function animateNumbers() {
    const elements = document.querySelectorAll('.stat-value');
    elements.forEach(element => {
        const finalValue = parseInt(element.textContent.replace(/,/g, ''));
        let currentValue = 0;
        const increment = finalValue / 30;
        
        const timer = setInterval(() => {
            currentValue += increment;
            if (currentValue >= finalValue) {
                currentValue = finalValue;
                clearInterval(timer);
            }
            element.textContent = formatNumber(Math.floor(currentValue));
        }, 30);
    });
}

function showLoading(show) {
    const loadingOverlay = document.getElementById('dashboard-loading');
    if (loadingOverlay) {
        loadingOverlay.style.display = show ? 'flex' : 'none';
    }
}

function showToast(message, type = 'info') {
    if (window.pwaManager) {
        window.pwaManager.showToast(message, type);
    } else {
        console.log(`${type}: ${message}`);
    }
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// 페이지 언로드 시 자동 새로고침 중지
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});