#!/bin/bash

# Media Files Backup Script
# OneSquare Project - 미디어 파일 백업 스크립트

set -e

# Configuration
BACKUP_DIR="/backup/media"
MEDIA_DIR="/opt/onesquare/media"
STATIC_DIR="/opt/onesquare/staticfiles"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/media_backup_${TIMESTAMP}.tar.gz"
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

# Check if media directory exists
if [ ! -d "${MEDIA_DIR}" ]; then
    log_warning "Media directory ${MEDIA_DIR} does not exist. Creating empty backup..."
    MEDIA_DIR="/tmp/empty_media"
    mkdir -p "${MEDIA_DIR}"
fi

# Start backup
log_message "Starting media files backup..."
log_message "Source directories: ${MEDIA_DIR}, ${STATIC_DIR}"

# Calculate total size
if [ -d "${MEDIA_DIR}" ] && [ -d "${STATIC_DIR}" ]; then
    TOTAL_SIZE=$(du -sh "${MEDIA_DIR}" "${STATIC_DIR}" 2>/dev/null | tail -1 | cut -f1)
    log_message "Total size to backup: ${TOTAL_SIZE}"
fi

# Create incremental backup if previous backup exists
LATEST_BACKUP="${BACKUP_DIR}/latest_backup.tar.gz"
if [ -f "${LATEST_BACKUP}" ]; then
    log_message "Creating incremental backup based on latest backup..."
    
    # Create snapshot file for incremental backup
    SNAPSHOT_FILE="${BACKUP_DIR}/backup.snapshot"
    
    # Perform incremental backup
    tar -czf "${BACKUP_FILE}" \
        --listed-incremental="${SNAPSHOT_FILE}" \
        --exclude="*.pyc" \
        --exclude="__pycache__" \
        --exclude=".DS_Store" \
        --exclude="thumbs.db" \
        --exclude="*.tmp" \
        --exclude="*.log" \
        -C / \
        "${MEDIA_DIR#/}" \
        "${STATIC_DIR#/}" 2>/dev/null || true
    
    BACKUP_TYPE="incremental"
else
    log_message "Creating full backup..."
    
    # Perform full backup
    tar -czf "${BACKUP_FILE}" \
        --exclude="*.pyc" \
        --exclude="__pycache__" \
        --exclude=".DS_Store" \
        --exclude="thumbs.db" \
        --exclude="*.tmp" \
        --exclude="*.log" \
        -C / \
        "${MEDIA_DIR#/}" \
        "${STATIC_DIR#/}" 2>/dev/null || true
    
    BACKUP_TYPE="full"
fi

# Check if backup was created successfully
if [ -f "${BACKUP_FILE}" ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    log_message "Media backup completed successfully!"
    log_message "Backup file: ${BACKUP_FILE}"
    log_message "Backup size: ${BACKUP_SIZE}"
    log_message "Backup type: ${BACKUP_TYPE}"
    
    # Verify backup integrity
    if tar -tzf "${BACKUP_FILE}" >/dev/null 2>&1; then
        log_message "Backup integrity verified."
    else
        log_error "Backup file appears to be corrupted!"
        exit 1
    fi
    
    # Clean up old backups (keep only last N backups)
    BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/media_backup_*.tar.gz 2>/dev/null | wc -l)
    if [ ${BACKUP_COUNT} -gt ${MAX_BACKUPS} ]; then
        log_message "Cleaning up old backups (keeping last ${MAX_BACKUPS})..."
        ls -1t "${BACKUP_DIR}"/media_backup_*.tar.gz | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f
    fi
    
    # Remove backups older than RETENTION_DAYS
    log_message "Removing backups older than ${RETENTION_DAYS} days..."
    find "${BACKUP_DIR}" -name "media_backup_*.tar.gz" -type f -mtime +${RETENTION_DAYS} -delete
    
    # Create latest symlink
    ln -sf "${BACKUP_FILE}" "${LATEST_BACKUP}"
    
    # Calculate checksums for verification
    CHECKSUM=$(sha256sum "${BACKUP_FILE}" | cut -d' ' -f1)
    
    # Log backup metadata
    cat > "${BACKUP_DIR}/media_metadata.json" <<EOF
{
    "timestamp": "${TIMESTAMP}",
    "type": "${BACKUP_TYPE}",
    "media_dir": "${MEDIA_DIR}",
    "static_dir": "${STATIC_DIR}",
    "file": "${BACKUP_FILE}",
    "size": "${BACKUP_SIZE}",
    "checksum": "${CHECKSUM}",
    "retention_days": ${RETENTION_DAYS},
    "max_backups": ${MAX_BACKUPS}
}
EOF
    
    log_message "Backup process completed successfully!"
    
else
    log_error "Media backup failed!"
    exit 1
fi

# Optional: Sync to cloud storage (S3, Google Cloud Storage, etc.)
if [ -n "${AWS_S3_BUCKET}" ]; then
    log_message "Uploading backup to S3..."
    
    # Use multipart upload for large files
    if aws s3 cp "${BACKUP_FILE}" "s3://${AWS_S3_BUCKET}/media-backups/" \
        --storage-class STANDARD_IA \
        --metadata "type=${BACKUP_TYPE},timestamp=${TIMESTAMP}"; then
        log_message "Backup uploaded to S3 successfully!"
        
        # Also upload metadata
        aws s3 cp "${BACKUP_DIR}/media_metadata.json" \
            "s3://${AWS_S3_BUCKET}/media-backups/metadata/" 2>/dev/null || true
    else
        log_warning "Failed to upload backup to S3"
    fi
fi

# Optional: Rsync to remote server
if [ -n "${REMOTE_BACKUP_HOST}" ]; then
    log_message "Syncing backup to remote server ${REMOTE_BACKUP_HOST}..."
    
    rsync -avz --progress "${BACKUP_FILE}" \
        "${REMOTE_BACKUP_USER}@${REMOTE_BACKUP_HOST}:${REMOTE_BACKUP_PATH}/" \
        2>/dev/null || log_warning "Failed to sync to remote server"
fi

# Send notification (optional)
if [ -n "${SLACK_WEBHOOK_URL}" ]; then
    curl -X POST "${SLACK_WEBHOOK_URL}" \
        -H 'Content-Type: application/json' \
        -d "{\"text\":\"✅ Media backup completed (${BACKUP_TYPE}): ${BACKUP_FILE} (${BACKUP_SIZE})\"}" \
        2>/dev/null || log_warning "Failed to send Slack notification"
fi

# Clean up temporary directory if created
if [ "${MEDIA_DIR}" = "/tmp/empty_media" ]; then
    rm -rf "${MEDIA_DIR}"
fi

exit 0