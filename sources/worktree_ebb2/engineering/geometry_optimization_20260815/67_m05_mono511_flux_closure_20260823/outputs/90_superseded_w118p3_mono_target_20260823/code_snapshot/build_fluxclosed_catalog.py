#!/usr/bin/env python3
"""Build the positive, flux-closed M05 background event catalogs.

For each model this program keeps every mature-catalog category except the
*prompt* broadband-gamma category, reconstructs that category from the exact
job membership recorded in the mature summaries, and streams each referenced
raw SIM to join detector-positive event IDs to their ``IA INIT`` energy and
direction.  The prompt-gamma proposal weight is multiplied by the W=118.3
matched-grid ``J_cont/J_total`` ratio from ``outputs/00_source_closure``.  The
separately transported mono-511 detector-positive catalog is then appended at
``1/sum(T_E)`` while retaining its 80-bin source identity.

The old mature catalogs and caches are read-only inputs.  Output is staged and
renamed into a new directory; an existing destination is never overwritten.
Raw SIM files are streamed and are deliberately not hashed or loaded whole.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]

SOURCE_CLOSURE_DIR = PACKAGE / "outputs/00_source_closure"
SOURCE_CLOSURE_JSON = SOURCE_CLOSURE_DIR / "source_closure.json"
SOURCE_CLOSURE_BINS = SOURCE_CLOSURE_DIR / "coarse_line_decomposition_20bins.csv"
MONO_TARGET_81X80 = SOURCE_CLOSURE_DIR / "mono511_target_81x80.csv"
SOURCE_CONTRACT = ROOT / "engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json"

A_BASE = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "62_sg3b_mature_poisson_timeline_20260818/outputs/01_event_catalog"
)
A_SUPPLEMENT = ROOT / (
    "engineering/geometry_optimization_20260815/"
    "63_m05new_sg3b_signal_statistics_20260820/outputs/03_expanded_catalog"
)
B_MATURE = ROOT / "DEEPSEEK_CODE/outputs/04_event_catalog_step05_m05_fixed_20260820"

LINE_DIRS = {
    "a": PACKAGE / "outputs/01_line_response_a",
    "b": PACKAGE / "outputs/01_line_response_b60",
}
DEFAULT_OUTPUTS = {
    "a": PACKAGE / "outputs/02_fluxclosed_catalog_a",
    "b": PACKAGE / "outputs/02_fluxclosed_catalog_b",
}
DEFAULT_INIT_CACHES = {
    "a": PACKAGE / "outputs/02_fluxclosed_init_cache_a",
    "b": PACKAGE / "outputs/02_fluxclosed_init_cache_b",
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
ADDED_EVENT_FIELDS = (
    "event_base_weight_cps",
    "event_component",
    "source_bin80",
    "continuum_importance_weight",
)

COMPONENT_OTHER = 0
COMPONENT_GAMMA_CONTINUUM = 1
COMPONENT_ATM511 = 2
SOURCE_BIN80_NOT_APPLICABLE = np.uint8(255)

LEFT_KEV = 449.65
NODE_KEV = 566.08
RIGHT_KEV = 712.64
INTERNAL_DIR_Z_BOUNDARIES = np.asarray(
    [-1.0 + 0.1 * index for index in range(1, 20)], dtype=np.float64
)
# IA INIT directions are printed to five decimal places.  Values within half
# a print quantum (plus a small parsing margin) are reported as boundary
# candidates, while the deterministic half-open bin assignment is retained.
BOUNDARY_DIR_Z_TOLERANCE = 5.1e-6

EXPECTED = {
    "a": {
        "base_gamma_jobs": 8,
        "supplement_gamma_jobs": 32,
        "gamma_jobs": 40,
        "gamma_detector_positive": 6_372_612,
    },
    "b": {
        "gamma_jobs": 280,
        "gamma_detector_positive": 4_189_660,
    },
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_display(path: Path) -> str:
    path = path.resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def resolve_recorded_path(value: str | Path) -> Path:
    """Resolve stale worktree/repository paths against this script's root.

    External paths (notably /mnt SIMs) remain external.  A recorded path whose
    components contain an exact ``TES_511_Balloon`` repository directory is
    first mapped to the current root, and falls back to the recorded path only
    when that root-relative object is absent.
    """

    recorded = Path(value).expanduser()
    parts = recorded.parts
    if "TES_511_Balloon" in parts:
        marker = len(parts) - 1 - tuple(reversed(parts)).index("TES_511_Balloon")
        candidate = ROOT.joinpath(*parts[marker + 1 :])
        if candidate.exists():
            return candidate.resolve()
    if recorded.exists():
        return recorded.resolve()
    if not recorded.is_absolute():
        candidate = ROOT / recorded
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"recorded input does not resolve: {value}")


def effective_sample_size(sumw: float, sumw2: float) -> float:
    return sumw * sumw / sumw2 if sumw2 > 0.0 else 0.0


def weight_stats(values: np.ndarray) -> dict[str, float | int]:
    weights = np.asarray(values, dtype=np.float64)
    if weights.ndim != 1 or not np.all(np.isfinite(weights)) or np.any(weights <= 0.0):
        raise RuntimeError("event weights must be a finite, strictly positive vector")
    sumw = float(np.sum(weights, dtype=np.float64))
    sumw2 = float(np.sum(weights * weights, dtype=np.float64))
    return {
        "events": int(len(weights)),
        "sumw_cps": sumw,
        "sumw2_cps2": sumw2,
        "effective_sample_size": effective_sample_size(sumw, sumw2),
        "minimum_event_weight_cps": float(np.min(weights)) if len(weights) else math.nan,
        "maximum_event_weight_cps": float(np.max(weights)) if len(weights) else math.nan,
    }


def as_event_vector(value: float | int | np.ndarray, count: int, dtype: np.dtype[Any]) -> np.ndarray:
    if np.isscalar(value):
        return np.full(count, value, dtype=dtype)
    result = np.asarray(value, dtype=dtype)
    if result.shape != (count,):
        raise RuntimeError(f"event-vector shape mismatch: {result.shape} != {(count,)}")
    return result


def prompt_gamma_category(categories: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [
        dict(row)
        for row in categories
        if row.get("stream") == "prompt" and row.get("family") == "gamma"
    ]
    if len(rows) != 1:
        raise RuntimeError(f"expected one prompt-gamma category, found {len(rows)}")
    return rows[0]


@dataclass(frozen=True)
class GammaJob:
    authority_group: str
    batch_id: str
    job_id: str
    scan_index: int
    seed: int
    events: int
    detector_positive_events: int
    sim_path: Path
    sim_bytes: int
    catalog_path: Path
    metadata_source: Path


class SourceClosure:
    """Matched-grid W=118.3 continuum/total importance evaluator."""

    def __init__(self) -> None:
        manifest = load_json(SOURCE_CLOSURE_JSON)
        required_manifest = {
            "status",
            "coarse_line",
            "source_reference_closure",
            "mono511_target",
        }
        missing = sorted(required_manifest - set(manifest))
        if missing:
            raise RuntimeError(
                "source closure is not the confirmed W=118.3 matched-grid output; "
                f"missing keys: {missing}"
            )
        if manifest["status"] != "COMPLETE__EXACT_COARSE_SUBTRACTION__OFFICIAL_W118P3_MONO_81X80":
            raise RuntimeError(f"source closure is not complete: {manifest['status']}")
        coarse = manifest["coarse_line"]
        basis = f"{coarse.get('definition', '')}; {coarse.get('interpolation', '')}"
        if "W=118.3" not in basis or "IP LIN" not in basis:
            raise RuntimeError(f"unexpected source-closure basis: {basis}")
        if int(coarse["negative_continuum_flux_or_importance_count"]) != 0:
            raise RuntimeError("source closure reports non-positive continuum weights")

        rows = read_csv(SOURCE_CLOSURE_BINS)
        required_columns = {
            "source_bin20",
            "line_node_total_density_ph_cm2_s_keV",
            "line_node_continuum_density_ph_cm2_s_keV",
            "line_node_continuum_importance_ratio",
        }
        if len(rows) != 20 or not rows or not required_columns.issubset(rows[0]):
            raise RuntimeError("source closure does not contain the confirmed 20-bin matched grid")
        rows.sort(key=lambda row: int(row["source_bin20"]))
        if [int(row["source_bin20"]) for row in rows] != list(range(20)):
            raise RuntimeError("source-closure angular bins are not exactly 0..19")

        self.manifest = manifest
        self.basis = basis
        self.grids: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
        contract = load_json(SOURCE_CONTRACT)
        gamma_card = next(
            row
            for row in contract["geometries"]["mass_model_511"]["cards"]
            if row["family"] == "gamma"
        )
        spectra = [ROOT / value for value in gamma_card["spectrum_files"]]
        source_card = ROOT / gamma_card["source"]
        flux_by_bin: dict[int, float] = {}
        for line in source_card.read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if len(fields) == 2 and fields[0].startswith("Atm_gamma_bin") and fields[0].endswith(".Flux"):
                bin_id = int(fields[0].split("_bin", 1)[1][:2])
                flux_by_bin[bin_id] = float(fields[1])
        if len(spectra) != 20 or sorted(flux_by_bin) != list(range(20)):
            raise RuntimeError("current gamma source authority is not the expected 20-bin set")
        grid_minimum = 1.0
        for bin_id, row in enumerate(rows):
            path = spectra[bin_id]
            if not path.is_file():
                raise RuntimeError(f"current gamma spectrum is missing: {path}")
            energy: list[float] = []
            total: list[float] = []
            lines = path.read_text(encoding="utf-8").splitlines()
            if "IP LIN" not in lines:
                raise RuntimeError(f"current gamma spectrum is not IP LIN: {path}")
            for line in lines:
                fields = line.split()
                if len(fields) == 3 and fields[0] == "DP":
                    energy.append(float(fields[1]))
                    total.append(float(fields[2]))
            x = np.asarray(energy, dtype=np.float64)
            pdf = np.asarray(total, dtype=np.float64)
            rounded_integral = float(np.trapezoid(pdf, x))
            y_total = pdf * flux_by_bin[bin_id] / rounded_integral
            if len(x) < 3 or not np.all(np.diff(x) > 0.0) or np.any(y_total < 0.0):
                raise RuntimeError(f"invalid gamma source grid: {path}")
            node_candidates = np.flatnonzero(np.isclose(x, NODE_KEV, rtol=0.0, atol=1e-12))
            if len(node_candidates) != 1:
                raise RuntimeError(f"566.08-keV node count in bin {bin_id}: {len(node_candidates)}")
            node = int(node_candidates[0])
            recorded_total = float(row["line_node_total_density_ph_cm2_s_keV"])
            current_total = float(y_total[node])
            if not math.isclose(recorded_total, current_total, rel_tol=2e-12, abs_tol=1e-18):
                raise RuntimeError(f"source-closure/raw node mismatch in bin {bin_id}")
            continuum_node = float(row["line_node_continuum_density_ph_cm2_s_keV"])
            if not 0.0 < continuum_node <= recorded_total:
                raise RuntimeError(f"non-positive continuum node in bin {bin_id}")
            recorded_ratio = float(row["line_node_continuum_importance_ratio"])
            if not math.isclose(
                continuum_node / recorded_total, recorded_ratio, rel_tol=2e-12, abs_tol=2e-15
            ):
                raise RuntimeError(f"source-closure node ratio mismatch in bin {bin_id}")
            y_continuum = y_total.copy()
            y_continuum[node] = continuum_node
            dense = np.unique(np.concatenate((
                x,
                np.asarray([NODE_KEV], dtype=np.float64),
                np.linspace(LEFT_KEV, RIGHT_KEV, 4097, dtype=np.float64),
            )))
            dense_total = np.interp(dense, x, y_total)
            dense_continuum = np.interp(dense, x, y_continuum)
            support = (
                (dense > LEFT_KEV)
                & (dense < RIGHT_KEV)
                & (dense_total > 0.0)
            )
            ratios = dense_continuum[support] / dense_total[support]
            if np.any(~np.isfinite(ratios)) or np.any(ratios <= 0.0) or np.any(ratios > 1.0 + 1e-12):
                raise RuntimeError(f"invalid matched-grid continuum ratio in bin {bin_id}")
            grid_minimum = min(grid_minimum, float(np.min(ratios)))
            self.grids.append((x, y_total, y_continuum))
        if not math.isclose(
            grid_minimum,
            float(coarse["minimum_event_importance_ratio_Jcont_over_Jtotal"]),
            rel_tol=2e-8,
            abs_tol=2e-10,
        ):
            raise RuntimeError(
                "reconstructed matched-grid minimum differs from source_closure.json: "
                f"{grid_minimum} vs {coarse['minimum_event_importance_ratio_Jcont_over_Jtotal']}"
            )
        self.grid_minimum = grid_minimum

    def importance(self, bins20: np.ndarray, energy_keV: np.ndarray) -> np.ndarray:
        bins = np.asarray(bins20, dtype=np.int16)
        energy = np.asarray(energy_keV, dtype=np.float64)
        if bins.shape != energy.shape or bins.ndim != 1:
            raise RuntimeError("importance input shapes differ")
        if np.any((bins < 0) | (bins >= 20)):
            raise RuntimeError("prompt-gamma source bin outside 0..19")
        if np.any(~np.isfinite(energy)) or np.any(energy <= 0.0):
            raise RuntimeError("invalid IA INIT energy")
        result = np.ones(len(energy), dtype=np.float64)
        for bin_id in range(20):
            mask = bins == bin_id
            if not np.any(mask):
                continue
            selected = energy[mask]
            x, y_total, y_continuum = self.grids[bin_id]
            if float(np.min(selected)) < float(x[0]) - 1e-9 or float(np.max(selected)) > float(x[-1]) + 1e-9:
                raise RuntimeError(f"gamma event energy outside proposal grid in bin {bin_id}")
            denominator = np.interp(selected, x, y_total)
            numerator = np.interp(selected, x, y_continuum)
            if np.any(denominator <= 0.0):
                raise RuntimeError(f"zero proposal density in source bin {bin_id}")
            result[mask] = numerator / denominator
        if np.any(~np.isfinite(result)) or np.any(result <= 0.0) or np.any(result > 1.0 + 1e-12):
            bad = result[(~np.isfinite(result)) | (result <= 0.0) | (result > 1.0 + 1e-12)]
            raise RuntimeError(f"non-positive/out-of-range continuum importance weights: {bad[:8]}")
        result[result > 1.0] = 1.0
        return result


def validate_mono_target() -> dict[str, Any]:
    rows = read_csv(MONO_TARGET_81X80)
    required = {
        "time_bin_id",
        "day_mid",
        "source_bin80",
        "target_flux_ph_cm2_s",
        "proposal_flux_ph_cm2_s",
        "importance_ratio",
    }
    if len(rows) != 81 * 80 or not rows or not required.issubset(rows[0]):
        raise RuntimeError("mono511_target_81x80.csv is absent or has the wrong schema/row count")
    keys: set[tuple[int, int]] = set()
    minimum = math.inf
    maximum = -math.inf
    for row in rows:
        node = int(row["time_bin_id"])
        source_bin = int(row["source_bin80"])
        key = (node, source_bin)
        if not 0 <= node < 81 or not 0 <= source_bin < 80 or key in keys:
            raise RuntimeError(f"invalid/duplicate mono target key: {key}")
        keys.add(key)
        target = float(row["target_flux_ph_cm2_s"])
        proposal = float(row["proposal_flux_ph_cm2_s"])
        ratio = float(row["importance_ratio"])
        if not all(math.isfinite(value) for value in (target, proposal, ratio)):
            raise RuntimeError(f"non-finite mono target row: {key}")
        if target <= 0.0 or proposal <= 0.0 or ratio <= 0.0:
            raise RuntimeError(f"non-positive mono target/proposal/ratio: {key}")
        if not math.isclose(target / proposal, ratio, rel_tol=2e-12, abs_tol=2e-14):
            raise RuntimeError(f"mono target ratio mismatch: {key}")
        minimum = min(minimum, ratio)
        maximum = max(maximum, ratio)
    if keys != {(node, source_bin) for node in range(81) for source_bin in range(80)}:
        raise RuntimeError("mono target does not span the complete 81x80 axis")
    return {
        "rows": len(rows),
        "minimum_importance_ratio": minimum,
        "maximum_importance_ratio": maximum,
        "sha256": sha256_file(MONO_TARGET_81X80),
    }


def source_bin20_from_dir_z(dir_z: np.ndarray) -> np.ndarray:
    values = np.asarray(dir_z, dtype=np.float64)
    if values.ndim != 1 or np.any(~np.isfinite(values)):
        raise RuntimeError("invalid IA INIT direction vector")
    if np.any(values < -1.0 - 1e-5) or np.any(values > 1.0 + 1e-5):
        raise RuntimeError("IA INIT dir_z lies outside [-1,1]")
    clipped = np.clip(values, -1.0, 1.0)
    # Source bin 0 is the near-vertical down-going cell (IA points inward,
    # dir_z approximately -1); bin 19 is near-vertical up-going.  Preserve the
    # exact source-closure contract, including its deterministic treatment of
    # five-decimal printed boundary candidates.
    bins = np.floor((1.0 + clipped) * 10.0).astype(np.int16)
    return np.clip(bins, 0, 19).astype(np.uint8)


def boundary_candidates(dir_z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(dir_z, dtype=np.float64)
    scaled = (values + 1.0) * 10.0
    nearest_index = np.rint(scaled).astype(np.int16)
    valid = (nearest_index >= 1) & (nearest_index <= 19)
    nearest_boundary = -1.0 + nearest_index.astype(np.float64) / 10.0
    delta = values - nearest_boundary
    mask = valid & (np.abs(delta) <= BOUNDARY_DIR_Z_TOLERANCE)
    return mask, nearest_boundary, delta


def recover_gamma_init(
    sim_path: Path, event_ids: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    ids = np.asarray(event_ids, dtype=np.int64)
    if ids.ndim != 1 or len(ids) == 0:
        raise RuntimeError(f"empty detector-positive event ID vector: {sim_path}")
    if len(np.unique(ids)) != len(ids):
        raise RuntimeError(f"duplicate detector-positive event IDs: {sim_path}")
    index_by_id = {int(event_id): index for index, event_id in enumerate(ids)}
    energy = np.full(len(ids), np.nan, dtype=np.float64)
    dir_z = np.full(len(ids), np.nan, dtype=np.float64)
    found = np.zeros(len(ids), dtype=bool)
    current_index: int | None = None
    duplicate_init = 0
    with gzip.open(sim_path, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            if raw.startswith("ID "):
                fields = raw.split()
                current_index = index_by_id.get(int(fields[1])) if len(fields) >= 2 else None
                continue
            if current_index is None or not raw.startswith("IA INIT"):
                continue
            fields = [value.strip() for value in raw.split(";")]
            if len(fields) <= 22:
                raise RuntimeError(f"malformed IA INIT for a wanted event in {sim_path}")
            if found[current_index]:
                duplicate_init += 1
                continue
            dir_z[current_index] = float(fields[18])
            energy[current_index] = float(fields[22])
            found[current_index] = True
    matched = int(np.count_nonzero(found))
    if duplicate_init or matched != len(ids):
        missing = ids[~found][:12].tolist()
        raise RuntimeError(
            f"IA INIT join failed for {sim_path}: matched={matched}/{len(ids)}, "
            f"duplicate_init={duplicate_init}, missing={missing}"
        )
    return energy, dir_z, {
        "wanted_detector_positive_events": int(len(ids)),
        "matched_ia_init_events": matched,
        "matching_rate": matched / len(ids),
        "duplicate_ia_init_events": duplicate_init,
    }


def array_sha256(values: np.ndarray) -> str:
    normalized = np.ascontiguousarray(np.asarray(values, dtype="<i8"))
    return hashlib.sha256(normalized.tobytes()).hexdigest()


def gamma_init_cache_key(job: GammaJob) -> str:
    identity = f"{job.authority_group}|{job.batch_id}|{job.scan_index}|{job.sim_path}"
    suffix = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
    readable = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "_",
        f"{job.authority_group}__{job.batch_id}__{job.scan_index:04d}__{job.job_id}",
    ).strip("_")
    return f"{readable}__{suffix}"


def recover_gamma_init_cached(
    init_cache_root: Path, job: GammaJob, event_ids: np.ndarray
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Recover IA INIT once and atomically publish a reusable per-job cache."""

    init_cache_root.mkdir(parents=True, exist_ok=True)
    cache_key = gamma_init_cache_key(job)
    cache_dir = init_cache_root / cache_key
    event_ids64 = np.asarray(event_ids, dtype=np.int64)
    event_id_hash = array_sha256(event_ids64)
    expected_receipt = {
        "schema_version": 1,
        "status": "COMPLETE__RECOVERED_GAMMA_IA_INIT",
        "authority_group": job.authority_group,
        "batch_id": job.batch_id,
        "job_id": job.job_id,
        "scan_index": job.scan_index,
        "seed": job.seed,
        "incident_events": job.events,
        "sim_path": str(job.sim_path),
        "sim_bytes": job.sim_bytes,
        "job_catalog_path": str(job.catalog_path),
        "job_catalog_bytes": job.catalog_path.stat().st_size,
        "metadata_source": str(job.metadata_source.resolve()),
        "metadata_source_sha256": sha256_file(job.metadata_source),
        "detector_positive_event_count": int(len(event_ids64)),
        "detector_positive_event_id_sha256": event_id_hash,
        "sim_hash_computed": False,
    }

    def validate_existing() -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
        receipt_path = cache_dir / "receipt.json"
        npz_path = cache_dir / "recovered_init.npz"
        if not cache_dir.is_dir() or not receipt_path.is_file() or not npz_path.is_file():
            raise RuntimeError(f"incomplete persistent INIT cache; refusing overwrite: {cache_dir}")
        receipt = load_json(receipt_path)
        failed = [
            key for key, value in expected_receipt.items()
            if receipt.get(key) != value
        ]
        if failed:
            raise RuntimeError(f"persistent INIT cache provenance mismatch {cache_key}: {failed}")
        if receipt.get("cache_npz_sha256") != sha256_file(npz_path):
            raise RuntimeError(f"persistent INIT cache hash mismatch: {cache_dir}")
        with np.load(npz_path, allow_pickle=False) as data:
            required = {"event_id", "incident_energy_keV", "incident_dir_z"}
            if not required.issubset(data.files):
                raise RuntimeError(f"persistent INIT cache schema mismatch: {cache_dir}")
            cached_ids = data["event_id"].astype(np.int64)
            energy = data["incident_energy_keV"].astype(np.float64)
            dir_z = data["incident_dir_z"].astype(np.float64)
        if not np.array_equal(cached_ids, event_ids64):
            raise RuntimeError(f"persistent INIT cache event IDs changed: {cache_dir}")
        if energy.shape != event_ids64.shape or dir_z.shape != event_ids64.shape:
            raise RuntimeError(f"persistent INIT cache vector shapes differ: {cache_dir}")
        if np.any(~np.isfinite(energy)) or np.any(~np.isfinite(dir_z)):
            raise RuntimeError(f"persistent INIT cache contains non-finite values: {cache_dir}")
        return energy, dir_z, {
            "wanted_detector_positive_events": int(len(event_ids64)),
            "matched_ia_init_events": int(len(event_ids64)),
            "matching_rate": 1.0,
            "duplicate_ia_init_events": 0,
            "init_cache_status": "REUSED",
            "init_cache": repo_display(cache_dir),
            "init_cache_receipt": repo_display(receipt_path),
        }

    if cache_dir.exists():
        return validate_existing()

    stage = Path(tempfile.mkdtemp(prefix=f".{cache_key}.staging-", dir=init_cache_root))
    try:
        energy, dir_z, audit = recover_gamma_init(job.sim_path, event_ids64)
        cache_npz = stage / "recovered_init.npz"
        with cache_npz.open("wb") as handle:
            np.savez_compressed(
                handle,
                event_id=event_ids64,
                incident_energy_keV=energy,
                incident_dir_z=dir_z,
            )
        receipt = {
            **expected_receipt,
            "matched_ia_init_events": int(audit["matched_ia_init_events"]),
            "matching_rate": float(audit["matching_rate"]),
            "duplicate_ia_init_events": int(audit["duplicate_ia_init_events"]),
            "cache_npz_sha256": sha256_file(cache_npz),
        }
        write_json(stage / "receipt.json", receipt)
        if cache_dir.exists():
            raise RuntimeError(f"persistent INIT cache appeared during recovery: {cache_dir}")
        stage.rename(cache_dir)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return energy, dir_z, {
        **audit,
        "init_cache_status": "CREATED",
        "init_cache": repo_display(cache_dir),
        "init_cache_receipt": repo_display(cache_dir / "receipt.json"),
    }


class CatalogAssembler:
    """Append response blocks while repacking referenced hit arrays."""

    def __init__(self, original_event_fields: Sequence[str]) -> None:
        fields = tuple(field for field in original_event_fields if field != "event_category")
        for required in REQUIRED_RESPONSE_FIELDS:
            if required not in fields:
                raise RuntimeError(f"mature catalog is missing response field: {required}")
        self.original_event_fields = fields
        self.event_chunks: dict[str, list[np.ndarray]] = {field: [] for field in fields}
        self.event_chunks.update({field: [] for field in ADDED_EVENT_FIELDS})
        self.event_category_chunks: list[np.ndarray] = []
        self.hit_chunks: dict[str, list[np.ndarray]] = {field: [] for field in HIT_FIELDS}
        self.event_count = 0
        self.hit_count = 0
        self.component_accumulator = {
            component: {"events": 0, "sumw_cps": 0.0, "sumw2_cps2": 0.0}
            for component in (COMPONENT_OTHER, COMPONENT_GAMMA_CONTINUUM, COMPONENT_ATM511)
        }

    def append(
        self,
        arrays: Mapping[str, np.ndarray],
        *,
        category_id: int,
        component: int,
        base_weights: float | np.ndarray,
        continuum_importance: float | np.ndarray,
        source_bin80: int | np.ndarray,
        event_slice: slice | np.ndarray | None = None,
    ) -> tuple[int, int, dict[str, float | int]]:
        selector: slice | np.ndarray = slice(None) if event_slice is None else event_slice
        counts = np.asarray(arrays["hit_count"])[selector].astype(np.uint16, copy=False)
        count = int(len(counts))
        if count <= 0:
            raise RuntimeError("refusing to append an empty catalog block")
        starts = np.asarray(arrays["hit_start"])[selector].astype(np.int64, copy=False)
        weights = as_event_vector(base_weights, count, np.dtype(np.float64))
        importance = as_event_vector(continuum_importance, count, np.dtype(np.float64))
        bins80 = as_event_vector(source_bin80, count, np.dtype(np.uint8))
        if np.any(~np.isfinite(weights)) or np.any(weights <= 0.0):
            raise RuntimeError("catalog block contains non-positive event weights")
        if np.any(~np.isfinite(importance)) or np.any(importance <= 0.0) or np.any(importance > 1.0 + 1e-12):
            raise RuntimeError("catalog block contains invalid continuum importance weights")

        per_event_offsets = np.empty(count, dtype=np.int64)
        per_event_offsets[0] = 0
        if count > 1:
            np.cumsum(counts[:-1], dtype=np.int64, out=per_event_offsets[1:])
        new_starts = per_event_offsets + self.hit_count
        positive = np.flatnonzero(counts)
        total_new_hits = int(np.sum(counts, dtype=np.int64))
        if len(positive):
            old_starts = starts[positive]
            old_counts = counts[positive].astype(np.int64)
            hit_length = len(np.asarray(arrays[HIT_FIELDS[0]]))
            if np.any(old_starts < 0) or np.any(old_starts + old_counts > hit_length):
                raise RuntimeError("event hit ranges exceed source hit arrays")
            contiguous = bool(
                len(positive) == 1
                or np.all(old_starts[1:] == old_starts[:-1] + old_counts[:-1])
            )
            for field in HIT_FIELDS:
                source = np.asarray(arrays[field])
                if len(source) != hit_length:
                    raise RuntimeError("source hit-array lengths differ")
                if contiguous:
                    lo = int(old_starts[0])
                    hi = int(old_starts[-1] + old_counts[-1])
                    packed = source[lo:hi]
                else:
                    packed = np.concatenate(
                        [source[int(start) : int(start + width)] for start, width in zip(old_starts, old_counts)]
                    )
                if len(packed) != total_new_hits:
                    raise RuntimeError("repacked hit count does not equal sum(hit_count)")
                self.hit_chunks[field].append(np.asarray(packed))
        elif total_new_hits != 0:
            raise RuntimeError("positive total hit count without hit-bearing events")

        for field in self.original_event_fields:
            if field not in arrays:
                raise RuntimeError(f"appended catalog block is missing event field: {field}")
            values = np.asarray(arrays[field])[selector]
            if len(values) != count:
                raise RuntimeError(f"event field length mismatch: {field}")
            self.event_chunks[field].append(new_starts if field == "hit_start" else values)
        self.event_category_chunks.append(np.full(count, category_id, dtype=np.uint16))
        self.event_chunks["event_base_weight_cps"].append(weights)
        self.event_chunks["event_component"].append(np.full(count, component, dtype=np.uint8))
        self.event_chunks["source_bin80"].append(bins80)
        self.event_chunks["continuum_importance_weight"].append(importance)

        start = self.event_count
        self.event_count += count
        self.hit_count += total_new_hits
        sumw = float(np.sum(weights, dtype=np.float64))
        sumw2 = float(np.sum(weights * weights, dtype=np.float64))
        aggregate = self.component_accumulator[component]
        aggregate["events"] += count
        aggregate["sumw_cps"] += sumw
        aggregate["sumw2_cps2"] += sumw2
        return start, count, {
            "events": count,
            "sumw_cps": sumw,
            "sumw2_cps2": sumw2,
            "effective_sample_size": effective_sample_size(sumw, sumw2),
            "minimum_event_weight_cps": float(np.min(weights)),
            "maximum_event_weight_cps": float(np.max(weights)),
        }

    def finalize(self) -> dict[str, np.ndarray]:
        output: dict[str, np.ndarray] = {}
        for field, chunks in self.event_chunks.items():
            if not chunks:
                raise RuntimeError(f"no chunks were assembled for event field: {field}")
            output[field] = np.concatenate(chunks)
        output["event_category"] = np.concatenate(self.event_category_chunks)
        for field, chunks in self.hit_chunks.items():
            if chunks:
                output[field] = np.concatenate(chunks)
            else:
                output[field] = np.empty(0, dtype=np.float32)
        event_lengths = {field: len(output[field]) for field in (*self.original_event_fields, *ADDED_EVENT_FIELDS, "event_category")}
        if set(event_lengths.values()) != {self.event_count}:
            raise RuntimeError(f"assembled event-array lengths differ: {event_lengths}")
        hit_lengths = {field: len(output[field]) for field in HIT_FIELDS}
        if set(hit_lengths.values()) != {self.hit_count}:
            raise RuntimeError(f"assembled hit-array lengths differ: {hit_lengths}")
        if int(np.sum(output["hit_count"], dtype=np.int64)) != self.hit_count:
            raise RuntimeError("assembled sum(hit_count) does not close to hit-array length")
        return output

    def component_stats(self) -> dict[str, dict[str, float | int]]:
        names = {
            COMPONENT_OTHER: "other",
            COMPONENT_GAMMA_CONTINUUM: "gamma_continuum",
            COMPONENT_ATM511: "atm511",
        }
        result: dict[str, dict[str, float | int]] = {}
        for component, values in self.component_accumulator.items():
            sumw = float(values["sumw_cps"])
            sumw2 = float(values["sumw2_cps2"])
            result[names[component]] = {
                "component_id": component,
                "events": int(values["events"]),
                "sumw_cps": sumw,
                "sumw2_cps2": sumw2,
                "effective_sample_size": effective_sample_size(sumw, sumw2),
            }
        return result


def load_npz(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {field: data[field] for field in data.files}


def validate_mature_catalog(
    catalog_dir: Path,
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]], list[str], dict[str, Any]]:
    catalog_path = catalog_dir / "combined_event_catalog.npz"
    registry_path = catalog_dir / "category_registry.json"
    summary_path = catalog_dir / "summary.json"
    arrays = load_npz(catalog_path)
    registry = load_json(registry_path)
    summary = load_json(summary_path)
    categories = [dict(row) for row in registry["categories"]]
    for field in (*REQUIRED_RESPONSE_FIELDS, "event_category", *HIT_FIELDS):
        if field not in arrays:
            raise RuntimeError(f"mature catalog {catalog_path} lacks {field}")
    n_events = len(arrays["event_category"])
    original_event_fields = [
        field for field in arrays if field not in HIT_FIELDS and len(arrays[field]) == n_events
    ]
    if "event_category" not in original_event_fields:
        raise RuntimeError("mature catalog event_category is not event-aligned")
    expected_start = 0
    for row in categories:
        category_id = int(row["category_id"])
        start = int(row["event_start"])
        count = int(row["event_count"])
        stop = start + count
        if category_id < 0 or start != expected_start or stop > n_events:
            raise RuntimeError(f"mature category registry is not contiguous at category {category_id}")
        if not np.all(arrays["event_category"][start:stop] == category_id):
            raise RuntimeError(f"mature event_category mismatch at category {category_id}")
        expected_start = stop
    if expected_start != n_events:
        raise RuntimeError("mature category registry does not span all events")
    return arrays, categories, original_event_fields, summary


def gamma_jobs_for_model(model: str) -> tuple[list[GammaJob], float, dict[str, Any]]:
    if model == "a":
        base_summary_path = A_BASE / "summary.json"
        base_summary = load_json(base_summary_path)
        base_rows = [
            row for row in base_summary["jobs"]
            if row.get("stream") == "prompt" and row.get("family") == "gamma"
        ]
        supplement_summary_path = A_SUPPLEMENT / "summary.json"
        supplement_summary = load_json(supplement_summary_path)
        supplement_rows = list(supplement_summary["supplemental_jobs"])
        if len(base_rows) != EXPECTED[model]["base_gamma_jobs"]:
            raise RuntimeError(f"model-A base prompt-gamma membership changed: {len(base_rows)}")
        if len(supplement_rows) != EXPECTED[model]["supplement_gamma_jobs"]:
            raise RuntimeError(f"model-A supplement prompt-gamma membership changed: {len(supplement_rows)}")
        jobs: list[GammaJob] = []
        for row in base_rows:
            cache = resolve_recorded_path(row["catalog_path"])
            jobs.append(GammaJob(
                authority_group="package62_base",
                batch_id=str(row["batch_id"]),
                job_id=str(row["job_id"]),
                scan_index=int(row["scan_index"]),
                seed=int(row["seed"]),
                events=int(row["events"]),
                detector_positive_events=int(row["detector_positive_events"]),
                sim_path=resolve_recorded_path(row["sim_path"]),
                sim_bytes=int(row["sim_bytes"]),
                catalog_path=cache,
                metadata_source=base_summary_path,
            ))
        for row in supplement_rows:
            match = re.fullmatch(r"m05new_sg3b_gamma_shard(\d{4})", str(row["job_id"]))
            if not match:
                raise RuntimeError(f"unexpected model-A supplemental job ID: {row['job_id']}")
            shard = int(match.group(1))
            scan_index = 1000 + shard
            meta_path = A_SUPPLEMENT / "job_catalogs" / f"job_{scan_index}_{row['job_id']}.json"
            meta = load_json(meta_path)
            checks = {
                "job_id": meta.get("job_id") == row.get("job_id"),
                "stream": meta.get("stream") == "prompt",
                "family": meta.get("family") == "gamma",
                "events": int(meta.get("events", -1)) == int(row["events"]),
                "seed": int(meta.get("seed", -1)) == int(row["sim_header_seed"]),
                "sim_path": str(meta.get("sim_path")) == str(row["sim"]),
            }
            failed = [name for name, passed in checks.items() if not passed]
            if failed:
                raise RuntimeError(f"model-A supplemental metadata mismatch {row['job_id']}: {failed}")
            jobs.append(GammaJob(
                authority_group="package63_gamma_supplement",
                batch_id=str(meta["batch_id"]),
                job_id=str(row["job_id"]),
                scan_index=scan_index,
                seed=int(row["sim_header_seed"]),
                events=int(row["events"]),
                detector_positive_events=int(meta["detector_positive_events"]),
                sim_path=resolve_recorded_path(row["sim"]),
                sim_bytes=int(meta["sim_bytes"]),
                catalog_path=resolve_recorded_path(meta["catalog_path"]),
                metadata_source=meta_path,
            ))
        expanded_categories = load_json(A_SUPPLEMENT / "category_registry.json")["categories"]
        gamma_row = prompt_gamma_category(expanded_categories)
        proposal_weight = float(gamma_row["base_event_weight_cps"])
        authority = {
            "base_summary": repo_display(base_summary_path),
            "supplement_summary": repo_display(supplement_summary_path),
            "proposal_category_registry": repo_display(A_SUPPLEMENT / "category_registry.json"),
            "proposal_detector_positive_events": int(gamma_row["event_count"]),
        }
    else:
        summary_path = B_MATURE / "summary.json"
        summary = load_json(summary_path)
        rows = [
            row for row in summary["jobs"]
            if row.get("stream") == "prompt" and row.get("family") == "gamma"
        ]
        jobs = [
            GammaJob(
                authority_group="b60_mature_summary",
                batch_id=str(row["batch_id"]),
                job_id=str(row["job_id"]),
                scan_index=int(row["scan_index"]),
                seed=int(row["seed"]),
                events=int(row["events"]),
                detector_positive_events=int(row["detector_positive_events"]),
                sim_path=resolve_recorded_path(row["sim_path"]),
                sim_bytes=int(row["sim_bytes"]),
                catalog_path=resolve_recorded_path(row["catalog_path"]),
                metadata_source=summary_path,
            )
            for row in rows
        ]
        categories = load_json(B_MATURE / "category_registry.json")["categories"]
        gamma_row = prompt_gamma_category(categories)
        proposal_weight = float(gamma_row["base_event_weight_cps"])
        authority = {
            "mature_summary": repo_display(summary_path),
            "proposal_category_registry": repo_display(B_MATURE / "category_registry.json"),
            "proposal_detector_positive_events": int(gamma_row["event_count"]),
        }

    jobs.sort(key=lambda job: (job.authority_group, job.batch_id, job.scan_index, job.job_id))
    if len(jobs) != EXPECTED[model]["gamma_jobs"]:
        raise RuntimeError(f"model-{model} prompt-gamma job membership changed: {len(jobs)}")
    identities = {
        (job.authority_group, job.batch_id, job.scan_index, str(job.sim_path))
        for job in jobs
    }
    if len(identities) != len(jobs):
        raise RuntimeError("duplicate prompt-gamma authority/batch/scan/SIM identity")
    if len({job.seed for job in jobs}) != len(jobs):
        raise RuntimeError("duplicate prompt-gamma SIM seeds")
    if len({str(job.sim_path) for job in jobs}) != len(jobs):
        raise RuntimeError("duplicate prompt-gamma raw SIM paths")
    detector_positive = sum(job.detector_positive_events for job in jobs)
    if detector_positive != EXPECTED[model]["gamma_detector_positive"]:
        raise RuntimeError(
            f"model-{model} prompt-gamma detector-positive membership changed: {detector_positive}"
        )
    if detector_positive != int(authority["proposal_detector_positive_events"]):
        raise RuntimeError("gamma summary membership does not close to mature proposal category")
    if not math.isfinite(proposal_weight) or proposal_weight <= 0.0:
        raise RuntimeError("invalid pooled prompt-gamma proposal event weight")
    for job in jobs:
        if not job.sim_path.is_file() or job.sim_path.stat().st_size != job.sim_bytes:
            raise RuntimeError(f"raw SIM missing/size mismatch: {job.job_id}")
        if not job.catalog_path.is_file():
            raise RuntimeError(f"gamma job cache missing: {job.job_id}: {job.catalog_path}")
    authority.update({
        "jobs": len(jobs),
        "detector_positive_events": detector_positive,
        "pooled_proposal_event_weight_cps": proposal_weight,
    })
    return jobs, proposal_weight, authority


def line_arrays_for_model(
    model: str, required_event_fields: Sequence[str]
) -> tuple[dict[str, np.ndarray], dict[str, Any], dict[str, Any]]:
    line_dir = LINE_DIRS[model]
    summary_path = line_dir / "summary.json"
    summary = load_json(summary_path)
    arrays = load_npz(line_dir / "mono_line_event_catalog.npz")
    count = int(summary["detector_positive_events"])
    if len(arrays["source_bin80"]) != count or len(arrays["base_event_weight_cps"]) != count:
        raise RuntimeError(f"model-{model} mono-line catalog count mismatch")
    bins = np.asarray(arrays["source_bin80"], dtype=np.uint8)
    if np.any(bins >= 80):
        raise RuntimeError(f"model-{model} mono-line source_bin80 outside 0..79")
    expected_weight = 1.0 / float(summary["physical_exposure_s"])
    weights = np.asarray(arrays["base_event_weight_cps"], dtype=np.float64)
    if np.any(weights != weights[0]) or not math.isclose(
        float(weights[0]), expected_weight, rel_tol=2e-15, abs_tol=0.0
    ):
        raise RuntimeError(f"model-{model} mono-line event weights are not 1/sum(T_E)")

    missing = [field for field in required_event_fields if field not in arrays and field != "event_category"]
    recovered_fields: list[str] = []
    if missing:
        if missing != ["compton_keep"] or model != "b":
            raise RuntimeError(f"mono-line catalog lacks required response fields: {missing}")
        event_job_index = np.asarray(arrays["event_job_index"], dtype=np.int64)
        event_id = np.asarray(arrays["event_id"], dtype=np.int64)
        recovered = np.empty(count, dtype=np.uint8)
        metas = [load_json(path) for path in sorted((line_dir / "job_catalogs").glob("*.json"))]
        by_index = {int(meta["scan_index"]): meta for meta in metas}
        expected_indices = sorted(set(int(value) for value in event_job_index))
        if sorted(by_index) != expected_indices:
            raise RuntimeError("mono-line job caches do not span event_job_index")
        for scan_index in expected_indices:
            positions = np.flatnonzero(event_job_index == scan_index)
            if len(positions) == 0 or not np.all(np.diff(positions) == 1):
                raise RuntimeError(f"mono-line events are not contiguous for job index {scan_index}")
            cache = resolve_recorded_path(by_index[scan_index]["catalog_path"])
            with np.load(cache, allow_pickle=False) as data:
                if "compton_keep" not in data.files:
                    raise RuntimeError(f"line job cache lacks compton_keep: {cache}")
                if not np.array_equal(event_id[positions], data["event_id"].astype(np.int64)):
                    raise RuntimeError(f"line merged/job event IDs differ at scan index {scan_index}")
                recovered[positions] = data["compton_keep"].astype(np.uint8)
        arrays["compton_keep"] = recovered
        recovered_fields.append("compton_keep")
    audit = {
        "summary": repo_display(summary_path),
        "catalog": repo_display(line_dir / "mono_line_event_catalog.npz"),
        "incident_photons": int(summary["incident_photons"]),
        "jobs": int(summary["jobs"]),
        "detector_positive_events": count,
        "physical_exposure_s": float(summary["physical_exposure_s"]),
        "event_weight_cps": expected_weight,
        "source_bin80_minimum": int(np.min(bins)),
        "source_bin80_maximum": int(np.max(bins)),
        "recovered_response_fields": recovered_fields,
    }
    return arrays, summary, audit


def category_with_stats(
    source: Mapping[str, Any], *, category_id: int, component: str,
    event_start: int, stats: Mapping[str, Any], weight_policy: str,
    proposal_weight: float | None = None,
) -> dict[str, Any]:
    row = dict(source)
    row.update({
        "category_id": category_id,
        "event_start": event_start,
        "event_count": int(stats["events"]),
        "component": component,
        "weight_policy": weight_policy,
        "sum_event_base_weight_cps": float(stats["sumw_cps"]),
        "sum_event_base_weight2_cps2": float(stats["sumw2_cps2"]),
        "effective_sample_size": float(stats["effective_sample_size"]),
        "base_detector_positive_rate_cps": float(stats["sumw_cps"]),
    })
    if weight_policy == "per_event_catalog_array":
        row["base_event_weight_cps"] = None
    elif "base_event_weight_cps" not in row:
        row["base_event_weight_cps"] = float(stats["sumw_cps"]) / int(stats["events"])
    if proposal_weight is not None:
        row["proposal_event_weight_cps"] = proposal_weight
    return row


def save_catalog(path: Path, arrays: Mapping[str, np.ndarray]) -> None:
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(handle, **arrays)
    os.replace(temporary, path)


def build_model(model: str, output: Path, init_cache_root: Path) -> dict[str, Any]:
    mature_dir = A_BASE if model == "a" else B_MATURE
    mature_arrays, mature_categories, original_event_fields, mature_summary = validate_mature_catalog(mature_dir)
    old_gamma = prompt_gamma_category(mature_categories)
    assembler = CatalogAssembler(original_event_fields)
    categories: list[dict[str, Any]] = []

    # Preserve every mature category except prompt broadband gamma.  Delayed
    # gamma is intentionally retained: it is activation response, not the
    # atmospheric prompt component being decomposed.
    retained_events = 0
    for old_row in mature_categories:
        if old_row.get("stream") == "prompt" and old_row.get("family") == "gamma":
            continue
        old_start = int(old_row["event_start"])
        old_count = int(old_row["event_count"])
        new_id = len(categories)
        start, count, stats = assembler.append(
            mature_arrays,
            category_id=new_id,
            component=COMPONENT_OTHER,
            base_weights=float(old_row["base_event_weight_cps"]),
            continuum_importance=1.0,
            source_bin80=int(SOURCE_BIN80_NOT_APPLICABLE),
            event_slice=slice(old_start, old_start + old_count),
        )
        categories.append(category_with_stats(
            {**old_row, "original_category_id": int(old_row["category_id"])},
            category_id=new_id,
            component="other",
            event_start=start,
            stats=stats,
            weight_policy="constant_category_weight",
        ))
        retained_events += count

    source_closure = SourceClosure()
    mono_target_audit = validate_mono_target()
    gamma_jobs, proposal_weight, gamma_authority = gamma_jobs_for_model(model)
    gamma_category_id = len(categories)
    gamma_start = assembler.event_count
    gamma_count = 0
    gamma_sumw = 0.0
    gamma_sumw2 = 0.0
    gamma_min_weight = math.inf
    gamma_max_weight = -math.inf
    gamma_importance_min = math.inf
    gamma_importance_max = -math.inf
    gamma_job_rows: list[dict[str, Any]] = []
    boundary_rows: list[dict[str, Any]] = []
    bin_count = np.zeros(20, dtype=np.int64)
    bin_boundaries = np.zeros(20, dtype=np.int64)
    bin_sumw = np.zeros(20, dtype=np.float64)
    bin_sumw2 = np.zeros(20, dtype=np.float64)
    bin_importance_min = np.full(20, np.inf, dtype=np.float64)
    bin_importance_max = np.full(20, -np.inf, dtype=np.float64)
    bin_energy_min = np.full(20, np.inf, dtype=np.float64)
    bin_energy_max = np.full(20, -np.inf, dtype=np.float64)

    for ordinal, job in enumerate(gamma_jobs, 1):
        arrays = load_npz(job.catalog_path)
        for field in (*REQUIRED_RESPONSE_FIELDS, *HIT_FIELDS, "event_id"):
            if field not in arrays:
                raise RuntimeError(f"gamma cache {job.job_id} lacks {field}")
        count = len(arrays["event_id"])
        if count != job.detector_positive_events:
            raise RuntimeError(
                f"gamma cache/summary detector-positive mismatch {job.job_id}: "
                f"{count} vs {job.detector_positive_events}"
            )
        energy, dir_z, match_audit = recover_gamma_init_cached(
            init_cache_root, job, arrays["event_id"]
        )
        bins20 = source_bin20_from_dir_z(dir_z)
        importance = source_closure.importance(bins20, energy)
        weights = proposal_weight * importance
        boundary_mask, nearest_boundary, boundary_delta = boundary_candidates(dir_z)
        boundary_indices = np.flatnonzero(boundary_mask)
        for index in boundary_indices:
            boundary_rows.append({
                "model": model,
                "authority_group": job.authority_group,
                "batch_id": job.batch_id,
                "job_id": job.job_id,
                "event_id": int(arrays["event_id"][index]),
                "energy_keV": float(energy[index]),
                "dir_z": float(dir_z[index]),
                "nearest_internal_boundary_dir_z": float(nearest_boundary[index]),
                "delta_dir_z": float(boundary_delta[index]),
                "assigned_source_bin20": int(bins20[index]),
                "continuum_importance_weight": float(importance[index]),
            })
        for bin_id in range(20):
            mask = bins20 == bin_id
            if not np.any(mask):
                continue
            selected_weights = weights[mask]
            selected_importance = importance[mask]
            selected_energy = energy[mask]
            bin_count[bin_id] += int(np.count_nonzero(mask))
            bin_boundaries[bin_id] += int(np.count_nonzero(boundary_mask & mask))
            bin_sumw[bin_id] += float(np.sum(selected_weights, dtype=np.float64))
            bin_sumw2[bin_id] += float(np.sum(selected_weights * selected_weights, dtype=np.float64))
            bin_importance_min[bin_id] = min(bin_importance_min[bin_id], float(np.min(selected_importance)))
            bin_importance_max[bin_id] = max(bin_importance_max[bin_id], float(np.max(selected_importance)))
            bin_energy_min[bin_id] = min(bin_energy_min[bin_id], float(np.min(selected_energy)))
            bin_energy_max[bin_id] = max(bin_energy_max[bin_id], float(np.max(selected_energy)))

        _, appended, stats = assembler.append(
            arrays,
            category_id=gamma_category_id,
            component=COMPONENT_GAMMA_CONTINUUM,
            base_weights=weights,
            continuum_importance=importance,
            source_bin80=int(SOURCE_BIN80_NOT_APPLICABLE),
        )
        gamma_count += appended
        gamma_sumw += float(stats["sumw_cps"])
        gamma_sumw2 += float(stats["sumw2_cps2"])
        gamma_min_weight = min(gamma_min_weight, float(stats["minimum_event_weight_cps"]))
        gamma_max_weight = max(gamma_max_weight, float(stats["maximum_event_weight_cps"]))
        gamma_importance_min = min(gamma_importance_min, float(np.min(importance)))
        gamma_importance_max = max(gamma_importance_max, float(np.max(importance)))
        gamma_job_rows.append({
            "model": model,
            "authority_group": job.authority_group,
            "batch_id": job.batch_id,
            "job_id": job.job_id,
            "scan_index": job.scan_index,
            "seed": job.seed,
            "incident_events": job.events,
            "detector_positive_events": appended,
            "matched_ia_init_events": match_audit["matched_ia_init_events"],
            "matching_rate": match_audit["matching_rate"],
            "boundary_candidates": int(len(boundary_indices)),
            "proposal_event_weight_cps": proposal_weight,
            "minimum_continuum_importance_weight": float(np.min(importance)),
            "maximum_continuum_importance_weight": float(np.max(importance)),
            "sumw_cps": stats["sumw_cps"],
            "sumw2_cps2": stats["sumw2_cps2"],
            "effective_sample_size": stats["effective_sample_size"],
            "raw_sim": repo_display(job.sim_path),
            "job_cache": repo_display(job.catalog_path),
            "metadata_source": repo_display(job.metadata_source),
            "init_cache_status": match_audit["init_cache_status"],
            "init_cache": match_audit["init_cache"],
            "init_cache_receipt": match_audit["init_cache_receipt"],
        })
        print(json.dumps({
            "model": model,
            "gamma_job": job.job_id,
            "complete": ordinal,
            "total": len(gamma_jobs),
            "detector_positive": appended,
            "matched": match_audit["matched_ia_init_events"],
            "boundary_candidates": int(len(boundary_indices)),
        }), flush=True)

    if gamma_count != EXPECTED[model]["gamma_detector_positive"]:
        raise RuntimeError(f"assembled model-{model} gamma count changed: {gamma_count}")
    gamma_stats = {
        "events": gamma_count,
        "sumw_cps": gamma_sumw,
        "sumw2_cps2": gamma_sumw2,
        "effective_sample_size": effective_sample_size(gamma_sumw, gamma_sumw2),
        "minimum_event_weight_cps": gamma_min_weight,
        "maximum_event_weight_cps": gamma_max_weight,
    }
    categories.append(category_with_stats(
        {
            "stream": "prompt",
            "family": "gamma",
            "source_parent_ZA": -1,
            "replaces_original_category_id": int(old_gamma["category_id"]),
        },
        category_id=gamma_category_id,
        component="gamma_continuum",
        event_start=gamma_start,
        stats=gamma_stats,
        weight_policy="per_event_catalog_array",
        proposal_weight=proposal_weight,
    ))

    line_arrays, line_summary, line_audit = line_arrays_for_model(model, original_event_fields)
    line_category_id = len(categories)
    line_start, _, line_stats = assembler.append(
        line_arrays,
        category_id=line_category_id,
        component=COMPONENT_ATM511,
        base_weights=np.asarray(line_arrays["base_event_weight_cps"], dtype=np.float64),
        continuum_importance=1.0,
        source_bin80=np.asarray(line_arrays["source_bin80"], dtype=np.uint8),
    )
    categories.append(category_with_stats(
        {
            "stream": "prompt",
            "family": "atm511",
            "source_parent_ZA": -1,
            "mono511_target_81x80": repo_display(MONO_TARGET_81X80),
        },
        category_id=line_category_id,
        component="atm511",
        event_start=line_start,
        stats=line_stats,
        weight_policy="constant_transport_weight_with_bin80_timeline_importance",
        proposal_weight=float(line_summary["event_weight_cps"]),
    ))

    output_arrays = assembler.finalize()
    save_catalog(output / "combined_event_catalog.npz", output_arrays)
    write_json(output / "category_registry.json", {
        "schema_version": 2,
        "weight_authority": "combined_event_catalog.npz:event_base_weight_cps",
        "categories": categories,
    })
    component_registry = {
        "schema_version": 1,
        "event_component_dtype": "uint8",
        "source_bin80_not_applicable": int(SOURCE_BIN80_NOT_APPLICABLE),
        "components": [
            {
                "component_id": COMPONENT_OTHER,
                "component": "other",
                "time_scaling": "retained mature prompt-family or delayed-isotope policy",
            },
            {
                "component_id": COMPONENT_GAMMA_CONTINUUM,
                "component": "gamma_continuum",
                "time_scaling": "gamma_continuum_scale_to_reference from trajectory_component_scales_81nodes.csv",
                "reference_weight": "pooled prompt-gamma proposal weight times per-event Jcont/Jtotal",
            },
            {
                "component_id": COMPONENT_ATM511,
                "component": "atm511",
                "time_scaling": "source_bin80-specific importance_ratio from mono511_target_81x80.csv",
                "reference_weight": "1/sum(Cosima observation time over independent line shards)",
            },
        ],
    }
    write_json(output / "component_registry.json", component_registry)

    bin_rows = []
    for bin_id in range(20):
        count = int(bin_count[bin_id])
        if count <= 0:
            raise RuntimeError(f"no detector-positive prompt-gamma events in source bin {bin_id}")
        bin_rows.append({
            "model": model,
            "source_bin20": bin_id,
            "detector_positive_events": count,
            "boundary_candidates": int(bin_boundaries[bin_id]),
            "minimum_energy_keV": float(bin_energy_min[bin_id]),
            "maximum_energy_keV": float(bin_energy_max[bin_id]),
            "minimum_continuum_importance_weight": float(bin_importance_min[bin_id]),
            "maximum_continuum_importance_weight": float(bin_importance_max[bin_id]),
            "sumw_cps": float(bin_sumw[bin_id]),
            "sumw2_cps2": float(bin_sumw2[bin_id]),
            "effective_sample_size": effective_sample_size(float(bin_sumw[bin_id]), float(bin_sumw2[bin_id])),
        })
    write_csv(output / "gamma_job_audit.csv", gamma_job_rows, (
        "model", "authority_group", "batch_id", "job_id", "scan_index", "seed", "incident_events",
        "detector_positive_events", "matched_ia_init_events", "matching_rate",
        "boundary_candidates", "proposal_event_weight_cps",
        "minimum_continuum_importance_weight", "maximum_continuum_importance_weight",
        "sumw_cps", "sumw2_cps2", "effective_sample_size", "raw_sim", "job_cache",
        "metadata_source", "init_cache_status", "init_cache", "init_cache_receipt",
    ))
    write_csv(output / "gamma_importance_by_source_bin20.csv", bin_rows, (
        "model", "source_bin20", "detector_positive_events", "boundary_candidates",
        "minimum_energy_keV", "maximum_energy_keV", "minimum_continuum_importance_weight",
        "maximum_continuum_importance_weight", "sumw_cps", "sumw2_cps2",
        "effective_sample_size",
    ))
    write_csv(output / "gamma_boundary_candidates.csv", boundary_rows, (
        "model", "authority_group", "batch_id", "job_id", "event_id", "energy_keV", "dir_z",
        "nearest_internal_boundary_dir_z", "delta_dir_z", "assigned_source_bin20",
        "continuum_importance_weight",
    ))

    component_stats = assembler.component_stats()
    audit = {
        "status": "PASS__FLUXCLOSED_CATALOG_AUDIT",
        "model": model,
        "mature_input": repo_display(mature_dir),
        "mature_status": mature_summary.get("status"),
        "prompt_gamma_exclusion_policy": "exclude only stream=prompt,family=gamma; retain delayed gamma",
        "retained_other_events": retained_events,
        "excluded_mature_prompt_gamma_events": int(old_gamma["event_count"]),
        "gamma_authority": gamma_authority,
        "persistent_init_cache": repo_display(init_cache_root),
        "gamma_join": {
            "jobs": len(gamma_jobs),
            "detector_positive_events": gamma_count,
            "matched_ia_init_events": sum(int(row["matched_ia_init_events"]) for row in gamma_job_rows),
            "matching_rate": (
                sum(int(row["matched_ia_init_events"]) for row in gamma_job_rows) / gamma_count
            ),
            "boundary_dir_z_tolerance": BOUNDARY_DIR_Z_TOLERANCE,
            "boundary_candidates": len(boundary_rows),
            "minimum_continuum_importance_weight": gamma_importance_min,
            "maximum_continuum_importance_weight": gamma_importance_max,
            **gamma_stats,
        },
        "line": line_audit,
        "components": component_stats,
        "source_closure": {
            "manifest": repo_display(SOURCE_CLOSURE_JSON),
            "manifest_sha256": sha256_file(SOURCE_CLOSURE_JSON),
            "bins": repo_display(SOURCE_CLOSURE_BINS),
            "bins_sha256": sha256_file(SOURCE_CLOSURE_BINS),
            "basis": source_closure.basis,
            "grid_minimum_importance_weight": source_closure.grid_minimum,
            "mono_target": repo_display(MONO_TARGET_81X80),
            "mono_target_validation": mono_target_audit,
        },
        "output_schema": {
            "original_event_fields": original_event_fields,
            "original_hit_fields": list(HIT_FIELDS),
            "added_event_fields": list(ADDED_EVENT_FIELDS),
            "event_count": assembler.event_count,
            "hit_count": assembler.hit_count,
            "event_base_weight_dtype": str(output_arrays["event_base_weight_cps"].dtype),
            "event_component_dtype": str(output_arrays["event_component"].dtype),
            "source_bin80_dtype": str(output_arrays["source_bin80"].dtype),
        },
    }
    write_json(output / "audit.json", audit)
    summary = {
        "schema_version": 2,
        "status": "COMPLETE__POSITIVE_FLUXCLOSED_EVENT_CATALOG",
        "model": model,
        "events": assembler.event_count,
        "hits": assembler.hit_count,
        "categories": len(categories),
        "components": component_stats,
        "gamma_jobs": len(gamma_jobs),
        "gamma_detector_positive_events": gamma_count,
        "gamma_ia_init_matching_rate": audit["gamma_join"]["matching_rate"],
        "gamma_boundary_candidates": len(boundary_rows),
        "gamma_continuum_sumw_cps": gamma_sumw,
        "gamma_continuum_sumw2_cps2": gamma_sumw2,
        "gamma_continuum_effective_sample_size": gamma_stats["effective_sample_size"],
        "line_detector_positive_events": int(line_stats["events"]),
        "line_sumw_cps": float(line_stats["sumw_cps"]),
        "line_sumw2_cps2": float(line_stats["sumw2_cps2"]),
        "line_effective_sample_size": float(line_stats["effective_sample_size"]),
        "catalog": "combined_event_catalog.npz",
        "category_registry": "category_registry.json",
        "component_registry": "component_registry.json",
        "audit": "audit.json",
        "source_closure": repo_display(SOURCE_CLOSURE_JSON),
        "mono511_target_81x80": repo_display(MONO_TARGET_81X80),
    }
    write_json(output / "summary.json", summary)
    return summary


def preflight_model(model: str) -> dict[str, Any]:
    """Validate real authority membership and schemas without scanning SIMs."""

    mature_dir = A_BASE if model == "a" else B_MATURE
    mature_arrays, mature_categories, original_event_fields, mature_summary = validate_mature_catalog(
        mature_dir
    )
    old_gamma = prompt_gamma_category(mature_categories)
    source_closure = SourceClosure()
    mono_target = validate_mono_target()
    jobs, proposal_weight, gamma_authority = gamma_jobs_for_model(model)
    cache_events = 0
    for job in jobs:
        with np.load(job.catalog_path, allow_pickle=False) as data:
            required = {*REQUIRED_RESPONSE_FIELDS, *HIT_FIELDS, "event_id"}
            missing = sorted(required - set(data.files))
            if missing:
                raise RuntimeError(f"gamma cache schema mismatch {job.job_id}: {missing}")
            count = len(data["event_id"])
        if count != job.detector_positive_events:
            raise RuntimeError(
                f"gamma cache count mismatch {job.authority_group}/{job.batch_id}/"
                f"{job.scan_index}/{job.job_id}: {count} vs {job.detector_positive_events}"
            )
        cache_events += count
    line_arrays, _, line_audit = line_arrays_for_model(model, original_event_fields)
    if cache_events != EXPECTED[model]["gamma_detector_positive"]:
        raise RuntimeError("preflight gamma cache membership does not close")
    return {
        "status": "PASS__REAL_INPUT_PREFLIGHT__NO_RAW_SIM_SCAN",
        "model": model,
        "mature_input": repo_display(mature_dir),
        "mature_status": mature_summary.get("status"),
        "mature_events": len(mature_arrays["event_category"]),
        "mature_categories": len(mature_categories),
        "excluded_prompt_gamma_category_events": int(old_gamma["event_count"]),
        "original_event_fields": original_event_fields,
        "gamma_jobs": len(jobs),
        "gamma_unique_job_ids": len({job.job_id for job in jobs}),
        "gamma_detector_positive_events": cache_events,
        "gamma_pooled_proposal_event_weight_cps": proposal_weight,
        "gamma_authority": gamma_authority,
        "source_closure_status": source_closure.manifest["status"],
        "source_closure_minimum_importance_weight": source_closure.grid_minimum,
        "mono_target": mono_target,
        "line": line_audit,
        "line_catalog_events": len(line_arrays["source_bin80"]),
        "raw_sim_files_opened": 0,
        "raw_sim_hashes_computed": 0,
    }


def run_self_test() -> None:
    if source_bin20_from_dir_z(np.asarray([-1.0, -0.95, -0.9, -0.89999, 0.0, 0.99999, 1.0])).tolist() != [0, 0, 0, 1, 10, 19, 19]:
        raise RuntimeError("source_bin20 direction mapping self-test failed")
    mask, _, _ = boundary_candidates(np.asarray([-0.900004, -0.89998, 0.0, 0.12345]))
    if mask.tolist() != [True, False, True, False]:
        raise RuntimeError("boundary candidate self-test failed")
    arrays = {
        "plastic_keV": np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
        "bgo_keV": np.asarray([3.0, 4.0, 5.0], dtype=np.float32),
        "measured_total_keV": np.asarray([0.0, 511.0, 0.0], dtype=np.float32),
        "broad_flags": np.asarray([0, 1, 0], dtype=np.uint8),
        "w2_flags": np.asarray([0, 1, 0], dtype=np.uint8),
        "hit_start": np.asarray([0, 0, 2], dtype=np.int64),
        "hit_count": np.asarray([0, 2, 0], dtype=np.uint16),
        "hit_code": np.asarray([100001, 100002], dtype=np.int32),
        "hit_layer": np.asarray([1, 1], dtype=np.uint8),
        "hit_energy_keV": np.asarray([200.0, 311.0], dtype=np.float32),
        "hit_x_cm": np.asarray([0.0, 1.0], dtype=np.float32),
        "hit_y_cm": np.asarray([0.0, 1.0], dtype=np.float32),
        "hit_z_cm": np.asarray([0.0, 1.0], dtype=np.float32),
    }
    assembler = CatalogAssembler((*REQUIRED_RESPONSE_FIELDS, "event_category"))
    assembler.append(
        arrays,
        category_id=0,
        component=COMPONENT_GAMMA_CONTINUUM,
        base_weights=np.asarray([1.0, 0.5, 0.25]),
        continuum_importance=np.asarray([1.0, 0.5, 0.25]),
        source_bin80=int(SOURCE_BIN80_NOT_APPLICABLE),
    )
    output = assembler.finalize()
    if len(output["event_category"]) != 3 or len(output["hit_code"]) != 2:
        raise RuntimeError("catalog assembler self-test failed")
    if output["event_base_weight_cps"].dtype != np.float64:
        raise RuntimeError("event weight dtype self-test failed")
    print(json.dumps({"status": "PASS__STATIC_SELF_TEST"}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build model-A or model-B60 positive flux-closed event catalogs. "
            "This streams every prompt-gamma raw SIM and can take substantial time."
        )
    )
    parser.add_argument("--model", choices=("a", "b"), help="catalog model to build (b means current 60-cm model B)")
    parser.add_argument(
        "--output",
        type=Path,
        help="new output directory inside this package (default: outputs/02_fluxclosed_catalog_<model>)",
    )
    parser.add_argument(
        "--init-cache",
        type=Path,
        help=(
            "persistent per-job recovered-INIT cache inside this package "
            "(default: outputs/02_fluxclosed_init_cache_<model>)"
        ),
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="validate real manifests/catalog schemas without opening raw SIM streams",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run only synthetic parser/assembler checks; do not inspect or scan production inputs",
    )
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
        return 0
    if args.model is None:
        parser.error("--model is required unless --self-test is used")
    if args.preflight:
        print(json.dumps(preflight_model(args.model), indent=2, sort_keys=True))
        return 0
    output = args.output
    if output is None:
        output = DEFAULT_OUTPUTS[args.model]
    elif not output.is_absolute():
        output = PACKAGE / output
    output = output.resolve()
    if not output.is_relative_to(PACKAGE.resolve()):
        parser.error(f"output must remain inside {PACKAGE}")
    init_cache_root = args.init_cache
    if init_cache_root is None:
        init_cache_root = DEFAULT_INIT_CACHES[args.model]
    elif not init_cache_root.is_absolute():
        init_cache_root = PACKAGE / init_cache_root
    init_cache_root = init_cache_root.resolve()
    if not init_cache_root.is_relative_to(PACKAGE.resolve()):
        parser.error(f"INIT cache must remain inside {PACKAGE}")
    if output.exists():
        raise RuntimeError(f"refusing to overwrite existing output directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        summary = build_model(args.model, stage, init_cache_root)
        if output.exists():
            raise RuntimeError(f"destination appeared during build: {output}")
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print(json.dumps({**summary, "output": str(output)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
