"""Pydantic models for the Blaze graph domain."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field
from pydantic.functional_validators import BeforeValidator


def _convert_neo4j_datetime(v):
    """Convert neo4j.time.DateTime to native Python datetime for Pydantic."""
    if v is not None and hasattr(v, "year") and hasattr(v, "nanosecond"):
        return datetime(
            v.year, v.month, v.day, v.hour, v.minute,
            int(v.second), int(v.nanosecond / 1000),
            tzinfo=v.tzinfo,
        )
    return v


# Reusable type for Neo4j datetime fields
Neo4jDT = Annotated[datetime | None, BeforeValidator(_convert_neo4j_datetime)]


# ── User ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: str
    display_name: str | None = None


class UserResponse(UserCreate):
    user_id: str
    created_at: Neo4jDT = None


class UserSearchResult(BaseModel):
    user_id: str
    username: str
    display_name: str | None = None
    burner_name: str | None = None
    home_camp: str | None = None
    is_friend: bool = False


# ── BurnerProfile ─────────────────────────────────────────────────────

class BurnerProfileCreate(BaseModel):
    user_id: str
    burner_name: str = Field(min_length=2, max_length=100)
    home_camp: str | None = None
    years_active: list[int] = []


class BurnerProfileResponse(BurnerProfileCreate):
    profile_id: str


# ── Friend Connections ────────────────────────────────────────────────

class FriendRequestSend(BaseModel):
    from_user_id: str
    to_user_id: str
    message: str | None = None


class FriendRequestAction(BaseModel):
    user_id: str
    request_id: str


class FriendRequestResponse(BaseModel):
    request_id: str
    from_user_id: str
    from_username: str
    from_display_name: str | None = None
    to_user_id: str
    to_username: str
    to_display_name: str | None = None
    status: str  # pending / accepted / rejected
    message: str | None = None
    created_at: Neo4jDT = None


class FriendResponse(BaseModel):
    user_id: str
    username: str
    display_name: str | None = None
    burner_name: str | None = None
    home_camp: str | None = None
    friends_since: str | None = None


# ── Event ─────────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    name: str
    date: str = Field(..., description="Event date (YYYY-MM-DD)")
    location_on_playa: str | None = None
    camp: str | None = None
    description: str | None = None
    max_attendees: int | None = None


class EventUpdate(BaseModel):
    name: str | None = None
    date: str | None = None
    location_on_playa: str | None = None
    camp: str | None = None
    description: str | None = None
    max_attendees: int | None = None


class EventResponse(BaseModel):
    event_id: str
    name: str
    date: str | None = None
    location_on_playa: str | None = None
    camp: str | None = None
    description: str | None = None
    max_attendees: int | None = None
    created_by: str | None = None
    created_at: Neo4jDT = None
    attendee_count: int = 0


class RSVPAction(BaseModel):
    user_id: str
    status: str = Field(..., pattern=r"^(going|maybe|not going)$")


class RSVPResponse(BaseModel):
    event_id: str
    user_id: str
    status: str
    updated_at: Neo4jDT = None


class AttendeeResponse(BaseModel):
    user_id: str
    username: str
    display_name: str | None = None
    rsvp_status: str
    role: str | None = None


class PromoteAction(BaseModel):
    user_id: str
    promoted_by: str


# ── Camp ──────────────────────────────────────────────────────────────

class CampCreate(BaseModel):
    name: str
    description: str | None = None
    location_on_playa: str | None = None
    event_id: str | None = None


class CampUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    location_on_playa: str | None = None
    event_id: str | None = None


class CampResponse(BaseModel):
    camp_id: str
    name: str
    description: str | None = None
    location_on_playa: str | None = None
    created_by: str | None = None
    created_at: Neo4jDT = None
    member_count: int = 0
    event_id: str | None = None
    event_name: str | None = None


class CampMemberResponse(BaseModel):
    user_id: str
    username: str
    display_name: str | None = None
    role: str = "member"


# ── Group ─────────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str
    description: str | None = None
    is_public: bool = True


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None


class GroupResponse(BaseModel):
    group_id: str
    name: str
    description: str | None = None
    is_public: bool = True
    created_by: str | None = None
    created_at: Neo4jDT = None
    member_count: int = 0


class GroupMemberResponse(BaseModel):
    user_id: str
    username: str
    display_name: str | None = None
    role: str = "member"


# ── Post ──────────────────────────────────────────────────────────────

class PostCreate(BaseModel):
    author_id: str
    content: str = Field(max_length=5000)
    image_url: str | None = None
    event_id: str | None = None


class PostUpdate(BaseModel):
    content: str | None = Field(None, max_length=5000)
    image_url: str | None = None


class PostResponse(BaseModel):
    post_id: str
    author_id: str
    author_username: str | None = None
    author_display_name: str | None = None
    content: str
    image_url: str | None = None
    event_id: str | None = None
    created_at: Neo4jDT = None
    like_count: int = 0
    comment_count: int = 0
    is_liked_by_me: bool = False


class LikeResponse(BaseModel):
    post_id: str
    user_id: str
    liked_at: Neo4jDT = None


class CommentCreate(BaseModel):
    user_id: str
    content: str = Field(max_length=2000)


class CommentResponse(BaseModel):
    comment_id: str
    post_id: str
    user_id: str
    username: str | None = None
    display_name: str | None = None
    content: str
    created_at: Neo4jDT = None


# ── Feed ──────────────────────────────────────────────────────────────

class FeedItem(BaseModel):
    post: PostResponse
    author: UserSearchResult | None = None


class FeedResponse(BaseModel):
    items: list[FeedItem]
    next_cursor: str | None = None
    total: int = 0


# ── Generic Responses ─────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    detail: str | None = None


class PromoteAction(BaseModel):
    """Action to promote/demote an attendee to/from organizer."""
    user_id: str
    promoted_by: str


# ── Health ────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    neo4j_connected: bool
    node_count: int = 0
    relationship_count: int = 0
