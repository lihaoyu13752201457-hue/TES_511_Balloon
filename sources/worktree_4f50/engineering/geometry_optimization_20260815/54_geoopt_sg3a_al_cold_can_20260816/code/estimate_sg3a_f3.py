#!/usr/bin/env python3
"""Write a transparent pre-transport F3 estimate for SG3A.

This deliberately scales the frozen SE3 mission background by selected-volume
shares.  It is a sensitivity estimate, not candidate-own transport authority.
"""

from __future__ import annotations

import csv
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
REPO = SCRIPT.parents[4]
OUTPUT = PACKAGE / "data" / "sg3a_f3_pretransport_estimate.json"
BASELINE = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "48_se3_background_optimization_review_20260816/data/analysis_summary.json"
)
VOLUME_TABLE = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "48_se3_background_optimization_review_20260816/data/activation_origin_by_volume.csv"
)


def atomic_write_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = text.encode()
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        candidate = json.loads(text)
        for item in (existing, candidate):
            item.pop("generated_at_utc", None)
        if existing != candidate:
            raise RuntimeError(f"write-once estimate differs from current contract: {path}")
        return
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def rows_by_volume() -> dict[str, dict[str, str]]:
    with VOLUME_TABLE.open(newline="", encoding="utf-8") as handle:
        return {row["source_volume"]: row for row in csv.DictReader(handle)}


def main() -> int:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))["sensitivity"]["baseline"]
    rows = rows_by_volume()
    l0_share = float(rows["Cu_SubstrateSupport_SolidDisk_L0_deepest"]["selected_rate_share"])
    mxc_share = float(rows["ColdPlate_MXC_50mK_SD_anchor"]["selected_rate_share"])
    can_share = sum(
        float(rows[name]["selected_rate_share"])
        for name in (
            "Cu_50mK_StillLike_Can_bottom_cap_2mm",
            "Cu_50mK_StillLike_Can_side_wall_rectcut_window_band",
        )
    )
    bi_direct_attenuation = 0.527
    bi_upper_share = mxc_share * bi_direct_attenuation

    scenarios = {
        "conservative_benefit": {
            "l0_share_suppression": 0.5,
            "al_can_cu_lineage_suppression": 0.5,
            "fraction_of_bi_geometric_upper_realized": 0.0,
        },
        "central_engineering_estimate": {
            "l0_share_suppression": 1.0,
            "al_can_cu_lineage_suppression": 0.7,
            "fraction_of_bi_geometric_upper_realized": 0.5,
        },
        "optimistic_geometric_upper": {
            "l0_share_suppression": 1.0,
            "al_can_cu_lineage_suppression": 1.0,
            "fraction_of_bi_geometric_upper_realized": 1.0,
        },
    }
    f3_baseline = float(baseline["F3_ph_cm2_s"])
    b20_baseline = float(baseline["B20_counts"])
    for scenario in scenarios.values():
        reduction = (
            l0_share * scenario["l0_share_suppression"]
            + can_share * scenario["al_can_cu_lineage_suppression"]
            + bi_upper_share * scenario["fraction_of_bi_geometric_upper_realized"]
        )
        remaining = 1.0 - reduction
        scenario.update(
            {
                "estimated_background_reduction_fraction": reduction,
                "estimated_background_remaining_fraction": remaining,
                "estimated_B20_counts": b20_baseline * remaining,
                "estimated_F3_ph_cm2_s": f3_baseline * math.sqrt(remaining),
                "signal_retention_assumption": 1.0,
                "accepted_prompt_increment_assumption_cps": 0.0,
            }
        )

    payload = {
        "status": "PASS__SG3A_PRETRANSPORT_SENSITIVITY_ESTIMATE_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority_boundary": (
            "NOT_TRANSPORT__NOT_PROMOTION__conditional on no new accepted prompt and unchanged signal"
        ),
        "baseline": {
            "identity": "SE3 frozen central mission result",
            "F3_ph_cm2_s": f3_baseline,
            "B20_counts": b20_baseline,
            "S20_counts": float(baseline["S20_counts"]),
            "signal_Aeff_cm2": float(baseline["signal_Aeff_cm2"]),
        },
        "retained_small_table_levers": {
            "old_l0_disk_selected_rate_share": l0_share,
            "old_50mK_can_selected_rate_share": can_share,
            "mxc_selected_rate_share": mxc_share,
            "bi_direct_511_attenuation_screen": bi_direct_attenuation,
            "bi_mxc_geometric_upper_reduction_share": bi_upper_share,
        },
        "scenarios": scenarios,
        "headline": {
            "central_estimate_F3_ph_cm2_s": scenarios["central_engineering_estimate"]["estimated_F3_ph_cm2_s"],
            "conditional_range_F3_ph_cm2_s": [
                scenarios["optimistic_geometric_upper"]["estimated_F3_ph_cm2_s"],
                scenarios["conservative_benefit"]["estimated_F3_ph_cm2_s"],
            ],
            "interpretation": (
                "A defensible pre-transport estimate is about 5.8e-5, with a conditional "
                "5.1e-5 to 6.6e-5 engineering range. New accepted prompt, Al activation, "
                "or a different mission time profile can move the true result outside this range."
            ),
        },
        "required_closure": (
            "SG3A-own corrected prompt, buildup/inventory, actual-position delayed, fresh "
            "37194-ray signal, common response/veto/Step05, and 81-node/20-day fold"
        ),
    }
    atomic_write_once(OUTPUT, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload["headline"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
