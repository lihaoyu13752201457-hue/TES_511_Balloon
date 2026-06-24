#!/usr/bin/env python3
"""Build exact-position weighted delayed source v2 from G1/G2 authorities."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any, Iterable


getcontext().prec = 80

PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "04_custom_source_v2"
BY_TAG_DIR = OUT / "source_v2_native_activity_store_by_tag"

INVENTORY = PHASE_DIR / "01_raw_inventory/raw_inventory_all_states.csv"
JOIN = PHASE_DIR / "02_rpip_alignment/dat_rpip_key_join.csv"
POINTS = PHASE_DIR / "02_rpip_alignment/rpip_points_all.csv"
SEMANTICS = PHASE_DIR / "03_source_semantics/source_semantics_verdict.json"
GEOMETRY = (
    ROOT
    / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)

EVENTLIST = OUT / "source_v2_eventlist.dat"
WEIGHTS = OUT / "source_v2_event_weights.csv"
SOURCE_CARD = OUT / "source_v2_eventlist.source"
NATIVE_TOTAL = OUT / "source_v2_native_activity_store_total.dat"
KEY_CLOSURE = OUT / "source_v2_key_closure.csv"
MANIFEST = OUT / "source_v2_manifest.json"
ROUNDTRIP = OUT / "source_text_roundtrip.json"
NAME_AUDIT = OUT / "source_name_audit.json"
SAMPLING_AUDIT = OUT / "sampling_audit.json"
SYNTHETIC_TESTS = OUT / "synthetic_tests.json"
SUMMARY_JSON = OUT / "summary.json"
SUMMARY_MD = OUT / "summary.md"

RUN_NAME = "DelayedSourceV2"
SOURCE_NAME = "DelayedSourceV2_EventList"
DETECTOR_TIME_CONSTANT_S = "1e-9"


@dataclass(frozen=True)
class Key:
    production_tag: str
    raw_volume: str
    za: str
    exc_keV: str


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def dec(text: str | Decimal | None) -> Decimal:
    if isinstance(text, Decimal):
        return text
    if text is None or text == "":
        return Decimal(0)
    return Decimal(str(text))


def fmt_dec(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def key_from_row(row: dict[str, str]) -> Key:
    return Key(row["production_tag"], row["raw_volume"], row["ZA"], str(dec(row["exc_keV_decimal"])))


def key_string(key: Key) -> str:
    return "|".join([key.production_tag, key.raw_volume, key.za, key.exc_keV])


def stable_hash(text: str, n: int = 16) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def safe_token(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_]+", "_", text)
    return text.strip("_") or "x"


def state_token(exc_keV: str) -> str:
    d = dec(exc_keV)
    if d == 0:
        return "gs"
    return "ex" + safe_token(fmt_dec(d).replace(".", "p").replace("-", "m"))


def make_source_name(key: Key, point_index: int) -> str:
    tag = safe_token(key.production_tag)
    volume_hash = stable_hash(key.raw_volume)
    return f"RP2_{tag}_{volume_hash}_{key.za}_{state_token(key.exc_keV)}_{point_index:06d}"


def source_name_tests() -> dict[str, Any]:
    key_a = Key("gamma", "raw.volume/a", "11022", "0")
    key_b = Key("gamma", "raw.volume.b", "11022", "0")
    key_c = Key("gamma", "raw.volume/a", "11022", "12")
    names = {
        make_source_name(key_a, 0),
        make_source_name(key_a, 1),
        make_source_name(key_b, 0),
        make_source_name(key_c, 0),
    }
    return {
        "status": "PASS" if len(names) == 4 else "FAIL",
        "duplicate_source_name_test": len(names) == 4,
        "raw_volume_collision_test": make_source_name(key_a, 0) != make_source_name(key_b, 0),
        "excitation_collision_test": make_source_name(key_a, 0) != make_source_name(key_c, 0),
    }


def load_positive_inventory() -> dict[Key, dict[str, Any]]:
    inv_rows = read_csv(INVENTORY)
    join_rows = read_csv(JOIN)
    inv_by_key: dict[Key, dict[str, str]] = {key_from_row(row): row for row in inv_rows}
    positive: dict[Key, dict[str, Any]] = {}
    for row in join_rows:
        key = key_from_row(row)
        activity = dec(row["activity_day15_direct_Bq"])
        if activity <= 0:
            continue
        if row["status"] != "PASS":
            raise RuntimeError(f"non-PASS RPIP key in positive inventory: {key_string(key)}")
        inv = inv_by_key.get(key, {})
        positive[key] = {
            "production_tag": key.production_tag,
            "raw_volume": key.raw_volume,
            "canonical_volume_for_reporting_only": row["canonical_volume_for_reporting_only"],
            "ZA": key.za,
            "nuclide": row["nuclide"],
            "exc_keV_decimal": key.exc_keV,
            "state_id": inv.get("state_id", state_token(key.exc_keV)),
            "state_class": row["state_class"],
            "activity_Bq": activity,
            "rpip_count": int(row["rpip_count"]),
            "dat_production_count_raw": int(row["dat_production_count_raw"]),
            "source_files_count": int(row["source_files_count"]),
        }
    return positive


def load_points_for_keys(keys: set[Key]) -> dict[Key, list[dict[str, str]]]:
    grouped: dict[Key, list[dict[str, str]]] = defaultdict(list)
    with POINTS.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = key_from_row(row)
            if key in keys:
                grouped[key].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda r: (r["source_file"], int(r["line_no"])))
    return grouped


def excitation_is_exact_position_supported(exc_keV: str) -> bool:
    # File EventList excitation is parsed as an integer without a visible keV
    # scale. Treat non-ground states as unsupported for exact-position custom
    # authority until a dedicated nonzero-state microtest establishes units.
    return dec(exc_keV) == 0


def write_eventlist_source(event_count: int) -> None:
    text = f"""# Auto-generated delayed-source v2 exact-position EventList.
# Activity normalization lives in {rel(WEIGHTS)}.

Version 1
Geometry {rel(GEOMETRY)}
PhysicsListEM LivermorePol
PhysicsListRadioactiveDecay true
DecayMode ActivationDelayedDecay
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant {DETECTOR_TIME_CONSTANT_S}

Run {RUN_NAME}
{RUN_NAME}.FileName {rel(OUT / "source_v2_transport")}
{RUN_NAME}.Triggers {event_count}
{RUN_NAME}.Source {SOURCE_NAME}

{SOURCE_NAME}.EventList {rel(EVENTLIST)}
"""
    SOURCE_CARD.write_text(text, encoding="utf-8")


def write_native_store(path: Path, rows: list[tuple[str, str, str, Decimal]]) -> None:
    by_volume: dict[str, dict[tuple[str, str], Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for volume, za, exc, activity in rows:
        by_volume[volume][(za, exc)] += activity
    lines = [
        "# Cosima universal isotope store",
        "# VN is followed by the volume name in which the isotope was produced",
        "# RP is followed by isotope ID (1000*Z+A), excitation in keV, and activity in Bq",
        "",
        "TT 0",
        "",
    ]
    for volume in sorted(by_volume):
        lines.append(f"VN {volume}")
        for (za, exc), activity in sorted(by_volume[volume].items(), key=lambda kv: (int(kv[0][0]), dec(kv[0][1]))):
            lines.append(f"RP {za}   {fmt_dec(dec(exc))}   {fmt_dec(activity)}")
    lines.extend(["", "EN", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_weight_ledger(path: Path) -> tuple[dict[Key, Decimal], Decimal, int]:
    sums: dict[Key, Decimal] = defaultdict(Decimal)
    total = Decimal(0)
    count = 0
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = Key(row["production_tag"], row["raw_volume"], row["ZA"], str(dec(row["exc_keV_decimal"])))
            weight = dec(row["event_weight_Bq"])
            sums[key] += weight
            total += weight
            count += 1
    return sums, total, count


def parse_eventlist(path: Path) -> dict[str, Any]:
    count = 0
    bad_token_rows = 0
    first_ids: list[int] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) != 15:
                bad_token_rows += 1
                continue
            if count < 5:
                first_ids.append(int(parts[0]))
            count += 1
    return {"row_count": count, "bad_token_rows": bad_token_rows, "first_ids": first_ids}


def parse_native_store_total(path: Path) -> Decimal:
    total = Decimal(0)
    with path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 4 and parts[0] == "RP":
                total += dec(parts[3])
    return total


def relative_delta(a: Decimal, b: Decimal) -> Decimal:
    if b == 0:
        return Decimal(0) if a == 0 else Decimal("Infinity")
    return abs(a - b) / abs(b)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    BY_TAG_DIR.mkdir(parents=True, exist_ok=True)
    semantics = json.loads(SEMANTICS.read_text(encoding="utf-8"))
    if semantics.get("status") != "PASS":
        raise RuntimeError("WP03 source semantics must pass before WP04")

    tests = source_name_tests()
    positive = load_positive_inventory()
    points = load_points_for_keys(set(positive))

    unsupported_activity = Decimal(0)
    unsupported_keys: list[str] = []
    for key, info in positive.items():
        if not excitation_is_exact_position_supported(key.exc_keV):
            unsupported_activity += info["activity_Bq"]
            unsupported_keys.append(key_string(key))

    event_rows: list[dict[str, Any]] = []
    closure_rows: list[dict[str, Any]] = []
    name_counter: Counter[str] = Counter()
    ledger_sums: dict[Key, Decimal] = defaultdict(Decimal)
    native_rows: list[tuple[str, str, str, Decimal]] = []
    native_rows_by_tag: dict[str, list[tuple[str, str, str, Decimal]]] = defaultdict(list)
    event_id = 0
    omitted_positive_activity = Decimal(0)
    missing_rpip_keys: list[str] = []

    with EVENTLIST.open("w", encoding="utf-8") as ev, WEIGHTS.open("w", newline="", encoding="utf-8") as wf:
        weight_fields = [
            "event_id",
            "source_name",
            "production_tag",
            "raw_volume",
            "canonical_volume_for_reporting_only",
            "ZA",
            "nuclide",
            "exc_keV_decimal",
            "state_id",
            "point_index_within_key",
            "x_cm",
            "y_cm",
            "z_cm",
            "key_activity_Bq",
            "key_rpip_count",
            "event_weight_Bq",
        ]
        writer = csv.DictWriter(wf, fieldnames=weight_fields)
        writer.writeheader()
        for key in sorted(positive, key=lambda k: (k.production_tag, k.raw_volume, int(k.za), dec(k.exc_keV))):
            info = positive[key]
            key_points = points.get(key, [])
            activity = info["activity_Bq"]
            if not key_points:
                omitted_positive_activity += activity
                missing_rpip_keys.append(key_string(key))
                continue
            if not excitation_is_exact_position_supported(key.exc_keV):
                continue
            if len(key_points) != info["rpip_count"]:
                raise RuntimeError(f"RPIP count mismatch while building source: {key_string(key)}")
            point_weight = activity / Decimal(len(key_points))
            native_rows.append((key.raw_volume, key.za, key.exc_keV, activity))
            native_rows_by_tag[key.production_tag].append((key.raw_volume, key.za, key.exc_keV, activity))
            for point_index, point in enumerate(key_points):
                source_name = make_source_name(key, point_index)
                name_counter[source_name] += 1
                time_s = Decimal(event_id) * Decimal("1e-9")
                exc_token = int(dec(key.exc_keV))
                ev.write(
                    f"{event_id} 0 {key.za} {exc_token} {time_s:.12E} "
                    f"{point['x_cm']} {point['y_cm']} {point['z_cm']} "
                    "0 0 1 0 0 0 0\n"
                )
                writer.writerow(
                    {
                        "event_id": event_id,
                        "source_name": source_name,
                        "production_tag": key.production_tag,
                        "raw_volume": key.raw_volume,
                        "canonical_volume_for_reporting_only": info["canonical_volume_for_reporting_only"],
                        "ZA": key.za,
                        "nuclide": info["nuclide"],
                        "exc_keV_decimal": key.exc_keV,
                        "state_id": info["state_id"],
                        "point_index_within_key": point_index,
                        "x_cm": point["x_cm"],
                        "y_cm": point["y_cm"],
                        "z_cm": point["z_cm"],
                        "key_activity_Bq": fmt_dec(activity),
                        "key_rpip_count": len(key_points),
                        "event_weight_Bq": fmt_dec(point_weight),
                    }
                )
                ledger_sums[key] += point_weight
                event_id += 1

    duplicate_names = {name: count for name, count in name_counter.items() if count > 1}
    inventory_total = sum((info["activity_Bq"] for info in positive.values()), Decimal(0))
    represented_inventory_total = inventory_total - unsupported_activity - omitted_positive_activity
    source_total = sum(ledger_sums.values(), Decimal(0))
    major_failures: list[str] = []
    max_major_rel_delta = Decimal(0)
    for key in sorted(positive, key=lambda k: (k.production_tag, k.raw_volume, int(k.za), dec(k.exc_keV))):
        info = positive[key]
        inv = info["activity_Bq"]
        src = ledger_sums.get(key, Decimal(0))
        rel_delta = relative_delta(src, inv)
        fraction = inv / inventory_total if inventory_total else Decimal(0)
        status = "PASS"
        if unsupported_activity and key_string(key) in unsupported_keys:
            status = "UNSUPPORTED_NONZERO_EXCITATION_FOR_EVENTLIST"
        elif key_string(key) in missing_rpip_keys:
            status = "MISSING_RPIP"
        elif fraction >= Decimal("1e-3") and rel_delta > Decimal("1e-6"):
            status = "FAIL_MAJOR_CLOSURE"
            major_failures.append(key_string(key))
        if fraction >= Decimal("1e-3") and rel_delta > max_major_rel_delta:
            max_major_rel_delta = rel_delta
        closure_rows.append(
            {
                "production_tag": key.production_tag,
                "raw_volume": key.raw_volume,
                "canonical_volume_for_reporting_only": info["canonical_volume_for_reporting_only"],
                "ZA": key.za,
                "nuclide": info["nuclide"],
                "exc_keV_decimal": key.exc_keV,
                "state_id": info["state_id"],
                "inventory_activity_Bq": fmt_dec(inv),
                "source_activity_Bq": fmt_dec(src),
                "relative_delta": fmt_dec(rel_delta),
                "activity_fraction": fmt_dec(fraction),
                "rpip_count": info["rpip_count"],
                "source_rows": sum(1 for _name, _count in []),
                "status": status,
            }
        )
    source_rows_by_key = Counter()
    with WEIGHTS.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            source_rows_by_key[key_string(Key(row["production_tag"], row["raw_volume"], row["ZA"], str(dec(row["exc_keV_decimal"]))))] += 1
    for row in closure_rows:
        key = Key(row["production_tag"], row["raw_volume"], row["ZA"], str(dec(row["exc_keV_decimal"])))
        row["source_rows"] = source_rows_by_key[key_string(key)]

    write_csv(
        KEY_CLOSURE,
        closure_rows,
        [
            "production_tag",
            "raw_volume",
            "canonical_volume_for_reporting_only",
            "ZA",
            "nuclide",
            "exc_keV_decimal",
            "state_id",
            "inventory_activity_Bq",
            "source_activity_Bq",
            "relative_delta",
            "activity_fraction",
            "rpip_count",
            "source_rows",
            "status",
        ],
    )

    write_eventlist_source(event_id)
    write_native_store(NATIVE_TOTAL, native_rows)
    by_tag_paths: dict[str, str] = {}
    for tag, rows in sorted(native_rows_by_tag.items()):
        path = BY_TAG_DIR / f"source_v2_native_activity_store_{safe_token(tag)}.dat"
        write_native_store(path, rows)
        by_tag_paths[tag] = rel(path)

    ledger_roundtrip, ledger_total, ledger_count = parse_weight_ledger(WEIGHTS)
    eventlist_roundtrip = parse_eventlist(EVENTLIST)
    native_total_roundtrip = parse_native_store_total(NATIVE_TOTAL)
    roundtrip_key_failures = []
    for key, info in positive.items():
        if not excitation_is_exact_position_supported(key.exc_keV):
            continue
        if relative_delta(ledger_roundtrip.get(key, Decimal(0)), info["activity_Bq"]) > Decimal("1e-12"):
            roundtrip_key_failures.append(key_string(key))
    roundtrip = {
        "status": "PASS"
        if not roundtrip_key_failures
        and eventlist_roundtrip["bad_token_rows"] == 0
        and eventlist_roundtrip["row_count"] == ledger_count
        else "FAIL",
        "ledger_total_Bq": fmt_dec(ledger_total),
        "eventlist": eventlist_roundtrip,
        "native_store_total_Bq": fmt_dec(native_total_roundtrip),
        "roundtrip_key_failure_count": len(roundtrip_key_failures),
        "roundtrip_key_failures": roundtrip_key_failures[:20],
    }
    write_json(ROUNDTRIP, roundtrip)

    name_audit = {
        "status": "PASS" if not duplicate_names and tests["status"] == "PASS" else "FAIL",
        "registered_source_names": sum(name_counter.values()),
        "defined_source_names": event_id,
        "unique_source_names": len(name_counter),
        "duplicate_count": len(duplicate_names),
        "duplicate_examples": dict(list(duplicate_names.items())[:20]),
    }
    write_json(NAME_AUDIT, name_audit)

    sampling = {
        "status": "PASS" if omitted_positive_activity == 0 and unsupported_activity == 0 else "BLOCKED",
        "mode": "explicit_weighted_all_rpip_points",
        "stochastic_sampling": False,
        "eventlist_rows": event_id,
        "positive_inventory_keys": len(positive),
        "represented_keys": len(ledger_sums),
        "missing_rpip_key_count": len(missing_rpip_keys),
        "missing_rpip_keys": missing_rpip_keys[:20],
        "unsupported_nonzero_excitation_key_count": len(unsupported_keys),
        "unsupported_nonzero_excitation_activity_Bq": fmt_dec(unsupported_activity),
        "unsupported_nonzero_excitation_keys": unsupported_keys[:20],
        "omitted_positive_activity_Bq": fmt_dec(omitted_positive_activity),
        "multinomial_deviation_policy": "not applicable: all RPIP points retained with deterministic weights",
    }
    write_json(SAMPLING_AUDIT, sampling)
    write_json(SYNTHETIC_TESTS, tests)

    total_rel = relative_delta(source_total, inventory_total)
    represented_rel = relative_delta(source_total, represented_inventory_total)
    status = "PASS"
    problems: list[str] = []
    if total_rel > Decimal("1e-8"):
        status = "FAIL_INVENTORY_CLOSURE"
        problems.append("total_relative_flux_closure")
    if major_failures:
        status = "FAIL_INVENTORY_CLOSURE"
        problems.append("major_key_closure")
    if duplicate_names:
        status = "FAIL_SOURCE_NAME_COLLISION"
        problems.append("duplicate_source_names")
    if unsupported_activity > 0:
        status = "BLOCKED_UNREPRESENTED_ACTIVITY"
        problems.append("unsupported_nonzero_excitation_for_eventlist")
    if omitted_positive_activity > 0:
        status = "BLOCKED_UNREPRESENTED_ACTIVITY"
        problems.append("missing_rpip_activity")
    if roundtrip["status"] != "PASS":
        status = "FAIL_INVENTORY_CLOSURE"
        problems.append("roundtrip")

    state_activity: dict[str, Decimal] = defaultdict(Decimal)
    source_state_activity: dict[str, Decimal] = defaultdict(Decimal)
    for key, info in positive.items():
        state_activity[info["state_id"]] += info["activity_Bq"]
    with WEIGHTS.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            source_state_activity[row["state_id"]] += dec(row["event_weight_Bq"])

    manifest = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "claim_boundary": "source construction only; no transport selected-rate promotion",
        "source_strategy": "weighted_exact_position_eventlist",
        "native_oracle_strategy": "volume_level_activation_sources_isotope_store",
        "detector_time_constant_s": DETECTOR_TIME_CONSTANT_S,
        "geometry": rel(GEOMETRY),
        "inputs": {
            "inventory": rel(INVENTORY),
            "rpip_key_join": rel(JOIN),
            "rpip_points": rel(POINTS),
            "source_semantics": rel(SEMANTICS),
        },
        "outputs": {
            "eventlist": rel(EVENTLIST),
            "weights": rel(WEIGHTS),
            "source_card": rel(SOURCE_CARD),
            "native_total_store": rel(NATIVE_TOTAL),
            "native_by_tag_stores": by_tag_paths,
            "key_closure": rel(KEY_CLOSURE),
            "name_audit": rel(NAME_AUDIT),
            "sampling_audit": rel(SAMPLING_AUDIT),
            "roundtrip": rel(ROUNDTRIP),
        },
        "inventory_total_activity_Bq": fmt_dec(inventory_total),
        "source_total_activity_Bq": fmt_dec(source_total),
        "represented_inventory_total_activity_Bq": fmt_dec(represented_inventory_total),
        "total_relative_flux_closure": fmt_dec(total_rel),
        "represented_relative_flux_closure": fmt_dec(represented_rel),
        "max_major_key_relative_delta": fmt_dec(max_major_rel_delta),
        "major_key_failure_count": len(major_failures),
        "positive_inventory_keys": len(positive),
        "eventlist_rows": event_id,
        "duplicate_source_names": len(duplicate_names),
        "unsupported_activity_Bq": fmt_dec(unsupported_activity),
        "omitted_positive_activity_Bq": fmt_dec(omitted_positive_activity),
        "state_activity_Bq": {k: fmt_dec(v) for k, v in sorted(state_activity.items())},
        "source_state_activity_Bq": {k: fmt_dec(v) for k, v in sorted(source_state_activity.items())},
        "problems": problems,
    }
    write_json(MANIFEST, manifest)

    summary = {
        "status": status,
        "outputs": [
            rel(MANIFEST),
            rel(EVENTLIST),
            rel(WEIGHTS),
            rel(SOURCE_CARD),
            rel(NATIVE_TOTAL),
            rel(KEY_CLOSURE),
            rel(NAME_AUDIT),
            rel(SAMPLING_AUDIT),
            rel(ROUNDTRIP),
            rel(SUMMARY_MD),
        ],
        "findings": [
            f"Built {event_id} weighted EventList rows from RPIP points.",
            f"Total activity closure relative delta {fmt_dec(total_rel)}.",
            f"Duplicate source names {len(duplicate_names)}.",
            f"Unsupported positive activity {fmt_dec(unsupported_activity)} Bq.",
        ],
        "next_gate": "G5 native activation inventory/oracle comparison",
        "user_decision_required": False,
    }
    write_json(SUMMARY_JSON, summary)
    SUMMARY_MD.write_text(
        "\n".join(
            [
                "# WP04 Custom Source V2 Summary",
                "",
                f"status: `{status}`",
                "",
                f"- eventlist rows: `{event_id}`",
                f"- inventory total Bq: `{fmt_dec(inventory_total)}`",
                f"- source total Bq: `{fmt_dec(source_total)}`",
                f"- total relative closure: `{fmt_dec(total_rel)}`",
                f"- max major-key relative delta: `{fmt_dec(max_major_rel_delta)}`",
                f"- duplicate source names: `{len(duplicate_names)}`",
                f"- unsupported activity Bq: `{fmt_dec(unsupported_activity)}`",
                f"- omitted positive activity Bq: `{fmt_dec(omitted_positive_activity)}`",
                "",
                "Outputs:",
                f"- manifest: `{rel(MANIFEST)}`",
                f"- source card: `{rel(SOURCE_CARD)}`",
                f"- EventList: `{rel(EVENTLIST)}`",
                f"- weight ledger: `{rel(WEIGHTS)}`",
                f"- native store: `{rel(NATIVE_TOTAL)}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"WP04 {status}")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
