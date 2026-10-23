#!/usr/bin/env python3
import base64
import fcntl
import os
from pathlib import Path
import secrets
import sys
import tempfile


def initialize_key(path: Path) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_fd = os.open(path.with_suffix(".lock"), os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(lock_fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if path.exists():
            encoded = path.read_bytes().strip()
            if len(base64.b64decode(encoded, altchars=b"-_", validate=True)) != 32:
                raise ValueError(f"Invalid database encryption key: {path}")
            return
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as output:
                temporary = Path(output.name)
                output.write(base64.urlsafe_b64encode(secrets.token_bytes(32)))
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    if sys.argv[1:2] in (["run"], ["manage"]):
        initialize_key(
            Path(os.environ.get("PULP_DB_ENCRYPTION_KEY", "/etc/pulp/certs/database_fields.symmetric.key"))
        )
    os.execv("/entrypoint.sh", ["/entrypoint.sh", *sys.argv[1:]])
