#!/usr/bin/env python3
"""Replay SG3B background on the retained M05/Step05 common Poisson axis."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]
CONFIG = PACKAGE / "analysis_inputs.json"
CATALOG_DIR = PACKAGE / "outputs/01_event_catalog"
OUT = PACKAGE / "outputs/02_mature_timeline"
SECONDS_PER_DAY = 86_400.0


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve(text: str) -> Path:
    path = Path(text)
    return path if path.is_absolute() else ROOT / path


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing empty CSV: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class Replay:
    def __init__(self) -> None:
        self.config = load_json(CONFIG)
        self.p58 = load_module("sg3b_mature_p58", resolve(self.config["package58_code"]))
        self.catalog_code = load_module("sg3b_mature_catalog", PACKAGE / "code/build_event_catalog.py")
        self.p58_config = load_json(resolve(self.config["package58_config"]))
        self.parser, self.core, self.step05, self.disk = self.p58.runtime()
        with np.load(CATALOG_DIR / "combined_event_catalog.npz", allow_pickle=False) as data:
            self.a = {key: data[key] for key in data.files}
        self.categories = load_json(CATALOG_DIR / "category_registry.json")["categories"]
        self.n_categories = len(self.categories)
        self.starts = np.asarray([int(row["event_start"]) for row in self.categories], dtype=np.int64)
        self.counts = np.asarray([int(row["event_count"]) for row in self.categories], dtype=np.int64)
        self.base_weights = np.asarray(
            [float(row["base_event_weight_cps"]) for row in self.categories], dtype=np.float64
        )
        self.streams = np.asarray([row["stream"] for row in self.categories])
        self.families = np.asarray([row["family"] for row in self.categories])
        self.zas = np.asarray([int(row["source_parent_ZA"]) for row in self.categories], dtype=np.int32)
        self.scales = sorted(
            read_csv(resolve(self.p58_config["mission"]["family_scales"])),
            key=lambda row: int(row["time_bin_id"]),
        )
        self.atmosphere = sorted(
            read_csv(resolve(self.p58_config["mission"]["atmospheric_transmission"])),
            key=lambda row: int(row["time_bin_id"]),
        )
        if len(self.scales) != 81 or len(self.atmosphere) != 81:
            raise RuntimeError("mission axis is not the retained 81-node axis")
        activation = load_json(Path(self.p58_config["activation_manifest"]))
        self.inventory = self.p58.inventory_authority(activation)
        self.curves = self.p58.activity_curves(self.inventory, self.scales)
        self.signal_aeff = self.p58.signal_proxy_by_stage(self.p58_config)
        self.stages = tuple(self.catalog_code.STAGE_BITS)
        self.windows = dict(self.catalog_code.WINDOWS)
        self.flag_counts: dict[tuple[int, str, str], int] = {}
        for cat_id, row in enumerate(self.categories):
            start = int(row["event_start"])
            stop = start + int(row["event_count"])
            for window, field in (("broad_480_550", "broad_flags"), ("w2_510p58_511p42", "w2_flags")):
                flags = self.a[field][start:stop]
                for stage, bit in self.catalog_code.STAGE_BITS.items():
                    self.flag_counts[(cat_id, window, stage)] = int(np.count_nonzero(flags & bit))

    def category_rates(self, node: int) -> np.ndarray:
        row = self.scales[node]
        rates = np.empty(self.n_categories, dtype=np.float64)
        for cat_id in range(self.n_categories):
            family = str(self.families[cat_id])
            factor: float
            if self.streams[cat_id] == "prompt":
                factor = float(row[f"scale_{family}_to_parma_reference"])
            else:
                key = (family, int(self.zas[cat_id]))
                if key not in self.inventory:
                    raise RuntimeError(f"delayed category absent from inventory: {key}")
                factor = self.curves[key][node] / self.inventory[key]["day15_activity_Bq"]
            rates[cat_id] = self.counts[cat_id] * self.base_weights[cat_id] * factor
        return rates

    def direct_rates(self, node: int, category_rates: np.ndarray) -> dict[tuple[str, str], float]:
        out: dict[tuple[str, str], float] = {}
        per_event_rate = np.divide(
            category_rates,
            self.counts,
            out=np.zeros_like(category_rates),
            where=self.counts > 0,
        )
        for window in self.windows:
            for stage in self.stages:
                out[(window, stage)] = math.fsum(
                    self.flag_counts[(cat_id, window, stage)] * per_event_rate[cat_id]
                    for cat_id in range(self.n_categories)
                )
        return out

    def sample_marks(self, rng: np.random.Generator, n: int, category_rates: np.ndarray) -> np.ndarray:
        if n <= 0:
            return np.empty(0, dtype=np.int64)
        total = float(np.sum(category_rates))
        if total <= 0.0:
            raise RuntimeError("cannot sample zero-rate catalog")
        cumulative = np.cumsum(category_rates / total)
        cumulative[-1] = 1.0
        cat = np.searchsorted(cumulative, rng.random(n), side="right")
        # Every retained template in one category has the same physical
        # event weight, so uniform integer offsets are the exact mark law.
        offsets = np.floor(rng.random(n) * self.counts[cat]).astype(np.int64)
        return self.starts[cat] + offsets

    def combined_flags(self, event_indices: np.ndarray, node: int, serial: int) -> tuple[int, int]:
        plastic = float(np.sum(self.a["plastic_keV"][event_indices], dtype=np.float64))
        bgo = float(np.sum(self.a["bgo_keV"][event_indices], dtype=np.float64))
        pixels: dict[int, dict[str, float | int]] = {}
        for event_index in event_indices:
            start = int(self.a["hit_start"][event_index])
            stop = start + int(self.a["hit_count"][event_index])
            for hit_index in range(start, stop):
                code = int(self.a["hit_code"][hit_index])
                energy = float(self.a["hit_energy_keV"][hit_index])
                target = pixels.setdefault(
                    code,
                    {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(self.a["hit_layer"][hit_index])},
                )
                target["e"] = float(target["e"]) + energy
                target["wx"] = float(target["wx"]) + energy * float(self.a["hit_x_cm"][hit_index])
                target["wy"] = float(target["wy"]) + energy * float(self.a["hit_y_cm"][hit_index])
                target["wz"] = float(target["wz"]) + energy * float(self.a["hit_z_cm"][hit_index])
        measured_hits: list[Any] = []
        seed = int(self.config["timeline"]["seed"])
        for code, record in sorted(pixels.items()):
            energy = float(record["e"])
            layer = int(record["layer"])
            pixel = code - layer * 100_000
            uid = f"TP_L{layer}_{pixel}"
            measured = energy + self.core.SIGMA_KEV * self.core.keyed_standard_normal(
                "sg3b", "mature_timeline", seed, node, serial, uid
            )
            if measured < self.core.PIXEL_THRESHOLD_KEV:
                continue
            measured_hits.append(
                SimpleNamespace(
                    e=measured,
                    x=float(record["wx"]) / energy,
                    y=float(record["wy"]) / energy,
                    z=float(record["wz"]) / energy,
                    pixel_uid=uid,
                    layer=layer,
                )
            )
        measured_total = math.fsum(hit.e for hit in measured_hits)
        return self.catalog_code.flags_for_event(
            measured_hits,
            measured_total,
            plastic,
            bgo,
            float(self.config["timeline"]["plastic_threshold_keV"]),
            self.p58,
            self.step05,
            self.disk,
        )

    def process_groups(
        self,
        event_indices: np.ndarray,
        starts: np.ndarray,
        ends: np.ndarray,
        node: int,
        state: dict[str, Any],
    ) -> None:
        if len(starts) == 0:
            return
        sizes = ends - starts
        state["groups"] += int(len(starts))
        singles = event_indices[starts[sizes == 1]]
        for window, field in (("broad_480_550", "broad_flags"), ("w2_510p58_511p42", "w2_flags")):
            flags = self.a[field][singles]
            for stage, bit in self.catalog_code.STAGE_BITS.items():
                state["counts"][(window, stage)] += int(np.count_nonzero(flags & bit))
        multi_mask = sizes > 1
        if not np.any(multi_mask):
            return
        multi_starts = starts[multi_mask]
        multi_ends = ends[multi_mask]
        tes_indicator = (self.a["hit_count"][event_indices] > 0).astype(np.int16)
        cumulative_tes = np.empty(len(tes_indicator) + 1, dtype=np.int64)
        cumulative_tes[0] = 0
        np.cumsum(tes_indicator, dtype=np.int64, out=cumulative_tes[1:])
        tes_by_group = cumulative_tes[multi_ends] - cumulative_tes[multi_starts]
        state["multi_groups"] += int(len(multi_starts))
        for start, end, n_tes in zip(multi_starts, multi_ends, tes_by_group):
            if n_tes <= 0:
                continue
            state["multi_groups_with_raw_tes"] += 1
            ev = event_indices[start:end]
            broad, w2 = self.combined_flags(ev, node, state["multi_serial"])
            state["multi_serial"] += 1
            for window, flags in (("broad_480_550", broad), ("w2_510p58_511p42", w2)):
                for stage, bit in self.catalog_code.STAGE_BITS.items():
                    if flags & bit:
                        state["counts"][(window, stage)] += 1
            stream_set = set(self.streams[self.a["event_category"][ev]])
            if len(stream_set) > 1:
                state["mixed_stream_groups_with_tes"] += 1

    def timeline(self, node: int, category_rates: np.ndarray, exposure_s: float, rng: np.random.Generator) -> dict[str, Any]:
        total_rate = float(np.sum(category_rates))
        tau = float(self.config["timeline"]["coincidence_window_s"])
        chunk = int(self.config["timeline"]["chunk_events"])
        state: dict[str, Any] = {
            "groups": 0,
            "multi_groups": 0,
            "multi_groups_with_raw_tes": 0,
            "mixed_stream_groups_with_tes": 0,
            "multi_serial": 0,
            "counts": defaultdict(int),
        }
        pending = np.empty(0, dtype=np.int64)
        current_time = 0.0
        generated = 0
        finished = False
        while not finished:
            gaps = rng.exponential(1.0 / total_rate, size=chunk)
            times = current_time + np.cumsum(gaps)
            accepted = int(np.searchsorted(times, exposure_s, side="right"))
            if accepted < chunk:
                gaps = gaps[:accepted]
                finished = True
            marks = self.sample_marks(rng, len(gaps), category_rates)
            generated += len(marks)
            if len(marks):
                current_time = float(times[len(marks) - 1])
            if len(pending):
                combined = np.concatenate((pending, marks))
                flags = np.zeros(len(combined), dtype=bool)
                flags[0] = True
                if len(marks):
                    offset = len(pending)
                    flags[offset] = gaps[0] > tau
                    if len(marks) > 1:
                        flags[offset + 1 :] = gaps[1:] > tau
            else:
                combined = marks
                flags = np.zeros(len(combined), dtype=bool)
                if len(combined):
                    flags[0] = True
                    if len(combined) > 1:
                        flags[1:] = gaps[1:] > tau
            starts = np.flatnonzero(flags)
            if finished:
                ends = np.r_[starts[1:], len(combined)].astype(np.int64)
                self.process_groups(combined, starts, ends, node, state)
                pending = np.empty(0, dtype=np.int64)
            elif len(starts):
                process_starts = starts[:-1]
                process_ends = starts[1:]
                self.process_groups(combined, process_starts, process_ends, node, state)
                pending = combined[starts[-1] :].copy()
            if finished:
                break
        return {
            "node": node,
            "day_mid": float(self.scales[node]["day_mid"]),
            "exposure_s": exposure_s,
            "total_detector_positive_rate_cps": total_rate,
            "event_instances": generated,
            "expected_event_instances": total_rate * exposure_s,
            "groups": state["groups"],
            "multi_groups": state["multi_groups"],
            "multi_groups_with_raw_tes": state["multi_groups_with_raw_tes"],
            "mixed_stream_groups_with_tes": state["mixed_stream_groups_with_tes"],
            "counts": {f"{window}__{stage}": int(state["counts"][(window, stage)]) for window in self.windows for stage in self.stages},
        }

    def signal_probe(
        self, node: int, category_rates: np.ndarray, trials: int, rng: np.random.Generator
    ) -> dict[str, Any]:
        total_rate = float(np.sum(category_rates))
        tau = float(self.config["timeline"]["coincidence_window_s"])
        stop_probability = math.exp(-total_rate * tau)
        plastic = np.zeros(trials, dtype=np.float32)
        bgo = np.zeros(trials, dtype=np.float32)
        tes_contaminated = np.zeros(trials, dtype=bool)
        neighbors_total = 0
        for _side in ("left", "right"):
            counts = rng.geometric(stop_probability, size=trials) - 1
            trial_index = np.repeat(np.arange(trials, dtype=np.int64), counts)
            marks = self.sample_marks(rng, len(trial_index), category_rates)
            neighbors_total += len(marks)
            if len(marks):
                plastic += np.bincount(
                    trial_index, weights=self.a["plastic_keV"][marks], minlength=trials
                ).astype(np.float32)
                bgo += np.bincount(
                    trial_index, weights=self.a["bgo_keV"][marks], minlength=trials
                ).astype(np.float32)
                contaminated_counts = np.bincount(
                    trial_index,
                    weights=(self.a["hit_count"][marks] > 0).astype(np.uint8),
                    minlength=trials,
                )
                tes_contaminated |= contaminated_counts > 0
        keep = (
            (~tes_contaminated)
            & (plastic < float(self.config["timeline"]["plastic_threshold_keV"]))
            & (bgo < float(self.config["timeline"]["bgo_threshold_keV"]))
        )
        passed = int(np.count_nonzero(keep))
        survival = passed / trials
        return {
            "node": node,
            "day_mid": float(self.scales[node]["day_mid"]),
            "trials": trials,
            "passed": passed,
            "conditional_signal_accidental_survival": survival,
            "binomial_standard_error": math.sqrt(survival * (1.0 - survival) / trials),
            "total_background_rate_cps": total_rate,
            "one_sided_exp_minus_Rtau": stop_probability,
            "two_sided_isolation_exp_minus_2Rtau": stop_probability * stop_probability,
            "sampled_neighbor_event_instances": neighbors_total,
            "proxy_boundary": "W2-selected signal treated as lost by any coincident raw-TES background deposit; active-only deposits are summed per side-chain",
        }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    replay = Replay()
    tcfg = replay.config["timeline"]
    exposure = float(tcfg["exposure_s_per_anchor"])
    trials = int(tcfg["signal_probe_trials_per_anchor"])
    seed = int(tcfg["seed"])
    anchors: list[dict[str, Any]] = []
    rate_rows: list[dict[str, Any]] = []
    started = time.time()
    for ordinal, node in enumerate(tcfg["anchor_time_bin_ids"]):
        node = int(node)
        category_rates = replay.category_rates(node)
        direct = replay.direct_rates(node, category_rates)
        timeline = replay.timeline(
            node, category_rates, exposure, np.random.default_rng(np.random.SeedSequence([seed, ordinal, 1]))
        )
        signal = replay.signal_probe(
            node, category_rates, trials, np.random.default_rng(np.random.SeedSequence([seed, ordinal, 2]))
        )
        anchors.append({"timeline": timeline, "signal_probe": signal})
        for window in replay.windows:
            for stage in replay.stages:
                key = f"{window}__{stage}"
                count = int(timeline["counts"][key])
                observed = count / exposure
                direct_rate = direct[(window, stage)]
                per_event_rate = np.divide(
                    category_rates,
                    replay.counts,
                    out=np.zeros_like(category_rates),
                    where=replay.counts > 0,
                )
                selected_by_category = np.asarray(
                    [replay.flag_counts[(cat_id, window, stage)] for cat_id in range(replay.n_categories)],
                    dtype=np.int64,
                )
                transport_variance = float(np.sum(selected_by_category * per_event_rate**2))
                transport_sigma = math.sqrt(transport_variance)
                ratio = observed / direct_rate if direct_rate > 0.0 else float("nan")
                rate_rows.append({
                    "time_bin_id": node,
                    "day_mid": timeline["day_mid"],
                    "window_id": window,
                    "stage": stage,
                    "direct_no_coincidence_rate_cps": direct_rate,
                    "timeline_counts": count,
                    "timeline_rate_cps": observed,
                    "timeline_rate_standard_error_cps": math.sqrt(count) / exposure,
                    "timeline_to_direct_ratio": ratio,
                    "direct_selected_transport_templates": int(np.sum(selected_by_category)),
                    "direct_transport_MC_sigma_cps": transport_sigma,
                    "direct_transport_MC_relative_sigma": transport_sigma / direct_rate if direct_rate > 0 else "",
                    "direct_transport_MC_effective_survivors": direct_rate**2 / transport_variance if transport_variance > 0 else "",
                    "signal_accidental_survival": signal["conditional_signal_accidental_survival"],
                    "signal_survival_standard_error": signal["binomial_standard_error"],
                })
        print(json.dumps({
            "node": node,
            "day": timeline["day_mid"],
            "events": timeline["event_instances"],
            "groups": timeline["groups"],
            "w2_final_counts": timeline["counts"]["w2_510p58_511p42__compton_trajectory_veto"],
            "signal_survival": signal["conditional_signal_accidental_survival"],
        }), flush=True)

    anchor_nodes = np.asarray([int(node) for node in tcfg["anchor_time_bin_ids"]], dtype=float)
    final_anchor_rows = [
        row for row in rate_rows
        if row["window_id"] == "w2_510p58_511p42" and row["stage"] == "compton_trajectory_veto"
    ]
    final_ratios = np.asarray([float(row["timeline_to_direct_ratio"]) for row in final_anchor_rows])
    signal_survivals = np.asarray([float(row["signal_accidental_survival"]) for row in final_anchor_rows])
    mission_rows: list[dict[str, Any]] = []
    cumulative_b = 0.0
    cumulative_k = 0.0
    previous: tuple[float, float, float] | None = None
    final_selected_by_category = np.asarray(
        [
            replay.flag_counts[(cat_id, "w2_510p58_511p42", "compton_trajectory_veto")]
            for cat_id in range(replay.n_categories)
        ],
        dtype=np.int64,
    )
    integrated_weight_by_category = np.zeros(replay.n_categories, dtype=np.float64)
    previous_weight_by_category: np.ndarray | None = None
    slant = 1.0 / math.sin(math.radians(float(replay.p58_config["mission"]["source_elevation_deg"])))
    for node in range(81):
        category_rates = replay.category_rates(node)
        direct = replay.direct_rates(node, category_rates)[("w2_510p58_511p42", "compton_trajectory_veto")]
        ratio = float(np.interp(node, anchor_nodes, final_ratios))
        survival = float(np.interp(node, anchor_nodes, signal_survivals))
        background = direct * ratio
        per_event_rate = np.divide(
            category_rates,
            replay.counts,
            out=np.zeros_like(category_rates),
            where=replay.counts > 0,
        )
        corrected_weight_by_category = per_event_rate * ratio
        transmission = float(replay.atmosphere[node]["T_atm_511"]) ** slant
        kernel = replay.signal_aeff["compton_trajectory_veto"] * transmission * survival
        day = float(replay.scales[node]["day_mid"])
        if previous is not None:
            dt = (day - previous[0]) * SECONDS_PER_DAY
            cumulative_b += 0.5 * (previous[1] + background) * dt
            cumulative_k += 0.5 * (previous[2] + kernel) * dt
            if previous_weight_by_category is None:
                raise RuntimeError("missing previous category weight")
            integrated_weight_by_category += 0.5 * (
                previous_weight_by_category + corrected_weight_by_category
            ) * dt
        mission_rows.append({
            "time_bin_id": node,
            "day_mid": day,
            "direct_W2_final_no_coincidence_cps": direct,
            "interpolated_background_timeline_ratio": ratio,
            "mature_background_W2_final_cps": background,
            "conditional_signal_accidental_survival": survival,
            "T_atm_511_slant45": transmission,
            "conditional_signal_proxy_Aeff_cm2": replay.signal_aeff["compton_trajectory_veto"],
            "conditional_signal_kernel_cm2": kernel,
            "cumulative_background_counts": cumulative_b,
            "cumulative_signal_counts_per_unit_flux": cumulative_k,
            "Fmin_3sigma_gaussian_ph_cm2_s": 3.0 * math.sqrt(cumulative_b) / cumulative_k if cumulative_k > 0 else "",
            "Fmin_5sigma_gaussian_ph_cm2_s": 5.0 * math.sqrt(cumulative_b) / cumulative_k if cumulative_k > 0 else "",
            "Fmin_3sigma_poisson_asimov_ph_cm2_s": replay.p58.asimov_required_signal(cumulative_b, 3.0) / cumulative_k if cumulative_k > 0 else "",
            "Fmin_5sigma_poisson_asimov_ph_cm2_s": replay.p58.asimov_required_signal(cumulative_b, 5.0) / cumulative_k if cumulative_k > 0 else "",
        })
        previous = (day, background, kernel)
        previous_weight_by_category = corrected_weight_by_category

    transport_mc_background = float(np.sum(final_selected_by_category * integrated_weight_by_category))
    transport_mc_variance = float(np.sum(final_selected_by_category * integrated_weight_by_category**2))
    transport_mc_sigma = math.sqrt(transport_mc_variance)
    if not math.isclose(transport_mc_background, cumulative_b, rel_tol=2e-12, abs_tol=1e-6):
        raise RuntimeError(
            f"mission category-weight closure differs: {transport_mc_background} vs {cumulative_b}"
        )

    package58_summary = load_json(resolve(replay.config["package58"]) / "outputs/01_common_time_response/summary.json")
    final = mission_rows[-1]
    summary = {
        "schema_version": 1,
        "status": "PASS__SG3B_MATURE_COMMON_POISSON_TIMELINE__CONDITIONAL_SIGNAL_PROXY",
        "method": {
            "arrival_process": "chronological Exp(total detector-positive rate) inter-arrivals with iid rate-weighted event marks",
            "equivalence": "conditioned on event count, exponential-arrival construction equals per-stream Poisson counts plus uniform times and merge/sort",
            "grouping": "adjacent gaps <= 1 microsecond form one event; TES/plastic/BGO deposits are combined before veto and Compton/FoV",
            "normalization_prompt": "selected event / sum(TT_family) across all accepted instant batches",
            "normalization_delayed": "selected event * isotope activity(t) / 1,000,000 triggers within family",
        },
        "anchors": anchors,
        "mission_final_20day": final,
        "transport_MC_uncertainty_final_20day": {
            "selected_transport_templates": int(np.sum(final_selected_by_category)),
            "weighted_background_counts": transport_mc_background,
            "background_counts_sigma": transport_mc_sigma,
            "background_counts_relative_sigma": transport_mc_sigma / transport_mc_background,
            "weighted_effective_survivors": transport_mc_background**2 / transport_mc_variance,
            "approximate_relative_sigma_on_Fmin_from_background_only": 0.5 * transport_mc_sigma / transport_mc_background,
            "model": "Poisson uncertainty of the finite weighted transport survivors; each survivor's mission weight is treated as fully correlated across time nodes",
        },
        "comparison_package58": {
            "package58_status": package58_summary["status"],
            "package58_final_20day": package58_summary["mission"]["mission_endpoint_by_stage"]["compton_trajectory_veto"],
            "package58_analytic_model": package58_summary["common_time_axis"],
        },
        "authority_boundary": {
            "background_transport": "SG3B accepted prompt instant plus canonical exact-position delayed-v2",
            "signal": "SE3 full-envelope W2 conditional proxy; fresh SG3B 37,194-ray signal transport is absent",
            "signal_accidental_probe": "strict raw-TES contamination proxy because no SG3B event-level signal catalog exists",
            "underlying_transport_MC_uncertainty": "not reduced by timeline resampling; sparse accepted prompt W2 events remain sparse",
            "parma_mono511_included": False,
            "superseded_delayed_v1_included": False,
            "Cosima_transport_started": False,
        },
        "elapsed_s": time.time() - started,
    }
    write_csv(OUT / "anchor_timeline_rates.csv", rate_rows)
    write_csv(OUT / "mission_mature_flux_threshold.csv", mission_rows)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "mission_final_20day": final}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
