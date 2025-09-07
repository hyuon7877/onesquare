#!/bin/bash

# Setup Backup Cron Jobs
# OneSquare Project - 자동 백업 스케줄 설정

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   Backup Scheduling Setup${NC}"
echo -e "${BLUE}======================================${NC}\n"

# Script directory
SCRIPT_DIR="/opt/onesquare/scripts"
LOG_DIR="/var/log/onesquare"

# Create log directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Create crontab entries
CRON_FILE="/tmp/onesquare_backup_cron"

cat > "${CRON_FILE}" << 'EOF'
# OneSquare Backup Schedule
# ====================================

# Environment variables
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=admin@onesquare.com

# Database backup - Daily at 2:00 AM KST (17:00 UTC)
0 17 * * * /opt/onesquare/scripts/backup-db.sh >> /var/log/onesquare/backup-db.log 2>&1

# Media files backup - Weekly on Sunday at 3:00 AM KST (18:00 UTC)
0 18 * * 0 /opt/onesquare/scripts/backup-media.sh >> /var/log/onesquare/backup-media.log 2>&1

# Cleanup old backups - Daily at 4:00 AM KST (19:00 UTC)
0 19 * * * find /backup -name "*.gz" -mtime +30 -delete >> /var/log/onesquare/cleanup.log 2>&1

# Health check - Every 5 minutes
*/5 * * * * curl -f http://localhost:8081/health/ || echo "Health check failed at $(date)" >> /var/log/onesquare/health-check.log

# Disk space check - Daily at 6:00 AM KST (21:00 UTC)
0 21 * * * df -h | grep -E '^/dev/' | awk '{if(int($5) > 80) print "Warning: " $6 " is " $5 " full"}' >> /var/log/onesquare/disk-space.log

# Log rotation - Weekly on Monday at 1:00 AM KST (16:00 UTC on Sunday)
0 16 * * 0 /usr/sbin/logrotate /opt/onesquare/scripts/logrotate.conf --state /var/lib/logrotate/onesquare.state

# Test backup restore (staging only) - Monthly on 1st at 5:00 AM KST (20:00 UTC on last day)
0 20 1 * * [ "$ENVIRONMENT" = "staging" ] && /opt/onesquare/scripts/test-restore.sh >> /var/log/onesquare/test-restore.log 2>&1

EOF

echo -e "${GREEN}Crontab entries created${NC}"

# Install crontab for current user
echo -e "${YELLOW}Installing crontab for current user...${NC}"
crontab -l 2>/dev/null > /tmp/current_cron || true
cat "${CRON_FILE}" >> /tmp/current_cron
crontab /tmp/current_cron
rm /tmp/current_cron

echo -e "${GREEN}Crontab installed for $(whoami)${NC}"

# Create logrotate configuration
cat > "${SCRIPT_DIR}/logrotate.conf" << 'EOF'
/var/log/onesquare/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        # Restart rsyslog if needed
        /usr/bin/killall -SIGUSR1 rsyslogd 2>/dev/null || true
    endscript
}

/opt/onesquare/src/logs/*.log {
    weekly
    rotate 4
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        # Signal Django to reopen log files
        if [ -f /opt/onesquare/src/run/gunicorn.pid ]; then
            kill -USR1 $(cat /opt/onesquare/src/run/gunicorn.pid) 2>/dev/null || true
        fi
    endscript
}
EOF

echo -e "${GREEN}Logrotate configuration created${NC}"

# Create systemd timer as alternative (for systems with systemd)
if command -v systemctl &> /dev/null; then
    echo -e "${YELLOW}Creating systemd timers...${NC}"
    
    # Database backup timer
    cat > /etc/systemd/system/onesquare-backup-db.service << 'EOF'
[Unit]
Description=OneSquare Database Backup
After=network.target

[Service]
Type=oneshot
ExecStart=/opt/onesquare/scripts/backup-db.sh
StandardOutput=append:/var/log/onesquare/backup-db.log
StandardError=append:/var/log/onesquare/backup-db.log

[Install]
WantedBy=multi-user.target
EOF

    cat > /etc/systemd/system/onesquare-backup-db.timer << 'EOF'
[Unit]
Description=Daily OneSquare Database Backup
Requires=onesquare-backup-db.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Media backup timer
    cat > /etc/systemd/system/onesquare-backup-media.service << 'EOF'
[Unit]
Description=OneSquare Media Files Backup
After=network.target

[Service]
Type=oneshot
ExecStart=/opt/onesquare/scripts/backup-media.sh
StandardOutput=append:/var/log/onesquare/backup-media.log
StandardError=append:/var/log/onesquare/backup-media.log

[Install]
WantedBy=multi-user.target
EOF

    cat > /etc/systemd/system/onesquare-backup-media.timer << 'EOF'
[Unit]
Description=Weekly OneSquare Media Backup
Requires=onesquare-backup-media.service

[Timer]
OnCalendar=weekly
OnCalendar=Sun 03:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # Enable and start timers
    systemctl daemon-reload
    systemctl enable onesquare-backup-db.timer onesquare-backup-media.timer 2>/dev/null || true
    systemctl start onesquare-backup-db.timer onesquare-backup-media.timer 2>/dev/null || true
    
    echo -e "${GREEN}Systemd timers created and enabled${NC}"
fi

# Create backup monitoring script
cat > "${SCRIPT_DIR}/monitor-backups.sh" << 'EOF'
#!/bin/bash

# Check if backups are running as expected
BACKUP_DIR="/backup"
ALERT_EMAIL="admin@onesquare.com"
MAX_AGE_HOURS=26  # Alert if backup is older than 26 hours

# Check database backup
DB_BACKUP=$(find ${BACKUP_DIR}/database -name "db_backup_*.sql.gz" -type f -mmin -$((MAX_AGE_HOURS * 60)) | head -1)
if [ -z "$DB_BACKUP" ]; then
    echo "WARNING: No recent database backup found (older than ${MAX_AGE_HOURS} hours)" | \
        mail -s "OneSquare Backup Alert" ${ALERT_EMAIL} 2>/dev/null || \
        echo "WARNING: No recent database backup found" >> /var/log/onesquare/backup-monitor.log
fi

# Check media backup (weekly, so check for 8 days)
MEDIA_BACKUP=$(find ${BACKUP_DIR}/media -name "media_backup_*.tar.gz" -type f -mtime -8 | head -1)
if [ -z "$MEDIA_BACKUP" ]; then
    echo "WARNING: No recent media backup found (older than 8 days)" | \
        mail -s "OneSquare Backup Alert" ${ALERT_EMAIL} 2>/dev/null || \
        echo "WARNING: No recent media backup found" >> /var/log/onesquare/backup-monitor.log
fi

# Check disk space
DISK_USAGE=$(df ${BACKUP_DIR} | tail -1 | awk '{print $5}' | sed 's/%//')
if [ ${DISK_USAGE} -gt 80 ]; then
    echo "WARNING: Backup disk usage is ${DISK_USAGE}%" | \
        mail -s "OneSquare Disk Space Alert" ${ALERT_EMAIL} 2>/dev/null || \
        echo "WARNING: Backup disk usage is ${DISK_USAGE}%" >> /var/log/onesquare/backup-monitor.log
fi
EOF

chmod +x "${SCRIPT_DIR}/monitor-backups.sh"

echo -e "${GREEN}Backup monitoring script created${NC}"

# Make all scripts executable
chmod +x ${SCRIPT_DIR}/*.sh

# Display current crontab
echo -e "\n${BLUE}Current crontab entries:${NC}"
crontab -l | grep -E "onesquare|backup" || echo "No OneSquare backup jobs found"

# Display systemd timers if available
if command -v systemctl &> /dev/null; then
    echo -e "\n${BLUE}Systemd timers status:${NC}"
    systemctl list-timers --all | grep onesquare || echo "No OneSquare timers found"
fi

echo -e "\n${GREEN}======================================${NC}"
echo -e "${GREEN}   Backup scheduling setup complete!${NC}"
echo -e "${GREEN}======================================${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Verify crontab: crontab -l"
echo "2. Test backup scripts manually:"
echo "   ${SCRIPT_DIR}/backup-db.sh"
echo "   ${SCRIPT_DIR}/backup-media.sh"
echo "3. Check logs: tail -f /var/log/onesquare/*.log"
echo "4. Monitor backups: ${SCRIPT_DIR}/monitor-backups.sh"

# Cleanup
rm -f "${CRON_FILE}"