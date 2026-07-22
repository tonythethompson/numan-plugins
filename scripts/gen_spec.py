#!/usr/bin/env python3
"""Generate a numan-registry package spec from packaged plugin assets.

Consumes the `PACKAGED\\t<target>\\t<filename>\\t<sha256>\\t<exe>` lines emitted
by package_plugin.py (collected across all matrix jobs) plus the plugin's
manifest.json entry, and writes a spec JSON in the exact shape numan-registry's
scripts/add-package.py expects for a `kind: binary` artifact.

The spec intentionally OMITS sha256: add-package.py re-downloads each asset and
computes the hash itself (never hand-typed). The sha256 in the PACKAGED lines is
only used here to sanity-check the uploaded asset matches what we built.

Provenance is emitted as a top-level `source: {git, rev, cargo_name}` block
(from the manifest entry) so numan-registry `add-package.py` can pass it into
the signed index.

Usage:
  python scripts/gen_spec.py \\
    --name nu_plugin_regex \\
    --packaged packaged.tsv \\
    --release-base https://github.com/<org>/numan-plugins/releases/download/nu_plugin_regex-0.22.0 \\
    --out spec.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_manifest_entry(name: str, manifest_path: Path | None = None) -> dict:
    path = manifest_path or (REPO_ROOT / "manifest.json")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for entry in manifest.get("active", []):
        if entry["name"] == name:
            return entry
    print(f"FAIL: '{name}' not in manifest.json active[]", file=sys.stderr)
    raise SystemExit(1)


def parse_packaged(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("PACKAGED\t"):
            continue
        _, target, filename, sha256, exe = line.split("\t")
        rows.append({"target": target, "filename": filename, "sha256": sha256, "exe": exe})
    if not rows:
        print(f"FAIL: no PACKAGED rows in {path}", file=sys.stderr)
        raise SystemExit(1)
    return rows


def build_spec(entry: dict, packaged_rows: list[dict], release_base: str) -> dict:
    """Build a registry spec dict from a manifest entry and PACKAGED rows."""
    base = release_base.rstrip("/")
    targets = {}
    for r in packaged_rows:
        targets[r["target"]] = {
            "url": f"{base}/{r['filename']}",
            "executable_path": r["exe"],
        }

    return {
        "owner": entry["owner"],
        "name": entry["name"],
        "description": entry["description"]
        + f" CI-built from {entry['repo']}@{entry['tag']} and signed under the official trust root.",
        "repo": f"https://github.com/{entry['repo']}",
        "type": "plugin",
        "tags": entry["tags"],
        "version": entry["version"],
        "nu_version": entry["nu_version"],
        "verified_with": entry["verified_with"],
        "source": {
            "git": f"https://github.com/{entry['repo']}",
            "rev": entry["tag"],
            "cargo_name": entry["plugin_bin"],
        },
        "artifact": {
            "kind": "binary",
            "targets": {k: targets[k] for k in sorted(targets)},
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--packaged", required=True, type=Path)
    ap.add_argument("--release-base", required=True, help="release asset download base URL (no trailing slash)")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    entry = load_manifest_entry(args.name)
    rows = parse_packaged(args.packaged)
    spec = build_spec(entry, rows, args.release_base)

    args.out.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {args.out} with {len(spec['artifact']['targets'])} target(s): "
        f"{', '.join(sorted(spec['artifact']['targets']))}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
