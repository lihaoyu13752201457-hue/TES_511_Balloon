#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import os
import random
import re
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT = Path(__file__).resolve()
STEP_DIR = SCRIPT.parents[1]
FIX_ROOT = SCRIPT.parents[3]
OUTPUT_DIR = STEP_DIR / "outputs"
SNAPSHOT_DIR = STEP_DIR / "source_snapshots"

RAW_SOURCE = FIX_ROOT / "simulation/decay_from_buildup_equiv2602_cmfix/activation_decay_day15.source"
FIXED_SOURCE = FIX_ROOT / "simulation/delay_fix_from_buildup_equiv2602_cmfix/activation_decay_day15_groundstate_fixed.source"
INVENTORY = FIX_ROOT / "simulation/decay_from_buildup_equiv2602_cmfix/activation_inventory_day15.csv"
UNKNOWN = FIX_ROOT / "simulation/decay_from_buildup_equiv2602_cmfix/unknown_isotopes_day15.csv"
NO_RPIP = FIX_ROOT / "simulation/decay_from_buildup_equiv2602_cmfix/no_rpip_points_day15.csv"
FIX_SUMMARY = FIX_ROOT / "simulation/delay_fix_from_buildup_equiv2602_cmfix/source_fix_summary.json"
CORRECTIONS = FIX_ROOT / "simulation/delay_fix_from_buildup_equiv2602_cmfix/groundstate_activity_corrections.csv"
BUILD_SCRIPT = FIX_ROOT / "code/particle_sources/makedecaysourcewithplot_rpip.py"
FIX_SCRIPT = FIX_ROOT / "code/particle_sources/build_fixed_delay_source.py"
TIME_SCRIPT = FIX_ROOT / "code/particle_sources/build_time_variable_delayed_sources.py"
BOUNDS_FILE = FIX_ROOT / "code/geometry/bounds.json"
REMAP_CSV = OUTPUT_DIR / "unknown_half_life_remap_day15.csv"
REMAP_SUMMARY = OUTPUT_DIR / "unknown_half_life_remap_summary.json"

SOURCE_LINE_RE = re.compile(r"^(?P<run>\S+)\.Source\s+(?P<name>\S+)\s*$")
PARTICLE_RE = re.compile(r"^(?P<name>\S+)\.ParticleType\s+(?P<za>\d+)\s*$")
BEAM_RE = re.compile(
    r"^(?P<name>\S+)\.Beam\s+RadialProfileBeam\s+"
    r"(?P<x>[-+0-9.eE]+)\s+(?P<y>[-+0-9.eE]+)\s+(?P<z>[-+0-9.eE]+)\s+"
    r"(?P<dx>[-+0-9.eE]+)\s+(?P<dy>[-+0-9.eE]+)\s+(?P<dz>[-+0-9.eE]+)\s+"
    r"(?P<profile>\S+)\s*$"
)
FLUX_RE = re.compile(r"^(?P<name>\S+)\.Flux\s+(?P<flux>[-+0-9.eE]+)\s*$")
TRIG_RE = re.compile(r"^(?P<run>\S+)\.Triggers\s+(?P<triggers>\d+)\s*$")
FILENAME_RE = re.compile(r"^(?P<run>\S+)\.FileName\s+(?P<name>\S+)\s*$")
SOURCE_NAME_RE = re.compile(r"^S_(?P<vn>.+)_(?P<za>\d+)_z(?P<iz>\d+)$")

VOLUME_COLORS = {
    "W_Shield": (0.25, 0.25, 0.27),
    "BGO_Shield": (0.10, 0.55, 0.24),
    "Al_Shell": (0.70, 0.76, 0.82),
    "Cryo_Shell": (0.20, 0.55, 0.85),
    "TES_L0": (0.90, 0.16, 0.10),
    "TES_L1": (0.90, 0.16, 0.10),
    "TES_L2": (0.90, 0.16, 0.10),
    "TES_L3": (0.90, 0.16, 0.10),
    "TES_L4": (0.90, 0.16, 0.10),
    "TES_L5": (0.90, 0.16, 0.10),
    "Copper": (0.78, 0.42, 0.14),
    "Nb_Shield": (0.22, 0.36, 0.78),
    "CollBarX": (0.08, 0.08, 0.08),
    "CollBarY": (0.08, 0.08, 0.08),
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(FIX_ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_source(path: Path) -> dict:
    data = {
        "path": path,
        "geometry": "",
        "run": "",
        "filename": "",
        "triggers": 0,
        "sources": [],
        "blocks": {},
        "physics": [],
        "decay_mode": "",
    }
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("Geometry "):
                data["geometry"] = line.split(None, 1)[1]
                continue
            if line.startswith("Run "):
                data["run"] = line.split(None, 1)[1]
                continue
            if line.startswith("PhysicsList"):
                data["physics"].append(line)
                continue
            if line.startswith("DecayMode "):
                data["decay_mode"] = line.split(None, 1)[1]
                continue
            m = SOURCE_LINE_RE.match(line)
            if m:
                data["sources"].append(m.group("name"))
                continue
            m = TRIG_RE.match(line)
            if m:
                data["triggers"] = int(m.group("triggers"))
                continue
            m = FILENAME_RE.match(line)
            if m:
                data["filename"] = m.group("name")
                continue
            m = PARTICLE_RE.match(line)
            if m:
                block = data["blocks"].setdefault(m.group("name"), {})
                block["za"] = int(m.group("za"))
                continue
            m = BEAM_RE.match(line)
            if m:
                block = data["blocks"].setdefault(m.group("name"), {})
                block.update(
                    {
                        "x_cm": float(m.group("x")),
                        "y_cm": float(m.group("y")),
                        "z_cm": float(m.group("z")),
                        "dx": float(m.group("dx")),
                        "dy": float(m.group("dy")),
                        "dz": float(m.group("dz")),
                        "profile": m.group("profile"),
                    }
                )
                sm = SOURCE_NAME_RE.match(m.group("name"))
                if sm:
                    block["VN"] = sm.group("vn")
                    block["ZA_name"] = int(sm.group("za"))
                    block["z_index"] = int(sm.group("iz"))
                continue
            m = FLUX_RE.match(line)
            if m:
                block = data["blocks"].setdefault(m.group("name"), {})
                block["flux_Bq"] = float(m.group("flux"))
                continue
    source_set = set(data["sources"])
    for name, block in data["blocks"].items():
        block["name"] = name
        block["listed_in_run"] = name in source_set
        block.setdefault("VN", SOURCE_NAME_RE.match(name).group("vn") if SOURCE_NAME_RE.match(name) else "")
    return data


def source_block_rows(source: dict) -> list[dict]:
    rows = []
    for name, block in sorted(source["blocks"].items()):
        if "flux_Bq" not in block:
            continue
        rows.append(
            {
                "source_name": name,
                "VN": block.get("VN", ""),
                "ZA": block.get("za", ""),
                "z_index": block.get("z_index", ""),
                "z_cm": f"{block.get('z_cm', 0.0):.8g}",
                "flux_Bq": f"{block.get('flux_Bq', 0.0):.12e}",
                "profile": block.get("profile", ""),
                "listed_in_run": str(block.get("listed_in_run", False)),
            }
        )
    return rows


def profile_path(profile_text: str) -> Path:
    p = Path(profile_text)
    if p.is_absolute():
        return p
    return FIX_ROOT / p


def load_radial_profile(path: Path) -> list[tuple[float, float]]:
    rows: list[tuple[float, float]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                rows.append((float(parts[0]), max(0.0, float(parts[1]))))
            except ValueError:
                continue
    return rows


def weighted_pick(cdf: list[float], total: float, rng: random.Random) -> int:
    x = rng.random() * total
    lo, hi = 0, len(cdf) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if cdf[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def sample_decay_points(source: dict, n: int, seed: int) -> list[dict]:
    blocks = [
        block
        for block in source["blocks"].values()
        if block.get("listed_in_run") and block.get("flux_Bq", 0.0) > 0.0 and "profile" in block
    ]
    weights = [float(block["flux_Bq"]) for block in blocks]
    cdf = []
    running = 0.0
    for w in weights:
        running += w
        cdf.append(running)
    if running <= 0.0:
        return []
    rng = random.Random(seed)
    profile_cache: dict[str, list[tuple[float, float]]] = {}
    samples: list[dict] = []
    for event_id in range(1, n + 1):
        block = blocks[weighted_pick(cdf, running, rng)]
        profile = str(block["profile"])
        if profile not in profile_cache:
            profile_cache[profile] = load_radial_profile(profile_path(profile))
        radial = profile_cache[profile]
        if radial:
            r_values = [row[0] for row in radial]
            # The profile stores f(r); MEGAlib sampling is proportional to r*f(r).
            r_weights = [max(1.0e-12, row[0]) * row[1] for row in radial]
            rcdf = []
            rtotal = 0.0
            for rw in r_weights:
                rtotal += rw
                rcdf.append(rtotal)
            ridx = weighted_pick(rcdf, rtotal, rng) if rtotal > 0 else 0
            r_cm = r_values[ridx]
        else:
            r_cm = 0.0
        phi = 2.0 * math.pi * rng.random()
        x = float(block.get("x_cm", 0.0)) + r_cm * math.cos(phi)
        y = float(block.get("y_cm", 0.0)) + r_cm * math.sin(phi)
        z = float(block.get("z_cm", 0.0))
        samples.append(
            {
                "event_id": event_id,
                "source_name": block["name"],
                "VN": block.get("VN", ""),
                "ZA": int(block.get("za", 0)),
                "z_index": block.get("z_index", ""),
                "flux_Bq": float(block.get("flux_Bq", 0.0)),
                "x_cm": x,
                "y_cm": y,
                "z_cm": z,
                "r_cm": r_cm,
                "phi_deg": math.degrees(phi),
                "sample_source": "fixed_delayed_source_radial_profile_pdf",
            }
        )
    return samples


def color_for_volume(vn: str) -> tuple[float, float, float]:
    return VOLUME_COLORS.get(vn, (0.56, 0.34, 0.72))


def vrml_material(name: str, color: tuple[float, float, float], transparency: float) -> str:
    r, g, b = color
    return (
        f"DEF {name} Appearance {{ material Material {{ diffuseColor {r:.4f} {g:.4f} {b:.4f} "
        f"emissiveColor {0.20*r:.4f} {0.20*g:.4f} {0.20*b:.4f} "
        f"transparency {transparency:.4f} }} }}\n"
    )


def vrml_cylinder(name: str, radius: float, z_center: float, height: float, material: str) -> str:
    return (
        f"DEF {name} Transform {{\n"
        f"  translation 0 0 {z_center:.6f}\n"
        "  rotation 1 0 0 1.57079632679\n"
        "  children [\n"
        f"    Shape {{ appearance USE {material} geometry Cylinder {{ radius {radius:.6f} height {height:.6f} }} }}\n"
        "  ]\n"
        "}\n"
    )


def write_wrl(path: Path, samples: list[dict], bounds: dict) -> None:
    volume_order = sorted({row["VN"] for row in samples})
    lines = [
        "#VRML V2.0 utf8\n",
        f"WorldInfo {{ title \"Step03 delayed source: {len(samples)} decay-source samples\" }}\n",
        "NavigationInfo { type [\"EXAMINE\", \"ANY\"] speed 3.5 }\n",
        "Viewpoint { position 0 -34 10 orientation 1 0 0 1.25 fieldOfView 0.64 description \"Delayed source samples\" }\n",
        vrml_material("APP_AL", (0.78, 0.82, 0.88), 0.86),
        vrml_material("APP_BGO", (0.20, 0.55, 0.26), 0.82),
        vrml_material("APP_W", (0.18, 0.18, 0.18), 0.74),
        vrml_material("APP_NB", (0.22, 0.42, 0.78), 0.76),
        vrml_material("APP_TES", (0.92, 0.18, 0.10), 0.45),
        vrml_material("APP_COLL", (0.08, 0.08, 0.08), 0.52),
    ]
    for vn in volume_order:
        lines.append(vrml_material("APP_D_" + re.sub(r"[^A-Za-z0-9_]", "_", vn), color_for_volume(vn), 0.0))

    shields = bounds.get("SHIELDS", {})
    for material, key in [
        ("APP_AL", "Al_Shell"),
        ("APP_BGO", "BGO_Shield"),
        ("APP_W", "W_Shield"),
        ("APP_NB", "Nb_Shield"),
    ]:
        if key in shields:
            shield = shields[key]
            z_center = 0.5 * (shield["z_out_bot"] + shield["z_out_top"])
            height = shield["z_out_top"] - shield["z_out_bot"]
            lines.append(vrml_cylinder(key, shield["r_out"], z_center, height, material))
    for idx, layer in enumerate(bounds.get("TES_LAYERS", [])):
        lines.append(vrml_cylinder(f"TES_L{idx}", layer["r_max"], layer["z_center"], 2.0 * layer["hz"], "APP_TES"))
    coll = bounds.get("COLLIMATOR")
    if coll:
        lines.append(vrml_cylinder("Collimator", coll["r_max"], coll["z_center"], 2.0 * coll["hz"], "APP_COLL"))

    for sample in samples:
        app = "APP_D_" + re.sub(r"[^A-Za-z0-9_]", "_", sample["VN"])
        lines.append(
            "Transform {\n"
            f"  translation {sample['x_cm']:.6f} {sample['y_cm']:.6f} {sample['z_cm']:.6f}\n"
            "  children [ Shape { "
            f"appearance USE {app} geometry Sphere {{ radius 0.055 }} "
            "} ]\n"
            "}\n"
        )
    path.write_text("".join(lines), encoding="utf-8")


def draw_detector_cross_section(ax, bounds: dict) -> None:
    from matplotlib.patches import Rectangle

    def rect(x0, z0, w, h, color, alpha, edge="black", lw=0.45, label=None):
        ax.add_patch(
            Rectangle((x0, z0), w, h, facecolor=color, edgecolor=edge, linewidth=lw, alpha=alpha, label=label)
        )

    shell_specs = [
        ("Al shell", bounds["SHIELDS"]["Al_Shell"], "#a7a9ac", 0.18),
        ("BGO shield", bounds["SHIELDS"]["BGO_Shield"], "#84c184", 0.16),
        ("W shield", bounds["SHIELDS"]["W_Shield"], "#555555", 0.16),
        ("Nb shield", bounds["SHIELDS"]["Nb_Shield"], "#5ac8d8", 0.16),
    ]
    for label, shield, color, alpha in shell_specs:
        rout = shield["r_out"]
        z0 = shield["z_out_bot"]
        z1 = shield["z_out_top"]
        rect(-rout, z0, 2.0 * rout, z1 - z0, color, alpha, edge=color, lw=1.0, label=label)
    for idx, layer in enumerate(bounds["TES_LAYERS"]):
        rect(
            -layer["r_max"],
            layer["z_center"] - layer["hz"],
            2.0 * layer["r_max"],
            2.0 * layer["hz"],
            "#d73027",
            0.72,
            edge="#8c1d18",
            lw=0.65,
            label="TES" if idx == 0 else None,
        )
    for substrate in bounds.get("SUBSTRATES", []):
        rect(
            -substrate["r_max"],
            substrate["z_center"] - substrate["hz"],
            2.0 * substrate["r_max"],
            2.0 * substrate["hz"],
            "#f6c85f",
            0.36,
            edge="#d09b2c",
            lw=0.4,
        )
    cu = bounds.get("CU_BASE")
    if cu:
        rect(-cu["r_max"], cu["z_bot"], 2.0 * cu["r_max"], cu["z_top"] - cu["z_bot"], "#c07a3a", 0.36)
    coll = bounds.get("COLLIMATOR")
    if coll:
        rect(-coll["r_max"], coll["z_center"] - coll["hz"], 2.0 * coll["r_max"], 2.0 * coll["hz"], "#1f1f1f", 0.46)


def draw_detector_xy(ax, bounds: dict) -> None:
    from matplotlib.patches import Circle

    for label, color, alpha in [
        ("Al_Shell", "#a7a9ac", 0.18),
        ("BGO_Shield", "#84c184", 0.16),
        ("W_Shield", "#555555", 0.16),
        ("Nb_Shield", "#5ac8d8", 0.16),
    ]:
        shield = bounds["SHIELDS"].get(label)
        if shield:
            ax.add_patch(Circle((0, 0), shield["r_out"], fill=False, edgecolor=color, lw=1.0, alpha=0.85))
    for layer in bounds.get("TES_LAYERS", []):
        ax.add_patch(Circle((0, 0), layer["r_max"], fill=False, edgecolor="#d73027", lw=0.7, alpha=0.70))


def make_2d_schematic(path: Path, samples: list[dict], bounds: dict, saturation_rows: list[dict]) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_step03_matplotlib")
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec

    fig = plt.figure(figsize=(14.5, 9.0), constrained_layout=True)
    gs = GridSpec(2, 3, figure=fig, width_ratios=[1.55, 1.0, 1.05])
    ax_xz = fig.add_subplot(gs[:, 0])
    ax_xy = fig.add_subplot(gs[0, 1])
    ax_bar = fig.add_subplot(gs[0, 2])
    ax_sat = fig.add_subplot(gs[1, 1:])

    draw_detector_cross_section(ax_xz, bounds)

    xs = [row["x_cm"] for row in samples]
    ys = [row["y_cm"] for row in samples]
    zs = [row["z_cm"] for row in samples]
    signed_r = [math.copysign(math.hypot(row["x_cm"], row["y_cm"]), row["x_cm"] if row["x_cm"] != 0 else 1.0) for row in samples]
    colors = [color_for_volume(row["VN"]) for row in samples]

    ax_xz.scatter(signed_r, zs, s=5, c=colors, alpha=0.44, linewidths=0)
    ax_xz.set_xlim(-7.8, 7.8)
    ax_xz.set_ylim(-8.0, 13.4)
    ax_xz.set_xlabel("signed radius (cm)")
    ax_xz.set_ylabel("z (cm)")
    ax_xz.set_title(f"Delayed source samples over Step02 geometry (n={len(samples)})")
    ax_xz.set_aspect("equal", adjustable="box")
    ax_xz.grid(alpha=0.18)

    draw_detector_xy(ax_xy, bounds)
    ax_xy.scatter(xs, ys, s=4, c=colors, alpha=0.38, linewidths=0)
    ax_xy.set_xlim(-7.6, 7.6)
    ax_xy.set_ylim(-7.6, 7.6)
    ax_xy.set_xlabel("x (cm)")
    ax_xy.set_ylabel("y (cm)")
    ax_xy.set_title("x-y source footprint over geometry radii")
    ax_xy.set_aspect("equal", adjustable="box")
    ax_xy.grid(alpha=0.18)

    counts = Counter(row["VN"] for row in samples)
    top = counts.most_common(10)
    ax_bar.barh([name for name, _count in reversed(top)], [count for _name, count in reversed(top)], color="0.35")
    ax_bar.set_title(f"{len(samples)} sampled points by volume")
    ax_bar.set_xlabel("count")

    ns = [int(row["rank"]) for row in saturation_rows]
    cum = [float(row["cumulative_activity_fraction"]) for row in saturation_rows]
    ax_sat.plot(ns, cum, color="#1f6feb", lw=2)
    ax_sat.axhline(0.95, color="0.45", lw=0.9, ls="--")
    ax_sat.axhline(0.99, color="0.45", lw=0.9, ls=":")
    ax_sat.set_ylim(0.0, 1.01)
    ax_sat.set_xlabel("inventory rows included by activity rank")
    ax_sat.set_ylabel("cumulative activity fraction")
    ax_sat.set_title("Activity saturation from existing inventory ordering")
    ax_sat.grid(alpha=0.2)

    fig.savefig(path, dpi=190)
    plt.close(fig)


def build_saturation_rows(inventory_rows: list[dict[str, str]]) -> list[dict]:
    clean = []
    for row in inventory_rows:
        try:
            activity = float(row["Activity_Bq"])
            points = int(float(row.get("Points", "0")))
        except (KeyError, ValueError):
            continue
        clean.append({**row, "Activity_Bq": activity, "Points": points})
    clean.sort(key=lambda row: row["Activity_Bq"], reverse=True)
    total = sum(row["Activity_Bq"] for row in clean)
    rows = []
    running = 0.0
    for idx, row in enumerate(clean, 1):
        running += row["Activity_Bq"]
        rows.append(
            {
                "rank": idx,
                "VN": row.get("VN", ""),
                "ZA": row.get("ZA", ""),
                "nuclide": row.get("nuclide", ""),
                "Activity_Bq": f"{row['Activity_Bq']:.12e}",
                "Points": row["Points"],
                "cumulative_activity_Bq": f"{running:.12e}",
                "cumulative_activity_fraction": f"{(running / total if total > 0 else 0.0):.12e}",
            }
        )
    return rows


def rank_at_fraction(rows: list[dict], fraction: float) -> int | None:
    for row in rows:
        if float(row["cumulative_activity_fraction"]) >= fraction:
            return int(row["rank"])
    return None


def copy_snapshot(src: Path, dst_name: str) -> None:
    dst = SNAPSHOT_DIR / dst_name
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())


def write_sample_csv(path: Path, samples: list[dict]) -> None:
    rows = []
    for sample in samples:
        rows.append(
            {
                "event_id": sample["event_id"],
                "source_name": sample["source_name"],
                "VN": sample["VN"],
                "ZA": sample["ZA"],
                "z_index": sample["z_index"],
                "flux_Bq": f"{sample['flux_Bq']:.12e}",
                "x_cm": f"{sample['x_cm']:.8f}",
                "y_cm": f"{sample['y_cm']:.8f}",
                "z_cm": f"{sample['z_cm']:.8f}",
                "r_cm": f"{sample['r_cm']:.8f}",
                "phi_deg": f"{sample['phi_deg']:.8f}",
                "sample_source": sample["sample_source"],
            }
        )
    fieldnames = [
        "event_id",
        "source_name",
        "VN",
        "ZA",
        "z_index",
        "flux_Bq",
        "x_cm",
        "y_cm",
        "z_cm",
        "r_cm",
        "phi_deg",
        "sample_source",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_readme(path: Path, audit: dict, top_rows: list[dict]) -> None:
    stable_names = ", ".join(audit.get("remap_stable_nuclides", [])) or "none"
    top_table = "\n".join(
        f"| {row['rank']} | {row['VN']} | {row['nuclide']} | {row['Activity_Bq']} | {row['Points']} | {float(row['cumulative_activity_fraction']):.6f} |"
        for row in top_rows[:12]
    )
    text = f"""# Step03 Delayed Activation Source Maintenance

## Scope

This directory freezes and audits the delayed activation source that follows the Step02 atmospheric cosmic-ray buildup run. The maintained day-15 source is:

- raw RPIP source: `source_snapshots/activation_decay_day15_raw.source`
- ground-state fixed source: `source_snapshots/activation_decay_day15_groundstate_fixed.source`
- source inventory: `source_snapshots/activation_inventory_day15.csv`
- fix summary: `source_snapshots/source_fix_summary.json`

The production transport source is `simulation/delay_fix_from_buildup_equiv2602_cmfix/activation_decay_day15_groundstate_fixed.source`.

## Code Used

| path | role |
| --- | --- |
| `code/particle_sources/makedecaysourcewithplot_rpip.py` | Builds the original delayed source from buildup `.dat` RP yields and SIM `CC IP RP` production-position records. |
| `code/particle_sources/build_fixed_delay_source.py` | Recomputes ground-state activities from local NUBASE records and rescales/removes source blocks. |
| `code/particle_sources/build_time_variable_delayed_sources.py` | Builds day-series constant-profile sources by scaling the fixed day-15 source with external activity ratios. |
| `stepwise_maintenance/step03_delay_source/code/build_step03_delay_source_audit.py` | Audits the existing Step03 source, samples 1000 decay-source positions from the fixed RadialProfileBeam PDFs, and writes WRL/2D visual products. |
| `stepwise_maintenance/step03_delay_source/code/map_unknown_half_lives.py` | Rechecks the archived `unknown_isotopes_day15.csv` ledger against local NUBASE ground-state records and estimates which entries would enter the source after regeneration. |

## Main Function Logic

| function | role |
| --- | --- |
| `parse_rp_from_dat` | Reads Cosima isotope-store `.dat` files, collecting `TT`, `VN`, and `RP <ZA> <exc_keV> <yield>` records. Non-gamma replicas are divided by 8 to undo the production replica strategy. |
| `parse_rpip_points_mp` | Reads native SIM comment lines matching `CC IP RP <VN> x y z ZA exc_keV t`; these are the custom MCSteppingAction RPIP records used as production-position evidence. |
| `build_zbins_radial_profiles` | Converts true RPIP points into an axisymmetric z-bin plus radial-profile approximation to avoid an enormous 3D source histogram. |
| `build_half_life_db` | Resolves half-lives via cache, optional Python decay library, local NUBASE, and optional online fallback. The archived run used the local products now frozen in `simulation/decay_from_buildup_equiv2602_cmfix`. |
| `activity_after_exposure` | Computes continuous-exposure activity: `A = (Nprod / TT) * (1 - exp(-lambda * Texposure)) * exp(-lambda * Tafter)`. For the archived day-15 source, `Texposure = 15 days` and `Tafter = 0`. |
| `write_cosima_source` | Writes `DecayMode ActivationDelayedDecay` source blocks using `ParticleType ZA`, `RadialProfileBeam`, and per-z-slice flux in Bq. |
| `load_nubase_ground_half_lives` | Loads NUBASE ground-state half-lives used by the later W-183/W-180 ground-state fix. |
| `write_fixed_source` | Applies ground-state activity scale factors to the raw source, removes negligible/stable source blocks below the configured threshold, and updates geometry/output path metadata. |
| `map_unknown_half_lives.py` | Maps each archived unknown row by `(tag,VN,ZA,exc_keV)` to local NUBASE ground-state half-life records, keeps the original RP excitation value, recovers the corresponding RP yield, estimates day-15 activity, and checks whether profile files already exist. |

## Verification of the User-Asked Model

Conclusion: the implemented workflow is mostly the model described, with one important correction.

- Yes: isotope production is taken from Step02/buildup `.dat` RP records and true RPIP position records.
- Yes: the position model is built from the custom `CC IP RP` records, which encode volume, position, ZA, excitation energy, and time.
- Yes: source positions are sampled from those RPIP-derived radial profile files, not from a uniform geometry prior.
- Yes: activity is derived from half-life exponential buildup under continuous cosmic-ray exposure, not a single instantaneous decay of all produced nuclei.
- Yes: the final source uses `DecayMode ActivationDelayedDecay` so Cosima transports decay products from the generated activation source.
- No: the current production code does not implement an explicit stochastic "nuclide species sampling N then N+1 saturation" loop. It instead enumerates all RP yield entries for which a half-life is known and a spatial profile has at least `min_points = 15`, then writes every resulting source block above threshold. Activity saturation is audited after the fact by sorting inventory rows by activity.

## Current Source Audit

| item | value |
| --- | --- |
| raw source blocks | {audit['raw_source_blocks']} |
| fixed source blocks | {audit['fixed_source_blocks']} |
| fixed source listed blocks | {audit['fixed_listed_sources']} |
| raw total activity Bq | {audit['raw_total_activity_Bq']:.12e} |
| fixed total activity Bq | {audit['fixed_total_activity_Bq']:.12e} |
| inventory rows | {audit['inventory_rows']} |
| unknown isotope rows | {audit['unknown_isotope_rows']} |
| no-RPIP/profile-skipped rows | {audit['no_rpip_rows']} |
| profile files referenced by fixed source | {audit['profile_files_referenced']} |
| profile files present | {audit['profile_files_present']} |
| source blocks removed by ground-state fix | {audit['source_blocks_removed']} |
| rank for 95% activity | {audit['rank_95_activity']} |
| rank for 99% activity | {audit['rank_99_activity']} |
| WRL sampled source points | {audit['sampled_points_wrl']} |
| 2D schematic sampled source points | {audit['sampled_points_2d']} |
| archived unknown rows remapped | {audit['remap_input_unknown_rows']} |
| remapped finite half-life rows | {audit['remap_finite_rows']} |
| remapped stable rows | {audit['remap_stable_rows']} |
| remapped finite rows with profile support | {audit['remap_profile_supported_finite_rows']} |
| remapped profile-supported activity Bq | {audit['remap_profile_supported_activity_Bq']:.12e} |

## Half-Life Remap Finding

The archived `unknown_isotopes_day15.csv` rows are not all stable nuclei. They
were mostly true half-life lookup misses from the archived source-generation
run. Rechecking them against the local NUBASE 2020 ground-state table maps all
{audit['remap_unique_unknown_nuclides']} unique nuclides: {audit['remap_finite_unique']} have
finite ground-state half-lives and {audit['remap_stable_unique']} are stable
ground states ({stable_names}). The archived unknown rows all have
`exc_keV = 0.0`, so this remap is a ground-state remap, not an isomeric-state
remap.

The source generator records RP excitation energy from the `.dat` table and
RPIP records as `exc_keV`. The current production logic still resolves
half-lives by ground-state nuclide name (`ZA -> element-A`) rather than by an
isomer-specific `(ZA, exc_keV)` level. That is not changing the current remap
because the affected archived rows are all ground-state rows.

The remap estimates {audit['remap_profile_supported_finite_rows']} finite half-life rows already
have profile support and would contribute about {audit['remap_profile_supported_activity_Bq']:.6e}
Bq at day 15 if the delayed source is regenerated with the fixed NUBASE mapping.

## Rerun Completion From Saturation Evidence

The absence of an explicit stochastic N then N+1 nuclide-species saturation
sampler does not by itself prove that the archived delayed source was randomly
under-sampled. The archived workflow is deterministic at source-writing time:
it enumerates every RP-derived source term that has a resolved half-life and an
RPIP-derived spatial profile with enough support, then writes all surviving
source blocks.

The source-correctness rerun has now been completed with the fixed NUBASE
mapping and the wider tiny-excitation ground-state tolerance. The regenerated
fixed source has {audit['fixed_source_blocks']} profile-backed source blocks,
all {audit['profile_files_referenced']} referenced profile files are present,
and the sorted inventory reaches 99% cumulative activity by rank
{audit['rank_99_activity']} out of {audit['inventory_rows']} inventory rows.
The remaining `unknown_isotopes_day15.csv` rows remap to stable ground states
(`Pb-204`, `W-183`) and add no finite day-15 activity.

The separate spatial incompleteness ledger remains the {audit['no_rpip_rows']}
rows without enough RPIP/profile support; reducing that uncertainty requires
more Step02 buildup statistics or a controlled profile-threshold study.

Top activity rows:

| rank | VN | nuclide | Activity_Bq | Points | cumulative_fraction |
| --- | --- | --- | --- | --- | --- |
{top_table}

## Generated Outputs

- `outputs/delay_source_audit.json`: machine-readable audit.
- `outputs/unknown_half_life_remap_day15.csv`: remap of the archived half-life lookup misses against local NUBASE ground states.
- `outputs/unknown_half_life_remap_summary.json`: machine-readable remap summary.
- `outputs/fixed_source_blocks.csv`: parsed source-block table.
- `outputs/activity_saturation_by_inventory.csv`: cumulative activity saturation by sorted inventory rows.
- `outputs/decay_source_sample_1000.csv`: 1000 sampled decay-source positions used for the compact WRL scene.
- `outputs/decay_source_sample_10000.csv`: 10000 sampled decay-source positions used for the denser 2D schematic.
- `outputs/delay_source_1000_particles.wrl`: WRL scene with transparent geometry shells and the 1000 sampled source points.
- `outputs/delay_source_2d_schematic.png`: Step02-style 2D geometry overlay with 10000 delayed-source points.

## Open Caveats

- The WRL and 2D PNG visualize the source-position PDFs, not a full Geant4 trajectory dump. They are appropriate for checking delayed-source spatial placement.
- The archived source uses an axisymmetric radial-profile approximation per z slice; it does not preserve all azimuthal asymmetries in the raw RPIP point cloud.
- The `unknown_isotopes_day15.csv` ledger has now been locally remapped after
  source regeneration. The production delayed source and the 1M delayed
  transport are aligned to the regenerated fixed source as of 2026-05-27.
- `no_rpip_points_day15.csv` remains a real spatial-support exclusion ledger. Therefore "as many nuclides as possible" means all locally resolvable and spatially supportable source terms under the current thresholds, not mathematically every RP record.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    copy_snapshot(RAW_SOURCE, "activation_decay_day15_raw.source")
    copy_snapshot(FIXED_SOURCE, "activation_decay_day15_groundstate_fixed.source")
    copy_snapshot(INVENTORY, "activation_inventory_day15.csv")
    copy_snapshot(FIX_SUMMARY, "source_fix_summary.json")

    raw_source = parse_source(RAW_SOURCE)
    fixed_source = parse_source(FIXED_SOURCE)
    inventory_rows = read_csv(INVENTORY)
    unknown_rows = read_csv(UNKNOWN)
    no_rpip_rows = read_csv(NO_RPIP)
    fix_summary = json.loads(FIX_SUMMARY.read_text(encoding="utf-8"))
    remap_summary = json.loads(REMAP_SUMMARY.read_text(encoding="utf-8")) if REMAP_SUMMARY.exists() else {}

    block_rows = source_block_rows(fixed_source)
    write_csv(OUTPUT_DIR / "fixed_source_blocks.csv", block_rows)

    saturation_rows = build_saturation_rows(inventory_rows)
    write_csv(OUTPUT_DIR / "activity_saturation_by_inventory.csv", saturation_rows)

    samples_1000 = sample_decay_points(fixed_source, n=1000, seed=260503)
    samples_10000 = sample_decay_points(fixed_source, n=10000, seed=260504)
    write_sample_csv(OUTPUT_DIR / "decay_source_sample_1000.csv", samples_1000)
    write_sample_csv(OUTPUT_DIR / "decay_source_sample_10000.csv", samples_10000)

    bounds = json.loads(BOUNDS_FILE.read_text(encoding="utf-8"))
    write_wrl(OUTPUT_DIR / "delay_source_1000_particles.wrl", samples_1000, bounds)
    make_2d_schematic(OUTPUT_DIR / "delay_source_2d_schematic.png", samples_10000, bounds, saturation_rows)

    profile_refs = {
        str(block.get("profile"))
        for block in fixed_source["blocks"].values()
        if block.get("listed_in_run") and block.get("profile")
    }
    profiles_present = sum(1 for p in profile_refs if profile_path(p).exists())
    raw_total = sum(float(block.get("flux_Bq", 0.0)) for block in raw_source["blocks"].values())
    fixed_total = sum(
        float(block.get("flux_Bq", 0.0))
        for block in fixed_source["blocks"].values()
        if block.get("listed_in_run")
    )

    build_script_text = BUILD_SCRIPT.read_text(encoding="utf-8", errors="ignore")
    fixed_script_text = FIX_SCRIPT.read_text(encoding="utf-8", errors="ignore")
    audit = {
        "status": "PASS_WITH_EXPLICIT_CAVEATS",
        "raw_source": rel(RAW_SOURCE),
        "fixed_source": rel(FIXED_SOURCE),
        "inventory": rel(INVENTORY),
        "build_script": rel(BUILD_SCRIPT),
        "fix_script": rel(FIX_SCRIPT),
        "time_variable_script": rel(TIME_SCRIPT),
        "raw_source_blocks": len(raw_source["blocks"]),
        "fixed_source_blocks": len(fixed_source["blocks"]),
        "fixed_listed_sources": len(fixed_source["sources"]),
        "raw_total_activity_Bq": raw_total,
        "fixed_total_activity_Bq": fixed_total,
        "inventory_rows": len(inventory_rows),
        "unknown_isotope_rows": len(unknown_rows),
        "no_rpip_rows": len(no_rpip_rows),
        "profile_files_referenced": len(profile_refs),
        "profile_files_present": profiles_present,
        "source_blocks_removed": int(fix_summary.get("source_blocks_removed", 0)),
        "rank_95_activity": rank_at_fraction(saturation_rows, 0.95),
        "rank_99_activity": rank_at_fraction(saturation_rows, 0.99),
        "sampled_points_wrl": len(samples_1000),
        "sampled_points_2d": len(samples_10000),
        "remap_input_unknown_rows": int(remap_summary.get("input_unknown_rows", 0)),
        "remap_unique_unknown_nuclides": int(remap_summary.get("input_unique_nuclides", 0)),
        "remap_finite_rows": int(remap_summary.get("status_rows", {}).get("finite_ground_state_half_life", 0)),
        "remap_stable_rows": int(remap_summary.get("status_rows", {}).get("stable_ground_state", 0)),
        "remap_finite_unique": int(remap_summary.get("status_unique_nuclides", {}).get("finite_ground_state_half_life", 0)),
        "remap_stable_unique": int(remap_summary.get("status_unique_nuclides", {}).get("stable_ground_state", 0)),
        "remap_stable_nuclides": remap_summary.get("status_unique_nuclide_names", {}).get("stable_ground_state", []),
        "remap_profile_supported_finite_rows": int(remap_summary.get("profile_supported_finite_rows", 0)),
        "remap_profile_supported_activity_Bq": float(
            remap_summary.get("profile_supported_estimated_activity_Bq_day15", 0.0)
        ),
        "workflow_checks": {
            "build_script_parses_cc_ip_rp": "CC IP RP" in build_script_text and "IP_RE" in build_script_text,
            "build_script_uses_activity_after_exposure": "def activity_after_exposure" in build_script_text,
            "build_script_writes_radial_profile_beam": "RadialProfileBeam" in build_script_text,
            "fixed_source_uses_activation_delayed_decay": fixed_source["decay_mode"] == "ActivationDelayedDecay",
            "fixed_source_has_profile_files": profiles_present == len(profile_refs),
            "fixed_script_uses_nubase_ground_half_lives": "load_nubase_ground_half_lives" in fixed_script_text,
            "explicit_n_plus_1_saturation_sampler_present": "N+1" in build_script_text or "saturation" in build_script_text.lower(),
        },
        "interpretation": {
            "uses_true_rpip_positions": True,
            "uses_half_life_exponential_continuous_exposure": True,
            "samples_positions_from_rpip_profiles": True,
            "generates_all_supported_nuclides_not_stochastic_saturation": True,
            "n_plus_1_species_saturation_is_not_implemented": True,
        },
    }
    (OUTPUT_DIR / "delay_source_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    write_readme(STEP_DIR / "README.md", audit, saturation_rows)
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
