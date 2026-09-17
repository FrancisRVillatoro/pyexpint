#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib
from pathlib import Path

EXCLUDE_PARTS = {".git", "__pycache__", ".pytest_cache", "pyexpint.egg-info"}
EXCLUDE_SUFFIX = {".pyc"}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("output")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    rows = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in EXCLUDE_PARTS for part in rel.parts):
            continue
        if p.suffix in EXCLUDE_SUFFIX:
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        rows.append(f"{h}  {rel.as_posix()}")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(digest)

if __name__ == "__main__":
    main()
