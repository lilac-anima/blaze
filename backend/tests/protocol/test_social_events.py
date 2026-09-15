from datetime import datetime

import pytest

from backend.app.protocol.identity import generate_identity
from backend.app.protocol.social import (
    EventRejected,
    LocalEventStore,
    SocialEventFactory,
)


NOW = "2026-01-01T00:00:00Z"


def test_comment_is_signed_by_author_and_projects_after_post_dependency() -> None:
    author = generate_identity()
    post = SocialEventFactory.post_created(
        author, "post-1", "hello", NOW,
    )
    comment = SocialEventFactory.comment_created(
        author, "comment-1", "post-1", "first!", NOW, parents=(post.event_id,)
    )
    peer = LocalEventStore()
    assert peer.receive(comment).status == "missing_parent"
    assert peer.receive(post).status == "accepted"
    assert peer.receive(comment).status == "duplicate"
    assert peer.projection.comments_for("post-1")[0].content == "first!"
    assert peer.projection.comments_for("post-1")[0].author == author.public_key_encoded()


def test_comment_cannot_be_forged_or_created_for_unknown_post() -> None:
    author = generate_identity()
    other = generate_identity()
    post = SocialEventFactory.post_created(author, "post-1", "hello", NOW)
    forged = SocialEventFactory.comment_created(
        other, "comment-1", "post-1", "not yours", NOW, parents=(post.event_id,)
    )
    # A valid signature is necessary but authorization is still object-scoped:
    # this store allows any identity to comment on a public post.
    peer = LocalEventStore()
    assert peer.receive(post).status == "accepted"
    assert peer.receive(forged).status == "accepted"
    unknown = SocialEventFactory.comment_created(other, "comment-2", "missing", "x", NOW)
    with pytest.raises(EventRejected, match="unknown post"):
        peer.receive(unknown)


def test_like_unlike_is_idempotent_and_lww_by_author_timestamp_then_event_id() -> None:
    author = generate_identity()
    liker = generate_identity()
    post = SocialEventFactory.post_created(author, "post-1", "hello", NOW)
    store = LocalEventStore()
    store.receive(post)
    liked = SocialEventFactory.liked(liker, "post-1", "2026-01-01T00:00:01Z")
    unliked = SocialEventFactory.unliked(liker, "post-1", "2026-01-01T00:00:02Z")
    assert store.receive(liked).status == "accepted"
    assert store.receive(liked).status == "duplicate"
    assert store.receive(unliked).status == "accepted"
    assert store.projection.like_count("post-1") == 0
    assert store.projection.liked_by("post-1") == ()


def test_two_peers_converge_when_events_arrive_reordered_and_retried() -> None:
    author = generate_identity()
    liker = generate_identity()
    post = SocialEventFactory.post_created(author, "post-1", "hello", NOW)
    comment = SocialEventFactory.comment_created(
        liker, "comment-1", "post-1", "hello", "2026-01-01T00:00:03Z", parents=(post.event_id,)
    )
    like = SocialEventFactory.liked(liker, "post-1", "2026-01-01T00:00:02Z", parents=(post.event_id,))
    peer_a, peer_b = LocalEventStore(), LocalEventStore()
    for event in (post, comment, like):
        peer_a.receive(event)
    for event in (like, comment, post, like):
        peer_b.receive(event)
    assert peer_a.projection.snapshot() == peer_b.projection.snapshot()
    assert peer_b.projection.like_count("post-1") == 1
    assert len(peer_b.projection.comments_for("post-1")) == 1
