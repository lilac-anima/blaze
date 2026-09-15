# Camp events

Camp events use the version-1 signed envelope. `object_id` is the stable `camp:` identifier. Payload IDs for members are the member's encoded public key (`member_id`).

Event types:

- `camp.created`: payload includes `name`, optional camp fields, and `created_by` equal to the signing author's public key. Creation also grants that author the `lead` role.
- `camp.updated`: payload contains only changed camp fields. A camp lead may update a live camp.
- `camp.tombstoned`: payload may contain `reason`. A camp lead may tombstone a camp; replicas retain the tombstone and do not physically delete it.
- `camp.membership.added`: payload contains `member_id`. A member may join themself; a lead may add another member.
- `camp.membership.removed`: payload contains `member_id`. A member may leave themself; a lead may remove another member.
- `camp.role.granted`: payload contains `member_id` and `role`. Only a lead may grant `moderator`; lead ownership cannot be granted by an event.
- `camp.role.revoked`: payload contains `member_id` and `role`. Only a lead may revoke a matching role; the member returns to `member`.

Receivers first sort valid events by `(created_at, event_id)`, then apply the authorization rule against the current projection. Unauthorized events are ignored by the projection but remain in the signed event log for audit and possible future policy changes. Duplicate event IDs are handled by the replica store. A tombstoned camp rejects later camp mutations. Membership and role changes are deterministic under reordering because the same total event order is used on every replica.

The centralized `/camps` HTTP routes remain unchanged for compatibility. They are not authoritative for local signed projections and continue to use their existing Neo4j behavior.
