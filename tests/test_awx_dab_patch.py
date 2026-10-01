from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "images" / "awx" / "patch-dab-requirement.py"
_SPEC = spec_from_file_location("patch_dab_requirement", MODULE_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
patch_dab_requirement = module_from_spec(_SPEC)
_SPEC.loader.exec_module(patch_dab_requirement)


def test_rewrite_dab_requirement_preserves_extras_and_fragment() -> None:
    original = (
        "django-ansible-base[extras] @ "
        "git+https://github.com/ansible/django-ansible-base@devel#egg=django-ansible-base[extras]\n"
    )

    rewritten = patch_dab_requirement.rewrite_dab_requirement(original, "2024.6.26")

    assert rewritten == (
        "django-ansible-base[extras] @ "
        "git+https://github.com/ansible/django-ansible-base@2024.6.26#egg=django-ansible-base[extras]\n"
    )


def test_rewrite_dab_requirement_supports_plain_dependency_line() -> None:
    original = (
        "django-ansible-base @ "
        "git+https://github.com/ansible/django-ansible-base@devel\n"
    )

    rewritten = patch_dab_requirement.rewrite_dab_requirement(original, "2024.6.26")

    assert rewritten == (
        "django-ansible-base @ "
        "git+https://github.com/ansible/django-ansible-base@2024.6.26\n"
    )
