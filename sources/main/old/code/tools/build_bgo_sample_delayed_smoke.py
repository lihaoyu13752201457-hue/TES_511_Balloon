#!/usr/bin/env python3
"""Build and summarize a Bgo_sample delayed-source smoke transport.

This is intentionally a smoke-level bridge from the BGO activation probe to a
Cosima delayed-decay source. It does not produce a rate authority.
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
BGO_DIR = ROOT / "Bgo_sample"
PROBE_DIR = ROOT / "runs" / "step02_bgo_sample_activation_probe_buildup_pn50k"
SOURCE_DIR = ROOT / "runs" / "step02_bgo_sample_delay_smoke"
TRANSPORT_DIR = ROOT / "runs" / "step02_bgo_sample_delayed_transport_smoke"
GEOMETRY = ROOT / "Bgo_sample" / "Bgo_sample.geo.setup"
SOURCE = SOURCE_DIR / "activation_decay_probe.source"
MANIFEST = SOURCE_DIR / "bgo_delayed_smoke_manifest.json"
SOURCE_PREFIX = TRANSPORT_DIR / "DelayedDecayBgoProbe"
SUMMARY_JSON = BGO_DIR / "delayed_smoke_summary.json"
SUMMARY_MD = BGO_DIR / "DELAYED_SMOKE.md"

NUM = r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
IP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<vn>\S+)\s+"
    rf"(?P<x>{NUM})\s+(?P<y>{NUM})\s+(?P<z>{NUM})\s+"
    rf"(?P<za>\d+)\s+(?P<exc>{NUM})\s+(?P<t>{NUM})"
)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def open_sim(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="ignore")


def parse_dat(path: Path) -> dict[str, Any]:
    tt = None
    vn = None
    counts: Counter[tuple[str, int, float]] = Counter()
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = raw.split()
        if not parts:
            continue
        if parts[0] == "TT" and len(parts) >= 2:
            tt = float(parts[1])
        elif parts[0] == "VN" and len(parts) >= 2:
            vn = parts[1]
        elif parts[0] == "RP" and vn and len(parts) >= 4:
            counts[(vn, int(parts[1]), float(parts[2]))] += float(parts[3])
    return {
        "path": rel(path),
        "TT_s": tt,
        "keys": len(counts),
        "total_rp_count": sum(counts.values()),
        "counts": counts,
    }


def parse_sim_points(path: Path) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    with open_sim(path) as handle:
        for raw in handle:
            match = IP_RE.match(raw.strip())
            if not match:
                continue
            points.append(
                {
                    "VN": match.group("vn"),
                    "ZA": int(match.group("za")),
                    "exc_keV": float(match.group("exc")),
                    "x_cm": float(match.group("x")),
                    "y_cm": float(match.group("y")),
                    "z_cm": float(match.group("z")),
                    "source_sim": rel(path),
                }
            )
    return points


def collect_probe() -> dict[str, Any]:
    dat_payloads = [parse_dat(path) for path in sorted(PROBE_DIR.glob("*.dat.inc1.dat"))]
    points: list[dict[str, Any]] = []
    for path in sorted(PROBE_DIR.glob("*.sim.gz")):
        points.extend(parse_sim_points(path))

    counts: Counter[tuple[str, int, float]] = Counter()
    tt_by_key: dict[tuple[str, int, float], float] = {}
    for payload in dat_payloads:
        tt = payload["TT_s"]
        for key, count in payload["counts"].items():
            counts[key] += count
            if tt:
                tt_by_key[key] = tt

    points_by_key: Counter[tuple[str, int, float]] = Counter(
        (p["VN"], int(p["ZA"]), float(p["exc_keV"])) for p in points
    )
    if counts != points_by_key:
        missing_in_points = dict(counts - points_by_key)
        missing_in_dat = dict(points_by_key - counts)
        raise SystemExit(f"DAT/SIM RPIP mismatch: missing_in_points={missing_in_points}, missing_in_dat={missing_in_dat}")

    # Assign each true point a flux equal to its share of the DAT count divided
    # by the Cosima buildup TT for that source card. This is a smoke activation
    # proxy, not a day-15 activity.
    enriched = []
    for point in points:
        key = (point["VN"], int(point["ZA"]), float(point["exc_keV"]))
        n_points = points_by_key[key]
        tt = tt_by_key[key]
        flux = float(counts[key]) / float(n_points) / float(tt)
        enriched.append({**point, "flux_Bq_proxy": flux})

    return {
        "dat_payloads": dat_payloads,
        "points": enriched,
        "counts_by_key": counts,
        "points_by_key": points_by_key,
        "total_flux_Bq_proxy": sum(p["flux_Bq_proxy"] for p in enriched),
    }


def build_source(triggers: int) -> dict[str, Any]:
    probe = collect_probe()
    points = probe["points"]
    if not points:
        raise SystemExit("No BGO activation probe RPIP points found")
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    TRANSPORT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
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
    lines.extend(f"DecayRun.Source RP_{idx:05d}" for idx, _ in enumerate(points))
    lines.append("")
    lines.append("# ===== Bgo_sample delayed-source smoke PointSource blocks =====")
    for idx, point in enumerate(points):
        name = f"RP_{idx:05d}"
        lines.append(f"{name}.ParticleType {point['ZA']}")
        lines.append(f"{name}.Beam PointSource {point['x_cm']:.6f} {point['y_cm']:.6f} {point['z_cm']:.6f}")
        lines.append(f"{name}.Flux {point['flux_Bq_proxy']:.8e}")
        lines.append("")
    SOURCE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    by_species = Counter((p["VN"], p["ZA"]) for p in points)
    manifest = {
        "status": "PASS_BGO_SAMPLE_DELAYED_SOURCE_SMOKE_READY",
        "claim_level": "BGO_SAMPLE_DELAYED_SOURCE_TRANSPORT_SMOKE_ONLY_NO_RATE_AUTHORITY",
        "source": rel(SOURCE),
        "geometry": rel(GEOMETRY),
        "source_prefix": rel(SOURCE_PREFIX),
        "probe_run_dir": rel(PROBE_DIR),
        "source_mode": "one_PointSource_per_real_RPIP_probe_position",
        "n_pointsource_blocks": len(points),
        "triggers_requested": int(triggers),
        "total_flux_Bq_proxy": probe["total_flux_Bq_proxy"],
        "dat_total_rp_count": sum(float(v) for v in probe["counts_by_key"].values()),
        "rpip_points": len(points),
        "rpip_keys": len(probe["counts_by_key"]),
        "top_species": [
            {"VN": vn, "ZA": za, "points": count}
            for (vn, za), count in by_species.most_common(20)
        ],
        "inputs": {
            "dat_files": [payload["path"] for payload in probe["dat_payloads"]],
            "sim_files": sorted(rel(path) for path in PROBE_DIR.glob("*.sim.gz")),
        },
        "boundary": [
            "Activation probe uses p,n buildup only at 50k gamma-equivalent statistics.",
            "Flux values are a smoke proxy from DAT production counts divided by probe TT, not day-15 BGO activity.",
            "This source proves BGO delayed PointSource formatting and Cosima transport connectivity only.",
        ],
    }
    write_json(MANIFEST, manifest)
    write_summary({"manifest": manifest, "transport": None})
    print(json.dumps({"status": manifest["status"], "source": manifest["source"], "manifest": rel(MANIFEST)}, indent=2))
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
                info["geometry"] = raw.strip().split(" ", 1)[1].strip()
    return info


def summarize_transport() -> dict[str, Any]:
    manifest = load_json(MANIFEST)
    sim_path = SOURCE_PREFIX.with_suffix(".inc1.id1.sim.gz")
    transport = sim_info(sim_path)
    problems: list[str] = []
    if not transport["exists"]:
        problems.append("missing_delayed_transport_sim")
    if transport["SE"] != transport["ID"]:
        problems.append("SE_ID_mismatch")
    if transport["SE"] <= 0:
        problems.append("no_delayed_transport_events")
    if "Bgo_sample/Bgo_sample.geo.setup" not in transport["geometry"]:
        problems.append("transport_geometry_not_Bgo_sample")
    transport["status"] = "PASS" if not problems else "FAIL"
    manifest["status"] = "PASS_BGO_SAMPLE_DELAYED_TRANSPORT_SMOKE" if not problems else "FAIL_BGO_SAMPLE_DELAYED_TRANSPORT_SMOKE"
    manifest["delayed_transport"] = transport
    manifest["problems"] = problems
    write_json(MANIFEST, manifest)
    write_summary({"manifest": manifest, "transport": transport})
    print(json.dumps({"status": manifest["status"], "problems": problems, "transport": transport}, indent=2))
    return manifest


def write_summary(payload: dict[str, Any]) -> None:
    manifest = payload["manifest"]
    transport = payload.get("transport")
    summary = {
        "status": manifest["status"],
        "claim_level": manifest["claim_level"],
        "manifest": rel(MANIFEST),
        "source": manifest["source"],
        "geometry": manifest["geometry"],
        "probe_run_dir": manifest["probe_run_dir"],
        "n_pointsource_blocks": manifest["n_pointsource_blocks"],
        "triggers_requested": manifest["triggers_requested"],
        "total_flux_Bq_proxy": manifest["total_flux_Bq_proxy"],
        "dat_total_rp_count": manifest["dat_total_rp_count"],
        "rpip_points": manifest["rpip_points"],
        "rpip_keys": manifest["rpip_keys"],
        "top_species": manifest["top_species"],
        "delayed_transport": transport,
        "problems": manifest.get("problems", []),
        "boundary": manifest["boundary"],
    }
    write_json(SUMMARY_JSON, summary)
    lines = [
        "# Bgo_sample Delayed-Source Smoke",
        "",
        f"Status: `{summary['status']}`.",
        "",
        f"- source: `{summary['source']}`",
        f"- manifest: `{summary['manifest']}`",
        f"- probe run: `{summary['probe_run_dir']}`",
        f"- PointSource blocks: `{summary['n_pointsource_blocks']}`",
        f"- triggers requested: `{summary['triggers_requested']}`",
        f"- proxy flux sum: `{summary['total_flux_Bq_proxy']:.8g} Bq`",
        f"- DAT RP count: `{summary['dat_total_rp_count']}`",
        f"- RPIP points: `{summary['rpip_points']}`",
    ]
    if transport:
        lines.extend(
            [
                f"- delayed sim: `{transport['path']}`",
                f"- SE/ID/TS: `{transport['SE']}/{transport['ID']}/{transport['TS']}`",
                f"- TE: `{transport['TE_s']}` s",
            ]
        )
    lines.extend(
        [
            "",
            "Boundary:",
            "- This is a BGO delayed-source and delayed-transport smoke only.",
            "- The activation probe is p,n only at 50k gamma-equivalent statistics and does not define a BGO background rate.",
            "- Production day-15 BGO delayed-source/rate transport remains not run.",
            "- Step05 response, Step06--Step08 significance, and BGO-vs-CsI comparison remain not run.",
            "",
        ]
    )
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build")
    build.add_argument("--triggers", type=int, default=200)
    sub.add_parser("summarize-transport")
    args = parser.parse_args()
    if args.cmd == "build":
        build_source(triggers=args.triggers)
    elif args.cmd == "summarize-transport":
        manifest = summarize_transport()
        return 0 if manifest["status"].startswith("PASS") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
