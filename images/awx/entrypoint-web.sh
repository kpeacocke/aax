#!/bin/bash
set -e

if [ "$#" -gt 0 ]; then
  exec "$@"
fi

# Wait for database
echo "Waiting for database..."
until PGPASSWORD=$DATABASE_PASSWORD psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_NAME" -c '\q' 2>/dev/null; do
  sleep 1
done

echo "Database is ready"

# Run migrations
echo "Running database migrations..."
awx-manage migrate --noinput

# Create admin user if it doesn't exist
echo "Checking for admin user..."
awx-manage shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='${AWX_ADMIN_USER:-admin}').exists():
    User.objects.create_superuser('${AWX_ADMIN_USER:-admin}', '', '${AWX_ADMIN_PASSWORD:-password}')
    print("Admin user created")
else:
    print("Admin user already exists")
EOF

# Start AWX web service
echo "Starting AWX web service..."
exec awx-manage runserver 0.0.0.0:8052
