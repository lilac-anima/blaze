"""Signed, mergeable group events and a local read-model projection.

Group state is derived exclusively from the event log.  Event authors are Ed25519
keys; the user IDs in payloads are application identifiers and are bound to the
key by ``actor_author``.  This keeps the protocol usable by offline peers while
letting the centralized API expose the same model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

from .events import Event, EventValidationError
from .identity import Identity

GROUP_CREATED = "group.created"
GROUP_UPDATED = "group.updated"
GROUP_TOMBSTONED = "group.tombstoned"
GROUP_MEMBER_JOINED = "group.member_joined"
GROUP_MEMBER_LEFT = "group.member_left"
GROUP_ROLE_CHANGED = "group.role_changed"
ROLES = frozenset({"owner", "admin", "moderator", "member"})


@dataclass(frozen=True)
class GroupMember:
    user_id: str
    role: str
    author: str
    joined_at: str


@dataclass
class GroupState:
    group_id: str
    name: str
    description: str | None
    is_public: bool
    created_by: str
    creator_author: str
    created_at: str
    updated_at: str
    members: dict[str, GroupMember] = field(default_factory=dict)
    deleted: bool = False


class GroupProjection:
    """Validate and apply group events to a deterministic local read model."""

    def __init__(self) -> None:
        self.groups: dict[str, GroupState] = {}
        self.tombstones: dict[str, str] = {}
        self.event_ids: set[str] = set()
        self.rejected_ids: set[str] = set()
        self._known: dict[str, Event] = {}
        self._pending: dict[str, Event] = {}

    def apply(self, value: Event | dict[str, Any]) -> bool:
        try:
            event = value if isinstance(value, Event) else Event.from_dict(value)
            if not event.verify() or event.event_type not in {
                GROUP_CREATED, GROUP_UPDATED, GROUP_TOMBSTONED,
                GROUP_MEMBER_JOINED, GROUP_MEMBER_LEFT, GROUP_ROLE_CHANGED,
            }:
                return False
        except (EventValidationError, TypeError, ValueError):
            return False
        if event.event_id in self.event_ids or event.event_id in self.rejected_ids or event.event_id in self._pending:
            return False
        self._known[event.event_id] = event
        if any(parent not in self.event_ids for parent in event.parents):
            self._pending[event.event_id] = event
            return False
        if not self._apply_ready(event):
            self._known.pop(event.event_id, None)
            return False
        self.event_ids.add(event.event_id)
        self._drain_pending()
        return True

    def _drain_pending(self) -> None:
        progress = True
        while progress:
            progress = False
            for event_id, event in sorted(self._pending.items(), key=lambda item: _event_key(item[1])):
                if not all(parent in self.event_ids for parent in event.parents):
                    continue
                del self._pending[event_id]
                if self._apply_ready(event):
                    self.event_ids.add(event_id)
                else:
                    self._known.pop(event_id, None)
                    self.rejected_ids.add(event_id)
                progress = True

    def _apply_ready(self, event: Event) -> bool:
        payload = event.payload
        if payload.get("actor_author") != event.author:
            return False
        if event.event_type == GROUP_CREATED:
            if event.object_id in self.groups or event.object_id in self.tombstones:
                return False
            if payload.get("created_by") != payload.get("actor_user_id"):
                return False
            self.groups[event.object_id] = GroupState(
                group_id=event.object_id,
                name=payload.get("name", ""),
                description=payload.get("description"),
                is_public=bool(payload.get("is_public", True)),
                created_by=payload["created_by"],
                creator_author=event.author,
                created_at=event.created_at,
                updated_at=event.created_at,
                members={payload["created_by"]: GroupMember(payload["created_by"], "owner", event.author, event.created_at)},
            )
            return True

        group = self.groups.get(event.object_id)
        if group is None or group.deleted:
            return False
        actor = payload.get("actor_user_id")
        member = group.members.get(actor)
        if event.event_type == GROUP_UPDATED:
            if not _can_manage(group, actor, event.author):
                return False
            if _newer(event.created_at, event.event_id, group.updated_at, ""):
                for key in ("name", "description", "is_public"):
                    if key in payload:
                        setattr(group, key, payload[key])
                group.updated_at = event.created_at
            return True
        if event.event_type == GROUP_TOMBSTONED:
            if not _can_manage(group, actor, event.author):
                return False
            group.deleted = True
            self.tombstones[event.object_id] = event.event_id
            return True
        target = payload.get("user_id")
        target_author = payload.get("user_author")
        if not isinstance(target, str) or target_author != (event.author if event.event_type in {GROUP_MEMBER_JOINED, GROUP_MEMBER_LEFT} else target_author):
            return False
        if event.event_type == GROUP_MEMBER_JOINED:
            if target != actor or target_author != event.author:
                return False
            if not group.is_public and not _can_manage(group, actor, event.author):
                return False
            if target in group.members:
                return False
            group.members[target] = GroupMember(target, "member", event.author, event.created_at)
            return True
        if event.event_type == GROUP_MEMBER_LEFT:
            if target != actor or target_author != event.author:
                return False
            if target == group.created_by:
                return False
            if target not in group.members:
                return False
            del group.members[target]
            return True
        if event.event_type == GROUP_ROLE_CHANGED:
            if not _can_change_role(group, actor, event.author) or target not in group.members:
                return False
            role = payload.get("role")
            if role not in ROLES or (target == group.created_by and role != "owner"):
                return False
            group.members[target] = GroupMember(target, role, target_author or group.members[target].author, event.created_at)
            return True
        return False

    def group(self, group_id: str) -> GroupState | None:
        group = self.groups.get(group_id)
        return None if group is None or group.deleted else group

    def members(self, group_id: str) -> list[GroupMember]:
        group = self.group(group_id)
        return sorted(group.members.values(), key=lambda member: (member.role, member.user_id)) if group else []

    def export(self) -> list[dict[str, Any]]:
        return [self._known[event_id].to_dict() for event_id in sorted(self.event_ids)]


class GroupEventStore:
    """Small local event store used by clients and two-peer synchronization."""

    def __init__(self) -> None:
        self.projection = GroupProjection()

    def ingest(self, event: Event | dict[str, Any]) -> bool:
        return self.projection.apply(event)

    def export(self) -> list[dict[str, Any]]:
        return self.projection.export()

    def sync(self, events: Iterable[Event | dict[str, Any]]) -> int:
        before = len(self.projection.event_ids)
        for event in events:
            self.ingest(event)
        return len(self.projection.event_ids) - before


def _event(identity: Identity, event_type: str, group_id: str, payload: dict[str, Any], created_at: str, parents: tuple[str, ...] = ()) -> Event:
    payload = {**payload, "actor_author": identity.public_key_encoded()}
    return Event.create(identity, event_type, group_id, created_at, payload, parents)


def create_group(identity: Identity, group_id: str, name: str, description: str | None, is_public: bool, user_id: str, created_at: str, parents: tuple[str, ...] = ()) -> Event:
    return _event(identity, GROUP_CREATED, group_id, {"name": name, "description": description, "is_public": is_public, "created_by": user_id, "actor_user_id": user_id}, created_at, parents)


def update_group(identity: Identity, group_id: str, changes: dict[str, Any], user_id: str, created_at: str, parents: tuple[str, ...] = ()) -> Event:
    allowed = {key: value for key, value in changes.items() if key in {"name", "description", "is_public"}}
    return _event(identity, GROUP_UPDATED, group_id, {**allowed, "actor_user_id": user_id}, created_at, parents)


def tombstone_group(identity: Identity, group_id: str, user_id: str, created_at: str, parents: tuple[str, ...] = ()) -> Event:
    return _event(identity, GROUP_TOMBSTONED, group_id, {"actor_user_id": user_id}, created_at, parents)


def join_group(identity: Identity, group_id: str, user_id: str, created_at: str, parents: tuple[str, ...] = ()) -> Event:
    return _event(identity, GROUP_MEMBER_JOINED, group_id, {"actor_user_id": user_id, "user_id": user_id, "user_author": identity.public_key_encoded()}, created_at, parents)


def leave_group(identity: Identity, group_id: str, user_id: str, created_at: str, parents: tuple[str, ...] = ()) -> Event:
    return _event(identity, GROUP_MEMBER_LEFT, group_id, {"actor_user_id": user_id, "user_id": user_id, "user_author": identity.public_key_encoded()}, created_at, parents)


def change_role(identity: Identity, group_id: str, actor_user_id: str, target_user_id: str, target_author: str, role: str, created_at: str, parents: tuple[str, ...] = ()) -> Event:
    return _event(identity, GROUP_ROLE_CHANGED, group_id, {"actor_user_id": actor_user_id, "user_id": target_user_id, "user_author": target_author, "role": role}, created_at, parents)


def _can_manage(group: GroupState, user_id: str | None, author: str) -> bool:
    member = group.members.get(user_id)
    return bool(member and member.author == author and member.role in {"owner", "admin", "moderator"})


def _can_change_role(group: GroupState, user_id: str | None, author: str) -> bool:
    member = group.members.get(user_id)
    return bool(member and member.author == author and member.role in {"owner", "admin"})


def _event_key(event: Event) -> tuple[str, str]:
    return event.created_at, event.event_id


def _newer(created_at: str, event_id: str, old_created_at: str, old_event_id: str) -> bool:
    try:
        left = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        right = datetime.fromisoformat(old_created_at.replace("Z", "+00:00"))
        return (left, event_id) > (right, old_event_id)
    except ValueError:
        return (created_at, event_id) > (old_created_at, old_event_id)
