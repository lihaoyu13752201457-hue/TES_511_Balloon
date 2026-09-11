#!/usr/bin/env python3
"""Strict reconciliation of one-row-per-AddIsotope activation sidecars to native DAT."""

from __future__ import annotations

import csv
import math
import re
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from geometry_classification import classification_index, validate_geometry_classification
from preflight_common import PACKAGE, strict_json
from tape_contract import SIDECAR_COLUMNS


RECORD_SCHEMA_PATH = PACKAGE / "schema/m05cc_v2.record_schema.json"
_RECORD_SCHEMA = strict_json(RECORD_SCHEMA_PATH)
_TABLES = _RECORD_SCHEMA["x-tsv-tables"]
REQUIRED_ACTIVATION_FIELDS = tuple(_TABLES["activation"]["header"])
REQUIRED_ROOT_FIELDS = tuple(_TABLES["roots"]["header"])
REQUIRED_FOOTER_FIELDS = tuple(_TABLES["footer"]["header"])
FAMILY_PRIMARY_PARTICLE = {
    "gamma": "gamma", "n": "neutron", "eplus": "e+", "eminus": "e-", "alpha": "alpha",
    "muminus": "mu-", "muplus": "mu+",
}


def parse_dat(path: Path) -> tuple[float, Counter[tuple[str, int, str]]]:
    tt: float | None = None
    volume: str | None = None
    totals: Counter[tuple[str, int, str]] = Counter()
    en_count = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if fields[0] == "TT":
            if tt is not None or len(fields) != 2:
                raise ValueError("DAT must have exactly one TT")
            tt = float(fields[1])
        elif fields[0] == "VN":
            if len(fields) != 2:
                raise ValueError("malformed VN")
            volume = fields[1]
        elif fields[0] == "RP":
            if len(fields) != 4 or volume is None:
                raise ValueError("malformed/orphan RP")
            value = float(fields[3])
            if not value >= 0.0 or not value.is_integer():
                raise ValueError("native RP count is not a nonnegative integer")
            totals[(volume, int(fields[1]), f"{float(fields[2]):.2f}")] += int(value)
        elif fields[0] == "EN":
            en_count += 1
        else:
            raise ValueError(f"unknown DAT record {fields[0]}")
    if tt is None or not math.isfinite(tt) or tt <= 0.0 or en_count != 1:
        raise ValueError("DAT TT/EN closure failed")
    return tt, totals


def parse_tape_roots(path: Path) -> dict[int, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != SIDECAR_COLUMNS:
            raise ValueError("frozen tape-root sidecar schema mismatch")
        rows = list(reader)
    by_event: dict[int, dict[str, str]] = {}
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if (
            int(row["row_index0"]) != index - 1
            or int(row["eventlist_id"]) != index
            or row["driver_assignment"] != "sampled_exact_not_inferred"
            or row["family"] not in FAMILY_PRIMARY_PARTICLE
            or re.fullmatch(r"[0-9a-f]{64}", row["stable_root_id"]) is None
            or row["stable_root_id"] in seen
        ):
            raise ValueError("frozen tape-root order/identity closure failed")
        by_event[index] = row
        seen.add(row["stable_root_id"])
    if not rows:
        raise ValueError("frozen tape-root sidecar is empty")
    return by_event


def parse_roots(
    path: Path, tape_by_event: dict[int, dict[str, str]]
) -> tuple[list[dict[str, str]], dict[int, dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != REQUIRED_ROOT_FIELDS:
            raise ValueError("root sidecar schema mismatch")
        rows = list(reader)
    by_event: dict[int, dict[str, str]] = {}
    seen_roots: set[str] = set()
    for index, row in enumerate(rows, start=1):
        event = int(row["simulation_event_id"])
        if event != index or int(row["row_index0"]) != index - 1 or int(row["eventlist_id"]) != index:
            raise ValueError("root sidecar event/row/EventList order mismatch")
        if event in by_event or row["stable_root_id"] in seen_roots:
            raise ValueError("duplicate root event or stable root ID")
        digests = (
            row["stable_root_id"], row["raw_tape_line_sha256"], row["expected_generated_tuple_sha256"],
            row["observed_generated_tuple_sha256"], row["observed_ia_init_tuple_sha256"],
        )
        if any(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in digests):
            raise ValueError("invalid root digest")
        if row["expected_generated_tuple_sha256"] != row["observed_generated_tuple_sha256"]:
            raise ValueError("root expected/observed generated tuple hash mismatch")
        if (
            not row["benchmark_driver_id"]
            or row["family"] not in FAMILY_PRIMARY_PARTICLE
            or row["driver_inference_quality"] not in {"exact", "rounded_unique", "rounded_ambiguous", "unavailable"}
            or row["driver_inference_ambiguity_set"] != "[]"
            or row["control_flag"] not in {"0", "1"}
            or row["generated_flag"] != "1"
            or row["started_flag"] != "1"
            or row["native_event_populated"] != "1"
            or row["completed_flag"] != "1"
            or row["aborted_flag"] != "0"
        ):
            raise ValueError("invalid root driver/family/control provenance")
        tape = tape_by_event.get(event)
        if tape is None or any((
            row["stable_root_id"] != tape["stable_root_id"],
            row["benchmark_driver_id"] != tape["driver"],
            row["family"] != tape["family"],
            row["raw_tape_line_sha256"] != tape["raw_eventlist_line_sha256"],
            row["expected_generated_tuple_sha256"] != tape["expected_generated_tuple_sha256"],
            row["control_flag"] != tape["control_flag"],
        )):
            raise ValueError("runtime root does not join exactly to frozen tape root")
        by_event[event] = row
        seen_roots.add(row["stable_root_id"])
    if not rows:
        raise ValueError("root sidecar is empty")
    return rows, by_event


def parse_activation(
    path: Path,
    roots_by_event: dict[int, dict[str, str]],
    *,
    geometry: str,
    geometry_classification: dict[str, Any],
) -> tuple[list[dict[str, str]], Counter[tuple[str, int, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != REQUIRED_ACTIVATION_FIELDS:
            raise ValueError("activation sidecar schema mismatch")
        rows = list(reader)
    totals: Counter[tuple[str, int, str]] = Counter()
    volume_index = classification_index(geometry_classification, geometry)
    for index, row in enumerate(rows, start=1):
        if int(row["production_serial"]) != index:
            raise ValueError("production serial gap/duplicate/out-of-order")
        if re.fullmatch(r"[0-9a-f]{64}", row["stable_root_id"]) is None:
            raise ValueError("invalid stable root ID")
        event = int(row["simulation_event_id"])
        if event not in roots_by_event:
            raise ValueError("RP event has no root-sidecar row")
        root = roots_by_event[event]
        if (
            row["stable_root_id"] != root["stable_root_id"]
            or int(row["eventlist_id"]) != int(root["eventlist_id"])
            or row["driver"] != root["benchmark_driver_id"]
            or row["family"] != root["family"]
        ):
            raise ValueError("RP event/root/EventList/driver/family join mismatch")
        if any(not row[field] for field in (
            "driver", "family", "native_dat_volume", "physical_volume", "logical_volume",
            "touchable_copy_path", "material", "particle", "primary_particle", "step_process", "ancestry_chain",
        )):
            raise ValueError("RP row lacks required lineage/volume/material field")
        za = int(row["za"])
        z = int(row["z"])
        a = int(row["a"])
        if z <= 0 or z > 118 or a <= 0 or a > 400 or a < z or za != 1000*z + a:
            raise ValueError("ZA != 1000*Z+A")
        excitation = float(row["excitation_keV"])
        expected_bits = f"{struct.unpack('>Q', struct.pack('>d', excitation))[0]:016x}"
        if re.fullmatch(r"[0-9a-f]{16}", row["excitation_f64_bits"]) is None or (
            row["excitation_f64_bits"] != expected_bits
        ):
            raise ValueError("excitation IEEE-754 bits do not match excitation_keV")
        for field in ("root_weight", "excitation_keV", "production_x_cm", "production_y_cm", "production_z_cm", "production_time_s"):
            if not math.isfinite(float(row[field])):
                raise ValueError(f"non-finite activation field {field}")
        if float(row["root_weight"]) != 1.0:
            raise ValueError("analog smoke root weight must equal one")
        if excitation < 0.0:
            raise ValueError("negative RP excitation state")
        if len(row["logical_volume"]) < 3 or row["logical_volume"][:-3] != row["native_dat_volume"]:
            raise ValueError("native DAT volume is not the exact logical-name-minus-three contract")
        if float(row["production_time_s"]) < 0.0:
            raise ValueError("negative RP production time")
        track = int(row["track_id"])
        parent = int(row["parent_track_id"])
        primary = int(row["primary_track_id"])
        try:
            chain = [tuple(int(value) for value in edge.split(":")) for edge in row["ancestry_chain"].split(",")]
        except (TypeError, ValueError) as exc:
            raise ValueError("malformed RP ancestry edge chain") from exc
        tids = [edge[0] for edge in chain if len(edge) == 2]
        if (
            track <= 0 or parent < 0 or primary <= 0 or not chain or any(len(edge) != 2 for edge in chain)
            or len(tids) != len(set(tids)) or chain[0] != (primary, 0) or chain[-1][0] != track
            or chain[-1][1] != parent
            or any(child_pid != parent_tid for (parent_tid, _), (_, child_pid) in zip(chain, chain[1:]))
        ):
            raise ValueError("RP ancestry/track chain mismatch")
        if row["primary_particle"] != FAMILY_PRIMARY_PARTICLE[row["family"]]:
            raise ValueError("RP primary particle does not match frozen family")
        classification = volume_index.get(row["physical_volume"])
        if classification is None:
            raise ValueError("RP physical volume is absent from canonical geometry classification")
        touchable_level0 = row["touchable_copy_path"].split("/", 1)[0]
        expected_level0 = (
            f"{classification['physical_volume']}:{classification['runtime_logical_volume']}:"
            f"{classification['copy_number']}"
        )
        if (
            row["logical_volume"] != classification["runtime_logical_volume"]
            or row["native_dat_volume"] != classification["native_dat_volume"]
            or row["material"] != classification["material"]
            or touchable_level0 != expected_level0
        ):
            raise ValueError("RP physical/logical/touchable/material/native-DAT geometry join mismatch")
        totals[(row["native_dat_volume"], za, f"{float(row['excitation_keV']):.2f}")] += 1
    return rows, totals


def reconcile(
    activation_path: Path,
    dat_path: Path,
    footer_path: Path,
    roots_path: Path,
    tape_roots_path: Path,
    *,
    geometry: str,
    geometry_classification: dict[str, Any],
    verify_geometry_authority: bool = True,
) -> dict[str, Any]:
    geometry_check = validate_geometry_classification(
        geometry_classification, verify_canonical_authority=verify_geometry_authority
    )
    tape_by_event = parse_tape_roots(tape_roots_path)
    root_rows, roots_by_event = parse_roots(roots_path, tape_by_event)
    rows, sidecar_totals = parse_activation(
        activation_path,
        roots_by_event,
        geometry=geometry,
        geometry_classification=geometry_classification,
    )
    tt, dat_totals = parse_dat(dat_path)
    if sidecar_totals != dat_totals:
        raise ValueError(f"RP aggregate mismatch: sidecar={sidecar_totals}, DAT={dat_totals}")
    with footer_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if tuple(reader.fieldnames or ()) != REQUIRED_FOOTER_FIELDS:
            raise ValueError("footer schema mismatch")
        footer_rows = list(reader)
    if len(footer_rows) != 1:
        raise ValueError("footer must contain exactly one job row")
    footer = footer_rows[0]
    tape_families = {row["family"] for row in tape_by_event.values()}
    tape_modes = {row["mode"] for row in tape_by_event.values()}
    if (
        footer["arm"] != "C"
        or footer["geometry"] != geometry
        or tape_families != {footer["family"]}
        or tape_modes != {footer["mode"]}
    ):
        raise ValueError("RP reconciliation requires compact C arm")
    count_fields = (
        "tape_count", "generated_count", "started_count", "completed_count", "native_populated_count",
        "root_count", "ia_init_count", "native_observed_simulation_event_id_count",
        "native_observed_event_id_count",
    )
    if any(int(footer[field]) != len(root_rows) for field in count_fields) or len(tape_by_event) != len(root_rows):
        raise ValueError("footer lifecycle/native/IA/SE/ID/root counts differ from tape length")
    if int(footer["aborted_count"]) != 0 or int(footer["rp_row_count"]) != len(rows):
        raise ValueError("footer aborted/RP count closure failed")
    if not math.isclose(float(footer["TT_s"]), tt, rel_tol=0.0, abs_tol=5.0e-6):
        raise ValueError("footer TT differs from serialized native DAT TT")
    if (
        footer["active_block_coverage"] != "geometry_specific"
        or re.fullmatch(r"[0-9a-f]{64}", footer["veto_whitelist_sha256"]) is None
        or re.fullmatch(r"[0-9a-f]{64}", footer["record_schema_sha256"]) is None
        or footer["finalized"] != "1"
    ):
        raise ValueError("job did not finalize")
    return {
        "status": "PASS",
        "rp_row_count": len(rows),
        "TT_s": tt,
        "aggregate_key_count": len(dat_totals),
        "zero_rp_positive_tt": not rows and tt > 0.0,
        "native_commit_evidence": (
            "runtime production_serial/count is one callback per committed AddIsotope; native DAT provides only "
            "aggregate (volume,ZA,displayed-2dp-state) reconciliation, never native row-by-row identity"
        ),
        "geometry_classification_join": "PASS",
        "geometry_classification_authority_rebuilt": geometry_check["canonical_authority_rebuilt"],
    }
