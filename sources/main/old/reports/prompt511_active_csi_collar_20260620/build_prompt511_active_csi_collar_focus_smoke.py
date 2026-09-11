#!/usr/bin/env python3
"""Build and summarize active-CsI-collar focused EventList transport smoke."""

from __future__ import annotations

import argparse
import gzip
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_active_csi_collar_20260620"
GEOMETRY = (
    WORK
    / "geometry_active_csi_collar"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_active_csi_collar_r4p25_5p95.geo.setup"
)
BASE_PROXY = WORK / "build_prompt511_active_csi_collar_l1_proxy.py"
BASE_REPACK_PROXY = ROOT / "outputs/reports/prompt511_repack_smoke_20260617/build_prompt511_repack_l1_proxy.py"
BASE_STEP09 = ROOT / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
BASE_SUMMARY = BASE_STEP09 / "step09_optics_bridge_summary.json"
EVENTLIST = BASE_STEP09 / "eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
CURRENT_FOCUS_SIM = ROOT / "runs/step09_optics_bridge/Opticsim_laue_f10m_a1_v3p5_centerfinger.inc1.id1.sim.gz"
RUN_DIR = WORK / "runs/active_csi_collar_focus_smoke"
RUN_NAME = "Opticsim_laue_f10m_a1_prompt511_active_csi_collar"
SOURCE = RUN_DIR / f"{RUN_NAME}.source"
PREFIX = RUN_DIR / RUN_NAME
SIM = PREFIX.with_suffix(".inc1.id1.sim.gz")
SUMMARY_JSON = WORK / "prompt511_active_csi_collar_focus_smoke_summary.json"
SUMMARY_MD = WORK / "prompt511_active_csi_collar_focus_smoke_summary.md"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def source_text(triggers: int, seed: int) -> str:
    return f"""# Auto-generated prompt-511 active-CsI-collar focused EventList smoke.
# Replays the current f10m A1 v3p5 Step09 EventList through active-CsI-collar geometry.

Version 1
Geometry {rel(GEOMETRY)}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {int(seed)}

Run {RUN_NAME}
{RUN_NAME}.FileName {rel(PREFIX)}
{RUN_NAME}.Triggers {int(triggers)}
{RUN_NAME}.Source {RUN_NAME}_EventList

{RUN_NAME}_EventList.EventList {rel(EVENTLIST)}
"""


def build_source(seed: int) -> dict[str, Any]:
    base = load_json(BASE_SUMMARY)
    rows = int(base["bridge"]["rows_written"])
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE.write_text(source_text(rows, seed), encoding="utf-8")
    payload = {
        "status": "PASS_PROMPT511_ACTIVE_CSI_COLLAR_FOCUS_SOURCE_READY",
        "claim_level": "focused EventList source for active-CsI-collar signal smoke; not response authority",
        "source": rel(SOURCE),
        "geometry": rel(GEOMETRY),
        "eventlist": rel(EVENTLIST),
        "outfile_prefix": rel(PREFIX),
        "triggers": rows,
        "seed": int(seed),
        "base_step09_summary": rel(BASE_SUMMARY),
        "base_step09_status": base.get("status"),
        "base_bridge": base.get("bridge", {}),
        "boundary": [
            "This source replays the current f10m A1 v3p5 focused EventList through the active-CsI-collar geometry.",
            "It is a signal-clipping smoke only; it is not a prompt, delayed, Step06, Step07, or Step08 authority.",
        ],
    }
    write_summary(payload)
    print(json.dumps({"status": payload["status"], "source": payload["source"], "triggers": rows}, indent=2))
    return payload


def inspect_sim(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "SE": 0,
        "ID": 0,
        "TS": 0,
        "TE_s": None,
        "geometry": "",
    }
    if not path.exists():
        return info
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            if raw.startswith("SE"):
                info["SE"] += 1
            elif raw.startswith("ID"):
                info["ID"] += 1
            elif raw.startswith("TS"):
                info["TS"] += 1
            elif raw.startswith("TE"):
                parts = raw.split()
                if len(parts) >= 2:
                    info["TE_s"] = float(parts[1])
            elif raw.startswith("Geometry "):
                info["geometry"] = raw.strip().split(" ", 1)[1].strip()
    return info


def summarize_signal_response(path: Path, proxy, step05) -> dict[str, Any]:
    disk = step05.side_entry_disk()
    row = proxy.summarize_sim_stream(step05, path, 1.0, disk, "keep")
    summary = row.copy()
    for key in ("raw_rate_s-1", "active_veto_pass_rate_s-1", "side_compton_fov_pass_rate_s-1"):
        summary.pop(key, None)
    return summary


def summarize_transport_and_signal() -> dict[str, Any]:
    if not SUMMARY_JSON.exists():
        build_source(seed=260620)
    payload = load_json(SUMMARY_JSON)
    transport = inspect_sim(SIM)
    current_transport = inspect_sim(CURRENT_FOCUS_SIM)
    problems: list[str] = []
    triggers = int(payload["triggers"])
    if not transport["exists"]:
        problems.append("missing_active_csi_collar_focus_transport_sim")
    if int(transport["SE"]) != int(transport["ID"]):
        problems.append("active_csi_collar_SE_ID_mismatch")
    if int(transport["SE"]) != triggers:
        problems.append("active_csi_collar_stored_events_do_not_match_eventlist_triggers")
    if rel(GEOMETRY) not in str(transport["geometry"]) and str(GEOMETRY) not in str(transport["geometry"]):
        problems.append("active_csi_collar_transport_geometry_mismatch")

    payload["focused_transport"] = transport
    payload["current_focused_transport"] = current_transport
    if transport["exists"]:
        proxy = load_module("prompt511_focus_smoke_base_proxy", BASE_REPACK_PROXY)
        active_proxy = load_module("prompt511_active_csi_collar_l1_proxy_for_focus", BASE_PROXY)
        active_proxy.install_prompt_only_rate_fallback(proxy)
        step05 = load_module(
            "build_v3p5_centerfinger_step05_l1_response_focus_smoke",
            ROOT / "code/tools/build_v3p5_centerfinger_step05_l1_response.py",
        )
        active_summary = summarize_signal_response(SIM, proxy, step05)
        current_summary = summarize_signal_response(CURRENT_FOCUS_SIM, proxy, step05)
        payload["focused_signal_proxy"] = {
            "line_window_keV": list(proxy.LINE_WINDOW),
            "active_veto_threshold_keV": proxy.ACTIVE_VETO_THRESHOLD_KEV,
            "current_baseline": current_summary,
            "active_csi_collar": active_summary,
            "ratios_active_over_current": {
                "raw_events": active_summary["raw_events"] / max(current_summary["raw_events"], 1),
                "active_veto_pass_events": active_summary["active_veto_pass_events"]
                / max(current_summary["active_veto_pass_events"], 1),
                "side_compton_fov_pass_events": active_summary["side_compton_fov_pass_events"]
                / max(current_summary["side_compton_fov_pass_events"], 1),
            },
        }
    payload["problems"] = problems
    if problems:
        payload["status"] = "FAIL_PROMPT511_ACTIVE_CSI_COLLAR_FOCUS_SMOKE"
    else:
        payload["status"] = "PASS_PROMPT511_ACTIVE_CSI_COLLAR_FOCUS_SMOKE"
        payload["claim_level"] = "focused EventList transport plus Step05-like signal-retention smoke; not mission authority"
        payload["boundary"] = [
            "Focused EventList transport through active-CsI-collar geometry passed.",
            "The signal-retention proxy uses the same W2 line window, 50 keV active-veto threshold, and side-Compton/FoV function as the prompt diagnostics.",
            "This is not a Step05/06/07/08 authority because prompt, delayed, and signal are not rebuilt together on a common chain.",
        ]
    write_summary(payload)
    print(json.dumps({"status": payload["status"], "problems": problems, "focused_transport": transport}, indent=2))
    return payload


def write_summary(payload: dict[str, Any]) -> None:
    write_json(SUMMARY_JSON, payload)
    lines = [
        "# Prompt-511 Active-CsI Collar Focused EventList Smoke",
        "",
        f"Status: `{payload['status']}`.",
        "",
        f"- source: `{payload['source']}`",
        f"- geometry: `{payload['geometry']}`",
        f"- EventList: `{payload['eventlist']}`",
        f"- outfile prefix: `{payload['outfile_prefix']}`",
        f"- triggers: `{payload['triggers']}`",
        f"- seed: `{payload['seed']}`",
        f"- base Step09 status: `{payload.get('base_step09_status', '')}`",
    ]
    transport = payload.get("focused_transport")
    if transport:
        lines.extend(
            [
                f"- focused sim: `{transport['path']}`",
                f"- SE/ID/TS: `{transport['SE']}/{transport['ID']}/{transport['TS']}`",
                f"- TE: `{transport['TE_s']}` s",
            ]
        )
    proxy = payload.get("focused_signal_proxy")
    if proxy:
        cur = proxy["current_baseline"]
        var = proxy["active_csi_collar"]
        ratios = proxy["ratios_active_over_current"]
        lines.extend(
            [
                "",
                "Step05-like focused-signal proxy:",
                "",
                "| case | generated | TES kept | W2 raw | active pass | side-Compton/FoV pass |",
                "|---|---:|---:|---:|---:|---:|",
                f"| current_baseline | {cur['generated_events_seen']} | {cur['tes_events_kept']} | {cur['raw_events']} | {cur['active_veto_pass_events']} | {cur['side_compton_fov_pass_events']} |",
                f"| active_csi_collar | {var['generated_events_seen']} | {var['tes_events_kept']} | {var['raw_events']} | {var['active_veto_pass_events']} | {var['side_compton_fov_pass_events']} |",
                "",
                f"- active/current W2 raw event ratio: `{ratios['raw_events']:.6g}`.",
                f"- active/current active-veto-pass ratio: `{ratios['active_veto_pass_events']:.6g}`.",
                f"- active/current side-Compton/FoV-pass ratio: `{ratios['side_compton_fov_pass_events']:.6g}`.",
            ]
        )
    lines.extend(["", "Boundary:"])
    lines.extend(f"- {item}" for item in payload.get("boundary", []))
    lines.append("")
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-source")
    build.add_argument("--seed", type=int, default=260620)
    sub.add_parser("summarize")
    args = parser.parse_args()
    if args.cmd == "build-source":
        build_source(seed=args.seed)
    elif args.cmd == "summarize":
        payload = summarize_transport_and_signal()
        return 0 if str(payload["status"]).startswith("PASS") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
