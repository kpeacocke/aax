from pathlib import Path
import re
import sys


_DAB_GIT_URL = "git+https://github.com/ansible/django-ansible-base@"
_DAB_LINE_RE = re.compile(
    rf"^(?P<prefix>django-ansible-base(?:\[[^\]]+\])?\s*@\s*{re.escape(_DAB_GIT_URL)})(?P<ref>[^#\s]+)(?P<suffix>#.*)?$"
)


def rewrite_dab_requirement(requirements_text: str, dab_ref: str) -> str:
    lines = requirements_text.splitlines()
    matches = [index for index, line in enumerate(lines) if _DAB_LINE_RE.match(line)]
    if len(matches) != 1:
        raise ValueError(f"Expected one django-ansible-base dependency, found {len(matches)}")

    match = _DAB_LINE_RE.match(lines[matches[0]])
    if match is None:
        raise ValueError("Failed to parse django-ansible-base dependency")

    suffix = match.group("suffix") or ""
    lines[matches[0]] = f"{match.group('prefix')}{dab_ref}{suffix}"
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    awx_version, dab_ref = argv[1:]
    if not dab_ref and awx_version == "24.6.1":
        dab_ref = "2024.6.26"
    if not dab_ref:
        return 0

    requirements_file = Path("/awx/requirements/requirements_git.txt")
    requirements_file.write_text(
        rewrite_dab_requirement(requirements_file.read_text(), dab_ref)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
