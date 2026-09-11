#!/usr/bin/env python3
"""Convert archived two-column tables into MEGAlib MFunction DP format.

The full-sphere archive contains spectra whose public `cosima_spectra/` tables
were converted to keV.  The February 2602 workflow, however, passed the EXPACS
energy column to Cosima unchanged.  For 2605 "same statistics, extended
geometry" production we therefore keep both versions:

- `cosima_spectra_dp/`: archived keV axis, retained for audit;
- `cosima_spectra_dp_2602units/`: energy axis divided by 1000, matching the
  2602 source-file convention used by `megalib_sources_v2`.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def numeric_rows(path: Path) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        if len(parts) < 2:
            continue
        rows.append((float(parts[0]), float(parts[1])))
    if len(rows) < 2:
        raise ValueError(f"Need at least two numeric rows in {path}")
    return rows


def write_dp(path: Path, rows: list[tuple[float, float]], *, header: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if header:
        lines.extend(header)
    lines.append("IP LIN")
    lines.extend(f"DP {x:.10e} {y:.10e}" for x, y in rows)
    lines.append("EN")
    path.write_text("\n".join(lines) + "\n")


def convert_spectra() -> int:
    src_dir = ROOT / "expacs_fullsphere_20bin_sources" / "cosima_spectra"
    dst_dir = ROOT / "expacs_fullsphere_20bin_sources" / "cosima_spectra_dp"
    legacy_dir = ROOT / "expacs_fullsphere_20bin_sources" / "cosima_spectra_dp_2602units"
    n = 0
    for src in sorted(src_dir.glob("*.dat")):
        rows = numeric_rows(src)
        write_dp(dst_dir / src.name, rows)
        legacy_rows = [(x / 1000.0, y) for x, y in rows]
        write_dp(
            legacy_dir / src.name,
            legacy_rows,
            header=[
                "# 2602-compatible energy axis: archived keV values divided by 1000.",
                "# This matches /home/ubuntu/cosmosray_bg_2602/megalib_sources_v2 inputs.",
            ],
        )
        n += 1
    return n


def convert_lightcurves() -> int:
    src_dir = ROOT / "time_variable_balloon_background_curves_verified" / "lightcurves"
    dst_dir = ROOT / "time_variable_balloon_background_curves_verified" / "lightcurves_dp"
    n = 0
    for src in sorted(src_dir.glob("*.lc")):
        write_dp(dst_dir / src.name, numeric_rows(src))
        n += 1
    return n


def main() -> int:
    spectra = convert_spectra()
    lightcurves = convert_lightcurves()
    print(f"converted spectra={spectra}")
    print(f"converted lightcurves={lightcurves}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
