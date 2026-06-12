#!/usr/bin/env python3
"""Build a DEMO2 BGO active-shield control geometry scaffold.

This does not run the Step02-Step08 physics chain.  It creates the clean input
geometry/control ledger needed for that future run: same DEMO2 detector-head
geometry, same active-shield segmentation, but with the active shield material
and detector/veto names changed from CsI to BGO.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm"
OUT = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_bgo_control"

SRC_GEO = SRC / "TibetTES_ADR_v4c_mkflange_cm.geo"
SRC_DET = SRC / "TibetTES_ADR_v4c_mkflange_cm.det"
SRC_SETUP = SRC / "TibetTES_ADR_v4c_mkflange_cm.geo.setup"
SRC_BOUNDS = SRC / "bounds.json"
SRC_MASS = SRC / "mass_budget.json"
SRC_MATERIALS = SRC / "Materials_TibetTES_demo2.geo"
SRC_INTRO = SRC / "Intro_TibetTES_demo2.geo"

MODEL = "TibetTES_ADR_v4c_mkflange_bgo_control"
GEO = OUT / f"{MODEL}.geo"
DET = OUT / f"{MODEL}.det"
SETUP = OUT / f"{MODEL}.geo.setup"
BOUNDS = OUT / "bounds.json"
MASS_JSON = OUT / "mass_budget.json"
MASS_CSV = OUT / "mass_budget.csv"
SUMMARY_JSON = OUT / "bgo_control_geometry_summary.json"
SUMMARY_MD = OUT / "bgo_control_geometry.md"
OVERLAP_SOURCE = OUT / "overlap_check_bgo_control.source"
OVERLAP_LOG = OUT / "cosima_overlap_bgo_control.log"
MEGALIB_MATERIALS = Path("/home/ubuntu/MEGAlib_Install/megalib-main/resource/examples/geomega/materials/Materials.geo")
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")


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


def parse_material_density(material: str, path: Path) -> float:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(rf"^Material\s+{re.escape(material)}\s*$.*?^{re.escape(material)}\.Density\s+([-+0-9.eE]+)\s*$", text, flags=re.MULTILINE | re.DOTALL)
    if not m:
        raise RuntimeError(f"Could not find density for {material} in {path}")
    return float(m.group(1))


def replace_active_names(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("CsI_Active_Shield", "BGO_Active_Shield").replace("CsI(Tl)", "BGO")
    if isinstance(value, list):
        return [replace_active_names(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_active_names(item) for key, item in value.items()}
    return value


def transform_geo(text: str) -> str:
    text = text.replace("CsI_Active_Shield", "BGO_Active_Shield")
    text = re.sub(r"(// Volume BGO_Active_Shield_\S+; material=)CsI", r"\1BGO", text)
    text = re.sub(r"(BGO_Active_Shield_\S+\.Material\s+)CsI(\s*)$", r"\1BGO\2", text, flags=re.MULTILINE)
    return text


def transform_det(text: str) -> str:
    text = text.replace("CsI_Active_Shield", "BGO_Active_Shield")
    text = text.replace("CsI anticoincidence veto", "BGO anticoincidence veto")
    text = text.replace("CsI veto triggers", "BGO veto triggers")
    text = text.replace("CsI segment", "BGO segment")
    return text


def update_bounds(src_bounds: dict[str, Any]) -> dict[str, Any]:
    bounds = replace_active_names(src_bounds)
    bounds["VERSION"] = "ADR_v6_demo2_adrpassive_bgo_control"
    bounds["DESIGN_NOTE"] = (
        "DEMO2 BGO-control geometry scaffold: same detector-head geometry and active-shield "
        "segmentation as the current CsI authority, but active-shield material/names are BGO. "
        "This is an input scaffold only; Step02-Step08 transport is not run here."
    )
    active = bounds["ACTIVE_SHIELD"]
    active["name"] = "BGO_Active_Shield"
    active["mat"] = "BGO"
    active["basis"] = "BGO active-shield control variant with current DEMO2 dimensions and segmentation."
    meta = bounds["META"]
    meta["active_material_nominal"] = "BGO control scaffold, same geometry as current CsI DEMO2 authority"
    meta["claim_level"] = "L1_BGO_CONTROL_GEOMETRY_SCAFFOLD_NO_TRANSPORT"
    meta["bgo_control_source_geometry"] = rel(SRC)
    meta["bgo_control_transport_status"] = "NOT_RUN"
    return bounds


def update_mass_budget(src_mass: dict[str, Any], bgo_density: float) -> dict[str, Any]:
    rows = src_mass["rows"]
    active_volume = 0.0
    csi_active_mass = 0.0
    csi_density_values = set()
    new_rows = []
    for row in rows:
        row = dict(row)
        if str(row.get("category", "")).startswith("active_shield"):
            volume = float(row["volume_cm3"])
            active_volume += volume
            csi_active_mass += float(row["mass_kg"])
            csi_density_values.add(float(row["density_g_cm3"]))
            row["unit"] = str(row["unit"]).replace("CsI_Active_Shield", "BGO_Active_Shield")
            row["material"] = "BGO"
            row["density_g_cm3"] = bgo_density
            row["mass_kg"] = volume * bgo_density / 1000.0
            row["notes"] = str(row.get("notes", "")).replace("CsI", "BGO") + " BGO-control material substitution."
        new_rows.append(row)
    group: dict[str, float] = {}
    for row in new_rows:
        group[row["category"]] = group.get(row["category"], 0.0) + float(row["mass_kg"])
    return {
        "rows": new_rows,
        "group_mass_kg": group,
        "total_mass_kg": sum(float(row["mass_kg"]) for row in new_rows),
        "bgo_control": {
            "source_mass_budget": rel(SRC_MASS),
            "csi_density_g_cm3_from_source_rows": sorted(csi_density_values),
            "bgo_density_g_cm3_from_megalib_materials": bgo_density,
            "active_volume_cm3": active_volume,
            "csi_active_mass_kg": csi_active_mass,
            "bgo_active_mass_kg": active_volume * bgo_density / 1000.0,
            "active_mass_ratio_bgo_over_csi": (active_volume * bgo_density / 1000.0) / csi_active_mass if csi_active_mass else 0.0,
            "transport_status": "NOT_RUN",
        },
    }


def write_mass_csv(payload: dict[str, Any]) -> None:
    rows = payload["rows"]
    fields = list(rows[0])
    with MASS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_overlap_source() -> None:
    source = f"""Version                     1
Geometry                    {SETUP}
CheckForOverlaps            1000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/DelMe_bgo_control_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
"""
    write_text(OVERLAP_SOURCE, source)


def run_cosima_overlap() -> dict[str, Any]:
    write_overlap_source()
    if not COSIMA.exists():
        write_text(OVERLAP_LOG, f"ERROR: missing cosima executable: {COSIMA}\n")
        return {"available": False, "status": "MISSING_COSIMA", "path": rel(OVERLAP_LOG), "problems": ["missing_cosima"]}
    proc = subprocess.run([str(COSIMA), str(OVERLAP_SOURCE)], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    write_text(OVERLAP_LOG, proc.stdout)
    problems = []
    for label, pattern in {
        "overlap_warnings": "GeomVol1002",
        "duplicate_material": "already exists",
        "detector_init_failure": "Unable to initalize",
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


def check_output_files(overlap: dict[str, Any], mass: dict[str, Any]) -> dict[str, Any]:
    geo_text = GEO.read_text(encoding="utf-8", errors="ignore")
    det_text = DET.read_text(encoding="utf-8", errors="ignore")
    bounds = load_json(BOUNDS)
    bgo_segments = sorted(set(re.findall(r"^(BGO_Active_Shield_(?:Side|Bottom|Top)\d{2})\.Material\s+BGO\s*$", geo_text, flags=re.MULTILINE)))
    det_segments = sorted(set(re.findall(r"^(BGO_Active_Shield_(?:Side|Bottom|Top)\d{2})_SD\.SensitiveVolume\s+BGO_Active_Shield_", det_text, flags=re.MULTILINE)))
    veto_triggers = sorted(set(re.findall(r"^Trigger\s+Veto_(BGO_Active_Shield_(?:Side|Bottom|Top)\d{2})\s*$", det_text, flags=re.MULTILINE)))
    thresholds = re.findall(r"^BGO_Active_Shield_(?:Side|Bottom|Top)\d{2}_SD\.TriggerThreshold\s+50(?:\.0)?\s*$", det_text, flags=re.MULTILINE)
    noise = re.findall(r"^BGO_Active_Shield_(?:Side|Bottom|Top)\d{2}_SD\.NoiseThresholdEqualsTriggerThreshold\s+true\s*$", det_text, flags=re.MULTILINE)
    stale_csi = []
    for path in (GEO, DET, BOUNDS):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "CsI_Active_Shield" in text:
            stale_csi.append(rel(path))
    bgo_meta = mass["bgo_control"]
    return {
        "geo_exists": GEO.exists(),
        "det_exists": DET.exists(),
        "setup_exists": SETUP.exists(),
        "bounds_exists": BOUNDS.exists(),
        "mass_json_exists": MASS_JSON.exists(),
        "bgo_material_segments": len(bgo_segments),
        "detector_segments": len(det_segments),
        "veto_triggers": len(veto_triggers),
        "threshold50_segments": len(thresholds),
        "noise_equals_threshold_segments": len(noise),
        "stale_csi_active_names": stale_csi,
        "bounds_active_name": bounds.get("ACTIVE_SHIELD", {}).get("name"),
        "bounds_active_material": bounds.get("ACTIVE_SHIELD", {}).get("mat"),
        "bgo_density_g_cm3": bgo_meta["bgo_density_g_cm3_from_megalib_materials"],
        "active_volume_cm3": bgo_meta["active_volume_cm3"],
        "csi_active_mass_kg": bgo_meta["csi_active_mass_kg"],
        "bgo_active_mass_kg": bgo_meta["bgo_active_mass_kg"],
        "active_mass_ratio_bgo_over_csi": bgo_meta["active_mass_ratio_bgo_over_csi"],
        "bgo_total_mass_kg": mass["total_mass_kg"],
        "transport_status": "NOT_RUN",
        "cosima_overlap_status": overlap.get("status"),
    }


def markdown_table(rows: list[dict[str, Any]], fields: list[str]) -> str:
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join(["---"] * len(fields)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(field, "")) for field in fields) + " |")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    bgo_density = parse_material_density("BGO", MEGALIB_MATERIALS)

    intro = SRC_INTRO.read_text(encoding="utf-8", errors="ignore").replace(
        "MassmodelTibetTES_ADR_v6_demo2_adrpassive_csi",
        "MassmodelTibetTES_ADR_v6_demo2_adrpassive_bgo_control",
    )
    write_text(OUT / SRC_INTRO.name, intro)
    shutil.copyfile(SRC_MATERIALS, OUT / SRC_MATERIALS.name)
    write_text(GEO, transform_geo(SRC_GEO.read_text(encoding="utf-8", errors="ignore")))
    write_text(DET, transform_det(SRC_DET.read_text(encoding="utf-8", errors="ignore")))
    setup = f"""Name TibetTES_ADR_v6_demo2_adrpassive_bgo_control
Version 1
Include {GEO.name}
Include {DET.name}
SurroundingSphere 35 0 0 -3 35
"""
    write_text(SETUP, setup)
    bounds = update_bounds(load_json(SRC_BOUNDS))
    write_text(BOUNDS, json.dumps(bounds, indent=2, ensure_ascii=False) + "\n")
    mass = update_mass_budget(load_json(SRC_MASS), bgo_density)
    write_text(MASS_JSON, json.dumps(mass, indent=2, ensure_ascii=False) + "\n")
    write_mass_csv(mass)
    overlap = run_cosima_overlap()
    checks = check_output_files(overlap, mass)
    ok = (
        checks["bgo_material_segments"] == 20
        and checks["detector_segments"] == 20
        and checks["veto_triggers"] == 20
        and checks["threshold50_segments"] == 20
        and checks["noise_equals_threshold_segments"] == 20
        and not checks["stale_csi_active_names"]
        and checks["bounds_active_name"] == "BGO_Active_Shield"
        and checks["bounds_active_material"] == "BGO"
        and checks["transport_status"] == "NOT_RUN"
        and checks["cosima_overlap_status"] == "PASS"
    )
    payload = {
        "status": "PASS" if ok else "FAIL",
        "claim_level": "L1_BGO_CONTROL_GEOMETRY_SCAFFOLD_NO_TRANSPORT",
        "scope": "BGO active-shield control geometry scaffold only. Same DEMO2 geometry and segmentation as the current CsI authority; Step02-Step08 transport/source/significance chain is not run.",
        "inputs": {
            "source_geometry_dir": rel(SRC),
            "megalib_materials": str(MEGALIB_MATERIALS),
            "bgo_density_source": "local MEGAlib Materials.geo",
        },
        "outputs": {
            "geometry": rel(GEO),
            "detector": rel(DET),
            "setup": rel(SETUP),
            "bounds": rel(BOUNDS),
            "mass_budget_json": rel(MASS_JSON),
            "mass_budget_csv": rel(MASS_CSV),
            "cosima_overlap_log": rel(OVERLAP_LOG),
        },
        "checks": checks,
        "overlap": overlap,
    }
    write_text(SUMMARY_JSON, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")

    rows = [
        {"quantity": "BGO active material segments", "value": checks["bgo_material_segments"]},
        {"quantity": "BGO detector segments", "value": checks["detector_segments"]},
        {"quantity": "BGO veto triggers", "value": checks["veto_triggers"]},
        {"quantity": "BGO density", "value": f"{checks['bgo_density_g_cm3']:.6g} g/cm3"},
        {"quantity": "Current CsI active mass", "value": f"{checks['csi_active_mass_kg']:.6g} kg"},
        {"quantity": "BGO control active mass", "value": f"{checks['bgo_active_mass_kg']:.6g} kg"},
        {"quantity": "Active mass ratio", "value": f"{checks['active_mass_ratio_bgo_over_csi']:.6g}"},
        {"quantity": "BGO total local modeled mass", "value": f"{checks['bgo_total_mass_kg']:.6g} kg"},
        {"quantity": "Transport/source/significance status", "value": checks["transport_status"]},
        {"quantity": "Cosima overlap check", "value": checks["cosima_overlap_status"]},
    ]
    lines = [
        "# BGO Control Geometry Scaffold",
        "",
        f"Status: `{payload['status']}`.",
        "",
        "This is a BGO active-shield geometry scaffold, not a BGO physics-control result.",
        "It preserves the current DEMO2 detector-head geometry and active-shield segmentation, changes active-shield material/names to BGO, and keeps Step02-Step08 transport status at `NOT_RUN`.",
        "",
        markdown_table(rows, ["quantity", "value"]),
        "",
        "## Boundary",
        "",
        "- This artifact is sufficient as the input geometry authority for a future BGO control run.",
        "- It does not estimate BGO activation yields, delayed transport leakage, veto efficiency, or detectability.",
        "- A paper-facing CsI-vs-BGO conclusion still requires rebuilding the delayed source, delayed transport, Step05 selection, and Step08 significance for this geometry.",
        "",
    ]
    write_text(SUMMARY_MD, "\n".join(lines))
    print(json.dumps({"status": payload["status"], "checks": checks, "out": rel(OUT)}, indent=2, ensure_ascii=False))
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
