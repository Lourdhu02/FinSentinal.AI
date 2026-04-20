from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import get_settings


class AESCipher:
    def __init__(self, key: bytes | str | None = None) -> None:
        self.key = self._normalize_key(key if key is not None else get_settings().encryption_key)
        self._aes = AESGCM(self.key)

    @staticmethod
    def _normalize_key(value: bytes | str) -> bytes:
        if isinstance(value, bytes):
            candidate = value
        else:
            try:
                candidate = base64.urlsafe_b64decode(value.encode("utf-8"))
            except Exception:
                candidate = value.encode("utf-8")
        if len(candidate) == 32:
            return candidate
        return hashlib.sha256(candidate).digest()

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(12)
        ciphertext = self._aes.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")

    def decrypt(self, token: str) -> str:
        raw = base64.urlsafe_b64decode(token.encode("utf-8"))
        nonce = raw[:12]
        ciphertext = raw[12:]
        return self._aes.decrypt(nonce, ciphertext, None).decode("utf-8")


def get_cipher() -> AESCipher:
    return AESCipher()
