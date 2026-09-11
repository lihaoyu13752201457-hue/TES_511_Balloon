#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.validation_summary import build_validation_manifest, write_validation_summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default=str(ROOT / "reports"))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_validation_manifest(ROOT)
    (out_dir / "validation_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_validation_summary(out_dir / "laue511_crosscheck_summary.md", manifest)
    print(json.dumps({"status": manifest["status"], "production_validation_ready": manifest["production_validation_ready"]}, indent=2, sort_keys=True))
    return _status_exit_code(str(manifest["status"]))


def _status_exit_code(status: str) -> int:
    return 0 if status.startswith("crosscheck_pass_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
