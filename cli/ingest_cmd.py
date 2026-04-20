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
    user = auth.authenticate(username, password, db_manager=db)
    if not user:
        raise PermissionError("Authentication required.")
    RBACManager().require_permission(user, "upload")
    pipeline = FinSentinelPipeline(db_manager=db)
    summary = pipeline.ingest_and_store(Path(path), user_id=int(user["id"]))
    print(
        f"Processed {summary['processed_count']} files, "
        f"{summary['success_count']} success, "
        f"{summary['failed_count']} failed"
    )
    for item in summary["documents"]:
        print(item)
    return 0
