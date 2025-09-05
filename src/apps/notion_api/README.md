# OneSquare Notion API 연동 시스템

OneSquare 프로젝트의 Notion API 연동 모듈입니다. Notion 데이터베이스와의 실시간 동기화, 스케줄링, 오류 복구 등의 기능을 제공합니다.

## 주요 기능

### 📋 데이터베이스 관리
- Notion 데이터베이스 등록 및 스키마 자동 감지
- 다양한 데이터베이스 타입 지원 (작업 관리, 캘린더, 리포트, 사용자 관리, 매출 관리)
- 동적 스키마 업데이트 및 호환성 유지

### 🔄 실시간 동기화
- 양방향 데이터 동기화 (Notion ↔ Django)
- 증분 동기화 및 전체 동기화 지원
- 충돌 감지 및 해결 메커니즘
- 캐시 기반 성능 최적화

### ⏰ 자동 스케줄링
- cron 기반 주기적 동기화
- 데이터베이스별 개별 동기화 간격 설정
- 강제 동기화 및 우선순위 처리
- 변경사항 자동 감지

### 🛡️ 오류 처리 & 복구
- 지수 백오프 재시도 메커니즘
- 서킷 브레이커 패턴으로 장애 격리
- 상세한 오류 로깅 및 모니터링
- Rate Limit 자동 처리

### 📊 모니터링 & 알림
- 실시간 동기화 상태 모니터링
- 성능 메트릭 수집 및 분석
- 이메일 알림 시스템
- 웹 대시보드 통합

## 시스템 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Notion API    │◄──►│  Django Models   │◄──►│   PWA Client    │
│   (External)    │    │                  │    │   (Frontend)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                        ▲                       ▲
         │                        │                       │
         ▼                        ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ NotionClient    │    │  Sync Service    │    │  API Views      │
│ - API Wrapper   │    │  - Orchestration │    │  - REST API     │
│ - Rate Limiting │    │  - Conflict Res. │    │  - Authentication│
│ - Retry Logic   │    │  - Caching       │    │  - Serialization │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  │
                      ┌──────────────────┐
                      │   Scheduler      │
                      │   - Cron Jobs    │
                      │   - Monitoring   │
                      │   - Health Check │
                      └──────────────────┘
```

## 설치 및 설정

### 1. 의존성 설치

```bash
# requirements.txt에 이미 포함됨
pip install notion-client
```

### 2. Django 설정 업데이트

`settings.py`에 다음 설정을 추가:

```python
# Notion API Settings
NOTION_TOKEN = 'your_notion_integration_token'
NOTION_DATABASE_ID = 'your_default_database_id'

# 동기화 설정
NOTION_SYNC_INTERVAL_DEFAULT = 300  # 5분
NOTION_CACHE_TIMEOUT = 300
NOTION_MAX_RETRIES = 3
NOTION_RETRY_DELAY = 1.0

# 모니터링 설정
NOTION_ALERT_THRESHOLD_MINUTES = 30
NOTION_MAX_FAILED_SYNCS = 3
NOTION_ADMIN_EMAILS = ['admin@example.com']
```

### 3. 데이터베이스 마이그레이션

```bash
python manage.py makemigrations notion_api
python manage.py migrate
```

### 4. Cron 작업 설정

```bash
# crontab -e
# 5분마다 동기화
*/5 * * * * /path/to/onesquare/scripts/notion_sync_cron.sh

# 30분마다 건강성 검사
*/30 * * * * /path/to/onesquare/scripts/notion_health_check.sh
```

## 사용법

### 데이터베이스 등록

```python
from apps.notion_api.models import NotionDatabase

database = NotionDatabase.objects.create(
    notion_id='your-database-id',
    title='My Database',
    database_type='tasks',
    sync_interval=300,  # 5분
    created_by=user
)
```

### 수동 동기화

```bash
# 특정 데이터베이스 동기화
python manage.py sync_notion sync 1

# 모든 예정된 동기화 실행
python manage.py sync_notion run

# 동기화 상태 확인
python manage.py sync_notion status
```

### API 사용 예제

```python
from apps.notion_api.services import NotionClient, NotionSyncService

# Notion 클라이언트 사용
client = NotionClient()
database_data = client.get_database('database-id')
pages = client.query_database('database-id')

# 동기화 서비스 사용
sync_service = NotionSyncService()
result = sync_service.sync_database(database, 'manual', user)
```

### REST API 엔드포인트

```http
GET    /api/notion/databases/           # 데이터베이스 목록
GET    /api/notion/databases/{id}/      # 데이터베이스 상세
POST   /api/notion/databases/{id}/sync/ # 수동 동기화
GET    /api/notion/pages/{id}/          # 페이지 상세
GET    /api/notion/sync-history/        # 동기화 기록
POST   /api/notion/search/              # 워크스페이스 검색
```

## 모델 구조

### NotionDatabase
- Notion 데이터베이스 메타데이터
- 동기화 설정 및 스케줄
- 스키마 정보 저장

### NotionPage
- Notion 페이지 데이터
- 속성 및 콘텐츠 블록
- 충돌 감지 정보

### SyncHistory
- 동기화 작업 이력
- 성능 메트릭
- 오류 정보

### NotionWebhook
- 웹훅 설정 (향후 지원)
- 실시간 변경 알림

## 모니터링 및 문제 해결

### 로그 확인

```bash
# 동기화 로그
tail -f /path/to/logs/notion_sync_cron.log

# Django 애플리케이션 로그
tail -f /path/to/logs/django.log
```

### 상태 모니터링

```bash
# 건강성 검사
python manage.py sync_notion status --json

# 성능 메트릭
python -c "
from apps.notion_api.monitoring import get_sync_metrics
import json
print(json.dumps(get_sync_metrics(7), indent=2))
"
```

### 일반적인 문제 해결

#### 1. API 인증 오류
```bash
# Notion 토큰 확인
echo $NOTION_TOKEN

# 데이터베이스 권한 확인
python manage.py sync_notion list
```

#### 2. 동기화 실패
```bash
# 강제 동기화
python manage.py sync_notion sync 1 --force

# 오류 세부사항 확인
python manage.py sync_notion status
```

#### 3. 서킷 브레이커 열림
```bash
# 캐시 초기화
python manage.py shell -c "
from django.core.cache import cache
cache.clear()
print('Cache cleared')
"
```

## 개발 및 테스트

### 테스트 실행

```bash
# 전체 테스트 스위트
./scripts/test_notion_api.sh

# Django 단위 테스트만
python manage.py test apps.notion_api

# 특정 테스트 클래스
python manage.py test apps.notion_api.tests.NotionClientTestCase
```

### 개발 환경 설정

```bash
# Mock 서버 사용 (개발 시)
export NOTION_DEBUG_MODE=true
export NOTION_LOG_LEVEL=DEBUG

# 테스트 데이터베이스 생성
python manage.py shell -c "
from apps.notion_api.models import NotionDatabase
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.first()
NotionDatabase.objects.create(
    notion_id='test-db-123',
    title='Test Database',
    created_by=user
)
"
```

## 성능 최적화

### 캐시 전략
- 데이터베이스 스키마: 5분 캐시
- 페이지 데이터: 1분 캐시
- API 응답: 30초 캐시

### 배치 처리
- 페이지 조회: 100개씩 배치
- 병렬 처리: 최대 5개 동시 요청
- Rate Limit: 요청당 100ms 지연

### 메모리 최적화
- 대용량 데이터베이스: 스트리밍 처리
- 가비지 컬렉션: 배치 작업 후 명시적 호출
- 연결 풀: 최대 10개 연결 유지

## 보안 고려사항

### API 키 관리
- 환경변수 또는 secrets.json 사용
- 정기적인 키 로테이션
- 최소 권한 원칙

### 데이터 보호
- 전송 중 암호화 (HTTPS 강제)
- 민감 정보 마스킹
- 감사 로그 유지

### 접근 제어
- 사용자 권한 기반 필터링
- API 요청 제한 (Rate Limiting)
- 세션 기반 인증

## 확장성 고려사항

### 수평 확장
- 데이터베이스별 분산 처리
- 메시지 큐 기반 비동기 처리
- 마이크로서비스 아키텍처 준비

### 성능 모니터링
- APM 도구 통합 (예: New Relic, DataDog)
- 커스텀 메트릭 수집
- 실시간 대시보드

## 문의 및 지원

- **버그 리포트**: GitHub Issues
- **기능 요청**: GitHub Discussions
- **긴급 지원**: admin@onesquare.com

## 라이선스

MIT License - 자세한 내용은 LICENSE 파일을 참조하세요.