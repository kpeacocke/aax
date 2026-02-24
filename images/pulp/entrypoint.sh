#!/bin/bash
set -e

# Wait for PostgreSQL
until PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c '\q' 2>/dev/null; do
  echo "Waiting for PostgreSQL..."
  sleep 2
done

echo "PostgreSQL is ready"

# Wait for Redis
until redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ping 2>/dev/null | grep -q PONG; do
  echo "Waiting for Redis..."
  sleep 2
done

echo "Redis is ready"

# Run migrations on first startup (only for API service)
if [ "$1" = "pulpcore-api" ]; then
  echo "Running database migrations..."
  pulpcore-manager migrate --no-input

  echo "Collecting static files..."
  pulpcore-manager collectstatic --no-input --clear

  echo "Creating default access policy..."
  pulpcore-manager create-access-policy || true
fi

# Start the requested service
case "$1" in
  pulpcore-api)
    echo "Starting Pulp API server..."
    exec gunicorn pulpcore.app.wsgi:application \
      --bind '0.0.0.0:24817' \
      --workers 4 \
      --timeout 90 \
      --access-logfile - \
      --error-logfile -
    ;;
  pulpcore-content)
    echo "Starting Pulp content server..."
    exec gunicorn pulpcore.content:server \
      --bind '0.0.0.0:24816' \
      --workers 2 \
      --timeout 90 \
      --access-logfile - \
      --error-logfile -
    ;;
  pulpcore-worker)
    echo "Starting Pulp worker..."
    exec pulpcore-worker
    ;;
  *)
    echo "Unknown service: $1"
    exec "$@"
    ;;
esac
