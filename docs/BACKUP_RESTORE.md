# Backup and Restore Guide

Complete guide for backing up and restoring AAX data.

## Overview

AAX uses Docker volumes for persistent data storage across several components:

| Component  | Volume          | Data Stored                            |
| ---------- | --------------- | -------------------------------------- |
| AWX        | `awx-data`      | Settings, SSH keys, credentials        |
| PostgreSQL | `postgres-data` | All databases (AWX, Galaxy, Pulp, EDA) |
| Redis      | `redis-data`    | Cache and task queue                   |
| Logs       | `awx-logs`      | Application logs                       |
| Projects   | `awx-projects`  | Playbook projects                      |

---

## Quick Backup

### Create a complete backup

```bash
#!/bin/bash
# Backup all AAX data with timestamp

BACKUP_DIR="$HOME/aax-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="aax-backup-$TIMESTAMP"

mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
cd "$BACKUP_DIR/$BACKUP_NAME"

# Stop containers gracefully
docker compose stop

# Backup all volumes
echo "Backing up Docker volumes..."
docker run --rm \
  -v awx-data:/data \
  -v "$PWD":/backup \
  alpine tar czf /backup/awx-data.tar.gz -C /data .

docker run --rm \
  -v postgres-data:/data \
  -v "$PWD":/backup \
  alpine tar czf /backup/postgres-data.tar.gz -C /data .

docker run --rm \
  -v redis-data:/data \
  -v "$PWD":/backup \
  alpine tar czf /backup/redis-data.tar.gz -C /data .

docker run --rm \
  -v awx-logs:/data \
  -v "$PWD":/backup \
  alpine tar czf /backup/awx-logs.tar.gz -C /data .

docker run --rm \
  -v awx-projects:/data \
  -v "$PWD":/backup \
  alpine tar czf /backup/awx-projects.tar.gz -C /data .

# Backup compose files and environment
cp docker-compose.yml .
cp .env .

# Create backup manifest
cat > BACKUP_MANIFEST.txt <<EOF
AAX Backup Manifest
===================
Created: $(date)
Hostname: $(hostname)
Docker Version: $(docker --version)
Docker Compose Version: $(docker compose --version)

Included Volumes:
- awx-data
- postgres-data
- redis-data
- awx-logs
- awx-projects

Configuration Files:
- docker-compose.yml
- .env

Restore Instructions:
1. Stop running containers: docker compose down
2. Extract archives to volumes
3. Restart containers: docker compose up -d
EOF

# Restart containers
docker compose start

echo "Backup completed: $BACKUP_DIR/$BACKUP_NAME"
```

### Create tar archive for transfer

```bash
cd ~/aax-backups
tar czf aax-backup-$TIMESTAMP.tar.gz $BACKUP_NAME/
```

---

## PostgreSQL Backup

### Backup specific database

```bash
# Backup AWX database
docker compose exec postgres pg_dump -U awx awx | gzip > awx-database.sql.gz

# Backup Galaxy database
docker compose exec postgres pg_dump -U galaxy galaxy | gzip > galaxy-database.sql.gz

# Backup Pulp database
docker compose exec postgres pg_dump -U pulp pulp | gzip > pulp-database.sql.gz

# Backup EDA database
docker compose exec postgres pg_dump -U eda eda | gzip > eda-database.sql.gz
```

### Backup all databases

```bash
docker compose exec postgres pg_dumpall -U postgres | gzip > all-databases.sql.gz
```

### Backup with custom options

```bash
# Backup with verbose output and custom format
docker compose exec postgres pg_dump \
  -U awx \
  -d awx \
  -F custom \
  -v \
  -f /tmp/awx-backup.dump

# Copy from container
docker compose cp postgres:/tmp/awx-backup.dump ./awx-backup.dump
```

---

## Volume Backup

### Backup specific volume

```bash
# Backup AWX data volume
docker run --rm \
  -v awx-data:/source \
  -v "$PWD":/backup \
  alpine tar czf /backup/awx-data-$(date +%Y%m%d_%H%M%S).tar.gz -C /source .
```

### Backup to NFS or remote storage

```bash
# Mount remote storage
sudo mount -t nfs nfs-server:/export/backups /mnt/backups

# Backup to remote location
docker run --rm \
  -v awx-data:/source \
  -v /mnt/backups:/backup \
  alpine tar czf /backup/awx-data.tar.gz -C /source .

# Unmount when done
sudo umount /mnt/backups
```

---

## Restore from Backup

### Full restore from backup directory

```bash
#!/bin/bash
# Restore from backup

BACKUP_DIR="$1"
if [ -z "$BACKUP_DIR" ]; then
  echo "Usage: $0 <backup-directory>"
  exit 1
fi

# Verify backup exists
if [ ! -d "$BACKUP_DIR" ]; then
  echo "Backup directory not found: $BACKUP_DIR"
  exit 1
fi

# Stop containers
echo "Stopping containers..."
docker compose down

# Remove old volumes (WARNING: Data loss!)
echo "Removing old volumes..."
docker volume rm awx-data postgres-data redis-data awx-logs awx-projects

# Create new volumes
docker volume create awx-data
docker volume create postgres-data
docker volume create redis-data
docker volume create awx-logs
docker volume create awx-projects

# Restore volumes from backup
echo "Restoring volumes..."
docker run --rm \
  -v awx-data:/target \
  -v "$BACKUP_DIR":/backup \
  alpine tar xzf /backup/awx-data.tar.gz -C /target

docker run --rm \
  -v postgres-data:/target \
  -v "$BACKUP_DIR":/backup \
  alpine tar xzf /backup/postgres-data.tar.gz -C /target

docker run --rm \
  -v redis-data:/target \
  -v "$BACKUP_DIR":/backup \
  alpine tar xzf /backup/redis-data.tar.gz -C /target

docker run --rm \
  -v awx-logs:/target \
  -v "$BACKUP_DIR":/backup \
  alpine tar xzf /backup/awx-logs.tar.gz -C /target

docker run --rm \
  -v awx-projects:/target \
  -v "$BACKUP_DIR":/backup \
  alpine tar xzf /backup/awx-projects.tar.gz -C /target

# Restore configuration (optional)
if [ -f "$BACKUP_DIR/.env" ]; then
  cp "$BACKUP_DIR/.env" .env
  echo "Restored .env configuration"
fi

# Start containers
echo "Starting containers..."
docker compose up -d

# Wait for services
echo "Waiting for services to be healthy..."
sleep 30

# Verify
docker compose ps

echo "Restore completed!"
```

### Restore database only

```bash
# Restore AWX database
docker compose exec -T postgres psql -U awx awx < awx-database.sql

# Or from compressed backup
gunzip < awx-database.sql.gz | docker compose exec -T postgres psql -U awx awx

# Restore from custom format
docker compose cp awx-backup.dump postgres:/tmp/awx-backup.dump
docker compose exec postgres pg_restore \
  -U awx \
  -d awx \
  --no-owner \
  /tmp/awx-backup.dump
```

### Selective restore

```bash
# Restore only PostgreSQL volume
docker volume rm postgres-data
docker volume create postgres-data

docker run --rm \
  -v postgres-data:/target \
  -v "$PWD":/backup \
  alpine tar xzf /backup/postgres-data.tar.gz -C /target

# Restart database services
docker compose restart postgres
```

---

## Incremental Backups

### Daily incremental backup strategy

```bash
#!/bin/bash
# Daily incremental backup script

BACKUP_BASE="$HOME/aax-backups"
DAY=$(date +%A)
TIMESTAMP=$(date +%H%M%S)

# Create daily directory
mkdir -p "$BACKUP_BASE/$DAY"

# Backup only changed files (faster)
docker run --rm \
  -v awx-data:/data \
  -v "$BACKUP_BASE/$DAY":/backup \
  alpine tar czf /backup/awx-data-$TIMESTAMP.tar.gz \
  --newer-mtime-than /backup/awx-data-*.tar.gz \
  -C /data . 2>/dev/null || \
  tar czf /backup/awx-data-$TIMESTAMP.tar.gz -C /data .

# Run weekly full backup on Sunday
if [ "$DAY" = "Sunday" ]; then
  docker compose exec postgres pg_dumpall -U postgres | \
    gzip > "$BACKUP_BASE/$DAY/databases-$TIMESTAMP.sql.gz"
  echo "Full database backup created"
else
  echo "Incremental backup created"
fi

# Keep only last 7 days
find "$BACKUP_BASE" -name "awx-data-*.tar.gz" -mtime +7 -delete
```

### Automate with cron

```bash
# Add to crontab: crontab -e

# Daily backup at 2 AM
0 2 * * * /usr/local/bin/aax-backup.sh >> /var/log/aax-backup.log 2>&1

# Weekly full backup Sunday at 3 AM
0 3 * * 0 /usr/local/bin/aax-full-backup.sh >> /var/log/aax-backup.log 2>&1
```

---

## Cloud Backup

### AWS S3 backup

```bash
#!/bin/bash
# Backup to AWS S3

AWS_BUCKET="s3://my-aax-backups"
BACKUP_FILE="aax-backup-$(date +%Y%m%d_%H%M%S).tar.gz"

# Create tar archive
tar czf /tmp/$BACKUP_FILE \
  --exclude=.git \
  --exclude=docker-compose.override.yml \
  .

# Upload to S3
aws s3 cp /tmp/$BACKUP_FILE $AWS_BUCKET/$BACKUP_FILE \
  --sse AES256 \
  --storage-class GLACIER_IR

# Clean up
rm /tmp/$BACKUP_FILE

echo "Uploaded $BACKUP_FILE to $AWS_BUCKET"
```

### Azure Blob Storage backup

```bash
#!/bin/bash
# Backup to Azure Blob Storage

CONTAINER="aax-backups"
BACKUP_FILE="aax-backup-$(date +%Y%m%d_%H%M%S).tar.gz"

# Create tar archive
tar czf /tmp/$BACKUP_FILE \
  --exclude=.git \
  --exclude=docker-compose.override.yml \
  .

# Upload using az CLI
az storage blob upload \
  --account-name mystorageaccount \
  --container-name $CONTAINER \
  --name $BACKUP_FILE \
  --file /tmp/$BACKUP_FILE

# Clean up
rm /tmp/$BACKUP_FILE

echo "Uploaded $BACKUP_FILE to Azure"
```

### Google Cloud Storage backup

```bash
#!/bin/bash
# Backup to Google Cloud Storage

BUCKET="gs://aax-backups"
BACKUP_FILE="aax-backup-$(date +%Y%m%d_%H%M%S).tar.gz"

# Create tar archive
tar czf /tmp/$BACKUP_FILE \
  --exclude=.git \
  --exclude=docker-compose.override.yml \
  .

# Upload using gsutil
gsutil -m cp /tmp/$BACKUP_FILE $BUCKET/$BACKUP_FILE

# Clean up
rm /tmp/$BACKUP_FILE

echo "Uploaded $BACKUP_FILE to Google Cloud Storage"
```

---

## Backup Verification

### Verify backup integrity

```bash
# List backup contents
tar tzf awx-data.tar.gz | head -20

# Check file count
tar tzf awx-data.tar.gz | wc -l

# Verify compressed file
tar -tzf awx-data.tar.gz > /dev/null && echo "Archive is valid" || echo "Archive is corrupted"
```

### Calculate checksums

```bash
# SHA256 checksum
sha256sum awx-data.tar.gz > awx-data.tar.gz.sha256

# Verify checksum later
sha256sum -c awx-data.tar.gz.sha256
```

### Backup health check

```bash
#!/bin/bash
# Verify all backups exist and are valid

BACKUP_DIR="$1"
errors=0

for backup in awx-data.tar.gz postgres-data.tar.gz redis-data.tar.gz; do
  if [ -f "$BACKUP_DIR/$backup" ]; then
    if tar -tzf "$BACKUP_DIR/$backup" > /dev/null 2>&1; then
      size=$(du -h "$BACKUP_DIR/$backup" | cut -f1)
      echo "✓ $backup ($size)"
    else
      echo "✗ $backup - CORRUPTED"
      ((errors++))
    fi
  else
    echo "✗ $backup - MISSING"
    ((errors++))
  fi
done

if [ $errors -eq 0 ]; then
  echo "All backups verified successfully"
  exit 0
else
  echo "Found $errors backup issues"
  exit 1
fi
```

---

## Disaster Recovery

### Recover from complete data loss

```bash
# 1. Remove all containers and volumes
docker compose down -v

# 2. Restore from backup (see Restore section above)
./restore-backup.sh /backup/aax-backup-20240227_120000

# 3. Verify all services are running
docker compose ps

# 4. Check AWX is accessible
curl http://localhost:8080/api/v2/ping/

# 5. Restore any additional databases if needed
docker compose exec postgres psql -U awx awx < awx-database.sql
```

### Partial recovery - single service

```bash
# Recover only AWX database
docker volume rm postgres-data
docker volume create postgres-data

docker run --rm \
  -v postgres-data:/target \
  -v /backup:/backup \
  alpine tar xzf /backup/postgres-data.tar.gz -C /target

# Restart database
docker compose restart postgres
docker compose restart awx-web awx-task
```

### Point-in-time recovery

```bash
# 1. Restore full backup
./restore-backup.sh /backup/aax-backup-20240225_000000

# 2. Connect to database
docker compose exec postgres psql -U awx awx

# 3. List transaction timeline (if WAL archiving is configured)
SELECT * FROM pg_wal_lsn_diff(pg_current_wal_lsn(), '0/0');

# 4. Recovery can be done with recovery_target_time
# (Requires WAL archiving and recovery_target_time configuration)
```

---

## Backup Storage Best Practices

### 3-2-1 Backup Strategy

- **3** copies of your data
  - Original production data
  - Local backup
  - Off-site backup
- **2** different storage types
  - On-disk (fast recovery)
  - Cloud storage (reliable)
- **1** off-site location
  - Different geographic region
  - Protected from local disasters

### Implementation

```bash
#!/bin/bash
# 3-2-1 backup implementation

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="aax-backup-$TIMESTAMP"

# Create backup
mkdir -p ~/aax-backups/$BACKUP_NAME
cd ~/aax-backups/$BACKUP_NAME
./full-backup.sh

# Create archive
cd ~/aax-backups
tar czf $BACKUP_NAME.tar.gz $BACKUP_NAME/

# Copy 1: Local backup (kept for 30 days)
cp $BACKUP_NAME.tar.gz /mnt/local-backup/

# Copy 2: Off-site cloud backup (kept indefinitely)
aws s3 cp $BACKUP_NAME.tar.gz s3://aax-backups/$BACKUP_NAME.tar.gz

# Copy 3: Off-site archived backup (stored securely)
# Send to another organization's storage or professional backup service

echo "3-2-1 backup strategy completed:"
echo "1. Production: /var/lib/docker/volumes/"
echo "2. Local: /mnt/local-backup/$BACKUP_NAME.tar.gz"
echo "3. Cloud: s3://aax-backups/$BACKUP_NAME.tar.gz"
```

---

## Monitoring and Alerts

### Check backup age

```bash
#!/bin/bash
# Alert if backups are too old

BACKUP_DIR="$HOME/aax-backups"
MAX_AGE_HOURS=26
THRESHOLD_TIME=$(($(date +%s) - MAX_AGE_HOURS * 3600))

for backup in $BACKUP_DIR/aax-backup-*/postgres-data.tar.gz; do
  if [ -f "$backup" ]; then
    file_time=$(stat -c %Y "$backup")
    if [ $file_time -lt $THRESHOLD_TIME ]; then
      echo "WARNING: Backup is older than $MAX_AGE_HOURS hours: $backup"
      # Send alert (email, Slack, etc.)
    fi
  fi
done
```

### Backup size monitoring

```bash
#!/bin/bash
# Monitor backup size growth

BACKUP_DIR="$HOME/aax-backups"

echo "Backup sizes:"
du -sh $BACKUP_DIR/aax-backup-*/ | sort -h | tail -10

echo ""
echo "Size trend:"
for dir in $BACKUP_DIR/aax-backup-*/; do
  date=$(basename "$dir" | cut -d- -f3-4)
  size=$(du -sh "$dir" | cut -f1)
  echo "$date: $size"
done
```

---

## Troubleshooting

### Volume mount permission denied

```bash
# Run with proper permissions
docker run --rm \
  -v awx-data:/source \
  -v "$PWD":/backup \
  --user $(id -u):$(id -g) \
  alpine tar czf /backup/awx-data.tar.gz -C /source .
```

### Out of disk space during backup

```bash
# Stream backup directly to destination
docker run --rm \
  -v awx-data:/source \
  alpine tar czf - -C /source . | \
  ssh user@backup-server "cat > /backups/awx-data.tar.gz"

# Or use compression level
docker run --rm \
  -v awx-data:/source \
  alpine tar czf --gzip=9 - -C /source . | gzip -9 > awx-data.tar.gz
```

### Database locked during backup

```bash
# Force close connections
docker compose exec postgres psql -U postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'awx';"

# Then run backup
docker compose exec postgres pg_dump -U awx awx | gzip > awx-database.sql.gz
```

### Restore fails with permission errors

```bash
# Fix permissions after restore
docker volume inspect awx-data | grep Mountpoint
sudo chown -R 1000:1000 /var/lib/docker/volumes/awx-data/_data

# Or from within container
docker run --rm -v awx-data:/data alpine chown -R 1000:1000 /data
```

---

## See Also

- [docs/INDEX.md](INDEX.md) – Documentation index
- [FAQ.md](FAQ.md) – Frequently asked questions
- [HA-DEPLOYMENT.md](HA-DEPLOYMENT.md) – High availability setup
- [PostgreSQL Backup Documentation](https://www.postgresql.org/docs/current/backup.html)
- [Docker Volume Management](https://docs.docker.com/storage/volumes/)
