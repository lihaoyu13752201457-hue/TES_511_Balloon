#!/usr/bin/env python3
"""Build two non-manuscript figures explaining the BPE factor-1000 issue.

The corrected case reuses the accepted 20 mm, 5 wt% BPE boundary diagnostic.
The legacy case shifts the neutron energy coordinate by 1/1000 while preserving
the current per-log-energy rate.  Because no matched legacy BPE-only boundary
transport exists, its post-BPE curve is explicitly an attenuation-only proxy
based on the corrected run's primary first-passage transmission by incident
energy.  It is not labelled or used as a transported output spectrum.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import zlib
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


DEFAULT_AUTHORITY_ROOT = Path("/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon")
ABUNDANCE_63 = 0.6915
ABUNDANCE_65 = 0.3085
XS_MAX_KEV = 100_000.0
PRODUCTS = ("Cu61", "Cu62", "Cu64")
PRODUCT_LABELS = {
    "Cu61": r"$^{61}$Cu",
    "Cu62": r"$^{62}$Cu",
    "Cu64": r"$^{64}$Cu",
}
PRODUCT_COLORS = {
    "Cu61": "#0072B2",
    "Cu62": "#D55E00",
    "Cu64": "#7B2CBF",
}


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-root", type=Path, default=DEFAULT_AUTHORITY_ROOT)
    parser.add_argument("--output-dir", type=Path, default=here / "outputs")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_isotope_production(path: Path) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    n_products = int(lines[0])
    cursor = 1
    output: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for _ in range(n_products):
        product = lines[cursor].upper()
        cursor += 3  # product label, reaction identifier, state flag
        n_points = int(lines[cursor])
        cursor += 1
        values: list[float] = []
        while len(values) < 2 * n_points:
            values.extend(float(value) for value in lines[cursor].split())
            cursor += 1
        array = np.asarray(values[: 2 * n_points], dtype=float).reshape(-1, 2)
        output[product] = (array[:, 0] / 1000.0, array[:, 1])  # eV -> keV
    return output


def parse_capture(path: Path) -> tuple[np.ndarray, np.ndarray]:
    text = zlib.decompress(path.read_bytes()).decode("utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    n_points = int(lines[4])
    values: list[float] = []
    for line in lines[5:]:
        values.extend(float(value) for value in line.split())
        if len(values) >= 2 * n_points:
            break
    array = np.asarray(values[: 2 * n_points], dtype=float).reshape(-1, 2)
    return array[:, 0] / 1000.0, array[:, 1]  # eV -> keV


def interp_xs(table: tuple[np.ndarray, np.ndarray], energy_keV: np.ndarray) -> np.ndarray:
    return np.interp(energy_keV, table[0], table[1], left=0.0, right=0.0)


def effective_xs(
    product: str,
    energy_keV: np.ndarray,
    prod63: dict[str, tuple[np.ndarray, np.ndarray]],
    prod65: dict[str, tuple[np.ndarray, np.ndarray]],
    capture63: tuple[np.ndarray, np.ndarray],
) -> np.ndarray:
    if product == "Cu61":
        result = ABUNDANCE_63 * interp_xs(prod63["CU61"], energy_keV)
        result += ABUNDANCE_65 * interp_xs(prod65["CU61"], energy_keV)
    elif product == "Cu62":
        result = ABUNDANCE_63 * interp_xs(prod63["CU62"], energy_keV)
        result += ABUNDANCE_65 * interp_xs(prod65["CU62"], energy_keV)
    elif product == "Cu64":
        result = ABUNDANCE_63 * interp_xs(capture63, energy_keV)
        result += ABUNDANCE_65 * interp_xs(prod65["CU64"], energy_keV)
    else:
        raise ValueError(product)
    return np.where((energy_keV > 0.0) & (energy_keV <= XS_MAX_KEV), result, 0.0)


def bin_average_xs(
    product: str,
    lo_keV: np.ndarray,
    hi_keV: np.ndarray,
    prod63: dict[str, tuple[np.ndarray, np.ndarray]],
    prod65: dict[str, tuple[np.ndarray, np.ndarray]],
    capture63: tuple[np.ndarray, np.ndarray],
) -> np.ndarray:
    """Average sigma uniformly in log(E) within each 0.1-decade spectrum bin."""
    output = np.zeros_like(lo_keV, dtype=float)
    for index, (lo, hi) in enumerate(zip(lo_keV, hi_keV)):
        if lo <= 0.0 or lo >= XS_MAX_KEV:
            continue
        clipped_hi = min(hi, XS_MAX_KEV)
        if clipped_hi <= lo:
            continue
        grid = np.geomspace(lo, clipped_hi, 257)
        sigma = effective_xs(product, grid, prod63, prod65, capture63)
        output[index] = np.trapz(sigma, x=np.log(grid)) / math.log(clipped_hi / lo)
    return output


def load_spectrum(rows: list[dict[str, str]], population: str, stage: str) -> dict[str, np.ndarray]:
    selected = [row for row in rows if row["population"] == population and row["stage"] == stage]
    if not selected:
        raise ValueError((population, stage))
    lo_keV = np.asarray([float(row["energy_lo_keV"]) for row in selected])
    hi_keV = np.asarray([float(row["energy_hi_keV"]) for row in selected])
    rate_bin = np.asarray([float(row["crossing_rate_s-1"]) for row in selected])
    dex = np.log10(hi_keV / lo_keV)
    return {
        "lo_keV": lo_keV,
        "hi_keV": hi_keV,
        "center_keV": np.sqrt(lo_keV * hi_keV),
        "dex": dex,
        "rate_per_decade": rate_bin / dex,
    }


def attenuation_proxy(energy_keV: np.ndarray) -> np.ndarray:
    """Piecewise primary first-passage reach fraction from the corrected run."""
    energy_keV = np.asarray(energy_keV)
    result = np.empty_like(energy_keV, dtype=float)
    result[energy_keV <= 5.0e-4] = 0.0161
    result[(energy_keV > 5.0e-4) & (energy_keV < 100.0)] = 0.2781
    result[(energy_keV >= 100.0) & (energy_keV < 1_000.0)] = 0.5994
    result[(energy_keV >= 1_000.0) & (energy_keV < 10_000.0)] = 0.7609
    result[(energy_keV >= 10_000.0) & (energy_keV < 20_000.0)] = 0.8083
    result[(energy_keV >= 20_000.0) & (energy_keV < 39_000.0)] = 0.8133
    result[energy_keV >= 39_000.0] = 0.8555
    return result


def positive_step(ax: plt.Axes, x: np.ndarray, y: np.ndarray, **kwargs) -> None:
    values = np.where(y > 0.0, y, np.nan)
    ax.step(x, values, where="mid", **kwargs)


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "figure.dpi": 120,
            "savefig.dpi": 240,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
            "xtick.color": "#333333",
            "ytick.color": "#333333",
            "text.color": "#222222",
        }
    )


def build_spectrum_figure(
    output_dir: Path,
    corrected_in: dict[str, np.ndarray],
    corrected_out: dict[str, np.ndarray],
    legacy_in: dict[str, np.ndarray],
    legacy_proxy_out: dict[str, np.ndarray],
    summary: dict,
    historical: dict,
) -> None:
    setup_style()
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.0), sharex=True, sharey=True)
    outer_color = "#777777"
    inner_color = "#1f77b4"

    for ax in axes:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(1.0e-10, 1.0e4)
        ax.grid(which="major", color="#dddddd", lw=0.6)
        ax.tick_params(which="both", direction="out", width=0.7)

    positive_step(
        axes[0],
        corrected_in["center_keV"] / 1000.0,
        corrected_in["rate_per_decade"],
        color=outer_color,
        lw=1.2,
        ls="--",
        label="Before BPE",
    )
    positive_step(
        axes[0],
        corrected_out["center_keV"] / 1000.0,
        corrected_out["rate_per_decade"],
        color=inner_color,
        lw=1.4,
        label="After BPE",
    )
    axes[0].set_title("(a) Corrected energy axis", loc="left")
    axes[0].legend(loc="best", frameon=False)

    positive_step(
        axes[1],
        legacy_in["center_keV"] / 1000.0,
        legacy_in["rate_per_decade"],
        color=outer_color,
        lw=1.2,
        ls="--",
        label="Before BPE",
    )
    positive_step(
        axes[1],
        legacy_proxy_out["center_keV"] / 1000.0,
        legacy_proxy_out["rate_per_decade"],
        color=inner_color,
        lw=1.4,
        label="After BPE (proxy)",
    )
    axes[1].set_title("(b) Energy axis divided by 1000", loc="left")
    axes[1].legend(loc="best", frameon=False)

    axes[0].set_ylabel(r"$\mathrm{d}J/\mathrm{d}\log_{10}E$ (s$^{-1}$ decade$^{-1}$)")
    for ax in axes:
        ax.set_xlabel("Neutron energy (MeV)")
    fig.suptitle("Neutron spectra across 2 cm BPE", fontsize=11, fontweight="normal")
    fig.tight_layout(rect=(0.035, 0.035, 0.995, 0.94), w_pad=1.5)
    for suffix in ("png", "pdf"):
        fig.savefig(output_dir / f"figure_1_bpe_neutron_spectra_current_vs_factor1000.{suffix}", bbox_inches="tight")
    plt.close(fig)


def build_copper_figure(
    output_dir: Path,
    fine_energy_keV: np.ndarray,
    fine_xs: dict[str, np.ndarray],
    corrected_out: dict[str, np.ndarray],
    legacy_proxy_out: dict[str, np.ndarray],
) -> None:
    setup_style()
    fig, (ax_xs, ax_spectrum) = plt.subplots(1, 2, figsize=(9.5, 4.1))

    for product in PRODUCTS:
        sigma = np.where(fine_xs[product] > 0.0, fine_xs[product], np.nan)
        ax_xs.plot(
            fine_energy_keV / 1000.0,
            sigma,
            color=PRODUCT_COLORS[product],
            lw=1.2,
            label=PRODUCT_LABELS[product],
        )
    ax_xs.set_xscale("log")
    ax_xs.set_yscale("log")
    ax_xs.set_xlim(1.0e-10, 100.0)
    ax_xs.set_xlabel("Neutron energy (MeV)")
    ax_xs.set_ylabel(r"Natural-Cu $\sigma(E)$ (barn)")
    ax_xs.set_title("(a) Natural-Cu production", loc="left")
    ax_xs.legend(frameon=False, loc="best")

    positive_step(
        ax_spectrum,
        corrected_out["center_keV"] / 1000.0,
        corrected_out["rate_per_decade"],
        color="#1f77b4",
        lw=1.3,
        label="Corrected",
    )
    positive_step(
        ax_spectrum,
        legacy_proxy_out["center_keV"] / 1000.0,
        legacy_proxy_out["rate_per_decade"],
        color="#d55e00",
        lw=1.2,
        ls="--",
        label="Energy axis / 1000 (proxy)",
    )
    ax_spectrum.set_xscale("log")
    ax_spectrum.set_yscale("log")
    ax_spectrum.set_xlim(1.0e-10, 100.0)
    ax_spectrum.set_xlabel("Neutron energy (MeV)")
    ax_spectrum.set_ylabel(r"$\mathrm{d}J/\mathrm{d}\log_{10}E$ (s$^{-1}$ decade$^{-1}$)")
    ax_spectrum.set_title("(b) Post-BPE neutron spectra", loc="left")
    ax_spectrum.legend(frameon=False, loc="best")

    for ax in (ax_xs, ax_spectrum):
        ax.grid(which="major", color="#dddddd", lw=0.6)
        ax.tick_params(which="both", direction="out", width=0.7)

    fig.suptitle("Natural-copper production cross sections and post-BPE neutron spectra", fontsize=11, fontweight="normal")
    fig.subplots_adjust(left=0.08, right=0.99, bottom=0.15, top=0.84, wspace=0.30)
    for suffix in ("png", "pdf"):
        fig.savefig(output_dir / f"figure_2_natural_cu_beta_plus_overlap.{suffix}", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    args = parse_args()
    authority_root = args.authority_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    boundary_package = authority_root / (
        "engineering/particle_source_unit_repair_20260811/"
        "bpe_neutron_boundary_20260813"
    )
    boundary_csv = boundary_package / "outputs/boundary_spectrum.csv"
    fold_csv = boundary_package / "outputs/cu_reaction_fold.csv"
    summary_json = boundary_package / "outputs/summary.json"
    historical_json = authority_root / (
        "engineering/geometry_optimization_20260704/"
        "39_mass511_to_s3_html_presentation_20260710/data/bpe_evidence_summary.json"
    )
    g4ndl = Path(
        "/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/"
        "share/Geant4-10.2.3/data/G4NDL4.5"
    )
    cu63_prod_path = g4ndl / "IsotopeProduction/CrossSection/29_63_Copper"
    cu65_prod_path = g4ndl / "IsotopeProduction/CrossSection/29_65_Copper"
    cu63_capture_path = g4ndl / "Capture/CrossSection/29_63_Copper.z"
    inputs = [boundary_csv, fold_csv, summary_json, historical_json, cu63_prod_path, cu65_prod_path, cu63_capture_path]
    missing = [str(path) for path in inputs if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required inputs:\n" + "\n".join(missing))

    spectrum_rows = read_csv(boundary_csv)
    fold_rows = read_csv(fold_csv)
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    historical = json.loads(historical_json.read_text(encoding="utf-8"))

    corrected_in = load_spectrum(spectrum_rows, "all", "outer_input")
    corrected_out = load_spectrum(spectrum_rows, "all", "inner_output")
    legacy_in = {
        key: (value / 1000.0 if key in {"lo_keV", "hi_keV", "center_keV"} else value.copy())
        for key, value in corrected_in.items()
    }
    proxy_t = attenuation_proxy(legacy_in["center_keV"])
    legacy_proxy_out = {key: value.copy() for key, value in legacy_in.items()}
    legacy_proxy_out["rate_per_decade"] = legacy_in["rate_per_decade"] * proxy_t

    prod63 = parse_isotope_production(cu63_prod_path)
    prod65 = parse_isotope_production(cu65_prod_path)
    capture63 = parse_capture(cu63_capture_path)
    fine_energy_keV = np.geomspace(1.0e-9, XS_MAX_KEV, 7000)
    fine_xs = {
        product: effective_xs(product, fine_energy_keV, prod63, prod65, capture63)
        for product in PRODUCTS
    }

    authoritative = {}
    ratio_authority = {}
    for row in fold_rows:
        if row["population"] != "all" or row["reaction_channel"] != "total":
            continue
        product = row["reaction_product"]
        if row["stage"] in {"outer_input", "inner_output"}:
            authoritative[(product, row["stage"])] = float(row["evaluated_le100MeV_current_index_b_s-1"])
        elif row["output_over_input_evaluated_le100MeV_current_index"]:
            ratio_authority[product] = (
                float(row["output_over_input_evaluated_le100MeV_current_index"]),
                float(row["current_ratio_jackknife_se"]),
            )

    corrected_kernel: dict[tuple[str, str], dict[str, np.ndarray | float]] = {}
    legacy_kernel: dict[tuple[str, str], dict[str, np.ndarray | float]] = {}
    kernel_rows: list[dict] = []
    integrated_rows: list[dict] = []
    closure_factors: dict[str, float] = {}

    for product in PRODUCTS:
        for stage, spectrum, authority_stage in (
            ("input", corrected_in, "outer_input"),
            ("output", corrected_out, "inner_output"),
        ):
            avg_sigma = bin_average_xs(
                product,
                spectrum["lo_keV"],
                spectrum["hi_keV"],
                prod63,
                prod65,
                capture63,
            )
            raw_kernel = spectrum["rate_per_decade"] * avg_sigma
            raw_total = float(np.sum(raw_kernel * spectrum["dex"]))
            authority_total = authoritative[(product, authority_stage)]
            closure = authority_total / raw_total if raw_total > 0 else 1.0
            kernel = raw_kernel * closure
            closure_factors[f"{product}:{stage}"] = closure
            corrected_kernel[(product, stage)] = {
                "energy_keV": spectrum["center_keV"],
                "kernel": kernel,
                "closure_factor": closure,
            }
            ratio, ratio_se = ratio_authority[product]
            integrated_rows.append(
                {
                    "scenario": "corrected_transport",
                    "stage": stage,
                    "product": product,
                    "integrated_index_b_s-1": authority_total,
                    "output_over_input": ratio if stage == "output" else 1.0,
                    "ratio_se": ratio_se if stage == "output" else 0.0,
                    "status": "event-wise authority",
                }
            )
            for idx in range(len(spectrum["center_keV"])):
                kernel_rows.append(
                    {
                        "scenario": "corrected_transport",
                        "stage": stage,
                        "product": product,
                        "energy_lo_keV": spectrum["lo_keV"][idx],
                        "energy_hi_keV": spectrum["hi_keV"][idx],
                        "energy_center_keV": spectrum["center_keV"][idx],
                        "rate_per_decade_s-1": spectrum["rate_per_decade"][idx],
                        "sigma_bin_average_b": avg_sigma[idx],
                        "kernel_b_s-1_decade-1": kernel[idx],
                        "closure_factor_to_eventwise_total": closure,
                        "status": "transported spectrum; kernel shape closed to event-wise integral",
                    }
                )

        legacy_totals: dict[str, float] = {}
        for stage, spectrum in (("input", legacy_in), ("output", legacy_proxy_out)):
            avg_sigma = bin_average_xs(
                product,
                spectrum["lo_keV"],
                spectrum["hi_keV"],
                prod63,
                prod65,
                capture63,
            )
            kernel = spectrum["rate_per_decade"] * avg_sigma
            total = float(np.sum(kernel * spectrum["dex"]))
            legacy_totals[stage] = total
            legacy_kernel[(product, stage)] = {
                "energy_keV": spectrum["center_keV"],
                "kernel": kernel,
                "closure_factor": 1.0,
            }
            for idx in range(len(spectrum["center_keV"])):
                kernel_rows.append(
                    {
                        "scenario": "factor1000_proxy",
                        "stage": stage,
                        "product": product,
                        "energy_lo_keV": spectrum["lo_keV"][idx],
                        "energy_hi_keV": spectrum["hi_keV"][idx],
                        "energy_center_keV": spectrum["center_keV"][idx],
                        "rate_per_decade_s-1": spectrum["rate_per_decade"][idx],
                        "sigma_bin_average_b": avg_sigma[idx],
                        "kernel_b_s-1_decade-1": kernel[idx],
                        "closure_factor_to_eventwise_total": 1.0,
                        "status": (
                            "energy-axis counterfactual input"
                            if stage == "input"
                            else "attenuation-only proxy; not transported output"
                        ),
                    }
                )
        legacy_ratio = legacy_totals["output"] / legacy_totals["input"] if legacy_totals["input"] > 0 else math.nan
        for stage in ("input", "output"):
            integrated_rows.append(
                {
                    "scenario": "factor1000_proxy",
                    "stage": stage,
                    "product": product,
                    "integrated_index_b_s-1": legacy_totals[stage],
                    "output_over_input": legacy_ratio if stage == "output" else 1.0,
                    "ratio_se": 0.0,
                    "status": (
                        "energy-axis counterfactual input"
                        if stage == "input"
                        else "attenuation-only proxy; no transport uncertainty assigned"
                    ),
                }
            )

    spectrum_export: list[dict] = []
    for scenario, stage, spectrum, status in (
        ("corrected_transport", "input", corrected_in, "accepted transported outer-boundary current"),
        ("corrected_transport", "output", corrected_out, "accepted transported inner-boundary current"),
        ("factor1000_proxy", "input", legacy_in, "energy coordinate divided by 1000; current unchanged"),
        ("factor1000_proxy", "output", legacy_proxy_out, "attenuation-only proxy; not transported output"),
    ):
        for idx in range(len(spectrum["center_keV"])):
            spectrum_export.append(
                {
                    "scenario": scenario,
                    "stage": stage,
                    "energy_lo_keV": spectrum["lo_keV"][idx],
                    "energy_hi_keV": spectrum["hi_keV"][idx],
                    "energy_center_keV": spectrum["center_keV"][idx],
                    "rate_per_decade_s-1": spectrum["rate_per_decade"][idx],
                    "status": status,
                }
            )
    write_csv(output_dir / "spectra_for_figures.csv", spectrum_export)
    write_csv(output_dir / "cu_kernel_for_figures.csv", kernel_rows)
    write_csv(output_dir / "integrated_cu_indices.csv", integrated_rows)
    cross_section_rows = [
        {
            "energy_keV": energy,
            "sigma_nat_Cu61_b": fine_xs["Cu61"][idx],
            "sigma_nat_Cu62_b": fine_xs["Cu62"][idx],
            "sigma_nat_Cu64_b": fine_xs["Cu64"][idx],
        }
        for idx, energy in enumerate(fine_energy_keV)
    ]
    write_csv(output_dir / "natural_cu_cross_sections.csv", cross_section_rows)

    build_spectrum_figure(
        output_dir,
        corrected_in,
        corrected_out,
        legacy_in,
        legacy_proxy_out,
        summary,
        historical,
    )
    build_copper_figure(
        output_dir,
        fine_energy_keV,
        fine_xs,
        corrected_out,
        legacy_proxy_out,
    )

    provenance = {
        "status": "PASS__TWO_NON_MANUSCRIPT_BPE_FACTOR1000_EXPLAINER_FIGURES",
        "scope": "Mechanism illustration only; no manuscript integration and no new transport.",
        "current_case": {
            "description": "Accepted corrected-keV, 20-bin integrated, 20 mm 5 wt% BPE boundary transport.",
            "population": "all boundary crossings, including secondary neutrons and repeated crossings",
            "cu_fold": "event-wise current indices for E<=100 MeV",
        },
        "factor1000_case": {
            "transform": "E_old = E_current / 1000; dJ/dlog10(E) unchanged",
            "post_bpe_status": "attenuation-only screening proxy; not a transported output spectrum",
            "proxy_definition": "piecewise multiplication by corrected-run primary first-passage reach fraction",
            "energy_redistribution": "not represented",
            "uncertainty": "not assigned",
        },
        "transmission_proxy": [
            {"range": "E<=0.5 eV", "reach_fraction": 0.0161},
            {"range": "0.5 eV<E<100 keV", "reach_fraction": 0.2781},
            {"range": "0.1<=E<1 MeV", "reach_fraction": 0.5994},
            {"range": "1<=E<10 MeV", "reach_fraction": 0.7609},
            {"range": "10<=E<20 MeV", "reach_fraction": 0.8083},
            {"range": "20<=E<39 MeV", "reach_fraction": 0.8133},
            {"range": "E>=39 MeV", "reach_fraction": 0.8555},
        ],
        "cross_sections": {
            "library": "G4NDL4.5",
            "natural_abundance": {"Cu63": ABUNDANCE_63, "Cu65": ABUNDANCE_65},
            "fold_range": "0<E<=100 MeV",
            "products": {
                "Cu61": ["63Cu(n,3n)", "65Cu(n,5n)"],
                "Cu62": ["63Cu(n,2n)", "65Cu(n,4n)"],
                "Cu64": ["63Cu(n,gamma)", "65Cu(n,2n)"],
            },
            "note": "Cu64 is a mixed beta+/EC/beta- decay product; the figure is not beta+-branch weighted.",
        },
        "corrected_kernel_closure_factors": closure_factors,
        "inputs": {str(path): sha256(path) for path in inputs},
        "outputs": [
            "figure_1_bpe_neutron_spectra_current_vs_factor1000.png",
            "figure_1_bpe_neutron_spectra_current_vs_factor1000.pdf",
            "figure_2_natural_cu_beta_plus_overlap.png",
            "figure_2_natural_cu_beta_plus_overlap.pdf",
            "spectra_for_figures.csv",
            "cu_kernel_for_figures.csv",
            "integrated_cu_indices.csv",
            "natural_cu_cross_sections.csv",
        ],
        "historical_full_stack_caveat": (
            "The historical S3 comparison includes BPE, plastic, CsI and geometry changes. "
            "It is used only as qualitative context, not as a BPE-only causal estimate."
        ),
    }
    (output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
