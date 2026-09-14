"""
End-to-end smoke test for Blaze.

This script verifies that the backend API and frontend are both operational.
It does NOT require Neo4j — it tests graceful degradation mode and basic
connectivity.

Usage:
    python backend/tests/e2e_smoke.py              # test only backend
    python backend/tests/e2e_smoke.py --frontend    # test both backend and frontend
"""

import argparse
import sys
import urllib.request
import json
import time


def check_backend(base_url="http://localhost:8000"):
    """Check that the backend API is responding correctly."""
    print(f"=== Backend Smoke Test ({base_url}) ===")
    passed = 0
    failed = 0

    # 1. Health endpoint
    try:
        resp = urllib.request.urlopen(f"{base_url}/health", timeout=5)
        data = json.loads(resp.read().decode())
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        assert data["status"] in ("ok", "degraded", "error")
        print(f"  ✓ /health — status={data['status']}, neo4j={data['neo4j_connected']}")
        passed += 1
    except Exception as e:
        print(f"  ✗ /health — {e}")
        failed += 1

    # 2. OpenAPI schema
    try:
        resp = urllib.request.urlopen(f"{base_url}/openapi.json", timeout=5)
        schema = json.loads(resp.read().decode())
        paths = schema["paths"]
        assert "/api/auth/register" in paths
        assert "/friends/request" in paths
        assert "/events" in paths
        assert "/camps" in paths
        assert "/groups" in paths
        assert "/posts" in paths
        assert "/feed/{user_id}" in paths
        print(f"  ✓ /openapi.json — {len(paths)} paths registered")
        passed += 1
    except Exception as e:
        print(f"  ✗ /openapi.json — {e}")
        failed += 1

    # 3. Auth refresh (stateless, no DB needed)
    try:
        req = urllib.request.Request(
            f"{base_url}/api/auth/refresh",
            data=json.dumps({"refresh_token": "bad-token"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as e:
            resp = e

        assert resp.status == 401, f"Expected 401, got {resp.status}"
        print(f"  ✓ POST /api/auth/refresh (bad token) — 401")
        passed += 1
    except Exception as e:
        print(f"  ✗ POST /api/auth/refresh — {e}")
        failed += 1

    # 4. CORS headers
    try:
        req = urllib.request.Request(f"{base_url}/health", method="OPTIONS")
        req.add_header("Origin", "http://localhost:5173")
        req.add_header("Access-Control-Request-Method", "GET")
        try:
            resp = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as e:
            resp = e

        cors = resp.headers.get("Access-Control-Allow-Origin", "")
        if "localhost:5173" in cors:
            print(f"  ✓ CORS headers present — origin allowed")
            passed += 1
        else:
            print(f"  ✗ CORS — expected localhost:5173, got '{cors}'")
            failed += 1
    except Exception as e:
        print(f"  ✗ CORS check — {e}")
        failed += 1

    total = passed + failed
    print(f"\nBackend: {passed}/{total} checks passed")
    return failed == 0


def check_frontend(base_url="http://localhost:5173"):
    """Check that the frontend dev server is responding."""
    print(f"\n=== Frontend Smoke Test ({base_url}) ===")
    passed = 0
    failed = 0

    try:
        resp = urllib.request.urlopen(base_url, timeout=5)
        html = resp.read().decode()
        assert resp.status == 200
        assert "burner" in html.lower() or "social" in html.lower() or "svelte" in html.lower() or "app" in html.lower()
        print(f"  ✓ Frontend index served — {resp.status}")
        passed += 1
    except Exception as e:
        print(f"  ✗ Frontend index — {e}")
        failed += 1

    # Try the built version too
    try:
        resp = urllib.request.urlopen(
            f"{base_url.replace(':5173', ':4173')}", timeout=5
        )
        print(f"  ✓ Preview server responded — {resp.status}")
        passed += 1
    except Exception:
        print(f"  - Preview server not running (optional)")

    total = passed + failed
    print(f"\nFrontend: {passed}/{max(passed, 1)} checks passed")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Blaze E2E smoke test")
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument("--frontend-url", default="http://localhost:5173")
    parser.add_argument("--frontend", action="store_true", help="Also test frontend")
    args = parser.parse_args()

    backend_ok = check_backend(args.backend_url)
    frontend_ok = True
    if args.frontend:
        frontend_ok = check_frontend(args.frontend_url)

    if backend_ok and frontend_ok:
        print("\n✓ All smoke tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some smoke tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
