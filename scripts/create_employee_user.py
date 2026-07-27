#!/usr/bin/env python3
"""Create WKT employee login. Usage:
  python scripts/create_employee_user.py --username zhangsan --name 张三 --password pass1234
  python scripts/create_employee_user.py --username lisi --name 李四 --password pass1234 --admin
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_impl.auth.service import AuthError, AuthService
from test_impl.auth.store import AuthStore, default_db_path


def main() -> int:
    p = argparse.ArgumentParser(description="Create WKT user account")
    p.add_argument("--username", required=True)
    p.add_argument("--name", required=True, help="display name")
    p.add_argument("--password", required=True)
    p.add_argument("--admin", action="store_true")
    p.add_argument("--db", default=str(default_db_path()))
    args = p.parse_args()

    store = AuthStore(Path(args.db))
    auth = AuthService(store=store)
    role = "admin" if args.admin else "user"
    try:
        user = auth.create_user(
            username=args.username,
            display_name=args.name,
            password=args.password,
            role=role,
        )
    except AuthError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Created: {user['username']} ({user['display_name']}) role={user['role']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
