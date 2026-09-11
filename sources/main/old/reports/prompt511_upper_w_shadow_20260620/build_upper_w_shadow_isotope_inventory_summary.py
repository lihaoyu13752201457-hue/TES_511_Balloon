#!/usr/bin/env python3
"""Summarize isotope-store records for the upper-W-shadow buildup smoke."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_upper_w_shadow_20260620"
RUN = WORK / "runs/upper_w_shadow_buildup_isotope_g1m_r2"
SUMMARY_JSON = WORK / "upper_w_shadow_isotope_inventory_summary.json"
SUMMARY_MD = WORK / "upper_w_shadow_isotope_inventory_summary.md"
CSV_BY_NUCLIDE = WORK / "upper_w_shadow_isotope_by_nuclide.csv"
CSV_BY_VOLUME = WORK / "upper_w_shadow_isotope_by_volume.csv"
CSV_BY_PARTICLE_NUCLIDE = WORK / "upper_w_shadow_isotope_by_particle_nuclide.csv"
CSV_W_SHADOW = WORK / "upper_w_shadow_isotope_w_shadow_records.csv"

TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)

ELEMENTS = [
    "",
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
    "At",
    "Rn",
    "Fr",
    "Ra",
    "Ac",
    "Th",
    "Pa",
    "U",
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def parse_tag(path: Path) -> str:
    match = TAG_RE.search(path.name)
    return match.group("tag").lower() if match else "unknown"


def nuclide_name(rp_id: int) -> str:
    z = rp_id // 1000
    a = rp_id % 1000
    symbol = ELEMENTS[z] if 0 < z < len(ELEMENTS) else f"Z{z}"
    return f"{symbol}-{a}"


def parse_dat(path: Path) -> tuple[float | None, list[dict[str, Any]]]:
    tt = None
    volume = None
    rows = []
    particle = parse_tag(path)
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line == "EN":
            continue
        if line.startswith("TT "):
            tt = float(line.split()[1])
            continue
        if line.startswith("VN "):
            volume = line.split(maxsplit=1)[1]
            continue
        if line.startswith("RP "):
            if volume is None:
                raise ValueError(f"RP before VN in {path}")
            fields = line.split()
            rp_id = int(fields[1])
            excitation = float(fields[2])
            value = float(fields[3])
            rows.append(
                {
                    "particle": particle,
                    "source_dat": rel(path),
                    "volume": volume,
                    "rp_id": rp_id,
                    "nuclide": nuclide_name(rp_id),
                    "excitation_keV": excitation,
                    "raw_value": value,
                    "is_added_w_shadow_volume": volume.startswith("Prompt511_UpperWShadow"),
                }
            )
    return tt, rows


def compact(counter: Counter[tuple[Any, ...]], fields: list[str]) -> list[dict[str, Any]]:
    rows = []
    for key, value in counter.most_common():
        row = dict(zip(fields, key, strict=True))
        row["raw_value"] = value
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Upper W Shadow Isotope Inventory Smoke",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This summarizes raw Cosima isotope-store records from the buildup smoke.",
        "It is not a delayed source, decay transport, veto replay, time-axis result,",
        "or activity authority.",
        "",
        f"- run: `{payload['run']}`",
        f"- dat files: `{payload['dat_files']}`",
        f"- generated particles: `{payload['generated_particles']}`",
        f"- total raw isotope-store value: `{payload['total_raw_value']:.6g}`",
        f"- added W-shadow raw value: `{payload['added_w_shadow_raw_value']:.6g}`",
        "",
        "Top nuclides:",
        "",
        "| nuclide | raw value |",
        "|---|---:|",
    ]
    for row in payload["top_nuclides"]:
        lines.append(f"| {row['nuclide']} | {row['raw_value']:.6g} |")
    lines.extend(["", "Top added W-shadow records:", "", "| volume | nuclide | particle | raw value |", "|---|---|---|---:|"])
    for row in payload["top_added_w_shadow_records"]:
        lines.append(f"| {row['volume']} | {row['nuclide']} | {row['particle']} | {row['raw_value']:.6g} |")
    lines.extend(["", "Outputs:", ""])
    for key in ("csv_by_nuclide", "csv_by_volume", "csv_by_particle_nuclide", "csv_w_shadow"):
        lines.append(f"- `{payload[key]}`")
    return "\n".join(lines) + "\n"


def main() -> int:
    if not RUN.exists():
        raise FileNotFoundError(RUN)
    dats = sorted(RUN.glob("*.dat.inc1.dat"))
    if not dats:
        raise FileNotFoundError(f"no isotope dat files in {RUN}")

    all_rows: list[dict[str, Any]] = []
    tt_by_dat = {}
    for dat in dats:
        tt, rows = parse_dat(dat)
        tt_by_dat[rel(dat)] = tt
        all_rows.extend(rows)

    by_nuclide: Counter[tuple[str]] = Counter()
    by_volume: Counter[tuple[str]] = Counter()
    by_particle_nuclide: Counter[tuple[str, str]] = Counter()
    by_w_shadow: Counter[tuple[str, str, str]] = Counter()
    by_particle: Counter[tuple[str]] = Counter()
    for row in all_rows:
        value = float(row["raw_value"])
        by_nuclide[(row["nuclide"],)] += value
        by_volume[(row["volume"],)] += value
        by_particle_nuclide[(row["particle"], row["nuclide"])] += value
        by_particle[(row["particle"],)] += value
        if row["is_added_w_shadow_volume"]:
            by_w_shadow[(row["volume"], row["nuclide"], row["particle"])] += value

    rows_by_nuclide = compact(by_nuclide, ["nuclide"])
    rows_by_volume = compact(by_volume, ["volume"])
    rows_by_particle_nuclide = compact(by_particle_nuclide, ["particle", "nuclide"])
    rows_w_shadow = compact(by_w_shadow, ["volume", "nuclide", "particle"])

    write_csv(CSV_BY_NUCLIDE, rows_by_nuclide)
    write_csv(CSV_BY_VOLUME, rows_by_volume)
    write_csv(CSV_BY_PARTICLE_NUCLIDE, rows_by_particle_nuclide)
    write_csv(CSV_W_SHADOW, rows_w_shadow)

    run_summary = json.loads((RUN / "run_summary.json").read_text(encoding="utf-8"))
    payload = {
        "status": "PASS_UPPER_W_SHADOW_ISOTOPE_INVENTORY_SMOKE",
        "claim_level": "raw isotope-store inventory smoke only; not delayed/activity authority",
        "run": rel(RUN),
        "dat_files": len(dats),
        "generated_particles": sum(int(row.get("generated_particles") or 0) for row in run_summary),
        "total_raw_value": sum(float(row["raw_value"]) for row in all_rows),
        "added_w_shadow_raw_value": sum(row["raw_value"] for row in rows_w_shadow),
        "raw_value_by_particle": {
            key[0]: value for key, value in sorted(by_particle.items(), key=lambda item: item[0][0])
        },
        "tt_by_dat_s": tt_by_dat,
        "top_nuclides": rows_by_nuclide[:20],
        "top_volumes": rows_by_volume[:20],
        "top_particle_nuclides": rows_by_particle_nuclide[:30],
        "top_added_w_shadow_records": rows_w_shadow[:30],
        "csv_by_nuclide": rel(CSV_BY_NUCLIDE),
        "csv_by_volume": rel(CSV_BY_VOLUME),
        "csv_by_particle_nuclide": rel(CSV_BY_PARTICLE_NUCLIDE),
        "csv_w_shadow": rel(CSV_W_SHADOW),
    }
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON), "report": rel(SUMMARY_MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
