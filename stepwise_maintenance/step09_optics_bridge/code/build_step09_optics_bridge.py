#!/usr/bin/env python3
"""Build the Step09 opticsim phase-space to MEGAlib EventList bridge."""

from __future__ import annotations

import csv
import gzip
import json
import math
import os
import re
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = ROOT / "stepwise_maintenance" / "step09_optics_bridge"
PROFILE = os.environ.get("STEP09_OPTICS_PROFILE", "f9m").strip().lower()
if PROFILE not in {"f9m", "f10m_a1", "f10m_a1_v3p5"}:
    raise SystemExit(f"unsupported STEP09_OPTICS_PROFILE={PROFILE!r}; expected f9m, f10m_a1, or f10m_a1_v3p5")

OUT = STEP_DIR / ("outputs" if PROFILE == "f9m" else f"outputs_{PROFILE}")
EVENTLIST_DIR = OUT / "eventlists"
RUN_CONFIG_DIR = OUT / "run_configs"
FIG_DIR = OUT / "figures"

if PROFILE in {"f10m_a1", "f10m_a1_v3p5"}:
    RUN_DIR = ROOT / "stepwise_maintenance" / "step04_opticsim" / "outputs" / "opticsim_laue_bfull_f10m_a1_r2_3seed"
    NAME = "Opticsim_laue_f10m_a1_v3p5_centerfinger" if PROFILE == "f10m_a1_v3p5" else "Opticsim_laue_f10m_a1_new_geo_re"
else:
    RUN_DIR = ROOT / "stepwise_maintenance" / "step04_opticsim" / "outputs" / "opticsim_laue_bfull_xopmap_real"
    NAME = "Opticsim_laue_new_geo_re"

# Physical focused-signal handoff: the tracked diffracted gammas that actually
# cross the focal plane (focal_crossings.csv, source_tag laue_bfull_diffracted),
# NOT the analytic phase_space.csv projection. The projection writes one row per
# diffraction interaction and ignores the EM attenuation / Compton scatter of the
# diffracted photon as it exits the Ge crystal, so it overcounts the focused flux
# (15963 projected rows vs 12566 tracked diffracted focal rows in the current
# 511-line run) and hides the scattered tail.
FOCAL_CROSSINGS = RUN_DIR / "focal_crossings.csv"
PHASE_SPACE = RUN_DIR / "phase_space.csv"  # retained reference only; not bridged
if PROFILE == "f10m_a1_v3p5":
    BOUNDS = ROOT / "geo_refer" / "DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json"
    GEOMETRY = "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
    GEOM_VALIDATION = ROOT / "outputs" / "geometry" / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy" / "geometry_proxy_validation.json"
else:
    BOUNDS = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "bounds.json"
    GEOMETRY = "outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup"
    GEOM_VALIDATION = None

EVENTLIST = EVENTLIST_DIR / f"{NAME}.eventlist.dat"
SOURCE = RUN_CONFIG_DIR / f"{NAME}.source"
SMOKE_SOURCE = RUN_CONFIG_DIR / f"{NAME}_smoke1000.source"
SMOKE_LOG = OUT / "cosima_smoke1000.log"
SMOKE_SIM = ROOT / "runs" / "step09_optics_bridge" / f"{NAME}_smoke1000.inc1.id1.sim.gz"
FULL_LOG = OUT / "cosima_full37194.log"
FULL_SIM = ROOT / "runs" / "step09_optics_bridge" / f"{NAME}.inc1.id1.sim.gz"
SMOKE_PREFIX = f"runs/step09_optics_bridge/{NAME}_smoke1000"
FULL_PREFIX = f"runs/step09_optics_bridge/{NAME}"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def ensure_dirs() -> None:
    for path in (EVENTLIST_DIR, RUN_CONFIG_DIR, FIG_DIR, ROOT / "runs" / "step09_optics_bridge"):
        path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(x: float, nd: int = 6) -> str:
    if not math.isfinite(float(x)):
        return "nan"
    x = float(x)
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.{nd}e}"
    return f"{x:.{nd}g}"


def beam_authority(bounds: dict[str, Any]) -> dict[str, Any]:
    if PROFILE == "f10m_a1_v3p5":
        comps = {c["name"]: c for c in bounds.get("COMPONENTS", [])}
        be = comps["Win_Be_Vacuum_150um_side"]["params"]
        geom_validation = load_json(GEOM_VALIDATION) if GEOM_VALIDATION is not None else {}
        frame = geom_validation.get("geometry_extents", {}).get("instrument_frame", {})
        rotation = frame.get("rotation_deg") or [0.0, 45.0, 0.0]
        return {
            "axis_policy": "v3p5_side_entry_tilt45",
            "x_plane_cm": float(be["x_center_cm"]),
            "axis_y_cm": float(be.get("axis_y_cm", 0.0)),
            "axis_z_cm": float(be.get("axis_z_cm", -5.2)),
            "be_radius_cm": float(be.get("r_cm", 1.898)),
            "xy_scale_cm_per_opticsim_mm": 0.1,
            "instrument_rotation_y_deg": float(rotation[1]),
            "side_window_look_elevation_deg": float(frame.get("side_window_look_elevation_deg", 45.0)),
            "incoming_photon_global_axis": frame.get("incoming_photon_global_axis", [math.sqrt(0.5), 0.0, -math.sqrt(0.5)]),
        }
    meta = bounds.get("META", {})
    return {
        "axis_policy": "legacy_z_entry",
        "z_plane_cm": float(meta.get("science_beam_z_cm", 16.051)),
        "be_radius_cm": float(meta.get("be_window_radius_reference_cm", 1.898)),
        "xy_scale_cm_per_opticsim_mm": 0.1,
    }


def particle_type(row: dict[str, str]) -> int:
    if row.get("particle_type"):
        return int(row["particle_type"])
    if row.get("pdg_encoding") and int(row["pdg_encoding"]) == 22:
        return 1
    if row.get("particle_name", "").lower() == "gamma":
        return 1
    return 1


def norm_dir(ux: float, uy: float, uz: float) -> tuple[float, float, float]:
    n = math.sqrt(ux * ux + uy * uy + uz * uz)
    if n <= 0.0 or not math.isfinite(n):
        raise ValueError("bad direction norm")
    return ux / n, uy / n, uz / n


def rotate_y(values: tuple[float, float, float], angle_deg: float) -> tuple[float, float, float]:
    x, y, z = values
    angle = math.radians(angle_deg)
    c = math.cos(angle)
    s = math.sin(angle)
    return c * x + s * z, y, -s * x + c * z


def dot(a: list[float] | tuple[float, float, float], b: list[float] | tuple[float, float, float]) -> float:
    return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1]) + float(a[2]) * float(b[2])


def select_diffracted_focal_crossings(
    path: Path, authority: dict[str, Any]
) -> tuple[list[dict[str, str]], int, int]:
    """Select the physically focused science signal: tracked diffracted gammas
    crossing the focal plane, restricted to those landing inside the Be window.

    The tracked diffracted set carries the EM exit attenuation (absorbed photons
    never appear) and the real spatial distribution (a ~5% Compton-scattered tail
    reaches large radius). Photons outside the Be window hit the window mount /
    structure rather than the TES, so they are not part of the focused signal and
    are reported separately instead of being projected into the spot.
    """
    scale = authority["xy_scale_cm_per_opticsim_mm"]
    be = authority["be_radius_cm"]
    diffracted = [r for r in read_rows(path) if r.get("source_tag") == "laue_bfull_diffracted"]
    within: list[dict[str, str]] = []
    outside = 0
    for r in diffracted:
        rr = math.hypot(float(r["x_mm"]) * scale, float(r["y_mm"]) * scale)
        if rr <= be + 1.0e-9:
            within.append(r)
        else:
            outside += 1
    return within, len(diffracted), outside


def write_eventlist(rows: list[dict[str, str]], authority: dict[str, Any]) -> dict[str, Any]:
    stats = {
        "rows_seen": len(rows),
        "rows_written": 0,
        "rows_skipped": 0,
        "energy_min_keV": None,
        "energy_max_keV": None,
        "max_radius_cm": 0.0,
        "direction_uz_min": None,
        "direction_uz_max": None,
        "direction_axis_dot_min": None,
        "direction_axis_dot_max": None,
    }
    radii_cm: list[float] = []
    incoming_axis = authority.get("incoming_photon_global_axis", [0.0, 0.0, -1.0])
    with EVENTLIST.open("w", encoding="utf-8", newline="") as handle:
        out_id = 0
        for row in rows:
            try:
                weight = float(row.get("weight", "1"))
                if weight <= 0.0:
                    stats["rows_skipped"] += 1
                    continue
                e = float(row["E_keV"])
                transverse_1 = float(row["x_mm"]) * authority["xy_scale_cm_per_opticsim_mm"]
                transverse_2 = float(row["y_mm"]) * authority["xy_scale_cm_per_opticsim_mm"]
                if authority["axis_policy"] == "v3p5_side_entry_tilt45":
                    local_point = (
                        float(authority["x_plane_cm"]),
                        float(authority["axis_y_cm"]) + transverse_1,
                        float(authority["axis_z_cm"]) + transverse_2,
                    )
                    local_dir = norm_dir(float(row["uz"]), float(row["ux"]), float(row["uy"]))
                    x, y, z = rotate_y(local_point, float(authority["instrument_rotation_y_deg"]))
                    ux, uy, uz = norm_dir(*rotate_y(local_dir, float(authority["instrument_rotation_y_deg"])))
                else:
                    x = transverse_1
                    y = transverse_2
                    z = authority["z_plane_cm"]
                    ux, uy, uz = norm_dir(float(row["ux"]), float(row["uy"]), -float(row["uz"]))
                ptype = particle_type(row)
            except Exception:
                stats["rows_skipped"] += 1
                continue
            event_time = out_id * 1.0e-9
            fields = [
                out_id,
                0,
                ptype,
                0,
                f"{event_time:.12e}",
                f"{x:.12g}",
                f"{y:.12g}",
                f"{z:.12g}",
                f"{ux:.12g}",
                f"{uy:.12g}",
                f"{uz:.12g}",
                "0",
                "0",
                "0",
                f"{e:.12g}",
            ]
            handle.write(" ".join(str(v) for v in fields) + "\n")
            stats["rows_written"] += 1
            stats["energy_min_keV"] = e if stats["energy_min_keV"] is None else min(stats["energy_min_keV"], e)
            stats["energy_max_keV"] = e if stats["energy_max_keV"] is None else max(stats["energy_max_keV"], e)
            r_cm = math.hypot(transverse_1, transverse_2)
            radii_cm.append(r_cm)
            stats["max_radius_cm"] = max(stats["max_radius_cm"], r_cm)
            stats["direction_uz_min"] = uz if stats["direction_uz_min"] is None else min(stats["direction_uz_min"], uz)
            stats["direction_uz_max"] = uz if stats["direction_uz_max"] is None else max(stats["direction_uz_max"], uz)
            axis_dot = dot((ux, uy, uz), incoming_axis)
            stats["direction_axis_dot_min"] = axis_dot if stats["direction_axis_dot_min"] is None else min(stats["direction_axis_dot_min"], axis_dot)
            stats["direction_axis_dot_max"] = axis_dot if stats["direction_axis_dot_max"] is None else max(stats["direction_axis_dot_max"], axis_dot)
            out_id += 1
    if radii_cm:
        radii_cm.sort()
        for key, frac in (("r50_cm", 0.50), ("r90_cm", 0.90), ("r95_cm", 0.95), ("r99_cm", 0.99)):
            idx = min(len(radii_cm) - 1, max(0, math.ceil(frac * len(radii_cm)) - 1))
            stats[key] = radii_cm[idx]
    return stats


def source_text(name: str, triggers: int, output_prefix: str, eventlist_ref: str, seed: int) -> str:
    source_name = f"{name}_PhaseSpace"
    return f"""# Auto-generated by Step09 optics bridge.
# Replays Step04 B-FULL Laue focal-plane phase space at the selected detector Be-window plane.
# Claim control: EventList bridge source, not an optics-mass activation transport.

Version 1
Geometry {GEOMETRY}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {seed}

Run {name}
{name}.FileName {output_prefix}
{name}.Triggers {triggers}
{name}.Source {source_name}

{source_name}.EventList {eventlist_ref}
"""


def write_sources(n_rows: int) -> None:
    eventlist_ref = rel(EVENTLIST)
    SOURCE.write_text(source_text(NAME, n_rows, FULL_PREFIX, eventlist_ref, 5119001), encoding="utf-8")
    SMOKE_SOURCE.write_text(source_text(f"{NAME}_smoke1000", min(1000, n_rows), SMOKE_PREFIX, eventlist_ref, 5119002), encoding="utf-8")


def inspect_transport(source: Path, sim: Path, log: Path) -> dict[str, Any]:
    out: dict[str, Any] = {
        "source": rel(source),
        "sim": rel(sim),
        "sim_exists": sim.exists(),
        "log": rel(log),
        "log_exists": log.exists(),
    }
    if sim.exists():
        out["sim_size_bytes"] = sim.stat().st_size
        try:
            n_se = 0
            n_id = 0
            n_ts = 0
            te_s = None
            geometry = ""
            with gzip.open(sim, "rt", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    if line.startswith("SE"):
                        n_se += 1
                    elif line.startswith("ID"):
                        n_id += 1
                    elif line.startswith("TS "):
                        n_ts += 1
                    elif line.startswith("TE "):
                        vals = line.split()
                        if len(vals) > 1:
                            te_s = float(vals[1])
                    elif line.startswith("Geometry "):
                        geometry = line.strip().split(" ", 1)[1]
            out["stored_events"] = n_se
            out["id_events"] = n_id
            out["time_start_records"] = n_ts
            out["observation_time_from_sim_s"] = te_s
            out["geometry"] = geometry
        except Exception as exc:
            out["stored_events_error"] = repr(exc)
    if log.exists():
        text = log.read_text(encoding="utf-8", errors="ignore")
        out["log_tail"] = "\n".join(text.splitlines()[-12:])
        obs = None
        for line in text.splitlines():
            if "Observation time:" in line:
                vals = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
                if vals:
                    obs = float(vals[0])
        out["observation_time_s"] = obs
    return out


def inspect_smoke() -> dict[str, Any]:
    return inspect_transport(SMOKE_SOURCE, SMOKE_SIM, SMOKE_LOG)


def inspect_full() -> dict[str, Any]:
    return inspect_transport(SOURCE, FULL_SIM, FULL_LOG)


def plot_phase_space(rows: list[dict[str, str]], authority: dict[str, Any]) -> None:
    x = np.asarray([float(r["x_mm"]) * authority["xy_scale_cm_per_opticsim_mm"] for r in rows])
    y = np.asarray([float(r["y_mm"]) * authority["xy_scale_cm_per_opticsim_mm"] for r in rows])
    e = np.asarray([float(r["E_keV"]) for r in rows])
    fig, ax = plt.subplots(figsize=(5.4, 5.0))
    sc = ax.scatter(x, y, c=e, s=5, cmap="viridis", alpha=0.75)
    circ = plt.Circle((0.0, 0.0), authority["be_radius_cm"], fill=False, color="#D62728", lw=1.2, label="Be radius")
    ax.add_patch(circ)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("transverse axis 1 at injection plane (cm)")
    ax.set_ylabel("transverse axis 2 at injection plane (cm)")
    ax.set_title("Step09 B-FULL Laue EventList focal spot at selected Be plane")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right")
    fig.colorbar(sc, ax=ax, label="Energy (keV)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "eventlist_phase_space_xy.png", dpi=220)
    plt.close(fig)


def write_readme(summary: dict[str, Any]) -> None:
    bridge = summary["bridge"]
    smoke = summary["smoke_transport"]
    full = summary["full_transport"]
    focus_response = OUT / "detector_coupled_focus_response.json"
    lines = [
        f"# Step09 Opticsim EventList Bridge ({PROFILE})",
        "",
        f"Status: `{summary['status']}`.",
        "",
        "This step converts the current Step04 B-FULL Laue tracked diffracted focal-plane crossings (`focal_crossings.csv`, `source_tag=laue_bfull_diffracted`, restricted to the Be window) into a MEGAlib EventList source at the selected detector Be-window plane. The analytic `phase_space.csv` projection is NOT used because it overcounts the focused flux (it ignores the EM exit attenuation of the diffracted beam).",
        "",
        "## Coordinate Policy",
        "",
        f"- axis policy: `{bridge['axis_policy']}`.",
        f"- transverse scale: `{bridge['xy_scale_cm_per_opticsim_mm']} cm per opticsim mm`.",
        f"- max EventList radius: `{fmt(bridge['max_radius_cm'])} cm`.",
        f"- EventList r95: `{fmt(bridge.get('r95_cm', float('nan')))} cm`.",
        f"- Be radius: `{bridge['be_radius_cm']} cm`.",
    ]
    if bridge["axis_policy"] == "v3p5_side_entry_tilt45":
        lines.extend(
            [
                f"- local Be x plane: `{bridge['x_plane_cm']} cm`; local axis center `(y,z)=({bridge['axis_y_cm']}, {bridge['axis_z_cm']}) cm`.",
                f"- instrument rotation: `0 {bridge['instrument_rotation_y_deg']} 0` degrees.",
                f"- side-window look elevation: `{fmt(bridge['side_window_look_elevation_deg'])} deg`.",
                "- direction policy: opticsim longitudinal direction maps to detector local `+x`, then the full EventList is rotated with the v3p5 `InstrumentFrame`.",
            ]
        )
    else:
        lines.extend(
            [
                f"- z plane: `{bridge['z_plane_cm']} cm`.",
                "- direction policy: keep x/y direction and reverse z, so opticsim rays are injected toward the detector.",
            ]
        )
    lines.extend(
        [
            "",
            "## Smoke Transport",
            "",
            f"- source: `{smoke['source']}`",
            f"- sim exists: `{smoke['sim_exists']}`",
            f"- stored events: `{smoke.get('stored_events', '')}`",
            "",
            "## Full Transport",
            "",
            f"- source: `{full['source']}`",
            f"- sim exists: `{full['sim_exists']}`",
            f"- stored events: `{full.get('stored_events', '')}`",
            f"- ID events: `{full.get('id_events', '')}`",
            f"- observation time from SIM: `{full.get('observation_time_from_sim_s', '')} s`",
            "",
        ]
    )
    if PROFILE == "f9m" and focus_response.exists():
        focus = load_json(focus_response)
        w1 = focus.get("window_checks", {}).get("W1_design_passband", {})
        w2 = focus.get("window_checks", {}).get("W2_511_pm_420eV", {})
        spatial = focus.get("spatial_checks", {})
        lines.extend(
            [
                "## Full Detector-Coupled Response",
                "",
                f"- full focused source: `{rel(SOURCE)}`",
                "- full focused SIM: `runs/step09_optics_bridge/Opticsim_laue_new_geo_re.inc1.id1.sim.gz`",
                f"- parsed response: `{rel(focus_response)}`",
                f"- status: `{focus.get('status', '')}`",
                f"- W1 final signal at `1e-4 ph cm^-2 s^-1`: `{fmt(w1.get('signal_both_cps_at_reference_flux', float('nan')))} cps`; W1 final non-X-ray background: `{fmt(w1.get('background_both_cps', float('nan')))} cps`.",
                f"- W2 final signal at `1e-4 ph cm^-2 s^-1`: `{fmt(w2.get('signal_both_cps_at_reference_flux', float('nan')))} cps`; W2 final non-X-ray background: `{fmt(w2.get('background_both_cps', float('nan')))} cps`.",
                f"- detector-coupled W2 signal radii: `r90={fmt(spatial.get('signal_radius_r90_cm', float('nan')))} cm`, `r99={fmt(spatial.get('signal_radius_r99_cm', float('nan')))} cm`, `rmax={fmt(spatial.get('signal_radius_max_cm', float('nan')))} cm`.",
                f"- headline spatial cut is `spot_r90`: background `{fmt(spatial.get('spot_r90_background_cps', float('nan')))} cps`, `Z20d={fmt(spatial.get('spot_r90_Z20d', float('nan')))}`.",
                "",
            ]
        )
    lines.extend(
        [
        "## Outputs",
        "",
        f"- EventList: `{rel(EVENTLIST)}`",
        f"- full source: `{rel(SOURCE)}`",
        f"- smoke source: `{rel(SMOKE_SOURCE)}`",
        f"- manifest: `{rel(OUT / 'step09_optics_bridge_summary.json')}`",
    ]
    )
    if PROFILE == "f9m" and focus_response.exists():
        lines.append(f"- detector-coupled response: `{rel(focus_response)}`")
    lines.extend(
        [
        "",
        "## Rebuild",
        "",
        "```bash",
        "python3 stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py"
        if PROFILE == "f9m"
        else f"STEP09_OPTICS_PROFILE={PROFILE} python3 stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py",
        "```",
        "",
        "Smoke transport command:",
        "",
        "```bash",
        f"/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima {rel(SMOKE_SOURCE)}",
        "```",
        ]
    )
    readme_path = STEP_DIR / "README.md" if PROFILE == "f9m" else OUT / "README.md"
    readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_summary(stats: dict[str, Any], authority: dict[str, float]) -> dict[str, Any]:
    smoke = inspect_smoke()
    full = inspect_full()
    transported = bool(smoke.get("sim_exists")) and int(smoke.get("stored_events", 0) or 0) > 0
    full_transported = (
        bool(full.get("sim_exists"))
        and int(full.get("stored_events", 0) or 0) == int(stats["rows_written"])
        and int(full.get("id_events", 0) or 0) == int(stats["rows_written"])
    )
    if authority["axis_policy"] == "v3p5_side_entry_tilt45":
        direction_ok = stats["direction_axis_dot_min"] is not None and stats["direction_axis_dot_min"] > 0.999
    else:
        direction_ok = stats["direction_uz_max"] < 0.0
    ok_bridge = (
        stats["rows_written"] > 0
        and stats["max_radius_cm"] <= authority["be_radius_cm"] + 1.0e-9
        and direction_ok
    )
    if full_transported and transported and ok_bridge:
        status = "PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED"
    elif transported and ok_bridge:
        status = "PASS_EVENTLIST_BRIDGE_SMOKE_TRANSPORTED"
    else:
        status = "PASS_EVENTLIST_BRIDGE_GENERATED_SMOKE_PENDING"
    summary = {
        "status": status,
        "claim_level": "L1_OPTICS_EVENTLIST_BRIDGE",
        "profile": PROFILE,
        "scope": "Step04 B-FULL Laue tracked diffracted focal-plane crossings (EM-attenuated, within the Be window) replayed as a MEGAlib EventList at the selected detector injection plane. Uses focal_crossings.csv, not the analytic phase_space.csv projection, so the focused flux is not overcounted. This does not add optics-mass prompt/delayed activation.",
        "optics_model": "B-FULL external per-ring XOP/CRYSTAL rocking-curve map; standard Geant4 EM competing with finite-MFP Laue diffraction; handoff = tracked diffracted focal crossings",
        "inputs": {"focal_crossings": rel(FOCAL_CROSSINGS), "geometry": GEOMETRY, "bounds": rel(BOUNDS)},
        "bridge": {
            **stats,
            **{k: v for k, v in authority.items() if k != "incoming_photon_global_axis"},
            "be_radius_cm": authority["be_radius_cm"],
            "xy_scale_cm_per_opticsim_mm": authority["xy_scale_cm_per_opticsim_mm"],
            "eventlist": rel(EVENTLIST),
            "source": rel(SOURCE),
            "smoke_source": rel(SMOKE_SOURCE),
            "incoming_photon_global_axis": authority.get("incoming_photon_global_axis"),
            "coordinate_policy": "v3p5 side-entry local +x with InstrumentFrame tilt" if authority["axis_policy"] == "v3p5_side_entry_tilt45" else "x/y opticsim mm scaled to cm; z at science_beam_z_cm; direction reverse_z",
        },
        "smoke_transport": smoke,
        "full_transport": full,
        "checks": {
            "rows_written_positive": stats["rows_written"] > 0,
            "max_radius_within_be": stats["max_radius_cm"] <= authority["be_radius_cm"] + 1.0e-9,
            "directions_point_to_detector": direction_ok,
            "smoke_transport_done": transported,
            "full_transport_done": full_transported,
        },
    }
    write_json(OUT / "step09_optics_bridge_summary.json", summary)
    return summary


def main() -> int:
    ensure_dirs()
    bounds = load_json(BOUNDS)
    authority = beam_authority(bounds)
    rows, n_diffracted_total, n_scattered_outside_be = select_diffracted_focal_crossings(FOCAL_CROSSINGS, authority)
    stats = write_eventlist(rows, authority)
    stats["n_diffracted_focal_total"] = n_diffracted_total
    stats["n_within_be_window"] = len(rows)
    stats["n_scattered_outside_be"] = n_scattered_outside_be
    write_sources(int(stats["rows_written"]))
    plot_phase_space(rows, authority)
    summary = build_summary(stats, authority)
    write_readme(summary)
    print(json.dumps({"status": summary["status"], "claim_level": summary["claim_level"], "checks": summary["checks"], "out": rel(OUT)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
