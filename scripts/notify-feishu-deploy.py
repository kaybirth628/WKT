#!/usr/bin/env python3
"""云端部署完成后：飞书通知 + 操作记录（含 version/build 从→到）。"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_impl.integrations.wkt_events import (
    collect_deploy_delta,
    load_pre_deploy_snapshot,
    log_system_deploy_audit,
    notify_system_deploy,
    save_last_deploy_snapshot,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Notify Feishu + audit log after WKT cloud deploy")
    parser.add_argument(
        "--app-dir",
        default=str(ROOT),
        help="Application root on server (default: repo root)",
    )
    parser.add_argument("--host-label", default="云端", help="Environment label in message")
    parser.add_argument(
        "--operator",
        default="",
        help="Who triggered deploy (default: env WKT_DEPLOY_OPERATOR or deploy)",
    )
    parser.add_argument("--changelog-limit", type=int, default=50)
    args = parser.parse_args()

    app_dir = Path(args.app_dir)
    operator = (args.operator or os.environ.get("WKT_DEPLOY_OPERATOR") or "deploy").strip() or "deploy"
    previous = load_pre_deploy_snapshot(app_dir)
    since_cl = str((previous or {}).get("top_cl") or "").strip()
    summary = collect_deploy_delta(app_dir, since_cl=since_cl, changelog_limit=args.changelog_limit)

    feishu_ok = notify_system_deploy(
        version=summary["version"],
        build=summary["build"],
        prev_version=str((previous or {}).get("version") or ""),
        prev_build=str((previous or {}).get("build") or ""),
        prev_top_cl=since_cl,
        top_cl=str(summary.get("top_cl") or ""),
        cl_transition=str(summary.get("cl_transition") or ""),
        changes=summary["changes"],
        host_label=args.host_label,
        operator=operator,
        sync=True,
    )
    try:
        log_system_deploy_audit(
            app_dir,
            previous=previous,
            current=summary,
            operator=operator,
            host_label=args.host_label,
        )
        audit_ok = True
    except Exception as exc:
        audit_ok = False
        print(f"WARN: audit log failed: {exc}", file=sys.stderr)

    save_last_deploy_snapshot(app_dir, summary)
    print(
        f"Deploy notify: {since_cl or '—'} -> {summary.get('top_cl') or '—'} "
        f"build {((previous or {}).get('build') or '—')} -> {summary['build']} "
        f"changes={len(summary.get('changes') or [])} "
        f"operator={operator} feishu={'ok' if feishu_ok else 'failed/skipped'} audit={'ok' if audit_ok else 'failed'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
