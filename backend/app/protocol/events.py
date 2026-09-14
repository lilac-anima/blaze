"""Version 1 signed event envelope."""

from __future__ import annotations

import base64
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .canonical import canonical_json
from .identity import Identity, identity_from_public_encoded

PROTOCOL_VERSION = 1
MAX_EVENT_BYTES = 128_000
MAX_PAYLOAD_BYTES = 100_000
_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")


class EventValidationError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True)
class Event:
    protocol_version: int
    event_id: str
    event_type: str
    author: str
    object_id: str
    created_at: str
    payload: dict[str, Any]
    parents: tuple[str, ...]
    signature: str

    @classmethod
    def create(cls, identity: Identity, event_type: str, object_id: str, created_at: str, payload: dict[str, Any], parents: tuple[str, ...] = ()) -> "Event":
        author = identity.public_key_encoded()
        unsigned = {"protocol_version": 1, "event_type": event_type, "author": author, "object_id": object_id, "created_at": created_at, "payload": payload, "parents": list(parents)}
        event_id = hashlib.sha256(canonical_json(unsigned)).hexdigest()
        signature = _b64(identity.sign(canonical_json({"event_id": event_id, **unsigned})))
        return cls(1, event_id, event_type, author, object_id, created_at, payload, tuple(parents), signature)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        try:
            required = ("protocol_version", "event_id", "event_type", "author", "object_id", "created_at", "payload", "parents", "signature")
            if set(data) != set(required) or data["protocol_version"] != PROTOCOL_VERSION:
                raise EventValidationError("invalid or unsupported event version/fields")
            if not isinstance(data["payload"], dict) or not isinstance(data["parents"], list):
                raise EventValidationError("payload and parents must be objects/lists")
            event = cls(data["protocol_version"], data["event_id"], data["event_type"], data["author"], data["object_id"], data["created_at"], data["payload"], tuple(data["parents"]), data["signature"])
            event._validate()
            if len(canonical_json(data)) > MAX_EVENT_BYTES:
                raise EventValidationError("event exceeds size limit")
            return event
        except EventValidationError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise EventValidationError("malformed event") from exc

    def _unsigned(self) -> dict[str, Any]:
        return {"protocol_version": self.protocol_version, "event_type": self.event_type, "author": self.author, "object_id": self.object_id, "created_at": self.created_at, "payload": self.payload, "parents": list(self.parents)}

    def _validate(self) -> None:
        if not all(isinstance(x, str) and _ID_RE.fullmatch(x) for x in (self.event_type, self.object_id, self.event_id)):
            raise EventValidationError("invalid identifier")
        if not isinstance(self.author, str) or not isinstance(self.signature, str) or len(self.signature) > 256:
            raise EventValidationError("invalid identity or signature")
        try:
            datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
            identity_from_public_encoded(self.author)
            if len(canonical_json(self.payload)) > MAX_PAYLOAD_BYTES:
                raise EventValidationError("payload exceeds size limit")
        except EventValidationError:
            raise
        except (ValueError, TypeError) as exc:
            raise EventValidationError("invalid timestamp, key, or payload") from exc

    def signing_bytes(self) -> bytes:
        return canonical_json({"event_id": self.event_id, **self._unsigned()})

    def verify(self) -> bool:
        expected_id = hashlib.sha256(canonical_json(self._unsigned())).hexdigest()
        if expected_id != self.event_id:
            raise EventValidationError("event ID mismatch")
        try:
            return identity_from_public_encoded(self.author).verify(self.signing_bytes(), _unb64(self.signature))
        except (ValueError, TypeError) as exc:
            raise EventValidationError("invalid signature") from exc

    def to_dict(self) -> dict[str, Any]:
        return {**self._unsigned(), "event_id": self.event_id, "signature": self.signature}
