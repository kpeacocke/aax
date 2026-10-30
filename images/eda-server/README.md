# EDA controller runtime

This image wraps the digest-pinned official `ansible/eda-server` image. It runs
schema migrations, creates upstream initial data, and serves the real controller
API on port 5000. It does not emulate a controller with a health-only HTTP server.

The regular devel bundle publisher also builds this image, so its
`devel-<commit>` tag works with the overlay defaults. For a targeted repair, the
devel overlay accepts `DEVEL_EDA_IMAGE_TAG=runtime-<commit>` while retaining
`DEVEL_IMAGE_TAG` for the other bundle images. The stable-image pipeline is
unchanged; this runtime is selected by the devel overlay. The dedicated EDA workflow
tests migrations, authenticated API boundaries, and restart before publishing.

The API readiness endpoint is `/_healthz`. Background project work uses the
`eda-worker` service. Activation execution uses a separate
`eda-activation-worker` (`ActivationWorker`) and a privileged, network-isolated
Podman API service. The Podman service is the only EDA component granted
privileged access: it must create nested containers and namespaces. Its TCP API
is not published on the host and is reachable only from the activation worker
over `eda-podman-network`. It uses
the `vfs` storage driver for compatibility with nested container storage on
Synology; the separate `eda_podman_storage` volume preserves pulled images and
containers across redeploys.

The `eda-ws` service runs the pinned image's ASGI application with Daphne. The
configured public WebSocket base URL is
`wss://awx.ambitiouscake.com/eda/ws`; EDA appends its own
`/api/eda/ws/ansible-rulebook` path. The gateway routes that generated path to
Daphne and the corresponding token-refresh URL to the controller. Both
`EDA_WEBSOCKET_SSL_VERIFY` and `EDA_CONTROLLER_SSL_VERIFY` remain enabled.

Set `EDA_CONTROLLER_URL` to an HTTPS AWX URL resolvable from activation
containers, and keep `EDA_CONTROLLER_SSL_VERIFY=true`. Nested Podman containers
inherit the configured `EDA_PODMAN_DNS` resolver so they can resolve GitHub,
the image registry, AWX, and the public callback endpoint.

Existing database credentials are retained. `EDA_SECRET_KEY` defaults to the
existing `SECRET_KEY` when unset; preserve the chosen value across deployments.

No administrator password is created or reset automatically. Use the upstream
`aap-eda-manage createsuperuser` command interactively through an authorized
administrator session for the initial account. Do not place that password or
AWX tokens in Compose, `.env.example`, or Git.

## Bootstrap and activation setup

1. Start or redeploy the `eda` profile without removing named volumes. The EDA
   PostgreSQL, Redis, project, log, and Podman container-storage volumes are
   persistent.
2. Create the first administrator interactively:

   ```sh
   docker compose --profile eda exec eda-controller aap-eda-manage createsuperuser
   ```

3. Sign in to EDA and create or confirm the organization. In AWX, use a
   dedicated service user with **Execute only** permission on the intended job
   template. Create a `write`-scope personal token through AWX's
   `/api/v2/tokens/` endpoint, then register that token in EDA under
   `users/me/awx-tokens`. The scope permits launching jobs but cannot expand
   the service user's template permissions. Do not grant this account broader
   AWX permissions.
4. Register the published decision environment
   `ghcr.io/kpeacocke/aax-eda-decision-environment:<immutable-bundle-tag>`.
   Publication patches its application-user Python environment and replaces its
   bundled Drools JAR with the maintained Jackson-patched build. Unused desktop
   indexer/JavaScript-engine RPMs and pip build caches are removed. The final
   patched image, not just its pinned upstream base, must pass the bundle scans
   and nested Podman execution test before deployment.
   This image is based on the digest-pinned upstream ansible-rulebook image,
   includes Python 3.12 and `ansible.eda` 2.13.0, and is intentionally generic.
   The RustberryPi/Hailo event-source collection is deferred until that project
   is updated.
5. Add the Git project and rulebook, then create an activation. Confirm its
   status and logs in EDA. A harmless AWX template is suitable for testing
   `run_job_template`.

Before enabling a real project, verify from a Podman activation container that
the configured DNS resolver can reach `https://api.github.com`,
`https://awx.ambitiouscake.com`, and the registry used by the decision
environment. Do not publish the Podman API port or disable TLS verification.

The Compose `eda` profile now supplies the execution backend and WebSocket
service, but successful EDA API health does not prove that a project can
activate. A first-run activation still requires the administrator,
organization, AWX token, decision environment, and project setup described
above.

For Portainer with a separate Docker host filesystem, set `AAX_AWX_CACHE_FILE`
to an existing absolute host path containing the repository's `compat/awx-cache.py`.
The default relative path is appropriate for ordinary local Compose.

Set `EDA_CSRF_TRUSTED_ORIGINS` to a JSON list of the exact public HTTPS origins
used for EDA session authentication (default: `["https://awx.ambitiouscake.com"]`).
The reverse proxy terminates TLS before forwarding HTTP to EDA, so the public
origin must be explicitly trusted for session-authenticated API writes. Keep
CSRF checks enabled; do not use a wildcard or trust arbitrary origins.

`EDA_RULEBOOK_READINESS_TIMEOUT_SECONDS` retains upstream's 60-second default.
On slow legacy hosts, JVM startup and WebSocket callback processing can exceed
that window even when a rulebook successfully launches an AWX job. After
confirming callback reachability and inspecting activation logs, a bounded
300-second window is appropriate for the approved Synology profile. This does
not disable readiness checks or TLS verification; an unresponsive activation
still fails after the configured interval.

## Standalone AWX bearer tokens

Current upstream AWX no longer includes its old personal-token implementation.
The maintained AWX bundle enables the upstream django-ansible-base OAuth2
provider when `AAX_AWX_OAUTH2_ENABLED=true`, as configured for both AWX services
in Compose. Normal migrations create its separate token tables. Existing user,
project and job data is retained. Scope permission checks apply even to AWX
views that override their default permission classes: a `read` token cannot
launch jobs or create users, including when its owner is an administrator.

This enables bearer-token integration, not shared AWX/EDA passwords or SSO.
An explicit source-bound adaptation avoids loading DAB's optional external
authentication models when that application is absent; standalone local users
have no DAB external-provider association. When that application is installed,
the original external-account restriction remains. Platform deployments with
`RESOURCE_SERVER__URL` configured still enforce upstream JWT-only authentication.

Fresh project/log volumes inherit ownership for EDA's unprivileged UID 1001
from the image. Existing externally provisioned volumes must already be writable
by that UID; do not grant the workers runtime root privileges to repair storage.

### Upgrading a legacy AWX OAuth migration history

An upgraded AWX database can retain `oauth2_provider.0001_initial` while the
newly enabled `dab_oauth2_provider.0001_initial` dependency is absent. Ordinary
`migrate` then reports `InconsistentMigrationHistory`; fresh databases do not
exercise this case. Back up the database, stop AWX web, and confirm no jobs are
active before proceeding. Keep the updated task service running with OAuth
enabled. Do not fake migrations or delete the legacy migration records.

For this exact case, the following guarded repair applies the real initial
migration using its dependency state, then runs the ordinary migration command.
It refuses an unexpected plan, existing DAB tables or changed domain counts.
Validate it against an isolated copy of the legacy database first. On Alexandria
this passed with unchanged users, jobs, projects, inventories and templates;
historical job-event partitions were excluded only from the isolated test copy,
not the production backup or production migration.

Use the deployment's database name and trusted origin. The explicit JSON origin
also avoids passing a legacy CSV value to AWX's settings loader:

```sh
docker compose --profile controller stop awx-web &&
if docker compose --profile controller exec -T \
  -e 'AWX_CSRF_TRUSTED_ORIGINS=["https://awx.ambitiouscake.com"]' \
  awx-task awx-manage shell <<'PY'
from django.apps import apps
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from awx.main.models import User, Job, Project, Inventory, JobTemplate, UnifiedJob

assert connection.settings_dict["NAME"] == "awx", "Unexpected database"
assert not UnifiedJob.objects.filter(status__in=["pending", "waiting", "running"]).exists()
models = (User, Job, Project, Inventory, JobTemplate)
before = {model.__name__: model.objects.count() for model in models}
executor = MigrationExecutor(connection)
target = ("dab_oauth2_provider", "0001_initial")
plan = executor.migration_plan([target])
assert [(m.app_label, m.name, backwards) for m, backwards in plan] == [
    (*target, False)
], "Unexpected migration plan"
assert ("oauth2_provider", "0001_initial") in executor.loader.applied_migrations
tables = {m._meta.db_table for m in apps.get_app_config(target[0]).get_models()}
assert len(tables) == 4 and not tables.intersection(connection.introspection.table_names())
assert [type(op).__name__ for op in plan[0][0].operations] == ["CreateModel"] * 4 + ["AddField"]
state = executor.loader.project_state(nodes=[target], at_end=False)
executor.apply_migration(state, plan[0][0], fake=False, fake_initial=False)
MigrationExecutor(connection).loader.check_consistent_history(connection)
call_command("migrate", interactive=False)
assert before == {model.__name__: model.objects.count() for model in models}
executor = MigrationExecutor(connection)
executor.loader.check_consistent_history(connection)
assert not executor.migration_plan(executor.loader.graph.leaf_nodes())
print("Legacy OAuth upgrade passed; domain counts unchanged")
PY
then
  docker compose --profile controller start awx-web
else
  printf '%s\n' 'OAuth repair failed; leave awx-web stopped and investigate.' >&2
  false
fi
```

The dependency-only state is necessary: rendering the full legacy state before
creating the DAB models also fails on the toolkit's swapped-model references.
After a successful repair, ordinary startup migrations work again; do not rerun
this one-time command on an already migrated database.

## Legacy Synology execution compatibility

The activation worker is already a Compose container. Rulebook activations are
separate containers created through the private Podman service; all of them
still share the NAS kernel. On Alexandria's Linux 4.4.302, the default netavark
network fails with `Protocol not available`, and the default nested seccomp
filter fails with `prctl: Invalid argument`.

Normal Linux hosts must retain the default `EDA_PODMAN_EXTRA_ARGS="@json {}"`.
Only after explicit operator approval, a legacy Synology deployment can test:

```dotenv
EDA_PODMAN_EXTRA_ARGS='@json {"network_mode":"host","cap_drop":["ALL"],"no_new_privileges":true,"seccomp_profile_path":"unconfined"}'
```

Here `host` means the **Podman service container's network namespace**, not the
NAS host network. The outer Podman service must remain on its private Compose
network with no published ports and no Docker socket mount. The worker remains
unprivileged with `cap_drop: [ALL]` and `no-new-privileges`. Nested activations
also drop every capability and retain `no-new-privileges`.

This mode removes nested network separation and syscall filtering. Activations
can reach the private Podman API from that shared namespace, so only trusted,
reviewed rulebooks and decision images are suitable. Do not silently select
this mode on kernel detection, or describe it as equivalent to normal isolation.
Prefer a supported modern execution host when untrusted rules must run.

## Controller-driven acceptance

The Git project must contain `extensions/eda/rulebooks` or `rulebooks`;
`tests/fixtures` alone is not discovered by EDA project import. This repository
provides a persistent tick/debug canary and a separate one-shot AWX readiness
rulebook in `extensions/eda/rulebooks`.

Use `scripts/test-eda-activation.py` with the exact scanned decision-image
digest. It drives the real authenticated HTTP API, imports a pinned Git ref,
creates an activation, and requires a fresh event marker in persisted EDA logs.
Run `--phase prepare` followed by `--phase check` with the same state file.
Repeat `check` after worker restart and stack redeploy to require new logs,
not an old successful status. Each check first watermarks all persisted instance
logs, follows replacement instances, and requires a later marker while the
current instance is still Running with the recorded Git revision. Logs produced
between an earlier successful check and shutdown cannot satisfy recovery.
Keep the state file in a persistent operator-owned
location. `--phase disable` disables only the activation recorded in that file.

For remote HTTPS use, supply `EDA_TEST_USERNAME` and `EDA_TEST_PASSWORD` through
the authorized operator environment, never command-line arguments. Inside the
controller, an administrator with container-console access can instead use
`--local-user <existing-admin>` against the loopback API. This creates a
temporary authenticated session, deletes it on exit, and does not reset or
read the user's password. It is not a shared AWX/EDA login implementation.

AWX action acceptance additionally requires `--phase launch`,
`--awx-token-id` and `--awx-organization`. Use a dedicated test identity scoped
to template 58, not the later Hailo identity restricted to template 66.
Correlate the rulebook's `aax_eda_acceptance_marker` extra variable with a
successful AWX job and its service-user attribution. Disable this one-shot
activation before recovery tests so it cannot launch another job on restart.

The RustberryPi/Hailo collection remains externally blocked until RustberryPi
publishes a standalone, versioned collection and compatible Python dependencies.
Do not package uncommitted RustberryPi sources or claim Hailo readiness based on
the generic acceptance rulebooks.
