#!/usr/bin/env python3
"""Validate the public EN/ZH paper story against the retained all-eight-family authorities."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parents[1]
ASSETS = PAPER / "paper_source_figure_table"
EN = PAPER / "balloon511_ea_draft_en.tex"
ZH = PAPER / "balloon511_ea_draft_zh.tex"
PROVENANCE = ASSETS / "background_optimization_story_provenance_20260713.json"

ACTIVATION = ROOT / (
    "engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/"
    "data/s3d_o8_all8_activation_campaign.json"
)
COMPONENTS = ROOT / (
    "engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/"
    "data/s3d_o8_all8_delayed_components.json"
)
STEP05 = ROOT / (
    "engineering/geometry_optimization_20260704/44_s3d_o8_all8_activation_20260713/"
    "fullchain/step05/step05_s3d_o8_all8_activation_l1_response_summary.json"
)
RESPONSE = ROOT / (
    "engineering/ea_s3d_o8_all8_detector_response_closure_20260713/"
    "data/s3d_o8_all8_energy_response_summary.json"
)
RESPONSE_VALIDATION = ROOT / (
    "engineering/ea_s3d_o8_all8_detector_response_closure_20260713/"
    "data/s3d_o8_all8_energy_response_validation.json"
)
MISSION = ROOT / (
    "engineering/ea_s3d_o8_all8_family_nuclide_mission_fold_20260713/"
    "data/s3d_o8_all8_family_nuclide_mission_summary.json"
)
MISSION_VALIDATION = ROOT / (
    "engineering/ea_s3d_o8_all8_family_nuclide_mission_fold_20260713/"
    "data/s3d_o8_all8_family_nuclide_mission_validation.json"
)
SLANT45_ROOT = ROOT / "engineering/ea_peer_review_p02_slant_transmission_20260714"
SLANT45_MISSION = SLANT45_ROOT / "data/slant45_signal_refold_summary.json"
SLANT45_VALIDATION = SLANT45_ROOT / "data/slant45_signal_refold_validation.json"
SLANT45_TIMELINE = SLANT45_ROOT / "outputs/w2_all8_family_nuclide_mission_timeline_slant45.csv"
REFERENCE_BREAKDOWN = ROOT / (
    "engineering/ea_detector_response_closure_20260713/"
    "data/reference_response_background_breakdown.json"
)
OUT = PAPER / "s3d_story_sync_validation_20260713.json"

FIGURES = (
    "fig_reference_detector_cryostat_geometry.png",
    "fig_background_origin_story.png",
    "fig_optimized_shield_background.png",
    "fig_optimized_mission_significance.png",
)
FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
POSITIVE_FAMILIES = ("alpha", "eplus", "gamma", "muminus", "muplus", "n", "p")
ZERO_FAMILY = "eminus"
W2 = "w2_510p58_511p42"

EXPECTED_STATUSES = {
    "activation": "PASS_S3D_O8_ALL8_ACTIVATION_AND_FAMILY_DELAYED_TRANSPORT",
    "components": "PASS_S3D_O8_ALL8_STEP05_DELAYED_COMPONENTS",
    "step05": "PASS_S3D_O8_ALL8_ACTIVATION_STEP05_DAY15",
    "response": "PASS_S3D_O8_ALL8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE",
    "response_validation": "PASS_S3D_O8_ALL8_ENERGY_RESPONSE_VALIDATION",
    "mission": "PASS_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_CLOSURE",
    "mission_validation": "PASS_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_VALIDATION",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def english_abstract_word_count(text: str) -> int:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", text, re.DOTALL)
    if not match:
        match = re.search(
            r"\\textbf\{Abstract\}\\hspace\{[^}]+\}(.*?)\\vspace\{0\.7em\}",
            text,
            re.DOTALL,
        )
    if not match:
        return -1
    abstract = re.sub(r"\\cite\{[^}]+\}", " ", match.group(1))
    abstract = re.sub(r"\\[A-Za-z]+", " ", abstract)
    abstract = abstract.replace("--", "-")
    return len(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", abstract))


def add_close(
    problems: list[str],
    actual: float,
    expected: float,
    label: str,
    *,
    atol: float = 1.0e-15,
    rtol: float = 1.0e-12,
) -> None:
    if not math.isclose(float(actual), float(expected), rel_tol=rtol, abs_tol=atol):
        problems.append(f"{label}: actual={actual!r}, expected={expected!r}")


def latex_sci(value: float, decimals: int = 5) -> str:
    """Return the manuscript's normalized LaTeX scientific-notation token."""
    value = float(value)
    if value == 0.0 or not math.isfinite(value):
        raise ValueError(f"latex_sci requires a finite nonzero value, got {value!r}")
    exponent = math.floor(math.log10(abs(value)))
    mantissa = value / (10.0**exponent)
    return rf"{mantissa:.{decimals}f}\times10^{{{exponent}}}"


def check_authority_hash(
    problems: list[str],
    owner: dict[str, Any],
    key: str,
    path: Path,
    label: str,
) -> None:
    expected_path = rel(path)
    if owner.get(key) != expected_path:
        problems.append(f"{label} path={owner.get(key)!r}, expected {expected_path!r}")
    if owner.get(f"{key}_sha256") != sha256(path):
        problems.append(f"{label} hash does not bind the current artifact")


def check_family_contracts(
    problems: list[str],
    activation: dict[str, Any],
    components: dict[str, Any],
    step05: dict[str, Any],
    response: dict[str, Any],
    mission_summary: dict[str, Any],
) -> dict[str, Any]:
    expected = set(FAMILIES)
    positive = set(POSITIVE_FAMILIES)
    campaign_rows = {row["family"]: row for row in activation["families"]}
    component_rows = {row["family"]: row for row in components["components"]}
    step05_rows = {
        row["family"]: row for row in step05["normalization"]["delayed_components"]
    }
    response_metrics = response["response_seed_ensemble"]["delayed_family_metrics"]
    response_delayed = response["primary_authority"]["step05"]["windows"][W2][
        "physical_reference_flux"
    ]["uncertainty_95"]["delayed_components_by_incident_family"]
    mission_rates = mission_summary["mission"]["day15_selected_rates_cps"][
        "delayed_by_incident_family"
    ]

    family_sets = {
        "activation": set(campaign_rows),
        "components": set(component_rows),
        "step05": set(step05_rows),
        "response": set(response_metrics),
        "response_physical": set(response_delayed),
        "mission": set(mission_rates),
    }
    for label, family_set in family_sets.items():
        if family_set != expected:
            problems.append(
                f"{label} family set={sorted(family_set)!r}, expected {list(FAMILIES)!r}"
            )
    if components.get("family_order") != list(FAMILIES):
        problems.append("delayed-component authority family order is not the exact eight-family order")
    if set(components.get("positive_families", [])) != positive:
        problems.append("delayed-component authority does not identify exactly seven positive families")
    if components.get("audited_zero_families") != [ZERO_FAMILY]:
        problems.append("delayed-component authority does not identify eminus as the sole audited zero family")

    total_activity = 0.0
    for family in FAMILIES:
        campaign = campaign_rows[family]
        component = component_rows[family]
        step_component = step05_rows[family]
        production = component["production"]
        add_close(
            problems,
            float(component["activity_Bq"]),
            float(campaign["activity_Bq"]),
            f"{family} campaign/component activity closure",
        )
        add_close(
            problems,
            float(step_component["activity_Bq"]),
            float(component["activity_Bq"]),
            f"{family} component/Step05 activity closure",
        )
        if int(production["files"]) != int(production["tt_lines"]):
            problems.append(f"{family} buildup file count does not equal TT line count")
        if not math.isclose(
            float(production["division"]), float(production["files"]), rel_tol=0.0, abs_tol=0.0
        ):
            problems.append(f"{family} buildup family-division guard is not files==division")

        if family in positive:
            total_activity += float(component["activity_Bq"])
            if campaign.get("status") != "PASS" or component.get("status") != "PASS":
                problems.append(f"{family} is not a PASS positive activation family")
            if bool(production.get("zero_production")) or float(component["activity_Bq"]) <= 0.0:
                problems.append(f"{family} lacks positive production/activity")
            te_s = component.get("TE_s")
            weight = component.get("event_weight_hz")
            if te_s is None or weight is None or float(te_s) <= 0.0 or float(weight) <= 0.0:
                problems.append(f"{family} lacks a positive delayed TE and 1/TE event weight")
            else:
                add_close(
                    problems,
                    float(weight),
                    1.0 / float(te_s),
                    f"{family} delayed 1/TE normalization",
                    atol=1.0e-20,
                )
            if response_metrics[family].get("component_status") != "PASS":
                problems.append(f"{family} response ensemble does not retain positive-family status")
        else:
            if campaign.get("status") != "PASS_ZERO_PRODUCTION":
                problems.append("eminus campaign status is not PASS_ZERO_PRODUCTION")
            if component.get("status") != "PASS_ZERO_PRODUCTION":
                problems.append("eminus component status is not PASS_ZERO_PRODUCTION")
            if not bool(production.get("zero_production")):
                problems.append("eminus production row is not marked as a finite-buildup zero observation")
            if float(component.get("activity_Bq", math.nan)) != 0.0:
                problems.append("eminus finite-buildup activity is not exactly zero")
            if any(component.get(key) is not None for key in ("sim", "TE_s", "event_weight_hz")):
                problems.append("eminus incorrectly has a delayed SIM, TE, or event weight")
            if int(component.get("SE", -1)) != 0 or int(component.get("ID", -1)) != 0:
                problems.append("eminus zero-family component has nonzero transported event counts")
            if campaign.get("transport"):
                problems.append("eminus campaign row incorrectly has delayed transport provenance")
            metric = response_metrics[family]
            if metric.get("status") != "PASS_FINITE_BUILDUP_ZERO_NO_TRANSPORT_RESPONSE_REPLICAS":
                problems.append("eminus response branch is not finite-buildup-zero/no-transport")
            if metric.get("event_weight_cps") is not None or not metric.get("all_replicas_exact_zero"):
                problems.append("eminus response branch invents an exposure or a nonzero replica")
            physical = response_delayed[family]
            if any(
                physical.get(key) is not None
                for key in ("event_weight_cps", "rate_interval95_cps", "rate_upper95_cps")
            ):
                problems.append("eminus response endpoint invents a TE-derived interval")
            if float(mission_rates[family]) != 0.0:
                problems.append("eminus mission delayed rate is not exactly zero")

        add_close(
            problems,
            float(mission_rates[family]),
            float(response_delayed[family]["rate_cps"]),
            f"{family} response/mission selected delayed-rate closure",
        )

    add_close(
        problems,
        total_activity,
        float(activation["total_fixed_day15_activity_Bq"]),
        "seven-positive-family activation total",
        atol=1.0e-12,
    )
    return {
        "families": list(FAMILIES),
        "positive_families": list(POSITIVE_FAMILIES),
        "audited_zero_families": [ZERO_FAMILY],
        "positive_family_count": len(POSITIVE_FAMILIES),
        "total_fixed_day15_activity_Bq": total_activity,
        "eminus_no_transport_exposure": not any(
            component_rows[ZERO_FAMILY].get(key) is not None
            for key in ("sim", "TE_s", "event_weight_hz")
        ),
    }


def paper_endpoint_semantics(language: str, text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text)
    patterns = {
        "en": {
            "conditional endpoint": r"conditional.{0,120}component(?:[- ]?wise).{0,80}transport[- ]counting endpoint|component(?:[- ]?wise).{0,80}transport[- ]counting endpoint.{0,120}conditional",
            "not full 95-percent coverage": r"(?:not (?:a )?(?:full|joint)|does not (?:represent|have)).{0,40}(?:95\\?%|95-percent).{0,30}(?:coverage|interval)",
            "finite-buildup zero observation": r"finite[- ]buildup zero observation",
            "no fictitious transport exposure": r"no fictitious transport exposure",
        },
        "zh": {
            "conditional endpoint": r"条件.{0,80}(?:逐分量|分量逐项).{0,50}输运计数端点|(?:逐分量|分量逐项).{0,50}输运计数端点.{0,80}条件",
            "not full 95-percent coverage": r"(?:不是|不构成).{0,30}完整.{0,20}95\\?%.{0,20}覆盖",
            "finite-buildup zero observation": r"有限(?:累积|积累|\s*BUILDUP\s*)零观测",
            "no fictitious transport exposure": r"不.{0,12}虚构.{0,12}输运曝光",
        },
    }
    return [
        label
        for label, pattern in patterns[language].items()
        if not re.search(pattern, compact, re.IGNORECASE)
    ]


def main() -> int:
    authority_paths = {
        "activation": ACTIVATION,
        "components": COMPONENTS,
        "step05": STEP05,
        "response": RESPONSE,
        "response_validation": RESPONSE_VALIDATION,
        "mission": MISSION,
        "mission_validation": MISSION_VALIDATION,
    }
    required = [
        EN,
        ZH,
        EN.with_suffix(".pdf"),
        ZH.with_suffix(".pdf"),
        EN.with_suffix(".log"),
        ZH.with_suffix(".log"),
        PROVENANCE,
        SLANT45_MISSION,
        SLANT45_VALIDATION,
        SLANT45_TIMELINE,
        *authority_paths.values(),
        REFERENCE_BREAKDOWN,
        *(ASSETS / name for name in FIGURES),
    ]
    problems = [f"missing {rel(path)}" for path in required if not path.is_file()]
    if problems:
        raise SystemExit("; ".join(problems))

    en = EN.read_text(encoding="utf-8")
    zh = ZH.read_text(encoding="utf-8")
    provenance = load_json(PROVENANCE)
    authorities = {name: load_json(path) for name, path in authority_paths.items()}
    activation = authorities["activation"]
    components = authorities["components"]
    step05 = authorities["step05"]
    response = authorities["response"]
    response_validation = authorities["response_validation"]
    mission_summary = authorities["mission"]
    mission_validation = authorities["mission_validation"]
    slant45_summary = load_json(SLANT45_MISSION)
    slant45_validation = load_json(SLANT45_VALIDATION)
    reference_breakdown = load_json(REFERENCE_BREAKDOWN)

    if provenance.get("status") != "SOURCE_BACKED_FIGURES_GENERATED":
        problems.append(f"figure provenance status={provenance.get('status')!r}")
    for label, expected_status in EXPECTED_STATUSES.items():
        if authorities[label].get("status") != expected_status:
            problems.append(
                f"{label} authority status={authorities[label].get('status')!r}, "
                f"expected {expected_status!r}"
            )
    if reference_breakdown.get("status") != "PASS_REFERENCE_RESPONSE_BACKGROUND_BREAKDOWN":
        problems.append(f"reference-response authority status={reference_breakdown.get('status')!r}")
    if (
        slant45_summary.get("status")
        != "PASS_EA_P02_FIXED_45DEG_SLANT_SIGNAL_REFOLD"
        or slant45_summary.get("problems")
    ):
        problems.append(
            f"slant45 authority status/problems={slant45_summary.get('status')!r}/"
            f"{slant45_summary.get('problems')!r}"
        )
    if (
        slant45_validation.get("status")
        != "PASS_EA_P02_FIXED_45DEG_SLANT_SIGNAL_REFOLD_VALIDATION"
        or slant45_validation.get("problems")
    ):
        problems.append(
            f"slant45 validation status/problems={slant45_validation.get('status')!r}/"
            f"{slant45_validation.get('problems')!r}"
        )
    if slant45_validation.get("summary_sha256") != sha256(SLANT45_MISSION):
        problems.append("slant45 validation does not bind the current summary")
    if slant45_validation.get("timeline_sha256") != sha256(SLANT45_TIMELINE):
        problems.append("slant45 validation does not bind the current timeline")
    slant45_inputs = slant45_summary.get("input_authorities") or {}
    if slant45_inputs.get("retained_mission_summary_sha256") != sha256(MISSION):
        problems.append("slant45 summary does not bind the retained mission summary")

    response_inputs = response["input_authorities"]
    for key, path in (("campaign", ACTIVATION), ("components", COMPONENTS), ("step05", STEP05)):
        check_authority_hash(problems, response_inputs, key, path, f"response/{key}")
    check_authority_hash(
        problems, response_validation, "summary", RESPONSE, "response-validation/summary"
    )
    check_authority_hash(
        problems, response_validation, "components", COMPONENTS, "response-validation/components"
    )
    if int(response_validation.get("replica_rows", -1)) != int(
        response["response_seed_ensemble"]["replicas"]
    ):
        problems.append("response validation replica count does not match response authority")

    mission_inputs = mission_summary["input_authorities"]
    for key, path in (
        ("campaign", ACTIVATION),
        ("components", COMPONENTS),
        ("step05", STEP05),
        ("response", RESPONSE),
        ("response_validation", RESPONSE_VALIDATION),
    ):
        check_authority_hash(problems, mission_inputs, key, path, f"mission/{key}")
    check_authority_hash(
        problems, mission_validation, "summary", MISSION, "mission-validation/summary"
    )
    if int(mission_validation.get("families_rechecked", -1)) != len(FAMILIES):
        problems.append("mission validation did not independently recheck all eight families")
    if not mission_validation.get("activity_key_set_complete"):
        problems.append("mission validation activity key set is incomplete")

    family_contract = check_family_contracts(
        problems, activation, components, step05, response, mission_summary
    )

    w2 = response["primary_authority"]["step05"]["windows"][W2]
    streams = w2["by_stream"]
    physical = w2["physical_reference_flux"]
    retained_mission = mission_summary["mission"]
    mission = slant45_summary["mission"]
    ensemble = response["response_seed_ensemble"]
    component_rates = {
        "prompt": float(streams["prompt"]["side_compton_fov_pass_rate_cps"]),
        "delayed": float(streams["delayed"]["side_compton_fov_pass_rate_cps"]),
        "atm511": float(streams["atm511_sidecar"]["side_compton_fov_pass_rate_cps"]),
    }
    recomputed_background = sum(component_rates.values())
    authority_background = float(physical["background_cps"])
    add_close(
        problems,
        recomputed_background,
        authority_background,
        "response-convolved background component sum",
    )
    final_background_records = sum(
        int(streams[name]["side_compton_fov_pass_events"])
        for name in ("prompt", "delayed", "atm511_sidecar")
    )
    selected_delayed_events = int(mission_summary["selected_delayed_lineage"]["selected_events"])
    if int(streams["delayed"]["side_compton_fov_pass_events"]) != selected_delayed_events:
        problems.append("response delayed record count differs from mission selected lineage")
    if int(mission_validation.get("selected_events_rechecked", -1)) != selected_delayed_events:
        problems.append("mission validation selected-event count differs from mission authority")

    component_shares = {
        name: 100.0 * rate / authority_background for name, rate in component_rates.items()
    }
    add_close(
        problems,
        sum(component_shares.values()),
        100.0,
        "response-convolved component-share sum",
        atol=1.0e-12,
        rtol=0.0,
    )
    mission_rates = retained_mission["day15_selected_rates_cps"]
    for key, expected in (
        ("prompt", component_rates["prompt"]),
        ("delayed", component_rates["delayed"]),
        ("atm511", component_rates["atm511"]),
        ("background", authority_background),
        ("signal", float(physical["signal_cps_at_reference_flux"])),
    ):
        add_close(problems, float(mission_rates[key]), expected, f"response/mission day-15 {key}")
    add_close(
        problems,
        sum(float(value) for value in mission_rates["delayed_by_incident_family"].values()),
        float(mission_rates["delayed"]),
        "mission delayed incident-family sum",
    )

    recomputed_z20 = float(mission["source_counts_20d"]) / math.sqrt(
        float(mission["background_counts_20d"])
    )
    add_close(problems, recomputed_z20, float(mission["Z20d"]), "mission central Z20", atol=1e-12)
    recomputed_conditional_z20 = float(
        mission["source_transport_counting_lower_endpoint_counts_20d"]
    ) / math.sqrt(float(mission["background_componentwise_transport_counting_upper_endpoint_counts_20d"]))
    add_close(
        problems,
        recomputed_conditional_z20,
        float(mission["Z20d_componentwise_transport_counting_endpoint_conditional"]),
        "mission conditional componentwise-transport-counting Z20",
        atol=1e-12,
    )
    recomputed_f3 = float(mission["reference_flux_ph_cm2_s"]) * 3.0 / recomputed_z20
    add_close(
        problems,
        recomputed_f3,
        float(mission["flux_3sigma_20d_ph_cm2_s"]),
        "mission central F3",
    )
    recomputed_conditional_f3 = (
        float(mission["reference_flux_ph_cm2_s"]) * 3.0 / recomputed_conditional_z20
    )
    add_close(
        problems,
        recomputed_conditional_f3,
        float(
            mission[
                "flux_3sigma_20d_componentwise_transport_counting_endpoint_conditional_ph_cm2_s"
            ]
        ),
        "mission conditional componentwise-transport-counting F3",
    )
    if ensemble.get("status") != "PASS_RESPONSE_SEED_ENSEMBLE" or int(
        ensemble.get("replicas", 0)
    ) != 64:
        problems.append("64-replica detector-response seed audit is not PASS")

    conditional_model = mission["model"]["conditional_componentwise_transport_counting_endpoint"]
    for fragment in (
        "conditional",
        "not a full 95% coverage statement",
        "finite-buildup zero-family",
        "no fictitious transport exposure",
    ):
        if fragment.lower() not in conditional_model.lower():
            problems.append(f"mission conditional-endpoint model is missing semantic fragment {fragment!r}")
    if mission_summary["scope"].get(
        "finite_buildup_zero_family_uncertainty_in_conditional_transport_counting_endpoint"
    ) is not False:
        problems.append("mission scope incorrectly claims zero-family uncertainty coverage")

    reference_prompt = reference_breakdown["reference_baseline"]["prompt"]
    reference_total = reference_breakdown["reference_baseline"]["total"]
    reference_particle_rates = {
        row["particle"]: float(row["rate_cps"])
        for row in reference_breakdown["prompt_particles"]
    }
    reference_eplus_neutron_rate = reference_particle_rates["eplus"] + reference_particle_rates["n"]
    reference_eplus_neutron_prompt_percent = (
        100.0 * reference_eplus_neutron_rate / float(reference_prompt["rate_cps"])
    )
    reference_eplus_neutron_total_percent = (
        100.0 * reference_eplus_neutron_rate / float(reference_total["rate_cps"])
    )

    provenance_inputs = provenance.get("inputs", {})
    for label, path in authority_paths.items():
        record = provenance_inputs.get(rel(path), {})
        if record.get("sha256") != sha256(path):
            problems.append(f"figure provenance does not bind current {label} authority")
    for label, path in (
        ("slant45_summary", SLANT45_MISSION),
        ("slant45_validation", SLANT45_VALIDATION),
        ("slant45_timeline", SLANT45_TIMELINE),
    ):
        record = provenance_inputs.get(rel(path), {})
        if record.get("sha256") != sha256(path):
            problems.append(f"figure provenance does not bind current {label} authority")

    figure_budget = provenance.get("fig_optimized_shield_background", {})
    add_close(
        problems,
        float(figure_budget.get("final_total_background_cps", math.nan)),
        authority_background,
        "optimized-background figure total",
    )
    expected_figure_components = {
        "Prompt": component_rates["prompt"],
        "Delayed activation": component_rates["delayed"],
        "Atmospheric 511 keV": component_rates["atm511"],
    }
    for label, expected in expected_figure_components.items():
        add_close(
            problems,
            float(figure_budget.get("final_components_cps", {}).get(label, math.nan)),
            expected,
            f"optimized-background figure {label}",
        )

    figure_mission = provenance.get("fig_optimized_mission_significance", {})
    figure_mission_contract = {
        "T3_day_central": "T3_day",
        "T5_day_central": "T5_day",
        "Z20_central": "Z20d",
        "T3_day_componentwise_transport_counting_endpoint_conditional": (
            "T3_day_componentwise_transport_counting_endpoint_conditional"
        ),
        "T5_day_componentwise_transport_counting_endpoint_conditional": (
            "T5_day_componentwise_transport_counting_endpoint_conditional"
        ),
        "Z20_componentwise_transport_counting_endpoint_conditional": (
            "Z20d_componentwise_transport_counting_endpoint_conditional"
        ),
    }
    for figure_key, mission_key in figure_mission_contract.items():
        add_close(
            problems,
            float(figure_mission.get(figure_key, math.nan)),
            float(mission[mission_key]),
            f"mission figure {figure_key}",
            atol=1e-12,
        )
    for key in ("source_counts_20d", "background_counts_20d"):
        add_close(
            problems,
            float(figure_mission.get(key, math.nan)),
            float(mission[key]),
            f"mission figure {key}",
            atol=1e-9,
        )

    geometry = provenance.get("fig_reference_detector_cryostat_geometry", {})
    if geometry.get("triangles", 0) < 80_000:
        problems.append("reference semantic render has an implausibly small triangle count")
    required_materials = {"tes_ta", "tes_copper_link", "w_collimator", "external_active_shield"}
    missing_materials = required_materials.difference(geometry.get("semantic_materials", []))
    if missing_materials:
        problems.append(f"semantic geometry is missing materials={sorted(missing_materials)}")

    required_shared_tokens = [
        *FIGURES,
        latex_sci(component_rates["prompt"]),
        latex_sci(component_rates["delayed"]),
        latex_sci(component_rates["atm511"]),
        latex_sci(authority_background),
        latex_sci(float(slant45_summary["day15_selected_rates_cps"]["signal"])),
        f"{component_shares['prompt']:.2f}",
        f"{component_shares['delayed']:.2f}",
        f"{component_shares['atm511']:.2f}",
        f"{float(mission['Z20d']):.3f}",
        f"{float(mission['Z20d_componentwise_transport_counting_endpoint_conditional']):.3f}",
        f"{float(mission['T3_day']):.3f}",
        f"{float(mission['T5_day']):.3f}",
        f"{float(mission['T3_day_componentwise_transport_counting_endpoint_conditional']):.3f}",
        f"{float(mission['T5_day_componentwise_transport_counting_endpoint_conditional']):.3f}",
        latex_sci(float(mission["flux_3sigma_20d_ph_cm2_s"]), decimals=4),
        latex_sci(
            float(
                mission[
                    "flux_3sigma_20d_componentwise_transport_counting_endpoint_conditional_ph_cm2_s"
                ]
            ),
            decimals=4,
        ),
        str(response["primary_authority"]["main"]["response_seed"]),
        f"{float(response['detector_contract']['sigma_keV']):.5f}",
        f"{reference_eplus_neutron_total_percent:.2f}",
        f"{reference_eplus_neutron_prompt_percent:.2f}",
        "Tian2026DIXE",
        "Gallego2025Balloon",
    ]
    for language, text in (("en", en), ("zh", zh)):
        for token in required_shared_tokens:
            if token not in text:
                problems.append(f"{language} missing authority-derived story token: {token}")
        missing_semantics = paper_endpoint_semantics(language, text)
        if missing_semantics:
            problems.append(f"{language} missing conditional-endpoint semantics={missing_semantics}")

    language_tokens = {
        "en": [
            "semantic OBJ/MTL export",
            "directionally graded active-shield geometry",
            "Background-led geometry design and statistical treatment",
            "40 mm BGO",
            "30 mm BGO",
            "10 mm annulus",
            "64-seed response ensemble",
            "seven positive activation families",
        ],
        "zh": [
            "语义 OBJ/MTL 导出",
            "最终方向分级主动屏蔽几何",
            "由本底来源驱动的几何设计与统计方法",
            "40 mm BGO",
            "30 mm BGO",
            "10 mm BGO 环",
            "64 个",
            "7 个正活化族",
        ],
    }
    for language, text in (("en", en), ("zh", zh)):
        for token in language_tokens[language]:
            if token not in text:
                problems.append(f"{language} missing language-specific token: {token}")

    forbidden = re.compile(
        r"\bS3(?:[a-d])?\b|\bO[89]\b|391\.199|309\.777|20\.81|"
        r"mass[- ]reduction|mass saving|减重|质量削减|"
        r"shield_iteration|fig_s34_cumulative_z|fig_mass_model_xz_overview|"
        r"uniform thinning|均匀减薄|\\(?:added|rewritten)\{",
        re.IGNORECASE,
    )
    for language, text in (("en", en), ("zh", zh)):
        hits = sorted({match.group(0) for match in forbidden.finditer(text)})
        if hits:
            problems.append(f"{language} contains retired/internal public-story terms={hits}")

    abstract_words = english_abstract_word_count(en)
    if not 150 <= abstract_words <= 250:
        problems.append(f"English abstract word count {abstract_words} is outside 150--250")

    compile_patterns = re.compile(
        r"undefined references|Citation .* undefined|LaTeX Error|Package .* Error|"
        r"Emergency stop|Fatal error|Overfull \\hbox",
        re.IGNORECASE,
    )
    log_checks: dict[str, list[str]] = {}
    for language, tex_path in (("en", EN), ("zh", ZH)):
        log = tex_path.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
        hits = sorted({match.group(0) for match in compile_patterns.finditer(log)})
        log_checks[language] = hits
        if hits:
            problems.append(f"{language} compile log problems={hits}")

    figure_records = {}
    for name in FIGURES:
        path = ASSETS / name
        if path.stat().st_size < 100_000:
            problems.append(f"figure is unexpectedly small: {name}")
        figure_records[name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}

    manuscripts = {}
    for language, tex_path in (("en", EN), ("zh", ZH)):
        pdf_path = tex_path.with_suffix(".pdf")
        if pdf_path.stat().st_size < 1_000_000:
            problems.append(f"{language} PDF is unexpectedly small")
        manuscripts[language] = {
            "tex": rel(tex_path),
            "tex_sha256": sha256(tex_path),
            "pdf": rel(pdf_path),
            "pdf_sha256": sha256(pdf_path),
            "pdf_bytes": pdf_path.stat().st_size,
        }

    payload = {
        "status": "PASS_FINAL_DIRECTIONALLY_GRADED_PAPER_STORY" if not problems else "FAIL",
        "generated_at_utc": now_utc(),
        "figure_provenance": rel(PROVENANCE),
        "authorities": {
            label: {"path": rel(path), "sha256": sha256(path), "status": authorities[label]["status"]}
            for label, path in authority_paths.items()
        },
        "slant45_signal_refold": {
            "summary": rel(SLANT45_MISSION),
            "summary_sha256": sha256(SLANT45_MISSION),
            "validation": rel(SLANT45_VALIDATION),
            "validation_sha256": sha256(SLANT45_VALIDATION),
            "timeline": rel(SLANT45_TIMELINE),
            "timeline_sha256": sha256(SLANT45_TIMELINE),
            "status": slant45_summary.get("status"),
        },
        "reference_response_authority": rel(REFERENCE_BREAKDOWN),
        "checks": {
            "all8_authority_chain_bound": not any("hash" in problem or "authority status" in problem for problem in problems),
            "eight_family_contract": not any("family set" in problem or "family order" in problem for problem in problems),
            "seven_positive_plus_eminus_zero_no_te": not any("eminus" in problem or "positive activation" in problem for problem in problems),
            "conditional_endpoint_semantics": not any("conditional" in problem or "coverage" in problem for problem in problems),
            "actual_semantic_mass_model_render": not any("semantic" in p or "triangle" in p for p in problems),
            "four_current_figures_present": not any("figure" in p and "small" in p for p in problems),
            "shared_numeric_story_synchronized": not any("story token" in p for p in problems),
            "response_components_sum_to_total": not any("component sum" in p for p in problems),
            "mission_values_recomputed": not any("mission central" in p or "mission conditional" in p for p in problems),
            "response_seed_ensemble_pass": not any("64-replica" in p for p in problems),
        "figures_match_all8_authorities": not any(
            "figure" in p and ("authority" in p or "actual=" in p)
            for p in problems
        ),
            "internal_design_labels_absent_from_public_story": not any("public-story" in p for p in problems),
            "english_abstract_words": abstract_words,
            "compile_logs_clean": not any("compile log" in p for p in problems),
        },
        "family_contract": family_contract,
        "compile_log_matches": log_checks,
        "authority_spot_checks": {
            "component_rates_cps": component_rates,
            "recomputed_background_cps": recomputed_background,
            "authority_background_cps": authority_background,
            "component_shares_percent": component_shares,
            "final_background_records": final_background_records,
            "selected_delayed_events": selected_delayed_events,
            "recomputed_Z20": recomputed_z20,
            "authority_Z20": mission["Z20d"],
            "recomputed_conditional_Z20": recomputed_conditional_z20,
            "authority_conditional_Z20": mission[
                "Z20d_componentwise_transport_counting_endpoint_conditional"
            ],
            "recomputed_F3_20d_ph_cm2_s": recomputed_f3,
            "authority_F3_20d_ph_cm2_s": mission["flux_3sigma_20d_ph_cm2_s"],
            "recomputed_conditional_F3_20d_ph_cm2_s": recomputed_conditional_f3,
            "authority_conditional_F3_20d_ph_cm2_s": mission[
                "flux_3sigma_20d_componentwise_transport_counting_endpoint_conditional_ph_cm2_s"
            ],
        },
        "manuscripts": manuscripts,
        "figures": figure_records,
        "problems": problems,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"status": payload["status"], "output": rel(OUT), "problems": problems},
            indent=2,
        )
    )
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
