from __future__ import annotations

import hashlib
import hmac
import string
from secrets import choice, token_urlsafe

import bcrypt

BCRYPT_ROUNDS = 13


def generate_token(byte_length: int = 32) -> str:
    return token_urlsafe(byte_length)


def generate_alphanumeric_code(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(choice(alphabet) for _ in range(length))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_hash_matches(token: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), expected_hash)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def sign_value(value: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def encode_signed_token(token: str, secret: str) -> str:
    return f"{token}.{sign_value(token, secret)}"


def decode_signed_token(cookie_value: str, secret: str) -> str | None:
    token, separator, signature = cookie_value.partition(".")
    if separator != "." or token == "":
        return None
    expected = sign_value(token, secret)
    if not hmac.compare_digest(signature, expected):
        return None
    return token
