#!/usr/bin/env python3
"""Reproduce the retained O8 prompt-gamma line-term deduplication audit.

This program is deliberately analysis-only.  It never invokes Cosima, never
generates a particle, never performs transport, and never writes into the
repository.  A tiny C++ executable is compiled in a temporary directory only
to evaluate the unmodified official PARMA analytic functions needed at the
single legacy wide-bin node.  Results are emitted as JSON on stdout.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import multiprocessing as mp
import pickle
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
RUN = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o8_fullstat_prompt_all8_20260712"
)
SOURCE_CARD = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "43_geoopt_s3d_o8_fallback_20260712/config/full_prompt_all8"
    / "source_cards/Background_gamma_fullsphere20.source"
)
CATALOG = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "43_geoopt_s3d_o8_fallback_20260712/fullchain/step05/work"
    / "event_catalog.pkl"
)
RESPONSE = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "43_geoopt_s3d_o8_fallback_20260712/fullchain/step05"
    / "step05_s3d_o8_fullchain_l1_response_summary.json"
)
SPECTRA = ROOT / "expacs_fullsphere_20bin_sources"
VENDOR = PACKAGE / "vendor/parma_cpp_official_20260810"

W = 118.3
RC_GV = 11.6
DEPTH_G_CM2 = 3.84535
G_PARAMETER = 0.0
LINE_NODE_MEV = 0.56608
LINE_LEFT_MEV = 0.44965
LINE_RIGHT_MEV = 0.71264
RATE_PER_EVENT_CPS = 0.005426798726004732

GRIDS: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
WANTED: dict[str, set[int]] = {}

PROBE_SOURCE = r"""
#include <cstdlib>
#include <iomanip>
#include <iostream>
double getSpecCpp(int, double, double, double, double, double);
double getSpecAngFinalCpp(int, double, double, double, double, double, double);
double get511fluxCpp(double, double, double);
int main(int argc, char** argv) {
  if (argc != 7) return 2;
  const double s = std::strtod(argv[1], nullptr);
  const double r = std::strtod(argv[2], nullptr);
  const double d = std::strtod(argv[3], nullptr);
  const double g = std::strtod(argv[4], nullptr);
  const double e = std::strtod(argv[5], nullptr);
  const double mu = std::strtod(argv[6], nullptr);
  const double c = getSpecCpp(33, s, r, d, e, g)
                 * getSpecAngFinalCpp(6, s, r, d, e, g, mu);
  std::cout << std::setprecision(17) << c << ","
            << get511fluxCpp(s, r, d) << "\n";
  return 0;
}
"""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def compile_probe(tmp: Path) -> Path:
    source = tmp / "parma_gamma_continuum_probe.cpp"
    binary = tmp / "parma_gamma_continuum_probe"
    source.write_text(PROBE_SOURCE, encoding="utf-8")
    subprocess.run(
        [
            "g++",
            "-std=c++17",
            "-O2",
            str(source),
            str(VENDOR / "subroutines.cpp"),
            "-o",
            str(binary),
        ],
        check=True,
        cwd=VENDOR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return binary


def evaluate_node(binary: Path, mu: float) -> tuple[float, float]:
    output = subprocess.check_output(
        [
            str(binary),
            str(W),
            str(RC_GV),
            str(DEPTH_G_CM2),
            str(G_PARAMETER),
            str(LINE_NODE_MEV),
            str(mu),
        ],
        cwd=VENDOR,
        text=True,
    ).strip()
    continuum, line_flux = output.split(",")
    return float(continuum), float(line_flux)


def gamma_manifest_rows() -> list[dict[str, str]]:
    with (SPECTRA / "manifest.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        return [row for row in csv.DictReader(handle) if row["particle"] == "gamma"]


def raw_grid(path: Path) -> tuple[np.ndarray, np.ndarray]:
    x: list[float] = []
    y: list[float] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) == 2:
            x.append(float(fields[0]))
            y.append(float(fields[1]))
    return np.asarray(x, dtype=float), np.asarray(y, dtype=float)


def make_grids(binary: Path) -> tuple[list[dict[str, Any]], float, float]:
    global GRIDS
    GRIDS = []
    closure_rows: list[dict[str, Any]] = []
    bump_flux = 0.0
    old_flux = 0.0
    line_flux_values: list[float] = []
    for row in gamma_manifest_rows():
        x, old = raw_grid(ROOT / row["raw_spectrum_path"])
        continuum = old.copy()
        node = int(np.argmin(np.abs(x - LINE_NODE_MEV)))
        if abs(float(x[node]) - LINE_NODE_MEV) > 1.0e-12:
            raise RuntimeError(f"line node absent: {row['raw_spectrum_path']}")
        continuum[node], line_flux = evaluate_node(binary, float(row["mu_mid"]))
        line_flux_values.append(line_flux)
        GRIDS.append((x, old, continuum))
        domega = float(row["delta_omega_sr"])
        bump_flux += float(np.trapz(old - continuum, x)) * domega
        old_flux += float(row["flux_cm2_s"])
        closure_rows.append(
            {
                "bin": int(row["bin_id"]),
                "mu_mid": float(row["mu_mid"]),
                "old_line_node": float(old[node]),
                "continuum_line_node": float(continuum[node]),
                "node_ratio": float(continuum[node] / old[node]),
            }
        )
    if max(line_flux_values) - min(line_flux_values) > 1.0e-12:
        raise RuntimeError("PARMA line flux changed between angular evaluations")
    return closure_rows, bump_flux, old_flux


def source_bin(dir_z: float) -> int:
    return max(0, min(19, int(math.floor((1.0 + dir_z) * 10.0))))


def boundary_candidate(dir_z: float) -> bool:
    edge = round(dir_z * 10.0)
    return bool(
        -9 <= edge <= 9
        and abs(dir_z - edge / 10.0) <= 0.0000050001
    )


def event_weight(bin_id: int, energy_keV: float) -> float:
    if not LINE_LEFT_MEV < energy_keV < LINE_RIGHT_MEV:
        return 1.0
    x, old, continuum = GRIDS[bin_id]
    denominator = float(np.interp(energy_keV, x, old))
    return float(np.interp(energy_keV, x, continuum) / denominator)


def scan_raw_sim(path: Path) -> dict[str, Any]:
    inferred = np.zeros(20, dtype=np.int64)
    affected = np.zeros(20, dtype=np.int64)
    sum_w = np.zeros(20, dtype=float)
    sum_w2 = np.zeros(20, dtype=float)
    energy_min = math.inf
    energy_max = -math.inf
    below_one = 0
    in_broad_initial = 0
    in_w2_initial = 0
    all_boundary = 0
    affected_boundary = 0
    n_init = 0
    weight_min = 1.0
    weight_max = 0.0
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if not line.startswith("IA INIT"):
                continue
            fields = line.rsplit(";", 7)
            dir_z = float(fields[3])
            energy = float(fields[7])
            bin_id = source_bin(dir_z)
            inferred[bin_id] += 1
            n_init += 1
            energy_min = min(energy_min, energy)
            energy_max = max(energy_max, energy)
            below_one += energy < 1.0
            in_broad_initial += 480.0 <= energy < 550.0
            in_w2_initial += 510.0 <= energy < 512.0
            is_boundary = boundary_candidate(dir_z)
            all_boundary += is_boundary
            if LINE_LEFT_MEV < energy < LINE_RIGHT_MEV:
                weight = event_weight(bin_id, energy)
                affected[bin_id] += 1
                sum_w[bin_id] += weight
                sum_w2[bin_id] += weight * weight
                weight_min = min(weight_min, weight)
                weight_max = max(weight_max, weight)
                affected_boundary += is_boundary
    return {
        "inferred": inferred,
        "affected": affected,
        "sum_w": sum_w,
        "sum_w2": sum_w2,
        "n_init": n_init,
        "energy_min": energy_min,
        "energy_max": energy_max,
        "below_one": below_one,
        "in_broad_initial": in_broad_initial,
        "in_w2_initial": in_w2_initial,
        "all_boundary": all_boundary,
        "affected_boundary": affected_boundary,
        "weight_min": weight_min,
        "weight_max": weight_max,
    }


def scan_catalog_membership(path: Path) -> tuple[str, dict[int, float]]:
    wanted = WANTED[str(path)]
    found: dict[int, float] = {}
    current_id: int | None = None
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("ID "):
                current_id = int(line.split()[1])
                continue
            if current_id not in wanted or not line.startswith("IA INIT"):
                continue
            fields = line.rsplit(";", 7)
            dir_z = float(fields[3])
            energy = float(fields[7])
            if LINE_LEFT_MEV < energy < LINE_RIGHT_MEV:
                found[current_id] = event_weight(source_bin(dir_z), energy)
    return str(path), found


def log_source_counts() -> list[int]:
    counts = [0] * 20
    pattern = re.compile(
        r"^\s*Source\s+Atm_gamma_bin(\d+)_(?:down|up):\s+(\d+)\s*$",
        re.MULTILINE,
    )
    for path in sorted((RUN / "logs").glob("Background_gamma*.log")):
        for bin_id, count in pattern.findall(
            path.read_text(encoding="utf-8", errors="ignore")
        ):
            counts[int(bin_id)] += int(count)
    return counts


def summarize_raw(files: list[Path]) -> dict[str, Any]:
    ctx = mp.get_context("fork")
    with ctx.Pool(len(files)) as pool:
        parts = pool.map(scan_raw_sim, files)
    inferred = sum(
        (row["inferred"] for row in parts), np.zeros(20, dtype=np.int64)
    )
    affected = sum(
        (row["affected"] for row in parts), np.zeros(20, dtype=np.int64)
    )
    sum_w = sum((row["sum_w"] for row in parts), np.zeros(20, dtype=float))
    sum_w2 = sum((row["sum_w2"] for row in parts), np.zeros(20, dtype=float))
    logs = np.asarray(log_source_counts(), dtype=np.int64)
    n_affected = int(affected.sum())
    equivalent_after = float(sum_w.sum())
    return {
        "events": int(sum(row["n_init"] for row in parts)),
        "energy_min_keV": float(min(row["energy_min"] for row in parts)),
        "energy_max_keV": float(max(row["energy_max"] for row in parts)),
        "events_below_1_keV": int(sum(row["below_one"] for row in parts)),
        "initial_events_480_550_keV": int(
            sum(row["in_broad_initial"] for row in parts)
        ),
        "initial_events_510_512_keV": int(
            sum(row["in_w2_initial"] for row in parts)
        ),
        "direction_inferred_counts": inferred.tolist(),
        "cosima_log_source_counts": logs.tolist(),
        "max_abs_bin_count_difference": int(np.max(np.abs(inferred - logs))),
        "all_direction_boundary_candidates": int(
            sum(row["all_boundary"] for row in parts)
        ),
        "affected_events": n_affected,
        "affected_events_by_bin": affected.tolist(),
        "affected_direction_boundary_candidates": int(
            sum(row["affected_boundary"] for row in parts)
        ),
        "equivalent_events_after_weight": equivalent_after,
        "equivalent_events_removed": n_affected - equivalent_after,
        "finite_mc_removed_generation_rate_cps": (
            n_affected - equivalent_after
        )
        * RATE_PER_EVENT_CPS,
        "sum_weight_squared": float(sum_w2.sum()),
        "minimum_weight": float(min(row["weight_min"] for row in parts)),
        "maximum_weight_inside_support": float(
            max(row["weight_max"] for row in parts)
        ),
    }


def summarize_catalog(files: list[Path]) -> dict[str, Any]:
    global WANTED
    with CATALOG.open("rb") as handle:
        catalog = pickle.load(handle)
    gamma_mask = (catalog["stream"] == "prompt") & (catalog["tag"] == "gamma")
    source_files = sorted(set(str(value) for value in catalog["source_file"][gamma_mask]))
    WANTED = {
        path: set(
            int(value)
            for value in catalog["local_id"][
                gamma_mask & (catalog["source_file"] == path)
            ]
        )
        for path in source_files
    }
    if {str(path) for path in files} != set(source_files):
        raise RuntimeError("catalog gamma file set does not match retained SIM files")
    ctx = mp.get_context("fork")
    with ctx.Pool(len(files)) as pool:
        weight_maps = dict(pool.map(scan_catalog_membership, files))
    indices: list[int] = []
    weights: list[float] = []
    for index in np.flatnonzero(gamma_mask):
        weight = weight_maps[str(catalog["source_file"][index])].get(
            int(catalog["local_id"][index])
        )
        if weight is not None:
            indices.append(int(index))
            weights.append(weight)
    selected = np.asarray(indices, dtype=np.int64)
    event_weights = np.asarray(weights, dtype=float)
    rates = catalog["rate_hz"][selected]
    tes = catalog["tes_total_keV"][selected]
    return {
        "catalog_event_rows": int(len(catalog["stream"])),
        "catalog_prompt_gamma_rows": int(np.sum(gamma_mask)),
        "affected_rows": int(len(selected)),
        "old_rate_sum_cps": float(np.sum(rates)),
        "deduped_rate_sum_cps": float(np.sum(rates * event_weights)),
        "removed_rate_sum_cps": float(np.sum(rates * (1.0 - event_weights))),
        "tes_nonzero_rows": int(np.sum(tes > 0.0)),
        "active_volume_nonzero_rows": int(
            np.sum(catalog["bgo_total_keV"][selected] > 0.0)
        ),
        "broad_480_550_affected_rows": int(
            np.sum((tes >= 480.0) & (tes < 550.0))
        ),
        "w2_affected_rows": int(
            np.sum((tes >= 510.58) & (tes < 511.42))
        ),
    }


def selected_gamma_summary() -> dict[str, Any]:
    payload = json.loads(RESPONSE.read_text(encoding="utf-8"))
    out: dict[str, Any] = {}
    for name in ("broad_480_550", "w2_510p58_511p42"):
        window = payload["windows"][name]
        prompt = window["by_stream"]["prompt"]
        component = next(
            row
            for row in window["physical_reference_flux"]["uncertainty_95"][
                "prompt_components"
            ]
            if row["tag"] == "gamma"
        )
        out[name] = {
            "all_prompt_raw_events": int(prompt["raw_events"]),
            "all_prompt_active_events": int(prompt["active_veto_pass_events"]),
            "all_prompt_final_events": int(prompt["side_compton_fov_pass_events"]),
            "gamma_final_events": int(component["events"]),
            "gamma_final_rate_cps": float(component["rate_cps"]),
            "gamma_upper95_cps": float(component["rate_upper95_cps"]),
        }
    return out


def input_hashes(files: list[Path]) -> dict[str, str]:
    fixed = [
        Path(__file__),
        SOURCE_CARD,
        RUN / "run_manifest.csv",
        RUN / "normalization.json",
        CATALOG,
        RESPONSE,
        SPECTRA / "manifest.csv",
        SPECTRA / "extraction_log.csv",
        SPECTRA / "raw_expacs/spectrum_gamma_bin00_theta18.19_BHNo.dat",
        SPECTRA / "cosima_spectra_dp/gamma_bin00_theta18.19_pdf.dat",
        SPECTRA
        / "cosima_spectra_dp_2602units/gamma_bin00_theta18.19_pdf.dat",
        VENDOR / "subroutines.cpp",
    ]
    paths = fixed + files
    ctx = mp.get_context("fork")
    with ctx.Pool(min(len(paths), 12)) as pool:
        values = pool.map(sha256, paths)
    return {rel(path): value for path, value in zip(paths, values)}


def main() -> int:
    files = sorted(
        RUN.glob("Background_gamma_fullsphere20_rep01_part*.inc1.id1.sim.gz")
    )
    if len(files) != 12:
        raise RuntimeError(f"expected 12 retained gamma SIMs, found {len(files)}")
    with tempfile.TemporaryDirectory(prefix="o8_gamma_line_dedup_") as tmp_name:
        probe = compile_probe(Path(tmp_name))
        closure, bump_flux, old_flux = make_grids(probe)
        raw = summarize_raw(files)
        catalog = summarize_catalog(files)
    observation_time = 1.0 / RATE_PER_EVENT_CPS
    payload = {
        "status": "REPRODUCED_OFFLINE_LINE_TERM_DEDUP__NO_SIMULATION",
        "scope": {
            "cosima_launched": False,
            "transport_launched": False,
            "particle_generation_launched": False,
            "repository_files_written": False,
            "temporary_analytic_parma_probe_only": True,
        },
        "scientific_blocker": {
            "whole_legacy_prompt_gamma_axis_factor_too_low": 1000.0,
            "applies_only_to_line_node": False,
            "resolved_by_this_line_dedup": False,
            "continuum_or_other_module_rerun_authorized": False,
        },
        "line_support_actual_sim_keV": [LINE_LEFT_MEV, LINE_RIGHT_MEV],
        "line_node_actual_sim_keV": LINE_NODE_MEV,
        "old_total_flux_ph_cm2_s": old_flux,
        "line_bump_integral_ph_cm2_s": bump_flux,
        "deduped_flux_ph_cm2_s": old_flux - bump_flux,
        "analytic_expected_removed_generation_rate_cps": (
            10000000.0 / observation_time * bump_flux / old_flux
        ),
        "parma_node_closure": closure,
        "raw_sim": raw,
        "catalog": catalog,
        "selected_windows": selected_gamma_summary(),
        "input_sha256": input_hashes(files),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
