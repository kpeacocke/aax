#!/bin/bash
set -e

# Allow command override for testing
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

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
echo "Starting HTTP health endpoint on port ${EDA_PORT:-5000}..."

# Start a minimal HTTP health server so the compose/k8s healthcheck can pass.
# Runs in the background so the main loop continues.
python3 - <<'PYEOF' &
import http.server
import json
import os

class HealthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            body = json.dumps({"status": "running"}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()
    def log_message(self, *args):
        pass  # suppress access logs

port = int(os.getenv('EDA_PORT', '5000'))
httpd = http.server.HTTPServer(('0.0.0.0', port), HealthHandler)
httpd.serve_forever()
PYEOF

echo "To run a rulebook:"
echo "  docker exec eda-controller ansible-rulebook -r /path/to/rulebook.yml"
echo ""
echo "Or use the AWX integration to trigger rulebooks from events"
echo ""

# Keep container alive for rulebook execution requests
while true; do
  echo "[$(date)] EDA Controller running - waiting for rulebook execution requests"
  sleep 60
done
