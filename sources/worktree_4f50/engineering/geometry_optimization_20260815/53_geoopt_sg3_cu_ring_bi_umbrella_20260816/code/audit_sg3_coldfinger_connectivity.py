#!/usr/bin/env python3
"""Audit the inherited SG3 Cu cold-finger chain and render its footprint.

This is a geometry-only diagnostic.  It launches no transport and does not
change the SG3 geometry.  The audit is deliberately pinned to the reviewed
SF3 parent and SG3 child bytes.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sg3_coldfinger_audit_mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Rectangle


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
SG3_GEO = PACKAGE / "geometry/DEMO2_DR_v3p5_SG3.geo"
SF3_GEO = Path(
    "/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/48_geoopt_sf3_windowed_w_nearfield_20260816/"
    "geometry/DEMO2_DR_v3p5_SF3.geo"
)
BASE_AUDIT = PACKAGE / "audit/sg3_geometry_validation.json"
OUTPUT_AUDIT = PACKAGE / "audit/sg3_coldfinger_connectivity_and_minimal_delta.json"
FIGURE_STEM = PACKAGE / "figures/sg3_coldfinger_connectivity"
TOOL = SCRIPT.parents[2] / "52_se3_sf3_activation_prompt_section_tool_20260816/TOOL"
MESH = TOOL / "inputs/se3_geometry_mesh_products.npz"
EVENTLIST = Path(
    "/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/47_se3_plan1_transport_20260815/config/"
    "signal_eventlists/signal_full_envelope_se3.eventlist.dat"
)

PINNED = {
    "sf3": (697_978, "7d2a5ee19d118d8ecb2c095203d7a8c6046e3c0e0020a67ba63d77ba399d8b16"),
    "sg3": (697_331, "f0bb7f993b6804522fb0ad239b629405949ac70d4a6b0476ecd942d73bb887c5"),
}

RODS = {
    "Cu_ColdFinger_OffAxis_YP_ZP_from_Disk_to_Stem": (1.1375, 0.113137085, 0.113137085, 4.7425, 1.1, -4.1),
    "Cu_ColdFinger_OffAxis_YM_ZP_from_Disk_to_Stem": (1.1375, 0.113137085, 0.113137085, 4.7425, -1.1, -4.1),
    "Cu_ColdFinger_OffAxis_YP_ZM_from_Disk_to_Stem": (1.5375, 0.113137085, 0.113137085, 5.1425, 1.1, -6.3),
    "Cu_ColdFinger_OffAxis_YM_ZM_from_Disk_to_Stem": (1.5375, 0.113137085, 0.113137085, 5.1425, -1.1, -6.3),
}
STEMS = {
    "Cu_ColdFinger_Stem_YP_ZP_to_MXC": (1.9, 0.16, 6.05, 1.1, -2.2),
    "Cu_ColdFinger_Stem_YM_ZP_to_MXC": (1.9, 0.16, 6.05, -1.1, -2.2),
    "Cu_ColdFinger_Stem_YP_ZM_to_MXC": (3.0, 0.16, 6.85, 1.1, -3.3),
    "Cu_ColdFinger_Stem_YM_ZM_to_MXC": (3.0, 0.16, 6.85, -1.1, -3.3),
}
CLAMPS = {
    "Cu_MXC_Clamp_Pad_YP_ZP_for_OffAxisStem": (6.05, 1.1, -0.4),
    "Cu_MXC_Clamp_Pad_YM_ZP_for_OffAxisStem": (6.05, -1.1, -0.4),
    "Cu_MXC_Clamp_Pad_YP_ZM_for_OffAxisStem": (6.85, 1.1, -0.4),
    "Cu_MXC_Clamp_Pad_YM_ZM_for_OffAxisStem": (6.85, -1.1, -0.4),
}

RING_X = (3.245, 3.595)
RING_CENTER_Z = -5.2
RING_OUTER_HALF = 2.8
RING_INNER_HALF = 0.8
CU_DENSITY = 8.96


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pinned_record(path: Path, key: str) -> dict[str, object]:
    record = {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
    expected_bytes, expected_sha = PINNED[key]
    if (record["bytes"], record["sha256"]) != (expected_bytes, expected_sha):
        raise RuntimeError(f"{key.upper()} geometry drift: {record}")
    return record


def definition_lines(text: str, name: str) -> list[str]:
    lines = [
        line
        for line in text.splitlines()
        if line == f"Volume {name}" or line.startswith(f"{name}.")
    ]
    if len(lines) != 6:
        raise RuntimeError(f"expected six definition lines for {name}, found {len(lines)}")
    return lines


def number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else repr(value)


def expected_lines() -> dict[str, list[str]]:
    expected: dict[str, list[str]] = {}
    for name, (hx, hy, hz, x, y, z) in RODS.items():
        expected[name] = [
            f"Volume {name}",
            f"{name}.Material Copper",
            f"{name}.Visibility 1",
            f"{name}.Shape BRIK {number(hx)} {number(hy)} {number(hz)}",
            f"{name}.Position {number(x)} {number(y)} {number(z)}",
            f"{name}.Mother InstrumentFrame",
        ]
    for name, (half_length, radius, x, y, z) in STEMS.items():
        expected[name] = [
            f"Volume {name}",
            f"{name}.Material Copper",
            f"{name}.Visibility 1",
            f"{name}.Shape PCON 0 360 2 {number(-half_length)} 0 {number(radius)} {number(half_length)} 0 {number(radius)}",
            f"{name}.Position {number(x)} {number(y)} {number(z)}",
            f"{name}.Mother InstrumentFrame",
        ]
    for name, (x, y, z) in CLAMPS.items():
        expected[name] = [
            f"Volume {name}",
            f"{name}.Material Copper",
            f"{name}.Visibility 1",
            f"{name}.Shape PCON 0 360 2 -0.1 0.18 0.35 0.1 0.18 0.35",
            f"{name}.Position {number(x)} {number(y)} {number(z)}",
            f"{name}.Mother InstrumentFrame",
        ]
    return expected


def signal_intersections() -> tuple[np.ndarray, int]:
    mesh = np.load(MESH)
    events = np.loadtxt(EVENTLIST, dtype=np.float64)
    if len(events) != 37_194:
        raise RuntimeError(f"focused EventList row drift: {len(events)}")
    rotation = mesh["instrument_from_world_rotation"]
    points = events[:, 5:8] @ rotation.T
    directions = events[:, 8:11] @ rotation.T
    distance = (3.42 - points[:, 0]) / directions[:, 0]
    intersections = points + distance[:, None] * directions
    y = intersections[:, 1]
    z_relative = intersections[:, 2] - RING_CENTER_Z
    centered_pole_r = 0.16
    footprint_hits = int(np.count_nonzero(y * y + z_relative * z_relative <= centered_pole_r**2))
    return np.column_stack((y, z_relative)), footprint_hits


def render_figure(intersections: np.ndarray, footprint_hits: int) -> list[dict[str, object]]:
    plt.rcParams.update({"font.size": 8.0, "axes.grid": True, "grid.alpha": 0.18})
    fig, (ax, side) = plt.subplots(1, 2, figsize=(12.6, 5.8))

    # Ring-plane y'-z' footprint.  The four cold-finger feet are visible here,
    # unlike in the retained y'=0 global/local sections.
    outer = Rectangle((-2.8, -2.8), 5.6, 5.6, facecolor="#D56A2A", edgecolor="#78330E", alpha=0.50)
    hole = Rectangle((-0.8, -0.8), 1.6, 1.6, facecolor="white", edgecolor="#78330E", hatch="//", linewidth=1.2)
    substrate = Rectangle((-1.8, -1.8), 3.6, 3.6, fill=False, edgecolor="#247BA0", linestyle="--", linewidth=1.1)
    ax.add_patch(outer)
    ax.add_patch(hole)
    ax.add_patch(substrate)
    stride = max(1, len(intersections) // 7000)
    ax.scatter(intersections[::stride, 0], intersections[::stride, 1], s=2.0, color="#6B46C1", alpha=0.13, linewidths=0)
    for y in (-1.1, 1.1):
        for zr in (-1.1, 1.1):
            ax.add_patch(Rectangle((y - 0.113137085, zr - 0.113137085), 0.22627417, 0.22627417,
                                   facecolor="#8B4513", edgecolor="black", linewidth=0.8, zorder=6))
    ax.add_patch(Circle((0, 0), 0.16, fill=False, edgecolor="#C53030", linestyle=(0, (4, 2)), linewidth=1.4, zorder=7))
    ax.scatter([-0.347], [0.530], marker="*", s=75, color="#C53030", edgecolor="white", linewidth=0.5, zorder=8)
    ax.annotate(f"hypothetical central r=1.6 mm pole\n{footprint_hits:,}/37,194 ray-plane intersections",
                xy=(0.14, 0.08), xytext=(0.45, 0.52), color="#9B2C2C",
                arrowprops={"arrowstyle": "->", "color": "#9B2C2C", "lw": 0.8})
    ax.set(xlabel="InstrumentFrame y' [cm]", ylabel="z' - z'ring [cm]", xlim=(-3.1, 3.1), ylim=(-3.1, 3.1),
           title="Ring-plane footprint: four inherited Cu cold-finger feet")
    ax.set_aspect("equal")

    # Side topology at y'=+1.1 cm.  Tiny gaps are deliberate navigation
    # clearances in the transport mass model, not a thermal-contact solution.
    side.add_patch(Rectangle((RING_X[0], -8.0), RING_X[1] - RING_X[0], 5.6,
                             facecolor="#D56A2A", edgecolor="#78330E", alpha=0.62, label="SG3 Cu ring at y'=+1.1"))
    for _, (hx, _, hz, x, y, z) in RODS.items():
        if y > 0:
            side.add_patch(Rectangle((x - hx, z - hz), 2 * hx, 2 * hz,
                                     facecolor="#B87333", edgecolor="#6B3515"))
    for _, (half_length, radius, x, y, z) in STEMS.items():
        if y > 0:
            side.add_patch(Rectangle((x - radius, z - half_length), 2 * radius, 2 * half_length,
                                     facecolor="#B87333", edgecolor="#6B3515"))
    for _, (x, y, z) in CLAMPS.items():
        if y > 0:
            side.add_patch(Rectangle((x - 0.35, z - 0.1), 0.70, 0.20,
                                     facecolor="#E2A76F", edgecolor="#6B3515"))
    side.add_patch(Rectangle((-15, -0.2), 30, 0.4, facecolor="#C9D1D9", edgecolor="#57606A", alpha=0.6,
                             label="inherited MXC plate"))
    side.annotate("1.0 mm mass-model\nclearance to MXC plate", xy=(6.45, -0.25), xytext=(3.8, 0.75),
                  arrowprops={"arrowstyle": "->", "lw": 0.8})
    side.annotate("0.1 mm navigation gaps", xy=(3.60, -4.1), xytext=(0.2, -3.25),
                  arrowprops={"arrowstyle": "->", "lw": 0.8})
    side.set(xlabel="InstrumentFrame x' [cm]", ylabel="InstrumentFrame z' [cm]", xlim=(2.7, 7.5), ylim=(-8.4, 1.35),
             title="Inherited four-chain topology (shown at y'=+1.1 cm)")
    side.legend(loc="lower left", frameon=False)

    fig.suptitle("SG3 cold-finger connectivity audit — geometry diagnostic only; no transport", weight="bold")
    fig.tight_layout()
    outputs: list[dict[str, object]] = []
    for suffix in (".png", ".svg", ".pdf"):
        path = FIGURE_STEM.with_suffix(suffix)
        fig.savefig(path, dpi=220 if suffix == ".png" else None, bbox_inches="tight")
        outputs.append({"path": str(path), "sha256": sha256(path)})
    plt.close(fig)
    return outputs


def main() -> int:
    sf3_record = pinned_record(SF3_GEO, "sf3")
    sg3_record = pinned_record(SG3_GEO, "sg3")
    sf3_text = SF3_GEO.read_text(encoding="utf-8")
    sg3_text = SG3_GEO.read_text(encoding="utf-8")
    definitions = expected_lines()
    identity: dict[str, bool] = {}
    for name, expected in definitions.items():
        parent = definition_lines(sf3_text, name)
        child = definition_lines(sg3_text, name)
        identity[name] = parent == child == expected
    if not all(identity.values()):
        raise RuntimeError(f"cold-finger definition drift: {identity}")

    contacts = []
    for name, (_, hy, hz, _, y, z) in RODS.items():
        z_relative = z - RING_CENTER_Z
        max_inner_edge = max(abs(y) - hy, abs(z_relative) - hz)
        max_outer_edge = max(abs(y) + hy, abs(z_relative) + hz)
        inside_band = max_inner_edge >= RING_INNER_HALF and max_outer_edge <= RING_OUTER_HALF
        contacts.append({
            "volume": name,
            "foot_center_y_zrelative_cm": [y, z_relative],
            "entire_foot_inside_ring_band": inside_band,
            "inner_cut_clearance_cm": max_inner_edge - RING_INNER_HALF,
            "outer_edge_clearance_cm": RING_OUTER_HALF - max_outer_edge,
            "ring_to_rod_navigation_clearance_x_cm": (4.7425 - 1.1375 if z > RING_CENTER_Z else 5.1425 - 1.5375) - RING_X[1],
        })
    if not all(item["entire_foot_inside_ring_band"] for item in contacts):
        raise RuntimeError("one or more cold-finger feet miss the SG3 ring")

    rod_volume = sum(8 * hx * hy * hz for hx, hy, hz, *_ in RODS.values())
    stem_volume = sum(math.pi * radius**2 * (2 * half_length) for half_length, radius, *_ in STEMS.values())
    clamp_volume = len(CLAMPS) * math.pi * (0.35**2 - 0.18**2) * 0.2
    chain_volume = rod_volume + stem_volume + clamp_volume

    base = json.loads(BASE_AUDIT.read_text(encoding="utf-8"))
    expected_removed = {
        "Cu_SubstrateSupport_SolidDisk_L0_deepest",
        "SF3_W_NearField_FrontWindowPlate_2p9mm",
        "SF3_W_NearField_RearColdFingerAnnulus_2p9mm",
        "SF3_W_NearField_SideSleeve_2p9mm",
    }
    expected_added = {
        "SG3_Bi_MXC_TES_ShadowUmbrella_4p796mm",
        "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm",
    }
    minimal_delta_pass = (
        base["status"] == "PASS__SG3_TWO_CHANGE_BYTE_REVERSIBLE_SF3_CHILD"
        and base["fidelity"]["sf3_geo_reconstructed_byte_exact"]
        and base["fidelity"]["sf3_detector_map_reconstructed_byte_exact"]
        and set(base["fidelity"]["removed_physical_volumes"]) == expected_removed
        and set(base["fidelity"]["added_physical_volumes"]) == expected_added
    )
    if not minimal_delta_pass:
        raise RuntimeError("base SG3 minimal-delta audit no longer closes")

    intersections, footprint_hits = signal_intersections()
    figures = render_figure(intersections, footprint_hits)
    payload = {
        "status": "PASS__FOUR_INHERITED_COLD_FINGER_CHAINS_UNCHANGED_AND_RING_CAPTURED",
        "transport_launched": False,
        "geometry_modified_by_this_audit": False,
        "geometry": {"sf3_parent": sf3_record, "sg3_child": sg3_record},
        "cold_finger_contract": {
            "inherited_chain_count": 4,
            "component_count": len(definitions),
            "all_12_component_definitions_byte_line_identical_sf3_to_sg3": all(identity.values()),
            "component_identity": identity,
            "all_four_rod_feet_inside_sg3_ring": True,
            "contacts": contacts,
            "mass_unchanged_from_sf3": True,
            "rod_volume_cm3": rod_volume,
            "stem_volume_cm3": stem_volume,
            "clamp_volume_cm3": clamp_volume,
            "audited_chain_volume_cm3": chain_volume,
            "audited_chain_mass_g_at_8p96": chain_volume * CU_DENSITY,
        },
        "mass_model_clearances": {
            "ring_to_horizontal_rods_cm": 0.01,
            "horizontal_rods_to_vertical_stems_cm": 0.01,
            "stem_to_clamp_radial_cm": 0.02,
            "clamp_top_to_mxc_plate_lower_face_cm": 0.10,
            "interpretation": "Deliberate transport-navigation clearances; the geometry encodes the inherited thermal-link topology but is not a literal contact/thermal-conductance model.",
        },
        "minimal_delta": {
            "pass": minimal_delta_pass,
            "physical_changes_only": ["SF3 solid L0 Cu disk -> SG3 Cu ring", "three SF3 passive W volumes -> one SG3 passive Bi umbrella"],
            "pole_or_cold_finger_change": "NONE",
        },
        "central_hole_routing_screen": {
            "hypothetical_centered_pole_radius_cm": 0.16,
            "focused_ray_intersections_at_ring_plane": footprint_hits,
            "focused_ray_total": len(intersections),
            "fraction": footprint_hits / len(intersections),
            "scope": "Plane-footprint diagnostic only, not a transport efficiency prediction.",
            "decision": "Do not repopulate the opened central corridor; retain the four inherited off-axis chains.",
        },
        "figures": figures,
    }
    OUTPUT_AUDIT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "mass_g": chain_volume * CU_DENSITY,
                      "central_footprint_hits": footprint_hits, "figure": figures[0]["path"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
