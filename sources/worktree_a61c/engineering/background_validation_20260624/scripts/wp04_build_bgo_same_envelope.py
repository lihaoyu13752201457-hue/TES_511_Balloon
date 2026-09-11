#!/usr/bin/env python3
"""WP04 BGO same-envelope derived geometry for HARNESS_20260624.

Only CsI active-shield material lines are changed to BGO. Geometry shapes,
positions, mothers, detector references, and parser-facing volume names are
kept unchanged.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
ENG = Path(__file__).resolve().parents[1]
OUT = ENG / "04_bgo_variant"
DERIVED = OUT / "geometry_bgo_same_envelope"

BASE_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy"
BASE_STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
NEW_STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_bgo_same_envelope_megalib_proxy"
BASE_GEO = BASE_DIR / f"{BASE_STEM}.geo"
BASE_DET = BASE_DIR / f"{BASE_STEM}.det"
BASE_SETUP = BASE_DIR / f"{BASE_STEM}.geo.setup"
BASE_INTRO = BASE_DIR / f"Intro_{BASE_STEM}.geo"
BASE_MATERIALS = BASE_DIR / "Materials_DEMO2_DR_v3p5.geo"
AUDIT_FIX5 = ROOT / "outputs/reports/user_redesign_multiholeW_fix5_20260621/audit_fix5_geometry.py"

NEW_GEO = DERIVED / f"{NEW_STEM}.geo"
NEW_DET = DERIVED / f"{NEW_STEM}.det"
NEW_SETUP = DERIVED / f"{NEW_STEM}.geo.setup"
NEW_INTRO = DERIVED / BASE_INTRO.name
NEW_MATERIALS = DERIVED / BASE_MATERIALS.name
OVERLAP_SOURCE = OUT / "overlap_check_bgo_same_envelope.source"
OVERLAP_LOG = OUT / "overlap_check.log"
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
MEGALIB_MATERIALS = MEGALIB / "resource/examples/geomega/materials/Materials.geo"

CSI_MATERIAL_RE = re.compile(r"^(?P<volume>[A-Za-z0-9_]+)\.Material\s+CsI\s*$")
SENSITIVE_RE = re.compile(r"(?m)^.*\.SensitiveVolume\s+(\S+)\s*$")
VOLUME_RE = re.compile(r"(?m)^Volume\s+(\S+)\s*$")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def load_audit_module() -> Any:
    spec = importlib.util.spec_from_file_location("fix5_static_audit", AUDIT_FIX5)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {AUDIT_FIX5}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def parse_bgo_material() -> dict[str, Any]:
    text = MEGALIB_MATERIALS.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    rows: list[str] = []
    capture = False
    for line in lines:
        if re.match(r"^Material\s+BGO\s*$", line.strip()):
            capture = True
            rows.append(line)
            continue
        if capture and line.startswith("Material "):
            break
        if capture:
            rows.append(line)
    density = None
    components = []
    for line in rows:
        m_density = re.match(r"^BGO\.Density\s+([-+0-9.eE]+)\s*$", line.strip())
        if m_density:
            density = float(m_density.group(1))
        m_comp = re.match(r"^BGO\.Component\s+(\S+)\s+([-+0-9.eE]+)\s*$", line.strip())
        if m_comp:
            components.append({"element": m_comp.group(1), "stoichiometry": float(m_comp.group(2))})
    return {
        "status": "PASS" if rows and density is not None and components else "BLOCKED_MATERIAL",
        "authority": str(MEGALIB_MATERIALS),
        "density_g_cm3": density,
        "components": components,
        "definition_lines": rows,
    }


def is_parser_active_volume(volume: str) -> bool:
    upper = volume.upper()
    return upper.startswith("CSI_") or "ACTIVE_SHIELD" in upper or "CEBR3" in upper or "BGO" in upper


def derive_geometry() -> tuple[list[str], list[dict[str, Any]]]:
    DERIVED.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BASE_INTRO, NEW_INTRO)
    shutil.copy2(BASE_MATERIALS, NEW_MATERIALS)
    shutil.copy2(BASE_DET, NEW_DET)

    base_geo = BASE_GEO.read_text(encoding="utf-8", errors="replace")
    volumes = []
    out_lines = []
    for line in base_geo.splitlines():
        match = CSI_MATERIAL_RE.match(line)
        if match:
            volume = match.group("volume")
            volumes.append(volume)
            out_lines.append(f"{volume}.Material BGO")
        else:
            out_lines.append(line)
    NEW_GEO.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    sphere_line = next(
        line for line in BASE_SETUP.read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("SurroundingSphere ")
    )
    setup = "\n".join(
        [
            f"Name {NEW_STEM}",
            "Version 1",
            f"Include {NEW_GEO.name}",
            f"Include {NEW_DET.name}",
            sphere_line,
        ]
    )
    NEW_SETUP.write_text(setup + "\n", encoding="utf-8")

    det_text = BASE_DET.read_text(encoding="utf-8", errors="replace")
    sensitive = sorted(set(SENSITIVE_RE.findall(det_text)))
    all_active = sorted(vol for vol in sensitive if is_parser_active_volume(vol))
    rows = []
    replaced = set(volumes)
    for vol in sorted(set(volumes) | set(all_active)):
        rows.append(
            {
                "volume": vol,
                "baseline_material": "CsI" if vol in replaced else "unchanged_non_CsI",
                "derived_material": "BGO" if vol in replaced else "unchanged",
                "material_replaced": vol in replaced,
                "parser_active_veto_volume": is_parser_active_volume(vol),
                "det_sensitive_ref_present": vol in sensitive,
                "legacy_volume_name_with_BGO_material": vol in replaced,
            }
        )
    return volumes, rows


def compare_geo(allowlist: set[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base_lines = BASE_GEO.read_text(encoding="utf-8", errors="replace").splitlines()
    new_lines = NEW_GEO.read_text(encoding="utf-8", errors="replace").splitlines()
    diff_rows = []
    problems = []
    if len(base_lines) != len(new_lines):
        problems.append(f"geo_line_count_changed:{len(base_lines)}->{len(new_lines)}")
    for idx, (base, new) in enumerate(zip(base_lines, new_lines), start=1):
        if base == new:
            continue
        m = CSI_MATERIAL_RE.match(base)
        whitelisted = bool(m and m.group("volume") in allowlist and new == f"{m.group('volume')}.Material BGO")
        if not whitelisted:
            problems.append(f"non_whitelisted_geo_diff_line_{idx}")
        diff_rows.append(
            {
                "line": idx,
                "volume": m.group("volume") if m else "",
                "baseline": base,
                "derived": new,
                "whitelisted_material_change": whitelisted,
            }
        )

    restored = []
    for line in new_lines:
        m = re.match(r"^(?P<volume>[A-Za-z0-9_]+)\.Material\s+BGO\s*$", line)
        if m and m.group("volume") in allowlist:
            restored.append(f"{m.group('volume')}.Material CsI")
        else:
            restored.append(line)
    normalized_equal = sha256_text("\n".join(base_lines) + "\n") == sha256_text("\n".join(restored) + "\n")
    if not normalized_equal:
        problems.append("normalized_geo_not_hash_equivalent_after_material_restore")
    summary = {
        "geo_line_count_baseline": len(base_lines),
        "geo_line_count_derived": len(new_lines),
        "diff_count": len(diff_rows),
        "whitelisted_diff_count": sum(1 for row in diff_rows if row["whitelisted_material_change"]),
        "non_whitelisted_diff_count": sum(1 for row in diff_rows if not row["whitelisted_material_change"]),
        "normalized_geo_hash_equivalent_after_material_restore": normalized_equal,
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
    }
    return diff_rows, summary


def detector_reference_check(geo_text: str, det_text: str) -> dict[str, Any]:
    volumes = set(VOLUME_RE.findall(geo_text))
    refs = set(SENSITIVE_RE.findall(det_text))
    missing = sorted(ref for ref in refs if ref not in volumes)
    return {
        "sensitive_reference_count": len(refs),
        "volume_count": len(volumes),
        "missing_count": len(missing),
        "missing": missing,
        "pass": len(missing) == 0,
    }


def side_window_audit(geo_text: str, det_text: str) -> dict[str, Any]:
    mod = load_audit_module()
    side_rows = [mod.audit_side_cut(geo_text, name, rin, rout) for name, rin, rout in mod.SIDE_CUTS]
    magnetic = mod.audit_magnetic_incident(geo_text, det_text)
    return {
        "side_window_through_cut_audit": {"rows": side_rows, "pass": all(bool(row["pass"]) for row in side_rows)},
        "magnetic_incident_audit": {**magnetic, "pass": all(bool(value) for value in magnetic.values())},
        "csi_bottom_side_seam_audit": mod.audit_csi_seam(geo_text),
    }


def write_overlap_source() -> None:
    source = f"""Version                     1
Geometry                    {NEW_SETUP.resolve()}
CheckForOverlaps            10000 0.0001
PhysicsListEM               LivermorePol
Run Minimum
Minimum.FileName            /tmp/DelMe_bgo_same_envelope_overlap
Minimum.NEvents             1
Minimum.Source MinimumS
MinimumS.ParticleType       1
MinimumS.Beam               PointSource 0 0 0
MinimumS.Spectrum           Mono 511
MinimumS.Flux               1.0
"""
    OVERLAP_SOURCE.write_text(source, encoding="utf-8")


def cosima_env() -> dict[str, str]:
    env = os.environ.copy()
    env["MEGALIB"] = str(MEGALIB)
    g4 = MEGALIB / "external/geant4_v10.02.p03"
    g4_data = g4 / "share/Geant4-10.2.3/data"
    lib_parts = [
        str(MEGALIB / "lib"),
        str(MEGALIB / "external/root_v6.36.6/lib"),
        str(g4 / "lib"),
    ]
    existing = env.get("LD_LIBRARY_PATH")
    if existing:
        lib_parts.append(existing)
    env["LD_LIBRARY_PATH"] = ":".join(lib_parts)
    env["PATH"] = f"{MEGALIB / 'bin'}:{env.get('PATH', '')}"
    env.update(
        {
            "G4NEUTRONHPDATA": str(g4_data / "G4NDL4.5"),
            "G4LEDATA": str(g4_data / "G4EMLOW6.48"),
            "G4LEVELGAMMADATA": str(g4_data / "PhotonEvaporation3.2"),
            "G4RADIOACTIVEDATA": str(g4_data / "RadioactiveDecay4.3.2"),
            "G4NEUTRONXSDATA": str(g4_data / "G4NEUTRONXS1.4"),
            "G4PIIDATA": str(g4_data / "G4PII1.3"),
            "G4REALSURFACEDATA": str(g4_data / "RealSurface1.0"),
            "G4SAIDXSDATA": str(g4_data / "G4SAIDDATA1.1"),
            "G4ABLADATA": str(g4_data / "G4ABLA3.0"),
            "G4ENSDFSTATEDATA": str(g4_data / "G4ENSDFSTATE1.2.3"),
        }
    )
    return env


def run_overlap() -> dict[str, Any]:
    write_overlap_source()
    if not COSIMA.exists():
        OVERLAP_LOG.write_text(f"ERROR: missing cosima executable: {COSIMA}\n", encoding="utf-8")
        return {"status": "MISSING_COSIMA", "returncode": None, "log": rel(OVERLAP_LOG), "problems": ["missing_cosima"]}
    proc = subprocess.run(
        [str(COSIMA), str(OVERLAP_SOURCE)],
        cwd=ROOT,
        env=cosima_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=300,
    )
    OVERLAP_LOG.write_text(proc.stdout, encoding="utf-8")
    forbidden = {
        "GeomVol": "GeomVol",
        "Overlap": "Overlap",
        "Fatal": "Fatal",
        "Exception": "Exception",
    }
    problems = [label for label, pattern in forbidden.items() if pattern in proc.stdout]
    if "Summary for run Minimum" not in proc.stdout:
        problems.append("missing_summary_for_run_minimum")
    if proc.returncode != 0:
        problems.append(f"returncode_{proc.returncode}")
    return {
        "status": "PASS" if not problems else "FAIL",
        "returncode": proc.returncode,
        "source": rel(OVERLAP_SOURCE),
        "log": rel(OVERLAP_LOG),
        "contains_summary_for_run_minimum": "Summary for run Minimum" in proc.stdout,
        "forbidden_keyword_hits": [label for label, pattern in forbidden.items() if pattern in proc.stdout],
        "problems": problems,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# WP04 BGO Same-Envelope Geometry",
        "",
        f"Status: `{payload['status']}`.",
        "",
        f"Material replaced volumes: `{payload['checks']['material_replaced_volume_count']}`.",
        f"Non-whitelisted geometry diffs: `{payload['geometry_diff']['non_whitelisted_diff_count']}`.",
        f"Detector missing refs: `{payload['det_reference_check']['missing_count']}`.",
        f"Overlap status: `{payload['overlap_check']['status']}`.",
        "",
        "Outputs:",
        f"- derived setup: `{payload['outputs']['derived_setup']}`",
        f"- shield volume map: `{payload['outputs']['shield_volume_map_csv']}`",
        f"- geometry diff whitelist: `{payload['outputs']['geometry_diff_whitelist_csv']}`",
        f"- overlap log: `{payload['overlap_check']['log']}`",
    ]
    if payload["problems"]:
        lines.extend(["", "Problems:"])
        lines.extend(f"- {item}" for item in payload["problems"])
    return "\n".join(lines) + "\n"


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    material = parse_bgo_material()
    if material["status"] != "PASS":
        payload = {
            "artifact_type": "wp04_bgo_same_envelope_geometry",
            "status": "BLOCKED_MATERIAL",
            "created_utc": now_utc(),
            "bgo_material_authority": material,
            "problems": ["BGO material not found in MEGAlib material authority"],
        }
        write_json(OUT / "bgo_geometry_manifest.json", payload)
        return payload

    replaced_volumes, shield_rows = derive_geometry()
    shield_csv = OUT / "shield_volume_map.csv"
    write_csv(shield_csv, shield_rows)

    diff_rows, diff_summary = compare_geo(set(replaced_volumes))
    diff_csv = OUT / "geometry_diff_whitelist.csv"
    write_csv(diff_csv, diff_rows)

    geo_text = NEW_GEO.read_text(encoding="utf-8", errors="replace")
    det_text = NEW_DET.read_text(encoding="utf-8", errors="replace")
    det_check = detector_reference_check(geo_text, det_text)
    side_audit = side_window_audit(geo_text, det_text)
    overlap = run_overlap()

    setup_sphere_baseline = [line for line in BASE_SETUP.read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("SurroundingSphere ")]
    setup_sphere_derived = [line for line in NEW_SETUP.read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("SurroundingSphere ")]
    det_same = sha256(BASE_DET) == sha256(NEW_DET)
    intro_same = sha256(BASE_INTRO) == sha256(NEW_INTRO)
    materials_same = sha256(BASE_MATERIALS) == sha256(NEW_MATERIALS)
    problems = []
    if diff_summary["status"] != "PASS":
        problems.extend(diff_summary["problems"])
    if not det_check["pass"]:
        problems.append("detector_reference_check_failed")
    if not side_audit["side_window_through_cut_audit"]["pass"]:
        problems.append("side_window_audit_failed")
    if not side_audit["magnetic_incident_audit"]["pass"]:
        problems.append("magnetic_incident_audit_failed")
    if not side_audit["csi_bottom_side_seam_audit"]["pass"]:
        problems.append("csi_bottom_side_seam_audit_failed")
    if overlap["status"] != "PASS":
        problems.append("overlap_check_failed")
    if setup_sphere_baseline != setup_sphere_derived:
        problems.append("surrounding_sphere_changed")
    if not det_same:
        problems.append("det_file_changed")
    if not intro_same or not materials_same:
        problems.append("support_include_file_changed")
    if len(replaced_volumes) != 24:
        problems.append(f"unexpected_material_replaced_volume_count_{len(replaced_volumes)}")

    payload = {
        "artifact_type": "wp04_bgo_same_envelope_geometry",
        "status": "PASS_BGO_SAME_ENVELOPE_GEOMETRY" if not problems else "FAIL_GEOMETRY_DIFF",
        "created_utc": now_utc(),
        "inputs": {
            "baseline_geo": rel(BASE_GEO),
            "baseline_det": rel(BASE_DET),
            "baseline_setup": rel(BASE_SETUP),
            "baseline_intro": rel(BASE_INTRO),
            "baseline_materials": rel(BASE_MATERIALS),
        },
        "outputs": {
            "derived_geo": rel(NEW_GEO),
            "derived_det": rel(NEW_DET),
            "derived_setup": rel(NEW_SETUP),
            "shield_volume_map_csv": rel(shield_csv),
            "geometry_diff_whitelist_csv": rel(diff_csv),
            "manifest_json": rel(OUT / "bgo_geometry_manifest.json"),
            "manifest_md": rel(OUT / "bgo_geometry_manifest.md"),
        },
        "bgo_material_authority": material,
        "checks": {
            "material_replaced_volume_count": len(replaced_volumes),
            "parser_active_volume_count": sum(1 for row in shield_rows if row["parser_active_veto_volume"]),
            "legacy_volume_name_with_BGO_material": True,
            "det_file_hash_equal": det_same,
            "intro_file_hash_equal": intro_same,
            "materials_file_hash_equal": materials_same,
            "setup_surrounding_sphere_equal": setup_sphere_baseline == setup_sphere_derived,
            "setup_surrounding_sphere": setup_sphere_derived[0] if setup_sphere_derived else "",
        },
        "geometry_diff": diff_summary,
        "det_reference_check": det_check,
        "side_window_audit": side_audit,
        "overlap_check": overlap,
        "problems": problems,
    }
    write_json(OUT / "bgo_material_authority.json", material)
    write_json(OUT / "bgo_geometry_manifest.json", payload)
    write_json(OUT / "summary.json", payload)
    md = markdown(payload)
    (OUT / "bgo_geometry_manifest.md").write_text(md, encoding="utf-8")
    (OUT / "summary.md").write_text(md, encoding="utf-8")
    return payload


def main() -> int:
    payload = build()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "derived_setup": payload.get("outputs", {}).get("derived_setup"),
                "material_replaced_volume_count": payload.get("checks", {}).get("material_replaced_volume_count"),
                "overlap_status": payload.get("overlap_check", {}).get("status"),
                "problems": payload.get("problems", []),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if str(payload["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
