"""Locally computed feed projection for the synchronized event log.

The projection is intentionally independent of Neo4j.  A peer can rebuild it
from any validated subset of events, and the result is therefore not part of
the wire protocol or a source of authority.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from backend.app.protocol.events import Event


_POST_EVENTS = {"post.created", "post.updated", "post.tombstoned"}
_FRIEND_ADD = {"friend.accepted"}
_FRIEND_REMOVE = {"friend.removed"}
_MEMBERSHIP_ADD = {
    "camp.membership.added",
    "camp.membership.requested",
    "group.membership.added",
}
_MEMBERSHIP_REMOVE = {"camp.membership.removed", "group.membership.removed"}


def _value(payload: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in payload:
            return payload[name]
    return default


def _members(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return the two users in a relationship payload, in stable order."""
    left = _value(payload, "user_a", "from_user_id", "requester_id")
    right = _value(payload, "user_b", "to_user_id", "target_user_id")
    return left, right


def _event_sort_key(event: Event) -> tuple[str, str]:
    return event.created_at, event.event_id


def _as_event(value: Event | dict[str, Any]) -> Event:
    if isinstance(value, Event):
        return value
    return Event.from_dict(value)


@dataclass
class _PostState:
    post_id: str
    author_id: str
    created_at: str
    content: str
    visibility: str
    scope_id: str | None
    image_url: str | None = None
    event_id: str | None = None
    tombstoned: bool = False
    updated_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        # sort_key is opaque to callers but makes cursor pagination stable even
        # when two posts have the same timestamp.
        return {
            "post_id": self.post_id,
            "author_id": self.author_id,
            "content": self.content,
            "visibility": self.visibility,
            "scope_id": self.scope_id,
            "image_url": self.image_url,
            "event_id": self.event_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "sort_key": f"{self.created_at}|{self.post_id}",
        }


class FeedProjection:
    """Rebuild and query a feed from signed, validated domain events.

    Events are deduplicated by ``event_id``.  Updates and tombstones are
    ordered by their event timestamp and ID, so peers that receive the same
    events in different batches converge to the same result.
    """

    def __init__(self, events: Iterable[Event | dict[str, Any]] = ()) -> None:
        parsed = [_as_event(item) for item in events]
        unique = {event.event_id: event for event in parsed}
        self.events = tuple(sorted(unique.values(), key=_event_sort_key))

    def _state(self) -> tuple[dict[str, _PostState], set[tuple[str, str]], set[tuple[str, str]]]:
        posts: dict[str, _PostState] = {}
        friends: set[tuple[str, str]] = set()
        memberships: set[tuple[str, str]] = set()

        for event in self.events:
            payload = event.payload
            if event.event_type in _FRIEND_ADD | _FRIEND_REMOVE:
                left, right = _members(payload)
                if not left or not right:
                    continue
                relationship = tuple(sorted((left, right)))
                if event.event_type in _FRIEND_ADD:
                    friends.add(relationship)
                else:
                    friends.discard(relationship)
                continue

            if event.event_type in _MEMBERSHIP_ADD | _MEMBERSHIP_REMOVE:
                user_id = _value(payload, "user_id", "member_id")
                scope_id = _value(payload, "camp_id", "group_id")
                if not user_id or not scope_id:
                    continue
                membership = (user_id, scope_id)
                if event.event_type in _MEMBERSHIP_ADD:
                    memberships.add(membership)
                else:
                    memberships.discard(membership)
                continue

            if event.event_type not in _POST_EVENTS:
                continue

            if event.event_type == "post.created":
                author_id = _value(payload, "author_id", "user_id", default=event.author)
                posts[event.object_id] = _PostState(
                    post_id=event.object_id,
                    author_id=author_id,
                    created_at=event.created_at,
                    content=_value(payload, "content", "body", default=""),
                    visibility=_value(payload, "visibility", default="public"),
                    scope_id=_value(payload, "scope_id", "camp_id", "group_id"),
                    image_url=_value(payload, "image_url"),
                    event_id=_value(payload, "event_id"),
                )
            elif event.object_id in posts:
                post = posts[event.object_id]
                if event.event_type == "post.tombstoned":
                    post.tombstoned = True
                    post.updated_at = event.created_at
                else:
                    for field, names in {
                        "content": ("content", "body"),
                        "image_url": ("image_url",),
                        "visibility": ("visibility",),
                        "scope_id": ("scope_id", "camp_id", "group_id"),
                    }.items():
                        value = _value(payload, *names)
                        if value is not None:
                            setattr(post, field, value)
                    post.updated_at = event.created_at
        return posts, friends, memberships

    def feed_for(
        self,
        viewer_id: str,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if limit < 1:
            return []
        posts, friends, memberships = self._state()
        visible = [
            post for post in posts.values()
            if not post.tombstoned
            and _is_visible(post, viewer_id, friends, memberships)
            and (cursor is None or post.as_dict()["sort_key"] < cursor)
        ]
        visible.sort(key=lambda post: post.post_id)
        visible.sort(key=lambda post: post.created_at, reverse=True)
        return [post.as_dict() for post in visible[:limit]]


def _is_visible(
    post: _PostState,
    viewer_id: str,
    friends: set[tuple[str, str]],
    memberships: set[tuple[str, str]],
) -> bool:
    if post.author_id == viewer_id or post.visibility == "public":
        return True
    if post.visibility in {"private", "compatibility"}:
        return False
    if post.visibility == "social":
        return tuple(sorted((viewer_id, post.author_id))) in friends
    if post.visibility in {"camp", "group", "group/camp"}:
        return bool(post.scope_id and (viewer_id, post.scope_id) in memberships)
    return False


def project_feed(
    events: Iterable[Event | dict[str, Any]],
    viewer_id: str,
    *,
    cursor: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Convenience wrapper for rebuilding and querying one local feed."""
    return FeedProjection(events).feed_for(viewer_id, cursor=cursor, limit=limit)
