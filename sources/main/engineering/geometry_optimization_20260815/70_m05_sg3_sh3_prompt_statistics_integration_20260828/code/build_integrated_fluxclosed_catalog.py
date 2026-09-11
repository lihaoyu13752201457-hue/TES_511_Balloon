#!/usr/bin/env python3
"""Merge validated prompt supplements into the retained P67 catalogs.

The P67 catalog is the response-level authority.  This program replaces only
the seven ``other/prompt`` family blocks with a uniformly reweighted union of
their retained events and the explicitly listed supplement compact catalogs.
Delayed response, prompt-gamma continuum, and atmospheric-511 response are
copied without changing their event weights or component semantics.

No directory discovery is used for simulation products.  Supplement
membership is determined solely by the explicit model ``jobs.json`` manifests
emitted by the compact builders.  Multiple manifests may be combined so SG3
main and minimal-SD remain separate setup strata while sharing one physical
family exposure denominator.  The output directory must not exist.
"""

from __future__ import annotations

import argparse
import copy
import ctypes
import errno
import hashlib
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


INTEGRATION_SCHEMA = "m05_integrated_fluxclosed_catalog_v1"
SUPPLEMENT_SCHEMA = "m05_supplement_compact_jobs_v1"
DEFERRED_WEIGHT_POLICY = "DEFERRED__UNIFIED_OLD_PLUS_NEW_EXPOSURE"
SUPPLEMENT_SIDECAR_STATUS = "PASS__COMPACT_JOB_CATALOG"
# These two values are an exact P67 consumer contract, not merely labels.
PASS_STATUS = "PASS__FLUXCLOSED_CATALOG_AUDIT"
COMPLETE_STATUS = "COMPLETE__POSITIVE_FLUXCLOSED_EVENT_CATALOG"
INTEGRATION_PASS_STATUS = "PASS__INTEGRATED_PROMPT_STATISTICS"

FAMILIES = (
    "alpha",
    "eminus",
    "eplus",
    "muminus",
    "muplus",
    "n",
    "p",
)
FAMILY_SET = frozenset(FAMILIES)
MODEL_LABEL = {"a": "sg3", "b": "sh3"}
EXPECTED_CANDIDATE = {
    ("a", "main"): "SG3B",
    ("a", "minimal_sd"): "SG3B_MINIMAL_SD",
    ("b", "main"): "SH3_OptV3_60cm",
}
EXPECTED_MANIFEST_STATUS = {
    ("a", "main"): "PASS__M05_SUPPLEMENT_COMPACT_JOBS",
    ("a", "minimal_sd"): "PASS__M05_SG3_MINIMAL_COMPACT_JOBS",
    ("b", "main"): "PASS__M05_SUPPLEMENT_COMPACT_JOBS",
}

HIT_FIELDS = (
    "hit_code",
    "hit_layer",
    "hit_energy_keV",
    "hit_x_cm",
    "hit_y_cm",
    "hit_z_cm",
)
REQUIRED_RESPONSE_FIELDS = (
    "plastic_keV",
    "bgo_keV",
    "measured_total_keV",
    "broad_flags",
    "w2_flags",
    "hit_start",
    "hit_count",
)
GENERATED_EVENT_FIELDS = (
    "event_base_weight_cps",
    "event_component",
    "source_bin80",
    "continuum_importance_weight",
    "event_category",
)

DEFAULT_P67_PACKAGE = Path(
    "/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/"
    "engineering/geometry_optimization_20260815/"
    "67_m05_mono511_flux_closure_20260823"
)
P67_MODEL_DIR = {
    "a": "02_fluxclosed_catalog_a",
    "b": "02_fluxclosed_catalog_b",
}

REL_TOL = 5.0e-10
ABS_TOL = 5.0e-12
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def finite_positive(value: Any, label: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise RuntimeError(f"{label} must be finite and positive, got {value!r}")
    return result


def close(left: float, right: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=REL_TOL, abs_tol=ABS_TOL)


def effective_sample_size(sumw: float, sumw2: float) -> float:
    return sumw * sumw / sumw2 if sumw2 > 0.0 else 0.0


def weight_stats(weights: np.ndarray) -> dict[str, float | int]:
    values = np.asarray(weights, dtype=np.float64)
    if values.ndim != 1:
        raise RuntimeError(f"event weights are not one-dimensional: {values.shape}")
    if len(values) and (
        np.any(~np.isfinite(values)) or np.any(values <= 0.0)
    ):
        raise RuntimeError("event weights must be finite and strictly positive")
    sumw = float(np.sum(values, dtype=np.float64))
    sumw2 = float(np.sum(values * values, dtype=np.float64))
    return {
        "events": int(len(values)),
        "sumw_cps": sumw,
        "sumw2_cps2": sumw2,
        "effective_sample_size": effective_sample_size(sumw, sumw2),
        "minimum_event_weight_cps": (
            float(np.min(values)) if len(values) else None
        ),
        "maximum_event_weight_cps": (
            float(np.max(values)) if len(values) else None
        ),
    }


def require_close(actual: float, expected: float, label: str) -> None:
    if not close(actual, expected):
        raise RuntimeError(f"{label} differs: {actual:.17g} != {expected:.17g}")


def first_present(row: Mapping[str, Any], names: Sequence[str]) -> Any:
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return None


def normalize_setup_stratum(value: Any) -> str:
    text = str(value if value is not None else "main").strip().lower()
    text = text.replace("-", "_").replace(" ", "_")
    aliases = {
        "default": "main",
        "full": "main",
        "full_geometry": "main",
        "sg3": "main",
        "sh3": "main",
        "minimal": "minimal_sd",
        "minimal_sensitive_detector": "minimal_sd",
        "minimal_sensitive_detectors": "minimal_sd",
    }
    text = aliases.get(text, text)
    if not text or not re.fullmatch(r"[a-z0-9_]+", text):
        raise RuntimeError(f"invalid setup_stratum: {value!r}")
    return text


def model_alias_matches(model: str, value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip().lower().replace("_", "").replace("-", "")
    aliases = {
        "a": {"a", "sg3", "modela", "qualitymodela"},
        "b": {"b", "sh3", "modelb", "qualitymodelb"},
    }
    return text in aliases[model]


def path_with_repo_remap(value: str | Path, repo_root: Path) -> Path:
    """Resolve recorded repository paths without remapping external storage."""

    recorded = Path(value).expanduser()
    parts = recorded.parts
    if "TES_511_Balloon" in parts:
        marker = len(parts) - 1 - tuple(reversed(parts)).index("TES_511_Balloon")
        candidate = repo_root.joinpath(*parts[marker + 1 :])
        if candidate.exists():
            return candidate.resolve()
    if not recorded.is_absolute():
        candidate = repo_root / recorded
        if candidate.exists():
            return candidate.resolve()
    if recorded.exists():
        return recorded.resolve()
    raise FileNotFoundError(f"recorded authority path does not resolve: {value}")


def resolve_manifest_path(value: str | Path, manifest_path: Path, root: Path) -> Path:
    recorded = Path(value).expanduser()
    candidates: list[Path] = []
    if recorded.is_absolute():
        candidates.append(recorded)
    else:
        candidates.extend((manifest_path.parent / recorded, root / recorded))
    parts = recorded.parts
    if "TES_511_Balloon" in parts:
        marker = len(parts) - 1 - tuple(reversed(parts)).index("TES_511_Balloon")
        repo_root = Path(__file__).resolve().parents[4]
        candidates.append(repo_root.joinpath(*parts[marker + 1 :]))
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(
        f"manifest-recorded file does not resolve from {manifest_path}: {value}"
    )


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {name: data[name] for name in data.files}


def save_npz_atomic(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise RuntimeError(f"refusing to replace stale temporary file: {temporary}")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    os.replace(temporary, path)


def publish_directory_noreplace(stage: Path, output: Path) -> None:
    """Atomically publish ``stage`` without ever replacing ``output``.

    P67 catalog construction is long-running, so an existence check followed
    by ``os.replace`` has an unacceptable race.  Linux ``renameat2`` with
    ``RENAME_NOREPLACE`` makes the non-overwrite rule a kernel-enforced final
    operation.  Absence of that primitive is a hard failure, not permission to
    fall back to a replacing rename.
    """

    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise RuntimeError(
            "renameat2(RENAME_NOREPLACE) is unavailable; refusing a racy publish"
        )
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    at_fdcwd = -100
    rename_noreplace = 1
    result = renameat2(
        at_fdcwd,
        os.fsencode(stage),
        at_fdcwd,
        os.fsencode(output),
        rename_noreplace,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise FileExistsError(
            error_number,
            "non-overwrite publish refused an existing output",
            str(output),
        )
    raise OSError(error_number, os.strerror(error_number), str(output))


@dataclass(frozen=True)
class SupplementJob:
    job_id: str
    scan_index: int
    seed: int
    family: str
    setup_stratum: str
    exposure_TT_s: float
    transport_events: int
    detector_positive_events: int | None
    source_sha256: str
    cache_npz: Path
    cache_json: Path
    raw: Mapping[str, Any]


@dataclass
class BaseCatalog:
    model: str
    catalog_dir: Path
    repo_root: Path
    arrays: dict[str, np.ndarray]
    payload_fields: tuple[str, ...]
    categories: list[dict[str, Any]]
    category_registry: dict[str, Any]
    component_registry: dict[str, Any]
    audit: dict[str, Any]
    summary: dict[str, Any]
    component_id_by_name: dict[str, int]
    source_bin80_not_applicable: int
    prompt_rows: dict[str, dict[str, Any]]
    mature_summary_path: Path
    mature_summary: dict[str, Any]
    old_jobs: list[dict[str, Any]]
    old_exposure_by_family: dict[str, float]


@dataclass
class SupplementManifest:
    model: str
    roots: tuple[Path, ...]
    paths: tuple[Path, ...]
    raw_manifests: tuple[dict[str, Any], ...]
    jobs: list[SupplementJob]
    exposure_by_family: dict[str, float]
    exposure_by_family_stratum: dict[str, dict[str, float]]
    duplicate_audit: dict[str, Any]


def component_statistics(
    arrays: Mapping[str, np.ndarray], component_id_by_name: Mapping[str, int]
) -> dict[str, dict[str, float | int]]:
    weights = np.asarray(arrays["event_base_weight_cps"], dtype=np.float64)
    components = np.asarray(arrays["event_component"])
    result: dict[str, dict[str, float | int]] = {}
    for name, component_id in sorted(component_id_by_name.items(), key=lambda item: item[1]):
        selected = weights[components == component_id]
        stats = weight_stats(selected)
        result[name] = {
            "component_id": int(component_id),
            "events": int(stats["events"]),
            "sumw_cps": float(stats["sumw_cps"]),
            "sumw2_cps2": float(stats["sumw2_cps2"]),
            "effective_sample_size": float(stats["effective_sample_size"]),
        }
    return result


def validate_component_stats(
    actual: Mapping[str, Mapping[str, Any]],
    recorded: Mapping[str, Mapping[str, Any]],
    label: str,
) -> None:
    if set(actual) != set(recorded):
        raise RuntimeError(
            f"{label} component names differ: {sorted(actual)} != {sorted(recorded)}"
        )
    for name in actual:
        if int(actual[name]["events"]) != int(recorded[name]["events"]):
            raise RuntimeError(f"{label} {name} event count differs")
        for field in ("sumw_cps", "sumw2_cps2", "effective_sample_size"):
            require_close(
                float(actual[name][field]),
                float(recorded[name][field]),
                f"{label} {name} {field}",
            )


def validate_hit_ranges(arrays: Mapping[str, np.ndarray], label: str) -> int:
    starts = np.asarray(arrays["hit_start"], dtype=np.int64)
    counts = np.asarray(arrays["hit_count"], dtype=np.int64)
    if starts.shape != counts.shape or starts.ndim != 1:
        raise RuntimeError(f"{label} hit_start/hit_count shape mismatch")
    hit_lengths = {name: len(np.asarray(arrays[name])) for name in HIT_FIELDS}
    if len(set(hit_lengths.values())) != 1:
        raise RuntimeError(f"{label} hit-array lengths differ: {hit_lengths}")
    hit_total = next(iter(hit_lengths.values()))
    if np.any(starts < 0) or np.any(counts < 0) or np.any(starts + counts > hit_total):
        raise RuntimeError(f"{label} contains an out-of-range hit span")
    if len(starts):
        expected = np.empty(len(starts), dtype=np.int64)
        expected[0] = 0
        if len(starts) > 1:
            np.cumsum(counts[:-1], dtype=np.int64, out=expected[1:])
        if not np.array_equal(starts, expected):
            raise RuntimeError(f"{label} hit spans are not continuously packed")
    if int(np.sum(counts, dtype=np.int64)) != hit_total:
        raise RuntimeError(f"{label} sum(hit_count) does not close to hit arrays")
    return hit_total


def validate_category_rows(
    arrays: Mapping[str, np.ndarray],
    categories: Sequence[Mapping[str, Any]],
    component_id_by_name: Mapping[str, int],
) -> None:
    n_events = len(np.asarray(arrays["event_category"]))
    expected_start = 0
    for expected_id, row in enumerate(categories):
        category_id = int(row["category_id"])
        start = int(row["event_start"])
        count = int(row["event_count"])
        stop = start + count
        if category_id != expected_id or start != expected_start or count <= 0 or stop > n_events:
            raise RuntimeError(
                f"base category registry is not positive and contiguous at {expected_id}"
            )
        if not np.all(np.asarray(arrays["event_category"])[start:stop] == category_id):
            raise RuntimeError(f"base event_category mismatch at category {category_id}")
        component_name = str(row["component"])
        if component_name not in component_id_by_name:
            raise RuntimeError(f"unknown component in category {category_id}: {component_name}")
        expected_component = component_id_by_name[component_name]
        if not np.all(
            np.asarray(arrays["event_component"])[start:stop] == expected_component
        ):
            raise RuntimeError(f"base component mismatch at category {category_id}")
        weights = np.asarray(arrays["event_base_weight_cps"])[start:stop]
        stats = weight_stats(weights)
        for field, stat_name in (
            ("sum_event_base_weight_cps", "sumw_cps"),
            ("sum_event_base_weight2_cps2", "sumw2_cps2"),
            ("effective_sample_size", "effective_sample_size"),
        ):
            require_close(
                float(row[field]),
                float(stats[stat_name]),
                f"base category {category_id} {field}",
            )
        constant = row.get("base_event_weight_cps")
        if constant is not None and not np.allclose(
            weights, float(constant), rtol=REL_TOL, atol=ABS_TOL
        ):
            raise RuntimeError(f"base constant category weight mismatch at {category_id}")
        expected_start = stop
    if expected_start != n_events:
        raise RuntimeError("base category registry does not span the catalog")


def load_base_catalog(model: str) -> BaseCatalog:
    p67_package = Path(os.environ.get("M05_P67_PACKAGE", DEFAULT_P67_PACKAGE)).resolve()
    catalog_dir = p67_package / "outputs" / P67_MODEL_DIR[model]
    required_paths = {
        "catalog": catalog_dir / "combined_event_catalog.npz",
        "category_registry": catalog_dir / "category_registry.json",
        "component_registry": catalog_dir / "component_registry.json",
        "audit": catalog_dir / "audit.json",
        "summary": catalog_dir / "summary.json",
    }
    missing = [str(path) for path in required_paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"P67 model-{model} inputs are missing: {missing}")

    arrays = load_npz(required_paths["catalog"])
    category_registry = load_json(required_paths["category_registry"])
    component_registry = load_json(required_paths["component_registry"])
    audit = load_json(required_paths["audit"])
    summary = load_json(required_paths["summary"])
    categories = [dict(row) for row in category_registry["categories"]]

    if str(audit.get("status")) != "PASS__FLUXCLOSED_CATALOG_AUDIT":
        raise RuntimeError(f"P67 audit is not authoritative PASS: {audit.get('status')}")
    if str(summary.get("status")) != "COMPLETE__POSITIVE_FLUXCLOSED_EVENT_CATALOG":
        raise RuntimeError(f"P67 summary is not COMPLETE: {summary.get('status')}")
    if str(audit.get("model")) != model or str(summary.get("model")) != model:
        raise RuntimeError("P67 model labels do not match the requested model")

    component_id_by_name = {
        str(row["component"]): int(row["component_id"])
        for row in component_registry["components"]
    }
    expected_component_ids = {
        "other": 0,
        "gamma_continuum": 1,
        "atm511": 2,
    }
    if component_id_by_name != expected_component_ids:
        raise RuntimeError(f"unexpected P67 component registry: {component_id_by_name}")
    source_bin80_not_applicable = int(
        component_registry["source_bin80_not_applicable"]
    )
    if source_bin80_not_applicable != 255:
        raise RuntimeError("P67 source_bin80_not_applicable is not the required 255")

    for field in (
        *REQUIRED_RESPONSE_FIELDS,
        *GENERATED_EVENT_FIELDS,
        *HIT_FIELDS,
    ):
        if field not in arrays:
            raise RuntimeError(f"P67 catalog lacks required field: {field}")
    n_events = len(np.asarray(arrays["event_category"]))
    payload_fields = tuple(
        name
        for name, values in arrays.items()
        if name not in HIT_FIELDS
        and name not in GENERATED_EVENT_FIELDS
        and np.asarray(values).shape == (n_events,)
    )
    for field in REQUIRED_RESPONSE_FIELDS:
        if field not in payload_fields:
            raise RuntimeError(f"P67 response payload is missing {field}")
    if model == "b" and "compton_keep" not in payload_fields:
        raise RuntimeError("model-B P67 payload lacks compton_keep")
    if model == "a" and "compton_keep" in payload_fields:
        raise RuntimeError("model-A P67 payload unexpectedly contains compton_keep")
    for name in (*payload_fields, *GENERATED_EVENT_FIELDS):
        if np.asarray(arrays[name]).shape != (n_events,):
            raise RuntimeError(f"P67 event field is not event-aligned: {name}")
    hit_total = validate_hit_ranges(arrays, "P67 catalog")
    if int(summary["events"]) != n_events or int(summary["hits"]) != hit_total:
        raise RuntimeError("P67 summary event/hit counts do not close")
    if int(summary["categories"]) != len(categories):
        raise RuntimeError("P67 summary category count does not close")
    validate_category_rows(arrays, categories, component_id_by_name)
    base_component_stats = component_statistics(arrays, component_id_by_name)
    validate_component_stats(base_component_stats, summary["components"], "P67 summary")
    validate_component_stats(base_component_stats, audit["components"], "P67 audit")

    prompt_rows: dict[str, dict[str, Any]] = {}
    for row in categories:
        family = str(row.get("family", ""))
        if row.get("stream") == "prompt" and family in FAMILY_SET:
            if row.get("component") != "other":
                raise RuntimeError(f"prompt family {family} is not in component other")
            if family in prompt_rows:
                raise RuntimeError(f"multiple P67 prompt categories for {family}")
            prompt_rows[family] = row
    if set(prompt_rows) != FAMILY_SET:
        raise RuntimeError(
            f"P67 prompt-family set differs: {sorted(prompt_rows)} != {sorted(FAMILY_SET)}"
        )

    # Resolve the mature summary named by the P67 audit.  This supplies the
    # exact old job/seed lineage needed for fail-closed overlap checks.
    repo_root = p67_package.parents[2]
    mature_dir = path_with_repo_remap(audit["mature_input"], repo_root)
    mature_summary_path = mature_dir / "summary.json"
    if not mature_summary_path.is_file():
        raise FileNotFoundError(f"P67 mature summary is missing: {mature_summary_path}")
    mature_summary = load_json(mature_summary_path)
    if str(mature_summary.get("status")) != str(audit.get("mature_status")):
        raise RuntimeError("P67 mature status no longer matches its recorded authority")
    old_jobs = [
        dict(row)
        for row in mature_summary.get("jobs", [])
        if row.get("stream") == "prompt" and row.get("family") in FAMILY_SET
    ]
    if not old_jobs:
        raise RuntimeError("P67 mature summary has no retained prompt-family jobs")
    old_keys = [
        (str(row.get("batch_id", "")), str(row["job_id"])) for row in old_jobs
    ]
    old_seeds = [int(row["seed"]) for row in old_jobs]
    if len(set(old_keys)) != len(old_keys) or len(set(old_seeds)) != len(old_seeds):
        raise RuntimeError(
            "P67 mature prompt lineage contains duplicate batch/job keys or seeds"
        )

    old_exposure_by_family: dict[str, float] = {}
    for family in FAMILIES:
        family_jobs = [row for row in old_jobs if row["family"] == family]
        if not family_jobs:
            raise RuntimeError(f"P67 mature summary lacks old jobs for {family}")
        row = prompt_rows[family]
        base_weight = finite_positive(row["base_event_weight_cps"], f"P67 {family} weight")
        weights = [finite_positive(job["weight_cps"], f"P67 job {job['job_id']} weight") for job in family_jobs]
        if any(not close(value, base_weight) for value in weights):
            raise RuntimeError(f"P67 mature job weights do not close for {family}")
        detector_positive = sum(int(job["detector_positive_events"]) for job in family_jobs)
        if detector_positive != int(row["event_count"]):
            raise RuntimeError(
                f"P67 old detector-positive membership does not close for {family}: "
                f"{detector_positive} != {row['event_count']}"
            )
        start = int(row["event_start"])
        stop = start + int(row["event_count"])
        if not np.allclose(
            np.asarray(arrays["event_base_weight_cps"])[start:stop],
            base_weight,
            rtol=REL_TOL,
            atol=ABS_TOL,
        ):
            raise RuntimeError(f"P67 old event weights do not close for {family}")
        old_exposure_by_family[family] = 1.0 / base_weight

    return BaseCatalog(
        model=model,
        catalog_dir=catalog_dir,
        repo_root=repo_root,
        arrays=arrays,
        payload_fields=payload_fields,
        categories=categories,
        category_registry=category_registry,
        component_registry=component_registry,
        audit=audit,
        summary=summary,
        component_id_by_name=component_id_by_name,
        source_bin80_not_applicable=source_bin80_not_applicable,
        prompt_rows=prompt_rows,
        mature_summary_path=mature_summary_path,
        mature_summary=mature_summary,
        old_jobs=old_jobs,
        old_exposure_by_family=old_exposure_by_family,
    )


def locate_supplement_manifest(model: str, root: Path) -> Path:
    label = MODEL_LABEL[model]
    candidates = (
        root if root.name == "jobs.json" else root / "jobs.json",
        root / "outputs" / label / "jobs.json",
        root / "outputs" / model / "jobs.json",
        root / label / "jobs.json",
        root / model / "jobs.json",
    )
    existing: list[Path] = []
    for candidate in candidates:
        if candidate.is_file() and candidate.resolve() not in existing:
            existing.append(candidate.resolve())
    if len(existing) != 1:
        raise RuntimeError(
            f"expected exactly one model-{model} supplement jobs.json under {root}; "
            f"found {[str(path) for path in existing]}"
        )
    return existing[0]


def schema_name(manifest: Mapping[str, Any]) -> str:
    for key in ("schema", "schema_version", "catalog_schema"):
        value = manifest.get(key)
        if isinstance(value, str):
            return value
    return ""


def cache_paths_for_job(
    row: Mapping[str, Any], manifest_path: Path, root: Path
) -> tuple[Path, Path]:
    nested = row.get("cache") if isinstance(row.get("cache"), Mapping) else {}
    npz_value = first_present(
        row,
        ("cache_npz", "catalog_path", "cache_path", "npz_path", "compact_path"),
    )
    if npz_value is None:
        npz_value = first_present(nested, ("npz", "path", "catalog", "cache_npz"))
    if npz_value is None:
        raise RuntimeError(f"supplement job {row.get('job_id')} has no compact NPZ path")
    npz_path = resolve_manifest_path(npz_value, manifest_path, root)
    json_value = first_present(
        row, ("cache_json", "catalog_json", "metadata_path", "sidecar_path")
    )
    if json_value is None:
        json_value = first_present(nested, ("json", "metadata", "receipt"))
    if json_value is None:
        json_path = npz_path.with_suffix(".json")
        if not json_path.is_file():
            raise FileNotFoundError(
                f"supplement job {row.get('job_id')} has no compact JSON sidecar"
            )
    else:
        json_path = resolve_manifest_path(json_value, manifest_path, root)
    return npz_path, json_path


def load_supplement_manifest(
    model: str, root: Path, base: BaseCatalog
) -> SupplementManifest:
    root = root.expanduser().resolve()
    manifest_path = locate_supplement_manifest(model, root)
    authority_root = root.parent if root.is_file() else root
    raw = load_json(manifest_path)
    if schema_name(raw) != SUPPLEMENT_SCHEMA:
        raise RuntimeError(
            f"unexpected supplement schema in {manifest_path}: {schema_name(raw)!r}"
        )
    if not model_alias_matches(model, raw.get("model")):
        raise RuntimeError(f"supplement manifest model differs from requested model-{model}")
    if raw.get("setup_stratum") is None:
        raise RuntimeError("supplement jobs.json lacks top-level setup_stratum")
    recorded_stratum = normalize_setup_stratum(raw["setup_stratum"])
    status = str(raw.get("status", ""))
    expected_status = EXPECTED_MANIFEST_STATUS.get((model, recorded_stratum))
    if expected_status is None or status != expected_status:
        raise RuntimeError(
            f"supplement manifest status differs for {model}/{recorded_stratum}: "
            f"{status!r} != {expected_status!r}"
        )
    expected_candidate = EXPECTED_CANDIDATE.get((model, recorded_stratum))
    if expected_candidate is None:
        raise RuntimeError(
            f"unsupported model/setup_stratum authority: {model}/{recorded_stratum}"
        )
    if str(raw.get("candidate", "")) != expected_candidate:
        raise RuntimeError(
            f"supplement candidate differs for {model}/{recorded_stratum}: "
            f"{raw.get('candidate')!r} != {expected_candidate!r}"
        )
    upstream_overlap = raw.get("base_overlap_audit")
    if not isinstance(upstream_overlap, Mapping):
        raise RuntimeError("supplement jobs.json lacks base_overlap_audit")
    if str(upstream_overlap.get("status")) != "PASS__NO_BASE_JOB_OR_SEED_OVERLAP":
        raise RuntimeError(
            f"supplement upstream base-overlap audit is not PASS: {upstream_overlap}"
        )
    for field in ("duplicate_job_ids", "duplicate_seeds"):
        if list(upstream_overlap.get(field, [])):
            raise RuntimeError(f"supplement upstream overlap field is non-empty: {field}")
    raw_jobs = raw.get("jobs")
    if not isinstance(raw_jobs, list) or not raw_jobs:
        raise RuntimeError("supplement jobs.json contains no jobs")
    if raw.get("weight_policy") != DEFERRED_WEIGHT_POLICY:
        raise RuntimeError("supplement top-level weight policy is not deferred")

    jobs: list[SupplementJob] = []
    for ordinal, raw_row in enumerate(raw_jobs):
        if not isinstance(raw_row, Mapping):
            raise RuntimeError(f"supplement job row {ordinal} is not an object")
        row = dict(raw_row)
        family = str(row.get("family", ""))
        if family not in FAMILY_SET:
            raise RuntimeError(f"supplement job has a non-retained family: {family!r}")
        if row.get("stream") != "prompt":
            raise RuntimeError(f"supplement job {row.get('job_id')} is not prompt")
        if row.get("setup_stratum") is None:
            raise RuntimeError(
                f"supplement job {row.get('job_id')} lacks setup_stratum"
            )
        job_stratum = normalize_setup_stratum(row["setup_stratum"])
        if job_stratum != recorded_stratum:
            raise RuntimeError(
                f"supplement job {row.get('job_id')} setup_stratum differs: "
                f"{job_stratum!r} != {recorded_stratum!r}"
            )
        if row.get("weight_policy") != DEFERRED_WEIGHT_POLICY:
            raise RuntimeError(
                f"supplement job {row.get('job_id')} weight policy is not deferred"
            )
        if row.get("weight_cps") is None or float(row["weight_cps"]) != 0.0:
            raise RuntimeError(
                f"supplement job {row.get('job_id')} does not declare deferred weight_cps=0"
            )
        job_id = str(row.get("job_id", "")).strip()
        if not job_id:
            raise RuntimeError(f"supplement row {ordinal} has no job_id")
        if not str(row.get("batch_id", "")).strip():
            raise RuntimeError(f"supplement job {job_id} has no batch_id")
        if row.get("scan_index") is None:
            raise RuntimeError(f"supplement job {job_id} has no scan_index")
        seed = int(row["seed"])
        if seed <= 0:
            raise RuntimeError(f"supplement job {job_id} has invalid seed {seed}")
        exposure = finite_positive(
            first_present(row, ("exposure_TT_s", "physical_exposure_s", "TT_s")),
            f"supplement job {job_id} exposure",
        )
        transport_events = int(first_present(row, ("events", "incident_events")) or 0)
        if transport_events <= 0:
            raise RuntimeError(f"supplement job {job_id} has invalid transport event count")
        detector_positive_value = first_present(
            row, ("detector_positive_events", "catalog_events", "selected_events")
        )
        if detector_positive_value is None:
            raise RuntimeError(
                f"supplement job {job_id} lacks detector_positive_events"
            )
        detector_positive = int(detector_positive_value)
        if detector_positive < 0:
            raise RuntimeError(f"supplement job {job_id} has a negative compact count")
        source_hash = str(row.get("source_sha256", "")).lower()
        if not SHA256_RE.fullmatch(source_hash):
            raise RuntimeError(f"supplement job {job_id} lacks a valid source_sha256")
        cache_npz, cache_json = cache_paths_for_job(row, manifest_path, authority_root)
        jobs.append(
            SupplementJob(
                job_id=job_id,
                scan_index=int(row["scan_index"]),
                seed=seed,
                family=family,
                setup_stratum=job_stratum,
                exposure_TT_s=exposure,
                transport_events=transport_events,
                detector_positive_events=detector_positive,
                source_sha256=source_hash,
                cache_npz=cache_npz,
                cache_json=cache_json,
                raw=row,
            )
        )

    job_strata = {job.setup_stratum for job in jobs}
    if job_strata != {recorded_stratum}:
        raise RuntimeError(
            f"supplement top-level setup_stratum differs from jobs: "
            f"{recorded_stratum!r} vs {sorted(job_strata)}"
        )

    job_ids = [job.job_id for job in jobs]
    seeds = [job.seed for job in jobs]
    source_hashes = [job.source_sha256 for job in jobs]
    cache_paths = [str(job.cache_npz) for job in jobs]
    duplicate_jobs = sorted(name for name, count in Counter(job_ids).items() if count > 1)
    duplicate_seeds = sorted(value for value, count in Counter(seeds).items() if count > 1)
    duplicate_sources = sorted(
        value for value, count in Counter(source_hashes).items() if count > 1
    )
    duplicate_caches = sorted(
        value for value, count in Counter(cache_paths).items() if count > 1
    )
    if duplicate_jobs or duplicate_seeds or duplicate_sources or duplicate_caches:
        raise RuntimeError(
            "supplement internal duplication detected: "
            f"jobs={duplicate_jobs}, seeds={duplicate_seeds}, "
            f"source_sha256={duplicate_sources}, caches={duplicate_caches}"
        )

    old_job_ids = {str(row["job_id"]) for row in base.old_jobs}
    old_seeds = {int(row["seed"]) for row in base.old_jobs}
    overlap_jobs = sorted(old_job_ids.intersection(job_ids))
    overlap_seeds = sorted(old_seeds.intersection(seeds))
    if overlap_jobs or overlap_seeds:
        raise RuntimeError(
            f"supplement overlaps retained P67 prompt lineage: "
            f"jobs={overlap_jobs}, seeds={overlap_seeds}"
        )

    exposure_by_family = {family: 0.0 for family in FAMILIES}
    exposure_by_family_stratum: dict[str, dict[str, float]] = {
        family: defaultdict(float) for family in FAMILIES
    }
    for job in jobs:
        exposure_by_family[job.family] += job.exposure_TT_s
        exposure_by_family_stratum[job.family][job.setup_stratum] += job.exposure_TT_s
    observed_families = {job.family for job in jobs}

    recorded_exposure = first_present(
        raw,
        (
            "exposure_TT_s_by_family",
            "physical_exposure_s_by_family",
            "TT_s_by_family",
        ),
    )
    if not isinstance(recorded_exposure, Mapping):
        raise RuntimeError("supplement jobs.json lacks exposure_TT_s_by_family")
    if set(recorded_exposure) != observed_families:
        raise RuntimeError(
            "supplement exposure family set differs from this manifest's jobs: "
            f"{sorted(recorded_exposure)} != {sorted(observed_families)}"
        )
    for family in observed_families:
        require_close(
            exposure_by_family[family],
            float(recorded_exposure[family]),
            f"supplement {family} exposure total",
        )

    recorded_jobs = first_present(raw, ("jobs_count", "job_count"))
    if recorded_jobs is not None and int(recorded_jobs) != len(jobs):
        raise RuntimeError("supplement jobs_count does not match jobs membership")
    recorded_seeds = raw.get("seeds")
    if recorded_seeds is not None:
        if sorted(int(value) for value in recorded_seeds) != sorted(seeds):
            raise RuntimeError("supplement top-level seed registry does not close")

    duplicate_audit = {
        "status": "PASS__ZERO_INTERNAL_OR_BASE_PROMPT_OVERLAP",
        "supplement_jobs": len(jobs),
        "supplement_unique_job_ids": len(set(job_ids)),
        "supplement_unique_seeds": len(set(seeds)),
        "supplement_unique_source_sha256": len(set(source_hashes)),
        "supplement_unique_cache_paths": len(set(cache_paths)),
        "retained_base_prompt_jobs": len(base.old_jobs),
        "duplicate_job_ids_with_base": overlap_jobs,
        "duplicate_seeds_with_base": overlap_seeds,
        "upstream_base_overlap_status": upstream_overlap["status"],
    }
    return SupplementManifest(
        model=model,
        roots=(authority_root,),
        paths=(manifest_path,),
        raw_manifests=(raw,),
        jobs=sorted(jobs, key=lambda job: (job.scan_index, job.job_id)),
        exposure_by_family=exposure_by_family,
        exposure_by_family_stratum={
            family: dict(values)
            for family, values in exposure_by_family_stratum.items()
        },
        duplicate_audit=duplicate_audit,
    )


def combine_supplement_manifests(
    model: str,
    manifests: Sequence[SupplementManifest],
    base: BaseCatalog,
) -> SupplementManifest:
    """Combine explicit main/minimal manifests before assigning family weights."""

    if not manifests:
        raise RuntimeError("no supplement jobs manifests were supplied")
    paths = tuple(path for manifest in manifests for path in manifest.paths)
    if len(set(paths)) != len(paths):
        raise RuntimeError(f"duplicate supplement manifest paths: {paths}")
    jobs = [job for manifest in manifests for job in manifest.jobs]
    if not jobs:
        raise RuntimeError("combined supplement manifest membership is empty")
    observed_strata = {job.setup_stratum for job in jobs}
    required_strata = {"main", "minimal_sd"} if model == "a" else {"main"}
    if observed_strata != required_strata:
        raise RuntimeError(
            f"model-{model} supplement setup strata differ: "
            f"{sorted(observed_strata)} != {sorted(required_strata)}"
        )

    def duplicates(values: Iterable[Any]) -> list[Any]:
        return sorted(value for value, count in Counter(values).items() if count > 1)

    duplicate_jobs = duplicates(job.job_id for job in jobs)
    duplicate_seeds = duplicates(job.seed for job in jobs)
    duplicate_sources = duplicates(job.source_sha256 for job in jobs)
    duplicate_caches = duplicates(str(job.cache_npz) for job in jobs)
    if duplicate_jobs or duplicate_seeds or duplicate_sources or duplicate_caches:
        raise RuntimeError(
            "cross-manifest supplement duplication detected: "
            f"jobs={duplicate_jobs}, seeds={duplicate_seeds}, "
            f"source_sha256={duplicate_sources}, caches={duplicate_caches}"
        )

    old_job_ids = {str(row["job_id"]) for row in base.old_jobs}
    old_seeds = {int(row["seed"]) for row in base.old_jobs}
    overlap_jobs = sorted(old_job_ids.intersection(job.job_id for job in jobs))
    overlap_seeds = sorted(old_seeds.intersection(job.seed for job in jobs))
    if overlap_jobs or overlap_seeds:
        raise RuntimeError(
            f"combined supplements overlap retained P67 prompt lineage: "
            f"jobs={overlap_jobs}, seeds={overlap_seeds}"
        )

    exposure_by_family = {family: 0.0 for family in FAMILIES}
    exposure_by_family_stratum: dict[str, dict[str, float]] = {
        family: defaultdict(float) for family in FAMILIES
    }
    for job in jobs:
        exposure_by_family[job.family] += job.exposure_TT_s
        exposure_by_family_stratum[job.family][job.setup_stratum] += job.exposure_TT_s
    missing_exposure = [
        family for family in FAMILIES if exposure_by_family[family] <= 0.0
    ]
    if missing_exposure:
        raise RuntimeError(
            f"combined supplement manifests lack positive exposure for {missing_exposure}"
        )

    duplicate_audit = {
        "status": "PASS__ZERO_INTERNAL_CROSS_MANIFEST_OR_BASE_PROMPT_OVERLAP",
        "supplement_manifests": len(manifests),
        "supplement_jobs": len(jobs),
        "supplement_unique_job_ids": len({job.job_id for job in jobs}),
        "supplement_unique_seeds": len({job.seed for job in jobs}),
        "supplement_unique_source_sha256": len({job.source_sha256 for job in jobs}),
        "supplement_unique_cache_paths": len({str(job.cache_npz) for job in jobs}),
        "retained_base_prompt_jobs": len(base.old_jobs),
        "duplicate_job_ids_with_base": overlap_jobs,
        "duplicate_seeds_with_base": overlap_seeds,
        "member_audits": [manifest.duplicate_audit for manifest in manifests],
    }
    return SupplementManifest(
        model=model,
        roots=tuple(root for manifest in manifests for root in manifest.roots),
        paths=paths,
        raw_manifests=tuple(
            raw for manifest in manifests for raw in manifest.raw_manifests
        ),
        jobs=sorted(
            jobs,
            key=lambda job: (
                FAMILIES.index(job.family),
                job.setup_stratum,
                job.scan_index,
                job.job_id,
            ),
        ),
        exposure_by_family=exposure_by_family,
        exposure_by_family_stratum={
            family: dict(values)
            for family, values in exposure_by_family_stratum.items()
        },
        duplicate_audit=duplicate_audit,
    )


def validate_job_arrays(
    job: SupplementJob,
    payload_fields: Sequence[str],
    payload_dtypes: Mapping[str, np.dtype[Any]],
) -> dict[str, np.ndarray]:
    sidecar = load_json(job.cache_json)
    status = str(sidecar.get("status", ""))
    if status != SUPPLEMENT_SIDECAR_STATUS:
        raise RuntimeError(
            f"supplement cache sidecar status differs: {job.cache_json}: "
            f"{status!r} != {SUPPLEMENT_SIDECAR_STATUS!r}"
        )
    required_sidecar = {
        "job_id",
        "family",
        "seed",
        "stream",
        "batch_id",
        "scan_index",
        "events",
        "detector_positive_events",
        "catalog_path",
        "weight_cps",
    }
    missing_sidecar = sorted(required_sidecar.difference(sidecar))
    if missing_sidecar:
        raise RuntimeError(
            f"supplement cache sidecar {job.job_id} lacks fields: {missing_sidecar}"
        )
    for key, expected in (
        ("job_id", job.job_id),
        ("family", job.family),
        ("seed", job.seed),
        ("stream", "prompt"),
        ("batch_id", job.raw["batch_id"]),
        ("scan_index", job.scan_index),
        ("events", job.transport_events),
    ):
        if str(sidecar[key]) != str(expected):
            raise RuntimeError(f"supplement cache sidecar {key} mismatch for {job.job_id}")
    if float(sidecar["weight_cps"]) != 0.0:
        raise RuntimeError(f"supplement cache {job.job_id} weight_cps is not deferred zero")
    recorded_catalog = Path(str(sidecar["catalog_path"])).expanduser().resolve()
    if recorded_catalog != job.cache_npz.resolve():
        raise RuntimeError(
            f"supplement cache sidecar catalog_path mismatch for {job.job_id}: "
            f"{recorded_catalog} != {job.cache_npz.resolve()}"
        )
    if (
        job.detector_positive_events is not None
        and int(sidecar["detector_positive_events"])
        != job.detector_positive_events
    ):
        raise RuntimeError(
            f"supplement cache sidecar detector-positive count mismatch for {job.job_id}"
        )

    arrays = load_npz(job.cache_npz)
    required = {"event_id", "source_za", *payload_fields, *HIT_FIELDS}
    missing = sorted(required.difference(arrays))
    if missing:
        raise RuntimeError(f"supplement compact {job.job_id} lacks arrays: {missing}")
    n_events = len(np.asarray(arrays["event_id"]))
    for name in ("event_id", "source_za", *payload_fields):
        if np.asarray(arrays[name]).shape != (n_events,):
            raise RuntimeError(
                f"supplement compact {job.job_id} field {name} is not event-aligned"
            )
    if job.detector_positive_events is not None and n_events != job.detector_positive_events:
        raise RuntimeError(
            f"supplement compact count differs for {job.job_id}: "
            f"{n_events} != {job.detector_positive_events}"
        )
    sidecar_count = first_present(
        sidecar, ("detector_positive_events", "catalog_events", "selected_events")
    )
    if sidecar_count is not None and int(sidecar_count) != n_events:
        raise RuntimeError(f"supplement cache sidecar count differs for {job.job_id}")
    event_ids = np.asarray(arrays["event_id"])
    if len(np.unique(event_ids)) != n_events:
        raise RuntimeError(f"supplement compact event_id duplicates within {job.job_id}")
    validate_hit_ranges(arrays, f"supplement compact {job.job_id}")
    for field in payload_fields:
        source_dtype = np.asarray(arrays[field]).dtype
        target_dtype = np.dtype(payload_dtypes[field])
        if not np.can_cast(source_dtype, target_dtype, casting="same_kind"):
            raise RuntimeError(
                f"supplement compact {job.job_id} cannot cast {field} "
                f"from {source_dtype} to P67 {target_dtype}"
            )
    return arrays


class CatalogAssembler:
    """Append event blocks and repack their hit arrays continuously."""

    def __init__(
        self,
        payload_fields: Sequence[str],
        payload_dtypes: Mapping[str, np.dtype[Any]],
        hit_dtypes: Mapping[str, np.dtype[Any]],
    ) -> None:
        self.payload_fields = tuple(payload_fields)
        self.payload_dtypes = {name: np.dtype(value) for name, value in payload_dtypes.items()}
        self.hit_dtypes = {name: np.dtype(value) for name, value in hit_dtypes.items()}
        self.event_chunks: dict[str, list[np.ndarray]] = {
            name: [] for name in self.payload_fields
        }
        self.event_chunks.update(
            {
                "event_base_weight_cps": [],
                "event_component": [],
                "source_bin80": [],
                "continuum_importance_weight": [],
            }
        )
        self.category_chunks: list[np.ndarray] = []
        self.hit_chunks: dict[str, list[np.ndarray]] = {name: [] for name in HIT_FIELDS}
        self.events = 0
        self.hits = 0

    def append(
        self,
        arrays: Mapping[str, np.ndarray],
        *,
        category_id: int,
        weights: float | np.ndarray,
        component: int | np.ndarray,
        source_bin80: int | np.ndarray,
        continuum_importance: float | np.ndarray,
        event_slice: slice | np.ndarray | None = None,
    ) -> tuple[int, int, dict[str, float | int]]:
        selector: slice | np.ndarray = slice(None) if event_slice is None else event_slice
        counts = np.asarray(arrays["hit_count"])[selector].astype(np.int64, copy=False)
        starts = np.asarray(arrays["hit_start"])[selector].astype(np.int64, copy=False)
        count = int(len(counts))
        if count == 0:
            return self.events, 0, weight_stats(np.empty(0, dtype=np.float64))

        def vector(value: float | int | np.ndarray, dtype: np.dtype[Any]) -> np.ndarray:
            if np.isscalar(value):
                return np.full(count, value, dtype=dtype)
            result = np.asarray(value, dtype=dtype)
            if result.shape != (count,):
                raise RuntimeError(f"event-vector shape mismatch: {result.shape} != {(count,)}")
            return result

        weight_values = vector(weights, np.dtype(np.float64))
        component_values = vector(component, np.dtype(np.uint8))
        bin_values = vector(source_bin80, np.dtype(np.uint8))
        importance_values = vector(continuum_importance, np.dtype(np.float64))
        if np.any(~np.isfinite(weight_values)) or np.any(weight_values <= 0.0):
            raise RuntimeError("appended block has invalid event weights")
        if np.any(~np.isfinite(importance_values)) or np.any(importance_values <= 0.0):
            raise RuntimeError("appended block has invalid continuum importance")

        offsets = np.empty(count, dtype=np.int64)
        offsets[0] = 0
        if count > 1:
            np.cumsum(counts[:-1], dtype=np.int64, out=offsets[1:])
        new_starts = offsets + self.hits
        total_hits = int(np.sum(counts, dtype=np.int64))
        positive = np.flatnonzero(counts)
        if len(positive):
            old_starts = starts[positive]
            old_counts = counts[positive]
            expected_positive_starts = offsets[positive]
            if not np.array_equal(old_starts, expected_positive_starts):
                # A sliced source block may begin after hit zero.
                relative = old_starts - int(old_starts[0])
                expected_relative = expected_positive_starts - int(expected_positive_starts[0])
                if not np.array_equal(relative, expected_relative):
                    raise RuntimeError("appended event hit spans are not continuous")
            lo = int(old_starts[0])
            hi = int(old_starts[-1] + old_counts[-1])
            if hi - lo != total_hits:
                raise RuntimeError("appended hit slice does not equal sum(hit_count)")
            for field in HIT_FIELDS:
                source = np.asarray(arrays[field])
                if hi > len(source):
                    raise RuntimeError(f"appended hit slice exceeds {field}")
                packed = np.asarray(source[lo:hi], dtype=self.hit_dtypes[field])
                if len(packed) != total_hits:
                    raise RuntimeError(f"appended {field} hit count differs")
                self.hit_chunks[field].append(packed)
        elif total_hits:
            raise RuntimeError("positive hit sum without hit-bearing events")

        for field in self.payload_fields:
            if field not in arrays:
                raise RuntimeError(f"appended block lacks payload field {field}")
            values = np.asarray(arrays[field])[selector]
            if len(values) != count:
                raise RuntimeError(f"appended payload length differs for {field}")
            if field == "hit_start":
                values = new_starts
            self.event_chunks[field].append(
                np.asarray(values, dtype=self.payload_dtypes[field])
            )
        self.event_chunks["event_base_weight_cps"].append(weight_values)
        self.event_chunks["event_component"].append(component_values)
        self.event_chunks["source_bin80"].append(bin_values)
        self.event_chunks["continuum_importance_weight"].append(importance_values)
        self.category_chunks.append(np.full(count, category_id, dtype=np.uint16))

        event_start = self.events
        self.events += count
        self.hits += total_hits
        return event_start, count, weight_stats(weight_values)

    def finalize(self) -> dict[str, np.ndarray]:
        output: dict[str, np.ndarray] = {}
        for field, chunks in self.event_chunks.items():
            if not chunks:
                raise RuntimeError(f"no event chunks assembled for {field}")
            output[field] = np.concatenate(chunks)
        if not self.category_chunks:
            raise RuntimeError("no event categories assembled")
        output["event_category"] = np.concatenate(self.category_chunks)
        for field, chunks in self.hit_chunks.items():
            output[field] = (
                np.concatenate(chunks)
                if chunks
                else np.empty(0, dtype=self.hit_dtypes[field])
            )
        event_lengths = {
            name: len(values)
            for name, values in output.items()
            if name not in HIT_FIELDS
        }
        if set(event_lengths.values()) != {self.events}:
            raise RuntimeError(f"assembled event-array lengths differ: {event_lengths}")
        hit_lengths = {name: len(output[name]) for name in HIT_FIELDS}
        if set(hit_lengths.values()) != {self.hits}:
            raise RuntimeError(f"assembled hit-array lengths differ: {hit_lengths}")
        validate_hit_ranges(output, "integrated catalog")
        return output


def category_with_stats(
    source: Mapping[str, Any],
    *,
    category_id: int,
    event_start: int,
    stats: Mapping[str, Any],
) -> dict[str, Any]:
    row = dict(source)
    row.update(
        {
            "category_id": int(category_id),
            "event_start": int(event_start),
            "event_count": int(stats["events"]),
            "sum_event_base_weight_cps": float(stats["sumw_cps"]),
            "sum_event_base_weight2_cps2": float(stats["sumw2_cps2"]),
            "effective_sample_size": float(stats["effective_sample_size"]),
            "base_detector_positive_rate_cps": float(stats["sumw_cps"]),
        }
    )
    return row


def aggregate_constant_stats(events: int, weight: float) -> dict[str, float | int]:
    sumw = float(events) * weight
    sumw2 = float(events) * weight * weight
    return {
        "events": int(events),
        "sumw_cps": sumw,
        "sumw2_cps2": sumw2,
        "effective_sample_size": effective_sample_size(sumw, sumw2),
        "minimum_event_weight_cps": weight if events else None,
        "maximum_event_weight_cps": weight if events else None,
    }


def preflight_report(base: BaseCatalog, supplement: SupplementManifest) -> dict[str, Any]:
    payload_dtypes = {
        field: np.asarray(base.arrays[field]).dtype for field in base.payload_fields
    }
    compact_events = 0
    compact_hits = 0
    observed_by_family = Counter()
    observed_by_stratum = Counter()
    for index, job in enumerate(supplement.jobs, 1):
        arrays = validate_job_arrays(job, base.payload_fields, payload_dtypes)
        events = len(arrays["event_id"])
        hits = len(arrays[HIT_FIELDS[0]])
        compact_events += events
        compact_hits += hits
        observed_by_family[job.family] += events
        observed_by_stratum[job.setup_stratum] += events
        if index % 50 == 0 or index == len(supplement.jobs):
            print(
                json.dumps(
                    {
                        "check_inputs": True,
                        "model": base.model,
                        "validated_jobs": index,
                        "total_jobs": len(supplement.jobs),
                    },
                    sort_keys=True,
                ),
                file=sys.stderr,
                flush=True,
            )
    return {
        "schema": INTEGRATION_SCHEMA,
        "status": "PASS__INTEGRATION_INPUT_PREFLIGHT",
        "model": base.model,
        "quality_model": MODEL_LABEL[base.model],
        "p67_catalog": str(base.catalog_dir / "combined_event_catalog.npz"),
        "p67_events": int(base.summary["events"]),
        "p67_hits": int(base.summary["hits"]),
        "p67_categories": int(base.summary["categories"]),
        "p67_mature_summary": str(base.mature_summary_path),
        "supplement_manifests": [
            {
                "path": str(path),
                "sha256": sha256_file(path),
                "schema": schema_name(raw),
                "status": raw["status"],
                "model": raw.get("model"),
                "setup_stratum": raw.get("setup_stratum"),
            }
            for path, raw in zip(supplement.paths, supplement.raw_manifests)
        ],
        "supplement_jobs": len(supplement.jobs),
        "supplement_compact_events": compact_events,
        "supplement_compact_hits": compact_hits,
        "supplement_compact_events_by_family": dict(sorted(observed_by_family.items())),
        "supplement_compact_events_by_setup_stratum": dict(
            sorted(observed_by_stratum.items())
        ),
        "supplement_exposure_TT_s_by_family": supplement.exposure_by_family,
        "duplicate_audit": supplement.duplicate_audit,
        "output_policy": "NON_OVERWRITING__OUTPUT_DIRECTORY_MUST_NOT_EXIST",
    }


def integration_family_plan(
    base: BaseCatalog, supplement: SupplementManifest
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for family in FAMILIES:
        old_exposure = base.old_exposure_by_family[family]
        supplement_exposure = supplement.exposure_by_family[family]
        total_exposure = old_exposure + supplement_exposure
        unified_weight = 1.0 / total_exposure
        result[family] = {
            "old_exposure_TT_s": old_exposure,
            "supplement_exposure_TT_s": supplement_exposure,
            "supplement_exposure_TT_s_by_setup_stratum": (
                supplement.exposure_by_family_stratum[family]
            ),
            "combined_exposure_TT_s": total_exposure,
            "unified_event_weight_cps": unified_weight,
            "old_detector_positive_events": int(base.prompt_rows[family]["event_count"]),
            "old_jobs": sum(1 for row in base.old_jobs if row["family"] == family),
            "supplement_jobs": sum(1 for job in supplement.jobs if job.family == family),
            "supplement_transport_events": sum(
                job.transport_events for job in supplement.jobs if job.family == family
            ),
        }
    return result


def build_catalog(
    base: BaseCatalog,
    supplement: SupplementManifest,
    stage: Path,
) -> dict[str, Any]:
    payload_dtypes = {
        field: np.asarray(base.arrays[field]).dtype for field in base.payload_fields
    }
    hit_dtypes = {field: np.asarray(base.arrays[field]).dtype for field in HIT_FIELDS}
    assembler = CatalogAssembler(base.payload_fields, payload_dtypes, hit_dtypes)
    family_plan = integration_family_plan(base, supplement)
    jobs_by_family_stratum: dict[str, dict[str, list[SupplementJob]]] = {
        family: defaultdict(list) for family in FAMILIES
    }
    for job in supplement.jobs:
        jobs_by_family_stratum[job.family][job.setup_stratum].append(job)

    new_categories: list[dict[str, Any]] = []
    integrated_families: dict[str, dict[str, Any]] = {}
    consumed_jobs: set[str] = set()
    supplemental_event_total = 0
    supplemental_hit_total = 0

    for old_row in base.categories:
        family = str(old_row.get("family", ""))
        is_integrated = old_row.get("stream") == "prompt" and family in FAMILY_SET
        if not is_integrated:
            old_start = int(old_row["event_start"])
            old_count = int(old_row["event_count"])
            selector = slice(old_start, old_start + old_count)
            new_id = len(new_categories)
            start, count, stats = assembler.append(
                base.arrays,
                category_id=new_id,
                weights=np.asarray(base.arrays["event_base_weight_cps"])[selector],
                component=np.asarray(base.arrays["event_component"])[selector],
                source_bin80=np.asarray(base.arrays["source_bin80"])[selector],
                continuum_importance=np.asarray(
                    base.arrays["continuum_importance_weight"]
                )[selector],
                event_slice=selector,
            )
            if count != old_count:
                raise RuntimeError("unchanged P67 category event count changed")
            source = dict(old_row)
            source["integration_original_category_id"] = int(old_row["category_id"])
            new_categories.append(
                category_with_stats(
                    source,
                    category_id=new_id,
                    event_start=start,
                    stats=stats,
                )
            )
            continue

        plan = family_plan[family]
        unified_weight = float(plan["unified_event_weight_cps"])
        stratum_jobs = jobs_by_family_stratum[family]
        ordered_strata = ["main"] + sorted(name for name in stratum_jobs if name != "main")
        family_event_count = 0
        family_hit_count = 0
        stratum_summaries: dict[str, dict[str, Any]] = {}
        for stratum in ordered_strata:
            jobs = stratum_jobs.get(stratum, [])
            has_old_block = stratum == "main"
            if not has_old_block and not jobs:
                continue
            new_id = len(new_categories)
            category_start = assembler.events
            category_events = 0
            category_hits_before = assembler.hits
            if has_old_block:
                old_start = int(old_row["event_start"])
                old_count = int(old_row["event_count"])
                _, appended, _ = assembler.append(
                    base.arrays,
                    category_id=new_id,
                    weights=unified_weight,
                    component=base.component_id_by_name["other"],
                    source_bin80=base.source_bin80_not_applicable,
                    continuum_importance=1.0,
                    event_slice=slice(old_start, old_start + old_count),
                )
                if appended != old_count:
                    raise RuntimeError(f"old prompt block count changed for {family}")
                category_events += appended

            job_event_count = 0
            job_hit_count = 0
            for job in jobs:
                arrays = validate_job_arrays(job, base.payload_fields, payload_dtypes)
                before_hits = assembler.hits
                _, appended, _ = assembler.append(
                    arrays,
                    category_id=new_id,
                    weights=unified_weight,
                    component=base.component_id_by_name["other"],
                    source_bin80=base.source_bin80_not_applicable,
                    continuum_importance=1.0,
                )
                job_event_count += appended
                job_hit_count += assembler.hits - before_hits
                consumed_jobs.add(job.job_id)
                print(
                    json.dumps(
                        {
                            "model": base.model,
                            "family": family,
                            "setup_stratum": stratum,
                            "supplement_job": job.job_id,
                            "detector_positive_events": appended,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )
            category_events += job_event_count
            if category_events == 0:
                # Exposure from an all-zero stratum still belongs in the family
                # denominator, but an empty category is not added to P67.
                stratum_summaries[stratum] = {
                    "category_id": None,
                    "events": 0,
                    "hits": 0,
                    "supplement_jobs": len(jobs),
                    "supplement_job_ids": [job.job_id for job in jobs],
                    "exposure_TT_s": sum(job.exposure_TT_s for job in jobs),
                    "status": "NO_DETECTOR_POSITIVE_EVENTS__EXPOSURE_RETAINED",
                }
                continue
            category_stats = aggregate_constant_stats(category_events, unified_weight)
            source: dict[str, Any]
            if has_old_block:
                source = dict(old_row)
                source["integration_original_category_id"] = int(old_row["category_id"])
            else:
                source = {
                    "stream": "prompt",
                    "family": family,
                    "source_parent_ZA": -1,
                    "component": "other",
                }
            source.update(
                {
                    "setup_stratum": stratum,
                    # Exact P67 consumer contract; the extended policy is
                    # recorded separately below.
                    "weight_policy": "constant_category_weight",
                    "integration_weight_policy": "constant_family_weight__unified_old_plus_supplement_exposure",
                    "base_event_weight_cps": unified_weight,
                    "family_combined_exposure_TT_s": float(plan["combined_exposure_TT_s"]),
                    "family_old_exposure_TT_s": float(plan["old_exposure_TT_s"]),
                    "family_supplement_exposure_TT_s": float(plan["supplement_exposure_TT_s"]),
                    "stratum_supplement_exposure_TT_s": sum(
                        job.exposure_TT_s for job in jobs
                    ),
                    "supplement_jobs": len(jobs),
                    "supplement_job_ids": [job.job_id for job in jobs],
                    "supplement_transport_events": sum(job.transport_events for job in jobs),
                }
            )
            new_categories.append(
                category_with_stats(
                    source,
                    category_id=new_id,
                    event_start=category_start,
                    stats=category_stats,
                )
            )
            category_hits = assembler.hits - category_hits_before
            family_event_count += category_events
            family_hit_count += category_hits
            supplemental_event_total += job_event_count
            supplemental_hit_total += job_hit_count
            stratum_summaries[stratum] = {
                "category_id": new_id,
                "events": category_events,
                "hits": category_hits,
                "old_events": int(old_row["event_count"]) if has_old_block else 0,
                "supplement_events": job_event_count,
                "supplement_hits": job_hit_count,
                "supplement_jobs": len(jobs),
                "supplement_job_ids": [job.job_id for job in jobs],
                "exposure_TT_s": sum(job.exposure_TT_s for job in jobs),
                "status": "PASS__SETUP_STRATUM_PRESERVED",
            }

        family_stats = aggregate_constant_stats(family_event_count, unified_weight)
        integrated_families[family] = {
            **plan,
            "detector_positive_events": family_event_count,
            "hits": family_hit_count,
            "sumw_cps": float(family_stats["sumw_cps"]),
            "sumw2_cps2": float(family_stats["sumw2_cps2"]),
            "effective_sample_size": float(family_stats["effective_sample_size"]),
            "setup_strata": stratum_summaries,
            "status": "PASS__UNIFIED_OLD_PLUS_SUPPLEMENT_EXPOSURE",
        }

    if consumed_jobs != {job.job_id for job in supplement.jobs}:
        missing = sorted({job.job_id for job in supplement.jobs} - consumed_jobs)
        extra = sorted(consumed_jobs - {job.job_id for job in supplement.jobs})
        raise RuntimeError(f"supplement job consumption does not close: missing={missing}, extra={extra}")
    if set(integrated_families) != FAMILY_SET:
        raise RuntimeError("not all seven prompt families were integrated")

    output_arrays = assembler.finalize()
    validate_category_rows(output_arrays, new_categories, base.component_id_by_name)
    component_stats = component_statistics(output_arrays, base.component_id_by_name)
    expected_events = int(base.summary["events"]) + supplemental_event_total
    expected_hits = int(base.summary["hits"]) + supplemental_hit_total
    if assembler.events != expected_events or assembler.hits != expected_hits:
        raise RuntimeError(
            "integrated catalog does not equal base plus supplement compacts: "
            f"events {assembler.events}!={expected_events}, "
            f"hits {assembler.hits}!={expected_hits}"
        )

    # Components that were not targeted must be numerically invariant.
    for name in ("gamma_continuum", "atm511"):
        validate_component_stats(
            {name: component_stats[name]},
            {name: base.summary["components"][name]},
            f"unchanged component {name}",
        )
    base_other_events = int(base.summary["components"]["other"]["events"])
    expected_other_events = base_other_events + supplemental_event_total
    if int(component_stats["other"]["events"]) != expected_other_events:
        raise RuntimeError(
            "other-component event count does not equal base plus supplement: "
            f"{component_stats['other']['events']} != {expected_other_events}"
        )

    save_npz_atomic(stage / "combined_event_catalog.npz", output_arrays)
    category_registry = copy.deepcopy(base.category_registry)
    category_registry["weight_authority"] = (
        "combined_event_catalog.npz:event_base_weight_cps"
    )
    category_registry["integration_schema"] = INTEGRATION_SCHEMA
    category_registry["integration_provenance"] = "integration_provenance.json"
    category_registry["categories"] = new_categories
    write_json(stage / "category_registry.json", category_registry)
    write_json(stage / "component_registry.json", base.component_registry)

    created = datetime.now(timezone.utc).isoformat()
    provenance = {
        "schema": INTEGRATION_SCHEMA,
        "status": "PASS__INTEGRATION_PROVENANCE",
        "created_utc": created,
        "model": base.model,
        "quality_model": MODEL_LABEL[base.model],
        "scope": {
            "reweighted_and_augmented": "other/prompt: alpha, eminus, eplus, muminus, muplus, n, p",
            "preserved": ["all delayed categories", "gamma_continuum", "atm511"],
            "normalization": "one family weight = 1/(retained TT + supplement TT across setup strata)",
            "setup_stratum_policy": "separate category marks with a common family weight",
        },
        "base_p67": {
            "catalog_dir": str(base.catalog_dir),
            "catalog": str(base.catalog_dir / "combined_event_catalog.npz"),
            "category_registry": str(base.catalog_dir / "category_registry.json"),
            "component_registry": str(base.catalog_dir / "component_registry.json"),
            "audit": str(base.catalog_dir / "audit.json"),
            "summary": str(base.catalog_dir / "summary.json"),
            "audit_sha256": sha256_file(base.catalog_dir / "audit.json"),
            "summary_sha256": sha256_file(base.catalog_dir / "summary.json"),
            "status": base.summary["status"],
            "events": int(base.summary["events"]),
            "hits": int(base.summary["hits"]),
        },
        "retained_mature_prompt_lineage": {
            "summary": str(base.mature_summary_path),
            "summary_sha256": sha256_file(base.mature_summary_path),
            "jobs": len(base.old_jobs),
            "unique_batch_job_keys": len(
                {
                    (str(row.get("batch_id", "")), str(row["job_id"]))
                    for row in base.old_jobs
                }
            ),
            "unique_seeds": len({int(row["seed"]) for row in base.old_jobs}),
        },
        "supplement": {
            "manifests": [
                {
                    "path": str(path),
                    "sha256": sha256_file(path),
                    "schema": schema_name(raw),
                    "status": raw["status"],
                    "model": raw.get("model"),
                    "setup_stratum": raw.get("setup_stratum"),
                }
                for path, raw in zip(supplement.paths, supplement.raw_manifests)
            ],
            "jobs": len(supplement.jobs),
            "transport_events": sum(job.transport_events for job in supplement.jobs),
            "compact_detector_positive_events": supplemental_event_total,
            "compact_hits": supplemental_hit_total,
            "setup_strata": dict(Counter(job.setup_stratum for job in supplement.jobs)),
        },
        "duplicate_audit": supplement.duplicate_audit,
        "families": integrated_families,
        "output": {
            "events": assembler.events,
            "hits": assembler.hits,
            "categories": len(new_categories),
            "components": component_stats,
            "event_fields": [*base.payload_fields, *GENERATED_EVENT_FIELDS],
            "hit_fields": list(HIT_FIELDS),
        },
        "non_overwrite_policy": "output created via a new sibling stage directory and atomic directory rename",
    }
    write_json(stage / "integration_provenance.json", provenance)

    audit = copy.deepcopy(base.audit)
    audit.update(
        {
            "status": PASS_STATUS,
            "integration_status": INTEGRATION_PASS_STATUS,
            "model": base.model,
            "integration_schema": INTEGRATION_SCHEMA,
            "integration_provenance": "integration_provenance.json",
            "base_fluxclosed_audit": {
                "path": str(base.catalog_dir / "audit.json"),
                "sha256": sha256_file(base.catalog_dir / "audit.json"),
                "status": base.audit["status"],
            },
            "supplement_manifests": [
                {
                    "path": str(path),
                    "sha256": sha256_file(path),
                    "schema": schema_name(raw),
                    "status": raw["status"],
                    "model": raw.get("model"),
                    "setup_stratum": raw.get("setup_stratum"),
                }
                for path, raw in zip(supplement.paths, supplement.raw_manifests)
            ],
            "duplicate_audit": supplement.duplicate_audit,
            "prompt_family_integration": integrated_families,
            "retained_other_events": int(component_stats["other"]["events"]),
            "components": component_stats,
            "output_schema": {
                "original_event_fields": list(base.payload_fields),
                "original_hit_fields": list(HIT_FIELDS),
                "added_event_fields": [
                    "event_base_weight_cps",
                    "event_component",
                    "source_bin80",
                    "continuum_importance_weight",
                ],
                "event_count": assembler.events,
                "hit_count": assembler.hits,
                "event_base_weight_dtype": str(
                    output_arrays["event_base_weight_cps"].dtype
                ),
                "event_component_dtype": str(output_arrays["event_component"].dtype),
                "source_bin80_dtype": str(output_arrays["source_bin80"].dtype),
            },
        }
    )
    write_json(stage / "audit.json", audit)

    summary = copy.deepcopy(base.summary)
    summary.update(
        {
            "status": COMPLETE_STATUS,
            "integration_status": INTEGRATION_PASS_STATUS,
            "integration_schema": INTEGRATION_SCHEMA,
            "integration_provenance": "integration_provenance.json",
            "events": assembler.events,
            "hits": assembler.hits,
            "categories": len(new_categories),
            "components": component_stats,
            "prompt_family_integration": integrated_families,
            "supplement_jobs": len(supplement.jobs),
            "supplement_detector_positive_events": supplemental_event_total,
            "supplement_hits": supplemental_hit_total,
            "catalog": "combined_event_catalog.npz",
            "category_registry": "category_registry.json",
            "component_registry": "component_registry.json",
            "audit": "audit.json",
        }
    )
    write_json(stage / "summary.json", summary)
    return summary


def validate_output_location(output: Path, base: BaseCatalog, supplement: SupplementManifest) -> Path:
    output = output.expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"non-overwrite policy: output already exists: {output}")
    protected = (base.catalog_dir.resolve(), *(root.resolve() for root in supplement.roots))
    for path in protected:
        if output == path:
            raise RuntimeError(f"output equals a protected input directory: {path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    return output


def run_self_test() -> None:
    payload_fields = REQUIRED_RESPONSE_FIELDS
    payload_dtypes = {
        "plastic_keV": np.dtype(np.float32),
        "bgo_keV": np.dtype(np.float32),
        "measured_total_keV": np.dtype(np.float32),
        "broad_flags": np.dtype(np.uint8),
        "w2_flags": np.dtype(np.uint8),
        "hit_start": np.dtype(np.int64),
        "hit_count": np.dtype(np.uint16),
    }
    hit_dtypes = {
        "hit_code": np.dtype(np.int32),
        "hit_layer": np.dtype(np.uint8),
        "hit_energy_keV": np.dtype(np.float32),
        "hit_x_cm": np.dtype(np.float32),
        "hit_y_cm": np.dtype(np.float32),
        "hit_z_cm": np.dtype(np.float32),
    }
    arrays: dict[str, np.ndarray] = {
        "plastic_keV": np.asarray([0.0, 4.0, 0.0], dtype=np.float32),
        "bgo_keV": np.asarray([1.0, 0.0, 2.0], dtype=np.float32),
        "measured_total_keV": np.asarray([0.0, 511.0, 0.0], dtype=np.float32),
        "broad_flags": np.asarray([0, 1, 0], dtype=np.uint8),
        "w2_flags": np.asarray([0, 1, 0], dtype=np.uint8),
        "hit_start": np.asarray([0, 0, 2], dtype=np.int64),
        "hit_count": np.asarray([0, 2, 1], dtype=np.uint16),
        "hit_code": np.asarray([1, 2, 3], dtype=np.int32),
        "hit_layer": np.asarray([0, 1, 2], dtype=np.uint8),
        "hit_energy_keV": np.asarray([1.0, 2.0, 3.0], dtype=np.float32),
        "hit_x_cm": np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
        "hit_y_cm": np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
        "hit_z_cm": np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
    }
    validate_hit_ranges(arrays, "self-test input")
    assembler = CatalogAssembler(payload_fields, payload_dtypes, hit_dtypes)
    start, count, stats = assembler.append(
        arrays,
        category_id=0,
        weights=0.25,
        component=0,
        source_bin80=255,
        continuum_importance=1.0,
    )
    assert start == 0 and count == 3
    assert close(float(stats["sumw_cps"]), 0.75)
    output = assembler.finalize()
    assert len(output["event_category"]) == 3
    assert np.array_equal(output["hit_start"], arrays["hit_start"])
    assert np.array_equal(output["hit_code"], arrays["hit_code"])
    assert normalize_setup_stratum("minimal-sensitive-detectors") == "minimal_sd"
    constant = aggregate_constant_stats(7, 0.5)
    assert close(float(constant["effective_sample_size"]), 7.0)

    def synthetic_job(
        job_id: str, seed: int, family: str, stratum: str
    ) -> SupplementJob:
        return SupplementJob(
            job_id=job_id,
            scan_index=seed,
            seed=seed,
            family=family,
            setup_stratum=stratum,
            exposure_TT_s=1.0,
            transport_events=10,
            detector_positive_events=1,
            source_sha256=f"{seed:064x}",
            cache_npz=Path(f"/synthetic/{job_id}.npz"),
            cache_json=Path(f"/synthetic/{job_id}.json"),
            raw={},
        )

    main_jobs = [
        synthetic_job(f"main_{family}", index + 100, family, "main")
        for index, family in enumerate(FAMILIES)
    ]
    minimal_job = synthetic_job("minimal_alpha", 200, "alpha", "minimal_sd")
    empty_exposure = {family: 0.0 for family in FAMILIES}
    main_exposure = {family: 1.0 for family in FAMILIES}
    main_manifest = SupplementManifest(
        model="a",
        roots=(Path("/synthetic/main"),),
        paths=(Path("/synthetic/main/jobs.json"),),
        raw_manifests=({},),
        jobs=main_jobs,
        exposure_by_family=main_exposure,
        exposure_by_family_stratum={family: {"main": 1.0} for family in FAMILIES},
        duplicate_audit={},
    )
    minimal_exposure = dict(empty_exposure)
    minimal_exposure["alpha"] = 1.0
    minimal_manifest = SupplementManifest(
        model="a",
        roots=(Path("/synthetic/minimal"),),
        paths=(Path("/synthetic/minimal/jobs.json"),),
        raw_manifests=({},),
        jobs=[minimal_job],
        exposure_by_family=minimal_exposure,
        exposure_by_family_stratum={
            family: ({"minimal_sd": 1.0} if family == "alpha" else {})
            for family in FAMILIES
        },
        duplicate_audit={},
    )
    dummy_base = type(
        "DummyBase",
        (),
        {
            "old_jobs": [
                {"job_id": f"old_{family}", "seed": index + 1}
                for index, family in enumerate(FAMILIES)
            ]
        },
    )()
    combined = combine_supplement_manifests(
        "a", (main_manifest, minimal_manifest), dummy_base
    )
    assert len(combined.jobs) == 8
    assert close(combined.exposure_by_family["alpha"], 2.0)
    assert combined.exposure_by_family_stratum["alpha"] == {
        "main": 1.0,
        "minimal_sd": 1.0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=("a", "b"), required=True)
    parser.add_argument(
        "--supplement-root",
        type=Path,
        help="package/root used to locate the main model jobs.json",
    )
    parser.add_argument(
        "--supplement-jobs",
        type=Path,
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "explicit jobs.json (repeat for independent setup strata, e.g. "
            "SG3 main plus SG3 minimal-SD)"
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--check-inputs",
        action="store_true",
        help="validate exact manifest members and print a report; write nothing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_sources: list[Path] = []
    if args.supplement_root is not None:
        manifest_sources.append(args.supplement_root)
    manifest_sources.extend(args.supplement_jobs)
    if not manifest_sources:
        raise RuntimeError(
            "at least one --supplement-root or --supplement-jobs PATH is required"
        )
    base = load_base_catalog(args.model)
    supplement = combine_supplement_manifests(
        args.model,
        [
            load_supplement_manifest(args.model, source, base)
            for source in manifest_sources
        ],
        base,
    )
    if args.check_inputs:
        print(json.dumps(preflight_report(base, supplement), indent=2, sort_keys=True))
        return 0

    output = validate_output_location(args.output_dir, base, supplement)
    stage = output.parent / f".{output.name}.stage-{os.getpid()}"
    if stage.exists():
        raise FileExistsError(f"non-overwrite policy: stage already exists: {stage}")
    stage.mkdir()
    summary = build_catalog(base, supplement, stage)
    publish_directory_noreplace(stage, output)
    print(json.dumps({**summary, "output": str(output)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
