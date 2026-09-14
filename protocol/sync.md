# Transport-independent synchronization

Status: Phase 0 boundary specification.

Synchronization exchanges verified events and event identifiers, not database rows or HTTP CRUD semantics. WebRTC, HTTP, relays, removable files, and future transports are interchangeable delivery mechanisms and must not change event meaning or trust.

## Required operations

A transport adapter must be able to negotiate protocol versions, advertise known event IDs/cursors, request missing parents or event ranges, transfer bounded batches, acknowledge accepted/quarantined/duplicate events, and resume from a cursor after interruption. Batches may be reordered or retried.

The receiver validates every event locally before append/projection. A sender cannot make an event authoritative merely by delivering it. The local replica remains usable with incomplete synchronization, and missing data is represented as incomplete rather than fabricated.

## Two-peer first boundary

Phase 0 and the first implementation target reliable synchronization between two peers. No global gossip, mesh convergence, relay authority, or background mobile availability is promised. Signaling may exchange transport metadata, but it is outside the event log.

## Errors and limits

Adapters must bound batch size, event size, request depth, and work per peer. They must distinguish unsupported protocol, malformed event, unauthorized event, missing parent, duplicate, quarantine, and transient transport failure. Retry is safe for event delivery; applying a derived projection must be deterministic and repeatable.
