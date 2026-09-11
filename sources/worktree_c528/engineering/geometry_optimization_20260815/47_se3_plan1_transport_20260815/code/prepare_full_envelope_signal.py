#!/usr/bin/env python3
"""Prepare the frozen full-envelope S3d-O8/SE3 focused-signal pair.

This is a static, fail-closed preparation step.  It validates the pinned
37,194-row post-Be EventList, deterministically back-projects only its position
columns to one instrument-frame plane, and writes byte-identical geometry-
specific EventLists plus their two Cosima source cards.  It never launches
transport and never discovers, opens, or hashes a SIM artifact.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable


SCRIPT = Path(__file__).resolve()
PACKAGE_ROOT = SCRIPT.parents[1]
CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
JOB_PLAN = PACKAGE_ROOT / "data/se3_plan1_job_plan.csv"
SEED_REGISTRY = PACKAGE_ROOT / "data/se3_plan1_seed_registry.csv"

EXPECTED_INPUT_SHA256 = "ee538d20d818baab94a5c3ebe01392a3ae9f278a231aa5b8938cdf23870f62b5"
EXPECTED_ROWS = 37_194
EXPECTED_FIELDS = 15
EXPECTED_ENERGY_KEV = 511.0
EXPECTED_POST_BE_XPRIME_CM = -13.1
INJECTION_XPRIME_CM = -30.0001
INSTRUMENT_ROTATION_Y_DEG = 45.0
POSITION_COLUMNS = (5, 6, 7)
NON_POSITION_COLUMNS = tuple(index for index in range(EXPECTED_FIELDS) if index not in POSITION_COLUMNS)
POSITION_RENDER_DIGITS = 15

PAIR_IDENTITY = "full_envelope_signal_pair_37194"
PAIR_JOBS = {
    "S3d_O8": "signal_full_envelope_s3d_o8",
    "SE3": "signal_full_envelope_se3",
}
EVENTLIST_OUTPUTS = {
    geometry: PACKAGE_ROOT / "config/signal_eventlists" / f"{job_id}.eventlist.dat"
    for geometry, job_id in PAIR_JOBS.items()
}
NAVIGATION_PLAN = PACKAGE_ROOT / "data/full_envelope_signal_navigation_plan.csv"
STATIC_AUDIT = PACKAGE_ROOT / "audit/full_envelope_signal_static_audit.json"


class PreparationError(RuntimeError):
    """Fail-closed static preparation error."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PreparationError(f"JSON object required: {path}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise PreparationError(f"CSV has no rows: {path}")
    return rows


def parse_bool(value: str, *, label: str) -> bool:
    normalized = value.strip().lower()
    if normalized not in {"true", "false"}:
        raise PreparationError(f"{label} is not a boolean: {value!r}")
    return normalized == "true"


def world_to_instrument(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    angle = math.radians(INSTRUMENT_ROTATION_Y_DEG)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    x, y, z = vector
    return cosine * x - sine * z, y, sine * x + cosine * z


def instrument_to_world(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    angle = math.radians(INSTRUMENT_ROTATION_Y_DEG)
    cosine = math.cos(angle)
    sine = math.sin(angle)
    x, y, z = vector
    return cosine * x + sine * z, y, -sine * x + cosine * z


def finite_fields(tokens: list[str], *, physical_line: int) -> list[float]:
    if len(tokens) != EXPECTED_FIELDS:
        raise PreparationError(
            f"EventList line {physical_line}: expected {EXPECTED_FIELDS} fields, got {len(tokens)}"
        )
    try:
        values = [float(token) for token in tokens]
    except ValueError as exc:
        raise PreparationError(f"EventList line {physical_line}: non-numeric field") from exc
    if not all(math.isfinite(value) for value in values):
        raise PreparationError(f"EventList line {physical_line}: non-finite field")
    return values


def render_position(value: float) -> str:
    return f"{value:.{POSITION_RENDER_DIGITS}e}"


def build_back_projected_bank(input_path: Path) -> tuple[bytes, dict[str, Any]]:
    input_bytes = input_path.read_bytes()
    input_sha = sha256_bytes(input_bytes)
    if input_sha != EXPECTED_INPUT_SHA256:
        raise PreparationError(
            f"frozen EventList SHA differs: {input_sha} != {EXPECTED_INPUT_SHA256}"
        )
    try:
        input_text = input_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PreparationError("frozen EventList is not UTF-8") from exc

    output_lines: list[str] = []
    data_rows = 0
    comments_or_blank = 0
    back_projection_distances: list[float] = []
    source_xprime: list[float] = []
    output_xprime: list[float] = []
    direction_xprime: list[float] = []
    direction_norms: list[float] = []
    changed_positions = 0

    for physical_line, raw in enumerate(input_text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            output_lines.append(raw)
            comments_or_blank += 1
            continue

        tokens = stripped.split()
        values = finite_fields(tokens, physical_line=physical_line)
        event_id_value = values[0]
        event_id = int(round(event_id_value))
        if not math.isclose(event_id_value, event_id, rel_tol=0.0, abs_tol=1e-12):
            raise PreparationError(f"EventList line {physical_line}: non-integral event ID")
        if event_id != data_rows:
            raise PreparationError(
                f"EventList line {physical_line}: event ID {event_id} != ordered row {data_rows}"
            )
        if values[14] != EXPECTED_ENERGY_KEV:
            raise PreparationError(
                f"EventList line {physical_line}: energy {values[14]} != {EXPECTED_ENERGY_KEV} keV"
            )

        position_world = (values[5], values[6], values[7])
        direction_world = (values[8], values[9], values[10])
        position_instrument = world_to_instrument(position_world)
        direction_instrument = world_to_instrument(direction_world)
        direction_norm = math.sqrt(math.fsum(component * component for component in direction_instrument))
        if not math.isclose(position_instrument[0], EXPECTED_POST_BE_XPRIME_CM, rel_tol=0.0, abs_tol=1e-7):
            raise PreparationError(
                f"EventList line {physical_line}: post-Be x'={position_instrument[0]:.12g} cm"
            )
        if direction_instrument[0] <= 0.999:
            raise PreparationError(
                f"EventList line {physical_line}: ray is not forward +x' ({direction_instrument[0]:.12g})"
            )
        if not math.isclose(direction_norm, 1.0, rel_tol=0.0, abs_tol=1e-8):
            raise PreparationError(
                f"EventList line {physical_line}: direction norm={direction_norm:.12g}"
            )

        scale = (INJECTION_XPRIME_CM - position_instrument[0]) / direction_instrument[0]
        if not scale < 0.0:
            raise PreparationError(f"EventList line {physical_line}: back-projection scale is not negative")
        projected_instrument = tuple(
            position_instrument[index] + scale * direction_instrument[index] for index in range(3)
        )
        if not math.isclose(projected_instrument[0], INJECTION_XPRIME_CM, rel_tol=0.0, abs_tol=2e-12):
            raise PreparationError(f"EventList line {physical_line}: in-memory injection plane closure failed")
        projected_world = instrument_to_world(projected_instrument)

        rendered = list(tokens)
        for index, value in zip(POSITION_COLUMNS, projected_world):
            rendered[index] = render_position(value)
        if any(rendered[index] != tokens[index] for index in POSITION_COLUMNS):
            changed_positions += 1
        if any(rendered[index] != tokens[index] for index in NON_POSITION_COLUMNS):
            raise AssertionError("non-position token changed during deterministic rendering")
        output_lines.append(" ".join(rendered))

        round_trip_world = tuple(float(rendered[index]) for index in POSITION_COLUMNS)
        round_trip_xprime = world_to_instrument(round_trip_world)[0]
        if not math.isclose(round_trip_xprime, INJECTION_XPRIME_CM, rel_tol=0.0, abs_tol=5e-12):
            raise PreparationError(
                f"EventList line {physical_line}: rendered x'={round_trip_xprime:.15g} cm"
            )

        source_xprime.append(position_instrument[0])
        output_xprime.append(round_trip_xprime)
        direction_xprime.append(direction_instrument[0])
        direction_norms.append(direction_norm)
        back_projection_distances.append(-scale * direction_norm)
        data_rows += 1

    if data_rows != EXPECTED_ROWS:
        raise PreparationError(f"frozen EventList rows={data_rows}, expected {EXPECTED_ROWS}")
    if changed_positions != EXPECTED_ROWS:
        raise PreparationError(f"not every ray position changed: {changed_positions}/{EXPECTED_ROWS}")

    output_text = "\n".join(output_lines) + "\n"
    output_bytes = output_text.encode("utf-8")
    verify_rendered_bank(input_text, output_text)
    summary = {
        "input_path": str(input_path),
        "input_bytes": len(input_bytes),
        "input_sha256": input_sha,
        "data_rows": data_rows,
        "comment_or_blank_rows": comments_or_blank,
        "field_count": EXPECTED_FIELDS,
        "first_id": 0,
        "last_id": data_rows - 1,
        "zero_based_sequential_ids": True,
        "energy_min_keV": EXPECTED_ENERGY_KEV,
        "energy_max_keV": EXPECTED_ENERGY_KEV,
        "source_xprime_cm": {
            "min": min(source_xprime),
            "max": max(source_xprime),
        },
        "injection_xprime_cm": {
            "target": INJECTION_XPRIME_CM,
            "min_after_render": min(output_xprime),
            "max_after_render": max(output_xprime),
        },
        "direction_xprime": {
            "min": min(direction_xprime),
            "max": max(direction_xprime),
        },
        "direction_norm": {
            "min": min(direction_norms),
            "max": max(direction_norms),
        },
        "back_projection_distance_cm": {
            "min": min(back_projection_distances),
            "max": max(back_projection_distances),
            "mean": math.fsum(back_projection_distances) / data_rows,
        },
        "changed_position_rows": changed_positions,
        "non_position_columns_preserved_verbatim": list(NON_POSITION_COLUMNS),
        "output_bytes": len(output_bytes),
        "output_sha256": sha256_bytes(output_bytes),
    }
    return output_bytes, summary


def data_tokens(text: str) -> Iterable[list[str]]:
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            yield stripped.split()


def verify_rendered_bank(input_text: str, output_text: str) -> None:
    input_rows = list(data_tokens(input_text))
    output_rows = list(data_tokens(output_text))
    if len(input_rows) != len(output_rows):
        raise PreparationError("rendered bank row count differs from frozen bank")
    for row_index, (source, target) in enumerate(zip(input_rows, output_rows)):
        if len(target) != EXPECTED_FIELDS:
            raise PreparationError(f"rendered row {row_index}: field count differs")
        if any(source[index] != target[index] for index in NON_POSITION_COLUMNS):
            raise PreparationError(f"rendered row {row_index}: non-position token changed")
        values = finite_fields(target, physical_line=row_index + 1)
        if int(round(values[0])) != row_index:
            raise PreparationError(f"rendered row {row_index}: ID/order changed")
        if values[14] != EXPECTED_ENERGY_KEV:
            raise PreparationError(f"rendered row {row_index}: energy changed")
        xprime = world_to_instrument((values[5], values[6], values[7]))[0]
        if not math.isclose(xprime, INJECTION_XPRIME_CM, rel_tol=0.0, abs_tol=5e-12):
            raise PreparationError(f"rendered row {row_index}: injection-plane closure failed")


def validate_configuration(config: dict[str, Any]) -> tuple[Path, Path]:
    signal = config.get("signal", {})
    source_path = Path(str(signal.get("eventlist", ""))).resolve()
    if not source_path.is_file():
        raise PreparationError(f"frozen EventList missing: {source_path}")
    if signal.get("eventlist_frozen_sha256") != EXPECTED_INPUT_SHA256:
        raise PreparationError("analysis_inputs frozen EventList SHA differs from pinned authority")
    if int(signal.get("eventlist_rows", -1)) != EXPECTED_ROWS:
        raise PreparationError("analysis_inputs EventList row contract differs")
    if not math.isclose(
        float(signal.get("injection_plane_xprime_cm", math.nan)),
        INJECTION_XPRIME_CM,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise PreparationError("analysis_inputs injection plane differs from -30.0001 cm")
    run_root = Path(str(config.get("run_root", ""))).resolve()
    if not run_root.is_absolute():
        raise PreparationError("run_root must be absolute")
    return source_path, run_root


def signal_plan_rows() -> tuple[list[dict[str, Any]], int]:
    rows = [row for row in read_csv(JOB_PLAN) if row.get("stage") == "signal"]
    if len(rows) != 2:
        raise PreparationError(f"job plan requires exactly two signal rows, got {len(rows)}")
    by_geometry = {row["geometry"]: row for row in rows}
    if set(by_geometry) != set(PAIR_JOBS):
        raise PreparationError(f"signal geometries differ: {sorted(by_geometry)}")

    seeds: set[int] = set()
    for geometry, expected_job_id in PAIR_JOBS.items():
        row = by_geometry[geometry]
        if row["job_id"] != expected_job_id:
            raise PreparationError(f"{geometry} signal job ID differs: {row['job_id']}")
        if int(row["events"]) != EXPECTED_ROWS:
            raise PreparationError(f"{geometry} signal events differ")
        if row["seed_identity"] != PAIR_IDENTITY:
            raise PreparationError(f"{geometry} signal seed identity differs")
        if not parse_bool(row["paired_seed_exception"], label=f"{geometry} paired_seed_exception"):
            raise PreparationError(f"{geometry} signal row is not registered as a paired exception")
        source = Path(row["source_path"]).resolve()
        expected_source = PACKAGE_ROOT / "config/signal_source_cards" / f"{expected_job_id}.source"
        if source != expected_source.resolve():
            raise PreparationError(f"{geometry} source path differs: {source}")
        setup = Path(row["setup_path"]).resolve()
        if not setup.is_file():
            raise PreparationError(f"{geometry} setup missing: {setup}")
        seeds.add(int(row["seed"]))
        row["seed_int"] = int(row["seed"])
        row["events_int"] = int(row["events"])
    if len(seeds) != 1:
        raise PreparationError(f"paired signal seeds differ: {sorted(seeds)}")
    shared_seed = next(iter(seeds))

    registry = {row["job_id"]: row for row in read_csv(SEED_REGISTRY)}
    for geometry, job_id in PAIR_JOBS.items():
        if job_id not in registry:
            raise PreparationError(f"seed registry lacks {job_id}")
        item = registry[job_id]
        if int(item["seed"]) != shared_seed or item["seed_identity"] != PAIR_IDENTITY:
            raise PreparationError(f"seed registry differs for {job_id}")
        if not parse_bool(item["paired_seed_exception"], label=f"{job_id} registry paired exception"):
            raise PreparationError(f"seed registry does not retain paired exception for {job_id}")
    return [by_geometry[geometry] for geometry in ("S3d_O8", "SE3")], shared_seed


def build_source(row: dict[str, Any], eventlist: Path, run_root: Path) -> str:
    job_id = str(row["job_id"])
    setup = Path(str(row["setup_path"])).resolve()
    seed = int(row["seed_int"])
    events = int(row["events_int"])
    prefix = run_root / "jobs" / job_id / "active" / job_id
    eventlist_source = f"{job_id}_EventList"
    text = "\n".join(
        [
            "# SE3 Plan-1 paired full-envelope focused-signal replay.",
            "# Position-only deterministic back-projection of the frozen 37,194-ray bank.",
            "# Static preparation authority; this source has not yet been transported.",
            "",
            "Version 1",
            f"Geometry {setup}",
            "PhysicsListEM LivermorePol",
            "PhysicsListHD qgsp-bic-hp",
            "StoreSimulationInfo all",
            "DiscretizeHits true",
            "DetectorTimeConstant 1e-9",
            f"Seed {seed}",
            "",
            f"Run {job_id}",
            f"{job_id}.FileName {prefix}",
            f"{job_id}.Triggers {events}",
            f"{job_id}.Source {eventlist_source}",
            "",
            f"{eventlist_source}.EventList {eventlist.resolve()}",
            "",
        ]
    )
    validate_source(text, row=row, eventlist=eventlist, prefix=prefix)
    return text


def validate_source(text: str, *, row: dict[str, Any], eventlist: Path, prefix: Path) -> None:
    job_id = str(row["job_id"])
    setup = Path(str(row["setup_path"])).resolve()
    seed = int(row["seed_int"])
    events = int(row["events_int"])
    eventlist_source = f"{job_id}_EventList"
    required = (
        f"Geometry {setup}",
        "PhysicsListEM LivermorePol",
        "PhysicsListHD qgsp-bic-hp",
        "StoreSimulationInfo all",
        "DiscretizeHits true",
        "DetectorTimeConstant 1e-9",
        f"Seed {seed}",
        f"Run {job_id}",
        f"{job_id}.FileName {prefix}",
        f"{job_id}.Triggers {events}",
        f"{job_id}.Source {eventlist_source}",
        f"{eventlist_source}.EventList {eventlist.resolve()}",
    )
    lines = text.splitlines()
    bad = {line: sum(item == line for item in lines) for line in required if sum(item == line for item in lines) != 1}
    if bad:
        raise PreparationError(f"signal source exact-line audit failed: {bad}")
    forbidden = ("Spectrum", "mono511", "mono_511", "DecayMode", "StoreIsotopes")
    if any(marker.lower() in text.lower() for marker in forbidden):
        raise PreparationError(f"signal source contains a forbidden atmospheric/activation marker: {job_id}")


def csv_bytes(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
    target = io.StringIO(newline="")
    writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return target.getvalue().encode("utf-8")


def write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise PreparationError(f"write-once output differs: {path}")
        return
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    try:
        with partial.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(partial, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise PreparationError(f"concurrent write-once output differs: {path}")
    finally:
        partial.unlink(missing_ok=True)


def prepare(*, write: bool) -> dict[str, Any]:
    config = load_json(CONFIG)
    frozen_eventlist, run_root = validate_configuration(config)
    rows, shared_seed = signal_plan_rows()
    bank_bytes, bank = build_back_projected_bank(frozen_eventlist)
    bank_sha = sha256_bytes(bank_bytes)

    source_payloads: dict[str, bytes] = {}
    navigation_rows: list[dict[str, Any]] = []
    job_records: list[dict[str, Any]] = []
    for row in rows:
        geometry = str(row["geometry"])
        job_id = str(row["job_id"])
        eventlist = EVENTLIST_OUTPUTS[geometry]
        source = Path(str(row["source_path"])).resolve()
        source_payload = build_source(row, eventlist, run_root).encode("utf-8")
        source_payloads[geometry] = source_payload
        expected_bpe = "POSITIVE_FULL_SHELL_CHORD" if geometry == "S3d_O8" else "ZERO_CHORD_THROUGH_FOCUSED_PORT"
        navigation_rows.append(
            {
                "job_id": job_id,
                "geometry": geometry,
                "setup_path": str(Path(row["setup_path"]).resolve()),
                "eventlist_path": str(eventlist.resolve()),
                "eventlist_sha256": bank_sha,
                "rows": EXPECTED_ROWS,
                "shared_seed": shared_seed,
                "injection_plane_xprime_cm": f"{INJECTION_XPRIME_CM:.4f}",
                "require_start_outside_geometry": "true",
                "require_forward_xprime": "true",
                "expected_bpe_path": expected_bpe,
                "expected_plastic_path": "POSITIVE_COMPLETE_SHELL_CHORD",
                "transport_gate": "NAVIGATOR_PASS_REQUIRED_BEFORE_LAUNCH",
            }
        )
        job_records.append(
            {
                "job_id": job_id,
                "geometry": geometry,
                "setup_path": str(Path(row["setup_path"]).resolve()),
                "events": EXPECTED_ROWS,
                "seed": shared_seed,
                "seed_identity": PAIR_IDENTITY,
                "paired_seed_exception": True,
                "eventlist_path": str(eventlist.resolve()),
                "eventlist_bytes": len(bank_bytes),
                "eventlist_sha256": bank_sha,
                "source_path": str(source),
                "source_bytes": len(source_payload),
                "source_sha256": sha256_bytes(source_payload),
                "output_prefix": str(run_root / "jobs" / job_id / "active" / job_id),
            }
        )

    navigation_fields = [
        "job_id",
        "geometry",
        "setup_path",
        "eventlist_path",
        "eventlist_sha256",
        "rows",
        "shared_seed",
        "injection_plane_xprime_cm",
        "require_start_outside_geometry",
        "require_forward_xprime",
        "expected_bpe_path",
        "expected_plastic_path",
        "transport_gate",
    ]
    navigation_payload = csv_bytes(navigation_rows, navigation_fields)
    audit = {
        "schema_version": 1,
        "status": "PASS__FULL_ENVELOPE_SIGNAL_STATIC_PREPARATION",
        "authority_boundary": "STATIC_AND_NAVIGATION_INPUTS_ONLY__NO_TRANSPORT_LAUNCHED",
        "algorithm": {
            "coordinate_frame": "InstrumentFrame",
            "instrument_rotation_y_deg": INSTRUMENT_ROTATION_Y_DEG,
            "source_plane_xprime_cm": EXPECTED_POST_BE_XPRIME_CM,
            "injection_plane_xprime_cm": INJECTION_XPRIME_CM,
            "operation": "p_injection = p_postBe + ((x_injection-p_xprime)/u_xprime)*u",
            "position_columns_changed": list(POSITION_COLUMNS),
            "all_other_columns_copied_verbatim": list(NON_POSITION_COLUMNS),
            "position_render_digits_after_decimal": POSITION_RENDER_DIGITS,
        },
        "frozen_bank": bank,
        "pair": {
            "shared_seed": shared_seed,
            "seed_identity": PAIR_IDENTITY,
            "jobs": job_records,
            "byte_identical_geometry_banks": True,
            "no_resampling_or_bootstrap": True,
            "ray_id_order_time_energy_direction_weight_preserved": True,
        },
        "navigation_plan": {
            "path": str(NAVIGATION_PLAN),
            "bytes": len(navigation_payload),
            "sha256": sha256_bytes(navigation_payload),
            "rows": len(navigation_rows),
            "status": "PENDING_NATIVE_NAVIGATOR__TRANSPORT_MUST_NOT_START",
        },
        "provenance_policy": "FROZEN_EVENTLIST_AND_SMALL_SOURCE_PLAN_AUDIT_ONLY__NO_SIM_DISCOVERY_OPEN_OR_HASH",
    }
    audit_payload = (json.dumps(audit, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")

    if write:
        for geometry in ("S3d_O8", "SE3"):
            write_once(EVENTLIST_OUTPUTS[geometry], bank_bytes)
        for row in rows:
            geometry = str(row["geometry"])
            write_once(Path(str(row["source_path"])).resolve(), source_payloads[geometry])
        write_once(NAVIGATION_PLAN, navigation_payload)
        write_once(STATIC_AUDIT, audit_payload)

        actual_eventlist_hashes = {geometry: sha256_file(path) for geometry, path in EVENTLIST_OUTPUTS.items()}
        if set(actual_eventlist_hashes.values()) != {bank_sha}:
            raise PreparationError(f"written paired EventLists differ: {actual_eventlist_hashes}")
        if sha256_file(NAVIGATION_PLAN) != sha256_bytes(navigation_payload):
            raise PreparationError("written navigation plan digest differs")
        if sha256_file(STATIC_AUDIT) != sha256_bytes(audit_payload):
            raise PreparationError("written static audit digest differs")
        for row in rows:
            geometry = str(row["geometry"])
            path = Path(str(row["source_path"])).resolve()
            if sha256_file(path) != sha256_bytes(source_payloads[geometry]):
                raise PreparationError(f"written source digest differs: {path}")

    return {
        "status": "PASS__FULL_ENVELOPE_SIGNAL_STATIC_OUTPUT_WRITTEN" if write else "PASS__DRY_RUN_ONLY",
        "input_eventlist": str(frozen_eventlist),
        "input_sha256": bank["input_sha256"],
        "rows": bank["data_rows"],
        "injection_plane_xprime_cm": INJECTION_XPRIME_CM,
        "shared_seed": shared_seed,
        "output_eventlist_sha256": bank_sha,
        "output_eventlists": {geometry: str(path) for geometry, path in EVENTLIST_OUTPUTS.items()},
        "sources": {str(row["geometry"]): str(Path(row["source_path"]).resolve()) for row in rows},
        "navigation_plan": str(NAVIGATION_PLAN),
        "static_audit": str(STATIC_AUDIT),
        "transport_launched": False,
        "sim_discovery_open_or_hash": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate and render in memory without writing")
    mode.add_argument("--write", action="store_true", help="publish write-once static preparation products")
    args = parser.parse_args()
    summary = prepare(write=args.write)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
