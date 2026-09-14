# Blaze 🏜️🔥

A local-first, community-operated social graph platform for the Burning Man community — connect with burners, find events, join camps and groups, and share your playa experience.

Blaze is being designed to evolve from its current FastAPI + Neo4j prototype into a peer-to-peer application. The long-term goal is not merely to remove one central server. The goal is to remove the requirement for a single authority to own identities, social data, feeds, and availability while keeping the application usable on ordinary phones.

## Project Status

The repository currently contains a working centralized prototype. The frontend also has an opt-in Phase 3 local-first preview controlled by `VITE_FEATURE_MODE`:

- `centralized` (default): existing JWT/API behavior.
- `local-first`: browser-generated signing identity, signed profile/post events, local projections, and offline local creation.
- `p2p-preview`: same local behavior while peer transport is still disabled.

Local-first data is local-only or pending sync until the compatibility bridge and peer synchronization phases land. A local identity is separate from a JWT account; device loss requires an encrypted recovery bundle or explicit identity rotation and never silently links a replacement identity to an old account. WebRTC, server event ingestion, and remote sync are intentionally not implemented in this phase.

The repository currently contains a working centralized prototype:

- FastAPI backend
- Neo4j graph database
- Svelte 5 frontend
- JWT/password authentication
- Server-side social graph queries and feeds

The decentralized architecture described below is the target architecture and migration plan. It is intentionally more specific than the current implementation; the sections marked "current" and "target" distinguish what exists from what we are building toward.

## P2P Migration Documentation

Phase 0 baseline and the authoritative protocol boundary are documented here:

- [Migration baseline](docs/p2p-migration/baseline.md)
- [Current mutation/event inventory](docs/p2p-migration/event-inventory.md)
- [Migration decisions](docs/p2p-migration/decisions.md)
- [Protocol documents](protocol/README.md)

These documents define the migration boundary without changing the current API.

## Design Goals

The architecture is guided by these goals:

1. No mandatory central authority for identity or social data.
2. Offline-first behavior: reading and creating content should work without an internet connection whenever the local replica has enough data.
3. Mobile usability: a participant's phone should be a useful peer even though mobile operating systems suspend background applications.
4. User-controlled identity: accounts should be portable between devices and not depend on a password database owned by one operator.
5. Verifiable authorship: peers must be able to verify who signed an object and whether it was altered.
6. Community operation: camps, regions, and trusted groups should be able to run durable nodes, relays, and archives.
7. Explicit privacy boundaries: public, group-scoped, and private content must not be treated as the same kind of data.
8. Incremental migration: the existing application should remain useful while the peer protocol is introduced.
9. Simple first implementation: the first networked milestone is two peers exchanging signed events, not a complete global mesh.

## Non-Goals

The project is not initially trying to:

- Make every phone a 24/7 server.
- Guarantee that replicated data can be permanently deleted everywhere.
- Eliminate every server. Relays, rendezvous services, and community nodes are useful and sometimes necessary for mobile connectivity.
- Build a globally consistent database with immediate worldwide agreement.
- Treat decentralization as a replacement for authorization, moderation, or abuse controls.
- Use a blockchain, token, cryptocurrency, or proof-of-work mechanism.

The intended model is best described as local-first, peer-to-peer, and community-operated rather than absolutely serverless.

## Current Prototype

### Features

- Burner profiles — playa names, home camps, years attended, vibe emoji, bio
- Friend connections — send/accept/reject friend requests, list friends
- Events — create, RSVP, attendee management with capacity limits
- Camps — create camps, join/leave, member management with lead roles
- Groups — public and invite-only groups, join/leave, member management with admin roles
- Posts and comments — create posts, like/unlike, comment threads
- News feed — personalized feed from friends and camp/group mates with cursor-based pagination
- User discovery — search by username, burner name, or home camp; friend-of-friend suggestions
- JWT authentication — access and refresh token pairs, password reset flow
- Graceful degradation — returns `503 Database unavailable` when Neo4j is offline

### Current Architecture

```text
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Svelte 5   │────▶│  FastAPI     │────▶│  Neo4j      │
│  Frontend   │     │  Backend     │     │  Graph DB   │
│  :5173      │     │  :8000       │     │  :7687      │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │
       │   JWT Bearer       │   Async Bolt
       │   Auth             │   Protocol
       └────────────────────┘
```

This is a useful prototype, but it has centralized assumptions:

- Neo4j is the authoritative source of truth.
- The backend creates and identifies users.
- JWTs are signed by one server secret.
- The backend decides whether a relationship or mutation is valid.
- The backend calculates personalized feeds.
- A database outage makes most API routes unavailable.
- A server operator can potentially read, modify, or delete all application data.

Those assumptions are intentionally being replaced, not hidden behind a P2P transport.

## Target Architecture

```text
                    Optional community infrastructure
             ┌─────────────────────────────────────────────┐
             │ rendezvous │ STUN/TURN │ relay │ archive    │
             └──────┬──────────┬──────────┬──────────┬─────┘
                    │          │          │          │
        ┌───────────┴───┐  ┌───┴────────┐  ┌────────┴──────┐
        │ Phone / PWA   │  │ Camp node  │  │ Desktop peer  │
        │ local replica │◀▶│ durable DB │◀▶│ local replica │
        │ local identity│  │ optional   │  │ local identity│
        └───────────────┘  └────────────┘  └───────────────┘
```

Every participant owns a local replica. Replicas exchange signed domain events. A local database provides fast queries for the UI, but it is a materialized view of verified events rather than the global authority.

A community node can provide better availability, indexing, relay capacity, or media retention. It is still a peer with extra resources, not the owner of the protocol.

## Architectural Decisions

### AD-001: Local-first replicas are the primary application model

Decision: every client maintains local state and can operate without a live central API.

Rationale:

- Phones may be offline or on unreliable event networks.
- Local reads are faster and more private.
- A user should be able to draft and create content before reconnecting.
- Synchronization can be retried instead of making every UI action depend on request success.

Consequence: the frontend cannot assume that a successful HTTP response means the whole network accepted a mutation. The UI should distinguish between local acceptance, synchronization, and remote visibility.

### AD-002: Signed events, not mutable replicated rows, are the protocol primitive

Decision: mutations are represented as append-only, signed events. Local tables are derived views.

Example:

```json
{
  "event_id": "sha256:...",
  "type": "post.created",
  "author": "did:key-or-public-key",
  "object_id": "sha256:...",
  "created_at": "2026-09-13T18:20:00Z",
  "payload": {
    "body": "See you at camp!",
    "visibility": "public"
  },
  "parents": [],
  "signature": "..."
}
```

An edit, comment, like, RSVP, membership approval, or deletion is another event referencing the relevant object. Events are deduplicated by `event_id` and validated before entering the local replica.

Rationale:

- Events can arrive out of order.
- Retries are safe.
- Peers can detect duplicates.
- Authorship and integrity are independently verifiable.
- Conflict handling is explicit rather than hidden in database replication behavior.

Consequence: the application needs an event validator, event store, and projector/materializer. Neo4j can remain a derived index on durable nodes, but it is not the wire-level source of truth.

### AD-003: Public-key identities replace central account ownership

Decision: a user identity is based on a locally generated signing keypair. The public key, or a stable identifier derived from it, is the user identifier.

The private key remains on the user's device or encrypted backup. Public profile data is published in signed events. Devices verify signatures before accepting events as authored by that identity.

Rationale:

- No central account table is required.
- Users can prove authorship across peers.
- A profile can move between devices by importing a recovery bundle.
- Pseudonymous and disposable identities are possible.

Consequence: key recovery is a first-class product feature. The initial implementation must support encrypted export/import and should later support a human-readable recovery phrase or trusted-device pairing.

The existing password and JWT system remains a compatibility mechanism during migration. It must not be treated as the eventual decentralized identity system.

### AD-004: Authorization is explicit and object-scoped

Decision: signatures prove authorship, but they do not automatically grant permission to modify every object.

Examples:

- A user may create and edit their own profile.
- A post author may create a valid deletion tombstone for their post.
- A camp lead may approve camp membership if a valid camp-role event grants that authority.
- A group moderator may issue a moderation event scoped to that group.
- An RSVP is authored by the attendee; an event capacity rule may still be enforced by the event organizer or group policy.

Every event type must specify:

- Who may issue it.
- Which object it targets.
- Which previous event or authorization it depends on.
- Whether it is mergeable, revocable, or terminal.
- What a peer does when authorization cannot yet be verified.

Unknown or unauthorized events are retained only in quarantine/diagnostic storage, not materialized into user-visible state.

### AD-005: Merge semantics are chosen per feature

Decision: there is no single universal conflict-resolution rule.

Initial merge rules:

| Feature | Proposed representation | Merge behavior |
|---|---|---|
| Profile fields | Signed versioned updates | Deterministic version ordering; preserve history |
| Posts | Append-only creation events | Immutable content plus signed edits/tombstones |
| Comments | Append-only events | Order by logical timestamp plus event ID tie-breaker |
| Likes | Set of signed like/unlike events | Derive current state deterministically |
| Friend requests | State-machine events | Accept only valid transitions from authorized parties |
| Camp membership | Add/remove or request/approval events | Membership requires applicable camp authority |
| Group membership | Invitation/request/approval events | Group policy determines authorization |
| RSVPs | Signed attendee events | Current RSVP is derived; organizer policy handles capacity |
| Moderation | Scoped signed moderation events | Local/group policy decides visibility |

CRDT techniques may be used where they fit, especially for sets and append-only collections. CRDTs do not replace authorization or moderation rules.

### AD-006: Feeds are computed locally

Decision: there is no required global feed service. Each device builds its feed from verified events available in its local replica.

The local feed pipeline is:

1. Receive events from storage, peers, or an optional community node.
2. Verify event signatures and authorization.
3. Project accepted events into local indexes.
4. Apply the user's local visibility, block, mute, and trust rules.
5. Rank or paginate the resulting feed locally.

Consequence: a newly connected device may have an incomplete feed until it synchronizes relevant peers. This is acceptable and should be represented in the UI rather than concealed.

### AD-007: WebRTC is the first browser transport

Decision: the first two-peer prototype will use WebRTC data channels.

Rationale:

- It is available to modern browsers and PWAs.
- It provides encrypted peer data channels.
- It allows us to validate the event protocol before committing to a larger networking stack.

WebRTC still needs signaling. The signaling service exchanges connection metadata; it does not need to store social events or become an authority. STUN helps discover viable network paths. TURN may relay encrypted traffic when direct connectivity fails.

WebRTC is not expected to provide reliable background participation on mobile devices.

### AD-008: libp2p is the likely long-term native networking layer

Decision: libp2p is the preferred direction for native/mobile peers and durable community nodes, but it is not a prerequisite for the first browser spike.

A later native layer can provide:

- Persistent peer identity
- Peer discovery and rendezvous
- Pub/sub or stream protocols
- Multiple transports
- NAT traversal
- Background synchronization where the operating system permits it

The application protocol must remain transport-independent so that a WebRTC peer and a libp2p peer can exchange the same event envelopes.

### AD-009: Mobile devices are opportunistic peers, not permanent servers

Decision: phones participate when active, charging, connected, or otherwise permitted by the operating system. They are not assumed to accept inbound connections continuously.

Mobile clients can:

- Store a local replica.
- Create and verify events offline.
- Synchronize when opened.
- Share data with nearby peers.
- Cache content temporarily.
- Participate in WebRTC sessions.

Persistent availability comes from optional camp nodes, desktop peers, community relays, or archive nodes. This avoids designing the system around behavior iOS and Android cannot reliably provide.

### AD-010: Content is content-addressed and separately replicated

Decision: large media objects are stored by cryptographic content hash and referenced by events.

A post event may contain:

```text
media hash → encrypted or public blob
```

Text events and media availability are separate concerns. A peer may possess the post metadata but not the referenced image. The UI must show unavailable media clearly and allow retrieval from other providers.

Initial storage options, in order of complexity:

1. Local device cache.
2. Peer-to-peer transfer from a device that has the blob.
3. Optional community pin/archive nodes.
4. IPFS-like content-addressed storage if it proves useful.

Private media must be encrypted for its intended recipients before replication.

### AD-011: Privacy is enforced with encryption and local policy

Decision: transport encryption alone is not sufficient for private content.

Visibility classes:

- `public`: any peer may replicate and display subject to local policy.
- `group`: encrypted or policy-scoped to a camp/group membership set.
- `friends`: encrypted for the intended audience where practical.
- `private`: encrypted for the owner or explicitly selected recipients.

Metadata such as event existence, author identifiers, timing, and replication patterns may still leak. The privacy model must document this instead of promising anonymous operation.

### AD-012: Moderation is federated and scoped

Decision: moderation is performed by users, camps, groups, and optional community policy providers rather than one universal delete authority.

Possible mechanisms:

- Personal block and mute lists.
- Group or camp moderation events.
- Community-maintained blocklists.
- Report events.
- Trust and reputation lists.
- Local content warnings.
- Relay-level spam controls.

A moderation event affects the scope for which its issuer has authority. Clients may still choose stronger local filtering.

### AD-013: Deletion is best-effort tombstoning

Decision: deletion is represented by signed tombstones and local hiding, not a promise that every replicated copy disappears.

Peers should:

- Stop displaying a valid tombstoned object when policy requires it.
- Propagate the tombstone.
- Remove local encrypted media where possible.
- Respect retention and legal policy on durable nodes.

The product must not promise universal erasure after data has been replicated to unknown peers.

### AD-014: Optional infrastructure must be replaceable

Decision: rendezvous, relay, indexing, and archive services are providers, not authorities.

Clients should support multiple configured providers. A provider may be unavailable or untrusted without making locally stored content unusable.

Provider roles:

| Role | Purpose | Can author social data? |
|---|---|---|
| Rendezvous/signaling | Help peers find each other | No |
| STUN/TURN | Assist or relay connectivity | No |
| Community relay | Forward encrypted protocol traffic | No |
| Archive/pinning node | Retain events or media | No, unless separately authorized |
| Index node | Build searchable derived indexes | No |

## Data and Protocol Model

### Event envelope

The protocol should use a versioned canonical encoding. JSON is acceptable for the first spike; a canonical binary encoding can be evaluated later.

Required envelope fields:

```json
{
  "protocol_version": 1,
  "event_id": "sha256(canonical_event_bytes)",
  "type": "post.created",
  "author": "public-key-or-derived-id",
  "object_id": "content-address-or-stable-id",
  "created_at": "2026-09-13T18:20:00Z",
  "parents": [],
  "payload": {},
  "signature": "signature-over-canonical-fields"
}
```

Rules:

- Canonicalize before hashing and signing.
- The event ID must be deterministic.
- Signatures cover all fields that affect meaning.
- Receivers validate size, type, timestamp policy, signature, authorization, and referenced parents.
- Unknown protocol versions are rejected or quarantined rather than guessed.
- Events must be idempotent: receiving the same event twice has no additional effect.

### Synchronization protocol

The first protocol should be request/response synchronization over an established peer channel:

```text
peer A → hello(protocol version, identity, capabilities)
peer B → hello(...)
peer A → want(cursor or event IDs, object scopes)
peer B → events(batch)
peer A → accepted/rejected/quarantined acknowledgements
peer A → want(missing parents or media hashes)
peer B → events/media or provider references
```

The protocol should support:

- Cursor-based event exchange.
- Explicit object or group scopes.
- Bounded batches.
- Resumption after disconnect.
- Duplicate-safe retries.
- Backpressure on mobile devices.
- Capability negotiation.
- A maximum event and media size.

A gossip protocol may be added later. It should not be required before direct synchronization is reliable.

### Local storage

The target local storage model is:

```text
local database
├── identities / encrypted key references
├── raw_events
├── quarantined_events
├── event_parents
├── object_projection tables
├── peer cursors
├── media_manifest
├── local_blocks_and_mutes
└── sync_tasks
```

SQLite is the default target for native and durable nodes because it is embedded, portable, transactional, and well supported. Browser clients may initially use IndexedDB, with a repository interface shared conceptually with the SQLite implementation.

Neo4j can remain useful for a community node as a derived graph projection and search/indexing layer. It should not be required for a phone to read or create local content.

## Mobile and Offline Design

### PWA first

The first client should remain a Svelte PWA so the existing frontend can be reused. The PWA should add:

- IndexedDB local event storage.
- Local identity generation and encrypted key storage.
- A sync queue.
- Service-worker asset caching.
- Offline read and compose flows.
- WebRTC transport support.
- Clear synchronization state in the UI.

The PWA can participate while open, but it should not claim to be an always-on node.

### Native capabilities later

A native wrapper or companion service may eventually be needed for:

- Background sync.
- Better secure key storage.
- Push notifications.
- Local Wi-Fi discovery.
- Bluetooth or nearby-device exchange.
- Large media caching.
- Durable peer operation.

Native work should follow a successful browser protocol spike rather than precede it.

### Playa/offline mode

A useful event-specific feature is local-network operation when internet access is poor:

- Nearby devices discover one another on local Wi-Fi where available.
- Devices exchange signed events opportunistically.
- Camp nodes retain events for later synchronization.
- Event announcements and camp information remain usable offline.
- Internet-connected peers eventually bridge local event data to the wider network.

This mode requires native discovery for the most reliable experience, but the event protocol should support it from the beginning.

## Security Model

Security responsibilities are split deliberately:

| Concern | Mechanism |
|---|---|
| Authorship | Public-key signatures |
| Integrity | Event hash/content address |
| Transport confidentiality | WebRTC/libp2p secure channels |
| Private content confidentiality | End-to-end encryption |
| Authorization | Signed role and relationship events |
| Local account protection | OS keystore or encrypted key bundle |
| Replay resistance | Event IDs, parent/version rules, timestamps |
| Spam resistance | Quotas, invitations, trust, local blocks, relay policy |
| Recovery | Encrypted export, recovery phrase, or trusted-device pairing |

Threats that must be addressed before production:

- Stolen device and extracted keys.
- Malicious peers sending forged events.
- Replay and event amplification attacks.
- Sybil identities and automated spam.
- Malicious or compromised relay nodes.
- Metadata leakage.
- Malformed event/resource exhaustion attacks.
- Conflicting or dishonest role claims.

Cryptographic algorithms and libraries should be selected during implementation and recorded in a protocol specification. Do not invent cryptographic primitives or custom signature formats.

## Migration Plan

### Phase 0: Document and isolate current assumptions

- Keep the existing centralized prototype working.
- Introduce a domain layer separate from FastAPI route handlers.
- Identify every mutation and its current authorization rule.
- Define event types and deterministic identifiers.
- Add tests for projection and merge behavior.

### Phase 1: Local-first single-device mode

- Add a local event store.
- Generate a local identity.
- Create signed profile and post events.
- Project events into local read models.
- Add offline compose and read behavior.
- Keep the existing server API as an optional compatibility backend.

Acceptance criteria:

- A user can create a profile and post with the backend unavailable.
- Restarting the client preserves local state.
- Tampered events are rejected.
- Replaying the same event does not duplicate content.

### Phase 2: Two-browser synchronization

- Implement WebRTC data channels.
- Add a minimal signaling service.
- Exchange hello messages and event batches.
- Verify and materialize received events.
- Add disconnect/resume behavior.

Acceptance criteria:

- Two browser instances can exchange profiles and posts.
- Either peer can go offline and later catch up.
- Events arrive out of order without corrupting projections.
- No social data is stored by the signaling service.

### Phase 3: Social graph events

Add event-backed implementations for:

- Friend requests and friendship state.
- Comments and reactions.
- Events and RSVPs.
- Camp membership and roles.
- Groups and moderation.
- Locally computed feeds.

Each feature must define its authorization and merge tests before being networked.

### Phase 4: Community infrastructure

- Add configurable rendezvous providers.
- Add STUN/TURN configuration.
- Add optional relay nodes.
- Add durable camp/community nodes.
- Add event/media archive and retention policy.
- Make provider failure observable but non-fatal to local use.

### Phase 5: Native mobile participation

- Package the client for mobile.
- Add secure key storage and recovery UX.
- Add background synchronization where permitted.
- Add local Wi-Fi/Bluetooth discovery if justified by field testing.
- Test battery, data, storage, and privacy behavior on real devices.

## Repository Direction

The current repository structure remains useful during migration. The target additions should look conceptually like this:

```text
blaze/
├── backend/
│   ├── app/                         # compatibility API and node services
│   ├── schema/                      # current Neo4j schema and projections
│   └── tests/
├── frontend/
│   └── src/
│       ├── lib/local/               # IndexedDB/local replica adapter
│       ├── lib/identity/            # key generation and recovery
│       ├── lib/protocol/            # event encoding and validation
│       ├── lib/sync/                # WebRTC and sync queue
│       └── lib/projections/         # local feed/read models
├── protocol/
│   ├── events.md                    # event types and authorization rules
│   ├── sync.md                      # peer synchronization protocol
│   └── security.md                  # cryptographic and threat model
├── node/                            # future durable peer implementation
│   ├── event_store/
│   ├── projections/
│   ├── transports/
│   └── providers/
└── README.md
```

The exact module layout may change. The important boundary is that domain events, validation, and synchronization are not embedded directly in HTTP route handlers or Neo4j queries.

## First Technical Spike

The first implementation should be intentionally narrow:

```text
Two browser instances
→ generate local identities
→ create signed profile and post events
→ connect through WebRTC
→ exchange missing events
→ verify signatures
→ project events into local views
→ render the merged feed
→ disconnect and continue offline
→ reconnect and catch up
```

Do not begin with camps, private media, global gossip, or a native mobile app. If this slice works, it validates the most important architectural assumptions: identity, event format, local persistence, transport independence, synchronization, and projection.

## Running the Current Prototype

### Prerequisites

- Python 3.10+
- Node.js 18+
- Docker (optional, for Neo4j or full stack)

### Start Neo4j

Option A: Docker:

```bash
docker run -d \
  --name burner-neo4j \
  -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/burner_social_dev \
  neo4j:5-community
```

Option B: Docker Compose:

```bash
docker compose up -d neo4j
```

### Start the Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\\Scripts\\activate         # Windows
pip install -e ".[dev]"
cp ../.env.example .env
python schema/load.py
uvicorn backend.app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`.
Interactive documentation is available at `/docs` and `/redoc`.

### Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend is available at `http://localhost:5173`.

## Current API Documentation

Once the centralized prototype is running:

| Endpoint | Description |
|---|---|
| `GET /health` | Health check with Neo4j status |
| `POST /api/auth/register` | Register a new user |
| `POST /api/auth/login` | Login with email/username |
| `POST /api/auth/refresh` | Refresh token pair |
| `POST /api/auth/password-reset/request` | Request password reset |
| `POST /api/auth/password-reset/confirm` | Confirm password reset |
| `GET /api/users/me` | Get current user profile |
| `PATCH /api/users/me` | Update current user profile |
| `POST /friends/request` | Send friend request |
| `POST /friends/request/{id}/accept` | Accept friend request |
| `POST /friends/request/{id}/reject` | Reject friend request |
| `GET /friends/{user_id}` | List friends |
| `GET /friends/{user_id}/pending` | List pending requests |
| `DELETE /friends/{user_id}/unfriend/{friend_id}` | Unfriend |
| `POST /users` | Create user |
| `GET /users` | Search users |
| `GET /users/{user_id}` | Get user by ID |
| `GET /users/{user_id}/suggestions` | Get friend suggestions |
| `POST /events` | Create event |
| `GET /events` | List events |
| `GET /events/{event_id}` | Get event details |
| `PATCH /events/{event_id}` | Update event |
| `DELETE /events/{event_id}` | Delete event |
| `POST /events/{event_id}/rsvp` | RSVP to event |
| `GET /events/{event_id}/attendees` | List attendees |
| `POST /camps` | Create camp |
| `GET /camps` | List camps |
| `GET /camps/{camp_id}` | Get camp details |
| `PATCH /camps/{camp_id}` | Update camp |
| `DELETE /camps/{camp_id}` | Delete camp |
| `POST /camps/{camp_id}/join` | Join camp |
| `POST /camps/{camp_id}/leave` | Leave camp |
| `GET /camps/{camp_id}/members` | List camp members |
| `POST /groups` | Create group |
| `GET /groups` | List groups |
| `GET /groups/{group_id}` | Get group details |
| `PATCH /groups/{group_id}` | Update group |
| `DELETE /groups/{group_id}` | Delete group |
| `POST /groups/{group_id}/join` | Join group |
| `POST /groups/{group_id}/leave` | Leave group |
| `GET /groups/{group_id}/members` | List group members |
| `POST /posts` | Create post |
| `GET /posts/{post_id}` | Get post |
| `PATCH /posts/{post_id}` | Update post |
| `DELETE /posts/{post_id}` | Delete post |
| `POST /posts/{post_id}/like` | Like post |
| `DELETE /posts/{post_id}/like` | Unlike post |
| `GET /posts/{post_id}/likes` | Get post likes |
| `POST /posts/{post_id}/comments` | Add comment |
| `GET /posts/{post_id}/comments` | List comments |
| `GET /posts/user/{user_id}` | List user's posts |
| `GET /feed/{user_id}` | Personalized news feed |

These routes are part of the current compatibility application. New peer protocol operations should not automatically be modeled as server CRUD endpoints.

## Testing the Current Prototype

```bash
cd backend
python -m pytest tests/ --tb=short -v
python tests/e2e_smoke.py
python tests/e2e_smoke.py --frontend
```

The existing integration tests cover centralized API behavior, including graceful degradation when Neo4j is unavailable. Future protocol tests should additionally cover signature validation, deterministic event IDs, duplicate delivery, out-of-order delivery, authorization, merge behavior, reconnect/resume, and projection rebuilding.

## Docker Compose

```bash
docker compose up --build
docker compose up --build -d
docker compose logs -f
docker compose down
docker compose down -v
```

The current full stack includes:

- Neo4j on `localhost:7687`
- FastAPI on `localhost:8000`
- Nginx serving Svelte on `localhost:5173`

The target architecture may use these services as one optional community node, not as the only way to use Blaze.

## Neo4j Backup

The current centralized prototype supports graph backups:

```bash
python backend/scripts/backup_graph.py
python backend/scripts/backup_graph.py --format json
python backend/scripts/backup_graph.py --format cypher
python backend/scripts/backup_graph.py --output-dir /path/to/backups
```

Decentralized nodes will additionally need event-log export and encrypted identity backup. A Neo4j backup alone will not be sufficient to recover a user's decentralized identity or portable event history.

## Environment Variables

| Variable | Default | Current purpose |
|---|---|---|
| `NEO4J_URI` | `bolt://localhost:7687` | Current graph database URI |
| `NEO4J_USER` | `neo4j` | Current graph database username |
| `NEO4J_PASSWORD` | `burner_social_dev` | Current graph database password |
| `JWT_SECRET_KEY` | `blaze-dev-secret-change-in-production` | Current compatibility authentication |
| `HOST` | `0.0.0.0` | Current API bind host |
| `PORT` | `8000` | Current API listen port |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Current frontend API base URL |

Future configuration will likely include:

- Local storage provider and quota.
- Identity/key-storage settings.
- Signaling/rendezvous provider URLs.
- STUN/TURN servers.
- Relay and archive providers.
- Sync batch and bandwidth limits.
- Community policy providers.

## CORS Configuration

The current backend allows the Vite development and preview origins:

- `http://localhost:5173`
- `http://localhost:4173`
- `http://127.0.0.1:5173`
- `http://127.0.0.1:4173`

Update `ORIGINS` in `backend/app/main.py` to add production domains. In the target P2P model, CORS remains relevant for browser-hosted nodes, but it is not a substitute for peer authentication or event signature validation.

## License

Blaze is licensed under the [GNU Affero General Public License v3.0 or later](LICENSE).
