# OneSquare 시스템 아키텍처

> 시스템 전체 아키텍처와 모듈 간 의존성을 시각화한 문서

---

## 📊 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph "Client Layer"
        PWA[PWA Frontend]
        Mobile[Mobile Web]
        Desktop[Desktop Web]
    end
    
    subgraph "Application Layer"
        Django[Django Server<br/>Port: 8500]
        ServiceWorker[Service Worker]
        Static[Static Files]
    end
    
    subgraph "Data Layer"
        SQLite[(SQLite DB)]
        NotionAPI[Notion API]
        Cache[IndexedDB Cache]
    end
    
    PWA --> ServiceWorker
    Mobile --> Django
    Desktop --> Django
    ServiceWorker --> Cache
    Django --> SQLite
    Django --> NotionAPI
    ServiceWorker --> Django
    Django --> Static
```

## 🔧 모듈 의존성 다이어그램

```mermaid
graph LR
    subgraph Core["🔵 Core Modules"]
        config_settings_py[config/settings.py]
        config_urls_py[config/urls.py]
        config_wsgi_py[config/wsgi.py]
        secrets_json[secrets.json]
    end

    subgraph Auth["🟢 Authentication"]
        AuthSystem[auth_system]
        Decorators[decorators.py]
        CustomUser[CustomUser Model]
    end

    subgraph Features["🟡 Feature Modules"]
        auth_system[auth_system]
        calendar_system[calendar_system]
        dashboard[dashboard]
        field_reports[field_reports]
        leave_management[leave_management]
        time_tracking[time_tracking]
        revenue[revenue]
        feedback[feedback]
        ai_analytics[ai_analytics]
        monitoring[monitoring]
    end

    subgraph Integration["🟣 Integration"]
        notion_api[notion_api]
        pwa[pwa]
        static_js_sw_js[static/js/sw.js]
        static_manifest_json[static/manifest.json]
    end

    %% Dependencies
    config_urls_py --> settings_py
    config_wsgi_py --> settings_py
    auth_system_decorators_py --> auth_system_models
    dashboard_services_py --> dashboard_models
    dashboard_layout_manager_py --> dashboard_models
    notion_api_services_py --> notion-client
    auth_system --> Django_contrib_auth
    calendar_system --> FullCalendar
    dashboard --> auth_system
    dashboard --> revenue
    field_reports --> auth_system
    leave_management --> auth_system
    leave_management --> calendar
    time_tracking --> auth_system
    revenue --> auth_system
    revenue --> notion_api
    feedback --> auth_system
    ai_analytics --> dashboard
    ai_analytics --> revenue
    notion_api --> notion-client
```

## 🎯 기능별 모듈 관계도

```mermaid
flowchart TD
    subgraph UserFlow["👤 사용자 플로우"]
        Login[로그인]
        Auth{인증}
        Permission{권한확인}
        Access[접근허가]
    end
    
    subgraph AdminFlow["👨‍💼 관리자 기능"]
        AdminDash[관리자 대시보드]
        Reports[리포트 관리]
        UserMgmt[사용자 관리]
        Analytics[데이터 분석]
    end
    
    subgraph PartnerFlow["🤝 파트너 기능"]
        FieldApp[현장 리포트 앱]
        CheckList[체크리스트]
        PhotoUpload[사진 업로드]
        TimeRecord[시간 기록]
    end
    
    Login --> Auth
    Auth -->|성공| Permission
    Auth -->|실패| Login
    Permission -->|관리자| AdminFlow
    Permission -->|파트너| PartnerFlow
    Permission -->|일반| Access
    
    AdminDash --> Reports
    AdminDash --> UserMgmt
    AdminDash --> Analytics
    
    FieldApp --> CheckList
    FieldApp --> PhotoUpload
    FieldApp --> TimeRecord
```

## 🔄 데이터 플로우

```mermaid
sequenceDiagram
    participant User
    participant PWA
    participant Django
    participant SQLite
    participant Notion
    participant Cache
    
    User->>PWA: 요청
    PWA->>Cache: 캐시 확인
    alt 캐시 있음
        Cache-->>PWA: 캐시 데이터
        PWA-->>User: 빠른 응답
        PWA->>Django: 백그라운드 업데이트
    else 캐시 없음
        PWA->>Django: API 요청
        Django->>SQLite: 로컬 데이터 조회
        Django->>Notion: Notion 동기화
        Notion-->>Django: 데이터 응답
        Django-->>PWA: 처리된 데이터
        PWA->>Cache: 캐시 저장
        PWA-->>User: 응답
    end
```

## 📦 모듈 카테고리 분포

```mermaid
pie title 모듈 카테고리별 분포
    "Core Modules" : 4
    "Feature Modules" : 10
    "Utils Modules" : 4
    "Integration Modules" : 4
```

## 🏗️ 시스템 레이어 구조

```mermaid
graph TD
    subgraph Presentation["🎨 Presentation Layer"]
        Templates[HTML Templates]
        StaticFiles[CSS/JS/Images]
        PWAAssets[PWA Assets]
    end
    
    subgraph Business["💼 Business Layer"]
        Views[Django Views]
        Serializers[Serializers]
        Services[Service Classes]
        Utils[Utility Functions]
    end
    
    subgraph Data["💾 Data Layer"]
        Models[Django Models]
        Migrations[Migrations]
        DBRouter[DB Router]
    end
    
    subgraph External["🌐 External Services"]
        NotionDB[Notion Database]
        EmailService[Email Service]
        SMSService[SMS Service]
    end
    
    Templates --> Views
    StaticFiles --> Templates
    PWAAssets --> StaticFiles
    
    Views --> Services
    Views --> Serializers
    Services --> Utils
    
    Services --> Models
    Models --> Migrations
    Models --> DBRouter
    
    Services --> NotionDB
    Services --> EmailService
    Services --> SMSService
```

## 📈 모듈 성숙도 매트릭스

```mermaid
quadrantChart
    title 모듈 성숙도 및 복잡도 매트릭스
    x-axis 낮은 복잡도 --> 높은 복잡도
    y-axis 개발 초기 --> 운영 안정
    quadrant-1 핵심 기능
    quadrant-2 성숙 모듈
    quadrant-3 개선 필요
    quadrant-4 단순 기능
    
    "Dashboard": [0.8, 0.9]
    "Auth System": [0.6, 0.95]
    "Calendar": [0.7, 0.85]
    "Field Reports": [0.75, 0.9]
    "Revenue": [0.85, 0.88]
    "PWA Core": [0.5, 0.92]
    "Notion API": [0.9, 0.85]
    "AI Analytics": [0.95, 0.7]
    "Feedback": [0.4, 0.8]
    "Monitoring": [0.6, 0.75]
```

## 🔗 주요 API 엔드포인트 구조

```mermaid
graph LR
    subgraph API["/api/"]
        Auth_EP["/auth/"]
        Dashboard_EP["/dashboard/"]
        Calendar_EP["/calendar/"]
        Field_EP["/field-report/"]
        Revenue_EP["/revenue/"]
        Notion_EP["/notion/"]
    end
    
    subgraph Auth_Routes["인증 API"]
        Login_API[login/]
        Logout_API[logout/]
        OTP_API[otp/]
        Session_API[session/]
    end
    
    subgraph Dashboard_Routes["대시보드 API"]
        Widget_API[widgets/]
        Data_API[data/]
        Notification_API[notifications/]
    end
    
    Auth_EP --> Auth_Routes
    Dashboard_EP --> Dashboard_Routes
```

---

## 📝 다이어그램 업데이트 가이드

1. **새 모듈 추가 시**
   - 해당 카테고리의 subgraph에 모듈 추가
   - 의존성 화살표 연결
   - 색상 코드 준수 (Core: 🔵, Auth: 🟢, Features: 🟡, Integration: 🟣)

2. **의존성 변경 시**
   - 화살표 방향 확인 (의존하는 쪽 → 의존받는 쪽)
   - 순환 의존성 방지

3. **자동 업데이트 스크립트**
   - `update-architecture.py` 실행
   - MODULE_TRACKER.md 기반 자동 생성

---

*마지막 업데이트: 2025-09-08 00:30:33*
*자동 생성 스크립트: `/scripts/update-architecture.py`*