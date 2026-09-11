#!/usr/bin/env python3
"""Freeze the one candidate-own focused-511 replay source.

The input EventList is streamed from the established f10m/A1 post-Be-window
authority.  No EventList or baseline SIM is copied into this worktree.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
SETUP = (
    PACKAGE
    / "agents/geometry/candidate_proxy/"
    "S3D_O8_unified_Al_mag05_innerBPE_topcatch_proxy.geo.setup"
)
EVENTLIST = Path(
    "/home/ubuntu/TES_511_Balloon/stepwise_maintenance/step09_optics_bridge/"
    "outputs_f10m_a1_v3p5/eventlists/"
    "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)
INPUT_DIR = PACKAGE / "focused_signal"
RUN_DIR = ROOT / (
    "runs/s3d_o8_loop_engineering_20260814/"
    "af1_48_focused_signal_20260814"
)
RUN_NAME = "Opticsim_laue_f10m_a1_af1_48_signal37194"
SOURCE = INPUT_DIR / f"{RUN_NAME}.source"
PLAN = INPUT_DIR / "candidate_signal_plan.json"
SEED = 260616
TRIALS = 37_194


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not SETUP.is_file() or not EVENTLIST.is_file():
        raise FileNotFoundError("candidate setup or signal EventList is missing")
    rows = sum(
        1
        for line in EVENTLIST.open("r", encoding="utf-8")
        if line.strip() and not line.startswith("#")
    )
    if rows != TRIALS:
        raise RuntimeError(f"signal EventList rows={rows}, expected={TRIALS}")

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    prefix = RUN_DIR / RUN_NAME
    source_text = f"""# AF1-48 candidate-own focused signal replay; post-Be scope only.
Version 1
Geometry {SETUP.resolve()}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {SEED}

Run {RUN_NAME}
{RUN_NAME}.FileName {prefix.resolve()}
{RUN_NAME}.Triggers {TRIALS}
{RUN_NAME}.Source {RUN_NAME}_EventList
{RUN_NAME}_EventList.EventList {EVENTLIST.resolve()}
"""
    if SOURCE.exists() and SOURCE.read_text(encoding="utf-8") != source_text:
        raise RuntimeError(f"refusing to change frozen source: {SOURCE}")
    SOURCE.write_text(source_text, encoding="utf-8")

    payload = {
        "schema_version": 1,
        "status": "FROZEN__TRANSPORT_NOT_YET_VERIFIED",
        "claim_boundary": (
            "Candidate-own post-Be-window focused signal only; outer-envelope "
            "transmission and background are outside this replay."
        ),
        "candidate_setup": str(SETUP.resolve()),
        "candidate_setup_sha256": sha256(SETUP),
        "eventlist": str(EVENTLIST.resolve()),
        "eventlist_sha256": sha256(EVENTLIST),
        "eventlist_rows": rows,
        "source": str(SOURCE.resolve()),
        "source_sha256": sha256(SOURCE),
        "seed": SEED,
        "run_name": RUN_NAME,
        "expected_sim": str(Path(f"{prefix}.inc1.id1.sim.gz").resolve()),
    }
    PLAN.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(PLAN)


if __name__ == "__main__":
    main()
