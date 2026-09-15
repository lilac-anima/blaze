"""Friend connections — send/accept/reject friend requests, list friends, list pending."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any as AsyncSession

from backend.app.database import get_session
from backend.app.models import (
    FriendRequestAction,
    FriendRequestResponse,
    FriendRequestSend,
    FriendResponse,
    MessageResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/friends", tags=["Friends"])


async def _user_exists(session: AsyncSession, user_id: str) -> bool:
    result = await session.run(
        "MATCH (u:User {user_id: $user_id}) RETURN u", user_id=user_id
    )
    return await result.single() is not None


# ── Send Friend Request ───────────────────────────────────────────────

@router.post("/request", response_model=FriendRequestResponse)
async def send_friend_request(
    req: FriendRequestSend,
    session: AsyncSession = Depends(get_session),
):
    """Send a friend request from one user to another."""
    if req.from_user_id == req.to_user_id:
        raise HTTPException(400, "Cannot send friend request to yourself")

    # Check both users exist
    from_exists = await _user_exists(session, req.from_user_id)
    to_exists = await _user_exists(session, req.to_user_id)
    if not from_exists:
        raise HTTPException(404, f"Sender user {req.from_user_id} not found")
    if not to_exists:
        raise HTTPException(404, f"Recipient user {req.to_user_id} not found")

    # Check for existing friendship
    existing = await session.run(
        """
        MATCH (a:User {user_id: $from_id})-[r:FRIENDS_WITH]-(b:User {user_id: $to_id})
        RETURN r
        """,
        from_id=req.from_user_id, to_id=req.to_user_id,
    )
    if await existing.single():
        raise HTTPException(409, "Users are already friends")

    # Check for existing pending request
    existing_req = await session.run(
        """
        MATCH (from_user:User {user_id: $from_id})
        MATCH (to_user:User {user_id: $to_id})
        MATCH (from_user)-[r:FRIEND_REQUEST]->(to_user)
        RETURN r
        """,
        from_id=req.from_user_id, to_id=req.to_user_id,
    )
    if await existing_req.single():
        raise HTTPException(409, "Friend request already sent")

    # Check for reverse pending request
    reverse_req = await session.run(
        """
        MATCH (from_user:User {user_id: $to_id})
        MATCH (to_user:User {user_id: $from_id})
        MATCH (from_user)-[r:FRIEND_REQUEST]->(to_user)
        RETURN r
        """,
        from_id=req.from_user_id, to_id=req.to_user_id,
    )
    if await reverse_req.single():
        raise HTTPException(409, "That user has already sent you a request — accept it instead")

    request_id = f"fr-{req.from_user_id}-{req.to_user_id}-{int(datetime.utcnow().timestamp())}"

    await session.run(
        """
        MATCH (from_user:User {user_id: $from_id})
        MATCH (to_user:User {user_id: $to_id})
        CREATE (from_user)-[r:FRIEND_REQUEST {
            request_id: $request_id,
            status: 'pending',
            message: $message,
            created_at: datetime()
        }]->(to_user)
        """,
        from_id=req.from_user_id,
        to_id=req.to_user_id,
        request_id=request_id,
        message=req.message or "",
    )

    result = await session.run(
        """
        MATCH (from_user:User {user_id: $from_id})
        MATCH (to_user:User {user_id: $to_id})
        MATCH (from_user)-[r:FRIEND_REQUEST]->(to_user)
        WHERE r.request_id = $request_id
        RETURN from_user, to_user, r
        """,
        from_id=req.from_user_id,
        to_id=req.to_user_id,
        request_id=request_id,
    )
    row = await result.single()
    if not row:
        raise HTTPException(500, "Failed to create friend request")

    from_user = row["from_user"]
    to_user = row["to_user"]
    rel = row["r"]

    return FriendRequestResponse(
        request_id=rel.get("request_id", request_id),
        from_user_id=from_user["user_id"],
        from_username=from_user["username"],
        from_display_name=from_user.get("display_name"),
        to_user_id=to_user["user_id"],
        to_username=to_user["username"],
        to_display_name=to_user.get("display_name"),
        status=rel.get("status", "pending"),
        message=rel.get("message") or None,
        created_at=rel.get("created_at"),
    )


# ── Accept / Reject Friend Request ────────────────────────────────────

@router.post("/request/{request_id}/accept", response_model=MessageResponse)
async def accept_friend_request(
    request_id: str,
    action: FriendRequestAction,
    session: AsyncSession = Depends(get_session),
):
    """Accept a pending friend request."""
    result = await session.run(
        """
        MATCH (from_user:User)-[r:FRIEND_REQUEST {request_id: $request_id}]->(to_user:User {user_id: $user_id})
        WHERE r.status = 'pending'
        RETURN from_user, to_user, r
        """,
        request_id=request_id,
        user_id=action.user_id,
    )
    row = await result.single()
    if not row:
        raise HTTPException(404, "Pending friend request not found")

    from_user = row["from_user"]
    to_user = row["to_user"]

    # Delete the request relationship
    await session.run(
        """
        MATCH (from_user:User {user_id: $from_id})-[r:FRIEND_REQUEST]->(to_user:User {user_id: $to_id})
        DELETE r
        """,
        from_id=from_user["user_id"],
        to_id=to_user["user_id"],
    )

    # Create FRIENDS_WITH relationship
    await session.run(
        """
        MATCH (a:User {user_id: $from_id})
        MATCH (b:User {user_id: $to_id})
        CREATE (a)-[:FRIENDS_WITH {since: date()}]->(b)
        """,
        from_id=from_user["user_id"],
        to_id=to_user["user_id"],
    )

    return MessageResponse(
        message=f"Friend request from {from_user['username']} accepted",
        detail=f"You are now friends with {from_user['username']}",
    )


@router.post("/request/{request_id}/reject", response_model=MessageResponse)
async def reject_friend_request(
    request_id: str,
    action: FriendRequestAction,
    session: AsyncSession = Depends(get_session),
):
    """Reject a pending friend request."""
    result = await session.run(
        """
        MATCH (from_user:User)-[r:FRIEND_REQUEST {request_id: $request_id}]->(to_user:User {user_id: $user_id})
        WHERE r.status = 'pending'
        RETURN from_user, r
        """,
        request_id=request_id,
        user_id=action.user_id,
    )
    row = await result.single()
    if not row:
        raise HTTPException(404, "Pending friend request not found")

    from_user = row["from_user"]

    # Update status to rejected
    await session.run(
        """
        MATCH (from_user:User)-[r:FRIEND_REQUEST {request_id: $request_id}]->(to_user:User {user_id: $user_id})
        SET r.status = 'rejected'
        """,
        request_id=request_id,
        user_id=action.user_id,
    )

    return MessageResponse(
        message=f"Friend request from {from_user['username']} rejected",
    )


# ── List Friends ──────────────────────────────────────────────────────

@router.get("/{user_id}", response_model=list[FriendResponse])
async def list_friends(
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List all friends for a user."""
    exists = await _user_exists(session, user_id)
    if not exists:
        raise HTTPException(404, f"User {user_id} not found")

    result = await session.run(
        """
        MATCH (u:User {user_id: $user_id})-[r:FRIENDS_WITH]-(friend:User)
        OPTIONAL MATCH (friend)-[:HAS_PROFILE]->(profile:BurnerProfile)
        RETURN friend, r, profile
        ORDER BY friend.display_name, friend.username
        """,
        user_id=user_id,
    )

    friends = []
    async for row in result:
        friend = row["friend"]
        rel = row["r"]
        profile = row.get("profile")
        friends.append(FriendResponse(
            user_id=friend["user_id"],
            username=friend["username"],
            display_name=friend.get("display_name"),
            burner_name=profile.get("burner_name") if profile else None,
            home_camp=profile.get("home_camp") if profile else None,
            friends_since=str(rel.get("since")) if rel.get("since") else None,
        ))

    return friends


# ── List Pending Friend Requests ──────────────────────────────────────

@router.get("/{user_id}/pending", response_model=list[FriendRequestResponse])
async def list_pending_requests(
    user_id: str,
    direction: str = Query("incoming", description="incoming (to me) or outgoing (from me)"),
    session: AsyncSession = Depends(get_session),
):
    """List pending friend requests for a user."""
    exists = await _user_exists(session, user_id)
    if not exists:
        raise HTTPException(404, f"User {user_id} not found")

    if direction == "incoming":
        query = """
            MATCH (from_user:User)-[r:FRIEND_REQUEST {status: 'pending'}]->(to_user:User {user_id: $user_id})
            RETURN from_user, to_user, r
            ORDER BY r.created_at DESC
        """
    else:
        query = """
            MATCH (from_user:User {user_id: $user_id})-[r:FRIEND_REQUEST {status: 'pending'}]->(to_user:User)
            RETURN from_user, to_user, r
            ORDER BY r.created_at DESC
        """

    result = await session.run(query, user_id=user_id)
    requests = []
    async for row in result:
        from_user = row["from_user"]
        to_user = row["to_user"]
        rel = row["r"]
        requests.append(FriendRequestResponse(
            request_id=rel.get("request_id", ""),
            from_user_id=from_user["user_id"],
            from_username=from_user["username"],
            from_display_name=from_user.get("display_name"),
            to_user_id=to_user["user_id"],
            to_username=to_user["username"],
            to_display_name=to_user.get("display_name"),
            status=rel.get("status", "pending"),
            message=rel.get("message") or None,
            created_at=rel.get("created_at"),
        ))

    return requests


# ── Unfriend ──────────────────────────────────────────────────────────

@router.delete("/{user_id}/unfriend/{friend_id}", response_model=MessageResponse)
async def unfriend(
    user_id: str,
    friend_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Remove a friend connection."""
    result = await session.run(
        """
        MATCH (a:User {user_id: $user_id})-[r:FRIENDS_WITH]-(b:User {user_id: $friend_id})
        RETURN a, b
        """,
        user_id=user_id,
        friend_id=friend_id,
    )
    if not await result.single():
        raise HTTPException(404, "Friendship not found")

    await session.run(
        """
        MATCH (a:User {user_id: $user_id})-[r:FRIENDS_WITH]-(b:User {user_id: $friend_id})
        DELETE r
        """,
        user_id=user_id,
        friend_id=friend_id,
    )

    return MessageResponse(message="Friendship removed")
