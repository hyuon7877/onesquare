# 모듈 추가 템플릿

## 🆕 새 모듈 정보

### 기본 정보
- **모듈명**: [모듈 이름]
- **파일 경로**: `/src/apps/[앱이름]/[파일명]`
- **카테고리**: [ ] Core [ ] Utils [ ] Features [ ] Integration
- **추가 날짜**: [YYYY-MM-DD]

### 상태 및 의존성
- **상태**: [ ] 대기 [ ] 개발중 [ ] 완료
- **의존성**: [의존 모듈 목록, 없으면 '-']
- **추가 이유**: [왜 이 모듈이 필요한지]

### 모듈 상세
```python
# 주요 클래스/함수 시그니처
class ModuleName:
    def main_method(self):
        pass
```

### 연관 파일
- [ ] models.py 수정
- [ ] views.py 수정
- [ ] urls.py 수정
- [ ] 템플릿 추가
- [ ] 정적 파일 추가
- [ ] 마이그레이션 필요

### 테스트
- [ ] 유닛 테스트 작성
- [ ] 통합 테스트 작성
- [ ] 수동 테스트 완료

### 문서화
- [ ] 코드 주석 추가
- [ ] README 업데이트
- [ ] API 문서 작성

### 체크리스트
- [ ] MODULE_TRACKER.md에 추가
- [ ] 의존성 확인
- [ ] 코드 리뷰
- [ ] 다이어그램 업데이트 (`make update-arch`)

---

## 📝 Quick Template (복사용)

```markdown
| **모듈명** | `/src/apps/경로` | ⏸️ 대기 | 의존성 | 추가이유 | YYYY-MM-DD |
```

---

## 🔧 카테고리 가이드

### Core Modules
- Django 설정 파일 (settings, urls, wsgi)
- 프로젝트 핵심 구성 파일

### Utils Modules  
- 데코레이터, 헬퍼 함수
- 서비스 클래스, 유틸리티

### Feature Modules
- 비즈니스 로직 앱 (auth, dashboard, calendar 등)
- 사용자 기능 구현

### Integration Modules
- 외부 API 연동 (Notion, PWA)
- 서드파티 통합

---

## 사용 예시

### 1. 새 인증 데코레이터 추가
```markdown
| **auth_decorators.py** | `/src/apps/auth_system/decorators.py` | ✅ 완료 | auth_system.models | 권한 검증 강화 | 2025-09-05 |
```

### 2. 새 대시보드 위젯 추가
```markdown
| **widget_manager.py** | `/src/apps/dashboard/widget_manager.py` | 🔄 개발중 | dashboard.models | 위젯 동적 관리 | 2025-09-05 |
```

### 3. Notion 동기화 모듈 추가
```markdown
| **notion_sync.py** | `/src/apps/notion_api/sync.py` | ⏸️ 대기 | notion-client | 실시간 동기화 | 2025-09-05 |
```