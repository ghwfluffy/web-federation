from __future__ import annotations

from app.core.security import (
    BCRYPT_ROUNDS,
    generate_token,
    hash_password,
    hash_token,
    token_hash_matches,
    verify_password,
)


def test_token_hashing_is_stable_and_one_way() -> None:
    token = "example-token"
    token_hash = hash_token(token)

    assert token_hash == hash_token(token)
    assert token_hash != token
    assert token_hash_matches(token, token_hash)
    assert not token_hash_matches("other-token", token_hash)


def test_generate_token_returns_distinct_values() -> None:
    assert generate_token() != generate_token()


def test_password_hash_uses_configured_bcrypt_rounds() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash.startswith(f"$2b${BCRYPT_ROUNDS:02d}$")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)
