#!/usr/bin/env python3
"""Build and summarize fix5 focused Step09 EventList transport.

The optical phase-space authority remains the existing f10m A1 v3p5 EventList.
This replays that EventList through the fix5 detector geometry so Step05 can
consume a fix5-geometry focused signal SIM instead of the v3p5 placeholder.
"""

from __future__ import annotations

import argparse
import gzip
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LABEL = "fix5_fullstat_v2_exactpos_m50000_s260613"
FIX5_GEO = (
    ROOT
    / "outputs"
    / "geometry"
    / "DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
BASELINE_GEO = (
    "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
BASE_STEP09 = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / "outputs_f10m_a1_v3p5"
BASE_SUMMARY = BASE_STEP09 / "step09_optics_bridge_summary.json"
EVENTLIST = BASE_STEP09 / "eventlists" / "Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat"
OUT = ROOT / "stepwise_maintenance" / "step09_optics_bridge" / f"outputs_{LABEL}"
RUN_DIR = ROOT / "runs" / f"step09_focus_{LABEL}"
RUN_NAME = "Opticsim_laue_f10m_a1_fix5_fullstat_v2_exactpos_m50000_s260613"
SOURCE = RUN_DIR / f"{RUN_NAME}.source"
PREFIX = RUN_DIR / RUN_NAME
SIM = PREFIX.with_suffix(".inc1.id1.sim.gz")
LOG = OUT / "cosima_full.log"
SUMMARY_JSON = OUT / "step09_focus_summary.json"
SUMMARY_MD = OUT / "STEP09_FOCUS.md"
SOURCE_MANIFEST = ROOT / "outputs" / "reports" / "fix5_fullstat_v2" / "fix5_source_manifest.json"
VERIFIER = ROOT / "outputs" / "reports" / "fix5_fullstat_v2" / "fix5_verification_verdict.json"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def upsert_row(rows: list[dict[str, Any]], key: str, value: str, row: dict[str, Any]) -> None:
    for index, existing in enumerate(rows):
        if existing.get(key) == value:
            rows[index] = row
            return
    rows.append(row)


def update_contract_artifacts(payload: dict[str, Any]) -> None:
    source_body = SOURCE.read_text(encoding="utf-8", errors="ignore")
    manifest = load_json(SOURCE_MANIFEST)
    signal_card = {
        "path": rel(SOURCE),
        "source_family": "focused_signal_eventlist",
        "geometry_setup": rel(FIX5_GEO),
        "eventlist": rel(EVENTLIST),
        "triggers": int(payload["triggers"]),
        "seed": int(payload["seed"]),
        "far_field_or_surrounding_sphere": "MEGAlib EventList injection at the Step09 detector Be-window plane; no atmospheric far-field surface.",
        "normalization_constants": {
            "rate_rule": "Step05 normalizes focused EventList to reference_flux * A_eff(511) * T_atm / eventlist_rows.",
            "eventlist_rows": int(payload["triggers"]),
        },
        "expected_sim_outputs": [rel(SIM)],
        "contains_fix5_geometry": rel(FIX5_GEO) in source_body,
        "contains_forbidden_baseline_geometry": BASELINE_GEO in source_body,
    }
    cards = manifest.setdefault("source_cards", [])
    upsert_row(cards, "path", rel(SOURCE), signal_card)
    manifest["signal_source_card"] = signal_card
    manifest.setdefault("expected_sim_outputs", [])
    if rel(SIM) not in manifest["expected_sim_outputs"]:
        manifest["expected_sim_outputs"].append(rel(SIM))
    manifest.setdefault("source_family", {})["focused_signal_eventlist"] = {
        "eventlist_authority": rel(EVENTLIST),
        "detector_geometry": rel(FIX5_GEO),
        "use_for": "fix5 focused signal replay consumed by Step05",
    }
    manifest.setdefault("random_seed_policy", {})["focused_signal_eventlist_seed"] = int(payload["seed"])
    manifest["updated_at_utc"] = now_utc()
    write_json(SOURCE_MANIFEST, manifest)

    verifier = load_json(VERIFIER)
    rows = verifier.setdefault("rows", [])
    upsert_row(
        rows,
        "check",
        "fix5_signal_source_card_geometry",
        {
            "check": "fix5_signal_source_card_geometry",
            "status": "PASS" if signal_card["contains_fix5_geometry"] and not signal_card["contains_forbidden_baseline_geometry"] else "FAIL",
            "evidence_path": rel(SOURCE),
            "blocking": True,
            "details": {
                "contains_fix5_geometry": signal_card["contains_fix5_geometry"],
                "contains_forbidden_baseline_geometry": signal_card["contains_forbidden_baseline_geometry"],
                "expected_sim": rel(SIM),
                "triggers": int(payload["triggers"]),
                "eventlist": rel(EVENTLIST),
            },
        },
    )
    verifier["updated_at_utc"] = now_utc()
    write_json(VERIFIER, verifier)


def source_text(triggers: int, seed: int) -> str:
    return f"""# Auto-generated fix5 focused EventList transport source.
# Replays the current f10m A1 v3p5 Step09 EventList through fix5 geometry.
# The optical EventList is reused; the detector mass model is fix5.

Version 1
Geometry {rel(FIX5_GEO)}
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


def write_summary(payload: dict[str, Any]) -> None:
    write_json(SUMMARY_JSON, payload)
    lines = [
        "# fix5 Step09 Focused EventList Transport",
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
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def build_source(seed: int) -> dict[str, Any]:
    base = load_json(BASE_SUMMARY)
    bridge = base.get("bridge", {})
    rows = int(bridge["rows_written"])
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    SOURCE.write_text(source_text(rows, seed), encoding="utf-8")
    source_body = SOURCE.read_text(encoding="utf-8", errors="ignore")
    payload = {
        "status": "PASS_FIX5_STEP09_FOCUS_SOURCE_READY",
        "claim_level": "FIX5_STEP09_FOCUSED_EVENTLIST_SOURCE_READY_NOT_STEP05_AUTHORITY",
        "label": LABEL,
        "generated_at_utc": now_utc(),
        "source": rel(SOURCE),
        "geometry": rel(FIX5_GEO),
        "eventlist": rel(EVENTLIST),
        "outfile_prefix": rel(PREFIX),
        "triggers": rows,
        "seed": int(seed),
        "base_step09_summary": rel(BASE_SUMMARY),
        "base_step09_status": base.get("status"),
        "base_bridge": bridge,
        "source_audit": {
            "contains_fix5_geometry": rel(FIX5_GEO) in source_body,
            "contains_forbidden_baseline_geometry": BASELINE_GEO in source_body,
        },
        "boundary": [
            "This source replays the current f10m A1 v3p5 focused EventList through fix5 geometry.",
            "It is not a fix5 detector-response authority until Cosima transport is summarized and Step05 consumes this fix5 signal SIM.",
        ],
    }
    update_contract_artifacts(payload)
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
        build_source(seed=260616)
    payload = load_json(SUMMARY_JSON)
    transport = inspect_sim(SIM)
    problems = []
    triggers = int(payload["triggers"])
    geom_text = str(transport["geometry"])
    if not transport["exists"]:
        problems.append("missing_focus_transport_sim")
    if int(transport["SE"]) != int(transport["ID"]):
        problems.append("SE_ID_mismatch")
    if int(transport["SE"]) != triggers:
        problems.append("stored_events_do_not_match_eventlist_triggers")
    if rel(FIX5_GEO) not in geom_text and str(FIX5_GEO) not in geom_text:
        problems.append("transport_geometry_not_fix5")
    if BASELINE_GEO in geom_text:
        problems.append("transport_geometry_contains_forbidden_baseline")
    payload["updated_at_utc"] = now_utc()
    payload["focused_transport"] = transport
    payload["problems"] = problems
    if problems:
        payload["status"] = "FAIL_FIX5_STEP09_FOCUS_TRANSPORT"
    else:
        payload["status"] = "PASS_FIX5_STEP09_FOCUS_TRANSPORT"
        payload["claim_level"] = "FIX5_STEP09_FOCUSED_EVENTLIST_TRANSPORT_NOT_STEP05_AUTHORITY"
        payload["boundary"] = [
            "Focused EventList transport through fix5 geometry passed.",
            "Step05 detector response must consume this fix5 signal SIM together with fix5 prompt and delayed SIMs before quoting signal keep or sensitivity.",
        ]
    update_signal_transport_verifier(payload)
    write_summary(payload)
    print(json.dumps({"status": payload["status"], "problems": problems, "focused_transport": transport}, indent=2))
    return payload


def update_signal_transport_verifier(payload: dict[str, Any]) -> None:
    verifier = load_json(VERIFIER)
    rows = verifier.setdefault("rows", [])
    transport = payload.get("focused_transport", {})
    upsert_row(
        rows,
        "check",
        "fix5_signal_transport_sim_header",
        {
            "check": "fix5_signal_transport_sim_header",
            "status": "PASS" if str(payload.get("status", "")).startswith("PASS") else "FAIL",
            "evidence_path": transport.get("path", rel(SIM)),
            "blocking": True,
            "details": {
                "SE": transport.get("SE"),
                "ID": transport.get("ID"),
                "TS": transport.get("TS"),
                "TE_s": transport.get("TE_s"),
                "size_bytes": transport.get("size_bytes"),
                "geometry": transport.get("geometry"),
                "geometry_ok": "DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy" in str(transport.get("geometry", "")),
                "problems": payload.get("problems", []),
            },
        },
    )
    verifier["updated_at_utc"] = now_utc()
    write_json(VERIFIER, verifier)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-source")
    build.add_argument("--seed", type=int, default=260616)
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
