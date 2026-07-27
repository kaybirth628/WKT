"""Extract WKT data tarball on Windows (UTF-8 paths; skip unreadable members)."""
from __future__ import annotations

import sys
import tarfile
from pathlib import Path


def extract_archive(archive: Path, dest_root: Path) -> list[tuple[str, str]]:
    skipped: list[tuple[str, str]] = []
    dest_root = dest_root.resolve()

    with tarfile.open(archive, mode="r:gz", encoding="utf-8") as tf:
        for member in tf.getmembers():
            name = member.name.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts:
                skipped.append((name, "unsafe path"))
                continue
            target = dest_root / name
            try:
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                src = tf.extractfile(member)
                if src is None:
                    skipped.append((name, "not a file"))
                    continue
                with src, open(target, "wb") as dst:
                    dst.write(src.read())
            except OSError as exc:
                skipped.append((name, str(exc)))
    return skipped


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python extract-data-tar.py <archive.tar.gz> <dest_root>", file=sys.stderr)
        return 2
    archive = Path(sys.argv[1])
    dest_root = Path(sys.argv[2])
    if not archive.is_file():
        print(f"Archive not found: {archive}", file=sys.stderr)
        return 1
    skipped = extract_archive(archive, dest_root)
    if skipped:
        print(f"Extracted with {len(skipped)} skipped member(s):")
        for name, reason in skipped[:20]:
            print(f"  skip: {name} ({reason})")
        if len(skipped) > 20:
            print(f"  ... and {len(skipped) - 20} more")
    else:
        print("Extracted all members.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
