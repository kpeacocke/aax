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
`eda-worker` service; scheduled work uses `eda-scheduler`. Existing database
credentials are retained. `EDA_SECRET_KEY` defaults to the existing `SECRET_KEY`
when unset; preserve the chosen value across deployments.

No administrator password is created or reset automatically. Use the upstream
`aap-eda-manage createsuperuser` command through an authorized administrator
session for the initial account. Standalone authentication remains enabled;
TLS verification is not disabled.

Rulebook activation additionally needs an execution backend and its websocket
service, such as the upstream Podman or Kubernetes deployment. This repair does
not grant privileged container access, configure that backend, or claim to
verify rulebook execution. Do not treat HTTP health as an activation test.

For Portainer with a separate Docker host filesystem, set `AAX_AWX_CACHE_FILE`
to an existing absolute host path containing the repository's `compat/awx-cache.py`.
The default relative path is appropriate for ordinary local Compose.
