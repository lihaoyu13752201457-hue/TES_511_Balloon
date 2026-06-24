#!/usr/bin/env python3
"""WP02 RPIP alignment for delayed-source authority v2.

This streams existing `.sim.gz` files and aligns `CC IP RP` production-position
records with the WP01 raw inventory. It does not run Cosima.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "02_rpip_alignment"
BUILDUP = ROOT / "runs/step02_buildup_fix5_fullstat_v2"
RUN_MANIFEST = BUILDUP / "run_manifest.csv"
RAW_INVENTORY = PHASE_DIR / "01_raw_inventory/raw_inventory_all_states.csv"

TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)
NUM = r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
COPY_SUFFIX_RE = re.compile(r"^(?P<base>.+)_\d+$")
GROUND_EXC_TOL_KEV = Decimal("0.001")
IP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<vn>\S+)\s+"
    rf"(?P<x>{NUM})\s+(?P<y>{NUM})\s+(?P<z>{NUM})\s+"
    rf"(?P<za>\d+)\s+(?P<exc>{NUM})\s+(?P<t>{NUM})"
    r"(?P<meta>.*)$"
)

RE_SEG_SHIELD = re.compile(r"^(Nb_Shield|W_Shield|Cryo_Shell|BGO_Shield|Al_Shell)(?:_p\d+_z\d+)?$", re.I)
RE_TP = re.compile(r"^TP_L(?P<l>\d+)_\d+$", re.I)
RE_TESPIX = re.compile(r"^TES_Pixel_L(?P<l>\d+)$", re.I)
RE_COLLBAR = re.compile(r"^(CollBar[XY])_\d+$", re.I)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def dec_to_str(value: Decimal | None) -> str:
    if value is None:
        return ""
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def normalize_decimal_token(token: str) -> str:
    try:
        value = Decimal(token.strip())
    except InvalidOperation:
        return token.strip()
    if abs(value) <= GROUND_EXC_TOL_KEV:
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def parse_tag(path: Path) -> str:
    match = TAG_RE.search(path.name)
    return match.group("tag").lower() if match else "unknown"


def canon_vn(vn: str) -> str:
    if not vn:
        return "Other"
    match = RE_SEG_SHIELD.match(vn)
    if match:
        return match.group(1)
    match = RE_TESPIX.match(vn)
    if match:
        return f"TES_L{int(match.group('l'))}"
    if vn.startswith("TES_L"):
        return vn
    match = RE_TP.match(vn)
    if match:
        return f"TES_L{int(match.group('l'))}"
    match = RE_COLLBAR.match(vn)
    if match:
        return match.group(1)
    if vn in ("Cu_Base", "Cu_SupportPole", "CU_BASE", "CU_SUPPORT", "Copper"):
        return "Copper"
    if vn in ("Collimator", "CollimatorVac", "CollimatorEnvelope"):
        return "CollimatorVac"
    if "window" in vn.lower() or vn.lower().startswith("win"):
        return "Window"
    return vn


def dat_volume_key_from_rpip(rpip_volume: str, dat_volumes: set[str]) -> str:
    if rpip_volume in dat_volumes:
        return rpip_volume
    match = RE_TP.match(rpip_volume)
    if match:
        tes_pixel = f"TES_Pixel_L{int(match.group('l'))}"
        if tes_pixel in dat_volumes:
            return tes_pixel
    candidate = rpip_volume
    while True:
        match = COPY_SUFFIX_RE.match(candidate)
        if not match:
            return rpip_volume
        candidate = match.group("base")
        if candidate in dat_volumes:
            return candidate


def load_run_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out[Path(row["sim_path"]).name] = row
    return out


def load_inventory(path: Path) -> dict[tuple[str, str, int, str], dict[str, Any]]:
    out: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["production_tag"], row["raw_volume"], int(row["ZA"]), row["exc_keV_decimal"])
            out[key] = row
    return out


def parse_meta(meta: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for token in meta.strip().split():
        if "=" not in token:
            continue
        k, v = token.split("=", 1)
        out[k] = v
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def stream_rpip(sim_files: list[Path], manifest_rows: dict[str, dict[str, str]], dat_volumes: set[str]) -> tuple[
    dict[tuple[str, str, int, str], dict[str, Any]],
    list[dict[str, Any]],
    Counter[str],
]:
    key_stats: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    file_rows: list[dict[str, Any]] = []
    meta_counts: Counter[str] = Counter()
    points_path = OUT / "rpip_points_all.csv"
    with points_path.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "production_tag",
            "source_file",
            "line_no",
            "raw_volume",
            "rpip_volume",
            "canonical_volume_for_reporting_only",
            "ZA",
            "exc_keV_decimal",
            "x_cm",
            "y_cm",
            "z_cm",
            "t_s",
            "tid",
            "pid",
            "sproc",
            "prim",
            "par",
            "cproc",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for path in sim_files:
            tag = manifest_rows.get(path.name, {}).get("particle") or parse_tag(path)
            n_lines = 0
            n_parsed = 0
            n_bad = 0
            with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as gz:
                for line_no, raw in enumerate(gz, 1):
                    if not raw.startswith("CC IP RP"):
                        continue
                    n_lines += 1
                    match = IP_RE.match(raw.strip())
                    if not match:
                        n_bad += 1
                        continue
                    n_parsed += 1
                    rpip_volume = match.group("vn")
                    raw_volume = dat_volume_key_from_rpip(rpip_volume, dat_volumes)
                    za = int(match.group("za"))
                    exc_norm = normalize_decimal_token(match.group("exc"))
                    meta = parse_meta(match.group("meta"))
                    key = (tag, raw_volume, za, exc_norm)
                    stat = key_stats.setdefault(
                        key,
                        {
                            "production_tag": tag,
                            "raw_volume": raw_volume,
                            "canonical_volume_for_reporting_only": canon_vn(raw_volume),
                            "ZA": za,
                            "exc_keV_decimal": exc_norm,
                            "rpip_count": 0,
                            "source_files": set(),
                            "rpip_volume_counts": Counter(),
                            "x_sum": 0.0,
                            "y_sum": 0.0,
                            "z_sum": 0.0,
                            "t_min": None,
                            "t_max": None,
                            "cproc_counts": Counter(),
                            "sproc_counts": Counter(),
                            "prim_counts": Counter(),
                        },
                    )
                    x = float(match.group("x"))
                    y = float(match.group("y"))
                    z = float(match.group("z"))
                    t = float(match.group("t"))
                    stat["rpip_count"] += 1
                    stat["source_files"].add(rel(path))
                    stat["rpip_volume_counts"][rpip_volume] += 1
                    stat["x_sum"] += x
                    stat["y_sum"] += y
                    stat["z_sum"] += z
                    stat["t_min"] = t if stat["t_min"] is None else min(float(stat["t_min"]), t)
                    stat["t_max"] = t if stat["t_max"] is None else max(float(stat["t_max"]), t)
                    for name in ("cproc", "sproc", "prim"):
                        value = meta.get(name, "")
                        if value:
                            stat[f"{name}_counts"][value] += 1
                            meta_counts[f"{name}={value}"] += 1
                    writer.writerow(
                        {
                            "production_tag": tag,
                            "source_file": rel(path),
                            "line_no": line_no,
                            "raw_volume": raw_volume,
                            "rpip_volume": rpip_volume,
                            "canonical_volume_for_reporting_only": canon_vn(raw_volume),
                            "ZA": za,
                            "exc_keV_decimal": exc_norm,
                            "x_cm": f"{x:.9g}",
                            "y_cm": f"{y:.9g}",
                            "z_cm": f"{z:.9g}",
                            "t_s": f"{t:.9g}",
                            "tid": meta.get("tid", ""),
                            "pid": meta.get("pid", ""),
                            "sproc": meta.get("sproc", ""),
                            "prim": meta.get("prim", ""),
                            "par": meta.get("par", ""),
                            "cproc": meta.get("cproc", ""),
                        }
                    )
            file_rows.append(
                {
                    "source_file": rel(path),
                    "production_tag": tag,
                    "cc_ip_rp_lines": n_lines,
                    "parsed_lines": n_parsed,
                    "unparsed_lines": n_bad,
                    "manifest_job_name": manifest_rows.get(path.name, {}).get("job_name", ""),
                    "manifest_events": manifest_rows.get(path.name, {}).get("events", ""),
                }
            )
    return key_stats, file_rows, meta_counts


def first_counter(counter: Counter[str]) -> str:
    if not counter:
        return ""
    key, count = counter.most_common(1)[0]
    return f"{key}:{count}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-point-csv", action="store_true", help="reserved; point CSV is currently required")
    args = parser.parse_args()
    if args.skip_point_csv:
        raise SystemExit("--skip-point-csv is not supported for this harness run")

    OUT.mkdir(parents=True, exist_ok=True)
    inventory = load_inventory(RAW_INVENTORY)
    manifest_rows = load_run_manifest(RUN_MANIFEST)
    sim_files = sorted(BUILDUP.glob("*.sim.gz"))
    if not sim_files:
        summary = {
            "status": "BLOCKED_RAW_ACTIVATION_PRODUCTS_MISSING",
            "inputs": [],
            "outputs": [],
            "findings": ["no raw buildup .sim.gz files found"],
            "claim_impact": ["RPIP alignment cannot be performed."],
            "next_gate": "provide raw activation SIM products",
            "user_decision_required": True,
        }
        write_json(OUT / "summary.json", summary)
        raise SystemExit("BLOCKED_RAW_ACTIVATION_PRODUCTS_MISSING")

    dat_volumes = {key[1] for key in inventory}
    key_stats, file_rows, meta_counts = stream_rpip(sim_files, manifest_rows, dat_volumes)

    write_csv(
        OUT / "rpip_file_manifest.csv",
        file_rows,
        ["source_file", "production_tag", "cc_ip_rp_lines", "parsed_lines", "unparsed_lines", "manifest_job_name", "manifest_events"],
    )

    join_rows: list[dict[str, Any]] = []
    count_rows: list[dict[str, Any]] = []
    missing_positive_activity: list[dict[str, Any]] = []
    count_mismatch_rows: list[dict[str, Any]] = []
    represented_positive = 0
    total_positive = 0
    activity_without_rpip = Decimal("0")
    total_activity = Decimal("0")

    all_keys = sorted(set(inventory) | set(key_stats))
    for key in all_keys:
        inv = inventory.get(key)
        stat = key_stats.get(key)
        dat_count = Decimal(inv["production_count_raw"]) if inv else Decimal("0")
        activity = Decimal(inv["activity_day15_direct_Bq"]) if inv else Decimal("0")
        state_class = inv["state_class"] if inv else "RPIP_WITHOUT_DAT"
        total_activity += activity
        rpip_count = int(stat["rpip_count"]) if stat else 0
        coverage = Decimal(rpip_count) / dat_count if dat_count > 0 else Decimal("0")
        status = "PASS"
        if inv is None:
            status = "RPIP_WITHOUT_DAT_KEY"
        elif rpip_count == 0 and activity > 0:
            status = "MISSING_RPIP_FOR_POSITIVE_ACTIVITY"
        elif dat_count != Decimal(rpip_count):
            status = "COUNT_MISMATCH"
        if activity > 0:
            total_positive += 1
            if rpip_count > 0:
                represented_positive += 1
            else:
                activity_without_rpip += activity
                missing_positive_activity.append({"key": key, "activity_day15_direct_Bq": dec_to_str(activity)})
        if status == "COUNT_MISMATCH":
            count_mismatch_rows.append({"key": key, "dat_count": dec_to_str(dat_count), "rpip_count": rpip_count})

        tag, raw_volume, za, exc = key
        centroid_x = centroid_y = centroid_z = ""
        n_eff = ""
        if stat and rpip_count > 0:
            centroid_x = f"{float(stat['x_sum']) / rpip_count:.9g}"
            centroid_y = f"{float(stat['y_sum']) / rpip_count:.9g}"
            centroid_z = f"{float(stat['z_sum']) / rpip_count:.9g}"
            n_eff = str(rpip_count)
        row = {
            "production_tag": tag,
            "raw_volume": raw_volume,
            "canonical_volume_for_reporting_only": inv["canonical_volume_for_reporting_only"] if inv else (stat["canonical_volume_for_reporting_only"] if stat else canon_vn(raw_volume)),
            "ZA": za,
            "nuclide": inv["nuclide"] if inv else "",
            "exc_keV_decimal": exc,
            "state_id": inv["state_id"] if inv else "",
            "state_class": state_class,
            "dat_production_count_raw": dec_to_str(dat_count),
            "rpip_count": rpip_count,
            "coverage_fraction": dec_to_str(coverage),
            "activity_day15_direct_Bq": dec_to_str(activity),
            "source_files_count": len(stat["source_files"]) if stat else 0,
            "rpip_volume_count": len(stat["rpip_volume_counts"]) if stat else 0,
            "rpip_volume_examples": ";".join(name for name, _count in stat["rpip_volume_counts"].most_common(5)) if stat else "",
            "centroid_x_cm": centroid_x,
            "centroid_y_cm": centroid_y,
            "centroid_z_cm": centroid_z,
            "effective_sample_size": n_eff,
            "dominant_cproc": first_counter(stat["cproc_counts"]) if stat else "",
            "dominant_sproc": first_counter(stat["sproc_counts"]) if stat else "",
            "dominant_prim": first_counter(stat["prim_counts"]) if stat else "",
            "status": status,
        }
        join_rows.append(row)
        count_rows.append(
            {
                "production_tag": tag,
                "raw_volume": raw_volume,
                "ZA": za,
                "exc_keV_decimal": exc,
                "dat_production_count_raw": dec_to_str(dat_count),
                "rpip_count": rpip_count,
                "delta_rpip_minus_dat": dec_to_str(Decimal(rpip_count) - dat_count),
                "status": status,
            }
        )

    join_fields = [
        "production_tag",
        "raw_volume",
        "canonical_volume_for_reporting_only",
        "ZA",
        "nuclide",
        "exc_keV_decimal",
        "state_id",
        "state_class",
        "dat_production_count_raw",
        "rpip_count",
        "coverage_fraction",
        "activity_day15_direct_Bq",
        "source_files_count",
        "rpip_volume_count",
        "rpip_volume_examples",
        "centroid_x_cm",
        "centroid_y_cm",
        "centroid_z_cm",
        "effective_sample_size",
        "dominant_cproc",
        "dominant_sproc",
        "dominant_prim",
        "status",
    ]
    write_csv(OUT / "dat_rpip_key_join.csv", join_rows, join_fields)
    write_csv(
        OUT / "dat_rpip_count_closure.csv",
        count_rows,
        ["production_tag", "raw_volume", "ZA", "exc_keV_decimal", "dat_production_count_raw", "rpip_count", "delta_rpip_minus_dat", "status"],
    )

    state_rows = []
    state_group: dict[tuple[str, int, str, str], dict[str, Any]] = {}
    for row in join_rows:
        key = (row["production_tag"], int(row["ZA"]), row["exc_keV_decimal"], row["state_id"])
        item = state_group.setdefault(
            key,
            {
                "production_tag": row["production_tag"],
                "ZA": row["ZA"],
                "nuclide": row["nuclide"],
                "exc_keV_decimal": row["exc_keV_decimal"],
                "state_id": row["state_id"],
                "raw_volume_count": 0,
                "dat_count": Decimal("0"),
                "rpip_count": 0,
                "activity_day15_direct_Bq": Decimal("0"),
            },
        )
        item["raw_volume_count"] += 1
        item["dat_count"] += Decimal(row["dat_production_count_raw"])
        item["rpip_count"] += int(row["rpip_count"])
        item["activity_day15_direct_Bq"] += Decimal(row["activity_day15_direct_Bq"])
    for item in state_group.values():
        state_rows.append(
            {
                **{k: v for k, v in item.items() if k not in ("dat_count", "activity_day15_direct_Bq")},
                "dat_production_count_raw": dec_to_str(item["dat_count"]),
                "activity_day15_direct_Bq": dec_to_str(item["activity_day15_direct_Bq"]),
            }
        )
    write_csv(
        OUT / "rpip_state_catalog.csv",
        sorted(state_rows, key=lambda r: (r["production_tag"], int(r["ZA"]), r["exc_keV_decimal"], r["state_id"])),
        ["production_tag", "ZA", "nuclide", "exc_keV_decimal", "state_id", "raw_volume_count", "dat_production_count_raw", "rpip_count", "activity_day15_direct_Bq"],
    )

    volume_groups: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    for row in join_rows:
        if row["state_class"] == "RPIP_WITHOUT_DAT":
            continue
        key = (row["production_tag"], row["canonical_volume_for_reporting_only"], int(row["ZA"]), row["exc_keV_decimal"])
        item = volume_groups.setdefault(
            key,
            {
                "production_tag": row["production_tag"],
                "canonical_volume_for_reporting_only": row["canonical_volume_for_reporting_only"],
                "ZA": row["ZA"],
                "nuclide": row["nuclide"],
                "exc_keV_decimal": row["exc_keV_decimal"],
                "raw_volumes": set(),
                "activity_day15_direct_Bq": Decimal("0"),
                "dat_count": Decimal("0"),
            },
        )
        item["raw_volumes"].add(row["raw_volume"])
        item["activity_day15_direct_Bq"] += Decimal(row["activity_day15_direct_Bq"])
        item["dat_count"] += Decimal(row["dat_production_count_raw"])
    volume_rows = []
    canonicalization_at_risk = Decimal("0")
    for item in volume_groups.values():
        raw_count = len(item["raw_volumes"])
        if raw_count > 1:
            canonicalization_at_risk += item["activity_day15_direct_Bq"]
        volume_rows.append(
            {
                "production_tag": item["production_tag"],
                "canonical_volume_for_reporting_only": item["canonical_volume_for_reporting_only"],
                "ZA": item["ZA"],
                "nuclide": item["nuclide"],
                "exc_keV_decimal": item["exc_keV_decimal"],
                "raw_volume_count": raw_count,
                "raw_volumes": ";".join(sorted(item["raw_volumes"])),
                "dat_production_count_raw": dec_to_str(item["dat_count"]),
                "activity_day15_direct_Bq": dec_to_str(item["activity_day15_direct_Bq"]),
                "canonicalization_would_merge_raw_volumes": raw_count > 1,
            }
        )
    write_csv(
        OUT / "volume_identity_audit.csv",
        sorted(volume_rows, key=lambda r: (r["production_tag"], r["canonical_volume_for_reporting_only"], int(r["ZA"]), r["exc_keV_decimal"])),
        [
            "production_tag",
            "canonical_volume_for_reporting_only",
            "ZA",
            "nuclide",
            "exc_keV_decimal",
            "raw_volume_count",
            "raw_volumes",
            "dat_production_count_raw",
            "activity_day15_direct_Bq",
            "canonicalization_would_merge_raw_volumes",
        ],
    )

    state_identity_rows = []
    for key, item in state_group.items():
        _tag, _za, exc, state_id = key
        state_identity_rows.append(
            {
                "production_tag": item["production_tag"],
                "ZA": item["ZA"],
                "nuclide": item["nuclide"],
                "exc_keV_decimal": exc,
                "state_id": state_id,
                "is_ground_state": exc == "0",
                "would_fold_to_ground_if_exc_ignored": exc != "0",
                "activity_day15_direct_Bq": dec_to_str(item["activity_day15_direct_Bq"]),
            }
        )
    write_csv(
        OUT / "state_identity_audit.csv",
        sorted(state_identity_rows, key=lambda r: (r["production_tag"], int(r["ZA"]), r["exc_keV_decimal"])),
        [
            "production_tag",
            "ZA",
            "nuclide",
            "exc_keV_decimal",
            "state_id",
            "is_ground_state",
            "would_fold_to_ground_if_exc_ignored",
            "activity_day15_direct_Bq",
        ],
    )

    parsed_lines = sum(int(row["parsed_lines"]) for row in file_rows)
    unparsed_lines = sum(int(row["unparsed_lines"]) for row in file_rows)
    rpip_without_dat = sum(1 for row in join_rows if row["status"] == "RPIP_WITHOUT_DAT_KEY")
    mismatches = len(count_mismatch_rows)
    status = "PASS"
    findings = [
        f"Parsed {parsed_lines} CC IP RP rows from {len(sim_files)} SIM files.",
        f"Positive-activity keys represented: {represented_positive}/{total_positive}.",
        f"Canonicalization would merge {dec_to_str(canonicalization_at_risk)} Bq if used as the physics key.",
    ]
    if unparsed_lines:
        status = "FAIL_RPIP_ALIGNMENT"
        findings.append(f"{unparsed_lines} CC IP RP lines failed parser.")
    if missing_positive_activity:
        status = "BLOCKED_UNREPRESENTED_ACTIVITY"
        findings.append(f"{len(missing_positive_activity)} positive-activity keys have no RPIP support.")
    if mismatches:
        status = "FAIL_RPIP_ALIGNMENT"
        findings.append(f"{mismatches} dat/RPIP key counts do not close exactly.")
    if rpip_without_dat:
        status = "FAIL_RPIP_ALIGNMENT"
        findings.append(f"{rpip_without_dat} RPIP keys have no matching raw .dat inventory key.")

    summary_payload = {
        "artifact_type": "rpip_coverage_summary",
        "status": status,
        "sim_file_count": len(sim_files),
        "parsed_cc_ip_rp_rows": parsed_lines,
        "unparsed_cc_ip_rp_rows": unparsed_lines,
        "inventory_key_count": len(inventory),
        "rpip_key_count": len(key_stats),
        "joined_key_count": len(all_keys),
        "positive_activity_keys": total_positive,
        "positive_activity_keys_with_rpip": represented_positive,
        "activity_without_rpip_Bq": dec_to_str(activity_without_rpip),
        "activity_without_rpip_fraction": dec_to_str((activity_without_rpip / total_activity) if total_activity else Decimal("0")),
        "count_mismatch_key_count": mismatches,
        "rpip_without_dat_key_count": rpip_without_dat,
        "canonicalization_at_risk_Bq": dec_to_str(canonicalization_at_risk),
        "top_metadata_tokens": dict(meta_counts.most_common(20)),
    }
    write_json(OUT / "rpip_coverage_summary.json", summary_payload)

    summary = {
        "status": status,
        "inputs": [
            rel(RAW_INVENTORY),
            rel(RUN_MANIFEST),
            f"{rel(BUILDUP)}/*.sim.gz",
        ],
        "outputs": [
            rel(OUT / "rpip_file_manifest.csv"),
            rel(OUT / "rpip_points_all.csv"),
            rel(OUT / "rpip_state_catalog.csv"),
            rel(OUT / "dat_rpip_key_join.csv"),
            rel(OUT / "dat_rpip_count_closure.csv"),
            rel(OUT / "volume_identity_audit.csv"),
            rel(OUT / "state_identity_audit.csv"),
            rel(OUT / "rpip_coverage_summary.json"),
            rel(OUT / "rpip_coverage_summary.md"),
        ],
        "findings": findings,
        "claim_impact": [
            "This closes spatial support for raw inventory keys only if status is PASS.",
            "No delayed source v2 has been emitted or promoted yet.",
        ],
        "next_gate": "G3 source semantics and excited-ion/native activation strategy",
        "user_decision_required": False,
    }
    write_json(OUT / "summary.json", summary)

    md = [
        "# WP02 RPIP Alignment",
        "",
        f"status: `{status}`",
        f"SIM files: `{len(sim_files)}`",
        f"parsed CC IP RP rows: `{parsed_lines}`",
        f"positive-activity keys represented: `{represented_positive}/{total_positive}`",
        f"activity without RPIP: `{dec_to_str(activity_without_rpip)}` Bq",
        f"count mismatch keys: `{mismatches}`",
        f"RPIP-without-DAT keys: `{rpip_without_dat}`",
        "",
        "## Findings",
    ]
    md.extend(f"- {item}" for item in findings)
    (OUT / "rpip_coverage_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"WP02 {status}: wrote {rel(OUT / 'rpip_coverage_summary.json')}")


if __name__ == "__main__":
    main()
