from __future__ import annotations

import hashlib
import hmac
from secrets import token_urlsafe


def generate_token(byte_length: int = 32) -> str:
    return token_urlsafe(byte_length)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_hash_matches(token: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), expected_hash)
