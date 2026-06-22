#!/usr/bin/env python3
"""Build a v3p5 fullstat exact-RPIP delayed source.

This promotes the real-position smoke-test method to the current v3p5 fullstat
chain: sample decays from true ``CC IP RP`` production positions, weighted by
the ground-state-fixed source activity, and emit one Cosima ``PointSource``
block per sampled decay.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import multiprocessing as mp
import random
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BASE_LABEL = "fullstat_v2"
DEFAULT_EXACT_LABEL = "fullstat_v2_exactpos"
EXACT_LABEL = DEFAULT_EXACT_LABEL

BUILDUP = ROOT / "runs" / "step02_buildup_v3p5_centerfinger_fullstat_v2"
BASE_STEP02 = (
    ROOT
    / "stepwise_maintenance"
    / "step02_raw_background_simulation"
    / "outputs_v3p5_centerfinger_fullstat_v2"
    / "step02_v3p5_centerfinger_fullstat_v2_summary.json"
)
BASE_SOURCE_DIR = ROOT / "runs" / "step02_decay_source_v3p5_centerfinger_fullstat_v2"
BASE_FIXED_DIR = ROOT / "runs" / "step02_delay_fix_v3p5_centerfinger_fullstat_v2"
BASE_FIXED_SOURCE = BASE_FIXED_DIR / "activation_decay_day15_groundstate_fixed.source"
BASE_AUDIT = BASE_SOURCE_DIR / "normalization_audit_day15.json"

CANONICAL_TABLE_DIR = ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{DEFAULT_EXACT_LABEL}"
OUT_SOURCE_DIR = ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{EXACT_LABEL}"
OUT_TRANSPORT_DIR = ROOT / "runs" / f"step02_delayed_transport_v3p5_centerfinger_{EXACT_LABEL}"
OUT_STEP02 = ROOT / "stepwise_maintenance" / "step02_raw_background_simulation" / f"outputs_v3p5_centerfinger_{EXACT_LABEL}"
TABLE = CANONICAL_TABLE_DIR / "exactpos_weighted_rpip_table.csv"
TABLE_SUMMARY = CANONICAL_TABLE_DIR / "exactpos_weighted_rpip_summary.json"
SOURCE = OUT_SOURCE_DIR / "activation_decay_day15_groundstate_fixed.source"
MANIFEST = OUT_SOURCE_DIR / "exactpos_delayed_source_manifest.json"
STEP02_SUMMARY = OUT_STEP02 / f"step02_v3p5_centerfinger_{EXACT_LABEL}_summary.json"
STEP02_MD = OUT_STEP02 / f"step02_v3p5_centerfinger_{EXACT_LABEL}_summary.md"

SOURCE_PREFIX = OUT_TRANSPORT_DIR / "DelayedDecayRPIPGroundStateFixed"
DEFAULT_GEOMETRY = ROOT / "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"

TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)
SOURCE_NAME_RE = re.compile(r"^S_(?P<vn>.+)_(?P<za>\d+)_z\d+$")
PARTICLE_RE = re.compile(r"^(?P<name>S_\S+)\.ParticleType\s+(?P<za>\d+)\s*$")
FLUX_RE = re.compile(r"^(?P<name>S_\S+)\.Flux\s+(?P<flux>[-+0-9.eE]+)\s*$")
GEOMETRY_RE = re.compile(r"^Geometry\s+(?P<path>\S+)\s*$")
TRIGGERS_RE = re.compile(r"^DecayRun\.Triggers\s+(?P<triggers>\d+)\s*$")
NUM = r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
IP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<vn>\S+)\s+"
    rf"(?P<x>{NUM})\s+(?P<y>{NUM})\s+(?P<z>{NUM})\s+"
    rf"(?P<za>\d+)\s+(?P<exc>{NUM})\s+(?P<t>{NUM})"
)
RE_SEG_SHIELD = re.compile(r"^(Nb_Shield|W_Shield|Cryo_Shell|BGO_Shield|Al_Shell)(?:_p\d+_z\d+)?$", re.I)
RE_TP = re.compile(r"^TP_L(?P<l>\d+)_\d+$", re.I)
RE_TESPIX = re.compile(r"^TES_Pixel_L(?P<l>\d+)$", re.I)
RE_COLLBAR = re.compile(r"^(CollBar[XY])_\d+$", re.I)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def configure_label(label: str) -> None:
    global EXACT_LABEL, OUT_SOURCE_DIR, OUT_TRANSPORT_DIR, OUT_STEP02
    global SOURCE, MANIFEST, STEP02_SUMMARY, STEP02_MD, SOURCE_PREFIX

    if not label.startswith(DEFAULT_EXACT_LABEL):
        raise SystemExit(f"exact-position labels must start with {DEFAULT_EXACT_LABEL!r}: {label}")
    EXACT_LABEL = label
    OUT_SOURCE_DIR = ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{label}"
    OUT_TRANSPORT_DIR = ROOT / "runs" / f"step02_delayed_transport_v3p5_centerfinger_{label}"
    OUT_STEP02 = ROOT / "stepwise_maintenance" / "step02_raw_background_simulation" / f"outputs_v3p5_centerfinger_{label}"
    SOURCE = OUT_SOURCE_DIR / "activation_decay_day15_groundstate_fixed.source"
    MANIFEST = OUT_SOURCE_DIR / "exactpos_delayed_source_manifest.json"
    STEP02_SUMMARY = OUT_STEP02 / f"step02_v3p5_centerfinger_{label}_summary.json"
    STEP02_MD = OUT_STEP02 / f"step02_v3p5_centerfinger_{label}_summary.md"
    SOURCE_PREFIX = OUT_TRANSPORT_DIR / "DelayedDecayRPIPGroundStateFixed"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def parse_tag(path: Path | str) -> str:
    m = TAG_RE.search(Path(path).name)
    return m.group("tag").lower() if m else "unknown"


def canon_vn(vn: str) -> str:
    if not vn:
        return "Other"
    m = RE_SEG_SHIELD.match(vn)
    if m:
        return m.group(1)
    m = RE_TESPIX.match(vn)
    if m:
        return f"TES_L{int(m.group('l'))}"
    if vn.startswith("TES_L"):
        return vn
    m = RE_TP.match(vn)
    if m:
        return f"TES_L{int(m.group('l'))}"
    m = RE_COLLBAR.match(vn)
    if m:
        return m.group(1)
    if vn in ("Cu_Base", "Cu_SupportPole", "CU_BASE", "CU_SUPPORT", "Copper"):
        return "Copper"
    if vn in ("Collimator", "CollimatorVac", "CollimatorEnvelope"):
        return "CollimatorVac"
    if "window" in vn.lower() or vn.lower().startswith("win"):
        return "Window"
    return vn


def division_by_tag() -> dict[str, float]:
    audit = load_json(BASE_AUDIT)
    if audit.get("status") != "PASS":
        raise SystemExit(f"normalization audit is not PASS: {BASE_AUDIT}")
    return {row["tag"]: float(row["division"]) for row in audit["rows"]}


def parse_fixed_source() -> dict[str, Any]:
    lines = BASE_FIXED_SOURCE.read_text(encoding="utf-8", errors="ignore").splitlines()
    name_za: dict[str, int] = {}
    name_flux: dict[str, float] = {}
    key_flux: dict[tuple[str, int], float] = defaultdict(float)
    source_blocks = 0
    geometry = DEFAULT_GEOMETRY
    triggers = 1_000_000
    for line in lines:
        stripped = line.strip()
        gm = GEOMETRY_RE.match(stripped)
        if gm:
            geometry = (ROOT / gm.group("path")).resolve() if not Path(gm.group("path")).is_absolute() else Path(gm.group("path"))
        tm = TRIGGERS_RE.match(stripped)
        if tm:
            triggers = int(tm.group("triggers"))
        pm = PARTICLE_RE.match(stripped)
        if pm:
            name_za[pm.group("name")] = int(pm.group("za"))
            source_blocks += 1
        fm = FLUX_RE.match(stripped)
        if fm:
            name_flux[fm.group("name")] = float(fm.group("flux"))
    for name, za in name_za.items():
        sm = SOURCE_NAME_RE.match(name)
        flux = name_flux.get(name, 0.0)
        if sm and flux > 0.0:
            key_flux[(sm.group("vn"), za)] += flux
    return {
        "geometry": geometry,
        "triggers": triggers,
        "source_blocks": source_blocks,
        "activity_by_key": dict(key_flux),
        "total_activity_Bq": sum(key_flux.values()),
    }


def parse_one_sim(args_tuple: tuple[str, dict[str, float]]) -> dict[str, Any]:
    fp = Path(args_tuple[0])
    divs = args_tuple[1]
    tag = parse_tag(fp)
    div = float(divs.get(tag, 1.0))
    wfile = 1.0 / div if div > 0.0 else 1.0
    rows: list[tuple[str, int, float, float, float, float, float, str]] = []
    n_cc_ip_rp = 0
    with open_text(fp) as handle:
        for raw in handle:
            if not raw.startswith("CC IP RP"):
                continue
            n_cc_ip_rp += 1
            m = IP_RE.match(raw.strip())
            if not m:
                continue
            exc = float(m.group("exc"))
            if abs(exc) < 1.0e-6:
                exc = 0.0
            rows.append(
                (
                    canon_vn(m.group("vn")),
                    int(m.group("za")),
                    exc,
                    wfile,
                    float(m.group("x")),
                    float(m.group("y")),
                    float(m.group("z")),
                    fp.name,
                )
            )
    return {"file": fp.name, "tag": tag, "wfile": wfile, "n_cc_ip_rp": n_cc_ip_rp, "rows": rows}


def build_weighted_table(workers: int, force: bool) -> dict[str, Any]:
    if TABLE.exists() and TABLE_SUMMARY.exists() and not force:
        return load_json(TABLE_SUMMARY)
    CANONICAL_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    divs = division_by_tag()
    fixed = parse_fixed_source()
    activity_by_key: dict[tuple[str, int], float] = fixed["activity_by_key"]
    files = sorted(BUILDUP.glob("*.sim.gz"))
    if not files:
        raise SystemExit(f"no buildup SIM files in {BUILDUP}")
    task_args = [(str(path), divs) for path in files]
    ctx = mp.get_context("fork") if sys.platform.startswith("linux") else mp.get_context("spawn")
    t0 = time.time()
    results: list[dict[str, Any]] = []
    with ctx.Pool(processes=max(1, workers)) as pool:
        for idx, result in enumerate(pool.imap_unordered(parse_one_sim, task_args), 1):
            results.append(result)
            print(
                f"[{idx:02d}/{len(files):02d}] {result['file']}: "
                f"{len(result['rows'])} RP rows (wfile={result['wfile']:.6g})",
                flush=True,
            )

    total_rows = 0
    eligible_rows = 0
    total_cc_ip_rp = 0
    tag_rows: Counter[str] = Counter()
    source_weight_by_key: dict[tuple[str, int], float] = defaultdict(float)
    missing_fixed_keys = set(activity_by_key)
    for result in results:
        total_cc_ip_rp += int(result["n_cc_ip_rp"])
        tag_rows[result["tag"]] += len(result["rows"])
        for vn, za, _exc, wfile, _x, _y, _z, _src in result["rows"]:
            total_rows += 1
            key = (vn, za)
            if key in activity_by_key:
                eligible_rows += 1
                source_weight_by_key[key] += float(wfile)
                missing_fixed_keys.discard(key)

    if missing_fixed_keys:
        preview = sorted([f"{vn}:{za}" for vn, za in missing_fixed_keys])[:20]
        raise SystemExit(f"{len(missing_fixed_keys)} fixed activity keys have no exact RPIP rows: {preview}")

    with TABLE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["VN", "ZA", "exc_keV", "wfile", "source_file", "x_cm", "y_cm", "z_cm", "sample_weight"])
        for result in results:
            for vn, za, exc, wfile, x, y, z, src in result["rows"]:
                key = (vn, za)
                activity = activity_by_key.get(key, 0.0)
                if activity <= 0.0:
                    continue
                denom = source_weight_by_key[key]
                sample_weight = activity * float(wfile) / denom if denom > 0.0 else 0.0
                if sample_weight <= 0.0:
                    continue
                writer.writerow(
                    [
                        vn,
                        za,
                        f"{exc:.6g}",
                        f"{float(wfile):.8g}",
                        src,
                        f"{float(x):.6f}",
                        f"{float(y):.6f}",
                        f"{float(z):.6f}",
                        f"{sample_weight:.12e}",
                    ]
                )

    summary = {
        "status": "PASS_EXACTPOS_WEIGHTED_RPIP_TABLE",
        "label": DEFAULT_EXACT_LABEL,
        "base_label": BASE_LABEL,
        "buildup_dir": rel(BUILDUP),
        "files_parsed": len(files),
        "normalization_audit": rel(BASE_AUDIT),
        "fixed_source": rel(BASE_FIXED_SOURCE),
        "fixed_source_blocks": fixed["source_blocks"],
        "fixed_activity_keys": len(activity_by_key),
        "fixed_total_activity_Bq": fixed["total_activity_Bq"],
        "total_cc_ip_rp_lines_seen": total_cc_ip_rp,
        "rp_rows_seen": total_rows,
        "eligible_rows_written": eligible_rows,
        "rp_rows_by_tag": dict(tag_rows),
        "division_by_tag": divs,
        "table": rel(TABLE),
        "elapsed_s": round(time.time() - t0, 1),
        "method": "sample_weight = fixed_activity_Bq(VN,ZA) * wfile / sum_wfile(VN,ZA), with wfile from current normalization audit",
    }
    write_json(TABLE_SUMMARY, summary)
    return summary


def load_sampling_rows() -> tuple[list[dict[str, Any]], list[float]]:
    rows: list[dict[str, Any]] = []
    weights: list[float] = []
    with TABLE.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            weight = float(row["sample_weight"])
            if weight <= 0.0:
                continue
            rows.append(
                {
                    "VN": row["VN"],
                    "ZA": int(row["ZA"]),
                    "exc_keV": float(row["exc_keV"]),
                    "x_cm": float(row["x_cm"]),
                    "y_cm": float(row["y_cm"]),
                    "z_cm": float(row["z_cm"]),
                }
            )
            weights.append(weight)
    if not rows:
        raise SystemExit(f"no positive sampling rows in {TABLE}")
    return rows, weights


def weighted_sample_indices(weights: list[float], n: int, seed: int) -> list[int]:
    total = math.fsum(weights)
    if total <= 0.0:
        raise SystemExit("sampling weights sum to zero")
    cdf: list[float] = []
    run = 0.0
    for weight in weights:
        run += weight
        cdf.append(run)
    rng = random.Random(seed)
    out: list[int] = []
    for _ in range(n):
        x = rng.random() * total
        lo, hi = 0, len(cdf) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cdf[mid] < x:
                lo = mid + 1
            else:
                hi = mid
        out.append(lo)
    return out


def write_weighted_table_source(triggers: int) -> dict[str, Any]:
    table_summary = build_weighted_table(workers=1, force=False)
    fixed = parse_fixed_source()
    geometry = fixed["geometry"]
    n_blocks = int(table_summary["eligible_rows_written"])
    OUT_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_TRANSPORT_DIR.mkdir(parents=True, exist_ok=True)

    source_lines = [
        "Version 1",
        f"Geometry {geometry}",
        "",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "PhysicsListRadioactiveDecay true",
        "DecayMode ActivationDelayedDecay",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
        "DetectorTimeConstant 1e-9",
        "",
        "Run DecayRun",
        f"DecayRun.FileName {SOURCE_PREFIX}",
        f"DecayRun.Triggers {int(triggers)}",
        "",
    ]
    source_lines.extend(f"DecayRun.Source RP_{i:06d}" for i in range(n_blocks))
    source_lines.append("")
    source_lines.append("# ===== exact-RPIP weighted-table PointSource decay blocks =====")

    flux_sum = 0.0
    top_flux: dict[tuple[str, int], float] = defaultdict(float)
    with SOURCE.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(source_lines) + "\n")
        with TABLE.open("r", encoding="utf-8", newline="") as table_handle:
            for i, row in enumerate(csv.DictReader(table_handle)):
                flux = float(row["sample_weight"])
                za = int(row["ZA"])
                flux_sum += flux
                top_flux[(row["VN"], za)] += flux
                name = f"RP_{i:06d}"
                handle.write(f"{name}.ParticleType {za}\n")
                handle.write(f"{name}.Beam PointSource {float(row['x_cm']):.6f} {float(row['y_cm']):.6f} {float(row['z_cm']):.6f}\n")
                handle.write(f"{name}.Flux {flux:.8e}\n\n")

    manifest = base_manifest(
        table_summary=table_summary,
        fixed=fixed,
        source_mode="weighted_table_all_eligible_rpip_points",
        triggers=triggers,
        seed=None,
        n_pointsource_blocks=n_blocks,
        flux_per_pointsource_Bq=None,
        sum_flux_check_Bq=flux_sum,
        distinct_species=len(top_flux),
        top_species=[
            {"VN": vn, "ZA": za, "activity_Bq": flux}
            for (vn, za), flux in sorted(top_flux.items(), key=lambda item: item[1], reverse=True)[:20]
        ],
    )
    finish_source_outputs(manifest)
    return manifest


def write_sampled_source(n_decays: int, triggers: int, seed: int) -> dict[str, Any]:
    table_summary = build_weighted_table(workers=1, force=False)
    fixed = parse_fixed_source()
    geometry = fixed["geometry"]
    rows, weights = load_sampling_rows()
    indices = weighted_sample_indices(weights, n_decays, seed)
    total_activity = float(fixed["total_activity_Bq"])
    flux_per_source = total_activity / float(n_decays)
    expected_by_species = expected_draws_by_species(rows, weights, n_decays)
    OUT_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_TRANSPORT_DIR.mkdir(parents=True, exist_ok=True)

    species_counts: Counter[tuple[str, int]] = Counter()
    source_lines = [
        "Version 1",
        f"Geometry {geometry}",
        "",
        "PhysicsListHD qgsp-bic-hp",
        "PhysicsListEM LivermorePol",
        "PhysicsListRadioactiveDecay true",
        "DecayMode ActivationDelayedDecay",
        "StoreSimulationInfo all",
        "StoreIsotopes true",
        "DetectorTimeConstant 1e-9",
        "",
        "Run DecayRun",
        f"DecayRun.FileName {SOURCE_PREFIX}",
        f"DecayRun.Triggers {int(triggers)}",
        "",
    ]
    source_lines.extend(f"DecayRun.Source RP_{i:07d}" for i in range(n_decays))
    source_lines.append("")
    source_lines.append("# ===== exact-RPIP PointSource decay blocks =====")
    with SOURCE.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(source_lines) + "\n")
        for i, row_idx in enumerate(indices):
            row = rows[row_idx]
            species_counts[(row["VN"], row["ZA"])] += 1
            name = f"RP_{i:07d}"
            handle.write(f"{name}.ParticleType {row['ZA']}\n")
            handle.write(f"{name}.Beam PointSource {row['x_cm']:.6f} {row['y_cm']:.6f} {row['z_cm']:.6f}\n")
            handle.write(f"{name}.Flux {flux_per_source:.8e}\n\n")

    manifest = base_manifest(
        table_summary=table_summary,
        fixed=fixed,
        source_mode="sampled_equal_flux_pointsource_blocks",
        triggers=triggers,
        seed=seed,
        n_pointsource_blocks=n_decays,
        flux_per_pointsource_Bq=flux_per_source,
        sum_flux_check_Bq=flux_per_source * n_decays,
        distinct_species=len(species_counts),
        top_species=[
            {"VN": vn, "ZA": za, "drawn": count}
            for (vn, za), count in species_counts.most_common(20)
        ],
        sampling_audit=sampled_source_audit(
            expected_by_species=expected_by_species,
            observed_by_species=species_counts,
            n_decays=n_decays,
            total_activity_Bq=total_activity,
            sum_flux_check_Bq=flux_per_source * n_decays,
        ),
    )
    finish_source_outputs(manifest)
    return manifest


def expected_draws_by_species(rows: list[dict[str, Any]], weights: list[float], n_decays: int) -> dict[tuple[str, int], float]:
    total = math.fsum(weights)
    if total <= 0.0:
        raise SystemExit("sampling weights sum to zero")
    expected: dict[tuple[str, int], float] = defaultdict(float)
    scale = float(n_decays) / total
    for row, weight in zip(rows, weights):
        expected[(row["VN"], int(row["ZA"]))] += weight * scale
    return dict(expected)


def sampled_source_audit(
    *,
    expected_by_species: dict[tuple[str, int], float],
    observed_by_species: Counter[tuple[str, int]],
    n_decays: int,
    total_activity_Bq: float,
    sum_flux_check_Bq: float,
) -> dict[str, Any]:
    top_rows: list[dict[str, Any]] = []
    max_abs_sigma = 0.0
    chi2_top = 0.0
    for (vn, za), expected in sorted(expected_by_species.items(), key=lambda item: item[1], reverse=True)[:20]:
        observed = int(observed_by_species.get((vn, za), 0))
        sigma = math.sqrt(expected * max(1.0 - expected / float(n_decays), 0.0)) if expected > 0.0 else 0.0
        sigma_delta = (observed - expected) / sigma if sigma > 0.0 else 0.0
        rel_delta = (observed - expected) / expected if expected > 0.0 else 0.0
        max_abs_sigma = max(max_abs_sigma, abs(sigma_delta))
        chi2_top += ((observed - expected) ** 2 / expected) if expected > 0.0 else 0.0
        top_rows.append(
            {
                "VN": vn,
                "ZA": za,
                "expected_draws": expected,
                "observed_draws": observed,
                "relative_delta": rel_delta,
                "sigma_delta": sigma_delta,
            }
        )
    flux_abs_delta = abs(float(sum_flux_check_Bq) - float(total_activity_Bq))
    status = "PASS"
    problems: list[str] = []
    if flux_abs_delta > max(1.0e-9, 1.0e-12 * total_activity_Bq):
        status = "FAIL"
        problems.append(f"sum_flux_check_Bq differs from fixed_total_activity_Bq by {flux_abs_delta:.12g} Bq")
    if max_abs_sigma > 8.0:
        status = "WARN" if status == "PASS" else status
        problems.append(f"top-20 species draw deviation has max_abs_sigma={max_abs_sigma:.3g}; check support-size/seed stability")
    return {
        "status": status,
        "scope": "sampled_equal_flux_pointsource_blocks_species_level_audit",
        "n_decays": int(n_decays),
        "species_with_expected_draws": len(expected_by_species),
        "species_drawn": len(observed_by_species),
        "sum_flux_abs_delta_Bq": flux_abs_delta,
        "sum_flux_relative_delta": flux_abs_delta / total_activity_Bq if total_activity_Bq > 0.0 else math.inf,
        "top20_expected_species_chi2": chi2_top,
        "top20_max_abs_sigma_delta": max_abs_sigma,
        "top20_expected_species": top_rows,
        "problems": problems,
        "interpretation": (
            "This audit checks activity conservation exactly and records species-level multinomial draw deviations. "
            "It is not a substitute for support-size/seed convergence of the final W2 delayed rate."
        ),
    }


def base_manifest(
    *,
    table_summary: dict[str, Any],
    fixed: dict[str, Any],
    source_mode: str,
    triggers: int,
    seed: int | None,
    n_pointsource_blocks: int,
    flux_per_pointsource_Bq: float | None,
    sum_flux_check_Bq: float,
    distinct_species: int,
    top_species: list[dict[str, Any]],
    sampling_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "status": "PASS_V3P5_EXACTPOS_DELAYED_SOURCE",
        "label": EXACT_LABEL,
        "base_label": BASE_LABEL,
        "method": "exact_RPIP_PointSource_fixed_inventory",
        "source_mode": source_mode,
        "source": rel(SOURCE),
        "outfile_prefix": rel(SOURCE_PREFIX),
        "geometry": rel(Path(fixed["geometry"])),
        "table_summary": rel(TABLE_SUMMARY),
        "table": rel(TABLE),
        "fixed_source": rel(BASE_FIXED_SOURCE),
        "fixed_total_activity_Bq": float(fixed["total_activity_Bq"]),
        "n_pointsource_blocks": int(n_pointsource_blocks),
        "n_decays_emitted": int(n_pointsource_blocks),
        "triggers_requested": int(triggers),
        "flux_per_pointsource_Bq": flux_per_pointsource_Bq,
        "sum_flux_check_Bq": float(sum_flux_check_Bq),
        "seed": seed,
        "sampling_rows": int(table_summary["eligible_rows_written"]),
        "distinct_species_drawn": int(distinct_species),
        "top_drawn_species": top_species,
        "sampling_audit": sampling_audit,
        "production_semantics": (
            "Fixed source activity is preserved by summing ground-state-fixed Flux over each (VN,ZA); "
            "true RPIP positions are sampled with replacement using current Step03 wfile normalization."
            if source_mode == "sampled_equal_flux_pointsource_blocks"
            else "Fixed source activity is preserved by assigning each eligible true RPIP row a PointSource Flux equal to its fixed-inventory activity weight."
        ),
        "table_summary_payload": table_summary,
    }
    if sampling_audit is None:
        payload["sampling_audit"] = {
            "status": "PASS",
            "scope": "weighted_table_all_eligible_rpip_points",
            "interpretation": "No multinomial draw audit is needed because every eligible weighted RPIP row is emitted.",
        }
    return payload


def finish_source_outputs(manifest: dict[str, Any]) -> None:
    for src in [
        BASE_FIXED_DIR / "groundstate_activity_corrections.csv",
        BASE_FIXED_DIR / "normalization_audit_groundstate_fix.csv",
        BASE_FIXED_DIR / "normalization_audit_groundstate_fix.json",
        BASE_FIXED_DIR / "source_fix_summary.json",
    ]:
        if src.exists():
            shutil.copy2(src, OUT_SOURCE_DIR / src.name)
    write_json(MANIFEST, manifest)
    write_step02_summary(manifest)


def write_step02_summary(manifest: dict[str, Any]) -> None:
    base = load_json(BASE_STEP02)
    base["status"] = "PASS_FULLSTAT_V2_EXACTPOS_SOURCE_READY_TRANSPORT_PENDING"
    base["statistics_label"] = EXACT_LABEL
    base["scope"] = "all-particle fullstat_v2 exact-position delayed-source closure"
    base["known_limitations"] = exactpos_known_limitations(manifest)
    base["exact_position_delayed_source"] = {
        "status": manifest["status"],
        "source": manifest["source"],
        "manifest": rel(MANIFEST),
        "table_summary": rel(TABLE_SUMMARY),
        "source_mode": manifest["source_mode"],
        "n_pointsource_blocks": manifest["n_pointsource_blocks"],
        "triggers_requested": manifest["triggers_requested"],
        "fixed_total_activity_Bq": manifest["fixed_total_activity_Bq"],
        "flux_per_pointsource_Bq": manifest["flux_per_pointsource_Bq"],
        "sum_flux_check_Bq": manifest["sum_flux_check_Bq"],
    }
    base["delayed_transport"] = {
        "path": rel(SOURCE_PREFIX) + ".inc1.id1.sim.gz",
        "SE": None,
        "ID": None,
        "TS": None,
        "TE_s": None,
        "geometry": manifest["geometry"],
        "TE_source": "pending Cosima transport; final TE is read from the SIM TE record",
        "status": "PENDING_COSIMA_RERUN",
    }
    write_json(STEP02_SUMMARY, base)
    STEP02_MD.parent.mkdir(parents=True, exist_ok=True)
    STEP02_MD.write_text(
        "\n".join(
            [
                "# Step02 v3p5 Center-Finger Fullstat v2 Exact-Position Delayed Source",
                "",
                f"Status: `{base['status']}`.",
                "",
                f"- source: `{manifest['source']}`",
                f"- manifest: `{rel(MANIFEST)}`",
                f"- weighted RPIP table: `{rel(TABLE)}`",
                f"- source mode: `{manifest['source_mode']}`",
                f"- PointSource blocks: `{manifest['n_pointsource_blocks']}`",
                f"- triggers requested: `{manifest['triggers_requested']}`",
                f"- fixed activity: `{manifest['fixed_total_activity_Bq']:.12g} Bq`",
                "",
                "This summary is promoted from the fullstat_v2 prompt/buildup authority and remains transport-pending until Cosima writes the exact-position delayed sim.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def summarize_transport() -> dict[str, Any]:
    sim = SOURCE_PREFIX.with_suffix(".inc1.id1.sim.gz")
    if not sim.exists():
        alt = SOURCE_PREFIX.with_suffix(".inc1.id1.sim")
        sim = alt if alt.exists() else sim
    if not sim.exists():
        raise SystemExit(f"missing exact-position delayed transport output: {sim}")
    se = 0
    ident = 0
    ts = 0
    te = None
    with open_text(sim) as handle:
        for raw in handle:
            if raw.startswith("SE"):
                se += 1
            elif raw.startswith("ID"):
                ident += 1
            elif raw.startswith("TS"):
                ts += 1
            elif raw.startswith("TE"):
                parts = raw.split()
                if len(parts) >= 2:
                    te = float(parts[1])
    manifest = load_json(MANIFEST)
    summary = load_json(STEP02_SUMMARY)
    summary["status"] = "PASS_FULLSTAT_V2_EXACTPOS_TRANSPORT_CLOSURE"
    summary["known_limitations"] = exactpos_known_limitations(manifest)
    summary["delayed_transport"] = {
        "path": rel(sim),
        "SE": se,
        "ID": ident,
        "TS": ts,
        "TE_s": te,
        "geometry": manifest["geometry"],
        "size_bytes": sim.stat().st_size,
        "TE_source": "Cosima SIM TE live-time record; radioactive daughter decays can make TE differ from triggers/fixed_total_activity_Bq",
        "primary_activity_time_s_if_no_daughters": float(manifest["triggers_requested"]) / float(manifest["fixed_total_activity_Bq"]),
        "status": "PASS",
    }
    write_json(STEP02_SUMMARY, summary)
    STEP02_MD.write_text(
        "\n".join(
            [
                "# Step02 v3p5 Center-Finger Fullstat v2 Exact-Position Delayed Source",
                "",
                f"Status: `{summary['status']}`.",
                "",
                f"- source: `{manifest['source']}`",
                f"- delayed sim: `{rel(sim)}`",
                f"- SE/ID/TS: `{se}/{ident}/{ts}`",
                f"- TE: `{te:.9g} s`" if te is not None else "- TE: ``",
                "- TE source: Cosima SIM `TE` live-time record; daughter decays can make it differ from `triggers/fixed_total_activity_Bq`.",
                f"- source mode: `{manifest['source_mode']}`",
                f"- PointSource blocks: `{manifest['n_pointsource_blocks']}`",
                f"- fixed activity: `{manifest['fixed_total_activity_Bq']:.12g} Bq`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return summary["delayed_transport"]


def exactpos_known_limitations(manifest: dict[str, Any]) -> list[str]:
    if manifest.get("source_mode") == "sampled_equal_flux_pointsource_blocks":
        return [
            "exact-position delayed source uses sampled PointSource support; support size and seed are recorded in exactpos_delayed_source_manifest.json",
            "full weighted-table one-block-per-RPIP source remains a robustness target if Cosima source parsing can be made practical",
        ]
    return [
        "exact-position delayed source uses one PointSource per eligible weighted RPIP row from the fixed inventory",
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", dest="global_label", default=DEFAULT_EXACT_LABEL, help="Exact-position output label; must start with fullstat_v2_exactpos")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--label", default=None, help="Exact-position output label; overrides the global --label")
    b.add_argument("--n-decays", type=int, default=1_000_000)
    b.add_argument("--triggers", type=int, default=1_000_000)
    b.add_argument("--seed", type=int, default=260613)
    b.add_argument("--workers", type=int, default=max(1, (mp.cpu_count() or 4) - 2))
    b.add_argument("--force-table", action="store_true")
    b.add_argument("--source-mode", choices=["weighted-table", "sampled"], default="weighted-table")
    s = sub.add_parser("summarize-transport")
    s.add_argument("--label", default=None, help="Exact-position output label; overrides the global --label")
    args = ap.parse_args()
    configure_label(args.label or args.global_label)
    if args.cmd == "build":
        table = build_weighted_table(workers=args.workers, force=args.force_table)
        if args.source_mode == "weighted-table":
            manifest = write_weighted_table_source(triggers=args.triggers)
        else:
            manifest = write_sampled_source(n_decays=args.n_decays, triggers=args.triggers, seed=args.seed)
        print(json.dumps({"status": manifest["status"], "source": manifest["source"], "table_status": table["status"], "manifest": rel(MANIFEST)}, indent=2))
    elif args.cmd == "summarize-transport":
        transport = summarize_transport()
        print(json.dumps({"status": "PASS_EXACTPOS_TRANSPORT_SUMMARY", "delayed_transport": transport}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
