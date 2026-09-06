#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ "${AAX_CONFIRM_RESTORE:-}" != "RESTORE" ]; then
  echo "Usage: AAX_CONFIRM_RESTORE=RESTORE $0 /absolute/path/to/aax-backup"
  exit 2
fi

backup_dir=$1
project_name=${COMPOSE_PROJECT_NAME:-aax}
volumes="workspace ee_builds ee_definitions dev_workspace awx_postgres_data awx_redis_data awx_projects awx_rsyslog receptor_data receptor_hop_data receptor_execution_data hub_postgres_data hub_redis_data hub_pulp_storage hub_assets eda_postgres_data eda_redis_data eda_projects eda_logs"

case ${backup_dir} in /*) ;; *) echo "Backup path must be absolute"; exit 2 ;; esac
test -d "${backup_dir}"
(cd "${backup_dir}" && sha256sum -c SHA256SUMS)

if [ -n "$(docker compose ps --services --filter status=running)" ]; then
  echo "Refusing restore while AAX services are running. Stop the stack first."
  exit 1
fi

for volume_key in ${volumes}; do
  archive=${backup_dir}/${volume_key}.tar.gz
  [ -f "${archive}" ] || continue
  volume_name=${project_name}_${volume_key}
  docker volume create "${volume_name}" >/dev/null
  docker run --rm -v "${volume_name}:/target" -v "${backup_dir}:/backup:ro" \
    alpine:3.22 sh -c "find /target -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + && tar -xzf /backup/${volume_key}.tar.gz -C /target"
done

echo "Restore complete. Review environment.env, then redeploy deliberately."
