#!/usr/bin/env python3
"""Prepare/audit the matched 3M atmospheric-511 replay; execute only on confirmation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from _s3d_replay_common import (
    AuditError,
    DATA,
    ROOT,
    S3D_GEOMETRY_SETUP,
    audit_geometry_authority,
    canonicalize_source,
    cosima_environment,
    existing_run_artifacts,
    geometry_header_matches,
    rel,
    run_cosima,
    safe_write_json,
    safe_write_text,
    selection_contract,
    sha256,
    sim_header,
    source_run_name,
    source_scalar,
)


C0_RUN_NAME = "Atm511SidecarS3cBgoW2mmAl3mmShell3M"
C0_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3c_bgo_w2mm_al3mm_shell_atm511_sidecar_3m_20260709"
)
C0_SOURCE = C0_RUN_DIR / f"{C0_RUN_NAME}.source"
C0_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709"
    / "s3c_atm511_sidecar_3m_summary.json"
)

RUN_NAME = "Atm511SidecarS3dO9_3M"
RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o9_atm511_sidecar_3m_20260712"
)
SOURCE = RUN_DIR / f"{RUN_NAME}.source"
PREFIX = RUN_DIR / RUN_NAME
LOG = RUN_DIR / f"cosima_{RUN_NAME}.log"
SIM = RUN_DIR / f"{RUN_NAME}.inc1.id1.sim.gz"
MANIFEST = DATA / "s3d_atm511_replay_manifest.json"

EVENTS = 3_000_000
SEED = 26070917
SOURCE_COUNT = 20


def build_source() -> str:
    text = C0_SOURCE.read_text(encoding="utf-8")
    if source_run_name(text) != C0_RUN_NAME:
        raise AuditError("C0 atmospheric source run label changed")
    lines = text.splitlines()
    if lines:
        lines[0] = "# Matched C0 atmospheric-511 source replay through S3d O9 geometry."
    text = "\n".join(lines) + "\n"
    text, n_geometry = re.subn(
        r"^Geometry\s+.*$",
        f"Geometry {rel(S3D_GEOMETRY_SETUP)}",
        text,
        count=1,
        flags=re.M,
    )
    text = text.replace(C0_RUN_NAME, RUN_NAME)
    text, n_prefix = re.subn(
        rf"^{re.escape(RUN_NAME)}\.FileName\s+.*$",
        f"{RUN_NAME}.FileName {rel(PREFIX)}",
        text,
        count=1,
        flags=re.M,
    )
    if n_geometry != 1 or n_prefix != 1:
        raise AuditError(
            f"unexpected atmospheric source patch counts: geometry={n_geometry}, prefix={n_prefix}"
        )
    return text


def source_audit(text: str, reference: str) -> dict[str, Any]:
    new_canonical = canonicalize_source(
        text,
        run_name=RUN_NAME,
        geometry=rel(S3D_GEOMETRY_SETUP),
        output_prefix=rel(PREFIX),
    )
    ref_canonical = canonicalize_source(
        reference,
        run_name=C0_RUN_NAME,
        geometry=source_scalar(reference, "Geometry"),
        output_prefix=source_scalar(reference, f"{C0_RUN_NAME}.FileName"),
    )
    checks = {
        "canonical_transport_directives_identical_to_c0": new_canonical == ref_canonical,
        "geometry_is_s3d": source_scalar(text, "Geometry") == rel(S3D_GEOMETRY_SETUP),
        "seed": int(source_scalar(text, "Seed")),
        "events": int(source_scalar(text, f"{RUN_NAME}.Events")),
        "run_name": source_run_name(text),
        "source_bindings": len(
            re.findall(rf"^{re.escape(RUN_NAME)}\.Source\s+", text, flags=re.M)
        ),
        "far_field_bins": len(
            re.findall(r"^Atm511_bin\d\d_(?:up|down)\.Beam\s+FarFieldAreaSource\s+", text, flags=re.M)
        ),
        "mono_511_bins": len(
            re.findall(r"^Atm511_bin\d\d_(?:up|down)\.Spectrum\s+Mono\s+511\s*$", text, flags=re.M)
        ),
        "flux_bins": len(
            re.findall(r"^Atm511_bin\d\d_(?:up|down)\.Flux\s+", text, flags=re.M)
        ),
    }
    passed = (
        checks["canonical_transport_directives_identical_to_c0"]
        and checks["geometry_is_s3d"]
        and checks["seed"] == SEED
        and checks["events"] == EVENTS
        and checks["run_name"] == RUN_NAME
        and checks["source_bindings"] == SOURCE_COUNT
        and checks["far_field_bins"] == SOURCE_COUNT
        and checks["mono_511_bins"] == SOURCE_COUNT
        and checks["flux_bins"] == SOURCE_COUNT
    )
    if not passed:
        raise AuditError(f"atmospheric source audit failed: {checks}")
    return {"status": "PASS", "checks": checks}


def build_manifest(text: str, write_state: str) -> dict[str, Any]:
    geometry = audit_geometry_authority()
    env, env_evidence = cosima_environment()
    del env
    reference = C0_SOURCE.read_text(encoding="utf-8")
    source_checks = source_audit(text, reference)
    c0 = json.loads(C0_SUMMARY.read_text(encoding="utf-8"))
    preexisting = existing_run_artifacts(RUN_DIR, {SOURCE})
    header = sim_header(SIM)
    if header.get("exists"):
        if not geometry_header_matches(header.get("geometry"), S3D_GEOMETRY_SETUP):
            raise AuditError("existing atmospheric SIM header points at the wrong geometry")
        if header.get("seed") != SEED:
            raise AuditError("existing atmospheric SIM header has the wrong seed")
    model = c0["model"]
    environment = c0["environment"]
    return {
        "status": (
            "PASS_DRY_RUN_READY_NO_PRODUCTION_LAUNCHED"
            if not preexisting
            else "AUDIT_EXISTING_OUTPUTS_PRESENT_NO_OVERWRITE"
        ),
        "claim_boundary": (
            "Transport source and later selection are matched to S3c-C0. "
            "This manifest is not a transport result; atmospheric occupancy and window yields remain pending."
        ),
        "run": {
            "name": RUN_NAME,
            "directory": rel(RUN_DIR),
            "source": rel(SOURCE),
            "output_prefix": rel(PREFIX),
            "log": rel(LOG),
            "sim": rel(SIM),
            "events": EVENTS,
            "seed": SEED,
            "cosima_command": f"/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima -s {SEED} {rel(SOURCE)}",
            "guarded_execute_command": (
                f"python3 {rel(Path(__file__))} --execute --confirm {RUN_NAME}"
            ),
        },
        "source_authority": {
            "c0_source": rel(C0_SOURCE),
            "c0_source_sha256": sha256(C0_SOURCE),
            "prepared_source_sha256": sha256(SOURCE),
            "source_write_state": "PRESENT_IDENTICAL",
            "source_audit": source_checks,
        },
        "geometry_authority": geometry,
        "megalib_environment": env_evidence,
        "source_model_frozen_from_c0": {
            "source_model": model["source_model"],
            "scenario": "S1 nominal physical ATM511 source, transported through S3d O9 geometry",
            "phi_ref_ph_cm2_s": model["phi_ref_ph_cm2_s"],
            "X_ref_g_cm2": model["X_ref_g_cm2"],
            "eta": model["eta"],
            "r0": model["r0"],
            "beta": model["beta"],
            "Lambda_511_g_cm2": model["Lambda_511_g_cm2"],
            "albedo_limb_darkening_a": model["albedo_limb_darkening_a"],
            "phi_4pi_ph_cm2_s": model["phi_4pi_ph_cm2_s"],
            "phi_up_ph_cm2_s": model["phi_up_ph_cm2_s"],
            "phi_down_ph_cm2_s": model["phi_down_ph_cm2_s"],
            "Rc_GV": environment["Rc_GV"],
            "depth_g_cm2": environment["depth_g_cm2"],
            "day_mid": environment["day_mid"],
        },
        "selection_contract": selection_contract(),
        "result_contract": {
            "summary": rel(DATA / "s3d_atm511_replay_summary.json"),
            "required_catalog_fields": [
                "generated_events",
                "kept_events_tes_or_active",
                "detector_catalog_event_rate_cps",
                "observation_time_s",
            ],
            "required_window_fields": (
                "W2 and broad raw/active-veto/final event counts and rates"
            ),
            "accidental_occupancy_status": "PENDING_TRANSPORT_NOT_ZERO",
        },
        "dry_run": {
            "production_launched": False,
            "non_source_artifacts_in_run_dir": preexisting,
            "no_overwrite_ready": not preexisting,
            "sim_header": header,
        },
        "resource_estimate_from_c0": {
            "cpu_seconds": 1152.0,
            "wall_time_guidance": "about 20 minutes on one comparable CPU core",
            "compressed_sim_bytes": 806542758,
            "log_bytes": 310685512,
            "minimum_free_disk_guidance_gb": 2.0,
        },
    }


def prepare() -> dict[str, Any]:
    audit_geometry_authority()
    if not C0_SOURCE.is_file() or not C0_SUMMARY.is_file():
        raise AuditError("retained C0 atmospheric source/summary is missing")
    text = build_source()
    source_audit(text, C0_SOURCE.read_text(encoding="utf-8"))
    safe_write_text(SOURCE, text)
    payload = build_manifest(text, "PRESENT_IDENTICAL")
    manifest_state = safe_write_json(MANIFEST, payload)
    return {**payload, "manifest_write_state": manifest_state}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="launch the full 3M transport")
    parser.add_argument("--confirm", default="", help="must exactly match the run name")
    parser.add_argument("--audit-existing", action="store_true", help="scan an existing SIM header")
    args = parser.parse_args()
    try:
        if args.audit_existing:
            audit_geometry_authority()
            header = sim_header(SIM, count_events=True)
            checks = {
                "geometry_matches": geometry_header_matches(
                    header.get("geometry"), S3D_GEOMETRY_SETUP
                ),
                "seed_matches": header.get("seed") == SEED,
                "SE_matches": header.get("SE") == EVENTS,
                "ID_matches": header.get("ID") == EVENTS,
            }
            if not all(checks.values()):
                raise AuditError(
                    f"existing atmospheric SIM header/count audit failed: {header}, {checks}"
                )
            print(json.dumps({"manifest": rel(MANIFEST), "sim_header": header}, indent=2))
            return 0
        payload = prepare()
        if args.execute:
            if args.confirm != RUN_NAME:
                raise AuditError(f"--confirm must exactly equal {RUN_NAME}")
            rc = run_cosima(
                source=SOURCE,
                log=LOG,
                run_dir=RUN_DIR,
                allowed_preexisting={SOURCE},
                seed=SEED,
            )
            if rc != 0:
                raise AuditError(f"Cosima failed with return code {rc}; log retained at {rel(LOG)}")
            header = sim_header(SIM, count_events=True)
            if not geometry_header_matches(header.get("geometry"), S3D_GEOMETRY_SETUP):
                raise AuditError("completed atmospheric SIM header points at the wrong geometry")
            if header.get("seed") != SEED or header.get("SE") != EVENTS:
                raise AuditError(f"completed atmospheric SIM count/seed audit failed: {header}")
            print(json.dumps({"status": "PASS_TRANSPORT_HEADER", "sim_header": header}, indent=2))
            return 0
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "manifest": rel(MANIFEST),
                    "source": rel(SOURCE),
                    "production_launched": False,
                },
                indent=2,
            )
        )
        return 0
    except AuditError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
