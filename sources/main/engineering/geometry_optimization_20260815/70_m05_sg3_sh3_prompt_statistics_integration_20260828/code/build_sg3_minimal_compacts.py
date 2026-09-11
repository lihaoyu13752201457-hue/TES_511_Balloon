#!/usr/bin/env python3
"""Validate and compact the retained SG3 minimal-SD prompt supplement.

The default/``--preflight`` path reads only small authorities, the first SIM
header of each receipt-backed production job, and the bounded fixed-seed
100-event bridge pilot.  It never hashes a SIM and never launches transport.
Full production SIM payloads are streamed only after explicit ``--execute``.

The compact arrays intentionally match package 62 model-A job catalogs.  The
only representation change is the validated minimal-SD bridge: ``HTsim`` kind
2 is mapped to one of all 2,256 exact SG3 TES pixel UIDs/centres, and kind 4 is
mapped to the three plastic plus three BGO active volumes.  Unknown kinds fail
closed.  Physical weights remain deferred to the unified old+new exposure
merge; this builder never adds per-stratum rates.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any, Iterable, Mapping

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = HERE.parents[4]
PACKAGE68 = (
    ROOT
    / "engineering/geometry_optimization_20260815/"
    "68_sg3_minimal_sd_prompt_supplement_20260823"
)
DEFAULT_MANIFEST = PACKAGE / "analysis_manifest.json"
DEFAULT_OUTPUT = PACKAGE / "outputs/sg3_minimal"
P62_PATH = (
    ROOT
    / "engineering/geometry_optimization_20260815/"
    "62_sg3b_mature_poisson_timeline_20260818/code/build_event_catalog.py"
)
PHYSICAL_GEO = PACKAGE68 / "geometry/DEMO2_DR_v3p5_SG3B.geo"
MINIMAL_SETUP = PACKAGE68 / "geometry/DEMO2_DR_v3p5_SG3B_MINIMAL.geo.setup"
INTRO_GEO = PACKAGE68 / "geometry/Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"

EXPECTED_PHYSICAL_GEO_SHA256 = "5f0482e307bf8701204f1d6df1b74396b7105d853dccb885e4df401146f552d9"
EXPECTED_MINIMAL_SETUP_SHA256 = "7e944cfa55cc9fcd6d4e69baca281ca8298647e1ded2adb036bc2470dc283f90"
FORBIDDEN_TASK_ID = "01a02314-a50b-78d2-bb8c-b43ffa350704"
LEGACY_SPECTRUM = "cosima_spectra_dp_2602units"
CORRECTED_SPECTRUM = (
    "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
)

FAMILIES = ("alpha", "eplus", "n", "p")
EXPECTED_RECEIPTS = {"alpha": 7, "eplus": 9, "n": 6, "p": 21}
EXPECTED_COMPLETED_EVENTS = {
    "alpha": 25_148,
    "eplus": 333_933,
    "n": 931_968,
    "p": 355_380,
}
BATCH_ID = "m05new_zero_prompt_minimal_supplement_20260823_v1"
SETUP_STRATUM = "minimal_sd"
PASS_COMPACT = "PASS__COMPACT_JOB_CATALOG"
COMPACT_SCHEMA = "m05_sg3_minimal_compact_job_v1"
JOBS_SCHEMA = "m05_supplement_compact_jobs_v1"
PILOT_GATE_ID = "SG3_FIXEDSEED_EXACT_UID_RESPONSE_GATE_20260828_V1"
PILOT_BATCH_ID = "fixedseed_response_bridge_pilot_20260823"
PILOT_JOB_ID = "m05z_sg3_minimal_fixedseed_alpha_all_100"
PILOT_SEED = 707270754
ZERO_PLACEHOLDER_POLICY_ID = "HTSIM_FIXED5_ZERO_PLACEHOLDER_IGNORE_20260828_V1"
SERIALIZED_ZERO_ENERGY_TOKEN = "0.00000"
ZERO_PLACEHOLDER_FIXTURES: dict[str, dict[str, Any]] = {
    "m05zm_sg3_instant_alpha_shard0005": {
        "event_id": 2014,
        "kind": 2,
        "target": "TP_L2_00147",
        "xyz": (-3.88202, -0.31000, -3.03349),
    },
    "m05zm_sg3_instant_alpha_shard0007": {
        "event_id": 86,
        "kind": 4,
        "target": "BGO_S3D_O8_FullWrap_BottomCap_30mm",
        "xyz": (-23.63305, 14.95666, -5.51490),
    },
}
MEGALIB_SOURCE_ROOT = Path("/home/ubuntu/MEGAlib_Install/megalib-main/src")

SOURCE_GEOMETRY_RE = re.compile(r"^Geometry\s+(\S+)\s*$", re.MULTILINE)
SOURCE_SEED_RE = re.compile(r"^Seed\s+(\d+)\s*$", re.MULTILINE)
SOURCE_RUN_RE = re.compile(r"^Run\s+(\S+)\s*$", re.MULTILINE)
SOURCE_STORE_RE = re.compile(r"^StoreSimulationInfo\s+(\S+)\s*$", re.MULTILINE)
SIM_ID_RE = re.compile(r"^ID\s+(?P<id>\d+)\s+\d+\s*$")
HT_RE = re.compile(
    r"^HTsim (?P<kind>\d+);\s*(?P<x>[0-9.eE+-]+);\s*(?P<y>[0-9.eE+-]+);"
    r"\s*(?P<z>[0-9.eE+-]+);\s*(?P<e>[0-9.eE+-]+);\s*(?P<t>[0-9.eE+-]+)\s*$"
)
LAYER_RE = re.compile(
    r"^TES_L(?P<layer>[0-5])\.Position\s+"
    r"(?P<x>[0-9.eE+-]+)\s+(?P<y>[0-9.eE+-]+)\s+(?P<z>[0-9.eE+-]+)\s*$"
)
PIXEL_RE = re.compile(
    r"^(?P<uid>TP_L(?P<layer>[0-5])_(?P<pixel>\d+))\.Position\s+"
    r"(?P<x>[0-9.eE+-]+)\s+(?P<y>[0-9.eE+-]+)\s+(?P<z>[0-9.eE+-]+)\s*$"
)

SCINT_CENTERS: dict[str, tuple[float, float, float]] = {
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm": (-6.08911, -6.76237, 33.98055),
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm": (-29.80831, 17.80555, -8.23908),
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm": (23.57825, 17.80555, 45.14748),
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm": (-13.19737, 14.21073, 11.59823),
    "BGO_S3D_O8_FullWrap_BottomCap_30mm": (-23.63305, 14.95666, -5.51490),
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm": (16.73710, 14.21073, 41.53270),
}
PLASTIC_VOLUMES = frozenset(tuple(SCINT_CENTERS)[:3])
BGO_VOLUMES = frozenset(tuple(SCINT_CENTERS)[3:])

ARRAY_DTYPES: dict[str, Any] = {
    "event_id": np.int32,
    "source_za": np.int32,
    "plastic_keV": np.float32,
    "bgo_keV": np.float32,
    "measured_total_keV": np.float32,
    "broad_flags": np.uint8,
    "w2_flags": np.uint8,
    "hit_start": np.int32,
    "hit_count": np.uint16,
    "hit_code": np.int32,
    "hit_layer": np.uint8,
    "hit_energy_keV": np.float32,
    "hit_x_cm": np.float32,
    "hit_y_cm": np.float32,
    "hit_z_cm": np.float32,
}

_RUNTIME: tuple[Any, Any, Any, Any, dict[str, Any]] | None = None
_GEOMETRY: dict[str, Any] | None = None


class ClosureError(RuntimeError):
    """An input, bridge, or output contract failed closed."""


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ClosureError(f"cannot read JSON authority {path}: {exc}") from exc


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def sha256_small(path: Path, *, maximum_bytes: int = 64 * 1024 * 1024) -> str:
    if path.name.lower().endswith((".sim", ".sim.gz")):
        raise ClosureError(f"refusing to hash SIM payload: {path}")
    size = path.stat().st_size
    if size > maximum_bytes:
        raise ClosureError(f"small-file hash guard exceeded for {path}: {size}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise ClosureError(f"{label} mismatch: {observed!r} != {expected!r}")


def require_close(
    observed: float,
    expected: float,
    label: str,
    *,
    relative: float = 0.0,
    absolute: float = 1e-12,
) -> None:
    if not math.isclose(observed, expected, rel_tol=relative, abs_tol=absolute):
        raise ClosureError(f"{label} mismatch: {observed!r} != {expected!r}")


def indexed(rows: Iterable[Mapping[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for raw in rows:
        row = dict(raw)
        value = str(row.get(key, ""))
        if not value or value in result:
            raise ClosureError(f"{label} has missing/duplicate {key}: {value!r}")
        result[value] = row
    return result


def one_match(pattern: re.Pattern[str], text: str, label: str, path: Path) -> str:
    values = pattern.findall(text)
    if len(values) != 1:
        raise ClosureError(f"{label} must occur exactly once in {path}; found {len(values)}")
    return str(values[0])


def is_below(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def decode_mount_field(value: str) -> str:
    return (
        value.replace("\\040", " ")
        .replace("\\011", "\t")
        .replace("\\012", "\n")
        .replace("\\134", "\\")
    )


def mount_authority(path: Path) -> dict[str, Any]:
    target = path.resolve(strict=True)
    candidates: list[tuple[int, dict[str, Any]]] = []
    for raw in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
        fields = raw.split()
        if "-" not in fields:
            continue
        separator = fields.index("-")
        if separator + 3 >= len(fields):
            continue
        mountpoint = Path(decode_mount_field(fields[4]))
        try:
            resolved = mountpoint.resolve(strict=True)
        except FileNotFoundError:
            continue
        if target == resolved or is_below(target, resolved):
            options = set(fields[5].split(",")) | set(fields[separator + 3].split(","))
            candidates.append(
                (
                    len(str(resolved)),
                    {
                        "mountpoint": str(resolved),
                        "filesystem": fields[separator + 1],
                        "source": fields[separator + 2],
                        "read_only": "ro" in options,
                        "options": sorted(options),
                    },
                )
            )
    if not candidates:
        raise ClosureError(f"cannot resolve mount authority for {target}")
    authority = max(candidates, key=lambda item: item[0])[1]
    require(Path(authority["mountpoint"]), target, "configured external root mountpoint")
    require(authority["read_only"], True, "external mount read-only policy")
    return authority


def map_external(path_text: str, legacy_prefix: Path, mount_root: Path) -> Path:
    if FORBIDDEN_TASK_ID in path_text:
        raise ClosureError("forbidden task path encountered")
    pure = PurePosixPath(path_text)
    try:
        relative = pure.relative_to(PurePosixPath(str(legacy_prefix)))
    except ValueError as exc:
        raise ClosureError(f"external path is outside exact legacy prefix: {path_text}") from exc
    candidate = mount_root.joinpath(*relative.parts).resolve(strict=True)
    if not is_below(candidate, mount_root):
        raise ClosureError(f"mapped path escapes the read-only mount: {path_text}")
    return candidate


def source_authority(path: Path, job_id: str) -> dict[str, Any]:
    if FORBIDDEN_TASK_ID in str(path):
        raise ClosureError("forbidden task source path encountered")
    payload = path.read_bytes()
    text = payload.decode("utf-8", errors="strict")
    if LEGACY_SPECTRUM in text:
        raise ClosureError(f"legacy factor-1000 spectrum in {path}")
    if CORRECTED_SPECTRUM not in text:
        raise ClosureError(f"corrected-keV spectrum token absent from {path}")
    escaped = re.escape(job_id)
    events = int(
        one_match(
            re.compile(rf"^{escaped}\.Events\s+(\d+)\s*$", re.MULTILINE),
            text,
            f"{job_id}.Events",
            path,
        )
    )
    filename = one_match(
        re.compile(rf"^{escaped}\.FileName\s+(\S+)\s*$", re.MULTILINE),
        text,
        f"{job_id}.FileName",
        path,
    )
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "geometry": one_match(SOURCE_GEOMETRY_RE, text, "Geometry", path),
        "seed": int(one_match(SOURCE_SEED_RE, text, "Seed", path)),
        "run": one_match(SOURCE_RUN_RE, text, "Run", path),
        "store_simulation_info": one_match(SOURCE_STORE_RE, text, "StoreSimulationInfo", path),
        "events": events,
        "filename": filename,
    }


def sim_header(path: Path, *, maximum_uncompressed_bytes: int = 1024 * 1024) -> dict[str, Any]:
    geometry: str | None = None
    seed: int | None = None
    consumed = 0
    lines = 0
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            consumed += len(raw.encode("utf-8"))
            lines += 1
            if consumed > maximum_uncompressed_bytes:
                raise ClosureError(f"SIM header guard exceeded for {path}")
            line = raw.strip()
            if line.startswith("Geometry"):
                geometry = line.split(maxsplit=1)[1]
            elif line.startswith("Seed"):
                seed = int(line.split()[1])
            elif SIM_ID_RE.match(line):
                break
    if geometry is None or seed is None:
        raise ClosureError(f"SIM header lacks geometry/seed: {path}")
    return {
        "geometry": geometry,
        "seed": seed,
        "uncompressed_bytes_read": consumed,
        "lines_read": lines,
        "policy": "HEADER_ONLY__NO_SIM_HASH",
    }


def isotope_dat_authority(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="strict")
    tt_values: list[float] = []
    rp_count = 0
    terminal = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        terminal = line
        fields = line.split()
        if fields[0] == "TT":
            if len(fields) != 2:
                raise ClosureError(f"malformed TT record in {path}: {line}")
            tt_values.append(float(fields[1]))
        elif fields[0] == "RP":
            rp_count += 1
    if len(tt_values) != 1 or terminal != "EN" or rp_count != 0:
        raise ClosureError(
            f"prompt isotope DAT closure failed for {path}: TT={tt_values}, RP={rp_count}, terminal={terminal!r}"
        )
    if not math.isfinite(tt_values[0]) or tt_values[0] <= 0.0:
        raise ClosureError(f"nonpositive TT in {path}: {tt_values[0]}")
    return {"TT_s": tt_values[0], "RP_record_count": rp_count, "terminal_EN": True}


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ClosureError(f"cannot import retained P62 code: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def runtime() -> tuple[Any, Any, Any, Any, dict[str, Any]]:
    global _RUNTIME
    if _RUNTIME is None:
        p62 = load_module(f"m05_sg3_minimal_p62_{os.getpid()}", P62_PATH)
        common = p62.common_module()
        parser, core, step05, disk = common.runtime()
        _RUNTIME = p62, common, parser, core, {"step05": step05, "disk": disk}
    return _RUNTIME


def xyz_key(xyz: tuple[float, float, float]) -> tuple[str, str, str]:
    return tuple(f"{value:.5f}" for value in xyz)  # type: ignore[return-value]


def distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(math.fsum((x - y) ** 2 for x, y in zip(a, b, strict=True)))


def geometry_authority() -> dict[str, Any]:
    global _GEOMETRY
    if _GEOMETRY is not None:
        return _GEOMETRY
    require(sha256_small(PHYSICAL_GEO), EXPECTED_PHYSICAL_GEO_SHA256, "physical geometry SHA-256")
    require(sha256_small(MINIMAL_SETUP), EXPECTED_MINIMAL_SETUP_SHA256, "minimal setup SHA-256")
    intro_text = INTRO_GEO.read_text(encoding="utf-8")
    if not re.search(r"^InstrumentFrame\.Position\s+0\s+0\s+0\s*$", intro_text, re.MULTILINE):
        raise ClosureError("InstrumentFrame position is no longer the validated origin")
    if not re.search(r"^InstrumentFrame\.Rotation\s+0\s+45\s+0\s*$", intro_text, re.MULTILINE):
        raise ClosureError("InstrumentFrame rotation is no longer validated 0/45/0")

    layers: dict[int, tuple[float, float, float]] = {}
    local_pixels: dict[str, tuple[int, int, tuple[float, float, float]]] = {}
    for raw in PHYSICAL_GEO.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        match = LAYER_RE.match(line)
        if match:
            layer = int(match.group("layer"))
            layers[layer] = tuple(float(match.group(axis)) for axis in ("x", "y", "z"))
            continue
        match = PIXEL_RE.match(line)
        if match:
            uid = match.group("uid")
            local_pixels[uid] = (
                int(match.group("layer")),
                int(match.group("pixel")),
                tuple(float(match.group(axis)) for axis in ("x", "y", "z")),
            )
    require(len(layers), 6, "TES layer count")
    require(len(local_pixels), 2256, "TES pixel UID count")

    cosine = 1.0 / math.sqrt(2.0)
    centers: dict[str, tuple[float, float, float]] = {}
    codes: dict[str, tuple[int, int]] = {}
    for uid, (layer, pixel, offset) in local_pixels.items():
        local = tuple(a + b for a, b in zip(layers[layer], offset, strict=True))
        centers[uid] = (
            cosine * (local[0] + local[2]),
            local[1],
            cosine * (-local[0] + local[2]),
        )
        codes[uid] = (layer, layer * 100_000 + pixel)
    require(len(set(centers.values())), 2256, "unique exact TES centres")
    center_by_key: dict[tuple[str, str, str], str] = {}
    for uid, center in centers.items():
        key = xyz_key(center)
        if key in center_by_key:
            raise ClosureError(f"five-decimal TES centre collision: {uid} and {center_by_key[key]}")
        center_by_key[key] = uid
    require(len(center_by_key), 2256, "five-decimal TES centre map")
    active_by_key = {xyz_key(center): volume for volume, center in SCINT_CENTERS.items()}
    require(len(active_by_key), 6, "active centre map")
    _GEOMETRY = {
        "centers": centers,
        "codes": codes,
        "center_by_key": center_by_key,
        "active_by_key": active_by_key,
        "physical_geo_sha256": EXPECTED_PHYSICAL_GEO_SHA256,
        "minimal_setup_sha256": EXPECTED_MINIMAL_SETUP_SHA256,
    }
    return _GEOMETRY


def map_tes(
    xyz: tuple[float, float, float], geometry: dict[str, Any]
) -> tuple[str, tuple[float, float, float], float]:
    uid = geometry["center_by_key"].get(xyz_key(xyz))
    if uid is None:
        raise ClosureError(f"HTsim kind2 coordinate is not one of the 2,256 SG3 centres: {xyz}")
    center = geometry["centers"][uid]
    separation = distance(xyz, center)
    if separation > 2.0e-5:
        raise ClosureError(f"HTsim kind2 centre residual exceeds 2e-5 cm: {xyz}, {separation}")
    return uid, center, separation


def map_active(xyz: tuple[float, float, float], geometry: dict[str, Any]) -> tuple[str, float]:
    volume = geometry["active_by_key"].get(xyz_key(xyz))
    if volume is None:
        raise ClosureError(f"HTsim kind4 coordinate is not one of the six active centres: {xyz}")
    separation = distance(xyz, SCINT_CENTERS[volume])
    if separation > 2.0e-4:
        raise ClosureError(f"HTsim kind4 centre residual exceeds 2e-4 cm: {xyz}, {separation}")
    return volume, separation


def decode_htsim_record(
    match: re.Match[str], geometry: dict[str, Any], *, context: str
) -> dict[str, Any]:
    """Decode one HTsim row and classify a narrowly valid serialized zero.

    Unknown kinds and unmapped coordinates fail before zero handling, so a
    zero token can never bypass detector/geometry validation.  Negative,
    non-finite, scientific-zero, shortened-zero, and signed-zero energy tokens
    remain invalid.  The sole accepted placeholder spelling is the fixed-five
    decimal token emitted by this retained SIM format.
    """
    kind = int(match.group("kind"))
    xyz = tuple(float(match.group(axis)) for axis in ("x", "y", "z"))
    energy_token = match.group("e").strip()
    energy = float(energy_token)
    time_value = float(match.group("t"))
    if not all(math.isfinite(value) for value in (*xyz, energy, time_value)):
        raise ClosureError(f"{context}: non-finite HTsim field")
    if kind == 2:
        target, center, separation = map_tes(xyz, geometry)
        target_type = "tes_pixel"
    elif kind == 4:
        target, separation = map_active(xyz, geometry)
        center = SCINT_CENTERS[target]
        target_type = "active_volume"
    else:
        raise ClosureError(f"{context}: unknown HTsim kind {kind}")
    if energy < 0.0:
        raise ClosureError(f"{context}: negative HTsim energy {energy_token}")
    serialized_zero = energy == 0.0
    if serialized_zero and energy_token != SERIALIZED_ZERO_ENERGY_TOKEN:
        raise ClosureError(
            f"{context}: zero HTsim energy has an unapproved serialization {energy_token!r}"
        )
    return {
        "kind": kind,
        "xyz": xyz,
        "center": center,
        "mapping_distance_cm": separation,
        "target": target,
        "target_type": target_type,
        "energy_keV": energy,
        "energy_token": energy_token,
        "time_s": time_value,
        "serialized_zero_placeholder": serialized_zero,
    }


def megalib_zero_semantics_authority() -> dict[str, Any]:
    """Bound the inference that fixed-five ``0.00000`` is a legal no-op row."""
    sources = {
        "writer": MEGALIB_SOURCE_ROOT / "sivan/src/MSimHT.cxx",
        "scintillator_sd": MEGALIB_SOURCE_ROOT / "cosima/src/MCScintillatorSD.cc",
        "voxel_sd": MEGALIB_SOURCE_ROOT / "cosima/src/MCVoxel3DSD.cc",
        "calorbar_sd": MEGALIB_SOURCE_ROOT / "cosima/src/MCCalorBarSD.cc",
        "calibration_bridge": MEGALIB_SOURCE_ROOT / "cosima/src/MCVHit.cc",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in sources.items()}
    for token in (
        "Precision = 5;",
        "S.setf(ios_base::fixed, ios_base::floatfield);",
        "S<<setw(WidthEnergy)<<m_Energy<<\";\";",
    ):
        if token not in texts["writer"]:
            raise ClosureError(f"MEGAlib fixed-five HTsim writer authority changed: {token}")
    for name in ("scintillator_sd", "voxel_sd", "calorbar_sd"):
        if "if (Energy <= 0.0)" not in texts[name] or "return false;" not in texts[name]:
            raise ClosureError(f"MEGAlib positive pre-serialization hit authority changed: {name}")
    if "m_Energy/keV" not in texts["calibration_bridge"] or ", false);" not in texts["calibration_bridge"]:
        raise ClosureError("MEGAlib unnoised calibration bridge authority changed")
    return {
        "status": "PASS__FIXED_FIVE_DECIMAL_SERIALIZATION_AUTHORITY",
        "sources": {
            name: {"path": str(path), "sha256": sha256_small(path)}
            for name, path in sources.items()
        },
        "writer_semantics": (
            "HTsim energy is written in fixed notation with five digits after the decimal "
            "when ScientificPrecision is not positive"
        ),
        "producer_semantics": (
            "retained scintillator and calorimeter sensitive-detector paths reject nonpositive "
            "energy before the unnoised MCVHit-to-MSimHT conversion"
        ),
        "inference": (
            "a serialized 0.00000 at a valid kind/centre is exact zero or a positive deposit "
            "rounded below half a 1e-5-keV output quantum; adding or omitting the serialized "
            "value changes every reconstructed sum by exactly zero"
        ),
    }


def response_record(
    event_id: int,
    pixels: Mapping[str, Mapping[str, float]],
    plastic_keV: float,
    bgo_keV: float,
    job: Mapping[str, Any],
) -> dict[str, Any]:
    p62, common, _, core, topology = runtime()
    measured_hits: list[Any] = []
    raw_hits: list[dict[str, Any]] = []
    for uid, values in sorted(pixels.items()):
        energy = float(values["e"])
        if energy <= 0.0:
            continue
        match = p62.PIXEL_RE.match(uid)
        if not match:
            raise ClosureError(f"unrecognized TES UID after geometry mapping: {uid}")
        x = float(values["wx"]) / energy
        y = float(values["wy"]) / energy
        z = float(values["wz"]) / energy
        measured = energy + core.SIGMA_KEV * core.keyed_standard_normal(
            "sg3b",
            str(job["mode"]),
            str(job["family"]),
            str(job["batch_id"]),
            int(job["seed"]),
            str(job["job_id"]),
            int(event_id),
            uid,
        )
        raw_hits.append(
            {
                "uid": uid,
                "layer": int(match.group("layer")),
                "energy": energy,
                "x": x,
                "y": y,
                "z": z,
                "measured": measured,
            }
        )
        if measured >= core.PIXEL_THRESHOLD_KEV:
            measured_hits.append(
                SimpleNamespace(
                    e=measured,
                    x=x,
                    y=y,
                    z=z,
                    pixel_uid=uid,
                    layer=int(match.group("layer")),
                )
            )
    measured_total = math.fsum(hit.e for hit in measured_hits)
    broad, w2 = p62.flags_for_event(
        measured_hits,
        measured_total,
        plastic_keV,
        bgo_keV,
        float(job["threshold_keV"]),
        common,
        topology["step05"],
        topology["disk"],
    )
    topology_keep, topology_class = common.topology_keep(
        measured_hits, topology["step05"], topology["disk"]
    )
    return {
        "event_id": event_id,
        "plastic_keV": plastic_keV,
        "bgo_keV": bgo_keV,
        "measured_total_keV": measured_total,
        "broad_flags": broad,
        "w2_flags": w2,
        "raw_hits": raw_hits,
        "measured_hits": measured_hits,
        "topology_keep": topology_keep,
        "topology_class": topology_class,
    }


def empty_pixel(uid: str, energy: float, xyz: tuple[float, float, float]) -> dict[str, float]:
    return {"e": energy, "wx": energy * xyz[0], "wy": energy * xyz[1], "wz": energy * xyz[2]}


def add_pixel(
    pixels: dict[str, dict[str, float]], uid: str, energy: float, xyz: tuple[float, float, float]
) -> None:
    row = pixels.get(uid)
    if row is None:
        pixels[uid] = empty_pixel(uid, energy, xyz)
        return
    row["e"] += energy
    row["wx"] += energy * xyz[0]
    row["wy"] += energy * xyz[1]
    row["wz"] += energy * xyz[2]


def collect_pilot_cc(path: Path, job: Mapping[str, Any]) -> tuple[list[dict[str, Any]], int]:
    _, _, parser, _, _ = runtime()
    records: list[dict[str, Any]] = []
    current_id: int | None = None
    pixels: dict[str, dict[str, float]] = {}
    plastic = 0.0
    bgo = 0.0
    generated = 0

    def flush() -> None:
        nonlocal current_id, pixels, plastic, bgo
        if current_id is None:
            return
        if pixels or plastic > 0.0 or bgo > 0.0:
            records.append(response_record(current_id, pixels, plastic, bgo, job))
        current_id = None
        pixels = {}
        plastic = 0.0
        bgo = 0.0

    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            match = parser.ID_RE.match(line)
            if match:
                if current_id is not None:
                    raise ClosureError("pilot CC: ID before event boundary")
                current_id = int(match.group(1))
                generated += 1
                continue
            if not line.startswith("CC HIT "):
                continue
            if current_id is None:
                raise ClosureError("pilot CC hit outside an event")
            hit = parser.parse_cc_hit(line)
            if hit is None:
                raise ClosureError(f"pilot malformed CC HIT: {line[:200]}")
            volume, energy, x, y, z = hit
            if not math.isfinite(energy) or energy <= 0.0:
                raise ClosureError(f"pilot invalid CC energy: {energy}")
            xyz = (x, y, z)
            if parser.TP_RE.match(volume):
                add_pixel(pixels, volume, energy, xyz)
            elif volume in PLASTIC_VOLUMES:
                plastic += energy
            elif volume in BGO_VOLUMES:
                bgo += energy
    flush()  # The retained pilot's final event has no trailing SE.
    return records, generated


def collect_pilot_htsim(
    path: Path, job: Mapping[str, Any], geometry: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current_id: int | None = None
    pixels: dict[str, dict[str, float]] = {}
    plastic = 0.0
    bgo = 0.0
    generated = 0
    kinds: Counter[int] = Counter()
    max_tes_distance = 0.0
    max_active_distance = 0.0
    bgo_50_80: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal current_id, pixels, plastic, bgo
        if current_id is None:
            return
        if pixels or plastic > 0.0 or bgo > 0.0:
            records.append(response_record(current_id, pixels, plastic, bgo, job))
        current_id = None
        pixels = {}
        plastic = 0.0
        bgo = 0.0

    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            match_id = SIM_ID_RE.match(line)
            if match_id:
                if current_id is not None:
                    raise ClosureError("pilot HTsim: ID before event boundary")
                current_id = int(match_id.group("id"))
                generated += 1
                continue
            if not line.startswith("HTsim"):
                continue
            if current_id is None:
                raise ClosureError("pilot HTsim record outside an event")
            match = HT_RE.match(line)
            if not match:
                raise ClosureError(f"pilot malformed HTsim record: {line[:200]}")
            kind = int(match.group("kind"))
            kinds[kind] += 1
            xyz = tuple(float(match.group(axis)) for axis in ("x", "y", "z"))
            energy = float(match.group("e"))
            if not math.isfinite(energy) or energy <= 0.0:
                raise ClosureError(f"pilot invalid HTsim energy: {energy}")
            if kind == 2:
                uid, center, separation = map_tes(xyz, geometry)
                max_tes_distance = max(max_tes_distance, separation)
                add_pixel(pixels, uid, energy, center)
            elif kind == 4:
                volume, separation = map_active(xyz, geometry)
                max_active_distance = max(max_active_distance, separation)
                if volume in PLASTIC_VOLUMES:
                    plastic += energy
                else:
                    bgo += energy
                    if 50.0 <= energy < 80.0:
                        bgo_50_80.append(
                            {"event_id": current_id, "volume": volume, "energy_keV": energy}
                        )
            else:
                raise ClosureError(f"pilot unknown HTsim kind {kind}")
    flush()  # Mandatory EOF flush.
    return records, {
        "generated": generated,
        "kind_counts": {str(key): value for key, value in sorted(kinds.items())},
        "max_tes_mapping_distance_cm": max_tes_distance,
        "max_active_mapping_distance_cm": max_active_distance,
        "bgo_50_80_keV_records": bgo_50_80,
    }


def scalar_diagnostic(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]], field: str
) -> dict[str, Any]:
    left32 = np.asarray([row[field] for row in baseline], dtype=np.float32)
    right32 = np.asarray([row[field] for row in candidate], dtype=np.float32)
    differences = [
        abs(float(left[field]) - float(right[field]))
        for left, right in zip(baseline, candidate, strict=True)
    ]
    relatives = [
        difference
        / max(abs(float(left[field])), abs(float(right[field])), 1.0e-300)
        for difference, left, right in zip(differences, baseline, candidate, strict=True)
    ]
    return {
        "float32_exact_mismatch_events": int(np.count_nonzero(left32 != right32)),
        "max_abs_diff_double_keV": max(differences, default=0.0),
        "max_relative_diff_double": max(relatives, default=0.0),
        "max_abs_diff_float32_keV": float(
            np.max(np.abs(left32.astype(np.float64) - right32.astype(np.float64)), initial=0.0)
        ),
    }


def fixedseed_exact_gate(
    legacy_prefix: Path, mount_root: Path, threshold_keV: float
) -> dict[str, Any]:
    physics = load_json(PACKAGE68 / "FIXEDSEED_PILOT_PHYSICS_VALIDATION_V2.json")
    bridge = load_json(PACKAGE68 / "FIXEDSEED_HTSIM_BRIDGE_VALIDATION_V2.json")
    require(physics.get("status"), "PASS__ACTIVE_HISTORIES_IDENTICAL", "pilot physics status")
    require(physics.get("events_compared"), 100, "pilot physics event count")
    require(physics["baseline_vs_minimal_all"].get("pass"), True, "pilot baseline/all pass")
    require(physics["minimal_all_vs_initonly"].get("pass"), True, "pilot all/init-only pass")
    require(bridge.get("status"), "PASS__HTSIM_RECONSTRUCTS_ACTIVE_CC_HITS", "pilot bridge status")
    require(bridge.get("mismatch_count"), 0, "pilot bridge mismatch count")

    pilot_root = (
        PurePosixPath("/mnt/data/TES_Balloon_511_data/SG3/")
        / "m05new_minimal_sd_alpha_fixedseed_pilot_20260823_v1"
    )
    all_sim = map_external(
        str(
            pilot_root
            / "m05z_sg3_minimal_fixedseed_alpha_all_100/pass/"
            "m05z_sg3_minimal_fixedseed_alpha_all_100.inc1.id1.sim.gz"
        ),
        legacy_prefix,
        mount_root,
    )
    init_sim = map_external(
        str(
            pilot_root
            / "m05z_sg3_minimal_fixedseed_alpha_initonly_100/pass/"
            "m05z_sg3_minimal_fixedseed_alpha_initonly_100.inc1.id1.sim.gz"
        ),
        legacy_prefix,
        mount_root,
    )
    require(all_sim.stat().st_size, 77_492_233, "pilot all SIM size")
    require(init_sim.stat().st_size, 7_990, "pilot init-only SIM size")
    for label, path in (("all", all_sim), ("init-only", init_sim)):
        header = sim_header(path)
        require(Path(header["geometry"]).resolve(strict=True), MINIMAL_SETUP.resolve(), f"pilot {label} geometry")
        require(header["seed"], PILOT_SEED, f"pilot {label} seed")

    geometry = geometry_authority()
    pilot_job = {
        "mode": "instant",
        "family": "alpha",
        "batch_id": PILOT_BATCH_ID,
        "seed": PILOT_SEED,
        "job_id": PILOT_JOB_ID,
        "threshold_keV": threshold_keV,
    }
    baseline, generated_cc = collect_pilot_cc(all_sim, pilot_job)
    candidate, candidate_diagnostic = collect_pilot_htsim(init_sim, pilot_job, geometry)
    require(generated_cc, 100, "pilot CC generated events")
    require(candidate_diagnostic["generated"], 100, "pilot HTsim generated events")
    baseline_ids = [row["event_id"] for row in baseline]
    candidate_ids = [row["event_id"] for row in candidate]
    require(baseline_ids, candidate_ids, "pilot detector-positive event IDs")
    require(len(baseline), 49, "pilot detector-positive event count")
    require(candidate_diagnostic["kind_counts"], {"2": 22, "4": 189}, "pilot raw HTsim kinds")

    uid_mismatch_events: list[int] = []
    energy_mismatch_pairs = 0
    threshold_uid_mismatch_events: list[int] = []
    response_bit_mismatches: dict[str, dict[str, list[int]]] = {
        "broad_flags": {},
        "w2_flags": {},
    }
    topology_mismatch_events: list[int] = []
    p62, _, _, _, _ = runtime()
    for left, right in zip(baseline, candidate, strict=True):
        left_hits = {row["uid"]: row for row in left["raw_hits"]}
        right_hits = {row["uid"]: row for row in right["raw_hits"]}
        if set(left_hits) != set(right_hits):
            uid_mismatch_events.append(int(left["event_id"]))
        else:
            for uid in left_hits:
                if not math.isclose(
                    float(left_hits[uid]["energy"]),
                    float(right_hits[uid]["energy"]),
                    rel_tol=2.0e-5,
                    abs_tol=2.0e-3,
                ):
                    energy_mismatch_pairs += 1
        left_measured = {hit.pixel_uid for hit in left["measured_hits"]}
        right_measured = {hit.pixel_uid for hit in right["measured_hits"]}
        if left_measured != right_measured:
            threshold_uid_mismatch_events.append(int(left["event_id"]))
        for field in ("plastic_keV", "bgo_keV"):
            if not math.isclose(
                float(left[field]), float(right[field]), rel_tol=2.0e-5, abs_tol=2.0e-3
            ):
                raise ClosureError(f"pilot {field} mismatch at event {left['event_id']}")
        for field in ("broad_flags", "w2_flags"):
            for stage, bit in p62.STAGE_BITS.items():
                if bool(int(left[field]) & bit) != bool(int(right[field]) & bit):
                    response_bit_mismatches[field].setdefault(stage, []).append(
                        int(left["event_id"])
                    )
        if (
            left["topology_keep"] != right["topology_keep"]
            or left["topology_class"] != right["topology_class"]
        ):
            topology_mismatch_events.append(int(left["event_id"]))

    if uid_mismatch_events or energy_mismatch_pairs or threshold_uid_mismatch_events:
        raise ClosureError(
            "pilot TES reconstruction differs: "
            f"UID={uid_mismatch_events}, energy_pairs={energy_mismatch_pairs}, "
            f"threshold_UID={threshold_uid_mismatch_events}"
        )
    nonempty_response_mismatches = {
        field: stages for field, stages in response_bit_mismatches.items() if stages
    }
    if nonempty_response_mismatches or topology_mismatch_events:
        raise ClosureError(
            f"pilot P62 response closure differs: bits={nonempty_response_mismatches}, "
            f"topology={topology_mismatch_events}"
        )

    tes_positive = sum(bool(row["measured_hits"]) for row in baseline)
    multi_hit = sum(len(row["measured_hits"]) >= 2 for row in baseline)
    require(tes_positive, 9, "pilot TES-positive event count")
    require(multi_hit, 5, "pilot multi-hit direct-Step05 event count")
    broad_pre = sum(bool(int(row["broad_flags"]) & p62.STAGE_BITS["pre_veto"]) for row in baseline)
    w2_pre = sum(bool(int(row["w2_flags"]) & p62.STAGE_BITS["pre_veto"]) for row in baseline)
    require(broad_pre, 0, "pilot 480--550-keV occupancy")
    require(w2_pre, 0, "pilot W2 occupancy")
    bgo_band = candidate_diagnostic["bgo_50_80_keV_records"]
    require(len(bgo_band), 1, "pilot retained 50--80-keV BGO record count")
    require(bgo_band[0]["event_id"], 48, "pilot 50--80-keV BGO event")
    require_close(bgo_band[0]["energy_keV"], 59.42559, "pilot 50--80-keV BGO energy")

    return {
        "status": "PASS__FIXEDSEED_EXACT_UID_AND_P62_RESPONSE_GATE",
        "gate_id": PILOT_GATE_ID,
        "events_generated_each": 100,
        "detector_positive_events": len(baseline),
        "tes_positive_events": tes_positive,
        "multi_hit_direct_step05_events": multi_hit,
        "raw_htsim_kind_counts": candidate_diagnostic["kind_counts"],
        "pixel_uid_set_mismatch_events": 0,
        "pixel_energy_mismatch_pairs_at_bridge_tolerance": 0,
        "post_smear_threshold_uid_mismatch_events": 0,
        "broad_five_stage_bit_mismatch_events": 0,
        "w2_five_stage_bit_mismatch_events": 0,
        "direct_step05_keep_or_class_mismatch_events": 0,
        "scalar_rounding": {
            field: scalar_diagnostic(baseline, candidate, field)
            for field in ("plastic_keV", "bgo_keV", "measured_total_keV")
        },
        "max_tes_mapping_distance_cm": candidate_diagnostic["max_tes_mapping_distance_cm"],
        "max_active_mapping_distance_cm": candidate_diagnostic["max_active_mapping_distance_cm"],
        "bgo_50_80_keV_retention": bgo_band,
        "limitation": (
            "The 100-event alpha pilot contains zero 480--550-keV and zero W2 events. "
            "Therefore the in-window Compton-bit closure is an empty-window check; the "
            "non-empty topology evidence is the direct Step05 closure on five multi-hit events."
        ),
        "claim_boundary": "representation bridge only; not a 511-keV-window statistics validation",
        "sim_hashes_computed": 0,
        "transport_started": False,
    }


def bounded_zero_placeholder_gate(jobs: list[dict[str, Any]]) -> dict[str, Any]:
    """Reproduce the two known fixed-five zero rows from exact PASS receipts."""
    geometry = geometry_authority()
    by_job = {str(job["job_id"]): job for job in jobs}
    require(set(ZERO_PLACEHOLDER_FIXTURES).issubset(by_job), True, "zero fixture job membership")
    fixture_audits: list[dict[str, Any]] = []
    total_bytes = 0
    for job_id, expected in ZERO_PLACEHOLDER_FIXTURES.items():
        job = by_job[job_id]
        total_bytes += int(job["sim_bytes"])
        current_id: int | None = None
        htsim_records = 0
        kind_counts: Counter[int] = Counter()
        positive_by_event: Counter[int] = Counter()
        placeholders: list[dict[str, Any]] = []
        with gzip.open(job["sim_path"], "rt", encoding="utf-8", errors="strict") as handle:
            for raw in handle:
                line = raw.strip()
                match_id = SIM_ID_RE.match(line)
                if match_id:
                    current_id = int(match_id.group("id"))
                    continue
                if line == "SE":
                    current_id = None
                    continue
                if not line.startswith("HTsim"):
                    continue
                if current_id is None:
                    raise ClosureError(f"{job_id}: bounded zero gate found HTsim outside an event")
                match = HT_RE.match(line)
                if not match:
                    raise ClosureError(f"{job_id}: bounded zero gate malformed HTsim: {line[:200]}")
                decoded = decode_htsim_record(
                    match, geometry, context=f"{job_id} event {current_id} bounded-zero gate"
                )
                htsim_records += 1
                kind_counts[int(decoded["kind"])] += 1
                if decoded["serialized_zero_placeholder"]:
                    placeholders.append(
                        {
                            "event_id": current_id,
                            "kind": int(decoded["kind"]),
                            "target": decoded["target"],
                            "target_type": decoded["target_type"],
                            "xyz": list(decoded["xyz"]),
                            "energy_token": decoded["energy_token"],
                            "energy_keV": 0.0,
                            "time_s": decoded["time_s"],
                            "mapping_distance_cm": decoded["mapping_distance_cm"],
                        }
                    )
                else:
                    positive_by_event[current_id] += 1
        require(len(placeholders), 1, f"{job_id} serialized-zero placeholder count")
        placeholder = placeholders[0]
        require(placeholder["event_id"], expected["event_id"], f"{job_id} zero event")
        require(placeholder["kind"], expected["kind"], f"{job_id} zero kind")
        require(placeholder["target"], expected["target"], f"{job_id} zero mapped target")
        require(tuple(placeholder["xyz"]), expected["xyz"], f"{job_id} zero coordinate")
        require(
            placeholder["energy_token"],
            SERIALIZED_ZERO_ENERGY_TOKEN,
            f"{job_id} fixed-five zero token",
        )
        other_positive = int(positive_by_event[placeholder["event_id"]])
        if other_positive <= 0:
            raise ClosureError(f"{job_id}: zero fixture event lacks independent positive HTsim records")
        placeholder["other_positive_htsim_records_in_event"] = other_positive
        fixture_audits.append(
            {
                "job_id": job_id,
                "receipt_path": job["receipt_path"],
                "sim_path": job["sim_path"],
                "sim_bytes": int(job["sim_bytes"]),
                "htsim_records": htsim_records,
                "kind_counts": {str(key): value for key, value in sorted(kind_counts.items())},
                "serialized_zero_placeholders": placeholders,
                "negative_or_nonfinite_energy_records": 0,
            }
        )
    return {
        "status": "PASS__BOUNDED_FIXED5_ZERO_PLACEHOLDER_GATE",
        "policy_id": ZERO_PLACEHOLDER_POLICY_ID,
        "accepted_zero_token": SERIALIZED_ZERO_ENERGY_TOKEN,
        "fixture_jobs": fixture_audits,
        "fixture_job_count": len(fixture_audits),
        "fixture_sim_bytes_streamed": total_bytes,
        "serialized_zero_placeholder_records": len(fixture_audits),
        "expected_records": [
            {
                "job_id": item["job_id"],
                **item["serialized_zero_placeholders"][0],
            }
            for item in fixture_audits
        ],
        "semantics_authority": megalib_zero_semantics_authority(),
        "parser_policy": (
            "validate kind and mapped centre first; count and ignore only exact fixed-five 0.00000; "
            "all unknown kinds, unmapped centres, non-finite values, negative energies, and other "
            "zero spellings fail closed"
        ),
        "response_impact": (
            "ignored serialized energy is exactly 0.0 keV, so TES, plastic, BGO, measured-total, "
            "veto, and Step05 inputs are unchanged"
        ),
    }


def base_overlap_audit(manifest: Mapping[str, Any], jobs: list[dict[str, Any]]) -> dict[str, Any]:
    base_ids: set[str] = set()
    base_seeds: set[int] = set()
    authorities: list[dict[str, Any]] = []
    for source in manifest["models"]["sg3"]["base_lineage"]:
        path = (ROOT / str(source["path"])).resolve(strict=True)
        if FORBIDDEN_TASK_ID in str(path):
            raise ClosureError("forbidden task entered base lineage")
        payload = load_json(path)
        rows = payload.get(source["jobs_key"], [])
        if not isinstance(rows, list):
            raise ClosureError(f"base lineage job rows are not a list: {path}")
        for row in rows:
            base_ids.add(str(row["job_id"]))
            base_seeds.add(int(row[source["seed_key"]]))
        authorities.append(
            {
                "path": str(path),
                "sha256": sha256_small(path),
                "rows": len(rows),
                "jobs_key": source["jobs_key"],
                "seed_key": source["seed_key"],
            }
        )
    new_ids = {str(job["job_id"]) for job in jobs}
    new_seeds = {int(job["seed"]) for job in jobs}
    duplicate_ids = sorted(new_ids & base_ids)
    duplicate_seeds = sorted(new_seeds & base_seeds)
    if duplicate_ids or duplicate_seeds:
        raise ClosureError(
            f"minimal supplement overlaps retained P67/P63 lineage: jobs={duplicate_ids}, seeds={duplicate_seeds}"
        )
    return {
        "status": "PASS__NO_BASE_JOB_OR_SEED_OVERLAP",
        "authorities": authorities,
        "base_unique_job_ids": len(base_ids),
        "base_unique_seeds": len(base_seeds),
        "duplicate_job_ids": duplicate_ids,
        "duplicate_seeds": duplicate_seeds,
    }


def validate_receipt(
    receipt_path: Path,
    family: str,
    plan: Mapping[str, Any],
    source_row: Mapping[str, Any],
    seed_row: Mapping[str, Any],
    legacy_prefix: Path,
    mount_root: Path,
    source_root: Path,
    threshold_keV: float,
) -> dict[str, Any]:
    receipt = load_json(receipt_path)
    job_id = str(receipt.get("job_id", ""))
    context = f"{family}/{job_id or receipt_path.name}"
    require(receipt_path.stem, job_id, f"{context} receipt filename")
    require(receipt.get("status"), "PASS", f"{context} receipt status")
    require(int(receipt.get("returncode", -1)), 0, f"{context} return code")
    require(receipt.get("errors"), [], f"{context} receipt errors")
    require(receipt.get("watchdog_reason"), "completed", f"{context} watchdog")
    require(receipt.get("candidate"), "SG3B_MINIMAL_SD", f"{context} candidate")
    require(receipt.get("family"), family, f"{context} family")
    require(receipt.get("mode"), "instant", f"{context} mode")
    for field in ("job_id", "family", "candidate", "mode", "seed", "events", "setup_path", "source_path"):
        require(receipt.get(field), plan.get(field), f"{context} receipt/job-plan {field}")
    for field in ("job_id", "family", "mode", "seed", "events", "setup_path", "source_path"):
        require(receipt.get(field), source_row.get(field), f"{context} receipt/source-manifest {field}")
    require(source_row.get("store_simulation_info"), "init-only", f"{context} manifest store mode")
    require(seed_row.get("job_id"), job_id, f"{context} seed-registry job")
    require(int(seed_row.get("seed", -1)), int(receipt["seed"]), f"{context} seed-registry seed")

    for key in ("source_path", "setup_path", "sim_path", "log_path", "isotope_dat_path"):
        if FORBIDDEN_TASK_ID in str(receipt.get(key, "")):
            raise ClosureError(f"{context} references forbidden task through {key}")
    source = Path(str(receipt["source_path"])).resolve(strict=True)
    if not is_below(source, source_root):
        raise ClosureError(f"{context} source escapes generated/sources: {source}")
    source_info = source_authority(source, job_id)
    require(source_info["sha256"], receipt.get("source_sha256"), f"{context} receipt source SHA")
    require(source_info["sha256"], source_row.get("source_sha256"), f"{context} manifest source SHA")
    require(source_info["run"], job_id, f"{context} source Run")
    require(source_info["store_simulation_info"], "init-only", f"{context} source store mode")
    require(source_info["seed"], int(receipt["seed"]), f"{context} source seed")
    require(source_info["events"], int(receipt["events"]), f"{context} source events")
    require(source_info["filename"], plan.get("output_prefix"), f"{context} source output prefix")

    setup = Path(str(receipt["setup_path"])).resolve(strict=True)
    require(setup, MINIMAL_SETUP.resolve(strict=True), f"{context} setup path")
    require(sha256_small(setup), EXPECTED_MINIMAL_SETUP_SHA256, f"{context} setup SHA")
    require(Path(source_info["geometry"]).resolve(strict=True), setup, f"{context} source geometry")

    sim = map_external(str(receipt["sim_path"]), legacy_prefix, mount_root)
    log = map_external(str(receipt["log_path"]), legacy_prefix, mount_root)
    isotope = map_external(str(receipt["isotope_dat_path"]), legacy_prefix, mount_root)
    require(sim.stat().st_size, int(receipt["sim_bytes"]), f"{context} SIM size")
    require(log.stat().st_size, int(receipt["log_bytes"]), f"{context} log size")
    require(isotope.stat().st_size, int(receipt["isotope_dat_bytes"]), f"{context} isotope DAT size")
    require(
        int(receipt["sim_bytes"]) + int(receipt["log_bytes"]) + int(receipt["isotope_dat_bytes"]),
        int(receipt["artifact_bytes"]),
        f"{context} artifact byte closure",
    )

    receipt_header = receipt.get("sim_header", {})
    require(Path(str(receipt_header.get("geometry", ""))).resolve(strict=True), setup, f"{context} receipt header geometry")
    require(int(receipt_header.get("seed", -1)), int(receipt["seed"]), f"{context} receipt header seed")
    require(receipt.get("sim_digest_policy"), "OMITTED__PATH_SIZE_AND_HEADER_ONLY", f"{context} digest policy")
    actual_header = sim_header(sim)
    require(Path(actual_header["geometry"]).resolve(strict=True), setup, f"{context} actual header geometry")
    require(actual_header["seed"], int(receipt["seed"]), f"{context} actual header seed")

    log_meta = receipt.get("log", {})
    require(int(log_meta.get("generated_events", -1)), int(receipt["events"]), f"{context} log events")
    require(log_meta.get("error_marker"), False, f"{context} log error marker")
    require(log_meta.get("graphics_terminal_marker"), True, f"{context} log terminal marker")
    dat = isotope_dat_authority(isotope)
    isotope_meta = receipt.get("isotope_dat", {})
    require(isotope_meta.get("terminal_EN"), True, f"{context} receipt terminal EN")
    require(int(isotope_meta.get("RP_record_count", -1)), 0, f"{context} receipt RP count")
    require(isotope_meta.get("errors"), [], f"{context} receipt isotope errors")
    require_close(dat["TT_s"], float(isotope_meta.get("TT_s", -1.0)), f"{context} actual/receipt TT")
    require_close(dat["TT_s"], float(log_meta.get("observation_time_s", -1.0)), f"{context} TT/log time")

    return {
        "stream": "prompt",
        "family": family,
        "mode": "instant",
        "batch_id": BATCH_ID,
        "job_id": job_id,
        "seed": int(receipt["seed"]),
        "events": int(receipt["events"]),
        "sim_path": str(sim),
        "sim_path_receipt": str(receipt["sim_path"]),
        "sim_bytes": int(receipt["sim_bytes"]),
        "source_path": str(source),
        "source_sha256": source_info["sha256"],
        "expected_geometry": str(setup),
        "setup_sha256": EXPECTED_MINIMAL_SETUP_SHA256,
        "setup_stratum": SETUP_STRATUM,
        "weight_cps": 0.0,
        "weight_policy": "DEFERRED__UNIFIED_OLD_PLUS_NEW_EXPOSURE",
        "exposure_TT_s": dat["TT_s"],
        "receipt_path": str(receipt_path),
        "threshold_keV": threshold_keV,
        "plastic_volumes": sorted(PLASTIC_VOLUMES),
        "bgo_volumes": sorted(BGO_VOLUMES),
        "sim_header": actual_header,
    }


def validate_family(
    family: str,
    legacy_prefix: Path,
    mount_root: Path,
    threshold_keV: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bundle = PACKAGE68 / "production_bundles" / family
    generated = bundle / "generated"
    config = load_json(bundle / "config.json")
    plan_payload = load_json(generated / "job_plan.json")
    source_payload = load_json(generated / "source_manifest.json")
    seed_payload = load_json(generated / "seed_registry.json")
    preflight_payload = load_json(generated / "preflight.json")
    run = map_external(str(config["run_root"]), legacy_prefix, mount_root)
    controller = load_json(run / "controller_state.json")
    receipt_paths = sorted((run / "receipts").glob("*.json"))

    require(config.get("candidate"), "SG3B_MINIMAL_SD", f"{family} config candidate")
    require(config.get("source_policy"), "corrected_keV_background__init_only", f"{family} source policy")
    require(config.get("corrected_token"), CORRECTED_SPECTRUM, f"{family} corrected token")
    require(config.get("forbidden_legacy_token"), LEGACY_SPECTRUM, f"{family} forbidden token")
    require(preflight_payload.get("status"), config.get("preflight_pass_status"), f"{family} generated preflight")
    require(plan_payload.get("status"), "PASS", f"{family} job plan status")
    require(source_payload.get("status"), config.get("source_manifest_pass_status"), f"{family} source manifest status")
    require(seed_payload.get("status"), config.get("seed_registry_pass_status"), f"{family} seed registry status")
    require(Path(config["geometry_setup"]).resolve(strict=True), MINIMAL_SETUP.resolve(), f"{family} geometry setup")

    plan = indexed(plan_payload.get("jobs", []), "job_id", f"{family} job plan")
    source_rows = indexed(source_payload.get("sources", []), "job_id", f"{family} source manifest")
    seed_rows = indexed(seed_payload.get("seeds", []), "job_id", f"{family} seed registry")
    require(set(source_rows), set(plan), f"{family} source/plan job IDs")
    require(set(seed_rows), set(plan), f"{family} seed/plan job IDs")
    require(len(plan), int(config["expected_jobs"]), f"{family} planned jobs")
    require(len(receipt_paths), EXPECTED_RECEIPTS[family], f"{family} retained PASS receipts")

    receipt_ids = {path.stem for path in receipt_paths}
    completed = {str(value) for value in controller.get("completed_jobs", [])}
    active = {str(value) for value in controller.get("active", {})}
    pending = {str(value) for value in controller.get("pending_jobs", [])}
    require(int(controller.get("completed_count", -1)), len(completed), f"{family} controller completed count")
    require(completed, receipt_ids, f"{family} controller/receipt membership")
    if not (completed | active | pending).issubset(set(plan)):
        raise ClosureError(f"{family} controller membership escapes job plan")
    if completed & active or completed & pending or active & pending:
        raise ClosureError(f"{family} controller completed/active/pending sets overlap")
    if len(completed) == len(plan):
        require(controller.get("status"), "COMPLETE", f"{family} complete controller status")
        require(active, set(), f"{family} complete active set")
        require(pending, set(), f"{family} complete pending set")
        partial_policy = "COMPLETE"
    else:
        require(family, "n", "only neutron family may be partial")
        if controller.get("status") not in {"RUNNING", "FAILED", "INTERRUPTED"}:
            raise ClosureError(f"partial neutron controller status is not recognized: {controller.get('status')}")
        partial_policy = "PARTIAL_PASS_RECEIPTS_ONLY__ACTIVE_AND_PENDING_EXCLUDED__ACTUAL_TT"

    source_root = (generated / "sources").resolve(strict=True)
    jobs: list[dict[str, Any]] = []
    for path in receipt_paths:
        job_id = path.stem
        if job_id not in plan:
            raise ClosureError(f"{family} receipt absent from job plan: {job_id}")
        jobs.append(
            validate_receipt(
                path,
                family,
                plan[job_id],
                source_rows[job_id],
                seed_rows[job_id],
                legacy_prefix,
                mount_root,
                source_root,
                threshold_keV,
            )
        )
    events = sum(int(job["events"]) for job in jobs)
    require(events, EXPECTED_COMPLETED_EVENTS[family], f"{family} completed event count")
    return jobs, {
        "status": "PASS__ACTUAL_RECEIPT_SUBSET_CLOSED",
        "family": family,
        "controller_status": controller.get("status"),
        "partial_policy": partial_policy,
        "planned_jobs": len(plan),
        "completed_pass_receipts": len(jobs),
        "active_unreceipted_jobs_excluded": sorted(active),
        "pending_unreceipted_jobs_excluded": sorted(pending),
        "events": events,
        "sim_bytes": sum(int(job["sim_bytes"]) for job in jobs),
        "actual_exposure_TT_s": math.fsum(float(job["exposure_TT_s"]) for job in jobs),
        "receipt_directory": str(run / "receipts"),
        "job_plan": str(generated / "job_plan.json"),
        "source_manifest": str(generated / "source_manifest.json"),
        "seed_registry": str(generated / "seed_registry.json"),
    }


def preflight(manifest_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = load_json(manifest_path)
    require(manifest.get("status"), "READY__PREFLIGHT_REQUIRED__NO_TRANSPORT", "integration manifest status")
    require(manifest.get("forbidden_task_id"), FORBIDDEN_TASK_ID, "forbidden task authority")
    if FORBIDDEN_TASK_ID in str(PACKAGE) or FORBIDDEN_TASK_ID in str(PACKAGE68):
        raise ClosureError("forbidden task ID entered a configured package path")
    legacy_prefix = Path(str(manifest["legacy_external_prefix"]))
    mount_root = Path(str(manifest["readonly_external_mount"])).resolve(strict=True)
    mount = mount_authority(mount_root)
    threshold = float(manifest["offline_veto_threshold_keV"])
    require_close(threshold, 50.0, "SG3 offline veto threshold")
    require(sha256_small(P62_PATH), manifest["models"]["sg3"]["parser_sha256"], "retained P62 parser SHA")
    geometry = geometry_authority()
    gate = fixedseed_exact_gate(legacy_prefix, mount_root, threshold)

    jobs: list[dict[str, Any]] = []
    family_audits: dict[str, Any] = {}
    for family in FAMILIES:
        rows, audit = validate_family(family, legacy_prefix, mount_root, threshold)
        jobs.extend(rows)
        family_audits[family] = audit
    for scan_index, job in enumerate(jobs):
        job["scan_index"] = scan_index
    job_ids = [str(job["job_id"]) for job in jobs]
    seeds = [int(job["seed"]) for job in jobs]
    if len(job_ids) != len(set(job_ids)):
        raise ClosureError("duplicate minimal-SD production job IDs")
    if len(seeds) != len(set(seeds)):
        raise ClosureError("duplicate minimal-SD production seeds")
    require(len(jobs), sum(EXPECTED_RECEIPTS.values()), "minimal-SD retained job count")
    require(
        sum(int(job["events"]) for job in jobs),
        sum(EXPECTED_COMPLETED_EVENTS.values()),
        "minimal-SD retained event count",
    )
    zero_placeholder_gate = bounded_zero_placeholder_gate(jobs)
    overlap = base_overlap_audit(manifest, jobs)
    exposure = {
        family: math.fsum(float(job["exposure_TT_s"]) for job in jobs if job["family"] == family)
        for family in FAMILIES
    }
    audit = {
        "schema_version": 1,
        "schema": "m05_sg3_minimal_targeted_preflight_v1",
        "status": "PASS__SG3_MINIMAL_TARGETED_PREFLIGHT",
        "manifest": str(manifest_path),
        "candidate": "SG3B_MINIMAL_SD",
        "setup_stratum": SETUP_STRATUM,
        "mount_authority": mount,
        "geometry": {
            "physical_geo": str(PHYSICAL_GEO),
            "physical_geo_sha256": geometry["physical_geo_sha256"],
            "minimal_setup": str(MINIMAL_SETUP),
            "minimal_setup_sha256": geometry["minimal_setup_sha256"],
            "pixel_uid_centres": len(geometry["centers"]),
            "active_volume_centres": len(SCINT_CENTERS),
        },
        "fixedseed_exact_gate": gate,
        "bounded_zero_placeholder_gate": zero_placeholder_gate,
        "families": family_audits,
        "jobs_count": len(jobs),
        "events": sum(int(job["events"]) for job in jobs),
        "sim_bytes": sum(int(job["sim_bytes"]) for job in jobs),
        "seeds": seeds,
        "exposure_TT_s_by_family": exposure,
        "base_overlap_audit": overlap,
        "normalization_policy": (
            "deferred; each family will receive one common 1/(T_old+sum T_new) weight "
            "across main and minimal_sd setup strata"
        ),
        "authority_boundary": {
            "production_sim_headers_read": len(jobs),
            "production_sim_payloads_streamed_for_compaction": 0,
            "bounded_fixedseed_pilot_payloads_streamed": 2,
            "bounded_zero_placeholder_fixture_payloads_streamed": int(
                zero_placeholder_gate["fixture_job_count"]
            ),
            "bounded_zero_placeholder_fixture_bytes_streamed": int(
                zero_placeholder_gate["fixture_sim_bytes_streamed"]
            ),
            "sim_hashes_computed": 0,
            "cosima_transport_started": False,
            "unreceipted_neutron_partial_read": False,
            "forbidden_task_outputs_read": False,
        },
    }
    return audit, jobs


def expected_cache_paths(output: Path, job: Mapping[str, Any]) -> tuple[Path, Path]:
    stem = f"job_{int(job['scan_index']):03d}_{job['job_id']}"
    npz = output / "job_catalogs" / f"{stem}.npz"
    return npz, npz.with_suffix(".json")


def validate_cached_meta(meta: Mapping[str, Any], job: Mapping[str, Any], npz: Path) -> None:
    require(meta.get("status"), PASS_COMPACT, f"{job['job_id']} cached status")
    require(meta.get("builder_schema"), COMPACT_SCHEMA, f"{job['job_id']} cached builder schema")
    for key in ("job_id", "seed", "events", "sim_bytes", "sim_path", "family", "batch_id"):
        require(meta.get(key), job.get(key), f"{job['job_id']} cached {key}")
    require(meta.get("setup_stratum"), SETUP_STRATUM, f"{job['job_id']} cached setup stratum")
    require_close(
        float(meta.get("exposure_TT_s", math.nan)),
        float(job["exposure_TT_s"]),
        f"{job['job_id']} cached TT",
    )
    if "serialized_zero_energy_placeholder_records" in meta:
        if int(meta["serialized_zero_energy_placeholder_records"]) < 0:
            raise ClosureError(f"{job['job_id']} cached serialized-zero count is negative")
        require(
            meta.get("serialized_zero_energy_placeholder_policy_id"),
            ZERO_PLACEHOLDER_POLICY_ID,
            f"{job['job_id']} cached serialized-zero policy",
        )
    require(Path(str(meta.get("catalog_path", ""))).resolve(strict=True), npz.resolve(strict=True), f"{job['job_id']} catalog path")


def scan_htsim_job(job: dict[str, Any], output_text: str) -> dict[str, Any]:
    output = Path(output_text)
    npz_path, meta_path = expected_cache_paths(output, job)
    if npz_path.exists() != meta_path.exists():
        raise ClosureError(f"partial compact pair requires review: {npz_path}, {meta_path}")
    if npz_path.is_file():
        meta = load_json(meta_path)
        validate_cached_meta(meta, job, npz_path)
        return meta

    geometry = geometry_authority()
    runtime()
    arrays: dict[str, list[Any]] = {key: [] for key in ARRAY_DTYPES}
    current_id: int | None = None
    pixels: dict[str, dict[str, float]] = {}
    plastic = 0.0
    bgo = 0.0
    generated = 0
    header_geometry = ""
    header_seed: int | None = None
    kinds: Counter[int] = Counter()
    positive_kinds: Counter[int] = Counter()
    zero_placeholder_kinds: Counter[int] = Counter()
    zero_placeholder_targets: Counter[str] = Counter()
    zero_placeholder_examples: list[dict[str, Any]] = []
    max_tes_distance = 0.0
    max_active_distance = 0.0
    bgo_50_80_records = 0
    bgo_below_50_records = 0

    def flush() -> None:
        nonlocal current_id, pixels, plastic, bgo
        if current_id is None:
            return
        detector_positive = bool(pixels) or plastic > 0.0 or bgo > 0.0
        if detector_positive:
            response = response_record(current_id, pixels, plastic, bgo, job)
            raw_hits = response["raw_hits"]
            if len(raw_hits) > np.iinfo(np.uint16).max:
                raise ClosureError(f"{job['job_id']} event {current_id} exceeds uint16 hit count")
            if len(arrays["hit_energy_keV"]) > np.iinfo(np.int32).max:
                raise ClosureError(f"{job['job_id']} exceeds int32 hit_start")
            arrays["event_id"].append(current_id)
            arrays["source_za"].append(-1)
            arrays["plastic_keV"].append(plastic)
            arrays["bgo_keV"].append(bgo)
            arrays["measured_total_keV"].append(response["measured_total_keV"])
            arrays["broad_flags"].append(response["broad_flags"])
            arrays["w2_flags"].append(response["w2_flags"])
            arrays["hit_start"].append(len(arrays["hit_energy_keV"]))
            arrays["hit_count"].append(len(raw_hits))
            for hit in raw_hits:
                layer, code = geometry["codes"][hit["uid"]]
                arrays["hit_code"].append(code)
                arrays["hit_layer"].append(layer)
                arrays["hit_energy_keV"].append(hit["energy"])
                arrays["hit_x_cm"].append(hit["x"])
                arrays["hit_y_cm"].append(hit["y"])
                arrays["hit_z_cm"].append(hit["z"])
        current_id = None
        pixels = {}
        plastic = 0.0
        bgo = 0.0

    started = time.time()
    with gzip.open(job["sim_path"], "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if not header_geometry and line.startswith("Geometry"):
                header_geometry = line.split(maxsplit=1)[1]
            elif header_seed is None and line.startswith("Seed"):
                header_seed = int(line.split()[1])
            if line == "SE":
                flush()
                continue
            id_match = SIM_ID_RE.match(line)
            if id_match:
                if current_id is not None:
                    raise ClosureError(f"{job['job_id']}: ID before event boundary")
                current_id = int(id_match.group("id"))
                generated += 1
                continue
            if not line.startswith("HTsim"):
                continue
            if current_id is None:
                raise ClosureError(f"{job['job_id']}: HTsim outside an event")
            match = HT_RE.match(line)
            if not match:
                raise ClosureError(f"{job['job_id']}: malformed HTsim record: {line[:200]}")
            decoded = decode_htsim_record(
                match,
                geometry,
                context=f"{job['job_id']} event {current_id}",
            )
            kind = int(decoded["kind"])
            kinds[kind] += 1
            separation = float(decoded["mapping_distance_cm"])
            if kind == 2:
                max_tes_distance = max(max_tes_distance, separation)
            elif kind == 4:
                max_active_distance = max(max_active_distance, separation)
            if decoded["serialized_zero_placeholder"]:
                zero_placeholder_kinds[kind] += 1
                zero_placeholder_targets[str(decoded["target"])] += 1
                if len(zero_placeholder_examples) < 20:
                    zero_placeholder_examples.append(
                        {
                            "event_id": current_id,
                            "kind": kind,
                            "target": decoded["target"],
                            "target_type": decoded["target_type"],
                            "xyz": list(decoded["xyz"]),
                            "energy_token": decoded["energy_token"],
                            "time_s": decoded["time_s"],
                            "mapping_distance_cm": separation,
                        }
                    )
                # A validated serialized zero contributes exactly nothing to
                # detector sums or response inputs.  Do not create a raw hit.
                continue
            positive_kinds[kind] += 1
            energy = float(decoded["energy_keV"])
            if kind == 2:
                add_pixel(
                    pixels,
                    str(decoded["target"]),
                    energy,
                    tuple(decoded["center"]),
                )
            else:
                volume = str(decoded["target"])
                if volume in PLASTIC_VOLUMES:
                    plastic += energy
                else:
                    bgo += energy
                    bgo_50_80_records += int(50.0 <= energy < 80.0)
                    bgo_below_50_records += int(energy < 50.0)
    flush()  # Mandatory: retained SIMs may omit trailing SE on the final event.

    require(generated, int(job["events"]), f"{job['job_id']} generated event count")
    require(Path(header_geometry).resolve(strict=True), Path(job["expected_geometry"]).resolve(strict=True), f"{job['job_id']} streamed geometry")
    require(header_seed, int(job["seed"]), f"{job['job_id']} streamed seed")
    if set(kinds) - {2, 4}:
        raise ClosureError(f"{job['job_id']}: unknown HTsim kinds survived: {sorted(set(kinds) - {2, 4})}")

    payload = {key: np.asarray(values, dtype=ARRAY_DTYPES[key]) for key, values in arrays.items()}
    event_count = len(payload["event_id"])
    if any(len(payload[key]) != event_count for key in ARRAY_DTYPES if not key.startswith("hit_")):
        raise ClosureError(f"{job['job_id']}: event-array length closure failed")
    if len(payload["hit_start"]) != event_count or len(payload["hit_count"]) != event_count:
        raise ClosureError(f"{job['job_id']}: event-to-hit index length closure failed")
    hit_count = len(payload["hit_energy_keV"])
    if any(len(payload[key]) != hit_count for key in ARRAY_DTYPES if key.startswith("hit_") and key not in {"hit_start", "hit_count"}):
        raise ClosureError(f"{job['job_id']}: hit-array length closure failed")

    npz_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_npz = npz_path.with_name(f".{npz_path.name}.tmp.{os.getpid()}")
    with temporary_npz.open("wb") as handle:
        np.savez_compressed(handle, **payload)
    os.replace(temporary_npz, npz_path)
    meta = {
        "schema_version": 1,
        "builder_schema": COMPACT_SCHEMA,
        "status": PASS_COMPACT,
        "scan_index": int(job["scan_index"]),
        "stream": "prompt",
        "mode": "instant",
        "candidate": "SG3B_MINIMAL_SD",
        "family": job["family"],
        "batch_id": BATCH_ID,
        "job_id": job["job_id"],
        "seed": int(job["seed"]),
        "events": generated,
        "sim_path": job["sim_path"],
        "sim_bytes": int(job["sim_bytes"]),
        "source_sha256": job["source_sha256"],
        "setup_stratum": SETUP_STRATUM,
        "exposure_TT_s": float(job["exposure_TT_s"]),
        "weight_cps": 0.0,
        "weight_policy": "DEFERRED__UNIFIED_OLD_PLUS_NEW_EXPOSURE",
        "detector_positive_events": event_count,
        "tes_positive_events": int(np.count_nonzero(payload["hit_count"])),
        "active_only_events": int(np.count_nonzero(payload["hit_count"] == 0)),
        "raw_pixel_hits": hit_count,
        "catalog_path": str(npz_path.resolve()),
        "htsim_kind_counts": {str(key): value for key, value in sorted(kinds.items())},
        "htsim_positive_kind_counts": {
            str(key): value for key, value in sorted(positive_kinds.items())
        },
        "unknown_htsim_kind_records": 0,
        "negative_or_nonfinite_htsim_energy_records": 0,
        "serialized_zero_energy_placeholder_records": int(
            sum(zero_placeholder_kinds.values())
        ),
        "serialized_zero_energy_placeholders_by_kind": {
            str(key): value for key, value in sorted(zero_placeholder_kinds.items())
        },
        "serialized_zero_energy_placeholders_by_target": dict(
            sorted(zero_placeholder_targets.items())
        ),
        "serialized_zero_energy_placeholder_examples": zero_placeholder_examples,
        "serialized_zero_energy_placeholder_policy_id": ZERO_PLACEHOLDER_POLICY_ID,
        "serialized_zero_energy_placeholder_policy": (
            "kind/centre validated first; exact fixed-five 0.00000 counted and ignored; "
            "all other nonpositive/nonfinite or unknown records fail closed"
        ),
        "max_tes_mapping_distance_cm": max_tes_distance,
        "max_active_mapping_distance_cm": max_active_distance,
        "bgo_50_80_keV_records": bgo_50_80_records,
        "bgo_below_50_keV_records": bgo_below_50_records,
        "geometry_pixel_uid_count": 2256,
        "fixedseed_gate_id": PILOT_GATE_ID,
        "fixedseed_gate_limitation": "100-event alpha pilot has no 480--550-keV or W2 event",
        "elapsed_s": time.time() - started,
        "sim_hashes_computed": 0,
        "transport_started": False,
    }
    write_json(meta_path, meta)
    return meta


def guard_cache(output: Path, jobs: list[dict[str, Any]]) -> None:
    cache = output / "job_catalogs"
    cache.mkdir(parents=True, exist_ok=True)
    expected: set[Path] = set()
    for job in jobs:
        npz, meta = expected_cache_paths(output, job)
        expected.update((npz, meta))
        if npz.exists() != meta.exists():
            raise ClosureError(f"partial compact pair requires manual review: {npz}, {meta}")
        if meta.is_file():
            validate_cached_meta(load_json(meta), job, npz)
    extras = sorted(
        str(path)
        for path in cache.iterdir()
        if path.is_file() and path.suffix in {".npz", ".json"} and path not in expected
    )
    if extras:
        raise ClosureError(f"unexpected SG3-minimal cache files: {extras[:5]}")


def verify_meta(job: Mapping[str, Any], meta: Mapping[str, Any], output: Path) -> dict[str, Any]:
    npz, sidecar = expected_cache_paths(output, job)
    validate_cached_meta(meta, job, npz)
    if not npz.is_file() or not sidecar.is_file():
        raise ClosureError(f"compact pair missing after scan: {npz}, {sidecar}")
    explicit_zero_audit = "serialized_zero_energy_placeholder_records" in meta
    zero_count = int(meta.get("serialized_zero_energy_placeholder_records", 0))
    return {
        "job_id": job["job_id"],
        "seed": int(job["seed"]),
        "family": job["family"],
        "stream": "prompt",
        "batch_id": BATCH_ID,
        "setup_stratum": SETUP_STRATUM,
        "exposure_TT_s": float(job["exposure_TT_s"]),
        "events": int(job["events"]),
        "sim_bytes": int(job["sim_bytes"]),
        "sim_path": job["sim_path"],
        "receipt_path": job["receipt_path"],
        "source_path": job["source_path"],
        "source_sha256": job["source_sha256"],
        "expected_geometry": job["expected_geometry"],
        "setup_sha256": job["setup_sha256"],
        "scan_index": int(job["scan_index"]),
        "cache_npz": str(npz.resolve()),
        "cache_json": str(sidecar.resolve()),
        "detector_positive_events": int(meta["detector_positive_events"]),
        "tes_positive_events": int(meta["tes_positive_events"]),
        "active_only_events": int(meta["active_only_events"]),
        "raw_pixel_hits": int(meta["raw_pixel_hits"]),
        "serialized_zero_energy_placeholder_records": zero_count,
        "serialized_zero_energy_placeholder_audit": (
            "EXPLICIT__FIXED5_POLICY"
            if explicit_zero_audit
            else "LEGACY_SUCCESSFUL_STRICT_SCAN__IMPLIES_ZERO_SUCH_RECORDS"
        ),
        "weight_cps": 0.0,
        "weight_policy": "DEFERRED__UNIFIED_OLD_PLUS_NEW_EXPOSURE",
    }


def execute(
    output: Path,
    jobs: list[dict[str, Any]],
    audit: dict[str, Any],
    workers: int,
) -> dict[str, Any]:
    output = output.resolve()
    allowed_root = (PACKAGE / "outputs").resolve()
    if output != allowed_root and not is_below(output, allowed_root):
        raise ClosureError(f"output must remain below the new dated package outputs: {output}")
    if FORBIDDEN_TASK_ID in str(output):
        raise ClosureError("forbidden task ID entered output path")
    guard_cache(output, jobs)
    write_json(output / "preflight_audit.json", audit)
    started = time.time()
    metas: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(scan_htsim_job, job, str(output)): job
            for job in jobs
        }
        for future in as_completed(futures):
            job = futures[future]
            meta = future.result()
            metas.append(meta)
            print(
                json.dumps(
                    {
                        "status": "PROGRESS__SG3_MINIMAL_COMPACT",
                        "job_id": job["job_id"],
                        "family": job["family"],
                        "detector_positive_events": int(meta["detector_positive_events"]),
                        "complete": len(metas),
                        "total": len(jobs),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    meta_by_job = indexed(metas, "job_id", "minimal compact metadata")
    rows = [verify_meta(job, meta_by_job[str(job["job_id"])], output) for job in jobs]
    exposure = {
        family: math.fsum(float(row["exposure_TT_s"]) for row in rows if row["family"] == family)
        for family in FAMILIES
    }
    jobs_payload = {
        "schema_version": 1,
        "schema": JOBS_SCHEMA,
        "status": "PASS__M05_SG3_MINIMAL_COMPACT_JOBS",
        "model": "sg3",
        "candidate": "SG3B_MINIMAL_SD",
        "setup_stratum": SETUP_STRATUM,
        "jobs_count": len(rows),
        "events": sum(int(row["events"]) for row in rows),
        "seeds": [int(row["seed"]) for row in rows],
        "exposure_TT_s_by_family": exposure,
        "weight_policy": "DEFERRED__UNIFIED_OLD_PLUS_NEW_EXPOSURE",
        "base_overlap_audit": audit["base_overlap_audit"],
        "fixedseed_exact_gate": audit["fixedseed_exact_gate"],
        "bounded_zero_placeholder_gate": audit["bounded_zero_placeholder_gate"],
        "serialized_zero_energy_placeholder_policy_id": ZERO_PLACEHOLDER_POLICY_ID,
        "jobs": rows,
    }
    jobs_path = output / "jobs.json"
    write_json(jobs_path, jobs_payload)
    scan_audit = {
        "schema_version": 1,
        "schema": "m05_sg3_minimal_scan_audit_v1",
        "status": "PASS__M05_SG3_MINIMAL_STREAMING_COMPACTION",
        "model": "sg3",
        "candidate": "SG3B_MINIMAL_SD",
        "setup_stratum": SETUP_STRATUM,
        "jobs_json": str(jobs_path),
        "jobs_count": len(rows),
        "events": jobs_payload["events"],
        "detector_positive_events": sum(int(row["detector_positive_events"]) for row in rows),
        "tes_positive_events": sum(int(row["tes_positive_events"]) for row in rows),
        "active_only_events": sum(int(row["active_only_events"]) for row in rows),
        "raw_pixel_hits": sum(int(row["raw_pixel_hits"]) for row in rows),
        "serialized_zero_energy_placeholder_records": sum(
            int(row["serialized_zero_energy_placeholder_records"]) for row in rows
        ),
        "serialized_zero_energy_placeholder_policy_id": ZERO_PLACEHOLDER_POLICY_ID,
        "bounded_zero_placeholder_gate_status": audit["bounded_zero_placeholder_gate"][
            "status"
        ],
        "exposure_TT_s_by_family": exposure,
        "workers": workers,
        "wall_s": time.time() - started,
        "fixedseed_gate_id": PILOT_GATE_ID,
        "authority_boundary": {
            "sim_payloads_streamed": len(rows),
            "sim_payload_bytes_streamed": sum(int(row["sim_bytes"]) for row in rows),
            "sim_hashes_computed": 0,
            "cosima_transport_started": False,
            "unreceipted_neutron_partial_read": False,
            "model_or_setup_strata_merged": False,
            "final_physical_weights_assigned": False,
        },
    }
    write_json(output / "scan_audit.json", scan_audit)
    return scan_audit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight", action="store_true", help="validate authorities and bounded pilot (default)")
    mode.add_argument("--execute", action="store_true", help="stream all validated receipt-backed minimal SIMs")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 1 <= args.workers <= 8:
        raise ClosureError("--workers must be in [1, 8]")
    manifest = args.manifest.resolve(strict=True)
    audit, jobs = preflight(manifest)
    print(json.dumps(audit, indent=2, sort_keys=True), flush=True)
    if not args.execute:
        return 0
    result = execute(args.output, jobs, audit, args.workers)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ClosureError as exc:
        print(json.dumps({"status": "FAIL__CLOSURE", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(2)
