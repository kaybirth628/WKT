#!/usr/bin/env python3
"""部署合并前捕获云端当前 version/build。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_impl.integrations.wkt_events import capture_pre_deploy_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-dir", default=str(ROOT), help="Application root on server")
    args = parser.parse_args()
    app_dir = Path(args.app_dir)
    summary = capture_pre_deploy_snapshot(app_dir)
    print(
        f"Captured pre-deploy snapshot: version={summary.get('version') or '—'} "
        f"build={summary.get('build') or '—'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
