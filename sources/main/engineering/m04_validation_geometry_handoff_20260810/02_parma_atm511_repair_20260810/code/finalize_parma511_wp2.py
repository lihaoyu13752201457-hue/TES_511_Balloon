#!/usr/bin/env python3
"""Offline-only finalizer for the corrected PARMA atmospheric-511 module.

The program has no simulation or transport execution surface.  It accepts an
already-complete *single-campaign* aggregate receipt, an already-produced
offline modular-recomposition directory, and one or more external raw-cleanup
receipts.  It validates their dynamic evidence and writes a new, isolated WP2
conclusion package.

Top-level strings such as ``DIAGNOSTIC_ONLY`` or campaign-level
``PREPARED_NOT_RUN`` counters are deliberately informational: some producers
hard-code those labels.  The authoritative rate decision is reconstructed from
``response.primary_gate`` and the response summary's
``primary_detector_rate_gate`` and the two dictionaries must be identical.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]

EXPECTED_BATCHES = list(range(60))
EXPECTED_EVENTS_PER_BATCH = 3_000_000
EXPECTED_TOTAL_TS = 180_000_000
CAMPAIGN_ID = "o8_parma511_line_nominal_180m_20260810"
CAMPAIGN_BASE_SEED = 260_811_000
CAMPAIGN_SEED_STRIDE = 104_729
PRIMARY_RESPONSE_SEED = 1_026_071_308
RESPONSE_SEED_STRIDE = 7_919
RESPONSE_REPLICAS = 64
MAX_ENUM_HITS = 6
LINE_ENERGY_KEV = 510.99895
LINE_FLUX = 0.16651547160226118
O8_SETUP_REL = (
    "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/"
    "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
HARNESS_REL = (
    "engineering/m04_validation_geometry_handoff_20260810/"
    "02_parma_atm511_repair_20260810/code/o8_parma511_line_transport_harness.py"
)
HARNESS_SHA256 = "6c7c921769f99141325cd856b6c476d94ecbbec3a3c8806409ef3caa5faacc37"
RECOMPOSITION_BUILDER_SHA256 = "c944f2382b3e3f57830e69cccabd78cf76dc7397672bc334dba7429f4531a581"
RECOMPOSITION_CONFIG_SHA256 = "6d80b8bbcb1429c3313b2ab52228a1ac4684017b0f31b72416f64157660bd7f3"
SOURCE_BUILDER_REL = (
    "engineering/m04_validation_geometry_handoff_20260810/"
    "02_parma_atm511_repair_20260810/code/build_parma511_source_package.py"
)
SOURCE_BUILDER_SHA256 = "b2e3ca2d87fa86356cc2b5be10976ec9673b45faa45d1f53ba02cd03e266d15f"
COSIMA_SHA256 = "3fb7613de58ebb365f2a55c3336e54d2aabea2a4ddb282003a5d25eac6f1c74a"
PACKAGE44_RUNNER_SHA256 = "942bbcc3b466bd11ec38d8bd9b868762b70a7d895caadf610a85cdbbacc23a9c"
LAUNCH_ENVIRONMENT_SHA256 = "685ffa106aad847bdedfd1d0c4126f8c9e3fa6708fe44adf981375c29a90afe0"
INTENT_FINGERPRINT_SHA256 = "dd4c510ee856330fef3ddc54fc733d7853d6187e518c598bee859e616b6230cf"

LINE_GRID_HEADER = [
    "source_id",
    "theta_bin_id",
    "direction_label",
    "parma_mu_low",
    "parma_mu_high",
    "cosima_theta_low_deg",
    "cosima_theta_high_deg",
    "line_fraction",
    "line_flux_ph_cm-2_s-1",
]
PRIMARY_RESPONSE_HEADER = [
    "event_id",
    "dir_z",
    "measured_total_keV",
    "measured_multiplicity",
    "active_total_keV",
    "raw_w2",
    "active_w2",
    "final_w2",
    "topology_class",
]
REPLICA_HEADER = [
    "replica_index",
    "response_seed",
    "w2_raw_events",
    "w2_active_veto_pass_events",
    "w2_frozen_step05_pass_events",
    "rate_20bin_cps",
    "mc_sigma_20bin_cps",
    "ess_20bin",
    "rate_40bin_cps",
    "mc_sigma_40bin_cps",
    "ess_40bin",
    "rate_80bin_cps",
    "mc_sigma_80bin_cps",
    "ess_80bin",
    "relative_20_minus_80",
    "relative_40_minus_80",
]
RESPONSE_ARTIFACT_NAMES = {
    "angular_response_coefficients_20bins.csv",
    "angular_response_coefficients_40bins.csv",
    "angular_response_coefficients_80bins.csv",
    "primary_event_response.csv",
    "response_seed_replicas.csv",
}
RECOMPOSITION_FLUX_HEADER = [
    "time_bin_id", "day_mid", "depth_g_cm2", "solar_modulation_MV_fixed",
    "cutoff_rigidity_GV_fixed", "trajectory_Rc_GV_not_used_for_line",
    "parma511_flux_ph_cm2_s", "scale_to_day15",
]
RECOMPOSITION_TIMELINE_HEADER = [
    "time_bin_id", "day_mid", "elapsed_stop_day", "dt_s", "altitude_km",
    "latitude_deg", "longitude_deg", "trajectory_Rc_GV_retained_prompt_delayed_only",
    "depth_g_cm2", "corrected_line_Rc_GV_fixed", "corrected_line_flux_ph_cm2_s",
    "corrected_line_flux_scale_to_day15", "prompt_scale_gamma",
    "prompt_event_rate_hz_retained_before_line_occupancy_dedup",
    "prompt_gamma_misplaced_line_event_rate_hz_removed",
    "prompt_event_rate_hz_after_line_occupancy_dedup", "delayed_event_rate_hz_retained",
    "legacy_sidecar_event_rate_hz_removed", "corrected_parma511_event_rate_hz",
    "coincidence_occupancy_rate_hz_recomposed",
    "coincidence_occupancy_rate_hz_pre_fix_no_prompt_gamma_occupancy_dedup",
    "accidental_live_factor_recomposed",
    "accidental_live_factor_pre_fix_no_prompt_gamma_occupancy_dedup",
    "prompt_final_cps_noacc_retained", "delayed_final_cps_noacc_retained",
    "legacy_sidecar_final_cps_noacc_removed", "prompt_gamma_line_dedup_delta_cps",
    "corrected_parma511_final_cps_noacc", "background_final_cps_noacc_recomposed",
    "signal_final_cps_noacc_retained", "prompt_final_upper95_cps_noacc_retained",
    "delayed_final_upper95_cps_noacc_retained", "legacy_sidecar_final_upper95_cps_noacc_removed",
    "corrected_parma511_final_upper95_cps_noacc",
    "background_componentwise_endpoint_cps_noacc_recomposed",
    "signal_final_lower95_cps_noacc_retained", "cumulative_source_counts",
    "cumulative_background_counts", "cumulative_source_transport_counting_lower_endpoint_counts",
    "cumulative_background_componentwise_endpoint_counts", "counting_Z",
    "counting_Z_componentwise_endpoint_conditional",
]

SOURCE_AUTHORITY_HASHES = {
    "config/day15_environment_authority.json": "b4e5e4bb165735c3cf4add6af62090382aa88b839a0bea71e0da800eaafff6d2",
    "data/build_manifest.json": "976d8c8d7cf636c6c5576bed8ea8a6dc2f1c186532fe9dadf627d5ec94b5cb24",
    "data/parma_line_closure.json": "dee071a7ec7f7714f8515c7df7de687a0de2c9c9648ecbb67eeb20e89cfc041b",
    "transport/line_only_transport_contract.json": "87e034405d46c0a928f4e4c2aa2c36030f110f7dc8ab4c843436bf195bf9357f",
}

PROTECTED_LIST_REL = "engineering/m04_validation_geometry_handoff_20260810/00_review/protected_file_hashes.sha256"
PROTECTED_LIST_SHA256 = "81af1b574f0e70154c9ecaa0065ad3a8fea3ada522675a7adb6087c40d7ce0d6"
PROTECTED_HASHES = {
    "core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_en_m04_atm511_revision_20260804.tex": "3eb0c1edccd7af7b198ab397371d633392c6a316a4ee3fbdf258057f54c7c53e",
    "core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_zh_m04_atm511_revision_20260804.tex": "66df5babd3ecf5107c6f15e0eab525b25aaaea4fe5a641879962cd753524ba19",
    "core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_en_m04_atm511_revision_20260804.pdf": "9217af3b62fe0bd4a48c0db81d5a7770d2df20a78989a57fca972a5a41879694",
    "core_md/balloon511_ea_latex_drafts/balloon511_ea_draft_zh_m04_atm511_revision_20260804.pdf": "5acce4670bed2d6366242276b878891fe48c7f51039991b6fe840a35f54ff56f",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_en_20260810.pdf": "f739b3af1a6f3eb194f26596e1cc2b1bbfcebd14a68ab2c2b9a86a8f323ff2b2",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_zh_20260810.pdf": "41a3b31f4ea79c0aab3d9e0616bec5fbd76a9377e3a2f061db739db17558edea",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_en_20260810.png": "e96eaebe3457b97670c554a216441a8649cceaf6352b0c9d37ffbf98c9fafa37",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_zh_20260810.png": "7dab74ce43c5824a16b0aaa756f00b30ebe07cda8f6fa7f725799393acd41d94",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_en_20260810.tex": "4406b062ac676c60a878eecd85bc60bbc424ccaed442720180af0bde8976dbc1",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_simulation_workflow_m04_zh_20260810.tex": "1d04e0e9e21c4d26d9ec053f05154de2f2da6d1459a775b81bd7c73821d7f39d",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_reference_detector_cryostat_geometry.png": "f019c227cb283e9259ef1751804e15d536363302d78ff8251f079b0de7801b83",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_expacs_fullsphere_flux.png": "be9467ec956498a281d7d530a1ae0f6ddc48e2949b74c4f179622d479b1fa704",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_s33_poisson_normalization.png": "d9b71f7daa63f8e1de1f55d99031313a1ceda80630107a28b932ab4aa20ccb7e",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_s33_spectrum_normalized.png": "fad0233857e407248cd6a3ac30ee28f0d0d72109fa8c47e4f58bdd9647a604fa",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_s33_spectrum_anticoincidence.png": "f9229f77ace674a7eec7e0e24fd0e0248814c42118b260e5d7e11867f8ca0558",
    "core_md/balloon511_ea_latex_drafts/paper_source_figure_table/fig_s33_compton_multiplicity.png": "3130fe8a7a43b5341c9e1528f2e0a133dcc87116e83e12cb4fe83598de401dfc",
    O8_SETUP_REL: "86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec",
    "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo": "ff4e8402df702501e0112fe377d837a74c39100317146b09e9569b7bd615c37c",
    "engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det": "dd2c1d68cd474f8b0c7489f2cbbfc924eb69beb14d3ce360d9437c319a33d6cb",
}

REQUIRED_DYNAMIC_GATE_KEYS = {
    "combined_relative_40_vs_80_error",
    "importance_effective_sample_size_80bin",
    "passes_angular_paired_error",
    "passes_count_or_rse",
    "passes_detector_rate_gate",
    "relative_standard_error_80bin",
    "selected_events_80bin",
    "status",
    "required_final_events_or_rse",
    "required_combined_relative_40_vs_80_error",
}

REQUIRED_BLOCKERS = {
    "LEGACY_PROMPT_GAMMA_AXIS_FACTOR_1000",
    "FROZEN_ACTIVE_SHIELD_NAME_MATCH_INCLUDES_PASSIVE_KAPTON",
    "DAY15_ANGULAR_RESPONSE_HELD_FIXED_ACROSS_MISSION",
}


class ValidationError(RuntimeError):
    """A required evidence, schema, hash, or arithmetic gate failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def close(a: float, b: float, *, atol: float = 1.0e-12, rtol: float = 2.0e-10) -> bool:
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= atol + rtol * max(abs(a), abs(b))


def require_close(a: float, b: float, message: str, *, atol: float = 1.0e-12, rtol: float = 2.0e-10) -> None:
    if not close(float(a), float(b), atol=atol, rtol=rtol):
        raise ValidationError(f"{message}: {a!r} != {b!r}")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def require_under(path: Path, parent: Path, label: str) -> None:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise ValidationError(f"{label} escapes {parent}: {path}") from exc


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path}: {exc}") from exc
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def read_csv(path: Path, *, expected_header: list[str] | None = None) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if expected_header is not None:
                require(reader.fieldnames == expected_header, f"CSV header changed: {path}: {reader.fieldnames!r}")
            rows = list(reader)
            require(all(None not in row for row in rows), f"CSV has excess unnamed fields: {path}")
            return rows
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ValidationError(f"cannot read CSV {path}: {exc}") from exc


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def strict_int(value: Any, label: str) -> int:
    text = str(value)
    require(re.fullmatch(r"0|[1-9][0-9]*", text) is not None, f"{label} is not a canonical non-negative integer: {value!r}")
    return int(text)


def finite_float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{label} is not numeric: {value!r}") from exc
    require(math.isfinite(result), f"{label} is non-finite: {value!r}")
    return result


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def bool_text(value: Any) -> bool:
    require(value in {"True", "False"}, f"invalid canonical Boolean text: {value!r}")
    return value == "True"


def crossing(days: list[float], values: list[float], threshold: float) -> float | None:
    for index, value in enumerate(values):
        if value < threshold:
            continue
        if index == 0:
            return days[0]
        x0, x1 = days[index - 1], days[index]
        y0, y1 = values[index - 1], values[index]
        require(y1 > y0, "significance crossing is not increasing")
        return x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def time_or_extrapolate(days: list[float], values: list[float], threshold: float) -> float:
    value = crossing(days, values, threshold)
    require(values[-1] > 0.0 and days[-1] > 0.0, "cannot extrapolate a non-positive significance curve")
    return value if value is not None else days[-1] * (threshold / values[-1]) ** 2


class EvidenceRegistry:
    """Hash every file actually trusted by the final decision."""

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def verify(
        self,
        value: str | Path,
        *,
        expected_sha256: str | None = None,
        expected_bytes: int | None = None,
        label: str,
        require_repo: bool = True,
    ) -> Path:
        path = resolve_path(value)
        if require_repo:
            require_under(path, ROOT, label)
        require(path.is_file(), f"missing {label}: {path}")
        actual_bytes = path.stat().st_size
        actual_sha = sha256(path)
        if expected_sha256 is not None:
            require(actual_sha == str(expected_sha256), f"{label} SHA-256 mismatch: {path}: {actual_sha} != {expected_sha256}")
        if expected_bytes is not None:
            require(actual_bytes == int(expected_bytes), f"{label} byte-size mismatch: {path}: {actual_bytes} != {expected_bytes}")
        key = path.as_posix()
        if key in self._records:
            record = self._records[key]
            require(record["sha256"] == actual_sha and record["bytes"] == actual_bytes, f"file changed during validation: {path}")
            if label not in record["roles"]:
                record["roles"].append(label)
        else:
            self._records[key] = {
                "path": key,
                "bytes": actual_bytes,
                "sha256": actual_sha,
                "roles": [label],
            }
        return path

    def records(self) -> list[dict[str, Any]]:
        return [self._records[key] for key in sorted(self._records)]


def verify_file_record(
    registry: EvidenceRegistry,
    item: dict[str, Any],
    expected_path: Path,
    label: str,
    *,
    require_repo: bool = True,
) -> Path:
    require(isinstance(item, dict), f"malformed {label} file record")
    require("path" in item and "sha256" in item, f"{label} lacks path/SHA-256")
    supplied_path = resolve_path(item["path"])
    expected_path = expected_path.resolve()
    require(supplied_path == expected_path, f"{label} points to the wrong file: {supplied_path} != {expected_path}")
    return registry.verify(
        expected_path,
        expected_sha256=str(item["sha256"]),
        expected_bytes=int(item["bytes"]) if "bytes" in item else None,
        label=label,
        require_repo=require_repo,
    )


def verify_artifact_map(
    registry: EvidenceRegistry,
    mapping: dict[str, Any],
    label: str,
    *,
    expected_paths: dict[str, Path],
    required_parent: Path,
) -> dict[str, Path]:
    """Verify an exact artifact set and return the exact Paths actually hashed.

    Producers use two key styles: a logical basename or the artifact path.  A
    key is accepted only when it identifies the one expected path; any nested
    ``path`` field must identify that same path.  Downstream readers consume
    only the returned Paths, so a receipt cannot hash artifact A and make the
    validator subsequently read artifact B with the same basename.
    """

    require(isinstance(mapping, dict) and mapping, f"empty {label} artifact map")
    require(len(mapping) == len(expected_paths), f"{label} artifact count changed")
    remaining = dict(mapping)
    verified: dict[str, Path] = {}
    for logical_name, expected_value in expected_paths.items():
        expected = expected_value.resolve()
        require_under(expected, required_parent, f"{label}:{logical_name}")
        matches: list[tuple[str, dict[str, Any]]] = []
        for key, item in remaining.items():
            if key == logical_name:
                matches.append((key, item))
                continue
            try:
                if resolve_path(key) == expected:
                    matches.append((key, item))
            except (OSError, RuntimeError):
                pass
        require(len(matches) == 1, f"{label} does not uniquely identify exact artifact {logical_name}")
        key, item = matches[0]
        require(isinstance(item, dict), f"malformed {label} artifact entry: {key}")
        if "path" in item:
            require(resolve_path(item["path"]) == expected, f"{label}:{logical_name} key/path disagreement")
        require("sha256" in item, f"{label}:{logical_name} lacks SHA-256")
        verified[logical_name] = registry.verify(
            expected,
            expected_sha256=str(item["sha256"]),
            expected_bytes=int(item["bytes"]) if "bytes" in item else None,
            label=f"{label}:{logical_name}",
        )
        del remaining[key]
    require(not remaining, f"{label} contains unexpected artifacts: {sorted(remaining)}")
    return verified


def validate_protected_files(registry: EvidenceRegistry) -> dict[str, Any]:
    list_path = registry.verify(
        PROTECTED_LIST_REL,
        expected_sha256=PROTECTED_LIST_SHA256,
        label="protected hash authority",
    )
    parsed: dict[str, str] = {}
    for number, line in enumerate(list_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split(maxsplit=1)
        require(len(parts) == 2 and re.fullmatch(r"[0-9a-f]{64}", parts[0]), f"malformed protected hash line {number}")
        parsed[parts[1].strip()] = parts[0]
    require(parsed == PROTECTED_HASHES, "protected hash authority contents differ from the frozen 19-file set")
    for rel_path, expected in PROTECTED_HASHES.items():
        registry.verify(rel_path, expected_sha256=expected, label=f"protected:{Path(rel_path).name}")
    return {
        "status": "PASS_19_OF_19_PROTECTED_M04_AND_O8_HASHES",
        "files_checked": len(PROTECTED_HASHES),
        "authority_path": list_path.as_posix(),
        "authority_sha256": PROTECTED_LIST_SHA256,
    }


def parse_physical_line_grid(path: Path, bins: int) -> list[dict[str, Any]]:
    rows = read_csv(path, expected_header=LINE_GRID_HEADER)
    require(len(rows) == bins, f"PARMA {bins}-bin grid row count changed")
    parsed: list[dict[str, Any]] = []
    width = 2.0 / bins
    for index, row in enumerate(rows):
        bin_id = strict_int(row["theta_bin_id"], f"PARMA {bins}-bin theta_bin_id row {index}")
        require(bin_id == index, f"PARMA {bins}-bin IDs are not exactly 0..{bins - 1}")
        direction = "down" if index < bins // 2 else "up"
        require(row["direction_label"] == direction, f"PARMA {bins}-bin direction label changed at row {index}")
        require(row["source_id"] == f"PARMA511_bin{index:02d}_{direction}", f"PARMA {bins}-bin source name changed at row {index}")
        mu_low = finite_float(row["parma_mu_low"], f"PARMA {bins}-bin mu_low row {index}")
        mu_high = finite_float(row["parma_mu_high"], f"PARMA {bins}-bin mu_high row {index}")
        expected_high = 1.0 - index * width
        expected_low = expected_high - width
        require_close(mu_low, expected_low, f"PARMA {bins}-bin mu_low row {index}", atol=2.0e-15)
        require_close(mu_high, expected_high, f"PARMA {bins}-bin mu_high row {index}", atol=2.0e-15)
        theta_low = finite_float(row["cosima_theta_low_deg"], f"PARMA {bins}-bin theta_low row {index}")
        theta_high = finite_float(row["cosima_theta_high_deg"], f"PARMA {bins}-bin theta_high row {index}")
        require_close(theta_low, math.degrees(math.acos(max(-1.0, min(1.0, mu_high)))), f"PARMA {bins}-bin theta_low row {index}", atol=2.0e-11)
        require_close(theta_high, math.degrees(math.acos(max(-1.0, min(1.0, mu_low)))), f"PARMA {bins}-bin theta_high row {index}", atol=2.0e-11)
        fraction = finite_float(row["line_fraction"], f"PARMA {bins}-bin fraction row {index}")
        flux = finite_float(row["line_flux_ph_cm-2_s-1"], f"PARMA {bins}-bin flux row {index}")
        require(fraction > 0.0 and flux > 0.0, f"PARMA {bins}-bin row {index} has a non-positive weight")
        require_close(flux, fraction * LINE_FLUX, f"PARMA {bins}-bin flux/fraction row {index}", atol=2.0e-18, rtol=2.0e-13)
        parsed.append({
            "source_id": row["source_id"],
            "theta_bin_id": bin_id,
            "direction_label": direction,
            "parma_mu_low": mu_low,
            "parma_mu_high": mu_high,
            "cosima_theta_low_deg": theta_low,
            "cosima_theta_high_deg": theta_high,
            "line_fraction": fraction,
            "flux_ph_cm2_s": flux,
            "raw": row,
        })
    require_close(sum(row["line_fraction"] for row in parsed), 1.0, f"PARMA {bins}-bin fraction sum", atol=1.0e-12)
    require_close(sum(row["flux_ph_cm2_s"] for row in parsed), LINE_FLUX, f"PARMA {bins}-bin flux sum", atol=2.0e-13)
    return parsed


def validate_vendor_runtime_tree(
    registry: EvidenceRegistry,
    archive_path: Path,
) -> dict[str, Any]:
    vendor_root = PACKAGE / "vendor/parma_cpp_official_20260810"
    input_root = vendor_root / "input"
    require(input_root.is_dir() and not input_root.is_symlink(), "official PARMA extracted input tree is missing or symlinked")
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            entries = [item for item in archive.infolist() if not item.is_dir() and item.filename.startswith("input/")]
            archive_names = [item.filename for item in entries]
            require(len(archive_names) == len(set(archive_names)) and archive_names, "official PARMA archive has duplicate/empty input entries")
            for name in archive_names:
                pure = Path(name)
                require(not pure.is_absolute() and ".." not in pure.parts and "\\" not in name, f"unsafe PARMA archive member: {name}")
            extracted_names = sorted(
                path.relative_to(vendor_root).as_posix()
                for path in input_root.rglob("*")
                if path.is_file()
            )
            require(sorted(archive_names) == extracted_names, "extracted PARMA runtime input tree differs from the official archive")
            records: list[dict[str, Any]] = []
            for item in sorted(entries, key=lambda value: value.filename):
                extracted = vendor_root / item.filename
                require(not extracted.is_symlink(), f"PARMA runtime dependency is symlinked: {extracted}")
                with archive.open(item, "r") as handle:
                    digest = hashlib.sha256()
                    total = 0
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(block)
                        total += len(block)
                require(total == item.file_size, f"PARMA archive member size mismatch: {item.filename}")
                expected_sha = digest.hexdigest()
                path = registry.verify(
                    extracted,
                    expected_sha256=expected_sha,
                    expected_bytes=item.file_size,
                    label=f"official PARMA runtime dependency:{item.filename}",
                )
                records.append({"path": path.as_posix(), "bytes": item.file_size, "sha256": expected_sha})
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError(f"cannot validate official PARMA archive/runtime tree: {exc}") from exc
    return {
        "archive": {"path": archive_path.as_posix(), "bytes": archive_path.stat().st_size, "sha256": sha256(archive_path)},
        "dependency_count": len(records),
        "dependencies": records,
        "manifest_sha256": canonical_sha256(records),
    }


def validate_source_authority(registry: EvidenceRegistry) -> dict[str, Any]:
    paths: dict[str, Path] = {}
    for rel_path, expected in SOURCE_AUTHORITY_HASHES.items():
        paths[rel_path] = registry.verify(PACKAGE / rel_path, expected_sha256=expected, label=f"PARMA authority:{rel_path}")

    environment = read_json(paths["config/day15_environment_authority.json"])
    env = environment["authority"]
    require(environment.get("authority_status") == "FROZEN_EXPLICIT_DAY15_TUPLE_FOR_MODULAR_511_REPAIR", "day-15 authority status changed")
    expected_env = {
        "altitude_km": 38.75,
        "atmospheric_depth_g_cm2": 3.4614689720143224,
        "cutoff_rigidity_GV": 11.6,
        "date": "2025-08-31",
        "latitude_deg": 34.0,
        "line_energy_MeV": 0.51099895,
        "line_energy_keV": LINE_ENERGY_KEV,
        "local_geometry_g": 0.15,
        "longitude_deg": 100.0,
        "solar_modulation_MV": 114.6,
    }
    require(env == expected_env, "day-15 environment tuple changed")
    scope = environment["scope"]
    require(scope.get("only_physical_component_changed") == "atmospheric annihilation 511-keV line", "day-15 scope changed")
    require(scope.get("continuum_changed") is False and scope.get("other_particles_changed") is False, "day-15 scope expanded")

    closure = read_json(paths["data/parma_line_closure.json"])
    require(closure.get("status") == "PASS_PARMA_511_SOURCE_LEVEL_ONLY", "PARMA source-level closure is not PASS")
    require_close(float(closure["line_energy_keV_cosima"]), LINE_ENERGY_KEV, "PARMA line energy")
    require_close(float(closure["line_flux_ph_cm2_s"]), LINE_FLUX, "PARMA line flux", atol=2.0e-13)
    accounting = closure["component_accounting"]
    require(accounting.get("continuum_line_terms_modified") == 0, "continuum terms were modified")
    require(accounting.get("discrete_line_families_generated") == 1, "line is not single-counted")
    require(accounting.get("continuum_transport_rerun") is False, "continuum rerun flag is true")
    require(accounting.get("other_particle_transport_rerun") is False, "other-particle rerun flag is true")
    angular = closure["angular_checksum"]
    require_close(float(angular["fraction_sum"]), 1.0, "angular fraction sum", atol=1.0e-12)
    require_close(float(angular["mu_negative_fraction"]) + float(angular["mu_positive_fraction"]), 1.0, "hemisphere sum")
    require(angular.get("mu_definition") == "PARMA cx: -1 upward, +1 downward; Cosima polar theta=acos(mu)", "angular convention changed")
    bins = closure["source_bin_closure"]
    require([int(item["equal_mu_bins"]) for item in bins] == [20, 40, 80], "source closure does not contain exactly 20/40/80 bins")
    for item in bins:
        n_bins = int(item["equal_mu_bins"])
        require(abs(float(item["fraction_closure_abs"])) < 1.0e-8, f"{n_bins}-bin fraction closure failed")
        require(abs(float(item["flux_closure_abs_ph_cm-2_s-1"])) < 1.0e-12, f"{n_bins}-bin flux closure failed")
        require(abs(float(item["full_sphere_angular_integral"]) - 1.0) < (1.0e-6 if n_bins == 20 else 1.0e-8), f"{n_bins}-bin angular integral failed")

    build = read_json(paths["data/build_manifest.json"])
    require(build.get("status") == "PASS_REPRODUCIBLE_SOURCE_ONLY_BUILD_NO_SIMULATION", "PARMA build manifest is not source-only PASS")
    require(build.get("cosima_invoked") is False and build.get("sim_created") is False, "source build reports simulation activity")
    require(build.get("forbidden_calls_observed") == [], "source build recorded forbidden calls")
    expected_vendor_working_directory = (PACKAGE / "vendor/parma_cpp_official_20260810").resolve()
    require(resolve_path(build["working_directory_for_driver"]) == expected_vendor_working_directory, "PARMA source-build working directory changed")
    require(build["compiler"] == "g++ (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0", "PARMA source-build compiler identity changed")
    expected_compile_command = [
        "g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic",
        (PACKAGE / "code/parma511_driver.cpp").as_posix(),
        (PACKAGE / "vendor/parma_cpp_official_20260810/subroutines.cpp").as_posix(),
        "-o", (PACKAGE / "code/parma511_driver").as_posix(),
    ]
    require(build["compile_command"] == expected_compile_command, "PARMA source-build compile command changed")
    driver_binary = registry.verify(
        PACKAGE / "code/parma511_driver",
        expected_sha256=build["driver_binary_sha256"],
        label="frozen local PARMA driver binary",
    )
    verified_build_files: dict[str, dict[str, Path]] = {}
    for group_name in ("source_hashes", "output_hashes"):
        group = build[group_name]
        require(isinstance(group, dict) and group, f"empty build {group_name}")
        verified_build_files[group_name] = {}
        for rel_path, expected in group.items():
            verified_build_files[group_name][rel_path] = registry.verify(
                PACKAGE / rel_path,
                expected_sha256=str(expected),
                label=f"PARMA build {group_name}:{rel_path}",
            )
    require(build["output_hashes"]["data/parma_line_closure.json"] == SOURCE_AUTHORITY_HASHES["data/parma_line_closure.json"], "build/closure hash link failed")
    require(build["output_hashes"]["config/day15_environment_authority.json"] == SOURCE_AUTHORITY_HASHES["config/day15_environment_authority.json"], "build/environment hash link failed")
    require(closure["vendor_hashes"] == build["source_hashes"], "closure vendor hashes and build source hashes differ")

    source_builder_path = registry.verify(
        SOURCE_BUILDER_REL,
        expected_sha256=SOURCE_BUILDER_SHA256,
        label="frozen PARMA source-package builder",
    )
    grid_paths = {
        bins: verified_build_files["output_hashes"][f"line/parma511_day15_{bins}bins.csv"]
        for bins in (20, 40, 80)
    }
    grids = {bins: parse_physical_line_grid(path, bins) for bins, path in grid_paths.items()}
    for bins, path in grid_paths.items():
        registry.verify(path, label=f"PARMA {bins}-bin grid post-read stability")
    archive_path = verified_build_files["source_hashes"]["vendor/parma_cpp_official_20260810.zip"]
    vendor_runtime = validate_vendor_runtime_tree(registry, archive_path)

    contract = read_json(paths["transport/line_only_transport_contract.json"])
    require(contract.get("schema") == "o8-parma511-line-transport-contract-v1", "line-only contract schema changed")
    require(contract.get("included") == "atmospheric annihilation mono gamma line only", "line-only contract scope changed")
    require_close(float(contract["line_energy_keV"]), LINE_ENERGY_KEV, "contract line energy")
    require_close(float(contract["physical_4pi_flux_ph_cm2_s"]), LINE_FLUX, "contract line flux", atol=2.0e-13)
    require(int(contract["physical_angular_grid_equal_mu_bins"]) == 80, "contract angular grid is not 80")
    require(contract["cleanup"]["raw_automatically_deleted"] is False and contract["cleanup"]["delete_command_implemented"] is False, "contract unexpectedly implements deletion")
    require(set(contract["excluded"]) >= {"broadband photon continuum", "prompt", "delayed or activation", "focused signal", "all other particles", "full-chain recomposition"}, "line-only exclusions changed")
    require(contract["response"] == {
        "active_veto_threshold_keV": 50.0,
        "default_seed_replicas": RESPONSE_REPLICAS,
        "fwhm_keV": 0.42,
        "primary_atmospheric_seed": PRIMARY_RESPONSE_SEED,
        "seed_stride": RESPONSE_SEED_STRIDE,
        "tes_threshold_keV": 0.3,
    }, "line-only response contract changed")
    require(contract["runtime"]["cosima_binary_sha256"] == COSIMA_SHA256, "line-only contract Cosima hash changed")
    require(contract["runtime"]["package44_runner_sha256"] == PACKAGE44_RUNNER_SHA256, "line-only contract package-44 runner hash changed")
    require(contract["runtime"]["preflight_probe"] == "cosima -h only; no source argument", "line-only runtime preflight contract changed")
    require(contract["source_card_required"] == {"particle_type": 1, "spectrum": "Mono 510.99895", "store_simulation_info": "all"}, "line-only source-card contract changed")
    require(contract["execution_gate"] == {"confirmation": "RUN_O8_PARMA511_LINE_ONLY_510.99895", "flag": "--authorize-line-only-cosima", "preparation_is_authorization": False}, "line-only execution gate changed")
    require(contract["authority"]["o8_setup_sha256"] == PROTECTED_HASHES[O8_SETUP_REL], "contract O8 setup hash changed")
    require(contract["authority"]["o8_geo_sha256"] == PROTECTED_HASHES[next(key for key in PROTECTED_HASHES if key.endswith(".geo"))], "contract O8 geo hash changed")
    require(contract["authority"]["o8_det_sha256"] == PROTECTED_HASHES[next(key for key in PROTECTED_HASHES if key.endswith(".det"))], "contract O8 det hash changed")

    return {
        "status": "PASS_FROZEN_PARMA_SOURCE_AND_SINGLE_COUNT_CLOSURE",
        "line_energy_keV": LINE_ENERGY_KEV,
        "line_flux_ph_cm2_s": LINE_FLUX,
        "angular_bins": [20, 40, 80],
        "component_accounting": accounting,
        "source_builder": {
            "path": source_builder_path.as_posix(),
            "bytes": source_builder_path.stat().st_size,
            "sha256": SOURCE_BUILDER_SHA256,
        },
        "local_parma_driver": {
            "path": driver_binary.as_posix(),
            "bytes": driver_binary.stat().st_size,
            "sha256": sha256(driver_binary),
        },
        "grid_paths": grid_paths,
        "grids": grids,
        "vendor_runtime_dependency_manifest": vendor_runtime,
    }


def validate_source_card(
    path: Path,
    batch_index: int,
    transport_seed: int,
    authority_rows: list[dict[str, str]],
    expected_run_name: str,
    expected_raw_path: Path,
) -> None:
    text = path.read_text(encoding="utf-8")
    noncomment = [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    geometry_lines = [line for line in noncomment if line.startswith("Geometry ")]
    require(geometry_lines == [f"Geometry {O8_SETUP_REL}"], f"batch {batch_index}: source geometry is not the exact O8 setup")
    require([line for line in noncomment if line.startswith("PhysicsListHD ")] == ["PhysicsListHD qgsp-bic-hp"], f"batch {batch_index}: hadronic physics list changed")
    require([line for line in noncomment if line.startswith("PhysicsListEM ")] == ["PhysicsListEM LivermorePol"], f"batch {batch_index}: EM physics list changed")
    require([line for line in noncomment if line.startswith("StoreSimulationInfo ")] == ["StoreSimulationInfo all"], f"batch {batch_index}: StoreSimulationInfo contract changed")
    require([line for line in noncomment if line.startswith("StoreIsotopes ")] == ["StoreIsotopes false"], f"batch {batch_index}: StoreIsotopes contract changed")
    require([line for line in noncomment if line.startswith("DetectorTimeConstant ")] == ["DetectorTimeConstant 1e-9"], f"batch {batch_index}: detector time constant changed")
    seed_lines = [line for line in noncomment if line.startswith("Seed ")]
    require(seed_lines == [f"Seed {transport_seed}"], f"batch {batch_index}: source seed is missing, duplicated, or mismatched")
    run_lines = [line for line in noncomment if line.startswith("Run ")]
    require(run_lines == [f"Run {expected_run_name}"], f"batch {batch_index}: source does not declare the expected unique run")
    event_lines = [line for line in noncomment if ".Events " in line]
    require(event_lines == [f"{expected_run_name}.Events {EXPECTED_EVENTS_PER_BATCH}"], f"batch {batch_index}: source event count/run binding is not exactly 3M")
    file_lines = [line for line in noncomment if ".FileName " in line]
    raw_suffix = ".inc1.id1.sim.gz"
    require(expected_raw_path.as_posix().endswith(raw_suffix), f"batch {batch_index}: unexpected raw filename convention")
    expected_prefix = expected_raw_path.as_posix()[: -len(raw_suffix)]
    try:
        expected_prefix = Path(expected_prefix).relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise ValidationError(f"batch {batch_index}: raw path escapes repository") from exc
    require(file_lines == [f"{expected_run_name}.FileName {expected_prefix}"], f"batch {batch_index}: source output prefix is not bound to the recorded raw path")
    source_refs = [line for line in noncomment if ".Source " in line]
    particle = [line for line in noncomment if ".ParticleType " in line]
    spectra = [line for line in noncomment if ".Spectrum " in line]
    fluxes = [line for line in noncomment if ".Flux " in line]
    require(len(source_refs) == len(particle) == len(spectra) == len(fluxes) == 80, f"batch {batch_index}: source does not contain exactly 80 line bins")
    beam_lines = [line for line in noncomment if ".Beam " in line]
    require(len(beam_lines) == 80, f"batch {batch_index}: source does not contain exactly 80 beams")
    flux_sum = 0.0
    for bin_index, authority in enumerate(authority_rows):
        source_id = authority["source_id"]
        require(source_refs[bin_index] == f"{expected_run_name}.Source {source_id}", f"batch {batch_index}: source run/name/order mismatch at bin {bin_index}")
        require(particle[bin_index] == f"{source_id}.ParticleType 1", f"batch {batch_index}: non-gamma or wrong source name at bin {bin_index}")
        spectrum_match = re.fullmatch(rf"{re.escape(source_id)}\.Spectrum\s+Mono\s+([0-9.eE+-]+)", spectra[bin_index])
        require(spectrum_match is not None and close(float(spectrum_match.group(1)), LINE_ENERGY_KEV, atol=1.0e-10), f"batch {batch_index}: non-mono or wrong line energy at bin {bin_index}")
        beam_match = re.fullmatch(
            rf"{re.escape(source_id)}\.Beam\s+FarFieldAreaSource\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)",
            beam_lines[bin_index],
        )
        require(beam_match is not None, f"batch {batch_index}: malformed beam at bin {bin_index}")
        observed_beam = [float(value) for value in beam_match.groups()]
        expected_beam = [
            float(authority["cosima_theta_low_deg"]),
            float(authority["cosima_theta_high_deg"]),
            0.0,
            360.0,
        ]
        for observed, expected in zip(observed_beam, expected_beam):
            require_close(observed, expected, f"batch {batch_index}: beam boundary at bin {bin_index}", atol=1.0e-11)
        flux_match = re.fullmatch(rf"{re.escape(source_id)}\.Flux\s+([0-9.eE+-]+)", fluxes[bin_index])
        require(flux_match is not None, f"batch {batch_index}: malformed flux at bin {bin_index}")
        observed_flux = float(flux_match.group(1))
        require_close(observed_flux, float(authority["flux_ph_cm2_s"]), f"batch {batch_index}: per-bin flux at bin {bin_index}", atol=2.0e-18, rtol=2.0e-13)
        flux_sum += observed_flux
    require_close(flux_sum, LINE_FLUX, f"batch {batch_index}: source-card flux closure", atol=2.0e-13)
    forbidden = [line for line in noncomment if line.startswith("Include ") or "Spectrum File" in line]
    require(not forbidden, f"batch {batch_index}: composite/include source content is present: {forbidden[:2]}")


def validate_receipt_coverage(receipt: dict[str, Any], *, require_complete: bool) -> list[int]:
    require(receipt.get("schema") == "o8-parma511-line-campaign-aggregate-v1", "aggregate receipt schema changed")
    included = receipt.get("included_batch_indices")
    incomplete = receipt.get("incomplete_batch_indices")
    require(isinstance(included, list) and all(isinstance(value, int) for value in included), "aggregate included_batch_indices is malformed")
    require(isinstance(incomplete, list) and all(isinstance(value, int) for value in incomplete), "aggregate incomplete_batch_indices is malformed")
    require(included and included == list(range(len(included))), "aggregate included batches must be a contiguous prefix beginning at zero")
    require(incomplete == list(range(len(included), 60)), "aggregate incomplete batches are not the exact complementary suffix")
    require(len(receipt.get("batch_receipts", [])) == len(included), "aggregate batch receipt count differs from coverage")
    if require_complete:
        require(receipt.get("allow_partial") is False, "aggregate is partial: allow_partial must be false")
        require(included == EXPECTED_BATCHES, "aggregate is not exactly batches 0..59")
        require(incomplete == [], "aggregate still lists incomplete batches")
    else:
        require(receipt.get("allow_partial") is True, "partial-regression receipt must explicitly set allow_partial=true")
        require(len(included) < 60 and incomplete, "partial-regression receipt is unexpectedly complete")
    return included


def validate_completion_header(receipt: dict[str, Any]) -> None:
    validate_receipt_coverage(receipt, require_complete=True)


def validate_batch_provenance(
    registry: EvidenceRegistry,
    provenance_path: Path,
    batch: dict[str, Any],
) -> None:
    value = read_json(provenance_path)
    index = int(batch["batch_index"])
    require(value.get("schema") == "o8-parma511-line-stream-catalog-v1", f"batch {index}: compact provenance schema changed")
    require(value.get("status") == "PASS_STREAM_PARSE_COMPLETE", f"batch {index}: compact parse is not PASS")
    require(value.get("scope") == "atmospheric annihilation mono line only", f"batch {index}: compact scope changed")
    require(value.get("proposal") == "parma80_physical_flux", f"batch {index}: compact proposal changed")
    require(all(flag is True for flag in value["checks"].values()), f"batch {index}: a compact parse check failed")
    require_close(float(value["expected_energy_keV"]), LINE_ENERGY_KEV, f"batch {index}: expected energy")
    require(value["sim_footer"] == batch["sim_footer"], f"batch {index}: footer differs between aggregate and provenance")
    require(value["counts"] == batch["counts"], f"batch {index}: counts differ between aggregate and provenance")
    require(value["source_card"] == batch["source_card"], f"batch {index}: source differs between aggregate and provenance")
    require(value["raw_sim"]["path"] == batch["raw_sim"]["path"] and value["raw_sim"]["sha256"] == batch["raw_sim"]["sha256"], f"batch {index}: raw lineage differs")
    require(int(value["transport_seed"]) == int(batch["transport_seed"]), f"batch {index}: transport seed differs")
    require(value["parser"]["path"] == HARNESS_REL and value["parser"]["sha256"] == HARNESS_SHA256, f"batch {index}: parser authority changed")
    registry.verify(value["parser"]["path"], expected_sha256=value["parser"]["sha256"], label="line-only parser")
    geometry = value["geometry_authority"]
    require(geometry["setup"]["sha256"] == PROTECTED_HASHES[O8_SETUP_REL], f"batch {index}: O8 setup hash changed")


def angular_bin_from_dir_z(dir_z: float, bins: int) -> int:
    return max(0, min(bins - 1, int(math.floor((1.0 + dir_z) * bins / 2.0))))


def independently_weight_selected_events(
    selected: list[dict[str, Any]],
    te_s: float,
    grids: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    require(te_s > 0.0, "cannot weight events with non-positive TE")
    proposal = grids[80]
    weights_by_bins: dict[int, list[float]] = {}
    output: dict[str, Any] = {}
    for bins in (20, 40, 80):
        weights: list[float] = []
        for row in selected:
            direction = float(row["dir_z"])
            target_flux = float(grids[bins][angular_bin_from_dir_z(direction, bins)]["flux_ph_cm2_s"])
            proposal_flux = float(proposal[angular_bin_from_dir_z(direction, 80)]["flux_ph_cm2_s"])
            ratio = (bins / 80.0) * target_flux / proposal_flux
            weight = ratio / te_s
            require(math.isfinite(weight) and weight > 0.0, "non-positive/non-finite independent importance weight")
            weights.append(weight)
        weights_by_bins[bins] = weights
        rate = sum(weights)
        variance = sum(value * value for value in weights)
        sigma = math.sqrt(variance)
        output[str(bins)] = {
            "selected_events": len(weights),
            "importance_weighted_rate_cps": rate,
            "mc_stat_sigma_cps": sigma,
            "mc_relative_sigma": sigma / rate if rate > 0.0 else None,
            "importance_effective_sample_size": rate * rate / variance if variance > 0.0 else 0.0,
        }
    rate80 = float(output["80"]["importance_weighted_rate_cps"])
    paired_delta = [left - right for left, right in zip(weights_by_bins[40], weights_by_bins[80])]
    paired_sigma = math.sqrt(sum(value * value for value in paired_delta))
    if rate80 > 0.0:
        absolute_relative = abs(float(output["40"]["importance_weighted_rate_cps"]) - rate80) / rate80
        paired_relative = paired_sigma / rate80
        relative20 = float(output["20"]["importance_weighted_rate_cps"]) / rate80 - 1.0
        relative40 = float(output["40"]["importance_weighted_rate_cps"]) / rate80 - 1.0
    else:
        absolute_relative = paired_relative = relative20 = relative40 = None
    output["paired_diagnostics"] = {
        "relative_20_minus_80": relative20,
        "relative_40_minus_80": relative40,
        "paired_40_minus_80_mc_sigma_cps": paired_sigma,
        "absolute_relative_40_vs_80": absolute_relative,
        "paired_relative_40_minus_80_mc_sigma": paired_relative,
        "combined_relative_40_vs_80_error": (
            absolute_relative + paired_relative
            if absolute_relative is not None and paired_relative is not None
            else None
        ),
        "combined_definition": (
            "abs(rate40-rate80)/rate80 + sqrt(sum_i((w40_i-w80_i)^2))/rate80; "
            "the second term preserves same-event pairing"
        ),
    }
    return output


def independently_derive_gate(weighted: dict[str, Any]) -> dict[str, Any]:
    selected = int(weighted["80"]["selected_events"])
    ess = float(weighted["80"]["importance_effective_sample_size"])
    rse = weighted["80"]["mc_relative_sigma"]
    combined = weighted["paired_diagnostics"]["combined_relative_40_vs_80_error"]
    count_or_rse = selected >= 400 or (rse is not None and float(rse) <= 0.05)
    angular = combined is not None and float(combined) < 0.015
    passed = bool(count_or_rse and angular)
    return {
        "status": "PASS_PARMA511_LINE_MODULE_RATE_GATE" if passed else "DIAGNOSTIC_ONLY_FAIL_LINE_MODULE_RATE_GATE",
        "selected_events_80bin": selected,
        "importance_effective_sample_size_80bin": ess,
        "relative_standard_error_80bin": rse,
        "required_final_events_or_rse": ">=400 final events OR RSE<=0.05",
        "passes_count_or_rse": count_or_rse,
        "combined_relative_40_vs_80_error": combined,
        "required_combined_relative_40_vs_80_error": "<0.015",
        "passes_angular_paired_error": angular,
        "passes_detector_rate_gate": passed,
    }


def validate_gate_mapping(observed: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    require(isinstance(observed, dict) and set(observed) == REQUIRED_DYNAMIC_GATE_KEYS, f"{label} has a changed key set")
    for key, wanted in expected.items():
        actual = observed[key]
        if isinstance(wanted, float):
            require_close(float(actual), wanted, f"{label}.{key}")
        else:
            require(actual == wanted, f"{label}.{key} differs from independent reconstruction")


def validate_weighted_mapping(observed: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    require(set(observed) == {"20", "40", "80", "paired_diagnostics"}, f"{label} key set changed")
    numeric_keys = {
        "importance_weighted_rate_cps",
        "mc_stat_sigma_cps",
        "mc_relative_sigma",
        "importance_effective_sample_size",
    }
    for bins in (20, 40, 80):
        actual = observed[str(bins)]
        wanted = expected[str(bins)]
        require(set(actual) == {"selected_events", *numeric_keys}, f"{label} {bins}-bin field set changed")
        require(int(actual["selected_events"]) == int(wanted["selected_events"]), f"{label} {bins}-bin selected count differs")
        for key in numeric_keys:
            require_close(float(actual[key]), float(wanted[key]), f"{label} {bins}-bin {key}", atol=2.0e-15)
    paired_keys = {
        "relative_20_minus_80",
        "relative_40_minus_80",
        "paired_40_minus_80_mc_sigma_cps",
        "absolute_relative_40_vs_80",
        "paired_relative_40_minus_80_mc_sigma",
        "combined_relative_40_vs_80_error",
        "combined_definition",
    }
    actual_paired = observed["paired_diagnostics"]
    wanted_paired = expected["paired_diagnostics"]
    require(set(actual_paired) == paired_keys, f"{label} paired-diagnostic field set changed")
    require(actual_paired["combined_definition"] == wanted_paired["combined_definition"], f"{label} paired definition changed")
    for key in paired_keys - {"combined_definition"}:
        require_close(float(actual_paired[key]), float(wanted_paired[key]), f"{label} paired {key}", atol=2.0e-15)


def validate_primary_response_csv(
    path: Path,
    response: dict[str, Any],
    te_s: float,
    grids: dict[int, list[dict[str, Any]]],
    expected_tes_events: int,
    expected_pixel_hits: int,
    label: str,
) -> dict[str, Any]:
    rows = read_csv(path, expected_header=PRIMARY_RESPONSE_HEADER)
    require(len(rows) == expected_tes_events, f"{label}: primary CSV row count differs from compact TES events")
    parsed: list[dict[str, Any]] = []
    event_ids: set[int] = set()
    class_counts: Counter[str] = Counter()
    accepted = {"single", "keep", "reject_kept"}
    allowed_classes = {"not_evaluated", "zero_after_threshold", "single", "keep", "veto", "reject_kept"}
    raw_count = active_count = final_count = broad_count = 0
    for index, row in enumerate(rows):
        event_id = strict_int(row["event_id"], f"{label}: event_id row {index}")
        require(event_id > 0 and event_id not in event_ids, f"{label}: duplicate/non-positive event_id {event_id}")
        event_ids.add(event_id)
        dir_z = finite_float(row["dir_z"], f"{label}: dir_z row {index}")
        require(-1.0 <= dir_z <= 1.0, f"{label}: dir_z outside [-1,1] at row {index}")
        measured = finite_float(row["measured_total_keV"], f"{label}: measured_total row {index}")
        active_energy = finite_float(row["active_total_keV"], f"{label}: active_total row {index}")
        multiplicity = strict_int(row["measured_multiplicity"], f"{label}: multiplicity row {index}")
        require(measured >= 0.0 and active_energy >= 0.0, f"{label}: negative energy at row {index}")
        raw_w2 = bool_text(row["raw_w2"])
        active_w2 = bool_text(row["active_w2"])
        final_w2 = bool_text(row["final_w2"])
        topology = row["topology_class"]
        require(topology in allowed_classes, f"{label}: unknown topology class {topology!r}")
        broad = 480.0 <= measured < 550.0
        active_pass = active_energy < 50.0
        expected_raw = 510.58 <= measured < 511.42
        require(raw_w2 is expected_raw, f"{label}: raw_w2 selection mismatch at row {index}")
        require(active_w2 is (expected_raw and active_pass), f"{label}: active_w2 selection mismatch at row {index}")
        if not (broad and active_pass):
            require(topology == "not_evaluated", f"{label}: topology evaluated outside broad/active contract at row {index}")
        elif multiplicity == 0:
            require(topology == "zero_after_threshold", f"{label}: zero-hit topology mismatch at row {index}")
        elif multiplicity == 1:
            require(topology == "single", f"{label}: single-hit topology mismatch at row {index}")
        elif multiplicity > MAX_ENUM_HITS:
            require(topology == "reject_kept", f"{label}: >MAX_ENUM_HITS policy mismatch at row {index}")
        else:
            require(topology in {"keep", "veto", "reject_kept"}, f"{label}: multi-hit topology mismatch at row {index}")
        expected_final = expected_raw and active_pass and topology in accepted
        require(final_w2 is expected_final, f"{label}: final_w2 selection mismatch at row {index}")
        raw_count += int(raw_w2)
        active_count += int(active_w2)
        final_count += int(final_w2)
        broad_count += int(broad and active_pass and topology in accepted)
        class_counts[topology] += 1
        parsed.append({
            "event_id": event_id,
            "dir_z": dir_z,
            "measured_total_keV": measured,
            "measured_multiplicity": multiplicity,
            "active_total_keV": active_energy,
            "raw_w2": raw_w2,
            "active_w2": active_w2,
            "final_w2": final_w2,
            "topology_class": topology,
        })
    primary = response["primary_420eV"]
    require(int(primary["response_seed"]) == PRIMARY_RESPONSE_SEED, f"{label}: primary response seed changed")
    require(int(primary["tes_events"]) == expected_tes_events, f"{label}: primary TES count changed")
    require(int(primary["pixel_hits_before_response"]) == expected_pixel_hits, f"{label}: primary pixel-hit count changed")
    require(int(primary["w2_raw_events"]) == raw_count, f"{label}: primary raw-W2 count differs from CSV")
    require(int(primary["w2_active_veto_pass_events"]) == active_count, f"{label}: primary active-W2 count differs from CSV")
    require(int(primary["w2_frozen_step05_pass_events"]) == final_count, f"{label}: primary final-W2 count differs from CSV")
    require(primary["topology_class_counts"] == dict(sorted(class_counts.items())), f"{label}: topology-class counts differ from CSV")
    selected_rows = [row for row in parsed if row["final_w2"]]
    expected_max_active = max((row["active_total_keV"] for row in selected_rows), default=None)
    if expected_max_active is None:
        require(primary["w2_final_active_energy_max_keV"] is None, f"{label}: final active-energy maximum should be null")
    else:
        require_close(float(primary["w2_final_active_energy_max_keV"]), expected_max_active, f"{label}: final active-energy maximum")
    weighted = independently_weight_selected_events(selected_rows, te_s, grids)
    validate_weighted_mapping(primary["paired_reweight"], weighted, f"{label}: primary paired reweight")
    gate = independently_derive_gate(weighted)
    validate_gate_mapping(response["primary_detector_rate_gate"], gate, f"{label}: response dynamic gate")
    return {
        "rows": parsed,
        "selected_rows": selected_rows,
        "raw_count": raw_count,
        "active_count": active_count,
        "final_count": final_count,
        "broad_count": broad_count,
        "weighted": weighted,
        "gate": gate,
    }


def validate_replica_csv(
    path: Path,
    response: dict[str, Any],
    te_s: float,
    primary: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    rows = read_csv(path, expected_header=REPLICA_HEADER)
    require(len(rows) == RESPONSE_REPLICAS, f"{label}: replica CSV is not exactly 64 rows")
    final_counts: list[float] = []
    rate80_values: list[float] = []
    for index, row in enumerate(rows):
        require(strict_int(row["replica_index"], f"{label}: replica index row {index}") == index, f"{label}: replica indices are not 0..63")
        seed = strict_int(row["response_seed"], f"{label}: response seed row {index}")
        require(seed == PRIMARY_RESPONSE_SEED + index * RESPONSE_SEED_STRIDE, f"{label}: response seed schedule changed at row {index}")
        raw = strict_int(row["w2_raw_events"], f"{label}: raw count row {index}")
        active = strict_int(row["w2_active_veto_pass_events"], f"{label}: active count row {index}")
        final = strict_int(row["w2_frozen_step05_pass_events"], f"{label}: final count row {index}")
        require(0 < final <= active <= raw <= int(response["primary_420eV"]["tes_events"]), f"{label}: count ordering failed at row {index}")
        values: dict[int, tuple[float, float, float]] = {}
        for bins in (20, 40, 80):
            rate = finite_float(row[f"rate_{bins}bin_cps"], f"{label}: {bins}-bin rate row {index}")
            sigma = finite_float(row[f"mc_sigma_{bins}bin_cps"], f"{label}: {bins}-bin sigma row {index}")
            ess = finite_float(row[f"ess_{bins}bin"], f"{label}: {bins}-bin ESS row {index}")
            require(rate > 0.0 and sigma > 0.0 and 0.0 < ess <= final + 1.0e-8, f"{label}: invalid {bins}-bin rate/sigma/ESS row {index}")
            require_close(ess, (rate / sigma) ** 2, f"{label}: {bins}-bin ESS identity row {index}")
            values[bins] = (rate, sigma, ess)
        require_close(values[80][0], final / te_s, f"{label}: 80-bin count/rate row {index}", atol=2.0e-15)
        require_close(values[80][1], math.sqrt(final) / te_s, f"{label}: 80-bin count/sigma row {index}", atol=2.0e-15)
        require_close(values[80][2], float(final), f"{label}: 80-bin count/ESS row {index}")
        relative20 = finite_float(row["relative_20_minus_80"], f"{label}: relative20 row {index}")
        relative40 = finite_float(row["relative_40_minus_80"], f"{label}: relative40 row {index}")
        require_close(relative20, values[20][0] / values[80][0] - 1.0, f"{label}: relative20 identity row {index}")
        require_close(relative40, values[40][0] / values[80][0] - 1.0, f"{label}: relative40 identity row {index}")
        if index == 0:
            require(raw == primary["raw_count"] and active == primary["active_count"] and final == primary["final_count"], f"{label}: replica row 0 counts differ from primary CSV")
            for bins in (20, 40, 80):
                wanted = primary["weighted"][str(bins)]
                require_close(values[bins][0], float(wanted["importance_weighted_rate_cps"]), f"{label}: row0 {bins}-bin rate")
                require_close(values[bins][1], float(wanted["mc_stat_sigma_cps"]), f"{label}: row0 {bins}-bin sigma")
                require_close(values[bins][2], float(wanted["importance_effective_sample_size"]), f"{label}: row0 {bins}-bin ESS")
            require_close(relative20, float(primary["weighted"]["paired_diagnostics"]["relative_20_minus_80"]), f"{label}: row0 relative20")
            require_close(relative40, float(primary["weighted"]["paired_diagnostics"]["relative_40_minus_80"]), f"{label}: row0 relative40")
        final_counts.append(float(final))
        rate80_values.append(values[80][0])
    ensemble = response["ensemble"]
    require(set(ensemble) == {"final_w2_count_mean", "final_w2_count_sample_std", "rate_80bin_cps_mean", "rate_80bin_cps_sample_std", "note"}, f"{label}: ensemble field set changed")
    require(ensemble["note"] == "Response seeds are not independent transported photons.", f"{label}: ensemble interpretation changed")
    require_close(float(ensemble["final_w2_count_mean"]), statistics.fmean(final_counts), f"{label}: ensemble count mean")
    require_close(float(ensemble["final_w2_count_sample_std"]), statistics.stdev(final_counts), f"{label}: ensemble count sample std")
    require_close(float(ensemble["rate_80bin_cps_mean"]), statistics.fmean(rate80_values), f"{label}: ensemble rate mean")
    require_close(float(ensemble["rate_80bin_cps_sample_std"]), statistics.stdev(rate80_values), f"{label}: ensemble rate sample std")
    return {"rows": RESPONSE_REPLICAS, "base_seed": PRIMARY_RESPONSE_SEED, "seed_stride": RESPONSE_SEED_STRIDE}


def validate_response_summary(
    registry: EvidenceRegistry,
    response_path: Path,
    response_dir: Path,
    provenance_path: Path,
    provenance_sha256: str,
    footer: dict[str, Any],
    expected_tes_events: int,
    expected_pixel_hits: int,
    grids: dict[int, list[dict[str, Any]]],
    label: str,
) -> dict[str, Any]:
    require(response_path == (response_dir / "response_64seed_summary.json").resolve(), f"{label}: summary path/name changed")
    require_under(response_path, response_dir, f"{label}: response summary")
    response = read_json(response_path)
    require(response.get("schema") == "o8-parma511-line-step05-response-v1", f"{label}: response schema changed")
    require(response.get("proposal") == "parma80", f"{label}: response proposal is not parma80")
    require(response.get("scope") == "atmospheric annihilation mono line only", f"{label}: response scope changed")
    input_parse = response["input_parse"]
    require(set(input_parse) == {"path", "sha256"}, f"{label}: response input-provenance schema changed")
    require(resolve_path(input_parse["path"]) == provenance_path.resolve(), f"{label}: response input-provenance path differs")
    require(input_parse["sha256"] == provenance_sha256, f"{label}: response input-provenance SHA differs")
    require(response["transport_footer"] == footer, f"{label}: response footer differs")
    detector = response["detector_response"]
    require_close(float(detector["fwhm_keV"]), 0.42, f"{label}: detector FWHM")
    require_close(float(detector["sigma_keV"]), 0.178357578060484, f"{label}: detector sigma")
    require_close(float(detector["tes_threshold_keV"]), 0.3, f"{label}: TES threshold")
    require_close(float(detector["active_threshold_keV"]), 50.0, f"{label}: active threshold")
    require(int(detector["primary_seed"]) == PRIMARY_RESPONSE_SEED, f"{label}: primary seed changed")
    require(int(detector["seed_stride"]) == RESPONSE_SEED_STRIDE, f"{label}: response seed stride changed")
    require(int(detector["replicas"]) == RESPONSE_REPLICAS, f"{label}: response replica count changed")
    require(detector["step05_implementation"] == "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py", f"{label}: Step05 path changed")
    require(detector["step05_sha256"] == "0c1e69e4a73bd8653e999b1d8d2aff404a37a44457e40f134388c819ad4b91ab", f"{label}: frozen Step05 hash changed")
    registry.verify(detector["step05_implementation"], expected_sha256=detector["step05_sha256"], label="frozen Step05 response implementation")
    require(detector["step09_summary"] == "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json", f"{label}: Step09 path changed")
    require(detector["step09_summary_sha256"] == "8d147e21928b4830a215ab034f29379383b4368b4177f8a16a2f45769df73a25", f"{label}: Step09 hash changed")
    registry.verify(detector["step09_summary"], expected_sha256=detector["step09_summary_sha256"], label="frozen Step09 response authority")
    require("passive Kapton" in str(detector.get("active_veto_predicate_blocker", "")), f"{label}: passive-Kapton blocker disappeared")
    require(detector["topology_contract"] == "broad 480<=E<550, active<50; single keep; multiplicity>MAX_ENUM_HITS reject_kept; otherwise frozen side_keep_from_hits(...,'keep')", f"{label}: topology contract changed")
    require(detector["active_shield_named_passive_kapton_wrappers_in_o8"] == [
        "ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm",
        "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm",
        "ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm",
    ], f"{label}: frozen passive-Kapton wrapper audit changed")
    expected_artifacts = {name: response_dir / name for name in RESPONSE_ARTIFACT_NAMES}
    artifacts = verify_artifact_map(
        registry,
        response["artifacts"],
        f"{label} artifacts",
        expected_paths=expected_artifacts,
        required_parent=response_dir,
    )
    angular_artifacts = response["angular_response_coefficients"]["artifacts"]
    require(set(angular_artifacts) == {"20", "40", "80"}, f"{label}: angular artifact set changed")
    for bins in (20, 40, 80):
        name = f"angular_response_coefficients_{bins}bins.csv"
        item = angular_artifacts[str(bins)]
        require(resolve_path(item["path"]) == artifacts[name], f"{label}: angular {bins}-bin path differs from verified artifact")
        require(item["sha256"] == sha256(artifacts[name]) and int(item["bytes"]) == artifacts[name].stat().st_size, f"{label}: angular {bins}-bin receipt differs")
    primary = validate_primary_response_csv(
        artifacts["primary_event_response.csv"], response, float(footer["TE_s"]), grids,
        expected_tes_events, expected_pixel_hits, label,
    )
    replica = validate_replica_csv(
        artifacts["response_seed_replicas.csv"], response, float(footer["TE_s"]), primary, label,
    )
    for name, path in artifacts.items():
        registry.verify(path, label=f"{label} post-read stability:{name}")
    registry.verify(response_path, label=f"{label} summary post-read stability")
    return {"response": response, "primary": primary, "replica": replica, "artifacts": artifacts}


def validate_dynamic_gate(
    receipt: dict[str, Any],
    response: dict[str, Any],
    independent_gate: dict[str, Any],
    *,
    require_pass: bool,
) -> dict[str, Any]:
    receipt_gate = receipt["response"]["primary_gate"]
    response_gate = response["primary_detector_rate_gate"]
    require(set(receipt_gate) == REQUIRED_DYNAMIC_GATE_KEYS, "aggregate dynamic primary gate field set changed")
    require(set(response_gate) == REQUIRED_DYNAMIC_GATE_KEYS, "response dynamic detector gate field set changed")
    require(receipt_gate == response_gate, "aggregate response.primary_gate and response-summary primary_detector_rate_gate differ")
    validate_gate_mapping(response_gate, independent_gate, "aggregate/response dynamic gate")
    if require_pass:
        require(response_gate["passes_detector_rate_gate"] is True, "completed campaign fails the dynamic detector-rate gate")
        require(str(response_gate["status"]).startswith("PASS"), "completed campaign dynamic gate status is not PASS")
    return dict(response_gate)


def validate_campaign_runtime_contract(registry: EvidenceRegistry, manifest: dict[str, Any]) -> dict[str, Any]:
    runtime = manifest["cosima_runtime_preflight"]
    require(runtime.get("status") == "PASS_PACKAGE44_EXACT_MINIMAL_COSIMA_ENVIRONMENT", "campaign runtime preflight is not PASS")
    cosima_expected = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
    cosima_path = verify_file_record(registry, runtime["cosima"], cosima_expected, "frozen Cosima runtime binary", require_repo=False)
    require(runtime["cosima"]["sha256"] == COSIMA_SHA256, "campaign Cosima binary hash changed")
    runner = runtime["package44_runner"]
    expected_runner = ROOT / "engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/code/run_s3d_o8_all8_activation.py"
    runner_path = registry.verify(expected_runner, expected_sha256=PACKAGE44_RUNNER_SHA256, label="frozen package-44 runtime runner")
    require(resolve_path(runner["path"]) == runner_path and runner["sha256"] == PACKAGE44_RUNNER_SHA256, "campaign package-44 runner authority changed")
    launch_environment = runtime["launch_environment"]
    require(isinstance(launch_environment, dict) and launch_environment, "campaign launch environment is empty")
    require(canonical_sha256(launch_environment) == LAUNCH_ENVIRONMENT_SHA256, "campaign launch environment canonical hash changed")
    require(runtime["launch_environment_canonical_sha256"] == LAUNCH_ENVIRONMENT_SHA256, "campaign launch-environment receipt hash changed")
    require(runtime.get("parent_environment_inherited") is False and runtime.get("rootsys_present") is False, "campaign runtime inherited an unsafe environment")
    expected_ld = str(launch_environment["LD_LIBRARY_PATH"]).split(":")
    require(runtime["ld_library_path_components"] == expected_ld, "campaign LD_LIBRARY_PATH components differ")
    probe = runtime["runtime_probe"]
    require(probe.get("status") == "PASS_COSIMA_HELP_RUNTIME_PROBE_NO_SOURCE_TRANSPORT", "campaign runtime probe status changed")
    require(probe.get("transport_launched") is False and probe.get("source_card_argument_present") is False, "campaign runtime probe reports transport/source activity")
    require(probe.get("command") == [cosima_path.as_posix(), "-h"] and int(probe.get("returncode", -1)) == 0, "campaign runtime probe command/return code changed")
    require(re.fullmatch(r"[0-9a-f]{64}", str(probe.get("combined_output_sha256", ""))) is not None and int(probe.get("combined_output_bytes", 0)) > 0, "campaign runtime-probe output receipt is malformed")
    return runtime


def validate_campaign_aggregate(
    registry: EvidenceRegistry,
    receipt_path: Path,
    source: dict[str, Any],
    *,
    require_complete: bool = True,
) -> dict[str, Any]:
    receipt_path = registry.verify(receipt_path, label="single-campaign aggregate receipt")
    receipt = read_json(receipt_path)
    included_indices = validate_receipt_coverage(receipt, require_complete=require_complete)

    manifest_ref = receipt["campaign_manifest"]
    require(set(manifest_ref) == {"path", "sha256_before_aggregate_receipt"}, "aggregate campaign-manifest reference schema changed")
    require(
        re.fullmatch(r"[0-9a-f]{64}", str(manifest_ref.get("sha256_before_aggregate_receipt", ""))) is not None,
        "aggregate receipt lacks a valid pre-aggregate campaign-manifest hash",
    )
    manifest_candidate = resolve_path(manifest_ref["path"])
    campaign_dir = manifest_candidate.parent
    expected_campaign_dir = PACKAGE / "transport/campaigns" / CAMPAIGN_ID
    require(campaign_dir == expected_campaign_dir.resolve(), f"aggregate points to unexpected campaign directory: {campaign_dir}")
    manifest_path = registry.verify(campaign_dir / "campaign_manifest.json", label="campaign manifest current state")
    require(manifest_candidate == manifest_path, "aggregate campaign-manifest path is not the exact campaign_manifest.json")
    campaign_dir = manifest_path.parent
    fingerprint = str(receipt.get("aggregate_fingerprint_sha256", ""))
    require(re.fullmatch(r"[0-9a-f]{64}", fingerprint) is not None, "aggregate fingerprint is malformed")
    expected_wave_name = f"wave_0000_{included_indices[-1]:04d}_{fingerprint[:12]}"
    expected_receipt = campaign_dir / "aggregate" / expected_wave_name / "campaign_aggregate_receipt.json"
    require(receipt_path == expected_receipt.resolve(), f"aggregate receipt path/name does not match its exact coverage/fingerprint: {receipt_path}")
    campaign_id = campaign_dir.name
    require(campaign_id == CAMPAIGN_ID, "campaign ID changed")
    manifest = read_json(manifest_path)
    require(manifest.get("schema") == "o8-parma511-line-transport-campaign-v1", "campaign manifest schema changed")
    expected_intent = {
        "base_seed": CAMPAIGN_BASE_SEED,
        "batches": 60,
        "campaign_id": CAMPAIGN_ID,
        "events_per_batch": EXPECTED_EVENTS_PER_BATCH,
        "line_energy_keV": LINE_ENERGY_KEV,
        "o8_setup_sha256": PROTECTED_HASHES[O8_SETUP_REL],
        "proposal_csv_sha256": sha256(source["grid_paths"][80]),
        "proposal_grid_bins": 80,
        "schema": "o8-parma511-line-transport-campaign-v1",
    }
    require(manifest.get("intent") == expected_intent, "campaign intent changed")
    require(canonical_sha256(manifest["intent"]) == INTENT_FINGERPRINT_SHA256, "campaign intent does not reproduce its frozen fingerprint")
    require(manifest.get("intent_fingerprint_sha256") == INTENT_FINGERPRINT_SHA256, "campaign intent fingerprint changed")
    require(manifest.get("scope_contract") == {
        "excluded": ["broadband photon continuum", "prompt", "delayed or activation", "focused signal", "all other particles", "full-chain recomposition"],
        "included": "atmospheric annihilation mono line at 510.99895 keV",
        "physical_flux_ph_cm2_s": LINE_FLUX,
        "physical_source_grid": "PARMA 80 equal-mu bins",
    }, "campaign scope contract changed")
    require(manifest.get("response_contract") == {
        "active_threshold_keV": 50.0,
        "default_replicas": RESPONSE_REPLICAS,
        "fwhm_keV": 0.42,
        "primary_atmospheric_seed": PRIMARY_RESPONSE_SEED,
        "seed_stride": RESPONSE_SEED_STRIDE,
        "sigma_keV": 0.178357578060484,
        "step05_sha256": "0c1e69e4a73bd8653e999b1d8d2aff404a37a44457e40f134388c819ad4b91ab",
        "step09_summary_sha256": "8d147e21928b4830a215ab034f29379383b4368b4177f8a16a2f45769df73a25",
        "tes_threshold_keV": 0.3,
    }, "campaign response contract changed")
    require(manifest.get("execution_gate") == {
        "command": "run-batch",
        "note": "Preparation is not authorization to launch transport.",
        "requires_confirmation": "RUN_O8_PARMA511_LINE_ONLY_510.99895",
        "requires_flag": "--authorize-line-only-cosima",
    }, "campaign execution-gate contract changed")
    runtime_contract = validate_campaign_runtime_contract(registry, manifest)
    line_authority_rows = source["grids"][80]
    authority = manifest["authority"]
    require(authority.get("status") == "PASS_O8_PARMA511_LINE_ONLY_PREFLIGHT", "campaign preflight authority is not PASS")
    require(authority.get("scope") == "atmospheric annihilation mono line only", "campaign scope changed")
    require_close(float(authority["line_energy_keV"]), LINE_ENERGY_KEV, "campaign line energy")
    require_close(float(authority["physical_flux_ph_cm2_s"]), LINE_FLUX, "campaign physical flux", atol=2.0e-13)
    require(authority["grid_rows"] == {"20": 20, "40": 40, "80": 80}, "campaign angular grids changed")
    authority_expected_paths = {
        O8_SETUP_REL: ROOT / O8_SETUP_REL,
        next(key for key in PROTECTED_HASHES if key.endswith(".geo")): ROOT / next(key for key in PROTECTED_HASHES if key.endswith(".geo")),
        next(key for key in PROTECTED_HASHES if key.endswith(".det")): ROOT / next(key for key in PROTECTED_HASHES if key.endswith(".det")),
        **{f"engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/line/parma511_day15_{bins}bins.csv": source["grid_paths"][bins] for bins in (20, 40, 80)},
        "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py": ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py",
        "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json": ROOT / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json",
    }
    verify_artifact_map(
        registry,
        authority["files"],
        "campaign authority",
        expected_paths=authority_expected_paths,
        required_parent=ROOT,
    )
    require(authority["files"][O8_SETUP_REL]["sha256"] == PROTECTED_HASHES[O8_SETUP_REL], "campaign O8 setup authority mismatch")

    batches = receipt["batch_receipts"]
    require([int(batch["batch_index"]) for batch in batches] == included_indices, "batch receipts are not ordered exactly like aggregate coverage")
    manifest_batches = manifest.get("batches", [])
    require(len(manifest_batches) == 60, "current campaign manifest does not contain 60 batch records")
    require([int(batch["batch_index"]) for batch in manifest_batches] == EXPECTED_BATCHES, "campaign-manifest batches are not ordered 0..59")
    manifest_batch_by_index = {int(batch["batch_index"]): batch for batch in manifest_batches}
    seeds: set[int] = set()
    total_ts = 0
    total_te = 0.0
    total_tes_events = 0
    total_pixel_hits = 0
    raw_by_index: dict[int, dict[str, Any]] = {}
    for batch in batches:
        index = int(batch["batch_index"])
        manifest_batch = manifest_batch_by_index[index]
        expected_seed = CAMPAIGN_BASE_SEED + index * CAMPAIGN_SEED_STRIDE
        expected_run_name = f"O8PARMA511L_{CAMPAIGN_ID}_b{index:04d}"
        expected_source_path = campaign_dir / "source_cards" / f"{expected_run_name}.source"
        expected_raw_path = campaign_dir / "raw" / f"{expected_run_name}.inc1.id1.sim.gz"
        parsed_dir = campaign_dir / "parsed" / f"batch_{index:04d}"
        expected_provenance_path = parsed_dir / "provenance.json"
        response_dir = parsed_dir / "response"
        expected_response_path = response_dir / "response_64seed_summary.json"
        require(int(manifest_batch["events_requested"]) == EXPECTED_EVENTS_PER_BATCH, f"batch {index}: manifest request is not 3M")
        require(int(manifest_batch["transport_seed"]) == int(batch["transport_seed"]) == expected_seed, f"batch {index}: transport seed schedule changed")
        require(manifest_batch["run_name"] == batch["run_name"] == expected_run_name, f"batch {index}: run name changed")
        require(resolve_path(manifest_batch["source_card"]) == resolve_path(batch["source_card"]["path"]) == expected_source_path.resolve(), f"batch {index}: source path mismatch")
        require(manifest_batch["source_card_sha256"] == batch["source_card"]["sha256"], f"batch {index}: manifest/receipt source hash mismatch")
        require(resolve_path(manifest_batch["expected_sim"]) == resolve_path(batch["raw_sim"]["path"]) == expected_raw_path.resolve(), f"batch {index}: raw-lineage path mismatch")
        require(int(manifest_batch["sim_bytes"]) == int(batch["raw_sim"]["bytes"]), f"batch {index}: manifest/receipt raw size mismatch")
        require(resolve_path(manifest_batch["parsed_dir"]) == parsed_dir.resolve(), f"batch {index}: parsed directory changed")
        require(resolve_path(manifest_batch["parse_provenance"]) == resolve_path(batch["compact_provenance"]["path"]) == expected_provenance_path.resolve(), f"batch {index}: provenance path mismatch")
        require(manifest_batch["parse_provenance_sha256"] == batch["compact_provenance"]["sha256"], f"batch {index}: manifest/receipt provenance hash mismatch")
        require(resolve_path(manifest_batch["response_summary"]) == resolve_path(batch["batch_response"]["path"]) == expected_response_path.resolve(), f"batch {index}: response path mismatch")
        require(manifest_batch["response_summary_sha256"] == batch["batch_response"]["sha256"], f"batch {index}: manifest/receipt response hash mismatch")
        require(int(manifest_batch["returncode"]) == 0, f"batch {index}: manifest transport return code is nonzero")
        require(manifest_batch["cosima_executable"] == runtime_contract["cosima"]["path"], f"batch {index}: Cosima executable path changed")
        require(manifest_batch["cosima_executable_sha256"] == COSIMA_SHA256, f"batch {index}: Cosima executable hash changed")
        require(manifest_batch["cosima_runtime_environment"] == runtime_contract, f"batch {index}: runtime environment differs from campaign preflight")
        require(manifest_batch["cosima_command"] == [runtime_contract["cosima"]["path"], "-s", str(expected_seed), expected_source_path.as_posix()], f"batch {index}: Cosima command provenance changed")
        expected_log = campaign_dir / "logs" / f"{expected_run_name}.stdout.log.gz"
        require(resolve_path(manifest_batch["stdout_log"]) == expected_log.resolve(), f"batch {index}: stdout log path changed")
        log_receipt = manifest_batch["stdout_log_receipt"]
        require(resolve_path(log_receipt["path"]) == expected_log.resolve() and log_receipt["compression"] == "gzip" and log_receipt["uncompressed_log_retained"] is False, f"batch {index}: stdout-log receipt changed")
        require(re.fullmatch(r"[0-9a-f]{64}", str(log_receipt["sha256"])) is not None and int(log_receipt["bytes"]) > 0, f"batch {index}: stdout-log hash/size receipt malformed")
        checks = batch["checks"]
        require(isinstance(checks, dict) and checks and all(value is True for value in checks.values()), f"batch {index}: aggregate check failed")
        require(batch.get("raw_was_read_during_this_receipt_check") is False, f"batch {index}: aggregate read raw unexpectedly")
        footer = batch["sim_footer"]
        require(int(footer["TS"]) == EXPECTED_EVENTS_PER_BATCH, f"batch {index}: TS is not 3M")
        require(float(footer["TE_s"]) > 0.0, f"batch {index}: TE is non-positive")
        require(int(batch["counts"]["generated_id_records"]) == EXPECTED_EVENTS_PER_BATCH, f"batch {index}: ID count mismatch")
        require(int(batch["counts"]["ia_init_records"]) == EXPECTED_EVENTS_PER_BATCH, f"batch {index}: INIT count mismatch")
        for n_bins in (20, 40, 80):
            angular_counts = batch["angular_counts"][str(n_bins)]
            require(len(angular_counts) == n_bins and sum(int(value) for value in angular_counts) == EXPECTED_EVENTS_PER_BATCH, f"batch {index}: {n_bins}-bin angular closure failed")
        seed = int(batch["transport_seed"])
        require(seed not in seeds, f"batch {index}: duplicate transport seed {seed}")
        seeds.add(seed)
        require(int(batch["sim_header"]["seed"]) == seed, f"batch {index}: SIM-header seed mismatch")
        require(resolve_path(batch["sim_header"]["geometry"]) == resolve_path(O8_SETUP_REL), f"batch {index}: SIM header points to wrong geometry")
        energy_match = re.search(r"Mono\s+([0-9.eE+-]+)", str(batch["sim_header"]["spectral_type_first"]))
        require(energy_match is not None and close(float(energy_match.group(1)), LINE_ENERGY_KEV, atol=0.001), f"batch {index}: SIM header is not the mono line")

        source_path = verify_file_record(registry, batch["source_card"], expected_source_path, f"batch {index} source card")
        validate_source_card(
            source_path,
            index,
            seed,
            line_authority_rows,
            str(batch["run_name"]),
            expected_raw_path,
        )
        compact_paths = verify_artifact_map(
            registry,
            batch["compact_artifacts"],
            f"batch {index} compact",
            expected_paths={name: parsed_dir / name for name in ("angular_counts.json", "tes_events.csv", "tes_pixel_hits.csv")},
            required_parent=parsed_dir,
        )
        provenance_path = verify_file_record(
            registry,
            batch["compact_provenance"],
            expected_provenance_path,
            f"batch {index} compact provenance",
        )
        response_path = verify_file_record(
            registry,
            batch["batch_response"],
            expected_response_path,
            f"batch {index} response summary",
        )
        validate_batch_provenance(registry, provenance_path, batch)
        provenance_value = read_json(provenance_path)
        provenance_artifacts = verify_artifact_map(
            registry,
            provenance_value["artifacts"],
            f"batch {index} provenance artifacts",
            expected_paths={name: path for name, path in compact_paths.items()},
            required_parent=parsed_dir,
        )
        require(provenance_artifacts == compact_paths, f"batch {index}: provenance and receipt compact paths differ")
        validate_response_summary(
            registry,
            response_path,
            response_dir.resolve(),
            provenance_path,
            str(batch["compact_provenance"]["sha256"]),
            footer,
            int(batch["counts"]["tes_events"]),
            int(batch["counts"]["tes_pixel_hits"]),
            source["grids"],
            f"batch {index}",
        )
        raw = batch["raw_sim"]
        raw_path = resolve_path(raw["path"])
        require(raw_path == expected_raw_path.resolve(), f"batch {index}: raw lineage is not the exact expected path")
        require(re.fullmatch(r"[0-9a-f]{64}", str(raw["sha256"])) is not None and int(raw["bytes"]) > 0, f"batch {index}: invalid raw receipt")
        raw_by_index[index] = {"path": raw_path.as_posix(), "sha256": str(raw["sha256"]), "bytes": int(raw["bytes"])}
        total_ts += int(footer["TS"])
        total_te += float(footer["TE_s"])
        total_tes_events += int(batch["counts"]["tes_events"])
        total_pixel_hits += int(batch["counts"]["tes_pixel_hits"])

    require(total_ts == len(included_indices) * EXPECTED_EVENTS_PER_BATCH, "campaign TS differs from included 3M batches")
    if require_complete:
        require(total_ts == EXPECTED_TOTAL_TS, "completed campaign TS is not 180M")
    merged = receipt["merged_compact"]
    require(int(merged["TS"]) == total_ts, "merged TS does not equal batch sum")
    require_close(float(merged["TE_s"]), total_te, "merged TE does not equal batch sum", atol=1.0e-6)
    require(int(merged["events"]) == total_tes_events, "merged TES-event count does not equal batch sum")
    require(int(merged["pixel_hits"]) == total_pixel_hits, "merged pixel-hit count does not equal batch sum")
    require(merged.get("raw_sim_files_read") is False, "aggregate reports reading raw files during compact merge")
    aggregate_dir = receipt_path.parent
    merged_dir = aggregate_dir / "merged_compact"
    merged_artifacts = verify_artifact_map(
        registry,
        merged["artifacts"],
        "merged compact",
        expected_paths={name: merged_dir / name for name in ("angular_counts.json", "event_lineage.csv", "tes_events.csv", "tes_pixel_hits.csv")},
        required_parent=merged_dir,
    )
    expected_merged_provenance = merged_dir / "provenance.json"
    require(resolve_path(merged["provenance"]) == expected_merged_provenance.resolve(), "merged provenance path/name changed")
    merged_provenance_path = registry.verify(
        expected_merged_provenance,
        expected_sha256=merged["provenance_sha256"],
        label="merged compact provenance",
    )
    merged_provenance = read_json(merged_provenance_path)
    require(merged_provenance.get("status") == "PASS_STREAM_PARSE_COMPLETE", "merged compact provenance is not PASS")
    require(all(value is True for value in merged_provenance["checks"].values()), "merged compact check failed")
    require(merged_provenance.get("raw_sim_files_read_during_merge") is False, "merged provenance reports raw reads")
    require(
        merged_provenance.get("aggregate_fingerprint_sha256") == receipt.get("aggregate_fingerprint_sha256"),
        "merged provenance and aggregate receipt fingerprints differ",
    )
    require(merged_provenance["sim_footer"] == {"TE_s": merged["TE_s"], "TS": merged["TS"]}, "merged provenance footer mismatch")
    require(int(merged_provenance["counts"]["tes_events"]) == total_tes_events, "merged provenance TES count mismatch")
    require(int(merged_provenance["counts"]["tes_pixel_hits"]) == total_pixel_hits, "merged provenance pixel count mismatch")
    require(merged_provenance["parser"]["path"] == HARNESS_REL and merged_provenance["parser"]["sha256"] == HARNESS_SHA256, "merged parser authority changed")
    merged_provenance_artifacts = verify_artifact_map(
        registry,
        merged_provenance["artifacts"],
        "merged provenance artifacts",
        expected_paths=merged_artifacts,
        required_parent=merged_dir,
    )
    require(merged_provenance_artifacts == merged_artifacts, "merged receipt/provenance artifact paths differ")

    response_ref = receipt["response"]
    require(set(response_ref) == {"primary_gate", "replicas", "summary", "summary_sha256"}, "aggregate response reference schema changed")
    require(int(response_ref["replicas"]) == RESPONSE_REPLICAS, "aggregate receipt does not record 64 response seeds")
    response_dir = aggregate_dir / "response"
    expected_response_path = response_dir / "response_64seed_summary.json"
    require(resolve_path(response_ref["summary"]) == expected_response_path.resolve(), "aggregate response summary path/name changed")
    response_path = registry.verify(
        expected_response_path,
        expected_sha256=response_ref["summary_sha256"],
        label="campaign aggregate response summary",
    )
    response_evidence = validate_response_summary(
        registry,
        response_path,
        response_dir.resolve(),
        merged_provenance_path,
        str(merged["provenance_sha256"]),
        {"TE_s": merged["TE_s"], "TS": merged["TS"]},
        total_tes_events,
        total_pixel_hits,
        source["grids"],
        "campaign aggregate",
    )
    response = response_evidence["response"]
    primary_evidence = response_evidence["primary"]
    gate = validate_dynamic_gate(
        receipt,
        response,
        primary_evidence["gate"],
        require_pass=require_complete,
    )
    matching_manifest_aggregates = [
        item
        for item in manifest.get("aggregates", [])
        if resolve_path(item.get("path", "")) == receipt_path
    ]
    require(len(matching_manifest_aggregates) == 1, "current campaign manifest does not uniquely reference this aggregate receipt")
    manifest_aggregate = matching_manifest_aggregates[0]
    require(manifest_aggregate.get("sha256") == sha256(receipt_path), "campaign manifest aggregate-receipt hash mismatch")
    require(manifest_aggregate.get("fingerprint") == receipt.get("aggregate_fingerprint_sha256"), "campaign manifest aggregate fingerprint mismatch")
    require(manifest_aggregate.get("included_batch_indices") == included_indices, "campaign manifest aggregate coverage differs from receipt")
    require(manifest_aggregate.get("primary_gate_status") == gate["status"], "campaign manifest dynamic gate status differs")

    cleanup_entries = receipt["cleanup_eligible_raw"]
    require(len(cleanup_entries) == len(included_indices), "aggregate cleanup-eligible count differs from coverage")
    require([int(item["batch_index"]) for item in cleanup_entries] == included_indices, "cleanup-eligible indices differ from aggregate coverage")
    for item in cleanup_entries:
        index = int(item["batch_index"])
        require(item["path"] == raw_by_index[index]["path"] or resolve_path(item["path"]).as_posix() == raw_by_index[index]["path"], f"batch {index}: cleanup raw path mismatch")
        require(item["sha256"] == raw_by_index[index]["sha256"], f"batch {index}: cleanup raw hash mismatch")
        require(item.get("batch_compact_and_response_closed") is True and item.get("raw_was_read_during_aggregate") is False, f"batch {index}: raw is not cleanup-eligible")

    registry.verify(receipt_path, label="aggregate receipt post-read stability")
    registry.verify(manifest_path, label="campaign manifest post-read stability")
    registry.verify(merged_provenance_path, label="merged provenance post-read stability")
    registry.verify(response_path, label="aggregate response post-read stability")

    ignored = [
        {
            "field": "aggregate_receipt.status",
            "value": receipt.get("status"),
            "authority": "INFORMATIONAL_ONLY",
            "reason": "producer top-level status may retain a hard-coded DIAGNOSTIC string; the dynamic primary gate is authoritative",
        },
        {
            "field": "response_summary.status",
            "value": response.get("status"),
            "authority": "INFORMATIONAL_ONLY",
            "reason": "producer top-level status may retain a hard-coded DIAGNOSTIC string; the dynamic primary gate is authoritative",
        },
        {
            "field": "campaign_manifest.batch_status_counts",
            "value": manifest.get("batch_status_counts"),
            "authority": "INFORMATIONAL_ONLY",
            "reason": "PREPARED/DIAGNOSTIC labels are producer bookkeeping; included compact batch receipts and their checks are validated directly",
        },
    ]
    return {
        "receipt_path": receipt_path,
        "receipt": receipt,
        "receipt_sha256": sha256(receipt_path),
        "campaign_dir": campaign_dir,
        "campaign_id": campaign_id,
        "campaign_manifest_path": manifest_path,
        "response_path": response_path,
        "response": response,
        "gate": gate,
        "raw_by_index": raw_by_index,
        "merged_provenance_path": merged_provenance_path,
        "merged_counts": dict(merged_provenance["counts"]),
        "primary_csv_selected": primary_evidence["final_count"],
        "primary_csv_broad_selected": primary_evidence["broad_count"],
        "independent_weighted_response": primary_evidence["weighted"],
        "response_replica_validation": response_evidence["replica"],
        "included_batch_indices": included_indices,
        "complete": require_complete,
        "transport": {
            "batches": len(included_indices),
            "TS": total_ts,
            "TE_s": total_te,
            "unique_transport_seeds": len(seeds),
            "tes_events": total_tes_events,
            "tes_pixel_hits": total_pixel_hits,
        },
        "ignored_status_fields": ignored,
    }


def validate_cleanup_receipts(
    registry: EvidenceRegistry,
    cleanup_paths: list[Path],
    campaign: dict[str, Any],
) -> dict[str, Any]:
    require(cleanup_paths, "at least one external raw-cleanup receipt is required")
    covered: dict[int, str] = {}
    receipts: list[dict[str, Any]] = []
    final_raw = campaign["raw_by_index"]
    for ordinal, input_path in enumerate(cleanup_paths, start=1):
        path = registry.verify(input_path, label=f"external raw-cleanup receipt {ordinal}")
        require(path.parent == campaign["campaign_dir"], f"cleanup receipt {ordinal}: path is not directly under the exact campaign directory")
        value = read_json(path)
        require(value.get("schema") == "o8-parma511-line-external-raw-cleanup-v1", f"cleanup receipt {ordinal}: schema changed")
        require(value.get("status") == "EXACT_NEW_CAMPAIGN_RAW_FILES_REMOVED_AFTER_COMPACT_CLOSURE", f"cleanup receipt {ordinal}: status is not closed")
        require(value.get("scope") == "atmospheric annihilation 510.99895-keV mono module only", f"cleanup receipt {ordinal}: scope changed")
        require(value.get("campaign_id") == campaign["campaign_id"], f"cleanup receipt {ordinal}: wrong campaign ID")
        expected_cleanup_keys = {
            "schema", "status", "removed_at_utc", "scope", "campaign_id",
            "removed_batch_indices", "removed_raw_file_count", "source_cleanup_authority",
            "post_cleanup_check", "recovery", "destructive_scope_boundary",
        }
        if "removed_raw_bytes" in value:
            expected_cleanup_keys.add("removed_raw_bytes")
        require(set(value) == expected_cleanup_keys, f"cleanup receipt {ordinal}: top-level field set changed")
        indices = [int(item) for item in value["removed_batch_indices"]]
        require(indices == sorted(set(indices)) and indices, f"cleanup receipt {ordinal}: indices are empty, duplicated, or unsorted")
        require(path.name == f"EXTERNAL_RAW_CLEANUP_WAVE{indices[0]:04d}_{indices[-1]:04d}.json", f"cleanup receipt {ordinal}: filename does not match exact removed range")
        require(int(value["removed_raw_file_count"]) == len(indices), f"cleanup receipt {ordinal}: file count mismatch")
        for index in indices:
            require(index in final_raw, f"cleanup receipt {ordinal}: unknown batch {index}")
            require(index not in covered, f"batch {index} appears in multiple cleanup receipts")
            covered[index] = path.as_posix()

        source_ref = value["source_cleanup_authority"]
        source_candidate = resolve_path(source_ref["path"])
        require_under(source_candidate, campaign["campaign_dir"] / "aggregate", f"cleanup receipt {ordinal} source aggregate")
        require(source_candidate.name == "campaign_aggregate_receipt.json", f"cleanup receipt {ordinal}: source aggregate filename changed")
        source_path = registry.verify(source_candidate, expected_sha256=source_ref["sha256"], label=f"cleanup receipt {ordinal} source aggregate")
        source = read_json(source_path)
        require(source.get("schema") == "o8-parma511-line-campaign-aggregate-v1", f"cleanup receipt {ordinal}: source aggregate schema changed")
        eligible = {int(item["batch_index"]): item for item in source["cleanup_eligible_raw"]}
        source_indices = [int(item) for item in source["included_batch_indices"]]
        source_fingerprint = str(source["aggregate_fingerprint_sha256"])
        require(source_path.parent.name == f"wave_0000_{source_indices[-1]:04d}_{source_fingerprint[:12]}", f"cleanup receipt {ordinal}: source aggregate directory/fingerprint mismatch")
        require(int(source_ref["cleanup_eligible_entries"]) == len(eligible), f"cleanup receipt {ordinal}: eligible-entry count mismatch")
        expected_source_ref_keys = {"path", "sha256", "cleanup_eligible_entries", "all_batch_checks_true", "raw_files_read_during_aggregate"}
        if "removed_entries_subset" in source_ref:
            expected_source_ref_keys.add("removed_entries_subset")
            require(int(source_ref["removed_entries_subset"]) == len(indices), f"cleanup receipt {ordinal}: removed-subset count mismatch")
        else:
            require(indices == list(range(15)) and len(eligible) == 15, f"cleanup receipt {ordinal}: only the frozen first-wave receipt may omit removed_entries_subset")
        require(set(source_ref) == expected_source_ref_keys, f"cleanup receipt {ordinal}: source-authority field set changed")
        require(source_ref.get("all_batch_checks_true") is True and source_ref.get("raw_files_read_during_aggregate") is False, f"cleanup receipt {ordinal}: source authority flags failed")
        batch_map = {int(item["batch_index"]): item for item in source["batch_receipts"]}
        for index in indices:
            require(index in eligible and index in batch_map, f"cleanup receipt {ordinal}: batch {index} absent from source aggregate")
            require(all(flag is True for flag in batch_map[index]["checks"].values()), f"cleanup receipt {ordinal}: batch {index} had a failed source check")
            require(batch_map[index].get("raw_was_read_during_this_receipt_check") is False, f"cleanup receipt {ordinal}: batch {index} raw was read during receipt check")
            source_raw = eligible[index]
            require(resolve_path(source_raw["path"]).as_posix() == final_raw[index]["path"], f"cleanup receipt {ordinal}: batch {index} raw path differs from final aggregate")
            require(source_raw["sha256"] == final_raw[index]["sha256"], f"cleanup receipt {ordinal}: batch {index} raw hash differs from final aggregate")
        if "removed_raw_bytes" in value:
            require(int(value["removed_raw_bytes"]) == sum(final_raw[index]["bytes"] for index in indices), f"cleanup receipt {ordinal}: removed byte total mismatch")
        else:
            require(indices == list(range(15)), f"cleanup receipt {ordinal}: only the frozen first-wave receipt may omit removed_raw_bytes")
        post = value["post_cleanup_check"]
        require(set(post) == {"campaign_raw_directory_regular_files", "retained_compact_batches", "retained_campaign_aggregate", "retained_source_cards", "retained_compressed_logs", "retained_raw_sha256_in_provenance"}, f"cleanup receipt {ordinal}: post-cleanup field set changed")
        require(int(post["campaign_raw_directory_regular_files"]) == 0 and int(post["retained_compact_batches"]) == len(source_indices), f"cleanup receipt {ordinal}: post-cleanup count audit failed")
        require(post.get("retained_campaign_aggregate") is True and post.get("retained_source_cards") is True and post.get("retained_compressed_logs") is True and post.get("retained_raw_sha256_in_provenance") is True, f"cleanup receipt {ordinal}: retained-evidence flags failed")
        registry.verify(source_path, label=f"cleanup receipt {ordinal} source aggregate post-read stability")
        registry.verify(path, label=f"cleanup receipt {ordinal} post-read stability")
        receipts.append({
            "path": path.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "removed_batch_indices": indices,
            "source_cleanup_authority": source_path.as_posix(),
            "source_cleanup_authority_sha256": sha256(source_path),
        })

    require(sorted(covered) == EXPECTED_BATCHES, f"cleanup receipts cover {len(covered)}/60 batches, not exactly 0..59")
    for index, raw in final_raw.items():
        require(not os.path.lexists(raw["path"]), f"batch {index}: raw path still exists after claimed cleanup: {raw['path']}")
    return {
        "status": "PASS_EXTERNAL_RAW_CLEANUP_60_OF_60",
        "covered_batch_indices": EXPECTED_BATCHES,
        "raw_files_absent": 60,
        "receipts": receipts,
        "recovery_boundary": "The 60 removed raw SIM files are not locally recoverable; their exact paths, sizes, SHA-256 values, source cards, seeds, compact catalogs, response outputs, and cleanup receipts remain auditable.",
    }


def validate_recomposition(
    registry: EvidenceRegistry,
    directory: Path,
    campaign: dict[str, Any],
) -> dict[str, Any]:
    directory = directory.resolve()
    require_under(directory, PACKAGE / "recomposition/outputs", "recomposition directory")
    require(directory.is_dir(), f"missing recomposition directory: {directory}")
    names = {
        "flux": "parma511_line_flux_by_time.csv",
        "timeline": "w2_modular_recomposition_by_time.csv",
        "day15": "day15_modular_recomposition.json",
        "mission": "mission_20d_modular_recomposition.json",
        "result": "RECOMPOSITION_RESULT.md",
        "manifest": "recomposition_manifest.json",
    }
    paths = {key: registry.verify(directory / name, label=f"final recomposition:{name}") for key, name in names.items()}
    manifest = read_json(paths["manifest"])
    day15 = read_json(paths["day15"])
    mission = read_json(paths["mission"])
    require(manifest.get("schema") == "o8-parma511-modular-recomposition-manifest-v1", "recomposition manifest schema changed")
    require(day15.get("schema") == "o8-parma511-day15-modular-recomposition-v1", "day-15 recomposition schema changed")
    require(mission.get("schema") == "o8-parma511-20d-modular-recomposition-v1", "mission recomposition schema changed")
    require(manifest.get("scope") == "offline replacement of only the atmospheric annihilation mono-line module", "recomposition scope changed")

    expected_config_path = PACKAGE / "recomposition/config/modular_recomposition_config.json"
    expected_builder_path = PACKAGE / "recomposition/code/build_modular_recomposition.py"
    require(resolve_path(manifest["config"]["path"]) == expected_config_path.resolve(), "recomposition manifest points to an unexpected config")
    require(manifest["config"]["sha256"] == RECOMPOSITION_CONFIG_SHA256, "recomposition config is not the frozen reviewed version")
    config_path = registry.verify(expected_config_path, expected_sha256=RECOMPOSITION_CONFIG_SHA256, label="recomposition config")
    config = read_json(config_path)
    require(config.get("schema") == "o8-parma511-modular-recomposition-config-v1", "recomposition config schema changed")
    scope = config["scope_contract"]
    require(scope.get("only_replaced_module") == "atmospheric annihilation 510.99895-keV mono line", "recomposition replacement scope changed")
    for key in ("cosima_or_transport_allowed", "continuum_rerun_allowed", "m_sampling_transport_allowed", "retained_products_writable", "m04_writable"):
        require(scope.get(key) is False, f"unsafe recomposition scope flag: {key}")
    require(resolve_path(manifest["script"]["path"]) == expected_builder_path.resolve(), "recomposition manifest points to an unexpected builder")
    require(manifest["script"]["sha256"] == RECOMPOSITION_BUILDER_SHA256, "recomposition builder is not the frozen reviewed version")
    registry.verify(expected_builder_path, expected_sha256=RECOMPOSITION_BUILDER_SHA256, label="recomposition script")
    for name, item in manifest["input_authorities"].items():
        require(name in config["authorities"], f"recomposition manifest contains an authority absent from config: {name}")
        require(item["path"] == config["authorities"][name]["path"] and item["sha256"] == config["authorities"][name]["sha256"], f"recomposition authority {name} differs from frozen config")
        authority_path = resolve_path(config["authorities"][name]["path"])
        require_under(authority_path, ROOT, f"recomposition input authority:{name}")
        registry.verify(authority_path, expected_sha256=item["sha256"], label=f"recomposition input authority:{name}")
        require(item.get("matches_config") is True, f"recomposition authority {name} did not match config")
    require(set(manifest["input_authorities"]) == set(config["authorities"]), "recomposition manifest/config authority sets differ")
    occupancy_config = config["prompt_gamma_line_occupancy_dedup"]
    removed_prompt_gamma_line_day15_hz = finite_float(
        occupancy_config["day15_removed_event_rate_hz"],
        "recomposition prompt-gamma line occupancy removal",
    )
    require_close(removed_prompt_gamma_line_day15_hz, 737.844505175763, "frozen prompt-gamma line occupancy removal", atol=2.0e-12)
    require(occupancy_config["mission_scale_field"] == "prompt_scale_gamma", "prompt-gamma occupancy removal scale field changed")
    expected_occupancy_formula = (
        "lambda(t) = prompt_event_rate_hz(t) - removed_prompt_gamma_line_occupancy_hz(t) + "
        "delayed_event_rate_hz(t) + corrected_PARMA511_event_rate_hz(t)"
    )
    require(occupancy_config["corrected_total_occupancy_formula"] == expected_occupancy_formula, "recomposition occupancy formula changed")
    require(int(occupancy_config["affected_rows_expected"]) == 317048, "prompt-gamma occupancy affected-row authority changed")
    require(int(occupancy_config["tes_nonzero_rows_expected"]) == 0, "prompt-gamma occupancy TES-row authority changed")
    require(int(occupancy_config["active_volume_nonzero_rows_expected"]) == 317048, "prompt-gamma occupancy active-row authority changed")
    dedup_authority = read_json(resolve_path(config["authorities"]["prompt_gamma_line_dedup"]["path"]))
    require(str(dedup_authority.get("status", "")).startswith("PASS_OFFLINE_LINE_TERM_DEDUP"), "prompt-gamma line de-dup authority is not PASS")
    dedup_catalog = dedup_authority["affected_events"]["step05_catalog"]
    require_close(float(dedup_catalog["removed_rate_sum_cps"]), removed_prompt_gamma_line_day15_hz, "prompt-gamma occupancy removal vs audit", atol=2.0e-12)
    require(int(dedup_catalog["affected_rows"]) == int(occupancy_config["affected_rows_expected"]), "prompt-gamma occupancy affected rows differ from audit")
    require(int(dedup_catalog["tes_nonzero_rows"]) == int(occupancy_config["tes_nonzero_rows_expected"]), "prompt-gamma occupancy TES rows differ from audit")
    require(int(dedup_catalog["active_volume_nonzero_rows"]) == int(occupancy_config["active_volume_nonzero_rows_expected"]), "prompt-gamma occupancy active rows differ from audit")
    retained_mission_rows = read_csv(resolve_path(config["authorities"]["mission_timeline"]["path"]))
    retained_trajectory_rows = read_csv(resolve_path(config["authorities"]["trajectory"]["path"]))
    require(len(retained_mission_rows) == len(retained_trajectory_rows) == 81, "retained mission/trajectory authorities are not 81 bins")
    for name, item in manifest["protected_files_after_run"].items():
        require(name in config["protected_files"], f"recomposition protected file absent from config: {name}")
        require(item["path"] == config["protected_files"][name]["path"] and item["sha256"] == config["protected_files"][name]["sha256"], f"recomposition protected file {name} differs from config")
        protected_path = resolve_path(config["protected_files"][name]["path"])
        require_under(protected_path, ROOT, f"recomposition protected file:{name}")
        registry.verify(protected_path, expected_sha256=item["sha256"], label=f"recomposition protected file:{name}")
        require(item.get("matches_config") is True, f"recomposition protected file {name} did not match config")
    require(set(manifest["protected_files_after_run"]) == set(config["protected_files"]), "recomposition protected-file sets differ")
    expected_output_names = {names["flux"], names["timeline"], names["day15"], names["mission"], names["result"]}
    require(set(manifest["outputs"]) == expected_output_names, "recomposition manifest output set is incomplete or unexpected")
    manifest_output_paths = verify_artifact_map(
        registry,
        manifest["outputs"],
        "recomposition manifest outputs",
        expected_paths={name: directory / name for name in expected_output_names},
        required_parent=directory,
    )
    for key in ("flux", "timeline", "day15", "mission", "result"):
        require(paths[key] == manifest_output_paths[names[key]], f"recomposition {key} verified/read path mismatch")

    line = manifest["line_input"]
    require(line.get("input_kind") == "final_line_campaign_aggregate", "recomposition did not use a final campaign aggregate")
    require(resolve_path(line["input_path"]) == campaign["receipt_path"], "recomposition used a different aggregate receipt")
    require(line["input_sha256"] == campaign["receipt_sha256"], "recomposition aggregate-receipt hash mismatch")
    require(resolve_path(line["response_summary_path"]) == campaign["response_path"], "recomposition used a different response summary")
    require(line["response_summary_sha256"] == sha256(campaign["response_path"]), "recomposition response-summary hash mismatch")
    require(line.get("passes_detector_rate_gate") is True and line.get("passes_final_input_gate") is True, "recomposition final input gate is not PASS")
    require(line.get("response_grade") == "CAMPAIGN_RATE_GATE_PASS", "recomposition response grade is not campaign PASS")
    receipt_meta = line["campaign_receipt"]
    require(receipt_meta.get("aggregate_complete") is True and receipt_meta.get("allow_partial") is False, "recomposition campaign metadata is incomplete")
    require(receipt_meta.get("included_batch_indices") == EXPECTED_BATCHES and receipt_meta.get("incomplete_batch_indices") == [], "recomposition campaign batch coverage is not 60/60")
    require(line["detector_gate"] == campaign["gate"], "recomposition detector gate differs from campaign dynamic gate")

    response = campaign["response"]
    weighted = response["primary_420eV"]["paired_reweight"]["80"]
    require_close(float(line["w2_rate_day15_cps"]), float(weighted["importance_weighted_rate_cps"]), "recomposition line rate vs response")
    require_close(float(line["w2_mc_sigma_day15_cps"]), float(weighted["mc_stat_sigma_cps"]), "recomposition line sigma vs response")
    require(int(line["w2_selected_events"]) == int(weighted["selected_events"]), "recomposition line count vs response")
    require_close(float(line["w2_importance_effective_sample_size"]), float(weighted["importance_effective_sample_size"]), "recomposition line ESS vs response")
    require_close(float(line["transport_TE_s"]), float(campaign["transport"]["TE_s"]), "recomposition TE vs campaign", atol=1.0e-6)
    occupancy_events = int(campaign["merged_counts"]["tes_or_active_events"])
    expected_occupancy_hz = occupancy_events / float(campaign["transport"]["TE_s"])
    require(int(line["line_occupancy_events"]) == occupancy_events, "recomposition line occupancy-event count differs from merged compact")
    require_close(float(line["line_occupancy_day15_hz"]), expected_occupancy_hz, "recomposition line occupancy is not merged tes_or_active/TE")
    require(line["line_occupancy_method"] == "exact merged tes_or_active_events/TE from the line-only campaign compact provenance", "recomposition line occupancy method changed")
    require(int(line["broad_selected_events"]) == int(campaign["primary_csv_broad_selected"]), "recomposition broad-window count differs from primary event CSV")
    require_close(float(line["broad_rate_day15_cps"]), int(campaign["primary_csv_broad_selected"]) / float(campaign["transport"]["TE_s"]), "recomposition broad rate is not count/TE")
    try:
        from scipy.stats import chi2
    except ImportError as exc:
        raise ValidationError("SciPy is required to independently verify the saved Garwood endpoints") from exc
    selected_count = int(line["w2_selected_events"])
    broad_count = int(line["broad_selected_events"])
    te_s = float(campaign["transport"]["TE_s"])
    expected_w2_upper = 0.5 * float(chi2.ppf(0.975, 2.0 * (selected_count + 1))) / te_s
    expected_broad_upper = 0.5 * float(chi2.ppf(0.975, 2.0 * (broad_count + 1))) / te_s
    require_close(float(line["w2_upper95_day15_cps"]), expected_w2_upper, "recomposition W2 Garwood upper endpoint", atol=2.0e-15)
    require_close(float(line["broad_upper95_day15_cps"]), expected_broad_upper, "recomposition broad Garwood upper endpoint", atol=2.0e-15)
    require(line["w2_upper95_method"] == "two-sided 95% Garwood upper endpoint on primary transported count divided by TE", "recomposition W2 endpoint method changed")
    require(day15["line_input"] == line, "day-15 and manifest line-input records differ")

    expected_formula = "R_new = R_old - R_legacy_sidecar - Delta_R_prompt_gamma_line + R_PARMA511_corrected"
    composition = day15["composition"]
    require(composition.get("formula") == expected_formula, "recomposition formula text changed")
    require(composition.get("legacy_sidecar_removed") is True and composition.get("all_other_modules_reused") is True, "recomposition did not preserve modular replacement")
    require(composition.get("occupancy_formula") == expected_occupancy_formula, "recomposition day-15 occupancy formula changed")
    require(composition.get("legacy_sidecar_subtracted_from_prompt_occupancy") is False, "legacy sidecar was incorrectly subtracted from prompt occupancy")
    require(composition.get("prompt_gamma_misplaced_line_occupancy_removed") is True, "prompt-gamma misplaced-line occupancy was not removed")
    require(float(composition["prompt_gamma_line_dedup_delta_W2_cps"]) == 0.0 and float(composition["prompt_gamma_line_dedup_delta_broad_480_550_cps"]) == 0.0, "prompt-gamma de-dup delta is not exactly zero")
    rates = day15["retained_and_replaced_rates_cps"]
    from_components = float(rates["prompt_retained"]) + float(rates["delayed_retained"]) - float(composition["prompt_gamma_line_dedup_delta_W2_cps"]) + float(rates["corrected_PARMA511_added"])
    from_old_formula = float(rates["old_background"]) - float(rates["legacy_atm511_sidecar_removed"]) - float(composition["prompt_gamma_line_dedup_delta_W2_cps"]) + float(rates["corrected_PARMA511_added"])
    require_close(float(rates["recomposed_background"]), from_components, "day-15 recomposed background from frozen modules")
    require_close(float(rates["recomposed_background"]), from_old_formula, "day-15 explicit replacement formula")
    require_close(float(rates["recomposed_minus_old_background"]), float(rates["recomposed_background"]) - float(rates["old_background"]), "day-15 background delta")
    require_close(float(rates["corrected_PARMA511_added"]), float(line["w2_rate_day15_cps"]), "day-15 corrected line rate")

    invariants = manifest["invariants"]
    required_invariants = {
        "time_bins_81",
        "elapsed_days_20",
        "day15_index_60",
        "legacy_sidecar_removed",
        "legacy_sidecar_occupancy_omitted_separately_once",
        "legacy_sidecar_not_subtracted_from_prompt_occupancy",
        "day15_prompt_gamma_line_occupancy_removal_matches_audit",
        "prompt_occupancy_nonnegative_after_dedup_all_81_bins",
        "total_occupancy_nonnegative_all_81_bins",
        "recomposed_occupancy_formula_passes_all_81_bins",
        "w2_prompt_gamma_line_dedup_delta_zero",
        "broad_prompt_gamma_line_dedup_delta_zero",
        "all_other_modules_reused",
    }
    require(required_invariants <= set(invariants) and all(invariants[key] is True for key in required_invariants), "recomposition manifest invariant failed")
    expected_attestation_keys = {
        "cosima_launched",
        "transport_launched",
        "continuum_rerun",
        "other_particle_rerun",
        "m_sampling_rerun",
        "retained_product_modified",
        "m04_modified",
    }
    for attestation_name, attestation in (("manifest", manifest["execution_attestation"]), ("day15", day15["no_rerun_attestation"])):
        require(set(attestation) == expected_attestation_keys, f"{attestation_name} no-rerun attestation key set changed")
        require(all(value is False for value in attestation.values()), f"{attestation_name} no-rerun attestation failed")
    identity = manifest["formula_identity_self_test"]
    require(identity.get("status") == "PASS_RETAINED_81BIN_FORMULA_IDENTITY", "retained formula identity did not pass")
    require(max(float(value) for value in identity["max_absolute_residuals"].values()) <= 5.0e-8, "retained formula identity residual is too large")
    require(mission["formula_audit"] == identity, "mission and manifest formula-identity records differ")
    require(mission["line_input_grade"] == "CAMPAIGN_RATE_GATE_PASS", "mission line-input grade is not campaign PASS")
    flux_audit = manifest["parma_flux_evaluation"]
    require(flux_audit.get("status") == "PASS_OFFICIAL_PARMA_LINE_FLUX_EVALUATION", "mission PARMA flux evaluation is not PASS")
    require("no Cosima/transport executable" in str(flux_audit.get("subprocess_allowlist", "")), "flux audit lacks its offline allowlist boundary")
    frozen_driver = config["parma_line_fold"]["driver"]
    require(resolve_path(frozen_driver["path"]) == (PACKAGE / "code/parma511_driver").resolve(), "recomposition PARMA driver path is not the exact package driver")
    require(resolve_path(frozen_driver["working_directory"]) == (PACKAGE / "vendor/parma_cpp_official_20260810").resolve(), "recomposition PARMA driver working directory changed")
    require(flux_audit["driver"] == frozen_driver["path"], "flux audit driver path differs from frozen config")
    require(flux_audit["driver_sha256"] == frozen_driver["sha256"], "flux audit driver hash differs from frozen config")
    require(resolve_path(flux_audit["working_directory"]) == resolve_path(frozen_driver["working_directory"]), "flux audit vendor working directory differs from frozen config")
    registry.verify(frozen_driver["path"], expected_sha256=frozen_driver["sha256"], label="hash-locked local PARMA line driver")

    flux_rows = read_csv(paths["flux"], expected_header=RECOMPOSITION_FLUX_HEADER)
    timeline = read_csv(paths["timeline"], expected_header=RECOMPOSITION_TIMELINE_HEADER)
    require(len(flux_rows) == len(timeline) == 81, "recomposition timeline is not 81 bins")
    require([int(row["time_bin_id"]) for row in timeline] == list(range(81)), "recomposition time-bin IDs are not 0..80")
    require(int(day15["day15_index_zero_based"]) == 60, "day-15 index is not 60")
    require(int(mission["time_bins"]) == 81, "mission summary time-bin count is not 81")
    require_close(float(mission["elapsed_days"]), 20.0, "mission elapsed days")

    cumulative_source = 0.0
    cumulative_background = 0.0
    cumulative_source_lower = 0.0
    cumulative_background_upper = 0.0
    cumulative_source_pre_fix = 0.0
    cumulative_background_pre_fix = 0.0
    cumulative_source_lower_pre_fix = 0.0
    cumulative_background_upper_pre_fix = 0.0
    elapsed = 0.0
    max_residual = 0.0
    elapsed_days: list[float] = []
    z_curve: list[float] = []
    z_conditional_curve: list[float] = []
    live_factors: list[float] = []
    retained_field_map = {
        "prompt_event_rate_hz_retained_before_line_occupancy_dedup": "prompt_event_rate_hz",
        "delayed_event_rate_hz_retained": "delayed_event_rate_hz",
        "legacy_sidecar_event_rate_hz_removed": "atm511_event_rate_hz",
        "prompt_final_cps_noacc_retained": "prompt_final_cps_noacc",
        "delayed_final_cps_noacc_retained": "delayed_final_cps_noacc",
        "legacy_sidecar_final_cps_noacc_removed": "atm511_final_cps_noacc",
        "signal_final_cps_noacc_retained": "signal_final_cps_noacc",
        "prompt_final_upper95_cps_noacc_retained": "prompt_final_upper95_cps_noacc",
        "delayed_final_upper95_cps_noacc_retained": "delayed_final_upper95_cps_noacc",
        "legacy_sidecar_final_upper95_cps_noacc_removed": "atm511_final_upper95_cps_noacc",
        "signal_final_lower95_cps_noacc_retained": "signal_final_lower95_cps_noacc",
    }
    trajectory_field_map = {
        "altitude_km": "altitude_km",
        "latitude_deg": "latitude_deg",
        "longitude_deg": "longitude_deg",
        "trajectory_Rc_GV_retained_prompt_delayed_only": "Rc_GV",
        "depth_g_cm2": "depth_g_cm2",
    }
    for index, (flux_row, row, base, trajectory) in enumerate(
        zip(flux_rows, timeline, retained_mission_rows, retained_trajectory_rows)
    ):
        require(int(flux_row["time_bin_id"]) == index and int(row["time_bin_id"]) == index, f"timeline alignment failed at bin {index}")
        require(int(base["time_bin_id"]) == index and int(trajectory["time_bin_id"]) == index, f"retained authority alignment failed at bin {index}")
        require_close(float(row["day_mid"]), float(base["day_mid"]), f"retained day_mid at bin {index}")
        require_close(float(trajectory["day_mid"]), float(base["day_mid"]), f"trajectory day_mid at bin {index}")
        require_close(float(row["dt_s"]), float(base["dt_s"]), f"retained dt at bin {index}")
        require_close(float(trajectory["dt_s"]), float(base["dt_s"]), f"trajectory dt at bin {index}")
        for output_field, authority_field in retained_field_map.items():
            require_close(float(row[output_field]), float(base[authority_field]), f"retained {output_field} at bin {index}")
        require_close(float(row["prompt_scale_gamma"]), float(base["prompt_scale_gamma"]), f"retained prompt_scale_gamma at bin {index}")
        for output_field, authority_field in trajectory_field_map.items():
            require_close(float(row[output_field]), float(trajectory[authority_field]), f"trajectory {output_field} at bin {index}")
        require_close(float(flux_row["day_mid"]), float(base["day_mid"]), f"flux day_mid at bin {index}")
        require_close(float(flux_row["depth_g_cm2"]), float(trajectory["depth_g_cm2"]), f"flux depth at bin {index}")
        require_close(float(flux_row["trajectory_Rc_GV_not_used_for_line"]), float(trajectory["Rc_GV"]), f"flux retained Rc at bin {index}")
        require_close(float(row["corrected_line_Rc_GV_fixed"]), float(config["parma_line_fold"]["cutoff_rigidity_GV"]), f"fixed corrected-line Rc at bin {index}")
        require_close(float(flux_row["cutoff_rigidity_GV_fixed"]), float(config["parma_line_fold"]["cutoff_rigidity_GV"]), f"flux fixed Rc at bin {index}")
        require_close(float(flux_row["solar_modulation_MV_fixed"]), float(config["parma_line_fold"]["solar_modulation_MV"]), f"flux fixed solar modulation at bin {index}")
        scale = float(row["corrected_line_flux_scale_to_day15"])
        flux = float(row["corrected_line_flux_ph_cm2_s"])
        require(flux > 0.0, f"non-positive corrected line flux at bin {index}")
        require_close(float(flux_row["parma511_flux_ph_cm2_s"]), flux, f"flux alignment at bin {index}")
        require_close(float(flux_row["scale_to_day15"]), scale, f"flux scale alignment at bin {index}")
        require_close(scale, flux / LINE_FLUX, f"flux/day15 scale at bin {index}")
        new_line = float(line["w2_rate_day15_cps"]) * scale
        new_occ = float(line["line_occupancy_day15_hz"]) * scale
        prompt_occ = float(base["prompt_event_rate_hz"])
        prompt_gamma_scale = float(base["prompt_scale_gamma"])
        removed_prompt_gamma_line_occ = removed_prompt_gamma_line_day15_hz * prompt_gamma_scale
        prompt_occ_after_dedup = prompt_occ - removed_prompt_gamma_line_occ
        require(prompt_occ_after_dedup >= 0.0, f"negative prompt occupancy after line de-dup at bin {index}")
        delayed_occ = float(base["delayed_event_rate_hz"])
        total_occ = prompt_occ_after_dedup + delayed_occ + new_occ
        pre_fix_total_occ = prompt_occ + delayed_occ + new_occ
        live = math.exp(-total_occ * 1.0e-6)
        pre_fix_live = math.exp(-pre_fix_total_occ * 1.0e-6)
        require(float(row["prompt_gamma_line_dedup_delta_cps"]) == 0.0, f"nonzero prompt-gamma de-dup delta at bin {index}")
        background = float(row["prompt_final_cps_noacc_retained"]) + float(row["delayed_final_cps_noacc_retained"]) - float(row["prompt_gamma_line_dedup_delta_cps"]) + new_line
        expected_line_upper = float(line["w2_upper95_day15_cps"]) * scale
        background_upper = float(row["prompt_final_upper95_cps_noacc_retained"]) + float(row["delayed_final_upper95_cps_noacc_retained"]) + expected_line_upper
        dt = float(row["dt_s"])
        require(dt > 0.0, f"non-positive dt at bin {index}")
        cumulative_source += float(row["signal_final_cps_noacc_retained"]) * live * dt
        cumulative_background += background * live * dt
        cumulative_source_lower += float(row["signal_final_lower95_cps_noacc_retained"]) * live * dt
        cumulative_background_upper += background_upper * live * dt
        cumulative_source_pre_fix += float(row["signal_final_cps_noacc_retained"]) * pre_fix_live * dt
        cumulative_background_pre_fix += background * pre_fix_live * dt
        cumulative_source_lower_pre_fix += float(row["signal_final_lower95_cps_noacc_retained"]) * pre_fix_live * dt
        cumulative_background_upper_pre_fix += background_upper * pre_fix_live * dt
        elapsed += dt
        current_day = elapsed / 86400.0
        current_z = cumulative_source / math.sqrt(cumulative_background)
        current_z_conditional = cumulative_source_lower / math.sqrt(cumulative_background_upper)
        elapsed_days.append(current_day)
        z_curve.append(current_z)
        z_conditional_curve.append(current_z_conditional)
        live_factors.append(live)
        expected = {
            "prompt_gamma_misplaced_line_event_rate_hz_removed": removed_prompt_gamma_line_occ,
            "prompt_event_rate_hz_after_line_occupancy_dedup": prompt_occ_after_dedup,
            "corrected_parma511_final_cps_noacc": new_line,
            "corrected_parma511_event_rate_hz": new_occ,
            "coincidence_occupancy_rate_hz_recomposed": total_occ,
            "coincidence_occupancy_rate_hz_pre_fix_no_prompt_gamma_occupancy_dedup": pre_fix_total_occ,
            "accidental_live_factor_recomposed": live,
            "accidental_live_factor_pre_fix_no_prompt_gamma_occupancy_dedup": pre_fix_live,
            "background_final_cps_noacc_recomposed": background,
            "corrected_parma511_final_upper95_cps_noacc": expected_line_upper,
            "background_componentwise_endpoint_cps_noacc_recomposed": background_upper,
            "cumulative_source_counts": cumulative_source,
            "cumulative_background_counts": cumulative_background,
            "cumulative_source_transport_counting_lower_endpoint_counts": cumulative_source_lower,
            "cumulative_background_componentwise_endpoint_counts": cumulative_background_upper,
            "counting_Z": current_z,
            "counting_Z_componentwise_endpoint_conditional": current_z_conditional,
            "elapsed_stop_day": current_day,
        }
        for field, wanted in expected.items():
            actual = float(row[field])
            residual = abs(actual - wanted)
            max_residual = max(max_residual, residual)
            require_close(actual, wanted, f"recomposition formula {field} at bin {index}", atol=5.0e-8)

    require_close(elapsed, 20.0 * 86400.0, "sum of recomposition dt is not 20 days", atol=5.0e-8)
    require_close(float(flux_rows[60]["parma511_flux_ph_cm2_s"]), LINE_FLUX, "day-15 mission-fold line flux", atol=2.0e-13)
    require_close(float(flux_rows[60]["scale_to_day15"]), 1.0, "day-15 mission-fold line scale")
    require_close(float(timeline[60]["day_mid"]), 15.0, "day-15 mission-fold day_mid")
    require_close(float(timeline[60]["depth_g_cm2"]), 3.4614689720143224, "day-15 mission-fold depth")

    day15_row = timeline[60]
    day15_base = retained_mission_rows[60]
    require_close(float(rates["prompt_retained"]), float(day15_base["prompt_final_cps_noacc"]), "day-15 summary retained prompt")
    require_close(float(rates["delayed_retained"]), float(day15_base["delayed_final_cps_noacc"]), "day-15 summary retained delayed")
    require_close(float(rates["signal_retained_slant45"]), float(day15_base["signal_final_cps_noacc"]), "day-15 summary retained signal")
    require_close(float(rates["legacy_atm511_sidecar_removed"]), float(day15_base["atm511_final_cps_noacc"]), "day-15 summary legacy sidecar")
    require_close(float(rates["old_background"]), float(day15_base["background_final_cps_noacc"]), "day-15 summary old background")
    require_close(float(rates["recomposed_background"]), float(day15_row["background_final_cps_noacc_recomposed"]), "day-15 summary recomposed background")
    endpoint_summary = day15["endpoint_rates_cps"]
    require_close(float(endpoint_summary["prompt_retained_componentwise_upper95"]), float(day15_base["prompt_final_upper95_cps_noacc"]), "day-15 prompt endpoint")
    require_close(float(endpoint_summary["delayed_retained_componentwise_upper95"]), float(day15_base["delayed_final_upper95_cps_noacc"]), "day-15 delayed endpoint")
    require_close(float(endpoint_summary["legacy_sidecar_upper95_removed"]), float(day15_base["atm511_final_upper95_cps_noacc"]), "day-15 legacy sidecar endpoint")
    require_close(float(endpoint_summary["corrected_line_endpoint_added"]), float(line["w2_upper95_day15_cps"]), "day-15 corrected line endpoint")
    require_close(float(endpoint_summary["recomposed_background_componentwise_endpoint"]), float(day15_row["background_componentwise_endpoint_cps_noacc_recomposed"]), "day-15 recomposed background endpoint")
    require(endpoint_summary["corrected_line_endpoint_method"] == line["w2_upper95_method"], "day-15 corrected-line endpoint method differs")
    occupancy_summary = day15["occupancy_and_live_factor"]
    require_close(float(occupancy_summary["prompt_hz_retained_before_line_occupancy_dedup"]), float(day15_base["prompt_event_rate_hz"]), "day-15 retained prompt occupancy")
    require_close(float(occupancy_summary["prompt_gamma_scale"]), float(day15_base["prompt_scale_gamma"]), "day-15 prompt-gamma scale")
    day15_removed_occ = removed_prompt_gamma_line_day15_hz * float(day15_base["prompt_scale_gamma"])
    require_close(float(occupancy_summary["prompt_gamma_misplaced_line_hz_removed"]), day15_removed_occ, "day-15 prompt-gamma line occupancy removal")
    require_close(float(occupancy_summary["prompt_hz_after_line_occupancy_dedup"]), float(day15_base["prompt_event_rate_hz"]) - day15_removed_occ, "day-15 prompt occupancy after line de-dup")
    require_close(float(occupancy_summary["delayed_hz_retained"]), float(day15_base["delayed_event_rate_hz"]), "day-15 retained delayed occupancy")
    require_close(float(occupancy_summary["legacy_sidecar_hz_removed"]), float(day15_base["atm511_event_rate_hz"]), "day-15 legacy sidecar occupancy")
    require(occupancy_summary["legacy_sidecar_subtracted_from_prompt_occupancy"] is False, "day-15 legacy sidecar was subtracted from prompt occupancy")
    require_close(float(occupancy_summary["corrected_line_hz_added"]), float(line["line_occupancy_day15_hz"]), "day-15 corrected line occupancy")
    require_close(float(occupancy_summary["old_live_factor"]), float(day15_base["accidental_live_factor"]), "day-15 old live factor")
    require_close(float(occupancy_summary["pre_fix_recomposition_live_factor_without_prompt_gamma_occupancy_dedup"]), float(day15_row["accidental_live_factor_pre_fix_no_prompt_gamma_occupancy_dedup"]), "day-15 pre-fix recomposition live factor")
    require_close(float(occupancy_summary["recomposed_live_factor"]), float(day15_row["accidental_live_factor_recomposed"]), "day-15 recomposed live factor")
    dedup_provenance = occupancy_summary["dedup_provenance"]
    require(dedup_provenance.get("status") == "PASS_PROMPT_GAMMA_LINE_TERM_OCCUPANCY_SCALE_SEMANTICS", "day-15 occupancy de-dup provenance is not PASS")
    require(int(dedup_provenance["affected_rows"]) == 317048 and int(dedup_provenance["tes_nonzero_rows"]) == 0 and int(dedup_provenance["active_volume_nonzero_rows"]) == 317048, "day-15 occupancy de-dup row provenance changed")
    require_close(float(dedup_provenance["removed_event_rate_day15_hz"]), removed_prompt_gamma_line_day15_hz, "day-15 occupancy de-dup authority rate")
    require(dedup_provenance["scale_field"] == "prompt_scale_gamma" and dedup_provenance["formula"] == expected_occupancy_formula and dedup_provenance["sidecar_subtracted_from_prompt"] is False, "day-15 occupancy de-dup semantics changed")
    occupancy_formula_audit = mission["recomposed_occupancy_formula_validation"]
    require(occupancy_summary["formula_validation"] == occupancy_formula_audit, "day-15 and mission occupancy formula audits differ")
    require(occupancy_formula_audit.get("status") == "PASS_81BIN_PROMPT_GAMMA_LINE_OCCUPANCY_DEDUP_FORMULA", "81-bin occupancy formula audit is not PASS")
    require(int(occupancy_formula_audit["checked_bins"]) == 81, "occupancy formula audit did not check all 81 bins")
    require(max(float(value) for value in occupancy_formula_audit["max_absolute_residuals"].values()) <= 5.0e-8, "occupancy formula audit residual is too large")
    require(occupancy_formula_audit["formula"] == expected_occupancy_formula, "occupancy formula audit text changed")
    require(occupancy_formula_audit["legacy_sidecar_occupancy_omitted_separately_once"] is True and occupancy_formula_audit["legacy_sidecar_subtracted_from_prompt_occupancy"] is False, "occupancy formula audit sidecar semantics changed")
    require(mission["prompt_gamma_line_occupancy_dedup_audit"] == dedup_provenance, "mission/day-15 occupancy de-dup provenance differs")
    require_close(float(day15["broad_window_corrected_line"]["rate_day15_cps"]), float(line["broad_rate_day15_cps"]), "day-15 broad line rate")
    require_close(float(day15["broad_window_corrected_line"]["upper95_day15_cps"]), float(line["broad_upper95_day15_cps"]), "day-15 broad line endpoint")

    metrics = mission["metrics_20d"]
    z20 = cumulative_source / math.sqrt(cumulative_background)
    z20_conditional = cumulative_source_lower / math.sqrt(cumulative_background_upper)
    reference_flux = float(config["mission"]["reference_flux_ph_cm2_s"])
    require_close(float(mission["reference_flux_ph_cm2_s"]), reference_flux, "mission reference flux")
    expected_metrics = {
        "source_counts": cumulative_source,
        "background_counts": cumulative_background,
        "source_transport_counting_lower_endpoint_counts": cumulative_source_lower,
        "background_componentwise_endpoint_counts": cumulative_background_upper,
        "Z20d": z20,
        "Z20d_componentwise_endpoint_conditional": z20_conditional,
        "flux_3sigma_20d_ph_cm2_s": reference_flux * 3.0 / z20,
        "flux_3sigma_20d_componentwise_endpoint_conditional_ph_cm2_s": reference_flux * 3.0 / z20_conditional,
        "T3_day": time_or_extrapolate(elapsed_days, z_curve, 3.0),
        "T5_day": time_or_extrapolate(elapsed_days, z_curve, 5.0),
        "T3_day_componentwise_endpoint_conditional": time_or_extrapolate(elapsed_days, z_conditional_curve, 3.0),
        "T5_day_componentwise_endpoint_conditional": time_or_extrapolate(elapsed_days, z_conditional_curve, 5.0),
        "accidental_loss_min": min(1.0 - value for value in live_factors),
        "accidental_loss_max": max(1.0 - value for value in live_factors),
    }
    require(set(metrics) == set(expected_metrics), "mission metrics set is incomplete or unexpected")
    for field, wanted in expected_metrics.items():
        require_close(float(metrics[field]), wanted, f"20d metric {field}", atol=5.0e-8)

    pre_fix_z = cumulative_source_pre_fix / math.sqrt(cumulative_background_pre_fix)
    pre_fix_z_conditional = cumulative_source_lower_pre_fix / math.sqrt(cumulative_background_upper_pre_fix)
    pre_fix_comparison = mission["comparison_to_pre_fix_recomposition_without_prompt_gamma_occupancy_dedup"]
    expected_pre_fix_comparison = {
        "pre_fix_source_counts_20d": cumulative_source_pre_fix,
        "pre_fix_background_counts_20d": cumulative_background_pre_fix,
        "pre_fix_source_lower_endpoint_counts_20d": cumulative_source_lower_pre_fix,
        "pre_fix_background_upper_endpoint_counts_20d": cumulative_background_upper_pre_fix,
        "pre_fix_Z20d": pre_fix_z,
        "pre_fix_Z20d_componentwise_endpoint_conditional": pre_fix_z_conditional,
        "corrected_minus_pre_fix_source_counts_20d": cumulative_source - cumulative_source_pre_fix,
        "corrected_minus_pre_fix_background_counts_20d": cumulative_background - cumulative_background_pre_fix,
        "corrected_minus_pre_fix_Z20d": z20 - pre_fix_z,
    }
    require(set(pre_fix_comparison) == set(expected_pre_fix_comparison), "pre-fix occupancy comparison set is incomplete or unexpected")
    for field, wanted in expected_pre_fix_comparison.items():
        require_close(float(pre_fix_comparison[field]), wanted, f"pre-fix occupancy comparison {field}", atol=5.0e-8)

    old_final = retained_mission_rows[-1]
    comparison = mission["comparison_to_retained_old_sidecar_fold"]
    expected_comparison = {
        "old_source_counts_20d": float(old_final["cumulative_source_counts"]),
        "old_background_counts_20d": float(old_final["cumulative_background_counts"]),
        "old_Z20d": float(old_final["counting_Z"]),
        "old_conditional_Z20d": float(old_final["counting_Z_componentwise_transport_counting_endpoint_conditional"]),
        "delta_source_counts_20d_from_live_factor_only": cumulative_source - float(old_final["cumulative_source_counts"]),
        "delta_background_counts_20d": cumulative_background - float(old_final["cumulative_background_counts"]),
        "delta_Z20d": z20 - float(old_final["counting_Z"]),
    }
    require(set(comparison) == set(expected_comparison), "old-sidecar comparison set is incomplete or unexpected")
    for field, wanted in expected_comparison.items():
        require_close(float(comparison[field]), wanted, f"old-sidecar comparison {field}", atol=5.0e-8)

    blocker_ids = {item["id"] for item in mission["scientific_blockers"]}
    require(REQUIRED_BLOCKERS <= blocker_ids, "required scientific blockers are missing from final recomposition")
    require("LINE_RESPONSE_INPUT_NOT_FINAL_RATE_GATE_AUTHORITY" not in blocker_ids, "final recomposition still contains the dynamic line-rate failure blocker")
    require(day15["scientific_blockers"] == mission["scientific_blockers"], "day-15 and mission blocker lists differ")

    ignored = [
        {
            "field": "recomposition_manifest.status",
            "value": manifest.get("status"),
            "authority": "INFORMATIONAL_CLAIM_GRADE_ONLY",
            "reason": "numeric validity is reconstructed from final-input gates, formulas, hashes, and invariants; publication blockers are reported separately",
        },
        {
            "field": "day15_modular_recomposition.status",
            "value": day15.get("status"),
            "authority": "INFORMATIONAL_CLAIM_GRADE_ONLY",
            "reason": "not used as a substitute for the dynamic line gate or formula audit",
        },
        {
            "field": "mission_20d_modular_recomposition.status",
            "value": mission.get("status"),
            "authority": "INFORMATIONAL_CLAIM_GRADE_ONLY",
            "reason": "not used as a substitute for the dynamic line gate or formula audit",
        },
    ]
    for key, path in paths.items():
        registry.verify(path, label=f"recomposition post-read stability:{key}")
    registry.verify(config_path, label="recomposition config post-read stability")
    registry.verify(expected_builder_path, label="recomposition builder post-read stability")
    return {
        "directory": directory.as_posix(),
        "manifest_path": paths["manifest"].as_posix(),
        "manifest_sha256": sha256(paths["manifest"]),
        "day15": day15,
        "mission": mission,
        "line_input": line,
        "max_formula_absolute_residual": max_residual,
        "scientific_blockers": mission["scientific_blockers"],
        "ignored_status_fields": ignored,
    }


def make_summary(
    registry: EvidenceRegistry,
    source: dict[str, Any],
    protected: dict[str, Any],
    campaign: dict[str, Any],
    recomposition: dict[str, Any],
    cleanup: dict[str, Any],
) -> dict[str, Any]:
    gate = campaign["gate"]
    line = recomposition["line_input"]
    rates = recomposition["day15"]["retained_and_replaced_rates_cps"]
    metrics = recomposition["mission"]["metrics_20d"]
    ignored = campaign["ignored_status_fields"] + recomposition["ignored_status_fields"]
    source_summary = {key: value for key, value in source.items() if key not in {"grid_paths", "grids"}}
    source_summary["line_grid_authorities"] = {
        str(bins): {
            "path": path.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "rows": bins,
        }
        for bins, path in source["grid_paths"].items()
    }
    return {
        "schema": "wp2-parma511-offline-final-summary-v1",
        "status": "PASS_PARMA511_MONO_LINE_MODULE_AND_OFFLINE_RECOMPOSITION__SCIENTIFIC_BLOCKERS_REMAIN",
        "overall_assessment": "SHARE_WITH_CAVEATS__NOT_PUBLICATION_AUTHORITY",
        "generated_at_utc": now_utc(),
        "scope": {
            "changed_physical_component": "atmospheric annihilation mono gamma at 510.99895 keV only",
            "all_other_modules": "retained and recomposed offline",
            "continuum_rerun": False,
            "prompt_rerun": False,
            "delayed_or_activation_rerun": False,
            "signal_rerun": False,
            "other_particle_rerun": False,
            "m_sampling_rerun": False,
            "finalizer_launched_transport": False,
        },
        "source_and_protected_authority": {
            "parma_source": source_summary,
            "protected_m04_and_o8": protected,
        },
        "single_campaign_line_response": {
            "campaign_id": campaign["campaign_id"],
            "aggregate_receipt": campaign["receipt_path"].as_posix(),
            "aggregate_receipt_sha256": campaign["receipt_sha256"],
            "response_summary": campaign["response_path"].as_posix(),
            "response_summary_sha256": sha256(campaign["response_path"]),
            "batches": campaign["transport"]["batches"],
            "TS": campaign["transport"]["TS"],
            "TE_s": campaign["transport"]["TE_s"],
            "unique_transport_seeds": campaign["transport"]["unique_transport_seeds"],
            "selected_events_80bin": int(gate["selected_events_80bin"]),
            "rate_80bin_cps": float(line["w2_rate_day15_cps"]),
            "mc_sigma_80bin_cps": float(line["w2_mc_sigma_day15_cps"]),
            "relative_standard_error_80bin": float(gate["relative_standard_error_80bin"]),
            "importance_effective_sample_size_80bin": float(gate["importance_effective_sample_size_80bin"]),
            "combined_relative_40_vs_80_error": float(gate["combined_relative_40_vs_80_error"]),
            "dynamic_gate": gate,
            "independent_primary_csv_weight_reconstruction": campaign["independent_weighted_response"],
            "response_replica_validation": campaign["response_replica_validation"],
        },
        "offline_modular_recomposition": {
            "directory": recomposition["directory"],
            "manifest": recomposition["manifest_path"],
            "manifest_sha256": recomposition["manifest_sha256"],
            "formula": recomposition["day15"]["composition"]["formula"],
            "occupancy_formula": recomposition["day15"]["composition"]["occupancy_formula"],
            "max_independent_formula_absolute_residual": recomposition["max_formula_absolute_residual"],
            "day15_rates_cps": rates,
            "day15_occupancy_and_live_factor": recomposition["day15"]["occupancy_and_live_factor"],
            "metrics_20d": metrics,
        },
        "cleanup": cleanup,
        "informational_status_fields_ignored_or_downgraded": ignored,
        "scientific_blockers": recomposition["scientific_blockers"],
        "claim_boundary": (
            "The corrected PARMA mono-line module passes its completed single-campaign detector-rate gate and the offline replacement arithmetic closes. "
            "The recomposed total background and mission metrics remain conditional and are not publication authority because the retained prompt-gamma energy-axis and frozen passive-Kapton veto-predicate blockers remain; the day-15 angular response is also held fixed across the mission fold."
        ),
        "validated_input_file_count": len(registry.records()),
    }


def conclusion_markdown(summary: dict[str, Any]) -> str:
    line = summary["single_campaign_line_response"]
    recomposed = summary["offline_modular_recomposition"]
    rates = recomposed["day15_rates_cps"]
    occupancy = recomposed["day15_occupancy_and_live_factor"]
    metrics = recomposed["metrics_20d"]
    blocker_lines = "\n".join(
        f"- `{item['id']}` ({item['severity']}): {item['statement']}" for item in summary["scientific_blockers"]
    )
    ignored_lines = "\n".join(
        f"- `{item['field']}` = `{item['value']}`：仅作信息记录；{item['reason']}。" for item in summary["informational_status_fields_ignored_or_downgraded"]
    )
    return f"""# PARMA atmospheric-511 WP2 conclusion

状态：`{summary['status']}`  
总体证据等级：`{summary['overall_assessment']}`

## 结论

PARMA 给出的大气湮没线已作为唯一被替换的物理模块处理：单能 gamma 为 510.99895 keV，day-15 全立体角通量为 {summary['source_and_protected_authority']['parma_source']['line_flux_ph_cm2_s']:.15g} ph cm^-2 s^-1。其余 prompt、delayed/activation、signal、continuum 和其他粒子模块均沿用 retained 产品并只做离线重组；本最终化步骤没有模拟或 transport 执行接口。

完整单 campaign 由 {line['batches']} 个批次组成，TS={line['TS']:,}，TE={line['TE_s']:.6f} s，transport seeds={line['unique_transport_seeds']}。80-bin 主响应选后 {line['selected_events_80bin']} 个事件，day-15 率为 {line['rate_80bin_cps']:.12g} cps，RSE={100.0 * line['relative_standard_error_80bin']:.3f}%，40/80 同事件组合相对差为 {100.0 * line['combined_relative_40_vs_80_error']:.3f}%。动态 detector-rate gate 通过。

离线重组严格复核公式：

`{recomposed['formula']}`

day-15 retained prompt={rates['prompt_retained']:.12g} cps，retained delayed={rates['delayed_retained']:.12g} cps，移除旧 sidecar={rates['legacy_atm511_sidecar_removed']:.12g} cps，加入修正 PARMA line={rates['corrected_PARMA511_added']:.12g} cps，重组本底={rates['recomposed_background']:.12g} cps。20 d 条件式折叠得到 source counts={metrics['source_counts']:.6f}、background counts={metrics['background_counts']:.6f}、Z={metrics['Z20d']:.6f}。这些总本底和任务指标仍是条件式结果，不是论文发表权威。

偶然符合 occupancy 也只做离线去重：`{recomposed['occupancy_formula']}`。day-15 从 retained prompt occupancy 中按 `prompt_scale_gamma` 移除 {occupancy['prompt_gamma_misplaced_line_hz_removed']:.12g} Hz 的错误展宽线项，再加入修正 line occupancy；legacy sidecar occupancy 独立省略一次，未从 prompt 重复扣除。该修正没有重新运行任何粒子或输运。

外部 raw 清理凭据覆盖 60/60 个新 campaign raw 路径；这些 raw 已不存在，不能本地恢复。其精确路径、原大小、SHA-256、source cards、seeds、compact catalogs、response 输出与分批清理凭据仍保留可审计链路。

## 仍然存在的科学 blocker

{blocker_lines}

## 顶层状态字符串的处理

以下 producer 顶层字符串或计数可能硬编码为 diagnostic/prepared，本工具没有用它们替代动态数值门槛：

{ignored_lines}

## 声明边界

修正后的 PARMA 单线模块及其离线替换算术通过。本结论不授权、也不建议重跑 continuum、prompt、delayed/activation、signal、其他粒子或全链；现有科学 blocker 未解决前，不得把重组后的总本底和任务指标直接写成 publication authority。
"""


def write_final_outputs(output_dir: Path, summary: dict[str, Any], registry: EvidenceRegistry) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    require_under(output_dir, PACKAGE, "WP2 final output directory")
    require(not os.path.lexists(output_dir), f"output directory must be new and absent: {output_dir}")
    require(output_dir.parent.is_dir(), f"output parent must already exist: {output_dir.parent}")
    stage = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp.", dir=output_dir.parent))
    names = ("PARMA_ATM511_CONCLUSION.md", "wp2_final_summary.json", "wp2_output_manifest.json")
    try:
        conclusion_stage = stage / names[0]
        summary_stage = stage / names[1]
        manifest_stage = stage / names[2]
        atomic_write(conclusion_stage, conclusion_markdown(summary))
        atomic_write(summary_stage, json_text(summary))
        output_records = [
            {
                "path": (output_dir / path.name).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in (conclusion_stage, summary_stage)
        ]
        manifest = {
            "schema": "wp2-parma511-full-path-sha256-manifest-v1",
            "status": "PASS_OUTPUT_HASH_MANIFEST_COMPLETE",
            "generated_at_utc": now_utc(),
            "generator": {
                "path": Path(__file__).resolve().as_posix(),
                "bytes": Path(__file__).stat().st_size,
                "sha256": sha256(Path(__file__)),
            },
            "outputs": output_records,
            "validated_inputs": registry.records(),
            "commit_protocol": "three files built and rehashed in a same-parent temporary sibling, then directory-atomically committed with os.replace",
            "manifest_self_record": "Intentionally omitted: a file cannot contain a stable cryptographic hash of itself. The finalizer rehashes this manifest before and after the directory commit and returns its detached record.",
        }
        atomic_write(manifest_stage, json_text(manifest))
        require({path.name for path in stage.iterdir()} == set(names), "staging directory does not contain exactly the three WP2 outputs")
        require(read_json(summary_stage) == summary, "staged final summary failed full JSON reread")
        require(read_json(manifest_stage) == manifest, "staged output manifest failed full JSON reread")
        staged_records: list[dict[str, Any]] = []
        for name in names:
            path = stage / name
            first = {"path": (output_dir / name).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
            require(first["bytes"] == path.stat().st_size and first["sha256"] == sha256(path), f"staged output changed during hash verification: {name}")
            staged_records.append(first)
        directory_fd = os.open(stage, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        require(not os.path.lexists(output_dir), f"output target appeared during staging: {output_dir}")
        os.replace(stage, output_dir)
        committed_records: list[dict[str, Any]] = []
        for staged in staged_records:
            path = Path(staged["path"])
            committed = {"path": path.as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
            require(committed == staged, f"committed output hash/size differs from staged file: {path.name}")
            committed_records.append(committed)
        require({path.name for path in output_dir.iterdir()} == set(names), "committed output directory does not contain exactly three files")
        parent_fd = os.open(output_dir.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
        return {
            "status": summary["status"],
            "output_dir": output_dir.as_posix(),
            "commit": "ATOMIC_SAME_PARENT_DIRECTORY_OS_REPLACE",
            "outputs": committed_records,
        }
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def run_expected_rejection_self_test(receipt_path: Path) -> dict[str, Any]:
    registry = EvidenceRegistry()
    protected = validate_protected_files(registry)
    source = validate_source_authority(registry)
    campaign = validate_campaign_aggregate(
        registry,
        receipt_path,
        source,
        require_complete=False,
    )
    path = campaign["receipt_path"]
    receipt = campaign["receipt"]
    require(campaign["included_batch_indices"] == list(range(45)), "self-test requires the exact 45-batch compact aggregate (0..44)")
    require(receipt.get("incomplete_batch_indices") == list(range(45, 60)), "self-test receipt is not the exact 45/60 partial state")
    rejection: str | None = None
    try:
        validate_completion_header(receipt)
    except ValidationError as exc:
        rejection = str(exc)
    require(rejection is not None, "self-test failed: supplied receipt was accepted as complete")
    expected_partial_evidence = (
        receipt.get("allow_partial") is True
        or receipt.get("included_batch_indices") != EXPECTED_BATCHES
        or bool(receipt.get("incomplete_batch_indices"))
        or len(receipt.get("batch_receipts", [])) != 60
    )
    require(expected_partial_evidence, "self-test rejection was not caused by partial/incomplete campaign evidence")
    return {
        "schema": "wp2-parma511-finalizer-self-test-v1",
        "status": "PASS_EXPECTED_REJECTION_OF_PARTIAL_AGGREGATE",
        "tested_at_utc": now_utc(),
        "input": {"path": path.as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)},
        "observed": {
            "allow_partial": receipt.get("allow_partial"),
            "included_batch_count": len(receipt.get("included_batch_indices", [])),
            "incomplete_batch_count": len(receipt.get("incomplete_batch_indices", [])),
            "batch_receipt_count": len(receipt.get("batch_receipts", [])),
            "deep_offline_compact_validation": "PASS_45_OF_45_BATCHES_PRIMARY_AND_64SEED_RESPONSE",
            "dynamic_gate": campaign["gate"],
            "primary_csv_selected": campaign["primary_csv_selected"],
            "replica_rows_validated": campaign["response_replica_validation"]["rows"],
            "protected_status": protected["status"],
            "vendor_runtime_dependency_count": source["vendor_runtime_dependency_manifest"]["dependency_count"],
            "validated_input_file_count": len(registry.records()),
        },
        "rejection": rejection,
        "execution_surface": {
            "subprocess_module_used": False,
            "simulation_or_transport_callable_present": False,
            "raw_files_opened": False,
            "compact_and_response_files_read": True,
            "retained_files_modified": False,
            "self_test_outputs_restricted_to_tmp": True,
        },
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--aggregate-receipt", type=Path, required=True, help="complete single-campaign aggregate receipt (partial receipt in --self-test mode)")
    value.add_argument("--recomposition-dir", type=Path, help="already-produced final offline recomposition output directory")
    value.add_argument("--cleanup-receipt", type=Path, action="append", default=[], help="external raw-cleanup receipt; repeat for every wave")
    value.add_argument("--output-dir", type=Path, help="new absent directory for the three WP2 finalization outputs")
    value.add_argument("--self-test", action="store_true", help="expect and verify rejection of a partial aggregate; no final outputs")
    value.add_argument("--self-test-output", type=Path, help="optional self-test JSON; must be under /tmp")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.self_test:
            require(args.recomposition_dir is None and not args.cleanup_receipt and args.output_dir is None, "--self-test accepts only --aggregate-receipt and optional --self-test-output")
            report = run_expected_rejection_self_test(args.aggregate_receipt.resolve())
            if args.self_test_output is not None:
                target = args.self_test_output.resolve()
                require_under(target, Path("/tmp"), "self-test output")
                require(not os.path.lexists(target), f"refusing to overwrite self-test output: {target}")
                atomic_write(target, json_text(report))
            print(json_text(report), end="")
            return 0

        require(args.recomposition_dir is not None, "--recomposition-dir is required")
        require(args.cleanup_receipt, "at least one --cleanup-receipt is required")
        require(args.output_dir is not None, "--output-dir is required")
        registry = EvidenceRegistry()
        protected = validate_protected_files(registry)
        source = validate_source_authority(registry)
        campaign = validate_campaign_aggregate(registry, args.aggregate_receipt.resolve(), source, require_complete=True)
        recomposition = validate_recomposition(registry, args.recomposition_dir.resolve(), campaign)
        cleanup = validate_cleanup_receipts(registry, [path.resolve() for path in args.cleanup_receipt], campaign)
        summary = make_summary(registry, source, protected, campaign, recomposition, cleanup)
        result = write_final_outputs(args.output_dir, summary, registry)
        print(json_text(result), end="")
        return 0
    except ValidationError as exc:
        print(json.dumps({"status": "REJECTED", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except (KeyError, TypeError, ValueError, OSError) as exc:
        print(
            json.dumps(
                {
                    "status": "REJECTED",
                    "error": f"malformed or incomplete evidence schema: {type(exc).__name__}: {exc}",
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
