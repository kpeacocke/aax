#!/bin/sh
set -eu

backup_root=${AAX_BACKUP_ROOT:-/volume1/backups/aax}
project_name=${COMPOSE_PROJECT_NAME:-aax}
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_dir=${backup_root}/${timestamp}
quiesce=${AAX_BACKUP_QUIESCE:-true}
volumes="workspace ee_builds ee_definitions dev_workspace awx_postgres_data awx_redis_data awx_projects awx_rsyslog receptor_data receptor_hop_data receptor_execution_data hub_postgres_data hub_redis_data hub_pulp_storage hub_assets eda_postgres_data eda_redis_data eda_projects eda_logs"
running_services=$(docker compose ps --services --filter status=running)
restart_required=false

mkdir -p "${backup_dir}"
chmod 700 "${backup_dir}"

restore_running_services() {
  if [ "${restart_required}" = true ] && [ -n "${running_services}" ]; then
    # shellcheck disable=SC2086
    docker compose start ${running_services}
  fi
}
trap restore_running_services EXIT INT TERM

if [ "${quiesce}" = true ] && [ -n "${running_services}" ]; then
  docker compose stop
  restart_required=true
fi

for volume_key in ${volumes}; do
  volume_name=${project_name}_${volume_key}
  if ! docker volume inspect "${volume_name}" >/dev/null 2>&1; then
    echo "Skipping absent volume: ${volume_name}"
    continue
  fi
  docker run --rm -v "${volume_name}:/source:ro" -v "${backup_dir}:/backup" \
    alpine:3.22 tar -czf "/backup/${volume_key}.tar.gz" -C /source .
done

cp docker-compose.yml "${backup_dir}/"
if [ -f .env ]; then
  cp .env "${backup_dir}/environment.env"
  chmod 600 "${backup_dir}/environment.env"
fi
git rev-parse HEAD > "${backup_dir}/git-revision.txt" 2>/dev/null || true
(cd "${backup_dir}" && sha256sum ./*.tar.gz docker-compose.yml git-revision.txt > SHA256SUMS)
echo "AAX backup complete: ${backup_dir}"
