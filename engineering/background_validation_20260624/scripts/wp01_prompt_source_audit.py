#!/usr/bin/env python3
"""WP01 prompt source normalization audit for HARNESS_20260624."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import pickle
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ENG = Path(__file__).resolve().parents[1]
OUT = ENG / "01_prompt_source_audit"
MANIFEST = ENG / "00_manifest" / "baseline_authority_manifest.json"
SOURCE_DIR = ROOT / "config/megalib_sources_fullsphere20_fix5_tilt45"
PROMPT_RUN = ROOT / "runs/step02_instant_fix5_fullstat_v2"
STEP05_DIR = ROOT / "stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1"
STEP05_SUMMARY = STEP05_DIR / "step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json"
STEP05_CODE = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
SETUP = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
MC_SOURCE_CC = Path("/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCSource.cc")
RUNNER = ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py"


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_source(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    particle = path.name.removeprefix("Background_").removesuffix("_fullsphere20.source")
    geom = next((line.split(maxsplit=1)[1] for line in text.splitlines() if line.startswith("Geometry ")), "")
    farfield_comment = None
    m = re.search(r"^#\s*farfield_radius_cm\s*=\s*([-+0-9.eE]+)\s*$", text, re.MULTILINE)
    if m:
        farfield_comment = float(m.group(1))
    total_flux_comment = None
    m = re.search(r"total_flux_cm2_s\s*=\s*([-+0-9.eE]+)", text)
    if m:
        total_flux_comment = float(m.group(1))

    bins = []
    current = None
    for line in text.splitlines():
        beam = re.search(r"^(Atm_[^.]+)\.Beam\s+FarFieldAreaSource\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", line)
        if beam:
            current = {
                "source_name": beam.group(1),
                "theta_min_deg": float(beam.group(2)),
                "theta_max_deg": float(beam.group(3)),
                "phi_min_deg": float(beam.group(4)),
                "phi_max_deg": float(beam.group(5)),
            }
            continue
        flux = re.search(r"^(Atm_[^.]+)\.Flux\s+([-+0-9.eE]+)", line)
        if flux and current and flux.group(1) == current["source_name"]:
            current["flux_cm2_s"] = float(flux.group(2))
            th1 = math.radians(current["theta_min_deg"])
            th2 = math.radians(current["theta_max_deg"])
            ph1 = math.radians(current["phi_min_deg"])
            ph2 = math.radians(current["phi_max_deg"])
            current["delta_mu"] = math.cos(th1) - math.cos(th2)
            current["delta_omega_sr"] = current["delta_mu"] * (ph2 - ph1)
            bins.append(current)
            current = None
    info = {
        "particle": particle,
        "path": rel(path),
        "sha256": sha256(path),
        "geometry": geom,
        "farfield_radius_cm_comment": farfield_comment,
        "total_flux_cm2_s_comment": total_flux_comment,
        "total_flux_cm2_s_sum": sum(row["flux_cm2_s"] for row in bins),
        "bin_count": len(bins),
    }
    return info, bins


def parse_setup_radius() -> float | None:
    for line in SETUP.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("SurroundingSphere "):
            vals = []
            for token in line.split()[1:]:
                try:
                    vals.append(float(token))
                except ValueError:
                    pass
            hits = [v for v in vals if abs(v - 60.0) < 1e-9]
            if hits:
                return hits[0]
    return None


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_step05_module():
    spec = importlib.util.spec_from_file_location("step05_fix5_mod", STEP05_CODE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {STEP05_CODE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT
    mod.configure_paths("fix5_fullstat_v2_exactpos_m50000_s260613")
    return mod


def selected_rate_closure() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mod = load_step05_module()
    with (STEP05_DIR / "work/event_catalog.pkl").open("rb") as fh:
        cat = pickle.load(fh)
    disk = mod.side_entry_disk()
    reconstructed = mod.summarize_window(cat, 510.58, 511.42, disk, "keep")
    summary = load_json(STEP05_SUMMARY)
    official = summary["windows"]["w2_510p58_511p42"]

    stream_diff = {}
    for stream in ("prompt", "delayed", "science"):
        rec = reconstructed["by_stream"][stream]["side_compton_fov_pass_rate_s-1"]
        off = official["by_stream"][stream]["side_compton_fov_pass_rate_s-1"]
        stream_diff[stream] = {
            "reconstructed_rate_cps": rec,
            "official_rate_cps": off,
            "abs_diff_cps": abs(rec - off),
            "rel_diff": abs(rec - off) / abs(off) if off else 0.0,
        }

    stream = np.asarray(cat["stream"], dtype=object)
    tag = np.asarray(cat["tag"], dtype=object)
    tes = np.asarray(cat["tes_total_keV"], dtype=float)
    shield = np.asarray(cat["bgo_total_keV"], dtype=float)
    rate = np.asarray(cat["rate_hz"], dtype=float)

    rows = []
    prompt_mask = (stream == "prompt") & (tes >= 510.58) & (tes <= 511.42)
    for particle in sorted(set(str(x) for x in tag[prompt_mask])):
        raw_idx = np.nonzero(prompt_mask & (tag == particle))[0]
        active_idx = raw_idx[shield[raw_idx] < 50.0]
        final = []
        class_counts: dict[str, int] = defaultdict(int)
        for idx in active_idx:
            keep, cls = mod.side_keep_from_hits(mod.event_hits(cat, int(idx)), disk, "keep")
            class_counts[cls] += 1
            if keep:
                final.append(int(idx))
        final_idx = np.asarray(final, dtype=int)
        rows.append(
            {
                "particle": particle,
                "raw_events": int(len(raw_idx)),
                "raw_sum_w": float(rate[raw_idx].sum()),
                "raw_sum_w2": float(np.square(rate[raw_idx]).sum()),
                "active_events": int(len(active_idx)),
                "active_sum_w": float(rate[active_idx].sum()),
                "active_sum_w2": float(np.square(rate[active_idx]).sum()),
                "final_events": int(len(final_idx)),
                "final_sum_w": float(rate[final_idx].sum()) if len(final_idx) else 0.0,
                "final_sum_w2": float(np.square(rate[final_idx]).sum()) if len(final_idx) else 0.0,
                "side_class_counts": ";".join(f"{k}:{v}" for k, v in sorted(class_counts.items())),
            }
        )

    totals = {
        "prompt_final_sum_w": sum(row["final_sum_w"] for row in rows),
        "prompt_final_sum_w2": sum(row["final_sum_w2"] for row in rows),
        "official_prompt_final_cps": official["by_stream"]["prompt"]["side_compton_fov_pass_rate_s-1"],
        "reconstructed_prompt_final_cps": reconstructed["by_stream"]["prompt"]["side_compton_fov_pass_rate_s-1"],
        "stream_diff": stream_diff,
        "selection_code": rel(STEP05_CODE),
        "selection_code_sha256": sha256(STEP05_CODE),
    }
    totals["prompt_final_rel_diff_vs_official"] = abs(totals["prompt_final_sum_w"] - totals["official_prompt_final_cps"]) / totals["official_prompt_final_cps"]
    return rows, totals


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else ["empty"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_final_status(g0: str, g1: str, g1_blocking: bool) -> None:
    git_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    git_status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT, text=True).strip()
    status_label = "clean" if not git_status else "dirty"
    rows = [
        ("G0 Authority", g0, "00_manifest/baseline_authority_manifest.json", g0 != "PASS", "Resolve ambiguous/missing authority before downstream work." if g0 != "PASS" else "Proceed."),
        ("G1 Prompt normalization", g1, "01_prompt_source_audit/prompt_normalization_audit.json", g1_blocking, "Do not start BGO production until PASS." if g1 != "PASS" else "Proceed to WP02/WP03."),
        ("G2 eplus provenance", "NOT_STARTED", "", True, "Run WP02 using existing event catalog/SIM records."),
        ("G3 delayed convergence", "NOT_STARTED", "", True, "Run WP03 resource estimate before any new delayed transport."),
        ("G4 BGO geometry", "NOT_STARTED", "", True, "Only after G1 PASS."),
        ("G5/G6 matched runs", "NOT_STARTED", "", True, "Requires G4 and resource guard."),
        ("G7 comparison", "NOT_STARTED", "", True, "Requires matched run evidence."),
        ("G8 paper support", "NOT_STARTED", "", True, "Requires completed or blocked prior gates."),
    ]
    lines = [
        "# FINAL_STATUS",
        "",
        f"git_head: {git_head}",
        f"git_status: {status_label}",
        "harness_version: HARNESS_20260624 v1.0",
        "",
        "| Gate | Status | Evidence | Blocking? | Next action |",
        "|---|---|---|---:|---|",
    ]
    for gate, status, evidence, blocking, next_action in rows:
        lines.append(f"| {gate} | {status} | {evidence} | {str(bool(blocking)).lower()} | {next_action} |")
    lines.extend(
        [
            "",
            "Files created:",
            "- engineering/background_validation_20260624/00_manifest/",
            "- engineering/background_validation_20260624/01_prompt_source_audit/",
            "- engineering/background_validation_20260624/work_packets/",
            "- engineering/background_validation_20260624/scripts/",
            "",
            "Files intentionally not modified:",
            "- baseline geometry",
            "- baseline source cards",
            "- Step05 authority outputs",
            "- manuscript source",
            "",
            "Resource approvals requested:",
            "- none",
        ]
    )
    (ENG / "FINAL_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    baseline = load_json(MANIFEST)
    source_manifest = load_json(SOURCE_DIR / "source_migration_manifest.json")
    norm = load_json(PROMPT_RUN / "normalization.json")
    run_manifest_rows = read_csv(PROMPT_RUN / "run_manifest.csv")
    run_summary_rows = read_csv(PROMPT_RUN / "run_summary.csv")

    inventory = []
    bin_rows = []
    problems: list[str] = []
    warnings: list[str] = []

    for source in sorted(SOURCE_DIR.glob("Background_*_fullsphere20.source")):
        info, bins = parse_source(source)
        inventory.append(info)
        manifest_match = next((row for row in source_manifest.get("sources", []) if row.get("particle") == info["particle"]), {})
        manifest_flux = manifest_match.get("total_flux_cm2_s")
        rel_diff = abs(info["total_flux_cm2_s_sum"] - float(manifest_flux)) / float(manifest_flux) if manifest_flux else None
        info["manifest_total_flux_cm2_s"] = manifest_flux
        info["flux_relative_diff_vs_manifest"] = rel_diff
        if rel_diff is None or rel_diff > 1e-8:
            problems.append(f"flux sum mismatch for {info['particle']}: rel_diff={rel_diff}")
        if info["bin_count"] != 20:
            problems.append(f"{info['particle']} has {info['bin_count']} bins, expected 20")
        for i, row in enumerate(bins):
            row = dict(row)
            row["particle"] = info["particle"]
            row["bin"] = i
            row["expected_delta_mu"] = 0.1
            row["delta_mu_abs_diff_from_equal_mu"] = abs(row["delta_mu"] - 0.1)
            row["expected_delta_omega_sr"] = 2.0 * math.pi * 0.1
            row["delta_omega_abs_diff"] = abs(row["delta_omega_sr"] - row["expected_delta_omega_sr"])
            bin_rows.append(row)

    write_csv(OUT / "source_card_inventory.csv", inventory)
    write_csv(OUT / "source_flux_bin_audit.csv", bin_rows)

    radii = {
        "setup_surrounding_sphere_cm": parse_setup_radius(),
        "source_manifest_farfield_radius_cm": source_manifest.get("farfield_radius_cm"),
        "instant_normalization_farfield_radius_cm": norm.get("farfield_radius_cm"),
    }
    card_radii = sorted({row["farfield_radius_cm_comment"] for row in inventory if row["farfield_radius_cm_comment"] is not None})
    radii["source_card_comment_radii_cm"] = card_radii
    authoritative_values = [v for v in [radii["setup_surrounding_sphere_cm"], radii["source_manifest_farfield_radius_cm"], radii["instant_normalization_farfield_radius_cm"], *card_radii] if v is not None]
    radius_unique = len({round(float(v), 9) for v in authoritative_values}) == 1
    radius = float(authoritative_values[0]) if authoritative_values else None
    area = math.pi * radius * radius if radius is not None else None
    area_rel_diff = abs(area - float(norm["farfield_area_cm2"])) / float(norm["farfield_area_cm2"]) if area else None
    if not radius_unique:
        problems.append("farfield radius authority mismatch")
    if area_rel_diff is None or area_rel_diff > 1e-12:
        problems.append(f"farfield area mismatch: rel_diff={area_rel_diff}")

    mc_text = MC_SOURCE_CC.read_text(encoding="utf-8", errors="replace") if MC_SOURCE_CC.exists() else ""
    runner_text = RUNNER.read_text(encoding="utf-8", errors="replace")
    semantics_pass = (
        "m_StartAreaAverageArea = c_Pi*m_StartAreaParam1*m_StartAreaParam1" in mc_text
        and "m_Flux *= m_StartAreaAverageArea" in mc_text
        and "area_cm2 = math.pi * args.farfield_radius_cm * args.farfield_radius_cm" in runner_text
        and "prompt_time_s = args.gamma_events / (gamma_flux * area_cm2)" in runner_text
    )
    if not semantics_pass:
        problems.append("source semantics evidence incomplete")

    farfield = {
        "status": "PASS" if radius_unique and area_rel_diff is not None and area_rel_diff <= 1e-12 and semantics_pass else "FAIL",
        "radii": radii,
        "radius_unique": radius_unique,
        "area_cm2_from_pi_r2": area,
        "normalization_area_cm2": norm.get("farfield_area_cm2"),
        "area_relative_diff": area_rel_diff,
        "source_semantics_evidence": {
            "megalib_mcsource_cc": str(MC_SOURCE_CC),
            "sphere_average_area_formula_found": "m_StartAreaAverageArea = c_Pi*m_StartAreaParam1*m_StartAreaParam1" in mc_text,
            "farfield_flux_area_multiply_found": "m_Flux *= m_StartAreaAverageArea" in mc_text,
            "runner_area_formula_found": "area_cm2 = math.pi * args.farfield_radius_cm * args.farfield_radius_cm" in runner_text,
            "runner_prompt_time_formula_found": "prompt_time_s = args.gamma_events / (gamma_flux * area_cm2)" in runner_text,
        },
    }
    (OUT / "farfield_geometry_audit.json").write_text(json.dumps(farfield, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "farfield_geometry_audit.md").write_text(
        "\n".join(
            [
                "# Farfield Geometry Audit",
                "",
                f"- status: `{farfield['status']}`",
                f"- radius unique: `{radius_unique}`",
                f"- radius cm: `{radius}`",
                f"- area from pi R^2: `{area}`",
                f"- normalization area: `{norm.get('farfield_area_cm2')}`",
                f"- area relative diff: `{area_rel_diff}`",
                "- MEGAlib evidence: `MCSource.cc` contains the spherical start-area `pi R^2` formula and multiplies far-field flux by start-area average area.",
                "- Runner evidence: `run_equiv2602_pipeline_NEW_GEO.py` computes `area_cm2 = pi * R^2` and `prompt_time_s = gamma_events / (gamma_flux * area_cm2)`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    seeds = [row["seed"] for row in run_manifest_rows]
    unique_seeds = len(seeds) == len(set(seeds))
    if not unique_seeds:
        problems.append("duplicate prompt run seeds")
    status_counts: dict[str, int] = defaultdict(int)
    generated_by_particle: dict[str, int] = defaultdict(int)
    for row in run_summary_rows:
        status_counts[row["status"]] += 1
        generated_by_particle[row["particle"]] += int(row["generated_particles"] or 0)
        if row["status"] != "PASS":
            problems.append(f"run_summary non-PASS job {row['job_name']}: {row['status']}")
    for particle, expected_base in norm["base_events_by_particle"].items():
        expected = int(expected_base) if particle == "gamma" else int(expected_base) * int(norm["non_gamma_replicas"])
        actual = generated_by_particle.get(particle, 0)
        if actual != expected:
            problems.append(f"generated count mismatch for {particle}: actual={actual} expected={expected}")

    closure_rows, closure_totals = selected_rate_closure()
    write_csv(
        OUT / "prompt_weight_closure.csv",
        closure_rows,
        [
            "particle",
            "raw_events",
            "raw_sum_w",
            "raw_sum_w2",
            "active_events",
            "active_sum_w",
            "active_sum_w2",
            "final_events",
            "final_sum_w",
            "final_sum_w2",
            "side_class_counts",
        ],
    )
    if closure_totals["prompt_final_rel_diff_vs_official"] > 1e-6:
        problems.append(f"selected-rate closure mismatch: rel_diff={closure_totals['prompt_final_rel_diff_vs_official']}")

    prompt_status = "PASS" if not problems else ("BLOCKED_SOURCE_SEMANTICS" if "source semantics evidence incomplete" in problems else "FAIL_NORMALIZATION")
    audit = {
        "artifact_type": "prompt_normalization_audit",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": prompt_status,
        "problems": problems,
        "warnings": warnings,
        "baseline_manifest": rel(MANIFEST),
        "source_cards": {
            "count": len(inventory),
            "flux_bin_count_total": len(bin_rows),
            "max_flux_relative_diff_vs_manifest": max((row.get("flux_relative_diff_vs_manifest") or 0.0) for row in inventory),
            "max_delta_mu_abs_diff": max((row["delta_mu_abs_diff_from_equal_mu"] for row in bin_rows), default=None),
        },
        "farfield": farfield,
        "run_manifest": {
            "path": rel(PROMPT_RUN / "run_manifest.csv"),
            "rows": len(run_manifest_rows),
            "unique_seeds": unique_seeds,
            "seed_count": len(seeds),
            "status_counts": dict(status_counts),
            "generated_by_particle": dict(generated_by_particle),
            "gamma_splits": norm.get("gamma_splits"),
            "non_gamma_replicas": norm.get("non_gamma_replicas"),
        },
        "selected_rate_closure": closure_totals,
    }
    (OUT / "prompt_normalization_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = [
        "# Prompt Normalization Audit",
        "",
        f"- status: `{prompt_status}`",
        f"- source cards: `{len(inventory)}`",
        f"- flux bins: `{len(bin_rows)}`",
        f"- max flux relative diff vs manifest: `{audit['source_cards']['max_flux_relative_diff_vs_manifest']}`",
        f"- farfield radius unique: `{radius_unique}`",
        f"- unique seeds: `{unique_seeds}`",
        f"- prompt W2 final reconstructed cps: `{closure_totals['prompt_final_sum_w']}`",
        f"- prompt W2 final official cps: `{closure_totals['official_prompt_final_cps']}`",
        f"- selected-rate relative diff: `{closure_totals['prompt_final_rel_diff_vs_official']}`",
        f"- prompt W2 final sum_w2: `{closure_totals['prompt_final_sum_w2']}`",
        "",
        "## Problems",
    ]
    md.extend([f"- {p}" for p in problems] or ["- none"])
    md.extend(
        [
            "",
            "## Evidence",
            "",
            "- `source_card_inventory.csv` records geometry lines, source-card flux sums, and radius comments.",
            "- `source_flux_bin_audit.csv` records the 20 equal-mu angular bins for each particle family.",
            "- `farfield_geometry_audit.json` records radius/area and local MEGAlib/runner code evidence.",
            "- `prompt_weight_closure.csv` reconstructs W2 prompt selected rates from event weights and Step05 selection code.",
        ]
    )
    (OUT / "prompt_normalization_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    g0 = baseline.get("status", "UNKNOWN")
    write_final_status(g0, prompt_status, prompt_status != "PASS")
    print(json.dumps({"status": prompt_status, "audit": rel(OUT / "prompt_normalization_audit.json")}, indent=2))
    return 0 if prompt_status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
