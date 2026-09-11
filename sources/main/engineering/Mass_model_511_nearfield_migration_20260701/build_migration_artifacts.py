#!/usr/bin/env python3
"""Build engineering artifacts for the Mass_model_511 MEGAlib geometry migration.

This is a detector-geometry migration package. It does not edit the previous
nearfield engineering run, source authority cards, Step05 cuts, or promoted
mainline geometry. It prepares a new engineering directory whose candidate
geometry is the latest Mass_model_511 MEGAlib setup.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "engineering/Mass_model_511_nearfield_migration_20260701"

MANIFEST_DIR = OUT / "00_manifest"
GEOM_DIR = OUT / "01_geometry"
RUN_PLAN_DIR = OUT / "02_run_plan"
SOURCE_DIR = OUT / "03_source_migration"
BRIDGE_DIR = OUT / "04_bridge_resolution"
MANUSCRIPT_DIR = OUT / "11_manuscript_support"

OLD_ENGINEERING = ROOT / "engineering/nearfield_mass_impact_20260625"
OLD_HARNESS = ROOT / "engineering/harness_20260625/HARNESS_ENGINEERING_A_NF2_OF1_MASS_MODEL_IMPACT.md"
OLD_FINAL = OLD_ENGINEERING / "00_manifest/FINAL_STATUS.md"
OLD_NF2_SETUP = OLD_ENGINEERING / "01_geometry/fixed_candidates/detector_NF2_overlapfix_minimal/DEMO2_DR_fix5_NF2_closedcycle.geo.setup"
OLD_SMOKE_MATRIX = OLD_ENGINEERING / "02_run_plan/smoke_run_matrix.csv"

LATEST_GEOM_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy"
LATEST_REPORT_DIR = ROOT / "outputs/reports/Mass_model_511_stage_diam_300_300_300_350_350_400_20260701"
LATEST_SETUP = LATEST_GEOM_DIR / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
LATEST_GEO = LATEST_GEOM_DIR / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
LATEST_DET = LATEST_GEOM_DIR / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"
LATEST_INTRO = LATEST_GEOM_DIR / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
LATEST_MATERIALS = LATEST_GEOM_DIR / "Materials_DEMO2_DR_v3p5.geo"
LATEST_README = LATEST_GEOM_DIR / "README.md"
LATEST_MANIFEST = LATEST_REPORT_DIR / "Mass_model_511_stage_diam_300_300_300_350_350_400_manifest.json"
LATEST_MASS_AUDIT = LATEST_REPORT_DIR / "Mass_model_511_stage_diam_300_300_300_350_350_400_mass_audit.json"
LATEST_MASS_AUDIT_MD = LATEST_REPORT_DIR / "MASS_MODEL_511_STAGE_DIAM_300_300_300_350_350_400_MASS_AUDIT.md"
LATEST_FINAL_REVIEW = LATEST_REPORT_DIR / "MASS_MODEL_511_STAGE_DIAM_300_300_300_350_350_400_FINAL_REVIEW.md"
LATEST_OVERLAP_LOG = LATEST_REPORT_DIR / "Mass_model_511_stage_diam_300_300_300_350_350_400_overlap_after_support_parent_fix.log"
LATEST_SCHEMATIC = LATEST_REPORT_DIR / "Mass_model_511_stage_diam_300_300_300_350_350_400_2d_schematic.png"
LATEST_WRL = LATEST_REPORT_DIR / "DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400.wrl"

SOURCE_AUTH_DIR = SOURCE_DIR / "source_dirs/Mass_model_511"
SOURCE_AUTH_MANIFEST = SOURCE_AUTH_DIR / "source_migration_manifest.json"

BASELINE_SETUP = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
WORKSPACE_INDEX = ROOT / "core_md/README.md"

BAD_OVERLAP_PATTERNS = [
    "GeomVol",
    "Overlap is detected",
    "overlapping by",
    "G4Exception",
    "Error",
    "Exception",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


GIT_HEAD = git(["rev-parse", "HEAD"])
GIT_STATUS = git(["status", "--short"])
GIT_STATUS_LINES = [line for line in GIT_STATUS.splitlines() if line.strip()]


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def file_record(path: Path, role: str, claim_level: str = "") -> dict[str, Any]:
    rec: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "role": role,
        "claim_level": claim_level,
        "git_head": GIT_HEAD,
        "git_dirty": bool(GIT_STATUS_LINES),
        "git_status_line_count": len(GIT_STATUS_LINES),
    }
    if path.exists() and path.is_file():
        st = path.stat()
        rec.update(
            {
                "sha256": sha256(path),
                "size": st.st_size,
                "mtime_utc": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat(),
            }
        )
    elif path.exists() and path.is_dir():
        files = [p for p in path.rglob("*") if p.is_file()]
        rec.update(
            {
                "type": "directory",
                "file_count": len(files),
                "size": sum(p.stat().st_size for p in files),
                "mtime_utc": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat(),
            }
        )
    return rec


def resolve_include(setup_path: Path, include: str) -> Path:
    if include.startswith("$(MEGALIB)"):
        return Path("/home/ubuntu/MEGAlib_Install/megalib-main") / include.replace("$(MEGALIB)/", "")
    p = Path(include)
    return p if p.is_absolute() else setup_path.parent / p


def parse_setup(setup_path: Path) -> dict[str, Any]:
    includes: list[dict[str, Any]] = []
    surrounding_sphere = None
    name = None
    version = None
    for raw in read_text(setup_path).splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        parts = line.split()
        if parts[0] == "Name" and len(parts) > 1:
            name = parts[1]
        elif parts[0] == "Version" and len(parts) > 1:
            version = parts[1]
        elif parts[0] == "Include" and len(parts) > 1:
            resolved = resolve_include(setup_path, parts[1])
            includes.append(
                {
                    "include": parts[1],
                    "resolved_path": rel(resolved),
                    "exists": resolved.exists(),
                    "sha256": sha256(resolved) if resolved.exists() and resolved.is_file() else None,
                }
            )
        elif parts[0] == "SurroundingSphere" and len(parts) >= 6:
            surrounding_sphere = {
                "raw": line,
                "radius_cm": float(parts[1]),
                "center_cm": [float(parts[2]), float(parts[3]), float(parts[4])],
                "source_radius_cm": float(parts[5]),
            }
    return {
        "path": rel(setup_path),
        "exists": setup_path.exists(),
        "name": name,
        "version": version,
        "sha256": sha256(setup_path),
        "includes": includes,
        "missing_includes": [item for item in includes if not item["exists"]],
        "surrounding_sphere": surrounding_sphere,
    }


def overlap_log_status(path: Path) -> dict[str, Any]:
    text = read_text(path)
    bad = [pattern for pattern in BAD_OVERLAP_PATTERNS if pattern in text]
    return {
        "path": rel(path),
        "exists": path.exists(),
        "sha256": sha256(path),
        "bad_patterns": bad,
        "has_summary": "Summary for run Minimum" in text,
        "has_stage12": "Stage 12" in text,
        "status": "PASS" if path.exists() and not bad and "Summary for run Minimum" in text else "FAIL",
    }


def final_review_status(path: Path) -> dict[str, Any]:
    text = read_text(path)
    checks = {
        "overlap_clean_claim": "overlap check passed" in text or "is clean after the support-parent repair" in text,
        "side_window_axis_passed": "Side-window axis check passed" in text,
        "side_wall_closure_represented_layers_passed": "Window-exterior side-wall closure check passed" in text,
        "passive_side_wall_caveat_present": "Passive side-wall caveat" in text,
    }
    return {
        "path": rel(path),
        "exists": path.exists(),
        "sha256": sha256(path),
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "WARN",
    }


def patch_source_text(text: str, geometry_setup: str) -> str:
    out: list[str] = []
    geometry_lines = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# geometry_setup="):
            out.append(f"# geometry_setup={geometry_setup}")
        elif stripped.startswith("Geometry "):
            out.append(f"Geometry {geometry_setup}")
            geometry_lines += 1
        else:
            out.append(line)
    if geometry_lines != 1:
        raise ValueError(f"Expected exactly one Geometry line, found {geometry_lines}")
    return "\n".join(out) + "\n"


def prepare_source_cards(candidate_setup_rel: str) -> dict[str, Any]:
    target_dir = SOURCE_AUTH_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    sources = sorted(target_dir.glob("Background_*_fullsphere20.source"))
    if not sources:
        raise FileNotFoundError(f"missing package-local Mass_model_511 source cards in {target_dir}")

    copied: list[str] = []
    for source in sources:
        source.write_text(
            patch_source_text(source.read_text(encoding="utf-8", errors="replace"), candidate_setup_rel),
            encoding="utf-8",
        )
        copied.append(rel(source))

    manifest = read_json(SOURCE_AUTH_MANIFEST) or {}
    manifest.update(
        {
            "status": "PASS_MASS_MODEL_511_GEOMETRY_SOURCE_COPY_PREPARED_NO_AUTHORITY_EDIT",
            "label": "Mass_model_511_nearfield_migration_20260701",
            "source_dir": rel(target_dir),
            "authority_source_dir": "package-local cleaned checkout source copy",
            "geometry_setup": candidate_setup_rel,
            "change_scope": "Package-local source copy; changed only geometry_setup comments and MEGAlib Geometry lines.",
            "old_nearfield_candidate_setup_replaced": rel(OLD_NF2_SETUP),
            "new_candidate_setup": candidate_setup_rel,
        }
    )
    for item in manifest.get("sources", []):
        source_name = Path(item.get("source", "")).name
        item["authority_source"] = "legacy top-level source authority removed in cleaned checkout; package-local copy retained"
        item["source"] = rel(target_dir / source_name)
        item["geometry_setup"] = candidate_setup_rel
    write_json(target_dir / "source_migration_manifest.json", manifest)

    return {
        "status": "PASS",
        "source_dir": rel(target_dir),
        "source_count": len(copied),
        "source_files": copied,
        "manifest": rel(target_dir / "source_migration_manifest.json"),
    }


def build_run_matrix(candidate_setup_rel: str) -> None:
    rows: list[dict[str, Any]] = []
    if OLD_SMOKE_MATRIX.exists():
        with OLD_SMOKE_MATRIX.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            for row in reader:
                out = dict(row)
                if out.get("branch") == "candidate_nf2":
                    out["branch"] = "candidate_Mass_model_511"
                    out["geometry_setup"] = candidate_setup_rel
                    out["execution_status"] = "PLANNED_NOT_RUN"
                rows.append(out)
        write_csv(RUN_PLAN_DIR / "smoke_run_matrix.csv", rows, fields)
    else:
        write_csv(
            RUN_PLAN_DIR / "smoke_run_matrix.csv",
            [{"branch": "candidate_Mass_model_511", "geometry_setup": candidate_setup_rel, "execution_status": "PLANNED_NOT_RUN"}],
            ["branch", "geometry_setup", "execution_status"],
        )

    write_csv(
        RUN_PLAN_DIR / "bridge_and_fullstat_release.csv",
        [
            {
                "gate": "G1_geometry",
                "status": "GEOMETRY_PASS_REUSED_FROM_MASS_MODEL_511_REVIEW",
                "blocking": "no",
                "notes": "Latest Mass_model_511 geometry already has clean cosima overlap after support-parent repair.",
            },
            {
                "gate": "G2_source_migration",
                "status": "SOURCE_COPY_PREPARED",
                "blocking": "no",
                "notes": "Authority source cards are copied locally and only Geometry lines are changed.",
            },
            {
                "gate": "G5_optics_bridge",
                "status": "OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY",
                "blocking": "no",
                "notes": "This branch has no independent OF1 optics local geometry; the Mass_model_511 mass is loaded directly in detector geometry.",
            },
            {
                "gate": "G3_G4_transport",
                "status": "NOT_RUN",
                "blocking": "requires resource authorization",
                "notes": "Prompt/buildup/delayed transport can reuse the old paired workflow with candidate_Mass_model_511.",
            },
        ],
        ["gate", "status", "blocking", "notes"],
    )


def mass_summary() -> dict[str, Any]:
    audit = read_json(LATEST_MASS_AUDIT) or {}
    return {
        "heavy_total_with_csi_kg": audit.get("heavy", {}).get("mass_with_csi_kg"),
        "heavy_total_without_csi_kg": audit.get("heavy", {}).get("mass_without_csi_kg"),
        "baseline_without_csi_kg": audit.get("baseline", {}).get("mass_without_csi_kg"),
        "delta_without_csi_kg": audit.get("delta", {}).get("mass_without_csi_kg"),
        "heavy_major_categories": audit.get("heavy", {}).get("category_masses_kg", {}),
    }


def build() -> None:
    for directory in [MANIFEST_DIR, GEOM_DIR, RUN_PLAN_DIR, SOURCE_DIR, BRIDGE_DIR, MANUSCRIPT_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    generated = now_utc()
    candidate_setup_rel = rel(LATEST_SETUP)
    latest_setup = parse_setup(LATEST_SETUP)
    source_cards = prepare_source_cards(candidate_setup_rel)
    build_run_matrix(candidate_setup_rel)

    overlap = overlap_log_status(LATEST_OVERLAP_LOG)
    review = final_review_status(LATEST_FINAL_REVIEW)
    geometry_status = "GEOMETRY_PASS" if latest_setup["exists"] and not latest_setup["missing_includes"] and overlap["status"] == "PASS" else "BLOCKED_GEOMETRY"

    authority_files = [
        file_record(OLD_HARNESS, "PREVIOUS_NEARFIELD_HARNESS_TEMPLATE"),
        file_record(OLD_FINAL, "PREVIOUS_NEARFIELD_FINAL_STATUS"),
        file_record(OLD_NF2_SETUP, "OLD_DETECTOR_NEARFIELD_CANDIDATE_REPLACED"),
        file_record(BASELINE_SETUP, "BASELINE_FIX5_DETECTOR_REFERENCE"),
        file_record(LATEST_SETUP, "NEW_MASS_MODEL_511_CANDIDATE_SETUP"),
        file_record(LATEST_GEO, "NEW_MASS_MODEL_511_CANDIDATE_GEO"),
        file_record(LATEST_DET, "NEW_MASS_MODEL_511_CANDIDATE_DET"),
        file_record(LATEST_INTRO, "NEW_MASS_MODEL_511_CANDIDATE_INTRO"),
        file_record(LATEST_MATERIALS, "NEW_MASS_MODEL_511_CANDIDATE_MATERIALS"),
        file_record(LATEST_README, "NEW_MASS_MODEL_511_CANDIDATE_README"),
        file_record(LATEST_MANIFEST, "NEW_MASS_MODEL_511_MANIFEST"),
        file_record(LATEST_MASS_AUDIT, "NEW_MASS_MODEL_511_MASS_AUDIT_JSON"),
        file_record(LATEST_MASS_AUDIT_MD, "NEW_MASS_MODEL_511_MASS_AUDIT_MD"),
        file_record(LATEST_FINAL_REVIEW, "NEW_MASS_MODEL_511_FINAL_REVIEW"),
        file_record(LATEST_OVERLAP_LOG, "NEW_MASS_MODEL_511_OVERLAP_LOG"),
        file_record(LATEST_SCHEMATIC, "NEW_MASS_MODEL_511_2D_SCHEMATIC"),
        file_record(LATEST_WRL, "NEW_MASS_MODEL_511_WRL"),
        file_record(SOURCE_AUTH_DIR, "PACKAGE_LOCAL_SOURCE_COPY_DIR"),
        file_record(SOURCE_AUTH_MANIFEST, "PACKAGE_LOCAL_SOURCE_MIGRATION_MANIFEST"),
        file_record(WORKSPACE_INDEX, "CLEANED_WORKSPACE_INDEX"),
    ]
    current_required_roles = {
        "NEW_MASS_MODEL_511_CANDIDATE_SETUP",
        "NEW_MASS_MODEL_511_CANDIDATE_GEO",
        "NEW_MASS_MODEL_511_CANDIDATE_DET",
        "NEW_MASS_MODEL_511_CANDIDATE_INTRO",
        "NEW_MASS_MODEL_511_CANDIDATE_MATERIALS",
        "NEW_MASS_MODEL_511_CANDIDATE_README",
        "NEW_MASS_MODEL_511_MANIFEST",
        "NEW_MASS_MODEL_511_MASS_AUDIT_JSON",
        "NEW_MASS_MODEL_511_MASS_AUDIT_MD",
        "NEW_MASS_MODEL_511_FINAL_REVIEW",
        "NEW_MASS_MODEL_511_OVERLAP_LOG",
        "NEW_MASS_MODEL_511_2D_SCHEMATIC",
        "NEW_MASS_MODEL_511_WRL",
        "PACKAGE_LOCAL_SOURCE_COPY_DIR",
        "PACKAGE_LOCAL_SOURCE_MIGRATION_MANIFEST",
        "CLEANED_WORKSPACE_INDEX",
    }
    current_required_ok = all(
        item["exists"] for item in authority_files if item["role"] in current_required_roles
    )

    authority_manifest = {
        "document_type": "Mass_model_511_nearfield_migration_authority_manifest",
        "generated_at_utc": generated,
        "status": "AUTHORITY_PASS_CLEANED_CHECKOUT" if current_required_ok else "AUTHORITY_WARN_MISSING_CURRENT_FILES",
        "repo_head": GIT_HEAD,
        "repo_dirty": bool(GIT_STATUS_LINES),
        "repo_status_line_count": len(GIT_STATUS_LINES),
        "old_nearfield_candidate_setup_replaced": rel(OLD_NF2_SETUP),
        "new_candidate_setup": candidate_setup_rel,
        "baseline_setup": rel(BASELINE_SETUP),
        "source_authority_dir": "package-local cleaned checkout source copy",
        "source_migration_output": source_cards,
        "files": authority_files,
    }
    write_json(MANIFEST_DIR / "authority_manifest.json", authority_manifest)

    write_text(
        MANIFEST_DIR / "authority_manifest.md",
        "\n".join(
            [
                "# Mass_model_511 Nearfield Migration Authority",
                "",
                f"generated_at_utc: `{generated}`",
                f"status: `{authority_manifest['status']}`",
                "",
                f"- old nearfield candidate replaced: `{rel(OLD_NF2_SETUP)}`",
                f"- new candidate setup: `{candidate_setup_rel}`",
                f"- package-local source copy: `{rel(SOURCE_AUTH_DIR)}`",
                f"- local migrated source dir: `{source_cards['source_dir']}`",
                "",
                "The previous NF2/OF1 engineering run remains immutable. This package is a new detector-geometry migration branch.",
                "",
            ]
        ),
    )

    write_json(
        GEOM_DIR / "geometry_gate.json",
        {
            "document_type": "Mass_model_511_geometry_gate",
            "generated_at_utc": generated,
            "status": geometry_status,
            "candidate_setup": latest_setup,
            "overlap_log_status": overlap,
            "final_review_status": review,
            "mass_summary": mass_summary(),
            "claim_boundary": "Geometry/runtime readiness only; no prompt/delayed background claim is made here.",
        },
    )
    write_text(
        GEOM_DIR / "geometry_gate.md",
        "\n".join(
            [
                "# Mass_model_511 Geometry Gate",
                "",
                f"generated_at_utc: `{generated}`",
                f"status: `{geometry_status}`",
                "",
                "| Check | Status | Evidence |",
                "| --- | --- | --- |",
                f"| Candidate setup exists/includes resolve | `{'PASS' if latest_setup['exists'] and not latest_setup['missing_includes'] else 'FAIL'}` | `{candidate_setup_rel}` |",
                f"| Cosima overlap | `{overlap['status']}` | `{rel(LATEST_OVERLAP_LOG)}` |",
                f"| Final geometry review | `{review['status']}` | `{rel(LATEST_FINAL_REVIEW)}` |",
                f"| Source cards migrated locally | `{source_cards['status']}` | `{source_cards['manifest']}` |",
                "",
                "Notes:",
                "- This gate replaces the old NF2 detector-nearfield candidate with the latest Mass_model_511 detector geometry.",
                "- The passive side-wall W/Pb liner caveat from the latest final review is preserved; this migration does not silently resolve it.",
                "- This file is not a transport-rate or no-effect claim.",
                "",
            ]
        ),
    )

    bridge_resolution = {
        "document_type": "Mass_model_511_bridge_resolution",
        "generated_at_utc": generated,
        "status": "OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY",
        "old_blocker": "BLOCKED_OPTICS_BRIDGE in engineering/nearfield_mass_impact_20260625 applied to the independent OF1 optics-local mass model.",
        "resolution": "The new Mass_model_511 migration is a detector MEGAlib geometry replacement. The support/feedthrough/cryostat masses are loaded directly by the detector .geo.setup, so detector prompt/buildup/delayed transport does not need an optics-to-detector transfer bridge.",
        "not_claimed": [
            "No OF1 optics local background or detector-coupled optics background result is promoted.",
            "The previous OF1 bridge blocker remains true for the old OF1 optics campaign.",
            "This resolution only removes the bridge blocker from this detector-only Mass_model_511 migration branch.",
        ],
        "allowed_next_steps": [
            "Run candidate_Mass_model_511 prompt and buildup with the migrated source cards.",
            "Build geometry-specific delayed sources from the candidate_Mass_model_511 buildup output.",
            "Use existing Step05/normalization authority unchanged.",
        ],
    }
    write_json(BRIDGE_DIR / "bridge_resolution.json", bridge_resolution)
    write_text(
        BRIDGE_DIR / "bridge_resolution.md",
        "\n".join(
            [
                "# Bridge Resolution",
                "",
                f"generated_at_utc: `{generated}`",
                f"status: `{bridge_resolution['status']}`",
                "",
                "The previous `BLOCKED_OPTICS_BRIDGE` belonged to the old independent OF1 optics-local branch. In this new branch, the candidate is a detector MEGAlib geometry replacement:",
                "",
                f"- new detector candidate: `{candidate_setup_rel}`",
                "- no independent optics local geometry is introduced in this migration package",
                "- source cards point directly at the detector geometry",
                "- detector prompt/buildup/delayed transport can proceed without an optics-to-detector transfer calculation",
                "",
                "Non-claims:",
                "- This does not promote any OF1 optics-background result.",
                "- This does not overwrite the old nearfield engineering final status.",
                "- This does not make a no-effect claim for the Mass_model_511 geometry.",
                "",
            ]
        ),
    )

    write_text(
        OUT / "HARNESS_MASS_MODEL_511_NEARFIELD_MIGRATION.md",
        "\n".join(
            [
                "# Harness: Mass_model_511 Nearfield Migration",
                "",
                f"created_at_utc: `{generated}`",
                "status: `READY_FOR_DETECTOR_TRANSPORT_REVIEW`",
                "",
                "## Objective",
                "",
                "Replace the previous NF2 detector-nearfield support candidate used by the 20260625 engineering workflow with the latest Mass_model_511 detector MEGAlib geometry, while keeping the previous workflow's authority-lock/source-copy discipline.",
                "",
                "## Active Geometry",
                "",
                f"- baseline detector: `{rel(BASELINE_SETUP)}`",
                f"- replaced nearfield candidate: `{rel(OLD_NF2_SETUP)}`",
                f"- active Mass_model_511 candidate: `{candidate_setup_rel}`",
                "",
                "## Gates",
                "",
                "1. G0 authority: `00_manifest/authority_manifest.json`",
                "2. G1 geometry: `01_geometry/geometry_gate.md`",
                "3. G2 source migration: `03_source_migration/source_dirs/Mass_model_511/source_migration_manifest.json`",
                "4. G5 bridge resolution: `04_bridge_resolution/bridge_resolution.md`",
                "5. G3/G4 detector transport: not run by this artifact builder; use `02_run_plan/smoke_run_matrix.csv` after resource approval.",
                "",
                "## Boundary",
                "",
                "This harness is detector-only. The old OF1 optics bridge blocker is not carried into this branch because no independent optics-local mass model is being coupled to the detector. The old OF1 campaign remains blocked unless a separate bridge is built.",
                "",
            ]
        ),
    )

    write_text(
        MANIFEST_DIR / "FINAL_STATUS.md",
        "\n".join(
            [
                "# FINAL_STATUS",
                "",
                f"updated_at_utc: `{generated}`",
                "status: `MASS_MODEL_511_ENGINEERING_MIGRATION_PREPARED`",
                "",
                f"- old nearfield support geometry replaced: `{rel(OLD_NF2_SETUP)}`",
                f"- active Mass_model_511 geometry: `{candidate_setup_rel}`",
                f"- local source migration: `{source_cards['manifest']}`",
                f"- optics bridge status: `OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY`",
                "",
                "| Gate | Status | Blocking | Evidence |",
                "| --- | --- | --- | --- |",
                f"| G0 authority | `{authority_manifest['status']}` | no | `00_manifest/authority_manifest.json` |",
                f"| G1 geometry | `{geometry_status}` | {'no' if geometry_status == 'GEOMETRY_PASS' else 'yes'} | `01_geometry/geometry_gate.md` |",
                "| G2 source migration | `SOURCE_COPY_PREPARED` | no | `03_source_migration/source_dirs/Mass_model_511/source_migration_manifest.json` |",
                "| G5 optics bridge | `OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY` | no | `04_bridge_resolution/bridge_resolution.md` |",
                "| G3/G4 detector transport | `NOT_RUN` | resource authorization required | `02_run_plan/smoke_run_matrix.csv` |",
                "",
                "Claim boundary: this package prepares the new engineering geometry/source/bridge state. It does not claim detector background rates or no-effect closure.",
                "",
            ]
        ),
    )

    write_text(
        MANUSCRIPT_DIR / "claim_boundary.md",
        "\n".join(
            [
                "# Claim Boundary",
                "",
                "The Mass_model_511 detector geometry has been migrated into a new engineering branch and source-card copies have been prepared. No prompt, delayed, activation, or focused-signal transport result is produced by this package.",
                "",
                "Do not cite this branch as a physics/background result until the detector transport workflow is run with the migrated `candidate_Mass_model_511` source cards.",
                "",
            ]
        ),
    )


if __name__ == "__main__":
    build()
