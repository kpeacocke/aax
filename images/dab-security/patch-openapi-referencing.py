"""Adapt DAB's test-only OpenAPI dependency bound to validator 0.8.4."""

from pathlib import Path
import sys


def patch(path: Path) -> None:
    source = path.read_text()
    old = "referencing<0.37.0  # consistent with pin from jsonschema-path, via openapi-spec-validator"
    new = "referencing>=0.37.0,<0.38.0  # compatible with openapi-spec-validator 0.8.4"
    if source.count(old) != 1 or new in source:
        raise ValueError("Unexpected DAB OpenAPI referencing constraint; review compatibility")
    path.write_text(source.replace(old, new))


if __name__ == "__main__":
    patch(Path(sys.argv[1]))
