from __future__ import annotations

from typing import Any

from models.user import User


ROLE_PERMISSIONS = {
    "admin": {"chat", "upload", "create_user", "view_audit"},
    "user": {"chat", "upload"},
}


class RBACManager:
    def has_permission(self, role: str, action: str) -> bool:
        if role == "admin":
            return True
        return action in ROLE_PERMISSIONS.get(role, set())

    def _get_role(self, user: User | dict[str, Any]) -> str:
        if isinstance(user, dict):
            return str(user.get("role", ""))
        return user.role

    def require_permission(self, user: User | dict[str, Any] | None, action: str) -> None:
        if user is None:
            raise PermissionError("Authentication required.")
        role = self._get_role(user)
        if not self.has_permission(role, action):
            raise PermissionError(f"Role '{role}' cannot perform '{action}'.")

    def require_role(self, user: User | dict[str, Any] | None, allowed_roles: set[str]) -> None:
        if user is None:
            raise PermissionError("Authentication required.")
        role = self._get_role(user)
        if role not in allowed_roles:
            raise PermissionError("Insufficient role.")
