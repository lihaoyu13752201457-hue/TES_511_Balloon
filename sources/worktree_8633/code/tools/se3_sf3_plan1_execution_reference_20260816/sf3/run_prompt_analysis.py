#!/usr/bin/env python3
"""Build the SF3 Plan-1 prompt catalog and common-response-ready tables.

The canonical Plan-1 receipts select the instant rich-SIM artifacts.  A normal
run is refused until every planned instant job has a canonical PASS receipt.
Each selected SIM is then decompressed exactly once to build a compact catalog;
SIM payload hashes are deliberately neither computed nor checked here.

``--check-prerequisites`` is read-only.  It checks plans, receipts, artifact
paths/sizes, and the retained response implementations without opening a SIM.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import importlib.util
import json
import math
import os
import pickle
import random
import re
import shutil
import sys
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from sf3_plan1_common import FAMILIES, PACKAGE_ROOT, PROFILE_ID, REPO_ROOT


HERE = Path(__file__).resolve()
DEFAULT_CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
SOURCE_WORKTREE = Path("/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon")
OLD_CATALOG_PARSER = SOURCE_WORKTREE / "old/code/tools/make_complete_day15_report_ADR.py"
CORRECTED_CORE = SOURCE_WORKTREE / (
    "engineering/particle_source_unit_repair_20260811/"
    "composite_partial_postprocess_20260812/code/analyze_composite_partial.py"
)
STEP05 = SOURCE_WORKTREE / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP09_SUMMARY = SOURCE_WORKTREE / (
    "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/"
    "step09_optics_bridge_summary.json"
)
os.environ.setdefault("MPLCONFIGDIR", "/tmp/sf3_plan1_prompt_matplotlib")

GEOMETRY_ORDER = ("SF3",)
FAMILY_ORDER = tuple(FAMILIES)
CORE_GEOMETRY = {"SF3": "sf3", "S3d_O8": "s3d_o8"}
WINDOWS = {
    "broad_480_550": (480.0, 550.0),
    "w2_510p58_511p42": (510.58, 511.42),
}
VETO_THRESHOLDS_KEV = (50.0, 70.0, 80.0)
PASSIVE_W_VOLUMES = (
    "SF3_W_NearField_FrontWindowPlate_2p9mm",
    "SF3_W_NearField_SideSleeve_2p9mm",
    "SF3_W_NearField_RearColdFingerAnnulus_2p9mm",
)
SPECTRUM_LO_KEV = 480.0
SPECTRUM_HI_KEV = 550.0
SPECTRUM_BIN_KEV = 0.5
EXPECTED_INSTANT_JOBS = 11
EXPECTED_INSTANT_HISTORIES = 1_280_693

_OLD: Any | None = None

IA_RE = re.compile(r"^IA\s+(?P<process>\S+)\s+(?P<body>.*)$")
CC_META_RE = re.compile(
    r"\bt=(?P<time>[-+0-9.eE]+)\s+sec=(?P<secondary>\S+)\s+"
    r"tid=(?P<tid>\d+)\s+pid=(?P<pid>\d+)\s+sproc=(?P<sproc>\S+)"
)
_IA_PROCESS_ALIASES = {
    "COMP": frozenset({"compt"}),
    "PHOT": frozenset({"phot"}),
    "RAYL": frozenset({"rayl"}),
    "PAIR": frozenset({"conv", "pair"}),
    "ANNI": frozenset({"anni", "annih", "annihilation"}),
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON object required: {path}")
    return value


def display_path(path: Path) -> str:
    """Prefer repository-relative provenance, but preserve external authorities."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import retained implementation: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def old_parser() -> Any:
    global _OLD
    if _OLD is None:
        tools = str(OLD_CATALOG_PARSER.parent)
        if tools not in sys.path:
            sys.path.insert(0, tools)
        _OLD = load_module("sf3_retained_compact_catalog_parser", OLD_CATALOG_PARSER)
    return _OLD


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write an empty CSV without a declared schema: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fields or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def cast_plan_row(row: dict[str, str]) -> dict[str, Any]:
    value: dict[str, Any] = dict(row)
    for key in (
        "ordinal", "shard", "events", "s3d_histories", "target_histories",
        "seed", "estimated_bytes",
    ):
        value[key] = int(row[key])
    for key in ("paired_seed_exception", "production_canary"):
        value[key] = row[key].strip().lower() == "true"
    return value


def read_plan(config: dict[str, Any]) -> list[dict[str, Any]]:
    path = Path(config["transport"]["job_plan"])
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [cast_plan_row(row) for row in csv.DictReader(handle)]


def instant_plan(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row for row in read_plan(config)
        if row["stage"] == "background" and row["mode"] == "instant"
    ]
    return sorted(rows, key=lambda row: row["ordinal"])


def receipt_path(config: dict[str, Any], job_id: str) -> Path:
    return Path(config["run_root"]) / "receipts" / f"{job_id}.json"


def explicit_veto_policy(config: dict[str, Any]) -> dict[str, Any]:
    geometry = config["geometry"]
    shield = list(geometry["shield_veto_volumes"])
    plastic = list(geometry["plastic_veto_volumes"])
    active = list(geometry["active_veto_volumes"])
    return {
        "policy_id": "SF3_EXPLICIT_3BGO_PLUS_3PLASTIC",
        "shield_volumes": shield,
        "plastic_volumes": plastic,
        "active_veto_volumes": active,
        "apply_plastic_veto": bool(geometry["apply_plastic_veto"]),
        "plastic_threshold_keV": float(config["analysis"]["active_veto_threshold_keV"]),
        "shield_thresholds_keV": list(VETO_THRESHOLDS_KEV),
        "passive_w_volumes": list(passive_w_volumes(config)),
        "passive_w_role": "DIAGNOSTIC_ONLY__NEVER_ACTIVE_VETO",
    }


def passive_w_volumes(config: dict[str, Any]) -> tuple[str, ...]:
    """Return the frozen passive-W contract or fail closed.

    W is intentionally absent from the measured-response veto.  Keeping this
    validation separate from the hit scanner prevents a geometry-name shortcut
    from silently turning a passive plate into a seventh active-veto volume.
    """
    geometry = config["geometry"]
    actual = tuple(str(value) for value in geometry.get("passive_w_volumes", []))
    if actual != PASSIVE_W_VOLUMES:
        raise RuntimeError("SF3 passive-W role list differs from the frozen three-volume contract")
    if not bool(geometry.get("passive_w_never_active_veto", False)):
        raise RuntimeError("SF3 passive-W never-active-veto assertion is not enabled")
    active = {str(value) for value in geometry.get("active_veto_volumes", [])}
    overlap = active & set(actual)
    if overlap:
        raise RuntimeError(f"SF3 passive W appears in an active-veto role: {sorted(overlap)}")
    return actual


def parse_ia(line: str) -> dict[str, Any] | None:
    """Parse the common SIM IA fields needed for W-local diagnostics."""
    match = IA_RE.match(line)
    if not match or match.group("process").upper() == "INIT":
        return None
    fields = [field.strip() for field in match.group("body").split(";")]
    if len(fields) < 7:
        return None
    try:
        return {
            "process": match.group("process").upper(),
            "interaction_id": int(fields[0]),
            "parent_id": int(fields[1]),
            "time_s": float(fields[3]),
            "x_cm": float(fields[4]),
            "y_cm": float(fields[5]),
            "z_cm": float(fields[6]),
        }
    except (TypeError, ValueError):
        return None


def match_ia_volume(
    interaction: dict[str, Any] | None,
    cc_hits: list[dict[str, Any]],
) -> tuple[str, str]:
    """Resolve one IA to a recorded CC HIT using the retained time/process rule.

    The method deliberately reports an unresolved state when an interaction has
    no recorded deposit.  It never infers W locality from the IA coordinate
    alone, so the W-local PAIR/ANNI counts are conservative and auditable.
    """
    if interaction is None:
        return "", "NO_NON_INIT_IA"
    expected = _IA_PROCESS_ALIASES.get(str(interaction["process"]).upper(), set())
    time_s = float(interaction["time_s"])
    tolerance = max(5.0e-15, abs(time_s) * 2.0e-5)
    candidates = [
        hit for hit in cc_hits
        if abs(float(hit["time_s"]) - time_s) <= tolerance
        and (not expected or str(hit["sproc"]).lower() in expected)
    ]
    if not candidates:
        candidates = [
            hit for hit in cc_hits
            if abs(float(hit["time_s"]) - time_s) <= tolerance
        ]
    if not candidates:
        return "", "UNRESOLVED_ZERO_EDEP_OR_UNRECORDED_IA"
    selected = min(candidates, key=lambda hit: abs(float(hit["time_s"]) - time_s))
    return str(selected["volume"]), "MATCHED_CC_HIT_TIME_PROCESS"


def _cc_hit_time(hit: dict[str, Any]) -> float:
    return float(hit["time_s"])


class _StableHitTimeIndex:
    """Event-local exact accelerator for :func:`match_ia_volume`.

    The lists contain references to the original HIT dictionaries, not copied
    records.  Python's stable sort preserves source order for identical times.
    For two different, exactly equidistant times, ``_first_in_original_order``
    restores the stable-``min`` tie rule of the linear reference implementation.
    """

    def __init__(
        self,
        cc_hits: list[dict[str, Any]],
        needed_processes: set[str],
    ) -> None:
        self._original = cc_hits
        try:
            self.finite = all(math.isfinite(_cc_hit_time(hit)) for hit in cc_hits)
        except (TypeError, ValueError, OverflowError):
            self.finite = False
        self._all: list[dict[str, Any]] = []
        self._by_process: dict[str, list[dict[str, Any]]] = {}
        if not self.finite:
            return

        self._all = sorted(cc_hits, key=_cc_hit_time)
        wanted = {
            str(process).upper() for process in needed_processes
            if str(process).upper() in _IA_PROCESS_ALIASES
        }
        self._by_process = {process: [] for process in wanted}
        for hit in self._all:
            secondary_process = str(hit["sproc"]).lower()
            for process in wanted:
                if secondary_process in _IA_PROCESS_ALIASES[process]:
                    self._by_process[process].append(hit)

    def _first_in_original_order(
        self,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if len(candidates) == 1:
            return candidates[0]
        candidate_ids = {id(hit) for hit in candidates}
        for hit in self._original:
            if id(hit) in candidate_ids:
                return hit
        raise RuntimeError("indexed CC HIT is absent from its source-order list")

    def _nearest(
        self,
        rows: list[dict[str, Any]],
        time_s: float,
        tolerance: float,
    ) -> dict[str, Any] | None:
        """Return the stable reference winner around the insertion point."""
        position = bisect.bisect_left(rows, time_s, key=_cc_hit_time)
        adjacent_distances: list[float] = []

        if position < len(rows):
            adjacent_distances.append(abs(_cc_hit_time(rows[position]) - time_s))

        if position > 0:
            preceding_time = _cc_hit_time(rows[position - 1])
            adjacent_distances.append(abs(preceding_time - time_s))

        if not adjacent_distances:
            return None
        best_distance = min(adjacent_distances)
        if best_distance > tolerance:
            return None

        # Normally there are one or two winners.  Expanding an equal-distance
        # floating-point plateau makes the stable-min equivalence exact even at
        # subnormal/opposite-sign boundaries where rounded subtraction could
        # give more than two distinct times the same absolute-distance key.
        candidates: list[dict[str, Any]] = []
        left_position = position - 1
        while left_position >= 0:
            candidate_time = _cc_hit_time(rows[left_position])
            first_at_time = bisect.bisect_left(rows, candidate_time, key=_cc_hit_time)
            distance = abs(candidate_time - time_s)
            if distance > best_distance:
                break
            if distance == best_distance:
                candidates.append(rows[first_at_time])
            left_position = first_at_time - 1

        right_position = position
        while right_position < len(rows):
            candidate_time = _cc_hit_time(rows[right_position])
            distance = abs(candidate_time - time_s)
            if distance > best_distance:
                break
            if distance == best_distance:
                candidates.append(rows[right_position])
            right_position = bisect.bisect_right(
                rows, candidate_time, key=_cc_hit_time
            )

        if not candidates:
            raise RuntimeError("adjacent CC HIT distance has no indexed winner")
        return self._first_in_original_order(candidates)

    def match(self, interaction: dict[str, Any] | None) -> tuple[str, str]:
        if interaction is None:
            return "", "NO_NON_INIT_IA"
        time_s = float(interaction["time_s"])
        if not self.finite or not math.isfinite(time_s):
            return match_ia_volume(interaction, self._original)

        tolerance = max(5.0e-15, abs(time_s) * 2.0e-5)
        process = str(interaction["process"]).upper()
        selected = None
        if process in _IA_PROCESS_ALIASES:
            selected = self._nearest(
                self._by_process.get(process, []), time_s, tolerance
            )
        if selected is None:
            selected = self._nearest(self._all, time_s, tolerance)
        if selected is None:
            return "", "UNRESOLVED_ZERO_EDEP_OR_UNRECORDED_IA"
        return str(selected["volume"]), "MATCHED_CC_HIT_TIME_PROCESS"


def _all_event_times_finite(*rows: list[dict[str, Any]]) -> bool:
    try:
        return all(
            math.isfinite(float(item["time_s"]))
            for collection in rows
            for item in collection
        )
    except (TypeError, ValueError, OverflowError):
        return False


def event_w_diagnostics(
    interactions: list[dict[str, Any]],
    primary_hits: list[dict[str, Any]],
    all_meta_hits: list[dict[str, Any]],
    passive_w: set[str],
) -> dict[str, Any]:
    """Classify first interaction and resolvable PAIR/ANNI locality for one event."""
    first = min(
        (item for item in interactions if int(item["parent_id"]) == 1),
        key=lambda item: (float(item["time_s"]), int(item["interaction_id"])),
        default=None,
    )
    diagnostic_processes = {
        item["process"] for item in interactions
        if item["process"] in {"PAIR", "ANNI"}
    }
    use_index = _all_event_times_finite(interactions, primary_hits, all_meta_hits)
    if use_index:
        if first is None:
            first_volume, first_resolution = "", "NO_NON_INIT_IA"
        else:
            primary_index = _StableHitTimeIndex(
                primary_hits, {str(first["process"])},
            )
            if not primary_index.finite:
                raise RuntimeError("finite event produced a non-finite primary HIT index")
            first_volume, first_resolution = primary_index.match(first)
        all_hit_index = (
            _StableHitTimeIndex(all_meta_hits, diagnostic_processes)
            if diagnostic_processes else None
        )
        if all_hit_index is not None and not all_hit_index.finite:
            raise RuntimeError("finite event produced a non-finite all-HIT index")
    else:
        all_hit_index = None
        first_volume, first_resolution = match_ia_volume(first, primary_hits)

    result: dict[str, Any] = {
        "first_interaction_volume": first_volume,
        "first_interaction_resolution": first_resolution,
        "first_interaction_in_passive_w": first_volume in passive_w,
    }
    for process, prefix in (("PAIR", "pair"), ("ANNI", "annihilation")):
        count = 0
        w_count = 0
        unresolved_count = 0
        for item in interactions:
            if item["process"] != process:
                continue
            count += 1
            volume, _ = (
                all_hit_index.match(item)
                if all_hit_index is not None
                else match_ia_volume(item, all_meta_hits)
            )
            w_count += int(volume in passive_w)
            unresolved_count += int(not volume)
        result[f"{prefix}_ia_count"] = count
        result[f"w_{prefix}_ia_count"] = w_count
        result[f"{prefix}_ia_unresolved_count"] = unresolved_count
    return result


def check_prerequisites(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Check all prompt inputs without opening or hashing a SIM payload."""
    errors: list[str] = []
    missing_receipts: list[str] = []
    validated: list[dict[str, Any]] = []
    config_path = config_path.resolve()
    try:
        config = load_json(config_path)
    except Exception as exc:
        return {
            "schema_version": 1,
            "status": "FAIL__SF3_PROMPT_CONFIG",
            "ready": False,
            "errors": [str(exc)],
            "missing_receipts": [],
            "sim_access_policy": "NO_SIM_OPEN_OR_HASH",
        }

    for implementation in (OLD_CATALOG_PARSER, CORRECTED_CORE, STEP05, STEP09_SUMMARY):
        if not implementation.is_file():
            errors.append(f"retained implementation missing: {implementation}")
    for key in ("job_plan", "receipts"):
        path = Path(config["transport"][key])
        if not path.is_file():
            errors.append(f"transport {key} missing: {path}")
    setup = Path(config["geometry"]["sf3_setup"])
    if not setup.is_file():
        errors.append(f"SF3 setup missing: {setup}")

    try:
        policy = explicit_veto_policy(config)
        shield = policy["shield_volumes"]
        plastic = policy["plastic_volumes"]
        active = policy["active_veto_volumes"]
        if len(shield) != 3 or len(plastic) != 3 or len(active) != 6:
            errors.append("SF3 veto policy must contain exactly 3 shield + 3 plastic volumes")
        if set(shield) & set(plastic) or set(shield) | set(plastic) != set(active):
            errors.append("SF3 explicit shield/plastic roles do not exactly partition six active volumes")
        if len(active) != len(set(active)):
            errors.append("SF3 active-veto list contains duplicates")
        passive_w = set(config["geometry"].get("passive_w_volumes", []))
        expected_w = {
            "SF3_W_NearField_FrontWindowPlate_2p9mm",
            "SF3_W_NearField_SideSleeve_2p9mm",
            "SF3_W_NearField_RearColdFingerAnnulus_2p9mm",
        }
        if passive_w != expected_w:
            errors.append("SF3 passive-W role list differs from the frozen three-volume contract")
        if set(active) & passive_w:
            errors.append("SF3 passive W appears in an active-veto role")
        if not policy["apply_plastic_veto"]:
            errors.append("SF3 plastic veto is not explicitly enabled")
        if not math.isclose(policy["plastic_threshold_keV"], 50.0, abs_tol=0.0):
            errors.append("SF3 nominal plastic-veto threshold is not 50 keV")
    except Exception as exc:
        errors.append(f"invalid explicit veto policy: {exc}")

    analysis = config.get("analysis", {})
    if not math.isclose(float(analysis.get("response_fwhm_keV", -1)), 0.42, abs_tol=0.0):
        errors.append("configured response FWHM is not 0.42 keV")
    if not math.isclose(float(analysis.get("measured_pixel_threshold_keV", -1)), 0.3, abs_tol=0.0):
        errors.append("configured measured-pixel threshold is not 0.3 keV")
    if tuple(float(value) for value in analysis.get("w2_keV", [])) != WINDOWS["w2_510p58_511p42"]:
        errors.append("configured W2 is not 510.58--511.42 keV")

    try:
        plan = instant_plan(config)
    except Exception as exc:
        plan = []
        errors.append(f"instant plan unreadable: {exc}")
    if len(plan) != EXPECTED_INSTANT_JOBS:
        errors.append(f"instant job count {len(plan)} != {EXPECTED_INSTANT_JOBS}")
    if sum(int(row["events"]) for row in plan) != EXPECTED_INSTANT_HISTORIES:
        errors.append("instant history total differs from frozen Plan-1 target")
    if {row["family"] for row in plan} != set(FAMILY_ORDER):
        errors.append("instant family closure differs from the eight-family contract")
    for family in FAMILY_ORDER:
        rows = [row for row in plan if row["family"] == family]
        if not rows:
            continue
        target = rows[0]["target_histories"]
        if any(row["target_histories"] != target for row in rows):
            errors.append(f"inconsistent target histories for {family}")
        if sum(row["events"] for row in rows) != target:
            errors.append(f"instant shard closure differs for {family}")
        if target <= 100_000 and len(rows) != 1:
            errors.append(f"target <=100k was split for {family}")
        if target > 100_000 and any(row["events"] < 100_000 for row in rows):
            errors.append(f"instant shard below 100k for {family}")

    aggregate_selected: dict[str, dict[str, Any]] = {}
    aggregate_path = Path(config["transport"]["receipts"])
    if aggregate_path.is_file():
        try:
            aggregate = load_json(aggregate_path)
            aggregate_selected = {
                str(row["job_id"]): row for row in aggregate.get("selected_receipts", [])
            }
        except Exception as exc:
            errors.append(f"aggregate receipt ledger unreadable: {exc}")

    seen_sim: set[str] = set()
    for row in plan:
        path = receipt_path(config, row["job_id"])
        if not path.is_file():
            missing_receipts.append(row["job_id"])
            continue
        try:
            receipt = load_json(path)
        except Exception as exc:
            errors.append(f"receipt unreadable {row['job_id']}: {exc}")
            continue
        if receipt.get("status") != "PASS" or receipt.get("errors") not in ([], None):
            errors.append(f"canonical receipt is not clean PASS: {row['job_id']}")
        expected = {
            "profile_id": PROFILE_ID,
            "job_id": row["job_id"],
            "stage": "background",
            "geometry": "SF3",
            "mode": "instant",
            "family": row["family"],
            "events": row["events"],
            "seed": row["seed"],
            "source_path": row["source_path"],
            "setup_path": row["setup_path"],
        }
        for key, value in expected.items():
            if receipt.get(key) != value:
                errors.append(
                    f"{row['job_id']} receipt {key}={receipt.get(key)!r}, expected {value!r}"
                )
        sim = Path(str(receipt.get("sim_path", "")))
        source = Path(str(receipt.get("source_path", "")))
        if not sim.is_file() or sim.stat().st_size != int(receipt.get("sim_bytes", -1)):
            errors.append(f"SIM path/size declaration failed: {row['job_id']}")
        if not source.is_file():
            errors.append(f"source path is missing: {row['job_id']}")
        tt_s = receipt.get("isotope_dat", {}).get("TT_s")
        if tt_s is None or not math.isfinite(float(tt_s)) or float(tt_s) <= 0.0:
            errors.append(f"non-positive receipt TT: {row['job_id']}")
        if receipt.get("log", {}).get("generated_events") != row["events"]:
            errors.append(f"generated-event receipt mismatch: {row['job_id']}")
        if receipt.get("log", {}).get("graphics_terminal_marker") is not True:
            errors.append(f"terminal marker receipt mismatch: {row['job_id']}")
        header = receipt.get("sim_header", {})
        try:
            header_geometry_matches = (
                Path(str(header.get("geometry"))).resolve() == Path(row["setup_path"]).resolve()
            )
        except Exception:
            header_geometry_matches = False
        if not header_geometry_matches or header.get("seed") != row["seed"]:
            errors.append(f"SIM header receipt mismatch: {row['job_id']}")
        if receipt.get("sim_digest_policy") != "OMITTED_BY_CONTRACT__PATH_SIZE_HEADER_RECEIPT_ONLY":
            errors.append(f"SIM no-digest policy differs: {row['job_id']}")
        resolved_sim = str(sim.resolve()) if sim.exists() else str(sim)
        if resolved_sim in seen_sim:
            errors.append(f"duplicate selected SIM: {resolved_sim}")
        seen_sim.add(resolved_sim)
        aggregate_row = aggregate_selected.get(row["job_id"])
        if aggregate_row is None:
            errors.append(f"canonical aggregate omits PASS receipt: {row['job_id']}")
        elif aggregate_row.get("sim_path") != str(sim):
            errors.append(f"aggregate SIM binding differs: {row['job_id']}")
        validated.append({
            "job_id": row["job_id"],
            "family": row["family"],
            "events": row["events"],
            "seed": row["seed"],
            "TT_s": tt_s,
            "receipt_path": str(path),
            "sim_path": str(sim),
            "sim_bytes": receipt.get("sim_bytes"),
        })

    ready = not errors and not missing_receipts and len(validated) == len(plan)
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": (
            "READY__SF3_PLAN1_PROMPT_RECEIPTS_COMPLETE"
            if ready else "NOT_READY__SF3_PLAN1_PROMPT_RECEIPTS_INCOMPLETE"
        ),
        "ready": ready,
        "config": str(config_path),
        "required_jobs": len(plan),
        "required_histories": sum(int(row["events"]) for row in plan),
        "validated_jobs": len(validated),
        "validated_histories": sum(int(row["events"]) for row in validated),
        "missing_receipts": missing_receipts,
        "errors": errors,
        "veto_policy": explicit_veto_policy(config) if "geometry" in config else {},
        "implementations": [
            str(OLD_CATALOG_PARSER), str(CORRECTED_CORE), str(STEP05), str(STEP09_SUMMARY),
        ],
        "sim_access_policy": "STAT_ONLY__NO_SIM_OPEN_OR_HASH",
        "selected": validated,
    }


def selected_instant_jobs(config_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    prerequisites = check_prerequisites(config_path)
    if not prerequisites["ready"]:
        raise RuntimeError(json.dumps(prerequisites, indent=2, sort_keys=True))
    config = load_json(config_path)
    policy = explicit_veto_policy(config)
    jobs: list[dict[str, Any]] = []
    for scan_index, row in enumerate(instant_plan(config)):
        rpath = receipt_path(config, row["job_id"])
        receipt = load_json(rpath)
        jobs.append({
            **row,
            "scan_index": scan_index,
            "input_id": "sf3_plan1_canonical_receipt",
            "batch_id": PROFILE_ID,
            "job_id": row["job_id"],
            "sim_path": str(Path(receipt["sim_path"]).resolve()),
            "TT_s": float(receipt["isotope_dat"]["TT_s"]),
            "receipt_path": str(rpath.resolve()),
            "receipt_sim_bytes": int(receipt["sim_bytes"]),
            "expected_geometry": str(Path(row["setup_path"]).resolve()),
            "shield_volumes": list(policy["shield_volumes"]),
            "plastic_volumes": list(policy["plastic_volumes"]),
            "passive_w_volumes": list(policy["passive_w_volumes"]),
            "veto_policy": policy,
        })
    return config, jobs, prerequisites


def scan_job(job: dict[str, Any], cache_dir: str) -> dict[str, Any]:
    """Read one rich SIM once and retain TES plus exact veto deposits."""
    parser = old_parser()
    catalog = parser.empty_catalog()
    extras: dict[str, list[Any]] = {
        "input_id": [],
        "batch_id": [],
        "job_name": [],
        "seed": [],
        "plastic_total_keV": [],
        "has_pair_ia": [],
        "has_annihilation_ia": [],
        "w_total_keV": [],
        "first_interaction_volume": [],
        "first_interaction_resolution": [],
        "first_interaction_in_passive_w": [],
        "w_pair_ia_count": [],
        "w_annihilation_ia_count": [],
        "pair_ia_unresolved_count": [],
        "annihilation_ia_unresolved_count": [],
    }
    shield = set(job["shield_volumes"])
    plastic = set(job["plastic_volumes"])
    passive_w = set(job["passive_w_volumes"])
    if passive_w & (shield | plastic):
        raise RuntimeError(f"{job['job_id']}: passive W overlaps the active-veto volumes")
    current_id: int | None = None
    active_total = 0.0
    plastic_total = 0.0
    w_total = 0.0
    pixels: dict[str, dict[str, float | int]] = {}
    has_pair = False
    has_annihilation = False
    interactions: list[dict[str, Any]] = []
    primary_hits: list[dict[str, Any]] = []
    all_meta_hits: list[dict[str, Any]] = []
    generated = 0
    active_only = 0
    w_deposit_events = 0
    w_deposit_keV_sum = 0.0
    w_first_interaction_events = 0
    w_pair_events = 0
    w_annihilation_events = 0
    pair_ia_count = 0
    w_pair_ia_count = 0
    pair_ia_unresolved_count = 0
    annihilation_ia_count = 0
    w_annihilation_ia_count = 0
    annihilation_ia_unresolved_count = 0
    header_geometry = ""
    header_seed: int | None = None
    terminal_en = 0

    def flush() -> None:
        nonlocal current_id, active_total, plastic_total, w_total, pixels
        nonlocal has_pair, has_annihilation, active_only
        nonlocal interactions, primary_hits, all_meta_hits
        nonlocal w_deposit_events, w_deposit_keV_sum, w_first_interaction_events
        nonlocal w_pair_events, w_annihilation_events
        nonlocal pair_ia_count, w_pair_ia_count, pair_ia_unresolved_count
        nonlocal annihilation_ia_count, w_annihilation_ia_count
        nonlocal annihilation_ia_unresolved_count
        if current_id is None:
            return
        w_diag = event_w_diagnostics(interactions, primary_hits, all_meta_hits, passive_w)
        w_deposit_events += int(w_total > 0.0)
        w_deposit_keV_sum += w_total
        w_first_interaction_events += int(w_diag["first_interaction_in_passive_w"])
        pair_ia_count += int(w_diag["pair_ia_count"])
        w_pair_ia_count += int(w_diag["w_pair_ia_count"])
        pair_ia_unresolved_count += int(w_diag["pair_ia_unresolved_count"])
        annihilation_ia_count += int(w_diag["annihilation_ia_count"])
        w_annihilation_ia_count += int(w_diag["w_annihilation_ia_count"])
        annihilation_ia_unresolved_count += int(w_diag["annihilation_ia_unresolved_count"])
        w_pair_events += int(int(w_diag["w_pair_ia_count"]) > 0)
        w_annihilation_events += int(int(w_diag["w_annihilation_ia_count"]) > 0)
        if pixels:
            before = len(catalog["stream"])
            parser.append_event(
                catalog,
                "prompt",
                job["family"],
                job["sim_path"],
                current_id,
                0.0,
                active_total,
                pixels,
            )
            if len(catalog["stream"]) == before + 1:
                extras["input_id"].append(job["input_id"])
                extras["batch_id"].append(job["batch_id"])
                extras["job_name"].append(job["job_id"])
                extras["seed"].append(job["seed"])
                extras["plastic_total_keV"].append(plastic_total)
                extras["has_pair_ia"].append(has_pair)
                extras["has_annihilation_ia"].append(has_annihilation)
                extras["w_total_keV"].append(w_total)
                extras["first_interaction_volume"].append(w_diag["first_interaction_volume"])
                extras["first_interaction_resolution"].append(
                    w_diag["first_interaction_resolution"]
                )
                extras["first_interaction_in_passive_w"].append(
                    w_diag["first_interaction_in_passive_w"]
                )
                extras["w_pair_ia_count"].append(w_diag["w_pair_ia_count"])
                extras["w_annihilation_ia_count"].append(w_diag["w_annihilation_ia_count"])
                extras["pair_ia_unresolved_count"].append(
                    w_diag["pair_ia_unresolved_count"]
                )
                extras["annihilation_ia_unresolved_count"].append(
                    w_diag["annihilation_ia_unresolved_count"]
                )
        elif active_total > 0.0 or plastic_total > 0.0:
            active_only += 1
        current_id = None
        active_total = 0.0
        plastic_total = 0.0
        w_total = 0.0
        pixels = {}
        has_pair = False
        has_annihilation = False
        interactions = []
        primary_hits = []
        all_meta_hits = []

    with parser.open_text(job["sim_path"]) as handle:
        for raw in handle:
            line = raw.strip()
            if not header_geometry and line.startswith("Geometry "):
                header_geometry = line.split(maxsplit=1)[1]
            elif header_seed is None and line.startswith("Seed "):
                header_seed = int(line.split()[1])
            if line == "EN":
                terminal_en += 1
                continue
            if line == "SE":
                flush()
                continue
            match = parser.ID_RE.match(line)
            if match:
                current_id = int(match.group(1))
                generated += 1
                continue
            interaction = parse_ia(line)
            if interaction is not None:
                interactions.append(interaction)
                has_pair = has_pair or interaction["process"] == "PAIR"
                has_annihilation = has_annihilation or interaction["process"] == "ANNI"
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = parser.parse_cc_hit(line)
            if hit is None:
                continue
            volume, edep, x, y, z = hit
            meta = CC_META_RE.search(line)
            if meta:
                meta_hit = {
                    "volume": volume,
                    "time_s": float(meta.group("time")),
                    "sproc": meta.group("sproc"),
                }
                all_meta_hits.append(meta_hit)
                if int(meta.group("tid")) == 1 and int(meta.group("pid")) == 0:
                    primary_hits.append(meta_hit)
            pixel_match = parser.TP_RE.match(volume)
            if pixel_match:
                record = pixels.setdefault(
                    volume,
                    {
                        "e": 0.0,
                        "wx": 0.0,
                        "wy": 0.0,
                        "wz": 0.0,
                        "layer": int(pixel_match.group("layer")),
                    },
                )
                record["e"] = float(record["e"]) + edep
                record["wx"] = float(record["wx"]) + edep * x
                record["wy"] = float(record["wy"]) + edep * y
                record["wz"] = float(record["wz"]) + edep * z
            elif volume in shield:
                active_total += edep
            elif volume in plastic:
                plastic_total += edep
            elif volume in passive_w:
                w_total += edep
    flush()

    if generated != int(job["events"]):
        raise RuntimeError(
            f"{job['job_id']}: generated events {generated} != {job['events']}"
        )
    if Path(header_geometry).resolve() != Path(job["expected_geometry"]).resolve():
        raise RuntimeError(f"{job['job_id']}: SIM geometry differs: {header_geometry}")
    if header_seed != int(job["seed"]):
        raise RuntimeError(f"{job['job_id']}: SIM seed differs: {header_seed}")
    if terminal_en != 1:
        raise RuntimeError(f"{job['job_id']}: SIM terminal EN count {terminal_en} != 1")

    catalog.update(extras)
    catalog["n_generated_events_seen"] = generated
    catalog["active_only_events"] = active_only
    cache_path = Path(cache_dir) / f"job_{int(job['scan_index']):04d}.pkl"
    with cache_path.open("xb") as handle:
        pickle.dump(catalog, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return {
        "scan_index": int(job["scan_index"]),
        "path": str(cache_path),
        "geometry": job["geometry"],
        "family": job["family"],
        "generated_events": generated,
        "tes_positive_events": len(catalog["stream"]),
        "active_only_events": active_only,
        "pixel_hits": len(catalog["pix_e"]),
        "header_geometry": header_geometry,
        "header_seed": header_seed,
        "terminal_en": terminal_en,
        "semantic_sim_scans": 1,
        "w_deposit_events": w_deposit_events,
        "w_deposit_keV_sum": w_deposit_keV_sum,
        "w_first_interaction_events": w_first_interaction_events,
        "w_pair_events": w_pair_events,
        "w_annihilation_events": w_annihilation_events,
        "pair_ia_count": pair_ia_count,
        "w_pair_ia_count": w_pair_ia_count,
        "pair_ia_unresolved_count": pair_ia_unresolved_count,
        "annihilation_ia_count": annihilation_ia_count,
        "w_annihilation_ia_count": w_annihilation_ia_count,
        "annihilation_ia_unresolved_count": annihilation_ia_unresolved_count,
    }


def merge_cell(
    jobs: list[dict[str, Any]],
    results: dict[int, dict[str, Any]],
    target: Path,
    veto_policy: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    parser = old_parser()
    merged = parser.empty_catalog()
    extra_names = (
        "input_id", "batch_id", "job_name", "seed", "plastic_total_keV",
        "has_pair_ia", "has_annihilation_ia", "w_total_keV",
        "first_interaction_volume", "first_interaction_resolution",
        "first_interaction_in_passive_w", "w_pair_ia_count",
        "w_annihilation_ia_count", "pair_ia_unresolved_count",
        "annihilation_ia_unresolved_count",
    )
    extras = {name: [] for name in extra_names}
    active_only = 0
    for job in jobs:
        with Path(results[int(job["scan_index"])]["path"]).open("rb") as handle:
            catalog = pickle.load(handle)
        parser.merge_one_catalog_into(merged, catalog)
        for name in extra_names:
            extras[name].extend(catalog[name])
        active_only += int(catalog["active_only_events"])
    merged.update(extras)
    tt_s = math.fsum(float(job["TT_s"]) for job in jobs)
    if tt_s <= 0.0:
        raise RuntimeError(f"non-positive family TT: {jobs[0]['family']}")
    weight = 1.0 / tt_s
    merged["rate_hz"] = [weight] * len(merged["stream"])
    merged["generated_events"] = sum(int(job["events"]) for job in jobs)
    merged["active_only_events"] = active_only
    merged["active_only_rate_hz"] = active_only * weight
    merged["cell_metadata"] = {
        "geometry": "SF3",
        "family": jobs[0]["family"],
        "mode": "instant",
        "jobs": len(jobs),
        "generated_events": merged["generated_events"],
        "TT_s": tt_s,
        "event_weight_cps": weight,
        "veto_policy": veto_policy,
        "response_geometry_key": CORE_GEOMETRY["SF3"],
        "authority_status": "SF3_PLAN1_PROMPT_CANONICAL_RECEIPTS_COMPLETE",
        "normalization": "selected events / sum(TT) within SF3 x instant x family",
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        pickle.dump(merged, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return merged, merged["cell_metadata"]


def in_window(value: float, bounds: tuple[float, float]) -> bool:
    return bounds[0] <= value < bounds[1]


def topology_keep(hits: list[Any], step05: Any, disk: dict[str, Any]) -> tuple[bool, str]:
    if len(hits) == 1:
        return True, "single"
    if len(hits) > int(step05.MAX_ENUM_HITS):
        return True, "reject_kept"
    return step05.side_keep_from_hits(hits, disk, "keep")


def evaluate_event(
    catalog: dict[str, Any],
    event_index: int,
    core: Any,
    step05: Any,
    disk: dict[str, Any],
) -> dict[str, Any]:
    """Apply keyed response, explicit six-volume veto, and retained Step05."""
    meta = catalog["cell_metadata"]
    geometry = str(meta["geometry"])
    family = str(meta["family"])
    mode = str(meta.get("mode", "instant"))
    policy = meta.get("veto_policy")
    if not isinstance(policy, dict):
        raise RuntimeError(f"catalog lacks explicit veto policy: {geometry}/{family}")
    core_geometry = str(meta.get("response_geometry_key", CORE_GEOMETRY[geometry]))
    start = int(catalog["pix_start"][event_index])
    stop = start + int(catalog["pix_count"][event_index])
    raw_hits: list[Any] = []
    measured_hits: list[Any] = []
    for hit_index in range(start, stop):
        energy = float(catalog["pix_e"][hit_index])
        uid = str(catalog["pix_uid"][hit_index])
        common = {
            "x": float(catalog["pix_x"][hit_index]),
            "y": float(catalog["pix_y"][hit_index]),
            "z": float(catalog["pix_z"][hit_index]),
            "pixel_uid": uid,
            "layer": int(catalog["pix_layer"][hit_index]),
        }
        raw_hits.append(SimpleNamespace(e=energy, **common))
        measured = energy + core.SIGMA_KEV * core.keyed_standard_normal(
            core_geometry,
            mode,
            family,
            catalog["batch_id"][event_index],
            int(catalog["seed"][event_index]),
            catalog["job_name"][event_index],
            int(catalog["local_id"][event_index]),
            uid,
        )
        if measured >= core.PIXEL_THRESHOLD_KEV:
            measured_hits.append(SimpleNamespace(e=measured, **common))

    shield_keV = float(catalog["bgo_total_keV"][event_index])
    plastic_keV = float(catalog["plastic_total_keV"][event_index])
    plastic_pass = (
        not bool(policy["apply_plastic_veto"])
        or plastic_keV < float(policy["plastic_threshold_keV"])
    )
    active_pass = {
        threshold: shield_keV < threshold and plastic_pass
        for threshold in VETO_THRESHOLDS_KEV
    }
    measured_total = math.fsum(hit.e for hit in measured_hits)
    topology_pass = False
    topology_class = "not_evaluated"
    if active_pass[50.0] and in_window(measured_total, WINDOWS["broad_480_550"]):
        topology_pass, topology_class = topology_keep(measured_hits, step05, disk)
    return {
        "raw_hits": raw_hits,
        "measured_hits": measured_hits,
        "raw_total_keV": math.fsum(hit.e for hit in raw_hits),
        "measured_total_keV": measured_total,
        "shield_keV": shield_keV,
        "plastic_keV": plastic_keV,
        "active_pass": active_pass,
        "topology_pass": topology_pass,
        "topology_class": topology_class,
    }


def evaluate_cell(
    catalog: dict[str, Any], core: Any, step05: Any, disk: dict[str, Any]
) -> tuple[
    list[dict[str, Any]],
    dict[tuple[str, str, int], tuple[int, float, float]],
    dict[str, Any],
]:
    meta = catalog["cell_metadata"]
    geometry = str(meta["geometry"])
    family = str(meta["family"])
    mode = str(meta.get("mode", "instant"))
    normalization_time_s = float(meta["TT_s"])
    weight = float(meta.get("event_weight_cps", 1.0 / normalization_time_s))
    counts: Counter[tuple[str, str, str]] = Counter()
    spectrum_counts: Counter[tuple[str, str, int]] = Counter()
    topology_classes: Counter[str] = Counter()
    n_bins = int(round((SPECTRUM_HI_KEV - SPECTRUM_LO_KEV) / SPECTRUM_BIN_KEV))

    for event_index in range(len(catalog["stream"])):
        event = evaluate_event(catalog, event_index, core, step05, disk)
        responses = {"raw": event["raw_hits"], "measured": event["measured_hits"]}
        if event["topology_class"] != "not_evaluated":
            topology_classes[str(event["topology_class"])] += 1
        for response, hits in responses.items():
            total = math.fsum(hit.e for hit in hits)
            stage_flags = {
                "pre_veto": True,
                "active_veto50": event["active_pass"][50.0],
                "active_veto70": event["active_pass"][70.0],
                "active_veto80": event["active_pass"][80.0],
            }
            if response == "measured":
                stage_flags["side_compton_fov_pass"] = (
                    event["active_pass"][50.0] and bool(event["topology_pass"])
                )
            for stage, passes in stage_flags.items():
                if not passes:
                    continue
                for window_id, bounds in WINDOWS.items():
                    if in_window(total, bounds):
                        counts[(response, stage, window_id)] += 1
                if SPECTRUM_LO_KEV <= total < SPECTRUM_HI_KEV:
                    bin_index = int((total - SPECTRUM_LO_KEV) / SPECTRUM_BIN_KEV)
                    if 0 <= bin_index < n_bins:
                        spectrum_counts[(response, stage, bin_index)] += 1

    cutflow: list[dict[str, Any]] = []
    for response in ("raw", "measured"):
        stages = ["pre_veto", "active_veto50", "active_veto70", "active_veto80"]
        if response == "measured":
            stages.append("side_compton_fov_pass")
        for stage in stages:
            for window_id, bounds in WINDOWS.items():
                count = int(counts[(response, stage, window_id)])
                low, high = core.gamma.garwood_interval(count)
                cutflow.append({
                    "geometry": geometry,
                    "family": family,
                    "mode": mode,
                    "response_state": response,
                    "stage": stage,
                    "window_id": window_id,
                    "energy_lo_keV": bounds[0],
                    "energy_hi_keV": bounds[1],
                    "generated_events": int(meta["generated_events"]),
                    "TT_s": normalization_time_s,
                    "selected_events": count,
                    "event_weight_cps": weight,
                    "rate_cps": count * weight,
                    "rate_stat_sigma_cps": math.sqrt(count) * weight,
                    "rate_lower95_cps": low * weight,
                    "rate_upper95_cps": high * weight,
                    "authority_status": meta["authority_status"],
                })
    spectrum = {
        key: (int(value), value * weight, value * weight * weight)
        for key, value in spectrum_counts.items()
    }
    occupancy = {
        "geometry": geometry,
        "family": family,
        "generated_events": int(meta["generated_events"]),
        "TT_s": normalization_time_s,
        "detector_occupancy_events": len(catalog["stream"]) + int(catalog["active_only_events"]),
        "tes_positive_events": len(catalog["stream"]),
        "active_only_events": int(catalog["active_only_events"]),
        "pixel_hits": len(catalog["pix_e"]),
        "fullband_rate_cps": (
            len(catalog["stream"]) + int(catalog["active_only_events"])
        ) * weight,
        "tes_rate_cps": len(catalog["stream"]) * weight,
        "active_only_rate_cps": int(catalog["active_only_events"]) * weight,
        "rate_stat_sigma_cps": math.sqrt(
            len(catalog["stream"]) + int(catalog["active_only_events"])
        ) * weight,
        "topology_class_counts_json": json.dumps(
            dict(sorted(topology_classes.items())), separators=(",", ":")
        ),
    }
    return cutflow, spectrum, occupancy


def aggregate_spectrum(
    pieces: list[tuple[str, dict[tuple[str, str, int], tuple[int, float, float]]]]
) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str, str, int], list[float]] = defaultdict(
        lambda: [0.0, 0.0, 0.0]
    )
    for geometry, piece in pieces:
        for (response, stage, bin_index), (events, rate, variance) in piece.items():
            target = totals[(geometry, response, stage, bin_index)]
            target[0] += events
            target[1] += rate
            target[2] += variance
    rows: list[dict[str, Any]] = []
    n_bins = int(round((SPECTRUM_HI_KEV - SPECTRUM_LO_KEV) / SPECTRUM_BIN_KEV))
    for geometry in GEOMETRY_ORDER:
        for response, stages in (
            ("raw", ("pre_veto", "active_veto50")),
            ("measured", ("pre_veto", "active_veto50", "side_compton_fov_pass")),
        ):
            for stage in stages:
                for bin_index in range(n_bins):
                    events, rate, variance = totals[(geometry, response, stage, bin_index)]
                    lo = SPECTRUM_LO_KEV + bin_index * SPECTRUM_BIN_KEV
                    rows.append({
                        "geometry": geometry,
                        "response_state": response,
                        "stage": stage,
                        "energy_lo_keV": lo,
                        "energy_hi_keV": lo + SPECTRUM_BIN_KEV,
                        "energy_center_keV": lo + 0.5 * SPECTRUM_BIN_KEV,
                        "events_per_bin": int(events),
                        "rate_cps_per_keV": rate / SPECTRUM_BIN_KEV,
                        "rate_stat_sigma_cps_per_keV": math.sqrt(variance) / SPECTRUM_BIN_KEV,
                    })
    return rows


def geometry_summary(cutflow: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(
        lambda: {"events": 0.0, "rate": 0.0, "variance": 0.0}
    )
    for row in cutflow:
        key = (row["geometry"], row["response_state"], row["stage"], row["window_id"])
        totals[key]["events"] += int(row["selected_events"])
        totals[key]["rate"] += float(row["rate_cps"])
        totals[key]["variance"] += float(row["rate_stat_sigma_cps"]) ** 2
    rows: list[dict[str, Any]] = []
    for key in sorted(totals, key=lambda value: (value[0], value[1], value[2], value[3])):
        value = totals[key]
        rows.append({
            "geometry": key[0],
            "response_state": key[1],
            "stage": key[2],
            "window_id": key[3],
            "descriptive_selected_events_across_families": int(value["events"]),
            "rate_cps_sum_of_family_rates": value["rate"],
            "rate_stat_sigma_cps_quadrature": math.sqrt(value["variance"]),
        })
    return rows


def response_runtime(config: dict[str, Any]) -> tuple[Any, Any, dict[str, Any]]:
    wrapper = load_module("sf3_corrected_response_core", CORRECTED_CORE)
    core = wrapper.core
    if not math.isclose(float(core.FWHM_KEV), float(config["analysis"]["response_fwhm_keV"]), abs_tol=1e-15):
        raise RuntimeError("retained response FWHM differs from SF3 config")
    if not math.isclose(
        float(core.PIXEL_THRESHOLD_KEV),
        float(config["analysis"]["measured_pixel_threshold_keV"]),
        abs_tol=1e-15,
    ):
        raise RuntimeError("retained response pixel threshold differs from SF3 config")
    step05 = load_module("sf3_retained_step05", STEP05)
    step05.ROOT = SOURCE_WORKTREE
    step05.STEP09_SUMMARY = STEP09_SUMMARY
    return core, step05, step05.side_entry_disk()


def build_report(
    summary_rows: list[dict[str, Any]],
    histories: int,
    jobs: int,
    w_summary: dict[str, Any],
) -> str:
    wanted = {
        (row["stage"], row["window_id"]): row
        for row in summary_rows if row["response_state"] == "measured"
    }

    def cell(stage: str, window: str) -> str:
        row = wanted[(stage, window)]
        return (
            f"{int(row['descriptive_selected_events_across_families'])} "
            f"({row['rate_cps_sum_of_family_rates']:.8g} cps)"
        )

    return "\n".join([
        "# SF3 Plan-1 corrected-keV prompt analysis",
        "",
        f"Status: `PASS__SF3_PLAN1_PROMPT_COMPLETE`",
        "",
        f"The stage consumed {jobs:,} canonical PASS instant receipts and {histories:,} histories.",
        "Each rich SIM was decompressed once and was not hashed. Rates are count/sum(TT) inside each incident-family cell before family rates are added.",
        "",
        "| Geometry | 480–550 measured | after explicit 50-keV veto | after Step05 | W2 measured | after veto | after Step05 |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| SF3 | {cell('pre_veto', 'broad_480_550')} | {cell('active_veto50', 'broad_480_550')} | {cell('side_compton_fov_pass', 'broad_480_550')} | {cell('pre_veto', 'w2_510p58_511p42')} | {cell('active_veto50', 'w2_510p58_511p42')} | {cell('side_compton_fov_pass', 'w2_510p58_511p42')} |",
        "",
        (
            f"Passive-W diagnostics found {w_summary['w_deposit_events']:,} events with a "
            f"recorded W deposit and {w_summary['w_first_interaction_events']:,} events whose "
            "first resolvable primary interaction was in one of the three near-field W volumes. "
            f"Resolved W-local PAIR/ANNI counts are {w_summary['w_pair_ia_count']:,}/"
            f"{w_summary['w_annihilation_ia_count']:,}; unresolved IA counts are retained separately."
        ),
        "The veto is an explicit three-BGO plus three-plastic policy. The three W volumes are passive diagnostics only and never enter BGO/plastic veto energy. This is prompt/common-response input authority, not delayed, mission, F3, or geometry-promotion authority.",
        "",
    ])


def self_test() -> dict[str, Any]:
    """Exercise passive-W/IA matching contracts without opening a SIM."""
    config = {
        "geometry": {
            "passive_w_volumes": list(PASSIVE_W_VOLUMES),
            "passive_w_never_active_veto": True,
            "active_veto_volumes": ["BGO_A", "BGO_B", "BGO_C", "P_A", "P_B", "P_C"],
        }
    }
    if passive_w_volumes(config) != PASSIVE_W_VOLUMES:
        raise AssertionError("passive-W self-test closure failed")
    interaction = parse_ia("IA PAIR 2;1;0;1e-09;0;0;0")
    hit = {"volume": PASSIVE_W_VOLUMES[0], "time_s": 1.0e-9, "sproc": "conv"}
    diagnostic = event_w_diagnostics(
        [interaction] if interaction is not None else [], [hit], [hit], set(PASSIVE_W_VOLUMES)
    )
    if not diagnostic["first_interaction_in_passive_w"]:
        raise AssertionError("first-interaction W matching self-test failed")
    if diagnostic["w_pair_ia_count"] != 1 or diagnostic["pair_ia_unresolved_count"] != 0:
        raise AssertionError("W-local PAIR matching self-test failed")

    def reference_event_w_diagnostics(
        interactions: list[dict[str, Any]],
        primary_hits: list[dict[str, Any]],
        all_meta_hits: list[dict[str, Any]],
        passive_w: set[str],
    ) -> dict[str, Any]:
        """Pre-index implementation retained locally as a differential oracle."""
        first = min(
            (item for item in interactions if int(item["parent_id"]) == 1),
            key=lambda item: (float(item["time_s"]), int(item["interaction_id"])),
            default=None,
        )
        first_volume, first_resolution = match_ia_volume(first, primary_hits)
        result: dict[str, Any] = {
            "first_interaction_volume": first_volume,
            "first_interaction_resolution": first_resolution,
            "first_interaction_in_passive_w": first_volume in passive_w,
        }
        for process, prefix in (("PAIR", "pair"), ("ANNI", "annihilation")):
            items = [item for item in interactions if item["process"] == process]
            resolved = [match_ia_volume(item, all_meta_hits) for item in items]
            result[f"{prefix}_ia_count"] = len(items)
            result[f"w_{prefix}_ia_count"] = sum(
                volume in passive_w for volume, _ in resolved
            )
            result[f"{prefix}_ia_unresolved_count"] = sum(
                not volume for volume, _ in resolved
            )
        return result

    def assert_index_matches_reference(
        hits: list[dict[str, Any]],
        queries: list[dict[str, Any]],
    ) -> int:
        index = _StableHitTimeIndex(
            hits, {str(query["process"]).upper() for query in queries}
        )
        for query in queries:
            reference = match_ia_volume(query, hits)
            indexed = index.match(query)
            if indexed != reference:
                raise AssertionError(
                    f"indexed IA match differs: query={query!r}, "
                    f"reference={reference!r}, indexed={indexed!r}"
                )
        return len(queries)

    # Explicit preferred-alias, time-only fallback, inclusive-boundary,
    # duplicate-time, signed-zero, and original-order tie cases.
    query_time = 1.0
    tolerance = max(5.0e-15, abs(query_time) * 2.0e-5)
    tie_high = {
        "volume": "TIE_HIGH_FIRST", "time_s": 2.5e-15,
        "sproc": "conv",
    }
    tie_low = {
        "volume": "TIE_LOW_SECOND", "time_s": -2.5e-15,
        "sproc": "pair",
    }
    tie_query = {"process": "PAIR", "time_s": 0.0}
    if match_ia_volume(tie_query, [tie_high, tie_low])[0] != "TIE_HIGH_FIRST":
        raise AssertionError("linear reference original-order tie contract changed")
    differential_match_cases = assert_index_matches_reference(
        [tie_high, tie_low], [tie_query]
    )
    explicit_hits = [
        {"volume": "PAIR_NEAR_HIGH", "time_s": query_time + tolerance * 0.5,
         "sproc": "conv"},
        {"volume": "PAIR_NEAR_LOW", "time_s": query_time - tolerance * 0.5,
         "sproc": "pair"},
        {"volume": "TIME_ONLY_CLOSER", "time_s": query_time, "sproc": "other"},
        {"volume": "LOW_EDGE", "time_s": query_time - tolerance, "sproc": "phot"},
        {
            "volume": "LOW_OUTSIDE",
            "time_s": math.nextafter(query_time - tolerance, -math.inf),
            "sproc": "rayl",
        },
        {"volume": "HIGH_EDGE", "time_s": query_time + tolerance, "sproc": "anni"},
        {
            "volume": "HIGH_OUTSIDE",
            "time_s": math.nextafter(query_time + tolerance, math.inf),
            "sproc": "annihilation",
        },
        {"volume": "ZERO_FIRST", "time_s": -0.0, "sproc": "conv"},
        {"volume": "ZERO_SECOND", "time_s": 0.0, "sproc": "pair"},
    ]
    explicit_queries = [
        tie_query,
        {"process": "BREM", "time_s": query_time},
        {"process": "PHOT", "time_s": query_time},
        {"process": "RAYL", "time_s": query_time},
        {"process": "ANNI", "time_s": query_time},
        {"process": "PAIR", "time_s": 0.0},
    ]
    differential_match_cases += assert_index_matches_reference(
        explicit_hits, explicit_queries
    )

    alias_fallback_hits = [
        {"volume": "FALLBACK", "time_s": query_time, "sproc": "unaliased"}
    ]
    alias_fallback_query = {"process": "PAIR", "time_s": query_time}
    if match_ia_volume(alias_fallback_query, alias_fallback_hits)[0] != "FALLBACK":
        raise AssertionError("linear reference time-only fallback contract changed")
    differential_match_cases += assert_index_matches_reference(
        alias_fallback_hits, [alias_fallback_query]
    )

    rng = random.Random(0x5F3)
    labels = (
        "compt", "phot", "rayl", "conv", "pair", "anni", "annih",
        "annihilation", "unaliased", "PAIR",
    )
    processes = tuple(_IA_PROCESS_ALIASES) + ("BREM", "ELAS")
    anchors = (0.0, 1.0e-12, 1.0e-9, 1.0, -1.0, 1.0e6)
    passive = {PASSIVE_W_VOLUMES[0], PASSIVE_W_VOLUMES[1], PASSIVE_W_VOLUMES[2]}
    differential_event_cases = 0
    for case_index in range(300):
        anchor = rng.choice(anchors)
        scale = max(5.0e-15, abs(anchor) * 2.0e-5)
        hits: list[dict[str, Any]] = []
        for hit_index in range(rng.randrange(0, 48)):
            displacement = rng.choice(
                (-2.0, -1.0, -0.5, 0.0, 0.0, 0.5, 1.0, 2.0, rng.uniform(-3.0, 3.0))
            )
            volume = (
                PASSIVE_W_VOLUMES[hit_index % len(PASSIVE_W_VOLUMES)]
                if hit_index % 7 == 0 else f"SYNTHETIC_VOLUME_{hit_index % 11}"
            )
            hits.append({
                "volume": volume,
                "time_s": anchor + displacement * scale,
                "sproc": rng.choice(labels),
            })
        rng.shuffle(hits)

        queries = [{
            "process": rng.choice(processes),
            "time_s": anchor + rng.choice(
                (-1.0, -0.5, 0.0, 0.5, 1.0, rng.uniform(-2.0, 2.0))
            ) * scale,
        } for _ in range(4)]
        differential_match_cases += assert_index_matches_reference(hits, queries)

        interactions = [{
            "process": rng.choice(processes),
            "time_s": anchor + rng.choice(
                (-1.0, 0.0, 0.0, 0.5, 1.0, rng.uniform(-2.0, 2.0))
            ) * scale,
            "parent_id": rng.randrange(1, 4),
            "interaction_id": interaction_index + 1,
        } for interaction_index in range(rng.randrange(0, 18))]
        primary_hits = [hit for hit in hits if rng.random() < 0.35]
        reference = reference_event_w_diagnostics(
            interactions, primary_hits, hits, passive
        )
        indexed = event_w_diagnostics(interactions, primary_hits, hits, passive)
        if indexed != reference:
            raise AssertionError(
                f"event differential differs at case {case_index}: "
                f"reference={reference!r}, indexed={indexed!r}"
            )
        differential_event_cases += 1

    # Accepted non-finite floats are routed to the untouched linear reference.
    nonfinite_hits = [
        {"volume": "FINITE", "time_s": 0.0, "sproc": "conv"},
        {"volume": "INFINITE", "time_s": math.inf, "sproc": "pair"},
    ]
    nonfinite_queries = [
        {"process": "PAIR", "time_s": 0.0},
        {"process": "PAIR", "time_s": math.inf},
        {"process": "PAIR", "time_s": math.nan},
    ]
    differential_match_cases += assert_index_matches_reference(
        nonfinite_hits, nonfinite_queries
    )
    nonfinite_event_interactions = [
        {
            "process": "PAIR", "time_s": 0.0, "parent_id": 1,
            "interaction_id": 1,
        },
        {
            "process": "BREM", "time_s": math.inf, "parent_id": 2,
            "interaction_id": 2,
        },
    ]
    nonfinite_event_reference = reference_event_w_diagnostics(
        nonfinite_event_interactions, nonfinite_hits[:1], nonfinite_hits, passive
    )
    nonfinite_event_indexed = event_w_diagnostics(
        nonfinite_event_interactions, nonfinite_hits[:1], nonfinite_hits, passive
    )
    if nonfinite_event_indexed != nonfinite_event_reference:
        raise AssertionError("non-finite event fallback differs from the linear reference")
    differential_event_cases += 1

    # Large enough that the former Q x H scan is conspicuous, while the
    # event-local index remains a sub-second synthetic check on normal hosts.
    large_hit_count = 20_000
    large_query_count = 1_200
    large_base_time = 1.0e-6
    large_hits = [{
        "volume": (
            PASSIVE_W_VOLUMES[index % len(PASSIVE_W_VOLUMES)]
            if index % 29 == 0 else f"LARGE_VOLUME_{index % 17}"
        ),
        "time_s": large_base_time + (
            ((index * 7_919) % 20_001) - 10_000
        ) * 1.0e-15,
        "sproc": ("conv", "pair", "anni", "phot")[index % 4],
    } for index in range(large_hit_count)]
    large_interactions = [{
        "process": "COMP",
        "time_s": large_base_time,
        "parent_id": 1,
        "interaction_id": 1,
    }] + [{
        "process": "PAIR",
        "time_s": large_base_time + (index % 101 - 50) * 1.0e-15,
        "parent_id": 2,
        "interaction_id": index + 2,
    } for index in range(large_query_count)]
    large_primary_hits = large_hits[:64]
    sample_interactions = large_interactions[:17]
    if event_w_diagnostics(
        sample_interactions, large_primary_hits, large_hits, passive
    ) != reference_event_w_diagnostics(
        sample_interactions, large_primary_hits, large_hits, passive
    ):
        raise AssertionError("large synthetic sample differs from the linear reference")
    performance_started = time.perf_counter()
    large_result = event_w_diagnostics(
        large_interactions, large_primary_hits, large_hits, passive
    )
    performance_elapsed_s = time.perf_counter() - performance_started
    if large_result["pair_ia_count"] != large_query_count:
        raise AssertionError("large synthetic PAIR count differs")
    performance_limit_s = 2.0
    if performance_elapsed_s >= performance_limit_s:
        raise AssertionError(
            f"indexed large-event performance regression: {performance_elapsed_s:.6f}s "
            f">= {performance_limit_s:.1f}s"
        )

    return {
        "schema_version": 1,
        "status": "PASS__SF3_PROMPT_W_DIAGNOSTICS_SELF_TEST",
        "checks": [
            "three_W_volumes_passive_and_disjoint",
            "first_primary_IA_to_CC_HIT_time_process_match",
            "W_local_PAIR_match_with_unresolved_counter",
            "stable_bisect_matches_linear_reference_for_float_alias_fallback_and_order_ties",
            "nonfinite_event_uses_linear_reference",
            "large_synthetic_event_avoids_Q_times_H_scan",
        ],
        "differential": {
            "match_cases": differential_match_cases,
            "event_cases": differential_event_cases,
            "seed": "0x5F3",
        },
        "large_synthetic_performance": {
            "hits": large_hit_count,
            "pair_queries": large_query_count,
            "elapsed_s": performance_elapsed_s,
            "limit_s": performance_limit_s,
        },
        "sim_opened": False,
    }


def run(config_path: Path, output: Path, workers: int) -> dict[str, Any]:
    config, jobs, prerequisites = selected_instant_jobs(config_path)
    max_workers = int(config["transport"].get(
        "max_cpu_budget", config["transport"]["cpu_budget"]
    ))
    if workers < 1 or workers > max_workers:
        raise ValueError(f"workers must be within 1..{max_workers}")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite prompt output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    cache_dir = work / "job_cache"
    cache_dir.mkdir()
    started = time.monotonic()
    results: dict[int, dict[str, Any]] = {}
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(scan_job, job, str(cache_dir)): job for job in jobs}
            for completed, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                results[int(result["scan_index"])] = result
                print(json.dumps({
                    "event": "prompt_sim_scanned_once",
                    "completed": completed,
                    "total": len(jobs),
                    "job_id": futures[future]["job_id"],
                    "generated_events": result["generated_events"],
                }, sort_keys=True), flush=True)

        if len(results) != len(jobs) or sum(row["semantic_sim_scans"] for row in results.values()) != len(jobs):
            raise RuntimeError("one-pass SIM scan closure failed")
        core, step05, disk = response_runtime(config)
        policy = explicit_veto_policy(config)
        jobs_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for job in jobs:
            jobs_by_family[job["family"]].append(job)

        cutflow: list[dict[str, Any]] = []
        occupancy: list[dict[str, Any]] = []
        coverage: list[dict[str, Any]] = []
        spectrum_pieces: list[
            tuple[str, dict[tuple[str, str, int], tuple[int, float, float]]]
        ] = []
        for family in FAMILY_ORDER:
            cell_jobs = jobs_by_family[family]
            target = work / "catalog" / "SF3" / f"{family}.pkl"
            catalog, metadata = merge_cell(cell_jobs, results, target, policy)
            cell_cutflow, cell_spectrum, cell_occupancy = evaluate_cell(
                catalog, core, step05, disk
            )
            cutflow.extend(cell_cutflow)
            spectrum_pieces.append(("SF3", cell_spectrum))
            occupancy.append(cell_occupancy)
            cell_results = [results[int(job["scan_index"])] for job in cell_jobs]
            coverage.append({
                "geometry": "SF3",
                "family": family,
                "completeness_status": "CANONICAL_PASS_RECEIPTS_AND_SINGLE_SEMANTIC_SCAN",
                "jobs": metadata["jobs"],
                "generated_events": metadata["generated_events"],
                "TT_s": metadata["TT_s"],
                "tes_positive_events": len(catalog["stream"]),
                "active_only_events": catalog["active_only_events"],
                "pixel_hits": len(catalog["pix_e"]),
                "w_deposit_events": sum(row["w_deposit_events"] for row in cell_results),
                "w_deposit_keV_sum": math.fsum(
                    float(row["w_deposit_keV_sum"]) for row in cell_results
                ),
                "w_first_interaction_events": sum(
                    row["w_first_interaction_events"] for row in cell_results
                ),
                "w_pair_ia_count": sum(row["w_pair_ia_count"] for row in cell_results),
                "w_annihilation_ia_count": sum(
                    row["w_annihilation_ia_count"] for row in cell_results
                ),
                "event_weight_cps": metadata["event_weight_cps"],
                "catalog_path": display_path(output / "catalog" / "SF3" / f"{family}.pkl"),
            })

        spectrum = aggregate_spectrum(spectrum_pieces)
        summary_rows = geometry_summary(cutflow)
        w_rows = [{
            "geometry": "SF3",
            "family": job["family"],
            "job_id": job["job_id"],
            "generated_events": results[int(job["scan_index"])]["generated_events"],
            "tes_positive_events": results[int(job["scan_index"])]["tes_positive_events"],
            "w_deposit_events": results[int(job["scan_index"])]["w_deposit_events"],
            "w_deposit_keV_sum": results[int(job["scan_index"])]["w_deposit_keV_sum"],
            "w_first_interaction_events": results[int(job["scan_index"])][
                "w_first_interaction_events"
            ],
            "pair_ia_count": results[int(job["scan_index"])]["pair_ia_count"],
            "w_pair_ia_count": results[int(job["scan_index"])]["w_pair_ia_count"],
            "pair_ia_unresolved_count": results[int(job["scan_index"])][
                "pair_ia_unresolved_count"
            ],
            "annihilation_ia_count": results[int(job["scan_index"])]["annihilation_ia_count"],
            "w_annihilation_ia_count": results[int(job["scan_index"])][
                "w_annihilation_ia_count"
            ],
            "annihilation_ia_unresolved_count": results[int(job["scan_index"])][
                "annihilation_ia_unresolved_count"
            ],
            "passive_w_volumes_json": json.dumps(
                list(PASSIVE_W_VOLUMES), separators=(",", ":")
            ),
            "veto_role": "PASSIVE_DIAGNOSTIC_ONLY__NOT_BGO_OR_PLASTIC_VETO",
        } for job in jobs]
        w_summary = {
            key: (
                math.fsum(float(row[key]) for row in w_rows)
                if key == "w_deposit_keV_sum"
                else sum(int(row[key]) for row in w_rows)
            )
            for key in (
                "w_deposit_events", "w_deposit_keV_sum", "w_first_interaction_events",
                "pair_ia_count", "w_pair_ia_count", "pair_ia_unresolved_count",
                "annihilation_ia_count", "w_annihilation_ia_count",
                "annihilation_ia_unresolved_count",
            )
        }
        w_summary.update({
            "passive_w_volumes": list(PASSIVE_W_VOLUMES),
            "role": "PASSIVE_DIAGNOSTIC_ONLY__STRICTLY_DISJOINT_FROM_SIX_ACTIVE_VETO_VOLUMES",
            "first_interaction_method": (
                "FIRST_PARENT_ID_1_IA_MATCHED_TO_PRIMARY_CC_HIT_BY_TIME_AND_PROCESS"
            ),
            "pair_annihilation_locality_method": (
                "IA_MATCHED_TO_RECORDED_CC_HIT_BY_TIME_AND_PROCESS__UNRESOLVED_REPORTED_SEPARATELY"
            ),
        })
        input_manifest = [{
            "input_id": job["input_id"],
            "receipt_path": job["receipt_path"],
            "geometry": "SF3",
            "family": job["family"],
            "mode": "instant",
            "job_id": job["job_id"],
            "seed": job["seed"],
            "events": job["events"],
            "TT_s": job["TT_s"],
            "sim_path": job["sim_path"],
            "sim_bytes": job["receipt_sim_bytes"],
            "semantic_sim_scans": 1,
            "sim_hash_recomputed": False,
        } for job in jobs]
        write_csv(work / "prompt_input_manifest.csv", input_manifest)
        write_csv(work / "prompt_cell_coverage.csv", coverage)
        write_csv(work / "prompt_cutflow.csv", cutflow)
        write_csv(work / "prompt_spectrum_480_550.csv", spectrum)
        write_csv(work / "prompt_fullband_occupancy.csv", occupancy)
        write_csv(work / "prompt_geometry_summary.csv", summary_rows)
        write_csv(work / "prompt_w_diagnostics.csv", w_rows)

        selected_histories = sum(int(job["events"]) for job in jobs)
        summary = {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "PASS__SF3_PLAN1_PROMPT_COMPLETE",
            "scope": "SF3 corrected-keV instant prompt; eight incident families",
            "selected_jobs": len(jobs),
            "selected_histories": selected_histories,
            "response": {
                "fwhm_keV": float(core.FWHM_KEV),
                "pixel_threshold_keV": float(core.PIXEL_THRESHOLD_KEV),
                "rng_namespace": str(core.RESPONSE_NAMESPACE),
                "response_geometry_key": CORE_GEOMETRY["SF3"],
                "rng": "retained keyed Box-Muller response",
            },
            "energy_windows_keV": {key: list(value) for key, value in WINDOWS.items()},
            "active_veto": policy,
            "passive_w_diagnostics": w_summary,
            "compton_fov": {
                "implementation": str(STEP05),
                "policy": "retained side_keep_from_hits; reject_policy=keep",
            },
            "normalization": "count/sum(TT) per SF3 x instant x family; family rates summed",
            "sim_scan_policy": {
                "selected_sim_count": len(jobs),
                "semantic_scans": len(jobs),
                "scans_per_sim": 1,
                "sim_hashes_recomputed": 0,
            },
            "gamma_model": "unit_only_total_gamma broadband; no additive mono-511",
            "receipt_prerequisite_status": prerequisites["status"],
            "geometry_summary": summary_rows,
            "elapsed_s": time.monotonic() - started,
            "authority_boundary": "PROMPT_AND_COMMON_RESPONSE_INPUT_ONLY__NOT_ACTIVATION_DELAYED_MISSION_F3_OR_GEOMETRY_PROMOTION_AUTHORITY",
        }
        write_json(work / "summary.json", summary)
        (work / "REPORT.md").write_text(
            build_report(summary_rows, selected_histories, len(jobs), w_summary),
            encoding="utf-8",
        )
        shutil.rmtree(cache_dir)
        files = sorted(path for path in work.rglob("*") if path.is_file())
        manifest = {
            "schema_version": 1,
            "status": summary["status"],
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "analysis_code": display_path(HERE),
            "reused_code": [
                str(OLD_CATALOG_PARSER), str(CORRECTED_CORE), str(STEP05),
            ],
            "files": [
                {"path": str(path.relative_to(work)), "bytes": path.stat().st_size}
                for path in files
            ],
            "hash_note": "No rich SIM payload hash was computed; every selected SIM was semantically scanned once.",
        }
        write_json(work / "manifest.json", manifest)
        os.rename(work, output)
        print(json.dumps({
            "status": summary["status"],
            "jobs": len(jobs),
            "histories": selected_histories,
            "output": str(output),
        }, sort_keys=True))
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--check-prerequisites", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    config_path = args.config.resolve()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return 0
    if args.check_prerequisites:
        result = check_prerequisites(config_path)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ready"] else 2
    config = load_json(config_path)
    output = args.output or Path(config["outputs"]["stage_01"])
    workers = (
        args.workers if args.workers is not None
        else int(config["transport"]["cpu_budget"])
    )
    run(config_path, output.resolve(), workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
