#!/usr/bin/env python3
"""Build the S3d-O8 all-eight-family, family-by-nuclide 81-bin mission fold.

Analysis-only: this runner contains no Cosima invocation.  It fails closed on
the upstream campaign/Step05/response status, exact family set, strong delayed
lineage, per-family 1/TE weights, O8 geometry, family inventory provenance, and
the exact-position mapping from a transported daughter back to its sampled
source-parent nuclide.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


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
STEP05 = P44 / "fullchain/step05/step05_s3d_o8_all8_activation_l1_response_summary.json"

RESPONSE_PACKAGE = ROOT / "engineering/ea_s3d_o8_all8_detector_response_closure_20260713"
RESPONSE = RESPONSE_PACKAGE / "data/s3d_o8_all8_energy_response_summary.json"
RESPONSE_REPLICAS = RESPONSE_PACKAGE / "data/s3d_o8_all8_energy_response_replicas.csv"
RESPONSE_VALIDATION = RESPONSE_PACKAGE / "data/s3d_o8_all8_energy_response_validation.json"
RESPONSE_CODE = RESPONSE_PACKAGE / "code/build_s3d_o8_all8_energy_response.py"

O8 = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "43_geoopt_s3d_o8_fallback_20260712"
)
O8_GEOMETRY = O8 / "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
BASE_STEP06 = O8 / "fullchain/step06/background_time_variation.csv"

RETAINED_MISSION_PACKAGE = ROOT / "engineering/ea_s3d_family_nuclide_mission_fold_20260713"
ALL8_SCALES = RETAINED_MISSION_PACKAGE / "data/live_parma_all8_scales_81bins.csv"
THREE_FAMILY_CURVE = (
    ROOT
    / "engineering/trajectory_transport_validation_20260709"
    / "11_analytic_agreement_20260709/claude_source_response_curve_by_time.csv"
)
TARGETED_AUDIT = (
    ROOT
    / "engineering/trajectory_transport_validation_20260709"
    / "11_analytic_agreement_20260709/analytic_agreement_summary.json"
)
RETAINED_NEUTRON_MISSION = RETAINED_MISSION_PACKAGE / "data/s3d_family_nuclide_mission_summary.json"

PREFLIGHT = DATA / "s3d_o8_all8_family_nuclide_mission_preflight.json"
REGRESSION = DATA / "s3d_o8_all8_only_n_generalized_mission_regression.json"
REGRESSION_CODE = PACKAGE / "code/validate_only_n_generalized_regression.py"
SELECTED = DATA / "s3d_o8_all8_selected_family_nuclides_primary_seed.json"
SUMMARY = DATA / "s3d_o8_all8_family_nuclide_mission_summary.json"
VALIDATION = DATA / "s3d_o8_all8_family_nuclide_mission_validation.json"
ACTIVITY_TIMELINE = OUTPUTS / "family_nuclide_activity_by_time.csv"
MISSION_TIMELINE = OUTPUTS / "w2_all8_family_nuclide_mission_timeline.csv"
README = PACKAGE / "README.md"

FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
FAMILY_SET = set(FAMILIES)
ZERO_STATUSES = {"PASS_ZERO_PRODUCTION", "PASS_ZERO_ACTIVITY"}
CAMPAIGN_PASS = "PASS_S3D_O8_ALL8_ACTIVATION_AND_FAMILY_DELAYED_TRANSPORT"
COMPONENT_PASS = "PASS_S3D_O8_ALL8_STEP05_DELAYED_COMPONENTS"
STEP05_PASS = "PASS_S3D_O8_ALL8_ACTIVATION_STEP05_DAY15"
RESPONSE_PASS = "PASS_S3D_O8_ALL8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE"
RESPONSE_VALIDATION_PASS = "PASS_S3D_O8_ALL8_ENERGY_RESPONSE_VALIDATION"
REGRESSION_PASS = "PASS_S3D_O8_ALL8_ONLY_N_GENERALIZED_MISSION_REGRESSION"
MISSION_PASS = "PASS_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_CLOSURE"
VALIDATION_PASS = "PASS_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_VALIDATION"

PRIMARY_SEED = 26_071_301
DAY15 = 15.0
SECONDS_PER_DAY = 86_400.0
COINCIDENCE_WINDOW_S = 1.0e-6
REFERENCE_FLUX = 1.0e-4
CONFIRM_TOKEN = "RUN_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_20260713"
SIM_POSITION_DECIMALS = 5
SOURCE_POSITION_MATCH_TOL_CM = 1.01e-5
SOURCE_POSITION_BUCKET_CM = 1.0e-4


class MissionError(RuntimeError):
    """An authority or numerical closure invariant failed."""


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


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MissionError(f"cannot import {rel(path)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str] | None = None) -> None:
    rows = list(rows)
    if not rows:
        raise MissionError(f"refusing to write empty CSV: {rel(path)}")
    if fields is None:
        fields = list(rows[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def require_close(
    actual: float,
    expected: float,
    label: str,
    *,
    atol: float = 1.0e-12,
    rtol: float = 1.0e-10,
) -> None:
    if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol):
        raise MissionError(f"{label}: {actual:.17g} != {expected:.17g}")


def exact_o8_geometry(value: str | None) -> bool:
    return bool(value) and resolve_path(str(value)).resolve() == O8_GEOMETRY.resolve()


def load_time_authorities() -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, Any]]:
    base = [row for row in read_csv(BASE_STEP06) if row["selection_id"] == "w2_510p58_511p42"]
    base.sort(key=lambda row: int(row["time_bin_id"]))
    scales = read_csv(ALL8_SCALES)
    scales.sort(key=lambda row: int(row["time_bin_id"]))
    if len(base) != 81 or len(scales) != 81:
        raise MissionError(f"time authority rows: Step06={len(base)}, all8={len(scales)}; expected 81/81")
    for base_row, scale_row in zip(base, scales):
        if int(base_row["time_bin_id"]) != int(scale_row["time_bin_id"]):
            raise MissionError("Step06 and all-eight PARMA time-bin IDs differ")
        require_close(float(base_row["day_mid"]), float(scale_row["day_mid"]), "trajectory day")
    day15 = next(index for index, row in enumerate(base) if math.isclose(float(row["day_mid"]), DAY15))
    for family in FAMILIES:
        require_close(float(scales[day15][f"scale_{family}"]), 1.0, f"day15 PARMA scale {family}")
    old_three = {int(row["time_bin_id"]): row for row in read_csv(THREE_FAMILY_CURVE)}
    max_delta = 0.0
    for row in scales:
        for family in ("eplus", "n", "gamma"):
            max_delta = max(
                max_delta,
                abs(float(row[f"scale_{family}"]) - float(old_three[int(row["time_bin_id"])][f"scale_{family}"])),
            )
    if max_delta > 5.0e-10:
        raise MissionError(f"all-eight PARMA curve parity delta={max_delta}")
    targeted = read_json(TARGETED_AUDIT)
    return base, scales, {
        "status": "PASS_ALL8_PARMA_81BIN_AND_RETAINED_THREE_FAMILY_PARITY",
        "bins": 81,
        "day15_index": day15,
        "max_abs_eplus_n_gamma_scale_delta": max_delta,
        "targeted_direct_transport_audit": rel(TARGETED_AUDIT),
        "targeted_direct_transport_status": targeted.get("status"),
    }


def upstream_audit() -> dict[str, Any]:
    required = [
        CAMPAIGN, COMPONENTS, STEP05, RESPONSE, RESPONSE_REPLICAS,
        RESPONSE_VALIDATION, RESPONSE_CODE, REGRESSION, REGRESSION_CODE,
        BASE_STEP06, ALL8_SCALES, THREE_FAMILY_CURVE, TARGETED_AUDIT,
    ]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        return {"status": "PENDING_S3D_O8_ALL8_MISSION_INPUTS", "missing": missing, "problems": []}
    campaign = read_json(CAMPAIGN)
    components = read_json(COMPONENTS)
    step05 = read_json(STEP05)
    response = read_json(RESPONSE)
    response_validation = read_json(RESPONSE_VALIDATION)
    regression = read_json(REGRESSION)
    problems: list[str] = []
    if campaign.get("status") != CAMPAIGN_PASS:
        problems.append(f"campaign status={campaign.get('status')}")
    if components.get("status") != COMPONENT_PASS:
        problems.append(f"components status={components.get('status')}")
    if step05.get("status") != STEP05_PASS:
        problems.append(f"Step05 status={step05.get('status')}")
    if response.get("status") != RESPONSE_PASS:
        problems.append(f"response status={response.get('status')}")
    if response_validation.get("status") != RESPONSE_VALIDATION_PASS:
        problems.append(f"response validation={response_validation.get('status')}")
    if response_validation.get("summary_sha256") != sha256(RESPONSE):
        problems.append("response validator does not bind the current response summary")
    if response_validation.get("replicas_sha256") != sha256(RESPONSE_REPLICAS):
        problems.append("response validator does not bind the current response replicas")
    if response_validation.get("validator_sha256") != sha256(
        RESPONSE_PACKAGE / "code/validate_s3d_o8_all8_energy_response.py"
    ):
        problems.append("response validator implementation hash is stale")
    if regression.get("status") != REGRESSION_PASS:
        problems.append(f"only-n generalized mission regression={regression.get('status')}")
    regression_inputs = regression.get("input_authorities") or {}
    regression_impl = regression_inputs.get("regression_implementation") or {}
    generalized_impl = regression_inputs.get("generalized_mission_implementation") or {}
    if regression_impl.get("sha256") != sha256(REGRESSION_CODE):
        problems.append("only-n regression implementation hash is stale")
    if generalized_impl.get("sha256") != sha256(Path(__file__)):
        problems.append("only-n regression does not bind current generalized mission implementation")
    if (response.get("unsmeared_reproduction") or {}).get("status") != "PASS_EXACT_ALL8_UNSMEARED_STEP05_REPRODUCTION":
        problems.append("response unsmeared reproduction is not PASS")
    if (response.get("retained_neutron_regression") or {}).get("status") != "PASS_S3D_O8_ALL8_RETAINED_NEUTRON_RESPONSE_REGRESSION":
        problems.append("response retained-neutron raw-SIM regression is not PASS")
    if not exact_o8_geometry(campaign.get("geometry_setup")):
        problems.append(f"campaign geometry={campaign.get('geometry_setup')}")
    response_gate = response.get("upstream_gate") or {}
    if response_gate.get("status") != "PASS_READY_FOR_S3D_O8_ALL8_RESPONSE":
        problems.append(f"response upstream gate={response_gate.get('status')}")
    authorities = response.get("input_authorities") or {}
    if authorities.get("campaign_sha256") != sha256(CAMPAIGN):
        problems.append("response does not bind current campaign")
    if authorities.get("components_sha256") != sha256(COMPONENTS):
        problems.append("response does not bind current components")
    if authorities.get("step05_sha256") != sha256(STEP05):
        problems.append("response does not bind current Step05")
    if authorities.get("response_implementation_sha256") != sha256(RESPONSE_CODE):
        problems.append("response summary does not bind its current implementation")
    implementation = authorities.get("response_implementation")
    if not implementation or resolve_path(implementation).resolve() != RESPONSE_CODE.resolve():
        problems.append("response summary points to a different implementation")
    kernel_value = authorities.get("response_kernel_implementation")
    kernel = resolve_path(kernel_value) if kernel_value else Path("/")
    if not kernel.is_file() or authorities.get("response_kernel_implementation_sha256") != sha256(kernel):
        problems.append("response summary does not bind its current response kernel")
    if int((response.get("primary_authority") or {}).get("step05", {}).get("response_seed") or -1) != PRIMARY_SEED:
        problems.append("response primary seed changed")
    ensemble = response.get("response_seed_ensemble") or {}
    if ensemble.get("status") != "PASS_RESPONSE_SEED_ENSEMBLE" or int(ensemble.get("replicas") or 0) != 64:
        problems.append(f"response ensemble={ensemble.get('status')}/{ensemble.get('replicas')}")
    rows = components.get("components") or []
    if len(rows) != 8 or {str(row.get("family")) for row in rows} != FAMILY_SET:
        problems.append("component family set is not exactly all eight")
    primary_step = (response.get("primary_authority") or {}).get("step05") or {}
    if primary_step.get("status") != "PASS_S3D_O8_ALL8_EVENT_LEVEL_420EV_FWHM_RESPONSE_STEP05":
        problems.append(f"primary response Step05 status={primary_step.get('status')}")
    w2 = (primary_step.get("windows") or {}).get("w2_510p58_511p42") or {}
    uncertainty = (w2.get("physical_reference_flux") or {}).get("uncertainty_95") or {}
    delayed = uncertainty.get("delayed_components_by_incident_family") or {}
    prompt = uncertainty.get("prompt_components") or []
    if set(delayed) != FAMILY_SET:
        problems.append(f"response delayed family set={sorted(delayed)}")
    if {str(row.get("tag")) for row in prompt} != FAMILY_SET:
        problems.append("response prompt family set is not all eight")
    occupancy = primary_step.get("occupancy_day15_by_family") or {}
    for stream in ("prompt", "delayed"):
        if set((occupancy.get(stream) or {})) != FAMILY_SET:
            problems.append(f"response {stream} occupancy family set is incomplete")
    selected = (
        (response.get("primary_authority") or {})
        .get("main", {})
        .get("windows", {})
        .get("w2_510p58_511p42", {})
        .get("selected_delayed_lineage", [])
    )
    strong = {
        (str(row.get("incident_family")), str(row.get("source_file")), int(row.get("local_id") or -1))
        for row in selected
    }
    if len(strong) != len(selected):
        problems.append("selected delayed strong-lineage keys are not unique")
    component_by_family = {str(row.get("family")): row for row in rows}
    selected_counts = Counter(str(row.get("incident_family")) for row in selected)
    for family in FAMILIES:
        component = component_by_family.get(family) or {}
        response_component = delayed.get(family) or {}
        if component.get("status") in ZERO_STATUSES:
            if selected_counts[family] or int(response_component.get("events") or 0):
                problems.append(f"finite-buildup zero family {family} has selected events")
            continue
        if component.get("status") != "PASS" or response_component.get("status") != "PASS":
            problems.append(f"positive family {family} lacks PASS response/component")
            continue
        if selected_counts[family] != int(response_component.get("events") or 0):
            problems.append(f"{family}: selected lineage count does not match response count")
        weight = float(component.get("event_weight_hz") or 0.0)
        if not math.isclose(weight, float(response_component.get("event_weight_cps") or 0.0), rel_tol=0.0, abs_tol=1.0e-18):
            problems.append(f"{family}: response/component event weight differs")
        expected_sim = resolve_path(component.get("sim", "/")).resolve()
        for row in selected:
            if row.get("incident_family") == family and resolve_path(row["source_file"]).resolve() != expected_sim:
                problems.append(f"{family}: selected lineage source differs from component SIM")
                break
    try:
        _base, _scales, time_audit = load_time_authorities()
    except (MissionError, OSError, KeyError, ValueError) as exc:
        problems.append(f"time authority: {exc}")
        time_audit = None
    return {
        "status": "PASS_READY_FOR_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION" if not problems else "FAIL_S3D_O8_ALL8_MISSION_UPSTREAM",
        "family_set": list(FAMILIES),
        "positive_families": components.get("positive_families"),
        "audited_zero_families": components.get("audited_zero_families"),
        "selected_delayed_events": len(selected),
        "time_authority": time_audit,
        "hashes": {
            "campaign": sha256(CAMPAIGN),
            "components": sha256(COMPONENTS),
            "step05": sha256(STEP05),
            "response": sha256(RESPONSE),
            "response_replicas": sha256(RESPONSE_REPLICAS),
            "response_validation": sha256(RESPONSE_VALIDATION),
            "only_n_regression": sha256(REGRESSION),
            "base_step06": sha256(BASE_STEP06),
            "all8_scales": sha256(ALL8_SCALES),
        },
        "problems": problems,
    }


def run_only_n_regression(*, force: bool = False) -> dict[str, Any]:
    module = load_module("s3d_o8_all8_only_n_mission_regression", REGRESSION_CODE)
    payload = module.run_regression(force=force)
    if payload.get("status") != REGRESSION_PASS:
        raise MissionError(f"only-n generalized mission regression={payload.get('status')}")
    return payload


def open_sim(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.suffix == ".gz" else path.open("r", encoding="utf-8", errors="replace")


def source_position_key(values: Iterable[float]) -> tuple[str, str, str]:
    position = tuple(float(value) for value in values)
    if len(position) != 3 or not all(math.isfinite(value) for value in position):
        raise MissionError(f"invalid source position={position}")
    return tuple(f"{value:.{SIM_POSITION_DECIMALS}f}" for value in position)  # type: ignore[return-value]


def source_position_bucket(values: Iterable[float]) -> tuple[int, int, int]:
    position = tuple(float(value) for value in values)
    if len(position) != 3 or not all(math.isfinite(value) for value in position):
        raise MissionError(f"invalid source position={position}")
    return tuple(  # type: ignore[return-value]
        math.floor(value / SOURCE_POSITION_BUCKET_CM) for value in position
    )


def scan_initial_state(sim: Path, event_ids: list[int]) -> dict[int, dict[str, Any]]:
    wanted = set(event_ids)
    if len(wanted) != len(event_ids):
        raise MissionError(f"duplicate selected local IDs within {rel(sim)}")
    if not wanted:
        return {}
    found: dict[int, dict[str, Any]] = {}
    current: int | None = None
    with open_sim(sim) as handle:
        for line in handle:
            if line.startswith("ID "):
                fields = line.split()
                current = int(fields[1]) if len(fields) >= 2 else None
                continue
            if current not in wanted or not line.startswith("IA INIT"):
                continue
            parts = [field.strip() for field in line[7:].split(";")]
            if len(parts) < 16:
                raise MissionError(f"malformed IA INIT for {rel(sim)} event {current}")
            state = {
                "sim_initial_ZA": int(parts[15]),
                "sim_initial_position_cm": [
                    float(parts[4]),
                    float(parts[5]),
                    float(parts[6]),
                ],
            }
            state["sim_initial_position_key"] = list(
                source_position_key(state["sim_initial_position_cm"])
            )
            if current in found and found[current] != state:
                raise MissionError(
                    f"multiple IA INIT states for {rel(sim)} event {current}"
                )
            found[current] = state
            if len(found) == len(wanted):
                break
    missing = sorted(wanted.difference(found))
    if missing:
        raise MissionError(f"missing IA INIT ZA in {rel(sim)} for {len(missing)} selected events")
    return found


def scan_initial_za(sim: Path, event_ids: list[int]) -> dict[int, int]:
    """Compatibility view used by the retained only-n numerical regression."""
    return {
        local_id: int(state["sim_initial_ZA"])
        for local_id, state in scan_initial_state(sim, event_ids).items()
    }


def verify_artifact_record(record: Any, label: str) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise MissionError(f"{label}: artifact record is absent")
    path_value = record.get("path")
    if not path_value:
        raise MissionError(f"{label}: artifact path is absent")
    path = resolve_path(path_value)
    if not path.is_file():
        raise MissionError(f"{label}: artifact is missing: {rel(path)}")
    current = {
        "path": rel(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }
    if int(record.get("size_bytes") or -1) != current["size_bytes"]:
        raise MissionError(f"{label}: artifact size is stale")
    if record.get("sha256") != current["sha256"]:
        raise MissionError(f"{label}: artifact hash is stale")
    return current


def load_source_parent_index(
    component: dict[str, Any],
) -> tuple[dict[tuple[int, int, int], list[dict[str, Any]]], dict[str, Any]]:
    """Load the exact-position table that binds a SIM IA INIT position to its source parent.

    Cosima can begin a delayed trigger at a daughter produced by the sampled
    radioactive source.  The IA INIT ZA is therefore retained as transport
    evidence, but mission-time scaling must use the sampled parent inventory.
    The exact-position weighted table is the auditable parent authority.
    """
    family = str(component["family"])
    source_provenance = component.get("source_provenance") or {}
    weighted_record = verify_artifact_record(
        source_provenance.get("weighted_table"),
        f"{family} source_provenance/weighted_table",
    )
    weighted_path = resolve_path(weighted_record["path"])
    index: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    exact_positions: set[tuple[float, float, float]] = set()
    rows = 0
    for row_number, row in enumerate(read_csv(weighted_path), start=2):
        position = [float(row[axis]) for axis in ("x_cm", "y_cm", "z_cm")]
        exact_position = tuple(position)
        if exact_position in exact_positions:
            raise MissionError(
                f"{family}: duplicate exact weighted-table position={exact_position}"
            )
        exact_positions.add(exact_position)
        source_za = int(row["ZA"])
        if source_za <= 0:
            raise MissionError(
                f"{family}: weighted-table row {row_number} has invalid ZA={source_za}"
            )
        record = {
            "source_parent_ZA": source_za,
            "source_parent_position_cm": position,
            "source_parent_position_key": list(source_position_key(position)),
            "source_parent_volume": row["VN"],
            "weighted_table_row": row_number,
        }
        index[source_position_bucket(position)].append(record)
        rows += 1
    if not index:
        raise MissionError(f"{family}: exact-position weighted table is empty")
    return index, {
        "status": "PASS_TOLERANCE_BOUNDED_UNIQUE_EXACT_POSITION_SOURCE_PARENT_INDEX",
        "family": family,
        "weighted_table": weighted_record["path"],
        "weighted_table_size_bytes": weighted_record["size_bytes"],
        "weighted_table_sha256": weighted_record["sha256"],
        "position_decimals": SIM_POSITION_DECIMALS,
        "position_match_tolerance_cm_per_axis": SOURCE_POSITION_MATCH_TOL_CM,
        "position_bucket_cm": SOURCE_POSITION_BUCKET_CM,
        "rows": rows,
        "unique_positions": len(exact_positions),
    }


def match_source_parent(
    index: dict[tuple[int, int, int], list[dict[str, Any]]],
    position: Iterable[float],
    *,
    family: str,
    local_id: int,
) -> dict[str, Any]:
    observed = tuple(float(value) for value in position)
    center = source_position_bucket(observed)
    matches: list[tuple[dict[str, Any], list[float]]] = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for record in index.get(
                    (center[0] + dx, center[1] + dy, center[2] + dz), []
                ):
                    delta = [
                        abs(observed[axis] - float(record["source_parent_position_cm"][axis]))
                        for axis in range(3)
                    ]
                    if all(value <= SOURCE_POSITION_MATCH_TOL_CM for value in delta):
                        matches.append((record, delta))
    if len(matches) != 1:
        raise MissionError(
            f"selected {family}/local_id={local_id} IA INIT position={observed} "
            f"has {len(matches)} exact-source parent matches within "
            f"{SOURCE_POSITION_MATCH_TOL_CM} cm per axis"
        )
    record, delta = matches[0]
    return {
        **record,
        "source_parent_position_abs_delta_cm": delta,
        "source_parent_position_max_abs_delta_cm": max(delta),
        "source_parent_position_match_tolerance_cm_per_axis": SOURCE_POSITION_MATCH_TOL_CM,
    }


def load_family_inventory(component: dict[str, Any]) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    family = str(component["family"])
    summary_path = resolve_path(component["fixed_summary"])
    if not summary_path.is_file():
        raise MissionError(f"{family}: fixed-source summary is missing")
    current_summary = {
        "path": rel(summary_path),
        "size_bytes": summary_path.stat().st_size,
        "sha256": sha256(summary_path),
    }
    if component.get("fixed_summary_sha256") != current_summary["sha256"]:
        raise MissionError(f"{family}: fixed-summary hash is stale")
    source_provenance = component.get("source_provenance") or {}
    if not isinstance(source_provenance, dict):
        raise MissionError(f"{family}: source_provenance is absent")
    provenance_summary = verify_artifact_record(
        source_provenance.get("fixed_summary"),
        f"{family} source_provenance/fixed_summary",
    )
    if provenance_summary != current_summary:
        raise MissionError(f"{family}: fixed summary differs from source_provenance")
    artifact_audits: dict[str, dict[str, Any]] = {}
    for name in ("fixed_source", "groundstate_corrections", "inventory"):
        top = verify_artifact_record(component.get(name), f"{family} top-level/{name}")
        provenance = verify_artifact_record(
            source_provenance.get(name), f"{family} source_provenance/{name}"
        )
        if top != provenance:
            raise MissionError(f"{family}: top-level {name} differs from source_provenance")
        artifact_audits[name] = top
    summary = read_json(summary_path)
    correction_value = summary.get("corrections_csv")
    correction = resolve_path(correction_value) if correction_value else summary_path.parent / "groundstate_activity_corrections.csv"
    if not correction.is_file():
        raise MissionError(f"{family}: ground-state correction CSV is missing")
    if correction.resolve() != resolve_path(artifact_audits["groundstate_corrections"]["path"]).resolve():
        raise MissionError(f"{family}: fixed summary points to a different correction CSV")
    if not exact_o8_geometry(summary.get("geometry")):
        raise MissionError(f"{family}: fixed-source geometry={summary.get('geometry')}")
    norm = summary.get("normalization") or {}
    if set(norm) != {family}:
        raise MissionError(f"{family}: fixed-source normalization family set={sorted(norm)}")
    expected_division = 12.0 if family == "gamma" else 8.0
    for key in ("files", "division", "tt_count", "tt_files", "tt_line_count"):
        require_close(float(norm[family][key]), expected_division, f"{family} normalization {key}", atol=0.0, rtol=0.0)
    inventory: dict[int, dict[str, Any]] = {}
    for row in read_csv(correction):
        activity = float(row["new_groundstate_activity_Bq"])
        if activity <= 0.0:
            continue
        half_life = float(row["nubase_half_life_s"])
        if not math.isfinite(half_life) or half_life <= 0.0:
            raise MissionError(f"{family}/{row['ZA']}: invalid NUBASE half-life={half_life}")
        za = int(row["ZA"])
        record = inventory.setdefault(za, {
            "incident_family": family,
            "ZA": za,
            "nuclide": row["nuclide"],
            "half_life_s": half_life,
            "day15_activity_Bq": 0.0,
            "volume_rows": 0,
        })
        if record["nuclide"] != row["nuclide"]:
            raise MissionError(f"{family}/ZA={za}: inconsistent nuclide names")
        require_close(float(record["half_life_s"]), half_life, f"{family}/ZA={za} half-life")
        record["day15_activity_Bq"] += activity
        record["volume_rows"] += 1
    total = sum(float(row["day15_activity_Bq"]) for row in inventory.values())
    require_close(total, float(component["activity_Bq"]), f"{family} inventory total", atol=max(1.0e-9, total * 1.0e-8))
    require_close(total, float(summary["new_total_activity_Bq"]), f"{family} source-summary total", atol=max(1.0e-9, total * 1.0e-8))
    return inventory, {
        "status": "PASS_FAMILY_NUBASE_GROUNDSTATE_INVENTORY",
        "family": family,
        "fixed_summary": rel(summary_path),
        "fixed_summary_size_bytes": summary_path.stat().st_size,
        "fixed_summary_sha256": current_summary["sha256"],
        "fixed_source": artifact_audits["fixed_source"],
        "groundstate_corrections": rel(correction),
        "groundstate_corrections_sha256": sha256(correction),
        "groundstate_corrections_artifact": artifact_audits["groundstate_corrections"],
        "inventory_artifact": artifact_audits["inventory"],
        "source_provenance_verified": True,
        "nuclides": len(inventory),
        "day15_activity_Bq": total,
        "division": expected_division,
        "tt_count": int(norm[family]["tt_count"]),
    }


def build_selected_authority(
    response: dict[str, Any],
    components: dict[str, Any],
    inventories: dict[str, dict[int, dict[str, Any]]],
) -> tuple[dict[str, Any], dict[tuple[str, int], int]]:
    records = response["primary_authority"]["main"]["windows"]["w2_510p58_511p42"]["selected_delayed_lineage"]
    component_by_family = {row["family"]: row for row in components["components"]}
    selected_counts: dict[tuple[str, int], int] = defaultdict(int)
    lineage_rows: list[dict[str, Any]] = []
    family_audits: list[dict[str, Any]] = []
    for family in FAMILIES:
        component = component_by_family[family]
        family_rows = [row for row in records if row["incident_family"] == family]
        if component["status"] in ZERO_STATUSES:
            if family_rows:
                raise MissionError(f"finite-buildup zero family {family} has selected lineages")
            family_audits.append({"family": family, "status": component["status"], "selected_events": 0})
            continue
        sim = resolve_path(component["sim"])
        if not sim.is_file():
            raise MissionError(f"{family}: delayed SIM is missing before IA INIT scan")
        sim_record = {
            "path": rel(sim),
            "size_bytes": sim.stat().st_size,
            "sha256": sha256(sim),
        }
        if int(component.get("sim_size_bytes") or -1) != sim_record["size_bytes"]:
            raise MissionError(f"{family}: component delayed-SIM size is stale")
        if component.get("sim_sha256") != sim_record["sha256"]:
            raise MissionError(f"{family}: component delayed-SIM hash is stale")
        transport = component.get("transport_provenance") or {}
        if int(transport.get("size_bytes") or -1) != sim_record["size_bytes"] or transport.get("sha256") != sim_record["sha256"]:
            raise MissionError(f"{family}: transport_provenance does not bind current delayed SIM")
        for row in family_rows:
            if resolve_path(row["source_file"]).resolve() != sim.resolve():
                raise MissionError(f"{family}: selected lineage points to a different delayed SIM")
        ids = [int(row["local_id"]) for row in family_rows]
        source_parent_index, source_parent_audit = load_source_parent_index(component)
        # Only after the size/hash/source lineage checks may the large SIM be
        # opened and IA INIT records consumed.  IA INIT can be a daughter;
        # its exact position binds it back to the sampled source-parent table.
        state_by_id = scan_initial_state(sim, ids)
        daughter_or_chain_events = 0
        source_parent_nuclides: set[int] = set()
        sim_initial_nuclides: set[int] = set()
        for row in family_rows:
            local_id = int(row["local_id"])
            state = state_by_id[local_id]
            source_parent = match_source_parent(
                source_parent_index,
                state["sim_initial_position_cm"],
                family=family,
                local_id=local_id,
            )
            source_za = int(source_parent["source_parent_ZA"])
            sim_initial_za = int(state["sim_initial_ZA"])
            if source_za not in inventories[family]:
                raise MissionError(
                    f"selected {family}/source-parent ZA={source_za} is absent from "
                    "its ground-state inventory"
                )
            selected_counts[(family, source_za)] += 1
            source_parent_nuclides.add(source_za)
            sim_initial_nuclides.add(sim_initial_za)
            daughter_or_chain_events += int(source_za != sim_initial_za)
            lineage_rows.append({
                **row,
                # Backward-compatible literal IA INIT field plus explicit names.
                "initial_ZA": sim_initial_za,
                "sim_initial_ZA": sim_initial_za,
                "sim_initial_position_cm": state["sim_initial_position_cm"],
                "sim_initial_position_key": state["sim_initial_position_key"],
                **source_parent,
                "source_parent_nuclide": inventories[family][source_za]["nuclide"],
                "source_parent_assignment": (
                    "TOLERANCE_BOUNDED_UNIQUE_EXACT_POSITION_WEIGHTED_TABLE_MATCH"
                ),
                "sim_initial_is_source_parent": sim_initial_za == source_za,
            })
        weight = float(component["event_weight_hz"])
        expected = response["primary_authority"]["step05"]["windows"]["w2_510p58_511p42"]["physical_reference_flux"]["uncertainty_95"]["delayed_components_by_incident_family"][family]
        if len(ids) != int(expected["events"]):
            raise MissionError(f"{family}: selected-lineage count differs from response")
        require_close(len(ids) * weight, float(expected["rate_cps"]), f"{family} selected rate", atol=1.0e-15)
        family_audits.append({
            "family": family,
            "status": "PASS",
            "sim": rel(sim),
            "sim_size_bytes": sim_record["size_bytes"],
            "sim_sha256": sim_record["sha256"],
            "transport_provenance_verified": True,
            "selected_events": len(ids),
            "event_weight_cps": weight,
            "selected_rate_cps": len(ids) * weight,
            "selected_nuclides": len(source_parent_nuclides),
            "selected_source_parent_nuclides": len(source_parent_nuclides),
            "selected_sim_initial_nuclides": len(sim_initial_nuclides),
            "daughter_or_chain_events": daughter_or_chain_events,
            "source_parent_index": source_parent_audit,
        })
    by_nuclide = [
        {
            "incident_family": family,
            "ZA": za,
            "nuclide": inventories[family][za]["nuclide"],
            "selected_events": count,
            "event_weight_cps": float(component_by_family[family]["event_weight_hz"]),
            "day15_selected_rate_cps": count * float(component_by_family[family]["event_weight_hz"]),
        }
        for (family, za), count in sorted(selected_counts.items())
    ]
    payload = {
        "status": "PASS_S3D_O8_ALL8_PRIMARY_SEED_FAMILY_NUCLIDE_LINEAGE",
        "generated_at_utc": now_utc(),
        "response_seed": PRIMARY_SEED,
        "response_authority": rel(RESPONSE),
        "response_authority_sha256": sha256(RESPONSE),
        "component_authority": rel(COMPONENTS),
        "component_authority_sha256": sha256(COMPONENTS),
        "strong_lineage_key": ["incident_family", "source_file", "local_id"],
        "nuclide_assignment_contract": (
            "SIM IA INIT ZA is retained as transport/daughter evidence; the unique "
            "IA INIT position match in the provenance-bound exact-position weighted "
            "table supplies the sampled source-parent ZA used for inventory and "
            "mission-time scaling"
        ),
        "selected_events": len(lineage_rows),
        "family_audits": family_audits,
        "by_family_nuclide": by_nuclide,
        "lineage": sorted(lineage_rows, key=lambda row: (FAMILIES.index(row["incident_family"]), int(row["local_id"]))),
    }
    write_json(SELECTED, payload)
    return payload, dict(selected_counts)


def one_minus_exp_neg(value: float) -> float:
    """Stable evaluation of 1-exp(-value), including long-lived nuclides."""
    if value < 0.0 or not math.isfinite(value):
        raise MissionError(f"invalid nonnegative exponential argument={value}")
    return -math.expm1(-value)


def advance_inventory_number(number: float, production: float, lam: float, dt_s: float) -> float:
    if lam <= 0.0 or dt_s < 0.0:
        raise MissionError(f"invalid inventory advance lambda/dt={lam}/{dt_s}")
    return number * math.exp(-lam * dt_s) + (production / lam) * one_minus_exp_neg(lam * dt_s)


def long_life_integrator_regression() -> dict[str, Any]:
    half_life_s = 1.0e30
    lam = math.log(2.0) / half_life_s
    dt_s = 0.5 * SECONDS_PER_DAY
    x = lam * dt_s
    stable = one_minus_exp_neg(x)
    series = x - 0.5 * x * x
    naive = 1.0 - math.exp(-x)
    require_close(stable, series, "long-life expm1 series", atol=0.0, rtol=1.0e-15)
    production = 2.0
    advanced = advance_inventory_number(0.0, production, lam, dt_s)
    require_close(advanced, production * dt_s, "long-life inventory production", atol=1.0e-10, rtol=1.0e-15)
    if stable <= 0.0 or advanced <= 0.0 or naive != 0.0:
        raise MissionError("long-life expm1 regression did not exercise naive cancellation")
    return {
        "status": "PASS_LONG_LIFE_EXPM1_INVENTORY_REGRESSION",
        "half_life_s": half_life_s,
        "dt_s": dt_s,
        "lambda_dt": x,
        "stable_one_minus_exp_neg": stable,
        "naive_one_minus_exp_neg": naive,
        "stable_inventory_number": advanced,
        "expected_no_decay_inventory_number": production * dt_s,
    }


def integrate_activities(
    base: list[dict[str, str]],
    scales: list[dict[str, str]],
    inventories: dict[str, dict[int, dict[str, Any]]],
    selected_counts: dict[tuple[str, int], int],
    component_by_family: dict[str, dict[str, Any]],
) -> tuple[dict[tuple[str, int], list[float]], list[dict[str, Any]], dict[str, Any]]:
    day15_index = next(index for index, row in enumerate(base) if math.isclose(float(row["day_mid"]), DAY15))
    curves: dict[tuple[str, int], list[float]] = {}
    output: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    for family in FAMILIES:
        if component_by_family[family]["status"] in ZERO_STATUSES:
            audits.append({"family": family, "status": component_by_family[family]["status"], "nuclides": 0, "day15_activity_Bq": 0.0})
            continue
        family_inventory = inventories[family]
        driver = [float(row[f"scale_{family}"]) for row in scales]
        family_total = 0.0
        for za, item in sorted(family_inventory.items()):
            activity_ref = float(item["day15_activity_Bq"])
            half_life = float(item["half_life_s"])
            lam = math.log(2.0) / half_life
            build_factor = one_minus_exp_neg(lam * DAY15 * SECONDS_PER_DAY)
            production_ref = activity_ref / max(build_factor, 1.0e-300)
            number = 0.0
            raw: list[float] = []
            for index, row in enumerate(base):
                dt_s = float(row["dt_s"])
                production = production_ref * driver[index]
                half = 0.5 * dt_s
                midpoint_number = advance_inventory_number(number, production, lam, half)
                raw.append(lam * midpoint_number)
                number = advance_inventory_number(number, production, lam, dt_s)
            anchor = raw[day15_index]
            if anchor <= 0.0:
                raise MissionError(f"{family}/ZA={za}: non-positive day15 integration anchor")
            curve = [value * activity_ref / anchor for value in raw]
            curves[(family, za)] = curve
            count = selected_counts.get((family, za), 0)
            weight = float(component_by_family[family]["event_weight_hz"])
            epsilon = count * weight / activity_ref
            for index, value in enumerate(curve):
                output.append({
                    "time_bin_id": int(base[index]["time_bin_id"]),
                    "day_mid": float(base[index]["day_mid"]),
                    "incident_family": family,
                    "ZA": za,
                    "nuclide": item["nuclide"],
                    "half_life_s": half_life,
                    "day15_activity_Bq": activity_ref,
                    "activity_Bq": value,
                    "activity_scale_to_day15": value / activity_ref,
                    "selected_events_day15": count,
                    "event_weight_cps": weight,
                    "selection_response_cps_per_Bq": epsilon,
                    "selected_rate_cps": value * epsilon,
                })
            family_total += curve[day15_index]
        require_close(family_total, float(component_by_family[family]["activity_Bq"]), f"{family} integrated day15 activity", atol=max(1.0e-9, family_total * 1.0e-8))
        audits.append({
            "family": family,
            "status": "PASS_FAMILY_NUCLIDE_ACTIVITY_DRIVER",
            "driver": f"live-PARMA scale_{family}",
            "nuclides": len(family_inventory),
            "day15_activity_Bq": family_total,
            "selected_nuclides": sum(1 for za in family_inventory if selected_counts.get((family, za), 0) > 0),
        })
    return curves, output, {
        "status": "PASS_ALL8_FAMILY_BY_NUCLIDE_ACTIVITY_INTEGRATION",
        "long_life_integrator_regression": long_life_integrator_regression(),
        "day15_anchor": "each family/nuclide curve is anchored to its NUBASE-corrected day-15 inventory",
        "families": audits,
    }


def crossing(days: list[float], values: list[float], threshold: float) -> float | None:
    for index, value in enumerate(values):
        if value < threshold:
            continue
        if index == 0:
            return days[0]
        x0, x1 = days[index - 1], days[index]
        y0, y1 = values[index - 1], values[index]
        return x1 if y1 == y0 else x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def time_or_extrapolate(days: list[float], values: list[float], threshold: float) -> float:
    value = crossing(days, values, threshold)
    return value if value is not None else days[-1] * (threshold / values[-1]) ** 2


def mission_fold(
    response: dict[str, Any],
    base: list[dict[str, str]],
    scales: list[dict[str, str]],
    curves: dict[tuple[str, int], list[float]],
    inventories: dict[str, dict[int, dict[str, Any]]],
    selected_counts: dict[tuple[str, int], int],
    component_by_family: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    primary = response["primary_authority"]["step05"]
    physical = primary["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
    uncertainty = physical["uncertainty_95"]
    prompt_components = {row["tag"]: row for row in uncertainty["prompt_components"]}
    delayed_components = uncertainty["delayed_components_by_incident_family"]
    if set(prompt_components) != FAMILY_SET or set(delayed_components) != FAMILY_SET:
        raise MissionError("response component family set changed")
    occupancy = primary["occupancy_day15_by_family"]
    day15_index = next(index for index, row in enumerate(base) if math.isclose(float(row["day_mid"]), DAY15))

    family_activity: dict[str, list[float]] = {}
    family_selected_rate: dict[str, list[float]] = {}
    for family in FAMILIES:
        if component_by_family[family]["status"] in ZERO_STATUSES:
            family_activity[family] = [0.0] * len(base)
            family_selected_rate[family] = [0.0] * len(base)
            continue
        activity_curve = [sum(curves[(family, za)][index] for za in inventories[family]) for index in range(len(base))]
        rate_curve = []
        for index in range(len(base)):
            rate = 0.0
            for za, item in inventories[family].items():
                count = selected_counts.get((family, za), 0)
                if count:
                    epsilon = count * float(component_by_family[family]["event_weight_hz"]) / float(item["day15_activity_Bq"])
                    rate += curves[(family, za)][index] * epsilon
            rate_curve.append(rate)
        family_activity[family] = activity_curve
        family_selected_rate[family] = rate_curve
        require_close(activity_curve[day15_index], float(component_by_family[family]["activity_Bq"]), f"{family} activity day15")
        require_close(rate_curve[day15_index], float(delayed_components[family]["rate_cps"]), f"{family} selected rate day15", atol=1.0e-15)

    prompt_day15 = float(physical["prompt_background_cps"])
    delayed_day15 = float(physical["delayed_background_cps"])
    atm_day15 = float(physical["atm511_background_cps"])
    signal_day15 = float(physical["signal_cps_at_reference_flux"])
    atm_upper_day15 = float(uncertainty["atm511_background_upper95_cps"])
    signal_lower_day15 = float(uncertainty["signal_cps_lower95_at_reference_flux"])
    require_close(delayed_day15, sum(family_selected_rate[family][day15_index] for family in FAMILIES), "all-family delayed day15")

    base_day15 = base[day15_index]
    atm_occ_day15 = float(primary["occupancy_day15"]["atm511_sidecar"]["rate_hz"])
    cumulative_signal = cumulative_background = 0.0
    cumulative_signal_lower = cumulative_background_upper = 0.0
    elapsed_s = 0.0
    days: list[float] = []
    central_z: list[float] = []
    conditional_endpoint_z: list[float] = []
    timeline: list[dict[str, Any]] = []
    for index, base_row in enumerate(base):
        family_scale = {family: float(scales[index][f"scale_{family}"]) for family in FAMILIES}
        prompt_rate = sum(float(prompt_components[family]["rate_cps"]) * family_scale[family] for family in FAMILIES)
        prompt_upper = sum(float(prompt_components[family]["rate_upper95_cps"]) * family_scale[family] for family in FAMILIES)
        prompt_occ = sum(float(occupancy["prompt"][family]["rate_hz"]) * family_scale[family] for family in FAMILIES)
        delayed_rate_by_family = {family: family_selected_rate[family][index] for family in FAMILIES}
        delayed_rate = sum(delayed_rate_by_family.values())
        delayed_upper_by_family: dict[str, float] = {}
        delayed_occ = 0.0
        for family in FAMILIES:
            component = component_by_family[family]
            if component["status"] in ZERO_STATUSES:
                delayed_upper_by_family[family] = 0.0
                continue
            activity_scale = family_activity[family][index] / family_activity[family][day15_index]
            selected_day15 = family_selected_rate[family][day15_index]
            response_scale = family_selected_rate[family][index] / selected_day15 if selected_day15 > 0.0 else activity_scale
            delayed_upper_by_family[family] = float(delayed_components[family]["rate_upper95_cps"]) * response_scale
            delayed_occ += float(occupancy["delayed"][family]["rate_hz"]) * activity_scale
        delayed_upper = sum(delayed_upper_by_family.values())
        atm_scale = float(base_row["atm511_phi_4pi_scale_to_day15"])
        science_scale = float(base_row["science_atm_scale_to_day15"])
        atm_rate = atm_day15 * atm_scale
        atm_upper = atm_upper_day15 * atm_scale
        signal_rate = signal_day15 * science_scale
        signal_lower = signal_lower_day15 * science_scale
        atm_occ = atm_occ_day15 * float(base_row["atm511_event_rate_hz"]) / float(base_day15["atm511_event_rate_hz"])
        total_occ = prompt_occ + delayed_occ + atm_occ
        live = math.exp(-total_occ * COINCIDENCE_WINDOW_S)
        background = prompt_rate + delayed_rate + atm_rate
        background_upper = prompt_upper + delayed_upper + atm_upper
        dt_s = float(base_row["dt_s"])
        cumulative_signal += signal_rate * live * dt_s
        cumulative_background += background * live * dt_s
        cumulative_signal_lower += signal_lower * live * dt_s
        cumulative_background_upper += background_upper * live * dt_s
        elapsed_s += dt_s
        day = elapsed_s / SECONDS_PER_DAY
        z = cumulative_signal / math.sqrt(cumulative_background)
        z_cons = cumulative_signal_lower / math.sqrt(cumulative_background_upper)
        days.append(day)
        central_z.append(z)
        conditional_endpoint_z.append(z_cons)
        row: dict[str, Any] = {
            "time_bin_id": int(base_row["time_bin_id"]),
            "day_mid": float(base_row["day_mid"]),
            "elapsed_stop_day": day,
            "dt_s": dt_s,
            "prompt_event_rate_hz": prompt_occ,
            "delayed_event_rate_hz": delayed_occ,
            "atm511_event_rate_hz": atm_occ,
            "coincidence_occupancy_rate_hz": total_occ,
            "accidental_live_factor": live,
            "prompt_final_cps_noacc": prompt_rate,
            "delayed_final_cps_noacc": delayed_rate,
            "atm511_final_cps_noacc": atm_rate,
            "background_final_cps_noacc": background,
            "signal_final_cps_noacc": signal_rate,
            "prompt_final_upper95_cps_noacc": prompt_upper,
            "delayed_final_upper95_cps_noacc": delayed_upper,
            "atm511_final_upper95_cps_noacc": atm_upper,
            "background_final_componentwise_transport_counting_endpoint_cps_noacc": background_upper,
            "signal_final_lower95_cps_noacc": signal_lower,
            "cumulative_source_counts": cumulative_signal,
            "cumulative_background_counts": cumulative_background,
            "cumulative_source_transport_counting_lower_endpoint_counts": cumulative_signal_lower,
            "cumulative_background_componentwise_transport_counting_upper_endpoint_counts": cumulative_background_upper,
            "counting_Z": z,
            "counting_Z_componentwise_transport_counting_endpoint_conditional": z_cons,
        }
        for family in FAMILIES:
            row[f"prompt_scale_{family}"] = family_scale[family]
            row[f"delayed_{family}_activity_Bq"] = family_activity[family][index]
            row[f"delayed_{family}_selected_cps"] = delayed_rate_by_family[family]
            row[f"delayed_{family}_upper95_cps"] = delayed_upper_by_family[family]
        timeline.append(row)

    day15_row = timeline[day15_index]
    require_close(float(day15_row["prompt_final_cps_noacc"]), prompt_day15, "mission prompt day15")
    require_close(float(day15_row["delayed_final_cps_noacc"]), delayed_day15, "mission delayed day15")
    require_close(float(day15_row["atm511_final_cps_noacc"]), atm_day15, "mission atm day15")
    require_close(float(day15_row["signal_final_cps_noacc"]), signal_day15, "mission signal day15")
    z20 = central_z[-1]
    z20_cons = conditional_endpoint_z[-1]
    summary = {
        "status": "PASS_S3D_O8_ALL8_W2_FAMILY_NUCLIDE_MISSION_FOLD",
        "reference_flux_ph_cm2_s": REFERENCE_FLUX,
        "day15_selected_rates_cps": {
            "prompt": prompt_day15,
            "delayed": delayed_day15,
            "delayed_by_incident_family": {family: family_selected_rate[family][day15_index] for family in FAMILIES},
            "atm511": atm_day15,
            "background": prompt_day15 + delayed_day15 + atm_day15,
            "signal": signal_day15,
            "background_componentwise_transport_counting_endpoint_cps": float(
                day15_row["background_final_componentwise_transport_counting_endpoint_cps_noacc"]
            ),
            "signal_transport_counting_lower_endpoint_cps": signal_lower_day15,
        },
        "source_counts_20d": cumulative_signal,
        "background_counts_20d": cumulative_background,
        "source_transport_counting_lower_endpoint_counts_20d": cumulative_signal_lower,
        "background_componentwise_transport_counting_upper_endpoint_counts_20d": cumulative_background_upper,
        "Z20d": z20,
        "Z20d_componentwise_transport_counting_endpoint_conditional": z20_cons,
        "flux_3sigma_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / z20,
        "flux_3sigma_20d_componentwise_transport_counting_endpoint_conditional_ph_cm2_s": REFERENCE_FLUX * 3.0 / z20_cons,
        "T3_day": time_or_extrapolate(days, central_z, 3.0),
        "T5_day": time_or_extrapolate(days, central_z, 5.0),
        "T3_day_componentwise_transport_counting_endpoint_conditional": time_or_extrapolate(days, conditional_endpoint_z, 3.0),
        "T5_day_componentwise_transport_counting_endpoint_conditional": time_or_extrapolate(days, conditional_endpoint_z, 5.0),
        "accidental_loss_min": min(1.0 - float(row["accidental_live_factor"]) for row in timeline),
        "accidental_loss_max": max(1.0 - float(row["accidental_live_factor"]) for row in timeline),
        "model": {
            "prompt": "sum of eight response-selected day15 family rates times matching live-PARMA family scales",
            "delayed_central": "sum over incident family and exact-source parent nuclide of activity times the same family/nuclide selected response",
            "delayed_finite_count": (
                "componentwise (not joint-coverage) sum of transported-family Garwood upper counts times that family's 1/TE; "
                "the selected family/nuclide response curve supplies the time scale, with total family activity used when that "
                "positive transported family has zero selected W2 events"
            ),
            "conditional_componentwise_transport_counting_endpoint": (
                "This endpoint combines componentwise transported-count Garwood upper endpoints and a focused-signal "
                "Clopper-Pearson lower endpoint. It is conditional on the transported samples and selected nuclide "
                "mixture, is not a full 95% coverage statement, and excludes buildup-yield, exact-position M sampling, "
                "finite-buildup zero-family, and nuclide-mixture uncertainty. Zero-observation families receive no "
                "fictitious transport exposure."
            ),
            "coincidence": "family-resolved prompt occupancy plus family activity-scaled delayed occupancy plus atmospheric-line occupancy",
        },
    }
    audit = {
        "status": "PASS_MISSION_DAY15_AND_COMPONENT_CLOSURE",
        "day15_index": day15_index,
        "delayed_family_sum_cps": sum(summary["day15_selected_rates_cps"]["delayed_by_incident_family"].values()),
        "time_bins": len(timeline),
        "elapsed_days": elapsed_s / SECONDS_PER_DAY,
    }
    return summary, timeline, audit


def validate_outputs() -> dict[str, Any]:
    required = [
        SUMMARY, SELECTED, ACTIVITY_TIMELINE, MISSION_TIMELINE, RESPONSE,
        RESPONSE_REPLICAS, RESPONSE_VALIDATION, COMPONENTS, CAMPAIGN, STEP05,
        REGRESSION,
    ]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        raise MissionError(f"mission outputs missing: {missing}")
    summary = read_json(SUMMARY)
    problems: list[str] = []
    if summary.get("status") != MISSION_PASS:
        problems.append(f"summary status={summary.get('status')}")
    inputs = summary.get("input_authorities") or {}
    for key, value in inputs.items():
        if key.endswith("_sha256") or not isinstance(value, str):
            continue
        hash_key = f"{key}_sha256"
        path = resolve_path(value)
        if hash_key not in inputs:
            problems.append(f"input authority {key} lacks {hash_key}")
        elif not path.is_file():
            problems.append(f"input authority {key} is absent")
        elif inputs[hash_key] != sha256(path):
            problems.append(f"stale input authority hash: {key}")

    response_validation = read_json(RESPONSE_VALIDATION)
    if response_validation.get("status") != RESPONSE_VALIDATION_PASS:
        problems.append(f"response validation status={response_validation.get('status')}")
    if response_validation.get("summary_sha256") != sha256(RESPONSE):
        problems.append("response validation summary hash is stale")
    if response_validation.get("replicas_sha256") != sha256(RESPONSE_REPLICAS):
        problems.append("response validation replica hash is stale")
    regression = read_json(REGRESSION)
    if regression.get("status") != REGRESSION_PASS:
        problems.append(f"only-n generalized regression={regression.get('status')}")
    generalized_record = ((regression.get("input_authorities") or {}).get("generalized_mission_implementation") or {})
    if generalized_record.get("sha256") != sha256(Path(__file__)):
        problems.append("only-n generalized regression is stale against mission implementation")

    selected = read_json(SELECTED)
    if selected.get("status") != "PASS_S3D_O8_ALL8_PRIMARY_SEED_FAMILY_NUCLIDE_LINEAGE":
        problems.append(f"selected lineage status={selected.get('status')}")
    if selected.get("response_authority_sha256") != sha256(RESPONSE):
        problems.append("selected lineage response hash is stale")
    if selected.get("component_authority_sha256") != sha256(COMPONENTS):
        problems.append("selected lineage component hash is stale")

    components = read_json(COMPONENTS)
    component_by_family = {
        str(row.get("family")): row for row in components.get("components", [])
    }
    if set(component_by_family) != FAMILY_SET:
        problems.append("component family set is not exactly all eight")
    inventory_audits = {
        str(row.get("family")): row
        for row in summary.get("family_inventory_audits", [])
    }
    selected_audits = {
        str(row.get("family")): row for row in selected.get("family_audits", [])
    }
    lineage_rows = selected.get("lineage") or []
    strong = {
        (str(row.get("incident_family")), str(row.get("source_file")), int(row.get("local_id") or -1))
        for row in lineage_rows
    }
    if len(strong) != len(lineage_rows):
        problems.append("selected strong-lineage keys are not unique")
    recomputed_counts: Counter[tuple[str, int]] = Counter()
    fresh_inventories: dict[str, dict[int, dict[str, Any]]] = {}
    for family in FAMILIES:
        component = component_by_family.get(family) or {}
        family_rows = [row for row in lineage_rows if row.get("incident_family") == family]
        if component.get("status") in ZERO_STATUSES:
            fresh_inventories[family] = {}
            if family_rows:
                problems.append(f"finite-buildup zero family {family} has selected lineage")
            continue
        if component.get("status") != "PASS":
            problems.append(f"{family}: unsupported component status={component.get('status')}")
            continue
        try:
            sim = resolve_path(component["sim"])
            sim_hash = sha256(sim)
            if int(component.get("sim_size_bytes") or -1) != sim.stat().st_size or component.get("sim_sha256") != sim_hash:
                problems.append(f"{family}: component SIM size/hash stale")
            transport = component.get("transport_provenance") or {}
            if int(transport.get("size_bytes") or -1) != sim.stat().st_size or transport.get("sha256") != sim_hash:
                problems.append(f"{family}: transport_provenance SIM binding stale")
            inventory, current_inventory_audit = load_family_inventory(component)
            fresh_inventories[family] = inventory
            recorded_inventory = inventory_audits.get(family) or {}
            for key in (
                "fixed_summary_sha256", "groundstate_corrections_sha256",
                "day15_activity_Bq", "nuclides", "division", "tt_count",
            ):
                if isinstance(current_inventory_audit.get(key), float):
                    try:
                        require_close(
                            float(recorded_inventory.get(key)),
                            float(current_inventory_audit[key]),
                            f"validator {family} inventory audit/{key}",
                        )
                    except (MissionError, TypeError, ValueError) as exc:
                        problems.append(str(exc))
                elif recorded_inventory.get(key) != current_inventory_audit.get(key):
                    problems.append(f"{family}: recorded inventory audit {key} is stale")
            source_parent_index, current_source_parent_audit = load_source_parent_index(
                component
            )
            selected_audit = selected_audits.get(family) or {}
            recorded_source_parent_audit = selected_audit.get("source_parent_index") or {}
            for key in (
                "status",
                "weighted_table",
                "weighted_table_size_bytes",
                "weighted_table_sha256",
                "position_decimals",
                "position_match_tolerance_cm_per_axis",
                "position_bucket_cm",
                "rows",
                "unique_positions",
            ):
                if recorded_source_parent_audit.get(key) != current_source_parent_audit.get(key):
                    problems.append(
                        f"{family}: recorded source-parent index audit {key} is stale"
                    )
            ids = [int(row["local_id"]) for row in family_rows]
            fresh_state = scan_initial_state(sim, ids)
            fresh_daughter_or_chain_events = 0
            for row in family_rows:
                if resolve_path(row["source_file"]).resolve() != sim.resolve():
                    problems.append(f"{family}: selected source differs from current SIM")
                local_id = int(row["local_id"])
                state = fresh_state[local_id]
                sim_initial_za = int(state["sim_initial_ZA"])
                if int(row.get("initial_ZA") or -1) != sim_initial_za:
                    problems.append(
                        f"{family}/{local_id}: backward-compatible IA INIT ZA is stale"
                    )
                if int(row.get("sim_initial_ZA") or -1) != sim_initial_za:
                    problems.append(f"{family}/{local_id}: SIM initial ZA is stale")
                if row.get("sim_initial_position_key") != state.get(
                    "sim_initial_position_key"
                ):
                    problems.append(f"{family}/{local_id}: SIM initial position is stale")
                source_parent = match_source_parent(
                    source_parent_index,
                    state["sim_initial_position_cm"],
                    family=family,
                    local_id=local_id,
                )
                source_za = int(source_parent["source_parent_ZA"])
                if int(row.get("source_parent_ZA") or -1) != source_za:
                    problems.append(f"{family}/{local_id}: source-parent ZA is stale")
                for key in (
                    "source_parent_position_cm",
                    "source_parent_position_key",
                    "source_parent_volume",
                    "weighted_table_row",
                    "source_parent_position_abs_delta_cm",
                    "source_parent_position_max_abs_delta_cm",
                    "source_parent_position_match_tolerance_cm_per_axis",
                ):
                    if row.get(key) != source_parent.get(key):
                        problems.append(
                            f"{family}/{local_id}: source-parent lineage {key} is stale"
                        )
                if source_za not in inventory:
                    problems.append(
                        f"{family}/{local_id}: source-parent ZA absent from inventory"
                    )
                if row.get("source_parent_nuclide") != (
                    inventory.get(source_za) or {}
                ).get("nuclide"):
                    problems.append(
                        f"{family}/{local_id}: source-parent nuclide name is stale"
                    )
                fresh_daughter_or_chain_events += int(source_za != sim_initial_za)
                recomputed_counts[(family, source_za)] += 1
            if selected_audit.get("sim_sha256") != sim_hash:
                problems.append(f"{family}: selected family SIM hash is stale")
            if int(selected_audit.get("selected_events") or 0) != len(ids):
                problems.append(f"{family}: selected family count is stale")
            if int(selected_audit.get("daughter_or_chain_events") or 0) != (
                fresh_daughter_or_chain_events
            ):
                problems.append(
                    f"{family}: selected daughter/source-parent count is stale"
                )
        except (MissionError, OSError, KeyError, ValueError, TypeError, gzip.BadGzipFile) as exc:
            problems.append(f"{family}: provenance/lineage validation failed: {exc}")

    recorded_counts = {
        (str(row["incident_family"]), int(row["ZA"])): int(row["selected_events"])
        for row in selected.get("by_family_nuclide", [])
    }
    if dict(recomputed_counts) != recorded_counts:
        problems.append(
            "selected by-family/nuclide counts differ from fresh SIM-position "
            "to exact-source-parent lineage scan"
        )
    daughter_fixture = [
        row
        for row in lineage_rows
        if row.get("incident_family") == "n" and int(row.get("local_id") or -1) == 92071
    ]
    if len(daughter_fixture) != 1:
        problems.append("Ta-182 -> W-182 selected-lineage fixture is absent or duplicated")
    else:
        fixture = daughter_fixture[0]
        if (
            int(fixture.get("sim_initial_ZA") or -1) != 74182
            or int(fixture.get("source_parent_ZA") or -1) != 73182
            or fixture.get("source_parent_nuclide") != "Ta-182"
        ):
            problems.append("Ta-182 -> W-182 selected-lineage fixture changed")

    mission_rows = read_csv(MISSION_TIMELINE)
    activity_rows = read_csv(ACTIVITY_TIMELINE)
    if len(mission_rows) != 81:
        problems.append(f"mission timeline rows={len(mission_rows)}")
    if not activity_rows:
        problems.append("activity timeline is empty")
    mission_bin_ids = [int(row["time_bin_id"]) for row in mission_rows]
    expected_activity_keys = {
        (time_bin_id, family, za)
        for time_bin_id in mission_bin_ids
        for family, inventory in fresh_inventories.items()
        for za in inventory
    }
    actual_activity_keys = [
        (int(row["time_bin_id"]), str(row["incident_family"]), int(row["ZA"]))
        for row in activity_rows
    ]
    if len(actual_activity_keys) != len(set(actual_activity_keys)):
        problems.append("activity timeline family/parent/time keys are duplicated")
    if set(actual_activity_keys) != expected_activity_keys:
        problems.append(
            f"activity timeline key set differs from fresh inventory cross product: "
            f"actual={len(set(actual_activity_keys))} expected={len(expected_activity_keys)}"
        )
    for row, key in zip(activity_rows, actual_activity_keys):
        _time_bin_id, family, za = key
        inventory_row = (fresh_inventories.get(family) or {}).get(za)
        if inventory_row is None:
            continue
        if row.get("nuclide") != inventory_row.get("nuclide"):
            problems.append(f"activity timeline {family}/ZA={za} nuclide name is stale")
        try:
            require_close(
                float(row["half_life_s"]),
                float(inventory_row["half_life_s"]),
                f"validator activity {family}/ZA={za} half-life",
            )
            require_close(
                float(row["day15_activity_Bq"]),
                float(inventory_row["day15_activity_Bq"]),
                f"validator activity {family}/ZA={za} day15 activity",
            )
        except (MissionError, KeyError, ValueError, TypeError) as exc:
            problems.append(str(exc))
        if int(row.get("selected_events_day15") or 0) != int(
            recomputed_counts.get((family, za), 0)
        ):
            problems.append(
                f"activity timeline {family}/ZA={za} selected-event count is stale"
            )
    if mission_rows:
        if not math.isclose(float(mission_rows[-1]["elapsed_stop_day"]), 20.0, rel_tol=0.0, abs_tol=1.0e-12):
            problems.append(f"elapsed mission days={mission_rows[-1]['elapsed_stop_day']}")
        for key in ("cumulative_source_counts", "cumulative_background_counts", "counting_Z"):
            values = [float(row[key]) for row in mission_rows]
            if any(b < a for a, b in zip(values, values[1:])):
                problems.append(f"non-monotonic {key}")
        mission = summary.get("mission") or {}
        for key, timeline_key in (
            ("source_counts_20d", "cumulative_source_counts"),
            ("background_counts_20d", "cumulative_background_counts"),
            ("source_transport_counting_lower_endpoint_counts_20d", "cumulative_source_transport_counting_lower_endpoint_counts"),
            ("background_componentwise_transport_counting_upper_endpoint_counts_20d", "cumulative_background_componentwise_transport_counting_upper_endpoint_counts"),
            ("Z20d", "counting_Z"),
            ("Z20d_componentwise_transport_counting_endpoint_conditional", "counting_Z_componentwise_transport_counting_endpoint_conditional"),
        ):
            try:
                require_close(float(mission[key]), float(mission_rows[-1][timeline_key]), f"validator mission/{key}")
            except (MissionError, KeyError, ValueError, TypeError) as exc:
                problems.append(str(exc))
    long_life = ((summary.get("activity_integration") or {}).get("long_life_integrator_regression") or {})
    if long_life.get("status") != "PASS_LONG_LIFE_EXPM1_INVENTORY_REGRESSION":
        problems.append("long-life expm1 integrator regression is absent")

    outputs = summary.get("outputs") or {}
    for prefix, path in (
        ("selected_lineage", SELECTED),
        ("activity_timeline", ACTIVITY_TIMELINE),
        ("mission_timeline", MISSION_TIMELINE),
    ):
        if outputs.get(prefix) != rel(path):
            problems.append(f"summary output path differs for {prefix}")
        if int(outputs.get(f"{prefix}_size_bytes") or -1) != path.stat().st_size:
            problems.append(f"summary output size stale for {prefix}")
        if outputs.get(f"{prefix}_sha256") != sha256(path):
            problems.append(f"summary output hash stale for {prefix}")

    payload = {
        "status": VALIDATION_PASS if not problems else "FAIL_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_VALIDATION",
        "generated_at_utc": now_utc(),
        "summary": rel(SUMMARY),
        "summary_sha256": sha256(SUMMARY),
        "selected_lineage": rel(SELECTED),
        "selected_lineage_sha256": sha256(SELECTED),
        "activity_timeline": rel(ACTIVITY_TIMELINE),
        "activity_timeline_sha256": sha256(ACTIVITY_TIMELINE),
        "mission_timeline": rel(MISSION_TIMELINE),
        "mission_timeline_sha256": sha256(MISSION_TIMELINE),
        "mission_bins": len(mission_rows),
        "activity_rows": len(activity_rows),
        "expected_activity_keys": len(expected_activity_keys),
        "activity_key_set_complete": set(actual_activity_keys) == expected_activity_keys,
        "families_rechecked": len(component_by_family),
        "selected_events_rechecked": len(lineage_rows),
        "response_validation_status": response_validation.get("status"),
        "only_n_regression_status": regression.get("status"),
        "problems": problems,
    }
    write_json(VALIDATION, payload)
    return payload


def write_readme(payload: dict[str, Any]) -> None:
    mission = payload["mission"]
    rates = mission["day15_selected_rates_cps"]
    zeros = [
        row["family"]
        for row in payload["family_inventory_audits"]
        if row["status"] in ZERO_STATUSES
    ]
    README.write_text(
        "\n".join(
            [
                "# S3d-O8 all-eight-family family/nuclide mission fold",
                "",
                f"Status: `{payload['status']}`",
                "",
                "This package advances every positive activation inventory by incident family",
                "and exact-source parent nuclide through the 81-bin live-PARMA trajectory, then",
                "applies the same family/nuclide day-15 selected response. SIM IA INIT daughter",
                "ZA values are retained separately and position-matched back to the sampled",
                "source parent through each provenance-bound exact-position weighted table.",
                "",
                "## Headline",
                "",
                f"- Day-15 prompt: `{rates['prompt']:.12g}` cps.",
                f"- Day-15 all-family delayed: `{rates['delayed']:.12g}` cps.",
                f"- Day-15 total background: `{rates['background']:.12g}` cps.",
                f"- 20 d source counts: `{mission['source_counts_20d']:.12g}`.",
                f"- 20 d background counts: `{mission['background_counts_20d']:.12g}`.",
                f"- Central Z20: `{mission['Z20d']:.12g}`.",
                f"- Conditional componentwise transport-counting endpoint Z20: `{mission['Z20d_componentwise_transport_counting_endpoint_conditional']:.12g}`.",
                f"- Central 3-sigma flux: `{mission['flux_3sigma_20d_ph_cm2_s']:.12g}` ph cm^-2 s^-1.",
                f"- Conditional componentwise transport-counting endpoint 3-sigma flux: `{mission['flux_3sigma_20d_componentwise_transport_counting_endpoint_conditional_ph_cm2_s']:.12g}` ph cm^-2 s^-1.",
                "",
                f"Finite-buildup zero-observation families: `{', '.join(zeros) or 'none'}`.",
                "This is not a physical-zero claim. Their central delayed estimate is zero and",
                "no fictitious transport exposure is assigned. The conditional endpoint excludes",
                "buildup-yield, exact-position M sampling, finite-buildup zero-family, and",
                "nuclide-mixture uncertainty; it is not a full 95% coverage statement.",
                "",
                f"Machine validation: `{payload['validation']['status']}`.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run() -> dict[str, Any]:
    regression = run_only_n_regression()
    upstream = upstream_audit()
    if upstream["status"] != "PASS_READY_FOR_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION":
        raise MissionError(f"upstream gate={upstream['status']}: {upstream.get('problems') or upstream.get('missing')}")
    response = read_json(RESPONSE)
    components = read_json(COMPONENTS)
    component_by_family = {row["family"]: row for row in components["components"]}
    base, scales, time_audit = load_time_authorities()
    inventories: dict[str, dict[int, dict[str, Any]]] = {}
    inventory_audits: list[dict[str, Any]] = []
    for family in FAMILIES:
        component = component_by_family[family]
        if component["status"] in ZERO_STATUSES:
            inventories[family] = {}
            inventory_audits.append({"family": family, "status": component["status"], "nuclides": 0, "day15_activity_Bq": 0.0})
            continue
        inventory, audit = load_family_inventory(component)
        inventories[family] = inventory
        inventory_audits.append(audit)
    selected, selected_counts = build_selected_authority(
        response, components, inventories
    )

    curves, activity_rows, activity_audit = integrate_activities(
        base, scales, inventories, selected_counts, component_by_family
    )
    mission, timeline, mission_audit = mission_fold(
        response, base, scales, curves, inventories, selected_counts, component_by_family
    )
    activity_fields = [
        "time_bin_id", "day_mid", "incident_family", "ZA", "nuclide", "half_life_s",
        "day15_activity_Bq", "activity_Bq", "activity_scale_to_day15",
        "selected_events_day15", "event_weight_cps", "selection_response_cps_per_Bq", "selected_rate_cps",
    ]
    write_csv(ACTIVITY_TIMELINE, activity_rows, activity_fields)
    write_csv(MISSION_TIMELINE, timeline, list(timeline[0]))
    retained = read_json(RETAINED_NEUTRON_MISSION) if RETAINED_NEUTRON_MISSION.is_file() else None
    payload = {
        "status": MISSION_PASS,
        "generated_at_utc": now_utc(),
        "claim": (
            "The final S3d-O8 mission fold uses all-eight prompt families and every positive "
            "activation family, retaining family/source-parent-nuclide lineage, transported "
            "daughter evidence, and per-family normalization."
        ),
        "upstream_gate": upstream,
        "input_authorities": {
            "mission_implementation": rel(Path(__file__)),
            "mission_implementation_sha256": sha256(Path(__file__)),
            "campaign": rel(CAMPAIGN),
            "campaign_sha256": sha256(CAMPAIGN),
            "components": rel(COMPONENTS),
            "components_sha256": sha256(COMPONENTS),
            "step05": rel(STEP05),
            "step05_sha256": sha256(STEP05),
            "response": rel(RESPONSE),
            "response_sha256": sha256(RESPONSE),
            "response_replicas": rel(RESPONSE_REPLICAS),
            "response_replicas_sha256": sha256(RESPONSE_REPLICAS),
            "response_validation": rel(RESPONSE_VALIDATION),
            "response_validation_sha256": sha256(RESPONSE_VALIDATION),
            "only_n_generalized_regression": rel(REGRESSION),
            "only_n_generalized_regression_sha256": sha256(REGRESSION),
            "only_n_regression_implementation": rel(REGRESSION_CODE),
            "only_n_regression_implementation_sha256": sha256(REGRESSION_CODE),
            "base_step06_time_atmosphere_signal": rel(BASE_STEP06),
            "base_step06_time_atmosphere_signal_sha256": sha256(BASE_STEP06),
            "all8_parma_scales": rel(ALL8_SCALES),
            "all8_parma_scales_sha256": sha256(ALL8_SCALES),
            "retained_three_family_curve": rel(THREE_FAMILY_CURVE),
            "retained_three_family_curve_sha256": sha256(THREE_FAMILY_CURVE),
            "targeted_transport_audit": rel(TARGETED_AUDIT),
            "targeted_transport_audit_sha256": sha256(TARGETED_AUDIT),
        },
        "time_authority": time_audit,
        "only_n_generalized_regression": {
            "status": regression["status"],
            "authority": rel(REGRESSION),
            "authority_sha256": sha256(REGRESSION),
        },
        "selected_delayed_lineage": {
            "authority": rel(SELECTED),
            "status": selected["status"],
            "selected_events": selected["selected_events"],
            "by_family_nuclide": selected["by_family_nuclide"],
        },
        "family_inventory_audits": inventory_audits,
        "activity_integration": activity_audit,
        "mission_closure": mission_audit,
        "mission": mission,
        "comparison_to_retained_neutron_only_mission": None if retained is None else {
            "retained_authority": rel(RETAINED_NEUTRON_MISSION),
            "retained_authority_sha256": sha256(RETAINED_NEUTRON_MISSION),
            "retained_status": retained.get("status"),
            "retained_Z20d": (retained.get("mission") or {}).get("Z20d"),
            "all8_Z20d": mission["Z20d"],
            "boundary": "comparison only; the retained neutron-only fold is not added to the all-eight-family delayed rate",
        },
        "outputs": {
            "selected_lineage": rel(SELECTED),
            "selected_lineage_size_bytes": SELECTED.stat().st_size,
            "selected_lineage_sha256": sha256(SELECTED),
            "activity_timeline": rel(ACTIVITY_TIMELINE),
            "activity_timeline_size_bytes": ACTIVITY_TIMELINE.stat().st_size,
            "activity_timeline_sha256": sha256(ACTIVITY_TIMELINE),
            "mission_timeline": rel(MISSION_TIMELINE),
            "mission_timeline_size_bytes": MISSION_TIMELINE.stat().st_size,
            "mission_timeline_sha256": sha256(MISSION_TIMELINE),
            "summary": rel(SUMMARY),
            "validation": rel(VALIDATION),
        },
        "scope": {
            "new_monte_carlo_transport": False,
            "paper_sync_authorized_only_after_validation_pass": True,
            "finite_buildup_zero_family_uncertainty_in_conditional_transport_counting_endpoint": False,
            "zero_family_boundary": (
                "PASS_ZERO_PRODUCTION is a finite-buildup zero observation, not a physical-zero claim; "
                "the conditional componentwise endpoint is not full 95% coverage and excludes "
                "buildup-yield, exact-position M sampling, finite-buildup zero-family, and "
                "nuclide-mixture uncertainty"
            ),
        },
    }
    write_json(SUMMARY, payload)
    validation = validate_outputs()
    if validation["status"] != VALIDATION_PASS:
        payload["status"] = "FAIL_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_CLOSURE"
        payload["validation"] = validation
        write_json(SUMMARY, payload)
        raise MissionError(f"output validation failed: {validation['problems']}")
    # Do not rewrite SUMMARY after VALIDATION hashes it.  The returned object
    # carries the validation for the console caller; the stable on-disk summary
    # points to the separately hashed validation authority.
    payload["validation"] = validation
    write_readme(payload)
    return payload


def preflight() -> dict[str, Any]:
    regression = run_only_n_regression()
    upstream = upstream_audit()
    status = (
        "PASS_READY_FOR_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_POSTPROCESS"
        if upstream["status"] == "PASS_READY_FOR_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION"
        else "PENDING_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_INPUTS"
        if upstream["status"].startswith("PENDING")
        else "FAIL_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_PREFLIGHT"
    )
    payload = {
        "status": status,
        "generated_at_utc": now_utc(),
        "script": rel(Path(__file__)),
        "script_sha256": sha256(Path(__file__)),
        "upstream": upstream,
        "only_n_generalized_regression": regression,
        "production_launched": False,
        "postprocess_confirmation": {"flag": "--allow-postprocess", "token": CONFIRM_TOKEN},
    }
    write_json(PREFLIGHT, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=("regression", "preflight", "run", "validate"),
        nargs="?",
        default="preflight",
    )
    parser.add_argument("--force-regression", action="store_true")
    parser.add_argument("--allow-postprocess", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    try:
        if args.stage == "regression":
            payload = run_only_n_regression(force=args.force_regression)
        elif args.stage == "preflight":
            payload = preflight()
        elif args.stage == "validate":
            payload = validate_outputs()
        else:
            if not args.allow_postprocess or args.confirm != CONFIRM_TOKEN:
                raise MissionError(f"mission postprocessing requires --allow-postprocess --confirm {CONFIRM_TOKEN}")
            payload = run()
        print(json.dumps({
            "status": payload["status"],
            "summary": rel(SUMMARY) if args.stage == "run" else None,
            "Z20d": (payload.get("mission") or {}).get("Z20d"),
        }, indent=2))
        return 0 if str(payload["status"]).startswith(("PASS", "PENDING")) else 2
    except (MissionError, OSError, ValueError, KeyError, EOFError, gzip.BadGzipFile) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
