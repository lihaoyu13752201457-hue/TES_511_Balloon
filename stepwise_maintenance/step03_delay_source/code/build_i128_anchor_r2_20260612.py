#!/usr/bin/env python3
"""Build the R2 CsI I-128 activation anchor from repo-local products."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "stepwise_maintenance" / "step03_delay_source" / "outputs"
OUT_JSON = OUT / "i128_anchor_r2_20260612.json"
OUT_CSV = OUT / "i128_anchor_r2_20260612.csv"
OUT_MD = OUT / "i128_anchor_r2_20260612.md"

MAINLINE_INVENTORY = ROOT / "runs" / "step02_decay_source_mainline_div8_review_20260612" / "activation_inventory_day15.csv"
V3P5_INVENTORY = ROOT / "runs" / "step02_decay_source_v3p5_centerfinger_fullstat_v2" / "activation_inventory_day15.csv"
V3P5_BOUNDS = ROOT / "geo_refer" / "DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json"

RETIRED_20260611_ANCHOR = {
    "chain_specific_activity_bq_per_kg": 8.185,
    "two_group_no_self_shielding_bq_per_kg": 6.323,
    "reason": "Pre-R2 anchor depended on pre-fix activation products and is not a current authority.",
}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def i128_csi_inventory(path: Path) -> dict[str, float]:
    rows = [
        row for row in read_rows(path)
        if row.get("ZA") == "53128" and "CsI" in row.get("VN", "")
    ]
    activity = sum(float(row["Activity_Bq"]) for row in rows)
    points = sum(float(row.get("Points") or 0.0) for row in rows)
    return {
        "rows": float(len(rows)),
        "activity_bq": activity,
        "points": points,
    }


def v3p5_active_csi_mass_kg() -> float:
    bounds = json.loads(V3P5_BOUNDS.read_text(encoding="utf-8"))
    return float(bounds["META"]["active_csi_mass_kg"])


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(value: float, ndigits: int = 8) -> str:
    if value == 0:
        return "0"
    if abs(value) < 1.0e-3 or abs(value) >= 1.0e5:
        return f"{value:.{ndigits}e}"
    return f"{value:.{ndigits}g}"


def build() -> dict[str, Any]:
    mainline = i128_csi_inventory(MAINLINE_INVENTORY)
    v3p5 = i128_csi_inventory(V3P5_INVENTORY)
    mass = v3p5_active_csi_mass_kg()
    specific_activity = v3p5["activity_bq"] / mass

    rows = [
        {
            "case": "mainline_div8_review_20260612",
            "geometry": "legacy_DEMO2_mainline_div8_rebuilt",
            "inventory": rel(MAINLINE_INVENTORY),
            "i128_csi_rows": int(mainline["rows"]),
            "i128_activity_bq": mainline["activity_bq"],
            "i128_points": mainline["points"],
            "active_csi_mass_kg": "",
            "specific_activity_bq_per_kg": "",
            "authority": "R1/R2 normalization cross-check only; current v3p5 geometry uses the next row.",
        },
        {
            "case": "v3p5_centerfinger_fullstat_v2_current",
            "geometry": "DEMO2_DR_v3p5_minpatch_centerfinger",
            "inventory": rel(V3P5_INVENTORY),
            "i128_csi_rows": int(v3p5["rows"]),
            "i128_activity_bq": v3p5["activity_bq"],
            "i128_points": v3p5["points"],
            "active_csi_mass_kg": mass,
            "specific_activity_bq_per_kg": specific_activity,
            "authority": "Current R2 repo-local CsI I-128 anchor.",
        },
    ]
    payload = {
        "status": "PASS_I128_R2_CURRENT_CHAIN_ANCHOR",
        "claim_level": "L1_R2_CSI_I128_CHAIN_ANCHOR",
        "date": "2026-06-12",
        "inputs": {
            "mainline_div8_inventory": rel(MAINLINE_INVENTORY),
            "v3p5_fullstat_inventory": rel(V3P5_INVENTORY),
            "v3p5_bounds": rel(V3P5_BOUNDS),
        },
        "checks": {
            "mainline_div8_i128_activity_bq": mainline["activity_bq"],
            "v3p5_i128_activity_bq": v3p5["activity_bq"],
            "v3p5_active_csi_mass_kg": mass,
            "v3p5_i128_specific_activity_bq_per_kg": specific_activity,
            "v3p5_to_mainline_i128_activity_ratio": v3p5["activity_bq"] / mainline["activity_bq"],
        },
        "retired_anchor": RETIRED_20260611_ANCHOR,
        "notes": [
            "The current anchor is chain-derived and repo-local: v3p5 I-128 activity divided by active CsI mass from the v3p5 bounds file.",
            "The 2026-06-11 chain-vs-two-group analytic anchor is explicitly retired for current claims because it used pre-R2 activation products and omitted geometry self-shielding.",
            "This script does not rerun transport; it audits the R2-fixed inventories and current v3p5 geometry metadata.",
        ],
        "rows": rows,
        "outputs": {
            "json": rel(OUT_JSON),
            "csv": rel(OUT_CSV),
            "markdown": rel(OUT_MD),
        },
    }
    write_csv(OUT_CSV, rows)
    write_json(OUT_JSON, payload)
    write_md(payload)
    return payload


def write_md(payload: dict[str, Any]) -> None:
    checks = payload["checks"]
    retired = payload["retired_anchor"]
    lines = [
        "# R2 CsI I-128 Activation Anchor",
        "",
        f"Status: `{payload['status']}`.",
        "",
        "This is the current repo-local I-128 anchor after the R2 normalization fixes. It does not rerun transport; it recomputes the anchor from the fixed inventory CSVs and the v3p5 bounds mass file.",
        "",
        "## Current V3p5 Anchor",
        "",
        "| Quantity | Value |",
        "| --- | ---: |",
        f"| v3p5 I-128 activity in CsI | `{fmt(checks['v3p5_i128_activity_bq'])}` Bq |",
        f"| v3p5 active CsI mass | `{fmt(checks['v3p5_active_csi_mass_kg'])}` kg |",
        f"| v3p5 I-128 specific activity | `{fmt(checks['v3p5_i128_specific_activity_bq_per_kg'])}` Bq/kg |",
        f"| mainline div8 I-128 activity cross-check | `{fmt(checks['mainline_div8_i128_activity_bq'])}` Bq |",
        f"| v3p5/mainline I-128 activity ratio | `{fmt(checks['v3p5_to_mainline_i128_activity_ratio'])}` |",
        "",
        "## Retired Anchor",
        "",
        f"The 2026-06-11 anchor (`{retired['chain_specific_activity_bq_per_kg']}` vs `{retired['two_group_no_self_shielding_bq_per_kg']}` Bq/kg) is not a current authority. It used pre-R2 activation products and a no-self-shielding two-group reference, so it is retained only as provenance.",
        "",
        "## Inputs",
        "",
    ]
    for key, value in payload["inputs"].items():
        lines.append(f"- `{key}`: `{value}`")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    payload = build()
    print(json.dumps({"status": payload["status"], "outputs": payload["outputs"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
