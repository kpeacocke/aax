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
until python /var/lib/awx/manage.py migrate --check 2>/dev/null; do
  sleep 5
done
echo "Migrations complete"

# Start AWX task dispatcher
echo "Starting AWX task dispatcher..."
exec python /var/lib/awx/manage.py run_dispatcher
