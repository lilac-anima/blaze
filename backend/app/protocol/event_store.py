"""Event-backed local storage and deterministic event projection for the event slice.

The compatibility Neo4j routes remain unchanged.  This module is the peer-side
boundary: only verified signed events are stored, and the read model is rebuilt
from those events rather than being treated as wire data.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Iterable

from .events import Event, EventValidationError


class ProjectionError(ValueError):
    pass


class AuthorizationError(ProjectionError):
    pass


class MissingParent(ProjectionError):
    pass


class DuplicateEvent(ProjectionError):
    pass


@dataclass
class EventRecord:
    event_id: str
    name: str
    date: str | None = None
    location_on_playa: str | None = None
    camp: str | None = None
    description: str | None = None
    max_attendees: int | None = None
    created_by: str = ""
    tombstoned: bool = False
    tombstone_reason: str | None = None
    rsvps: dict[str, str] = field(default_factory=dict)
    organizers: set[str] = field(default_factory=set)
    _field_versions: dict[str, tuple[str, str]] = field(default_factory=dict, repr=False)


class EventProjector:
    """Apply event-slice events to an in-memory read model.

    Authorization is object scoped: the creator and currently granted organizers
    may mutate event metadata or roles; an RSVP author may only change their own
    RSVP.  Concurrent metadata writes use a deterministic (timestamp, event ID)
    last-writer-wins tie-breaker.
    """

    EVENT_TYPES = {
        "event.created", "event.updated", "event.tombstoned",
        "event.rsvp.updated", "event.role.granted", "event.role.revoked",
    }
    RSVP_STATUSES = {"going", "maybe", "not going"}

    def __init__(self) -> None:
        self.events: dict[str, EventRecord] = {}
        self.applied_ids: set[str] = set()

    def apply(self, event: Event) -> None:
        if event.event_id in self.applied_ids:
            raise DuplicateEvent(event.event_id)
        if event.event_type not in self.EVENT_TYPES:
            raise ProjectionError(f"unsupported event type: {event.event_type}")
        for parent in event.parents:
            if parent not in self.applied_ids:
                raise MissingParent(parent)
        handler = getattr(self, "_" + event.event_type.replace(".", "_"))
        handler(event)
        self.applied_ids.add(event.event_id)

    def _event_created(self, event: Event) -> None:
        if event.object_id in self.events:
            raise ProjectionError("event already exists")
        payload = event.payload
        if not isinstance(payload.get("name"), str) or not payload["name"]:
            raise ProjectionError("event.created requires a name")
        record = EventRecord(
            event_id=event.object_id,
            name=payload["name"],
            date=payload.get("date"),
            location_on_playa=payload.get("location_on_playa"),
            camp=payload.get("camp"),
            description=payload.get("description"),
            max_attendees=payload.get("max_attendees"),
            created_by=event.author,
            organizers={event.author},
        )
        self.events[event.object_id] = record

    def _record_for_mutation(self, event: Event) -> EventRecord:
        record = self.events.get(event.object_id)
        if record is None:
            raise ProjectionError("event does not exist")
        if record.tombstoned:
            raise AuthorizationError("tombstoned event cannot be mutated")
        if event.author not in record.organizers:
            raise AuthorizationError("author is not an event organizer")
        return record

    def _event_updated(self, event: Event) -> None:
        record = self._record_for_mutation(event)
        fields = {"name", "date", "location_on_playa", "camp", "description", "max_attendees"}
        for field_name, value in event.payload.items():
            if field_name not in fields:
                raise ProjectionError(f"unknown event field: {field_name}")
            version = (event.created_at, event.event_id)
            if version > record._field_versions.get(field_name, ("", "")):
                setattr(record, field_name, value)
                record._field_versions[field_name] = version

    def _event_tombstoned(self, event: Event) -> None:
        record = self._record_for_mutation(event)
        record.tombstoned = True
        record.tombstone_reason = event.payload.get("reason")

    def _event_rsvp_updated(self, event: Event) -> None:
        record = self.events.get(event.object_id)
        if record is None or record.tombstoned:
            raise ProjectionError("event does not exist or is tombstoned")
        user_id = event.payload.get("user_id")
        status = event.payload.get("status")
        if user_id != event.author:
            raise AuthorizationError("RSVP author may only update their own RSVP")
        if status not in self.RSVP_STATUSES:
            raise ProjectionError("invalid RSVP status")
        record.rsvps[user_id] = status
        if user_id == record.created_by:
            record.organizers.add(user_id)

    def _event_role_granted(self, event: Event) -> None:
        record = self._record_for_mutation(event)
        user_id = event.payload.get("user_id")
        if event.payload.get("role") != "organizer" or user_id not in record.rsvps:
            raise ProjectionError("organizer grant requires an RSVP and organizer role")
        record.organizers.add(user_id)

    def _event_role_revoked(self, event: Event) -> None:
        record = self._record_for_mutation(event)
        user_id = event.payload.get("user_id")
        if user_id == record.created_by:
            raise AuthorizationError("event creator cannot be demoted")
        record.organizers.discard(user_id)


class EventStore:
    """Durable local event log with idempotent receive and parent retry."""

    def __init__(self, path: str = ":memory:") -> None:
        self._db = sqlite3.connect(path)
        self._db.execute("CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY, data TEXT NOT NULL)")
        self._db.commit()
        self.projector = EventProjector()
        self._pending: dict[str, Event] = {}
        self._load()

    @property
    def pending_ids(self) -> set[str]:
        return set(self._pending)

    def _load(self) -> None:
        rows = self._db.execute("SELECT data FROM events ORDER BY rowid").fetchall()
        for (data,) in rows:
            event = Event.from_dict(json.loads(data))
            try:
                self.projector.apply(event)
            except MissingParent:
                self._pending[event.event_id] = event

    def append(self, event: Event) -> str:
        if not event.verify():
            raise EventValidationError("invalid event signature")
        if self._db.execute("SELECT 1 FROM events WHERE event_id = ?", (event.event_id,)).fetchone():
            return "duplicate"
        self._db.execute("INSERT INTO events(event_id, data) VALUES (?, ?)", (event.event_id, json.dumps(event.to_dict(), sort_keys=True)))
        self._db.commit()
        self._pending[event.event_id] = event
        applied = self._drain()
        return "accepted" if event.event_id in applied else "pending"

    def _drain(self) -> set[str]:
        applied: set[str] = set()
        progress = True
        while progress:
            progress = False
            for event_id, event in list(self._pending.items()):
                try:
                    self.projector.apply(event)
                except MissingParent:
                    continue
                except DuplicateEvent:
                    del self._pending[event_id]
                    continue
                del self._pending[event_id]
                applied.add(event_id)
                progress = True
        return applied

    def receive(self, data: Iterable[dict[str, Any]]) -> dict[str, int]:
        counts = {"accepted": 0, "duplicate": 0, "rejected": 0}
        for raw in data:
            try:
                event = Event.from_dict(raw)
                before = set(self.projector.applied_ids)
                result = self.append(event)
                if result == "duplicate":
                    counts["duplicate"] += 1
                counts["accepted"] += len(self.projector.applied_ids - before)
            except (EventValidationError, ProjectionError):
                counts["rejected"] += 1
        # A parent can make previously pending children applicable.
        self._drain()
        return counts

    def export(self) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT data FROM events ORDER BY rowid").fetchall()
        return [json.loads(data) for (data,) in rows]

    def close(self) -> None:
        self._db.close()
