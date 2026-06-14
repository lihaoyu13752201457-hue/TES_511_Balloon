#!/usr/bin/env python3
"""Build and summarize Bgo_sample 1of10 exact-position delayed transport.

This is the first low-statistics BGO closure layer above smoke. It uses the
Bgo_sample 1of10 buildup RPIP positions and the day-15 ground-state-fixed
activity source, then assigns activity back to true RPIP PointSource blocks.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BGO = ROOT / "Bgo_sample"
INSTANT = ROOT / "runs" / "step02_bgo_sample_1of10_instant"
BUILDUP = ROOT / "runs" / "step02_bgo_sample_1of10_buildup"
FIX = ROOT / "runs" / "step02_bgo_sample_1of10_delay_fix"
FIXED_SOURCE = FIX / "activation_decay_day15_groundstate_fixed.source"
FIX_SUMMARY = FIX / "source_fix_summary.json"
FIX_AUDIT = FIX / "normalization_audit_groundstate_fix.json"
SOURCE_DIR = ROOT / "runs" / "step02_bgo_sample_1of10_exactpos_delay_source"
TRANSPORT_DIR = ROOT / "runs" / "step02_bgo_sample_1of10_exactpos_delayed_transport"
SOURCE_PREFIX = TRANSPORT_DIR / "DelayedDecayBgoSample1of10Exactpos"
SOURCE = SOURCE_DIR / "activation_decay_day15_groundstate_fixed_exactpos.source"
MANIFEST = SOURCE_DIR / "bgo_sample_1of10_exactpos_manifest.json"
SUMMARY_JSON = BGO / "step02_1of10_exactpos_summary.json"
SUMMARY_MD = BGO / "STEP02_1OF10_EXACTPOS.md"
GEOMETRY = ROOT / "Bgo_sample" / "Bgo_sample.geo.setup"

NUM = r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
IP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<vn>\S+)\s+"
    rf"(?P<x>{NUM})\s+(?P<y>{NUM})\s+(?P<z>{NUM})\s+"
    rf"(?P<za>\d+)\s+(?P<exc>{NUM})\s+(?P<t>{NUM})"
)
SOURCE_RE = re.compile(r"^DecayRun\.Source\s+(?P<name>\S+)")
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
        if not match:
            continue
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


def build_source(triggers: int) -> dict[str, Any]:
    divs = division_by_tag()
    activity = fixed_activity_by_key()
    points = parse_rpip_points(divs)
    if not points:
        raise SystemExit(f"no RPIP points found in {BUILDUP}")

    weight_by_key: dict[tuple[str, int], float] = defaultdict(float)
    total_seen_by_key: Counter[tuple[str, int]] = Counter()
    for point in points:
        key = (point["VN"], int(point["ZA"]))
        total_seen_by_key[key] += 1
        if activity.get(key, 0.0) > 0.0:
            weight_by_key[key] += float(point["wfile"])

    missing_activity_keys = sorted(f"{vn}:{za}" for (vn, za), flux in activity.items() if flux > 0.0 and weight_by_key.get((vn, za), 0.0) <= 0.0)
    if missing_activity_keys:
        raise SystemExit(f"fixed activity keys without true RPIP support: {missing_activity_keys[:20]}")

    emitted: list[dict[str, Any]] = []
    for point in points:
        key = (point["VN"], int(point["ZA"]))
        total_activity = float(activity.get(key, 0.0))
        denom = float(weight_by_key.get(key, 0.0))
        if total_activity <= 0.0 or denom <= 0.0:
            continue
        flux = total_activity * float(point["wfile"]) / denom
        emitted.append({**point, "flux_Bq": flux})
    if not emitted:
        raise SystemExit("no positive exact-position BGO source points emitted")

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    TRANSPORT_DIR.mkdir(parents=True, exist_ok=True)
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
    header.extend(f"DecayRun.Source RP_{idx:06d}" for idx, _ in enumerate(emitted))
    header.append("")
    header.append("# ===== Bgo_sample 1of10 exact-RPIP PointSource blocks =====")
    with SOURCE.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(header) + "\n")
        for idx, point in enumerate(emitted):
            name = f"RP_{idx:06d}"
            handle.write(f"{name}.ParticleType {point['ZA']}\n")
            handle.write(f"{name}.Beam PointSource {point['x_cm']:.6f} {point['y_cm']:.6f} {point['z_cm']:.6f}\n")
            handle.write(f"{name}.Flux {point['flux_Bq']:.8e}\n\n")

    flux_by_key: dict[tuple[str, int], float] = defaultdict(float)
    count_by_key: Counter[tuple[str, int]] = Counter()
    for point in emitted:
        key = (point["VN"], int(point["ZA"]))
        flux_by_key[key] += float(point["flux_Bq"])
        count_by_key[key] += 1

    fixed = load_json(FIX_SUMMARY)
    instant = summarize_run(INSTANT)
    buildup = summarize_run(BUILDUP)
    manifest = {
        "status": "PASS_BGO_SAMPLE_1OF10_EXACTPOS_SOURCE_READY",
        "claim_level": "BGO_SAMPLE_1OF10_EXACTPOS_DELAYED_SOURCE_READY_NOT_RATE_AUTHORITY",
        "source": rel(SOURCE),
        "geometry": rel(GEOMETRY),
        "outfile_prefix": rel(SOURCE_PREFIX),
        "triggers_requested": int(triggers),
        "instant_transport": instant,
        "buildup_transport": buildup,
        "fixed_source": rel(FIXED_SOURCE),
        "fixed_total_activity_Bq": float(fixed["new_total_activity_Bq"]),
        "fixed_source_blocks": int(fixed["source_blocks_in"] - fixed["source_blocks_removed"]),
        "rpip_lines_seen": len(points),
        "rpip_keys_seen": len(total_seen_by_key),
        "n_pointsource_blocks": len(emitted),
        "activity_keys": len(activity),
        "sum_flux_check_Bq": sum(float(p["flux_Bq"]) for p in emitted),
        "sum_flux_abs_delta_Bq": abs(sum(float(p["flux_Bq"]) for p in emitted) - float(fixed["new_total_activity_Bq"])),
        "top_activity_keys": [
            {"VN": vn, "ZA": za, "pointsource_blocks": count_by_key[(vn, za)], "activity_Bq": flux}
            for (vn, za), flux in sorted(flux_by_key.items(), key=lambda item: item[1], reverse=True)[:20]
        ],
        "division_by_tag": divs,
        "boundary": [
            "Bgo_sample 1of10 exact-position delayed source uses low-stat prompt/buildup production, not full-stat production.",
            "Activity is day-15 ground-state-fixed and conserved over true RPIP PointSource blocks.",
            "Downstream delayed transport, Step05 response, Step06--Step08 significance, and full-stat BGO-vs-CsI comparison remain separate gates.",
        ],
    }
    write_json(MANIFEST, manifest)
    write_summary(manifest, transport=None)
    print(json.dumps({"status": manifest["status"], "source": rel(SOURCE), "n_pointsource_blocks": len(emitted)}, indent=2))
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
    manifest["status"] = "PASS_BGO_SAMPLE_1OF10_EXACTPOS_DELAYED_TRANSPORT" if not problems else "FAIL_BGO_SAMPLE_1OF10_EXACTPOS_DELAYED_TRANSPORT"
    if not problems:
        manifest["claim_level"] = "BGO_SAMPLE_1OF10_EXACTPOS_DELAYED_TRANSPORT_NOT_RATE_AUTHORITY"
        manifest["boundary"] = [
            "Bgo_sample 1of10 exact-position delayed source/transport uses low-stat prompt/buildup production, not full-stat production.",
            "Activity is day-15 ground-state-fixed and conserved over true RPIP PointSource blocks.",
            "Delayed transport passed for this low-stat sample; Step05 response, Step06--Step08 significance, and full-stat BGO-vs-CsI comparison remain separate gates.",
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
        "source": manifest["source"],
        "manifest": rel(MANIFEST),
        "geometry": manifest["geometry"],
        "instant_transport": manifest["instant_transport"],
        "buildup_transport": manifest["buildup_transport"],
        "fixed_total_activity_Bq": manifest["fixed_total_activity_Bq"],
        "fixed_source_blocks": manifest["fixed_source_blocks"],
        "rpip_lines_seen": manifest["rpip_lines_seen"],
        "rpip_keys_seen": manifest["rpip_keys_seen"],
        "n_pointsource_blocks": manifest["n_pointsource_blocks"],
        "sum_flux_check_Bq": manifest["sum_flux_check_Bq"],
        "sum_flux_abs_delta_Bq": manifest["sum_flux_abs_delta_Bq"],
        "top_activity_keys": manifest["top_activity_keys"],
        "delayed_transport": transport,
        "problems": manifest.get("problems", []),
        "boundary": manifest["boundary"],
    }
    write_json(SUMMARY_JSON, summary)

    lines = [
        "# Bgo_sample Step02 1of10 Exact-Position Delayed Source",
        "",
        f"Status: `{summary['status']}`.",
        "",
        f"- source: `{summary['source']}`",
        f"- manifest: `{summary['manifest']}`",
        f"- geometry: `{summary['geometry']}`",
        f"- instant generated: `{summary['instant_transport']['events_generated']}` / `{summary['instant_transport']['events_requested']}`",
        f"- buildup generated: `{summary['buildup_transport']['events_generated']}` / `{summary['buildup_transport']['events_requested']}`",
        f"- fixed day-15 activity: `{summary['fixed_total_activity_Bq']:.8g} Bq`",
        f"- fixed source blocks: `{summary['fixed_source_blocks']}`",
        f"- RPIP lines/keys: `{summary['rpip_lines_seen']}` / `{summary['rpip_keys_seen']}`",
        f"- PointSource blocks: `{summary['n_pointsource_blocks']}`",
        f"- flux conservation abs delta: `{summary['sum_flux_abs_delta_Bq']:.6g} Bq`",
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
    build.add_argument("--triggers", type=int, default=100000)
    sub.add_parser("summarize-transport")
    args = parser.parse_args()
    if args.cmd == "build-source":
        build_source(args.triggers)
    elif args.cmd == "summarize-transport":
        manifest = summarize_transport()
        return 0 if manifest["status"].startswith("PASS") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
