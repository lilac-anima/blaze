"""Integration test: full camp flow (search, create, join, promote, demote, leave)."""
import json, urllib.request, time

B = 'http://localhost:8000'
s = str(int(time.time()))[-6:]
U1 = f'camp{s}'
U2 = f'camp2{str(int(time.time()))[-5:]}'


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
    if c: p += 1; print(f'  ✓ {lbl}')
    else: f += 1; print(f'  ✗ {lbl}')


# 1-3. Register + login user1
r = req('POST', '/api/auth/register', {'email': f'{U1}@x.org', 'username': U1, 'password': 'test1234', 'burner_name': 'CampTester'})
T1 = r.get('access_token', ''); ok('register user1', bool(T1))
r = req('POST', '/api/auth/login', {'login': U1, 'password': 'test1234'})
T1 = r.get('access_token', ''); ok('login user1', bool(T1))
UID1 = req('GET', '/api/users/me', tok=T1).get('user', {}).get('user_id', '')
ok('got uid1', bool(UID1))

# 4. Create camp
r = req('POST', f'/camps?created_by={UID1}', {'name': 'IntegrationTestCamp', 'description': 'Test', 'location_on_playa': '3&D'}, tok=T1)
CID = r.get('camp_id', ''); ok('create camp', bool(CID))

# 5. Search by name
r = req('GET', '/camps?q=IntegrationTestCamp')
ok('search by name', isinstance(r, list) and any(c['camp_id'] == CID for c in r))

# 6. Camp detail
r = req('GET', f'/camps/{CID}'); ok('get camp detail', r.get('name') == 'IntegrationTestCamp')

# 7. Members (creator = lead)
r = req('GET', f'/camps/{CID}/members')
ok('creator is lead', any(m['role'] == 'lead' for m in r))
ok('1 member', len(r) == 1)

# 8-9. Register user2
r = req('POST', '/api/auth/register', {'email': f'{U2}@x.org', 'username': U2, 'password': 'test1234', 'burner_name': 'Member2'})
ok('register user2', bool(r.get('access_token', '')))
r = req('POST', '/api/auth/login', {'login': U2, 'password': 'test1234'})
T2 = r.get('access_token', ''); UID2 = req('GET', '/api/users/me', tok=T2).get('user', {}).get('user_id', '')
ok('got uid2', bool(UID2))

# 10. User2 joins
r = req('POST', f'/camps/{CID}/join?user_id={UID2}')
ok('user2 joins', r.get('_error') != 404)

# 11. 2 members
r = req('GET', f'/camps/{CID}/members'); ok('2 members', len(r) == 2)

# 12. Promote to moderator
r = req('POST', f'/camps/{CID}/promote?user_id={UID2}&promoted_by={UID1}')
ok('promote to mod', r.get('_error') != 403)

# 13. Verify role
r = req('GET', f'/camps/{CID}/members')
m2 = next((m for m in r if m['user_id'] == UID2), None)
ok('user2 is moderator', m2 and m2['role'] == 'moderator')

# 14. Demote
r = req('POST', f'/camps/{CID}/demote?user_id={UID2}&demoted_by={UID1}')
ok('demote to member', r.get('_error') != 403)

# 15. Verify
r = req('GET', f'/camps/{CID}/members')
m2 = next((m for m in r if m['user_id'] == UID2), None)
ok('user2 is member', m2 and m2['role'] == 'member')

# 16. User2 leaves
r = req('POST', f'/camps/{CID}/leave?user_id={UID2}')
ok('user2 leaves', r.get('_error') != 404)

# 17. Back to 1
r = req('GET', f'/camps/{CID}/members'); ok('1 member', len(r) == 1)

print(f'\n✅ {p}/{p + f} checks passed' if f == 0 else f'\n❌ {p}/{p + f} checks passed, {f} failed')
