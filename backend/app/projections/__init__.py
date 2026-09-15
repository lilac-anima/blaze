"""Deterministic local projections rebuilt from validated peer events."""

from .feed import FeedProjection, project_feed

__all__ = ["FeedProjection", "project_feed"]
