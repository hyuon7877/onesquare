#!/bin/bash

# Rollback Script
# OneSquare Project - 배포 롤백 스크립트

set -e

# Configuration
PROJECT_DIR="/opt/onesquare"
BACKUP_DIR="/backup"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-}"
ROLLBACK_TAG="${1:-previous}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Function to get current deployment info
get_current_deployment() {
    if [ -f "${PROJECT_DIR}/.deployment" ]; then
        source "${PROJECT_DIR}/.deployment"
        log_info "Current deployment:"
        log_info "  - Version: ${CURRENT_VERSION:-unknown}"
        log_info "  - Deployed: ${DEPLOYMENT_DATE:-unknown}"
        log_info "  - Git SHA: ${GIT_SHA:-unknown}"
    else
        log_warning "No deployment information found"
    fi
}

# Function to backup current state
backup_current_state() {
    log_message "Creating backup of current state..."
    
    BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    ROLLBACK_BACKUP_DIR="${BACKUP_DIR}/rollback_${BACKUP_TIMESTAMP}"
    
    mkdir -p "${ROLLBACK_BACKUP_DIR}"
    
    # Backup database
    if [ -x "${PROJECT_DIR}/scripts/backup-db.sh" ]; then
        log_message "Backing up database..."
        "${PROJECT_DIR}/scripts/backup-db.sh" || log_warning "Database backup failed"
    fi
    
    # Backup media files
    if [ -x "${PROJECT_DIR}/scripts/backup-media.sh" ]; then
        log_message "Backing up media files..."
        "${PROJECT_DIR}/scripts/backup-media.sh" || log_warning "Media backup failed"
    fi
    
    # Backup current code
    log_message "Backing up current code..."
    tar -czf "${ROLLBACK_BACKUP_DIR}/code_backup.tar.gz" \
        -C "${PROJECT_DIR}" \
        --exclude=".git" \
        --exclude="media" \
        --exclude="staticfiles" \
        --exclude="*.pyc" \
        --exclude="__pycache__" \
        . 2>/dev/null || log_warning "Code backup failed"
    
    # Save current Docker images
    if command -v docker &> /dev/null; then
        log_message "Saving current Docker images..."
        docker images --format "{{.Repository}}:{{.Tag}}" | \
            grep -E "(onesquare|${PROJECT_NAME})" | \
            while read image; do
                IMAGE_FILE="${ROLLBACK_BACKUP_DIR}/$(echo ${image} | tr '/:' '_').tar"
                docker save "${image}" -o "${IMAGE_FILE}" 2>/dev/null || true
            done
    fi
    
    log_message "Current state backed up to: ${ROLLBACK_BACKUP_DIR}"
}

# Function to rollback using Docker
rollback_docker() {
    log_message "Rolling back Docker deployment..."
    
    cd "${PROJECT_DIR}"
    
    # Get previous image tag
    if [ "${ROLLBACK_TAG}" = "previous" ]; then
        # Find previous deployment tag
        PREVIOUS_TAG=$(docker images --format "{{.Repository}}:{{.Tag}}" | \
            grep -E "onesquare" | \
            grep -v "latest" | \
            head -2 | tail -1 | cut -d: -f2)
        
        if [ -z "${PREVIOUS_TAG}" ]; then
            log_error "No previous Docker image found!"
            exit 1
        fi
    else
        PREVIOUS_TAG="${ROLLBACK_TAG}"
    fi
    
    log_info "Rolling back to image tag: ${PREVIOUS_TAG}"
    
    # Update docker-compose.yml to use previous tag
    if [ -f "docker-compose.yml" ]; then
        sed -i.bak "s/onesquare:latest/onesquare:${PREVIOUS_TAG}/g" docker-compose.yml
    fi
    
    # Stop current containers
    log_message "Stopping current containers..."
    docker-compose down || true
    
    # Start with previous version
    log_message "Starting previous version..."
    docker-compose up -d
    
    # Wait for services to be ready
    sleep 10
    
    # Run migrations
    log_message "Running database migrations..."
    docker-compose exec -T web python manage.py migrate --noinput || true
    
    # Collect static files
    log_message "Collecting static files..."
    docker-compose exec -T web python manage.py collectstatic --noinput || true
}

# Function to rollback using Git
rollback_git() {
    log_message "Rolling back using Git..."
    
    cd "${PROJECT_DIR}/src"
    
    # Get current branch
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    
    # Get previous commit
    if [ "${ROLLBACK_TAG}" = "previous" ]; then
        PREVIOUS_COMMIT=$(git rev-parse HEAD~1)
    else
        PREVIOUS_COMMIT="${ROLLBACK_TAG}"
    fi
    
    log_info "Rolling back to commit: ${PREVIOUS_COMMIT}"
    
    # Create rollback branch
    ROLLBACK_BRANCH="rollback-$(date +%Y%m%d-%H%M%S)"
    git checkout -b "${ROLLBACK_BRANCH}" "${PREVIOUS_COMMIT}"
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        log_message "Installing Python dependencies..."
        pip install -r requirements.txt --quiet
    fi
    
    # Run migrations
    log_message "Running database migrations..."
    python manage.py migrate --noinput
    
    # Collect static files
    log_message "Collecting static files..."
    python manage.py collectstatic --noinput
    
    # Restart services
    log_message "Restarting services..."
    if command -v systemctl &> /dev/null; then
        systemctl restart gunicorn || true
        systemctl restart nginx || true
    elif command -v supervisorctl &> /dev/null; then
        supervisorctl restart all || true
    fi
}

# Function to verify rollback
verify_rollback() {
    log_message "Verifying rollback..."
    
    # Check if application is responding
    HEALTH_CHECK_URL="${HEALTH_CHECK_URL:-http://localhost:8081/health/}"
    
    for i in {1..30}; do
        if curl -f "${HEALTH_CHECK_URL}" >/dev/null 2>&1; then
            log_message "Application is responding!"
            break
        fi
        
        if [ $i -eq 30 ]; then
            log_error "Application is not responding after rollback!"
            return 1
        fi
        
        sleep 2
    done
    
    # Check database connectivity
    if [ -f "${PROJECT_DIR}/src/manage.py" ]; then
        cd "${PROJECT_DIR}/src"
        python manage.py dbshell -c "SELECT 1;" >/dev/null 2>&1 || {
            log_error "Database connectivity check failed!"
            return 1
        }
    fi
    
    log_message "Rollback verification completed successfully!"
    return 0
}

# Function to restore from backup
restore_from_backup() {
    log_message "Restoring from backup..."
    
    # Find latest rollback backup
    LATEST_BACKUP=$(ls -1dt "${BACKUP_DIR}"/rollback_* 2>/dev/null | head -1)
    
    if [ -z "${LATEST_BACKUP}" ]; then
        log_error "No rollback backup found!"
        exit 1
    fi
    
    log_info "Restoring from: ${LATEST_BACKUP}"
    
    # Restore code
    if [ -f "${LATEST_BACKUP}/code_backup.tar.gz" ]; then
        log_message "Restoring code..."
        tar -xzf "${LATEST_BACKUP}/code_backup.tar.gz" -C "${PROJECT_DIR}"
    fi
    
    # Restore Docker images
    for image_file in "${LATEST_BACKUP}"/*.tar; do
        if [ -f "${image_file}" ]; then
            log_message "Loading Docker image: $(basename ${image_file})"
            docker load -i "${image_file}" || true
        fi
    done
    
    # Restore database if needed
    if [ -f "${BACKUP_DIR}/database/latest_backup.sql.gz" ]; then
        log_warning "Database restoration available. Run restore-db.sh if needed."
    fi
}

# Main script
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   Deployment Rollback Tool${NC}"
echo -e "${BLUE}======================================${NC}\n"

# Check deployment method
if [ -f "${PROJECT_DIR}/docker-compose.yml" ] && command -v docker-compose &> /dev/null; then
    DEPLOYMENT_METHOD="docker"
elif [ -d "${PROJECT_DIR}/.git" ] && command -v git &> /dev/null; then
    DEPLOYMENT_METHOD="git"
else
    DEPLOYMENT_METHOD="backup"
fi

log_info "Deployment method: ${DEPLOYMENT_METHOD}"

# Get current deployment info
get_current_deployment

# Confirm rollback
if [ "$2" != "--force" ]; then
    echo -e "\n${YELLOW}WARNING: This will rollback the current deployment!${NC}"
    echo -n "Do you want to continue? (y/N): "
    read -r response
    
    if [[ ! "${response}" =~ ^[Yy]$ ]]; then
        log_message "Rollback cancelled by user."
        exit 0
    fi
fi

# Backup current state
backup_current_state

# Perform rollback based on deployment method
case "${DEPLOYMENT_METHOD}" in
    docker)
        rollback_docker
        ;;
    git)
        rollback_git
        ;;
    backup)
        restore_from_backup
        ;;
    *)
        log_error "Unknown deployment method!"
        exit 1
        ;;
esac

# Verify rollback
if verify_rollback; then
    # Update deployment info
    cat > "${PROJECT_DIR}/.deployment" <<EOF
CURRENT_VERSION="${ROLLBACK_TAG}"
DEPLOYMENT_DATE="$(date -Iseconds)"
DEPLOYMENT_TYPE="rollback"
PREVIOUS_VERSION="${CURRENT_VERSION:-unknown}"
ROLLBACK_FROM="${GIT_SHA:-unknown}"
EOF
    
    log_message "Rollback completed successfully!"
    
    # Send notification
    if [ -n "${SLACK_WEBHOOK_URL}" ]; then
        curl -X POST "${SLACK_WEBHOOK_URL}" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"⚠️ Production rolled back to: ${ROLLBACK_TAG}\"}" \
            2>/dev/null || true
    fi
else
    log_error "Rollback verification failed!"
    log_warning "You may need to manually intervene or restore from backup."
    exit 1
fi

exit 0