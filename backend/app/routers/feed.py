"""News feed — personalized feed of posts from friends & camps, paginated."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any as AsyncSession

from backend.app.database import get_session
from backend.app.models import FeedItem, FeedResponse, PostResponse, UserSearchResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feed", tags=["Feed"])


@router.get("/{user_id}", response_model=FeedResponse)
async def get_feed(
    user_id: str,
    cursor: str | None = Query(None, description="Pagination cursor (post_id or timestamp)"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    Personalized news feed: posts from friends and camp/group mates.
    Paginated with cursor-based pagination.
    """
    # Verify user exists
    user_check = await session.run(
        "MATCH (u:User {user_id: $uid}) RETURN u", uid=user_id
    )
    if not await user_check.single():
        raise HTTPException(404, f"User {user_id} not found")

    cursor_clause = "AND p.created_at < $cursor" if cursor else ""
    cursor_clause2 = "AND p2.created_at < $cursor" if cursor else ""

    query = f"""
        // Start with the user
        MATCH (me:User {{user_id: $user_id}})

        // Posts from friends
        OPTIONAL MATCH (me)-[:FRIENDS_WITH]-(friend:User)-[:POSTED]->(p:Post)
        {cursor_clause}

        // Posts from camp/group mates (excluding friends and self)
        OPTIONAL MATCH (me)-[:MEMBER_OF]->(:Camp)<-[:MEMBER_OF]-(mate:User)-[:POSTED]->(p2:Post)
        WHERE mate.user_id <> $user_id
              AND NOT EXISTS {{ (me)-[:FRIENDS_WITH]-(mate) }}
              {cursor_clause2}

        // Combine into distinct posts with their authors
        WITH
            COLLECT(DISTINCT {{post: p, author: friend}}) +
            COLLECT(DISTINCT {{post: p2, author: mate}}) AS all_items
        UNWIND all_items AS item
        WITH DISTINCT item.post AS post, item.author AS author
        WHERE post IS NOT NULL

        // Get like/comment counts
        OPTIONAL MATCH (post)<-[lk:LIKES]-(:User)
        OPTIONAL MATCH (comment:Comment)-[:COMMENTED_ON]->(post)
        OPTIONAL MATCH (me)-[my_like:LIKES]->(post)

        WITH post, author,
             count(DISTINCT lk) AS like_count,
             count(DISTINCT comment) AS comment_count,
             my_like IS NOT NULL AS is_liked_by_me
        ORDER BY post.created_at DESC
        LIMIT $limit
        RETURN post, author, like_count, comment_count, is_liked_by_me
    """

    result = await session.run(
        query,
        user_id=user_id,
        cursor=cursor if cursor else "",
        limit=limit + 1,  # Fetch one extra to determine if there's a next page
    )

    items = []
    has_more = False
    last_created_at = None
    count = 0
    async for row in result:
        count += 1
        if count > limit:
            has_more = True
            break

        p = row["post"]
        author = row.get("author")

        post_resp = PostResponse(
            post_id=p["post_id"],
            author_id=author["user_id"] if author else p.get("author_id", ""),
            author_username=author["username"] if author else None,
            author_display_name=author.get("display_name") if author else None,
            content=p["content"],
            image_url=p.get("image_url") or None,
            created_at=p.get("created_at"),
            like_count=row["like_count"],
            comment_count=row["comment_count"],
            is_liked_by_me=row.get("is_liked_by_me", False),
        )

        author_info = None
        if author:
            author_info = UserSearchResult(
                user_id=author["user_id"],
                username=author["username"],
                display_name=author.get("display_name"),
                is_friend=True,
            )

        items.append(FeedItem(post=post_resp, author=author_info))
        last_created_at = str(p.get("created_at")) if p.get("created_at") else None

    return FeedResponse(
        items=items,
        next_cursor=last_created_at if has_more else None,
        total=len(items),
    )
