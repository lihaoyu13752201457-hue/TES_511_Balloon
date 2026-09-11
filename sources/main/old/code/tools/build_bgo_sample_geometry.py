#!/usr/bin/env python3
"""Build the current-v3p5 BGO equal-attenuation sample geometry.

This creates a repository-local ``Bgo_sample`` package without changing the
current CsI geometry authority.  The sample keeps the v3p5 detector head and
inner clearances, replaces only the active scintillator with BGO, recomputes
BGO thicknesses to match the current CsI slab total-interaction efficiency, and
moves the active-shield package/outer shell to follow the new BGO envelope.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REF_BOUNDS = ROOT / "geo_refer" / "DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json"
REF_BUILDER = ROOT / "code" / "geometry" / "build_demo2_dr_v3p5_centerfinger_megalib.py"
OUT = ROOT / "Bgo_sample"

GEOM_NAME = "Bgo_sample"
GEO = OUT / f"{GEOM_NAME}.geo"
DET = OUT / f"{GEOM_NAME}.det"
SETUP = OUT / f"{GEOM_NAME}.geo.setup"
INTRO = OUT / f"Intro_{GEOM_NAME}.geo"
MATERIALS = OUT / "Materials_Bgo_sample.geo"
BOUNDS = OUT / "bounds.json"
MASS_JSON = OUT / "mass_budget.json"
MASS_CSV = OUT / "mass_budget.csv"
SUMMARY_JSON = OUT / "bgo_sample_summary.json"
SUMMARY_MD = OUT / "README.md"
ATTEN_JSON = OUT / "attenuation_verification.json"
ATTEN_CSV = OUT / "attenuation_verification.csv"
OVERLAP_SOURCE = OUT / "overlap_check.source"
OVERLAP_LOG = OUT / "cosima_overlap.log"

MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
COSIMA = MEGALIB / "bin" / "cosima"
MEGALIB_MATERIALS = MEGALIB / "resource/examples/geomega/materials/Materials.geo"
CSI_XSECTION = MEGALIB / "resource/examples/geomega/materials/Xsection.Total.CsI.rsp"
BGO_XSECTION = MEGALIB / "resource/examples/geomega/materials/Xsection.Total.BGO.rsp"

BGO_VETO_THRESHOLD_KEV = 70.0
RELATIVE_TOLERANCE = 0.10
OPTIMIZE_STEP_CM = 0.001
OPTIMIZE_MARGIN_FACTOR = 3.0
ENERGIES_KEV = [
    (511.0, "annihilation_line"),
    (662.0, "Cs137_reference"),
    (1173.2, "Co60_line"),
    (1332.5, "Co60_line"),
    (1460.8, "K40_background_line"),
    (1764.5, "Bi214_background_line"),
    (2614.5, "Tl208_background_line"),
]
PARTS = ("side", "bottom", "top")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fmt(value: float) -> str:
    return f"{value:.9g}"


def load_v3p5_builder() -> Any:
    spec = importlib.util.spec_from_file_location("v3p5_builder", REF_BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not import geometry builder: {REF_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.GEOM_NAME = GEOM_NAME
    module.OUT = OUT
    module.GEO = GEO
    module.DET = DET
    module.SETUP = SETUP
    module.INTRO = INTRO
    module.MATERIALS = MATERIALS
    module.VALIDATION = OUT / "geometry_proxy_validation.json"
    module.README = OUT / "geometry_builder_readme.md"
    module.OVERLAP_SOURCE = OVERLAP_SOURCE
    module.OVERLAP_LOG = OVERLAP_LOG
    return module


def read_rsp(path: Path) -> dict[str, Any]:
    points: list[tuple[float, float]] = []
    source_note = ""
    x_note = ""
    y_note = ""
    name = ""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped.startswith("# Derived from"):
            source_note = stripped.lstrip("#").strip()
        elif stripped.startswith("# X:"):
            x_note = stripped.lstrip("#").strip()
        elif stripped.startswith("# Y:"):
            y_note = stripped.lstrip("#").strip()
        elif stripped.startswith("NM "):
            name = stripped[3:]
        cols = stripped.split()
        if len(cols) == 3 and cols[0] == "R1":
            energy = float(cols[1])
            mu = float(cols[2])
            if energy > 0.0 and mu > 0.0:
                points.append((energy, mu))
    if len(points) < 2:
        raise RuntimeError(f"No usable R1 rows in {path}")
    points.sort()
    return {
        "path": str(path),
        "name": name,
        "source_note": source_note,
        "x_note": x_note,
        "y_note": y_note,
        "energy_min_keV": points[0][0],
        "energy_max_keV": points[-1][0],
        "points": points,
    }


def loglog_interp(points: list[tuple[float, float]], energy_kev: float) -> float:
    if not points[0][0] <= energy_kev <= points[-1][0]:
        raise RuntimeError(f"{energy_kev} keV outside xsection range {points[0][0]}-{points[-1][0]}")
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= energy_kev <= x1:
            if energy_kev == x0:
                return y0
            if energy_kev == x1:
                return y1
            frac = (math.log(energy_kev) - math.log(x0)) / (math.log(x1) - math.log(x0))
            return math.exp(math.log(y0) + frac * (math.log(y1) - math.log(y0)))
    return points[-1][1]


def interaction_efficiency(mu_cm_inv: float, thickness_cm: float) -> float:
    return 1.0 - math.exp(-mu_cm_inv * thickness_cm)


def compare_part_rows(
    csi_rsp: dict[str, Any],
    bgo_rsp: dict[str, Any],
    part: str,
    csi_thickness_cm: float,
    bgo_thickness_cm: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for energy, label in ENERGIES_KEV:
        mu_csi = loglog_interp(csi_rsp["points"], energy)
        mu_bgo = loglog_interp(bgo_rsp["points"], energy)
        eff_csi = interaction_efficiency(mu_csi, csi_thickness_cm)
        eff_bgo = interaction_efficiency(mu_bgo, bgo_thickness_cm)
        rel_diff = (eff_bgo - eff_csi) / eff_csi if eff_csi else 0.0
        rows.append(
            {
                "part": part,
                "energy_keV": energy,
                "energy_label": label,
                "mu_csi_cm_inv": mu_csi,
                "mu_bgo_cm_inv": mu_bgo,
                "mu_csi_over_mu_bgo": mu_csi / mu_bgo,
                "csi_thickness_cm": csi_thickness_cm,
                "bgo_thickness_cm": bgo_thickness_cm,
                "csi_efficiency": eff_csi,
                "bgo_efficiency": eff_bgo,
                "relative_difference": rel_diff,
                "abs_relative_difference": abs(rel_diff),
                "within_tolerance": abs(rel_diff) <= RELATIVE_TOLERANCE,
            }
        )
    return rows


def max_abs_relative_difference(rows: list[dict[str, Any]]) -> float:
    return max(float(row["abs_relative_difference"]) for row in rows) if rows else math.inf


def optimize_bgo_thickness(
    csi_rsp: dict[str, Any],
    bgo_rsp: dict[str, Any],
    part: str,
    csi_thickness_cm: float,
) -> dict[str, Any]:
    mu_csi = loglog_interp(csi_rsp["points"], 662.0)
    mu_bgo = loglog_interp(bgo_rsp["points"], 662.0)
    seed = csi_thickness_cm * mu_csi / mu_bgo
    max_cm = max(seed * OPTIMIZE_MARGIN_FACTOR, csi_thickness_cm, 1.0)
    best: dict[str, Any] | None = None
    for i in range(1, int(round(max_cm / OPTIMIZE_STEP_CM)) + 1):
        trial = i * OPTIMIZE_STEP_CM
        rows = compare_part_rows(csi_rsp, bgo_rsp, part, csi_thickness_cm, trial)
        score = max_abs_relative_difference(rows)
        if best is None or score < best["max_abs_relative_difference"]:
            best = {
                "part": part,
                "csi_thickness_cm": csi_thickness_cm,
                "recommended_bgo_thickness_cm": round(trial, 3),
                "max_abs_relative_difference": score,
                "passes_tolerance": score <= RELATIVE_TOLERANCE,
                "rows": rows,
            }
    if best is None:
        raise RuntimeError(f"Could not optimize BGO thickness for {part}")
    return best


def source_csi_thicknesses(bounds: dict[str, Any]) -> dict[str, float]:
    comps = bounds["COMPONENTS"]
    side = next(c for c in comps if c["category"] == "active_shield_side")
    bottom = next(c for c in comps if c["category"] == "active_shield_bottom")
    top = next(c for c in comps if c["category"] == "active_shield_top")
    return {
        "side": float(side["params"]["r_out_cm"]) - float(side["params"]["r_in_cm"]),
        "bottom": float(bottom["params"]["z1_cm"]) - float(bottom["params"]["z0_cm"]),
        "top": float(top["params"]["z1_cm"]) - float(top["params"]["z0_cm"]),
    }


def attenuation_verification(csi_thick: dict[str, float]) -> dict[str, Any]:
    csi_rsp = read_rsp(CSI_XSECTION)
    bgo_rsp = read_rsp(BGO_XSECTION)
    part_summaries = [optimize_bgo_thickness(csi_rsp, bgo_rsp, part, csi_thick[part]) for part in PARTS]
    bgo_thick = {item["part"]: item["recommended_bgo_thickness_cm"] for item in part_summaries}
    rows: list[dict[str, Any]] = []
    for item in part_summaries:
        rows.extend(compare_part_rows(csi_rsp, bgo_rsp, item["part"], csi_thick[item["part"]], bgo_thick[item["part"]]))
    return {
        "status": "PASS" if max_abs_relative_difference(rows) <= RELATIVE_TOLERANCE else "FAIL",
        "claim": "BGO current-v3p5 equal-attenuation total-interaction efficiency match to CsI",
        "method": "per-part minimax absolute relative slab total-interaction efficiency difference",
        "tolerance": {
            "metric": "maximum absolute relative difference in slab total-interaction efficiency",
            "relative_tolerance": RELATIVE_TOLERANCE,
        },
        "inputs": {
            "csi_bounds": rel(REF_BOUNDS),
            "csi_xsection": {k: v for k, v in csi_rsp.items() if k != "points"},
            "bgo_xsection": {k: v for k, v in bgo_rsp.items() if k != "points"},
        },
        "energies": [{"energy_keV": energy, "label": label} for energy, label in ENERGIES_KEV],
        "source_csi_thickness_cm": csi_thick,
        "recommended_bgo_thickness_cm": bgo_thick,
        "step_cm": OPTIMIZE_STEP_CM,
        "max_abs_relative_difference": max_abs_relative_difference(rows),
        "by_part": {
            item["part"]: {
                "csi_thickness_cm": item["csi_thickness_cm"],
                "bgo_thickness_cm": item["recommended_bgo_thickness_cm"],
                "max_abs_relative_difference": item["max_abs_relative_difference"],
                "passes_tolerance": item["passes_tolerance"],
            }
            for item in part_summaries
        },
        "rows": rows,
    }


def segment_volume(comp: dict[str, Any]) -> float:
    p = comp["params"]
    shape = comp["shape"]
    if shape == "z_annulus_phi_segment":
        dphi = float(p["dphi_deg"])
        return (
            (dphi / 360.0)
            * math.pi
            * (float(p["r_out_cm"]) ** 2 - float(p["r_in_cm"]) ** 2)
            * (float(p["z1_cm"]) - float(p["z0_cm"]))
        )
    if shape == "z_annulus":
        return math.pi * (float(p["r_out_cm"]) ** 2 - float(p["r_in_cm"]) ** 2) * (
            float(p["z1_cm"]) - float(p["z0_cm"])
        )
    if shape == "z_shell_top_annulus":
        r_out = float(p["r_out_cm"])
        bottom = math.pi * r_out * r_out * (float(p["z_in_bot_cm"]) - float(p["z_out_bot_cm"]))
        side = math.pi * (r_out * r_out - float(p["r_in_cm"]) ** 2) * (
            float(p["z_top_cm"]) - float(p["z_in_bot_cm"])
        )
        top = math.pi * (r_out * r_out - float(p["top_hole_r_cm"]) ** 2) * (
            float(p["top_ann_z1_cm"]) - float(p["top_ann_z0_cm"])
        )
        return bottom + side + top
    return float(comp["volume_cm3"])


def component_density(comp: dict[str, Any], bgo_density: float) -> float:
    if comp["material"] == "BGO":
        return bgo_density
    volume = float(comp.get("volume_cm3", 0.0))
    mass = float(comp.get("mass_kg", 0.0))
    if volume > 0.0:
        return mass * 1000.0 / volume
    raise RuntimeError(f"Cannot derive density for {comp['name']}")


def rename_active(name: str) -> str:
    m = re.fullmatch(r"CsI_Side_Segment_(\d\d)", name)
    if m:
        return f"BGO_Active_Shield_Side{m.group(1)}"
    m = re.fullmatch(r"CsI_Bottom_Quadrant_(\d\d)", name)
    if m:
        return f"BGO_Active_Shield_Bottom{m.group(1)}"
    m = re.fullmatch(r"CsI_TopAnnulus_Segment_(\d\d)", name)
    if m:
        return f"BGO_Active_Shield_Top{m.group(1)}"
    return name


def replace_text_tokens(value: Any) -> Any:
    if isinstance(value, str):
        return (
            value.replace("CsI_Side_Segment_", "BGO_Active_Shield_Side")
            .replace("CsI_Bottom_Quadrant_", "BGO_Active_Shield_Bottom")
            .replace("CsI_TopAnnulus_Segment_", "BGO_Active_Shield_Top")
            .replace("CsI active", "BGO active")
            .replace("CsI veto", "BGO veto")
            .replace("CsI", "BGO")
        )
    if isinstance(value, list):
        return [replace_text_tokens(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_text_tokens(item) for key, item in value.items()}
    return value


def parse_material_density(material: str, path: Path) -> float:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(
        rf"^Material\s+{re.escape(material)}\s*$.*?^{re.escape(material)}\.Density\s+([-+0-9.eE]+)\s*$",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise RuntimeError(f"Could not find density for {material} in {path}")
    return float(match.group(1))


def build_bgo_bounds(src: dict[str, Any], atten: dict[str, Any], bgo_density: float) -> tuple[dict[str, Any], dict[str, Any]]:
    bounds = json.loads(json.dumps(src))
    source_csi_mass = sum(float(c["mass_kg"]) for c in src["COMPONENTS"] if str(c.get("category", "")).startswith("active_shield"))
    t = atten["recommended_bgo_thickness_cm"]

    side_src = next(c for c in src["COMPONENTS"] if c["category"] == "active_shield_side")
    bottom_src = next(c for c in src["COMPONENTS"] if c["category"] == "active_shield_bottom")
    top_src = next(c for c in src["COMPONENTS"] if c["category"] == "active_shield_top")
    side_r_in = float(side_src["params"]["r_in_cm"])
    side_r_out = side_r_in + float(t["side"])
    side_z0 = float(side_src["params"]["z0_cm"])
    side_z1 = float(side_src["params"]["z1_cm"])
    bottom_z1 = float(bottom_src["params"]["z1_cm"])
    bottom_z0 = bottom_z1 - float(t["bottom"])
    top_z0 = float(top_src["params"]["z0_cm"])
    top_z1 = top_z0 + float(t["top"])
    top_r_in = float(top_src["params"]["r_in_cm"])

    for comp in bounds["COMPONENTS"]:
        cat = str(comp.get("category", ""))
        if cat.startswith("active_shield"):
            comp["name"] = rename_active(comp["name"])
            comp["material"] = "BGO"
            p = comp["params"]
            if cat == "active_shield_side":
                p["r_in_cm"] = side_r_in
                p["r_out_cm"] = side_r_out
                p["z0_cm"] = side_z0
                p["z1_cm"] = side_z1
            elif cat == "active_shield_bottom":
                p["r_in_cm"] = 0.0
                p["r_out_cm"] = side_r_out
                p["z0_cm"] = bottom_z0
                p["z1_cm"] = bottom_z1
            elif cat == "active_shield_top":
                p["r_in_cm"] = top_r_in
                p["r_out_cm"] = side_r_out
                p["z0_cm"] = top_z0
                p["z1_cm"] = top_z1
            comp["install"] = replace_text_tokens(comp.get("install", ""))
            comp["why_for_sim"] = replace_text_tokens(comp.get("why_for_sim", ""))
            comp["size_basis"] = (
                "BGO thickness recomputed against the current v3p5 CsI dimensions using "
                "MEGAlib/Geant4 total cross-section slab efficiency matching."
            )
            comp["source_tag"] = "TES_511_Balloon Bgo_sample current-v3p5 equal-attenuation control"

        if comp["name"] == "ActiveShield_Al_Backplane_detector_bay":
            p = comp["params"]
            p["r_in_cm"] = side_r_out + 0.05
            p["r_out_cm"] = side_r_out + 0.15
        elif comp["name"] == "ActiveShield_Flex_Kapton_detector_bay":
            p = comp["params"]
            p["r_in_cm"] = side_r_out + 0.17
            p["r_out_cm"] = side_r_out + 0.20
        elif comp["name"] == "Outer_Al_Mechanical_Shell_detector_bay":
            p = comp["params"]
            p["r_in_cm"] = side_r_out + 0.30
            p["r_out_cm"] = side_r_out + 0.60
            p["z_out_bot_cm"] = bottom_z0 - 0.60
            p["z_in_bot_cm"] = bottom_z0 - 0.30
            p["z_top_cm"] = top_z1 + 0.20
            p["top_ann_z0_cm"] = top_z1 + 0.20
            p["top_ann_z1_cm"] = top_z1 + 0.50

    changed_names = {
        "ActiveShield_Al_Backplane_detector_bay",
        "ActiveShield_Flex_Kapton_detector_bay",
        "Outer_Al_Mechanical_Shell_detector_bay",
    }
    for comp in bounds["COMPONENTS"]:
        if str(comp.get("category", "")).startswith("active_shield") or comp["name"] in changed_names:
            volume = segment_volume(comp)
            density = component_density(comp, bgo_density)
            comp["volume_cm3"] = volume
            comp["mass_kg"] = volume * density / 1000.0

    active_mass = sum(float(c["mass_kg"]) for c in bounds["COMPONENTS"] if str(c.get("category", "")).startswith("active_shield"))
    total_mass = sum(float(c["mass_kg"]) for c in bounds["COMPONENTS"])
    bounds["VERSION"] = "Bgo_sample_current_v3p5_equal_attenuation"
    bounds["DESIGN_NOTE"] = (
        "Current v3p5 BGO sample: same inner detector-head model, active scintillator replaced "
        "by BGO with current-CsI equal-attenuation thicknesses, BGO threshold 70 keV, and "
        "outer package/shell radii and z limits adapted to the BGO envelope."
    )
    bounds["META"]["claim_level"] = "BGO_SAMPLE_STEP01_GEOMETRY_NO_TRANSPORT"
    bounds["META"]["active_material_nominal"] = "BGO current-v3p5 equal-attenuation sample"
    bounds["META"]["source_csi_active_mass_kg"] = source_csi_mass
    bounds["META"]["active_bgo_mass_kg"] = active_mass
    bounds["META"]["active_mass_ratio_bgo_over_csi"] = active_mass / source_csi_mass if source_csi_mass else 0.0
    bounds["META"]["total_mass_kg"] = total_mass
    bounds["META"]["non_active_mass_kg"] = total_mass - active_mass
    bounds["META"]["bgo_sample"] = {
        "threshold_keV": BGO_VETO_THRESHOLD_KEV,
        "source_csi_thickness_cm": atten["source_csi_thickness_cm"],
        "bgo_thickness_cm": t,
        "attenuation_status": atten["status"],
        "attenuation_max_abs_relative_difference": atten["max_abs_relative_difference"],
        "outer_shell_policy": "preserve inner clearances; move active package and outer shell by original offsets from the active BGO envelope",
        "transport_status": "NOT_RUN",
    }
    bounds["META"] = replace_text_tokens(bounds["META"])

    mass = {
        "rows": [
            {
                "cid": comp.get("cid"),
                "name": comp.get("name"),
                "category": comp.get("category"),
                "material": comp.get("material"),
                "shape": comp.get("shape"),
                "volume_cm3": comp.get("volume_cm3"),
                "mass_kg": comp.get("mass_kg"),
            }
            for comp in bounds["COMPONENTS"]
        ],
        "total_mass_kg": total_mass,
        "source_csi_active_mass_kg": source_csi_mass,
        "bgo_active_mass_kg": active_mass,
        "active_mass_ratio_bgo_over_csi": active_mass / source_csi_mass if source_csi_mass else 0.0,
        "bgo_density_g_cm3": bgo_density,
    }
    return bounds, mass


def write_mass_csv(payload: dict[str, Any]) -> None:
    fields = ["cid", "name", "category", "material", "shape", "volume_cm3", "mass_kg"]
    with MASS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(payload["rows"])


def write_attenuation_outputs(payload: dict[str, Any]) -> None:
    write_text(ATTEN_JSON, json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    fields = [
        "part",
        "energy_keV",
        "energy_label",
        "mu_csi_cm_inv",
        "mu_bgo_cm_inv",
        "mu_csi_over_mu_bgo",
        "csi_thickness_cm",
        "bgo_thickness_cm",
        "csi_efficiency",
        "bgo_efficiency",
        "relative_difference",
        "abs_relative_difference",
        "within_tolerance",
    ]
    with ATTEN_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(payload["rows"])


def patch_bgo_thresholds(det_text: str) -> str:
    lines = det_text.splitlines()
    patched: list[str] = []
    pending_noise: str | None = None
    active_detector_re = r"BGO_Active_Shield_(?:Side|Bottom|Top)\d\d(?:_[A-Za-z0-9_]+)?_SD"
    for line in lines:
        if pending_noise and not line.startswith(pending_noise.split(".")[0] + ".NoiseThresholdEqualsTriggerThreshold"):
            patched.append(pending_noise)
            pending_noise = None
        m = re.match(rf"^({active_detector_re})\.TriggerThreshold\s+[-+0-9.eE]+$", line)
        if m:
            det = m.group(1)
            patched.append(f"{det}.TriggerThreshold {fmt(BGO_VETO_THRESHOLD_KEV)}")
            pending_noise = f"{det}.NoiseThresholdEqualsTriggerThreshold true"
            continue
        if pending_noise and line.startswith(pending_noise.split(".")[0] + ".NoiseThresholdEqualsTriggerThreshold"):
            patched.append(pending_noise)
            pending_noise = None
            continue
        m = re.match(rf"^({active_detector_re})\.EnergyResolution\s+Gauss\s+0\.001\s+0\.001\s+1$", line)
        if m:
            det = m.group(1)
            patched.append(f"{det}.EnergyResolution Gauss {fmt(BGO_VETO_THRESHOLD_KEV)} {fmt(BGO_VETO_THRESHOLD_KEV)} 1")
            continue
        patched.append(line)
    if pending_noise:
        patched.append(pending_noise)
    return "\n".join(patched) + "\n"


def write_overlap_source() -> None:
    text = f"""Version                     1
Geometry                    {SETUP}
CheckForOverlaps            10000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/DelMe_Bgo_sample_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
"""
    write_text(OVERLAP_SOURCE, text)


def run_cosima_overlap() -> dict[str, Any]:
    write_overlap_source()
    if not COSIMA.exists():
        write_text(OVERLAP_LOG, f"ERROR: missing cosima executable: {COSIMA}\n")
        return {"available": False, "status": "MISSING_COSIMA", "path": rel(OVERLAP_LOG), "problems": ["missing_cosima"]}
    proc = subprocess.run([str(COSIMA), str(OVERLAP_SOURCE)], cwd=OUT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    write_text(OVERLAP_LOG, proc.stdout)
    problems = []
    for label, pattern in {
        "overlap_warnings": "GeomVol1002",
        "duplicate_material": "already exists",
        "detector_init_failure": "Unable to initalize",
        "detector_initialize_failure": "Unable to initialize",
        "geometry_parse_error": "Unable to parse",
        "missing_run_summary": "Summary for run Minimum",
    }.items():
        present = pattern in proc.stdout
        if label == "missing_run_summary":
            if not present:
                problems.append(label)
        elif present:
            problems.append(label)
    return {
        "available": True,
        "status": "PASS" if proc.returncode == 0 and not problems else "FAIL",
        "returncode": proc.returncode,
        "path": rel(OVERLAP_LOG),
        "problems": problems,
    }


def check_outputs(bounds: dict[str, Any], mass: dict[str, Any], atten: dict[str, Any], overlap: dict[str, Any]) -> dict[str, Any]:
    geo_text = GEO.read_text(encoding="utf-8", errors="ignore")
    det_text = DET.read_text(encoding="utf-8", errors="ignore")
    active_components = [c for c in bounds["COMPONENTS"] if str(c.get("category", "")).startswith("active_shield")]
    bgo_proxy_detectors = sorted(set(re.findall(r"^(BGO_Active_Shield_(?:Side|Bottom|Top)\d\d(?:_[A-Za-z0-9_]+)?_SD)\.TriggerThreshold\s+70(?:\.0)?\s*$", det_text, re.MULTILINE)))
    bgo_noise = sorted(set(re.findall(r"^(BGO_Active_Shield_(?:Side|Bottom|Top)\d\d(?:_[A-Za-z0-9_]+)?_SD)\.NoiseThresholdEqualsTriggerThreshold\s+true\s*$", det_text, re.MULTILINE)))
    bgo_energy70 = sorted(set(re.findall(r"^(BGO_Active_Shield_(?:Side|Bottom|Top)\d\d(?:_[A-Za-z0-9_]+)?_SD)\.EnergyResolution\s+Gauss\s+70(?:\.0)?\s+70(?:\.0)?\s+1\s*$", det_text, re.MULTILINE)))
    bgo_energy_default = sorted(set(re.findall(r"^(BGO_Active_Shield_(?:Side|Bottom|Top)\d\d(?:_[A-Za-z0-9_]+)?_SD)\.EnergyResolution\s+Gauss\s+0\.001\s+0\.001\s+1\s*$", det_text, re.MULTILINE)))
    logical_segments = sorted({re.sub(r"_(?:below|above|side_port).*", "", name) for name in re.findall(r"\b(BGO_Active_Shield_(?:Side|Bottom|Top)\d\d)", geo_text)})
    stale = []
    for path in (GEO, DET, BOUNDS):
        if "CsI_Side_Segment" in path.read_text(encoding="utf-8", errors="ignore") or "CsI_Bottom_Quadrant" in path.read_text(encoding="utf-8", errors="ignore") or "CsI_TopAnnulus_Segment" in path.read_text(encoding="utf-8", errors="ignore"):
            stale.append(rel(path))
    native_trigger_residue = bool(re.search(r"^(Trigger|Veto_)\b", det_text, re.MULTILINE) or "TES_MainTrigger" in det_text)
    outer = next(c for c in bounds["COMPONENTS"] if c["name"] == "Outer_Al_Mechanical_Shell_detector_bay")["params"]
    side = next(c for c in active_components if c["category"] == "active_shield_side")["params"]
    return {
        "active_component_count": len(active_components),
        "logical_bgo_segment_count": len(logical_segments),
        "bgo_geo_material_proxy_count": len(re.findall(r"^BGO_Active_Shield_(?:Side|Bottom|Top)\d\d(?:_[A-Za-z0-9_]+)?\.Material\s+BGO\s*$", geo_text, re.MULTILINE)),
        "bgo_proxy_detector_threshold70_count": len(bgo_proxy_detectors),
        "bgo_proxy_detector_noise_equals_count": len(bgo_noise),
        "bgo_proxy_detector_energy_resolution70_count": len(bgo_energy70),
        "bgo_proxy_detector_default_low_energy_resolution_count": len(bgo_energy_default),
        "bgo_threshold_detectors_equal_noise_detectors": bgo_proxy_detectors == bgo_noise,
        "bgo_threshold_detectors_equal_energy_resolution70_detectors": bgo_proxy_detectors == bgo_energy70,
        "native_trigger_residue": native_trigger_residue,
        "stale_csi_active_name_paths": stale,
        "source_csi_thickness_cm": atten["source_csi_thickness_cm"],
        "bgo_thickness_cm": atten["recommended_bgo_thickness_cm"],
        "attenuation_status": atten["status"],
        "attenuation_max_abs_relative_difference": atten["max_abs_relative_difference"],
        "bgo_veto_threshold_keV": BGO_VETO_THRESHOLD_KEV,
        "source_csi_active_mass_kg": mass["source_csi_active_mass_kg"],
        "bgo_active_mass_kg": mass["bgo_active_mass_kg"],
        "active_mass_ratio_bgo_over_csi": mass["active_mass_ratio_bgo_over_csi"],
        "bgo_total_mass_kg": mass["total_mass_kg"],
        "outer_shell_r_out_cm": outer["r_out_cm"],
        "outer_shell_z_out_bot_cm": outer["z_out_bot_cm"],
        "outer_shell_top_ann_z1_cm": outer["top_ann_z1_cm"],
        "active_side_r_out_cm": side["r_out_cm"],
        "transport_status": "NOT_RUN",
        "cosima_overlap_status": overlap.get("status"),
    }


def md_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def write_summary(payload: dict[str, Any]) -> None:
    checks = payload["checks"]
    rows = [
        {"quantity": "Source CsI thickness side/bottom/top", "value": checks["source_csi_thickness_cm"]},
        {"quantity": "BGO thickness side/bottom/top", "value": checks["bgo_thickness_cm"]},
        {"quantity": "BGO veto threshold", "value": f"{checks['bgo_veto_threshold_keV']} keV"},
        {"quantity": "Attenuation max abs relative diff", "value": f"{checks['attenuation_max_abs_relative_difference']:.6g}"},
        {"quantity": "BGO active mass", "value": f"{checks['bgo_active_mass_kg']:.6g} kg"},
        {"quantity": "Source CsI active mass", "value": f"{checks['source_csi_active_mass_kg']:.6g} kg"},
        {"quantity": "Active mass ratio BGO/CsI", "value": f"{checks['active_mass_ratio_bgo_over_csi']:.6g}"},
        {"quantity": "Logical active segments", "value": checks["logical_bgo_segment_count"]},
        {"quantity": "BGO proxy detectors at 70 keV", "value": checks["bgo_proxy_detector_threshold70_count"]},
        {"quantity": "BGO proxy energy-resolution low anchors at 70 keV", "value": checks["bgo_proxy_detector_energy_resolution70_count"]},
        {"quantity": "Cosima overlap", "value": checks["cosima_overlap_status"]},
    ]
    lines = [
        "# Bgo_sample",
        "",
        f"Status: `{payload['status']}`.",
        "",
        "This package is a current-v3p5 BGO equal-attenuation geometry sample for TES_511_Balloon. It is a Step01 geometry/control artifact, not a BGO background or sensitivity result.",
        "",
        md_table(rows, ["quantity", "value"]),
        "",
        "## Files",
        "",
        f"- `{GEO.name}`",
        f"- `{DET.name}`",
        f"- `{SETUP.name}`",
        f"- `{BOUNDS.name}`",
        f"- `{MASS_JSON.name}` / `{MASS_CSV.name}`",
        f"- `{ATTEN_JSON.name}` / `{ATTEN_CSV.name}`",
        f"- `{OVERLAP_LOG.name}`",
        "",
        "## Boundary",
        "",
        "- Inner detector-head geometry and side-entry pointing are inherited from the current v3p5 center-finger bounds.",
        "- BGO thicknesses are recomputed against the current v3p5 CsI side/bottom/top thicknesses, not copied from the older `new_geo_re_2` branch.",
        "- The active package and outer Al shell follow the new BGO active-envelope by preserving the original radial and z offsets.",
        "- Prompt, activation, delayed transport, Step05 veto/time-axis, Step08 significance, and detector-coupled Step09 response remain `NOT_RUN` for this sample.",
        "",
    ]
    write_text(SUMMARY_MD, "\n".join(lines))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    src_bounds = load_json(REF_BOUNDS)
    csi_thick = source_csi_thicknesses(src_bounds)
    atten = attenuation_verification(csi_thick)
    bgo_density = parse_material_density("BGO", MEGALIB_MATERIALS)
    bounds, mass = build_bgo_bounds(src_bounds, atten, bgo_density)

    builder = load_v3p5_builder()
    builder.write_materials()
    builder.write_intro()
    geo_text, records, component_to_volumes = builder.build_geo(bounds)
    write_text(GEO, geo_text)
    builder.write_det(records)
    write_text(DET, patch_bgo_thresholds(DET.read_text(encoding="utf-8")))
    extents = builder.parse_generated_geometry_extents(geo_text)
    builder.write_setup(extents)

    write_text(BOUNDS, json.dumps(bounds, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    write_text(MASS_JSON, json.dumps(mass, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    write_mass_csv(mass)
    write_attenuation_outputs(atten)

    overlap = run_cosima_overlap()
    checks = check_outputs(bounds, mass, atten, overlap)
    problems = []
    if atten["status"] != "PASS":
        problems.append("attenuation_not_pass")
    if checks["active_component_count"] != 20 or checks["logical_bgo_segment_count"] != 20:
        problems.append("wrong_bgo_logical_segment_count")
    if checks["bgo_proxy_detector_threshold70_count"] == 0:
        problems.append("no_bgo_70kev_proxy_detectors")
    if not checks["bgo_threshold_detectors_equal_noise_detectors"]:
        problems.append("bgo_noise_threshold_mismatch")
    if not checks["bgo_threshold_detectors_equal_energy_resolution70_detectors"]:
        problems.append("bgo_energy_resolution_threshold_mismatch")
    if checks["bgo_proxy_detector_default_low_energy_resolution_count"] != 0:
        problems.append("bgo_default_low_energy_resolution_residue")
    if checks["native_trigger_residue"]:
        problems.append("native_trigger_residue_present")
    if checks["stale_csi_active_name_paths"]:
        problems.append("stale_csi_active_names")
    if overlap.get("status") != "PASS":
        problems.append("cosima_overlap_not_pass")

    payload = {
        "status": "PASS" if not problems else "FAIL",
        "claim_level": "BGO_SAMPLE_STEP01_GEOMETRY_NO_TRANSPORT",
        "scope": "Current-v3p5 BGO equal-attenuation sample geometry with 70 keV BGO detector thresholds.",
        "inputs": {
            "source_bounds": rel(REF_BOUNDS),
            "geometry_builder": rel(REF_BUILDER),
            "megalib_materials": str(MEGALIB_MATERIALS),
        },
        "outputs": {
            "directory": rel(OUT),
            "geometry": rel(GEO),
            "detector": rel(DET),
            "setup": rel(SETUP),
            "bounds": rel(BOUNDS),
            "mass_budget_json": rel(MASS_JSON),
            "attenuation_json": rel(ATTEN_JSON),
            "cosima_overlap_log": rel(OVERLAP_LOG),
        },
        "checks": checks,
        "geometry_extents": extents,
        "component_to_generated_volumes": component_to_volumes,
        "overlap": overlap,
        "problems": problems,
    }
    write_text(SUMMARY_JSON, json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    write_summary(payload)
    print(json.dumps({"status": payload["status"], "problems": problems, "checks": checks, "out": rel(OUT)}, indent=2, ensure_ascii=False))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
