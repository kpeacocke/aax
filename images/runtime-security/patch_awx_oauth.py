"""Enable the upstream DAB OAuth2 provider for standalone AWX."""

import ast
import importlib.util
from pathlib import Path


DEFAULTS_ANCHOR = "# SWAGGER_SETTINGS removed - migrated to drf-spectacular (see SPECTACULAR_SETTINGS below)"
OAUTH_SETTINGS = """if os.environ.get('AAX_AWX_OAUTH2_ENABLED', 'false').lower() == 'true':
    INSTALLED_APPS.append('ansible_base.oauth2_provider')
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = list(REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'])
    REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = (
        'ansible_base.oauth2_provider.permissions.OAuth2ScopePermission',
        *REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'],
    )

"""
VIEW_ANCHOR = """class APIView(views.APIView):
    # Schema is inherited from DRF's APIView, which uses DEFAULT_SCHEMA_CLASS
    # No need to override it here - drf-spectacular will handle it
    versioning_class = URLPathVersioning
"""
SCOPE_CHECK = """
    def get_permissions(self):
        permissions = super().get_permissions()
        # Explicit view permissions must not bypass bearer-token scopes.
        if getattr(self.request.user, 'oauth_scopes', None) is not None:
            from ansible_base.oauth2_provider.permissions import OAuth2ScopePermission

            if not any(isinstance(permission, OAuth2ScopePermission) for permission in permissions):
                permissions.insert(0, OAuth2ScopePermission())
        return permissions
"""
AUTHENTICATION_CLASSES = (
    "ansible_base.jwt_consumer.awx.auth.AwxJWTAuthentication",
    "awx.api.authentication.SessionAuthentication",
    "awx.api.authentication.LoggedBasicAuthentication",
)
EXTERNAL_LOOKUP = """authenticator_users = user.authenticator_users.all()
local = 'ansible_base.authentication.authenticator_plugins.local'
for auth_user in authenticator_users:
    if auth_user.provider.type != local:
        return auth_user.provider
return None
"""


def patch(root: Path) -> None:
    defaults = root / "settings/defaults.py"
    views = root / "api/generics.py"
    defaults_source = defaults.read_text()
    views_source = views.read_text()
    framework = next(
        (node.value for node in ast.parse(defaults_source).body
         if isinstance(node, ast.Assign)
         and any(isinstance(target, ast.Name) and target.id == "REST_FRAMEWORK"
                 for target in node.targets)),
        None,
    )
    if not isinstance(framework, ast.Dict):
        raise ValueError("Unexpected AWX REST framework settings")
    values = {key.value: value for key, value in zip(framework.keys, framework.values)
              if isinstance(key, ast.Constant)}
    if (
        ast.literal_eval(values["DEFAULT_AUTHENTICATION_CLASSES"]) != AUTHENTICATION_CLASSES
        or ast.literal_eval(values["DEFAULT_PERMISSION_CLASSES"])
        != ("awx.api.permissions.ModelAccessPermission",)
    ):
        raise ValueError("Unexpected AWX authentication or permission policy")
    if (
        defaults_source.count(DEFAULTS_ANCHOR) != 1
        or "'ansible_base.oauth2_provider'" in defaults_source
        or views_source.count(VIEW_ANCHOR) != 1
        or "def get_permissions(" in views_source
    ):
        raise ValueError("Unexpected AWX OAuth2 integration source; review upstream changes")
    defaults.write_text(defaults_source.replace(DEFAULTS_ANCHOR, OAUTH_SETTINGS + DEFAULTS_ANCHOR))
    views.write_text(views_source.replace(VIEW_ANCHOR, VIEW_ANCHOR + SCOPE_CHECK))


def patch_optional_auth(path: Path) -> None:
    source = path.read_text()
    old_import = "from ansible_base.authentication.models import Authenticator"
    old_lookup = "    authenticator_users = user.authenticator_users.all()"
    functions = [node for node in ast.parse(source).body
                 if isinstance(node, ast.FunctionDef) and node.name == "is_external_account"]
    expected_body = ast.parse(EXTERNAL_LOOKUP).body
    actual_body = [
        node for node in functions[0].body
        if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str))
    ] if len(functions) == 1 else []
    if (
        source.count(old_import) != 1
        or source.count(old_lookup) != 1
        or "TYPE_CHECKING" in source
        or "apps.is_installed" in source
        or [ast.dump(node) for node in actual_body] != [ast.dump(node) for node in expected_body]
    ):
        raise ValueError("Unexpected DAB external-account lookup; review optional authentication")
    source = "from __future__ import annotations\n\n" + source
    source = source.replace(
        old_import,
        "from django.apps import apps\n"
        "from typing import TYPE_CHECKING\n\n"
        "if TYPE_CHECKING:\n"
        "    from ansible_base.authentication.models import Authenticator",
    )
    source = source.replace(
        old_lookup,
        "    if not apps.is_installed('ansible_base.authentication'):\n"
        "        return None\n" + old_lookup,
    )
    path.write_text(source)


if __name__ == "__main__":
    spec = importlib.util.find_spec("awx")
    if spec is None or spec.origin is None:
        raise ValueError("AWX source package is required")
    patch(Path(spec.origin).parent)
    dab_spec = importlib.util.find_spec("ansible_base")
    if dab_spec is None or dab_spec.origin is None:
        raise ValueError("DAB source package is required")
    patch_optional_auth(Path(dab_spec.origin).parent / "oauth2_provider/utils.py")
