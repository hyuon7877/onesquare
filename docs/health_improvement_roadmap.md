# 🏥 코드 건강도 개선 로드맵
## 목표: 30/100 → 75/100

📅 작성일: 2025-09-05

---

## 🎯 현재 상태 분석

### 주요 문제점
- **평균 복잡도:** 22.2 (목표: 15.0 이하)
- **고복잡도 모듈:** 5개 (100+ 복잡도)
- **중복 코드:** ~15%
- **테스트 커버리지:** 0% (추정)

### 병목 지점
1. **Permissions** - 복잡도 121.2, 408줄
2. **Validators** - 복잡도 118.4, 321줄
3. **Notion Sync** - 복잡도 117.6, 578줄
4. **Photo Views** - 복잡도 102.3, 513줄
5. **Middleware** - 복잡도 255.6, 878줄 (부분 완료)

---

## 📋 우선순위별 작업 계획

### 🔴 Phase 1: 긴급 (1주차) - 건강도 목표: 45/100

#### 1. 고복잡도 모듈 분할
```bash
# Permissions 모듈 분할 (121.2 → 30 이하)
src/apps/auth_system/permissions/
├── __init__.py
├── base.py          # 기본 권한 클래스
├── user.py          # 사용자 권한
├── group.py         # 그룹 권한
├── notion.py        # Notion 권한
└── decorators.py    # 권한 데코레이터

# Validators 모듈 분할 (118.4 → 30 이하)
src/apps/security/validators/
├── __init__.py
├── input.py         # 입력 검증
├── file.py          # 파일 검증
├── api.py           # API 검증
└── notion.py        # Notion 데이터 검증

# 예상 개선
- 복잡도: 22.2 → 18.5
- 코드 라인: 35,790 → 34,000
```

#### 2. 공통 유틸리티 적용
```python
# Before (42개 모듈에서 중복)
import datetime
now = datetime.datetime.now()

# After
from utils.datetime_helper import get_now
now = get_now()

# 예상 효과
- 중복 코드: 15% → 10%
- 코드 라인: 34,000 → 32,000
```

### 🟡 Phase 2: 중요 (2주차) - 건강도 목표: 60/100

#### 3. 중복 모델 통합
```python
# models/base.py - 공통 베이스 모델
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class NotionSyncModel(TimeStampedModel):
    notion_id = models.CharField(max_length=100, unique=True)
    last_synced = models.DateTimeField(null=True)
    
    class Meta:
        abstract = True
```

#### 4. 서비스 레이어 도입
```python
# services/notion_service.py
class NotionService:
    def sync_data(self, model_instance):
        """Notion 동기화 로직 통합"""
        pass
    
    def validate_data(self, data):
        """Notion 데이터 검증"""
        pass
```

### 🟢 Phase 3: 개선 (3-4주차) - 건강도 목표: 75/100

#### 5. 테스트 코드 작성
```python
# tests/test_utils.py
class TestDateTimeHelper(TestCase):
    def test_get_now(self):
        now = get_now()
        self.assertIsNotNone(now)
    
    def test_format_korean_date(self):
        date = datetime(2025, 9, 5)
        result = format_korean_date(date)
        self.assertEqual(result, "2025년 9월 5일")

# 목표: 80% 테스트 커버리지
```

#### 6. 성능 최적화
```python
# 캐싱 전략
from django.core.cache import cache

def get_user_permissions(user_id):
    cache_key = f'permissions:{user_id}'
    permissions = cache.get(cache_key)
    if not permissions:
        permissions = calculate_permissions(user_id)
        cache.set(cache_key, permissions, 300)
    return permissions
```

---

## 📊 예상 개선 지표

| 단계 | 기간 | 건강도 | 복잡도 | 코드 라인 | 중복률 |
|------|------|--------|--------|----------|--------|
| 현재 | - | 30/100 | 22.2 | 35,790 | 15% |
| Phase 1 | 1주 | 45/100 | 18.5 | 32,000 | 10% |
| Phase 2 | 2주 | 60/100 | 16.0 | 30,000 | 7% |
| Phase 3 | 4주 | 75/100 | 14.5 | 28,000 | 5% |

---

## 🛠️ 실행 명령어

### Phase 1 실행
```bash
# 1. Permissions 분할
mkdir -p src/apps/auth_system/permissions
python scripts/split_module.py --module permissions --parts 4

# 2. Validators 분할  
mkdir -p src/apps/security/validators
python scripts/split_module.py --module validators --parts 4

# 3. 유틸리티 적용
python scripts/apply_utils.py --module all --util datetime_helper

# 4. 분석 실행
make analyze-modules
```

### Phase 2 실행
```bash
# 1. 베이스 모델 생성
python manage.py create_base_models

# 2. 서비스 레이어 생성
python manage.py create_services

# 3. 중복 제거
python scripts/remove_duplicates.py
```

### Phase 3 실행
```bash
# 1. 테스트 생성
python manage.py create_tests --coverage 80

# 2. 테스트 실행
python manage.py test --parallel

# 3. 커버리지 확인
coverage run --source='.' manage.py test
coverage report
```

---

## ✅ 체크리스트

### Week 1
- [ ] Permissions 모듈 4개로 분할
- [ ] Validators 모듈 4개로 분할
- [ ] datetime_helper 전체 적용
- [ ] json_handler 전체 적용
- [ ] 첫 번째 건강도 측정 (목표: 45/100)

### Week 2
- [ ] 베이스 모델 클래스 생성
- [ ] 중복 models.py 통합
- [ ] 서비스 레이어 구현
- [ ] logger 유틸리티 적용
- [ ] 두 번째 건강도 측정 (목표: 60/100)

### Week 3-4
- [ ] 단위 테스트 작성 (최소 50개)
- [ ] 통합 테스트 작성 (최소 20개)
- [ ] 캐싱 전략 구현
- [ ] 쿼리 최적화
- [ ] 최종 건강도 측정 (목표: 75/100)

---

## 🎯 성공 지표

### 정량적 지표
- ✅ 건강도 75/100 이상
- ✅ 평균 복잡도 15.0 이하
- ✅ 코드 라인 30,000 이하
- ✅ 중복률 5% 이하
- ✅ 테스트 커버리지 80% 이상

### 정성적 지표
- ✅ 새 기능 추가 시간 50% 단축
- ✅ 버그 발생률 70% 감소
- ✅ 코드 리뷰 시간 30% 단축
- ✅ 신규 개발자 온보딩 시간 40% 단축

---

## 🚀 Quick Start

다음 주 작업을 바로 시작하려면:

```bash
# 자동화 스크립트 실행
./scripts/health_improvement.sh --phase 1

# 또는 Make 명령
make improve-health-phase1
```

---

*건강한 코드베이스는 지속 가능한 개발의 기초입니다.*
*목표: 2025년 10월까지 건강도 90/100 달성*