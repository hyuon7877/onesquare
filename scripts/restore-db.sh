#!/bin/bash

# Database Restoration Script
# OneSquare Project - 데이터베이스 복원 스크립트

set -e

# Configuration
BACKUP_DIR="/backup/database"
DB_NAME="${DB_NAME:-onesquare_db}"
DB_USER="${DB_USER:-onesquare_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

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

# Function to list available backups
list_backups() {
    echo -e "\n${BLUE}Available backups:${NC}"
    echo "----------------------------------------"
    
    if [ -d "${BACKUP_DIR}" ]; then
        BACKUPS=$(ls -1t "${BACKUP_DIR}"/db_backup_*.sql.gz 2>/dev/null)
        if [ -z "${BACKUPS}" ]; then
            log_warning "No backups found in ${BACKUP_DIR}"
            return 1
        fi
        
        i=1
        for backup in ${BACKUPS}; do
            SIZE=$(du -h "${backup}" | cut -f1)
            DATE=$(basename "${backup}" | sed 's/db_backup_\(.*\)\.sql\.gz/\1/')
            echo "${i}. $(basename ${backup}) - ${SIZE} - ${DATE}"
            ((i++))
        done
    else
        log_error "Backup directory ${BACKUP_DIR} does not exist!"
        return 1
    fi
    
    echo "----------------------------------------"
}

# Function to select backup file
select_backup() {
    if [ -n "$1" ]; then
        # Backup file specified as argument
        if [ -f "$1" ]; then
            BACKUP_FILE="$1"
        else
            log_error "Specified backup file not found: $1"
            exit 1
        fi
    else
        # Interactive selection
        list_backups || exit 1
        
        echo -n "Select backup number (or enter path to backup file): "
        read selection
        
        if [[ "${selection}" =~ ^[0-9]+$ ]]; then
            # Numeric selection
            BACKUP_FILE=$(ls -1t "${BACKUP_DIR}"/db_backup_*.sql.gz 2>/dev/null | sed -n "${selection}p")
            if [ -z "${BACKUP_FILE}" ]; then
                log_error "Invalid selection!"
                exit 1
            fi
        elif [ -f "${selection}" ]; then
            # File path provided
            BACKUP_FILE="${selection}"
        else
            log_error "Invalid selection or file not found!"
            exit 1
        fi
    fi
    
    log_message "Selected backup: ${BACKUP_FILE}"
}

# Function to create database backup before restoration
create_safety_backup() {
    log_message "Creating safety backup before restoration..."
    SAFETY_BACKUP="${BACKUP_DIR}/safety_backup_$(date +%Y%m%d_%H%M%S).sql.gz"
    
    export PGPASSWORD="${DB_PASSWORD}"
    
    if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
        --clean --no-owner --no-acl 2>/dev/null | gzip > "${SAFETY_BACKUP}"; then
        log_message "Safety backup created: ${SAFETY_BACKUP}"
    else
        log_warning "Failed to create safety backup. Continue anyway? (y/N)"
        read -r response
        if [[ ! "${response}" =~ ^[Yy]$ ]]; then
            log_message "Restoration cancelled."
            exit 1
        fi
    fi
    
    unset PGPASSWORD
}

# Function to restore database
restore_database() {
    local backup_file="$1"
    
    log_message "Starting database restoration from ${backup_file}..."
    
    # Verify backup file integrity
    log_message "Verifying backup integrity..."
    if ! gunzip -t "${backup_file}" 2>/dev/null; then
        log_error "Backup file appears to be corrupted!"
        exit 1
    fi
    
    # Stop application services
    log_warning "Stopping application services..."
    if command -v docker-compose &> /dev/null; then
        docker-compose stop web 2>/dev/null || true
    fi
    
    # Kill active database connections
    log_message "Terminating active database connections..."
    export PGPASSWORD="${DB_PASSWORD}"
    
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres <<EOF 2>/dev/null || true
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${DB_NAME}'
  AND pid <> pg_backend_pid();
EOF
    
    # Restore database
    log_message "Restoring database..."
    if gunzip -c "${backup_file}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" 2>/dev/null; then
        log_message "Database restored successfully!"
    else
        log_error "Database restoration failed!"
        
        # Attempt to restore safety backup
        if [ -f "${SAFETY_BACKUP}" ]; then
            log_warning "Attempting to restore safety backup..."
            gunzip -c "${SAFETY_BACKUP}" | psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" 2>/dev/null || true
        fi
        
        exit 1
    fi
    
    unset PGPASSWORD
    
    # Run Django migrations
    log_message "Running Django migrations..."
    if [ -f "/opt/onesquare/src/manage.py" ]; then
        cd /opt/onesquare/src
        python manage.py migrate --noinput 2>/dev/null || log_warning "Migrations failed"
    fi
    
    # Restart application services
    log_message "Restarting application services..."
    if command -v docker-compose &> /dev/null; then
        docker-compose start web 2>/dev/null || true
    fi
    
    # Verify restoration
    log_message "Verifying database restoration..."
    export PGPASSWORD="${DB_PASSWORD}"
    
    TABLE_COUNT=$(psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null)
    
    unset PGPASSWORD
    
    log_info "Database contains ${TABLE_COUNT} tables"
    
    # Log restoration details
    cat > "${BACKUP_DIR}/last_restore.json" <<EOF
{
    "timestamp": "$(date -Iseconds)",
    "backup_file": "${backup_file}",
    "database": "${DB_NAME}",
    "table_count": ${TABLE_COUNT},
    "safety_backup": "${SAFETY_BACKUP:-none}"
}
EOF
    
    log_message "Restoration completed successfully!"
}

# Main script
echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   Database Restoration Tool${NC}"
echo -e "${BLUE}======================================${NC}\n"

# Check if PostgreSQL client is installed
if ! command -v psql &> /dev/null; then
    log_error "psql command not found. Please install PostgreSQL client."
    exit 1
fi

# Parse command line arguments
SKIP_SAFETY_BACKUP=false
AUTO_CONFIRM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-safety)
            SKIP_SAFETY_BACKUP=true
            shift
            ;;
        --yes|-y)
            AUTO_CONFIRM=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [BACKUP_FILE]"
            echo ""
            echo "Options:"
            echo "  --skip-safety    Skip creating safety backup"
            echo "  --yes, -y        Auto-confirm restoration"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Example:"
            echo "  $0                                    # Interactive mode"
            echo "  $0 /backup/db_backup_20240101.sql.gz  # Restore specific backup"
            echo "  $0 --yes --skip-safety                # Auto-restore latest backup"
            exit 0
            ;;
        *)
            BACKUP_FILE="$1"
            shift
            ;;
    esac
done

# Select backup file
select_backup "${BACKUP_FILE}"

# Show restoration plan
echo -e "\n${YELLOW}Restoration Plan:${NC}"
echo "----------------------------------------"
echo "Backup file: ${BACKUP_FILE}"
echo "Target database: ${DB_NAME}@${DB_HOST}:${DB_PORT}"
echo "Safety backup: $([ ${SKIP_SAFETY_BACKUP} = true ] && echo 'SKIPPED' || echo 'ENABLED')"
echo "----------------------------------------"

# Confirm restoration
if [ ${AUTO_CONFIRM} = false ]; then
    echo -e "\n${YELLOW}WARNING: This will replace all data in the database!${NC}"
    echo -n "Do you want to continue? (y/N): "
    read -r response
    
    if [[ ! "${response}" =~ ^[Yy]$ ]]; then
        log_message "Restoration cancelled by user."
        exit 0
    fi
fi

# Create safety backup unless skipped
if [ ${SKIP_SAFETY_BACKUP} = false ]; then
    create_safety_backup
fi

# Perform restoration
restore_database "${BACKUP_FILE}"

# Send notification (optional)
if [ -n "${SLACK_WEBHOOK_URL}" ]; then
    curl -X POST "${SLACK_WEBHOOK_URL}" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"✅ Database restored successfully from: $(basename ${BACKUP_FILE})\"}" \
        2>/dev/null || true
fi

exit 0