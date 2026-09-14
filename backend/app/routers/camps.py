"""Camp CRUD — create/edit camps, join/leave camp, list camp members."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from backend.app.database import get_session
from backend.app.models import (
    CampCreate,
    CampMemberResponse,
    CampResponse,
    CampUpdate,
    MessageResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/camps", tags=["Camps"])


async def _get_camp_response(session: AsyncSession, camp_id: str) -> CampResponse:
    result = await session.run(
        """
        MATCH (c:Camp {camp_id: $camp_id})
        OPTIONAL MATCH (u:User)-[r:MEMBER_OF]->(c)
        OPTIONAL MATCH (c)-[:HOSTED_BY]->(e:Event)
        WITH c, count(DISTINCT u) AS member_count, e
        RETURN c, member_count, e
        """,
        camp_id=camp_id,
    )
    row = await result.single()
    if not row:
        raise HTTPException(404, f"Camp {camp_id} not found")

    c = row["c"]
    e = row.get("e")
    return CampResponse(
        camp_id=c["camp_id"],
        name=c["name"],
        description=c.get("description") or None,
        location_on_playa=c.get("location_on_playa") or None,
        created_by=c.get("created_by"),
        created_at=c.get("created_at"),
        member_count=row["member_count"],
        event_id=e["event_id"] if e else None,
        event_name=e["name"] if e else None,
    )


# ── Create Camp ──────────────────────────────────────────────────────

@router.post("", response_model=CampResponse, status_code=201)
async def create_camp(
    camp: CampCreate,
    created_by: str = Query(..., description="User ID of the creator"),
    session: AsyncSession = Depends(get_session),
):
    """Create a new camp."""
    import uuid
    camp_id = f"camp-{uuid.uuid4().hex[:8]}"

    creator_check = await session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u", uid=created_by
    )
    if not await creator_check.single():
        raise HTTPException(404, f"User {created_by} not found")

    await session.run(
        """
        CREATE (c:Camp {
            camp_id: $camp_id,
            name: $name,
            description: $description,
            location_on_playa: $location_on_playa,
            created_by: $created_by,
            created_at: datetime()
        })
        """,
        camp_id=camp_id,
        name=camp.name,
        description=camp.description or "",
        location_on_playa=camp.location_on_playa or "",
        created_by=created_by,
    )

    # Link to event if provided
    if camp.event_id:
        await session.run(
            """
            MATCH (c:Camp {camp_id: $cid})
            MATCH (e:Event {event_id: $eid})
            CREATE (c)-[:HOSTED_BY]->(e)
            """,
            cid=camp_id,
            eid=camp.event_id,
        )

    # Auto-join creator as lead
    await session.run(
        """
        MATCH (u:User {user_id: $uid})
        MATCH (c:Camp {camp_id: $cid})
        CREATE (u)-[:MEMBER_OF {role: 'lead', joined_at: datetime()}]->(c)
        """,
        uid=created_by,
        cid=camp_id,
    )

    return await _get_camp_response(session, camp_id)


# ── Get Camp ─────────────────────────────────────────────────────────

@router.get("/{camp_id}", response_model=CampResponse)
async def get_camp(
    camp_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get camp details."""
    return await _get_camp_response(session, camp_id)


# ── List Camps ──────────────────────────────────────────────────────

@router.get("", response_model=list[CampResponse])
async def list_camps(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
    q: str | None = Query(None, description="Case-insensitive name search"),
):
    """List all camps, optionally filtered by name (case-insensitive partial match)."""
    result = await session.run(
        """
        MATCH (c:Camp)
        OPTIONAL MATCH (u:User)-[r:MEMBER_OF]->(c)
        OPTIONAL MATCH (c)-[:HOSTED_BY]->(e:Event)
        WHERE ($q IS NULL OR toLower(c.name) CONTAINS toLower($q))
        WITH c, count(DISTINCT u) AS member_count, e
        RETURN c, member_count, e
        ORDER BY c.name
        LIMIT $limit
        """,
        limit=limit,
        q=q,
    )

    camps = []
    async for row in result:
        c = row["c"]
        e = row.get("e")
        camps.append(CampResponse(
            camp_id=c["camp_id"],
            name=c["name"],
            description=c.get("description") or None,
            location_on_playa=c.get("location_on_playa") or None,
            created_by=c.get("created_by"),
            created_at=c.get("created_at"),
            member_count=row["member_count"],
            event_id=e["event_id"] if e else None,
            event_name=e["name"] if e else None,
        ))

    return camps


# ── Update Camp ─────────────────────────────────────────────────────

@router.patch("/{camp_id}", response_model=CampResponse)
async def update_camp(
    camp_id: str,
    camp: CampUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update camp details."""
    check = await session.run(
        "MATCH (c:Camp {camp_id: $cid}) RETURN c", cid=camp_id
    )
    if not await check.single():
        raise HTTPException(404, f"Camp {camp_id} not found")

    set_clauses = []
    params = {"camp_id": camp_id}
    for field in ("name", "description", "location_on_playa"):
        val = getattr(camp, field, None)
        if val is not None:
            set_clauses.append(f"c.{field} = ${field}")
            params[field] = val

    if set_clauses:
        cypher = f"MATCH (c:Camp {{camp_id: $camp_id}}) SET {', '.join(set_clauses)}"
        await session.run(cypher, **params)

    return await _get_camp_response(session, camp_id)


# ── Delete Camp ─────────────────────────────────────────────────────

@router.delete("/{camp_id}", response_model=MessageResponse)
async def delete_camp(
    camp_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a camp and its relationships."""
    check = await session.run(
        "MATCH (c:Camp {camp_id: $cid}) RETURN c.name AS name", cid=camp_id
    )
    row = await check.single()
    if not row:
        raise HTTPException(404, f"Camp {camp_id} not found")

    name = row["name"]
    await session.run(
        "MATCH (c:Camp {camp_id: $cid}) DETACH DELETE c",
        cid=camp_id,
    )

    return MessageResponse(message=f"Camp '{name}' deleted")


# ── Join Camp ────────────────────────────────────────────────────────

@router.post("/{camp_id}/join", response_model=MessageResponse)
async def join_camp(
    camp_id: str,
    user_id: str = Query(..., description="User ID joining the camp"),
    session: AsyncSession = Depends(get_session),
):
    """Join a camp."""
    # Check camp exists
    camp_check = await session.run(
        "MATCH (c:Camp {camp_id: $cid}) RETURN c", cid=camp_id
    )
    if not await camp_check.single():
        raise HTTPException(404, f"Camp {camp_id} not found")

    # Check user exists
    user_check = await session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u", uid=user_id
    )
    if not await user_check.single():
        raise HTTPException(404, f"User {user_id} not found")

    # Check if already a member
    member_check = await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:MEMBER_OF]->(c:Camp {camp_id: $cid})
        RETURN r
        """,
        uid=user_id,
        cid=camp_id,
    )
    if await member_check.single():
        raise HTTPException(409, "User is already a member of this camp")

    await session.run(
        """
        MATCH (u:User {user_id: $uid})
        MATCH (c:Camp {camp_id: $cid})
        CREATE (u)-[:MEMBER_OF {role: 'member', joined_at: datetime()}]->(c)
        """,
        uid=user_id,
        cid=camp_id,
    )

    return MessageResponse(message=f"User {user_id} joined camp")


# ── Leave Camp ───────────────────────────────────────────────────────

@router.post("/{camp_id}/leave", response_model=MessageResponse)
async def leave_camp(
    camp_id: str,
    user_id: str = Query(..., description="User ID leaving the camp"),
    session: AsyncSession = Depends(get_session),
):
    """Leave a camp."""
    result = await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:MEMBER_OF]->(c:Camp {camp_id: $cid})
        DELETE r
        RETURN c.name AS camp_name
        """,
        uid=user_id,
        cid=camp_id,
    )
    row = await result.single()
    if not row:
        raise HTTPException(404, "User is not a member of this camp")

    return MessageResponse(message=f"User {user_id} left camp '{row['camp_name']}'")


# ── List Camp Members ────────────────────────────────────────────────

@router.get("/{camp_id}/members", response_model=list[CampMemberResponse])
async def list_camp_members(
    camp_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List all members of a camp."""
    camp_check = await session.run(
        "MATCH (c:Camp {camp_id: $cid}) RETURN c", cid=camp_id
    )
    if not await camp_check.single():
        raise HTTPException(404, f"Camp {camp_id} not found")

    result = await session.run(
        """
        MATCH (u:User)-[r:MEMBER_OF]->(c:Camp {camp_id: $cid})
        RETURN u, r.role AS role
        ORDER BY r.role, u.display_name, u.username
        """,
        cid=camp_id,
    )

    members = []
    async for row in result:
        u = row["u"]
        members.append(CampMemberResponse(
            user_id=u["user_id"],
            username=u["username"],
            display_name=u.get("display_name"),
            role=row["role"] or "member",
        ))

    return members


# ── Promote to Moderator ──────────────────────────────────────────────

@router.post("/{camp_id}/promote", response_model=MessageResponse)
async def promote_member(
    camp_id: str,
    user_id: str = Query(..., description="User ID to promote to moderator"),
    promoted_by: str = Query(..., description="User ID of the camp lead performing promotion"),
    session: AsyncSession = Depends(get_session),
):
    """Promote a camp member to moderator. Only camp leads can promote."""
    # Check caller is a lead
    caller_check = await session.run(
        """
        MATCH (u:User {user_id: $caller})-[r:MEMBER_OF]->(c:Camp {camp_id: $cid})
        RETURN r.role AS role
        """,
        caller=promoted_by,
        cid=camp_id,
    )
    caller_row = await caller_check.single()
    if not caller_row or caller_row["role"] != "lead":
        raise HTTPException(403, "Only camp leads can promote members")

    # Check target is a current member
    target_check = await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:MEMBER_OF]->(c:Camp {camp_id: $cid})
        RETURN r.role AS role
        """,
        uid=user_id,
        cid=camp_id,
    )
    target_row = await target_check.single()
    if not target_row:
        raise HTTPException(404, f"User {user_id} is not a member of this camp")
    if target_row["role"] == "lead":
        raise HTTPException(400, "Cannot promote the camp lead")
    if target_row["role"] == "moderator":
        raise HTTPException(409, "User is already a moderator")

    await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:MEMBER_OF]->(c:Camp {camp_id: $cid})
        SET r.role = 'moderator'
        """,
        uid=user_id,
        cid=camp_id,
    )

    return MessageResponse(message=f"User {user_id} promoted to moderator")


# ── Demote from Moderator ─────────────────────────────────────────────

@router.post("/{camp_id}/demote", response_model=MessageResponse)
async def demote_member(
    camp_id: str,
    user_id: str = Query(..., description="User ID to demote from moderator"),
    demoted_by: str = Query(..., description="User ID of the camp lead performing demotion"),
    session: AsyncSession = Depends(get_session),
):
    """Demote a moderator back to member. Only camp leads can demote."""
    # Check caller is a lead
    caller_check = await session.run(
        """
        MATCH (u:User {user_id: $caller})-[r:MEMBER_OF]->(c:Camp {camp_id: $cid})
        RETURN r.role AS role
        """,
        caller=demoted_by,
        cid=camp_id,
    )
    caller_row = await caller_check.single()
    if not caller_row or caller_row["role"] != "lead":
        raise HTTPException(403, "Only camp leads can demote members")

    # Check target is a moderator
    target_check = await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:MEMBER_OF]->(c:Camp {camp_id: $cid})
        RETURN r.role AS role
        """,
        uid=user_id,
        cid=camp_id,
    )
    target_row = await target_check.single()
    if not target_row:
        raise HTTPException(404, f"User {user_id} is not a member of this camp")
    if target_row["role"] != "moderator":
        raise HTTPException(400, "User is not a moderator")

    await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:MEMBER_OF]->(c:Camp {camp_id: $cid})
        SET r.role = 'member'
        """,
        uid=user_id,
        cid=camp_id,
    )

    return MessageResponse(message=f"User {user_id} demoted to member")
