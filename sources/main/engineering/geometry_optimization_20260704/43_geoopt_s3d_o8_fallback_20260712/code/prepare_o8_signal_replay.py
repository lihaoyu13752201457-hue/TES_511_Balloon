#!/usr/bin/env python3
"""Prepare, execute, or audit the O8 matched focused-signal replay.

The completed heavy-control branch is reused as immutable authority.  Only the
new O8 branch can be launched, and its direct Cosima invocation is explicitly
seeded with ``-s 260616``.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from _o8_replay_common import (
    AuditError,
    DATA,
    ROOT,
    S3C_GEOMETRY_SETUP,
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


REFERENCE_RUN_NAME = "Opticsim_laue_f10m_a1_geo_opt_s1_bpe_w5_fullstat_v1_signal"
REFERENCE_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "step09_focus_geo_opt_s1_bpe_w5_fullstat_v1"
)
REFERENCE_SOURCE = REFERENCE_RUN_DIR / f"{REFERENCE_RUN_NAME}.source"
REFERENCE_TRANSPORT_MANIFEST = (
    ROOT
    / "engineering/geometry_optimization_20260704/03_step05_detector_response_20260706"
    / "signal_transport_manifest.json"
)
BRIDGE_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)
EVENTLIST = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists"
    / "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
)

C0_MANIFEST = (
    ROOT
    / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712"
    / "data/s3d_signal_replay_manifest.json"
)
C0_RUN_NAME = "Opticsim_laue_f10m_a1_s3c_c0_signal37194"
C0_RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3c_c0_f10m_a1_signal_replay_37194_matched_20260712"
)
C0_SOURCE = C0_RUN_DIR / f"{C0_RUN_NAME}.source"
C0_SIM = C0_RUN_DIR / f"{C0_RUN_NAME}.inc1.id1.sim.gz"

RUN_NAME = "Opticsim_laue_f10m_a1_s3d_o8_signal37194"
RUN_DIR = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o8_f10m_a1_signal_replay_37194_20260712"
)
SOURCE = RUN_DIR / f"{RUN_NAME}.source"
PREFIX = RUN_DIR / RUN_NAME
LOG = RUN_DIR / f"cosima_{RUN_NAME}.log"
SIM = RUN_DIR / f"{RUN_NAME}.inc1.id1.sim.gz"
MANIFEST = DATA / "s3d_o8_signal_replay_manifest.json"

TRIGGERS = 37_194
SEED = 260_616
SIGNAL_LOSS_LIMIT = 0.02
CONFIRMATION = "O8_MATCHED_SIGNAL37194_SEED260616"


def eventlist_audit() -> dict[str, Any]:
    if not EVENTLIST.is_file() or not C0_MANIFEST.is_file():
        raise AuditError("focused EventList or completed matched-control manifest is missing")
    count = 0
    first_id: int | None = None
    last_id: int | None = None
    sequential = True
    min_energy = float("inf")
    max_energy = float("-inf")
    columns: set[int] = set()
    with EVENTLIST.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split()
            if len(fields) < 2:
                raise AuditError(f"malformed EventList row {count + 1}")
            event_id = int(fields[0])
            energy = float(fields[-1])
            columns.add(len(fields))
            if first_id is None:
                first_id = event_id
            if event_id != count:
                sequential = False
            last_id = event_id
            min_energy = min(min_energy, energy)
            max_energy = max(max_energy, energy)
            count += 1
    digest = sha256(EVENTLIST)
    c0_manifest = json.loads(C0_MANIFEST.read_text(encoding="utf-8"))
    retained = (
        c0_manifest.get("reference_authority", {})
        .get("eventlist_audit", {})
        .get("sha256")
    )
    checks = {
        "rows": count,
        "first_id": first_id,
        "last_id": last_id,
        "zero_based_sequential_ids": sequential,
        "column_counts": sorted(columns),
        "energy_min_keV": min_energy,
        "energy_max_keV": max_energy,
        "sha256": digest,
        "completed_control_manifest_sha256": retained,
        "matches_completed_control_manifest": digest == retained,
    }
    passed = (
        count == TRIGGERS
        and first_id == 0
        and last_id == TRIGGERS - 1
        and sequential
        and min_energy == 511.0
        and max_energy == 511.0
        and digest == retained
    )
    if not passed:
        raise AuditError(f"focused EventList audit failed: {checks}")
    return {"status": "PASS", **checks}


def build_source() -> str:
    reference = REFERENCE_SOURCE.read_text(encoding="utf-8")
    if source_run_name(reference) != REFERENCE_RUN_NAME:
        raise AuditError("reference focused-signal run label changed")
    lines = reference.splitlines()
    if lines:
        lines[0] = "# Matched focused EventList replay through the O8 fallback geometry."
    text = "\n".join(lines) + "\n"
    text, n_geometry = re.subn(
        r"^Geometry\s+.*$",
        f"Geometry {rel(S3D_GEOMETRY_SETUP)}",
        text,
        count=1,
        flags=re.M,
    )
    text = text.replace(REFERENCE_RUN_NAME, RUN_NAME)
    text, n_prefix = re.subn(
        rf"^{re.escape(RUN_NAME)}\.FileName\s+.*$",
        f"{RUN_NAME}.FileName {rel(PREFIX)}",
        text,
        count=1,
        flags=re.M,
    )
    if n_geometry != 1 or n_prefix != 1:
        raise AuditError(
            f"unexpected O8 signal source patch counts: geometry={n_geometry}, prefix={n_prefix}"
        )
    return text


def source_audit(
    text: str,
    *,
    run_name: str,
    geometry: Path,
    prefix: Path,
    reference: str,
) -> dict[str, Any]:
    canonical = canonicalize_source(
        text,
        run_name=run_name,
        geometry=rel(geometry),
        output_prefix=rel(prefix),
    )
    ref_canonical = canonicalize_source(
        reference,
        run_name=REFERENCE_RUN_NAME,
        geometry=source_scalar(reference, "Geometry"),
        output_prefix=source_scalar(reference, f"{REFERENCE_RUN_NAME}.FileName"),
    )
    eventlist = source_scalar(text, f"{run_name}_EventList.EventList")
    checks = {
        "canonical_equal_to_reference": canonical == ref_canonical,
        "geometry": source_scalar(text, "Geometry"),
        "run_name": source_run_name(text),
        "seed": int(source_scalar(text, "Seed")),
        "triggers": int(source_scalar(text, f"{run_name}.Triggers")),
        "eventlist": eventlist,
        "eventlist_matches": eventlist == rel(EVENTLIST),
        "physics_em": source_scalar(text, "PhysicsListEM"),
        "physics_hd": source_scalar(text, "PhysicsListHD"),
        "discretize_hits": source_scalar(text, "DiscretizeHits"),
        "detector_time_constant": source_scalar(text, "DetectorTimeConstant"),
    }
    passed = (
        checks["canonical_equal_to_reference"]
        and checks["geometry"] == rel(geometry)
        and checks["run_name"] == run_name
        and checks["seed"] == SEED
        and checks["triggers"] == TRIGGERS
        and checks["eventlist_matches"]
        and checks["physics_em"] == "LivermorePol"
        and checks["physics_hd"] == "qgsp-bic-hp"
        and checks["discretize_hits"] == "true"
        and checks["detector_time_constant"] == "1e-9"
    )
    if not passed:
        raise AuditError(f"focused-signal source audit failed for {run_name}: {checks}")
    return {"status": "PASS", "checks": checks, "canonical": canonical}


def audit_control(*, count_events: bool) -> dict[str, Any]:
    if not C0_SOURCE.is_file() or not C0_SIM.is_file():
        raise AuditError("completed heavy-control focused-signal branch is missing")
    reference = REFERENCE_SOURCE.read_text(encoding="utf-8")
    text = C0_SOURCE.read_text(encoding="utf-8")
    prefix = C0_RUN_DIR / C0_RUN_NAME
    audit = source_audit(
        text,
        run_name=C0_RUN_NAME,
        geometry=S3C_GEOMETRY_SETUP,
        prefix=prefix,
        reference=reference,
    )
    header = sim_header(C0_SIM, count_events=count_events)
    checks = {
        "geometry_matches": geometry_header_matches(header.get("geometry"), S3C_GEOMETRY_SETUP),
        "seed_matches": header.get("seed") == SEED,
    }
    if count_events:
        checks.update(
            {
                "SE_matches": header.get("SE") == TRIGGERS,
                "ID_matches": header.get("ID") == TRIGGERS,
            }
        )
    if not all(checks.values()):
        raise AuditError(f"completed heavy-control signal audit failed: {header}, {checks}")
    return {
        "status": "PASS_REUSED_COMPLETED_CONTROL",
        "source": rel(C0_SOURCE),
        "source_sha256": sha256(C0_SOURCE),
        "sim": rel(C0_SIM),
        "sim_header": header,
        "checks": checks,
        "source_audit": {k: v for k, v in audit.items() if k != "canonical"},
        "canonical": audit["canonical"],
    }


def prepare() -> dict[str, Any]:
    for path in (REFERENCE_SOURCE, REFERENCE_TRANSPORT_MANIFEST, BRIDGE_SUMMARY):
        if not path.is_file():
            raise AuditError(f"missing focused-signal authority: {rel(path)}")
    geometry = audit_geometry_authority()
    _env, environment = cosima_environment()
    eventlist = eventlist_audit()
    reference = REFERENCE_SOURCE.read_text(encoding="utf-8")
    control = audit_control(count_events=False)
    text = build_source()
    o8_audit = source_audit(
        text,
        run_name=RUN_NAME,
        geometry=S3D_GEOMETRY_SETUP,
        prefix=PREFIX,
        reference=reference,
    )
    if o8_audit["canonical"] != control["canonical"]:
        raise AuditError("O8 and completed control signal sources differ beyond geometry/run/output")
    safe_write_text(SOURCE, text)
    artifacts = existing_run_artifacts(RUN_DIR, {SOURCE})
    header = sim_header(SIM)
    if header.get("exists"):
        if not geometry_header_matches(header.get("geometry"), S3D_GEOMETRY_SETUP):
            raise AuditError("existing O8 signal SIM points at the wrong geometry")
        if header.get("seed") != SEED:
            raise AuditError("existing O8 signal SIM has the wrong seed")
    payload = {
        "status": (
            "PASS_O8_SIGNAL_DRY_RUN_READY_NO_PRODUCTION_LAUNCHED"
            if not artifacts
            else "AUDIT_EXISTING_OUTPUTS_PRESENT_NO_OVERWRITE"
        ),
        "claim_boundary": (
            "Prepared matched detector transport only. The completed heavy-control branch is "
            "reused; no O8 acceptance result is claimed before full SIM audit and selection."
        ),
        "reference_authority": {
            "source": rel(REFERENCE_SOURCE),
            "source_sha256": sha256(REFERENCE_SOURCE),
            "transport_manifest": rel(REFERENCE_TRANSPORT_MANIFEST),
            "bridge_summary": rel(BRIDGE_SUMMARY),
            "eventlist": rel(EVENTLIST),
            "eventlist_audit": eventlist,
        },
        "matched_contract": {
            "triggers": TRIGGERS,
            "seed": SEED,
            "explicit_cosima_seed_argument": True,
            "canonical_sources_identical_except_geometry_run_output": True,
            "selection": selection_contract(),
        },
        "geometry_authority": geometry,
        "megalib_environment": environment,
        "branches": {
            "heavy_control": {k: v for k, v in control.items() if k != "canonical"},
            "o8": {
                "label": "O8 fallback",
                "run_name": RUN_NAME,
                "run_dir": rel(RUN_DIR),
                "geometry": rel(S3D_GEOMETRY_SETUP),
                "source": rel(SOURCE),
                "source_sha256": sha256(SOURCE),
                "sim": rel(SIM),
                "log": rel(LOG),
                "source_audit": {k: v for k, v in o8_audit.items() if k != "canonical"},
                "non_source_artifacts_in_run_dir": artifacts,
                "no_overwrite_ready": not artifacts,
                "sim_header": header,
            },
        },
        "execution": {
            "production_launched": False,
            "guarded_execute_command": (
                f"python3 {rel(Path(__file__))} --execute --confirm {CONFIRMATION}"
            ),
            "direct_cosima_command": (
                "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima "
                f"-s {SEED} {rel(SOURCE)}"
            ),
        },
        "result_contract": {
            "summary": rel(DATA / "s3d_o8_signal_replay_summary.json"),
            "required_observed_header_fields": ["geometry", "seed", "SE", "ID"],
            "promotion_metric": "1 - (O8 final W2 acceptance / heavy-control final W2 acceptance)",
            "promotion_limit_relative_loss": SIGNAL_LOSS_LIMIT,
            "gate_policy": "central matched acceptance loss <= 2%",
            "status": "PENDING_O8_TRANSPORT_NOT_ZERO",
        },
    }
    payload["manifest_write_state"] = safe_write_json(MANIFEST, payload)
    return payload


def audit_o8(*, count_events: bool = True) -> dict[str, Any]:
    header = sim_header(SIM, count_events=count_events)
    checks = {
        "geometry_matches": geometry_header_matches(header.get("geometry"), S3D_GEOMETRY_SETUP),
        "seed_matches": header.get("seed") == SEED,
    }
    if count_events:
        checks.update(
            {
                "SE_matches": header.get("SE") == TRIGGERS,
                "ID_matches": header.get("ID") == TRIGGERS,
            }
        )
    if not all(checks.values()):
        raise AuditError(f"O8 signal header/count audit failed: {header}, {checks}")
    return {"status": "PASS", "sim_header": header, "checks": checks}


def self_test() -> dict[str, Any]:
    eventlist = eventlist_audit()
    if TRIGGERS != 37_194 or SEED != 260_616 or SIGNAL_LOSS_LIMIT != 0.02:
        raise AuditError("internal signal contract changed")
    return {
        "status": "PASS_SELF_TEST",
        "eventlist_rows": eventlist["rows"],
        "eventlist_sha256": eventlist["sha256"],
        "signal_loss_limit": SIGNAL_LOSS_LIMIT,
        "production_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--audit-existing", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            print(json.dumps(self_test(), indent=2))
            return 0
        if args.audit_existing:
            audit_geometry_authority()
            eventlist_audit()
            print(
                json.dumps(
                    {
                        "status": "PASS_MATCHED_SIGNAL_HEADERS",
                        "manifest": rel(MANIFEST),
                        "heavy_control": audit_control(count_events=True),
                        "o8": audit_o8(count_events=True),
                    },
                    indent=2,
                )
            )
            return 0
        payload = prepare()
        if not args.execute:
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
        if args.confirm != CONFIRMATION:
            raise AuditError(f"--confirm must exactly equal {CONFIRMATION}")
        rc = run_cosima(
            source=SOURCE,
            log=LOG,
            run_dir=RUN_DIR,
            allowed_preexisting={SOURCE},
            seed=SEED,
        )
        if rc != 0:
            raise AuditError(f"Cosima returned {rc}; retained log: {rel(LOG)}")
        print(json.dumps({"status": "PASS_O8_SIGNAL_TRANSPORT_HEADER", **audit_o8()}, indent=2))
        return 0
    except (AuditError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
