/**
 * 매출 관리 대시보드 JavaScript
 * PWA 오프라인 지원 및 실시간 데이터 업데이트
 */

class RevenueDashboard {
    constructor() {
        this.apiBaseUrl = '/api/revenue';
        this.dashboardData = null;
        this.charts = {};
        this.updateInterval = null;
        this.isOffline = !navigator.onLine;
        
        this.init();
    }
    
    async init() {
        console.log('매출 대시보드 초기화 중...');
        
        // 네트워크 상태 감지
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
        
        // 초기 데이터 로딩
        await this.loadDashboardData();
        
        // 주기적 업데이트 (5분마다)
        this.startAutoUpdate();
        
        // 이벤트 리스너 등록
        this.setupEventListeners();
        
        console.log('매출 대시보드 초기화 완료');
    }
    
    async loadDashboardData() {
        try {
            this.showLoading(true);
            
            // 캐시된 데이터 먼저 표시 (오프라인 대응)
            const cachedData = this.getCachedData('dashboard');
            if (cachedData && this.isOffline) {
                this.renderDashboard(cachedData);
                this.showOfflineIndicator();
                return;
            }
            
            // API에서 실시간 데이터 가져오기
            const response = await fetch(`${this.apiBaseUrl}/dashboard/`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.dashboardData = await response.json();
            
            // 데이터 캐싱 (오프라인 대응)
            this.cacheData('dashboard', this.dashboardData);
            
            // 대시보드 렌더링
            this.renderDashboard(this.dashboardData);
            
        } catch (error) {
            console.error('대시보드 데이터 로딩 실패:', error);
            
            // 오프라인이거나 네트워크 오류시 캐시 데이터 사용
            const cachedData = this.getCachedData('dashboard');
            if (cachedData) {
                this.renderDashboard(cachedData);
                this.showOfflineIndicator();
            } else {
                this.showError('데이터를 불러올 수 없습니다. 네트워크 연결을 확인해주세요.');
            }
        } finally {
            this.showLoading(false);
        }
    }
    
    renderDashboard(data) {
        this.renderMainStats(data);
        this.renderRecentRevenues(data.recent_revenues || []);
        this.loadAnalyticsData();  // 차트 및 상세 분석 데이터
    }
    
    renderMainStats(data) {
        // 이번 달 매출
        this.animateCounter('this-month-revenue', data.this_month_revenue, '원');
        
        // 성장률 표시
        const growthElement = document.getElementById('growth-rate');
        const growthRate = data.growth_rate || 0;
        
        if (growthRate > 0) {
            growthElement.textContent = `↗ ${growthRate.toFixed(1)}%`;
            growthElement.className = 'growth-indicator positive';
        } else if (growthRate < 0) {
            growthElement.textContent = `↘ ${Math.abs(growthRate).toFixed(1)}%`;
            growthElement.className = 'growth-indicator negative';
        } else {
            growthElement.textContent = `→ 0%`;
            growthElement.className = 'growth-indicator neutral';
        }
        
        // 미수금
        this.animateCounter('pending-revenue', data.pending_revenue, '원');
        
        // 연체 매출
        this.animateCounter('overdue-revenue', data.overdue_revenue, '원');
        
        // 목표 달성률 (별도 API 호출 필요)
        this.loadTargetProgress();
    }
    
    renderRecentRevenues(revenues) {
        const tbody = document.querySelector('#recent-revenues-table tbody');
        tbody.innerHTML = '';
        
        if (revenues.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">최근 매출 기록이 없습니다.</td></tr>';
            return;
        }
        
        revenues.forEach(revenue => {
            const row = document.createElement('tr');
            row.className = 'fade-in-up';
            
            // 데이터 마스킹 확인
            const isMasked = revenue.is_masked || false;
            const amountDisplay = isMasked ? revenue.amount : this.formatCurrency(revenue.amount);
            
            row.innerHTML = `
                <td>${this.formatDate(revenue.revenue_date)}</td>
                <td>${revenue.project_name}</td>
                <td>${revenue.client_name}</td>
                <td class="${isMasked ? 'masked-data' : ''}">${amountDisplay}</td>
                <td><span class="badge status-${revenue.payment_status}">${this.getStatusText(revenue.payment_status)}</span></td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    async loadAnalyticsData() {
        try {
            const [analyticsResponse, targetResponse] = await Promise.all([
                fetch(`${this.apiBaseUrl}/analytics/`),
                fetch(`${this.apiBaseUrl}/targets/progress/`)
            ]);
            
            if (analyticsResponse.ok) {
                const analyticsData = await analyticsResponse.json();
                this.renderCharts(analyticsData);
                this.renderTopClients(analyticsData.client_stats || []);
            }
            
            if (targetResponse.ok) {
                const targetData = await targetResponse.json();
                this.renderTargetProgress(targetData.targets || []);
            }
            
        } catch (error) {
            console.error('분석 데이터 로딩 실패:', error);
            // 오프라인 또는 권한 부족시 차트 숨김
            this.hideChartsForLimitedAccess();
        }
    }
    
    renderCharts(data) {
        // 매출 트렌드 차트 (Canvas 기반 간단 차트)
        this.renderTrendChart(data.monthly_trend || []);
        
        // 카테고리별 매출 파이차트
        this.renderCategoryChart(data.category_stats || []);
    }
    
    renderTrendChart(monthlyData) {
        const canvas = document.getElementById('revenue-trend-chart');
        const ctx = canvas.getContext('2d');
        
        if (monthlyData.length === 0) {
            ctx.fillStyle = '#6c757d';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('데이터가 없습니다', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        // 간단한 선 차트 구현
        this.drawLineChart(ctx, canvas, monthlyData);
    }
    
    renderCategoryChart(categoryData) {
        const canvas = document.getElementById('category-pie-chart');
        const ctx = canvas.getContext('2d');
        
        if (categoryData.length === 0) {
            ctx.fillStyle = '#6c757d';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('데이터가 없습니다', canvas.width / 2, canvas.height / 2);
            return;
        }
        
        // 간단한 파이차트 구현
        this.drawPieChart(ctx, canvas, categoryData);
    }
    
    renderTopClients(clientStats) {
        const container = document.getElementById('top-clients-list');
        container.innerHTML = '';
        
        if (clientStats.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">데이터가 없습니다.</p>';
            return;
        }
        
        clientStats.slice(0, 5).forEach((client, index) => {
            const item = document.createElement('div');
            item.className = 'top-client-item fade-in-up';
            item.style.animationDelay = `${index * 0.1}s`;
            
            item.innerHTML = `
                <div>
                    <div class="client-name">${client.client__name}</div>
                    <small class="client-count">${client.count}건</small>
                </div>
                <div class="client-revenue">${this.formatCurrency(client.total_revenue)}</div>
            `;
            
            container.appendChild(item);
        });
    }
    
    async loadTargetProgress() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/targets/progress/`);
            if (response.ok) {
                const data = await response.json();
                this.renderTargetProgress(data.targets || []);
            }
        } catch (error) {
            console.error('목표 진행률 로딩 실패:', error);
            document.getElementById('target-achievement').textContent = 'N/A';
        }
    }
    
    renderTargetProgress(targets) {
        const targetElement = document.getElementById('target-achievement');
        
        if (targets.length === 0) {
            targetElement.textContent = 'N/A';
            return;
        }
        
        // 전체 목표의 평균 달성률 계산
        const avgAchievement = targets.reduce((sum, target) => sum + target.achievement_rate, 0) / targets.length;
        
        targetElement.textContent = `${avgAchievement.toFixed(1)}%`;
        targetElement.className = avgAchievement >= 80 ? 'text-success' : avgAchievement >= 60 ? 'text-warning' : 'text-danger';
    }
    
    // 유틸리티 함수들
    formatCurrency(amount) {
        return new Intl.NumberFormat('ko-KR', {
            style: 'currency',
            currency: 'KRW',
            minimumFractionDigits: 0
        }).format(amount);
    }
    
    formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('ko-KR');
    }
    
    getStatusText(status) {
        const statusMap = {
            'confirmed': '확정',
            'pending': '대기',
            'overdue': '연체',
            'cancelled': '취소'
        };
        return statusMap[status] || status;
    }
    
    animateCounter(elementId, targetValue, suffix = '') {
        const element = document.getElementById(elementId);
        const startValue = 0;
        const duration = 1500; // 1.5초
        const startTime = Date.now();
        
        const updateCounter = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // easeOutCubic 애니메이션 함수
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            const currentValue = startValue + (targetValue - startValue) * easeProgress;
            
            element.textContent = this.formatCurrency(currentValue);
            element.className = 'counter-animation';
            
            if (progress < 1) {
                requestAnimationFrame(updateCounter);
            }
        };
        
        requestAnimationFrame(updateCounter);
    }
    
    // 캐시 관련 함수들 (PWA 오프라인 지원)
    cacheData(key, data) {
        try {
            localStorage.setItem(`revenue_dashboard_${key}`, JSON.stringify({
                data: data,
                timestamp: Date.now(),
                ttl: 5 * 60 * 1000 // 5분 TTL
            }));
        } catch (error) {
            console.warn('데이터 캐싱 실패:', error);
        }
    }
    
    getCachedData(key) {
        try {
            const cached = localStorage.getItem(`revenue_dashboard_${key}`);
            if (!cached) return null;
            
            const { data, timestamp, ttl } = JSON.parse(cached);
            
            // TTL 체크 (온라인 상태에서만)
            if (!this.isOffline && Date.now() - timestamp > ttl) {
                localStorage.removeItem(`revenue_dashboard_${key}`);
                return null;
            }
            
            return data;
        } catch (error) {
            console.warn('캐시 데이터 읽기 실패:', error);
            return null;
        }
    }
    
    // 네트워크 상태 처리
    handleOnline() {
        this.isOffline = false;
        console.log('온라인 상태 복구');
        this.hideOfflineIndicator();
        this.loadDashboardData(); // 최신 데이터 다시 로딩
    }
    
    handleOffline() {
        this.isOffline = true;
        console.log('오프라인 상태');
        this.showOfflineIndicator();
    }
    
    showOfflineIndicator() {
        const indicator = document.createElement('div');
        indicator.id = 'offline-indicator';
        indicator.className = 'alert alert-warning text-center';
        indicator.innerHTML = '<i class="fas fa-wifi-slash"></i> 오프라인 모드 - 캐시된 데이터를 표시 중';
        document.querySelector('.container-fluid').prepend(indicator);
    }
    
    hideOfflineIndicator() {
        const indicator = document.getElementById('offline-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    // 차트 그리기 함수들
    drawLineChart(ctx, canvas, data) {
        const width = canvas.width;
        const height = canvas.height;
        const padding = 40;
        
        // 배경 클리어
        ctx.clearRect(0, 0, width, height);
        
        if (data.length < 2) return;
        
        // 데이터 범위 계산
        const values = data.map(d => d.revenue);
        const maxValue = Math.max(...values);
        const minValue = Math.min(...values);
        const valueRange = maxValue - minValue || 1;
        
        // 좌표 변환 함수
        const getX = (index) => padding + (width - 2 * padding) * (index / (data.length - 1));
        const getY = (value) => height - padding - (height - 2 * padding) * ((value - minValue) / valueRange);
        
        // 격자 그리기
        ctx.strokeStyle = '#e9ecef';
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);
        
        for (let i = 0; i <= 4; i++) {
            const y = padding + (height - 2 * padding) * (i / 4);
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(width - padding, y);
            ctx.stroke();
        }
        
        // 선 그리기
        ctx.setLineDash([]);
        ctx.strokeStyle = '#007bff';
        ctx.lineWidth = 3;
        ctx.beginPath();
        
        data.forEach((point, index) => {
            const x = getX(index);
            const y = getY(point.revenue);
            
            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        
        ctx.stroke();
        
        // 점 그리기
        ctx.fillStyle = '#007bff';
        data.forEach((point, index) => {
            const x = getX(index);
            const y = getY(point.revenue);
            
            ctx.beginPath();
            ctx.arc(x, y, 4, 0, 2 * Math.PI);
            ctx.fill();
        });
        
        // 축 레이블
        ctx.fillStyle = '#6c757d';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        
        data.forEach((point, index) => {
            const x = getX(index);
            const month = point.month.split('-')[1];
            ctx.fillText(`${month}월`, x, height - 10);
        });
    }
    
    drawPieChart(ctx, canvas, data) {
        const width = canvas.width;
        const height = canvas.height;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) / 3;
        
        // 배경 클리어
        ctx.clearRect(0, 0, width, height);
        
        // 총합 계산
        const total = data.reduce((sum, item) => sum + item.total_revenue, 0);
        if (total === 0) return;
        
        // 색상 팔레트
        const colors = ['#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1', '#17a2b8', '#fd7e14'];
        
        let startAngle = -Math.PI / 2; // 12시 방향부터 시작
        
        data.forEach((item, index) => {
            const sliceAngle = (item.total_revenue / total) * 2 * Math.PI;
            const color = colors[index % colors.length];
            
            // 파이 슬라이스 그리기
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, startAngle, startAngle + sliceAngle);
            ctx.closePath();
            ctx.fill();
            
            // 테두리 그리기
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // 레이블 그리기 (퍼센트가 5% 이상일 때만)
            const percentage = (item.total_revenue / total) * 100;
            if (percentage >= 5) {
                const labelAngle = startAngle + sliceAngle / 2;
                const labelX = centerX + Math.cos(labelAngle) * (radius * 0.7);
                const labelY = centerY + Math.sin(labelAngle) * (radius * 0.7);
                
                ctx.fillStyle = '#ffffff';
                ctx.font = 'bold 12px Arial';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(`${percentage.toFixed(1)}%`, labelX, labelY);
            }
            
            startAngle += sliceAngle;
        });
        
        // 범례 그리기
        const legendX = 20;
        let legendY = 20;
        
        ctx.font = '12px Arial';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        
        data.slice(0, 5).forEach((item, index) => {
            const color = colors[index % colors.length];
            
            // 색상 박스
            ctx.fillStyle = color;
            ctx.fillRect(legendX, legendY, 15, 15);
            
            // 텍스트
            ctx.fillStyle = '#333';
            const text = item.category__name || item.client__name || 'Unknown';
            ctx.fillText(text, legendX + 20, legendY + 7.5);
            
            legendY += 20;
        });
    }
    
    showLoading(show) {
        // 로딩 인디케이터 표시/숨김
        const existing = document.getElementById('dashboard-loading');
        
        if (show && !existing) {
            const loading = document.createElement('div');
            loading.id = 'dashboard-loading';
            loading.className = 'loading';
            loading.innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">로딩 중...</span></div>';
            document.querySelector('.container-fluid').appendChild(loading);
        } else if (!show && existing) {
            existing.remove();
        }
    }
    
    showError(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container-fluid').prepend(alert);
        
        // 5초 후 자동 제거
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }
    
    setupEventListeners() {
        // 새로고침 버튼 (있다면)
        const refreshBtn = document.getElementById('refresh-dashboard');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadDashboardData());
        }
    }
    
    startAutoUpdate() {
        // 5분마다 자동 업데이트
        this.updateInterval = setInterval(() => {
            if (!this.isOffline) {
                console.log('대시보드 자동 업데이트');
                this.loadDashboardData();
            }
        }, 5 * 60 * 1000);
    }
    
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    hideChartsForLimitedAccess() {
        // 권한이 제한된 사용자를 위해 차트 영역 숨기기
        const chartContainers = document.querySelectorAll('.card canvas');
        chartContainers.forEach(canvas => {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#6c757d';
            ctx.font = '16px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('접근 권한이 제한됩니다', canvas.width / 2, canvas.height / 2);
        });
    }
}

// 전역 함수들 (템플릿에서 호출)
function viewAnalytics() {
    // 상세 분석 모달 표시
    loadAnalyticsModal();
}

function exportData(format) {
    // 데이터 내보내기
    const url = `/api/revenue/export/?format=${format}`;
    window.open(url, '_blank');
}

async function loadAnalyticsModal() {
    try {
        const response = await fetch('/api/revenue/analytics/');
        const data = await response.json();
        
        const modalContent = document.getElementById('analytics-content');
        modalContent.innerHTML = generateAnalyticsHTML(data);
        
        const modal = new bootstrap.Modal(document.getElementById('analyticsModal'));
        modal.show();
        
    } catch (error) {
        console.error('분석 데이터 로딩 실패:', error);
        alert('분석 데이터를 불러올 수 없습니다.');
    }
}

function generateAnalyticsHTML(data) {
    return `
        <div class="row">
            <div class="col-md-6">
                <h6>고객별 매출 TOP 10</h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr><th>고객명</th><th>매출액</th><th>건수</th></tr>
                        </thead>
                        <tbody>
                            ${data.client_stats.map(client => `
                                <tr>
                                    <td>${client.client__name}</td>
                                    <td>${new Intl.NumberFormat('ko-KR', {style: 'currency', currency: 'KRW'}).format(client.total_revenue)}</td>
                                    <td>${client.count}건</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="col-md-6">
                <h6>프로젝트별 매출 TOP 10</h6>
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr><th>프로젝트명</th><th>매출액</th><th>건수</th></tr>
                        </thead>
                        <tbody>
                            ${data.project_stats.map(project => `
                                <tr>
                                    <td>${project.project__name}</td>
                                    <td>${new Intl.NumberFormat('ko-KR', {style: 'currency', currency: 'KRW'}).format(project.total_revenue)}</td>
                                    <td>${project.count}건</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
}

// 페이지 로드 시 대시보드 초기화
document.addEventListener('DOMContentLoaded', () => {
    window.revenueDashboard = new RevenueDashboard();
});

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', () => {
    if (window.revenueDashboard) {
        window.revenueDashboard.stopAutoUpdate();
    }
});