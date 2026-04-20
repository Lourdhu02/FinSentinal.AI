from __future__ import annotations

from getpass import getpass

from core.pipeline import FinSentinelPipeline
from database.db_manager import DatabaseManager
from security.auth import AuthManager
from security.rbac import RBACManager


def run_chat(username: str, password: str | None = None) -> int:
    password = password or getpass("Password: ")
    db = DatabaseManager()
    auth = AuthManager()
    user = auth.authenticate_user(db, username, password)
    RBACManager().require_permission(user, "chat")
    pipeline = FinSentinelPipeline(db_manager=db)
    print(f"Authenticated as {user.username} ({user.role})")
    print("Type 'exit' or 'quit' to end the session.")
    while True:
        query = input("chat> ").strip()
        if not query:
            continue
        if query.lower() in {"exit", "quit"}:
            break
        result = pipeline.query(query, user_id=user.id)
        print(result["response"])
    return 0
