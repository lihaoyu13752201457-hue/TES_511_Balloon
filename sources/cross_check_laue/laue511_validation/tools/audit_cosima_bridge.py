#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.cosima_bridge import convert_phase_space_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--history", required=True)
    parser.add_argument("--out-dir", default=str(ROOT / "reports/cosima_bridge_current_audit"))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="laue511_bridge_audit_") as tmp:
        tmp_path = Path(tmp)
        sidecar = convert_phase_space_csv(
            args.input,
            tmp_path / "cosima_eventlist.source",
            tmp_path / "phase_space_sidecar.json",
            args.history,
        )
    metrics = _summarize_sidecar(sidecar)
    metrics["source_csv"] = args.input
    metrics["history_csv"] = args.history
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_summary(out_dir / "summary.md", metrics)
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0 if metrics["ok"] else 1


def _summarize_sidecar(sidecar: dict[str, object]) -> dict[str, object]:
    provenance = sidecar["provenance"]
    n_rows = int(sidecar["n_rows"])
    joined = int(sidecar["history_join"]["matched_rows"])
    missing_ring = sum(1 for row in provenance if row["ring_id"] is None)
    missing_tile = sum(1 for row in provenance if row["tile_id"] is None)
    branches = {}
    rings = {}
    for row in provenance:
        branches[row["branch"]] = branches.get(row["branch"], 0) + 1
        rings[str(row["ring_id"])] = rings.get(str(row["ring_id"]), 0) + 1
    return {
        "ok": n_rows > 0 and joined == n_rows and missing_ring == 0 and missing_tile == 0,
        "n_rows": n_rows,
        "history_joined_rows": joined,
        "missing_ring_id_rows": missing_ring,
        "missing_tile_id_rows": missing_tile,
        "branches": branches,
        "rings": rings,
        "preserved": sidecar["preserved"],
    }


def _write_summary(path: Path, metrics: dict[str, object]) -> None:
    lines = [
        "# Cosima Bridge Audit",
        "",
        f"Source phase space: `{metrics['source_csv']}`",
        f"History source: `{metrics['history_csv']}`",
        "",
        f"- ok: `{metrics['ok']}`",
        f"- rows: `{metrics['n_rows']}`",
        f"- history-joined rows: `{metrics['history_joined_rows']}`",
        f"- missing ring_id rows: `{metrics['missing_ring_id_rows']}`",
        f"- missing tile_id rows: `{metrics['missing_tile_id_rows']}`",
        f"- branches: `{metrics['branches']}`",
        f"- rings: `{metrics['rings']}`",
        "",
        "The EventList text and full sidecar were generated in a temporary directory",
        "for this audit and then removed. The retained evidence is this summary and",
        "`metrics.json`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
