#!/usr/bin/env python3
"""Streaming prompt-gamma TES/veto analysis for a pinned corrected-keV authority.

The canonical run consumes merge-eligible batch0000 and batch0001 plus exactly
one mutually exclusive batch0003 authority profile: the full stage-5M ledger,
or the committed-pair ordinal-76 prefix ledger.  It reads every referenced
gamma SIM to gzip EOF, checks the ledger-bound compressed-file SHA-256 while
parsing, and never pools the two geometries.

The detector response is a fixed, reproducible response realization.  Gaussian
noise is keyed by immutable event identity and TES pixel UID, so changing file
order, shard order, or streaming chunk size cannot change a measured event.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
import shutil
import sys
import tempfile
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, TextIO


def find_root(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise RuntimeError("repository root not found")


THIS_FILE = Path(__file__).resolve()
ROOT = find_root(THIS_FILE.parent)
ANALYSIS_DIR = THIS_FILE.parents[1]
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811"
DEFAULT_BATCH0000_LEDGER = RUN_ROOT / "mergeable_smoke_v1_ledger.json"
DEFAULT_BATCH0001_LEDGER = RUN_ROOT / "seven_family_batch0001_v1_ledger.json"
DEFAULT_STAGE5_LEDGER = RUN_ROOT / "gamma_instant_batch0003_stage5m_v1_ledger.json"
DEFAULT_STAGE5_VALIDATION = RUN_ROOT / "gamma_instant_batch0003_stage5m_v1_validation.json"
PREFIX_AUTHORITY_ROOT = RUN_ROOT / "gamma_instant_batch0003_prefix_checkpoints_20260811"
DEFAULT_PREFIX76_LEDGER = PREFIX_AUTHORITY_ROOT / "gamma_instant_batch0003_prefix_shard0076_v1_ledger.json"
DEFAULT_PREFIX76_VALIDATION = (
    PREFIX_AUTHORITY_ROOT / "gamma_instant_batch0003_prefix_shard0076_v1_validation.json"
)
CANONICAL_AUTHORITY_PIN = ANALYSIS_DIR / "data/canonical_gamma_authority.json"

# batch0000 and batch0001 are immutable retained authorities.  The selectable
# batch0003 authority files did not exist when this analyzer was frozen, so one
# profile's two digests are bound by the fixed-path, write-once pin after
# publication.  A single pin cannot authorize both profiles.
CANONICAL_BATCH0000_LEDGER_SHA256 = "036335b186bb1e8d9dbec53e0e8994dd8cb1fc055b930469b8d7d144f60b263f"
CANONICAL_BATCH0001_LEDGER_SHA256 = "bb89c618d519a6a8570c8c746012c9ad0e81cb427b2a23145084a429c34c5df4"

SOURCE_CONTRACT_SHA256 = "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326"
GEOMETRIES = ("mass_model_511", "s3d_o8")
GEOMETRY_LABELS = {"mass_model_511": "Mass_model_511", "s3d_o8": "S3d-O8"}
@dataclass(frozen=True)
class AuthorityProfile:
    key: str
    ledger: Path
    validation: Path
    ledger_status: str
    validation_status: str
    prior_events_per_geometry: int
    cumulative_events_per_geometry: int
    new_events_per_geometry: int
    expected_prior_shards: tuple[int, int]
    expected_new_shards: int
    prefix_end_ordinal: int | None
    full_checkpoint_authority: bool
    output_stem: str
    display_title: str
    pass_status: str


STAGE5_PROFILE = AuthorityProfile(
    key="stage5",
    ledger=DEFAULT_STAGE5_LEDGER,
    validation=DEFAULT_STAGE5_VALIDATION,
    ledger_status="PASS__BATCH0003_STAGE5M_MERGE_ELIGIBLE",
    validation_status="PASS",
    prior_events_per_geometry=101_000,
    cumulative_events_per_geometry=5_000_000,
    new_events_per_geometry=4_899_000,
    expected_prior_shards=(1, 4),
    expected_new_shards=196,
    prefix_end_ordinal=196,
    full_checkpoint_authority=True,
    output_stem="gamma_stage5m",
    display_title="Corrected-keV prompt gamma 5M checkpoint",
    pass_status="PASS__CORRECTED_KEV_GAMMA_STAGE5M_PROMPT_TES_POSTPROCESS",
)
PREFIX76_PROFILE = AuthorityProfile(
    key="prefix76",
    ledger=DEFAULT_PREFIX76_LEDGER,
    validation=DEFAULT_PREFIX76_VALIDATION,
    ledger_status="PARTIAL_PREFIX_MERGE_ELIGIBLE",
    validation_status="PASS__PARTIAL_PREFIX_VALIDATED",
    prior_events_per_geometry=101_000,
    cumulative_events_per_geometry=2_001_000,
    new_events_per_geometry=1_900_000,
    expected_prior_shards=(1, 4),
    expected_new_shards=76,
    prefix_end_ordinal=76,
    full_checkpoint_authority=False,
    output_stem="gamma_prefix76_2p001m_diagnostic",
    display_title="Corrected-keV prompt gamma 2.001M prefix diagnostic (ordinal 76; non-full)",
    pass_status="PASS__CORRECTED_KEV_GAMMA_PREFIX76_2P001M_PROMPT_TES_DIAGNOSTIC_NONFULL",
)
AUTHORITY_PROFILES = {profile.key: profile for profile in (STAGE5_PROFILE, PREFIX76_PROFILE)}

TES_RE = re.compile(r"^TP_L(?P<layer>[0-5])_(?P<pixel>\d+)$", re.IGNORECASE)
EDEP_RE = re.compile(r"(?:^|\s)edep_keV=([-+0-9.eE]+)(?:\s|$)")
GEOMETRY_RE = re.compile(r"^Geometry\s+(.+?)\s*$")
SEED_RE = re.compile(r"^Seed\s+(\d+)\s*$")

FWHM_KEV = 0.420
SIGMA_KEV = FWHM_KEV / 2.3548200450309493
PIXEL_THRESHOLD_KEV = 0.3
RESPONSE_NAMESPACE = "TES511_CORRECTED_GAMMA_PROMPT_KEYED_PIXEL_RESPONSE_V2"
W2_KEV = (510.58, 511.42)
BROAD_KEV = (480.0, 550.0)
VETO_THRESHOLDS_KEV = (50, 70, 80)
O8_PLASTIC_THRESHOLD_KEV = 50.0

# These are detector SensitiveVolume names, not fuzzy material tokens.  The
# separate active Kapton volumes are deliberately absent.
MASS_TRUE_CSI_VOLUMES = frozenset(
    {
        "CsI_Side_Segment_00",
        "CsI_Side_Segment_01",
        "CsI_Side_Segment_02",
        "CsI_Side_Segment_03_below_side_port",
        "CsI_Side_Segment_03_above_side_port",
        "CsI_Side_Segment_03_rectcut_window_band",
        "CsI_Side_Segment_04_below_side_port",
        "CsI_Side_Segment_04_above_side_port",
        "CsI_Side_Segment_04_rectcut_window_band",
        "CsI_Side_Segment_05",
        "CsI_Side_Segment_06",
        "CsI_Side_Segment_07",
        "CsI_Bottom_Quadrant_00",
        "CsI_Bottom_Quadrant_01",
        "CsI_Bottom_Quadrant_02",
        "CsI_Bottom_Quadrant_03",
        "CsI_TopAnnulus_Segment_00",
        "CsI_TopAnnulus_Segment_01",
        "CsI_TopAnnulus_Segment_02",
        "CsI_TopAnnulus_Segment_03",
        "CsI_TopAnnulus_Segment_04",
        "CsI_TopAnnulus_Segment_05",
        "CsI_TopAnnulus_Segment_06",
        "CsI_TopAnnulus_Segment_07",
    }
)
O8_TRUE_BGO_VOLUMES = frozenset(
    {
        "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
        "BGO_S3D_O8_FullWrap_BottomCap_30mm",
        "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
    }
)
O8_TRUE_PLASTIC_VOLUMES = frozenset(
    {
        "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
        "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
    }
)
MASS_DETECTOR_MAP = (
    ROOT
    / "outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"
)
O8_DETECTOR_MAP = (
    ROOT
    / "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"
)
MASS_GEOMETRY_SETUP = (
    ROOT
    / "outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
O8_GEOMETRY_SETUP = (
    ROOT
    / "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
GEOMETRY_CONTRACTS = {
    "mass_model_511": {
        "geometry_setup": MASS_GEOMETRY_SETUP,
        "geometry_setup_sha256": "f6ee8c36f45b6a66efa5544daf58a3431c6833289e5658eb8b4452f6792205b0",
        "detector_map": MASS_DETECTOR_MAP,
        "detector_map_sha256": "bdb084ed7ea776f04c6dee82d03ca1a2f9166dca5c575ea0b04f21c01dd0a06a",
    },
    "s3d_o8": {
        "geometry_setup": O8_GEOMETRY_SETUP,
        "geometry_setup_sha256": "86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec",
        "detector_map": O8_DETECTOR_MAP,
        "detector_map_sha256": "dd2c1d68cd474f8b0c7489f2cbbfc924eb69beb14d3ce360d9437c319a33d6cb",
    },
}

THETA_EDGES = (
    0.000,
    25.842,
    36.870,
    45.573,
    53.130,
    60.000,
    66.422,
    72.542,
    78.463,
    84.261,
    90.000,
    95.739,
    101.537,
    107.458,
    113.578,
    120.000,
    126.870,
    134.427,
    143.130,
    154.158,
    180.000,
)
ENERGY_EDGES = (0, 100, 300, 480, 550, 1000, 3000, 10000, 30000, 100000, 300000, math.inf)
ENERGY_LABELS = (
    "<100 keV",
    "100-300 keV",
    "300-480 keV",
    "480-550 keV",
    "0.55-1 MeV",
    "1-3 MeV",
    "3-10 MeV",
    "10-30 MeV",
    "30-100 MeV",
    "100-300 MeV",
    ">=300 MeV",
)


def _log_edges(low: float, high: float, steps_per_decade: int) -> tuple[float, ...]:
    start = math.log10(low)
    stop = math.log10(high)
    count = int(math.ceil((stop - start) * steps_per_decade))
    values = [10.0 ** (start + index / steps_per_decade) for index in range(count)]
    values.append(high)
    return tuple(values)


FULL_LOG_EDGES = _log_edges(0.3, 1.0e8, 10)
LINE_EDGES = tuple(480.0 + index for index in range(71))
W2_ZOOM_EDGES = tuple(508.0 + 0.1 * index for index in range(61))
HISTOGRAM_VIEWS = {
    "full_log": (FULL_LOG_EDGES, "log10_keV"),
    "line_480_550": (LINE_EDGES, "keV"),
    "w2_zoom_508_514": (W2_ZOOM_EDGES, "keV"),
}
SELECTIONS = ("pre_veto", "veto50", "veto70", "veto80")
WINDOWS = ("tes_positive", "broad_480_550", "w2_510p58_511p42")


def profile_output_name(profile: AuthorityProfile, suffix: str) -> str:
    return f"{profile.output_stem}_{suffix}"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(
        path,
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
    )


def atomic_csv(path: Path, rows: list[dict[str, Any]], fieldnames: Iterable[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    names = list(fieldnames or (list(rows[0]) if rows else []))
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON token {value}")),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(f"cannot read JSON {rel(path)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root is not an object: {rel(path)}")
    return payload


def validate_detector_map_contracts(
    geometry_contracts: dict[str, dict[str, Any]] = GEOMETRY_CONTRACTS,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    observed: dict[str, set[str]] = {}
    for geometry in GEOMETRIES:
        contract = geometry_contracts[geometry]
        setup = Path(contract["geometry_setup"]).resolve()
        path = Path(contract["detector_map"]).resolve()
        if not setup.is_file() or sha256(setup) != contract["geometry_setup_sha256"]:
            raise RuntimeError(f"{geometry}: fixed geometry setup is missing or hash-drifted: {rel(setup)}")
        if not path.is_file():
            raise RuntimeError(f"detector map missing: {rel(path)}")
        if sha256(path) != contract["detector_map_sha256"]:
            raise RuntimeError(f"{geometry}: fixed detector map hash drift: {rel(path)}")
        values: set[str] = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            if ".SensitiveVolume " in line:
                values.add(line.split(".SensitiveVolume ", 1)[1].strip())
        observed[geometry] = values
        records.append(
            {
                "geometry": geometry,
                "geometry_setup": rel(setup),
                "geometry_setup_sha256": sha256(setup),
                "detector_map": rel(path),
                "detector_map_sha256": sha256(path),
            }
        )
    mass_csi = {value for value in observed["mass_model_511"] if value.startswith("CsI_")}
    if mass_csi != set(MASS_TRUE_CSI_VOLUMES):
        raise RuntimeError("Mass detector-map CsI whitelist differs from the frozen 24-volume contract")
    o8_bgo = {value for value in observed["s3d_o8"] if value in O8_TRUE_BGO_VOLUMES}
    o8_plastic = {value for value in observed["s3d_o8"] if value in O8_TRUE_PLASTIC_VOLUMES}
    if o8_bgo != set(O8_TRUE_BGO_VOLUMES) or o8_plastic != set(O8_TRUE_PLASTIC_VOLUMES):
        raise RuntimeError("O8 detector-map BGO/plastic whitelist differs from the frozen contract")
    if any("KAPTON" in value.upper() for value in MASS_TRUE_CSI_VOLUMES | O8_TRUE_BGO_VOLUMES | O8_TRUE_PLASTIC_VOLUMES):
        raise RuntimeError("Kapton entered a true-active-veto whitelist")
    return records


def _validate_geometry_file_bindings(geometry_contracts: dict[str, dict[str, Any]]) -> None:
    if set(geometry_contracts) != set(GEOMETRIES):
        raise RuntimeError("geometry contract keys differ from the two frozen aggregation domains")
    for geometry in GEOMETRIES:
        contract = geometry_contracts[geometry]
        for kind, path_key, hash_key in (
            ("geometry setup", "geometry_setup", "geometry_setup_sha256"),
            ("detector map", "detector_map", "detector_map_sha256"),
        ):
            path = Path(contract[path_key]).resolve()
            expected = str(contract[hash_key])
            if not path.is_file() or sha256(path) != expected:
                raise RuntimeError(f"{geometry}: fixed {kind} path/hash binding failed: {rel(path)}")


def _parse_unique_source_geometry(path: Path) -> Path:
    matches = [match.group(1) for line in path.read_text(encoding="utf-8").splitlines() if (match := GEOMETRY_RE.match(line.strip()))]
    if len(matches) != 1:
        raise RuntimeError(f"{rel(path)}: expected exactly one Geometry directive, got {len(matches)}")
    return resolve_path(matches[0]).resolve()


def _parse_unique_dat_tt(path: Path) -> float:
    values: list[float] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        fields = raw.strip().split()
        if fields and fields[0] == "TT":
            if len(fields) != 2:
                raise RuntimeError(f"{rel(path)}: malformed TT record")
            try:
                values.append(float(fields[1]))
            except ValueError as exc:
                raise RuntimeError(f"{rel(path)}: non-numeric TT record") from exc
    if len(values) != 1 or not math.isfinite(values[0]) or values[0] <= 0.0:
        raise RuntimeError(f"{rel(path)}: expected exactly one positive finite TT, got {values!r}")
    return values[0]


LOG_TT_RE = re.compile(r"^Observation time:\s*([-+0-9.eE]+)\s+sec\s*$")


def _parse_unique_log_tt(path: Path) -> float:
    values: list[float] = []
    for raw in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if match := LOG_TT_RE.match(raw.strip()):
            try:
                values.append(float(match.group(1)))
            except ValueError as exc:
                raise RuntimeError(f"{rel(path)}: non-numeric observation time") from exc
    if len(values) != 1 or not math.isfinite(values[0]) or values[0] <= 0.0:
        raise RuntimeError(
            f"{rel(path)}: expected exactly one positive finite Observation time, got {values!r}"
        )
    return values[0]


def keyed_standard_normal(*parts: object) -> float:
    encoded = canonical_json_bytes([RESPONSE_NAMESPACE, *parts])
    digest = hashlib.sha256(encoded).digest()
    denominator = float(1 << 64)
    u1 = (int.from_bytes(digest[:8], "big") + 0.5) / denominator
    u2 = (int.from_bytes(digest[8:16], "big") + 0.5) / denominator
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if total <= 0:
        return None, None
    probability = successes / total
    denominator = 1.0 + z * z / total
    center = (probability + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt(
        probability * (1.0 - probability) / total + z * z / (4.0 * total * total)
    ) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def garwood_interval(count: int, alpha: float = 0.05) -> tuple[float, float]:
    if count < 0:
        raise ValueError("Poisson count cannot be negative")
    try:
        from scipy.stats import chi2
    except ImportError as exc:
        raise RuntimeError("scipy is required for exact Garwood Poisson intervals") from exc
    low = 0.0 if count == 0 else 0.5 * float(chi2.ppf(alpha / 2.0, 2 * count))
    high = 0.5 * float(chi2.ppf(1.0 - alpha / 2.0, 2 * (count + 1)))
    return low, high


def bin_index(value: float, edges: tuple[float, ...]) -> int:
    index = bisect.bisect_right(edges, value) - 1
    return max(0, min(len(edges) - 2, index))


def window_flags(measured_keV: float) -> dict[str, bool]:
    return {
        "tes_positive": measured_keV > 0.0,
        "broad_480_550": BROAD_KEV[0] <= measured_keV < BROAD_KEV[1],
        "w2_510p58_511p42": W2_KEV[0] <= measured_keV < W2_KEV[1],
    }


def pair_category(has_pair: bool, has_annihilation: bool) -> str:
    if has_pair and has_annihilation:
        return "pair_and_annihilation"
    if has_pair:
        return "pair_only"
    if has_annihilation:
        return "annihilation_only"
    return "neither"


@dataclass(frozen=True)
class JobInput:
    geometry: str
    batch_id: str
    ledger: Path
    ledger_sha256: str
    job_name: str
    events: int
    seed: int
    ordinal: int | None
    sum_tt_s: float
    sim: Path
    sim_sha256: str
    expected_geometry_setup: Path
    ledger_geometry_header: Path
    source_geometry: Path
    job_source: Path
    job_source_sha256: str
    isotope_dat: Path
    isotope_dat_sha256: str
    log: Path
    log_sha256: str

    @property
    def event_key_prefix(self) -> tuple[object, ...]:
        return (self.geometry, self.batch_id, self.seed, self.job_name)


def _campaign(ledger: dict[str, Any], geometry: str, *, stage: bool) -> dict[str, Any]:
    rows = [
        row
        for row in ledger.get("campaigns", [])
        if row.get("geometry") == geometry
        and row.get("mode") == "instant"
        and (not stage or row.get("family") == "gamma")
    ]
    if len(rows) != 1:
        raise RuntimeError(f"{ledger.get('batch_id')}/{geometry}: expected one instant gamma campaign, got {len(rows)}")
    return rows[0]


def _gamma_jobs(
    ledger: dict[str, Any],
    geometry: str,
    ledger_path: Path,
    ledger_digest: str,
    geometry_contracts: dict[str, dict[str, Any]],
) -> list[JobInput]:
    stage = ledger.get("batch_id") == "corrected_original_gamma_instant_batch0003"
    campaign = _campaign(ledger, geometry, stage=stage)
    raw_jobs = [row for row in campaign.get("jobs", []) if row.get("family") == "gamma"]
    jobs: list[JobInput] = []
    expected_geometry = Path(geometry_contracts[geometry]["geometry_setup"]).resolve()
    expected_geometry_hash = str(geometry_contracts[geometry]["geometry_setup_sha256"])
    if campaign.get("geometry_setup") is not None:
        if resolve_path(str(campaign["geometry_setup"])).resolve() != expected_geometry:
            raise RuntimeError(f"{ledger.get('batch_id')}/{geometry}: campaign Geometry path mismatch")
        if campaign.get("geometry_setup_sha256") != expected_geometry_hash:
            raise RuntimeError(f"{ledger.get('batch_id')}/{geometry}: campaign Geometry hash mismatch")
    for row in raw_jobs:
        job_identity = f"{ledger.get('batch_id')}/{geometry}/{row.get('job_name')}"
        ledger_tt_dat = float(row.get("TT_s_from_isotope_dat", 0.0))
        ledger_tt_log = float(row.get("TT_s_from_log", 0.0))
        if not (
            math.isfinite(ledger_tt_dat)
            and ledger_tt_dat > 0.0
            and math.isclose(ledger_tt_dat, ledger_tt_log, rel_tol=0.0, abs_tol=1e-12)
        ):
            raise RuntimeError(f"{job_identity}: invalid or mismatched ledger TT")
        ia = row.get("ia_init", {})
        if not ia.get("geometry_header"):
            raise RuntimeError(f"{job_identity}: missing ledger Geometry")
        ledger_geometry = resolve_path(str(ia["geometry_header"])).resolve()
        if ledger_geometry != expected_geometry:
            raise RuntimeError(f"{job_identity}: ledger Geometry differs from fixed geometry key")
        job_source = resolve_path(str(row["job_source"])).resolve()
        isotope_dat = resolve_path(str(row["isotope_dat"])).resolve()
        log = resolve_path(str(row["log"])).resolve()
        for kind, path, expected_hash in (
            ("job_source", job_source, str(row["job_source_sha256"])),
            ("isotope_dat", isotope_dat, str(row["isotope_dat_sha256"])),
            ("log", log, str(row["log_sha256"])),
        ):
            if not path.is_file() or path.stat().st_size <= 0:
                raise RuntimeError(f"{job_identity}: missing {kind}: {rel(path)}")
            if sha256(path) != expected_hash:
                raise RuntimeError(f"{job_identity}: {kind} hash drift")
        source_geometry = _parse_unique_source_geometry(job_source)
        if source_geometry != expected_geometry:
            raise RuntimeError(f"{job_identity}: job-source Geometry differs from fixed geometry key")
        observed_dat_tt = _parse_unique_dat_tt(isotope_dat)
        observed_log_tt = _parse_unique_log_tt(log)
        if not (
            math.isclose(observed_dat_tt, observed_log_tt, rel_tol=0.0, abs_tol=1e-12)
            and math.isclose(observed_dat_tt, ledger_tt_dat, rel_tol=0.0, abs_tol=1e-12)
            and math.isclose(observed_log_tt, ledger_tt_log, rel_tol=0.0, abs_tol=1e-12)
        ):
            raise RuntimeError(
                f"{job_identity}: TT mismatch: DAT={observed_dat_tt}, log={observed_log_tt}, "
                f"ledger_DAT={ledger_tt_dat}, ledger_log={ledger_tt_log}"
            )
        jobs.append(
            JobInput(
                geometry=geometry,
                batch_id=str(ledger.get("batch_id")),
                ledger=ledger_path,
                ledger_sha256=ledger_digest,
                job_name=str(row["job_name"]),
                events=int(row["events"]),
                seed=int(row["seed"]),
                ordinal=int(row["ordinal"]) if row.get("ordinal") is not None else None,
                sum_tt_s=observed_dat_tt,
                sim=resolve_path(str(row["sim"])),
                sim_sha256=str(row["sim_sha256"]),
                expected_geometry_setup=expected_geometry,
                ledger_geometry_header=ledger_geometry,
                source_geometry=source_geometry,
                job_source=job_source,
                job_source_sha256=str(row["job_source_sha256"]),
                isotope_dat=isotope_dat,
                isotope_dat_sha256=str(row["isotope_dat_sha256"]),
                log=log,
                log_sha256=str(row["log_sha256"]),
            )
        )
    jobs.sort(
        key=lambda item: (
            item.batch_id,
            item.ordinal is None,
            item.ordinal if item.ordinal is not None else 0,
            item.job_name,
        )
    )
    return jobs


def _validate_profile_authority_payloads(
    profile: AuthorityProfile,
    ledger: dict[str, Any],
    validation: dict[str, Any],
) -> None:
    if (
        ledger.get("schema_version") != 1
        or ledger.get("batch_id") != "corrected_original_gamma_instant_batch0003"
        or ledger.get("status") != profile.ledger_status
        or ledger.get("errors") not in (None, [])
        or ledger.get("source_contract_manifest_sha256") != SOURCE_CONTRACT_SHA256
    ):
        raise RuntimeError(f"{profile.key}: ledger identity/status/source-contract mismatch")
    if (
        validation.get("schema_version") != 1
        or validation.get("status") != profile.validation_status
        or validation.get("errors") not in (None, [])
    ):
        raise RuntimeError(f"{profile.key}: validation is not a clean expected PASS")
    if resolve_path(str(ledger.get("validation_report"))).resolve() != profile.validation.resolve():
        raise RuntimeError(f"{profile.key}: ledger points to a noncanonical validation path")
    validation_digest = sha256(profile.validation)
    if ledger.get("validation_report_sha256") != validation_digest:
        raise RuntimeError(f"{profile.key}: ledger-to-validation SHA binding failed")
    if int(ledger.get("prior_events_per_geometry", profile.prior_events_per_geometry)) != profile.prior_events_per_geometry:
        raise RuntimeError(f"{profile.key}: prior event credit differs from the fixed profile")
    if int(ledger.get("cumulative_events_per_geometry", profile.cumulative_events_per_geometry)) != profile.cumulative_events_per_geometry:
        raise RuntimeError(f"{profile.key}: cumulative event count mismatch")
    if profile.key == "stage5":
        if ledger.get("stage") != "5m" or validation.get("stage") != "5m":
            raise RuntimeError("stage5: ledger/validation stage marker mismatch")
        if int(ledger.get("cumulative_target_events_per_geometry", -1)) != profile.cumulative_events_per_geometry:
            raise RuntimeError("stage5: cumulative target mismatch")
    elif profile.key == "prefix76":
        expected_prefix = {
            "prefix_start_ordinal": 1,
            "prefix_end_ordinal": profile.prefix_end_ordinal,
            "prior_events_per_geometry": profile.prior_events_per_geometry,
            "new_events_per_geometry": profile.new_events_per_geometry,
            "cumulative_events_per_geometry": profile.cumulative_events_per_geometry,
            "validated_pair_count": profile.prefix_end_ordinal,
        }
        if any(ledger.get(key) != value for key, value in expected_prefix.items()):
            raise RuntimeError("prefix76: exact ordinal/count envelope mismatch")
        selection = validation.get("selection", {})
        if (
            selection.get("selected_prefix_start_ordinal") != 1
            or selection.get("selected_prefix_end_ordinal") != profile.prefix_end_ordinal
            or validation.get("merge_eligibility") != profile.ledger_status
            or validation.get("cumulative_events_per_geometry") != profile.cumulative_events_per_geometry
            or validation.get("campaigns") != ledger.get("campaigns")
        ):
            raise RuntimeError("prefix76: report/ledger prefix envelope mismatch")
        boundary = ledger.get("authority_boundary", {})
        if any(
            boundary.get(key) is not False
            for key in (
                "full_batch0003_5m_or_10m_checkpoint_authority",
                "full_eight_family_authority",
                "physics_rate_sensitivity_or_geometry_promotion_authority",
            )
        ):
            raise RuntimeError("prefix76: non-full authority boundary is not explicit")
    else:
        raise RuntimeError(f"unsupported authority profile: {profile.key}")


def _build_authority_pin_payload(profile: AuthorityProfile) -> dict[str, Any]:
    if not profile.ledger.is_file() or not profile.validation.is_file():
        raise RuntimeError(f"{profile.key}: canonical ledger/validation pair is not published")
    ledger = _load_json(profile.ledger)
    validation = _load_json(profile.validation)
    _validate_profile_authority_payloads(profile, ledger, validation)
    return {
        "schema_version": 1,
        "status": "PASS__CORRECTED_GAMMA_AUTHORITY_PIN",
        "write_once": True,
        "authority_profile": profile.key,
        "mutually_exclusive_profile_selection": True,
        "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
        "ledger": rel(profile.ledger),
        "ledger_sha256": sha256(profile.ledger),
        "validation": rel(profile.validation),
        "validation_sha256": sha256(profile.validation),
        "prior_events_per_geometry": profile.prior_events_per_geometry,
        "new_events_per_geometry": profile.new_events_per_geometry,
        "cumulative_events_per_geometry": profile.cumulative_events_per_geometry,
        "prefix_end_ordinal": profile.prefix_end_ordinal,
        "full_checkpoint_authority": profile.full_checkpoint_authority,
    }


def write_authority_pin(
    profile: AuthorityProfile,
    *,
    pin_path: Path = CANONICAL_AUTHORITY_PIN,
) -> dict[str, Any]:
    """Bind one already-published fixed-path PASS pair without reading attempts."""

    payload = _build_authority_pin_payload(profile)
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    if pin_path.exists():
        if _load_json(pin_path) != payload:
            raise RuntimeError(
                "write-once authority pin already selects a different profile or content"
            )
        return payload
    temporary = pin_path.with_name(f".{pin_path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        atomic_json(temporary, payload)
        try:
            os.link(temporary, pin_path)
        except FileExistsError:
            if _load_json(pin_path) != payload:
                raise RuntimeError("concurrent authority pin selects different content")
    finally:
        if temporary.exists():
            temporary.unlink()
    return payload


def _load_authority_pin(profile: AuthorityProfile) -> dict[str, Any]:
    if not CANONICAL_AUTHORITY_PIN.is_file():
        flag = "--pin-stage5-authority" if profile.key == "stage5" else "--pin-prefix76"
        raise RuntimeError(
            f"authority pin is absent; after the fixed {profile.key} PASS pair is published, run {flag}"
        )
    pin = _load_json(CANONICAL_AUTHORITY_PIN)
    expected_fields = {
        "schema_version": 1,
        "status": "PASS__CORRECTED_GAMMA_AUTHORITY_PIN",
        "write_once": True,
        "authority_profile": profile.key,
        "mutually_exclusive_profile_selection": True,
        "source_contract_manifest_sha256": SOURCE_CONTRACT_SHA256,
        "ledger": rel(profile.ledger),
        "validation": rel(profile.validation),
        "prior_events_per_geometry": profile.prior_events_per_geometry,
        "new_events_per_geometry": profile.new_events_per_geometry,
        "cumulative_events_per_geometry": profile.cumulative_events_per_geometry,
        "prefix_end_ordinal": profile.prefix_end_ordinal,
        "full_checkpoint_authority": profile.full_checkpoint_authority,
    }
    if any(pin.get(key) != value for key, value in expected_fields.items()):
        raise RuntimeError("authority pin selects a different profile or has noncanonical metadata")
    for key in ("ledger_sha256", "validation_sha256"):
        value = pin.get(key)
        if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise RuntimeError(f"authority pin has malformed {key}")
    if _build_authority_pin_payload(profile) != pin:
        raise RuntimeError("authority pin no longer matches the fixed-path PASS pair")
    return pin


def collect_jobs(
    batch0000_ledger: Path,
    batch0001_ledger: Path,
    selected_ledger: Path,
    *,
    profile: AuthorityProfile = STAGE5_PROFILE,
    require_profile_envelope: bool = True,
    expected_ledger_sha256: tuple[str, str, str] | None = None,
    exact_ledger_paths: tuple[Path, Path, Path] | None = None,
    selected_validation_binding: tuple[Path, str] | None = None,
    geometry_contracts: dict[str, dict[str, Any]] = GEOMETRY_CONTRACTS,
) -> tuple[dict[str, list[JobInput]], list[dict[str, Any]], dict[str, str]]:
    paths = tuple(path.resolve() for path in (batch0000_ledger, batch0001_ledger, selected_ledger))
    if exact_ledger_paths is not None:
        canonical_paths = tuple(path.resolve() for path in exact_ledger_paths)
        if paths != canonical_paths:
            raise RuntimeError("alternate ledger path is forbidden in canonical mode")
    _validate_geometry_file_bindings(geometry_contracts)
    for path in paths:
        if not path.is_file():
            raise RuntimeError(f"required PASS ledger is missing: {rel(path)}")
    digests = {rel(path): sha256(path) for path in paths}
    if expected_ledger_sha256 is not None:
        observed = tuple(digests[rel(path)] for path in paths)
        if observed != expected_ledger_sha256:
            raise RuntimeError("one or more canonical ledger SHA-256 bindings failed")
    ledgers = [_load_json(path) for path in paths]
    expected_batch_ids = (
        "corrected_original_all8_fullsphere20_batch0000",
        "corrected_original_seven_family_fullsphere20_batch0001",
        "corrected_original_gamma_instant_batch0003",
    )
    expected_status = (
        "PASS__BATCH0000_MERGE_ELIGIBLE",
        "PASS__BATCH0001_MERGE_ELIGIBLE",
        profile.ledger_status,
    )
    for path, ledger, status, batch_id in zip(paths, ledgers, expected_status, expected_batch_ids, strict=True):
        if ledger.get("schema_version") != 1 or ledger.get("batch_id") != batch_id:
            raise RuntimeError(f"{rel(path)} schema/batch identity mismatch")
        if ledger.get("status") != status:
            raise RuntimeError(f"{rel(path)} status={ledger.get('status')!r}, expected {status!r}")
        if ledger.get("source_contract_manifest_sha256") != SOURCE_CONTRACT_SHA256:
            raise RuntimeError(f"{rel(path)} is not bound to the corrected-keV source contract")
        if ledger.get("errors") not in (None, []):
            raise RuntimeError(f"{rel(path)} carries non-empty errors")
    selected = ledgers[2]
    if require_profile_envelope:
        if profile.key == "stage5" and selected.get("stage") != "5m":
            raise RuntimeError("batch0003 selected ledger is not the stage-5M authority")
        if profile.key == "prefix76" and (
            selected.get("prefix_start_ordinal") != 1
            or selected.get("prefix_end_ordinal") != profile.prefix_end_ordinal
        ):
            raise RuntimeError("batch0003 selected ledger is not the exact configured prefix authority")
        prior_revalidation = selected.get("prior_credit_revalidation", {})
        if prior_revalidation.get("status") != "PASS" or any(
            int(prior_revalidation.get("credited_events_per_geometry", {}).get(geometry, -1))
            != profile.prior_events_per_geometry
            for geometry in GEOMETRIES
        ):
            raise RuntimeError(f"{profile.key}: prior 101k credit revalidation is not PASS")
    if selected_validation_binding is not None:
        expected_report, expected_report_hash = selected_validation_binding
        report = resolve_path(str(selected.get("validation_report"))).resolve()
        if report != expected_report.resolve():
            raise RuntimeError(f"{profile.key}: validation path is not canonical")
        if selected.get("validation_report_sha256") != expected_report_hash:
            raise RuntimeError("batch0003 ledger validation SHA differs from authority pin")
        if not report.is_file() or sha256(report) != expected_report_hash:
            raise RuntimeError("batch0003 fixed-path validation SHA binding failed")
        _validate_profile_authority_payloads(profile, selected, _load_json(report))
    elif selected.get("validation_report_sha256"):
        report = resolve_path(str(selected.get("validation_report")))
        if not report.is_file() or sha256(report) != selected["validation_report_sha256"]:
            raise RuntimeError("batch0003 selected validation report binding failed")

    jobs_by_geometry: dict[str, list[JobInput]] = {}
    inventory: list[dict[str, Any]] = []
    observed_job_identities: set[tuple[str, str, str]] = set()
    observed_artifact_paths: set[Path] = set()
    for geometry in GEOMETRIES:
        prior0 = _gamma_jobs(ledgers[0], geometry, paths[0], digests[rel(paths[0])], geometry_contracts)
        prior1 = _gamma_jobs(ledgers[1], geometry, paths[1], digests[rel(paths[1])], geometry_contracts)
        new = _gamma_jobs(ledgers[2], geometry, paths[2], digests[rel(paths[2])], geometry_contracts)
        prior_events = sum(job.events for job in prior0 + prior1)
        total_events = prior_events + sum(job.events for job in new)
        selected_campaign = _campaign(selected, geometry, stage=True)
        if int(selected_campaign.get("prior_events_credited", -1)) != prior_events:
            raise RuntimeError(f"{geometry}: selected ledger prior credit does not match batch0000+0001")
        if int(selected_campaign.get("new_events_validated", -1)) != sum(job.events for job in new):
            raise RuntimeError(f"{geometry}: selected new-event count mismatch")
        if int(selected_campaign.get("cumulative_events", -1)) != total_events:
            raise RuntimeError(f"{geometry}: selected cumulative-event count mismatch")
        if require_profile_envelope:
            if (
                prior_events != profile.prior_events_per_geometry
                or sum(job.events for job in new) != profile.new_events_per_geometry
                or total_events != profile.cumulative_events_per_geometry
            ):
                raise RuntimeError(
                    f"{geometry}: {profile.key} must be {profile.prior_events_per_geometry} prior + "
                    f"{profile.new_events_per_geometry} new "
                    f"= {profile.cumulative_events_per_geometry}; got {prior_events} + "
                    f"{sum(job.events for job in new)} = {total_events}"
                )
            if (
                len(prior0) != profile.expected_prior_shards[0]
                or len(prior1) != profile.expected_prior_shards[1]
                or len(new) != profile.expected_new_shards
            ):
                raise RuntimeError(
                    f"{geometry}: canonical shard counts must be {profile.expected_prior_shards[0]}+"
                    f"{profile.expected_prior_shards[1]}+{profile.expected_new_shards}"
                )
            if int(selected_campaign.get("validated_shards", -1)) != profile.expected_new_shards:
                raise RuntimeError(f"{geometry}: selected validated-shard count mismatch")
            if profile.prefix_end_ordinal is not None and [job.ordinal for job in new] != list(
                range(1, profile.prefix_end_ordinal + 1)
            ):
                raise RuntimeError(f"{geometry}: selected jobs are not exact continuous ordinal prefix")
            if not math.isclose(
                float(selected_campaign.get("TT_s_new_sum", -1.0)),
                math.fsum(job.sum_tt_s for job in new),
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                raise RuntimeError(f"{geometry}: selected TT_s_new_sum does not close over jobs")
        seeds = [job.seed for job in prior0 + prior1 + new]
        if len(seeds) != len(set(seeds)):
            raise RuntimeError(f"{geometry}: duplicate registered gamma seed")
        jobs_by_geometry[geometry] = prior0 + prior1 + new
        for job in jobs_by_geometry[geometry]:
            identity = (job.geometry, job.batch_id, job.job_name)
            if identity in observed_job_identities:
                raise RuntimeError(f"duplicate job identity: {identity!r}")
            observed_job_identities.add(identity)
            for artifact in (job.sim, job.job_source, job.isotope_dat, job.log):
                resolved_artifact = artifact.resolve()
                if resolved_artifact in observed_artifact_paths:
                    raise RuntimeError(
                        f"artifact reused by more than one prior/selected job identity: {rel(artifact)}"
                    )
                observed_artifact_paths.add(resolved_artifact)
            if job.events <= 0 or len(job.sim_sha256) != 64:
                raise RuntimeError(f"{geometry}/{job.job_name}: malformed job identity")
            for kind, path, expected_hash in (
                ("job_source", job.job_source, job.job_source_sha256),
                ("isotope_dat", job.isotope_dat, job.isotope_dat_sha256),
                ("log", job.log, job.log_sha256),
            ):
                if not path.is_file() or path.stat().st_size <= 0:
                    raise RuntimeError(f"{geometry}/{job.job_name}: missing {kind}: {rel(path)}")
                if sha256(path) != expected_hash:
                    raise RuntimeError(f"{geometry}/{job.job_name}: {kind} hash drift")
            source_text = job.job_source.read_text(encoding="utf-8")
            if not (
                job.ledger_geometry_header == job.expected_geometry_setup
                and job.source_geometry == job.expected_geometry_setup
            ):
                raise RuntimeError(f"{geometry}/{job.job_name}: ledger/source/fixed Geometry mismatch")
            if "cosima_spectra_dp_2602units" in source_text:
                raise RuntimeError(f"{geometry}/{job.job_name}: legacy spectrum reference is forbidden")
            if require_profile_envelope and source_text.count(
                "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
            ) != 20:
                raise RuntimeError(f"{geometry}/{job.job_name}: corrected 20-bin source reference closure failed")
            if not job.sim.is_file() or job.sim.stat().st_size <= 0:
                raise RuntimeError(f"{geometry}/{job.job_name}: missing SIM: {rel(job.sim)}")
            inventory.append(
                {
                    "geometry": geometry,
                    "batch_id": job.batch_id,
                    "ledger": rel(job.ledger),
                    "ledger_sha256": job.ledger_sha256,
                    "job_name": job.job_name,
                    "events": job.events,
                    "seed": job.seed,
                    "ordinal": job.ordinal,
                    "TT_s": job.sum_tt_s,
                    "observed_TT_s_from_isotope_dat": _parse_unique_dat_tt(job.isotope_dat),
                    "observed_TT_s_from_log": _parse_unique_log_tt(job.log),
                    "sim": rel(job.sim),
                    "ledger_sim_sha256": job.sim_sha256,
                    "observed_sim_sha256": None,
                    "sim_bytes": job.sim.stat().st_size,
                    "job_source": rel(job.job_source),
                    "job_source_sha256": job.job_source_sha256,
                    "fixed_geometry_setup": rel(job.expected_geometry_setup),
                    "ledger_geometry_header": rel(job.ledger_geometry_header),
                    "job_source_geometry": rel(job.source_geometry),
                    "isotope_dat": rel(job.isotope_dat),
                    "isotope_dat_sha256": job.isotope_dat_sha256,
                    "log": rel(job.log),
                    "log_sha256": job.log_sha256,
                }
            )
    # Same-seed A/B scheduling is provenance only.  The assertion below checks
    # operational identity without granting a paired-estimator interpretation.
    for geometry in GEOMETRIES[1:]:
        left = [(job.batch_id, job.job_name, job.events, job.seed) for job in jobs_by_geometry[GEOMETRIES[0]]]
        right = [(job.batch_id, job.job_name, job.events, job.seed) for job in jobs_by_geometry[geometry]]
        if left != right:
            raise RuntimeError("cross-geometry gamma shard schedule is not operationally matched")
    return jobs_by_geometry, inventory, digests


def collect_canonical_jobs(
    profile: AuthorityProfile,
) -> tuple[dict[str, list[JobInput]], list[dict[str, Any]], dict[str, str]]:
    """Collect the two frozen prior ledgers plus one pinned profile authority."""

    if AUTHORITY_PROFILES.get(profile.key) != profile:
        raise RuntimeError("canonical collection requires an exact built-in authority profile")
    pin = _load_authority_pin(profile)
    return collect_jobs(
        DEFAULT_BATCH0000_LEDGER,
        DEFAULT_BATCH0001_LEDGER,
        profile.ledger,
        profile=profile,
        require_profile_envelope=True,
        expected_ledger_sha256=(
            CANONICAL_BATCH0000_LEDGER_SHA256,
            CANONICAL_BATCH0001_LEDGER_SHA256,
            str(pin["ledger_sha256"]),
        ),
        exact_ledger_paths=(DEFAULT_BATCH0000_LEDGER, DEFAULT_BATCH0001_LEDGER, profile.ledger),
        selected_validation_binding=(profile.validation, str(pin["validation_sha256"])),
        geometry_contracts=GEOMETRY_CONTRACTS,
    )


class HashingRawReader(io.RawIOBase):
    """Read-only raw stream that hashes the exact compressed bytes consumed."""

    def __init__(self, path: Path):
        super().__init__()
        self._handle = path.open("rb", buffering=0)
        self._digest = hashlib.sha256()

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: bytearray | memoryview) -> int:
        data = self._handle.read(len(buffer))
        if not data:
            return 0
        self._digest.update(data)
        buffer[: len(data)] = data
        return len(data)

    def close(self) -> None:
        if not self.closed:
            self._handle.close()
        super().close()

    def hexdigest(self) -> str:
        return self._digest.hexdigest()


@dataclass
class EventState:
    local_id: int | None = None
    init_count: int = 0
    init_energy_keV: float | None = None
    theta_deg: float | None = None
    dir_z: float | None = None
    pixel_e: dict[str, float] = field(default_factory=lambda: defaultdict(float))
    active_shield_keV: float = 0.0
    plastic_keV: float = 0.0
    excluded_kapton_keV: float = 0.0
    has_pair: bool = False
    has_annihilation: bool = False


@dataclass
class GeometryAccumulator:
    geometry: str
    primary_count: int = 0
    sum_tt_s: float = 0.0
    raw_tes_positive: int = 0
    measured_tes_positive: int = 0
    kapton_positive_tes_events: int = 0
    primary_energy_denominator: Counter[int] = field(default_factory=Counter)
    theta_denominator: Counter[int] = field(default_factory=Counter)
    cut_counts: Counter[tuple[str, str]] = field(default_factory=Counter)
    pair_counts: Counter[tuple[str, str, str]] = field(default_factory=Counter)
    driver_counts: Counter[tuple[str, int, str, str]] = field(default_factory=Counter)
    histogram_counts: Counter[tuple[str, str, int]] = field(default_factory=Counter)
    histogram_underflow: Counter[tuple[str, str]] = field(default_factory=Counter)
    histogram_overflow: Counter[tuple[str, str]] = field(default_factory=Counter)

    def process_event(self, job: JobInput, event: EventState, event_writer: csv.DictWriter) -> None:
        if event.local_id is None:
            return
        if event.init_count != 1 or event.init_energy_keV is None or event.theta_deg is None:
            raise RuntimeError(f"{rel(job.sim)} ID {event.local_id}: expected exactly one valid IA INIT")
        self.primary_count += 1
        energy_index = bin_index(event.init_energy_keV, ENERGY_EDGES)
        theta_index = bin_index(event.theta_deg, THETA_EDGES)
        self.primary_energy_denominator[energy_index] += 1
        self.theta_denominator[theta_index] += 1

        raw_pixels = [(name, energy) for name, energy in sorted(event.pixel_e.items()) if energy > 0.0]
        raw_total = math.fsum(energy for _, energy in raw_pixels)
        measured_pixels: list[tuple[str, float]] = []
        for pixel, energy in raw_pixels:
            normal = keyed_standard_normal(*job.event_key_prefix, event.local_id, pixel)
            measured = energy + SIGMA_KEV * normal
            if measured >= PIXEL_THRESHOLD_KEV:
                measured_pixels.append((pixel, measured))
        measured_total = math.fsum(energy for _, energy in measured_pixels)
        if raw_total > 0.0:
            self.raw_tes_positive += 1
        if measured_total > 0.0:
            self.measured_tes_positive += 1
        if measured_total > 0.0 and event.excluded_kapton_keV > 0.0:
            self.kapton_positive_tes_events += 1

        selection_flags = {"pre_veto": True}
        for threshold in VETO_THRESHOLDS_KEV:
            selection_flags[f"veto{threshold}"] = event.active_shield_keV < threshold and (
                self.geometry != "s3d_o8" or event.plastic_keV < O8_PLASTIC_THRESHOLD_KEV
            )
        flags = window_flags(measured_total)
        process = pair_category(event.has_pair, event.has_annihilation)
        for selection, passes_veto in selection_flags.items():
            if not passes_veto:
                continue
            for window, passes_window in flags.items():
                if not passes_window:
                    continue
                self.cut_counts[(selection, window)] += 1
                self.pair_counts[(selection, window, process)] += 1
                self.driver_counts[("initial_energy", energy_index, selection, window)] += 1
                self.driver_counts[("theta", theta_index, selection, window)] += 1
            if measured_total > 0.0:
                for view, (edges, _) in HISTOGRAM_VIEWS.items():
                    index = bisect.bisect_right(edges, measured_total) - 1
                    if index < 0:
                        self.histogram_underflow[(selection, view)] += 1
                    elif index >= len(edges) - 1:
                        self.histogram_overflow[(selection, view)] += 1
                    else:
                        self.histogram_counts[(selection, view, index)] += 1

        if raw_total > 0.0:
            event_writer.writerow(
                {
                    "geometry": self.geometry,
                    "batch_id": job.batch_id,
                    "job_name": job.job_name,
                    "seed": job.seed,
                    "local_event_id": event.local_id,
                    "init_energy_keV": f"{event.init_energy_keV:.12g}",
                    "source_theta_deg": f"{event.theta_deg:.12g}",
                    "source_hemisphere": "+z" if event.theta_deg < 90.0 else "-z",
                    "tes_raw_keV": f"{raw_total:.12g}",
                    "tes_measured_keV": f"{measured_total:.12g}",
                    "raw_pixel_count": len(raw_pixels),
                    "measured_pixel_count": len(measured_pixels),
                    "raw_pixels_json": json.dumps(
                        dict(raw_pixels), sort_keys=True, separators=(",", ":"), allow_nan=False
                    ),
                    "measured_pixels_json": json.dumps(
                        dict(measured_pixels), sort_keys=True, separators=(",", ":"), allow_nan=False
                    ),
                    "active_shield_keV": f"{event.active_shield_keV:.12g}",
                    "plastic_keV": f"{event.plastic_keV:.12g}",
                    "excluded_kapton_keV": f"{event.excluded_kapton_keV:.12g}",
                    "has_pair_ia": int(event.has_pair),
                    "has_annihilation_ia": int(event.has_annihilation),
                    "pair_annihilation_category": process,
                    "pass_veto50": int(selection_flags["veto50"]),
                    "pass_veto70": int(selection_flags["veto70"]),
                    "pass_veto80": int(selection_flags["veto80"]),
                    "in_480_550": int(flags["broad_480_550"]),
                    "in_w2": int(flags["w2_510p58_511p42"]),
                }
            )


EVENT_FIELDS = (
    "geometry",
    "batch_id",
    "job_name",
    "seed",
    "local_event_id",
    "init_energy_keV",
    "source_theta_deg",
    "source_hemisphere",
    "tes_raw_keV",
    "tes_measured_keV",
    "raw_pixel_count",
    "measured_pixel_count",
    "raw_pixels_json",
    "measured_pixels_json",
    "active_shield_keV",
    "plastic_keV",
    "excluded_kapton_keV",
    "has_pair_ia",
    "has_annihilation_ia",
    "pair_annihilation_category",
    "pass_veto50",
    "pass_veto70",
    "pass_veto80",
    "in_480_550",
    "in_w2",
)


def _parse_init(line: str) -> tuple[int, float, float, float]:
    fields = [field.strip() for field in line.split("IA INIT", 1)[1].split(";")]
    if len(fields) < 23:
        raise ValueError(f"malformed IA INIT with {len(fields)} fields")
    particle_type = int(fields[15])
    direction = (float(fields[16]), float(fields[17]), float(fields[18]))
    energy = float(fields[22])
    if not all(math.isfinite(value) for value in (*direction, energy)):
        raise ValueError("non-finite IA INIT field")
    norm = math.sqrt(math.fsum(value * value for value in direction))
    if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=5e-4):
        raise ValueError(f"non-unit IA INIT direction norm={norm}")
    # FarFieldAreaSource's source-side direction is opposite to the inward IA
    # direction.  Store source theta rather than the mirrored IA theta used by
    # the earlier 100k diagnostic.
    theta = math.degrees(math.acos(max(-1.0, min(1.0, -direction[2]))))
    return particle_type, energy, theta, direction[2]


def _relevant_volume(geometry: str, volume: str) -> str | None:
    if TES_RE.match(volume):
        return "tes"
    if "KAPTON" in volume.upper():
        return "kapton"
    if geometry == "mass_model_511" and volume in MASS_TRUE_CSI_VOLUMES:
        return "active"
    if geometry == "s3d_o8" and volume in O8_TRUE_BGO_VOLUMES:
        return "active"
    if geometry == "s3d_o8" and volume in O8_TRUE_PLASTIC_VOLUMES:
        return "plastic"
    return None


def parse_job(job: JobInput, accumulator: GeometryAccumulator, event_writer: csv.DictWriter) -> str:
    before = job.sim.stat()
    hashing_raw = HashingRawReader(job.sim)
    buffered = io.BufferedReader(hashing_raw, buffer_size=1024 * 1024)
    event = EventState()
    expected_next_id = 1
    se_records = 0
    end_records = 0
    footer_ts: int | None = None
    footer_te: float | None = None
    header_seed: int | None = None
    header_geometry: str | None = None
    header_geometry_count = 0

    def flush() -> None:
        nonlocal event
        if event.local_id is not None:
            accumulator.process_event(job, event, event_writer)
        event = EventState()

    try:
        with gzip.GzipFile(fileobj=buffered, mode="rb") as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", errors="replace") as handle:
                for raw in handle:
                    line = raw.strip()
                    if match := GEOMETRY_RE.match(line):
                        header_geometry_count += 1
                        if header_geometry is None:
                            header_geometry = match.group(1)
                        continue
                    if header_seed is None and (match := SEED_RE.match(line)):
                        header_seed = int(match.group(1))
                        continue
                    if line == "SE":
                        flush()
                        se_records += 1
                        continue
                    if line == "EN":
                        end_records += 1
                        continue
                    if line.startswith("TS "):
                        footer_ts = int(line.split()[1])
                        continue
                    if line.startswith("TE "):
                        footer_te = float(line.split()[1])
                        continue
                    if line.startswith("ID "):
                        if event.local_id is not None:
                            raise RuntimeError(f"{rel(job.sim)}: ID before SE")
                        event.local_id = int(line.split()[1])
                        if event.local_id != expected_next_id:
                            raise RuntimeError(
                                f"{rel(job.sim)}: ID={event.local_id}, expected {expected_next_id}"
                            )
                        expected_next_id += 1
                        continue
                    if line.startswith("IA INIT"):
                        if event.local_id is None:
                            raise RuntimeError(f"{rel(job.sim)}: IA INIT outside event")
                        particle, energy, theta, direction_z = _parse_init(line)
                        if particle != 1 or energy <= 0.0:
                            raise RuntimeError(f"{rel(job.sim)} ID {event.local_id}: non-gamma/invalid IA INIT")
                        event.init_count += 1
                        event.init_energy_keV = energy
                        event.theta_deg = theta
                        event.dir_z = direction_z
                        continue
                    if line.startswith("IA PAIR"):
                        event.has_pair = True
                        continue
                    if line.startswith("IA ANNI"):
                        event.has_annihilation = True
                        continue
                    if not line.startswith("CC HIT "):
                        continue
                    parts = line.split(maxsplit=3)
                    if len(parts) != 4:
                        raise RuntimeError(f"{rel(job.sim)}: malformed CC HIT")
                    volume = parts[2]
                    role = _relevant_volume(job.geometry, volume)
                    if role is None:
                        continue
                    match = EDEP_RE.search(parts[3])
                    if match is None:
                        raise RuntimeError(f"{rel(job.sim)}: relevant CC HIT lacks edep_keV")
                    energy = float(match.group(1))
                    if not math.isfinite(energy) or energy < 0.0:
                        raise RuntimeError(f"{rel(job.sim)}: invalid deposit {energy}")
                    if role == "tes":
                        event.pixel_e[volume] += energy
                    elif role == "active":
                        event.active_shield_keV += energy
                    elif role == "plastic":
                        event.plastic_keV += energy
                    else:
                        event.excluded_kapton_keV += energy
        flush()
    except (OSError, EOFError, gzip.BadGzipFile, UnicodeError) as exc:
        raise RuntimeError(f"{rel(job.sim)} gzip/read failure: {exc}") from exc
    finally:
        if not buffered.closed:
            buffered.close()
    observed_digest = hashing_raw.hexdigest()
    after = job.sim.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise RuntimeError(f"{rel(job.sim)} changed while being parsed")
    if observed_digest != job.sim_sha256:
        raise RuntimeError(f"{rel(job.sim)} compressed SHA-256 differs from PASS ledger")
    parsed = expected_next_id - 1
    if parsed != job.events or se_records != job.events:
        raise RuntimeError(
            f"{rel(job.sim)} event closure failed: ID={parsed}, SE={se_records}, expected={job.events}"
        )
    if end_records != 1 or footer_ts != job.events or footer_te is None or not footer_te > 0.0:
        raise RuntimeError(
            f"{rel(job.sim)} footer closure failed: EN={end_records}, TS={footer_ts}, TE={footer_te}"
        )
    if header_seed != job.seed:
        raise RuntimeError(f"{rel(job.sim)} Seed={header_seed}, expected={job.seed}")
    if header_geometry is None or header_geometry_count != 1:
        raise RuntimeError(f"{rel(job.sim)} expected exactly one Geometry header, got {header_geometry_count}")
    sim_geometry = resolve_path(header_geometry).resolve()
    if not (
        sim_geometry
        == job.ledger_geometry_header
        == job.source_geometry
        == job.expected_geometry_setup
    ):
        raise RuntimeError(
            f"{rel(job.sim)} Geometry mismatch across SIM header, ledger, job source, and fixed geometry key"
        )
    return observed_digest


def _selection_thresholds(selection: str) -> tuple[float | None, float | None]:
    if selection == "pre_veto":
        return None, None
    threshold = float(selection.removeprefix("veto"))
    return threshold, O8_PLASTIC_THRESHOLD_KEV


def build_cutflow_rows(accumulators: dict[str, GeometryAccumulator]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        acc = accumulators[geometry]
        for selection in SELECTIONS:
            shield_threshold, plastic_threshold = _selection_thresholds(selection)
            for window in WINDOWS:
                count = int(acc.cut_counts[(selection, window)])
                poisson_low, poisson_high = garwood_interval(count)
                efficiency_low, efficiency_high = wilson_interval(count, acc.primary_count)
                pre_count = int(acc.cut_counts[("pre_veto", window)])
                survival_low, survival_high = wilson_interval(count, pre_count)
                rows.append(
                    {
                        "geometry": geometry,
                        "selection": selection,
                        "window": window,
                        "active_shield_threshold_keV": shield_threshold,
                        "o8_plastic_threshold_keV": plastic_threshold if geometry == "s3d_o8" else None,
                        "primary_count": acc.primary_count,
                        "sum_TT_s": acc.sum_tt_s,
                        "count": count,
                        "rate_s-1": count / acc.sum_tt_s,
                        "rate_garwood95_low_s-1": poisson_low / acc.sum_tt_s,
                        "rate_garwood95_high_s-1": poisson_high / acc.sum_tt_s,
                        "zero_count_one_sided95_rate_upper_s-1": (
                            -math.log(0.05) / acc.sum_tt_s if count == 0 else None
                        ),
                        "efficiency_per_primary": count / acc.primary_count,
                        "efficiency_wilson95_low": efficiency_low,
                        "efficiency_wilson95_high": efficiency_high,
                        "pre_veto_window_count": pre_count,
                        "veto_survival_fraction": count / pre_count if pre_count else None,
                        "veto_survival_wilson95_low": survival_low,
                        "veto_survival_wilson95_high": survival_high,
                    }
                )
    return rows


def build_histogram_rows(accumulators: dict[str, GeometryAccumulator]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        acc = accumulators[geometry]
        for selection in SELECTIONS:
            for view, (edges, width_unit) in HISTOGRAM_VIEWS.items():
                transformed = tuple(math.log10(value) for value in edges) if width_unit == "log10_keV" else edges
                for index in range(len(edges) - 1):
                    count = int(acc.histogram_counts[(selection, view, index)])
                    low, high = garwood_interval(count)
                    width = transformed[index + 1] - transformed[index]
                    rows.append(
                        {
                            "geometry": geometry,
                            "selection": selection,
                            "view": view,
                            "bin_index": index,
                            "energy_low_keV": edges[index],
                            "energy_high_keV": edges[index + 1],
                            "width_unit": width_unit,
                            "bin_width": width,
                            "count": count,
                            "count_garwood95_low": low,
                            "count_garwood95_high": high,
                            "rate_density_s-1_per_width": count / acc.sum_tt_s / width,
                            "rate_density_garwood95_low_s-1_per_width": low / acc.sum_tt_s / width,
                            "rate_density_garwood95_high_s-1_per_width": high / acc.sum_tt_s / width,
                            "events_per_million_primaries_per_width": count * 1e6 / acc.primary_count / width,
                            "underflow_count_for_view": int(acc.histogram_underflow[(selection, view)]),
                            "overflow_count_for_view": int(acc.histogram_overflow[(selection, view)]),
                        }
                    )
    return rows


def build_driver_rows(accumulators: dict[str, GeometryAccumulator]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        acc = accumulators[geometry]
        dimensions = (
            ("initial_energy", len(ENERGY_LABELS), acc.primary_energy_denominator),
            ("theta", len(THETA_EDGES) - 1, acc.theta_denominator),
        )
        for dimension, size, denominator in dimensions:
            for index in range(size):
                primaries = int(denominator[index])
                if dimension == "initial_energy":
                    label = ENERGY_LABELS[index]
                    low_value = ENERGY_EDGES[index]
                    raw_high_value = ENERGY_EDGES[index + 1]
                    high_value = None if math.isinf(raw_high_value) else raw_high_value
                    high_open_ended = math.isinf(raw_high_value)
                else:
                    label = f"{THETA_EDGES[index]:g}-{THETA_EDGES[index + 1]:g} deg"
                    low_value = THETA_EDGES[index]
                    high_value = THETA_EDGES[index + 1]
                    high_open_ended = False
                for selection in SELECTIONS:
                    for window in WINDOWS:
                        count = int(acc.driver_counts[(dimension, index, selection, window)])
                        low, high = wilson_interval(count, primaries)
                        rows.append(
                            {
                                "geometry": geometry,
                                "dimension": dimension,
                                "bin_index": index,
                                "bin_label": label,
                                "bin_low": low_value,
                                "bin_high": high_value,
                                "bin_high_open_ended": high_open_ended,
                                "selection": selection,
                                "window": window,
                                "primary_count": primaries,
                                "selected_count": count,
                                "efficiency": count / primaries if primaries else None,
                                "efficiency_wilson95_low": low,
                                "efficiency_wilson95_high": high,
                            }
                        )
    return rows


def build_pair_rows(accumulators: dict[str, GeometryAccumulator]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    categories = ("neither", "pair_only", "annihilation_only", "pair_and_annihilation")
    for geometry in GEOMETRIES:
        acc = accumulators[geometry]
        for selection in SELECTIONS:
            for window in WINDOWS:
                denominator = int(acc.cut_counts[(selection, window)])
                for category in categories:
                    count = int(acc.pair_counts[(selection, window, category)])
                    low, high = wilson_interval(count, denominator)
                    poisson_low, poisson_high = garwood_interval(count)
                    rows.append(
                        {
                            "geometry": geometry,
                            "selection": selection,
                            "window": window,
                            "pair_annihilation_category": category,
                            "window_count": denominator,
                            "count": count,
                            "fraction": count / denominator if denominator else None,
                            "fraction_wilson95_low": low,
                            "fraction_wilson95_high": high,
                            "rate_s-1": count / acc.sum_tt_s,
                            "rate_garwood95_low_s-1": poisson_low / acc.sum_tt_s,
                            "rate_garwood95_high_s-1": poisson_high / acc.sum_tt_s,
                        }
                    )
    return rows


def _plot_spectra(
    histogram_rows: list[dict[str, Any]],
    output_png: Path,
    output_svg: Path,
    profile_title: str,
) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/tes_gamma_prompt_mplconfig")
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["svg.fonttype"] = "none"
    import matplotlib.pyplot as plt
    import numpy as np

    colors = {"pre_veto": "#0072B2", "veto50": "#D55E00"}
    labels = {"pre_veto": "Before active veto", "veto50": "Nominal active veto"}
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.8), constrained_layout=True)
    for row_index, geometry in enumerate(GEOMETRIES):
        for column_index, view in enumerate(("full_log", "line_480_550")):
            axis = axes[row_index, column_index]
            for selection in ("pre_veto", "veto50"):
                rows = [
                    row
                    for row in histogram_rows
                    if row["geometry"] == geometry and row["selection"] == selection and row["view"] == view
                ]
                rows.sort(key=lambda row: int(row["bin_index"]))
                edges = np.asarray([row["energy_low_keV"] for row in rows] + [rows[-1]["energy_high_keV"]])
                values = np.asarray([row["rate_density_s-1_per_width"] for row in rows])
                plot_values = np.where(values > 0.0, values, np.nan) if view == "full_log" else values
                axis.stairs(plot_values, edges, color=colors[selection], linewidth=1.7, label=labels[selection])
            axis.set_title(
                f"{GEOMETRY_LABELS[geometry]} — "
                + ("full measured TES spectrum" if view == "full_log" else "480–550 keV measured TES spectrum")
            )
            axis.set_xlabel("Event-summed TES energy (keV)")
            axis.grid(True, which="both", alpha=0.18)
            if view == "full_log":
                axis.set_xscale("log")
                axis.set_yscale("log")
                axis.set_ylabel("Events s$^{-1}$ per log$_{10}$(keV)")
            else:
                axis.axvspan(W2_KEV[0], W2_KEV[1], color="#777777", alpha=0.17, linewidth=0)
                axis.set_xlim(*BROAD_KEV)
                axis.set_ylim(bottom=0.0)
                axis.set_ylabel("Events s$^{-1}$ keV$^{-1}$")
            if row_index == 0 and column_index == 0:
                axis.legend(frameon=False)
    fig.suptitle(
        f"{profile_title}\nPrompt gamma TES spectra\n"
        "420 eV FWHM per pixel, 0.3 keV post-noise pixel threshold; nominal O8 plastic veto fixed at 50 keV",
        fontsize=13,
    )
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=180, facecolor="white")
    fig.savefig(output_svg, facecolor="white")
    plt.close(fig)


def _plot_cutflow(
    cutflow_rows: list[dict[str, Any]],
    output_png: Path,
    output_svg: Path,
    profile_title: str,
) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/tes_gamma_prompt_mplconfig")
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["svg.fonttype"] = "none"
    import matplotlib.pyplot as plt
    import numpy as np

    colors = {"mass_model_511": "#0072B2", "s3d_o8": "#D55E00"}
    titles = {
        "tes_positive": "TES-positive events",
        "broad_480_550": "480–550 keV events",
        "w2_510p58_511p42": "510.58–511.42 keV events",
    }
    x = np.arange(len(SELECTIONS), dtype=float)
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.8), constrained_layout=True)
    for axis, window in zip(axes, WINDOWS, strict=True):
        for offset, geometry in ((-0.18, "mass_model_511"), (0.18, "s3d_o8")):
            rows = [
                next(
                    row
                    for row in cutflow_rows
                    if row["geometry"] == geometry and row["selection"] == selection and row["window"] == window
                )
                for selection in SELECTIONS
            ]
            rates = np.asarray([row["rate_s-1"] for row in rows])
            lows = np.asarray([row["rate_garwood95_low_s-1"] for row in rows])
            highs = np.asarray([row["rate_garwood95_high_s-1"] for row in rows])
            bars = axis.bar(x + offset, rates, width=0.34, color=colors[geometry], alpha=0.78, label=GEOMETRY_LABELS[geometry])
            axis.errorbar(
                x + offset,
                rates,
                yerr=np.vstack((rates - lows, highs - rates)),
                fmt="none",
                color="#222222",
                linewidth=0.8,
                capsize=2.0,
            )
            for bar, row in zip(bars, rows, strict=True):
                axis.annotate(
                    str(row["count"]),
                    (bar.get_x() + bar.get_width() / 2.0, max(bar.get_height(), row["rate_garwood95_high_s-1"])),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                )
        axis.set_title(titles[window])
        axis.set_xticks(x, ("Pre", "50", "70", "80"))
        axis.set_xlabel("Active-shield veto threshold (keV)")
        axis.set_ylabel("Selected rate (s$^{-1}$)")
        axis.set_ylim(bottom=0.0)
        axis.grid(True, axis="y", alpha=0.18)
    axes[0].legend(frameon=False, fontsize=9)
    fig.suptitle(
        f"{profile_title}\nPrompt gamma veto cutflow\n"
        "Bars: count/sum(TT); error bars: exact 95% Garwood intervals; O8 plastic threshold = 50 keV",
        fontsize=13,
    )
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=180, facecolor="white")
    fig.savefig(output_svg, facecolor="white")
    plt.close(fig)


def _plot_drivers(
    driver_rows: list[dict[str, Any]],
    output_png: Path,
    output_svg: Path,
    profile_title: str,
) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/tes_gamma_prompt_mplconfig")
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.rcParams["svg.fonttype"] = "none"
    import matplotlib.pyplot as plt
    import numpy as np

    colors = {"mass_model_511": "#0072B2", "s3d_o8": "#D55E00"}
    fig, axes = plt.subplots(1, 2, figsize=(14.0, 5.0), constrained_layout=True)
    for geometry in GEOMETRIES:
        energy_rows = [
            row
            for row in driver_rows
            if row["geometry"] == geometry
            and row["dimension"] == "initial_energy"
            and row["selection"] == "veto50"
            and row["window"] == "tes_positive"
        ]
        energy_rows.sort(key=lambda row: int(row["bin_index"]))
        x = np.arange(len(energy_rows))
        y = np.asarray([row["efficiency"] if row["efficiency"] is not None else np.nan for row in energy_rows])
        low = np.asarray([row["efficiency_wilson95_low"] if row["efficiency_wilson95_low"] is not None else np.nan for row in energy_rows])
        high = np.asarray([row["efficiency_wilson95_high"] if row["efficiency_wilson95_high"] is not None else np.nan for row in energy_rows])
        axes[0].errorbar(
            x,
            y,
            yerr=np.vstack((y - low, high - y)),
            color=colors[geometry],
            marker="o",
            linewidth=1.4,
            capsize=2.0,
            label=GEOMETRY_LABELS[geometry],
        )
        theta_rows = [
            row
            for row in driver_rows
            if row["geometry"] == geometry
            and row["dimension"] == "theta"
            and row["selection"] == "veto50"
            and row["window"] == "tes_positive"
        ]
        theta_rows.sort(key=lambda row: int(row["bin_index"]))
        centers = np.asarray([(row["bin_low"] + row["bin_high"]) / 2.0 for row in theta_rows])
        y = np.asarray([row["efficiency"] if row["efficiency"] is not None else np.nan for row in theta_rows])
        low = np.asarray([row["efficiency_wilson95_low"] if row["efficiency_wilson95_low"] is not None else np.nan for row in theta_rows])
        high = np.asarray([row["efficiency_wilson95_high"] if row["efficiency_wilson95_high"] is not None else np.nan for row in theta_rows])
        axes[1].errorbar(
            centers,
            y,
            yerr=np.vstack((y - low, high - y)),
            color=colors[geometry],
            marker="o",
            linewidth=1.4,
            capsize=2.0,
            label=GEOMETRY_LABELS[geometry],
        )
    axes[0].set_xticks(np.arange(len(ENERGY_LABELS)), ENERGY_LABELS, rotation=45, ha="right")
    axes[0].set_title("Initial gamma energy bands")
    axes[0].set_xlabel("Primary kinetic energy")
    axes[1].set_title("Initial gamma direction")
    axes[1].set_xlabel("Source-side polar angle acos(-IA dir_z) (deg)")
    axes[1].set_xlim(0.0, 180.0)
    for axis in axes:
        axis.set_ylabel("Post-veto TES-positive efficiency")
        axis.set_ylim(bottom=0.0)
        axis.grid(True, alpha=0.18)
    axes[0].legend(frameon=False)
    fig.suptitle(
        f"{profile_title}\nPrompt gamma TES drivers; nominal 50 keV true active-shield veto; "
        "Wilson 95% intervals",
        fontsize=13,
    )
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=180, facecolor="white")
    fig.savefig(output_svg, facecolor="white")
    plt.close(fig)


def _published_rel(path: Path, work_dir: Path, published_dir: Path) -> str:
    return rel(published_dir / path.resolve().relative_to(work_dir.resolve()))


def _figure_qa(
    paths: Iterable[Path], *, work_dir: Path | None = None, published_dir: Path | None = None
) -> dict[str, Any]:
    from PIL import Image

    result: dict[str, Any] = {}
    for path in paths:
        if path.suffix.lower() != ".png":
            continue
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            key = (
                _published_rel(path, work_dir, published_dir)
                if work_dir is not None and published_dir is not None
                else rel(path)
            )
            result[key] = {"format": image.format, "width": image.width, "height": image.height}
            if image.width < 1800 or image.height < 650:
                raise RuntimeError(f"figure is unexpectedly small: {rel(path)}")
    return result


def compute_closure_checks(accumulators: dict[str, GeometryAccumulator]) -> dict[str, bool]:
    categories = ("neither", "pair_only", "annihilation_only", "pair_and_annihilation")
    line_closure = True
    pair_all_windows_closure = True
    driver_denominator_closure = True
    driver_selected_closure = True
    full_histogram_with_overflow_closure = True
    veto_monotonicity = True
    for geometry in GEOMETRIES:
        acc = accumulators[geometry]
        for selection in SELECTIONS:
            line_sum = sum(
                int(acc.histogram_counts[(selection, "line_480_550", index)])
                for index in range(len(LINE_EDGES) - 1)
            )
            line_closure &= line_sum == int(acc.cut_counts[(selection, "broad_480_550")])
            full_sum = (
                sum(
                    int(acc.histogram_counts[(selection, "full_log", index)])
                    for index in range(len(FULL_LOG_EDGES) - 1)
                )
                + int(acc.histogram_underflow[(selection, "full_log")])
                + int(acc.histogram_overflow[(selection, "full_log")])
            )
            full_histogram_with_overflow_closure &= full_sum == int(
                acc.cut_counts[(selection, "tes_positive")]
            )
            for window in WINDOWS:
                pair_all_windows_closure &= sum(
                    int(acc.pair_counts[(selection, window, category)]) for category in categories
                ) == int(acc.cut_counts[(selection, window)])
        for window in WINDOWS:
            counts = [int(acc.cut_counts[(selection, window)]) for selection in SELECTIONS]
            veto_monotonicity &= counts[1] <= counts[2] <= counts[3] <= counts[0]
        for dimension, size, denominator in (
            ("initial_energy", len(ENERGY_LABELS), acc.primary_energy_denominator),
            ("theta", len(THETA_EDGES) - 1, acc.theta_denominator),
        ):
            driver_denominator_closure &= sum(int(denominator[index]) for index in range(size)) == acc.primary_count
            for selection in SELECTIONS:
                for window in WINDOWS:
                    driver_selected_closure &= sum(
                        int(acc.driver_counts[(dimension, index, selection, window)])
                        for index in range(size)
                    ) == int(acc.cut_counts[(selection, window)])
    return {
        "line_480_550_histogram_count_closure": bool(line_closure),
        "pair_category_all_three_windows_count_closure": bool(pair_all_windows_closure),
        "driver_primary_denominator_count_closure": bool(driver_denominator_closure),
        "driver_selected_all_three_windows_count_closure": bool(driver_selected_closure),
        "full_histogram_including_underflow_overflow_count_closure": bool(
            full_histogram_with_overflow_closure
        ),
        "veto_threshold_monotonicity": bool(veto_monotonicity),
    }


def _all_boolean_leaves_true(payload: Any) -> bool:
    if isinstance(payload, bool):
        return payload
    if isinstance(payload, dict):
        return all(_all_boolean_leaves_true(value) for value in payload.values())
    if isinstance(payload, (list, tuple)):
        return all(_all_boolean_leaves_true(value) for value in payload)
    return True


def _run_analysis_in_directory(
    jobs_by_geometry: dict[str, list[JobInput]],
    inventory: list[dict[str, Any]],
    ledger_digests: dict[str, str],
    output_dir: Path,
    published_output_dir: Path,
    *,
    profile: AuthorityProfile,
    make_figures: bool = True,
) -> dict[str, Any]:
    detector_maps = validate_detector_map_contracts()
    if not output_dir.is_dir() or any(output_dir.iterdir()):
        raise RuntimeError("transaction work directory must exist and be empty")
    event_path = output_dir / profile_output_name(profile, "event_diagnostics.csv.gz")
    event_temporary = event_path.with_name(f".{event_path.name}.tmp-{os.getpid()}")
    accumulators = {geometry: GeometryAccumulator(geometry) for geometry in GEOMETRIES}
    inventory_lookup = {
        (row["geometry"], row["batch_id"], row["job_name"]): row for row in inventory
    }
    try:
        with gzip.open(event_temporary, "wt", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=EVENT_FIELDS)
            writer.writeheader()
            for geometry in GEOMETRIES:
                acc = accumulators[geometry]
                for job in jobs_by_geometry[geometry]:
                    observed_digest = parse_job(job, acc, writer)
                    inventory_lookup[(geometry, job.batch_id, job.job_name)]["observed_sim_sha256"] = observed_digest
                    acc.sum_tt_s = math.fsum((acc.sum_tt_s, job.sum_tt_s))
        os.replace(event_temporary, event_path)
    finally:
        if event_temporary.exists():
            event_temporary.unlink()

    for geometry in GEOMETRIES:
        expected = sum(job.events for job in jobs_by_geometry[geometry])
        if accumulators[geometry].primary_count != expected:
            raise RuntimeError(
                f"{geometry}: parsed primary count {accumulators[geometry].primary_count}, expected {expected}"
            )
        if not accumulators[geometry].sum_tt_s > 0.0:
            raise RuntimeError(f"{geometry}: non-positive sum(TT)")

    cutflow_rows = build_cutflow_rows(accumulators)
    histogram_rows = build_histogram_rows(accumulators)
    driver_rows = build_driver_rows(accumulators)
    pair_rows = build_pair_rows(accumulators)
    input_manifest = output_dir / profile_output_name(profile, "input_manifest.csv")
    cutflow_csv = output_dir / profile_output_name(profile, "cutflow.csv")
    histogram_csv = output_dir / profile_output_name(profile, "tes_histograms.csv")
    driver_csv = output_dir / profile_output_name(profile, "primary_drivers.csv")
    pair_csv = output_dir / profile_output_name(profile, "pair_annihilation.csv")
    atomic_csv(input_manifest, inventory)
    atomic_csv(cutflow_csv, cutflow_rows)
    atomic_csv(histogram_csv, histogram_rows)
    atomic_csv(driver_csv, driver_rows)
    atomic_csv(pair_csv, pair_rows)

    figure_paths: list[Path] = []
    if make_figures:
        for stem, function, rows in (
            (profile_output_name(profile, "tes_spectra"), _plot_spectra, histogram_rows),
            (profile_output_name(profile, "veto_cutflow"), _plot_cutflow, cutflow_rows),
            (profile_output_name(profile, "primary_drivers"), _plot_drivers, driver_rows),
        ):
            png = output_dir / f"{stem}.png"
            svg = output_dir / f"{stem}.svg"
            function(rows, png, svg, profile.display_title)
            figure_paths.extend((png, svg))
    figure_qa = (
        _figure_qa(figure_paths, work_dir=output_dir, published_dir=published_output_dir)
        if make_figures
        else {}
    )
    closure_checks = compute_closure_checks(accumulators)

    summary_path = output_dir / profile_output_name(profile, "prompt_tes_summary.json")
    published_summary_path = published_output_dir / summary_path.name
    outputs = [event_path, input_manifest, cutflow_csv, histogram_csv, driver_csv, pair_csv, *figure_paths]
    summary = {
        "schema_version": 1,
        "status": profile.pass_status,
        "authority_profile": {
            "key": profile.key,
            "display_title": profile.display_title,
            "prior_events_per_geometry": profile.prior_events_per_geometry,
            "new_events_per_geometry": profile.new_events_per_geometry,
            "cumulative_events_per_geometry": profile.cumulative_events_per_geometry,
            "prefix_end_ordinal": profile.prefix_end_ordinal,
            "full_checkpoint_authority": profile.full_checkpoint_authority,
            "diagnostic_nonfull": not profile.full_checkpoint_authority,
        },
        "authority_boundary": (
            (
                "PROMPT_GAMMA_STAGE5M_TES_AND_TRUE_ACTIVE_VETO_STATISTICS_ONLY__"
                if profile.full_checkpoint_authority
                else "PROMPT_GAMMA_PREFIX76_2P001M_DIAGNOSTIC_NONFULL__"
            )
            + "NOT_ACTIVATION_DELAYED_STEP05_FOV_MISSION_SENSITIVITY_OR_GEOMETRY_PROMOTION_AUTHORITY"
        ),
        "pooling_boundary": "counts and TT are never pooled across geometry, mode, or particle family",
        "source_model": "unit_only_total_gamma; no additional mono-511 source",
        "response": {
            "fwhm_keV_per_pixel": FWHM_KEV,
            "sigma_keV_per_pixel": SIGMA_KEV,
            "post_noise_pixel_threshold_keV": PIXEL_THRESHOLD_KEV,
            "rng": "SHA-256 keyed Box-Muller normal",
            "rng_namespace": RESPONSE_NAMESPACE,
            "rng_key": "geometry,batch_id,seed,job_name,local_event_id,TES_pixel_UID",
            "semantics": "one deterministic response realization; not an MC uncertainty band",
        },
        "windows_keV": {
            "broad_480_550": {"low_inclusive": BROAD_KEV[0], "high_exclusive": BROAD_KEV[1]},
            "w2_510p58_511p42": {"low_inclusive": W2_KEV[0], "high_exclusive": W2_KEV[1]},
        },
        "veto_contracts": {
            "mass_model_511": {
                "kind": "24_exact_physical_CsI_sensitive_volumes",
                "volumes": sorted(MASS_TRUE_CSI_VOLUMES),
                "thresholds_keV": list(VETO_THRESHOLDS_KEV),
                "kapton_included": False,
            },
            "s3d_o8": {
                "kind": "three_exact_physical_BGO_crystals_plus_three_exact_plastic_volumes",
                "bgo_volumes": sorted(O8_TRUE_BGO_VOLUMES),
                "bgo_thresholds_keV": list(VETO_THRESHOLDS_KEV),
                "plastic_volumes": sorted(O8_TRUE_PLASTIC_VOLUMES),
                "plastic_threshold_keV": O8_PLASTIC_THRESHOLD_KEV,
                "kapton_included": False,
            },
        },
        "normalization": {
            "rate": "sum(selected counts) / sum(positive matching ledger TT)",
            "rate_interval": "two-sided exact 95% Garwood Poisson interval divided by sum(TT)",
            "zero_count_extra": "one-sided 95% Poisson upper bound -ln(0.05)/sum(TT)",
            "efficiency_interval": "two-sided 95% Wilson score interval",
        },
        "inputs": {
            "ledgers": [{"path": path, "sha256": digest} for path, digest in sorted(ledger_digests.items())],
            "detector_maps": detector_maps,
            "input_manifest": _published_rel(input_manifest, output_dir, published_output_dir),
            "input_manifest_sha256": sha256(input_manifest),
            "analyzer": rel(THIS_FILE),
            "analyzer_sha256": sha256(THIS_FILE),
        },
        "geometries": {
            geometry: {
                "primary_count": accumulators[geometry].primary_count,
                "sum_TT_s": accumulators[geometry].sum_tt_s,
                "job_count": len(jobs_by_geometry[geometry]),
                "raw_TES_positive_events": accumulators[geometry].raw_tes_positive,
                "measured_TES_positive_events": accumulators[geometry].measured_tes_positive,
                "TES_events_with_excluded_Kapton_deposit": accumulators[geometry].kapton_positive_tes_events,
                "cutflow": [row for row in cutflow_rows if row["geometry"] == geometry],
                "pair_annihilation": [row for row in pair_rows if row["geometry"] == geometry],
                "primary_drivers": [row for row in driver_rows if row["geometry"] == geometry],
            }
            for geometry in GEOMETRIES
        },
        "outputs": [
            {
                "path": _published_rel(path, output_dir, published_output_dir),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in outputs
        ],
    }
    atomic_json(summary_path, summary)

    # Rehash every small authority/ancillary input after the full SIM sweep.
    # This prevents a long analysis from publishing against moving metadata.
    ending_ledger_hashes = {path: sha256(resolve_path(path)) for path in ledger_digests}
    ledgers_stable = ending_ledger_hashes == ledger_digests
    ancillary_stable = all(
        sha256(resolve_path(row[path_key])) == row[hash_key]
        for row in inventory
        for path_key, hash_key in (
            ("job_source", "job_source_sha256"),
            ("isotope_dat", "isotope_dat_sha256"),
            ("log", "log_sha256"),
        )
    )
    tt_three_way_stable = all(
        math.isclose(_parse_unique_dat_tt(resolve_path(row["isotope_dat"])), float(row["TT_s"]), rel_tol=0.0, abs_tol=1e-12)
        and math.isclose(_parse_unique_log_tt(resolve_path(row["log"])), float(row["TT_s"]), rel_tol=0.0, abs_tol=1e-12)
        for row in inventory
    )
    geometry_three_way_stable = all(
        _parse_unique_source_geometry(resolve_path(row["job_source"]))
        == resolve_path(row["fixed_geometry_setup"]).resolve()
        == resolve_path(row["ledger_geometry_header"]).resolve()
        for row in inventory
    )
    validation_path = output_dir / profile_output_name(profile, "postprocess_validation.json")
    published_validation_path = published_output_dir / validation_path.name
    all_outputs = [*outputs, summary_path]
    output_records = [
        {
            "path": _published_rel(path, output_dir, published_output_dir),
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in all_outputs
    ]
    strict_summary_json = _load_json(summary_path) == summary
    svg_theta_label = (
        not make_figures
        or "Source-side polar angle acos(-IA dir_z) (deg)"
        in (output_dir / f"{profile_output_name(profile, 'primary_drivers')}.svg").read_text(
            encoding="utf-8"
        )
    )
    response_probe = keyed_standard_normal("probe", 1)
    checks: dict[str, Any] = {
        "geometry_separation": list(accumulators) == list(GEOMETRIES),
        "all_primary_counts_match_ledger": all(
            accumulators[geometry].primary_count == sum(job.events for job in jobs_by_geometry[geometry])
            for geometry in GEOMETRIES
        ),
        "all_primary_counts_match_selected_profile_cumulative": all(
            accumulators[geometry].primary_count == profile.cumulative_events_per_geometry
            for geometry in GEOMETRIES
        ),
        "all_sum_TT_positive": all(accumulators[geometry].sum_tt_s > 0.0 for geometry in GEOMETRIES),
        "all_sim_hashes_match_ledgers": all(
            row["observed_sim_sha256"] == row["ledger_sim_sha256"] for row in inventory
        ),
        "input_ledgers_stable": ledgers_stable,
        "ancillary_input_hashes_stable": ancillary_stable,
        "dat_log_ledger_TT_three_way_match": tt_three_way_stable,
        "ledger_job_source_fixed_geometry_three_way_match": geometry_three_way_stable,
        "job_identity_unique": len(inventory)
        == len({(row["geometry"], row["batch_id"], row["job_name"]) for row in inventory}),
        **closure_checks,
        "kapton_excluded_from_veto": not any(
            "KAPTON" in value.upper()
            for value in MASS_TRUE_CSI_VOLUMES | O8_TRUE_BGO_VOLUMES | O8_TRUE_PLASTIC_VOLUMES
        ),
        "response_is_keyed_and_order_invariant": math.isfinite(response_probe)
        and response_probe == keyed_standard_normal("probe", 1),
        "all_output_files_nonempty": all(path.is_file() and path.stat().st_size > 0 for path in all_outputs),
        "all_output_hash_records_close": all(
            sha256(path) == record["sha256"] and path.stat().st_size == record["size_bytes"]
            for path, record in zip(all_outputs, output_records, strict=True)
        ),
        "strict_JSON_summary_no_nonfinite_tokens": strict_summary_json,
        "driver_SVG_uses_source_side_acos_minus_dir_z_label": svg_theta_label,
        "figures_valid": (not make_figures) or len(figure_qa) == 3,
    }
    all_checks_pass = _all_boolean_leaves_true(checks)
    validation = {
        "schema_version": 1,
        "status": "PASS" if all_checks_pass else "FAIL",
        "authority_profile": profile.key,
        "profile_display_title": profile.display_title,
        "cumulative_events_per_geometry": profile.cumulative_events_per_geometry,
        "authority_scope": "full_checkpoint" if profile.full_checkpoint_authority else "diagnostic_nonfull",
        "errors": [] if all_checks_pass else ["one or more validation boolean checks failed"],
        "status_derivation": "PASS iff every boolean leaf in checks is true and errors is empty",
        "checks": checks,
        "figure_qa": figure_qa,
        "summary": rel(published_summary_path),
        "summary_sha256": sha256(summary_path),
        "outputs": output_records,
    }
    atomic_json(validation_path, validation)
    if _load_json(validation_path) != validation:
        raise RuntimeError("strict JSON validation round-trip failed")
    if not all_checks_pass or validation["status"] != "PASS" or validation["errors"]:
        raise RuntimeError("analysis validation failed; canonical output will not be published")
    if {path: sha256(resolve_path(path)) for path in ledger_digests} != ledger_digests:
        raise RuntimeError("one or more input ledgers changed before directory publication")
    return {
        "summary": summary,
        "validation": validation,
        "validation_path": published_validation_path,
    }


def run_analysis(
    jobs_by_geometry: dict[str, list[JobInput]],
    inventory: list[dict[str, Any]],
    ledger_digests: dict[str, str],
    output_dir: Path,
    *,
    profile: AuthorityProfile = STAGE5_PROFILE,
    make_figures: bool = True,
    protect_existing: bool = True,
) -> dict[str, Any]:
    """Build in a sibling directory and atomically publish only a closed PASS."""

    published_output_dir = output_dir.resolve()
    parent = published_output_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    if published_output_dir.exists():
        raise RuntimeError(f"refusing to overwrite existing analysis directory {rel(published_output_dir)}")
    work_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{published_output_dir.name}.tmp-{os.getpid()}-",
            dir=parent,
        )
    )
    try:
        result = _run_analysis_in_directory(
            jobs_by_geometry,
            inventory,
            ledger_digests,
            work_dir,
            published_output_dir,
            profile=profile,
            make_figures=make_figures,
        )
        if published_output_dir.exists():
            raise RuntimeError(f"publication target appeared during analysis: {rel(published_output_dir)}")
        os.rename(work_dir, published_output_dir)
        return result
    except BaseException:
        if work_dir.exists():
            shutil.rmtree(work_dir)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=tuple(AUTHORITY_PROFILES), help="explicit pinned authority profile")
    parser.add_argument("--output-dir", type=Path)
    pin_group = parser.add_mutually_exclusive_group()
    pin_group.add_argument(
        "--pin-stage5-authority",
        action="store_true",
        help="write-once bind the already-published fixed-path stage-5M PASS ledger/validation SHA pair",
    )
    pin_group.add_argument(
        "--pin-prefix76",
        action="store_true",
        help="write-once bind the fixed ordinal-76 2.001M committed-prefix PASS report/ledger pair",
    )
    parser.add_argument(
        "--check-inputs-only",
        action="store_true",
        help="validate canonical PASS ledger metadata and ancillary hashes without reading SIM payloads",
    )
    args = parser.parse_args(argv)
    if args.pin_stage5_authority or args.pin_prefix76:
        if args.check_inputs_only or args.profile is not None or args.output_dir is not None:
            parser.error("pin mode is mutually exclusive with --profile, --output-dir, and --check-inputs-only")
        profile = STAGE5_PROFILE if args.pin_stage5_authority else PREFIX76_PROFILE
        try:
            payload = write_authority_pin(profile)
        except RuntimeError as exc:
            print(
                json.dumps(
                    {
                        "status": "FAIL",
                        "authority_profile": profile.key,
                        "authority_written": False,
                        "errors": [str(exc)],
                    },
                    indent=2,
                    ensure_ascii=False,
                    allow_nan=False,
                )
            )
            return 1
        print(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    if args.profile is None:
        parser.error("--profile is required for input checking and analysis")
    profile = AUTHORITY_PROFILES[args.profile]
    jobs, inventory, digests = collect_canonical_jobs(profile)
    if args.check_inputs_only:
        print(
            json.dumps(
                {
                    "status": f"PASS__CANONICAL_{profile.key.upper()}_INPUT_METADATA_READY",
                    "authority_profile": profile.key,
                    "profile_display_title": profile.display_title,
                    "authority_scope": (
                        "full_checkpoint" if profile.full_checkpoint_authority else "diagnostic_nonfull"
                    ),
                    "expected_events_per_geometry": profile.cumulative_events_per_geometry,
                    "jobs_per_geometry": {geometry: len(rows) for geometry, rows in jobs.items()},
                    "events_per_geometry": {
                        geometry: sum(job.events for job in rows) for geometry, rows in jobs.items()
                    },
                    "ledger_sha256": digests,
                    "sim_payloads_read": False,
                },
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
            )
        )
        return 0
    requested_output = args.output_dir or (ANALYSIS_DIR / f"results_{profile.output_stem}")
    output_dir = requested_output if requested_output.is_absolute() else ROOT / requested_output
    result = run_analysis(
        jobs,
        inventory,
        digests,
        output_dir,
        profile=profile,
        make_figures=True,
        protect_existing=True,
    )
    print(
        json.dumps(
            {
                "status": result["validation"]["status"],
                "analysis_status": result["summary"]["status"],
                "authority_profile": profile.key,
                "profile_display_title": profile.display_title,
                "summary": result["validation"]["summary"],
                "validation": rel(result["validation_path"]),
                "geometries": {
                    geometry: {
                        "primaries": result["summary"]["geometries"][geometry]["primary_count"],
                        "sum_TT_s": result["summary"]["geometries"][geometry]["sum_TT_s"],
                        "measured_TES_positive_events": result["summary"]["geometries"][geometry][
                            "measured_TES_positive_events"
                        ],
                    }
                    for geometry in GEOMETRIES
                },
            },
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
