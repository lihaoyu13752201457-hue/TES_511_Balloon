#!/usr/bin/env python3
"""Run the publication-statistics S3d-O8 all-family activation campaign.

This campaign complements the retained all-eight-family prompt transport with
an independent all-eight-family ActivationBuildUp run.  Delayed sources and
transports are kept separate by incident family so that the downstream
trajectory fold can apply the matching live PARMA family driver.  A family
with audited zero production is retained as PASS_ZERO_PRODUCTION and is not
assigned a fictitious delayed transport.

All mutable outputs are written to the dated package and dated run paths.  The
retained package-43 O8 geometry, source cards, prompt SIMs, and neutron-only
campaign remain read-only provenance.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import shlex
import subprocess
import sys
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
LOGS = PACKAGE / "logs"
REPORT_ROOT = PACKAGE / "fullchain/delayed_source"

O8_PACKAGE = (
    ROOT
    / "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712"
)
O8_CODE = O8_PACKAGE / "code"
if str(O8_CODE) not in sys.path:
    sys.path.insert(0, str(O8_CODE))

from _o8_replay_common import (  # noqa: E402
    S3D_GEOMETRY_SETUP,
    audit_geometry_authority,
    cosima_environment as _shared_cosima_environment,
    geometry_header_matches,
)
from s3d_o8_volume_map import (  # noqa: E402
    audit as audit_volume_map,
    canonicalize as canonicalize_volume,
    copy_map_from_geometry,
    configure as configure_volume_map,
    logical_volumes_from_dat,
)


GEOMETRY = S3D_GEOMETRY_SETUP.resolve()
GEOMETRY_REL = GEOMETRY.relative_to(ROOT).as_posix()
GEOMETRY_SOURCE = GEOMETRY.with_suffix("")
GEOMETRY_COPY_MAP = copy_map_from_geometry(GEOMETRY_SOURCE)
GEOMETRY_STEM = GEOMETRY_SOURCE.stem
GEOMETRY_BUNDLE = {
    "geometry_setup": GEOMETRY,
    "geometry_source": GEOMETRY_SOURCE,
    "geometry_detector": GEOMETRY.parent / f"{GEOMETRY_STEM}.det",
    "geometry_intro": GEOMETRY.parent / f"Intro_{GEOMETRY_STEM}.geo",
    "geometry_materials": GEOMETRY.parent / "Materials_DEMO2_DR_v3p5.geo",
}
# Hash-pinned retained O8 geometry authority.  These values are deliberately
# local constants: changing both a geometry include and an upstream mutable
# JSON cannot silently re-authorize an old delayed transport.
EXPECTED_O8_GEOMETRY_HASHES = {
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup": "86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec",
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo": "ff4e8402df702501e0112fe377d837a74c39100317146b09e9569b7bd615c37c",
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det": "dd2c1d68cd474f8b0c7489f2cbbfc924eb69beb14d3ce360d9437c319a33d6cb",
    "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo": "f4ea834bf385f68a85690e018fd52d692e94e19dd93959e35e6f91efd3dbfd52",
    "Materials_DEMO2_DR_v3p5.geo": "751cd83f08631085496ee86efa4418e4f001a639b15573554b93e73ff95678bf",
}
EXPECTED_MEGALIB_STANDARD_MATERIALS_SHA256 = (
    "db84cb337155c9dcf0c75e1d307ce1430cc27d95522dd33da6b1879730a5cb01"
)
# Filled with canonical relative-path/size/content tree digests from the pinned
# Geant4-10.2.3 data directories used by the retained MEGAlib environment.
EXPECTED_GEANT4_DATASET_TREE_SHA256: dict[str, str] = {
    "G4ABLADATA": "c624258ef723dc0ff7fefec2bb8a376a648e67931f674731ad7289b816a258a0",
    "G4ENSDFSTATEDATA": "d3f096b654c8f78113673ff37c22029a9f45b54aac56fd4111fc9bcb258e4f5e",
    "G4LEDATA": "44db30a6c8dd0575dd0f7d6427830fb132e75e5c55731d0170bf1a870f1cb572",
    "G4LEVELGAMMADATA": "0ecaab72b8a30c76efea5fbc4a76ef7a9401c76622c1698faf3108ff4463a9bd",
    "G4NEUTRONHPDATA": "eeb370ab24ad8ef4da3e2bc9a68e43facd4fe73f0155998b471b9adabb5c3a93",
    "G4NEUTRONXSDATA": "e61ca4358433e2831ac0696cc2b7a53c9466509abe99f0e15c8b5a9f6ab50b33",
    "G4PIIDATA": "37b1c83dbfb1085de9679c0a40a54c900a458be2b9c4aeecb1e128c9d27f421e",
    "G4RADIOACTIVEDATA": "7968f90f688a497a175c3b733a5a78c302d15e13a7b5f344029f8aaed9efa5e0",
    "G4REALSURFACEDATA": "311b9796777cebd6c786049c81d2df5f8d9996f80c42f4b7bae52ee0778637c2",
    "G4SAIDXSDATA": "fb25972753429eee4cf980c608314f5311d6c3b476d35d73a6db80e5474e4e65",
}
EXPECTED_RUNTIME_LIBRARY_CLOSURE_SHA256 = (
    "67f4f811c08e675ec4e8353e8ffc40c0c1ab812d26c2f1162d593e14273fa710"
)
EXPECTED_MEGALIB_ROOT = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
EXPECTED_GEANT4_ROOT = EXPECTED_MEGALIB_ROOT / "external/geant4_v10.02.p03"
EXPECTED_GEANT4_DATA_ROOT = (
    EXPECTED_GEANT4_ROOT / "share/Geant4-10.2.3/data"
)
EXPECTED_GEANT4_DATASET_PATHS = {
    "G4ABLADATA": str(EXPECTED_GEANT4_DATA_ROOT / "G4ABLA3.0"),
    "G4ENSDFSTATEDATA": str(EXPECTED_GEANT4_DATA_ROOT / "G4ENSDFSTATE1.2.3"),
    "G4LEDATA": str(EXPECTED_GEANT4_DATA_ROOT / "G4EMLOW6.48"),
    "G4LEVELGAMMADATA": str(EXPECTED_GEANT4_DATA_ROOT / "PhotonEvaporation3.2"),
    "G4NEUTRONHPDATA": str(EXPECTED_GEANT4_DATA_ROOT / "G4NDL4.5"),
    "G4NEUTRONXSDATA": str(EXPECTED_GEANT4_DATA_ROOT / "G4NEUTRONXS1.4"),
    "G4PIIDATA": str(EXPECTED_GEANT4_DATA_ROOT / "G4PII1.3"),
    "G4RADIOACTIVEDATA": str(EXPECTED_GEANT4_DATA_ROOT / "RadioactiveDecay4.3.2"),
    "G4REALSURFACEDATA": str(EXPECTED_GEANT4_DATA_ROOT / "RealSurface1.0"),
    "G4SAIDXSDATA": str(EXPECTED_GEANT4_DATA_ROOT / "G4SAIDDATA1.1"),
}
# These optional ParticleHP/NeutronHP switches can materially change isotope
# production.  The retained authority has every one absent.  Since the gate
# also rejects *any* unrecognised G4* key, this explicit list is documentary
# rather than an incomplete allow-list.
OPTIONAL_GEANT4_HP_ENVIRONMENT_KEYS = (
    "G4NEUTRONHP_DBRC_MAX_A",
    "G4NEUTRONHP_DBRC_MAX_ENERGY",
    "G4NEUTRONHP_DBRC_MIN_A",
    "G4NEUTRONHP_DBRC_MIN_ENERGY",
    "G4NEUTRONHP_DO_NOT_ADJUST_FINAL_STATE",
    "G4NEUTRONHP_NEGLECT_DOPPLER",
    "G4NEUTRONHP_PRODUCE_FISSION_FRAGMENTS",
    "G4NEUTRONHP_SKIP_MISSING_ISOTOPES",
    "G4NEUTRONHP_USE_DBRC",
    "G4NEUTRONHP_USE_NRESP71_MODEL",
    "G4NEUTRONHP_USE_ONLY_PHOTONEVAPORATION",
    "G4NEUTRONHP_USE_WENDT_FISSION_MODEL",
    "G4PARTICLEHP_DO_NOT_ADJUST_FINAL_STATE",
    "G4PARTICLEHP_PRODUCE_FISSION_FRAGMENTS",
    "G4PARTICLEHP_SKIP_MISSING_ISOTOPES",
    "G4PARTICLEHP_USE_ONLY_PHOTONEVAPORATION",
    "G4PARTICLEHP_USE_WENDT_FISSION_MODEL",
    "G4PHP_DO_NOT_ADJUST_FINAL_STATE",
)
EXPECTED_COSIMA_LAUNCH_ENVIRONMENT = {
    **EXPECTED_GEANT4_DATASET_PATHS,
    "HOME": "/home/ubuntu",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "LD_LIBRARY_PATH": ":".join(
        (
            str(EXPECTED_MEGALIB_ROOT / "lib"),
            str(EXPECTED_MEGALIB_ROOT / "external/root_v6.36.6/lib"),
            str(EXPECTED_GEANT4_ROOT / "lib"),
        )
    ),
    "LOGNAME": "ubuntu",
    "MEGALIB": str(EXPECTED_MEGALIB_ROOT),
    "PATH": (
        f"{EXPECTED_MEGALIB_ROOT}/bin:"
        "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    ),
    "TZ": "UTC",
    "USER": "ubuntu",
}
PARENT_ENVIRONMENT_REJECT_KEYS = (
    "LD_AUDIT",
    "LD_PRELOAD",
    "LD_PROFILE",
    "MEGALIB",
    "ROOTSYS",
)
SOURCE_CARDS = O8_PACKAGE / "config/full_prompt_all8/source_cards"
SOURCE_CARD_MANIFEST = SOURCE_CARDS / "source_migration_manifest.json"
EXPECTED_SOURCE_CARD_MANIFEST_SHA256 = (
    "f7b673eb2a35a25b4902e369838e43d78531c88f8a75e8eabd38422ea1384485"
)
EXPECTED_SOURCE_CARD_SHA256 = {
    "alpha": "f2f1cae592061a8c21092e9358dc24168685db6b8f3eea3c44b4442b5d6e17ab",
    "eminus": "6142fecc9434b93745ce6f06f12873ff9f2086d72deadde031781e9f544f28d2",
    "eplus": "e5e88cad2451e467a9099f48ec6e726469a29bb57c481c4758175628e47ad1c5",
    "gamma": "eec96f3d779a6db79852077d274837b8547e7db2d1596e5607962c1b9efaf260",
    "muminus": "b50119751da2b419f7a2635c25a907ba3048ae93f023cdd0b7fecbc1a49368e6",
    "muplus": "d7ca2176b33cde823ac6c636beac312c3905da9913e1bce804a632e9ab017bc3",
    "n": "9dcbec5540604e353b7c1e93156364b0b536e6edd1364996b8bca0531a84aa23",
    "p": "04d61c3b4f49d72a83519810c856d08ac42995236268262da9f4f283b3b06c9b",
}
SOURCE_SPECTRUM_ROOT = (
    ROOT / "expacs_fullsphere_20bin_sources/cosima_spectra_dp_2602units"
)
EXPECTED_SOURCE_SPECTRUM_TREE_SHA256 = (
    "b73f9647916468a5a6a2cc11aae312766ffa7c14c1c02b5f8af214ddbcd9d1f0"
)
EXPECTED_SOURCE_SPECTRUM_TOTAL_BYTES = 542_160
EXPECTED_SOURCE_SPECTRUM_AGGREGATE_SHA256 = (
    "1b658cd9712e3773067e0012c9fab71d566b027c48bbc00c95d2f8b735820f98"
)
PROMPT_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704/s3d_o8_fullstat_prompt_all8_20260712"
)

RUN_ROOT = ROOT / "runs/geometry_optimization_20260704"
LABEL = "s3d_o8_all8_activation_m50000_20260713"
BUILDUP_DIR = RUN_ROOT / f"step02_buildup_{LABEL}"
RAW_ROOT = RUN_ROOT / f"step02_decay_source_{LABEL}"
FIX_ROOT = RUN_ROOT / f"step02_delay_fix_{LABEL}"
VIEW_ROOT = RUN_ROOT / f"step02_family_view_{LABEL}"
EXACT_ROOT = RUN_ROOT / f"step02_delay_exactpos_{LABEL}"
TRANSPORT_ROOT = RUN_ROOT / f"step02_delayed_transport_{LABEL}"

RUN_EQUIV = ROOT / "code/tools/run_equiv2602_pipeline_NEW_GEO.py"
MAKE_RPIP = PACKAGE / "code/run_s3d_o8_makedecay.py"
FIX_SOURCE = PACKAGE / "code/run_s3d_o8_fixed_source.py"
EXACTPOS_HELPER = ROOT / "code/tools/build_fix5_1of10_exactpos_delayed_source.py"
FIX_HELPER = ROOT / "code/tools/build_fixed_delay_source.py"
NUBASE = ROOT / "inputs/nubase/nubase_2020.txt"
EXPECTED_NUBASE_2020_SHA256 = (
    "1585a5eea86c5e17e90307c7e6e786d060049c4039e392a261ff6db977df9859"
)
MAKE_RPIP_HELPER = ROOT / "code/tools/makedecaysourcewithplot_rpip.py"
VOLUME_MAP_CODE = PACKAGE / "code/s3d_o8_volume_map.py"
ACTIVATION_HARNESS = Path(__file__).resolve()
O8_REPLAY_COMMON = O8_CODE / "_o8_replay_common.py"
SHARED_REPLAY_COMMON = (
    ROOT
    / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/_s3d_replay_common.py"
)

FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
EXPECTED_COUNTS = {tag: (12 if tag == "gamma" else 8) for tag in FAMILIES}
EXPECTED_JOBS = sum(EXPECTED_COUNTS.values())
EXPECTED_EVENTS = 25_210_216
EXPECTED_BUILDUP_JOB_CONTRACT_SHA256 = (
    "da593d56a2e9d81ea41c2c27332cf1b51abc4b693573cb3a560297f35cfe1024"
)
EXPECTED_SOURCE_FLUX_CM2_S = {
    "alpha": 0.011487096450232017,
    "eminus": 0.19900204457214196,
    "eplus": 0.11698054572276201,
    "gamma": 4.7996615777852,
    "muminus": 0.0049689300223750696,
    "muplus": 0.0055700117660621405,
    "n": 0.462239182229625,
    "p": 0.11230072163133409,
}
EXPECTED_BASE_EVENTS_BY_FAMILY = {
    "alpha": 23_933,
    "eminus": 414_617,
    "eplus": 243_727,
    "gamma": 10_000_000,
    "muminus": 10_353,
    "muplus": 11_605,
    "n": 963_066,
    "p": 233_976,
}
EXPECTED_TOTAL_EVENTS_BY_FAMILY = {
    "alpha": 191_464,
    "eminus": 3_316_936,
    "eplus": 1_949_816,
    "gamma": 10_000_000,
    "muminus": 82_824,
    "muplus": 92_840,
    "n": 7_704_528,
    "p": 1_871_808,
}
GAMMA_EVENTS = 10_000_000
GAMMA_SPLITS = 12
NON_GAMMA_REPLICAS = 8
NON_GAMMA_DIV = 8
FARFIELD_RADIUS_CM = 60.0
N_SAMPLE = 2_000_000
RAW_TRIGGERS = 1_000_000
M_BLOCKS = 50_000
SEED = 260_613
T_FLIGHT_DAYS = 15.0

PREFLIGHT = DATA / "s3d_o8_all8_activation_preflight.json"
CAMPAIGN = DATA / "s3d_o8_all8_activation_campaign.json"
FAMILY_ACTIVITY = DATA / "s3d_o8_all8_family_activity_audit.json"
AUTHORITY_LOCK = DATA / ".s3d_o8_all8_source_transport_authority.lock"

# Set only while this process owns AUTHORITY_LOCK.  Transport children inherit
# this descriptor (and the family descriptor) so a SIGKILL of Python cannot
# release the locks while an orphan Cosima is still writing the same prefix.
_CURRENT_AUTHORITY_LOCK_FD: int | None = None
_CURRENT_AUTHORITY_LOCK_EVIDENCE: dict[str, Any] | None = None

CONFIRM_TOKENS = {
    "run-buildup": "RUN_S3D_O8_ALL8_BUILDUP_20260713",
    "prepare-delay": "BUILD_S3D_O8_ALL8_FAMILY_DELAY_SOURCES_20260713",
    "run-delay": "RUN_S3D_O8_ALL8_FAMILY_DELAYED_1M_20260713",
    "all": "RUN_S3D_O8_ALL8_ACTIVATION_FULLCHAIN_20260713",
}

GEOMETRY_RE = re.compile(r"^\s*Geometry\s+(.+?)\s*$")
RP_RE = re.compile(r"^\s*RP\s+(\d+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$")
TT_RE = re.compile(r"^\s*TT\s+([-+0-9.eE]+)\s*$")
EXACT_FLUX_RE = re.compile(
    r"^\s*RP_(\d+)\.Flux\s+([-+0-9.eE]+)\s*$"
)
SPECTRUM_FILE_RE = re.compile(r"^\s*\S+\.Spectrum\s+File\s+(\S+)\s*$")


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
        return value.resolve().relative_to(ROOT).as_posix()
    except (ValueError, FileNotFoundError):
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_record(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "sha256": sha256(path) if path.is_file() else None,
    }


def nubase_authority_record() -> dict[str, Any]:
    record = artifact_record(NUBASE)
    if record.get("sha256") != EXPECTED_NUBASE_2020_SHA256:
        raise RuntimeError(
            "NUBASE-2020 differs from the hash-pinned ground-state authority: "
            f"{record.get('sha256')} != {EXPECTED_NUBASE_2020_SHA256}"
        )
    return {
        **record,
        "status": "PASS",
        "expected_sha256": EXPECTED_NUBASE_2020_SHA256,
    }


def canonical_payload_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def physics_environment_contract(env: dict[str, str]) -> dict[str, Any]:
    """Return the complete, non-secret environment passed to Cosima.

    Cosima is deliberately launched with a minimal deterministic environment,
    not a copy of the calling shell.  Thus this is both a complete record and
    a hard pin rather than a selected-key projection of a larger inherited
    environment.
    """
    current = dict(sorted(env.items()))
    if current != dict(sorted(EXPECTED_COSIMA_LAUNCH_ENVIRONMENT.items())):
        raise RuntimeError(
            "effective Cosima launch environment differs from the retained "
            f"minimal authority: current={current} "
            f"expected={EXPECTED_COSIMA_LAUNCH_ENVIRONMENT}"
        )
    all_g4 = {key: value for key, value in current.items() if key.startswith("G4")}
    if all_g4 != EXPECTED_GEANT4_DATASET_PATHS:
        raise RuntimeError(
            "complete G4* environment differs from the ten-key dataset-only "
            f"authority: current={all_g4} expected={EXPECTED_GEANT4_DATASET_PATHS}"
        )
    optional_hp = {
        key: {"present": key in current, "value": current.get(key)}
        for key in OPTIONAL_GEANT4_HP_ENVIRONMENT_KEYS
    }
    if any(row["present"] for row in optional_hp.values()):
        raise RuntimeError(f"optional Geant4 HP switches must be absent: {optional_hp}")
    loader = {
        key: {"present": key in current, "value": current.get(key)}
        for key in ("LD_LIBRARY_PATH", "LD_PRELOAD", "LD_AUDIT", "LD_PROFILE")
    }
    payload: dict[str, Any] = {
        "status": "PASS",
        "policy": "COMPLETE_MINIMAL_ENVIRONMENT_NO_PARENT_INHERITANCE",
        "launch_environment": current,
        "all_g4_environment": all_g4,
        "all_g4_environment_keys": sorted(all_g4),
        "optional_geant4_hp_environment": optional_hp,
        "megalib": {"present": "MEGALIB" in current, "value": current.get("MEGALIB")},
        "rootsys": {"present": "ROOTSYS" in current, "value": current.get("ROOTSYS")},
        "dynamic_loader_environment": loader,
        "parent_environment_policy": {
            "reject_prefixes": ["G4"],
            "reject_keys": list(PARENT_ENVIRONMENT_REJECT_KEYS),
            "sanitized_not_inherited": [
                "HOME",
                "LANG",
                "LC_ALL",
                "LD_LIBRARY_PATH",
                "LOGNAME",
                "PATH",
                "TZ",
                "USER",
            ],
        },
    }
    payload["canonical_payload_sha256"] = canonical_payload_sha256(payload)
    return payload


def cosima_environment() -> tuple[dict[str, str], dict[str, Any]]:
    """Load the pinned setup, reject physics injection, then sanitize it.

    The shared loader sources the retained script in a child shell.  Before
    doing so, reject every parent G4* key (including unknown future switches)
    and the loader/MEGAlib injection keys that cannot safely be inherited.
    The returned environment is then reconstructed from constants, so the
    caller's PATH and LD_LIBRARY_PATH cannot enter Cosima either.
    """
    injected = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("G4") or key in PARENT_ENVIRONMENT_REJECT_KEYS
    }
    if injected:
        raise RuntimeError(
            "refusing parent physics-environment injection before loading the "
            f"retained MEGAlib authority: {dict(sorted(injected.items()))}"
        )
    loaded_env, evidence = _shared_cosima_environment()
    loaded_g4 = {
        key: value for key, value in loaded_env.items() if key.startswith("G4")
    }
    if loaded_g4 != EXPECTED_GEANT4_DATASET_PATHS:
        raise RuntimeError(
            "retained environment script exported an unexpected complete G4* "
            f"mapping: current={loaded_g4} expected={EXPECTED_GEANT4_DATASET_PATHS}"
        )
    if loaded_env.get("MEGALIB") != str(EXPECTED_MEGALIB_ROOT):
        raise RuntimeError(
            f"MEGALIB={loaded_env.get('MEGALIB')} expected={EXPECTED_MEGALIB_ROOT}"
        )
    env = dict(EXPECTED_COSIMA_LAUNCH_ENVIRONMENT)
    contract = physics_environment_contract(env)
    enriched_evidence = dict(evidence)
    enriched_evidence["required_dataset_paths"] = dict(
        EXPECTED_GEANT4_DATASET_PATHS
    )
    enriched_evidence["physics_environment"] = contract
    return env, enriched_evidence


def directory_tree_record(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    files = 0
    total_bytes = 0
    if path.is_dir():
        for item in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
            relative = item.relative_to(path).as_posix()
            size = item.stat().st_size
            item_sha = sha256(item)
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(str(size).encode("ascii"))
            digest.update(b"\0")
            digest.update(item_sha.encode("ascii"))
            digest.update(b"\n")
            files += 1
            total_bytes += size
    return {
        "path": str(path.resolve()),
        "files": files,
        "total_bytes": total_bytes,
        "tree_sha256": digest.hexdigest() if path.is_dir() else None,
    }


def exact_source_flux_audit(
    path: Path,
    *,
    expected_total_activity_bq: float | None = None,
) -> dict[str, Any]:
    indices: list[int] = []
    fluxes: list[float] = []
    if path.is_file():
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = EXACT_FLUX_RE.match(raw)
            if match:
                indices.append(int(match.group(1)))
                fluxes.append(float(match.group(2)))
    problems: list[str] = []
    if indices != list(range(len(indices))):
        problems.append("RP Flux indices are not contiguous and zero-based")
    if len(indices) != M_BLOCKS:
        problems.append(f"Flux blocks={len(indices)} expected={M_BLOCKS}")
    if any(not math.isfinite(value) or value <= 0.0 for value in fluxes):
        problems.append("one or more RP Flux values are non-finite/non-positive")
    unique_fluxes = sorted(set(fluxes))
    if len(unique_fluxes) != 1:
        problems.append(
            f"RP Flux values are not uniform: unique_values={len(unique_fluxes)}"
        )
    expected_unrounded_flux = None
    expected_serialized_flux_text = None
    expected_serialized_flux = None
    expected_serialized_sum = None
    independently_derived_rounding_delta = None
    max_rounding_delta_bound = None
    if expected_total_activity_bq is not None:
        expected_unrounded_flux = expected_total_activity_bq / M_BLOCKS
        expected_serialized_flux_text = f"{expected_unrounded_flux:.8e}"
        expected_serialized_flux = float(expected_serialized_flux_text)
        expected_serialized_sum = expected_serialized_flux * M_BLOCKS
        independently_derived_rounding_delta = abs(
            expected_total_activity_bq - expected_serialized_sum
        )
        exponent = math.floor(math.log10(abs(expected_unrounded_flux)))
        single_value_half_ulp = 0.5 * 10.0 ** (exponent - 8)
        max_rounding_delta_bound = M_BLOCKS * single_value_half_ulp
        if any(value != expected_serialized_flux for value in fluxes):
            problems.append(
                "one or more RP Flux values differ from the independently formatted fixed_total/M value"
            )
        if independently_derived_rounding_delta > max_rounding_delta_bound + 1e-15:
            problems.append(
                "independently derived serialized-source rounding delta exceeds the 0.5-ulp-per-block bound"
            )
    return {
        "status": "PASS" if not problems else "FAIL",
        "path": rel(path),
        "blocks": len(indices),
        "sum_flux_Bq": math.fsum(fluxes),
        "min_flux_Bq": min(fluxes) if fluxes else None,
        "max_flux_Bq": max(fluxes) if fluxes else None,
        "unique_flux_values": len(unique_fluxes),
        "uniform_flux_Bq": unique_fluxes[0] if len(unique_fluxes) == 1 else None,
        "expected_total_activity_Bq": expected_total_activity_bq,
        "expected_unrounded_flux_Bq": expected_unrounded_flux,
        "expected_serialized_flux_text": expected_serialized_flux_text,
        "expected_serialized_flux_Bq": expected_serialized_flux,
        "expected_serialized_sum_Bq": expected_serialized_sum,
        "independently_derived_rounding_delta_Bq": independently_derived_rounding_delta,
        "max_rounding_delta_bound_Bq": max_rounding_delta_bound,
        "problems": problems,
    }


def geometry_bundle_snapshot() -> dict[str, Any]:
    """Return and independently hash the complete five-file O8 geometry."""
    authority = audit_geometry_authority()
    current_hashes = authority.get("o8_geometry_hashes") or {}
    if current_hashes != EXPECTED_O8_GEOMETRY_HASHES:
        raise RuntimeError(
            "current O8 geometry bundle differs from the retained hash-pinned authority: "
            f"current={current_hashes} expected={EXPECTED_O8_GEOMETRY_HASHES}"
        )
    artifacts = {name: artifact_record(path) for name, path in GEOMETRY_BUNDLE.items()}
    artifact_hashes = {
        Path(str(row["path"])).name: row.get("sha256") for row in artifacts.values()
    }
    if artifact_hashes != EXPECTED_O8_GEOMETRY_HASHES:
        raise RuntimeError(
            "direct five-file geometry rehash differs from retained authority: "
            f"current={artifact_hashes} expected={EXPECTED_O8_GEOMETRY_HASHES}"
        )
    return {
        "status": "PASS",
        "expected_sha256_by_filename": dict(EXPECTED_O8_GEOMETRY_HASHES),
        "artifacts": artifacts,
    }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_json_atomic(path: Path, payload: Any) -> None:
    """Atomically replace a small authority JSON after complete serialization."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def run_command(
    command: list[str],
    log_path: Path,
    env: dict[str, str] | None = None,
    *,
    pass_fds: tuple[int, ...] = (),
) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write("command=" + shlex.join(command) + "\n")
        handle.write("-" * 78 + "\n")
        handle.flush()
        proc = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            pass_fds=pass_fds,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
        handle.write("-" * 78 + "\n")
        handle.write(f"returncode={proc.returncode}\n")
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed with return code {proc.returncode}; see {rel(log_path)}"
        )


def authority_lock_pass_fds() -> tuple[int, ...]:
    if _CURRENT_AUTHORITY_LOCK_FD is None:
        raise RuntimeError("this mutation requires the global authority lock")
    return (_CURRENT_AUTHORITY_LOCK_FD,)


def normalize_path(value: str | Path | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    path = Path(str(value).strip())
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve().as_posix()


def source_geometry(path: Path) -> list[str]:
    values: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = GEOMETRY_RE.match(raw)
        if match:
            values.append(match.group(1).strip())
    return values


def open_sim(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def sim_geometry(path: Path) -> str | None:
    if not path.is_file():
        return None
    with open_sim(path) as handle:
        for raw in handle:
            if raw.startswith("Geometry"):
                parts = raw.split(None, 1)
                return parts[1].strip() if len(parts) == 2 else ""
            if raw.startswith("SE"):
                break
    return None


def sim_header_metadata(path: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {"geometry": None, "seed": None}
    if not path.is_file():
        return metadata
    with open_sim(path) as handle:
        for raw in handle:
            fields = raw.strip().split(None, 1)
            if len(fields) == 2 and fields[0] == "Geometry":
                metadata["geometry"] = fields[1].strip()
            elif len(fields) == 2 and fields[0] == "Seed":
                try:
                    metadata["seed"] = int(fields[1].strip())
                except ValueError:
                    metadata["seed"] = fields[1].strip()
            elif fields and fields[0] == "SE":
                break
    return metadata


def parse_sim_transport(path: Path) -> dict[str, Any]:
    """Independently stream-parse the SIM transport contract from raw bytes."""
    result: dict[str, Any] = {
        "path": rel(path),
        "geometry": None,
        "seed": None,
        "SE": 0,
        "ID": 0,
        "ID_sequence_mismatches": 0,
        "TS_records": 0,
        "TS_value": None,
        "TE_records": 0,
        "TE_s": None,
    }
    problems: list[str] = []
    if not path.is_file():
        result.update({"status": "FAIL", "problems": ["SIM is missing"]})
        return result
    expected_id = 1
    with open_sim(path) as handle:
        for raw in handle:
            line = raw.strip()
            fields = line.split()
            if not fields:
                continue
            key = fields[0]
            if key == "Geometry" and len(fields) >= 2:
                result["geometry"] = " ".join(fields[1:])
            elif key == "Seed" and len(fields) == 2:
                try:
                    result["seed"] = int(fields[1])
                except ValueError:
                    problems.append(f"invalid Seed line: {line}")
            elif key == "SE" and len(fields) == 1:
                result["SE"] += 1
            elif key == "ID":
                result["ID"] += 1
                try:
                    first = int(fields[1])
                    second = int(fields[2])
                except (IndexError, ValueError):
                    result["ID_sequence_mismatches"] += 1
                else:
                    if first != expected_id or second != expected_id:
                        result["ID_sequence_mismatches"] += 1
                expected_id += 1
            elif key == "TS":
                result["TS_records"] += 1
                try:
                    result["TS_value"] = int(fields[1])
                except (IndexError, ValueError):
                    problems.append(f"invalid TS line: {line}")
            elif key == "TE":
                result["TE_records"] += 1
                try:
                    result["TE_s"] = float(fields[1])
                except (IndexError, ValueError):
                    problems.append(f"invalid TE line: {line}")
    if result["ID_sequence_mismatches"]:
        problems.append(
            f"ID sequence mismatches={result['ID_sequence_mismatches']}"
        )
    result["status"] = "PASS" if not problems else "FAIL"
    result["problems"] = problems
    return result


def tt_values(path: Path) -> list[float]:
    values: list[float] = []
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = TT_RE.match(raw)
        if match:
            values.append(float(match.group(1)))
    return values


def path_from_row(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def runtime_library_closure(
    env: dict[str, str],
    cosima_executable: Path,
    *,
    verify_expected: bool = True,
) -> dict[str, Any]:
    proc = subprocess.run(
        ["ldd", str(cosima_executable)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ldd failed for Cosima: {proc.stderr.strip()}")
    paths: set[Path] = set()
    unresolved: list[str] = []
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if not line or line.startswith("linux-vdso"):
            continue
        if "=> not found" in line:
            unresolved.append(line)
            continue
        candidate: str | None = None
        if "=>" in line:
            rhs = line.split("=>", 1)[1].strip()
            if rhs.startswith("/"):
                candidate = rhs.split()[0]
        elif line.startswith("/"):
            candidate = line.split()[0]
        if candidate:
            paths.add(Path(candidate).resolve())
    if unresolved:
        raise RuntimeError(f"unresolved Cosima runtime libraries: {unresolved}")
    libraries = [artifact_record(path) for path in sorted(paths)]
    if any(not row.get("sha256") for row in libraries):
        raise RuntimeError("one or more resolved Cosima runtime libraries are missing")
    closure_sha = canonical_payload_sha256(libraries)
    if (
        verify_expected
        and closure_sha != EXPECTED_RUNTIME_LIBRARY_CLOSURE_SHA256
    ):
        raise RuntimeError(
            "Cosima dynamic-library closure differs from retained authority: "
            f"{closure_sha} != {EXPECTED_RUNTIME_LIBRARY_CLOSURE_SHA256}"
        )
    return {
        "status": "PASS",
        "libraries": libraries,
        "library_count": len(libraries),
        "closure_sha256": closure_sha,
        "expected_closure_sha256": EXPECTED_RUNTIME_LIBRARY_CLOSURE_SHA256,
    }


def runtime_dependency_snapshot(
    env: dict[str, str],
    evidence: dict[str, Any],
    *,
    verify_expected: bool = True,
) -> dict[str, Any]:
    physics_environment = physics_environment_contract(env)
    if evidence.get("physics_environment") != physics_environment:
        raise RuntimeError(
            "MEGAlib environment evidence does not bind the exact environment "
            "that will be passed to Cosima"
        )
    if (evidence.get("required_dataset_paths") or {}) != (
        EXPECTED_GEANT4_DATASET_PATHS
    ):
        raise RuntimeError(
            "MEGAlib environment evidence has unexpected Geant4 dataset paths"
        )
    standard_materials = (
        Path(env["MEGALIB"])
        / "resource/examples/geomega/materials/Materials.geo"
    )
    standard_record = artifact_record(standard_materials)
    if (
        verify_expected
        and standard_record.get("sha256")
        != EXPECTED_MEGALIB_STANDARD_MATERIALS_SHA256
    ):
        raise RuntimeError(
            "MEGAlib standard Materials.geo differs from the retained authority: "
            f"{standard_record.get('sha256')} != "
            f"{EXPECTED_MEGALIB_STANDARD_MATERIALS_SHA256}"
        )
    datasets = {
        name: directory_tree_record(Path(path))
        for name, path in sorted(
            (evidence.get("required_dataset_paths") or {}).items()
        )
    }
    current_dataset_hashes = {
        name: row.get("tree_sha256") for name, row in datasets.items()
    }
    if verify_expected and current_dataset_hashes != EXPECTED_GEANT4_DATASET_TREE_SHA256:
        raise RuntimeError(
            "Geant4 dataset trees differ from the retained hash-pinned authority: "
            f"current={current_dataset_hashes} "
            f"expected={EXPECTED_GEANT4_DATASET_TREE_SHA256}"
        )
    environment_script = path_from_row(str(evidence["script"]))
    cosima_path = Path(str(evidence["cosima"]))
    library_closure = runtime_library_closure(
        env,
        cosima_path,
        verify_expected=verify_expected,
    )
    return {
        "status": "PASS",
        "environment_script": artifact_record(environment_script),
        "environment_script_pinned_sha256": evidence.get("pinned_script_sha256"),
        "cosima_executable": artifact_record(cosima_path),
        "dynamic_library_closure": library_closure,
        "physics_environment": physics_environment,
        "megalib_standard_materials": standard_record,
        "geant4_datasets": datasets,
        "expected_geant4_dataset_tree_sha256": dict(
            EXPECTED_GEANT4_DATASET_TREE_SHA256
        ),
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def source_spectrum_authority_snapshot() -> dict[str, Any]:
    by_family: dict[str, list[dict[str, Any]]] = {}
    all_references: list[str] = []
    problems: list[str] = []
    for tag in FAMILIES:
        card = SOURCE_CARDS / f"Background_{tag}_fullsphere20.source"
        references: list[str] = []
        if card.is_file():
            for raw in card.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines():
                match = SPECTRUM_FILE_RE.match(raw)
                if match:
                    references.append(match.group(1))
        records: list[dict[str, Any]] = []
        if len(references) != 20 or len(set(references)) != 20:
            problems.append(
                f"{tag}: spectrum references={len(references)} "
                f"unique={len(set(references))} expected=20/20"
            )
        for reference in references:
            path = (ROOT / reference).resolve()
            try:
                path.relative_to(SOURCE_SPECTRUM_ROOT.resolve())
            except ValueError:
                problems.append(f"{tag}: spectrum escapes pinned root: {reference}")
            record = artifact_record(path)
            records.append(record)
            if not record.get("sha256"):
                problems.append(f"{tag}: missing spectrum: {reference}")
        by_family[tag] = sorted(records, key=lambda row: str(row["path"]))
        all_references.extend(references)
    records = sorted(
        (row for family_rows in by_family.values() for row in family_rows),
        key=lambda row: str(row["path"]),
    )
    unique_paths = {str(row["path"]) for row in records}
    directory_files = {
        rel(path)
        for path in SOURCE_SPECTRUM_ROOT.rglob("*")
        if path.is_file()
    }
    if len(records) != 160 or len(unique_paths) != 160:
        problems.append(
            f"spectrum records={len(records)} unique_paths={len(unique_paths)} "
            "expected=160/160"
        )
    if unique_paths != directory_files:
        problems.append(
            "card-referenced spectrum set differs from the complete pinned directory"
        )
    tree = directory_tree_record(SOURCE_SPECTRUM_ROOT)
    if (
        tree.get("files") != 160
        or tree.get("total_bytes") != EXPECTED_SOURCE_SPECTRUM_TOTAL_BYTES
        or tree.get("tree_sha256") != EXPECTED_SOURCE_SPECTRUM_TREE_SHA256
    ):
        problems.append(
            f"spectrum tree={tree.get('files')}/{tree.get('total_bytes')}/"
            f"{tree.get('tree_sha256')} expected=160/"
            f"{EXPECTED_SOURCE_SPECTRUM_TOTAL_BYTES}/"
            f"{EXPECTED_SOURCE_SPECTRUM_TREE_SHA256}"
        )
    aggregate = canonical_payload_sha256(records)
    if aggregate != EXPECTED_SOURCE_SPECTRUM_AGGREGATE_SHA256:
        problems.append(
            f"spectrum aggregate={aggregate} expected="
            f"{EXPECTED_SOURCE_SPECTRUM_AGGREGATE_SHA256}"
        )
    return {
        "status": "PASS" if not problems else "FAIL",
        "root": rel(SOURCE_SPECTRUM_ROOT),
        "expected_files": 160,
        "referenced_files": len(records),
        "unique_referenced_files": len(unique_paths),
        "tree": tree,
        "expected_tree_sha256": EXPECTED_SOURCE_SPECTRUM_TREE_SHA256,
        "records": records,
        "by_family": by_family,
        "aggregate_sha256": aggregate,
        "expected_aggregate_sha256": EXPECTED_SOURCE_SPECTRUM_AGGREGATE_SHA256,
        "problems": problems,
    }


def source_spectrum_bundle_record() -> dict[str, Any]:
    snapshot = source_spectrum_authority_snapshot()
    if snapshot["status"] != "PASS":
        raise RuntimeError(
            f"source spectrum authority failed: {snapshot['problems']}"
        )
    return {
        "path": rel(SOURCE_SPECTRUM_ROOT),
        "size_bytes": snapshot["tree"]["total_bytes"],
        "sha256": snapshot["aggregate_sha256"],
        "files": snapshot["referenced_files"],
        "tree_sha256": snapshot["tree"]["tree_sha256"],
    }


def expected_particle_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(row.get("particle", "")) for row in rows))


def audit_source_cards() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    spectrum_authority = source_spectrum_authority_snapshot()
    if spectrum_authority["status"] != "PASS":
        problems.extend(
            f"source spectrum authority: {problem}"
            for problem in spectrum_authority["problems"]
        )
    manifest = (
        load_json(SOURCE_CARD_MANIFEST)
        if SOURCE_CARD_MANIFEST.is_file()
        else {}
    )
    manifest_sha = (
        sha256(SOURCE_CARD_MANIFEST) if SOURCE_CARD_MANIFEST.is_file() else None
    )
    if manifest_sha != EXPECTED_SOURCE_CARD_MANIFEST_SHA256:
        problems.append(
            f"source manifest sha256={manifest_sha} expected="
            f"{EXPECTED_SOURCE_CARD_MANIFEST_SHA256}"
        )
    if manifest.get("status") != "PASS_S3D_O8_ALL8_SOURCE_CARDS":
        problems.append(f"source manifest status={manifest.get('status')}")
    if manifest.get("problems"):
        problems.append(f"source manifest problems={manifest.get('problems')}")
    if manifest.get("geometry_setup") != GEOMETRY_REL:
        problems.append(
            f"source manifest geometry={manifest.get('geometry_setup')}"
        )
    if not math.isclose(
        float(manifest.get("farfield_radius_cm") or -1.0),
        FARFIELD_RADIUS_CM,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        problems.append(
            f"source manifest farfield={manifest.get('farfield_radius_cm')}"
        )
    expected_statistics_reference = (
        "10M gamma, 12 gamma splits, 8 replicas per non-gamma family"
    )
    if manifest.get("statistics_reference") != expected_statistics_reference:
        problems.append(
            f"source manifest statistics_reference={manifest.get('statistics_reference')}"
        )
    manifest_rows = manifest.get("sources") or []
    manifest_by_family = {
        str(row.get("particle")): row
        for row in manifest_rows
        if isinstance(row, dict) and row.get("particle")
    }
    if len(manifest_rows) != len(FAMILIES) or set(manifest_by_family) != set(
        FAMILIES
    ):
        problems.append(
            f"source manifest family set={sorted(manifest_by_family)} "
            f"expected={list(FAMILIES)}"
        )
    for tag in FAMILIES:
        card = SOURCE_CARDS / f"Background_{tag}_fullsphere20.source"
        text = card.read_text(encoding="utf-8", errors="replace") if card.is_file() else ""
        geoms = source_geometry(card) if card.is_file() else []
        manifest_row = manifest_by_family.get(tag) or {}
        current_sha = sha256(card) if card.is_file() else None
        ok = (
            card.is_file()
            and len(geoms) == 1
            and normalize_path(geoms[0]) == GEOMETRY.as_posix()
            and "StoreIsotopes true" in text
            and current_sha == EXPECTED_SOURCE_CARD_SHA256[tag]
            and manifest_row.get("source_sha256")
            == EXPECTED_SOURCE_CARD_SHA256[tag]
            and manifest_row.get("canonical_non_geometry_match") is True
            and not manifest_row.get("problems")
            and manifest_row.get("geometry_line_count") == 1
            and manifest_row.get("geometry_lines") == [GEOMETRY_REL]
        )
        if not ok:
            problems.append(
                f"{tag}: source card is not the hash-pinned retained-prompt authority"
            )
        rows.append(
            {
                "family": tag,
                "source": rel(card),
                "sha256": current_sha,
                "expected_sha256": EXPECTED_SOURCE_CARD_SHA256[tag],
                "manifest_row": manifest_row,
                "spectra": spectrum_authority["by_family"].get(tag, []),
                "geometry": geoms,
                "store_isotopes": "StoreIsotopes true" in text,
                "status": "PASS" if ok else "FAIL",
            }
        )
    return {
        "status": "PASS" if not problems else "FAIL",
        "source_dir": rel(SOURCE_CARDS),
        "retained_prompt_source_manifest": artifact_record(
            SOURCE_CARD_MANIFEST
        ),
        "retained_prompt_source_spectra": source_spectrum_bundle_record(),
        "expected_manifest_sha256": EXPECTED_SOURCE_CARD_MANIFEST_SHA256,
        "manifest_status": manifest.get("status"),
        "manifest_geometry_setup": manifest.get("geometry_setup"),
        "manifest_farfield_radius_cm": manifest.get("farfield_radius_cm"),
        "manifest_statistics_reference": manifest.get("statistics_reference"),
        "source_spectrum_authority": spectrum_authority,
        "rows": rows,
        "problems": problems,
    }


def audit_completed_run(run_dir: Path, mode: str) -> dict[str, Any]:
    summary_path = run_dir / "run_summary.json"
    norm_path = run_dir / "normalization.json"
    rows = load_json(summary_path) if summary_path.is_file() else []
    normalization = load_json(norm_path) if norm_path.is_file() else {}
    problems: list[str] = []
    counts = expected_particle_counts(rows)
    if len(rows) != EXPECTED_JOBS:
        problems.append(f"rows={len(rows)} expected={EXPECTED_JOBS}")
    if counts != EXPECTED_COUNTS:
        problems.append(f"particle_counts={counts} expected={EXPECTED_COUNTS}")
    generated = 0
    requested = 0
    header_rows: list[dict[str, Any]] = []
    for row in rows:
        name = str(row.get("job_name", ""))
        sim = path_from_row(str(row.get("sim_path", "")))
        dat = path_from_row(str(row.get("dat_path", "")))
        geometry = sim_geometry(sim)
        tts = tt_values(dat)
        requested_i = int(row.get("events") or 0)
        generated_i = int(row.get("generated_particles") or 0)
        requested += requested_i
        generated += generated_i
        local: list[str] = []
        if row.get("status") not in ("PASS", "SKIP"):
            local.append(f"status={row.get('status')}")
        if requested_i != generated_i:
            local.append(f"generated={generated_i} requested={requested_i}")
        if not sim.is_file() or not dat.is_file():
            local.append("missing SIM or DAT")
        if not geometry_header_matches(geometry, GEOMETRY):
            local.append(f"geometry={geometry}")
        if len(tts) != 1 or not math.isfinite(tts[0]) or tts[0] <= 0:
            local.append(f"TT={tts}")
        problems.extend(f"{name}: {item}" for item in local)
        header_rows.append(
            {
                "job_name": name,
                "family": row.get("particle"),
                "sim": rel(sim),
                "dat": rel(dat),
                "geometry": geometry,
                "tt_s": tts[0] if len(tts) == 1 else tts,
                "status": "PASS" if not local else "FAIL",
            }
        )
    if rows and requested != EXPECTED_EVENTS:
        problems.append(f"events_requested={requested} expected={EXPECTED_EVENTS}")
    if rows and generated != requested:
        problems.append(f"events_generated={generated} requested={requested}")
    return {
        "status": "PASS" if rows and not problems else "NOT_READY" if not rows else "FAIL",
        "mode": mode,
        "run_dir": rel(run_dir),
        "summary": rel(summary_path),
        "normalization": rel(norm_path),
        "jobs": len(rows),
        "particle_counts": counts,
        "events_requested": requested,
        "events_generated": generated,
        "selected_particles": normalization.get("selected_particles"),
        "headers": header_rows,
        "problems": problems,
    }


def retained_buildup_validation() -> dict[str, Any]:
    """Bind downstream source work to the retained 68-job PASS validation."""
    path = DATA / "s3d_o8_all8_buildup_validation.json"
    stored = load_json(path) if path.is_file() else {}
    current = audit_completed_run(BUILDUP_DIR, "buildup")
    problems: list[str] = []
    if stored.get("status") != "PASS":
        problems.append(f"stored buildup validation status={stored.get('status')}")
    if stored != current:
        problems.append(
            "stored buildup validation differs from the current 68-job summary/headers"
        )
    if (
        current.get("jobs") != EXPECTED_JOBS
        or current.get("events_generated") != EXPECTED_EVENTS
        or current.get("particle_counts") != EXPECTED_COUNTS
    ):
        problems.append(
            "current buildup jobs/events/family counts differ from the retained contract"
        )
    return {
        "status": "PASS" if not problems else "FAIL",
        "artifact": artifact_record(path),
        "stored": stored,
        "current": current,
        "problems": problems,
    }


def buildup_command(
    workers: int,
    prepare_only: bool,
    force: bool = False,
) -> list[str]:
    command = [
        sys.executable,
        str(RUN_EQUIV),
        "--mode",
        "buildup",
        "--source-dir",
        str(SOURCE_CARDS),
        "--outdir",
        str(BUILDUP_DIR),
        "--gamma-events",
        str(GAMMA_EVENTS),
        "--gamma-splits",
        str(GAMMA_SPLITS),
        "--non-gamma-replicas",
        str(NON_GAMMA_REPLICAS),
        "--farfield-radius-cm",
        str(FARFIELD_RADIUS_CM),
        "--workers",
        str(workers),
        "--keep-sources",
    ]
    if prepare_only:
        command.append("--prepare-sources-only")
    else:
        command.append("--allow-heavy-run")
    if force:
        command.append("--force")
    return command


def audit_prepared_buildup() -> dict[str, Any]:
    manifest = BUILDUP_DIR / "run_manifest.csv"
    normalization_path = BUILDUP_DIR / "normalization.json"
    rows = read_csv(manifest) if manifest.is_file() else []
    normalization = load_json(normalization_path) if normalization_path.is_file() else {}
    counts = expected_particle_counts(rows)
    problems: list[str] = []
    if len(rows) != EXPECTED_JOBS:
        problems.append(f"jobs={len(rows)} expected={EXPECTED_JOBS}")
    if counts != EXPECTED_COUNTS:
        problems.append(f"particle_counts={counts} expected={EXPECTED_COUNTS}")
    if sum(int(row.get("events") or 0) for row in rows) != EXPECTED_EVENTS:
        problems.append("event total differs from retained all-eight prompt exposure")
    seeds = [row.get("seed") for row in rows]
    if len(seeds) != len(set(seeds)):
        problems.append("job seeds are not globally unique")
    try:
        job_contract = sorted(
            (
                {
                    "job_name": str(row["job_name"]),
                    "particle": str(row["particle"]),
                    "events": int(row["events"]),
                    "rep": int(row["rep"]),
                    "part": int(row["part"]),
                    "seed": int(row["seed"]),
                }
                for row in rows
            ),
            key=lambda row: row["job_name"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        job_contract = []
        problems.append(f"cannot parse exact buildup job contract: {exc}")
    job_contract_sha = canonical_payload_sha256(job_contract)
    if job_contract_sha != EXPECTED_BUILDUP_JOB_CONTRACT_SHA256:
        problems.append(
            f"job contract sha256={job_contract_sha} expected="
            f"{EXPECTED_BUILDUP_JOB_CONTRACT_SHA256}"
        )
    family_event_totals = {
        tag: sum(
            int(row["events"])
            for row in job_contract
            if row["particle"] == tag
        )
        for tag in FAMILIES
    }
    if family_event_totals != EXPECTED_TOTAL_EVENTS_BY_FAMILY:
        problems.append(
            f"family event totals={family_event_totals} expected="
            f"{EXPECTED_TOTAL_EVENTS_BY_FAMILY}"
        )
    current_fluxes = normalization.get("flux_by_particle_cm2_s") or {}
    if current_fluxes != EXPECTED_SOURCE_FLUX_CM2_S:
        problems.append(
            f"source fluxes={current_fluxes} expected={EXPECTED_SOURCE_FLUX_CM2_S}"
        )
    current_base_events = normalization.get("base_events_by_particle") or {}
    if current_base_events != EXPECTED_BASE_EVENTS_BY_FAMILY:
        problems.append(
            f"base events={current_base_events} expected="
            f"{EXPECTED_BASE_EVENTS_BY_FAMILY}"
        )
    if normalization.get("gamma_splits") != GAMMA_SPLITS or normalization.get(
        "non_gamma_replicas"
    ) != NON_GAMMA_REPLICAS:
        problems.append(
            "normalization gamma-split/non-gamma-replica statistics differ"
        )
    source_rows: list[dict[str, Any]] = []
    for row in rows:
        card = path_from_row(row["temp_source"])
        text = card.read_text(encoding="utf-8", errors="replace") if card.is_file() else ""
        geoms = source_geometry(card) if card.is_file() else []
        ok = (
            card.is_file()
            and len(geoms) == 1
            and normalize_path(geoms[0]) == GEOMETRY.as_posix()
            and "DecayMode ActivationBuildUp" in text
            and "StoreIsotopes true" in text
        )
        if not ok:
            problems.append(f"invalid prepared source: {row.get('job_name')}")
        source_rows.append(
            {
                "job_name": row.get("job_name"),
                "family": row.get("particle"),
                "source": rel(card),
                "geometry": geoms,
                "activation_buildup": "DecayMode ActivationBuildUp" in text,
                "store_isotopes": "StoreIsotopes true" in text,
                "status": "PASS" if ok else "FAIL",
            }
        )
    return {
        "status": "PASS" if rows and not problems else "NOT_READY" if not rows else "FAIL",
        "run_dir": rel(BUILDUP_DIR),
        "manifest": rel(manifest),
        "normalization": rel(normalization_path),
        "normalization_selected_particles": normalization.get("selected_particles"),
        "jobs": len(rows),
        "particle_counts": counts,
        "events": sum(int(row.get("events") or 0) for row in rows),
        "job_contract": job_contract,
        "job_contract_sha256": job_contract_sha,
        "expected_job_contract_sha256": EXPECTED_BUILDUP_JOB_CONTRACT_SHA256,
        "family_event_totals": family_event_totals,
        "expected_family_event_totals": EXPECTED_TOTAL_EVENTS_BY_FAMILY,
        "source_flux_cm2_s": current_fluxes,
        "expected_source_flux_cm2_s": EXPECTED_SOURCE_FLUX_CM2_S,
        "base_events_by_family": current_base_events,
        "expected_base_events_by_family": EXPECTED_BASE_EVENTS_BY_FAMILY,
        "job_sources": source_rows,
        "problems": problems,
    }


def _prepare_locked(workers: int) -> dict[str, Any]:
    geometry = audit_geometry_authority()
    sources = audit_source_cards()
    prompt = audit_completed_run(PROMPT_DIR, "instant")
    env, megalib = cosima_environment()
    del env
    if sources["status"] != "PASS" or prompt["status"] != "PASS":
        raise SystemExit(
            "retained O8 geometry/source/prompt authority is not ready; inspect preflight"
        )
    run_command(
        buildup_command(workers, prepare_only=True),
        LOGS / "prepare_all8_buildup.log",
        pass_fds=authority_lock_pass_fds(),
    )
    buildup = audit_prepared_buildup()
    payload = {
        "status": "PASS_S3D_O8_ALL8_ACTIVATION_PREFLIGHT"
        if buildup["status"] == "PASS"
        else "FAIL_S3D_O8_ALL8_ACTIVATION_PREFLIGHT",
        "generated_at_utc": now_utc(),
        "geometry_setup": GEOMETRY_REL,
        "geometry_authority": geometry,
        "source_cards": sources,
        "retained_all8_prompt": prompt,
        "prepared_all8_buildup": buildup,
        "megalib_environment": megalib,
        "statistics": {
            "families": list(FAMILIES),
            "expected_jobs": EXPECTED_JOBS,
            "expected_events": EXPECTED_EVENTS,
            "gamma_splits": GAMMA_SPLITS,
            "non_gamma_replicas": NON_GAMMA_REPLICAS,
            "m_exact_pointsource_blocks_per_nonzero_family": M_BLOCKS,
            "delayed_triggers_per_nonzero_family": RAW_TRIGGERS,
            "seed": SEED,
        },
        "claim_boundary": (
            "Preparation only. No all-family delayed-rate claim is valid until all "
            "nonzero family transports and downstream response/mission closure pass."
        ),
    }
    write_json(PREFLIGHT, payload)
    if not payload["status"].startswith("PASS"):
        raise SystemExit("all-eight buildup preflight failed")
    return payload


def prepare(workers: int) -> dict[str, Any]:
    with exclusive_source_transport_authority_lock("prepare"):
        return _prepare_locked(workers)


def require_confirmation(args: argparse.Namespace, stage: str) -> None:
    expected = CONFIRM_TOKENS[stage]
    if not args.allow_heavy_run or args.confirm != expected:
        raise SystemExit(
            f"{stage} requires --allow-heavy-run --confirm {expected}"
        )


def _run_buildup_locked(args: argparse.Namespace) -> dict[str, Any]:
    if not PREFLIGHT.is_file() or not str(load_json(PREFLIGHT).get("status", "")).startswith("PASS"):
        _prepare_locked(args.workers)
    env, _evidence = cosima_environment()
    run_command(
        buildup_command(args.workers, prepare_only=False, force=args.force),
        LOGS / "run_all8_buildup.log",
        env,
        pass_fds=authority_lock_pass_fds(),
    )
    result = audit_completed_run(BUILDUP_DIR, "buildup")
    write_json(DATA / "s3d_o8_all8_buildup_validation.json", result)
    if result["status"] != "PASS":
        raise SystemExit("all-eight buildup transport failed validation")
    return result


def run_buildup(args: argparse.Namespace) -> dict[str, Any]:
    with exclusive_source_transport_authority_lock("run-buildup"):
        return _run_buildup_locked(args)


def family_rows(run_dir: Path, tag: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [row for row in load_json(run_dir / "run_summary.json") if row.get("particle") == tag]
    normalization = dict(load_json(run_dir / "normalization.json"))
    normalization["outdir"] = rel(run_dir)
    normalization["selected_particles"] = [tag]
    normalization["jobs"] = len(rows)
    normalization["family_view_of"] = rel(run_dir)
    return rows, normalization


def materialize_family_view(tag: str) -> tuple[Path, Path]:
    prompt_view = VIEW_ROOT / tag / "instant"
    buildup_view = VIEW_ROOT / tag / "buildup"
    for source_dir, view_dir in ((PROMPT_DIR, prompt_view), (BUILDUP_DIR, buildup_view)):
        rows, normalization = family_rows(source_dir, tag)
        view_dir.mkdir(parents=True, exist_ok=True)
        normalization["outdir"] = rel(view_dir)
        normalization["family_view_of"] = rel(source_dir)
        write_json(view_dir / "run_summary.json", rows)
        write_json(view_dir / "normalization.json", normalization)
        for row in rows:
            for key in ("sim_path", "dat_path"):
                target = path_from_row(str(row[key])).resolve()
                link = view_dir / target.name
                if link.is_symlink() and link.resolve() == target:
                    continue
                if link.exists() or link.is_symlink():
                    raise RuntimeError(f"family view collision: {rel(link)}")
                link.symlink_to(target)
    return prompt_view, buildup_view


def raw_rp_total(tag: str) -> dict[str, Any]:
    files = sorted(BUILDUP_DIR.glob(f"Background_{tag}_*.dat.inc1.dat"))
    rp_total = 0.0
    tt: list[float] = []
    for path in files:
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = RP_RE.match(raw)
            if match:
                rp_total += float(match.group(3))
            tmatch = TT_RE.match(raw)
            if tmatch:
                tt.append(float(tmatch.group(1)))
    division = float(len(files))
    return {
        "family": tag,
        "files": len(files),
        "division": division,
        "tt_lines": len(tt),
        "tt_mean_s": sum(tt) / len(tt) if tt else None,
        "rp_raw_total": rp_total,
        "rp_scaled_total": rp_total / division if division else 0.0,
        "zero_production": rp_total <= 0.0,
    }


def family_raw_dir(tag: str) -> Path:
    return RAW_ROOT / tag


def family_fix_dir(tag: str) -> Path:
    return FIX_ROOT / tag


def family_exact_dir(tag: str) -> Path:
    return EXACT_ROOT / tag


def family_transport_dir(tag: str) -> Path:
    return TRANSPORT_ROOT / tag


def family_transport_launch_path(tag: str) -> Path:
    return family_transport_dir(tag) / "transport_launch_provenance.json"


@contextmanager
def exclusive_family_transport_lock(tag: str):
    transport_dir = family_transport_dir(tag)
    transport_dir.mkdir(parents=True, exist_ok=True)
    lock_path = transport_dir / ".transport.lock"
    launch_nonce = uuid.uuid4().hex
    with lock_path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(
                f"{tag} transport is already locked by another process: {rel(lock_path)}"
            ) from exc
        try:
            yield {
                "path": rel(lock_path),
                "launch_nonce": launch_nonce,
                "inherited_fd": handle.fileno(),
            }
        finally:
            # Do not call LOCK_UN: Cosima inherits this same open-file
            # description.  Closing only the parent's descriptor leaves the
            # lock held until the last orphan/child descriptor closes.
            pass


@contextmanager
def exclusive_source_transport_authority_lock(stage: str):
    global _CURRENT_AUTHORITY_LOCK_FD, _CURRENT_AUTHORITY_LOCK_EVIDENCE
    AUTHORITY_LOCK.parent.mkdir(parents=True, exist_ok=True)
    nonce = uuid.uuid4().hex
    with AUTHORITY_LOCK.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(
                "another prepare/run process holds the all-family buildup/source/"
                f"transport authority lock: {rel(AUTHORITY_LOCK)}"
            ) from exc
        evidence = {
            "path": rel(AUTHORITY_LOCK),
            "stage": stage,
            "nonce": nonce,
            "inherited_fd": handle.fileno(),
        }
        if _CURRENT_AUTHORITY_LOCK_FD is not None:
            raise RuntimeError("authority-lock context re-entry is forbidden")
        _CURRENT_AUTHORITY_LOCK_FD = handle.fileno()
        _CURRENT_AUTHORITY_LOCK_EVIDENCE = evidence
        try:
            yield evidence
        finally:
            _CURRENT_AUTHORITY_LOCK_FD = None
            _CURRENT_AUTHORITY_LOCK_EVIDENCE = None
            # As above, close only the parent's descriptor on context exit.
            # An inherited Cosima descriptor must continue to hold the lock.
            pass


def family_report_dir(tag: str) -> Path:
    return REPORT_ROOT / tag


def family_source_prefix(tag: str) -> Path:
    camel = {"eminus": "EMinus", "eplus": "EPlus", "muminus": "MuMinus", "muplus": "MuPlus"}.get(tag, tag.capitalize())
    return family_transport_dir(tag) / f"DelayedDecayS3dO8{camel}M50000"


def family_buildup_provenance_path(tag: str) -> Path:
    return DATA / f"s3d_o8_{tag}_buildup_input_provenance.json"


def family_prepared_source_authority_path(tag: str) -> Path:
    return DATA / f"s3d_o8_{tag}_prepared_source_authority.json"


TRANSPORT_MUTABLE_MANIFEST_FIELDS = {
    "boundary",
    "claim_level",
    "delayed_transport",
    "problems",
    "status",
}


def manifest_source_contract(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in manifest.items()
        if key not in TRANSPORT_MUTABLE_MANIFEST_FIELDS
    }


def family_buildup_provenance(tag: str) -> dict[str, Any]:
    summary_path = BUILDUP_DIR / "run_summary.json"
    normalization_path = BUILDUP_DIR / "normalization.json"
    rows = load_json(summary_path) if summary_path.is_file() else []
    selected = sorted(
        (row for row in rows if row.get("particle") == tag),
        key=lambda row: str(row.get("job_name")),
    )
    artifacts: list[dict[str, Any]] = []
    problems: list[str] = []
    for row in selected:
        job_name = str(row.get("job_name"))
        sim = path_from_row(str(row.get("sim_path") or ""))
        dat = path_from_row(str(row.get("dat_path") or ""))
        source = BUILDUP_DIR / "job_sources" / f"{job_name}.source"
        record = {
            "job_name": job_name,
            "sim": artifact_record(sim),
            "dat": artifact_record(dat),
            "source": artifact_record(source),
        }
        artifacts.append(record)
        if any(
            not (record[name] or {}).get("sha256")
            for name in ("sim", "dat", "source")
        ):
            problems.append(f"{job_name}: one or more buildup artifacts are missing")
    if len(selected) != EXPECTED_COUNTS[tag]:
        problems.append(
            f"jobs={len(selected)} expected={EXPECTED_COUNTS[tag]} for {tag}"
        )
    payload = {
        "status": "PASS" if not problems else "FAIL",
        "family": tag,
        "jobs": len(selected),
        "run_summary": artifact_record(summary_path),
        "normalization": artifact_record(normalization_path),
        "job_artifacts": artifacts,
        "problems": problems,
    }
    payload["canonical_payload_sha256"] = canonical_payload_sha256(payload)
    return payload


def expected_family_source_provenance(
    tag: str,
    *,
    geometry_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bundle = geometry_bundle if geometry_bundle is not None else geometry_bundle_snapshot()
    exact_dir = family_exact_dir(tag)
    return {
        "buildup_inputs": artifact_record(family_buildup_provenance_path(tag)),
        "raw_source": artifact_record(
            family_raw_dir(tag) / "activation_decay_day15.source"
        ),
        "inventory": artifact_record(
            family_raw_dir(tag) / "activation_inventory_day15.csv"
        ),
        "raw_half_life_cache": artifact_record(
            family_raw_dir(tag) / "half_life_cache.json"
        ),
        "raw_normalization_json": artifact_record(
            family_raw_dir(tag) / "normalization_audit_day15.json"
        ),
        "raw_normalization_csv": artifact_record(
            family_raw_dir(tag) / "normalization_audit_day15.csv"
        ),
        "raw_no_rpip_points": artifact_record(
            family_raw_dir(tag) / "no_rpip_points_day15.csv"
        ),
        "raw_unknown_isotopes": artifact_record(
            family_raw_dir(tag) / "unknown_isotopes_day15.csv"
        ),
        "fixed_source": artifact_record(
            family_fix_dir(tag) / "activation_decay_day15_groundstate_fixed.source"
        ),
        "fixed_summary": artifact_record(
            family_fix_dir(tag) / "source_fix_summary.json"
        ),
        "groundstate_corrections": artifact_record(
            family_fix_dir(tag) / "groundstate_activity_corrections.csv"
        ),
        "fixed_normalization": artifact_record(
            family_fix_dir(tag) / "normalization_audit_groundstate_fix.json"
        ),
        "fixed_normalization_csv": artifact_record(
            family_fix_dir(tag) / "normalization_audit_groundstate_fix.csv"
        ),
        "fixed_removed_or_rescaled": artifact_record(
            family_fix_dir(tag) / "removed_or_rescaled_sources.csv"
        ),
        "volume_map_audit": artifact_record(
            DATA / f"s3d_o8_{tag}_volume_map_audit.json"
        ),
        "activity_completeness_audit": artifact_record(
            DATA / f"s3d_o8_{tag}_activity_completeness_audit.json"
        ),
        "exact_source": artifact_record(
            exact_dir / "activation_decay_day15_groundstate_fixed_exactpos_m50000.source"
        ),
        "weighted_table": artifact_record(
            exact_dir / f"exactpos_weighted_rpip_table_m50000_s{SEED}.csv"
        ),
        "nubase": nubase_authority_record(),
        "retained_prompt_source_manifest": artifact_record(
            SOURCE_CARD_MANIFEST
        ),
        "retained_prompt_source_spectra": source_spectrum_bundle_record(),
        "code_activation_harness": artifact_record(ACTIVATION_HARNESS),
        "code_makedecay_wrapper": artifact_record(MAKE_RPIP),
        "code_makedecay_helper": artifact_record(MAKE_RPIP_HELPER),
        "code_fixed_wrapper": artifact_record(FIX_SOURCE),
        "code_fixed_helper": artifact_record(FIX_HELPER),
        "code_exactpos_helper": artifact_record(EXACTPOS_HELPER),
        "code_volume_map": artifact_record(VOLUME_MAP_CODE),
        "code_o8_replay_common": artifact_record(O8_REPLAY_COMMON),
        "code_shared_replay_common": artifact_record(SHARED_REPLAY_COMMON),
        **bundle["artifacts"],
    }


def current_prepared_source_authority(
    tag: str,
    expected_family_status: str,
) -> dict[str, Any]:
    nubase_authority_record()
    production = raw_rp_total(tag)
    buildup_path = family_buildup_provenance_path(tag)
    volume_path = DATA / f"s3d_o8_{tag}_volume_map_audit.json"
    volume_audit = load_json(volume_path) if volume_path.is_file() else {}
    problems: list[str] = []
    payload: dict[str, Any] = {
        "schema_version": 1,
        "family": tag,
        "family_source_status": expected_family_status,
        "production": production,
        "buildup_input_provenance": artifact_record(buildup_path),
        "volume_map_audit": artifact_record(volume_path),
    }
    if not (payload["buildup_input_provenance"] or {}).get("sha256"):
        problems.append("buildup-input provenance artifact is missing")
    if volume_audit.get("status") != "PASS":
        problems.append(f"volume-map status={volume_audit.get('status')}")
    if expected_family_status == "PASS_ZERO_PRODUCTION":
        if not production.get("zero_production"):
            problems.append("family is not zero-production in current DAT files")
        payload.update(
            {
                "activity_Bq": 0.0,
                "exact_manifest_source_contract": None,
                "exact_manifest_source_contract_sha256": None,
                "source_provenance": None,
                "exact_source_flux_audit": None,
            }
        )
    else:
        manifest_path = (
            family_exact_dir(tag)
            / f"s3d_o8_{tag}_exactpos_m50000_s{SEED}_manifest.json"
        )
        manifest = load_json(manifest_path) if manifest_path.is_file() else {}
        fixed_summary_path = family_fix_dir(tag) / "source_fix_summary.json"
        fixed_summary = (
            load_json(fixed_summary_path) if fixed_summary_path.is_file() else {}
        )
        activity_audit_path = DATA / f"s3d_o8_{tag}_activity_completeness_audit.json"
        activity_audit = (
            load_json(activity_audit_path)
            if activity_audit_path.is_file()
            else {}
        )
        fixed_total = float(manifest.get("fixed_total_activity_Bq") or 0.0)
        exact_source_path = (
            family_exact_dir(tag)
            / "activation_decay_day15_groundstate_fixed_exactpos_m50000.source"
        )
        exact_flux = exact_source_flux_audit(
            exact_source_path,
            expected_total_activity_bq=fixed_total,
        )
        geometry_bundle = geometry_bundle_snapshot()
        current_provenance = expected_family_source_provenance(
            tag, geometry_bundle=geometry_bundle
        )
        source_contract = manifest_source_contract(manifest)
        activity_values = {
            "manifest_fixed_total": fixed_total,
            "fixed_summary": float(
                fixed_summary.get("new_total_activity_Bq") or 0.0
            ),
            "audit_expected_ground": float(
                activity_audit.get("expected_ground_activity_Bq") or 0.0
            ),
            "audit_fixed_source": float(
                activity_audit.get("fixed_source_activity_Bq") or 0.0
            ),
            "audit_fixed_summary": float(
                activity_audit.get("source_fix_summary_activity_Bq") or 0.0
            ),
            "M_times_unrounded_flux": float(
                manifest.get("flux_per_pointsource_Bq") or 0.0
            )
            * M_BLOCKS,
        }
        if expected_family_status != "PASS":
            problems.append(
                f"positive family expected source status={expected_family_status}"
            )
        if production.get("zero_production") or fixed_total <= 0.0:
            problems.append("positive source authority has zero production/activity")
        if manifest.get("source_provenance") != current_provenance:
            problems.append("manifest source provenance differs from current bytes")
        if manifest.get("geometry_bundle_authority") != geometry_bundle:
            problems.append("manifest geometry bundle differs from retained authority")
        if manifest.get("exact_source_flux_audit") != exact_flux:
            problems.append("manifest exact-source Flux audit differs from current text")
        if exact_flux.get("status") != "PASS" or exact_flux.get("problems"):
            problems.append(f"exact-source Flux audit={exact_flux}")
        if activity_audit.get("status") != "PASS" or activity_audit.get("problems"):
            problems.append(f"activity completeness audit={activity_audit}")
        fixed_source_tolerance = max(
            1e-9,
            float(activity_audit.get("absolute_tolerance_Bq") or 0.0),
        )
        precise_activity_values = {
            key: value
            for key, value in activity_values.items()
            if key != "audit_fixed_source"
        }
        if any(
            not math.isclose(value, fixed_total, rel_tol=0.0, abs_tol=1e-9)
            for value in precise_activity_values.values()
        ) or not math.isclose(
            activity_values["audit_fixed_source"],
            fixed_total,
            rel_tol=0.0,
            abs_tol=fixed_source_tolerance,
        ):
            problems.append(
                "prepared activity closure failed: "
                f"values={activity_values} fixed_source_tolerance_Bq={fixed_source_tolerance}"
            )
        recorded_delta = float(
            manifest.get("source_text_flux_abs_delta_Bq") or 0.0
        )
        derived_delta = float(
            exact_flux.get("independently_derived_rounding_delta_Bq") or 0.0
        )
        bound = float(exact_flux.get("max_rounding_delta_bound_Bq") or 0.0)
        if not math.isclose(
            recorded_delta, derived_delta, rel_tol=0.0, abs_tol=1e-12
        ) or recorded_delta > bound + 1e-15:
            problems.append("serialized Flux rounding delta is not independently closed")
        payload.update(
            {
                "activity_Bq": fixed_total,
                "activity_closure_Bq": activity_values,
                "exact_manifest_path": rel(manifest_path),
                "exact_manifest_source_contract": source_contract,
                "exact_manifest_source_contract_sha256": canonical_payload_sha256(
                    source_contract
                ),
                "source_provenance": current_provenance,
                "exact_source_flux_audit": exact_flux,
            }
        )
    payload["status"] = "PASS_PREPARED_SOURCE_AUTHORITY" if not problems else "FAIL_PREPARED_SOURCE_AUTHORITY"
    payload["problems"] = problems
    payload["canonical_payload_sha256"] = canonical_payload_sha256(payload)
    return payload


def transport_launch_inputs(
    tag: str,
    source: Path,
    cosima_executable: str,
    runtime_dependencies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if runtime_dependencies is None:
        runtime_env, runtime_evidence = cosima_environment()
        if str(runtime_evidence["cosima"]) != cosima_executable:
            raise RuntimeError(
                "current Cosima executable differs from the launch command"
            )
        runtime_dependencies = runtime_dependency_snapshot(
            runtime_env, runtime_evidence
        )
    command = [cosima_executable, "-s", str(SEED), str(source)]
    return {
        "family": tag,
        "seed_requested": SEED,
        "command": command,
        "source": artifact_record(source),
        "source_geometry": source_geometry(source),
        "geometry_bundle": geometry_bundle_snapshot(),
        "runtime_dependencies": runtime_dependencies,
    }


def transport_summary_contract(
    transport: dict[str, Any],
    sim: Path,
    sim_parse: dict[str, Any] | None = None,
) -> dict[str, Any]:
    parsed = sim_parse if sim_parse is not None else parse_sim_transport(sim)
    return {
        "independent_sim_parse": parsed,
        "manifest_summary": {
            "path": rel(sim),
            "SE": transport.get("SE"),
            "ID": transport.get("ID"),
            "TS": transport.get("TS"),
            "TS_value": transport.get("TS_value"),
            "TE_s": transport.get("TE_s"),
            "geometry": transport.get("geometry"),
            "status": transport.get("status"),
        },
    }


def audit_transport_launch_contract(
    tag: str,
    source: Path,
    sim: Path,
    transport: dict[str, Any],
    cosima_executable: str,
    runtime_dependencies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail closed unless a current SIM matches its generation-time inputs."""
    sidecar_path = family_transport_launch_path(tag)
    sidecar = load_json(sidecar_path) if sidecar_path.is_file() else {}
    problems: list[str] = []
    try:
        current_inputs = transport_launch_inputs(
            tag,
            source,
            cosima_executable,
            runtime_dependencies=runtime_dependencies,
        )
    except Exception as exc:  # preserve an auditable FAIL rather than a traceback-only gate
        current_inputs = {}
        problems.append(f"cannot establish current launch inputs: {exc}")
    if not sidecar:
        problems.append("generation-time launch provenance sidecar is missing")
    elif sidecar.get("status") != "PASS":
        problems.append(f"launch sidecar status={sidecar.get('status')} expected=PASS")
    lock_evidence = sidecar.get("exclusive_lock") or {}
    if lock_evidence.get("path") != rel(
        family_transport_dir(tag) / ".transport.lock"
    ) or not re.fullmatch(r"[0-9a-f]{32}", str(lock_evidence.get("launch_nonce") or "")):
        problems.append("family-exclusive lock path/launch nonce is absent or invalid")
    authority_lock_evidence = sidecar.get("authority_lock") or {}
    if authority_lock_evidence.get("path") != rel(
        AUTHORITY_LOCK
    ) or not re.fullmatch(
        r"[0-9a-f]{32}", str(authority_lock_evidence.get("nonce") or "")
    ):
        problems.append("global-authority lock path/nonce is absent or invalid")
    if sidecar.get("launch_inputs") != current_inputs:
        problems.append("launch-time inputs differ from current source/seed/geometry/Cosima")
    if sidecar.get("post_launch_inputs") != sidecar.get("launch_inputs"):
        problems.append("launch before/after runtime/source inputs are not identical")
    current_sim = artifact_record(sim)
    if sidecar.get("sim") != current_sim:
        problems.append("launch sidecar SIM artifact differs from current SIM")
    current_header = sim_header_metadata(sim)
    if sidecar.get("sim_header") != current_header:
        problems.append("launch sidecar SIM header differs from current SIM header")
    current_sim_parse = parse_sim_transport(sim)
    current_summary = transport_summary_contract(
        transport, sim, sim_parse=current_sim_parse
    )
    if sidecar.get("transport_summary") != current_summary:
        problems.append("launch sidecar transport summary differs from current SIM parse")
    if current_header.get("seed") != SEED:
        problems.append(f"SIM header seed={current_header.get('seed')} expected={SEED}")
    if not geometry_header_matches(current_header.get("geometry"), GEOMETRY):
        problems.append(f"SIM header geometry={current_header.get('geometry')}")
    if current_sim_parse.get("status") != "PASS":
        problems.append(f"independent SIM parse={current_sim_parse}")
    for key in ("SE", "ID", "TE_s", "geometry", "seed"):
        manifest_value = (
            transport.get(key)
            if key not in ("geometry", "seed")
            else transport.get("header_geometry" if key == "geometry" else "seed")
        )
        if manifest_value != current_sim_parse.get(key):
            problems.append(
                f"manifest/header {key}={manifest_value} differs from independent SIM parse={current_sim_parse.get(key)}"
            )
    if transport.get("TS") != current_sim_parse.get("TS_records"):
        problems.append(
            f"manifest TS={transport.get('TS')} differs from independent TS records={current_sim_parse.get('TS_records')}"
        )
    if transport.get("TS_value") != current_sim_parse.get("TS_value"):
        problems.append(
            f"manifest TS_value={transport.get('TS_value')} differs from independent SIM parse={current_sim_parse.get('TS_value')}"
        )
    return {
        "status": "PASS" if not problems else "FAIL",
        "path": rel(sidecar_path),
        "artifact": artifact_record(sidecar_path),
        "launch_inputs": sidecar.get("launch_inputs"),
        "sim": sidecar.get("sim"),
        "sim_header": sidecar.get("sim_header"),
        "transport_summary": sidecar.get("transport_summary"),
        "independent_sim_parse": current_sim_parse,
        "problems": problems,
    }


def family_raw_source(tag: str, workers: int, force: bool) -> dict[str, Any]:
    production = raw_rp_total(tag)
    if production["zero_production"]:
        return {
            "status": "PASS_ZERO_PRODUCTION",
            "family": tag,
            "production": production,
        }
    outdir = family_raw_dir(tag)
    marker = outdir / "activation_decay_day15.source"
    if force or not marker.is_file():
        command = [
            sys.executable,
            str(MAKE_RPIP),
            "--dat",
            str(BUILDUP_DIR / f"Background_{tag}_*.dat.inc1.dat"),
            "--sim",
            str(BUILDUP_DIR / f"Background_{tag}_*.inc1.id1.sim.gz"),
            "--geo",
            GEOMETRY_REL,
            "--non-gamma-div",
            str(NON_GAMMA_DIV),
            "--gamma-div",
            "auto",
            "--t-ground-days",
            "0",
            "--t-flight-days",
            str(T_FLIGHT_DAYS),
            "--t-after-days",
            "0",
            "--outdir",
            str(outdir),
            "--outfile-prefix",
            str(outdir / f"DelayedDecayRawS3dO8_{tag}"),
            "--triggers",
            str(RAW_TRIGGERS),
            "--z-bins",
            "60",
            "--r-bins",
            "100",
            "--min-points",
            "1",
            "--n-sample",
            str(N_SAMPLE),
            "--workers",
            str(workers),
            "--nubase",
            str(NUBASE),
            "--seed",
            str(SEED),
        ]
        run_command(
            command,
            LOGS / f"build_raw_{tag}.log",
            pass_fds=authority_lock_pass_fds(),
        )
    return {
        "status": "PASS" if marker.is_file() else "FAIL",
        "family": tag,
        "production": production,
        "raw_source": rel(marker),
        "normalization_audit": rel(outdir / "normalization_audit_day15.json"),
        "inventory": rel(outdir / "activation_inventory_day15.csv"),
        "no_rpip_points": rel(outdir / "no_rpip_points_day15.csv"),
    }


def family_volume_map_audit(tag: str) -> dict[str, Any]:
    dat_files = sorted(BUILDUP_DIR.glob(f"Background_{tag}_*.dat.inc1.dat"))
    sim_files = sorted(BUILDUP_DIR.glob(f"Background_{tag}_*.inc1.id1.sim.gz"))
    payload = {
        "family": tag,
        **audit_volume_map(dat_files, sim_files, GEOMETRY_COPY_MAP),
    }
    path = DATA / f"s3d_o8_{tag}_volume_map_audit.json"
    write_json(path, payload)
    if payload["status"] != "PASS":
        raise SystemExit(
            f"{tag} logical/physical volume map failed; inspect {rel(path)}"
        )
    return payload


def family_fixed_source(tag: str, force: bool) -> dict[str, Any]:
    production = raw_rp_total(tag)
    if production["zero_production"]:
        return {
            "status": "PASS_ZERO_PRODUCTION",
            "family": tag,
            "production": production,
            "activity_Bq": 0.0,
        }
    outdir = family_fix_dir(tag)
    marker = outdir / "activation_decay_day15_groundstate_fixed.source"
    if force or not marker.is_file():
        command = [
            sys.executable,
            str(FIX_SOURCE),
            "--source",
            str(family_raw_dir(tag) / "activation_decay_day15.source"),
            "--dat-glob",
            str(BUILDUP_DIR / f"Background_{tag}_*.dat.inc1.dat"),
            "--nubase",
            str(NUBASE),
            "--outdir",
            str(outdir),
            "--outfile-prefix",
            str(outdir / f"DelayedDecayFixedS3dO8_{tag}"),
            "--output-source-name",
            marker.name,
            "--triggers",
            str(RAW_TRIGGERS),
            "--geometry",
            str(GEOMETRY),
            "--non-gamma-div",
            str(NON_GAMMA_DIV),
            "--gamma-div",
            "auto",
            "--t-flight-days",
            str(T_FLIGHT_DAYS),
        ]
        run_command(
            command,
            LOGS / f"build_fixed_{tag}.log",
            pass_fds=authority_lock_pass_fds(),
        )
    audit_path = outdir / "normalization_audit_groundstate_fix.json"
    summary_path = outdir / "source_fix_summary.json"
    audit = load_json(audit_path) if audit_path.is_file() else {}
    summary = load_json(summary_path) if summary_path.is_file() else {}
    rows = audit.get("rows") or []
    expected_files = EXPECTED_COUNTS[tag]
    problems = list(audit.get("problems") or [])
    if audit.get("status") != "PASS":
        problems.append(f"normalization_status={audit.get('status')}")
    if len(rows) != 1 or rows[0].get("tag") != tag:
        problems.append(f"normalization_rows={rows}")
    elif any(
        float(rows[0].get(key, -1)) != expected
        for key, expected in (
            ("files", expected_files),
            ("division", float(expected_files)),
            ("tt_count", expected_files),
            ("tt_files", expected_files),
            ("tt_line_count", expected_files),
        )
    ):
        problems.append(f"TT/division guard failed: {rows[0]}")
    geoms = source_geometry(marker) if marker.is_file() else []
    if len(geoms) != 1 or normalize_path(geoms[0]) != GEOMETRY.as_posix():
        problems.append(f"fixed source geometry={geoms}")
    activity = float(summary.get("new_total_activity_Bq") or 0.0)
    completeness = (
        family_activity_completeness(tag, marker, summary)
        if marker.is_file()
        else {"status": "FAIL", "problems": ["fixed source is missing"]}
    )
    if completeness["status"] != "PASS":
        problems.append(
            "independent DAT/NUBASE activity completeness audit failed: "
            + "; ".join(completeness.get("problems") or [])
        )
    return {
        "status": "PASS" if not problems else "FAIL",
        "family": tag,
        "production": production,
        "fixed_source": rel(marker),
        "source_fix_summary": rel(summary_path),
        "normalization_audit": rel(audit_path),
        "normalization_rows": rows,
        "activity_Bq": activity,
        "activity_completeness": completeness,
        "problems": problems,
    }


def load_exactpos(tag: str):
    name = f"s3d_o8_all8_exactpos_{tag}"
    spec = importlib.util.spec_from_file_location(name, EXACTPOS_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load exact-position helper: {EXACTPOS_HELPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_fixed_helper(tag: str):
    """Load the shared NUBASE activity implementation for an independent audit."""
    name = f"s3d_o8_all8_fixed_audit_{tag}"
    spec = importlib.util.spec_from_file_location(name, FIX_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load fixed-source helper: {FIX_HELPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    module.canon_vn = canonicalize_volume
    return module


def family_activity_completeness(
    tag: str,
    fixed_source: Path,
    source_summary: dict[str, Any],
) -> dict[str, Any]:
    """Prove that every positive day-15 ground-state activity reached the source.

    The source builder starts from RPIP-positioned blocks.  This independent
    calculation starts from every ground-state ``RP`` record in the family DAT
    authority, applies the same per-family division, mean TT, NUBASE-2020
    half-life, and 15-day exposure, then compares the result key by key with the
    final fixed source.  It therefore catches a real isotope/volume activity
    that could otherwise disappear because no RPIP block was emitted.
    """
    dat_files = sorted(BUILDUP_DIR.glob(f"Background_{tag}_*.dat.inc1.dat"))
    configure_volume_map(logical_volumes_from_dat(dat_files), GEOMETRY_COPY_MAP)
    module = load_fixed_helper(tag)
    ground_hl = module.load_nubase_ground_half_lives(NUBASE)
    tt_by_tag, rp, normalization, normalization_problems = module.parse_rp_from_dat(
        dat_files,
        float(NON_GAMMA_DIV),
        "auto",
        False,
    )

    expected_by_key: dict[tuple[str, int], float] = defaultdict(float)
    yield_by_key: dict[tuple[str, int], float] = defaultdict(float)
    missing_nubase: list[dict[str, Any]] = []
    for (incident, vn, za, excitation), produced in rp.items():
        if excitation != 0.0 or produced <= 0.0:
            continue
        key = (vn, int(za))
        yield_by_key[key] += float(produced)
        info = ground_hl.get(int(za))
        if info is None:
            missing_nubase.append(
                {
                    "family": incident,
                    "VN": vn,
                    "ZA": int(za),
                    "scaled_RP_yield": float(produced),
                }
            )
            continue
        expected_by_key[key] += module.activity_after_exposure(
            float(produced),
            float(tt_by_tag.get(incident, 0.0)),
            float(info["half_life_s"]),
            T_FLIGHT_DAYS,
        )

    _lines, _name_za, name_flux, name_key = module.parse_source(fixed_source)
    observed_by_key: dict[tuple[str, int], float] = defaultdict(float)
    for name, key in name_key.items():
        observed_by_key[key] += float(name_flux.get(name, 0.0))

    raw_blocks_by_key: Counter[tuple[str, int]] = Counter()
    raw_source_value = source_summary.get("source_in")
    raw_source = Path(str(raw_source_value)) if raw_source_value else Path()
    if raw_source_value and not raw_source.is_absolute():
        raw_source = ROOT / raw_source
    if raw_source_value and raw_source.is_file():
        _raw_lines, _raw_name_za, _raw_flux, raw_name_key = module.parse_source(
            raw_source
        )
        raw_blocks_by_key.update(raw_name_key.values())

    expected_total = sum(expected_by_key.values())
    observed_total = sum(observed_by_key.values())
    summary_total = float(source_summary.get("new_total_activity_Bq") or 0.0)
    min_flux_bq = float(source_summary.get("min_flux_bq") or 0.0)
    explicit_removal_bound_bq = (
        float(source_summary.get("source_blocks_in") or 0) * min_flux_bq
    )
    absolute_tolerance_bq = max(
        1.0e-9,
        expected_total * 1.0e-8,
        explicit_removal_bound_bq * 1.000001,
    )
    key_rows: list[dict[str, Any]] = []
    for key in sorted(set(expected_by_key) | set(observed_by_key)):
        expected = expected_by_key.get(key, 0.0)
        observed = observed_by_key.get(key, 0.0)
        delta = observed - expected
        key_tolerance = max(
            1.0e-12,
            abs(expected) * 1.0e-8,
            raw_blocks_by_key.get(key, 0) * min_flux_bq * 1.000001,
        )
        if abs(delta) > key_tolerance:
            key_rows.append(
                {
                    "VN": key[0],
                    "ZA": key[1],
                    "scaled_RP_yield": yield_by_key.get(key, 0.0),
                    "expected_ground_activity_Bq": expected,
                    "fixed_source_activity_Bq": observed,
                    "delta_Bq": delta,
                    "tolerance_Bq": key_tolerance,
                }
            )

    problems = list(normalization_problems)
    if missing_nubase:
        problems.append(
            f"positive ground-state RP keys missing NUBASE records: {len(missing_nubase)}"
        )
    if abs(observed_total - expected_total) > absolute_tolerance_bq:
        problems.append(
            "fixed-source total does not close to the independent DAT/NUBASE total"
        )
    if abs(summary_total - observed_total) > absolute_tolerance_bq:
        problems.append("source-fix summary total does not match parsed fixed source")
    if key_rows:
        problems.append(f"activity keys outside tolerance: {len(key_rows)}")

    payload = {
        "status": "PASS" if not problems else "FAIL",
        "family": tag,
        "dat_files": len(dat_files),
        "normalization": normalization,
        "expected_ground_activity_Bq": expected_total,
        "fixed_source_activity_Bq": observed_total,
        "source_fix_summary_activity_Bq": summary_total,
        "delta_Bq": observed_total - expected_total,
        "absolute_tolerance_Bq": absolute_tolerance_bq,
        "explicit_subthreshold_removal_bound_Bq": explicit_removal_bound_bq,
        "expected_activity_keys": len(expected_by_key),
        "fixed_source_activity_keys": len(observed_by_key),
        "missing_nubase": missing_nubase,
        "key_mismatches": key_rows,
        "problems": problems,
    }
    write_json(DATA / f"s3d_o8_{tag}_activity_completeness_audit.json", payload)
    return payload


def configure_exactpos(
    module: Any,
    tag: str,
    *,
    configure_mapping: bool = True,
) -> None:
    prompt_view, buildup_view = materialize_family_view(tag)
    exact = family_exact_dir(tag)
    transport = family_transport_dir(tag)
    report = family_report_dir(tag)
    exact.mkdir(parents=True, exist_ok=True)
    transport.mkdir(parents=True, exist_ok=True)
    report.mkdir(parents=True, exist_ok=True)
    module.LABEL = f"s3d_o8_{tag}_activation_20260713_exactpos_m50000_s{SEED}"
    module.REPORT_DIR = report
    module.INSTANT = prompt_view
    module.BUILDUP = buildup_view
    module.RAW_SOURCE_DIR = family_raw_dir(tag)
    module.FIX = family_fix_dir(tag)
    module.FIXED_SOURCE = family_fix_dir(tag) / "activation_decay_day15_groundstate_fixed.source"
    module.FIX_SUMMARY = family_fix_dir(tag) / "source_fix_summary.json"
    module.FIX_AUDIT = family_fix_dir(tag) / "normalization_audit_groundstate_fix.json"
    module.SOURCE_DIR = exact
    module.TRANSPORT_DIR = transport
    module.SOURCE_PREFIX = family_source_prefix(tag)
    module.SOURCE = exact / "activation_decay_day15_groundstate_fixed_exactpos_m50000.source"
    module.MANIFEST = exact / f"s3d_o8_{tag}_exactpos_m50000_s{SEED}_manifest.json"
    module.WEIGHTED_TABLE = exact / f"exactpos_weighted_rpip_table_m50000_s{SEED}.csv"
    module.SUMMARY_JSON = report / "delayed_source_exactpos_summary.json"
    module.SUMMARY_MD = report / "delayed_source_exactpos_summary.md"
    module.GEOMETRY = GEOMETRY
    if configure_mapping:
        dat_files = sorted(BUILDUP_DIR.glob(f"Background_{tag}_*.dat.inc1.dat"))
        configure_volume_map(logical_volumes_from_dat(dat_files), GEOMETRY_COPY_MAP)
    module.canon_vn = canonicalize_volume


def build_family_exactpos(tag: str, force: bool) -> dict[str, Any]:
    fixed = family_fixed_source(tag, force=False)
    if fixed["status"] == "PASS_ZERO_PRODUCTION" or fixed.get("activity_Bq", 0.0) <= 0.0:
        return {
            "status": "PASS_ZERO_ACTIVITY",
            "family": tag,
            "activity_Bq": 0.0,
            "production": fixed.get("production"),
        }
    if fixed["status"] != "PASS":
        raise SystemExit(f"{tag} fixed source failed validation")
    module = load_exactpos(tag)
    configure_exactpos(module, tag)
    if force or not module.SOURCE.is_file():
        manifest = module.build_source(M_BLOCKS, RAW_TRIGGERS, SEED)
    else:
        manifest = load_json(module.MANIFEST)
    manifest["incident_family"] = tag
    manifest["family_resolved_contract"] = True
    geometry_bundle = geometry_bundle_snapshot()
    manifest["source_provenance"] = expected_family_source_provenance(
        tag, geometry_bundle=geometry_bundle
    )
    manifest["geometry_bundle_authority"] = geometry_bundle
    fixed_total = float(manifest.get("fixed_total_activity_Bq") or 0.0)
    source_flux_audit = exact_source_flux_audit(
        module.SOURCE,
        expected_total_activity_bq=fixed_total,
    )
    manifest["exact_source_flux_audit"] = source_flux_audit
    manifest["boundary"] = [
        f"This source contains only {tag}-induced S3d-O8 activation at day 15.",
        "The family separation is retained so the mission fold can apply the matching live incident-family flux driver.",
        "The buildup used the per-family file-count/TT division guard, NUBASE-2020 ground-state correction, min-points=1, exact RPIP positions, M=50,000, and one million requested delayed events.",
    ]
    module.write_json(module.MANIFEST, manifest)
    module.write_summary(manifest, manifest.get("delayed_transport"))
    sampling = manifest.get("sampling_audit") or {}
    divisions = manifest.get("division_by_tag") or {}
    problems: list[str] = []
    missing_provenance = sorted(
        name
        for name, record in (manifest.get("source_provenance") or {}).items()
        if not (record or {}).get("sha256")
    )
    if missing_provenance:
        problems.append(f"source provenance missing={missing_provenance}")
    if sampling.get("status") != "PASS" or sampling.get("problems"):
        problems.append(f"sampling={sampling}")
    if divisions != {tag: float(EXPECTED_COUNTS[tag])}:
        problems.append(f"division_by_tag={divisions}")
    if manifest.get("n_pointsource_blocks") != M_BLOCKS:
        problems.append(f"M={manifest.get('n_pointsource_blocks')}")
    if manifest.get("seed") != SEED:
        problems.append(f"seed={manifest.get('seed')}")
    if not module.SOURCE.is_file() or source_geometry(module.SOURCE) != [GEOMETRY_REL]:
        problems.append("source missing or geometry mismatch")
    source_text_sum = float(source_flux_audit.get("sum_flux_Bq") or 0.0)
    serialized_sum = float(manifest.get("source_text_sum_flux_Bq") or 0.0)
    if source_flux_audit["status"] != "PASS":
        problems.append(f"exact source Flux audit={source_flux_audit}")
    if not math.isclose(
        fixed_total, float(fixed["activity_Bq"]), rel_tol=0.0, abs_tol=1e-9
    ):
        problems.append(
            f"fixed activity={fixed['activity_Bq']} manifest fixed total={fixed_total}"
        )
    if not math.isclose(source_text_sum, serialized_sum, rel_tol=0.0, abs_tol=1e-9):
        problems.append(
            f"parsed exact-source Flux sum={source_text_sum} manifest serialized sum={serialized_sum}"
        )
    if not math.isclose(
        float(manifest.get("source_text_flux_abs_delta_Bq") or 0.0),
        float(
            source_flux_audit.get(
                "independently_derived_rounding_delta_Bq"
            )
            or 0.0
        ),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        problems.append(
            "manifest source-text rounding delta differs from independent 8-digit serialization"
        )
    if not math.isclose(
        float(manifest.get("flux_per_pointsource_Bq") or 0.0) * M_BLOCKS,
        fixed_total,
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        problems.append("M times manifest point-source flux does not close to fixed activity")
    return {
        "status": "PASS" if not problems else "FAIL",
        "family": tag,
        "activity_Bq": fixed["activity_Bq"],
        "source": rel(module.SOURCE),
        "manifest": rel(module.MANIFEST),
        "weighted_table": rel(module.WEIGHTED_TABLE),
        "summary": rel(module.SUMMARY_JSON),
        "sampling": sampling,
        "division_by_tag": divisions,
        "problems": problems,
    }


def reuse_prepared_sources_without_resigning() -> list[dict[str, Any]]:
    """Purely compare an existing prepared-source signature set.

    This path intentionally performs no writes and calls none of the source
    builders.  A missing or stale snapshot is not an invitation to bless the
    current bytes: only an explicit ``prepare-delay --force`` may rebuild raw,
    fixed and exact-position sources and issue new signatures.
    """
    validation_path = DATA / "s3d_o8_all8_family_source_validation.json"
    if not validation_path.is_file():
        raise RuntimeError(
            "non-force prepare-delay cannot create missing source authority; "
            "rerun prepare-delay --force"
        )
    rows = load_json(validation_path)
    if not isinstance(rows, list):
        raise RuntimeError(
            "source validation is not a list; rerun prepare-delay --force"
        )
    by_family = {
        str(row.get("family")): row
        for row in rows
        if isinstance(row, dict) and row.get("family")
    }
    problems: list[str] = []
    if len(rows) != len(FAMILIES) or set(by_family) != set(FAMILIES):
        problems.append(
            f"family set={sorted(by_family)} expected={list(FAMILIES)}"
        )
    for tag in FAMILIES:
        row = by_family.get(tag) or {}
        buildup_path = family_buildup_provenance_path(tag)
        stored_buildup = (
            load_json(buildup_path) if buildup_path.is_file() else None
        )
        current_buildup = family_buildup_provenance(tag)
        if stored_buildup != current_buildup:
            problems.append(f"{tag}: buildup provenance is missing or stale")
        if row.get("buildup_input_provenance") != artifact_record(buildup_path):
            problems.append(
                f"{tag}: source validation does not bind buildup provenance"
            )
        authority_path = family_prepared_source_authority_path(tag)
        stored_authority = (
            load_json(authority_path) if authority_path.is_file() else None
        )
        try:
            current_authority = current_prepared_source_authority(
                tag, str(row.get("status") or "")
            )
        except Exception as exc:
            current_authority = None
            problems.append(f"{tag}: cannot compute current authority: {exc}")
        if stored_authority != current_authority:
            problems.append(
                f"{tag}: prepared-source authority is missing or differs from current bytes"
            )
        if (current_authority or {}).get("status") != (
            "PASS_PREPARED_SOURCE_AUTHORITY"
        ):
            problems.append(
                f"{tag}: current prepared-source authority status="
                f"{(current_authority or {}).get('status')}"
            )
        if row.get("prepared_source_authority") != artifact_record(
            authority_path
        ) or row.get("prepared_source_authority_status") != (
            "PASS_PREPARED_SOURCE_AUTHORITY"
        ):
            problems.append(
                f"{tag}: source validation does not bind prepared-source authority"
            )
    if problems:
        raise RuntimeError(
            "non-force prepare-delay is compare-only and found stale/missing "
            "authority; no files were refreshed. Rerun prepare-delay --force:\n- "
            + "\n- ".join(problems)
        )
    return rows


def _prepare_delay_locked(args: argparse.Namespace) -> list[dict[str, Any]]:
    nubase_authority_record()
    source_card_authority = audit_source_cards()
    if source_card_authority["status"] != "PASS":
        raise RuntimeError(
            f"retained prompt source authority failed: {source_card_authority['problems']}"
        )
    buildup_authority = retained_buildup_validation()
    if buildup_authority["status"] != "PASS":
        raise SystemExit(
            f"retained all-eight buildup validation failed: "
            f"{buildup_authority['problems']}"
        )
    if not args.force:
        return reuse_prepared_sources_without_resigning()
    results: list[dict[str, Any]] = []
    for tag in FAMILIES:
        buildup_provenance = family_buildup_provenance(tag)
        write_json_atomic(family_buildup_provenance_path(tag), buildup_provenance)
        if buildup_provenance["status"] != "PASS":
            raise SystemExit(f"{tag} buildup-input provenance failed")
        volume_map = family_volume_map_audit(tag)
        raw = family_raw_source(tag, args.source_workers, force=True)
        if raw["status"] == "PASS_ZERO_PRODUCTION":
            results.append(
                {
                    **raw,
                    "buildup_input_provenance": artifact_record(
                        family_buildup_provenance_path(tag)
                    ),
                    "volume_map": volume_map,
                }
            )
            continue
        if raw["status"] != "PASS":
            raise SystemExit(f"{tag} raw delayed source failed")
        fixed = family_fixed_source(tag, force=True)
        if fixed["status"] != "PASS":
            raise SystemExit(f"{tag} fixed delayed source failed")
        exact = build_family_exactpos(tag, force=True)
        if exact["status"] not in ("PASS", "PASS_ZERO_ACTIVITY"):
            raise SystemExit(f"{tag} exact-position source failed")
        results.append(
            {
                "family": tag,
                "buildup_input_provenance": artifact_record(
                    family_buildup_provenance_path(tag)
                ),
                "volume_map": volume_map,
                "raw": raw,
                "fixed": fixed,
                "exact": exact,
                "status": exact["status"],
            }
        )
    authorities: list[tuple[dict[str, Any], Path, dict[str, Any]]] = []
    for row in results:
        tag = str(row["family"])
        authority = current_prepared_source_authority(tag, str(row["status"]))
        authority_path = family_prepared_source_authority_path(tag)
        if authority["status"] != "PASS_PREPARED_SOURCE_AUTHORITY":
            raise SystemExit(
                f"{tag} prepared source authority failed: {authority['problems']}"
            )
        authorities.append((row, authority_path, authority))
    for row, authority_path, authority in authorities:
        write_json_atomic(authority_path, authority)
        row["prepared_source_authority"] = artifact_record(authority_path)
        row["prepared_source_authority_status"] = authority["status"]
    write_json_atomic(
        DATA / "s3d_o8_all8_family_source_validation.json", results
    )
    return results


def prepare_delay(args: argparse.Namespace) -> list[dict[str, Any]]:
    with exclusive_source_transport_authority_lock("prepare-delay"):
        return _prepare_delay_locked(args)


def _family_transport_locked(
    tag: str,
    force: bool,
    source_result: dict[str, Any],
    lock_evidence: dict[str, Any],
) -> dict[str, Any]:
    if source_result["status"] != "PASS":
        raise RuntimeError(f"{tag} exact-position source is not ready")
    module = load_exactpos(tag)
    configure_exactpos(module, tag, configure_mapping=False)
    sim = module.SOURCE_PREFIX.with_suffix(".inc1.id1.sim.gz")
    env, evidence = cosima_environment()
    cosima_executable = str(evidence["cosima"])
    if _CURRENT_AUTHORITY_LOCK_FD is None or not _CURRENT_AUTHORITY_LOCK_EVIDENCE:
        raise RuntimeError(
            f"{tag}: delayed transport requires the global authority lock"
        )
    family_lock_fd = int(lock_evidence["inherited_fd"])
    inherited_lock_fds = tuple(
        sorted({_CURRENT_AUTHORITY_LOCK_FD, family_lock_fd})
    )
    launched = force or not sim.is_file()
    launch_payload: dict[str, Any] = {}
    if launched:
        runtime_before = runtime_dependency_snapshot(env, evidence)
        launch_inputs = transport_launch_inputs(
            tag,
            module.SOURCE,
            cosima_executable,
            runtime_dependencies=runtime_before,
        )
        replaced_sim = artifact_record(sim) if sim.is_file() else None
        if force and sim.is_file():
            sim.unlink()
        launch_payload = {
            "schema_version": 2,
            "status": "LAUNCH_PREPARED",
            "prepared_at_utc": now_utc(),
            "exclusive_lock": lock_evidence,
            "authority_lock": _CURRENT_AUTHORITY_LOCK_EVIDENCE,
            "inherited_lock_fds": list(inherited_lock_fds),
            "launch_inputs": launch_inputs,
            "replaced_existing_sim": replaced_sim,
            "claim_boundary": (
                "This sidecar binds the generated SIM to the source, requested seed, "
                "Cosima executable, complete five-file geometry bundle, recursive "
                "MEGAlib material include, and Geant4 dataset trees as they existed "
                "immediately before launch under a family-exclusive lock. Reuse is "
                "fail-closed."
            ),
        }
        write_json(family_transport_launch_path(tag), launch_payload)
        try:
            run_command(
                launch_inputs["command"],
                LOGS / f"run_delayed_{tag}.log",
                env,
                pass_fds=inherited_lock_fds,
            )
        except BaseException as exc:
            launch_payload["status"] = "LAUNCH_FAILED_OR_INTERRUPTED"
            launch_payload["completed_at_utc"] = now_utc()
            launch_payload["error"] = f"{type(exc).__name__}: {exc}"
            write_json(family_transport_launch_path(tag), launch_payload)
            raise
    manifest = module.summarize_transport()
    manifest["incident_family"] = tag
    manifest["family_resolved_contract"] = True
    transport = manifest.get("delayed_transport") or {}
    sim_path = path_from_row(str(transport.get("path") or sim))
    header = sim_header_metadata(sim_path)
    transport["size_bytes"] = sim_path.stat().st_size if sim_path.is_file() else None
    transport["sha256"] = sha256(sim_path) if sim_path.is_file() else None
    transport["seed"] = header.get("seed")
    transport["header_geometry"] = header.get("geometry")
    sim_parse = parse_sim_transport(sim_path)
    transport["TS_value"] = sim_parse.get("TS_value")
    transport["independent_sim_parse"] = sim_parse
    problems: list[str] = []
    if transport.get("SE") != RAW_TRIGGERS or transport.get("ID") != RAW_TRIGGERS:
        problems.append(f"SE/ID={transport.get('SE')}/{transport.get('ID')}")
    if not geometry_header_matches(transport.get("geometry"), GEOMETRY):
        problems.append(f"geometry={transport.get('geometry')}")
    if not geometry_header_matches(transport.get("header_geometry"), GEOMETRY):
        problems.append(f"header_geometry={transport.get('header_geometry')}")
    if transport.get("seed") != SEED:
        problems.append(f"seed={transport.get('seed')} expected={SEED}")
    if transport.get("TS") != 1 or transport.get("status") != "PASS":
        problems.append(
            f"TS/status={transport.get('TS')}/{transport.get('status')} expected=1/PASS"
        )
    if not math.isfinite(float(transport.get("TE_s") or 0.0)) or float(
        transport.get("TE_s") or 0.0
    ) <= 0.0:
        problems.append(f"TE_s={transport.get('TE_s')}")
    if sim_parse.get("status") != "PASS":
        problems.append(f"independent SIM parse={sim_parse}")
    if sim_parse.get("SE") != RAW_TRIGGERS or sim_parse.get("ID") != RAW_TRIGGERS:
        problems.append(
            f"independent SE/ID={sim_parse.get('SE')}/{sim_parse.get('ID')}"
        )
    if sim_parse.get("TS_records") != 1 or sim_parse.get("TS_value") != RAW_TRIGGERS:
        problems.append(
            f"independent TS records/value={sim_parse.get('TS_records')}/{sim_parse.get('TS_value')}"
        )
    if sim_parse.get("TE_records") != 1 or not math.isclose(
        float(sim_parse.get("TE_s") or 0.0),
        float(transport.get("TE_s") or -1.0),
        rel_tol=0.0,
        abs_tol=1e-9,
    ):
        problems.append(
            f"independent TE records/value={sim_parse.get('TE_records')}/{sim_parse.get('TE_s')}"
        )
    if sim_parse.get("seed") != SEED or not geometry_header_matches(
        sim_parse.get("geometry"), GEOMETRY
    ):
        problems.append(
            f"independent seed/geometry={sim_parse.get('seed')}/{sim_parse.get('geometry')}"
        )
    if launched:
        post_env, post_evidence = cosima_environment()
        if str(post_evidence["cosima"]) != cosima_executable:
            problems.append("Cosima executable changed across delayed transport")
        runtime_after = runtime_dependency_snapshot(post_env, post_evidence)
        post_launch_inputs = transport_launch_inputs(
            tag,
            module.SOURCE,
            cosima_executable,
            runtime_dependencies=runtime_after,
        )
        if post_launch_inputs != launch_payload.get("launch_inputs"):
            problems.append(
                "source/seed/geometry/Cosima inputs changed during transport"
            )
        launch_payload.update(
            {
                "status": "PASS" if not problems else "TRANSPORT_VALIDATION_FAIL",
                "completed_at_utc": now_utc(),
                "post_launch_inputs": post_launch_inputs,
                "sim": artifact_record(sim_path),
                "sim_header": header,
                "transport_summary": transport_summary_contract(
                    transport, sim_path, sim_parse=sim_parse
                ),
                "validation_problems": list(problems),
            }
        )
        write_json(family_transport_launch_path(tag), launch_payload)
    launch_audit = audit_transport_launch_contract(
        tag,
        module.SOURCE,
        sim_path,
        transport,
        cosima_executable,
        runtime_dependencies=runtime_after if launched else None,
    )
    problems.extend(launch_audit["problems"])
    if launched and problems and launch_payload.get("status") == "PASS":
        launch_payload["status"] = "TRANSPORT_PROVENANCE_FAIL"
        launch_payload["validation_problems"] = list(dict.fromkeys(problems))
        write_json(family_transport_launch_path(tag), launch_payload)
        launch_audit = audit_transport_launch_contract(
            tag,
            module.SOURCE,
            sim_path,
            transport,
            cosima_executable,
            runtime_dependencies=runtime_after if launched else None,
        )
    transport["source_sha256"] = (
        ((launch_audit.get("launch_inputs") or {}).get("source") or {}).get("sha256")
        if launch_audit["status"] == "PASS"
        else None
    )
    transport["geometry_bundle_sha256"] = (
        ((launch_audit.get("launch_inputs") or {}).get("geometry_bundle") or {}).get(
            "expected_sha256_by_filename"
        )
    )
    transport["launch_provenance"] = artifact_record(
        family_transport_launch_path(tag)
    )
    transport["launch_provenance_status"] = launch_audit["status"]
    manifest["delayed_transport"] = transport
    module.write_json(module.MANIFEST, manifest)
    module.write_summary(manifest, manifest.get("delayed_transport"))
    problems = list(dict.fromkeys(problems))
    return {
        "status": "PASS" if not problems else "FAIL",
        "family": tag,
        "activity_Bq": source_result["activity_Bq"],
        "source": rel(module.SOURCE),
        "sim": transport.get("path"),
        "SE": transport.get("SE"),
        "ID": transport.get("ID"),
        "TE_s": transport.get("TE_s"),
        "geometry": transport.get("geometry"),
        "header_geometry": transport.get("header_geometry"),
        "seed": transport.get("seed"),
        "TS": transport.get("TS"),
        "transport_status": transport.get("status"),
        "launch_provenance": transport.get("launch_provenance"),
        "launch_provenance_status": transport.get("launch_provenance_status"),
        "manifest": rel(module.MANIFEST),
        "problems": problems,
    }


def family_transport(
    tag: str,
    force: bool,
    source_result: dict[str, Any],
) -> dict[str, Any]:
    with exclusive_family_transport_lock(tag) as lock_evidence:
        return _family_transport_locked(
            tag,
            force,
            source_result,
            lock_evidence,
        )


def _run_delays_locked(args: argparse.Namespace) -> list[dict[str, Any]]:
    nubase_authority_record()
    source_card_authority = audit_source_cards()
    if source_card_authority["status"] != "PASS":
        raise RuntimeError(
            f"retained prompt source authority failed: {source_card_authority['problems']}"
        )
    buildup_authority = retained_buildup_validation()
    if buildup_authority["status"] != "PASS":
        raise RuntimeError(
            f"retained all-eight buildup validation failed: "
            f"{buildup_authority['problems']}"
        )
    source_validation = DATA / "s3d_o8_all8_family_source_validation.json"
    if not source_validation.is_file():
        raise SystemExit("family sources are not prepared")
    validation_rows = load_json(source_validation)
    validation_by_family = {
        str(row.get("family")): row
        for row in validation_rows
        if isinstance(row, dict) and row.get("family")
    }
    gate_problems: list[str] = []
    if len(validation_rows) != len(FAMILIES) or set(validation_by_family) != set(
        FAMILIES
    ):
        gate_problems.append(
            f"source validation family set={sorted(validation_by_family)} expected={list(FAMILIES)}"
        )
    candidates: list[str] = []
    zero_results: list[dict[str, Any]] = []
    prepared_sources: dict[str, dict[str, Any]] = {}
    for tag in FAMILIES:
        row = validation_by_family.get(tag) or {}
        provenance_path = family_buildup_provenance_path(tag)
        stored_provenance = (
            load_json(provenance_path) if provenance_path.is_file() else {}
        )
        current_provenance = family_buildup_provenance(tag)
        if stored_provenance != current_provenance:
            gate_problems.append(
                f"{tag}: buildup DAT/SIM/source provenance differs from prepared source authority"
            )
        if row.get("buildup_input_provenance") != artifact_record(provenance_path):
            gate_problems.append(
                f"{tag}: source validation does not bind the current buildup provenance artifact"
            )
        source_authority_path = family_prepared_source_authority_path(tag)
        stored_source_authority = (
            load_json(source_authority_path)
            if source_authority_path.is_file()
            else {}
        )
        current_source_authority = current_prepared_source_authority(
            tag, str(row.get("status") or "")
        )
        if stored_source_authority != current_source_authority:
            gate_problems.append(
                f"{tag}: current post-buildup source authority differs from prepare-delay snapshot"
            )
        if row.get("prepared_source_authority") != artifact_record(
            source_authority_path
        ) or row.get("prepared_source_authority_status") != (
            "PASS_PREPARED_SOURCE_AUTHORITY"
        ):
            gate_problems.append(
                f"{tag}: source validation does not bind the prepared source-authority snapshot"
            )
        production = raw_rp_total(tag)
        fixed_summary = family_fix_dir(tag) / "source_fix_summary.json"
        activity = float(load_json(fixed_summary).get("new_total_activity_Bq") or 0.0) if fixed_summary.is_file() else 0.0
        if production["zero_production"] or activity <= 0.0:
            expected_status = (
                "PASS_ZERO_PRODUCTION"
                if production["zero_production"]
                else "PASS_ZERO_ACTIVITY"
            )
            if row.get("status") != expected_status:
                gate_problems.append(
                    f"{tag}: source validation status={row.get('status')} expected={expected_status}"
                )
            zero_results.append(
                {
                    "status": expected_status,
                    "family": tag,
                    "activity_Bq": activity,
                    "production": production,
                }
            )
        else:
            if row.get("status") != "PASS":
                gate_problems.append(
                    f"{tag}: source validation status={row.get('status')} expected=PASS"
                )
            exact_dir = family_exact_dir(tag)
            required_exact = (
                exact_dir
                / "activation_decay_day15_groundstate_fixed_exactpos_m50000.source",
                exact_dir / f"s3d_o8_{tag}_exactpos_m50000_s{SEED}_manifest.json",
                exact_dir / f"exactpos_weighted_rpip_table_m50000_s{SEED}.csv",
            )
            missing_exact = [rel(path) for path in required_exact if not path.is_file()]
            if missing_exact:
                gate_problems.append(
                    f"{tag}: prepared exact-position artifacts missing={missing_exact}; rerun prepare-delay"
                )
                continue
            if current_source_authority.get("status") != (
                "PASS_PREPARED_SOURCE_AUTHORITY"
            ):
                gate_problems.append(
                    f"{tag}: prepared exact-position source authority={current_source_authority}"
                )
            prepared_sources[tag] = {
                "status": "PASS",
                "family": tag,
                "activity_Bq": current_source_authority.get("activity_Bq"),
                "source": rel(required_exact[0]),
                "manifest": rel(required_exact[1]),
                "weighted_table": rel(required_exact[2]),
                "problems": [],
            }
            candidates.append(tag)
    if gate_problems:
        raise RuntimeError(
            "run-delay source authority is not closed:\n- "
            + "\n- ".join(gate_problems)
        )
    results = list(zero_results)
    with ThreadPoolExecutor(max_workers=max(1, args.family_workers)) as executor:
        futures = {
            executor.submit(
                family_transport,
                tag,
                args.force,
                prepared_sources[tag],
            ): tag
            for tag in candidates
        }
        for future in as_completed(futures):
            tag = futures[future]
            result = future.result()
            if result["status"] != "PASS":
                raise RuntimeError(f"{tag} delayed transport failed: {result.get('problems')}")
            results.append(result)
    results.sort(key=lambda row: FAMILIES.index(str(row["family"])))
    write_json(DATA / "s3d_o8_all8_family_transport_validation.json", results)
    return results


def run_delays(args: argparse.Namespace) -> list[dict[str, Any]]:
    with exclusive_source_transport_authority_lock("run-delay"):
        return _run_delays_locked(args)


def _campaign_status_locked() -> dict[str, Any]:
    nubase_authority = nubase_authority_record()
    source_card_authority = audit_source_cards()
    if source_card_authority["status"] != "PASS":
        raise RuntimeError(
            f"retained prompt source authority failed: {source_card_authority['problems']}"
        )
    prompt = audit_completed_run(PROMPT_DIR, "instant")
    buildup_authority = retained_buildup_validation()
    buildup = buildup_authority["current"]
    campaign_geometry_bundle = geometry_bundle_snapshot()
    _cosima_env, cosima_evidence = cosima_environment()
    campaign_runtime_dependencies = runtime_dependency_snapshot(
        _cosima_env, cosima_evidence
    )
    del _cosima_env
    cosima_executable = str(cosima_evidence["cosima"])
    source_validation_path = DATA / "s3d_o8_all8_family_source_validation.json"
    source_validation_rows = (
        load_json(source_validation_path) if source_validation_path.is_file() else []
    )
    source_validation_by_family = {
        str(row.get("family")): row
        for row in source_validation_rows
        if isinstance(row, dict) and row.get("family")
    }
    source_validation_set_ok = (
        len(source_validation_rows) == len(FAMILIES)
        and set(source_validation_by_family) == set(FAMILIES)
    )
    families: list[dict[str, Any]] = []
    all_ready = buildup_authority["status"] == "PASS" and source_validation_set_ok
    total_activity = 0.0
    for tag in FAMILIES:
        production = raw_rp_total(tag) if BUILDUP_DIR.is_dir() else {
            "family": tag,
            "files": 0,
            "rp_raw_total": 0.0,
            "zero_production": False,
        }
        fixed_summary = family_fix_dir(tag) / "source_fix_summary.json"
        fixed_summary_payload = load_json(fixed_summary) if fixed_summary.is_file() else {}
        summary_activity = float(
            fixed_summary_payload.get("new_total_activity_Bq") or 0.0
        )
        exact_manifest = (
            family_exact_dir(tag)
            / f"s3d_o8_{tag}_exactpos_m50000_s{SEED}_manifest.json"
        )
        manifest = load_json(exact_manifest) if exact_manifest.is_file() else {}
        activity = float(
            manifest.get("fixed_total_activity_Bq")
            if manifest.get("fixed_total_activity_Bq") is not None
            else summary_activity
        )
        total_activity += activity
        transport = manifest.get("delayed_transport") or {}
        volume_audit_path = DATA / f"s3d_o8_{tag}_volume_map_audit.json"
        volume_audit = load_json(volume_audit_path) if volume_audit_path.is_file() else {}
        activity_audit_path = DATA / f"s3d_o8_{tag}_activity_completeness_audit.json"
        activity_audit = (
            load_json(activity_audit_path) if activity_audit_path.is_file() else {}
        )
        fixed_audit_path = family_fix_dir(tag) / "normalization_audit_groundstate_fix.json"
        fixed_audit = load_json(fixed_audit_path) if fixed_audit_path.is_file() else {}
        source_validation = source_validation_by_family.get(tag) or {}
        evidence_problems: list[str] = []
        launch_audit: dict[str, Any] = {}
        buildup_provenance_path = family_buildup_provenance_path(tag)
        stored_buildup_provenance = (
            load_json(buildup_provenance_path)
            if buildup_provenance_path.is_file()
            else {}
        )
        current_buildup_provenance = family_buildup_provenance(tag)
        if stored_buildup_provenance != current_buildup_provenance:
            evidence_problems.append(
                "current buildup DAT/SIM/source bytes differ from prepared provenance"
            )
        if source_validation.get("buildup_input_provenance") != artifact_record(
            buildup_provenance_path
        ):
            evidence_problems.append(
                "source validation does not bind current buildup-input provenance"
            )
        if source_validation.get("volume_map") != volume_audit:
            evidence_problems.append(
                "source validation volume-map evidence differs from current audit"
            )
        prepared_source_authority_path = family_prepared_source_authority_path(tag)
        stored_prepared_source_authority = (
            load_json(prepared_source_authority_path)
            if prepared_source_authority_path.is_file()
            else {}
        )
        current_source_authority = current_prepared_source_authority(
            tag, str(source_validation.get("status") or "")
        )
        if stored_prepared_source_authority != current_source_authority:
            evidence_problems.append(
                "current post-buildup source authority differs from prepare-delay snapshot"
            )
        if source_validation.get("prepared_source_authority") != artifact_record(
            prepared_source_authority_path
        ) or source_validation.get("prepared_source_authority_status") != (
            "PASS_PREPARED_SOURCE_AUTHORITY"
        ):
            evidence_problems.append(
                "source validation does not bind current prepared source-authority snapshot"
            )
        if current_source_authority.get("status") != (
            "PASS_PREPARED_SOURCE_AUTHORITY"
        ):
            evidence_problems.append(
                f"prepared source-authority status={current_source_authority.get('status')}"
            )
        expected_files = EXPECTED_COUNTS[tag]
        if int(production.get("files") or -1) != expected_files:
            evidence_problems.append(
                f"production files={production.get('files')} expected={expected_files}"
            )
        if float(production.get("division") or -1.0) != float(expected_files):
            evidence_problems.append(
                f"production division={production.get('division')} expected={expected_files}"
            )
        if int(production.get("tt_lines") or -1) != expected_files:
            evidence_problems.append(
                f"production TT lines={production.get('tt_lines')} expected={expected_files}"
            )
        if volume_audit.get("status") != "PASS":
            evidence_problems.append(f"volume-map status={volume_audit.get('status')}")

        if production.get("zero_production"):
            status = "PASS_ZERO_PRODUCTION"
            if source_validation.get("status") != status:
                evidence_problems.append(
                    f"source-validation status={source_validation.get('status')} expected={status}"
                )
        elif activity <= 0.0 and fixed_summary.is_file():
            status = "PASS_ZERO_ACTIVITY"
            if source_validation.get("status") != status:
                evidence_problems.append(
                    f"source-validation status={source_validation.get('status')} expected={status}"
                )
            if fixed_audit.get("status") != "PASS":
                evidence_problems.append(f"fixed normalization={fixed_audit.get('status')}")
            if activity_audit.get("status") != "PASS":
                evidence_problems.append(
                    f"activity completeness={activity_audit.get('status')}"
                )
        elif transport.get("SE") == RAW_TRIGGERS and transport.get("ID") == RAW_TRIGGERS and geometry_header_matches(transport.get("geometry"), GEOMETRY):
            status = "PASS"
            if source_validation.get("status") != "PASS":
                evidence_problems.append(
                    f"source-validation status={source_validation.get('status')} expected=PASS"
                )
            if fixed_audit.get("status") != "PASS":
                evidence_problems.append(f"fixed normalization={fixed_audit.get('status')}")
            if activity_audit.get("status") != "PASS":
                evidence_problems.append(
                    f"activity completeness={activity_audit.get('status')}"
                )
            if not str(manifest.get("status") or "").startswith("PASS_"):
                evidence_problems.append(
                    f"exact manifest status={manifest.get('status')}"
                )
            if manifest.get("problems"):
                evidence_problems.append(
                    f"exact manifest problems={manifest.get('problems')}"
                )
            expected_division = {tag: float(expected_files)}
            if manifest.get("incident_family") != tag:
                evidence_problems.append(
                    f"exact incident_family={manifest.get('incident_family')}"
                )
            if manifest.get("family_resolved_contract") is not True:
                evidence_problems.append("exact family-resolved contract is absent")
            if manifest.get("division_by_tag") != expected_division:
                evidence_problems.append(
                    f"exact division_by_tag={manifest.get('division_by_tag')} expected={expected_division}"
                )
            if int(manifest.get("n_pointsource_blocks") or -1) != M_BLOCKS:
                evidence_problems.append(
                    f"exact M={manifest.get('n_pointsource_blocks')} expected={M_BLOCKS}"
                )
            if int(manifest.get("seed") or -1) != SEED:
                evidence_problems.append(
                    f"exact seed={manifest.get('seed')} expected={SEED}"
                )
            sampling = manifest.get("sampling_audit") or {}
            if sampling.get("status") != "PASS" or sampling.get("problems"):
                evidence_problems.append(f"exact sampling audit={sampling}")
            source_provenance = manifest.get("source_provenance") or {}
            required_source_artifacts = {
                "buildup_inputs",
                "raw_source",
                "inventory",
                "raw_half_life_cache",
                "raw_normalization_json",
                "raw_normalization_csv",
                "raw_no_rpip_points",
                "raw_unknown_isotopes",
                "fixed_source",
                "fixed_summary",
                "groundstate_corrections",
                "fixed_normalization",
                "fixed_normalization_csv",
                "fixed_removed_or_rescaled",
                "volume_map_audit",
                "activity_completeness_audit",
                "exact_source",
                "weighted_table",
                "nubase",
                "retained_prompt_source_manifest",
                "retained_prompt_source_spectra",
                "geometry_setup",
                "geometry_source",
                "geometry_detector",
                "geometry_intro",
                "geometry_materials",
                "code_activation_harness",
                "code_makedecay_wrapper",
                "code_makedecay_helper",
                "code_fixed_wrapper",
                "code_fixed_helper",
                "code_exactpos_helper",
                "code_volume_map",
                "code_o8_replay_common",
                "code_shared_replay_common",
            }
            missing_source_artifacts = sorted(
                name
                for name in required_source_artifacts
                if not (source_provenance.get(name) or {}).get("sha256")
            )
            if missing_source_artifacts:
                evidence_problems.append(
                    f"exact source provenance missing={missing_source_artifacts}"
                )
            if activity_audit.get("status") != "PASS" or activity_audit.get(
                "problems"
            ):
                evidence_problems.append(
                    f"prepared DAT/NUBASE/fixed-source activity audit={activity_audit}"
                )
            current_source_provenance = expected_family_source_provenance(
                tag, geometry_bundle=campaign_geometry_bundle
            )
            if source_provenance != current_source_provenance:
                changed = sorted(
                    name
                    for name in set(source_provenance) | set(current_source_provenance)
                    if source_provenance.get(name)
                    != current_source_provenance.get(name)
                )
                evidence_problems.append(
                    f"exact source provenance differs from current bytes: {changed}"
                )
            if manifest.get("geometry_bundle_authority") != campaign_geometry_bundle:
                evidence_problems.append(
                    "exact source complete geometry-bundle authority differs from current retained authority"
                )
            exact_source_path = family_exact_dir(tag) / (
                "activation_decay_day15_groundstate_fixed_exactpos_m50000.source"
            )
            exact_flux_audit = exact_source_flux_audit(
                exact_source_path,
                expected_total_activity_bq=activity,
            )
            if exact_flux_audit.get("status") != "PASS":
                evidence_problems.append(
                    f"current exact-source Flux audit={exact_flux_audit}"
                )
            if manifest.get("exact_source_flux_audit") != exact_flux_audit:
                evidence_problems.append(
                    "manifest exact-source Flux audit differs from current source text"
                )
            activity_values = {
                "fixed_summary": summary_activity,
                "manifest_fixed_total": float(
                    manifest.get("fixed_total_activity_Bq") or 0.0
                ),
                "activity_expected_ground": float(
                    activity_audit.get("expected_ground_activity_Bq") or 0.0
                ),
                "activity_fixed_source": float(
                    activity_audit.get("fixed_source_activity_Bq") or 0.0
                ),
                "activity_summary": float(
                    activity_audit.get("source_fix_summary_activity_Bq") or 0.0
                ),
                "M_times_unrounded_flux": float(
                    manifest.get("flux_per_pointsource_Bq") or 0.0
                )
                * M_BLOCKS,
            }
            fixed_source_tolerance = max(
                1e-9,
                float(activity_audit.get("absolute_tolerance_Bq") or 0.0),
            )
            precise_activity_values = {
                key: value
                for key, value in activity_values.items()
                if key != "activity_fixed_source"
            }
            if any(
                not math.isclose(
                    value,
                    activity,
                    rel_tol=0.0,
                    abs_tol=1e-9,
                )
                for value in precise_activity_values.values()
            ) or not math.isclose(
                activity_values["activity_fixed_source"],
                activity,
                rel_tol=0.0,
                abs_tol=fixed_source_tolerance,
            ):
                evidence_problems.append(
                    "day-15 activity closure failed: "
                    f"authority={activity} values={activity_values} "
                    f"fixed_source_tolerance_Bq={fixed_source_tolerance}"
                )
            parsed_source_sum = float(exact_flux_audit.get("sum_flux_Bq") or 0.0)
            serialized_source_sum = float(
                manifest.get("source_text_sum_flux_Bq") or 0.0
            )
            recorded_rounding_delta = float(
                manifest.get("source_text_flux_abs_delta_Bq") or 0.0
            )
            if not math.isclose(
                parsed_source_sum,
                serialized_source_sum,
                rel_tol=0.0,
                abs_tol=1e-9,
            ) or not math.isclose(
                abs(activity - parsed_source_sum),
                recorded_rounding_delta,
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                evidence_problems.append(
                    "serialized exact-source activity does not match its audited rounding delta"
                )
            independently_derived_delta = float(
                exact_flux_audit.get(
                    "independently_derived_rounding_delta_Bq"
                )
                or 0.0
            )
            rounding_bound = float(
                exact_flux_audit.get("max_rounding_delta_bound_Bq") or 0.0
            )
            if not math.isclose(
                recorded_rounding_delta,
                independently_derived_delta,
                rel_tol=0.0,
                abs_tol=1e-12,
            ) or recorded_rounding_delta > rounding_bound + 1e-15:
                evidence_problems.append(
                    "manifest source-text rounding delta is not the independently derived 8-digit serialization delta"
                )
            sim_value = transport.get("path")
            sim_path = path_from_row(str(sim_value)) if sim_value else Path()
            if int(transport.get("size_bytes") or -1) != (
                sim_path.stat().st_size if sim_path.is_file() else -2
            ):
                evidence_problems.append("delayed SIM size provenance mismatch")
            if not transport.get("sha256"):
                evidence_problems.append("delayed SIM sha256 provenance is absent")
            elif sim_path.is_file() and transport.get("sha256") != sha256(sim_path):
                evidence_problems.append("delayed SIM sha256 provenance mismatch")
            if int(transport.get("seed") or -1) != SEED:
                evidence_problems.append(
                    f"delayed transport seed={transport.get('seed')} expected={SEED}"
                )
            if not geometry_header_matches(transport.get("header_geometry"), GEOMETRY):
                evidence_problems.append(
                    f"delayed SIM header geometry={transport.get('header_geometry')}"
                )
            if transport.get("TS") != 1 or transport.get("status") != "PASS":
                evidence_problems.append(
                    f"delayed TS/status={transport.get('TS')}/{transport.get('status')} expected=1/PASS"
                )
            source_value = (source_provenance.get("exact_source") or {}).get("path")
            source_path = path_from_row(str(source_value)) if source_value else Path()
            launch_audit = audit_transport_launch_contract(
                tag,
                source_path,
                sim_path,
                transport,
                cosima_executable,
                runtime_dependencies=campaign_runtime_dependencies,
            )
            if launch_audit["status"] != "PASS":
                evidence_problems.extend(
                    f"launch provenance: {problem}"
                    for problem in launch_audit["problems"]
                )
            if transport.get("launch_provenance") != launch_audit.get("artifact"):
                evidence_problems.append(
                    "manifest launch-provenance artifact differs from current sidecar"
                )
            if transport.get("launch_provenance_status") != "PASS":
                evidence_problems.append(
                    f"manifest launch-provenance status={transport.get('launch_provenance_status')}"
                )
        elif fixed_summary.is_file():
            status = "SOURCE_READY_TRANSPORT_PENDING"
        else:
            status = "NOT_READY"
        if evidence_problems and status in (
            "PASS",
            "PASS_ZERO_PRODUCTION",
            "PASS_ZERO_ACTIVITY",
        ):
            status = "FAIL_AUDIT_EVIDENCE"
        if status not in ("PASS", "PASS_ZERO_PRODUCTION", "PASS_ZERO_ACTIVITY"):
            all_ready = False
        families.append(
            {
                "family": tag,
                "status": status,
                "production": production,
                "activity_Bq": activity,
                "fixed_summary": rel(fixed_summary),
                "fixed_summary_sha256": sha256(fixed_summary) if fixed_summary.is_file() else None,
                "fixed_source": artifact_record(
                    family_fix_dir(tag)
                    / "activation_decay_day15_groundstate_fixed.source"
                ),
                "groundstate_corrections": artifact_record(
                    family_fix_dir(tag) / "groundstate_activity_corrections.csv"
                ),
                "inventory": artifact_record(
                    family_raw_dir(tag) / "activation_inventory_day15.csv"
                ),
                "exact_manifest": rel(exact_manifest),
                "transport": transport,
                "source_provenance": manifest.get("source_provenance") or {},
                "audit_evidence": {
                    "family_source_validation_status": source_validation.get("status"),
                    "buildup_input_provenance": {
                        "path": rel(buildup_provenance_path),
                        "artifact": artifact_record(buildup_provenance_path),
                        "canonical_payload_sha256": current_buildup_provenance.get(
                            "canonical_payload_sha256"
                        ),
                        "status": current_buildup_provenance.get("status"),
                    },
                    "prepared_source_authority": {
                        "path": rel(prepared_source_authority_path),
                        "artifact": artifact_record(
                            prepared_source_authority_path
                        ),
                        "canonical_payload_sha256": current_source_authority.get(
                            "canonical_payload_sha256"
                        ),
                        "status": current_source_authority.get("status"),
                    },
                    "volume_map": {
                        "path": rel(volume_audit_path),
                        "sha256": sha256(volume_audit_path) if volume_audit_path.is_file() else None,
                        "status": volume_audit.get("status"),
                    },
                    "fixed_normalization": {
                        "path": rel(fixed_audit_path),
                        "sha256": sha256(fixed_audit_path) if fixed_audit_path.is_file() else None,
                        "status": fixed_audit.get("status"),
                        "rows": fixed_audit.get("rows"),
                    },
                    "activity_completeness": {
                        "path": rel(activity_audit_path),
                        "sha256": sha256(activity_audit_path) if activity_audit_path.is_file() else None,
                        "status": activity_audit.get("status"),
                    },
                    "exact_manifest_sha256": sha256(exact_manifest) if exact_manifest.is_file() else None,
                    "transport_launch_provenance": launch_audit,
                    "problems": evidence_problems,
                },
            }
        )
    payload = {
        "status": "PASS_S3D_O8_ALL8_ACTIVATION_AND_FAMILY_DELAYED_TRANSPORT"
        if prompt["status"] == "PASS" and all_ready
        else "S3D_O8_ALL8_ACTIVATION_IN_PROGRESS",
        "generated_at_utc": now_utc(),
        "document_type": "s3d_o8_all8_prompt_all8_activation_family_resolved_delayed_chain",
        "geometry_setup": GEOMETRY_REL,
        "geometry_bundle_authority": campaign_geometry_bundle,
        "runtime_dependency_authority": campaign_runtime_dependencies,
        "retained_prompt": prompt,
        "all8_buildup": buildup,
        "retained_all8_buildup_validation": {
            "status": buildup_authority["status"],
            "artifact": buildup_authority["artifact"],
            "problems": buildup_authority["problems"],
        },
        "family_source_validation": {
            "path": rel(source_validation_path),
            "sha256": sha256(source_validation_path) if source_validation_path.is_file() else None,
            "family_set_complete": source_validation_set_ok,
        },
        "families": families,
        "total_fixed_day15_activity_Bq": total_activity,
        "statistics": {
            "gamma_splits": GAMMA_SPLITS,
            "non_gamma_replicas": NON_GAMMA_REPLICAS,
            "n_sample_per_nonzero_family": N_SAMPLE,
            "m_blocks_per_nonzero_family": M_BLOCKS,
            "delayed_triggers_per_nonzero_family": RAW_TRIGGERS,
            "seed": SEED,
        },
        "provenance": {
            "retained_o8_package": rel(O8_PACKAGE),
            "source_cards": rel(SOURCE_CARDS),
            "source_card_hashes": {
                tag: sha256(SOURCE_CARDS / f"Background_{tag}_fullsphere20.source")
                for tag in FAMILIES
            },
            "retained_prompt_source_manifest": artifact_record(
                SOURCE_CARD_MANIFEST
            ),
            "retained_prompt_source_authority": source_card_authority,
            "source_spectrum_authority": source_card_authority[
                "source_spectrum_authority"
            ],
            "nubase": rel(NUBASE),
            "nubase_sha256": nubase_authority["sha256"],
            "nubase_authority": nubase_authority,
        },
        "claim_boundary": (
            "Family-resolved delayed transports are transport authorities. Final paper "
            "rates require the new Step05 selection, 420 eV response ensemble, and "
            "family-by-nuclide trajectory fold."
        ),
    }
    write_json(CAMPAIGN, payload)
    return payload


def campaign_status() -> dict[str, Any]:
    with exclusive_source_transport_authority_lock("campaign-status"):
        return _campaign_status_locked()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=("prepare", "run-buildup", "prepare-delay", "run-delay", "status", "all"),
        nargs="?",
        default="status",
    )
    parser.add_argument("--workers", type=int, default=8, help="Cosima buildup workers")
    parser.add_argument("--source-workers", type=int, default=4, help="RPIP parsing workers")
    parser.add_argument("--family-workers", type=int, default=3, help="concurrent family delayed transports")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-heavy-run", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()

    payload: dict[str, Any] | None = None
    if args.stage != "status":
        if args.stage in ("run-buildup", "prepare-delay", "run-delay", "all"):
            require_confirmation(args, args.stage)
        with exclusive_source_transport_authority_lock(args.stage):
            if args.stage in ("prepare", "all"):
                _prepare_locked(args.workers)
            if args.stage in ("run-buildup", "all"):
                _run_buildup_locked(args)
            if args.stage in ("prepare-delay", "all"):
                _prepare_delay_locked(args)
            if args.stage in ("run-delay", "all"):
                _run_delays_locked(args)
            payload = _campaign_status_locked()

    if payload is None:
        payload = campaign_status()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "campaign": rel(CAMPAIGN),
                "total_fixed_day15_activity_Bq": payload["total_fixed_day15_activity_Bq"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
