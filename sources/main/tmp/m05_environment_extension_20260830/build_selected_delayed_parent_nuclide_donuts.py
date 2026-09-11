#!/usr/bin/env python3
"""Build the A/B parent-nuclide donuts used in the Results section.

Only the two compact, final-selected delayed-event catalogues and the current
audited model-B family reweighting record are read.  The script does not open
SIM/NPZ payloads or job catalogues and does not start a simulation.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/m05_parent_nuclide_donuts_mpl")

import matplotlib as mpl
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
A_SOURCE = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "59_sg3b_prompt_activation_coupling_20260818"
    / "outputs/02_coupling_analysis/selected_event_lineage.csv"
)
B_SOURCE = (
    REPO
    / "engineering/geometry_optimization_20260815"
    / "63_m05new_sg3b_signal_statistics_20260820"
    / "outputs/05_optv3_delayed_origins/optv3_delayed_selected_events.csv"
)
AUDIT = (
    HERE
    / "figure_revision_r19/M05_SECTION4_PUBLICATION_FIGURES_20260829.json"
)
OUTDIR = HERE / "figures/section4_current"
OUTSTEM = "fig_selected_delayed_parent_nuclide_donuts"

EXPECTED_A_ROWS = 394
EXPECTED_B_ROWS = 111
EXPECTED_A_TOTAL = 0.037720860604326306
EXPECTED_B_TOTAL = 0.003580537811785916
TOP_N = 7

ELEMENT_SYMBOLS = {
    6: "C",
    8: "O",
    9: "F",
    13: "Al",
    24: "Cr",
    29: "Cu",
    75: "Re",
    84: "Po",
}

# Shared nuclides retain the same colour in both panels.  The palette is
# colour-vision-friendly and remains distinguishable in grayscale through the
# legend and the hatch applied to the aggregated remainder.
NUCLIDE_COLORS = {
    (29, 62): "#0072B2",
    (29, 64): "#E69F00",
    (29, 61): "#009E73",
    (8, 15): "#56B4E9",
    (84, 199): "#CC79A7",
    (9, 18): "#D55E00",
    (6, 11): "#F0E442",
    (13, 25): "#CC79A7",
    (24, 49): "#8C564B",
    (75, 175): "#56B4E9",
}
OTHER_COLOR = "#8A8A8A"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_za(value: str) -> tuple[int, int]:
    za = int(float(value))
    return za // 1000, za % 1000


def nuclide_label(key: tuple[int, int] | str) -> str:
    if key == "other":
        return "Other"
    z, mass = key
    symbol = ELEMENT_SYMBOLS.get(z)
    if symbol is None:
        raise RuntimeError(f"missing element symbol for Z={z}")
    return rf"$^{{{mass}}}\mathrm{{{symbol}}}$"


def load_inputs() -> tuple[dict[tuple[int, int], dict[str, float]], dict[tuple[int, int], dict[str, float]], dict[str, str]]:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    audited_hashes = audit["input_sha256"]
    input_hashes = {str(path): sha256(path) for path in (A_SOURCE, B_SOURCE)}
    for path, digest in input_hashes.items():
        if audited_hashes.get(path) != digest:
            raise RuntimeError(f"compact source does not match audited input: {path}")

    a_by_nuclide: dict[tuple[int, int], dict[str, float]] = defaultdict(
        lambda: {"rate": 0.0, "variance": 0.0, "records": 0}
    )
    with A_SOURCE.open(newline="", encoding="utf-8") as handle:
        a_rows = [row for row in csv.DictReader(handle) if row["stream"] == "delayed"]
    if len(a_rows) != EXPECTED_A_ROWS:
        raise RuntimeError(f"unexpected model-A row count: {len(a_rows)}")
    for row in a_rows:
        key = parse_za(row["source_parent_ZA"])
        weight = float(row["day15_noacc_cps"])
        a_by_nuclide[key]["rate"] += weight
        a_by_nuclide[key]["variance"] += weight * weight
        a_by_nuclide[key]["records"] += 1

    scales = audit["geometry_response"]["model_B_family_reweight"]
    b_by_nuclide: dict[tuple[int, int], dict[str, float]] = defaultdict(
        lambda: {"rate": 0.0, "variance": 0.0, "records": 0}
    )
    b_family_rate: dict[str, float] = defaultdict(float)
    b_family_variance: dict[str, float] = defaultdict(float)
    with B_SOURCE.open(newline="", encoding="utf-8") as handle:
        b_rows = list(csv.DictReader(handle))
    if len(b_rows) != EXPECTED_B_ROWS:
        raise RuntimeError(f"unexpected model-B row count: {len(b_rows)}")
    for row in b_rows:
        family = row["family"]
        if family not in scales:
            raise RuntimeError(f"missing model-B family reweight: {family}")
        old_weight = float(row["day15_event_weight_cps"])
        rate = old_weight * float(scales[family]["rate_scale"])
        variance = old_weight * old_weight * float(scales[family]["variance_scale"])
        key = parse_za(row["source_parent_ZA"])
        b_by_nuclide[key]["rate"] += rate
        b_by_nuclide[key]["variance"] += variance
        b_by_nuclide[key]["records"] += 1
        b_family_rate[family] += rate
        b_family_variance[family] += variance

    for family, expected in scales.items():
        if not math.isclose(
            b_family_rate[family], float(expected["formal_rate"]),
            rel_tol=2.0e-12, abs_tol=1.0e-14,
        ):
            raise RuntimeError(f"model-B rate reweight does not close for {family}")
        if not math.isclose(
            b_family_variance[family], float(expected["formal_variance"]),
            rel_tol=2.0e-12, abs_tol=1.0e-16,
        ):
            raise RuntimeError(f"model-B variance reweight does not close for {family}")

    for name, data, expected in (
        ("A", a_by_nuclide, EXPECTED_A_TOTAL),
        ("B", b_by_nuclide, EXPECTED_B_TOTAL),
    ):
        total = math.fsum(item["rate"] for item in data.values())
        if not math.isclose(total, expected, rel_tol=2.0e-12, abs_tol=1.0e-14):
            raise RuntimeError(f"model-{name} parent-nuclide rates do not close")

    return a_by_nuclide, b_by_nuclide, input_hashes


def top_with_other(data: dict[tuple[int, int], dict[str, float]]) -> list[tuple[tuple[int, int] | str, dict[str, float]]]:
    ranked = sorted(data.items(), key=lambda item: (-item[1]["rate"], item[0]))
    selected = [(key, dict(value)) for key, value in ranked[:TOP_N]]
    remainder = ranked[TOP_N:]
    selected.append(
        (
            "other",
            {
                "rate": math.fsum(value["rate"] for _, value in remainder),
                "variance": math.fsum(value["variance"] for _, value in remainder),
                "records": sum(int(value["records"]) for _, value in remainder),
            },
        )
    )
    return selected


def autopct_threshold(percent: float) -> str:
    return f"{percent:.1f}%" if percent >= 5.0 else ""


def draw_panel(
    ax: mpl.axes.Axes,
    model: str,
    entries: list[tuple[tuple[int, int] | str, dict[str, float]]],
    total: float,
) -> None:
    values = [item["rate"] for _, item in entries]
    colors = [OTHER_COLOR if key == "other" else NUCLIDE_COLORS[key] for key, _ in entries]
    wedges, _, autotexts = ax.pie(
        values,
        colors=colors,
        startangle=90,
        counterclock=False,
        radius=1.0,
        wedgeprops={"width": 0.36, "edgecolor": "white", "linewidth": 1.4},
        autopct=autopct_threshold,
        pctdistance=0.815,
    )
    wedges[-1].set_hatch("///")
    for wedge, text in zip(wedges, autotexts, strict=True):
        red, green, blue, _ = wedge.get_facecolor()
        luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        text.set_color("#171717" if luminance > 0.62 else "white")
        text.set_fontweight("bold")
        text.set_fontsize(8.3)

    exponent = -2 if model == "A" else -3
    coefficient = total / (10.0**exponent)
    ax.text(0.0, 0.17, "Final selected", ha="center", va="center", fontsize=8.5, color="#4B5563")
    ax.text(0.0, 0.01, "delayed background", ha="center", va="center", fontsize=8.5, color="#4B5563")
    ax.text(
        0.0,
        -0.20,
        rf"${coefficient:.5f}\times10^{{{exponent}}}$",
        ha="center",
        va="center",
        fontsize=9.8,
        fontweight="bold",
    )
    ax.text(0.0, -0.35, r"$\mathrm{s}^{-1}$", ha="center", va="center", fontsize=8.5, color="#4B5563")
    ax.set_title(f"Mass model {model}", pad=7, fontsize=10.5, fontweight="bold")
    ax.set_aspect("equal")

    legend_labels = [
        f"{nuclide_label(key)}  ({100.0 * item['rate'] / total:.2f}%)"
        for key, item in entries
    ]
    ax.legend(
        wedges,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.035),
        frameon=False,
        fontsize=8.05,
        handlelength=1.15,
        handletextpad=0.50,
        labelspacing=0.43,
    )


def serialize_entries(entries: list[tuple[tuple[int, int] | str, dict[str, float]]], total: float) -> list[dict[str, float | int | str]]:
    output = []
    for key, item in entries:
        output.append(
            {
                "nuclide": nuclide_label(key).replace("$", ""),
                "records": int(item["records"]),
                "rate_cps": item["rate"],
                "sigma_cps": math.sqrt(item["variance"]),
                "share_percent": 100.0 * item["rate"] / total,
            }
        )
    return output


def main() -> None:
    a_data, b_data, input_hashes = load_inputs()
    a_entries = top_with_other(a_data)
    b_entries = top_with_other(b_data)
    OUTDIR.mkdir(parents=True, exist_ok=True)

    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.8,
            "axes.titlesize": 10.5,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(7.20, 5.25), constrained_layout=True)
    fig.set_constrained_layout_pads(w_pad=0.045, h_pad=0.04, wspace=0.12, hspace=0.04)
    draw_panel(axes[0], "A", a_entries, EXPECTED_A_TOTAL)
    draw_panel(axes[1], "B", b_entries, EXPECTED_B_TOTAL)
    for panel, ax in zip(("(a)", "(b)"), axes, strict=True):
        ax.text(-0.06, 1.03, panel, transform=ax.transAxes, fontsize=10.5, fontweight="bold")

    generated = []
    for suffix in ("pdf", "png"):
        path = OUTDIR / f"{OUTSTEM}.{suffix}"
        kwargs: dict[str, object] = {"bbox_inches": "tight", "pad_inches": 0.04}
        if suffix == "png":
            kwargs["dpi"] = 600
        fig.savefig(path, **kwargs)
        generated.append(str(path))
        print(path)
    plt.close(fig)

    manifest = {
        "scope": "final selected day-15 delayed-activation background by parent nuclide",
        "authority_boundary": {
            "SIM_or_NPZ_opened": False,
            "large_job_catalog_scanned": False,
            "simulation_started": False,
        },
        "input_sha256": input_hashes,
        "model_A": {
            "selected_records": EXPECTED_A_ROWS,
            "total_rate_cps": EXPECTED_A_TOTAL,
            "displayed": serialize_entries(a_entries, EXPECTED_A_TOTAL),
        },
        "model_B": {
            "selected_records": EXPECTED_B_ROWS,
            "total_rate_cps": EXPECTED_B_TOTAL,
            "displayed": serialize_entries(b_entries, EXPECTED_B_TOTAL),
            "normalization": "current audited family-wise rate and variance scales",
        },
        "generated": generated,
    }
    manifest_path = OUTDIR / f"{OUTSTEM}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)


if __name__ == "__main__":
    main()
