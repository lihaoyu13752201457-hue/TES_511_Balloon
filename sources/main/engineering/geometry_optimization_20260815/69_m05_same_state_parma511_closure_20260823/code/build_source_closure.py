#!/usr/bin/env python3
"""Build the audited corrected-keV continuum/mono-511 source closure.

The current W=118.3 broadband tables are de-lined by replacing only their
566.08-keV node with the official PARMA continuum at the same source state.
The resulting 449.65/566.08/712.64-keV IP-LIN hat is removed exactly.  The
independent physical line is never rescaled to preserve the old total.

The continuum de-line state is frozen at W=118.3, g=0, Rc=11.6 GV, and
X=3.84535 g cm-2.  The independent physical mono-line target instead follows
the handoff authority: W=114.6, g=0.15, and each trajectory node's Rc/depth.
Its 81 x 80 target grid is divided by the already transported line source at
that same day-15 mono state to form line-event importance ratios.  Node 60 is
therefore an exact identity check (80 ratios equal one).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]
OUT = PACKAGE / "outputs/00_source_closure"

CONTRACT = ROOT / "engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json"
LINE80 = ROOT / (
    "engineering/m04_validation_geometry_handoff_20260810/"
    "02_parma_atm511_repair_20260810/line/parma511_day15_80bins.csv"
)
DAY15_ENVIRONMENT = ROOT / (
    "engineering/m04_validation_geometry_handoff_20260810/"
    "02_parma_atm511_repair_20260810/config/day15_environment_authority.json"
)
FAMILY_TIME = ROOT / (
    "engineering/particle_source_unit_repair_20260811/"
    "m05_corrected_reanalysis_20260813/data/parma_energy_integrated_family_scales_81bins.csv"
)
PARMA_PACKAGE_REL = Path(
    "engineering/m04_validation_geometry_handoff_20260810/"
    "02_parma_atm511_repair_20260810"
)

LINE_BINS = 80
QUADRATURE_ORDER = 64
SOURCE_SCHEMA_VERSION = 2
SOURCE_STATUS = (
    "COMPLETE__HYBRID_W118P3_G0_DELINE__W114P6_G0P15_MONO_81X80"
)

# These states deliberately have different jobs.  Do not collapse them.
CONTINUUM_DELINE_W_MV = 118.3
CONTINUUM_DELINE_G = 0.0
CONTINUUM_DELINE_RC_GV = 11.6
CONTINUUM_DELINE_DEPTH_G_CM2 = 3.84535

MONO_TARGET_W_MV = 114.6
MONO_TARGET_G = 0.15
DAY15_NODE_ID = 60
DAY15_RC_GV = 11.6
DAY15_DEPTH_G_CM2 = 3.4614689720143224
DAY15_LINE_FLUX_PH_CM2_S = 0.16651547160226118

# The transported proposal is exactly the frozen day-15 mono target state.
PROPOSAL_W_MV = MONO_TARGET_W_MV
PROPOSAL_RC_GV = DAY15_RC_GV
PROPOSAL_DEPTH_G_CM2 = DAY15_DEPTH_G_CM2
PROPOSAL_G = MONO_TARGET_G

LEFT_KEV = 449.65
NODE_KEV = 566.08
RIGHT_KEV = 712.64
W2 = (510.58, 511.42)
DELTA_OMEGA_SR = 2.0 * math.pi * 0.1

PROBE_SOURCE = r"""
#include <cstdlib>
#include <iomanip>
#include <iostream>
double getSpecCpp(int, double, double, double, double, double);
double getSpecAngFinalCpp(int, double, double, double, double, double, double);
int main(int argc, char** argv) {
  if (argc != 2) return 2;
  const double mu = std::strtod(argv[1], nullptr);
  const double value = getSpecCpp(33, 118.3, 11.6, 3.84535, 0.56608, 0.0)
                     * getSpecAngFinalCpp(6, 118.3, 11.6, 3.84535, 0.56608, 0.0, mu);
  std::cout << std::setprecision(17) << value << "\n";
  return 0;
}
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_manifest_sha256(directory: Path) -> tuple[str, int]:
    """Hash sorted relative names plus the hash of each runtime input file."""
    digest = hashlib.sha256()
    paths = sorted(path for path in directory.rglob("*") if path.is_file())
    for path in paths:
        digest.update(path.relative_to(directory).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest(), len(paths)


def select_parma_authority() -> tuple[Path, Path, Path]:
    """Choose a local driver with the complete runtime input tree."""
    failures: list[str] = []
    for base in (ROOT, Path("/home/ubuntu/TES_511_Balloon")):
        package = base / PARMA_PACKAGE_REL
        driver = package / "code/parma511_driver"
        vendor = package / "vendor/parma_cpp_official_20260810"
        required = (
            driver,
            vendor / "subroutines.cpp",
            vendor / "input/angle/photon.out",
            vendor / "input/angle/photon-Eint.out",
            vendor / "input/elemag/flux511keV.inp",
        )
        missing = [str(path) for path in required if not path.is_file()]
        if not missing:
            return base, driver, vendor
        failures.append(f"{base}: missing {missing}")
    raise RuntimeError("no complete local PARMA authority; " + "; ".join(failures))


PARMA_ROOT, DRIVER, VENDOR = select_parma_authority()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"empty output: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def current_gamma_authority(
    gamma_card: dict[str, Any],
) -> tuple[Path, list[Path], list[float]]:
    """Resolve the exact source card, corrected DP tables, and 20 card fluxes."""
    source_card = ROOT / gamma_card["source"]
    spectra = [ROOT / value for value in gamma_card["spectrum_files"]]
    if len(spectra) != 20 or any(not path.is_file() for path in spectra):
        raise RuntimeError("current corrected gamma spectrum set is incomplete")
    flux_by_bin: dict[int, float] = {}
    spectrum_by_bin: dict[int, str] = {}
    for line in source_card.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) == 2 and fields[0].startswith("Atm_gamma_bin") and fields[0].endswith(".Flux"):
            bin_id = int(fields[0].split("_bin", 1)[1][:2])
            flux_by_bin[bin_id] = float(fields[1])
        elif (
            len(fields) == 3
            and fields[0].startswith("Atm_gamma_bin")
            and fields[0].endswith(".Spectrum")
            and fields[1] == "File"
        ):
            bin_id = int(fields[0].split("_bin", 1)[1][:2])
            spectrum_by_bin[bin_id] = fields[2]
    if sorted(flux_by_bin) != list(range(20)) or sorted(spectrum_by_bin) != list(range(20)):
        raise RuntimeError("current gamma source card does not contain 20 ordered Flux/Spectrum entries")
    for bin_id, path in enumerate(spectra):
        if (ROOT / spectrum_by_bin[bin_id]).resolve() != path.resolve():
            raise RuntimeError(f"source-card/manifest spectrum mismatch in bin {bin_id}")
    fluxes = [flux_by_bin[bin_id] for bin_id in range(20)]
    if not math.isclose(
        math.fsum(fluxes),
        float(gamma_card["flux_sum_cm2_s"]),
        rel_tol=0.0,
        abs_tol=5e-13,
    ):
        raise RuntimeError("source-card gamma flux entries do not close to the manifest")
    return source_card, spectra, fluxes


def current_grid(
    bin_id: int, spectra: list[Path], fluxes: list[float]
) -> tuple[np.ndarray, np.ndarray, float]:
    """Return the actual source intensity implied by Flux and the rounded DP PDF."""
    path = spectra[bin_id]
    lines = path.read_text(encoding="utf-8").splitlines()
    if "IP LIN" not in lines:
        raise RuntimeError(f"current gamma spectrum is not IP LIN: {path}")
    pairs = [
        (float(fields[1]), float(fields[2]))
        for fields in (line.split() for line in lines)
        if len(fields) == 3 and fields[0] == "DP"
    ]
    x = np.asarray([pair[0] for pair in pairs], dtype=np.float64)
    pdf = np.asarray([pair[1] for pair in pairs], dtype=np.float64)
    if not (len(x) >= 3 and np.all(np.diff(x) > 0.0) and np.all(pdf >= 0.0)):
        raise RuntimeError(f"invalid current corrected gamma grid: {path}")
    rounded_pdf_integral = float(np.trapezoid(pdf, x))
    if not math.isclose(rounded_pdf_integral, 1.0, rel_tol=0.0, abs_tol=5e-11):
        raise RuntimeError(f"current gamma PDF does not integrate to unity: {path}")
    # The source card's Flux is authoritative.  Renormalize only the tiny
    # decimal-printing residual in the nominally unit-integral DP table.
    intensity = pdf * fluxes[bin_id] / rounded_pdf_integral
    return x, intensity, rounded_pdf_integral


def compile_probe(directory: Path) -> Path:
    source = directory / "parma_gamma_continuum_probe.cpp"
    binary = directory / "parma_gamma_continuum_probe"
    source.write_text(PROBE_SOURCE, encoding="utf-8")
    subprocess.run(
        [
            "g++", "-std=c++17", "-O2", str(source),
            str(VENDOR / "subroutines.cpp"), "-o", str(binary),
        ],
        cwd=VENDOR,
        check=True,
        text=True,
        capture_output=True,
    )
    return binary


def official_continuum_nodes() -> list[float]:
    values: list[float] = []
    with tempfile.TemporaryDirectory(prefix="m05_mono511_continuum_") as name:
        binary = compile_probe(Path(name))
        for bin_id in range(20):
            mu_mid = 0.95 - 0.1 * bin_id
            output = subprocess.check_output(
                [str(binary), repr(mu_mid)], cwd=VENDOR, text=True
            ).strip()
            value = float(output) * DELTA_OMEGA_SR / 1000.0
            if not math.isfinite(value) or value <= 0.0:
                raise RuntimeError(f"invalid official continuum node for bin {bin_id}: {value}")
            values.append(value)
    return values


def integrate_piecewise(x: np.ndarray, y: np.ndarray, lo: float, hi: float) -> float:
    points = np.asarray(
        [lo, *[value for value in x if lo < value < hi], hi],
        dtype=np.float64,
    )
    return float(np.trapezoid(np.interp(points, x, y), points))


def read_line_proposal() -> list[dict[str, Any]]:
    rows = read_csv(LINE80)
    if len(rows) != LINE_BINS:
        raise RuntimeError(f"line proposal is not {LINE_BINS}-bin")
    result: list[dict[str, Any]] = []
    for expected, row in enumerate(rows):
        bin_id = int(row["theta_bin_id"])
        flux = float(row["line_flux_ph_cm-2_s-1"])
        fraction = float(row["line_fraction"])
        if bin_id != expected or not (math.isfinite(flux) and flux > 0.0):
            raise RuntimeError(f"invalid proposal bin {expected}")
        result.append({
            **row,
            "theta_bin_id": bin_id,
            "line_flux": flux,
            "line_fraction_value": fraction,
            "parma_mu_low_value": float(row["parma_mu_low"]),
            "parma_mu_high_value": float(row["parma_mu_high"]),
            "theta_low_value": float(row["cosima_theta_low_deg"]),
            "theta_high_value": float(row["cosima_theta_high_deg"]),
        })
    total = math.fsum(row["line_flux"] for row in result)
    fractions = math.fsum(row["line_fraction_value"] for row in result)
    if not math.isclose(
        total, DAY15_LINE_FLUX_PH_CM2_S, rel_tol=0.0, abs_tol=2e-15
    ):
        raise RuntimeError(f"proposal line total changed: {total}")
    if not math.isclose(fractions, 1.0, rel_tol=0.0, abs_tol=2e-14):
        raise RuntimeError(f"proposal fractions do not close: {fractions}")
    return result


def validate_day15_environment_authority() -> dict[str, Any]:
    payload = json.loads(DAY15_ENVIRONMENT.read_text(encoding="utf-8"))
    if payload.get("authority_status") != (
        "FROZEN_EXPLICIT_DAY15_TUPLE_FOR_MODULAR_511_REPAIR"
    ):
        raise RuntimeError("day-15 mono environment authority is not frozen")
    authority = payload.get("authority")
    if not isinstance(authority, dict):
        raise RuntimeError("day-15 mono environment authority payload is missing")
    expected = {
        "solar_modulation_MV": MONO_TARGET_W_MV,
        "cutoff_rigidity_GV": DAY15_RC_GV,
        "atmospheric_depth_g_cm2": DAY15_DEPTH_G_CM2,
        "local_geometry_g": MONO_TARGET_G,
        "line_energy_MeV": 0.51099895,
        "line_energy_keV": 510.99895,
    }
    for key, target in expected.items():
        actual = float(authority.get(key, math.nan))
        if not math.isclose(actual, target, rel_tol=0.0, abs_tol=2e-14):
            raise RuntimeError(
                f"day-15 mono authority mismatch for {key}: {actual} vs {target}"
            )
    return payload


def run_parma511_driver(
    s_mv: float,
    rc_gv: float,
    depth_g_cm2: float,
    g: float,
) -> dict[str, Any]:
    command = [
        str(DRIVER),
        "--s", format(s_mv, ".17g"),
        "--rc", format(rc_gv, ".17g"),
        "--depth", format(depth_g_cm2, ".17g"),
        "--g", format(g, ".17g"),
        "--bins", str(LINE_BINS),
        "--quadrature-order", str(QUADRATURE_ORDER),
    ]
    completed = subprocess.run(
        command, cwd=VENDOR, check=True, text=True, capture_output=True
    )
    stdout = completed.stdout
    authority: dict[str, float] = {}
    line_values: dict[str, float] = {}
    angular: dict[str, float] = {}
    bins: list[dict[str, float | int]] = []
    for fields in csv.reader(io.StringIO(stdout)):
        if not fields or fields[0] == "record":
            continue
        if fields[0] == "authority":
            authority[fields[1]] = float(fields[2])
        elif fields[0] == "line":
            line_values[fields[1]] = float(fields[2])
        elif fields[0] == "angular" and fields[1] in {
            "full_sphere_integral", "bins", "quadrature_order"
        }:
            angular[fields[1]] = float(fields[2])
        elif fields[0] == "bin" and fields[1] != "bin_id":
            if len(fields) != 6:
                raise RuntimeError(f"malformed PARMA bin row: {fields}")
            bins.append({
                "driver_bin_id": int(fields[1]),
                "mu_low": float(fields[2]),
                "mu_high": float(fields[3]),
                "fraction": float(fields[4]),
                "flux": float(fields[5]),
            })
    expected_authority = {
        "solar_modulation": s_mv,
        "cutoff_rigidity": rc_gv,
        "atmospheric_depth": depth_g_cm2,
        "local_geometry_g": g,
    }
    for key, expected in expected_authority.items():
        actual = authority.get(key, math.nan)
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=2e-12):
            raise RuntimeError(f"driver authority mismatch for {key}: {actual} vs {expected}")
    if len(bins) != LINE_BINS:
        raise RuntimeError(f"PARMA driver returned {len(bins)} bins")
    if [row["driver_bin_id"] for row in bins] != list(range(LINE_BINS)):
        raise RuntimeError("PARMA driver bins are not ordered")
    if int(angular.get("bins", -1)) != LINE_BINS:
        raise RuntimeError("PARMA driver bin setting differs")
    if int(angular.get("quadrature_order", -1)) != QUADRATURE_ORDER:
        raise RuntimeError("PARMA driver quadrature setting differs")
    full_sphere = angular.get("full_sphere_integral", math.nan)
    line_flux = line_values.get("integrated_flux", math.nan)
    line_energy = line_values.get("line_energy", math.nan)
    numeric = [
        full_sphere,
        line_flux,
        line_energy,
        *[
            float(row[key])
            for row in bins
            for key in ("mu_low", "mu_high", "fraction", "flux")
        ],
    ]
    if not all(math.isfinite(value) for value in numeric):
        raise RuntimeError("non-finite PARMA output; vendor runtime inputs/cwd are incomplete")
    if line_flux <= 0.0 or any(
        float(row["fraction"]) <= 0.0 or float(row["flux"]) <= 0.0
        for row in bins
    ):
        raise RuntimeError("non-positive PARMA line flux/fraction")
    fraction_sum = math.fsum(float(row["fraction"]) for row in bins)
    bin_flux_sum = math.fsum(float(row["flux"]) for row in bins)
    if not math.isclose(full_sphere, 1.0, rel_tol=0.0, abs_tol=2e-12):
        raise RuntimeError(f"PARMA angular integral does not close: {full_sphere}")
    if not math.isclose(fraction_sum, 1.0, rel_tol=0.0, abs_tol=2e-12):
        raise RuntimeError(f"PARMA fractions do not close: {fraction_sum}")
    if not math.isclose(bin_flux_sum, line_flux, rel_tol=0.0, abs_tol=2e-12):
        raise RuntimeError(f"PARMA bin fluxes do not close: {bin_flux_sum} vs {line_flux}")
    if not math.isclose(line_energy, 0.51099895, rel_tol=0.0, abs_tol=2e-15):
        raise RuntimeError(f"unexpected line energy: {line_energy}")
    return {
        "command": command,
        "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
        "line_energy_MeV": line_energy,
        "line_flux": line_flux,
        "full_sphere_integral": full_sphere,
        "fraction_sum": fraction_sum,
        "bin_flux_sum": bin_flux_sum,
        # Driver order is increasing PARMA mu; Cosima source order is reversed.
        "source_order_bins": list(reversed(bins)),
    }


def validate_bin_alignment(
    target_bins: list[dict[str, Any]], proposal: list[dict[str, Any]]
) -> None:
    if len(target_bins) != LINE_BINS:
        raise RuntimeError("target source-bin count differs")
    for source_bin, (target, old) in enumerate(zip(target_bins, proposal)):
        if int(target["driver_bin_id"]) != LINE_BINS - 1 - source_bin:
            raise RuntimeError(f"driver/source reversal failed at bin {source_bin}")
        if not math.isclose(
            float(target["mu_low"]), old["parma_mu_low_value"],
            rel_tol=0.0, abs_tol=2e-15,
        ):
            raise RuntimeError(f"target/proposal mu-low mismatch at bin {source_bin}")
        if not math.isclose(
            float(target["mu_high"]), old["parma_mu_high_value"],
            rel_tol=0.0, abs_tol=2e-15,
        ):
            raise RuntimeError(f"target/proposal mu-high mismatch at bin {source_bin}")


def aggregate_80_to_20(values: list[float]) -> list[float]:
    if len(values) != LINE_BINS:
        raise RuntimeError("80-to-20 aggregation input differs")
    return [
        math.fsum(values[4 * index:4 * index + 4])
        for index in range(20)
    ]


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    validate_day15_environment_authority()
    proposal = read_line_proposal()
    proposal_flux = [float(row["line_flux"]) for row in proposal]
    proposal_total = math.fsum(proposal_flux)

    continuum_state_line = run_parma511_driver(
        CONTINUUM_DELINE_W_MV,
        CONTINUUM_DELINE_RC_GV,
        CONTINUUM_DELINE_DEPTH_G_CM2,
        CONTINUUM_DELINE_G,
    )
    validate_bin_alignment(continuum_state_line["source_order_bins"], proposal)
    continuum_state_line80 = [
        float(row["flux"])
        for row in continuum_state_line["source_order_bins"]
    ]
    continuum_state_line20 = aggregate_80_to_20(continuum_state_line80)
    proposal20 = aggregate_80_to_20(proposal_flux)

    continuum_nodes = official_continuum_nodes()
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    gamma_card = next(
        row
        for row in contract["geometries"]["mass_model_511"]["cards"]
        if row["family"] == "gamma"
    )
    contract_flux = float(gamma_card["flux_sum_cm2_s"])
    source_card, current_spectra, source_flux20 = current_gamma_authority(
        gamma_card
    )

    bin_rows: list[dict[str, Any]] = []
    total_flux_sum = 0.0
    continuum_flux = 0.0
    coarse_line_flux = 0.0
    total_w2 = 0.0
    line_w2 = 0.0
    min_continuum_ratio = 1.0
    for bin_id in range(20):
        x, total, rounded_pdf_integral = current_grid(
            bin_id, current_spectra, source_flux20
        )
        node = int(np.argmin(np.abs(x - NODE_KEV)))
        if not math.isclose(float(x[node]), NODE_KEV, rel_tol=0.0, abs_tol=1e-12):
            raise RuntimeError(f"coarse line node missing in bin {bin_id}")
        continuum = total.copy()
        continuum[node] = continuum_nodes[bin_id]
        coarse_line = total - continuum
        if float(np.min(coarse_line)) < -1e-15:
            raise RuntimeError(f"official continuum exceeds current total in bin {bin_id}")

        total_integral = float(np.trapezoid(total, x))
        continuum_integral = float(np.trapezoid(continuum, x))
        line_integral = float(np.trapezoid(coarse_line, x))
        dense = np.unique(
            np.concatenate((x, np.linspace(LEFT_KEV, RIGHT_KEV, 4097)))
        )
        total_dense = np.interp(dense, x, total)
        continuum_dense = np.interp(dense, x, continuum)
        if float(np.min(continuum_dense)) < -1e-14:
            raise RuntimeError(f"negative continuum in bin {bin_id}")
        support = (
            (dense > LEFT_KEV)
            & (dense < RIGHT_KEV)
            & (total_dense > 0.0)
        )
        ratios = continuum_dense[support] / total_dense[support]
        if (
            len(ratios) == 0
            or float(np.min(ratios)) < -1e-12
            or float(np.max(ratios)) > 1.0 + 1e-12
        ):
            raise RuntimeError(f"invalid continuum importance ratios in bin {bin_id}")
        min_continuum_ratio = min(
            min_continuum_ratio, float(np.min(ratios))
        )

        total_w2_bin = integrate_piecewise(x, total, *W2)
        line_w2_bin = integrate_piecewise(x, coarse_line, *W2)
        total_flux_sum += total_integral
        continuum_flux += continuum_integral
        coarse_line_flux += line_integral
        total_w2 += total_w2_bin
        line_w2 += line_w2_bin
        node_total = float(total[node])
        node_line = float(coarse_line[node])
        bin_rows.append({
            "source_bin20": bin_id,
            "source_card_flux_ph_cm2_s": source_flux20[bin_id],
            "rounded_dp_pdf_integral_before_card_flux_normalization": rounded_pdf_integral,
            "embedded_coarse_line_flux_ph_cm2_s": line_integral,
            "parma511_continuum_deline_state_flux_ph_cm2_s": (
                continuum_state_line20[bin_id]
            ),
            "mono511_day15_authority_flux_ph_cm2_s": proposal20[bin_id],
            "broadband_total_flux_ph_cm2_s": total_integral,
            "continuum_flux_ph_cm2_s": continuum_integral,
            "line_node_total_density_ph_cm2_s_keV": node_total,
            "line_node_subtracted_density_ph_cm2_s_keV": node_line,
            "line_node_continuum_density_ph_cm2_s_keV": continuum_nodes[bin_id],
            "line_node_continuum_importance_ratio": continuum_nodes[bin_id] / node_total,
            "w2_total_flux_ph_cm2_s": total_w2_bin,
            "w2_coarse_line_flux_ph_cm2_s": line_w2_bin,
            "w2_continuum_flux_ph_cm2_s": total_w2_bin - line_w2_bin,
        })

    if not math.isclose(total_flux_sum, contract_flux, rel_tol=0.0, abs_tol=5e-10):
        raise RuntimeError(f"current/source-card mismatch: {total_flux_sum} vs {contract_flux}")
    if not math.isclose(
        coarse_line_flux, 0.1764426312336, rel_tol=0.0, abs_tol=2e-12
    ):
        raise RuntimeError(f"embedded coarse-line area differs: {coarse_line_flux}")
    if not math.isclose(
        continuum_flux + coarse_line_flux,
        total_flux_sum,
        rel_tol=0.0,
        abs_tol=2e-12,
    ):
        raise RuntimeError("current continuum/coarse-line integrals do not close")
    if continuum_flux <= 0.0 or min_continuum_ratio < 0.0:
        raise RuntimeError("non-positive continuum decomposition")
    coarse_path = OUT / "coarse_line_decomposition_20bins.csv"
    write_csv(coarse_path, bin_rows)

    family_rows = read_csv(FAMILY_TIME)
    if (
        len(family_rows) != 81
        or [int(row["time_bin_id"]) for row in family_rows] != list(range(81))
    ):
        raise RuntimeError("mission source axis is not ordered 81 nodes")

    target_rows: list[dict[str, Any]] = []
    node_lines: list[dict[str, Any]] = []
    global_min_importance = math.inf
    global_max_importance = 0.0
    max_line_closure_residual = 0.0
    day15_max_bin_flux_delta = 0.0
    day15_max_ratio_delta = 0.0
    for family in family_rows:
        node_id = int(family["time_bin_id"])
        day_mid = float(family["day_mid"])
        rc_gv = float(family["Rc_GV_parma"])
        depth_g_cm2 = float(family["depth_g_cm2_parma"])
        if not all(
            math.isfinite(value) and value >= 0.0
            for value in (day_mid, rc_gv, depth_g_cm2)
        ):
            raise RuntimeError(f"invalid node authority at {node_id}")
        if node_id == DAY15_NODE_ID:
            if not math.isclose(day_mid, 15.0, rel_tol=0.0, abs_tol=2e-14):
                raise RuntimeError(f"node 60 day is not frozen day 15: {day_mid}")
            if not math.isclose(rc_gv, DAY15_RC_GV, rel_tol=0.0, abs_tol=2e-12):
                raise RuntimeError(f"node 60 Rc differs from authority: {rc_gv}")
            if not math.isclose(
                depth_g_cm2,
                DAY15_DEPTH_G_CM2,
                rel_tol=0.0,
                abs_tol=2e-10,
            ):
                raise RuntimeError(
                    f"node 60 depth differs from authority: {depth_g_cm2}"
                )
            # The family table is decimal-truncated.  The mono authority tuple
            # is not: always pass the frozen full-precision day-15 values.
            rc_gv = DAY15_RC_GV
            depth_g_cm2 = DAY15_DEPTH_G_CM2
        run = run_parma511_driver(
            MONO_TARGET_W_MV, rc_gv, depth_g_cm2, MONO_TARGET_G
        )
        bins = run["source_order_bins"]
        validate_bin_alignment(bins, proposal)
        node_importance: list[float] = []
        for source_bin, (target, old) in enumerate(zip(bins, proposal)):
            target_flux = float(target["flux"])
            old_flux = float(old["line_flux"])
            importance = target_flux / old_flux
            if not (math.isfinite(importance) and importance >= 0.0):
                raise RuntimeError(
                    f"invalid importance at node {node_id}, bin {source_bin}"
                )
            if node_id == DAY15_NODE_ID:
                flux_delta = abs(target_flux - old_flux)
                ratio_delta = abs(importance - 1.0)
                day15_max_bin_flux_delta = max(
                    day15_max_bin_flux_delta, flux_delta
                )
                day15_max_ratio_delta = max(
                    day15_max_ratio_delta, ratio_delta
                )
                if flux_delta > 2e-15 or ratio_delta > 2e-13:
                    raise RuntimeError(
                        "node 60 target/proposal authority mismatch at bin "
                        f"{source_bin}: target={target_flux:.17g}, "
                        f"proposal={old_flux:.17g}, ratio={importance:.17g}"
                    )
                # The proposal CSV is the frozen serialized authority for this
                # exact driver state.  After verifying the regenerated value,
                # canonicalize node 60 so the published identity is literal.
                target_flux = old_flux
                importance = 1.0
            node_importance.append(importance)
            global_min_importance = min(global_min_importance, importance)
            global_max_importance = max(global_max_importance, importance)
            target_rows.append({
                # Fixed downstream schema.
                "time_bin_id": node_id,
                "day_mid": day_mid,
                "source_bin80": source_bin,
                "target_flux_ph_cm2_s": target_flux,
                "proposal_flux_ph_cm2_s": old_flux,
                "importance_ratio": importance,
                # Additional authority/audit columns.
                "altitude_km": float(family["altitude_km"]),
                "latitude_deg": float(family["latitude_deg"]),
                "longitude_deg": float(family["longitude_deg"]),
                "target_W_MV": MONO_TARGET_W_MV,
                "target_Rc_GV": rc_gv,
                "target_depth_g_cm2": depth_g_cm2,
                "target_g": MONO_TARGET_G,
                "driver_bin_id": int(target["driver_bin_id"]),
                "parma_mu_low": float(target["mu_low"]),
                "parma_mu_high": float(target["mu_high"]),
                "cosima_theta_low_deg": old["theta_low_value"],
                "cosima_theta_high_deg": old["theta_high_value"],
                "direction_label": old["direction_label"],
                "target_line_fraction": float(target["fraction"]),
                "proposal_W_MV": PROPOSAL_W_MV,
                "proposal_Rc_GV": PROPOSAL_RC_GV,
                "proposal_depth_g_cm2": PROPOSAL_DEPTH_G_CM2,
                "proposal_g": PROPOSAL_G,
                "proposal_line_fraction": float(old["line_fraction_value"]),
            })
        weighted_proposal = math.fsum(
            flux * ratio
            for flux, ratio in zip(proposal_flux, node_importance)
        )
        driver_line_total = float(run["line_flux"])
        line_total = (
            proposal_total if node_id == DAY15_NODE_ID else driver_line_total
        )
        max_line_closure_residual = max(
            max_line_closure_residual,
            abs(float(run["bin_flux_sum"]) - driver_line_total),
            abs(driver_line_total - line_total),
            abs(weighted_proposal - line_total),
        )
        node_lines.append({
            "time_bin_id": node_id,
            "day_mid": day_mid,
            "line_flux": line_total,
            "minimum_importance_ratio": min(node_importance),
            "maximum_importance_ratio": max(node_importance),
            "driver_full_sphere_integral": float(run["full_sphere_integral"]),
            "driver_bin_flux_sum": float(run["bin_flux_sum"]),
            "driver_line_flux_before_day15_canonicalization": driver_line_total,
            "proposal_weighted_flux_sum": weighted_proposal,
            "driver_stdout_sha256": run["stdout_sha256"],
            "target_Rc_GV": rc_gv,
            "target_depth_g_cm2": depth_g_cm2,
        })

    day15_line = node_lines[DAY15_NODE_ID]
    if int(day15_line["time_bin_id"]) != DAY15_NODE_ID:
        raise RuntimeError("node 60 mono authority row is missing")
    if not math.isclose(
        float(day15_line["line_flux"]),
        DAY15_LINE_FLUX_PH_CM2_S,
        rel_tol=0.0,
        abs_tol=2e-15,
    ):
        raise RuntimeError(
            "node 60 line integral differs from frozen authority: "
            f"{day15_line['line_flux']}"
        )
    if not (
        math.isclose(
            float(day15_line["minimum_importance_ratio"]),
            1.0,
            rel_tol=0.0,
            abs_tol=2e-13,
        )
        and math.isclose(
            float(day15_line["maximum_importance_ratio"]),
            1.0,
            rel_tol=0.0,
            abs_tol=2e-13,
        )
    ):
        raise RuntimeError("node 60 80-bin importance ratios do not close to one")

    if len(target_rows) != 81 * LINE_BINS:
        raise RuntimeError(f"target grid row count differs: {len(target_rows)}")
    target_path = OUT / "mono511_target_81x80.csv"
    write_csv(target_path, target_rows)

    timeline: list[dict[str, Any]] = []
    max_subtraction_residual = 0.0
    max_deficit = 0.0
    max_surplus = 0.0
    for family, line in zip(family_rows, node_lines):
        if int(family["time_bin_id"]) != int(line["time_bin_id"]):
            raise RuntimeError("gamma/line axes differ")
        gamma_scale = float(family["scale_gamma_to_parma_reference"])
        if not (math.isfinite(gamma_scale) and gamma_scale >= 0.0):
            raise RuntimeError(f"negative gamma scale at {family['time_bin_id']}")
        removed = coarse_line_flux * gamma_scale
        continuum = continuum_flux * gamma_scale
        original = contract_flux * gamma_scale
        target_line = float(line["line_flux"])
        recomposed = continuum + target_line
        representation_delta = recomposed - original
        subtraction_residual = continuum + removed - original
        max_subtraction_residual = max(
            max_subtraction_residual, abs(subtraction_residual)
        )
        max_deficit = max(max_deficit, max(0.0, -representation_delta))
        max_surplus = max(max_surplus, max(0.0, representation_delta))
        nonnegative = (
            gamma_scale,
            removed,
            continuum,
            original,
            target_line,
            recomposed,
            float(line["minimum_importance_ratio"]),
            float(line["maximum_importance_ratio"]),
        )
        if not all(
            math.isfinite(value) and value >= 0.0 for value in nonnegative
        ):
            raise RuntimeError(f"invalid component at {family['time_bin_id']}")
        timeline.append({
            # Fixed downstream schema.
            "time_bin_id": int(family["time_bin_id"]),
            "day_mid": float(family["day_mid"]),
            "gamma_continuum_scale_to_reference": gamma_scale,
            "removed_coarse_line_flux_ph_cm2_s": removed,
            "target_mono511_flux_ph_cm2_s": target_line,
            "recomposed_gamma_flux_ph_cm2_s": recomposed,
            "original_broadband_flux_ph_cm2_s": original,
            "representation_delta_ph_cm2_s": representation_delta,
            # Additional closure/audit columns.
            "continuum_flux_ph_cm2_s": continuum,
            "exact_subtraction_identity_residual_ph_cm2_s": subtraction_residual,
            "representation_deficit_ph_cm2_s": max(0.0, -representation_delta),
            "representation_surplus_ph_cm2_s": max(0.0, representation_delta),
            "target_line_scale_to_w114p6_day15_total": target_line / proposal_total,
            "minimum_bin80_importance_ratio": float(line["minimum_importance_ratio"]),
            "maximum_bin80_importance_ratio": float(line["maximum_importance_ratio"]),
            "target_Rc_GV": float(line["target_Rc_GV"]),
            "target_depth_g_cm2": float(line["target_depth_g_cm2"]),
            "source_gamma_scale_W_index_MV": float(family["W_index"]),
            "driver_full_sphere_integral": float(line["driver_full_sphere_integral"]),
            "driver_bin_flux_sum_ph_cm2_s": float(line["driver_bin_flux_sum"]),
            "proposal_weighted_flux_sum_ph_cm2_s": float(
                line["proposal_weighted_flux_sum"]
            ),
            "line_driver_stdout_sha256": line["driver_stdout_sha256"],
        })
    timeline_path = OUT / "trajectory_component_scales_81nodes.csv"
    write_csv(timeline_path, timeline)

    continuum_state_line_flux = float(continuum_state_line["line_flux"])
    continuum_state_recomposed = continuum_flux + continuum_state_line_flux
    continuum_state_delta = continuum_state_recomposed - contract_flux
    physical = (
        contract_flux,
        coarse_line_flux,
        continuum_flux,
        continuum_state_line_flux,
        continuum_state_recomposed,
        min_continuum_ratio,
        global_min_importance,
        global_max_importance,
    )
    if not all(
        math.isfinite(value) and value >= 0.0 for value in physical
    ):
        raise RuntimeError("source closure contains a negative physical quantity")

    current_spectrum_hashes = {
        path.name: sha256(path) for path in current_spectra
    }
    vendor_tree_hash, vendor_tree_files = tree_manifest_sha256(VENDOR / "input")
    output_hashes = {
        path.name: sha256(path)
        for path in (coarse_path, target_path, timeline_path)
    }
    line_totals = [float(row["line_flux"]) for row in node_lines]
    min_line_index = int(np.argmin(np.asarray(line_totals)))
    max_line_index = int(np.argmax(np.asarray(line_totals)))
    gamma_scale_w = sorted({float(row["W_index"]) for row in family_rows})

    result = {
        "schema_version": SOURCE_SCHEMA_VERSION,
        "status": SOURCE_STATUS,
        "continuum_deline_reference_closure": {
            "state_role": "CONTINUUM_DELINE_STATE",
            "solar_modulation_W_MV": CONTINUUM_DELINE_W_MV,
            "cutoff_rigidity_Rc_GV": CONTINUUM_DELINE_RC_GV,
            "atmospheric_depth_g_cm2": CONTINUUM_DELINE_DEPTH_G_CM2,
            "local_geometry_g": CONTINUUM_DELINE_G,
            "broadband_reference_flux_ph_cm2_s": contract_flux,
            "removed_coarse_line_reference_flux_ph_cm2_s": coarse_line_flux,
            "continuum_reference_flux_ph_cm2_s": continuum_flux,
            "parma511_flux_at_continuum_deline_state_ph_cm2_s": (
                continuum_state_line_flux
            ),
            "recomposed_continuum_plus_same_state_parma511_flux_ph_cm2_s": (
                continuum_state_recomposed
            ),
            "representation_delta_ph_cm2_s": continuum_state_delta,
            "representation_deficit_ph_cm2_s": max(
                0.0, -continuum_state_delta
            ),
            "representation_surplus_ph_cm2_s": max(
                0.0, continuum_state_delta
            ),
            "exact_subtraction_identity_residual_ph_cm2_s": (
                continuum_flux + coarse_line_flux - total_flux_sum
            ),
            "current_grid_integral_minus_contract_ph_cm2_s": (
                total_flux_sum - contract_flux
            ),
        },
        "coarse_line": {
            "energy_basis_keV": [LEFT_KEV, NODE_KEV, RIGHT_KEV],
            "interpolation": "IP LIN in energy and intensity",
            "definition": (
                "current W=118.3 total grid minus official W=118.3 continuum; "
                "only the 566.08-keV node differs"
            ),
            "current_table_intensity_definition": (
                "source-card Flux times the printed corrected-keV DP values, "
                "divided by the printed DP trapezoidal integral"
            ),
            "event_importance_ratio_definition": (
                "For an existing broadband event use source_bin20="
                "clip(floor((1+IA_INIT.dir_z)*10),0,19), then "
                "w_cont=J_cont(source_bin20,IA_INIT.energy_keV)/"
                "J_total(source_bin20,IA_INIT.energy_keV); w_cont=1 outside "
                "(449.65,712.64) keV. Both J grids use the same IP-LIN nodes."
            ),
            "minimum_event_importance_ratio_Jcont_over_Jtotal": min_continuum_ratio,
            "maximum_event_importance_ratio_Jcont_over_Jtotal": 1.0,
            "negative_continuum_flux_or_importance_count": 0,
            "w2_source_flux": {
                "broadband_total_ph_cm2_s": total_w2,
                "coarse_line_contribution_ph_cm2_s": line_w2,
                "continuum_ph_cm2_s": total_w2 - line_w2,
            },
        },
        "mono511_day15_authority": {
            "state_role": "MONO_TARGET_STATE_AND_TRANSPORT_PROPOSAL_AT_NODE60",
            "time_bin_id": DAY15_NODE_ID,
            "day_mid": 15.0,
            "solar_modulation_W_MV": MONO_TARGET_W_MV,
            "cutoff_rigidity_Rc_GV": DAY15_RC_GV,
            "atmospheric_depth_g_cm2": DAY15_DEPTH_G_CM2,
            "local_geometry_g": MONO_TARGET_G,
            "integrated_flux_ph_cm2_s": DAY15_LINE_FLUX_PH_CM2_S,
            "angular_bins": LINE_BINS,
            "maximum_target_minus_proposal_bin_flux_abs_ph_cm2_s": (
                day15_max_bin_flux_delta
            ),
            "maximum_importance_ratio_minus_one_abs": day15_max_ratio_delta,
            "all_80_importance_ratios_equal_one_within_abs_tolerance": 2e-13,
        },
        "mono511_target": {
            "state_role": "MONO_TARGET_STATE",
            "solar_modulation_W_MV": MONO_TARGET_W_MV,
            "local_geometry_g": MONO_TARGET_G,
            "trajectory_nodes": len(node_lines),
            "angular_bins_per_node": LINE_BINS,
            "rows": len(target_rows),
            "quadrature_order": QUADRATURE_ORDER,
            "driver_command_template": (
                "parma511_driver --s 114.6 --rc <Rc_GV_parma> "
                "--depth <depth_g_cm2_parma> --g 0.15 --bins 80 "
                "--quadrature-order 64"
            ),
            "source_bin80_from_event_definition": (
                "clip(floor((1+IA_INIT.dir_z)*40),0,79)"
            ),
            "line_energy_MeV": float(
                continuum_state_line["line_energy_MeV"]
            ),
            "minimum_node_flux_ph_cm2_s": min(line_totals),
            "minimum_node_time_bin_id": int(
                node_lines[min_line_index]["time_bin_id"]
            ),
            "maximum_node_flux_ph_cm2_s": max(line_totals),
            "maximum_node_time_bin_id": int(
                node_lines[max_line_index]["time_bin_id"]
            ),
            "minimum_importance_ratio": global_min_importance,
            "maximum_importance_ratio": global_max_importance,
            "maximum_bin_sum_or_importance_closure_residual_ph_cm2_s": (
                max_line_closure_residual
            ),
            "negative_target_flux_or_importance_count": 0,
            "day15_identity_node": DAY15_NODE_ID,
            "day15_integrated_flux_ph_cm2_s": float(
                day15_line["line_flux"]
            ),
            "day15_minimum_importance_ratio": float(
                day15_line["minimum_importance_ratio"]
            ),
            "day15_maximum_importance_ratio": float(
                day15_line["maximum_importance_ratio"]
            ),
        },
        "proposal_denominator": {
            "definition": "existing transported W=114.6 day-15 PARMA 80-bin source",
            "solar_modulation_W_MV": PROPOSAL_W_MV,
            "cutoff_rigidity_Rc_GV": PROPOSAL_RC_GV,
            "atmospheric_depth_g_cm2": PROPOSAL_DEPTH_G_CM2,
            "local_geometry_g": PROPOSAL_G,
            "integrated_flux_ph_cm2_s": proposal_total,
            "importance_ratio_definition": (
                "target_flux(time_bin_id,source_bin80; "
                "W=114.6,Rc_t,depth_t,g=0.15) / "
                "proposal_flux(source_bin80; frozen W=114.6,g=0.15 day15 source)"
            ),
        },
        "trajectory_component_policy": {
            "continuum": (
                "exact de-lined W=118.3 reference continuum multiplied by the "
                "existing scale_gamma_to_parma_reference; no line-dependent "
                "renormalization"
            ),
            "line": (
                "absolute official W=114.6/Rc_t/depth_t/g=0.15 driver result; "
                "node 60 uses the full-precision frozen day-15 Rc/depth tuple"
            ),
            "recomposition": (
                "continuum plus physical mono line; old broadband total is not enforced"
            ),
            "maximum_exact_subtraction_identity_residual_ph_cm2_s": (
                max_subtraction_residual
            ),
            "maximum_representation_deficit_ph_cm2_s": max_deficit,
            "maximum_representation_surplus_ph_cm2_s": max_surplus,
            "gamma_scale_input_W_index_values_MV": gamma_scale_w,
        },
        "caveats": [
            (
                "The old corrected-keV broadband total contains a coarse "
                "449.65/566.08/712.64-keV IP-LIN hat. Its exact removed area is "
                "not numerically identical to the official physical mono-line "
                "integral, so recomposition intentionally changes the total."
            ),
            (
                "This is an explicit hybrid closure: continuum de-line uses "
                "W=118.3/g=0/Rc=11.6/X=3.84535, while the physical mono target "
                "uses W=114.6/g=0.15 and node-specific Rc/depth. The two states "
                "must not be presented as one common atmosphere."
            ),
            (
                "The continuum trajectory retains scale_gamma_to_parma_reference "
                "from the existing 81-node family table, whose W_index is 114.6. "
                "No new W=118.3 broadband continuum trajectory was generated."
            ),
            (
                "Physical PARMA flux/source-model systematics are EXCLUDED; "
                "the closure and later top-up decision cover finite transport "
                "statistics and deterministic source reweighting only."
            ),
            (
                "The ebb2 vendor copy lacks required runtime angle tables, so "
                "the script selected the complete local /home/ubuntu/TES_511_Balloon "
                "PARMA vendor tree. Driver and input-tree hashes are recorded."
            ),
        ],
        "inputs": {
            "broadband_contract": {
                "path": str(CONTRACT),
                "sha256": sha256(CONTRACT),
            },
            "current_broadband_source_card": {
                "path": str(source_card),
                "sha256": sha256(source_card),
            },
            "current_corrected_gamma_spectra": {
                "path_pattern": str(
                    current_spectra[0].parent
                    / "gamma_binNN_*_pdf.spectrum"
                ),
                "sha256_by_file": current_spectrum_hashes,
            },
            "proposal_mono_line_80bins": {
                "path": str(LINE80),
                "sha256": sha256(LINE80),
            },
            "day15_environment_authority": {
                "path": str(DAY15_ENVIRONMENT),
                "sha256": sha256(DAY15_ENVIRONMENT),
            },
            "gamma_scale_81nodes": {
                "path": str(FAMILY_TIME),
                "sha256": sha256(FAMILY_TIME),
            },
            "parma_driver": {
                "path": str(DRIVER),
                "sha256": sha256(DRIVER),
            },
            "parma_driver_source": {
                "path": str(
                    PARMA_ROOT / PARMA_PACKAGE_REL / "code/parma511_driver.cpp"
                ),
                "sha256": sha256(
                    PARMA_ROOT / PARMA_PACKAGE_REL / "code/parma511_driver.cpp"
                ),
            },
            "parma_subroutines_source": {
                "path": str(VENDOR / "subroutines.cpp"),
                "sha256": sha256(VENDOR / "subroutines.cpp"),
            },
            "parma_vendor_input_tree": {
                "path": str(VENDOR / "input"),
                "manifest_scheme": (
                    "sha256(relative_path + NUL + sha256(file) + newline), sorted"
                ),
                "file_count": vendor_tree_files,
                "sha256": vendor_tree_hash,
            },
            "source_builder": {
                "path": str(HERE),
                "sha256": sha256(HERE),
            },
        },
        "outputs": {
            "coarse_line_decomposition_20bins.csv": {
                "rows": len(bin_rows),
                "sha256": output_hashes[
                    "coarse_line_decomposition_20bins.csv"
                ],
            },
            "mono511_target_81x80.csv": {
                "rows": len(target_rows),
                "sha256": output_hashes["mono511_target_81x80.csv"],
            },
            "trajectory_component_scales_81nodes.csv": {
                "rows": len(timeline),
                "sha256": output_hashes[
                    "trajectory_component_scales_81nodes.csv"
                ],
            },
        },
    }
    closure_path = OUT / "source_closure.json"
    closure_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


if __name__ == "__main__":
    build()
