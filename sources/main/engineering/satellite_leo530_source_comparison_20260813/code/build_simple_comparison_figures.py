#!/usr/bin/env python3
"""Build a compact four-figure readout from the validated comparison tables."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "tes511_mplconfig"))
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle  # noqa: E402


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TABLE_ROOT = PACKAGE_ROOT / "outputs" / "tables"
SIMPLE_ROOT = PACKAGE_ROOT / "outputs" / "simple"
FIGURE_ROOT = SIMPLE_ROOT / "figures"
SIMPLE_TABLE_ROOT = SIMPLE_ROOT / "tables"

BALLOON = "#2369BD"
LEO = "#E07A1F"
TEXT = "#1F2933"
MUTED = "#5B6670"
GRID = "#D5DADE"

GAMMA_BANDS = (
    ("100_300_keV", "100–300 keV"),
    ("300_450_keV", "300–450 keV"),
    ("450_600_keV_annihilation_region_proxy", "450–600 keV†"),
    ("600_1000_keV", "600–1000 keV"),
    ("1_10_MeV", "1–10 MeV"),
)

MATRIX_BANDS = (
    ("1_10_MeV", "1–10\nMeV"),
    ("10_100_MeV", "10–100\nMeV"),
    ("100_MeV_1_GeV", "0.1–1\nGeV"),
    ("1_100_GeV", "1–100\nGeV"),
)

MATRIX_FAMILIES = (
    ("n", "Neutron*"),
    ("p", "Proton"),
    ("alpha", "Alpha"),
    ("eminus", "Electron"),
    ("eplus", "Positron"),
    ("muon", "Muon ±"),
)

SOURCE_TABLES = (
    "environment_contrasts.csv",
    "balloon_aggregated_spectra.csv",
    "balloon_angular_spectra_long.csv",
    "satellite_profile_spectra.csv",
    "satellite_line_components.csv",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def require_validated_inputs() -> dict:
    validation_path = PACKAGE_ROOT / "data" / "validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if validation.get("status") != "PASS":
        raise RuntimeError("Base source-input comparison does not have PASS validation")
    recorded = validation.get("output_sha256", {})
    for filename in SOURCE_TABLES:
        path = TABLE_ROOT / filename
        relative = str(path.relative_to(PACKAGE_ROOT))
        if relative not in recorded:
            raise RuntimeError(f"Base validation did not pin {relative}")
        actual = sha256(path)
        if actual != recorded[relative]:
            raise RuntimeError(f"Validated source table changed: {relative}")
    return validation


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 220,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10.5,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.alpha": 0.65,
            "grid.linestyle": ":",
        }
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE_ROOT / f"{stem}.png", bbox_inches="tight", facecolor="white")
    fig.savefig(FIGURE_ROOT / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def unique_curve(rows: list[dict[str, str]], energy_field: str, value_field: str) -> tuple[np.ndarray, np.ndarray]:
    grouped: dict[float, list[float]] = {}
    for row in rows:
        raw_value = row[value_field]
        if raw_value == "":
            continue
        energy = float(row[energy_field])
        value = float(raw_value)
        if math.isfinite(energy) and math.isfinite(value) and energy > 0 and value > 0:
            grouped.setdefault(energy, []).append(value)
    energy = np.asarray(sorted(grouped))
    values = np.asarray([float(np.mean(grouped[item])) for item in energy])
    return energy, values


def contrast_lookup(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        key = (row["family"], row["band"])
        if key in lookup:
            raise RuntimeError(f"Duplicate environment contrast row: {key}")
        lookup[key] = row
    return lookup


def plot_incident_component_spectra(line_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    component_rows = read_csv(TABLE_ROOT / "satellite_component_spectra.csv")
    balloon_rows = read_csv(TABLE_ROOT / "balloon_aggregated_spectra.csv")
    line_fluxes = [
        float(row["physical_line_flux_cm2_s"])
        for row in line_rows
        if row["component_id"] == "atmospheric_511_line"
    ]
    if len(line_fluxes) != 1:
        raise RuntimeError("Expected exactly one atmospheric mono-511 row")

    satellite_specs = (
        ("Cosmic photons", "gamma", "#1F77B4", "-", "cosmic_photons"),
        ("Albedo photons", "gamma", "#1F77B4", "--", "albedo_photons_continuum"),
        ("Primary protons", "p", "#2CA02C", "-", "primary_proton"),
        ("Secondary protons", "p", "#2CA02C", "--", "secondary_proton"),
        ("Primary alpha", "alpha", "#7A8B22", ":", "primary_alpha"),
        ("Primary electrons", "eminus", "#E07A1F", "-", "primary_electron"),
        ("Secondary electrons", "eminus", "#E07A1F", "--", "secondary_electron"),
        ("Primary positrons", "eplus", "#CC5C91", "-", "primary_positron"),
        ("Secondary positrons", "eplus", "#CC5C91", "--", "secondary_positron"),
        ("Albedo neutrons (10-GV proxy)*", "n", "#6F42C1", "-.", "albedo_neutrons_10gv_proxy"),
    )
    balloon_style = {
        "gamma": ("Gamma total broadband", "#1F77B4", "-"),
        "p": ("Proton", "#2CA02C", "-"),
        "alpha": ("Alpha", "#7A8B22", ":"),
        "eminus": ("Electron", "#E07A1F", "-"),
        "eplus": ("Positron", "#CC5C91", "--"),
        "n": ("Neutron", "#6F42C1", "-."),
        "muminus": ("Muon −", "#7F7F7F", "-."),
        "muplus": ("Muon +", "#7F7F7F", ":"),
    }

    fig, axes = plt.subplots(1, 2, figsize=(14.0, 5.8), sharex=True, sharey=True)
    chart_rows: list[dict[str, object]] = []

    for label, family, color, style, component_id in satellite_specs:
        rows = [
            row
            for row in component_rows
            if row["component_id"] == component_id and row["within_cited_model_validity"].lower() == "true"
        ]
        energy_keV, intensity_keV = unique_curve(
            rows, "energy_keV_total", "support_avg_intensity_cm2_s_sr_keV"
        )
        energy = energy_keV / 1000.0
        value = intensity_keV * 1000.0
        mask = (energy >= 0.1) & (energy <= 1.0e6) & (value >= 1.0e-16)
        if np.any(mask):
            axes[0].loglog(energy[mask], value[mask], color=color, ls=style, lw=1.65, label=label)
        in_range = (energy >= 0.1) & (energy <= 1.0e6)
        for current_energy, current_value in zip(energy[in_range], value[in_range]):
            chart_rows.append(
                {
                    "environment": "satellite_leo530_proxy",
                    "component": label,
                    "family": family,
                    "energy_MeV_total": current_energy,
                    "support_avg_intensity_cm2_s_sr_MeV": current_value,
                    "plotted_above_display_floor": current_value >= 1.0e-16,
                    "activation_or_delayed": False,
                }
            )
    line_omega = float(line_rows[0]["solid_angle_sr"])
    axes[0].axvline(0.511, color="#222222", lw=1.25, ls=":", label="Atmospheric mono-511 (position only)")
    axes[0].text(
        0.03,
        0.04,
        f"Mono-511 integrated intensity: {line_fluxes[0] / line_omega:.6f} "
        "cm$^{-2}$ s$^{-1}$ sr$^{-1}$\n"
        "Line position only; no arbitrary differential height is assigned.",
        transform=axes[0].transAxes,
        ha="left",
        va="bottom",
        fontsize=8.1,
        color=MUTED,
        bbox={"facecolor": "white", "edgecolor": "#D6D6D6", "alpha": 0.92, "pad": 3},
    )

    for family, (label, color, style) in balloon_style.items():
        selected = [row for row in balloon_rows if row["family"] == family and row["domain"] == "full"]
        energy_keV, intensity_keV = unique_curve(
            selected, "energy_keV_total", "support_avg_intensity_cm2_s_sr_keV"
        )
        energy = energy_keV / 1000.0
        value = intensity_keV * 1000.0
        mask = (energy >= 0.1) & (energy <= 1.0e6) & (value >= 1.0e-16)
        axes[1].loglog(energy[mask], value[mask], color=color, ls=style, lw=1.65, label=label)
        in_range = (energy >= 0.1) & (energy <= 1.0e6)
        for current_energy, current_value in zip(energy[in_range], value[in_range]):
            chart_rows.append(
                {
                    "environment": "balloon_38km",
                    "component": label,
                    "family": family,
                    "energy_MeV_total": current_energy,
                    "support_avg_intensity_cm2_s_sr_MeV": current_value,
                    "plotted_above_display_floor": current_value >= 1.0e-16,
                    "activation_or_delayed": False,
                }
            )

    for ax, title in zip(axes, ("530-km near-equatorial LEO proxy", "38-km corrected balloon field")):
        ax.set_xlim(0.1, 1.0e6)
        ax.set_ylim(1.0e-16, 5.0)
        ax.set_xlabel("Total kinetic energy [MeV]")
        ax.set_title(title, fontsize=12.2)
        ax.legend(loc="upper right", fontsize=6.8, ncol=1, frameon=True, framealpha=0.93)
    axes[0].set_ylabel(r"Support-average $dJ/dE$ [cm$^{-2}$ s$^{-1}$ sr$^{-1}$ MeV$^{-1}$]")
    axes[1].text(
        0.03,
        0.04,
        "Balloon gamma is a coarse broadband total with an annihilation bump;\n"
        "it is not a separately resolved mono-511 component.",
        transform=axes[1].transAxes,
        ha="left",
        va="bottom",
        fontsize=8.1,
        color=MUTED,
        bbox={"facecolor": "white", "edgecolor": "#D6D6D6", "alpha": 0.92, "pad": 3},
    )
    fig.suptitle("Prompt incident particle spectra — activation and delayed sources omitted", fontsize=15, weight="bold", y=0.985)
    fig.text(
        0.5,
        0.935,
        "Component layout follows the supplied CubeSat example, but the quantity is source flux rather than reconstructed Counts/keV/s; no cross-family total is drawn",
        ha="center",
        color=MUTED,
        fontsize=9.0,
    )
    fig.text(
        0.5,
        0.025,
        "Source-support average intensity; shared display floor 10⁻¹⁶ cm⁻² s⁻¹ sr⁻¹ MeV⁻¹; * neutron is a diagnostic 10-GV fallback; LEO SAA and Galactic diffuse are excluded",
        ha="center",
        color=MUTED,
        fontsize=8.4,
    )
    fig.tight_layout(rect=(0.02, 0.065, 0.99, 0.91))
    save_figure(fig, "simple_00_incident_component_spectra")
    return chart_rows


def plot_gamma_summary(contrasts: list[dict[str, str]], line_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    balloon_rows = [
        row
        for row in read_csv(TABLE_ROOT / "balloon_aggregated_spectra.csv")
        if row["family"] == "gamma" and row["domain"] == "full"
    ]
    leo_rows = [
        row
        for row in read_csv(TABLE_ROOT / "satellite_profile_spectra.csv")
        if row["family"] == "gamma" and row["profile"] == "satellite_nominal_continuum"
    ]
    native_knots = np.asarray(
        sorted(
            {
                float(row["energy_keV_total"])
                for row in read_csv(TABLE_ROOT / "balloon_angular_spectra_long.csv")
                if row["family"] == "gamma" and 300.0 <= float(row["energy_keV_total"]) <= 800.0
            }
        )
    )
    balloon_energy, balloon_value = unique_curve(
        balloon_rows, "energy_keV_total", "energy_weighted_flux_cm2_s"
    )
    leo_energy, leo_value = unique_curve(
        leo_rows, "energy_keV_total", "validity_filtered_energy_weighted_flux_cm2_s"
    )
    balloon_mask = (balloon_energy >= 100.0) & (balloon_energy <= 1.0e4)
    leo_mask = (leo_energy >= 100.0) & (leo_energy <= 1.0e4)

    lookup = contrast_lookup(contrasts)
    band_rows: list[dict[str, object]] = []
    for band_id, label in GAMMA_BANDS:
        row = lookup[("gamma", band_id)]
        if not row["satellite_to_balloon_ratio"]:
            raise RuntimeError(f"Selected gamma band unexpectedly unavailable: {band_id}")
        band_rows.append(
            {
                "band_id": band_id,
                "display_label": label,
                "balloon_flux_cm2_s": float(row["balloon_full_flux_cm2_s"]),
                "leo_flux_cm2_s": float(row["satellite_flux_cm2_s"]),
                "leo_to_balloon_ratio": float(row["satellite_to_balloon_ratio"]),
                "comparison_grade": row["comparison_grade"],
                "model_validity_coverage": row["satellite_model_validity_coverage"],
            }
        )

    line_fluxes = [
        float(row["physical_line_flux_cm2_s"])
        for row in line_rows
        if row["component_id"] == "atmospheric_511_line"
    ]
    if len(line_fluxes) != 1:
        raise RuntimeError("Expected exactly one atmospheric mono-511 row")
    line_flux = line_fluxes[0]

    fig, axes = plt.subplots(1, 2, figsize=(13.6, 5.4), gridspec_kw={"width_ratios": [1.22, 1.0]})
    ax = axes[0]
    ax.loglog(
        balloon_energy[balloon_mask],
        balloon_value[balloon_mask],
        color=BALLOON,
        lw=2.6,
        label="Balloon 38 km — full sphere",
    )
    ax.loglog(
        leo_energy[leo_mask],
        leo_value[leo_mask],
        color=LEO,
        lw=2.4,
        ls="--",
        label="LEO 530 km — nominal continuum",
    )
    ax.scatter(
        native_knots,
        np.interp(native_knots, balloon_energy, balloon_value),
        s=30,
        color=BALLOON,
        edgecolor="white",
        linewidth=0.8,
        zorder=4,
        label="Balloon native knots near 511 keV",
    )
    ax.axvspan(450.0, 600.0, color="#C84C4C", alpha=0.08)
    ax.axvline(511.0, color="#A33A3A", lw=1.25, ls=":")
    ax.annotate(
        f"LEO mono-511 integral\n{line_flux:.6f} cm$^{{-2}}$ s$^{{-1}}$",
        xy=(511.0, 0.90),
        xycoords=("data", "axes fraction"),
        xytext=(12, -5),
        textcoords="offset points",
        ha="left",
        va="top",
        color="#8C2D2D",
        fontsize=9,
        bbox={"facecolor": "white", "edgecolor": "#D9D9D9", "alpha": 0.92, "pad": 3},
    )
    ax.set_xlim(100.0, 1.0e4)
    ax.set_xlabel("Total kinetic energy [keV]")
    ax.set_ylabel(r"$E\,dF/dE$ [cm$^{-2}$ s$^{-1}$]")
    ax.set_title("Continuous gamma source")
    ax.legend(loc="lower left", frameon=True, framealpha=0.92)

    ax = axes[1]
    positions = np.arange(len(band_rows))[::-1]
    balloon_flux = np.asarray([row["balloon_flux_cm2_s"] for row in band_rows], dtype=float)
    leo_flux = np.asarray([row["leo_flux_cm2_s"] for row in band_rows], dtype=float)
    for y, first, second in zip(positions, balloon_flux, leo_flux):
        ax.hlines(y, min(first, second), max(first, second), color="#B9C0C5", lw=2.0, zorder=1)
    ax.scatter(balloon_flux, positions, s=68, color=BALLOON, edgecolor="white", lw=0.8, zorder=3)
    ax.scatter(leo_flux, positions, s=72, color=LEO, marker="D", edgecolor="white", lw=0.8, zorder=3)
    ax.set_yticks(positions, [row["display_label"] for row in band_rows])
    ax.set_xlim(0.0, max(max(balloon_flux), max(leo_flux)) * 1.32)
    ax.set_ylim(-0.6, len(band_rows) - 0.35)
    ax.set_xlabel(r"Band-integrated flux [cm$^{-2}$ s$^{-1}$]")
    ax.set_title("Gamma band integrals")
    ax.grid(axis="x")
    ax.grid(axis="y", visible=False)
    transform = ax.get_yaxis_transform()
    for y, row in zip(positions, band_rows):
        ax.text(
            0.985,
            y,
            f"{row['leo_to_balloon_ratio']:.2f}×",
            transform=transform,
            ha="right",
            va="center",
            color=TEXT,
            fontsize=9.3,
            weight="bold",
        )
    ax.text(
        0.985,
        1.02,
        "LEO / balloon",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        color=MUTED,
        fontsize=8.5,
    )
    ax.legend(
        handles=(
            Line2D([], [], color=BALLOON, marker="o", lw=0, markersize=7, label="Balloon"),
            Line2D([], [], color=LEO, marker="D", lw=0, markersize=6.5, label="LEO proxy"),
        ),
        loc="upper left",
        frameon=False,
    )

    fig.suptitle("Gamma source comparison in one view", fontsize=15, weight="bold", y=0.985)
    fig.text(
        0.5,
        0.935,
        "Angular-domain integrated incident flux; normal-science static LEO proxy; no orbit weighting or detector response",
        ha="center",
        color=MUTED,
        fontsize=9.2,
    )
    fig.text(
        0.5,
        0.025,
        "† 450–600 keV is a broad annihilation-region proxy. Its LEO integral includes the mono-511 line; the balloon table cannot isolate a narrow line.",
        ha="center",
        color=MUTED,
        fontsize=8.6,
    )
    fig.tight_layout(rect=(0.02, 0.07, 0.99, 0.91))
    save_figure(fig, "simple_01_gamma_source")
    return band_rows


def category_index(ratio: float) -> int:
    if ratio <= 0.1:
        return 0
    if ratio < 0.5:
        return 1
    if ratio <= 2.0:
        return 2
    if ratio <= 10.0:
        return 3
    return 4


def format_ratio(ratio: float) -> str:
    if ratio < 1.0e-3:
        return f"{ratio:.1e}×"
    if ratio < 0.1:
        return f"{ratio:.3f}×"
    if ratio < 10.0:
        return f"{ratio:.2f}×"
    return f"{ratio:.1f}×"


def plot_family_matrix(contrasts: list[dict[str, str]]) -> list[dict[str, object]]:
    lookup = contrast_lookup(contrasts)
    values = np.full((len(MATRIX_FAMILIES), len(MATRIX_BANDS)), np.nan)
    labels = np.full(values.shape, "NA", dtype=object)
    table_rows: list[dict[str, object]] = []

    for row_index, (family, family_label) in enumerate(MATRIX_FAMILIES):
        for column_index, (band_id, band_label) in enumerate(MATRIX_BANDS):
            if family == "muon":
                source = None
            else:
                source = lookup[(family, band_id)]
            ratio_text = "" if source is None else source["satellite_to_balloon_ratio"]
            if not ratio_text:
                validity = "unavailable" if family == "muon" else source["satellite_model_validity_coverage"]
                grade = "NA" if family == "muon" else source["comparison_grade"]
                table_rows.append(
                    {
                        "family": family,
                        "family_label": family_label,
                        "band_id": band_id,
                        "band_label": band_label.replace("\n", " "),
                        "leo_to_balloon_ratio": "",
                        "display_label": "NA",
                        "category": "NA",
                        "model_validity_coverage": validity,
                        "comparison_grade": grade,
                    }
                )
                continue

            ratio = float(ratio_text)
            category = category_index(ratio)
            values[row_index, column_index] = category
            marker = ""
            if source["satellite_model_validity_coverage"] == "partial_or_mixed":
                marker += "~"
            display = format_ratio(ratio) + marker
            labels[row_index, column_index] = display
            category_name = ("≤0.1", "0.1–0.5", "0.5–2", "2–10", ">10")[category]
            table_rows.append(
                {
                    "family": family,
                    "family_label": family_label,
                    "band_id": band_id,
                    "band_label": band_label.replace("\n", " "),
                    "leo_to_balloon_ratio": ratio,
                    "display_label": display,
                    "category": category_name,
                    "model_validity_coverage": source["satellite_model_validity_coverage"],
                    "comparison_grade": source["comparison_grade"],
                }
            )

    colors = ("#2166AC", "#92C5DE", "#F2F2F2", "#F4A261", "#C84E00")
    cmap = ListedColormap(colors)
    cmap.set_bad("#E4E7E9")
    masked = np.ma.masked_invalid(values)

    fig, ax = plt.subplots(figsize=(11.8, 7.0))
    ax.imshow(masked, cmap=cmap, vmin=-0.5, vmax=4.5, aspect="auto", interpolation="nearest")
    ax.set_xticks(np.arange(len(MATRIX_BANDS)), [label for _, label in MATRIX_BANDS])
    ax.set_yticks(np.arange(len(MATRIX_FAMILIES)), [label for _, label in MATRIX_FAMILIES])
    ax.tick_params(axis="x", length=0, pad=8)
    ax.tick_params(axis="y", length=0, pad=8)
    ax.set_xticks(np.arange(-0.5, len(MATRIX_BANDS), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(MATRIX_FAMILIES), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2.2)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for row_index in range(values.shape[0]):
        for column_index in range(values.shape[1]):
            value = values[row_index, column_index]
            label = labels[row_index, column_index]
            text_color = "white" if not np.isnan(value) and int(value) in {0, 4} else TEXT
            ax.text(
                column_index,
                row_index,
                label,
                ha="center",
                va="center",
                color=text_color,
                fontsize=10.0,
                weight="bold" if label != "NA" else "normal",
            )

    legend_handles = [
        Patch(facecolor=color, edgecolor="none", label=label)
        for color, label in zip(colors, ("≤0.1×", "0.1–0.5×", "0.5–2×", "2–10×", ">10×"))
    ]
    legend_handles.append(Patch(facecolor="#E4E7E9", edgecolor="none", label="NA"))
    ax.legend(
        handles=legend_handles,
        title="LEO / balloon",
        ncol=6,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.10),
        frameon=False,
        handlelength=1.3,
        columnspacing=1.2,
    )
    fig.suptitle("Non-gamma source contrast by energy band", fontsize=15, weight="bold", y=0.985)
    fig.text(
        0.5,
        0.935,
        "Band-integrated angular-domain source flux ratio; gamma is kept in figure 1; <1 does not automatically mean less detector background",
        ha="center",
        color=MUTED,
        fontsize=9.2,
    )
    fig.text(
        0.5,
        0.025,
        "* diagnostic 10-GV neutron fallback   ~ partial/mixed cited validity   NA = unavailable or outside support   SAA is excluded",
        ha="center",
        color=MUTED,
        fontsize=8.7,
    )
    fig.tight_layout(rect=(0.03, 0.12, 0.98, 0.91))
    save_figure(fig, "simple_02_family_band_ratio")
    return table_rows


def build_readout_rows() -> list[dict[str, str]]:
    return [
        {
            "topic": "Source spectra and units",
            "status": "Input established",
            "status_class": "input_established",
            "evidence_level": "input authority",
            "evidence": "Corrected balloon 8×20 spectra and pinned LEO components use total kinetic keV with explicit normalization.",
        },
        {
            "topic": "Absolute source flux",
            "status": "B-level contrast",
            "status_class": "b_level_contrast",
            "evidence_level": "source-level comparison",
            "evidence": "Angular-domain integrated incident flux is comparable as an environment contrast; orbit and angular supports differ.",
        },
        {
            "topic": "Angular equivalence",
            "status": "Not established",
            "status_class": "not_established",
            "evidence_level": "requires source-card binding",
            "evidence": "The COSI component beams and balloon full/down/up fields are not yet a matched instrument-coordinate angular model.",
        },
        {
            "topic": "Prompt detector background",
            "status": "Not established",
            "status_class": "not_established",
            "evidence_level": "requires matched transport",
            "evidence": "Source-flux ratios do not include shielding, veto, secondary production, energy deposition, or detector selections.",
        },
        {
            "topic": "Activation + delayed\nbackground",
            "status": "Not established",
            "status_class": "not_established",
            "evidence_level": "requires orbit + inventory chain",
            "evidence": "SAA residence, trapped particles, isotope inventory, decay timing, and delayed response are outside the static profile.",
        },
        {
            "topic": "511-window detector rate",
            "status": "Not established",
            "status_class": "not_established",
            "evidence_level": "requires response closure",
            "evidence": "The LEO delta line and balloon coarse broadband bump cannot be converted to a detector-window ratio without transport and response.",
        },
        {
            "topic": "Sensitivity + design\nranking",
            "status": "Not established",
            "status_class": "not_established",
            "evidence_level": "requires full matched chain",
            "evidence": "Prompt, activation, delayed response, exposure, and focused-signal normalization must close before Mass511/S3d ranking.",
        },
        {
            "topic": "CPU and disk cost",
            "status": "Pilot required",
            "status_class": "pilot_required",
            "evidence_level": "resource calibration absent",
            "evidence": "Source inventory is known; runtime, event complexity, retention, and isotope-output size need per-component and per-state pilots.",
        },
    ]


def plot_readout(rows: list[dict[str, str]]) -> None:
    status_style = {
        "input_established": ("#DDEAF5", "#285E85"),
        "b_level_contrast": ("#E7EDF2", "#496372"),
        "not_established": ("#ECEDEF", "#5A6066"),
        "pilot_required": ("#F5E9DC", "#7D5A35"),
    }
    fig, ax = plt.subplots(figsize=(13.5, 8.1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.035, 0.955, "What can the current evidence answer?", fontsize=16, weight="bold", color=TEXT)
    ax.text(
        0.035,
        0.915,
        "Evidence readout for a 530-km near-equatorial LEO proxy versus the corrected 38-km balloon environment",
        fontsize=9.8,
        color=MUTED,
    )
    ax.text(0.035, 0.865, "Topic", fontsize=9, color=MUTED, weight="bold")
    ax.text(0.225, 0.865, "Current status", fontsize=9, color=MUTED, weight="bold")
    ax.text(0.465, 0.865, "Evidence or next requirement", fontsize=9, color=MUTED, weight="bold")

    top = 0.835
    row_height = 0.091
    for index, row in enumerate(rows):
        y_top = top - index * row_height
        y_bottom = y_top - 0.076
        background = "#FAFBFC" if index % 2 == 0 else "#F5F7F8"
        ax.add_patch(Rectangle((0.025, y_bottom), 0.95, 0.076, facecolor=background, edgecolor="none"))
        ax.text(0.035, y_bottom + 0.038, row["topic"], va="center", fontsize=9.7, weight="bold", color=TEXT)

        face, foreground = status_style[row["status_class"]]
        badge = FancyBboxPatch(
            (0.218, y_bottom + 0.014),
            0.218,
            0.048,
            boxstyle="round,pad=0.006,rounding_size=0.009",
            facecolor=face,
            edgecolor="none",
        )
        ax.add_patch(badge)
        ax.text(0.327, y_bottom + 0.038, row["status"], ha="center", va="center", fontsize=9.1, weight="bold", color=foreground)

        ax.text(0.465, y_bottom + 0.048, row["evidence"], va="center", fontsize=8.75, color=TEXT, wrap=True)
        ax.text(0.465, y_bottom + 0.015, row["evidence_level"], va="center", fontsize=7.8, color=MUTED, style="italic")

    conclusion_y = 0.055
    ax.add_patch(
        FancyBboxPatch(
            (0.025, conclusion_y - 0.018),
            0.95,
            0.073,
            boxstyle="round,pad=0.008,rounding_size=0.01",
            facecolor="#EFF3F6",
            edgecolor="#CFD7DD",
            linewidth=0.8,
        )
    )
    ax.text(
        0.045,
        conclusion_y + 0.018,
        "Bottom line",
        fontsize=10.1,
        weight="bold",
        color=TEXT,
        va="center",
    )
    ax.text(
        0.145,
        conclusion_y + 0.018,
        "Figures 1–2 establish source inputs and environment contrasts. Detector background, activation, 511-window rate, and resource cost still require matched pilots and transport.",
        fontsize=9.4,
        color=TEXT,
        va="center",
    )
    ax.text(
        0.975,
        0.012,
        "Neutral readiness matrix — not a project acceptance score",
        ha="right",
        fontsize=8.1,
        color=MUTED,
    )
    save_figure(fig, "simple_03_readout")


def main() -> None:
    require_validated_inputs()
    configure_plotting()
    contrasts = read_csv(TABLE_ROOT / "environment_contrasts.csv")
    line_rows = read_csv(TABLE_ROOT / "satellite_line_components.csv")
    component_chart_rows = plot_incident_component_spectra(line_rows)
    gamma_rows = plot_gamma_summary(contrasts, line_rows)
    matrix_rows = plot_family_matrix(contrasts)
    readout_rows = build_readout_rows()
    plot_readout(readout_rows)

    write_csv(
        SIMPLE_TABLE_ROOT / "simple_gamma_bands.csv",
        gamma_rows,
        (
            "band_id",
            "display_label",
            "balloon_flux_cm2_s",
            "leo_flux_cm2_s",
            "leo_to_balloon_ratio",
            "comparison_grade",
            "model_validity_coverage",
        ),
    )
    write_csv(
        SIMPLE_TABLE_ROOT / "simple_family_band_matrix.csv",
        matrix_rows,
        (
            "family",
            "family_label",
            "band_id",
            "band_label",
            "leo_to_balloon_ratio",
            "display_label",
            "category",
            "model_validity_coverage",
            "comparison_grade",
        ),
    )
    write_csv(
        SIMPLE_TABLE_ROOT / "simple_readout.csv",
        readout_rows,
        ("topic", "status", "status_class", "evidence_level", "evidence"),
    )
    write_csv(
        SIMPLE_TABLE_ROOT / "simple_incident_component_spectra.csv",
        component_chart_rows,
        (
            "environment",
            "component",
            "family",
            "energy_MeV_total",
            "support_avg_intensity_cm2_s_sr_MeV",
            "plotted_above_display_floor",
            "activation_or_delayed",
        ),
    )

    manifest = {
        "schema_version": 1,
        "status": "BUILT__FOUR_FIGURE_SOURCE_COMPARISON__NOT_TRANSPORT_AUTHORITY",
        "figure_count": 4,
        "figures": [
            {
                "id": "simple_00_incident_component_spectra",
                "question": "How do the prompt incident particle components compare in the LEO proxy and balloon field?",
                "reference": "cube_satelite/基于立方星的康普顿望远镜在轨性能模拟.docx, supplied component-spectrum layout",
                "quantity_boundary": "incident dF/dE; activation/delayed sources omitted; no reconstructed Counts/keV/s or cross-family total",
            },
            {
                "id": "simple_01_gamma_source",
                "question": "How do the nominal gamma continua and broad gamma bands differ?",
            },
            {
                "id": "simple_02_family_band_ratio",
                "question": "Which non-gamma particle-family energy bands have less or more source flux in the LEO proxy?",
            },
            {
                "id": "simple_03_readout",
                "question": "Which questions are established by current evidence, and which require matched transport or pilots?",
            },
        ],
        "input_table_sha256": {filename: sha256(TABLE_ROOT / filename) for filename in SOURCE_TABLES},
        "authority_boundary": "source-input comparison only; not detector background, activation, sensitivity, or geometry promotion authority",
    }
    SIMPLE_ROOT.mkdir(parents=True, exist_ok=True)
    (SIMPLE_ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Built {manifest['figure_count']} simple figures under {FIGURE_ROOT}")


if __name__ == "__main__":
    main()
