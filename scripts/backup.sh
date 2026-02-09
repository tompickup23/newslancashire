#!/bin/bash
# Automated backup script - runs daily
DATE=$(date +%Y%m%d)
BACKUP_DIR=~/backups
DB_PATH=~/newslancashire/db/news.db
SITE_PATH=~/newslancashire/site

mkdir -p $BACKUP_DIR

# Backup database
sqlite3 $DB_PATH .backup $BACKUP_DIR/news_$DATE.db

# Backup site content
tar -czf $BACKUP_DIR/site_content_$DATE.tar.gz -C $SITE_PATH content

# Keep only last 7 days of backups
find $BACKUP_DIR -name '*.db' -mtime +7 -delete
find $BACKUP_DIR -name '*.tar.gz' -mtime +7 -delete

echo "Backup completed: $DATE"
ls -lh $BACKUP_DIR
