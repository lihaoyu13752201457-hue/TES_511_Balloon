#!/usr/bin/env python3
"""Validate the aligned public EN/ZH manuscript pair against the all8 authorities."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = {
    "en": HERE / "balloon511_ea_draft_en.tex",
    "zh": HERE / "balloon511_ea_draft_zh.tex",
}
PDFS = {
    "en": HERE / "balloon511_ea_draft_en_aligned_20260713.pdf",
    "zh": HERE / "balloon511_ea_draft_zh_aligned_20260713.pdf",
}
LOGS = {
    "en": HERE / "balloon511_ea_draft_en_aligned_20260713.log",
    "zh": HERE / "balloon511_ea_draft_zh_aligned_20260713.log",
}
OUTPUT = HERE / "ea_bilingual_alignment_validation_20260713.json"

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
AUTHORITIES = {
    "activation": ACTIVATION,
    "components": COMPONENTS,
    "step05": STEP05,
    "response": RESPONSE,
    "response_validation": RESPONSE_VALIDATION,
    "mission": MISSION,
    "mission_validation": MISSION_VALIDATION,
    "slant45_mission": SLANT45_MISSION,
    "slant45_validation": SLANT45_VALIDATION,
}

EXPECTED_COUNTS = {
    "section": 5,
    "section_star": 2,
    "subsection": 12,
    "subsubsection": 6,
    "figure": 10,
    "table": 7,
    "equation": 20,
}
EXPECTED_STATUSES = {
    "activation": "PASS_S3D_O8_ALL8_ACTIVATION_AND_FAMILY_DELAYED_TRANSPORT",
    "components": "PASS_S3D_O8_ALL8_STEP05_DELAYED_COMPONENTS",
    "step05": "PASS_S3D_O8_ALL8_ACTIVATION_STEP05_DAY15",
    "response": "PASS_S3D_O8_ALL8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE",
    "response_validation": "PASS_S3D_O8_ALL8_ENERGY_RESPONSE_VALIDATION",
    "mission": "PASS_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_CLOSURE",
    "mission_validation": "PASS_S3D_O8_ALL8_FAMILY_NUCLIDE_MISSION_VALIDATION",
    "slant45_mission": "PASS_EA_P02_FIXED_45DEG_SLANT_SIGNAL_REFOLD",
    "slant45_validation": "PASS_EA_P02_FIXED_45DEG_SLANT_SIGNAL_REFOLD_VALIDATION",
}
FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
POSITIVE_FAMILIES = ("alpha", "eplus", "gamma", "muminus", "muplus", "n", "p")
ZERO_FAMILY = "eminus"
W2 = "w2_510p58_511p42"

FORBIDDEN_PUBLIC_LABELS = {
    "mass_model_511": re.compile(r"mass[_-]?model[_-]?511", re.I),
    "mass_511": re.compile(r"mass[_-]?511", re.I),
    "internal_s3_design_family": re.compile(r"\bS3(?:[a-d])?\b", re.I),
    "o8_o9": re.compile(r"\bO[89]\b", re.I),
    "c0": re.compile(r"\bC0\b", re.I),
    "lw1": re.compile(r"\bLW1\b", re.I),
    "fix5": re.compile(r"\bfix5\b", re.I),
    "f10m": re.compile(r"\bf10m\b", re.I),
}

STATIC_REQUIRED_SOURCE_TEXT = {
    "en": (
        "mass-complete reference geometry",
        "directionally graded active-shield geometry",
        "all eight prompt families",
        "seven positive activation families",
    ),
    "zh": (
        "质量完备参考几何",
        "最终方向分级主动屏蔽几何",
        "全部八类瞬发粒子",
        "7 个正活化族",
    ),
}

HEADING_RE = re.compile(
    r"^\\(?P<kind>section\*?|subsection\*?|subsubsection\*?)\{(?P<title>.*)\}\s*$",
    re.M,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_close(
    actual: float,
    expected: float,
    message: str,
    *,
    atol: float = 1.0e-15,
    rtol: float = 1.0e-12,
) -> None:
    require(
        math.isclose(float(actual), float(expected), rel_tol=rtol, abs_tol=atol),
        f"{message}: actual={actual!r}, expected={expected!r}",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latex_sci(value: float, decimals: int = 5) -> str:
    value = float(value)
    require(value != 0.0 and math.isfinite(value), f"Invalid scientific-notation value {value!r}")
    exponent = math.floor(math.log10(abs(value)))
    mantissa = value / (10.0**exponent)
    return rf"{mantissa:.{decimals}f}\times10^{{{exponent}}}"


def require_authority_hash(owner: dict[str, Any], key: str, path: Path, label: str) -> None:
    require(owner.get(key) == rel(path), f"{label} records the wrong path")
    require(owner.get(f"{key}_sha256") == sha256(path), f"{label} hash is stale")


def command_counts(text: str) -> dict[str, int]:
    return {
        "section": len(re.findall(r"^\\section\{", text, re.M)),
        "section_star": len(re.findall(r"^\\section\*\{", text, re.M)),
        "subsection": len(re.findall(r"^\\subsection\{", text, re.M)),
        "subsubsection": len(re.findall(r"^\\subsubsection\{", text, re.M)),
        "figure": text.count(r"\begin{figure}"),
        "table": text.count(r"\begin{table}"),
        "equation": text.count(r"\begin{equation}"),
    }


def citation_keys(text: str) -> set[str]:
    keys: set[str] = set()
    for group in re.findall(r"\\cite\{([^}]+)\}", text):
        keys.update(key.strip() for key in group.split(","))
    return keys


def citation_order(text: str) -> list[str]:
    body = text.split(r"\begin{thebibliography}", 1)[0]
    order: list[str] = []
    for group in re.findall(r"\\cite\{([^}]+)\}", body):
        for raw_key in group.split(","):
            key = raw_key.strip()
            if key and key not in order:
                order.append(key)
    return order


def bibliography_keys(text: str) -> set[str]:
    return set(re.findall(r"\\bibitem(?:\[[^]]*\])?\{([^}]+)\}", text))


def bibliography_order(text: str) -> list[str]:
    return re.findall(r"^\\bibitem\{([^}]+)\}", text, re.M)


def heading_profile(text: str) -> list[dict[str, object]]:
    body = text.split(r"\begin{thebibliography}", 1)[0]
    matches = list(HEADING_RE.finditer(body))
    profile: list[dict[str, object]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        blocks = [block for block in re.split(r"\n\s*\n", content) if block.strip()]
        profile.append(
            {
                "kind": match.group("kind"),
                "title": match.group("title"),
                "block_count": len(blocks),
            }
        )
    return profile


def environment_sequence(text: str) -> list[str]:
    return re.findall(r"\\begin\{(figure|table|equation)\}", text)


def pdf_text(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def pdf_pages(path: Path) -> int:
    result = subprocess.run(
        ["pdfinfo", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.M)
    require(match is not None, f"Could not read page count for {path.name}")
    return int(match.group(1))


def require_endpoint_semantics(language: str, text: str) -> None:
    compact = re.sub(r"\s+", " ", text)
    patterns = {
        "en": {
            "conditional componentwise transport-counting endpoint": r"conditional.{0,120}component(?:[- ]?wise).{0,80}transport[- ]counting endpoint|component(?:[- ]?wise).{0,80}transport[- ]counting endpoint.{0,120}conditional",
            "not full 95-percent coverage": r"(?:not (?:a )?(?:full|joint)|does not (?:represent|have)).{0,40}(?:95\\?%|95-percent).{0,30}(?:coverage|interval)",
            "finite-buildup zero observation": r"finite[- ]buildup zero observation",
            "no fictitious transport exposure": r"no fictitious transport exposure",
        },
        "zh": {
            "conditional componentwise transport-counting endpoint": r"条件.{0,80}(?:逐分量|分量逐项).{0,50}输运计数端点|(?:逐分量|分量逐项).{0,50}输运计数端点.{0,80}条件",
            "not full 95-percent coverage": r"(?:不是|不构成).{0,30}完整.{0,20}95\\?%.{0,20}覆盖",
            "finite-buildup zero observation": r"有限(?:累积|积累|\s*BUILDUP\s*)零观测",
            "no fictitious transport exposure": r"不.{0,12}虚构.{0,12}输运曝光",
        },
    }
    for label, pattern in patterns[language].items():
        require(re.search(pattern, compact, re.I) is not None, f"Missing {label} semantics in {language}")


def validate_authorities() -> dict[str, Any]:
    for label, path in AUTHORITIES.items():
        require(path.is_file(), f"Missing {label} authority: {rel(path)}")
    require(SLANT45_TIMELINE.is_file(), f"Missing slant45 timeline: {rel(SLANT45_TIMELINE)}")
    data = {label: load_json(path) for label, path in AUTHORITIES.items()}
    for label, expected in EXPECTED_STATUSES.items():
        require(data[label].get("status") == expected, f"{label} status is not {expected}")

    activation = data["activation"]
    components = data["components"]
    step05 = data["step05"]
    response = data["response"]
    response_validation = data["response_validation"]
    mission_summary = data["mission"]
    mission_validation = data["mission_validation"]
    slant45_summary = data["slant45_mission"]
    slant45_validation = data["slant45_validation"]

    response_inputs = response["input_authorities"]
    for key, path in (("campaign", ACTIVATION), ("components", COMPONENTS), ("step05", STEP05)):
        require_authority_hash(response_inputs, key, path, f"response/{key}")
    require_authority_hash(response_validation, "summary", RESPONSE, "response-validation/summary")
    require_authority_hash(
        response_validation, "components", COMPONENTS, "response-validation/components"
    )
    require(
        int(response_validation.get("replica_rows", -1))
        == int(response["response_seed_ensemble"]["replicas"])
        == 64,
        "Response authority/validation does not bind exactly 64 replicas",
    )

    mission_inputs = mission_summary["input_authorities"]
    for key, path in (
        ("campaign", ACTIVATION),
        ("components", COMPONENTS),
        ("step05", STEP05),
        ("response", RESPONSE),
        ("response_validation", RESPONSE_VALIDATION),
    ):
        require_authority_hash(mission_inputs, key, path, f"mission/{key}")
    require_authority_hash(mission_validation, "summary", MISSION, "mission-validation/summary")
    require(int(mission_validation.get("families_rechecked", -1)) == 8, "Mission validator did not recheck eight families")
    require(bool(mission_validation.get("activity_key_set_complete")), "Mission activity key set is incomplete")
    require(not slant45_summary.get("problems"), "Slant45 summary contains validation problems")
    require(not slant45_validation.get("problems"), "Slant45 validation contains problems")
    require(
        slant45_validation.get("summary_sha256") == sha256(SLANT45_MISSION),
        "Slant45 validation does not bind the current summary",
    )
    require(
        slant45_validation.get("timeline_sha256") == sha256(SLANT45_TIMELINE),
        "Slant45 validation does not bind the current timeline",
    )
    require(
        (slant45_summary.get("input_authorities") or {}).get(
            "retained_mission_summary_sha256"
        )
        == sha256(MISSION),
        "Slant45 summary does not bind the retained mission summary",
    )

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
    mission_family_rates = mission_summary["mission"]["day15_selected_rates_cps"][
        "delayed_by_incident_family"
    ]
    for label, value in (
        ("activation", campaign_rows),
        ("components", component_rows),
        ("Step05", step05_rows),
        ("response", response_metrics),
        ("response physical", response_delayed),
        ("mission", mission_family_rates),
    ):
        require(set(value) == expected, f"{label} does not contain the exact eight-family set")
    require(components.get("family_order") == list(FAMILIES), "Component family order is stale")
    require(set(components.get("positive_families", [])) == positive, "Not exactly seven positive activation families")
    require(components.get("audited_zero_families") == [ZERO_FAMILY], "eminus is not the sole audited zero family")

    total_activity = 0.0
    for family in FAMILIES:
        campaign = campaign_rows[family]
        component = component_rows[family]
        production = component["production"]
        require_close(component["activity_Bq"], campaign["activity_Bq"], f"{family} activity closure")
        require_close(
            step05_rows[family]["activity_Bq"], component["activity_Bq"], f"{family} Step05 activity closure"
        )
        require(int(production["files"]) == int(production["tt_lines"]), f"{family} TT line guard failed")
        require_close(
            production["division"], production["files"], f"{family} family-division guard", atol=0.0, rtol=0.0
        )
        if family in positive:
            total_activity += float(component["activity_Bq"])
            require(campaign["status"] == component["status"] == "PASS", f"{family} is not PASS positive")
            require(not production["zero_production"], f"{family} is incorrectly zero production")
            require(float(component["activity_Bq"]) > 0.0, f"{family} activity is not positive")
            te_s = component.get("TE_s")
            weight = component.get("event_weight_hz")
            require(te_s is not None and float(te_s) > 0.0, f"{family} lacks positive TE")
            require(weight is not None and float(weight) > 0.0, f"{family} lacks positive 1/TE weight")
            require_close(weight, 1.0 / float(te_s), f"{family} 1/TE normalization", atol=1e-20)
            require(response_metrics[family]["component_status"] == "PASS", f"{family} response status is not positive-family PASS")
        else:
            require(campaign["status"] == component["status"] == "PASS_ZERO_PRODUCTION", "eminus status is not PASS_ZERO_PRODUCTION")
            require(bool(production["zero_production"]), "eminus is not marked finite-buildup zero")
            require(float(component["activity_Bq"]) == 0.0, "eminus activity is not exactly zero")
            require(
                all(component.get(key) is None for key in ("sim", "TE_s", "event_weight_hz")),
                "eminus incorrectly has a delayed SIM, TE, or event weight",
            )
            require(int(component.get("SE", -1)) == int(component.get("ID", -1)) == 0, "eminus has transported events")
            require(not campaign.get("transport"), "eminus campaign invents transport provenance")
            metric = response_metrics[family]
            require(
                metric["status"] == "PASS_FINITE_BUILDUP_ZERO_NO_TRANSPORT_RESPONSE_REPLICAS",
                "eminus response branch is not finite-buildup-zero/no-transport",
            )
            require(metric["event_weight_cps"] is None and metric["all_replicas_exact_zero"], "eminus response invents exposure")
            physical = response_delayed[family]
            require(
                all(
                    physical.get(key) is None
                    for key in ("event_weight_cps", "rate_interval95_cps", "rate_upper95_cps")
                ),
                "eminus response invents a TE-derived counting interval",
            )
        require_close(
            mission_family_rates[family],
            response_delayed[family]["rate_cps"],
            f"{family} response/mission delayed-rate closure",
        )
    require_close(
        total_activity,
        activation["total_fixed_day15_activity_Bq"],
        "Seven-positive-family activity total",
        atol=1e-12,
    )

    w2 = response["primary_authority"]["step05"]["windows"][W2]
    streams = w2["by_stream"]
    physical = w2["physical_reference_flux"]
    rates = {
        "prompt": float(streams["prompt"]["side_compton_fov_pass_rate_cps"]),
        "delayed": float(streams["delayed"]["side_compton_fov_pass_rate_cps"]),
        "atm511": float(streams["atm511_sidecar"]["side_compton_fov_pass_rate_cps"]),
    }
    background = sum(rates.values())
    require_close(background, physical["background_cps"], "Response background component sum")
    retained_mission = mission_summary["mission"]
    mission_rates = retained_mission["day15_selected_rates_cps"]
    for key, expected_rate in (
        ("prompt", rates["prompt"]),
        ("delayed", rates["delayed"]),
        ("atm511", rates["atm511"]),
        ("background", background),
        ("signal", float(physical["signal_cps_at_reference_flux"])),
    ):
        require_close(mission_rates[key], expected_rate, f"Response/mission {key} day-15 rate")
    require_close(
        sum(float(value) for value in mission_family_rates.values()),
        mission_rates["delayed"],
        "Mission delayed family sum",
    )

    mission = slant45_summary["mission"]
    z20 = float(mission["source_counts_20d"]) / math.sqrt(float(mission["background_counts_20d"]))
    conditional_z20 = float(
        mission["source_transport_counting_lower_endpoint_counts_20d"]
    ) / math.sqrt(float(mission["background_componentwise_transport_counting_upper_endpoint_counts_20d"]))
    require_close(z20, mission["Z20d"], "Central Z20 recomputation", atol=1e-12)
    require_close(
        conditional_z20,
        mission["Z20d_componentwise_transport_counting_endpoint_conditional"],
        "Conditional componentwise transport-counting Z20 recomputation",
        atol=1e-12,
    )
    f3 = float(mission["reference_flux_ph_cm2_s"]) * 3.0 / z20
    conditional_f3 = float(mission["reference_flux_ph_cm2_s"]) * 3.0 / conditional_z20
    require_close(f3, mission["flux_3sigma_20d_ph_cm2_s"], "Central F3 recomputation")
    require_close(
        conditional_f3,
        mission[
            "flux_3sigma_20d_componentwise_transport_counting_endpoint_conditional_ph_cm2_s"
        ],
        "Conditional componentwise transport-counting F3 recomputation",
    )
    endpoint_model = mission["model"]["conditional_componentwise_transport_counting_endpoint"].lower()
    for fragment in (
        "conditional",
        "not a full 95% coverage statement",
        "finite-buildup zero-family",
        "no fictitious transport exposure",
    ):
        require(fragment in endpoint_model, f"Mission endpoint model lacks {fragment!r}")
    require(
        mission_summary["scope"][
            "finite_buildup_zero_family_uncertainty_in_conditional_transport_counting_endpoint"
        ]
        is False,
        "Mission scope incorrectly claims finite-buildup zero-family uncertainty coverage",
    )

    shares = {name: 100.0 * rate / background for name, rate in rates.items()}
    return {
        "data": data,
        "rates_cps": rates,
        "background_cps": background,
        "signal_cps": float(slant45_summary["day15_selected_rates_cps"]["signal"]),
        "shares_percent": shares,
        "mission": mission,
        "response_seed": int(response["primary_authority"]["main"]["response_seed"]),
        "selected_delayed_events": int(mission_summary["selected_delayed_lineage"]["selected_events"]),
        "final_background_records": sum(
            int(streams[name]["side_compton_fov_pass_events"])
            for name in ("prompt", "delayed", "atm511_sidecar")
        ),
        "family_contract": {
            "families": list(FAMILIES),
            "positive_families": list(POSITIVE_FAMILIES),
            "audited_zero_families": [ZERO_FAMILY],
            "total_fixed_day15_activity_Bq": total_activity,
            "eminus_no_delayed_te": component_rows[ZERO_FAMILY]["TE_s"] is None,
        },
    }


def authority_derived_source_tokens(authority: dict[str, Any]) -> tuple[str, ...]:
    mission = authority["mission"]
    rates = authority["rates_cps"]
    shares = authority["shares_percent"]
    return (
        latex_sci(rates["prompt"]),
        latex_sci(rates["delayed"]),
        latex_sci(rates["atm511"]),
        latex_sci(authority["background_cps"]),
        latex_sci(authority["signal_cps"]),
        f"{shares['prompt']:.2f}",
        f"{shares['delayed']:.2f}",
        f"{shares['atm511']:.2f}",
        f"{float(mission['source_counts_20d']):.2f}",
        f"{float(mission['background_counts_20d']):.2f}",
        f"{float(mission['T3_day']):.3f}",
        f"{float(mission['T5_day']):.3f}",
        f"{float(mission['T3_day_componentwise_transport_counting_endpoint_conditional']):.3f}",
        f"{float(mission['T5_day_componentwise_transport_counting_endpoint_conditional']):.3f}",
        f"{float(mission['Z20d']):.3f}",
        f"{float(mission['Z20d_componentwise_transport_counting_endpoint_conditional']):.3f}",
        latex_sci(float(mission["flux_3sigma_20d_ph_cm2_s"]), decimals=4),
        latex_sci(
            float(
                mission[
                    "flux_3sigma_20d_componentwise_transport_counting_endpoint_conditional_ph_cm2_s"
                ]
            ),
            decimals=4,
        ),
        str(authority["response_seed"]),
    )


def main() -> None:
    authority = validate_authorities()
    source_text = {
        language: path.read_text(encoding="utf-8") for language, path in SOURCES.items()
    }
    results: dict[str, Any] = {
        "status": "PASS_BILINGUAL_SENTENCE_ALIGNMENT_ALL8_AUTHORITY_BOUND",
        "authorities": {
            label: {
                "path": rel(path),
                "sha256": sha256(path),
                "status": authority["data"][label]["status"],
            }
            for label, path in AUTHORITIES.items()
        },
        "family_contract": authority["family_contract"],
        "authority_derived_story": {
            "rates_cps": authority["rates_cps"],
            "background_cps": authority["background_cps"],
            "signal_cps": authority["signal_cps"],
            "shares_percent": authority["shares_percent"],
            "selected_delayed_events": authority["selected_delayed_events"],
            "final_background_records": authority["final_background_records"],
        },
        "sources": {},
        "pdfs": {},
    }

    profiles = {language: heading_profile(text) for language, text in source_text.items()}
    kinds = {language: [item["kind"] for item in profile] for language, profile in profiles.items()}
    blocks = {
        language: [item["block_count"] for item in profile]
        for language, profile in profiles.items()
    }
    require(kinds["en"] == kinds["zh"], "Heading-level sequence differs between languages")
    require(blocks["en"] == blocks["zh"], "Corresponding heading block counts differ between languages")

    sequences = {language: environment_sequence(text) for language, text in source_text.items()}
    require(sequences["en"] == sequences["zh"], "Figure/table/equation sequence differs between languages")

    citations = {language: citation_keys(text) for language, text in source_text.items()}
    bibliography = {language: bibliography_keys(text) for language, text in source_text.items()}
    first_citation = {language: citation_order(text) for language, text in source_text.items()}
    bibliography_sequence = {
        language: bibliography_order(text) for language, text in source_text.items()
    }
    require(citations["en"] == citations["zh"], "Citation-key sets differ between languages")
    require(bibliography["en"] == bibliography["zh"], "Bibliography-key sets differ between languages")
    require(first_citation["en"] == first_citation["zh"], "First-citation order differs between languages")
    require(
        bibliography_sequence["en"] == bibliography_sequence["zh"],
        "Bibliography order differs between languages",
    )

    derived_tokens = authority_derived_source_tokens(authority)
    for language, text in source_text.items():
        counts = command_counts(text)
        require(counts == EXPECTED_COUNTS, f"Unexpected structural counts in {language}: {counts}")
        require(citations[language] <= bibliography[language], f"Missing bibliography entries in {language}")
        require(bibliography[language] <= citations[language], f"Unused bibliography entries in {language}")
        require(
            first_citation[language] == bibliography_sequence[language],
            f"Bibliography is not in first-citation order in {language}",
        )
        require(r"\usepackage{cite}" in text, f"Numeric citation compression package missing in {language}")
        require(
            not re.search(r"^\\bibitem\[", text, re.M),
            f"Author-year bibliography label remains in {language}",
        )
        for label, pattern in FORBIDDEN_PUBLIC_LABELS.items():
            require(not pattern.search(text), f"Forbidden internal label {label} appears in {language} source")
        for phrase in STATIC_REQUIRED_SOURCE_TEXT[language]:
            require(
                re.search(re.escape(phrase), text, re.I) is not None,
                f"Required current phrase missing from {language}: {phrase}",
            )
        for token in derived_tokens:
            require(token in text, f"Authority-derived value missing from {language}: {token}")
        require_endpoint_semantics(language, text)
        require(
            "historical depth--cutoff scalar" not in text,
            f"Retired scalar mission fold remains in {language}",
        )
        results["sources"][language] = {
            "path": str(SOURCES[language].relative_to(HERE)),
            "counts": counts,
            "heading_profile": profiles[language],
            "citation_count": len(citations[language]),
            "bibliography_count": len(bibliography[language]),
            "citation_style": "numeric_first_appearance",
            "first_citation_order_matches_bibliography": True,
            "all8_authority_values_present": True,
            "conditional_endpoint_semantics_present": True,
        }

    for language, pdf_path in PDFS.items():
        require(pdf_path.exists(), f"Missing aligned {language} PDF")
        require(pdf_path.stat().st_size > 1_000_000, f"Aligned {language} PDF is unexpectedly small")
        require(
            pdf_path.stat().st_mtime >= SOURCES[language].stat().st_mtime,
            f"Aligned {language} PDF predates source",
        )
        log_text = LOGS[language].read_text(encoding="utf-8", errors="replace")
        require("Overfull \\hbox" not in log_text, f"Overfull box remains in {language} build")
        require(
            not re.search(
                r"undefined (?:references|citations)|(?:Citation|Reference).+undefined",
                log_text,
                re.I,
            ),
            f"Undefined citation/reference remains in {language} build",
        )
        visible_text = pdf_text(pdf_path)
        require(
            "[Prantzos" not in visible_text and "[Jean" not in visible_text,
            f"Author-year citations remain visible in {language} PDF",
        )
        require("[1, 2]" in visible_text, f"Expected numeric citation pair missing in {language} PDF")
        for label, pattern in FORBIDDEN_PUBLIC_LABELS.items():
            require(
                not pattern.search(visible_text),
                f"Forbidden internal label {label} appears in {language} PDF",
            )
        results["pdfs"][language] = {
            "path": str(pdf_path.relative_to(HERE)),
            "bytes": pdf_path.stat().st_size,
            "pages": pdf_pages(pdf_path),
            "overfull_boxes": 0,
            "undefined_references_or_citations": 0,
        }

    results["cross_language"] = {
        "heading_sequence_match": True,
        "corresponding_block_counts_match": True,
        "float_equation_sequence_match": True,
        "citation_set_match": True,
        "bibliography_set_match": True,
        "first_citation_order_match": True,
        "numeric_citation_style": True,
        "forbidden_internal_labels_absent_from_sources_and_pdfs": True,
        "all8_authority_chain_bound": True,
        "seven_positive_plus_eminus_zero_no_te": True,
        "conditional_endpoint_semantics_aligned": True,
    }
    OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": results["status"], "output": str(OUTPUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
