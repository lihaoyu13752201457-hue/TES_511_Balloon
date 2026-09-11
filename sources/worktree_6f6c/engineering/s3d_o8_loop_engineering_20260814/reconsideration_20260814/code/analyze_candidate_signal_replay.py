#!/usr/bin/env python3
"""Apply the frozen corrected-keV common response to the AF1-48 signal SIM."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import pickle
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
PLAN = PACKAGE / "focused_signal/candidate_signal_plan.json"
OUTPUT = PACKAGE / "focused_signal/candidate_signal_result.json"
CUTFLOW = PACKAGE / "focused_signal/candidate_signal_cutflow.csv"
M05_CODE = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/code"
)
BASELINE_ACCEPTANCE = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/"
    "outputs/04_common_response/signal_acceptance_effective_area.csv"
)
BRIDGE = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/stepwise_maintenance/"
    "step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json"
)
OPTICS = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/stepwise_maintenance/"
    "step04_opticsim/optics_aeff_authority_f10m_a1.json"
)
BASELINE_S20 = 1645.3877530659986


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_baseline() -> dict[str, str]:
    with BASELINE_ACCEPTANCE.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if (
                row["geometry"] == "S3d_O8"
                and row["response_state"] == "measured"
                and row["stage"] == "side_compton_fov_pass"
                and row["window_id"] == "w2_510p58_511p42"
            ):
                return row
    raise RuntimeError("baseline signal row not found")


def sim_header_seed(path: Path) -> int:
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for line in handle:
            if line.startswith("Seed "):
                return int(line.split()[1])
            if line == "SE\n":
                break
    raise RuntimeError("candidate SIM header seed is absent")


def main() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    sim = Path(plan["expected_sim"])
    if not sim.is_file():
        raise FileNotFoundError(sim)

    sys.path.insert(0, str(M05_CODE))
    import build_common_response as common  # type: ignore
    import run_prompt_analysis as prompt  # type: ignore

    active = [
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
        "BGO_S3D_O8_FullWrap_BottomCap_30mm",
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
    ]
    event_sha = plan["eventlist_sha256"]
    header_seed = sim_header_seed(sim)
    # Use the candidate's actual transport identity in the keyed detector
    # response.  Only the EventList is paired to baseline; transport and
    # response RNGs are intentionally not claimed to be eventwise paired.
    job = {
        "scan_index": 0,
        "geometry": "S3d_O8",
        "family": "focused_511",
        "mode": "signal",
        "input_id": "focused_signal_eventlist",
        "batch_id": f"eventlist_sha256:{event_sha}",
        "job_id": plan["run_name"],
        "events": int(plan["eventlist_rows"]),
        "sim_path": str(sim),
        "seed": header_seed,
        "source_declared_seed": int(plan["seed"]),
        "shield_volumes": [name for name in active if "Plastic" not in name],
        "plastic_volumes": [name for name in active if "Plastic" in name],
    }
    optics = json.loads(OPTICS.read_text(encoding="utf-8"))
    aeff_cm2 = float(optics["aeff_511_cm2"])
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))["bridge"]

    with tempfile.TemporaryDirectory(prefix="af1-signal-scan-", dir="/tmp") as tmp:
        cache = Path(tmp) / "cache"
        cache.mkdir()
        scan = prompt.scan_job(job, str(cache))
        catalog_path = Path(tmp) / "candidate.pkl"
        common.publish_signal_catalog(
            job, scan, catalog_path, aeff_cm2, event_sha, sha256(sim)
        )
        result = common.evaluate_catalog(
            {
                "path": str(catalog_path),
                "geometry": "S3d_O8",
                "stream": "signal",
                "family": "focused_511",
                "bridge": bridge,
            }
        )
        cutflow = common.common_cutflow([result], aeff_cm2)

    with CUTFLOW.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cutflow[0]))
        writer.writeheader()
        writer.writerows(cutflow)

    candidate = next(
        row
        for row in cutflow
        if row["response_state"] == "measured"
        and row["stage"] == "side_compton_fov_pass"
        and row["window_id"] == "w2_510p58_511p42"
    )
    baseline = load_baseline()
    ratio = float(candidate["selected_events"]) / float(baseline["selected_events"])
    s20 = BASELINE_S20 * ratio
    payload = {
        "schema_version": 1,
        "status": "PASS__CANDIDATE_OWN_FOCUSED_SIGNAL_COMMON_RESPONSE",
        "claim_boundary": (
            "Post-Be-window focused signal only. The result does not validate "
            "outer-envelope signal transmission or any background suppression."
        ),
        "candidate_setup": plan["candidate_setup"],
        "candidate_sim": str(sim),
        "candidate_sim_sha256": sha256(sim),
        "candidate_source_declared_seed": plan["seed"],
        "candidate_transport_header_seed": header_seed,
        "response_pairing": (
            "same EventList local IDs as baseline; transport and keyed-response "
            "RNG identities are candidate-specific, matching the established "
            "common-response contract"
        ),
        "trials": int(plan["eventlist_rows"]),
        "baseline_selected_events": int(baseline["selected_events"]),
        "candidate_selected_events": int(candidate["selected_events"]),
        "signal_retention_ratio": ratio,
        "candidate_selected_aeff_cm2": float(candidate["weighted_value"]),
        "candidate_selected_aeff_lower95_cm2": float(candidate["weighted_lower95"]),
        "candidate_selected_aeff_upper95_cm2": float(candidate["weighted_upper95"]),
        "baseline_S20_counts": BASELINE_S20,
        "candidate_S20_counts": s20,
        "candidate_B20_max_counts": (s20 / 10.0) ** 2,
        "cutflow": str(CUTFLOW.resolve()),
    }
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT)


if __name__ == "__main__":
    main()
