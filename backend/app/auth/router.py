"""Auth and user profile router for Blaze."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from neo4j import AsyncSession as Neo4jAsyncSession

from backend.app.auth.dependencies import get_current_user
from backend.app.auth.schemas import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserProfileResponse,
    UserPublic,
    BurnerProfilePublic,
    UserUpdateRequest,
)
from backend.app.auth.utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.app.database import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── Helper ──────────────────────────────────────────────────────────────


def _parse_burner_profile(record) -> BurnerProfilePublic:
    """Extract a BurnerProfilePublic from a Neo4j record."""
    props = record.get("bp") or {}
    return BurnerProfilePublic(
        playa_name=props.get("playa_name", record.get("burner_name", "")),
        home_camp=props.get("home_camp"),
        years_attended=props.get("years_attended", []),
        vibe=props.get("vibe"),
        bio=props.get("bio"),
    )


# ── Register ────────────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, neo4j_session: Neo4jAsyncSession = Depends(get_session)):
    """Register a new user account with a burner profile."""

    # Check for duplicate username
    check = await neo4j_session.run(
        "MATCH (u:User) WHERE u.username = $username RETURN u LIMIT 1",
        username=body.username,
    )
    existing = await check.single()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that username already exists",
        )

    # Check for duplicate email only if provided
    if body.email:
        email_check = await neo4j_session.run(
            "MATCH (u:User) WHERE u.email = $email RETURN u LIMIT 1",
            email=body.email,
        )
        if await email_check.single():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with that email already exists",
            )

    user_id = str(uuid.uuid4())
    now_iso = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    password_hash = hash_password(body.password)

    # Create User + BurnerProfile nodes in a single transaction
    if body.email:
        await neo4j_session.run(
            """
            CREATE (u:User {
                user_id: $user_id,
                username: $username,
                email: $email,
                password_hash: $password_hash,
                created_at: $now,
                updated_at: $now
            })
            CREATE (bp:BurnerProfile {
                profile_id: $profile_id,
                playa_name: $burner_name,
                home_camp: NULL,
                years_attended: [],
                vibe: NULL,
                bio: NULL
            })
            CREATE (u)-[:HAS_PROFILE]->(bp)
            """,
            user_id=user_id,
            username=body.username,
            email=body.email,
            password_hash=password_hash,
            now=now_iso,
            profile_id=str(uuid.uuid4()),
            burner_name=body.burner_name,
        )
    else:
        await neo4j_session.run(
            """
            CREATE (u:User {
                user_id: $user_id,
                username: $username,
                password_hash: $password_hash,
                created_at: $now,
                updated_at: $now
            })
            CREATE (bp:BurnerProfile {
                profile_id: $profile_id,
                playa_name: $burner_name,
                home_camp: NULL,
                years_attended: [],
                vibe: NULL,
                bio: NULL
            })
            CREATE (u)-[:HAS_PROFILE]->(bp)
            """,
            user_id=user_id,
            username=body.username,
            password_hash=password_hash,
            now=now_iso,
            profile_id=str(uuid.uuid4()),
            burner_name=body.burner_name,
        )

    access_token = create_access_token(user_id, body.username)
    refresh_token = create_refresh_token(user_id, body.username)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# ── Login ───────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, neo4j_session: Neo4jAsyncSession = Depends(get_session)):
    """Authenticate with username + password."""

    result = await neo4j_session.run(
        "MATCH (u:User) WHERE u.username = $login RETURN u LIMIT 1",
        login=body.login,
    )
    record = await result.single()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user = record["u"]
    if not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    user_id = user["user_id"]
    username = user["username"]

    access_token = create_access_token(user_id, username)
    refresh_token = create_refresh_token(user_id, username)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# ── Token Refresh ───────────────────────────────────────────────────────


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload["sub"]

    # We need the username — but we don't have a session here.
    # To keep this endpoint stateless we'd need a DB lookup, but since
    # the middleware doesn't need a session dependency, we'll fetch it.
    # For a lightweight implementation we include username in refresh token payload.
    username = payload.get("username", "")
    new_access = create_access_token(user_id, username)
    new_refresh = create_refresh_token(user_id, username)

    return TokenResponse(access_token=new_access, refresh_token=new_refresh)


# ── Password Reset: Request ─────────────────────────────────────────────


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    body: PasswordResetRequest,
    neo4j_session: Neo4jAsyncSession = Depends(get_session),
):
    """Request a password reset. In production this would send an email.

    Returns a reset token (in production this would be emailed).
    """

    result = await neo4j_session.run(
        "MATCH (u:User) WHERE u.email = $email RETURN u.user_id AS uid LIMIT 1",
        email=body.email,
    )
    record = await result.single()

    # Always return 202 to avoid leaking whether the email exists
    if not record:
        return {"message": "If that email is registered, a reset link has been sent."}

    uid = record["uid"]
    # Create a short-lived reset token (valid 15 minutes)
    reset_token_data = {
        "sub": uid,
        "type": "password_reset",
        "exp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        + __import__("datetime").timedelta(minutes=15),
        "jti": str(uuid.uuid4()),
    }
    from jose import jwt as _jwt

    from backend.app.auth.utils import _get_secret_key, ALGORITHM

    reset_token = _jwt.encode(reset_token_data, _get_secret_key(), algorithm=ALGORITHM)

    # Store the reset token on the User node
    await neo4j_session.run(
        "MATCH (u:User {user_id: $uid}) SET u.reset_token = $token",
        uid=uid,
        token=reset_token,
    )

    return {
        "message": "If that email is registered, a reset link has been sent.",
        # In production, remove this and send via email:
        "reset_token": reset_token,
    }


# ── Password Reset: Confirm ─────────────────────────────────────────────


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    body: PasswordResetConfirm,
    neo4j_session: Neo4jAsyncSession = Depends(get_session),
):
    """Confirm password reset with the reset token and new password."""
    # Validate the token first — doesn't need Neo4j
    payload = decode_token(body.token)
    if payload is None or payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user_id = payload["sub"]

    # Verify the stored token matches
    result = await neo4j_session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u.reset_token AS stored_token",
        uid=user_id,
    )
    record = await result.single()
    if not record or record["stored_token"] != body.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    new_hash = hash_password(body.new_password)
    now_iso = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()

    await neo4j_session.run(
        """
        MATCH (u:User {user_id: $uid})
        SET u.password_hash = $hash,
            u.updated_at = $now,
            u.reset_token = NULL
        """,
        uid=user_id,
        hash=new_hash,
        now=now_iso,
    )

    return {"message": "Password has been reset successfully."}
