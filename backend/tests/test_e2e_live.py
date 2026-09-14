"""Full E2E test for Blaze with live Neo4j."""
import json
import time
import urllib.request

BASE = "http://localhost:8000"
SUFFIX = str(int(time.time()))[-6:]
UNIQUE = f"e2e{SUFFIX}"

def req(method, path, data=None, token=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=5)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read())
        except Exception:
            detail = e.read().decode()
        return {"_error": e.code, "_detail": detail}

passed = 0
failed = 0

def check(label, ok):
    global passed, failed
    if ok:
        print(f"  ✓ {label}")
        passed += 1
    else:
        print(f"  ✗ {label}")
        failed += 1

# ── 1. Health ──
h = req("GET", "/health")
check("health ok + neo4j", h.get("status") == "ok" and h.get("neo4j_connected"))

# ── 2. Register ──
r = req("POST", "/api/auth/register", {
    "email": f"{UNIQUE}@playa.org", "username": UNIQUE,
    "password": "burn12345", "burner_name": "E2ETester",
    "display_name": "E2E Test", "home_camp": "E2E Camp",
    "years_attended": 3, "vibe": "🔥", "bio": "E2E testing!"
})
TOKEN = r.get("access_token", "")
check("register works", "access_token" in r)

# ── 3. Login ──
r = req("POST", "/api/auth/login", {"login": UNIQUE, "password": "burn12345"})
TOKEN = r.get("access_token", "")
check("login works", "access_token" in r)

# ── 4. Profile ──
r = req("GET", "/api/users/me", token=TOKEN)
UID = r.get("user", {}).get("user_id", "")
check("profile has user_id", bool(UID))
check("burner has playa_name", r.get("burner", {}).get("playa_name") == "E2ETester")

# ── 5. List users ──
r = req("GET", "/users")
check("users listed (6+)", isinstance(r, list) and len(r) >= 6)

# ── 6. Get user detail ──
r = req("GET", "/users/user-1")
check("sparklepony found", r.get("username") == "sparklepony")

# ── 7. Suggestions ──
r = req("GET", "/users/user-1/suggestions")
check("suggestions", isinstance(r, list))

# ── 8-9. Events ──
r = req("GET", "/events")
check("3 events", len(r) == 3)
r = req("GET", "/events/bm-2025")
check("BM2025 detail", r.get("name") == "Burning Man 2025")

# ── 10-12. Camps ──
r = req("GET", "/camps")
check("camps listed", isinstance(r, list) and len(r) >= 3)
r = req("POST", f"/camps?created_by={UID}", {
    "name": "Test Camp", "description": "A test camp", "location_on_playa": "3:00 & D"
}, token=TOKEN)
CID = r.get("camp_id", "")
check("camp created", bool(CID))
r = req("GET", f"/camps/{CID}")
check("camp name", r.get("name") == "Test Camp")

# ── 10b. Camp search by name ──
r = req("GET", "/camps?q=test")
check("search 'test' finds our camp", any(c.get("name") == "Test Camp" for c in r))
r = req("GET", "/camps?q=TEST")
check("search 'TEST' case-insensitive", any(c.get("name") == "Test Camp" for c in r))
r = req("GET", "/camps?q=xyzzy")
check("search 'xyzzy' returns empty", r == [])
r = req("GET", "/camps?q=")
check("search empty string returns all", isinstance(r, list) and len(r) >= 4)

# ── 11-12. Camp Members ──
r = req("GET", f"/camps/{CID}/members")
check("camp has creator as member", len(r) >= 1)
check("creator is lead role", any(m.get("user_id") == UID and m.get("role") == "lead" for m in r))

# ── 13-15. Second user for join/leave/promote ──
UNIQUE2 = f"{UNIQUE}v2"
r = req("POST", "/api/auth/register", {
    "email": f"{UNIQUE2}@playa.org", "username": UNIQUE2,
    "password": "burn12345", "burner_name": "E2ETester2",
    "display_name": "E2E Test 2", "home_camp": "Other Camp",
    "years_attended": 2, "vibe": "🌟", "bio": "Second E2E tester"
})
UID2 = r.get("user_id", "")
if not UID2 and "access_token" in r:
    r2 = req("GET", "/api/users/me", token=r["access_token"])
    UID2 = r2.get("user", {}).get("user_id", "")
check("second user registered", bool(UID2))

# ── 16. Join camp ──
if UID2:
    r = req("POST", f"/camps/{CID}/join?user_id={UID2}")
    check("second user joined camp", "joined" in r.get("message", "").lower())

# ── 17. Verify 2 members ──
r = req("GET", f"/camps/{CID}/members")
check("camp has 2 members", len(r) >= 2)
check("second user is member role", any(m.get("user_id") == UID2 and m.get("role") == "member" for m in r))

# ── 18. Promote to moderator ──
if UID2:
    r = req("POST", f"/camps/{CID}/promote?user_id={UID2}&promoted_by={UID}")
    check("promoted to moderator", "promoted" in r.get("message", "").lower())

# ── 19. Verify moderator role ──
r = req("GET", f"/camps/{CID}/members")
check("second user is now moderator", any(m.get("user_id") == UID2 and m.get("role") == "moderator" for m in r))

# ── 20. Demote back to member ──
if UID2:
    r = req("POST", f"/camps/{CID}/demote?user_id={UID2}&demoted_by={UID}")
    check("demoted to member", "demoted" in r.get("message", "").lower())

# ── 21. Verify member role ──
r = req("GET", f"/camps/{CID}/members")
check("second user is member again", any(m.get("user_id") == UID2 and m.get("role") == "member" for m in r))

# ── 22. Leave camp ──
if UID2:
    r = req("POST", f"/camps/{CID}/leave?user_id={UID2}")
    check("second user left camp", "left" in r.get("message", "").lower())

# ── 23. Verify 1 member after leave ──
r = req("GET", f"/camps/{CID}/members")
check("camp has 1 member after leave", len(r) == 1)

# ── 24-25. Groups ──
r = req("POST", f"/groups?created_by={UID}", {
    "name": "Test Group", "description": "A test group", "is_public": True
}, token=TOKEN)
GID = r.get("group_id", "")
check("group created", bool(GID))
r = req("GET", "/groups")
check("groups listed", isinstance(r, list) and len(r) >= 1)

# ── 15-17. Posts ──
r = req("POST", "/posts", {
    "author_id": UID, "content": "Hello playa! 🌵✨", "tags": ["test"]
}, token=TOKEN)
PID = r.get("post_id", "")
check("post created", bool(PID))
r = req("GET", f"/posts/{PID}") if PID else {}
check("post content", r.get("content", "").startswith("Hello playa!"))

# ── 18. Like ──
if PID:
    r = req("POST", f"/posts/{PID}/like?user_id={UID}")
    check("like works", r.get("user_id") == UID)

# ── 19. Comment ──
if PID:
    r = req("POST", f"/posts/{PID}/comments", {"user_id": UID, "content": "Nice! 🔥"})
    check("comment works", "comment_id" in r)

# ── 20. RSVP ──
r = req("POST", "/events/bm-2025/rsvp", {"user_id": UID, "status": "going"})
check("rsvp works", r.get("status") == "going")

# ── 21. Feed ──
r = req("GET", "/feed/user-1?limit=3")
check("feed returns items", isinstance(r, dict) and "items" in r)

# ── 22. Profile update ──
r = req("PATCH", "/api/users/me", {
    "user_update": {"username": f"{UNIQUE}v2"},
    "profile_update": {"bio": "Testing profile updates!", "home_camp": "Updated Camp"}
}, token=TOKEN)
check("profile username updated", r.get("user", {}).get("username") == f"{UNIQUE}v2")
check("bio updated", r.get("burner", {}).get("bio") == "Testing profile updates!")
check("home_camp updated", r.get("burner", {}).get("home_camp") == "Updated Camp")

# ── 23. Friend request ──
r = req("POST", "/friends/request", {"from_user_id": UID, "to_user_id": "user-1"})
check("friend request sent", r.get("_error") != 404)

# ── 24. Pending requests ──
r = req("GET", "/friends/user-1/pending")
check("user-1 has pending", isinstance(r, list) and len(r) >= 1)

# ── 25. Token refresh (use refresh token from initial login) ──
RTOKEN = req("POST", "/api/auth/login", {"login": f"{UNIQUE}v2", "password": "burn12345"}).get("refresh_token", "")
r = req("POST", "/api/auth/refresh", {"refresh_token": RTOKEN})
check("refresh works", "access_token" in r)

# ── 26. Attendees ──
r = req("GET", "/events/bm-2025/attendees")
check("bm-2025 has attendee", len(r) >= 1)

# ── 27. User posts ──
r = req("GET", f"/posts/user/{UID}")
check("user has posts", isinstance(r, list) and len(r) >= 1)

# ── 28. Password reset request ──
r = req("POST", "/api/auth/password-reset/request", {"email": f"{UNIQUE}@playa.org"})
check("pw reset accepted", r.get("_error") in (None, 202, 503))

# ── 29. Camps list (again, includes our created one) ──
r = req("GET", "/camps")
check("camps 4+ with ours", isinstance(r, list) and len(r) >= 4)

print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed of {passed+failed}")
