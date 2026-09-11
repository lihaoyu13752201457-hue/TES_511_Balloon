#!/usr/bin/env python3
"""Build the fail-closed S3c-C0 versus S3d-O9 screening comparison.

This analyzer owns the *screening* result only.  It deliberately waits for all
matched transports before issuing a promotion decision and never substitutes a
proxy value for a missing run.  The exact retained 50-keV active-veto and
side-entry Compton/FoV implementation are imported at run time.

Outputs are deterministic summaries under the new 42_ package.  Missing or
still-running transports produce a clean PENDING state; a present but
inconsistent authority produces FAIL.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scipy import __version__ as scipy_version
from scipy.stats import beta, chi2, norm


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "42_geoopt_s3d_lightweight_20260712"
)
DATA = PACKAGE / "data"

S3D_SETUP = (
    PACKAGE
    / "geometry"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
S3C_SETUP = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709"
    / "geometry"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)

S3C_DOMINANT = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "32_s3c_dominant_backgrounds_20260709"
    / "dominant_background_summary.json"
)
S3C_ATM_SUMMARY = S3C_DOMINANT.parent / "s3c_atm511_sidecar_3m_summary.json"
S3C_DELAYED_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "38_s3c_neutron_delayed_chain_m50000_clean_20260710"
    / "delayed_source"
    / "delayed_source_exactpos_summary.json"
)
S3C_DELAYED_CAMPAIGN = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "38_s3c_neutron_delayed_chain_m50000_clean_20260710"
    / "s3c_bgo_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710_campaign_manifest.json"
)

S3D_PROMPT_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_lightweight_eqstats_prompt_eplus_n_20260712"
)
S3D_PROMPT_SOURCE_MANIFEST = (
    PACKAGE
    / "config/prompt_eqstats_eplus_n/source_cards/source_migration_manifest.json"
)
S3D_PROMPT_PREFLIGHT = DATA / "s3d_prompt_eqstats_preflight.json"

S3D_ATM_MANIFEST = DATA / "s3d_atm511_replay_manifest.json"
S3D_ATM_RUN_NAME = "Atm511SidecarS3dO9_3M"
S3D_ATM_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o9_atm511_sidecar_3m_20260712"
)
S3D_ATM_SOURCE = S3D_ATM_DIR / f"{S3D_ATM_RUN_NAME}.source"
S3D_ATM_LOG = S3D_ATM_DIR / f"cosima_{S3D_ATM_RUN_NAME}.log"
S3D_ATM_SIM = S3D_ATM_DIR / f"{S3D_ATM_RUN_NAME}.inc1.id1.sim.gz"

SIGNAL_MANIFEST = DATA / "s3d_signal_replay_manifest.json"
SIGNAL_BRANCHES = {
    "s3c_c0": {
        "label": "S3c-C0",
        "run_name": "Opticsim_laue_f10m_a1_s3c_c0_signal37194",
        "run_dir": (
            ROOT
            / "runs/geometry_optimization_20260704"
            / "s3c_c0_f10m_a1_signal_replay_37194_matched_20260712"
        ),
        "geometry": S3C_SETUP,
    },
    "s3d_o9": {
        "label": "S3d-O9",
        "run_name": "Opticsim_laue_f10m_a1_s3d_o9_signal37194",
        "run_dir": (
            ROOT
            / "runs/geometry_optimization_20260704"
            / "s3d_o9_f10m_a1_signal_replay_37194_20260712"
        ),
        "geometry": S3D_SETUP,
    },
}
for _branch in SIGNAL_BRANCHES.values():
    _branch["source"] = _branch["run_dir"] / f"{_branch['run_name']}.source"
    _branch["sim"] = _branch["run_dir"] / f"{_branch['run_name']}.inc1.id1.sim.gz"
    _branch["log"] = _branch["run_dir"] / f"cosima_{_branch['run_name']}.log"

S3D_DELAYED_CAMPAIGN = DATA / "s3d_delayed_activation_campaign.json"
S3D_DELAYED_SUMMARY = PACKAGE / "fullchain/delayed_source/delayed_source_exactpos_summary.json"
S3D_DELAY_LABEL = "s3d_o9_neutron_delayed_m50000_20260712"
S3D_DELAY_FIX_AUDIT = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / f"step02_delay_fix_{S3D_DELAY_LABEL}"
    / "normalization_audit_groundstate_fix.json"
)

PROMPT_PROXY = (
    ROOT
    / "old/reports/prompt511_repack_smoke_20260617"
    / "build_prompt511_repack_l1_proxy.py"
)
STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
ATM_BASE_SCRIPT = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "12_atm511_sidecar_replay_20260708"
    / "build_geo_opt_atm511_sidecar_replay.py"
)
STEP09_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)

OUT_JSON = DATA / "s3d_screening_analysis.json"
OUT_CSV = DATA / "s3d_screening_comparison.csv"
OUT_MD = PACKAGE / "S3D_SCREENING_ANALYSIS.md"
OUT_ATM = DATA / "s3d_atm511_replay_summary.json"
OUT_SIGNAL = DATA / "s3d_signal_replay_summary.json"

ACTIVE_VETO_THRESHOLD_KEV = 50.0
W2 = (510.58, 511.42)
BROAD = (480.0, 550.0)
PROMPT_PARTICLES = ("eplus", "n")
PROMPT_JOBS = 16
PROMPT_EXPECTED_EVENTS = {"eplus": 243_727 * 8, "n": 963_066 * 8}
PROMPT_EXPECTED_TOTAL = sum(PROMPT_EXPECTED_EVENTS.values())
ATM_EVENTS = 3_000_000
ATM_SEED = 26070917
SIGNAL_TRIGGERS = 37_194
SIGNAL_SEED = 260616
DELAYED_EVENTS = 1_000_000
DELAYED_SEED = 260613

DOMINANT_LIMIT_CPS = 0.0052
SIGNAL_LOSS_LIMIT = 0.02
DELAYED_ACTIVITY_LIMIT_BQ = 57.8243

STAGES = (
    ("raw", "raw_events", "raw_rate_s-1"),
    ("active_veto_pass", "active_veto_pass_events", "active_veto_pass_rate_s-1"),
    (
        "side_compton_fov_pass",
        "side_compton_fov_pass_events",
        "side_compton_fov_pass_rate_s-1",
    ),
)
ATM_STAGES = (
    ("raw", "raw_events", "raw_rate_cps"),
    ("active_veto_pass", "active_veto_pass_events", "active_rate_cps"),
    ("side_compton_fov_pass", "side_compton_fov_pass_events", "final_rate_cps"),
)


class PendingInput(RuntimeError):
    """A dated production artifact is not complete yet."""


class AuditFailure(RuntimeError):
    """A present authority violates the frozen comparison contract."""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_ids(ids: set[int]) -> str:
    text = "".join(f"{value}\n" for value in sorted(ids))
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "section",
        "component",
        "stage",
        "metric",
        "unit",
        "c0_count",
        "c0_value",
        "c0_ci95_low",
        "c0_ci95_high",
        "s3d_count",
        "s3d_value",
        "s3d_ci95_low",
        "s3d_ci95_high",
        "s3d_over_c0",
        "ratio_ci95_low",
        "ratio_ci95_high",
        "gate_limit",
        "gate_pass",
        "note",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_module(name: str, path: Path):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuditFailure(f"cannot import {rel(path)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def normalized_geometry(value: str | Path | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    p = Path(str(value).strip())
    if not p.is_absolute():
        p = ROOT / p
    return p.resolve().as_posix()


def geometry_matches(value: str | Path | None, expected: Path) -> bool:
    return normalized_geometry(value) == expected.resolve().as_posix()


def source_geometry(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [
        line.split(None, 1)[1].strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip().startswith("Geometry ")
    ]


def sim_header(path: Path, *, count_events: bool = False) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "status": "PENDING"}
    # Never expose synthetic zero counts from a header-only scan.  SE/ID are
    # present only when the entire gzip stream has actually been counted.
    out: dict[str, Any] = {"exists": True, "status": "PRESENT"}
    if count_events:
        out.update({"SE": 0, "ID": 0, "count_authority": "full_readable_sim_stream"})
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
            for raw in handle:
                line = raw.strip()
                if line.startswith("Geometry") and "geometry" not in out:
                    parts = line.split(None, 1)
                    out["geometry"] = parts[1].strip() if len(parts) == 2 else ""
                elif line.startswith("Seed") and "seed" not in out:
                    parts = line.split()
                    out["seed"] = int(parts[1]) if len(parts) > 1 else None
                if count_events:
                    if line == "SE":
                        out["SE"] += 1
                    elif line.startswith("ID "):
                        out["ID"] += 1
                elif line == "SE":
                    break
    except (EOFError, OSError) as exc:
        raise PendingInput(f"SIM is not a complete readable gzip yet: {rel(path)} ({exc})") from exc
    return out


def require_file(path: Path, label: str, *, retained: bool = False) -> None:
    if path.is_file():
        return
    if retained:
        raise AuditFailure(f"retained authority is missing: {label}={rel(path)}")
    raise PendingInput(f"waiting for {label}: {rel(path)}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


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


def selection_modules():
    for path in (PROMPT_PROXY, STEP05_SCRIPT, STEP09_SUMMARY):
        require_file(path, "selection authority", retained=True)
    proxy = load_module("s3d_screening_prompt_proxy", PROMPT_PROXY)
    step05 = load_module("s3d_screening_step05", STEP05_SCRIPT)
    step05.ROOT = ROOT
    step05.STEP09_SUMMARY = STEP09_SUMMARY
    proxy.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    proxy.TP_ACTIVE_FILTER_RE = (
        r"^(ID |SE$|CC HIT "
        r"(TP_L|CsI_|.*ACTIVE_SHIELD|.*ActiveShield|.*CEBR3|.*BGO|"
        r"GeoOpt_S1_PlasticFullWrap|GeoOpt_S2B_CryoShell_Plastic))"
    )
    step05.is_v3p5_active_veto_volume = is_active_veto_volume
    try:
        disk = step05.side_entry_disk()
    except Exception:
        # This is the same retained fallback used by the S3c authority builder.
        dominant_builder = load_module(
            "s3d_screening_dominant_builder",
            S3C_DOMINANT.parent / "build_s3c_dominant_background_summary.py",
        )
        disk = dominant_builder.side_entry_disk(step05)
    return proxy, step05, disk


def poisson_rate_interval(count: int, weight: float, level: float = 0.95) -> dict[str, float]:
    alpha = 1.0 - level
    low_mu = 0.0 if count == 0 else 0.5 * float(chi2.ppf(alpha / 2.0, 2 * count))
    high_mu = 0.5 * float(chi2.ppf(1.0 - alpha / 2.0, 2 * (count + 1)))
    return {"low": low_mu * weight, "high": high_mu * weight, "level": level}


def poisson_rate_ratio_interval(
    num_count: int,
    num_weight: float,
    den_count: int,
    den_weight: float,
    level: float = 0.95,
) -> dict[str, float | None]:
    alpha = 1.0 - level
    total = num_count + den_count
    if total == 0 or den_weight <= 0.0 or num_weight < 0.0:
        return {"low": None, "high": None, "level": level}
    p_low = 0.0 if num_count == 0 else float(beta.ppf(alpha / 2.0, num_count, den_count + 1))
    p_high = 1.0 if den_count == 0 else float(beta.ppf(1.0 - alpha / 2.0, num_count + 1, den_count))
    scale = num_weight / den_weight
    low = 0.0 if p_low <= 0.0 else scale * p_low / (1.0 - p_low)
    high = None if p_high >= 1.0 else scale * p_high / (1.0 - p_high)
    return {"low": low, "high": high, "level": level}


def wilson_interval(successes: int, trials: int, level: float = 0.95) -> dict[str, float | None]:
    if trials <= 0:
        return {"low": None, "high": None, "level": level}
    z = float(norm.ppf(0.5 + level / 2.0))
    p = successes / trials
    den = 1.0 + z * z / trials
    center = (p + z * z / (2.0 * trials)) / den
    half = z * math.sqrt(p * (1.0 - p) / trials + z * z / (4.0 * trials * trials)) / den
    return {"low": max(0.0, center - half), "high": min(1.0, center + half), "level": level}


def risk_ratio_interval(
    num_success: int,
    num_trials: int,
    den_success: int,
    den_trials: int,
    level: float = 0.95,
) -> dict[str, float | None]:
    if min(num_success, den_success, num_trials, den_trials) <= 0:
        return {"low": None, "high": None, "level": level}
    point = (num_success / num_trials) / (den_success / den_trials)
    variance = (1.0 - num_success / num_trials) / num_success + (
        1.0 - den_success / den_trials
    ) / den_success
    z = float(norm.ppf(0.5 + level / 2.0))
    half = z * math.sqrt(max(0.0, variance))
    return {
        "low": point * math.exp(-half),
        "high": point * math.exp(half),
        "level": level,
    }


def rate_weight(summary: dict[str, Any], count_key: str, rate_key: str) -> float:
    count = int(summary[count_key])
    rate = float(summary[rate_key])
    if count > 0:
        return rate / count
    explicit = summary.get("event_rate_weight_cps")
    if explicit is not None:
        return float(explicit)
    return 0.0


def comparison_row(
    *,
    section: str,
    component: str,
    stage: str,
    metric: str,
    unit: str,
    c0_count: int,
    c0_value: float,
    c0_weight: float,
    s3d_count: int,
    s3d_value: float,
    s3d_weight: float,
    note: str = "",
) -> dict[str, Any]:
    c0_ci = poisson_rate_interval(c0_count, c0_weight)
    s3d_ci = poisson_rate_interval(s3d_count, s3d_weight)
    ratio = s3d_value / c0_value if c0_value > 0.0 else None
    ratio_ci = poisson_rate_ratio_interval(s3d_count, s3d_weight, c0_count, c0_weight)
    return {
        "section": section,
        "component": component,
        "stage": stage,
        "metric": metric,
        "unit": unit,
        "c0_count": c0_count,
        "c0_value": c0_value,
        "c0_ci95_low": c0_ci["low"],
        "c0_ci95_high": c0_ci["high"],
        "s3d_count": s3d_count,
        "s3d_value": s3d_value,
        "s3d_ci95_low": s3d_ci["low"],
        "s3d_ci95_high": s3d_ci["high"],
        "s3d_over_c0": ratio,
        "ratio_ci95_low": ratio_ci["low"],
        "ratio_ci95_high": ratio_ci["high"],
        "note": note,
    }


def audit_retained_c0() -> dict[str, Any]:
    require_file(S3C_DOMINANT, "S3c dominant summary", retained=True)
    require_file(S3C_ATM_SUMMARY, "S3c atmospheric summary", retained=True)
    dominant = load_json(S3C_DOMINANT)
    atm = load_json(S3C_ATM_SUMMARY)
    require(
        dominant.get("status") == "PASS_S3C_DOMINANT_BACKGROUNDS_EPLUS_N_ATM511",
        f"bad retained S3c dominant status: {dominant.get('status')}",
    )
    require(
        atm.get("status") == "PASS_S3C_ATM511_4PI_SIDECAR_REPLAY",
        f"bad retained S3c atmospheric status: {atm.get('status')}",
    )
    checks = dominant.get("geometry_verification", {})
    require(
        all(checks.get(key, {}).get("all_match") for key in ("source_cards", "prompt_temp_sources", "prompt_sim_headers", "atm511")),
        "retained S3c dominant geometry evidence is not all PASS",
    )
    require(
        float(dominant.get("normalization", {}).get("active_veto_threshold_keV", -1))
        == ACTIVE_VETO_THRESHOLD_KEV,
        "retained S3c active-veto threshold is not 50 keV",
    )
    require(
        list(dominant.get("normalization", {}).get("w2_window_keV", [])) == list(W2),
        "retained S3c W2 window differs from the frozen window",
    )
    for particle in PROMPT_PARTICLES:
        case = dominant.get("prompt_cases", {}).get(particle, {})
        require(case, f"retained S3c prompt case missing: {particle}")
        expected = PROMPT_EXPECTED_EVENTS[particle]
        require(
            int(case["summary"].get("generated_events_seen", -1)) == expected,
            f"retained S3c {particle} generated count does not match {expected}",
        )
    return {
        "status": "PASS",
        "dominant_summary": rel(S3C_DOMINANT),
        "dominant_sha256": sha256(S3C_DOMINANT),
        "atm_summary": rel(S3C_ATM_SUMMARY),
        "atm_sha256": sha256(S3C_ATM_SUMMARY),
        "prompt_cases": dominant["prompt_cases"],
        "atm_case": atm,
        "geometry_verification": checks,
    }


def audit_prompt_run() -> dict[str, Any]:
    run_summary_path = S3D_PROMPT_DIR / "run_summary.json"
    require_file(run_summary_path, "completed 16-job S3d prompt run summary")
    for path, label in (
        (S3D_PROMPT_SOURCE_MANIFEST, "S3d prompt source manifest"),
        (S3D_PROMPT_PREFLIGHT, "S3d prompt preflight"),
        (S3D_PROMPT_DIR / "normalization.json", "S3d prompt normalization"),
        (S3D_PROMPT_DIR / "run_manifest.csv", "S3d prompt run manifest"),
    ):
        require_file(path, label)
    source_manifest = load_json(S3D_PROMPT_SOURCE_MANIFEST)
    preflight = load_json(S3D_PROMPT_PREFLIGHT)
    normalization = load_json(S3D_PROMPT_DIR / "normalization.json")
    rows = load_json(run_summary_path)
    with (S3D_PROMPT_DIR / "run_manifest.csv").open(encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    require(
        source_manifest.get("status") == "PASS_S3D_PROMPT_EQSTATS_SOURCE_COPY_PREPARED",
        "S3d prompt source migration is not PASS",
    )
    require(
        str(preflight.get("status", "")).startswith("PASS"),
        f"S3d prompt preflight is not PASS: {preflight.get('status')}",
    )
    expected_norm = {
        "mode": "instant",
        "gamma_events": 10_000_000,
        "gamma_splits": 12,
        "non_gamma_replicas": 8,
        "farfield_radius_cm": 60.0,
        "jobs": 16,
    }
    for key, expected in expected_norm.items():
        require(
            normalization.get(key) == expected,
            f"S3d prompt normalization {key}={normalization.get(key)!r}, expected {expected!r}",
        )
    require(normalization.get("selected_particles") == ["eplus", "n"], "unexpected prompt particle set")
    require(len(rows) == PROMPT_JOBS, f"prompt run has {len(rows)} jobs, expected {PROMPT_JOBS}")
    require(len(manifest_rows) == PROMPT_JOBS, "prompt run_manifest row count is not 16")
    bad = [row for row in rows if row.get("status") not in ("PASS", "SKIP")]
    require(not bad, f"prompt production contains failed jobs: {bad}")
    requested = sum(int(row.get("events") or 0) for row in rows)
    generated = sum(int(row.get("generated_particles") or 0) for row in rows)
    require(requested == PROMPT_EXPECTED_TOTAL, f"prompt requested count={requested}")
    require(generated == PROMPT_EXPECTED_TOTAL, f"prompt generated count={generated}")

    headers: list[dict[str, Any]] = []
    for row in manifest_rows:
        source = Path(row["temp_source"])
        sim = Path(row["sim_path"])
        dat = Path(row["dat_path"])
        if not source.is_absolute():
            source = ROOT / source
        if not sim.is_absolute():
            sim = ROOT / sim
        if not dat.is_absolute():
            dat = ROOT / dat
        require_file(source, f"prompt job source {row['job_name']}")
        require_file(sim, f"prompt SIM {row['job_name']}")
        require_file(dat, f"prompt DAT {row['job_name']}")
        require(
            len(source_geometry(source)) == 1 and geometry_matches(source_geometry(source)[0], S3D_SETUP),
            f"prompt source points at wrong geometry: {rel(source)}",
        )
        header = sim_header(sim)
        require(
            geometry_matches(header.get("geometry"), S3D_SETUP),
            f"prompt SIM header points at wrong geometry: {rel(sim)}",
        )
        tt = [
            float(line.split()[1])
            for line in dat.read_text(encoding="utf-8", errors="replace").splitlines()
            if line.startswith("TT ")
        ]
        require(len(tt) == 1 and tt[0] > 0.0, f"prompt DAT TT audit failed: {rel(dat)}")
        headers.append(
            {
                "job_name": row["job_name"],
                "particle": row["particle"],
                "source": rel(source),
                "sim": rel(sim),
                "geometry": header.get("geometry"),
                "tt_s": tt[0],
                "status": "PASS",
            }
        )
    return {
        "status": "PASS",
        "run_dir": rel(S3D_PROMPT_DIR),
        "run_summary": rel(run_summary_path),
        "jobs": len(rows),
        "events_requested": requested,
        "events_generated": generated,
        "normalization": normalization,
        "headers": headers,
    }


def analyze_prompt(c0: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    run_audit = audit_prompt_run()
    proxy, step05, disk = selection_modules()
    cases: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    for particle in PROMPT_PARTICLES:
        result = proxy.summarize_prompt_dir(step05, S3D_PROMPT_DIR, disk, "keep", tag=particle)
        summary = result["summary"]
        require(
            int(summary["generated_events_seen"]) == PROMPT_EXPECTED_EVENTS[particle],
            f"analyzed S3d {particle} generated count mismatch",
        )
        cases[particle] = result
        baseline_case = c0["prompt_cases"][particle]
        baseline = baseline_case["summary"]
        c0_event_weight = float(baseline_case["rate_per_event_s-1"])
        s3d_event_weight = float(result["rate_per_event_s-1"])
        for stage, count_key, rate_key in STAGES:
            c0_count = int(baseline[count_key])
            s3d_count = int(summary[count_key])
            c0_value = float(baseline[rate_key])
            s3d_value = float(summary[rate_key])
            rows.append(
                comparison_row(
                    section="prompt",
                    component=particle,
                    stage=stage,
                    metric="W2_rate",
                    unit="cps",
                    c0_count=c0_count,
                    c0_value=c0_value,
                    c0_weight=c0_event_weight,
                    s3d_count=s3d_count,
                    s3d_value=s3d_value,
                    s3d_weight=s3d_event_weight,
                    note="Garwood marginal rate CI; exact conditional Poisson rate-ratio CI",
                )
            )
    return {
        "status": "PASS_S3D_PROMPT_EPLUS_N_ANALYZED",
        "run_audit": run_audit,
        "cases": cases,
    }, rows


def log_tail_text(path: Path, max_bytes: int = 1_048_576) -> str:
    with path.open("rb") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(max(0, size - max_bytes))
        return handle.read().decode("utf-8", errors="replace")


def observation_time_from_log(path: Path, *, running_is_pending: bool = False) -> float:
    for line in log_tail_text(path).splitlines():
        if "Observation time:" not in line:
            continue
        numbers = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
        if numbers:
            value = float(numbers[0])
            if value > 0.0:
                return value
    message = f"cannot locate positive Observation time in {rel(path)}"
    if running_is_pending:
        raise PendingInput(f"atmospheric transport log has no completion-time record yet: {rel(path)}")
    raise AuditFailure(message)


def analyze_atm(c0: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    for path, label in (
        (S3D_ATM_MANIFEST, "S3d atmospheric replay manifest"),
        (S3D_ATM_SOURCE, "S3d atmospheric source"),
        (S3D_ATM_LOG, "S3d atmospheric Cosima log"),
        (S3D_ATM_SIM, "S3d atmospheric SIM"),
    ):
        require_file(path, label)
    manifest = load_json(S3D_ATM_MANIFEST)
    source_audit = manifest.get("source_authority", {}).get("source_audit", {})
    contract = manifest.get("selection_contract", {})
    run_contract = manifest.get("run", {})
    require(source_audit.get("status") == "PASS", "S3d atmospheric source audit is not PASS")
    require(
        int(run_contract.get("events", -1)) == ATM_EVENTS,
        f"S3d atmospheric manifest events={run_contract.get('events')}",
    )
    require(
        int(run_contract.get("seed", -1)) == ATM_SEED,
        f"S3d atmospheric manifest seed={run_contract.get('seed')}",
    )
    require(
        float(contract.get("active_veto_threshold_keV", -1)) == ACTIVE_VETO_THRESHOLD_KEV,
        "S3d atmospheric selection threshold is not 50 keV",
    )
    require(
        contract.get("energy_windows_keV", {}).get("w2_510p58_511p42") == list(W2),
        "S3d atmospheric W2 contract changed",
    )
    require(
        len(source_geometry(S3D_ATM_SOURCE)) == 1
        and geometry_matches(source_geometry(S3D_ATM_SOURCE)[0], S3D_SETUP),
        "S3d atmospheric source points at the wrong geometry",
    )
    header_quick = sim_header(S3D_ATM_SIM)
    require(
        geometry_matches(header_quick.get("geometry"), S3D_SETUP),
        "S3d atmospheric SIM geometry mismatch",
    )
    require(
        header_quick.get("seed") == ATM_SEED,
        f"S3d atmospheric SIM seed={header_quick.get('seed')}",
    )

    # Observation time is written at transport completion.  Check it before
    # scanning the large SIM so a live production file remains cleanly PENDING.
    observation_time_s = observation_time_from_log(S3D_ATM_LOG, running_is_pending=True)
    base = load_module("s3d_screening_atm_base", ATM_BASE_SCRIPT)
    base.SIM = S3D_ATM_SIM
    base.LOG = S3D_ATM_LOG
    base.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    base.is_active_veto_volume = is_active_veto_volume
    step05 = base.load_step05_module()
    step05.is_v3p5_active_veto_volume = is_active_veto_volume
    cat = base.parse_catalog()
    require(
        int(cat["generated_events"]) == ATM_EVENTS,
        f"S3d atmospheric catalog ID count={cat['generated_events']}",
    )
    # The catalog parser counts ID records while applying detector selection,
    # but it does not retain SE.  Perform an explicit full-stream SE/ID audit so
    # the public sim_header is observed data, not a copy of the requested 3M.
    header = sim_header(S3D_ATM_SIM, count_events=True)
    require(
        geometry_matches(header.get("geometry"), S3D_SETUP),
        "counted S3d atmospheric SIM geometry mismatch",
    )
    require(header.get("seed") == ATM_SEED, "counted S3d atmospheric SIM seed mismatch")
    require(
        header.get("SE") == ATM_EVENTS and header.get("ID") == ATM_EVENTS,
        f"S3d atmospheric observed SE/ID={header.get('SE')}/{header.get('ID')}, expected {ATM_EVENTS}",
    )
    require(
        int(cat["generated_events"]) == int(header["ID"]),
        "S3d atmospheric catalog ID count disagrees with full-stream header audit",
    )
    cat["observation_time_s"] = observation_time_s
    source_model = manifest.get("source_model_frozen_from_c0", {})
    phi_4pi = float(source_model.get("phi_4pi_ph_cm2_s", 0.0))
    require(phi_4pi > 0.0, "S3d atmospheric 4pi flux is missing or non-positive")
    w2 = base.summarize_window(cat, step05, *W2, phi_4pi)
    broad = base.summarize_window(cat, step05, *BROAD, phi_4pi)
    event_weight = 1.0 / observation_time_s
    c0_atm = c0["atm_case"]
    c0_w2 = c0_atm["windows"]["w2_510p58_511p42"]
    c0_broad = c0_atm["windows"]["broad_480_550"]

    relative: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    for window_name, current, baseline in (
        ("w2_510p58_511p42", w2, c0_w2),
        ("broad_480_550", broad, c0_broad),
    ):
        relative[window_name] = {}
        for stage, count_key, rate_key in ATM_STAGES:
            c0_count = int(baseline[count_key])
            s3d_count = int(current[count_key])
            c0_value = float(baseline[rate_key])
            s3d_value = float(current[rate_key])
            c0_weight = float(baseline["event_rate_weight_cps"])
            ratio = s3d_value / c0_value if c0_value > 0 else None
            ratio_ci = poisson_rate_ratio_interval(s3d_count, event_weight, c0_count, c0_weight)
            relative[window_name][stage] = {
                "c0_events": c0_count,
                "s3d_events": s3d_count,
                "c0_rate_cps": c0_value,
                "s3d_rate_cps": s3d_value,
                "s3d_over_c0": ratio,
                "ratio_counting_95": ratio_ci,
            }
            if window_name == "w2_510p58_511p42":
                rows.append(
                    comparison_row(
                        section="atm511",
                        component="atm511",
                        stage=stage,
                        metric="W2_rate",
                        unit="cps",
                        c0_count=c0_count,
                        c0_value=c0_value,
                        c0_weight=c0_weight,
                        s3d_count=s3d_count,
                        s3d_value=s3d_value,
                        s3d_weight=event_weight,
                        note="matched 3M 4pi sidecar; Garwood marginal rate CI",
                    )
                )
    tes_events = int((cat["tes_total_keV"] > 0.0).sum())
    payload = {
        "status": "PASS_S3D_ATM511_4PI_SIDECAR_REPLAY",
        "generated_at_utc": now_utc(),
        "claim_boundary": (
            "Semi-empirical S1 atmospheric-511 sidecar transported with the frozen C0 source model; "
            "this is not a native EXPACS line component."
        ),
        "inputs": {
            "manifest": rel(S3D_ATM_MANIFEST),
            "source": rel(S3D_ATM_SOURCE),
            "log": rel(S3D_ATM_LOG),
            "sim": rel(S3D_ATM_SIM),
            "c0_summary": rel(S3C_ATM_SUMMARY),
        },
        "sim_header": header,
        "transport": {
            "status": "PASS_COMPLETE_READABLE_SIM",
            "events_requested": ATM_EVENTS,
            "events_generated": int(cat["generated_events"]),
            "SE": int(header["SE"]),
            "ID": int(header["ID"]),
            "count_authority": header["count_authority"],
            "seed": ATM_SEED,
            "geometry": rel(S3D_SETUP),
        },
        "source_model": {
            "phi_4pi_ph_cm2_s": phi_4pi,
            "depth_g_cm2": source_model.get("depth_g_cm2"),
            "Rc_GV": source_model.get("Rc_GV"),
            "source_model": source_model.get("source_model"),
        },
        "normalization": {
            "observation_time_s": observation_time_s,
            "event_rate_weight_cps": event_weight,
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "selection_contract": contract,
        },
        "catalog": {
            "generated_events": int(cat["generated_events"]),
            "kept_events_tes_or_active": int(cat["kept_events_tes_or_active"]),
            "detector_catalog_event_rate_cps": int(cat["kept_events_tes_or_active"]) * event_weight,
            "tes_events": tes_events,
            "tes_event_rate_cps": tes_events * event_weight,
            "observation_time_s": observation_time_s,
        },
        "windows": {"w2_510p58_511p42": w2, "broad_480_550": broad},
        "relative_to_c0": relative,
    }
    return payload, rows


def summarize_unit_signal(proxy: Any, step05: Any, disk: dict[str, Any], sim: Path) -> dict[str, Any]:
    generated, tes_kept, candidates = proxy.line_window_candidates(sim)
    active_ids: set[int] = set()
    final_ids: set[int] = set()
    class_counts: Counter[str] = Counter()
    active_energy_by_id: dict[int, float] = {}
    final_energy_by_id: dict[int, float] = {}
    cur_id: int | None = None
    in_candidate = False
    active_total = 0.0
    pix: dict[str, dict[str, Any]] = {}

    def flush() -> None:
        nonlocal cur_id, in_candidate, active_total, pix
        if cur_id is not None and in_candidate:
            tes_total, hits = proxy.hits_from_pix(pix)
            if active_total < ACTIVE_VETO_THRESHOLD_KEV:
                active_ids.add(cur_id)
                active_energy_by_id[cur_id] = active_total
                keep, cls = step05.side_keep_from_hits(hits, disk, "keep")
                class_counts[cls] += 1
                if keep:
                    final_ids.add(cur_id)
                    final_energy_by_id[cur_id] = float(candidates.get(cur_id, tes_total))
        cur_id = None
        in_candidate = False
        active_total = 0.0
        pix = {}

    for line in proxy.iter_filtered_sim_lines(sim, proxy.TP_ACTIVE_FILTER_RE):
        if not line:
            continue
        if line == "SE":
            flush()
            continue
        match_id = proxy.ID_RE.match(line)
        if match_id:
            cur_id = int(match_id.group(1))
            in_candidate = cur_id in candidates
            active_total = 0.0
            pix = {}
            continue
        if not in_candidate or not line.startswith("CC HIT "):
            continue
        hit = proxy.parse_cc_hit(line)
        if hit is None:
            continue
        volume, edep, x, y, z = hit
        match_tp = proxy.TP_RE.match(volume)
        if match_tp:
            rec = pix.setdefault(
                volume,
                {
                    "e": 0.0,
                    "wx": 0.0,
                    "wy": 0.0,
                    "wz": 0.0,
                    "layer": int(match_tp.group("layer")),
                },
            )
            rec["e"] += edep
            rec["wx"] += edep * x
            rec["wy"] += edep * y
            rec["wz"] += edep * z
        elif step05.is_v3p5_active_veto_volume(volume):
            active_total += edep
    flush()
    return {
        "generated_events_seen": generated,
        "tes_events_kept": tes_kept,
        "window_keV": list(W2),
        "raw_events": len(candidates),
        "active_veto_pass_events": len(active_ids),
        "side_compton_fov_pass_events": len(final_ids),
        "raw_acceptance": len(candidates) / SIGNAL_TRIGGERS,
        "active_veto_pass_acceptance": len(active_ids) / SIGNAL_TRIGGERS,
        "side_compton_fov_pass_acceptance": len(final_ids) / SIGNAL_TRIGGERS,
        "side_compton_class_counts": dict(sorted(class_counts.items())),
        "raw_event_ids_sha256": sha256_ids(set(candidates)),
        "active_event_ids_sha256": sha256_ids(active_ids),
        "final_event_ids_sha256": sha256_ids(final_ids),
        "final_event_ids": final_ids,
        "final_examples": [
            {
                "event_id": event_id,
                "tes_total_keV": final_energy_by_id[event_id],
                "active_veto_keV": active_energy_by_id[event_id],
            }
            for event_id in sorted(final_ids)[:20]
        ],
    }


def analyze_signal() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    require_file(SIGNAL_MANIFEST, "matched signal replay manifest")
    manifest = load_json(SIGNAL_MANIFEST)
    contract = manifest.get("matched_contract", {})
    eventlist = manifest.get("reference_authority", {}).get("eventlist_audit", {})
    require(eventlist.get("status") == "PASS", "matched signal EventList audit is not PASS")
    require(int(eventlist.get("rows", -1)) == SIGNAL_TRIGGERS, "matched signal EventList does not have 37,194 rows")
    require(int(contract.get("triggers", -1)) == SIGNAL_TRIGGERS, "matched signal trigger contract changed")
    require(int(contract.get("seed", -1)) == SIGNAL_SEED, "matched signal seed contract changed")
    require(
        contract.get("canonical_sources_identical_except_geometry_run_output") is True,
        "matched signal sources differ beyond geometry/run/output",
    )
    require(
        float(contract.get("selection", {}).get("active_veto_threshold_keV", -1))
        == ACTIVE_VETO_THRESHOLD_KEV,
        "matched signal selection threshold is not 50 keV",
    )
    proxy, step05, disk = selection_modules()
    analyzed: dict[str, Any] = {}
    for key, branch in SIGNAL_BRANCHES.items():
        require_file(branch["source"], f"{branch['label']} matched signal source")
        require_file(branch["sim"], f"{branch['label']} matched signal SIM")
        require(
            len(source_geometry(branch["source"])) == 1
            and geometry_matches(source_geometry(branch["source"])[0], branch["geometry"]),
            f"{branch['label']} signal source points at wrong geometry",
        )
        header = sim_header(branch["sim"], count_events=True)
        require(
            geometry_matches(header.get("geometry"), branch["geometry"]),
            f"{branch['label']} signal SIM points at wrong geometry",
        )
        require(header.get("seed") == SIGNAL_SEED, f"{branch['label']} signal seed mismatch")
        require(
            header.get("SE") == SIGNAL_TRIGGERS and header.get("ID") == SIGNAL_TRIGGERS,
            f"{branch['label']} signal SE/ID={header.get('SE')}/{header.get('ID')}",
        )
        summary = summarize_unit_signal(proxy, step05, disk, branch["sim"])
        require(
            summary["generated_events_seen"] == SIGNAL_TRIGGERS,
            f"{branch['label']} signal analyzed event count mismatch",
        )
        summary["final_acceptance_wilson_95"] = wilson_interval(
            summary["side_compton_fov_pass_events"], SIGNAL_TRIGGERS
        )
        analyzed[key] = {
            "label": branch["label"],
            "geometry": rel(branch["geometry"]),
            "source": rel(branch["source"]),
            "sim": rel(branch["sim"]),
            "sim_header": header,
            "selection": {k: v for k, v in summary.items() if k != "final_event_ids"},
            "_final_ids": summary["final_event_ids"],
        }

    c0 = analyzed["s3c_c0"]
    s3d = analyzed["s3d_o9"]
    c0_sel = c0["selection"]
    s3d_sel = s3d["selection"]
    c0_final = int(c0_sel["side_compton_fov_pass_events"])
    s3d_final = int(s3d_sel["side_compton_fov_pass_events"])
    require(c0_final > 0, "matched C0 signal final acceptance is zero; loss gate is undefined")
    ratio = s3d_final / c0_final
    loss = 1.0 - ratio
    ratio_ci = risk_ratio_interval(s3d_final, SIGNAL_TRIGGERS, c0_final, SIGNAL_TRIGGERS)
    c0_ids = c0.pop("_final_ids")
    s3d_ids = s3d.pop("_final_ids")
    paired = {
        "both_pass": len(c0_ids & s3d_ids),
        "c0_only": len(c0_ids - s3d_ids),
        "s3d_only": len(s3d_ids - c0_ids),
        "neither": SIGNAL_TRIGGERS - len(c0_ids | s3d_ids),
    }
    gate_pass = loss <= SIGNAL_LOSS_LIMIT
    comparison = {
        "s3d_over_c0_final_acceptance": ratio,
        "risk_ratio_counting_95_katz": ratio_ci,
        "relative_signal_loss": loss,
        "paired_acceptance_counts": paired,
        "promotion_limit_relative_loss": SIGNAL_LOSS_LIMIT,
        "promotion_gate_pass": gate_pass,
        "gate_policy": "central matched acceptance loss <= 2%; interval is reported, not substituted for the stated central gate",
    }
    payload = {
        "status": "PASS_MATCHED_S3C_C0_S3D_SIGNAL_REPLAY_ANALYZED",
        "generated_at_utc": now_utc(),
        "claim_boundary": "Matched detector-transport and W2 selection only; not an optics-background simulation.",
        "manifest": rel(SIGNAL_MANIFEST),
        "eventlist_audit": eventlist,
        "selection_contract": contract.get("selection"),
        "branches": {"s3c_c0": c0, "s3d_o9": s3d},
        "comparison": comparison,
    }
    c0_ci = c0_sel["final_acceptance_wilson_95"]
    s3d_ci = s3d_sel["final_acceptance_wilson_95"]
    row = {
        "section": "signal",
        "component": "focused_f10m_a1",
        "stage": "side_compton_fov_pass",
        "metric": "W2_acceptance",
        "unit": "fraction",
        "c0_count": c0_final,
        "c0_value": c0_final / SIGNAL_TRIGGERS,
        "c0_ci95_low": c0_ci["low"],
        "c0_ci95_high": c0_ci["high"],
        "s3d_count": s3d_final,
        "s3d_value": s3d_final / SIGNAL_TRIGGERS,
        "s3d_ci95_low": s3d_ci["low"],
        "s3d_ci95_high": s3d_ci["high"],
        "s3d_over_c0": ratio,
        "ratio_ci95_low": ratio_ci["low"],
        "ratio_ci95_high": ratio_ci["high"],
        "gate_limit": SIGNAL_LOSS_LIMIT,
        "gate_pass": gate_pass,
        "note": "matched 37,194-row EventList; paired pass/loss table is in JSON",
    }
    return payload, [row]


def audit_delayed_authority(
    *,
    summary_path: Path,
    campaign_path: Path,
    expected_geometry: Path,
    label: str,
    new_chain: bool,
) -> dict[str, Any]:
    require_file(summary_path, f"{label} exact-position delayed summary", retained=not new_chain)
    require_file(campaign_path, f"{label} delayed campaign", retained=not new_chain)
    summary = load_json(summary_path)
    campaign = load_json(campaign_path)
    if new_chain and campaign.get("status") != "PASS_S3D_O9_NEUTRON_DELAYED_TRANSPORT":
        if campaign.get("status") == "S3D_O9_NEUTRON_DELAYED_CHAIN_INCOMPLETE":
            raise PendingInput(f"waiting for completed S3d neutron-only delayed chain: {rel(campaign_path)}")
        raise AuditFailure(f"unexpected S3d delayed campaign status: {campaign.get('status')}")
    if not new_chain:
        require(
            campaign.get("status") == "PASS_S3C_NEUTRON_DELAYED_CHAIN_M50000_TRANSPORT",
            f"bad retained S3c delayed campaign status: {campaign.get('status')}",
        )
    require(str(summary.get("status", "")).startswith("PASS"), f"{label} delayed summary is not PASS")
    activity = float(summary.get("fixed_total_activity_Bq", -1.0))
    require(activity >= 0.0, f"{label} fixed delayed activity is invalid")
    require(
        abs(float(summary.get("sum_flux_check_Bq", activity)) - activity) <= max(1.0e-7, 1.0e-8 * activity),
        f"{label} delayed activity/flux closure failed",
    )
    sampling = summary.get("sampling_audit", {})
    require(sampling.get("status") == "PASS" and not sampling.get("problems"), f"{label} sampling audit failed")
    transport = summary.get("delayed_transport", {})
    require(transport.get("SE") == DELAYED_EVENTS and transport.get("ID") == DELAYED_EVENTS, f"{label} delayed SE/ID mismatch")
    require(geometry_matches(transport.get("geometry"), expected_geometry), f"{label} delayed geometry mismatch")
    te_s = float(transport.get("TE_s") or 0.0)
    require(te_s > 0.0, f"{label} delayed TE_s is not positive")
    sim = ROOT / transport["path"] if not Path(transport["path"]).is_absolute() else Path(transport["path"])
    require_file(sim, f"{label} delayed SIM", retained=not new_chain)
    header = sim_header(sim)
    require(geometry_matches(header.get("geometry"), expected_geometry), f"{label} delayed SIM header mismatch")
    if new_chain:
        require_file(S3D_DELAY_FIX_AUDIT, "S3d ground-state/TT normalization audit")
        fix = load_json(S3D_DELAY_FIX_AUDIT)
        require(fix.get("status") == "PASS" and not fix.get("problems"), "S3d delayed ground-state fix is not PASS")
        rows = fix.get("rows") or []
        require(len(rows) == 1 and rows[0].get("tag") == "n", "S3d delayed normalization row is not neutron-only")
        row = rows[0]
        require(
            int(row.get("files", -1)) == 8
            and float(row.get("division", -1)) == 8.0
            and int(row.get("tt_count", -1)) == 8
            and int(row.get("tt_files", -1)) == 8
            and int(row.get("tt_line_count", -1)) == 8,
            f"S3d delayed TT/division guard failed: {row}",
        )
        stats = campaign.get("statistics", {})
        expected_stats = {
            "non_gamma_div": 8,
            "n_sample": 2_000_000,
            "raw_triggers": 1_000_000,
            "m_blocks": 50_000,
            "seed": DELAYED_SEED,
        }
        for key, expected in expected_stats.items():
            require(stats.get(key) == expected, f"S3d delayed statistics {key} changed")
        normalization_evidence: Any = {"path": rel(S3D_DELAY_FIX_AUDIT), "row": row, "status": "PASS"}
    else:
        fixed = campaign.get("fixed_source", {})
        require(
            fixed.get("normalization_status") == "PASS" and not fixed.get("normalization_problems"),
            "retained S3c delayed normalization is not PASS",
        )
        stats = campaign.get("statistics", {})
        require(stats.get("non_gamma_div") == 8 and stats.get("non_gamma_replicas") == 8, "retained S3c TT division changed")
        normalization_evidence = fixed
    return {
        "status": "PASS",
        "summary": rel(summary_path),
        "campaign": rel(campaign_path),
        "fixed_total_activity_Bq": activity,
        "sampling_audit": sampling,
        "transport": transport,
        "sim": sim,
        "TE_s": te_s,
        "normalization_evidence": normalization_evidence,
    }


def analyze_delayed() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    c0 = audit_delayed_authority(
        summary_path=S3C_DELAYED_SUMMARY,
        campaign_path=S3C_DELAYED_CAMPAIGN,
        expected_geometry=S3C_SETUP,
        label="S3c-C0",
        new_chain=False,
    )
    s3d = audit_delayed_authority(
        summary_path=S3D_DELAYED_SUMMARY,
        campaign_path=S3D_DELAYED_CAMPAIGN,
        expected_geometry=S3D_SETUP,
        label="S3d-O9",
        new_chain=True,
    )
    proxy, step05, disk = selection_modules()
    c0_selected = proxy.summarize_sim_stream(step05, c0["sim"], 1.0 / c0["TE_s"], disk, "keep")
    s3d_selected = proxy.summarize_sim_stream(step05, s3d["sim"], 1.0 / s3d["TE_s"], disk, "keep")
    require(c0_selected["generated_events_seen"] == DELAYED_EVENTS, "C0 delayed analyzed event count mismatch")
    require(s3d_selected["generated_events_seen"] == DELAYED_EVENTS, "S3d delayed analyzed event count mismatch")
    rows: list[dict[str, Any]] = []
    for stage, count_key, rate_key in STAGES:
        rows.append(
            comparison_row(
                section="delayed_transport",
                component="neutron_only_delayed",
                stage=stage,
                metric="W2_rate",
                unit="cps",
                c0_count=int(c0_selected[count_key]),
                c0_value=float(c0_selected[rate_key]),
                c0_weight=1.0 / c0["TE_s"],
                s3d_count=int(s3d_selected[count_key]),
                s3d_value=float(s3d_selected[rate_key]),
                s3d_weight=1.0 / s3d["TE_s"],
                note="neutron-only day-15 delayed transport; rates normalized by 1/Cosima TE_s",
            )
        )
    activity_gate = s3d["fixed_total_activity_Bq"] <= DELAYED_ACTIVITY_LIMIT_BQ
    activity_ratio = (
        s3d["fixed_total_activity_Bq"] / c0["fixed_total_activity_Bq"]
        if c0["fixed_total_activity_Bq"] > 0
        else None
    )
    rows.append(
        {
            "section": "delayed_source",
            "component": "neutron_only_delayed",
            "stage": "day15_groundstate_fixed",
            "metric": "fixed_total_activity",
            "unit": "Bq",
            "c0_value": c0["fixed_total_activity_Bq"],
            "s3d_value": s3d["fixed_total_activity_Bq"],
            "s3d_over_c0": activity_ratio,
            "gate_limit": DELAYED_ACTIVITY_LIMIT_BQ,
            "gate_pass": activity_gate,
            "note": "source-side activity; no simple counting interval is asserted",
        }
    )
    payload = {
        "status": "PASS_S3D_NEUTRON_ONLY_DELAYED_SCREEN_ANALYZED",
        "claim_boundary": "Neutron-only activation and delayed transport, not the complete delayed background.",
        "s3c_c0": {**{k: v for k, v in c0.items() if k != "sim"}, "selection": c0_selected},
        "s3d_o9": {**{k: v for k, v in s3d.items() if k != "sim"}, "selection": s3d_selected},
        "comparison": {
            "activity_ratio_s3d_over_c0": activity_ratio,
            "activity_limit_Bq": DELAYED_ACTIVITY_LIMIT_BQ,
            "activity_gate_pass": activity_gate,
        },
    }
    return payload, rows


def dominant_gate(
    c0: dict[str, Any], prompt: dict[str, Any], atm: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for particle in PROMPT_PARTICLES:
        c0_summary = c0["prompt_cases"][particle]["summary"]
        s3d_summary = prompt["cases"][particle]["summary"]
        components.append(
            {
                "component": particle,
                "c0_events": int(c0_summary["side_compton_fov_pass_events"]),
                "c0_rate_cps": float(c0_summary["side_compton_fov_pass_rate_s-1"]),
                "c0_weight_cps": float(c0["prompt_cases"][particle]["rate_per_event_s-1"]),
                "s3d_events": int(s3d_summary["side_compton_fov_pass_events"]),
                "s3d_rate_cps": float(s3d_summary["side_compton_fov_pass_rate_s-1"]),
                "s3d_weight_cps": float(prompt["cases"][particle]["rate_per_event_s-1"]),
            }
        )
    c0_atm = c0["atm_case"]["windows"]["w2_510p58_511p42"]
    s3d_atm = atm["windows"]["w2_510p58_511p42"]
    components.append(
        {
            "component": "atm511",
            "c0_events": int(c0_atm["side_compton_fov_pass_events"]),
            "c0_rate_cps": float(c0_atm["final_rate_cps"]),
            "c0_weight_cps": float(c0_atm["event_rate_weight_cps"]),
            "s3d_events": int(s3d_atm["side_compton_fov_pass_events"]),
            "s3d_rate_cps": float(s3d_atm["final_rate_cps"]),
            "s3d_weight_cps": float(s3d_atm["event_rate_weight_cps"]),
        }
    )
    c0_rate = sum(row["c0_rate_cps"] for row in components)
    s3d_rate = sum(row["s3d_rate_cps"] for row in components)
    c0_sigma = math.sqrt(sum(row["c0_events"] * row["c0_weight_cps"] ** 2 for row in components))
    s3d_sigma = math.sqrt(sum(row["s3d_events"] * row["s3d_weight_cps"] ** 2 for row in components))
    z = float(norm.ppf(0.975))
    result = {
        "components": components,
        "definition": "final W2 eplus + neutron + atmospheric-511 matched screening subset",
        "excludes": "retained non-dominant residual and all other prompt families",
        "c0_rate_cps": c0_rate,
        "s3d_rate_cps": s3d_rate,
        "s3d_over_c0": s3d_rate / c0_rate if c0_rate > 0 else None,
        "c0_counting_95_gaussian_propagation": [max(0.0, c0_rate - z * c0_sigma), c0_rate + z * c0_sigma],
        "s3d_counting_95_gaussian_propagation": [max(0.0, s3d_rate - z * s3d_sigma), s3d_rate + z * s3d_sigma],
        "promotion_limit_cps": DOMINANT_LIMIT_CPS,
        "promotion_gate_pass": s3d_rate <= DOMINANT_LIMIT_CPS,
        "gate_policy": "central matched subset rate <= 0.0052 cps; interval is diagnostic",
    }
    csv_row = {
        "section": "dominant_subset",
        "component": "eplus+n+atm511",
        "stage": "side_compton_fov_pass",
        "metric": "W2_rate_sum",
        "unit": "cps",
        "c0_count": sum(row["c0_events"] for row in components),
        "c0_value": c0_rate,
        "c0_ci95_low": result["c0_counting_95_gaussian_propagation"][0],
        "c0_ci95_high": result["c0_counting_95_gaussian_propagation"][1],
        "s3d_count": sum(row["s3d_events"] for row in components),
        "s3d_value": s3d_rate,
        "s3d_ci95_low": result["s3d_counting_95_gaussian_propagation"][0],
        "s3d_ci95_high": result["s3d_counting_95_gaussian_propagation"][1],
        "s3d_over_c0": result["s3d_over_c0"],
        "gate_limit": DOMINANT_LIMIT_CPS,
        "gate_pass": result["promotion_gate_pass"],
        "note": "central gate; counting CI uses independent-Poisson Gaussian propagation across unequal weights",
    }
    return result, csv_row


def pending_payload(kind: str, pending: list[str], failures: list[str]) -> dict[str, Any]:
    if failures:
        status = f"FAIL_{kind}_AUDIT"
    else:
        status = f"PENDING_{kind}_INPUTS"
    return {
        "status": status,
        "generated_at_utc": now_utc(),
        "pending_inputs": pending,
        "audit_failures": failures,
        "no_zero_substitution": True,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# S3c-C0 versus S3d-O9 Screening Analysis",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This package is a matched screening comparison. It is not the complete eight-family prompt + full delayed Step05-Step08 performance closure.",
        "",
    ]
    if payload.get("pending_inputs"):
        lines.extend(["## Pending inputs", ""])
        lines.extend(f"- {item}" for item in payload["pending_inputs"])
        lines.append("")
    if payload.get("audit_failures"):
        lines.extend(["## Audit failures", ""])
        lines.extend(f"- {item}" for item in payload["audit_failures"])
        lines.append("")
    gates = payload.get("promotion_gates")
    if gates:
        lines.extend(
            [
                "## Promotion gates",
                "",
                f"Decision so far: `{gates.get('decision_so_far', 'PENDING')}`",
                "",
            ]
        )
        if gates.get("any_evaluated_gate_failed"):
            lines.extend(
                [
                    "The O9 candidate is ineligible for promotion and its full-chain production is not authorized. "
                    "The pending delayed diagnostic cannot reverse a failed mandatory gate.",
                    "",
                ]
            )
        lines.extend(
            [
                "| gate | S3d result | limit | state |",
                "|---|---:|---:|---:|",
            ]
        )
        dominant = gates.get("dominant_subset", {})
        if dominant.get("evaluation_status") in ("PASS", "FAIL"):
            lines.append(
                f"| final W2 dominant subset | {dominant['s3d_rate_cps']:.9g} cps | "
                f"{DOMINANT_LIMIT_CPS:.9g} cps | `{dominant['evaluation_status']}` |"
            )
        else:
            lines.append(
                f"| final W2 dominant subset | pending | {DOMINANT_LIMIT_CPS:.9g} cps | `PENDING` |"
            )
        signal = gates.get("signal", {})
        if signal.get("evaluation_status") in ("PASS", "FAIL"):
            lines.append(
                f"| matched focused-signal loss | {signal['relative_signal_loss']:.6%} | "
                f"{SIGNAL_LOSS_LIMIT:.2%} | `{signal['evaluation_status']}` |"
            )
        else:
            lines.append(
                f"| matched focused-signal loss | pending | {SIGNAL_LOSS_LIMIT:.2%} | `PENDING` |"
            )
        delayed = gates.get("delayed", {})
        if delayed.get("evaluation_status") in ("PASS", "FAIL"):
            lines.append(
                f"| neutron-only day-15 activity | {delayed['s3d_activity_Bq']:.9g} Bq | "
                f"{DELAYED_ACTIVITY_LIMIT_BQ:.9g} Bq | `{delayed['evaluation_status']}` |"
            )
        else:
            lines.append(
                f"| neutron-only day-15 activity | pending | {DELAYED_ACTIVITY_LIMIT_BQ:.9g} Bq | `PENDING` |"
            )
        lines.append("")
    sections = payload.get("sections", {})
    if sections:
        lines.extend(["## Section status", "", "| section | status |", "|---|---|"])
        for name in ("prompt", "atm511", "signal", "neutron_only_delayed"):
            section = sections.get(name, {})
            lines.append(f"| {name} | `{section.get('status', 'PENDING')}` |")
        lines.append("")
    lines.extend(
        [
            "## Frozen selection",
            "",
            "- W2: `510.58 <= TES energy < 511.42 keV`.",
            "- Active-veto acceptance: summed matched active energy `< 50 keV`; BGO/CsI/ActiveShield/CEBR3 and retained plastic active volumes included; W/Al excluded.",
            "- Side-entry Compton/FoV: retained Step05 `side_keep_from_hits`, reject policy `keep`.",
            "- The literal Knob0 S0/S1-retain rule is not used.",
            "",
            "## Counting intervals",
            "",
            "Component rate intervals are exact two-sided 95% Garwood intervals. Component rate-ratio intervals use the exact conditional Poisson construction. Signal acceptances use Wilson 95% intervals; its ratio interval uses the Katz approximation and the JSON also records the paired pass/loss table.",
            "",
            "Generated files: `data/s3d_screening_analysis.json`, `data/s3d_screening_comparison.csv`, `data/s3d_atm511_replay_summary.json`, and `data/s3d_signal_replay_summary.json`.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="only audit input presence/status; do not scan completed SIM payloads",
    )
    args = parser.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    if args.status_only:
        atm_complete = False
        if S3D_ATM_LOG.is_file():
            atm_complete = "Observation time:" in log_tail_text(S3D_ATM_LOG)
        delayed_status = None
        if S3D_DELAYED_CAMPAIGN.is_file():
            try:
                delayed_status = load_json(S3D_DELAYED_CAMPAIGN).get("status")
            except (OSError, json.JSONDecodeError):
                delayed_status = "UNREADABLE"
        readiness = {
            "prompt_run_summary": (S3D_PROMPT_DIR / "run_summary.json").is_file(),
            "atm_completion_record": atm_complete,
            "signal_s3c_c0_sim": SIGNAL_BRANCHES["s3c_c0"]["sim"].is_file(),
            "signal_s3d_o9_sim": SIGNAL_BRANCHES["s3d_o9"]["sim"].is_file(),
            "delayed_campaign_status": delayed_status,
            "delayed_exact_summary": S3D_DELAYED_SUMMARY.is_file(),
        }
        ready = (
            readiness["prompt_run_summary"]
            and readiness["atm_completion_record"]
            and readiness["signal_s3c_c0_sim"]
            and readiness["signal_s3d_o9_sim"]
            and readiness["delayed_campaign_status"]
            == "PASS_S3D_O9_NEUTRON_DELAYED_TRANSPORT"
            and readiness["delayed_exact_summary"]
        )
        print(
            json.dumps(
                {
                    "status": "READY_FOR_FULL_ANALYSIS" if ready else "PENDING_INPUTS",
                    "readiness": readiness,
                    "outputs_unchanged": True,
                },
                indent=2,
            )
        )
        return 0
    pending: list[str] = []
    failures: list[str] = []
    rows: list[dict[str, Any]] = []
    sections: dict[str, Any] = {}

    try:
        c0 = audit_retained_c0()
    except (AuditFailure, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        c0 = {}
        failures.append(f"retained C0 authority: {exc}")

    def run_section(name: str, func: Any, *func_args: Any) -> Any | None:
        try:
            result, section_rows = func(*func_args)
            sections[name] = result
            rows.extend(section_rows)
            return result
        except PendingInput as exc:
            sections[name] = {"status": "PENDING", "reason": str(exc)}
            pending.append(f"{name}: {exc}")
            return None
        except (AuditFailure, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            sections[name] = {"status": "FAIL", "reason": str(exc)}
            failures.append(f"{name}: {exc}")
            return None

    prompt = run_section("prompt", analyze_prompt, c0) if c0 else None
    atm = run_section("atm511", analyze_atm, c0) if c0 else None
    signal = run_section("signal", analyze_signal)
    delayed = run_section("neutron_only_delayed", analyze_delayed)

    if atm is None:
        atm_pending = [item for item in pending if item.startswith("atm511:")]
        atm_fail = [item for item in failures if item.startswith("atm511:")]
        write_json(OUT_ATM, pending_payload("S3D_ATM511", atm_pending, atm_fail))
    else:
        write_json(OUT_ATM, atm)
    if signal is None:
        signal_pending = [item for item in pending if item.startswith("signal:")]
        signal_fail = [item for item in failures if item.startswith("signal:")]
        write_json(OUT_SIGNAL, pending_payload("S3D_SIGNAL_REPLAY", signal_pending, signal_fail))
    else:
        write_json(OUT_SIGNAL, signal)

    # Evaluate every gate as soon as its own inputs are available.  A pending
    # delayed chain must not hide an already-failed prompt+atm central-rate gate.
    promotion_gates: dict[str, Any] = {}
    if c0 and prompt and atm:
        dominant, dominant_row = dominant_gate(c0, prompt, atm)
        rows.append(dominant_row)
        dominant["evaluation_status"] = (
            "PASS" if dominant["promotion_gate_pass"] else "FAIL"
        )
        promotion_gates["dominant_subset"] = dominant
    else:
        promotion_gates["dominant_subset"] = {
            "evaluation_status": "PENDING",
            "reason": "requires retained C0, prompt eplus/neutron, and atmospheric-511 sections",
            "promotion_limit_cps": DOMINANT_LIMIT_CPS,
        }

    if signal:
        signal_gate = dict(signal["comparison"])
        signal_gate["evaluation_status"] = (
            "PASS" if signal_gate["promotion_gate_pass"] else "FAIL"
        )
        promotion_gates["signal"] = signal_gate
    else:
        promotion_gates["signal"] = {
            "evaluation_status": "PENDING",
            "reason": sections.get("signal", {}).get(
                "reason", "matched signal section unavailable"
            ),
            "promotion_limit_relative_loss": SIGNAL_LOSS_LIMIT,
        }

    if delayed:
        delayed_gate = delayed["comparison"]
        promotion_gates["delayed"] = {
            "evaluation_status": (
                "PASS" if delayed_gate["activity_gate_pass"] else "FAIL"
            ),
            "s3d_activity_Bq": delayed["s3d_o9"]["fixed_total_activity_Bq"],
            "limit_Bq": DELAYED_ACTIVITY_LIMIT_BQ,
            "promotion_gate_pass": delayed_gate["activity_gate_pass"],
        }
    else:
        promotion_gates["delayed"] = {
            "evaluation_status": "PENDING",
            "reason": sections.get("neutron_only_delayed", {}).get(
                "reason", "neutron-only delayed section unavailable"
            ),
            "limit_Bq": DELAYED_ACTIVITY_LIMIT_BQ,
        }

    gate_rows = [
        promotion_gates["dominant_subset"],
        promotion_gates["signal"],
        promotion_gates["delayed"],
    ]
    all_gates_evaluated = all(
        row["evaluation_status"] in ("PASS", "FAIL") for row in gate_rows
    )
    any_evaluated_gate_failed = any(
        row["evaluation_status"] == "FAIL" for row in gate_rows
    )
    promotion_gates["all_required_gates_evaluated"] = all_gates_evaluated
    promotion_gates["any_evaluated_gate_failed"] = any_evaluated_gate_failed
    promotion_gates["promotion_eligible"] = not any_evaluated_gate_failed
    promotion_gates["fullchain_authorized"] = not any_evaluated_gate_failed
    promotion_gates["decision_so_far"] = (
        "FAIL_AT_LEAST_ONE_COMPLETED_GATE"
        if any_evaluated_gate_failed
        else (
            "PASS_ALL_COMPLETED_GATES"
            if any(row["evaluation_status"] == "PASS" for row in gate_rows)
            else "PENDING"
        )
    )

    # A failed mandatory gate is terminal for promotion even if a separate
    # diagnostic input remains pending.  Preserve that pending input below,
    # but do not let it mask the fail-closed candidate decision.
    if not failures and any_evaluated_gate_failed:
        status = "FAIL_S3D_SCREENING_PROMOTION_GATES"
    elif not failures and not pending and all_gates_evaluated:
        all_pass = all(
            row.get("promotion_gate_pass") is True for row in gate_rows
        )
        status = (
            "PASS_S3D_SCREENING_PROMOTION_GATES"
            if all_pass
            else "FAIL_S3D_SCREENING_PROMOTION_GATES"
        )
    elif failures:
        status = "FAIL_S3D_SCREENING_AUDIT"
    else:
        status = "PENDING_S3D_SCREENING_INPUTS"

    if not rows:
        rows.append(
            {
                "section": "analysis",
                "component": "all",
                "stage": "input_audit",
                "metric": "status",
                "note": status,
            }
        )
    payload = {
        "status": status,
        "generated_at_utc": now_utc(),
        "claim_boundary": (
            "Matched S3c-C0 versus S3d screening for eplus/neutron prompt, atmospheric-511, "
            "focused signal, and neutron-only delayed activation/transport. This is not full "
            "eight-family prompt + complete delayed Step05-Step08 closure."
        ),
        "pending_inputs": pending,
        "audit_failures": failures,
        "no_zero_substitution": True,
        "selection_contract": {
            "w2_window_keV": list(W2),
            "interval_policy": "lower-inclusive, upper-exclusive",
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "active_veto_volume_rule": (
                "BGO/CsI active scintillator + ActiveShield/CEBR3 + "
                "GeoOpt_S1_PlasticFullWrap* + GeoOpt_S2B_CryoShell_Plastic*; W/Al excluded"
            ),
            "side_compton_fov": f"{rel(STEP05_SCRIPT)}::side_keep_from_hits(reject_policy='keep')",
            "knob0": "frozen monotonic policy; literal S0/S1-retain rule not promoted",
        },
        "counting_interval_contract": {
            "component_rates": "two-sided 95% Garwood exact Poisson interval",
            "component_rate_ratios": "two-sided 95% exact conditional Poisson interval",
            "signal_acceptance": "two-sided 95% Wilson score interval",
            "signal_acceptance_ratio": "two-sided 95% Katz log-risk-ratio interval plus paired counts",
            "dominant_subset_sum": "independent-Poisson Gaussian propagation; diagnostic only",
            "scipy_version": scipy_version,
        },
        "algorithm_authority": {
            "prompt_parser": rel(PROMPT_PROXY),
            "prompt_parser_sha256": sha256(PROMPT_PROXY),
            "step05_side_compton": rel(STEP05_SCRIPT),
            "step05_side_compton_sha256": sha256(STEP05_SCRIPT),
            "atm_catalog_parser": rel(ATM_BASE_SCRIPT),
            "atm_catalog_parser_sha256": sha256(ATM_BASE_SCRIPT),
            "analysis_script": rel(Path(__file__)),
            "analysis_script_sha256": sha256(Path(__file__)),
        },
        "retained_c0_authority": c0,
        "sections": sections,
        "promotion_gates": promotion_gates,
        "outputs": {
            "json": rel(OUT_JSON),
            "csv": rel(OUT_CSV),
            "markdown": rel(OUT_MD),
            "atm_summary": rel(OUT_ATM),
            "signal_summary": rel(OUT_SIGNAL),
        },
    }
    write_json(OUT_JSON, payload)
    write_csv(OUT_CSV, rows)
    OUT_MD.write_text(markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": status,
                "pending": len(pending),
                "failures": len(failures),
                "json": rel(OUT_JSON),
                "csv": rel(OUT_CSV),
                "md": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 2 if status == "FAIL_S3D_SCREENING_AUDIT" else 0


if __name__ == "__main__":
    raise SystemExit(main())
