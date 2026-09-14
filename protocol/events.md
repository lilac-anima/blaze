# Versioned signed events

Status: Phase 1 normative specification, version 1.

## Envelope and canonical representation

A v1 event is a JSON object with exactly these fields: `protocol_version`, `event_id`, `event_type`, `author`, `object_id`, `created_at`, `payload`, `parents`, and `signature`. Object keys are encoded in lexicographic order; arrays retain their declared order; JSON uses compact separators (`,` and `:`), UTF-8, and escaped non-ASCII characters (`ensure_ascii` equivalent). Numbers must be finite JSON numbers. No extra fields are accepted.

`protocol_version` is integer `1`. `event_type`, `object_id`, and parent IDs are 1–256 ASCII characters matching `[A-Za-z0-9._:-]+`. `author` is an URL-safe unpadded base64 Ed25519 public key (32 decoded bytes). `created_at` is an RFC 3339 timestamp with an explicit UTC offset; vectors use `Z`. `parents` is an array of IDs and may be empty. Payload is a JSON object.

The complete canonical encoding is UTF-8 bytes. Payload is limited to 100,000 canonical bytes and the complete event to 128,000 bytes. Implementations must reject malformed JSON, invalid UTF-8, non-finite numbers, missing/extra fields, invalid timestamps, invalid key/signature encodings, and size violations.

## IDs and signatures

The unsigned representation is the envelope without `event_id` and `signature`, retaining all other fields. `event_id` is the lowercase hexadecimal SHA-256 digest of its canonical UTF-8 encoding. The signature covers the canonical UTF-8 encoding of an object containing `event_id` plus the unsigned representation. Signatures are Ed25519, encoded as URL-safe unpadded base64 (64 decoded bytes).

## Receiver behavior

Receivers validate structure, version, size, event ID, and signature before projection. Unsupported versions are rejected and quarantined; they are not silently downgraded. A duplicate `event_id` is idempotent: it is acknowledged as already present and never applied twice. A changed event with an existing ID is invalid. Events may arrive out of order; missing parents remain synchronization dependencies.

Reference vectors, including valid post/profile events and rejection cases, are in `protocol/test-vectors/events.json`. Python reference primitives are in `backend/app/protocol/`.
