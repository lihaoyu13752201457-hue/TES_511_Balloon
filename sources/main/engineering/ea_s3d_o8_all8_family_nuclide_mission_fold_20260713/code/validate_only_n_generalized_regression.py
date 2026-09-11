#!/usr/bin/env python3
"""Regression of the generalized all-family mission fold against retained S3d n-only data.

This module is deliberately analysis-only.  It never invokes Cosima and it never
writes any retained authority.  Prompt response and occupancy remain resolved
over all eight incident families, while the delayed adapter exposes the retained
neutron component and explicit finite-buildup zero observations for the other
seven families.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
RUNNER = Path(__file__).with_name("build_s3d_o8_all8_family_nuclide_mission_fold.py")
OUTPUT = DATA / "s3d_o8_all8_only_n_generalized_mission_regression.json"

RETAINED_PACKAGE = ROOT / "engineering/ea_s3d_family_nuclide_mission_fold_20260713"
RETAINED_SUMMARY = RETAINED_PACKAGE / "data/s3d_family_nuclide_mission_summary.json"
RETAINED_SELECTED = RETAINED_PACKAGE / "data/selected_delayed_nuclides_primary_seed.json"
RETAINED_ACTIVITY = RETAINED_PACKAGE / "outputs/nuclide_activity_by_time.csv"
RETAINED_TIMELINE = RETAINED_PACKAGE / "outputs/w2_family_nuclide_mission_timeline.csv"
RETAINED_RESPONSE = (
    ROOT
    / "engineering/ea_detector_response_closure_20260713/data/"
    "o8_energy_response_closure_summary.json"
)

FIX_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704/"
    "step02_delay_fix_s3d_o8_neutron_delayed_m50000_20260712"
)
FIXED_SUMMARY = FIX_DIR / "source_fix_summary.json"
FIXED_SOURCE = FIX_DIR / "activation_decay_day15_groundstate_fixed.source"
GROUNDSTATE = FIX_DIR / "groundstate_activity_corrections.csv"
INVENTORY = (
    ROOT
    / "runs/geometry_optimization_20260704/"
    "step02_decay_source_s3d_o8_neutron_delayed_m50000_20260712/"
    "activation_inventory_day15.csv"
)
EXACTPOS_MANIFEST = (
    ROOT
    / "runs/geometry_optimization_20260704/"
    "step02_delay_exactpos_s3d_o8_neutron_delayed_m50000_20260712/"
    "s3d_o8_neutron_delayed_m50000_20260712_exactpos_m50000_s260613_delayed_source_manifest.json"
)
WEIGHTED_TABLE = (
    ROOT
    / "runs/geometry_optimization_20260704/"
    "step02_delay_exactpos_s3d_o8_neutron_delayed_m50000_20260712/"
    "exactpos_weighted_rpip_table_m50000_s260613.csv"
)
DELAYED_SIM = (
    ROOT
    / "runs/geometry_optimization_20260704/"
    "step02_delayed_transport_s3d_o8_neutron_delayed_m50000_20260712/"
    "DelayedDecayS3dO8NeutronM50000.inc1.id1.sim.gz"
)

PASS = "PASS_S3D_O8_ALL8_ONLY_N_GENERALIZED_MISSION_REGRESSION"
FAIL = "FAIL_S3D_O8_ALL8_ONLY_N_GENERALIZED_MISSION_REGRESSION"


class RegressionError(RuntimeError):
    """A retained-authority or numerical-regression invariant failed."""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


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


def load_runner() -> Any:
    spec = importlib.util.spec_from_file_location("s3d_o8_all8_mission_regression_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RegressionError(f"cannot import {rel(RUNNER)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def require_close(
    actual: float,
    expected: float,
    label: str,
    *,
    atol: float = 1.0e-12,
    rtol: float = 1.0e-10,
) -> None:
    if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol):
        raise RegressionError(f"{label}: {actual:.17g} != {expected:.17g}")


def artifact(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RegressionError(f"missing retained authority: {rel(path)}")
    return {"path": rel(path), "size_bytes": path.stat().st_size, "sha256": sha256(path)}


def input_fingerprint(runner: Any) -> dict[str, dict[str, Any]]:
    paths = {
        "regression_implementation": Path(__file__),
        "generalized_mission_implementation": RUNNER,
        "retained_summary": RETAINED_SUMMARY,
        "retained_selected": RETAINED_SELECTED,
        "retained_activity": RETAINED_ACTIVITY,
        "retained_timeline": RETAINED_TIMELINE,
        "retained_response": RETAINED_RESPONSE,
        "fixed_summary": FIXED_SUMMARY,
        "fixed_source": FIXED_SOURCE,
        "groundstate_corrections": GROUNDSTATE,
        "inventory": INVENTORY,
        "exactpos_manifest": EXACTPOS_MANIFEST,
        "weighted_table": WEIGHTED_TABLE,
        "delayed_sim": DELAYED_SIM,
        "base_step06": runner.BASE_STEP06,
        "all8_scales": runner.ALL8_SCALES,
    }
    return {name: artifact(path) for name, path in paths.items()}


def independent_inventory(runner: Any) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Legacy loader used only if the production loader requires new all8 provenance."""
    fixed = read_json(FIXED_SUMMARY)
    if not runner.exact_o8_geometry(fixed.get("geometry")):
        raise RegressionError(f"retained fixed-source geometry changed: {fixed.get('geometry')}")
    normalization = fixed.get("normalization") or {}
    if set(normalization) != {"n"}:
        raise RegressionError(f"retained normalization family set={sorted(normalization)}")
    norm = normalization["n"]
    for key in ("files", "division", "tt_count", "tt_files", "tt_line_count"):
        require_close(float(norm[key]), 8.0, f"retained neutron normalization {key}", atol=0.0, rtol=0.0)

    inventory: dict[int, dict[str, Any]] = {}
    for row in read_csv(GROUNDSTATE):
        activity = float(row["new_groundstate_activity_Bq"])
        half_life = float(row["nubase_half_life_s"])
        if activity <= 0.0:
            continue
        if not math.isfinite(half_life) or half_life <= 0.0:
            raise RegressionError(f"n/ZA={row['ZA']}: invalid half-life {half_life}")
        za = int(row["ZA"])
        record = inventory.setdefault(
            za,
            {
                "incident_family": "n",
                "ZA": za,
                "nuclide": row["nuclide"],
                "half_life_s": half_life,
                "day15_activity_Bq": 0.0,
                "volume_rows": 0,
            },
        )
        if record["nuclide"] != row["nuclide"]:
            raise RegressionError(f"n/ZA={za}: inconsistent nuclide names")
        require_close(float(record["half_life_s"]), half_life, f"n/ZA={za} half-life")
        record["day15_activity_Bq"] += activity
        record["volume_rows"] += 1
    total = sum(float(row["day15_activity_Bq"]) for row in inventory.values())
    require_close(total, float(fixed["new_total_activity_Bq"]), "retained inventory total", atol=1.0e-8)
    return inventory, {
        "status": "PASS_RETAINED_NEUTRON_NUBASE_GROUNDSTATE_INVENTORY",
        "loader": "independent_legacy_loader_after_strict_all8_provenance_incompatibility",
        "nuclides": len(inventory),
        "day15_activity_Bq": total,
        "division": 8.0,
        "tt_count": int(norm["tt_count"]),
    }


def load_inventory(runner: Any, component: dict[str, Any]) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    try:
        inventory, audit = runner.load_family_inventory(component)
        audit = {**audit, "loader": "generalized_mission_runner.load_family_inventory"}
        return inventory, audit
    except (runner.MissionError, KeyError, TypeError, ValueError) as exc:
        inventory, audit = independent_inventory(runner)
        audit["generalized_loader_rejection"] = str(exc)
        return inventory, audit


def retained_neutron_component(runner: Any, inputs: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    fixed = read_json(FIXED_SUMMARY)
    manifest = read_json(EXACTPOS_MANIFEST)
    selected = read_json(RETAINED_SELECTED)
    transport = manifest.get("delayed_transport") or {}
    te_s = float(transport.get("TE_s") or 0.0)
    if transport.get("status") != "PASS" or te_s <= 0.0:
        raise RegressionError(f"retained delayed transport status/TE={transport.get('status')}/{te_s}")
    manifest_sim = runner.resolve_path(str(transport.get("path")))
    if manifest_sim.resolve() != DELAYED_SIM.resolve():
        raise RegressionError(f"manifest delayed SIM changed: {transport.get('path')}")
    if int(transport.get("size_bytes") or -1) != DELAYED_SIM.stat().st_size:
        raise RegressionError("manifest delayed SIM size differs from the retained file")
    if int(transport.get("SE") or -1) != 1_000_000 or int(transport.get("ID") or -1) != 1_000_000:
        raise RegressionError("retained delayed transport no longer reports SE=ID=1,000,000")

    weight = float(selected["selected_summary"]["event_weight_cps"])
    require_close(weight, 1.0 / te_s, "retained neutron 1/TE event weight", atol=0.0, rtol=1.0e-15)
    activity = float(fixed["new_total_activity_Bq"])
    require_close(activity, float(manifest["fixed_total_activity_Bq"]), "fixed activity vs exact-position manifest")

    source_records = {
        "fixed_summary": inputs["fixed_summary"],
        "fixed_source": inputs["fixed_source"],
        "groundstate_corrections": inputs["groundstate_corrections"],
        "inventory": inputs["inventory"],
    }
    component: dict[str, Any] = {
        "family": "n",
        "status": "PASS_RETAINED_NEUTRON_DELAYED_COMPONENT",
        "activity_Bq": activity,
        "TE_s": te_s,
        "event_weight_hz": weight,
        "fixed_summary": rel(FIXED_SUMMARY),
        "fixed_summary_sha256": inputs["fixed_summary"]["sha256"],
        "fixed_source": inputs["fixed_source"],
        "groundstate_corrections": inputs["groundstate_corrections"],
        "inventory": inputs["inventory"],
        "source_provenance": source_records,
        "sim": rel(DELAYED_SIM),
        "sim_size_bytes": DELAYED_SIM.stat().st_size,
        "sim_sha256": inputs["delayed_sim"]["sha256"],
        "transport_provenance": inputs["delayed_sim"],
    }
    audit = {
        "status": "PASS_RETAINED_NEUTRON_FIXED_SOURCE_SIM_AND_TE",
        "fixed_total_activity_Bq": activity,
        "TE_s": te_s,
        "event_weight_cps": weight,
        "SE": int(transport["SE"]),
        "ID": int(transport["ID"]),
        "sim": inputs["delayed_sim"],
        "fixed_summary": inputs["fixed_summary"],
        "groundstate_corrections": inputs["groundstate_corrections"],
        "normalization_division": float(fixed["normalization"]["n"]["division"]),
    }
    return component, audit


def response_adapter(runner: Any, retained_response: dict[str, Any], retained_summary: dict[str, Any], selected: dict[str, Any]) -> dict[str, Any]:
    # JSON round-trip gives a plain deep copy without importing the old response implementation.
    response = json.loads(json.dumps(retained_response))
    primary = response["primary_authority"]["step05"]
    w2 = primary["windows"]["w2_510p58_511p42"]
    physical = w2["physical_reference_flux"]
    uncertainty = physical["uncertainty_95"]
    old_interval = list(uncertainty["delayed_background_interval95_cps"])
    old_upper = float(uncertainty["delayed_background_upper95_cps"])
    weight = float(selected["selected_summary"]["event_weight_cps"])
    events = int(selected["selected_summary"]["events"])
    delayed: dict[str, dict[str, Any]] = {}
    for family in runner.FAMILIES:
        if family == "n":
            delayed[family] = {
                "events": events,
                "rate_cps": float(physical["delayed_background_cps"]),
                "event_weight_cps": weight,
                "rate_interval95_cps": old_interval,
                "rate_upper95_cps": old_upper,
                "adapter_status": "RETAINED_POSITIVE_NEUTRON_TRANSPORT",
            }
        else:
            delayed[family] = {
                "events": 0,
                "rate_cps": 0.0,
                "event_weight_cps": 0.0,
                "rate_interval95_cps": [0.0, 0.0],
                "rate_upper95_cps": 0.0,
                "adapter_status": "FINITE_BUILDUP_ZERO_OBSERVATION_NO_FICTITIOUS_TRANSPORT_EXPOSURE",
            }
    uncertainty["delayed_components_by_incident_family"] = delayed

    retained_prompt_occ = retained_summary["prompt_occupancy_day15_by_family"]
    old_delayed_occ = primary["occupancy_day15"]["delayed"]
    primary["occupancy_day15_by_family"] = {
        "prompt": {
            family: {
                "events": int(retained_prompt_occ[family]["events"]),
                "rate_hz": float(retained_prompt_occ[family]["rate_hz_day15"]),
            }
            for family in runner.FAMILIES
        },
        "delayed": {
            family: (
                {"events": int(old_delayed_occ["events"]), "rate_hz": float(old_delayed_occ["rate_hz"])}
                if family == "n"
                else {"events": 0, "rate_hz": 0.0}
            )
            for family in runner.FAMILIES
        },
    }
    return response


def component_map(runner: Any, neutron: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for family in runner.FAMILIES:
        out[family] = neutron if family == "n" else {
            "family": family,
            "status": "PASS_ZERO_PRODUCTION",
            "activity_Bq": 0.0,
            "TE_s": None,
            "event_weight_hz": 0.0,
        }
    return out


def selected_lineage_audit(runner: Any, selected: dict[str, Any], inputs: dict[str, dict[str, Any]]) -> tuple[dict[tuple[str, int], int], dict[str, Any]]:
    if selected.get("status") != "PASS_PRIMARY_SEED_DELAYED_NUCLIDE_LINEAGE":
        raise RegressionError(f"retained selected status={selected.get('status')}")
    if int(selected.get("response_seed") or -1) != int(runner.PRIMARY_SEED):
        raise RegressionError("retained selected response seed changed")
    selected_sim = runner.resolve_path(str(selected.get("delayed_sim")))
    if selected_sim.resolve() != DELAYED_SIM.resolve():
        raise RegressionError(f"retained selected authority points to {selected.get('delayed_sim')}")
    if int(selected.get("delayed_sim_size_bytes") or -1) != DELAYED_SIM.stat().st_size:
        raise RegressionError("retained selected delayed-SIM size changed")

    ids = [int(value) for value in selected.get("selected_event_ids") or []]
    if len(ids) != int(selected["selected_summary"]["events"]) or len(ids) != len(set(ids)):
        raise RegressionError("retained selected event IDs are missing or duplicated")
    states = runner.scan_initial_state(DELAYED_SIM, ids)
    rescanned = {
        local_id: int(state["sim_initial_ZA"])
        for local_id, state in states.items()
    }
    expected = {int(key): int(value) for key, value in selected["initial_za_by_event_id"].items()}
    if rescanned != expected:
        raise RegressionError("fresh IA INIT scan does not reproduce retained selected-neutron ZA lineage")
    source_parent_index, source_parent_audit = runner.load_source_parent_index({
        "family": "n",
        "source_provenance": {"weighted_table": inputs["weighted_table"]},
    })
    source_parent_counts: dict[int, int] = defaultdict(int)
    daughter_or_chain_events = 0
    max_position_delta_cm = 0.0
    for local_id, state in states.items():
        source_parent = runner.match_source_parent(
            source_parent_index,
            state["sim_initial_position_cm"],
            family="n",
            local_id=local_id,
        )
        source_za = int(source_parent["source_parent_ZA"])
        source_parent_counts[source_za] += 1
        daughter_or_chain_events += int(source_za != int(state["sim_initial_ZA"]))
        max_position_delta_cm = max(
            max_position_delta_cm,
            float(source_parent["source_parent_position_max_abs_delta_cm"]),
        )
    authority_counts = {int(row["ZA"]): int(row["selected_events"]) for row in selected["by_nuclide"]}
    if dict(source_parent_counts) != authority_counts:
        raise RegressionError(
            "fresh exact-source parent counts do not reproduce retained by-nuclide authority"
        )
    if daughter_or_chain_events != 0:
        raise RegressionError(
            "retained only-n selected sample unexpectedly changed source-parent/IA INIT identity"
        )
    # Synthetic edge-case guard for the all8 Ta-182 -> W-182 daughter exposed
    # by n/local_id=92071.  This prevents a future regression to direct IA-ZA
    # inventory lookup without making the retained only-n package depend on the
    # new all8 SIM.
    fixture_source = [-3.235295, 0.988888, -4.188056]
    fixture_record = {
        "source_parent_ZA": 73182,
        "source_parent_position_cm": fixture_source,
        "source_parent_position_key": list(runner.source_position_key(fixture_source)),
        "source_parent_volume": "TES_Pixel_L3",
        "weighted_table_row": 15418,
    }
    fixture_index = {
        runner.source_position_bucket(fixture_source): [fixture_record]
    }
    fixture_match = runner.match_source_parent(
        fixture_index,
        [-3.23530, 0.98888, -4.18806],
        family="n",
        local_id=92071,
    )
    if int(fixture_match["source_parent_ZA"]) != 73182:
        raise RegressionError("Ta-182 -> W-182 source-parent mapper fixture failed")
    counts = {("n", za): count for za, count in authority_counts.items()}
    return counts, {
        "status": "PASS_FRESH_RETAINED_NEUTRON_SOURCE_PARENT_LINEAGE_SCAN",
        "selected_events": len(ids),
        "selected_nuclides": len(authority_counts),
        "by_ZA": {str(key): value for key, value in sorted(authority_counts.items())},
        "sim_initial_by_ZA": {
            str(key): value
            for key, value in sorted(
                {za: list(rescanned.values()).count(za) for za in set(rescanned.values())}.items()
            )
        },
        "daughter_or_chain_events": daughter_or_chain_events,
        "max_source_parent_position_delta_cm": max_position_delta_cm,
        "source_parent_index": source_parent_audit,
        "ta182_to_w182_mapper_fixture": {
            "status": "PASS_TA182_TO_W182_SOURCE_PARENT_FIXTURE",
            "sim_initial_ZA": 74182,
            "source_parent_ZA": 73182,
            "source_parent_position_max_abs_delta_cm": fixture_match[
                "source_parent_position_max_abs_delta_cm"
            ],
        },
        "delayed_sim": inputs["delayed_sim"],
    }


def maximum_delta(actual: float, expected: float, record: dict[str, float]) -> None:
    absolute = abs(actual - expected)
    relative = absolute / max(abs(expected), 1.0e-300)
    record["max_abs_delta"] = max(record.get("max_abs_delta", 0.0), absolute)
    record["max_rel_delta"] = max(record.get("max_rel_delta", 0.0), relative)


def compare_activity_rows(runner: Any, generated: list[dict[str, Any]]) -> dict[str, Any]:
    retained = read_csv(RETAINED_ACTIVITY)
    if len(retained) != 6561 or len(generated) != 6561:
        raise RegressionError(f"activity row count retained/generated={len(retained)}/{len(generated)}, expected 6561/6561")
    expected = {(int(row["time_bin_id"]), int(row["ZA"])): row for row in retained}
    actual = {(int(row["time_bin_id"]), int(row["ZA"])): row for row in generated}
    if len(expected) != 6561 or set(actual) != set(expected):
        raise RegressionError("generalized activity (time_bin_id, ZA) keys differ from retained authority")

    exact_fields = ("time_bin_id", "ZA", "nuclide", "selected_events_day15")
    numeric_fields = (
        "day_mid",
        "half_life_s",
        "day15_activity_Bq",
        "activity_Bq",
        "activity_scale_to_day15",
        "selection_response_cps_per_Bq",
        "selected_rate_cps",
    )
    deltas = {field: {"max_abs_delta": 0.0, "max_rel_delta": 0.0} for field in numeric_fields}
    retained_weight = 1.0 / float(read_json(EXACTPOS_MANIFEST)["delayed_transport"]["TE_s"])
    for key in sorted(expected):
        old = expected[key]
        new = actual[key]
        if str(new.get("incident_family")) != "n":
            raise RegressionError(f"activity {key}: incident_family={new.get('incident_family')}")
        for field in exact_fields:
            if str(new[field]) != str(old[field]):
                raise RegressionError(f"activity {key} {field}: {new[field]} != {old[field]}")
        for field in numeric_fields:
            av = float(new[field])
            ev = float(old[field])
            # The retained authority used cancellation-prone 1-exp(-x).  For
            # long-lived nuclides the new expm1 path is the numerically correct
            # result, so admit and report that bounded, intentional delta while
            # keeping ordinary half-lives on a tight reduction tolerance.
            long_lived_value = float(new["half_life_s"]) >= 1.0e12
            stabilized_field = field in (
                "activity_Bq", "activity_scale_to_day15", "selected_rate_cps"
            )
            rtol = (
                1.0e-4
                if long_lived_value and stabilized_field
                else 1.0e-8
                if stabilized_field
                else 2.0e-10
            )
            require_close(av, ev, f"activity {key} {field}", atol=5.0e-15, rtol=rtol)
            maximum_delta(av, ev, deltas[field])
        require_close(
            float(new["event_weight_cps"]),
            retained_weight,
            f"activity {key} new event_weight_cps",
            atol=0.0,
            rtol=1.0e-15,
        )
    return {
        "status": "PASS_6561_RETAINED_NEUTRON_ACTIVITY_ROWS_WITH_BOUNDED_EXPM1_STABILITY_DELTA",
        "rows": len(generated),
        "key": ["time_bin_id", "ZA"],
        "common_numeric_field_deltas": deltas,
        "new_fields": {
            "incident_family": "n for all 6561 rows",
            "event_weight_cps": "exactly 1/retained TE_s for all 6561 rows",
        },
        "floating_point_contract": "non-integrated fields rtol=2e-10; expm1-stabilized activity/scale/selected-rate rows rtol=1e-8, relaxed to rtol=1e-4 only for half-life >=1e12 s, with atol=5e-15; all deltas are reported field by field and mission headlines remain tightly gated",
    }


def get_alias(mapping: dict[str, Any], aliases: tuple[str, ...], label: str) -> float:
    for key in aliases:
        if key in mapping:
            return float(mapping[key])
    raise RegressionError(f"missing generalized field for {label}; aliases={aliases}")


def compare_timeline(runner: Any, generated: list[dict[str, Any]], activity: list[dict[str, Any]]) -> dict[str, Any]:
    retained = read_csv(RETAINED_TIMELINE)
    if len(retained) != 81 or len(generated) != 81:
        raise RegressionError(f"mission timeline retained/generated={len(retained)}/{len(generated)}, expected 81/81")
    old = {int(row["time_bin_id"]): row for row in retained}
    new = {int(row["time_bin_id"]): row for row in generated}
    if set(old) != set(new) or len(new) != 81:
        raise RegressionError("generalized 81-bin timeline keys differ from retained authority")

    common = sorted(set(retained[0]).intersection(generated[0]))
    common.remove("time_bin_id")
    deltas = {field: {"max_abs_delta": 0.0, "max_rel_delta": 0.0} for field in common}
    activity_by_bin: dict[int, float] = defaultdict(float)
    for row in activity:
        activity_by_bin[int(row["time_bin_id"])] += float(row["activity_Bq"])
    for index in sorted(old):
        for field in common:
            av = float(new[index][field])
            ev = float(old[index][field])
            require_close(av, ev, f"timeline bin={index} {field}", atol=5.0e-12, rtol=2.0e-10)
            maximum_delta(av, ev, deltas[field])
        require_close(float(new[index]["delayed_n_activity_Bq"]), activity_by_bin[index], f"timeline bin={index} new delayed_n_activity_Bq")
        require_close(float(new[index]["delayed_n_selected_cps"]), float(old[index]["delayed_final_cps_noacc"]), f"timeline bin={index} new delayed_n_selected_cps")
        n_upper = get_alias(
            new[index],
            ("delayed_n_upper95_cps", "delayed_n_componentwise_transport_counting_endpoint_conditional_cps"),
            f"timeline bin={index} delayed n endpoint",
        )
        require_close(n_upper, float(old[index]["delayed_final_upper95_cps_noacc"]), f"timeline bin={index} new delayed_n endpoint")
        for family in runner.FAMILIES:
            if family == "n":
                continue
            for suffix in ("activity_Bq", "selected_cps"):
                require_close(float(new[index][f"delayed_{family}_{suffix}"]), 0.0, f"timeline bin={index} zero {family} {suffix}", atol=0.0, rtol=0.0)
            zero_endpoint = get_alias(
                new[index],
                (f"delayed_{family}_upper95_cps", f"delayed_{family}_componentwise_transport_counting_endpoint_conditional_cps"),
                f"timeline bin={index} zero {family} endpoint",
            )
            require_close(zero_endpoint, 0.0, f"timeline bin={index} zero {family} endpoint", atol=0.0, rtol=0.0)
        for retained_key, generated_key in (
            ("background_final_upper95_cps_noacc", "background_final_componentwise_transport_counting_endpoint_cps_noacc"),
            ("cumulative_source_lower95_counts", "cumulative_source_transport_counting_lower_endpoint_counts"),
            ("cumulative_background_upper95_counts", "cumulative_background_componentwise_transport_counting_upper_endpoint_counts"),
            ("counting_Z_conservative95", "counting_Z_componentwise_transport_counting_endpoint_conditional"),
        ):
            require_close(
                float(new[index][generated_key]),
                float(old[index][retained_key]),
                f"timeline bin={index} conditional endpoint reduction {generated_key}",
                atol=5.0e-12,
                rtol=2.0e-10,
            )
    return {
        "status": "PASS_RETAINED_81BIN_COMMON_NUMERICS_AND_NEW_N_FIELDS",
        "bins": len(generated),
        "common_numeric_fields": len(common),
        "common_numeric_field_deltas": deltas,
        "new_n_fields_checked": [
            "delayed_n_activity_Bq",
            "delayed_n_selected_cps",
            "delayed_n conditional componentwise transport-counting endpoint",
        ],
        "explicit_zero_family_fields_checked": 7 * 3 * 81,
    }


def compare_headlines(generated: dict[str, Any], retained: dict[str, Any]) -> dict[str, Any]:
    aliases: dict[str, tuple[str, ...]] = {
        "reference_flux_ph_cm2_s": ("reference_flux_ph_cm2_s",),
        "source_counts_20d": ("source_counts_20d",),
        "background_counts_20d": ("background_counts_20d",),
        "source_lower95_counts_20d": (
            "source_lower95_counts_20d",
            "source_lower_transport_counting_endpoint_conditional_counts_20d",
            "source_transport_counting_lower_endpoint_counts_20d",
        ),
        "background_upper95_counts_20d": (
            "background_upper95_counts_20d",
            "background_componentwise_transport_counting_endpoint_conditional_counts_20d",
            "background_componentwise_transport_counting_upper_endpoint_counts_20d",
        ),
        "Z20d": ("Z20d",),
        "Z20d_conservative95": ("Z20d_conservative95", "Z20d_componentwise_transport_counting_endpoint_conditional"),
        "flux_3sigma_20d_ph_cm2_s": ("flux_3sigma_20d_ph_cm2_s",),
        "flux_3sigma_20d_conservative95_ph_cm2_s": (
            "flux_3sigma_20d_conservative95_ph_cm2_s",
            "flux_3sigma_20d_componentwise_transport_counting_endpoint_conditional_ph_cm2_s",
        ),
        "T3_day": ("T3_day",),
        "T5_day": ("T5_day",),
        "T3_day_conservative95": ("T3_day_conservative95", "T3_day_componentwise_transport_counting_endpoint_conditional"),
        "T5_day_conservative95": ("T5_day_conservative95", "T5_day_componentwise_transport_counting_endpoint_conditional"),
        "accidental_loss_min": ("accidental_loss_min",),
        "accidental_loss_max": ("accidental_loss_max",),
    }
    deltas: dict[str, dict[str, float]] = {}
    for old_key, candidates in aliases.items():
        av = get_alias(generated, candidates, old_key)
        ev = float(retained[old_key])
        require_close(av, ev, f"mission headline {old_key}", atol=5.0e-12, rtol=2.0e-10)
        record = {"max_abs_delta": 0.0, "max_rel_delta": 0.0}
        maximum_delta(av, ev, record)
        deltas[old_key] = record

    old_rates = retained["day15_selected_rates_cps"]
    new_rates = generated["day15_selected_rates_cps"]
    rate_aliases = {
        "prompt": ("prompt",),
        "delayed": ("delayed",),
        "atm511": ("atm511",),
        "background": ("background",),
        "signal": ("signal",),
        "background_upper95": (
            "background_upper95",
            "background_componentwise_upper95",
            "background_componentwise_transport_counting_endpoint_conditional",
            "background_componentwise_transport_counting_endpoint_cps",
        ),
        "signal_lower95": (
            "signal_lower95",
            "signal_lower_transport_counting_endpoint_conditional",
            "signal_transport_counting_lower_endpoint_cps",
        ),
    }
    for old_key, candidates in rate_aliases.items():
        require_close(get_alias(new_rates, candidates, f"day15 {old_key}"), float(old_rates[old_key]), f"mission day15 {old_key}", atol=5.0e-12, rtol=2.0e-10)
    by_family = new_rates.get("delayed_by_incident_family") or {}
    if set(by_family) != {"alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p"}:
        raise RegressionError("generalized day15 delayed family set is not exactly all eight")
    require_close(float(by_family["n"]), float(old_rates["delayed"]), "day15 generalized neutron delayed rate")
    for family, value in by_family.items():
        if family != "n":
            require_close(float(value), 0.0, f"day15 generalized zero delayed family {family}", atol=0.0, rtol=0.0)
    return {
        "status": "PASS_ALL_RETAINED_MISSION_HEADLINES",
        "headline_scalars": len(aliases),
        "day15_rate_scalars": len(rate_aliases),
        "numeric_deltas": deltas,
        "delayed_by_incident_family": {key: float(value) for key, value in by_family.items()},
    }


def execute_regression(runner: Any, inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    retained_summary = read_json(RETAINED_SUMMARY)
    retained_mission = retained_summary["mission"]
    retained_response = read_json(RETAINED_RESPONSE)
    selected = read_json(RETAINED_SELECTED)
    neutron, transport_audit = retained_neutron_component(runner, inputs)
    inventory, inventory_audit = load_inventory(runner, neutron)
    if len(inventory) != 81:
        raise RegressionError(f"retained neutron ground-state inventory has {len(inventory)} nuclides, expected 81")
    selected_counts, selected_audit = selected_lineage_audit(runner, selected, inputs)
    if any(za not in inventory for _family, za in selected_counts):
        raise RegressionError("selected neutron ZA is absent from retained ground-state inventory")

    base, scales, time_audit = runner.load_time_authorities()
    response = response_adapter(runner, retained_response, retained_summary, selected)
    components = component_map(runner, neutron)
    inventories = {family: (inventory if family == "n" else {}) for family in runner.FAMILIES}
    curves, activity_rows, activity_audit = runner.integrate_activities(
        base, scales, inventories, selected_counts, components
    )
    mission, timeline, mission_audit = runner.mission_fold(
        response, base, scales, curves, inventories, selected_counts, components
    )

    activity_regression = compare_activity_rows(runner, activity_rows)
    timeline_regression = compare_timeline(runner, timeline, activity_rows)
    headline_regression = compare_headlines(mission, retained_mission)
    return {
        "status": PASS,
        "generated_at_utc": now_utc(),
        "scope": {
            "new_monte_carlo_transport": False,
            "retained_authorities_modified": False,
            "prompt_model": "retained all-eight-family prompt response and occupancy",
            "delayed_model": "retained neutron positive component plus seven explicit finite-buildup zero observations",
            "purpose": "executable regression of the generalized all-family equations, not a final all8 production result",
        },
        "input_authorities": inputs,
        "retained_neutron_transport": transport_audit,
        "retained_neutron_inventory": inventory_audit,
        "retained_selected_lineage": selected_audit,
        "time_authority": time_audit,
        "generalized_activity_audit": activity_audit,
        "generalized_mission_audit": mission_audit,
        "activity_regression": activity_regression,
        "timeline_regression": timeline_regression,
        "headline_regression": headline_regression,
    }


def run_regression(force: bool = False) -> dict[str, Any]:
    """Run or reuse the exact retained only-neutron generalized regression."""
    try:
        runner = load_runner()
        inputs = input_fingerprint(runner)
        if not force and OUTPUT.is_file():
            cached = read_json(OUTPUT)
            if cached.get("status") == PASS and cached.get("input_authorities") == inputs:
                return cached
        payload = execute_regression(runner, inputs)
    except Exception as exc:  # Always leave an auditable failure result for preflight.
        payload = {
            "status": FAIL,
            "generated_at_utc": now_utc(),
            "error_type": type(exc).__name__,
            "error": str(exc),
            "scope": {
                "new_monte_carlo_transport": False,
                "retained_authorities_modified": False,
            },
        }
    write_json(OUTPUT, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="ignore a hash-current PASS cache")
    args = parser.parse_args()
    payload = run_regression(force=args.force)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload.get("status") == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
