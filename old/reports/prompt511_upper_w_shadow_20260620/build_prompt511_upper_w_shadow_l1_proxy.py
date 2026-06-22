#!/usr/bin/env python3
"""Build a prompt Step05-like L1 proxy for the upper-W-shadow smoke."""

from __future__ import annotations

import importlib.util
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_upper_w_shadow_20260620"
BASE_PROXY = ROOT / "outputs/reports/prompt511_repack_smoke_20260617/build_prompt511_repack_l1_proxy.py"
CURRENT_STEP05_CACHE = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613_l1/work/event_catalog.pkl"
)

UPPER_W_SHADOW_PROMPT_DIR_BY_TAG = {
    "eplus": WORK / "runs/upper_w_shadow_eplus_g10m_r4_promptonly",
    "n": WORK / "runs/upper_w_shadow_n_g10m_r16_promptonly",
    "muplus": WORK / "runs/upper_w_shadow_muplus_g10m_r80_promptonly",
}

SUMMARY_JSON = WORK / "prompt511_upper_w_shadow_l1_proxy_summary.json"
SUMMARY_MD = WORK / "prompt511_upper_w_shadow_l1_proxy_summary.md"

OLD_NEW_GEO_RE_PROMPT_TOTAL_CPS = 0.0323247092031
TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_module(name: str, path: Path):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def parse_tag(value: str | Path) -> str:
    m = TAG_RE.search(Path(value).name)
    return m.group("tag").lower() if m else "unknown"


def prompt_only_rates_from_norm(prompt_dir: Path) -> dict[str, float]:
    """Return per-generated-event rates for prompt-only runs without TT dat files."""
    norm_path = prompt_dir / "normalization.json"
    summary_path = prompt_dir / "run_summary.json"
    if not norm_path.exists() or not summary_path.exists():
        return {}
    norm = json.loads(norm_path.read_text(encoding="utf-8"))
    rows = json.loads(summary_path.read_text(encoding="utf-8"))
    area = float(norm["farfield_area_cm2"])
    flux_by_tag = {str(k): float(v) for k, v in norm["flux_by_particle_cm2_s"].items()}
    events_by_tag: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.get("status") != "PASS":
            continue
        tag = parse_tag(str(row.get("job_name") or row.get("sim_path") or ""))
        if tag == "unknown":
            continue
        events_by_tag[tag] += int(row.get("generated_particles") or row.get("events") or 0)
    rates = {}
    for tag, events in events_by_tag.items():
        if events > 0 and tag in flux_by_tag:
            rates[tag] = flux_by_tag[tag] * area / events
    return rates


def install_prompt_only_rate_fallback(proxy) -> None:
    original = proxy.load_prompt_rates

    def load_prompt_rates_compat(prompt_dir: Path) -> dict[str, float]:
        rates = {}
        try:
            rates.update(original(prompt_dir))
        except Exception:
            pass
        for tag, rate in prompt_only_rates_from_norm(prompt_dir).items():
            rates.setdefault(tag, rate)
        return rates

    proxy.load_prompt_rates = load_prompt_rates_compat


def ratio(num: float, den: float) -> float | None:
    return num / den if den > 0.0 else None


def poisson_ratio_sigma(num_events: int, den_events: int, r: float | None) -> float | None:
    if r is None or num_events <= 0 or den_events <= 0:
        return None
    return r * math.sqrt(1.0 / num_events + 1.0 / den_events)


def summarize_particle_cases(proxy, step05, disk: dict[str, Any], reject_policy: str) -> dict[str, Any]:
    particle_cases: dict[str, Any] = {}
    for tag, prompt_dir in UPPER_W_SHADOW_PROMPT_DIR_BY_TAG.items():
        if not proxy.repack_dir_ready(prompt_dir, tag):
            continue
        particle_cases[tag] = {
            "current_baseline": proxy.summarize_catalog_case(
                step05, CURRENT_STEP05_CACHE, disk, reject_policy, stream="prompt", tag=tag
            ),
            "upper_w_shadow": proxy.summarize_prompt_dir(step05, prompt_dir, disk, reject_policy, tag=tag),
        }
    if "eplus" not in particle_cases:
        raise RuntimeError("eplus upper-W-shadow case is required")
    return particle_cases


def summarize_ratios(particle_cases: dict[str, Any]) -> dict[str, Any]:
    stages = {
        "raw": ("raw_rate_s-1", "raw_events"),
        "active_veto_pass": ("active_veto_pass_rate_s-1", "active_veto_pass_events"),
        "side_compton_fov_pass": ("side_compton_fov_pass_rate_s-1", "side_compton_fov_pass_events"),
    }
    out: dict[str, Any] = {}
    for tag, pair in particle_cases.items():
        out[tag] = {}
        cur = pair["current_baseline"]["summary"]
        var = pair["upper_w_shadow"]["summary"]
        for stage, (rate_key, event_key) in stages.items():
            r = ratio(float(cur[rate_key]), float(var[rate_key]))
            out[tag][stage] = {
                "current_over_upper_w_shadow_ratio": r,
                "counting_only_1sigma": poisson_ratio_sigma(int(cur[event_key]), int(var[event_key]), r),
                "current_events": int(cur[event_key]),
                "upper_w_shadow_events": int(var[event_key]),
                "current_rate_s-1": float(cur[rate_key]),
                "upper_w_shadow_rate_s-1": float(var[rate_key]),
            }
    return out


def build_projection(proxy, step05, disk: dict[str, Any], reject_policy: str, particle_cases: dict[str, Any]) -> dict[str, Any]:
    current_by_tag = proxy.summarize_current_final_by_tag(step05, CURRENT_STEP05_CACHE, disk, reject_policy)
    current_final_rates = {
        tag: float(row["side_compton_fov_pass_rate_s-1"])
        for tag, row in current_by_tag.items()
        if float(row["side_compton_fov_pass_rate_s-1"]) > 0.0
    }
    projected_rates = dict(current_final_rates)
    for tag, pair in particle_cases.items():
        projected_rates[tag] = float(pair["upper_w_shadow"]["summary"]["side_compton_fov_pass_rate_s-1"])
    current_total = sum(current_final_rates.values())
    projected_total = sum(projected_rates.values())
    return {
        "current_total_s-1": current_total,
        "projected_total_s-1": projected_total,
        "old_new_geo_re_prompt_total_s-1": OLD_NEW_GEO_RE_PROMPT_TOTAL_CPS,
        "projected_over_old_prompt_total": projected_total / OLD_NEW_GEO_RE_PROMPT_TOTAL_CPS,
        "upper_w_shadow_replaced_tags": sorted(particle_cases),
        "current_carried_tags": sorted(set(current_final_rates) - set(particle_cases)),
        "projected_by_tag_s-1": dict(sorted(projected_rates.items())),
        "current_final_by_tag_s-1": dict(sorted(current_final_rates.items())),
        "current_final_prompt_by_tag": current_by_tag,
    }


def markdown(payload: dict[str, Any]) -> str:
    def tag_list(tags: list[str]) -> str:
        return ", ".join(tags) if tags else "(none)"

    lines = [
        "# Prompt-511 Upper W Shadow L1-like Proxy",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This is a prompt-only Step05-like diagnostic for the upper-W-shadow",
        "candidate. It is not a delayed-source, science-signal, Step06, Step07,",
        "or Step08 authority. W-only candidates must still pass n/mu and isotope",
        "recording gates before any design promotion.",
        "",
        f"Window: `{payload['line_window_keV'][0]} <= TES_total_keV < {payload['line_window_keV'][1]}`.",
        f"Active-veto threshold used by this proxy: `{payload['active_veto_threshold_keV']} keV`.",
        "",
        "| tag | case | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for tag, pair in payload["particle_cases"].items():
        for case_name in ("current_baseline", "upper_w_shadow"):
            row = pair[case_name]["summary"]
            lines.append(
                f"| {tag} | {case_name} | {row['raw_events']} | {row['raw_rate_s-1']:.6g} | "
                f"{row['active_veto_pass_events']} | {row['active_veto_pass_rate_s-1']:.6g} | "
                f"{row['side_compton_fov_pass_events']} | {row['side_compton_fov_pass_rate_s-1']:.6g} |"
            )

    lines.extend(["", "Current/upper-W-shadow suppression factors:", ""])
    for tag, stages in payload["particle_ratios"].items():
        for stage, row in stages.items():
            r = row["current_over_upper_w_shadow_ratio"]
            if r is None:
                continue
            sigma = row["counting_only_1sigma"]
            suffix = "" if sigma is None else f" +/- {sigma:.3g}"
            lines.append(f"- {tag} {stage}: `{r:.6g}{suffix}`")

    proj = payload["total_prompt_projection"]
    lines.extend(
        [
            "",
            "Total prompt projection:",
            "",
            f"- current official prompt total: `{proj['current_total_s-1']:.6g} cps`.",
            f"- projected prompt total with upper-W-shadow replaced tags: `{proj['projected_total_s-1']:.6g} cps`.",
            f"- old `new_geo_re` prompt total: `{proj['old_new_geo_re_prompt_total_s-1']:.6g} cps`.",
            f"- projected/old ratio: `{proj['projected_over_old_prompt_total']:.6g}`.",
            f"- upper-W-shadow replaced tags: `{tag_list(proj['upper_w_shadow_replaced_tags'])}`.",
            f"- current-carried tags: `{tag_list(proj['current_carried_tags'])}`.",
            "",
            "Limitations:",
            "",
        ]
    )
    for item in payload["limitations"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def main() -> int:
    proxy = load_module("prompt511_repack_l1_proxy_base_for_upper_w_shadow", BASE_PROXY)
    install_prompt_only_rate_fallback(proxy)
    step05 = load_module(
        "build_v3p5_centerfinger_step05_l1_response_for_upper_w_shadow",
        ROOT / "code/tools/build_v3p5_centerfinger_step05_l1_response.py",
    )
    disk = step05.side_entry_disk()
    reject_policy = "keep"

    particle_cases = summarize_particle_cases(proxy, step05, disk, reject_policy)
    particle_ratios = summarize_ratios(particle_cases)
    projection = build_projection(proxy, step05, disk, reject_policy, particle_cases)
    status = (
        "PASS_PROMPT511_UPPER_W_SHADOW_L1_PROXY"
        if {"eplus", "n", "muplus"}.issubset(particle_cases)
        else "PASS_PROMPT511_UPPER_W_SHADOW_L1_PROXY_PARTIAL"
    )
    payload = {
        "status": status,
        "claim_level": "prompt-only upper-W-shadow design smoke; not rate authority",
        "line_window_keV": list(proxy.LINE_WINDOW),
        "active_veto_threshold_keV": proxy.ACTIVE_VETO_THRESHOLD_KEV,
        "reject_policy": reject_policy,
        "particle_cases": particle_cases,
        "particle_ratios": particle_ratios,
        "total_prompt_projection": projection,
        "limitations": [
            "Only completed upper-W-shadow prompt particle runs are parsed.",
            "The current baseline is replayed from the official Step05 event_catalog cache.",
            "No delayed transport, no rebuilt delayed source, no science signal, and no mission time axis are included.",
            "The added W is passive and has no native active-veto detector entries.",
            "W-only candidates can reduce e+ while raising neutron prompt or activation; n/mu and isotope-record gates are mandatory.",
        ],
    }
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text(markdown(payload) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "summary": rel(SUMMARY_JSON), "report": rel(SUMMARY_MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
