"""Regression coverage for the registration and login request path."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.database import get_session
from backend.app.main import app


class _Result:
    def __init__(self, record=None):
        self._record = record

    async def single(self):
        return self._record


class _RegistrationSession:
    """Minimal async Neo4j session double for the HTTP auth flow."""

    def __init__(self):
        self.calls = []
        self.user = None

    async def run(self, query, **parameters):
        self.calls.append((query, parameters))
        if "CREATE (u:User" in query:
            self.user = {
                "user_id": parameters["user_id"],
                "username": parameters["username"],
                "password_hash": parameters["password_hash"],
            }
            return _Result()
        if "MATCH (u:User)" in query:
            if self.user and parameters.get("login") == self.user["username"]:
                return _Result({"u": self.user})
            return _Result()
        raise AssertionError(f"Unexpected query: {query}")


@pytest.mark.asyncio
async def test_register_then_login_returns_tokens_without_http_500():
    session = _RegistrationSession()

    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            registration = await client.post(
                "/api/auth/register",
                json={
                    "email": "regression@example.test",
                    "username": "regression_user",
                    "burner_name": "Regression Burner",
                    "password": "secret12345",
                },
            )
            assert registration.status_code == 201, registration.text
            assert registration.json()["access_token"]
            assert registration.json()["refresh_token"]

            login = await client.post(
                "/api/auth/login",
                json={"login": "regression_user", "password": "secret12345"},
            )
            assert login.status_code == 200, login.text
            assert login.json()["access_token"]
            assert login.json()["refresh_token"]
    finally:
        app.dependency_overrides.pop(get_session, None)
