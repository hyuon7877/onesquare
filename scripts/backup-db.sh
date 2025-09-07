#!/bin/bash

# Database Backup Script
# OneSquare Project - 백업 스크립트

set -e

# Configuration
BACKUP_DIR="/backup/database"
DB_NAME="${DB_NAME:-onesquare_db}"
DB_USER="${DB_USER:-onesquare_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30
MAX_BACKUPS=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Check if PostgreSQL client is installed
if ! command -v pg_dump &> /dev/null; then
    log_error "pg_dump command not found. Please install PostgreSQL client."
    exit 1
fi

# Start backup
log_message "Starting database backup for ${DB_NAME}..."

# Perform database backup
export PGPASSWORD="${DB_PASSWORD}"

if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" \
    --clean --no-owner --no-acl --verbose 2>/dev/null | gzip > "${BACKUP_FILE}"; then
    
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    log_message "Database backup completed successfully!"
    log_message "Backup file: ${BACKUP_FILE}"
    log_message "Backup size: ${BACKUP_SIZE}"
    
    # Verify backup integrity
    if gunzip -t "${BACKUP_FILE}" 2>/dev/null; then
        log_message "Backup integrity verified."
    else
        log_error "Backup file appears to be corrupted!"
        exit 1
    fi
    
    # Clean up old backups (keep only last N backups)
    BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/db_backup_*.sql.gz 2>/dev/null | wc -l)
    if [ ${BACKUP_COUNT} -gt ${MAX_BACKUPS} ]; then
        log_message "Cleaning up old backups (keeping last ${MAX_BACKUPS})..."
        ls -1t "${BACKUP_DIR}"/db_backup_*.sql.gz | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f
    fi
    
    # Also remove backups older than RETENTION_DAYS
    log_message "Removing backups older than ${RETENTION_DAYS} days..."
    find "${BACKUP_DIR}" -name "db_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
    
    # Create latest symlink
    ln -sf "${BACKUP_FILE}" "${BACKUP_DIR}/latest_backup.sql.gz"
    
    # Log backup metadata
    cat > "${BACKUP_DIR}/backup_metadata.json" <<EOF
{
    "timestamp": "${TIMESTAMP}",
    "database": "${DB_NAME}",
    "file": "${BACKUP_FILE}",
    "size": "${BACKUP_SIZE}",
    "retention_days": ${RETENTION_DAYS},
    "max_backups": ${MAX_BACKUPS}
}
EOF
    
    log_message "Backup process completed successfully!"
    
else
    log_error "Database backup failed!"
    exit 1
fi

# Cleanup
unset PGPASSWORD

# Optional: Upload to cloud storage (S3, Google Cloud Storage, etc.)
if [ -n "${AWS_S3_BUCKET}" ]; then
    log_message "Uploading backup to S3..."
    if aws s3 cp "${BACKUP_FILE}" "s3://${AWS_S3_BUCKET}/database-backups/" --storage-class GLACIER_IR; then
        log_message "Backup uploaded to S3 successfully!"
    else
        log_warning "Failed to upload backup to S3"
    fi
fi

# Send notification (optional)
if [ -n "${SLACK_WEBHOOK_URL}" ]; then
    curl -X POST "${SLACK_WEBHOOK_URL}" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"✅ Database backup completed: ${BACKUP_FILE} (${BACKUP_SIZE})\"}" \
        2>/dev/null || log_warning "Failed to send Slack notification"
fi

exit 0