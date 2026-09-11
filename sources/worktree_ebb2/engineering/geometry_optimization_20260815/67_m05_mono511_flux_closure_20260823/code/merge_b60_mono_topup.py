#!/usr/bin/env python3
"""Build a publication-auditable compact B60 mono-line top-up response.

A hash-frozen compact response is used as an immutable prefix.  Only the new
top-up SIM files are scanned.  Their detector response and primary 80-bin
identity are retained in a resumable, per-job, directory-atomic cache.  A new
staging authority is then assembled with one common 1/sum(T_E) event weight.

No transport, broadband catalog, timeline, or manuscript operation lives in
this script.  Promotion is a separate explicit command and is never implicit.
"""

from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]
OUTPUTS = PACKAGE / "outputs"

OLD_RESPONSE = OUTPUTS / "01_line_response_b60"
TOPUP_ROOT = Path(
    "/mnt/data/TES_Balloon_511_data/SH3/"
    "sh3_optv3_60cm_mono511_topup_3477841_20260823_v1"
)
TOPUP_CACHE = TOPUP_ROOT / "analysis_cache_package67_b60_topup01"
STAGING_RESPONSE = OUTPUTS / "01_line_response_b60_topup1_staging"

B_CONFIG = ROOT / "DEEPSEEK_CODE/modified/analysis_inputs_optv3_B.json"
B_BUILDER = ROOT / "DEEPSEEK_CODE/modified/build_event_catalog_sh3_step05.py"
SIDE_COMPTON = ROOT / "DEEPSEEK_CODE/modified/step05_side_compton.py"
ANALYZER = HERE.with_name("analyze_mono_line.py")
TOPUP_RUNNER = HERE.with_name("run_b60_mono_topup.py")
ADAPTIVE_SCRIPT = Path(
    "/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/64_sh3_optv3_60cm_adaptive_20260818/"
    "adaptive_campaign.py"
)
LINE_FRAGMENT = Path(
    "/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/"
    "m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/"
    "line/PARMA_atm511_day15_fullsphere_80bins.inc.source"
)
LINE_CONTRACT = (
    LINE_FRAGMENT.parents[1] / "transport/line_only_transport_contract.json"
)

OLD_REQUIRED_HASHES = {
    "summary.json": "64d94a7d0538c62a8b4c2459afa7583f187fd14a5eeba6e4fd53729eebf79ab2",
    "mono_line_event_catalog.npz": (
        "7a549ed7f7e9239aec94d5084bf556db26c13ecebbde84b2fd6d7fc9de7823d7"
    ),
    "mono_line_cutflow.csv": (
        "234143f212bff4c88512229f99462768002ea4c27fd8da59ef8a9093c1e28524"
    ),
    "mono_line_final_by_source_bin80.csv": (
        "53dee946385aa77afcbd6f704e4bab609679f2b126edb8cd789b7cbaf072a860"
    ),
}
# Every incremental merge may start only from one of these fully validated,
# already promoted compact authorities. Binding all four response products and
# the merge receipt prevents a stale canonical directory becoming a prefix.
PROMOTED_PREFIX_REQUIRED_HASHES = {
    "promoted_67_compact": {
        "summary.json": (
            "22935f7f16cd61c4a536271da7b8ae74e378ffef4f5d051c10d2ec05177b0b42"
        ),
        "mono_line_event_catalog.npz": (
            "dc45a3204891fc37428c1d7d46585973170c4cd912481ae3e098d93c9adadf26"
        ),
        "mono_line_cutflow.csv": (
            "22f53b4395170f6088cec92cdb6e78658f92da16de02230ffdfd29c94bbf9f78"
        ),
        "mono_line_final_by_source_bin80.csv": (
            "28fcca31afa08f706aea9f05f8f428e85df3e520307472280a4b0f7a89d59a25"
        ),
        "MERGE_RECEIPT.json": (
            "0a65de10d43eab7b307cf474efb3aa098ac75d1410edb6b336376dd74ea57a34"
        ),
    },
    "promoted_68_compact": {
        "summary.json": (
            "80f6a12ceedc46d99343d773d435338bd61733c1947812ababb193a71deb2173"
        ),
        "mono_line_event_catalog.npz": (
            "6f691ec3aae28d3f3eeb58ebeb55ad7de633b4c0c9afd59fbe29c970a7d50191"
        ),
        "mono_line_cutflow.csv": (
            "f30700f522aab40a79f80f8c8bb96dc852159f17877e8405d710233ceb8a2924"
        ),
        "mono_line_final_by_source_bin80.csv": (
            "0a6f1e75ea0c97bb0276aff38d3b0d5c0912947b2315d86beac275e3fbc467cc"
        ),
        "MERGE_RECEIPT.json": (
            "2a445fdd559dfc75da0f39021d551be3d7626915626ac39bdca17e735021dea7"
        ),
    },
}
EXPECTED_SETUP_SHA256 = "36e44e7bc1af3f3ae296e5f3e82ac0388d7ff28182e2897a30abfca6616b5768"
EXPECTED_GEO_SHA256 = "a270ab2caf340a34858b448374b3dad955878ebbb9df9169f97d80df46026934"
EXPECTED_DET_SHA256 = "12d3a6831f3d00da6668f48487e5d83f7a0354419fdec75cfec211b28373cae9"
EXPECTED_FRAGMENT_SHA256 = "fc386a44b096d33d12d4a096532a3a57da5743681d93e779e653ae1349f776e6"
EXPECTED_LINE_CONTRACT_SHA256 = "87e034405d46c0a928f4e4c2aa2c36030f110f7dc8ab4c843436bf195bf9357f"

BASE_INCIDENT_PHOTONS = 12_140_688
BASE_JOBS = 52
BASE_DETECTOR_POSITIVE = 502_682
LINE_FLUX_4PI = 0.16651547160226118
LINE_ENERGY_KEV = 510.99895
ACTIVE_VETO_THRESHOLD_KEV = 50.0

STAGES = {
    "pre_veto": 1 << 0,
    "plastic_positron_veto": 1 << 1,
    "bgo_active_scintillator_veto": 1 << 2,
    "combined_active_veto": 1 << 3,
    "compton_trajectory_veto": 1 << 4,
}
WINDOW_FIELDS = {
    "broad_480_550": "broad_flags",
    "w2_510p58_511p42": "w2_flags",
}
FINAL_WINDOW = "w2_510p58_511p42"
FINAL_STAGE = "compton_trajectory_veto"

EVENT_FIELDS = (
    "event_id",
    "plastic_keV",
    "bgo_keV",
    "measured_total_keV",
    "broad_flags",
    "w2_flags",
    "compton_keep",
    "hit_start",
    "hit_count",
)
HIT_FIELDS = (
    "hit_code",
    "hit_layer",
    "hit_energy_keV",
    "hit_x_cm",
    "hit_y_cm",
    "hit_z_cm",
)
FOUR_RESPONSE_FILES = tuple(OLD_REQUIRED_HASHES)
FIVE_MERGED_PREFIX_FILES = (*FOUR_RESPONSE_FILES, "MERGE_RECEIPT.json")


class MergeError(RuntimeError):
    """A frozen-input, compact-cache, or merged-authority check failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MergeError(message)


def required_hashes_for_mode(mode: str) -> Mapping[str, str]:
    if mode == "legacy_52_compact":
        return OLD_REQUIRED_HASHES
    hashes = PROMOTED_PREFIX_REQUIRED_HASHES.get(mode)
    if hashes is None:
        raise MergeError(f"unknown compact-prefix mode: {mode}")
    return hashes


def promoted_mode_from_records(records: Mapping[str, Mapping[str, Any]]) -> str:
    matches = [
        mode
        for mode, expected in PROMOTED_PREFIX_REQUIRED_HASHES.items()
        if set(records) == set(expected)
        and all(records[name]["sha256"] == digest for name, digest in expected.items())
    ]
    require(len(matches) == 1, "merged-prefix five-file hashes are not an approved authority")
    return matches[0]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.partial")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    fsync_directory(path.parent)


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"empty CSV payload: {path.name}")
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise MergeError(f"cannot import reviewed module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def file_record(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    require(resolved.is_file(), f"required file missing: {resolved}")
    return {
        "path": str(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": sha256(resolved),
    }


def records_digest(records: Iterable[Mapping[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(str(record["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["bytes"]).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(record["sha256"]).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def transport_receipt_digest(records: Iterable[Mapping[str, Any]]) -> str:
    """Match the top-up transport validator's filename/NUL/hash manifest."""
    digest = hashlib.sha256()
    for record in records:
        digest.update(Path(str(record["path"])).name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(record["sha256"]).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def normalized_fragment_lines(text: str, run_id: str) -> list[str]:
    """Return the complete, job-name-normalized 80-bin source definition."""
    source_prefix = f"{run_id}.Source "
    rows: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(source_prefix):
            rows.append("PARMA511Day15.Source " + line[len(source_prefix):])
        elif line.startswith("PARMA511_bin"):
            rows.append(line)
    return rows


def validate_normalized_fragment(text: str, run_id: str) -> dict[str, Any]:
    canonical_text = LINE_FRAGMENT.read_text(encoding="utf-8")
    canonical = normalized_fragment_lines(canonical_text, "PARMA511Day15")
    observed = normalized_fragment_lines(text, run_id)
    require(len(canonical) == 400, "canonical PARMA fragment is not 80*(source+4 fields)")
    require(observed == canonical, f"normalized 80-bin PARMA fragment differs: {run_id}")

    beams: list[tuple[float, float]] = []
    fluxes: list[float] = []
    names: list[str] = []
    for line in canonical:
        if line.startswith("PARMA511Day15.Source "):
            names.append(line.split(maxsplit=1)[1])
        elif ".Beam FarFieldAreaSource " in line:
            fields = line.split()
            beams.append((float(fields[-4]), float(fields[-3])))
        elif ".Flux " in line:
            fluxes.append(float(line.rsplit(maxsplit=1)[-1]))
    require(len(names) == len(beams) == len(fluxes) == 80, "PARMA 80-bin fields differ")
    require(names == [
        f"PARMA511_bin{index:02d}_{'down' if index < 40 else 'up'}"
        for index in range(80)
    ], "PARMA source order differs")
    require(math.isclose(beams[0][0], 0.0, abs_tol=1e-12), "PARMA theta start differs")
    require(math.isclose(beams[-1][1], 180.0, abs_tol=1e-12), "PARMA theta end differs")
    max_edge_gap = max(abs(beams[index][1] - beams[index + 1][0]) for index in range(79))
    mu_widths = [math.cos(math.radians(lo)) - math.cos(math.radians(hi)) for lo, hi in beams]
    max_mu_residual = max(abs(width - 0.025) for width in mu_widths)
    require(max_edge_gap <= 1e-12, "PARMA theta bins are not contiguous")
    require(max_mu_residual <= 2e-14, "PARMA bins are not equal in mu")
    require(math.isclose(math.fsum(fluxes), LINE_FLUX_4PI, rel_tol=0.0, abs_tol=2e-15),
            "PARMA 80-bin flux vector does not close")
    normalized = "\n".join(canonical) + "\n"
    return {
        "status": "PASS__EXACT_NORMALIZED_PARMA_80BIN_FRAGMENT",
        "bins": 80,
        "line_energy_keV": LINE_ENERGY_KEV,
        "flux_4pi_ph_cm2_s": math.fsum(fluxes),
        "maximum_theta_edge_gap_deg": max_edge_gap,
        "maximum_equal_mu_width_residual": max_mu_residual,
        "normalized_contract_sha256": text_sha256(normalized),
        "canonical_fragment_sha256": sha256(LINE_FRAGMENT),
    }


def selection_authority(builder: Any, config: Mapping[str, Any]) -> dict[str, Any]:
    side = config["side_entry_disk"]
    return {
        "fwhm_keV": float(builder.FWHM_KEV),
        "sigma_keV": float(builder.SIGMA_KEV),
        "post_noise_pixel_threshold_keV": float(builder.PIXEL_THRESHOLD_KEV),
        "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
        "windows_keV": {key: list(value) for key, value in builder.WINDOWS.items()},
        "stage_bits": dict(builder.STAGE_BITS),
        "plastic_veto_volumes": list(config["active_veto"]["plastic_positron_veto_volumes"]),
        "bgo_veto_volumes": list(config["active_veto"]["bgo_active_scintillator_volumes"]),
        "side_entry_disk": {
            "local_center_cm": [float(value) for value in side["local_center_cm"]],
            "radius_cm": float(side["radius_cm"]),
            "rotation_y_deg": float(side["rotation_y_deg"]),
            "reject_policy": str(side.get("reject_policy", "keep")),
        },
    }


def validate_frozen_files(contract: Mapping[str, Any]) -> dict[str, Any]:
    authority = contract["authority"]
    setup = Path(authority["setup_path"]).resolve()
    geo = Path(authority["geo_path"]).resolve()
    det = Path(authority["det_path"]).resolve()
    expected = (
        (setup, EXPECTED_SETUP_SHA256, "setup"),
        (geo, EXPECTED_GEO_SHA256, "geo"),
        (det, EXPECTED_DET_SHA256, "det"),
        (LINE_FRAGMENT, EXPECTED_FRAGMENT_SHA256, "fragment"),
        (LINE_CONTRACT, EXPECTED_LINE_CONTRACT_SHA256, "line contract"),
    )
    records: dict[str, Any] = {}
    for path, digest, label in expected:
        record = file_record(path)
        require(record["sha256"] == digest, f"frozen {label} hash differs")
        records[label.replace(" ", "_")] = record
    require(authority["setup_sha256"] == EXPECTED_SETUP_SHA256, "contract setup hash differs")
    require(authority["geo_sha256"] == EXPECTED_GEO_SHA256, "contract geo hash differs")
    require(authority["det_sha256"] == EXPECTED_DET_SHA256, "contract det hash differs")
    return records


def load_topup(
    topup_root: Path, *, scan_index_start: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    root = topup_root.resolve()
    named = {
        "contract": root / "TOPUP_CONTRACT.json",
        "validation": root / "TOPUP_VALIDATION.json",
        "source80_validation": root / "TOPUP_SOURCE80_VALIDATION.json",
        "controller": root / "run/controller_state.json",
        "config": root / "config.json",
        "job_plan": root / "generated/job_plan.json",
        "seed_registry": root / "generated/seed_registry.json",
        "source_manifest": root / "generated/source_manifest.json",
        "preflight": root / "generated/preflight.json",
    }
    records = {name: file_record(path) for name, path in named.items()}
    contract = load_json(named["contract"])
    validation = load_json(named["validation"])
    source80_validation = load_json(named["source80_validation"])
    controller = load_json(named["controller"])
    plan = load_json(named["job_plan"])
    manifest = load_json(named["source_manifest"])
    require(contract.get("status") == "PASS__B60_MONO511_MINIMUM_TOPUP_PREPARED",
            "top-up preparation contract is not PASS")
    require(validation.get("status") == "PASS__B60_MONO511_MINIMUM_TOPUP_TRANSPORT_COMPLETE",
            "top-up transport validation is not PASS")
    require(controller.get("status") == "COMPLETE" and controller.get("error") is None,
            "top-up controller is not complete")
    require(source80_validation.get("status") == "PASS__EXACT_NORMALIZED_PARMA_80BIN_FRAGMENT",
            "top-up exact 80-bin source validation is not PASS")
    require(records["contract"]["sha256"] == validation["contract_sha256"],
            "top-up validation/contract hash differs")
    require(records["controller"]["sha256"] == validation["controller_sha256"],
            "top-up validation/controller hash differs")
    for name, key in (
        ("config", "config.json"),
        ("job_plan", "generated/job_plan.json"),
        ("seed_registry", "generated/seed_registry.json"),
        ("source_manifest", "generated/source_manifest.json"),
    ):
        require(records[name]["sha256"] == contract["hashes"][key],
                f"top-up frozen manifest hash differs: {key}")
    require(contract["hashes"]["day15_parma_80bin_fragment"] == EXPECTED_FRAGMENT_SHA256,
            "top-up fragment authority differs")
    require(contract["hashes"]["line_only_transport_contract"] == EXPECTED_LINE_CONTRACT_SHA256,
            "top-up line transport contract differs")
    frozen_files = validate_frozen_files(contract)

    plan_rows = list(plan["jobs"])
    manifest_by = {str(row["job_id"]): row for row in manifest["sources"]}
    receipt_paths = sorted((root / "run/receipts").glob("*.json"))
    receipts = [load_json(path) for path in receipt_paths]
    receipt_by = {str(row["job_id"]): row for row in receipts}
    receipt_path_by = {
        str(row["job_id"]): path for row, path in zip(receipts, receipt_paths)
    }
    transport_receipt_records = [file_record(path) for path in receipt_paths]
    job_ids = [str(row["job_id"]) for row in plan_rows]
    require(len(job_ids) == int(contract["jobs"]) == int(validation["jobs"]),
            "top-up job count differs")
    require(len(job_ids) > 0 and len(set(job_ids)) == len(job_ids),
            "top-up does not contain positive unique jobs")
    require(set(job_ids) == set(manifest_by) == set(receipt_by), "top-up job lineage differs")
    require(int(controller["completed_count"]) == len(job_ids), "top-up completed count differs")

    # The transport bundle config owns scheduling and source-card provenance;
    # detector-response selections are frozen separately in B_CONFIG.
    response_cfg = load_json(B_CONFIG)
    plastic = list(
        response_cfg["active_veto"]["plastic_positron_veto_volumes"]
    )
    bgo = list(response_cfg["active_veto"]["bgo_active_scintillator_volumes"])
    setup = Path(contract["authority"]["setup_path"]).resolve()
    source_records: list[dict[str, Any]] = []
    jobs: list[dict[str, Any]] = []
    exposures: list[float] = []
    all_seeds: list[int] = []
    fragment_audits: list[dict[str, Any]] = []
    for ordinal, plan_row in enumerate(plan_rows):
        job_id = str(plan_row["job_id"])
        receipt = receipt_by[job_id]
        source_meta = manifest_by[job_id]
        require(receipt.get("status") == "PASS" and not receipt.get("errors"),
                f"top-up receipt is not PASS: {job_id}")
        require(int(receipt["events"]) == int(plan_row["events"]) == int(source_meta["events"]),
                f"top-up event count differs: {job_id}")
        require(Path(receipt["setup_path"]).resolve() == setup, f"top-up setup differs: {job_id}")
        require(Path(receipt["sim_header"]["geometry"]).resolve() == setup,
                f"top-up SIM geometry differs: {job_id}")
        seed = int(receipt["seed"])
        require(seed == int(receipt["sim_header"]["seed"]) == int(source_meta["seed"]),
                f"top-up seed differs: {job_id}")
        sim = Path(receipt["sim_path"]).resolve()
        source = Path(receipt["source_path"]).resolve()
        require(sim.is_file() and sim.stat().st_size == int(receipt["sim_bytes"]),
                f"top-up SIM path/size differs: {job_id}")
        source_record = file_record(source)
        require(source_record["sha256"] == receipt["source_sha256"] == source_meta["source_sha256"],
                f"top-up source hash differs: {job_id}")
        audit = validate_normalized_fragment(source.read_text(encoding="utf-8"), job_id)
        fragment_audits.append(audit)
        exposure = float(receipt["log"]["observation_time_s"])
        require(math.isfinite(exposure) and exposure > 0.0, f"bad exposure: {job_id}")
        exposures.append(exposure)
        all_seeds.append(seed)
        source_records.append(source_record)
        receipt_record = file_record(receipt_path_by[job_id])
        jobs.append({
            "stream": "prompt",
            "family": "atm511",
            "mode": "atm511",
            "batch_id": root.name,
            "job_id": job_id,
            "scan_index": scan_index_start + ordinal,
            "seed": seed,
            "events": int(receipt["events"]),
            "sim_path": str(sim),
            "sim_bytes": int(receipt["sim_bytes"]),
            "source_path": str(source),
            "source_sha256": source_record["sha256"],
            "receipt_sha256": receipt_record["sha256"],
            "expected_geometry": str(setup),
            "weight_cps": 0.0,
            "plastic_volumes": plastic,
            "bgo_volumes": bgo,
            "positions_path": None,
        })
    require(len(set(all_seeds)) == len(all_seeds), "top-up seeds are not unique")
    require(sum(int(job["events"]) for job in jobs) == int(contract["additional_incident_photons"]),
            "top-up incident count does not close")
    require(all(audit == fragment_audits[0] for audit in fragment_audits),
            "top-up normalized fragments differ across jobs")
    require(math.isclose(math.fsum(exposures), float(validation["physical_exposure_s"]),
                         rel_tol=2e-15, abs_tol=0.0), "top-up exposure does not close")
    require(
        transport_receipt_digest(transport_receipt_records)
        == validation["receipts_manifest_sha256"],
        "top-up receipt-manifest digest differs",
    )
    require(
        source80_validation["receipts_manifest_sha256"]
        == validation["receipts_manifest_sha256"],
        "top-up exact-source/transport receipt binding differs",
    )
    require(int(source80_validation["jobs_validated"]) == len(jobs)
            and int(source80_validation["bins_per_job"]) == 80,
            "top-up exact-source validation coverage differs")
    require(source80_validation["contract_sha256"] == records["contract"]["sha256"]
            and source80_validation["controller_sha256"] == records["controller"]["sha256"],
            "top-up exact-source input binding differs")
    require(source80_validation["canonical_fragment_sha256"] == EXPECTED_FRAGMENT_SHA256,
            "top-up exact-source fragment hash differs")
    require(source80_validation["normalized_fragment_sha256"]
            == fragment_audits[0]["normalized_contract_sha256"],
            "top-up normalized source digest differs")
    return jobs, {
        "root": str(root),
        "files": records,
        "frozen_transport_files": frozen_files,
        "receipt_files": transport_receipt_records,
        "receipt_manifest_sha256": transport_receipt_digest(
            transport_receipt_records
        ),
        "source_files": source_records,
        "source_manifest_sha256": records_digest(source_records),
        "normalized_fragment": fragment_audits[0],
        "jobs": len(jobs),
        "incident_photons": sum(int(job["events"]) for job in jobs),
        "physical_exposure_s": math.fsum(exposures),
        "seeds": all_seeds,
    }


def npz_arrays(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {name: np.asarray(data[name]) for name in data.files}


def check_hit_layout(arrays: Mapping[str, np.ndarray], label: str) -> None:
    starts = np.asarray(arrays["hit_start"], dtype=np.int64)
    counts = np.asarray(arrays["hit_count"], dtype=np.int64)
    hits = len(arrays["hit_code"])
    require(starts.ndim == counts.ndim == 1 and len(starts) == len(counts),
            f"{label} hit event arrays differ")
    if len(starts):
        require(starts[0] == 0, f"{label} first hit_start is not zero")
        require(np.all(starts >= 0) and np.all(counts >= 0), f"{label} negative hit layout")
        require(np.all(starts[:-1] + counts[:-1] == starts[1:]),
                f"{label} hit_start is not exactly cumulative")
        require(int(starts[-1] + counts[-1]) == hits, f"{label} hit layout does not close")


def load_old_response(old_response: Path) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    root = old_response.resolve()
    response_records = {name: file_record(root / name) for name in FOUR_RESPONSE_FILES}
    for name, expected in OLD_REQUIRED_HASHES.items():
        require(response_records[name]["sha256"] == expected,
                f"frozen old B60 compact authority differs: {name}")
    summary = load_json(root / "summary.json")
    require(int(summary["incident_photons"]) == BASE_INCIDENT_PHOTONS, "old incident count differs")
    require(int(summary["jobs"]) == BASE_JOBS, "old job count differs")
    require(int(summary["detector_positive_events"]) == BASE_DETECTOR_POSITIVE,
            "old detector-positive count differs")
    arrays = npz_arrays(root / "mono_line_event_catalog.npz")
    required = set(EVENT_FIELDS) - {"compton_keep"}
    required.update(HIT_FIELDS)
    required.update(("source_bin80", "event_job_index", "base_event_weight_cps"))
    require(required <= set(arrays), "old compact response arrays are incomplete")
    require(len(arrays["event_id"]) == BASE_DETECTOR_POSITIVE, "old compact count differs")
    require(set(np.unique(arrays["event_job_index"]).tolist()) == set(range(BASE_JOBS)),
            "old compact job indices differ")
    check_hit_layout(arrays, "old compact response")

    cache_dir = root / "job_catalogs"
    meta_paths = sorted(cache_dir.glob("*.json"))
    metas = [load_json(path) for path in meta_paths]
    require(len(metas) == BASE_JOBS, "old compact auxiliary cache count differs")
    by_index = {int(meta["scan_index"]): meta for meta in metas}
    meta_path_by_index = {
        int(meta["scan_index"]): path for meta, path in zip(metas, meta_paths)
    }
    require(set(by_index) == set(range(BASE_JOBS)), "old compact auxiliary indices differ")
    compton = np.empty(BASE_DETECTOR_POSITIVE, dtype=np.uint8)
    cache_records: list[dict[str, Any]] = []
    event_ids = arrays["event_id"].astype(np.int64)
    event_jobs = arrays["event_job_index"].astype(np.int64)
    old_seeds: list[int] = []
    for index in range(BASE_JOBS):
        meta = by_index[index]
        require(
            meta.get("status") == "PASS__COMPACT_JOB_CATALOG",
            f"old cache status differs: {index}",
        )
        meta_path = meta_path_by_index[index]
        catalog_path = Path(meta["catalog_path"]).resolve()
        if not catalog_path.is_file():
            # Promotion relocates the frozen response directory but deliberately
            # does not rewrite the hashed legacy per-job metadata.  The receipt
            # binds the relocated sibling NPZ, so use that exact sibling when
            # replaying the 52-job compatibility path after promotion.
            catalog_path = meta_path.with_suffix(".npz").resolve()
        require(catalog_path.is_file(), f"old compact catalog is missing: {index}")
        cache = npz_arrays(catalog_path)
        positions = np.flatnonzero(event_jobs == index)
        require(
            len(positions) and np.all(np.diff(positions) == 1),
            f"old job not contiguous: {index}",
        )
        require(np.array_equal(event_ids[positions], cache["event_id"].astype(np.int64)),
                f"old compact/cache event IDs differ: {index}")
        require(len(cache["compton_keep"]) == len(positions), f"old compton cache differs: {index}")
        compton[positions] = cache["compton_keep"].astype(np.uint8)
        cache_records.extend((file_record(meta_path), file_record(catalog_path)))
        old_seeds.append(int(meta["seed"]))
    require(len(set(old_seeds)) == BASE_JOBS, "old response seeds are not unique")
    arrays["compton_keep"] = compton
    old_line_roots = summary.get("line_roots")
    if old_line_roots is None:
        old_line_roots = [summary["line_root"]]
    return arrays, {
        "mode": "legacy_52_compact",
        "root": str(root),
        "line_roots": [str(path) for path in old_line_roots],
        "summary": summary,
        "incident_photons": BASE_INCIDENT_PHOTONS,
        "jobs": BASE_JOBS,
        "detector_positive_events": BASE_DETECTOR_POSITIVE,
        "physical_exposure_s": float(summary["physical_exposure_s"]),
        "response_files": response_records,
        "auxiliary_job_cache_files": cache_records,
        "auxiliary_job_cache_manifest_sha256": records_digest(cache_records),
        "seeds": old_seeds,
    }


def seeds_from_merge_receipt(receipt: Mapping[str, Any]) -> list[int]:
    """Recover every prefix transport seed from its replayable receipt inputs."""
    inputs = receipt["inputs"]
    recorded = inputs.get("old_response_seeds")
    if recorded is not None:
        seeds = [int(seed) for seed in recorded]
    else:
        seeds = []
        for record in inputs["old_auxiliary_job_cache_files"]:
            path = Path(record["path"])
            if path.suffix != ".json":
                continue
            meta = load_json(path)
            require(meta.get("status") == "PASS__COMPACT_JOB_CATALOG",
                    f"prefix seed metadata status differs: {path}")
            seeds.append(int(meta["seed"]))
    seeds.extend(int(seed) for seed in inputs["topup"]["seeds"])
    jobs = int(receipt["result"]["jobs"])
    require(len(seeds) == jobs, "merged-prefix seed registry does not cover every job")
    require(len(set(seeds)) == jobs, "merged-prefix seed registry is not unique")
    return seeds


def load_merged_response(
    merged_response: Path, *, allow_historical_location: bool = False
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Load an approved promoted authority without rescanning any raw SIM."""
    root = merged_response.resolve()
    records = {name: file_record(root / name) for name in FIVE_MERGED_PREFIX_FILES}
    mode = promoted_mode_from_records(records)
    validation = validate_output(
        root,
        verify_inputs=True,
        allow_historical_location=allow_historical_location,
    )
    receipt = load_json(root / "MERGE_RECEIPT.json")
    summary = load_json(root / "summary.json")
    result = receipt["result"]
    arrays = npz_arrays(root / "mono_line_event_catalog.npz")
    required = set(EVENT_FIELDS) | set(HIT_FIELDS) | {
        "source_bin80", "event_job_index", "base_event_weight_cps"
    }
    require(required <= set(arrays), "merged-prefix compact arrays are incomplete")
    detector_positive = int(result["detector_positive_events"])
    jobs = int(result["jobs"])
    require(len(arrays["event_id"]) == detector_positive,
            "merged-prefix detector-positive count differs")
    require(set(np.unique(arrays["event_job_index"]).tolist()) == set(range(jobs)),
            "merged-prefix job indices differ")
    require(np.all(np.diff(arrays["event_job_index"].astype(np.int64)) >= 0),
            "merged-prefix job indices are not ordered")
    require(arrays["compton_keep"].dtype == np.dtype("uint8"),
            "merged-prefix compton_keep is not directly reusable")
    require(np.all(arrays["compton_keep"] <= 1),
            "merged-prefix compton_keep values differ")
    check_hit_layout(arrays, "merged compact prefix")
    seeds = seeds_from_merge_receipt(receipt)
    line_roots = summary.get("line_roots")
    require(isinstance(line_roots, list) and len(line_roots) >= 2,
            "merged-prefix line roots are incomplete")
    return arrays, {
        "mode": mode,
        "root": str(root),
        "line_roots": [str(path) for path in line_roots],
        "summary": summary,
        "incident_photons": int(result["incident_photons"]),
        "jobs": jobs,
        "detector_positive_events": detector_positive,
        "physical_exposure_s": float(result["physical_exposure_s"]),
        "response_files": records,
        "auxiliary_job_cache_files": [],
        "auxiliary_job_cache_manifest_sha256": records_digest([]),
        "seeds": seeds,
        "prefix_validation": validation,
    }


def load_base_response(
    response: Path,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    if (response.resolve() / "MERGE_RECEIPT.json").is_file():
        return load_merged_response(response)
    return load_old_response(response)


def source_bin80_from_dir_z(dir_z: float) -> int:
    return max(0, min(79, int(math.floor((1.0 + dir_z) * 40.0))))


def extract_primary_bins(sim_path: Path, wanted: set[int]) -> dict[int, int]:
    found: dict[int, int] = {}
    current: int | None = None
    with gzip.open(sim_path, "rt", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("ID "):
                fields = line.split()
                current = int(fields[1]) if len(fields) >= 2 else None
                continue
            if current not in wanted or not line.startswith("IA INIT"):
                continue
            fields = [value.strip() for value in line.split(";")]
            require(len(fields) > 18, f"malformed IA INIT: {sim_path}")
            require(current not in found, f"multiple IA INIT records: {sim_path}:{current}")
            found[current] = source_bin80_from_dir_z(float(fields[18]))
    require(set(found) == wanted, f"primary-bin recovery incomplete: {sim_path}")
    return found


def cache_contract_payload(
    topup: Mapping[str, Any], builder: Any, config: Mapping[str, Any], *, base_jobs: int
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "PASS__B60_TOPUP_COMPACT_CACHE_CONTRACT",
        "topup_root": topup["root"],
        "topup_contract_sha256": topup["files"]["contract"]["sha256"],
        "topup_validation_sha256": topup["files"]["validation"]["sha256"],
        "topup_controller_sha256": topup["files"]["controller"]["sha256"],
        "topup_receipt_manifest_sha256": topup["receipt_manifest_sha256"],
        "topup_source_manifest_sha256": topup["source_manifest_sha256"],
        "jobs": int(topup["jobs"]),
        "incident_photons": int(topup["incident_photons"]),
        "job_indices": [base_jobs, base_jobs + int(topup["jobs"]) - 1],
        "analysis_files": {
            "compact_merge": file_record(HERE),
            "legacy_analyzer": file_record(ANALYZER),
            "topup_runner": file_record(TOPUP_RUNNER),
            "response_builder": file_record(B_BUILDER),
            "response_config": file_record(B_CONFIG),
            "side_compton": file_record(SIDE_COMPTON),
            "adaptive_generator": file_record(ADAPTIVE_SCRIPT),
        },
        "selection_authority": selection_authority(builder, config),
        "source_bin80_cache_contract": {
            "mapping": "floor((1+IA_INIT_dir_z)*40), clipped to [0,79]",
            "primary_record": "exactly one IA INIT for each detector-positive event",
            "persistence": "per-job directory-atomic NPZ plus JSON hash receipt",
        },
    }


def load_or_create_cache_contract(
    cache_root: Path,
    topup: Mapping[str, Any],
    builder: Any,
    config: Mapping[str, Any],
    *,
    base_jobs: int,
) -> dict[str, Any]:
    root = cache_root.resolve()
    payload = cache_contract_payload(topup, builder, config, base_jobs=base_jobs)
    contract_path = root / "CACHE_CONTRACT.json"
    if not root.exists():
        root.mkdir(parents=True, exist_ok=False)
        atomic_json(contract_path, payload)
    else:
        require(root.is_dir() and contract_path.is_file(), "cache root is uncontracted")
        require(load_json(contract_path) == payload, "existing cache contract differs")
    (root / "jobs").mkdir(exist_ok=True)
    return payload


def validate_cached_job(job: Mapping[str, Any], job_dir: Path) -> dict[str, Any]:
    meta_path = job_dir / "compact.json"
    catalog_path = job_dir / "compact.npz"
    bins_meta_path = job_dir / "source_bin80.json"
    bins_path = job_dir / "source_bin80.npz"
    require(all(path.is_file() for path in (meta_path, catalog_path, bins_meta_path, bins_path)),
            f"incomplete compact cache: {job_dir}")
    meta = load_json(meta_path)
    bins_meta = load_json(bins_meta_path)
    require(meta.get("status") == "PASS__COMPACT_JOB_CATALOG", f"bad compact cache: {job_dir}")
    for key in ("scan_index", "seed", "events", "sim_bytes"):
        require(int(meta[key]) == int(job[key]), f"cached {key} differs: {job['job_id']}")
    for key in ("job_id", "sim_path", "expected_geometry"):
        require(str(meta[key]) == str(job[key]), f"cached {key} differs: {job['job_id']}")
    require(meta["source_sha256"] == job["source_sha256"], "cached source hash differs")
    require(meta["receipt_sha256"] == job["receipt_sha256"], "cached receipt hash differs")
    require(meta["catalog_sha256"] == sha256(catalog_path), "compact cache hash differs")
    require(bins_meta.get("status") == "PASS__PERSISTENT_SOURCE_BIN80_CACHE",
            f"bad source-bin cache: {job['job_id']}")
    require(
        bins_meta["catalog_sha256"] == meta["catalog_sha256"],
        "source-bin/catalog binding differs",
    )
    require(
        bins_meta["source_bin80_npz_sha256"] == sha256(bins_path),
        "source-bin cache hash differs",
    )
    compact = npz_arrays(catalog_path)
    bins = npz_arrays(bins_path)
    require(np.array_equal(compact["event_id"], bins["event_id"]), "source-bin event IDs differ")
    require(bins["source_bin80"].dtype == np.dtype("uint8"), "source-bin dtype differs")
    require(np.all(bins["source_bin80"] < 80), "source-bin values differ")
    require(len(compact["event_id"]) == int(meta["detector_positive_events"]),
            "compact detector-positive count differs")
    check_hit_layout(compact, f"new compact job {job['job_id']}")
    return {
        "job": dict(job),
        "meta": meta,
        "compact": compact,
        "bins": bins["source_bin80"].astype(np.uint8, copy=True),
        "files": [
            file_record(path)
            for path in (meta_path, catalog_path, bins_meta_path, bins_path)
        ],
    }


def create_cached_job(
    job: Mapping[str, Any], cache_root: Path, builder: Any, disk: Mapping[str, Any], reject: str
) -> dict[str, Any]:
    final = cache_root / "jobs" / f"job_{int(job['scan_index']):03d}_{job['job_id']}"
    if final.exists():
        return validate_cached_job(job, final)
    temporary = Path(
        tempfile.mkdtemp(
            prefix=f".building_{int(job['scan_index']):03d}_", dir=cache_root
        )
    )
    try:
        builder_meta = builder.scan_job(
            dict(job), str(temporary), ACTIVE_VETO_THRESHOLD_KEV, dict(disk), reject
        )
        source_catalog = Path(builder_meta["catalog_path"])
        compact = npz_arrays(source_catalog)
        ids = compact["event_id"].astype(np.int64)
        recovered = extract_primary_bins(
            Path(job["sim_path"]), set(int(value) for value in ids)
        )
        bins = np.asarray([recovered[int(value)] for value in ids], dtype=np.uint8)

        final_catalog = temporary / "compact.npz"
        os.replace(source_catalog, final_catalog)
        source_meta = source_catalog.with_suffix(".json")
        if source_meta.is_file():
            source_meta.unlink()
        bins_path = temporary / "source_bin80.npz"
        with bins_path.open("xb") as handle:
            np.savez_compressed(handle, event_id=compact["event_id"], source_bin80=bins)
            handle.flush()
            os.fsync(handle.fileno())
        meta = {
            **builder_meta,
            "catalog_path": str((final / "compact.npz").resolve()),
            "source_sha256": job["source_sha256"],
            "receipt_sha256": job["receipt_sha256"],
            "catalog_sha256": sha256(final_catalog),
        }
        atomic_json(temporary / "compact.json", meta)
        bins_meta = {
            "schema_version": 1,
            "status": "PASS__PERSISTENT_SOURCE_BIN80_CACHE",
            "job_id": job["job_id"],
            "scan_index": int(job["scan_index"]),
            "events_cached": len(ids),
            "source_bin80_minimum": int(np.min(bins)) if len(bins) else None,
            "source_bin80_maximum": int(np.max(bins)) if len(bins) else None,
            "mapping": "floor((1+IA_INIT_dir_z)*40), clipped to [0,79]",
            "sim_path": job["sim_path"],
            "sim_bytes": int(job["sim_bytes"]),
            "source_sha256": job["source_sha256"],
            "receipt_sha256": job["receipt_sha256"],
            "catalog_sha256": sha256(final_catalog),
            "source_bin80_npz_sha256": sha256(bins_path),
        }
        atomic_json(temporary / "source_bin80.json", bins_meta)
        os.replace(temporary, final)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return validate_cached_job(job, final)


def scan_topup_jobs(
    jobs: Sequence[Mapping[str, Any]], cache_root: Path, builder: Any, config: Mapping[str, Any]
) -> list[dict[str, Any]]:
    side = config["side_entry_disk"]
    disk = builder.side_entry_disk(
        tuple(float(value) for value in side["local_center_cm"]),
        float(side["radius_cm"]),
        float(side["rotation_y_deg"]),
    )
    reject = str(side.get("reject_policy", "keep"))
    cached: list[dict[str, Any]] = []
    for ordinal, job in enumerate(jobs, 1):
        record = create_cached_job(job, cache_root, builder, disk, reject)
        cached.append(record)
        print(json.dumps({
            "status": "CACHED__B60_TOPUP_JOB",
            "job": job["job_id"],
            "scan_index": int(job["scan_index"]),
            "complete": ordinal,
            "total": len(jobs),
            "detector_positive_events": int(record["meta"]["detector_positive_events"]),
        }), flush=True)
    return cached


def merge_arrays(
    old: Mapping[str, np.ndarray], cached: Sequence[Mapping[str, Any]], exposure: float
) -> dict[str, np.ndarray]:
    event_chunks = {field: [np.asarray(old[field])] for field in EVENT_FIELDS}
    hit_chunks = {field: [np.asarray(old[field])] for field in HIT_FIELDS}
    bin_chunks = [np.asarray(old["source_bin80"], dtype=np.uint8)]
    job_chunks = [np.asarray(old["event_job_index"], dtype=np.uint16)]
    hit_offset = len(old["hit_code"])
    for record in cached:
        compact = record["compact"]
        starts = compact["hit_start"].astype(np.int64) + hit_offset
        for field in EVENT_FIELDS:
            chunk = starts if field == "hit_start" else np.asarray(compact[field])
            event_chunks[field].append(chunk)
        for field in HIT_FIELDS:
            hit_chunks[field].append(np.asarray(compact[field]))
        count = len(compact["event_id"])
        bin_chunks.append(np.asarray(record["bins"], dtype=np.uint8))
        job_chunks.append(np.full(count, int(record["job"]["scan_index"]), dtype=np.uint16))
        hit_offset += len(compact["hit_code"])
    merged = {
        field: np.concatenate(chunks) if chunks else np.empty(0)
        for field, chunks in {**event_chunks, **hit_chunks}.items()
    }
    merged["source_bin80"] = np.concatenate(bin_chunks)
    merged["event_job_index"] = np.concatenate(job_chunks)
    merged["base_event_weight_cps"] = np.full(
        len(merged["event_id"]), 1.0 / exposure, dtype=np.float64
    )
    return merged


def response_rows(
    arrays: Mapping[str, np.ndarray], weight: float
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cutflow: list[dict[str, Any]] = []
    for window, field in WINDOW_FIELDS.items():
        flags = arrays[field]
        for stage, bit in STAGES.items():
            count = int(np.count_nonzero((flags & bit) != 0))
            cutflow.append({
                "model": "b",
                "window_id": window,
                "stage": stage,
                "selected_events": count,
                "event_weight_cps": weight,
                "weighted_rate_cps": count * weight,
                "weighted_mc_sigma_cps": math.sqrt(count) * weight,
                "effective_selected_events": count,
            })
    final = (arrays[WINDOW_FIELDS[FINAL_WINDOW]] & STAGES[FINAL_STAGE]) != 0
    counts = np.bincount(arrays["source_bin80"][final].astype(np.int64), minlength=80)
    by_bin = [{
        "source_bin80": index,
        "selected_events": int(count),
        "weighted_rate_cps": int(count) * weight,
    } for index, count in enumerate(counts)]
    return cutflow, by_bin


def build(
    old_response: Path, topup_root: Path, cache_root: Path, output: Path
) -> dict[str, Any]:
    output = output.resolve()
    require(not output.exists(), f"directory-level non-overwrite gate: {output}")
    require(output.parent.is_dir(), f"staging parent is missing: {output.parent}")
    old, old_audit = load_base_response(old_response)
    base_jobs = int(old_audit["jobs"])
    jobs, topup_audit = load_topup(
        topup_root, scan_index_start=base_jobs
    )
    require(set(old_audit["seeds"]).isdisjoint(topup_audit["seeds"]),
            "top-up seed overlaps frozen compact prefix")
    builder = load_module("m05_b60_topup_compact_builder", B_BUILDER)
    config = load_json(B_CONFIG)
    cache_contract = load_or_create_cache_contract(
        cache_root, topup_audit, builder, config, base_jobs=base_jobs
    )
    exposure = float(old_audit["physical_exposure_s"]) + float(
        topup_audit["physical_exposure_s"])
    require(math.isfinite(exposure) and exposure > 0.0, "combined exposure is invalid")
    for job in jobs:
        job["weight_cps"] = 1.0 / exposure
    cached = scan_topup_jobs(jobs, cache_root.resolve(), builder, config)
    merged = merge_arrays(old, cached, exposure)
    check_hit_layout(merged, "merged response")
    detector_positive = len(merged["event_id"])
    incident = int(old_audit["incident_photons"]) + int(topup_audit["incident_photons"])
    job_count = base_jobs + len(jobs)
    require(set(np.unique(merged["event_job_index"]).tolist()) == set(range(job_count)),
            "merged job indices do not span the prefix plus new top-up")
    require(np.all(np.diff(merged["event_job_index"].astype(np.int64)) >= 0),
            "merged jobs are not contiguous and ordered")
    weight = 1.0 / exposure
    cutflow, by_bin = response_rows(merged, weight)
    final_count = next(
        int(row["selected_events"])
        for row in cutflow
        if row["window_id"] == FINAL_WINDOW and row["stage"] == FINAL_STAGE
    )

    temporary = output.parent / f".{output.name}.building.{os.getpid()}"
    require(not temporary.exists(), f"staging build directory exists: {temporary}")
    temporary.mkdir(exist_ok=False)
    try:
        catalog_path = temporary / "mono_line_event_catalog.npz"
        with catalog_path.open("xb") as handle:
            np.savez_compressed(handle, **merged)
            handle.flush()
            os.fsync(handle.fileno())
        write_csv(temporary / "mono_line_cutflow.csv", cutflow)
        write_csv(temporary / "mono_line_final_by_source_bin80.csv", by_bin)
        summary = {
            "status": "COMPLETE__MONO_LINE_COMMON_RESPONSE",
            "model": "b",
            "line_roots": [*old_audit["line_roots"], topup_audit["root"]],
            "geometry_setup": topup_audit["frozen_transport_files"]["setup"]["path"],
            "incident_photons": incident,
            "jobs": job_count,
            "physical_exposure_s": exposure,
            "event_weight_cps": weight,
            "detector_positive_events": detector_positive,
            "detector_positive_rate_cps": detector_positive * weight,
            "w2_final_selected_events": final_count,
            "w2_final_rate_cps": final_count * weight,
            "w2_final_mc_sigma_cps": math.sqrt(final_count) * weight,
            "w2_final_relative_mc_sigma": (
                1.0 / math.sqrt(final_count) if final_count else None
            ),
            "w2_final_effective_sample_size": final_count,
            "catalog": "mono_line_event_catalog.npz",
            "response_authority_receipt": "MERGE_RECEIPT.json",
            "normalization": (
                "every prefix and top-up detector-positive event carries one common "
                "1/sum(T_E)"
            ),
            "merge_method": (
                f"frozen {old_audit['mode']} prefix plus newly scanned top-up jobs; "
                "no prefix raw SIM rescan"
            ),
            "job_index_contract": (
                f"prefix=0..{base_jobs - 1}; "
                f"top-up={base_jobs}..{job_count - 1}"
            ),
            "sim_hashes_computed": 0,
        }
        atomic_json(temporary / "summary.json", summary)
        cache_files = [file for record in cached for file in record["files"]]
        output_records = {}
        for name in FOUR_RESPONSE_FILES:
            record = file_record(temporary / name)
            record["path"] = name
            output_records[name] = record
        receipt = {
            "schema_version": 1,
            "status": "PASS__B60_COMPACT_TOPUP_MERGE_AUTHORITY",
            "method": {
                "prefix_raw_sim_files_scanned": 0,
                "new_raw_sim_jobs_scanned": len(jobs),
                "base_mode": old_audit["mode"],
                "base_compact_prefix_events": int(old_audit["detector_positive_events"]),
                "new_job_source_bin80_cache": "PERSISTENT__PER_JOB_DIRECTORY_ATOMIC",
                "output_policy": "ALL_NEW_STAGING_DIRECTORY__REFUSE_OVERWRITE",
            },
            "inputs": {
                "base_response": {
                    "mode": old_audit["mode"],
                    "root": old_audit["root"],
                    "files": old_audit["response_files"],
                    "result": {
                        "incident_photons": int(old_audit["incident_photons"]),
                        "jobs": base_jobs,
                        "job_index_minimum": 0,
                        "job_index_maximum": base_jobs - 1,
                        "detector_positive_events": int(
                            old_audit["detector_positive_events"]
                        ),
                        "physical_exposure_s": float(
                            old_audit["physical_exposure_s"]
                        ),
                    },
                },
                "old_response_mode": old_audit["mode"],
                "old_response_root": old_audit["root"],
                "old_response_files": old_audit["response_files"],
                "old_response_seeds": old_audit["seeds"],
                "old_auxiliary_job_cache_manifest_sha256": old_audit[
                    "auxiliary_job_cache_manifest_sha256"
                ],
                "old_auxiliary_job_cache_files": old_audit["auxiliary_job_cache_files"],
                "topup": topup_audit,
                "cache_contract": cache_contract,
                "cache_contract_file": file_record(cache_root.resolve() / "CACHE_CONTRACT.json"),
                "new_compact_cache_files": cache_files,
                "new_compact_cache_manifest_sha256": records_digest(cache_files),
            },
            "selection_authority": selection_authority(builder, config),
            "source_authority": topup_audit["normalized_fragment"],
            "result": {
                "incident_photons": incident,
                "jobs": job_count,
                "job_index_minimum": 0,
                "job_index_maximum": job_count - 1,
                "detector_positive_events": detector_positive,
                "physical_exposure_s": exposure,
                "event_weight_cps": weight,
                "w2_final_selected_events": final_count,
                "w2_final_rate_cps": final_count * weight,
                "hit_records": len(merged["hit_code"]),
            },
            "outputs": output_records,
        }
        atomic_json(temporary / "MERGE_RECEIPT.json", receipt)
        validate_output(temporary, verify_inputs=True)
        os.replace(temporary, output)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    result = validate_output(output, verify_inputs=True)
    print(json.dumps(result, indent=2, sort_keys=True), flush=True)
    return result


def validate_output(
    output: Path, *, verify_inputs: bool, allow_historical_location: bool = False
) -> dict[str, Any]:
    root = output.resolve()
    receipt_path = root / "MERGE_RECEIPT.json"
    receipt = load_json(receipt_path)
    require(receipt.get("status") == "PASS__B60_COMPACT_TOPUP_MERGE_AUTHORITY",
            "merge receipt status differs")
    require(int(receipt.get("schema_version", -1)) == 1, "merge receipt schema differs")
    promotion = receipt.get("promotion")
    if promotion is not None:
        require(
            promotion.get("status")
            == "PASS__OLD_INPUT_PATHS_RELOCATED__POSTVALIDATION_GATE",
            "promotion receipt status differs",
        )
        if not allow_historical_location:
            require(Path(promotion["canonical"]).resolve() == root,
                    "promotion canonical path differs")
        require(
            Path(promotion["recoverable_old_authority"]).resolve()
            == Path(receipt["inputs"]["old_response_root"]).resolve(),
            "promotion archive/old-input path differs",
        )
    for name in FOUR_RESPONSE_FILES:
        record = receipt["outputs"][name]
        path = root / name
        require(path.stat().st_size == int(record["bytes"]), f"output size differs: {name}")
        require(sha256(path) == record["sha256"], f"output hash differs: {name}")
    summary = load_json(root / "summary.json")
    result = receipt["result"]
    for key in ("incident_photons", "jobs", "detector_positive_events", "w2_final_selected_events"):
        require(int(summary[key]) == int(result[key]), f"summary/receipt differs: {key}")
    for key in ("physical_exposure_s", "event_weight_cps", "w2_final_rate_cps"):
        require(math.isclose(float(summary[key]), float(result[key]), rel_tol=2e-15, abs_tol=0.0),
                f"summary/receipt differs: {key}")
    arrays = npz_arrays(root / "mono_line_event_catalog.npz")
    required = set(EVENT_FIELDS) | set(HIT_FIELDS) | {
        "source_bin80", "event_job_index", "base_event_weight_cps"
    }
    require(required <= set(arrays), "merged response arrays are incomplete")
    count = int(result["detector_positive_events"])
    merged_event_fields = (
        *EVENT_FIELDS,
        "source_bin80",
        "event_job_index",
        "base_event_weight_cps",
    )
    for field in merged_event_fields:
        require(np.asarray(arrays[field]).ndim == 1 and len(arrays[field]) == count,
                f"merged event array length differs: {field}")
    for field in HIT_FIELDS:
        require(
            len(arrays[field]) == int(result["hit_records"]),
            f"merged hit length differs: {field}",
        )
    check_hit_layout(arrays, "validated merged response")
    weights = arrays["base_event_weight_cps"]
    require(weights.dtype == np.dtype("float64") and np.all(weights == weights[0]),
            "merged event weights are not one constant float64 value")
    require(math.isclose(float(weights[0]), 1.0 / float(result["physical_exposure_s"]),
                         rel_tol=2e-15, abs_tol=0.0), "merged weight is not 1/sum(T_E)")
    jobs = arrays["event_job_index"].astype(np.int64)
    require(np.all(np.diff(jobs) >= 0), "merged jobs are not contiguous")
    require(set(np.unique(jobs).tolist()) == set(range(int(result["jobs"]))),
            "merged job-index coverage differs")
    require(int(np.min(jobs)) == 0 and int(np.max(jobs)) == int(result["jobs"]) - 1,
            "merged job-index endpoints differ")
    bins = arrays["source_bin80"]
    require(bins.dtype == np.dtype("uint8") and np.all(bins < 80), "merged source bins differ")
    require(set(np.unique(bins).tolist()) == set(range(80)), "merged source bins do not span 80")
    for field in ("broad_flags", "w2_flags"):
        require(np.all((arrays[field].astype(np.uint64) & np.uint64(0xE0)) == 0),
                f"unknown response flag bits: {field}")
    cutflow, by_bin = response_rows(arrays, float(result["event_weight_cps"]))
    require((root / "mono_line_cutflow.csv").read_text(encoding="utf-8") == csv_text(cutflow),
            "merged cutflow does not recompute exactly")
    require(
        (root / "mono_line_final_by_source_bin80.csv").read_text(encoding="utf-8")
        == csv_text(by_bin),
        "merged by-bin response does not recompute exactly",
    )
    final_count = next(int(row["selected_events"]) for row in cutflow
                       if row["window_id"] == FINAL_WINDOW and row["stage"] == FINAL_STAGE)
    require(
        final_count == int(result["w2_final_selected_events"]),
        "merged final selection differs",
    )
    source_authority = receipt["source_authority"]
    require(source_authority.get("status") == "PASS__EXACT_NORMALIZED_PARMA_80BIN_FRAGMENT",
            "receipt lacks exact normalized source validation")
    require(source_authority["canonical_fragment_sha256"] == EXPECTED_FRAGMENT_SHA256,
            "receipt source fragment differs")
    old_cache_records = receipt["inputs"]["old_auxiliary_job_cache_files"]
    require(
        records_digest(old_cache_records)
        == receipt["inputs"]["old_auxiliary_job_cache_manifest_sha256"],
        "old compact-cache receipt manifest differs",
    )

    inputs = receipt["inputs"]
    old_mode = inputs.get("old_response_mode", "legacy_52_compact")
    expected_old_hashes = required_hashes_for_mode(old_mode)
    require(set(inputs["old_response_files"]) == set(expected_old_hashes),
            "compact-prefix frozen file set differs")
    for name, expected in expected_old_hashes.items():
        require(inputs["old_response_files"][name]["sha256"] == expected,
                f"compact-prefix receipt hash differs: {name}")
    base_response = inputs.get("base_response")
    if base_response is not None:
        require(base_response.get("mode") == old_mode,
                "base-response mode differs")
        require(Path(base_response["root"]).resolve()
                == Path(inputs["old_response_root"]).resolve(),
                "base-response root differs")
        require(base_response["files"] == inputs["old_response_files"],
                "base-response file binding differs")
        base_result = base_response["result"]
        topup_result = inputs["topup"]
        require(int(base_result["job_index_minimum"]) == 0
                and int(base_result["job_index_maximum"]) == int(base_result["jobs"]) - 1,
                "base-response job-index endpoints differ")
        require(int(result["jobs"]) == int(base_result["jobs"]) + int(topup_result["jobs"]),
                "base plus incremental top-up jobs do not close")
        require(int(result["incident_photons"])
                == int(base_result["incident_photons"])
                + int(topup_result["incident_photons"]),
                "base plus incremental top-up incidents do not close")
        require(math.isclose(
                    float(result["physical_exposure_s"]),
                    float(base_result["physical_exposure_s"])
                    + float(topup_result["physical_exposure_s"]),
                    rel_tol=2e-15,
                    abs_tol=0.0,
                ), "base plus incremental top-up exposure does not close")
        require(int(receipt["method"]["base_compact_prefix_events"])
                == int(base_result["detector_positive_events"]),
                "base detector-positive count differs")
    recorded_old_seeds = inputs.get("old_response_seeds")
    if recorded_old_seeds is not None:
        old_seeds = [int(seed) for seed in recorded_old_seeds]
        topup_seeds = [int(seed) for seed in inputs["topup"]["seeds"]]
        require(len(set(old_seeds)) == len(old_seeds),
                "compact-prefix recorded seeds are not unique")
        require(set(old_seeds).isdisjoint(topup_seeds),
                "top-up seed overlaps compact prefix in merge receipt")
        require(len(old_seeds) + len(topup_seeds) == int(result["jobs"]),
                "merge receipt seed registry does not cover every job")

    if verify_inputs:
        for name, record in inputs["old_response_files"].items():
            path = Path(record["path"])
            require(path.is_file() and path.stat().st_size == int(record["bytes"])
                    and sha256(path) == record["sha256"],
                    f"old input binding differs: {name}")
        for record in inputs["old_auxiliary_job_cache_files"]:
            path = Path(record["path"])
            require(path.is_file() and path.stat().st_size == int(record["bytes"])
                    and sha256(path) == record["sha256"],
                    f"old compact-cache binding differs: {path}")
        if old_mode in PROMOTED_PREFIX_REQUIRED_HASHES:
            # Recompute the prior merge products and reverify every transport,
            # cache, and original-prefix input named by its immutable receipt.
            validate_output(
                Path(inputs["old_response_root"]),
                verify_inputs=True,
                allow_historical_location=True,
            )
        topup = inputs["topup"]
        topup_records = (
            list(topup["files"].values())
            + list(topup["frozen_transport_files"].values())
            + list(topup["receipt_files"])
            + list(topup["source_files"])
        )
        for record in topup_records:
            path = Path(record["path"])
            require(path.is_file() and path.stat().st_size == int(record["bytes"])
                    and sha256(path) == record["sha256"], f"top-up input binding differs: {path}")
        cache_contract = inputs["cache_contract_file"]
        cache_contract_path = Path(cache_contract["path"])
        require(cache_contract_path.is_file()
                and sha256(cache_contract_path) == cache_contract["sha256"],
                "compact-cache contract binding differs")
        for record in inputs["new_compact_cache_files"]:
            path = Path(record["path"])
            require(path.is_file() and sha256(path) == record["sha256"],
                    f"new compact-cache binding differs: {path}")
    return {
        "status": "PASS__B60_COMPACT_TOPUP_STAGING_VALIDATED",
        "output": str(root),
        "receipt_sha256": sha256(receipt_path),
        "incident_photons": int(result["incident_photons"]),
        "jobs": int(result["jobs"]),
        "detector_positive_events": count,
        "w2_final_selected_events": final_count,
        "event_weight_cps": float(result["event_weight_cps"]),
        "inputs_reverified": verify_inputs,
    }


def csv_text(rows: list[dict[str, Any]]) -> str:
    import io

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def relocated_promotion_receipt(
    receipt: Mapping[str, Any], old_root: Path, archive_root: Path
) -> dict[str, Any]:
    """Relocate only frozen-old input paths while preserving their digests."""
    old_root = old_root.resolve()
    archive_root = archive_root.resolve()
    relocated = copy.deepcopy(dict(receipt))
    inputs = relocated["inputs"]
    require(
        Path(inputs["old_response_root"]).resolve() == old_root,
        "receipt old-response root differs before relocation",
    )
    inputs["old_response_root"] = str(archive_root)
    record_groups = (
        inputs["old_response_files"].values(),
        inputs["old_auxiliary_job_cache_files"],
    )
    for records in record_groups:
        for record in records:
            original = Path(record["path"]).resolve()
            try:
                relative = original.relative_to(old_root)
            except ValueError as error:
                raise MergeError(
                    f"old input path escapes canonical response: {original}"
                ) from error
            record["path"] = str(archive_root / relative)
    inputs["old_auxiliary_job_cache_manifest_sha256"] = records_digest(
        inputs["old_auxiliary_job_cache_files"]
    )
    base_response = inputs.get("base_response")
    if base_response is not None:
        require(Path(base_response["root"]).resolve() == old_root,
                "base-response root differs before relocation")
        base_response["root"] = str(archive_root)
        for record in base_response["files"].values():
            original = Path(record["path"]).resolve()
            try:
                relative = original.relative_to(old_root)
            except ValueError as error:
                raise MergeError(
                    f"base-response input path escapes canonical response: {original}"
                ) from error
            record["path"] = str(archive_root / relative)
    return relocated


def write_exclusive_bytes(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(path.parent)


def rollback_promotion(
    *,
    staging: Path,
    canonical: Path,
    archive: Path,
    receipt_backup: Path,
    original_receipt_sha256: str,
    old_was_moved: bool,
    new_was_moved: bool,
    expected_old_hashes: Mapping[str, str] = OLD_REQUIRED_HASHES,
) -> None:
    """Restore the exact pre-promotion two-directory state or fail loudly."""
    errors: list[str] = []
    if new_was_moved:
        try:
            if receipt_backup.is_file():
                os.replace(receipt_backup, canonical / "MERGE_RECEIPT.json")
                fsync_directory(canonical)
            os.replace(canonical, staging)
            fsync_directory(staging.parent)
        except OSError as error:
            errors.append(f"new-authority rollback failed: {error}")
    if old_was_moved:
        try:
            os.replace(archive, canonical)
            fsync_directory(canonical.parent)
        except OSError as error:
            errors.append(f"old-authority rollback failed: {error}")
    if receipt_backup.is_file() and staging.is_dir():
        try:
            os.replace(receipt_backup, staging / "MERGE_RECEIPT.json")
            fsync_directory(staging)
        except OSError as error:
            errors.append(f"receipt rollback failed: {error}")
    if not errors:
        try:
            require(staging.is_dir(), "rollback did not restore staging")
            require(canonical.is_dir(), "rollback did not restore canonical")
            require(not archive.exists(), "rollback left the archive target occupied")
            require(
                sha256(staging / "MERGE_RECEIPT.json")
                == original_receipt_sha256,
                "rollback did not restore the original receipt",
            )
            for name, expected in expected_old_hashes.items():
                require(
                    sha256(canonical / name) == expected,
                    f"rollback did not restore old canonical: {name}",
                )
        except (MergeError, OSError) as error:
            errors.append(str(error))
    if errors:
        raise MergeError("promotion rollback failed: " + " | ".join(errors))


def promote(staging: Path, canonical: Path, archive: Path) -> dict[str, Any]:
    staging = staging.resolve()
    canonical = canonical.resolve()
    archive = archive.resolve()
    require(staging.is_dir(), f"staging response is missing: {staging}")
    require(canonical.is_dir(), f"canonical response is missing: {canonical}")
    require(not archive.exists(), f"non-overwrite archive gate: {archive}")
    require(archive.parent.is_dir(), f"archive parent is missing: {archive.parent}")
    devices = {
        staging.parent.stat().st_dev,
        canonical.parent.stat().st_dev,
        archive.parent.stat().st_dev,
    }
    require(len(devices) == 1, "promotion paths must share one filesystem")
    validate_output(staging, verify_inputs=True)
    receipt_path = staging / "MERGE_RECEIPT.json"
    original_receipt_bytes = receipt_path.read_bytes()
    original_receipt_sha256 = hashlib.sha256(original_receipt_bytes).hexdigest()
    receipt = json.loads(original_receipt_bytes.decode("utf-8"))
    require(Path(receipt["inputs"]["old_response_root"]).resolve() == canonical,
            "promotion canonical is not the frozen merge prefix")
    old_mode = receipt["inputs"].get("old_response_mode", "legacy_52_compact")
    expected_hashes = required_hashes_for_mode(old_mode)
    require(set(receipt["inputs"]["old_response_files"]) == set(expected_hashes),
            "promotion compact-prefix file set differs")
    for name, expected in expected_hashes.items():
        require(receipt["inputs"]["old_response_files"][name]["sha256"] == expected,
                f"promotion receipt prefix hash differs: {name}")
        require(sha256(canonical / name) == expected, f"canonical changed before promotion: {name}")
    relocated_receipt = relocated_promotion_receipt(receipt, canonical, archive)
    relocated_receipt["promotion"] = {
        "status": "PASS__OLD_INPUT_PATHS_RELOCATED__POSTVALIDATION_GATE",
        "canonical": str(canonical),
        "recoverable_old_authority": str(archive),
        "prepromotion_receipt_sha256": original_receipt_sha256,
        "postpromotion_validation": "validate_output(verify_inputs=True)",
    }
    receipt_backup = canonical.parent / (
        f".{staging.name}.prepromotion-receipt.{os.getpid()}.json"
    )
    require(not receipt_backup.exists(), f"promotion receipt backup exists: {receipt_backup}")
    write_exclusive_bytes(receipt_backup, original_receipt_bytes)
    old_was_moved = False
    new_was_moved = False
    try:
        os.replace(canonical, archive)
        old_was_moved = True
        fsync_directory(canonical.parent)
        os.replace(staging, canonical)
        new_was_moved = True
        fsync_directory(canonical.parent)
        atomic_json(canonical / "MERGE_RECEIPT.json", relocated_receipt)
        validation = validate_output(canonical, verify_inputs=True)
    except BaseException as promotion_error:
        try:
            rollback_promotion(
                staging=staging,
                canonical=canonical,
                archive=archive,
                receipt_backup=receipt_backup,
                original_receipt_sha256=original_receipt_sha256,
                old_was_moved=old_was_moved,
                new_was_moved=new_was_moved,
                expected_old_hashes=expected_hashes,
            )
        except BaseException as rollback_error:
            raise MergeError(
                f"promotion failed ({promotion_error}); {rollback_error}"
            ) from rollback_error
        raise
    if receipt_backup.is_file():
        receipt_backup.unlink()
        fsync_directory(receipt_backup.parent)
    payload = {
        **validation,
        "status": "PASS__B60_COMPACT_TOPUP_ATOMICALLY_PROMOTED",
        "canonical": str(canonical),
        "recoverable_old_authority": str(archive),
    }
    print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
    return payload


def self_test() -> dict[str, Any]:
    canonical_text = LINE_FRAGMENT.read_text(encoding="utf-8")
    audit = validate_normalized_fragment(canonical_text, "PARMA511Day15")
    altered = canonical_text.replace(
        "PARMA511_bin00_down.Flux 0.00012959490410391518",
        "PARMA511_bin00_down.Flux 0.00012959490410391519",
        1,
    )
    rejected = False
    try:
        validate_normalized_fragment(altered, "PARMA511Day15")
    except MergeError:
        rejected = True
    require(rejected, "fragment mutation self-test was not rejected")
    synthetic = {
        "hit_start": np.asarray([0, 1, 1], dtype=np.int64),
        "hit_count": np.asarray([1, 0, 2], dtype=np.uint16),
        "hit_code": np.asarray([1, 2, 3], dtype=np.int32),
    }
    check_hit_layout(synthetic, "synthetic")
    old: dict[str, np.ndarray] = {
        "event_id": np.asarray([1], dtype=np.int32),
        "plastic_keV": np.asarray([0.0], dtype=np.float32),
        "bgo_keV": np.asarray([0.0], dtype=np.float32),
        "measured_total_keV": np.asarray([511.0], dtype=np.float32),
        "broad_flags": np.asarray([31], dtype=np.uint8),
        "w2_flags": np.asarray([31], dtype=np.uint8),
        "compton_keep": np.asarray([1], dtype=np.uint8),
        "hit_start": np.asarray([0], dtype=np.int64),
        "hit_count": np.asarray([1], dtype=np.uint16),
        "hit_code": np.asarray([1], dtype=np.int32),
        "hit_layer": np.asarray([1], dtype=np.uint8),
        "hit_energy_keV": np.asarray([511.0], dtype=np.float32),
        "hit_x_cm": np.asarray([0.0], dtype=np.float32),
        "hit_y_cm": np.asarray([0.0], dtype=np.float32),
        "hit_z_cm": np.asarray([0.0], dtype=np.float32),
        "source_bin80": np.asarray([0], dtype=np.uint8),
        "event_job_index": np.asarray([0], dtype=np.uint16),
        "base_event_weight_cps": np.asarray([1.0], dtype=np.float64),
    }
    new = {
        **{key: value.copy() for key, value in old.items() if key in EVENT_FIELDS},
        **{key: value.copy() for key, value in old.items() if key in HIT_FIELDS},
    }
    merged = merge_arrays(
        old,
        [{
            "compact": new,
            "bins": np.asarray([79], dtype=np.uint8),
            "job": {"scan_index": 52},
        }],
        2.0,
    )
    require(merged["hit_start"].tolist() == [0, 1], "hit-offset self-test differs")
    require(merged["event_job_index"].tolist() == [0, 52], "job-index self-test differs")
    require(np.all(merged["base_event_weight_cps"] == 0.5), "weight self-test differs")
    check_hit_layout(merged, "synthetic merged")
    merged67 = merge_arrays(
        old,
        [{
            "compact": new,
            "bins": np.asarray([79], dtype=np.uint8),
            "job": {"scan_index": 67},
        }],
        2.0,
    )
    require(merged67["event_job_index"].tolist() == [0, 67],
            "dynamic 67->68 job-index self-test differs")
    merged68 = merge_arrays(
        old,
        [{
            "compact": new,
            "bins": np.asarray([79], dtype=np.uint8),
            "job": {"scan_index": 68},
        }],
        2.0,
    )
    require(merged68["event_job_index"].tolist() == [0, 68],
            "dynamic 68->69 job-index self-test differs")
    fake_old = Path("/tmp/m05_merge_selftest_old")
    fake_archive = Path("/tmp/m05_merge_selftest_archive")
    fake_receipt = {
        "inputs": {
            "base_response": {
                "mode": "legacy_52_compact",
                "root": str(fake_old),
                "files": {
                    "summary.json": {
                        "path": str(fake_old / "summary.json"),
                        "bytes": 7,
                        "sha256": "a" * 64,
                    }
                },
                "result": {"jobs": 52},
            },
            "old_response_root": str(fake_old),
            "old_response_files": {
                "summary.json": {
                    "path": str(fake_old / "summary.json"),
                    "bytes": 7,
                    "sha256": "a" * 64,
                }
            },
            "old_auxiliary_job_cache_files": [{
                "path": str(fake_old / "job_catalogs/job_000.json"),
                "bytes": 11,
                "sha256": "b" * 64,
            }],
        }
    }
    relocated = relocated_promotion_receipt(fake_receipt, fake_old, fake_archive)
    require(
        relocated["inputs"]["old_response_root"] == str(fake_archive),
        "receipt-root relocation self-test differs",
    )
    require(
        relocated["inputs"]["old_response_files"]["summary.json"]["path"]
        == str(fake_archive / "summary.json"),
        "response-path relocation self-test differs",
    )
    require(
        relocated["inputs"]["base_response"]["root"] == str(fake_archive)
        and relocated["inputs"]["base_response"]["files"]["summary.json"]["path"]
        == str(fake_archive / "summary.json"),
        "base-response relocation self-test differs",
    )
    require(
        relocated["inputs"]["old_auxiliary_job_cache_files"][0]["path"]
        == str(fake_archive / "job_catalogs/job_000.json"),
        "cache-path relocation self-test differs",
    )
    require(
        fake_receipt["inputs"]["old_response_root"] == str(fake_old),
        "receipt relocation mutated its source",
    )
    require(
        relocated["inputs"]["old_response_files"]["summary.json"]["sha256"]
        == "a" * 64,
        "receipt relocation changed a frozen hash",
    )
    with tempfile.TemporaryDirectory(prefix="m05_promotion_rollback_selftest_") as text:
        transaction_root = Path(text)
        transaction_staging = transaction_root / "staging"
        transaction_canonical = transaction_root / "canonical"
        transaction_archive = transaction_root / "archive"
        transaction_backup = transaction_root / "receipt.backup"
        transaction_staging.mkdir()
        transaction_canonical.mkdir()
        original_receipt = b'{"original":true}\n'
        (transaction_staging / "MERGE_RECEIPT.json").write_bytes(original_receipt)
        (transaction_canonical / "old.marker").write_bytes(b"frozen old authority\n")
        expected_marker = sha256(transaction_canonical / "old.marker")
        write_exclusive_bytes(transaction_backup, original_receipt)
        os.replace(transaction_canonical, transaction_archive)
        os.replace(transaction_staging, transaction_canonical)
        (transaction_canonical / "MERGE_RECEIPT.json").write_bytes(
            b'{"relocated":true}\n'
        )
        rollback_promotion(
            staging=transaction_staging,
            canonical=transaction_canonical,
            archive=transaction_archive,
            receipt_backup=transaction_backup,
            original_receipt_sha256=hashlib.sha256(original_receipt).hexdigest(),
            old_was_moved=True,
            new_was_moved=True,
            expected_old_hashes={"old.marker": expected_marker},
        )
        require(
            (transaction_staging / "MERGE_RECEIPT.json").read_bytes()
            == original_receipt,
            "promotion rollback self-test did not restore the receipt",
        )
    require([BASE_JOBS + index for index in range(15)] == list(range(52, 67)),
            "top-up index self-test differs")
    _, promoted68_audit = load_merged_response(OLD_RESPONSE)
    require(promoted68_audit["mode"] == "promoted_68_compact",
            "current compact-prefix mode differs")
    require(int(promoted68_audit["jobs"]) == 68,
            "promoted-68 prefix job regression differs")
    require(int(promoted68_audit["incident_photons"]) == 15_655_124,
            "promoted-68 prefix incident regression differs")
    require(int(promoted68_audit["detector_positive_events"]) == 648_077,
            "promoted-68 prefix detector-positive regression differs")
    require(len(promoted68_audit["seeds"]) == 68,
            "promoted-68 prefix seed regression differs")
    promoted68_receipt = load_json(OLD_RESPONSE / "MERGE_RECEIPT.json")
    promoted67_root = Path(promoted68_receipt["inputs"]["old_response_root"])
    _, promoted67_audit = load_merged_response(
        promoted67_root, allow_historical_location=True
    )
    require(promoted67_audit["mode"] == "promoted_67_compact",
            "historical compact-prefix mode differs")
    require(int(promoted67_audit["jobs"]) == 67,
            "promoted-67 prefix job regression differs")
    require(int(promoted67_audit["incident_photons"]) == 15_618_529,
            "promoted-67 prefix incident regression differs")
    require(int(promoted67_audit["detector_positive_events"]) == 646_560,
            "promoted-67 prefix detector-positive regression differs")
    require(len(promoted67_audit["seeds"]) == 67,
            "promoted-67 prefix seed regression differs")
    promoted67_receipt = load_json(promoted67_root / "MERGE_RECEIPT.json")
    original_root = Path(promoted67_receipt["inputs"]["old_response_root"])
    _, original_audit = load_old_response(original_root)
    require(int(original_audit["jobs"]) == 52, "legacy-prefix job regression differs")
    require(int(original_audit["incident_photons"]) == 12_140_688,
            "legacy-prefix incident regression differs")
    payload = {
        "status": "PASS__B60_COMPACT_TOPUP_MERGE_SELF_TEST",
        "normalized_fragment": audit,
        "old_job_indices": [0, 51],
        "new_job_indices": [52, 66],
        "second_increment_job_index": 67,
        "third_increment_first_job_index": 68,
        "legacy_52_to_67_regression_reverified": True,
        "promoted_67_prefix_five_files_and_inputs_reverified": True,
        "promoted_68_prefix_five_files_and_inputs_reverified": True,
        "promotion_receipt_relocation_exercised": True,
        "promotion_failure_rollback_exercised": True,
        "transport_started": False,
        "formal_merge_started": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--old-response", type=Path, default=OLD_RESPONSE)
    build_parser.add_argument("--topup-root", type=Path, required=True)
    build_parser.add_argument("--cache-root", type=Path, required=True)
    build_parser.add_argument("--output", type=Path, required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--output", type=Path, required=True)
    validate_parser.add_argument("--skip-input-revalidation", action="store_true")
    promote_parser = subparsers.add_parser("promote")
    promote_parser.add_argument("--staging", type=Path, required=True)
    promote_parser.add_argument("--canonical", type=Path, required=True)
    promote_parser.add_argument("--archive", type=Path, required=True)
    subparsers.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "build":
        build(args.old_response, args.topup_root, args.cache_root, args.output)
    elif args.command == "validate":
        result = validate_output(args.output, verify_inputs=not args.skip_input_revalidation)
        print(json.dumps(result, indent=2, sort_keys=True))
    elif args.command == "promote":
        promote(args.staging, args.canonical, args.archive)
    else:
        self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
