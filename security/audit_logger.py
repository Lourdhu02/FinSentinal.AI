from __future__ import annotations

import hashlib

from database.db_manager import DatabaseManager
from security.encryption import AESCipher


class AuditLogger:
    def __init__(self, db_manager: DatabaseManager, cipher: AESCipher | None = None) -> None:
        self.db = db_manager
        self.cipher = cipher or AESCipher()

    def log_interaction(self, user_id: int | None, action: str, query: str, response: str) -> int:
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        response_hash = hashlib.sha256(response.encode("utf-8")).hexdigest()
        encrypted_query = self.cipher.encrypt(query)
        encrypted_response = self.cipher.encrypt(response)
        return self.db.create_audit_log(
            user_id=user_id,
            action=action,
            query_text=encrypted_query,
            response_text=encrypted_response,
            query_hash=query_hash,
            response_hash=response_hash,
        )

    def list_logs(self, limit: int = 50, decrypt: bool = False) -> list[dict]:
        rows = self.db.list_audit_logs(limit=limit)
        if not decrypt:
            return rows
        logs: list[dict] = []
        for row in rows:
            item = dict(row)
            item["query_text"] = self.cipher.decrypt(item["query_text"])
            item["response_text"] = self.cipher.decrypt(item["response_text"])
            logs.append(item)
        return logs
