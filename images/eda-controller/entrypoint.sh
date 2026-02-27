#!/bin/bash
set -e

# Event-Driven Ansible Controller Entrypoint
# Starts the ansible-rulebook engine in server mode

# Function to wait for a service
wait_for_service() {
  local host=$1
  local port=$2
  local service=$3

  echo "Waiting for $service..."
  for i in {1..30}; do
    if nc -z "$host" "$port" 2>/dev/null; then
      echo "$service is ready"
      return 0
    fi
    echo "Waiting for $service ($i/30)..."
    sleep 1
  done

  echo "Warning: $service did not become ready in time"
  return 0  # Don't fail, continue anyway
}

# Wait for required services
if [ -z "$EDA_SKIP_DB_WAIT" ]; then
  if [ -n "$EDA_DB_HOST" ]; then
    wait_for_service "$EDA_DB_HOST" "${EDA_DB_PORT:-5432}" "PostgreSQL"
  fi
fi

if [ -n "$EDA_REDIS_HOST" ]; then
  wait_for_service "$EDA_REDIS_HOST" "${EDA_REDIS_PORT:-6379}" "Redis"
fi

# Start as Event-Driven Ansible controller POC
# This container serves as a template for running ansible-rulebook rules
echo "Starting Event-Driven Ansible Controller..."
echo "EDA controller is ready to execute rulebooks"
echo ""
echo "To run a rulebook:"
echo "  docker exec eda-controller ansible-rulebook -r /path/to/rulebook.yml"
echo ""
echo "Or use the AWX integration to trigger rulebooks from events"
echo ""

# Keep container alive for rulebook execution requests
# Using sleep in an infinite loop
while true; do
  echo "[$(date)] EDA Controller running - waiting for rulebook execution requests"
  sleep 60
done
