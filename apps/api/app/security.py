from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from fastapi import HTTPException, status

from .settings import Settings

hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return hasher.verify(password_hash, password)
    except Exception:
        return False


def create_token(user_id: str, settings: Settings) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": user_id, "exp": expires}, settings.secret_key, algorithm="HS256")


def decode_token(token: str, settings: Settings) -> str:
    try:
        subject = jwt.decode(token, settings.secret_key, algorithms=["HS256"]).get("sub")
        if not subject:
            raise ValueError("Missing subject")
        return subject
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ungültiges Zugriffstoken") from exc
