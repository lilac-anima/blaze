"""Posts & comments — create posts, like/unlike, comment on posts."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from backend.app.database import get_session
from backend.app.models import (
    CommentCreate,
    CommentResponse,
    LikeResponse,
    MessageResponse,
    PostCreate,
    PostResponse,
    PostUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/posts", tags=["Posts"])


async def _get_post_response(
    session: AsyncSession,
    post_id: str,
    current_user_id: str | None = None,
) -> PostResponse:
    """Build a PostResponse with counts and optional is_liked_by_me flag."""
    result = await session.run(
        """
        MATCH (p:Post {post_id: $post_id})
        OPTIONAL MATCH (author:User)-[:POSTED]->(p)
        OPTIONAL MATCH (:User)-[lk:LIKES]->(p)
        OPTIONAL MATCH ()-[c:COMMENT_ON]->(p)
        WITH p, author, count(DISTINCT lk) AS like_count, count(DISTINCT c) AS comment_count
        RETURN p, author, like_count, comment_count
        """,
        post_id=post_id,
    )
    row = await result.single()
    if not row:
        raise HTTPException(404, f"Post {post_id} not found")

    p = row["p"]
    author = row.get("author")

    is_liked = False
    if current_user_id:
        like_check = await session.run(
            """
            MATCH (u:User {user_id: $uid})-[r:LIKES]->(p:Post {post_id: $pid})
            RETURN r
            """,
            uid=current_user_id,
            pid=post_id,
        )
        is_liked = await like_check.single() is not None

    return PostResponse(
        post_id=p["post_id"],
        author_id=author["user_id"] if author else p.get("author_id", ""),
        author_username=author["username"] if author else None,
        author_display_name=author.get("display_name") if author else None,
        content=p["content"],
        image_url=p.get("image_url") or None,
        created_at=p.get("created_at"),
        like_count=row["like_count"],
        comment_count=row["comment_count"],
        is_liked_by_me=is_liked,
        event_id=p.get("event_id") or None,
    )


# ── Create Post ──────────────────────────────────────────────────────

@router.post("", response_model=PostResponse, status_code=201)
async def create_post(
    post: PostCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new post."""
    import uuid
    post_id = f"post-{uuid.uuid4().hex[:8]}"

    # Verify author exists
    author_check = await session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u", uid=post.author_id
    )
    if not await author_check.single():
        raise HTTPException(404, f"User {post.author_id} not found")

    await session.run(
        """
        MATCH (author:User {user_id: $author_id})
        CREATE (p:Post {
            post_id: $post_id,
            author_id: $author_id,
            content: $content,
            image_url: $image_url,
            event_id: $event_id,
            created_at: datetime()
        })
        CREATE (author)-[:POSTED {at: datetime()}]->(p)
        """,
        author_id=post.author_id,
        post_id=post_id,
        content=post.content,
        image_url=post.image_url or "",
        event_id=post.event_id or "",
    )

    # Link to event if event_id provided
    if post.event_id:
        event_check = await session.run(
            "MATCH (e:Event {event_id: $eid}) RETURN e", eid=post.event_id
        )
        if await event_check.single():
            await session.run(
                """
                MATCH (p:Post {post_id: $pid})
                MATCH (e:Event {event_id: $eid})
                CREATE (p)-[:EVENT_POST]->(e)
                """,
                pid=post_id,
                eid=post.event_id,
            )
        # If event doesn't exist, just don't link (post still created)

    return await _get_post_response(session, post_id)


# ── Get Post ─────────────────────────────────────────────────────────

@router.get("/{post_id}", response_model=PostResponse)
async def get_post(
    post_id: str,
    current_user_id: str | None = Query(None, description="User ID to check like status"),
    session: AsyncSession = Depends(get_session),
):
    """Get a post by ID."""
    return await _get_post_response(session, post_id, current_user_id)


# ── Update Post ─────────────────────────────────────────────────────

@router.patch("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    post: PostUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update a post's content or image_url."""
    check = await session.run(
        "MATCH (p:Post {post_id: $pid}) RETURN p", pid=post_id
    )
    if not await check.single():
        raise HTTPException(404, f"Post {post_id} not found")

    set_clauses = []
    params = {"post_id": post_id}
    for field in ("content", "image_url"):
        val = getattr(post, field, None)
        if val is not None:
            set_clauses.append(f"p.{field} = ${field}")
            params[field] = val

    if set_clauses:
        cypher = f"MATCH (p:Post {{post_id: $post_id}}) SET {', '.join(set_clauses)}"
        await session.run(cypher, **params)

    return await _get_post_response(session, post_id)


# ── Delete Post ──────────────────────────────────────────────────────

@router.delete("/{post_id}", response_model=MessageResponse)
async def delete_post(
    post_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a post and its relationships (likes, comments)."""
    check = await session.run(
        "MATCH (p:Post {post_id: $pid}) RETURN p.content AS preview",
        pid=post_id,
    )
    row = await check.single()
    if not row:
        raise HTTPException(404, f"Post {post_id} not found")

    preview = row["preview"][:50]
    await session.run(
        "MATCH (p:Post {post_id: $pid}) DETACH DELETE p",
        pid=post_id,
    )

    return MessageResponse(message=f"Post deleted: '{preview}...'")


# ── List Posts by User ──────────────────────────────────────────────

@router.get("/user/{user_id}", response_model=list[PostResponse])
async def list_user_posts(
    user_id: str,
    current_user_id: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(50, ge=1, le=200),
):
    """List posts by a specific user."""
    result = await session.run(
        """
        MATCH (author:User {user_id: $user_id})-[:POSTED]->(p:Post)
        OPTIONAL MATCH (:User)-[lk:LIKES]->(p)
        OPTIONAL MATCH ()-[c:COMMENT_ON]->(p)
        WITH p, author, count(DISTINCT lk) AS like_count, count(DISTINCT c) AS comment_count
        RETURN p, author, like_count, comment_count
        ORDER BY p.created_at DESC
        LIMIT $limit
        """,
        user_id=user_id,
        limit=limit,
    )

    posts = []
    async for row in result:
        p = row["p"]
        author = row.get("author")

        is_liked = False
        if current_user_id:
            lk = await session.run(
                "MATCH (u:User {user_id: $uid})-[r:LIKES]->(p:Post {post_id: $pid}) RETURN r",
                uid=current_user_id,
                pid=p["post_id"],
            )
            is_liked = await lk.single() is not None

        posts.append(PostResponse(
            post_id=p["post_id"],
            author_id=author["user_id"] if author else p.get("author_id", ""),
            author_username=author["username"] if author else None,
            author_display_name=author.get("display_name") if author else None,
            content=p["content"],
            image_url=p.get("image_url") or None,
            created_at=p.get("created_at"),
            like_count=row["like_count"],
            comment_count=row["comment_count"],
            is_liked_by_me=is_liked,
            event_id=p.get("event_id") or None,
        ))

    return posts


# ── Like / Unlike Post ──────────────────────────────────────────────

@router.post("/{post_id}/like", response_model=LikeResponse)
async def like_post(
    post_id: str,
    user_id: str = Query(..., description="User ID liking the post"),
    session: AsyncSession = Depends(get_session),
):
    """Like a post."""
    # Check post exists
    post_check = await session.run(
        "MATCH (p:Post {post_id: $pid}) RETURN p", pid=post_id
    )
    if not await post_check.single():
        raise HTTPException(404, f"Post {post_id} not found")

    # Check user exists
    user_check = await session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u", uid=user_id
    )
    if not await user_check.single():
        raise HTTPException(404, f"User {user_id} not found")

    # Check if already liked
    like_check = await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:LIKES]->(p:Post {post_id: $pid})
        RETURN r
        """,
        uid=user_id,
        pid=post_id,
    )
    if await like_check.single():
        raise HTTPException(409, "Post already liked by this user")

    await session.run(
        """
        MATCH (u:User {user_id: $uid})
        MATCH (p:Post {post_id: $pid})
        CREATE (u)-[:LIKES {at: datetime()}]->(p)
        """,
        uid=user_id,
        pid=post_id,
    )

    return LikeResponse(post_id=post_id, user_id=user_id, liked_at=datetime.utcnow())


@router.delete("/{post_id}/like", response_model=MessageResponse)
async def unlike_post(
    post_id: str,
    user_id: str = Query(..., description="User ID unliking the post"),
    session: AsyncSession = Depends(get_session),
):
    """Unlike a post."""
    result = await session.run(
        """
        MATCH (u:User {user_id: $uid})-[r:LIKES]->(p:Post {post_id: $pid})
        DELETE r
        RETURN count(r) AS deleted
        """,
        uid=user_id,
        pid=post_id,
    )
    row = await result.single()
    if not row or row["deleted"] == 0:
        raise HTTPException(404, "Like not found")

    return MessageResponse(message="Like removed")


# ── Who Liked a Post ────────────────────────────────────────────────

@router.get("/{post_id}/likes", response_model=list[dict])
async def get_post_likes(
    post_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get users who liked a post."""
    post_check = await session.run(
        "MATCH (p:Post {post_id: $pid}) RETURN p", pid=post_id
    )
    if not await post_check.single():
        raise HTTPException(404, f"Post {post_id} not found")

    result = await session.run(
        """
        MATCH (u:User)-[r:LIKES]->(p:Post {post_id: $pid})
        RETURN u.user_id AS user_id, u.username AS username, u.display_name AS display_name,
               r.at AS liked_at
        ORDER BY r.at DESC
        """,
        pid=post_id,
    )

    likes = []
    async for row in result:
        likes.append({
            "user_id": row["user_id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "liked_at": str(row.get("liked_at")) if row.get("liked_at") else None,
        })

    return likes


# ── Add Comment ─────────────────────────────────────────────────────

@router.post("/{post_id}/comments", response_model=CommentResponse, status_code=201)
async def add_comment(
    post_id: str,
    comment: CommentCreate,
    session: AsyncSession = Depends(get_session),
):
    """Add a comment to a post."""
    import uuid
    comment_id = f"cmt-{uuid.uuid4().hex[:8]}"

    # Check post exists
    post_check = await session.run(
        "MATCH (p:Post {post_id: $pid}) RETURN p", pid=post_id
    )
    if not await post_check.single():
        raise HTTPException(404, f"Post {post_id} not found")

    # Check user exists
    user_check = await session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u", uid=comment.user_id
    )
    row = await user_check.single()
    if not row:
        raise HTTPException(404, f"User {comment.user_id} not found")

    user = row["u"]

    # Create the Comment node (COMMENTED_ON from User to Post, COMMENT_ON from Comment to Post)
    await session.run(
        """
        MATCH (u:User {user_id: $user_id})
        MATCH (p:Post {post_id: $post_id})
        CREATE (c:Comment {
            comment_id: $comment_id,
            content: $content,
            created_at: datetime()
        })
        CREATE (u)-[:COMMENTED_ON {content: $content, at: datetime()}]->(p)
        CREATE (c)-[:COMMENT_ON]->(p)
        """,
        user_id=comment.user_id,
        post_id=post_id,
        comment_id=comment_id,
        content=comment.content,
    )

    return CommentResponse(
        comment_id=comment_id,
        post_id=post_id,
        user_id=comment.user_id,
        username=user["username"],
        display_name=user.get("display_name"),
        content=comment.content,
        created_at=datetime.utcnow(),
    )


# ── List Comments ────────────────────────────────────────────────────

@router.get("/{post_id}/comments", response_model=list[CommentResponse])
async def list_comments(
    post_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List all comments on a post."""
    post_check = await session.run(
        "MATCH (p:Post {post_id: $pid}) RETURN p", pid=post_id
    )
    if not await post_check.single():
        raise HTTPException(404, f"Post {post_id} not found")

    result = await session.run(
        """
        MATCH (u:User)-[r:COMMENTED_ON]->(p:Post {post_id: $pid})
        OPTIONAL MATCH (c:Comment)-[:COMMENT_ON]->(p)
        WHERE c.content = r.content
        RETURN u, r, c
        ORDER BY r.at ASC
        """,
        pid=post_id,
    )

    comments = []
    async for row in result:
        u = row["u"]
        rel = row["r"]
        c = row.get("c")
        comments.append(CommentResponse(
            comment_id=c["comment_id"] if c else "",
            post_id=post_id,
            user_id=u["user_id"],
            username=u["username"],
            display_name=u.get("display_name"),
            content=rel.get("content", ""),
            created_at=rel.get("at"),
        ))

    return comments
