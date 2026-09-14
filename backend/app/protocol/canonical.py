"""Canonical JSON encoding for protocol signatures and IDs."""

from __future__ import annotations

import json
from typing import Any


def canonical_json(value: Any) -> bytes:
    """Encode JSON deterministically as compact UTF-8 with sorted object keys."""
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
