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
   template; create its token in EDA under `users/me/awx-tokens`. Do not grant
   this account broader AWX permissions.
4. Register the published decision environment
   `ghcr.io/kpeacocke/aax-eda-decision-environment:<immutable-bundle-tag>`.
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
