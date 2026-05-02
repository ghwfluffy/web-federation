from __future__ import annotations

from app.core.security import generate_token, hash_token, token_hash_matches


def test_token_hashing_is_stable_and_one_way() -> None:
    token = "example-token"
    token_hash = hash_token(token)

    assert token_hash == hash_token(token)
    assert token_hash != token
    assert token_hash_matches(token, token_hash)
    assert not token_hash_matches("other-token", token_hash)


def test_generate_token_returns_distinct_values() -> None:
    assert generate_token() != generate_token()
