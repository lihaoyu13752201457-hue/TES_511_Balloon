#!/usr/bin/env python3
"""Summarize S3c dominant-background equal-stat runs against S3 baseline."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent

S3C_GEOMETRY_SETUP = (
    "engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/"
    "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
S3C_GEOMETRY_SETUP_NORMALIZED = (ROOT / S3C_GEOMETRY_SETUP).resolve().as_posix()
SOURCE_CARDS = WORK / "source_cards"
PROMPT_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_eqstats_prompt_eplus_n_20260709"
)
ATM_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_atm511_sidecar_3m_20260709"
)
ATM_RUN_NAME = "Atm511SidecarS3cBgoW2mmAl3mmShell3M"
ATM_SOURCE = ATM_RUN_DIR / f"{ATM_RUN_NAME}.source"
ATM_SIM = ATM_RUN_DIR / f"{ATM_RUN_NAME}.inc1.id1.sim.gz"
ATM_SUMMARY = WORK / "s3c_atm511_sidecar_3m_summary.json"

S3_BASELINE_PROMPT_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/retained_conclusions"
    / "s3_eqstats_prompt_all_summary.json"
)
S3_BASELINE_ATM_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/retained_conclusions"
    / "s3_atm511_sidecar_3m_summary.json"
)
PROMPT_PROXY = ROOT / "old/reports/prompt511_repack_smoke_20260617/build_prompt511_repack_l1_proxy.py"
STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"

OUT_JSON = WORK / "dominant_background_summary.json"
OUT_CSV = WORK / "dominant_background_summary.csv"
OUT_MD = WORK / "dominant_background_summary.md"

COMPONENTS = ("eplus", "n", "atm511")
ACTIVE_VETO_THRESHOLD_KEV = 50.0
PROMPT_STAGES = (
    ("raw", "raw_rate_s-1", "raw_events"),
    ("active_veto_pass", "active_veto_pass_rate_s-1", "active_veto_pass_events"),
    ("side_compton_fov_pass", "side_compton_fov_pass_rate_s-1", "side_compton_fov_pass_events"),
)
ATM_STAGES = (
    ("raw", "raw_rate_cps", "raw_events"),
    ("active_veto_pass", "active_rate_cps", "active_veto_pass_events"),
    ("side_compton_fov_pass", "final_rate_cps", "side_compton_fov_pass_events"),
)


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_module(name: str, path: Path):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def geometry_line(path: Path) -> str | None:
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("Geometry "):
            return line.split(None, 1)[1]
    return None


def sim_header_geometry(path: Path) -> str | None:
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("Geometry "):
                return line.split(None, 1)[1]
            if line == "SE":
                break
    return None


def normalize_geometry_path(value: str | None) -> str | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve().as_posix()


def geometry_matches(value: str | None) -> bool:
    return normalize_geometry_path(value) == S3C_GEOMETRY_SETUP_NORMALIZED


def read_source_card_evidence() -> dict[str, Any]:
    source_cards = sorted(SOURCE_CARDS.glob("Background_*_fullsphere20.source"))
    rows = []
    for path in source_cards:
        geometry = geometry_line(path)
        rows.append(
            {
                "path": rel(path),
                "geometry": geometry,
                "geometry_normalized": normalize_geometry_path(geometry),
            }
        )
    return {
        "expected_geometry": S3C_GEOMETRY_SETUP,
        "expected_geometry_normalized": S3C_GEOMETRY_SETUP_NORMALIZED,
        "count": len(rows),
        "all_match": bool(rows) and all(geometry_matches(row["geometry"]) for row in rows),
        "rows": rows,
    }


def read_prompt_temp_source_evidence() -> dict[str, Any]:
    manifest = PROMPT_RUN_DIR / "run_manifest.csv"
    if not manifest.exists():
        return {
            "expected_geometry": S3C_GEOMETRY_SETUP,
            "expected_geometry_normalized": S3C_GEOMETRY_SETUP_NORMALIZED,
            "count": 0,
            "all_match": False,
            "rows": [],
        }
    rows: list[dict[str, Any]] = []
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            path = ROOT / row["temp_source"]
            if row["particle"] not in ("eplus", "n"):
                continue
            geometry = geometry_line(path) if path.exists() else None
            rows.append(
                {
                    "job_name": row["job_name"],
                    "particle": row["particle"],
                    "path": rel(path),
                    "geometry": geometry,
                    "geometry_normalized": normalize_geometry_path(geometry),
                }
            )
    return {
        "expected_geometry": S3C_GEOMETRY_SETUP,
        "expected_geometry_normalized": S3C_GEOMETRY_SETUP_NORMALIZED,
        "count": len(rows),
        "all_match": bool(rows) and all(geometry_matches(row["geometry"]) for row in rows),
        "rows": rows,
    }


def read_prompt_sim_header_evidence() -> dict[str, Any]:
    manifest = PROMPT_RUN_DIR / "run_manifest.csv"
    if not manifest.exists():
        return {
            "expected_geometry": S3C_GEOMETRY_SETUP,
            "expected_geometry_normalized": S3C_GEOMETRY_SETUP_NORMALIZED,
            "count": 0,
            "all_match": False,
            "rows": [],
        }
    rows: list[dict[str, Any]] = []
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["particle"] not in ("eplus", "n"):
                continue
            path = ROOT / row["sim_path"]
            geometry = sim_header_geometry(path) if path.exists() else None
            rows.append(
                {
                    "job_name": row["job_name"],
                    "particle": row["particle"],
                    "path": rel(path),
                    "geometry": geometry,
                    "geometry_normalized": normalize_geometry_path(geometry),
                }
            )
    return {
        "expected_geometry": S3C_GEOMETRY_SETUP,
        "expected_geometry_normalized": S3C_GEOMETRY_SETUP_NORMALIZED,
        "count": len(rows),
        "all_match": bool(rows) and all(geometry_matches(row["geometry"]) for row in rows),
        "rows": rows,
    }


def read_atm_geometry_evidence() -> dict[str, Any]:
    source_geometry = geometry_line(ATM_SOURCE) if ATM_SOURCE.exists() else None
    sim_geometry = sim_header_geometry(ATM_SIM) if ATM_SIM.exists() else None
    return {
        "expected_geometry": S3C_GEOMETRY_SETUP,
        "expected_geometry_normalized": S3C_GEOMETRY_SETUP_NORMALIZED,
        "source": {
            "path": rel(ATM_SOURCE),
            "geometry": source_geometry,
            "geometry_normalized": normalize_geometry_path(source_geometry),
            "match": geometry_matches(source_geometry),
        },
        "sim": {
            "path": rel(ATM_SIM),
            "geometry": sim_geometry,
            "geometry_normalized": normalize_geometry_path(sim_geometry),
            "match": geometry_matches(sim_geometry),
        },
        "all_match": geometry_matches(source_geometry) and geometry_matches(sim_geometry),
    }


def require_prompt_run_pass() -> dict[str, Any]:
    summary_path = PROMPT_RUN_DIR / "run_summary.json"
    rows = load_json(summary_path)
    selected = [row for row in rows if row["particle"] in ("eplus", "n")]
    bad = [row for row in selected if row["status"] not in ("PASS", "SKIP")]
    if len(selected) != 16 or bad:
        raise RuntimeError(f"prompt run status gate failed: selected={len(selected)} bad={bad}")
    return {
        "path": rel(summary_path),
        "selected_jobs": len(selected),
        "pass_or_skip_jobs": sum(1 for row in selected if row["status"] in ("PASS", "SKIP")),
        "fail_jobs": len(bad),
        "events_requested": sum(int(row["events"]) for row in selected),
        "events_generated": sum(int(row["generated_particles"] or 0) for row in selected),
    }


def side_entry_disk(step05) -> dict[str, Any]:
    try:
        return step05.side_entry_disk()
    except Exception:
        mass_sum = load_json(
            ROOT
            / "stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1"
            / "step05_Mass_model_511_fullstat_v1_l1_response_summary.json"
        )
        import numpy as np

        d0 = mass_sum["normalization"]["side_entry_disk"]
        center = np.asarray(d0["center_cm"], dtype=float)
        normal = np.asarray(d0["normal"], dtype=float)
        normal = normal / np.linalg.norm(normal)
        ref = np.asarray([0.0, 0.0, 1.0], dtype=float)
        if abs(float(np.dot(normal, ref))) > 0.9:
            ref = np.asarray([0.0, 1.0, 0.0], dtype=float)
        u = np.cross(normal, ref)
        u = u / np.linalg.norm(u)
        v = np.cross(normal, u)
        v = v / np.linalg.norm(v)
        return {
            "center_cm": center,
            "normal": normal,
            "basis_u": u,
            "basis_v": v,
            "radius_cm": float(d0["radius_cm"]),
        }


def is_active_veto_volume(volume: str) -> bool:
    upper = str(volume).upper()
    return (
        upper.startswith("CSI_")
        or "ACTIVE_SHIELD" in upper
        or "ACTIVESHIELD" in upper
        or "CEBR3" in upper
        or "BGO" in upper
        or upper.startswith("GEOOPT_S1_PLASTICFULLWRAP")
        or upper.startswith("GEOOPT_S2B_CRYOSHELL_PLASTIC")
    )


def configure_proxy(proxy, step05) -> None:
    step05.ROOT = ROOT
    step05.STEP09_SUMMARY = (
        ROOT
        / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
        / "step09_optics_bridge_summary.json"
    )
    proxy.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    proxy.TP_ACTIVE_FILTER_RE = (
        r"^(ID |SE$|CC HIT "
        r"(TP_L|CsI_|.*ACTIVE_SHIELD|.*ActiveShield|.*CEBR3|.*BGO|"
        r"GeoOpt_S1_PlasticFullWrap|GeoOpt_S2B_CryoShell_Plastic))"
    )
    step05.is_v3p5_active_veto_volume = is_active_veto_volume


def summarize_prompt_cases() -> dict[str, Any]:
    proxy = load_module("s3c_dominant_prompt_proxy", PROMPT_PROXY)
    step05 = load_module("s3c_dominant_step05", STEP05_SCRIPT)
    configure_proxy(proxy, step05)
    disk = side_entry_disk(step05)
    out: dict[str, Any] = {}
    for component in ("eplus", "n"):
        out[component] = proxy.summarize_prompt_dir(step05, PROMPT_RUN_DIR, disk, "keep", tag=component)
    return out


def ratio(num: float, den: float) -> float | None:
    return num / den if den > 0.0 else None


def poisson_ratio_sigma(num_events: int, den_events: int, value: float | None) -> float | None:
    if value is None or num_events <= 0 or den_events <= 0:
        return None
    return value * math.sqrt(1.0 / num_events + 1.0 / den_events)


def add_prompt_rows(
    rows: list[dict[str, Any]],
    component: str,
    s3c: dict[str, Any],
    s3: dict[str, Any],
) -> None:
    for stage, rate_key, event_key in PROMPT_STAGES:
        s3c_events = int(s3c[event_key])
        s3_events = int(s3[event_key])
        s3c_rate = float(s3c[rate_key])
        s3_rate = float(s3[rate_key])
        value = ratio(s3c_rate, s3_rate)
        rows.append(
            {
                "component": component,
                "stage": stage,
                "s3c_events": s3c_events,
                "s3c_rate_cps": s3c_rate,
                "s3_events": s3_events,
                "s3_rate_cps": s3_rate,
                "s3c_over_s3_ratio": value,
                "counting_only_1sigma": poisson_ratio_sigma(s3c_events, s3_events, value),
            }
        )


def add_atm_rows(rows: list[dict[str, Any]], s3c_w2: dict[str, Any], s3_w2: dict[str, Any]) -> None:
    for stage, rate_key, event_key in ATM_STAGES:
        s3c_events = int(s3c_w2[event_key])
        s3_events = int(s3_w2[event_key])
        s3c_rate = float(s3c_w2[rate_key])
        s3_rate = float(s3_w2[rate_key])
        value = ratio(s3c_rate, s3_rate)
        rows.append(
            {
                "component": "atm511",
                "stage": stage,
                "s3c_events": s3c_events,
                "s3c_rate_cps": s3c_rate,
                "s3_events": s3_events,
                "s3_rate_cps": s3_rate,
                "s3c_over_s3_ratio": value,
                "counting_only_1sigma": poisson_ratio_sigma(s3c_events, s3_events, value),
            }
        )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "component",
        "stage",
        "s3c_events",
        "s3c_rate_cps",
        "s3_events",
        "s3_rate_cps",
        "s3c_over_s3_ratio",
        "counting_only_1sigma",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# S3c Dominant Background Summary",
        "",
        f"Status: `{payload['status']}`",
        "",
        "Scope: S3c geometry, prompt `eplus`, prompt `n`, and atmospheric 511-keV 4pi sidecar only.",
        "Active veto: BGO/CsI active scintillator, ActiveShield/CEBR3, and `GeoOpt_S2B_CryoShell_Plastic*`; W/Al mechanical shell excluded.",
        "",
        "## W2 510.58-511.42 keV",
        "",
        "| component | stage | S3c events | S3c cps | S3 events | S3 cps | S3c/S3 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        value = row["s3c_over_s3_ratio"]
        sigma = row["counting_only_1sigma"]
        if value is None:
            ratio_text = ""
        elif sigma is None:
            ratio_text = f"{value:.6g}"
        else:
            ratio_text = f"{value:.6g} +/- {sigma:.3g}"
        lines.append(
            f"| {row['component']} | {row['stage']} | {row['s3c_events']} | {row['s3c_rate_cps']:.6g} | "
            f"{row['s3_events']} | {row['s3_rate_cps']:.6g} | {ratio_text} |"
        )
    checks = payload["geometry_verification"]
    lines.extend(
        [
            "",
            "## Geometry Evidence",
            "",
            f"- Expected geometry: `{S3C_GEOMETRY_SETUP}`",
            f"- Source cards Geometry match: `{checks['source_cards']['all_match']}` ({checks['source_cards']['count']} files)",
            f"- Prompt temp source Geometry match: `{checks['prompt_temp_sources']['all_match']}` ({checks['prompt_temp_sources']['count']} files)",
            f"- Prompt SIM header Geometry match: `{checks['prompt_sim_headers']['all_match']}` ({checks['prompt_sim_headers']['count']} files)",
            f"- ATM511 source/SIM Geometry match: `{checks['atm511']['all_match']}`",
            "",
            "## Inputs",
            "",
            f"- Prompt run: `{rel(PROMPT_RUN_DIR)}`",
            f"- ATM511 run: `{rel(ATM_RUN_DIR)}`",
            f"- S3 prompt baseline: `{rel(S3_BASELINE_PROMPT_SUMMARY)}`",
            f"- S3 ATM511 baseline: `{rel(S3_BASELINE_ATM_SUMMARY)}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    prompt_gate = require_prompt_run_pass()
    s3_prompt = load_json(S3_BASELINE_PROMPT_SUMMARY)
    s3_atm = load_json(S3_BASELINE_ATM_SUMMARY)
    s3c_atm = load_json(ATM_SUMMARY)
    if s3_prompt.get("status") != "PASS_S3_EQSTATS_PROMPT_ALL_WITH_ATM511":
        raise RuntimeError(f"bad S3 prompt baseline status: {s3_prompt.get('status')}")
    if s3_atm.get("status") != "PASS_S3_ATM511_4PI_SIDECAR_REPLAY":
        raise RuntimeError(f"bad S3 atm baseline status: {s3_atm.get('status')}")
    if s3c_atm.get("status") != "PASS_S3C_ATM511_4PI_SIDECAR_REPLAY":
        raise RuntimeError(f"bad S3c atm status: {s3c_atm.get('status')}")

    s3c_prompt_cases = summarize_prompt_cases()
    rows: list[dict[str, Any]] = []
    for component in ("eplus", "n"):
        add_prompt_rows(
            rows,
            component,
            s3c_prompt_cases[component]["summary"],
            s3_prompt["prompt_cases"][component]["summary"],
        )
    add_atm_rows(
        rows,
        s3c_atm["windows"]["w2_510p58_511p42"],
        s3_atm["windows"]["w2_510p58_511p42"],
    )

    geometry_verification = {
        "source_cards": read_source_card_evidence(),
        "prompt_temp_sources": read_prompt_temp_source_evidence(),
        "prompt_sim_headers": read_prompt_sim_header_evidence(),
        "atm511": read_atm_geometry_evidence(),
    }
    if not all(
        (
            geometry_verification["source_cards"]["all_match"],
            geometry_verification["prompt_temp_sources"]["all_match"],
            geometry_verification["prompt_sim_headers"]["all_match"],
            geometry_verification["atm511"]["all_match"],
        )
    ):
        raise RuntimeError("Geometry verification failed; inspect dominant_background_summary evidence")

    payload = {
        "status": "PASS_S3C_DOMINANT_BACKGROUNDS_EPLUS_N_ATM511",
        "inputs": {
            "geometry_setup": S3C_GEOMETRY_SETUP,
            "source_cards": rel(SOURCE_CARDS),
            "prompt_run_dir": rel(PROMPT_RUN_DIR),
            "atm511_run_dir": rel(ATM_RUN_DIR),
            "s3_prompt_baseline": rel(S3_BASELINE_PROMPT_SUMMARY),
            "s3_atm511_baseline": rel(S3_BASELINE_ATM_SUMMARY),
        },
        "normalization": {
            "prompt_match": "gamma 1e7/12 splits, non-gamma 8 replicas, farfield R=60 cm; selected particles eplus,n",
            "atm511_match": "3e6 events, seed 26070917, same 4pi sidecar flux model as S3",
            "w2_window_keV": [510.58, 511.42],
            "active_veto_threshold_keV": 50.0,
            "active_veto_volume_rule": (
                "BGO/CsI active scintillator + ActiveShield/CEBR3 + "
                "GeoOpt_S2B_CryoShell_Plastic*; W/Al mechanical shell excluded"
            ),
            "ratio_uncertainty": "selected-event Poisson counting-only",
        },
        "prompt_run_gate": prompt_gate,
        "prompt_cases": s3c_prompt_cases,
        "atm511_case": s3c_atm,
        "geometry_verification": geometry_verification,
        "rows": rows,
    }
    write_json(OUT_JSON, payload)
    write_csv(OUT_CSV, rows)
    OUT_MD.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "json": rel(OUT_JSON), "csv": rel(OUT_CSV), "md": rel(OUT_MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
