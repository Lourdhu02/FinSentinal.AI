from __future__ import annotations

from getpass import getpass

from database.db_manager import DatabaseManager
from security.auth import AuthManager
from security.rbac import RBACManager


def run_create_user(
    admin_username: str,
    username: str,
    role: str = "user",
    admin_password: str | None = None,
    password: str | None = None,
) -> int:
    admin_password = admin_password or getpass("Admin password: ")
    password = password or getpass("New user password: ")
    db = DatabaseManager()
    auth = AuthManager()
    admin_user = auth.authenticate_user(db, admin_username, admin_password)
    RBACManager().require_permission(admin_user, "create_user")
    existing = db.get_user_by_username(username)
    if existing is not None:
        raise ValueError(f"User '{username}' already exists.")
    user = db.create_user(username=username, password_hash=auth.hash_password(password), role=role)
    token = auth.create_access_token(user)
    print(f"Created user {user.username} with role {user.role}")
    print(token)
    return 0
