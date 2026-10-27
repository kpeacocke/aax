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
- `aax-eda-podman`
- `aax-eda-decision-environment`

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

For a source-pinned remediation retry, supply `upstream_revisions` as a JSON
object mapping `awx`, `awx-ee`, `receptor`, `ansible-rulebook` and `galaxy-ng`
to full Git commit hashes from the previous artifact's `sources.json`.
The workflow fetches and verifies those exact revisions instead of advancing
upstream branches. Leaving the input empty preserves daily upstream tracking.
This freezes those source repositories, not external package repositories or
mutable base-image tags.

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
  preserving the pre-3.16 behavior while allowing REST framework 3.18.2.
  The build runs the upstream OAuth provider tests before producing a wheel.
- Hub rebuilds Galaxy NG, pulpcore and pulp-glue source wheels to allow the
  patched REST framework, yarl, requests and multidict versions. Pulpcore's
  REST framework cap is widened alongside Galaxy NG's. Changed source wheels
  carry incremented AAX versions so pip cannot retain an older same-version
  wheel with obsolete dependency constraints.
- EDA rebuilds the source shipped in its pinned upstream image to support the
  patched cryptography, ECDSA, setuptools and REST framework dependencies.
  Its AES-256 implementation initializes the cipher required by cryptography 50
  while preserving existing ciphertext; build-time tests cover legacy values,
  tampering, expiry and invalid keys. AWX and EDA also check actual WebSocket
  imports after upgrading Autobahn.
- AWX's system virtualenv/filelock packages are maintained separately from its
  application virtualenv; EDA's user-site tooling receives its own updates.
- AWX and EDA pin Twisted 26.10.0rc1 because it is the currently published
  security-fixed release; no patched stable release is available. This
  prerelease choice requires compatibility validation before production use.
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

Native Go tools use signed EL9 source RPM recipes and are compiled with Go
1.27.3 plus pinned `golang-fips` patches, rather than disabling the existing
strict-FIPS capability. Podman source is pinned to upstream 5.8.8 at an exact
commit and its checked compatibility backport replaces retired Docker
container-spec APIs with the maintained Moby API, removing the vulnerable
legacy Docker module from Podman's source and vendor graph. Skopeo remains on
its signed distribution source. Compiler crypto and strict-mode tests run
during the build. This does not make AAX a certified FIPS product.
The git-lfs, Podman and skopeo builds regenerate their vendored dependencies
using reviewed security pins and module-aware compilation, so embedded dependency
inventories remain visible to scanners. After applying the pins, the module graph
is tidied and downloaded before vendoring to resolve indirect requirements and
populate transitive checksums. New vendored sources, module checksums
and licenses are included in the corresponding source RPM, not just downloaded
and discarded. An existing newer dependency fails the build rather than being
downgraded.
Podman's legacy EL9 recipe uses module-relative command targets and its v5 module
path for embedded build metadata; the upstream source archive URL is unchanged.
The setuptools backport is applied with RPM's zero-fuzz patch policy and tested
against the downstream source, including its existing vendor patches.
Podman's backport includes the compatibility entry points needed by all
shipped RPM binaries; a full unprivileged RPM build (`rpmbuild -ba`), normal
`dnf install`, installed-binary smoke checks and focused Podman tests are
required before the source layer is accepted. Current Podman and Skopeo source
scans still report the unfixed legacy `github.com/docker/distribution` v2
medium advisory and an unknown-severity `x/crypto/openpgp` advisory. The
available distribution/v3 replacement requires broader Buildah and conformance
test migration; ProtonMail OpenPGP rejects legacy V3 signatures Podman currently
accepts. Candidate replacements failed compatibility checks and were not
shipped. These are not ignored or represented as fixed; a later source/API
migration must preserve the existing conformance coverage.
Skopeo uses libtrust's standard Go crypto implementation with the maintained
Go/FIPS toolchain, rather than the legacy `libtrust_openssl` build tag that calls
the removed nonstandard `ecdsa.HashSign` API. The recipe overrides the EL9 Go RPM
macro's injected legacy tag as well as the recipe's own tag. Other compiler and
hardening flags are preserved. This does not disable Go FIPS mode
or constitute a certification claim.
Source preparation and dependency installation use root, then RPM compilation
and `%check` run as an unprivileged build account. This preserves permission-sensitive
tests such as SQLite's, which refuse to run as root.
The DAB OAuth compatibility layer applies its backport to older sources, or
verifies the explicit required, non-null organization field in newer upstream
sources. Unknown patch conflicts stop the build. Both paths retain the pinned
DRF installation and OAuth test suite before wheel creation.
EDA's rebuilt metadata pins the exact source-patched DAB wheel provided by the
bundle build, preserving EDA's upstream source selection without guessing a
date-based version floor. Missing or ambiguous wheel inputs stop the build.
Hub metadata patches support both the older `setup.py` layout and upstream's
`pyproject.toml` layout. Each patch is checked before application; unknown
packaging changes fail the build rather than skipping the dependency fixes.
After native RPM builds, the runtime layers remove the old system
`python3.12-setuptools` build-helper RPM before installing maintained Python
packages. Application virtualenvs retain their maintained setuptools; the
execution image installs its maintained system setuptools after removal.
Removal uses normal RPM dependency checks,
not forced removal or version-metadata changes; a required helper blocks the
build instead of leaving broken dependencies.

Each image/scanner SARIF report has its own analysis identity, so GitHub can
accept all Trivy and Grype results without duplicate-category upload failures.
The artifact preserves both the original reports and the upload-ready SARIF.
Both Trivy vulnerability databases use independent official registry fallbacks
so an unavailable mirror need not invalidate an otherwise successful build.

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

Production deployment is explicit: pushes and image publication do not trigger
Portainer automatically. The upstream bundle is the sole publisher for
AWX/Hub/EDA; generic image publication does not update these services.

In Portainer, create or update the Git-backed stack and redeploy. Portainer pulls
the exact image tag selected above. To advance the baseline, run the workflow
again and change only `DEVEL_IMAGE_TAG` and the matching AWX/Receptor variables.

Alternatively, after saving and verifying every matching image pin in Portainer,
dispatch **Deploy controller stack** from `main`. Supply the successful
**Publish upstream devel bundle** run ID, its exact immutable tag and the explicit
pin/backup confirmation. The workflow rejects failed/incomplete runs, other
workflows, non-main bundles and mismatched tags before calling the webhook.
It does not set the image pins for you. Verify actual service health, EDA
activation recovery and AWX job execution after the request is accepted.

The local helper `scripts/deploy-devel.sh` remains for Docker Desktop development;
it defaults to local `aax/*:devel` images and is not required by Portainer.
