"""Adapt AWX's loaded-file check to the pinned Dynaconf settings core."""

import importlib.metadata
import importlib.util
from pathlib import Path


def patch(path: Path) -> None:
    source = path.read_text()
    old = "for f in settings._loaded_files"
    new = "for f in settings.__core__.config.loaded_files"
    if source.count(old) != 1 or new in source:
        raise ValueError("Unexpected AWX production settings check; review Dynaconf compatibility")
    path.write_text(source.replace(old, new))


if __name__ == "__main__":
    if importlib.metadata.version("dynaconf") != "3.3.5":
        raise ValueError("Review AWX loaded-file compatibility before changing Dynaconf")
    spec = importlib.util.find_spec("awx")
    if spec is None or spec.origin is None:
        raise ValueError("AWX source package is required")
    patch(Path(spec.origin).parent / "settings/functions.py")
