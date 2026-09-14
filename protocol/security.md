# Protocol security boundary

Status: Phase 1 decision. v1 uses Ed25519 from Python `cryptography` and the browser Web Crypto-compatible algorithm family; no custom cryptography is introduced. Canonical encoding and signature coverage are normative in `protocol/events.md`.

Private keys remain in protected identity storage and are never serialized in events or ordinary profile payloads. Public keys are the event author references. The Python implementation supports raw 32-byte private/public key import/export and signing; encrypted recovery export and browser interoperability are follow-on work. Losing a device can therefore make an identity's private key unavailable: password reset cannot recover it, and identity recovery is distinct from account authentication. Future encrypted export must be tested before being treated as a recovery guarantee.

Signature verification proves authorship and integrity, not authorization. Receivers still apply object-scoped authorization, visibility policy, timestamp/size limits, and parent rules. Invalid, unsupported-version, or unauthorized events are quarantined. Relays and transport encryption cannot rewrite a signed event.
