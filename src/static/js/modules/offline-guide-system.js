/**
 * OneSquare 오프라인 가이드 시스템
 * 
 * 사용자에게 오프라인 모드에서 사용 가능한 기능들을 안내하고
 * 네트워크 상태에 따른 적절한 가이드라인 제공
 */

class OfflineGuideSystem {
    constructor(config = {}) {
        this.config = {
            showWelcomeGuide: config.showWelcomeGuide !== false,
            showFeatureTooltips: config.showFeatureTooltips !== false,
            showOfflineHelp: config.showOfflineHelp !== false,
            autoShowGuides: config.autoShowGuides !== false,
            guideAnimationDuration: config.guideAnimationDuration || 300,
            tooltipDelay: config.tooltipDelay || 500,
            ...config
        };

        this.currentGuide = null;
        this.seenGuides = new Set(JSON.parse(localStorage.getItem('seenOfflineGuides') || '[]'));
        this.activeTooltips = new Map();
        this.tourSteps = [];
        this.currentTourStep = 0;

        // 가이드 템플릿들
        this.guideTemplates = new Map();
        this.setupGuideTemplates();

        this.init();
    }

    /**
     * 가이드 시스템 초기화
     */
    async init() {
        try {
            console.log('[OfflineGuideSystem] Initializing offline guide system...');

            await this.createGuideElements();
            await this.setupEventListeners();
            await this.initializeFeatureTooltips();
            await this.setupOfflineHelp();

            // 첫 방문 시 환영 가이드 표시
            if (this.config.showWelcomeGuide && !this.seenGuides.has('welcome')) {
                setTimeout(() => this.showWelcomeGuide(), 2000);
            }

            console.log('[OfflineGuideSystem] Offline guide system initialized successfully');

        } catch (error) {
            console.error('[OfflineGuideSystem] Initialization failed:', error);
        }
    }

    /**
     * 가이드 템플릿 설정
     */
    setupGuideTemplates() {
        // 환영 가이드
        this.guideTemplates.set('welcome', {
            title: '🌟 OneSquare에 오신 것을 환영합니다!',
            content: `
                <div class="guide-content">
                    <p>OneSquare는 오프라인에서도 강력한 기능을 제공하는 PWA입니다.</p>
                    <div class="feature-highlights">
                        <div class="feature-item">
                            <i class="fas fa-wifi-slash text-primary"></i>
                            <h6>오프라인 지원</h6>
                            <p>네트워크 없이도 80% 이상의 기능 사용</p>
                        </div>
                        <div class="feature-item">
                            <i class="fas fa-sync text-success"></i>
                            <h6>자동 동기화</h6>
                            <p>연결 복구 시 자동으로 데이터 동기화</p>
                        </div>
                        <div class="feature-item">
                            <i class="fas fa-mobile-alt text-info"></i>
                            <h6>모바일 최적화</h6>
                            <p>모바일에서도 완벽한 사용자 경험</p>
                        </div>
                    </div>
                </div>
            `,
            actions: [
                { label: '투어 시작', action: 'startTour', className: 'btn-primary' },
                { label: '건너뛰기', action: 'close', className: 'btn-outline-secondary' }
            ]
        });

        // 오프라인 모드 가이드
        this.guideTemplates.set('offlineMode', {
            title: '📶 오프라인 모드 활성화',
            content: `
                <div class="guide-content">
                    <div class="alert alert-info">
                        <i class="fas fa-info-circle"></i>
                        네트워크 연결이 끊어졌지만 걱정하지 마세요!
                    </div>
                    <h6>🟢 사용 가능한 기능들:</h6>
                    <ul class="available-features">
                        <li><i class="fas fa-chart-bar text-success"></i> 대시보드 통계 조회</li>
                        <li><i class="fas fa-bell text-success"></i> 최근 알림 확인</li>
                        <li><i class="fas fa-cog text-success"></i> 사용자 설정 변경</li>
                        <li><i class="fas fa-history text-success"></i> 활동 내역 조회</li>
                        <li><i class="fas fa-bookmark text-success"></i> 저장된 데이터 접근</li>
                    </ul>
                    <h6>🟡 제한된 기능들:</h6>
                    <ul class="limited-features">
                        <li><i class="fas fa-cloud-upload-alt text-warning"></i> 새 데이터 업로드</li>
                        <li><i class="fas fa-sync text-warning"></i> 실시간 데이터 업데이트</li>
                        <li><i class="fas fa-share text-warning"></i> 외부 공유 기능</li>
                    </ul>
                    <div class="mt-3">
                        <small class="text-muted">
                            💡 연결이 복구되면 모든 변경사항이 자동으로 동기화됩니다.
                        </small>
                    </div>
                </div>
            `,
            actions: [
                { label: '이해했습니다', action: 'close', className: 'btn-primary' }
            ]
        });

        // 동기화 가이드
        this.guideTemplates.set('syncStatus', {
            title: '🔄 데이터 동기화',
            content: `
                <div class="guide-content">
                    <p>OneSquare는 네트워크 상태에 따라 스마트하게 데이터를 관리합니다.</p>
                    <div class="sync-status-guide">
                        <div class="status-item">
                            <div class="status-indicator success"></div>
                            <div>
                                <strong>동기화됨</strong>
                                <p>모든 데이터가 최신 상태입니다.</p>
                            </div>
                        </div>
                        <div class="status-item">
                            <div class="status-indicator syncing"></div>
                            <div>
                                <strong>동기화 중</strong>
                                <p>서버와 데이터를 교환하고 있습니다.</p>
                            </div>
                        </div>
                        <div class="status-item">
                            <div class="status-indicator error"></div>
                            <div>
                                <strong>동기화 실패</strong>
                                <p>네트워크 문제로 동기화에 실패했습니다.</p>
                            </div>
                        </div>
                    </div>
                </div>
            `,
            actions: [
                { label: '확인', action: 'close', className: 'btn-primary' }
            ]
        });

        // 기능 투어
        this.guideTemplates.set('featureTour', {
            title: '🎯 주요 기능 둘러보기',
            content: `
                <div class="guide-content">
                    <p>OneSquare의 주요 기능들을 함께 살펴보겠습니다.</p>
                    <div class="tour-progress">
                        <div class="progress">
                            <div class="progress-bar" style="width: 0%"></div>
                        </div>
                        <small class="text-muted">1 / 5 단계</small>
                    </div>
                </div>
            `,
            actions: [
                { label: '다음', action: 'nextTourStep', className: 'btn-primary' },
                { label: '건너뛰기', action: 'close', className: 'btn-outline-secondary' }
            ]
        });
    }

    /**
     * 가이드 UI 요소 생성
     */
    async createGuideElements() {
        // 가이드 모달 생성
        this.createGuideModal();
        
        // 헬프 버튼 생성
        this.createHelpButton();
        
        // 투어 하이라이트 오버레이 생성
        this.createTourOverlay();

        // 가이드 스타일 주입
        this.injectGuideStyles();
    }

    /**
     * 가이드 모달 생성
     */
    createGuideModal() {
        const modal = document.createElement('div');
        modal.id = 'offline-guide-modal';
        modal.className = 'offline-guide-modal';
        modal.innerHTML = `
            <div class="guide-modal-backdrop"></div>
            <div class="guide-modal-container">
                <div class="guide-modal-header">
                    <h5 class="guide-modal-title"></h5>
                    <button type="button" class="guide-close-btn" onclick="offlineGuideSystem.closeGuide()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="guide-modal-body">
                    <!-- 가이드 내용이 동적으로 삽입됩니다 -->
                </div>
                <div class="guide-modal-actions">
                    <!-- 액션 버튼들이 동적으로 생성됩니다 -->
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.style.display = 'none';
    }

    /**
     * 도움말 버튼 생성
     */
    createHelpButton() {
        const helpButton = document.createElement('div');
        helpButton.id = 'offline-help-button';
        helpButton.className = 'offline-help-button';
        helpButton.innerHTML = `
            <button type="button" class="help-btn" title="도움말 및 가이드">
                <i class="fas fa-question-circle"></i>
            </button>
            <div class="help-menu">
                <div class="help-menu-item" onclick="offlineGuideSystem.showGuide('welcome')">
                    <i class="fas fa-play-circle"></i>
                    <span>시작 가이드</span>
                </div>
                <div class="help-menu-item" onclick="offlineGuideSystem.startFeatureTour()">
                    <i class="fas fa-route"></i>
                    <span>기능 투어</span>
                </div>
                <div class="help-menu-item" onclick="offlineGuideSystem.showGuide('offlineMode')">
                    <i class="fas fa-wifi-slash"></i>
                    <span>오프라인 가이드</span>
                </div>
                <div class="help-menu-item" onclick="offlineGuideSystem.showGuide('syncStatus')">
                    <i class="fas fa-sync"></i>
                    <span>동기화 가이드</span>
                </div>
                <div class="help-menu-item" onclick="offlineGuideSystem.showKeyboardShortcuts()">
                    <i class="fas fa-keyboard"></i>
                    <span>단축키</span>
                </div>
            </div>
        `;

        document.body.appendChild(helpButton);

        // 헬프 버튼 클릭 이벤트
        const btn = helpButton.querySelector('.help-btn');
        const menu = helpButton.querySelector('.help-menu');

        btn.addEventListener('click', () => {
            menu.classList.toggle('show');
        });

        // 외부 클릭 시 메뉴 닫기
        document.addEventListener('click', (event) => {
            if (!helpButton.contains(event.target)) {
                menu.classList.remove('show');
            }
        });
    }

    /**
     * 투어 오버레이 생성
     */
    createTourOverlay() {
        const overlay = document.createElement('div');
        overlay.id = 'tour-overlay';
        overlay.className = 'tour-overlay';
        overlay.innerHTML = `
            <div class="tour-backdrop"></div>
            <div class="tour-spotlight"></div>
            <div class="tour-tooltip">
                <div class="tour-tooltip-header">
                    <h6 class="tour-tooltip-title"></h6>
                    <div class="tour-tooltip-progress">
                        <span class="current-step">1</span> / <span class="total-steps">5</span>
                    </div>
                </div>
                <div class="tour-tooltip-content"></div>
                <div class="tour-tooltip-actions">
                    <button type="button" class="btn btn-sm btn-outline-secondary" onclick="offlineGuideSystem.previousTourStep()">
                        이전
                    </button>
                    <button type="button" class="btn btn-sm btn-primary" onclick="offlineGuideSystem.nextTourStep()">
                        다음
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="offlineGuideSystem.endTour()">
                        종료
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        overlay.style.display = 'none';
    }

    /**
     * 가이드 스타일 주입
     */
    injectGuideStyles() {
        const styles = `
            <style id="offline-guide-styles">
                /* 가이드 모달 */
                .offline-guide-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    z-index: 10000;
                }
                
                .guide-modal-backdrop {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.6);
                    backdrop-filter: blur(4px);
                }
                
                .guide-modal-container {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    width: 90%;
                    max-width: 600px;
                    max-height: 80vh;
                    background: white;
                    border-radius: 16px;
                    box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
                    overflow: hidden;
                    animation: guideModalFadeIn 0.3s ease-out;
                }
                
                @keyframes guideModalFadeIn {
                    from {
                        opacity: 0;
                        transform: translate(-50%, -50%) scale(0.9);
                    }
                    to {
                        opacity: 1;
                        transform: translate(-50%, -50%) scale(1);
                    }
                }
                
                .guide-modal-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 20px 24px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                
                .guide-modal-title {
                    margin: 0;
                    font-size: 18px;
                    font-weight: 600;
                }
                
                .guide-close-btn {
                    background: none;
                    border: none;
                    color: white;
                    font-size: 20px;
                    cursor: pointer;
                    padding: 4px;
                    border-radius: 4px;
                    transition: background-color 0.2s ease;
                }
                
                .guide-close-btn:hover {
                    background: rgba(255, 255, 255, 0.2);
                }
                
                .guide-modal-body {
                    padding: 24px;
                    max-height: 60vh;
                    overflow-y: auto;
                }
                
                .guide-modal-actions {
                    padding: 16px 24px;
                    background: #f8f9fa;
                    border-top: 1px solid #dee2e6;
                    display: flex;
                    justify-content: flex-end;
                    gap: 12px;
                }

                /* 기능 하이라이트 */
                .feature-highlights {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 16px;
                    margin: 20px 0;
                }
                
                .feature-item {
                    text-align: center;
                    padding: 20px;
                    background: #f8f9fa;
                    border-radius: 12px;
                    border: 1px solid #e9ecef;
                }
                
                .feature-item i {
                    font-size: 32px;
                    margin-bottom: 12px;
                }
                
                .feature-item h6 {
                    margin: 8px 0;
                    color: #495057;
                    font-weight: 600;
                }
                
                .feature-item p {
                    margin: 0;
                    font-size: 14px;
                    color: #6c757d;
                }

                /* 기능 목록 */
                .available-features, .limited-features {
                    list-style: none;
                    padding: 0;
                    margin: 12px 0;
                }
                
                .available-features li, .limited-features li {
                    padding: 8px 0;
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    font-size: 14px;
                }
                
                .available-features i {
                    width: 20px;
                    text-align: center;
                }
                
                .limited-features i {
                    width: 20px;
                    text-align: center;
                }

                /* 동기화 상태 가이드 */
                .sync-status-guide {
                    margin: 16px 0;
                }
                
                .status-item {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    padding: 12px;
                    margin: 8px 0;
                    border-radius: 8px;
                    background: #f8f9fa;
                }
                
                .status-indicator {
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                    flex-shrink: 0;
                }
                
                .status-indicator.success {
                    background: #28a745;
                }
                
                .status-indicator.syncing {
                    background: #ffc107;
                    animation: pulse 1.5s ease-in-out infinite alternate;
                }
                
                .status-indicator.error {
                    background: #dc3545;
                }
                
                @keyframes pulse {
                    from { opacity: 1; }
                    to { opacity: 0.5; }
                }
                
                .status-item strong {
                    display: block;
                    margin-bottom: 4px;
                }
                
                .status-item p {
                    margin: 0;
                    font-size: 13px;
                    color: #6c757d;
                }

                /* 도움말 버튼 */
                .offline-help-button {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    z-index: 9999;
                }
                
                .help-btn {
                    width: 56px;
                    height: 56px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border: none;
                    color: white;
                    font-size: 24px;
                    cursor: pointer;
                    box-shadow: 0 8px 16px rgba(102, 126, 234, 0.4);
                    transition: all 0.3s ease;
                }
                
                .help-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 12px 24px rgba(102, 126, 234, 0.5);
                }
                
                .help-menu {
                    position: absolute;
                    bottom: 70px;
                    right: 0;
                    min-width: 200px;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
                    border: 1px solid #e9ecef;
                    opacity: 0;
                    transform: translateY(10px);
                    visibility: hidden;
                    transition: all 0.3s ease;
                }
                
                .help-menu.show {
                    opacity: 1;
                    transform: translateY(0);
                    visibility: visible;
                }
                
                .help-menu-item {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 12px 16px;
                    cursor: pointer;
                    transition: background-color 0.2s ease;
                    font-size: 14px;
                }
                
                .help-menu-item:hover {
                    background: #f8f9fa;
                }
                
                .help-menu-item:first-child {
                    border-radius: 12px 12px 0 0;
                }
                
                .help-menu-item:last-child {
                    border-radius: 0 0 12px 12px;
                }
                
                .help-menu-item i {
                    width: 16px;
                    text-align: center;
                    color: #667eea;
                }

                /* 투어 오버레이 */
                .tour-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    z-index: 10001;
                    pointer-events: none;
                }
                
                .tour-backdrop {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.8);
                    backdrop-filter: blur(3px);
                }
                
                .tour-spotlight {
                    position: absolute;
                    border-radius: 8px;
                    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.8);
                    transition: all 0.5s ease;
                }
                
                .tour-tooltip {
                    position: absolute;
                    width: 320px;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.2);
                    pointer-events: all;
                    animation: tooltipFadeIn 0.3s ease-out;
                }
                
                @keyframes tooltipFadeIn {
                    from {
                        opacity: 0;
                        transform: scale(0.9);
                    }
                    to {
                        opacity: 1;
                        transform: scale(1);
                    }
                }
                
                .tour-tooltip-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 16px 20px;
                    background: #667eea;
                    color: white;
                    border-radius: 12px 12px 0 0;
                }
                
                .tour-tooltip-title {
                    margin: 0;
                    font-size: 16px;
                    font-weight: 600;
                }
                
                .tour-tooltip-progress {
                    font-size: 12px;
                    opacity: 0.9;
                }
                
                .tour-tooltip-content {
                    padding: 20px;
                    font-size: 14px;
                    line-height: 1.6;
                }
                
                .tour-tooltip-actions {
                    padding: 12px 20px 20px;
                    display: flex;
                    justify-content: space-between;
                    gap: 8px;
                }

                /* 투어 진행 표시 */
                .tour-progress {
                    margin: 20px 0;
                }
                
                .tour-progress .progress {
                    height: 6px;
                    background: #e9ecef;
                    border-radius: 3px;
                    margin-bottom: 8px;
                }
                
                .tour-progress .progress-bar {
                    background: linear-gradient(90deg, #667eea, #764ba2);
                    height: 100%;
                    border-radius: 3px;
                    transition: width 0.3s ease;
                }

                /* 반응형 조정 */
                @media (max-width: 768px) {
                    .guide-modal-container {
                        width: 95%;
                        max-height: 90vh;
                    }
                    
                    .feature-highlights {
                        grid-template-columns: 1fr;
                    }
                    
                    .tour-tooltip {
                        width: 280px;
                    }
                    
                    .offline-help-button {
                        bottom: 16px;
                        right: 16px;
                    }
                    
                    .help-btn {
                        width: 48px;
                        height: 48px;
                        font-size: 20px;
                    }
                }

                /* 애니메이션 효과 */
                .guide-fade-in {
                    animation: fadeInUp 0.5s ease-out;
                }
                
                @keyframes fadeInUp {
                    from {
                        opacity: 0;
                        transform: translateY(20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                /* 툴팁 스타일 */
                .offline-tooltip {
                    position: absolute;
                    background: rgba(0, 0, 0, 0.9);
                    color: white;
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-size: 12px;
                    z-index: 9998;
                    opacity: 0;
                    transition: opacity 0.3s ease;
                    pointer-events: none;
                    max-width: 200px;
                }
                
                .offline-tooltip.show {
                    opacity: 1;
                }
                
                .offline-tooltip::after {
                    content: '';
                    position: absolute;
                    top: 100%;
                    left: 50%;
                    margin-left: -5px;
                    border-width: 5px;
                    border-style: solid;
                    border-color: rgba(0, 0, 0, 0.9) transparent transparent transparent;
                }
            </style>
        `;

        document.head.insertAdjacentHTML('beforeend', styles);
    }

    /**
     * 이벤트 리스너 설정
     */
    async setupEventListeners() {
        // 오프라인 상태 변경 감지
        window.addEventListener('offlineStatusChange', (event) => {
            if (!event.detail.isOnline && !this.seenGuides.has('offlineMode')) {
                setTimeout(() => this.showGuide('offlineMode'), 1000);
            }
        });

        // 키보드 단축키
        document.addEventListener('keydown', (event) => {
            // F1: 도움말 표시
            if (event.key === 'F1') {
                event.preventDefault();
                this.showGuide('welcome');
            }
            
            // Ctrl+?: 단축키 도움말
            if (event.ctrlKey && event.key === '?') {
                event.preventDefault();
                this.showKeyboardShortcuts();
            }
            
            // ESC: 가이드 닫기
            if (event.key === 'Escape' && this.currentGuide) {
                this.closeGuide();
            }
        });

        // 가이드 모달 백드롭 클릭
        const modal = document.getElementById('offline-guide-modal');
        if (modal) {
            modal.querySelector('.guide-modal-backdrop').addEventListener('click', () => {
                this.closeGuide();
            });
        }
    }

    /**
     * 기능 툴팁 초기화
     */
    async initializeFeatureTooltips() {
        if (!this.config.showFeatureTooltips) return;

        // 오프라인 관련 기능들에 툴팁 추가
        const tooltipElements = [
            { selector: '[data-widget-id]', content: '오프라인에서도 사용 가능한 위젯입니다' },
            { selector: '.sync-status', content: '데이터 동기화 상태를 표시합니다' },
            { selector: '.offline-indicator', content: '현재 오프라인 모드입니다' },
            { selector: '.data-freshness-indicator', content: '데이터의 최신성을 나타냅니다' }
        ];

        tooltipElements.forEach(({ selector, content }) => {
            document.querySelectorAll(selector).forEach(element => {
                this.addTooltip(element, content);
            });
        });
    }

    /**
     * 툴팁 추가
     */
    addTooltip(element, content) {
        let tooltip = null;
        let timeoutId = null;

        const showTooltip = (event) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                if (tooltip) return;

                tooltip = document.createElement('div');
                tooltip.className = 'offline-tooltip';
                tooltip.textContent = content;
                document.body.appendChild(tooltip);

                const rect = element.getBoundingClientRect();
                tooltip.style.left = `${rect.left + rect.width / 2}px`;
                tooltip.style.top = `${rect.top - tooltip.offsetHeight - 8}px`;
                tooltip.style.transform = 'translateX(-50%)';

                requestAnimationFrame(() => {
                    tooltip.classList.add('show');
                });
            }, this.config.tooltipDelay);
        };

        const hideTooltip = () => {
            clearTimeout(timeoutId);
            if (tooltip) {
                tooltip.classList.remove('show');
                setTimeout(() => {
                    if (tooltip && tooltip.parentNode) {
                        tooltip.parentNode.removeChild(tooltip);
                    }
                    tooltip = null;
                }, 300);
            }
        };

        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
        element.addEventListener('focus', showTooltip);
        element.addEventListener('blur', hideTooltip);
    }

    /**
     * 오프라인 도움말 설정
     */
    async setupOfflineHelp() {
        // PWA 설치 가이드
        window.addEventListener('beforeinstallprompt', (event) => {
            if (!this.seenGuides.has('pwaInstall')) {
                setTimeout(() => this.showPWAInstallGuide(event), 2000);
            }
        });
    }

    /**
     * 가이드 표시
     */
    showGuide(guideId, options = {}) {
        const template = this.guideTemplates.get(guideId);
        if (!template) {
            console.warn(`[OfflineGuideSystem] Guide template not found: ${guideId}`);
            return;
        }

        this.currentGuide = guideId;
        const modal = document.getElementById('offline-guide-modal');
        
        // 제목 설정
        const title = modal.querySelector('.guide-modal-title');
        title.innerHTML = template.title;
        
        // 내용 설정
        const body = modal.querySelector('.guide-modal-body');
        body.innerHTML = template.content;
        
        // 액션 버튼 설정
        const actions = modal.querySelector('.guide-modal-actions');
        actions.innerHTML = '';
        
        template.actions.forEach(action => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `btn ${action.className}`;
            button.textContent = action.label;
            button.onclick = () => this.handleAction(action.action, guideId);
            actions.appendChild(button);
        });

        // 모달 표시
        modal.style.display = 'block';
        
        // 애니메이션
        setTimeout(() => {
            modal.classList.add('show');
        }, 10);

        // 가이드 표시 기록
        if (!options.skipTracking) {
            this.seenGuides.add(guideId);
            this.saveSeenGuides();
        }
    }

    /**
     * 가이드 닫기
     */
    closeGuide() {
        const modal = document.getElementById('offline-guide-modal');
        modal.classList.remove('show');
        
        setTimeout(() => {
            modal.style.display = 'none';
            this.currentGuide = null;
        }, this.config.guideAnimationDuration);
    }

    /**
     * 액션 처리
     */
    handleAction(action, guideId) {
        switch (action) {
            case 'close':
                this.closeGuide();
                break;
                
            case 'startTour':
                this.closeGuide();
                setTimeout(() => this.startFeatureTour(), 500);
                break;
                
            case 'nextTourStep':
                this.nextTourStep();
                break;
                
            case 'previousTourStep':
                this.previousTourStep();
                break;
                
            default:
                console.warn(`[OfflineGuideSystem] Unknown action: ${action}`);
        }
    }

    /**
     * 환영 가이드 표시
     */
    showWelcomeGuide() {
        this.showGuide('welcome');
    }

    /**
     * 기능 투어 시작
     */
    startFeatureTour() {
        this.tourSteps = [
            {
                target: '.dashboard-header',
                title: '대시보드 헤더',
                content: '여기서 동기화 상태와 네트워크 상태를 확인할 수 있습니다.',
                position: 'bottom'
            },
            {
                target: '[data-widget-id="stats-overview"]',
                title: '통계 위젯',
                content: '주요 통계들을 한눈에 볼 수 있으며, 오프라인에서도 이용 가능합니다.',
                position: 'right'
            },
            {
                target: '[data-widget-id="notifications"]',
                title: '알림 위젯',
                content: '최근 알림들을 확인할 수 있으며, 오프라인 상태에서도 저장된 알림을 볼 수 있습니다.',
                position: 'left'
            },
            {
                target: '.offline-help-button',
                title: '도움말 버튼',
                content: '언제든지 이 버튼을 통해 가이드와 도움말에 접근할 수 있습니다.',
                position: 'left'
            },
            {
                target: 'body',
                title: '투어 완료!',
                content: 'OneSquare의 주요 기능들을 둘러보았습니다. 오프라인에서도 대부분의 기능을 자유롭게 사용하세요!',
                position: 'center'
            }
        ];

        this.currentTourStep = 0;
        this.showTourStep();
    }

    /**
     * 투어 단계 표시
     */
    showTourStep() {
        if (this.currentTourStep >= this.tourSteps.length) {
            this.endTour();
            return;
        }

        const step = this.tourSteps[this.currentTourStep];
        const overlay = document.getElementById('tour-overlay');
        const spotlight = overlay.querySelector('.tour-spotlight');
        const tooltip = overlay.querySelector('.tour-tooltip');

        // 대상 요소 찾기
        const target = step.target === 'body' ? document.body : document.querySelector(step.target);
        if (!target && step.target !== 'body') {
            console.warn(`[OfflineGuideSystem] Tour target not found: ${step.target}`);
            this.nextTourStep();
            return;
        }

        // 스포트라이트 위치 설정
        if (target && step.target !== 'body') {
            const rect = target.getBoundingClientRect();
            spotlight.style.left = `${rect.left - 8}px`;
            spotlight.style.top = `${rect.top - 8}px`;
            spotlight.style.width = `${rect.width + 16}px`;
            spotlight.style.height = `${rect.height + 16}px`;
        } else {
            // 중앙 표시
            spotlight.style.left = '50%';
            spotlight.style.top = '50%';
            spotlight.style.width = '0px';
            spotlight.style.height = '0px';
            spotlight.style.transform = 'translate(-50%, -50%)';
        }

        // 툴팁 내용 설정
        tooltip.querySelector('.tour-tooltip-title').textContent = step.title;
        tooltip.querySelector('.tour-tooltip-content').textContent = step.content;
        tooltip.querySelector('.current-step').textContent = this.currentTourStep + 1;
        tooltip.querySelector('.total-steps').textContent = this.tourSteps.length;

        // 툴팁 위치 설정
        this.positionTourTooltip(tooltip, target, step.position);

        // 이전/다음 버튼 상태 조정
        const prevBtn = tooltip.querySelector('.tour-tooltip-actions .btn:nth-child(1)');
        const nextBtn = tooltip.querySelector('.tour-tooltip-actions .btn:nth-child(2)');
        
        prevBtn.style.display = this.currentTourStep === 0 ? 'none' : 'inline-block';
        nextBtn.textContent = this.currentTourStep === this.tourSteps.length - 1 ? '완료' : '다음';

        // 오버레이 표시
        overlay.style.display = 'block';
    }

    /**
     * 투어 툴팁 위치 설정
     */
    positionTourTooltip(tooltip, target, position) {
        if (!target || position === 'center') {
            // 중앙에 표시
            tooltip.style.left = '50%';
            tooltip.style.top = '50%';
            tooltip.style.transform = 'translate(-50%, -50%)';
            return;
        }

        const rect = target.getBoundingClientRect();
        const tooltipRect = tooltip.getBoundingClientRect();
        
        let left, top, transform = '';

        switch (position) {
            case 'top':
                left = rect.left + rect.width / 2;
                top = rect.top - tooltipRect.height - 20;
                transform = 'translateX(-50%)';
                break;
                
            case 'bottom':
                left = rect.left + rect.width / 2;
                top = rect.bottom + 20;
                transform = 'translateX(-50%)';
                break;
                
            case 'left':
                left = rect.left - tooltipRect.width - 20;
                top = rect.top + rect.height / 2;
                transform = 'translateY(-50%)';
                break;
                
            case 'right':
                left = rect.right + 20;
                top = rect.top + rect.height / 2;
                transform = 'translateY(-50%)';
                break;
                
            default:
                left = rect.left + rect.width / 2;
                top = rect.bottom + 20;
                transform = 'translateX(-50%)';
        }

        // 화면 경계 체크
        const margin = 20;
        if (left < margin) left = margin;
        if (left + tooltipRect.width > window.innerWidth - margin) {
            left = window.innerWidth - tooltipRect.width - margin;
        }
        if (top < margin) top = margin;
        if (top + tooltipRect.height > window.innerHeight - margin) {
            top = window.innerHeight - tooltipRect.height - margin;
        }

        tooltip.style.left = `${left}px`;
        tooltip.style.top = `${top}px`;
        tooltip.style.transform = transform;
    }

    /**
     * 다음 투어 단계
     */
    nextTourStep() {
        this.currentTourStep++;
        this.showTourStep();
    }

    /**
     * 이전 투어 단계
     */
    previousTourStep() {
        if (this.currentTourStep > 0) {
            this.currentTourStep--;
            this.showTourStep();
        }
    }

    /**
     * 투어 종료
     */
    endTour() {
        const overlay = document.getElementById('tour-overlay');
        overlay.style.display = 'none';
        
        this.currentTourStep = 0;
        this.tourSteps = [];
        
        // 투어 완료 기록
        this.seenGuides.add('featureTour');
        this.saveSeenGuides();
    }

    /**
     * PWA 설치 가이드 표시
     */
    showPWAInstallGuide(installPrompt) {
        this.guideTemplates.set('pwaInstall', {
            title: '📱 앱으로 설치하기',
            content: `
                <div class="guide-content">
                    <p>OneSquare를 모바일 앱처럼 사용해보세요!</p>
                    <div class="pwa-benefits">
                        <div class="benefit-item">
                            <i class="fas fa-rocket text-primary"></i>
                            <span>빠른 시작</span>
                        </div>
                        <div class="benefit-item">
                            <i class="fas fa-wifi-slash text-success"></i>
                            <span>오프라인 지원</span>
                        </div>
                        <div class="benefit-item">
                            <i class="fas fa-mobile-alt text-info"></i>
                            <span>앱과 같은 경험</span>
                        </div>
                    </div>
                    <p class="mt-3">
                        <small class="text-muted">
                            설치 후에도 브라우저에서 계속 사용할 수 있습니다.
                        </small>
                    </p>
                </div>
            `,
            actions: [
                { 
                    label: '설치하기', 
                    action: () => {
                        installPrompt.prompt();
                        this.closeGuide();
                    }, 
                    className: 'btn-primary' 
                },
                { label: '나중에', action: 'close', className: 'btn-outline-secondary' }
            ]
        });

        this.showGuide('pwaInstall');
    }

    /**
     * 키보드 단축키 가이드 표시
     */
    showKeyboardShortcuts() {
        this.guideTemplates.set('keyboardShortcuts', {
            title: '⌨️ 키보드 단축키',
            content: `
                <div class="guide-content">
                    <div class="shortcuts-list">
                        <div class="shortcut-item">
                            <kbd>F1</kbd>
                            <span>도움말 표시</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>?</kbd>
                            <span>단축키 목록</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>O</kbd>
                            <span>오프라인 가이드</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>ESC</kbd>
                            <span>가이드/모달 닫기</span>
                        </div>
                        <div class="shortcut-item">
                            <kbd>F5</kbd> / <kbd>Ctrl</kbd> + <kbd>R</kbd>
                            <span>페이지 새로고침</span>
                        </div>
                    </div>
                </div>
                <style>
                    .shortcuts-list {
                        display: flex;
                        flex-direction: column;
                        gap: 12px;
                    }
                    .shortcut-item {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 8px 0;
                        border-bottom: 1px solid #e9ecef;
                    }
                    .shortcut-item:last-child {
                        border-bottom: none;
                    }
                    kbd {
                        background: #f8f9fa;
                        border: 1px solid #ccc;
                        border-radius: 4px;
                        padding: 2px 6px;
                        font-size: 12px;
                        font-family: monospace;
                        margin: 0 2px;
                    }
                </style>
            `,
            actions: [
                { label: '확인', action: 'close', className: 'btn-primary' }
            ]
        });

        this.showGuide('keyboardShortcuts');
    }

    /**
     * 본 가이드 목록 저장
     */
    saveSeenGuides() {
        localStorage.setItem('seenOfflineGuides', JSON.stringify([...this.seenGuides]));
    }

    /**
     * 가이드 상태 초기화
     */
    resetGuides() {
        this.seenGuides.clear();
        localStorage.removeItem('seenOfflineGuides');
        console.log('[OfflineGuideSystem] Guide state reset');
    }

    /**
     * 현재 상태 조회
     */
    getStatus() {
        return {
            currentGuide: this.currentGuide,
            seenGuides: [...this.seenGuides],
            tourInProgress: this.tourSteps.length > 0,
            currentTourStep: this.currentTourStep,
            config: this.config
        };
    }

    /**
     * 정리
     */
    destroy() {
        // 모든 UI 요소 제거
        const elementsToRemove = [
            '#offline-guide-modal',
            '#offline-help-button',
            '#tour-overlay',
            '#offline-guide-styles'
        ];

        elementsToRemove.forEach(selector => {
            const element = document.querySelector(selector);
            if (element && element.parentNode) {
                element.parentNode.removeChild(element);
            }
        });

        // 툴팁 제거
        this.activeTooltips.forEach(tooltip => {
            if (tooltip.parentNode) {
                tooltip.parentNode.removeChild(tooltip);
            }
        });

        this.activeTooltips.clear();
        this.currentGuide = null;
        this.tourSteps = [];

        console.log('[OfflineGuideSystem] Offline guide system destroyed');
    }
}

// 전역으로 내보내기
window.OfflineGuideSystem = OfflineGuideSystem;

// 자동 초기화
window.addEventListener('DOMContentLoaded', () => {
    if (window.oneSquareConfig?.enableOfflineGuide !== false) {
        window.offlineGuideSystem = new OfflineGuideSystem();
    }
});