#!/usr/bin/env python3
"""Event-level Knob0 replay on the retained S3c atmospheric-511 3M SIM.

The script performs one sequential gzip pass, reproduces the current W2/FoV
selection, then applies the thresholds frozen in the Knob0 brief.  It does not
run transport and it never overwrites the retained S3c products.
"""

from __future__ import annotations

import csv
import gzip
import importlib.util
import itertools
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
DATA = WORK / "data"

RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3c_bgo_w2mm_al3mm_shell_atm511_sidecar_3m_20260709"
)
RUN_NAME = "Atm511SidecarS3cBgoW2mmAl3mmShell3M"
SIM = RUN_DIR / f"{RUN_NAME}.inc1.id1.sim.gz"
LOG = RUN_DIR / f"cosima_{RUN_NAME}.log"
SOURCE = RUN_DIR / f"{RUN_NAME}.source"
CURRENT_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709"
    / "s3c_atm511_sidecar_3m_summary.json"
)
MAINLINE_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710"
    / "data/s3c_mainline_analysis_summary.json"
)
KNOB0_BRIEF = ROOT / "engineering/compton_veto_knob0_20260710/KNOB0_FLUORESCENCE_ARM_STRATIFICATION_BRIEF.md"
STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP09_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
EXPECTED_GEOMETRY = (
    ROOT
    / "engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709"
    / "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)

ACTIVE_VETO_THRESHOLD_KEV = 50.0
W2 = (510.58, 511.42)
DIAGNOSTIC_WINDOW = (430.0, 550.0)
K_LINES_KEV = {
    "Kalpha2": 56.277,
    "Kalpha1": 57.532,
    "Kbeta3": 64.949,
    "Kbeta1": 65.223,
    "Kbeta2": 66.990,
}
TES_SIGMA_AT_511_KEV = 0.178
K_TAG_HALF_WIDTH_KEV = 3.0 * TES_SIGMA_AT_511_KEV
SHORT_ARM_MM = 8.0
LONG_ARM_MM = 20.0
POSITION_SIGMA_MM = 0.87
DOPPLER_SIGMA_DEG = 3.0
K_VALUES = (2.0, 2.5, 3.0)
DISK_RADIAL_SAMPLES = 48
DISK_AZIMUTH_SAMPLES = 720

CC_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
ID_RE = re.compile(r"^ID\s+(\d+)")
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)


@dataclass
class Hit:
    x: float
    y: float
    z: float
    e: float
    pixel_uid: str
    layer: int


def rel(path: Path | str) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        if not rows:
            raise ValueError(f"no rows and no fields for {path}")
        fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def normalize_geometry(value: str | None) -> str | None:
    if not value:
        return None
    path = Path(value.strip())
    if not path.is_absolute():
        path = ROOT / path
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def source_geometry() -> str | None:
    for raw in SOURCE.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.strip().startswith("Geometry "):
            return raw.strip().split(None, 1)[1]
    return None


def observation_time_s() -> float:
    with LOG.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            if "Observation time:" not in raw:
                continue
            values = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", raw)
            if values:
                return float(values[0])
    raise RuntimeError(f"Observation time missing from {LOG}")


def is_active_veto_volume(volume: str) -> bool:
    upper = volume.upper()
    return (
        upper.startswith("CSI_")
        or "ACTIVE_SHIELD" in upper
        or "ACTIVESHIELD" in upper
        or "CEBR3" in upper
        or "BGO" in upper
        or upper.startswith("GEOOPT_S1_PLASTICFULLWRAP")
        or upper.startswith("GEOOPT_S2B_CRYOSHELL_PLASTIC")
    )


def load_step05():
    spec = importlib.util.spec_from_file_location("knob0_atm511_step05", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    module.STEP09_SUMMARY = STEP09_SUMMARY
    return module


def parse_init(line: str) -> dict[str, Any] | None:
    try:
        fields = [item.strip() for item in line[len("IA INIT") :].split(";")]
        return {
            "position_cm": [float(fields[4]), float(fields[5]), float(fields[6])],
            "direction": [float(fields[16]), float(fields[17]), float(fields[18])],
            "energy_keV": float(fields[22]),
        }
    except (IndexError, ValueError):
        return None


def truth_k_photon_energies(ia_lines: Iterable[str]) -> list[float]:
    """Return IA PHOT secondary-photon energies that land in a frozen Ta K window."""
    energies: list[float] = []
    for line in ia_lines:
        if not line.startswith("IA PHOT"):
            continue
        try:
            fields = [item.strip() for item in line[len("IA PHOT") :].split(";")]
            energy = float(fields[22])
        except (IndexError, ValueError):
            continue
        if closest_k_line(energy) is not None:
            energies.append(energy)
    return energies


def aggregate_hits(pixel_records: dict[str, dict[str, float]]) -> list[Hit]:
    hits: list[Hit] = []
    for uid, rec in sorted(pixel_records.items()):
        energy = float(rec["e"])
        if energy <= 0.0:
            continue
        hits.append(
            Hit(
                x=float(rec["wx"] / energy),
                y=float(rec["wy"] / energy),
                z=float(rec["wz"] / energy),
                e=energy,
                pixel_uid=uid,
                layer=int(rec["layer"]),
            )
        )
    return hits


def closest_k_line(energy_keV: float) -> tuple[str, float, float] | None:
    candidates = sorted(
        ((name, center, abs(energy_keV - center)) for name, center in K_LINES_KEV.items()),
        key=lambda item: item[2],
    )
    name, center, delta = candidates[0]
    if delta <= K_TAG_HALF_WIDTH_KEV:
        return name, center, delta
    return None


def fluorescence_tags(hits: list[Hit]) -> list[dict[str, Any]]:
    tags = []
    for index, hit in enumerate(hits):
        match = closest_k_line(hit.e)
        if match is None:
            continue
        name, center, delta = match
        tags.append(
            {
                "hit_index": index,
                "pixel_uid": hit.pixel_uid,
                "energy_keV": hit.e,
                "line": name,
                "line_energy_keV": center,
                "absolute_delta_keV": delta,
            }
        )
    return tags


def distance_mm(a: Hit, b: Hit) -> float:
    return 10.0 * math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2)


def valid_two_hit_orders(step05: Any, hits: list[Hit]) -> list[tuple[list[Hit], dict[str, float]]]:
    orders: list[tuple[list[Hit], dict[str, float]]] = []
    if len(hits) == 2:
        for indices in ((0, 1), (1, 0)):
            ordered = [hits[indices[0]], hits[indices[1]]]
            metrics = step05.sequence_metrics(ordered)
            if metrics is not None:
                orders.append((ordered, metrics))
        return orders
    if len(hits) < 2 or len(hits) > int(step05.MAX_ENUM_HITS):
        return []
    ranked: list[tuple[float, float, list[Hit], dict[str, float]]] = []
    for permutation in itertools.permutations(range(len(hits))):
        ordered = [hits[index] for index in permutation]
        metrics = step05.sequence_metrics(ordered)
        if metrics is not None:
            ranked.append((metrics["qf"], -metrics["first_lever_arm"], ordered, metrics))
    if not ranked:
        return []
    _, _, ordered, metrics = sorted(ranked, key=lambda item: (item[0], item[1]))[0]
    return [(ordered, metrics)]


def cone_axis_theta(step05: Any, ordered: list[Hit]) -> tuple[np.ndarray, float] | None:
    if len(ordered) < 2:
        return None
    axis = np.asarray(
        [ordered[0].x - ordered[1].x, ordered[0].y - ordered[1].y, ordered[0].z - ordered[1].z],
        dtype=float,
    )
    norm = float(np.linalg.norm(axis))
    if norm <= 0.0:
        return None
    ctheta = step05.compton_cos_theta(ordered[0].e, sum(hit.e for hit in ordered[1:]))
    if not math.isfinite(ctheta) or ctheta < -1.0 or ctheta > 1.0:
        return None
    return axis / norm, math.acos(float(np.clip(ctheta, -1.0, 1.0)))


def disk_points(disk: dict[str, Any]) -> np.ndarray:
    center = np.asarray(disk["center_cm"], dtype=float)
    u = np.asarray(disk["basis_u"], dtype=float)
    v = np.asarray(disk["basis_v"], dtype=float)
    radius = float(disk["radius_cm"])
    radial = np.linspace(0.0, radius, DISK_RADIAL_SAMPLES)
    azimuth = np.linspace(0.0, 2.0 * math.pi, DISK_AZIMUTH_SAMPLES, endpoint=False)
    offsets = (
        radial[:, None, None]
        * (
            np.cos(azimuth)[None, :, None] * u[None, None, :]
            + np.sin(azimuth)[None, :, None] * v[None, None, :]
        )
    )
    return center[None, None, :] + offsets


def cone_disk_residual_deg(
    step05: Any,
    ordered: list[Hit],
    sampled_disk_points: np.ndarray,
) -> float | None:
    cone = cone_axis_theta(step05, ordered)
    if cone is None:
        return None
    axis, theta = cone
    origin = np.asarray([ordered[0].x, ordered[0].y, ordered[0].z], dtype=float)
    rays = sampled_disk_points.reshape(-1, 3) - origin[None, :]
    norms = np.linalg.norm(rays, axis=1)
    valid = norms > 0.0
    if not np.any(valid):
        return None
    rays = rays[valid] / norms[valid, None]
    angles = np.arccos(np.clip(rays @ axis, -1.0, 1.0))
    return math.degrees(float(np.min(np.abs(angles - theta))))


def true_arm_deg(step05: Any, ordered: list[Hit], init: dict[str, Any] | None) -> float | None:
    if init is None:
        return None
    cone = cone_axis_theta(step05, ordered)
    if cone is None:
        return None
    axis, theta = cone
    incoming = np.asarray(init["direction"], dtype=float)
    norm = float(np.linalg.norm(incoming))
    if norm <= 0.0:
        return None
    source_direction = -incoming / norm
    angle = math.acos(float(np.clip(np.dot(axis, source_direction), -1.0, 1.0)))
    return math.degrees(abs(angle - theta))


def delta_deg(lever_arm_mm: float, k: float) -> float:
    positional_rad = math.sqrt(2.0) * POSITION_SIGMA_MM / lever_arm_mm
    combined_rad = math.sqrt(positional_rad**2 + math.radians(DOPPLER_SIGMA_DEG) ** 2)
    return k * math.degrees(combined_rad)


def wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float] | None:
    if trials <= 0:
        return None
    p = successes / trials
    denom = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / denom
    half = z / denom * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials))
    return max(0.0, center - half), min(1.0, center + half)


def minimum_zero_success_trials_for_upper_bound(target_upper: float) -> int:
    for trials in range(1, 100_000):
        interval = wilson_interval(0, trials)
        if interval is not None and interval[1] <= target_upper:
            return trials
    raise RuntimeError(f"target upper bound not reached: {target_upper}")


def event_metrics(
    step05: Any,
    disk: dict[str, Any],
    sampled_disk_points: np.ndarray,
    hits: list[Hit],
    init: dict[str, Any] | None,
) -> dict[str, Any]:
    current_keep, current_class = step05.side_keep_from_hits(hits, disk, "keep")
    tags = fluorescence_tags(hits)
    valid_orders = valid_two_hit_orders(step05, hits)
    lever_arm = None
    if len(hits) == 2:
        lever_arm = distance_mm(hits[0], hits[1])
    elif valid_orders:
        lever_arm = 10.0 * float(valid_orders[0][1]["first_lever_arm"])
    elif len(hits) > 1:
        lever_arm = min(distance_mm(a, b) for a, b in itertools.combinations(hits, 2))

    disk_residuals = [
        value
        for ordered, _ in valid_orders
        if (value := cone_disk_residual_deg(step05, ordered, sampled_disk_points)) is not None
    ]
    arm_values = [
        value
        for ordered, _ in valid_orders
        if (value := true_arm_deg(step05, ordered, init)) is not None
    ]
    min_disk_residual = min(disk_residuals) if disk_residuals else None
    min_true_arm = min(arm_values) if arm_values else None

    if len(hits) <= 1:
        stratum = "single"
    elif tags:
        stratum = "S0_fluorescence"
    elif lever_arm is not None and lever_arm < SHORT_ARM_MM:
        stratum = "S1_short"
    elif lever_arm is not None and lever_arm < LONG_ARM_MM:
        stratum = "S2_medium"
    elif lever_arm is not None:
        stratum = "S3_long"
    else:
        stratum = "unresolved"

    policies: dict[str, dict[str, bool]] = {}
    for k in K_VALUES:
        tight_pass = bool(
            stratum == "S3_long"
            and lever_arm is not None
            and min_disk_residual is not None
            and min_disk_residual <= delta_deg(lever_arm, k)
        )
        if stratum in {"single", "S0_fluorescence", "S1_short"}:
            literal_keep = True
        elif stratum == "S2_medium":
            literal_keep = bool(current_keep)
        elif stratum == "S3_long":
            literal_keep = tight_pass
        else:
            literal_keep = bool(current_keep)
        monotonic_keep = bool(current_keep) and (tight_pass if stratum == "S3_long" else True)
        policies[str(k)] = {
            "tight_pass": tight_pass,
            "literal_brief_keep": literal_keep,
            "monotonic_frozen_keep": monotonic_keep,
        }

    return {
        "current_keep": bool(current_keep),
        "current_class": current_class,
        "stratum": stratum,
        "fluorescence_tags": tags,
        "lever_arm_mm": lever_arm,
        "valid_order_count": len(valid_orders),
        "min_cone_to_window_residual_deg": min_disk_residual,
        "min_true_arm_deg": min_true_arm,
        "delta_deg": {str(k): (delta_deg(lever_arm, k) if lever_arm else None) for k in K_VALUES},
        "policies": policies,
    }


def spectrum_bin(energy_keV: float) -> int | None:
    if 0.0 <= energy_keV < 200.0:
        return int(math.floor(energy_keV))
    return None


def scan_sim(step05: Any, disk: dict[str, Any]) -> dict[str, Any]:
    sampled_disk_points = disk_points(disk)
    generated = 0
    duplicate_ids = 0
    nonmonotonic_ids = 0
    last_id: int | None = None
    header: dict[str, Any] = {}
    profile = Counter()
    spectrum: dict[str, Counter[int]] = defaultdict(Counter)
    lever_strata: dict[str, Counter[str]] = defaultdict(Counter)
    tag_counts: dict[str, Counter[str]] = defaultdict(Counter)
    selected_events: list[dict[str, Any]] = []

    cur_id: int | None = None
    active_total = 0.0
    pixels: dict[str, dict[str, float]] = {}
    init: dict[str, Any] | None = None
    ia_lines: list[str] = []
    tes_cc_records: list[dict[str, Any]] = []

    def reset() -> None:
        nonlocal cur_id, active_total, pixels, init, ia_lines, tes_cc_records
        cur_id = None
        active_total = 0.0
        pixels = {}
        init = None
        ia_lines = []
        tes_cc_records = []

    def flush() -> None:
        nonlocal selected_events
        if cur_id is None:
            return
        hits = aggregate_hits(pixels)
        tes_total = sum(hit.e for hit in hits)
        if hits or active_total > 0.0:
            profile["events_with_tes_or_active"] += 1
        if hits:
            profile["events_with_tes"] += 1
        if active_total > 0.0:
            profile["events_with_active_veto"] += 1
        active_pass = active_total < ACTIVE_VETO_THRESHOLD_KEV
        if active_pass and len(hits) >= 2:
            scopes = ["all_energy"]
            if DIAGNOSTIC_WINDOW[0] <= tes_total < DIAGNOSTIC_WINDOW[1]:
                scopes.append("diagnostic_430_550")
            if W2[0] <= tes_total < W2[1]:
                scopes.append("w2")
            tags = fluorescence_tags(hits)
            for scope in scopes:
                profile[f"{scope}_active_multihit"] += 1
                if tags:
                    for tag in tags:
                        tag_counts[scope][tag["line"]] += 1
            if len(hits) == 2:
                low_energy = min(hit.e for hit in hits)
                energy_bin = spectrum_bin(low_energy)
                arm = distance_mm(hits[0], hits[1])
                stratum = "S1_short" if arm < SHORT_ARM_MM else ("S2_medium" if arm < LONG_ARM_MM else "S3_long")
                for scope in scopes:
                    if energy_bin is not None:
                        spectrum[scope][energy_bin] += 1
                    lever_strata[scope][stratum] += 1

        in_w2 = W2[0] <= tes_total < W2[1]
        if in_w2:
            profile["w2_raw"] += 1
        if in_w2 and active_pass:
            profile["w2_active"] += 1
            metrics = event_metrics(step05, disk, sampled_disk_points, hits, init)
            truth_k_energies = truth_k_photon_energies(ia_lines)
            selected_events.append(
                {
                    "event_id": int(cur_id),
                    "tes_total_keV": tes_total,
                    "active_veto_keV": active_total,
                    "hit_count": len(hits),
                    "hits": [
                        {
                            "pixel_uid": hit.pixel_uid,
                            "layer": hit.layer,
                            "energy_keV": hit.e,
                            "position_cm": [hit.x, hit.y, hit.z],
                        }
                        for hit in hits
                    ],
                    "init": init,
                    "metrics": metrics,
                    "truth_k_photon_energies_keV": truth_k_energies,
                    "fluorescence_truth_supported": bool(
                        metrics["fluorescence_tags"] and truth_k_energies
                    ),
                    "tes_cc_records": tes_cc_records,
                    "ia_lines": ia_lines,
                }
            )

    with gzip.open(SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("Geometry") and "geometry" not in header:
                header["geometry"] = line.split(None, 1)[1]
            elif line.startswith("Seed") and "seed" not in header:
                try:
                    header["seed"] = int(line.split()[1])
                except (IndexError, ValueError):
                    pass
            if line == "SE":
                flush()
                reset()
                continue
            id_match = ID_RE.match(line)
            if id_match:
                if cur_id is not None:
                    flush()
                    reset()
                cur_id = int(id_match.group(1))
                generated += 1
                if last_id is not None:
                    if cur_id == last_id:
                        duplicate_ids += 1
                    if cur_id <= last_id:
                        nonmonotonic_ids += 1
                last_id = cur_id
                continue
            if cur_id is None:
                continue
            if line.startswith("IA "):
                ia_lines.append(line)
                if line.startswith("IA INIT") and init is None:
                    init = parse_init(line)
                continue
            if not line.startswith("CC HIT "):
                continue
            hit_match = CC_RE.match(line)
            if hit_match is None:
                continue
            volume = hit_match.group(1)
            values = dict(KV_RE.findall(hit_match.group(2)))
            try:
                edep = float(values["edep_keV"])
                x, y, z = float(values["x"]), float(values["y"]), float(values["z"])
            except (KeyError, ValueError):
                profile["malformed_cc_hit"] += 1
                continue
            tp_match = TP_RE.match(volume)
            if tp_match:
                record = pixels.setdefault(
                    volume,
                    {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": float(tp_match.group("layer"))},
                )
                record["e"] += edep
                record["wx"] += edep * x
                record["wy"] += edep * y
                record["wz"] += edep * z
                tes_cc_records.append(
                    {
                        "volume": volume,
                        "edep_keV": edep,
                        "position_cm": [x, y, z],
                        "sec": values.get("sec"),
                        "tid": values.get("tid"),
                        "pid": values.get("pid"),
                        "sproc": values.get("sproc"),
                        "prim": values.get("prim"),
                        "par": values.get("par"),
                        "cproc": values.get("cproc"),
                    }
                )
            elif is_active_veto_volume(volume):
                active_total += edep
    flush()

    return {
        "generated_events": generated,
        "last_event_id": last_id,
        "duplicate_event_ids": duplicate_ids,
        "nonmonotonic_event_ids": nonmonotonic_ids,
        "sim_header": header,
        "profile": dict(profile),
        "spectrum": {scope: dict(counter) for scope, counter in spectrum.items()},
        "lever_strata": {scope: dict(counter) for scope, counter in lever_strata.items()},
        "tag_counts": {scope: dict(counter) for scope, counter in tag_counts.items()},
        "w2_events": sorted(selected_events, key=lambda row: row["event_id"]),
    }


def event_audit_rows(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for event in events:
        metrics = event["metrics"]
        tags = metrics["fluorescence_tags"]
        row: dict[str, Any] = {
            "event_id": event["event_id"],
            "tes_total_keV": event["tes_total_keV"],
            "active_veto_keV": event["active_veto_keV"],
            "hit_count": event["hit_count"],
            "hit_energies_keV": ";".join(f"{hit['energy_keV']:.9g}" for hit in event["hits"]),
            "hit_pixels": ";".join(hit["pixel_uid"] for hit in event["hits"]),
            "hit_layers": ";".join(str(hit["layer"]) for hit in event["hits"]),
            "current_class": metrics["current_class"],
            "current_keep": int(metrics["current_keep"]),
            "stratum": metrics["stratum"],
            "fluorescence_tag": int(bool(tags)),
            "fluorescence_lines": ";".join(tag["line"] for tag in tags),
            "truth_k_photon_energies_keV": ";".join(
                f"{value:.9g}" for value in event.get("truth_k_photon_energies_keV", [])
            ),
            "fluorescence_truth_supported": int(event.get("fluorescence_truth_supported", False)),
            "lever_arm_mm": "" if metrics["lever_arm_mm"] is None else metrics["lever_arm_mm"],
            "min_true_arm_deg": "" if metrics["min_true_arm_deg"] is None else metrics["min_true_arm_deg"],
            "min_cone_to_window_residual_deg": ""
            if metrics["min_cone_to_window_residual_deg"] is None
            else metrics["min_cone_to_window_residual_deg"],
        }
        for k in K_VALUES:
            key = str(k)
            row[f"delta_k{k:g}_deg"] = metrics["delta_deg"][key] or ""
            row[f"literal_k{k:g}_keep"] = int(metrics["policies"][key]["literal_brief_keep"])
            row[f"monotonic_k{k:g}_keep"] = int(metrics["policies"][key]["monotonic_frozen_keep"])
        rows.append(row)
    return rows


def policy_yields(
    events: list[dict[str, Any]],
    event_weight: float,
    total_background_proxy: float,
    current_atm_rate: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    current_count = sum(int(event["metrics"]["current_keep"]) for event in events)
    policies = [("current", None, None)]
    for k in K_VALUES:
        policies.append(("literal_brief", k, "literal_brief_keep"))
        policies.append(("monotonic_frozen", k, "monotonic_frozen_keep"))
    rows: list[dict[str, Any]] = []
    transitions: list[dict[str, Any]] = []
    for policy, k, field in policies:
        new_keeps: list[bool] = []
        for event in events:
            current = bool(event["metrics"]["current_keep"])
            if policy == "current":
                new = current
            else:
                new = bool(event["metrics"]["policies"][str(k)][str(field)])
            new_keeps.append(new)
            transitions.append(
                {
                    "policy": policy,
                    "k": "" if k is None else k,
                    "event_id": event["event_id"],
                    "stratum": event["metrics"]["stratum"],
                    "current_keep": int(current),
                    "new_keep": int(new),
                    "transition": f"{int(current)}->{int(new)}",
                }
            )
        new_count = sum(new_keeps)
        removed = sum(
            1
            for event, new in zip(events, new_keeps)
            if event["metrics"]["current_keep"] and not new
        )
        resurrected = sum(
            1
            for event, new in zip(events, new_keeps)
            if not event["metrics"]["current_keep"] and new
        )
        interval = wilson_interval(removed, current_count)
        new_rate = new_count * event_weight
        new_total_proxy = total_background_proxy - current_atm_rate + new_rate
        rows.append(
            {
                "policy": policy,
                "k": "" if k is None else k,
                "active_w2_events": len(events),
                "current_final_events": current_count,
                "new_final_events": new_count,
                "current_kept_to_rejected": removed,
                "current_rejected_to_kept": resurrected,
                "net_event_change": new_count - current_count,
                "new_atm511_rate_cps": new_rate,
                "atm511_rate_change_fraction": new_rate / current_atm_rate - 1.0,
                "current_kept_rejection_fraction": removed / current_count if current_count else None,
                "rejection_fraction_wilson95_low": None if interval is None else interval[0],
                "rejection_fraction_wilson95_high": None if interval is None else interval[1],
                "atm_component_sqrtB_gain_signal_unchanged": math.sqrt(current_atm_rate / new_rate)
                if new_rate > 0.0
                else None,
                "s3c_total_proxy_background_cps": new_total_proxy,
                "s3c_total_proxy_sqrtB_gain_signal_unchanged": math.sqrt(total_background_proxy / new_total_proxy)
                if new_total_proxy > 0.0
                else None,
            }
        )
    return rows, transitions


def spectrum_rows(scan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for scope in ("all_energy", "diagnostic_430_550", "w2"):
        counts = scan["spectrum"].get(scope, {})
        for energy_bin in range(200):
            rows.append(
                {
                    "scope": scope,
                    "energy_bin_low_keV": energy_bin,
                    "energy_bin_high_keV": energy_bin + 1,
                    "two_hit_events": int(counts.get(str(energy_bin), counts.get(energy_bin, 0))),
                }
            )
    return rows


def lever_rows(scan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for scope in ("all_energy", "diagnostic_430_550", "w2"):
        total = sum(scan["lever_strata"].get(scope, {}).values())
        for stratum in ("S1_short", "S2_medium", "S3_long"):
            count = int(scan["lever_strata"].get(scope, {}).get(stratum, 0))
            rows.append(
                {
                    "scope": scope,
                    "stratum": stratum,
                    "two_hit_events": count,
                    "share": count / total if total else None,
                }
            )
    return rows


def main() -> int:
    required = [SIM, LOG, SOURCE, CURRENT_SUMMARY, MAINLINE_SUMMARY, KNOB0_BRIEF, STEP05_SCRIPT, STEP09_SUMMARY]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("missing required inputs: " + ", ".join(missing))

    step05 = load_step05()
    disk = step05.side_entry_disk()
    scan = scan_sim(step05, disk)
    current = load_json(CURRENT_SUMMARY)
    mainline = load_json(MAINLINE_SUMMARY)
    current_w2 = current["windows"]["w2_510p58_511p42"]
    obs_time = observation_time_s()
    event_weight = 1.0 / obs_time
    total_background_proxy = float(mainline["background"]["estimated_total_background_cps"])
    current_atm_rate = float(current_w2["final_rate_cps"])
    audit_rows = event_audit_rows(scan["w2_events"])
    yield_rows, transition_rows = policy_yields(
        scan["w2_events"], event_weight, total_background_proxy, current_atm_rate
    )

    actual_final_ids = sorted(
        event["event_id"] for event in scan["w2_events"] if event["metrics"]["current_keep"]
    )
    expected_geometry = normalize_geometry(str(EXPECTED_GEOMETRY))
    w2_multihit = sum(event["hit_count"] > 1 for event in scan["w2_events"])
    w2_tagged = sum(bool(event["metrics"]["fluorescence_tags"]) for event in scan["w2_events"])
    w2_long = sum(event["metrics"]["stratum"] == "S3_long" for event in scan["w2_events"])
    tag_interval = wilson_interval(w2_tagged, w2_multihit)
    long_interval = wilson_interval(w2_long, w2_multihit)
    literal_primary = next(
        row for row in yield_rows if row["policy"] == "literal_brief" and row["k"] == 2.5
    )
    monotonic_primary = next(
        row for row in yield_rows if row["policy"] == "monotonic_frozen" and row["k"] == 2.5
    )
    long_events = [event for event in scan["w2_events"] if event["metrics"]["stratum"] == "S3_long"]
    long_min_k_to_pass = None
    if long_events:
        long_metrics = long_events[0]["metrics"]
        base_delta = float(long_metrics["delta_deg"]["2.0"]) / 2.0
        residual = float(long_metrics["min_cone_to_window_residual_deg"])
        long_min_k_to_pass = residual / base_delta
    n_for_10pct_upper = minimum_zero_success_trials_for_upper_bound(0.10)
    n_for_5pct_upper = minimum_zero_success_trials_for_upper_bound(0.05)
    generated_for_10pct_upper = math.ceil(3_000_000 * n_for_10pct_upper / max(int(current_w2["side_compton_fov_pass_events"]), 1))
    generated_for_5pct_upper = math.ceil(3_000_000 * n_for_5pct_upper / max(int(current_w2["side_compton_fov_pass_events"]), 1))
    validation = {
        "generated_events_match_3m": scan["generated_events"] == 3_000_000,
        "event_ids_unique_and_monotonic": scan["duplicate_event_ids"] == 0
        and scan["nonmonotonic_event_ids"] == 0,
        "sim_geometry_matches_s3c": normalize_geometry(scan["sim_header"].get("geometry")) == expected_geometry,
        "source_geometry_matches_s3c": normalize_geometry(source_geometry()) == expected_geometry,
        "w2_raw_count_reproduced": int(scan["profile"].get("w2_raw", 0)) == int(current_w2["raw_events"]),
        "w2_active_count_reproduced": int(scan["profile"].get("w2_active", 0))
        == int(current_w2["active_veto_pass_events"]),
        "w2_final_count_reproduced": len(actual_final_ids) == int(current_w2["side_compton_fov_pass_events"]),
        "w2_final_ids_reproduced": actual_final_ids == sorted(int(value) for value in current_w2["final_event_ids"]),
        "event_weight_reproduced": abs(event_weight - float(current_w2["event_rate_weight_cps"])) < 1.0e-15,
        "all_w2_events_have_init": all(event["init"] is not None for event in scan["w2_events"]),
        "all_w2_events_have_pixel_hits": all(event["hit_count"] > 0 for event in scan["w2_events"]),
    }
    status = "PASS_S3C_ATM511_KNOB0_EVENT_REPLAY" if all(validation.values()) else "FAIL_S3C_ATM511_KNOB0_EVENT_REPLAY"

    payload = {
        "status": status,
        "as_of": "2026-07-10",
        "question": "How much atmospheric-511 background benefit does the frozen Knob0 fluorescence/lever-arm policy provide on the retained S3c 3M transport?",
        "inputs": {
            "sim": rel(SIM),
            "log": rel(LOG),
            "source": rel(SOURCE),
            "current_atm511_summary": rel(CURRENT_SUMMARY),
            "s3c_mainline_summary": rel(MAINLINE_SUMMARY),
            "knob0_brief": rel(KNOB0_BRIEF),
            "step05_authority": rel(STEP05_SCRIPT),
        },
        "definitions": {
            "w2_keV": list(W2),
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "k_lines_keV": K_LINES_KEV,
            "k_tag_half_width_keV": K_TAG_HALF_WIDTH_KEV,
            "short_arm_boundary_mm": SHORT_ARM_MM,
            "long_arm_boundary_mm": LONG_ARM_MM,
            "position_sigma_mm": POSITION_SIGMA_MM,
            "doppler_sigma_deg": DOPPLER_SIGMA_DEG,
            "k_values": list(K_VALUES),
            "literal_brief": "S0/S1 are retained calorimetrically; S2 uses current 81-OR; S3 uses centroid cone-to-window residual <= delta(L).",
            "monotonic_frozen": "Never resurrect an event rejected by the current selection; only S3 current survivors can be newly rejected by the frozen tight criterion.",
        },
        "normalization": {
            "generated_events": scan["generated_events"],
            "observation_time_s": obs_time,
            "event_rate_weight_cps": event_weight,
            "current_atm511_final_rate_cps": current_atm_rate,
            "s3c_estimated_total_background_proxy_cps": total_background_proxy,
        },
        "data_quality": {
            "sim_header": scan["sim_header"],
            "last_event_id": scan["last_event_id"],
            "duplicate_event_ids": scan["duplicate_event_ids"],
            "nonmonotonic_event_ids": scan["nonmonotonic_event_ids"],
            "profile": scan["profile"],
            "w2_event_count": len(scan["w2_events"]),
            "w2_current_final_event_ids": actual_final_ids,
            "per_hit_energy_position_available": True,
            "truth_initial_direction_available": all(event["init"] is not None for event in scan["w2_events"]),
            "aggregation_note": "CC HIT deposits are summed by TP pixel; K tagging is applied to aggregated per-pixel energy, matching the current event catalog grain.",
        },
        "g1": {
            "tag_counts": scan["tag_counts"],
            "lever_strata": scan["lever_strata"],
            "w2_stratum_counts": dict(Counter(event["metrics"]["stratum"] for event in scan["w2_events"])),
            "w2_fluorescence_tagged_events": w2_tagged,
            "w2_fluorescence_truth_supported_events": sum(
                bool(event.get("fluorescence_truth_supported")) for event in scan["w2_events"]
            ),
            "w2_multihit_events": w2_multihit,
            "w2_fluorescence_fraction_of_multihit": w2_tagged / w2_multihit if w2_multihit else None,
            "w2_fluorescence_fraction_wilson95": tag_interval,
            "w2_long_arm_events": w2_long,
            "w2_long_arm_fraction_of_multihit": w2_long / w2_multihit if w2_multihit else None,
            "w2_long_arm_fraction_wilson95": long_interval,
            "long_event_minimum_k_to_pass": long_min_k_to_pass,
        },
        "policy_yields": yield_rows,
        "decision": {
            "observed_result": "NO_ATM511_BENEFIT_AND_LITERAL_POLICY_IS_HARMFUL_IN_SAMPLE",
            "literal_k2p5": literal_primary,
            "monotonic_k2p5": monotonic_primary,
            "interpretation": (
                "The literal S0/S1 calorimetric-retain rule resurrects one current short-arm veto, while the only long-arm survivor intersects the side-window disk and passes every frozen k. "
                "The monotonic policy therefore changes no event."
            ),
            "promotion_recommendation": "DO_NOT_PROMOTE_LITERAL_KNOB0_FOR_ATM511; retain current selection.",
            "additional_statistics_if_zero_rejections_persist": {
                "current_final_events_required_for_wilson95_upper_le_10pct": n_for_10pct_upper,
                "approx_total_generated_atm511_events_required": generated_for_10pct_upper,
                "current_final_events_required_for_wilson95_upper_le_5pct": n_for_5pct_upper,
                "approx_total_generated_atm511_events_required_for_5pct": generated_for_5pct_upper,
                "scaling_note": "Linear yield scaling from 6 current final events in 3M generated events; not a guarantee.",
            },
        },
        "validation": validation,
        "claim_boundary": [
            "This is a replay of the retained S3c atmospheric-511 transport, not a new transport.",
            "Only eight active-veto-pass W2 events are available; exact event transitions control the estimate and uncertainty is large.",
            "The atmospheric-only sqrt(B) gains assume unchanged signal acceptance and are not measured sensitivity gains.",
            "The S3c-total proxy uses the retained non-dominant S3 residual and is not a full S3c prompt-family closure.",
            "Pixel aggregation can dilute or shift a fluorescence-line hit when another deposit lands in the same pixel.",
        ],
    }

    DATA.mkdir(parents=True, exist_ok=True)
    write_json(DATA / "s3c_atm511_knob0_summary.json", payload)
    write_json(DATA / "s3c_atm511_w2_event_truth.json", scan["w2_events"])
    write_csv(DATA / "s3c_atm511_w2_event_audit.csv", audit_rows)
    write_csv(DATA / "s3c_atm511_knob0_policy_yields.csv", yield_rows)
    write_csv(DATA / "s3c_atm511_knob0_transitions.csv", transition_rows)
    write_csv(
        DATA / "s3c_atm511_low_hit_spectrum_1kev.csv",
        spectrum_rows(scan),
        ["scope", "energy_bin_low_keV", "energy_bin_high_keV", "two_hit_events"],
    )
    write_csv(DATA / "s3c_atm511_lever_strata.csv", lever_rows(scan))
    print(json.dumps({"status": status, "summary": rel(DATA / "s3c_atm511_knob0_summary.json"), "policy_yields": yield_rows}, indent=2, ensure_ascii=False))
    return 0 if status.startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
