"""User profile router for the authenticated user (GET/PATCH /api/users/me)."""

from fastapi import APIRouter, Depends, HTTPException, status
from neo4j import AsyncSession as Neo4jAsyncSession

from backend.app.auth.dependencies import get_current_user
from backend.app.auth.schemas import (
    BurnerProfilePublic,
    ProfileUpdateRequest,
    UserProfileResponse,
    UserPublic,
    UserUpdateRequest,
)
from backend.app.database import get_session

router = APIRouter(prefix="/api/users", tags=["users"])


# ── Helpers ─────────────────────────────────────────────────────────────


def _user_from_record(record) -> UserPublic:
    """Build a UserPublic from a Neo4j User node record."""
    user = record["u"]
    return UserPublic(
        user_id=user.get("user_id", ""),
        email=user.get("email"),
        username=user.get("username", ""),
        created_at=user.get("created_at"),
    )


def _burner_from_record(record) -> BurnerProfilePublic:
    """Build a BurnerProfilePublic from a Neo4j record."""
    bp = record.get("bp")
    if bp is None:
        return BurnerProfilePublic(playa_name="")
    return BurnerProfilePublic(
        playa_name=bp.get("playa_name", ""),
        home_camp=bp.get("home_camp"),
        years_attended=bp.get("years_attended", []),
        vibe=bp.get("vibe"),
        bio=bp.get("bio"),
    )


# ── GET /api/users/me ───────────────────────────────────────────────────


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user: dict = Depends(get_current_user),
    neo4j_session: Neo4jAsyncSession = Depends(get_session),
):
    """Get the current user's profile and burner info."""
    user_id = current_user["sub"]

    result = await neo4j_session.run(
        """
        MATCH (u:User {user_id: $uid})
        OPTIONAL MATCH (u)-[:HAS_PROFILE]->(bp:BurnerProfile)
        RETURN u, bp
        """,
        uid=user_id,
    )
    record = await result.single()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserProfileResponse(
        user=_user_from_record(record),
        burner=_burner_from_record(record),
    )


# ── PATCH /api/users/me ─────────────────────────────────────────────────


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    user_update: UserUpdateRequest = None,
    profile_update: ProfileUpdateRequest = None,
    current_user: dict = Depends(get_current_user),
    neo4j_session: Neo4jAsyncSession = Depends(get_session),
):
    """Update the current user's account and/or burner profile fields.

    Accepts a combined JSON body with optional 'user' and 'burner' nested objects.
    """
    if not neo4j_session:
        raise HTTPException(status_code=503, detail="Database unavailable")

    user_id = current_user["sub"]
    now_iso = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    changes_made = False

    # Update User fields
    if user_update:
        set_parts = []
        params = {"uid": user_id, "now": now_iso}
        if user_update.email is not None:
            # Check for duplicate email
            dup = await neo4j_session.run(
                "MATCH (u:User {email: $email}) WHERE u.user_id <> $uid RETURN u LIMIT 1",
                email=user_update.email,
                uid=user_id,
            )
            if await dup.single():
                raise HTTPException(status_code=409, detail="Email already in use")
            set_parts.append("u.email = $email")
            params["email"] = user_update.email
        if user_update.username is not None:
            dup = await neo4j_session.run(
                "MATCH (u:User {username: $username}) WHERE u.user_id <> $uid RETURN u LIMIT 1",
                username=user_update.username,
                uid=user_id,
            )
            if await dup.single():
                raise HTTPException(status_code=409, detail="Username already in use")
            set_parts.append("u.username = $username")
            params["username"] = user_update.username

        if set_parts:
            set_parts.append("u.updated_at = $now")
            query = f"MATCH (u:User {{user_id: $uid}}) SET {', '.join(set_parts)}"
            await neo4j_session.run(query, **params)
            changes_made = True

    # Update BurnerProfile fields
    if profile_update:
        set_parts = []
        params = {"uid": user_id}
        if profile_update.playa_name is not None:
            set_parts.append("bp.playa_name = $playa_name")
            params["playa_name"] = profile_update.playa_name
        if profile_update.home_camp is not None:
            set_parts.append("bp.home_camp = $home_camp")
            params["home_camp"] = profile_update.home_camp
        if profile_update.years_attended is not None:
            set_parts.append("bp.years_attended = $years_attended")
            params["years_attended"] = profile_update.years_attended
        if profile_update.vibe is not None:
            set_parts.append("bp.vibe = $vibe")
            params["vibe"] = profile_update.vibe
        if profile_update.bio is not None:
            set_parts.append("bp.bio = $bio")
            params["bio"] = profile_update.bio

        if set_parts:
            query = (
                f"MATCH (u:User {{user_id: $uid}})-[:HAS_PROFILE]->(bp:BurnerProfile) "
                f"SET {', '.join(set_parts)}"
            )
            await neo4j_session.run(query, **params)
            changes_made = True

    # Fetch and return updated profile
    result = await neo4j_session.run(
        """
        MATCH (u:User {user_id: $uid})
        OPTIONAL MATCH (u)-[:HAS_PROFILE]->(bp:BurnerProfile)
        RETURN u, bp
        """,
        uid=user_id,
    )
    record = await result.single()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserProfileResponse(
        user=_user_from_record(record),
        burner=_burner_from_record(record),
    )
