# Backup and restore

AAX persists data in separate Compose volumes for AWX, Hub/Pulp, EDA,
Receptor, projects, logs, and developer tooling. The checked-in scripts are the
canonical backup contract; do not use older examples referring to `awx-data`,
`postgres-data`, or a generic `postgres` service.

## Backup destination

The default destination is `/volume1/backups/aax`, suitable for the Synology
host. Override it when necessary:

```bash
AAX_BACKUP_ROOT=/volume1/backups/aax ./scripts/backup.sh
```

The script records which services were running, stops them long enough to make
consistent database-volume copies, archives every existing named volume, saves
the Compose file and Git revision, writes SHA-256 checksums, and returns only
the previously running services to service. A copy of `.env`, when present, is
included with mode `0600`.

Set `AAX_BACKUP_QUIESCE=false` only for non-database test data. A live tar copy
of a PostgreSQL volume is not a valid database backup.

The backup contains credentials and must remain access-controlled. Mirror the
resulting directory away from the NAS.

## Restore test

Restores are deliberately gated and never start the application:

```bash
docker compose down
AAX_CONFIRM_RESTORE=RESTORE ./scripts/restore.sh \
  /volume1/backups/aax/20260907T000000Z
```

The restore verifies checksums, refuses to run while AAX services are active,
restores only archives present in the selected backup, and leaves the stack
stopped for inspection. Review `environment.env`, restore the required
Portainer variables, and then deploy the desired profiles.

Test a restore after every material database or image-version change. A backup
without a demonstrated restore is not considered healthy.
