from __future__ import annotations

import csv
import json
import math
import re
import shutil
from pathlib import Path

from .probabilities import darwin_hamilton_mosaic_probabilities

REQUIRED_COLUMNS = (
    "delta_theta_rad",
    "reflectivity",
    "transmittivity",
    "absorption",
    "source_tool",
    "source_version",
)


def import_external_curve(
    input_path: str | Path,
    out_dir: str | Path,
    *,
    energy_keV: float,
    d_spacing_A: float,
    thickness_mm: float,
    output_name: str = "ge111_511keV_rocking_curve.csv",
) -> dict[str, object]:
    input_path = Path(input_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / output_name
    shutil.copyfile(input_path, output_path)
    summary = summarize_external_curve(output_path, energy_keV=energy_keV, d_spacing_A=d_spacing_A, thickness_mm=thickness_mm)
    summary["curve_csv"] = str(output_path)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def convert_diffpat_to_external_curve(
    diffpat_dat: str | Path,
    output_path: str | Path,
    *,
    thickness_mm: float,
    diffpat_par: str | Path | None = None,
    source_version: str | None = None,
) -> dict[str, object]:
    """Convert CRYSTAL/XOP diff_pat output to the local external-curve CSV schema."""
    dat_path = Path(diffpat_dat)
    par_info = _read_diffpat_par(diffpat_par) if diffpat_par is not None else {}
    mu_cm_inv = float(par_info.get("absorption_mu_cm_inv", 0.0))
    gamma0 = abs(float(par_info.get("gamma0", 1.0)))
    path_length_cm = (thickness_mm / 10.0) / gamma0
    absorption = 1.0 - math.exp(-mu_cm_inv * path_length_cm) if mu_cm_inv > 0.0 else 0.0
    version = source_version or str(par_info.get("source_version", "diff_pat"))

    rows = []
    for raw in dat_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.split()
        if len(parts) < 7:
            continue
        scan_arcsec = _parse_fortran_float(parts[0])
        reflectivity_p = _parse_fortran_float(parts[5])
        reflectivity_s = _parse_fortran_float(parts[6])
        reflectivity = 0.5 * (reflectivity_p + reflectivity_s)
        transmittivity = max(0.0, 1.0 - absorption - reflectivity)
        rows.append(
            {
                "delta_theta_rad": math.radians(scan_arcsec / 3600.0),
                "reflectivity": reflectivity,
                "transmittivity": transmittivity,
                "absorption": absorption,
                "source_tool": "CRYSTAL-diff_pat",
                "source_version": version,
                "scan_arcsec": scan_arcsec,
                "reflectivity_p": reflectivity_p,
                "reflectivity_s": reflectivity_s,
                "absorption_mu_cm_inv": mu_cm_inv,
                "path_length_cm": path_length_cm,
                "absorption_model": "CRYSTAL beta-derived mu from diff_pat.par",
                "transmittivity_model": "1 - absorption - unpolarized diffracted reflectivity",
            }
        )
    if not rows:
        raise ValueError(f"no diff_pat data rows found in {dat_path}")

    fieldnames = list(rows[0])
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return {
        "n_rows": len(rows),
        "peak_reflectivity": max(row["reflectivity"] for row in rows),
        "absorption": absorption,
        "path_length_cm": path_length_cm,
        "source_version": version,
    }


def summarize_external_curve(
    path: str | Path,
    *,
    energy_keV: float,
    d_spacing_A: float,
    thickness_mm: float,
) -> dict[str, object]:
    rows = _read_rows(path)
    errors = _validate_rows(rows)
    numeric = [_numeric_row(row) for row in rows] if not errors else []
    source_tools = sorted({row["source_tool"] for row in rows if row.get("source_tool")}) if rows else []
    source_versions = sorted({row["source_version"] for row in rows if row.get("source_version")}) if rows else []
    if errors:
        return {
            "ok": False,
            "n_rows": len(rows),
            "errors": errors,
            "source_tools": source_tools,
            "source_versions": source_versions,
        }
    reflectivity = [row["reflectivity"] for row in numeric]
    delta = [row["delta_theta_rad"] for row in numeric]
    conservation_residuals = [
        abs(1.0 - row["reflectivity"] - row["transmittivity"] - row["absorption"])
        for row in numeric
    ]
    reference = [
        darwin_hamilton_mosaic_probabilities(
            E_keV=energy_keV,
            d_spacing_A=d_spacing_A,
            thickness_mm=thickness_mm,
            delta_theta_rad=row["delta_theta_rad"],
        ).p_diff
        for row in numeric
    ]
    return {
        "ok": bool(rows) and max(conservation_residuals) <= 0.05,
        "n_rows": len(rows),
        "errors": [],
        "source_tools": source_tools,
        "source_versions": source_versions,
        "energy_keV": energy_keV,
        "thickness_mm": thickness_mm,
        "delta_theta_rad_min": min(delta),
        "delta_theta_rad_max": max(delta),
        "peak_reflectivity": max(reflectivity),
        "integrated_reflectivity_rad": _trapz(delta, reflectivity),
        "max_flux_conservation_residual": max(conservation_residuals),
        "reference_kernel_peak_p_diff": max(reference),
        "peak_reflectivity_minus_reference": max(reflectivity) - max(reference),
    }


def _read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def _read_diffpat_par(path: str | Path | None) -> dict[str, object]:
    if path is None:
        return {}
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    info: dict[str, object] = {}
    version = re.search(r"DIFF_PAT\s+v([0-9.]+)", text)
    if version:
        info["source_version"] = f"diff_pat v{version.group(1)}"
    absorption = re.search(r"Absorption coeff =\s*([+-]?\d+(?:\.\d*)?(?:[EeDd][+-]?\d+)?)", text)
    if absorption:
        info["absorption_mu_cm_inv"] = _parse_fortran_float(absorption.group(1))
    gamma0 = re.search(r"Gamma0 =\s+VIN_BRAGG\(3\)\s*=\s*([+-]?\d+(?:\.\d*)?(?:[EeDd][+-]?\d+)?)", text)
    if gamma0:
        info["gamma0"] = _parse_fortran_float(gamma0.group(1))
    return info


def _parse_fortran_float(token: str) -> float:
    normalized = token.replace("D", "E").replace("d", "E")
    try:
        return float(normalized)
    except ValueError:
        match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))([+-]\d+)", normalized)
        if match:
            return float(match.group(1) + "E" + match.group(2))
        raise


def _validate_rows(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return ["empty curve file"]
    missing = [name for name in REQUIRED_COLUMNS if name not in rows[0]]
    if missing:
        return ["missing columns: " + ",".join(missing)]
    errors = []
    for idx, row in enumerate(rows):
        try:
            parsed = _numeric_row(row)
        except ValueError as exc:
            errors.append(f"row {idx}: {exc}")
            continue
        for key in ("reflectivity", "transmittivity", "absorption"):
            if parsed[key] < 0.0:
                errors.append(f"row {idx}: negative {key}")
    return errors


def _numeric_row(row: dict[str, str]) -> dict[str, float]:
    return {
        "delta_theta_rad": float(row["delta_theta_rad"]),
        "reflectivity": float(row["reflectivity"]),
        "transmittivity": float(row["transmittivity"]),
        "absorption": float(row["absorption"]),
    }


def _trapz(x: list[float], y: list[float]) -> float:
    pairs = sorted(zip(x, y), key=lambda item: item[0])
    total = 0.0
    for (x0, y0), (x1, y1) in zip(pairs, pairs[1:]):
        total += 0.5 * (y0 + y1) * (x1 - x0)
    return total
