#!/usr/bin/env python3
"""云端部署完成后推送飞书：版本号、build、CHANGELOG 摘要。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_impl.integrations.wkt_events import collect_deploy_summary, notify_system_deploy


def main() -> int:
    parser = argparse.ArgumentParser(description="Notify Feishu after WKT cloud deploy")
    parser.add_argument(
        "--app-dir",
        default=str(ROOT),
        help="Application root on server (default: repo root)",
    )
    parser.add_argument("--host-label", default="云端", help="Environment label in message")
    parser.add_argument("--changelog-limit", type=int, default=8)
    args = parser.parse_args()

    app_dir = Path(args.app_dir)
    summary = collect_deploy_summary(app_dir, changelog_limit=args.changelog_limit)
    notify_system_deploy(
        version=summary["version"],
        build=summary["build"],
        changes=summary["changes"],
        host_label=args.host_label,
    )
    print(
        f"Feishu deploy notify queued: version={summary['version'] or '—'} build={summary['build']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
