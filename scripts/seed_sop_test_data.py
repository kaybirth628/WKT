#!/usr/bin/env python3
"""一键写入 SOP 各模块测试数据（保留 JSON 客商档案）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from test_impl.demo.sop_seed import seed_sop_test_data  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="写入 SOP 测试数据（带「测」标注）")
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=15,
        help="每模块约 N 条（10~20，默认 15）",
    )
    args = parser.parse_args()
    summary = seed_sop_test_data(count=args.count)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("\n完成。客商 JSON 档案未改动。请重启网页或刷新后查看。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
