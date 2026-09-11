#!/usr/bin/env python3
"""Build the S3d-O8 all-eight-family 420 eV detector-response authority.

This is analysis-only postprocessing.  It cannot launch Cosima.  The runner
fails closed unless package 44 proves the all-eight-family activation campaign,
component set, family lineage, per-family event weights, and exact O8 geometry.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import multiprocessing as mp
import pickle
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import numpy as np
from scipy.stats import beta, chi2


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
OUTPUTS = PACKAGE / "outputs"

P44 = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "44_s3d_o8_all8_activation_20260713"
)
CAMPAIGN = P44 / "data/s3d_o8_all8_activation_campaign.json"
COMPONENTS = P44 / "data/s3d_o8_all8_delayed_components.json"
CATALOG_AUDIT = P44 / "data/s3d_o8_all8_step05_catalog_audit.json"
STEP05_REGRESSION = P44 / "data/s3d_o8_all8_step05_neutron_regression.json"
EVENT_CATALOG = P44 / "fullchain/step05/work/event_catalog.pkl"
STEP05 = P44 / "fullchain/step05/step05_s3d_o8_all8_activation_l1_response_summary.json"
P44_STEP05_RUNNER = P44 / "code/run_s3d_o8_all8_step05.py"

O8 = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "43_geoopt_s3d_o8_fallback_20260712"
)
O8_GEOMETRY = O8 / "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
O8_DETECTOR_MAP = O8_GEOMETRY.parent / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"
ATM_SUMMARY = O8 / "data/s3d_o8_atm511_replay_summary.json"
ATM_SIM = (
    ROOT
    / "runs/geometry_optimization_20260704/s3d_o8_atm511_sidecar_3m_20260712"
    / "Atm511SidecarS3dO8_3M.inc1.id1.sim.gz"
)
ATM_PARSER = (
    ROOT
    / "engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708"
    / "build_geo_opt_atm511_sidecar_replay.py"
)
SELECTION_IMPLEMENTATION = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
ADR_IMPLEMENTATION = ROOT / "old/code/tools/make_complete_day15_report_ADR.py"
STEP09_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
RETAINED_RESPONSE_CODE = (
    ROOT
    / "engineering/ea_detector_response_closure_20260713/code"
    / "build_o8_energy_response_closure.py"
)
RETAINED_RESPONSE_SUMMARY = (
    ROOT
    / "engineering/ea_detector_response_closure_20260713/data"
    / "o8_energy_response_closure_summary.json"
)
RETAINED_RESPONSE_REPLICAS = (
    ROOT
    / "engineering/ea_detector_response_closure_20260713/data"
    / "o8_energy_response_replicas.csv"
)
RETAINED_ATM_CACHE = (
    ROOT
    / "engineering/ea_detector_response_closure_20260713/data"
    / "o8_atm511_compact_catalog.pkl"
)
RETAINED_NEUTRON_SIM = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "step02_delayed_transport_s3d_o8_neutron_delayed_m50000_20260712"
    / "DelayedDecayS3dO8NeutronM50000.inc1.id1.sim.gz"
)

PREFLIGHT = DATA / "s3d_o8_all8_response_preflight.json"
REGRESSION = DATA / "s3d_o8_all8_response_neutron_regression.json"
SUMMARY = DATA / "s3d_o8_all8_energy_response_summary.json"
REPLICAS = DATA / "s3d_o8_all8_energy_response_replicas.csv"
VALIDATION = DATA / "s3d_o8_all8_energy_response_validation.json"
ATM_CACHE = DATA / "s3d_o8_all8_atm511_compact_catalog.pkl"
README = PACKAGE / "README.md"
VALIDATOR = PACKAGE / "code/validate_s3d_o8_all8_energy_response.py"

FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
FAMILY_SET = set(FAMILIES)
ZERO_STATUSES = {"PASS_ZERO_PRODUCTION", "PASS_ZERO_ACTIVITY"}
CAMPAIGN_PASS = "PASS_S3D_O8_ALL8_ACTIVATION_AND_FAMILY_DELAYED_TRANSPORT"
COMPONENT_PASS = "PASS_S3D_O8_ALL8_STEP05_DELAYED_COMPONENTS"
CATALOG_PASS = "PASS_S3D_O8_ALL8_STEP05_CATALOG"
STEP05_PASS = "PASS_S3D_O8_ALL8_ACTIVATION_STEP05_DAY15"
REGRESSION_PASS = "PASS_S3D_O8_ALL8_RETAINED_NEUTRON_RESPONSE_REGRESSION"
RESPONSE_PASS = "PASS_S3D_O8_ALL8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE"
VALIDATION_PASS = "PASS_S3D_O8_ALL8_ENERGY_RESPONSE_VALIDATION"

FWHM_KEV = 0.420
SIGMA_KEV = FWHM_KEV / (2.0 * math.sqrt(2.0 * math.log(2.0)))
TES_THRESHOLD_KEV = 0.3
ACTIVE_THRESHOLD_KEV = 50.0
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}
PRIMARY_SEED = 26_071_301
SEED_STRIDE = 7_919
SIGNAL_TRIALS = 37_194
REFERENCE_FLUX = 1.0e-4
ALPHA_TWO_SIDED = 0.05
CONFIRM_TOKEN = "RUN_S3D_O8_ALL8_RESPONSE_64_20260713"


class ResponseError(RuntimeError):
    """A fail-closed response invariant was not satisfied."""


@dataclass(frozen=True)
class LineageSidecar:
    local_id: np.ndarray
    source_file: np.ndarray
    active_only_by_stream_tag: dict[tuple[str, str], tuple[int, float]]


_WORKER_MAIN: Any | None = None
_WORKER_LINEAGE: LineageSidecar | None = None
_WORKER_ATM: Any | None = None
_WORKER_CLOSURE: Any | None = None
_WORKER_SELECTION: Any | None = None
_WORKER_DISK: dict[str, Any] | None = None
_WORKER_COMPONENTS: dict[str, Any] | None = None
_WORKER_STEP05: dict[str, Any] | None = None

_REG_MAIN: Any | None = None
_REG_LINEAGE: LineageSidecar | None = None
_REG_ATM: Any | None = None
_REG_REFERENCE: Any | None = None
_REG_CLOSURE: Any | None = None
_REG_SELECTION: Any | None = None
_REG_DISK: dict[str, Any] | None = None
_REG_BASE_STEP05: dict[str, Any] | None = None
_REG_COMPONENTS: dict[str, Any] | None = None


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    value = Path(path)
    try:
        return value.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(value.resolve())


def resolve_path(value: Path | str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        raise ResponseError(f"refusing to write empty CSV: {rel(path)}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ResponseError(f"cannot import {rel(path)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


def exact_o8_geometry(value: str | None) -> bool:
    if not value:
        return False
    return resolve_path(value).resolve() == O8_GEOMETRY.resolve()


def poisson_upper_95(count: int) -> float:
    return float(0.5 * chi2.ppf(1.0 - ALPHA_TWO_SIDED / 2.0, 2.0 * (count + 1)))


def poisson_interval_95(count: int, weight: float) -> list[float]:
    low = 0.0 if count == 0 else 0.5 * float(chi2.ppf(ALPHA_TWO_SIDED / 2.0, 2.0 * count))
    return [low * weight, poisson_upper_95(count) * weight]


def binomial_lower_95(successes: int, trials: int) -> float:
    if successes <= 0 or trials <= 0:
        return 0.0
    if successes >= trials:
        return float(beta.ppf(ALPHA_TWO_SIDED / 2.0, successes, 1))
    return float(beta.ppf(ALPHA_TWO_SIDED / 2.0, successes, trials - successes + 1))


def require_close(actual: float, expected: float, label: str, *, atol: float = 1.0e-12) -> None:
    if not math.isclose(actual, expected, rel_tol=1.0e-10, abs_tol=atol):
        raise ResponseError(f"{label}: {actual:.17g} != {expected:.17g}")


def dependency_problems(records: dict[str, Any], label: str) -> list[str]:
    problems: list[str] = []
    if not records:
        return [f"{label}: dependency hash map is absent"]
    for name, record in records.items():
        if not isinstance(record, dict):
            problems.append(f"{label}/{name}: dependency record is not an object")
            continue
        path_value = record.get("path")
        recorded_hash = record.get("sha256")
        if path_value:
            path = resolve_path(path_value)
            if not path.is_file():
                problems.append(f"{label}/{name}: dependency path is absent")
            elif recorded_hash != sha256(path):
                problems.append(f"{label}/{name}: dependency hash is stale")
        elif not record.get("callable") or not recorded_hash:
            problems.append(f"{label}/{name}: dependency lacks path/callable hash")
    return problems


def load_selection() -> tuple[Any, dict[str, Any]]:
    module = load_module("s3d_o8_all8_response_selection", SELECTION_IMPLEMENTATION)
    module.ROOT = ROOT
    module.STEP09_SUMMARY = STEP09_SUMMARY
    module.is_v3p5_active_veto_volume = is_active_veto_volume
    return module, module.side_entry_disk()


def audit_detector_contract() -> dict[str, Any]:
    text = O8_DETECTOR_MAP.read_text(encoding="utf-8", errors="replace")
    resolution: list[tuple[float, float, float]] = []
    thresholds: list[float] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(tuple(f"D{i}.EnergyResolution Gauss" for i in range(1, 7))):
            resolution.append(tuple(float(value) for value in stripped.split()[-3:]))
        if stripped.startswith(tuple(f"D{i}.TriggerThreshold" for i in range(1, 7))):
            thresholds.append(float(stripped.split()[-2]))
    if len(resolution) != 12 or thresholds != [TES_THRESHOLD_KEV] * 6:
        raise ResponseError(
            f"detector-map response contract changed: resolution_rows={len(resolution)}, thresholds={thresholds}"
        )
    return {
        "status": "PASS_O8_DETECTOR_MAP_RESPONSE_CONTRACT",
        "geometry_setup": rel(O8_GEOMETRY),
        "detector_map": rel(O8_DETECTOR_MAP),
        "detector_map_sha256": sha256(O8_DETECTOR_MAP),
        "fwhm_keV": FWHM_KEV,
        "sigma_keV": SIGMA_KEV,
        "tes_hit_threshold_keV": TES_THRESHOLD_KEV,
        "configured_sigma_values_before_closure_keV": sorted({row[2] for row in resolution}),
    }


def upstream_audit() -> dict[str, Any]:
    required = [
        CAMPAIGN,
        COMPONENTS,
        CATALOG_AUDIT,
        STEP05_REGRESSION,
        EVENT_CATALOG,
        STEP05,
        P44_STEP05_RUNNER,
        ADR_IMPLEMENTATION,
    ]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return {"status": "PENDING_S3D_O8_ALL8_STEP05", "missing": missing, "problems": []}
    campaign = read_json(CAMPAIGN)
    components = read_json(COMPONENTS)
    catalog = read_json(CATALOG_AUDIT)
    step05 = read_json(STEP05)
    regression = read_json(STEP05_REGRESSION)
    event_catalog_hash = sha256(EVENT_CATALOG)
    problems: list[str] = []
    if campaign.get("status") != CAMPAIGN_PASS:
        problems.append(f"campaign status={campaign.get('status')}")
    if components.get("status") != COMPONENT_PASS:
        problems.append(f"components status={components.get('status')}")
    if catalog.get("status") != CATALOG_PASS:
        problems.append(f"catalog status={catalog.get('status')}")
    if step05.get("status") != STEP05_PASS:
        problems.append(f"Step05 status={step05.get('status')}")
    if regression.get("status") != "PASS_S3D_O8_NEUTRON_ONLY_STEP05_REGRESSION":
        problems.append(f"Step05 regression status={regression.get('status')}")
    if not exact_o8_geometry(campaign.get("geometry_setup")):
        problems.append(f"campaign geometry={campaign.get('geometry_setup')}")
    if not exact_o8_geometry(components.get("geometry_setup")):
        problems.append(f"component geometry={components.get('geometry_setup')}")
    if not exact_o8_geometry(step05.get("geometry_setup")):
        problems.append(f"Step05 geometry={step05.get('geometry_setup')}")
    rows = components.get("components") or []
    names = [str(row.get("family")) for row in rows]
    if len(rows) != 8 or set(names) != FAMILY_SET or len(set(names)) != 8:
        problems.append(f"component family set={names}")
    for row in rows:
        family = str(row.get("family"))
        status = str(row.get("status"))
        if status in ZERO_STATUSES:
            if row.get("sim") is not None or row.get("event_weight_hz") is not None:
                problems.append(f"{family}: finite-buildup zero observation has SIM/weight")
            continue
        if status != "PASS":
            problems.append(f"{family}: unsupported status={status}")
            continue
        te = float(row.get("TE_s") or 0.0)
        weight = float(row.get("event_weight_hz") or 0.0)
        if te <= 0.0 or not math.isclose(weight, 1.0 / te, rel_tol=0.0, abs_tol=1.0e-18):
            problems.append(f"{family}: event weight does not equal 1/TE")
        sim_value = row.get("sim")
        if not sim_value or not resolve_path(sim_value).is_file():
            problems.append(f"{family}: delayed SIM missing")
        if not exact_o8_geometry(row.get("geometry_header")):
            problems.append(f"{family}: delayed SIM geometry={row.get('geometry_header')}")
    if components.get("campaign_sha256") != sha256(CAMPAIGN):
        problems.append("component manifest does not bind the current campaign hash")
    if catalog.get("components_sha256") != sha256(COMPONENTS):
        problems.append("catalog audit does not bind the current component hash")
    if catalog.get("script_sha256") != sha256(P44_STEP05_RUNNER):
        problems.append("catalog audit does not bind the current package-44 Step05 runner")
    problems.extend(
        dependency_problems(catalog.get("dependency_hashes") or {}, "catalog audit")
    )
    if resolve_path(catalog.get("event_catalog", "/")).resolve() != EVENT_CATALOG.resolve():
        problems.append("catalog audit points to a different event catalogue")
    if int(catalog.get("event_catalog_size_bytes") or -1) != EVENT_CATALOG.stat().st_size:
        problems.append("catalog audit event-catalog size is stale")
    if catalog.get("event_catalog_sha256") != event_catalog_hash:
        problems.append("catalog audit event-catalog hash is stale")
    if (catalog.get("lineage") or {}).get("status") != "PASS_FAMILY_LOCAL_ID_LINEAGE":
        problems.append("catalog family lineage is not PASS")
    positive = {row["family"]: row for row in rows if row.get("status") == "PASS"}
    parse_rows = catalog.get("parse_audit") or []
    if {str(row.get("family")) for row in parse_rows} != set(positive):
        problems.append("catalog parse-audit family set differs from positive component set")
    for parse_row in parse_rows:
        family = str(parse_row.get("family"))
        component = positive.get(family)
        if component is None:
            continue
        sim = resolve_path(component["sim"])
        if not sim.is_file():
            # The missing-SIM problem was recorded above; avoid dereferencing it.
            continue
        if int(parse_row.get("generated_events_seen") or -1) != int(component["SE"]):
            problems.append(f"{family}: cache generated_events_seen != component SE")
        if int(parse_row.get("SE") or -1) != int(component["SE"]):
            problems.append(f"{family}: cache flattened SE != component SE")
        if int(parse_row.get("sim_size_bytes") or -1) != sim.stat().st_size:
            problems.append(f"{family}: cache audit SIM size is stale")
        if parse_row.get("sim_sha256") != sha256(sim):
            problems.append(f"{family}: cache audit SIM hash is stale")
        if parse_row.get("parser_sha256") != sha256(ADR_IMPLEMENTATION):
            problems.append(f"{family}: cache audit parser hash is stale")
        if parse_row.get("script_sha256") != sha256(P44_STEP05_RUNNER):
            problems.append(f"{family}: cache audit package-44 script hash is stale")
        if parse_row.get("raw_sim_parse_completed") is not True:
            problems.append(f"{family}: cache audit lacks raw-SIM parse provenance")
        problems.extend(
            dependency_problems(
                parse_row.get("cache_dependencies") or {},
                f"{family} parse cache",
            )
        )
    if (step05.get("catalog") or {}).get("lineage", {}).get("status") != "PASS_FAMILY_LOCAL_ID_LINEAGE":
        problems.append("Step05 family lineage is not PASS")
    inputs = step05.get("inputs") or {}
    for key, expected in (
        ("event_catalog", EVENT_CATALOG),
        ("catalog_audit", CATALOG_AUDIT),
        ("components", COMPONENTS),
        ("campaign", CAMPAIGN),
    ):
        value = inputs.get(key)
        if not value or resolve_path(value).resolve() != expected.resolve():
            problems.append(f"Step05 input {key}={value}")
    for window in WINDOWS:
        window_row = (step05.get("windows") or {}).get(window, {})
        delayed = window_row.get("delayed_by_incident_family") or {}
        if set(delayed) != FAMILY_SET:
            problems.append(f"{window}: delayed family set={sorted(delayed)}")
            continue
        delayed_sum = 0.0
        component_by_family = {str(row.get("family")): row for row in rows}
        for family in FAMILIES:
            authority = component_by_family[family]
            selected = delayed[family]
            stage = selected.get("side_compton_fov_pass") or {}
            delayed_sum += float(stage.get("rate_cps") or 0.0)
            if authority.get("status") in ZERO_STATUSES:
                if int(stage.get("events") or 0) != 0 or float(stage.get("rate_cps") or 0.0) != 0.0:
                    problems.append(f"{window}/{family}: finite-buildup zero has a selected rate")
                continue
            if selected.get("status") != "PASS":
                problems.append(f"{window}/{family}: delayed Step05 component status={selected.get('status')}")
                continue
            if not math.isclose(
                float(selected.get("event_weight_cps") or 0.0),
                float(authority.get("event_weight_hz") or 0.0),
                rel_tol=0.0,
                abs_tol=1.0e-18,
            ):
                problems.append(f"{window}/{family}: delayed Step05 event weight differs from 1/TE authority")
        stream_rate = float(
            ((window_row.get("by_stream") or {}).get("delayed") or {}).get(
                "side_compton_fov_pass_rate_s-1", 0.0
            )
        )
        if not math.isclose(delayed_sum, stream_rate, rel_tol=1.0e-12, abs_tol=1.0e-15):
            problems.append(f"{window}: delayed family-rate sum differs from delayed stream")
    return {
        "status": "PASS_READY_FOR_S3D_O8_ALL8_RESPONSE" if not problems else "FAIL_S3D_O8_ALL8_RESPONSE_UPSTREAM",
        "campaign_status": campaign.get("status"),
        "component_status": components.get("status"),
        "catalog_status": catalog.get("status"),
        "step05_status": step05.get("status"),
        "geometry_setup": rel(O8_GEOMETRY),
        "family_set": list(FAMILIES),
        "positive_families": components.get("positive_families"),
        "audited_zero_families": components.get("audited_zero_families"),
        "hashes": {
            "campaign": sha256(CAMPAIGN),
            "components": sha256(COMPONENTS),
            "catalog_audit": sha256(CATALOG_AUDIT),
            "event_catalog": event_catalog_hash,
            "step05": sha256(STEP05),
        },
        "problems": problems,
    }


def multi_family_contract_self_test(closure: Any) -> dict[str, Any]:
    """Exercise different TE, cross-family local-ID reuse, and zero observation."""
    streams: list[str] = []
    tags: list[str] = []
    rates: list[float] = []
    local_ids: list[int] = []
    source_files: list[str] = []
    prompt_weights = {family: 1.0e-3 + index * 1.0e-6 for index, family in enumerate(FAMILIES)}
    delayed_weights = {family: 2.0e-3 + index * 1.0e-6 for index, family in enumerate(FAMILIES)}
    for family in FAMILIES:
        streams.append("prompt")
        tags.append(family)
        rates.append(prompt_weights[family])
        local_ids.append(1)
        source_files.append(f"prompt-{family}")
    for family in FAMILIES[1:]:
        streams.append("delayed")
        tags.append(family)
        rates.append(delayed_weights[family])
        # The same local ID is deliberately legal across distinct families.
        local_ids.append(1)
        source_files.append(f"delayed-{family}.sim.gz")
    streams.append("science")
    tags.append("science_511_onaxis")
    rates.append(1.0)
    local_ids.append(1)
    source_files.append("science")
    n_events = len(streams)
    cat = closure.CompactCatalog(
        label="synthetic_all8_contract",
        event_id=np.arange(n_events, dtype=np.int64),
        stream=np.asarray(streams, dtype=object),
        tag=np.asarray(tags, dtype=object),
        rate_hz=np.asarray(rates, dtype=np.float64),
        active_keV=np.zeros(n_events),
        raw_total_keV=np.full(n_events, 511.0),
        hit_start=np.arange(n_events, dtype=np.int64),
        hit_count=np.ones(n_events, dtype=np.int64),
        hit_uid=np.asarray([f"pixel-{index}" for index in range(n_events)], dtype=object),
        hit_layer=np.zeros(n_events, dtype=np.int16),
        hit_e_keV=np.full(n_events, 511.0),
        hit_x_cm=np.zeros(n_events),
        hit_y_cm=np.zeros(n_events),
        hit_z_cm=np.zeros(n_events),
        active_only_rate_by_stream={},
        active_only_events_by_stream={},
        generated_events=n_events,
    )
    sidecar = LineageSidecar(
        local_id=np.asarray(local_ids, dtype=np.int64),
        source_file=np.asarray(source_files, dtype=object),
        active_only_by_stream_tag={
            (stream, family): (0, 0.0)
            for stream in ("prompt", "delayed")
            for family in FAMILIES
        },
    )
    selection = SimpleNamespace(MAX_ENUM_HITS=6)
    evaluated = evaluate_catalog(
        cat,
        closure,
        selection,
        {},
        None,
        apply_response=False,
        apply_threshold=False,
        lineage=sidecar,
        include_lineage=True,
    )
    atm_weight = float(read_json(ATM_SUMMARY)["normalization"]["event_rate_weight_cps"])
    atm_cat = closure.CompactCatalog(
        label="synthetic_atm",
        event_id=np.asarray([1], dtype=np.int64),
        stream=np.asarray(["atm511_sidecar"], dtype=object),
        tag=np.asarray(["atm511"], dtype=object),
        rate_hz=np.asarray([atm_weight]),
        active_keV=np.asarray([0.0]),
        raw_total_keV=np.asarray([511.0]),
        hit_start=np.asarray([0], dtype=np.int64),
        hit_count=np.asarray([1], dtype=np.int64),
        hit_uid=np.asarray(["atm-pixel"], dtype=object),
        hit_layer=np.asarray([0], dtype=np.int16),
        hit_e_keV=np.asarray([511.0]),
        hit_x_cm=np.asarray([0.0]),
        hit_y_cm=np.asarray([0.0]),
        hit_z_cm=np.asarray([0.0]),
        active_only_rate_by_stream={},
        active_only_events_by_stream={},
        generated_events=1,
    )
    evaluated_atm = evaluate_catalog(
        atm_cat,
        closure,
        selection,
        {},
        None,
        apply_response=False,
        apply_threshold=False,
        lineage=None,
        include_lineage=False,
    )
    base = {
        "normalization": {
            "prompt_normalization_audit": {
                "rows": [
                    {"tag": family, "rate_hz_per_event": prompt_weights[family]}
                    for family in FAMILIES
                ]
            }
        },
        "science_physical_normalization": {"rate_to_v3p5_injection_plane_s-1": 2.0},
    }
    components = {
        "components": [
            {
                "family": family,
                "status": "PASS_ZERO_PRODUCTION" if family == FAMILIES[0] else "PASS",
                "event_weight_hz": None if family == FAMILIES[0] else delayed_weights[family],
                "TE_s": None if family == FAMILIES[0] else 1.0 / delayed_weights[family],
                "activity_Bq": 0.0 if family == FAMILIES[0] else 1.0,
                "sim": None if family == FAMILIES[0] else f"delayed-{family}.sim.gz",
            }
            for family in FAMILIES
        ]
    }
    folded = build_response_step05(evaluated, evaluated_atm, base, components)
    delayed = folded["windows"]["w2_510p58_511p42"]["physical_reference_flux"]["uncertainty_95"]["delayed_components_by_incident_family"]
    lineage_rows = evaluated["windows"]["w2_510p58_511p42"]["selected_delayed_lineage"]
    strong = {
        (row["incident_family"], row["source_file"], row["local_id"])
        for row in lineage_rows
    }
    if len(lineage_rows) != 7 or len(strong) != 7:
        raise ResponseError("multi-family lineage self-test failed")
    if delayed[FAMILIES[0]]["rate_upper95_cps"] is not None:
        raise ResponseError("finite-buildup zero self-test acquired fictitious exposure")
    positive_weights = {
        float(delayed[family]["event_weight_cps"])
        for family in FAMILIES[1:]
    }
    if len(positive_weights) != 7:
        raise ResponseError("different-TE self-test collapsed family weights")
    return {
        "status": "PASS_DIFFERENT_TE_LOCAL_ID_AND_FINITE_BUILDUP_ZERO_BRANCH_SELF_TEST",
        "positive_family_weights": sorted(positive_weights),
        "cross_family_reused_local_id": 1,
        "strong_lineage_keys": len(strong),
        "finite_buildup_zero_family": FAMILIES[0],
        "finite_buildup_zero_transport_upper95_cps": delayed[FAMILIES[0]]["rate_upper95_cps"],
    }


def _regression_fingerprint(
    step05_regression: dict[str, Any], retained: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    raw_cache = resolve_path(step05_regression["raw_neutron_parse"]["cache"])
    paths = {
        "response_implementation": Path(__file__),
        "retained_response_implementation": RETAINED_RESPONSE_CODE,
        "retained_response_summary": RETAINED_RESPONSE_SUMMARY,
        "retained_response_replicas": RETAINED_RESPONSE_REPLICAS,
        "retained_atm_cache": RETAINED_ATM_CACHE,
        "package44_regression": STEP05_REGRESSION,
        "package44_runner": P44_STEP05_RUNNER,
        "raw_neutron_parse_cache": raw_cache,
    }
    for name, value in (retained.get("input_authorities") or {}).items():
        if name.endswith("_sha256") or not isinstance(value, str):
            continue
        candidate = resolve_path(value)
        if candidate.is_file():
            paths[f"retained_input/{name}"] = candidate
    records = {
        name: {
            "path": rel(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for name, path in sorted(paths.items())
    }
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest(), records


def _compare_regression_tree(
    expected: Any,
    actual: Any,
    path: str,
    problems: list[str],
    audit: dict[str, Any],
) -> None:
    """Compare the retained schema as a required subset of the regenerated tree."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            problems.append(f"{path}: expected object")
            return
        for key, value in expected.items():
            if key not in actual:
                problems.append(f"{path}/{key}: missing")
            else:
                _compare_regression_tree(value, actual[key], f"{path}/{key}", problems, audit)
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            problems.append(f"{path}: list length/type mismatch")
            return
        for index, value in enumerate(expected):
            _compare_regression_tree(value, actual[index], f"{path}[{index}]", problems, audit)
        return
    if isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if actual != expected:
            problems.append(f"{path}: {actual!r} != {expected!r}")
        else:
            audit["exact_values_checked"] += 1
        return
    if isinstance(expected, int):
        if not isinstance(actual, (int, np.integer)) or int(actual) != expected:
            problems.append(f"{path}: {actual!r} != {expected!r}")
        else:
            audit["exact_values_checked"] += 1
        return
    if isinstance(expected, float):
        try:
            observed = float(actual)
        except (TypeError, ValueError):
            problems.append(f"{path}: nonnumeric {actual!r}")
            return
        delta = abs(observed - expected)
        relative = delta / abs(expected) if expected else delta
        audit["numeric_values_checked"] += 1
        audit["max_abs_difference"] = max(audit["max_abs_difference"], delta)
        audit["max_relative_difference"] = max(audit["max_relative_difference"], relative)
        if not math.isclose(observed, expected, rel_tol=1.0e-12, abs_tol=1.0e-15):
            problems.append(f"{path}: {observed:.17g} != {expected:.17g}")
        return
    if actual != expected:
        problems.append(f"{path}: unsupported value mismatch")


def _retained_atm_catalog_readonly(closure: Any) -> Any:
    """Load the retained compact ATM cache without invoking its rewriting loader."""
    with RETAINED_ATM_CACHE.open("rb") as handle:
        cached = pickle.load(handle)
    if isinstance(cached, dict) and "catalog" in cached:
        cached = cached["catalog"]
    if isinstance(cached, dict):
        return closure.CompactCatalog(**cached)
    if isinstance(cached, closure.CompactCatalog):
        return cached
    raise ResponseError(f"unexpected retained ATM cache type={type(cached)}")


def _numeric_neutron_response_worker(index: int) -> dict[str, Any]:
    if any(
        value is None
        for value in (
            _REG_MAIN, _REG_LINEAGE, _REG_ATM, _REG_REFERENCE, _REG_CLOSURE,
            _REG_SELECTION, _REG_DISK, _REG_BASE_STEP05, _REG_COMPONENTS,
        )
    ):
        raise ResponseError("numeric-regression worker context is not initialized")
    seed = PRIMARY_SEED + index * SEED_STRIDE
    main = evaluate_catalog(
        _REG_MAIN, _REG_CLOSURE, _REG_SELECTION, _REG_DISK, seed,
        apply_response=True, apply_threshold=True, lineage=_REG_LINEAGE,
        include_lineage=index == 0,
    )
    atm = evaluate_catalog(
        _REG_ATM, _REG_CLOSURE, _REG_SELECTION, _REG_DISK,
        seed + 1_000_000_007, apply_response=True, apply_threshold=True,
        lineage=None, include_lineage=False,
    )
    generalized = build_response_step05(
        main, atm, _REG_BASE_STEP05, _REG_COMPONENTS
    )
    legacy_step = _REG_CLOSURE.primary_step05(main, atm)
    mission, timeline = _REG_CLOSURE.fold_w2_mission(legacy_step)
    reference = evaluate_catalog(
        _REG_REFERENCE, _REG_CLOSURE, _REG_SELECTION, _REG_DISK, seed,
        apply_response=True, apply_threshold=True, lineage=None,
        include_lineage=False,
    )
    reference_step = _REG_CLOSURE.reference_response_step05(reference)
    reference_mission, reference_timeline = _REG_CLOSURE.fold_reference_w2_mission(
        reference_step
    )
    row = _REG_CLOSURE.flatten_replica(index, seed, main, atm, mission)
    reference_w2 = reference_step["windows"]["w2_510p58_511p42"]
    row.update({
        "reference_prompt_final_cps": reference_w2["physical_reference_flux"]["prompt_background_cps"],
        "reference_delayed_final_cps": reference_w2["physical_reference_flux"]["delayed_background_cps"],
        "reference_signal_final_cps": reference_w2["physical_reference_flux"]["signal_cps_at_reference_flux"],
        "reference_Z20d": reference_mission["Z20d"],
        "reference_flux_3sigma_20d_ph_cm2_s": reference_mission["flux_3sigma_20d_ph_cm2_s"],
    })
    physical = generalized["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
    for key, expected in (
        ("prompt_background_cps", row["prompt_final_cps"]),
        ("delayed_background_cps", row["delayed_final_cps"]),
        ("atm511_background_cps", row["atm511_final_cps"]),
        ("science_unit_acceptance", row["science_unit_acceptance"]),
    ):
        require_close(
            float(physical[key]), float(expected),
            f"numeric regression seed {seed}/{key}", atol=1.0e-15,
        )
    delayed_family = physical["uncertainty_95"][
        "delayed_components_by_incident_family"
    ]
    require_close(
        float(delayed_family["n"]["rate_cps"]), float(row["delayed_final_cps"]),
        f"numeric regression seed {seed}/n", atol=1.0e-15,
    )
    for family in FAMILIES:
        if family != "n" and (
            int(delayed_family[family]["events"]) != 0
            or float(delayed_family[family]["rate_cps"]) != 0.0
        ):
            raise ResponseError(
                f"numeric regression seed {seed}: disabled fixture family {family} is nonzero"
            )
    result: dict[str, Any] = {"index": index, "row": row, "generalized_checks": 5}
    if index == 0:
        result["primary"] = {
            "response_seed": seed,
            "main_catalog_selection": main,
            "atm511_selection": atm,
            "step05": legacy_step,
            "mission_fold": mission,
            "reference_catalog_selection": reference,
            "reference_step05": reference_step,
            "reference_mission_fold": reference_mission,
            "timeline": timeline,
            "reference_timeline": reference_timeline,
        }
    return result


def retained_neutron_numeric_regression(
    closure: Any,
    step05_regression: dict[str, Any],
    retained: dict[str, Any],
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Execute the new generalized response on the raw-SIM-derived only-n fixture."""
    fingerprint, fingerprint_inputs = _regression_fingerprint(step05_regression, retained)
    if REGRESSION.is_file() and not force:
        cached = read_json(REGRESSION).get("numeric_response_regression") or {}
        if cached.get("status") == "PASS_EXACT_64SEED_RAW_SIM_NEUTRON_RESPONSE_REGRESSION" and cached.get("fingerprint") == fingerprint:
            return cached

    raw_audit = step05_regression["raw_neutron_parse"]
    raw_cache = resolve_path(raw_audit["cache"])
    if raw_audit.get("cache_sha256") != sha256(raw_cache):
        raise ResponseError("retained neutron parse-cache hash changed")
    with raw_cache.open("rb") as handle:
        delayed = pickle.load(handle)
    if int(delayed.get("n_generated_events_seen") or -1) != 1_000_000:
        raise ResponseError("raw-SIM-derived neutron cache generated-event closure failed")

    package44 = load_module("s3d_o8_all8_numeric_regression_splicer", P44_STEP05_RUNNER)
    base_catalog = resolve_path(step05_regression["base_catalog"])
    with base_catalog.open("rb") as handle:
        base_raw = pickle.load(handle)
    spliced = package44.splice_retained_catalog(base_raw, delayed)
    retained_identity = package44.retained_block_identity(base_raw, spliced)
    neutron_weight = float(np.unique(np.asarray(delayed["rate_hz"], dtype=np.float64))[0])
    neutron_component = {
        "family": "n",
        "status": "PASS",
        "sim": rel(RETAINED_NEUTRON_SIM),
        "SE": 1_000_000,
        "ID": 1_000_000,
        "TE_s": 1.0 / neutron_weight,
        "event_weight_hz": neutron_weight,
        "activity_Bq": 1.0,
    }
    lineage_audit = package44.lineage_audit(spliced, [neutron_component])
    if lineage_audit.get("status") != "PASS_FAMILY_LOCAL_ID_LINEAGE":
        raise ResponseError(f"raw-SIM neutron lineage regression failed: {lineage_audit.get('problems')}")

    main_cat, lineage = compact_main(
        closure,
        spliced,
        label="o8_fullchain_prompt_delayed_signal",
    )
    atm_cat = _retained_atm_catalog_readonly(closure)
    reference_cat = closure.compact_event_catalog(
        closure.REFERENCE_CATALOG,
        "reference_mass_model_511_prompt_delayed_signal",
    )
    selection, disk = closure.load_step05_selection()
    base_step05 = read_json(closure.BASE_STEP05)
    fixture_components = {
        "components": [
            neutron_component
            if family == "n"
            else {
                "family": family,
                "status": "PASS_ZERO_PRODUCTION",
                "sim": None,
                "SE": 0,
                "ID": 0,
                "TE_s": None,
                "event_weight_hz": None,
                "activity_Bq": 0.0,
            }
            for family in FAMILIES
        ]
    }
    expected_rows = read_csv(RETAINED_RESPONSE_REPLICAS)
    if len(expected_rows) != 64:
        raise ResponseError(f"retained response replicas={len(expected_rows)} expected=64")

    global _REG_MAIN, _REG_LINEAGE, _REG_ATM, _REG_REFERENCE, _REG_CLOSURE
    global _REG_SELECTION, _REG_DISK, _REG_BASE_STEP05, _REG_COMPONENTS
    _REG_MAIN = main_cat
    _REG_LINEAGE = lineage
    _REG_ATM = atm_cat
    _REG_REFERENCE = reference_cat
    _REG_CLOSURE = closure
    _REG_SELECTION = selection
    _REG_DISK = disk
    _REG_BASE_STEP05 = base_step05
    _REG_COMPONENTS = fixture_components
    rows: list[dict[str, Any]] = []
    primary: dict[str, Any] | None = None
    generalized_checks = 0
    pool = mp.get_context("fork").Pool(processes=8)
    try:
        for completed, result in enumerate(
            pool.imap(_numeric_neutron_response_worker, range(64), chunksize=1),
            start=1,
        ):
            rows.append(result["row"])
            primary = result.get("primary", primary)
            generalized_checks += int(result["generalized_checks"])
            if completed % 8 == 0:
                print(f"[neutron-response-regression] completed {completed}/64", flush=True)
    finally:
        pool.close()
        pool.join()
    rows.sort(key=lambda row: int(row["replica_index"]))
    if primary is None:
        raise ResponseError("numeric regression primary realization is absent")

    columns = list(expected_rows[0])
    integer_columns = {
        "replica_index", "response_seed", "prompt_final_events",
        "delayed_final_events", "atm511_final_events", "science_final_events",
    }
    row_problems: list[str] = []
    max_abs = 0.0
    max_rel = 0.0
    for index, (expected, actual) in enumerate(zip(expected_rows, rows)):
        for column in columns:
            if column in integer_columns:
                if int(expected[column]) != int(actual[column]):
                    row_problems.append(f"row {index}/{column}")
                continue
            wanted = float(expected[column])
            observed = float(actual[column])
            delta = abs(observed - wanted)
            max_abs = max(max_abs, delta)
            max_rel = max(max_rel, delta / abs(wanted) if wanted else delta)
            atol = 1.0e-18 if "flux" in column else 1.0e-15
            if not math.isclose(observed, wanted, rel_tol=1.0e-12, abs_tol=atol):
                row_problems.append(f"row {index}/{column}")
    if row_problems:
        raise ResponseError(f"64-seed retained replica mismatch: {row_problems[:12]}")

    tree_problems: list[str] = []
    tree_audit = {
        "numeric_values_checked": 0,
        "exact_values_checked": 0,
        "max_abs_difference": 0.0,
        "max_relative_difference": 0.0,
    }
    expected_primary = retained["primary_authority"]
    for block in (
        "response_seed", "main_catalog_selection", "atm511_selection", "step05",
        "mission_fold", "reference_catalog_selection", "reference_step05",
        "reference_mission_fold",
    ):
        _compare_regression_tree(expected_primary[block], primary[block], f"primary/{block}", tree_problems, tree_audit)
    regenerated_ensemble = closure.ensemble_summary(rows)
    _compare_regression_tree(
        retained["response_seed_ensemble"], regenerated_ensemble,
        "response_seed_ensemble", tree_problems, tree_audit,
    )
    if tree_problems:
        raise ResponseError(f"retained primary/ensemble numeric mismatch: {tree_problems[:12]}")
    return {
        "status": "PASS_EXACT_64SEED_RAW_SIM_NEUTRON_RESPONSE_REGRESSION",
        "generated_at_utc": now_utc(),
        "fingerprint": fingerprint,
        "fingerprint_inputs": fingerprint_inputs,
        "raw_sim_derived_fixture": True,
        "retained_prompt_science_identity": retained_identity,
        "lineage": lineage_audit,
        "replica_rows_checked": 64,
        "replica_columns_checked": columns,
        "replica_numeric_values_checked": 64 * (len(columns) - len(integer_columns)),
        "replica_exact_values_checked": 64 * len(integer_columns),
        "max_abs_replica_difference": max_abs,
        "max_relative_replica_difference": max_rel,
        "generalized_family_response_checks": generalized_checks,
        "primary_blocks_checked": [
            "main_catalog_selection", "atm511_selection", "step05", "mission_fold",
            "reference_catalog_selection", "reference_step05", "reference_mission_fold",
        ],
        "primary_and_ensemble_audit": tree_audit,
        "excluded_fields": ["generated_at_utc"],
    }


def run_regression(*, force_numeric: bool = False) -> dict[str, Any]:
    required = [
        STEP05_REGRESSION,
        RETAINED_RESPONSE_CODE,
        RETAINED_RESPONSE_SUMMARY,
        RETAINED_RESPONSE_REPLICAS,
        RETAINED_ATM_CACHE,
        RETAINED_NEUTRON_SIM,
        ADR_IMPLEMENTATION,
        P44_STEP05_RUNNER,
    ]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        raise ResponseError(f"retained regression authorities missing: {missing}")
    step05_regression = read_json(STEP05_REGRESSION)
    retained = read_json(RETAINED_RESPONSE_SUMMARY)
    if step05_regression.get("status") != "PASS_S3D_O8_NEUTRON_ONLY_STEP05_REGRESSION":
        raise ResponseError(f"package-44 neutron regression={step05_regression.get('status')}")
    if retained.get("status") != "PASS_O8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE":
        raise ResponseError(f"retained response status={retained.get('status')}")
    if int((retained.get("response_seed_ensemble") or {}).get("replicas") or 0) != 64:
        raise ResponseError("retained response ensemble is not 64 replicas")
    if int((retained.get("primary_authority") or {}).get("response_seed") or -1) != PRIMARY_SEED:
        raise ResponseError("retained response primary seed changed")
    old_catalog = resolve_path(retained["input_authorities"]["o8_event_catalog"])
    old_catalog_hash = sha256(old_catalog)
    if old_catalog_hash != retained["input_authorities"]["o8_event_catalog_sha256"]:
        raise ResponseError("retained neutron catalogue hash changed")
    if step05_regression.get("base_catalog_sha256") != old_catalog_hash:
        raise ResponseError("package-44 neutron regression binds a different base catalogue")
    closure = load_module("s3d_o8_all8_retained_response_regression", RETAINED_RESPONSE_CODE)
    self_test = closure.self_test()
    multi_family_self_test = multi_family_contract_self_test(closure)
    raw_audit = step05_regression.get("raw_neutron_parse") or {}
    raw_parse = bool(
        step05_regression.get("reparsed_from_sim")
        and step05_regression.get("raw_sim_parse_completed")
        and raw_audit.get("raw_sim_parse_completed")
    )
    provenance_problems: list[str] = []
    if raw_parse:
        if int(raw_audit.get("generated_events_seen") or -1) != 1_000_000:
            provenance_problems.append("retained neutron raw regression generated-event closure failed")
        if int(raw_audit.get("SE") or -1) != 1_000_000:
            provenance_problems.append("retained neutron raw regression flattened SE is absent/stale")
        if int(raw_audit.get("sim_size_bytes") or -1) != RETAINED_NEUTRON_SIM.stat().st_size:
            provenance_problems.append("retained neutron raw-regression SIM size is stale")
        if raw_audit.get("sim_sha256") != sha256(RETAINED_NEUTRON_SIM):
            provenance_problems.append("retained neutron raw-regression SIM hash is stale")
        if raw_audit.get("parser_sha256") != sha256(ADR_IMPLEMENTATION):
            provenance_problems.append("retained neutron raw-regression parser hash is stale")
        if raw_audit.get("script_sha256") != sha256(P44_STEP05_RUNNER):
            provenance_problems.append("retained neutron raw-regression Step05 script hash is stale")
        provenance_problems.extend(
            dependency_problems(
                raw_audit.get("cache_dependencies") or {},
                "retained neutron raw cache",
            )
        )
        provenance_problems.extend(
            dependency_problems(
                step05_regression.get("dependency_hashes") or {},
                "retained neutron regression",
            )
        )
    if provenance_problems:
        raise ResponseError("; ".join(provenance_problems))
    numeric = (
        retained_neutron_numeric_regression(
            closure, step05_regression, retained, force=force_numeric
        )
        if raw_parse
        else {"status": "PENDING_RAW_SIM_NEUTRON_RESPONSE_REGRESSION"}
    )
    regression_pass = (
        raw_parse
        and numeric.get("status")
        == "PASS_EXACT_64SEED_RAW_SIM_NEUTRON_RESPONSE_REGRESSION"
    )
    payload = {
        "status": REGRESSION_PASS if regression_pass else "PENDING_RAW_SIM_NEUTRON_RESPONSE_REGRESSION",
        "generated_at_utc": now_utc(),
        "response_script": rel(Path(__file__)),
        "response_script_sha256": sha256(Path(__file__)),
        "package44_step05_neutron_regression": rel(STEP05_REGRESSION),
        "package44_step05_neutron_regression_status": step05_regression["status"],
        "retained_response_summary": rel(RETAINED_RESPONSE_SUMMARY),
        "retained_response_summary_sha256": sha256(RETAINED_RESPONSE_SUMMARY),
        "retained_response_status": retained["status"],
        "retained_response_replicas": retained["response_seed_ensemble"]["replicas"],
        "retained_primary_seed": retained["primary_authority"]["response_seed"],
        "retained_catalog": rel(old_catalog),
        "retained_catalog_sha256": old_catalog_hash,
        "raw_sim_parse_required": True,
        "raw_sim_parse_completed": raw_parse,
        "raw_sim": rel(RETAINED_NEUTRON_SIM),
        "raw_neutron_parse": raw_audit,
        "response_kernel_self_test": self_test,
        "multi_family_contract_self_test": multi_family_self_test,
        "numeric_response_regression": numeric,
        "claim": (
            "The raw-SIM-derived package-44 neutron parse is spliced into the retained "
            "prompt/science catalogue and the new generalized response is executed for all "
            "64 deterministic seeds; all 19 retained replica columns, primary blocks, and "
            "ensemble statistics reproduce the retained neutron-only authority."
        ),
    }
    write_json(REGRESSION, payload)
    return payload


def compact_main(
    closure: Any,
    raw_catalog: dict[str, Any] | None = None,
    *,
    label: str = "s3d_o8_all8_prompt_family_delayed_signal",
) -> tuple[Any, LineageSidecar]:
    """Compact either the production all8 catalogue or an in-memory fixture."""
    if raw_catalog is None:
        with EVENT_CATALOG.open("rb") as handle:
            raw = pickle.load(handle)
    else:
        raw = raw_catalog
    counts_all = np.asarray(raw["pix_count"], dtype=np.int64)
    tes_mask = counts_all > 0
    event_indices = np.flatnonzero(tes_mask)
    counts = counts_all[tes_mask]
    starts = np.asarray(raw["pix_start"], dtype=np.int64)[tes_mask]
    expected_starts = np.zeros(len(counts), dtype=np.int64)
    if len(counts) > 1:
        expected_starts[1:] = np.cumsum(counts[:-1], dtype=np.int64)
    if not np.array_equal(starts, expected_starts) or int(np.sum(counts)) != len(raw["pix_e"]):
        raise ResponseError("multi-family TES hit slices are not contiguous")
    stream_all = np.asarray(raw["stream"], dtype=object)
    tag_all = np.asarray(raw["tag"], dtype=object)
    rate_all = np.asarray(raw["rate_hz"], dtype=np.float64)
    active_all = np.asarray(raw["bgo_total_keV"], dtype=np.float64)
    active_only = (~tes_mask) & (active_all > 0.0)
    active_by_stream: dict[str, float] = {}
    active_count_by_stream: dict[str, int] = {}
    active_by_group: dict[tuple[str, str], tuple[int, float]] = {}
    for stream in sorted(set(str(value) for value in stream_all)):
        mask = active_only & (stream_all == stream)
        active_by_stream[stream] = float(np.sum(rate_all[mask]))
        active_count_by_stream[stream] = int(np.count_nonzero(mask))
    for stream in ("prompt", "delayed"):
        for family in FAMILIES:
            mask = active_only & (stream_all == stream) & (tag_all == family)
            active_by_group[(stream, family)] = (
                int(np.count_nonzero(mask)),
                float(np.sum(rate_all[mask])),
            )
    compact = closure.CompactCatalog(
        label=label,
        event_id=event_indices.astype(np.int64),
        stream=stream_all[tes_mask].copy(),
        tag=tag_all[tes_mask].copy(),
        rate_hz=rate_all[tes_mask].copy(),
        active_keV=active_all[tes_mask].copy(),
        raw_total_keV=np.asarray(raw["tes_total_keV"], dtype=np.float64)[tes_mask].copy(),
        hit_start=expected_starts,
        hit_count=counts.copy(),
        hit_uid=np.asarray(raw["pix_uid"], dtype=object).copy(),
        hit_layer=np.asarray(raw["pix_layer"], dtype=np.int16).copy(),
        hit_e_keV=np.asarray(raw["pix_e"], dtype=np.float64).copy(),
        hit_x_cm=np.asarray(raw["pix_x"], dtype=np.float64).copy(),
        hit_y_cm=np.asarray(raw["pix_y"], dtype=np.float64).copy(),
        hit_z_cm=np.asarray(raw["pix_z"], dtype=np.float64).copy(),
        active_only_rate_by_stream=active_by_stream,
        active_only_events_by_stream=active_count_by_stream,
        generated_events=int(raw.get("n_generated_events_seen", 0)),
    )
    lineage = LineageSidecar(
        local_id=np.asarray(raw["local_id"], dtype=np.int64)[tes_mask].copy(),
        source_file=np.asarray(raw["source_file"], dtype=object)[tes_mask].copy(),
        active_only_by_stream_tag=active_by_group,
    )
    del raw
    return compact, lineage


def expected_atm_cache_metadata() -> dict[str, Any]:
    return {
        "schema": "s3d_o8_all8_atm_compact_cache_v2",
        "sim": rel(ATM_SIM),
        "sim_size_bytes": ATM_SIM.stat().st_size,
        "sim_sha256": sha256(ATM_SIM),
        "parser": rel(ATM_PARSER),
        "parser_sha256": sha256(ATM_PARSER),
        "atm_summary": rel(ATM_SUMMARY),
        "atm_summary_sha256": sha256(ATM_SUMMARY),
        "response_script_sha256": sha256(Path(__file__)),
    }


def build_atm(closure: Any, rebuild: bool, metadata: dict[str, Any]) -> Any:
    if ATM_CACHE.is_file() and not rebuild:
        with ATM_CACHE.open("rb") as handle:
            cached = pickle.load(handle)
        if (
            isinstance(cached, dict)
            and cached.get("metadata") == metadata
            and isinstance(cached.get("catalog"), dict)
        ):
            return closure.CompactCatalog(**cached["catalog"])
    parser = load_module("s3d_o8_all8_response_atm_parser", ATM_PARSER)
    parser.SIM = ATM_SIM
    parser.is_active_veto_volume = is_active_veto_volume
    raw = parser.parse_catalog()
    counts_all = np.asarray(raw["pix_count"], dtype=np.int64)
    tes_mask = counts_all > 0
    counts = counts_all[tes_mask]
    starts = np.asarray(raw["pix_start"], dtype=np.int64)[tes_mask]
    expected = np.zeros(len(counts), dtype=np.int64)
    if len(counts) > 1:
        expected[1:] = np.cumsum(counts[:-1], dtype=np.int64)
    if not np.array_equal(starts, expected):
        raise ResponseError("atmospheric TES hit slices are not contiguous")
    weight = float(read_json(ATM_SUMMARY)["normalization"]["event_rate_weight_cps"])
    active = np.asarray(raw["active_total_keV"], dtype=np.float64)
    active_only = (~tes_mask) & (active > 0.0)
    compact = closure.CompactCatalog(
        label="s3d_o8_atm511_sidecar",
        event_id=np.asarray(raw["local_id"], dtype=np.int64)[tes_mask].copy(),
        stream=np.full(int(np.count_nonzero(tes_mask)), "atm511_sidecar", dtype=object),
        tag=np.full(int(np.count_nonzero(tes_mask)), "atm511", dtype=object),
        rate_hz=np.full(int(np.count_nonzero(tes_mask)), weight, dtype=np.float64),
        active_keV=active[tes_mask].copy(),
        raw_total_keV=np.asarray(raw["tes_total_keV"], dtype=np.float64)[tes_mask].copy(),
        hit_start=expected,
        hit_count=counts.copy(),
        hit_uid=np.asarray(raw["pix_uid"], dtype=object).copy(),
        hit_layer=np.asarray(raw["pix_layer"], dtype=np.int16).copy(),
        hit_e_keV=np.asarray(raw["pix_e"], dtype=np.float64).copy(),
        hit_x_cm=np.asarray(raw["pix_x"], dtype=np.float64).copy(),
        hit_y_cm=np.asarray(raw["pix_y"], dtype=np.float64).copy(),
        hit_z_cm=np.asarray(raw["pix_z"], dtype=np.float64).copy(),
        active_only_rate_by_stream={"atm511_sidecar": int(np.count_nonzero(active_only)) * weight},
        active_only_events_by_stream={"atm511_sidecar": int(np.count_nonzero(active_only))},
        generated_events=int(raw["generated_events"]),
    )
    ATM_CACHE.parent.mkdir(parents=True, exist_ok=True)
    with ATM_CACHE.open("wb") as handle:
        pickle.dump(
            {"metadata": metadata, "catalog": compact.__dict__},
            handle,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    return compact


def atm_cache_audit(expected: dict[str, Any]) -> dict[str, Any]:
    if not ATM_CACHE.is_file():
        raise ResponseError("atmospheric compact cache is missing after build")
    with ATM_CACHE.open("rb") as handle:
        cached = pickle.load(handle)
    if not isinstance(cached, dict) or not isinstance(cached.get("metadata"), dict):
        raise ResponseError("atmospheric compact cache lacks provenance metadata")
    metadata = cached["metadata"]
    if metadata != expected:
        raise ResponseError("atmospheric compact cache provenance is stale")
    return {
        "status": "PASS_ATM_CACHE_BINDS_SIM_SIZE_HASH_PARSER_AND_RESPONSE_SCRIPT",
        "cache": rel(ATM_CACHE),
        "cache_size_bytes": ATM_CACHE.stat().st_size,
        "cache_sha256": sha256(ATM_CACHE),
        "metadata": metadata,
    }


def evaluate_catalog(
    cat: Any,
    closure: Any,
    selection: Any,
    disk: dict[str, Any],
    seed: int | None,
    *,
    apply_response: bool,
    apply_threshold: bool,
    lineage: LineageSidecar | None,
    include_lineage: bool,
) -> dict[str, Any]:
    hits, totals, multiplicity = closure.measured_hits(
        cat, seed, apply_response=apply_response, apply_threshold=apply_threshold
    )
    broad_lo, broad_hi = WINDOWS["broad_480_550"]
    broad_active = (
        (totals >= broad_lo)
        & (totals < broad_hi)
        & (cat.active_keV < ACTIVE_THRESHOLD_KEV)
    )
    keep = np.zeros(len(totals), dtype=bool)
    classes = np.full(len(totals), "not_evaluated", dtype=object)
    one = broad_active & (multiplicity == 1)
    keep[one] = True
    classes[one] = "single"
    many = broad_active & (multiplicity > int(selection.MAX_ENUM_HITS))
    keep[many] = True
    classes[many] = "reject_kept"
    complex_indices = np.flatnonzero(
        broad_active & (multiplicity >= 2) & (multiplicity <= int(selection.MAX_ENUM_HITS))
    )
    for index in complex_indices:
        accepted, classification = selection.side_keep_from_hits(
            closure._event_hits(cat, int(index), hits), disk, "keep"
        )
        keep[index] = bool(accepted)
        classes[index] = str(classification)

    streams = sorted(set(str(value) for value in cat.stream))
    windows: dict[str, Any] = {}
    for name, (lo, hi) in WINDOWS.items():
        raw_mask = (totals >= lo) & (totals < hi)
        active_mask = raw_mask & (cat.active_keV < ACTIVE_THRESHOLD_KEV)
        final_mask = active_mask & keep
        by_stream: dict[str, Any] = {}
        for stream in streams:
            stream_mask = cat.stream == stream
            record: dict[str, Any] = {}
            for stage, mask in (
                ("raw", raw_mask),
                ("active_veto_pass", active_mask),
                ("side_compton_fov_pass", final_mask),
            ):
                selected = stream_mask & mask
                record[f"{stage}_events"] = int(np.count_nonzero(selected))
                record[f"{stage}_rate_cps"] = float(np.sum(cat.rate_hz[selected]))
                record[f"{stage}_rate_stat_sigma_cps"] = float(
                    math.sqrt(float(np.sum(np.square(cat.rate_hz[selected]))))
                )
            class_mask = stream_mask & active_mask
            class_names = sorted(set(str(value) for value in classes[class_mask]))
            record["side_compton_class_counts"] = dict(
                sorted(Counter(str(value) for value in classes[class_mask]).items())
            )
            record["side_compton_class_rate_cps"] = {
                class_name: float(
                    np.sum(cat.rate_hz[class_mask & (classes == class_name)])
                )
                for class_name in class_names
            }
            record["side_compton_class_rate_stat_sigma_cps"] = {
                class_name: float(
                    math.sqrt(
                        float(
                            np.sum(
                                np.square(
                                    cat.rate_hz[
                                        class_mask & (classes == class_name)
                                    ]
                                )
                            )
                        )
                    )
                )
                for class_name in class_names
            }
            by_stream[stream] = record

        prompt_by_family: dict[str, Any] = {}
        delayed_by_family: dict[str, Any] = {}
        for family in FAMILIES:
            for stream, target in (("prompt", prompt_by_family), ("delayed", delayed_by_family)):
                all_mask = (cat.stream == stream) & (cat.tag == family)
                unique = np.unique(cat.rate_hz[all_mask])
                record: dict[str, Any] = {
                    "events_in_catalog": int(np.count_nonzero(all_mask)),
                    "event_weight_cps": float(unique[0]) if len(unique) == 1 else None,
                }
                if np.count_nonzero(all_mask) and len(unique) != 1:
                    raise ResponseError(f"{stream}/{family} has non-unique event weights={unique}")
                for stage, mask in (
                    ("raw", raw_mask),
                    ("active_veto_pass", active_mask),
                    ("side_compton_fov_pass", final_mask),
                ):
                    selected = all_mask & mask
                    record[stage] = {
                        "events": int(np.count_nonzero(selected)),
                        "rate_cps": float(np.sum(cat.rate_hz[selected])),
                    }
                target[family] = record
        item: dict[str, Any] = {
            "window_keV": [lo, hi],
            "by_stream": by_stream,
            "prompt_by_family": prompt_by_family,
            "prompt_final_by_tag": {
                family: {
                    "events": int(
                        prompt_by_family[family]["side_compton_fov_pass"]["events"]
                    ),
                    "rate_cps": float(
                        prompt_by_family[family]["side_compton_fov_pass"]["rate_cps"]
                    ),
                    "event_weight_cps": prompt_by_family[family][
                        "event_weight_cps"
                    ],
                }
                for family in FAMILIES
                if int(prompt_by_family[family]["events_in_catalog"]) > 0
            },
            "delayed_by_family": delayed_by_family,
        }
        if include_lineage and lineage is not None and name == "w2_510p58_511p42":
            selected = np.flatnonzero(final_mask & (cat.stream == "delayed"))
            records = [
                {
                    "incident_family": str(cat.tag[index]),
                    "source_file": str(lineage.source_file[index]),
                    "local_id": int(lineage.local_id[index]),
                    "event_weight_cps": float(cat.rate_hz[index]),
                }
                for index in selected
            ]
            strong = {(row["incident_family"], row["source_file"], row["local_id"]) for row in records}
            if len(strong) != len(records):
                raise ResponseError("selected delayed strong-lineage keys are not unique")
            item["selected_delayed_lineage"] = records
        windows[name] = item

    has_tes = multiplicity > 0
    occupancy: dict[str, Any] = {}
    for stream in streams:
        mask = cat.stream == stream
        selected = mask & (has_tes | (cat.active_keV > 0.0))
        occupancy[stream] = {
            "events": int(np.count_nonzero(selected)) + int(cat.active_only_events_by_stream.get(stream, 0)),
            "rate_hz": float(np.sum(cat.rate_hz[selected])) + float(cat.active_only_rate_by_stream.get(stream, 0.0)),
        }
    occupancy_by_family: dict[str, dict[str, Any]] = {"prompt": {}, "delayed": {}}
    if lineage is not None:
        for stream in ("prompt", "delayed"):
            for family in FAMILIES:
                mask = (cat.stream == stream) & (cat.tag == family)
                selected = mask & (has_tes | (cat.active_keV > 0.0))
                extra_count, extra_rate = lineage.active_only_by_stream_tag[(stream, family)]
                occupancy_by_family[stream][family] = {
                    "events": int(np.count_nonzero(selected)) + extra_count,
                    "rate_hz": float(np.sum(cat.rate_hz[selected])) + extra_rate,
                }
    return {
        "catalog": cat.label,
        "response_seed": seed,
        "apply_response": apply_response,
        "apply_threshold": apply_threshold,
        "tes_events_before_response": len(cat.event_id),
        "pixel_hits_before_response": len(cat.hit_e_keV),
        "tes_events_after_threshold": int(np.count_nonzero(has_tes)),
        "pixel_hits_after_threshold": int(np.count_nonzero(hits > 0.0)),
        "windows": windows,
        "occupancy": occupancy,
        "occupancy_by_family": occupancy_by_family,
    }


def validate_unsmeared(main: dict[str, Any], atm: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    atm_base = read_json(ATM_SUMMARY)
    for window in WINDOWS:
        for stream in ("prompt", "delayed", "science"):
            actual = main["windows"][window]["by_stream"][stream]
            expected = base["windows"][window]["by_stream"][stream]
            for stage in ("raw", "active_veto_pass", "side_compton_fov_pass"):
                event_key = f"{stage}_events"
                actual_rate = f"{stage}_rate_cps"
                expected_rate = f"{stage}_rate_s-1"
                if int(actual[event_key]) != int(expected[event_key]):
                    raise ResponseError(f"unsmeared {window}/{stream}/{stage} count mismatch")
                require_close(float(actual[actual_rate]), float(expected[expected_rate]), f"unsmeared {window}/{stream}/{stage}")
                checks.append({"window": window, "stream": stream, "stage": stage, "events": actual[event_key], "rate_cps": actual[actual_rate]})
        for family in FAMILIES:
            actual = main["windows"][window]["delayed_by_family"][family]
            expected = base["windows"][window]["delayed_by_incident_family"][family]
            if expected["status"] in ZERO_STATUSES:
                if any(int(actual[stage]["events"]) != 0 for stage in ("raw", "active_veto_pass", "side_compton_fov_pass")):
                    raise ResponseError(f"unsmeared finite-buildup zero family {family} contains events")
                continue
            for stage in ("raw", "active_veto_pass", "side_compton_fov_pass"):
                if int(actual[stage]["events"]) != int(expected[stage]["events"]):
                    raise ResponseError(f"unsmeared {window}/delayed/{family}/{stage} count mismatch")
                require_close(float(actual[stage]["rate_cps"]), float(expected[stage]["rate_cps"]), f"unsmeared {window}/delayed/{family}/{stage}")
        actual_atm = atm["windows"][window]["by_stream"]["atm511_sidecar"]
        expected_atm = atm_base["windows"][window]
        for stage, event_key, rate_key in (
            ("raw", "raw_events", "raw_rate_cps"),
            ("active_veto_pass", "active_veto_pass_events", "active_rate_cps"),
            ("side_compton_fov_pass", "side_compton_fov_pass_events", "final_rate_cps"),
        ):
            if int(actual_atm[f"{stage}_events"]) != int(expected_atm[event_key]):
                raise ResponseError(f"unsmeared {window}/atm/{stage} count mismatch")
            require_close(float(actual_atm[f"{stage}_rate_cps"]), float(expected_atm[rate_key]), f"unsmeared {window}/atm/{stage}")
    return {"status": "PASS_EXACT_ALL8_UNSMEARED_STEP05_REPRODUCTION", "checks": checks}


def build_response_step05(
    main: dict[str, Any],
    atm: dict[str, Any],
    base: dict[str, Any],
    components: dict[str, Any],
) -> dict[str, Any]:
    component_by_family = {row["family"]: row for row in components["components"]}
    prompt_norm = {
        str(row["tag"]): float(row["rate_hz_per_event"])
        for row in base["normalization"]["prompt_normalization_audit"]["rows"]
    }
    if set(prompt_norm) != FAMILY_SET:
        raise ResponseError(f"prompt normalization family set={sorted(prompt_norm)}")
    injection = float(base["science_physical_normalization"]["rate_to_v3p5_injection_plane_s-1"])
    atm_weight = float(read_json(ATM_SUMMARY)["normalization"]["event_rate_weight_cps"])
    windows: dict[str, Any] = {}
    for name, bounds in WINDOWS.items():
        by = dict(main["windows"][name]["by_stream"])
        by["atm511_sidecar"] = atm["windows"][name]["by_stream"]["atm511_sidecar"]
        prompt_components: list[dict[str, Any]] = []
        for family in FAMILIES:
            item = main["windows"][name]["prompt_by_family"][family]
            weight = prompt_norm[family]
            if item["events_in_catalog"] > 0 and not math.isclose(float(item["event_weight_cps"]), weight, rel_tol=0.0, abs_tol=1.0e-18):
                raise ResponseError(f"prompt {family} event-weight mismatch")
            count = int(item["side_compton_fov_pass"]["events"])
            rate = float(item["side_compton_fov_pass"]["rate_cps"])
            prompt_components.append({
                "tag": family,
                "events": count,
                "rate_cps": rate,
                "event_weight_cps": weight,
                "rate_interval95_cps": poisson_interval_95(count, weight),
                "rate_upper95_cps": poisson_upper_95(count) * weight,
            })
        delayed_components: dict[str, Any] = {}
        for family in FAMILIES:
            authority = component_by_family[family]
            measured = main["windows"][name]["delayed_by_family"][family]
            if authority["status"] in ZERO_STATUSES:
                if measured["events_in_catalog"] != 0:
                    raise ResponseError(f"finite-buildup zero family {family} has catalogue events")
                delayed_components[family] = {
                    "status": authority["status"],
                    "events": 0,
                    "rate_cps": 0.0,
                    "event_weight_cps": None,
                    "rate_interval95_cps": None,
                    "rate_upper95_cps": None,
                    "uncertainty_note": (
                        "finite buildup observed zero production; central delayed estimate is zero and no fictitious "
                        "transport exposure is assigned; this interval does not cover buildup-yield, M-sampling, "
                        "or zero-family uncertainty"
                    ),
                }
                continue
            weight = float(authority["event_weight_hz"])
            if measured["events_in_catalog"] > 0 and not math.isclose(float(measured["event_weight_cps"]), weight, rel_tol=0.0, abs_tol=1.0e-18):
                raise ResponseError(f"delayed {family} event-weight mismatch")
            count = int(measured["side_compton_fov_pass"]["events"])
            rate = float(measured["side_compton_fov_pass"]["rate_cps"])
            require_close(rate, count * weight, f"delayed {family} selected rate", atol=1.0e-15)
            delayed_components[family] = {
                "status": "PASS",
                "events": count,
                "rate_cps": rate,
                "event_weight_cps": weight,
                "TE_s": float(authority["TE_s"]),
                "activity_Bq": float(authority["activity_Bq"]),
                "source_file": authority["sim"],
                "rate_interval95_cps": poisson_interval_95(count, weight),
                "rate_upper95_cps": poisson_upper_95(count) * weight,
            }
        prompt = float(by["prompt"]["side_compton_fov_pass_rate_cps"])
        delayed = float(by["delayed"]["side_compton_fov_pass_rate_cps"])
        atmosphere = float(by["atm511_sidecar"]["side_compton_fov_pass_rate_cps"])
        science_unit = float(by["science"]["side_compton_fov_pass_rate_cps"])
        require_close(prompt, sum(float(row["rate_cps"]) for row in prompt_components), f"{name} prompt family sum")
        require_close(delayed, sum(float(row["rate_cps"]) for row in delayed_components.values()), f"{name} delayed family sum")
        signal = science_unit * injection
        signal_events = int(by["science"]["side_compton_fov_pass_events"])
        signal_lower = binomial_lower_95(signal_events, SIGNAL_TRIALS) * injection
        prompt_upper = sum(float(row["rate_upper95_cps"]) for row in prompt_components)
        delayed_upper = sum(float(row["rate_upper95_cps"] or 0.0) for row in delayed_components.values())
        atm_events = int(by["atm511_sidecar"]["side_compton_fov_pass_events"])
        atm_upper = poisson_upper_95(atm_events) * atm_weight
        windows[name] = {
            "window_keV": list(bounds),
            "by_stream": by,
            "physical_reference_flux": {
                "reference_flux_ph_cm2_s": REFERENCE_FLUX,
                "rate_to_injection_plane_cps": injection,
                "prompt_background_cps": prompt,
                "delayed_background_cps": delayed,
                "atm511_background_cps": atmosphere,
                "background_cps": prompt + delayed + atmosphere,
                "science_unit_acceptance": science_unit,
                "signal_cps_at_reference_flux": signal,
                "uncertainty_95": {
                    "method": (
                        "two-sided Garwood endpoints summed across prompt and positive delayed incident-family components "
                        "as a componentwise endpoint sum, not a joint-coverage interval; "
                        "finite-buildup zero-observation families have no fictitious transport exposure; this bound does not cover their "
                        "buildup-yield or M-sampling uncertainty; signal uses a two-sided Clopper-Pearson lower endpoint"
                    ),
                    "prompt_components": prompt_components,
                    "prompt_background_componentwise_upper95_sum_cps": prompt_upper,
                    "delayed_components_by_incident_family": delayed_components,
                    "delayed_background_componentwise_upper95_sum_cps": delayed_upper,
                    "atm511_background_upper95_cps": atm_upper,
                    "background_componentwise_upper95_sum_cps": prompt_upper + delayed_upper + atm_upper,
                    "signal_trials": SIGNAL_TRIALS,
                    "signal_successes": signal_events,
                    "signal_acceptance_lower95": signal_lower / injection,
                    "signal_cps_lower95_at_reference_flux": signal_lower,
                },
            },
        }
    return {
        "status": "PASS_S3D_O8_ALL8_EVENT_LEVEL_420EV_FWHM_RESPONSE_STEP05",
        "response_seed": main["response_seed"],
        "response_model": {
            "distribution": "independent Gaussian per aggregated TES pixel readout",
            "fwhm_keV": FWHM_KEV,
            "sigma_keV": SIGMA_KEV,
            "post_noise_hit_threshold_keV": TES_THRESHOLD_KEV,
        },
        "occupancy_day15": {**main["occupancy"], **atm["occupancy"]},
        "occupancy_day15_by_family": main["occupancy_by_family"],
        "windows": windows,
    }


def evaluate_worker(index: int) -> dict[str, Any]:
    if any(value is None for value in (_WORKER_MAIN, _WORKER_LINEAGE, _WORKER_ATM, _WORKER_CLOSURE, _WORKER_SELECTION, _WORKER_DISK, _WORKER_COMPONENTS, _WORKER_STEP05)):
        raise ResponseError("response worker context is not initialized")
    seed = PRIMARY_SEED + index * SEED_STRIDE
    main = evaluate_catalog(
        _WORKER_MAIN, _WORKER_CLOSURE, _WORKER_SELECTION, _WORKER_DISK, seed,
        apply_response=True, apply_threshold=True, lineage=_WORKER_LINEAGE,
        include_lineage=index == 0,
    )
    atm = evaluate_catalog(
        _WORKER_ATM, _WORKER_CLOSURE, _WORKER_SELECTION, _WORKER_DISK,
        seed + 1_000_000_007, apply_response=True, apply_threshold=True,
        lineage=None, include_lineage=False,
    )
    response = build_response_step05(main, atm, _WORKER_STEP05, _WORKER_COMPONENTS)
    w2 = response["windows"]["w2_510p58_511p42"]
    physical = w2["physical_reference_flux"]
    delayed_family = physical["uncertainty_95"]["delayed_components_by_incident_family"]
    row: dict[str, Any] = {
        "replica_index": index,
        "response_seed": seed,
        "prompt_final_events": w2["by_stream"]["prompt"]["side_compton_fov_pass_events"],
        "prompt_final_cps": physical["prompt_background_cps"],
        "delayed_final_events": w2["by_stream"]["delayed"]["side_compton_fov_pass_events"],
        "delayed_final_cps": physical["delayed_background_cps"],
        "atm511_final_events": w2["by_stream"]["atm511_sidecar"]["side_compton_fov_pass_events"],
        "atm511_final_cps": physical["atm511_background_cps"],
        "science_final_events": w2["by_stream"]["science"]["side_compton_fov_pass_events"],
        "science_unit_acceptance": physical["science_unit_acceptance"],
        "day15_background_cps": physical["background_cps"],
        "day15_signal_cps": physical["signal_cps_at_reference_flux"],
    }
    for family in FAMILIES:
        row[f"delayed_{family}_final_events"] = delayed_family[family]["events"]
        row[f"delayed_{family}_final_cps"] = delayed_family[family]["rate_cps"]
    result: dict[str, Any] = {"index": index, "row": row}
    if index == 0:
        result["primary"] = {"main": main, "atm": atm, "step05": response}
    return result


def ensemble_summary(rows: list[dict[str, Any]], components: dict[str, Any]) -> dict[str, Any]:
    """Audit total and incident-family response stability across exactly 64 seeds.

    Low-count families are deliberately routed through explicit sparse/all-zero
    branches rather than through unstable relative-deviation tests.  Every
    branch still enforces seed identity, non-negativity, finiteness, and the
    exact per-family ``count * (1/TE)`` rate closure.
    """
    metrics = (
        "prompt_final_cps",
        "delayed_final_cps",
        "atm511_final_cps",
        "science_unit_acceptance",
        "day15_background_cps",
        "day15_signal_cps",
    )
    summary: dict[str, Any] = {}
    failures: list[str] = []
    for metric in metrics:
        values = np.asarray([float(row[metric]) for row in rows], dtype=np.float64)
        half = len(values) // 2
        mean = float(np.mean(values))
        sd = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
        primary = float(values[0])
        standardized = abs(primary - mean) / sd if sd > 0.0 else (0.0 if primary == mean else math.inf)
        half_delta = abs(float(np.mean(values[:half])) - float(np.mean(values[half:]))) / abs(mean) if mean else 0.0
        record = {
            "mean": mean,
            "sample_sd": sd,
            "mean_standard_error": sd / math.sqrt(len(values)) if len(values) > 1 else 0.0,
            "q02p5": float(np.quantile(values, 0.025)),
            "q16": float(np.quantile(values, 0.16)),
            "median": float(np.median(values)),
            "q84": float(np.quantile(values, 0.84)),
            "q97p5": float(np.quantile(values, 0.975)),
            "primary_value": primary,
            "primary_relative_deviation_from_mean": abs(primary - mean) / abs(mean) if mean else 0.0,
            "primary_standardized_deviation": standardized,
            "half_mean_relative_difference": half_delta,
            "primary_within_q02p5_q97p5": bool(
                np.quantile(values, 0.025) <= primary <= np.quantile(values, 0.975)
            ),
        }
        if standardized > 3.0 or record["primary_relative_deviation_from_mean"] > 0.20 or half_delta > 0.10:
            failures.append(metric)
        summary[metric] = record

    component_by_family = {
        str(row["family"]): row for row in components.get("components", [])
    }
    if set(component_by_family) != FAMILY_SET:
        failures.append("component_family_set")
    family_metrics: dict[str, Any] = {}
    family_failures: list[str] = []
    for family in FAMILIES:
        component = component_by_family.get(family) or {}
        counts = np.asarray(
            [int(row[f"delayed_{family}_final_events"]) for row in rows],
            dtype=np.int64,
        )
        rates = np.asarray(
            [float(row[f"delayed_{family}_final_cps"]) for row in rows],
            dtype=np.float64,
        )
        problems: list[str] = []
        if np.any(counts < 0):
            problems.append("negative_count")
        if np.any(~np.isfinite(rates)) or np.any(rates < 0.0):
            problems.append("nonfinite_or_negative_rate")
        status = str(component.get("status"))
        if status in ZERO_STATUSES:
            if np.any(counts != 0) or np.any(rates != 0.0):
                problems.append("finite_buildup_zero_family_has_selected_response")
            family_metrics[family] = {
                "status": (
                    "PASS_FINITE_BUILDUP_ZERO_NO_TRANSPORT_RESPONSE_REPLICAS"
                    if not problems
                    else "FAIL_FINITE_BUILDUP_ZERO_RESPONSE_REPLICAS"
                ),
                "component_status": status,
                "branch": "FINITE_BUILDUP_ZERO_OBSERVATION_NO_TRANSPORT_EXPOSURE",
                "replicas": len(rows),
                "event_weight_cps": None,
                "primary_events": int(counts[0]),
                "primary_rate_cps": float(rates[0]),
                "all_replicas_exact_zero": bool(
                    np.all(counts == 0) and np.all(rates == 0.0)
                ),
                "problems": problems,
            }
        elif status == "PASS":
            weight = float(component.get("event_weight_hz") or 0.0)
            if not math.isfinite(weight) or weight <= 0.0:
                problems.append("invalid_event_weight")
            expected_rates = counts.astype(np.float64) * weight
            if not np.allclose(rates, expected_rates, rtol=0.0, atol=1.0e-15):
                problems.append("count_weight_rate_closure")
            mean_count = float(np.mean(counts))
            sd_count = float(np.std(counts, ddof=1)) if len(counts) > 1 else 0.0
            primary_count = int(counts[0])
            zero_fraction = float(np.mean(counts == 0))
            half = len(counts) // 2
            first_half = float(np.mean(counts[:half]))
            second_half = float(np.mean(counts[half:]))
            half_delta = (
                abs(first_half - second_half) / abs(mean_count)
                if mean_count
                else 0.0
            )
            relative = (
                abs(primary_count - mean_count) / abs(mean_count)
                if mean_count
                else 0.0
            )
            standardized = (
                abs(primary_count - mean_count) / sd_count
                if sd_count > 0.0
                else (0.0 if primary_count == mean_count else math.inf)
            )
            q02p5 = float(np.quantile(counts, 0.025))
            q16 = float(np.quantile(counts, 0.16))
            median = float(np.median(counts))
            q84 = float(np.quantile(counts, 0.84))
            q97p5 = float(np.quantile(counts, 0.975))
            primary_in_quantiles = bool(q02p5 <= primary_count <= q97p5)
            if bool(np.all(counts == 0)):
                branch = "ALL_ZERO_SELECTED_RESPONSE_REPLICAS"
            elif mean_count < 5.0 or zero_fraction > 0.25:
                branch = "SPARSE_SELECTED_RESPONSE_REPLICAS"
            else:
                branch = "REGULAR_SELECTED_RESPONSE_REPLICAS"
                if standardized > 3.0:
                    problems.append("primary_gt_3sd_from_mean")
                if relative > 0.20:
                    problems.append("primary_gt_20pct_from_mean")
                if half_delta > 0.10:
                    problems.append("half_mean_gt_10pct")
                if not primary_in_quantiles:
                    problems.append("primary_outside_empirical_q02p5_q97p5")
            family_metrics[family] = {
                "status": (
                    "PASS_FAMILY_RESPONSE_SEED_GATE"
                    if not problems
                    else "FAIL_FAMILY_RESPONSE_SEED_GATE"
                ),
                "component_status": status,
                "branch": branch,
                "replicas": len(rows),
                "event_weight_cps": weight,
                "primary_events": primary_count,
                "primary_rate_cps": float(rates[0]),
                "mean_events": mean_count,
                "sample_sd_events": sd_count,
                "mean_rate_cps": float(np.mean(rates)),
                "sample_sd_rate_cps": (
                    float(np.std(rates, ddof=1)) if len(rates) > 1 else 0.0
                ),
                "q02p5_events": q02p5,
                "q16_events": q16,
                "median_events": median,
                "q84_events": q84,
                "q97p5_events": q97p5,
                "zero_replica_fraction": zero_fraction,
                "first_half_mean_events": first_half,
                "second_half_mean_events": second_half,
                "half_mean_relative_difference": half_delta,
                "primary_relative_deviation_from_mean": relative,
                "primary_standardized_deviation": standardized,
                "primary_within_q02p5_q97p5": primary_in_quantiles,
                "count_weight_rate_closure_all_replicas": bool(
                    np.allclose(rates, expected_rates, rtol=0.0, atol=1.0e-15)
                ),
                "problems": problems,
            }
        else:
            problems.append(f"unsupported_component_status={status}")
            family_metrics[family] = {
                "status": "FAIL_FAMILY_RESPONSE_SEED_GATE",
                "component_status": status,
                "branch": "UNSUPPORTED_COMPONENT_STATUS",
                "problems": problems,
            }
        if problems:
            family_failures.append(family)

    if len(rows) != 64:
        failures.append(f"replica_count={len(rows)}_expected=64")
    failures.extend(f"delayed_family:{family}" for family in family_failures)
    return {
        "status": "PASS_RESPONSE_SEED_ENSEMBLE" if not failures else "FAIL_RESPONSE_SEED_ENSEMBLE",
        "replicas": len(rows),
        "primary_seed": PRIMARY_SEED,
        "seed_stride": SEED_STRIDE,
        "failure_metrics": failures,
        "acceptance_contract": (
            "exactly 64 deterministic seeds; total metrics satisfy the preregistered "
            "3-sigma/20-percent/10-percent gates; each positive delayed family has "
            "explicit regular, sparse, or all-zero selected-response handling with exact "
            "count times 1/TE closure; finite-buildup zero-observation families remain "
            "exactly zero without an invented transport exposure"
        ),
        "metrics": summary,
        "delayed_family_metrics": family_metrics,
    }


def write_readme(payload: dict[str, Any]) -> None:
    primary = payload["primary_authority"]["step05"]
    physical = primary["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
    delayed = physical["uncertainty_95"]["delayed_components_by_incident_family"]
    positive = [family for family in FAMILIES if delayed[family]["status"] == "PASS"]
    zeros = [family for family in FAMILIES if delayed[family]["status"] in ZERO_STATUSES]
    README.write_text(
        "\n".join(
            [
                "# S3d-O8 all-eight-family detector-response closure",
                "",
                f"Status: `{payload['status']}`",
                "",
                "This package applies the 420 eV FWHM Gaussian TES response per aggregated pixel,",
                "then the 0.3 keV measured-hit threshold and the frozen W2/active-veto/side-entry",
                "selection, to the package-44 all-eight-family catalogue.",
                "",
                "## Primary W2 day-15 result",
                "",
                f"- Response seed: `{PRIMARY_SEED}`.",
                f"- Prompt: `{physical['prompt_background_cps']:.12g}` cps.",
                f"- Delayed (all incident families): `{physical['delayed_background_cps']:.12g}` cps.",
                f"- Atmospheric 511: `{physical['atm511_background_cps']:.12g}` cps.",
                f"- Total background: `{physical['background_cps']:.12g}` cps.",
                f"- Reference-flux signal: `{physical['signal_cps_at_reference_flux']:.12g}` cps.",
                f"- Positive transported delayed families: `{', '.join(positive) or 'none'}`.",
                f"- Finite-buildup zero-observation families: `{', '.join(zeros) or 'none'}`.",
                "",
                "The zero-observation label is not a physical-zero claim. Its central delayed",
                "estimate is zero and no fictitious transport exposure is assigned. The conditional",
                "componentwise transport-counting endpoint is not full 95% coverage and excludes",
                "buildup-yield, M-sampling, zero-family, and nuclide-mixture uncertainty.",
                "",
                "## Validation",
                "",
                f"- Unsmeared Step05 reproduction: `{payload['unsmeared_reproduction']['status']}`.",
                f"- Retained neutron/raw-SIM regression: `{payload['retained_neutron_regression']['status']}`.",
                f"- Response ensemble: `{payload['response_seed_ensemble']['status']}` across `{payload['response_seed_ensemble']['replicas']}` seeds.",
                f"- Independent response validator: `{payload['validation']['status']}`.",
                "- Final mission numbers are intentionally deferred to the family-by-nuclide 81-bin fold.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run(replicas: int, workers: int, rebuild_atm: bool) -> dict[str, Any]:
    if replicas != 64:
        raise ResponseError("the all8 response authority requires exactly --replicas 64")
    if workers < 1:
        raise ResponseError("--workers must be >= 1")
    upstream = upstream_audit()
    if upstream["status"] != "PASS_READY_FOR_S3D_O8_ALL8_RESPONSE":
        raise ResponseError(f"upstream gate={upstream['status']}: {upstream.get('problems') or upstream.get('missing')}")
    regression = run_regression()
    if regression["status"] != REGRESSION_PASS:
        raise ResponseError(
            "retained neutron regression must include at least one raw-SIM parse "
            "(--rebuild-cache on package-44 regression)"
        )
    detector = audit_detector_contract()
    closure = load_module("s3d_o8_all8_response_kernel", RETAINED_RESPONSE_CODE)
    selection, disk = load_selection()
    main_cat, lineage = compact_main(closure)
    atm_metadata = expected_atm_cache_metadata()
    atm_cat = build_atm(closure, rebuild_atm, atm_metadata)
    atm_provenance = atm_cache_audit(atm_metadata)
    components = read_json(COMPONENTS)
    base = read_json(STEP05)

    unsmeared_main = evaluate_catalog(
        main_cat, closure, selection, disk, None,
        apply_response=False, apply_threshold=False, lineage=lineage, include_lineage=False,
    )
    unsmeared_atm = evaluate_catalog(
        atm_cat, closure, selection, disk, None,
        apply_response=False, apply_threshold=False, lineage=None, include_lineage=False,
    )
    reproduction = validate_unsmeared(unsmeared_main, unsmeared_atm, base)

    global _WORKER_MAIN, _WORKER_LINEAGE, _WORKER_ATM, _WORKER_CLOSURE
    global _WORKER_SELECTION, _WORKER_DISK, _WORKER_COMPONENTS, _WORKER_STEP05
    _WORKER_MAIN = main_cat
    _WORKER_LINEAGE = lineage
    _WORKER_ATM = atm_cat
    _WORKER_CLOSURE = closure
    _WORKER_SELECTION = selection
    _WORKER_DISK = disk
    _WORKER_COMPONENTS = components
    _WORKER_STEP05 = base
    worker_count = min(workers, replicas)
    pool = None
    results = map(evaluate_worker, range(replicas))
    if worker_count > 1:
        pool = mp.get_context("fork").Pool(processes=worker_count)
        results = pool.imap(evaluate_worker, range(replicas), chunksize=1)
    rows: list[dict[str, Any]] = []
    primary: dict[str, Any] | None = None
    try:
        for completed, result in enumerate(results, start=1):
            rows.append(result["row"])
            primary = result.get("primary", primary)
            if completed % max(1, replicas // 8) == 0 or completed == replicas:
                print(f"[all8-response] completed {completed}/{replicas}", flush=True)
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    rows.sort(key=lambda row: int(row["replica_index"]))
    if primary is None:
        raise ResponseError("primary response realization was not returned")
    ensemble = ensemble_summary(rows, components)
    status = RESPONSE_PASS if ensemble["status"] == "PASS_RESPONSE_SEED_ENSEMBLE" else "FAIL_S3D_O8_ALL8_ENERGY_RESPONSE_CLOSURE"
    payload = {
        "status": status,
        "generated_at_utc": now_utc(),
        "claim": (
            "The 420 eV FWHM TES response is applied at pixel-readout level to the package-44 "
            "all-eight-family Step05 catalogue while retaining per-family delayed normalization and strong lineage."
        ),
        "upstream_gate": upstream,
        "retained_neutron_regression": regression,
        "detector_contract": detector,
        "atm_cache_provenance": atm_provenance,
        "input_authorities": {
            "campaign": rel(CAMPAIGN),
            "campaign_sha256": sha256(CAMPAIGN),
            "components": rel(COMPONENTS),
            "components_sha256": sha256(COMPONENTS),
            "event_catalog": rel(EVENT_CATALOG),
            "event_catalog_sha256": upstream["hashes"]["event_catalog"],
            "catalog_audit": rel(CATALOG_AUDIT),
            "catalog_audit_sha256": sha256(CATALOG_AUDIT),
            "step05": rel(STEP05),
            "step05_sha256": sha256(STEP05),
            "atm511_sim": rel(ATM_SIM),
            "atm511_sim_sha256": sha256(ATM_SIM),
            "atm511_summary": rel(ATM_SUMMARY),
            "atm511_summary_sha256": sha256(ATM_SUMMARY),
            "selection_implementation": rel(SELECTION_IMPLEMENTATION),
            "selection_implementation_sha256": sha256(SELECTION_IMPLEMENTATION),
            "response_kernel_implementation": rel(RETAINED_RESPONSE_CODE),
            "response_kernel_implementation_sha256": sha256(RETAINED_RESPONSE_CODE),
            "response_implementation": rel(Path(__file__)),
            "response_implementation_sha256": sha256(Path(__file__)),
            "response_validator": rel(VALIDATOR),
            "response_validator_sha256": sha256(VALIDATOR),
            "retained_mass_model_response_authority": rel(RETAINED_RESPONSE_SUMMARY),
            "retained_mass_model_response_authority_sha256": sha256(RETAINED_RESPONSE_SUMMARY),
        },
        "unsmeared_reproduction": reproduction,
        "primary_authority": primary,
        "response_seed_ensemble": ensemble,
        "outputs": {
            "summary": rel(SUMMARY),
            "replicas": rel(REPLICAS),
            "replicas_size_bytes": None,
            "replicas_sha256": None,
            "atm_cache": rel(ATM_CACHE),
            "validation": rel(VALIDATION),
        },
        "scope": {
            "new_monte_carlo_transport": False,
            "mission_fold_included": False,
            "finite_buildup_zero_family_uncertainty_in_conditional_transport_counting_endpoint": False,
            "zero_family_boundary": (
                "PASS_ZERO_PRODUCTION is a finite-buildup zero observation, not a physical-zero claim; "
                "the conditional endpoint excludes buildup-yield, M-sampling, zero-family, "
                "and nuclide-mixture uncertainty and is not a full 95% coverage statement"
            ),
            "next_required_authority": "family-by-nuclide 81-bin mission fold",
        },
    }
    write_csv(REPLICAS, rows)
    payload["outputs"]["replicas_size_bytes"] = REPLICAS.stat().st_size
    payload["outputs"]["replicas_sha256"] = sha256(REPLICAS)
    write_json(SUMMARY, payload)
    validator = load_module("s3d_o8_all8_response_independent_validator", VALIDATOR)
    validation = validator.validate()
    if validation.get("status") != VALIDATION_PASS:
        raise ResponseError(
            f"independent response validation failed: {validation.get('problems')}"
        )
    payload["validation"] = validation
    write_readme(payload)
    return payload


def preflight() -> dict[str, Any]:
    regression = run_regression()
    validator = load_module("s3d_o8_all8_response_validator_preflight", VALIDATOR)
    validator_self_test = validator.self_test()
    upstream = upstream_audit()
    status = (
        "PASS_READY_FOR_S3D_O8_ALL8_RESPONSE_POSTPROCESS"
        if upstream["status"] == "PASS_READY_FOR_S3D_O8_ALL8_RESPONSE" and regression["status"] == REGRESSION_PASS
        else "PENDING_S3D_O8_ALL8_RESPONSE_INPUTS"
        if upstream["status"].startswith("PENDING") or regression["status"].startswith("PENDING")
        else "FAIL_S3D_O8_ALL8_RESPONSE_PREFLIGHT"
    )
    payload = {
        "status": status,
        "generated_at_utc": now_utc(),
        "script": rel(Path(__file__)),
        "script_sha256": sha256(Path(__file__)),
        "upstream": upstream,
        "retained_neutron_regression": regression,
        "independent_validator_self_test": validator_self_test,
        "production_launched": False,
        "postprocess_confirmation": {"flag": "--allow-postprocess", "token": CONFIRM_TOKEN},
    }
    write_json(PREFLIGHT, payload)
    return payload


def validate_outputs() -> dict[str, Any]:
    validator = load_module("s3d_o8_all8_response_validator_cli", VALIDATOR)
    return validator.validate()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=("regression", "preflight", "run", "validate"),
        nargs="?",
        default="preflight",
    )
    parser.add_argument("--replicas", type=int, default=64)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--rebuild-atm-cache", action="store_true")
    parser.add_argument("--force-neutron-regression", action="store_true")
    parser.add_argument("--allow-postprocess", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    try:
        if args.stage == "regression":
            payload = run_regression(force_numeric=args.force_neutron_regression)
        elif args.stage == "preflight":
            payload = preflight()
        elif args.stage == "validate":
            payload = validate_outputs()
        else:
            if not args.allow_postprocess or args.confirm != CONFIRM_TOKEN:
                raise ResponseError(f"production postprocessing requires --allow-postprocess --confirm {CONFIRM_TOKEN}")
            payload = run(args.replicas, args.workers, args.rebuild_atm_cache)
        print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY) if args.stage == "run" else None}, indent=2))
        return 0 if str(payload["status"]).startswith(("PASS", "PENDING")) else 2
    except (ResponseError, OSError, ValueError, KeyError, EOFError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
