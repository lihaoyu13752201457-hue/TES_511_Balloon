#!/usr/bin/env python3
"""Build and summarize BGO same-envelope focused Step09 EventList transport.

This is an engineering-only wrapper for HARNESS_20260624.  It reuses the
current f10m A1 v3p5 optical EventList, but replays it through the matched BGO
same-envelope detector geometry.  Outputs stay under the requested BGO stage
directory and do not update any project authority artifacts.
"""

from __future__ import annotations

import argparse
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
BGO_GEO = (
    ROOT
    / "engineering"
    / "background_validation_20260624"
    / "04_bgo_variant"
    / "geometry_bgo_same_envelope"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_bgo_same_envelope_megalib_proxy.geo.setup"
)
BASELINE_GEO_FRAGMENT = "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
FIX5_GEO_FRAGMENT = "DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy"
BASE_STEP09 = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs_f10m_a1_v3p5"
BASE_SUMMARY = BASE_STEP09 / "step09_optics_bridge_summary.json"
EVENTLIST = BASE_STEP09 / "eventlists" / "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def paths(stage_dir: Path, label: str) -> dict[str, Path]:
    out = stage_dir / "step09_focus"
    run_dir = out / "run"
    run_name = f"Opticsim_laue_f10m_a1_{label}"
    source = run_dir / f"{run_name}.source"
    prefix = run_dir / run_name
    return {
        "out": out,
        "run_dir": run_dir,
        "run_name": Path(run_name),
        "source": source,
        "prefix": prefix,
        "sim": prefix.with_suffix(".inc1.id1.sim.gz"),
        "summary_json": out / "step09_focus_summary.json",
        "summary_md": out / "STEP09_FOCUS.md",
        "log": out / "cosima_focus.log",
    }


def source_text(stage_dir: Path, label: str, triggers: int, seed: int) -> str:
    p = paths(stage_dir, label)
    run_name = p["run_name"].as_posix()
    return f"""# Auto-generated BGO same-envelope focused EventList transport source.
# Replays the current f10m A1 v3p5 Step09 EventList through BGO same-envelope geometry.
# Engineering-only output for HARNESS_20260624.

Version 1
Geometry {rel(BGO_GEO)}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {int(seed)}

Run {run_name}
{run_name}.FileName {rel(p["prefix"])}
{run_name}.Triggers {int(triggers)}
{run_name}.Source {run_name}_EventList

{run_name}_EventList.EventList {rel(EVENTLIST)}
"""


def write_summary(stage_dir: Path, label: str, payload: dict[str, Any]) -> None:
    p = paths(stage_dir, label)
    write_json(p["summary_json"], payload)
    lines = [
        "# BGO Same-Envelope Step09 Focused EventList Transport",
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
                f"- SIM geometry: `{transport['geometry']}`",
            ]
        )
    lines.extend(["", "Boundary:"])
    lines.extend(f"- {item}" for item in payload.get("boundary", []))
    lines.append("")
    p["summary_md"].write_text("\n".join(lines), encoding="utf-8")


def build_source(stage_dir: Path, label: str, seed: int) -> dict[str, Any]:
    base = load_json(BASE_SUMMARY)
    bridge = base.get("bridge", {})
    rows = int(bridge["rows_written"])
    p = paths(stage_dir, label)
    p["run_dir"].mkdir(parents=True, exist_ok=True)
    p["out"].mkdir(parents=True, exist_ok=True)
    p["source"].write_text(source_text(stage_dir, label, rows, seed), encoding="utf-8")
    body = p["source"].read_text(encoding="utf-8", errors="ignore")
    payload = {
        "status": "PASS_BGO_ENGINEERING_STEP09_FOCUS_SOURCE_READY",
        "claim_level": "BGO_ENGINEERING_FOCUSED_EVENTLIST_SOURCE_READY_NOT_STEP05_AUTHORITY",
        "label": label,
        "generated_at_utc": now_utc(),
        "source": rel(p["source"]),
        "geometry": rel(BGO_GEO),
        "eventlist": rel(EVENTLIST),
        "outfile_prefix": rel(p["prefix"]),
        "triggers": rows,
        "seed": int(seed),
        "base_step09_summary": rel(BASE_SUMMARY),
        "base_step09_status": base.get("status"),
        "base_bridge": bridge,
        "source_audit": {
            "contains_bgo_geometry": rel(BGO_GEO) in body,
            "contains_forbidden_baseline_geometry": BASELINE_GEO_FRAGMENT in body,
            "contains_forbidden_fix5_geometry": FIX5_GEO_FRAGMENT in body,
        },
        "boundary": [
            "This source replays the current f10m A1 v3p5 focused EventList through BGO same-envelope geometry.",
            "It is not a BGO detector-response authority until Cosima transport is summarized and Step05 consumes this BGO signal SIM.",
        ],
    }
    write_summary(stage_dir, label, payload)
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


def summarize_transport(stage_dir: Path, label: str) -> dict[str, Any]:
    p = paths(stage_dir, label)
    if not p["summary_json"].exists():
        build_source(stage_dir=stage_dir, label=label, seed=260617)
    payload = load_json(p["summary_json"])
    transport = inspect_sim(p["sim"])
    problems: list[str] = []
    triggers = int(payload["triggers"])
    geom_text = str(transport["geometry"])
    if not transport["exists"]:
        problems.append("missing_focus_transport_sim")
    if int(transport["SE"]) != int(transport["ID"]):
        problems.append("SE_ID_mismatch")
    if int(transport["SE"]) != triggers:
        problems.append("stored_events_do_not_match_eventlist_triggers")
    if rel(BGO_GEO) not in geom_text and str(BGO_GEO) not in geom_text:
        problems.append("transport_geometry_not_bgo_same_envelope")
    if BASELINE_GEO_FRAGMENT in geom_text:
        problems.append("transport_geometry_contains_forbidden_baseline")
    if FIX5_GEO_FRAGMENT in geom_text:
        problems.append("transport_geometry_contains_forbidden_fix5")
    payload["updated_at_utc"] = now_utc()
    payload["focused_transport"] = transport
    payload["problems"] = problems
    if problems:
        payload["status"] = "FAIL_BGO_ENGINEERING_STEP09_FOCUS_TRANSPORT"
    else:
        payload["status"] = "PASS_BGO_ENGINEERING_STEP09_FOCUS_TRANSPORT"
        payload["claim_level"] = "BGO_ENGINEERING_FOCUSED_EVENTLIST_TRANSPORT_NOT_STEP05_AUTHORITY"
        payload["boundary"] = [
            "Focused EventList transport through BGO same-envelope geometry passed.",
            "Step05 detector response must consume this BGO signal SIM together with BGO prompt and delayed SIMs before quoting signal keep or sensitivity.",
        ]
    write_summary(stage_dir, label, payload)
    print(json.dumps({"status": payload["status"], "problems": problems, "focused_transport": transport}, indent=2))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage-dir", type=Path, required=True)
    parser.add_argument("--label", default="bgo_same_envelope_p2_focus")
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-source")
    build.add_argument("--seed", type=int, default=260617)
    sub.add_parser("summarize-transport")
    args = parser.parse_args()
    stage_dir = args.stage_dir.resolve()
    if args.cmd == "build-source":
        build_source(stage_dir=stage_dir, label=args.label, seed=args.seed)
    elif args.cmd == "summarize-transport":
        payload = summarize_transport(stage_dir=stage_dir, label=args.label)
        return 0 if str(payload["status"]).startswith("PASS") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
