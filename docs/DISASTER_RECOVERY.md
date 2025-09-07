# OneSquare Disaster Recovery Plan

## 목차
1. [개요](#개요)
2. [백업 전략](#백업-전략)
3. [복구 절차](#복구-절차)
4. [롤백 절차](#롤백-절차)
5. [비상 연락처](#비상-연락처)
6. [체크리스트](#체크리스트)

---

## 개요

이 문서는 OneSquare 프로젝트의 재해 복구 계획을 설명합니다. 시스템 장애, 데이터 손실, 또는 배포 실패 시 신속한 복구를 위한 절차를 제공합니다.

### 복구 목표
- **RTO (Recovery Time Objective)**: 4시간 이내
- **RPO (Recovery Point Objective)**: 24시간 이내 데이터 손실

### 주요 구성 요소
- Django 웹 애플리케이션
- PostgreSQL 데이터베이스
- 미디어 파일 및 정적 파일
- Docker 컨테이너 환경

---

## 백업 전략

### 1. 자동 백업 스케줄

#### 데이터베이스 백업
- **주기**: 매일 02:00 AM (KST)
- **보관**: 30일간 보관, 최대 10개 백업 파일
- **위치**: `/backup/database/`
- **형식**: 압축된 SQL 덤프 (`.sql.gz`)

```bash
# Crontab 설정
0 2 * * * /opt/onesquare/scripts/backup-db.sh >> /var/log/backup.log 2>&1
```

#### 미디어 파일 백업
- **주기**: 매주 일요일 03:00 AM (KST)
- **보관**: 30일간 보관, 최대 10개 백업 파일
- **위치**: `/backup/media/`
- **형식**: tar.gz 아카이브

```bash
# Crontab 설정
0 3 * * 0 /opt/onesquare/scripts/backup-media.sh >> /var/log/backup.log 2>&1
```

### 2. 수동 백업

#### 즉시 백업 실행
```bash
# 데이터베이스 백업
sudo /opt/onesquare/scripts/backup-db.sh

# 미디어 파일 백업
sudo /opt/onesquare/scripts/backup-media.sh
```

### 3. 클라우드 백업

AWS S3 또는 Google Cloud Storage에 자동 업로드:
```bash
# 환경 변수 설정
export AWS_S3_BUCKET=onesquare-backups
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
```

---

## 복구 절차

### 시나리오 1: 데이터베이스 손상

#### 1단계: 현재 상태 평가
```bash
# 데이터베이스 상태 확인
psql -U onesquare_user -d onesquare_db -c "SELECT 1;"

# 에러 로그 확인
tail -n 100 /var/log/postgresql/postgresql-*.log
```

#### 2단계: 서비스 중지
```bash
# 애플리케이션 중지
docker-compose stop web

# 또는 systemctl 사용
sudo systemctl stop gunicorn
```

#### 3단계: 데이터베이스 복원
```bash
# 대화형 복원
sudo /opt/onesquare/scripts/restore-db.sh

# 특정 백업 파일 복원
sudo /opt/onesquare/scripts/restore-db.sh /backup/database/db_backup_20240101_020000.sql.gz

# 자동 복원 (최신 백업)
sudo /opt/onesquare/scripts/restore-db.sh --yes
```

#### 4단계: 서비스 재시작
```bash
# 애플리케이션 시작
docker-compose start web

# 상태 확인
docker-compose ps
```

#### 5단계: 검증
```bash
# 헬스체크
curl http://localhost:8081/health/

# 데이터 무결성 확인
python manage.py dbshell -c "SELECT COUNT(*) FROM django_migrations;"
```

### 시나리오 2: 미디어 파일 손실

#### 복원 절차
```bash
# 최신 백업 확인
ls -la /backup/media/

# 미디어 파일 복원
cd /opt/onesquare
tar -xzf /backup/media/media_backup_latest.tar.gz

# 권한 설정
chown -R www-data:www-data media/
chmod -R 755 media/
```

### 시나리오 3: 전체 시스템 장애

#### 1단계: 새 서버 준비
```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Docker Compose 설치
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2단계: 프로젝트 복원
```bash
# Git에서 코드 복원
git clone https://github.com/your-org/onesquare.git /opt/onesquare
cd /opt/onesquare

# 환경 설정 파일 복원
cp /backup/config/.env.production .env
cp /backup/config/secrets.json src/secrets.json
```

#### 3단계: 데이터 복원
```bash
# 데이터베이스 복원
./scripts/restore-db.sh /backup/database/latest_backup.sql.gz

# 미디어 파일 복원
tar -xzf /backup/media/latest_backup.tar.gz -C /
```

#### 4단계: 서비스 시작
```bash
# Docker 컨테이너 시작
docker-compose up -d

# 마이그레이션 실행
docker-compose exec web python manage.py migrate

# 정적 파일 수집
docker-compose exec web python manage.py collectstatic --noinput
```

---

## 롤백 절차

### 배포 실패 시 롤백

#### 자동 롤백
```bash
# 이전 버전으로 롤백
sudo /opt/onesquare/scripts/rollback.sh

# 특정 버전으로 롤백
sudo /opt/onesquare/scripts/rollback.sh v1.2.3

# 강제 롤백 (확인 없이)
sudo /opt/onesquare/scripts/rollback.sh previous --force
```

#### 수동 롤백 (Docker)
```bash
# 이전 이미지 확인
docker images | grep onesquare

# 이전 버전으로 전환
docker-compose down
sed -i 's/onesquare:latest/onesquare:v1.2.3/g' docker-compose.yml
docker-compose up -d
```

#### 수동 롤백 (Git)
```bash
# 이전 커밋 확인
git log --oneline -10

# 특정 커밋으로 롤백
git checkout -b rollback-branch abc1234
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn
```

---

## 비상 연락처

### 핵심 팀원
| 역할 | 이름 | 연락처 | 비고 |
|------|------|--------|------|
| 프로젝트 관리자 | 홍길동 | 010-1234-5678 | 1차 연락 |
| 시스템 관리자 | 김철수 | 010-2345-6789 | 인프라 담당 |
| 데이터베이스 관리자 | 이영희 | 010-3456-7890 | DB 복구 담당 |
| 개발 팀장 | 박민수 | 010-4567-8901 | 애플리케이션 담당 |

### 외부 지원
- **AWS Support**: 1-800-123-4567
- **Docker Support**: support@docker.com
- **PostgreSQL Consultant**: consultant@example.com

---

## 체크리스트

### 일일 점검 사항
- [ ] 백업 스크립트 실행 확인
- [ ] 디스크 공간 확인 (80% 미만 사용)
- [ ] 에러 로그 확인
- [ ] 모니터링 대시보드 확인

### 주간 점검 사항
- [ ] 백업 파일 무결성 검증
- [ ] 복구 테스트 (개발 환경)
- [ ] 보안 업데이트 확인
- [ ] 성능 메트릭 검토

### 월간 점검 사항
- [ ] 전체 복구 시뮬레이션
- [ ] 백업 정책 검토
- [ ] 비상 연락처 업데이트
- [ ] 문서 업데이트

### 재해 발생 시 체크리스트
1. [ ] 영향 범위 파악
2. [ ] 핵심 팀원 소집
3. [ ] 현재 상태 백업
4. [ ] 복구 계획 수립
5. [ ] 복구 작업 수행
6. [ ] 시스템 검증
7. [ ] 서비스 재개
8. [ ] 사후 분석 보고서 작성

---

## 복구 시간 예상

| 시나리오 | 예상 시간 | 우선순위 |
|----------|-----------|----------|
| 데이터베이스 복원 | 30분 - 1시간 | 높음 |
| 미디어 파일 복원 | 1-2시간 | 중간 |
| 전체 시스템 복구 | 2-4시간 | 높음 |
| 배포 롤백 | 15-30분 | 높음 |
| 코드 복원 | 30분 | 중간 |

---

## 테스트 절차

### 복구 테스트 (월 1회)
```bash
# 1. 테스트 환경 준비
docker-compose -f docker-compose.test.yml up -d

# 2. 백업 복원 테스트
./scripts/restore-db.sh --test-mode

# 3. 애플리케이션 동작 확인
pytest tests/disaster_recovery/

# 4. 결과 기록
echo "Test completed: $(date)" >> /var/log/dr-test.log
```

### 알림 테스트
```bash
# Slack 알림 테스트
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{"text":"DR Test: This is a test notification"}'
```

---

## 추가 리소스

- [Django 배포 가이드](https://docs.djangoproject.com/en/4.2/howto/deployment/)
- [PostgreSQL 백업 문서](https://www.postgresql.org/docs/current/backup.html)
- [Docker 복구 가이드](https://docs.docker.com/engine/swarm/admin_guide/)
- [AWS 재해 복구 백서](https://aws.amazon.com/disaster-recovery/)

---

**마지막 업데이트**: 2024년 1월
**다음 검토 예정일**: 2024년 2월

> 📌 **중요**: 이 문서는 정기적으로 업데이트되어야 합니다. 시스템 변경사항이 있을 때마다 이 문서를 검토하고 필요시 수정하세요.