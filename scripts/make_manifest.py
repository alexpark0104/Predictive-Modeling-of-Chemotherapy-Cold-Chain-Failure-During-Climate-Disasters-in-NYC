"""Write a checksum manifest for a data directory: python scripts/make_manifest.py raw_data

Creates <dir>/MANIFEST.csv (path, size_bytes, sha256). Commit the manifest (small) but not the data.
"""
import csv
import hashlib
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(root: str) -> None:
    root_p = Path(root)
    out = root_p / "MANIFEST.csv"
    rows = []
    for p in sorted(root_p.rglob("*")):
        if p.is_file() and p.name != "MANIFEST.csv":
            rows.append((p.relative_to(root_p).as_posix(), p.stat().st_size, sha256(p)))
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "size_bytes", "sha256"])
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} files)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "raw_data")
