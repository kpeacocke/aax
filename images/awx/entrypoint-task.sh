#!/bin/bash
set -e

# Wait for database
echo "Waiting for database..."
until PGPASSWORD=$DATABASE_PASSWORD psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_NAME" -c '\q' 2>/dev/null; do
  sleep 1
done

echo "Database is ready"

# Wait for migrations to complete (web container handles this)
echo "Waiting for migrations..."
sleep 10

# Start AWX task dispatcher
echo "Starting AWX task dispatcher..."
exec awx-manage run_dispatcher
