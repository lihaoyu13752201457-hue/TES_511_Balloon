#!/usr/bin/env python3
"""Build and summarize Bgo_sample full-stat exact-position delayed source.

The source uses Bgo_sample full-stat buildup RPIP positions and the day-15
ground-state-fixed activity budget. By default it emits a sampled equal-flux
PointSource support with M=5000, matching the current CsI exact-position
authority style while keeping the BGO result separate from CsI rates.
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
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BGO = ROOT / "Bgo_sample"
INSTANT = ROOT / "runs" / "step02_bgo_sample_fullstat_v2_instant"
BUILDUP = ROOT / "runs" / "step02_bgo_sample_fullstat_v2_buildup"
RAW_SOURCE_DIR = ROOT / "runs" / "step02_bgo_sample_fullstat_v2_decay_source"
FIX = ROOT / "runs" / "step02_bgo_sample_fullstat_v2_delay_fix"
FIXED_SOURCE = FIX / "activation_decay_day15_groundstate_fixed.source"
FIX_SUMMARY = FIX / "source_fix_summary.json"
FIX_AUDIT = FIX / "normalization_audit_groundstate_fix.json"
SOURCE_DIR = ROOT / "runs" / "step02_bgo_sample_fullstat_v2_exactpos_delay_source"
TRANSPORT_DIR = ROOT / "runs" / "step02_bgo_sample_fullstat_v2_exactpos_delayed_transport"
SOURCE_PREFIX = TRANSPORT_DIR / "DelayedDecayBgoSampleFullstatV2Exactpos"
SOURCE = SOURCE_DIR / "activation_decay_day15_groundstate_fixed_exactpos.source"
MANIFEST = SOURCE_DIR / "bgo_sample_fullstat_v2_exactpos_manifest.json"
WEIGHTED_TABLE = SOURCE_DIR / "exactpos_weighted_rpip_table.csv"
SUMMARY_JSON = BGO / "step02_fullstat_v2_exactpos_summary.json"
SUMMARY_MD = BGO / "STEP02_FULLSTAT_V2_EXACTPOS.md"
GEOMETRY = BGO / "Bgo_sample.geo.setup"

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


def sample_audit(points: list[dict[str, Any]], weights: list[float], drawn: Counter[tuple[str, int]], n_decays: int) -> dict[str, Any]:
    expected = expected_counts(points, weights, n_decays)
    rows = []
    max_abs_sigma = 0.0
    for (vn, za), exp in sorted(expected.items(), key=lambda item: item[1], reverse=True)[:20]:
        obs = int(drawn.get((vn, za), 0))
        sigma = math.sqrt(exp * max(1.0 - exp / float(n_decays), 0.0)) if exp > 0.0 else 0.0
        sigma_delta = (obs - exp) / sigma if sigma > 0.0 else 0.0
        max_abs_sigma = max(max_abs_sigma, abs(sigma_delta))
        rows.append({"VN": vn, "ZA": za, "expected_draws": exp, "observed_draws": obs, "sigma_delta": sigma_delta})
    status = "PASS" if max_abs_sigma <= 8.0 else "WARN"
    return {
        "status": status,
        "scope": "sampled_equal_flux_pointsource_blocks_species_level_audit",
        "n_decays": int(n_decays),
        "species_with_expected_draws": len(expected),
        "species_drawn": len(drawn),
        "top20_max_abs_sigma_delta": max_abs_sigma,
        "top20_expected_species": rows,
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
        raise SystemExit("no positive exact-position BGO full-stat source points emitted")

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    TRANSPORT_DIR.mkdir(parents=True, exist_ok=True)
    fixed = load_json(FIX_SUMMARY)
    total_activity = float(fixed["new_total_activity_Bq"])
    flux_per_source = total_activity / float(n_decays)
    chosen = weighted_indices(weights, n_decays, seed)

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
    header.append("# ===== Bgo_sample fullstat_v2 sampled exact-RPIP PointSource blocks =====")

    drawn: Counter[tuple[str, int]] = Counter()
    with SOURCE.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(header) + "\n")
        for idx, point_idx in enumerate(chosen):
            point = eligible[point_idx]
            drawn[(point["VN"], int(point["ZA"]))] += 1
            name = f"RP_{idx:07d}"
            handle.write(f"{name}.ParticleType {point['ZA']}\n")
            handle.write(f"{name}.Beam PointSource {point['x_cm']:.6f} {point['y_cm']:.6f} {point['z_cm']:.6f}\n")
            handle.write(f"{name}.Flux {flux_per_source:.8e}\n\n")

    instant = summarize_run(INSTANT)
    buildup = summarize_run(BUILDUP)
    manifest = {
        "status": "PASS_BGO_SAMPLE_FULLSTAT_V2_EXACTPOS_SOURCE_READY",
        "claim_level": "BGO_SAMPLE_FULLSTAT_V2_EXACTPOS_SOURCE_READY_NOT_RATE_AUTHORITY",
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
        "sum_flux_check_Bq": flux_per_source * float(n_decays),
        "sum_flux_abs_delta_Bq": abs(flux_per_source * float(n_decays) - total_activity),
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
        "division_by_tag": divs,
        "top_drawn_species": [
            {"VN": vn, "ZA": za, "drawn": count}
            for (vn, za), count in drawn.most_common(20)
        ],
        "sampling_audit": sample_audit(eligible, weights, drawn, n_decays),
        "boundary": [
            "Bgo_sample fullstat_v2 exact-position source uses full-stat prompt/buildup production and day-15 ground-state-fixed activity.",
            "This source card is not a BGO rate authority by itself; final BGO sensitivity is quoted only from the downstream Step08/comparison reports after delayed transport, Step05 response, and Step06--Step08 propagation.",
            "The sampled support uses M=5000 equal-flux PointSource blocks by default, matching the current CsI exact-position authority style.",
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
    problems = []
    if not transport["exists"]:
        problems.append("missing_delayed_transport_sim")
    if transport["SE"] != transport["ID"]:
        problems.append("SE_ID_mismatch")
    if transport["SE"] <= 0:
        problems.append("no_delayed_events")
    if "Bgo_sample/Bgo_sample.geo.setup" not in transport["geometry"]:
        problems.append("transport_geometry_not_Bgo_sample")
    manifest["delayed_transport"] = transport
    manifest["problems"] = problems
    manifest["status"] = "PASS_BGO_SAMPLE_FULLSTAT_V2_EXACTPOS_DELAYED_TRANSPORT" if not problems else "FAIL_BGO_SAMPLE_FULLSTAT_V2_EXACTPOS_DELAYED_TRANSPORT"
    if not problems:
        manifest["claim_level"] = "BGO_SAMPLE_FULLSTAT_V2_EXACTPOS_DELAYED_TRANSPORT_NOT_RATE_AUTHORITY"
        manifest["boundary"] = [
            "Bgo_sample fullstat_v2 exact-position delayed source/transport uses full-stat prompt/buildup production.",
            "Delayed transport passed as the Step02/03 authority for this branch.",
            "Supersession note: downstream Step05 detector response, Step06--Step08 mission-time significance, and the BGO-vs-CsI exact-position material-control comparison have since passed for this same bgo_sample_fullstat_v2_exactpos label. Quote BGO sensitivity from the Step08/comparison reports, not from this transport-only note.",
        ]
    transport["status"] = "PASS" if not problems else "FAIL"
    write_json(MANIFEST, manifest)
    write_summary(manifest, transport)
    print(json.dumps({"status": manifest["status"], "problems": problems, "transport": transport}, indent=2))
    return manifest


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
        "top_drawn_species": manifest["top_drawn_species"],
        "sampling_audit": manifest["sampling_audit"],
        "delayed_transport": transport,
        "problems": manifest.get("problems", []),
        "boundary": manifest["boundary"],
    }
    write_json(SUMMARY_JSON, summary)

    lines = [
        "# Bgo_sample Step02 Fullstat v2 Exact-Position Delayed Source",
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
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-source")
    build.add_argument("--n-decays", type=int, default=5000)
    build.add_argument("--triggers", type=int, default=1_000_000)
    build.add_argument("--seed", type=int, default=260613)
    sub.add_parser("summarize-transport")
    args = parser.parse_args()
    if args.cmd == "build-source":
        build_source(args.n_decays, args.triggers, args.seed)
    elif args.cmd == "summarize-transport":
        manifest = summarize_transport()
        return 0 if manifest["status"].startswith("PASS") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
