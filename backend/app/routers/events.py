"""Event CRUD, RSVP/attendance, promote to organizer, and event posts."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession
from backend.app.database import get_session
from backend.app.models import (
    AttendeeResponse,
    EventCreate,
    EventResponse,
    EventUpdate,
    MessageResponse,
    PostCreate,
    PostResponse,
    PromoteAction,
    RSVPAction,
    RSVPResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["Events"])


# ── Create Event ─────────────────────────────────────────────────────

@router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    event: EventCreate,
    created_by: str = Query(..., description="User ID of the creator"),
    session: AsyncSession = Depends(get_session),
):
    """Create a new event."""
    import uuid
    event_id = f"evt-{uuid.uuid4().hex[:8]}"

    # Verify creator exists
    creator_check = await session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u", uid=created_by
    )
    if not await creator_check.single():
        raise HTTPException(404, f"User {created_by} not found")

    await session.run(
        """
        MATCH (creator:User {user_id: $created_by})
        CREATE (e:Event {
            event_id: $event_id,
            name: $name,
            date: $date,
            location_on_playa: $location_on_playa,
            camp: $camp,
            description: $description,
            max_attendees: $max_attendees,
            created_by: $created_by,
            created_at: datetime()
        })
        CREATE (creator)-[:HOSTED_BY]->(e)
        """,
        created_by=created_by,
        event_id=event_id,
        name=event.name,
        date=event.date,
        location_on_playa=event.location_on_playa or "",
        camp=event.camp or "",
        description=event.description or "",
        max_attendees=event.max_attendees,
    )

    # Add creator as "going" RSVP with organizer role
    await session.run(
        """
        MATCH (u:User {user_id: $uid})
        MATCH (e:Event {event_id: $eid})
        CREATE (u)-[:RSVP {status: 'going', role: 'organizer', updated_at: datetime()}]->(e)
        """,
        uid=created_by,
        eid=event_id,
    )

    return await _get_event_response(session, event_id)


async def _get_event_response(session: AsyncSession, event_id: str) -> EventResponse:
    """Helper to build an EventResponse from event_id."""
    result = await session.run(
        """
        MATCH (e:Event {event_id: $event_id})
        OPTIONAL MATCH (u:User)-[r:RSVP]->(e)
        WITH e, count(DISTINCT u) AS attendee_count
        RETURN e, attendee_count
        """,
        event_id=event_id,
    )
    row = await result.single()
    if not row:
        raise HTTPException(404, f"Event {event_id} not found")

    e = row["e"]
    return EventResponse(
        event_id=e["event_id"],
        name=e["name"],
        date=e.get("date") or None,
        location_on_playa=e.get("location_on_playa") or None,
        camp=e.get("camp") or None,
        description=e.get("description") or None,
        max_attendees=e.get("max_attendees"),
        created_by=e.get("created_by"),
        created_at=e.get("created_at"),
        attendee_count=row["attendee_count"],
    )


# ── Get Event ────────────────────────────────────────────────────────

@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get event details."""
    return await _get_event_response(session, event_id)


# ── List / Search Events ─────────────────────────────────────────────

@router.get("", response_model=list[EventResponse])
async def list_events(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    q: str | None = Query(None, description="Case-insensitive name search"),
):
    """List all events, optionally filtered by name (case-insensitive partial match)."""
    result = await session.run(
        """
        MATCH (e:Event)
        OPTIONAL MATCH (u:User)-[r:RSVP]->(e)
        WITH e, count(DISTINCT u) AS attendee_count
        WHERE ($q IS NULL OR toLower(e.name) CONTAINS toLower($q))
        RETURN e, attendee_count
        ORDER BY e.created_at DESC
        LIMIT $limit
        """,
        limit=limit,
        q=q,
    )

    events = []
    async for row in result:
        e = row["e"]
        events.append(EventResponse(
            event_id=e["event_id"],
            name=e["name"],
            date=e.get("date") or None,
            location_on_playa=e.get("location_on_playa") or None,
            camp=e.get("camp") or None,
            description=e.get("description") or None,
            max_attendees=e.get("max_attendees"),
            created_by=e.get("created_by"),
            created_at=e.get("created_at"),
            attendee_count=row["attendee_count"],
        ))

    return events


# ── Update Event ─────────────────────────────────────────────────────

@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    event: EventUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update event details."""
    check = await session.run(
        "MATCH (e:Event {event_id: $eid}) RETURN e", eid=event_id
    )
    if not await check.single():
        raise HTTPException(404, f"Event {event_id} not found")

    set_clauses = []
    params = {"event_id": event_id}
    for field in ("name", "date", "location_on_playa", "camp", "description", "max_attendees"):
        val = getattr(event, field, None)
        if val is not None:
            set_clauses.append(f"e.{field} = ${field}")
            params[field] = val

    if set_clauses:
        cypher = f"MATCH (e:Event {{event_id: $event_id}}) SET {', '.join(set_clauses)}"
        await session.run(cypher, **params)

    return await _get_event_response(session, event_id)


# ── Delete Event ─────────────────────────────────────────────────────

@router.delete("/{event_id}", response_model=MessageResponse)
async def delete_event(
    event_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete an event and its relationships."""
    check = await session.run(
        "MATCH (e:Event {event_id: $eid}) RETURN e.name AS name",
        eid=event_id,
    )
    row = await check.single()
    if not row:
        raise HTTPException(404, f"Event {event_id} not found")

    name = row["name"]
    await session.run(
        "MATCH (e:Event {event_id: $eid}) DETACH DELETE e",
        eid=event_id,
    )

    return MessageResponse(message=f"Event '{name}' deleted")


# ── RSVP ─────────────────────────────────────────────────────────────

@router.post("/{event_id}/rsvp", response_model=RSVPResponse)
async def rsvp(
    event_id: str,
    action: RSVPAction,
    session: AsyncSession = Depends(get_session),
):
    """RSVP to an event (going/maybe/not going)."""
    # Check event exists
    event_check = await session.run(
        "MATCH (e:Event {event_id: $eid}) RETURN e", eid=event_id
    )
    if not await event_check.single():
        raise HTTPException(404, f"Event {event_id} not found")

    # Check user exists
    user_check = await session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u", uid=action.user_id
    )
    if not await user_check.single():
        raise HTTPException(404, f"User {action.user_id} not found")

    # Check max_attendees if going
    if action.status == "going":
        max_check = await session.run(
            """
            MATCH (e:Event {event_id: $eid})
            OPTIONAL MATCH (u:User)-[r:RSVP {status: 'going'}]->(e)
            WITH e, count(DISTINCT u) AS going_count
            WHERE e.max_attendees IS NOT NULL AND going_count >= e.max_attendees
            RETURN e.max_attendees AS max, going_count
            """,
            eid=event_id,
        )
        cap_row = await max_check.single()
        if cap_row and cap_row["max"] is not None:
            if cap_row["going_count"] >= cap_row["max"]:
                raise HTTPException(409, "Event is at full capacity")

    # Delete existing RSVP if any, then create new one
    await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:RSVP]->(e:Event {event_id: $eid})
        DELETE r
        """,
        uid=action.user_id,
        eid=event_id,
    )

    await session.run(
        """
        MATCH (u:User {user_id: $uid})
        MATCH (e:Event {event_id: $eid})
        CREATE (u)-[:RSVP {status: $status, updated_at: datetime()}]->(e)
        """,
        uid=action.user_id,
        eid=event_id,
        status=action.status,
    )

    return RSVPResponse(
        event_id=event_id,
        user_id=action.user_id,
        status=action.status,
        updated_at=datetime.utcnow(),
    )


# ── List Attendees ──────────────────────────────────────────────────

@router.get("/{event_id}/attendees", response_model=list[AttendeeResponse])
async def list_attendees(
    event_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List all attendees for an event with their RSVP status and role."""
    result = await session.run(
        """
        MATCH (u:User)-[r:RSVP]->(e:Event {event_id: $eid})
        RETURN u, r.status AS status, r.role AS role
        ORDER BY r.status, u.display_name, u.username
        """,
        eid=event_id,
    )

    attendees = []
    async for row in result:
        u = row["u"]
        attendees.append(AttendeeResponse(
            user_id=u["user_id"],
            username=u["username"],
            display_name=u.get("display_name"),
            rsvp_status=row["status"],
            role=row.get("role") or None,
        ))

    return attendees


# ── Promote to Organizer ─────────────────────────────────────────────

@router.post("/{event_id}/promote", response_model=MessageResponse)
async def promote_attendee(
    event_id: str,
    action: PromoteAction,
    session: AsyncSession = Depends(get_session),
):
    """Promote an attendee to organizer. Only existing organizers can promote."""
    # Check event exists
    event_check = await session.run(
        "MATCH (e:Event {event_id: $eid}) RETURN e", eid=event_id
    )
    if not await event_check.single():
        raise HTTPException(404, f"Event {event_id} not found")

    # Check caller is an organizer
    caller_check = await session.run(
        """
        MATCH (u:User {user_id: $caller})-[r:RSVP]->(e:Event {event_id: $eid})
        RETURN r.role AS role
        """,
        caller=action.promoted_by,
        eid=event_id,
    )
    caller_row = await caller_check.single()
    if not caller_row or caller_row.get("role") != "organizer":
        raise HTTPException(403, "Only event organizers can promote attendees")

    # Check target has an RSVP
    target_check = await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:RSVP]->(e:Event {event_id: $eid})
        RETURN r.role AS role
        """,
        uid=action.user_id,
        eid=event_id,
    )
    target_row = await target_check.single()
    if not target_row:
        raise HTTPException(404, f"User {action.user_id} has not RSVPed to this event")
    if target_row.get("role") == "organizer":
        raise HTTPException(409, "User is already an organizer")

    await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:RSVP]->(e:Event {event_id: $eid})
        SET r.role = 'organizer'
        """,
        uid=action.user_id,
        eid=event_id,
    )

    return MessageResponse(message=f"User {action.user_id} promoted to organizer")


# ── Demote from Organizer ─────────────────────────────────────────────

@router.post("/{event_id}/demote", response_model=MessageResponse)
async def demote_attendee(
    event_id: str,
    action: PromoteAction,
    session: AsyncSession = Depends(get_session),
):
    """Demote an organizer to regular attendee. Only organizers can demote."""
    # Check event exists
    event_check = await session.run(
        "MATCH (e:Event {event_id: $eid}) RETURN e", eid=event_id
    )
    if not await event_check.single():
        raise HTTPException(404, f"Event {event_id} not found")

    # Check caller is an organizer
    caller_check = await session.run(
        """
        MATCH (u:User {user_id: $caller})-[r:RSVP]->(e:Event {event_id: $eid})
        RETURN r.role AS role
        """,
        caller=action.promoted_by,
        eid=event_id,
    )
    caller_row = await caller_check.single()
    if not caller_row or caller_row.get("role") != "organizer":
        raise HTTPException(403, "Only event organizers can demote attendees")

    # Check target is an organizer
    target_check = await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:RSVP]->(e:Event {event_id: $eid})
        RETURN r.role AS role
        """,
        uid=action.user_id,
        eid=event_id,
    )
    target_row = await target_check.single()
    if not target_row:
        raise HTTPException(404, f"User {action.user_id} has not RSVPed to this event")
    if target_row.get("role") != "organizer":
        raise HTTPException(400, "User is not an organizer")

    await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:RSVP]->(e:Event {event_id: $eid})
        REMOVE r.role
        """,
        uid=action.user_id,
        eid=event_id,
    )

    return MessageResponse(message=f"User {action.user_id} demoted from organizer")


# ── Event Posts ──────────────────────────────────────────────────────

@router.post("/{event_id}/posts", response_model=PostResponse, status_code=201)
async def create_event_post(
    event_id: str,
    post: PostCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a post scoped to an event."""
    # Check event exists
    event_check = await session.run(
        "MATCH (e:Event {event_id: $eid}) RETURN e", eid=event_id
    )
    if not await event_check.single():
        raise HTTPException(404, f"Event {event_id} not found")

    import uuid
    post_id = f"post-{uuid.uuid4().hex[:8]}"

    # Verify author exists
    author_check = await session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u", uid=post.author_id
    )
    if not await author_check.single():
        raise HTTPException(404, f"User {post.author_id} not found")

    await session.run(
        """
        MATCH (author:User {user_id: $author_id})
        CREATE (p:Post {
            post_id: $post_id,
            author_id: $author_id,
            content: $content,
            image_url: $image_url,
            event_id: $event_id,
            created_at: datetime()
        })
        CREATE (author)-[:POSTED {at: datetime()}]->(p)
        """,
        author_id=post.author_id,
        post_id=post_id,
        content=post.content,
        image_url=post.image_url or "",
        event_id=event_id,
    )

    from backend.app.routers.posts import _get_post_response
    return await _get_post_response(session, post_id, post.author_id)


@router.get("/{event_id}/posts", response_model=list[PostResponse])
async def list_event_posts(
    event_id: str,
    current_user_id: str | None = Query(None, description="User ID for is_liked_by_me flag"),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
):
    """List all posts for an event, newest first."""
    # Check event exists
    event_check = await session.run(
        "MATCH (e:Event {event_id: $eid}) RETURN e", eid=event_id
    )
    if not await event_check.single():
        raise HTTPException(404, f"Event {event_id} not found")

    result = await session.run(
        """
        MATCH (author:User)-[:POSTED]->(p:Post {event_id: $event_id})
        OPTIONAL MATCH (:User)-[lk:LIKES]->(p)
        OPTIONAL MATCH ()-[c:COMMENT_ON]->(p)
        WITH p, author, count(DISTINCT lk) AS like_count, count(DISTINCT c) AS comment_count
        RETURN p, author, like_count, comment_count
        ORDER BY p.created_at DESC
        LIMIT $limit
        """,
        event_id=event_id,
        limit=limit,
    )

    posts = []
    async for row in result:
        p = row["p"]
        author = row.get("author")

        is_liked = False
        if current_user_id:
            lk = await session.run(
                "MATCH (u:User {user_id: $uid})-[r:LIKES]->(p:Post {post_id: $pid}) RETURN r",
                uid=current_user_id,
                pid=p["post_id"],
            )
            is_liked = await lk.single() is not None

        posts.append(PostResponse(
            post_id=p["post_id"],
            author_id=author["user_id"] if author else p.get("author_id", ""),
            author_username=author["username"] if author else None,
            author_display_name=author.get("display_name") if author else None,
            content=p["content"],
            image_url=p.get("image_url") or None,
            created_at=p.get("created_at"),
            like_count=row["like_count"],
            comment_count=row["comment_count"],
            is_liked_by_me=is_liked,
            event_id=p.get("event_id") or None,
        ))

    return posts

