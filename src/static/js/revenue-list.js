/**
 * 매출 목록 페이지 JavaScript
 * PWA 오프라인 지원 및 CRUD 기능
 */

class RevenueList {
    constructor() {
        this.apiBaseUrl = '/api/revenue';
        this.currentPage = 1;
        this.perPage = 20;
        this.totalPages = 1;
        this.totalCount = 0;
        this.currentFilters = {};
        this.isOffline = !navigator.onLine;
        
        this.init();
    }
    
    async init() {
        console.log('매출 목록 초기화 중...');
        
        // 네트워크 상태 감지
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
        
        // 이벤트 리스너 설정
        this.setupEventListeners();
        
        // 초기 데이터 로딩
        await this.loadRevenueList();
        
        // 필터 옵션 로딩
        await this.loadFilterOptions();
        
        console.log('매출 목록 초기화 완료');
    }
    
    setupEventListeners() {
        // 필터 폼 이벤트
        const filterForm = document.getElementById('filter-form');
        if (filterForm) {
            filterForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.applyFilters();
            });
        }
        
        // 검색 입력 디바운스
        const searchInput = document.getElementById('search');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', () => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.applyFilters();
                }, 500);
            });
        }
        
        // 페이지당 표시 개수 변경
        const perPageSelect = document.getElementById('per-page');
        if (perPageSelect) {
            perPageSelect.addEventListener('change', () => this.changePerPage());
        }
    }
    
    async loadRevenueList(page = 1) {
        try {
            this.showLoading(true);
            
            // 캐시된 데이터 먼저 표시 (오프라인 대응)
            const cacheKey = `list_${page}_${JSON.stringify(this.currentFilters)}`;
            const cachedData = this.getCachedData(cacheKey);
            
            if (cachedData && this.isOffline) {
                this.renderRevenueList(cachedData);
                this.showOfflineIndicator();
                return;
            }
            
            // API 호출
            const params = new URLSearchParams({
                page: page,
                per_page: this.perPage,
                ...this.currentFilters
            });
            
            const response = await fetch(`${this.apiBaseUrl}/list/?${params}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // 데이터 캐싱
            this.cacheData(cacheKey, data);
            
            // UI 업데이트
            this.currentPage = page;
            this.totalPages = data.total_pages;
            this.totalCount = data.total_count;
            
            this.renderRevenueList(data);
            
        } catch (error) {
            console.error('매출 목록 로딩 실패:', error);
            
            // 오프라인이거나 네트워크 오류시 캐시 데이터 사용
            const cacheKey = `list_${page}_${JSON.stringify(this.currentFilters)}`;
            const cachedData = this.getCachedData(cacheKey);
            
            if (cachedData) {
                this.renderRevenueList(cachedData);
                this.showOfflineIndicator();
            } else {
                this.showError('데이터를 불러올 수 없습니다.');
            }
        } finally {
            this.showLoading(false);
        }
    }
    
    renderRevenueList(data) {
        const tbody = document.querySelector('#revenues-table tbody');
        tbody.innerHTML = '';
        
        if (data.results.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="11" class="text-center text-muted py-4">
                        검색 조건에 맞는 매출 데이터가 없습니다.
                    </td>
                </tr>
            `;
            this.updateTableInfo(0, 0, 0);
            this.renderPagination(1, 1);
            return;
        }
        
        // 테이블 행 생성
        data.results.forEach((revenue, index) => {
            const row = this.createRevenueRow(revenue, index);
            tbody.appendChild(row);
        });
        
        // 테이블 정보 및 페이지네이션 업데이트
        this.updateTableInfo(data.page, data.per_page, data.total_count);
        this.renderPagination(data.page, data.total_pages);
    }
    
    createRevenueRow(revenue, index) {
        const row = document.createElement('tr');
        row.className = 'fade-in';
        row.style.animationDelay = `${index * 0.05}s`;
        
        const isMasked = revenue.is_masked || false;
        const hasEditPermission = document.querySelector('[data-can-edit="true"]') !== null;
        
        row.innerHTML = `
            <td class="date-cell">${this.formatDate(revenue.revenue_date)}</td>
            <td class="project-cell" title="${revenue.project_name}">
                ${this.truncateText(revenue.project_name, 20)}
                <small class="d-block text-muted">${revenue.project_code}</small>
            </td>
            <td class="client-cell" title="${revenue.client_name}">
                ${this.truncateText(revenue.client_name, 15)}
            </td>
            <td>${revenue.category_name}</td>
            <td>${revenue.revenue_type}</td>
            <td class="amount-cell ${isMasked ? 'masked-data' : ''}">
                ${isMasked ? revenue.amount : this.formatCurrency(revenue.amount)}
            </td>
            <td class="amount-cell ${isMasked ? 'masked-data' : ''}">
                ${isMasked ? (revenue.net_amount || '***') : this.formatCurrency(revenue.net_amount)}
            </td>
            <td>
                <span class="badge status-${revenue.payment_status}">
                    ${revenue.payment_status}
                </span>
            </td>
            <td>
                <span class="badge ${revenue.is_confirmed ? 'confirmed-yes' : 'confirmed-no'}">
                    ${revenue.is_confirmed ? '확정' : '미확정'}
                </span>
            </td>
            <td>${revenue.sales_person || '-'}</td>
            ${hasEditPermission ? `
                <td>
                    <div class="action-buttons">
                        <button class="btn btn-outline-primary btn-sm" 
                                onclick="viewRevenueDetail('${revenue.id}')" 
                                title="상세보기">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-outline-warning btn-sm" 
                                onclick="editRevenue('${revenue.id}')" 
                                title="수정">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-danger btn-sm" 
                                onclick="deleteRevenue('${revenue.id}')" 
                                title="삭제">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            ` : ''}
        `;
        
        return row;
    }
    
    updateTableInfo(page, perPage, totalCount) {
        const tableInfo = document.getElementById('table-info');
        if (!tableInfo) return;
        
        const startItem = ((page - 1) * perPage) + 1;
        const endItem = Math.min(page * perPage, totalCount);
        
        tableInfo.textContent = `${totalCount}개 중 ${startItem}-${endItem} 표시`;
    }
    
    renderPagination(currentPage, totalPages) {
        const pagination = document.getElementById('pagination');
        if (!pagination) return;
        
        pagination.innerHTML = '';
        
        if (totalPages <= 1) return;
        
        // 이전 버튼
        const prevDisabled = currentPage <= 1;
        const prevLi = this.createPaginationItem('이전', currentPage - 1, prevDisabled);
        pagination.appendChild(prevLi);
        
        // 페이지 번호들
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, currentPage + 2);
        
        if (startPage > 1) {
            pagination.appendChild(this.createPaginationItem('1', 1));
            if (startPage > 2) {
                pagination.appendChild(this.createPaginationItem('...', null, true));
            }
        }
        
        for (let i = startPage; i <= endPage; i++) {
            const isActive = i === currentPage;
            pagination.appendChild(this.createPaginationItem(i, i, false, isActive));
        }
        
        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                pagination.appendChild(this.createPaginationItem('...', null, true));
            }
            pagination.appendChild(this.createPaginationItem(totalPages, totalPages));
        }
        
        // 다음 버튼
        const nextDisabled = currentPage >= totalPages;
        const nextLi = this.createPaginationItem('다음', currentPage + 1, nextDisabled);
        pagination.appendChild(nextLi);
    }
    
    createPaginationItem(text, page, disabled = false, active = false) {
        const li = document.createElement('li');
        li.className = `page-item ${disabled ? 'disabled' : ''} ${active ? 'active' : ''}`;
        
        const link = document.createElement('a');
        link.className = 'page-link';
        link.href = '#';
        link.textContent = text;
        
        if (!disabled && page) {
            link.onclick = (e) => {
                e.preventDefault();
                this.goToPage(page);
            };
        }
        
        li.appendChild(link);
        return li;
    }
    
    async applyFilters() {
        const form = document.getElementById('filter-form');
        const formData = new FormData(form);
        
        this.currentFilters = {};
        for (const [key, value] of formData.entries()) {
            if (value.trim()) {
                this.currentFilters[key] = value;
            }
        }
        
        this.currentPage = 1; // 필터 적용 시 첫 페이지로
        await this.loadRevenueList(1);
    }
    
    resetFilters() {
        const form = document.getElementById('filter-form');
        form.reset();
        this.currentFilters = {};
        this.currentPage = 1;
        this.loadRevenueList(1);
    }
    
    changePerPage() {
        const select = document.getElementById('per-page');
        this.perPage = parseInt(select.value);
        this.currentPage = 1;
        this.loadRevenueList(1);
    }
    
    goToPage(page) {
        if (page < 1 || page > this.totalPages) return;
        this.loadRevenueList(page);
    }
    
    // 매출 CRUD 기능들
    async showAddRevenueModal() {
        const modal = new bootstrap.Modal(document.getElementById('revenueModal'));
        document.getElementById('revenueModalTitle').textContent = '매출 등록';
        document.getElementById('revenue-form').reset();
        document.getElementById('revenue-id').value = '';
        
        // 프로젝트, 고객 옵션 로딩
        await this.loadFormOptions();
        
        modal.show();
    }
    
    async editRevenue(revenueId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/${revenueId}/`);
            if (!response.ok) throw new Error('매출 데이터 로딩 실패');
            
            const revenue = await response.json();
            
            // 모달 제목 변경
            document.getElementById('revenueModalTitle').textContent = '매출 수정';
            
            // 폼에 데이터 입력
            this.populateForm(revenue);
            
            // 모달 표시
            const modal = new bootstrap.Modal(document.getElementById('revenueModal'));
            modal.show();
            
        } catch (error) {
            console.error('매출 수정 폼 로딩 실패:', error);
            this.showError('매출 정보를 불러올 수 없습니다.');
        }
    }
    
    async viewRevenueDetail(revenueId) {
        try {
            const response = await fetch(`${this.apiBaseUrl}/${revenueId}/`);
            if (!response.ok) throw new Error('매출 상세 정보 로딩 실패');
            
            const revenue = await response.json();
            
            // 상세 정보 HTML 생성
            const detailHtml = this.generateRevenueDetailHtml(revenue);
            document.getElementById('revenue-detail-content').innerHTML = detailHtml;
            
            // 모달 표시
            const modal = new bootstrap.Modal(document.getElementById('revenueDetailModal'));
            modal.show();
            
        } catch (error) {
            console.error('매출 상세 정보 로딩 실패:', error);
            this.showError('매출 상세 정보를 불러올 수 없습니다.');
        }
    }
    
    async saveRevenue() {
        const form = document.getElementById('revenue-form');
        const formData = new FormData(form);
        const revenueId = document.getElementById('revenue-id').value;
        
        try {
            this.showLoading(true);
            
            const url = revenueId ? 
                `${this.apiBaseUrl}/${revenueId}/` : 
                `${this.apiBaseUrl}/`;
            
            const method = revenueId ? 'PUT' : 'POST';
            
            const response = await fetch(url, {
                method: method,
                body: formData,
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || '저장에 실패했습니다.');
            }
            
            // 모달 닫기
            const modal = bootstrap.Modal.getInstance(document.getElementById('revenueModal'));
            modal.hide();
            
            // 목록 새로고침
            await this.loadRevenueList(this.currentPage);
            
            this.showSuccess(revenueId ? '매출이 수정되었습니다.' : '매출이 등록되었습니다.');
            
        } catch (error) {
            console.error('매출 저장 실패:', error);
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    async deleteRevenue(revenueId) {
        if (!confirm('이 매출 기록을 삭제하시겠습니까?')) return;
        
        try {
            this.showLoading(true);
            
            const response = await fetch(`${this.apiBaseUrl}/${revenueId}/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                throw new Error('삭제에 실패했습니다.');
            }
            
            // 목록 새로고침
            await this.loadRevenueList(this.currentPage);
            
            this.showSuccess('매출이 삭제되었습니다.');
            
        } catch (error) {
            console.error('매출 삭제 실패:', error);
            this.showError(error.message);
        } finally {
            this.showLoading(false);
        }
    }
    
    async exportRevenues() {
        try {
            const params = new URLSearchParams(this.currentFilters);
            const url = `${this.apiBaseUrl}/export/?${params}`;
            
            const response = await fetch(url);
            if (!response.ok) throw new Error('내보내기 실패');
            
            const data = await response.json();
            
            // CSV 형태로 다운로드
            this.downloadCSV(data.data, 'revenue_export.csv');
            
        } catch (error) {
            console.error('내보내기 실패:', error);
            this.showError('데이터 내보내기에 실패했습니다.');
        }
    }
    
    // 유틸리티 함수들
    formatCurrency(amount) {
        if (amount === null || amount === undefined) return '-';
        return new Intl.NumberFormat('ko-KR', {
            style: 'currency',
            currency: 'KRW',
            minimumFractionDigits: 0
        }).format(amount);
    }
    
    formatDate(dateString) {
        if (!dateString) return '-';
        return new Date(dateString).toLocaleDateString('ko-KR');
    }
    
    truncateText(text, maxLength) {
        if (!text) return '-';
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }
    
    generateRevenueDetailHtml(revenue) {
        const isMasked = revenue.is_masked || false;
        
        return `
            <div class="row">
                <div class="col-md-6">
                    <h6 class="text-primary">기본 정보</h6>
                    <table class="table table-sm">
                        <tr><th>프로젝트:</th><td>${revenue.project_name} (${revenue.project_code})</td></tr>
                        <tr><th>고객:</th><td>${revenue.client_name}</td></tr>
                        <tr><th>카테고리:</th><td>${revenue.category_name}</td></tr>
                        <tr><th>매출 유형:</th><td>${revenue.revenue_type}</td></tr>
                        <tr><th>매출일:</th><td>${this.formatDate(revenue.revenue_date)}</td></tr>
                        <tr><th>영업담당:</th><td>${revenue.sales_person || '-'}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6 class="text-primary">금액 정보</h6>
                    <table class="table table-sm">
                        <tr><th>총 금액:</th><td class="${isMasked ? 'masked-data' : ''}">${isMasked ? revenue.amount : this.formatCurrency(revenue.amount)}</td></tr>
                        <tr><th>세금:</th><td class="${isMasked ? 'masked-data' : ''}">${isMasked ? '***' : this.formatCurrency(revenue.tax_amount)}</td></tr>
                        <tr><th>순매출:</th><td class="${isMasked ? 'masked-data' : ''}">${isMasked ? '***' : this.formatCurrency(revenue.net_amount)}</td></tr>
                        <tr><th>결제 상태:</th><td><span class="badge status-${revenue.payment_status}">${revenue.payment_status}</span></td></tr>
                        <tr><th>확정 여부:</th><td><span class="badge ${revenue.is_confirmed ? 'confirmed-yes' : 'confirmed-no'}">${revenue.is_confirmed ? '확정' : '미확정'}</span></td></tr>
                    </table>
                </div>
            </div>
            ${revenue.description ? `
                <div class="row mt-3">
                    <div class="col-12">
                        <h6 class="text-primary">설명</h6>
                        <p class="border rounded p-3">${revenue.description}</p>
                    </div>
                </div>
            ` : ''}
        `;
    }
    
    populateForm(revenue) {
        document.getElementById('revenue-id').value = revenue.id;
        document.getElementById('amount').value = revenue.amount;
        document.getElementById('revenue-date').value = revenue.revenue_date;
        document.getElementById('revenue-type').value = revenue.revenue_type;
        document.getElementById('payment-status').value = revenue.payment_status;
        document.getElementById('is-confirmed').checked = revenue.is_confirmed;
        
        if (revenue.description) {
            document.getElementById('description').value = revenue.description;
        }
        
        if (revenue.due_date) {
            document.getElementById('due-date').value = revenue.due_date;
        }
        
        if (revenue.tax_rate) {
            document.getElementById('tax-rate').value = revenue.tax_rate;
        }
    }
    
    downloadCSV(data, filename) {
        if (!data || data.length === 0) {
            this.showError('내보낼 데이터가 없습니다.');
            return;
        }
        
        // CSV 헤더
        const headers = [
            '매출일', '프로젝트명', '프로젝트코드', '고객명', '카테고리',
            '매출유형', '금액', '세금', '순매출', '결제상태', '확정여부',
            '영업담당', '설명'
        ];
        
        // CSV 데이터 생성
        const csvContent = [
            headers.join(','),
            ...data.map(item => [
                item.revenue_date,
                `"${item.project_name}"`,
                item.project_code,
                `"${item.client_name}"`,
                `"${item.category}"`,
                `"${item.revenue_type}"`,
                item.amount,
                item.tax_amount,
                item.net_amount,
                item.payment_status,
                item.is_confirmed ? '확정' : '미확정',
                `"${item.sales_person || ''}"`,
                `"${item.description || ''}"`
            ].join(','))
        ].join('\n');
        
        // 파일 다운로드
        const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
        URL.revokeObjectURL(link.href);
    }
    
    // PWA 캐시 관련 함수들
    cacheData(key, data) {
        try {
            localStorage.setItem(`revenue_list_${key}`, JSON.stringify({
                data: data,
                timestamp: Date.now(),
                ttl: 3 * 60 * 1000 // 3분 TTL
            }));
        } catch (error) {
            console.warn('데이터 캐싱 실패:', error);
        }
    }
    
    getCachedData(key) {
        try {
            const cached = localStorage.getItem(`revenue_list_${key}`);
            if (!cached) return null;
            
            const { data, timestamp, ttl } = JSON.parse(cached);
            
            if (!this.isOffline && Date.now() - timestamp > ttl) {
                localStorage.removeItem(`revenue_list_${key}`);
                return null;
            }
            
            return data;
        } catch (error) {
            console.warn('캐시 데이터 읽기 실패:', error);
            return null;
        }
    }
    
    handleOnline() {
        this.isOffline = false;
        this.hideOfflineIndicator();
        this.loadRevenueList(this.currentPage);
    }
    
    handleOffline() {
        this.isOffline = true;
        this.showOfflineIndicator();
    }
    
    showOfflineIndicator() {
        if (document.getElementById('offline-indicator')) return;
        
        const indicator = document.createElement('div');
        indicator.id = 'offline-indicator';
        indicator.className = 'offline-indicator';
        indicator.innerHTML = '<i class="fas fa-wifi-slash"></i> 오프라인 모드';
        document.body.appendChild(indicator);
    }
    
    hideOfflineIndicator() {
        const indicator = document.getElementById('offline-indicator');
        if (indicator) indicator.remove();
    }
    
    showLoading(show) {
        const existing = document.getElementById('list-loading');
        
        if (show && !existing) {
            const loading = document.createElement('div');
            loading.id = 'list-loading';
            loading.className = 'loading-overlay';
            loading.innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">로딩 중...</span></div>';
            document.querySelector('.card').style.position = 'relative';
            document.querySelector('.card').appendChild(loading);
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
        
        setTimeout(() => {
            if (alert.parentNode) alert.remove();
        }, 5000);
    }
    
    showSuccess(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container-fluid').prepend(alert);
        
        setTimeout(() => {
            if (alert.parentNode) alert.remove();
        }, 3000);
    }
    
    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
    
    async loadFilterOptions() {
        // 필터 옵션들을 동적으로 로딩 (필요한 경우)
    }
    
    async loadFormOptions() {
        // 폼의 select 옵션들을 동적으로 로딩 (필요한 경우)
    }
}

// 전역 함수들
function showAddRevenueModal() {
    window.revenueList.showAddRevenueModal();
}

function editRevenue(id) {
    window.revenueList.editRevenue(id);
}

function viewRevenueDetail(id) {
    window.revenueList.viewRevenueDetail(id);
}

function deleteRevenue(id) {
    window.revenueList.deleteRevenue(id);
}

function saveRevenue() {
    window.revenueList.saveRevenue();
}

function exportRevenues() {
    window.revenueList.exportRevenues();
}

function resetFilters() {
    window.revenueList.resetFilters();
}

function changePerPage() {
    window.revenueList.changePerPage();
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    window.revenueList = new RevenueList();
});