"""Regressions for source-backported CPython security fixes."""

from http.client import HTTPResponse, IncompleteRead
import io
import json
from pathlib import Path
import platform
import poplib
import socket
import sys
import sysconfig
import unittest


class FakeSocket:
    def __init__(self, response: bytes) -> None:
        self.response = response

    def makefile(self, mode: str) -> io.BytesIO:
        assert mode == "rb"
        return io.BytesIO(self.response)


class RuntimeSecurityTests(unittest.TestCase):
    def test_pop3_rejects_control_characters_before_sending(self) -> None:
        client = object.__new__(poplib.POP3)
        client._debugging = 0
        client.encoding = "UTF-8"
        sent = []
        client._putline = sent.append
        client._getresp = lambda: b"+OK"
        for character in (*range(32), 127):
            with self.subTest(character=character):
                with self.assertRaises(ValueError):
                    client.user(f"alice{chr(character)}DELE 1")
                with self.assertRaises(ValueError):
                    client.pass_(f"secret{chr(character)}QUIT")
        self.assertEqual(sent, [])
        self.assertEqual(client.user("alice"), b"+OK")
        self.assertEqual(sent, [b"USER alice"])

    def test_getaddrinfo_rejects_nulls_in_hosts_and_ports(self) -> None:
        for host in ("local\0host", b"localhost\0", "\0localhost", "b\u00fccher\0.example"):
            with self.subTest(host=host):
                with self.assertRaisesRegex(ValueError, "host"):
                    socket.getaddrinfo(host, 80)
        for port in ("8\x000", b"8\x000", "http\0", b"\0"):
            with self.subTest(port=port):
                with self.assertRaisesRegex(ValueError, "port"):
                    socket.getaddrinfo("127.0.0.1", port)
        self.assertTrue(socket.getaddrinfo(
            "127.0.0.1", 80, flags=socket.AI_NUMERICHOST | socket.AI_NUMERICSERV,
        ))
        left, right = socket.socketpair()
        with left, right:
            left.sendall(b"fixed")
            self.assertEqual(right.recv(5), b"fixed")

    def test_http_rejects_malformed_framing_and_preserves_optional_whitespace(self) -> None:
        for size in (b"-5", b"+5", b"0x5", b"1_f", b" 5"):
            with self.subTest(size=size):
                response = HTTPResponse(FakeSocket(
                    b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
                    + size + b"\r\nHELLO\r\n0\r\n\r\n",
                ))
                response.begin()
                with self.assertRaises(IncompleteRead):
                    response.read()
                self.assertTrue(response.isclosed())
        for length in (b"+5", b"5_0"):
            with self.subTest(length=length):
                response = HTTPResponse(FakeSocket(
                    b"HTTP/1.1 200 OK\r\nContent-Length: " + length + b"\r\n\r\nHello",
                ))
                response.begin()
                self.assertIsNone(response.length)
                self.assertEqual(response.read(), b"Hello")
        response = HTTPResponse(FakeSocket(
            b"HTTP/1.1 200 OK\r\nContent-Length: 5 \t\r\n\r\nHelloEXTRA",
        ))
        response.begin()
        self.assertEqual(response.length, 5)
        self.assertEqual(response.read(), b"Hello")

    def test_matching_runtime_provenance(self) -> None:
        provenance = json.loads(Path(
            "/usr/local/share/aax/python-security/provenance.json",
        ).read_text())
        self.assertEqual(provenance["version"], platform.python_version())
        self.assertEqual(provenance["soabi"], sysconfig.get_config_var("SOABI"))
        self.assertEqual(provenance["architecture"], platform.machine())
        self.assertEqual(sys.version_info[:2], (3, 14))


if __name__ == "__main__":
    unittest.main()
