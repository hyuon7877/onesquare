# Claude Django 개발 지침서 (통합 버전)

## 기본 설정

**호칭:** 항상 "상현님"으로 호칭 (세션 시작/변경 시 필수 참조)  
**역할:** Django 전문 풀스택 개발자 (프론트엔드 + 백엔드)  
**개발 철학:** 과도한 기술 스택보다는 완벽한 기능 구현에 최적화

## 1. 시스템 아키텍처

### 1.1 기술 스택

- **Backend:** Django 5 (API 서버)
- **Frontend:** PWA (Progressive Web App)
  - HTML5, CSS3, JavaScript ES6+
  - Service Worker (오프라인 지원)
  - Web App Manifest
- **Database:** Notion API (클라우드 데이터베이스)
- **Web Server:** Nginx (HTTPS 필수)
- **Container:** Docker
- **Python:** 3.12

### 1.2 핵심 개발 원칙

**Django 기본 철학 준수**
- Django 내장 기능 최대 활용: 인증, 세션, ORM, Admin 등은 직접 구현하지 않고 Django 기본 기능 우선 적용
- 서드파티 기능 신중 선택: 불필요한 외부 라이브러리 도입 지양
- Django 표준 구조 유지: 앱 단위 분리, settings 모듈화, urls 관리 등 일관성 유지
- 커스텀 구조 최소화: 불가피한 패턴 변경사항 예외 적용

**코드 품질 관리**
- 함수 중복 방지: 새로운 함수 작성 전 기존 함수 적절한 검토
- 재사용성: 각 앱별로 역할 분담, 의존성 최소화
- 모듈화: 각 앱별로 역할 분담, 의존성 최소화

**PWA 최적화 목표**
- 로딩 속도: 3초 이내
- Notion 동기화: 99% 정확도
- 오프라인 기능: 80% 이상 기능 사용 가능
- 모바일 앱 수준의 UX
- HTTPS 우선: SSL 없으면 PWA 기능 작동 안 함

**보안 & 인증**
- Django 권한 시스템 + Notion 접근 권한 이중 보안
- secrets.json: Notion API 키, Django Secret Key 등 민감 정보 관리
- HTTPS 강제 적용 (PWA 필수 요구사항)

### 1.3 기술 스택 제한사항

본 프로젝트는 PWA (Progressive Web App) 방식으로 개발되며, Django는 API 서버로 활용하고 Notion을 데이터베이스로 사용합니다:

#### ✅ 허용된 기술

- **Backend:** Django 5 (REST API 서버)
- **Database:** Notion API (클라우드 데이터베이스)
- **PWA Frontend:**
  - HTML5, CSS3, JavaScript ES6+
  - Service Worker (오프라인 캐싱)
  - Web App Manifest (앱 설치)
  - Bootstrap 5 (CSS 프레임워크)
  - Fetch API (비동기 통신)
- **API:** Django REST Framework (DRF)
- **인증:** Django 내장 인증 + Notion OAuth
- **캐싱:** localStorage, sessionStorage, IndexedDB
- **환경:** Docker Compose (django, nginx 컨테이너)
- **HTTPS:** Let's Encrypt 또는 개발용 자체 서명 인증서

#### ❌ 금지된 기술

- React, Vue, Angular 등 복잡한 SPA 프레임워크
- 전통적인 MariaDB, PostgreSQL 등 관계형 DB
- Redis, Celery, RabbitMQ 등 메시지 큐 (개발용 제외)
- WebSocket, Server-Sent Events (PWA 표준 기능 우선)
- GraphQL (REST API 우선)
- 복잡한 외부 인증 서비스 (Notion OAuth 외)
- 마이크로서비스 아키텍처
- **jQuery 사용 최소화** (Vanilla JS 또는 Fetch API 우선)
- **Chart.js 대신 CSS/SVG 기반 차트**

### 1.4 PWA 핵심 기능 및 오프라인 지원

**Service Worker 기능**
- 오프라인 캐싱: 핵심 리소스 및 API 응답 캐시
- 백그라운드 동기화: 네트워크 복구 시 자동 데이터 동기화
- 푸시 알림: 중요한 업데이트 실시간 알림

**파일 위치 및 구조**
- **Service Worker:** `/static/js/sw.js`
- **PWA Manifest:** `/static/manifest.json`
- **오프라인 페이지:** `/templates/offline.html`
- **JavaScript 모듈:** `/static/js/modules/`
  - `notion-api.js` (Notion API 연동)
  - `cache-manager.js` (캐시 관리)
  - `offline-sync.js` (오프라인 동기화)

**캐싱 전략**
- **Cache First:** 정적 리소스 (CSS, JS, 이미지)
- **Network First:** 동적 데이터 (Notion API 응답)
- **Stale While Revalidate:** 자주 업데이트되는 컨텐츠

**PWA 기능 API**
- `installApp()` - 앱 설치 유도
- `syncNotionData()` - Notion 데이터 동기화
- `enableOfflineMode()` - 오프라인 모드 활성화
- `showNotification()` - 푸시 알림 표시
- `cacheUserData()` - 사용자 데이터 로컬 캐싱

**PWA 주요 특징**
- 📱 네이티브 앱 수준의 사용자 경험
- 🌐 오프라인에서도 80% 이상 기능 사용 가능
- 🔄 실시간 Notion 데이터 동기화
- 🔒 HTTPS 기반 보안 통신
- ⚡ Service Worker 기반 빠른 로딩

### 1.5 접속 정보 및 Notion 연동

- **웹 포트:** 8081 (HTTPS 필수)
- **메인 페이지:** https://localhost:8081/ (PWA 설치 가능)
- **API 엔드포인트:** https://localhost:8081/api/
- **관리자 페이지:** https://localhost:8081/admin/
- **Notion Workspace:** [설정된 Notion 워크스페이스]
- **Notion Database ID:** [환경변수로 관리]

### 1.6 Notion 데이터베이스 연동

**Notion API 기본 설정**
- **API 버전:** 2022-06-28 (최신 버전 사용)
- **인증 방식:** Internal Integration Token
- **주요 기능:** CRUD 작업, 페이지 내용 동기화, 실시간 업데이트

**데이터베이스 구조**
```json
{
  "databases": {
    "main_db": "database_id_1",
    "users_db": "database_id_2",
    "tasks_db": "database_id_3"
  }
}
```

**API 사용 패턴**
- **읽기:** GET /v1/databases/{database_id}/query
- **생성:** POST /v1/pages
- **수정:** PATCH /v1/pages/{page_id}
- **삭제:** PATCH /v1/pages/{page_id} (archived: true)

### 1.7 도커 및 HTTPS 설정

**docker compose:** PWA 및 Notion API 연동을 위해 HTTPS 개발환경 필수  
**SSL 인증서:** 개발용 자체 서명 인증서 또는 mkcert 사용

## 2. 개발 환경 구성

### 2.1 Docker Compose 기반 개발환경 (가상환경 불필요)

```
├── Nginx (웹서버/리버스 프록시)
├── MySQL/MariaDB (데이터베이스)
├── Gunicorn (WSGI 서버)
├── Django (웹 프레임워크)
└── Python (런타임)
```

**중요:** Docker 컨테이너로 격리된 환경이므로 별도의 Python 가상환경(venv, conda 등)은 필요하지 않습니다.

### 2.2 프로젝트 구조

```
onesquare/                  # 프로젝트 루트
├── Makefile
├── cleanup_project.sh
├── docker/                 # Docker 관련 설정
├── docker-compose.yml
├── load-env.sh
├── optimize-wsl2.sh
├── requirements.txt
└── src/                    # 메인 개발 코드 위치
    ├── manage.py
    ├── secrets.json        # 민감한 설정 정보
    ├── apps/               # Django 앱들 (startapp 생성 위치)
    ├── config/             # Django 메인 설정
    │   ├── settings.py
    │   ├── urls.py
    │   └── wsgi.py
    ├── logs/               # 로그 파일
    ├── main/               # 메인 앱
    ├── media/              # 업로드된 미디어 파일
    ├── run/                # PID 파일 등
    ├── static/             # 정적 파일 (개발용)
    │   ├── css/
    │   │   └── common.css  # 추가 전역 스타일
    │   ├── js/
    │   │   ├── common.js   # 공통 함수
    │   │   └── modal.js    # 공통 모달창 및 토스트 메시지창 스타일
    │   └── images/
    ├── staticfiles/        # 수집된 정적 파일 (배포용)
    └── templates/          # HTML 템플릿
        └── base.html       # 기본 템플릿
```

## 3. 개발 프로세스

### 3.1 새로운 앱 생성 시 수행사항

**A. Django 앱 생성**
```bash
cd ~/onesquare/src
python manage.py startapp [앱이름]
# 또는 apps 디렉토리 안에 생성
python manage.py startapp [앱이름] apps/[앱이름]
```

**B. 필수 설정 업데이트**

**settings.py 수정**
- INSTALLED_APPS에 새 API 앱 추가
- Notion API 설정 확인 (secrets.json)
- CORS 설정 및 PWA 미들웨어 추가

**urls.py 설정**
- 메인 config/urls.py에 앱 URL 패턴 포함
- 앱별 urls.py 생성 및 뷰 연결

**Notion API 서비스 설정**
```bash
# Notion API 커넥션 테스트
python manage.py test apps.notion_api.tests
# API 엔드포인트 작동 확인
curl -X GET https://localhost:8081/api/notion/test/
```

### 3.2 Views 작성 시 수행사항

**A. API 뷰 클래스 작성**
- Django REST Framework ViewSet 또는 APIView
- Notion API 연동 로직 구현
- PWA 캐싱을 위한 HTTP 헤더 설정
- 비동기 요청 에러 핸들링

**B. URL 패턴 연결**
- 앱의 urls.py에 뷰 연결
- URL 네이밍 규칙 준수

**C. PWA 템플릿 연결**
- src/templates/pwa/ 디렉토리에 PWA 전용 템플릿 생성
- Service Worker 및 매니페스트 설정
- src/static/js/modules/에서 JavaScript 모듈 관리

### 3.3 의존성 관리

**A. requirements.txt 필수 라이브러리**

프로젝트에 포함되어야 할 최소한의 라이브러리들:

```txt
# Django 기본
Django>=5.0.0
gunicorn

# 데이터베이스 (MySQL/MariaDB)
mysqlclient
PyMySQL

# 엑셀 관련
openpyxl
xlsxwriter
pandas
xlrd

# 이미지 처리 관련
Pillow
django-imagekit
python-magic

# 기타 유용한 라이브러리
django-extensions
django-debug-toolbar
python-decouple
requests

# 개발/테스트용 (운영시 제외)
matplotlib
seaborn
plotly
```

**B. 라이브러리 추가 시**

새로운 패키지 설치 시 프로젝트 루트의 requirements.txt 업데이트

```bash
cd ~/onesquare
# Docker 컨테이너 내에서 직접 설치하거나
docker-compose exec web pip install [패키지명]
# requirements.txt에 추가 후 이미지 재빌드
docker-compose build web
```

**C. Docker 이미지 재빌드 (의존성 변경 시)**

```bash
cd ~/onesquare
# requirements.txt 수정 후 이미지 재빌드
docker-compose build web
docker-compose up -d
```

### 3.4 서비스 재시작 및 테스트

**A. Docker Compose 명령어 세트**

```bash
# 프로젝트 루트에서 실행
cd ~/onesquare

# 서비스 중지
docker-compose down

# 서비스 재시작
docker-compose up -d

# 특정 서비스만 재시작
docker-compose restart web

# 로그 확인
docker-compose logs -f web

# 전체 서비스 상태 확인
docker-compose ps
```

**B. 개발 중 빠른 재시작**

```bash
# 프로젝트 루트에서
cd ~/onesquare

# Django 개발서버만 재시작 (개발 중)
docker-compose restart web

# 전체 서비스 재시작 (설정 변경 시)
docker-compose down && docker-compose up -d

# Makefile 활용 (있는 경우)
make restart
```

**C. 웹페이지 테스트 준비**
- 브라우저에서 http://localhost:8081 또는 설정된 포트로 접속
- Django admin 페이지 확인: http://localhost:8081/admin
- API 엔드포인트 테스트

## 4. 핵심 작업 플로우

### 4.1 새 기능 개발 시
1. 앱 생성 → 2. 모델 정의 → 3. 마이그레이션 → 4. 뷰 작성 → 5. URL 연결 → 6. 템플릿 작성 → 7. 서비스 재시작 → 8. 테스트

### 4.2 기존 기능 수정 시 (PWA/Notion)
1. Notion API 스키마 변경 확인 → 2. PWA 캐시 업데이트 → 3. Service Worker 재등록 → 4. 서비스 재시작 → 5. 오프라인/온라인 테스트

## 5. 주요 디렉토리 역할

- **apps/:** 새로운 Django 앱 생성 위치
- **config/:** Django 메인 설정 파일들 (settings.py, urls.py 등)
- **main/:** 메인 앱 (프로젝트 기본 앱)
- **templates/:** 전역 HTML 템플릿
- **static/:** 개발 시 정적 파일 (CSS, JS, 이미지)
- **staticfiles/:** collectstatic으로 수집된 정적 파일 (배포용)
- **media/:** 사용자 업로드 파일
- **logs/:** 애플리케이션 로그 파일
- **run/:** PID 파일 등 런타임 파일
- **secrets.json:** 민감한 설정 정보 (DB 패스워드, Secret Key 등)

## 6. 주의사항

- **가상환경 불필요:** Docker 컨테이너로 격리되어 있으므로 venv, conda 등 가상환경 설정 불필요
- 모든 변경사항은 Docker 컨테이너 재시작을 통해 반영 확인
- 데이터베이스 스키마 변경 시 반드시 마이그레이션 수행
- 정적 파일 변경 시 collectstatic 명령 실행 고려
- 개발 중에는 DEBUG=True, 운영 시에는 DEBUG=False 설정
- 패키지 설치: Docker 컨테이너 내에서 직접 설치하거나 requirements.txt 수정 후 이미지 재빌드

## 7. 자동화 스크립트 예시

```bash
#!/bin/bash
# deploy.sh - 개발 배포 자동화
cd ~/onesquare
echo "Restarting Django services..."
docker-compose restart web
echo "Checking service status..."
docker-compose ps
echo "Service ready for testing!"

# cleanup_project.sh 스크립트 활용
./cleanup_project.sh

# optimize-wsl2.sh 스크립트 활용 (WSL2 환경)
./optimize-wsl2.sh
```

---

## 8. Notion API 연동 상세 가이드

### 8.1 Notion 인티그레이션 설정

**1단계: Notion 인티그레이션 생성**
```bash
# 1. https://www.notion.so/my-integrations 접속
# 2. "New integration" 클릭
# 3. 인티그레이션 이름 입력 (OneSquare App)
# 4. Internal Integration Token 복사
# 5. secrets.json에 저장
```

**2단계: 데이터베이스 공유 설정**
```bash
# 1. Notion 데이터베이스 페이지에서 "Share" 클릭
# 2. 생성한 Integration 추가
# 3. Database ID 복사 (URL에서 확인 가능)
```

### 8.2 Django Notion API 연돔 방식

**API 클래스 구조**
```python
# apps/notion_api/services.py
class NotionService:
    def __init__(self):
        self.client = notion_client.Client(auth=settings.NOTION_TOKEN)
        self.database_id = settings.NOTION_DATABASE_ID
    
    def query_database(self, filter_criteria=None):
        """Notion 데이터베이스 조회"""
        return self.client.databases.query(
            database_id=self.database_id,
            filter=filter_criteria
        )
    
    def create_page(self, properties):
        """Notion 페이지 생성"""
        return self.client.pages.create(
            parent={"database_id": self.database_id},
            properties=properties
        )
```

### 8.3 PWA 오프라인 동기화 전략

**오프라인 데이터 저장**
```javascript
// static/js/modules/offline-sync.js
class OfflineSync {
    constructor() {
        this.dbName = 'OneSquareOfflineDB';
        this.version = 1;
    }
    
    async saveOfflineData(data) {
        const db = await this.openDB();
        const transaction = db.transaction(['offline_data'], 'readwrite');
        const store = transaction.objectStore('offline_data');
        return store.put(data);
    }
    
    async syncToNotion() {
        // 네트워크 연결 시 Notion으로 데이터 전송
        const offlineData = await this.getOfflineData();
        for (const item of offlineData) {
            await fetch('/api/notion/sync/', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(item)
            });
        }
    }
}
```

### 8.4 실시간 데이터 동기화

**Webhook 설정** (추후 Notion에서 지원 시)
```python
# apps/notion_api/webhooks.py
@csrf_exempt
def notion_webhook(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # PWA에 실시간 데이터 업데이트 전송
        broadcast_to_pwa(data)
        return JsonResponse({'status': 'success'})
```

**주기적 동기화** (대안)
```javascript
// 매 5분마다 데이터 동기화
setInterval(async () => {
    if (navigator.onLine) {
        await syncManager.syncWithNotion();
    }
}, 300000); // 5분
```

### 8.5 보안 및 에러 처리

**API 키 보안**
```python
# secrets.json
{
    "NOTION_TOKEN": "secret_xxxxxxxxxxx",
    "NOTION_DATABASE_ID": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "DJANGO_SECRET_KEY": "django-secret-key"
}
```

**에러 처리 예시**
```python
def safe_notion_request(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIResponseError as e:
            logger.error(f"Notion API Error: {e}")
            return {"error": "Notion API 오류", "detail": str(e)}
        except Exception as e:
            logger.error(f"Unexpected Error: {e}")
            return {"error": "예기치 못한 오류"}
    return wrapper
```

---

## Task Master AI 통합 지침

### Essential Commands

```bash
# Project Setup
task-master init                                    # Initialize Task Master in current project
task-master parse-prd .taskmaster/docs/prd.txt      # Generate tasks from PRD document
task-master models --setup                        # Configure AI models interactively

# Daily Development Workflow
task-master list                                   # Show all tasks with status
task-master next                                   # Get next available task to work on
task-master show <id>                             # View detailed task information (e.g., task-master show 1.2)
task-master set-status --id=<id> --status=done    # Mark task complete

# Task Management
task-master add-task --prompt="description" --research        # Add new task with AI assistance
task-master expand --id=<id> --research --force              # Break task into subtasks
task-master update-task --id=<id> --prompt="changes"         # Update specific task
task-master update --from=<id> --prompt="changes"            # Update multiple tasks from ID onwards
task-master update-subtask --id=<id> --prompt="notes"        # Add implementation notes to subtask

# Analysis & Planning
task-master analyze-complexity --research          # Analyze task complexity
task-master complexity-report                      # View complexity analysis
task-master expand --all --research               # Expand all eligible tasks
```

### MCP Integration

Task Master provides an MCP server that Claude Code can connect to. Configure in `.mcp.json`:

```json
{
  "mcpServers": {
    "task-master-ai": {
      "command": "npx",
      "args": ["-y", "--package=task-master-ai", "task-master-ai"],
      "env": {
        "ANTHROPIC_API_KEY": "your_key_here",
        "PERPLEXITY_API_KEY": "your_key_here",
        "OPENAI_API_KEY": "OPENAI_API_KEY_HERE"
      }
    }
  }
}
```

### Standard Development Workflow

#### 1. Project Initialization
```bash
# Initialize Task Master
task-master init

# Create or obtain PRD, then parse it
task-master parse-prd .taskmaster/docs/prd.txt

# Analyze complexity and expand tasks
task-master analyze-complexity --research
task-master expand --all --research
```

#### 2. Daily Development Loop
```bash
# Start each session
task-master next                           # Find next available task
task-master show <id>                     # Review task details

# During implementation, check in code context into the tasks and subtasks
task-master update-subtask --id=<id> --prompt="implementation notes..."

# Complete tasks
task-master set-status --id=<id> --status=done
```

**이 문서는 상현님의 Django 개발 환경에 최적화된 작업 가이드입니다.**