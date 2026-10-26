"""Apply the compatibility backport or verify the upstream replacement."""

import ast
from pathlib import Path
import subprocess
import sys


def verify_upstream_fix(source: Path) -> None:
    serializer = ast.parse(source.read_text())
    application = next(
        node for node in serializer.body
        if isinstance(node, ast.ClassDef) and node.name == "OAuth2ApplicationSerializer"
    )
    organization = next(
        node.value for node in application.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "organization"
                for target in node.targets)
    )
    if not (
        isinstance(organization, ast.Call)
        and isinstance(organization.func, ast.Attribute)
        and isinstance(organization.func.value, ast.Name)
        and organization.func.value.id == "serializers"
        and organization.func.attr == "PrimaryKeyRelatedField"
    ):
        raise ValueError("Upstream organization must be an explicit PrimaryKeyRelatedField")
    options = {keyword.arg: keyword.value for keyword in organization.keywords}
    for name, expected in (("required", True), ("allow_null", False)):
        value = options.get(name)
        if not isinstance(value, ast.Constant) or value.value is not expected:
            raise ValueError(f"Upstream organization must set {name}={expected}")
    if "default" in options:
        raise ValueError("Upstream organization must not supply a default")


def main() -> None:
    patch = sys.argv[1]
    check = subprocess.run(["git", "apply", "--check", patch], capture_output=True, text=True)
    if check.returncode == 0:
        subprocess.run(["git", "apply", patch], check=True)
        print("Applied OAuth organization compatibility backport")
        return
    try:
        verify_upstream_fix(Path("ansible_base/oauth2_provider/serializers/application.py"))
    except (StopIteration, ValueError, SyntaxError) as error:
        raise SystemExit(
            f"OAuth backport does not apply and upstream fix was not verified: {error}\n"
            f"{check.stderr}"
        ) from error
    print("Verified upstream explicit required, non-null OAuth organization field")


if __name__ == "__main__":
    main()
