#!/bin/bash
# base/backup_app.sh
# Backup Script for sattabase Application
# Run using crontab or manually to backup database and media files
# Click Add Cron Job.
# Label: sattabase Daily Backup
# Schedule: Choose Daily (e.g., 0 3 * * * for 3:00 AM).
# bash /path/to/your/base/backup_app.sh
# Ensure your project folder is owned by the user running the cron job.
# The chown -R appuser:appuser /app inside your Dockerfile is perfect for internal operations, but on the Host, ensure the media folder has 755 permissions so the backup script can read it.

## ====================================================================
## 2. The "Host-Side" Fix (Crucial)
# # Create the folders manually
# mkdir -p backend/staticfiles backend/media backend/logs
# # Set the ownership to your current host user (e.g., 'ubuntu' or 'admin')
# sudo chown -R $USER:$USER backend/staticfiles backend/media backend/logs
# # Give the container permission to write
# chmod -R 775 backend/media backend/logs
## ====================================================================


# Exit on any error
set -e

# --- Configuration ---
# Use absolute paths. Replace 'youruser' with the actual CloudPanel user.
PROJECT_DIR="/home/youruser/base" 
BACKUP_PATH="/home/youruser/backups/sattabase"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RETENTION_DAYS=15

# 1. Load Environment Variables safely
if [ -f "$PROJECT_DIR/.env" ]; then
    # Use 'set -a' to export all variables from the file
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "Error: .env file not found at $PROJECT_DIR/.env"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_PATH"

echo "[$TIMESTAMP] Starting backup..."

# 2. Backup Database
# Pass PGPASSWORD into the docker environment so pg_dump doesn't ask for it
echo "Dumping database..."
docker exec -e PGPASSWORD="$SB_DB_PASSWORD" sb-postgres \
    pg_dump -U "$SB_DB_USER" "$SB_DB_NAME" | gzip > "$BACKUP_PATH/db_$TIMESTAMP.sql.gz"

# 3. Backup Media Folder
# We use --absolute-names to avoid 'removing leading /' warnings
echo "Archiving media files..."
tar -czf "$BACKUP_PATH/media_$TIMESTAMP.tar.gz" -C "$PROJECT_DIR/backend" media

# 4. Cleanup old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_PATH" -type f -name "*.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully: $BACKUP_PATH/db_$TIMESTAMP.sql.gz"