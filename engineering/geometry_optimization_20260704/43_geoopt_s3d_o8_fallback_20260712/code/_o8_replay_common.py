#!/usr/bin/env python3
"""O8-bound facade over the audited 42_ replay helper implementation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
SHARED_PATH = (
    ROOT
    / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/"
    "_s3d_replay_common.py"
)


def _load_shared() -> Any:
    spec = importlib.util.spec_from_file_location("o8_shared_replay_common", SHARED_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load shared replay helper: {SHARED_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shared = _load_shared()
DATA = PACKAGE / "data"
S3D_GEOMETRY_DIR = PACKAGE / "geometry"
S3D_GEOMETRY_SETUP = (
    S3D_GEOMETRY_DIR / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
GEOMETRY_MANIFEST = DATA / "s3d_o8_geometry_manifest.json"
GEOMETRY_VALIDATION = DATA / "s3d_o8_independent_geometry_validation.json"
EXPECTED_GEOMETRY_STATUS = "S3D_O8_FALLBACK_GEOMETRY_VALIDATED_COSIMA_OVERLAP_PASS"

# Rebind every geometry-dependent shared global before forwarding helpers.
shared.PACKAGE = PACKAGE
shared.DATA = DATA
shared.S3D_GEOMETRY_DIR = S3D_GEOMETRY_DIR
shared.S3D_GEOMETRY_SETUP = S3D_GEOMETRY_SETUP
shared.GEOMETRY_MANIFEST = GEOMETRY_MANIFEST
shared.GEOMETRY_VALIDATION = GEOMETRY_VALIDATION

AuditError = shared.AuditError
rel = shared.rel
sha256 = shared.sha256
load_json = shared.load_json
safe_write_text = shared.safe_write_text
safe_write_json = shared.safe_write_json
geometry_hashes = shared.geometry_hashes
source_scalar = shared.source_scalar
source_run_name = shared.source_run_name
canonicalize_source = shared.canonicalize_source
existing_run_artifacts = shared.existing_run_artifacts
assert_no_production_artifacts = shared.assert_no_production_artifacts
sim_header = shared.sim_header
geometry_header_matches = shared.geometry_header_matches
cosima_environment = shared.cosima_environment
run_cosima = shared.run_cosima
selection_contract = shared.selection_contract
S3C_GEOMETRY_DIR = shared.S3C_GEOMETRY_DIR
S3C_GEOMETRY_SETUP = shared.S3C_GEOMETRY_SETUP
GEOMETRY_COMPONENTS = shared.GEOMETRY_COMPONENTS


def audit_geometry_authority() -> dict[str, Any]:
    if not GEOMETRY_MANIFEST.is_file() or not GEOMETRY_VALIDATION.is_file():
        raise AuditError("O8 geometry manifest or independent validation is missing")
    manifest = load_json(GEOMETRY_MANIFEST)
    validation = load_json(GEOMETRY_VALIDATION)
    checks = {
        "manifest_status": manifest.get("status"),
        "static_diff_status": manifest.get("static_diff_status"),
        "overlap_status": manifest.get("overlap_validation", {}).get("status"),
        "overlap_hash_match": manifest.get("overlap_validation", {}).get("hash_match"),
        "independent_validation_status": validation.get("status"),
        "generated_geometry_matches": (
            manifest.get("generated_geometry") == rel(S3D_GEOMETRY_SETUP)
        ),
    }
    passed = (
        checks["manifest_status"] == EXPECTED_GEOMETRY_STATUS
        and checks["static_diff_status"] == "PASS"
        and checks["overlap_status"] == "PASS"
        and checks["overlap_hash_match"] is True
        and checks["independent_validation_status"] == "PASS"
        and checks["generated_geometry_matches"]
    )
    if not passed:
        raise AuditError(f"O8 geometry authority is not transport-ready: {checks}")
    return {
        "status": "PASS",
        "checks": checks,
        "o8_geometry_hashes": geometry_hashes(S3D_GEOMETRY_DIR),
        "heavy_control_geometry_hashes": geometry_hashes(S3C_GEOMETRY_DIR),
        "shared_helper": rel(SHARED_PATH),
        "shared_helper_sha256": sha256(SHARED_PATH),
    }
