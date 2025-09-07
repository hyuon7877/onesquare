/**
 * 검색 바 컴포넌트
 * 자동완성 및 인기 검색어 기능 포함
 */
class SearchBar {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.searchInput = null;
        this.suggestionsBox = null;
        this.trendingBox = null;
        this.searchHistory = [];
        this.currentSuggestions = [];
        this.selectedIndex = -1;
        this.debounceTimer = null;
        
        this.init();
    }
    
    init() {
        this.render();
        this.attachEventListeners();
        this.loadTrendingSearches();
    }
    
    render() {
        const searchHTML = `
            <div class="search-bar-container">
                <div class="search-bar">
                    <div class="search-input-wrapper">
                        <i class="bi bi-search search-icon"></i>
                        <input 
                            type="text" 
                            class="search-input form-control" 
                            placeholder="검색어를 입력하세요..."
                            autocomplete="off"
                        >
                        <button class="btn-clear-search" style="display: none;">
                            <i class="bi bi-x-circle"></i>
                        </button>
                    </div>
                    <div class="search-filters">
                        <select class="form-select search-type" style="width: auto;">
                            <option value="all">전체</option>
                            <option value="reports">리포트</option>
                            <option value="comments">댓글</option>
                            <option value="users">사용자</option>
                            <option value="activities">활동</option>
                        </select>
                        <button class="btn btn-primary btn-search">
                            <i class="bi bi-search"></i> 검색
                        </button>
                    </div>
                </div>
                
                <div class="search-dropdown" style="display: none;">
                    <!-- 자동완성 제안 -->
                    <div class="suggestions-section" style="display: none;">
                        <div class="dropdown-header">
                            <i class="bi bi-lightbulb"></i> 추천 검색어
                        </div>
                        <div class="suggestions-list"></div>
                    </div>
                    
                    <!-- 인기 검색어 -->
                    <div class="trending-section">
                        <div class="dropdown-header">
                            <i class="bi bi-fire"></i> 인기 검색어
                        </div>
                        <div class="trending-list"></div>
                    </div>
                    
                    <!-- 최근 검색어 -->
                    <div class="history-section" style="display: none;">
                        <div class="dropdown-header">
                            <i class="bi bi-clock-history"></i> 최근 검색
                            <button class="btn-clear-history">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                        <div class="history-list"></div>
                    </div>
                </div>
                
                <!-- 검색 결과 영역 -->
                <div class="search-results-container" style="display: none;">
                    <div class="search-results-header">
                        <h5 class="results-title"></h5>
                        <div class="results-actions">
                            <button class="btn btn-sm btn-outline-primary btn-save-filter">
                                <i class="bi bi-bookmark"></i> 필터 저장
                            </button>
                            <button class="btn btn-sm btn-outline-secondary btn-export">
                                <i class="bi bi-download"></i> 내보내기
                            </button>
                        </div>
                    </div>
                    <div class="search-results"></div>
                    <div class="search-pagination"></div>
                </div>
            </div>
        `;
        
        this.container.innerHTML = searchHTML;
        
        // 요소 참조 저장
        this.searchInput = this.container.querySelector('.search-input');
        this.searchDropdown = this.container.querySelector('.search-dropdown');
        this.suggestionsSection = this.container.querySelector('.suggestions-section');
        this.suggestionsList = this.container.querySelector('.suggestions-list');
        this.trendingList = this.container.querySelector('.trending-list');
        this.historySection = this.container.querySelector('.history-section');
        this.historyList = this.container.querySelector('.history-list');
        this.resultsContainer = this.container.querySelector('.search-results-container');
        this.searchResults = this.container.querySelector('.search-results');
        this.clearButton = this.container.querySelector('.btn-clear-search');
    }
    
    attachEventListeners() {
        // 검색 입력
        this.searchInput.addEventListener('input', (e) => {
            this.handleInput(e.target.value);
        });
        
        // 포커스 이벤트
        this.searchInput.addEventListener('focus', () => {
            this.showDropdown();
            this.loadSearchHistory();
        });
        
        // 포커스 아웃
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.hideDropdown();
            }
        });
        
        // 키보드 네비게이션
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeydown(e);
        });
        
        // 검색 버튼
        this.container.querySelector('.btn-search').addEventListener('click', () => {
            this.performSearch();
        });
        
        // 검색어 지우기
        this.clearButton.addEventListener('click', () => {
            this.clearSearch();
        });
        
        // 검색 기록 삭제
        this.container.querySelector('.btn-clear-history')?.addEventListener('click', () => {
            this.clearSearchHistory();
        });
        
        // 필터 저장
        this.container.querySelector('.btn-save-filter')?.addEventListener('click', () => {
            this.saveSearchFilter();
        });
    }
    
    handleInput(value) {
        // 지우기 버튼 표시/숨김
        this.clearButton.style.display = value ? 'block' : 'none';
        
        // 디바운스 처리
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(() => {
            if (value.length >= 2) {
                this.fetchSuggestions(value);
            } else {
                this.hideSuggestions();
            }
        }, 300);
    }
    
    handleKeydown(e) {
        const items = this.suggestionsList.querySelectorAll('.suggestion-item');
        
        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(this.selectedIndex + 1, items.length - 1);
                this.highlightSuggestion(items);
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.highlightSuggestion(items);
                break;
                
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && items[this.selectedIndex]) {
                    this.selectSuggestion(items[this.selectedIndex].dataset.keyword);
                } else {
                    this.performSearch();
                }
                break;
                
            case 'Escape':
                this.hideDropdown();
                break;
        }
    }
    
    highlightSuggestion(items) {
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('active');
                this.searchInput.value = item.dataset.keyword;
            } else {
                item.classList.remove('active');
            }
        });
    }
    
    async fetchSuggestions(query) {
        try {
            const response = await fetch(`/search/autocomplete/?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.suggestions && data.suggestions.length > 0) {
                this.displaySuggestions(data.suggestions);
            } else {
                this.hideSuggestions();
            }
        } catch (error) {
            console.error('자동완성 조회 실패:', error);
        }
    }
    
    displaySuggestions(suggestions) {
        this.currentSuggestions = suggestions;
        
        const html = suggestions.map(item => `
            <div class="suggestion-item" data-keyword="${item.suggestion}">
                <i class="bi bi-search"></i>
                <span class="suggestion-text">${this.highlightMatch(item.suggestion, this.searchInput.value)}</span>
                ${item.category === 'trending' ? '<span class="badge bg-danger ms-2">인기</span>' : ''}
            </div>
        `).join('');
        
        this.suggestionsList.innerHTML = html;
        this.suggestionsSection.style.display = 'block';
        
        // 클릭 이벤트
        this.suggestionsList.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', () => {
                this.selectSuggestion(item.dataset.keyword);
            });
        });
    }
    
    highlightMatch(text, query) {
        const regex = new RegExp(`(${query})`, 'gi');
        return text.replace(regex, '<strong>$1</strong>');
    }
    
    hideSuggestions() {
        this.suggestionsSection.style.display = 'none';
        this.selectedIndex = -1;
    }
    
    selectSuggestion(keyword) {
        this.searchInput.value = keyword;
        this.performSearch();
        this.hideDropdown();
    }
    
    async performSearch() {
        const query = this.searchInput.value.trim();
        if (!query) return;
        
        const searchType = this.container.querySelector('.search-type').value;
        
        // 검색 기록에 추가
        this.addToHistory(query);
        
        // 로딩 표시
        this.showLoading();
        
        try {
            const response = await fetch(`/search/?q=${encodeURIComponent(query)}&type=${searchType}`);
            const data = await response.json();
            
            this.displayResults(data, query);
            this.hideDropdown();
        } catch (error) {
            console.error('검색 실패:', error);
            this.showError('검색 중 오류가 발생했습니다.');
        }
    }
    
    displayResults(data, query) {
        const resultsTitle = this.container.querySelector('.results-title');
        resultsTitle.textContent = `"${query}" 검색 결과 (${data.total_count}건)`;
        
        if (data.results.length === 0) {
            this.searchResults.innerHTML = `
                <div class="no-results">
                    <i class="bi bi-search"></i>
                    <p>검색 결과가 없습니다.</p>
                </div>
            `;
        } else {
            const html = data.results.map(item => this.renderResultItem(item)).join('');
            this.searchResults.innerHTML = html;
        }
        
        // 페이지네이션
        if (data.total_pages > 1) {
            this.renderPagination(data);
        }
        
        this.resultsContainer.style.display = 'block';
    }
    
    renderResultItem(item) {
        const typeIcon = {
            'report': 'bi-file-text',
            'comment': 'bi-chat-dots',
            'user': 'bi-person',
            'activity': 'bi-activity'
        };
        
        return `
            <div class="search-result-item">
                <div class="result-icon">
                    <i class="bi ${typeIcon[item.type] || 'bi-file'}"></i>
                </div>
                <div class="result-content">
                    <h6 class="result-title">
                        <a href="${item.url}">${item.title}</a>
                    </h6>
                    <p class="result-excerpt">${item.content}</p>
                    <div class="result-meta">
                        ${item.author ? `
                            <span class="author">
                                <i class="bi bi-person"></i> ${item.author.full_name}
                            </span>
                        ` : ''}
                        <span class="date">
                            <i class="bi bi-calendar"></i> ${new Date(item.created_at).toLocaleDateString('ko-KR')}
                        </span>
                        ${item.tags && item.tags.length > 0 ? `
                            <span class="tags">
                                ${item.tags.map(tag => `<span class="badge bg-secondary">${tag}</span>`).join(' ')}
                            </span>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    renderPagination(data) {
        const pagination = this.container.querySelector('.search-pagination');
        let html = '<nav><ul class="pagination">';
        
        // 이전 페이지
        html += `
            <li class="page-item ${!data.has_previous ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${data.current_page - 1}">이전</a>
            </li>
        `;
        
        // 페이지 번호
        for (let i = 1; i <= data.total_pages; i++) {
            html += `
                <li class="page-item ${i === data.current_page ? 'active' : ''}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }
        
        // 다음 페이지
        html += `
            <li class="page-item ${!data.has_next ? 'disabled' : ''}">
                <a class="page-link" href="#" data-page="${data.current_page + 1}">다음</a>
            </li>
        `;
        
        html += '</ul></nav>';
        pagination.innerHTML = html;
        
        // 페이지 클릭 이벤트
        pagination.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(link.dataset.page);
                if (page > 0 && page <= data.total_pages) {
                    this.performSearch(page);
                }
            });
        });
    }
    
    async loadTrendingSearches() {
        try {
            const response = await fetch('/search/trending/?limit=5');
            const data = await response.json();
            
            if (data.trending && data.trending.length > 0) {
                const html = data.trending.map((item, index) => `
                    <div class="trending-item" data-keyword="${item.keyword}">
                        <span class="trending-rank">${index + 1}</span>
                        <span class="trending-keyword">${item.keyword}</span>
                        <span class="trending-count">${item.count}회</span>
                    </div>
                `).join('');
                
                this.trendingList.innerHTML = html;
                
                // 클릭 이벤트
                this.trendingList.querySelectorAll('.trending-item').forEach(item => {
                    item.addEventListener('click', () => {
                        this.selectSuggestion(item.dataset.keyword);
                    });
                });
            }
        } catch (error) {
            console.error('인기 검색어 조회 실패:', error);
        }
    }
    
    async loadSearchHistory() {
        try {
            const response = await fetch('/search/history/');
            const data = await response.json();
            
            if (data.history && data.history.length > 0) {
                const html = data.history.slice(0, 5).map(item => `
                    <div class="history-item" data-keyword="${item.query}">
                        <i class="bi bi-clock-history"></i>
                        <span class="history-keyword">${item.query}</span>
                        <button class="btn-remove-history" data-id="${item.id}">
                            <i class="bi bi-x"></i>
                        </button>
                    </div>
                `).join('');
                
                this.historyList.innerHTML = html;
                this.historySection.style.display = 'block';
                
                // 클릭 이벤트
                this.historyList.querySelectorAll('.history-item').forEach(item => {
                    item.addEventListener('click', (e) => {
                        if (!e.target.closest('.btn-remove-history')) {
                            this.selectSuggestion(item.dataset.keyword);
                        }
                    });
                });
            }
        } catch (error) {
            console.error('검색 기록 조회 실패:', error);
        }
    }
    
    addToHistory(query) {
        if (!this.searchHistory.includes(query)) {
            this.searchHistory.unshift(query);
            this.searchHistory = this.searchHistory.slice(0, 10);
        }
    }
    
    async clearSearchHistory() {
        try {
            await fetch('/search/history/clear/', {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });
            
            this.historyList.innerHTML = '';
            this.historySection.style.display = 'none';
            showToast('검색 기록이 삭제되었습니다.');
        } catch (error) {
            console.error('검색 기록 삭제 실패:', error);
        }
    }
    
    clearSearch() {
        this.searchInput.value = '';
        this.clearButton.style.display = 'none';
        this.hideDropdown();
        this.resultsContainer.style.display = 'none';
    }
    
    showDropdown() {
        this.searchDropdown.style.display = 'block';
    }
    
    hideDropdown() {
        this.searchDropdown.style.display = 'none';
    }
    
    showLoading() {
        this.searchResults.innerHTML = `
            <div class="text-center p-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">검색 중...</span>
                </div>
            </div>
        `;
        this.resultsContainer.style.display = 'block';
    }
    
    showError(message) {
        this.searchResults.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="bi bi-exclamation-triangle"></i> ${message}
            </div>
        `;
    }
    
    async saveSearchFilter() {
        const query = this.searchInput.value;
        const searchType = this.container.querySelector('.search-type').value;
        
        const filterName = prompt('필터 이름을 입력하세요:');
        if (!filterName) return;
        
        try {
            const response = await fetch('/search/saved/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    name: filterName,
                    query: query,
                    filters: { type: searchType }
                })
            });
            
            const data = await response.json();
            if (data.success) {
                showToast('검색 필터가 저장되었습니다.');
            }
        } catch (error) {
            console.error('필터 저장 실패:', error);
        }
    }
}