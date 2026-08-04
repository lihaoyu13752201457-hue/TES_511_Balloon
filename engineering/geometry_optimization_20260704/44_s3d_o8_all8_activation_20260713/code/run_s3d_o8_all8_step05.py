#!/usr/bin/env python3
"""Build the S3d-O8 all-family day-15 Step05 response, fail closed.

This postprocessor is deliberately separate from the retained package-42 and
package-43 runners.  It reuses their reviewed parser and event-selection
functions, but replaces the single neutron-delayed binding with an explicit
eight-family component manifest.  It never launches Cosima.

The required order of operations is intentional:

1. ``regression`` proves that the splice/selection path reproduces the retained
   neutron-only package-43 Step05 result.
2. ``components`` consumes package 44 only after its campaign has reached its
   terminal PASS state and writes the normalized family-component authority.
3. ``catalog`` replaces only the retained neutron-delayed block in the O8
   event catalogue; prompt and focused-signal records remain identical.
4. ``step05`` evaluates the frozen selection and reports delayed rates and
   Garwood limits separately for every incident family.

No Step06--Step08, 420 eV response, mission fold, or manuscript result is
claimed here.  Those products require separate dated rebuilds.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import inspect
import json
import math
import multiprocessing as mp
import pickle
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import numpy as np
from scipy.stats import beta, chi2


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
FULLCHAIN = PACKAGE / "fullchain"
STEP05_OUT = FULLCHAIN / "step05"
WORK = STEP05_OUT / "work"

O8_PACKAGE = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "43_geoopt_s3d_o8_fallback_20260712"
)
O8_GEOMETRY = (
    O8_PACKAGE
    / "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
GEOMETRY_BUNDLE_NAMES = (
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup",
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det",
    "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "Materials_DEMO2_DR_v3p5.geo",
)
PROMPT_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704/s3d_o8_fullstat_prompt_all8_20260712"
)
PROMPT_NORM = PROMPT_DIR / "normalization.json"
SIGNAL_SIM = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o8_f10m_a1_signal_replay_37194_20260712"
    / "Opticsim_laue_f10m_a1_s3d_o8_signal37194.inc1.id1.sim.gz"
)
ATM_SUMMARY = O8_PACKAGE / "data/s3d_o8_atm511_replay_summary.json"

BASE_CATALOG = O8_PACKAGE / "fullchain/step05/work/event_catalog.pkl"
BASE_STEP05 = (
    O8_PACKAGE
    / "fullchain/step05/step05_s3d_o8_fullchain_l1_response_summary.json"
)
OLD_NEUTRON_SIM = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "step02_delayed_transport_s3d_o8_neutron_delayed_m50000_20260712"
    / "DelayedDecayS3dO8NeutronM50000.inc1.id1.sim.gz"
)
OLD_EXACT_SUMMARY = O8_PACKAGE / "fullchain/delayed_source/delayed_source_exactpos_summary.json"

CAMPAIGN = DATA / "s3d_o8_all8_activation_campaign.json"
COMPONENTS_JSON = DATA / "s3d_o8_all8_delayed_components.json"
REGRESSION_JSON = DATA / "s3d_o8_all8_step05_neutron_regression.json"
PREFLIGHT_JSON = DATA / "s3d_o8_all8_step05_preflight.json"
CATALOG_AUDIT_JSON = DATA / "s3d_o8_all8_step05_catalog_audit.json"
CATALOG = WORK / "event_catalog.pkl"
STEP05_JSON = STEP05_OUT / "step05_s3d_o8_all8_activation_l1_response_summary.json"
STEP05_RATES = STEP05_OUT / "step05_s3d_o8_all8_activation_l1_rates.csv"

STEP05_IMPLEMENTATION = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
ADR_IMPLEMENTATION = ROOT / "old/code/tools/make_complete_day15_report_ADR.py"
BRIDGE_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
AEFF_AUTHORITY = (
    ROOT
    / "stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json"
)
SCIENCE_LEDGER = ROOT / "old/config/science_511_onaxis_source/metadata/science_rate_ledger.csv"
BOUNDARY_SUMMARY = (
    ROOT
    / "old/reports/v3p5_boundary_closure_fullstat_v2_exactpos_20260613"
    / "v3p5_boundary_closure_summary.json"
)

FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
FAMILY_SET = set(FAMILIES)
EXPECTED_COUNTS = {family: (12 if family == "gamma" else 8) for family in FAMILIES}
CAMPAIGN_PASS = "PASS_S3D_O8_ALL8_ACTIVATION_AND_FAMILY_DELAYED_TRANSPORT"
COMPONENT_PASS = "PASS_S3D_O8_ALL8_STEP05_DELAYED_COMPONENTS"
REGRESSION_PASS = "PASS_S3D_O8_NEUTRON_ONLY_STEP05_REGRESSION"
CATALOG_PASS = "PASS_S3D_O8_ALL8_STEP05_CATALOG"
STEP05_PASS = "PASS_S3D_O8_ALL8_ACTIVATION_STEP05_DAY15"
ZERO_STATUSES = {"PASS_ZERO_PRODUCTION", "PASS_ZERO_ACTIVITY"}

PROMPT_GENERATED = 25_210_216
SIGNAL_GENERATED = 37_194
DELAYED_GENERATED_PER_POSITIVE_FAMILY = 1_000_000
ACTIVE_VETO_THRESHOLD_KEV = 50.0
MISSION_DAYS = 20.0
SECONDS_PER_DAY = 86_400.0
REFERENCE_FLUX = 1.0e-4
CONFIDENCE = 0.95
ALPHA_TWO_SIDED = 1.0 - CONFIDENCE
TE_ACTIVITY_REL_TOL = 0.10
CACHE_SCHEMA_VERSION = 2
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}

CONFIRM_TOKEN = "RUN_S3D_O8_ALL8_STEP05_POSTPROCESS_20260713"

EVENT_FIELDS = (
    "stream",
    "tag",
    "source_file",
    "local_id",
    "rate_hz",
    "tes_total_keV",
    "bgo_total_keV",
    "pix_count",
)
PIXEL_FIELDS = ("pix_uid", "pix_layer", "pix_e", "pix_x", "pix_y", "pix_z")


class Step05GateError(RuntimeError):
    """A provenance, normalization, or regression gate failed."""


_SHA256_MEMO: dict[tuple[str, int, int], str] = {}
_SIM_METADATA_MEMO: dict[tuple[str, int, int], dict[str, Any]] = {}


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def rel(path: Path | str) -> str:
    value = Path(path)
    try:
        return value.resolve().relative_to(ROOT.resolve()).as_posix()
    except (ValueError, FileNotFoundError):
        return str(path)


def resolve_path(value: Path | str) -> Path:
    path = Path(str(value).strip())
    return (path if path.is_absolute() else ROOT / path).resolve()


def sha256(path: Path) -> str:
    resolved = path.resolve()
    stat = resolved.stat()
    key = (resolved.as_posix(), int(stat.st_size), int(stat.st_mtime_ns))
    cached = _SHA256_MEMO.get(key)
    if cached is not None:
        return cached
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    value = digest.hexdigest()
    _SHA256_MEMO[key] = value
    return value


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def json_bytes(path: Path) -> tuple[Any, str]:
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_json_if_changed(path: Path, payload: Any) -> bool:
    """Write stable JSON only when its exact serialized authority changed."""
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    records = list(rows)
    if not records:
        raise Step05GateError(f"refusing to write empty CSV: {rel(path)}")
    fields: list[str] = []
    for row in records:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Step05GateError(f"cannot import {rel(path)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def open_sim(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def sim_transport_metadata(path: Path) -> dict[str, Any]:
    """Read transport facts from the SIM itself, rather than its manifest."""
    resolved = path.resolve()
    stat = resolved.stat()
    key = (resolved.as_posix(), int(stat.st_size), int(stat.st_mtime_ns))
    cached = _SIM_METADATA_MEMO.get(key)
    if cached is not None:
        return cached

    geometry_values: list[str] = []
    seed_values: list[int | str] = []
    te_values: list[float | str] = []
    counts = Counter({"SE": 0, "ID": 0, "TS": 0, "TE": 0})
    with open_sim(resolved) as handle:
        for raw in handle:
            stripped = raw.strip()
            if not stripped:
                continue
            fields = stripped.split()
            token = fields[0]
            if token == "Geometry":
                geometry_values.append(
                    stripped.split(None, 1)[1].strip() if len(fields) >= 2 else ""
                )
            elif token == "Seed":
                value = fields[1] if len(fields) >= 2 else ""
                try:
                    seed_values.append(int(value))
                except ValueError:
                    seed_values.append(value)
            elif token in counts:
                counts[token] += 1
                if token == "TE":
                    value = fields[1] if len(fields) >= 2 else ""
                    try:
                        te_values.append(float(value))
                    except ValueError:
                        te_values.append(value)

    result = {
        "geometry_values": geometry_values,
        "geometry": geometry_values[0] if len(geometry_values) == 1 else None,
        "seed_values": seed_values,
        "seed": seed_values[0] if len(seed_values) == 1 else None,
        "SE": int(counts["SE"]),
        "ID": int(counts["ID"]),
        "TS": int(counts["TS"]),
        "TE": int(counts["TE"]),
        "TE_values_s": te_values,
        "TE_s": te_values[0] if len(te_values) == 1 else None,
    }
    _SIM_METADATA_MEMO[key] = result
    return result


def sim_geometry(path: Path) -> str | None:
    if not path.is_file():
        return None
    return sim_transport_metadata(path).get("geometry")


def exact_o8_geometry(value: str | None) -> bool:
    if not value:
        return False
    return resolve_path(value) == O8_GEOMETRY.resolve()


def retained_geometry_bundle_audit() -> dict[str, Any]:
    """Bind all five retained O8 geometry files to package-43 authority."""
    problems: list[str] = []
    authority = load_json(BASE_STEP05)
    try:
        expected = authority["preflight"]["gates"]["geometry"]["authority"][
            "o8_geometry_hashes"
        ]
    except (KeyError, TypeError) as exc:
        raise Step05GateError(
            "package-43 Step05 lacks the retained O8 geometry-bundle authority"
        ) from exc
    if not isinstance(expected, dict):
        raise Step05GateError("package-43 O8 geometry-bundle authority is not a map")

    expected_names = set(GEOMETRY_BUNDLE_NAMES)
    if set(expected) != expected_names:
        problems.append(
            f"authority names={sorted(expected)} expected={sorted(expected_names)}"
        )
    records: dict[str, Any] = {}
    for name in GEOMETRY_BUNDLE_NAMES:
        path = O8_GEOMETRY.parent / name
        exists = path.is_file()
        current_hash = sha256(path) if exists else None
        expected_hash = expected.get(name)
        if not exists:
            problems.append(f"geometry bundle file absent: {rel(path)}")
        elif current_hash != expected_hash:
            problems.append(
                f"geometry bundle {name} sha256={current_hash} expected={expected_hash}"
            )
        records[name] = {
            "path": rel(path),
            "size_bytes": path.stat().st_size if exists else None,
            "sha256": current_hash,
            "authority_sha256": expected_hash,
            "matches_authority": bool(exists and current_hash == expected_hash),
        }
    return {
        "status": (
            "PASS_RETAINED_PACKAGE43_O8_GEOMETRY_BUNDLE"
            if not problems
            else "FAIL_RETAINED_PACKAGE43_O8_GEOMETRY_BUNDLE"
        ),
        "authority": rel(BASE_STEP05),
        "authority_sha256": sha256(BASE_STEP05),
        "required_exact_file_set": list(GEOMETRY_BUNDLE_NAMES),
        "files": records,
        "problems": problems,
    }


def is_s3d_active_veto_volume(volume: str) -> bool:
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


def active_veto_predicate_sha256() -> str:
    return hashlib.sha256(
        inspect.getsource(is_s3d_active_veto_volume).encode("utf-8")
    ).hexdigest()


def authority_dependencies() -> dict[str, Any]:
    paths = {
        "adr_implementation": ADR_IMPLEMENTATION,
        "selection_implementation": STEP05_IMPLEMENTATION,
        "bridge_summary": BRIDGE_SUMMARY,
        "aeff_authority": AEFF_AUTHORITY,
        "science_ledger": SCIENCE_LEDGER,
        "boundary_summary": BOUNDARY_SUMMARY,
        "atm511_authority": ATM_SUMMARY,
    }
    missing = [rel(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise Step05GateError(f"missing Step05 dependency authorities: {missing}")
    return {
        name: {"path": rel(path), "sha256": sha256(path)}
        for name, path in paths.items()
    } | {
        "step05_harness": {
            "path": rel(Path(__file__)),
            "sha256": sha256(Path(__file__)),
        },
        "active_veto_predicate": {
            "callable": "is_s3d_active_veto_volume",
            "sha256": active_veto_predicate_sha256(),
        },
    }


def require_dependency_match(recorded: dict[str, Any], label: str) -> dict[str, Any]:
    current = authority_dependencies()
    if recorded != current:
        changed = sorted(
            key
            for key in set(recorded) | set(current)
            if recorded.get(key) != current.get(key)
        )
        raise Step05GateError(f"{label} dependency hashes are stale: {changed}")
    return current


def configure_step05() -> Any:
    module = load_module("s3d_o8_all8_step05_selection", STEP05_IMPLEMENTATION)
    module.ROOT = ROOT
    module.TOOLS = ROOT / "old/code/tools"
    module.OUT = STEP05_OUT
    module.SUMMARY_JSON = STEP05_JSON
    module.SUMMARY_MD = STEP05_OUT / "step05_s3d_o8_all8_activation_l1_response_summary.md"
    module.RATES_CSV = STEP05_RATES
    module.TIMELINE_CSV = STEP05_OUT / "step05_s3d_o8_all8_activation_timeline_not_run.csv"
    module.PROMPT_DIR = PROMPT_DIR
    module.PROMPT_NORM = PROMPT_NORM
    module.SCIENCE_SIM = SIGNAL_SIM
    module.STEP09_SUMMARY = BRIDGE_SUMMARY
    module.F10M_A1_AEFF = AEFF_AUTHORITY
    module.SCIENCE_RATE_LEDGER = SCIENCE_LEDGER
    module.BOUNDARY_CLOSURE_SUMMARY = BOUNDARY_SUMMARY
    module.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    module.ACTIVE_VETO_MATCH_DESCRIPTION = (
        "O8 BGO/CsI/ActiveShield/CEBR3 and retained active plastic volumes; "
        "W/Al/Kapton mechanical volumes excluded"
    )
    module.is_v3p5_active_veto_volume = is_s3d_active_veto_volume
    module._PROMPT_NORMALIZATION_AUDIT = None
    return module


def load_adr() -> Any:
    tools = str(ADR_IMPLEMENTATION.parent)
    if tools not in sys.path:
        sys.path.insert(0, tools)
    return load_module("s3d_o8_all8_adr", ADR_IMPLEMENTATION)


def configure_delayed_parser(adr: Any, components: list[dict[str, Any]]) -> None:
    mapping = {
        resolve_path(row["sim"]).as_posix(): {
            "family": str(row["family"]),
            "TE_s": float(row["TE_s"]),
        }
        for row in components
        if row["status"] == "PASS"
    }
    adr.is_active_veto_volume = is_s3d_active_veto_volume

    def event_rate_for_mode(path: str, mode: str, science_flux: float):
        del science_flux
        if mode != "delayed":
            raise ValueError(f"multi-family parser accepts delayed mode only, got {mode}")
        key = resolve_path(path).as_posix()
        if key not in mapping:
            raise ValueError(f"unregistered delayed SIM: {path}")
        item = mapping[key]
        return "delayed", item["family"], 1.0 / item["TE_s"]

    adr.event_rate_for_mode = event_rate_for_mode


def audit_json_evidence(
    evidence: dict[str, Any],
    label: str,
    problems: list[str],
    *,
    expected_status: str = "PASS",
) -> tuple[dict[str, Any], Path | None, str | None]:
    value = evidence.get("path")
    if not value:
        problems.append(f"{label}: evidence path is absent")
        return {}, None, None
    path = resolve_path(value)
    if not path.is_file():
        problems.append(f"{label}: evidence file is absent: {rel(path)}")
        return {}, path, None
    current_hash = sha256(path)
    if evidence.get("sha256") != current_hash:
        problems.append(
            f"{label}: current sha256={current_hash} recorded={evidence.get('sha256')}"
        )
    current = load_json(path)
    if evidence.get("status") != expected_status:
        problems.append(
            f"{label}: recorded status={evidence.get('status')} expected={expected_status}"
        )
    if current.get("status") != expected_status:
        problems.append(
            f"{label}: current status={current.get('status')} expected={expected_status}"
        )
    if current.get("problems"):
        problems.append(f"{label}: current problems={current.get('problems')}")
    return current, path, current_hash


def audit_artifact_record(
    record: dict[str, Any] | None,
    label: str,
    problems: list[str],
    *,
    required: bool,
) -> dict[str, Any]:
    """Recompute one campaign artifact record and bind it to current bytes."""
    recorded = record if isinstance(record, dict) else {}
    value = recorded.get("path")
    if not value:
        if required:
            problems.append(f"{label}: artifact path is absent")
        return {"path": None, "size_bytes": None, "sha256": None}

    path = resolve_path(value)
    exists = path.is_file()
    current_size = path.stat().st_size if exists else None
    current_hash = sha256(path) if exists else None
    if required and not exists:
        problems.append(f"{label}: required artifact is absent: {rel(path)}")
    if recorded.get("size_bytes") != current_size:
        problems.append(
            f"{label}: current size_bytes={current_size} "
            f"recorded={recorded.get('size_bytes')}"
        )
    if recorded.get("sha256") != current_hash:
        problems.append(
            f"{label}: current sha256={current_hash} recorded={recorded.get('sha256')}"
        )
    if required and current_hash is None:
        problems.append(f"{label}: required artifact has no current sha256")
    return {
        "path": rel(path),
        "size_bytes": current_size,
        "sha256": current_hash,
    }


def exact_normalization_guard(
    family: str,
    rows: list[dict[str, Any]],
    expected_files: int,
    problems: list[str],
) -> None:
    if len(rows) != 1 or rows[0].get("tag") != family:
        problems.append(f"{family}: fixed normalization rows={rows}")
        return
    row = rows[0]
    expected = {
        "files": expected_files,
        "division": float(expected_files),
        "tt_count": expected_files,
        "tt_files": expected_files,
        "tt_line_count": expected_files,
    }
    for key, value in expected.items():
        actual = row.get(key)
        try:
            matches = float(actual) == float(value)
        except (TypeError, ValueError):
            matches = False
        if not matches:
            problems.append(f"{family}: fixed normalization {key}={actual} expected={value}")


def component_campaign_audit(write: bool = True) -> dict[str, Any]:
    if not CAMPAIGN.is_file():
        return {
            "status": "PENDING_S3D_O8_ALL8_ACTIVATION_CAMPAIGN",
            "generated_at_utc": now_utc(),
            "campaign": rel(CAMPAIGN),
            "problems": ["campaign manifest is absent"],
        }
    campaign, campaign_hash = json_bytes(CAMPAIGN)
    if campaign.get("status") != CAMPAIGN_PASS:
        return {
            "status": "PENDING_S3D_O8_ALL8_ACTIVATION_CAMPAIGN",
            "generated_at_utc": now_utc(),
            "campaign": rel(CAMPAIGN),
            "campaign_sha256": campaign_hash,
            "campaign_status": campaign.get("status"),
            "problems": [
                f"campaign status={campaign.get('status')}; required={CAMPAIGN_PASS}"
            ],
        }

    problems: list[str] = []
    geometry_bundle = retained_geometry_bundle_audit()
    problems.extend(geometry_bundle["problems"])
    dependencies = authority_dependencies()
    if not exact_o8_geometry(campaign.get("geometry_setup")):
        problems.append(f"campaign geometry={campaign.get('geometry_setup')}")
    buildup = campaign.get("all8_buildup") or {}
    if buildup.get("status") != "PASS":
        problems.append(f"all8_buildup status={buildup.get('status')}")
    if int(buildup.get("jobs") or -1) != sum(EXPECTED_COUNTS.values()):
        problems.append(f"all8_buildup jobs={buildup.get('jobs')} expected=68")
    if buildup.get("particle_counts") != EXPECTED_COUNTS:
        problems.append(
            f"all8_buildup particle_counts={buildup.get('particle_counts')} expected={EXPECTED_COUNTS}"
        )

    source_validation_evidence = campaign.get("family_source_validation") or {}
    source_validation_path_value = source_validation_evidence.get("path")
    source_validation_path = (
        resolve_path(source_validation_path_value)
        if source_validation_path_value
        else Path("/")
    )
    source_validation_hash = (
        sha256(source_validation_path) if source_validation_path.is_file() else None
    )
    if not source_validation_path.is_file():
        problems.append("family source-validation authority is absent")
    elif source_validation_evidence.get("sha256") != source_validation_hash:
        problems.append("family source-validation current hash differs from campaign")
    if source_validation_evidence.get("family_set_complete") is not True:
        problems.append("campaign family source-validation set is incomplete")

    rows = campaign.get("families") or []
    names = [str(row.get("family")) for row in rows]
    if len(rows) != len(FAMILIES) or set(names) != FAMILY_SET or len(set(names)) != len(names):
        problems.append(f"family set/order source={names}; required exact set={list(FAMILIES)}")
    by_family = {str(row.get("family")): row for row in rows}
    components: list[dict[str, Any]] = []
    positive_paths: set[str] = set()

    for family in FAMILIES:
        row = by_family.get(family)
        if row is None:
            continue
        status = str(row.get("status"))
        production = row.get("production") or {}
        evidence = row.get("audit_evidence") or {}
        activity = float(row.get("activity_Bq") or 0.0)
        expected_files = EXPECTED_COUNTS[family]
        for key, expected in (
            ("files", expected_files),
            ("division", float(expected_files)),
            ("tt_lines", expected_files),
        ):
            actual = production.get(key)
            try:
                matches = float(actual) == float(expected)
            except (TypeError, ValueError):
                matches = False
            if not matches:
                problems.append(f"{family}: production {key}={actual} expected={expected}")
        if evidence.get("problems"):
            problems.append(f"{family}: campaign audit_evidence problems={evidence.get('problems')}")
        if evidence.get("family_source_validation_status") != status:
            problems.append(
                f"{family}: source-validation={evidence.get('family_source_validation_status')} expected={status}"
            )
        volume_current, volume_path, volume_hash = audit_json_evidence(
            evidence.get("volume_map") or {}, f"{family} volume-map", problems
        )

        fixed_current: dict[str, Any] = {}
        fixed_path: Path | None = None
        fixed_hash: str | None = None
        activity_current: dict[str, Any] = {}
        activity_path: Path | None = None
        activity_hash: str | None = None
        if status in {"PASS", "PASS_ZERO_ACTIVITY"}:
            fixed_current, fixed_path, fixed_hash = audit_json_evidence(
                evidence.get("fixed_normalization") or {},
                f"{family} fixed normalization",
                problems,
            )
            recorded_rows = (evidence.get("fixed_normalization") or {}).get("rows") or []
            current_rows = fixed_current.get("rows") or []
            if recorded_rows != current_rows:
                problems.append(f"{family}: fixed-normalization rows changed after campaign")
            exact_normalization_guard(family, current_rows, expected_files, problems)
            activity_current, activity_path, activity_hash = audit_json_evidence(
                evidence.get("activity_completeness") or {},
                f"{family} activity completeness",
                problems,
            )
            if activity_current.get("missing_nubase"):
                problems.append(f"{family}: activity completeness has missing NUBASE keys")
            if activity_current.get("key_mismatches"):
                problems.append(f"{family}: activity completeness has key mismatches")

        fixed_summary_value = row.get("fixed_summary")
        fixed_summary = resolve_path(fixed_summary_value) if fixed_summary_value else Path("/")
        fixed_summary_hash = sha256(fixed_summary) if fixed_summary.is_file() else None
        fixed_summary_current = load_json(fixed_summary) if fixed_summary.is_file() else {}
        if row.get("fixed_summary_sha256") != fixed_summary_hash:
            problems.append(
                f"{family}: fixed-summary current sha256={fixed_summary_hash} "
                f"recorded={row.get('fixed_summary_sha256')}"
            )
        if status in {"PASS", "PASS_ZERO_ACTIVITY"}:
            if not fixed_summary.is_file():
                problems.append(f"{family}: fixed summary is absent")
            summary_activity = float(fixed_summary_current.get("new_total_activity_Bq") or 0.0)
            if not math.isclose(summary_activity, activity, rel_tol=1.0e-12, abs_tol=1.0e-12):
                problems.append(
                    f"{family}: campaign activity={activity} fixed-summary activity={summary_activity}"
                )

        top_level_artifacts = {
            name: audit_artifact_record(
                row.get(name),
                f"{family} top-level {name}",
                problems,
                required=status in {"PASS", "PASS_ZERO_ACTIVITY"},
            )
            for name in ("fixed_source", "groundstate_corrections", "inventory")
        }

        base = {
            "family": family,
            "status": status,
            "activity_Bq": activity,
            "production": production,
            "fixed_summary": rel(fixed_summary) if fixed_summary_value else None,
            "fixed_summary_sha256": fixed_summary_hash,
            "fixed_source": top_level_artifacts["fixed_source"],
            "groundstate_corrections": top_level_artifacts[
                "groundstate_corrections"
            ],
            "inventory": top_level_artifacts["inventory"],
            "audit_evidence": {
                "family_source_validation_status": evidence.get(
                    "family_source_validation_status"
                ),
                "volume_map": {
                    "path": rel(volume_path) if volume_path else None,
                    "sha256": volume_hash,
                    "status": volume_current.get("status"),
                },
                "fixed_normalization": {
                    "path": rel(fixed_path) if fixed_path else None,
                    "sha256": fixed_hash,
                    "status": fixed_current.get("status"),
                    "rows": fixed_current.get("rows"),
                },
                "activity_completeness": {
                    "path": rel(activity_path) if activity_path else None,
                    "sha256": activity_hash,
                    "status": activity_current.get("status"),
                    "expected_activity_keys": activity_current.get(
                        "expected_activity_keys"
                    ),
                    "fixed_source_activity_keys": activity_current.get(
                        "fixed_source_activity_keys"
                    ),
                },
            },
        }
        if status in ZERO_STATUSES:
            if status == "PASS_ZERO_PRODUCTION" and not production.get("zero_production"):
                problems.append(f"{family}: zero-production status lacks zero_production=true")
            if status == "PASS_ZERO_ACTIVITY" and production.get("zero_production"):
                problems.append(f"{family}: zero-activity status conflicts with zero production")
            if activity != 0.0:
                problems.append(f"{family}: zero status has activity={activity}")
            components.append(
                {
                    **base,
                    "sim": None,
                    "SE": 0,
                    "ID": 0,
                    "TE_s": None,
                    "event_weight_hz": None,
                    "exact_manifest": None,
                    "zero_observation_label": "ZERO_OBSERVED_PRODUCTION_IN_FINITE_BUILDUP_CAMPAIGN",
                    "normalization_contract": (
                        "no delayed transport exposure is assigned; this is a finite-campaign "
                        "zero observation, not a physical or structural zero"
                    ),
                }
            )
            continue
        if status != "PASS":
            problems.append(f"{family}: unsupported family status={status}")
            components.append(base)
            continue

        transport = row.get("transport") or {}
        sim_value = transport.get("path")
        sim = resolve_path(sim_value) if sim_value else Path("/")
        se = int(transport.get("SE") or -1)
        ident = int(transport.get("ID") or -1)
        te = float(transport.get("TE_s") or 0.0)
        if activity <= 0.0 or not math.isfinite(activity):
            problems.append(f"{family}: PASS activity={activity}")
        if se != DELAYED_GENERATED_PER_POSITIVE_FAMILY or ident != se:
            problems.append(f"{family}: SE/ID={se}/{ident} expected=1000000/1000000")
        if te <= 0.0 or not math.isfinite(te):
            problems.append(f"{family}: invalid TE_s={te}")
        if transport.get("status") != "PASS":
            problems.append(
                f"{family}: delayed transport status={transport.get('status')} expected=PASS"
            )
        if not sim.is_file():
            problems.append(f"{family}: delayed SIM absent: {rel(sim)}")
        sim_metadata = sim_transport_metadata(sim) if sim.is_file() else {}
        header_geometry = sim_metadata.get("geometry")
        if not exact_o8_geometry(header_geometry):
            problems.append(f"{family}: SIM header geometry={header_geometry}")
        if sim_metadata.get("geometry_values") != [header_geometry]:
            problems.append(
                f"{family}: SIM Geometry line values={sim_metadata.get('geometry_values')}"
            )
        if sim_metadata.get("seed_values") != [260_613]:
            problems.append(
                f"{family}: SIM Seed line values={sim_metadata.get('seed_values')} expected=[260613]"
            )
        for key, expected in (
            ("SE", DELAYED_GENERATED_PER_POSITIVE_FAMILY),
            ("ID", DELAYED_GENERATED_PER_POSITIVE_FAMILY),
            ("TS", 1),
            ("TE", 1),
        ):
            if int(sim_metadata.get(key) or 0) != expected:
                problems.append(
                    f"{family}: SIM {key} count={sim_metadata.get(key)} expected={expected}"
                )
        actual_te = sim_metadata.get("TE_s")
        if not isinstance(actual_te, (int, float)) or not math.isclose(
            float(actual_te), te, rel_tol=1.0e-12, abs_tol=1.0e-12
        ):
            problems.append(f"{family}: SIM TE_s={actual_te} manifest TE_s={te}")
        if not exact_o8_geometry(transport.get("geometry")):
            problems.append(f"{family}: transport geometry={transport.get('geometry')}")
        sim_key = sim.as_posix()
        if sim_key in positive_paths:
            problems.append(f"{family}: delayed SIM is reused by another family: {rel(sim)}")
        positive_paths.add(sim_key)

        closure_rel = (
            abs(te * activity - se) / se
            if se > 0 and te > 0.0 and activity > 0.0
            else math.inf
        )
        exact_value = row.get("exact_manifest")
        exact_manifest = resolve_path(exact_value) if exact_value else Path("/")
        if not exact_manifest.is_file():
            problems.append(f"{family}: exact manifest absent: {rel(exact_manifest)}")
        elif "step02_delay_exactpos_s3d_o8_all8_activation_m50000_20260713" not in exact_manifest.as_posix():
            problems.append(f"{family}: exact manifest is outside package44 campaign roots")
        exact_hash = sha256(exact_manifest) if exact_manifest.is_file() else None
        if evidence.get("exact_manifest_sha256") != exact_hash:
            problems.append(f"{family}: exact manifest current hash differs from campaign")
        exact_current = load_json(exact_manifest) if exact_manifest.is_file() else {}
        exact_status = str(exact_current.get("status") or "")
        if not exact_status.startswith("PASS_"):
            problems.append(f"{family}: exact manifest status={exact_status}")
        if exact_current.get("problems"):
            problems.append(
                f"{family}: exact manifest problems={exact_current.get('problems')}"
            )
        expected_division = {family: float(expected_files)}
        if exact_current.get("incident_family") != family:
            problems.append(
                f"{family}: exact incident_family={exact_current.get('incident_family')}"
            )
        if exact_current.get("family_resolved_contract") is not True:
            problems.append(f"{family}: exact family-resolved contract is absent")
        if exact_current.get("division_by_tag") != expected_division:
            problems.append(
                f"{family}: exact division_by_tag={exact_current.get('division_by_tag')} expected={expected_division}"
            )
        if int(exact_current.get("n_pointsource_blocks") or -1) != 50_000:
            problems.append(f"{family}: exact M={exact_current.get('n_pointsource_blocks')}")
        if int(exact_current.get("seed") or -1) != 260_613:
            problems.append(f"{family}: exact seed={exact_current.get('seed')}")
        sampling = exact_current.get("sampling_audit") or {}
        if sampling.get("status") != "PASS" or sampling.get("problems"):
            problems.append(f"{family}: exact sampling={sampling}")
        manifest_source_provenance = exact_current.get("source_provenance") or {}
        campaign_source_provenance = row.get("source_provenance") or {}
        if campaign_source_provenance != manifest_source_provenance:
            problems.append(
                f"{family}: campaign source_provenance differs from current exact manifest"
            )
        required_source_artifacts = (
            "raw_source",
            "inventory",
            "fixed_source",
            "fixed_summary",
            "groundstate_corrections",
            "fixed_normalization",
            "volume_map_audit",
            "activity_completeness_audit",
            "exact_source",
            "weighted_table",
            "nubase",
            "geometry_setup",
            "geometry_source",
        )
        current_source_provenance = {
            name: audit_artifact_record(
                manifest_source_provenance.get(name),
                f"{family} exact source_provenance {name}",
                problems,
                required=True,
            )
            for name in required_source_artifacts
        }
        for top_name in ("inventory", "fixed_source", "groundstate_corrections"):
            if top_level_artifacts[top_name] != current_source_provenance[top_name]:
                problems.append(
                    f"{family}: top-level {top_name} differs from exact source provenance"
                )
        fixed_summary_artifact = current_source_provenance["fixed_summary"]
        if fixed_summary_artifact.get("path") != (
            rel(fixed_summary) if fixed_summary_value else None
        ) or fixed_summary_artifact.get("sha256") != fixed_summary_hash:
            problems.append(
                f"{family}: fixed summary differs from exact source provenance"
            )
        evidence_provenance_links = {
            "fixed_normalization": (fixed_path, fixed_hash),
            "volume_map_audit": (volume_path, volume_hash),
            "activity_completeness_audit": (activity_path, activity_hash),
        }
        for name, (authority_path, authority_hash) in evidence_provenance_links.items():
            current_record = current_source_provenance[name]
            if current_record.get("path") != (
                rel(authority_path) if authority_path else None
            ) or current_record.get("sha256") != authority_hash:
                problems.append(
                    f"{family}: {name} differs between audit evidence and source provenance"
                )
        geometry_record = current_source_provenance["geometry_setup"]
        if geometry_record.get("path") != rel(O8_GEOMETRY):
            problems.append(
                f"{family}: source provenance geometry_setup={geometry_record.get('path')}"
            )
        exact_transport = exact_current.get("delayed_transport") or {}
        if exact_transport.get("status") != "PASS":
            problems.append(
                f"{family}: exact delayed transport status={exact_transport.get('status')} expected=PASS"
            )
        for key in (
            "status",
            "path",
            "SE",
            "ID",
            "TE_s",
            "geometry",
            "size_bytes",
            "sha256",
            "seed",
            "source_sha256",
        ):
            if exact_transport.get(key) != transport.get(key):
                problems.append(
                    f"{family}: exact/campaign transport {key} mismatch: "
                    f"{exact_transport.get(key)} != {transport.get(key)}"
                )

        sim_hash = sha256(sim) if sim.is_file() else None
        sim_size = sim.stat().st_size if sim.is_file() else None
        if transport.get("size_bytes") != sim_size:
            problems.append(
                f"{family}: delayed SIM current size_bytes={sim_size} "
                f"recorded={transport.get('size_bytes')}"
            )
        if transport.get("sha256") != sim_hash:
            problems.append(
                f"{family}: delayed SIM current sha256={sim_hash} "
                f"recorded={transport.get('sha256')}"
            )
        if int(transport.get("seed") or -1) != 260_613:
            problems.append(f"{family}: delayed transport seed={transport.get('seed')}")
        exact_source_hash = current_source_provenance["exact_source"].get("sha256")
        if transport.get("source_sha256") != exact_source_hash:
            problems.append(
                f"{family}: delayed transport source_sha256={transport.get('source_sha256')} "
                f"exact-source sha256={exact_source_hash}"
            )

        components.append(
            {
                **base,
                "sim": rel(sim),
                "sim_size_bytes": sim_size,
                "sim_sha256": sim_hash,
                "SE": se,
                "ID": ident,
                "TE_s": te,
                "event_weight_hz": 1.0 / te if te > 0.0 else None,
                "geometry_header": header_geometry,
                "exact_manifest": rel(exact_manifest),
                "exact_manifest_sha256": exact_hash,
                "source_provenance": current_source_provenance,
                "transport_provenance": {
                    "status": transport.get("status"),
                    "size_bytes": sim_size,
                    "sha256": sim_hash,
                    "seed": transport.get("seed"),
                    "source_sha256": exact_source_hash,
                    "sim_header_and_terminator": sim_metadata,
                },
                "TE_times_activity": te * activity,
                "TE_activity_relative_delta_to_SE": closure_rel,
                "TE_activity_diagnostic": (
                    "WITHIN_COARSE_10_PERCENT_DIAGNOSTIC"
                    if closure_rel <= TE_ACTIVITY_REL_TOL
                    else "OUTSIDE_COARSE_10_PERCENT_DIAGNOSTIC_NONBLOCKING"
                ),
                "normalization_contract": "each retained detector event carries 1/TE_s for its incident family",
            }
        )

    payload = {
        "status": COMPONENT_PASS if not problems else "FAIL_S3D_O8_ALL8_STEP05_COMPONENTS",
        "campaign_generated_at_utc": campaign.get("generated_at_utc"),
        "document_type": "s3d_o8_all8_family_delayed_step05_component_authority",
        "script": rel(Path(__file__)),
        "script_sha256": sha256(Path(__file__)),
        "campaign": rel(CAMPAIGN),
        "campaign_sha256": campaign_hash,
        "campaign_status": campaign.get("status"),
        "geometry_setup": rel(O8_GEOMETRY),
        "geometry_bundle": geometry_bundle,
        "family_order": list(FAMILIES),
        "family_set_contract": "exactly alpha, eminus, eplus, gamma, muminus, muplus, n, p",
        "family_source_validation": {
            "path": rel(source_validation_path) if source_validation_path_value else None,
            "sha256": source_validation_hash,
            "family_set_complete": source_validation_evidence.get(
                "family_set_complete"
            ),
        },
        "dependency_hashes": dependencies,
        "components": components,
        "positive_families": [row["family"] for row in components if row.get("status") == "PASS"],
        "audited_zero_families": [row["family"] for row in components if row.get("status") in ZERO_STATUSES],
        "normalization": {
            "positive_family_event_weight": "1 / that family's delayed SIM TE_s",
            "TE_activity_relative_tolerance": TE_ACTIVITY_REL_TOL,
            "TE_activity_check_scope": (
                "nonblocking diagnostic only because daughter-chain source timing need not "
                "satisfy SE/activity; recorded SIM TE is the event-weight authority"
            ),
            "zero_family_rule": (
                "finite buildup campaign observed no production/activity; assign no fictitious "
                "transport exposure, but do not claim a physical zero"
            ),
        },
        "lineage_key": ["stream", "tag_as_incident_family", "source_file", "local_id"],
        "problems": problems,
        "claim_boundary": (
            "This is a day-15 component authority only. Garwood intervals downstream cover "
            "transport counting for transported families only; they do not cover buildup yield, "
            "exact-position M sampling, or upper limits for zero-observed families. Paper claims "
            "remain blocked on Step05, the 420 eV response ensemble, and the family-by-nuclide fold."
        ),
    }
    payload["authority_fingerprint"] = canonical_sha256(payload)
    if write and payload["status"] == COMPONENT_PASS:
        write_json_if_changed(COMPONENTS_JSON, payload)
    return payload


def require_current_components() -> dict[str, Any]:
    if not COMPONENTS_JSON.is_file():
        raise Step05GateError("materialize the stable component manifest with the components stage")
    stored = load_json(COMPONENTS_JSON)
    if stored.get("status") != COMPONENT_PASS:
        raise Step05GateError(f"component status={stored.get('status')}")
    if stored.get("script_sha256") != sha256(Path(__file__)):
        raise Step05GateError("component manifest script hash is stale")
    _campaign, current_campaign_hash = json_bytes(CAMPAIGN)
    if stored.get("campaign_sha256") != current_campaign_hash:
        raise Step05GateError("component manifest campaign hash is stale")
    require_dependency_match(stored.get("dependency_hashes") or {}, "component manifest")
    current = component_campaign_audit(write=False)
    if current.get("status") != COMPONENT_PASS:
        raise Step05GateError(
            "current campaign component audit failed: " + "; ".join(current.get("problems") or [])
        )
    if stored.get("authority_fingerprint") != current.get("authority_fingerprint"):
        raise Step05GateError("component authority fingerprint is stale")
    return stored


def catalog_structure_audit(cat: dict[str, Any], label: str) -> dict[str, Any]:
    """Require compact cumulative pixels and equal lengths across the full schema."""
    required = (*EVENT_FIELDS, "pix_start", *PIXEL_FIELDS)
    missing = [field for field in required if field not in cat]
    if missing:
        raise Step05GateError(f"{label}: catalog fields absent={missing}")

    event_count = len(cat["stream"])
    event_lengths = {
        field: len(cat[field]) for field in (*EVENT_FIELDS, "pix_start")
    }
    bad_event_lengths = {
        field: length
        for field, length in event_lengths.items()
        if length != event_count
    }
    if bad_event_lengths:
        raise Step05GateError(
            f"{label}: event-field lengths={bad_event_lengths} expected={event_count}"
        )

    pixel_count = len(cat["pix_e"])
    pixel_lengths = {field: len(cat[field]) for field in PIXEL_FIELDS}
    bad_pixel_lengths = {
        field: length
        for field, length in pixel_lengths.items()
        if length != pixel_count
    }
    if bad_pixel_lengths:
        raise Step05GateError(
            f"{label}: pixel-field lengths={bad_pixel_lengths} expected={pixel_count}"
        )

    counts_raw = np.asarray(cat["pix_count"])
    counts = counts_raw.astype(np.int64, copy=False)
    if not np.array_equal(counts_raw, counts):
        raise Step05GateError(f"{label}: pix_count contains non-integer values")
    if np.any(counts < 0):
        raise Step05GateError(f"{label}: pix_count contains negative values")
    starts = np.asarray(cat["pix_start"], dtype=np.int64)
    expected_starts = np.zeros(event_count, dtype=np.int64)
    if event_count > 1:
        expected_starts[1:] = np.cumsum(counts[:-1], dtype=np.int64)
    if not np.array_equal(starts, expected_starts):
        raise Step05GateError(
            f"{label}: pix_start is not the cumulative sum of prior pix_count"
        )
    if int(np.sum(counts, dtype=np.int64)) != pixel_count:
        raise Step05GateError(
            f"{label}: sum(pix_count)={int(np.sum(counts))} pixels={pixel_count}"
        )
    if int(cat.get("n_kept_events", -1)) != event_count:
        raise Step05GateError(
            f"{label}: n_kept_events={cat.get('n_kept_events')} rows={event_count}"
        )
    return {
        "status": "PASS_COMPACT_CUMULATIVE_CATALOG_SCHEMA",
        "label": label,
        "event_fields": event_lengths,
        "pixel_fields": pixel_lengths,
        "events": event_count,
        "pixels": pixel_count,
        "sum_pix_count": int(np.sum(counts, dtype=np.int64)),
        "n_kept_events": int(cat["n_kept_events"]),
    }


def stream_blocks(cat: dict[str, Any]) -> tuple[int, int]:
    stream = np.asarray(cat["stream"], dtype=object)
    changes = np.flatnonzero(stream[1:] != stream[:-1]) + 1
    if len(changes) != 2:
        raise Step05GateError(f"retained catalog stream blocks are not prompt/delayed/science: {changes}")
    prompt_end, science_start = (int(changes[0]), int(changes[1]))
    observed = [str(stream[0]), str(stream[prompt_end]), str(stream[science_start])]
    if observed != ["prompt", "delayed", "science"]:
        raise Step05GateError(f"retained catalog stream order={observed}")
    return prompt_end, science_start


def splice_retained_catalog(base: dict[str, Any], delayed: dict[str, Any]) -> dict[str, Any]:
    prompt_end, science_start = stream_blocks(base)
    base_pix_start = np.asarray(base["pix_start"], dtype=np.int64)
    prompt_pix_end = int(base_pix_start[prompt_end])
    science_pix_start = int(base_pix_start[science_start])
    new_pixel_count = len(delayed["pix_e"])
    out: dict[str, Any] = {}
    for field in EVENT_FIELDS:
        out[field] = np.concatenate(
            [
                np.asarray(base[field])[:prompt_end],
                np.asarray(delayed[field]),
                np.asarray(base[field])[science_start:],
            ]
        )
    out["pix_start"] = np.concatenate(
        [
            base_pix_start[:prompt_end],
            np.asarray(delayed["pix_start"], dtype=np.int64) + prompt_pix_end,
            base_pix_start[science_start:]
            - science_pix_start
            + prompt_pix_end
            + new_pixel_count,
        ]
    ).astype(np.int64, copy=False)
    for field in PIXEL_FIELDS:
        out[field] = np.concatenate(
            [
                np.asarray(base[field])[:prompt_pix_end],
                np.asarray(delayed[field]),
                np.asarray(base[field])[science_pix_start:],
            ]
        )
    out["n_generated_events_seen"] = (
        PROMPT_GENERATED + SIGNAL_GENERATED + int(delayed.get("n_generated_events_seen", 0))
    )
    out["n_kept_events"] = int(len(out["stream"]))
    return out


def retained_block_identity(base: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    base_prompt_end, base_science_start = stream_blocks(base)
    out_prompt_end, out_science_start = stream_blocks(out)
    checks: dict[str, bool] = {}
    for field in EVENT_FIELDS:
        checks[f"prompt_{field}"] = np.array_equal(
            np.asarray(base[field])[:base_prompt_end], np.asarray(out[field])[:out_prompt_end]
        )
        checks[f"science_{field}"] = np.array_equal(
            np.asarray(base[field])[base_science_start:], np.asarray(out[field])[out_science_start:]
        )
    base_prompt_pix = int(np.asarray(base["pix_start"])[base_prompt_end])
    base_science_pix = int(np.asarray(base["pix_start"])[base_science_start])
    out_prompt_pix = int(np.asarray(out["pix_start"])[out_prompt_end])
    out_science_pix = int(np.asarray(out["pix_start"])[out_science_start])
    for field in PIXEL_FIELDS:
        checks[f"prompt_{field}"] = np.array_equal(
            np.asarray(base[field])[:base_prompt_pix], np.asarray(out[field])[:out_prompt_pix]
        )
        checks[f"science_{field}"] = np.array_equal(
            np.asarray(base[field])[base_science_pix:], np.asarray(out[field])[out_science_pix:]
        )
    if not all(checks.values()):
        failed = [name for name, ok in checks.items() if not ok]
        raise Step05GateError(f"retained prompt/science splice identity failed: {failed}")
    return {
        "status": "PASS_RETAINED_PROMPT_SCIENCE_ARRAY_IDENTITY",
        "prompt_events": out_prompt_end,
        "science_events": len(out["stream"]) - out_science_start,
        "prompt_pixels": out_prompt_pix,
        "science_pixels": len(out["pix_e"]) - out_science_pix,
        "checks": len(checks),
    }


def lineage_audit(cat: dict[str, Any], components: list[dict[str, Any]]) -> dict[str, Any]:
    stream = np.asarray(cat["stream"], dtype=object)
    tags = np.asarray(cat["tag"], dtype=object)
    source = np.asarray(cat["source_file"], dtype=object)
    local_id = np.asarray(cat["local_id"], dtype=np.int64)
    rates = np.asarray(cat["rate_hz"], dtype=np.float64)
    problems: list[str] = []
    rows: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, int]] = set()
    for component in components:
        family = component["family"]
        mask = (stream == "delayed") & (tags == family)
        count = int(np.count_nonzero(mask))
        if component["status"] in ZERO_STATUSES:
            if count:
                problems.append(f"{family}: zero-observed campaign family has {count} catalog events")
            rows.append({"family": family, "status": component["status"], "kept_events": 0})
            continue
        expected_source = resolve_path(component["sim"]).as_posix()
        observed_sources = sorted({resolve_path(value).as_posix() for value in source[mask]})
        if count and observed_sources != [expected_source]:
            problems.append(f"{family}: source lineage={observed_sources} expected={[expected_source]}")
        ids = local_id[mask]
        if len(ids) != len(np.unique(ids)):
            problems.append(f"{family}: duplicate local_id values")
        if len(ids) and (int(np.min(ids)) < 1 or int(np.max(ids)) > int(component["ID"])):
            problems.append(f"{family}: local_id range={int(np.min(ids))}..{int(np.max(ids))}")
        expected_weight = float(component["event_weight_hz"])
        if count and not np.allclose(rates[mask], expected_weight, rtol=0.0, atol=1.0e-18):
            problems.append(f"{family}: event weights differ from 1/TE")
        for value in ids:
            key = (family, int(value))
            if key in seen_keys:
                problems.append(f"duplicate lineage key={key}")
                break
            seen_keys.add(key)
        rows.append(
            {
                "family": family,
                "status": "PASS",
                "kept_events": count,
                "local_id_min": int(np.min(ids)) if len(ids) else None,
                "local_id_max": int(np.max(ids)) if len(ids) else None,
                "source_file": rel(expected_source),
                "event_weight_hz": expected_weight,
            }
        )
    delayed_tags = set(str(value) for value in tags[stream == "delayed"])
    unknown = sorted(delayed_tags - FAMILY_SET)
    if unknown:
        problems.append(f"delayed catalog has unknown incident-family tags={unknown}")
    return {
        "status": "PASS_FAMILY_LOCAL_ID_LINEAGE" if not problems else "FAIL_FAMILY_LOCAL_ID_LINEAGE",
        "lineage_key": ["tag_as_incident_family", "local_id"],
        "strong_lineage_key": ["tag_as_incident_family", "source_file", "local_id"],
        "families": rows,
        "problems": problems,
    }


def cache_dependency_subset() -> dict[str, Any]:
    full = authority_dependencies()
    return {
        key: full[key]
        for key in (
            "adr_implementation",
            "step05_harness",
            "active_veto_predicate",
        )
    }


def component_cache_spec(
    adr: Any,
    component: dict[str, Any],
    cache_root: Path,
    *,
    rebuild: bool,
    require_existing_raw_parse: bool,
) -> dict[str, Any]:
    family = str(component["family"])
    sim = resolve_path(component["sim"])
    if not sim.is_file():
        raise Step05GateError(f"{family}: cache input SIM is absent: {rel(sim)}")
    size = sim.stat().st_size
    current_sim_hash = sha256(sim)
    recorded_hash = component.get("sim_sha256")
    if recorded_hash and recorded_hash != current_sim_hash:
        raise Step05GateError(f"{family}: SIM hash differs from component authority")
    recorded_size = component.get("sim_size_bytes")
    if recorded_size is not None and int(recorded_size) != int(size):
        raise Step05GateError(f"{family}: SIM size differs from component authority")
    dependencies = cache_dependency_subset()
    fingerprint_payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "family": family,
        "sim": rel(sim),
        "sim_size_bytes": size,
        "sim_sha256": current_sim_hash,
        "SE": int(component["SE"]),
        "ID": int(component["ID"]),
        "TE_s": float(component["TE_s"]),
        "event_weight_hz": float(component["event_weight_hz"]),
        "dependencies": dependencies,
    }
    fingerprint = canonical_sha256(fingerprint_payload)
    family_root = cache_root / family
    cache_dir = family_root / fingerprint
    cache_path = cache_dir / adr.cache_name_for_path(str(sim), "delayed")
    meta_path = family_root / "current_cache.json"
    metadata = load_json(meta_path) if meta_path.is_file() else {}
    stale_reasons: list[str] = []
    cache_hit = False
    if metadata:
        if metadata.get("fingerprint") != fingerprint:
            stale_reasons.append("fingerprint")
        if metadata.get("cache") != rel(cache_path):
            stale_reasons.append("cache_path")
        if not cache_path.is_file():
            stale_reasons.append("cache_missing")
        elif metadata.get("cache_sha256") != sha256(cache_path):
            stale_reasons.append("cache_sha256")
        if metadata.get("raw_sim_parse_completed") is not True:
            stale_reasons.append("raw_sim_parse_provenance")
        cache_hit = not stale_reasons
    elif require_existing_raw_parse and not rebuild:
        raise Step05GateError(
            f"{family}: raw-SIM regression cache is absent; rerun regression --rebuild-cache"
        )
    if stale_reasons and not rebuild:
        raise Step05GateError(
            f"{family}: stale delayed cache {stale_reasons}; rerun with --rebuild-cache"
        )
    return {
        "component": component,
        "family": family,
        "sim": sim,
        "cache_dir": cache_dir,
        "cache": cache_path,
        "meta": meta_path,
        "fingerprint": fingerprint,
        "fingerprint_payload": fingerprint_payload,
        "dependencies": dependencies,
        "parse_required": bool(rebuild or not cache_hit),
        "previous_metadata": metadata,
    }


def validate_parsed_component(
    parsed: dict[str, Any], component: dict[str, Any]
) -> dict[str, Any]:
    family = str(component["family"])
    generated = int(parsed.get("n_generated_events_seen", -1))
    if generated != int(component["SE"]):
        raise Step05GateError(
            f"{family}: parsed generated_events_seen={generated} expected SE={component['SE']}"
        )
    if int(parsed.get("n_kept_events", len(parsed["stream"]))) != len(parsed["stream"]):
        raise Step05GateError(f"{family}: parsed kept-event scalar does not close")
    if set(str(value) for value in parsed["stream"]) - {"delayed"}:
        raise Step05GateError(f"{family}: parsed cache contains non-delayed streams")
    if set(str(value) for value in parsed["tag"]) - {family}:
        raise Step05GateError(f"{family}: parsed cache contains wrong incident-family tags")
    expected_source = resolve_path(component["sim"]).as_posix()
    observed_sources = {
        resolve_path(value).as_posix() for value in parsed["source_file"]
    }
    if observed_sources and observed_sources != {expected_source}:
        raise Step05GateError(
            f"{family}: parsed source lineage={sorted(observed_sources)} expected={expected_source}"
        )
    expected_weight = float(component["event_weight_hz"])
    if parsed["rate_hz"] and not np.allclose(
        parsed["rate_hz"], expected_weight, rtol=0.0, atol=1.0e-18
    ):
        raise Step05GateError(f"{family}: parsed event weights differ from 1/TE")
    ids = np.asarray(parsed["local_id"], dtype=np.int64)
    if len(ids) != len(np.unique(ids)):
        raise Step05GateError(f"{family}: parsed local_id values are not unique")
    if len(ids) and (int(np.min(ids)) < 1 or int(np.max(ids)) > int(component["ID"])):
        raise Step05GateError(f"{family}: parsed local_id range is outside SIM ID authority")
    counts = np.asarray(parsed["pix_count"], dtype=np.int64)
    starts = np.asarray(parsed["pix_start"], dtype=np.int64)
    expected_starts = np.zeros(len(counts), dtype=np.int64)
    if len(counts) > 1:
        expected_starts[1:] = np.cumsum(counts[:-1], dtype=np.int64)
    if not np.array_equal(starts, expected_starts):
        raise Step05GateError(f"{family}: parsed pixel offsets are not compact")
    if int(np.sum(counts)) != len(parsed["pix_e"]):
        raise Step05GateError(f"{family}: parsed pixel-count sum does not close")
    return {
        "family": family,
        "generated_events_seen": generated,
        "detector_records_kept": len(parsed["stream"]),
        "pixel_hits_kept": len(parsed["pix_e"]),
        "local_id_min": int(np.min(ids)) if len(ids) else None,
        "local_id_max": int(np.max(ids)) if len(ids) else None,
        "event_weight_hz": expected_weight,
    }


def finalize_component_cache(
    spec: dict[str, Any], parsed: dict[str, Any], *, parsed_this_run: bool
) -> dict[str, Any]:
    validation = validate_parsed_component(parsed, spec["component"])
    cache_path = spec["cache"]
    if parsed_this_run:
        metadata = {
            "status": "PASS_FINGERPRINTED_RAW_SIM_PARSE_CACHE",
            "schema_version": CACHE_SCHEMA_VERSION,
            "fingerprint": spec["fingerprint"],
            "fingerprint_payload": spec["fingerprint_payload"],
            "cache": rel(cache_path),
            "cache_sha256": sha256(cache_path),
            "raw_sim_parse_completed": True,
            "validation": validation,
        }
        write_json_if_changed(spec["meta"], metadata)
    else:
        metadata = spec["previous_metadata"]
        if metadata.get("validation", {}).get("generated_events_seen") != int(
            spec["component"]["SE"]
        ):
            raise Step05GateError(f"{spec['family']}: cache metadata SE closure is stale")
    return {
        **validation,
        "SE": int(spec["component"]["SE"]),
        "ID": int(spec["component"]["ID"]),
        "cache": rel(cache_path),
        "cache_sha256": sha256(cache_path),
        "cache_fingerprint": spec["fingerprint"],
        "raw_sim_parse_completed": True,
        "parsed_this_run": parsed_this_run,
        "sim_sha256": spec["fingerprint_payload"]["sim_sha256"],
        "sim_size_bytes": spec["fingerprint_payload"]["sim_size_bytes"],
        "parser_sha256": spec["dependencies"]["adr_implementation"]["sha256"],
        "script_sha256": spec["dependencies"]["step05_harness"]["sha256"],
        "active_veto_predicate_sha256": spec["dependencies"][
            "active_veto_predicate"
        ]["sha256"],
        "cache_dependencies": spec["dependencies"],
    }


def load_single_component_cache(
    adr: Any,
    component: dict[str, Any],
    cache_root: Path,
    *,
    rebuild: bool,
    require_existing_raw_parse: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = component_cache_spec(
        adr,
        component,
        cache_root,
        rebuild=rebuild,
        require_existing_raw_parse=require_existing_raw_parse,
    )
    if spec["parse_required"]:
        spec["cache_dir"].mkdir(parents=True, exist_ok=True)
        actual = Path(
            adr.parse_sim_catalog_to_cache(
                (
                    str(spec["sim"]),
                    "delayed",
                    1.0,
                    str(spec["cache_dir"]),
                    True,
                )
            )
        )
        if actual.resolve() != spec["cache"].resolve():
            raise Step05GateError(f"{spec['family']}: ADR cache path mismatch")
    with spec["cache"].open("rb") as handle:
        parsed = pickle.load(handle)
    audit = finalize_component_cache(
        spec, parsed, parsed_this_run=bool(spec["parse_required"])
    )
    return parsed, audit


def old_neutron_component(adr: Any, rebuild: bool) -> dict[str, Any]:
    old_summary = load_json(OLD_EXACT_SUMMARY)
    te = float(old_summary["delayed_transport"]["TE_s"])
    component = {
        "family": "n",
        "status": "PASS",
        "sim": rel(OLD_NEUTRON_SIM),
        "SE": DELAYED_GENERATED_PER_POSITIVE_FAMILY,
        "ID": DELAYED_GENERATED_PER_POSITIVE_FAMILY,
        "TE_s": te,
        "event_weight_hz": 1.0 / te,
        "sim_size_bytes": OLD_NEUTRON_SIM.stat().st_size,
        "sim_sha256": sha256(OLD_NEUTRON_SIM),
    }
    configure_delayed_parser(adr, [component])
    parsed, cache_audit = load_single_component_cache(
        adr,
        component,
        WORK / "regression_file_catalogs",
        rebuild=rebuild,
        require_existing_raw_parse=True,
    )
    parsed = adr.catalog_to_arrays(parsed)
    return {
        "component": component,
        "catalog": parsed,
        "cache": resolve_path(cache_audit["cache"]),
        "cache_audit": cache_audit,
    }


def compare_window_to_retained(
    actual: dict[str, Any], expected: dict[str, Any], window: str
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for stream in ("prompt", "delayed", "science"):
        observed = actual["by_stream"][stream]
        reference = expected["by_stream"][stream]
        for stage in ("raw", "active_veto_pass", "side_compton_fov_pass"):
            event_key = f"{stage}_events"
            rate_key = "raw_rate_s-1" if stage == "raw" else f"{stage}_rate_s-1"
            if int(observed[event_key]) != int(reference[event_key]):
                raise Step05GateError(
                    f"regression {window}/{stream}/{event_key}: "
                    f"{observed[event_key]} != {reference[event_key]}"
                )
            if not math.isclose(
                float(observed[rate_key]),
                float(reference[rate_key]),
                rel_tol=1.0e-12,
                abs_tol=1.0e-15,
            ):
                raise Step05GateError(
                    f"regression {window}/{stream}/{rate_key}: "
                    f"{observed[rate_key]} != {reference[rate_key]}"
                )
            checks.append(
                {
                    "window": window,
                    "stream": stream,
                    "stage": stage,
                    "events": int(observed[event_key]),
                    "rate_cps": float(observed[rate_key]),
                }
            )
    return checks


def delayed_family_stage_closure(
    family_rows: dict[str, Any], stream_record: dict[str, Any], label: str
) -> dict[str, Any]:
    """Close every delayed selection stage over incident-family rows."""
    rows: list[dict[str, Any]] = []
    for stage, event_key, rate_key in (
        ("raw", "raw_events", "raw_rate_s-1"),
        (
            "active_veto_pass",
            "active_veto_pass_events",
            "active_veto_pass_rate_s-1",
        ),
        (
            "side_compton_fov_pass",
            "side_compton_fov_pass_events",
            "side_compton_fov_pass_rate_s-1",
        ),
    ):
        family_events = sum(int(record[stage]["events"]) for record in family_rows.values())
        family_rate = sum(
            float(record[stage]["rate_cps"]) for record in family_rows.values()
        )
        stream_events = int(stream_record[event_key])
        stream_rate = float(stream_record[rate_key])
        if family_events != stream_events:
            raise Step05GateError(
                f"{label}/{stage}: family events={family_events} stream events={stream_events}"
            )
        if not math.isclose(
            family_rate, stream_rate, rel_tol=1.0e-12, abs_tol=1.0e-15
        ):
            raise Step05GateError(
                f"{label}/{stage}: family rate={family_rate} stream rate={stream_rate}"
            )
        rows.append(
            {
                "stage": stage,
                "family_event_sum": family_events,
                "stream_events": stream_events,
                "family_rate_sum_cps": family_rate,
                "stream_rate_cps": stream_rate,
            }
        )
    return {
        "status": "PASS_DELAYED_INCIDENT_FAMILY_ALL_STAGE_CLOSURE",
        "label": label,
        "stages": rows,
    }


def synthetic_multi_family_regression(adr: Any) -> dict[str, Any]:
    """Exercise ADR merge, unequal TE, reused local IDs, zero families, and splice."""
    base = {
        "stream": np.asarray(["prompt", "prompt", "delayed", "science"], dtype=object),
        "tag": np.asarray(["gamma", "n", "activation", "focused"], dtype=object),
        "source_file": np.asarray(
            ["/tmp/prompt_g.sim", "/tmp/prompt_n.sim", "/tmp/old_d.sim", "/tmp/sci.sim"],
            dtype=object,
        ),
        "local_id": np.asarray([1, 2, 1, 1], dtype=np.int64),
        "rate_hz": np.asarray([1.0, 2.0, 0.2, 1.0], dtype=np.float64),
        "tes_total_keV": np.asarray([511.0, 0.0, 511.0, 511.0]),
        "bgo_total_keV": np.asarray([0.0, 1.0, 0.0, 0.0]),
        "pix_start": np.asarray([0, 1, 1, 2], dtype=np.int64),
        "pix_count": np.asarray([1, 0, 1, 2], dtype=np.int32),
        "pix_uid": np.asarray(["P0", "OLD", "S0", "S1"], dtype=object),
        "pix_layer": np.asarray([1, 1, 1, 2], dtype=np.int16),
        "pix_e": np.asarray([511.0, 511.0, 255.5, 255.5]),
        "pix_x": np.asarray([0.0, 0.0, 0.0, 1.0]),
        "pix_y": np.asarray([0.0, 0.0, 0.0, 0.0]),
        "pix_z": np.asarray([0.0, 0.0, 0.0, 0.0]),
        "n_generated_events_seen": 4,
        "n_kept_events": 4,
    }
    base_structure = catalog_structure_audit(base, "synthetic retained base")

    gamma = adr.empty_catalog()
    gamma.update(
        {
            "stream": ["delayed", "delayed"],
            "tag": ["gamma", "gamma"],
            "source_file": ["/tmp/synthetic_gamma.sim"] * 2,
            "local_id": [1, 2],
            "rate_hz": [0.1, 0.1],
            "tes_total_keV": [511.0, 0.0],
            "bgo_total_keV": [0.0, 1.0],
            "pix_start": [0, 1],
            "pix_count": [1, 0],
            "pix_uid": ["G0"],
            "pix_layer": [1],
            "pix_e": [511.0],
            "pix_x": [0.0],
            "pix_y": [0.0],
            "pix_z": [0.0],
            "n_generated_events_seen": 3,
            "n_kept_events": 2,
        }
    )
    neutron = adr.empty_catalog()
    neutron.update(
        {
            "stream": ["delayed"],
            "tag": ["n"],
            "source_file": ["/tmp/synthetic_n.sim"],
            "local_id": [1],
            "rate_hz": [0.05],
            "tes_total_keV": [511.0],
            "bgo_total_keV": [0.0],
            "pix_start": [0],
            "pix_count": [2],
            "pix_uid": ["N0", "N1"],
            "pix_layer": [1, 2],
            "pix_e": [255.5, 255.5],
            "pix_x": [0.0, 1.0],
            "pix_y": [0.0, 0.0],
            "pix_z": [0.0, 0.0],
            "n_generated_events_seen": 3,
            "n_kept_events": 1,
        }
    )
    gamma_structure = catalog_structure_audit(gamma, "synthetic gamma component")
    neutron_structure = catalog_structure_audit(neutron, "synthetic neutron component")
    merged = adr.empty_catalog()
    adr.merge_one_catalog_into(merged, gamma)
    adr.merge_one_catalog_into(merged, neutron)
    delayed = adr.catalog_to_arrays(merged)
    delayed_structure = catalog_structure_audit(delayed, "synthetic ADR merged delayed")
    expected_delayed_starts = np.asarray([0, 1, 1], dtype=np.int64)
    if not np.array_equal(delayed["pix_start"], expected_delayed_starts):
        raise Step05GateError(
            f"synthetic ADR merged offsets={delayed['pix_start']} "
            f"expected={expected_delayed_starts}"
        )
    components: list[dict[str, Any]] = []
    for family in FAMILIES:
        if family == "gamma":
            components.append(
                {
                    "family": family,
                    "status": "PASS",
                    "sim": "/tmp/synthetic_gamma.sim",
                    "ID": 2,
                    "SE": 3,
                    "TE_s": 10.0,
                    "event_weight_hz": 0.1,
                    "activity_Bq": 1.0,
                }
            )
        elif family == "n":
            components.append(
                {
                    "family": family,
                    "status": "PASS",
                    "sim": "/tmp/synthetic_n.sim",
                    "ID": 1,
                    "SE": 3,
                    "TE_s": 20.0,
                    "event_weight_hz": 0.05,
                    "activity_Bq": 1.0,
                }
            )
        else:
            components.append(
                {
                    "family": family,
                    "status": "PASS_ZERO_PRODUCTION",
                    "sim": None,
                    "ID": 0,
                    "SE": 0,
                    "TE_s": None,
                    "event_weight_hz": None,
                    "activity_Bq": 0.0,
                }
            )
    spliced = splice_retained_catalog(base, delayed)
    spliced_structure = catalog_structure_audit(spliced, "synthetic full spliced catalog")
    identity = retained_block_identity(base, spliced)
    lineage = lineage_audit(spliced, components)
    if lineage["status"] != "PASS_FAMILY_LOCAL_ID_LINEAGE":
        raise Step05GateError(f"synthetic lineage failed: {lineage['problems']}")
    expected_starts = np.asarray([0, 1, 1, 2, 2, 4], dtype=np.int64)
    if not np.array_equal(spliced["pix_start"], expected_starts):
        raise Step05GateError(
            f"synthetic pixel offsets={spliced['pix_start']} expected={expected_starts}"
        )

    def fake_event_hits(cat: dict[str, Any], index: int) -> list[Any]:
        start = int(cat["pix_start"][index])
        count = int(cat["pix_count"][index])
        return [SimpleNamespace(e=float(cat["pix_e"][j])) for j in range(start, start + count)]

    fake_step05 = SimpleNamespace(
        event_hits=fake_event_hits,
        side_keep_from_hits=lambda hits, disk, policy: (
            True,
            "single" if len(hits) == 1 else "keep",
        ),
    )
    manifest = {"components": components}
    family_window = delayed_family_window(
        spliced,
        WINDOWS["w2_510p58_511p42"],
        {},
        fake_step05,
        manifest,
    )
    gamma_final = family_window["gamma"]["side_compton_fov_pass"]
    neutron_final = family_window["n"]["side_compton_fov_pass"]
    central_sum = float(gamma_final["rate_cps"]) + float(neutron_final["rate_cps"])
    direct_mask = (
        (spliced["stream"] == "delayed")
        & (spliced["tes_total_keV"] >= WINDOWS["w2_510p58_511p42"][0])
        & (spliced["tes_total_keV"] < WINDOWS["w2_510p58_511p42"][1])
    )
    direct_sum = float(np.sum(spliced["rate_hz"][direct_mask]))
    if not math.isclose(central_sum, 0.15, rel_tol=0.0, abs_tol=1.0e-15):
        raise Step05GateError(f"synthetic family central sum={central_sum}")
    if not math.isclose(central_sum, direct_sum, rel_tol=0.0, abs_tol=1.0e-15):
        raise Step05GateError("synthetic family/stream sum closure failed")
    upper_ratio = float(gamma_final["rate_upper95_cps"]) / float(
        neutron_final["rate_upper95_cps"]
    )
    if not math.isclose(upper_ratio, 2.0, rel_tol=1.0e-12, abs_tol=1.0e-12):
        raise Step05GateError(f"synthetic unequal-weight Garwood ratio={upper_ratio}")
    if family_window["alpha"]["side_compton_fov_pass"]["rate_upper95_cps"] is not None:
        raise Step05GateError("synthetic zero-observed family received fictitious Garwood exposure")
    stage_closure = delayed_family_stage_closure(
        family_window,
        {
            "raw_events": 2,
            "active_veto_pass_events": 2,
            "side_compton_fov_pass_events": 2,
            "raw_rate_s-1": 0.15,
            "active_veto_pass_rate_s-1": 0.15,
            "side_compton_fov_pass_rate_s-1": 0.15,
        },
        "synthetic central delayed",
    )
    return {
        "status": "PASS_SYNTHETIC_MULTI_FAMILY_SPLICE_LINEAGE_GARWOOD",
        "actual_adr_merge_one_catalog_into_calls": 2,
        "positive_families": {"gamma": {"TE_s": 10.0}, "n": {"TE_s": 20.0}},
        "cross_family_reused_local_id": 1,
        "zero_observed_family_checked": "alpha",
        "retained_identity": identity,
        "catalog_structure": {
            "base": base_structure,
            "gamma_component": gamma_structure,
            "neutron_component": neutron_structure,
            "merged_delayed": delayed_structure,
            "full_spliced": spliced_structure,
        },
        "expected_merged_delayed_pix_start": expected_delayed_starts.tolist(),
        "observed_merged_delayed_pix_start": delayed["pix_start"].tolist(),
        "expected_pix_start": expected_starts.tolist(),
        "observed_pix_start": spliced["pix_start"].tolist(),
        "family_final_rates_cps": {
            "gamma": gamma_final["rate_cps"],
            "n": neutron_final["rate_cps"],
            "sum": central_sum,
            "stream_sum": direct_sum,
        },
        "family_garwood_upper_ratio_gamma_over_n": upper_ratio,
        "delayed_family_stage_closure": stage_closure,
        "lineage": lineage,
    }


def neutron_only_physics_algebra_regression(
    step05: Any, cat: dict[str, Any], neutron_component: dict[str, Any]
) -> dict[str, Any]:
    """Exercise atmosphere merge and rebuilt physical derivatives on retained data."""
    component_rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        if family == "n":
            component_rows.append(
                {
                    **neutron_component,
                    "activity_Bq": 1.0,
                }
            )
        else:
            component_rows.append(
                {
                    "family": family,
                    "status": "PASS_ZERO_PRODUCTION",
                    "activity_Bq": 0.0,
                    "sim": None,
                    "SE": 0,
                    "ID": 0,
                    "TE_s": None,
                    "event_weight_hz": None,
                }
            )
    components = {"components": component_rows}
    disk = step05.side_entry_disk()
    windows = {
        name: step05.summarize_window(cat, *bounds, disk=disk, reject_policy="keep")
        for name, bounds in WINDOWS.items()
    }
    science_norm = step05.load_science_physical_normalization()
    step05.add_physical_reference_to_windows(windows, science_norm)
    merge_atmosphere_and_physics(windows, cat, step05, disk, components)
    records: dict[str, Any] = {}
    for name, item in windows.items():
        closure = item.get("algebra_closure") or {}
        if closure.get("status") != "PASS_ALL_STREAM_FAMILY_AND_PHYSICAL_ALGEBRA_CLOSURE":
            raise Step05GateError(f"{name}: neutron-only physical algebra closure is absent")
        physical = item["physical_reference_flux"]
        low_total = (
            int(physical["low_stat_prompt_final_events"])
            + int(physical["low_stat_delayed_final_events"])
            + int(physical["low_stat_atm511_final_events"])
        )
        expected_relative = 1.0 / math.sqrt(low_total) if low_total else math.inf
        if int(physical["low_stat_final_background_events"]) != low_total:
            raise Step05GateError(f"{name}: rebuilt low-stat event total is stale")
        if not math.isclose(
            float(physical["low_stat_background_relative_poisson_sigma_approx"]),
            expected_relative,
            rel_tol=1.0e-12,
            abs_tol=1.0e-15,
        ):
            raise Step05GateError(f"{name}: rebuilt low-stat Poisson relative sigma is stale")
        expected_ratio = float(physical["signal_cps_at_reference_flux"]) / float(
            physical["background_cps"]
        )
        if not math.isclose(
            float(physical["signal_to_background"]),
            expected_ratio,
            rel_tol=1.0e-12,
            abs_tol=1.0e-15,
        ):
            raise Step05GateError(f"{name}: rebuilt signal/background is stale")
        records[name] = {
            "algebra_status": closure["status"],
            "signal_to_background": physical["signal_to_background"],
            "low_stat_prompt_final_events": physical[
                "low_stat_prompt_final_events"
            ],
            "low_stat_delayed_final_events": physical[
                "low_stat_delayed_final_events"
            ],
            "low_stat_atm511_final_events": physical[
                "low_stat_atm511_final_events"
            ],
            "low_stat_final_background_events": physical[
                "low_stat_final_background_events"
            ],
            "low_stat_background_relative_poisson_sigma_approx": physical[
                "low_stat_background_relative_poisson_sigma_approx"
            ],
        }
    return {
        "status": "PASS_NEUTRON_ONLY_ATMOSPHERE_AND_PHYSICAL_ALGEBRA_REGRESSION",
        "windows": records,
    }


def run_neutron_regression(rebuild_cache: bool = False) -> dict[str, Any]:
    step05 = configure_step05()
    adr = load_adr()
    with BASE_CATALOG.open("rb") as handle:
        base = pickle.load(handle)
    base_structure = catalog_structure_audit(base, "retained package-43 base catalog")
    old_prompt_end, old_science_start = stream_blocks(base)
    old_delayed = {
        field: np.asarray(base[field])[old_prompt_end:old_science_start]
        for field in EVENT_FIELDS
    }
    old_pix_begin = int(np.asarray(base["pix_start"])[old_prompt_end])
    old_pix_end = int(np.asarray(base["pix_start"])[old_science_start])
    old_delayed["pix_start"] = (
        np.asarray(base["pix_start"])[old_prompt_end:old_science_start] - old_pix_begin
    )
    for field in PIXEL_FIELDS:
        old_delayed[field] = np.asarray(base[field])[old_pix_begin:old_pix_end]
    old_delayed["n_generated_events_seen"] = DELAYED_GENERATED_PER_POSITIVE_FAMILY
    old_delayed["n_kept_events"] = old_science_start - old_prompt_end

    parsed = old_neutron_component(adr, rebuild_cache)
    replacement = parsed["catalog"]
    replacement_structure = catalog_structure_audit(
        replacement, "raw-SIM reparsed neutron delayed catalog"
    )
    comparisons: dict[str, bool] = {}
    for field in EVENT_FIELDS:
        if field == "tag":
            comparisons[field] = set(str(value) for value in replacement[field]) == {"n"}
        else:
            comparisons[field] = np.array_equal(
                np.asarray(replacement[field]), np.asarray(old_delayed[field])
            )
    for field in ("pix_start", *PIXEL_FIELDS):
        comparisons[field] = np.array_equal(
            np.asarray(replacement[field]), np.asarray(old_delayed[field])
        )
    comparisons["n_generated_events_seen"] = (
        int(replacement["n_generated_events_seen"]) == DELAYED_GENERATED_PER_POSITIVE_FAMILY
    )
    if not all(comparisons.values()):
        failed = [name for name, ok in comparisons.items() if not ok]
        raise Step05GateError(f"retained neutron parser regression failed fields={failed}")

    spliced = splice_retained_catalog(base, replacement)
    spliced_structure = catalog_structure_audit(
        spliced, "neutron-regression full spliced catalog"
    )
    identity = retained_block_identity(base, spliced)
    lineage = lineage_audit(spliced, [parsed["component"]])
    if lineage["status"] != "PASS_FAMILY_LOCAL_ID_LINEAGE":
        raise Step05GateError(f"regression lineage failed: {lineage['problems']}")
    disk = step05.side_entry_disk()
    reference = load_json(BASE_STEP05)
    selection_checks: list[dict[str, Any]] = []
    for name, bounds in WINDOWS.items():
        actual = step05.summarize_window(spliced, *bounds, disk=disk, reject_policy="keep")
        selection_checks.extend(compare_window_to_retained(actual, reference["windows"][name], name))
    synthetic = synthetic_multi_family_regression(adr)
    physics_algebra = neutron_only_physics_algebra_regression(
        step05, spliced, parsed["component"]
    )
    dependencies = authority_dependencies()

    payload = {
        "status": REGRESSION_PASS,
        "generated_at_utc": now_utc(),
        "script": rel(Path(__file__)),
        "script_sha256": sha256(Path(__file__)),
        "base_catalog": rel(BASE_CATALOG),
        "base_catalog_sha256": sha256(BASE_CATALOG),
        "base_step05": rel(BASE_STEP05),
        "base_step05_sha256": sha256(BASE_STEP05),
        "raw_neutron_parse": parsed["cache_audit"],
        "reparsed_from_raw_sim_this_run": bool(
            parsed["cache_audit"]["parsed_this_run"]
        ),
        "reparsed_from_sim": bool(
            parsed["cache_audit"]["raw_sim_parse_completed"]
        ),
        "raw_sim_parse_completed": bool(
            parsed["cache_audit"]["raw_sim_parse_completed"]
        ),
        "dependency_hashes": dependencies,
        "old_neutron_TE_s": parsed["component"]["TE_s"],
        "parser_field_identity": comparisons,
        "catalog_structure": {
            "retained_base": base_structure,
            "raw_sim_replacement": replacement_structure,
            "full_spliced": spliced_structure,
        },
        "retained_prompt_science_identity": identity,
        "lineage": lineage,
        "synthetic_multi_family_regression": synthetic,
        "neutron_only_physics_algebra_regression": physics_algebra,
        "selection_checks": selection_checks,
        "claim": (
            "Replacing the retained activation-tagged neutron block with the same "
            "events tagged as incident family n reproduces package-43 Step05 exactly."
        ),
    }
    write_json(REGRESSION_JSON, payload)
    return payload


def require_current_regression() -> dict[str, Any]:
    if not REGRESSION_JSON.is_file():
        raise Step05GateError(
            f"run `python3 {rel(Path(__file__))} regression` before consuming package44"
        )
    payload = load_json(REGRESSION_JSON)
    if payload.get("status") != REGRESSION_PASS:
        raise Step05GateError(f"neutron regression status={payload.get('status')}")
    if payload.get("script_sha256") != sha256(Path(__file__)):
        raise Step05GateError("Step05 script changed after regression; rerun regression")
    if payload.get("base_catalog_sha256") != sha256(BASE_CATALOG):
        raise Step05GateError("retained package-43 event catalog changed after regression")
    if payload.get("base_step05_sha256") != sha256(BASE_STEP05):
        raise Step05GateError("retained package-43 Step05 changed after regression")
    if payload.get("raw_sim_parse_completed") is not True:
        raise Step05GateError("regression lacks a fingerprinted raw-neutron SIM parse")
    if payload.get("reparsed_from_sim") is not True:
        raise Step05GateError("regression compatibility field does not attest raw SIM parsing")
    require_dependency_match(payload.get("dependency_hashes") or {}, "neutron regression")
    synthetic = payload.get("synthetic_multi_family_regression") or {}
    if synthetic.get("status") != "PASS_SYNTHETIC_MULTI_FAMILY_SPLICE_LINEAGE_GARWOOD":
        raise Step05GateError("synthetic multi-family regression is absent or stale")
    physics_algebra = payload.get("neutron_only_physics_algebra_regression") or {}
    if physics_algebra.get("status") != (
        "PASS_NEUTRON_ONLY_ATMOSPHERE_AND_PHYSICAL_ALGEBRA_REGRESSION"
    ):
        raise Step05GateError("neutron-only physical algebra regression is absent or stale")
    return payload


def parse_positive_components(
    component_manifest: dict[str, Any], workers: int, rebuild: bool
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    components = component_manifest["components"]
    positive = [row for row in components if row["status"] == "PASS"]
    adr = load_adr()
    configure_delayed_parser(adr, positive)
    cache_dir = WORK / "file_catalogs"
    cache_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        component_cache_spec(
            adr,
            row,
            cache_dir,
            rebuild=rebuild,
            require_existing_raw_parse=False,
        )
        for row in positive
    ]
    parse_specs = [spec for spec in specs if spec["parse_required"]]
    for spec in parse_specs:
        spec["cache_dir"].mkdir(parents=True, exist_ok=True)
    tasks = [
        (
            str(spec["sim"]),
            "delayed",
            1.0,
            str(spec["cache_dir"]),
            True,
        )
        for spec in parse_specs
    ]
    if workers > 1 and len(tasks) > 1:
        with mp.get_context("fork").Pool(processes=min(workers, len(tasks))) as pool:
            parsed_paths = pool.map(adr.parse_sim_catalog_to_cache, tasks)
    else:
        parsed_paths = [adr.parse_sim_catalog_to_cache(task) for task in tasks]
    for spec, actual_value in zip(parse_specs, parsed_paths):
        actual = Path(actual_value)
        if actual.resolve() != spec["cache"].resolve():
            raise Step05GateError(f"{spec['family']}: ADR cache path mismatch")

    merged = adr.empty_catalog()
    audits: list[dict[str, Any]] = []
    for component, spec in zip(positive, specs):
        with spec["cache"].open("rb") as handle:
            parsed = pickle.load(handle)
        audit = finalize_component_cache(
            spec, parsed, parsed_this_run=bool(spec["parse_required"])
        )
        adr.merge_one_catalog_into(merged, parsed)
        audits.append(audit)
    return adr.catalog_to_arrays(merged), audits


def build_catalog(workers: int, rebuild: bool) -> dict[str, Any]:
    regression = require_current_regression()
    components = require_current_components()
    delayed, parse_audit = parse_positive_components(components, workers, rebuild)
    delayed_structure = catalog_structure_audit(
        delayed, "package44 all-positive-family merged delayed catalog"
    )
    with BASE_CATALOG.open("rb") as handle:
        base = pickle.load(handle)
    base_structure = catalog_structure_audit(base, "retained package-43 base catalog")
    out = splice_retained_catalog(base, delayed)
    full_structure = catalog_structure_audit(out, "package44 full spliced catalog")
    identity = retained_block_identity(base, out)
    lineage = lineage_audit(out, components["components"])
    if lineage["status"] != "PASS_FAMILY_LOCAL_ID_LINEAGE":
        raise Step05GateError("family lineage failed: " + "; ".join(lineage["problems"]))

    positive_se = sum(
        int(row["SE"]) for row in components["components"] if row["status"] == "PASS"
    )
    expected_generated = PROMPT_GENERATED + SIGNAL_GENERATED + positive_se
    if int(out["n_generated_events_seen"]) != expected_generated:
        raise Step05GateError(
            f"generated-event closure={out['n_generated_events_seen']} expected={expected_generated}"
        )
    WORK.mkdir(parents=True, exist_ok=True)
    with CATALOG.open("wb") as handle:
        pickle.dump(out, handle, protocol=pickle.HIGHEST_PROTOCOL)

    stream = np.asarray(out["stream"], dtype=object)
    tags = np.asarray(out["tag"], dtype=object)
    rates = np.asarray(out["rate_hz"], dtype=np.float64)
    component_hash = sha256(COMPONENTS_JSON)
    catalog_hash = sha256(CATALOG)
    dependencies = authority_dependencies()
    payload = {
        "status": CATALOG_PASS,
        "generated_at_utc": now_utc(),
        "event_catalog": rel(CATALOG),
        "event_catalog_size_bytes": CATALOG.stat().st_size,
        "event_catalog_sha256": catalog_hash,
        "base_catalog": rel(BASE_CATALOG),
        "base_catalog_sha256": regression["base_catalog_sha256"],
        "components": rel(COMPONENTS_JSON),
        "components_sha256": component_hash,
        "component_authority_fingerprint": components["authority_fingerprint"],
        "script_sha256": sha256(Path(__file__)),
        "dependency_hashes": dependencies,
        "events_kept": len(out["stream"]),
        "pixel_hits_kept": len(out["pix_e"]),
        "generated_events_seen": int(out["n_generated_events_seen"]),
        "by_stream_events": {
            name: int(np.count_nonzero(stream == name))
            for name in ("prompt", "delayed", "science")
        },
        "delayed_by_family": {
            family: {
                "events": int(np.count_nonzero((stream == "delayed") & (tags == family))),
                "detector_record_rate_hz": float(np.sum(rates[(stream == "delayed") & (tags == family)])),
            }
            for family in FAMILIES
        },
        "parse_audit": parse_audit,
        "catalog_structure": {
            "retained_base": base_structure,
            "merged_delayed": delayed_structure,
            "full_spliced": full_structure,
        },
        "retained_prompt_science_identity": identity,
        "lineage": lineage,
        "timeline_policy": "not built here; no single delayed TE is valid for all families",
    }
    write_json(CATALOG_AUDIT_JSON, payload)
    return payload


def poisson_upper_95(count: int) -> float:
    return float(0.5 * chi2.ppf(1.0 - ALPHA_TWO_SIDED / 2.0, 2.0 * (count + 1)))


def poisson_interval_95(count: int, weight: float) -> list[float]:
    low = (
        0.0
        if count == 0
        else 0.5 * float(chi2.ppf(ALPHA_TWO_SIDED / 2.0, 2.0 * count))
    )
    return [low * weight, poisson_upper_95(count) * weight]


def binomial_lower_95(successes: int, trials: int) -> float:
    if successes <= 0 or trials <= 0:
        return 0.0
    if successes >= trials:
        return float(beta.ppf(ALPHA_TWO_SIDED / 2.0, successes, 1))
    return float(beta.ppf(ALPHA_TWO_SIDED / 2.0, successes, trials - successes + 1))


def delayed_family_window(
    cat: dict[str, Any],
    bounds: tuple[float, float],
    disk: dict[str, Any],
    step05: Any,
    components: dict[str, Any],
) -> dict[str, Any]:
    lo, hi = bounds
    stream = np.asarray(cat["stream"], dtype=object)
    tags = np.asarray(cat["tag"], dtype=object)
    rates = np.asarray(cat["rate_hz"], dtype=np.float64)
    energy = np.asarray(cat["tes_total_keV"], dtype=np.float64)
    active_energy = np.asarray(cat["bgo_total_keV"], dtype=np.float64)
    raw = (stream == "delayed") & (energy >= lo) & (energy < hi)
    active = raw & (active_energy < ACTIVE_VETO_THRESHOLD_KEV)
    final = np.zeros(len(stream), dtype=bool)
    classes: dict[str, Counter[str]] = {family: Counter() for family in FAMILIES}
    for index in np.flatnonzero(active):
        keep, classification = step05.side_keep_from_hits(
            step05.event_hits(cat, int(index)), disk, "keep"
        )
        family = str(tags[index])
        classes[family][str(classification)] += 1
        final[index] = bool(keep)
    component_by_family = {row["family"]: row for row in components["components"]}
    rows: dict[str, Any] = {}
    for family in FAMILIES:
        component = component_by_family[family]
        family_mask = tags == family
        if component["status"] in ZERO_STATUSES:
            rows[family] = {
                "status": component["status"],
                "activity_Bq": 0.0,
                "event_weight_cps": None,
                "raw": {"events": 0, "rate_cps": 0.0, "rate_interval95_cps": None, "rate_upper95_cps": None},
                "active_veto_pass": {"events": 0, "rate_cps": 0.0, "rate_interval95_cps": None, "rate_upper95_cps": None},
                "side_compton_fov_pass": {"events": 0, "rate_cps": 0.0, "rate_interval95_cps": None, "rate_upper95_cps": None},
                "uncertainty_note": (
                    "zero observed production/activity in the finite buildup campaign; no "
                    "fictitious transport exposure is assigned and no physical-zero claim or "
                    "Garwood upper limit is inferred for this family"
                ),
            }
            continue
        weight = float(component["event_weight_hz"])
        record: dict[str, Any] = {
            "status": "PASS",
            "activity_Bq": float(component["activity_Bq"]),
            "TE_s": float(component["TE_s"]),
            "event_weight_cps": weight,
            "source_file": component["sim"],
            "side_compton_class_counts": dict(sorted(classes[family].items())),
        }
        for stage, mask in (
            ("raw", raw),
            ("active_veto_pass", active),
            ("side_compton_fov_pass", final),
        ):
            selected = mask & family_mask
            count = int(np.count_nonzero(selected))
            rate = float(np.sum(rates[selected]))
            record[stage] = {
                "events": count,
                "rate_cps": rate,
                "rate_interval95_cps": poisson_interval_95(count, weight),
                "rate_upper95_cps": poisson_upper_95(count) * weight,
            }
        rows[family] = record
    return rows


def selected_prompt_components(
    cat: dict[str, Any], bounds: tuple[float, float], disk: dict[str, Any], step05: Any
) -> list[dict[str, Any]]:
    lo, hi = bounds
    stream = np.asarray(cat["stream"], dtype=object)
    tags = np.asarray(cat["tag"], dtype=object)
    rates = np.asarray(cat["rate_hz"], dtype=np.float64)
    mask = (
        (stream == "prompt")
        & (np.asarray(cat["tes_total_keV"]) >= lo)
        & (np.asarray(cat["tes_total_keV"]) < hi)
        & (np.asarray(cat["bgo_total_keV"]) < ACTIVE_VETO_THRESHOLD_KEV)
    )
    out: list[dict[str, Any]] = []
    for family in FAMILIES:
        all_family = (stream == "prompt") & (tags == family)
        unique = np.unique(rates[all_family])
        if len(unique) != 1:
            raise Step05GateError(f"prompt family {family} has weights={unique}")
        weight = float(unique[0])
        count = 0
        rate = 0.0
        for index in np.flatnonzero(mask & (tags == family)):
            keep, _classification = step05.side_keep_from_hits(
                step05.event_hits(cat, int(index)), disk, "keep"
            )
            if keep:
                count += 1
                rate += float(rates[index])
        out.append(
            {
                "family": family,
                "events": count,
                "rate_cps": rate,
                "event_weight_cps": weight,
                "rate_interval95_cps": poisson_interval_95(count, weight),
                "rate_upper95_cps": poisson_upper_95(count) * weight,
            }
        )
    return out


def merge_atmosphere_and_physics(
    windows: dict[str, Any],
    cat: dict[str, Any],
    step05: Any,
    disk: dict[str, Any],
    components: dict[str, Any],
) -> None:
    atm = load_json(ATM_SUMMARY)
    if atm.get("status") != "PASS_O8_ATM511_4PI_SIDECAR_REPLAY":
        raise Step05GateError(f"atmospheric sidecar status={atm.get('status')}")
    mission_s = MISSION_DAYS * SECONDS_PER_DAY
    for name, bounds in WINDOWS.items():
        item = windows[name]
        atm_row = atm["windows"][name]
        item["by_stream"]["atm511_sidecar"] = {
            "raw_events": int(atm_row["raw_events"]),
            "active_veto_pass_events": int(atm_row["active_veto_pass_events"]),
            "side_compton_fov_pass_events": int(atm_row["side_compton_fov_pass_events"]),
            "raw_rate_s-1": float(atm_row["raw_rate_cps"]),
            "active_veto_pass_rate_s-1": float(atm_row["active_rate_cps"]),
            "side_compton_fov_pass_rate_s-1": float(atm_row["final_rate_cps"]),
            "side_compton_class_counts": atm_row["side_compton_class_counts"],
        }
        item["delayed_by_incident_family"] = delayed_family_window(
            cat, bounds, disk, step05, components
        )
        for stage, event_key, rate_key in (
            ("raw", "raw_events", "raw_rate_s-1"),
            ("active_veto_pass", "active_veto_pass_events", "active_veto_pass_rate_s-1"),
            ("side_compton_fov_pass", "side_compton_fov_pass_events", "side_compton_fov_pass_rate_s-1"),
        ):
            item["total"][stage] = {
                "events": sum(int(row[event_key]) for row in item["by_stream"].values()),
                "rate_s-1": sum(float(row[rate_key]) for row in item["by_stream"].values()),
            }

        delayed_families = item["delayed_by_incident_family"]
        delayed_closure = delayed_family_stage_closure(
            delayed_families,
            item["by_stream"]["delayed"],
            f"{name} delayed",
        )
        item["delayed_family_stage_closure"] = delayed_closure
        delayed_stream_rate = float(item["by_stream"]["delayed"]["side_compton_fov_pass_rate_s-1"])

        prompt_components = selected_prompt_components(cat, bounds, disk, step05)
        prompt_component_events = sum(int(row["events"]) for row in prompt_components)
        prompt_component_rate = sum(float(row["rate_cps"]) for row in prompt_components)
        prompt_stream_events = int(
            item["by_stream"]["prompt"]["side_compton_fov_pass_events"]
        )
        prompt_stream_rate = float(
            item["by_stream"]["prompt"]["side_compton_fov_pass_rate_s-1"]
        )
        if prompt_component_events != prompt_stream_events:
            raise Step05GateError(
                f"{name}: prompt component events={prompt_component_events} "
                f"stream events={prompt_stream_events}"
            )
        if not math.isclose(
            prompt_component_rate,
            prompt_stream_rate,
            rel_tol=1.0e-12,
            abs_tol=1.0e-15,
        ):
            raise Step05GateError(
                f"{name}: prompt component rate={prompt_component_rate} "
                f"stream rate={prompt_stream_rate}"
            )
        prompt_closure = {
            "status": "PASS_PROMPT_INCIDENT_FAMILY_FINAL_CLOSURE",
            "family_event_sum": prompt_component_events,
            "stream_events": prompt_stream_events,
            "family_rate_sum_cps": prompt_component_rate,
            "stream_rate_cps": prompt_stream_rate,
        }
        prompt_upper = sum(float(row["rate_upper95_cps"]) for row in prompt_components)
        delayed_positive = [
            row for row in delayed_families.values() if row["status"] == "PASS"
        ]
        delayed_lower = sum(
            float(row["side_compton_fov_pass"]["rate_interval95_cps"][0])
            for row in delayed_positive
        )
        delayed_upper = sum(
            float(row["side_compton_fov_pass"]["rate_upper95_cps"])
            for row in delayed_positive
        )
        atm_weight = float(atm["normalization"]["event_rate_weight_cps"])
        atm_events = int(atm_row["side_compton_fov_pass_events"])
        atm_upper = poisson_upper_95(atm_events) * atm_weight

        by = item["by_stream"]
        prompt = float(by["prompt"]["side_compton_fov_pass_rate_s-1"])
        delayed = delayed_stream_rate
        atmosphere = float(by["atm511_sidecar"]["side_compton_fov_pass_rate_s-1"])
        science_unit = float(by["science"]["side_compton_fov_pass_rate_s-1"])
        physical = item["physical_reference_flux"]
        reference_flux = float(physical["reference_flux_ph_cm2_s"])
        injection = float(physical["rate_to_v3p5_injection_plane_s-1"])
        signal = science_unit * injection
        background = prompt + delayed + atmosphere
        prompt_events = int(by["prompt"]["side_compton_fov_pass_events"])
        delayed_events = int(by["delayed"]["side_compton_fov_pass_events"])
        signal_events = int(by["science"]["side_compton_fov_pass_events"])
        low_stat_background_events = prompt_events + delayed_events + atm_events
        low_stat_relative = (
            1.0 / math.sqrt(low_stat_background_events)
            if low_stat_background_events > 0
            else math.inf
        )
        acceptance_lower = binomial_lower_95(signal_events, SIGNAL_GENERATED)
        signal_lower = acceptance_lower * injection
        background_upper = prompt_upper + delayed_upper + atm_upper
        z = signal * mission_s / math.sqrt(background * mission_s) if background > 0.0 else math.inf
        z_lower = (
            signal_lower * mission_s / math.sqrt(background_upper * mission_s)
            if background_upper > 0.0
            else 0.0
        )
        signal_to_background = signal / background if background > 0.0 else math.inf
        source_counts = signal * mission_s
        background_counts = background * mission_s
        t3 = MISSION_DAYS * (3.0 / z) ** 2 if z > 0.0 else math.inf
        t5 = MISSION_DAYS * (5.0 / z) ** 2 if z > 0.0 else math.inf
        flux3 = REFERENCE_FLUX * 3.0 / z if z > 0.0 else math.inf

        def close_float(label: str, actual: float, expected: float) -> dict[str, Any]:
            ok = math.isclose(actual, expected, rel_tol=1.0e-12, abs_tol=1.0e-15)
            if not ok:
                raise Step05GateError(
                    f"{name}: algebra closure {label}: actual={actual} expected={expected}"
                )
            return {"actual": actual, "expected": expected, "closed": True}

        if not math.isclose(
            atmosphere, atm_events * atm_weight, rel_tol=1.0e-12, abs_tol=1.0e-15
        ):
            raise Step05GateError(
                f"{name}: atmospheric event/rate closure={atmosphere} "
                f"expected={atm_events * atm_weight}"
            )
        total_stage_closure: list[dict[str, Any]] = []
        for stage, event_key, rate_key in (
            ("raw", "raw_events", "raw_rate_s-1"),
            (
                "active_veto_pass",
                "active_veto_pass_events",
                "active_veto_pass_rate_s-1",
            ),
            (
                "side_compton_fov_pass",
                "side_compton_fov_pass_events",
                "side_compton_fov_pass_rate_s-1",
            ),
        ):
            expected_total_events = sum(int(row[event_key]) for row in by.values())
            expected_total_rate = sum(float(row[rate_key]) for row in by.values())
            actual_total = item["total"][stage]
            if int(actual_total["events"]) != expected_total_events:
                raise Step05GateError(f"{name}/{stage}: total event algebra failed")
            close_float(
                f"{stage} total rate",
                float(actual_total["rate_s-1"]),
                expected_total_rate,
            )
            total_stage_closure.append(
                {
                    "stage": stage,
                    "events": expected_total_events,
                    "rate_cps": expected_total_rate,
                }
            )

        algebra_checks = {
            "reference_flux": close_float(
                "reference flux", reference_flux, REFERENCE_FLUX
            ),
            "background_rate": close_float(
                "background rate", background, prompt + delayed + atmosphere
            ),
            "signal_rate": close_float(
                "signal rate", signal, science_unit * injection
            ),
            "source_counts": close_float(
                "source counts", source_counts, signal * mission_s
            ),
            "background_counts": close_float(
                "background counts", background_counts, background * mission_s
            ),
            "signal_to_background": close_float(
                "signal/background", signal_to_background, signal / background
            ),
        }

        # Drop every inherited prompt+delayed-only derivative before rebuilding it
        # with the atmospheric sidecar included.
        physical.clear()
        physical.update(
            {
                "reference_flux_ph_cm2_s": reference_flux,
                "rate_to_v3p5_injection_plane_s-1": injection,
                "prompt_background_cps": prompt,
                "delayed_background_cps": delayed,
                "atm511_sidecar_background_cps": atmosphere,
                "background_cps": background,
                "signal_cps_at_reference_flux": signal,
                "signal_to_background": signal_to_background,
                "mission_days": MISSION_DAYS,
                "source_counts_20d": source_counts,
                "background_counts_20d": background_counts,
                "Z20d_direct_s_over_sqrt_b": z,
                "T3_day_constant_rate_direct": t3,
                "T5_day_constant_rate_direct": t5,
                "flux_3sigma_20d_ph_cm2_s": flux3,
                "low_stat_prompt_final_events": prompt_events,
                "low_stat_delayed_final_events": delayed_events,
                "low_stat_atm511_final_events": atm_events,
                "low_stat_final_background_events": low_stat_background_events,
                "low_stat_background_relative_poisson_sigma_approx": low_stat_relative,
                "science_unit_rate_final_events": signal_events,
                "uncertainty_95": {
                    "method": (
                        "per-component two-sided Garwood intervals; prompt and delayed "
                        "display bounds are sums of marginal component endpoints, not a "
                        "joint-coverage interval; delayed Garwood terms cover transported-family "
                        "transport counting only, not buildup yield, exact-position M sampling, or "
                        "zero-observed-family upper limits; signal uses a two-sided "
                        "Clopper-Pearson lower endpoint"
                    ),
                    "prompt_components": prompt_components,
                    "prompt_background_componentwise_upper95_sum_cps": prompt_upper,
                    "delayed_components_by_incident_family": delayed_families,
                    "delayed_background_componentwise_interval95_endpoint_sum_cps": [
                        delayed_lower,
                        delayed_upper,
                    ],
                    "delayed_background_componentwise_upper95_sum_cps": delayed_upper,
                    "atm511_background_upper95_cps": atm_upper,
                    "background_componentwise_upper95_sum_cps": background_upper,
                    "signal_trials": SIGNAL_GENERATED,
                    "signal_successes": signal_events,
                    "signal_acceptance_lower95": acceptance_lower,
                    "signal_cps_lower95_at_reference_flux": signal_lower,
                    "Z20d_direct_conservative_componentwise": z_lower,
                    "flux_3sigma_20d_direct_conservative_componentwise_ph_cm2_s": (
                        REFERENCE_FLUX * 3.0 / z_lower if z_lower > 0.0 else math.inf
                    ),
                },
                "claim_note": (
                    "Direct day-15 expectation only; no multi-family Step06--Step08 mission "
                    "claim is made by this script."
                ),
            }
        )
        if int(physical["low_stat_final_background_events"]) != (
            int(physical["low_stat_prompt_final_events"])
            + int(physical["low_stat_delayed_final_events"])
            + int(physical["low_stat_atm511_final_events"])
        ):
            raise Step05GateError(f"{name}: low-stat background-event algebra failed")
        item["algebra_closure"] = {
            "status": "PASS_ALL_STREAM_FAMILY_AND_PHYSICAL_ALGEBRA_CLOSURE",
            "prompt_family_final": prompt_closure,
            "delayed_family_all_stages": delayed_closure,
            "total_all_stream_stages": total_stage_closure,
            "atm511_final_event_weight": {
                "events": atm_events,
                "event_weight_cps": atm_weight,
                "rate_cps": atmosphere,
            },
            "low_stat_background_events": {
                "prompt": prompt_events,
                "delayed": delayed_events,
                "atm511_sidecar": atm_events,
                "total": low_stat_background_events,
            },
            "physical_checks": algebra_checks,
        }


def write_rates(payload: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    for selection, item in payload["windows"].items():
        for stream, record in item["by_stream"].items():
            for stage, event_key, rate_key in (
                ("raw", "raw_events", "raw_rate_s-1"),
                ("active_veto_pass", "active_veto_pass_events", "active_veto_pass_rate_s-1"),
                ("side_compton_fov_pass", "side_compton_fov_pass_events", "side_compton_fov_pass_rate_s-1"),
            ):
                rows.append(
                    {
                        "selection_id": selection,
                        "stream": stream,
                        "incident_family": "",
                        "stage": stage,
                        "events": record[event_key],
                        "rate_cps": record[rate_key],
                        "rate_upper95_cps": "",
                    }
                )
        for family, record in item["delayed_by_incident_family"].items():
            for stage in ("raw", "active_veto_pass", "side_compton_fov_pass"):
                stage_row = record[stage]
                rows.append(
                    {
                        "selection_id": selection,
                        "stream": "delayed",
                        "incident_family": family,
                        "stage": stage,
                        "events": stage_row["events"],
                        "rate_cps": stage_row["rate_cps"],
                        "rate_upper95_cps": stage_row["rate_upper95_cps"],
                    }
                )
    write_csv(STEP05_RATES, rows)


def run_step05() -> dict[str, Any]:
    regression = require_current_regression()
    components = require_current_components()
    if not CATALOG.is_file() or not CATALOG_AUDIT_JSON.is_file():
        raise Step05GateError("build the multi-family catalog before running Step05")
    catalog_audit = load_json(CATALOG_AUDIT_JSON)
    if catalog_audit.get("status") != CATALOG_PASS:
        raise Step05GateError(f"catalog status={catalog_audit.get('status')}")
    if catalog_audit.get("components_sha256") != sha256(COMPONENTS_JSON):
        raise Step05GateError("component manifest changed after catalog build")
    if catalog_audit.get("script_sha256") != sha256(Path(__file__)):
        raise Step05GateError("Step05 script changed after catalog build")
    if catalog_audit.get("event_catalog_sha256") != sha256(CATALOG):
        raise Step05GateError("event-catalog pickle hash changed after catalog audit")
    if catalog_audit.get("component_authority_fingerprint") != components.get(
        "authority_fingerprint"
    ):
        raise Step05GateError("catalog binds a stale component authority fingerprint")
    require_dependency_match(
        catalog_audit.get("dependency_hashes") or {}, "catalog audit"
    )

    with CATALOG.open("rb") as handle:
        cat = pickle.load(handle)
    catalog_structure = catalog_structure_audit(cat, "package44 full spliced catalog")
    if (
        catalog_audit.get("catalog_structure", {}).get("full_spliced")
        != catalog_structure
    ):
        raise Step05GateError("materialized catalog structure differs from catalog audit")
    lineage = lineage_audit(cat, components["components"])
    if lineage["status"] != "PASS_FAMILY_LOCAL_ID_LINEAGE":
        raise Step05GateError("catalog lineage failed")
    step05 = configure_step05()
    prompt_audit = step05.prompt_normalization_audit()
    if prompt_audit.get("problems"):
        raise Step05GateError("prompt normalization audit failed: " + "; ".join(prompt_audit["problems"]))
    if step05.refresh_prompt_event_rates(cat):
        raise Step05GateError("retained prompt event rates required mutation")
    disk = step05.side_entry_disk()
    windows = {
        name: step05.summarize_window(cat, *bounds, disk=disk, reject_policy="keep")
        for name, bounds in WINDOWS.items()
    }
    science_norm = step05.load_science_physical_normalization()
    step05.add_physical_reference_to_windows(windows, science_norm)
    merge_atmosphere_and_physics(windows, cat, step05, disk, components)
    stream = np.asarray(cat["stream"], dtype=object)
    tags = np.asarray(cat["tag"], dtype=object)
    rates = np.asarray(cat["rate_hz"], dtype=np.float64)
    payload = {
        "status": STEP05_PASS,
        "generated_at_utc": now_utc(),
        "claim_level": "DAY15_UNSMEARED_STEP05_ONLY_NOT_PAPER_FINAL",
        "geometry_setup": rel(O8_GEOMETRY),
        "inputs": {
            "event_catalog": rel(CATALOG),
            "event_catalog_sha256": catalog_audit["event_catalog_sha256"],
            "catalog_audit": rel(CATALOG_AUDIT_JSON),
            "components": rel(COMPONENTS_JSON),
            "components_sha256": catalog_audit["components_sha256"],
            "campaign": rel(CAMPAIGN),
            "retained_prompt": rel(PROMPT_DIR),
            "retained_signal": rel(SIGNAL_SIM),
            "retained_atm511": rel(ATM_SUMMARY),
            "dependency_hashes": catalog_audit["dependency_hashes"],
        },
        "regression": {
            "authority": rel(REGRESSION_JSON),
            "status": regression["status"],
            "base_catalog_sha256": regression["base_catalog_sha256"],
        },
        "normalization": {
            "prompt_rate_rule": "per-family event rate = 1 / sum(TT_s)",
            "prompt_normalization_audit": prompt_audit,
            "delayed_rate_rule": "per incident family event rate = 1 / that family's TE_s",
            "delayed_components": components["components"],
            "science_unit_injection_rate_s-1": 1.0,
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "reject_policy": "keep",
        },
        "science_physical_normalization": science_norm,
        "catalog": {
            "events_kept": len(cat["stream"]),
            "pixel_hits_kept": len(cat["pix_e"]),
            "generated_events_seen": int(cat["n_generated_events_seen"]),
            "by_stream_events": {
                name: int(np.count_nonzero(stream == name))
                for name in ("prompt", "delayed", "science")
            },
            "delayed_by_family": {
                family: {
                    "events": int(np.count_nonzero((stream == "delayed") & (tags == family))),
                    "rate_hz": float(np.sum(rates[(stream == "delayed") & (tags == family)])),
                }
                for family in FAMILIES
            },
            "structure": catalog_structure,
            "lineage": lineage,
        },
        "windows": windows,
        "timeline": {
            "status": "NOT_RUN_MULTI_FAMILY_SCALAR_TE_INVALID",
            "reason": (
                "The legacy diagnostic uses one delayed observation time. Family-resolved "
                "transports have distinct TE values and must be folded by the later mission model."
            ),
        },
        "downstream_required": [
            "event-level 420 eV FWHM response ensemble rebuilt from this catalog",
            "family-by-nuclide trajectory mission fold",
            "paper tables/text synchronized only after both authorities pass",
        ],
    }
    write_json(STEP05_JSON, payload)
    write_rates(payload)
    return payload


def preflight() -> dict[str, Any]:
    problems: list[str] = []
    pending: list[str] = []
    geometry_bundle = retained_geometry_bundle_audit()
    if not geometry_bundle["status"].startswith("PASS_"):
        problems.extend(geometry_bundle["problems"])
    regression: dict[str, Any]
    try:
        regression = require_current_regression()
    except Step05GateError as exc:
        regression = {"status": "MISSING_OR_STALE", "problem": str(exc)}
        pending.append("neutron_only_regression")
    components = component_campaign_audit(write=False)
    if components["status"].startswith("PENDING"):
        pending.append("all8_activation_campaign")
    elif components["status"] != COMPONENT_PASS:
        problems.extend(components.get("problems") or [])
    else:
        try:
            components = require_current_components()
        except Step05GateError as exc:
            components = {
                **components,
                "materialized_manifest_status": "MISSING_OR_STALE",
                "materialized_manifest_problem": str(exc),
            }
            pending.append("stable_components_manifest")
    status = (
        "FAIL_S3D_O8_ALL8_STEP05_PREFLIGHT"
        if problems
        else "PENDING_S3D_O8_ALL8_STEP05_INPUTS"
        if pending
        else "PASS_READY_FOR_S3D_O8_ALL8_STEP05_POSTPROCESS"
    )
    payload = {
        "status": status,
        "generated_at_utc": now_utc(),
        "regression": regression,
        "components": components,
        "geometry_bundle": geometry_bundle,
        "pending": pending,
        "problems": problems,
        "production_launched": False,
        "postprocess_confirmation": {
            "flag": "--allow-postprocess",
            "token": CONFIRM_TOKEN,
            "required_for": ["catalog", "step05", "all"],
        },
    }
    write_json(PREFLIGHT_JSON, payload)
    return payload


def require_postprocess_permission(args: argparse.Namespace) -> None:
    if not args.allow_postprocess or args.confirm != CONFIRM_TOKEN:
        raise Step05GateError(
            f"postprocessing requires --allow-postprocess --confirm {CONFIRM_TOKEN}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=("regression", "components", "preflight", "catalog", "step05", "all"),
        nargs="?",
        default="preflight",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--rebuild-cache", action="store_true")
    parser.add_argument("--allow-postprocess", action="store_true")
    parser.add_argument("--confirm")
    args = parser.parse_args()
    try:
        if args.stage == "regression":
            payload = run_neutron_regression(args.rebuild_cache)
        elif args.stage == "components":
            require_current_regression()
            payload = component_campaign_audit(write=True)
            if payload.get("status") == COMPONENT_PASS:
                payload = require_current_components()
        elif args.stage == "preflight":
            payload = preflight()
        else:
            require_postprocess_permission(args)
            ready = preflight()
            if ready["status"] != "PASS_READY_FOR_S3D_O8_ALL8_STEP05_POSTPROCESS":
                payload = ready
            else:
                payload = ready
                if args.stage in ("catalog", "all"):
                    payload = build_catalog(args.workers, args.rebuild_cache)
                if args.stage in ("step05", "all"):
                    payload = run_step05()
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "regression": rel(REGRESSION_JSON) if REGRESSION_JSON.is_file() else None,
                    "components": rel(COMPONENTS_JSON) if COMPONENTS_JSON.is_file() else None,
                    "catalog": rel(CATALOG) if CATALOG.is_file() else None,
                    "step05": rel(STEP05_JSON) if STEP05_JSON.is_file() else None,
                    "production_launched": False,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2 if str(payload["status"]).startswith("FAIL") else 0
    except (Step05GateError, FileNotFoundError, KeyError, ValueError) as exc:
        failure = {
            "status": "FAIL_CLOSED",
            "generated_at_utc": now_utc(),
            "error": str(exc),
            "production_launched": False,
        }
        print(json.dumps(failure, indent=2, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
