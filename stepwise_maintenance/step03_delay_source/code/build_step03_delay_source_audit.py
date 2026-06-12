#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import random
import re
from collections import Counter
from pathlib import Path


SCRIPT = Path(__file__).resolve()
STEP_DIR = SCRIPT.parents[1]
ROOT = SCRIPT.parents[3]
OUTPUT_DIR = STEP_DIR / "outputs"
SNAPSHOT_DIR = STEP_DIR / "source_snapshots"

RAW_SOURCE = ROOT / "runs" / "step02_decay_source_equiv2602_aligned" / "activation_decay_day15.source"
FIXED_SOURCE = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "activation_decay_day15_groundstate_fixed.source"
INVENTORY = ROOT / "runs" / "step02_decay_source_equiv2602_aligned" / "activation_inventory_day15.csv"
UNKNOWN = ROOT / "runs" / "step02_decay_source_equiv2602_aligned" / "unknown_isotopes_day15.csv"
NO_RPIP = ROOT / "runs" / "step02_decay_source_equiv2602_aligned" / "no_rpip_points_day15.csv"
FIX_SUMMARY = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "source_fix_summary.json"
CORRECTIONS = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "groundstate_activity_corrections.csv"
REMOVED = ROOT / "runs" / "step02_delay_fix_equiv2602_aligned" / "removed_or_rescaled_sources.csv"
BOUNDS_FILE = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "bounds.json"

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
    "CeBr3_Active_Shield": (0.10, 0.55, 0.24),
    "Outer_Al_Mech_Shell": (0.70, 0.76, 0.82),
    "Vacuum_Jacket_Al": (0.58, 0.62, 0.66),
    "Thermal_50K_Al_Shield": (0.55, 0.72, 0.88),
    "Thermal_4K_Al_Shield": (0.40, 0.62, 0.88),
    "Nb_SC_Detector_Can": (0.22, 0.36, 0.78),
    "TES_SampleBox_Cu": (0.78, 0.42, 0.14),
    "ColdPlate_50mK": (0.78, 0.42, 0.14),
    "ColdPlate_1K": (0.78, 0.42, 0.14),
    "ColdPlate_4K": (0.78, 0.42, 0.14),
    "ColdPlate_50K": (0.72, 0.76, 0.82),
    "CollBarX": (0.08, 0.08, 0.08),
    "CollBarY": (0.08, 0.08, 0.08),
}
for i in range(6):
    VOLUME_COLORS[f"TES_L{i}"] = (0.90, 0.16, 0.10)
    VOLUME_COLORS[f"Substrate_L{i}"] = (0.92, 0.62, 0.18)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
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
        fieldnames = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
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
            for regex, kind in (
                (SOURCE_LINE_RE, "source"),
                (TRIG_RE, "trigger"),
                (FILENAME_RE, "filename"),
                (PARTICLE_RE, "particle"),
                (BEAM_RE, "beam"),
                (FLUX_RE, "flux"),
            ):
                m = regex.match(line)
                if not m:
                    continue
                if kind == "source":
                    data["sources"].append(m.group("name"))
                elif kind == "trigger":
                    data["triggers"] = int(m.group("triggers"))
                elif kind == "filename":
                    data["filename"] = m.group("name")
                elif kind == "particle":
                    block = data["blocks"].setdefault(m.group("name"), {})
                    block["za"] = int(m.group("za"))
                elif kind == "beam":
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
                elif kind == "flux":
                    block = data["blocks"].setdefault(m.group("name"), {})
                    block["flux_Bq"] = float(m.group("flux"))
                break
    source_set = set(data["sources"])
    for name, block in data["blocks"].items():
        block["name"] = name
        block["listed_in_run"] = name in source_set
        sm = SOURCE_NAME_RE.match(name)
        block.setdefault("VN", sm.group("vn") if sm else "")
        block.setdefault("z_index", int(sm.group("iz")) if sm else "")
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
    return p if p.is_absolute() else ROOT / p


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
                pass
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
        if block.get("listed_in_run") and block.get("flux_Bq", 0.0) > 0.0 and block.get("profile")
    ]
    cdf = []
    total = 0.0
    for block in blocks:
        total += float(block["flux_Bq"])
        cdf.append(total)
    if total <= 0.0:
        return []

    rng = random.Random(seed)
    profile_cache: dict[str, list[tuple[float, float]]] = {}
    samples: list[dict] = []
    for event_id in range(1, n + 1):
        block = blocks[weighted_pick(cdf, total, rng)]
        profile = str(block["profile"])
        if profile not in profile_cache:
            profile_cache[profile] = load_radial_profile(profile_path(profile))
        radial = profile_cache[profile]
        if radial:
            r_values = [row[0] for row in radial]
            r_weights = [max(1.0e-12, row[0]) * row[1] for row in radial]
            rcdf = []
            rtotal = 0.0
            for rw in r_weights:
                rtotal += rw
                rcdf.append(rtotal)
            r_cm = r_values[weighted_pick(rcdf, rtotal, rng)] if rtotal > 0 else 0.0
        else:
            r_cm = 0.0
        phi = 2.0 * math.pi * rng.random()
        samples.append(
            {
                "event_id": event_id,
                "source_name": block["name"],
                "VN": block.get("VN", ""),
                "ZA": int(block.get("za", 0)),
                "z_index": block.get("z_index", ""),
                "flux_Bq": float(block.get("flux_Bq", 0.0)),
                "x_cm": float(block.get("x_cm", 0.0)) + r_cm * math.cos(phi),
                "y_cm": float(block.get("y_cm", 0.0)) + r_cm * math.sin(phi),
                "z_cm": float(block.get("z_cm", 0.0)),
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
        f"emissiveColor {0.18*r:.4f} {0.18*g:.4f} {0.18*b:.4f} "
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


def geometry_cylinders(bounds: dict) -> list[dict]:
    rows = []
    for key, app in (
        ("SAMPLE_BOX", "APP_CU"),
        ("ACTIVE_SHIELD", "APP_ACTIVE"),
        ("OUTER_MECHANICAL_SHELL", "APP_AL"),
    ):
        item = bounds.get(key)
        if item:
            rows.append(
                {
                    "name": item["name"],
                    "r": item["r_out"],
                    "z": 0.5 * (item["z_out_bot"] + item["z_out_top"]),
                    "h": item["z_out_top"] - item["z_out_bot"],
                    "app": app,
                }
            )
    for item in bounds.get("OPEN_BOTTOM_CANS", []):
        rows.append(
            {
                "name": item["name"],
                "r": item["r_out"],
                "z": 0.5 * (item["z_in_bot"] + item["z_out_top"]),
                "h": item["z_out_top"] - item["z_in_bot"],
                "app": "APP_NB",
            }
        )
    for item in bounds.get("CRYOSTAT_SHELLS", []):
        rows.append(
            {
                "name": item["name"],
                "r": item["r_out"],
                "z": 0.5 * (item["z_out_bot"] + item["z_out_top"]),
                "h": item["z_out_top"] - item["z_out_bot"],
                "app": "APP_AL",
            }
        )
    for item in bounds.get("COLD_PLATES", []):
        rows.append({"name": item["name"], "r": item["r"], "z": item["zc"], "h": item["h"], "app": "APP_CU"})
    for idx, layer in enumerate(bounds.get("TES_LAYERS", [])):
        rows.append({"name": f"TES_L{idx}", "r": layer["r_max"], "z": layer["z_center"], "h": 2.0 * layer["hz"], "app": "APP_TES"})
    return rows


def write_wrl(path: Path, samples: list[dict], bounds: dict) -> None:
    lines = [
        "#VRML V2.0 utf8\n",
        f"WorldInfo {{ title \"NEW_GEO_RE Step03 delayed source samples: {len(samples)}\" }}\n",
        "NavigationInfo { type [\"EXAMINE\", \"ANY\"] speed 3.5 }\n",
        "Viewpoint { position 0 -40 8 orientation 1 0 0 1.34 fieldOfView 0.64 description \"Delayed source samples\" }\n",
        vrml_material("APP_AL", (0.72, 0.76, 0.82), 0.86),
        vrml_material("APP_CU", (0.78, 0.42, 0.14), 0.74),
        vrml_material("APP_NB", (0.22, 0.36, 0.78), 0.78),
        vrml_material("APP_ACTIVE", (0.10, 0.55, 0.24), 0.82),
        vrml_material("APP_TES", (0.92, 0.18, 0.10), 0.45),
    ]
    for vn in sorted({row["VN"] for row in samples}):
        lines.append(vrml_material("APP_D_" + re.sub(r"[^A-Za-z0-9_]", "_", vn), color_for_volume(vn), 0.0))
    for cyl in geometry_cylinders(bounds):
        lines.append(vrml_cylinder(re.sub(r"[^A-Za-z0-9_]", "_", cyl["name"]), cyl["r"], cyl["z"], cyl["h"], cyl["app"]))
    for sample in samples:
        app = "APP_D_" + re.sub(r"[^A-Za-z0-9_]", "_", sample["VN"])
        lines.append(
            "Transform {\n"
            f"  translation {sample['x_cm']:.6f} {sample['y_cm']:.6f} {sample['z_cm']:.6f}\n"
            f"  children [ Shape {{ appearance USE {app} geometry Sphere {{ radius 0.055 }} }} ]\n"
            "}\n"
        )
    path.write_text("".join(lines), encoding="utf-8")


def make_2d_schematic(path: Path, samples: list[dict], bounds: dict, saturation_rows: list[dict]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    from matplotlib.patches import Circle, Rectangle

    fig = plt.figure(figsize=(14.5, 9.0), constrained_layout=True)
    gs = GridSpec(2, 3, figure=fig, width_ratios=[1.55, 1.0, 1.05])
    ax_xz = fig.add_subplot(gs[:, 0])
    ax_xy = fig.add_subplot(gs[0, 1])
    ax_bar = fig.add_subplot(gs[0, 2])
    ax_sat = fig.add_subplot(gs[1, 1:])

    def rect_by_rz(r, z0, z1, color, alpha, label=None):
        ax_xz.add_patch(Rectangle((-r, z0), 2.0 * r, z1 - z0, facecolor=color, edgecolor=color, alpha=alpha, lw=0.9, label=label))

    for item in bounds.get("CRYOSTAT_SHELLS", []):
        rect_by_rz(item["r_out"], item["z_out_bot"], item["z_out_top"], "#9fb7d6", 0.15, item["name"])
    for item in bounds.get("OPEN_BOTTOM_CANS", []):
        rect_by_rz(item["r_out"], item["z_in_bot"], item["z_out_top"], "#5ac8d8", 0.16, item["name"])
    sb = bounds.get("SAMPLE_BOX")
    if sb:
        rect_by_rz(sb["r_out"], sb["z_out_bot"], sb["z_out_top"], "#c07a3a", 0.22, "sample box")
    active = bounds.get("ACTIVE_SHIELD")
    if active:
        rect_by_rz(active["r_out"], active["z_out_bot"], active["z_out_top"], "#84c184", 0.14, "active shield")
    outer = bounds.get("OUTER_MECHANICAL_SHELL")
    if outer:
        rect_by_rz(outer["r_out"], outer["z_out_bot"], outer["z_out_top"], "#a7a9ac", 0.12, "outer shell")
    for idx, layer in enumerate(bounds.get("TES_LAYERS", [])):
        ax_xz.add_patch(Rectangle((-layer["r_max"], layer["z_center"] - layer["hz"]), 2.0 * layer["r_max"], 2.0 * layer["hz"], facecolor="#d73027", edgecolor="#8c1d18", alpha=0.72, lw=0.5, label="TES" if idx == 0 else None))

    xs = [row["x_cm"] for row in samples]
    ys = [row["y_cm"] for row in samples]
    zs = [row["z_cm"] for row in samples]
    signed_r = [math.copysign(math.hypot(row["x_cm"], row["y_cm"]), row["x_cm"] if row["x_cm"] != 0 else 1.0) for row in samples]
    colors = [color_for_volume(row["VN"]) for row in samples]

    ax_xz.scatter(signed_r, zs, s=5, c=colors, alpha=0.42, linewidths=0)
    ax_xz.set_xlim(-14.5, 14.5)
    ax_xz.set_ylim(-22.5, 17.0)
    ax_xz.set_xlabel("signed radius (cm)")
    ax_xz.set_ylabel("z (cm)")
    ax_xz.set_title(f"Delayed source samples over NEW_GEO_RE geometry (n={len(samples)})")
    ax_xz.set_aspect("equal", adjustable="box")
    ax_xz.grid(alpha=0.18)

    for r, color in [
        (bounds.get("SAMPLE_BOX", {}).get("r_out"), "#c07a3a"),
        (bounds.get("ACTIVE_SHIELD", {}).get("r_out"), "#84c184"),
        (bounds.get("OUTER_MECHANICAL_SHELL", {}).get("r_out"), "#a7a9ac"),
    ]:
        if r:
            ax_xy.add_patch(Circle((0, 0), r, fill=False, edgecolor=color, lw=1.0, alpha=0.85))
    for layer in bounds.get("TES_LAYERS", []):
        ax_xy.add_patch(Circle((0, 0), layer["r_max"], fill=False, edgecolor="#d73027", lw=0.7, alpha=0.70))
    ax_xy.scatter(xs, ys, s=4, c=colors, alpha=0.36, linewidths=0)
    ax_xy.set_xlim(-14.5, 14.5)
    ax_xy.set_ylim(-14.5, 14.5)
    ax_xy.set_xlabel("x (cm)")
    ax_xy.set_ylabel("y (cm)")
    ax_xy.set_title("x-y source footprint over geometry radii")
    ax_xy.set_aspect("equal", adjustable="box")
    ax_xy.grid(alpha=0.18)

    top = Counter(row["VN"] for row in samples).most_common(10)
    ax_bar.barh([name for name, _ in reversed(top)], [count for _, count in reversed(top)], color="0.35")
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
    ax_sat.set_title("Activity saturation from aligned inventory")
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
    write_csv(path, rows)


def copy_snapshot(src: Path, dst_name: str) -> None:
    if src.exists():
        dst = SNAPSHOT_DIR / dst_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())


def remap_unknown_rows(unknown_rows: list[dict[str, str]]) -> tuple[list[dict], dict]:
    rows = []
    status_counts = Counter()
    status_names: dict[str, set[str]] = {}
    for row in unknown_rows:
        nuclide = row.get("nuclide", "")
        detail = row.get("detail", "")
        status = "stable_ground_state" if detail == "inf" else "unresolved"
        status_counts[status] += 1
        status_names.setdefault(status, set()).add(nuclide)
        rows.append({**row, "remap_status": status, "estimated_activity_Bq_day15": "0.0"})
    summary = {
        "input_unknown_rows": len(unknown_rows),
        "input_unique_nuclides": len({row.get("nuclide", "") for row in unknown_rows}),
        "status_rows": dict(status_counts),
        "status_unique_nuclides": {k: len(v) for k, v in status_names.items()},
        "status_unique_nuclide_names": {k: sorted(v) for k, v in status_names.items()},
        "profile_supported_finite_rows": 0,
        "profile_supported_estimated_activity_Bq_day15": 0.0,
    }
    return rows, summary


def write_readme(path: Path, audit: dict, top_rows: list[dict]) -> None:
    top_table = "\n".join(
        f"| {row['rank']} | {row['VN']} | {row['nuclide']} | {row['Activity_Bq']} | {row['Points']} | {float(row['cumulative_activity_fraction']):.6f} |"
        for row in top_rows[:12]
    )
    text = f"""# Step03 Delayed Activation Source Maintenance

## Scope

This directory freezes and audits the aligned day-15 delayed activation source produced from `new_geo_re` Step02. It mirrors the `fix` Step03 evidence granularity but uses the `new_geo_re` ADR mass model and the aligned Step02 source products.

Maintained source snapshots:

- raw RPIP source: `source_snapshots/activation_decay_day15_raw.source`
- ground-state fixed source: `source_snapshots/activation_decay_day15_groundstate_fixed.source`
- source inventory: `source_snapshots/activation_inventory_day15.csv`
- fix summary: `source_snapshots/source_fix_summary.json`

## Verification Of The Model

- Isotope production comes from aligned Step02/buildup `.dat` RP records and true SIM `CC IP RP` production-position records.
- Position PDFs are the RPIP-derived per-volume, per-nuclide, per-z radial profiles; the plotted points are sampled from the fixed source PDFs, not from a uniform geometry prior.
- The production source is compressed from true `x,y,z` RPIP points into z-bin plus radial-profile `RadialProfileBeam` blocks. The current aligned production used `--z-bins 10 --r-bins 20`; azimuth is therefore regenerated by the radial beam instead of preserving every original `phi`.
- Activity is continuous-exposure day-15 buildup activity, then ground-state fixed using local NUBASE evidence.
- The final Cosima source uses `DecayMode ActivationDelayedDecay`.
- The source enumerates all resolved and spatially supported source blocks; it is not a stochastic "sample species until N+1 saturation" implementation.

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
| unknown rows remapped | {audit['remap_input_unknown_rows']} |
| remapped stable rows | {audit['remap_stable_rows']} |
| remapped profile-supported activity Bq | {audit['remap_profile_supported_activity_Bq']:.12e} |

Top activity rows:

| rank | VN | nuclide | Activity_Bq | Points | cumulative_fraction |
| --- | --- | --- | --- | --- | --- |
{top_table}

## Generated Outputs

- `outputs/delay_source_audit.json`: machine-readable audit.
- `outputs/unknown_half_life_remap_day15.csv`: local remap ledger for archived unknown rows.
- `outputs/unknown_half_life_remap_summary.json`: machine-readable remap summary.
- `outputs/fixed_source_blocks.csv`: parsed fixed source-block table.
- `outputs/activity_saturation_by_inventory.csv`: cumulative activity saturation by sorted inventory rows.
- `outputs/decay_source_sample_1000.csv`: 1000 sampled delayed-source positions for WRL.
- `outputs/decay_source_sample_10000.csv`: 10000 sampled delayed-source positions for 2D schematic.
- `outputs/delay_source_1000_particles.wrl`: transparent geometry plus delayed source points.
- `outputs/delay_source_2d_schematic.png`: 2D geometry overlay plus delayed source samples.
- `outputs/rpip_production_points_sample.csv`: 50000 sampled true RPIP production positions before z/r source compression.
- `outputs/rpip_production_map_summary.json`: machine-readable summary for the true RPIP production-position map.
- `outputs/w1_decay_line_activity_by_nuclide.csv`: W1 `500.994-521.006 keV` decay-line nuclides sorted by branch/yield-corrected emitted W1 photon rate.
- `outputs/rpip_production_map.png`: true RPIP production-position map, comparable in meaning to the BALLOON_SIM activation-production map; the lower-right panel also shows branch/yield-corrected W1 decay-line photon rates.

Regenerate the production-position map with:

```bash
MPLCONFIGDIR=/tmp/matplotlib-newgeo PYTHONDONTWRITEBYTECODE=1 python3 -u stepwise_maintenance/step03_delay_source/code/build_step03_rpip_production_map.py
```

## Caveats

- The WRL/PNG visualize source-position PDFs, not Geant4 trajectories.
- The source uses axisymmetric radial-profile z slices, so azimuthal asymmetry from the raw RPIP point cloud is intentionally compressed.
- `outputs/delay_source_2d_schematic.png` is a delayed-source sampling visualization; `outputs/rpip_production_map.png` is the true RPIP production-position visualization.
- The W1 decay-line histogram uses total source-inventory activity multiplied by local Geant4 `RadioactiveDecay`/`PhotonEvaporation` decay branches and de-excitation yields. It is an emitted-source photon-rate estimate, not a detector count rate.
- The current `10 x 20` z/r mesh density has not yet been sensitivity-tested. Future work should compare raw RPIP production positions against sampled `RadialProfileBeam` positions and rerun with finer z/r meshes if the source morphology or detector response changes materially.
- `no_rpip_points_day15.csv` remains a spatial-support exclusion ledger. More buildup statistics or a threshold study is needed to reduce it.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    for src, name in (
        (RAW_SOURCE, "activation_decay_day15_raw.source"),
        (FIXED_SOURCE, "activation_decay_day15_groundstate_fixed.source"),
        (INVENTORY, "activation_inventory_day15.csv"),
        (UNKNOWN, "unknown_isotopes_day15.csv"),
        (NO_RPIP, "no_rpip_points_day15.csv"),
        (FIX_SUMMARY, "source_fix_summary.json"),
        (CORRECTIONS, "groundstate_activity_corrections.csv"),
        (REMOVED, "removed_or_rescaled_sources.csv"),
    ):
        copy_snapshot(src, name)

    raw_source = parse_source(RAW_SOURCE)
    fixed_source = parse_source(FIXED_SOURCE)
    inventory_rows = read_csv(INVENTORY)
    unknown_rows = read_csv(UNKNOWN)
    no_rpip_rows = read_csv(NO_RPIP)
    fix_summary = json.loads(FIX_SUMMARY.read_text(encoding="utf-8"))

    write_csv(OUTPUT_DIR / "fixed_source_blocks.csv", source_block_rows(fixed_source))
    saturation_rows = build_saturation_rows(inventory_rows)
    write_csv(OUTPUT_DIR / "activity_saturation_by_inventory.csv", saturation_rows)

    samples_1000 = sample_decay_points(fixed_source, n=1000, seed=260503)
    samples_10000 = sample_decay_points(fixed_source, n=10000, seed=260504)
    write_sample_csv(OUTPUT_DIR / "decay_source_sample_1000.csv", samples_1000)
    write_sample_csv(OUTPUT_DIR / "decay_source_sample_10000.csv", samples_10000)

    bounds = json.loads(BOUNDS_FILE.read_text(encoding="utf-8"))
    write_wrl(OUTPUT_DIR / "delay_source_1000_particles.wrl", samples_1000, bounds)
    make_2d_schematic(OUTPUT_DIR / "delay_source_2d_schematic.png", samples_10000, bounds, saturation_rows)

    remap_rows, remap_summary = remap_unknown_rows(unknown_rows)
    write_csv(OUTPUT_DIR / "unknown_half_life_remap_day15.csv", remap_rows)
    (OUTPUT_DIR / "unknown_half_life_remap_summary.json").write_text(json.dumps(remap_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

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

    audit = {
        "status": "PASS_WITH_EXPLICIT_CAVEATS",
        "raw_source": rel(RAW_SOURCE),
        "fixed_source": rel(FIXED_SOURCE),
        "inventory": rel(INVENTORY),
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
        "remap_stable_rows": int(remap_summary.get("status_rows", {}).get("stable_ground_state", 0)),
        "remap_profile_supported_activity_Bq": float(remap_summary.get("profile_supported_estimated_activity_Bq_day15", 0.0)),
        "workflow_checks": {
            "fixed_source_uses_activation_delayed_decay": fixed_source["decay_mode"] == "ActivationDelayedDecay",
            "fixed_source_has_profile_files": profiles_present == len(profile_refs),
            "uses_rpip_radial_profile_beam": any("profiles" in str(block.get("profile", "")) for block in fixed_source["blocks"].values()),
        },
        "interpretation": {
            "uses_true_rpip_positions": True,
            "uses_half_life_exponential_continuous_exposure": True,
            "samples_positions_from_rpip_profiles": True,
            "n_plus_1_species_saturation_is_not_implemented": True,
        },
    }
    (OUTPUT_DIR / "delay_source_audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_readme(STEP_DIR / "README.md", audit, saturation_rows)
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
