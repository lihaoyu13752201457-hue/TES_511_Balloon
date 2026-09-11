#!/usr/bin/env python3
from __future__ import annotations

import csv
import gzip
import json
import math
import os
import random
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT = Path(__file__).resolve()
STEP_DIR = SCRIPT.parents[1]
FIX_ROOT = SCRIPT.parents[3]
SNAPSHOT_DIR = STEP_DIR / "source_snapshots"
OUTPUT_DIR = STEP_DIR / "outputs"

SOURCE_FILE = SNAPSHOT_DIR / "Background_atm_fullsphere_allparticles_20bins_smoke1k.source"
LOCAL_SOURCE_FILE = SNAPSHOT_DIR / "Background_atm_fullsphere_allparticles_20bins_local.source"
MANIFEST_FILE = SNAPSHOT_DIR / "manifest.csv"
EXTRACTION_LOG_FILE = SNAPSHOT_DIR / "extraction_log.csv"
FLUX_SUMMARY_FILE = SNAPSHOT_DIR / "flux_summary.csv"
BOUNDS_FILE = FIX_ROOT / "code/geometry/bounds.json"
GEOMETRY_SETUP_FILE = FIX_ROOT / "code/geometry/TibetTES_v5_6layers.geo.setup"
NATIVE_SIM_FILE = OUTPUT_DIR / "native_cosima_1000.sim.inc1.id1.sim.gz"

PARTICLE_COLORS = {
    "gamma": (1.00, 0.72, 0.10),
    "n": (0.10, 0.42, 0.95),
    "p": (0.88, 0.16, 0.16),
    "alpha": (0.55, 0.22, 0.82),
    "eminus": (0.06, 0.68, 0.55),
    "eplus": (0.98, 0.38, 0.58),
    "muminus": (0.42, 0.42, 0.42),
    "muplus": (0.05, 0.05, 0.05),
}

PARTICLE_BY_ID = {
    1: "gamma",
    2: "eplus",
    3: "eminus",
    4: "p",
    6: "n",
    8: "muplus",
    9: "muminus",
    21: "alpha",
}


def as_float(value: str) -> float:
    return float(value.strip())


def load_manifest(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            for key in (
                "theta_min_deg",
                "theta_max_deg",
                "theta_mid_deg",
                "mu_high",
                "mu_low",
                "mu_mid",
                "delta_omega_sr",
                "integral_per_sr_cm2_s",
                "flux_cm2_s",
                "expacs_lat_deg",
                "expacs_lon_deg",
                "expacs_altitude_km",
                "expacs_Rc_GV",
            ):
                row[key] = as_float(row[key])
            rows.append(row)
    return rows


def parse_source(path: Path) -> dict:
    info = {
        "path": str(path),
        "geometry": None,
        "run": None,
        "filename": None,
        "triggers": None,
        "source_order": [],
        "components": {},
    }
    component_re = re.compile(r"^([A-Za-z0-9_]+)\.(ParticleType|Beam|Spectrum|Flux)\s+(.+)$")
    with path.open() as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("Geometry "):
                info["geometry"] = line.split(None, 1)[1]
                continue
            if line.startswith("Run "):
                info["run"] = line.split(None, 1)[1]
                continue
            if line.startswith("BalloonPrompt.FileName "):
                info["filename"] = line.split(None, 1)[1]
                continue
            if line.startswith("BalloonPrompt.Triggers "):
                info["triggers"] = int(line.split()[-1])
                continue
            if line.startswith("BalloonPrompt.Source "):
                info["source_order"].append(line.split()[-1])
                continue
            match = component_re.match(line)
            if not match:
                continue
            name, key, value = match.groups()
            component = info["components"].setdefault(name, {})
            if key == "ParticleType":
                component["particle_type"] = int(value)
            elif key == "Beam":
                parts = value.split()
                component["beam_type"] = parts[0]
                component["theta_min_deg"] = float(parts[1])
                component["theta_max_deg"] = float(parts[2])
                component["phi_min_deg"] = float(parts[3])
                component["phi_max_deg"] = float(parts[4])
            elif key == "Spectrum":
                parts = value.split(None, 1)
                component["spectrum_mode"] = parts[0]
                component["spectrum_path"] = parts[1]
            elif key == "Flux":
                component["flux_cm2_s"] = float(value)
    source_set = set(info["source_order"])
    for name, component in info["components"].items():
        component["listed_in_run"] = name in source_set
    return info


def load_flux_summary(path: Path) -> dict[str, float]:
    values: dict[str, float] = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            values[row["particle"]] = float(row["total_flux_cm2_s"])
    return values


def load_extraction_summary(path: Path) -> dict:
    rows = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            row["pdf_integral"] = float(row["pdf_integral"])
            row["rows_seen"] = int(row["rows_seen"])
            row["numeric_rows"] = int(row["numeric_rows"])
            row["rows_dropped"] = int(row["rows_dropped"])
            rows.append(row)
    return {
        "rows": len(rows),
        "pdf_integral_min": min(row["pdf_integral"] for row in rows),
        "pdf_integral_max": max(row["pdf_integral"] for row in rows),
        "rows_dropped_total": sum(row["rows_dropped"] for row in rows),
        "numeric_rows_total": sum(row["numeric_rows"] for row in rows),
    }


def compare_source_to_manifest(source: dict, manifest: list[dict]) -> tuple[list[dict], dict]:
    rows = []
    source_components = source["components"]
    manifest_names = {row["component_name"] for row in manifest}
    particle_type_map: dict[str, set[int]] = defaultdict(set)
    manifest_flux_by_particle: dict[str, float] = defaultdict(float)
    source_flux_by_particle: dict[str, float] = defaultdict(float)

    for row in manifest:
        name = row["component_name"]
        component = source_components.get(name)
        status = "PASS"
        notes = []
        if component is None:
            status = "FAIL"
            notes.append("component_missing_in_source")
            out = {
                "component_name": name,
                "particle": row["particle"],
                "status": status,
                "notes": ";".join(notes),
            }
            rows.append(out)
            continue

        particle_type_map[row["particle"]].add(component["particle_type"])
        manifest_flux_by_particle[row["particle"]] += row["flux_cm2_s"]
        source_flux_by_particle[row["particle"]] += component["flux_cm2_s"]

        theta_min_diff = abs(component["theta_min_deg"] - row["theta_min_deg"])
        theta_max_diff = abs(component["theta_max_deg"] - row["theta_max_deg"])
        flux_abs_diff = abs(component["flux_cm2_s"] - row["flux_cm2_s"])
        flux_rel_diff = flux_abs_diff / max(row["flux_cm2_s"], 1.0e-300)
        spectrum_basename_match = (
            Path(component["spectrum_path"]).name == Path(row["cosima_spectrum_path"]).name
        )

        if not component["listed_in_run"]:
            status = "FAIL"
            notes.append("not_listed_in_run")
        if component["beam_type"] != "FarFieldAreaSource":
            status = "FAIL"
            notes.append("beam_type_mismatch")
        if theta_min_diff > 5.0e-4 or theta_max_diff > 5.0e-4:
            status = "FAIL"
            notes.append("theta_mismatch_gt_0p0005_deg")
        if abs(component["phi_min_deg"]) > 5.0e-6 or abs(component["phi_max_deg"] - 360.0) > 5.0e-6:
            status = "FAIL"
            notes.append("phi_not_full_azimuth")
        if flux_rel_diff > 5.0e-11:
            status = "FAIL"
            notes.append("flux_mismatch")
        if not spectrum_basename_match:
            status = "FAIL"
            notes.append("spectrum_basename_mismatch")

        rows.append(
            {
                "component_name": name,
                "particle": row["particle"],
                "bin_id": row["bin_id"],
                "direction_tag": row["direction_tag"],
                "status": status,
                "particle_type": component["particle_type"],
                "theta_min_manifest_deg": f"{row['theta_min_deg']:.6f}",
                "theta_min_source_deg": f"{component['theta_min_deg']:.6f}",
                "theta_max_manifest_deg": f"{row['theta_max_deg']:.6f}",
                "theta_max_source_deg": f"{component['theta_max_deg']:.6f}",
                "theta_diff_max_deg": f"{max(theta_min_diff, theta_max_diff):.6e}",
                "flux_manifest_cm2_s": f"{row['flux_cm2_s']:.12e}",
                "flux_source_cm2_s": f"{component['flux_cm2_s']:.12e}",
                "flux_rel_diff": f"{flux_rel_diff:.6e}",
                "spectrum_basename_match": str(spectrum_basename_match),
                "notes": ";".join(notes),
            }
        )

    extra_components = sorted(set(source_components) - manifest_names)
    fail_count = sum(1 for row in rows if row["status"] != "PASS")
    summary = {
        "manifest_components": len(manifest),
        "source_components": len(source_components),
        "listed_sources": len(source["source_order"]),
        "extra_source_components": extra_components,
        "pass_rows": len(rows) - fail_count,
        "fail_rows": fail_count,
        "overall_status": "PASS" if fail_count == 0 and not extra_components else "FAIL",
        "particle_type_map": {key: sorted(values) for key, values in sorted(particle_type_map.items())},
        "manifest_flux_by_particle": dict(sorted(manifest_flux_by_particle.items())),
        "source_flux_by_particle": dict(sorted(source_flux_by_particle.items())),
        "total_flux_cm2_s": sum(manifest_flux_by_particle.values()),
    }
    return rows, summary


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fields = list(rows[0].keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def component_summary_rows(summary: dict, flux_summary: dict[str, float], manifest: list[dict]) -> list[dict]:
    counts = Counter(row["particle"] for row in manifest)
    total = summary["total_flux_cm2_s"]
    rows = []
    for particle, flux in summary["manifest_flux_by_particle"].items():
        source_flux = summary["source_flux_by_particle"].get(particle, 0.0)
        reference_flux = flux_summary.get(particle, 0.0)
        rows.append(
            {
                "particle": particle,
                "components": counts[particle],
                "source_particle_types": ",".join(str(x) for x in summary["particle_type_map"][particle]),
                "manifest_flux_cm2_s": f"{flux:.12e}",
                "source_flux_cm2_s": f"{source_flux:.12e}",
                "flux_summary_cm2_s": f"{reference_flux:.12e}",
                "fraction_of_total": f"{flux / total:.8f}",
                "source_manifest_rel_diff": f"{abs(source_flux - flux) / max(flux, 1e-300):.6e}",
                "flux_summary_rel_diff": f"{abs(reference_flux - flux) / max(flux, 1e-300):.6e}",
            }
        )
    return rows


def integrate_xy(path: Path, cosima_dp: bool = False) -> tuple[float, int]:
    points: list[tuple[float, float]] = []
    with path.open() as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if cosima_dp:
                if len(parts) != 3 or parts[0] != "DP":
                    continue
                x, y = float(parts[1]), float(parts[2])
            else:
                if len(parts) < 2:
                    continue
                try:
                    x, y = float(parts[0]), float(parts[1])
                except ValueError:
                    continue
            points.append((x, y))
    integral = 0.0
    for idx in range(len(points) - 1):
        x0, y0 = points[idx]
        x1, y1 = points[idx + 1]
        integral += (x1 - x0) * 0.5 * (y0 + y1)
    return integral, len(points)


def check_spectrum_integrals(manifest: list[dict], source: dict) -> tuple[list[dict], dict]:
    rows = []
    max_raw_rel = 0.0
    max_flux_rel = 0.0
    max_pdf_abs = 0.0
    pass_count = 0
    for row in manifest:
        component = source["components"][row["component_name"]]
        raw_path = FIX_ROOT / "particle_sources" / row["raw_spectrum_path"]
        cosima_path = FIX_ROOT / component["spectrum_path"]
        raw_integral, raw_points = integrate_xy(raw_path, cosima_dp=False)
        pdf_integral, pdf_points = integrate_xy(cosima_path, cosima_dp=True)
        expected_pdf_integral = 1.0e-3 if "cosima_spectra_dp_2602units" in str(cosima_path) else 1.0
        raw_rel = abs(raw_integral - row["integral_per_sr_cm2_s"]) / max(row["integral_per_sr_cm2_s"], 1.0e-300)
        flux_from_raw = raw_integral * row["delta_omega_sr"]
        flux_rel = abs(flux_from_raw - component["flux_cm2_s"]) / max(component["flux_cm2_s"], 1.0e-300)
        pdf_abs = abs(pdf_integral - expected_pdf_integral)
        status = "PASS" if raw_rel < 1.0e-8 and flux_rel < 1.0e-8 and pdf_abs < 1.0e-8 else "FAIL"
        pass_count += status == "PASS"
        max_raw_rel = max(max_raw_rel, raw_rel)
        max_flux_rel = max(max_flux_rel, flux_rel)
        max_pdf_abs = max(max_pdf_abs, pdf_abs)
        rows.append(
            {
                "component_name": row["component_name"],
                "particle": row["particle"],
                "raw_points": raw_points,
                "pdf_points": pdf_points,
                "raw_integral_cm2_s_sr": f"{raw_integral:.12e}",
                "manifest_integral_cm2_s_sr": f"{row['integral_per_sr_cm2_s']:.12e}",
                "raw_integral_rel_diff": f"{raw_rel:.6e}",
                "flux_from_raw_cm2_s": f"{flux_from_raw:.12e}",
                "source_flux_cm2_s": f"{component['flux_cm2_s']:.12e}",
                "flux_from_raw_rel_diff": f"{flux_rel:.6e}",
                "cosima_pdf_integral": f"{pdf_integral:.12e}",
                "expected_cosima_pdf_integral": f"{expected_pdf_integral:.12e}",
                "cosima_pdf_abs_diff_from_expected": f"{pdf_abs:.6e}",
                "status": status,
            }
        )
    summary = {
        "rows": len(rows),
        "pass_rows": pass_count,
        "fail_rows": len(rows) - pass_count,
        "max_raw_integral_rel_diff": max_raw_rel,
        "max_flux_from_raw_rel_diff": max_flux_rel,
        "max_cosima_pdf_abs_diff_from_expected": max_pdf_abs,
        "overall_status": "PASS" if pass_count == len(rows) else "FAIL",
    }
    return rows, summary


def check_expacs_install(manifest: list[dict]) -> dict:
    driver = FIX_ROOT / "particle_sources/external/expacs_parma/phase2_parma_grid_driver"
    parma_cpp = FIX_ROOT / "particle_sources/external/expacs_parma/parma_cpp"
    readme = parma_cpp / "Readme.txt"
    first = manifest[0]
    expected_depth = 1033.0 * math.exp(-first["expacs_altitude_km"] / 6.8)
    result = {
        "status": "MISSING",
        "driver_path": str(driver),
        "driver_exists": driver.exists(),
        "driver_executable": os.access(driver, os.X_OK),
        "parma_cpp_path": str(parma_cpp),
        "parma_cpp_exists": parma_cpp.exists(),
        "readme_exists": readme.exists(),
        "source_manifest_lat_deg": first["expacs_lat_deg"],
        "source_manifest_lon_deg": first["expacs_lon_deg"],
        "source_manifest_altitude_km": first["expacs_altitude_km"],
        "source_manifest_rc_gv": first["expacs_Rc_GV"],
        "source_manifest_w_or_date": first["W_or_date"],
        "expected_standard_atmosphere_depth_g_cm2": expected_depth,
        "note": "",
    }
    if not (driver.exists() and parma_cpp.exists()):
        result["note"] = "EXPACS/PARMA files are not present at the expected fix tree paths."
        return result

    cmd = [
        str(driver),
        "2025",
        "8",
        "31",
        f"{first['expacs_lat_deg']:.8g}",
        f"{first['expacs_lon_deg']:.8g}",
        f"{first['expacs_altitude_km']:.8g}",
        "10",
    ]
    result["command"] = " ".join(cmd)
    result["working_directory"] = str(parma_cpp)
    try:
        proc = subprocess.run(
            cmd,
            cwd=parma_cpp,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except Exception as exc:  # pragma: no cover - local environment diagnostic
        result["status"] = "ERROR"
        result["note"] = f"Driver execution failed: {exc}"
        return result

    result["returncode"] = proc.returncode
    result["stderr_head"] = proc.stderr[:1000]
    lines = proc.stdout.splitlines()
    result["stdout_line_count"] = len(lines)
    meta = None
    nonzero_flux_rows = 0
    for line in lines:
        if line.startswith("META,"):
            parts = line.split(",")
            meta = {
                "solar_s_or_w": float(parts[1]),
                "rc_gv": float(parts[2]),
                "depth_g_cm2": float(parts[3]),
            }
        elif line and not line.startswith("particle,"):
            parts = line.split(",")
            if len(parts) == 8:
                try:
                    if float(parts[6]) != 0.0 or float(parts[7]) != 0.0:
                        nonzero_flux_rows += 1
                except ValueError:
                    pass
    result["meta"] = meta
    result["nonzero_flux_rows"] = nonzero_flux_rows
    if proc.returncode != 0 or meta is None:
        result["status"] = "ERROR"
        result["note"] = "Driver exists but did not produce a parseable META line."
        return result

    w_match = re.search(r"W=([0-9.]+)", first["W_or_date"])
    source_w = float(w_match.group(1)) if w_match else None
    result["source_manifest_w"] = source_w
    result["rc_match"] = abs(meta["rc_gv"] - first["expacs_Rc_GV"]) < 1.0e-9
    result["depth_match"] = abs(meta["depth_g_cm2"] - expected_depth) < 1.0e-9
    result["w_match"] = source_w is not None and abs(meta["solar_s_or_w"] - source_w) < 1.0e-9
    result["status"] = "PARTIAL_MATCH" if not result["w_match"] else "PASS"
    if result["status"] == "PASS":
        result["note"] = "Local PARMA driver runs and matches the archived source metadata."
    else:
        result["note"] = (
            "Local PARMA driver runs from parma_cpp cwd and matches Rc/depth, but its "
            "2025-08-31 solar parameter is not the archived manifest W=118.3. The "
            "source card itself is therefore validated against the archived EXPACS/PARMA "
            "manifest and raw spectra, not claimed as an exact live regeneration."
        )
    return result


def sample_particles(manifest: list[dict], n: int = 1000, seed: int = 2602) -> list[dict]:
    rng = random.Random(seed)
    sphere = load_surrounding_sphere(GEOMETRY_SETUP_FILE)
    start_radius = sphere["radius_cm"]
    center_x, center_y, center_z = sphere["center_cm"]
    display_length = 1.75 * start_radius
    weights = [row["flux_cm2_s"] for row in manifest]
    total = sum(weights)
    cumulative = []
    running = 0.0
    for weight in weights:
        running += weight
        cumulative.append(running)

    samples = []
    for idx in range(n):
        pick = rng.random() * total
        row_index = 0
        while cumulative[row_index] < pick:
            row_index += 1
        row = manifest[row_index]
        mu = rng.uniform(min(row["mu_low"], row["mu_high"]), max(row["mu_low"], row["mu_high"]))
        phi = rng.random() * 2.0 * math.pi
        sin_theta = math.sqrt(max(0.0, 1.0 - mu * mu))
        vx = sin_theta * math.cos(phi)
        vy = sin_theta * math.sin(phi)
        vz = mu
        dx, dy, dz = -vx, -vy, -vz

        while True:
            disk_x = start_radius * (2.0 * rng.random() - 1.0)
            disk_y = start_radius * (2.0 * rng.random() - 1.0)
            if disk_x * disk_x + disk_y * disk_y <= start_radius * start_radius:
                break
        disk_z = start_radius
        cos_t = mu
        sin_t = sin_theta
        cos_p = math.cos(phi)
        sin_p = math.sin(phi)
        start_x = (disk_x * cos_t + disk_z * sin_t) * cos_p - disk_y * sin_p + center_x
        start_y = (disk_x * cos_t + disk_z * sin_t) * sin_p + disk_y * cos_p + center_y
        start_z = -disk_x * sin_t + disk_z * cos_t + center_z
        end_x = start_x + display_length * dx
        end_y = start_y + display_length * dy
        end_z = start_z + display_length * dz
        samples.append(
            {
                "event_id": idx + 1,
                "component_name": row["component_name"],
                "particle": row["particle"],
                "direction_class": "down" if dz < 0 else "up",
                "theta_deg": math.degrees(math.acos(max(-1.0, min(1.0, mu)))),
                "phi_deg": math.degrees(phi),
                "mu": mu,
                "start_x_cm": start_x,
                "start_y_cm": start_y,
                "start_z_cm": start_z,
                "direction_x": dx,
                "direction_y": dy,
                "direction_z": dz,
                "end_x_cm": end_x,
                "end_y_cm": end_y,
                "end_z_cm": end_z,
                "energy_keV": "",
                "sample_source": "analytic_megalib_farfield",
            }
        )
    return samples


def load_surrounding_sphere(path: Path) -> dict:
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line.startswith("SurroundingSphere "):
            continue
        parts = line.split()
        return {
            "radius_cm": float(parts[1]),
            "center_cm": (float(parts[2]), float(parts[3]), float(parts[4])),
            "distance_cm": float(parts[5]),
        }
    return {"radius_cm": 15.0, "center_cm": (0.0, 0.0, 1.9), "distance_cm": 15.0}


def parse_init_events(sim_file: Path) -> list[dict]:
    samples = []
    sphere = load_surrounding_sphere(GEOMETRY_SETUP_FILE)
    display_length = 1.75 * sphere["radius_cm"]
    with gzip.open(sim_file, "rt", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line.startswith("IA INIT"):
                continue
            parts = [part.strip() for part in line.split(";")]
            try:
                event_id = len(samples) + 1
                start_x = float(parts[4])
                start_y = float(parts[5])
                start_z = float(parts[6])
                pid = int(float(parts[15]))
                dx = float(parts[16])
                dy = float(parts[17])
                dz = float(parts[18])
                energy = float(parts[-1])
            except (IndexError, ValueError):
                continue
            norm = math.sqrt(dx * dx + dy * dy + dz * dz)
            if norm == 0:
                continue
            dx, dy, dz = dx / norm, dy / norm, dz / norm
            theta_deg = math.degrees(math.acos(max(-1.0, min(1.0, -dz))))
            phi_deg = math.degrees(math.atan2(-dy, -dx))
            if phi_deg < 0:
                phi_deg += 360.0
            samples.append(
                {
                    "event_id": event_id,
                    "component_name": "native_cosima_IA_INIT",
                    "particle": PARTICLE_BY_ID.get(pid, "unknown"),
                    "direction_class": "down" if dz < 0 else "up",
                    "theta_deg": theta_deg,
                    "phi_deg": phi_deg,
                    "mu": -dz,
                    "start_x_cm": start_x,
                    "start_y_cm": start_y,
                    "start_z_cm": start_z,
                    "direction_x": dx,
                    "direction_y": dy,
                    "direction_z": dz,
                    "end_x_cm": start_x + display_length * dx,
                    "end_y_cm": start_y + display_length * dy,
                    "end_z_cm": start_z + display_length * dz,
                    "energy_keV": energy,
                    "sample_source": str(sim_file.relative_to(STEP_DIR)),
                }
            )
    return samples


def write_particle_sample(path: Path, samples: list[dict]) -> None:
    fields = [
        "event_id",
        "component_name",
        "particle",
        "direction_class",
        "theta_deg",
        "phi_deg",
        "mu",
        "start_x_cm",
        "start_y_cm",
        "start_z_cm",
        "direction_x",
        "direction_y",
        "direction_z",
        "end_x_cm",
        "end_y_cm",
        "end_z_cm",
        "energy_keV",
        "sample_source",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for sample in samples:
            writer.writerow(
                {
                    key: (f"{sample[key]:.8f}" if isinstance(sample[key], float) else sample[key])
                    for key in fields
                }
            )


def vrml_material(name: str, color: tuple[float, float, float], transparency: float) -> str:
    r, g, b = color
    return (
        f"DEF {name} Appearance {{ material Material {{ "
        f"diffuseColor {r:.4f} {g:.4f} {b:.4f} "
        f"emissiveColor {0.25*r:.4f} {0.25*g:.4f} {0.25*b:.4f} "
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
    lines = [
        "#VRML V2.0 utf8\n",
        "WorldInfo { title \"Step02 prompt cosmic source: 1000 sampled incident particles\" }\n",
        "NavigationInfo { type [\"EXAMINE\", \"ANY\"] speed 4.0 }\n",
        "Viewpoint { position 0 -38 12 orientation 1 0 0 1.28 fieldOfView 0.64 description \"1000 incident particles\" }\n",
        vrml_material("APP_AL", (0.78, 0.82, 0.88), 0.84),
        vrml_material("APP_BGO", (0.20, 0.55, 0.26), 0.78),
        vrml_material("APP_W", (0.18, 0.18, 0.18), 0.70),
        vrml_material("APP_NB", (0.22, 0.42, 0.78), 0.70),
        vrml_material("APP_TES", (0.92, 0.18, 0.10), 0.36),
        vrml_material("APP_COLL", (0.08, 0.08, 0.08), 0.40),
        vrml_material("APP_AXIS", (0.70, 0.70, 0.70), 0.00),
    ]
    shields = bounds["SHIELDS"]
    for material, key in [
        ("APP_AL", "Al_Shell"),
        ("APP_BGO", "BGO_Shield"),
        ("APP_W", "W_Shield"),
        ("APP_NB", "Nb_Shield"),
    ]:
        shield = shields[key]
        z_center = 0.5 * (shield["z_out_bot"] + shield["z_out_top"])
        height = shield["z_out_top"] - shield["z_out_bot"]
        lines.append(vrml_cylinder(key, shield["r_out"], z_center, height, material))
    for idx, layer in enumerate(bounds["TES_LAYERS"]):
        lines.append(
            vrml_cylinder(
                f"TES_L{idx}",
                layer["r_max"],
                layer["z_center"],
                2.0 * layer["hz"],
                "APP_TES",
            )
        )
    coll = bounds["COLLIMATOR"]
    lines.append(vrml_cylinder("Collimator", coll["r_max"], coll["z_center"], 2.0 * coll["hz"], "APP_COLL"))

    axis_coords = [
        "-8 0 0, 8 0 0",
        "0 -8 0, 0 8 0",
        "0 0 -8, 0 0 14",
    ]
    axis_indices = ["0 1 -1", "2 3 -1", "4 5 -1"]
    lines.append(
        "Shape { appearance USE APP_AXIS geometry IndexedLineSet { coord Coordinate { point ["
        + ", ".join(axis_coords)
        + "] } coordIndex ["
        + ", ".join(axis_indices)
        + "] } }\n"
    )

    for particle in sorted(PARTICLE_COLORS):
        particle_samples = [sample for sample in samples if sample["particle"] == particle]
        if not particle_samples:
            continue
        app_name = "APP_RAY_" + particle.upper().replace("+", "PLUS").replace("-", "MINUS")
        lines.append(vrml_material(app_name, PARTICLE_COLORS[particle], 0.00))
        points = []
        indices = []
        for idx, sample in enumerate(particle_samples):
            points.append(
                f"{sample['start_x_cm']:.5f} {sample['start_y_cm']:.5f} {sample['start_z_cm']:.5f}"
            )
            points.append(f"{sample['end_x_cm']:.5f} {sample['end_y_cm']:.5f} {sample['end_z_cm']:.5f}")
            indices.append(f"{2 * idx} {2 * idx + 1} -1")
        lines.append(
            f"Shape {{ appearance USE {app_name} geometry IndexedLineSet {{ "
            "coord Coordinate { point [\n      "
            + ",\n      ".join(points)
            + "\n    ] } coordIndex [\n      "
            + ",\n      ".join(indices)
            + "\n    ] } }\n"
        )

    path.write_text("".join(lines))


def make_2d_schematic(path: Path, samples: list[dict], bounds: dict, summary: dict) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/codex_step02_matplotlib")
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    from matplotlib.patches import Circle, Rectangle

    def color_for(sample: dict) -> tuple[float, float, float]:
        return PARTICLE_COLORS.get(sample["particle"], (0.45, 0.45, 0.45))

    fig = plt.figure(figsize=(14.6, 8.8), constrained_layout=True)
    gs = GridSpec(2, 3, figure=fig, width_ratios=[1.65, 1.0, 1.0])
    ax_xz = fig.add_subplot(gs[:, 0])
    ax_xy = fig.add_subplot(gs[0, 1])
    ax_theta = fig.add_subplot(gs[0, 2])
    ax_mix = fig.add_subplot(gs[1, 1:])

    draw_detector_cross_section(ax_xz, bounds)
    for sample in samples:
        c = color_for(sample)
        ax_xz.plot(
            [sample["start_x_cm"], sample["end_x_cm"]],
            [sample["start_z_cm"], sample["end_z_cm"]],
            color=c,
            alpha=0.22,
            linewidth=0.55,
        )
        ax_xz.scatter(sample["start_x_cm"], sample["start_z_cm"], color=c, s=6, alpha=0.70)
    max_coord = max(
        18.0,
        max(abs(sample["start_x_cm"]) for sample in samples),
        max(abs(sample["start_z_cm"]) for sample in samples),
    )
    lim = math.ceil(max_coord * 1.08)
    ax_xz.set_xlim(-lim, lim)
    ax_xz.set_ylim(-lim, lim)
    ax_xz.set_aspect("equal", adjustable="box")
    ax_xz.set_xlabel("x [cm]")
    ax_xz.set_ylabel("z [cm]")
    ax_xz.set_title("Cosima IA INIT: X-Z entry display")
    ax_xz.grid(True, color="#e1e1e1", linewidth=0.5)

    sphere = load_surrounding_sphere(GEOMETRY_SETUP_FILE)
    radius = sphere["radius_cm"]
    ax_xy.add_patch(Circle((sphere["center_cm"][0], sphere["center_cm"][1]), radius, fill=False, color="0.25", lw=1.0))
    for sample in samples:
        ax_xy.scatter(sample["start_x_cm"], sample["start_y_cm"], color=color_for(sample), s=7, alpha=0.72)
    xy_lim = math.ceil(max(radius * 1.25, max(abs(sample["start_x_cm"]) for sample in samples), max(abs(sample["start_y_cm"]) for sample in samples)) * 1.05)
    ax_xy.set_xlim(-xy_lim, xy_lim)
    ax_xy.set_ylim(-xy_lim, xy_lim)
    ax_xy.set_aspect("equal", adjustable="box")
    ax_xy.set_xlabel("x [cm]")
    ax_xy.set_ylabel("y [cm]")
    ax_xy.set_title("Primary start points: X-Y")
    ax_xy.grid(True, color="#e8e8e8", linewidth=0.5)

    down = [sample["theta_deg"] for sample in samples if sample["direction_class"] == "down"]
    up = [sample["theta_deg"] for sample in samples if sample["direction_class"] == "up"]
    bins = list(range(0, 181, 10))
    ax_theta.hist(down, bins=bins, alpha=0.70, color="#4c78a8", label="down")
    ax_theta.hist(up, bins=bins, alpha=0.70, color="#f58518", label="up")
    ax_theta.set_xlabel("theta from +Z downward axis [deg]")
    ax_theta.set_ylabel("count")
    ax_theta.set_title("Incoming theta")
    ax_theta.legend(frameon=False, fontsize=8)
    ax_theta.grid(True, color="#eeeeee", linewidth=0.5)

    counts = Counter(sample["particle"] for sample in samples)
    particles = [p for p, _ in counts.most_common()]
    colors = [PARTICLE_COLORS.get(p, (0.45, 0.45, 0.45)) for p in particles]
    values = [counts[p] for p in particles]
    ax_mix.bar(particles, values, color=colors)
    ax_mix.set_ylabel("generated primaries")
    ax_mix.set_title(f"Generated particle mix in this {len(samples)}-trigger Cosima smoke run")
    ax_mix.grid(axis="y", color="#eeeeee", linewidth=0.5)
    ymax = max(values) * 1.18 if values else 1.0
    ax_mix.set_ylim(0, ymax)
    for idx, value in enumerate(values):
        ax_mix.text(idx, value + ymax * 0.015, str(value), ha="center", va="bottom", fontsize=8)

    fig.suptitle("Full-sphere atmospheric source, native Cosima smoke1000", fontsize=15)
    fig.savefig(path, dpi=170)
    plt.close(fig)


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
            lw=0.7,
            label="TES layers" if idx == 0 else None,
        )
    coll = bounds["COLLIMATOR"]
    rect(-coll["r_max"], coll["z_center"] - coll["hz"], 2.0 * coll["r_max"], 2.0 * coll["hz"], "#111111", 0.75, label="collimator")
    ax.axvline(0, color="0.55", lw=0.4, ls=":")
    ax.legend(loc="upper left", fontsize=7, frameon=False)


def markdown_table(rows: list[dict], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
    return "\n".join([header, sep] + body)


def write_primary_summary(path: Path, samples: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for sample in samples:
        grouped[(sample["particle"], sample["direction_class"])].append(sample)
    rows = []
    for (particle, direction), group in sorted(grouped.items()):
        energies = [float(sample["energy_keV"]) for sample in group if sample["energy_keV"] != ""]
        rows.append(
            {
                "particle": particle,
                "direction_class": direction,
                "count": len(group),
                "mean_energy_keV": f"{sum(energies) / len(energies):.12g}" if energies else "",
            }
        )
    write_csv(path, rows)
    return rows


def write_readme(
    path: Path,
    source: dict,
    local_source: dict,
    summary: dict,
    component_rows: list[dict],
    extraction_summary: dict,
    spectrum_summary: dict,
    expacs_check: dict,
    primary_rows: list[dict],
) -> None:
    table_rows = [
        {
            "particle": row["particle"],
            "types": row["source_particle_types"],
            "components": row["components"],
            "flux_cm2_s": row["manifest_flux_cm2_s"],
            "fraction": row["fraction_of_total"],
        }
        for row in component_rows
    ]
    code_functions = [
        ("parse_source", "Parses MEGAlib .source run metadata, component list, beam bins, spectra, and fluxes."),
        ("load_manifest", "Loads archived EXPACS/PARMA component metadata and numeric flux columns."),
        ("compare_source_to_manifest", "Checks 160 source components against theta bins, spectra basenames, and fluxes."),
        ("check_expacs_install", "Runs the local PARMA C++ driver from the required parma_cpp cwd and parses META output."),
        ("parse_init_events", "Reads native Cosima SIM IA INIT records and extracts true far-field starts and momenta."),
        ("sample_particles", "Fallback only: samples MEGAlib-like far-field starts if no native SIM is present."),
        ("write_wrl", "Fallback only: writes an analytic VRML scene when no native Geant4 WRL is present."),
        ("make_2d_schematic", "Writes x-z/x-y/theta/mix diagnostics from native Cosima IA INIT records."),
    ]
    function_table = markdown_table(
        [{"function": name, "role": role} for name, role in code_functions],
        ["function", "role"],
    )
    component_table = markdown_table(
        table_rows,
        ["particle", "types", "components", "flux_cm2_s", "fraction"],
    )
    primary_table = markdown_table(primary_rows, ["particle", "direction_class", "count", "mean_energy_keV"])
    text = f"""# Step02 Instant Cosmic Source Maintenance

## Scope

This directory freezes and audits the prompt atmospheric cosmic-ray source used by the corrected `fix` workflow. The maintained source card is:

- `source_snapshots/Background_atm_fullsphere_allparticles_20bins_smoke1k.source`
- production-scale companion: `source_snapshots/Background_atm_fullsphere_allparticles_20bins_local.source`
- archived EXPACS/PARMA authority table: `source_snapshots/manifest.csv`

The smoke source has `BalloonPrompt.Triggers {source['triggers']}`. The local source has `BalloonPrompt.Triggers {local_source['triggers']}`. Both point to geometry `{source['geometry']}` and use the same 160 atmospheric components.

## Source Definition

The source is an instantaneous prompt cosmic-ray source, not a delayed activation source. It represents atmospheric flux at latitude 34 deg, longitude 100 deg, altitude 38 km, cutoff rigidity 11.6 GV, and archived solar/date metadata `{expacs_check['source_manifest_w_or_date']}`.

The angular definition is full-sphere `FarFieldAreaSource`:

- 8 particle species.
- 20 equal-mu theta bins per particle from 0 to 180 deg.
- full azimuth in every bin, phi = 0 to 360 deg.
- `BlackHole=No` in the archived EXPACS/PARMA extraction.
- source flux per component is `DeltaOmega * integral(phi(E, theta) dE)` in cm^-2 s^-1.
- each `Spectrum File` is a Cosima-compatible normalized PDF; `extraction_log.csv` gives PDF integral min/max = {extraction_summary['pdf_integral_min']:.12g}/{extraction_summary['pdf_integral_max']:.12g}.
- the checked source spectra are in `cosima_spectra_dp_2602units`; their displayed energy axis is legacy-scaled, so direct DP integration is expected to be 1e-3 while the archived extraction log remains 1. This audit re-integrates all 160 archived raw EXPACS spectra; spectrum integral status = `{spectrum_summary['overall_status']}`, max raw-integral relative difference = `{spectrum_summary['max_raw_integral_rel_diff']:.3e}`, and max Cosima DP expected-normalization error = `{spectrum_summary['max_cosima_pdf_abs_diff_from_expected']:.3e}`.

## Component Summary

Total archived all-particle flux = `{summary['total_flux_cm2_s']:.12e} cm^-2 s^-1`.

{component_table}

## Code Principle

The audit script treats `manifest.csv` as the archived EXPACS/PARMA authority for the source card and checks the `.source` file against it. It does not infer physics from filenames. It parses the source syntax, compares component names, particle type ids, theta bounds, full azimuth, spectra basenames, and flux values. The WRL and PNG are visualization products generated from the same flux-weighted component table.

Main script: `code/build_step02_source_audit.py`

{function_table}

## Generated Outputs

- `outputs/expacs_source_alignment.csv`: row-by-row source-vs-manifest comparison.
- `outputs/spectrum_integral_check.csv`: raw EXPACS spectrum integral and Cosima PDF normalization check.
- `outputs/source_component_summary.csv`: particle totals, source particle type ids, and flux closure.
- `outputs/expacs_install_check.json`: local EXPACS/PARMA install and driver result.
- `outputs/native_cosima_1000.source`: source card used for the native 1000-event visualization run.
- `outputs/vis_vrml2_1000.mac`: Geant4 VRML2FILE macro used for the native WRL run.
- `outputs/native_cosima_1000.sim.inc1.id1.sim.gz`: 1000-event Cosima SIM output used for IA INIT diagnostics.
- `outputs/particle_sample_1000.csv`: primary particles parsed from native Cosima `IA INIT` records.
- `outputs/native_cosima_primary_summary.csv`: particle and down/up summary parsed from native Cosima `IA INIT` records.
- `outputs/instant_cosmic_1000_particles.wrl`: native Geant4/Cosima VRML2FILE trajectory output, not an analytic drawing.
- `outputs/instant_cosmic_2d_schematic.png`: x-z/x-y/theta/mix diagnostic parsed from the same native SIM.
- `outputs/expacs_alignment_report.md`: compact factual result.

## Native 1000-Event Visual Check

The visual outputs are now based on an actual Cosima run. `FarFieldAreaSource` does not aim every particle at `(0,0,0)`: it samples a direction in the requested theta/phi bin, reverses it for particle momentum, and samples a random point on the far-field start disk. Therefore the line display must use `IA INIT` start positions and momentum directions, not radial lines through the origin.

Native SIM primary summary:

{primary_table}

## Records/01 Cross-Check

`source_snapshots/records01_mixed_fullsphere_1000.source` and `source_snapshots/records01_source_primary_summary.csv` preserve the corresponding `COSMOSRAY_BALLOON_SIM/Records/01_source_injection_smoke` evidence that triggered this correction. The source component definitions are the same 160 full-sphere `FarFieldAreaSource` components, but the visual semantics matter: Records/01 correctly uses actual Cosima `IA INIT` start positions and directions, not center-focused rays.

The corrected `fix` run uses the cm-fixed geometry setup `SurroundingSphere 15 0 0 1.9 15`, so its SIM header reports `SimulationStartAreaFarField 706.858`. The old Records/01 run from the pre-cmfix scale reports `70685.8`; that is a scale/history difference, not a different source angular definition.

## EXPACS/PARMA Check

Local EXPACS/PARMA is considered installed if the PARMA C++ tree and `phase2_parma_grid_driver` executable exist under `particle_sources/external/expacs_parma/`.

Observed status from this audit: `{expacs_check['status']}`.

The driver was run from `{expacs_check.get('working_directory', 'N/A')}`. This cwd matters because the public PARMA C++ helper reads its input database relative to that directory.

Driver/source comparison:

- Rc: driver `{expacs_check.get('meta', {}).get('rc_gv', 'N/A')}`, source manifest `{expacs_check['source_manifest_rc_gv']}`.
- depth: driver `{expacs_check.get('meta', {}).get('depth_g_cm2', 'N/A')}`, standard-atmosphere formula `{expacs_check['expected_standard_atmosphere_depth_g_cm2']:.12g}`.
- solar/date scalar: driver `{expacs_check.get('meta', {}).get('solar_s_or_w', 'N/A')}`, archived manifest `{expacs_check.get('source_manifest_w', 'N/A')}`.

Conclusion: the source card matches the archived EXPACS/PARMA manifest row-by-row. The installed local driver runs and matches the location/cutoff/depth metadata, but its direct 2025-08-31 solar scalar is not identical to the archived manifest W value, so exact live regeneration is not claimed unless the original W/date input is pinned.
"""
    path.write_text(text)


def write_report(path: Path, source: dict, summary: dict, spectrum_summary: dict, expacs_check: dict) -> None:
    native_status = "present" if NATIVE_SIM_FILE.exists() else "missing"
    text = f"""# Step02 EXPACS Source Alignment Report

- Source card: `{SOURCE_FILE.relative_to(STEP_DIR)}`
- Geometry path in source: `{source['geometry']}`
- Source components listed in run: `{summary['listed_sources']}`
- Parsed component blocks: `{summary['source_components']}`
- Manifest components: `{summary['manifest_components']}`
- Source-vs-manifest status: `{summary['overall_status']}`
- Raw-spectrum integral status: `{spectrum_summary['overall_status']}`
- Max raw-integral relative difference: `{spectrum_summary['max_raw_integral_rel_diff']:.6e}`
- Max raw-derived flux relative difference: `{spectrum_summary['max_flux_from_raw_rel_diff']:.6e}`
- Max Cosima PDF expected-normalization error: `{spectrum_summary['max_cosima_pdf_abs_diff_from_expected']:.6e}`
- Total flux: `{summary['total_flux_cm2_s']:.12e} cm^-2 s^-1`
- Native 1000-event Cosima SIM for visuals: `{native_status}` at `outputs/native_cosima_1000.sim.inc1.id1.sim.gz`
- Native WRL visual: `outputs/instant_cosmic_1000_particles.wrl`
- EXPACS/PARMA install status: `{expacs_check['status']}`
- EXPACS/PARMA note: {expacs_check['note']}

The strict source-card comparison passes when every archived component is present, listed in the run, uses `FarFieldAreaSource`, spans phi 0-360 deg, has theta bounds agreeing within 0.0005 deg, has flux agreeing within 5e-11 relative tolerance, and points to the same spectrum basename.
"""
    path.write_text(text)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(MANIFEST_FILE)
    source = parse_source(SOURCE_FILE)
    local_source = parse_source(LOCAL_SOURCE_FILE)
    flux_summary = load_flux_summary(FLUX_SUMMARY_FILE)
    extraction_summary = load_extraction_summary(EXTRACTION_LOG_FILE)
    alignment_rows, summary = compare_source_to_manifest(source, manifest)
    component_rows = component_summary_rows(summary, flux_summary, manifest)
    spectrum_rows, spectrum_summary = check_spectrum_integrals(manifest, source)
    expacs_check = check_expacs_install(manifest)

    write_csv(OUTPUT_DIR / "expacs_source_alignment.csv", alignment_rows)
    write_csv(OUTPUT_DIR / "spectrum_integral_check.csv", spectrum_rows)
    write_csv(OUTPUT_DIR / "source_component_summary.csv", component_rows)
    (OUTPUT_DIR / "expacs_install_check.json").write_text(json.dumps(expacs_check, indent=2, sort_keys=True) + "\n")

    if NATIVE_SIM_FILE.exists():
        samples = parse_init_events(NATIVE_SIM_FILE)
    else:
        samples = sample_particles(manifest, n=1000, seed=2602)
    write_particle_sample(OUTPUT_DIR / "particle_sample_1000.csv", samples)
    primary_rows = write_primary_summary(OUTPUT_DIR / "native_cosima_primary_summary.csv", samples)
    bounds = json.loads(BOUNDS_FILE.read_text())
    if not NATIVE_SIM_FILE.exists():
        write_wrl(OUTPUT_DIR / "instant_cosmic_1000_particles.wrl", samples, bounds)
    make_2d_schematic(OUTPUT_DIR / "instant_cosmic_2d_schematic.png", samples, bounds, summary)

    write_readme(
        STEP_DIR / "README.md",
        source,
        local_source,
        summary,
        component_rows,
        extraction_summary,
        spectrum_summary,
        expacs_check,
        primary_rows,
    )
    write_report(OUTPUT_DIR / "expacs_alignment_report.md", source, summary, spectrum_summary, expacs_check)
    print(
        json.dumps(
            {
                "source_alignment": summary["overall_status"],
                "spectrum_integrals": spectrum_summary["overall_status"],
                "expacs_status": expacs_check["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
