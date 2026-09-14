import pytest

from backend.app.protocol.canonical import canonical_json


def test_canonical_json_sorts_keys_and_uses_compact_utf8() -> None:
    assert canonical_json({"z": 1, "a": "café"}) == b'{"a":"caf\u00e9","z":1}'


def test_canonical_json_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError):
        canonical_json({"value": float("nan")})
