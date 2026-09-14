"""
Integration tests for Blaze API.
All tests run against the FastAPI application via httpx's ASGITransport,
so no network or database is needed — Neo4j routes gracefully return 503.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Return valid Authorization headers for a test user."""
    from backend.app.auth.utils import create_access_token

    token = create_access_token("test-user-123", "testuser")
    return {"Authorization": f"Bearer {token}"}


# ═════════════════════════════════════════════════════════════════════════
#  Health
# ═════════════════════════════════════════════════════════════════════════


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_degraded_without_neo4j(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["neo4j_connected"] is False

    @pytest.mark.asyncio
    async def test_health_returns_expected_shape(self, client):
        resp = await client.get("/health")
        data = resp.json()
        assert "status" in data
        assert "neo4j_connected" in data
        assert "node_count" in data
        assert "relationship_count" in data


# ═════════════════════════════════════════════════════════════════════════
#  OpenAPI Schema
# ═════════════════════════════════════════════════════════════════════════


class TestOpenAPISchema:
    @pytest.mark.asyncio
    async def test_schema_loads(self, client):
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "Blaze API"
        return schema

    @pytest.mark.asyncio
    async def test_all_auth_routes_present(self, client):
        resp = await client.get("/openapi.json")
        paths = resp.json()["paths"]
        auth_paths = {k for k in paths if k.startswith("/api/auth") or k.startswith("/api/users")}
        assert "/api/auth/register" in auth_paths
        assert "/api/auth/login" in auth_paths
        assert "/api/auth/refresh" in auth_paths
        assert "/api/auth/password-reset/request" in auth_paths
        assert "/api/auth/password-reset/confirm" in auth_paths
        assert "/api/users/me" in auth_paths

    @pytest.mark.asyncio
    async def test_all_social_routes_present(self, client):
        resp = await client.get("/openapi.json")
        paths = resp.json()["paths"]
        # Friends
        assert "/friends/request" in paths
        assert "/friends/request/{request_id}/accept" in paths
        assert "/friends/request/{request_id}/reject" in paths
        assert "/friends/{user_id}" in paths
        assert "/friends/{user_id}/pending" in paths
        assert "/friends/{user_id}/unfriend/{friend_id}" in paths
        # Users
        assert "/users" in paths
        assert "/users/{user_id}" in paths
        assert "/users/{user_id}/suggestions" in paths
        # Events
        assert "/events" in paths
        assert "/events/{event_id}" in paths
        assert "/events/{event_id}/rsvp" in paths
        assert "/events/{event_id}/attendees" in paths
        # Camps
        assert "/camps" in paths
        assert "/camps/{camp_id}" in paths
        assert "/camps/{camp_id}/join" in paths
        assert "/camps/{camp_id}/leave" in paths
        assert "/camps/{camp_id}/members" in paths
        assert "/camps/{camp_id}/promote" in paths
        assert "/camps/{camp_id}/demote" in paths
        # Groups
        assert "/groups" in paths
        assert "/groups/{group_id}" in paths
        assert "/groups/{group_id}/join" in paths
        assert "/groups/{group_id}/leave" in paths
        assert "/groups/{group_id}/members" in paths
        # Posts
        assert "/posts" in paths
        assert "/posts/{post_id}" in paths
        assert "/posts/{post_id}/like" in paths
        assert "/posts/{post_id}/comments" in paths
        assert "/posts/{post_id}/likes" in paths
        assert "/posts/user/{user_id}" in paths
        # Feed
        assert "/feed/{user_id}" in paths


# ═════════════════════════════════════════════════════════════════════════
#  Auth Endpoints
# ═════════════════════════════════════════════════════════════════════════


class TestAuth:
    @pytest.mark.asyncio
    async def test_register_validation_errors(self, client):
        """Register with invalid data — session dependency resolves first → 503."""
        resp = await client.post(
            "/api/auth/register",
            json={"email": "x", "username": "u", "burner_name": "y", "password": "short"},
        )
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_register_degraded(self, client):
        """Register returns 503 gracefully when Neo4j is unavailable."""
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "sparkle@burner.land",
                "username": "sparklepony",
                "burner_name": "Sparkle Pony",
                "password": "supersecret123",
            },
        )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Database unavailable"

    @pytest.mark.asyncio
    async def test_login_degraded(self, client):
        """Login returns 503 gracefully when Neo4j is unavailable."""
        resp = await client.post(
            "/api/auth/login",
            json={"login": "sparkle@burner.land", "password": "supersecret123"},
        )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Database unavailable"

    @pytest.mark.asyncio
    async def test_refresh_invalid_token(self, client):
        """Refresh with a bad token returns 401."""
        resp = await client.post(
            "/api/auth/refresh", json={"refresh_token": "not-a-real-token"}
        )
        assert resp.status_code == 401
        assert "Invalid or expired" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_refresh_with_access_token(self, client):
        """Refresh with an access token (wrong type) returns 401."""
        from backend.app.auth.utils import create_access_token

        token = create_access_token("test-user", "testuser")
        resp = await client.post(
            "/api/auth/refresh", json={"refresh_token": token}
        )
        assert resp.status_code == 401
        assert "Invalid or expired" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_refresh_valid_token(self, client):
        """Refresh with a valid refresh token returns a new token pair."""
        from backend.app.auth.utils import create_refresh_token

        token = create_refresh_token("test-user", "testuser")
        resp = await client.post(
            "/api/auth/refresh", json={"refresh_token": token}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_password_reset_request_degraded(self, client):
        """Password reset request returns 503 without Neo4j."""
        resp = await client.post(
            "/api/auth/password-reset/request",
            json={"email": "sparkle@burner.land"},
        )
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Database unavailable"

    @pytest.mark.asyncio
    async def test_password_reset_confirm_bad_token(self, client):
        """Password reset confirm — session dependency resolves first → 503."""
        resp = await client.post(
            "/api/auth/password-reset/confirm",
            json={"token": "not-a-real-token", "new_password": "newpassword123"},
        )
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_password_reset_confirm_no_body(self, client):
        """Password reset confirm with missing fields — session dependency resolves first → 503."""
        resp = await client.post(
            "/api/auth/password-reset/confirm", json={}
        )
        assert resp.status_code == 503


# ═════════════════════════════════════════════════════════════════════════
#  Profile Endpoints
# ═════════════════════════════════════════════════════════════════════════


class TestProfile:
    @pytest.mark.asyncio
    async def test_get_me_no_auth(self, client):
        """GET /api/users/me without auth returns 401."""
        resp = await client.get("/api/users/me")
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Authentication required"

    @pytest.mark.asyncio
    async def test_get_me_with_auth_degraded(self, client, auth_headers):
        """GET /api/users/me with valid token but no Neo4j returns 503."""
        resp = await client.get("/api/users/me", headers=auth_headers)
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Database unavailable"

    @pytest.mark.asyncio
    async def test_patch_me_no_auth(self, client):
        """PATCH /api/users/me without auth returns 401."""
        resp = await client.patch("/api/users/me", json={})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_patch_me_degraded(self, client, auth_headers):
        """PATCH /api/users/me with auth but no Neo4j returns 503."""
        resp = await client.patch(
            "/api/users/me",
            json={"user": {"username": "newname"}},
            headers=auth_headers,
        )
        assert resp.status_code == 503


# ═════════════════════════════════════════════════════════════════════════
#  Friend Endpoints (all return 422 or 500 because they need a Neo4j session)
# ═════════════════════════════════════════════════════════════════════════

# NOTE: The friend router does NOT inject get_session as a dependency on its
# own — it accepts an explicit body. Routes that call get_session via Depends
# will get None and raise 503. Routes that take explicit body params but
# still need Neo4j will raise internal errors. We test the 500 / 503 fallback.


class TestFriends:
    @pytest.mark.asyncio
    async def test_send_friend_request_no_body(self, client):
        """POST /friends/request — session dependency resolves first → 503."""
        resp = await client.post("/friends/request", json={})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_list_friends_no_user(self, client):
        """GET /friends/{id} for non-existent user returns 500 (no session)."""
        # Without Neo4j session, the Depends returns None — the route will crash
        # when it tries to call session.run() on None
        resp = await client.get("/friends/nonexistent-id")
        # Either 500 (AttributeError on None) or 503 if the router checked
        assert resp.status_code in (500, 503)

    @pytest.mark.asyncio
    async def test_pending_requests_no_user(self, client):
        """GET /friends/{id}/pending for non-existent user returns 500/503."""
        resp = await client.get("/friends/nonexistent-id/pending")
        assert resp.status_code in (500, 503)

    @pytest.mark.asyncio
    async def test_unfriend_no_user(self, client):
        """DELETE /friends/{uid}/unfriend/{fid} returns 500/503."""
        resp = await client.delete("/friends/user-1/unfriend/user-2")
        assert resp.status_code in (500, 503)


# ═════════════════════════════════════════════════════════════════════════
#  User Endpoints
# ═════════════════════════════════════════════════════════════════════════


class TestUsers:
    @pytest.mark.asyncio
    async def test_create_user_missing_params(self, client):
        """POST /users — session dependency resolves first → 503."""
        resp = await client.post("/users")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, client):
        """GET /users/{id} for non-existent ID returns 500/503."""
        resp = await client.get("/users/nonexistent-id")
        assert resp.status_code in (500, 503)

    @pytest.mark.asyncio
    async def test_search_users(self, client):
        """GET /users with query returns 500/503 gracefully."""
        resp = await client.get("/users", params={"q": "test"})
        assert resp.status_code in (500, 503)

    @pytest.mark.asyncio
    async def test_suggestions_no_user(self, client):
        """GET /users/{id}/suggestions for non-existent returns 500/503."""
        resp = await client.get("/users/nonexistent-id/suggestions")
        assert resp.status_code in (500, 503)


# ═════════════════════════════════════════════════════════════════════════
#  Event Endpoints
# ═════════════════════════════════════════════════════════════════════════


class TestEvents:
    @pytest.mark.asyncio
    async def test_create_event_no_body(self, client):
        """POST /events — session dependency resolves first → 503."""
        resp = await client.post("/events")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_get_event_not_found(self, client):
        """GET /events/{id} — session dependency resolves first → 503."""
        resp = await client.get("/events/nonexistent-id")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_list_events(self, client):
        """GET /events returns 503 gracefully."""
        resp = await client.get("/events")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_update_event_not_found(self, client):
        """PATCH /events/{id} — session dependency resolves first → 503."""
        resp = await client.patch("/events/nonexistent-id", json={"name": "New Name"})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_delete_event_not_found(self, client):
        """DELETE /events/{id} — session dependency resolves first → 503."""
        resp = await client.delete("/events/nonexistent-id")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_rsvp_no_body(self, client):
        """POST /events/{id}/rsvp — session dependency resolves first → 503."""
        resp = await client.post("/events/nonexistent-id/rsvp", json={})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_list_attendees(self, client):
        """GET /events/{id}/attendees — session dependency resolves first → 503."""
        resp = await client.get("/events/nonexistent-id/attendees")
        assert resp.status_code == 503


# ═════════════════════════════════════════════════════════════════════════
#  Camp Endpoints
# ═════════════════════════════════════════════════════════════════════════


class TestCamps:
    @pytest.mark.asyncio
    async def test_create_camp_no_body(self, client):
        """POST /camps — session dependency resolves first → 503."""
        resp = await client.post("/camps")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_get_camp_not_found(self, client):
        """GET /camps/{id} — session dependency resolves first → 503."""
        resp = await client.get("/camps/nonexistent-id")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_list_camps(self, client):
        """GET /camps returns 503 gracefully."""
        resp = await client.get("/camps")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_update_camp_not_found(self, client):
        """PATCH /camps/{id} — session dependency resolves first → 503."""
        resp = await client.patch("/camps/nonexistent-id", json={"name": "New Camp"})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_delete_camp_not_found(self, client):
        """DELETE /camps/{id} — session dependency resolves first → 503."""
        resp = await client.delete("/camps/nonexistent-id")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_join_camp(self, client):
        """POST /camps/{id}/join — session dependency resolves first → 503."""
        resp = await client.post("/camps/nonexistent-id/join")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_leave_camp(self, client):
        """POST /camps/{id}/leave — session dependency resolves first → 503."""
        resp = await client.post("/camps/nonexistent-id/leave")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_list_camp_members(self, client):
        """GET /camps/{id}/members — session dependency resolves first → 503."""
        resp = await client.get("/camps/nonexistent-id/members")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_promote_member(self, client):
        """POST /camps/{id}/promote — session dependency resolves first → 503."""
        resp = await client.post("/camps/nonexistent-id/promote")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_demote_member(self, client):
        """POST /camps/{id}/demote — session dependency resolves first → 503."""
        resp = await client.post("/camps/nonexistent-id/demote")
        assert resp.status_code == 503


# ═════════════════════════════════════════════════════════════════════════
#  Group Endpoints
# ═════════════════════════════════════════════════════════════════════════


class TestGroups:
    @pytest.mark.asyncio
    async def test_create_group_no_body(self, client):
        """POST /groups — session dependency resolves first → 503."""
        resp = await client.post("/groups")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_get_group_not_found(self, client):
        """GET /groups/{id} — session dependency resolves first → 503."""
        resp = await client.get("/groups/nonexistent-id")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_list_groups(self, client):
        """GET /groups returns 503 gracefully."""
        resp = await client.get("/groups")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_update_group_not_found(self, client):
        """PATCH /groups/{id} — session dependency resolves first → 503."""
        resp = await client.patch("/groups/nonexistent-id", json={"name": "New Group"})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_delete_group_not_found(self, client):
        """DELETE /groups/{id} — session dependency resolves first → 503."""
        resp = await client.delete("/groups/nonexistent-id")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_join_group(self, client):
        """POST /groups/{id}/join — session dependency resolves first → 503."""
        resp = await client.post("/groups/nonexistent-id/join")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_leave_group(self, client):
        """POST /groups/{id}/leave — session dependency resolves first → 503."""
        resp = await client.post("/groups/nonexistent-id/leave")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_list_group_members(self, client):
        """GET /groups/{id}/members — session dependency resolves first → 503."""
        resp = await client.get("/groups/nonexistent-id/members")
        assert resp.status_code == 503


# ═════════════════════════════════════════════════════════════════════════
#  Post Endpoints
# ═════════════════════════════════════════════════════════════════════════


class TestPosts:
    @pytest.mark.asyncio
    async def test_create_post_no_body(self, client):
        """POST /posts — session dependency resolves first → 503."""
        resp = await client.post("/posts", json={})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_get_post_not_found(self, client):
        """GET /posts/{id} — session dependency resolves first → 503."""
        resp = await client.get("/posts/nonexistent-id")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_update_post_not_found(self, client):
        """PATCH /posts/{id} — session dependency resolves first → 503."""
        resp = await client.patch("/posts/nonexistent-id", json={"content": "new"})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_delete_post_not_found(self, client):
        """DELETE /posts/{id} — session dependency resolves first → 503."""
        resp = await client.delete("/posts/nonexistent-id")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_list_user_posts(self, client):
        """GET /posts/user/{id} — session dependency resolves first → 503."""
        resp = await client.get("/posts/user/nonexistent-id")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_like_post(self, client):
        """POST /posts/{id}/like — session dependency resolves first → 503."""
        resp = await client.post("/posts/nonexistent-id/like")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_unlike_post(self, client):
        """DELETE /posts/{id}/like — session dependency resolves first → 503."""
        resp = await client.delete("/posts/nonexistent-id/like")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_get_likes(self, client):
        """GET /posts/{id}/likes — session dependency resolves first → 503."""
        resp = await client.get("/posts/nonexistent-id/likes")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_add_comment_no_body(self, client):
        """POST /posts/{id}/comments — session dependency resolves first → 503."""
        resp = await client.post("/posts/nonexistent-id/comments", json={})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_list_comments(self, client):
        """GET /posts/{id}/comments — session dependency resolves first → 503."""
        resp = await client.get("/posts/nonexistent-id/comments")
        assert resp.status_code == 503


# ═════════════════════════════════════════════════════════════════════════
#  Feed Endpoints
# ═════════════════════════════════════════════════════════════════════════


class TestFeed:
    @pytest.mark.asyncio
    async def test_feed_no_user(self, client):
        """GET /feed/{id} — session dependency resolves first → 503."""
        resp = await client.get("/feed/nonexistent-id")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_feed_with_cursor(self, client):
        """GET /feed/{id} with cursor — session dependency resolves first → 503."""
        resp = await client.get("/feed/nonexistent-id", params={"cursor": "2025-01-01T00:00:00"})
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_feed_validation(self, client):
        """GET /feed/{id} with limit > 100 — session dependency resolves first → 503."""
        resp = await client.get("/feed/nonexistent-id", params={"limit": 999})
        assert resp.status_code == 503


# ═════════════════════════════════════════════════════════════════════════
#  CORS Headers
# ═════════════════════════════════════════════════════════════════════════


class TestCORS:
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client):
        """CORS headers are returned for allowed origins."""
        resp = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI's CORSMiddleware should return 200 with CORS headers
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

    @pytest.mark.asyncio
    async def test_cors_blocked_for_unknown_origin(self, client):
        """CORS headers should NOT include unknown origins."""
        resp = await client.get(
            "/health",
            headers={"Origin": "http://evil.com"},
        )
        # CORSMiddleware with explicit origins won't echo back evil.com
        cors = resp.headers.get("access-control-allow-origin", "")
        assert "evil.com" not in cors
