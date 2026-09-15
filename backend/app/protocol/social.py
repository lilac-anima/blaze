"""Signed social events and a deterministic local projection.

This module is the peer-side boundary for comments and post reactions.  The
Neo4j HTTP routes remain compatibility code; peers exchange Event envelopes,
never database rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .events import Event, EventValidationError
from .identity import Identity


SOCIAL_EVENT_TYPES = frozenset(
    {"post.created", "comment.created", "post.liked", "post.unliked"}
)


class EventRejected(ValueError):
    """An event cannot be accepted or projected by this replica."""


@dataclass(frozen=True)
class ReceiveResult:
    status: str
    event_id: str


@dataclass(frozen=True)
class Comment:
    comment_id: str
    post_id: str
    author: str
    content: str
    created_at: str
    event_id: str


@dataclass(frozen=True)
class _Reaction:
    liked: bool
    created_at: str
    event_id: str


class SocialEventFactory:
    """Construct the protocol events owned by this slice."""

    @staticmethod
    def post_created(
        identity: Identity, post_id: str, content: str, created_at: str
    ) -> Event:
        return Event.create(identity, "post.created", post_id, created_at, {"content": content})

    @staticmethod
    def comment_created(
        identity: Identity,
        comment_id: str,
        post_id: str,
        content: str,
        created_at: str,
        parents: tuple[str, ...] = (),
    ) -> Event:
        return Event.create(
            identity,
            "comment.created",
            comment_id,
            created_at,
            {"post_id": post_id, "content": content},
            parents,
        )

    @staticmethod
    def liked(
        identity: Identity,
        post_id: str,
        created_at: str,
        parents: tuple[str, ...] = (),
    ) -> Event:
        return SocialEventFactory._reaction(identity, "post.liked", post_id, created_at, parents)

    @staticmethod
    def unliked(
        identity: Identity,
        post_id: str,
        created_at: str,
        parents: tuple[str, ...] = (),
    ) -> Event:
        return SocialEventFactory._reaction(identity, "post.unliked", post_id, created_at, parents)

    @staticmethod
    def _reaction(
        identity: Identity,
        event_type: str,
        post_id: str,
        created_at: str,
        parents: tuple[str, ...],
    ) -> Event:
        # The author + post pair is the reaction's LWW stream.  Using it as the
        # object ID makes repeated like/unlike deliveries naturally idempotent.
        object_id = f"{post_id}:{identity.public_key_encoded()}"
        return Event.create(identity, event_type, object_id, created_at, {"post_id": post_id}, parents)


class SocialProjection:
    """Rebuildable, deterministic read model for posts, comments, and likes."""

    def __init__(self) -> None:
        self._posts: dict[str, str] = {}
        self._comments: dict[str, Comment] = {}
        self._reactions: dict[tuple[str, str], _Reaction] = {}

    def apply(self, event: Event) -> None:
        if event.event_type not in SOCIAL_EVENT_TYPES:
            raise EventRejected(f"unsupported social event: {event.event_type}")
        if event.event_type == "post.created":
            content = event.payload.get("content")
            if not isinstance(content, str):
                raise EventRejected("post.created content must be a string")
            # Same object ID is immutable; equal duplicate events are handled by
            # the event store before projection.
            existing = self._posts.get(event.object_id)
            if existing is not None and existing != content:
                raise EventRejected("conflicting post.created")
            self._posts[event.object_id] = content
            return

        post_id = event.payload.get("post_id")
        if not isinstance(post_id, str) or post_id not in self._posts:
            raise EventRejected("unknown post")

        if event.event_type == "comment.created":
            content = event.payload.get("content")
            if not isinstance(content, str):
                raise EventRejected("comment.created content must be a string")
            self._comments.setdefault(
                event.object_id,
                Comment(event.object_id, post_id, event.author, content, event.created_at, event.event_id),
            )
            return

        key = (post_id, event.author)
        candidate = _Reaction(event.event_type == "post.liked", event.created_at, event.event_id)
        current = self._reactions.get(key)
        if current is None or (candidate.created_at, candidate.event_id) > (
            current.created_at,
            current.event_id,
        ):
            self._reactions[key] = candidate

    def comments_for(self, post_id: str) -> tuple[Comment, ...]:
        return tuple(sorted((c for c in self._comments.values() if c.post_id == post_id), key=lambda c: (c.created_at, c.event_id)))

    def liked_by(self, post_id: str) -> tuple[str, ...]:
        return tuple(sorted(author for (target, author), reaction in self._reactions.items() if target == post_id and reaction.liked))

    def like_count(self, post_id: str) -> int:
        return len(self.liked_by(post_id))

    def snapshot(self) -> dict[str, Any]:
        return {
            "posts": dict(sorted(self._posts.items())),
            "comments": [c.__dict__ for c in self.comments_for_all()],
            "likes": [
                {"post_id": post_id, "author": author, "liked": reaction.liked,
                 "created_at": reaction.created_at, "event_id": reaction.event_id}
                for (post_id, author), reaction in sorted(self._reactions.items())
            ],
        }

    def comments_for_all(self) -> tuple[Comment, ...]:
        return tuple(sorted(self._comments.values(), key=lambda c: (c.post_id, c.created_at, c.event_id)))


class LocalEventStore:
    """Append-only validated event log with pending-parent handling."""

    def __init__(self) -> None:
        self._events: dict[str, Event] = {}
        self._pending: dict[str, Event] = {}
        self.projection = SocialProjection()

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(self._events.values())

    @property
    def pending(self) -> tuple[Event, ...]:
        return tuple(self._pending.values())

    def receive(self, event: Event | dict[str, Any]) -> ReceiveResult:
        try:
            parsed = event if isinstance(event, Event) else Event.from_dict(event)
            if parsed.event_type not in SOCIAL_EVENT_TYPES:
                raise EventRejected(f"unsupported social event: {parsed.event_type}")
            parsed.verify()
        except (EventValidationError, ValueError) as exc:
            if isinstance(exc, EventRejected):
                raise
            raise EventRejected(str(exc)) from exc

        if parsed.event_id in self._events:
            return ReceiveResult("duplicate", parsed.event_id)
        if parsed.event_id in self._pending:
            return ReceiveResult("duplicate", parsed.event_id)

        missing = [parent for parent in parsed.parents if parent not in self._events]
        if missing:
            self._pending[parsed.event_id] = parsed
            return ReceiveResult("missing_parent", parsed.event_id)

        self._accept(parsed)
        self._drain_pending()
        return ReceiveResult("accepted", parsed.event_id)

    def _accept(self, event: Event) -> None:
        try:
            self.projection.apply(event)
        except EventRejected:
            raise
        self._events[event.event_id] = event

    def _drain_pending(self) -> None:
        changed = True
        while changed:
            changed = False
            for event_id, event in list(self._pending.items()):
                if all(parent in self._events for parent in event.parents):
                    self._accept(event)
                    del self._pending[event_id]
                    changed = True

    def export(self) -> tuple[dict[str, Any], ...]:
        return tuple(event.to_dict() for event in self._events.values())
