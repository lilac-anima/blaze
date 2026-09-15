from backend.app.protocol.groups import (
    GroupEventStore,
    GroupProjection,
    create_group,
    join_group,
    leave_group,
    tombstone_group,
    update_group,
    change_role,
)
from backend.app.protocol.identity import generate_identity


def test_signed_group_lifecycle_projects_and_replicates() -> None:
    owner = generate_identity()
    member = generate_identity()
    create = create_group(owner, "group-1", "Camp", "A group", True, "owner", "2026-01-01T00:00:00Z")
    join = join_group(member, "group-1", "member", "2026-01-01T00:00:01Z", parents=(create.event_id,))
    update = update_group(owner, "group-1", {"name": "Updated"}, "owner", "2026-01-01T00:00:02Z", parents=(join.event_id,))

    first = GroupEventStore()
    assert first.ingest(create)
    assert first.ingest(join)
    assert first.ingest(update)
    assert first.projection.group("group-1").name == "Updated"
    assert first.projection.members("group-1")[0].user_id == "member"

    second = GroupEventStore()
    assert second.sync(first.export()) == 3
    assert second.projection.group("group-1").name == "Updated"
    assert second.projection.members("group-1")[0].user_id == "member"


def test_group_authorization_and_tombstone() -> None:
    owner = generate_identity()
    stranger = generate_identity()
    create = create_group(owner, "group-2", "Camp", None, True, "owner", "2026-01-01T00:00:00Z")
    projection = GroupProjection()
    assert projection.apply(create)

    unauthorized = update_group(stranger, "group-2", {"name": "bad"}, "stranger", "2026-01-01T00:00:01Z", parents=(create.event_id,))
    assert not projection.apply(unauthorized)
    assert projection.group("group-2").name == "Camp"

    deleted = tombstone_group(owner, "group-2", "owner", "2026-01-01T00:00:02Z", parents=(create.event_id,))
    assert projection.apply(deleted)
    assert projection.group("group-2") is None
    assert projection.tombstones["group-2"] == deleted.event_id


def test_leave_is_last_writer_wins_and_rejects_bad_signature() -> None:
    owner = generate_identity()
    member = generate_identity()
    create = create_group(owner, "group-3", "Camp", None, True, "owner", "2026-01-01T00:00:00Z")
    join = join_group(member, "group-3", "member", "2026-01-01T00:00:01Z", parents=(create.event_id,))
    leave = leave_group(member, "group-3", "member", "2026-01-01T00:00:02Z", parents=(join.event_id,))
    projection = GroupProjection()
    assert projection.apply(create)
    assert projection.apply(join)
    assert projection.apply(leave)
    assert [member.user_id for member in projection.members("group-3")] == ["owner"]

    forged = leave.to_dict()
    forged["payload"]["user_id"] = "other"
    assert not projection.apply(forged)


def test_owner_can_delegate_moderation_but_moderator_cannot_change_roles() -> None:
    owner = generate_identity()
    moderator = generate_identity()
    member = generate_identity()
    create = create_group(owner, "group-4", "Camp", None, True, "owner", "2026-01-01T00:00:00Z")
    join_mod = join_group(moderator, "group-4", "moderator", "2026-01-01T00:00:01Z", parents=(create.event_id,))
    join_member = join_group(member, "group-4", "member", "2026-01-01T00:00:02Z", parents=(join_mod.event_id,))
    promote = change_role(owner, "group-4", "owner", "moderator", moderator.public_key_encoded(), "moderator", "2026-01-01T00:00:03Z", parents=(join_member.event_id,))
    bad_promote = change_role(moderator, "group-4", "moderator", "member", member.public_key_encoded(), "admin", "2026-01-01T00:00:04Z", parents=(promote.event_id,))
    projection = GroupProjection()
    for event in (create, join_mod, join_member, promote):
        assert projection.apply(event)
    assert not projection.apply(bad_promote)
    assert projection.group("group-4").members["moderator"].role == "moderator"
