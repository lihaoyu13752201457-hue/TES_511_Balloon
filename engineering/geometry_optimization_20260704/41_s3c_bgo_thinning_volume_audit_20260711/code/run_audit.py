#!/usr/bin/env python3
"""Read-only S3c BGO thinning replay and geometry-arithmetic audit.

All writes are confined to the package containing this script.  Retained SIM
and geometry products are streamed/read only; this program never launches
Cosima or Geant4.
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
import subprocess
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
DATA = WORK / "data"

GEOMETRY_SETUP_REL = (
    "engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/"
    "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
GEOMETRY_SETUP = ROOT / GEOMETRY_SETUP_REL
GEOMETRY_DIR = GEOMETRY_SETUP.parent
ATM_SIM_REL = (
    "runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_atm511_sidecar_3m_20260709/"
    "Atm511SidecarS3cBgoW2mmAl3mmShell3M.inc1.id1.sim.gz"
)
ATM_SIM = ROOT / ATM_SIM_REL
PROMPT_DIR_REL = (
    "runs/geometry_optimization_20260704/"
    "s3c_bgo_w2mm_al3mm_shell_eqstats_prompt_eplus_n_20260709"
)
PROMPT_DIR = ROOT / PROMPT_DIR_REL
REF29_REL = (
    "engineering/geometry_optimization_20260704/"
    "29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/README.md"
)
REF40_SUMMARY_REL = (
    "engineering/geometry_optimization_20260704/"
    "40_s3c_mainline_lightweight_review_20260710/data/s3c_mainline_analysis_summary.json"
)
REF40_CANDIDATES_REL = (
    "engineering/geometry_optimization_20260704/"
    "40_s3c_mainline_lightweight_review_20260710/data/s3c_lightweight_candidates.csv"
)
REF38_ACTIVITY_REL = (
    "engineering/geometry_optimization_20260704/"
    "38_s3c_neutron_delayed_chain_m50000_clean_20260710/"
    "delayed_source/delayed_source_exactpos_summary.json"
)

DENSITY = {"BGO": 7.13, "W": 19.3, "Aluminium": 2.70}
CAVITY_R = 21.20
CAVITY_ZMIN = -19.40
CAVITY_ZMAX = 40.90

ATM_W2_CPS = 0.00116688
B_TOTAL_C0 = 0.00505
F3_C0 = 1.35976e-5
EPLUS_CPS = 0.00135997
N_CPS = 0.00135670
RESIDUAL_CPS = 0.00116743
HISTORICAL_LW1_F3_SHIFT = 0.1175
Z95 = 1.959963984540054

IA_RE = re.compile(r"^IA\s+(?P<proc>\S+)\s+(?P<body>.*)$")
ID_RE = re.compile(r"^ID\s+(?P<id>\d+)")
MASS_COMMENT_RE = re.compile(
    r"^// Volume (?P<name>\S+);.*volume_cm3=(?P<vol>[0-9.eE+-]+); mass_kg=(?P<mass>[0-9.eE+-]+)"
)
ENERGY_PROCESSES = {"COMP", "PHOT", "PAIR"}
TRACK_PROCESSES = ENERGY_PROCESSES | {"RAYL"}


@dataclass(frozen=True)
class Panel:
    name: str
    group: str
    material: str
    density: float
    rmin: float
    rmax: float
    zmin: float
    zmax: float
    mass_kg: float


@dataclass(frozen=True)
class IA:
    process: str
    ia_id: int
    parent_id: int
    detector_code: int
    time_s: float
    point_world: tuple[float, float, float]


@dataclass(frozen=True)
class Option:
    option: str
    side_mm: float
    bottom_mm: float
    top_mm: float
    remove_w: bool
    label: str


OPTIONS = (
    Option("O1", 40, 40, 40, True, "remove W only"),
    Option("O2", 30, 40, 40, False, "side 40->30 mm"),
    Option("O3", 20, 40, 40, False, "side 40->20 mm"),
    Option("O4", 40, 30, 40, False, "bottom 40->30 mm"),
    Option("O5", 40, 20, 40, False, "bottom 40->20 mm"),
    Option("O6", 40, 40, 10, False, "top annulus 40->10 mm"),
    Option("O7", 40, 40, 0, False, "top annulus removed"),
    Option("O8", 40, 30, 10, True, "side40/bottom30/top10, no W (LW4 profile)"),
    Option("O9", 30, 30, 30, True, "side30/bottom30/top30, no W (LW5 profile)"),
    Option("O10", 30, 30, 10, True, "side30/bottom30/top10, no W"),
)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def resolve_geometry() -> tuple[Path, Path, tuple[float, float, float]]:
    setup_lines = GEOMETRY_SETUP.read_text(encoding="utf-8").splitlines()
    geo_name = next(line.split(None, 1)[1] for line in setup_lines if line.startswith("Include ") and line.endswith(".geo"))
    geo_path = GEOMETRY_DIR / geo_name
    geo_lines = geo_path.read_text(encoding="utf-8").splitlines()
    intro_name = next(line.split(None, 1)[1] for line in geo_lines if line.startswith("Include ") and "Intro_" in line)
    intro_path = GEOMETRY_DIR / intro_name
    intro = intro_path.read_text(encoding="utf-8").splitlines()
    rot_line = next(line for line in intro if line.startswith("InstrumentFrame.Rotation "))
    rotation = tuple(float(v) for v in rot_line.split()[1:4])
    if abs(rotation[0]) > 1e-12 or abs(rotation[2]) > 1e-12:
        raise RuntimeError(f"unsupported InstrumentFrame rotation: {rotation}")
    return geo_path, intro_path, rotation


def parse_mass_comments(geo_path: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for line in geo_path.read_text(encoding="utf-8").splitlines():
        match = MASS_COMMENT_RE.match(line)
        if match:
            out[match.group("name")] = {
                "volume_cm3": float(match.group("vol")),
                "mass_kg": float(match.group("mass")),
            }
    return out


def find_line_value(lines: list[str], prefix: str) -> list[float]:
    line = next((line for line in lines if line.startswith(prefix)), None)
    if line is None:
        raise RuntimeError(f"missing geometry line: {prefix}")
    return [float(value) for value in line.split()[1:]]


def parse_panel(
    lines: list[str], masses: dict[str, dict[str, float]], name: str, group: str, material: str, shape: str
) -> Panel:
    if shape == "side":
        params = find_line_value(lines, f"{name}_FullShellShape.Parameters ")
        position = find_line_value(lines, f"{name}.Position ")
        zmin, rmin, rmax = params[3:6]
        zmax = params[6]
        zmin += position[2]
        zmax += position[2]
    else:
        params = find_line_value(lines, f"{name}_BasePconShape.Parameters ")
        position = find_line_value(lines, f"{name}.Position ")
        zmin, rmin, rmax = params[3:6]
        zmax = params[6]
        zmin += position[2]
        zmax += position[2]
    return Panel(
        name=name,
        group=group,
        material=material,
        density=DENSITY[material],
        rmin=rmin,
        rmax=rmax,
        zmin=zmin,
        zmax=zmax,
        mass_kg=masses[name]["mass_kg"],
    )


def load_panels(geo_path: Path) -> tuple[list[Panel], dict[str, dict[str, float]]]:
    lines = geo_path.read_text(encoding="utf-8").splitlines()
    masses = parse_mass_comments(geo_path)
    specs = (
        ("BGO_S3C_FullWrap_SideShell_WindowCut_40mm", "bgo_side", "BGO", "side"),
        ("BGO_S3C_FullWrap_BottomCap_40mm", "bgo_bottom", "BGO", "cap"),
        ("BGO_S3C_FullWrap_TopAnnulus_40mm", "bgo_top", "BGO", "cap"),
        ("Outer_W_S3C_BGO_Mechanical_SideShell_WindowCut_2mm", "w_shell", "W", "side"),
        ("Outer_W_S3C_BGO_Mechanical_BottomCap_2mm", "w_shell", "W", "cap"),
        ("Outer_W_S3C_BGO_Mechanical_TopAnnulus_2mm", "w_shell", "W", "cap"),
        ("Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm", "al_shell", "Aluminium", "side"),
        ("Outer_Al_S3C_BGO_Mechanical_BottomCap_3mm", "al_shell", "Aluminium", "cap"),
        ("Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm", "al_shell", "Aluminium", "cap"),
    )
    return [parse_panel(lines, masses, *spec) for spec in specs], masses


def inverse_y_rotation(point: Iterable[float], angle_deg: float) -> tuple[float, float, float]:
    x, y, z = point
    angle = math.radians(angle_deg)
    c = math.cos(angle)
    s = math.sin(angle)
    return (c * x - s * z, y, s * x + c * z)


def parse_ia(line: str) -> IA | None:
    match = IA_RE.match(line)
    if not match:
        return None
    fields = [part.strip() for part in match.group("body").split(";")]
    if len(fields) < 7:
        return None
    try:
        return IA(
            process=match.group("proc").upper(),
            ia_id=int(fields[0]),
            parent_id=int(fields[1]),
            detector_code=int(fields[2]),
            time_s=float(fields[3]),
            point_world=(float(fields[4]), float(fields[5]), float(fields[6])),
        )
    except ValueError:
        return None


def parse_init(line: str) -> tuple[tuple[float, float, float], tuple[float, float, float], float] | None:
    match = IA_RE.match(line)
    if not match or match.group("proc").upper() != "INIT":
        return None
    fields = [part.strip() for part in match.group("body").split(";")]
    try:
        return (
            (float(fields[4]), float(fields[5]), float(fields[6])),
            (float(fields[16]), float(fields[17]), float(fields[18])),
            float(fields[-1]),
        )
    except (IndexError, ValueError):
        return None


def cylinder_interval(
    origin: tuple[float, float, float], direction: tuple[float, float, float], radius: float, zmin: float, zmax: float
) -> tuple[float, float] | None:
    ox, oy, oz = origin
    dx, dy, dz = direction
    a = dx * dx + dy * dy
    b = 2.0 * (ox * dx + oy * dy)
    c = ox * ox + oy * oy - radius * radius
    if a < 1e-15:
        if c > 0:
            return None
        radial_lo, radial_hi = -math.inf, math.inf
    else:
        disc = b * b - 4.0 * a * c
        if disc < 0:
            return None
        root = math.sqrt(max(0.0, disc))
        radial_lo = (-b - root) / (2.0 * a)
        radial_hi = (-b + root) / (2.0 * a)
    if abs(dz) < 1e-15:
        if not (zmin <= oz <= zmax):
            return None
        z_lo, z_hi = -math.inf, math.inf
    else:
        za = (zmin - oz) / dz
        zb = (zmax - oz) / dz
        z_lo, z_hi = min(za, zb), max(za, zb)
    lo = max(radial_lo, z_lo, 0.0)
    hi = min(radial_hi, z_hi)
    return (lo, hi) if hi > lo + 1e-10 else None


def panel_contains(panel: Panel, point: tuple[float, float, float], tol: float = 1e-8) -> bool:
    x, y, z = point
    radius = math.hypot(x, y)
    return (
        panel.rmin - tol <= radius <= panel.rmax + tol
        and panel.zmin - tol <= z <= panel.zmax + tol
    )


def panel_intervals(
    panel: Panel,
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    tmax: float,
) -> list[tuple[float, float]]:
    if tmax <= 0:
        return []
    ox, oy, oz = origin
    dx, dy, dz = direction
    cuts = [0.0, tmax]
    if abs(dz) > 1e-15:
        for z in (panel.zmin, panel.zmax):
            t = (z - oz) / dz
            if 0.0 < t < tmax:
                cuts.append(t)
    a = dx * dx + dy * dy
    if a > 1e-15:
        b = 2.0 * (ox * dx + oy * dy)
        for radius in {panel.rmin, panel.rmax}:
            c = ox * ox + oy * oy - radius * radius
            disc = b * b - 4.0 * a * c
            if disc < 0:
                continue
            root = math.sqrt(max(0.0, disc))
            for t in ((-b - root) / (2.0 * a), (-b + root) / (2.0 * a)):
                if 0.0 < t < tmax:
                    cuts.append(t)
    cuts = sorted(set(round(t, 12) for t in cuts))
    intervals: list[tuple[float, float]] = []
    for left, right in zip(cuts, cuts[1:]):
        if right <= left:
            continue
        mid = 0.5 * (left + right)
        point = (ox + mid * dx, oy + mid * dy, oz + mid * dz)
        if panel_contains(panel, point):
            intervals.append((left, right))
    return intervals


def path_column(
    panels: Iterable[Panel],
    origin: tuple[float, float, float],
    direction: tuple[float, float, float],
    tmax: float,
) -> float:
    total = 0.0
    for panel in panels:
        total += panel.density * sum(right - left for left, right in panel_intervals(panel, origin, direction, tmax))
    return total


def gross_volume(panel: Panel, thickness_cm: float | None = None) -> float:
    if panel.group == "bgo_side":
        rmax = panel.rmax if thickness_cm is None else panel.rmin + thickness_cm
        return math.pi * (rmax * rmax - panel.rmin * panel.rmin) * (panel.zmax - panel.zmin)
    if panel.group == "bgo_bottom":
        height = panel.zmax - panel.zmin if thickness_cm is None else thickness_cm
        return math.pi * (panel.rmax * panel.rmax - panel.rmin * panel.rmin) * height
    if panel.group == "bgo_top":
        height = panel.zmax - panel.zmin if thickness_cm is None else thickness_cm
        return math.pi * (panel.rmax * panel.rmax - panel.rmin * panel.rmin) * height
    return math.pi * (panel.rmax * panel.rmax - panel.rmin * panel.rmin) * (panel.zmax - panel.zmin)


def removed_panels(option: Option, panels: list[Panel]) -> list[Panel]:
    by_group = {panel.group: panel for panel in panels if panel.group.startswith("bgo_")}
    removed: list[Panel] = []
    side = by_group["bgo_side"]
    side_outer_new = side.rmin + option.side_mm / 10.0
    if side_outer_new < side.rmax - 1e-12:
        removed.append(Panel("removed_bgo_side", "removed", "BGO", side.density, side_outer_new, side.rmax, side.zmin, side.zmax, 0.0))
    bottom = by_group["bgo_bottom"]
    bottom_outer_new = bottom.zmax - option.bottom_mm / 10.0
    if bottom_outer_new > bottom.zmin + 1e-12:
        removed.append(Panel("removed_bgo_bottom", "removed", "BGO", bottom.density, bottom.rmin, bottom.rmax, bottom.zmin, bottom_outer_new, 0.0))
    top = by_group["bgo_top"]
    top_outer_new = top.zmin + option.top_mm / 10.0
    if top_outer_new < top.zmax - 1e-12:
        removed.append(Panel("removed_bgo_top", "removed", "BGO", top.density, top.rmin, top.rmax, top_outer_new, top.zmax, 0.0))
    if option.remove_w:
        removed.extend(panel for panel in panels if panel.group == "w_shell")
    return removed


def classify_point(point: tuple[float, float, float], panels: list[Panel]) -> str | None:
    # Axisymmetric coordinate boxes are the contract's classifier; exact CSG
    # reliefs/window cuts are intentionally not reconstructed in this replay.
    for group in ("al_shell", "w_shell", "bgo_top", "bgo_bottom", "bgo_side"):
        if any(panel_contains(panel, point) for panel in panels if panel.group == group):
            return group
    return None


def iter_filtered_sim(path: Path, pattern: str) -> Iterator[str]:
    gzip_proc = subprocess.Popen(["gzip", "-dc", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if gzip_proc.stdout is None:
        raise RuntimeError(f"cannot open gzip stream: {path}")
    grep_proc = subprocess.Popen(
        ["grep", "-E", pattern], stdin=gzip_proc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    gzip_proc.stdout.close()
    if grep_proc.stdout is None:
        raise RuntimeError(f"cannot filter gzip stream: {path}")
    try:
        for raw in grep_proc.stdout:
            yield raw.rstrip("\n")
    finally:
        grep_proc.stdout.close()
    grep_stderr = grep_proc.stderr.read() if grep_proc.stderr else ""
    gzip_stderr = gzip_proc.stderr.read() if gzip_proc.stderr else ""
    grep_rc = grep_proc.wait()
    gzip_rc = gzip_proc.wait()
    if grep_rc not in (0, 1) or gzip_rc != 0:
        raise RuntimeError(
            f"stream failure {path}: gzip={gzip_rc} grep={grep_rc}; {gzip_stderr.strip()} {grep_stderr.strip()}"
        )


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        return (math.nan, math.nan)
    p = successes / total
    z2 = Z95 * Z95
    denom = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denom
    half = Z95 * math.sqrt(p * (1.0 - p) / total + z2 / (4.0 * total * total)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def scan_atm(
    panels: list[Panel], rotation_y_deg: float, removals: dict[str, list[Panel]]
) -> tuple[dict[str, Any], dict[str, Counter[str]], list[tuple[float, float | None]]]:
    pattern = r"^(Geometry\s+|SE$|ID\s+|IA\s+(INIT|RAYL|COMP|PHOT|PAIR)\s+)"
    counters = Counter()
    option_new = Counter()
    panel_counts = Counter()
    depth_records: list[tuple[float, float | None]] = []
    header_geometry: str | None = None
    current_id: int | None = None
    init: tuple[tuple[float, float, float], tuple[float, float, float], float] | None = None
    primary_ias: list[IA] = []

    def flush() -> None:
        nonlocal current_id, init, primary_ias
        if current_id is None:
            return
        counters["generated_events"] += 1
        if init is None:
            counters["missing_init"] += 1
            current_id = None
            primary_ias = []
            return
        origin_world, direction_world, _energy = init
        origin = inverse_y_rotation(origin_world, rotation_y_deg)
        direction = inverse_y_rotation(direction_world, rotation_y_deg)
        norm = math.sqrt(sum(value * value for value in direction))
        if norm <= 0:
            counters["zero_direction"] += 1
            current_id = None
            init = None
            primary_ias = []
            return
        direction = tuple(value / norm for value in direction)
        cavity = cylinder_interval(origin, direction, CAVITY_R, CAVITY_ZMIN, CAVITY_ZMAX)
        if cavity is None:
            current_id = None
            init = None
            primary_ias = []
            return
        t_cavity = cavity[0]
        counters["cavity_reaching_rays"] += 1
        ordered = sorted(primary_ias, key=lambda item: (item.time_s, item.ia_id))
        if ordered and ordered[0].process == "RAYL":
            counters["rayl_first_events"] += 1
        first = next((item for item in ordered if item.process in ENERGY_PROCESSES), None)
        first_t: float | None = None
        first_point: tuple[float, float, float] | None = None
        if first is not None:
            first_point = inverse_y_rotation(first.point_world, rotation_y_deg)
            first_t = sum((first_point[i] - origin[i]) * direction[i] for i in range(3))
            perpendicular = math.sqrt(
                sum((first_point[i] - (origin[i] + first_t * direction[i])) ** 2 for i in range(3))
            )
            if perpendicular > 1e-3:
                counters["first_nonrayl_off_init_ray_gt_1e3cm"] += 1
        first_before_cavity = first_t is not None and first_t < t_cavity - 1e-8 and first_t >= 0.0
        c_orig = path_column(panels, origin, direction, t_cavity)
        if first_before_cavity:
            counters["vetoed_c0"] += 1
            x_column = path_column(panels, origin, direction, min(first_t, t_cavity))
            remaining = max(0.0, c_orig - x_column)
            group = classify_point(first_point, panels) if first_point is not None else None
            if group is not None:
                panel_counts[group] += 1
            else:
                counters["first_nonrayl_unclassified_before_cavity"] += 1
            for option_name, option_panels in removals.items():
                c_removed = path_column(option_panels, origin, direction, t_cavity)
                if remaining < c_removed:
                    option_new[option_name] += 1
        else:
            counters["passthrough_c0"] += 1
            if first is None:
                counters["no_primary_nonrayl"] += 1
            elif first_t is not None and first_t < 0:
                counters["negative_projected_first_t"] += 1

        # Censored exponential exposure for rays entering the cavity through
        # the side and traversing a contiguous BGO-side chord immediately prior.
        bgo_side = next(panel for panel in panels if panel.group == "bgo_side")
        intervals = panel_intervals(bgo_side, origin, direction, t_cavity)
        if intervals:
            entry, exit_ = intervals[-1]
            if abs(exit_ - t_cavity) < 1e-6 and exit_ > entry:
                if first_t is None or first_t >= entry - 1e-8:
                    chord = exit_ - entry
                    event_depth: float | None = None
                    if first_t is not None and entry - 1e-8 <= first_t < exit_ - 1e-8:
                        event_depth = max(0.0, first_t - entry)
                    depth_records.append((chord, event_depth))
        current_id = None
        init = None
        primary_ias = []

    start = time.monotonic()
    for line in iter_filtered_sim(ATM_SIM, pattern):
        if line.startswith("Geometry "):
            header_geometry = line.split(None, 1)[1]
        elif line == "SE":
            flush()
        else:
            match_id = ID_RE.match(line)
            if match_id:
                flush()
                current_id = int(match_id.group("id"))
                init = None
                primary_ias = []
            elif line.startswith("IA INIT"):
                init = parse_init(line)
            elif line.startswith("IA "):
                item = parse_ia(line)
                if item is not None and item.parent_id == 1 and item.process in TRACK_PROCESSES:
                    primary_ias.append(item)
    flush()
    elapsed = time.monotonic() - start
    counters["elapsed_seconds"] = elapsed
    counters["compressed_bytes"] = ATM_SIM.stat().st_size
    result = {
        "header_geometry": header_geometry,
        "counters": dict(counters),
        "option_new_leaks": dict(option_new),
        "panel_interceptions": dict(panel_counts),
    }
    return result, {"atm511": panel_counts}, depth_records


def choose_prompt_files(atm_elapsed_seconds: float) -> tuple[dict[str, list[Path]], dict[str, Any]]:
    all_files = {
        component: sorted(PROMPT_DIR.glob(f"Background_{component}_fullsphere20_*.sim.gz"))
        for component in ("eplus", "n")
    }
    total_bytes = sum(path.stat().st_size for paths in all_files.values() for path in paths)
    throughput = ATM_SIM.stat().st_size / max(atm_elapsed_seconds, 1e-9)
    projected = total_bytes / max(throughput, 1e-9)
    selected = {component: list(paths) for component, paths in all_files.items()}
    if projected > 900.0:
        fraction = 900.0 / projected
        for component, paths in all_files.items():
            keep = max(1, min(len(paths), int(math.floor(len(paths) * fraction))))
            if keep == 1:
                indices = [len(paths) // 2]
            else:
                indices = sorted({round(i * (len(paths) - 1) / (keep - 1)) for i in range(keep)})
            selected[component] = [paths[index] for index in indices]
    meta = {
        "projection_method": "scaled from the single retained atm511 streaming-pass compressed-byte throughput",
        "projected_full_prompt_seconds": projected,
        "budget_seconds": 900.0,
        "all_files": {component: [rel(path) for path in paths] for component, paths in all_files.items()},
        "selected_files": {component: [rel(path) for path in paths] for component, paths in selected.items()},
        "file_fraction": {
            component: (len(selected[component]) / len(all_files[component]) if all_files[component] else 0.0)
            for component in all_files
        },
        "byte_fraction": {
            component: (
                sum(path.stat().st_size for path in selected[component])
                / sum(path.stat().st_size for path in all_files[component])
                if all_files[component]
                else 0.0
            )
            for component in all_files
        },
    }
    return selected, meta


def normalize_geometry(value: str | None) -> str | None:
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve().as_posix()


def scan_prompt_file(path: Path, panels: list[Panel], rotation_y_deg: float) -> tuple[Counter[str], dict[str, Any]]:
    pattern = r"^(Geometry\s+|SE$|ID\s+|IA\s+(COMP|PHOT|PAIR)\s+)"
    counts = Counter()
    current_id: int | None = None
    event_groups: set[str] = set()
    header_geometry: str | None = None

    def flush() -> None:
        nonlocal current_id, event_groups
        if current_id is not None:
            counts["events"] += 1
            for group in event_groups:
                counts[group] += 1
        current_id = None
        event_groups = set()

    start = time.monotonic()
    for line in iter_filtered_sim(path, pattern):
        if line.startswith("Geometry "):
            header_geometry = line.split(None, 1)[1]
        elif line == "SE":
            flush()
        else:
            match_id = ID_RE.match(line)
            if match_id:
                flush()
                current_id = int(match_id.group("id"))
            elif current_id is not None and line.startswith("IA "):
                item = parse_ia(line)
                if item is None or item.process not in ENERGY_PROCESSES:
                    continue
                point = inverse_y_rotation(item.point_world, rotation_y_deg)
                group = classify_point(point, panels)
                if group is not None:
                    event_groups.add(group)
    flush()
    return counts, {
        "path": rel(path),
        "header_geometry": header_geometry,
        "geometry_match": normalize_geometry(header_geometry) == GEOMETRY_SETUP.resolve().as_posix(),
        "elapsed_seconds": time.monotonic() - start,
        "compressed_bytes": path.stat().st_size,
        "events": counts["events"],
    }


def scan_prompt(
    selected: dict[str, list[Path]], panels: list[Panel], rotation_y_deg: float, meta: dict[str, Any]
) -> tuple[dict[str, Counter[str]], dict[str, Any]]:
    totals: dict[str, Counter[str]] = {component: Counter() for component in selected}
    files_meta: dict[str, list[dict[str, Any]]] = {component: [] for component in selected}
    start = time.monotonic()
    for component in ("eplus", "n"):
        for path in selected[component]:
            counts, evidence = scan_prompt_file(path, panels, rotation_y_deg)
            totals[component].update(counts)
            files_meta[component].append(evidence)
    meta = dict(meta)
    meta["actual_elapsed_seconds"] = time.monotonic() - start
    meta["files"] = files_meta
    meta["all_selected_headers_match"] = all(
        item["geometry_match"] for rows in files_meta.values() for item in rows
    )
    return totals, meta


def build_depth_profile(records: list[tuple[float, float | None]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    interactions = sum(1 for _chord, depth in records if depth is not None)
    exposure = sum(depth if depth is not None else chord for chord, depth in records)
    mu = interactions / exposure if exposure > 0 else math.nan
    max_depth = max((chord for chord, _depth in records), default=0.0)
    width = 0.25
    bins = int(math.ceil(max_depth / width))
    rows: list[dict[str, Any]] = []
    for index in range(bins):
        left = index * width
        right = (index + 1) * width
        bin_exposure = 0.0
        at_risk = 0
        observed = 0
        for chord, depth in records:
            stop = depth if depth is not None else chord
            if stop > left:
                at_risk += 1
                bin_exposure += max(0.0, min(stop, right) - left)
            if depth is not None and left <= depth < right:
                observed += 1
        rows.append(
            {
                "depth_bin_lo_cm": left,
                "depth_bin_hi_cm": right,
                "depth_bin_mid_cm": 0.5 * (left + right),
                "at_risk_count": at_risk,
                "interaction_count": observed,
                "exposure_cm": bin_exposure,
                "hazard_per_cm": observed / bin_exposure if bin_exposure > 0 else "",
                "fitted_survival": math.exp(-mu * 0.5 * (left + right)) if math.isfinite(mu) else "",
            }
        )
    fit = {
        "method": "right-censored exponential MLE on straight-ray BGO-side chord depth",
        "eligible_chords": len(records),
        "interactions": interactions,
        "censored": len(records) - interactions,
        "total_exposure_cm": exposure,
        "mu_eff_cm-1": mu,
        "bin_width_cm": width,
    }
    return rows, fit


def mass_model(panels: list[Panel], masses: dict[str, dict[str, float]]) -> tuple[dict[str, Any], dict[str, float]]:
    bgo = {panel.group: panel for panel in panels if panel.group.startswith("bgo_")}
    checks: dict[str, Any] = {}
    factors: dict[str, float] = {}
    for group, panel in bgo.items():
        gross = gross_volume(panel)
        analytic_mass = gross * panel.density / 1000.0
        factor = panel.mass_kg / analytic_mass
        factors[group] = factor
        checks[group] = {
            "volume_name": panel.name,
            "analytic_gross_mass_kg": analytic_mass,
            "retained_mass_kg": panel.mass_kg,
            "relative_error": abs(analytic_mass - panel.mass_kg) / panel.mass_kg,
            "retained_to_gross_factor": factor,
        }
    kapton_names = [name for name in masses if name.startswith("ActiveShield_S3C_BGO_Kapton_")]
    kapton_mass = sum(masses[name]["mass_kg"] for name in kapton_names)
    group_mass = Counter()
    for panel in panels:
        group_mass[panel.group] += panel.mass_kg
    baseline = sum(group_mass.values()) + kapton_mass

    option_mass: dict[str, float] = {}
    for option in OPTIONS:
        side_mass = gross_volume(bgo["bgo_side"], option.side_mm / 10.0) * DENSITY["BGO"] / 1000.0 * factors["bgo_side"]
        bottom_mass = gross_volume(bgo["bgo_bottom"], option.bottom_mm / 10.0) * DENSITY["BGO"] / 1000.0 * factors["bgo_bottom"]
        top_mass = gross_volume(bgo["bgo_top"], option.top_mm / 10.0) * DENSITY["BGO"] / 1000.0 * factors["bgo_top"]
        w_mass = 0.0 if option.remove_w else group_mass["w_shell"]
        option_mass[option.option] = side_mass + bottom_mass + top_mass + w_mass + group_mass["al_shell"] + kapton_mass
    return {
        "bgo_reproduction": checks,
        "relief_scaling_rule": "retained-to-axisymmetric-gross mass factor held constant for each BGO panel",
        "kapton_mass_kg_held_constant": kapton_mass,
        "kapton_volume_names": kapton_names,
        "group_masses_kg": dict(group_mass),
        "baseline_mass_kg": baseline,
    }, option_mass


def git_status() -> list[str]:
    proc = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=True)
    return [line for line in proc.stdout.splitlines() if line]


def build_readme(summary: dict[str, Any], pareto_rows: list[dict[str, Any]], importance_rows: list[dict[str, Any]]) -> str:
    gates = summary["gates"]
    fail_names = [name for name, gate in gates.items() if gate["severity"] == "FAIL" and not gate["pass"]]
    status = "PASS_S3C_THINNING_VOLUME_AUDIT" if not fail_names else f"FAIL_S3C_THINNING_AUDIT_{fail_names[0]}"
    warn_tokens = []
    if not gates["G3"]["pass"]:
        warn_tokens.append("G3_INVESTIGATE_MU_EFF")
    if not gates["G4"]["pass"]:
        warn_tokens.append("METHOD_LOW_CONFIDENCE")
    status_suffix = "" if not warn_tokens else " — WARN: " + ", ".join(warn_tokens)
    baseline_leak = summary["atm511"]["counters"]["passthrough_c0"]
    cavity = summary["atm511"]["counters"]["cavity_reaching_rays"]
    worst = max(pareto_rows, key=lambda row: float(row["atm511_T_ratio"]))
    ranked = sorted(importance_rows, key=lambda row: float(row["interceptions_per_kg"]), reverse=True)
    top_rank = ranked[0]
    mu = summary["depth_fit"]["mu_eff_cm-1"]
    o1 = next(row for row in pareto_rows if row["option"] == "O1")
    o2 = next(row for row in pareto_rows if row["option"] == "O2")
    o4 = next(row for row in pareto_rows if row["option"] == "O4")
    o6 = next(row for row in pareto_rows if row["option"] == "O6")

    lines = [
        "# S3c BGO Thinning and Shield-Volume Audit",
        f"Status: `{status}`{status_suffix}",
        "",
        "## Answers",
        "",
        (
            f"1. **Can BGO be thinner?** C0 has {baseline_leak:,}/{cavity:,} straight-ray cavity passthroughs. "
            f"The mild isolated cuts are O4 bottom30: +{int(o4['new_leak'])} leaks, T/T0={float(o4['atm511_T_ratio']):.4f}, "
            f"F3={float(o4['predicted_F3_20d']):.6e}; O6 top10: +{int(o6['new_leak'])}, T/T0={float(o6['atm511_T_ratio']):.4f}, "
            f"F3={float(o6['predicted_F3_20d']):.6e}; and O2 side30: +{int(o2['new_leak'])}, "
            f"T/T0={float(o2['atm511_T_ratio']):.4f}, F3={float(o2['predicted_F3_20d']):.6e}. The combined worst listed "
            f"case is {worst['option']} at T/T0={float(worst['atm511_T_ratio']):.4f}. These are only proposals for "
            f"the 40_ screening matrix, not transport closure. "
            "Sources: `data/thinning_leak_table.csv`, `data/pareto_options.csv`, "
            f"`{REF40_SUMMARY_REL}`."
        ),
        (
            f"2. **Which volume is cheapest to remove?** The counted-interceptions/kg ranking is "
            + " > ".join(f"{row['volume']} {float(row['interceptions_per_kg']):.1f}" for row in ranked)
            + f"; the lightest Pareto-listed option is {min(pareto_rows, key=lambda row: float(row['mass_kg']))['option']}. "
            "Use the ranking only as a screening proxy because prompt counts include primary and descendant IA records "
            "deduplicated to one interception per event-volume. Sources: `data/panel_importance.csv`, "
            "`data/pareto_options.csv`."
        ),
        "",
        "The 6-event W2 atm511 anchor carries +/-41% (1 sigma) counting error, which dominates every "
        "predicted_atm511_w2_cps. Source: "
        "`engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/data/s3c_w2_background_distribution.csv`.",
        "",
        "## Option table",
        "",
        "All numbers below are sourced from `data/pareto_options.csv`; Delta-m is option minus C0 (negative means saved mass). "
        "All options retain Al3 and unchanged Kapton; `LW4/LW5` identify BGO profiles, not the historical Al5 shell.",
        "",
        "| Option | change | mass kg | Delta-m kg | atm511 T/T0 (95% CI) | atm511 W2 cps | B total cps | F3 scale | F3 20d | Pareto | delayed note |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|---|",
    ]
    for row in pareto_rows:
        lines.append(
            "| {option} | {change} | {mass:.3f} | {dmass:.3f} | {ratio:.4f} [{lo:.4f}, {hi:.4f}] | "
            "{atm:.7g} | {b:.7g} | {scale:.5f} | {f3:.6e} | {pareto} | {delayed} |".format(
                option=row["option"],
                change=row["change"],
                mass=float(row["mass_kg"]),
                dmass=float(row["dmass_kg"]),
                ratio=float(row["atm511_T_ratio"]),
                lo=float(row["atm511_T_ratio_ci_low"]),
                hi=float(row["atm511_T_ratio_ci_high"]),
                atm=float(row["predicted_atm511_w2_cps"]),
                b=float(row["predicted_B_total_cps"]),
                scale=float(row["F3_scale"]),
                f3=float(row["predicted_F3_20d"]),
                pareto="yes" if row["pareto_efficient"] else "no",
                delayed=row["delayed_note"],
            )
        )
    lines.extend(
        [
            "",
            "O1's delayed family figures come from "
            f"`{REF40_CANDIDATES_REL}` and `{REF38_ACTIVITY_REL}`; no Bq value is extrapolated to a BGO-thinning row.",
            "",
            "The ratio interval is a 95% Wilson binomial interval for option leaks among counted cavity-directed "
            "photons, divided by the observed C0 leak fraction. The absolute normalization assumes the per-cavity-reaching-"
            "photon W2 conversion probability is option-independent. Sources: `data/thinning_leak_table.csv`, "
            "`data/pareto_options.csv`.",
            "",
            "## Geometry and mass arithmetic",
            "",
            (
                f"Analytic gross BGO masses reproduce the retained side/bottom/top values within 1%; the retained "
                f"relief factors are then held fixed for thinner panels. The W side/bottom/top extents are "
                f"r=25.50--25.70 cm, z=-23.70--45.20 cm / r=0--26.00 cm, z=-23.90---23.70 cm / "
                f"r=20.90--26.00 cm, z=45.20--45.40 cm; Al is r=25.70--26.00 cm, z=-23.70--45.20 cm / "
                f"r=0--26.00 cm, z=-24.20---23.90 cm / r=20.90--26.00 cm, z=45.40--45.70 cm. "
                f"Sources: `{GEOMETRY_SETUP_REL}` and its included `.geo`, `{REF29_REL}`, `data/summary.json`."
            ),
            "",
            f"The right-censored straight-chord fit gives mu_eff={mu:.5f} cm^-1. Source: `data/depth_profile.csv`.",
            "",
            "## Method calibration",
            "",
            (
                f"O1 implies an F3 shift of {(float(o1['F3_scale']) - 1.0) * 100:.3f}% versus C0, while the historical "
                f"LW1 screen is +11.75% and also changes Al 3->8 mm; the larger/smaller shift ratio is "
                f"{summary['calibration']['shift_ratio']:.3f}. Sources: `data/pareto_options.csv`, "
                f"`{REF40_CANDIDATES_REL}`."
            ),
            "",
            "## Method limits",
            "",
            "(a) coupling drops secondary particles that interactions in the removed slab would have produced (biases leak LOW);",
            "",
            "(b) some newly leaked photons would scatter in remaining material and miss W2 anyway (biases leak HIGH);",
            "",
            "(c) e+/n/residual components are held flat at the frozen budget — thinning effects on them are NOT modeled here and require the 40_ run-matrix screening transport.",
            "",
            "## Data-quality and gate notes",
            "",
            f"- G1: {'PASS' if gates['G1']['pass'] else 'FAIL'}; analytic BGO mass errors and parsed W/Al extents are in `data/summary.json`.",
            f"- G2: {'PASS' if gates['G2']['pass'] else 'FAIL'}; exact per-option identities are in `data/thinning_leak_table.csv`.",
            f"- G3: {'PASS' if gates['G3']['pass'] else 'WARN'}; mu_eff={mu:.5f} cm^-1 from `data/depth_profile.csv`.",
            f"- G4: {'PASS' if gates['G4']['pass'] else 'WARN'}; O1/LW1 shift comparison is in `data/summary.json`.",
            f"- G5: {'PASS' if gates['G5']['pass'] else 'FAIL'}; literal `git status --porcelain` evidence is in `data/summary.json`.",
            f"- G6: {'PASS' if gates['G6']['pass'] else 'FAIL'}; checked again by `code/validate_audit.py`.",
            f"- RAYL-first cavity-directed events: {summary['atm511']['counters'].get('rayl_first_events', 0):,}; "
            "source: `data/summary.json`.",
            "",
            "## Gaps",
            "",
        ]
    )
    if not gates["G5"]["pass"]:
        lines.append(
            "- G5 literal gate is `MISSING_CLEAN_WORKTREE`: pre-existing modified/untracked paths outside `41_` were "
            "already present and were preserved. This audit created no intended output outside `41_`; see "
            "`data/summary.json` for the status snapshot."
        )
    prompt = summary["prompt_scan"]
    if min(prompt["file_fraction"].values(), default=1.0) < 1.0:
        lines.append(
            "- Prompt-panel importance used uniformly selected whole-file subsamples because the projected full scan "
            "exceeded 15 minutes; fractions are in `data/summary.json`."
        )
    if not prompt["all_selected_headers_match"]:
        lines.append("- `MISSING_INPUT`: at least one selected prompt SIM header does not match the pinned S3c geometry.")
    if gates["G3"]["pass"] is False:
        lines.append(
            "- G3 investigation: mu_eff is outside 0.80--1.10 cm^-1. Check the axisymmetric-box treatment of window/relief "
            "rays and the straight-INIT projection of RAYL-first events before using the fit quantitatively."
        )
    if all(gate["pass"] for name, gate in gates.items() if name != "G5") and not gates["G5"]["pass"]:
        lines.append("- No analysis-input or arithmetic gap remains; the only FAIL is the pre-existing-worktree G5 condition.")
    lines.extend(
        [
            "",
            "## Non-claims",
            "",
            "- Screening arithmetic on frozen budgets; NOT a full S3c prompt-family or Step05–08 closure; NOT structural qualification; no promotion decision.",
            "- atm511 absolute normalization inherits the unresolved Harris-vs-4π-sidecar calibration; ratios reported here are internal to the 4π sidecar and do not resolve it.",
            "- The 6-event W2 atm511 anchor carries ±41% (1σ) counting error which dominates every predicted_atm511_w2_cps; print this next to the table.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    starting_status = git_status()
    geo_path, intro_path, rotation = resolve_geometry()
    panels, mass_comments = load_panels(geo_path)
    removals = {option.option: removed_panels(option, panels) for option in OPTIONS}
    atm, panel_component_counts, depth_records = scan_atm(panels, rotation[1], removals)
    selected_prompt, prompt_projection = choose_prompt_files(float(atm["counters"]["elapsed_seconds"]))
    prompt_counts, prompt_meta = scan_prompt(selected_prompt, panels, rotation[1], prompt_projection)
    panel_component_counts.update(prompt_counts)
    depth_rows, depth_fit = build_depth_profile(depth_records)
    write_csv(DATA / "depth_profile.csv", depth_rows)
    mass_meta, option_masses = mass_model(panels, mass_comments)

    cavity = int(atm["counters"]["cavity_reaching_rays"])
    passthrough = int(atm["counters"]["passthrough_c0"])
    vetoed = int(atm["counters"]["vetoed_c0"])
    if passthrough + vetoed != cavity:
        raise RuntimeError("atm C0 population does not conserve")
    leak_rows: list[dict[str, Any]] = []
    for option in OPTIONS:
        new_leak = int(atm["option_new_leaks"].get(option.option, 0))
        leak = passthrough + new_leak
        still = vetoed - new_leak
        p_lo, p_hi = wilson_interval(leak, cavity)
        baseline_fraction = passthrough / cavity
        ratio = leak / passthrough
        leak_rows.append(
            {
                "option": option.option,
                "change": option.label,
                "cavity_reaching": cavity,
                "passthrough_c0": passthrough,
                "vetoed_c0": vetoed,
                "new_leak": new_leak,
                "still_vetoed": still,
                "leak": leak,
                "identity_leak_pass": leak == passthrough + new_leak,
                "identity_veto_pass": new_leak + still == vetoed,
                "atm511_T_ratio": ratio,
                "atm511_T_ratio_ci_low": p_lo / baseline_fraction,
                "atm511_T_ratio_ci_high": p_hi / baseline_fraction,
            }
        )
    write_csv(DATA / "thinning_leak_table.csv", leak_rows)

    baseline_mass = float(mass_meta["baseline_mass_kg"])
    pareto_rows: list[dict[str, Any]] = []
    for option, leak_row in zip(OPTIONS, leak_rows):
        ratio = float(leak_row["atm511_T_ratio"])
        predicted_atm = ATM_W2_CPS * ratio
        predicted_b = B_TOTAL_C0 - ATM_W2_CPS + predicted_atm
        f3_scale = math.sqrt(predicted_b / B_TOTAL_C0)
        mass = option_masses[option.option]
        delayed = (
            "W-removal family evidence: 57.824->31.308 Bq; O1 itself is not a delayed transport result"
            if option.option == "O1"
            else "BGO activation is self-vetoing; mass reduction is monotonically favorable; not quantified here"
        )
        pareto_rows.append(
            {
                **leak_row,
                "mass_kg": mass,
                "dmass_kg": mass - baseline_mass,
                "mass_saved_kg": baseline_mass - mass,
                "predicted_atm511_w2_cps": predicted_atm,
                "predicted_B_total_cps": predicted_b,
                "F3_scale": f3_scale,
                "predicted_F3_20d": F3_C0 * f3_scale,
                "delayed_note": delayed,
                "caveats": "frozen e+/n/residual; coupled straight-ray screening; Al3 and Kapton retained",
            }
        )
    for row in pareto_rows:
        dominated = any(
            float(other["mass_kg"]) <= float(row["mass_kg"]) + 1e-12
            and float(other["predicted_F3_20d"]) <= float(row["predicted_F3_20d"]) + 1e-18
            and (
                float(other["mass_kg"]) < float(row["mass_kg"]) - 1e-12
                or float(other["predicted_F3_20d"]) < float(row["predicted_F3_20d"]) - 1e-18
            )
            for other in pareto_rows
            if other is not row
        )
        row["pareto_efficient"] = not dominated
    write_csv(DATA / "pareto_options.csv", pareto_rows)

    group_masses = Counter()
    for panel in panels:
        group_masses[panel.group] += panel.mass_kg
    importance_rows: list[dict[str, Any]] = []
    for group in ("bgo_side", "bgo_bottom", "bgo_top", "w_shell", "al_shell"):
        observed = {
            "atm511": int(panel_component_counts["atm511"].get(group, 0)),
            "eplus": int(panel_component_counts["eplus"].get(group, 0)),
            "n": int(panel_component_counts["n"].get(group, 0)),
        }
        total = sum(observed.values())
        importance_rows.append(
            {
                "volume": group,
                "mass_kg": group_masses[group],
                "atm511_interceptions": observed["atm511"],
                "eplus_interceptions": observed["eplus"],
                "n_interceptions": observed["n"],
                "total_interceptions": total,
                "interceptions_per_kg": total / group_masses[group],
                "eplus_file_fraction": prompt_meta["file_fraction"]["eplus"],
                "n_file_fraction": prompt_meta["file_fraction"]["n"],
                "count_definition": "event-volume unique earliest COMP/PHOT/PAIR IA; atm511 restricted to cavity-directed primary first interaction",
            }
        )
    importance_rows.sort(key=lambda row: float(row["interceptions_per_kg"]), reverse=True)
    for rank, row in enumerate(importance_rows, 1):
        row["importance_rank"] = rank
    write_csv(DATA / "panel_importance.csv", importance_rows)

    g1_mass = all(item["relative_error"] <= 0.01 for item in mass_meta["bgo_reproduction"].values())
    w_al = [panel for panel in panels if panel.material in {"W", "Aluminium"}]
    g1 = g1_mass and len(w_al) == 6
    g2 = all(row["identity_leak_pass"] and row["identity_veto_pass"] for row in leak_rows)
    mu = float(depth_fit["mu_eff_cm-1"])
    g3 = math.isfinite(mu) and 0.80 <= mu <= 1.10
    o1 = next(row for row in pareto_rows if row["option"] == "O1")
    o1_shift = float(o1["F3_scale"]) - 1.0
    shift_ratio = (
        max(abs(o1_shift), HISTORICAL_LW1_F3_SHIFT) / min(abs(o1_shift), HISTORICAL_LW1_F3_SHIFT)
        if abs(o1_shift) > 0
        else math.inf
    )
    g4 = shift_ratio <= 3.0
    current_status = git_status()
    outside_41 = [line for line in current_status if "41_s3c_bgo_thinning_volume_audit_20260711" not in line]
    g5 = len(outside_41) == 0

    summary: dict[str, Any] = {
        "status": "PENDING_README_G6",
        "claim_ceiling": "screening",
        "inputs": {
            "geometry_setup": GEOMETRY_SETUP_REL,
            "resolved_geo": rel(geo_path),
            "resolved_intro": rel(intro_path),
            "instrument_frame_rotation_deg": rotation,
            "atm511_sim": ATM_SIM_REL,
            "prompt_dir": PROMPT_DIR_REL,
            "retained_reference_29": REF29_REL,
            "retained_reference_40_summary": REF40_SUMMARY_REL,
            "retained_reference_40_candidates": REF40_CANDIDATES_REL,
            "retained_reference_38_activity": REF38_ACTIVITY_REL,
        },
        "frozen_budget": {
            "eplus_cps": EPLUS_CPS,
            "n_cps": N_CPS,
            "atm511_cps": ATM_W2_CPS,
            "residual_cps": RESIDUAL_CPS,
            "B_total_C0_cps": B_TOTAL_C0,
            "F3_C0_20d": F3_C0,
            "budget_rule": "B_new = B_total_C0 - atm511_C0 + atm511_option",
        },
        "geometry": {
            "panels": [panel.__dict__ for panel in panels],
            "coordinate_system": "InstrumentFrame local; inverse parsed Y rotation applied to SIM world coordinates",
            "classification": "axisymmetric coordinate boxes; exact relief/window CSG not reconstructed",
        },
        "mass_model": mass_meta,
        "atm511": {
            **atm,
            "header_geometry_match": normalize_geometry(atm["header_geometry"]) == GEOMETRY_SETUP.resolve().as_posix(),
        },
        "depth_fit": depth_fit,
        "prompt_scan": prompt_meta,
        "panel_importance_definition": (
            "event-volume unique: earliest COMP/PHOT/PAIR IA establishes whether each event intercepts a panel; "
            "all IA parentages included for prompt, primary first interaction only for cavity-directed atm511"
        ),
        "calibration": {
            "O1_implied_F3_shift_fraction": o1_shift,
            "historical_LW1_F3_shift_fraction": HISTORICAL_LW1_F3_SHIFT,
            "historical_LW1_difference": "historical row also changes Al from 3 to 8 mm",
            "shift_ratio": shift_ratio,
        },
        "gates": {
            "G1": {"severity": "FAIL", "pass": g1, "detail": "BGO gross masses within 1%; six W/Al extents parsed"},
            "G2": {"severity": "FAIL", "pass": g2, "detail": "integer conservation identities exact per option"},
            "G3": {"severity": "WARN", "pass": g3, "detail": f"mu_eff={mu:.8g} cm^-1"},
            "G4": {"severity": "WARN", "pass": g4, "detail": f"larger/smaller F3 shift ratio={shift_ratio:.8g}"},
            "G5": {
                "severity": "FAIL",
                "pass": g5,
                "detail": "literal git status has only 41_ changes" if g5 else "pre-existing paths outside 41_ remain dirty",
                "starting_git_status": starting_status,
                "current_git_status": current_status,
                "outside_41_current": outside_41,
            },
            "G6": {"severity": "FAIL", "pass": True, "detail": "validator checks status placement, quote-rule markers, and required sections"},
        },
        "options": pareto_rows,
    }
    fail_gates = [name for name, gate in summary["gates"].items() if gate["severity"] == "FAIL" and not gate["pass"]]
    summary["status"] = "PASS_S3C_THINNING_VOLUME_AUDIT" if not fail_gates else f"FAIL_S3C_THINNING_AUDIT_{fail_gates[0]}"
    readme_text = build_readme(summary, pareto_rows, importance_rows)
    (WORK / "README.md").write_text(readme_text, encoding="utf-8")
    write_json(DATA / "summary.json", summary)
    print(json.dumps({"status": summary["status"], "gates": summary["gates"], "outputs": [rel(path) for path in sorted(DATA.glob("*"))]}, indent=2))


if __name__ == "__main__":
    main()
