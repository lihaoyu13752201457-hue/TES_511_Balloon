#!/usr/bin/env python3
"""Build and summarize Bgo_sample focused Step09 EventList transport.

The optical phase-space authority remains the existing f10m A1 v3p5 EventList.
This script replays that EventList through the Bgo_sample geometry so BGO
downstream response work does not borrow the CsI focused-signal SIM.
"""

from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BGO = ROOT / "Bgo_sample"
GEOMETRY = BGO / "Bgo_sample.geo.setup"
BASE_STEP09 = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs_f10m_a1_v3p5"
BASE_SUMMARY = BASE_STEP09 / "step09_optics_bridge_summary.json"
EVENTLIST = BASE_STEP09 / "eventlists" / "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
RUN_DIR = ROOT / "runs" / "step09_bgo_sample_focus"
RUN_NAME = "Opticsim_laue_f10m_a1_bgo_sample"
SOURCE = RUN_DIR / f"{RUN_NAME}.source"
PREFIX = RUN_DIR / RUN_NAME
SIM = PREFIX.with_suffix(".inc1.id1.sim.gz")
SUMMARY_JSON = BGO / "step09_focus_summary.json"
SUMMARY_MD = BGO / "STEP09_FOCUS.md"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def source_text(triggers: int, seed: int) -> str:
    return f"""# Auto-generated Bgo_sample focused EventList transport source.
# Replays the current f10m A1 v3p5 Step09 EventList through Bgo_sample.

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
        "status": "PASS_BGO_SAMPLE_STEP09_FOCUS_SOURCE_READY",
        "claim_level": "BGO_SAMPLE_STEP09_FOCUSED_EVENTLIST_SOURCE_READY_NOT_RESPONSE_AUTHORITY",
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
            "This source replays the current f10m A1 v3p5 focused EventList through Bgo_sample geometry.",
            "It is not a BGO detector-response authority until Cosima transport is summarized and Step05 consumes this BGO signal SIM.",
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
                info["geometry"] = raw.strip().split(" ", 1)[1]
    return info


def summarize_transport() -> dict[str, Any]:
    if not SUMMARY_JSON.exists():
        build_source(seed=260615)
    payload = load_json(SUMMARY_JSON)
    transport = inspect_sim(SIM)
    problems = []
    triggers = int(payload["triggers"])
    if not transport["exists"]:
        problems.append("missing_focus_transport_sim")
    if int(transport["SE"]) != int(transport["ID"]):
        problems.append("SE_ID_mismatch")
    if int(transport["SE"]) != triggers:
        problems.append("stored_events_do_not_match_eventlist_triggers")
    if "Bgo_sample/Bgo_sample.geo.setup" not in str(transport["geometry"]):
        problems.append("transport_geometry_not_Bgo_sample")
    payload["focused_transport"] = transport
    payload["problems"] = problems
    if problems:
        payload["status"] = "FAIL_BGO_SAMPLE_STEP09_FOCUS_TRANSPORT"
    else:
        payload["status"] = "PASS_BGO_SAMPLE_STEP09_FOCUS_TRANSPORT"
        payload["claim_level"] = "BGO_SAMPLE_STEP09_FOCUSED_EVENTLIST_TRANSPORT_NOT_STEP05_AUTHORITY"
        payload["boundary"] = [
            "Focused EventList transport through Bgo_sample geometry passed.",
            "Step05 detector response must consume this BGO signal SIM together with BGO prompt and delayed SIMs before quoting rates.",
        ]
    write_summary(payload)
    print(json.dumps({"status": payload["status"], "problems": problems, "focused_transport": transport}, indent=2))
    return payload


def write_summary(payload: dict[str, Any]) -> None:
    write_json(SUMMARY_JSON, payload)
    lines = [
        "# Bgo_sample Step09 Focused EventList Transport",
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
    lines.extend(["", "Boundary:"])
    lines.extend(f"- {item}" for item in payload.get("boundary", []))
    lines.append("")
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-source")
    build.add_argument("--seed", type=int, default=260615)
    sub.add_parser("summarize-transport")
    args = parser.parse_args()
    if args.cmd == "build-source":
        build_source(seed=args.seed)
    elif args.cmd == "summarize-transport":
        payload = summarize_transport()
        return 0 if str(payload["status"]).startswith("PASS") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
