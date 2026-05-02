from __future__ import annotations

import base64
import hashlib
import hmac
import string
from secrets import choice, token_bytes, token_urlsafe

import bcrypt

BCRYPT_ROUNDS = 13
PASSWORD_HASH_SCHEME = "bcrypt-sha256-v1"
PASSWORD_SEED_BYTES = 16


def generate_token(byte_length: int = 32) -> str:
    return token_urlsafe(byte_length)


def generate_alphanumeric_code(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(choice(alphabet) for _ in range(length))


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_hash_matches(token: str, expected_hash: str) -> bool:
    return hmac.compare_digest(hash_token(token), expected_hash)


def password_digest(password: str, seed: bytes) -> bytes:
    return hashlib.sha256(seed + password.encode("utf-8")).digest()


def encode_password_seed(seed: bytes) -> str:
    return base64.urlsafe_b64encode(seed).rstrip(b"=").decode("ascii")


def decode_password_seed(value: str) -> bytes:
    padded_value = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded_value.encode("ascii"))


def hash_password(password: str) -> str:
    seed = token_bytes(PASSWORD_SEED_BYTES)
    bcrypt_hash = bcrypt.hashpw(
        password_digest(password, seed),
        bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
    ).decode("utf-8")
    return f"{PASSWORD_HASH_SCHEME}${encode_password_seed(seed)}${bcrypt_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        if password_hash.startswith(f"{PASSWORD_HASH_SCHEME}$"):
            _scheme, encoded_seed, bcrypt_hash = password_hash.split("$", 2)
            seed = decode_password_seed(encoded_seed)
            return bcrypt.checkpw(password_digest(password, seed), bcrypt_hash.encode("utf-8"))
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
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
