#!/bin/bash
set -euo pipefail

case "${1:-api}" in
  api)
    : "${EDA_SECRET_KEY:?EDA_SECRET_KEY is required}"
    : "${EDA_DB_PASSWORD:?EDA_DB_PASSWORD is required}"
    aap-eda-manage migrate --noinput
    ANSIBLE_REVERSE_RESOURCE_SYNC=false aap-eda-manage create_initial_data
    exec gunicorn -b 0.0.0.0:5000 -w 2 aap_eda.wsgi --access-logfile -
    ;;
  scheduler) exec aap-eda-manage scheduler ;;
  worker) exec aap-eda-manage dispatcherd --worker-class DefaultWorker ;;
  *) exec "$@" ;;
esac
