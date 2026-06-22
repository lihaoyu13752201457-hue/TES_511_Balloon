#!/usr/bin/env python3
"""Build a prompt Step05-like all-particle gross check for upper-W-shadow."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_upper_w_shadow_20260620"
BASE_PROXY = ROOT / "outputs/reports/prompt511_repack_smoke_20260617/build_prompt511_repack_l1_proxy.py"
HELPER_PROXY = WORK / "build_prompt511_upper_w_shadow_l1_proxy.py"
ALLPARTICLE_DIR = WORK / "runs/upper_w_shadow_allparticle_g1m_r1_promptonly"
SUMMARY_JSON = WORK / "upper_w_shadow_allparticle_smoke_l1_proxy_summary.json"
SUMMARY_MD = WORK / "upper_w_shadow_allparticle_smoke_l1_proxy_summary.md"


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


def tag_sort_key(tag: str) -> tuple[int, str]:
    order = ["alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p"]
    return (order.index(tag) if tag in order else len(order), tag)


def selected_tags(prompt_dir: Path) -> list[str]:
    norm = json.loads((prompt_dir / "normalization.json").read_text(encoding="utf-8"))
    tags = norm.get("selected_particles")
    if tags:
        return sorted([str(tag).lower() for tag in tags], key=tag_sort_key)
    found = {path.name.split("_")[1].lower() for path in prompt_dir.glob("Background_*_fullsphere20_*.sim.gz")}
    return sorted(found, key=tag_sort_key)


def compact_by_tag(rows: dict[str, Any]) -> dict[str, Any]:
    compact = {}
    for tag, row in sorted(rows.items(), key=lambda item: tag_sort_key(item[0])):
        s = row["summary"]
        compact[tag] = {
            "generated_events_seen": s["generated_events_seen"],
            "tes_events_kept": s["tes_events_kept"],
            "raw_events": s["raw_events"],
            "raw_rate_s-1": s["raw_rate_s-1"],
            "active_veto_pass_events": s["active_veto_pass_events"],
            "active_veto_pass_rate_s-1": s["active_veto_pass_rate_s-1"],
            "side_compton_fov_pass_events": s["side_compton_fov_pass_events"],
            "side_compton_fov_pass_rate_s-1": s["side_compton_fov_pass_rate_s-1"],
            "active_veto_survival_fraction": s["active_veto_survival_fraction"],
            "side_compton_fov_survival_fraction_vs_active": s[
                "side_compton_fov_survival_fraction_vs_active"
            ],
            "side_compton_class_counts": s["side_compton_class_counts"],
        }
    return compact


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Upper W Shadow All-Particle Prompt Smoke L1-like Proxy",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This is a low-stat all-particle gross check. It is used only to catch",
        "unexpected prompt channels outside the high-stat eplus/n/muplus projection.",
        "",
        f"Run summary: `{payload['run_summary']}`.",
        f"Window: `{payload['line_window_keV'][0]} <= TES_total_keV < {payload['line_window_keV'][1]}`.",
        f"Active-veto threshold: `{payload['active_veto_threshold_keV']} keV`.",
        "",
        "| tag | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for tag, row in payload["by_tag"].items():
        lines.append(
            f"| {tag} | {row['raw_events']} | {row['raw_rate_s-1']:.6g} | "
            f"{row['active_veto_pass_events']} | {row['active_veto_pass_rate_s-1']:.6g} | "
            f"{row['side_compton_fov_pass_events']} | {row['side_compton_fov_pass_rate_s-1']:.6g} |"
        )
    lines.extend(
        [
            "",
            f"- all-particle smoke L1-like total: `{payload['allparticle_l1_total_s-1']:.6g} cps`.",
            f"- nonzero L1-like tags: `{', '.join(payload['nonzero_l1_tags']) or '(none)'}`.",
            f"- unexpected nonzero tags outside eplus/n/muplus: "
            f"`{', '.join(payload['unexpected_nonzero_l1_tags']) or '(none)'}`.",
            "",
            "Interpretation:",
            "",
            "- The high-stat eplus/n/muplus prompt proxy remains the central result.",
            "- This low-stat screen is not an upper limit for channels with zero selected events.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    proxy = load_module("prompt511_repack_l1_proxy_base_allparticle_upper_w", BASE_PROXY)
    helper = load_module("prompt511_upper_w_shadow_l1_helper", HELPER_PROXY)
    helper.install_prompt_only_rate_fallback(proxy)
    step05 = load_module(
        "build_v3p5_centerfinger_step05_l1_response_allparticle_upper_w",
        ROOT / "code/tools/build_v3p5_centerfinger_step05_l1_response.py",
    )
    disk = step05.side_entry_disk()
    reject_policy = "keep"

    rows = {}
    for tag in selected_tags(ALLPARTICLE_DIR):
        if proxy.repack_dir_ready(ALLPARTICLE_DIR, tag):
            rows[tag] = proxy.summarize_prompt_dir(step05, ALLPARTICLE_DIR, disk, reject_policy, tag=tag)
    by_tag = compact_by_tag(rows)
    nonzero = [
        tag
        for tag, row in by_tag.items()
        if float(row["side_compton_fov_pass_rate_s-1"]) > 0.0
    ]
    payload = {
        "status": "PASS_UPPER_W_SHADOW_ALLPARTICLE_SMOKE_L1_PROXY",
        "claim_level": "all-particle prompt gross check; not rate authority",
        "source_run": rel(ALLPARTICLE_DIR),
        "run_summary": rel(ALLPARTICLE_DIR / "run_summary.md"),
        "line_window_keV": list(proxy.LINE_WINDOW),
        "active_veto_threshold_keV": proxy.ACTIVE_VETO_THRESHOLD_KEV,
        "reject_policy": reject_policy,
        "by_tag": by_tag,
        "allparticle_l1_total_s-1": sum(
            float(row["side_compton_fov_pass_rate_s-1"]) for row in by_tag.values()
        ),
        "nonzero_l1_tags": nonzero,
        "unexpected_nonzero_l1_tags": [tag for tag in nonzero if tag not in {"eplus", "n", "muplus"}],
    }
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON), "report": rel(SUMMARY_MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
