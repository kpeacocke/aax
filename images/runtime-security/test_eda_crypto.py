"""Verify AES-256 compatibility with existing EDA encrypted database values."""

import base64
import hashlib
import hmac
import unittest

from aap_eda.core.utils.crypto.fernet import Fernet256
from cryptography.fernet import InvalidToken
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


class EdaCryptoTests(unittest.TestCase):
    def setUp(self):
        self.raw_key = bytes(range(64))
        self.fernet = Fernet256(base64.urlsafe_b64encode(self.raw_key))

    def legacy_token(self, data):
        iv = bytes(range(16))
        padder = padding.PKCS7(128).padder()
        padded = padder.update(data) + padder.finalize()
        encryptor = Cipher(algorithms.AES(self.raw_key[32:]), modes.CBC(iv)).encryptor()
        encrypted = encryptor.update(padded) + encryptor.finalize()
        payload = b"\x80" + (1700000000).to_bytes(8, "big") + iv + encrypted
        signature = hmac.digest(self.raw_key[:32], payload, hashlib.sha256)
        return base64.urlsafe_b64encode(payload + signature)

    def test_round_trip(self):
        for data in (b"", b"stored setting", bytes(range(256)), b"x" * 4096):
            with self.subTest(length=len(data)):
                self.assertEqual(self.fernet.decrypt(self.fernet.encrypt(data)), data)

    def test_existing_ciphertext_is_preserved(self):
        for data in (b"", b"existing database secret", bytes(range(256))):
            with self.subTest(length=len(data)):
                self.assertEqual(self.fernet.decrypt(self.legacy_token(data)), data)

    def test_tampering_is_rejected(self):
        token = self.legacy_token(b"protected value")
        for position in (25, -1):
            with self.subTest(position=position):
                raw = bytearray(base64.urlsafe_b64decode(token))
                raw[position] ^= 1
                with self.assertRaises(InvalidToken):
                    self.fernet.decrypt(base64.urlsafe_b64encode(raw))

    def test_expired_token_is_rejected(self):
        token = self.fernet.encrypt_at_time(b"expires", current_time=10)
        with self.assertRaises(InvalidToken):
            self.fernet.decrypt_at_time(token, ttl=100, current_time=111)

    def test_wrong_key_is_rejected(self):
        other = Fernet256(base64.urlsafe_b64encode(bytes(range(64, 128))))
        with self.assertRaises(InvalidToken):
            other.decrypt(self.legacy_token(b"protected value"))

    def test_invalid_key_lengths_are_rejected(self):
        for length in (0, 16, 32, 63, 65):
            with self.subTest(length=length), self.assertRaises(ValueError):
                Fernet256(base64.urlsafe_b64encode(bytes(length)))


if __name__ == "__main__":
    unittest.main()
