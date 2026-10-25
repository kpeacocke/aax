"""Bind the EDA rebuild to the DAB wheel verified by this bundle build."""

from email.parser import Parser
from pathlib import Path
import sys
import zipfile


def pin(project: Path, wheel_directory: Path) -> None:
    wheels = list(wheel_directory.glob("django_ansible_base-*.whl"))
    if len(wheels) != 1:
        raise ValueError(f"Expected one verified DAB wheel, found {len(wheels)}")
    with zipfile.ZipFile(wheels[0]) as wheel:
        metadata_files = [
            name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_files) != 1:
            raise ValueError("Expected one DAB wheel metadata record")
        metadata = Parser().parsestr(wheel.read(metadata_files[0]).decode("utf-8"))
    version = metadata["Version"]
    if metadata["Name"] != "django-ansible-base" or not version or "+aax." not in version:
        raise ValueError("Expected an AAX source-patched DAB wheel")
    old = 'django-ansible-base = { version = ">=2026.10.21.1.dev2"'
    contents = project.read_text()
    if contents.count(old) != 1:
        raise ValueError("Expected one patched EDA DAB dependency")
    project.write_text(contents.replace(old, f'django-ansible-base = {{ version = "=={version}"'))
    print(f"Pinned EDA to verified DAB wheel {version}")


if __name__ == "__main__":
    pin(Path(sys.argv[1]), Path(sys.argv[2]))
