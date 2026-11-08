# Security Baseline

This document defines baseline controls for local-dev and production-like AAX operation.

## Profiles

### Local-Dev Baseline

- `HOST_BIND` may be set to `127.0.0.1` (default) or explicitly opened for isolated lab testing.
- `AWX_ALLOW_INSECURE_COOKIES` may be set to `true` only for local HTTP lab flows.
- Placeholder secret values are allowed only for non-shared disposable environments.
- Security scans are expected to run, but findings may be triaged as non-blocking during early iteration.

### Production-Like Baseline

- `HOST_BIND` remains localhost by default unless access requirements are explicitly approved.
- `AWX_ALLOW_INSECURE_COOKIES` must remain `false`.
- Required secrets must be strong operator-provided values.
- No weak fallback passwords or secret defaults in runtime config.
- Policy checks must pass (repo policy + docs contract tests).
- Secret scanning and remediable HIGH/CRITICAL vulnerabilities are release gates.

## Mandatory CI Baseline Gates

- `tests/test_repo_policy.py`
- `tests/test_docs_contract.py`
- `tests/test_bundle_publication.py`
- Secret scanning workflow checks
- Image vulnerability scanning in CI/release workflows. All findings are retained
  in GitHub Security; required PR checks retain their fixable CRITICAL threshold
  so existing HIGH findings do not prevent remediation PRs. Publication blocks
  HIGH/CRITICAL findings with a scanner-reported fix.
  Main-channel multi-architecture candidates are scanned by
  digest before deployment tags are promoted. Candidate tags are not deployment tags.

## Scheduled Dependency Reports

The weekly Dependency Management workflow audits the combined `ee-base`,
`ee-builder` and `dev-tools` Python requirements with `ee-base` constraints.
It audits both the resolved dependency graph and every exact direct pin, including
bootstrap packages such as `setuptools` that pip's temporary environment may omit
from the resolved inventory. It validates report schemas, both audit exit statuses
and coverage of every direct requirement before changing issues. Missing, skipped
or malformed dependencies fail the workflow rather than being treated as clean.
Only audits running on `main` reconcile repository issues; branch runs still
validate both reports and fail for vulnerabilities without changing main's reports.

Vulnerable results keep one current security/dependencies issue open and close
older matching reports as duplicates, not as fixed vulnerabilities. A clean
audit closes those historical reports with the current commit, run and artifact
as evidence. These closures apply only to that requirements scope, not to
upstream application images or OS packages. Image publication gates remain
independent. The full `dependency-audit` artifact is retained on failure as well
as success.

## Deduplicated image fix inventory

Export all open GitHub image alerts and group advisory/package pairs locally:

```bash
gh api --paginate '/repos/kpeacocke/aax/code-scanning/alerts?state=open&per_page=100' \
  --jq '.[] | {number,rule_id:.rule.id,severity:.rule.security_severity_level,tool:.tool.name,help:.rule.help,message:.most_recent_instance.message.text,category:.most_recent_instance.category,ref:.most_recent_instance.ref,path:.most_recent_instance.location.path,commit:.most_recent_instance.commit_sha,url:.html_url}' \
  > image-alerts.jsonl &&
python scripts/report-image-fixes.py image-alerts.jsonl image-fix-inventory.json
```

Use `scanner_reported_fix` findings as the initial patch queue. The inventory
retains every affected image/architecture, scanner, version, path, commit and
alert link; it never dismisses GitHub alerts. `no_fix_reported` is not proof that
no source patch exists, and `fix_metadata_missing` requires investigation.
Fixed versions from historical alerts must be checked against current vendor
artifacts and fresh exact-image scans. Advisory aliases are not merged without
verified evidence. Refresh all Trivy and Grype reports before calling remediation
complete; a language-only SBOM scan does not establish OS coverage.
The weekly/manual Dependency Management workflow publishes the same
`image-fix-inventory` artifact and a patch-queue table in its run summary,
independently of the Python requirements audit. Failed exports or malformed
reports fail that job rather than publishing a partial inventory.

## Upstream Blockers

A clean package resolver does not establish a clean image. In particular, pip
vendors its own copies of libraries: constraints on installed `urllib3`, `msgpack`,
or `setuptools` do not replace pip's vendored code. If a scanner reports fixes for
those libraries but current pip has not incorporated them, publication remains
blocked. Do not delete vulnerability metadata, patch vendored code ad hoc, or add
blanket ignores to turn the gate green.

Distribution findings without patched vendor packages remain visible. A passing
fixable-vulnerability gate does not certify that the image has no known issues,
nor does it replace full-stack runtime tests. Review the exact bundle reports
and deployed image digests before production use.

### Coordinated dependency upgrades

AWX's protobuf 7 upgrade includes `googleapis-common-protos` 1.76.0 and the
complete pinned OpenTelemetry 1.45.2 / instrumentation 0.66b2 family. Upgrading
only protobuf leaves the older exporters' exact dependency pins inconsistent.
Dependabot groups this family together. The runtime image build requires
`pip check` and exercises AWX's actual OTLP log handler for both gRPC and HTTP,
including protobuf serialization, resource attributes and formatted log records.
These probes use an in-memory collector; they do not send task data externally.
The runtime patch stage force-installs the wheel supplied by the maintained
pip build, even if an inherited image reports the same package version. Version
equality alone cannot prove that a downstream wheel contains the current
vendored security fixes.

DAB's OpenAPI validator 0.9.0 uses the guarded, source-anchored `referencing`
constraint adapter. The wheel build runs both upstream OAuth and API
documentation tests before producing the patched wheel. Both upgrades retain
the existing publication vulnerability gates.

AWX, EDA and Hub pin oauthlib 4.0.1 for CVE-2026-49272. Device-flow
integrations must implement the updated oauthlib validator contract; a successful
dependency installation alone does not verify custom device-flow integrations.
Hub's OpenTelemetry API, SDK, protocol and HTTP exporter are upgraded together
with their matching semantic conventions and a source-patched pulpcore
dependency range to avoid incompatible runtime pins.
The decision environment also rebuilds signed vendor sources for Pixman,
ICU and kbd, covering CVE-2022-44638, CVE-2025-5222 and CVE-2026-72693.
These fixes are required even when CentOS Stream's available package releases
do not contain the distribution security backports.

Tooling images retain Python 3.14 and source-backport CPython fixes for POP3
command injection (CVE-2025-15367), HTTP response framing (CVE-2026-103995)
and null-byte truncation in `getaddrinfo` (CVE-2026-116566). The build verifies
the official Python source checksum and upstream patch checksums, rebuilds only
the affected socket extension against the matching interpreter's headers and
flags, and retains the patches and runtime ABI provenance in the image.
The final slim image executes regressions for malformed and valid inputs.
Neither the Python version nor scanner metadata is rewritten: scanners may
continue to report these version-based findings after the backport. Review the
retained patch evidence and executed runtime regressions, not just the count.
OpenSSH CVE-2026-60002 still requires a verified source backport or a fixed
stable distribution package; it is not unfixable merely because Debian's
stable package has no published fix.

All controller runtimes pin the fixed `pyasn1` 0.6.5; upgrading only AWX does
not protect EDA or Hub's separate virtual environments. The decision environment
is headless: it excludes the complete `libX11*` (including `libX11-xcb`) and
`libXtst*` GUI package families while retaining the headless JVM and its
dependencies. The rulebook, decision environment and EDA controller replace the vulnerable CentOS
OpenJDK 17 package with official Temurin 17.0.21+9 JRE archives, verified against
the upstream release's architecture-specific SHA256 hashes. CentOS Stream did
not yet offer the fixed package for CVE-2026-91415 when this change was made.
The patched JRE is shared from the exact scanned rulebook image into both the
decision image and EDA controller, including its dispatcher and WebSocket services.
The minimal rulebook base removes its old JVM with `microdnf`; the decision
and EDA controller bases use `dnf`. Missing package managers fail the build explicitly.
The image build verifies Java remains executable, sets its explicit library
path, and initializes the real Drools JPY engine in both rulebook runtimes as the unprivileged runtime user,
and publication still requires a real rulebook smoke test and image scan.

EDA retains Django 5.2.18: the pinned controller requires Django below 5.3,
and its DAB integration does not support Django 6. Removing a resolver bound
is not a framework migration. Remove the remaining Django major-version
exclusion only after coordinated EDA/DAB source and runtime tests pass.
The same rule applies to OAuth Toolkit: the pinned DAB source explicitly
requires a version below 2.4.0. Dependabot excludes every version at or above
that boundary, including the incompatible minor update 2.4.0.
Retain 2.3.0 until the DAB models, migrations,
token and scope tests support a coordinated major upgrade. A green tooling-image
PR check does not test this application dependency relationship.

### AWX worker protocol diagnostics

Receptor combines command stdout and stderr into its result stream. The Compose
workers therefore redirect runner stderr to uniquely named, mode-0600 files
under `/tmp/aax-runner-stderr.*` on the existing shared `awx_runner_tmp` volume.
Runner stdout remains its JSON protocol, and a nonzero worker exit still fails
the work unit. Empty diagnostic files are removed; nonempty files are retained,
including after a failed job, so a Python traceback cannot corrupt the protocol
or disappear with Receptor's work-directory cleanup.

When a worker fails, inspect the matching timestamped diagnostic files inside
`awx-receptor` or `receptor-execution`. Treat their contents as sensitive: they
may include task inputs or credentials. Never post raw files to an issue.
Retain only the evidence needed for diagnosis and delete reviewed files by
explicit path; these files do not have automatic age-based retention. A clean
protocol does not mean the underlying worker exception has been repaired.

The retained traceback for project update 1575 identified a `FileExistsError`
in `Runner.run`: another creator could make `job_events` between its existence
check and `os.mkdir`. The final AWX virtualenv and execution environment receive
a guarded source patch using
`os.makedirs(..., mode=0o700, exist_ok=True)`, after all upstream installations.
Every patched interpreter runs a deterministic regression against its actual
`Runner.run`, including concurrent creation, private directory permissions,
preserved existing events, file collisions and permission failures. Only an
existing directory is accepted; genuine filesystem errors still fail the job.
AWX system Python does not contain `ansible-runner`; it is not an additional
runner consumer.

## Operator Checklist

- Set all required secrets before startup.
- Confirm localhost-first bind policy.
- Confirm gateway-first exposure model for shared endpoints.
- Verify policy checks before merge or release.
