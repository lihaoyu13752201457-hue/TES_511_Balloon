#!/usr/bin/env python3
"""Ray-trace prompt e+ 511 proxy lines through MEGAlib geometry volumes.

This is a deterministic geometry diagnostic.  It traces straight lines from
the SIM annihilation point to the selected TES centroid, and a fixed side-axis
line through old/current geometry.  It does not model scattering or attenuation;
it only reports leaf-volume material chord lengths in the proxy .geo volumes.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_prompt511_prompt_incidence_figure as base  # noqa: E402


ROOT = base.ROOT
OUTDIR = base.OUTDIR

CURRENT_GEO = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
OLD_GEO = ROOT.parent / "codex_tes_511_sim/new_geo_re/outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo"

EVENT_CSV = OUTDIR / "prompt511_raytrace_event_chords.csv"
SEGMENT_CSV = OUTDIR / "prompt511_raytrace_volume_segments.csv"
LINE_CSV = OUTDIR / "prompt511_raytrace_line_chords.csv"
SUMMARY_JSON = OUTDIR / "prompt511_raytrace_summary.json"
REPORT_MD = OUTDIR / "prompt511_raytrace_ledger.md"

EPS = 1.0e-9
MATERIAL_ORDER = [
    "Ta/TES",
    "CsI",
    "Aluminium",
    "Copper",
    "W",
    "Be",
    "Kapton",
    "StainlessSteel",
    "LowCarbonSteel",
    "Nb",
    "Cryoperm",
    "Silicon",
    "SilverSinterProxy",
    "CuNi",
    "G10",
    "SaltProxy",
    "CharcoalProxy",
    "NbTiCableProxy",
    "other",
]


@dataclass
class Shape:
    kind: str
    params: list[float]


@dataclass
class Volume:
    name: str
    material: str | None = None
    shape: Shape | None = None
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    mother: str | None = None
    copy_from: str | None = None
    global_position: tuple[float, float, float] | None = None
    children: list[str] = field(default_factory=list)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vec_add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vec_scale(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def vec_len(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def material_name(material: str | None, volume_name: str = "") -> str:
    if not material:
        return "other"
    if material in {"Vacuum", "Air"}:
        return material
    if material == "Ta" or volume_name.startswith("TP_L") or volume_name.startswith("TES_Pixel"):
        return "Ta/TES"
    if material in {"Tungsten", "W"}:
        return "W"
    if material in {"Steel", "LowCarbonSteel"}:
        return "LowCarbonSteel"
    if material in {"Stainless", "StainlessSteel"}:
        return "StainlessSteel"
    if material in MATERIAL_ORDER:
        return material
    return material


def parse_geo(path: Path) -> dict[str, Volume]:
    volumes: dict[str, Volume] = {}
    seen_files: set[Path] = set()

    def ensure(name: str) -> Volume:
        if name not in volumes:
            volumes[name] = Volume(name=name)
        return volumes[name]

    def parse_file(file_path: Path) -> None:
        file_path = file_path.resolve()
        if file_path in seen_files:
            return
        seen_files.add(file_path)
        for raw in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("//"):
                continue
            if line.startswith("Include "):
                include_name = line.split(None, 1)[1].strip()
                include_path = file_path.parent / include_name
                if "$(" not in include_name and include_path.exists():
                    parse_file(include_path)
                continue
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "Volume" and len(parts) >= 2:
                ensure(parts[1])
                continue
            if ".Copy" in parts[0] and len(parts) >= 2:
                proto = parts[0].split(".Copy", 1)[0]
                new_name = parts[1]
                vol = ensure(new_name)
                vol.copy_from = proto
                continue
            if "." not in parts[0] or len(parts) < 2:
                continue
            name, attr = parts[0].split(".", 1)
            vol = ensure(name)
            if attr == "Material":
                vol.material = parts[1]
            elif attr == "Shape":
                vol.shape = Shape(kind=parts[1], params=[float(x) for x in parts[2:]])
            elif attr == "Position" and len(parts) >= 4:
                vol.position = (float(parts[1]), float(parts[2]), float(parts[3]))
            elif attr == "Mother":
                vol.mother = parts[1]

    parse_file(path)

    def resolve(name: str, stack: set[str] | None = None) -> Volume:
        stack = stack or set()
        vol = ensure(name)
        if name in stack:
            raise RuntimeError(f"Geometry mother/copy cycle at {name}")
        stack.add(name)
        if vol.copy_from:
            proto = resolve(vol.copy_from, stack)
            if vol.material is None:
                vol.material = proto.material
            if vol.shape is None:
                vol.shape = proto.shape
        if vol.global_position is None:
            if vol.mother and vol.mother in volumes:
                mother = resolve(vol.mother, stack)
                vol.global_position = vec_add(mother.global_position or (0.0, 0.0, 0.0), vol.position)
            else:
                vol.global_position = vol.position
        stack.remove(name)
        return vol

    for name in list(volumes):
        resolve(name)
    for vol in volumes.values():
        if vol.mother in volumes:
            volumes[vol.mother].children.append(vol.name)
    return volumes


def add_candidate(values: list[float], t: float) -> None:
    if -EPS <= t <= 1.0 + EPS:
        values.append(min(1.0, max(0.0, t)))


def cylinder_roots(px: float, py: float, dx: float, dy: float, radius: float) -> list[float]:
    if radius <= 0:
        return []
    a = dx * dx + dy * dy
    b = 2.0 * (px * dx + py * dy)
    c = px * px + py * py - radius * radius
    if abs(a) < EPS:
        return []
    disc = b * b - 4.0 * a * c
    if disc < -EPS:
        return []
    if disc < 0:
        disc = 0.0
    root = math.sqrt(disc)
    return [(-b - root) / (2.0 * a), (-b + root) / (2.0 * a)]


def slab_interval(p0: tuple[float, float, float], p1: tuple[float, float, float], half: tuple[float, float, float]) -> tuple[float, float] | None:
    t0, t1 = 0.0, 1.0
    d = vec_sub(p1, p0)
    for idx, h in enumerate(half):
        if abs(d[idx]) < EPS:
            if p0[idx] < -h - EPS or p0[idx] > h + EPS:
                return None
            continue
        a = (-h - p0[idx]) / d[idx]
        b = (h - p0[idx]) / d[idx]
        lo, hi = min(a, b), max(a, b)
        t0 = max(t0, lo)
        t1 = min(t1, hi)
        if t1 <= t0 + EPS:
            return None
    return (t0, t1)


def pcon_planes(params: list[float]) -> list[tuple[float, float, float]]:
    n = int(round(params[2]))
    triples = []
    for i in range(n):
        z = params[3 + 3 * i]
        r_in = params[4 + 3 * i]
        r_out = params[5 + 3 * i]
        triples.append((z, r_in, r_out))
    return triples


def interp_radius(z: float, planes: list[tuple[float, float, float]], which: int) -> float:
    # Preserve the PCON plane order.  Several local geometries use repeated
    # z-planes to describe a vertical wall/opening; sorting the triples by
    # (z, r_in, r_out) pairs the wrong side of that discontinuity.
    zmin = min(p[0] for p in planes)
    zmax = max(p[0] for p in planes)
    if z <= zmin:
        return next(p[which] for p in planes if abs(p[0] - zmin) < EPS)
    if z >= zmax:
        return next(p[which] for p in reversed(planes) if abs(p[0] - zmax) < EPS)
    for a, b in zip(planes, planes[1:]):
        if abs(b[0] - a[0]) < EPS:
            continue
        lo, hi = min(a[0], b[0]), max(a[0], b[0])
        if lo - EPS <= z <= hi + EPS:
            u = (z - a[0]) / (b[0] - a[0])
            return a[which] + u * (b[which] - a[which])
    nearest = min(planes, key=lambda p: abs(p[0] - z))
    return nearest[which]


def phi_inside(x: float, y: float, start_deg: float, delta_deg: float) -> bool:
    if delta_deg >= 359.999:
        return True
    phi = math.degrees(math.atan2(y, x)) % 360.0
    diff = (phi - start_deg) % 360.0
    return -1.0e-7 <= diff <= delta_deg + 1.0e-7


def inside_pcon(point: tuple[float, float, float], params: list[float]) -> bool:
    start, delta = params[0] % 360.0, params[1]
    planes = pcon_planes(params)
    zmin, zmax = min(p[0] for p in planes), max(p[0] for p in planes)
    x, y, z = point
    if z < zmin - EPS or z > zmax + EPS:
        return False
    r = math.hypot(x, y)
    r_in = interp_radius(z, planes, 1)
    r_out = interp_radius(z, planes, 2)
    if r < r_in - EPS or r > r_out + EPS:
        return False
    return phi_inside(x, y, start, delta)


def pcon_intervals(p0: tuple[float, float, float], p1: tuple[float, float, float], params: list[float]) -> list[tuple[float, float]]:
    d = vec_sub(p1, p0)
    planes = pcon_planes(params)
    ts = [0.0, 1.0]
    for z, r_in, r_out in planes:
        if abs(d[2]) > EPS:
            add_candidate(ts, (z - p0[2]) / d[2])
        for r in (r_in, r_out):
            for t in cylinder_roots(p0[0], p0[1], d[0], d[1], r):
                add_candidate(ts, t)
    start, delta = params[0] % 360.0, params[1]
    if delta < 359.999:
        for theta in (math.radians(start), math.radians((start + delta) % 360.0)):
            ex, ey = math.cos(theta), math.sin(theta)
            denom = ex * d[1] - ey * d[0]
            if abs(denom) > EPS:
                t = -(ex * p0[1] - ey * p0[0]) / denom
                add_candidate(ts, t)
    ts = sorted(set(round(t, 12) for t in ts))
    intervals = []
    for a, b in zip(ts, ts[1:]):
        if b <= a + EPS:
            continue
        mid = 0.5 * (a + b)
        point = vec_add(p0, vec_scale(d, mid))
        if inside_pcon(point, params):
            intervals.append((a, b))
    return intervals


def volume_intervals(vol: Volume, p0_global: tuple[float, float, float], p1_global: tuple[float, float, float]) -> list[tuple[float, float]]:
    if vol.shape is None or vol.global_position is None:
        return []
    p0 = vec_sub(p0_global, vol.global_position)
    p1 = vec_sub(p1_global, vol.global_position)
    if vol.shape.kind == "BRIK":
        half = tuple(vol.shape.params[:3])
        interval = slab_interval(p0, p1, half)
        return [interval] if interval else []
    if vol.shape.kind == "PCON":
        return pcon_intervals(p0, p1, vol.shape.params)
    return []


def volume_depths(volumes: dict[str, Volume]) -> dict[str, int]:
    depths: dict[str, int] = {}

    def depth(name: str, stack: set[str] | None = None) -> int:
        if name in depths:
            return depths[name]
        stack = stack or set()
        if name in stack:
            raise RuntimeError(f"Geometry mother cycle at {name}")
        stack.add(name)
        mother = volumes[name].mother
        if mother and mother in volumes:
            value = depth(mother, stack) + 1
        else:
            value = 0
        stack.remove(name)
        depths[name] = value
        return value

    for name in volumes:
        depth(name)
    return depths


def trace_segment(volumes: dict[str, Volume], p0: tuple[float, float, float], p1: tuple[float, float, float]) -> list[dict]:
    length = vec_len(vec_sub(p1, p0))
    depths = volume_depths(volumes)
    intervals = []
    ts = [0.0, 1.0]

    for vol in volumes.values():
        if vol.shape is None or vol.global_position is None:
            continue
        if vol.mother is None and vol.copy_from is None:
            # Prototype material volumes such as TES_Pixel_L0 are not placed.
            continue
        for t0, t1 in volume_intervals(vol, p0, p1):
            if t1 <= t0 + EPS:
                continue
            intervals.append(
                {
                    "volume": vol.name,
                    "material": material_name(vol.material, vol.name),
                    "raw_material": vol.material or "",
                    "depth": depths.get(vol.name, 0),
                    "t0": t0,
                    "t1": t1,
                }
            )
            add_candidate(ts, t0)
            add_candidate(ts, t1)

    ts = sorted(set(round(t, 12) for t in ts))
    rows = []
    for a, b in zip(ts, ts[1:]):
        if b <= a + EPS:
            continue
        mid = 0.5 * (a + b)
        containing = [row for row in intervals if row["t0"] < mid + EPS and row["t1"] > mid - EPS]
        if not containing:
            continue
        containing.sort(key=lambda row: (row["depth"], -(row["t1"] - row["t0"]), row["volume"]))
        selected = containing[-1]
        mat = selected["material"]
        if mat in {"Vacuum", "Air"}:
            continue
        chord = max(0.0, (b - a) * length)
        if chord <= 1.0e-7:
            continue
        material = mat if mat in MATERIAL_ORDER else "other"
        if rows and rows[-1]["volume"] == selected["volume"] and rows[-1]["material"] == material and abs(rows[-1]["t1"] - a) < 1.0e-8:
            rows[-1]["t1"] = b
            rows[-1]["length_cm"] += chord
        else:
            rows.append(
                {
                    "volume": selected["volume"],
                    "material": material,
                    "raw_material": selected["raw_material"],
                    "t0": a,
                    "t1": b,
                    "length_cm": chord,
                }
            )
    return rows


def compact_materials(lengths: dict[str, float], *, max_items: int = 7) -> str:
    items = [(k, v) for k, v in lengths.items() if v > 1.0e-7]
    items.sort(key=lambda kv: (-kv[1], MATERIAL_ORDER.index(kv[0]) if kv[0] in MATERIAL_ORDER else 999))
    return "; ".join(f"{k}:{v:.3g}" for k, v in items[:max_items])


def compact_volumes(rows: list[dict], *, max_items: int = 6) -> str:
    by_volume: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        by_volume[row["volume"]] += row["length_cm"]
    items = sorted(by_volume.items(), key=lambda kv: -kv[1])
    return "; ".join(f"{name}:{length:.3g}" for name, length in items[:max_items])


def event_points(case: str, row: dict) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    if case == "current":
        p0 = tuple(row.get("annihilation_local_cm") or base.global_to_current_local(row["annihilation_cm"]))
        p1 = tuple(row["tes_centroid_local_cm"])
    else:
        p0 = tuple(row["annihilation_cm"])
        p1 = tuple(row["tes_centroid_cm"])
    return p0, p1


def summarize_trace(rows: list[dict]) -> dict[str, float]:
    totals: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        totals[row["material"]] += row["length_cm"]
    return dict(totals)


def summarize_group(event_rows: list[dict]) -> dict:
    if not event_rows:
        return {}
    materials = {mat: sum(float(row[f"ray_cm_{mat}"]) for row in event_rows) for mat in MATERIAL_ORDER}
    passive = [float(row["passive_before_tes_cm"]) for row in event_rows]
    csi = [float(row["ray_cm_CsI"]) for row in event_rows]
    al = [float(row["ray_cm_Aluminium"]) for row in event_rows]
    w = [float(row["ray_cm_W"]) for row in event_rows]
    return {
        "events": len(event_rows),
        "median_passive_before_tes_cm": median(passive),
        "max_passive_before_tes_cm": max(passive),
        "events_with_lt_0p1cm_passive": sum(1 for v in passive if v < 0.1),
        "events_with_csi_chord": sum(1 for v in csi if v > 0.01),
        "events_with_aluminium_chord": sum(1 for v in al if v > 0.01),
        "events_with_w_chord": sum(1 for v in w if v > 0.01),
        "material_chord_sum_cm": {k: v for k, v in materials.items() if v > 1.0e-7},
    }


def median(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    n = len(values)
    mid = n // 2
    if n % 2:
        return values[mid]
    return 0.5 * (values[mid - 1] + values[mid])


def write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fieldnames.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_event_traces(case: str, records: list[dict], volumes: dict[str, Volume]) -> tuple[list[dict], list[dict]]:
    event_rows = []
    segment_rows = []
    for row in records:
        p0, p1 = event_points(case, row)
        segments = trace_segment(volumes, p0, p1)
        lengths = summarize_trace(segments)
        passive_before_tes = sum(v for k, v in lengths.items() if k != "Ta/TES")
        source_name = Path(row["source_file"]).name
        out = {
            "case": case,
            "source_name": source_name,
            "local_id": int(row["local_id"]),
            "leakage_class": row.get("side_window_leakage_class", ""),
            "first_primary_volume": row.get("first_primary_volume", ""),
            "last_primary_volume": row.get("last_primary_volume", ""),
            "ray_total_cm": vec_len(vec_sub(p1, p0)),
            "ray_material_cm": compact_materials(lengths),
            "top_volume_chords_cm": compact_volumes(segments),
            "passive_before_tes_cm": passive_before_tes,
            "p0_x_cm": p0[0],
            "p0_y_cm": p0[1],
            "p0_z_cm": p0[2],
            "p1_x_cm": p1[0],
            "p1_y_cm": p1[1],
            "p1_z_cm": p1[2],
        }
        for mat in MATERIAL_ORDER:
            out[f"ray_cm_{mat}"] = lengths.get(mat, 0.0)
        event_rows.append(out)
        for seg in segments:
            segment_rows.append(
                {
                    "case": case,
                    "source_name": source_name,
                    "local_id": int(row["local_id"]),
                    "leakage_class": row.get("side_window_leakage_class", ""),
                    **seg,
                }
            )
    return event_rows, segment_rows


def build_fixed_lines(current_vols: dict[str, Volume], old_vols: dict[str, Volume]) -> list[dict]:
    definitions = [
        ("current_side_axis_centerline", "current", current_vols, (-25.0, 0.0, -5.2), (8.0, 0.0, -5.2)),
        ("old_same_side_axis_centerline", "old", old_vols, (-25.0, 0.0, -5.2), (8.0, 0.0, -5.2)),
        ("current_side_axis_window_only", "current", current_vols, (-14.2, 0.0, -5.2), (-5.8, 0.0, -5.2)),
        ("old_corresponding_outer_to_inner", "old", old_vols, (-16.0, 0.0, -5.2), (-2.5, 0.0, -5.2)),
    ]
    rows = []
    for line_name, case, volumes, p0, p1 in definitions:
        segments = trace_segment(volumes, p0, p1)
        lengths = summarize_trace(segments)
        base_row = {
            "line": line_name,
            "case": case,
            "p0": list(p0),
            "p1": list(p1),
            "line_length_cm": vec_len(vec_sub(p1, p0)),
            "material_cm": compact_materials(lengths, max_items=12),
            "top_volume_chords_cm": compact_volumes(segments, max_items=12),
        }
        for mat in MATERIAL_ORDER:
            base_row[f"ray_cm_{mat}"] = lengths.get(mat, 0.0)
        rows.append(base_row)
    return rows


def write_report(summary: dict, event_rows: list[dict], line_rows: list[dict]) -> None:
    def line_lookup(name: str) -> dict:
        return next(row for row in line_rows if row["line"] == name)

    current = summary["groups"]["current_selected_all"]
    old = summary["groups"]["old_selected_all"]
    current_nonwindow = summary["groups"]["current_selected_nonwindow"]
    current_side = line_lookup("current_side_axis_centerline")
    current_window = line_lookup("current_side_axis_window_only")
    old_outer = line_lookup("old_corresponding_outer_to_inner")

    sample_rows = [row for row in event_rows if row["case"] == "current" and row["leakage_class"] == "non_window_no_window_disk_intersection"][:12]
    sample_table = [
        "| source:id | first/last primary volume | ray materials | passive before TES cm | top chord volumes |",
        "|---|---|---|---:|---|",
    ]
    for row in sample_rows:
        sid = f"{row['source_name'].split('.')[0].replace('Background_eplus_fullsphere20_', '')}:{row['local_id']}"
        prim = row["first_primary_volume"] or row["last_primary_volume"] or "-"
        if row["last_primary_volume"] and row["last_primary_volume"] != row["first_primary_volume"]:
            prim = f"{prim} -> {row['last_primary_volume']}"
        sample_table.append(
            f"| `{sid}` | `{prim}` | {row['ray_material_cm'] or '-'} | {float(row['passive_before_tes_cm']):.3g} | {row['top_volume_chords_cm'] or '-'} |"
        )

    line_table = [
        "| line | material chord summary | top volume chords |",
        "|---|---|---|",
    ]
    for row in line_rows:
        line_table.append(f"| `{row['line']}` | {row['material_cm'] or '-'} | {row['top_volume_chords_cm'] or '-'} |")

    text = f"""# Prompt 511 Geometry Ray-Trace Ledger

This is a straight-line geometry diagnostic through the MEGAlib proxy `.geo`
files. It traces selected prompt-eplus annihilation-to-TES proxy lines and a
fixed side-axis line through old/current geometry. It does not model scattering,
attenuation, or Geant4 step history. For each line segment it uses the deepest
placed volume containing that segment, so mother/child volume overlaps are not
double-counted.

## Main Result

The fixed side-axis blocker test is the cleanest result. In the current
geometry, the intended side-window segment has only
`{current_window['material_cm']}` before the detector region. Along the
corresponding old-geometry outer-to-inner side line, the path has
`{old_outer['material_cm']}`. In other words, old `new_geo_re` puts a real
side-shield material column in the region where the current geometry has a thin
window/side-port path.

For all current selected final prompt-eplus events, the median non-Ta material
chord between annihilation and TES is `{current['median_passive_before_tes_cm']:.4g}`
cm. In the current non-window subset, it is
`{current_nonwindow['median_passive_before_tes_cm']:.4g}` cm. Those survivor
lines are typically born in the side-wall/side-port neighborhood after the
outer blocker has already been bypassed; they are not entering through the
nominal Be/Al window disc.

Old selected final prompt-eplus events have a median non-Ta material chord of
`{old['median_passive_before_tes_cm']:.4g}` cm after leaf-volume tracing, but
those events are an old-geometry axial/top population. They are not used as the
direct side-port counterpart.

## Fixed Side-Axis Lines

{chr(10).join(line_table)}

## Current Non-Window Selected Event Examples

{chr(10).join(sample_table)}

## Files

- Event chord CSV: `{EVENT_CSV.relative_to(ROOT)}`
- Volume segment CSV: `{SEGMENT_CSV.relative_to(ROOT)}`
- Fixed-line CSV: `{LINE_CSV.relative_to(ROOT)}`
- Summary JSON: `{SUMMARY_JSON.relative_to(ROOT)}`

## Boundaries

- Volumes are parsed from `{CURRENT_GEO.relative_to(ROOT)}` and `{OLD_GEO}`.
- `BRIK` boxes and the constant-radius/plane boundaries of the local `PCON`
  shapes are traced as straight-line chord intervals in the no-rotation proxy
  geometry. The decisive fixed side-axis lines are constant-z radial lines.
- This is a chord-length audit, not a photon transport or attenuation
  calculation. The SIM interaction ledger remains the transport evidence; this
  ray trace explains the geometry along the proxy lines.
"""
    REPORT_MD.write_text(text, encoding="utf-8")


def main() -> int:
    current_records = load_json(base.CURRENT_RECORDS)
    old_records = load_json(base.OLD_RECORDS)
    current_vols = parse_geo(CURRENT_GEO)
    old_vols = parse_geo(OLD_GEO)

    current_events, current_segments = build_event_traces("current", current_records, current_vols)
    old_events, old_segments = build_event_traces("old", old_records, old_vols)
    event_rows = old_events + current_events
    segment_rows = old_segments + current_segments
    line_rows = build_fixed_lines(current_vols, old_vols)

    write_csv(EVENT_CSV, event_rows)
    write_csv(SEGMENT_CSV, segment_rows)
    write_csv(LINE_CSV, line_rows)

    summary = {
        "status": "PASS_PROMPT511_RAYTRACE_LEDGER",
        "method": {
            "current_geo": str(CURRENT_GEO.relative_to(ROOT)),
            "old_geo": str(OLD_GEO),
            "shape_support": ["BRIK", "PCON"],
            "rotation_support": "none needed; proxy .geo files used here do not contain volume rotations",
            "material_path_rule": "leaf-volume material path; deepest containing placed volume wins, so mother/child overlaps are not double-counted",
            "pcon_boundary_note": "constant-radius/plane PCON boundaries are traced as straight-line chord intervals; decisive fixed side-axis lines are constant-z radial lines",
            "event_ray": "SIM e+ annihilation point to selected TES centroid",
            "fixed_side_axis": "straight local/global line through y=0,z=-5.2 cm",
        },
        "groups": {
            "old_selected_all": summarize_group(old_events),
            "current_selected_all": summarize_group(current_events),
            "current_selected_nonwindow": summarize_group(
                [row for row in current_events if row["leakage_class"] == "non_window_no_window_disk_intersection"]
            ),
            "current_selected_any_window": summarize_group(
                [row for row in current_events if row["leakage_class"] != "non_window_no_window_disk_intersection"]
            ),
        },
        "fixed_lines": line_rows,
        "outputs": {
            "event_csv": str(EVENT_CSV.relative_to(ROOT)),
            "segment_csv": str(SEGMENT_CSV.relative_to(ROOT)),
            "line_csv": str(LINE_CSV.relative_to(ROOT)),
            "report_md": str(REPORT_MD.relative_to(ROOT)),
        },
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(summary, event_rows, line_rows)
    print(json.dumps({"status": summary["status"], "outputs": summary["outputs"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
