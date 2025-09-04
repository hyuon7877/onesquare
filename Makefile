# Docker Compose 명령 설정
COMPOSE_BASE := docker compose
COMPOSE_CMD := $(COMPOSE_BASE) --env-file .env

# 색상 정의
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
CYAN := \033[0;36m
NC := \033[0m

.PHONY: help build up down restart logs shell migrate test clean

help: ## 도움말 표시
	@echo "$(GREEN)Django Docker 개발환경 명령어$(NC)"
	@echo "======================================"
	@echo "시스템: $(CYAN)$(SYSTEM_TYPE)$(NC)"
	@echo "Docker Compose: $(CYAN)$(COMPOSE_BASE)$(NC)"
	@echo "Python: $(CYAN)$(PYTHON_VERSION)$(NC)"
	@echo "Django: $(CYAN)$(DJANGO_VERSION)$(NC)"
	@echo "======================================"	
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

build: ## Docker 이미지 빌드
	@echo "$(GREEN)Docker 이미지 빌드 중...$(NC)"
	$(COMPOSE_CMD) build --no-cache

build-fast: ## Docker 이미지 빠른 빌드 (캐시 사용)
	@echo "$(GREEN)Docker 이미지 빠른 빌드 중...$(NC)"
	$(COMPOSE_CMD) build

up: ## 컨테이너 실행
	@echo "$(GREEN)컨테이너 시작 중...$(NC)"
	$(COMPOSE_CMD) up -d
	@sleep 3
	@echo "$(GREEN)서비스가 시작되었습니다!$(NC)"
	@echo "웹: http://localhost:$(WEB_PORT)"
	@echo "Admin: http://localhost:$(WEB_PORT)/admin"
	@echo "API: http://localhost:$(WEB_PORT)/api/"

down: ## 컨테이너 중지
	@echo "$(YELLOW)컨테이너 중지 중...$(NC)"
	$(COMPOSE_CMD) down

restart: ## 컨테이너 재시작
	@echo "$(YELLOW)컨테이너 재시작 중...$(NC)"
	$(COMPOSE_CMD) restart

logs: ## 전체 로그 확인
	$(COMPOSE_CMD) logs -f

logs-web: ## Django 로그만 확인
	$(COMPOSE_CMD) logs -f web

logs-db: ## 데이터베이스 로그만 확인
	$(COMPOSE_CMD) logs -f db

logs-nginx: ## Nginx 로그만 확인
	$(COMPOSE_CMD) logs -f nginx

shell: ## Django Shell 접속
	@echo "$(GREEN)Django Shell 접속 중...$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && python manage.py shell_plus --ipython || python manage.py shell"
	
bash: ## 웹 컨테이너 bash 접속
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && bash"
	
dbshell: ## MySQL Shell 접속
	$(COMPOSE_CMD) exec db mysql -u$(MYSQL_USER) -p$(MYSQL_PASSWORD) $(MYSQL_DATABASE)

migrate: ## 마이그레이션 실행
	@echo "$(GREEN)마이그레이션 실행 중...$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && python manage.py makemigrations && python manage.py migrate"

makemigrations: ## 마이그레이션 파일 생성
	@echo "$(GREEN)마이그레이션 파일 생성 중...$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && python manage.py makemigrations"

createsuperuser: ## 슈퍼유저 생성
	@echo "$(GREEN)슈퍼유저 생성 중...$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && python manage.py createsuperuser"

collectstatic: ## Static 파일 수집
	@echo "$(GREEN)Static 파일 수집 중...$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && python manage.py collectstatic --noinput"

test: ## 테스트 실행
	@echo "$(GREEN)테스트 실행 중...$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && python manage.py test"

test-coverage: ## 테스트 커버리지 확인
	@echo "$(GREEN)테스트 커버리지 확인 중...$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && coverage run --source='.' manage.py test && coverage report"

startapp: ## Django 앱 생성 (사용법: make startapp name=myapp)
	@if [ -z "$(name)" ]; then \
		echo "$(RED)오류: 앱 이름을 지정하세요. 사용법: make startapp name=myapp$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Django 앱 생성 중: $(name)$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && python manage.py startapp $(name)"
	@echo "$(YELLOW)settings.py의 INSTALLED_APPS에 '$(name)'을 추가하는 것을 잊지 마세요!$(NC)"

pip-install: ## pip 패키지 설치 (사용법: make pip-install package=django-debug-toolbar)
	@if [ -z "$(package)" ]; then \
		echo "$(RED)오류: 패키지명을 지정하세요. 사용법: make pip-install package=package_name$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)$(package) 설치 중...$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && pip install $(package)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && pip freeze > /tmp/requirements.txt"
	docker cp $(PROJECT_NAME)_web:/tmp/requirements.txt ./requirements.txt
	@echo "$(YELLOW)requirements.txt가 업데이트되었습니다$(NC)"

pip-upgrade: ## 모든 패키지 업그레이드
	@echo "$(GREEN)패키지 업그레이드 중...$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && pip list --outdated"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && pip install --upgrade pip setuptools wheel"

status: ## 컨테이너 상태 확인
	@echo "$(GREEN)컨테이너 상태:$(NC)"
	@$(COMPOSE_CMD) ps

ps: ## 실행중인 프로세스 확인
	@$(COMPOSE_CMD) exec web ps aux

check-korean: ## 한글 설정 확인
	@echo "$(GREEN)한글 설정 확인 중...$(NC)"
	@$(COMPOSE_CMD) exec web bash -c "locale | grep ko_KR"
	@$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && python -c \"print('한글 테스트: 가나다라마바사')\""
	@$(COMPOSE_CMD) exec db mysql -u$(MYSQL_USER) -p$(MYSQL_PASSWORD) -e "SHOW VARIABLES LIKE 'character%';" $(MYSQL_DATABASE)

check-performance: ## 성능 설정 확인
	@echo "$(GREEN)성능 설정 확인 중...$(NC)"
	@echo "Gunicorn Workers: $(GUNICORN_WORKERS)"
	@echo "Nginx Timeout: $(NGINX_TIMEOUT)s"
	@echo "Max Upload Size: $(MAX_UPLOAD_SIZE)"
	@$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && python -c \"import multiprocessing; print(f'CPU Cores: {multiprocessing.cpu_count()}')\""

clean: ## 모든 컨테이너, 볼륨, 네트워크 제거 (주의!)
	@echo "$(RED)경고: 모든 컨테이너, 볼륨, 네트워크가 제거됩니다!$(NC)"
	@read -p "정말 계속하시겠습니까? [y/N] " confirm && [ "$confirm" = "y" ] || exit 1
	$(COMPOSE_CMD) down -v
	@echo "$(GREEN)정리 완료$(NC)"

clean-logs: ## 로그 파일 정리
	@echo "$(YELLOW)로그 파일 정리 중...$(NC)"
	@find src/logs -name "*.log" -type f -delete 2>/dev/null || true
	@echo "$(GREEN)로그 정리 완료$(NC)"

backup-db: ## 데이터베이스 백업
	@echo "$(GREEN)데이터베이스 백업 중...$(NC)"
	@mkdir -p backups
	$(COMPOSE_CMD) exec db mysqldump -u$(MYSQL_USER) -p$(MYSQL_PASSWORD) $(MYSQL_DATABASE) | gzip > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql.gz
	@echo "$(GREEN)백업 완료: backups/backup_$(shell date +%Y%m%d_%H%M%S).sql.gz$(NC)"

restore-db: ## 데이터베이스 복원 (사용법: make restore-db file=backup.sql.gz)
	@if [ -z "$(file)" ]; then \
		echo "$(RED)오류: 백업 파일을 지정하세요. 사용법: make restore-db file=backup.sql.gz$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)데이터베이스 복원 중...$(NC)"
	@gunzip -c $(file) | $(COMPOSE_CMD) exec -T db mysql -u$(MYSQL_USER) -p$(MYSQL_PASSWORD) $(MYSQL_DATABASE)
	@echo "$(GREEN)복원 완료$(NC)"

init: build up migrate collectstatic ## 초기 설정 (build + up + migrate + collectstatic)
	@echo "$(GREEN)초기 설정 완료!$(NC)"
	@echo "다음 단계: make createsuperuser"

dev: ## 개발 모드 실행 (로그 표시)
	@echo "$(GREEN)개발 모드로 실행 중...$(NC)"
	$(COMPOSE_CMD) up

prod: ## 프로덕션 모드 실행
	@echo "$(GREEN)프로덕션 모드로 실행 중...$(NC)"
	@sed -i 's/DEBUG=True/DEBUG=False/g' .env
	$(COMPOSE_CMD) up -d
	@echo "$(YELLOW)프로덕션 모드로 실행됨 (DEBUG=False)$(NC)"

dev-mode: ## 개발 모드로 전환
	@echo "$(GREEN)개발 모드로 전환 중...$(NC)"
	@sed -i 's/DEBUG=False/DEBUG=True/g' .env
	$(COMPOSE_CMD) restart web
	@echo "$(GREEN)개발 모드 활성화됨 (DEBUG=True)$(NC)"

check-security: ## 보안 체크
	@echo "$(GREEN)보안 체크 실행 중...$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && python manage.py check --deploy"

show-urls: ## URL 패턴 확인
	@echo "$(GREEN)URL 패턴:$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && python manage.py show_urls || echo 'django-extensions가 필요합니다'"

check-system: ## 시스템 호환성 체크
	@echo "$(GREEN)시스템 호환성 체크:$(NC)"
	@echo "OS Type: $(SYSTEM_TYPE)"
	@echo "Python Version: $(PYTHON_VERSION)"
	@echo "Django Version: $(DJANGO_VERSION)"
	@if [ "$(SYSTEM_TYPE)" = "CentOS7" ]; then \
		echo "$(YELLOW)CentOS 7 감지: SELinux 대응 및 Docker 최적화 적용$(NC)"; \
		echo "$(GREEN)Docker 컨테이너는 최신 Python/Django 사용 가능!$(NC)"; \
	elif [ "$(SYSTEM_TYPE)" = "WSL2" ]; then \
		echo "$(CYAN)WSL2 감지: 성능 최적화 적용됨$(NC)"; \
		echo "$(CYAN)Vim 한글 설정 완료$(NC)"; \
	else \
		echo "$(GREEN)표준 Ubuntu/Linux 환경$(NC)"; \
	fi

check-docker-version: ## Docker 버전 확인
	@echo "$(GREEN)Docker 환경 정보:$(NC)"
	@docker version --format 'Docker Engine: {{.Server.Version}}'
	@$(COMPOSE_BASE) version --short 2>/dev/null || echo "Docker Compose: Plugin mode"
	@echo ""
	@echo "$(GREEN)컨테이너 내부 환경:$(NC)"
	$(COMPOSE_CMD) exec web bash -c "cat /etc/os-release | grep PRETTY_NAME"
	$(COMPOSE_CMD) exec web bash -c "python --version"
	$(COMPOSE_CMD) exec web bash -c "cd /var/www/html/$(PROJECT_NAME) && django-admin --version"

env-check: ## 환경변수 확인
	@echo "$(GREEN)환경변수 확인:$(NC)"
	@echo "PROJECT_NAME: $(PROJECT_NAME)"
	@echo "WEB_PORT: $(WEB_PORT)"
	@echo "DB_PORT: $(DB_PORT)"
	@echo "COMPOSE_CMD: $(COMPOSE_CMD)"
	@echo "SYSTEM_TYPE: $(SYSTEM_TYPE)"

fix-permissions: ## 권한 문제 해결
	@echo "$(GREEN)파일 권한 수정 중...$(NC)"
	$(COMPOSE_CMD) exec web bash -c "chown -R django:django /var/www/html/$(PROJECT_NAME)"
	$(COMPOSE_CMD) exec web bash -c "chmod -R 755 /var/www/html/$(PROJECT_NAME)"
	@echo "$(GREEN)권한 수정 완료$(NC)"

check-compose-config: ## Docker Compose 설정 검증
	@echo "$(GREEN)Docker Compose 설정 검증 중...$(NC)"
	$(COMPOSE_CMD) config
