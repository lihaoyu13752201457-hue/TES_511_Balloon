#!/usr/bin/env python3
"""Build the retained S3c background, activation, and mass trade-space tables.

The script intentionally reads only S3c mainline products plus compact retained
conclusion snapshots.  It does not require the legacy S3/S3a/S3b simulations.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
DATA = WORK / "data"

DOMINANT = (
    ROOT
    / "engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709"
    / "dominant_background_summary.json"
)
ATM_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709"
    / "s3c_atm511_sidecar_3m_summary.json"
)
DELAYED = (
    ROOT
    / "engineering/geometry_optimization_20260704/38_s3c_neutron_delayed_chain_m50000_clean_20260710"
    / "delayed_source/delayed_source_exactpos_summary.json"
)
WEIGHTED_TABLE = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "step02_delay_exactpos_s3c_bgo_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710"
    / "exactpos_weighted_rpip_table_m50000_s260613.csv"
)
ACTIVATION_INVENTORY = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "step02_decay_source_s3c_bgo_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710"
    / "activation_inventory_day15.csv"
)
GEOMETRY_MANIFEST = (
    ROOT
    / "engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709"
    / "geoopt_s3c_geometry_manifest.json"
)
HISTORICAL = WORK / "retained_conclusions/historical_design_points.json"
DECK_EVIDENCE = (
    ROOT
    / "engineering/geometry_optimization_20260704/39_mass511_to_s3_html_presentation_20260710"
    / "deck_evidence_summary.json"
)

W2_NAME = "w2_510p58_511p42"
ID_RE = re.compile(r"^ID\s+(\d+)")

# S3c inherits the S2b outer plastic envelope in instrument-local coordinates.
OUTER_RADIUS_CM = 30.0
OUTER_ZMIN_CM = -27.5
OUTER_ZMAX_CM = 49.0
WINDOW_Z0_CM = -5.2
WINDOW_HALF_Y_CM = 1.898
WINDOW_HALF_Z_CM = 1.898


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path | str) -> str:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_ia_init(line: str) -> dict[str, float] | None:
    try:
        fields = [part.strip() for part in line.split("IA INIT", 1)[1].split(";")]
        return {
            "init_x_cm": float(fields[4]),
            "init_y_cm": float(fields[5]),
            "init_z_cm": float(fields[6]),
            "dir_x": float(fields[16]),
            "dir_y": float(fields[17]),
            "dir_z": float(fields[18]),
            "init_energy_keV": float(fields[-1]),
        }
    except (IndexError, ValueError):
        return None


def scan_target_inits(path: Path, ids: set[int]) -> dict[int, dict[str, float]]:
    remaining = set(ids)
    found: dict[int, dict[str, float]] = {}
    current_id: int | None = None
    interested = False
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE" and not remaining:
                break
            match = ID_RE.match(line)
            if match:
                current_id = int(match.group(1))
                interested = current_id in remaining
                continue
            if interested and current_id is not None and line.startswith("IA INIT"):
                parsed = parse_ia_init(line)
                if parsed is not None:
                    found[current_id] = parsed
                    remaining.discard(current_id)
                    interested = False
    if remaining:
        raise RuntimeError(f"missing selected INIT records in {rel(path)}: {sorted(remaining)}")
    return found


def rotate_y(values: tuple[float, float, float], angle_deg: float) -> tuple[float, float, float]:
    x, y, z = values
    angle = math.radians(angle_deg)
    c = math.cos(angle)
    s = math.sin(angle)
    return c * x + s * z, y, -s * x + c * z


def classify_entry(init: dict[str, float]) -> dict[str, Any]:
    p = rotate_y((init["init_x_cm"], init["init_y_cm"], init["init_z_cm"]), -45.0)
    d = rotate_y((init["dir_x"], init["dir_y"], init["dir_z"]), -45.0)
    norm = math.sqrt(sum(value * value for value in d))
    if norm <= 0:
        raise RuntimeError("zero IA INIT direction")
    d = tuple(value / norm for value in d)
    radius = math.hypot(p[0], p[1])
    if radius <= OUTER_RADIUS_CM + 1e-7 and OUTER_ZMIN_CM - 1e-7 <= p[2] <= OUTER_ZMAX_CM + 1e-7:
        return {"entry_surface": "internal", "entry_region": "inner_instrument"}

    candidates: list[tuple[float, str, tuple[float, float, float]]] = []
    a = d[0] ** 2 + d[1] ** 2
    b = 2.0 * (p[0] * d[0] + p[1] * d[1])
    c0 = p[0] ** 2 + p[1] ** 2 - OUTER_RADIUS_CM**2
    if abs(a) > 1e-15:
        disc = b * b - 4.0 * a * c0
        if disc >= 0:
            root = math.sqrt(disc)
            for t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
                if t <= 0:
                    continue
                q = (p[0] + t * d[0], p[1] + t * d[1], p[2] + t * d[2])
                if OUTER_ZMIN_CM - 1e-6 <= q[2] <= OUTER_ZMAX_CM + 1e-6:
                    candidates.append((t, "side", q))
    if abs(d[2]) > 1e-15:
        for zcap, surface in ((OUTER_ZMIN_CM, "bottom"), (OUTER_ZMAX_CM, "top")):
            t = (zcap - p[2]) / d[2]
            if t <= 0:
                continue
            q = (p[0] + t * d[0], p[1] + t * d[1], p[2] + t * d[2])
            if q[0] ** 2 + q[1] ** 2 <= OUTER_RADIUS_CM**2 + 1e-6:
                candidates.append((t, surface, q))
    if not candidates:
        return {"entry_surface": "miss", "entry_region": "miss_outer_envelope"}

    _, surface, q = min(candidates, key=lambda item: item[0])
    phi = math.degrees(math.atan2(q[1], q[0])) % 360.0
    is_window = (
        surface == "side"
        and q[0] < 0
        and abs(q[1]) <= WINDOW_HALF_Y_CM
        and abs(q[2] - WINDOW_Z0_CM) <= WINDOW_HALF_Z_CM
    )
    if is_window:
        region = "side_window_aperture"
    elif surface == "side":
        region = f"side_phi_sector_{int(math.floor((phi + 22.5) / 45.0)) % 8}"
    else:
        region = surface
    return {
        "entry_surface": surface,
        "entry_region": region,
        "entry_phi_deg_local": phi,
        "entry_local_x_cm": q[0],
        "entry_local_y_cm": q[1],
        "entry_local_z_cm": q[2],
    }


def selected_event_rows(dominant: dict[str, Any], atm: dict[str, Any]) -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    by_path: dict[Path, set[int]] = defaultdict(set)
    for component in ("eplus", "n"):
        examples = dominant["prompt_cases"][component]["summary"]["selected_examples"]
        for example in examples:
            path = ROOT / example["source_file"]
            event_id = int(example["local_id"])
            pending.append(
                {
                    "component": component,
                    "source_file": rel(path),
                    "local_id": event_id,
                    "rate_cps": float(example["rate_s-1"]),
                    "tes_total_keV": float(example["tes_total_keV"]),
                }
            )
            by_path[path].add(event_id)

    window = atm["windows"][W2_NAME]
    atm_path = ROOT / atm["inputs"]["sim"]
    for event_id, energy in zip(window["final_event_ids"], window["final_energies_keV"]):
        pending.append(
            {
                "component": "atm511",
                "source_file": rel(atm_path),
                "local_id": int(event_id),
                "rate_cps": float(window["event_rate_weight_cps"]),
                "tes_total_keV": float(energy),
            }
        )
        by_path[atm_path].add(int(event_id))

    metadata: dict[tuple[str, int], dict[str, float]] = {}
    for path, ids in sorted(by_path.items(), key=lambda item: str(item[0])):
        for event_id, init in scan_target_inits(path, ids).items():
            metadata[(rel(path), event_id)] = init

    rows = []
    for row in pending:
        init = metadata[(row["source_file"], row["local_id"])]
        rows.append({**row, **init, **classify_entry(init)})
    return rows


def volume_class(name: str) -> str:
    upper = name.upper()
    if upper.startswith("OUTER_W_S3C"):
        return "S3c W mechanical shell"
    if upper.startswith("OUTER_AL_S3C"):
        return "S3c Al mechanical shell"
    if upper.startswith("BGO_S3C"):
        return "S3c BGO active shell"
    if upper.startswith("ACTIVESHIELD_S3C"):
        return "S3c Kapton wrapper"
    if name == "Window":
        return "Window package"
    if upper.startswith("NF2_OUTERSUPPORT"):
        return "NF2 support"
    if "PASSIVE_W" in upper or "COLLIMATOR" in upper or "W_MULT" in upper:
        return "Retained passive W/collimator"
    if upper.startswith(("COLDPLATE", "DR_", "XS400", "CU_")):
        return "Cryostat and cold structure"
    return "Other"


def activation_tables(delayed: dict[str, Any], geometry: dict[str, Any]) -> dict[str, Any]:
    nuclide_by_za: dict[str, str] = {}
    with ACTIVATION_INVENTORY.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            nuclide_by_za.setdefault(str(row["ZA"]), str(row["nuclide"]))

    by_volume: dict[str, float] = defaultdict(float)
    by_nuclide: dict[tuple[str, str], float] = defaultdict(float)
    by_class: dict[str, float] = defaultdict(float)
    with WEIGHTED_TABLE.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            weight = float(row["sample_weight"])
            name = str(row["VN"])
            za = str(row["ZA"])
            nuclide = nuclide_by_za.get(za, f"ZA-{za}")
            by_volume[name] += weight
            by_nuclide[(nuclide, za)] += weight
            by_class[volume_class(name)] += weight

    total = sum(by_volume.values())
    expected = float(delayed["fixed_total_activity_Bq"])
    if not math.isclose(total, expected, rel_tol=0.0, abs_tol=2e-6):
        raise RuntimeError(f"activation sum mismatch: sampled={total} expected={expected}")

    volume_meta = {row["name"]: row for row in geometry["new_volumes"]}
    top_volume_rows = []
    for name, activity in sorted(by_volume.items(), key=lambda item: item[1], reverse=True):
        meta = volume_meta.get(name, {})
        mass = meta.get("mass_kg_pre_relief")
        top_volume_rows.append(
            {
                "volume": name,
                "volume_class": volume_class(name),
                "material": meta.get("material", "mixed/retained"),
                "activity_bq": activity,
                "fraction_of_neutron_only_activity": activity / total,
                "mass_kg_pre_relief_if_s3c_replacement": "" if mass is None else mass,
                "activity_bq_per_kg_if_available": "" if not mass else activity / float(mass),
            }
        )

    class_rows = [
        {
            "volume_class": name,
            "activity_bq": activity,
            "fraction_of_neutron_only_activity": activity / total,
        }
        for name, activity in sorted(by_class.items(), key=lambda item: item[1], reverse=True)
    ]
    nuclide_rows = [
        {
            "nuclide": nuclide,
            "ZA": za,
            "activity_bq": activity,
            "fraction_of_neutron_only_activity": activity / total,
        }
        for (nuclide, za), activity in sorted(by_nuclide.items(), key=lambda item: item[1], reverse=True)
    ]

    write_csv(
        DATA / "s3c_neutron_delayed_top_volumes.csv",
        list(top_volume_rows[0].keys()),
        top_volume_rows,
    )
    write_csv(DATA / "s3c_neutron_delayed_by_volume_class.csv", list(class_rows[0].keys()), class_rows)
    write_csv(DATA / "s3c_neutron_delayed_by_nuclide.csv", list(nuclide_rows[0].keys()), nuclide_rows)
    return {
        "total_activity_bq": total,
        "top_volumes": top_volume_rows[:12],
        "volume_classes": class_rows,
        "top_nuclides": nuclide_rows[:12],
    }


def bgo_uniform_mass(geometry: dict[str, Any], thickness_cm: float) -> float:
    volumes = {row["name"]: row for row in geometry["new_volumes"]}
    side = float(volumes["BGO_S3C_FullWrap_SideShell_WindowCut_40mm"]["mass_kg_pre_relief"])
    bottom = float(volumes["BGO_S3C_FullWrap_BottomCap_40mm"]["mass_kg_pre_relief"])
    top = float(volumes["BGO_S3C_FullWrap_TopAnnulus_40mm"]["mass_kg_pre_relief"])
    rin = 21.2
    opening = 20.9
    current_t = 4.0
    current_rout = rin + current_t
    rout = rin + thickness_cm
    side_ratio = (rout**2 - rin**2) / (current_rout**2 - rin**2)
    bottom_ratio = (rout**2 * thickness_cm) / (current_rout**2 * current_t)
    top_ratio = ((rout**2 - opening**2) * thickness_cm) / (
        (current_rout**2 - opening**2) * current_t
    )
    return side * side_ratio + bottom * bottom_ratio + top * top_ratio


def candidate_tables(geometry: dict[str, Any], historical: dict[str, Any]) -> list[dict[str, Any]]:
    current = historical["design_points"]["s3c_current"]
    lw1 = historical["design_points"]["s3a_rehomed_as_s3c_lw1"]
    current_mass = float(current["mass_kg_pre_relief"]["total"])
    bgo40 = float(current["mass_kg_pre_relief"]["scintillator"])
    kapton = float(current["mass_kg_pre_relief"]["kapton"])
    al3 = float(current["mass_kg_pre_relief"]["aluminium"])
    al8 = float(lw1["mass_kg_pre_relief"]["aluminium"])
    al5_approx = al8 * 5.0 / 8.0

    new_volumes = {row["name"]: row for row in geometry["new_volumes"]}
    side40 = float(new_volumes["BGO_S3C_FullWrap_SideShell_WindowCut_40mm"]["mass_kg_pre_relief"])
    bottom40 = float(new_volumes["BGO_S3C_FullWrap_BottomCap_40mm"]["mass_kg_pre_relief"])
    top40 = float(new_volumes["BGO_S3C_FullWrap_TopAnnulus_40mm"]["mass_kg_pre_relief"])

    candidates = [
        {
            "variant": "S3c-C0 current",
            "bgo_profile_mm": "side40/bottom40/top40",
            "mechanical_shell": "W2 + Al3",
            "mass_kg_pre_relief": current_mass,
            "mass_saved_kg_vs_current": 0.0,
            "mass_reduction_fraction": 0.0,
            "dominant_subset_w2_cps": current["dominant_subset_w2_cps"],
            "estimated_f3_20d_ph_cm2_s": current["estimated_f3_20d_ph_cm2_s"],
            "neutron_only_delayed_activity_bq": current["neutron_only_delayed_activity_bq"],
            "evidence_level": "measured screening + neutron-only delayed transport",
            "decision": "reference",
        },
        {
            "variant": "S3c-LW1 retained",
            "bgo_profile_mm": "side40/bottom40/top40",
            "mechanical_shell": "Al8, no W",
            "mass_kg_pre_relief": lw1["mass_kg_pre_relief"]["total"],
            "mass_saved_kg_vs_current": current_mass - float(lw1["mass_kg_pre_relief"]["total"]),
            "mass_reduction_fraction": 1.0 - float(lw1["mass_kg_pre_relief"]["total"]) / current_mass,
            "dominant_subset_w2_cps": lw1["dominant_subset_w2_cps"],
            "estimated_f3_20d_ph_cm2_s": lw1["estimated_f3_20d_ph_cm2_s"],
            "neutron_only_delayed_activity_bq": lw1["neutron_only_delayed_activity_bq"],
            "evidence_level": "historical equal-stat screen + neutron-only delayed transport",
            "decision": "first promotion candidate",
        },
        {
            "variant": "S3c-LW2",
            "bgo_profile_mm": "side40/bottom40/top40",
            "mechanical_shell": "Al5, no W",
            "mass_kg_pre_relief": bgo40 + kapton + al5_approx,
            "mass_saved_kg_vs_current": current_mass - (bgo40 + kapton + al5_approx),
            "mass_reduction_fraction": 1.0 - (bgo40 + kapton + al5_approx) / current_mass,
            "dominant_subset_w2_cps": "",
            "estimated_f3_20d_ph_cm2_s": "",
            "neutron_only_delayed_activity_bq": "",
            "evidence_level": "mass interpolation only; transport and structure untested",
            "decision": "second screening candidate",
        },
        {
            "variant": "S3c-LW3",
            "bgo_profile_mm": "side40/bottom40/top40",
            "mechanical_shell": "Al3, no W",
            "mass_kg_pre_relief": bgo40 + kapton + al3,
            "mass_saved_kg_vs_current": current_mass - (bgo40 + kapton + al3),
            "mass_reduction_fraction": 1.0 - (bgo40 + kapton + al3) / current_mass,
            "dominant_subset_w2_cps": "",
            "estimated_f3_20d_ph_cm2_s": "",
            "neutron_only_delayed_activity_bq": "",
            "evidence_level": "mass bookkeeping only; transport and structure untested",
            "decision": "mechanical lower-bound candidate",
        },
        {
            "variant": "S3c-LW4 graded",
            "bgo_profile_mm": "side40/bottom30/top10",
            "mechanical_shell": "Al5, no W",
            "mass_kg_pre_relief": side40 + 0.75 * bottom40 + 0.25 * top40 + kapton + al5_approx,
            "mass_saved_kg_vs_current": current_mass
            - (side40 + 0.75 * bottom40 + 0.25 * top40 + kapton + al5_approx),
            "mass_reduction_fraction": 1.0
            - (side40 + 0.75 * bottom40 + 0.25 * top40 + kapton + al5_approx) / current_mass,
            "dominant_subset_w2_cps": "",
            "estimated_f3_20d_ph_cm2_s": "",
            "neutron_only_delayed_activity_bq": "",
            "evidence_level": "directional hypothesis; no S3c transport",
            "decision": "test only after LW1/LW2",
        },
        {
            "variant": "S3c-LW5 uniform30",
            "bgo_profile_mm": "side30/bottom30/top30",
            "mechanical_shell": "Al5, no W",
            "mass_kg_pre_relief": bgo_uniform_mass(geometry, 3.0) + kapton + al5_approx,
            "mass_saved_kg_vs_current": current_mass
            - (bgo_uniform_mass(geometry, 3.0) + kapton + al5_approx),
            "mass_reduction_fraction": 1.0
            - (bgo_uniform_mass(geometry, 3.0) + kapton + al5_approx) / current_mass,
            "dominant_subset_w2_cps": "",
            "estimated_f3_20d_ph_cm2_s": "",
            "neutron_only_delayed_activity_bq": "",
            "evidence_level": "pre-relief geometric mass model only",
            "decision": "aggressive exploratory candidate",
        },
        {
            "variant": "S3c-LW6 uniform20",
            "bgo_profile_mm": "side20/bottom20/top20",
            "mechanical_shell": "Al5, no W",
            "mass_kg_pre_relief": bgo_uniform_mass(geometry, 2.0) + kapton + al5_approx,
            "mass_saved_kg_vs_current": current_mass
            - (bgo_uniform_mass(geometry, 2.0) + kapton + al5_approx),
            "mass_reduction_fraction": 1.0
            - (bgo_uniform_mass(geometry, 2.0) + kapton + al5_approx) / current_mass,
            "dominant_subset_w2_cps": "",
            "estimated_f3_20d_ph_cm2_s": "",
            "neutron_only_delayed_activity_bq": "",
            "evidence_level": "pre-relief geometric mass model only",
            "decision": "do not promote without staged veto-efficiency test",
        },
    ]
    for row in candidates:
        row["mass_kg_pre_relief"] = float(row["mass_kg_pre_relief"])
        row["mass_saved_kg_vs_current"] = float(row["mass_saved_kg_vs_current"])
        row["mass_reduction_fraction"] = float(row["mass_reduction_fraction"])
    write_csv(DATA / "s3c_lightweight_candidates.csv", list(candidates[0].keys()), candidates)
    return candidates


def run_matrix() -> list[dict[str, Any]]:
    rows = [
        {
            "priority": 1,
            "variant": "S3c-LW1 retained",
            "phase": "consolidation",
            "test": "rebuild under S3c naming + cosima overlap",
            "statistics": "geometry only",
            "promotion_gate": "exact geometry parity with retained BGO40/Al8 design point",
        },
        {
            "priority": 2,
            "variant": "S3c-C0/LW1/LW2/LW3",
            "phase": "fast screen",
            "test": "prompt eplus+n and matched 4pi atm511",
            "statistics": "same-stat screen; preserve 16 prompt jobs and 3M atm511",
            "promotion_gate": "dominant W2 subset <= 0.0052 cps with correct geometry headers",
        },
        {
            "priority": 3,
            "variant": "screen survivors",
            "phase": "signal guardrail",
            "test": "focused f10m A1 signal response",
            "statistics": "matched retained bridge statistics",
            "promotion_gate": "final W2 signal acceptance loss <= 2% versus S3c-C0",
        },
        {
            "priority": 4,
            "variant": "best two",
            "phase": "delayed guardrail",
            "test": "clean neutron-only delayed chain",
            "statistics": "8 files, TT division 8, M=50000, SE=ID=1000000",
            "promotion_gate": "NUBASE/TT/sampling PASS and activity <= 57.8243 Bq",
        },
        {
            "priority": 5,
            "variant": "winner",
            "phase": "full closure",
            "test": "all prompt families + delayed Step05 + Step06-Step08",
            "statistics": "publication-matched",
            "promotion_gate": "validated S3c-native 20d F3 and structural mass audit",
        },
    ]
    write_csv(DATA / "s3c_lightweight_run_matrix.csv", list(rows[0].keys()), rows)
    return rows


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    dominant = load_json(DOMINANT)
    atm = load_json(ATM_SUMMARY)
    delayed = load_json(DELAYED)
    geometry = load_json(GEOMETRY_MANIFEST)
    historical = load_json(HISTORICAL)
    deck = load_json(DECK_EVIDENCE)

    final_rows = [row for row in dominant["rows"] if row["stage"] == "side_compton_fov_pass"]
    final_by_component = {row["component"]: row for row in final_rows}
    dominant_sum = sum(float(row["s3c_rate_cps"]) for row in final_rows)
    s3_screen = deck["s3abc_screening"]["components_cps"]
    s3_subset = sum(float(s3_screen[key][0]) for key in ("eplus", "n", "atm511"))
    residual = float(deck["matched_total_background_cps"]) - s3_subset
    estimated_total = dominant_sum + residual

    background_rows = []
    for component in ("eplus", "n", "atm511"):
        row = final_by_component[component]
        events = int(row["s3c_events"])
        rate = float(row["s3c_rate_cps"])
        background_rows.append(
            {
                "component": component,
                "scope": "measured S3c final W2 screen",
                "events": events,
                "rate_cps": rate,
                "share_of_measured_dominant_subset": rate / dominant_sum,
                "share_of_estimated_total_background": rate / estimated_total,
                "counting_relative_1sigma": 1.0 / math.sqrt(events),
            }
        )
    background_rows.append(
        {
            "component": "retained_non_dominant_residual",
            "scope": "held at retained S3 value; not measured in S3c",
            "events": "",
            "rate_cps": residual,
            "share_of_measured_dominant_subset": "",
            "share_of_estimated_total_background": residual / estimated_total,
            "counting_relative_1sigma": "",
        }
    )
    write_csv(DATA / "s3c_w2_background_distribution.csv", list(background_rows[0].keys()), background_rows)

    event_rows = selected_event_rows(dominant, atm)
    write_csv(DATA / "s3c_final_event_entry_rows.csv", list(event_rows[0].keys()), event_rows)
    entry_accumulator: dict[tuple[str, str], dict[str, float]] = defaultdict(lambda: {"events": 0.0, "rate": 0.0})
    for row in event_rows:
        key = (str(row["component"]), str(row["entry_surface"]))
        entry_accumulator[key]["events"] += 1.0
        entry_accumulator[key]["rate"] += float(row["rate_cps"])
    entry_rows = [
        {
            "component": component,
            "entry_surface": surface,
            "events": int(values["events"]),
            "rate_cps": values["rate"],
            "share_of_selected_component_rate": values["rate"]
            / sum(float(row["rate_cps"]) for row in event_rows if row["component"] == component),
        }
        for (component, surface), values in sorted(entry_accumulator.items())
    ]
    write_csv(DATA / "s3c_final_event_entry_distribution.csv", list(entry_rows[0].keys()), entry_rows)

    activation = activation_tables(delayed, geometry)
    candidates = candidate_tables(geometry, historical)
    matrix = run_matrix()

    current = candidates[0]
    lw1 = candidates[1]
    summary = {
        "status": "PASS_S3C_MAINLINE_LIGHTWEIGHT_ANALYSIS",
        "as_of": "2026-07-10",
        "decision": "Promote S3c as a design family and make the retained BGO40/Al8 no-W point S3c-LW1, the first lightweight promotion candidate.",
        "background": {
            "measured_dominant_subset_cps": dominant_sum,
            "retained_s3_non_dominant_residual_cps": residual,
            "estimated_total_background_cps": estimated_total,
            "component_rows": background_rows,
            "selected_event_entry_rows": entry_rows,
            "selected_event_count": len(event_rows),
        },
        "activation": activation,
        "mass_trade": {
            "current_mass_kg_pre_relief": current["mass_kg_pre_relief"],
            "lw1_mass_kg_pre_relief": lw1["mass_kg_pre_relief"],
            "lw1_mass_saved_kg": lw1["mass_saved_kg_vs_current"],
            "lw1_mass_reduction_fraction": lw1["mass_reduction_fraction"],
            "lw1_f3_penalty_fraction_vs_current_estimate": float(lw1["estimated_f3_20d_ph_cm2_s"])
            / float(current["estimated_f3_20d_ph_cm2_s"])
            - 1.0,
            "lw1_neutron_activity_reduction_fraction": 1.0
            - float(lw1["neutron_only_delayed_activity_bq"])
            / float(current["neutron_only_delayed_activity_bq"]),
            "candidates": candidates,
        },
        "run_matrix": matrix,
        "validation": {
            "dominant_status": dominant["status"],
            "delayed_status": delayed["status"],
            "activation_flux_sum_delta_bq": activation["total_activity_bq"]
            - float(delayed["fixed_total_activity_Bq"]),
            "source_geometry_match": dominant["geometry_verification"]["source_cards"]["all_match"],
            "prompt_sim_geometry_match": dominant["geometry_verification"]["prompt_sim_headers"]["all_match"],
            "atm_geometry_match": dominant["geometry_verification"]["atm511"]["all_match"],
        },
        "claim_boundary": [
            "The S3c W2 distribution covers eplus, neutron, atm511, plus a retained S3 residual; it is not a full S3c prompt-family closure.",
            "Only 10 S3c final selected events support the entry-direction table.",
            "Delayed distributions are neutron-only source-side activities, not detector-selected W2 rates.",
            "Candidate masses are pre-relief geometry bookkeeping; Al5 and reduced-BGO candidates require generated geometry and structural review.",
        ],
        "sources": [rel(path) for path in (DOMINANT, ATM_SUMMARY, DELAYED, WEIGHTED_TABLE, GEOMETRY_MANIFEST, HISTORICAL, DECK_EVIDENCE)],
    }
    write_json(DATA / "s3c_mainline_analysis_summary.json", summary)
    print(json.dumps({"status": summary["status"], "output": rel(DATA / "s3c_mainline_analysis_summary.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
