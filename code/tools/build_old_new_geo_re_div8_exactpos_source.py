#!/usr/bin/env python3
"""Build a scratch exact-position delayed source for old new_geo_re after div8.

This is intentionally a scratch rebuild tool. It reads the old new_geo_re
buildup RP/IP production positions and the already corrected div8 +
ground-state fixed source snapshot stored in this workspace, then writes a new
sampled PointSource delayed source under a fresh runs/ directory.
"""

from __future__ import annotations

import argparse
import bisect
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
OLD_ROOT = Path("/home/ubuntu/codex_tes_511_sim/new_geo_re")

BUILDUP = OLD_ROOT / "runs" / "step02_buildup_equiv2602_aligned"
FIXED_DIR = ROOT / "old" / "runs" / "step02_delay_fix_mainline_div8_review_20260612"
FIXED_SOURCE = FIXED_DIR / "activation_decay_day15_groundstate_fixed.source"
NORMALIZATION_AUDIT = FIXED_DIR / "normalization_audit_groundstate_fix.json"
SOURCE_FIX_SUMMARY = FIXED_DIR / "source_fix_summary.json"

DEFAULT_LABEL = "old_new_geo_re_div8_exactpos_m50000_s260623"
DEFAULT_N_DECAYS = 50_000
DEFAULT_TRIGGERS = 1_000_000
DEFAULT_SEED = 260623

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
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    audit = load_json(NORMALIZATION_AUDIT)
    if audit.get("status") != "PASS":
        raise SystemExit(f"normalization audit is not PASS: {NORMALIZATION_AUDIT}")
    rows = audit.get("rows")
    if isinstance(rows, list):
        return {str(row["tag"]): float(row["division"]) for row in rows}
    norm = audit.get("normalization", {})
    return {str(tag): float(row["division"]) for tag, row in norm.items()}


def parse_fixed_source() -> dict[str, Any]:
    lines = FIXED_SOURCE.read_text(encoding="utf-8", errors="ignore").splitlines()
    name_za: dict[str, int] = {}
    name_flux: dict[str, float] = {}
    activity_by_key: dict[tuple[str, int], float] = defaultdict(float)
    source_blocks = 0
    geometry: Path | None = None
    triggers = DEFAULT_TRIGGERS

    for raw in lines:
        line = raw.strip()
        gm = GEOMETRY_RE.match(line)
        if gm:
            gp = Path(gm.group("path"))
            geometry = gp if gp.is_absolute() else (ROOT / gp).resolve()
        tm = TRIGGERS_RE.match(line)
        if tm:
            triggers = int(tm.group("triggers"))
        pm = PARTICLE_RE.match(line)
        if pm:
            name_za[pm.group("name")] = int(pm.group("za"))
            source_blocks += 1
        fm = FLUX_RE.match(line)
        if fm:
            name_flux[fm.group("name")] = float(fm.group("flux"))

    for name, za in name_za.items():
        sm = SOURCE_NAME_RE.match(name)
        flux = float(name_flux.get(name, 0.0))
        if sm and flux > 0.0:
            activity_by_key[(sm.group("vn"), za)] += flux

    if geometry is None:
        summary = load_json(SOURCE_FIX_SUMMARY)
        geometry = Path(summary["geometry"])
    return {
        "geometry": geometry,
        "triggers": triggers,
        "source_blocks": source_blocks,
        "activity_by_key": dict(activity_by_key),
        "total_activity_Bq": math.fsum(activity_by_key.values()),
    }


def parse_one_sim(args_tuple: tuple[str, dict[str, float]]) -> dict[str, Any]:
    fp = Path(args_tuple[0])
    divs = args_tuple[1]
    tag = parse_tag(fp)
    division = float(divs.get(tag, 1.0))
    wfile = 1.0 / division if division > 0.0 else 1.0
    rows: list[tuple[str, int, float, float, float, float, float, str]] = []
    n_cc_ip_rp = 0
    n_unparsed = 0
    with open_text(fp) as handle:
        for raw in handle:
            if not raw.startswith("CC IP RP"):
                continue
            n_cc_ip_rp += 1
            m = IP_RE.match(raw.strip())
            if not m:
                n_unparsed += 1
                continue
            exc = float(m.group("exc"))
            if abs(exc) < 1.0e-9:
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
    return {
        "file": fp.name,
        "tag": tag,
        "wfile": wfile,
        "n_cc_ip_rp": n_cc_ip_rp,
        "n_unparsed": n_unparsed,
        "rows": rows,
    }


def percentile(sorted_vals: list[float], q: float) -> float | None:
    if not sorted_vals:
        return None
    if q <= 0:
        return sorted_vals[0]
    if q >= 1:
        return sorted_vals[-1]
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] * (hi - pos) + sorted_vals[hi] * (pos - lo)


def stats_from(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "p01": None, "p10": None, "median": None, "p90": None, "p99": None, "max": None, "mean": None}
    sv = sorted(values)
    return {
        "min": sv[0],
        "p01": percentile(sv, 0.01),
        "p10": percentile(sv, 0.10),
        "median": percentile(sv, 0.50),
        "p90": percentile(sv, 0.90),
        "p99": percentile(sv, 0.99),
        "max": sv[-1],
        "mean": math.fsum(values) / len(values),
    }


def paths_for(label: str) -> dict[str, Path]:
    source_dir = ROOT / "runs" / f"step02_delay_fix_{label}"
    transport_dir = ROOT / "runs" / f"step02_delayed_transport_{label}"
    return {
        "source_dir": source_dir,
        "transport_dir": transport_dir,
        "table": source_dir / "exactpos_weighted_rpip_table.csv",
        "table_summary": source_dir / "exactpos_weighted_rpip_summary.json",
        "source": source_dir / "activation_decay_day15_groundstate_fixed_exactpos.source",
        "manifest": source_dir / "exactpos_delayed_source_manifest.json",
        "prefix": transport_dir / f"DelayedDecayOldNewGeoReDiv8Exactpos_{label}",
    }


def build_weighted_table(label: str, workers: int, force: bool) -> dict[str, Any]:
    out = paths_for(label)
    if out["table"].exists() and out["table_summary"].exists() and not force:
        return load_json(out["table_summary"])
    out["source_dir"].mkdir(parents=True, exist_ok=True)
    out["transport_dir"].mkdir(parents=True, exist_ok=True)

    divs = division_by_tag()
    fixed = parse_fixed_source()
    activity_by_key: dict[tuple[str, int], float] = fixed["activity_by_key"]
    files = sorted(BUILDUP.glob("*.sim.gz"))
    if not files:
        raise SystemExit(f"no buildup SIM files in {BUILDUP}")

    t0 = time.time()
    args = [(str(path), divs) for path in files]
    ctx = mp.get_context("fork") if sys.platform.startswith("linux") else mp.get_context("spawn")
    results: list[dict[str, Any]] = []
    with ctx.Pool(processes=max(1, workers)) as pool:
        for idx, result in enumerate(pool.imap_unordered(parse_one_sim, args), 1):
            results.append(result)
            print(
                f"[{idx:02d}/{len(files):02d}] {result['file']}: "
                f"{len(result['rows'])} RP rows wfile={float(result['wfile']):.6g}",
                flush=True,
            )

    total_cc_ip_rp = 0
    total_rows = 0
    eligible_rows = 0
    unparsed = 0
    tag_rows: Counter[str] = Counter()
    source_weight_by_key: dict[tuple[str, int], float] = defaultdict(float)
    missing_fixed_keys = set(activity_by_key)

    for result in results:
        total_cc_ip_rp += int(result["n_cc_ip_rp"])
        unparsed += int(result.get("n_unparsed", 0))
        tag_rows[result["tag"]] += len(result["rows"])
        for vn, za, _exc, wfile, _x, _y, _z, _src in result["rows"]:
            total_rows += 1
            key = (vn, za)
            if key in activity_by_key:
                eligible_rows += 1
                source_weight_by_key[key] += float(wfile)
                missing_fixed_keys.discard(key)

    missing_flux = math.fsum(float(activity_by_key[key]) for key in missing_fixed_keys)
    if missing_flux > max(1.0e-12, 1.0e-10 * float(fixed["total_activity_Bq"])):
        preview = [
            {"VN": vn, "ZA": za, "activity_Bq": activity_by_key[(vn, za)]}
            for vn, za in sorted(missing_fixed_keys, key=lambda key: activity_by_key[key], reverse=True)[:20]
        ]
        raise SystemExit(f"{len(missing_fixed_keys)} fixed activity keys have no exact RPIP rows; missing_flux={missing_flux:.12g}; preview={preview}")

    r_values: list[float] = []
    z_values: list[float] = []
    weighted_r_sum = 0.0
    weighted_z_sum = 0.0
    flux_sum = 0.0
    flux_r_lt_1 = 0.0
    rows_r_lt_1 = 0
    top_flux: dict[tuple[str, int], float] = defaultdict(float)

    with out["table"].open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["VN", "ZA", "exc_keV", "wfile", "source_file", "x_cm", "y_cm", "z_cm", "r_cm", "sample_weight"])
        for result in results:
            for vn, za, exc, wfile, x, y, z, src in result["rows"]:
                key = (vn, za)
                activity = float(activity_by_key.get(key, 0.0))
                if activity <= 0.0:
                    continue
                denom = float(source_weight_by_key[key])
                sample_weight = activity * float(wfile) / denom if denom > 0.0 else 0.0
                if sample_weight <= 0.0:
                    continue
                r = math.hypot(float(x), float(y))
                r_values.append(r)
                z_values.append(float(z))
                flux_sum += sample_weight
                weighted_r_sum += sample_weight * r
                weighted_z_sum += sample_weight * float(z)
                top_flux[key] += sample_weight
                if r < 1.0:
                    rows_r_lt_1 += 1
                    flux_r_lt_1 += sample_weight
                writer.writerow(
                    [
                        vn,
                        za,
                        f"{float(exc):.6g}",
                        f"{float(wfile):.8g}",
                        src,
                        f"{float(x):.6f}",
                        f"{float(y):.6f}",
                        f"{float(z):.6f}",
                        f"{r:.6f}",
                        f"{sample_weight:.12e}",
                    ]
                )

    summary = {
        "status": "PASS_OLD_NEW_GEO_RE_DIV8_EXACTPOS_WEIGHTED_RPIP_TABLE",
        "label": label,
        "method": "sample_weight = corrected_fixed_activity_Bq(VN,ZA) * wfile / sum_wfile(VN,ZA)",
        "old_root": str(OLD_ROOT),
        "buildup_dir": str(BUILDUP),
        "files_parsed": len(files),
        "normalization_audit": rel(NORMALIZATION_AUDIT),
        "fixed_source": rel(FIXED_SOURCE),
        "fixed_source_blocks": int(fixed["source_blocks"]),
        "fixed_activity_keys": len(activity_by_key),
        "fixed_total_activity_Bq": float(fixed["total_activity_Bq"]),
        "table_sum_activity_Bq": float(flux_sum),
        "table_sum_activity_relative_delta": abs(flux_sum - float(fixed["total_activity_Bq"])) / float(fixed["total_activity_Bq"]),
        "total_cc_ip_rp_lines_seen": int(total_cc_ip_rp),
        "parsed_rpip_rows_seen": int(total_rows),
        "unparsed_cc_ip_rp_lines": int(unparsed),
        "eligible_rows_written": int(eligible_rows),
        "missing_fixed_keys": len(missing_fixed_keys),
        "missing_fixed_flux_Bq": float(missing_flux),
        "rp_rows_by_tag": dict(sorted(tag_rows.items())),
        "division_by_tag": divs,
        "table": rel(out["table"]),
        "radius_stats_cm_unweighted_rows": stats_from(r_values),
        "z_stats_cm_unweighted_rows": stats_from(z_values),
        "activity_weighted_mean_r_cm": weighted_r_sum / flux_sum if flux_sum > 0.0 else None,
        "activity_weighted_mean_z_cm": weighted_z_sum / flux_sum if flux_sum > 0.0 else None,
        "fraction_rows_r_lt_1cm": rows_r_lt_1 / eligible_rows if eligible_rows else None,
        "fraction_activity_r_lt_1cm": flux_r_lt_1 / flux_sum if flux_sum > 0.0 else None,
        "top_activity_species": [
            {"VN": vn, "ZA": za, "activity_Bq": flux}
            for (vn, za), flux in sorted(top_flux.items(), key=lambda item: item[1], reverse=True)[:25]
        ],
        "elapsed_s": round(time.time() - t0, 1),
    }
    write_json(out["table_summary"], summary)
    return summary


def load_sampling_rows(label: str) -> tuple[list[dict[str, Any]], list[float]]:
    table = paths_for(label)["table"]
    rows: list[dict[str, Any]] = []
    weights: list[float] = []
    with table.open("r", encoding="utf-8", newline="") as handle:
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
                    "r_cm": float(row["r_cm"]),
                }
            )
            weights.append(weight)
    if not rows:
        raise SystemExit(f"no positive rows in {table}")
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
    return [bisect.bisect_left(cdf, rng.random() * total) for _ in range(n)]


def expected_draws_by_species(rows: list[dict[str, Any]], weights: list[float], n_decays: int) -> dict[tuple[str, int], float]:
    total = math.fsum(weights)
    expected: dict[tuple[str, int], float] = defaultdict(float)
    scale = float(n_decays) / total
    for row, weight in zip(rows, weights):
        expected[(row["VN"], int(row["ZA"]))] += weight * scale
    return dict(expected)


def sampled_source_audit(
    expected_by_species: dict[tuple[str, int], float],
    observed_by_species: Counter[tuple[str, int]],
    n_decays: int,
    total_activity_Bq: float,
    sum_flux_check_Bq: float,
) -> dict[str, Any]:
    top_rows: list[dict[str, Any]] = []
    max_abs_sigma = 0.0
    chi2_top = 0.0
    for (vn, za), expected in sorted(expected_by_species.items(), key=lambda item: item[1], reverse=True)[:25]:
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
        problems.append(f"top species draw deviation max_abs_sigma={max_abs_sigma:.3g}")
    return {
        "status": status,
        "n_decays": int(n_decays),
        "species_with_expected_draws": len(expected_by_species),
        "species_drawn": len(observed_by_species),
        "sum_flux_abs_delta_Bq": flux_abs_delta,
        "sum_flux_relative_delta": flux_abs_delta / total_activity_Bq if total_activity_Bq > 0.0 else math.inf,
        "top25_expected_species_chi2": chi2_top,
        "top25_max_abs_sigma_delta": max_abs_sigma,
        "top25_expected_species": top_rows,
        "problems": problems,
    }


def copy_audit_inputs(source_dir: Path) -> None:
    for src in (
        FIXED_DIR / "groundstate_activity_corrections.csv",
        FIXED_DIR / "removed_or_rescaled_sources.csv",
        FIXED_DIR / "normalization_audit_groundstate_fix.csv",
        FIXED_DIR / "normalization_audit_groundstate_fix.json",
        FIXED_DIR / "source_fix_summary.json",
    ):
        if src.exists():
            shutil.copy2(src, source_dir / src.name)


def build_source(label: str, n_decays: int, triggers: int, seed: int, workers: int, force_table: bool) -> dict[str, Any]:
    out = paths_for(label)
    table_summary = build_weighted_table(label=label, workers=workers, force=force_table)
    fixed = parse_fixed_source()
    rows, weights = load_sampling_rows(label)
    indices = weighted_sample_indices(weights, n_decays, seed)
    total_activity = float(fixed["total_activity_Bq"])
    flux_per_source = total_activity / float(n_decays)
    expected_by_species = expected_draws_by_species(rows, weights, n_decays)

    out["source_dir"].mkdir(parents=True, exist_ok=True)
    out["transport_dir"].mkdir(parents=True, exist_ok=True)
    species_counts: Counter[tuple[str, int]] = Counter()
    r_drawn: list[float] = []
    z_drawn: list[float] = []

    source_lines = [
        "Version 1",
        f"Geometry {fixed['geometry']}",
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
        f"DecayRun.FileName {out['prefix']}",
        f"DecayRun.Triggers {int(triggers)}",
        "",
    ]
    source_lines.extend(f"DecayRun.Source RP_{i:07d}" for i in range(n_decays))
    source_lines.append("")
    source_lines.append("# exact-position sampled PointSource decay blocks")

    with out["source"].open("w", encoding="utf-8") as handle:
        handle.write("\n".join(source_lines) + "\n")
        for i, row_idx in enumerate(indices):
            row = rows[row_idx]
            za = int(row["ZA"])
            species_counts[(row["VN"], za)] += 1
            r_drawn.append(float(row["r_cm"]))
            z_drawn.append(float(row["z_cm"]))
            name = f"RP_{i:07d}"
            handle.write(f"{name}.ParticleType {za}\n")
            handle.write(f"{name}.Beam PointSource {row['x_cm']:.6f} {row['y_cm']:.6f} {row['z_cm']:.6f}\n")
            handle.write(f"{name}.Flux {flux_per_source:.8e}\n\n")

    manifest = {
        "status": "PASS_OLD_NEW_GEO_RE_DIV8_EXACTPOS_SOURCE_READY_TRANSPORT_PENDING",
        "label": label,
        "method": "old_new_geo_re_div8_groundstate_fixed_exact_RPIP_sampled_PointSource",
        "source": rel(out["source"]),
        "outfile_prefix": rel(out["prefix"]),
        "geometry": str(fixed["geometry"]),
        "old_root": str(OLD_ROOT),
        "buildup_dir": str(BUILDUP),
        "fixed_source": rel(FIXED_SOURCE),
        "normalization_audit": rel(NORMALIZATION_AUDIT),
        "table": rel(out["table"]),
        "table_summary": rel(out["table_summary"]),
        "fixed_total_activity_Bq": total_activity,
        "n_pointsource_blocks": int(n_decays),
        "triggers_requested": int(triggers),
        "seed": int(seed),
        "flux_per_pointsource_Bq": flux_per_source,
        "sum_flux_check_Bq": flux_per_source * n_decays,
        "sampling_rows": int(table_summary["eligible_rows_written"]),
        "drawn_radius_stats_cm": stats_from(r_drawn),
        "drawn_z_stats_cm": stats_from(z_drawn),
        "drawn_fraction_r_lt_1cm": sum(1 for r in r_drawn if r < 1.0) / len(r_drawn) if r_drawn else None,
        "top_drawn_species": [
            {"VN": vn, "ZA": za, "drawn": count}
            for (vn, za), count in species_counts.most_common(25)
        ],
        "sampling_audit": sampled_source_audit(
            expected_by_species=expected_by_species,
            observed_by_species=species_counts,
            n_decays=n_decays,
            total_activity_Bq=total_activity,
            sum_flux_check_Bq=flux_per_source * n_decays,
        ),
        "table_summary_payload": table_summary,
        "transport": {
            "status": "PENDING_COSIMA",
            "sim": rel(out["prefix"].with_suffix(".inc1.id1.sim.gz")),
        },
    }
    copy_audit_inputs(out["source_dir"])
    write_json(out["manifest"], manifest)
    print(json.dumps({"status": manifest["status"], "source": manifest["source"], "manifest": rel(out["manifest"])}, indent=2))
    return manifest


def summarize_transport(label: str) -> dict[str, Any]:
    out = paths_for(label)
    sim = out["prefix"].with_suffix(".inc1.id1.sim.gz")
    if not sim.exists():
        alt = out["prefix"].with_suffix(".inc1.id1.sim")
        sim = alt if alt.exists() else sim
    if not sim.exists():
        raise SystemExit(f"missing delayed transport output: {sim}")
    se = 0
    ident = 0
    ts = 0
    te = None
    geometry = None
    with open_text(sim) as handle:
        for raw in handle:
            if raw.startswith("Geometry "):
                geometry = raw.split(maxsplit=1)[1].strip()
            elif raw.startswith("SE"):
                se += 1
            elif raw.startswith("ID"):
                ident += 1
            elif raw.startswith("TS"):
                ts += 1
            elif raw.startswith("TE"):
                parts = raw.split()
                if len(parts) >= 2:
                    te = float(parts[1])
    manifest = load_json(out["manifest"])
    transport = {
        "status": "PASS",
        "sim": rel(sim),
        "size_bytes": sim.stat().st_size,
        "SE": se,
        "ID": ident,
        "TS": ts,
        "TE_s": te,
        "geometry_record": geometry,
        "primary_activity_time_s_if_no_daughters": float(manifest["triggers_requested"]) / float(manifest["fixed_total_activity_Bq"]),
    }
    manifest["status"] = "PASS_OLD_NEW_GEO_RE_DIV8_EXACTPOS_TRANSPORT_DONE"
    manifest["transport"] = transport
    write_json(out["manifest"], manifest)
    print(json.dumps({"status": "PASS_OLD_NEW_GEO_RE_DIV8_EXACTPOS_TRANSPORT_DONE", "transport": transport}, indent=2))
    return transport


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default=DEFAULT_LABEL)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--n-decays", type=int, default=DEFAULT_N_DECAYS)
    b.add_argument("--triggers", type=int, default=DEFAULT_TRIGGERS)
    b.add_argument("--seed", type=int, default=DEFAULT_SEED)
    b.add_argument("--workers", type=int, default=max(1, (mp.cpu_count() or 4) - 2))
    b.add_argument("--force-table", action="store_true")
    sub.add_parser("summarize-transport")
    args = ap.parse_args()

    if args.cmd == "build":
        build_source(
            label=args.label,
            n_decays=int(args.n_decays),
            triggers=int(args.triggers),
            seed=int(args.seed),
            workers=max(1, int(args.workers)),
            force_table=bool(args.force_table),
        )
    elif args.cmd == "summarize-transport":
        summarize_transport(label=args.label)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
