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

### Maintained downstream security patches

AAX maintains source patches where an upstream dependency constraint prevents a
security update. These are downstream builds, not unmodified upstream releases:

- pip is rebuilt using its official vendoring tooling, with updated private
  msgpack/urllib3 dependencies. Its deprecated `pkg_resources` backend and
  vendored setuptools implementation are removed, not hidden from scanners.
  This AAX-internal pip supports Python 3.12 and newer and only the
  `importlib.metadata` backend. Explicitly selecting the removed backend fails.
- Django Ansible Base is rebuilt from each service's actual installed Git
  revision. Its OAuth application serializer explicitly requires an organization,
  preserving the pre-3.16 behavior while allowing REST framework 3.17.2.
  The build runs the upstream OAuth provider tests before producing a wheel.
- Hub rebuilds Galaxy NG, pulpcore and pulp-glue source wheels to allow the
  patched REST framework, yarl, requests and multidict versions.
- EDA rebuilds the source shipped in its pinned upstream image to support the
  patched cryptography, ECDSA, setuptools and REST framework dependencies.
  Its AES-256 implementation initializes the cipher required by cryptography 50
  while preserving existing ciphertext; build-time tests cover legacy values,
  tampering, expiry and invalid keys. AWX and EDA also check actual WebSocket
  imports after upgrading Autobahn.
- The rulebook integration is rebuilt against the public Drools 10.2.0 engine
  and Jackson 2.21.7 BOM, with its upstream Maven tests enabled.
- Receptor is rebuilt with patched Go dependencies. The execution image uses
  that same binary and bakes in runner and collections rather than downloading
  them at service startup.

Source patches and build inputs are retained with the bundle reports. Python
layers must pass `pip check`; source-patch failures, failed upstream tests and
fixable HIGH/CRITICAL findings block publication. No dependency metadata is
rewritten in place and no vulnerability ignores or dismissals are added.
Upstream changes may require reviewed patch refreshes before the next bundle
can publish. Full-stack compatibility validation is still required before
production deployment; the image scan gate alone is not production sign-off.

### CentOS Stream and native package coverage

Trivy does not cover CentOS Stream OS packages. The bundle also uses
checksum-pinned Grype to cover RPMs and Go code embedded in native tools.
Missing OS coverage fails the gate unless the supplemental report identifies
the exact same image ID; a clean language-only scan is not OS clearance.

The maintained source layer keeps the original distribution identity. It
verifies both SHA-256 digests and vendor signatures on pinned EL9 source RPMs,
then rebuilds their actual patched sources on CentOS Stream. AAX packages have
their own vendor/release identifiers; installed RPM metadata is not rewritten.
The system setuptools compatibility package receives a real Unicode exclusion
backport, including a regression that inspects the resulting source archive.

Native Go tools retain their pinned EL9 source versions and are compiled with Go
1.27.3 plus pinned `golang-fips` patches, rather than disabling the existing
strict-FIPS capability. Compiler crypto and strict-mode tests run during the
build. This does not make AAX a certified FIPS product.
The git-lfs, Podman and skopeo builds regenerate their vendored dependencies
using reviewed security pins and module-aware compilation, so embedded dependency
inventories remain visible to scanners. The full selected module graph is downloaded
before vendoring to populate transitive checksums. New vendored sources, module checksums
and licenses are included in the corresponding source RPM, not just downloaded
and discarded. An existing newer dependency fails the build rather than being
downgraded.

Runtime images upgrade only subpackages already installed, verify the resulting
RPM versions and run the dependency check. The build retains corresponding
source RPMs and build logs alongside its recipes. If vendor updates overtake
the pinned AAX packages, publication stops instead of downgrading; maintainers
must review and refresh `images/rpm-security/sources.json`, rebuild, rescan and
repeat compatibility validation. This source maintenance is deliberately more
expensive than ordinary package updates.

Dependabot covers the downstream Docker directories and standard
`requirements-*.txt` manifests, including pip's vendored requirements. Native
source revisions, RPM recipes and dependency JSON pins still require reviewed
maintenance; they are not automatically certified by a dependency PR.

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

### Hub persistent storage and encryption key

The devel override explicitly uses filesystem artifact storage at
`/var/lib/pulp/media`, shared by every Hub role. It does not require an S3 bucket.
All Hub roles also share `hub_pulp_certs`. Before migrations or service startup,
the image initializes a private database-field encryption key there if absent,
with locking and atomic creation so concurrent roles cannot create different
keys. An invalid existing key stops startup rather than being replaced.

Back up `hub_pulp_certs` together with the Hub database and artifact storage.
Never delete or regenerate the key when retaining an existing database: encrypted
fields require their original key. If migrating an existing deployment, restore
its original `database_fields.symmetric.key` before starting services. This
filesystem configuration does not migrate artifacts out of an existing S3 bucket;
copy or migrate existing content separately before changing storage backends.

## 4. Deploy

In Portainer, create or update the Git-backed stack and redeploy. Portainer pulls
the exact image tag selected above. To advance the baseline, run the workflow
again and change only `DEVEL_IMAGE_TAG` and the matching AWX/Receptor variables.

The local helper `scripts/deploy-devel.sh` remains for Docker Desktop development;
it defaults to local `aax/*:devel` images and is not required by Portainer.
