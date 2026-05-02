from __future__ import annotations

import bcrypt

from app.core.security import (
    BCRYPT_ROUNDS,
    PASSWORD_HASH_SCHEME,
    PASSWORD_SEED_BYTES,
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
    scheme, encoded_seed, bcrypt_hash = password_hash.split("$", 2)

    assert scheme == PASSWORD_HASH_SCHEME
    assert len(encoded_seed) == 22
    assert len(bcrypt_hash) == 60
    assert bcrypt_hash.startswith(f"$2b${BCRYPT_ROUNDS:02d}$")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_password_hash_uses_distinct_random_seed() -> None:
    password_hash = hash_password("same password")
    other_password_hash = hash_password("same password")

    assert password_hash != other_password_hash
    assert len(password_hash.split("$", 2)[1]) == 22
    assert PASSWORD_SEED_BYTES == 16


def test_verify_password_accepts_legacy_bcrypt_hash() -> None:
    legacy_hash = bcrypt.hashpw(
        b"correct horse battery staple",
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("utf-8")

    assert verify_password("correct horse battery staple", legacy_hash)
    assert not verify_password("wrong password", legacy_hash)
