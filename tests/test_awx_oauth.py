"""Verify standalone OAuth2 adaptation and explicit-view scope enforcement."""

import ast
from pathlib import Path
import runpy
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
PATCH = runpy.run_path(str(ROOT / "images/runtime-security/patch_awx_oauth.py"))


@pytest.mark.parametrize("mutation", ["none", "defaults", "views", "existing", "policy"])
def test_oauth_patch_rejects_unknown_source_atomically(tmp_path: Path, mutation: str) -> None:
    (tmp_path / "settings").mkdir()
    (tmp_path / "api").mkdir()
    defaults = tmp_path / "settings/defaults.py"
    views = tmp_path / "api/generics.py"
    defaults.write_text(
        "REST_FRAMEWORK = {\n"
        f"'DEFAULT_AUTHENTICATION_CLASSES': {PATCH['AUTHENTICATION_CLASSES']!r},\n"
        "'DEFAULT_PERMISSION_CLASSES': ('awx.api.permissions.ModelAccessPermission',),\n"
        "}\n" + (PATCH["DEFAULTS_ANCHOR"] if mutation != "defaults" else "")
    )
    if mutation == "policy":
        defaults.write_text(defaults.read_text().replace("AwxJWTAuthentication", "ChangedAuthentication"))
    views.write_text(
        PATCH["VIEW_ANCHOR"]
        + ("    def get_permissions(self): pass\n" if mutation == "existing" else "")
        if mutation != "views" else ""
    )
    before = (defaults.read_text(), views.read_text())
    if mutation == "none":
        PATCH["patch"](tmp_path)
        assert PATCH["OAUTH_SETTINGS"] in defaults.read_text()
        assert PATCH["SCOPE_CHECK"] in views.read_text()
        with pytest.raises(ValueError, match="Unexpected AWX"):
            PATCH["patch"](tmp_path)
    else:
        with pytest.raises(ValueError, match="Unexpected AWX"):
            PATCH["patch"](tmp_path)
        assert (defaults.read_text(), views.read_text()) == before


@pytest.mark.parametrize("scope", [None, [], ["read"], ["write"]])
def test_explicit_view_permissions_cannot_bypass_token_scope(monkeypatch, scope) -> None:
    import sys

    class ScopePermission:
        pass

    module = SimpleNamespace(OAuth2ScopePermission=ScopePermission)
    monkeypatch.setitem(sys.modules, "ansible_base.oauth2_provider.permissions", module)

    class Base:
        def get_permissions(self):
            return ["existing-rbac-check"]

    tree = ast.parse("class View(Base):\n" + PATCH["SCOPE_CHECK"])
    namespace = {"Base": Base}
    exec(compile(tree, "<scope-check>", "exec"), namespace)
    view = namespace["View"]()
    view.request = SimpleNamespace(user=SimpleNamespace(oauth_scopes=scope))
    permissions = view.get_permissions()
    assert permissions[-1] == "existing-rbac-check"
    assert sum(isinstance(p, ScopePermission) for p in permissions) == (scope is not None)


def test_optional_auth_adaptation_preserves_external_lookup(tmp_path: Path) -> None:
    path = tmp_path / "utils.py"
    path.write_text(
        "from ansible_base.authentication.models import Authenticator\n"
        "def is_external_account(user):\n"
        + "".join("    " + line + "\n" for line in PATCH["EXTERNAL_LOOKUP"].splitlines())
    )
    PATCH["patch_optional_auth"](path)
    source = path.read_text()
    assert "if TYPE_CHECKING:" in source
    assert "if not apps.is_installed('ansible_base.authentication'):" in source
    assert "authenticator_users = user.authenticator_users.all()" in source
    ast.parse(source)
    with pytest.raises(ValueError, match="Unexpected DAB"):
        PATCH["patch_optional_auth"](path)


@pytest.mark.parametrize("installed,external", [(False, False), (True, False), (True, True)])
def test_optional_auth_retains_external_user_restriction(
    tmp_path: Path, monkeypatch, installed: bool, external: bool,
) -> None:
    import sys

    path = tmp_path / "utils.py"
    path.write_text(
        "from typing import Optional\n"
        "from django.contrib.auth import get_user_model\n"
        "from ansible_base.authentication.models import Authenticator\n"
        "User = get_user_model()\n"
        'def is_external_account(user: "User") -> Optional[Authenticator]:\n'
        + "".join("    " + line + "\n" for line in PATCH["EXTERNAL_LOOKUP"].splitlines())
    )
    PATCH["patch_optional_auth"](path)
    monkeypatch.setitem(
        sys.modules, "django.apps",
        SimpleNamespace(apps=SimpleNamespace(is_installed=lambda _: installed)),
    )
    monkeypatch.setitem(
        sys.modules, "django.contrib.auth", SimpleNamespace(get_user_model=lambda: object),
    )
    namespace = {}
    exec(compile(path.read_text(), str(path), "exec"), namespace)
    provider = SimpleNamespace(
        type="external.ldap" if external else "ansible_base.authentication.authenticator_plugins.local",
    )
    user = SimpleNamespace()
    if installed:
        user.authenticator_users = SimpleNamespace(all=lambda: [SimpleNamespace(provider=provider)])
    result = namespace["is_external_account"](user)
    assert result is (provider if external else None)
