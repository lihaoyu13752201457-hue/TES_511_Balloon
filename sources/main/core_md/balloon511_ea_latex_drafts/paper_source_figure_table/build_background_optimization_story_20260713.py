#!/usr/bin/env python3
"""Build the source-backed geometry, background, optimization, and mission figures.

The script deliberately reads only retained authority products.  It does not use
the internal geometry comparison tables in the manuscript figures.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent

MASS_REPORT = ROOT / (
    "outputs/reports/"
    "Mass_model_511_stage_diam_300_300_300_350_350_400_20260701"
)
MASS_STEM = MASS_REPORT / (
    "DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_"
    "freecad_review_colored_mm"
)
MASS_OBJ = MASS_STEM.with_suffix(".obj")
MASS_MTL = MASS_STEM.with_suffix(".mtl")

REFERENCE_BREAKDOWN = ROOT / (
    "engineering/ea_detector_response_closure_20260713/data/"
    "reference_response_background_breakdown.json"
)
FINAL_ROOT = ROOT / (
    "engineering/geometry_optimization_20260704/"
    "43_geoopt_s3d_o8_fallback_20260712"
)
FINAL_MANIFEST = FINAL_ROOT / "data/s3d_o8_geometry_manifest.json"
ACTIVATION_ROOT = ROOT / (
    "engineering/geometry_optimization_20260704/"
    "44_s3d_o8_all8_activation_20260713"
)
ACTIVATION_CAMPAIGN = ACTIVATION_ROOT / (
    "data/s3d_o8_all8_activation_campaign.json"
)
DELAYED_COMPONENTS = ACTIVATION_ROOT / (
    "data/s3d_o8_all8_delayed_components.json"
)
STEP05_SUMMARY = ACTIVATION_ROOT / (
    "fullchain/step05/step05_s3d_o8_all8_activation_l1_response_summary.json"
)
ENERGY_RESPONSE_ROOT = ROOT / (
    "engineering/ea_s3d_o8_all8_detector_response_closure_20260713"
)
ENERGY_RESPONSE_SUMMARY = ENERGY_RESPONSE_ROOT / (
    "data/s3d_o8_all8_energy_response_summary.json"
)
ENERGY_RESPONSE_VALIDATION = ENERGY_RESPONSE_ROOT / (
    "data/s3d_o8_all8_energy_response_validation.json"
)
FAMILY_NUCLIDE_MISSION_ROOT = ROOT / (
    "engineering/ea_s3d_o8_all8_family_nuclide_mission_fold_20260713"
)
FAMILY_NUCLIDE_MISSION_SUMMARY = FAMILY_NUCLIDE_MISSION_ROOT / (
    "data/s3d_o8_all8_family_nuclide_mission_summary.json"
)
FAMILY_NUCLIDE_MISSION_VALIDATION = FAMILY_NUCLIDE_MISSION_ROOT / (
    "data/s3d_o8_all8_family_nuclide_mission_validation.json"
)
FAMILY_NUCLIDE_MISSION_TIMELINE = FAMILY_NUCLIDE_MISSION_ROOT / (
    "outputs/w2_all8_family_nuclide_mission_timeline.csv"
)
SLANT45_MISSION_ROOT = ROOT / (
    "engineering/ea_peer_review_p02_slant_transmission_20260714"
)
SLANT45_MISSION_SUMMARY = SLANT45_MISSION_ROOT / (
    "data/slant45_signal_refold_summary.json"
)
SLANT45_MISSION_VALIDATION = SLANT45_MISSION_ROOT / (
    "data/slant45_signal_refold_validation.json"
)
SLANT45_MISSION_TIMELINE = SLANT45_MISSION_ROOT / (
    "outputs/w2_all8_family_nuclide_mission_timeline_slant45.csv"
)

WINDOW_KEY = "w2_510p58_511p42"
BLUE = "#2474B5"
DEEP_BLUE = "#174A73"
ORANGE = "#E6862A"
GREEN = "#2A9D6F"
PURPLE = "#7A5AA6"
RED = "#C4473A"
GREY = "#7B8794"
LIGHT_GREY = "#E9EEF2"
INK = "#23313D"


mpl.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9.0,
        "axes.titlesize": 10.2,
        "axes.labelsize": 9.2,
        "xtick.labelsize": 8.2,
        "ytick.labelsize": 8.2,
        "legend.fontsize": 8.0,
        "axes.edgecolor": "#697783",
        "axes.linewidth": 0.7,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
    }
)


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_close(actual: float, expected: float, label: str, rtol=1e-8) -> None:
    if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=1e-12):
        raise RuntimeError(f"{label}: {actual!r} != {expected!r}")


def panel_label(ax, label: str) -> None:
    ax.text(
        0.0,
        1.02,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=10.5,
        fontweight="bold",
    )


def style_cartesian(ax, *, xgrid=True, ygrid=False) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    if xgrid:
        ax.grid(axis="x", color="#D8E0E6", linewidth=0.65, zorder=0)
    if ygrid:
        ax.grid(axis="y", color="#E2E8ED", linewidth=0.55, zorder=0)
    ax.set_axisbelow(True)


def save(fig, name: str, *, dpi=300, svg=True) -> None:
    fig.savefig(OUT / f"{name}.png", dpi=dpi, bbox_inches="tight", pad_inches=0.05)
    if svg:
        fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def parse_mtl(path: Path) -> dict[str, dict[str, object]]:
    materials: dict[str, dict[str, object]] = {}
    current = None
    description = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            description = line[1:].strip()
            continue
        fields = line.split()
        if fields[0] == "newmtl":
            current = fields[1]
            materials[current] = {
                "rgb": (0.65, 0.65, 0.65),
                "alpha": 1.0,
                "description": description,
            }
            description = ""
        elif current and fields[0] == "Kd":
            materials[current]["rgb"] = tuple(float(v) for v in fields[1:4])
        elif current and fields[0] == "d":
            materials[current]["alpha"] = float(fields[1])
    return materials


def parse_obj(path: Path):
    vertices: list[tuple[float, float, float]] = []
    triangles: list[tuple[int, int, int]] = []
    triangle_materials: list[str] = []
    current_material = "service"
    with path.open("r", encoding="utf-8", errors="strict") as handle:
        for raw in handle:
            if raw.startswith("v "):
                _, x, y, z = raw.split()[:4]
                vertices.append((float(x), float(y), float(z)))
            elif raw.startswith("usemtl "):
                current_material = raw.split()[1]
            elif raw.startswith("f "):
                indices = [int(token.split("/")[0]) - 1 for token in raw.split()[1:]]
                for j in range(1, len(indices) - 1):
                    triangles.append((indices[0], indices[j], indices[j + 1]))
                    triangle_materials.append(current_material)
    return (
        np.asarray(vertices, dtype=np.float32),
        np.asarray(triangles, dtype=np.int32),
        np.asarray(triangle_materials, dtype=object),
    )


def camera_basis(azimuth_deg: float, elevation_deg: float):
    az = np.deg2rad(azimuth_deg)
    el = np.deg2rad(elevation_deg)
    toward_camera = np.array(
        [np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)]
    )
    right = np.array([-np.sin(az), np.cos(az), 0.0])
    # right x up = view direction gives a right-handed screen basis.  The old
    # cross-product order inverted the vertical screen axis and made the
    # 45-degree sky-facing aperture appear to point downward.
    up = np.cross(toward_camera, right)
    up /= np.linalg.norm(up)
    return right, up, toward_camera


def material_vertices(vertices, faces, face_materials, material: str):
    selected = faces[face_materials == material]
    return vertices[np.unique(selected)]


def project_points(points, basis):
    right, up, depth = basis
    return np.column_stack((points @ right, points @ up, points @ depth))


ALPHA_OVERRIDE = {
    "dr_vacuum_jacket": 0.045,
    "external_outer_shell": 0.055,
    "external_active_shield": 0.10,
    "external_csi": 0.14,
    "dr_60K_shield": 0.075,
    "dr_4K_shield": 0.10,
    "dr_still_shield": 0.13,
    "dr_50mK_can": 0.18,
    "magnetic_shield": 0.30,
    "nearfield_outer_support": 0.16,
    "windows": 0.36,
    "plate_300K": 0.32,
}

COLOR_OVERRIDE = {
    # The source MTL intentionally uses a vivid review colour for this support.
    # A muted paper colour prevents it from hiding the detector internals.
    "nearfield_outer_support": (0.34, 0.50, 0.56),
}


def render_mesh_panel(
    ax,
    vertices,
    faces,
    face_materials,
    materials,
    *,
    included: set[str] | None,
    excluded: set[str] | None,
    azimuth: float,
    elevation: float,
    crop_materials: set[str] | None = None,
    scale_bar_mm: float = 100.0,
):
    available = set(face_materials.tolist())
    selected_materials = available if included is None else available & included
    if excluded:
        selected_materials -= excluded
    mask = np.isin(face_materials, sorted(selected_materials))
    selected_faces = faces[mask]
    selected_names = face_materials[mask]
    triangles = vertices[selected_faces].astype(np.float64)

    basis = camera_basis(azimuth, elevation)
    right, up, depth_axis = basis
    projected = np.empty_like(triangles)
    projected[:, :, 0] = triangles @ right
    projected[:, :, 1] = triangles @ up
    projected[:, :, 2] = triangles @ depth_axis

    normals = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    norm = np.linalg.norm(normals, axis=1)
    normals[norm > 0] /= norm[norm > 0, None]
    light = np.array([0.25, -0.35, 0.90])
    light /= np.linalg.norm(light)
    intensity = 0.68 + 0.32 * np.abs(normals @ light)

    rgba = np.zeros((len(selected_faces), 4), dtype=float)
    for material in selected_materials:
        item = selected_names == material
        rgb = np.asarray(
            COLOR_OVERRIDE.get(material, materials[material]["rgb"]), dtype=float
        )
        rgba[item, :3] = np.clip(rgb[None, :] * intensity[item, None], 0.0, 1.0)
        rgba[item, 3] = ALPHA_OVERRIDE.get(
            material, min(float(materials[material]["alpha"]), 0.88)
        )

    order = np.argsort(projected[:, :, 2].mean(axis=1))
    collection = PolyCollection(
        projected[order, :, :2],
        facecolors=rgba[order],
        edgecolors="none",
        linewidths=0.0,
        rasterized=True,
    )
    ax.add_collection(collection)

    if crop_materials:
        crop_mask = np.isin(face_materials, sorted(crop_materials))
        crop_points = vertices[np.unique(faces[crop_mask])]
    else:
        crop_points = vertices[np.unique(selected_faces)]
    crop = project_points(crop_points.astype(float), basis)[:, :2]
    xmin, ymin = crop.min(axis=0)
    xmax, ymax = crop.max(axis=0)
    pad = 0.05 * max(xmax - xmin, ymax - ymin)
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")

    bar_x0 = xmin + 0.04 * (xmax - xmin)
    bar_y = ymin + 0.045 * (ymax - ymin)
    ax.plot(
        [bar_x0, bar_x0 + scale_bar_mm],
        [bar_y, bar_y],
        color=INK,
        lw=2.1,
        solid_capstyle="butt",
        zorder=20,
    )
    ax.text(
        bar_x0 + scale_bar_mm / 2,
        bar_y + 0.018 * (ymax - ymin),
        f"{int(scale_bar_mm)} mm",
        ha="center",
        va="bottom",
        fontsize=7.8,
        zorder=20,
    )
    return basis


def material_centroid(vertices, faces, face_materials, material: str):
    points = material_vertices(vertices, faces, face_materials, material)
    return np.median(points.astype(float), axis=0)


def build_mass_model_figure(provenance: dict) -> dict:
    materials = parse_mtl(MASS_MTL)
    vertices, faces, face_materials = parse_obj(MASS_OBJ)
    fig, axes = plt.subplots(1, 2, figsize=(7.28, 4.25), gridspec_kw={"wspace": 0.015})

    full_excluded: set[str] = set()
    basis_full = render_mesh_panel(
        axes[0],
        vertices,
        faces,
        face_materials,
        materials,
        included=None,
        excluded=full_excluded,
        azimuth=-132,
        elevation=18,
        scale_bar_mm=200,
    )
    panel_label(axes[0], "a  Generated detector–cryostat model")

    detail_excluded = {
        "external_active_shield",
        "external_csi",
        "external_outer_shell",
        "dr_vacuum_jacket",
        "service",
        "xs400_group1",
        "xs400_group2",
        "xs400_group3",
        "xs400_group4",
        "plate_300K",
        "nearfield_outer_support",
    }
    crop_materials = {
        "tes_ta",
        "tes_silicon",
        "tes_copper_link",
        "magnetic_shield",
        "w_collimator",
        "windows",
        "dr_50mK_can",
        "cold_plate_50mK",
        "cold_plate_100mK",
    }
    basis_detail = render_mesh_panel(
        axes[1],
        vertices,
        faces,
        face_materials,
        materials,
        included=None,
        excluded=detail_excluded,
        azimuth=-132,
        elevation=18,
        crop_materials=crop_materials,
        scale_bar_mm=50,
    )
    panel_label(axes[1], "b  Detector bay (outer envelopes removed)")

    tes = material_centroid(vertices, faces, face_materials, "tes_ta")
    collimator = material_centroid(vertices, faces, face_materials, "w_collimator")
    window = material_centroid(vertices, faces, face_materials, "windows")
    copper = material_centroid(vertices, faces, face_materials, "tes_copper_link")
    projected = {
        "TES array": project_points(tes[None, :], basis_detail)[0, :2],
        "W collimator": project_points(collimator[None, :], basis_detail)[0, :2],
        "side windows": project_points(window[None, :], basis_detail)[0, :2],
        "Cu thermal link": project_points(copper[None, :], basis_detail)[0, :2],
    }
    offsets = {
        "TES array": (36, 20),
        "side windows": (16, 28),
        "Cu thermal link": (42, -30),
    }
    for label, xy in projected.items():
        if label == "W collimator":
            continue
        axes[1].annotate(
            label,
            xy=xy,
            xytext=offsets[label],
            textcoords="offset points",
            ha="center",
            fontsize=7.4,
            arrowprops={"arrowstyle": "-", "color": "#52616D", "lw": 0.7},
            bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.86},
            zorder=30,
        )

    p_tes = projected["TES array"]
    p_col = projected["W collimator"]
    p_start = p_col + 0.12 * (p_col - p_tes)
    axes[1].annotate(
        "",
        xy=p_tes,
        xytext=p_start,
        arrowprops={"arrowstyle": "-|>", "color": RED, "lw": 1.55},
        zorder=35,
    )
    axes[1].annotate(
        "sky\n45° elevation",
        xy=p_start,
        xytext=(-20, -42),
        textcoords="offset points",
        ha="center",
        va="top",
        color=DEEP_BLUE,
        fontsize=7.4,
        arrowprops={"arrowstyle": "-", "color": DEEP_BLUE, "lw": 0.8},
        bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.86},
        zorder=36,
    )
    p_label = 0.52 * p_start + 0.48 * p_tes
    axes[1].text(
        *(p_label + np.array([0.0, -10.0])),
        "focused 511 keV photons",
        color=RED,
        fontsize=7.4,
        ha="center",
        va="top",
        zorder=35,
    )

    legend = [
        Patch(facecolor="#39B55A", alpha=0.45, label="active scintillator"),
        Patch(facecolor="#577F8F", alpha=0.28, label="outer support frame"),
        Patch(facecolor="#B8D1E8", alpha=0.55, label="cryostat envelopes"),
        Patch(facecolor="#E97B36", label="cold Cu structures"),
        Patch(facecolor="#B52F2F", label="TES Ta absorbers"),
        Patch(facecolor="#252525", label="W collimator"),
    ]
    fig.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.01),
        ncol=6,
        frameon=False,
        columnspacing=0.8,
        handlelength=1.15,
    )
    fig.subplots_adjust(bottom=0.11, top=0.92, left=0.01, right=0.99)
    save(fig, "fig_reference_detector_cryostat_geometry", dpi=330, svg=False)

    stats = {
        "vertices": int(len(vertices)),
        "triangles": int(len(faces)),
        "semantic_materials": sorted(set(face_materials.tolist())),
        "bbox_mm": {
            "min": vertices.min(axis=0).astype(float).tolist(),
            "max": vertices.max(axis=0).astype(float).tolist(),
        },
    }
    provenance["fig_reference_detector_cryostat_geometry"] = stats
    return stats


def build_background_origin_figure(reference: dict, provenance: dict) -> None:
    prompt = reference["prompt_particles"]
    delayed_total = reference["reference_baseline"]["delayed"]
    components = [
        (r"Prompt $e^+$", prompt[0]["events"], prompt[0]["rate_cps"], prompt[0]["mc_sigma_cps"], BLUE),
        ("Prompt neutrons", prompt[1]["events"], prompt[1]["rate_cps"], prompt[1]["mc_sigma_cps"], ORANGE),
        (r"Prompt $\mu^+$", prompt[2]["events"], prompt[2]["rate_cps"], prompt[2]["mc_sigma_cps"], GREY),
        ("Delayed activation", delayed_total["events"], delayed_total["rate_cps"], delayed_total["mc_sigma_cps"], PURPLE),
    ]
    total_rate = reference["reference_baseline"]["total"]["rate_cps"]
    core_fraction_total = (components[0][2] + components[1][2]) / total_rate
    core_fraction_prompt = (components[0][2] + components[1][2]) / reference["reference_baseline"]["prompt"]["rate_cps"]
    require_close(core_fraction_total, 0.8912, "reference e+ plus n total fraction", rtol=8e-5)

    fig, axes = plt.subplots(1, 2, figsize=(7.28, 3.45), gridspec_kw={"width_ratios": [1.22, 0.78], "wspace": 0.38})
    ax = axes[0]
    labels = [c[0] for c in components][::-1]
    rates = np.asarray([c[2] for c in components][::-1])
    errors = np.asarray([c[3] for c in components][::-1])
    colors = [c[4] for c in components][::-1]
    records = [c[1] for c in components][::-1]
    y = np.arange(len(labels))
    ax.barh(y, rates, xerr=errors, color=colors, height=0.62, capsize=2.5, zorder=3)
    ax.set_yticks(y, labels)
    ax.set_xlabel(r"Selected rate (s$^{-1}$)")
    ax.set_xlim(0, max(rates + errors) * 1.34)
    for yi, rate, error, count in zip(y, rates, errors, records):
        ax.text(rate + error + 0.0005, yi, rf"{rate:.3g}  ($N={count}$)", va="center", fontsize=7.8)
    style_cartesian(ax)
    panel_label(ax, "a  Which components reach 511 keV?")

    ax = axes[1]
    nuclides = reference["delayed_selected_nuclides"]
    labels = [r["nuclide"] for r in nuclides][::-1]
    counts = np.asarray([r["events"] for r in nuclides][::-1], dtype=float)
    color_by_nuclide = {"Cu-64": PURPLE, "Cu-61": "#9B7DBB", "Cu-62": "#BCA8D2"}
    colors = [color_by_nuclide[label] for label in labels]
    y = np.arange(len(labels))
    ax.barh(y, counts, color=colors, height=0.62, zorder=3)
    ax.set_yticks(y, labels)
    ax.set_xlabel("Selected delayed records")
    delayed_records = int(delayed_total["events"])
    ax.set_xlim(0, max(3, delayed_records))
    for yi, count in zip(y, counts):
        ax.text(count + 0.6, yi, f"{int(count)}", va="center", fontweight="bold", fontsize=8.2)
    ax.text(
        0.02,
        0.97,
        f"All {delayed_records} records originate\nin cold Cu structures",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.0,
        bbox={"boxstyle": "round,pad=0.3", "fc": "#F7F4FA", "ec": "#DED3E8"},
    )
    style_cartesian(ax)
    panel_label(ax, "b  Which activation products survive?")

    fig.subplots_adjust(left=0.13, right=0.985, top=0.89, bottom=0.18)
    save(fig, "fig_background_origin_story")
    provenance["fig_background_origin_story"] = {
        "selected_total_rate_cps": total_rate,
        "eplus_plus_neutron_fraction_total": core_fraction_total,
        "eplus_plus_neutron_fraction_prompt": core_fraction_prompt,
        "components": [
            {"label": c[0], "events": c[1], "rate_cps": c[2], "mc_sigma_cps": c[3]}
            for c in components
        ],
        "delayed_nuclides": nuclides,
    }


def draw_final_shield(ax, manifest: dict) -> None:
    side = manifest["retained_bgo_volumes"][0]
    bottom = next(v for v in manifest["new_bgo_volumes"] if "Bottom" in v["name"])
    top = next(v for v in manifest["new_bgo_volumes"] if "Top" in v["name"])
    r_in, r_out = side["r_inner_cm"], side["r_outer_cm"]
    z0, z1 = side["z_min_cm"], side["z_max_cm"]
    bgo_fc = "#2A9D6F"
    bgo_ec = "#176A4C"

    ax.add_patch(Rectangle((-r_in, z0), 2 * r_in, z1 - z0, fc="#F2F5F7", ec="#BCC8D0", lw=0.8, zorder=1))
    for x in (-r_out, r_in):
        ax.add_patch(Rectangle((x, z0), r_out - r_in, z1 - z0, fc=bgo_fc, ec=bgo_ec, lw=0.8, zorder=3))
    ax.add_patch(Rectangle((-bottom["r_outer_cm"], bottom["z_min_cm"]), 2 * bottom["r_outer_cm"], bottom["z_max_cm"] - bottom["z_min_cm"], fc=bgo_fc, ec=bgo_ec, lw=0.8, zorder=3))
    for x in (-top["r_outer_cm"], top["r_inner_cm"]):
        ax.add_patch(Rectangle((x, top["z_min_cm"]), top["r_outer_cm"] - top["r_inner_cm"], top["z_max_cm"] - top["z_min_cm"], fc=bgo_fc, ec=bgo_ec, lw=0.8, zorder=3))

    # The retained side aperture is centred at local z=-5.2 cm and is 3.796 cm high.
    aperture_z0 = -5.2 - 1.898
    aperture_h = 2 * 1.898
    ax.add_patch(Rectangle((-r_out - 0.2, aperture_z0), r_out - r_in + 0.4, aperture_h, fc="white", ec=RED, lw=1.1, zorder=5))
    ax.annotate("", xy=(-4, -5.2), xytext=(-37, -5.2), arrowprops={"arrowstyle": "-|>", "color": RED, "lw": 1.45}, zorder=7)
    ax.text(-37, -1.8, "focused\n511 keV photons", ha="left", va="bottom", color=RED, fontsize=7.5)

    # A simplified central cryostat/TES symbol keeps the diagram readable.
    ax.add_patch(Rectangle((-11.5, -16.5), 23, 49, fc="#DCE7EF", ec="#8096A5", lw=0.8, zorder=2))
    ax.add_patch(Rectangle((-3.0, -7.2), 6.0, 4.0, fc="#C4473A", ec="#7E2C25", lw=0.7, zorder=6))
    ax.text(0, -9.2, "TES", ha="center", va="top", fontsize=7.5, color="#7E2C25")

    ax.annotate("40 mm side BGO", xy=(23.2, 12), xytext=(29, 22), ha="left", fontsize=7.6, arrowprops={"arrowstyle": "-", "color": bgo_ec, "lw": 0.8})
    ax.annotate("30 mm bottom BGO", xy=(0, -20.9), xytext=(8, -31), ha="left", fontsize=7.6, arrowprops={"arrowstyle": "-", "color": bgo_ec, "lw": 0.8})
    ax.annotate("10 mm top\nannulus", xy=(23.1, 41.4), xytext=(11, 35.5), ha="center", va="top", fontsize=7.6, arrowprops={"arrowstyle": "-", "color": bgo_ec, "lw": 0.8})
    ax.text(0.02, 0.98, "3 mm Al + Kapton outer shell\nNo external W layer", transform=ax.transAxes, ha="left", va="top", fontsize=7.7, bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#CCD6DD"})
    ax.set_xlim(-39, 44)
    ax.set_ylim(-34, 51)
    ax.set_aspect("equal")
    ax.set_xlabel("Local radial coordinate (cm)")
    ax.set_ylabel("Local axial coordinate (cm)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(color="#E3E9ED", lw=0.55, zorder=0)


def build_final_design_figure(manifest: dict, final05: dict, provenance: dict) -> None:
    w2 = final05["windows"][WINDOW_KEY]
    streams = w2["by_stream"]
    final_components = {
        "Prompt": streams["prompt"]["side_compton_fov_pass_rate_cps"],
        "Atmospheric 511 keV": streams["atm511_sidecar"]["side_compton_fov_pass_rate_cps"],
        "Delayed activation": streams["delayed"]["side_compton_fov_pass_rate_cps"],
    }
    total = sum(final_components.values())
    require_close(total, w2["physical_reference_flux"]["background_cps"], "final selected background")

    fig = plt.figure(figsize=(7.28, 5.15))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.10, 1.10], height_ratios=[1.08, 0.92], wspace=0.43, hspace=0.48)
    ax_geo = fig.add_subplot(grid[:, 0])
    ax_flow = fig.add_subplot(grid[0, 1])
    ax_budget = fig.add_subplot(grid[1, 1])

    draw_final_shield(ax_geo, manifest)
    panel_label(ax_geo, "a  Final directionally graded shield")

    stages = ["Energy window", "+ active veto", "+ topology / FoV"]
    x = np.arange(3)
    flow = {
        "Prompt": [
            streams["prompt"]["raw_rate_cps"],
            streams["prompt"]["active_veto_pass_rate_cps"],
            streams["prompt"]["side_compton_fov_pass_rate_cps"],
        ],
        "Delayed": [
            streams["delayed"]["raw_rate_cps"],
            streams["delayed"]["active_veto_pass_rate_cps"],
            streams["delayed"]["side_compton_fov_pass_rate_cps"],
        ],
        "Atmospheric 511 keV": [
            streams["atm511_sidecar"]["raw_rate_cps"],
            streams["atm511_sidecar"]["active_veto_pass_rate_cps"],
            streams["atm511_sidecar"]["side_compton_fov_pass_rate_cps"],
        ],
    }
    colors = {"Prompt": BLUE, "Delayed": PURPLE, "Atmospheric 511 keV": ORANGE}
    markers = {"Prompt": "o", "Delayed": "s", "Atmospheric 511 keV": "^"}
    for label, values in flow.items():
        ax_flow.plot(x, values, color=colors[label], marker=markers[label], ms=4.5, lw=1.6, label=label, zorder=3)
        ax_flow.text(x[-1] + 0.06, values[-1], f"{values[-1]:.2g}", color=colors[label], va="center", fontsize=7.5)
    ax_flow.set_yscale("log")
    ax_flow.set_xticks(x, stages)
    ax_flow.set_ylabel(r"Rate (s$^{-1}$)")
    ax_flow.set_xlim(-0.08, 2.48)
    ax_flow.set_ylim(6e-4, 5e-2)
    ax_flow.legend(frameon=False, ncol=1, loc="upper right")
    style_cartesian(ax_flow, xgrid=False, ygrid=True)
    panel_label(ax_flow, "b  What each selection removes")

    labels = ["Prompt", "Atmospheric line", "Delayed activation"]
    rates = np.asarray(list(final_components.values()))
    shares = rates / total
    y = np.arange(len(labels))[::-1]
    colors_list = [BLUE, ORANGE, PURPLE]
    ax_budget.barh(y, rates, color=colors_list, height=0.58, zorder=3)
    ax_budget.set_yticks(y, labels)
    ax_budget.set_xlabel(r"Final selected rate (s$^{-1}$)")
    ax_budget.set_xlim(0, max(rates) * 1.55)
    for yi, rate, share in zip(y, rates, shares):
        ax_budget.text(rate + max(rates) * 0.035, yi, f"{rate:.3g}  ({100*share:.1f}%)", va="center", fontsize=7.6)
    ax_budget.text(
        0.98,
        0.04,
        rf"Total = {total:.4g} s$^{{-1}}$",
        transform=ax_budget.transAxes,
        ha="right",
        va="bottom",
        fontsize=8.3,
        fontweight="bold",
    )
    style_cartesian(ax_budget)
    panel_label(ax_budget, "c  What remains after all selections")

    fig.subplots_adjust(left=0.08, right=0.985, top=0.94, bottom=0.11)
    save(fig, "fig_optimized_shield_background")
    provenance["fig_optimized_shield_background"] = {
        "geometry_variant_internal": manifest["variant"],
        "public_description": "directionally graded BGO shield",
        "final_components_cps": final_components,
        "final_total_background_cps": total,
        "cutflow_cps": flow,
    }


def build_mission_figure(
    mission_summary: dict, mission_validation: dict, provenance: dict
) -> None:
    with SLANT45_MISSION_TIMELINE.open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    expected_bins = int(
        mission_validation.get("mission_bins", mission_validation.get("bins", -1))
    )
    if len(rows) != expected_bins:
        raise RuntimeError(
            f"Expected {expected_bins} validated all-eight-family time bins, "
            f"found {len(rows)}"
        )
    days = np.asarray([float(r["elapsed_stop_day"]) for r in rows])
    central = np.asarray([float(r["counting_Z"]) for r in rows])
    conditional = np.asarray(
        [
            float(
                r[
                    "counting_Z_componentwise_transport_counting_endpoint_conditional"
                ]
            )
            for r in rows
        ]
    )
    require_close(central[-1], float(mission_summary["Z20d"]), "final central Z")
    require_close(
        conditional[-1],
        float(
            mission_summary[
                "Z20d_componentwise_transport_counting_endpoint_conditional"
            ]
        ),
        "final conditional componentwise transport-counting endpoint Z",
    )
    require_close(
        float(rows[-1]["cumulative_source_counts"]),
        float(mission_summary["source_counts_20d"]),
        "final central source counts",
    )
    require_close(
        float(rows[-1]["cumulative_background_counts"]),
        float(mission_summary["background_counts_20d"]),
        "final central background counts",
    )
    require_close(
        float(
            rows[-1]["cumulative_source_transport_counting_lower_endpoint_counts"]
        ),
        float(mission_summary["source_transport_counting_lower_endpoint_counts_20d"]),
        "final conditional source lower-endpoint counts",
    )
    require_close(
        float(
            rows[-1][
                "cumulative_background_componentwise_transport_counting_upper_endpoint_counts"
            ]
        ),
        float(
            mission_summary[
                "background_componentwise_transport_counting_upper_endpoint_counts_20d"
            ]
        ),
        "final conditional background upper-endpoint counts",
    )

    t3 = float(mission_summary["T3_day"])
    t5 = float(mission_summary["T5_day"])
    t3c = float(
        mission_summary[
            "T3_day_componentwise_transport_counting_endpoint_conditional"
        ]
    )
    t5c = float(
        mission_summary[
            "T5_day_componentwise_transport_counting_endpoint_conditional"
        ]
    )
    final_day = float(days[-1])
    reference_flux = float(mission_summary["reference_flux_ph_cm2_s"])
    reference_flux_exponent = int(math.floor(math.log10(reference_flux)))
    reference_flux_mantissa = reference_flux / (10.0**reference_flux_exponent)
    if math.isclose(reference_flux_mantissa, 1.0, rel_tol=1e-12):
        reference_flux_math = rf"10^{{{reference_flux_exponent}}}"
    else:
        reference_flux_math = (
            rf"{reference_flux_mantissa:g}\times 10^{{{reference_flux_exponent}}}"
        )

    fig, ax = plt.subplots(figsize=(7.28, 3.85))
    ax.plot(
        days,
        central,
        color=BLUE,
        lw=2.15,
        label="Central all-eight-family estimate",
        zorder=4,
    )
    ax.plot(
        days,
        conditional,
        color=PURPLE,
        lw=2.0,
        ls="--",
        label="Conditional componentwise transport-counting endpoint",
        zorder=4,
    )
    ax.axhline(3, color="#8A959D", lw=0.9, ls=":", zorder=1)
    ax.axhline(5, color="#65727B", lw=0.9, ls=":", zorder=1)
    threshold_x = final_day * 1.0175
    ax.text(threshold_x, 3, r"$3\sigma$", va="center", fontsize=8.0, color="#65727B")
    ax.text(threshold_x, 5, r"$5\sigma$", va="center", fontsize=8.0, color="#52606A")

    ax.scatter([t5, t5c], [5, 5], c=[BLUE, PURPLE], s=24, zorder=6, edgecolor="white", linewidth=0.6)
    ax.annotate(f"{t5:.2f} d", xy=(t5, 5), xytext=(t5 + 1.1, 7.1), color=BLUE, fontsize=8.0, arrowprops={"arrowstyle": "-", "color": BLUE, "lw": 0.8})
    ax.annotate(f"{t5c:.2f} d", xy=(t5c, 5), xytext=(t5c + 0.8, 2.2), color=PURPLE, fontsize=8.0, arrowprops={"arrowstyle": "-", "color": PURPLE, "lw": 0.8})
    ax.scatter([final_day, final_day], [central[-1], conditional[-1]], c=[BLUE, PURPLE], s=26, zorder=6)
    endpoint_label_x = final_day * 0.9775
    ax.text(endpoint_label_x, central[-1] + 0.55, f"{final_day:g} d: {central[-1]:.2f}", color=BLUE, ha="right", va="bottom", fontsize=8.4, fontweight="bold")
    ax.text(endpoint_label_x, conditional[-1] + 0.45, f"{final_day:g} d: {conditional[-1]:.2f}", color=PURPLE, ha="right", va="bottom", fontsize=8.4, fontweight="bold")

    ax.set_xlim(0, final_day * 1.0625)
    ax.set_ylim(0, max(5.0, float(central.max()), float(conditional.max())) * 1.13)
    ax.set_xlabel("Elapsed flight time (days)")
    ax.set_ylabel(r"Cumulative counting significance, $S/\sqrt{B}$")
    ax.legend(loc="upper left", frameon=False)
    style_cartesian(ax, xgrid=True, ygrid=True)
    panel_label(
        ax,
        rf"Reference source flux: ${reference_flux_math}$ ph cm$^{{-2}}$ s$^{{-1}}$",
    )
    fig.text(
        0.105,
        0.025,
        "Conditional endpoint: componentwise transported-count upper endpoints and "
        "signal lower bound; not a full 95% coverage interval.",
        ha="left",
        va="bottom",
        fontsize=7.3,
        color="#5E6972",
    )
    fig.subplots_adjust(left=0.105, right=0.94, top=0.89, bottom=0.20)
    save(fig, "fig_optimized_mission_significance")
    provenance["fig_optimized_mission_significance"] = {
        "analysis_scope": "S3d-O8 all-eight-family W2 mission fold",
        "window_key": WINDOW_KEY,
        "reference_flux_ph_cm2_s": reference_flux,
        "bins": len(rows),
        "elapsed_stop_day": final_day,
        "Z_final_central": float(central[-1]),
        "Z20_central": float(central[-1]),
        "Z_final_componentwise_transport_counting_endpoint_conditional": float(
            conditional[-1]
        ),
        "Z20_componentwise_transport_counting_endpoint_conditional": float(
            conditional[-1]
        ),
        "T3_day_central": t3,
        "T5_day_central": t5,
        "T3_day_componentwise_transport_counting_endpoint_conditional": t3c,
        "T5_day_componentwise_transport_counting_endpoint_conditional": t5c,
        "source_counts_final": float(rows[-1]["cumulative_source_counts"]),
        "source_counts_20d": float(rows[-1]["cumulative_source_counts"]),
        "background_counts_final": float(
            rows[-1]["cumulative_background_counts"]
        ),
        "background_counts_20d": float(
            rows[-1]["cumulative_background_counts"]
        ),
        "source_transport_counting_lower_endpoint_counts_final": float(
            rows[-1]["cumulative_source_transport_counting_lower_endpoint_counts"]
        ),
        "background_componentwise_transport_counting_upper_endpoint_counts_final": float(
            rows[-1][
                "cumulative_background_componentwise_transport_counting_upper_endpoint_counts"
            ]
        ),
        "conditional_endpoint_scope": mission_summary["model"][
            "conditional_componentwise_transport_counting_endpoint"
        ],
        "timeline_columns": {
            "central": "counting_Z",
            "conditional_endpoint": "counting_Z_componentwise_transport_counting_endpoint_conditional",
        },
    }


def main() -> None:
    required = [
        MASS_OBJ,
        MASS_MTL,
        REFERENCE_BREAKDOWN,
        FINAL_MANIFEST,
        ACTIVATION_CAMPAIGN,
        DELAYED_COMPONENTS,
        STEP05_SUMMARY,
        ENERGY_RESPONSE_SUMMARY,
        ENERGY_RESPONSE_VALIDATION,
        FAMILY_NUCLIDE_MISSION_SUMMARY,
        FAMILY_NUCLIDE_MISSION_VALIDATION,
        FAMILY_NUCLIDE_MISSION_TIMELINE,
        SLANT45_MISSION_SUMMARY,
        SLANT45_MISSION_VALIDATION,
        SLANT45_MISSION_TIMELINE,
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing authority files:\n" + "\n".join(missing))

    reference = read_json(REFERENCE_BREAKDOWN)
    manifest = read_json(FINAL_MANIFEST)
    activation = read_json(ACTIVATION_CAMPAIGN)
    if (
        activation.get("status")
        != "PASS_S3D_O8_ALL8_ACTIVATION_AND_FAMILY_DELAYED_TRANSPORT"
    ):
        raise RuntimeError(
            f"Activation authority is not PASS: {activation.get('status')}"
        )
    components = read_json(DELAYED_COMPONENTS)
    if components.get("status") != "PASS_S3D_O8_ALL8_STEP05_DELAYED_COMPONENTS":
        raise RuntimeError(
            f"Delayed-component authority is not PASS: {components.get('status')}"
        )
    step05 = read_json(STEP05_SUMMARY)
    if step05.get("status") != "PASS_S3D_O8_ALL8_ACTIVATION_STEP05_DAY15":
        raise RuntimeError(f"Step05 authority is not PASS: {step05.get('status')}")
    response = read_json(ENERGY_RESPONSE_SUMMARY)
    if (
        response.get("status")
        != "PASS_S3D_O8_ALL8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE"
    ):
        raise RuntimeError(f"Energy-response authority is not PASS: {response.get('status')}")
    response_validation = read_json(ENERGY_RESPONSE_VALIDATION)
    if (
        response_validation.get("status")
        != "PASS_S3D_O8_ALL8_ENERGY_RESPONSE_VALIDATION"
        or response_validation.get("problems")
    ):
        raise RuntimeError(
            "Energy-response validation is not clean PASS: "
            f"{response_validation.get('status')}, "
            f"problems={response_validation.get('problems')}"
        )
    if response_validation.get("summary_sha256") != sha256(ENERGY_RESPONSE_SUMMARY):
        raise RuntimeError("Energy-response validation does not bind the current summary")
    mission = read_json(FAMILY_NUCLIDE_MISSION_SUMMARY)
    if mission.get("status") != "PASS_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_CLOSURE":
        raise RuntimeError(f"Family/nuclide mission authority is not PASS: {mission.get('status')}")
    mission_validation = read_json(FAMILY_NUCLIDE_MISSION_VALIDATION)
    if (
        mission_validation.get("status")
        != "PASS_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_VALIDATION"
        or mission_validation.get("problems")
    ):
        raise RuntimeError(
            "Family/nuclide mission validation is not clean PASS: "
            f"{mission_validation.get('status')}, "
            f"problems={mission_validation.get('problems')}"
        )
    if (
        mission_validation.get("response_validation_status")
        != response_validation.get("status")
    ):
        raise RuntimeError("Mission validation is not bound to the PASS response validation")
    if mission_validation.get("summary_sha256") != sha256(
        FAMILY_NUCLIDE_MISSION_SUMMARY
    ):
        raise RuntimeError("Mission validation does not bind the current summary")
    if mission_validation.get("mission_timeline_sha256") != sha256(
        FAMILY_NUCLIDE_MISSION_TIMELINE
    ):
        raise RuntimeError("Mission validation does not bind the current timeline")
    slant45 = read_json(SLANT45_MISSION_SUMMARY)
    slant45_validation = read_json(SLANT45_MISSION_VALIDATION)
    if (
        slant45.get("status") != "PASS_EA_P02_FIXED_45DEG_SLANT_SIGNAL_REFOLD"
        or slant45.get("problems")
    ):
        raise RuntimeError(
            f"45-degree slant refold is not clean PASS: {slant45.get('status')}, "
            f"problems={slant45.get('problems')}"
        )
    if (
        slant45_validation.get("status")
        != "PASS_EA_P02_FIXED_45DEG_SLANT_SIGNAL_REFOLD_VALIDATION"
        or slant45_validation.get("problems")
    ):
        raise RuntimeError(
            "45-degree slant validation is not clean PASS: "
            f"{slant45_validation.get('status')}, "
            f"problems={slant45_validation.get('problems')}"
        )
    if slant45_validation.get("summary_sha256") != sha256(SLANT45_MISSION_SUMMARY):
        raise RuntimeError("45-degree validation does not bind the current summary")
    if slant45_validation.get("timeline_sha256") != sha256(SLANT45_MISSION_TIMELINE):
        raise RuntimeError("45-degree validation does not bind the current timeline")
    slant_inputs = slant45.get("input_authorities") or {}
    if slant_inputs.get("retained_mission_summary_sha256") != sha256(
        FAMILY_NUCLIDE_MISSION_SUMMARY
    ):
        raise RuntimeError("45-degree refold is not bound to the retained mission summary")
    if slant_inputs.get("retained_mission_timeline_sha256") != sha256(
        FAMILY_NUCLIDE_MISSION_TIMELINE
    ):
        raise RuntimeError("45-degree refold is not bound to the retained mission timeline")
    final05 = response["primary_authority"]["step05"]
    final08 = slant45["mission"]
    provenance = {
        "status": "SOURCE_BACKED_FIGURES_GENERATED",
        "generator": str(Path(__file__).resolve().relative_to(ROOT)),
        "authority_gates": {
            "activation_campaign_status": activation["status"],
            "delayed_components_status": components["status"],
            "step05_status": step05["status"],
            "response_summary_status": response["status"],
            "response_validation_status": response_validation["status"],
            "mission_summary_status": mission["status"],
            "mission_validation_status": mission_validation["status"],
            "slant45_signal_refold_status": slant45["status"],
            "slant45_signal_refold_validation_status": slant45_validation["status"],
            "families_rechecked": mission_validation["families_rechecked"],
            "selected_events_rechecked": mission_validation[
                "selected_events_rechecked"
            ],
        },
        "inputs": {
            str(path.relative_to(ROOT)): {"sha256": sha256(path)} for path in required
        },
    }

    build_mass_model_figure(provenance)
    build_background_origin_figure(reference, provenance)
    build_final_design_figure(manifest, final05, provenance)
    build_mission_figure(final08, slant45_validation, provenance)

    figure_outputs = [
        OUT / "fig_reference_detector_cryostat_geometry.png",
        OUT / "fig_background_origin_story.png",
        OUT / "fig_background_origin_story.svg",
        OUT / "fig_optimized_shield_background.png",
        OUT / "fig_optimized_shield_background.svg",
        OUT / "fig_optimized_mission_significance.png",
        OUT / "fig_optimized_mission_significance.svg",
    ]
    provenance["outputs"] = {
        path.name: {"sha256": sha256(path), "size_bytes": path.stat().st_size}
        for path in figure_outputs
    }
    provenance_path = OUT / "background_optimization_story_provenance_20260713.json"
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": provenance["status"],
                "outputs": [path.name for path in figure_outputs]
                + [provenance_path.name],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
