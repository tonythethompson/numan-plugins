#!/usr/bin/env python3
"""Package a built plugin binary into a Numan-compatible release archive.

Produces `.tar.gz` (Unix targets) or `.zip` (Windows targets) containing the
plugin executable at the archive root. The executable_path recorded in the
numan-registry spec is just the binary filename, matching the existing
upstream-asset plugin specs (e.g. specs/fdncred-nu_plugin_file-0.25.2.json).

Archive bytes are normalized (fixed mtime/mode) so a rebuild of the same
target from the same source produces an identical archive, and thus a stable
sha256 for hash-pinned registry entries.

Usage:
  python scripts/package_plugin.py \\
    --binary target/x86_64-unknown-linux-gnu/release/nu_plugin_regex \\
    --name nu_plugin_regex --version 0.22.0 \\
    --target x86_64-unknown-linux-gnu \\
    --outdir dist
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import sys
import tarfile
import zipfile
from pathlib import Path

FIXED_MTIME = 315532800  # 1980-01-01 UTC; matches zip epoch used for mirrors
UNIX_MODE = 0o755  # executable
ZIP_CREATE_SYSTEM = 3  # Unix, for stable zip central directory


def is_windows_target(target: str) -> bool:
    return "windows" in target


def executable_name(name: str, target: str) -> str:
    return f"{name}.exe" if is_windows_target(target) else name


def build_tar_gz(binary: Path, arcname: str, out: Path) -> None:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as tar:
        info = tarfile.TarInfo(name=arcname)
        data = binary.read_bytes()
        info.size = len(data)
        info.mtime = FIXED_MTIME
        info.mode = UNIX_MODE
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        tar.addfile(info, io.BytesIO(data))
    # gzip with mtime=0 so the wrapper is byte-stable too
    with out.open("wb") as fh:
        gz = gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0)
        gz.write(raw.getvalue())
        gz.close()


def build_zip(binary: Path, arcname: str, out: Path) -> None:
    data = binary.read_bytes()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zi = zipfile.ZipInfo(filename=arcname, date_time=(1980, 1, 1, 0, 0, 0))
        zi.create_system = ZIP_CREATE_SYSTEM
        zi.external_attr = (UNIX_MODE & 0xFFFF) << 16
        zf.writestr(zi, data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", required=True, type=Path, help="path to the built plugin executable")
    ap.add_argument("--name", required=True, help="plugin name, e.g. nu_plugin_regex")
    ap.add_argument("--version", required=True)
    ap.add_argument("--target", required=True, help="rust target triple")
    ap.add_argument("--outdir", required=True, type=Path)
    args = ap.parse_args()

    if not args.binary.is_file():
        print(f"FAIL: binary not found: {args.binary}", file=sys.stderr)
        return 1

    args.outdir.mkdir(parents=True, exist_ok=True)
    arcname = executable_name(args.name, args.target)
    win = is_windows_target(args.target)
    ext = "zip" if win else "tar.gz"
    out = args.outdir / f"{args.name}-{args.version}-{args.target}.{ext}"

    if win:
        build_zip(args.binary, arcname, out)
    else:
        build_tar_gz(args.binary, arcname, out)

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    # Emit machine-readable line for the workflow to collect: target|url-filename|sha256|executable_path
    print(f"PACKAGED\t{args.target}\t{out.name}\t{digest}\t{arcname}")
    print(f"  wrote {out} ({out.stat().st_size} bytes) sha256={digest}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
