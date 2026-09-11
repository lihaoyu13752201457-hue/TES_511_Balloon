#!/usr/bin/env python3
"""Build step-by-step review records for the opticsim Laue/channel work."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import tempfile
from pathlib import Path

_MPLCONFIGDIR = Path(tempfile.gettempdir()) / "opticsim_stepwise_mplconfig"
_MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPLCONFIGDIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


def parse_args() -> argparse.Namespace:
    script = Path(__file__).resolve()
    default_repo = script.parents[3]
    default_out = default_repo / "records" / "stepwise_review_2026-05-22"
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=default_repo)
    parser.add_argument("--out", type=Path, default=default_out)
    return parser.parse_args()


def load_json(repo: Path, rel_path: str):
    path = repo / rel_path
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_csv_dicts(repo: Path, rel_path: str) -> list[dict[str, str]]:
    path = repo / rel_path
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        write_text(path, "")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def savefig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def fmt(value, digits: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if abs(value) >= 1000 or (abs(value) > 0 and abs(value) < 0.001):
            return f"{value:.{digits}e}"
        return f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return str(value)


def table(rows: list[tuple[str, object]]) -> str:
    lines = ["| item | value |", "|---|---:|"]
    for key, value in rows:
        lines.append(f"| {key} | {fmt(value)} |")
    return "\n".join(lines)


def draw_review_pipeline(out: Path) -> None:
    steps = [
        ("00", "Map", "review boundary"),
        ("01", "Laue", "Barhoum-style baseline"),
        ("02", "Guan", "process/model split"),
        ("03", "Channel", "wall-by-wall optics"),
        ("04", "Bridge", "detector + activation"),
        ("05", "Checklist", "bug review"),
    ]
    fig, ax = plt.subplots(figsize=(12, 3.4))
    ax.set_axis_off()
    x0 = 0.02
    width = 0.145
    gap = 0.026
    for idx, (num, title, subtitle) in enumerate(steps):
        x = x0 + idx * (width + gap)
        rect = Rectangle((x, 0.32), width, 0.36, facecolor="#f5f7fb", edgecolor="#3f5f8f", lw=1.5)
        ax.add_patch(rect)
        ax.text(x + width / 2, 0.59, f"{num} {title}", ha="center", va="center", fontsize=11, weight="bold")
        ax.text(x + width / 2, 0.44, subtitle, ha="center", va="center", fontsize=8.5)
        if idx < len(steps) - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (x + width, 0.5),
                    (x + width + gap * 0.88, 0.5),
                    arrowstyle="-|>",
                    mutation_scale=13,
                    lw=1.2,
                    color="#53616f",
                )
            )
    ax.text(
        0.5,
        0.11,
        "Each directory is a review unit: markdown narrative + figures + source-path provenance.",
        ha="center",
        va="center",
        fontsize=10,
        color="#333333",
    )
    savefig(out / "00_review_map" / "review_pipeline.png")


def draw_laue_outcomes(out: Path, summary: dict) -> None:
    labels = ["diffracted", "absorbed", "transmitted"]
    values = [
        summary["diffraction_fraction"],
        summary["absorption_fraction"],
        summary["transmission_fraction"],
    ]
    colors = ["#2f7ed8", "#d9544f", "#7aa35a"]
    fig, ax = plt.subplots(figsize=(6.6, 4))
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylim(0, max(values) * 1.25)
    ax.set_ylabel("fraction")
    ax.set_title("Laue Barhoum-style baseline branch fractions")
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.01, f"{val:.4f}", ha="center", fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    savefig(out / "01_laue_barhoum_baseline" / "laue_barhoum_outcomes.png")


def draw_laue_per_ring(out: Path, per_ring: list[dict]) -> None:
    x = [row["design_energy_keV"] for row in per_ring]
    mean_p = [row["mean_p_diff"] for row in per_ring]
    sampled = [row["diffraction_fraction"] for row in per_ring]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(x, mean_p, marker="o", lw=2, label="mean table p_diff")
    ax.plot(x, sampled, marker="s", lw=2, label="sampled diffraction fraction")
    ax.set_xlabel("design energy (keV)")
    ax.set_ylabel("diffraction probability / fraction")
    ax.set_title("Laue baseline per-ring Darwin probability check")
    ax.grid(alpha=0.25)
    ax.legend()
    savefig(out / "01_laue_barhoum_baseline" / "laue_per_ring_darwin.png")


def draw_laue_wrl_quicklook(repo: Path, out: Path, subdir: str, run_dir: str, title: str, filename: str) -> None:
    rings = load_csv_dicts(repo, "data/laue/ge111_480_550keV_multiring_darwin_config.csv")
    phase_rows = load_csv_dicts(repo, f"{run_dir}/phase_space.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
    ax = axes[0]
    for row in rings:
        radius_cm = float(row["radius_mm"]) / 10.0
        n_tiles = int(row["n_tiles"])
        tile_cm = float(row["tile_size_mm"]) / 10.0
        phi = [2.0 * 3.141592653589793 * i / n_tiles for i in range(n_tiles)]
        ax.scatter(
            [radius_cm * math.cos(p) for p in phi],
            [radius_cm * math.sin(p) for p in phi],
            s=max(6, tile_cm * 32),
            alpha=0.65,
            label=f"{float(row['design_energy_keV']):.0f} keV",
        )
        circ = plt.Circle((0, 0), radius_cm, fill=False, color="#53616f", lw=0.8, alpha=0.35)
        ax.add_patch(circ)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x at lens plane (cm)")
    ax.set_ylabel("y at lens plane (cm)")
    ax.set_title("WRL lens-plane objects")
    ax.grid(alpha=0.22)
    ax.legend(fontsize=7, loc="upper right")

    ax2 = axes[1]
    xs = [float(row["x_mm"]) / 10.0 for row in phase_rows[:5000]]
    ys = [float(row["y_mm"]) / 10.0 for row in phase_rows[:5000]]
    if xs:
        ax2.scatter(xs, ys, s=4, alpha=0.25, color="#be3f3f")
    ax2.set_aspect("equal", adjustable="box")
    ax2.set_xlabel("x at focal plane (cm)")
    ax2.set_ylabel("y at focal plane (cm)")
    ax2.set_title("focal hits from phase_space.csv")
    ax2.grid(alpha=0.22)
    fig.suptitle(title, fontsize=12, weight="bold")
    savefig(out / subdir / filename)


def write_laue_review_wrl(repo: Path, out: Path, subdir: str, run_dir: str, title: str) -> None:
    rings = load_csv_dicts(repo, "data/laue/ge111_480_550keV_multiring_darwin_config.csv")
    history_rows = load_csv_dicts(repo, f"{run_dir}/optics_history.csv")
    path = out / subdir / "laue_multiring_scene.wrl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "#VRML V2.0 utf8",
        f'WorldInfo {{ title "{title}" }}',
        'Viewpoint { position 0 -310 135 orientation 1 0 0 1.15 description "Laue review scene" }',
        "Background { skyColor [ 1 1 1 ] }",
    ]
    for ring in rings:
        radius_mm = float(ring["radius_mm"])
        lines.append(
            "Shape { appearance Appearance { material Material { emissiveColor 0.1 0.45 0.9 "
            "diffuseColor 0.1 0.45 0.9 transparency 0.15 } } geometry IndexedLineSet { coord Coordinate { point ["
        )
        n_circle = 144
        for idx in range(n_circle + 1):
            phi = 2.0 * math.pi * idx / n_circle
            lines.append(f"{radius_mm * math.cos(phi):.6g} {radius_mm * math.sin(phi):.6g} 0,")
        lines.append("] } coordIndex [")
        for idx in range(n_circle):
            lines.append(f"{idx}, {idx + 1}, -1,")
        lines.append("] } }")
        n_tiles = int(ring["n_tiles"])
        tile_size = float(ring["tile_size_mm"])
        thickness = float(ring["thickness_mm"]) * 0.15
        for idx in range(n_tiles):
            phi = 2.0 * math.pi * idx / n_tiles
            lines.append(
                f"Transform {{ translation {radius_mm * math.cos(phi):.6g} {radius_mm * math.sin(phi):.6g} 0 "
                "children [ Shape { appearance Appearance { material Material { diffuseColor 0.0 0.55 0.25 } } "
                f"geometry Box {{ size {tile_size:.6g} {tile_size:.6g} {thickness:.6g} }} }} ] }}"
            )
    lines.append(
        "Transform { translation 0 0 8300 children [ Shape { appearance Appearance { material Material { diffuseColor 0.9 0.1 0.1 } } geometry Sphere { radius 5 } } ] }"
    )

    def add_segments(stage: str, color: tuple[float, float, float], limit: int = 90) -> None:
        rows = history_rows[:limit] if stage == "INCIDENT" else [row for row in history_rows if row["stage"] == stage][:limit]
        if not rows:
            return
        r, g, b = color
        lines.append(
            f"Shape {{ appearance Appearance {{ material Material {{ emissiveColor {r} {g} {b} diffuseColor {r} {g} {b} }} }} "
            "geometry IndexedLineSet { coord Coordinate { point ["
        )
        for row in rows:
            x = float(row["x_mm"])
            y = float(row["y_mm"])
            z = float(row["z_mm"])
            if stage == "INCIDENT":
                ux = float(row["ux_in"])
                uy = float(row["uy_in"])
                uz = float(row["uz_in"])
                start = (x - 60.0 * ux, y - 60.0 * uy, z - 60.0 * uz)
                end = (x, y, z)
            else:
                ux = float(row["ux_out"])
                uy = float(row["uy_out"])
                uz = float(row["uz_out"])
                if stage in {"DIFFRACT", "TRANSMIT"} and abs(uz) > 1.0e-12:
                    scale = (8300.0 - z) / uz
                else:
                    scale = 18.0
                start = (x, y, z)
                end = (x + scale * ux, y + scale * uy, z + scale * uz)
            lines.append(f"{start[0]:.6g} {start[1]:.6g} {start[2]:.6g},")
            lines.append(f"{end[0]:.6g} {end[1]:.6g} {end[2]:.6g},")
        lines.append("] } coordIndex [")
        for idx in range(len(rows)):
            lines.append(f"{2 * idx}, {2 * idx + 1}, -1,")
        lines.append("] } }")

    add_segments("INCIDENT", (0.05, 0.15, 0.95))
    add_segments("DIFFRACT", (0.9, 0.05, 0.05))
    add_segments("TRANSMIT", (0.45, 0.45, 0.45))
    add_segments("ABSORB", (0.95, 0.6, 0.0))
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def draw_guan_schematic(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 4.2))
    ax.set_axis_off()
    boxes = [
        (0.04, 0.58, 0.16, 0.23, "G4 primary\n511 keV gamma"),
        (0.28, 0.58, 0.20, 0.23, "GuanStyleLaue\nBraggProcess"),
        (0.56, 0.58, 0.18, 0.23, "Darwin/Zachariasen\nmosaic model"),
        (0.82, 0.58, 0.14, 0.23, "branch sample\n+ direction"),
        (0.28, 0.16, 0.20, 0.23, "Barhoum-style\napp process"),
        (0.56, 0.16, 0.18, 0.23, "same local\nDarwin table"),
        (0.82, 0.16, 0.14, 0.23, "same output\ncontract"),
    ]
    for x, y, w, h, label in boxes:
        ax.add_patch(Rectangle((x, y), w, h, facecolor="#f7f8fb", edgecolor="#4d617a", lw=1.4))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=10)
    arrows = [
        ((0.20, 0.70), (0.28, 0.70)),
        ((0.48, 0.70), (0.56, 0.70)),
        ((0.74, 0.70), (0.82, 0.70)),
        ((0.48, 0.28), (0.56, 0.28)),
        ((0.74, 0.28), (0.82, 0.28)),
    ]
    for start, end in arrows:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14, color="#56616f", lw=1.2))
    ax.text(0.04, 0.32, "comparison\nbaseline", ha="left", va="center", fontsize=9, color="#555555")
    ax.text(0.50, 0.93, "Compiled C++ process/model split, not a Geant4 EM-category patch", ha="center", fontsize=12, weight="bold")
    savefig(out / "02_laue_darwin_guan_process" / "guan_process_schematic.png")


def draw_guan_metrics(out: Path, barhoum: dict, guan: dict) -> None:
    metrics = ["diffraction_fraction", "absorption_fraction", "transmission_fraction", "spot_d90_cm"]
    labels = ["diffraction", "absorption", "transmission", "spot D90 cm"]
    x = range(len(metrics))
    width = 0.36
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    ax = axes[0]
    ax.bar([i - width / 2 for i in x[:3]], [barhoum[m] for m in metrics[:3]], width=width, label="Barhoum-style", color="#749bd1")
    ax.bar([i + width / 2 for i in x[:3]], [guan[m] for m in metrics[:3]], width=width, label="Guan-style", color="#91b66e")
    ax.set_xticks(list(x[:3]), labels[:3], rotation=15)
    ax.set_ylabel("fraction")
    ax.set_title("branch fractions")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    ax2 = axes[1]
    ax2.bar(["Barhoum-style", "Guan-style"], [barhoum["spot_d90_cm"], guan["spot_d90_cm"]], color=["#749bd1", "#91b66e"])
    ax2.set_ylabel("cm")
    ax2.set_title("focal spot D90")
    ax2.grid(axis="y", alpha=0.25)
    savefig(out / "02_laue_darwin_guan_process" / "guan_vs_barhoum_metrics.png")


def draw_guan_per_ring(out: Path, barhoum_ring: list[dict], guan_ring: list[dict]) -> None:
    energies = [row["design_energy_keV"] for row in barhoum_ring]
    b_mean = [row["mean_p_diff"] for row in barhoum_ring]
    g_mean = [row["mean_p_diff"] for row in guan_ring]
    b_sample = [row["diffraction_fraction"] for row in barhoum_ring]
    g_sample = [row["diffraction_fraction"] for row in guan_ring]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(energies, b_mean, "o-", label="Barhoum mean p_diff")
    ax.plot(energies, g_mean, "s--", label="Guan mean p_diff")
    ax.plot(energies, b_sample, "o:", label="Barhoum sampled")
    ax.plot(energies, g_sample, "s:", label="Guan sampled")
    ax.set_xlabel("design energy (keV)")
    ax.set_ylabel("diffraction probability / fraction")
    ax.set_title("Per-ring equivalence and Monte Carlo fluctuation")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    savefig(out / "02_laue_darwin_guan_process" / "guan_vs_barhoum_per_ring.png")


def draw_channel_outcomes(out: Path, summary: dict) -> None:
    labels = ["survived", "absorbed", "entry blocked", "leaked"]
    values = [
        summary["n_survived"],
        summary["n_absorbed"],
        summary["n_entry_blocked"],
        summary["n_leaked"],
    ]
    total = summary["n_primaries"]
    colors = ["#5b9f6a", "#cf5757", "#b9a35d", "#748ca9"]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bars = ax.bar(labels, values, color=colors)
    ax.set_ylabel("events")
    ax.set_title("Channel wall-by-wall outcomes")
    ax.grid(axis="y", alpha=0.25)
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + total * 0.015,
            f"{val}\n{val / total:.1%}",
            ha="center",
            va="bottom",
            fontsize=8.5,
        )
    savefig(out / "03_channel_wallbywall" / "channel_wallbywall_outcomes.png")


def draw_channel_closure(out: Path, closure: dict) -> None:
    variants = closure["wallbywall_variants"]
    labels = []
    values = []
    colors = []
    for item in variants:
        si = "with Si" if item["include_si_path_absorption"] else "no Si"
        labels.append(f"{item['roughness_nm']:.0f} nm\n{si}")
        values.append(item["transmissivity"])
        colors.append("#c75a5a" if item["include_si_path_absorption"] else "#5c9f69")
    target = closure["cam511_target"]["transmissivity"]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.bar(labels, values, color=colors)
    ax.axhline(target, color="#222222", lw=1.5, ls="--", label="CAM511 headline 0.80")
    ax.set_ylim(0, max(target, max(values)) * 1.18)
    ax.set_ylabel("transmissivity")
    ax.set_title("Channel closure variants without a calibration factor")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.015, f"{val:.3f}", ha="center", fontsize=8)
    savefig(out / "03_channel_wallbywall" / "channel_closure_variants.png")


def load_channel_yaml(repo: Path) -> dict:
    import yaml

    with (repo / "config/cam511_channel_baseline.yaml").open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def default_channel_tiles(radius_cm: float, width_cm: float) -> int:
    return max(1, int(round(2.0 * math.pi * radius_cm / width_cm)))


def draw_channel_wrl_quicklook(repo: Path, out: Path) -> None:
    cfg = load_channel_yaml(repo)
    phase_rows = load_csv_dicts(repo, "runs/channel_wallbywall_rebuild/phase_space.csv")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.3))
    ax = axes[0]
    for ring in cfg["rings"]:
        radius_cm = float(ring["radius_cm"])
        width_cm = float(ring["width_cm"])
        n_tiles = default_channel_tiles(radius_cm, width_cm)
        phi = [2.0 * math.pi * i / n_tiles for i in range(n_tiles)]
        ax.scatter(
            [radius_cm * math.cos(p) for p in phi],
            [radius_cm * math.sin(p) for p in phi],
            s=18,
            alpha=0.65,
            label=f"ring {ring['id']}",
        )
        ax.add_patch(plt.Circle((0, 0), radius_cm, fill=False, color="#53616f", lw=0.8, alpha=0.35))
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x at lens plane (cm)")
    ax.set_ylabel("y at lens plane (cm)")
    ax.set_title("public four-ring channel aperture")
    ax.grid(alpha=0.22)
    ax.legend(fontsize=7)

    ax2 = axes[1]
    xs = [float(row["x_mm"]) / 10.0 for row in phase_rows[:6000]]
    ys = [float(row["y_mm"]) / 10.0 for row in phase_rows[:6000]]
    if xs:
        ax2.scatter(xs, ys, s=4, alpha=0.25, color="#be3f3f")
    ax2.set_aspect("equal", adjustable="box")
    ax2.set_xlabel("x at focal plane (cm)")
    ax2.set_ylabel("y at focal plane (cm)")
    ax2.set_title("EXIT photons from phase_space.csv")
    ax2.grid(alpha=0.22)
    fig.suptitle("Channel wall-by-wall WRL-style quicklook", fontsize=12, weight="bold")
    savefig(out / "03_channel_wallbywall" / "channel_wrl_quicklook.png")


def write_channel_wrl_scene(repo: Path, out: Path) -> None:
    cfg = load_channel_yaml(repo)
    history_rows = load_csv_dicts(repo, "runs/channel_wallbywall_rebuild/optics_history.csv")
    path = out / "03_channel_wallbywall" / "channel_wallbywall_scene.wrl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "#VRML V2.0 utf8",
        'WorldInfo { title "Opticsim public-geometry channel wall-by-wall scene" }',
        'Viewpoint { position 0 -240 120 orientation 1 0 0 1.1 description "Channel wall-by-wall" }',
        "Background { skyColor [ 1 1 1 ] }",
    ]
    for ring in cfg["rings"]:
        radius_mm = float(ring["radius_cm"]) * 10.0
        lines.append(
            "Shape { appearance Appearance { material Material { emissiveColor 0.10 0.42 0.78 "
            "diffuseColor 0.10 0.42 0.78 transparency 0.15 } } geometry IndexedLineSet { coord Coordinate { point ["
        )
        n_circle = 144
        for idx in range(n_circle + 1):
            phi = 2.0 * math.pi * idx / n_circle
            lines.append(f"{radius_mm * math.cos(phi):.6g} {radius_mm * math.sin(phi):.6g} 0,")
        lines.append("] } coordIndex [")
        for idx in range(n_circle):
            lines.append(f"{idx}, {idx + 1}, -1,")
        lines.append("] } }")

    def first_rows_by_event(limit: int) -> list[dict[str, str]]:
        selected: list[dict[str, str]] = []
        seen: set[str] = set()
        for row in history_rows:
            event_id = row.get("event_id", "")
            if event_id in seen:
                continue
            seen.add(event_id)
            selected.append(row)
            if len(selected) >= limit:
                break
        return selected

    def add_segments(stage: str, color: tuple[float, float, float], limit: int = 80) -> None:
        selected = first_rows_by_event(limit) if stage == "INCIDENT" else [row for row in history_rows if row.get("stage") == stage][:limit]
        if not selected:
            return
        r, g, b = color
        lines.append(
            f"Shape {{ appearance Appearance {{ material Material {{ emissiveColor {r} {g} {b} diffuseColor {r} {g} {b} }} }} "
            "geometry IndexedLineSet { coord Coordinate { point ["
        )
        for row in selected:
            x = float(row["x_mm"])
            y = float(row["y_mm"])
            z = float(row["z_mm"])
            if stage == "INCIDENT":
                ux = float(row["ux_in"])
                uy = float(row["uy_in"])
                uz = float(row["uz_in"])
                start = (x - 25.0 * ux, y - 25.0 * uy, z - 25.0 * uz)
                end = (x, y, z)
            else:
                ux = float(row["ux_out"])
                uy = float(row["uy_out"])
                uz = float(row["uz_out"])
                scale = 25.0 if stage != "EXIT" else 200.0
                start = (x, y, z)
                end = (x + scale * ux, y + scale * uy, z + scale * uz)
            lines.append(f"{start[0]:.6g} {start[1]:.6g} {start[2]:.6g},")
            lines.append(f"{end[0]:.6g} {end[1]:.6g} {end[2]:.6g},")
        lines.append("] } coordIndex [")
        for idx in range(len(selected)):
            lines.append(f"{2 * idx}, {2 * idx + 1}, -1,")
        lines.append("] } }")

    add_segments("INCIDENT", (0.05, 0.15, 0.95))
    add_segments("BOUNCE", (0.05, 0.55, 0.25))
    add_segments("EXIT", (0.90, 0.05, 0.05))
    add_segments("ABSORB", (0.95, 0.55, 0.00))
    add_segments("LEAK", (0.45, 0.45, 0.45))
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def draw_detector_bridge(out: Path, detector: dict, activation: dict, focal: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    ax = axes[0]
    labels = ["simulated", "TES detected", "BGO veto"]
    values = [detector["n_simulated"], detector["n_tes_detected"], detector["n_bgo_veto"]]
    ax.bar(labels, values, color=["#778ca3", "#6aaa64", "#c75a5a"])
    ax.set_title("Detector wall-by-wall 1k smoke")
    ax.set_ylabel("events")
    ax.grid(axis="y", alpha=0.25)
    ax2 = axes[1]
    labels2 = ["inventory", "radioactive", "decay rows", "focal crossings"]
    values2 = [
        activation.get("n_inventory_rows", 0),
        activation.get("n_radioactive_rows", 0),
        activation.get("n_decay_source_rows", 0),
        focal.get("n_crossings", 0),
    ]
    ax2.bar(labels2, values2, color=["#778ca3", "#b89045", "#6b9ebf", "#6aaa64"])
    ax2.set_title("Activation builder + focal smoke")
    ax2.tick_params(axis="x", rotation=15)
    ax2.grid(axis="y", alpha=0.25)
    savefig(out / "04_detector_activation_bridge" / "detector_activation_smoke.png")


def draw_handoff_schematic(out: Path) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 4))
    ax.set_axis_off()
    boxes = [
        (0.04, 0.58, 0.18, 0.22, "optics phase space\nCSV"),
        (0.30, 0.58, 0.16, 0.22, "detector Geant4\nTES/BGO hits"),
        (0.54, 0.58, 0.16, 0.22, "I/O contract\nvalidation"),
        (0.78, 0.58, 0.17, 0.22, "reviewable\nsummary"),
        (0.04, 0.18, 0.18, 0.22, "all-particle\nprompt transport"),
        (0.30, 0.18, 0.16, 0.22, "true-position\ninventory"),
        (0.54, 0.18, 0.16, 0.22, "decay source\nbuilder"),
        (0.78, 0.18, 0.17, 0.22, "focal decay\ntransport"),
    ]
    for x, y, w, h, label in boxes:
        ax.add_patch(Rectangle((x, y), w, h, facecolor="#f7f8fb", edgecolor="#4d617a", lw=1.3))
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=10)
    for y in [0.69, 0.29]:
        for x1, x2 in [(0.22, 0.30), (0.46, 0.54), (0.70, 0.78)]:
            ax.add_patch(FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>", mutation_scale=14, color="#56616f", lw=1.2))
    ax.text(0.5, 0.92, "Two handoffs to review: science photons and delayed activation", ha="center", fontsize=12, weight="bold")
    savefig(out / "04_detector_activation_bridge" / "detector_activation_handoff.png")


def draw_risk_matrix(out: Path) -> None:
    rows = ["Laue baseline", "Guan process", "Channel optics", "Detector bridge", "Activation"]
    cols = ["formula", "geometry", "code path", "benchmark", "production gap"]
    values = [
        [1, 1, 1, 2, 2],
        [1, 1, 1, 1, 2],
        [1, 2, 1, 2, 3],
        [1, 2, 1, 2, 3],
        [2, 3, 2, 3, 3],
    ]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    image = ax.imshow(values, cmap="YlOrRd", vmin=1, vmax=3)
    ax.set_xticks(range(len(cols)), cols)
    ax.set_yticks(range(len(rows)), rows)
    ax.set_title("Review attention matrix: 1=low, 2=medium, 3=high")
    for i, row in enumerate(values):
        for j, value in enumerate(row):
            ax.text(j, i, str(value), ha="center", va="center", fontsize=11, weight="bold")
    plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    savefig(out / "05_review_checklist" / "review_attention_matrix.png")


def markdown_table_from_map(rows: list[dict[str, object]]) -> str:
    lines = ["| file | line | function/class | role | review focus |", "|---|---:|---|---|---|"]
    for row in rows:
        lines.append(
            f"| `{row['file']}` | {row['line']} | `{row['symbol']}` | {row['role']} | {row['review_focus']} |"
        )
    return "\n".join(lines)


def write_deep_dive_docs(
    repo: Path,
    out: Path,
    barhoum: dict,
    guan: dict,
    comparison: dict,
    channel: dict,
    closure: dict,
) -> None:
    laue_map = [
        {"file": "external_baseline/laue_raytrace_py/mosaic_darwin.py", "line": 56, "symbol": "bragg_angle_rad", "role": "由能量和晶面间距计算 Bragg 角。", "review_focus": "能量单位 keV、d-spacing 单位 Angstrom 是否一致。"},
        {"file": "external_baseline/laue_raytrace_py/mosaic_darwin.py", "line": 132, "symbol": "darwin_mosaic_probabilities", "role": "给出 p_diff、p_abs、p_trans 的物理概率。", "review_focus": "吸收项、mosaic 权重、概率归一化。"},
        {"file": "external_baseline/laue_raytrace_py/build_mosaic_darwin_table.py", "line": 104, "symbol": "_write_table", "role": "扫描 delta-theta 并写出 Darwin 概率表。", "review_focus": "delta 网格范围、mosaic arcsec、厚度。"},
        {"file": "geant4_app/src/optics/LaueEfficiencyTable.cc", "line": 55, "symbol": "ValidateProbabilities", "role": "检查三分支概率非负且和为 1。", "review_focus": "这是防止表损坏的第一道闸。"},
        {"file": "geant4_app/src/optics/LaueEfficiencyTable.cc", "line": 156, "symbol": "LaueEfficiencyTable::Lookup", "role": "按材料/晶面/能量找最近能量，并按 delta-theta 插值。", "review_focus": "是否误用最近能量、是否 clamp 到表边界。"},
        {"file": "geant4_app/src/laue_multiring_table_demo.cc", "line": 191, "symbol": "LoadRingConfig", "role": "读取五环 Ge(111) 配置并核对半径与 Bragg 半径。", "review_focus": "半径是否由 F*tan(2thetaB) 支持。"},
        {"file": "geant4_app/src/laue_multiring_table_demo.cc", "line": 300, "symbol": "MultiRingRunState::Record", "role": "记录 ABSORB/TRANSMIT/DIFFRACT，写 phase_space 和 history。", "review_focus": "输出 schema 和 stage 语义。"},
        {"file": "geant4_app/src/laue_multiring_table_demo.cc", "line": 504, "symbol": "MultiRingProcess::PostStepDoIt", "role": "Geant4 离散过程：边界触发、查表、抽样、生成二次 gamma。", "review_focus": "只作用 primary gamma 和 LaueCrystal 边界。"},
        {"file": "geant4_app/src/laue_multiring_table_demo.cc", "line": 566, "symbol": "MultiRingDetectorConstruction::Construct", "role": "把 ring/tile 放进 Geant4 world。", "review_focus": "copy number 与 ring/tile 对应。"},
        {"file": "geant4_app/src/laue_multiring_table_demo.cc", "line": 650, "symbol": "main", "role": "装配 options、geometry、table、process、primary generator，并 BeamOn。", "review_focus": "输入文件和 seed 是否是记录中的版本。"},
    ]
    guan_map = [
        {"file": "geant4_app/src/laue_multiring_darwin_guan_demo.cc", "line": 190, "symbol": "OnlineDarwinMosaicProbabilities", "role": "在线计算 p_diff/p_abs/p_trans，不读取 01 概率表。", "review_focus": "确认 02 的物理后端不是 01 的 CSV 查表。"},
        {"file": "geant4_app/src/laue_multiring_darwin_guan_demo.cc", "line": 224, "symbol": "ReflectAcrossPlane", "role": "按晶面法线做镜面反射方向计算。", "review_focus": "反射几何是否与 Bragg 平面定义一致。"},
        {"file": "geant4_app/src/laue_multiring_darwin_guan_demo.cc", "line": 230, "symbol": "PerturbDirection", "role": "用 mosaic sigma 给衍射方向加小角度散布。", "review_focus": "sigma 单位由 arcsec 转 rad。"},
        {"file": "geant4_app/src/laue_multiring_darwin_guan_demo.cc", "line": 292, "symbol": "LoadRingConfig", "role": "与 01 相同的五环几何读取和 Bragg 半径核验。", "review_focus": "确保 same-geometry comparison。"},
        {"file": "geant4_app/src/laue_multiring_darwin_guan_demo.cc", "line": 614, "symbol": "GuanDarwinDynamicalModel", "role": "把 Bragg mismatch、晶面法线、理想出射方向和在线 Darwin 概率集中在模型层。", "review_focus": "这是 02 与 01 的主要架构和物理后端差异。"},
        {"file": "geant4_app/src/laue_multiring_darwin_guan_demo.cc", "line": 618, "symbol": "GuanDarwinDynamicalModel::Evaluate", "role": "计算 focusPoint、planeNormal、deltaTheta，并调用在线 Darwin-Hamilton mosaic 模型。", "review_focus": "deltaTheta 定义是否与 01 等价，概率是否不再查表。"},
        {"file": "geant4_app/src/laue_multiring_darwin_guan_demo.cc", "line": 644, "symbol": "GuanStyleLaueBraggProcess", "role": "Geant4 process adapter，只处理 step 条件、抽样和 secondary。", "review_focus": "物理和 Geant4 glue 是否拆开。"},
        {"file": "geant4_app/src/laue_multiring_darwin_guan_demo.cc", "line": 661, "symbol": "GuanStyleLaueBraggProcess::PostStepDoIt", "role": "调用模型 Evaluate 后走 ABSORB/TRANSMIT/DIFFRACT 三分支。", "review_focus": "process 是否只做 Geant4 adapter。"},
        {"file": "geant4_app/src/laue_multiring_darwin_guan_demo.cc", "line": 750, "symbol": "MultiRingPhysicsList::ConstructProcess", "role": "把 process 加到 gamma process manager。", "review_focus": "这是 app-level discrete process，不是 EM-category patch。"},
        {"file": "analysis/compare_geant4_darwin_guan_vs_barhoum.py", "line": 23, "symbol": "compare", "role": "对 02 和 01 的 summary/per-ring 输出做数值闭合。", "review_focus": "mean p_diff delta 和 sampled fraction delta 分开看。"},
    ]
    channel_map = [
        {"file": "external_baseline/channel_raytrace_py/geometry.py", "line": 75, "symbol": "load_channel_config", "role": "读取 CAM511 public geometry YAML。", "review_focus": "四环半径、长度、弯角、W/Si 厚度。"},
        {"file": "external_baseline/channel_raytrace_py/parratt_reflectivity.py", "line": 90, "symbol": "compute_reflectivity_rows", "role": "用 xraydb multilayer reflectivity 生成 R/A/T(theta)。", "review_focus": "511 keV、W/Si 30/150 nm、roughness。"},
        {"file": "external_baseline/channel_raytrace_py/parratt_reflectivity.py", "line": 142, "symbol": "manual_parratt_reflectivity_s", "role": "独立 Parratt recursion 交叉核验。", "review_focus": "不要只相信一个库函数。"},
        {"file": "external_baseline/channel_raytrace_py/wallbywall_channel.py", "line": 86, "symbol": "simulate_wallbywall_channel", "role": "主 Monte Carlo loop：采样入口、trace、汇总 history。", "review_focus": "没有输入固定反射次数。"},
        {"file": "external_baseline/channel_raytrace_py/wallbywall_channel.py", "line": 325, "symbol": "_sample_entrance", "role": "按 ring 面积和 W/Si 周期采样入口点。", "review_focus": "W 层 entry blocked，Si spacer 才进入。"},
        {"file": "external_baseline/channel_raytrace_py/wallbywall_channel.py", "line": 399, "symbol": "_trace_one_event", "role": "在弯曲 channel 内逐墙求交、查 R/A/T、反射/吸收/泄漏。", "review_focus": "反射次数由几何自然产生。"},
        {"file": "external_baseline/channel_raytrace_py/wallbywall_channel.py", "line": 628, "symbol": "_next_wall_hit", "role": "解二次方程找下一次撞墙位置。", "review_focus": "弯曲项和正根选择。"},
        {"file": "external_baseline/channel_raytrace_py/wallbywall_channel.py", "line": 662, "symbol": "_global_position_direction", "role": "把局部 channel 坐标转为全局 x/y/z 和方向。", "review_focus": "焦平面投影和 ring/tile 方位。"},
        {"file": "external_baseline/channel_raytrace_py/wallbywall_channel.py", "line": 125, "symbol": "summarize_wallbywall", "role": "计算 transmissivity、Aeff、D90、bounce/grazing-angle 统计。", "review_focus": "性能数值的来源。"},
        {"file": "analysis/run_channel_wallbywall_rebuild.py", "line": 23, "symbol": "main", "role": "CLI runner，连接 config、reflectivity table 和 wall-by-wall 核心。", "review_focus": "默认是否含 Si path absorption。"},
        {"file": "analysis/build_channel_independent_closure.py", "line": 121, "symbol": "optical_constant_checks", "role": "低能 CXRO/Henke 范围和 511 keV electron-density/xraydb 检查。", "review_focus": "光学常数闭合边界。"},
        {"file": "analysis/build_channel_independent_closure.py", "line": 184, "symbol": "run_wallbywall_variant", "role": "扫描 roughness 和 Si path absorption 的 no-fudge variants。", "review_focus": "与 CAM511 0.80 headline 的差距来自哪里。"},
    ]
    write_csv(out / "01_laue_barhoum_baseline" / "code_function_map.csv", laue_map)
    write_csv(out / "02_laue_darwin_guan_process" / "code_function_map.csv", guan_map)
    write_csv(out / "03_channel_wallbywall" / "code_function_map.csv", channel_map)

    write_text(
        out / "01_laue_barhoum_baseline" / "implementation_manual.md",
        f"""
# 01 implementation manual: Laue Barhoum-style baseline

## 给没接触过本工作的人的一句话

这一步是在 Geant4 里放一个五环 Ge(111) Laue lens。每个 gamma 打到晶体边界时，代码不使用经验校正因子，而是从本地 Zachariasen/Darwin mosaic 表查出 `p_abs / p_diff / p_trans`，再在 Geant4 的 `G4VDiscreteProcess::PostStepDoIt` 里随机抽样：吸收、透过或衍射到焦平面。

## 物理原理

1. Bragg 条件给出每个 ring 应该收哪一段能量：`lambda = 2 d sin(theta_B)`。
2. 焦距 `F` 固定后，ring 半径近似由 `R = F tan(2 theta_B)` 决定。
3. mosaic crystal 不是 perfect crystal：微晶取向有角分布，所以 `delta_theta = theta_local - theta_B` 会改变衍射效率。
4. `external_baseline/laue_raytrace_py/mosaic_darwin.py` 用结构因子、extinction length、mosaic weight、吸收系数计算三分支概率。
5. Geant4 只负责事件输运、几何边界、secondary gamma 和输出 phase space。

## 当前运行结果

{table([
    ("primaries", barhoum["n_primaries"]),
    ("diffraction fraction", barhoum["diffraction_fraction"]),
    ("absorption fraction", barhoum["absorption_fraction"]),
    ("transmission fraction", barhoum["transmission_fraction"]),
    ("spot D90 cm", barhoum["spot_d90_cm"]),
    ("WRL", barhoum["visualization_wrl"]),
])}

## 代码函数地图

{markdown_table_from_map(laue_map)}

## 复现流程

1. 生成或更新 Darwin 表：

```bash
python3 -m external_baseline.laue_raytrace_py.build_mosaic_darwin_table \\
  --ring-config data/laue/ge111_480_550keV_multiring_darwin_config.csv \\
  --out-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv \\
  --mosaic-arcsec 30 \\
  --crystallite-um 5 \\
  --delta-multiple 4 \\
  --n-delta 81 \\
  --optimize-thickness
```

2. 构建 Geant4 executable：

```bash
cmake --build /tmp/opticsim-build-g4-11.4.0 --target laue_multiring_table_demo
```

3. 运行主样本：

```bash
/tmp/opticsim-build-g4-11.4.0/laue_multiring_table_demo \\
  --n 100000 \\
  --seed 20260520 \\
  --ring-config data/laue/ge111_480_550keV_multiring_darwin_config.csv \\
  --efficiency-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv \\
  --out runs/geant4_laue_multiring_darwin
```

## 输出文件怎么读

- `phase_space.csv`：只记录衍射后到焦平面的 gamma，可直接喂给后续 detector chain。
- `transmitted_space.csv`：未被吸收也未衍射的透过 gamma。
- `optics_history.csv`：每个 primary 在 lens 边界发生了哪种 stage，包含查表概率。
- `per_ring_summary.json`：每个 ring 的抽样分支和 mean table probability。
- `summary.json`：总 branch fraction、spot D90、输入表路径和 WRL 路径。
- `laue_multiring_scene.wrl`：Geant4/VRML 可视化场景。

## WRL 可视化

![WRL quicklook](laue_wrl_quicklook.png)

可直接打开本目录的 `laue_multiring_scene.wrl`。它是从 `ring_config` 和 `optics_history.csv` 重新生成的审阅 WRL：蓝色 ring 用 `IndexedLineSet` 画在 x-y lens plane，深蓝线段显示 incident beam 打到 tile 的入射段，红/灰/黄线段分别显示 DIFFRACT/TRANSMIT/ABSORB。这样避免旧 WRL 里 decorative cylinder 造成的视角误导。

这份 PNG 是从同一 ring config 和 `phase_space.csv` 生成的 quicklook，方便不装 WRL viewer 时先检查几何和焦斑。

## 审阅优先级

先审 `LoadRingConfig` 的 Bragg 半径核验，再审 `LaueEfficiencyTable::Lookup` 的 delta-theta 插值，最后审 `MultiRingProcess::PostStepDoIt` 的三分支抽样和 secondary 方向。
""",
    )

    write_text(
        out / "01_laue_barhoum_baseline" / "code_commentary.md",
        """
# 01 annotated code commentary

## Table builder side

```text
bragg_angle_rad()
  输入 E_keV 和 d_spacing_A，输出 theta_B。
  如果 lambda/(2d) 不在 (0,1)，立即报错，避免生成物理上不可能的 ring。

darwin_mosaic_probabilities()
  计算 mosaic 权重 w(delta_theta)，再得到 coherent sigma。
  p_abs 来自吸收透过率，p_diff 来自 Darwin mosaic diffraction efficiency * absorption transmission。
  最后把 p_diff + p_abs + p_trans 重新归一化，保证 Geant4 抽样是三分支概率。

_write_table()
  对每个 ring 的 design energy 扫描 delta_theta 网格。
  每个网格点写一行 E, theta_B, delta_theta, material, hkl, thickness, p_diff, p_abs, p_trans。
```

## Geant4 side

```text
MultiRingProcess::PostStepDoIt()
  1. 只处理 primary gamma。
  2. 只在 fGeomBoundary 且 volume 名含 LaueCrystal 时触发。
  3. 用 copyNo 找 ring 和 tile。
  4. 用 thetaLocal - thetaB 得到 deltaTheta。
  5. 查 LaueEfficiencyTable，得到 pAbs/pDiff/pTrans。
  6. 随机数 u < pAbs：吸收，kill track。
  7. u >= pAbs + pDiff：透过，kill track，并写 transmitted_space。
  8. 否则：生成一个二次 gamma 指向焦平面，写 phase_space。
```

## 这段代码最容易错在哪里

- ring 半径不是任意输入，必须和 `F tan(2 theta_B)` 对齐。
- `p_diff` 不是固定常数；它随 ring energy 和 `delta_theta` 变。
- Geant4 里 primary gamma 被 kill，衍射支路用 secondary gamma 表示，后续要读 `phase_space.csv` 而不是追原 track。
""",
    )

    write_text(
        out / "02_laue_darwin_guan_process" / "implementation_manual.md",
        f"""
# 02 implementation manual: Guan-style Darwin process split

## 给没接触过本工作的人的一句话

这一步是真正把 02 从 01 的查表变体中拆出来：`GuanDarwinDynamicalModel` 负责 Bragg/Darwin 物理判断和在线三分支概率计算，`GuanStyleLaueBraggProcess` 只负责接入 Geant4 tracking。它更接近 Guan/Reiazi 论文里“物理模型 + Geant4 process adapter”的路线，但仍不是他们的源码移植，也不是 Geant4 toolkit patch。

## 物理原理

1. 仍使用同一 Ge(111) 五环几何，方便与 01 做同结构对比。
2. 模型层在线计算理想焦点方向、晶面法线、局部 Bragg mismatch 和 Darwin-Hamilton mosaic 三分支概率。
3. process 层只在 Geant4 边界 step 触发，按模型返回的概率抽样。
4. 衍射方向由晶面法线反射得到，再加 virtual-crystallite/mosaic angular spread。

## 当前运行结果

{table([
    ("primaries", guan["n_primaries"]),
    ("diffraction fraction", guan["diffraction_fraction"]),
    ("absorption fraction", guan["absorption_fraction"]),
    ("transmission fraction", guan["transmission_fraction"]),
    ("spot D90 cm", guan["spot_d90_cm"]),
    ("uses 01 probability table", guan.get("uses_external_efficiency_table_for_physics")),
    ("online backend", guan.get("online_physics_backend")),
    ("registered in Geant4 EM category", guan["registered_in_geant4_em_category"]),
    ("WRL", guan["visualization_wrl"]),
])}

## 与 01 的数值闭合

{table([
    ("delta diffraction fraction", comparison["delta_diffraction_fraction"]),
    ("delta absorption fraction", comparison["delta_absorption_fraction"]),
    ("delta transmission fraction", comparison["delta_transmission_fraction"]),
    ("delta spot D90 cm", comparison["delta_spot_d90_cm"]),
    ("max abs delta mean p_diff by ring", comparison["max_abs_delta_mean_p_diff_by_ring"]),
])}

## 代码函数地图

{markdown_table_from_map(guan_map)}

## 复现流程

```bash
cmake --build /tmp/opticsim-build-g4-11.4.0 --target laue_multiring_darwin_guan_demo

/tmp/opticsim-build-g4-11.4.0/laue_multiring_darwin_guan_demo \\
  --n 100000 \\
  --seed 20260521 \\
  --ring-config data/laue/ge111_480_550keV_multiring_darwin_config.csv \\
  --efficiency-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv \\
  --mosaic-fwhm-arcsec 30 \\
  --crystallite-um 5 \\
  --out runs/geant4_laue_darwin_guan_process

python3 analysis/compare_geant4_darwin_guan_vs_barhoum.py
```

## 输出文件怎么读

- `summary.json`：明确写出 `model_process_split=true`、`registered_in_geant4_em_category=false` 和 `uses_external_efficiency_table_for_physics=false`。
- `barhoum_comparison_summary.json`：与 01 的直接数值差异。
- `per_ring_summary.json`：检查同 ring 的 mean `p_diff` 是否与 01 对齐。
- `laue_multiring_scene.wrl`：Guan-style run 自己输出的 WRL 场景。

## WRL 可视化

![WRL quicklook](guan_wrl_quicklook.png)

本目录的 `laue_multiring_scene.wrl` 是从 Guan-style run 的 `optics_history.csv` 重新生成的审阅 WRL。它显式画出 x-y lens plane 上的 ring、tile、incident segments 和输出分支，避免旧 decorative cylinder 视角下看起来像 beam 没打到 tile 的问题。

quicklook 左图显示同一五环几何，右图显示该 run 的焦平面 phase-space 点。

## 审阅优先级

先审 `OnlineDarwinMosaicProbabilities` 是否真的不读 01 概率表，再审 `GuanDarwinDynamicalModel::Evaluate` 的几何定义，最后看 `compare()` 里 online mean probability 和 sampled fraction 是否被混为一谈。
""",
    )

    write_text(
        out / "02_laue_darwin_guan_process" / "code_commentary.md",
        """
# 02 annotated code commentary

## Model/process split

```text
GuanDarwinDynamicalModel::Evaluate()
  1. 用焦距和 off-axis 参数定义 focusPoint。
  2. idealOutDir = focusPoint - hitPosition。
  3. planeNormal = inDir - idealOutDir，代表能把入射方向反射到理想出射方向的晶面法线。
  4. thetaLocal = 0.5 * angle(inDir, idealOutDir)。
  5. deltaTheta = thetaLocal - thetaB。
  6. 调用 OnlineDarwinMosaicProbabilities 在线计算 pAbs/pDiff/pTrans。

GuanStyleLaueBraggProcess::PostStepDoIt()
  1. 做 Geant4 step 过滤：primary gamma、geometry boundary、LaueCrystal volume。
  2. 调用 model_.Evaluate()。
  3. 根据 pAbs/pDiff/pTrans 抽样。
  4. DIFFRACT 分支使用 reflectedOutDir，再用 mosaic sigma 做方向扰动。
```

## 和 01 的真正区别

01 把几何、查表和 Geant4 抽样都写在 process 里。02 把 Bragg/Darwin 判断移到模型类里，并在模型层在线计算 Darwin-Hamilton mosaic 概率，所以它不再只是 01 的类名重构。当前没有做的事情也要明说：没有移植 Guan/Reiazi 源码，没有 patch Geant4 toolkit，也没有进入 Geant4 EM category。

## 最容易误读的地方

- `registered_process` 是 app-level 加到 gamma process manager，不等于 Geant4 官方 EM category 过程。
- 02 的可信度来自“同几何、在线模型与 01 表驱动 baseline 的数值闭合”，不是来自宣称拿到了 Guan/Reiazi 原始代码。
""",
    )

    best = closure["best_no_fudge_variant"]
    rough = closure["literature_roughness_1nm_no_si_variant"]
    write_text(
        out / "03_channel_wallbywall" / "implementation_manual.md",
        f"""
# 03 implementation manual: Channel wall-by-wall optics

## 给没接触过本工作的人的一句话

Channel 光学不是 Bragg 衍射，而是 511 keV gamma 在弯曲 W/Si multilayer spacer 中做小掠入射多次反射。当前实现不输入固定反射次数：每个 photon 从公开几何入口采样，在弯曲 channel 中逐墙求交，按 W/Si reflectivity table 抽样反射、吸收或泄漏，最后能到焦平面的才写入 `phase_space.csv`。

## 物理原理

1. W/Si 周期是 30 nm W + 150 nm Si，入口几何 open fraction 是 `150/(150+30)=0.8333`。
2. 落到 W 层的 photon 直接被 entry geometry block；落到 Si spacer 的 photon 才进入 channel。
3. 弯曲 channel 让局部 wall tangent 随路径长度变化，因此撞墙位置和 grazing angle 由几何自然产生。
4. 每次 wall hit 查 `R/A/T(E, theta)`，当前表来自 xraydb multilayer reflectivity，并用独立 Parratt recursion 做闭合。
5. 如果打开 Si path absorption，photon 在 spacer 中飞行的路径也会按 `exp(-mu * path)` 生存抽样。

## 当前运行结果

{table([
    ("primaries", channel["n_primaries"]),
    ("survived", channel["n_survived"]),
    ("transmissivity", channel["transmissivity"]),
    ("effective area cm2", channel["effective_area_cm2"]),
    ("spot D90 cm", channel["spot_d90_cm"]),
    ("mean bounces per survivor", channel["mean_bounces_per_survivor"]),
    ("include Si path absorption", channel["include_si_path_absorption"]),
])}

## no-fudge CAM511 对齐边界

{table([
    ("CAM511 target transmissivity", closure["cam511_target"]["transmissivity"]),
    ("best no-fudge transmissivity", best["transmissivity"]),
    ("best no-fudge delta", best["delta_to_cam511_transmissivity"]),
    ("1 nm roughness no-Si transmissivity", rough["transmissivity"]),
    ("no-fudge reaches CAM511", closure["no_fudge_reaches_cam511"]),
])}

## 代码函数地图

{markdown_table_from_map(channel_map)}

## 复现流程

主 wall-by-wall run：

```bash
python3 analysis/run_channel_wallbywall_rebuild.py \\
  --n 20000 \\
  --seed 20260521 \\
  --reflectivity-table data/reflectivity/WSi_511keV_parratt_grid_dense.csv \\
  --out runs/channel_wallbywall_rebuild
```

无 Si path absorption 的对照：

```bash
python3 analysis/run_channel_wallbywall_rebuild.py \\
  --n 5000 \\
  --seed 20260521 \\
  --no-si-path-absorption \\
  --out runs/channel_wallbywall_rebuild_no_si_abs_smoke
```

独立闭合包：

```bash
python3 analysis/build_channel_independent_closure.py
```

## 输出文件怎么读

- `wallbywall_events.csv`：每个 primary 的最终 outcome、bounce 数、路径长度。
- `optics_history.csv`：每一次 wall hit 的 stage、grazing angle、R/A/T。
- `phase_space.csv`：只有 `EXIT` photon，被投影到焦平面。
- `per_ring_summary.json`：每个 channel ring 的透过率和 bounce 统计。
- `summary.json`：总透过率、有效面积、D90、平均掠入射角和模型 warning。

## WRL 可视化

![WRL quicklook](channel_wrl_quicklook.png)

本目录里的 `channel_wallbywall_scene.wrl` 是用 `optics_history.csv` 的 wall-hit rows 生成的 WRL 审阅场景。蓝色 ring 用 `IndexedLineSet` 画在入口 x-y plane，不再用容易误导视角的 cylinder；深蓝线段显示 incident segment，绿色/红色/黄色/灰色分别表示 BOUNCE/EXIT/ABSORB/LEAK。

它不是原始 Geant4 可视化输出，而是基于本次 wall-by-wall path history 的审阅图，用来快速看 ring、wall-hit stage 和出射方向。

## 审阅优先级

先审 `_sample_entrance` 是否正确处理 W/Si open fraction，再审 `_next_wall_hit` 的几何求交和 `_trace_one_event` 的 R/A/T 抽样，最后审 no-fudge variants 是否把 roughness、Si path absorption 和 CAM511 headline 的差距说清楚。
""",
    )

    write_text(
        out / "03_channel_wallbywall" / "code_commentary.md",
        """
# 03 annotated code commentary

## Main loop

```text
simulate_wallbywall_channel()
  1. 先按 ring collecting area 抽一个 ring。
  2. 再在该 ring 上抽 tile 和入口位置。
  3. 如果抽到 W 层或支撑闭合部分，写 ENTRY_BLOCKED。
  4. 如果抽到 Si spacer，进入 _trace_one_event()。
```

## One photon trace

```text
_trace_one_event()
  state.s_mm      当前沿 channel 长度走了多远。
  state.q_mm      当前在 spacer gap 内的横向位置。
  state.alpha_rad 当前光线相对局部 channel tangent 的角度。

  while photon has not exited:
    _next_wall_hit() 解下一次撞哪一面墙。
    如果启用 Si path absorption，先对 spacer 路径做 exp(-mu*path) 抽样。
    lookup.lookup(abs(theta_hit)) 得到该 grazing angle 的 R/A/T。
    u < A           -> ABSORB
    u >= A + R      -> LEAK
    otherwise       -> BOUNCE, alpha 反号，继续下一墙

  EXIT photon 被投影到 focal_length_mm 平面，并写入 phase_space.csv。
```

## 独立闭合

```text
compute_reflectivity_rows()
  使用 xraydb.multilayer_reflectivity 生成 W/Si stack 的 R(theta)。

manual_parratt_reflectivity_s()
  不调用 xraydb.multilayer_reflectivity，只用 optical constants 手写 Parratt recursion。

build_channel_independent_closure.py
  用 roughness 和 Si path absorption 的组合扫描，检查不加校正因子时和 CAM511 0.80 headline 的距离。
```

## 最容易误读的地方

- wall-by-wall 不是 Geant4 navigation，而是 Python 独立 ray trace；Geant4 的价值在后续 detector/activation handoff。
- `max_bounces` 是死循环保护，不是物理上强行规定反射次数；实际 survivor mean bounces 来自几何和随机过程。
- `best_no_fudge_variant` 接近 CAM511 0.80，但没有完全闭合，不能偷加 multiplier。
""",
    )

def write_markdown(
    out: Path,
    barhoum: dict,
    guan: dict,
    comparison: dict,
    channel: dict,
    closure: dict,
    detector: dict,
    detector_contract: dict,
    activation: dict,
    focal_activation: dict,
) -> None:
    write_text(
        out / "README.md",
        f"""
# Opticsim stepwise review records

Date: 2026-05-22

This directory mirrors the `COSMOSRAY_BALLOON_SIM/Records` review style: split the work into small review units, and give each unit its own figures, local source paths, key numbers, and explicit non-claims. The purpose is bug hunting and later review, not a polished final paper.

![review pipeline](00_review_map/review_pipeline.png)

## Directory map

| step | directory | review purpose |
|---|---|---|
| 00 | `00_review_map` | Overall evidence map and review protocol. |
| 01 | `01_laue_barhoum_baseline` | Barhoum-style Laue baseline using the local Darwin/Zachariasen table. |
| 02 | `02_laue_darwin_guan_process` | Compiled Guan/Reiazi-inspired process/model split and direct comparison to 01. |
| 03 | `03_channel_wallbywall` | Channel wall-by-wall ray tracing, no calibration-factor closure, CAM511 alignment boundary. |
| 04 | `04_detector_activation_bridge` | Detector handoff and activation-source scaffold evidence. |
| 05 | `05_review_checklist` | Risk matrix and bug-review checklist. |
| 06 | `06_figure_scripts` | Rebuild script for all figures and markdown. |

Each of steps 01-03 also contains:

- `implementation_manual.md`: beginner-readable principle, function map, reproduction commands, and review priorities.
- `code_commentary.md`: annotated code walkthrough in plain language.
- `code_function_map.csv`: machine-readable file/function map for review.
- WRL scene or WRL-derived quicklook image.

## Regeneration

Run:

```bash
python3 records/stepwise_review_2026-05-22/06_figure_scripts/build_stepwise_review_records.py
```

The script only uses local run summaries already in this repository. It does not add a new physics claim beyond those summaries.
""",
    )

    write_text(
        out / "00_review_map" / "review_map.md",
        f"""
# 00 Review map

![pipeline](review_pipeline.png)

## What was copied from the COSMOSRAY Records style

- One physics or software step per directory.
- Each step has an `.md` file and at least one visual artifact.
- Each claim points back to a local source file, usually `summary.json` or `per_ring_summary.json`.
- Each step states what it does not prove, so later review can focus on the right weak point.

## Local source files used here

| evidence | path |
|---|---|
| Laue Barhoum-style baseline | `runs/geant4_laue_multiring_darwin/summary.json` |
| Laue baseline per ring | `runs/geant4_laue_multiring_darwin/per_ring_summary.json` |
| Guan-style compiled process | `runs/geant4_laue_darwin_guan_process/summary.json` |
| Guan vs Barhoum comparison | `runs/geant4_laue_darwin_guan_process/barhoum_comparison_summary.json` |
| Channel wall-by-wall | `runs/channel_wallbywall_rebuild/summary.json` |
| Channel independent closure | `runs/channel_independent_closure/summary.json` |
| Detector wall-by-wall smoke | `runs/geant4_detector_wallbywall_1k/summary.json` |
| Detector I/O contract | `runs/io_contract_validation_channel_wallbywall_detector_1k/summary.json` |
| Activation builder smoke | `runs/activation/synthetic_al28_day15/source_build_summary.json` |
| Activation focal smoke | `runs/activation/synthetic_al28_day15/focal_transport_no_neutrino/summary.json` |

## Current boundaries

- The Guan-style code is a compiled local process/model split. It is not a source-code migration of Guan or Reiazi and it is not registered inside the Geant4 EM category.
- The Channel code is a public-geometry wall-by-wall reconstruction. It is not the original 511-CAM IDL/IMD production model.
- The activation step in this repository is currently a workflow/smoke scaffold, not a production-statistics activation result.
""",
    )

    write_text(
        out / "01_laue_barhoum_baseline" / "laue_barhoum_baseline.md",
        f"""
# 01 Laue Barhoum-style baseline

This step records the current local Laue baseline. The implementation is a Geant4 application-level process driven by a local Ge(111) Darwin/Zachariasen mosaic table. In the code output this is called `multiring_zachariasen_darwin_mosaic_laue_process_v3`.

![outcomes](laue_barhoum_outcomes.png)

![per ring](laue_per_ring_darwin.png)

Deep dive files:

- `implementation_manual.md`
- `code_commentary.md`
- `code_function_map.csv`
- `laue_multiring_scene.wrl`
- `laue_wrl_quicklook.png`

## Key run summary

Source: `runs/geant4_laue_multiring_darwin/summary.json`

{table([
    ("primaries", barhoum["n_primaries"]),
    ("rings", barhoum["n_rings"]),
    ("diffraction fraction", barhoum["diffraction_fraction"]),
    ("absorption fraction", barhoum["absorption_fraction"]),
    ("transmission fraction", barhoum["transmission_fraction"]),
    ("spot D90 cm", barhoum["spot_d90_cm"]),
    ("energy min keV", barhoum["energy_min_keV"]),
    ("energy max keV", barhoum["energy_max_keV"]),
    ("focal length mm", barhoum["focal_length_mm"]),
])}

## Review target

Check whether the ring geometry, energy band, table lookup, branch probabilities, and focal deflection are internally consistent before comparing with the Guan-style split in step 02.

## Non-claim

This step does not prove the original Barhoum codebase or a publication-grade Ge measured-crystal validation. It records the local Barhoum-style baseline we can actually rerun and compare.
""",
    )

    write_text(
        out / "02_laue_darwin_guan_process" / "laue_darwin_guan_process.md",
        f"""
# 02 Guan-style Darwin process split

This step records the local compiled C++ implementation inspired by the Guan/Reiazi architecture: separate a process object from the Darwin/Zachariasen model object, then register that process in the gamma process manager for this application.

![process schematic](guan_process_schematic.png)

![metrics](guan_vs_barhoum_metrics.png)

![per ring](guan_vs_barhoum_per_ring.png)

Deep dive files:

- `implementation_manual.md`
- `code_commentary.md`
- `code_function_map.csv`
- `laue_multiring_scene.wrl`
- `guan_wrl_quicklook.png`

## Key run summary

Source: `runs/geant4_laue_darwin_guan_process/summary.json`

{table([
    ("primaries", guan["n_primaries"]),
    ("rings", guan["n_rings"]),
    ("diffraction fraction", guan["diffraction_fraction"]),
    ("absorption fraction", guan["absorption_fraction"]),
    ("transmission fraction", guan["transmission_fraction"]),
    ("spot D90 cm", guan["spot_d90_cm"]),
    ("registered in Geant4 EM category", guan["registered_in_geant4_em_category"]),
    ("model/process split", guan["model_process_split"]),
])}

## Direct comparison to step 01

Source: `runs/geant4_laue_darwin_guan_process/barhoum_comparison_summary.json`

{table([
    ("delta diffraction fraction", comparison["delta_diffraction_fraction"]),
    ("delta absorption fraction", comparison["delta_absorption_fraction"]),
    ("delta transmission fraction", comparison["delta_transmission_fraction"]),
    ("delta spot D90 cm", comparison["delta_spot_d90_cm"]),
    ("max abs delta mean p_diff by ring", comparison["max_abs_delta_mean_p_diff_by_ring"]),
])}

## Interpretation

The important closure is not that we copied Guan/Reiazi source code. We did not have that source. The closure is that the local process/model split uses the same geometry as step 01, computes Darwin-Hamilton mosaic probabilities online during compiled Geant4 tracking, and still reproduces the table-driven baseline to Monte Carlo scale.

## Non-claim

This is not a Geant4 toolkit patch and not an EM-category upstream integration. If that becomes necessary, this step gives the physics-equivalent app-level baseline to compare against.
""",
    )

    best = closure["best_no_fudge_variant"]
    rough = closure["literature_roughness_1nm_no_si_variant"]
    write_text(
        out / "03_channel_wallbywall" / "channel_wallbywall.md",
        f"""
# 03 Channel wall-by-wall optics

This step records the current Channel route. Photons are propagated through the public W/Si bilayer channel geometry wall by wall; survival is determined by geometry, multilayer reflectivity, path absorption choice, and leakage/exit, not by fitting a calibration multiplier.

![wall outcomes](channel_wallbywall_outcomes.png)

![closure variants](channel_closure_variants.png)

Deep dive files:

- `implementation_manual.md`
- `code_commentary.md`
- `code_function_map.csv`
- `channel_wallbywall_scene.wrl`
- `channel_wrl_quicklook.png`

## Wall-by-wall run

Source: `runs/channel_wallbywall_rebuild/summary.json`

{table([
    ("primaries", channel["n_primaries"]),
    ("survived", channel["n_survived"]),
    ("absorbed", channel["n_absorbed"]),
    ("entry blocked", channel["n_entry_blocked"]),
    ("leaked", channel["n_leaked"]),
    ("transmissivity", channel["transmissivity"]),
    ("effective area cm2", channel["effective_area_cm2"]),
    ("spot D90 cm", channel["spot_d90_cm"]),
    ("mean bounces per survivor", channel["mean_bounces_per_survivor"]),
    ("max bounces guard", channel["max_bounces"]),
])}

## No-fudge closure against CAM511 headline

Source: `runs/channel_independent_closure/summary.json`

{table([
    ("CAM511 target transmissivity", closure["cam511_target"]["transmissivity"]),
    ("best no-fudge transmissivity", best["transmissivity"]),
    ("best no-fudge delta", best["delta_to_cam511_transmissivity"]),
    ("best no-fudge effective area cm2", best["effective_area_cm2"]),
    ("1 nm roughness no-Si transmissivity", rough["transmissivity"]),
    ("1 nm roughness no-Si delta", rough["delta_to_cam511_transmissivity"]),
    ("no-fudge reaches CAM511", closure["no_fudge_reaches_cam511"]),
])}

## Review target

Audit the physical meaning of three switches: roughness, whether to include Si path absorption, and public-geometry open fraction. The best no-fudge case is close to the CAM511 0.80 headline but does not exactly reach it, so the honest conclusion is "public information aligns closely, but the remaining accounting gap is not eliminated."

## Non-claim

This does not claim access to the original CAM511 IDL/IMD model, exact aperture engineering drawings, or final assembly tolerances.
""",
    )

    write_text(
        out / "04_detector_activation_bridge" / "detector_activation_bridge.md",
        f"""
# 04 Detector and activation bridge

This step separates two different bridges: science photons from optics into a detector smoke model, and radioactive inventory positions into a delayed decay source. The current files are useful workflow checks, not final detector or activation rates.

![handoff](detector_activation_handoff.png)

![smoke](detector_activation_smoke.png)

## Detector handoff

Source: `runs/geant4_detector_wallbywall_1k/summary.json`

{table([
    ("input photons", detector["n_input_photons"]),
    ("simulated", detector["n_simulated"]),
    ("events written", detector["n_events_written"]),
    ("hits", detector["n_hits"]),
    ("TES detected", detector["n_tes_detected"]),
    ("BGO veto", detector["n_bgo_veto"]),
    ("TES detection fraction", detector["tes_detection_fraction"]),
    ("BGO veto fraction", detector["bgo_veto_fraction"]),
])}

I/O contract source: `runs/io_contract_validation_channel_wallbywall_detector_1k/summary.json`

{table([
    ("contract ok", detector_contract["ok"]),
    ("tables checked", detector_contract["n_tables"]),
])}

## Activation scaffold

Source: `runs/activation/synthetic_al28_day15/source_build_summary.json` and `runs/activation/synthetic_al28_day15/focal_transport_no_neutrino/summary.json`

{table([
    ("activation status", activation["status"]),
    ("inventory rows", activation["n_inventory_rows"]),
    ("radioactive rows", activation["n_radioactive_rows"]),
    ("day 15 activity Bq", activation["total_activity_Bq_day"]),
    ("decay source rows", activation["n_decay_source_rows"]),
    ("focal simulated", focal_activation["n_simulated"]),
    ("focal crossings", focal_activation["n_crossings"]),
    ("skipped neutrino crossings", focal_activation["n_neutrino_crossings_skipped"]),
])}

## Review target

Keep detector I/O schema bugs separate from physics-performance claims. The current detector and activation steps show that the interfaces can run, while production confidence still requires a higher fidelity detector geometry and a higher statistics true-mass activation run.
""",
    )

    write_text(
        out / "05_review_checklist" / "review_checklist.md",
        f"""
# 05 Review checklist

![risk matrix](review_attention_matrix.png)

## Step-by-step bug review

| step | first things to check | current pass condition |
|---|---|---|
| 01 Laue baseline | ring radii, energy band, Darwin table rows, branch fractions | `summary.json` and `per_ring_summary.json` agree with the generated figures. |
| 02 Guan process | app-level process registration, process/model split, online Darwin-Hamilton backend | mean `p_diff` delta by ring is near zero without reading the 01 probability table; branch deltas remain Monte Carlo scale. |
| 03 Channel | wall-by-wall exit logic, roughness, Si path absorption, open fraction | no calibration multiplier is used; CAM511 gap is explicitly reported. |
| 04 Detector bridge | phase-space schema, detector event IDs, hit/event crosslinks | contract summary is `ok: true`; subset-run warning is understood. |
| 04 Activation bridge | true-position inventory, source rows, neutrino handling | synthetic source and focal transport run with documented scaffold limits. |

## Anti-hallucination checks

- Do not call the Guan-style result a Guan/Reiazi source-code port.
- Do not call the Channel result the original CAM511 IDL/IMD model.
- Do not turn the 0.7615 no-fudge Channel transmissivity into the CAM511 0.80 number by adding a hidden multiplier.
- Do not quote detector or activation smoke results as final sensitivity.

## Single next confidence raiser

The highest-value next check is a production-statistics run that uses the same stepwise record format: optics phase space, detector replay, prompt inventory, delayed source, and mixed timeline, all with linked summaries and figures.
""",
    )


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    out = args.out.resolve()

    barhoum = load_json(repo, "runs/geant4_laue_multiring_darwin/summary.json")
    barhoum_ring = load_json(repo, "runs/geant4_laue_multiring_darwin/per_ring_summary.json")
    guan = load_json(repo, "runs/geant4_laue_darwin_guan_process/summary.json")
    guan_ring = load_json(repo, "runs/geant4_laue_darwin_guan_process/per_ring_summary.json")
    comparison = load_json(repo, "runs/geant4_laue_darwin_guan_process/barhoum_comparison_summary.json")
    channel = load_json(repo, "runs/channel_wallbywall_rebuild/summary.json")
    closure = load_json(repo, "runs/channel_independent_closure/summary.json")
    detector = load_json(repo, "runs/geant4_detector_wallbywall_1k/summary.json")
    detector_contract = load_json(repo, "runs/io_contract_validation_channel_wallbywall_detector_1k/summary.json")
    activation = load_json(repo, "runs/activation/synthetic_al28_day15/source_build_summary.json")
    focal_activation = load_json(repo, "runs/activation/synthetic_al28_day15/focal_transport_no_neutrino/summary.json")

    draw_review_pipeline(out)
    draw_laue_outcomes(out, barhoum)
    draw_laue_per_ring(out, barhoum_ring)
    write_laue_review_wrl(
        repo,
        out,
        "01_laue_barhoum_baseline",
        "runs/geant4_laue_multiring_darwin",
        "Corrected Laue Barhoum-style review scene",
    )
    draw_laue_wrl_quicklook(
        repo,
        out,
        "01_laue_barhoum_baseline",
        "runs/geant4_laue_multiring_darwin",
        "Laue Barhoum-style WRL quicklook",
        "laue_wrl_quicklook.png",
    )
    draw_guan_schematic(out)
    draw_guan_metrics(out, barhoum, guan)
    draw_guan_per_ring(out, barhoum_ring, guan_ring)
    write_laue_review_wrl(
        repo,
        out,
        "02_laue_darwin_guan_process",
        "runs/geant4_laue_darwin_guan_process",
        "Corrected Guan-style Laue review scene",
    )
    draw_laue_wrl_quicklook(
        repo,
        out,
        "02_laue_darwin_guan_process",
        "runs/geant4_laue_darwin_guan_process",
        "Guan-style Laue WRL quicklook",
        "guan_wrl_quicklook.png",
    )
    draw_channel_outcomes(out, channel)
    draw_channel_closure(out, closure)
    draw_channel_wrl_quicklook(repo, out)
    write_channel_wrl_scene(repo, out)
    draw_handoff_schematic(out)
    draw_detector_bridge(out, detector, activation, focal_activation)
    draw_risk_matrix(out)
    write_deep_dive_docs(repo, out, barhoum, guan, comparison, channel, closure)
    write_markdown(out, barhoum, guan, comparison, channel, closure, detector, detector_contract, activation, focal_activation)

    manifest = {
        "status": "PASS",
        "generated_root": str(out),
        "source_summaries": [
            "runs/geant4_laue_multiring_darwin/summary.json",
            "runs/geant4_laue_darwin_guan_process/summary.json",
            "runs/geant4_laue_darwin_guan_process/barhoum_comparison_summary.json",
            "runs/channel_wallbywall_rebuild/summary.json",
            "runs/channel_independent_closure/summary.json",
            "runs/geant4_detector_wallbywall_1k/summary.json",
            "runs/io_contract_validation_channel_wallbywall_detector_1k/summary.json",
            "runs/activation/synthetic_al28_day15/source_build_summary.json",
            "runs/activation/synthetic_al28_day15/focal_transport_no_neutrino/summary.json",
        ],
    }
    write_text(out / "00_review_map" / "review_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
