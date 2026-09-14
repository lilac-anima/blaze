# Phase 0 baseline

Captured 2026-09-13 from the working tree at `C:/Users/Lilac/Projects/burner-social`.

## Repository state

- The directory is not a Git repository: `git rev-parse HEAD` returned `fatal: not a git repository (or any of the parent directories)`. There is therefore no commit identifier, branch, or Git diff to record.
- Available project metadata: `pyproject.toml` identifies `blaze` version `0.1.0`; `frontend/package.json` identifies the frontend as version `0.0.0`.
- No source files were changed by Phase 0 runtime code; this phase adds documentation only.

## Current architecture and dependencies

- Frontend: Svelte 5 + Vite + `svelte-spa-router` in `frontend/`; default dev port 5173.
- Backend: FastAPI in `backend/app`; Uvicorn default port 8000.
- Persistence: Neo4j via the async Python driver and Bolt, default `bolt://localhost:7687`. Route dependencies raise 503 when Neo4j is unavailable, although startup checks degrade gracefully.
- Authentication: password registration/login and bcrypt password hashes; short-lived access and longer-lived refresh JWTs using HS256 and `JWT_SECRET_KEY`. Bearer tokens are validated by FastAPI dependencies. Password reset uses JWT reset tokens. This is compatibility authentication, not the future peer identity.
- Models/entities represented in the current backend include users and burner profiles, friend requests/friendships, posts, comments, likes, events and RSVPs/attendees, camps and camp membership/roles, groups and group membership/roles, feeds, and health status.

## Backend route surface

Routes are mounted without a global API prefix:

- `/api/auth`: register, login, refresh, password-reset request, password-reset confirm.
- `/api/users`: current profile GET/PATCH; user create, lookup, search, and suggestions.
- `/friends`: friend request, accept, reject, list/pending, unfriend.
- `/users`: user create, lookup, search, suggestions (legacy/current router surface; see application route registration).
- `/events`: create/list/get, update/delete, RSVP, attendees, promote/demote attendee, event posts and event posts listing.
- `/camps`: create/list/get, update/delete, join/leave, members, promote/demote member.
- `/groups`: create/list/get, update/delete, join/leave, members.
- `/posts`: create/get, update/delete, user posts, like/unlike, likes, comments, comment listing.
- `/feed`: personalized feed lookup.
- `/health`: API/Neo4j health check.

The complete mutation inventory, with method and path, is in [event-inventory.md](event-inventory.md). Existing route behavior is intentionally unchanged.

## Verification baseline

Commands run before/alongside documentation changes:

- Backend: `cd backend && python -m pytest tests/ --tb=short -v`
  - Result: failed during collection (exit code 2), 0 tests collected, 4 collection errors.
  - Pre-existing/environment failures observed: `httpx` is missing from the Python 3.9.7 interpreter used by `pytest`; `test_camp_flow.py` and `test_event_flow.py` execute live-style setup at import and then raise `TypeError` after failed requests; `test_e2e_live.py` cannot connect because no backend is listening (`WinError 10061`). Pytest also reports an old `asyncio_mode` config warning under the installed pytest/plugin set.
- Frontend: `cd frontend && npm run build`
  - Result: passed (Vite 8.1.5; 176 modules transformed; exit code 0).
  - Existing warning: unused CSS selector `.form-select` in `src/lib/components/CreateCampModal.svelte`.

These results describe the environment at baseline capture; the backend failures are not caused by the documentation changes.
