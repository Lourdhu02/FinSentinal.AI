from __future__ import annotations

import argparse

from cli.admin import run_create_user
from cli.chat import run_chat
from cli.ingest_cmd import run_upload
from database.db_manager import DatabaseManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="finsentinel", description="FinSentinelAI CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session")
    chat_parser.add_argument("--username", required=True)
    chat_parser.add_argument("--password")

    upload_parser = subparsers.add_parser("upload", help="Ingest a file or folder")
    upload_parser.add_argument("path")
    upload_parser.add_argument("--username", required=True)
    upload_parser.add_argument("--password")

    create_user_parser = subparsers.add_parser("create-user", help="Create a new user")
    create_user_parser.add_argument("--admin-username", required=True)
    create_user_parser.add_argument("--admin-password")
    create_user_parser.add_argument("--username", required=True)
    create_user_parser.add_argument("--password")
    create_user_parser.add_argument("--role", choices=["admin", "user"], default="user")
    return parser


def main() -> int:
    DatabaseManager()
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "chat":
        return run_chat(username=args.username, password=args.password)
    if args.command == "upload":
        return run_upload(path=args.path, username=args.username, password=args.password)
    if args.command == "create-user":
        return run_create_user(
            admin_username=args.admin_username,
            admin_password=args.admin_password,
            username=args.username,
            password=args.password,
            role=args.role,
        )
    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
