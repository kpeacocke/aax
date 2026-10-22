# Portainer Devel Deployment

GitHub Actions publishes the upstream devel bundle to GHCR. Portainer should pull
an immutable commit tag rather than build source on the deployment host.

## 1. Run the workflow

Run **Publish upstream devel bundle** from GitHub Actions. The workflow publishes
these images under `ghcr.io/<owner>`:

- `aax-awx`
- `aax-awx-ee`
- `aax-receptor`
- `aax-ansible-rulebook`
- `aax-galaxy-ng`
- `aax-pulp`
- `aax-gateway`
- `aax-eda-controller`

New immutable tags are `devel-<full-commit-sha>-<run-id>-<attempt>`. Each daily
build gets a distinct tag even when only upstream sources have changed. Older
`devel-<full-commit-sha>` tags remain usable. The mutable `devel` tag is also
published when the workflow input allows it, after all immutable images push.

Publication is blocked by fixable HIGH/CRITICAL vulnerabilities in the exact
built images. All severities, including vulnerabilities without patches, remain
in the reports; passing this gate does not mean vulnerability-free. The workflow
artifact contains upstream Git revisions, pinned EDA/UI build inputs, SBOMs,
security reports, and registry manifests with image digests. Use the tag printed
in the successful workflow summary rather than constructing one from a commit.
This scan gate does not replace full-stack runtime/compatibility validation.

## 2. Configure Portainer registry access

For a private GHCR package, create a Portainer registry credential for
`ghcr.io` using a GitHub token with package read access. Do not put the token in
the Compose file or Git.

## 3. Set the stack environment

Use the repository stack with `docker-compose.yml` and
`docker-compose.devel.yml`. In Portainer, select the base Compose file and add
the devel file as an additional Compose file/override. If the Portainer version
does not expose additional Compose files for Git stacks, use the same two files
with the Portainer API or deploy a generated combined Compose file from CI.
Set these variables in the Portainer stack:

```text
DEVEL_IMAGE_PREFIX=ghcr.io/<owner>
DEVEL_IMAGE_TAG=devel-<full-commit-sha>-<run-id>-<attempt>
AWX_IMAGE_REPOSITORY=ghcr.io/<owner>/aax-awx
AWX_VERSION=devel-<full-commit-sha>-<run-id>-<attempt>
AWX_EE_IMAGE_REPOSITORY=ghcr.io/<owner>/aax-awx-ee
AWX_EE_VERSION=devel-<full-commit-sha>-<run-id>-<attempt>
RECEPTOR_IMAGE_REPOSITORY=ghcr.io/<owner>/aax-receptor
RECEPTOR_VERSION=devel-<full-commit-sha>-<run-id>-<attempt>
COMPOSE_PROFILES=controller,hub,eda
```

Keep the required database passwords, AWX/Galaxy secrets, hostnames, and trusted
origins in Portainer's environment settings. Keep `AAX_ALLOW_PLACEHOLDER_SECRETS`
false.

## 4. Deploy

In Portainer, create or update the Git-backed stack and redeploy. Portainer pulls
the exact image tag selected above. To advance the baseline, run the workflow
again and change only `DEVEL_IMAGE_TAG` and the matching AWX/Receptor variables.

The local helper `scripts/deploy-devel.sh` remains for Docker Desktop development;
it defaults to local `aax/*:devel` images and is not required by Portainer.
