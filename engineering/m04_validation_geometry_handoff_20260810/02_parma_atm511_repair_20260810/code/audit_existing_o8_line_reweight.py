#!/usr/bin/env python3
"""Read-only audit of reusing the retained O8 mono-511 transport.

The script never launches Cosima and does not write files.  It joins the
retained atmospheric compact catalogue to the retained SIM event lineage,
reproduces the primary 420-eV-FWHM response realization, and evaluates
20/40/80-bin PARMA angular importance weights.  ``--deep-sim-audit`` scans all
3,000,000 ``IA INIT`` records to quantify source-bin recovery at printed SIM
precision; without that flag only the selected W511 records are evaluated.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import pickle
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]

OLD_RUN = (
    ROOT
    / "runs/geometry_optimization_20260704"
    / "s3d_o8_atm511_sidecar_3m_20260712"
)
OLD_SOURCE = OLD_RUN / "Atm511SidecarS3dO8_3M.source"
OLD_SIM = OLD_RUN / "Atm511SidecarS3dO8_3M.inc1.id1.sim.gz"
OLD_LOG = OLD_RUN / "cosima_Atm511SidecarS3dO8_3M.log"
OLD_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704"
    / "43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_atm511_replay_summary.json"
)
ATM_CACHE = (
    ROOT
    / "engineering/ea_s3d_o8_all8_detector_response_closure_20260713"
    / "data/s3d_o8_all8_atm511_compact_catalog.pkl"
)
RESPONSE_SUMMARY = (
    ROOT
    / "engineering/ea_detector_response_closure_20260713"
    / "data/o8_energy_response_closure_summary.json"
)

PARMA_CSV = {
    bins: PACKAGE / f"line/parma511_day15_{bins}bins.csv"
    for bins in (20, 40, 80)
}

W2_LOW_KEV = 510.58
W2_HIGH_KEV = 511.42
OLD_LINE_ENERGY_KEV = 511.0
PARMA_LINE_ENERGY_KEV = 510.99895
OLD_EQUAL_MU_WIDTH = 0.1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def parse_old_source() -> list[dict[str, Any]]:
    text = OLD_SOURCE.read_text(encoding="utf-8")
    rows: list[dict[str, Any]] = []
    for bin_id in range(20):
        suffix = "down" if bin_id < 10 else "up"
        name = f"Atm511_bin{bin_id:02d}_{suffix}"
        beam = re.search(
            rf"^{re.escape(name)}\.Beam FarFieldAreaSource\s+"
            r"([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+"
            r"([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$",
            text,
            re.MULTILINE,
        )
        spectrum = re.search(
            rf"^{re.escape(name)}\.Spectrum Mono\s+([-+0-9.eE]+)\s*$",
            text,
            re.MULTILINE,
        )
        flux = re.search(
            rf"^{re.escape(name)}\.Flux\s+([-+0-9.eE]+)\s*$",
            text,
            re.MULTILINE,
        )
        if beam is None or spectrum is None or flux is None:
            raise RuntimeError(f"missing old source definition: {name}")
        rows.append(
            {
                "bin_id": bin_id,
                "source_name": name,
                "direction_label": suffix,
                "theta_low_deg": float(beam.group(1)),
                "theta_high_deg": float(beam.group(2)),
                "phi_low_deg": float(beam.group(3)),
                "phi_high_deg": float(beam.group(4)),
                "line_energy_keV": float(spectrum.group(1)),
                "flux_ph_cm2_s": float(flux.group(1)),
            }
        )
    return rows


def parse_parma_grid(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "bin_id": int(row["theta_bin_id"]),
                "source_id": row["source_id"],
                "mu_low": float(row["parma_mu_low"]),
                "mu_high": float(row["parma_mu_high"]),
                "theta_low_deg": float(row["cosima_theta_low_deg"]),
                "theta_high_deg": float(row["cosima_theta_high_deg"]),
                "line_fraction": float(row["line_fraction"]),
                "line_flux_ph_cm2_s": float(row["line_flux_ph_cm-2_s-1"]),
            }
        )
    return out


def parse_log_summary() -> dict[str, Any]:
    source_counts: dict[str, int] = {}
    observation_time_s: float | None = None
    with OLD_LOG.open("rb") as handle:
        handle.seek(max(0, OLD_LOG.stat().st_size - 2_000_000))
        tail = handle.read().decode("utf-8", errors="replace")
    for name, count in re.findall(
        r"^\s*Source\s+(Atm511_bin\d+_(?:down|up)):\s+(\d+)\s*$",
        tail,
        re.MULTILINE,
    ):
        source_counts[name] = int(count)
    matches = re.findall(
        r"^Observation time:\s+([-+0-9.eE]+)\s+sec\s*$",
        tail,
        re.MULTILINE,
    )
    if matches:
        observation_time_s = float(matches[-1])
    with OLD_LOG.open("rb") as handle:
        prefix = handle.read(100_000).decode("utf-8", errors="replace")
    area_rows = {
        name: float(area)
        for name, area in re.findall(
            r"^(Atm511_bin\d+_(?:down|up)): average start area:\s+"
            r"([-+0-9.eE]+)\s+cm2\s*$",
            prefix,
            re.MULTILINE,
        )
    }
    if len(source_counts) != 20 or observation_time_s is None or len(area_rows) != 20:
        raise RuntimeError("old Cosima log does not contain a complete 20-bin summary")
    areas = sorted(set(area_rows.values()))
    if len(areas) != 1:
        raise RuntimeError(f"old source bins have non-common start areas: {areas}")
    return {
        "source_counts": source_counts,
        "observation_time_s": observation_time_s,
        "start_area_cm2": areas[0],
    }


def load_compact_catalog() -> tuple[dict[str, Any], dict[str, Any]]:
    with ATM_CACHE.open("rb") as handle:
        cached = pickle.load(handle)
    if not isinstance(cached, dict) or not isinstance(cached.get("catalog"), dict):
        raise RuntimeError("unexpected atmospheric compact-cache schema")
    return cached["metadata"], cached["catalog"]


def old_bin_from_init_dir_z(dir_z: float) -> int:
    # FarFieldAreaSource theta describes the source-side sky direction.  The IA
    # INIT vector points inward, hence mu_source=cos(theta_source)=-dir_z.
    return max(0, min(19, int(math.floor((1.0 + dir_z) * 10.0))))


def parma_bin_from_init_dir_z(dir_z: float, bins: int) -> int:
    return max(
        0,
        min(bins - 1, int(math.floor((1.0 + dir_z) * bins / 2.0))),
    )


def source_theta_deg(dir_z: float) -> float:
    return math.degrees(math.acos(max(-1.0, min(1.0, -dir_z))))


def reproduce_primary_response(
    catalog: dict[str, Any], response: dict[str, Any]
) -> tuple[int, float, np.ndarray, set[int]]:
    primary = response["primary_authority"]["atm511_selection"]
    seed = int(primary["response_seed"])
    sigma = float(response["detector_contract"]["paper_sigma_keV"])
    threshold = float(response["detector_contract"]["tes_hit_threshold_keV"])
    hits = np.asarray(catalog["hit_e_keV"], dtype=np.float64).copy()
    hits += np.random.default_rng(seed).normal(0.0, sigma, len(hits))
    hits[hits < threshold] = 0.0
    totals = np.add.reduceat(hits, np.asarray(catalog["hit_start"], dtype=np.int64))
    mask = (totals >= W2_LOW_KEV) & (totals < W2_HIGH_KEV)
    ids = set(int(value) for value in np.asarray(catalog["event_id"])[mask])
    expected = int(
        primary["windows"]["w2_510p58_511p42"]["by_stream"]
        ["atm511_sidecar"]["side_compton_fov_pass_events"]
    )
    if len(ids) != expected:
        raise RuntimeError(
            f"primary response membership count {len(ids)} != retained {expected}"
        )
    return seed, sigma, totals, ids


def importance_ratio(
    dir_z: float,
    grid_bins: int,
    old_rows: list[dict[str, Any]],
    parma_rows: dict[int, list[dict[str, Any]]],
) -> float:
    old_bin = old_bin_from_init_dir_z(dir_z)
    new_bin = parma_bin_from_init_dir_z(dir_z, grid_bins)
    # Old proposal is piecewise constant in 20 equal-mu bins.  A grid with G
    # bins has delta-mu=2/G, so density_new/density_old is
    # (G/20)*flux_new_subbin/flux_old_20bin.
    return (
        (grid_bins / 20.0)
        * float(parma_rows[grid_bins][new_bin]["line_flux_ph_cm2_s"])
        / float(old_rows[old_bin]["flux_ph_cm2_s"])
    )


def weighted_result(
    rows: list[dict[str, Any]],
    selected_ids: set[int],
    grid_bins: int,
    observation_time_s: float,
    old_rows: list[dict[str, Any]],
    parma_rows: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    event_weights = [
        importance_ratio(
            float(row["dir_z"]), grid_bins, old_rows, parma_rows
        )
        / observation_time_s
        for row in rows
        if int(row["event_id"]) in selected_ids
    ]
    rate = float(sum(event_weights))
    variance = float(sum(value * value for value in event_weights))
    sigma = math.sqrt(variance)
    ess = rate * rate / variance if variance > 0.0 else 0.0
    return {
        "angular_grid_equal_mu_bins": grid_bins,
        "selected_events": len(event_weights),
        "importance_weighted_rate_cps": rate,
        "mc_stat_sigma_cps": sigma,
        "mc_relative_sigma": sigma / rate if rate > 0.0 else None,
        "importance_effective_sample_size": ess,
    }


def deep_sim_audit(log_counts: list[int]) -> dict[str, Any]:
    inferred = [0] * 20
    boundary_candidates = [0] * 19
    ia_init = 0
    source_name_records = 0
    source_id_records = 0
    beam_type_records = 0
    internal_dir_z_edges = [-0.9 + 0.1 * index for index in range(19)]
    with gzip.open(OLD_SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            if "Atm511_bin" in raw:
                source_name_records += 1
            if "SourceID" in raw or re.match(r"^SI\s", raw):
                source_id_records += 1
            if raw.startswith("BeamType"):
                beam_type_records += 1
            if not raw.startswith("IA INIT"):
                continue
            fields = [part.strip() for part in raw.split("IA INIT", 1)[1].split(";")]
            dir_z = float(fields[18])
            inferred[old_bin_from_init_dir_z(dir_z)] += 1
            ia_init += 1
            for edge_index, edge in enumerate(internal_dir_z_edges):
                if abs(dir_z - edge) <= 0.0000050001:
                    boundary_candidates[edge_index] += 1
    deltas = [actual - expected for actual, expected in zip(inferred, log_counts)]
    return {
        "ia_init_records": ia_init,
        "source_name_records": source_name_records,
        "source_id_records": source_id_records,
        "beam_type_header_records": beam_type_records,
        "direction_inferred_counts": inferred,
        "log_source_counts": log_counts,
        "direction_minus_log_counts": deltas,
        "max_abs_bin_count_delta": max(abs(value) for value in deltas),
        "rounded_boundary_candidates_by_internal_edge": boundary_candidates,
        "rounded_boundary_candidates_total": sum(boundary_candidates),
        "boundary_candidate_definition": (
            "printed dir_z lies within half of the 5-decimal rounding unit of "
            "an old equal-mu internal boundary"
        ),
    }


def run(deep: bool) -> dict[str, Any]:
    old_rows = parse_old_source()
    parma_rows = {bins: parse_parma_grid(path) for bins, path in PARMA_CSV.items()}
    log = parse_log_summary()
    cache_metadata, catalog = load_compact_catalog()
    old_summary = load_json(OLD_SUMMARY)
    response = load_json(RESPONSE_SUMMARY)
    final_rows = old_summary["final_w2_entry_surface_audit"]["o8"]["rows"]
    unsmeared_ids = {int(row["event_id"]) for row in final_rows}
    seed, detector_sigma, measured_totals, response_ids = reproduce_primary_response(
        catalog, response
    )

    event_index = {
        int(event_id): index
        for index, event_id in enumerate(np.asarray(catalog["event_id"]))
    }
    event_rows: list[dict[str, Any]] = []
    for row in final_rows:
        event_id = int(row["event_id"])
        index = event_index[event_id]
        dir_z = float(row["dir_z"])
        old_bin = old_bin_from_init_dir_z(dir_z)
        theta = source_theta_deg(dir_z)
        event_rows.append(
            {
                "event_id": event_id,
                "dir_x": float(row["dir_x"]),
                "dir_y": float(row["dir_y"]),
                "dir_z": dir_z,
                "source_theta_deg": theta,
                "old_bin20": old_bin,
                "source_edge_margin_deg": min(
                    theta - float(old_rows[old_bin]["theta_low_deg"]),
                    float(old_rows[old_bin]["theta_high_deg"]) - theta,
                ),
                "parma_bin40": parma_bin_from_init_dir_z(dir_z, 40),
                "parma_bin80": parma_bin_from_init_dir_z(dir_z, 80),
                "ratio20": importance_ratio(dir_z, 20, old_rows, parma_rows),
                "ratio40": importance_ratio(dir_z, 40, old_rows, parma_rows),
                "ratio80": importance_ratio(dir_z, 80, old_rows, parma_rows),
                "raw_total_keV": float(catalog["raw_total_keV"][index]),
                "primary_response_total_keV": float(measured_totals[index]),
                "active_keV": float(catalog["active_keV"][index]),
                "unsmeared_w2": event_id in unsmeared_ids,
                "primary_420eV_w2": event_id in response_ids,
            }
        )

    unsmeared = {
        str(grid): weighted_result(
            final_rows,
            unsmeared_ids,
            grid,
            float(log["observation_time_s"]),
            old_rows,
            parma_rows,
        )
        for grid in (20, 40, 80)
    }
    primary = {
        str(grid): weighted_result(
            final_rows,
            response_ids,
            grid,
            float(log["observation_time_s"]),
            old_rows,
            parma_rows,
        )
        for grid in (20, 40, 80)
    }

    by_old_bin_unsmeared = Counter(row["old_bin20"] for row in event_rows)
    by_old_bin_primary = Counter(
        row["old_bin20"] for row in event_rows if row["primary_420eV_w2"]
    )
    source_bins: list[dict[str, Any]] = []
    for index, old in enumerate(old_rows):
        new = parma_rows[20][index]
        source_bins.append(
            {
                **old,
                "old_generated_events": int(log["source_counts"][old["source_name"]]),
                "parma20_flux_ph_cm2_s": float(new["line_flux_ph_cm2_s"]),
                "parma20_fraction": float(new["line_fraction"]),
                "parma20_to_old_flux_ratio": (
                    float(new["line_flux_ph_cm2_s"])
                    / float(old["flux_ph_cm2_s"])
                ),
                "unsmeared_w2_events": int(by_old_bin_unsmeared.get(index, 0)),
                "primary_420eV_w2_events": int(by_old_bin_primary.get(index, 0)),
            }
        )

    occupied_bins = set(by_old_bin_unsmeared)
    selected_bin_flux_share = sum(
        float(parma_rows[20][index]["line_fraction"])
        for index in occupied_bins
    )
    total_old_flux = sum(float(row["flux_ph_cm2_s"]) for row in old_rows)
    total_parma_flux = sum(
        float(row["line_flux_ph_cm2_s"]) for row in parma_rows[20]
    )

    hashes = {
        rel(path): sha256(path)
        for path in (
            OLD_SOURCE,
            OLD_SIM,
            OLD_LOG,
            OLD_SUMMARY,
            ATM_CACHE,
            RESPONSE_SUMMARY,
            PARMA_CSV[20],
            PARMA_CSV[40],
            PARMA_CSV[80],
        )
    }
    log_count_list = [
        int(log["source_counts"][row["source_name"]]) for row in old_rows
    ]
    deep_result = deep_sim_audit(log_count_list) if deep else None

    return {
        "status": "DIAGNOSTIC_REWEIGHT_REPRODUCED_BUT_FAILS_PASS_PARMA_511_STATISTICS",
        "scope": {
            "simulation_launched": False,
            "transport_launched": False,
            "other_particle_modules_changed": False,
            "allowed_use": "offline diagnostic/cross-check of the retained O8 mono-line SIM",
            "not_allowed_use": "paper-authority PASS_PARMA_511 detector response",
        },
        "input_hashes": hashes,
        "old_module": {
            "source": rel(OLD_SOURCE),
            "sim": rel(OLD_SIM),
            "log": rel(OLD_LOG),
            "sim_size_bytes": OLD_SIM.stat().st_size,
            "line_energy_keV": OLD_LINE_ENERGY_KEV,
            "total_flux_ph_cm2_s": total_old_flux,
            "observation_time_s": float(log["observation_time_s"]),
            "start_area_cm2": float(log["start_area_cm2"]),
            "generated_events": sum(log_count_list),
        },
        "parma_module": {
            "line_energy_keV": PARMA_LINE_ENERGY_KEV,
            "old_minus_parma_energy_keV": (
                OLD_LINE_ENERGY_KEV - PARMA_LINE_ENERGY_KEV
            ),
            "total_flux_ph_cm2_s": total_parma_flux,
            "total_flux_ratio_to_old": total_parma_flux / total_old_flux,
            "angular_grids_equal_mu_bins": [20, 40, 80],
        },
        "mapping": {
            "source_direction_formula": "mu_source=cos(theta_source)=-IA_INIT.dir_z",
            "old_bin_formula": "floor((1+dir_z)*10), clipped to [0,19]",
            "parma_bin_formula": "floor((1+dir_z)*G/2), clipped to [0,G-1]",
            "event_importance_ratio": (
                "(G/20)*PARMA_flux_G_bin/old_flux_20_bin"
            ),
            "event_rate_weight_cps": "importance_ratio / old_observation_time_s",
            "explicit_source_id_in_sim": False,
            "direction_lineage_available_in_sim": True,
        },
        "compact_catalog": {
            "path": rel(ATM_CACHE),
            "top_level_keys": ["metadata", "catalog"],
            "catalog_fields": list(catalog.keys()),
            "metadata": cache_metadata,
            "tes_events": len(catalog["event_id"]),
            "pixel_hits": len(catalog["hit_e_keV"]),
            "active_only_events": int(
                catalog["active_only_events_by_stream"]["atm511_sidecar"]
            ),
            "direction_or_source_bin_fields_present": False,
            "join_key_to_raw_sim": "event_id -> SIM ID/local_id",
        },
        "source_bins": source_bins,
        "w2_events": {
            "unsmeared_count": len(unsmeared_ids),
            "primary_420eV_count": len(response_ids),
            "primary_response_seed": seed,
            "detector_sigma_keV": detector_sigma,
            "removed_by_primary_response": sorted(unsmeared_ids - response_ids),
            "unsmeared_counts_by_old20_bin": {
                str(key): value for key, value in sorted(by_old_bin_unsmeared.items())
            },
            "primary_counts_by_old20_bin": {
                str(key): value for key, value in sorted(by_old_bin_primary.items())
            },
            "parma_flux_share_in_old20_bins_with_at_least_one_unsmeared_w2_event": selected_bin_flux_share,
            "parma_flux_share_in_old20_bins_with_zero_unsmeared_w2_events": 1.0 - selected_bin_flux_share,
            "rows": event_rows,
        },
        "offline_reweight": {
            "unsmeared_9": unsmeared,
            "primary_420eV_8": primary,
            "unsmeared_relative_40_vs_80": (
                float(unsmeared["40"]["importance_weighted_rate_cps"])
                / float(unsmeared["80"]["importance_weighted_rate_cps"])
                - 1.0
            ),
            "primary_relative_40_vs_80": (
                float(primary["40"]["importance_weighted_rate_cps"])
                / float(primary["80"]["importance_weighted_rate_cps"])
                - 1.0
            ),
            "naive_scalar_rate_unsmeared_cps": (
                len(unsmeared_ids)
                / float(log["observation_time_s"])
                * total_parma_flux
                / total_old_flux
            ),
            "naive_scalar_rate_primary_cps": (
                len(response_ids)
                / float(log["observation_time_s"])
                * total_parma_flux
                / total_old_flux
            ),
        },
        "deep_sim_lineage_audit": deep_result,
        "gate": {
            "handoff_required_final_w2_events_or_relative_error": (
                ">=400 final events or <=5% pure-counting relative standard error"
            ),
            "handoff_required_40_vs_80_combined_count_error": "<1.5%",
            "actual_unsmeared_events": len(unsmeared_ids),
            "actual_primary_events": len(response_ids),
            "actual_unsmeared_80bin_relative_mc_sigma": float(
                unsmeared["80"]["mc_relative_sigma"]
            ),
            "actual_primary_80bin_relative_mc_sigma": float(
                primary["80"]["mc_relative_sigma"]
            ),
            "passes_PASS_PARMA_511_detector_response": False,
            "decision": (
                "Existing transport supports a zero-simulation angular-reweight "
                "diagnostic only. If paper-authority PASS_PARMA_511 is required, "
                "transport only the corrected atmospheric 510.99895-keV mono-line "
                "module; reuse and recompose every other retained module."
            ),
        },
        "limitations": [
            "The SIM has IA INIT direction but no explicit source name or source-bin ID.",
            "IA INIT direction is printed to five decimals; full-stream boundary lineage is not exact.",
            "The compact atmospheric cache omits direction/source-bin fields and aggregates active-only events.",
            "Fourteen of twenty old bins have zero unsmeared W2 survivors; they contain most of the new PARMA line flux.",
            "The retained transport used 511.0 keV, 0.00105 keV above the PARMA mono energy.",
            "The primary count of eight is one deterministic detector-response realization, not a high-stat response coefficient.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--deep-sim-audit",
        action="store_true",
        help="scan all 3M IA INIT records; still read-only and launches no simulation",
    )
    args = parser.parse_args()
    print(json.dumps(run(args.deep_sim_audit), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
