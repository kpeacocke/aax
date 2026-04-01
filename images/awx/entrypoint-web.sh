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
python /var/lib/awx/manage.py migrate --noinput

# Create admin user if it doesn't exist
echo "Checking for admin user..."
python /var/lib/awx/manage.py shell <<'EOF'
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get("AWX_ADMIN_USER", "admin")
password = os.environ["AWX_ADMIN_PASSWORD"]

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, '', password)
    print("Admin user created")
else:
    print("Admin user already exists")
EOF

# Start AWX web service
echo "Starting AWX web service..."
exec python /var/lib/awx/manage.py runserver --insecure 0.0.0.0:8052
