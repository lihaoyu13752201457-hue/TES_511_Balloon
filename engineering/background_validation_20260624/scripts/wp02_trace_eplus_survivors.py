#!/usr/bin/env python3
"""WP02 prompt eplus survivor provenance for HARNESS_20260624.

This is a read-only audit of the existing fix5 full-stat Step05 catalog and
prompt eplus SIM files. It does not rerun transport or modify authority outputs.
"""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import pickle
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ENG = Path(__file__).resolve().parents[1]
OUT = ENG / "02_prompt_eplus_provenance"
STEP05_CODE = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP05_DIR = ROOT / "stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1"
CATALOG = STEP05_DIR / "work/event_catalog.pkl"
STEP05_SUMMARY = STEP05_DIR / "step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_response_summary.json"
W2 = (510.58, 511.42)

CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def load_step05_module() -> Any:
    spec = importlib.util.spec_from_file_location("wp02_step05_fix5", STEP05_CODE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {STEP05_CODE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT
    mod.configure_paths("fix5_fullstat_v2_exactpos_m50000_s260613")
    return mod


def resolve_path(path_text: str) -> Path:
    p = Path(path_text)
    if p.is_absolute():
        return p
    return ROOT / p


def selected_eplus_survivors(step05_mod: Any, cat: dict[str, Any]) -> list[dict[str, Any]]:
    disk = step05_mod.side_entry_disk()
    stream = np.asarray(cat["stream"], dtype=object)
    tag = np.asarray(cat["tag"], dtype=object)
    tes = np.asarray(cat["tes_total_keV"], dtype=float)
    bgo = np.asarray(cat["bgo_total_keV"], dtype=float)
    mask = (
        (stream == "prompt")
        & (tag == "eplus")
        & (tes >= W2[0])
        & (tes < W2[1])
        & (bgo < float(step05_mod.ACTIVE_VETO_THRESHOLD_KEV))
    )
    rows: list[dict[str, Any]] = []
    for idx in np.flatnonzero(mask):
        keep, cls = step05_mod.side_keep_from_hits(step05_mod.event_hits(cat, int(idx)), disk, "keep")
        if not keep:
            continue
        pix_start = int(cat["pix_start"][idx])
        pix_count = int(cat["pix_count"][idx])
        pixel_rows = []
        for j in range(pix_start, pix_start + pix_count):
            pixel_rows.append(
                {
                    "uid": str(cat["pix_uid"][j]),
                    "layer": int(cat["pix_layer"][j]),
                    "e_keV": float(cat["pix_e"][j]),
                    "x_cm": float(cat["pix_x"][j]),
                    "y_cm": float(cat["pix_y"][j]),
                    "z_cm": float(cat["pix_z"][j]),
                }
            )
        rows.append(
            {
                "catalog_index": int(idx),
                "stream": str(cat["stream"][idx]),
                "tag": str(cat["tag"][idx]),
                "source_file": str(cat["source_file"][idx]),
                "local_id": int(cat["local_id"][idx]),
                "rate_hz": float(cat["rate_hz"][idx]),
                "tes_total_keV": float(cat["tes_total_keV"][idx]),
                "bgo_total_keV": float(cat["bgo_total_keV"][idx]),
                "pix_count": pix_count,
                "pixel_multiplicity": "single" if pix_count == 1 else "multi",
                "pixel_uids": ";".join(row["uid"] for row in pixel_rows),
                "side_compton_class": cls,
            }
        )
    return rows


def iter_text_lines(path: Path):
    if path.suffix == ".gz":
        proc = subprocess.Popen(["gzip", "-cd", str(path)], stdout=subprocess.PIPE)
        assert proc.stdout is not None
        try:
            for raw in proc.stdout:
                yield raw.decode("utf-8", errors="ignore").rstrip("\n")
        finally:
            if proc.poll() is None:
                proc.terminate()
            proc.wait()
        return
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            yield raw.rstrip("\n")


def extract_event_blocks(wanted_by_path: dict[Path, set[int]]) -> dict[tuple[str, int], list[str]]:
    blocks: dict[tuple[str, int], list[str]] = {}
    for path, wanted_ids in sorted(wanted_by_path.items(), key=lambda item: str(item[0])):
        if not wanted_ids:
            continue
        path_key = rel(path)
        found_ids: set[int] = set()
        current_id: int | None = None
        current_lines: list[str] = []

        def flush() -> None:
            nonlocal current_id, current_lines
            if current_id in wanted_ids:
                blocks[(path_key, int(current_id))] = list(current_lines)
                found_ids.add(int(current_id))
            current_id = None
            current_lines = []

        for line in iter_text_lines(path):
            if line.strip() == "SE":
                flush()
                if len(found_ids) == len(wanted_ids):
                    break
                continue
            if line.startswith("ID "):
                flush()
                parts = line.split()
                current_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
                current_lines = [line]
                continue
            if current_id is not None:
                current_lines.append(line)
        flush()
    return blocks


def as_float(value: Any) -> float | None:
    try:
        out = float(value)
    except Exception:
        return None
    return out if math.isfinite(out) else None


def parse_ia(line: str) -> dict[str, Any] | None:
    parts = line.split(None, 2)
    if len(parts) < 3 or parts[0] != "IA":
        return None
    process = parts[1]
    fields = [field.strip() for field in parts[2].split(";")]
    out: dict[str, Any] = {
        "process": process,
        "raw": line,
        "field_count": len(fields),
    }
    if len(fields) >= 7:
        out["x_cm"] = as_float(fields[4])
        out["y_cm"] = as_float(fields[5])
        out["z_cm"] = as_float(fields[6])
    if len(fields) >= 4:
        out["time_s"] = as_float(fields[3])
    if len(fields) >= 16:
        out["secondary_code"] = fields[15]
    return out


def parse_cc_hit(line: str) -> dict[str, Any] | None:
    m = CC_HIT_RE.match(line.strip())
    if not m:
        return None
    kv = {key: value for key, value in KV_RE.findall(m.group(2))}
    row: dict[str, Any] = {"volume": m.group(1), "raw": line}
    row.update(kv)
    for key in ("edep_keV", "x", "y", "z", "t"):
        if key in row:
            row[key] = as_float(row[key])
    return row


def parse_htsim(line: str) -> dict[str, Any] | None:
    if not line.startswith("HTsim"):
        return None
    fields = [field.strip() for field in line[len("HTsim") :].split(";")]
    out: dict[str, Any] = {"raw": line, "field_count": len(fields)}
    if len(fields) >= 5:
        out.update(
            {
                "detector": fields[0],
                "x_cm": as_float(fields[1]),
                "y_cm": as_float(fields[2]),
                "z_cm": as_float(fields[3]),
                "energy_keV": as_float(fields[4]),
            }
        )
    return out


def parse_pm(line: str) -> dict[str, Any] | None:
    parts = line.split()
    if len(parts) >= 3 and parts[0] == "PM":
        return {"volume": parts[1], "path_length_cm": as_float(parts[2])}
    return None


def event_trace(lines: list[str]) -> dict[str, Any]:
    ia = [row for row in (parse_ia(line) for line in lines if line.startswith("IA ")) if row is not None]
    cc_hits = [row for row in (parse_cc_hit(line) for line in lines if line.startswith("CC HIT ")) if row is not None]
    htsim = [row for row in (parse_htsim(line) for line in lines if line.startswith("HTsim")) if row is not None]
    pm = [row for row in (parse_pm(line) for line in lines if line.startswith("PM ")) if row is not None]
    tes_hits = [row for row in cc_hits if TP_RE.match(str(row.get("volume", "")))]
    tes_hits.sort(key=lambda row: (float(row.get("t") or 0.0), -float(row.get("edep_keV") or 0.0)))
    return {"ia": ia, "cc_hits": cc_hits, "htsim": htsim, "pm": pm, "tes_hits": tes_hits, "line_count": len(lines)}


def compact_hit(hit: dict[str, Any] | None) -> dict[str, Any]:
    if not hit:
        return {}
    return {
        "volume": hit.get("volume", ""),
        "edep_keV": hit.get("edep_keV", ""),
        "x_cm": hit.get("x", ""),
        "y_cm": hit.get("y", ""),
        "z_cm": hit.get("z", ""),
        "sec": hit.get("sec", ""),
        "prim": hit.get("prim", ""),
        "par": hit.get("par", ""),
        "sproc": hit.get("sproc", ""),
        "cproc": hit.get("cproc", ""),
        "tid": hit.get("tid", ""),
        "pid": hit.get("pid", ""),
    }


def classify_trace(row: dict[str, Any], trace: dict[str, Any] | None) -> dict[str, Any]:
    if trace is None:
        return {
            "classification_code": "F",
            "classification_label": "parser/event-link inconsistency",
            "classification_reason": "SIM event block was not found for source_file/local_id.",
            "missing_trace_fields": "event_block",
        }
    if row.get("stream") != "prompt" or row.get("tag") != "eplus":
        return {
            "classification_code": "D",
            "classification_label": "neutron/other mis-tag impossible under current stream logic",
            "classification_reason": "Selected row is not prompt/eplus.",
            "missing_trace_fields": "",
        }

    tes_hits = trace["tes_hits"]
    if not tes_hits:
        return {
            "classification_code": "F",
            "classification_label": "parser/event-link inconsistency",
            "classification_reason": "Step05 catalog has TES energy but SIM block has no TP_* CC HIT.",
            "missing_trace_fields": "TP_CC_HIT",
        }

    ia_processes = Counter(str(item.get("process", "")) for item in trace["ia"])
    has_anni = ia_processes.get("ANNI", 0) > 0
    has_genealogy = any(
        all(key in hit and str(hit.get(key, "")) for key in ("sec", "prim", "par", "sproc", "cproc"))
        for hit in tes_hits
    )
    direct_charged = any(
        str(hit.get("sec", "")) == "e+"
        or (str(hit.get("prim", "")) == "e+" and str(hit.get("par", "")) in {"none", "e+"} and str(hit.get("cproc", "")) == "primary")
        for hit in tes_hits
    )
    annihilation_lineage = any(
        str(hit.get("cproc", "")) == "annihil"
        or (
            str(hit.get("prim", "")) == "e+"
            and str(hit.get("par", "")) in {"e+", "gamma"}
            and str(hit.get("sec", "")) in {"gamma", "e-"}
        )
        for hit in tes_hits
    )

    if direct_charged and not annihilation_lineage:
        return {
            "classification_code": "C",
            "classification_label": "direct charged-particle TES deposition",
            "classification_reason": "A TP_* CC HIT is carried by the primary positron before an annihilation-photon lineage is seen.",
            "missing_trace_fields": "" if has_genealogy else "partial_genealogy",
        }
    if has_anni and annihilation_lineage:
        return {
            "classification_code": "A",
            "classification_label": "aperture-coupled annihilation photon",
            "classification_reason": "The SIM block contains IA ANNI and TP_* CC HIT genealogy tied to the e+ annihilation photon; Step05 side-entry Compton/FoV accepted the event.",
            "missing_trace_fields": "" if has_genealogy else "partial_genealogy",
        }
    if has_anni and has_genealogy:
        return {
            "classification_code": "B",
            "classification_label": "annihilation/secondary photon generated in nearby passive material",
            "classification_reason": "The event has an annihilation and TES genealogy, but the accepted TES energy is not directly marked as annihilation-photon lineage.",
            "missing_trace_fields": "",
        }
    return {
        "classification_code": "E",
        "classification_label": "incomplete trace information",
        "classification_reason": "Existing SIM records do not expose enough IA/CC genealogy to classify A-C.",
        "missing_trace_fields": "IA_ANNI_or_CC_genealogy",
    }


def summarize(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    acc: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        key = tuple(row.get(k, "") for k in keys)
        item = acc.setdefault(key, {k: row.get(k, "") for k in keys} | {"events": 0, "rate_hz": 0.0, "sum_w2": 0.0})
        rate = float(row.get("rate_hz") or 0.0)
        item["events"] += 1
        item["rate_hz"] += rate
        item["sum_w2"] += rate * rate
    total = sum(float(item["rate_hz"]) for item in acc.values())
    out = list(acc.values())
    for item in out:
        item["fraction_of_rate"] = float(item["rate_hz"]) / total if total > 0 else 0.0
    out.sort(key=lambda item: (float(item["rate_hz"]), int(item["events"])), reverse=True)
    return out


def markdown(payload: dict[str, Any]) -> str:
    cls = payload["classification_counts"]
    lines = [
        "# WP02 Prompt eplus Survivor Provenance",
        "",
        f"Status: `{payload['status']}`.",
        "",
        f"Selected final W2 prompt eplus survivors: `{payload['selection']['selected_events']}`.",
        f"Selected eplus rate: `{payload['selection']['selected_rate_cps']:.12g}` cps.",
        f"A-C classified fraction: `{payload['classification']['a_to_c_event_fraction']:.3f}`.",
        "",
        "## Classification Counts",
        "",
        "| class | events | rate cps |",
        "|---|---:|---:|",
    ]
    for code in sorted(cls):
        item = cls[code]
        lines.append(f"| {code} | {item['events']} | {float(item['rate_hz']):.12g} |")
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "- Selection is reconstructed from the fix5 Step05 event catalog using the same active veto and side-entry Compton/FoV functions.",
            "- Event provenance is parsed from existing prompt eplus SIM `IA`, `CC HIT`, and `HTsim` blocks; no transport was rerun.",
            "",
            "Outputs:",
            f"- event table: `{payload['outputs']['events_csv']}`",
            f"- process summary: `{payload['outputs']['process_summary_csv']}`",
            f"- volume summary: `{payload['outputs']['volume_summary_csv']}`",
        ]
    )
    if payload["problems"]:
        lines.extend(["", "Problems:"])
        lines.extend(f"- {item}" for item in payload["problems"])
    return "\n".join(lines) + "\n"


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    step05_mod = load_step05_module()
    with CATALOG.open("rb") as handle:
        cat = pickle.load(handle)
    selected = selected_eplus_survivors(step05_mod, cat)

    wanted_by_path: dict[Path, set[int]] = defaultdict(set)
    for row in selected:
        wanted_by_path[resolve_path(str(row["source_file"]))].add(int(row["local_id"]))
    blocks = extract_event_blocks(wanted_by_path)

    event_rows: list[dict[str, Any]] = []
    problems: list[str] = []
    for row in selected:
        sim_path = resolve_path(str(row["source_file"]))
        block = blocks.get((rel(sim_path), int(row["local_id"])))
        trace = event_trace(block) if block is not None else None
        classification = classify_trace(row, trace)
        if classification["classification_code"] == "F":
            problems.append(f"event_link_{row['source_file']}:{row['local_id']}_{classification['missing_trace_fields']}")

        first_tes = compact_hit(trace["tes_hits"][0]) if trace and trace["tes_hits"] else {}
        max_tes = compact_hit(max(trace["tes_hits"], key=lambda hit: float(hit.get("edep_keV") or 0.0))) if trace and trace["tes_hits"] else {}
        annihilations = [item for item in trace["ia"] if item.get("process") == "ANNI"] if trace else []
        first_anni = annihilations[0] if annihilations else {}
        pm_first = trace["pm"][0] if trace and trace["pm"] else {}
        ia_counts = Counter(str(item.get("process", "")) for item in trace["ia"]) if trace else Counter()

        event_rows.append(
            {
                **row,
                **classification,
                "sim_path": rel(sim_path),
                "sim_block_lines": trace["line_count"] if trace else 0,
                "ia_process_counts": ";".join(f"{key}:{ia_counts[key]}" for key in sorted(ia_counts)),
                "has_ia_anni": bool(first_anni),
                "annihilation_x_cm": first_anni.get("x_cm", ""),
                "annihilation_y_cm": first_anni.get("y_cm", ""),
                "annihilation_z_cm": first_anni.get("z_cm", ""),
                "annihilation_medium": pm_first.get("volume", ""),
                "annihilation_medium_path_cm": pm_first.get("path_length_cm", ""),
                "htsim_hits": len(trace["htsim"]) if trace else 0,
                "tes_cc_hits": len(trace["tes_hits"]) if trace else 0,
                "first_tes_volume": first_tes.get("volume", ""),
                "first_tes_edep_keV": first_tes.get("edep_keV", ""),
                "first_tes_sec": first_tes.get("sec", ""),
                "first_tes_prim": first_tes.get("prim", ""),
                "first_tes_par": first_tes.get("par", ""),
                "first_tes_sproc": first_tes.get("sproc", ""),
                "first_tes_cproc": first_tes.get("cproc", ""),
                "first_tes_tid": first_tes.get("tid", ""),
                "first_tes_pid": first_tes.get("pid", ""),
                "max_tes_volume": max_tes.get("volume", ""),
                "max_tes_edep_keV": max_tes.get("edep_keV", ""),
                "max_tes_sec": max_tes.get("sec", ""),
                "max_tes_prim": max_tes.get("prim", ""),
                "max_tes_par": max_tes.get("par", ""),
                "max_tes_sproc": max_tes.get("sproc", ""),
                "max_tes_cproc": max_tes.get("cproc", ""),
                "entry_path_distribution": "single_pixel" if row["side_compton_class"] == "single" else "side_compton_keep",
            }
        )

    events_csv = OUT / "eplus_survivor_events.csv"
    process_csv = OUT / "eplus_survivor_process_summary.csv"
    volume_csv = OUT / "eplus_survivor_volume_summary.csv"
    entry_csv = OUT / "eplus_survivor_entry_path_summary.csv"
    write_csv(events_csv, event_rows)
    write_csv(
        process_csv,
        summarize(event_rows, ("classification_code", "classification_label", "first_tes_sec", "first_tes_sproc", "first_tes_cproc", "first_tes_par")),
    )
    write_csv(volume_csv, summarize(event_rows, ("classification_code", "annihilation_medium", "first_tes_volume", "max_tes_volume")))
    write_csv(entry_csv, summarize(event_rows, ("classification_code", "entry_path_distribution", "pixel_multiplicity", "side_compton_class")))

    class_rows = summarize(event_rows, ("classification_code", "classification_label"))
    class_counts = {
        str(row["classification_code"]): {
            "label": row["classification_label"],
            "events": int(row["events"]),
            "rate_hz": float(row["rate_hz"]),
        }
        for row in class_rows
    }
    selected_rate = sum(float(row.get("rate_hz") or 0.0) for row in event_rows)
    selected_sum_w2 = sum(float(row.get("rate_hz") or 0.0) ** 2 for row in event_rows)
    a_to_c_events = sum(1 for row in event_rows if str(row["classification_code"]) in {"A", "B", "C"})
    a_to_c_rate = sum(float(row.get("rate_hz") or 0.0) for row in event_rows if str(row["classification_code"]) in {"A", "B", "C"})
    e_events = sum(1 for row in event_rows if str(row["classification_code"]) == "E")
    status = "PASS_EPLUS_PROVENANCE" if event_rows and a_to_c_events / len(event_rows) >= 0.8 and not problems else "INSUFFICIENT_TRACE"
    if problems:
        status = "FAIL_EPLUS_PROVENANCE_LINK"

    payload = {
        "artifact_type": "wp02_prompt_eplus_survivor_provenance",
        "status": status,
        "created_utc": now_utc(),
        "inputs": {
            "event_catalog": rel(CATALOG),
            "step05_summary": rel(STEP05_SUMMARY),
            "step05_code": rel(STEP05_CODE),
            "sim_files": [rel(path) for path in sorted(wanted_by_path)],
        },
        "selection": {
            "stream": "prompt",
            "tag": "eplus",
            "window_keV": list(W2),
            "active_veto_threshold_keV": float(step05_mod.ACTIVE_VETO_THRESHOLD_KEV),
            "side_entry_policy": "same Step05 side_keep_from_hits/event_hits/side_entry_disk implementation",
            "selected_events": len(event_rows),
            "selected_rate_cps": selected_rate,
            "selected_sum_w2": selected_sum_w2,
            "mc_sigma_cps": math.sqrt(selected_sum_w2) if selected_sum_w2 >= 0 else None,
        },
        "classification": {
            "a_to_c_events": a_to_c_events,
            "a_to_c_rate_hz": a_to_c_rate,
            "a_to_c_event_fraction": a_to_c_events / len(event_rows) if event_rows else 0.0,
            "e_incomplete_trace_events": e_events,
            "e_incomplete_trace_fraction": e_events / len(event_rows) if event_rows else 0.0,
            "acceptance_rule": "PASS if >=80% survivors classify as A-C; otherwise explicit INSUFFICIENT_TRACE.",
        },
        "classification_counts": class_counts,
        "outputs": {
            "events_csv": rel(events_csv),
            "process_summary_csv": rel(process_csv),
            "volume_summary_csv": rel(volume_csv),
            "entry_path_summary_csv": rel(entry_csv),
            "json": rel(OUT / "eplus_survivor_provenance.json"),
            "markdown": rel(OUT / "eplus_survivor_provenance.md"),
        },
        "problems": problems,
    }
    write_json(OUT / "eplus_survivor_provenance.json", payload)
    write_json(OUT / "summary.json", payload)
    md = markdown(payload)
    (OUT / "eplus_survivor_provenance.md").write_text(md, encoding="utf-8")
    (OUT / "summary.md").write_text(md, encoding="utf-8")
    return payload


def main() -> int:
    payload = build()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_events": payload["selection"]["selected_events"],
                "selected_rate_cps": payload["selection"]["selected_rate_cps"],
                "a_to_c_event_fraction": payload["classification"]["a_to_c_event_fraction"],
                "out": payload["outputs"]["json"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if payload["status"] in {"PASS_EPLUS_PROVENANCE", "INSUFFICIENT_TRACE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
