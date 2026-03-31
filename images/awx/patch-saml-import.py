"""Patch awx/sso/backends.py to gracefully handle SAML import failures.

On aarch64 (arm64) with system libxml2 >= 2.12, the bundled libxml2 inside
the lxml 4.9.x wheel (2.10.3) mismatches the version that xmlsec links
against, causing xmlsec.InternalError at import time.  This crashes any
request that touches Django authentication backends, including /api/v2/auth/.

The fix: wrap the top-level SAML import with try/except so that the rest of
awx.sso.backends loads cleanly.  SAMLAuth.authenticate() already returns None
when SAML is unconfigured, so no SAML functionality is silently lost.
"""
import pathlib

p = pathlib.Path('/awx/awx/sso/backends.py')
text = p.read_text()

# All three top-level saml imports trigger the xmlsec import chain.
# Replace all three with a single guarded block.
OLD1 = 'from social_core.backends.saml import OID_USERID'
OLD2 = 'from social_core.backends.saml import SAMLAuth as BaseSAMLAuth'
OLD3 = 'from social_core.backends.saml import SAMLIdentityProvider as BaseSAMLIdentityProvider'
NEW = """\
try:
    from social_core.backends.saml import OID_USERID
    from social_core.backends.saml import SAMLAuth as BaseSAMLAuth
    from social_core.backends.saml import SAMLIdentityProvider as BaseSAMLIdentityProvider
except Exception as _saml_exc:
    import logging as _log
    _log.getLogger(__name__).warning(
        "SAML backend disabled (xmlsec/lxml libxml2 version mismatch): %s",
        _saml_exc,
    )
    OID_USERID = "urn:oid:0.9.2342.19200300.100.1.1"  # type: ignore[assignment]

    class BaseSAMLAuth:  # type: ignore[no-redef]
        name = "saml"
        backend_name = "saml"

    class BaseSAMLIdentityProvider:  # type: ignore[no-redef]
        pass\
"""

for label, target in [("OID_USERID", OLD1), ("SAMLAuth", OLD2), ("SAMLIdentityProvider", OLD3)]:
    if target not in text:
        raise SystemExit(f"Patch target '{label}' not found in {p}")

# Remove the two extra import lines (they move inside the try block)
text = text.replace(OLD1 + '\n', '', 1)
text = text.replace(OLD3 + '\n', '', 1)
# Replace the SAMLAuth line with the combined try/except block
p.write_text(text.replace(OLD2, NEW, 1))
print(f"Patched {p}")
