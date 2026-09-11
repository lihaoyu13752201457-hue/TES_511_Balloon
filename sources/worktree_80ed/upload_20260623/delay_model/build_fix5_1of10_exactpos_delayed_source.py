#!/usr/bin/env python3
"""Build and summarize fix5 exact-position delayed sources.

The default label remains the original fix5 1/10 screen.  The same audited path
is also used for the clean full-stat exact-position delayed source after the
full-stat fix5 buildup transport passes provenance.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LABEL = "fix5_1of10"
REPORT_DIR = ROOT / "outputs" / "reports" / LABEL
INSTANT = ROOT / "runs" / "step02_instant_fix5_1of10"
BUILDUP = ROOT / "runs" / "step02_buildup_fix5_1of10"
RAW_SOURCE_DIR = ROOT / "runs" / "step02_decay_source_fix5_1of10"
FIX = ROOT / "runs" / "step02_delay_fix_fix5_1of10"
FIXED_SOURCE = FIX / "activation_decay_day15_groundstate_fixed.source"
FIX_SUMMARY = FIX / "source_fix_summary.json"
FIX_AUDIT = FIX / "normalization_audit_groundstate_fix.json"
SOURCE_DIR = FIX
TRANSPORT_DIR = ROOT / "runs" / "step02_delayed_transport_fix5_1of10"
SOURCE_PREFIX = TRANSPORT_DIR / "DelayedDecayFix5Exactpos"
SOURCE = SOURCE_DIR / "activation_decay_day15_groundstate_fixed_exactpos.source"
MANIFEST = SOURCE_DIR / "fix5_1of10_exactpos_delayed_source_manifest.json"
WEIGHTED_TABLE = SOURCE_DIR / "exactpos_weighted_rpip_table.csv"
SUMMARY_JSON = REPORT_DIR / "fix5_delayed_source_exactpos_summary.json"
SUMMARY_MD = REPORT_DIR / "fix5_delayed_source_exactpos_summary.md"
GEOMETRY = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"

NUM = r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
IP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<vn>\S+)\s+"
    rf"(?P<x>{NUM})\s+(?P<y>{NUM})\s+(?P<z>{NUM})\s+"
    rf"(?P<za>\d+)\s+(?P<exc>{NUM})\s+(?P<t>{NUM})"
)
PARTICLE_RE = re.compile(r"^(?P<name>S_\S+)\.ParticleType\s+(?P<za>\d+)")
FLUX_RE = re.compile(r"^(?P<name>S_\S+)\.Flux\s+(?P<flux>[-+0-9.eE]+)")
SOURCE_NAME_RE = re.compile(r"^S_(?P<vn>.+)_(?P<za>\d+)_z\d+$")
TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)

RE_SEG_SHIELD = re.compile(r"^(Nb_Shield|W_Shield|Cryo_Shell|BGO_Shield|Al_Shell)(?:_p\d+_z\d+)?$", re.I)
RE_TP = re.compile(r"^TP_L(?P<l>\d+)_\d+$", re.I)
RE_TESPIX = re.compile(r"^TES_Pixel_L(?P<l>\d+)$", re.I)
RE_COLLBAR = re.compile(r"^(CollBar[XY])_\d+$", re.I)


def configure_paths(label: str) -> None:
    global LABEL, REPORT_DIR, INSTANT, BUILDUP, RAW_SOURCE_DIR, FIX, FIXED_SOURCE
    global FIX_SUMMARY, FIX_AUDIT, SOURCE_DIR, TRANSPORT_DIR, SOURCE_PREFIX
    global SOURCE, MANIFEST, WEIGHTED_TABLE, SUMMARY_JSON, SUMMARY_MD

    LABEL = label
    if label in ("fix5_1of10", "1of10"):
        LABEL = "fix5_1of10"
        REPORT_DIR = ROOT / "outputs" / "reports" / "fix5_1of10"
        INSTANT = ROOT / "runs" / "step02_instant_fix5_1of10"
        BUILDUP = ROOT / "runs" / "step02_buildup_fix5_1of10"
        RAW_SOURCE_DIR = ROOT / "runs" / "step02_decay_source_fix5_1of10"
        FIX = ROOT / "runs" / "step02_delay_fix_fix5_1of10"
        TRANSPORT_DIR = ROOT / "runs" / "step02_delayed_transport_fix5_1of10"
        SOURCE_PREFIX = TRANSPORT_DIR / "DelayedDecayFix5Exactpos"
        SOURCE = FIX / "activation_decay_day15_groundstate_fixed_exactpos.source"
        MANIFEST = FIX / "fix5_1of10_exactpos_delayed_source_manifest.json"
        WEIGHTED_TABLE = FIX / "exactpos_weighted_rpip_table.csv"
    elif label in ("fix5_fullstat_v2", "fix5_fullstat_v2_exactpos_m50000_s260613"):
        LABEL = "fix5_fullstat_v2_exactpos_m50000_s260613"
        REPORT_DIR = ROOT / "outputs" / "reports" / LABEL
        INSTANT = ROOT / "runs" / "step02_instant_fix5_fullstat_v2"
        BUILDUP = ROOT / "runs" / "step02_buildup_fix5_fullstat_v2"
        RAW_SOURCE_DIR = ROOT / "runs" / "step02_decay_source_fix5_fullstat_v2"
        FIX = ROOT / "runs" / "step02_delay_fix_fix5_fullstat_v2"
        TRANSPORT_DIR = ROOT / "runs" / "step02_delayed_transport_fix5_fullstat_v2_exactpos_m50000_s260613"
        SOURCE_PREFIX = TRANSPORT_DIR / "DelayedDecayFix5FullstatV2ExactposM50000S260613"
        SOURCE = FIX / "activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source"
        MANIFEST = FIX / "fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json"
        WEIGHTED_TABLE = FIX / "exactpos_weighted_rpip_table_m50000_s260613.csv"
    elif re.fullmatch(r"fix5_pi02_exactpos_m50000_s\d+", label):
        LABEL = label
        seed_token = label.rsplit("_", 1)[-1]
        seed_value = seed_token[1:]
        camel_seed = seed_token.upper()
        REPORT_DIR = ROOT / "outputs" / "reports" / LABEL
        INSTANT = ROOT / "runs" / "step02_instant_fix5_fullstat_v2"
        BUILDUP = ROOT / "runs" / "step02_buildup_fix5_fullstat_v2"
        RAW_SOURCE_DIR = ROOT / "runs" / "step02_decay_source_fix5_fullstat_v2"
        FIX = ROOT / "runs" / f"step02_delay_fix_{LABEL}"
        TRANSPORT_DIR = ROOT / "runs" / f"step02_delayed_transport_{LABEL}"
        SOURCE_PREFIX = TRANSPORT_DIR / f"DelayedDecayFix5Pi02ExactposM50000{camel_seed}"
        SOURCE = FIX / f"activation_decay_day15_groundstate_fixed_exactpos_m50000_s{seed_value}.source"
        MANIFEST = FIX / f"{LABEL}_delayed_source_manifest.json"
        WEIGHTED_TABLE = FIX / f"exactpos_weighted_rpip_table_m50000_s{seed_value}.csv"
    else:
        raise SystemExit(f"unsupported fix5 exactpos label: {label}")

    if re.fullmatch(r"fix5_pi02_exactpos_m50000_s\d+", label):
        base_fix = ROOT / "runs" / "step02_delay_fix_fix5_fullstat_v2"
        FIXED_SOURCE = base_fix / "activation_decay_day15_groundstate_fixed.source"
        FIX_SUMMARY = base_fix / "source_fix_summary.json"
        FIX_AUDIT = base_fix / "normalization_audit_groundstate_fix.json"
    else:
        FIXED_SOURCE = FIX / "activation_decay_day15_groundstate_fixed.source"
        FIX_SUMMARY = FIX / "source_fix_summary.json"
        FIX_AUDIT = FIX / "normalization_audit_groundstate_fix.json"
    SOURCE_DIR = FIX
    SUMMARY_JSON = REPORT_DIR / "fix5_delayed_source_exactpos_summary.json"
    SUMMARY_MD = REPORT_DIR / "fix5_delayed_source_exactpos_summary.md"


def claim_label() -> str:
    return LABEL.upper()


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


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def open_sim(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="ignore")


def parse_tag(path: Path | str) -> str:
    match = TAG_RE.search(Path(path).name)
    return match.group("tag").lower() if match else "unknown"


def canon_vn(vn: str) -> str:
    if not vn:
        return "Other"
    match = RE_SEG_SHIELD.match(vn)
    if match:
        return match.group(1)
    match = RE_TESPIX.match(vn)
    if match:
        return f"TES_L{int(match.group('l'))}"
    if vn.startswith("TES_L"):
        return vn
    match = RE_TP.match(vn)
    if match:
        return f"TES_L{int(match.group('l'))}"
    match = RE_COLLBAR.match(vn)
    if match:
        return match.group(1)
    if vn in ("Cu_Base", "Cu_SupportPole", "CU_BASE", "CU_SUPPORT", "Copper"):
        return "Copper"
    if vn in ("Collimator", "CollimatorVac", "CollimatorEnvelope"):
        return "CollimatorVac"
    if "window" in vn.lower() or vn.lower().startswith("win"):
        return "Window"
    return vn


def summarize_run(path: Path) -> dict[str, Any]:
    rows = load_json(path / "run_summary.json")
    norm = load_json(path / "normalization.json")
    by_particle: dict[str, dict[str, Any]] = {}
    for row in rows:
        tag = row["particle"]
        item = by_particle.setdefault(tag, {"jobs": 0, "passes": 0, "events": 0, "generated": 0, "cpu_s": 0.0})
        item["jobs"] += 1
        item["passes"] += 1 if row["status"] in ("PASS", "SKIP") else 0
        item["events"] += int(row["events"])
        item["generated"] += int(row["generated_particles"] or 0)
        item["cpu_s"] += float(row["cpu_s"] or 0.0)
    return {
        "run_dir": rel(path),
        "mode": norm["mode"],
        "jobs": len(rows),
        "passes": sum(1 for row in rows if row["status"] in ("PASS", "SKIP")),
        "failures": sum(1 for row in rows if row["status"] == "FAIL"),
        "events_requested": sum(int(row["events"]) for row in rows),
        "events_generated": sum(int(row["generated_particles"] or 0) for row in rows),
        "gamma_events": norm["gamma_events"],
        "gamma_splits": norm["gamma_splits"],
        "non_gamma_replicas": norm["non_gamma_replicas"],
        "farfield_radius_cm": norm["farfield_radius_cm"],
        "gamma_prompt_time_s_with_farfield_area": norm["gamma_prompt_time_s_with_farfield_area"],
        "by_particle": by_particle,
    }


def division_by_tag() -> dict[str, float]:
    audit = load_json(FIX_AUDIT)
    if audit.get("status") != "PASS":
        raise SystemExit(f"ground-state normalization audit is not PASS: {FIX_AUDIT}")
    return {row["tag"]: float(row["division"]) for row in audit["rows"]}


def fixed_activity_by_key() -> dict[tuple[str, int], float]:
    name_za: dict[str, int] = {}
    name_flux: dict[str, float] = {}
    for raw in FIXED_SOURCE.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = raw.strip()
        pm = PARTICLE_RE.match(stripped)
        if pm:
            name_za[pm.group("name")] = int(pm.group("za"))
            continue
        fm = FLUX_RE.match(stripped)
        if fm:
            name_flux[fm.group("name")] = float(fm.group("flux"))
    activity: dict[tuple[str, int], float] = defaultdict(float)
    for name, za in name_za.items():
        match = SOURCE_NAME_RE.match(name)
        if match:
            activity[(match.group("vn"), za)] += name_flux.get(name, 0.0)
    return dict(activity)


def parse_rpip_points(divs: dict[str, float]) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    for path in sorted(BUILDUP.glob("*.sim.gz")):
        tag = parse_tag(path)
        div = float(divs.get(tag, 1.0))
        wfile = 1.0 / div if div > 0.0 else 1.0
        with open_sim(path) as handle:
            for raw in handle:
                if not raw.startswith("CC IP RP"):
                    continue
                match = IP_RE.match(raw.strip())
                if not match:
                    continue
                exc = float(match.group("exc"))
                if abs(exc) < 1.0e-6:
                    exc = 0.0
                points.append(
                    {
                        "VN": canon_vn(match.group("vn")),
                        "ZA": int(match.group("za")),
                        "exc_keV": exc,
                        "x_cm": float(match.group("x")),
                        "y_cm": float(match.group("y")),
                        "z_cm": float(match.group("z")),
                        "wfile": wfile,
                        "source_sim": rel(path),
                    }
                )
    return points


def weighted_indices(weights: list[float], n: int, seed: int) -> list[int]:
    total = math.fsum(weights)
    if total <= 0.0:
        raise SystemExit("exact-position sampling weights sum to zero")
    cdf: list[float] = []
    acc = 0.0
    for weight in weights:
        acc += weight
        cdf.append(acc)
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


def expected_counts(points: list[dict[str, Any]], weights: list[float], n_decays: int) -> dict[tuple[str, int], float]:
    total = math.fsum(weights)
    expected: dict[tuple[str, int], float] = defaultdict(float)
    for point, weight in zip(points, weights):
        expected[(point["VN"], int(point["ZA"]))] += float(n_decays) * float(weight) / total
    return dict(expected)


def coord_key(point: dict[str, Any]) -> str:
    return f"{int(point['ZA'])}|{float(point['x_cm']):.6f}|{float(point['y_cm']):.6f}|{float(point['z_cm']):.6f}"


def sample_audit(
    points: list[dict[str, Any]],
    weights: list[float],
    drawn: Counter[tuple[str, int]],
    chosen_points: list[dict[str, Any]],
    n_decays: int,
    total_activity_Bq: float,
    sum_flux_check_Bq: float,
    source_text_sum_flux_Bq: float,
) -> dict[str, Any]:
    expected = expected_counts(points, weights, n_decays)
    rows = []
    max_abs_sigma = 0.0
    missed_expected_draws = 0.0
    for (vn, za), exp in sorted(expected.items(), key=lambda item: item[1], reverse=True)[:20]:
        obs = int(drawn.get((vn, za), 0))
        sigma = math.sqrt(exp * max(1.0 - exp / float(n_decays), 0.0)) if exp > 0.0 else 0.0
        sigma_delta = (obs - exp) / sigma if sigma > 0.0 else 0.0
        max_abs_sigma = max(max_abs_sigma, abs(sigma_delta))
        rows.append({"VN": vn, "ZA": za, "expected_draws": exp, "observed_draws": obs, "sigma_delta": sigma_delta})
    for key, exp in expected.items():
        if int(drawn.get(key, 0)) == 0:
            missed_expected_draws += float(exp)
    exact_key_counts = Counter(coord_key(point) for point in points)
    ambiguous = sum(1 for point in chosen_points if exact_key_counts[coord_key(point)] > 1)
    manifest_flux_abs_delta = abs(float(sum_flux_check_Bq) - float(total_activity_Bq))
    source_text_flux_abs_delta = abs(float(source_text_sum_flux_Bq) - float(total_activity_Bq))
    problems: list[str] = []
    if manifest_flux_abs_delta > 0.0:
        problems.append(f"manifest flux delta is {manifest_flux_abs_delta:.12g} Bq")
    if source_text_flux_abs_delta / max(float(total_activity_Bq), 1.0e-300) >= 1.0e-6:
        problems.append(f"source text flux relative delta is {source_text_flux_abs_delta / max(float(total_activity_Bq), 1.0e-300):.6g}")
    if ambiguous:
        problems.append(f"{ambiguous} sampled PointSource coordinate keys are ambiguous in the weighted table")
    status = "PASS" if not problems and max_abs_sigma <= 8.0 else "WARN"
    return {
        "status": status,
        "scope": f"{LABEL}_sampled_equal_flux_pointsource_blocks_inventory_audit",
        "n_decays": int(n_decays),
        "parsed_pointsource_blocks": int(n_decays),
        "species_with_expected_draws": len(expected),
        "species_drawn": len(drawn),
        "manifest_flux_abs_delta_Bq": manifest_flux_abs_delta,
        "manifest_flux_relative_delta": manifest_flux_abs_delta / max(float(total_activity_Bq), 1.0e-300),
        "source_text_flux_abs_delta_Bq": source_text_flux_abs_delta,
        "source_text_flux_relative_delta": source_text_flux_abs_delta / max(float(total_activity_Bq), 1.0e-300),
        "matched_back_to_exact_table_fraction": 1.0,
        "ambiguous_coordinate_key_fraction": ambiguous / float(n_decays) if n_decays else 0.0,
        "missed_nuclides_expected_draws_sum": missed_expected_draws,
        "missed_nuclides_total_activity_Bq": float(total_activity_Bq) * missed_expected_draws / float(n_decays),
        "missed_nuclides_total_activity_fraction": missed_expected_draws / float(n_decays),
        "top20_max_abs_sigma_delta": max_abs_sigma,
        "top20_expected_species": rows,
        "problems": problems,
        "interpretation": (
            "This source-level audit checks activity conservation, coordinate support, and species-level sampled support. "
            "It is not a substitute for transport-backed support-size/seed convergence of the final selected delayed rate."
        ),
    }


def activity_slices(activity: dict[tuple[str, int], float]) -> dict[str, Any]:
    by_volume: dict[str, float] = defaultdict(float)
    w_activity = 0.0
    w_or_collimator = 0.0
    for (vn, za), flux in activity.items():
        value = float(flux)
        by_volume[vn] += value
        is_w = int(za) // 1000 == 74
        is_collimator_like = "Coll" in vn or "Passive_W" in vn or "W_Shield" in vn
        if is_w:
            w_activity += value
        if is_w or is_collimator_like:
            w_or_collimator += value
    return {
        "w_element_activity_Bq": w_activity,
        "w_or_collimator_volume_activity_Bq": w_or_collimator,
        "top_activity_volumes": [
            {"VN": vn, "activity_Bq": value}
            for vn, value in sorted(by_volume.items(), key=lambda item: item[1], reverse=True)[:20]
        ],
        "w_or_collimator_volumes": [
            {"VN": vn, "activity_Bq": value}
            for vn, value in sorted(by_volume.items(), key=lambda item: item[1], reverse=True)
            if "Coll" in vn or "Passive_W" in vn or "W_Shield" in vn
        ],
    }


def build_source(n_decays: int, triggers: int, seed: int) -> dict[str, Any]:
    divs = division_by_tag()
    activity = fixed_activity_by_key()
    points = parse_rpip_points(divs)
    if not points:
        raise SystemExit(f"no RPIP points found in {BUILDUP}")

    weight_by_key: dict[tuple[str, int], float] = defaultdict(float)
    seen_by_key: Counter[tuple[str, int]] = Counter()
    for point in points:
        key = (point["VN"], int(point["ZA"]))
        seen_by_key[key] += 1
        if activity.get(key, 0.0) > 0.0:
            weight_by_key[key] += float(point["wfile"])

    missing = sorted(f"{vn}:{za}" for (vn, za), flux in activity.items() if flux > 0.0 and weight_by_key.get((vn, za), 0.0) <= 0.0)
    if missing:
        raise SystemExit(f"fixed activity keys without true RPIP support: {missing[:20]}")

    eligible: list[dict[str, Any]] = []
    weights: list[float] = []
    for point in points:
        key = (point["VN"], int(point["ZA"]))
        total_activity = float(activity.get(key, 0.0))
        denom = float(weight_by_key.get(key, 0.0))
        if total_activity <= 0.0 or denom <= 0.0:
            continue
        weight = total_activity * float(point["wfile"]) / denom
        if weight <= 0.0:
            continue
        eligible.append(point)
        weights.append(weight)
    if not eligible:
        raise SystemExit(f"no positive exact-position {LABEL} source points emitted")

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    TRANSPORT_DIR.mkdir(parents=True, exist_ok=True)
    fixed = load_json(FIX_SUMMARY)
    total_activity = float(fixed["new_total_activity_Bq"])
    flux_per_source = total_activity / float(n_decays)
    sum_flux_check = total_activity
    chosen = weighted_indices(weights, n_decays, seed)
    chosen_points = [eligible[idx] for idx in chosen]
    source_text_flux_per_source = float(f"{flux_per_source:.8e}")
    source_text_sum_flux = source_text_flux_per_source * float(n_decays)

    with WEIGHTED_TABLE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["VN", "ZA", "exc_keV", "wfile", "source_sim", "x_cm", "y_cm", "z_cm", "sample_weight"])
        for point, weight in zip(eligible, weights):
            writer.writerow(
                [
                    point["VN"],
                    point["ZA"],
                    f"{point['exc_keV']:.6g}",
                    f"{point['wfile']:.8g}",
                    point["source_sim"],
                    f"{point['x_cm']:.6f}",
                    f"{point['y_cm']:.6f}",
                    f"{point['z_cm']:.6f}",
                    f"{weight:.12e}",
                ]
            )

    header = [
        "Version 1",
        f"Geometry {rel(GEOMETRY)}",
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
    header.extend(f"DecayRun.Source RP_{idx:07d}" for idx in range(n_decays))
    header.append("")
    header.append(f"# ===== {LABEL} sampled exact-RPIP PointSource blocks =====")

    drawn: Counter[tuple[str, int]] = Counter()
    with SOURCE.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(header) + "\n")
        for idx, point in enumerate(chosen_points):
            drawn[(point["VN"], int(point["ZA"]))] += 1
            name = f"RP_{idx:07d}"
            handle.write(f"{name}.ParticleType {point['ZA']}\n")
            handle.write(f"{name}.Beam PointSource {point['x_cm']:.6f} {point['y_cm']:.6f} {point['z_cm']:.6f}\n")
            handle.write(f"{name}.Flux {flux_per_source:.8e}\n\n")

    instant = summarize_run(INSTANT)
    buildup = summarize_run(BUILDUP)
    sampling = sample_audit(
        eligible,
        weights,
        drawn,
        chosen_points,
        n_decays,
        total_activity,
        sum_flux_check,
        source_text_sum_flux,
    )
    manifest = {
        "status": f"PASS_{claim_label()}_EXACTPOS_SOURCE_READY",
        "claim_level": f"{claim_label()}_EXACTPOS_DELAYED_SOURCE_READY_NOT_RATE_AUTHORITY",
        "source_mode": "sampled_equal_flux_pointsource_blocks",
        "source": rel(SOURCE),
        "manifest": rel(MANIFEST),
        "weighted_table": rel(WEIGHTED_TABLE),
        "geometry": rel(GEOMETRY),
        "outfile_prefix": rel(SOURCE_PREFIX),
        "triggers_requested": int(triggers),
        "seed": int(seed),
        "n_pointsource_blocks": int(n_decays),
        "flux_per_pointsource_Bq": flux_per_source,
        "sum_flux_check_Bq": sum_flux_check,
        "source_text_sum_flux_Bq": source_text_sum_flux,
        "sum_flux_abs_delta_Bq": 0.0,
        "source_text_flux_abs_delta_Bq": abs(source_text_sum_flux - total_activity),
        "instant_transport": instant,
        "buildup_transport": buildup,
        "raw_source": rel(RAW_SOURCE_DIR / "activation_decay_day15.source"),
        "fixed_source": rel(FIXED_SOURCE),
        "fixed_total_activity_Bq": total_activity,
        "fixed_source_blocks": int(fixed["source_blocks_in"] - fixed["source_blocks_removed"]),
        "rpip_lines_seen": len(points),
        "rpip_keys_seen": len(seen_by_key),
        "eligible_rpip_rows": len(eligible),
        "activity_keys": len(activity),
        "activity_slices": activity_slices(activity),
        "division_by_tag": divs,
        "top_drawn_species": [
            {"VN": vn, "ZA": za, "drawn": count}
            for (vn, za), count in drawn.most_common(20)
        ],
        "sampling_audit": sampling,
        "boundary": [
            f"{LABEL} exact-position source uses matched fix5 prompt/buildup production and day-15 ground-state-fixed activity.",
            "This source card is not a delayed rate authority by itself; final delayed claims require delayed transport, Step05 response, Step06--Step08 propagation, and Verifier approval.",
            f"The sampled support uses M={int(n_decays)} equal-flux PointSource blocks and requires transport-backed selected-rate evidence before any delayed claim.",
        ],
    }
    write_json(MANIFEST, manifest)
    write_summary(manifest, transport=None)
    print(json.dumps({"status": manifest["status"], "source": rel(SOURCE), "n_pointsource_blocks": n_decays}, indent=2))
    return manifest


def sim_info(path: Path) -> dict[str, Any]:
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
    with open_sim(path) as handle:
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
    manifest = load_json(MANIFEST)
    transport = sim_info(SOURCE_PREFIX.with_suffix(".inc1.id1.sim.gz"))
    required_geometry = rel(GEOMETRY)
    problems = []
    if not transport["exists"]:
        problems.append("missing_delayed_transport_sim")
    if transport["SE"] != transport["ID"]:
        problems.append("SE_ID_mismatch")
    if transport["SE"] <= 0:
        problems.append("no_delayed_events")
    if not str(transport["geometry"]).endswith(required_geometry):
        problems.append("transport_geometry_not_fix5")
    manifest["delayed_transport"] = transport
    manifest["problems"] = problems
    manifest["status"] = (
        f"PASS_{claim_label()}_EXACTPOS_DELAYED_TRANSPORT"
        if not problems
        else f"FAIL_{claim_label()}_EXACTPOS_DELAYED_TRANSPORT"
    )
    if not problems:
        manifest["claim_level"] = f"{claim_label()}_EXACTPOS_DELAYED_TRANSPORT_NOT_RATE_AUTHORITY"
        manifest["boundary"] = [
            f"{LABEL} exact-position delayed source/transport uses matched fix5 buildup production.",
            "Delayed transport passed only as a transport artifact; delayed rate claims require Step05 detector response, Step06--Step08 propagation, W/collimator checks, and Verifier approval.",
        ]
    transport["status"] = "PASS" if not problems else "FAIL"
    write_json(MANIFEST, manifest)
    write_summary(manifest, transport)
    update_fullstat_delayed_transport_release(manifest, transport)
    print(json.dumps({"status": manifest["status"], "problems": problems, "transport": transport}, indent=2))
    return manifest


def update_fullstat_delayed_transport_release(manifest: dict[str, Any], transport: dict[str, Any]) -> None:
    if LABEL != "fix5_fullstat_v2_exactpos_m50000_s260613":
        return

    generated_at = now_utc()
    fullstat_report_dir = ROOT / "outputs" / "reports" / "fix5_fullstat_v2"
    release_path = REPORT_DIR / "fix5_fullstat_delayed_transport_release.json"
    verifier_path = fullstat_report_dir / "fix5_verification_verdict.json"
    groundstate_audit_path = REPORT_DIR / "fix5_groundstate_half_life_audit_summary.json"
    aborted_note_path = TRANSPORT_DIR / "aborted_stdout_pty_note.json"
    cosima_log = TRANSPORT_DIR / "cosima_fullstat_exactpos_m50000_s260613.log"

    groundstate_audit = load_json(groundstate_audit_path) if groundstate_audit_path.exists() else {}
    groundstate_checks = groundstate_audit.get("checks", {})
    sampling_audit = manifest.get("sampling_audit", {})
    geometry_ok = str(transport.get("geometry", "")).strip().endswith(rel(GEOMETRY))
    transport_pass = (
        transport.get("status") == "PASS"
        and transport.get("SE") == 1_000_000
        and transport.get("ID") == 1_000_000
        and transport.get("TS") == 1
        and isinstance(transport.get("TE_s"), (int, float))
        and float(transport["TE_s"]) > 0.0
        and geometry_ok
    )
    groundstate_pass = str(groundstate_audit.get("status", "")).startswith("PASS") and not groundstate_audit.get("problems")
    sampling_pass = sampling_audit.get("status") == "PASS" and not sampling_audit.get("problems")
    post_status = (
        "PASS_FULLSTAT_EXACTPOS_DELAYED_TRANSPORT_VERIFIED"
        if transport_pass and groundstate_pass and sampling_pass
        else "FAIL_FULLSTAT_EXACTPOS_DELAYED_TRANSPORT_VERIFIED"
    )

    release = load_json(release_path)
    release["updated_at_utc"] = generated_at
    release["post_transport_result"] = {
        "status": post_status,
        "delayed_source_summary": rel(SUMMARY_JSON),
        "delayed_source_manifest": rel(MANIFEST),
        "groundstate_audit": rel(groundstate_audit_path),
        "cosima_log": rel(cosima_log),
        "transport_sim": transport["path"],
        "transport_size_bytes": transport["size_bytes"],
        "SE": transport["SE"],
        "ID": transport["ID"],
        "TS": transport["TS"],
        "TE_s": transport["TE_s"],
        "geometry": str(transport.get("geometry", "")).strip(),
        "geometry_status": "PASS_FIX5_GEOMETRY" if geometry_ok else "FAIL_NOT_FIX5_GEOMETRY",
        "aborted_partial_retained_note": rel(aborted_note_path) if aborted_note_path.exists() else None,
        "rate_claim_allowed": False,
        "next_step": "Run Step05 detector/L1 response for fix5 full-stat prompt and exact-position delayed transport.",
    }
    release["commands_executed"] = [
        "bash -lc 'source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh >/tmp/fix5_megalib_env.log && cosima -s 260613 runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source > runs/step02_delayed_transport_fix5_fullstat_v2_exactpos_m50000_s260613/cosima_fullstat_exactpos_m50000_s260613.log 2>&1'"
    ]
    write_json(release_path, release)

    verifier = load_json(verifier_path)
    check_names = {
        "fullstat_delayed_groundstate_half_life_audit",
        "fullstat_exactpos_sampling_inventory_audit",
        "fullstat_exactpos_delayed_transport_sim_header",
        "fullstat_exactpos_aborted_partial_quarantined",
    }
    verifier["rows"] = [row for row in verifier.get("rows", []) if row.get("check") not in check_names]
    verifier["rows"].extend(
        [
            {
                "check": "fullstat_delayed_groundstate_half_life_audit",
                "status": "PASS" if groundstate_pass else "FAIL",
                "evidence_path": rel(groundstate_audit_path),
                "blocking": True,
                "details": {
                    "audit_status": groundstate_audit.get("status"),
                    "problems": groundstate_audit.get("problems", []),
                    "corrections_rows": groundstate_checks.get("corrections_rows"),
                    "nubase_line_mismatches": groundstate_checks.get("nubase_line_mismatches"),
                    "normalization_status": groundstate_checks.get("normalization_status"),
                    "normalization_problems": groundstate_checks.get("normalization_problems", []),
                    "fixed_source_geometry": groundstate_checks.get("fixed_source_geometry"),
                    "old_total_activity_Bq": groundstate_checks.get("old_total_activity_Bq"),
                    "new_total_activity_Bq": groundstate_checks.get("new_total_activity_Bq"),
                    "source_blocks_removed": groundstate_checks.get("source_blocks_removed"),
                    "w_or_collimator_new_activity_Bq": groundstate_checks.get("w_or_collimator_new_activity_Bq"),
                },
            },
            {
                "check": "fullstat_exactpos_sampling_inventory_audit",
                "status": "PASS" if sampling_pass else "FAIL",
                "evidence_path": rel(SUMMARY_JSON),
                "blocking": True,
                "details": {
                    "sampling_status": sampling_audit.get("status"),
                    "n_decays": sampling_audit.get("n_decays"),
                    "parsed_pointsource_blocks": sampling_audit.get("parsed_pointsource_blocks"),
                    "manifest_flux_relative_delta": sampling_audit.get("manifest_flux_relative_delta"),
                    "source_text_flux_relative_delta": sampling_audit.get("source_text_flux_relative_delta"),
                    "matched_back_to_exact_table_fraction": sampling_audit.get("matched_back_to_exact_table_fraction"),
                    "ambiguous_coordinate_key_fraction": sampling_audit.get("ambiguous_coordinate_key_fraction"),
                    "top20_max_abs_sigma_delta": sampling_audit.get("top20_max_abs_sigma_delta"),
                    "problems": sampling_audit.get("problems", []),
                },
            },
            {
                "check": "fullstat_exactpos_delayed_transport_sim_header",
                "status": "PASS" if transport_pass else "FAIL",
                "evidence_path": transport["path"],
                "blocking": True,
                "details": {
                    "SE": transport.get("SE"),
                    "ID": transport.get("ID"),
                    "TS": transport.get("TS"),
                    "TE_s": transport.get("TE_s"),
                    "size_bytes": transport.get("size_bytes"),
                    "geometry": str(transport.get("geometry", "")).strip(),
                    "geometry_ok": geometry_ok,
                },
            },
            {
                "check": "fullstat_exactpos_aborted_partial_quarantined",
                "status": "PASS" if aborted_note_path.exists() else "NOT_APPLICABLE",
                "evidence_path": rel(aborted_note_path) if aborted_note_path.exists() else "",
                "blocking": False,
                "details": {
                    "aborted_partial_note_exists": aborted_note_path.exists(),
                    "final_transport_sim": transport["path"],
                },
            },
        ]
    )
    verifier["updated_at_utc"] = generated_at
    verifier["overall_status"] = post_status
    verifier["phase_fullstat_exactpos_delayed_transport_status"] = manifest["status"]
    verifier["exactpos_delayed_source_summary"] = rel(SUMMARY_JSON)
    verifier["exactpos_delayed_transport_release"] = rel(release_path)
    verifier["step05_l1_response_release_allowed"] = post_status.startswith("PASS")
    verifier["final_rate_claim_allowed"] = False
    verifier["final_promotion_decision_allowed"] = False
    write_json(verifier_path, verifier)


def write_summary(manifest: dict[str, Any], transport: dict[str, Any] | None) -> None:
    summary = {
        "status": manifest["status"],
        "claim_level": manifest["claim_level"],
        "source_mode": manifest["source_mode"],
        "source": manifest["source"],
        "manifest": rel(MANIFEST),
        "weighted_table": manifest["weighted_table"],
        "geometry": manifest["geometry"],
        "instant_transport": manifest["instant_transport"],
        "buildup_transport": manifest["buildup_transport"],
        "raw_source": manifest["raw_source"],
        "fixed_source": manifest["fixed_source"],
        "fixed_total_activity_Bq": manifest["fixed_total_activity_Bq"],
        "fixed_source_blocks": manifest["fixed_source_blocks"],
        "rpip_lines_seen": manifest["rpip_lines_seen"],
        "rpip_keys_seen": manifest["rpip_keys_seen"],
        "eligible_rpip_rows": manifest["eligible_rpip_rows"],
        "n_pointsource_blocks": manifest["n_pointsource_blocks"],
        "seed": manifest["seed"],
        "flux_per_pointsource_Bq": manifest["flux_per_pointsource_Bq"],
        "sum_flux_check_Bq": manifest["sum_flux_check_Bq"],
        "sum_flux_abs_delta_Bq": manifest["sum_flux_abs_delta_Bq"],
        "source_text_sum_flux_Bq": manifest["source_text_sum_flux_Bq"],
        "source_text_flux_abs_delta_Bq": manifest["source_text_flux_abs_delta_Bq"],
        "activity_slices": manifest["activity_slices"],
        "top_drawn_species": manifest["top_drawn_species"],
        "sampling_audit": manifest["sampling_audit"],
        "delayed_transport": transport,
        "problems": manifest.get("problems", []),
        "boundary": manifest["boundary"],
    }
    write_json(SUMMARY_JSON, summary)

    lines = [
        f"# {LABEL} Exact-Position Delayed Source",
        "",
        f"Status: `{summary['status']}`.",
        "",
        f"- source: `{summary['source']}`",
        f"- manifest: `{summary['manifest']}`",
        f"- weighted table: `{summary['weighted_table']}`",
        f"- geometry: `{summary['geometry']}`",
        f"- instant generated: `{summary['instant_transport']['events_generated']}` / `{summary['instant_transport']['events_requested']}`",
        f"- buildup generated: `{summary['buildup_transport']['events_generated']}` / `{summary['buildup_transport']['events_requested']}`",
        f"- fixed day-15 activity: `{summary['fixed_total_activity_Bq']:.8g} Bq`",
        f"- fixed source blocks: `{summary['fixed_source_blocks']}`",
        f"- RPIP lines/keys: `{summary['rpip_lines_seen']}` / `{summary['rpip_keys_seen']}`",
        f"- eligible RPIP rows: `{summary['eligible_rpip_rows']}`",
        f"- PointSource blocks: `{summary['n_pointsource_blocks']}`",
        f"- seed: `{summary['seed']}`",
        f"- flux per PointSource: `{summary['flux_per_pointsource_Bq']:.8g} Bq`",
        f"- flux conservation abs delta: `{summary['sum_flux_abs_delta_Bq']:.6g} Bq`",
        f"- source text flux abs delta: `{summary['source_text_flux_abs_delta_Bq']:.6g} Bq`",
        f"- W element activity: `{summary['activity_slices']['w_element_activity_Bq']:.8g} Bq`",
        f"- W/collimator-volume activity: `{summary['activity_slices']['w_or_collimator_volume_activity_Bq']:.8g} Bq`",
        f"- sampling audit: `{summary['sampling_audit']['status']}`",
    ]
    if transport:
        lines.extend(
            [
                f"- delayed sim: `{transport['path']}`",
                f"- SE/ID/TS: `{transport['SE']}/{transport['ID']}/{transport['TS']}`",
                f"- TE: `{transport['TE_s']}` s",
            ]
        )
    lines.extend(["", "Boundary:"])
    lines.extend(f"- {item}" for item in summary["boundary"])
    lines.append("")
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="fix5_1of10")
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-source")
    build.add_argument("--n-decays", type=int, default=5000)
    build.add_argument("--triggers", type=int, default=100_000)
    build.add_argument("--seed", type=int, default=260613)
    sub.add_parser("summarize-transport")
    args = parser.parse_args()
    configure_paths(args.label)
    if args.cmd == "build-source":
        build_source(args.n_decays, args.triggers, args.seed)
    elif args.cmd == "summarize-transport":
        manifest = summarize_transport()
        return 0 if manifest["status"].startswith("PASS") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
