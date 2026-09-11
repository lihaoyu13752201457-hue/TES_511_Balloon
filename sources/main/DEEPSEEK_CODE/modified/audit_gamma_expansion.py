#!/usr/bin/env python3
"""Validate the 2026-08-19/20 gamma expansion without scanning SIM payloads."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path("/mnt/data/TES_511_Balloon_511_data/SH3/sh3_optv3_60cm_full_adaptive_2p5h_v1")
PRIOR_ROOTS = (
    Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_60cm_full_adaptive_2p5h_v1"),
    Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_m05_delayed_8m_v1"),
    Path("/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_signal_37194_focal_z2p8_v1"),
)
OUT = Path(__file__).resolve().parents[1] / "outputs/03_gamma_expansion_audit_20260820.json"
EXPECTED_SETUP = Path(
    "/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/geometry_optimization_20260815/"
    "sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3_60cm.geo.setup"
).resolve()
CORRECTED_TOKEN = "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
FORBIDDEN_TOKEN = "cosima_spectra_dp_2602units"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    round_rows = []
    all_seeds: list[int] = []
    total_events = 0
    total_tt = 0.0
    total_sim_bytes = 0
    total_bundle_bytes = 0

    for index in range(5, 37):
        name = f"round{index:03d}"
        bundle = ROOT / "rounds" / name / "corrected"
        controller_path = bundle / "run/controller_state.json"
        receipt_dir = bundle / "run/receipts"
        preflight_path = bundle / "generated/preflight.json"
        seed_registry_path = bundle / "generated/seed_registry.json"
        if not all(path.exists() for path in (controller_path, receipt_dir, preflight_path, seed_registry_path)):
            fail(errors, f"{name}: required controller/receipt/preflight/seed files missing")
            continue
        controller = load(controller_path)
        receipts = [load(path) for path in sorted(receipt_dir.glob("*.json"))]
        preflight = load(preflight_path)
        registry = load(seed_registry_path)
        if controller.get("status") != "COMPLETE" or controller.get("error") is not None:
            fail(errors, f"{name}: controller not COMPLETE")
        if int(controller.get("planned_jobs", -1)) != 8 or int(controller.get("completed_count", -1)) != 8:
            fail(errors, f"{name}: controller job closure is not 8/8")
        if len(receipts) != 8:
            fail(errors, f"{name}: receipt count {len(receipts)} != 8")
        if not str(preflight.get("status", "")).startswith("PASS__"):
            fail(errors, f"{name}: preflight is not PASS")
        if registry.get("status") != "PASS__FRESH_GLOBALLY_DISJOINT_SEEDS":
            fail(errors, f"{name}: seed registry is not PASS")

        round_events = 0
        round_tt = 0.0
        round_sim_bytes = 0
        for receipt in receipts:
            job_id = str(receipt.get("job_id", ""))
            if receipt.get("status") != "PASS" or int(receipt.get("returncode", -1)) != 0:
                fail(errors, f"{name}/{job_id}: receipt not PASS/returncode 0")
            if receipt.get("family") != "gamma" or receipt.get("mode") != "instant":
                fail(errors, f"{name}/{job_id}: not gamma INSTANT")
            seed = int(receipt.get("seed", -1))
            header = receipt.get("sim_header", {})
            if int(header.get("seed", -2)) != seed:
                fail(errors, f"{name}/{job_id}: SIM header seed mismatch")
            setup = Path(str(receipt.get("setup_path", ""))).resolve()
            header_setup = Path(str(header.get("geometry", ""))).resolve()
            if setup != EXPECTED_SETUP or header_setup != EXPECTED_SETUP:
                fail(errors, f"{name}/{job_id}: geometry header/setup mismatch")
            sim = Path(str(receipt.get("sim_path", "")))
            source = Path(str(receipt.get("source_path", "")))
            if not sim.is_file() or sim.stat().st_size != int(receipt.get("sim_bytes", -1)):
                fail(errors, f"{name}/{job_id}: SIM path/size mismatch")
            if not source.is_file():
                fail(errors, f"{name}/{job_id}: source missing")
            else:
                text = source.read_text(encoding="utf-8")
                if FORBIDDEN_TOKEN in text or text.count(CORRECTED_TOKEN) != 20:
                    fail(errors, f"{name}/{job_id}: corrected-keV source contract mismatch")
                if sha256(source) != receipt.get("source_sha256"):
                    fail(errors, f"{name}/{job_id}: source digest mismatch")
            events = int(receipt.get("events", 0))
            tt = float(receipt.get("isotope_dat", {}).get("TT_s", 0.0))
            generated = int(receipt.get("log", {}).get("generated_events", -1))
            if events <= 0 or generated != events or tt <= 0.0:
                fail(errors, f"{name}/{job_id}: events/generated/TT closure failed")
            all_seeds.append(seed)
            round_events += events
            round_tt += tt
            round_sim_bytes += int(receipt.get("sim_bytes", 0))
        if round_events != 3_207_738:
            fail(errors, f"{name}: primary total {round_events} != 3,207,738")
        bundle_bytes = sum(path.stat().st_size for path in bundle.rglob("*") if path.is_file())
        round_rows.append({
            "round": name,
            "controller_status": controller.get("status"),
            "receipt_count": len(receipts),
            "events": round_events,
            "sum_TT_s": round_tt,
            "sim_bytes": round_sim_bytes,
            "bundle_bytes": bundle_bytes,
            "analysis_disposition": "EXCLUDE__CANARY_SEED_REUSE" if index == 5 else "INCLUDE",
        })
        total_events += round_events
        total_tt += round_tt
        total_sim_bytes += round_sim_bytes
        total_bundle_bytes += bundle_bytes

    duplicates = sorted(seed for seed, count in Counter(all_seeds).items() if count > 1)
    if duplicates:
        fail(errors, f"duplicate full-production seeds across rounds: {duplicates}")
    prior_seeds: set[int] = set()
    for prior_root in PRIOR_ROOTS:
        if not prior_root.exists():
            continue
        for path in prior_root.rglob("seed_registry.json"):
            try:
                rows = load(path).get("seeds", [])
            except (OSError, json.JSONDecodeError):
                continue
            for row in rows:
                seed = row.get("seed") if isinstance(row, dict) else None
                if isinstance(seed, int) and seed > 0:
                    prior_seeds.add(seed)
        for path in prior_root.rglob("*receipt*.json"):
            try:
                payload = load(path)
            except (OSError, json.JSONDecodeError):
                continue
            seed = payload.get("seed") if isinstance(payload, dict) else None
            if isinstance(seed, int) and seed > 0:
                prior_seeds.add(seed)
    prior_collisions = sorted(set(all_seeds) & prior_seeds)
    if prior_collisions:
        fail(errors, f"full-production seeds collide with retained prior campaigns: {prior_collisions}")
    warnings.append(
        "round005 is excluded from analysis: --canary and full production used the same bundle profile/job IDs; "
        "deterministic seed derivation therefore reused the eight canary seeds after the canary directory was deleted."
    )
    result = {
        "schema_version": 1,
        "status": "PASS__GAMMA_EXPANSION_RECEIPT_AUDIT__ROUND005_EXCLUDED" if not errors else "FAIL__GAMMA_EXPANSION_RECEIPT_AUDIT",
        "root": str(ROOT),
        "scope": "receipt/source/header validation; no full SIM digest or payload scan",
        "expected_setup": str(EXPECTED_SETUP),
        "rounds_present": len(round_rows),
        "rounds_included": [row["round"] for row in round_rows if row["analysis_disposition"] == "INCLUDE"],
        "rounds_excluded": [row["round"] for row in round_rows if row["analysis_disposition"] != "INCLUDE"],
        "full_production_seed_count": len(all_seeds),
        "full_production_seed_duplicates": duplicates,
        "retained_prior_seed_count_checked": len(prior_seeds),
        "retained_prior_seed_collisions": prior_collisions,
        "total_events_all_32_rounds": total_events,
        "total_events_included_31_rounds": sum(row["events"] for row in round_rows if row["analysis_disposition"] == "INCLUDE"),
        "total_TT_s_all_32_rounds": total_tt,
        "total_SIM_bytes_all_32_rounds": total_sim_bytes,
        "total_bundle_bytes_all_32_rounds": total_bundle_bytes,
        "errors": errors,
        "warnings": warnings,
        "rounds": round_rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "status", "rounds_present", "rounds_included", "rounds_excluded",
        "total_events_all_32_rounds", "total_events_included_31_rounds",
        "total_SIM_bytes_all_32_rounds", "total_bundle_bytes_all_32_rounds", "errors",
    )}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
