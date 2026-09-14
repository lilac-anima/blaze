import pytest

from backend.app.protocol.identity import Identity, generate_identity


def test_identity_sign_verify_and_round_trip() -> None:
    identity = generate_identity()
    message = b"signed event"
    signature = identity.sign(message)
    assert identity.verify(message, signature)
    assert not identity.verify(b"tampered", signature)
    restored = Identity.from_private_bytes(identity.private_bytes())
    assert restored.public_bytes() == identity.public_bytes()
    assert restored.verify(message, signature)


def test_identity_rejects_wrong_signature() -> None:
    identity = generate_identity()
    assert not identity.verify(b"message", b"bad")
