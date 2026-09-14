# P2P migration decisions

## D-0001: Protocol documents are authoritative

The files under `protocol/` define the peer event and synchronization boundary. Existing FastAPI routes and Neo4j schemas remain compatibility implementation details. Changes to the protocol require a versioned decision and corresponding tests/vectors.

## D-0002: Events, not rows, cross the peer boundary

Peer mutations are append-only, versioned, signed domain events. Projections may be rebuilt and must not become the wire-level source of truth.

## D-0003: Synchronization is transport-independent

The protocol defines negotiation, discovery, transfer, validation, acknowledgement, and resume semantics independently of WebRTC or any other transport. The first milestone is two-peer sync.

## D-0004: v1 cryptography uses Ed25519

Version 1 uses Ed25519 through the existing Python `cryptography` dependency, with URL-safe base64 key/signature encoding and SHA-256 event IDs over canonical JSON. Canonical JSON uses sorted keys, compact separators, escaped non-ASCII, and UTF-8 bytes. This is a vetted standard primitive rather than a custom algorithm. The published vectors are the interoperability contract.

## D-0005: Recovery is separate from authentication

Private key material is never in event payloads. Device loss may lose signing capability until a separately designed encrypted export/recovery flow exists; password reset does not recover an identity key. Browser primitives and frontend interoperability are explicitly deferred to the next phase.

## D-0006: Compatibility is preserved

Phase 1 does not delete, rename, or alter current API behavior. JWT/password authentication and Neo4j remain current compatibility assumptions while the peer boundary is developed.
