#!/usr/bin/env python3
"""Run the Section-4 background scope on the P67 common-time engine.

The retained P67 catalog remains the transport/source lineage authority, but
the current Section-4 result scope is fixed before Poisson arrival generation.
Atmospheric-line templates remain present in the immutable input catalog for
lineage validation and are assigned zero arrival rate in this derived run.

This is deliberately a thin, non-overwriting adapter.  It does not change P67
or any current paper asset.  It changes the common-axis component law before
the five anchor replays, which is the earliest point at which the requested
result scope can be imposed consistently.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve()
ROOT = HERE.parents[4]
P67_TIMELINE = Path(
    "/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/67_m05_mono511_flux_closure_20260823/"
    "code/run_fluxclosed_timeline.py"
)
DISABLED_COMPONENT = "atm511"
SCENARIO_ID = "M05_SECTION4_SG3_SH3_BACKGROUND_SCOPE_20260828_V2"
LEGACY_MOUNT = Path("/mnt/data")
CURRENT_READONLY_MOUNT = Path("/media/ubuntu/903261CE3261BA3C")


def load_p67() -> Any:
    if not P67_TIMELINE.is_file():
        raise FileNotFoundError(P67_TIMELINE)
    spec = importlib.util.spec_from_file_location(
        "m05_section4_p67_common_axis", P67_TIMELINE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import P67 timeline authority: {P67_TIMELINE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P67 = load_p67()
_P67_REPLAY = P67.Replay
_P67_INPUT_CHECK = P67.input_check_report
_P67_WRITE_JSON_EXCLUSIVE = P67.write_json_exclusive
_P67_MODEL_AUTHORITY = P67.model_authority
_P67_RESOLVE_ROOT = P67.resolve_root


def remap_readonly_mount(path: Path) -> Path:
    """Map stale receipt/config mount paths without modifying their authority."""
    try:
        suffix = path.relative_to(LEGACY_MOUNT)
    except ValueError:
        return path
    mapped = CURRENT_READONLY_MOUNT / suffix
    return mapped if mapped.exists() else path


def resolve_root(path_text: str | Path) -> Path:
    path = Path(path_text)
    # P67 registries bind repository-relative authority paths to the ebb2
    # worktree that produced them.  Preserve that rule.  New derived outputs
    # are therefore supplied as explicit absolute paths by this package.
    resolved = path if path.is_absolute() else _P67_RESOLVE_ROOT(path)
    return remap_readonly_mount(resolved)


def model_authority(model: str) -> Any:
    authority = _P67_MODEL_AUTHORITY(model)
    authority.activation_path = remap_readonly_mount(authority.activation_path)
    return authority


class _NodeKeyedModelBResponse:
    """Per-call proxy that inserts the anchor node in model-B group noise.

    P67 already includes ``node`` in the model-A key.  Its retained model-B
    implementation uses ``(seed, multi_serial, pixel_code)`` and resets the
    serial at every anchor.  The proxy preserves every other P67 operation and
    changes only that key to ``(seed, node, multi_serial, pixel_code)``.
    """

    def __init__(self, authority: Any, seed: int, node: int, serial: int) -> None:
        self._authority = authority
        self._seed = int(seed)
        self._node = int(node)
        self._serial = int(serial)
        self.noise_calls = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._authority, name)

    def keyed_standard_normal(self, *keys: Any) -> float:
        expected_prefix = ("sh3_optv3", "mature_timeline")
        if (
            len(keys) != 5
            or tuple(keys[:2]) != expected_prefix
            or int(keys[2]) != self._seed
            or int(keys[3]) != self._serial
        ):
            raise RuntimeError(
                "model-B P67 group-response noise-key contract changed; "
                f"refusing an unreviewed adapter call: {keys!r}"
            )
        self.noise_calls += 1
        return float(
            self._authority.keyed_standard_normal(
                keys[0], keys[1], keys[2], self._node, keys[3], keys[4]
            )
        )


class Section4Replay(_P67_REPLAY):
    """P67 replay with the Section-4 component mask applied before Poisson."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.singleton_stored_flag_gate = self._singleton_stored_flag_parity_gate()
        self.group_response_noise_gate = self._group_response_noise_key_gate()
        disabled_code = int(P67.COMPONENT_CODES[DISABLED_COMPONENT])
        disabled_categories = np.flatnonzero(self.cat_components == disabled_code)
        if len(disabled_categories) != 1:
            raise RuntimeError(
                f"expected exactly one {DISABLED_COMPONENT} category, found "
                f"{len(disabled_categories)}"
            )

        disabled_events = self.a["event_component"] == disabled_code
        if not np.any(disabled_events):
            raise RuntimeError(f"input catalog contains no {DISABLED_COMPONENT} events")

        # Singleton groups use the precomputed event flags.  Clear only the
        # in-memory flags for disabled templates so day-15 diagnostic products
        # and direct aggregates have the same component scope as the timeline.
        for field in P67.WINDOW_FLAG_FIELDS.values():
            self.a[field][disabled_events] = 0

        for category_id in disabled_categories.tolist():
            zero = P67.Aggregate(
                count=0,
                bin_sum_q=np.zeros(80, dtype=np.float64),
                bin_sum_q2=np.zeros(80, dtype=np.float64),
            )
            for window in P67.WINDOWS:
                for stage in P67.STAGES:
                    self.selection_aggregates[(category_id, window, stage)] = zero

        # This is the decisive operation: the disabled category has no Poisson
        # arrivals and therefore cannot affect grouping, veto occupancy, the
        # signal accidental probe, or the five-anchor interpolation.
        self.category_rate_matrix[:, disabled_categories] = 0.0
        if np.any(self.category_rate_matrix[:, disabled_categories] != 0.0):
            raise RuntimeError("component mask did not zero the arrival-rate matrix")

        enabled_events = ~disabled_events
        self.fingerprint_payload = copy.deepcopy(self.fingerprint_payload)
        self.fingerprint_payload["analysis_scenario"] = {
            "scenario_id": SCENARIO_ID,
            "scope_applied_at": "category_rate_matrix_before_poisson_arrivals",
            "enabled_components": ["other", "gamma_continuum"],
            "disabled_components": [DISABLED_COMPONENT],
            "disabled_category_ids": disabled_categories.astype(int).tolist(),
            "enabled_catalog_event_templates": int(np.count_nonzero(enabled_events)),
            "disabled_catalog_event_templates": int(np.count_nonzero(disabled_events)),
            "grouping_then_response_contract": (
                "Poisson arrivals -> common sorted axis -> adjacent-gap <=1 us "
                "transitive groups -> raw TES/active sums -> response -> veto -> Compton"
            ),
            "singleton_stored_flag_gate": copy.deepcopy(
                self.singleton_stored_flag_gate
            ),
            "group_response_noise_gate": copy.deepcopy(
                self.group_response_noise_gate
            ),
        }
        self.fingerprint_payload["file_sha256"][P67.relative(HERE)] = P67.sha256_file(
            HERE
        )
        self.fingerprint_payload["parameters"]["analysis_scenario_id"] = SCENARIO_ID
        self.fingerprint_sha256 = P67.canonical_digest(self.fingerprint_payload)

    def _singleton_stored_flag_parity_gate(self) -> dict[str, Any]:
        """Check a bounded, deterministic sample of precomputed singleton flags.

        This deliberately does not search the catalog for favorable examples.
        It samples a fixed grid, every category's endpoints/midpoint, and a
        fixed grid of packed raw hits mapped back to their parent events.
        """
        required = {
            "measured_total_keV",
            "plastic_keV",
            "bgo_keV",
            "broad_flags",
            "w2_flags",
            "hit_start",
            "hit_count",
        }
        missing = sorted(required - set(self.a))
        if missing:
            raise RuntimeError(f"singleton stored-flag gate missing arrays: {missing}")

        n_events = len(self.a["event_category"])
        candidate_indices: list[int] = np.linspace(
            0, n_events - 1, min(n_events, 2048), dtype=np.int64
        ).tolist()
        for start, count in zip(self.starts.tolist(), self.counts.tolist()):
            start_i = int(start)
            count_i = int(count)
            candidate_indices.extend(
                (start_i, start_i + count_i // 2, start_i + count_i - 1)
            )
        n_hits = len(self.a["hit_code"])
        if n_hits:
            sampled_hits = np.linspace(
                0, n_hits - 1, min(n_hits, 2048), dtype=np.int64
            )
            parent_events = (
                np.searchsorted(
                    self.a["hit_start"], sampled_hits, side="right"
                )
                - 1
            )
            candidate_indices.extend(parent_events.astype(int).tolist())

        sample = np.unique(np.asarray(candidate_indices, dtype=np.int64))
        sample = sample[(sample >= 0) & (sample < n_events)]
        if len(sample) == 0:
            raise RuntimeError("singleton stored-flag gate produced an empty sample")

        measured = self.a["measured_total_keV"][sample].astype(
            np.float64, copy=False
        )
        plastic = self.a["plastic_keV"][sample].astype(np.float64, copy=False)
        bgo = self.a["bgo_keV"][sample].astype(np.float64, copy=False)
        threshold = float(self.veto_threshold_keV)
        valid_bits = int(sum(P67.STAGE_BITS.values()))
        has_compton_keep = "compton_keep" in self.a
        if self.model == "b" and not has_compton_keep:
            raise RuntimeError(
                "model-B singleton stored-flag gate requires compton_keep provenance"
            )

        window_reports: dict[str, Any] = {}
        for window, field in P67.WINDOW_FLAG_FIELDS.items():
            low, high = (float(value) for value in P67.WINDOWS[window])
            pre = (measured >= low) & (measured < high)
            plastic_pass = pre & (plastic < threshold)
            bgo_pass = pre & (bgo < threshold)
            combined_pass = plastic_pass & bgo_pass
            stored = self.a[field][sample].astype(np.uint16, copy=False)
            expected_prefix = (
                pre.astype(np.uint16) * P67.STAGE_BITS["pre_veto"]
                | plastic_pass.astype(np.uint16)
                * P67.STAGE_BITS["plastic_positron_veto"]
                | bgo_pass.astype(np.uint16)
                * P67.STAGE_BITS["bgo_active_scintillator_veto"]
                | combined_pass.astype(np.uint16)
                * P67.STAGE_BITS["combined_active_veto"]
            )
            prefix_mask = valid_bits ^ P67.STAGE_BITS["compton_trajectory_veto"]
            prefix_mismatch = int(
                np.count_nonzero((stored & prefix_mask) != expected_prefix)
            )
            unknown_mask = np.uint16((~valid_bits) & np.iinfo(np.uint16).max)
            unknown_bits = int(np.count_nonzero(stored & unknown_mask))
            final_set = (
                stored & P67.STAGE_BITS["compton_trajectory_veto"]
            ) != 0
            combined_set = (
                stored & P67.STAGE_BITS["combined_active_veto"]
            ) != 0
            final_without_combined = int(
                np.count_nonzero(final_set & ~combined_set)
            )
            final_mismatch = 0
            if has_compton_keep:
                final_pass = combined_pass & (self.a["compton_keep"][sample] != 0)
                expected_final = (
                    final_pass.astype(np.uint16)
                    * P67.STAGE_BITS["compton_trajectory_veto"]
                )
                final_mismatch = int(
                    np.count_nonzero(
                        (stored & P67.STAGE_BITS["compton_trajectory_veto"])
                        != expected_final
                    )
                )
            if prefix_mismatch or unknown_bits or final_without_combined or final_mismatch:
                raise RuntimeError(
                    f"singleton stored-flag parity failed for {window}: "
                    f"prefix={prefix_mismatch}, unknown={unknown_bits}, "
                    f"final_without_combined={final_without_combined}, "
                    f"final={final_mismatch}"
                )
            window_reports[window] = {
                "sample_pre_veto": int(np.count_nonzero(pre)),
                "sample_final": int(
                    np.count_nonzero(
                        stored & P67.STAGE_BITS["compton_trajectory_veto"]
                    )
                ),
                "response_prefix_mismatches": prefix_mismatch,
                "final_parity_mismatches": (
                    final_mismatch if has_compton_keep else None
                ),
                "unknown_flag_bits": unknown_bits,
            }

        return {
            "status": "PASS__BOUNDED_SINGLETON_STORED_FLAG_PARITY",
            "scope": (
                "deterministic bounded compact-catalog sample; no SIM scan and "
                "no search over the full NPZ event axis"
            ),
            "sample_events": int(len(sample)),
            "sample_events_with_raw_tes": int(
                np.count_nonzero(self.a["hit_count"][sample] > 0)
            ),
            "sample_index_sha256": P67.canonical_digest(sample.astype(int).tolist()),
            "stored_flag_provenance": (
                "immutable catalog measured_total/active deposits/flags, with "
                "catalog audit and response-code hashes bound by the input fingerprint"
            ),
            "compton_keep_parity_available": has_compton_keep,
            "windows": window_reports,
        }

    def _group_response_noise_key_gate(self) -> dict[str, Any]:
        if self.model == "a":
            return {
                "status": "PASS__P67_MODEL_A_NODE_KEY_RETAINED",
                "key": "(sg3b,mature_timeline,seed,node,multi_serial,pixel_uid)",
                "adapter_change": "none",
            }
        nodes = tuple(int(value) for value in P67.ANCHOR_NODES)
        def proxied_values() -> list[float]:
            output: list[float] = []
            for node in nodes:
                proxy = _NodeKeyedModelBResponse(
                    self.response_code, self.seed, node, 0
                )
                value = proxy.keyed_standard_normal(
                    "sh3_optv3", "mature_timeline", self.seed, 0, 100001
                )
                direct = self.response_code.keyed_standard_normal(
                    "sh3_optv3", "mature_timeline", self.seed, node, 0, 100001
                )
                if proxy.noise_calls != 1 or value != direct:
                    raise RuntimeError(
                        "model-B group-response proxy did not insert node exactly once"
                    )
                output.append(float(value))
            return output

        values = proxied_values()
        repeated = proxied_values()
        if values != repeated or len(set(values)) != len(nodes):
            raise RuntimeError(
                "model-B node-keyed group-response noise self-check failed"
            )
        return {
            "status": "PASS__MODEL_B_GROUP_RESPONSE_NODE_KEYED",
            "key": "(sh3_optv3,mature_timeline,seed,node,multi_serial,pixel_code)",
            "anchor_nodes_checked": list(nodes),
            "distinct_anchor_values": len(set(values)),
            "repeatability_mismatches": sum(a != b for a, b in zip(values, repeated)),
            "adapter_scope": "multi-event groups only; singleton stored flags unchanged",
        }

    def combined_flags(
        self, event_indices: np.ndarray, node: int, serial: int
    ) -> tuple[int, int]:
        if self.model != "b":
            return super().combined_flags(event_indices, node, serial)
        authority = self.response_code
        proxy = _NodeKeyedModelBResponse(authority, self.seed, node, serial)
        self.response_code = proxy
        try:
            flags = super().combined_flags(event_indices, node, serial)
        finally:
            self.response_code = authority
        if proxy.noise_calls <= 0:
            raise RuntimeError(
                "model-B multi-event group contained raw TES but made no response-noise call"
            )
        return flags


def input_check_report(replay: Section4Replay) -> dict[str, Any]:
    report = _P67_INPUT_CHECK(replay)
    report["analysis_scenario"] = copy.deepcopy(
        replay.fingerprint_payload["analysis_scenario"]
    )
    for node, row in report["anchors"].items():
        row["scope_check"] = (
            "total_detector_positive_rate_cps is computed after the component "
            "mask and before Poisson arrival generation"
        )
    report["status"] = "PASS__SECTION4_COMMON_AXIS_INPUTS_VALID"
    return report


def write_json_exclusive(path: Path, value: Any) -> None:
    """Annotate the final summary without changing receipt schemas."""
    payload = value
    if (
        path.name == "summary.json"
        and isinstance(value, dict)
        and value.get("status") == "PASS__M05_FLUXCLOSED_COMMON_TIME_TIMELINE"
    ):
        payload = copy.deepcopy(value)
        payload["schema_version"] = max(3, int(payload.get("schema_version", 0)))
        payload["status"] = "PASS__M05_SECTION4_COMMON_TIME_TIMELINE"
        payload["analysis_scenario"] = copy.deepcopy(
            payload["input_fingerprint"]["analysis_scenario"]
        )
        method = payload.setdefault("method", {})
        method["component_scope"] = (
            "fixed in the category-rate matrix before Poisson arrival generation"
        )
        method["event_mark_law"] = (
            "ordinary categories use validated constant within-category weights; "
            "the broadband gamma continuum uses exact rejection sampling from its "
            "event-level physical weights; only enabled categories enter the "
            "common Poisson axis"
        )
        method.pop("mono511_scale", None)
        boundary = payload.setdefault("authority_boundary", {})
        boundary["background"] = (
            "derived Section-4 component scope applied before common-time "
            "generation; immutable P67 source and response products are read-only"
        )
        boundary["no_transport_or_simulation_started"] = True
    _P67_WRITE_JSON_EXCLUSIVE(path, payload)


def main() -> int:
    # P67's CLI/output implementation remains authoritative.  Only the Replay
    # constructor, input report, and final summary annotation are replaced.
    P67.Replay = Section4Replay
    P67.input_check_report = input_check_report
    P67.write_json_exclusive = write_json_exclusive
    P67.resolve_root = resolve_root
    P67.model_authority = model_authority
    return int(P67.main())


if __name__ == "__main__":
    raise SystemExit(main())
