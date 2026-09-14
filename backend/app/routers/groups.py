"""Group CRUD — create invite-only or public groups, join/leave, member management."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from backend.app.database import get_session
from backend.app.models import (
    GroupCreate,
    GroupMemberResponse,
    GroupResponse,
    GroupUpdate,
    MessageResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/groups", tags=["Groups"])


async def _get_group_response(session: AsyncSession, group_id: str) -> GroupResponse:
    result = await session.run(
        """
        MATCH (g:Group {group_id: $group_id})
        OPTIONAL MATCH (u:User)-[r:MEMBER_OF]->(g)
        WITH g, count(DISTINCT u) AS member_count
        RETURN g, member_count
        """,
        group_id=group_id,
    )
    row = await result.single()
    if not row:
        raise HTTPException(404, f"Group {group_id} not found")

    g = row["g"]
    return GroupResponse(
        group_id=g["group_id"],
        name=g["name"],
        description=g.get("description") or None,
        is_public=g.get("is_public", True),
        created_by=g.get("created_by"),
        created_at=g.get("created_at"),
        member_count=row["member_count"],
    )


# ── Create Group ─────────────────────────────────────────────────────

@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    group: GroupCreate,
    created_by: str = Query(..., description="User ID of the creator"),
    session: AsyncSession = Depends(get_session),
):
    """Create a new group (public or invite-only)."""
    import uuid
    group_id = f"grp-{uuid.uuid4().hex[:8]}"

    creator_check = await session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u", uid=created_by
    )
    if not await creator_check.single():
        raise HTTPException(404, f"User {created_by} not found")

    await session.run(
        """
        CREATE (g:Group {
            group_id: $group_id,
            name: $name,
            description: $description,
            is_public: $is_public,
            created_by: $created_by,
            created_at: datetime()
        })
        """,
        group_id=group_id,
        name=group.name,
        description=group.description or "",
        is_public=group.is_public,
        created_by=created_by,
    )

    # Auto-join creator as admin
    await session.run(
        """
        MATCH (u:User {user_id: $uid})
        MATCH (g:Group {group_id: $gid})
        CREATE (u)-[:MEMBER_OF {role: 'admin', joined_at: datetime()}]->(g)
        """,
        uid=created_by,
        gid=group_id,
    )

    return await _get_group_response(session, group_id)


# ── Get Group ────────────────────────────────────────────────────────

@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get group details."""
    return await _get_group_response(session, group_id)


# ── List Groups ──────────────────────────────────────────────────────

@router.get("", response_model=list[GroupResponse])
async def list_groups(
    session: AsyncSession = Depends(get_session),
    public_only: bool = Query(True, description="Only show public groups"),
    limit: int = Query(50, ge=1, le=200),
):
    """List all groups."""
    if public_only:
        result = await session.run(
            """
            MATCH (g:Group {is_public: true})
            OPTIONAL MATCH (u:User)-[r:MEMBER_OF]->(g)
            WITH g, count(DISTINCT u) AS member_count
            RETURN g, member_count
            ORDER BY g.name
            LIMIT $limit
            """,
            limit=limit,
        )
    else:
        result = await session.run(
            """
            MATCH (g:Group)
            OPTIONAL MATCH (u:User)-[r:MEMBER_OF]->(g)
            WITH g, count(DISTINCT u) AS member_count
            RETURN g, member_count
            ORDER BY g.name
            LIMIT $limit
            """,
            limit=limit,
        )

    groups = []
    async for row in result:
        g = row["g"]
        groups.append(GroupResponse(
            group_id=g["group_id"],
            name=g["name"],
            description=g.get("description") or None,
            is_public=g.get("is_public", True),
            created_by=g.get("created_by"),
            created_at=g.get("created_at"),
            member_count=row["member_count"],
        ))

    return groups


# ── Update Group ────────────────────────────────────────────────────

@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    group: GroupUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update group details."""
    check = await session.run(
        "MATCH (g:Group {group_id: $gid}) RETURN g", gid=group_id
    )
    if not await check.single():
        raise HTTPException(404, f"Group {group_id} not found")

    set_clauses = []
    params = {"group_id": group_id}
    for field in ("name", "description", "is_public"):
        val = getattr(group, field, None)
        if val is not None:
            set_clauses.append(f"g.{field} = ${field}")
            params[field] = val

    if set_clauses:
        cypher = f"MATCH (g:Group {{group_id: $group_id}}) SET {', '.join(set_clauses)}"
        await session.run(cypher, **params)

    return await _get_group_response(session, group_id)


# ── Delete Group ────────────────────────────────────────────────────

@router.delete("/{group_id}", response_model=MessageResponse)
async def delete_group(
    group_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a group and its relationships."""
    check = await session.run(
        "MATCH (g:Group {group_id: $gid}) RETURN g.name AS name", gid=group_id
    )
    row = await check.single()
    if not row:
        raise HTTPException(404, f"Group {group_id} not found")

    name = row["name"]
    await session.run(
        "MATCH (g:Group {group_id: $gid}) DETACH DELETE g",
        gid=group_id,
    )

    return MessageResponse(message=f"Group '{name}' deleted")


# ── Join Group ───────────────────────────────────────────────────────

@router.post("/{group_id}/join", response_model=MessageResponse)
async def join_group(
    group_id: str,
    user_id: str = Query(..., description="User ID joining the group"),
    session: AsyncSession = Depends(get_session),
):
    """Join a public group. Private/invite-only groups require an invitation."""
    # Check group exists
    group_check = await session.run(
        "MATCH (g:Group {group_id: $gid}) RETURN g", gid=group_id
    )
    row = await group_check.single()
    if not row:
        raise HTTPException(404, f"Group {group_id} not found")

    g = row["g"]
    if not g.get("is_public", True):
        raise HTTPException(403, "This is an invite-only group — invitations required")

    # Check user exists
    user_check = await session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u", uid=user_id
    )
    if not await user_check.single():
        raise HTTPException(404, f"User {user_id} not found")

    # Check if already a member
    member_check = await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:MEMBER_OF]->(g:Group {group_id: $gid})
        RETURN r
        """,
        uid=user_id,
        gid=group_id,
    )
    if await member_check.single():
        raise HTTPException(409, "User is already a member of this group")

    await session.run(
        """
        MATCH (u:User {user_id: $uid})
        MATCH (g:Group {group_id: $gid})
        CREATE (u)-[:MEMBER_OF {role: 'member', joined_at: datetime()}]->(g)
        """,
        uid=user_id,
        gid=group_id,
    )

    return MessageResponse(message=f"User {user_id} joined group '{g['name']}'")


# ── Leave Group ──────────────────────────────────────────────────────

@router.post("/{group_id}/leave", response_model=MessageResponse)
async def leave_group(
    group_id: str,
    user_id: str = Query(..., description="User ID leaving the group"),
    session: AsyncSession = Depends(get_session),
):
    """Leave a group."""
    result = await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:MEMBER_OF]->(g:Group {group_id: $gid})
        DELETE r
        RETURN g.name AS group_name
        """,
        uid=user_id,
        gid=group_id,
    )
    row = await result.single()
    if not row:
        raise HTTPException(404, "User is not a member of this group")

    return MessageResponse(message=f"User {user_id} left group '{row['group_name']}'")


# ── List Group Members ───────────────────────────────────────────────

@router.get("/{group_id}/members", response_model=list[GroupMemberResponse])
async def list_group_members(
    group_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List all members of a group."""
    group_check = await session.run(
        "MATCH (g:Group {group_id: $gid}) RETURN g", gid=group_id
    )
    if not await group_check.single():
        raise HTTPException(404, f"Group {group_id} not found")

    result = await session.run(
        """
        MATCH (u:User)-[r:MEMBER_OF]->(g:Group {group_id: $gid})
        RETURN u, r.role AS role
        ORDER BY r.role, u.display_name, u.username
        """,
        gid=group_id,
    )

    members = []
    async for row in result:
        u = row["u"]
        members.append(GroupMemberResponse(
            user_id=u["user_id"],
            username=u["username"],
            display_name=u.get("display_name"),
            role=row["role"] or "member",
        ))

    return members
