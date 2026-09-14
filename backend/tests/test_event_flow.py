"""Integration test: event search, organizer roles, event posts."""
import json, urllib.request, time

B = 'http://localhost:8000'
s = str(int(time.time()))[-6:]
U1 = f'evt{s}'
U2 = f'evt2{str(int(time.time()))[-5:]}'


def req(m, p, d=None, tok=None):
    url = f'{B}{p}'; body = json.dumps(d).encode() if d else None
    h = {'Content-Type': 'application/json'}
    if tok: h['Authorization'] = f'Bearer {tok}'
    r = urllib.request.Request(url, data=body, headers=h, method=m)
    try:
        resp = urllib.request.urlopen(r, timeout=5)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read())
        except: return {'_error': e.code}
    except Exception as e: return {'_error': str(e)}


p = 0; f = 0
def ok(lbl, c):
    global p, f
    if c: p += 1; print(f'  \u2713 {lbl}')
    else: f += 1; print(f'  \u2717 {lbl}')


# 1-3. Register + login user1
r = req('POST', '/api/auth/register', {'email': f'{U1}@x.org', 'username': U1, 'password': 'test1234', 'burner_name': 'EventTester'})
T1 = r.get('access_token', ''); ok('register user1', bool(T1))
r = req('POST', '/api/auth/login', {'login': U1, 'password': 'test1234'})
T1 = r.get('access_token', ''); ok('login user1', bool(T1))
UID1 = req('GET', '/api/users/me', tok=T1).get('user', {}).get('user_id', '')
ok('got uid1', bool(UID1))

# 4. Register user2
r = req('POST', '/api/auth/register', {'email': f'{U2}@x.org', 'username': U2, 'password': 'test1234', 'burner_name': 'EventMember'})
ok('register user2', bool(r.get('access_token', '')))
r = req('POST', '/api/auth/login', {'login': U2, 'password': 'test1234'})
T2 = r.get('access_token', ''); UID2 = req('GET', '/api/users/me', tok=T2).get('user', {}).get('user_id', '')
ok('got uid2', bool(UID2))

# ── Task 1: Event Search ────────────────────────────────────────────────

# 5. Create an event
r = req('POST', f'/events?created_by={UID1}', {'name': 'SearchableEvent', 'date': '2026-09-01', 'description': 'Test event for search'})
EID = r.get('event_id', ''); ok('create event', bool(EID))

# 6. Search by exact name
r = req('GET', f'/events?q=SearchableEvent')
ok('search by exact name', isinstance(r, list) and any(e['event_id'] == EID for e in r))

# 7. Search case-insensitive
r = req('GET', '/events?q=searchableevent')
ok('search case-insensitive', isinstance(r, list) and any(e['event_id'] == EID for e in r))

# 8. Search partial match
r = req('GET', '/events?q=archable')
ok('search partial match', isinstance(r, list) and any(e['event_id'] == EID for e in r))

# 9. Search no match
r = req('GET', '/events?q=ZZZNOEXIST')
ok('search no match', isinstance(r, list) and len(r) == 0)

# 10. List all (no filter)
r = req('GET', '/events')
ok('list all events', isinstance(r, list) and len(r) >= 1)

# ── Task 2: Organizer Roles ─────────────────────────────────────────────

# 11. Creator is organizer
r = req('GET', f'/events/{EID}/attendees')
creator_att = next((a for a in r if a['user_id'] == UID1), None)
ok('creator is attendee', creator_att is not None)
ok('creator role is organizer', creator_att and creator_att.get('role') == 'organizer')

# 12. User2 RSVPs as going
r = req('POST', f'/events/{EID}/rsvp', {'user_id': UID2, 'status': 'going'})
ok('user2 RSVPs going', r.get('status') == 'going')

# 13. User2 has no role (plain attendee)
r = req('GET', f'/events/{EID}/attendees')
m2 = next((a for a in r if a['user_id'] == UID2), None)
ok('user2 is attendee', m2 is not None)
ok('user2 has no role', m2 and m2.get('role') is None)

# 14. Non-organizer cannot promote
r = req('POST', f'/events/{EID}/promote', {'user_id': UID2, 'promoted_by': UID2})
ok('non-organizer cannot promote', r.get('_error') == 403 or '403' in str(r))

# 15. Organizer promotes user2
r = req('POST', f'/events/{EID}/promote', {'user_id': UID2, 'promoted_by': UID1})
ok('promote to organizer', r.get('_error') != 403 and r.get('_error') != 404)

# 16. Verify user2 is now organizer
r = req('GET', f'/events/{EID}/attendees')
m2 = next((a for a in r if a['user_id'] == UID2), None)
ok('user2 is organizer', m2 and m2.get('role') == 'organizer')

# 17. Cannot promote again
r = req('POST', f'/events/{EID}/promote', {'user_id': UID2, 'promoted_by': UID1})
ok('cannot promote twice', r.get('_error') == 409 or '409' in str(r))

# 18. Demote user2
r = req('POST', f'/events/{EID}/demote', {'user_id': UID2, 'promoted_by': UID1})
ok('demote from organizer', r.get('_error') != 403 and r.get('_error') != 404)

# 19. Verify user2 is back to no role
r = req('GET', f'/events/{EID}/attendees')
m2 = next((a for a in r if a['user_id'] == UID2), None)
ok('user2 demoted', m2 and m2.get('role') is None)

# 20. Non-organizer cannot demote
r = req('POST', f'/events/{EID}/demote', {'user_id': UID2, 'promoted_by': UID2})
ok('non-organizer cannot demote', r.get('_error') == 403 or '403' in str(r))

# 21. Cannot demote someone who is not an organizer
r = req('POST', f'/events/{EID}/demote', {'user_id': UID2, 'promoted_by': UID1})
ok('cannot demote non-organizer', r.get('_error') == 400 or '400' in str(r))

# ── Task 3: Event Posts ─────────────────────────────────────────────────

# 22. Create an event post
r = req('POST', f'/events/{EID}/posts', {'author_id': UID1, 'content': 'This is an event post!'})
ok('create event post', r.get('_error') != 404)
POST_ID = r.get('post_id', '')
ok('got post_id', bool(POST_ID))
ok('post has event_id', r.get('event_id') == EID)
ok('post has author', r.get('author_id') == UID1)

# 23. Create a second post
r = req('POST', f'/events/{EID}/posts', {'author_id': UID2, 'content': 'Second event post!'})
POST2_ID = r.get('post_id', '')
ok('create second event post', bool(POST2_ID))

# 24. List event posts
r = req('GET', f'/events/{EID}/posts')
ok('list event posts', isinstance(r, list) and len(r) >= 2)
ok('includes first post', any(p['post_id'] == POST_ID for p in r))
ok('includes second post', any(p['post_id'] == POST2_ID for p in r))
ok('posts newest first', r[0]['created_at'] >= r[1]['created_at'])

# 25. Like a post
r = req('POST', f'/posts/{POST_ID}/like?user_id={UID1}')
ok('like event post', r.get('_error') != 404)

# 26. Comment on a post
r = req('POST', f'/posts/{POST_ID}/comments', {'user_id': UID2, 'content': 'Great post!'})
ok('comment on event post', r.get('_error') != 404)

# 27. Verify likes/comments appear on event post list
r = req('GET', f'/events/{EID}/posts')
p1 = next((p for p in r if p['post_id'] == POST_ID), None)
ok('post has likes', p1 and p1['like_count'] >= 1)
ok('post has comments', p1 and p1['comment_count'] >= 1)


print(f'\n\u2705 {p}/{p + f} checks passed' if f == 0 else f'\n\u274c {p}/{p + f} checks passed, {f} failed')
