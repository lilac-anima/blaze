# Blaze protocol

These documents are the authoritative boundary for the peer protocol during migration:

- [events.md](events.md): versioned event envelope, validation boundary, and event semantics.
- [sync.md](sync.md): transport-independent synchronization contract.
- [security.md](security.md): security assumptions and explicitly deferred cryptographic decisions.

The existing FastAPI/Neo4j API remains a compatibility application. It is not the definition of the peer wire protocol. Protocol changes require a versioned decision recorded in `docs/p2p-migration/decisions.md`.

Phase 0 intentionally specifies boundaries, not a cryptographic implementation. No algorithm, key format, signature encoding, or wire transport is normative until a later phase selects vetted primitives and adds test vectors.
