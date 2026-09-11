#!/usr/bin/env python3
"""Analyze S2b e+/n equal-stat prompt and atm511 sidecar against S1."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
PROMPT_PROXY = ROOT / "old/reports/prompt511_repack_smoke_20260617/build_prompt511_repack_l1_proxy.py"
STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
S1_PROMPT_DIR = ROOT / "runs/geometry_optimization_20260704/step02_instant_geo_opt_s1_bpe_w5_fullstat_v1"
S2B_PROMPT_DIR = ROOT / "runs/geometry_optimization_20260704/s2b_cryo_shell_45deg_eqstats_prompt_eplus_n_20260708"
S2B_ATM_SUMMARY = WORK / "s2b_atm511_sidecar_3m_summary.json"
S1_ATM_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708"
    / "p2_geo_opt_s1_bpe_w5_atm511_sidecar_summary.json"
)
SUMMARY_JSON = WORK / "s2b_eqstats_background_comparison_summary.json"
SUMMARY_CSV = WORK / "s2b_eqstats_background_comparison.csv"
SUMMARY_MD = WORK / "s2b_eqstats_background_comparison.md"

ACTIVE_VETO_THRESHOLD_KEV = 50.0
TAGS = ("eplus", "n")
STAGES = (
    ("raw", "raw_rate_s-1", "raw_events"),
    ("active_veto_pass", "active_veto_pass_rate_s-1", "active_veto_pass_events"),
    ("side_compton_fov_pass", "side_compton_fov_pass_rate_s-1", "side_compton_fov_pass_events"),
)


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
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


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "component",
        "stage",
        "s1_events",
        "s2b_events",
        "s1_rate_cps",
        "s2b_rate_cps",
        "s2b_over_s1_ratio",
        "counting_only_1sigma",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def is_active_veto_volume(vol: str) -> bool:
    upper = str(vol).upper()
    return (
        upper.startswith("CSI_")
        or "ACTIVE_SHIELD" in upper
        or "CEBR3" in upper
        or "BGO" in upper
        or upper.startswith("GEOOPT_S1_PLASTICFULLWRAP")
        or upper.startswith("GEOOPT_S2B_CRYOSHELL_PLASTIC")
    )


def configure_proxy(proxy, step05) -> None:
    step05.ROOT = ROOT
    step05.STEP09_SUMMARY = (
        ROOT
        / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
        / "step09_optics_bridge_summary.json"
    )
    proxy.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    proxy.TP_ACTIVE_FILTER_RE = (
        r"^(ID |SE$|CC HIT "
        r"(TP_L|CsI_|.*ACTIVE_SHIELD|.*CEBR3|.*BGO|"
        r"GeoOpt_S1_PlasticFullWrap|GeoOpt_S2B_CryoShell_Plastic))"
    )
    step05.is_v3p5_active_veto_volume = is_active_veto_volume


def ratio(num: float, den: float) -> float | None:
    return num / den if den > 0.0 else None


def poisson_ratio_sigma(num_events: int, den_events: int, value: float | None) -> float | None:
    if value is None or num_events <= 0 or den_events <= 0:
        return None
    return value * math.sqrt(1.0 / num_events + 1.0 / den_events)


def compare_rows(component: str, s1: dict[str, Any], s2b: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for stage, rate_key, event_key in STAGES:
        s1_rate = float(s1[rate_key])
        s2b_rate = float(s2b[rate_key])
        s1_events = int(s1[event_key])
        s2b_events = int(s2b[event_key])
        value = ratio(s2b_rate, s1_rate)
        rows.append(
            {
                "component": component,
                "stage": stage,
                "s1_events": s1_events,
                "s2b_events": s2b_events,
                "s1_rate_cps": s1_rate,
                "s2b_rate_cps": s2b_rate,
                "s2b_over_s1_ratio": value,
                "counting_only_1sigma": poisson_ratio_sigma(s2b_events, s1_events, value),
            }
        )
    return rows


def prompt_cases() -> dict[str, Any]:
    proxy = load_module("s2b_eqstats_prompt_proxy", PROMPT_PROXY)
    step05 = load_module("s2b_eqstats_step05", STEP05_SCRIPT)
    configure_proxy(proxy, step05)
    disk = step05.side_entry_disk()
    reject_policy = "keep"

    out = {}
    for tag in TAGS:
        out[tag] = {
            "s1": proxy.summarize_prompt_dir(step05, S1_PROMPT_DIR, disk, reject_policy, tag=tag),
            "s2b": proxy.summarize_prompt_dir(step05, S2B_PROMPT_DIR, disk, reject_policy, tag=tag),
        }
    return out


def atm_cases() -> dict[str, Any] | None:
    if not S2B_ATM_SUMMARY.exists():
        return None
    s1 = load_json(S1_ATM_SUMMARY)
    s2b = load_json(S2B_ATM_SUMMARY)
    if s2b.get("status") != "PASS_S2B_ATM511_4PI_SIDECAR_REPLAY":
        return None
    return {
        "s1": s1,
        "s2b": s2b,
        "comparison": s2b["relative_to_s1"]["w2_510p58_511p42"],
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# S2b Equal-Stat Background Comparison",
        "",
        f"Prompt source radius: `60 cm`, source sphere center: `(5, 0, 9) cm` in S2b `.geo.setup`.",
        f"Active-veto threshold: `{ACTIVE_VETO_THRESHOLD_KEV:g} keV`.",
        "Active-veto volumes include legacy active volumes plus `GeoOpt_S1_PlasticFullWrap*` and `GeoOpt_S2B_CryoShell_Plastic*`.",
        "",
        "| component | stage | S1 events | S2b events | S1 cps | S2b cps | S2b/S1 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in payload["comparison_rows"]:
        ratio_value = row["s2b_over_s1_ratio"]
        sigma = row["counting_only_1sigma"]
        if ratio_value is None:
            ratio_text = ""
        elif sigma is None:
            ratio_text = f"{ratio_value:.6g}"
        else:
            ratio_text = f"{ratio_value:.6g} +/- {sigma:.3g}"
        lines.append(
            f"| {row['component']} | {row['stage']} | {row['s1_events']} | {row['s2b_events']} | "
            f"{row['s1_rate_cps']:.6g} | {row['s2b_rate_cps']:.6g} | {ratio_text} |"
        )
    lines.extend(
        [
            "",
            "Scope notes:",
            "",
            "- This is a prompt e+/n plus atmospheric-511 geometry comparison, not a full Step05/06/08 sensitivity promotion.",
            "- Delayed activation and signal throughput are not rerun in this package.",
            "- Counting uncertainties above are simple selected-event Poisson errors only.",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    prompt = prompt_cases()
    rows: list[dict[str, Any]] = []
    for tag, pair in prompt.items():
        rows.extend(compare_rows(tag, pair["s1"]["summary"], pair["s2b"]["summary"]))

    atm = atm_cases()
    if atm is not None:
        for stage, rate_key, event_key in (
            ("raw", "raw_rate_cps", "raw_events"),
            ("active_veto_pass", "active_rate_cps", "active_veto_pass_events"),
            ("side_compton_fov_pass", "final_rate_cps", "side_compton_fov_pass_events"),
        ):
            s1_w2 = atm["s1"]["windows"]["w2_510p58_511p42"]
            s2b_w2 = atm["s2b"]["windows"]["w2_510p58_511p42"]
            value = ratio(float(s2b_w2[rate_key]), float(s1_w2[rate_key]))
            rows.append(
                {
                    "component": "atm511",
                    "stage": stage,
                    "s1_events": int(s1_w2[event_key]),
                    "s2b_events": int(s2b_w2[event_key]),
                    "s1_rate_cps": float(s1_w2[rate_key]),
                    "s2b_rate_cps": float(s2b_w2[rate_key]),
                    "s2b_over_s1_ratio": value,
                    "counting_only_1sigma": poisson_ratio_sigma(
                        int(s2b_w2[event_key]), int(s1_w2[event_key]), value
                    ),
                }
            )

    payload = {
        "status": "PASS_S2B_EQSTATS_BACKGROUND_COMPARISON" if atm is not None else "PASS_PROMPT_ONLY_ATM_PENDING",
        "inputs": {
            "s1_prompt_dir": rel(S1_PROMPT_DIR),
            "s2b_prompt_dir": rel(S2B_PROMPT_DIR),
            "s1_atm_summary": rel(S1_ATM_SUMMARY),
            "s2b_atm_summary": rel(S2B_ATM_SUMMARY),
        },
        "normalization": {
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "active_veto_rule": (
                "legacy active tokens + GeoOpt_S1_PlasticFullWrap* + "
                "GeoOpt_S2B_CryoShell_Plastic*"
            ),
        },
        "prompt_cases": prompt,
        "atm511_case": atm,
        "comparison_rows": rows,
    }
    write_json(SUMMARY_JSON, payload)
    write_csv(SUMMARY_CSV, rows)
    SUMMARY_MD.write_text(markdown(payload) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON), "csv": rel(SUMMARY_CSV)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
