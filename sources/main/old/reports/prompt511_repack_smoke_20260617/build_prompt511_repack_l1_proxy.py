#!/usr/bin/env python3
"""Build a prompt Step05-like L1 proxy for the W-liner repack smoke.

This is deliberately prompt-only.  It always includes eplus and can include
follow-up particle cases when completed repack runs exist.  It reuses the
official side-entry Compton/FoV functions, but it does not mix in delayed
activation, focused signal, or a Poisson mission-time axis.
"""

from __future__ import annotations

import importlib.util
import gzip
import json
import math
import pickle
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_repack_smoke_20260617"
CURRENT_PROMPT_DIR = ROOT / "runs/step02_instant_v3p5_centerfinger_fullstat_v2"
REPACK_PROMPT_DIR = WORK / "runs/instant_eplus_g10m_r4_cli_seed"
REPACK_PROMPT_DIR_BY_TAG = {
    "eplus": REPACK_PROMPT_DIR,
    "n": WORK / "runs/instant_n_g10m_r16_cli_seed",
    "muplus": WORK / "runs/instant_muplus_g10m_r80_l1plan",
}
CURRENT_STEP05_CACHE = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613_l1/work/event_catalog.pkl"
)
SUMMARY_JSON = WORK / "prompt511_repack_l1_proxy_summary.json"
SUMMARY_MD = WORK / "prompt511_repack_l1_proxy_summary.md"
SEED_AUDIT_MD = WORK / "prompt511_repack_seed_independence_audit.md"

LINE_WINDOW = (510.58, 511.42)
ACTIVE_VETO_THRESHOLD_KEV = 50.0
OLD_NEW_GEO_RE_PROMPT_TOTAL_CPS = 0.0323247092031
OLD_NEW_GEO_RE_PROMPT_EPLUS_CPS = 0.0244744226824
TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)
ID_RE = re.compile(r"^ID\s+(\d+)")
CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)
TP_FILTER_RE = r"^(ID |SE$|CC HIT TP_L)"
TP_ACTIVE_FILTER_RE = r"^(ID |SE$|CC HIT (TP_L|CsI_|.*ACTIVE_SHIELD|.*CEBR3|.*BGO))"


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


def parse_tag(path: Path | str) -> str:
    m = TAG_RE.search(Path(path).name)
    return m.group("tag").lower() if m else "unknown"


def load_prompt_rates(prompt_dir: Path) -> dict[str, float]:
    norm_path = prompt_dir / "normalization.json"
    norm = json.loads(norm_path.read_text(encoding="utf-8"))
    tags = norm.get("selected_particles") or sorted(
        {
            parse_tag(path)
            for path in prompt_dir.glob("Background_*_fullsphere20_*.dat.inc1.dat")
            if parse_tag(path) != "unknown"
        }
    )
    rates: dict[str, float] = {}
    for tag in tags:
        tt_sum = 0.0
        dats = sorted(prompt_dir.glob(f"Background_{tag}_fullsphere20_*.dat.inc1.dat"))
        for dat in dats:
            for raw in dat.read_text(encoding="utf-8", errors="ignore").splitlines():
                if raw.startswith("TT "):
                    tt_sum += float(raw.split()[1])
        if tt_sum > 0.0:
            rates[tag] = 1.0 / tt_sum
    return rates


def parse_cc_hit(line: str) -> tuple[str, float, float, float, float] | None:
    m = CC_HIT_RE.match(line.strip())
    if not m:
        return None
    kv = dict(KV_RE.findall(m.group(2)))
    try:
        return (
            m.group(1),
            float(kv["edep_keV"]),
            float(kv["x"]),
            float(kv["y"]),
            float(kv["z"]),
        )
    except Exception:
        return None


def hits_from_pix(pix: dict[str, dict[str, Any]]) -> tuple[float, list[Any]]:
    tes_total = 0.0
    hits = []
    for uid, rec in sorted(pix.items()):
        e = float(rec["e"])
        if e <= 0.0:
            continue
        tes_total += e
        hits.append(
            SimpleNamespace(
                x=float(rec["wx"] / e),
                y=float(rec["wy"] / e),
                z=float(rec["wz"] / e),
                e=e,
                pixel_uid=uid,
                layer=int(rec["layer"]),
            )
        )
    return tes_total, hits


def iter_filtered_sim_lines(sim: Path, pattern: str):
    gzip_proc = subprocess.Popen(["gzip", "-dc", str(sim)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if gzip_proc.stdout is None:
        raise RuntimeError(f"failed to open gzip stream for {sim}")
    grep_proc = subprocess.Popen(
        ["grep", "-E", pattern],
        stdin=gzip_proc.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    gzip_proc.stdout.close()
    if grep_proc.stdout is None:
        raise RuntimeError(f"failed to open grep stream for {sim}")
    try:
        for raw in grep_proc.stdout:
            yield raw.strip()
    finally:
        if grep_proc.stdout is not None:
            grep_proc.stdout.close()
    grep_stderr = grep_proc.stderr.read() if grep_proc.stderr is not None else ""
    gzip_stderr = gzip_proc.stderr.read() if gzip_proc.stderr is not None else ""
    grep_rc = grep_proc.wait()
    gzip_rc = gzip_proc.wait()
    if grep_rc not in (0, 1):
        raise RuntimeError(f"grep failed for {sim}: rc={grep_rc} {grep_stderr.strip()}")
    if gzip_rc != 0:
        raise RuntimeError(f"gzip failed for {sim}: rc={gzip_rc} {gzip_stderr.strip()}")


def line_window_candidates(sim: Path) -> tuple[int, int, dict[int, float]]:
    generated_events_seen = 0
    tes_events_kept = 0
    candidates: dict[int, float] = {}

    cur_id: int | None = None
    pix: dict[str, dict[str, Any]] = {}

    def flush() -> None:
        nonlocal cur_id, pix, tes_events_kept
        if cur_id is None:
            return
        tes_total, hits = hits_from_pix(pix)
        if tes_total > 0.0:
            tes_events_kept += 1
        if LINE_WINDOW[0] <= tes_total < LINE_WINDOW[1]:
            candidates[int(cur_id)] = float(tes_total)
        cur_id = None
        pix = {}

    for line in iter_filtered_sim_lines(sim, TP_FILTER_RE):
            if not line:
                continue
            if line == "SE":
                flush()
                continue
            m_id = ID_RE.match(line)
            if m_id:
                cur_id = int(m_id.group(1))
                generated_events_seen += 1
                pix = {}
                continue
            if not line.startswith("CC HIT "):
                continue
            hit = parse_cc_hit(line)
            if hit is None:
                continue
            vol, edep, x, y, z = hit
            m_tp = TP_RE.match(vol)
            if m_tp:
                rec = pix.setdefault(
                    vol,
                    {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(m_tp.group("layer"))},
                )
                rec["e"] += edep
                rec["wx"] += edep * x
                rec["wy"] += edep * y
                rec["wz"] += edep * z
    flush()
    return generated_events_seen, tes_events_kept, candidates


def summarize_sim_stream(step05, sim: Path, rate_per_event: float, disk: dict[str, Any], reject_policy: str) -> dict[str, Any]:
    generated_events_seen, tes_events_kept, candidates = line_window_candidates(sim)
    active_events = 0
    final_events = 0
    active_rate = 0.0
    final_rate = 0.0
    class_counts = Counter()
    examples = []

    cur_id: int | None = None
    in_candidate = False
    bgo_total = 0.0
    pix: dict[str, dict[str, Any]] = {}

    def flush() -> None:
        nonlocal cur_id, in_candidate, bgo_total, pix
        nonlocal active_events, final_events, active_rate, final_rate
        if cur_id is None or not in_candidate:
            cur_id = None
            in_candidate = False
            bgo_total = 0.0
            pix = {}
            return
        tes_total, hits = hits_from_pix(pix)
        if bgo_total < ACTIVE_VETO_THRESHOLD_KEV:
            active_events += 1
            active_rate += rate_per_event
            keep, cls = step05.side_keep_from_hits(hits, disk, reject_policy)
            class_counts[cls] += 1
            if keep:
                final_events += 1
                final_rate += rate_per_event
                if len(examples) < 20:
                    examples.append(
                        {
                            "source_file": rel(sim),
                            "local_id": int(cur_id),
                            "tes_total_keV": float(candidates.get(int(cur_id), tes_total)),
                            "active_veto_keV": float(bgo_total),
                            "side_compton_class": cls,
                            "rate_s-1": float(rate_per_event),
                        }
                    )
        cur_id = None
        in_candidate = False
        bgo_total = 0.0
        pix = {}

    for line in iter_filtered_sim_lines(sim, TP_ACTIVE_FILTER_RE):
            if not line:
                continue
            if line == "SE":
                flush()
                continue
            m_id = ID_RE.match(line)
            if m_id:
                cur_id = int(m_id.group(1))
                in_candidate = cur_id in candidates
                bgo_total = 0.0
                pix = {}
                continue
            if not in_candidate or not line.startswith("CC HIT "):
                continue
            hit = parse_cc_hit(line)
            if hit is None:
                continue
            vol, edep, x, y, z = hit
            m_tp = TP_RE.match(vol)
            if m_tp:
                rec = pix.setdefault(
                    vol,
                    {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": int(m_tp.group("layer"))},
                )
                rec["e"] += edep
                rec["wx"] += edep * x
                rec["wy"] += edep * y
                rec["wz"] += edep * z
            elif step05.is_v3p5_active_veto_volume(vol):
                bgo_total += edep
    flush()

    raw_events = len(candidates)
    raw_rate = raw_events * rate_per_event
    return {
        "path": rel(sim),
        "generated_events_seen": generated_events_seen,
        "tes_events_kept": tes_events_kept,
        "raw_events": raw_events,
        "active_veto_pass_events": active_events,
        "side_compton_fov_pass_events": final_events,
        "raw_rate_s-1": raw_rate,
        "active_veto_pass_rate_s-1": active_rate,
        "side_compton_fov_pass_rate_s-1": final_rate,
        "side_compton_class_counts": dict(sorted(class_counts.items())),
        "selected_examples": examples,
    }


def merge_summaries(rows: list[dict[str, Any]]) -> dict[str, Any]:
    class_counts = Counter()
    examples = []
    out = {
        "generated_events_seen": 0,
        "tes_events_kept": 0,
        "window_keV": list(LINE_WINDOW),
        "raw_events": 0,
        "active_veto_pass_events": 0,
        "side_compton_fov_pass_events": 0,
        "raw_rate_s-1": 0.0,
        "active_veto_pass_rate_s-1": 0.0,
        "side_compton_fov_pass_rate_s-1": 0.0,
    }
    for row in rows:
        for key in (
            "generated_events_seen",
            "tes_events_kept",
            "raw_events",
            "active_veto_pass_events",
            "side_compton_fov_pass_events",
        ):
            out[key] += int(row[key])
        for key in ("raw_rate_s-1", "active_veto_pass_rate_s-1", "side_compton_fov_pass_rate_s-1"):
            out[key] += float(row[key])
        class_counts.update(row["side_compton_class_counts"])
        if len(examples) < 20:
            examples.extend(row["selected_examples"][: 20 - len(examples)])
    raw_rate = float(out["raw_rate_s-1"])
    active_rate = float(out["active_veto_pass_rate_s-1"])
    out["active_veto_survival_fraction"] = active_rate / raw_rate if raw_rate > 0.0 else None
    out["side_compton_fov_survival_fraction_vs_active"] = (
        float(out["side_compton_fov_pass_rate_s-1"]) / active_rate if active_rate > 0.0 else None
    )
    out["side_compton_class_counts"] = dict(sorted(class_counts.items()))
    out["selected_examples"] = examples
    return out


def summarize_prompt_dir(step05, prompt_dir: Path, disk: dict[str, Any], reject_policy: str, tag: str = "eplus") -> dict[str, Any]:
    rates = load_prompt_rates(prompt_dir)
    if tag not in rates:
        raise KeyError(f"{tag!r} rate missing from {prompt_dir}")
    sims = sorted(prompt_dir.glob(f"Background_{tag}_fullsphere20_*.sim.gz"))
    if not sims:
        raise FileNotFoundError(f"no {tag} SIM files in {prompt_dir}")
    workers = min(8, len(sims))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(lambda sim: summarize_sim_stream(step05, sim, rates[tag], disk, reject_policy), sims))
    return {
        "prompt_dir": rel(prompt_dir),
        "sim_files": [rel(path) for path in sims],
        "rate_per_event_s-1": rates[tag],
        "summary": merge_summaries(rows),
        "files": rows,
    }


def repack_dir_ready(prompt_dir: Path, tag: str) -> bool:
    return (prompt_dir / "run_summary.json").exists() and any(
        prompt_dir.glob(f"Background_{tag}_fullsphere20_*.sim.gz")
    )


def summarize_catalog_case(
    step05,
    cache_path: Path,
    disk: dict[str, Any],
    reject_policy: str,
    stream: str = "prompt",
    tag: str = "eplus",
) -> dict[str, Any]:
    with cache_path.open("rb") as fh:
        cat = pickle.load(fh)

    raw_events = 0
    active_events = 0
    final_events = 0
    raw_rate = 0.0
    active_rate = 0.0
    final_rate = 0.0
    catalog_events_considered = 0
    tes_events_kept = 0
    class_counts = Counter()
    examples = []
    sim_files = set()

    for idx in range(len(cat["stream"])):
        if str(cat["stream"][idx]) != stream or str(cat["tag"][idx]) != tag:
            continue
        catalog_events_considered += 1
        sim_files.add(rel(Path(str(cat["source_file"][idx]))))
        tes_total = float(cat["tes_total_keV"][idx])
        if tes_total > 0.0:
            tes_events_kept += 1
        if not (LINE_WINDOW[0] <= tes_total < LINE_WINDOW[1]):
            continue
        rate = float(cat["rate_hz"][idx])
        raw_events += 1
        raw_rate += rate
        bgo_total = float(cat["bgo_total_keV"][idx])
        if bgo_total >= ACTIVE_VETO_THRESHOLD_KEV:
            continue
        active_events += 1
        active_rate += rate
        keep, cls = step05.side_keep_from_hits(step05.event_hits(cat, idx), disk, reject_policy)
        class_counts[cls] += 1
        if keep:
            final_events += 1
            final_rate += rate
            if len(examples) < 20:
                examples.append(
                    {
                        "source_file": rel(Path(str(cat["source_file"][idx]))),
                        "local_id": int(cat["local_id"][idx]),
                        "tes_total_keV": tes_total,
                        "active_veto_keV": bgo_total,
                        "side_compton_class": cls,
                        "rate_s-1": rate,
                    }
                )

    summary = {
        "catalog_events_considered": catalog_events_considered,
        "generated_events_seen": None,
        "tes_events_kept": tes_events_kept,
        "window_keV": list(LINE_WINDOW),
        "raw_events": raw_events,
        "active_veto_pass_events": active_events,
        "side_compton_fov_pass_events": final_events,
        "raw_rate_s-1": raw_rate,
        "active_veto_pass_rate_s-1": active_rate,
        "side_compton_fov_pass_rate_s-1": final_rate,
        "active_veto_survival_fraction": active_rate / raw_rate if raw_rate > 0.0 else None,
        "side_compton_fov_survival_fraction_vs_active": final_rate / active_rate if active_rate > 0.0 else None,
        "side_compton_class_counts": dict(sorted(class_counts.items())),
        "selected_examples": examples,
    }
    prompt_rates = load_prompt_rates(CURRENT_PROMPT_DIR)
    return {
        "prompt_dir": rel(CURRENT_PROMPT_DIR),
        "source_cache": rel(cache_path),
        "sim_files": sorted(sim_files),
        "rate_per_event_s-1_from_prompt_norm": prompt_rates.get(tag),
        "summary": summary,
        "files": [],
    }


def summarize_current_final_by_tag(step05, cache_path: Path, disk: dict[str, Any], reject_policy: str) -> dict[str, Any]:
    with cache_path.open("rb") as fh:
        cat = pickle.load(fh)

    by_tag: dict[str, dict[str, Any]] = {}
    for idx in range(len(cat["stream"])):
        if str(cat["stream"][idx]) != "prompt":
            continue
        tag = str(cat["tag"][idx])
        row = by_tag.setdefault(
            tag,
            {
                "tag": tag,
                "raw_events": 0,
                "raw_rate_s-1": 0.0,
                "active_veto_pass_events": 0,
                "active_veto_pass_rate_s-1": 0.0,
                "side_compton_fov_pass_events": 0,
                "side_compton_fov_pass_rate_s-1": 0.0,
            },
        )
        tes_total = float(cat["tes_total_keV"][idx])
        if not (LINE_WINDOW[0] <= tes_total < LINE_WINDOW[1]):
            continue
        rate = float(cat["rate_hz"][idx])
        row["raw_events"] += 1
        row["raw_rate_s-1"] += rate
        bgo_total = float(cat["bgo_total_keV"][idx])
        if bgo_total >= ACTIVE_VETO_THRESHOLD_KEV:
            continue
        row["active_veto_pass_events"] += 1
        row["active_veto_pass_rate_s-1"] += rate
        keep, _cls = step05.side_keep_from_hits(step05.event_hits(cat, idx), disk, reject_policy)
        if keep:
            row["side_compton_fov_pass_events"] += 1
            row["side_compton_fov_pass_rate_s-1"] += rate
    return dict(sorted(by_tag.items()))


def ratio(num: float, den: float) -> float | None:
    return num / den if den > 0.0 else None


def poisson_ratio_sigma(num_events: int, den_events: int, r: float | None) -> float | None:
    if r is None or num_events <= 0 or den_events <= 0:
        return None
    return r * math.sqrt(1.0 / num_events + 1.0 / den_events)


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Prompt-511 Repack L1-like Proxy",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This is a prompt-only Step05-like diagnostic. It reuses the official v3p5",
        "TES line window, CsI active-veto threshold, and side-entry Compton/FoV",
        "proxy, but it is not a delayed, signal, Step06, Step07, or Step08",
        "authority.",
        "",
    ]
    repack_dirs = [
        Path(pair["w_liner_repack"]["prompt_dir"]).name
        for pair in payload["particle_cases"].values()
    ]
    seed_correct = all("cli_seed" in name for name in repack_dirs)
    if seed_correct:
        lines.extend(
            [
                "Seed policy: the repack rows below use command-line",
                "`cosima -s <seed>` runs. The companion seed audit documents why",
                "the older source-card-Seed repack rows were not independent.",
                "",
            ]
        )
    elif SEED_AUDIT_MD.exists():
        lines.extend(
            [
                "Seed-independence caveat: the companion audit",
                f"`{rel(SEED_AUDIT_MD)}` shows that the existing W-liner repack",
                "eplus/n replicas are not independent. Source-card `Seed` changes",
                "repeated a small eplus check, while command-line `cosima -s` seeds",
                "produced different SIM hashes. The numeric repack rows below are",
                "therefore diagnostic repeated-seed rows, not high-stat closure.",
                "",
            ]
        )
    lines.extend(
        [
            f"Window: `{payload['line_window_keV'][0]} <= TES_total_keV < {payload['line_window_keV'][1]}`.",
            f"Active-veto threshold: `{payload['active_veto_threshold_keV']} keV`.",
            "",
            "| case | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name in ("current_baseline", "w_liner_repack"):
        row = payload["cases"][name]["summary"]
        lines.append(
            f"| {name} | {row['raw_events']} | {row['raw_rate_s-1']:.6g} | "
            f"{row['active_veto_pass_events']} | {row['active_veto_pass_rate_s-1']:.6g} | "
            f"{row['side_compton_fov_pass_events']} | {row['side_compton_fov_pass_rate_s-1']:.6g} |"
        )
    lines.extend(["", "Current/repack suppression factors:", ""])
    for stage, row in payload["current_over_repack_ratios"].items():
        sigma = row["counting_only_1sigma"]
        suffix = "" if sigma is None else f" +/- {sigma:.3g}"
        lines.append(f"- {stage}: `{row['ratio']:.6g}{suffix}`")
    lines.extend(
        [
            "",
            "Follow-up particle cases included in this run:",
            "",
            "| tag | current L1-like events | current cps | repack L1-like events | repack cps | current/repack |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for tag, pair in payload["particle_cases"].items():
        cur = pair["current_baseline"]["summary"]
        rep = pair["w_liner_repack"]["summary"]
        rat = payload["particle_ratios"][tag]["side_compton_fov_pass"]["ratio"]
        rat_s = "" if rat is None else f"{rat:.6g}"
        lines.append(
            f"| {tag} | {cur['side_compton_fov_pass_events']} | "
            f"{cur['side_compton_fov_pass_rate_s-1']:.6g} | "
            f"{rep['side_compton_fov_pass_events']} | "
            f"{rep['side_compton_fov_pass_rate_s-1']:.6g} | {rat_s} |"
        )

    proj = payload["total_prompt_projection"]
    lines.extend(
        [
            "",
            "Total prompt projection:",
            "",
            f"- current official Step05-like prompt total: `{proj['current_total_s-1']:.6g} cps`.",
            f"- projected prompt total with available repack particle runs: `{proj['projected_total_s-1']:.6g} cps`.",
            f"- old `new_geo_re` prompt total: `{proj['old_new_geo_re_prompt_total_s-1']:.6g} cps`.",
            f"- projected/old ratio: `{proj['projected_over_old_prompt_total']:.6g}`.",
            f"- repack-replaced tags: `{', '.join(proj['repack_replaced_tags'])}`.",
            f"- current-carried tags: `{', '.join(proj['current_carried_tags'])}`.",
            "",
            "Interpretation:",
            "",
            "- The W liner still suppresses the current eplus leakage after applying",
            "  active-veto and side Compton/FoV proxy stages.",
            "- The seed-correct n follow-up strengthens the hardware-risk interpretation:",
            "  W-only raises the surviving n component enough that the eplus+n projection",
            "  remains above old `new_geo_re` at the central value.",
            "- Follow-up particle rows are included only when their repack run has a",
            "  completed run summary; otherwise the projection carries the current",
            "  official prompt contribution for that tag.",
            "- The result remains a geometry/prompt diagnostic only because new W",
            "  activation and delayed-source rebuild are not included.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    step05 = load_module("build_v3p5_centerfinger_step05_l1_response_for_repack_l1", ROOT / "code/tools/build_v3p5_centerfinger_step05_l1_response.py")
    disk = step05.side_entry_disk()
    reject_policy = "keep"

    particle_cases: dict[str, Any] = {}
    for tag, prompt_dir in REPACK_PROMPT_DIR_BY_TAG.items():
        if not repack_dir_ready(prompt_dir, tag):
            continue
        particle_cases[tag] = {
            "current_baseline": summarize_catalog_case(
                step05, CURRENT_STEP05_CACHE, disk, reject_policy, stream="prompt", tag=tag
            ),
            "w_liner_repack": summarize_prompt_dir(step05, prompt_dir, disk, reject_policy, tag=tag),
        }

    if "eplus" not in particle_cases:
        raise RuntimeError("eplus repack case is required")

    cases = particle_cases["eplus"]

    ratios = {}
    stages = {
        "raw": ("raw_rate_s-1", "raw_events"),
        "active_veto_pass": ("active_veto_pass_rate_s-1", "active_veto_pass_events"),
        "side_compton_fov_pass": ("side_compton_fov_pass_rate_s-1", "side_compton_fov_pass_events"),
    }
    particle_ratios = {}
    for tag, pair in particle_cases.items():
        particle_ratios[tag] = {}
        cur = pair["current_baseline"]["summary"]
        rep = pair["w_liner_repack"]["summary"]
        for stage, (rate_key, event_key) in stages.items():
            r = ratio(float(cur[rate_key]), float(rep[rate_key]))
            particle_ratios[tag][stage] = {
                "ratio": r,
                "counting_only_1sigma": poisson_ratio_sigma(int(cur[event_key]), int(rep[event_key]), r),
                "current_events": int(cur[event_key]),
                "repack_events": int(rep[event_key]),
            }
    ratios = particle_ratios["eplus"]

    current_by_tag = summarize_current_final_by_tag(step05, CURRENT_STEP05_CACHE, disk, reject_policy)
    current_final_rates = {
        tag: float(row["side_compton_fov_pass_rate_s-1"])
        for tag, row in current_by_tag.items()
        if float(row["side_compton_fov_pass_rate_s-1"]) > 0.0
    }
    projected_rates = dict(current_final_rates)
    for tag, pair in particle_cases.items():
        projected_rates[tag] = float(pair["w_liner_repack"]["summary"]["side_compton_fov_pass_rate_s-1"])
    current_total = sum(current_final_rates.values())
    projected_total = sum(projected_rates.values())
    current_carried_tags = sorted(set(current_final_rates) - set(particle_cases))

    payload = {
        "status": "PASS_PROMPT511_REPACK_L1_PROXY",
        "claim_level": "prompt-only Step05-like proxy; not rate authority",
        "line_window_keV": list(LINE_WINDOW),
        "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
        "reject_policy": reject_policy,
        "side_entry_disk": {
            "center_cm": [float(x) for x in disk["center_cm"]],
            "normal": [float(x) for x in disk["normal"]],
            "radius_cm": float(disk["radius_cm"]),
            "local_center_cm": list(disk["local_center_cm"]),
            "rotation_y_deg": float(disk["rotation_y_deg"]),
        },
        "cases": cases,
        "particle_cases": particle_cases,
        "current_over_repack_ratios": ratios,
        "particle_ratios": particle_ratios,
        "current_final_prompt_by_tag": current_by_tag,
        "total_prompt_projection": {
            "current_total_s-1": current_total,
            "projected_total_s-1": projected_total,
            "old_new_geo_re_prompt_total_s-1": OLD_NEW_GEO_RE_PROMPT_TOTAL_CPS,
            "old_new_geo_re_prompt_eplus_s-1": OLD_NEW_GEO_RE_PROMPT_EPLUS_CPS,
            "projected_over_old_prompt_total": projected_total / OLD_NEW_GEO_RE_PROMPT_TOTAL_CPS,
            "repack_replaced_tags": sorted(particle_cases),
            "current_carried_tags": current_carried_tags,
            "projected_by_tag_s-1": dict(sorted(projected_rates.items())),
            "current_final_by_tag_s-1": dict(sorted(current_final_rates.items())),
        },
        "limitations": [
            "Only completed repack prompt particle runs are parsed.",
            "The current baseline is replayed from the official Step05 event_catalog cache instead of reparsing SIM gzip files.",
            "No delayed activation, no science signal, no common Poisson time axis.",
            "The W-liner delayed activation inventory is not rebuilt here.",
            "This proxy is evidence for local prompt suppression only, not for final sensitivity.",
        ],
    }
    SUMMARY_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text(markdown(payload) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON), "report": rel(SUMMARY_MD)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
