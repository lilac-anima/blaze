"""User discovery — search users by name/playa_name/camp, suggest connections."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any as AsyncSession

from backend.app.database import get_session
from backend.app.models import UserResponse, UserSearchResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


# ── Create User ──────────────────────────────────────────────────────

@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    username: str = Query(...),
    email: str = Query(...),
    display_name: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Create a new user node."""
    import uuid
    user_id = f"user-{uuid.uuid4().hex[:8]}"

    result = await session.run(
        """
        CREATE (u:User {
            user_id: $user_id,
            username: $username,
            email: $email,
            display_name: $display_name,
            created_at: datetime()
        })
        RETURN u
        """,
        user_id=user_id,
        username=username,
        email=email,
        display_name=display_name or username,
    )
    row = await result.single()
    if not row:
        raise HTTPException(500, "Failed to create user")

    u = row["u"]
    return UserResponse(
        user_id=u["user_id"],
        username=u["username"],
        email=u["email"],
        display_name=u.get("display_name"),
        created_at=u.get("created_at"),
    )


# ── Get User by ID ───────────────────────────────────────────────────

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get a user by their user_id."""
    result = await session.run(
        "MATCH (u:User {user_id: $user_id}) RETURN u",
        user_id=user_id,
    )
    row = await result.single()
    if not row:
        raise HTTPException(404, f"User {user_id} not found")

    u = row["u"]
    return UserResponse(
        user_id=u["user_id"],
        username=u["username"],
        email=u["email"],
        display_name=u.get("display_name"),
        created_at=u.get("created_at"),
    )


# ── Search Users ─────────────────────────────────────────────────────

@router.get("", response_model=list[UserSearchResult])
async def search_users(
    q: str = Query("", description="Search query — matches username, display_name, burner_name, or camp"),
    current_user_id: str | None = Query(None, description="If set, marks friendship status"),
    session: AsyncSession = Depends(get_session),
):
    """Search users by username, display name, burner name, or home camp."""
    if not q.strip():
        # Return recent users if no query
        result = await session.run(
            """
            MATCH (u:User)
            OPTIONAL MATCH (u)-[:HAS_PROFILE]->(p:BurnerProfile)
            RETURN u, p
            ORDER BY u.created_at DESC
            LIMIT 20
            """
        )
    else:
        result = await session.run(
            """
            MATCH (u:User)
            OPTIONAL MATCH (u)-[:HAS_PROFILE]->(p:BurnerProfile)
            WHERE
                toLower(u.username) CONTAINS toLower($q)
                OR toLower(u.display_name) CONTAINS toLower($q)
                OR toLower(p.burner_name) CONTAINS toLower($q)
                OR toLower(p.home_camp) CONTAINS toLower($q)
            RETURN u, p
            ORDER BY u.display_name, u.username
            LIMIT 20
            """,
            q=q,
        )

    # If current_user_id is set, check which results are already friends
    friend_ids: set[str] = set()
    if current_user_id:
        friend_result = await session.run(
            """
            MATCH (me:User {user_id: $current_user_id})-[r:FRIENDS_WITH]-(friend:User)
            RETURN collect(friend.user_id) AS friend_ids
            """,
            current_user_id=current_user_id,
        )
        friend_row = await friend_result.single()
        if friend_row:
            friend_ids = set(friend_row["friend_ids"])

    users = []
    async for row in result:
        u = row["u"]
        p = row.get("p")
        users.append(UserSearchResult(
            user_id=u["user_id"],
            username=u["username"],
            display_name=u.get("display_name"),
            burner_name=p.get("burner_name") if p else None,
            home_camp=p.get("home_camp") if p else None,
            is_friend=u["user_id"] in friend_ids,
        ))

    return users


# ── Suggest Connections ──────────────────────────────────────────────

@router.get("/{user_id}/suggestions", response_model=list[UserSearchResult])
async def suggest_connections(
    user_id: str,
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
):
    """
    Suggest potential connections: friends of friends who aren't already friends.
    """
    exists_result = await session.run(
        "MATCH (u:User {user_id: $user_id}) RETURN u", user_id=user_id
    )
    if not await exists_result.single():
        raise HTTPException(404, f"User {user_id} not found")

    result = await session.run(
        """
        MATCH (me:User {user_id: $user_id})-[:FRIENDS_WITH]->(friend:User)-[:FRIENDS_WITH]->(suggestion:User)
        WHERE NOT (me)-[:FRIENDS_WITH]-(suggestion)
        AND me <> suggestion
        OPTIONAL MATCH (suggestion)-[:HAS_PROFILE]->(p:BurnerProfile)
        RETURN DISTINCT suggestion, p
        ORDER BY suggestion.display_name, suggestion.username
        LIMIT $limit
        """,
        user_id=user_id,
        limit=limit,
    )

    suggestions = []
    async for row in result:
        s = row["suggestion"]
        p = row.get("p")
        suggestions.append(UserSearchResult(
            user_id=s["user_id"],
            username=s["username"],
            display_name=s.get("display_name"),
            burner_name=p.get("burner_name") if p else None,
            home_camp=p.get("home_camp") if p else None,
            is_friend=False,
        ))

    return suggestions
