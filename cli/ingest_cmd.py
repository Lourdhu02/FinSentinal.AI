from __future__ import annotations

from getpass import getpass
from pathlib import Path

from core.pipeline import FinSentinelPipeline
from database.db_manager import DatabaseManager
from security.auth import AuthManager
from security.rbac import RBACManager


def run_upload(path: str, username: str, password: str | None = None) -> int:
    password = password or getpass("Password: ")
    db = DatabaseManager()
    auth = AuthManager()
    user = auth.authenticate_user(db, username, password)
    if not user:
        raise PermissionError("Authentication failed.")
    RBACManager().require_permission(user, "upload")
    pipeline = FinSentinelPipeline(db_manager=db)
    session_id = f”user_{user.id}_default”
    summary = pipeline.ingest_and_store(Path(path), session_id=session_id, user_id=user.id)
    print(
        f”Processed {summary['processed_count']} files - “
        f”{summary['success_count']} stored, “
        f”{summary['failed_count']} failed”
    )
    for item in summary["documents"]:
        status = item.get("status", "?")
        path_str = item.get("path", "?")
        print(f"  [{status}] {path_str}")
    return 0
