"""Ed25519 identity and signature helpers."""

from __future__ import annotations

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class Identity:
    def __init__(self, private_key: Ed25519PrivateKey):
        self._private_key = private_key
        self._public_key = None

    @classmethod
    def from_private_bytes(cls, value: bytes) -> "Identity":
        if len(value) != 32:
            raise ValueError("Ed25519 private keys must be 32 bytes")
        return cls(Ed25519PrivateKey.from_private_bytes(value))

    @classmethod
    def from_public_bytes(cls, value: bytes) -> "Identity":
        if len(value) != 32:
            raise ValueError("Ed25519 public keys must be 32 bytes")
        obj = cls.__new__(cls)
        obj._private_key = None
        obj._public_key = Ed25519PublicKey.from_public_bytes(value)
        return obj

    def private_bytes(self) -> bytes:
        if self._private_key is None:
            raise ValueError("identity has no private key")
        return self._private_key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )

    def public_bytes(self) -> bytes:
        key = self._private_key.public_key() if self._private_key else self._public_key
        return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)

    def public_key_encoded(self) -> str:
        return _b64(self.public_bytes())

    def sign(self, message: bytes) -> bytes:
        if self._private_key is None:
            raise ValueError("identity has no private key")
        return self._private_key.sign(message)

    def verify(self, message: bytes, signature: bytes) -> bool:
        try:
            key = self._private_key.public_key() if self._private_key else self._public_key
            key.verify(signature, message)
        except InvalidSignature:
            return False
        except (ValueError, TypeError) as exc:
            raise ValueError("malformed signature") from exc
        return True


def generate_identity() -> Identity:
    return Identity(Ed25519PrivateKey.generate())


def identity_from_public_encoded(value: str) -> Identity:
    return Identity.from_public_bytes(_unb64(value))
