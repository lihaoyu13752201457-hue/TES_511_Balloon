#!/usr/bin/env python3
"""Validate reconstruction of the current CC-HIT estimator from HTsim fields."""

from __future__ import annotations

import gzip
import json
import math
import re
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SIM_DIR = Path(
    "/mnt/data/TES_Balloon_511_data/SG3/"
    "m05new_minimal_sd_alpha_fixedseed_pilot_20260823_v1/"
    "m05z_sg3_minimal_fixedseed_alpha_all_100/pass"
)
OUTPUT = PACKAGE / "FIXEDSEED_HTSIM_BRIDGE_VALIDATION_V2.json"
EVENTS = 100

SCINT_CENTERS = {
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm": (-6.08911, -6.76237, 33.98055),
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm": (-29.80831, 17.80555, -8.23908),
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm": (23.57825, 17.80555, 45.14748),
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm": (-13.19737, 14.21073, 11.59823),
    "BGO_S3D_O8_FullWrap_BottomCap_30mm": (-23.63305, 14.95666, -5.51490),
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm": (16.73710, 14.21073, 41.53270),
}
TES_RE = re.compile(r"^TP_L(?P<layer>[0-5])_\d+$")
CC_RE = re.compile(
    r"^CC HIT (?P<volume>\S+) edep_keV=(?P<e>[0-9.eE+-]+) "
    r"x=(?P<x>[0-9.eE+-]+) y=(?P<y>[0-9.eE+-]+) z=(?P<z>[0-9.eE+-]+)\b"
)
HT_RE = re.compile(
    r"^HTsim (?P<kind>\d+);\s*(?P<x>[0-9.eE+-]+);\s*(?P<y>[0-9.eE+-]+);"
    r"\s*(?P<z>[0-9.eE+-]+);\s*(?P<e>[0-9.eE+-]+);\s*(?P<t>[0-9.eE+-]+)"
)


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


def parse(path: Path) -> list[dict]:
    result = []
    current = None
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            line = raw.strip()
            if line.startswith("ID "):
                current = {"id": int(line.split()[1]), "cc": {}, "ht": []}
                continue
            if current is None:
                continue
            if line == "SE":
                result.append(current)
                current = None
                continue
            match = CC_RE.match(line)
            if match:
                volume = match.group("volume")
                if volume in SCINT_CENTERS or TES_RE.match(volume):
                    energy = float(match.group("e"))
                    row = current["cc"].setdefault(
                        volume, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0}
                    )
                    row["e"] += energy
                    row["wx"] += energy * float(match.group("x"))
                    row["wy"] += energy * float(match.group("y"))
                    row["wz"] += energy * float(match.group("z"))
                continue
            match = HT_RE.match(line)
            if match:
                current["ht"].append(
                    {
                        "kind": int(match.group("kind")),
                        "xyz": tuple(float(match.group(axis)) for axis in ("x", "y", "z")),
                        "e": float(match.group("e")),
                    }
                )
    if current is not None:
        result.append(current)
    if len(result) != EVENTS:
        raise RuntimeError(f"event count {len(result)} != {EVENTS}")
    return result


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    paths = sorted(SIM_DIR.glob("*.sim.gz"))
    if len(paths) != 1:
        raise RuntimeError(f"expected one SIM, found {len(paths)}")
    events = parse(paths[0])
    mismatches = []
    tes_hits = scint_hits = 0
    for event in events:
        expected_tes = []
        expected_scint = {}
        for volume, row in event["cc"].items():
            if row["e"] <= 0:
                continue
            if TES_RE.match(volume):
                expected_tes.append(
                    {
                        "volume": volume,
                        "xyz": (row["wx"] / row["e"], row["wy"] / row["e"], row["wz"] / row["e"]),
                        "e": row["e"],
                    }
                )
            else:
                expected_scint[volume] = row["e"]
        raw_got_tes = [row for row in event["ht"] if row["kind"] == 2]
        grouped_tes = {}
        for row in raw_got_tes:
            grouped_tes[row["xyz"]] = grouped_tes.get(row["xyz"], 0.0) + row["e"]
        got_tes = [
            {"kind": 2, "xyz": xyz, "e": energy}
            for xyz, energy in grouped_tes.items()
        ]
        got_scint = [row for row in event["ht"] if row["kind"] == 4]
        tes_hits += len(got_tes)
        scint_hits += len(got_scint)
        if len(expected_tes) != len(got_tes):
            mismatches.append({"event": event["id"], "type": "tes_count", "cc": len(expected_tes), "ht": len(got_tes)})
        else:
            remaining = list(got_tes)
            for expected in expected_tes:
                nearest = min(remaining, key=lambda row: distance(expected["xyz"], row["xyz"]))
                remaining.remove(nearest)
                layer = int(TES_RE.match(expected["volume"]).group("layer"))
                local_x = (nearest["xyz"][0] - nearest["xyz"][2]) / math.sqrt(2.0)
                inferred_layer = min(
                    range(6), key=lambda index: abs(local_x - (-3.0 + 1.2 * index))
                )
                if (
                    distance(expected["xyz"], nearest["xyz"]) > 0.20
                    or inferred_layer != layer
                    or not math.isclose(
                    expected["e"], nearest["e"], rel_tol=2e-5, abs_tol=2e-3
                    )
                ):
                    mismatches.append({"event": event["id"], "type": "tes_value", "cc": expected, "ht": nearest})
        reconstructed_scint = {}
        for row in got_scint:
            volume, center = min(SCINT_CENTERS.items(), key=lambda item: distance(item[1], row["xyz"]))
            if distance(center, row["xyz"]) > 2e-4:
                mismatches.append({"event": event["id"], "type": "unknown_scint_center", "ht": row})
                continue
            reconstructed_scint[volume] = row["e"]
        if set(expected_scint) != set(reconstructed_scint):
            mismatches.append({"event": event["id"], "type": "scint_set", "cc": sorted(expected_scint), "ht": sorted(reconstructed_scint)})
        else:
            for volume in expected_scint:
                if not math.isclose(
                    expected_scint[volume], reconstructed_scint[volume], rel_tol=2e-5, abs_tol=2e-3
                ):
                    mismatches.append(
                        {
                            "event": event["id"],
                            "type": "scint_energy",
                            "volume": volume,
                            "cc": expected_scint[volume],
                            "ht": reconstructed_scint[volume],
                        }
                    )
    payload = {
        "schema_version": 1,
        "status": "PASS__HTSIM_RECONSTRUCTS_ACTIVE_CC_HITS" if not mismatches else "FAIL__HTSIM_BRIDGE_MISMATCH",
        "events": len(events),
        "tes_htsim_hits": tes_hits,
        "scintillator_htsim_hits": scint_hits,
        "mismatch_count": len(mismatches),
        "first_mismatches": mismatches[:20],
        "bridge_policy": "HTsim kind=2: TES hit centroid/energy; kind=4: nearest one of six fixed scintillator centers",
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
