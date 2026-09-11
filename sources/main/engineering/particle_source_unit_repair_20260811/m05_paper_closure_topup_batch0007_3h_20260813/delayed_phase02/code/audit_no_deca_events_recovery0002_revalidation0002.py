#!/usr/bin/env python3
"""Strengthened append-only audit of recovery0002 no-DECA events.

This audit is downstream of the PASS revalidation0001 authority.  It requires
IA-DECA event coverage >=99.9% independently in each of the six cells and
streams the six immutable SIM artifacts again to classify every event without
an IA DECA record.  Those denominator events must be epsilon-INIT-only:

* one IA INIT and no other IA line;
* EC=0 and NS=0, with either ED=0 and zero raw hits, or ED=1e-6 keV
  with exactly one primary-ionization CC HIT of 1e-6 keV and one HTsim;
* no non-primary interaction and no future-decay interaction;
* therefore no true deposit at or above the paper's 0.3 keV measured-hit
  threshold and no physical route to W2 from these epsilon deposits.

The paper response order is explicitly preserved: 420 eV FWHM smearing occurs
before the measured-hit <0.3 keV discard.  This audit therefore does not claim
that a particular stochastic measured realization has zero retained hits; that
realization belongs to the response reader.

No old attempt, receipt, SIM, source, or revalidation is moved or modified.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parents[5]
RECOVERY_ROOT = (
    ROOT
    / "runs/particle_source_unit_repair_20260811"
    / "m05_paper_closure_topup_batch0007_3h_v1"
    / "delayed_phase02/state_aware_exactpos_v1"
    / "spectrum_epsilon_formal_partial_recovery0002"
)
INPUT = RECOVERY_ROOT / "revalidation0001/formal_partial_revalidation.json"
OUTPUT = RECOVERY_ROOT / "revalidation0002/no_deca_epsilon_subthreshold_true_deposit_audit.json"

EXPECTED_JOBS = 6
EXPECTED_EVENTS = 250_000
EPSILON_KEV = 1.0e-6
DECA_COVERAGE_MIN = 0.999
M05_MEASURED_HIT_THRESHOLD_KEV = 0.3
EDEP_RE = re.compile(r"\bedep_keV=([-+0-9.eE]+)")
SEC_RE = re.compile(r"\bsec=(\S+)")
CPROC_RE = re.compile(r"\bcproc=(\S+)")
SPROC_RE = re.compile(r"\bsproc=(\S+)")
PID_RE = re.compile(r"\bpid=(\d+)")
EXPECTED_NO_DECA_ISOTOPES = {55120, 71162, 71165, 75172, 81188}
EXPECTED_NO_DECA_ISOTOPE_LABELS = {
    55120: "Cs-120",
    71162: "Lu-162",
    71165: "Lu-165",
    75172: "Re-172",
    81188: "Tl-188",
}
EXPECTED_ZERO_HIT_NO_DECA = 106
EXPECTED_EPSILON_HIT_NO_DECA = 169


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json_once(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"write-once target exists: {path}")
    partial = path.with_name(f".{path.name}.partial.{os.getpid()}")
    with partial.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)


def stat_binding(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": rel(path),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "inode": stat.st_ino,
    }


def fresh_event() -> dict[str, Any]:
    return {
        "id": None,
        "ED": None,
        "EC": None,
        "NS": None,
        "init_count": 0,
        "init_ZA": None,
        "deca_count": 0,
        "other_IA_count": 0,
        "cc_count": 0,
        "cc_edep_sum_keV": 0.0,
        "cc_edep_max_keV": 0.0,
        "cc_volumes": [],
        "cc_secondaries": [],
        "cc_creation_processes": [],
        "cc_step_processes": [],
        "cc_parent_ids": [],
        "htsim_count": 0,
        "htsim_energy_values_keV": [],
    }


def scan(path: Path, expected_no_deca: int) -> dict[str, Any]:
    before = stat_binding(path)
    events = 0
    events_with_deca = 0
    no_deca: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def finish() -> None:
        nonlocal events, events_with_deca, current
        if current is None:
            return
        events += 1
        if current["deca_count"] > 0:
            events_with_deca += 1
        else:
            no_deca.append(current)
        current = None

    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            for raw in handle:
                stripped = raw.strip()
                if stripped == "SE":
                    finish()
                    current = fresh_event()
                    continue
                if stripped == "EN":
                    finish()
                    continue
                if current is None or not stripped:
                    continue
                fields = stripped.split()
                tag = fields[0]
                if tag == "ID" and len(fields) >= 3:
                    current["id"] = int(fields[1])
                elif tag == "ED" and len(fields) >= 2:
                    current["ED"] = float(fields[1])
                elif tag == "EC" and len(fields) >= 2:
                    current["EC"] = float(fields[1])
                elif tag == "NS" and len(fields) >= 2:
                    # MEGAlib SIM permits a floating-point NS value; only the
                    # audited INIT-only subset is required to have NS=0.
                    current["NS"] = float(fields[1])
                elif stripped.startswith("IA INIT"):
                    current["init_count"] += 1
                    pieces = stripped.split(";")
                    if len(pieces) > 15:
                        current["init_ZA"] = int(pieces[15].strip())
                elif stripped.startswith("IA DECA"):
                    current["deca_count"] += 1
                elif stripped.startswith("IA "):
                    current["other_IA_count"] += 1
                elif stripped.startswith("CC HIT "):
                    current["cc_count"] += 1
                    if len(fields) >= 3:
                        current["cc_volumes"].append(fields[2])
                    edep_match = EDEP_RE.search(stripped)
                    if edep_match:
                        value = float(edep_match.group(1))
                        current["cc_edep_sum_keV"] += value
                        current["cc_edep_max_keV"] = max(current["cc_edep_max_keV"], value)
                    sec_match = SEC_RE.search(stripped)
                    if sec_match:
                        current["cc_secondaries"].append(sec_match.group(1))
                    cproc_match = CPROC_RE.search(stripped)
                    if cproc_match:
                        current["cc_creation_processes"].append(cproc_match.group(1))
                    sproc_match = SPROC_RE.search(stripped)
                    if sproc_match:
                        current["cc_step_processes"].append(sproc_match.group(1))
                    pid_match = PID_RE.search(stripped)
                    if pid_match:
                        current["cc_parent_ids"].append(int(pid_match.group(1)))
                elif stripped.startswith("HTsim "):
                    current["htsim_count"] += 1
                    pieces = stripped.split(";")
                    if len(pieces) >= 5:
                        current["htsim_energy_values_keV"].append(float(pieces[4].strip()))
        finish()
    except (OSError, EOFError, ValueError) as exc:
        return {
            "status": "FAIL",
            "problem": f"gzip_or_parse_error:{exc}",
            "path": rel(path),
            "gzip_eof_reached": False,
        }

    after = stat_binding(path)
    stable = before == after
    actual_no_deca = len(no_deca)
    coverage = events_with_deca / events if events else 0.0
    zero_hit = [
        row for row in no_deca
        if row["ED"] == 0.0 and row["cc_count"] == 0 and row["htsim_count"] == 0
    ]
    epsilon_hit = [
        row for row in no_deca
        if row["ED"] is not None
        and math.isclose(row["ED"], EPSILON_KEV, rel_tol=0.0, abs_tol=1.0e-12)
        and row["cc_count"] == 1
        and math.isclose(row["cc_edep_sum_keV"], EPSILON_KEV, rel_tol=0.0, abs_tol=1.0e-12)
        and row["htsim_count"] == 1
        and row["htsim_energy_values_keV"] == [0.0]
    ]
    criteria = {
        "event_count_250000": events == EXPECTED_EVENTS,
        "matches_revalidation0001_no_DECA_count": actual_no_deca == expected_no_deca,
        "DECA_coverage_at_least_99p9_percent": coverage >= DECA_COVERAGE_MIN,
        "all_no_DECA_have_one_INIT": all(row["init_count"] == 1 for row in no_deca),
        "all_no_DECA_have_zero_nonINIT_IA": all(row["other_IA_count"] == 0 for row in no_deca),
        "all_no_DECA_ED_is_zero_or_epsilon_keV": all(
            row["ED"] is not None and (
                row["ED"] == 0.0
                or math.isclose(row["ED"], EPSILON_KEV, rel_tol=0.0, abs_tol=1.0e-12)
            )
            for row in no_deca
        ),
        "all_no_DECA_EC_zero": all(row["EC"] == 0.0 for row in no_deca),
        "all_no_DECA_NS_zero": all(row["NS"] == 0 for row in no_deca),
        "all_no_DECA_match_zero_hit_or_epsilon_primary_hit_class": (
            len(zero_hit) + len(epsilon_hit) == actual_no_deca
        ),
        "all_no_DECA_CC_hits_are_primary_ionization": all(
            all(value == "primary" for value in row["cc_creation_processes"])
            and all(value == "ionIoni" for value in row["cc_step_processes"])
            and all(value == 0 for value in row["cc_parent_ids"])
            for row in no_deca
        ),
        "all_no_DECA_true_CC_deposits_below_0p3keV": all(
            row["cc_edep_max_keV"] < M05_MEASURED_HIT_THRESHOLD_KEV for row in no_deca
        ),
        "all_no_DECA_HTsim_is_absent_or_printed_zero": all(
            row["htsim_energy_values_keV"] in ([], [0.0]) for row in no_deca
        ),
        "artifact_stable_during_full_scan": stable,
        "gzip_EOF_reached": True,
    }
    volumes = Counter(volume for row in no_deca for volume in row["cc_volumes"])
    secondaries = Counter(sec for row in no_deca for sec in row["cc_secondaries"])
    isotopes = Counter(row["init_ZA"] for row in no_deca)
    problems = [key for key, value in criteria.items() if not value]
    return {
        "status": "PASS" if not problems else "FAIL",
        "problem": None if not problems else ";".join(problems),
        "path": rel(path),
        "path_binding_before": before,
        "path_binding_after": after,
        "gzip_eof_reached": True,
        "events": events,
        "events_with_IA_DECA": events_with_deca,
        "events_without_IA_DECA": actual_no_deca,
        "expected_events_without_IA_DECA_from_revalidation0001": expected_no_deca,
        "IA_DECA_event_coverage_fraction": coverage,
        "IA_DECA_coverage_minimum_required": DECA_COVERAGE_MIN,
        "no_DECA_event_fraction": actual_no_deca / events if events else None,
        "no_DECA_event_ids": [row["id"] for row in no_deca],
        "no_DECA_ED_unique_keV": sorted({row["ED"] for row in no_deca}),
        "no_DECA_EC_unique_keV": sorted({row["EC"] for row in no_deca}),
        "no_DECA_NS_unique": sorted({row["NS"] for row in no_deca}),
        "no_DECA_CC_count_unique": sorted({row["cc_count"] for row in no_deca}),
        "no_DECA_CC_edep_sum_unique_keV": sorted({row["cc_edep_sum_keV"] for row in no_deca}),
        "no_DECA_CC_edep_max_keV": max((row["cc_edep_max_keV"] for row in no_deca), default=None),
        "no_DECA_HTsim_count_unique": sorted({row["htsim_count"] for row in no_deca}),
        "no_DECA_HTsim_energy_unique_keV": sorted({value for row in no_deca for value in row["htsim_energy_values_keV"]}),
        "no_DECA_CC_volume_counts": dict(sorted(volumes.items())),
        "no_DECA_secondary_counts": dict(sorted(secondaries.items())),
        "no_DECA_initial_isotope_ZA_counts": {
            str(key): value for key, value in sorted(isotopes.items())
        },
        "no_DECA_zero_hit_event_count": len(zero_hit),
        "no_DECA_epsilon_primary_ionization_hit_event_count": len(epsilon_hit),
        "M05_measured_hit_threshold_keV_after_smearing": M05_MEASURED_HIT_THRESHOLD_KEV,
        "no_DECA_true_deposits_at_or_above_0p3keV": (
            0 if criteria["all_no_DECA_true_CC_deposits_below_0p3keV"] else None
        ),
        "no_DECA_recorded_true_deposit_can_form_W2": False,
        "measured_hit_realization": (
            "NOT_EVALUATED_HERE__APPLY_420EV_FWHM_SMEAR_THEN_MEASURED_LT_0P3KEV_DISCARD_"
            "IN_RESPONSE_READER"
        ),
        "classification": "INIT_ONLY_ZERO_OR_EPSILON_PRIMARY_IONIZATION__SUBTHRESHOLD_TRUE_DEPOSIT",
        "criteria": criteria,
    }


def authority() -> dict[str, Any]:
    if not INPUT.is_file():
        raise RuntimeError(f"missing revalidation0001 PASS authority: {INPUT}")
    payload = load_json(INPUT)
    if payload.get("status") != "PASS__REVALIDATION0001_SIX_CELL_DELAYED_PARTIAL_SCREENING_COMPATIBLE":
        raise RuntimeError(f"revalidation0001 is not PASS: {payload.get('status')}")
    if len(payload.get("jobs", [])) != EXPECTED_JOBS:
        raise RuntimeError("revalidation0001 does not contain six jobs")
    return payload


def run() -> dict[str, Any]:
    if OUTPUT.exists():
        raise FileExistsError(f"write-once audit exists: {OUTPUT}")
    input_payload = authority()
    rows = input_payload["jobs"]
    # The six gzip streams are independent and immutable.  Audit them in six
    # processes so this strengthened read-only pass does not delay handoff.
    with ProcessPoolExecutor(max_workers=EXPECTED_JOBS) as executor:
        futures = [
            executor.submit(
                scan,
                ROOT / row["valid_artifact_path"],
                int(row["sim_revalidation"]["events_without_IA_DECA"]),
            )
            for row in rows
        ]
        results = [future.result() for future in futures]
    jobs = [
        {
            "status": result["status"],
            "job_id": row["job_id"],
            "geometry": row["geometry"],
            "family": row["family"],
            "artifact_state": row["artifact_state"],
            "valid_artifact_path": row["valid_artifact_path"],
            "revalidation0001_job_status": row["status"],
            "no_DECA_audit": result,
        }
        for row, result in zip(rows, results)
    ]
    total_events = sum(row["no_DECA_audit"].get("events", 0) for row in jobs)
    total_deca = sum(row["no_DECA_audit"].get("events_with_IA_DECA", 0) for row in jobs)
    total_no_deca = sum(row["no_DECA_audit"].get("events_without_IA_DECA", 0) for row in jobs)
    total_zero_hit = sum(row["no_DECA_audit"].get("no_DECA_zero_hit_event_count", 0) for row in jobs)
    total_epsilon_hit = sum(
        row["no_DECA_audit"].get("no_DECA_epsilon_primary_ionization_hit_event_count", 0)
        for row in jobs
    )
    aggregate_isotopes: Counter[int] = Counter()
    for row in jobs:
        aggregate_isotopes.update({
            int(key): int(value)
            for key, value in row["no_DECA_audit"].get("no_DECA_initial_isotope_ZA_counts", {}).items()
        })
    aggregate_crosscheck = {
        "total_no_DECA_is_275": total_no_deca == 275,
        "zero_hit_class_is_106": total_zero_hit == EXPECTED_ZERO_HIT_NO_DECA,
        "epsilon_primary_ionization_class_is_169": total_epsilon_hit == EXPECTED_EPSILON_HIT_NO_DECA,
        "class_counts_sum_to_total_no_DECA": total_zero_hit + total_epsilon_hit == total_no_deca,
        "initial_isotope_ZA_set_matches_independent_audit": set(aggregate_isotopes) == EXPECTED_NO_DECA_ISOTOPES,
    }
    passed = (
        len(jobs) == EXPECTED_JOBS
        and all(row["status"] == "PASS" for row in jobs)
        and all(aggregate_crosscheck.values())
    )
    payload = {
        "schema_version": 1,
        "status": (
            "PASS__REVALIDATION0002_DECA_99P9_CURRENT_RDM_ZERO_SECONDARY_EDGE_DOCUMENTED"
            if passed else "FAIL__REVALIDATION0002"
        ),
        "created_utc": now_utc(),
        "controller": rel(THIS_FILE),
        "controller_sha256": sha256(THIS_FILE),
        "input_authority": rel(INPUT),
        "input_authority_sha256": sha256(INPUT),
        "input_authority_status": input_payload["status"],
        "jobs": jobs,
        "passed_jobs": sum(row["status"] == "PASS" for row in jobs),
        "expected_jobs": EXPECTED_JOBS,
        "DECA_coverage_minimum_per_job": DECA_COVERAGE_MIN,
        "total_events": total_events,
        "total_events_with_IA_DECA": total_deca,
        "total_events_without_IA_DECA": total_no_deca,
        "aggregate_IA_DECA_coverage_fraction": total_deca / total_events if total_events else None,
        "aggregate_no_DECA_fraction": total_no_deca / total_events if total_events else None,
        "total_no_DECA_zero_hit_events": total_zero_hit,
        "total_no_DECA_epsilon_primary_ionization_hit_events": total_epsilon_hit,
        "aggregate_no_DECA_initial_isotope_ZA_counts": {
            str(key): value for key, value in sorted(aggregate_isotopes.items())
        },
        "aggregate_crosscheck": aggregate_crosscheck,
        "no_DECA_classification": {
            "allowed_raw_ED_keV": [0.0, EPSILON_KEV],
            "EC_keV": 0.0,
            "NS": 0,
            "zero_hit_events": EXPECTED_ZERO_HIT_NO_DECA,
            "epsilon_primary_ionization_hit_events": EXPECTED_EPSILON_HIT_NO_DECA,
            "epsilon_primary_ionization_CC_HIT_edep_keV": EPSILON_KEV,
            "allowed_initial_isotope_ZA": sorted(EXPECTED_NO_DECA_ISOTOPES),
            "allowed_initial_isotope_labels": [
                EXPECTED_NO_DECA_ISOTOPE_LABELS[value]
                for value in sorted(EXPECTED_NO_DECA_ISOTOPES)
            ],
            "nonprimary_interactions": 0,
            "future_decay_interactions": 0,
            "M05_measured_hit_threshold_keV_after_420eV_FWHM_smearing": (
                M05_MEASURED_HIT_THRESHOLD_KEV
            ),
            "true_deposits_at_or_above_0p3keV": 0,
            "recorded_true_deposit_can_form_W2": False,
            "measured_hit_realization": (
                "NOT_EVALUATED_HERE__MUST_BE_HANDLED_BY_RESPONSE_READER_IN_PAPER_ORDER"
            ),
            "model_edge_classification": "CURRENT_RDM_ZERO_SECONDARY_MODEL_EDGE",
            "trigger_level_model_edge_fraction": total_no_deca / total_events if total_events else None,
            "trigger_level_model_edge_percent": (
                100.0 * total_no_deca / total_events if total_events else None
            ),
            "interpretation": (
                "Recorded current-RDM realizations contain only the deliberately injected epsilon "
                "kinetic energy and no true deposit at or above 0.3 keV. They are complete SIM "
                "events, but must not be interpreted as established physical zero-response events. "
                "Actual measured hits are stochastic after 420 eV FWHM smearing and are handled "
                "by the response reader."
            ),
            "physics_caveat": (
                "The INIT-only subset is confined to Cs-120, Lu-162, Lu-165, Re-172, and Tl-188 "
                "and is classified as a current installed-Geant4 radioactive-decay-model edge. "
                "Independent event audit identified zero-generated-secondary cases including "
                "pseudo-ground-state isomeric-transition and below-pair-threshold beta-plus edges; "
                "MCSteppingAction consequently records no IA DECA. The resulting 275/1,500,000 "
                "(0.01833%) trigger-level modeling caveat remains in the denominator, but cannot "
                "be used as physical zero response or as support for a final paper rate."
            ),
        },
        "old_attempts_receipts_SIM_sources_or_revalidation0001_modified": False,
        "coverage_status": "STRENGTHENED_PARTIAL_SCREENING__P_N_ALPHA_ONLY__TWO_GEOMETRIES",
        "transport_analysis_compatibility_supported": passed,
        "partial_screening_supported": passed,
        "final_delayed_physical_rate_supported": False,
        "paper_closure_claimed": False,
        "authority_boundary": (
            "CORRECTED_EPSILON_DELAYED_PARTIAL_SCREENING_AND_SUBTHRESHOLD_TRUE_DEPOSIT_DENOMINATOR_AUDIT_ONLY__"
            "NO_FULL_DELAYED_RESPONSE_MISSION_SENSITIVITY_PAPER_CLOSURE_OR_GEOMETRY_PROMOTION"
        ),
        "output": rel(OUTPUT),
    }
    atomic_json_once(OUTPUT, payload)
    if not passed:
        raise RuntimeError(f"strengthened no-DECA audit failed; see {OUTPUT}")
    return payload


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="no_deca_audit_selftest_") as value:
        temp = Path(value)
        sim = temp / "synthetic.sim.gz"
        with gzip.open(sim, "wt", encoding="utf-8") as handle:
            for index in range(1, 2001):
                handle.write(f"SE\nID {index} {index}\n")
                if index == 1999:
                    handle.write(
                        "ED 0\nEC 0\nNS 0\n"
                        "IA INIT 1;0;0;0;0;0;0;0;0;0;0;0;0;0;0;55120;0;0;0;0;0;0;0.000\n"
                    )
                else:
                    handle.write(
                        "ED 1e-06\nEC 0\nNS 0\n"
                        "CC HIT V edep_keV=1.000000e-06 sproc=ionIoni sec=Cs120 pid=0 cproc=primary\n"
                        "IA INIT 1;0;0;0;0;0;0;0;0;0;0;0;0;0;0;55120;0;0;0;0;0;0;0.000\n"
                        "HTsim 4;0;0;0;0.00000;0;1\n"
                    )
                if index <= 1998:
                    handle.write("IA DECA 2;1;4;0.0\n")
            handle.write("EN\n")
        old_expected = globals()["EXPECTED_EVENTS"]
        try:
            globals()["EXPECTED_EVENTS"] = 2000
            result = scan(sim, 2)
        finally:
            globals()["EXPECTED_EVENTS"] = old_expected
        assert result["status"] == "PASS"
        assert result["events_without_IA_DECA"] == 2
        assert result["IA_DECA_event_coverage_fraction"] == 0.999
        assert result["no_DECA_true_deposits_at_or_above_0p3keV"] == 0
        assert result["no_DECA_zero_hit_event_count"] == 1
        assert result["no_DECA_epsilon_primary_ionization_hit_event_count"] == 1
    return {
        "status": "PASS__REVALIDATION0002_STATIC_SELF_TEST",
        "tests": 13,
        "synthetic_events": 2000,
        "synthetic_DECA_coverage": 0.999,
        "synthetic_no_DECA_epsilon_subthreshold_true_deposit": True,
        "transport_launched": False,
        "campaign_files_written": False,
    }


def print_plan() -> dict[str, Any]:
    return {
        "status": "READY_TO_AUDIT" if INPUT.is_file() and not OUTPUT.exists() else (
            "AUDIT_EXISTS" if OUTPUT.exists() else "WAITING_FOR_REVALIDATION0001_PASS"
        ),
        "controller": rel(THIS_FILE),
        "input": rel(INPUT),
        "output": rel(OUTPUT),
        "jobs": EXPECTED_JOBS,
        "DECA_coverage_minimum_per_job": DECA_COVERAGE_MIN,
        "no_DECA_event_gate": "epsilon_INIT_only_and_no_true_deposit_at_or_above_0p3keV",
        "mode": "read_only_full_gzip_stream_append_only_report",
        "transport_launched": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--print-plan", action="store_true")
    actions.add_argument("--self-test", action="store_true")
    actions.add_argument("--run", action="store_true")
    args = parser.parse_args()
    payload = print_plan() if args.print_plan else (self_test() if args.self_test else run())
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
