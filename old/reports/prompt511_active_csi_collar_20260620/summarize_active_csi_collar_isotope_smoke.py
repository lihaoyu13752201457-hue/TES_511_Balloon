#!/usr/bin/env python3
"""Summarize added-volume isotope records for the active-CsI collar smoke."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_DIR = ROOT / "runs" / "active_csi_collar_buildup_isotope_g1m_r2"
OUT_JSON = ROOT / "prompt511_active_csi_collar_isotope_smoke_summary.json"
OUT_MD = ROOT / "prompt511_active_csi_collar_isotope_smoke_summary.md"

ADDED_PREFIX = "CsI_Active_Shield_Prompt511_Collar_"

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
    return f"{ELEMENTS.get(z, f'Z{z}')}-{a}"


def parse_dat(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    volume = ""
    particle = particle_from_name(path)
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line == "EN" or line.startswith("TT "):
            continue
        if line.startswith("VN "):
            volume = line[3:].strip()
            continue
        if line.startswith("RP "):
            parts = line.split()
            if len(parts) < 4:
                continue
            za = int(parts[1])
            rows.append(
                {
                    "particle": particle,
                    "volume": volume,
                    "za": za,
                    "nuclide": nuclide(za),
                    "exc_keV": float(parts[2]),
                    "value": float(parts[3]),
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


def main() -> int:
    all_rows: list[dict[str, object]] = []
    for path in sorted(RUN_DIR.glob("*.dat.inc1.dat")):
        all_rows.extend(parse_dat(path))

    added_rows = [row for row in all_rows if str(row["volume"]).startswith(ADDED_PREFIX)]
    all_total = sum(float(row["value"]) for row in all_rows)
    added_total = sum(float(row["value"]) for row in added_rows)

    by_particle: Counter[tuple[str, ...]] = Counter()
    by_volume: Counter[tuple[str, ...]] = Counter()
    by_nuclide: Counter[tuple[str, ...]] = Counter()
    by_particle_nuclide: Counter[tuple[str, ...]] = Counter()
    for row in added_rows:
        value = float(row["value"])
        by_particle[(str(row["particle"]),)] += value
        by_volume[(str(row["volume"]),)] += value
        by_nuclide[(str(row["nuclide"]),)] += value
        by_particle_nuclide[(str(row["particle"]), str(row["nuclide"]))] += value

    summary = {
        "claim_level": "buildup isotope-store smoke on added active-CsI collar volumes only; not delayed-rate authority",
        "run_dir": str(RUN_DIR.relative_to(ROOT)),
        "dat_files": len(list(RUN_DIR.glob("*.dat.inc1.dat"))),
        "all_rp_rows": len(all_rows),
        "all_total_value": all_total,
        "added_volume_rp_rows": len(added_rows),
        "added_volume_total_value": added_total,
        "added_volume_fraction_of_all": added_total / all_total if all_total else None,
        "top_added_particles": top(by_particle, 10),
        "top_added_volumes": top(by_volume, 12),
        "top_added_nuclides": top(by_nuclide, 12),
        "top_added_particle_nuclides": top(by_particle_nuclide, 12),
        "limitations": [
            "Values are smoke-run isotope-store counts from DAT RP records.",
            "No half-life folding, RPIP delayed source build, delayed transport, or day-20 rate is inferred.",
            "Only added CsI_Active_Shield_Prompt511_Collar_* volumes are summarized.",
        ],
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    frac = summary["added_volume_fraction_of_all"]
    lines = [
        "# Active-CsI Collar Isotope-Store Smoke Summary",
        "",
        "This summarizes only added active-CsI collar volumes from buildup DAT RP records.",
        "It is not a delayed-source or delayed-rate authority.",
        "",
        f"- DAT files: `{summary['dat_files']}`",
        f"- all RP rows: `{summary['all_rp_rows']}`",
        f"- all-volume total smoke value: `{summary['all_total_value']:.6g}`",
        f"- added-volume RP rows: `{summary['added_volume_rp_rows']}`",
        f"- added-volume total smoke value: `{summary['added_volume_total_value']:.6g}`",
        f"- added-volume fraction of all smoke value: `{frac:.3%}`" if frac is not None else "- added-volume fraction of all smoke value: `n/a`",
        "",
        "## Top Added Particles",
        "",
        "| particle | value |",
        "|---|---:|",
    ]
    for row in summary["top_added_particles"]:
        lines.append(f"| {row['k0']} | {row['value']:.6g} |")

    lines += ["", "## Top Added Nuclides", "", "| nuclide | value |", "|---|---:|"]
    for row in summary["top_added_nuclides"]:
        lines.append(f"| {row['k0']} | {row['value']:.6g} |")

    lines += ["", "## Top Added Volumes", "", "| volume | value |", "|---|---:|"]
    for row in summary["top_added_volumes"]:
        lines.append(f"| {row['k0']} | {row['value']:.6g} |")

    lines += ["", "## Limitations", ""]
    for item in summary["limitations"]:
        lines.append(f"- {item}")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"summary_json": str(OUT_JSON), "summary_md": str(OUT_MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
