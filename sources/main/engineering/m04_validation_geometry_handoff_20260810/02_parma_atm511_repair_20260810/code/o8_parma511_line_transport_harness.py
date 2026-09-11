#!/usr/bin/env python3
"""Isolated, recoverable O8 transport harness for the PARMA 510.99895-keV line.

The default commands only preflight, prepare source cards, parse existing SIM
files, or run the retained 3M read-only self-test.  Cosima is reachable only
through ``run-batch`` and requires two explicit authorization arguments.  The
source-card validator rejects every particle/spectrum other than an 80-bin,
physical-flux, atmospheric gamma line at exactly 510.99895 keV.

This file deliberately has no continuum, prompt, delayed, focused-signal, or
other-particle composition logic.  Raw SIM files are never deleted.
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
import multiprocessing as mp
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_TRANSPORT_ROOT = PACKAGE / "transport/campaigns"

O8_ROOT = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "43_geoopt_s3d_o8_fallback_20260712"
)
O8_SETUP = (
    O8_ROOT
    / "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
O8_GEO = O8_SETUP.with_suffix("")
O8_DET = O8_SETUP.with_name(
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det"
)

PARMA_CSV = {
    bins: PACKAGE / f"line/parma511_day15_{bins}bins.csv"
    for bins in (20, 40, 80)
}
PARMA_LINE_ENERGY_KEV = 510.99895
PARMA_TOTAL_FLUX = 0.16651547160226118

STEP05_IMPLEMENTATION = (
    ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
)
STEP09_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)

OLD_RUN = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o8_atm511_sidecar_3m_20260712"
)
OLD_SOURCE = OLD_RUN / "Atm511SidecarS3dO8_3M.source"
OLD_SIM = OLD_RUN / "Atm511SidecarS3dO8_3M.inc1.id1.sim.gz"

EXPECTED_SHA256 = {
    O8_SETUP: "86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec",
    O8_GEO: "ff4e8402df702501e0112fe377d837a74c39100317146b09e9569b7bd615c37c",
    O8_DET: "dd2c1d68cd474f8b0c7489f2cbbfc924eb69beb14d3ce360d9437c319a33d6cb",
    PARMA_CSV[20]: "3e4c73e50f6a5e97c2cd613b9b85a666f27723d7faaa26e105803774936a7ecd",
    PARMA_CSV[40]: "093175c5b73a72bfba510f23e7bfecb4aa8c93bed19f80a7a5271bccab18daa5",
    PARMA_CSV[80]: "2f4ae904bf89179fe1709e3a8123ff864f4450e8bcf443389898ea43cd6a5a32",
    STEP05_IMPLEMENTATION: "0c1e69e4a73bd8653e999b1d8d2aff404a37a44457e40f134388c819ad4b91ab",
    STEP09_SUMMARY: "8d147e21928b4830a215ab034f29379383b4368b4177f8a16a2f45769df73a25",
    OLD_SOURCE: "323621f39737171ddc77a377f58dabc7a8c7148bfe195c101961b95d68008b2e",
    OLD_SIM: "f07b1c8073764257ba95e25eb340726d27e2740c4f17bffe108a13ecc15b234c",
}

FWHM_KEV = 0.420
SIGMA_KEV = FWHM_KEV / (2.0 * math.sqrt(2.0 * math.log(2.0)))
TES_THRESHOLD_KEV = 0.3
ACTIVE_THRESHOLD_KEV = 50.0
BROAD_WINDOW_KEV = (480.0, 550.0)
W2_WINDOW_KEV = (510.58, 511.42)
PRIMARY_ATM_RESPONSE_SEED = 26_071_301 + 1_000_000_007
RESPONSE_SEED_STRIDE = 7_919
DEFAULT_RESPONSE_REPLICAS = 64

COSIMA_DEFAULT = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
PACKAGE44_RUNNER = (
    ROOT
    / "engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713"
    / "code/run_s3d_o8_all8_activation.py"
)
PACKAGE44_RUNNER_SHA256 = "942bbcc3b466bd11ec38d8bd9b868762b70a7d895caadf610a85cdbbacc23a9c"
COSIMA_BINARY_SHA256 = "3fb7613de58ebb365f2a55c3336e54d2aabea2a4ddb282003a5d25eac6f1c74a"
RUN_CONFIRMATION = "RUN_O8_PARMA511_LINE_ONLY_510.99895"
CAMPAIGN_SCHEMA = "o8-parma511-line-transport-campaign-v1"
PARSE_SCHEMA = "o8-parma511-line-stream-catalog-v1"
RESPONSE_SCHEMA = "o8-parma511-line-step05-response-v1"
KNOWN_O8_ACTIVE_SHIELD_NAMED_WRAPPERS = (
    "ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm",
    "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm",
    "ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm",
)
ACTIVE_VETO_NAMING_BLOCKER = (
    "The frozen predicate counts BGO and the S1/S2B plastic volumes, but also "
    "matches any name containing ACTIVE_SHIELD. In O8 that unintentionally "
    "includes all three passive Kapton wrapper volumes named ActiveShield_S3C_BGO_Kapton_*. "
    "This harness preserves, rather than repairs, that frozen selection."
)


class HarnessError(RuntimeError):
    """A scope, authority, provenance, or numerical closure check failed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def rel(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def atomic_write_json(path: Path, value: Any) -> None:
    atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def verify_hash(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise HarnessError(f"required authority is missing: {rel(path)}")
    actual = sha256(path)
    expected = EXPECTED_SHA256[path]
    if actual != expected:
        raise HarnessError(
            f"authority hash mismatch for {rel(path)}: {actual} != {expected}"
        )
    return {"path": rel(path), "sha256": actual, "bytes": path.stat().st_size}


def parse_grid(bins: int) -> list[dict[str, Any]]:
    if bins not in PARMA_CSV:
        raise HarnessError(f"unsupported angular grid: {bins}")
    verify_hash(PARMA_CSV[bins])
    with PARMA_CSV[bins].open("r", encoding="utf-8", newline="") as handle:
        raw_rows = list(csv.DictReader(handle))
    if len(raw_rows) != bins:
        raise HarnessError(f"{bins}-bin CSV has {len(raw_rows)} rows")
    rows: list[dict[str, Any]] = []
    for expected_id, raw in enumerate(raw_rows):
        row = {
            "bin_id": int(raw["theta_bin_id"]),
            "source_id": str(raw["source_id"]),
            "direction_label": str(raw["direction_label"]),
            "mu_low": float(raw["parma_mu_low"]),
            "mu_high": float(raw["parma_mu_high"]),
            "theta_low_deg": float(raw["cosima_theta_low_deg"]),
            "theta_high_deg": float(raw["cosima_theta_high_deg"]),
            "line_fraction": float(raw["line_fraction"]),
            "flux_ph_cm2_s": float(raw["line_flux_ph_cm-2_s-1"]),
        }
        if row["bin_id"] != expected_id:
            raise HarnessError(f"{bins}-bin CSV index discontinuity at {expected_id}")
        if row["source_id"] != (
            f"PARMA511_bin{expected_id:02d}_"
            + ("down" if expected_id < bins // 2 else "up")
        ):
            raise HarnessError(f"unexpected source id: {row['source_id']}")
        expected_label = "down" if expected_id < bins // 2 else "up"
        if row["direction_label"] != expected_label:
            raise HarnessError(f"unexpected direction label in bin {expected_id}")
        mu_at_theta_low = math.cos(math.radians(row["theta_low_deg"]))
        mu_at_theta_high = math.cos(math.radians(row["theta_high_deg"]))
        if not math.isclose(mu_at_theta_low, row["mu_high"], abs_tol=2e-13):
            raise HarnessError(f"mu/theta low-edge mismatch in {bins} bin {expected_id}")
        if not math.isclose(mu_at_theta_high, row["mu_low"], abs_tol=2e-13):
            raise HarnessError(f"mu/theta high-edge mismatch in {bins} bin {expected_id}")
        if row["flux_ph_cm2_s"] <= 0.0:
            raise HarnessError(f"non-positive PARMA flux in {bins} bin {expected_id}")
        if not math.isclose(
            row["line_fraction"],
            row["flux_ph_cm2_s"] / PARMA_TOTAL_FLUX,
            rel_tol=0.0,
            abs_tol=2e-16,
        ):
            raise HarnessError(f"fraction/flux mismatch in {bins} bin {expected_id}")
        rows.append(row)
    if not math.isclose(rows[0]["theta_low_deg"], 0.0, abs_tol=1e-12):
        raise HarnessError(f"{bins}-bin grid does not begin at theta=0")
    if not math.isclose(rows[-1]["theta_high_deg"], 180.0, abs_tol=1e-12):
        raise HarnessError(f"{bins}-bin grid does not end at theta=180")
    for left, right in zip(rows[:-1], rows[1:]):
        if not math.isclose(
            left["theta_high_deg"], right["theta_low_deg"], abs_tol=2e-12
        ):
            raise HarnessError(f"{bins}-bin theta grid has a gap/overlap")
    if not math.isclose(
        sum(row["flux_ph_cm2_s"] for row in rows),
        PARMA_TOTAL_FLUX,
        rel_tol=0.0,
        abs_tol=2e-15,
    ):
        raise HarnessError(f"{bins}-bin physical flux does not close")
    if not math.isclose(
        sum(row["line_fraction"] for row in rows),
        1.0,
        rel_tol=0.0,
        abs_tol=2e-14,
    ):
        raise HarnessError(f"{bins}-bin fractions do not close")
    return rows


def authority_report(*, include_old: bool = False) -> dict[str, Any]:
    files = [O8_SETUP, O8_GEO, O8_DET, *PARMA_CSV.values(), STEP05_IMPLEMENTATION, STEP09_SUMMARY]
    if include_old:
        files.extend((OLD_SOURCE, OLD_SIM))
    report = {rel(path): verify_hash(path) for path in files}
    setup_lines = [
        line.strip()
        for line in O8_SETUP.read_text(encoding="utf-8", errors="strict").splitlines()
        if line.strip().startswith("Include ")
    ]
    expected_includes = [f"Include {O8_GEO.name}", f"Include {O8_DET.name}"]
    if setup_lines != expected_includes:
        raise HarnessError(f"O8 setup includes changed: {setup_lines}")
    named_wrappers = sorted(
        match.group(1)
        for line in O8_GEO.read_text(encoding="utf-8", errors="strict").splitlines()
        if (match := re.match(r"^Volume\s+(\S*ActiveShield\S*)\s*$", line.strip()))
    )
    if named_wrappers != sorted(KNOWN_O8_ACTIVE_SHIELD_NAMED_WRAPPERS):
        raise HarnessError(
            f"O8 ActiveShield-named volume inventory changed: {named_wrappers}"
        )
    geo_text = O8_GEO.read_text(encoding="utf-8", errors="strict")
    for wrapper in named_wrappers:
        if f"{wrapper}.Material Kapton" not in geo_text:
            raise HarnessError(f"ActiveShield-named wrapper is no longer Kapton: {wrapper}")
    grids = {str(bins): parse_grid(bins) for bins in (20, 40, 80)}
    return {
        "status": "PASS_O8_PARMA511_LINE_ONLY_PREFLIGHT",
        "scope": "atmospheric annihilation mono line only",
        "line_energy_keV": PARMA_LINE_ENERGY_KEV,
        "physical_flux_ph_cm2_s": PARMA_TOTAL_FLUX,
        "files": report,
        "grid_rows": {bins: len(rows) for bins, rows in grids.items()},
        "o8_setup_includes": setup_lines,
        "frozen_active_veto_naming_audit": {
            "active_shield_named_o8_volumes": named_wrappers,
            "all_are_passive_kapton_wrappers": True,
            "predicate_matches_them": all(
                is_active_veto_volume(name) for name in named_wrappers
            ),
            "blocker": ACTIVE_VETO_NAMING_BLOCKER,
        },
    }


def safe_campaign_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", value):
        raise HarnessError("campaign id must match [A-Za-z0-9][A-Za-z0-9_.-]{0,79}")
    return value


def source_text(
    *, run_name: str, events: int, seed: int, output_prefix: Path, rows: list[dict[str, Any]]
) -> str:
    lines = [
        "# Isolated atmospheric annihilation line transport: PARMA physical 80-bin flux.",
        "# No composite source is included; this card is valid only at 510.99895 keV.",
        f"Geometry {rel(O8_SETUP)}",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "StoreSimulationInfo all",
        "StoreIsotopes false",
        "DetectorTimeConstant 1e-9",
        f"Seed {seed}",
        "",
        f"Run {run_name}",
        f"{run_name}.Events {events}",
        f"{run_name}.FileName {rel(output_prefix)}",
        "",
    ]
    lines.extend(f"{run_name}.Source {row['source_id']}" for row in rows)
    lines.append("")
    for row in rows:
        source_id = row["source_id"]
        lines.extend(
            [
                f"{source_id}.ParticleType 1",
                (
                    f"{source_id}.Beam FarFieldAreaSource "
                    f"{row['theta_low_deg']:.12f} {row['theta_high_deg']:.12f} "
                    "0.000000000000 360.000000000000"
                ),
                f"{source_id}.Spectrum Mono {PARMA_LINE_ENERGY_KEV:.5f}",
                f"{source_id}.Flux {row['flux_ph_cm2_s']:.17g}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def validate_source_text(
    text: str,
    *,
    expected_run: str,
    expected_events: int,
    expected_seed: int,
    expected_prefix: Path,
    rows: list[dict[str, Any]],
) -> None:
    required_scalars = {
        "Geometry": rel(O8_SETUP),
        "StoreSimulationInfo": "all",
        "StoreIsotopes": "false",
        "Seed": str(expected_seed),
        "Run": expected_run,
        f"{expected_run}.Events": str(expected_events),
        f"{expected_run}.FileName": rel(expected_prefix),
    }
    parsed_scalars: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split(maxsplit=1)
        if len(fields) == 2:
            parsed_scalars[fields[0]] = fields[1]
    for key, expected in required_scalars.items():
        if parsed_scalars.get(key) != expected:
            raise HarnessError(
                f"source-card scalar mismatch for {key}: {parsed_scalars.get(key)!r}"
            )
    bindings = re.findall(rf"^{re.escape(expected_run)}\.Source\s+(\S+)\s*$", text, re.M)
    expected_ids = [str(row["source_id"]) for row in rows]
    if bindings != expected_ids or len(bindings) != 80:
        raise HarnessError("source card is not the exact ordered 80-bin PARMA module")
    particle_rows = re.findall(r"^(\S+)\.ParticleType\s+(\S+)\s*$", text, re.M)
    spectrum_rows = re.findall(r"^(\S+)\.Spectrum\s+(\S+)\s+(\S+)\s*$", text, re.M)
    flux_rows = re.findall(r"^(\S+)\.Flux\s+(\S+)\s*$", text, re.M)
    beam_rows = re.findall(r"^(\S+)\.Beam\s+(.+)$", text, re.M)
    if len(particle_rows) != 80 or any(value != "1" for _, value in particle_rows):
        raise HarnessError("source card contains a non-gamma or missing ParticleType")
    if len(spectrum_rows) != 80:
        raise HarnessError("source card must have exactly 80 spectra")
    for source_id, spectrum_type, energy in spectrum_rows:
        if spectrum_type != "Mono" or float(energy) != PARMA_LINE_ENERGY_KEV:
            raise HarnessError(f"non-line spectrum found for {source_id}")
    if len(flux_rows) != 80 or len(beam_rows) != 80:
        raise HarnessError("source card does not contain exactly 80 Flux/Beam rows")
    expected_by_id = {str(row["source_id"]): row for row in rows}
    for source_id, flux in flux_rows:
        if source_id not in expected_by_id or not math.isclose(
            float(flux),
            float(expected_by_id[source_id]["flux_ph_cm2_s"]),
            rel_tol=0.0,
            abs_tol=1e-18,
        ):
            raise HarnessError(f"physical PARMA flux changed for {source_id}")
    if set(source_id for source_id, _ in particle_rows) != set(expected_ids):
        raise HarnessError("ParticleType sources do not match run bindings")
    if set(source_id for source_id, _, _ in spectrum_rows) != set(expected_ids):
        raise HarnessError("Spectrum sources do not match run bindings")
    forbidden_directives = re.findall(
        r"^\S+\.Spectrum\s+(?!Mono\b)|^\S+\.ParticleType\s+(?!1\s*$)",
        text,
        re.M,
    )
    if forbidden_directives:
        raise HarnessError("source card contains a forbidden spectrum/particle directive")


def batch_seed(base_seed: int, batch_index: int) -> int:
    value = int(base_seed) + int(batch_index) * 104_729
    if value <= 0 or value >= 2_147_483_647:
        raise HarnessError(f"batch seed outside signed 32-bit range: {value}")
    return value


def prepare_campaign(
    *,
    campaign_id: str,
    batches: int,
    events_per_batch: int,
    base_seed: int,
    transport_root: Path,
    runtime_probe: bool = True,
) -> dict[str, Any]:
    authority = authority_report()
    runtime_evidence: dict[str, Any]
    if runtime_probe:
        _, runtime_evidence = cosima_runtime_probe()
    else:
        runtime_evidence = {
            "status": "SKIPPED_ONLY_FOR_MANIFEST_LOCK_SELF_TEST",
            "transport_launched": False,
        }
    campaign_id = safe_campaign_id(campaign_id)
    if batches < 1 or batches > 10_000:
        raise HarnessError("batches must be in [1, 10000]")
    if events_per_batch < 1:
        raise HarnessError("events per batch must be positive")
    rows = parse_grid(80)
    campaign_dir = transport_root.resolve() / campaign_id
    manifest_path = campaign_dir / "campaign_manifest.json"
    intent = {
        "schema": CAMPAIGN_SCHEMA,
        "campaign_id": campaign_id,
        "batches": int(batches),
        "events_per_batch": int(events_per_batch),
        "base_seed": int(base_seed),
        "line_energy_keV": PARMA_LINE_ENERGY_KEV,
        "proposal_grid_bins": 80,
        "proposal_csv_sha256": EXPECTED_SHA256[PARMA_CSV[80]],
        "o8_setup_sha256": EXPECTED_SHA256[O8_SETUP],
    }
    fingerprint = canonical_sha256(intent)
    if manifest_path.exists():
        existing = load_json(manifest_path)
        if existing.get("intent_fingerprint_sha256") != fingerprint:
            raise HarnessError(
                f"campaign exists with different intent: {rel(manifest_path)}"
            )
        for batch in existing["batches"]:
            card = ROOT / batch["source_card"] if not Path(batch["source_card"]).is_absolute() else Path(batch["source_card"])
            if not card.is_file() or sha256(card) != batch["source_card_sha256"]:
                raise HarnessError(f"existing campaign source card failed recovery check: {card}")
        existing["prepare_receipt"] = "IDEMPOTENT_EXISTING_CAMPAIGN_VERIFIED"
        return existing

    source_dir = campaign_dir / "source_cards"
    raw_dir = campaign_dir / "raw"
    log_dir = campaign_dir / "logs"
    parsed_dir = campaign_dir / "parsed"
    for directory in (source_dir, raw_dir, log_dir, parsed_dir):
        directory.mkdir(parents=True, exist_ok=True)

    batch_rows: list[dict[str, Any]] = []
    seeds: set[int] = set()
    prefixes: set[str] = set()
    for index in range(batches):
        seed = batch_seed(base_seed, index)
        run_name = f"O8PARMA511L_{campaign_id}_b{index:04d}"
        if len(run_name) > 120:
            raise HarnessError("run name is too long")
        prefix = raw_dir / run_name
        source_card = source_dir / f"{run_name}.source"
        expected_sim = Path(f"{prefix}.inc1.id1.sim.gz")
        stdout_log = log_dir / f"{run_name}.stdout.log.gz"
        if seed in seeds or str(prefix) in prefixes:
            raise HarnessError("duplicate seed or output prefix generated")
        seeds.add(seed)
        prefixes.add(str(prefix))
        if expected_sim.exists() or stdout_log.exists():
            raise HarnessError(f"unmanifested output collision: {rel(prefix)}")
        text = source_text(
            run_name=run_name,
            events=events_per_batch,
            seed=seed,
            output_prefix=prefix,
            rows=rows,
        )
        validate_source_text(
            text,
            expected_run=run_name,
            expected_events=events_per_batch,
            expected_seed=seed,
            expected_prefix=prefix,
            rows=rows,
        )
        if source_card.exists():
            if source_card.read_text(encoding="utf-8") != text:
                raise HarnessError(f"partial campaign card conflicts: {rel(source_card)}")
        else:
            atomic_write_text(source_card, text)
        batch_rows.append(
            {
                "batch_index": index,
                "run_name": run_name,
                "transport_seed": seed,
                "events_requested": events_per_batch,
                "source_card": rel(source_card),
                "source_card_sha256": sha256(source_card),
                "output_prefix": rel(prefix),
                "expected_sim": rel(expected_sim),
                "stdout_log": rel(stdout_log),
                "parsed_dir": rel(parsed_dir / f"batch_{index:04d}"),
                "status": "PREPARED_NOT_RUN",
                "raw_disposition": "DO_NOT_DELETE_UNTIL_VALIDATED_PARSE",
                "raw_deleted": False,
            }
        )

    manifest = {
        "schema": CAMPAIGN_SCHEMA,
        "status": "PREPARED_LINE_ONLY_NO_COSIMA_LAUNCHED",
        "created_at_utc": utc_now(),
        "intent": intent,
        "intent_fingerprint_sha256": fingerprint,
        "scope_contract": {
            "included": "atmospheric annihilation mono line at 510.99895 keV",
            "physical_source_grid": "PARMA 80 equal-mu bins",
            "physical_flux_ph_cm2_s": PARMA_TOTAL_FLUX,
            "excluded": [
                "broadband photon continuum",
                "prompt",
                "delayed or activation",
                "focused signal",
                "all other particles",
                "full-chain recomposition",
            ],
        },
        "authority": authority,
        "cosima_runtime_preflight": runtime_evidence,
        "response_contract": {
            "fwhm_keV": FWHM_KEV,
            "sigma_keV": SIGMA_KEV,
            "tes_threshold_keV": TES_THRESHOLD_KEV,
            "active_threshold_keV": ACTIVE_THRESHOLD_KEV,
            "primary_atmospheric_seed": PRIMARY_ATM_RESPONSE_SEED,
            "seed_stride": RESPONSE_SEED_STRIDE,
            "default_replicas": DEFAULT_RESPONSE_REPLICAS,
            "step05_sha256": EXPECTED_SHA256[STEP05_IMPLEMENTATION],
            "step09_summary_sha256": EXPECTED_SHA256[STEP09_SUMMARY],
        },
        "execution_gate": {
            "command": "run-batch",
            "requires_flag": "--authorize-line-only-cosima",
            "requires_confirmation": RUN_CONFIRMATION,
            "note": "Preparation is not authorization to launch transport.",
        },
        "batches": batch_rows,
    }
    launch_lines = [
        "# These commands are inert text. Each launch still requires explicit main-agent authorization.",
    ]
    for row in batch_rows:
        launch_lines.append(
            "python3 code/o8_parma511_line_transport_harness.py run-batch "
            f"--manifest {rel(manifest_path)} --batch {row['batch_index']} "
            "--authorize-line-only-cosima "
            f"--confirmation {RUN_CONFIRMATION} --quiet"
        )
    atomic_write_text(campaign_dir / "launch_plan.txt", "\n".join(launch_lines) + "\n")
    atomic_write_json(manifest_path, manifest)
    return manifest


def path_from_manifest(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def validate_campaign_document(manifest: dict[str, Any], path: Path) -> None:
    if manifest.get("schema") != CAMPAIGN_SCHEMA:
        raise HarnessError(f"not a line-only campaign manifest: {path}")
    intent = manifest.get("intent", {})
    if canonical_sha256(intent) != manifest.get("intent_fingerprint_sha256"):
        raise HarnessError("campaign intent fingerprint mismatch")
    if intent.get("line_energy_keV") != PARMA_LINE_ENERGY_KEV:
        raise HarnessError("campaign energy is not the frozen PARMA line energy")
    if intent.get("proposal_grid_bins") != 80:
        raise HarnessError("campaign proposal is not the physical 80-bin grid")


def load_campaign(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    validate_campaign_document(manifest, path)
    authority_report()
    return manifest


@contextmanager
def campaign_lock(manifest_path: Path) -> Iterable[None]:
    """Serialize campaign state transitions across independent processes."""
    lock_path = manifest_path.parent / ".campaign_manifest.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def manifest_batch(manifest: dict[str, Any], index: int) -> dict[str, Any]:
    matches = [row for row in manifest["batches"] if int(row["batch_index"]) == index]
    if len(matches) != 1:
        raise HarnessError(f"batch {index} is absent or duplicated")
    return matches[0]


def update_manifest_batch(
    manifest_path: Path,
    batch_index: int,
    updates: dict[str, Any],
    *,
    expected_statuses: set[str] | None = None,
) -> dict[str, Any]:
    # Never accept a caller-provided manifest: it can be stale when multiple
    # batch workers share a campaign. Reload and merge while holding flock.
    with campaign_lock(manifest_path):
        manifest = load_json(manifest_path)
        validate_campaign_document(manifest, manifest_path)
        row = manifest_batch(manifest, batch_index)
        if expected_statuses is not None and str(row.get("status")) not in expected_statuses:
            raise HarnessError(
                f"batch {batch_index} state transition rejected: {row.get('status')} "
                f"not in {sorted(expected_statuses)}"
            )
        row.update(updates)
        statuses = Counter(str(item["status"]) for item in manifest["batches"])
        manifest["batch_status_counts"] = dict(sorted(statuses.items()))
        manifest["updated_at_utc"] = utc_now()
        atomic_write_json(manifest_path, manifest)
        return manifest


def run_batch(args: argparse.Namespace) -> dict[str, Any]:
    if not args.authorize_line_only_cosima or args.confirmation != RUN_CONFIRMATION:
        raise HarnessError(
            "Cosima launch denied: both --authorize-line-only-cosima and the exact "
            f"--confirmation {RUN_CONFIRMATION} are required"
        )
    manifest_path = args.manifest.resolve()
    manifest = load_campaign(manifest_path)
    batch = manifest_batch(manifest, args.batch)
    source_card = path_from_manifest(batch["source_card"])
    expected_sim = path_from_manifest(batch["expected_sim"])
    stdout_log = path_from_manifest(batch["stdout_log"])
    prefix = path_from_manifest(batch["output_prefix"])
    rows = parse_grid(80)
    if sha256(source_card) != batch["source_card_sha256"]:
        raise HarnessError("source card hash changed after preparation")
    text = source_card.read_text(encoding="utf-8")
    validate_source_text(
        text,
        expected_run=batch["run_name"],
        expected_events=int(batch["events_requested"]),
        expected_seed=int(batch["transport_seed"]),
        expected_prefix=prefix,
        rows=rows,
    )
    if expected_sim.exists() or stdout_log.exists():
        raise HarnessError("refusing to overwrite an existing raw SIM or stdout log")
    cosima = args.cosima.resolve()
    runtime_env, runtime_evidence = cosima_runtime_probe()
    runtime_cosima = Path(runtime_evidence["cosima"]["path"]).resolve()
    if cosima != runtime_cosima:
        raise HarnessError(
            f"requested Cosima {cosima} differs from package44 runtime {runtime_cosima}"
        )
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    command = [str(cosima), "-s", str(batch["transport_seed"]), str(source_card)]
    update_manifest_batch(
        manifest_path,
        args.batch,
        {
            "status": "RUNNING_LINE_ONLY",
            "started_at_utc": utc_now(),
            "cosima_command": command,
            "cosima_executable": str(cosima),
            "cosima_executable_sha256": runtime_evidence["cosima"]["sha256"],
            "cosima_runtime_environment": runtime_evidence,
            "stdout_log_compression": "gzip-stream",
        },
        expected_statuses={"PREPARED_NOT_RUN", "FAILED_NO_VALID_SIM"},
    )
    with gzip.open(stdout_log, "xb", compresslevel=6) as log_handle:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=runtime_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        assert process.stdout is not None
        for chunk in iter(lambda: process.stdout.read(1024 * 1024), b""):
            log_handle.write(chunk)
        process.stdout.close()
        returncode = int(process.wait())
    log_receipt = {
        "path": rel(stdout_log),
        "sha256": sha256(stdout_log),
        "bytes": stdout_log.stat().st_size,
        "compression": "gzip",
        "uncompressed_log_retained": False,
    }
    if returncode != 0 or not expected_sim.is_file():
        update_manifest_batch(
            manifest_path,
            args.batch,
            {
                "status": "FAILED_NO_VALID_SIM",
                "finished_at_utc": utc_now(),
                "returncode": returncode,
                "stdout_log_receipt": log_receipt,
                "raw_disposition": "DO_NOT_DELETE_FAILED_OR_INCOMPLETE",
            },
            expected_statuses={"RUNNING_LINE_ONLY"},
        )
        raise HarnessError(
            f"Cosima did not produce the expected SIM (returncode={returncode})"
        )
    update_manifest_batch(
        manifest_path,
        args.batch,
        {
            "status": "TRANSPORT_COMPLETE_UNPARSED",
            "finished_at_utc": utc_now(),
            "returncode": returncode,
            "sim_bytes": expected_sim.stat().st_size,
            "stdout_log_receipt": log_receipt,
            "raw_disposition": "DO_NOT_DELETE_UNTIL_VALIDATED_PARSE",
        },
        expected_statuses={"RUNNING_LINE_ONLY"},
    )
    receipt = {
        "status": "TRANSPORT_COMPLETE_UNPARSED",
        "batch": args.batch,
        "sim": rel(expected_sim),
        "stdout_log": rel(stdout_log),
        "stdout_log_receipt": log_receipt,
        "raw_deleted": False,
    }
    if not args.quiet:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return receipt


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


def angular_bin_from_init_dir_z(dir_z: float, bins: int) -> int:
    # FarFieldAreaSource theta is a source-side direction. IA INIT points inward:
    # mu_source=cos(theta_source)=-dir_z, hence theta-bin index grows with dir_z.
    return max(0, min(bins - 1, int(math.floor((1.0 + dir_z) * bins / 2.0))))


def source_theta_deg(dir_z: float) -> float:
    return math.degrees(math.acos(max(-1.0, min(1.0, -dir_z))))


def parse_init(line: str) -> dict[str, float | int]:
    fields = [part.strip() for part in line.split("IA INIT", 1)[1].split(";")]
    if len(fields) < 23:
        raise HarnessError(f"malformed IA INIT row with {len(fields)} fields")
    return {
        "x_cm": float(fields[4]),
        "y_cm": float(fields[5]),
        "z_cm": float(fields[6]),
        "particle_type": int(fields[15]),
        "dir_x": float(fields[16]),
        "dir_y": float(fields[17]),
        "dir_z": float(fields[18]),
        "energy_keV": float(fields[22]),
    }


EVENT_FIELDS = [
    "event_id",
    "init_x_cm",
    "init_y_cm",
    "init_z_cm",
    "dir_x",
    "dir_y",
    "dir_z",
    "source_theta_deg",
    "init_energy_keV",
    "bin20",
    "bin40",
    "bin80",
    "tes_total_keV",
    "active_total_keV",
    "pixel_count",
]
PIXEL_FIELDS = [
    "event_id",
    "pixel_uid",
    "layer",
    "energy_keV",
    "x_cm",
    "y_cm",
    "z_cm",
]


def stream_parse_sim(
    *,
    sim: Path,
    output_dir: Path,
    expected_seed: int,
    expected_energy_keV: float,
    expected_events: int,
    source_card: Path,
    source_card_sha256: str,
    proposal_name: str,
    energy_tolerance_keV: float = 0.001,
) -> dict[str, Any]:
    authority = authority_report(include_old=sim.resolve() == OLD_SIM.resolve())
    if not sim.is_file():
        raise HarnessError(f"SIM is missing: {sim}")
    if not source_card.is_file() or sha256(source_card) != source_card_sha256:
        raise HarnessError("source-card provenance failed before SIM parse")
    sim_hash = sha256(sim)
    expected_sim_hash = EXPECTED_SHA256.get(sim)
    if expected_sim_hash is not None and sim_hash != expected_sim_hash:
        raise HarnessError("retained SIM hash mismatch")
    output_dir.mkdir(parents=True, exist_ok=True)
    provenance_path = output_dir / "provenance.json"
    if provenance_path.exists():
        previous = load_json(provenance_path)
        if (
            previous.get("status") == "PASS_STREAM_PARSE_COMPLETE"
            and previous.get("raw_sim", {}).get("sha256") == sim_hash
        ):
            previous["parse_receipt"] = "IDEMPOTENT_EXISTING_PARSE_VERIFIED"
            return previous
        raise HarnessError(f"parsed output exists but is not reusable: {output_dir}")

    event_path = output_dir / "tes_events.csv"
    pixel_path = output_dir / "tes_pixel_hits.csv"
    angular_path = output_dir / "angular_counts.json"
    marker_path = output_dir / "RAW_SAFE_TO_DELETE_NOT_DELETED.json"
    for path in (event_path, pixel_path, angular_path, marker_path):
        if path.exists():
            raise HarnessError(f"refusing to overwrite partial parse artifact: {path}")

    event_fd, event_tmp_name = tempfile.mkstemp(prefix=".tes_events.", dir=output_dir)
    pixel_fd, pixel_tmp_name = tempfile.mkstemp(prefix=".tes_pixels.", dir=output_dir)
    event_tmp = Path(event_tmp_name)
    pixel_tmp = Path(pixel_tmp_name)
    cc_re = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
    kv_re = re.compile(r"(\w+)=([^\s]+)")
    id_re = re.compile(r"^ID\s+(\d+)")
    tp_re = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.I)

    header: dict[str, Any] = {}
    footer: dict[str, Any] = {"TE_s": None, "TS": None}
    generated = 0
    init_records = 0
    tes_events = 0
    tes_pixel_hits = 0
    active_only_events = 0
    tes_or_active_events = 0
    energy_mismatch_records = 0
    non_gamma_init_records = 0
    energy_min: float | None = None
    energy_max: float | None = None
    angular = {bins: [0] * bins for bins in (20, 40, 80)}
    active_volume_hit_records: Counter[str] = Counter()
    active_volume_energy_keV: Counter[str] = Counter()
    cur_id: int | None = None
    cur_init: dict[str, Any] | None = None
    active_total = 0.0
    pixels: dict[str, dict[str, float]] = {}

    try:
        with os.fdopen(event_fd, "w", encoding="utf-8", newline="") as event_handle, os.fdopen(
            pixel_fd, "w", encoding="utf-8", newline=""
        ) as pixel_handle:
            event_writer = csv.DictWriter(event_handle, fieldnames=EVENT_FIELDS)
            pixel_writer = csv.DictWriter(pixel_handle, fieldnames=PIXEL_FIELDS)
            event_writer.writeheader()
            pixel_writer.writeheader()

            def flush() -> None:
                nonlocal cur_id, cur_init, active_total, pixels
                nonlocal tes_events, tes_pixel_hits, active_only_events, tes_or_active_events
                if cur_id is None:
                    return
                if cur_init is None:
                    raise HarnessError(f"event {cur_id} has no IA INIT record")
                sorted_pixels: list[tuple[str, dict[str, float]]] = []
                tes_total = 0.0
                for uid, rec in sorted(pixels.items()):
                    energy = float(rec["energy"])
                    if energy <= 0.0:
                        continue
                    tes_total += energy
                    sorted_pixels.append((uid, rec))
                if sorted_pixels or active_total > 0.0:
                    tes_or_active_events += 1
                if not sorted_pixels and active_total > 0.0:
                    active_only_events += 1
                if sorted_pixels:
                    dz = float(cur_init["dir_z"])
                    event_writer.writerow(
                        {
                            "event_id": cur_id,
                            "init_x_cm": f"{float(cur_init['x_cm']):.10g}",
                            "init_y_cm": f"{float(cur_init['y_cm']):.10g}",
                            "init_z_cm": f"{float(cur_init['z_cm']):.10g}",
                            "dir_x": f"{float(cur_init['dir_x']):.10g}",
                            "dir_y": f"{float(cur_init['dir_y']):.10g}",
                            "dir_z": f"{dz:.10g}",
                            "source_theta_deg": f"{source_theta_deg(dz):.12g}",
                            "init_energy_keV": f"{float(cur_init['energy_keV']):.12g}",
                            "bin20": angular_bin_from_init_dir_z(dz, 20),
                            "bin40": angular_bin_from_init_dir_z(dz, 40),
                            "bin80": angular_bin_from_init_dir_z(dz, 80),
                            "tes_total_keV": f"{tes_total:.12g}",
                            "active_total_keV": f"{active_total:.12g}",
                            "pixel_count": len(sorted_pixels),
                        }
                    )
                    tes_events += 1
                    for uid, rec in sorted_pixels:
                        energy = float(rec["energy"])
                        pixel_writer.writerow(
                            {
                                "event_id": cur_id,
                                "pixel_uid": uid,
                                "layer": int(rec["layer"]),
                                "energy_keV": f"{energy:.12g}",
                                "x_cm": f"{float(rec['wx']) / energy:.12g}",
                                "y_cm": f"{float(rec['wy']) / energy:.12g}",
                                "z_cm": f"{float(rec['wz']) / energy:.12g}",
                            }
                        )
                        tes_pixel_hits += 1
                cur_id = None
                cur_init = None
                active_total = 0.0
                pixels = {}

            with gzip.open(sim, "rt", encoding="utf-8", errors="replace") as handle:
                for raw in handle:
                    line = raw.strip()
                    if line == "SE":
                        flush()
                        continue
                    match_id = id_re.match(line)
                    if match_id:
                        if cur_id is not None:
                            raise HarnessError(f"event {cur_id} was not terminated by SE")
                        cur_id = int(match_id.group(1))
                        generated += 1
                        continue
                    if line.startswith("IA INIT"):
                        if cur_id is None:
                            raise HarnessError("IA INIT encountered outside an event")
                        if cur_init is not None:
                            raise HarnessError(f"event {cur_id} has multiple IA INIT rows")
                        cur_init = parse_init(line)
                        init_records += 1
                        energy = float(cur_init["energy_keV"])
                        energy_min = energy if energy_min is None else min(energy_min, energy)
                        energy_max = energy if energy_max is None else max(energy_max, energy)
                        if abs(energy - expected_energy_keV) > energy_tolerance_keV:
                            energy_mismatch_records += 1
                        if int(cur_init["particle_type"]) != 1:
                            non_gamma_init_records += 1
                        for bins in (20, 40, 80):
                            angular[bins][angular_bin_from_init_dir_z(float(cur_init["dir_z"]), bins)] += 1
                        continue
                    if line.startswith("CC HIT "):
                        if cur_id is None:
                            raise HarnessError("CC HIT encountered outside an event")
                        match_hit = cc_re.match(line)
                        if match_hit is None:
                            raise HarnessError(f"malformed CC HIT: {line[:160]}")
                        volume = match_hit.group(1)
                        kv = dict(kv_re.findall(match_hit.group(2)))
                        try:
                            edep = float(kv["edep_keV"])
                            x = float(kv["x"])
                            y = float(kv["y"])
                            z = float(kv["z"])
                        except (KeyError, ValueError) as exc:
                            raise HarnessError(f"malformed CC HIT payload: {line[:160]}") from exc
                        match_tp = tp_re.match(volume)
                        if match_tp:
                            rec = pixels.setdefault(
                                volume,
                                {
                                    "energy": 0.0,
                                    "wx": 0.0,
                                    "wy": 0.0,
                                    "wz": 0.0,
                                    "layer": float(match_tp.group("layer")),
                                },
                            )
                            rec["energy"] += edep
                            rec["wx"] += edep * x
                            rec["wy"] += edep * y
                            rec["wz"] += edep * z
                        elif is_active_veto_volume(volume):
                            active_total += edep
                            active_volume_hit_records[volume] += 1
                            active_volume_energy_keV[volume] += edep
                        continue
                    if line.startswith("Geometry") and "geometry" not in header:
                        header["geometry"] = line.split(maxsplit=1)[1]
                    elif line.startswith("Seed") and "seed" not in header:
                        header["seed"] = int(line.split()[1])
                    elif line.startswith("SimulationStartAreaFarField"):
                        header["start_area_cm2"] = float(line.split()[1])
                    elif line.startswith("BeamType") and "beam_type_first" not in header:
                        header["beam_type_first"] = line
                    elif line.startswith("SpectralType") and "spectral_type_first" not in header:
                        header["spectral_type_first"] = line
                    elif line.startswith("MEGAlib"):
                        header["megalib"] = line.split(maxsplit=1)[1]
                    elif line.startswith("Version"):
                        header["sim_version"] = line.split(maxsplit=1)[1]
                    elif line.startswith("Date"):
                        header["created"] = line.split(maxsplit=1)[1]
                    elif line.startswith("TE "):
                        footer["TE_s"] = float(line.split()[1])
                    elif line.startswith("TS "):
                        footer["TS"] = int(line.split()[1])
            flush()
            event_handle.flush()
            pixel_handle.flush()
            os.fsync(event_handle.fileno())
            os.fsync(pixel_handle.fileno())

        geometry_header = Path(str(header.get("geometry", ""))).resolve()
        checks = {
            "header_geometry_is_o8_setup": geometry_header == O8_SETUP.resolve(),
            "header_seed_matches_source": header.get("seed") == expected_seed,
            "footer_ts_present": footer["TS"] is not None,
            "footer_te_positive": footer["TE_s"] is not None and footer["TE_s"] > 0.0,
            "footer_ts_matches_id_count": footer["TS"] == generated,
            "footer_ts_matches_init_count": footer["TS"] == init_records,
            "requested_events_match_footer_ts": footer["TS"] == expected_events,
            "all_init_are_gamma": non_gamma_init_records == 0,
            "all_init_energy_matches": energy_mismatch_records == 0,
            "angular20_closure": sum(angular[20]) == init_records,
            "angular40_closure": sum(angular[40]) == init_records,
            "angular80_closure": sum(angular[80]) == init_records,
        }
        failed = [name for name, value in checks.items() if not value]
        if failed:
            raise HarnessError(f"SIM parse validation failed: {failed}")

        os.replace(event_tmp, event_path)
        os.replace(pixel_tmp, pixel_path)
        angular_payload = {
            "schema": PARSE_SCHEMA,
            "mapping": (
                "mu_source=-IA_INIT.dir_z; equal-mu bin=floor((1+dir_z)*G/2), clipped"
            ),
            "init_records": init_records,
            "counts": {str(bins): values for bins, values in angular.items()},
        }
        atomic_write_json(angular_path, angular_payload)
        artifacts = {
            rel(path): {"sha256": sha256(path), "bytes": path.stat().st_size}
            for path in (event_path, pixel_path, angular_path)
        }
        provenance = {
            "schema": PARSE_SCHEMA,
            "status": "PASS_STREAM_PARSE_COMPLETE",
            "parsed_at_utc": utc_now(),
            "parser": {"path": rel(Path(__file__)), "sha256": sha256(Path(__file__))},
            "scope": "atmospheric annihilation mono line only",
            "proposal": proposal_name,
            "source_card": {
                "path": rel(source_card),
                "sha256": source_card_sha256,
            },
            "raw_sim": {
                "path": rel(sim),
                "sha256": sim_hash,
                "bytes": sim.stat().st_size,
                "raw_disposition": "SAFE_TO_DELETE_NOT_DELETED",
                "raw_deleted": False,
            },
            "sim_header": header,
            "geometry_authority": {
                "setup": authority["files"][rel(O8_SETUP)],
                "geo": authority["files"][rel(O8_GEO)],
                "det": authority["files"][rel(O8_DET)],
            },
            "transport_seed": expected_seed,
            "expected_energy_keV": expected_energy_keV,
            "energy_tolerance_keV": energy_tolerance_keV,
            "init_energy_min_keV": energy_min,
            "init_energy_max_keV": energy_max,
            "sim_footer": footer,
            "counts": {
                "generated_id_records": generated,
                "ia_init_records": init_records,
                "tes_events": tes_events,
                "tes_pixel_hits": tes_pixel_hits,
                "active_only_events": active_only_events,
                "tes_or_active_events": tes_or_active_events,
            },
            "active_veto_volume_audit": {
                "predicate": (
                    "CSI_ prefix OR ACTIVE_SHIELD substring OR ACTIVESHIELD substring OR "
                    "CEBR3 substring OR BGO substring OR S1 plastic prefix OR S2B plastic prefix"
                ),
                "hit_records_by_volume": dict(sorted(active_volume_hit_records.items())),
                "deposited_energy_keV_by_volume": dict(
                    sorted((key, float(value)) for key, value in active_volume_energy_keV.items())
                ),
                "known_o8_active_shield_named_passive_kapton_wrappers": list(
                    KNOWN_O8_ACTIVE_SHIELD_NAMED_WRAPPERS
                ),
                "naming_blocker": ACTIVE_VETO_NAMING_BLOCKER,
            },
            "checks": checks,
            "artifacts": artifacts,
            "claim_boundary": (
                "A validated compact parse makes the raw SIM eligible for an external "
                "retention decision; this harness did not delete it."
            ),
        }
        atomic_write_json(provenance_path, provenance)
        atomic_write_json(
            marker_path,
            {
                "status": "SAFE_TO_DELETE_NOT_DELETED",
                "raw_sim": provenance["raw_sim"],
                "validated_provenance": rel(provenance_path),
                "validated_provenance_sha256": sha256(provenance_path),
                "warning": "This is a marker, not a deletion instruction.",
            },
        )
        return provenance
    finally:
        for tmp in (event_tmp, pixel_tmp):
            if tmp.exists():
                tmp.unlink()


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise HarnessError(f"cannot import module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def package44_cosima_environment() -> tuple[dict[str, str], dict[str, Any]]:
    """Reuse the exact minimal environment frozen by the validated package44 runner."""
    if not PACKAGE44_RUNNER.is_file() or sha256(PACKAGE44_RUNNER) != PACKAGE44_RUNNER_SHA256:
        raise HarnessError("package44 runtime authority is missing or changed")
    runner_code = str(PACKAGE44_RUNNER.parent)
    inserted = runner_code not in sys.path
    if inserted:
        sys.path.insert(0, runner_code)
    try:
        runtime = load_module("o8_parma511_package44_runtime", PACKAGE44_RUNNER)
    finally:
        if inserted:
            sys.path.remove(runner_code)
    env = dict(runtime.EXPECTED_COSIMA_LAUNCH_ENVIRONMENT)
    expected_cosima = Path(runtime.EXPECTED_MEGALIB_ROOT) / "bin/cosima"
    if expected_cosima.resolve() != COSIMA_DEFAULT.resolve():
        raise HarnessError(f"package44 Cosima path changed: {expected_cosima}")
    if not expected_cosima.is_file() or not os.access(expected_cosima, os.X_OK):
        raise HarnessError(f"package44 Cosima is missing/not executable: {expected_cosima}")
    binary_hash = sha256(expected_cosima)
    if binary_hash != COSIMA_BINARY_SHA256:
        raise HarnessError(f"Cosima binary hash changed: {binary_hash}")
    required_paths = {
        key: value
        for key, value in env.items()
        if key == "MEGALIB" or key.startswith("G4")
    }
    missing = [key for key, value in required_paths.items() if not Path(value).exists()]
    ld_paths = env.get("LD_LIBRARY_PATH", "").split(":")
    missing_ld = [value for value in ld_paths if not value or not Path(value).is_dir()]
    if missing or missing_ld:
        raise HarnessError(
            f"package44 runtime paths missing: variables={missing}, LD_LIBRARY_PATH={missing_ld}"
        )
    expected_ld = ":".join(
        (
            "/home/ubuntu/MEGAlib_Install/megalib-main/lib",
            "/home/ubuntu/MEGAlib_Install/megalib-main/external/root_v6.36.6/lib",
            "/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/lib",
        )
    )
    if env.get("LD_LIBRARY_PATH") != expected_ld:
        raise HarnessError("package44 MEGAlib/ROOT/Geant4 LD_LIBRARY_PATH changed")
    evidence = {
        "status": "PASS_PACKAGE44_EXACT_MINIMAL_COSIMA_ENVIRONMENT",
        "package44_runner": {
            "path": rel(PACKAGE44_RUNNER),
            "sha256": PACKAGE44_RUNNER_SHA256,
        },
        "cosima": {
            "path": str(expected_cosima),
            "sha256": binary_hash,
            "bytes": expected_cosima.stat().st_size,
        },
        "launch_environment": dict(sorted(env.items())),
        "launch_environment_canonical_sha256": canonical_sha256(dict(sorted(env.items()))),
        "parent_environment_inherited": False,
        "rootsys_present": "ROOTSYS" in env,
        "ld_library_path_components": ld_paths,
    }
    return env, evidence


def cosima_runtime_probe() -> tuple[dict[str, str], dict[str, Any]]:
    """Run only ``cosima -h`` under the exact package44 environment."""
    env, evidence = package44_cosima_environment()
    cosima = evidence["cosima"]["path"]
    try:
        completed = subprocess.run(
            [cosima, "-h"],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise HarnessError("Cosima -h runtime probe timed out") from exc
    output = completed.stdout or b""
    if completed.returncode != 0:
        tail = output.decode("utf-8", errors="replace")[-2000:]
        raise HarnessError(
            f"Cosima -h runtime probe failed rc={completed.returncode}: {tail}"
        )
    evidence["runtime_probe"] = {
        "status": "PASS_COSIMA_HELP_RUNTIME_PROBE_NO_SOURCE_TRANSPORT",
        "command": [cosima, "-h"],
        "returncode": completed.returncode,
        "combined_output_bytes": len(output),
        "combined_output_sha256": hashlib.sha256(output).hexdigest(),
        "first_lines": output.decode("utf-8", errors="replace").splitlines()[:12],
        "source_card_argument_present": False,
        "transport_launched": False,
    }
    return env, evidence


def preflight_report() -> dict[str, Any]:
    report = authority_report()
    _, runtime = cosima_runtime_probe()
    report["cosima_runtime"] = runtime
    report["status"] = "PASS_O8_PARMA511_LINE_ONLY_PREFLIGHT_AND_COSIMA_RUNTIME"
    return report


def load_step05() -> tuple[Any, dict[str, Any]]:
    verify_hash(STEP05_IMPLEMENTATION)
    verify_hash(STEP09_SUMMARY)
    step05 = load_module("o8_parma511_frozen_step05", STEP05_IMPLEMENTATION)
    step05.ROOT = ROOT
    step05.STEP09_SUMMARY = STEP09_SUMMARY
    step05.is_v3p5_active_veto_volume = is_active_veto_volume
    return step05, step05.side_entry_disk()


def load_parsed_catalog(parsed_dir: Path) -> list[dict[str, Any]]:
    provenance = load_json(parsed_dir / "provenance.json")
    if provenance.get("status") != "PASS_STREAM_PARSE_COMPLETE":
        raise HarnessError("parsed catalogue lacks PASS provenance")
    events: list[dict[str, Any]] = []
    by_id: dict[int, dict[str, Any]] = {}
    with (parsed_dir / "tes_events.csv").open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            event = {
                "event_id": int(raw["event_id"]),
                "dir_x": float(raw["dir_x"]),
                "dir_y": float(raw["dir_y"]),
                "dir_z": float(raw["dir_z"]),
                "init_energy_keV": float(raw["init_energy_keV"]),
                "tes_total_keV": float(raw["tes_total_keV"]),
                "active_total_keV": float(raw["active_total_keV"]),
                "pixels": [],
            }
            events.append(event)
            by_id[event["event_id"]] = event
    with (parsed_dir / "tes_pixel_hits.csv").open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            event_id = int(raw["event_id"])
            if event_id not in by_id:
                raise HarnessError(f"pixel row has unknown event id {event_id}")
            by_id[event_id]["pixels"].append(
                {
                    "pixel_uid": raw["pixel_uid"],
                    "layer": int(raw["layer"]),
                    "energy_keV": float(raw["energy_keV"]),
                    "x_cm": float(raw["x_cm"]),
                    "y_cm": float(raw["y_cm"]),
                    "z_cm": float(raw["z_cm"]),
                }
            )
    if len(events) != int(provenance["counts"]["tes_events"]):
        raise HarnessError("TES event count does not match provenance")
    if sum(len(event["pixels"]) for event in events) != int(
        provenance["counts"]["tes_pixel_hits"]
    ):
        raise HarnessError("pixel count does not match provenance")
    return events


def old_proposal_rows() -> list[dict[str, Any]]:
    verify_hash(OLD_SOURCE)
    text = OLD_SOURCE.read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for bin_id in range(20):
        suffix = "down" if bin_id < 10 else "up"
        source_id = f"Atm511_bin{bin_id:02d}_{suffix}"
        flux = re.search(
            rf"^{re.escape(source_id)}\.Flux\s+([-+0-9.eE]+)\s*$", text, re.M
        )
        if flux is None:
            raise HarnessError(f"old proposal flux missing: {source_id}")
        rows.append(
            {
                "bin_id": bin_id,
                "source_id": source_id,
                "flux_ph_cm2_s": float(flux.group(1)),
            }
        )
    return rows


def importance_ratio(
    dir_z: float,
    target_rows: list[dict[str, Any]],
    proposal_rows: list[dict[str, Any]],
) -> float:
    target_bins = len(target_rows)
    proposal_bins = len(proposal_rows)
    target = target_rows[angular_bin_from_init_dir_z(dir_z, target_bins)]
    proposal = proposal_rows[angular_bin_from_init_dir_z(dir_z, proposal_bins)]
    # Both sources are piecewise uniform in mu. Divide bin-integrated flux by
    # delta-mu before taking the density ratio.
    return (
        (target_bins / proposal_bins)
        * float(target["flux_ph_cm2_s"])
        / float(proposal["flux_ph_cm2_s"])
    )


def weighted_selection(
    selected: Iterable[dict[str, Any]],
    *,
    te_s: float,
    proposal_rows: list[dict[str, Any]],
    target_rows: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    selected_list = list(selected)
    out: dict[str, Any] = {}
    all_weights: dict[int, list[float]] = {}
    for bins in (20, 40, 80):
        weights = [
            importance_ratio(float(row["dir_z"]), target_rows[bins], proposal_rows) / te_s
            for row in selected_list
        ]
        all_weights[bins] = weights
        rate = float(sum(weights))
        variance = float(sum(value * value for value in weights))
        sigma = math.sqrt(variance)
        out[str(bins)] = {
            "selected_events": len(weights),
            "importance_weighted_rate_cps": rate,
            "mc_stat_sigma_cps": sigma,
            "mc_relative_sigma": sigma / rate if rate > 0.0 else None,
            "importance_effective_sample_size": rate * rate / variance if variance > 0.0 else 0.0,
        }
    rate80 = out["80"]["importance_weighted_rate_cps"]
    paired_delta = [
        left - right for left, right in zip(all_weights[40], all_weights[80])
    ]
    paired_delta_sigma = math.sqrt(sum(value * value for value in paired_delta))
    absolute_relative_difference = (
        abs(out["40"]["importance_weighted_rate_cps"] - rate80) / rate80
        if rate80
        else None
    )
    paired_relative_sigma = paired_delta_sigma / rate80 if rate80 else None
    out["paired_diagnostics"] = {
        "relative_20_minus_80": (
            out["20"]["importance_weighted_rate_cps"] / rate80 - 1.0 if rate80 else None
        ),
        "relative_40_minus_80": (
            out["40"]["importance_weighted_rate_cps"] / rate80 - 1.0 if rate80 else None
        ),
        "paired_40_minus_80_mc_sigma_cps": paired_delta_sigma,
        "absolute_relative_40_vs_80": absolute_relative_difference,
        "paired_relative_40_minus_80_mc_sigma": paired_relative_sigma,
        "combined_relative_40_vs_80_error": (
            absolute_relative_difference + paired_relative_sigma
            if absolute_relative_difference is not None and paired_relative_sigma is not None
            else None
        ),
        "combined_definition": (
            "abs(rate40-rate80)/rate80 + sqrt(sum_i((w40_i-w80_i)^2))/rate80; "
            "the second term preserves same-event pairing"
        ),
    }
    return out


def detector_rate_gate(weighted: dict[str, Any]) -> dict[str, Any]:
    count = int(weighted["80"]["selected_events"])
    ess = float(weighted["80"]["importance_effective_sample_size"])
    rse = weighted["80"]["mc_relative_sigma"]
    combined = weighted["paired_diagnostics"]["combined_relative_40_vs_80_error"]
    count_or_rse = count >= 400 or (rse is not None and float(rse) <= 0.05)
    angular = combined is not None and float(combined) < 0.015
    passed = bool(count_or_rse and angular)
    return {
        "status": "PASS_PARMA511_LINE_MODULE_RATE_GATE" if passed else "DIAGNOSTIC_ONLY_FAIL_LINE_MODULE_RATE_GATE",
        "selected_events_80bin": count,
        "importance_effective_sample_size_80bin": ess,
        "relative_standard_error_80bin": rse,
        "required_final_events_or_rse": ">=400 final events OR RSE<=0.05",
        "passes_count_or_rse": count_or_rse,
        "combined_relative_40_vs_80_error": combined,
        "required_combined_relative_40_vs_80_error": "<0.015",
        "passes_angular_paired_error": angular,
        "passes_detector_rate_gate": passed,
    }


def wilson_interval(successes: int, trials: int) -> tuple[float, float]:
    """Two-sided 95% Wilson score interval for a binomial probability."""
    if trials < 0 or successes < 0 or successes > trials:
        raise HarnessError(f"invalid binomial counts: {successes}/{trials}")
    if trials == 0:
        return 0.0, 1.0
    z = 1.959963984540054
    n = float(trials)
    p = successes / n
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denominator
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def exact_zero_success_upper95(trials: int) -> float:
    """Exact one-sided 95% upper bound when zero successes are observed."""
    if trials < 0:
        raise HarnessError("negative binomial trial count")
    return 1.0 if trials == 0 else 1.0 - 0.05 ** (1.0 / trials)


def start_area_from_provenance(provenance: dict[str, Any]) -> float:
    header = provenance["sim_header"]
    if "start_area_cm2" in header:
        value = float(header["start_area_cm2"])
        if value <= 0.0:
            raise HarnessError("non-positive SIM start area")
        return value
    batch_headers = header.get("batch_headers", [])
    values = sorted(set(float(row["start_area_cm2"]) for row in batch_headers))
    if len(values) != 1 or values[0] <= 0.0:
        raise HarnessError(f"campaign start areas are not identical and positive: {values}")
    return values[0]


def angular_response_coefficients(
    *,
    parsed_dir: Path,
    output_dir: Path,
    events: list[dict[str, Any]],
    unsmeared_details: list[dict[str, Any]],
    primary_details: list[dict[str, Any]],
    provenance: dict[str, Any],
    proposal_rows: list[dict[str, Any]],
    target_rows: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    angular = load_json(parsed_dir / "angular_counts.json")
    start_area_cm2 = start_area_from_provenance(provenance)
    te_s = float(provenance["sim_footer"]["TE_s"])
    if te_s <= 0.0:
        raise HarnessError("non-positive TE in angular response")
    if len(events) != len(unsmeared_details) or len(events) != len(primary_details):
        raise HarnessError("angular response event/detail lengths do not match")
    artifacts: dict[str, Any] = {}
    summaries: dict[str, Any] = {}
    for bins in (20, 40, 80):
        n_init = [int(value) for value in angular["counts"][str(bins)]]
        if len(n_init) != bins or sum(n_init) != int(provenance["sim_footer"]["TS"]):
            raise HarnessError(f"{bins}-bin INIT counts failed angular response closure")
        n_tes = [0] * bins
        n_unsmeared = [0] * bins
        n_primary = [0] * bins
        rate_unsmeared = [0.0] * bins
        rate_primary = [0.0] * bins
        for event, unsmeared, primary in zip(events, unsmeared_details, primary_details):
            bin_id = angular_bin_from_init_dir_z(float(event["dir_z"]), bins)
            n_tes[bin_id] += 1
            ratio = importance_ratio(
                float(event["dir_z"]), target_rows[bins], proposal_rows
            )
            if bool(unsmeared["final_w2"]):
                n_unsmeared[bin_id] += 1
                rate_unsmeared[bin_id] += ratio / te_s
            if bool(primary["final_w2"]):
                n_primary[bin_id] += 1
                rate_primary[bin_id] += ratio / te_s
        path = output_dir / f"angular_response_coefficients_{bins}bins.csv"
        fields = [
            "bin_id",
            "theta_low_deg",
            "theta_high_deg",
            "target_flux_ph_cm2_s",
            "N_init",
            "N_TES",
            "N_unsmeared_W2",
            "N_primary_W2",
            "q_TES",
            "q_unsmeared_W2",
            "q_primary_W2",
            "q_unsmeared_W2_wilson95_low",
            "q_unsmeared_W2_wilson95_high",
            "q_primary_W2_wilson95_low",
            "q_primary_W2_wilson95_high",
            "q_unsmeared_zero_count_upper95",
            "q_primary_zero_count_upper95",
            "response_unsmeared_cm2",
            "response_primary_cm2",
            "response_unsmeared_wilson95_low_cm2",
            "response_unsmeared_wilson95_high_cm2",
            "response_primary_wilson95_low_cm2",
            "response_primary_wilson95_high_cm2",
            "importance_rate_unsmeared_cps",
            "importance_rate_primary_cps",
            "importance_response_unsmeared_cm2",
            "importance_response_primary_cm2",
        ]
        with path.open("x", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for bin_id, target in enumerate(target_rows[bins]):
                trials = n_init[bin_id]
                q_tes = n_tes[bin_id] / trials if trials else 0.0
                q_u = n_unsmeared[bin_id] / trials if trials else 0.0
                q_p = n_primary[bin_id] / trials if trials else 0.0
                u_lo, u_hi = wilson_interval(n_unsmeared[bin_id], trials)
                p_lo, p_hi = wilson_interval(n_primary[bin_id], trials)
                flux = float(target["flux_ph_cm2_s"])
                writer.writerow(
                    {
                        "bin_id": bin_id,
                        "theta_low_deg": target["theta_low_deg"],
                        "theta_high_deg": target["theta_high_deg"],
                        "target_flux_ph_cm2_s": flux,
                        "N_init": trials,
                        "N_TES": n_tes[bin_id],
                        "N_unsmeared_W2": n_unsmeared[bin_id],
                        "N_primary_W2": n_primary[bin_id],
                        "q_TES": q_tes,
                        "q_unsmeared_W2": q_u,
                        "q_primary_W2": q_p,
                        "q_unsmeared_W2_wilson95_low": u_lo,
                        "q_unsmeared_W2_wilson95_high": u_hi,
                        "q_primary_W2_wilson95_low": p_lo,
                        "q_primary_W2_wilson95_high": p_hi,
                        "q_unsmeared_zero_count_upper95": (
                            exact_zero_success_upper95(trials)
                            if n_unsmeared[bin_id] == 0
                            else ""
                        ),
                        "q_primary_zero_count_upper95": (
                            exact_zero_success_upper95(trials)
                            if n_primary[bin_id] == 0
                            else ""
                        ),
                        "response_unsmeared_cm2": q_u * start_area_cm2,
                        "response_primary_cm2": q_p * start_area_cm2,
                        "response_unsmeared_wilson95_low_cm2": u_lo * start_area_cm2,
                        "response_unsmeared_wilson95_high_cm2": u_hi * start_area_cm2,
                        "response_primary_wilson95_low_cm2": p_lo * start_area_cm2,
                        "response_primary_wilson95_high_cm2": p_hi * start_area_cm2,
                        "importance_rate_unsmeared_cps": rate_unsmeared[bin_id],
                        "importance_rate_primary_cps": rate_primary[bin_id],
                        "importance_response_unsmeared_cm2": (
                            rate_unsmeared[bin_id] / flux if flux > 0.0 else ""
                        ),
                        "importance_response_primary_cm2": (
                            rate_primary[bin_id] / flux if flux > 0.0 else ""
                        ),
                    }
                )
        artifacts[str(bins)] = {
            "path": rel(path),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
        }
        summaries[str(bins)] = {
            "N_init": sum(n_init),
            "N_TES": sum(n_tes),
            "N_unsmeared_W2": sum(n_unsmeared),
            "N_primary_W2": sum(n_primary),
            "bins_with_zero_unsmeared_W2": sum(value == 0 for value in n_unsmeared),
            "bins_with_zero_primary_W2": sum(value == 0 for value in n_primary),
            "importance_rate_unsmeared_cps": sum(rate_unsmeared),
            "importance_rate_primary_cps": sum(rate_primary),
        }
    return {
        "definition": (
            "q=N_stage/N_init in each INIT-direction bin; response_cm2=q*SIM start area. "
            "importance_response_cm2 uses the same-event target/proposal rate divided by "
            "the target bin flux. Intervals are two-sided 95% Wilson; zero-count upper "
            "limits are exact one-sided 95%."
        ),
        "start_area_cm2": start_area_cm2,
        "summaries": summaries,
        "artifacts": artifacts,
    }


def evaluate_events(
    events: list[dict[str, Any]],
    step05: Any,
    disk: dict[str, Any],
    *,
    seed: int | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw_energies = np.asarray(
        [pixel["energy_keV"] for event in events for pixel in event["pixels"]],
        dtype=np.float64,
    )
    if seed is None:
        measured = raw_energies.copy()
    else:
        measured = raw_energies + np.random.default_rng(seed).normal(
            0.0, SIGMA_KEV, len(raw_energies)
        )
        measured[measured < TES_THRESHOLD_KEV] = 0.0
    cursor = 0
    details: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    for event in events:
        count = len(event["pixels"])
        hit_energy = measured[cursor : cursor + count]
        cursor += count
        hits: list[Any] = []
        for pixel, energy in zip(event["pixels"], hit_energy):
            if float(energy) <= 0.0:
                continue
            hits.append(
                SimpleNamespace(
                    x=float(pixel["x_cm"]),
                    y=float(pixel["y_cm"]),
                    z=float(pixel["z_cm"]),
                    e=float(energy),
                    pixel_uid=str(pixel["pixel_uid"]),
                    layer=int(pixel["layer"]),
                )
            )
        total = float(sum(hit.e for hit in hits))
        active_pass = float(event["active_total_keV"]) < ACTIVE_THRESHOLD_KEV
        broad = BROAD_WINDOW_KEV[0] <= total < BROAD_WINDOW_KEV[1]
        keep = False
        classification = "not_evaluated"
        if broad and active_pass:
            if len(hits) == 1:
                keep = True
                classification = "single"
            elif len(hits) > int(step05.MAX_ENUM_HITS):
                keep = True
                classification = "reject_kept"
            elif len(hits) >= 2:
                accepted, classification_raw = step05.side_keep_from_hits(hits, disk, "keep")
                keep = bool(accepted)
                classification = str(classification_raw)
            else:
                classification = "zero_after_threshold"
        class_counts[classification] += 1
        raw_w2 = W2_WINDOW_KEV[0] <= total < W2_WINDOW_KEV[1]
        details.append(
            {
                "event_id": int(event["event_id"]),
                "dir_z": float(event["dir_z"]),
                "measured_total_keV": total,
                "measured_multiplicity": len(hits),
                "active_total_keV": float(event["active_total_keV"]),
                "raw_w2": raw_w2,
                "active_w2": raw_w2 and active_pass,
                "final_w2": raw_w2 and active_pass and keep,
                "topology_class": classification,
            }
        )
    if cursor != len(measured):
        raise HarnessError("response hit cursor did not close")
    final_rows = [row for row in details if row["final_w2"]]
    summary = {
        "response_seed": seed,
        "tes_events": len(events),
        "pixel_hits_before_response": len(raw_energies),
        "w2_raw_events": sum(int(row["raw_w2"]) for row in details),
        "w2_active_veto_pass_events": sum(int(row["active_w2"]) for row in details),
        "w2_frozen_step05_pass_events": sum(int(row["final_w2"]) for row in details),
        "w2_final_active_energy_max_keV": (
            max(float(row["active_total_keV"]) for row in final_rows)
            if final_rows
            else None
        ),
        "topology_class_counts": dict(sorted(class_counts.items())),
    }
    return summary, details


def response_analysis(
    *,
    parsed_dir: Path,
    output_dir: Path,
    proposal: str,
    replicas: int = DEFAULT_RESPONSE_REPLICAS,
) -> dict[str, Any]:
    if replicas < 1 or replicas > 10_000:
        raise HarnessError("response replicas must be in [1, 10000]")
    provenance = load_json(parsed_dir / "provenance.json")
    if provenance.get("status") != "PASS_STREAM_PARSE_COMPLETE":
        raise HarnessError("response input does not have validated parse provenance")
    events = load_parsed_catalog(parsed_dir)
    step05, disk = load_step05()
    targets = {bins: parse_grid(bins) for bins in (20, 40, 80)}
    if proposal == "old20":
        proposal_rows = old_proposal_rows()
    elif proposal == "parma80":
        proposal_rows = targets[80]
    else:
        raise HarnessError("proposal must be old20 or parma80")
    te_s = float(provenance["sim_footer"]["TE_s"])
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "response_64seed_summary.json"
    seeds_path = output_dir / "response_seed_replicas.csv"
    primary_path = output_dir / "primary_event_response.csv"
    for path in (summary_path, seeds_path, primary_path):
        if path.exists():
            raise HarnessError(f"refusing to overwrite response output: {path}")

    unsmeared_summary, unsmeared_details = evaluate_events(
        events, step05, disk, seed=None
    )
    unsmeared_selected = [row for row in unsmeared_details if row["final_w2"]]
    unsmeared_summary["paired_reweight"] = weighted_selection(
        unsmeared_selected,
        te_s=te_s,
        proposal_rows=proposal_rows,
        target_rows=targets,
    )
    replica_rows: list[dict[str, Any]] = []
    primary_details: list[dict[str, Any]] | None = None
    primary_summary: dict[str, Any] | None = None
    for index in range(replicas):
        seed = PRIMARY_ATM_RESPONSE_SEED + index * RESPONSE_SEED_STRIDE
        result, details = evaluate_events(events, step05, disk, seed=seed)
        selected = [row for row in details if row["final_w2"]]
        reweighted = weighted_selection(
            selected,
            te_s=te_s,
            proposal_rows=proposal_rows,
            target_rows=targets,
        )
        row: dict[str, Any] = {
            "replica_index": index,
            "response_seed": seed,
            "w2_raw_events": result["w2_raw_events"],
            "w2_active_veto_pass_events": result["w2_active_veto_pass_events"],
            "w2_frozen_step05_pass_events": result["w2_frozen_step05_pass_events"],
        }
        for bins in (20, 40, 80):
            weighted = reweighted[str(bins)]
            row[f"rate_{bins}bin_cps"] = weighted["importance_weighted_rate_cps"]
            row[f"mc_sigma_{bins}bin_cps"] = weighted["mc_stat_sigma_cps"]
            row[f"ess_{bins}bin"] = weighted["importance_effective_sample_size"]
        row["relative_20_minus_80"] = reweighted["paired_diagnostics"]["relative_20_minus_80"]
        row["relative_40_minus_80"] = reweighted["paired_diagnostics"]["relative_40_minus_80"]
        replica_rows.append(row)
        if index == 0:
            result["paired_reweight"] = reweighted
            primary_summary = result
            primary_details = details
    assert primary_summary is not None and primary_details is not None

    with seeds_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(replica_rows[0]))
        writer.writeheader()
        writer.writerows(replica_rows)
    with primary_path.open("x", encoding="utf-8", newline="") as handle:
        fields = [
            "event_id",
            "dir_z",
            "measured_total_keV",
            "measured_multiplicity",
            "active_total_keV",
            "raw_w2",
            "active_w2",
            "final_w2",
            "topology_class",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(primary_details)
    angular_response = angular_response_coefficients(
        parsed_dir=parsed_dir,
        output_dir=output_dir,
        events=events,
        unsmeared_details=unsmeared_details,
        primary_details=primary_details,
        provenance=provenance,
        proposal_rows=proposal_rows,
        target_rows=targets,
    )
    final_counts = np.asarray(
        [row["w2_frozen_step05_pass_events"] for row in replica_rows], dtype=float
    )
    rate80 = np.asarray([row["rate_80bin_cps"] for row in replica_rows], dtype=float)
    summary = {
        "schema": RESPONSE_SCHEMA,
        "status": "DIAGNOSTIC_ONLY_LINE_MODULE_RESPONSE_NOT_MANUSCRIPT_PASS",
        "created_at_utc": utc_now(),
        "scope": "atmospheric annihilation mono line only",
        "input_parse": {
            "path": rel(parsed_dir / "provenance.json"),
            "sha256": sha256(parsed_dir / "provenance.json"),
        },
        "proposal": proposal,
        "transport_footer": provenance["sim_footer"],
        "detector_response": {
            "fwhm_keV": FWHM_KEV,
            "sigma_keV": SIGMA_KEV,
            "tes_threshold_keV": TES_THRESHOLD_KEV,
            "active_threshold_keV": ACTIVE_THRESHOLD_KEV,
            "primary_seed": PRIMARY_ATM_RESPONSE_SEED,
            "seed_stride": RESPONSE_SEED_STRIDE,
            "replicas": replicas,
            "step05_implementation": rel(STEP05_IMPLEMENTATION),
            "step05_sha256": sha256(STEP05_IMPLEMENTATION),
            "step09_summary": rel(STEP09_SUMMARY),
            "step09_summary_sha256": sha256(STEP09_SUMMARY),
            "topology_contract": (
                "broad 480<=E<550, active<50; single keep; multiplicity>MAX_ENUM_HITS "
                "reject_kept; otherwise frozen side_keep_from_hits(...,'keep')"
            ),
            "active_veto_predicate_blocker": ACTIVE_VETO_NAMING_BLOCKER,
            "active_shield_named_passive_kapton_wrappers_in_o8": list(
                KNOWN_O8_ACTIVE_SHIELD_NAMED_WRAPPERS
            ),
        },
        "unsmeared": unsmeared_summary,
        "primary_420eV": primary_summary,
        "primary_detector_rate_gate": detector_rate_gate(
            primary_summary["paired_reweight"]
        ),
        "angular_response_coefficients": angular_response,
        "ensemble": {
            "final_w2_count_mean": float(np.mean(final_counts)),
            "final_w2_count_sample_std": float(np.std(final_counts, ddof=1)) if replicas > 1 else 0.0,
            "rate_80bin_cps_mean": float(np.mean(rate80)),
            "rate_80bin_cps_sample_std": float(np.std(rate80, ddof=1)) if replicas > 1 else 0.0,
            "note": "Response seeds are not independent transported photons.",
        },
        "artifacts": {
            rel(seeds_path): {"sha256": sha256(seeds_path), "bytes": seeds_path.stat().st_size},
            rel(primary_path): {"sha256": sha256(primary_path), "bytes": primary_path.stat().st_size},
            **{
                record["path"]: {
                    "sha256": record["sha256"],
                    "bytes": record["bytes"],
                }
                for record in angular_response["artifacts"].values()
            },
        },
        "claim_boundary": (
            "20/40/80 are paired offline weights on the same transported events. "
            "Low W2 statistics can diagnose but cannot establish a detector-rate PASS."
        ),
    }
    atomic_write_json(summary_path, summary)
    return summary


def analyze_batch(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.manifest.resolve()
    manifest = load_campaign(manifest_path)
    batch = manifest_batch(manifest, args.batch)
    if batch.get("status") == "PARSED_AND_RESPONSE_DIAGNOSTIC_COMPLETE":
        verified_batch_compact_receipt(manifest_path=manifest_path, batch=batch)
        parsed_dir = path_from_manifest(batch["parsed_dir"])
        return {
            "status": "PARSED_AND_RESPONSE_DIAGNOSTIC_COMPLETE",
            "parse": load_json(parsed_dir / "provenance.json"),
            "response": load_json(path_from_manifest(batch["response_summary"])),
            "analysis_receipt": "IDEMPOTENT_EXISTING_BATCH_VERIFIED",
            "raw_deleted": False,
        }
    update_manifest_batch(
        manifest_path,
        args.batch,
        {"status": "ANALYZING_COMPACT_AND_RESPONSE", "analysis_started_at_utc": utc_now()},
        expected_statuses={
            "TRANSPORT_COMPLETE_UNPARSED",
            "PREPARED_NOT_RUN",
            "ANALYSIS_FAILED",
        },
    )
    sim = path_from_manifest(batch["expected_sim"])
    parsed_dir = path_from_manifest(batch["parsed_dir"])
    try:
        provenance = stream_parse_sim(
            sim=sim,
            output_dir=parsed_dir,
            expected_seed=int(batch["transport_seed"]),
            expected_energy_keV=PARMA_LINE_ENERGY_KEV,
            expected_events=int(batch["events_requested"]),
            source_card=path_from_manifest(batch["source_card"]),
            source_card_sha256=str(batch["source_card_sha256"]),
            proposal_name="parma80_physical_flux",
        )
        response_dir = parsed_dir / "response"
        response = response_analysis(
            parsed_dir=parsed_dir,
            output_dir=response_dir,
            proposal="parma80",
            replicas=args.response_replicas,
        )
    except Exception as exc:
        try:
            update_manifest_batch(
                manifest_path,
                args.batch,
                {
                    "status": "ANALYSIS_FAILED",
                    "analysis_failed_at_utc": utc_now(),
                    "analysis_error": str(exc),
                    "raw_disposition": "DO_NOT_DELETE_ANALYSIS_FAILED",
                },
                expected_statuses={"ANALYZING_COMPACT_AND_RESPONSE"},
            )
        except Exception:
            pass
        if isinstance(exc, HarnessError):
            raise
        raise HarnessError(f"batch analysis failed: {exc}") from exc
    update_manifest_batch(
        manifest_path,
        args.batch,
        {
            "status": "PARSED_AND_RESPONSE_DIAGNOSTIC_COMPLETE",
            "parse_provenance": rel(parsed_dir / "provenance.json"),
            "parse_provenance_sha256": sha256(parsed_dir / "provenance.json"),
            "response_summary": rel(response_dir / "response_64seed_summary.json"),
            "response_summary_sha256": sha256(response_dir / "response_64seed_summary.json"),
            "raw_disposition": "SAFE_TO_DELETE_NOT_DELETED",
            "raw_deleted": False,
        },
        expected_statuses={"ANALYZING_COMPACT_AND_RESPONSE"},
    )
    return {
        "status": "PARSED_AND_RESPONSE_DIAGNOSTIC_COMPLETE",
        "parse": provenance,
        "response": response,
        "raw_deleted": False,
    }


def verified_batch_compact_receipt(
    *, manifest_path: Path, batch: dict[str, Any]
) -> dict[str, Any]:
    parsed_dir = path_from_manifest(batch["parsed_dir"])
    provenance_path = parsed_dir / "provenance.json"
    if not provenance_path.is_file():
        raise HarnessError(f"batch {batch['batch_index']} has no compact provenance")
    provenance_hash = sha256(provenance_path)
    if batch.get("parse_provenance_sha256") != provenance_hash:
        raise HarnessError(f"batch {batch['batch_index']} provenance hash mismatch")
    provenance = load_json(provenance_path)
    if provenance.get("status") != "PASS_STREAM_PARSE_COMPLETE":
        raise HarnessError(f"batch {batch['batch_index']} compact parse is not PASS")
    expected_sim = path_from_manifest(batch["expected_sim"]).resolve()
    recorded_sim = path_from_manifest(provenance["raw_sim"]["path"]).resolve()
    expected_source = path_from_manifest(batch["source_card"]).resolve()
    recorded_source = path_from_manifest(provenance["source_card"]["path"]).resolve()
    checks = {
        "raw_path_matches_manifest": recorded_sim == expected_sim,
        "raw_sha_recorded": bool(re.fullmatch(r"[0-9a-f]{64}", provenance["raw_sim"]["sha256"])),
        "source_path_matches_manifest": recorded_source == expected_source,
        "source_sha_matches_manifest": provenance["source_card"]["sha256"] == batch["source_card_sha256"],
        "transport_seed_matches": int(provenance["transport_seed"]) == int(batch["transport_seed"]),
        "energy_matches": float(provenance["expected_energy_keV"]) == PARMA_LINE_ENERGY_KEV,
        "footer_ts_matches_requested": int(provenance["sim_footer"]["TS"]) == int(batch["events_requested"]),
        "footer_te_positive": float(provenance["sim_footer"]["TE_s"]) > 0.0,
        "id_count_matches_ts": int(provenance["counts"]["generated_id_records"]) == int(provenance["sim_footer"]["TS"]),
        "ia_count_matches_ts": int(provenance["counts"]["ia_init_records"]) == int(provenance["sim_footer"]["TS"]),
        "parse_checks_all_true": all(bool(value) for value in provenance["checks"].values()),
        "o8_setup_hash_matches": provenance["geometry_authority"]["setup"]["sha256"] == EXPECTED_SHA256[O8_SETUP],
        "o8_geo_hash_matches": provenance["geometry_authority"]["geo"]["sha256"] == EXPECTED_SHA256[O8_GEO],
        "o8_det_hash_matches": provenance["geometry_authority"]["det"]["sha256"] == EXPECTED_SHA256[O8_DET],
    }
    artifact_rows: dict[str, Any] = {}
    for recorded_path, record in provenance["artifacts"].items():
        path = path_from_manifest(recorded_path)
        if not path.is_file() or sha256(path) != record["sha256"]:
            raise HarnessError(
                f"batch {batch['batch_index']} compact artifact failed hash: {path}"
            )
        artifact_rows[path.name] = {
            "path": rel(path),
            "sha256": record["sha256"],
            "bytes": path.stat().st_size,
        }
    if set(artifact_rows) != {"tes_events.csv", "tes_pixel_hits.csv", "angular_counts.json"}:
        raise HarnessError(f"batch {batch['batch_index']} compact artifact set is incomplete")
    angular = load_json(parsed_dir / "angular_counts.json")
    angular_checks = {
        f"angular_{bins}_sum_matches_ts": sum(int(value) for value in angular["counts"][str(bins)])
        == int(provenance["sim_footer"]["TS"])
        for bins in (20, 40, 80)
    }
    checks.update(angular_checks)
    response_path = path_from_manifest(batch["response_summary"])
    if not response_path.is_file() or sha256(response_path) != batch["response_summary_sha256"]:
        raise HarnessError(f"batch {batch['batch_index']} response receipt failed hash")
    checks["batch_response_hash_matches"] = True
    failed = [name for name, value in checks.items() if not value]
    if failed:
        raise HarnessError(f"batch {batch['batch_index']} compact receipt failed: {failed}")
    return {
        "batch_index": int(batch["batch_index"]),
        "run_name": batch["run_name"],
        "transport_seed": int(batch["transport_seed"]),
        "source_card": provenance["source_card"],
        "raw_sim": provenance["raw_sim"],
        "sim_header": provenance["sim_header"],
        "sim_footer": provenance["sim_footer"],
        "counts": provenance["counts"],
        "angular_counts": angular["counts"],
        "compact_provenance": {
            "path": rel(provenance_path),
            "sha256": provenance_hash,
        },
        "compact_artifacts": artifact_rows,
        "batch_response": {
            "path": rel(response_path),
            "sha256": batch["response_summary_sha256"],
        },
        "checks": checks,
        "raw_was_read_during_this_receipt_check": False,
    }


def _aggregate_campaign_locked(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.manifest.resolve()
    manifest = load_campaign(manifest_path)
    complete_status = "PARSED_AND_RESPONSE_DIAGNOSTIC_COMPLETE"
    complete = [row for row in manifest["batches"] if row.get("status") == complete_status]
    incomplete = [row for row in manifest["batches"] if row.get("status") != complete_status]
    if not complete:
        raise HarnessError("campaign has no parsed batches to aggregate")
    if incomplete and not args.allow_partial:
        raise HarnessError(
            f"campaign has {len(incomplete)} incomplete batches; use --allow-partial for a wave receipt"
        )
    complete.sort(key=lambda row: int(row["batch_index"]))
    receipts = [
        verified_batch_compact_receipt(manifest_path=manifest_path, batch=row)
        for row in complete
    ]
    fingerprint_payload = {
        "campaign_intent": manifest["intent_fingerprint_sha256"],
        "batches": [
            {
                "batch_index": row["batch_index"],
                "compact_provenance_sha256": row["compact_provenance"]["sha256"],
                "batch_response_sha256": row["batch_response"]["sha256"],
            }
            for row in receipts
        ],
        "response_replicas": args.response_replicas,
    }
    aggregate_fingerprint = canonical_sha256(fingerprint_payload)
    indices = [int(row["batch_index"]) for row in receipts]
    aggregate_dir = (
        manifest_path.parent
        / "aggregate"
        / f"wave_{indices[0]:04d}_{indices[-1]:04d}_{aggregate_fingerprint[:12]}"
    )
    receipt_path = aggregate_dir / "campaign_aggregate_receipt.json"
    if receipt_path.exists():
        existing = load_json(receipt_path)
        if existing.get("aggregate_fingerprint_sha256") != aggregate_fingerprint:
            raise HarnessError("aggregate receipt fingerprint conflict")
        existing["aggregate_receipt"] = "IDEMPOTENT_EXISTING_AGGREGATE_VERIFIED"
        return existing
    aggregate_dir.mkdir(parents=True, exist_ok=True)
    merged_dir = aggregate_dir / "merged_compact"
    merged_dir.mkdir(parents=True, exist_ok=True)
    event_path = merged_dir / "tes_events.csv"
    pixel_path = merged_dir / "tes_pixel_hits.csv"
    lineage_path = merged_dir / "event_lineage.csv"
    angular_path = merged_dir / "angular_counts.json"
    provenance_path = merged_dir / "provenance.json"
    for path in (event_path, pixel_path, lineage_path, angular_path, provenance_path):
        if path.exists():
            raise HarnessError(f"refusing to overwrite partial aggregate: {path}")

    merged_angular = {bins: [0] * bins for bins in (20, 40, 80)}
    total_counts: Counter[str] = Counter()
    total_te_s = 0.0
    total_ts = 0
    event_count = 0
    pixel_count = 0
    with event_path.open("x", encoding="utf-8", newline="") as event_handle, pixel_path.open(
        "x", encoding="utf-8", newline=""
    ) as pixel_handle, lineage_path.open("x", encoding="utf-8", newline="") as lineage_handle:
        event_writer = csv.DictWriter(event_handle, fieldnames=EVENT_FIELDS)
        pixel_writer = csv.DictWriter(pixel_handle, fieldnames=PIXEL_FIELDS)
        lineage_writer = csv.DictWriter(
            lineage_handle,
            fieldnames=["global_event_id", "batch_index", "run_name", "local_event_id"],
        )
        event_writer.writeheader()
        pixel_writer.writeheader()
        lineage_writer.writeheader()
        for receipt in receipts:
            batch_index = int(receipt["batch_index"])
            parsed_dir = path_from_manifest(receipt["compact_provenance"]["path"]).parent
            id_map: dict[int, int] = {}
            with (parsed_dir / "tes_events.csv").open(
                "r", encoding="utf-8", newline=""
            ) as handle:
                for raw in csv.DictReader(handle):
                    local_id = int(raw["event_id"])
                    global_id = batch_index * 10_000_000_000 + local_id
                    if global_id in id_map.values():
                        raise HarnessError("aggregate global event id collision")
                    id_map[local_id] = global_id
                    row = dict(raw)
                    row["event_id"] = global_id
                    event_writer.writerow(row)
                    lineage_writer.writerow(
                        {
                            "global_event_id": global_id,
                            "batch_index": batch_index,
                            "run_name": receipt["run_name"],
                            "local_event_id": local_id,
                        }
                    )
                    event_count += 1
            with (parsed_dir / "tes_pixel_hits.csv").open(
                "r", encoding="utf-8", newline=""
            ) as handle:
                for raw in csv.DictReader(handle):
                    local_id = int(raw["event_id"])
                    if local_id not in id_map:
                        raise HarnessError("aggregate pixel references unknown local event")
                    row = dict(raw)
                    row["event_id"] = id_map[local_id]
                    pixel_writer.writerow(row)
                    pixel_count += 1
            for bins in (20, 40, 80):
                values = [int(value) for value in receipt["angular_counts"][str(bins)]]
                merged_angular[bins] = [
                    left + right for left, right in zip(merged_angular[bins], values)
                ]
            total_te_s += float(receipt["sim_footer"]["TE_s"])
            total_ts += int(receipt["sim_footer"]["TS"])
            total_counts.update(
                {key: int(value) for key, value in receipt["counts"].items()}
            )
    if event_count != total_counts["tes_events"] or pixel_count != total_counts["tes_pixel_hits"]:
        raise HarnessError("merged compact event/pixel count did not close")
    for bins in (20, 40, 80):
        if sum(merged_angular[bins]) != total_ts:
            raise HarnessError(f"merged {bins}-bin angular count did not close")
    atomic_write_json(
        angular_path,
        {
            "schema": PARSE_SCHEMA,
            "mapping": "mu_source=-IA_INIT.dir_z; same-event 20/40/80 merged counts",
            "init_records": total_ts,
            "counts": {str(bins): values for bins, values in merged_angular.items()},
        },
    )
    compact_artifacts = {
        rel(path): {"sha256": sha256(path), "bytes": path.stat().st_size}
        for path in (event_path, pixel_path, angular_path, lineage_path)
    }
    start_areas = sorted(
        set(float(row["sim_header"]["start_area_cm2"]) for row in receipts)
    )
    if len(start_areas) != 1 or start_areas[0] <= 0.0:
        raise HarnessError(f"batch start areas do not close: {start_areas}")
    merged_provenance = {
        "schema": PARSE_SCHEMA,
        "status": "PASS_STREAM_PARSE_COMPLETE",
        "parsed_at_utc": utc_now(),
        "parser": {"path": rel(Path(__file__)), "sha256": sha256(Path(__file__))},
        "scope": "campaign compact merge; atmospheric annihilation mono line only",
        "proposal": "parma80_physical_flux",
        "source_card": {
            "batch_sources": [row["source_card"] for row in receipts],
            "note": "Each batch source passed the exact physical 80-bin validator.",
        },
        "raw_sim": [row["raw_sim"] for row in receipts],
        "raw_sim_files_read_during_merge": False,
        "sim_header": {
            "start_area_cm2": start_areas[0],
            "batch_headers": [row["sim_header"] for row in receipts],
        },
        "geometry_authority": receipts[0]["sim_header"].get("geometry"),
        "transport_seed": [row["transport_seed"] for row in receipts],
        "expected_energy_keV": PARMA_LINE_ENERGY_KEV,
        "energy_tolerance_keV": 0.001,
        "sim_footer": {"TE_s": total_te_s, "TS": total_ts},
        "counts": dict(total_counts),
        "checks": {
            "batch_receipts_all_closed": True,
            "merged_event_count_closed": True,
            "merged_pixel_count_closed": True,
            "merged_angular_counts_closed": True,
            "merge_used_compact_only": True,
        },
        "artifacts": compact_artifacts,
        "batch_receipts": receipts,
        "aggregate_fingerprint_sha256": aggregate_fingerprint,
    }
    atomic_write_json(provenance_path, merged_provenance)
    response_dir = aggregate_dir / "response"
    response = response_analysis(
        parsed_dir=merged_dir,
        output_dir=response_dir,
        proposal="parma80",
        replicas=args.response_replicas,
    )
    raw_root = (manifest_path.parent / "raw").resolve()
    cleanup_eligible: list[dict[str, Any]] = []
    for receipt in receipts:
        raw_path = path_from_manifest(receipt["raw_sim"]["path"]).resolve()
        within_new_campaign_raw = raw_path.is_relative_to(raw_root)
        eligibility = within_new_campaign_raw and all(receipt["checks"].values())
        cleanup_eligible.append(
            {
                "batch_index": receipt["batch_index"],
                "path": rel(raw_path),
                "sha256": receipt["raw_sim"]["sha256"],
                "status": (
                    "ELIGIBLE_FOR_EXPLICIT_EXTERNAL_CLEANUP_NOT_DELETED"
                    if eligibility
                    else "NOT_ELIGIBLE_FOR_CLEANUP"
                ),
                "path_is_inside_this_new_campaign_raw_dir": within_new_campaign_raw,
                "batch_compact_and_response_closed": all(receipt["checks"].values()),
                "raw_was_read_during_aggregate": False,
                "raw_deleted_by_harness": False,
            }
        )
    aggregate_receipt = {
        "schema": "o8-parma511-line-campaign-aggregate-v1",
        "status": "CAMPAIGN_COMPACT_AGGREGATE_COMPLETE_DIAGNOSTIC_ONLY",
        "created_at_utc": utc_now(),
        "aggregate_fingerprint_sha256": aggregate_fingerprint,
        "campaign_manifest": {
            "path": rel(manifest_path),
            "sha256_before_aggregate_receipt": sha256(manifest_path),
        },
        "included_batch_indices": indices,
        "incomplete_batch_indices": [int(row["batch_index"]) for row in incomplete],
        "allow_partial": bool(args.allow_partial),
        "batch_receipts": receipts,
        "merged_compact": {
            "provenance": rel(provenance_path),
            "provenance_sha256": sha256(provenance_path),
            "events": event_count,
            "pixel_hits": pixel_count,
            "TS": total_ts,
            "TE_s": total_te_s,
            "artifacts": compact_artifacts,
            "raw_sim_files_read": False,
        },
        "response": {
            "summary": rel(response_dir / "response_64seed_summary.json"),
            "summary_sha256": sha256(response_dir / "response_64seed_summary.json"),
            "replicas": args.response_replicas,
            "primary_gate": response["primary_detector_rate_gate"],
        },
        "cleanup_eligible_raw": cleanup_eligible,
        "cleanup_contract": (
            "Eligibility is limited to exact raw paths under this new campaign. "
            "The harness has no delete command and deleted nothing."
        ),
        "raw_deleted": False,
    }
    atomic_write_json(receipt_path, aggregate_receipt)
    manifest = load_campaign(manifest_path)
    aggregate_record = {
        "path": rel(receipt_path),
        "sha256": sha256(receipt_path),
        "fingerprint": aggregate_fingerprint,
        "included_batch_indices": indices,
        "primary_gate_status": response["primary_detector_rate_gate"]["status"],
    }
    aggregates = [
        row for row in manifest.get("aggregates", [])
        if row.get("fingerprint") != aggregate_fingerprint
    ]
    aggregates.append(aggregate_record)
    manifest["aggregates"] = aggregates
    manifest["updated_at_utc"] = utc_now()
    atomic_write_json(manifest_path, manifest)
    return aggregate_receipt


def aggregate_campaign(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.manifest.resolve()
    with campaign_lock(manifest_path):
        return _aggregate_campaign_locked(args)


def concurrency_update_worker(manifest_path: str, batch_index: int, queue: Any) -> None:
    try:
        update_manifest_batch(
            Path(manifest_path),
            batch_index,
            {
                "status": f"LOCK_SELF_TEST_{batch_index:04d}",
                "lock_self_test_pid": os.getpid(),
            },
            expected_statuses={"PREPARED_NOT_RUN"},
        )
        queue.put({"batch_index": batch_index, "ok": True})
    except Exception as exc:
        queue.put({"batch_index": batch_index, "ok": False, "error": str(exc)})


def concurrency_self_test(workers: int = 15) -> dict[str, Any]:
    if workers < 2 or workers > 64:
        raise HarnessError("concurrency self-test workers must be in [2, 64]")
    with tempfile.TemporaryDirectory(prefix="o8_parma511_manifest_lock_") as tmp_name:
        root = Path(tmp_name)
        campaign_id = "manifest_lock_self_test"
        prepare_campaign(
            campaign_id=campaign_id,
            batches=workers,
            events_per_batch=1,
            base_seed=260_812_000,
            transport_root=root,
            runtime_probe=False,
        )
        manifest_path = root / campaign_id / "campaign_manifest.json"
        context = mp.get_context("fork")
        queue = context.Queue()
        processes = [
            context.Process(
                target=concurrency_update_worker,
                args=(str(manifest_path), index, queue),
            )
            for index in range(workers)
        ]
        for process in processes:
            process.start()
        results = [queue.get(timeout=30) for _ in processes]
        for process in processes:
            process.join(timeout=30)
        exitcodes = [process.exitcode for process in processes]
        manifest = load_json(manifest_path)
        validate_campaign_document(manifest, manifest_path)
        status_by_batch = {
            int(row["batch_index"]): str(row["status"]) for row in manifest["batches"]
        }
        checks = {
            "all_workers_reported_success": all(row["ok"] for row in results),
            "all_process_exitcodes_zero": all(value == 0 for value in exitcodes),
            "manifest_remains_valid_json_and_fingerprint": True,
            "all_batch_updates_retained": all(
                status_by_batch.get(index) == f"LOCK_SELF_TEST_{index:04d}"
                for index in range(workers)
            ),
            "no_cosima_or_transport": True,
        }
        failed = [name for name, value in checks.items() if not value]
        if failed:
            raise HarnessError(
                f"manifest concurrency self-test failed: {failed}; results={results}; exits={exitcodes}"
            )
        return {
            "status": "PASS_FCNTL_CONCURRENT_MANIFEST_UPDATE_SELF_TEST",
            "workers": workers,
            "checks": checks,
            "lock_file": ".campaign_manifest.lock",
            "temporary_artifacts_removed_on_exit": True,
            "cosima_launched": False,
            "raw_deleted": False,
        }


def old_self_test() -> dict[str, Any]:
    authority_report(include_old=True)
    with tempfile.TemporaryDirectory(prefix="o8_parma511_old3m_selftest_") as tmp_name:
        tmp = Path(tmp_name)
        parsed = tmp / "parsed"
        provenance = stream_parse_sim(
            sim=OLD_SIM,
            output_dir=parsed,
            expected_seed=26_070_917,
            expected_energy_keV=511.0,
            expected_events=3_000_000,
            source_card=OLD_SOURCE,
            source_card_sha256=EXPECTED_SHA256[OLD_SOURCE],
            proposal_name="retained_old_equal_mu_20bin",
            energy_tolerance_keV=1e-9,
        )
        response = response_analysis(
            parsed_dir=parsed,
            output_dir=tmp / "response",
            proposal="old20",
            replicas=DEFAULT_RESPONSE_REPLICAS,
        )
        checks = {
            "generated_events_3000000": provenance["sim_footer"]["TS"] == 3_000_000,
            "tes_events_69": provenance["counts"]["tes_events"] == 69,
            "unsmeared_w2_9": response["unsmeared"]["w2_frozen_step05_pass_events"] == 9,
            "primary_420eV_w2_8": response["primary_420eV"]["w2_frozen_step05_pass_events"] == 8,
            "primary_seed_1026071308": response["primary_420eV"]["response_seed"] == 1_026_071_308,
            "unsmeared_w2_active_total_is_zero": response["unsmeared"]["w2_final_active_energy_max_keV"] == 0.0,
            "primary_w2_active_total_is_zero": response["primary_420eV"]["w2_final_active_energy_max_keV"] == 0.0,
            "unsmeared_rate80_reproduced": math.isclose(
                response["unsmeared"]["paired_reweight"]["80"]["importance_weighted_rate_cps"],
                0.004766653571016595,
                rel_tol=0.0,
                abs_tol=5e-13,
            ),
            "primary_rate80_reproduced": math.isclose(
                response["primary_420eV"]["paired_reweight"]["80"]["importance_weighted_rate_cps"],
                0.004174895548884529,
                rel_tol=0.0,
                abs_tol=5e-13,
            ),
        }
        failed = [name for name, value in checks.items() if not value]
        if failed:
            raise HarnessError(f"old 3M self-test failed: {failed}")
        return {
            "status": "PASS_RETAINED_OLD3M_STREAM_RESPONSE_SELF_TEST",
            "checks": checks,
            "retained_sim": {"path": rel(OLD_SIM), "sha256": sha256(OLD_SIM)},
            "footer": provenance["sim_footer"],
            "counts": provenance["counts"],
            "unsmeared": response["unsmeared"],
            "primary_420eV": response["primary_420eV"],
            "primary_detector_rate_gate": response["primary_detector_rate_gate"],
            "active_veto_naming_blocker": ACTIVE_VETO_NAMING_BLOCKER,
            "active_veto_volume_audit": provenance["active_veto_volume_audit"],
            "old_line_w2_active_energy": {
                "unsmeared_max_keV": response["unsmeared"]["w2_final_active_energy_max_keV"],
                "primary_max_keV": response["primary_420eV"]["w2_final_active_energy_max_keV"],
            },
            "response_replicas": DEFAULT_RESPONSE_REPLICAS,
            "temporary_artifacts_removed_on_exit": True,
            "raw_deleted": False,
        }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("preflight", help="verify frozen authorities; write nothing")

    smoke = sub.add_parser("prepare-smoke", help="prepare, but do not run, one 1k line-only batch")
    smoke.add_argument("--campaign-id", default="o8_parma511_line_smoke_1k")
    smoke.add_argument("--base-seed", type=int, default=260_810_511)
    smoke.add_argument("--transport-root", type=Path, default=DEFAULT_TRANSPORT_ROOT)

    prepare = sub.add_parser("prepare-campaign", help="prepare recoverable line-only batches")
    prepare.add_argument("--campaign-id", required=True)
    prepare.add_argument("--batches", type=int, required=True)
    prepare.add_argument("--events-per-batch", type=int, required=True)
    prepare.add_argument("--base-seed", type=int, default=260_810_511)
    prepare.add_argument("--transport-root", type=Path, default=DEFAULT_TRANSPORT_ROOT)

    run = sub.add_parser("run-batch", help="explicitly gated Cosima entry; never used by self-test")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--batch", type=int, required=True)
    run.add_argument("--cosima", type=Path, default=COSIMA_DEFAULT)
    run.add_argument("--authorize-line-only-cosima", action="store_true")
    run.add_argument("--confirmation", default="")
    run.add_argument("--quiet", action="store_true", help="keep stdout in the batch log only")

    analyze = sub.add_parser("analyze-batch", help="stream-parse and response-fold one existing line SIM")
    analyze.add_argument("--manifest", type=Path, required=True)
    analyze.add_argument("--batch", type=int, required=True)
    analyze.add_argument("--response-replicas", type=int, default=DEFAULT_RESPONSE_REPLICAS)

    aggregate = sub.add_parser(
        "aggregate-campaign",
        help="merge validated per-batch compact receipts without reading raw SIM files",
    )
    aggregate.add_argument("--manifest", type=Path, required=True)
    aggregate.add_argument("--response-replicas", type=int, default=DEFAULT_RESPONSE_REPLICAS)
    aggregate.add_argument(
        "--allow-partial",
        action="store_true",
        help="emit a wave receipt for currently completed batches",
    )

    sub.add_parser("self-test-old", help="read-only old 3M SIM 69/9/8 closure; no Cosima")
    concurrent = sub.add_parser(
        "self-test-concurrency",
        help="race manifest-only updates under fcntl; no SIM and no Cosima",
    )
    concurrent.add_argument("--workers", type=int, default=15)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "preflight":
            result = preflight_report()
        elif args.command == "prepare-smoke":
            result = prepare_campaign(
                campaign_id=args.campaign_id,
                batches=1,
                events_per_batch=1_000,
                base_seed=args.base_seed,
                transport_root=args.transport_root,
            )
        elif args.command == "prepare-campaign":
            result = prepare_campaign(
                campaign_id=args.campaign_id,
                batches=args.batches,
                events_per_batch=args.events_per_batch,
                base_seed=args.base_seed,
                transport_root=args.transport_root,
            )
        elif args.command == "run-batch":
            result = run_batch(args)
        elif args.command == "analyze-batch":
            result = analyze_batch(args)
        elif args.command == "aggregate-campaign":
            result = aggregate_campaign(args)
        elif args.command == "self-test-old":
            result = old_self_test()
        elif args.command == "self-test-concurrency":
            result = concurrency_self_test(args.workers)
        else:
            raise HarnessError(f"unhandled command: {args.command}")
    except HarnessError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    if not (args.command == "run-batch" and args.quiet):
        receipt = {
            "status": result.get("status"),
            "scope": "atmospheric annihilation 510.99895-keV mono module only",
            "cosima_launched": args.command == "run-batch",
            "raw_deleted": False,
        }
        if args.command == "preflight":
            runtime = result["cosima_runtime"]
            receipt.update(
                {
                    "cosima_binary": runtime["cosima"],
                    "runtime_environment_canonical_sha256": runtime[
                        "launch_environment_canonical_sha256"
                    ],
                    "runtime_probe": runtime["runtime_probe"],
                    "package44_runner": runtime["package44_runner"],
                }
            )
        elif args.command == "prepare-smoke":
            receipt.update(
                {
                    "manifest": rel(args.transport_root.resolve() / args.campaign_id / "campaign_manifest.json"),
                    "batches": len(result["batches"]),
                    "events_per_batch": result["intent"]["events_per_batch"],
                }
            )
        elif args.command == "aggregate-campaign":
            receipt.update(
                {
                    "included_batch_indices": result["included_batch_indices"],
                    "merged_TS": result["merged_compact"]["TS"],
                    "merged_TE_s": result["merged_compact"]["TE_s"],
                    "primary_gate": result["response"]["primary_gate"],
                    "raw_files_read": False,
                }
            )
        elif args.command == "prepare-campaign":
            receipt.update(
                {
                    "manifest": rel(args.transport_root.resolve() / args.campaign_id / "campaign_manifest.json"),
                    "batches": len(result["batches"]),
                    "events_per_batch": result["intent"]["events_per_batch"],
                }
            )
        elif args.command == "self-test-old":
            receipt.update(
                {
                    "footer": result["footer"],
                    "counts": result["counts"],
                    "unsmeared_w2": result["unsmeared"]["w2_frozen_step05_pass_events"],
                    "primary_420eV_w2": result["primary_420eV"]["w2_frozen_step05_pass_events"],
                    "response_replicas": result["response_replicas"],
                    "unsmeared_rate80_cps": result["unsmeared"]["paired_reweight"]["80"]["importance_weighted_rate_cps"],
                    "primary_rate80_cps": result["primary_420eV"]["paired_reweight"]["80"]["importance_weighted_rate_cps"],
                    "primary_ess80": result["primary_420eV"]["paired_reweight"]["80"]["importance_effective_sample_size"],
                    "primary_rse80": result["primary_420eV"]["paired_reweight"]["80"]["mc_relative_sigma"],
                    "primary_gate": result["primary_detector_rate_gate"],
                    "old_line_w2_active_energy": result["old_line_w2_active_energy"],
                    "kapton_wrapper_hit_records": {
                        name: result["active_veto_volume_audit"]["hit_records_by_volume"].get(name, 0)
                        for name in KNOWN_O8_ACTIVE_SHIELD_NAMED_WRAPPERS
                    },
                }
            )
        elif args.command == "self-test-concurrency":
            receipt.update(
                {
                    "workers": result["workers"],
                    "checks": result["checks"],
                }
            )
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
