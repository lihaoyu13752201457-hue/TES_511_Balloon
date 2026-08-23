#!/usr/bin/env python3
"""Apply the retained M05 response chain to SG3B's own 37,194-ray SIM."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = ROOT / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820"
SOURCE = PACKAGE / "config/sg3b_signal_37194.source"
SIM = ROOT / "runs/m05new_sg3b_signal_20260820/M05NEW_SG3B_Signal37194.inc1.id1.sim.gz"
EVENTLIST = ROOT / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
GEOMETRY = Path("/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/geometry/DEMO2_DR_v3p5_SG3B.geo.setup")
OUT = PACKAGE / "outputs/01_signal"

sys.path.insert(0, str(ROOT / "DEEPSEEK_CODE/modified"))
from step05_side_compton import side_entry_disk, side_keep_from_hits  # noqa: E402

N_RAYS = 37_194
APERTURE_CM2 = 20.08476
FWHM_KEV = 0.420
SIGMA_KEV = FWHM_KEV / 2.3548200450309493
PIXEL_THRESHOLD_KEV = 0.3
VETO_THRESHOLD_KEV = 50.0
SOURCE_SEED = 1_058_253_892
PLASTIC = {
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
}
BGO = {
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
}
WINDOWS = {"broad_480_550": (480.0, 550.0), "w2_510p58_511p42": (510.58, 511.42)}
STAGES = (
    "pre_veto",
    "plastic_positron_veto",
    "bgo_active_scintillator_veto",
    "combined_active_veto",
    "compton_trajectory_veto",
)
ID_RE = re.compile(r"^ID\s+(\d+)\s+\d+")
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pixel>\d+)$")
CC_HIT_RE = re.compile(
    r"^CC HIT\s+(\S+)\s+edep_keV=([-\deE\.+]+)\s+x=([-\deE\.+]+)\s+y=([-\deE\.+]+)\s+z=([-\deE\.+]+)"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def keyed_standard_normal(*keys: object) -> float:
    payload = "|".join(str(key) for key in keys).encode()
    digest = hashlib.blake2b(payload, digest_size=16).digest()
    u1 = max(int.from_bytes(digest[:8], "little") / 2**64, 1e-300)
    u2 = int.from_bytes(digest[8:], "little") / 2**64
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def main() -> None:
    source_text = SOURCE.read_text(encoding="utf-8")
    if "cosima_spectra_dp_2602units" in source_text:
        raise RuntimeError("legacy factor-1000 spectrum reference found")
    if f"Geometry {GEOMETRY}" not in source_text or f"Seed {SOURCE_SEED}" not in source_text:
        raise RuntimeError("source contract differs from registered geometry/seed")
    if sum(1 for _ in EVENTLIST.open("r", encoding="utf-8")) != N_RAYS:
        raise RuntimeError("EventList row count is not 37,194")

    header_geometry = None
    header_seed = None
    with gzip.open(SIM, "rt") as handle:
        for line in handle:
            if line.startswith("Geometry"):
                header_geometry = line.split(maxsplit=1)[1].strip()
            elif line.startswith("Seed"):
                header_seed = int(line.split()[1])
            elif line.startswith("ID "):
                break
    if header_geometry != str(GEOMETRY):
        raise RuntimeError(f"SIM geometry mismatch: {header_geometry}")
    if header_seed != SOURCE_SEED:
        raise RuntimeError(f"SIM seed mismatch: {header_seed} != {SOURCE_SEED}")

    # Values are read from the retained Step09 optics-bridge contract.  The
    # Be-window radius is 1.898 cm (not the smaller focused-ray r99 radius).
    disk = side_entry_disk((-13.1, 0.0, -5.2), 1.898, 45.0)
    counts = {window: {stage: 0 for stage in STAGES} for window in WINDOWS}
    events = 0
    detector_positive = 0
    current_id = None
    pixels: dict[str, dict[str, float]] = {}
    plastic_keV = 0.0
    bgo_keV = 0.0

    def flush() -> None:
        nonlocal current_id, pixels, plastic_keV, bgo_keV, detector_positive
        if current_id is None:
            return
        measured_hits = []
        for uid, record in sorted(pixels.items()):
            energy = float(record["e"])
            if energy <= 0:
                continue
            measured = energy + SIGMA_KEV * keyed_standard_normal("sg3b_signal", current_id, uid)
            if measured >= PIXEL_THRESHOLD_KEV:
                measured_hits.append(SimpleNamespace(
                    e=measured,
                    x=float(record["wx"]) / energy,
                    y=float(record["wy"]) / energy,
                    z=float(record["wz"]) / energy,
                    pixel_uid=uid,
                    layer=int(record["layer"]),
                ))
        if measured_hits:
            detector_positive += 1
        total = math.fsum(hit.e for hit in measured_hits)
        plastic_pass = plastic_keV < VETO_THRESHOLD_KEV
        bgo_pass = bgo_keV < VETO_THRESHOLD_KEV
        combined = plastic_pass and bgo_pass
        topology = combined and side_keep_from_hits(measured_hits, disk, "keep")[0]
        for window, bounds in WINDOWS.items():
            if not bounds[0] <= total < bounds[1]:
                continue
            counts[window]["pre_veto"] += 1
            if plastic_pass:
                counts[window]["plastic_positron_veto"] += 1
            if bgo_pass:
                counts[window]["bgo_active_scintillator_veto"] += 1
            if combined:
                counts[window]["combined_active_veto"] += 1
            if topology:
                counts[window]["compton_trajectory_veto"] += 1
        current_id = None
        pixels = {}
        plastic_keV = 0.0
        bgo_keV = 0.0

    with gzip.open(SIM, "rt") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            match = ID_RE.match(line)
            if match:
                if current_id is not None:
                    raise RuntimeError("event boundary missing")
                current_id = int(match.group(1))
                events += 1
                continue
            if not line.startswith("CC HIT "):
                continue
            match = CC_HIT_RE.match(line)
            if match is None:
                continue
            volume, edep, x, y, z = match.groups()
            energy = float(edep)
            pixel = TP_RE.match(volume)
            if pixel:
                record = pixels.setdefault(volume, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(pixel.group("layer"))})
                record["e"] += energy
                record["wx"] += energy * float(x)
                record["wy"] += energy * float(y)
                record["wz"] += energy * float(z)
            elif volume in PLASTIC:
                plastic_keV += energy
            elif volume in BGO:
                bgo_keV += energy
    flush()
    if events != N_RAYS:
        raise RuntimeError(f"SIM event count {events} != {N_RAYS}")

    effective_area = {}
    for window, stage_counts in counts.items():
        effective_area[window] = {}
        for stage, count in stage_counts.items():
            p = count / N_RAYS
            p_sigma = math.sqrt(p * (1.0 - p) / N_RAYS)
            effective_area[window][stage] = {
                "count": count,
                "survival": p,
                "survival_binomial_sigma": p_sigma,
                "Aeff_cm2": APERTURE_CM2 * p,
                "Aeff_binomial_sigma_cm2": APERTURE_CM2 * p_sigma,
            }

    result = {
        "schema_version": 1,
        "status": "PASS",
        "candidate": "SG3B",
        "scope": "candidate_own_37194_ray_signal",
        "events": events,
        "detector_positive_events": detector_positive,
        "source_seed": SOURCE_SEED,
        "sim_header_seed": header_seed,
        "geometry": str(GEOMETRY),
        "response": {
            "fwhm_keV_per_pixel": FWHM_KEV,
            "post_noise_pixel_threshold_keV": PIXEL_THRESHOLD_KEV,
            "active_veto_threshold_keV": VETO_THRESHOLD_KEV,
            "side_entry_disk": {"local_center_cm": [-13.1, 0.0, -5.2], "radius_cm": 1.898, "rotation_y_deg": 45.0},
        },
        "optical_aperture_cm2": APERTURE_CM2,
        "stage_counts": counts,
        "effective_area": effective_area,
        "provenance": {
            "source": str(SOURCE), "source_sha256": sha256(SOURCE),
            "eventlist": str(EVENTLIST), "eventlist_sha256": sha256(EVENTLIST),
            "sim": str(SIM), "sim_sha256": sha256(SIM),
            "geometry_sha256": sha256(GEOMETRY),
        },
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "events": events,
        "w2_final": effective_area["w2_510p58_511p42"]["compton_trajectory_veto"],
        "sim_sha256": result["provenance"]["sim_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
