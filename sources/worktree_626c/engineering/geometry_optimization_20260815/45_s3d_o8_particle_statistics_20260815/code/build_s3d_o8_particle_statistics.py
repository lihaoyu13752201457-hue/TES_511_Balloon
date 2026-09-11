#!/usr/bin/env python3
"""Build the frozen S3d-O8 all-particle statistics record.

This is a read-only re-analysis of the published 2026-08-13 corrected-keV
M05 authority.  It does not start Cosima/Geant4 and it never reads the older
pre-unit-repair package-43 Step05 rates as current statistics.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path


AUTHORITY = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813"
)
SOURCE_CONTRACT = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "particle_source_unit_repair_20260811/data/source_contract_manifest.json"
)
GEOMETRY_SETUP = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/"
    "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)

PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
AUDIT = PACKAGE / "audit"

FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
LABELS = {
    "p": "p (proton)",
    "n": "n (neutron)",
    "alpha": "alpha",
    "gamma": "gamma",
    "eminus": "e-",
    "eplus": "e+",
    "muminus": "mu-",
    "muplus": "mu+",
}

PINNED = {
    "analysis_inputs": (
        AUTHORITY / "analysis_inputs.json",
        "9184f97c0252eeb97cc13f1da9ae2519f34281450c9c00b509fef7c1b8ecb90b",
    ),
    "input_audit": (
        AUTHORITY / "outputs/00_input_audit/input_audit.json",
        "79b431602510fa1ef52a29888c66c83c944f0e874eff7f8e5988f7c8e9aded84",
    ),
    "prompt_input_manifest": (
        AUTHORITY / "outputs/01_prompt/prompt_input_manifest.csv",
        "786e03faefed9971d6813a2bb9bf5fb76387cf627a1980844ff6fb58c18f9b9a",
    ),
    "prompt_cutflow": (
        AUTHORITY / "outputs/01_prompt/prompt_cutflow.csv",
        "016b4a158515ee83ed9a0793a06095644b66f60c507b2ddd482589372176ec96",
    ),
    "prompt_summary": (
        AUTHORITY / "outputs/01_prompt/summary.json",
        "5afcfaa19660d9843046332e4d78e648cb69695bf9595e78210e391483fec432",
    ),
    "activation_cells": (
        AUTHORITY / "outputs/02_activation/activation_cells.csv",
        "ad52b53ae93e91755b04fef7bed5a9d30f1c33a7649411ae220a62c2d9bb5e19",
    ),
    "day15_inventory": (
        AUTHORITY / "outputs/02_activation/day15_inventory.csv",
        "59581fd8249f1740641a63c4b57715aa4a614b417014c4470e0b13e40e6bc7e6",
    ),
    "day15_summary": (
        AUTHORITY / "outputs/02_activation/day15_summary.json",
        "9197846e26b180d62b3d46bff516677494660968578cc7462760c845c10af7ba",
    ),
    "delayed_source_index": (
        AUTHORITY / "outputs/02_activation/delayed_source_index.csv",
        "bfc4c9e0afa175f2613f97cf09bce0ee3f18e0d3cde84cd901171bf086be83d3",
    ),
    "delayed_input_manifest": (
        AUTHORITY / "outputs/03_delayed/delayed_input_manifest.csv",
        "c7ecc85d9e8591e5939009ca9aebc8871ff0bc4ddcb4387dfc04fa62279325f7",
    ),
    "delayed_summary": (
        AUTHORITY / "outputs/03_delayed/summary.json",
        "d666f5396c2d863f25b9c23baee4526be1c602fae5d4732e83c14aac344f99b0",
    ),
    "common_cutflow": (
        AUTHORITY / "outputs/04_common_response/common_cutflow.csv",
        "60b1740ba1e534b31eb8273c5fc4e361a6524acd37bc299a0ef167c94cbfcbfb",
    ),
    "common_summary": (
        AUTHORITY / "outputs/04_common_response/summary.json",
        "464f512b45bae6f90b9e0281cc5a591a5ed8c9e420589fd7270fa4234a58e6c0",
    ),
    "signal_acceptance": (
        AUTHORITY / "outputs/04_common_response/signal_acceptance_effective_area.csv",
        "0c4d958b65d2bd4b2915dc165f8ad20085b9ae69d278985c98e8585b46e9ac6a",
    ),
    "matched_family_budget": (
        AUTHORITY / "outputs/05_matched_comparison/w2_stream_family_budget.csv",
        "b8959240cc979cce12265874c52df67263e038afbc0aff494e6b3a42f1fd9e52",
    ),
    "matched_summary": (
        AUTHORITY / "outputs/05_matched_comparison/summary.json",
        "04450c6c0c87e5b059b7b182545cd9451575f1502147d41971fb3ef9c2a9d328",
    ),
    "mission_summary": (
        AUTHORITY / "outputs/06_mission/summary.json",
        "c9cc307cf5761233b71aaa0b7ac16ec783f0a93557bc87f14ec032fbfbbad2ce",
    ),
    "mission_timeline": (
        AUTHORITY / "outputs/06_mission/mission_timeline.csv",
        "ea520aa87b5d8acaa438861b6750645e98cc06f32c6d9beabb065d1a9b4a3549",
    ),
    "source_contract": (
        SOURCE_CONTRACT,
        "5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326",
    ),
    "geometry_setup": (
        GEOMETRY_SETUP,
        "86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec",
    ),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path):
    return json.loads(path.read_text())


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def close(a: float, b: float, *, atol: float = 1e-12, rtol: float = 1e-10) -> bool:
    return math.isclose(a, b, abs_tol=atol, rel_tol=rtol)


def only(rows: list[dict], **predicates) -> dict:
    selected = [r for r in rows if all(r.get(k) == v for k, v in predicates.items())]
    if len(selected) != 1:
        raise RuntimeError(f"Expected exactly one row for {predicates}, got {len(selected)}")
    return selected[0]


def f(value) -> float:
    return float(value)


def i(value) -> int:
    return int(value)


def fmt(value: float) -> str:
    if value == 0:
        return "0"
    if abs(value) < 1e-4 or abs(value) >= 1e5:
        return f"{value:.8e}"
    return f"{value:.10g}"


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    AUDIT.mkdir(parents=True, exist_ok=True)

    source_records = []
    for source_id, (path, expected_hash) in PINNED.items():
        if not path.is_file():
            raise RuntimeError(f"Missing pinned authority: {path}")
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"Authority hash drift for {source_id}: expected {expected_hash}, got {actual_hash}"
            )
        source_records.append(
            {
                "id": source_id,
                "path": str(path),
                "sha256": actual_hash,
                "size_bytes": path.stat().st_size,
            }
        )

    input_audit = read_json(PINNED["input_audit"][0])
    prompt_summary = read_json(PINNED["prompt_summary"][0])
    delayed_summary = read_json(PINNED["delayed_summary"][0])
    common_summary = read_json(PINNED["common_summary"][0])
    matched_summary = read_json(PINNED["matched_summary"][0])
    mission_summary = read_json(PINNED["mission_summary"][0])
    day15_summary = read_json(PINNED["day15_summary"][0])
    source_contract = read_json(PINNED["source_contract"][0])

    prompt_manifest = [
        r
        for r in read_csv(PINNED["prompt_input_manifest"][0])
        if r["geometry"] == "S3d_O8"
    ]
    prompt_cutflow = [
        r
        for r in read_csv(PINNED["prompt_cutflow"][0])
        if r["geometry"] == "S3d_O8" and r["window_id"] == "w2_510p58_511p42"
    ]
    activation_cells = [
        r
        for r in read_csv(PINNED["activation_cells"][0])
        if r["geometry"] == "S3d_O8"
    ]
    day15_inventory = [
        r
        for r in read_csv(PINNED["day15_inventory"][0])
        if r["geometry"] == "S3d_O8"
    ]
    delayed_source_index = [
        r
        for r in read_csv(PINNED["delayed_source_index"][0])
        if r["geometry"] == "S3d_O8"
    ]
    delayed_manifest = [
        r
        for r in read_csv(PINNED["delayed_input_manifest"][0])
        if r["geometry"] == "S3d_O8"
    ]
    common_cutflow = [
        r
        for r in read_csv(PINNED["common_cutflow"][0])
        if r["geometry"] == "S3d_O8" and r["window_id"] == "w2_510p58_511p42"
    ]
    family_budget = [
        r
        for r in read_csv(PINNED["matched_family_budget"][0])
        if r["geometry"] == "S3d_O8"
    ]
    mission_rows = [
        r
        for r in read_csv(PINNED["mission_timeline"][0])
        if r["geometry"] == "S3d_O8"
    ]
    signal_acceptance_rows = [
        r
        for r in read_csv(PINNED["signal_acceptance"][0])
        if r["geometry"] == "S3d_O8"
    ]

    flux_by_family = {
        r["family"]: f(r["flux_sum_cm2_s"])
        for r in source_contract["geometries"]["s3d_o8"]["cards"]
    }

    prompt_input = {}
    for family in FAMILIES:
        rows = [r for r in prompt_manifest if r["family"] == family]
        prompt_input[family] = {
            "jobs": len(rows),
            "histories": sum(i(r["events"]) for r in rows),
            "TT_s": sum(f(r["TT_s"]) for r in rows),
            "event_weight_cps": 1.0 / sum(f(r["TT_s"]) for r in rows),
            "hash_recomputed_for_all_large_sims": all(
                r["sim_hash_recomputed"].lower() == "true" for r in rows
            ),
        }

    activation = {}
    for family in FAMILIES:
        row = only(activation_cells, incident_family=family)
        activation[family] = {
            "jobs": i(row["N_BUILDUP_files"]),
            "histories": i(row["generated_primaries"]),
            "TT_s": f(row["sum_TT_s"]),
            "RP": i(float(row["sum_RP"])),
            "production_rate_s_1": f(row["production_rate_s-1"]),
            "zero_RP_files": i(row["zero_RP_files"]),
            "status": row["cell_status"],
        }

    ground_unique_ZA = defaultdict(set)
    for row in day15_inventory:
        if row["source_disposition"] == "transported_ground_state":
            ground_unique_ZA[row["incident_family"]].add(i(row["source_parent_ZA"]))

    delayed_input = {}
    for family in FAMILIES:
        row = only(delayed_manifest, family=family)
        source_row = only(delayed_source_index, incident_family=family)
        delayed_input[family] = {
            "source_sampling_seed": i(source_row["sampling_seed"]),
            "transport_seed": i(row["seed"]),
            "triggers": i(row["triggers"]),
            "day15_ground_activity_Bq": f(row["included_ground_activity_Bq"]),
            "event_weight_cps": f(row["event_weight_cps"]),
            "equivalent_time_s": f(row["equivalent_time_s"]),
            "holdout_activity_Bq": f(row["known_holdout_activity_Bq"]),
            "unknown_activity_state_count": i(row["unknown_activity_state_count"]),
            "subsample_rule": row["subsample_rule"],
            "source_status": row["source_status"],
            "transported_ground_unique_ZA": len(ground_unique_ZA[family]),
        }

    # Canonical measured-response W2 cutflow plus a raw pre-veto diagnostic row.
    cutflow_rows = []
    cutflow_index = {}
    cutflow_specs = (
        ("raw_pre_veto", "raw", "pre_veto"),
        ("measured_pre_veto", "measured", "pre_veto"),
        ("measured_active_veto50", "measured", "active_veto50"),
        ("measured_step05", "measured", "side_compton_fov_pass"),
    )
    for stream in ("prompt", "delayed"):
        for family in FAMILIES:
            for display_stage, response_state, stage in cutflow_specs:
                if stream == "prompt":
                    row = only(
                        prompt_cutflow,
                        family=family,
                        response_state=response_state,
                        stage=stage,
                    )
                    out = {
                        "stream": stream,
                        "family": family,
                        "particle_label": LABELS[family],
                        "display_stage": display_stage,
                        "response_state": response_state,
                        "stage": stage,
                        "selected_events": i(row["selected_events"]),
                        "event_weight_cps": f(row["event_weight_cps"]),
                        "rate_cps": f(row["rate_cps"]),
                        "rate_stat_sigma_cps": f(row["rate_stat_sigma_cps"]),
                        "rate_lower95_cps": f(row["rate_lower95_cps"]),
                        "rate_upper95_cps": f(row["rate_upper95_cps"]),
                        "authority_status": row["authority_status"],
                    }
                else:
                    row = only(
                        common_cutflow,
                        stream="delayed",
                        family=family,
                        response_state=response_state,
                        stage=stage,
                    )
                    out = {
                        "stream": stream,
                        "family": family,
                        "particle_label": LABELS[family],
                        "display_stage": display_stage,
                        "response_state": response_state,
                        "stage": stage,
                        "selected_events": i(row["selected_events"]),
                        "event_weight_cps": f(row["event_weight"]),
                        "rate_cps": f(row["weighted_value"]),
                        "rate_stat_sigma_cps": f(row["weighted_stat_sigma"]),
                        "rate_lower95_cps": f(row["weighted_lower95"]),
                        "rate_upper95_cps": f(row["weighted_upper95"]),
                        "authority_status": row["authority_status"],
                    }
                cutflow_rows.append(out)
                cutflow_index[(stream, family, display_stage)] = out

    budget_index = {
        (r["stream"], r["family"]): r
        for r in family_budget
    }
    if len(budget_index) != 16:
        raise RuntimeError(f"Expected 16 S3d-O8 family budget rows, got {len(budget_index)}")

    mission_count_rows = []
    mission_index = {}
    for family in FAMILIES:
        prompt_counts = sum(
            f(r[f"prompt_{family}_cps"])
            * f(r["accidental_live_factor"])
            * f(r["trajectory_quadrature_weight_s"])
            for r in mission_rows
        )
        delayed_counts = sum(
            f(r[f"delayed_{family}_cps"])
            * f(r["accidental_live_factor"])
            * f(r["trajectory_quadrature_weight_s"])
            for r in mission_rows
        )
        row = {
            "family": family,
            "particle_label": LABELS[family],
            "prompt_counts_20d": prompt_counts,
            "delayed_counts_20d": delayed_counts,
            "total_background_counts_20d": prompt_counts + delayed_counts,
            "uncertainty_status": (
                "NO_RELIABLE_FAMILY_CUMULATIVE_MC_VARIANCE_PROPAGATED"
            ),
        }
        mission_count_rows.append(row)
        mission_index[family] = row

    day15_node = mission_summary["geometries"]["S3d_O8"]["trajectory_day15_node"]
    family_rows = []
    for family in FAMILIES:
        p_final = budget_index[("prompt", family)]
        d_final = budget_index[("delayed", family)]
        p_pre = cutflow_index[("prompt", family, "measured_pre_veto")]
        p_veto = cutflow_index[("prompt", family, "measured_active_veto50")]
        d_pre = cutflow_index[("delayed", family, "measured_pre_veto")]
        d_veto = cutflow_index[("delayed", family, "measured_active_veto50")]
        family_rows.append(
            {
                "family": family,
                "particle_label": LABELS[family],
                "source_flux_sum_cm_2_s_1": flux_by_family[family],
                "prompt_jobs": prompt_input[family]["jobs"],
                "prompt_histories": prompt_input[family]["histories"],
                "prompt_TT_s": prompt_input[family]["TT_s"],
                "prompt_event_weight_cps": prompt_input[family]["event_weight_cps"],
                "prompt_w2_pre_events": p_pre["selected_events"],
                "prompt_w2_pre_rate_cps": p_pre["rate_cps"],
                "prompt_w2_veto50_events": p_veto["selected_events"],
                "prompt_w2_veto50_rate_cps": p_veto["rate_cps"],
                "prompt_w2_final_events": i(p_final["selected_events"]),
                "prompt_w2_final_rate_cps": f(p_final["rate_cps"]),
                "prompt_w2_final_stat_sigma_cps": f(p_final["rate_stat_sigma_cps"]),
                "prompt_w2_final_lower95_cps": f(p_final["rate_lower95_cps"]),
                "prompt_w2_final_upper95_cps": f(p_final["rate_upper95_cps"]),
                "prompt_support_flag": p_final["support_flag"],
                "activation_jobs": activation[family]["jobs"],
                "activation_histories": activation[family]["histories"],
                "activation_TT_s": activation[family]["TT_s"],
                "activation_RP": activation[family]["RP"],
                "activation_production_rate_s_1": activation[family]["production_rate_s_1"],
                "day15_ground_activity_Bq": delayed_input[family]["day15_ground_activity_Bq"],
                "day15_holdout_activity_Bq": delayed_input[family]["holdout_activity_Bq"],
                "transported_ground_unique_ZA": delayed_input[family]["transported_ground_unique_ZA"],
                "delayed_transport_triggers": delayed_input[family]["triggers"],
                "delayed_source_sampling_seed": delayed_input[family]["source_sampling_seed"],
                "delayed_transport_seed": delayed_input[family]["transport_seed"],
                "delayed_event_weight_cps": delayed_input[family]["event_weight_cps"],
                "delayed_equivalent_time_s": delayed_input[family]["equivalent_time_s"],
                "delayed_w2_pre_events": d_pre["selected_events"],
                "delayed_w2_pre_rate_cps": d_pre["rate_cps"],
                "delayed_w2_veto50_events": d_veto["selected_events"],
                "delayed_w2_veto50_rate_cps": d_veto["rate_cps"],
                "delayed_w2_final_events": i(d_final["selected_events"]),
                "delayed_w2_final_rate_cps": f(d_final["rate_cps"]),
                "delayed_w2_final_stat_sigma_cps": f(d_final["rate_stat_sigma_cps"]),
                "delayed_w2_final_lower95_cps": f(d_final["rate_lower95_cps"]),
                "delayed_w2_final_upper95_cps": f(d_final["rate_upper95_cps"]),
                "delayed_fraction_of_stream": f(d_final["fraction_of_stream"]),
                "delayed_support_flag": d_final["support_flag"],
                "mission_day15_prompt_cps_noacc": f(day15_node[f"prompt_{family}_cps"]),
                "mission_day15_delayed_cps_noacc": f(day15_node[f"delayed_{family}_cps"]),
                "mission20_prompt_counts": mission_index[family]["prompt_counts_20d"],
                "mission20_delayed_counts": mission_index[family]["delayed_counts_20d"],
                "mission20_total_background_counts": mission_index[family]["total_background_counts_20d"],
            }
        )

    final_prompt_rate = sum(r["prompt_w2_final_rate_cps"] for r in family_rows)
    final_delayed_rate = sum(r["delayed_w2_final_rate_cps"] for r in family_rows)
    final_prompt_sigma = math.sqrt(
        sum(r["prompt_w2_final_stat_sigma_cps"] ** 2 for r in family_rows)
    )
    final_delayed_sigma = math.sqrt(
        sum(r["delayed_w2_final_stat_sigma_cps"] ** 2 for r in family_rows)
    )
    prompt_neff = (
        final_prompt_rate**2
        / sum(r["prompt_w2_final_stat_sigma_cps"] ** 2 for r in family_rows)
    )
    delayed_neff = (
        final_delayed_rate**2
        / sum(r["delayed_w2_final_stat_sigma_cps"] ** 2 for r in family_rows)
    )

    mission_geometry = mission_summary["geometries"]["S3d_O8"]
    signal_authority_row = only(
        signal_acceptance_rows,
        response_state="measured",
        stage="side_compton_fov_pass",
        window_id="w2_510p58_511p42",
    )
    signal_record = {
        "component": "focused_511_signal",
        "particle": "gamma",
        "background_family_member": False,
        "scope": "post-Be-window focused EventList acceptance; kept separate from broadband atmospheric gamma background",
        "reference_flux_surface": mission_summary["mission_contract"]["reference_flux_surface"],
        "reference_flux_ph_cm2_s": f(
            mission_summary["mission_contract"]["reference_flux_ph_cm2_s"]
        ),
        "source_elevation_deg": f(
            mission_summary["mission_contract"]["source_elevation_deg"]
        ),
        "trials": i(signal_authority_row["trials"]),
        "selected_events": i(signal_authority_row["selected_events"]),
        "acceptance": f(signal_authority_row["acceptance"]),
        "acceptance_lower95": f(signal_authority_row["acceptance_lower95"]),
        "acceptance_upper95": f(signal_authority_row["acceptance_upper95"]),
        "input_optics_aeff_cm2": f(signal_authority_row["input_optics_aeff_cm2"]),
        "selected_effective_area_cm2": f(
            signal_authority_row["selected_effective_area_cm2"]
        ),
        "selected_effective_area_lower95_cm2": f(
            signal_authority_row["selected_effective_area_lower95_cm2"]
        ),
        "selected_effective_area_upper95_cm2": f(
            signal_authority_row["selected_effective_area_upper95_cm2"]
        ),
        "mission20_signal_counts": f(mission_geometry["source_counts_20d"]),
        "mission20_signal_lower95_counts": f(
            mission_geometry["source_lower95_counts_20d"]
        ),
    }
    totals = {
        "prompt_jobs": sum(r["prompt_jobs"] for r in family_rows),
        "prompt_histories": sum(r["prompt_histories"] for r in family_rows),
        "activation_jobs": sum(r["activation_jobs"] for r in family_rows),
        "activation_histories": sum(r["activation_histories"] for r in family_rows),
        "activation_RP": sum(r["activation_RP"] for r in family_rows),
        "delayed_transport_triggers": sum(r["delayed_transport_triggers"] for r in family_rows),
        "day15_ground_activity_Bq": sum(r["day15_ground_activity_Bq"] for r in family_rows),
        "day15_holdout_activity_Bq": sum(r["day15_holdout_activity_Bq"] for r in family_rows),
        "prompt_w2_final_events": sum(r["prompt_w2_final_events"] for r in family_rows),
        "prompt_w2_final_rate_cps": final_prompt_rate,
        "prompt_w2_final_stat_sigma_cps": final_prompt_sigma,
        "prompt_w2_weighted_Neff": prompt_neff,
        "delayed_w2_final_events": sum(r["delayed_w2_final_events"] for r in family_rows),
        "delayed_w2_final_rate_cps": final_delayed_rate,
        "delayed_w2_final_stat_sigma_cps": final_delayed_sigma,
        "delayed_w2_weighted_Neff": delayed_neff,
        "day15_constant_environment_total_background_cps": final_prompt_rate + final_delayed_rate,
        "day15_constant_environment_total_background_stat_sigma_cps": math.hypot(
            final_prompt_sigma, final_delayed_sigma
        ),
        "mission20_prompt_counts": sum(r["prompt_counts_20d"] for r in mission_count_rows),
        "mission20_delayed_counts": sum(r["delayed_counts_20d"] for r in mission_count_rows),
        "mission20_total_background_counts": sum(
            r["total_background_counts_20d"] for r in mission_count_rows
        ),
        "mission20_signal_counts": signal_record["mission20_signal_counts"],
        "mission20_signal_lower95_counts": signal_record[
            "mission20_signal_lower95_counts"
        ],
    }

    family_fields = list(family_rows[0])
    cutflow_fields = list(cutflow_rows[0])
    mission_fields = list(mission_count_rows[0])
    write_csv(DATA / "s3d_o8_particle_family_statistics.csv", family_rows, family_fields)
    write_csv(DATA / "s3d_o8_w2_cutflow_by_family.csv", cutflow_rows, cutflow_fields)
    write_csv(DATA / "s3d_o8_mission20_counts_by_family.csv", mission_count_rows, mission_fields)
    write_csv(DATA / "s3d_o8_authority_sources.csv", source_records, list(source_records[0]))
    write_csv(
        DATA / "s3d_o8_focused_511_signal_statistics.csv",
        [signal_record],
        list(signal_record),
    )

    response_contract = {
        "geometry": "S3d-O8",
        "geometry_setup": str(GEOMETRY_SETUP),
        "geometry_setup_sha256": PINNED["geometry_setup"][1],
        "energy_contract": "corrected Cosima total kinetic energy in keV; alpha is MeV/nucleon x 4 x 1000, all other families are MeV x 1000",
        "source_model": "20 equal-mu full-sphere FarFieldAreaSource bins at R=60 cm",
        "gamma_contract": "single broadband_total source; no additive atmospheric mono-511 stream",
        "TES_response_FWHM_keV": 0.42,
        "measured_pixel_threshold_keV": 0.3,
        "W2_keV": [510.58, 511.42],
        "active_veto_threshold_keV": 50.0,
        "final_stage": "side_compton_fov_pass (retained Step05, reject_policy=keep)",
        "normalization": {
            "prompt": "Within each incident family: selected rate=N_selected/sum(instant TT), event weight=1/sum(instant TT). Cross-family TT is never pooled.",
            "activation": "Within each geometry x incident-family cell: production rate=sum(RP)/sum(buildup TT); zero-RP files remain in the TT denominator.",
            "delayed": "Within each incident family: event weight=included day-15 transported-ground activity/250000 triggers=1/equivalent_time; selected rate=N_selected x event weight. Each 50,000-position source uses a deterministic stride-5 set of 10,000 positions with retained flux multiplied by 5.",
        },
    }
    mission_contract = dict(mission_summary["mission_contract"])
    mission_contract.update(
        {
            "integration": mission_summary["time_integration"],
            "inventory_initial_condition": "zero inventory at mission day 0; pre-flight and ground activation excluded",
            "known_exclusions": list(mission_summary["known_exclusions"]),
            "uncertainty_contract": dict(mission_summary["uncertainty_contract"]),
        }
    )

    caveats = [
        "The prompt campaign is heterogeneous screening, not uniform precision production; the final prompt rate has only two gamma survivors.",
        "A zero selected-event count is not a physical-zero claim. Positive per-family Garwood 95% upper limits are retained for all zero-survivor prompt families and delayed muplus.",
        "Delayed family labels identify the atmospheric incident family that made the activation inventory; they are not necessarily the direct projectile that made a nuclide or the delayed particle entering TES.",
        "Delayed 95% intervals are transport-count Garwood intervals from one source-sampling seed and one transport seed per family; source-position mixture, buildup yield, cross-section/physics, and other systematics are not included.",
        "The focused 511-keV signal is a separate post-Be-window gamma EventList acceptance component and is never added to the broadband atmospheric gamma background family.",
        "The 20-day mission is an 81-bin forward-analytic family-scalar fold, not 81 independent environment-point transports. Reliable per-family cumulative MC variance was not propagated, so no invented per-family mission error bars are reported.",
        "The 81-node altitude/position profile is synthetic rather than flight telemetry, and the family-scalar fold keeps each family's spectrum, angular distribution, detector response, and activation yield fixed without corrected multipoint-transport validation.",
        "The PARMA driver uses solar modulation W=114.6 while the corrected source contract records W=118.3; only driver-internal relative family ratios are used.",
        "Non-day15 delayed occupancy uses a family-total-activity proxy. The 10,000 exact-position source mixture has parent-ZA total-variation differences up to 6.19%, which are not included in the counting intervals.",
        "Optics effective-area systematics, source visibility/duty-cycle history, and full-envelope BPE/plastic transmission outside the post-Be EventList scope are excluded.",
        "The mission assumes zero inventory at day 0 and excludes pre-flight/ground activation.",
        "The proton inventory has a 0.0998092689784 Bq excited-state holdout; alpha and proton each have one unknown activity-state row outside the transported-ground central value.",
        "The authority manifests did not re-hash every large SIM in this re-analysis; they rely on terminal-ledger/receipt declarations.",
        "Do not mix the current corrected M05 rates with the older package-43 Step05 result (5 events, 0.003393031514 cps) or the separate frozen pixel/L3 diagnostic mission counts.",
    ]

    summary = {
        "schema_version": 1,
        "model_identity": "S3d-O8",
        "record_date": "2026-08-15",
        "status": "PASS_S3D_O8_CURRENT_ALL8_PARTICLE_STATISTICS_RECORDED",
        "authority_chain": {
            "primary": "2026-08-13 M05 corrected-keV all-eight-family transport/common-response and 81-bin forward-analytic mission scenario",
            "integrated_arbitration": "/home/ubuntu/.codex/worktrees/601e/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_integrated_arbitration_20260814/REPORT.md",
            "integrated_arbitration_role": "audit/index layer; not an independent simulation reproduction",
        },
        "upstream_status": {
            "input_audit": input_audit["status"],
            "prompt": prompt_summary["status"],
            "delayed": delayed_summary["status"],
            "common_response": common_summary["status"],
            "matched_day15": matched_summary["status"],
            "mission": mission_summary["status"],
        },
        "response_contract": response_contract,
        "mission_contract": mission_contract,
        "mission_known_exclusions": list(mission_summary["known_exclusions"]),
        "mission_uncertainty_contract": dict(mission_summary["uncertainty_contract"]),
        "totals": totals,
        "families": family_rows,
        "focused_511_signal": signal_record,
        "mission20_counts_by_family": mission_count_rows,
        "source_authorities": source_records,
        "caveats": caveats,
        "explicitly_superseded_or_separate": {
            "old_package43_step05": {
                "prompt_events": 5,
                "prompt_rate_cps": 0.003393031514121508,
                "reason_not_current": "pre-source-unit-repair/old exposure set",
            },
            "frozen_pixel_L3_diagnostic_mission": {
                "signal_counts_20d": 1490.802230,
                "prompt_counts_20d": 27807.088280,
                "delayed_counts_20d": 37662.902066,
                "reason_not_current": "different frozen pixel/L3 selection diagnostic",
            },
        },
    }
    summary_path = DATA / "s3d_o8_particle_statistics_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    checks = {
        "all_authority_hashes_match": True,
        "upstream_input_audit_pass": input_audit["status"] == "PASS__M05_CORRECTED_INPUTS_READY",
        "upstream_prompt_pass": prompt_summary["status"] == "PASS__M05_CORRECTED_PROMPT_SCREENING",
        "upstream_delayed_pass": delayed_summary["status"] == "PASS__M05_CORRECTED_DELAYED_RAW_CATALOG_15_SOURCE_CELL_COMPLETE",
        "upstream_common_response_pass": common_summary["status"] == "PASS__M05_CORRECTED_COMMON_RESPONSE_PROMPT_DELAYED_SIGNAL_COMPLETE",
        "upstream_matched_pass": matched_summary["status"] == "PASS__M05_CORRECTED_MATCHED_DAY15_COMPARISON__PROMOTION_DEFERRED",
        "upstream_mission_pass": mission_summary["status"] == "PASS__M05_CORRECTED_81BIN_FORWARD_ANALYTIC_SCENARIO__PROMOTION_DEFERRED",
        "family_set_exact": set(r["family"] for r in family_rows) == set(FAMILIES) and len(family_rows) == 8,
        "prompt_input_265_jobs": totals["prompt_jobs"] == 265,
        "prompt_input_3842075_histories": totals["prompt_histories"] == 3_842_075,
        "activation_223_jobs": totals["activation_jobs"] == 223,
        "activation_3046468_histories": totals["activation_histories"] == 3_046_468,
        "activation_72054_RP": totals["activation_RP"] == 72_054,
        "delayed_250000_triggers_each": all(r["delayed_transport_triggers"] == 250_000 for r in family_rows),
        "delayed_2000000_triggers_total": totals["delayed_transport_triggers"] == 2_000_000,
        "delayed_source_sampling_seeds_exact": {
            r["family"]: r["delayed_source_sampling_seed"] for r in family_rows
        }
        == {
            "p": 1970688221,
            "n": 1970098319,
            "alpha": 1970294953,
            "gamma": 1970000002,
            "eminus": 1970393270,
            "eplus": 1970196636,
            "muminus": 1970589904,
            "muplus": 1970491587,
        },
        "delayed_transport_seeds_exact": {
            r["family"]: r["delayed_transport_seed"] for r in family_rows
        }
        == {
            "p": 2068810001,
            "n": 2068910001,
            "alpha": 2069010001,
            "gamma": 2071010001,
            "eminus": 2071110001,
            "eplus": 2071310001,
            "muminus": 2071210001,
            "muplus": 2071410001,
        },
        "delayed_event_weight_is_activity_over_triggers": all(
            close(
                r["delayed_event_weight_cps"],
                r["day15_ground_activity_Bq"] / r["delayed_transport_triggers"],
            )
            for r in family_rows
        ),
        "day15_ground_activity_closure": close(totals["day15_ground_activity_Bq"], 1404.1310687262096),
        "day15_holdout_activity_closure": close(totals["day15_holdout_activity_Bq"], 0.09980926897839938),
        "prompt_final_2_events": totals["prompt_w2_final_events"] == 2,
        "prompt_final_rate_closure": close(totals["prompt_w2_final_rate_cps"], 0.03384292813088877),
        "prompt_final_sigma_closure": close(totals["prompt_w2_final_stat_sigma_cps"], 0.023930563976560425),
        "prompt_only_gamma_positive": all((r["prompt_w2_final_events"] > 0) == (r["family"] == "gamma") for r in family_rows),
        "prompt_zero_families_keep_positive_upper95": all(r["prompt_w2_final_events"] > 0 or r["prompt_w2_final_upper95_cps"] > 0 for r in family_rows),
        "delayed_final_420_events": totals["delayed_w2_final_events"] == 420,
        "delayed_final_rate_closure": close(totals["delayed_w2_final_rate_cps"], 0.054479752227267225),
        "delayed_final_sigma_closure": close(totals["delayed_w2_final_stat_sigma_cps"], 0.010159879311642049),
        "delayed_weighted_neff_closure": close(totals["delayed_w2_weighted_Neff"], 28.7536611, rtol=1e-8),
        "budget_matches_cutflow_final": all(
            i(budget_index[(stream, family)]["selected_events"])
            == cutflow_index[(stream, family, "measured_step05")]["selected_events"]
            and close(
                f(budget_index[(stream, family)]["rate_cps"]),
                cutflow_index[(stream, family, "measured_step05")]["rate_cps"],
            )
            for stream in ("prompt", "delayed")
            for family in FAMILIES
        ),
        "mission_81_bins": len(mission_rows) == 81,
        "mission_contract_preserved": all(
            mission_contract[key] == value
            for key, value in mission_summary["mission_contract"].items()
        ),
        "mission_known_exclusions_preserved": mission_contract["known_exclusions"]
        == mission_summary["known_exclusions"],
        "mission_uncertainty_contract_preserved": mission_contract[
            "uncertainty_contract"
        ]
        == mission_summary["uncertainty_contract"],
        "mission20_prompt_counts_closure": close(totals["mission20_prompt_counts"], 55398.97943402516, atol=1e-7),
        "mission20_delayed_counts_closure": close(totals["mission20_delayed_counts"], 88804.86265187593, atol=1e-7),
        "mission20_background_counts_closure": close(totals["mission20_total_background_counts"], 144203.8420859011, atol=1e-7),
        "mission20_signal_counts_closure": close(totals["mission20_signal_counts"], 1645.3877530659986, atol=1e-9),
        "focused_signal_trials_37194": signal_record["trials"] == 37_194,
        "focused_signal_selected_27855": signal_record["selected_events"] == 27_855,
        "focused_signal_acceptance_closure": close(
            signal_record["acceptance"], 0.7489111146959186
        ),
        "focused_signal_aeff_closure": close(
            signal_record["selected_effective_area_cm2"], 15.041700000000004
        ),
        "focused_signal_kept_separate_from_background": not signal_record[
            "background_family_member"
        ],
        "geometry_setup_hash_exact": sha256(GEOMETRY_SETUP) == PINNED["geometry_setup"][1],
        "cutflow_row_count_64": len(cutflow_rows) == 64,
        "mission_family_row_count_8": len(mission_count_rows) == 8,
    }
    problems = [name for name, passed in checks.items() if not passed]
    if problems:
        raise RuntimeError("Validation failed: " + ", ".join(problems))

    generated_files = [
        DATA / "s3d_o8_particle_family_statistics.csv",
        DATA / "s3d_o8_w2_cutflow_by_family.csv",
        DATA / "s3d_o8_mission20_counts_by_family.csv",
        DATA / "s3d_o8_focused_511_signal_statistics.csv",
        DATA / "s3d_o8_authority_sources.csv",
        summary_path,
    ]
    validation = {
        "schema_version": 1,
        "model_identity": "S3d-O8",
        "record_date": "2026-08-15",
        "status": "PASS_S3D_O8_CURRENT_ALL8_PARTICLE_STATISTICS_VALIDATION",
        "checks": checks,
        "failure_count": 0,
        "problems": [],
        "generated_outputs": [
            {
                "path": str(path),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in generated_files
        ],
        "transport_started": False,
        "large_sim_hash_policy": "not recomputed in this record; inherited terminal-ledger/receipt declarations are explicitly disclosed",
    }
    (AUDIT / "s3d_o8_particle_statistics_validation.json").write_text(
        json.dumps(validation, indent=2, sort_keys=True) + "\n"
    )

    rows_text = []
    for row in family_rows:
        p_rate = row["prompt_w2_final_rate_cps"]
        p_text = (
            f'{row["prompt_w2_final_events"]} / {fmt(p_rate)} +/- '
            f'{fmt(row["prompt_w2_final_stat_sigma_cps"])}'
            if row["prompt_w2_final_events"]
            else f'0 / 0; UL95={fmt(row["prompt_w2_final_upper95_cps"])}'
        )
        d_rate = row["delayed_w2_final_rate_cps"]
        d_text = (
            f'{row["delayed_w2_final_events"]} / {fmt(d_rate)} +/- '
            f'{fmt(row["delayed_w2_final_stat_sigma_cps"])}'
            if row["delayed_w2_final_events"]
            else f'0 / 0; UL95={fmt(row["delayed_w2_final_upper95_cps"])}'
        )
        rows_text.append(
            f'| {row["particle_label"]} | {row["prompt_jobs"]} / {row["prompt_histories"]:,} '
            f'| {row["activation_jobs"]} / {row["activation_histories"]:,} '
            f'| {fmt(row["day15_ground_activity_Bq"])} | {p_text} | {d_text} |'
        )

    mission_text = []
    for row in mission_count_rows:
        mission_text.append(
            f'| {row["particle_label"]} | {fmt(row["prompt_counts_20d"])} '
            f'| {fmt(row["delayed_counts_20d"])} | {fmt(row["total_background_counts_20d"])} |'
        )
    known_exclusions_text = "\n".join(
        f"- {item}" for item in mission_summary["known_exclusions"]
    )

    readme = f"""# S3d-O8 current all-particle statistics record

Status: **PASS**. This package freezes the current 2026-08-13 corrected-keV M05 all-eight-family authority for later S3d-O8 versus SE3 comparisons. It starts no new transport.

## Headline W2 statistics

W2 is 510.58--511.42 keV with 0.42-keV FWHM measured response, 0.3-keV pixel threshold, 50-keV active veto, and retained Step05 side-Compton/FoV selection.

| particle family | instant jobs / histories | buildup files / histories | day-15 ground Bq | prompt final events / cps +/- 1 sigma | delayed final events / cps +/- 1 sigma |
|---|---:|---:|---:|---:|---:|
{chr(10).join(rows_text)}

Totals: prompt **{totals['prompt_w2_final_events']} events / {totals['prompt_w2_final_rate_cps']:.12g} +/- {totals['prompt_w2_final_stat_sigma_cps']:.12g} cps**; delayed **{totals['delayed_w2_final_events']} events / {totals['delayed_w2_final_rate_cps']:.12g} +/- {totals['delayed_w2_final_stat_sigma_cps']:.12g} cps**; constant-environment day-15 total **{totals['day15_constant_environment_total_background_cps']:.12g} cps**.

Prompt is low support: only two gamma events survive. Every zero-survivor prompt family retains a positive Garwood 95% upper limit in the CSV/JSON; zero is not interpreted as a physical zero. Delayed p, alpha, and muminus are also low support; delayed muplus is a zero-survivor upper-limit branch.

## Input and activation statistics

- Instant prompt: 265 jobs, 3,842,075 histories.
- Buildup activation: 223 files, 3,046,468 histories, 72,054 RP records.
- Delayed transport: 250,000 triggers per family, 2,000,000 total.
- Every family row records both the exact-position source-sampling seed and the delayed-transport seed.
- Transported ground-state activity: 1,404.131068726 Bq; known proton excited-state holdout: 0.099809269 Bq.
- Prompt normalization is per family: `rate=N_selected/sum(instant TT)` and `event weight=1/sum(instant TT)`; TT is never pooled across particle families.
- Activation normalization is per geometry x incident family: `production rate=sum(RP)/sum(buildup TT)`, including zero-RP files in the TT denominator.
- Delayed normalization is per family: `event weight=day-15 transported-ground Bq/250000 triggers`; the 50,000-position source is deterministically thinned to 10,000 positions with stride 5 and retained flux multiplied by 5.

## Official 20-day forward-analytic mission fold

| particle family | prompt counts | delayed counts | total background counts |
|---|---:|---:|---:|
{chr(10).join(mission_text)}

Totals: prompt **{totals['mission20_prompt_counts']:.9f}**, delayed **{totals['mission20_delayed_counts']:.9f}**, background **{totals['mission20_total_background_counts']:.9f}**, and signal **{totals['mission20_signal_counts']:.9f}** counts.

These per-family mission counts reuse the same transported samples in a 20-day, 81-node family-scalar analytic fold. The focused source is fixed at 45-degree elevation; the signal uses post-Be-window effective area times 45-degree slant transmission at a top-of-atmosphere reference flux of 1e-4 ph cm-2 s-1. Inventory is zero at mission day 0, so pre-flight and ground activation are excluded. Background gamma is the corrected `unit_only_total_gamma` component; there is no additive atmospheric mono-511 stream. No reliable family-level cumulative MC variance was propagated, so this record does not manufacture family error bars.

Exact mission-authority exclusions retained in the machine record:

{known_exclusions_text}

## Focused 511-keV signal (separate from background gamma)

The post-Be-window focused EventList has **{signal_record['trials']:,} trials -> {signal_record['selected_events']:,} selected**, acceptance **{signal_record['acceptance']:.12f}** with 95% interval **[{signal_record['acceptance_lower95']:.12f}, {signal_record['acceptance_upper95']:.12f}]**. The selected effective area is **{signal_record['selected_effective_area_cm2']:.6f} cm2** with 95% interval **[{signal_record['selected_effective_area_lower95_cm2']:.9f}, {signal_record['selected_effective_area_upper95_cm2']:.9f}] cm2**. At the top-of-atmosphere reference flux of **{signal_record['reference_flux_ph_cm2_s']:.1e} ph cm-2 s-1**, the 20-day mission signal is **{signal_record['mission20_signal_counts']:.9f}** counts (lower95 **{signal_record['mission20_signal_lower95_counts']:.9f}**).

This is a focused signal gamma component, not a ninth atmospheric background family and not an additive mono-511 background source.

## Files

- `data/s3d_o8_particle_family_statistics.csv`: one complete row per particle family.
- `data/s3d_o8_w2_cutflow_by_family.csv`: raw pre-veto and canonical measured pre-veto/veto50/Step05 cutflows.
- `data/s3d_o8_mission20_counts_by_family.csv`: integrated 20-day family counts.
- `data/s3d_o8_focused_511_signal_statistics.csv`: separate focused-signal trials, acceptance, effective area, and mission counts.
- `data/s3d_o8_particle_statistics_summary.json`: full machine-readable record, totals, contracts, sources, and caveats.
- `data/s3d_o8_authority_sources.csv`: absolute path, SHA256, and size for every pinned authority.
- `audit/s3d_o8_particle_statistics_validation.json`: deterministic self-validation gates and output hashes.
- `code/build_s3d_o8_particle_statistics.py`: deterministic rebuild/validation entry point.

## Authority and exclusions

Primary authority is `{AUTHORITY}`. The 601e integrated arbitration is an audit/index layer, not an independent simulation reproduction.

Do not mix this corrected M05 record with either (1) the older package-43 Step05 prompt result of 5 events / 0.003393031514 cps, or (2) the separate frozen pixel/L3 diagnostic mission counts. Large SIM files were not re-hashed here; the authority relies on terminal-ledger/receipt hash declarations. The mission is a forward-analytic family-scalar scenario, not 81 independent environment-point transports and not a final geometry-promotion authority.
"""
    (PACKAGE / "README.md").write_text(readme)

    print(json.dumps({"status": validation["status"], "totals": totals}, indent=2))


if __name__ == "__main__":
    main()
