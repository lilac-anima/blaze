"""Signed friend-request events and a deterministic local friendship projection."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .events import Event, EventValidationError
from .identity import Identity


class FriendshipEventError(ValueError):
    pass


def friend_event(identity: Identity, event_type: str, object_id: str, created_at: str,
                 payload: dict[str, Any], parents: tuple[str, ...] = ()) -> Event:
    return Event.create(identity, event_type, object_id, created_at, payload, parents)


def _key(a: str, b: str) -> str:
    if not a or not b or a == b:
        raise FriendshipEventError("invalid friendship participants")
    return ":".join(sorted((a, b)))


@dataclass
class _Request:
    request_id: str
    from_user_id: str
    to_user_id: str
    status: str
    event_id: str


class FriendshipProjection:
    def __init__(self, authors: dict[str, str]):
        self.authors = dict(authors)
        self.requests: dict[str, _Request] = {}
        self.friendships: dict[str, str] = {}
        self.event_ids: set[str] = set()
        self._pending: dict[str, Event] = {}
        self._known: dict[str, Event] = {}

    def apply(self, value: Event | dict[str, Any]) -> str:
        try:
            event = value if isinstance(value, Event) else Event.from_dict(value)
            event.verify()
            self._authorize(event)
        except EventValidationError:
            raise
        except (FriendshipEventError, ValueError) as exc:
            raise FriendshipEventError(str(exc)) from exc
        if event.event_id in self.event_ids:
            return "applied"
        if event.event_id in self._pending:
            return "duplicate"
        self._known[event.event_id] = event
        if any(parent not in self.event_ids for parent in event.parents) or (
            event.event_type in {"friend.accepted", "friend.rejected"}
            and event.payload.get("request_id") not in self.requests
        ):
            self._pending[event.event_id] = event
            return "deferred"
        self._apply_ready(event)
        self.event_ids.add(event.event_id)
        self._drain()
        return "applied"

    def _authorize(self, event: Event) -> None:
        if event.event_type not in {"friend.requested", "friend.accepted", "friend.rejected", "friend.removed"}:
            raise FriendshipEventError("unsupported friendship event")
        payload = event.payload
        author = event.author
        if event.event_type == "friend.requested":
            if (payload.get("from_user_id") not in self.authors or
                self.authors[payload.get("from_user_id")] != author or
                payload.get("to_user_id") == payload.get("from_user_id") or
                event.object_id != payload.get("request_id")):
                raise FriendshipEventError("request author is not the sender")
        elif event.event_type in {"friend.accepted", "friend.rejected"}:
            if (payload.get("to_user_id") not in self.authors or
                self.authors[payload.get("to_user_id")] != author or
                event.object_id != payload.get("request_id")):
                raise FriendshipEventError("only the request recipient may change its state")
        else:
            left = payload.get("user_a", payload.get("from_user_id"))
            right = payload.get("user_b", payload.get("to_user_id"))
            if (left not in self.authors or right not in self.authors or
                self.authors[left] != author or payload.get("friendship_id", event.object_id) != f"friendship:{_key(left, right)}" or
                event.object_id != payload.get("friendship_id", event.object_id)):
                raise FriendshipEventError("only a friend may remove the friendship")

    def _apply_ready(self, event: Event) -> None:
        p = event.payload
        if event.event_type == "friend.requested":
            self.requests[event.object_id] = _Request(event.object_id, p["from_user_id"], p["to_user_id"], "pending", event.event_id)
        elif event.event_type in {"friend.accepted", "friend.rejected"}:
            request = self.requests.get(p["request_id"])
            if not request or request.status != "pending":
                raise FriendshipEventError("request does not exist or is already resolved")
            request.status = "accepted" if event.event_type == "friend.accepted" else "rejected"
            request.event_id = event.event_id
            if request.status == "accepted": self.friendships[f"friendship:{_key(request.from_user_id, request.to_user_id)}"] = "active"
        else:
            self.friendships[event.object_id] = "removed"

    def _drain(self) -> None:
        progress = True
        while progress:
            progress = False
            for event_id, event in sorted(list(self._pending.items()), key=lambda item: (item[1].created_at, item[0])):
                if all(parent in self.event_ids for parent in event.parents) and not (
                    event.event_type in {"friend.accepted", "friend.rejected"}
                    and event.payload.get("request_id") not in self.requests
                ):
                    del self._pending[event_id]
                    try:
                        self._apply_ready(event)
                        self.event_ids.add(event_id)
                    except FriendshipEventError:
                        self._known.pop(event_id, None)
                    progress = True

    def friends(self, user_id: str) -> set[str]:
        return {part for friendship, status in self.friendships.items() if status == "active" for part in friendship.removeprefix("friendship:").split(":") if part != user_id}

    def request_status(self, request_id: str) -> str | None:
        return self.requests.get(request_id).status if request_id in self.requests else None

    def friendship_status(self, user_a: str, user_b: str) -> str | None:
        return self.friendships.get(f"friendship:{_key(user_a, user_b)}")

    def snapshot(self) -> dict[str, Any]:
        return {
            "requests": {key: vars(value).copy() for key, value in sorted(self.requests.items())},
            "friendships": dict(sorted(self.friendships.items())),
        }
