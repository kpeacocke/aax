"""Adapt AWX's loaded-file check to the pinned Dynaconf settings core."""

import importlib.metadata
import importlib.util
from pathlib import Path


PRODUCTION_CHECK = '''def assert_production_settings(settings: Dynaconf, settings_dir: str, settings_file_path: str):  # pragma: no cover
    """Ensure at least one setting file has been loaded in production mode.
    Current systems will require /etc/tower/settings.py and
    new systems will require /etc/ansible-automation-platform/*.yaml
    """
    if "production" not in settings.current_env.lower():
        return

    required_settings_paths = [
        os.path.dirname(settings_file_path),
        "/etc/ansible-automation-platform/",
        settings_dir,
    ]

    for path in required_settings_paths:
        if any([path in os.path.dirname(f) for f in settings._loaded_files]):
            break
    else:
        from django.core.exceptions import ImproperlyConfigured  # noqa

        msg = 'No AWX configuration found at %s.' % required_settings_paths
        msg += '\\nDefine the AWX_SETTINGS_FILE environment variable to '
        msg += 'specify an alternate path.'
        raise ImproperlyConfigured(msg)
'''


def patch(path: Path) -> None:
    source = path.read_text()
    old = "for f in settings._loaded_files"
    new = "for f in settings.__core__.config.loaded_files"
    if source.count(PRODUCTION_CHECK) != 1 or source.count(old) != 1 or new in source:
        raise ValueError("Unexpected AWX production settings check; review Dynaconf compatibility")
    path.write_text(source.replace(PRODUCTION_CHECK, PRODUCTION_CHECK.replace(old, new)))


if __name__ == "__main__":
    if importlib.metadata.version("dynaconf") != "3.3.5":
        raise ValueError("Review AWX loaded-file compatibility before changing Dynaconf")
    spec = importlib.util.find_spec("awx")
    if spec is None or spec.origin is None:
        raise ValueError("AWX source package is required")
    patch(Path(spec.origin).parent / "settings/functions.py")
