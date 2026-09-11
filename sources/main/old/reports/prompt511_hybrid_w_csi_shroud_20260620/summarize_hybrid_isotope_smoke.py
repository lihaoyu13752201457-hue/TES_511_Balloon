#!/usr/bin/env python3
"""Summarize added-volume isotope records for the prompt-511 hybrid smoke."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_DIR = ROOT / "runs" / "hybrid_w_csi_shroud_buildup_isotope_g1m_r2"
OUT_JSON = ROOT / "prompt511_hybrid_w_csi_shroud_isotope_smoke_summary.json"
OUT_MD = ROOT / "prompt511_hybrid_w_csi_shroud_isotope_smoke_summary.md"

ADDED_PREFIXES = (
    "HybridW_Prompt511_",
    "CsI_HybridUpperShroud_Prompt511_",
)

ELEMENTS = {
    1: "H",
    2: "He",
    3: "Li",
    4: "Be",
    5: "B",
    6: "C",
    7: "N",
    8: "O",
    9: "F",
    10: "Ne",
    11: "Na",
    12: "Mg",
    13: "Al",
    14: "Si",
    15: "P",
    16: "S",
    17: "Cl",
    18: "Ar",
    19: "K",
    20: "Ca",
    21: "Sc",
    22: "Ti",
    23: "V",
    24: "Cr",
    25: "Mn",
    26: "Fe",
    27: "Co",
    28: "Ni",
    29: "Cu",
    30: "Zn",
    31: "Ga",
    32: "Ge",
    33: "As",
    34: "Se",
    35: "Br",
    36: "Kr",
    37: "Rb",
    38: "Sr",
    39: "Y",
    40: "Zr",
    41: "Nb",
    42: "Mo",
    43: "Tc",
    44: "Ru",
    45: "Rh",
    46: "Pd",
    47: "Ag",
    48: "Cd",
    49: "In",
    50: "Sn",
    51: "Sb",
    52: "Te",
    53: "I",
    54: "Xe",
    55: "Cs",
    56: "Ba",
    57: "La",
    58: "Ce",
    59: "Pr",
    60: "Nd",
    61: "Pm",
    62: "Sm",
    63: "Eu",
    64: "Gd",
    65: "Tb",
    66: "Dy",
    67: "Ho",
    68: "Er",
    69: "Tm",
    70: "Yb",
    71: "Lu",
    72: "Hf",
    73: "Ta",
    74: "W",
    75: "Re",
    76: "Os",
    77: "Ir",
    78: "Pt",
    79: "Au",
    80: "Hg",
    81: "Tl",
    82: "Pb",
    83: "Bi",
}


def particle_from_name(path: Path) -> str:
    match = re.match(r"Background_([^_]+)_", path.name)
    return match.group(1) if match else "unknown"


def nuclide(za: int) -> str:
    z, a = divmod(za, 1000)
    symbol = ELEMENTS.get(z, f"Z{z}")
    return f"{symbol}-{a}"


def parse_dat(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    volume = ""
    particle = particle_from_name(path)
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line in {"EN"} or line.startswith("TT "):
            continue
        if line.startswith("VN "):
            volume = line[3:].strip()
            continue
        if line.startswith("RP "):
            parts = line.split()
            if len(parts) < 4:
                continue
            za = int(parts[1])
            exc_keV = float(parts[2])
            value = float(parts[3])
            rows.append(
                {
                    "particle": particle,
                    "volume": volume,
                    "za": za,
                    "nuclide": nuclide(za),
                    "exc_keV": exc_keV,
                    "value": value,
                    "file": path.name,
                }
            )
    return rows


def top(counter: Counter[tuple[str, ...]], limit: int = 20) -> list[dict[str, object]]:
    rows = []
    for key, value in counter.most_common(limit):
        row = {f"k{i}": part for i, part in enumerate(key)}
        row["value"] = value
        rows.append(row)
    return rows


def main() -> None:
    all_rows: list[dict[str, object]] = []
    for path in sorted(RUN_DIR.glob("*.dat.inc1.dat")):
        all_rows.extend(parse_dat(path))

    added_rows = [
        row for row in all_rows if str(row["volume"]).startswith(ADDED_PREFIXES)
    ]
    w_rows = [
        row for row in added_rows if str(row["volume"]).startswith("HybridW_Prompt511_")
    ]
    csi_rows = [
        row
        for row in added_rows
        if str(row["volume"]).startswith("CsI_HybridUpperShroud_Prompt511_")
    ]

    all_total_value = sum(float(row["value"]) for row in all_rows)
    added_total_value = sum(float(row["value"]) for row in added_rows)

    all_by_volume = Counter()
    all_by_nuclide = Counter()
    for row in all_rows:
        value = float(row["value"])
        all_by_volume[(str(row["volume"]),)] += value
        all_by_nuclide[(str(row["nuclide"]),)] += value

    by_family = Counter()
    by_particle = Counter()
    by_volume = Counter()
    by_nuclide = Counter()
    by_particle_nuclide = Counter()
    for row in added_rows:
        volume = str(row["volume"])
        family = "Hybrid W" if volume.startswith("HybridW_") else "Hybrid CsI"
        value = float(row["value"])
        by_family[(family,)] += value
        by_particle[(str(row["particle"]),)] += value
        by_volume[(volume,)] += value
        by_nuclide[(str(row["nuclide"]),)] += value
        by_particle_nuclide[(str(row["particle"]), str(row["nuclide"]))] += value

    summary = {
        "claim_level": "buildup isotope-store smoke on added volumes only; not delayed-rate authority",
        "run_dir": str(RUN_DIR.relative_to(ROOT)),
        "dat_files": len(list(RUN_DIR.glob("*.dat.inc1.dat"))),
        "all_rp_rows": len(all_rows),
        "added_volume_rp_rows": len(added_rows),
        "all_total_value": all_total_value,
        "added_volume_total_value": added_total_value,
        "added_volume_fraction_of_all": added_total_value / all_total_value
        if all_total_value
        else None,
        "hybrid_w_rows": len(w_rows),
        "hybrid_w_total_value": sum(float(row["value"]) for row in w_rows),
        "hybrid_csi_rows": len(csi_rows),
        "hybrid_csi_total_value": sum(float(row["value"]) for row in csi_rows),
        "top_added_families": top(by_family, 10),
        "top_added_particles": top(by_particle, 10),
        "top_added_volumes": top(by_volume, 20),
        "top_added_nuclides": top(by_nuclide, 20),
        "top_added_particle_nuclides": top(by_particle_nuclide, 20),
        "top_all_volumes": top(all_by_volume, 20),
        "top_all_nuclides": top(all_by_nuclide, 20),
        "limitations": [
            "Values are smoke-run isotope-store counts from the DAT RP records.",
            "No isotope half-life folding, RPIP source build, delayed transport, or day-20 rate is inferred.",
            "Only added HybridW_Prompt511_* and CsI_HybridUpperShroud_Prompt511_* volumes are summarized.",
        ],
    }

    OUT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    lines = [
        "# Hybrid W/CsI Shroud Isotope-Store Smoke Summary",
        "",
        "This summarizes only added prompt-511 hybrid volumes from the buildup DAT RP records.",
        "It is not a delayed-source or delayed-rate authority.",
        "",
        f"- DAT files: `{summary['dat_files']}`",
        f"- all RP rows: `{summary['all_rp_rows']}`",
        f"- all-volume total smoke value: `{summary['all_total_value']:.6g}`",
        f"- added-volume RP rows: `{summary['added_volume_rp_rows']}`",
        f"- added-volume total smoke value: `{summary['added_volume_total_value']:.6g}`",
        f"- added-volume fraction of all smoke value: `{summary['added_volume_fraction_of_all']:.3%}`",
        f"- Hybrid W smoke value: `{summary['hybrid_w_total_value']:.6g}`",
        f"- Hybrid CsI smoke value: `{summary['hybrid_csi_total_value']:.6g}`",
        "",
        "## Added Families",
        "",
        "| family | value |",
        "|---|---:|",
    ]
    for row in summary["top_added_families"]:
        lines.append(f"| {row['k0']} | {row['value']:.6g} |")

    lines += [
        "",
        "## Top Added Particles",
        "",
        "| particle | value |",
        "|---|---:|",
    ]
    for row in summary["top_added_particles"]:
        lines.append(f"| {row['k0']} | {row['value']:.6g} |")

    lines += [
        "",
        "## Top Added Nuclides",
        "",
        "| nuclide | value |",
        "|---|---:|",
    ]
    for row in summary["top_added_nuclides"][:12]:
        lines.append(f"| {row['k0']} | {row['value']:.6g} |")

    lines += [
        "",
        "## Top Added Volumes",
        "",
        "| volume | value |",
        "|---|---:|",
    ]
    for row in summary["top_added_volumes"][:12]:
        lines.append(f"| {row['k0']} | {row['value']:.6g} |")

    lines += [
        "",
        "## Limitations",
        "",
    ]
    for item in summary["limitations"]:
        lines.append(f"- {item}")

    OUT_MD.write_text("\n".join(lines) + "\n")
    print(json.dumps({"summary_json": str(OUT_JSON), "summary_md": str(OUT_MD)}, indent=2))


if __name__ == "__main__":
    main()
