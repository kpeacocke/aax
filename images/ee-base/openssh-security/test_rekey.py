"""Exercise real client rekeying against a loopback-only SSH server."""

from concurrent.futures import ThreadPoolExecutor
import argparse
import os
from pathlib import Path
import socket
import subprocess
from tempfile import TemporaryDirectory
from threading import Event

import paramiko


class LocalServer(paramiko.ServerInterface):
    def __init__(self) -> None:
        self.executed = Event()

    def check_auth_none(self, username: str) -> int:
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind: str, channel_id: int) -> int:
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(self, channel: paramiko.Channel, command: bytes) -> bool:
        self.executed.set()
        return True


def exercise(client: str, host: str, rotate: bool) -> None:
    first = paramiko.RSAKey.generate(2048)
    second = paramiko.RSAKey.generate(2048) if rotate else first
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with TemporaryDirectory() as temporary, socket.socket(family) as listener:
        listener.bind((host, 0))
        listener.listen(1)
        listener.settimeout(30)
        port = listener.getsockname()[1]
        known_hosts = Path(temporary) / "known_hosts"
        known_hosts.write_text(f"[{host}]:{port} {first.get_name()} {first.get_base64()}\n")

        def serve() -> None:
            connection, _ = listener.accept()
            with connection, paramiko.Transport(connection) as transport:
                transport.add_server_key(first)
                server = LocalServer()
                transport.start_server(server=server)
                channel = transport.accept(30)
                if channel is None or not server.executed.wait(30):
                    raise TimeoutError("Client did not execute before rekey")
                channel.settimeout(30)
                ready = b""
                while len(ready) < 6:
                    chunk = channel.recv(6 - len(ready))
                    if not chunk:
                        raise AssertionError("Client closed before the rekey synchronization marker")
                    ready += chunk
                if ready != b"ready\n":
                    raise AssertionError("Client did not send the rekey synchronization marker")
                transport.add_server_key(second)
                try:
                    transport.renegotiate_keys()
                except (EOFError, ConnectionResetError, paramiko.SSHException):
                    if not rotate:
                        raise
                else:
                    if rotate:
                        raise AssertionError("Client accepted a changed, untrusted host key")
                    channel.sendall(b"rekey-complete\n")
                    channel.send_exit_status(0)
                    channel.close()
                    # Let the client finish its disconnect before closing the socket.
                    transport.join(30)
                    if transport.is_active():
                        raise TimeoutError("Client did not disconnect after successful rekey")

        with ThreadPoolExecutor(max_workers=1) as executor:
            server = executor.submit(serve)
            result = subprocess.run(
                [client, "-p", str(port), "-o", "StrictHostKeyChecking=yes",
                 "-o", f"UserKnownHostsFile={known_hosts}", "-o", "GlobalKnownHostsFile=/dev/null",
                 "-o", "UpdateHostKeys=no", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                 host, "true"],
                 input="ready\n", text=True, capture_output=True, timeout=60, check=False,
                env={**os.environ, "ASAN_OPTIONS": "detect_leaks=0"},
            )
            server.result(timeout=35)
        expected = 255 if rotate else 0
        if result.returncode != expected or "AddressSanitizer" in result.stderr:
            raise AssertionError(f"Rekey failed for {host}, rotate={rotate}: {result.returncode}\n{result.stderr}")
        if rotate:
            assert "Host key verification failed" in result.stderr, result.stderr
        else:
            assert result.stdout == "rekey-complete\n", result.stdout
        print(f"PASS: {host}, changed host key={rotate}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--asan", action="store_true")
    arguments = parser.parse_args()
    executable = "./ssh" if arguments.asan else "/usr/bin/ssh"
    for address in ("127.0.0.1", "::1"):
        for changed in (False, True):
            exercise(executable, address, changed)
