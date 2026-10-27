# Tested Version Matrix

This document is the canonical tested version matrix for the current AAX baseline.

## Compose and Portainer Component Images

The project intentionally targets a recent, compatible AAP-like deployment baseline:

- upstream AWX and AWX EE are pinned to recent tested versions
- execution/dev-tool images follow the AAX release channel
- Hub/EDA use the maintained upstream bundle, not the retired legacy publisher
- Portainer remains the deployment gate for the assembled stack

| Component      | Default Tag | Source             |
| -------------- | ----------- | ------------------ |
| awx            | `devel`     | `AWX_VERSION`      |
| awx-ee         | `devel`     | `AWX_EE_VERSION`   |
| ee-base        | `latest`    | `AAX_VERSION`      |
| ee-builder     | `latest`    | `AAX_VERSION`      |
| dev-tools      | `latest`    | `AAX_VERSION`      |
| galaxy-ng      | `devel`     | `DEVEL_IMAGE_TAG`  |
| pulp           | `devel`     | `DEVEL_IMAGE_TAG`  |
| eda-controller | `devel`     | `DEVEL_IMAGE_TAG`  |
| eda-podman     | `devel`     | `DEVEL_IMAGE_TAG`  |
| gateway        | `latest`    | `AAX_VERSION`      |
| receptor       | `devel`     | `RECEPTOR_VERSION` |

The upstream development stack uses Python 3.12, Django 5.2, and the matching
`django-ansible-base` development branch. The AWX image retains an explicit
compatibility pin for callers who build the older `24.6.1` stable tag.

The execution environment uses `ansible-core` 2.21.5, `ansible-runner` 2.4.3,
and Python 3.14. Development tools use `ansible-navigator` 26.10.0,
`ansible-lint` 26.10.1, and `ansible-dev-tools` 26.10.0. Controller and Hub
versions follow the exact source revisions and source-patched dependencies
recorded in each successful upstream bundle's provenance, not the versions
in the retained legacy Docker recipes.

The EE builder uses `ansible-builder` 3.2.0. Development validation uses
pytest 9.1.1, pytest-cov 7.1.0, pre-commit 4.7.0 and Commitizen 4.19.2.
The patched pip wheel vendors Rich 15.0.0.

The Python 3.11 Galaxy/Pulp recipes and rulebook-only EDA recipe are retained
as legacy source, not published as production controllers. Their old `latest`
images are not maintained and must not be used for new deployments. The upstream
bundle is the only publisher of AWX, Hub/Pulp and the real EDA controller;
standalone AWX UI and EDA workflows are validation-only. Production selects a
successful immutable bundle tag and uses both Compose files as documented in
[Portainer deployment](PORTAINER_DEVEL.md).

## Kubernetes Component Images

The Kubernetes manifests remain pinned to the locally built `aax/*:1.0.0`
baseline. They do not follow the Compose/Portainer `AAX_VERSION` channel and
must be advanced deliberately as a separate deployment target.

## Runtime Base Dependencies

| Dependency            | Default channel                       |
| --------------------- | ------------------------------------- |
| PostgreSQL (AWX, EDA) | `15` (floats to the newest `15.x`)    |
| PostgreSQL (Hub)      | `16-alpine` (newest Alpine `16.x`)    |
| Redis                 | `7.4` / `7.4-alpine` (newest `7.4.x`) |

## Update Rules

- Update this file whenever changing default image tags in Compose, Kubernetes,
  or `.env.example`.
- Keep CI/release workflows aligned with these defaults.
- Run policy and docs contract tests after any version change.
- Dependabot checks Python manifests, including the development container,
  and image build directories weekly. Python patch/minor updates are grouped.
  `ansible-core` is excluded from this group because minor releases can change
  application compatibility and require separate validation.
- Build-only toolchains use Node 26 for AWX UI, Maven/JDK 26 for Drools
  (Java 17 bytecode), and Python 3.15 for patched pip, DAB and Hub wheel builders.
  These do not change the deployed application Python/JVM requirements.
  DAB's builder includes zlib headers for its source-built lxml dependency.
- DAB test dependencies retain `openapi-spec-validator` 0.8.1: versions 0.8.4, 0.8.5
  and 0.9.0 require `referencing>=0.37.0`, conflicting with the pinned DAB source's
  `referencing<0.37.0` constraint.
  Newer validator releases remain deferred until the pinned DAB source accepts
  the newer dependency range.
- EDA retains Django 5.2 because its pinned source requires `>=5.2,<5.3`
  and DAB requires `<6`. AWX retains protobuf 6 because its Google API and
  OpenTelemetry dependencies require `<7`. These incompatible major updates
  are deferred until the upstream integrations can migrate together.
- The EDA decision environment receives user-site Python and patched Drools/Jackson
  updates, removes unused desktop RPMs and pip build caches, and executes a
  range/debug rule inside nested Podman before publication.
- Main-channel images are rebuilt weekly with fresh bases and package installs.
  Both architectures of each candidate digest must pass the fixable HIGH/CRITICAL
  vulnerability gate before `latest`/`main` tags are promoted. The execution-image
  descendants use the exact scanned base digest, not a moving base tag.
- The upstream development bundle uses a distinct tag per workflow run and retry;
  see [Portainer devel deployment](PORTAINER_DEVEL.md) for its source/SBOM evidence.

## Digest Pinning Strategy

- Use immutable digest pinning for externally sourced base/runtime images where practical.
- Use Portainer's `AAX_VERSION` as the deployment gate. The lab tracks the
  tested `latest` main-branch build until a semantic release tag is available.
- PostgreSQL and Redis intentionally use upstream-maintained floating channels.
  Watchtower is label-enabled but monitor-only for these stateful services: it
  reports a changed digest and Portainer remains the manual deployment gate.
- AWX, AWX EE, and Receptor use exact versions because their upgrades require
  coordinated compatibility testing. AAX uses the controlled `latest` channel
  for the lab and semantic tags for immutable releases.
- Introduce digest enforcement incrementally after validating multi-arch release behavior.
