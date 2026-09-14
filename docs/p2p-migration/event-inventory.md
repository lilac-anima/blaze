# Current mutation inventory

This inventory covers every mutating HTTP route found under `backend/app` during Phase 0. Read-only routes are listed only where useful for context. Event names below are proposed domain names, not an implemented wire format; authorization and merge rules must be validated again when Phase 1 specifies events.

Common rules: the current API uses caller-supplied IDs in several payloads/query parameters and Neo4j-backed route checks. Future events must use signed authorship plus object-scoped authorization. Unknown, unauthorized, or unverifiable events are quarantined; deletion is represented as a tombstone rather than physical peer deletion unless a later policy says otherwise. Visibility is marked `public`, `social`, `group/camp`, or `private/compatibility` as an initial classification.

| Current method and path | Proposed event | Author / authorization | Target and payload | Merge / tombstone / visibility |
|---|---|---|---|---|
| `POST /api/auth/register` | `identity.registered` (compatibility only) | Server account authority; no peer equivalent yet | User credentials and initial profile | Not peer-replicated; private compatibility data |
| `POST /api/auth/login` | None (session operation) | Server validates password | Token issuance | No event; private compatibility |
| `POST /api/auth/refresh` | None (session operation) | Server validates refresh token | Token rotation | No event; private compatibility |
| `POST /api/auth/password-reset/request` | None | Server/email authority | Reset request | No peer event; private |
| `POST /api/auth/password-reset/confirm` | None | Valid reset token | New password | No peer event; private; distinct from identity recovery |
| `PATCH /api/users/me` | `profile.updated` | Profile identity | Burner profile fields | Versioned field updates; prior history retained; public or social per field |
| `POST /users` | `profile.created` (legacy compatibility) | Creating identity/server compatibility | User identity/profile | Idempotent by identity; profile visibility policy |
| `POST /friends/request` | `friend.requested` | Requesting identity | Target user and optional message | State machine; no physical delete; social |
| `POST /friends/request/{request_id}/accept` | `friend.accepted` | Request recipient (or defined policy) | Friend request | State transition; social |
| `POST /friends/request/{request_id}/reject` | `friend.rejected` | Request recipient | Friend request | State transition; social |
| `DELETE /friends/{user_id}/unfriend/{friend_id}` | `friend.removed` | Either friend under policy | Friendship pair | Revocable relationship event; social |
| `POST /events` | `event.created` | Creating identity | Event fields | Append-only creation; public or group/camp |
| `PATCH /events/{event_id}` | `event.updated` | Event creator/organizer | Changed event fields | Versioned updates; history retained; same visibility |
| `DELETE /events/{event_id}` | `event.tombstoned` | Event creator/authorized organizer | Event ID and reason | Tombstone; no guarantee of global erasure; same visibility |
| `POST /events/{event_id}/rsvp` | `event.rsvp.updated` | Attendee identity | Event ID and RSVP status | Derived current RSVP; organizer capacity policy; event visibility |
| `POST /events/{event_id}/promote` | `event.role.granted` | Event organizer | Attendee and role | Scoped authorization grant; event/group visibility |
| `POST /events/{event_id}/demote` | `event.role.revoked` | Event organizer | Attendee and role | Scoped revocation; event/group visibility |
| `POST /events/{event_id}/posts` | `post.created` with event target | Author, subject to event policy | Post content/event ID | Append-only; edits/tombstones; event visibility |
| `POST /camps` | `camp.created` | Creating identity | Camp fields | Append-only; public or camp |
| `PATCH /camps/{camp_id}` | `camp.updated` | Camp lead/authorized role | Changed camp fields | Versioned updates; camp visibility |
| `DELETE /camps/{camp_id}` | `camp.tombstoned` | Camp lead/authorized role | Camp ID | Tombstone; camp visibility |
| `POST /camps/{camp_id}/join` | `camp.membership.requested` or `camp.membership.added` | User, then camp policy | Camp and user | Policy-dependent request/approval; camp visibility |
| `POST /camps/{camp_id}/leave` | `camp.membership.removed` | Member or camp authority | Camp and user | Revocable membership; camp visibility |
| `POST /camps/{camp_id}/promote` | `camp.role.granted` | Camp lead | Member and role | Scoped authorization grant; camp visibility |
| `POST /camps/{camp_id}/demote` | `camp.role.revoked` | Camp lead | Member and role | Scoped revocation; camp visibility |
| `POST /groups` | `group.created` | Creating identity | Group fields/policy | Append-only; public or group |
| `PATCH /groups/{group_id}` | `group.updated` | Group admin/authorized role | Changed group fields | Versioned updates; group visibility |
| `DELETE /groups/{group_id}` | `group.tombstoned` | Group admin/authorized role | Group ID | Tombstone; group visibility |
| `POST /groups/{group_id}/join` | `group.membership.requested` or `group.membership.added` | User, then group policy | Group and user | Policy-dependent request/approval; group visibility |
| `POST /groups/{group_id}/leave` | `group.membership.removed` | Member or group authority | Group and user | Revocable membership; group visibility |
| `POST /posts` | `post.created` | Author identity | Post content, optional event target | Append-only; public/social/group |
| `PATCH /posts/{post_id}` | `post.updated` | Post author/authorized moderator | Post ID and content | Versioned edits; history retained; original visibility |
| `DELETE /posts/{post_id}` | `post.tombstoned` | Post author/authorized moderator | Post ID/reason | Tombstone; no global erasure guarantee; original visibility |
| `POST /posts/{post_id}/like` | `post.liked` | User identity | Post ID | Set-derived with unlike; target visibility |
| `DELETE /posts/{post_id}/like` | `post.unliked` | User identity | Post ID | Set-derived/revocable; target visibility |
| `POST /posts/{post_id}/comments` | `comment.created` | Comment author and post visibility | Post ID/content | Append-only; comment tombstone policy later; inherited visibility |

## Areas not present or unsupported

- There is no dedicated moderation router or moderation endpoint in the current backend. Moderation-like authority exists only as camp/event role promotion and demotion; no `moderation.*` event is claimed for a nonexistent route.
- There is no direct comment update/delete endpoint; only comment creation and listing are present.
- There is no group invitation/approval or group admin promotion/demotion endpoint in the current router.
- There is no explicit camp/event capacity mutation endpoint; capacity is part of event behavior.
- Login, refresh, password reset, and other session/account-secret operations are intentionally not peer events.
- GET routes (search, feeds, members, attendees, likes, comments, and listings) do not create events. They read current projections and are not omitted mutations.
