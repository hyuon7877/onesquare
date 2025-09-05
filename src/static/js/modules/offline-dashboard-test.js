/**
 * OneSquare 오프라인 대시보드 테스트 스위트
 * 
 * 오프라인 대시보드 기능을 종합적으로 테스트하는 도구
 * 개발 중 기능 검증 및 품질 보장을 위한 자동화된 테스트 시나리오
 */

class OfflineDashboardTest {
    constructor(config = {}) {
        this.config = {
            enableAutoTest: config.enableAutoTest || false,
            testInterval: config.testInterval || 30000, // 30초
            logLevel: config.logLevel || 'info', // 'debug', 'info', 'warn', 'error'
            enableStressTest: config.enableStressTest || false,
            ...config
        };

        this.testResults = [];
        this.isRunning = false;
        this.currentTest = null;
        
        // 테스트 시나리오들
        this.testScenarios = new Map();
        this.setupTestScenarios();

        if (this.config.enableAutoTest) {
            this.startAutoTesting();
        }
    }

    /**
     * 테스트 시나리오 설정
     */
    setupTestScenarios() {
        // 1. 기본 초기화 테스트
        this.testScenarios.set('initialization', {
            name: '시스템 초기화 테스트',
            description: '오프라인 대시보드 시스템의 기본 초기화 확인',
            test: this.testInitialization.bind(this),
            timeout: 10000
        });

        // 2. 저장소 기능 테스트
        this.testScenarios.set('storage', {
            name: '오프라인 저장소 테스트',
            description: 'IndexedDB 저장소의 CRUD 기능 확인',
            test: this.testStorage.bind(this),
            timeout: 5000
        });

        // 3. UI 컴포넌트 테스트
        this.testScenarios.set('ui', {
            name: 'UI 컴포넌트 테스트',
            description: '오프라인 상태 표시 및 UI 반응성 확인',
            test: this.testUI.bind(this),
            timeout: 3000
        });

        // 4. 동기화 시스템 테스트
        this.testScenarios.set('sync', {
            name: '데이터 동기화 테스트',
            description: '온라인/오프라인 전환 시 데이터 동기화 확인',
            test: this.testSync.bind(this),
            timeout: 15000
        });

        // 5. 가이드 시스템 테스트
        this.testScenarios.set('guide', {
            name: '가이드 시스템 테스트',
            description: '사용자 가이드 및 도움말 기능 확인',
            test: this.testGuide.bind(this),
            timeout: 3000
        });

        // 6. 네트워크 시뮬레이션 테스트
        this.testScenarios.set('network', {
            name: '네트워크 상태 시뮬레이션',
            description: '오프라인/온라인 전환 시나리오 테스트',
            test: this.testNetworkSimulation.bind(this),
            timeout: 10000
        });

        // 7. 성능 테스트
        this.testScenarios.set('performance', {
            name: '성능 벤치마크',
            description: '오프라인 기능의 성능 지표 측정',
            test: this.testPerformance.bind(this),
            timeout: 5000
        });

        // 8. 스트레스 테스트 (선택적)
        if (this.config.enableStressTest) {
            this.testScenarios.set('stress', {
                name: '스트레스 테스트',
                description: '대량 데이터 처리 및 장시간 동작 테스트',
                test: this.testStress.bind(this),
                timeout: 30000
            });
        }
    }

    /**
     * 모든 테스트 실행
     */
    async runAllTests() {
        if (this.isRunning) {
            throw new Error('Tests already running');
        }

        this.isRunning = true;
        const startTime = Date.now();
        const results = {
            startTime: startTime,
            tests: [],
            summary: {
                total: this.testScenarios.size,
                passed: 0,
                failed: 0,
                skipped: 0
            }
        };

        this.log('info', 'Starting offline dashboard test suite...');

        for (const [testId, scenario] of this.testScenarios) {
            try {
                this.currentTest = testId;
                this.log('info', `Running test: ${scenario.name}`);

                const testResult = await this.runTest(testId, scenario);
                results.tests.push(testResult);

                if (testResult.passed) {
                    results.summary.passed++;
                    this.log('info', `✅ ${scenario.name} - PASSED (${testResult.duration}ms)`);
                } else {
                    results.summary.failed++;
                    this.log('error', `❌ ${scenario.name} - FAILED: ${testResult.error}`, testResult.details);
                }

            } catch (error) {
                results.summary.failed++;
                this.log('error', `💥 ${scenario.name} - EXCEPTION: ${error.message}`);
                
                results.tests.push({
                    testId: testId,
                    name: scenario.name,
                    passed: false,
                    error: error.message,
                    duration: 0,
                    timestamp: Date.now()
                });
            }

            // 테스트 간 짧은 지연
            await this.sleep(500);
        }

        results.endTime = Date.now();
        results.totalDuration = results.endTime - startTime;

        this.isRunning = false;
        this.currentTest = null;

        this.log('info', `Test suite completed in ${results.totalDuration}ms`);
        this.log('info', `Results: ${results.summary.passed} passed, ${results.summary.failed} failed`);

        // 테스트 결과 저장
        this.testResults.push(results);

        // 테스트 완료 이벤트 발생
        window.dispatchEvent(new CustomEvent('offlineTestCompleted', {
            detail: results
        }));

        return results;
    }

    /**
     * 개별 테스트 실행
     */
    async runTest(testId, scenario) {
        const startTime = Date.now();
        
        try {
            // 타임아웃 설정
            const timeoutPromise = new Promise((_, reject) => {
                setTimeout(() => reject(new Error('Test timeout')), scenario.timeout);
            });

            // 테스트 실행
            const testPromise = scenario.test();
            
            const result = await Promise.race([testPromise, timeoutPromise]);
            
            return {
                testId: testId,
                name: scenario.name,
                passed: true,
                result: result,
                duration: Date.now() - startTime,
                timestamp: Date.now()
            };

        } catch (error) {
            return {
                testId: testId,
                name: scenario.name,
                passed: false,
                error: error.message,
                details: error,
                duration: Date.now() - startTime,
                timestamp: Date.now()
            };
        }
    }

    /**
     * 시스템 초기화 테스트
     */
    async testInitialization() {
        const orchestrator = window.offlineDashboard;
        
        if (!orchestrator) {
            throw new Error('Offline dashboard orchestrator not found');
        }

        const status = orchestrator.getSystemStatus();
        
        if (!status.isInitialized) {
            throw new Error('System not initialized');
        }

        // 필수 컴포넌트 확인
        const requiredComponents = ['storage'];
        for (const component of requiredComponents) {
            if (!status.components.instances[component]) {
                throw new Error(`Required component missing: ${component}`);
            }
        }

        return {
            systemStatus: status,
            componentsReady: Object.keys(status.components.instances).filter(
                key => status.components.instances[key]
            )
        };
    }

    /**
     * 저장소 기능 테스트
     */
    async testStorage() {
        const orchestrator = window.offlineDashboard;
        const storage = orchestrator?.components?.storage;
        
        if (!storage) {
            throw new Error('Storage component not available');
        }

        // 테스트 데이터
        const testData = {
            id: `test_${Date.now()}`,
            content: 'Test storage content',
            timestamp: Date.now(),
            metadata: { test: true }
        };

        // 1. 데이터 저장 테스트
        await storage.updateMetadata(testData.id, testData);

        // 2. 데이터 조회 테스트
        const retrieved = await storage.getMetadata(testData.id);
        
        if (!retrieved || retrieved.content !== testData.content) {
            throw new Error('Storage read/write verification failed');
        }

        // 3. 저장소 상태 확인
        const storageStatus = storage.getStorageStatus();
        
        if (!storageStatus.isInitialized) {
            throw new Error('Storage not properly initialized');
        }

        return {
            testData: testData,
            retrieved: retrieved,
            storageStatus: storageStatus
        };
    }

    /**
     * UI 컴포넌트 테스트
     */
    async testUI() {
        const orchestrator = window.offlineDashboard;
        const ui = orchestrator?.components?.ui;
        
        if (!ui) {
            // UI 컴포넌트는 선택적이므로 경고만 출력
            this.log('warn', 'UI component not available, skipping UI tests');
            return { status: 'skipped', reason: 'UI component not available' };
        }

        const uiStatus = ui.getStatus();
        
        // UI 요소 존재 확인
        const expectedElements = [
            '#offline-guide-modal',
            '.offline-help-button'
        ];

        const missingElements = [];
        expectedElements.forEach(selector => {
            if (!document.querySelector(selector)) {
                missingElements.push(selector);
            }
        });

        if (missingElements.length > 0) {
            throw new Error(`Missing UI elements: ${missingElements.join(', ')}`);
        }

        return {
            uiStatus: uiStatus,
            elementsChecked: expectedElements.length,
            missingElements: missingElements
        };
    }

    /**
     * 동기화 시스템 테스트
     */
    async testSync() {
        const orchestrator = window.offlineDashboard;
        const sync = orchestrator?.components?.sync;
        
        if (!sync) {
            this.log('warn', 'Sync component not available, skipping sync tests');
            return { status: 'skipped', reason: 'Sync component not available' };
        }

        const syncStats = sync.getSyncStats();
        
        // 동기화 대기열 크기 확인
        if (syncStats.queueSize > 100) {
            throw new Error('Sync queue size too large');
        }

        // 최근 동기화 실패 확인
        if (syncStats.failedSyncAttempts > 5) {
            throw new Error('Too many recent sync failures');
        }

        return {
            syncStats: syncStats,
            queueHealthy: syncStats.queueSize <= 100,
            failureRateAcceptable: syncStats.failedSyncAttempts <= 5
        };
    }

    /**
     * 가이드 시스템 테스트
     */
    async testGuide() {
        const orchestrator = window.offlineDashboard;
        const guide = orchestrator?.components?.guide;
        
        if (!guide) {
            this.log('warn', 'Guide component not available, skipping guide tests');
            return { status: 'skipped', reason: 'Guide component not available' };
        }

        const guideStatus = guide.getStatus();

        // 가이드 템플릿 확인
        const hasWelcomeGuide = guide.guideTemplates?.has('welcome');
        const hasOfflineGuide = guide.guideTemplates?.has('offlineMode');

        return {
            guideStatus: guideStatus,
            hasWelcomeGuide: hasWelcomeGuide,
            hasOfflineGuide: hasOfflineGuide
        };
    }

    /**
     * 네트워크 시뮬레이션 테스트
     */
    async testNetworkSimulation() {
        // 네트워크 상태 시뮬레이션은 실제 네트워크를 끊을 수 없으므로
        // 이벤트 시뮬레이션으로 테스트
        const orchestrator = window.offlineDashboard;
        
        if (!orchestrator) {
            throw new Error('Orchestrator not available');
        }

        const initialState = orchestrator.state.isOffline;
        
        // 오프라인 이벤트 시뮬레이션
        await orchestrator.handleNetworkChange(false);
        
        if (!orchestrator.state.isOffline) {
            throw new Error('Offline state not properly set');
        }

        // 온라인 이벤트 시뮬레이션  
        await orchestrator.handleNetworkChange(true);
        
        if (orchestrator.state.isOffline) {
            throw new Error('Online state not properly restored');
        }

        // 원래 상태로 복원
        await orchestrator.handleNetworkChange(!initialState);

        return {
            initialState: initialState,
            offlineSimulated: true,
            onlineSimulated: true,
            stateRestored: true
        };
    }

    /**
     * 성능 테스트
     */
    async testPerformance() {
        const orchestrator = window.offlineDashboard;
        const storage = orchestrator?.components?.storage;
        
        if (!storage) {
            throw new Error('Storage component required for performance test');
        }

        const performanceMetrics = {
            storageWrite: [],
            storageRead: [],
            healthCheck: null
        };

        // 저장소 쓰기 성능 측정 (10회 반복)
        for (let i = 0; i < 10; i++) {
            const startTime = performance.now();
            await storage.updateMetadata(`perf_test_${i}`, { 
                data: 'performance test data',
                iteration: i,
                timestamp: Date.now()
            });
            performanceMetrics.storageWrite.push(performance.now() - startTime);
        }

        // 저장소 읽기 성능 측정
        for (let i = 0; i < 10; i++) {
            const startTime = performance.now();
            await storage.getMetadata(`perf_test_${i}`);
            performanceMetrics.storageRead.push(performance.now() - startTime);
        }

        // 헬스 체크 성능 측정
        const healthCheckStart = performance.now();
        await orchestrator.performHealthCheck();
        performanceMetrics.healthCheck = performance.now() - healthCheckStart;

        // 평균 계산
        const avgWrite = performanceMetrics.storageWrite.reduce((a, b) => a + b, 0) / performanceMetrics.storageWrite.length;
        const avgRead = performanceMetrics.storageRead.reduce((a, b) => a + b, 0) / performanceMetrics.storageRead.length;

        // 성능 임계값 확인
        if (avgWrite > 100) { // 100ms
            throw new Error(`Storage write too slow: ${avgWrite.toFixed(2)}ms`);
        }

        if (avgRead > 50) { // 50ms
            throw new Error(`Storage read too slow: ${avgRead.toFixed(2)}ms`);
        }

        return {
            averageWriteTime: avgWrite,
            averageReadTime: avgRead,
            healthCheckTime: performanceMetrics.healthCheck,
            rawMetrics: performanceMetrics
        };
    }

    /**
     * 스트레스 테스트
     */
    async testStress() {
        const orchestrator = window.offlineDashboard;
        const storage = orchestrator?.components?.storage;
        
        if (!storage) {
            throw new Error('Storage component required for stress test');
        }

        const stressMetrics = {
            dataSize: 1000, // 1000개 항목
            operations: 0,
            errors: 0,
            startTime: Date.now()
        };

        // 대량 데이터 생성 및 저장
        const promises = [];
        for (let i = 0; i < stressMetrics.dataSize; i++) {
            promises.push(
                storage.updateMetadata(`stress_test_${i}`, {
                    index: i,
                    data: `Stress test data item ${i}`,
                    randomData: Math.random().toString(36).repeat(10),
                    timestamp: Date.now()
                }).then(() => {
                    stressMetrics.operations++;
                }).catch(() => {
                    stressMetrics.errors++;
                })
            );
        }

        await Promise.allSettled(promises);

        stressMetrics.endTime = Date.now();
        stressMetrics.duration = stressMetrics.endTime - stressMetrics.startTime;
        stressMetrics.opsPerSecond = stressMetrics.operations / (stressMetrics.duration / 1000);

        // 스트레스 테스트 기준
        if (stressMetrics.errors > stressMetrics.dataSize * 0.1) { // 10% 이상 실패
            throw new Error(`Too many errors in stress test: ${stressMetrics.errors}/${stressMetrics.dataSize}`);
        }

        if (stressMetrics.opsPerSecond < 10) { // 초당 10개 미만
            throw new Error(`Performance too slow: ${stressMetrics.opsPerSecond.toFixed(2)} ops/sec`);
        }

        return stressMetrics;
    }

    /**
     * 자동 테스트 시작
     */
    startAutoTesting() {
        this.log('info', 'Starting automatic testing...');
        
        setInterval(async () => {
            if (!this.isRunning) {
                try {
                    await this.runAllTests();
                } catch (error) {
                    this.log('error', 'Auto test failed:', error);
                }
            }
        }, this.config.testInterval);
    }

    /**
     * 특정 테스트 실행
     */
    async runSingleTest(testId) {
        const scenario = this.testScenarios.get(testId);
        
        if (!scenario) {
            throw new Error(`Test not found: ${testId}`);
        }

        this.log('info', `Running single test: ${scenario.name}`);
        return await this.runTest(testId, scenario);
    }

    /**
     * 테스트 결과 조회
     */
    getTestResults(limit = 10) {
        return this.testResults.slice(-limit);
    }

    /**
     * 최근 테스트 결과 요약
     */
    getLastTestSummary() {
        if (this.testResults.length === 0) {
            return null;
        }

        const lastResult = this.testResults[this.testResults.length - 1];
        return {
            timestamp: lastResult.endTime,
            totalTests: lastResult.summary.total,
            passed: lastResult.summary.passed,
            failed: lastResult.summary.failed,
            successRate: (lastResult.summary.passed / lastResult.summary.total * 100).toFixed(1),
            duration: lastResult.totalDuration
        };
    }

    /**
     * 테스트 리포트 생성
     */
    generateReport() {
        const summary = this.getLastTestSummary();
        const fullResults = this.getTestResults(5);

        return {
            summary: summary,
            recentResults: fullResults,
            systemInfo: {
                userAgent: navigator.userAgent,
                online: navigator.onLine,
                timestamp: Date.now()
            },
            testConfig: this.config
        };
    }

    /**
     * 로그 출력
     */
    log(level, message, details = null) {
        if (!this.shouldLog(level)) {
            return;
        }

        const timestamp = new Date().toISOString();
        const logMessage = `[OfflineDashboardTest] ${timestamp} [${level.toUpperCase()}] ${message}`;

        switch (level) {
            case 'debug':
                console.debug(logMessage, details);
                break;
            case 'info':
                console.info(logMessage, details);
                break;
            case 'warn':
                console.warn(logMessage, details);
                break;
            case 'error':
                console.error(logMessage, details);
                break;
        }
    }

    /**
     * 로그 레벨 확인
     */
    shouldLog(level) {
        const levels = ['debug', 'info', 'warn', 'error'];
        const configLevel = levels.indexOf(this.config.logLevel);
        const currentLevel = levels.indexOf(level);
        
        return currentLevel >= configLevel;
    }

    /**
     * 유틸리티: 지연
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * 테스트 중단
     */
    stop() {
        this.isRunning = false;
        this.currentTest = null;
        this.log('info', 'Testing stopped');
    }

    /**
     * 테스트 결과 초기화
     */
    clearResults() {
        this.testResults = [];
        this.log('info', 'Test results cleared');
    }
}

// 전역으로 내보내기
window.OfflineDashboardTest = OfflineDashboardTest;

// 개발 모드에서 자동 초기화
if (window.location.search.includes('test=true') || localStorage.getItem('enableOfflineTest') === 'true') {
    window.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            window.offlineDashboardTest = new OfflineDashboardTest({
                enableAutoTest: false, // 수동으로 실행
                logLevel: 'info'
            });
            
            console.log('🧪 Offline Dashboard Test Suite loaded');
            console.log('Run tests with: offlineDashboardTest.runAllTests()');
        }, 5000); // 시스템이 완전히 로드된 후 실행
    });
}