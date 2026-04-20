from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from config import get_settings
from database.db_manager import DatabaseManager
from models.user import User


class AuthManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        return self.password_context.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        if not password_hash:
            return False
        try:
            return self.password_context.verify(password, password_hash)
        except Exception:
            return False

    def authenticate(
        self,
        username: str,
        password: str,
        db_manager: DatabaseManager | None = None,
    ) -> dict[str, Any] | None:
        db = db_manager or DatabaseManager()
        user = db.get_user(username)
        if user is None:
            return None
        if not bool(user.get("is_active", True)):
            return None
        if not self.verify_password(password, str(user.get("password_hash", ""))):
            return None
        return {
            "id": int(user["id"]),
            "username": str(user["username"]),
            "role": str(user["role"]),
        }

    def create_access_token(self, user: User, expires_minutes: int | None = None) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=expires_minutes or self.settings.token_expiry_minutes
        )
        payload = {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role,
            "exp": expires_at,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        return jwt.decode(token, self.settings.jwt_secret, algorithms=[self.settings.jwt_algorithm])

    def authenticate_user(self, db_manager: Any, username: str, password: str) -> User | None:
        user = self.authenticate(username, password, db_manager=db_manager)
        if user is None:
            return None
        existing = db_manager.get_user_by_username(username)
        if existing is None:
            return None
        return existing
