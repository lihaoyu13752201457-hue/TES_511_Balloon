#!/usr/bin/env python3
"""Build EXPACS/PARMA 511-keV line-gap evidence figures and tables."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
SOURCE_CARD = ROOT / "expacs_fullsphere_20bin_sources/Background_atm_fullsphere_allparticles_20bins.source"
SPECTRA_DIR = ROOT / "expacs_fullsphere_20bin_sources/cosima_spectra"
E_LINE = 511.0
W2_LO = 510.58
W2_HI = 511.42
PROJECT_HARRIS_RC11_13_FLUX = 4.38e-2 * 0.532


def read_spectrum(path: Path) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            rows.append((float(parts[0]), float(parts[1])))
    return rows


def interp(x: float, rows: list[tuple[float, float]]) -> tuple[float, float, float, float, float]:
    for (x0, y0), (x1, y1) in zip(rows, rows[1:]):
        if x0 <= x <= x1:
            frac = (x - x0) / (x1 - x0)
            return x0, y0, x1, y1, y0 + frac * (y1 - y0)
    raise ValueError(f"{x} outside spectrum range")


def integrated_linear(a: float, b: float, x0: float, y0: float, x1: float, y1: float) -> float:
    slope = (y1 - y0) / (x1 - x0)

    def anti(x: float) -> float:
        dx = x - x0
        return y0 * dx + 0.5 * slope * dx * dx

    return anti(b) - anti(a)


def parse_gamma_sources() -> list[dict[str, object]]:
    text = SOURCE_CARD.read_text(encoding="utf-8")
    entries: dict[str, dict[str, object]] = {}
    source_re = re.compile(r"^(Atm_gamma_bin(\d{2})_(down|up))\.(Beam|Spectrum|Flux)\s+(.+)$")
    for raw in text.splitlines():
        match = source_re.match(raw.strip())
        if not match:
            continue
        name, bin_id, hemi, field, value = match.groups()
        entry = entries.setdefault(name, {"name": name, "bin": int(bin_id), "hemisphere": hemi})
        if field == "Beam":
            parts = value.split()
            entry["theta0_deg"] = float(parts[1])
            entry["theta1_deg"] = float(parts[2])
            entry["phi0_deg"] = float(parts[3])
            entry["phi1_deg"] = float(parts[4])
        elif field == "Spectrum":
            entry["spectrum"] = value.split()[-1]
        elif field == "Flux":
            entry["flux_ph_cm2_s"] = float(value)
    return [entries[key] for key in sorted(entries, key=lambda k: int(re.search(r"bin(\d{2})", k).group(1)))]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gamma_sources = parse_gamma_sources()

    bin00_path = SPECTRA_DIR / "gamma_bin00_theta18.19_pdf.dat"
    bin00 = read_spectrum(bin00_path)
    x0, y0, x1, y1, y511 = interp(E_LINE, bin00)
    w2_pdf_integral = integrated_linear(W2_LO, W2_HI, x0, y0, x1, y1)
    bin00_flux = float(gamma_sources[0]["flux_ph_cm2_s"])

    excerpt_rows = []
    for e, pdf in bin00:
        if 300 <= e <= 750:
            excerpt_rows.append(
                {
                    "energy_keV": f"{e:.2f}",
                    "pdf_per_keV": f"{pdf:.12e}",
                    "status": "EXPACS_table_point",
                }
            )
    excerpt_rows.append(
        {
            "energy_keV": f"{E_LINE:.2f}",
            "pdf_per_keV": f"{y511:.12e}",
            "status": "linear_interpolation_only_not_table_point",
        }
    )
    excerpt_rows = sorted(excerpt_rows, key=lambda row: float(row["energy_keV"]))
    write_csv(OUT / "gamma_bin00_theta18p19_excerpt_around_511.csv", excerpt_rows)

    weight_rows: list[dict[str, object]] = []
    raw_weight_sum = 0.0
    for src in gamma_sources:
        spectrum = read_spectrum(SPECTRA_DIR / Path(str(src["spectrum"])).name)
        bx0, by0, bx1, by1, by511 = interp(E_LINE, spectrum)
        raw = float(src["flux_ph_cm2_s"]) * by511
        raw_weight_sum += raw
        weight_rows.append(
            {
                "bin": int(src["bin"]),
                "hemisphere": str(src["hemisphere"]),
                "theta0_deg": f"{float(src['theta0_deg']):.3f}",
                "theta1_deg": f"{float(src['theta1_deg']):.3f}",
                "expacs_gamma_flux_ph_cm2_s": f"{float(src['flux_ph_cm2_s']):.12e}",
                "pdf_interp_at_511_per_keV": f"{by511:.12e}",
                "continuum_differential_flux_at_511_ph_cm2_s_keV": f"{raw:.12e}",
                "source_name": str(src["name"]),
            }
        )
    for row in weight_rows:
        raw = float(row["continuum_differential_flux_at_511_ph_cm2_s_keV"])
        weight = raw / raw_weight_sum
        row["expacs_continuum_angular_weight_at_511"] = f"{weight:.12e}"
        row["mono511_flux_if_total_1_ph_cm2_s"] = f"{weight:.12e}"
        row["mono511_flux_if_project_harris_Rc11_13"] = f"{weight * PROJECT_HARRIS_RC11_13_FLUX:.12e}"
    write_csv(OUT / "expacs_gamma_511_interpolated_angular_weights.csv", weight_rows)

    energies = [e for e, _ in bin00 if 250 <= e <= 900]
    pdfs = [p for e, p in bin00 if 250 <= e <= 900]

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.0), dpi=180)
    ax = axes[0]
    ax.plot(energies, pdfs, marker="o", color="#275f8f", lw=1.8, ms=4, label="EXPACS gamma PDF table")
    ax.axvspan(W2_LO, W2_HI, color="#e2b93b", alpha=0.25, label="W2 510.58-511.42 keV")
    ax.axvline(E_LINE, color="#b12626", lw=1.8, label="511 keV")
    ax.set_yscale("log")
    ax.set_xlabel("Energy (keV)")
    ax.set_ylabel("PDF (keV$^{-1}$)")
    ax.set_title("EXPACS gamma bin00 table has no 511-keV point")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="lower left", fontsize=8)

    ax = axes[1]
    ax.plot([x0, x1], [y0, y1], color="#275f8f", lw=2.4, label="linear interpolation segment")
    ax.scatter([x0, x1], [y0, y1], color="#275f8f", s=48, zorder=3, label="table points")
    ax.scatter([E_LINE], [y511], facecolor="white", edgecolor="#111111", s=65, zorder=4, label="interpolated continuum at 511")
    spike_top = max(y0, y1) * 1.7
    ax.vlines(E_LINE, y511, spike_top, color="#b12626", lw=3.0)
    ax.annotate(
        "missing atmospheric\nmono-511 line\n(add separate source)",
        xy=(E_LINE, spike_top),
        xytext=(520, spike_top * 1.03),
        arrowprops={"arrowstyle": "->", "color": "#b12626", "lw": 1.2},
        color="#b12626",
        fontsize=9,
        ha="left",
        va="bottom",
    )
    ax.axvspan(W2_LO, W2_HI, color="#e2b93b", alpha=0.22)
    ax.set_xlim(430, 585)
    ax.set_ylim(min(y0, y1) * 0.92, spike_top * 1.22)
    ax.set_xlabel("Energy (keV)")
    ax.set_ylabel("PDF (keV$^{-1}$)")
    ax.set_title("449.65 -> 566.08 keV interpolation skips the line")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", fontsize=8)

    fig.suptitle("EXPACS/PARMA continuum is not an atmospheric 511-keV line model", y=1.02, fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT / "expacs_gamma_bin00_511_gap.png", bbox_inches="tight")
    fig.savefig(OUT / "expacs_gamma_bin00_511_gap.svg", bbox_inches="tight")
    plt.close(fig)

    source_lines = [
        "# Example only: keep the original EXPACS continuum source unchanged.",
        "# Add a separate mono-511 source for each angular bin.",
        "# Replace L00_PH_CM2_S with the selected atmospheric-line model value.",
        "",
        "BalloonPrompt.Source Atm511_gamma_bin00_down",
        "",
        "Atm511_gamma_bin00_down.ParticleType 1",
        "Atm511_gamma_bin00_down.Beam FarFieldAreaSource 0.000 25.842 0.000 360.000",
        "Atm511_gamma_bin00_down.Spectrum Mono 511",
        "Atm511_gamma_bin00_down.Flux L00_PH_CM2_S",
        "",
        "# If using the EXPACS-continuum angular-shape diagnostic:",
        f"# L00_PH_CM2_S = F511_TOTAL * {float(weight_rows[0]['expacs_continuum_angular_weight_at_511']):.12e}",
        f"# For the project Harris Rc~11-13 placeholder F511_TOTAL={PROJECT_HARRIS_RC11_13_FLUX:.8e},",
        f"# L00_PH_CM2_S = {float(weight_rows[0]['mono511_flux_if_project_harris_Rc11_13']):.12e}",
    ]
    (OUT / "mono511_supplement_bin00_source_snippet.source").write_text("\n".join(source_lines) + "\n", encoding="utf-8")

    unit_lines = [
        "# Full-sphere atmospheric 511-keV supplement template.",
        "# Diagnostic angular model: distribute total line flux by the EXPACS gamma",
        "# continuum angular shape interpolated at 511 keV.",
        "# The Flux values below sum to 1.0 ph cm^-2 s^-1.",
        "# Scale the final detector transfer by the chosen physical F511_TOTAL.",
        "",
    ]
    for row in weight_rows:
        name = f"Atm511_weighted_bin{int(row['bin']):02d}_{row['hemisphere']}"
        unit_lines.append(f"Atm511FullSphereUnit.Source {name}")
    unit_lines.append("")
    for row in weight_rows:
        name = f"Atm511_weighted_bin{int(row['bin']):02d}_{row['hemisphere']}"
        unit_lines.extend(
            [
                f"{name}.ParticleType 1",
                (
                    f"{name}.Beam FarFieldAreaSource {float(row['theta0_deg']):.3f} "
                    f"{float(row['theta1_deg']):.3f} 0.000 360.000"
                ),
                f"{name}.Spectrum Mono 511",
                f"{name}.Flux {float(row['mono511_flux_if_total_1_ph_cm2_s']):.12e}",
                "",
            ]
        )
    (OUT / "mono511_fullsphere_expacs_weighted_unit_sources.source").write_text(
        "\n".join(unit_lines) + "\n", encoding="utf-8"
    )

    md = f"""# EXPACS Gamma 511-keV Line Gap Evidence

This evidence package uses one local EXPACS/PARMA gamma spectrum:
`expacs_fullsphere_20bin_sources/cosima_spectra/gamma_bin00_theta18.19_pdf.dat`.

## What the table shows

For gamma angular bin00 (`theta=0.000--25.842 deg`), the EXPACS gamma PDF table has
the following local points around 511 keV:

| Energy keV | PDF keV^-1 | Status |
|---:|---:|---|
| 357.17 | 2.9376372290e-04 | EXPACS table point |
| 449.65 | 1.5142116335e-04 | EXPACS table point |
| 511.00 | {y511:.10e} | linear interpolation only, not a table point |
| 566.08 | 1.6759094943e-04 | EXPACS table point |
| 712.64 | 2.9600557973e-05 | EXPACS table point |

The 511-keV atmospheric annihilation line is therefore not represented as a
line feature in this spectrum. It is only a continuum interpolation between
449.65 and 566.08 keV.

For bin00, the original EXPACS gamma source-card flux is `{bin00_flux:.12e}`
ph cm^-2 s^-1. The interpolated continuum differential flux at 511 keV is
`{bin00_flux * y511:.12e}` ph cm^-2 s^-1 keV^-1, and the continuum integral over
W2 (`510.58--511.42 keV`) is `{bin00_flux * w2_pdf_integral:.12e}` ph cm^-2 s^-1.

## How to supplement

Do not insert the atmospheric 511-keV line into the continuous PDF as another
linear-interpolation point unless an artificial finite line width is explicitly
being modeled. For transport, add a separate mono-energetic source per angular
bin:

```text
BalloonPrompt.Source Atm511_gamma_bin00_down

Atm511_gamma_bin00_down.ParticleType 1
Atm511_gamma_bin00_down.Beam FarFieldAreaSource 0.000 25.842 0.000 360.000
Atm511_gamma_bin00_down.Spectrum Mono 511
Atm511_gamma_bin00_down.Flux L00_PH_CM2_S
```

For all 20 bins, choose line fluxes `L_i` from an atmospheric 511-keV model such
that `sum_i L_i = F511_TOTAL`. The file
`expacs_gamma_511_interpolated_angular_weights.csv` provides one diagnostic
choice where `L_i` is distributed by the EXPACS gamma continuum angular shape at
511 keV. This is a repair heuristic, not a literature-derived angular model.

## Outputs

- `expacs_gamma_bin00_511_gap.png`
- `expacs_gamma_bin00_511_gap.svg`
- `gamma_bin00_theta18p19_excerpt_around_511.csv`
- `expacs_gamma_511_interpolated_angular_weights.csv`
- `mono511_supplement_bin00_source_snippet.source`
- `mono511_fullsphere_expacs_weighted_unit_sources.source`
"""
    (OUT / "README.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
