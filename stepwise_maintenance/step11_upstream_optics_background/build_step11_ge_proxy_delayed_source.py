#!/usr/bin/env python3
"""Build and analyze the Step11 upstream Ge-proxy delayed source.

This keeps the upstream Laue-lens hardware branch separate from the baseline
detector/cryostat activation budget.  Only isotope records produced inside the
equal-mass Ge annulus proxy are converted to delayed PointSource blocks.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
STEP = ROOT / "stepwise_maintenance" / "step11_upstream_optics_background"
BUILDUP = ROOT / "runs" / "step11_upstream_optics_fullstat_buildup_r1060"
SOURCE_DIR = ROOT / "runs" / "step11_upstream_optics_ge_proxy_delay_source"
TRANSPORT_DIR = ROOT / "runs" / "step11_upstream_optics_ge_proxy_delayed_transport"
SOURCE_PREFIX = TRANSPORT_DIR / "DelayedDecayStep11GeProxyExactpos"
SOURCE = SOURCE_DIR / "activation_decay_day15_step11_ge_proxy_exactpos.source"
MANIFEST = SOURCE_DIR / "step11_ge_proxy_exactpos_manifest.json"
WEIGHTED_TABLE = SOURCE_DIR / "step11_ge_proxy_true_rpip_table.csv"
RESPONSE_DIR = STEP / "outputs_ge_proxy_delayed_response"
RESPONSE_JSON = RESPONSE_DIR / "step11_ge_proxy_delayed_detector_response_summary.json"
RESPONSE_CSV = RESPONSE_DIR / "step11_ge_proxy_delayed_detector_response_rates.csv"
NUBASE = ROOT / "inputs" / "nubase" / "nubase_2020.txt"
GEOMETRY = (
    STEP
    / "smoke_geometry"
    / "DEMO2_DR_v3p5_centerfinger_with_f10m_laue_ge_proxy.geo.setup"
)
TARGET_VOLUME = "Step11_Laue_Ge_Annulus_Proxy"
T_FLIGHT_DAYS = 15.0

NUM = r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)
VN_RE = re.compile(r"^\s*VN\s+(\S+)\s*$")
RP_RE = re.compile(r"^\s*RP\s+(\d+)\s+([-\d.]+)\s+([-\d.eE+]+)\s*$")
TT_RE = re.compile(r"^\s*TT\s+([-\d.eE+]+)\s*$")
IP_RE = re.compile(
    r"^CC\s+IP\s+RP\s+(?P<vn>\S+)\s+"
    rf"(?P<x>{NUM})\s+(?P<y>{NUM})\s+(?P<z>{NUM})\s+"
    rf"(?P<za>\d+)\s+(?P<exc>{NUM})\s+(?P<t>{NUM})"
)

SYMS = [
    None,
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
    "At",
    "Rn",
    "Fr",
    "Ra",
    "Ac",
    "Th",
    "Pa",
    "U",
    "Np",
    "Pu",
    "Am",
    "Cm",
    "Bk",
    "Cf",
    "Es",
    "Fm",
]

UNIT_SECONDS = {
    "ps": 1.0e-12,
    "ns": 1.0e-9,
    "us": 1.0e-6,
    "ms": 1.0e-3,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "y": 31557600.0,
    "ky": 1.0e3 * 31557600.0,
    "My": 1.0e6 * 31557600.0,
    "Gy": 1.0e9 * 31557600.0,
    "Ty": 1.0e12 * 31557600.0,
    "Py": 1.0e15 * 31557600.0,
    "Ey": 1.0e18 * 31557600.0,
    "Zy": 1.0e21 * 31557600.0,
    "Yy": 1.0e24 * 31557600.0,
}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_tag(path: Path | str) -> str:
    match = TAG_RE.search(Path(path).name)
    return match.group("tag").lower() if match else "unknown"


def division_by_tag(dat_files: list[Path], non_gamma_div: float, gamma_div: str) -> dict[str, float]:
    counts = Counter(parse_tag(path) for path in dat_files)
    out: dict[str, float] = {}
    for tag, count in counts.items():
        if tag == "gamma":
            out[tag] = float(count if str(gamma_div).lower() == "auto" else gamma_div)
        else:
            out[tag] = float(non_gamma_div)
    return out


def za_to_nuclide(za: int) -> str:
    z = za // 1000
    a = za % 1000
    if 0 < z < len(SYMS) and SYMS[z]:
        return f"{SYMS[z]}-{a}"
    return f"Z{z}-A{a}"


def parse_half_life_seconds(value: str, unit: str) -> float | None:
    txt = value.strip()
    if not txt:
        return None
    if "stbl" in txt.lower() or "stable" in txt.lower():
        return math.inf
    txt = re.sub(r"[#?><~*&]", "", txt).strip()
    if not txt:
        return None
    try:
        val = float(txt)
    except ValueError:
        return None
    u = unit.strip() or "s"
    return val * UNIT_SECONDS[u] if u in UNIT_SECONDS else None


def load_nubase_ground_half_lives(path: Path) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for lineno, line in enumerate(handle, 1):
            if len(line) < 90 or line.startswith("#"):
                continue
            try:
                a = int(line[0:3].strip())
                zstate = line[4:8].strip()
                z = int(zstate[:3])
                state = zstate[3:] if len(zstate) > 3 else "0"
            except ValueError:
                continue
            if state not in ("", "0"):
                continue
            field = line[69:78].strip()
            unit = line[78:80].strip()
            context = line[69:90]
            if "stbl" in context.lower() or "stable" in context.lower():
                half_life_s = math.inf
                why = "nubase_ground_stable"
            else:
                half_life_s = parse_half_life_seconds(field, unit)
                why = "nubase_ground"
            if half_life_s is None:
                continue
            out[1000 * z + a] = {
                "half_life_s": half_life_s,
                "why": why,
                "raw_value": field,
                "raw_unit": unit,
                "line": lineno,
            }
    return out


def activity_after_exposure(nprod: float, tt_s: float, half_life_s: float, t_flight_days: float) -> float:
    if nprod <= 0.0 or tt_s <= 0.0 or half_life_s <= 0.0 or math.isinf(half_life_s):
        return 0.0
    lam = math.log(2.0) / half_life_s
    return (nprod / tt_s) * (-math.expm1(-lam * t_flight_days * 86400.0))


def sim_for_dat(path: Path) -> Path:
    name = path.name
    if not name.endswith(".dat.inc1.dat"):
        raise ValueError(path)
    return path.with_name(name[: -len(".dat.inc1.dat")] + ".inc1.id1.sim.gz")


def parse_target_dat(
    dat_files: list[Path],
    non_gamma_div: float,
    gamma_div: str,
) -> tuple[
    dict[str, float],
    dict[tuple[str, str, int, float], float],
    dict[str, Any],
    dict[tuple[str, str, int, float], list[str]],
]:
    divs = division_by_tag(dat_files, non_gamma_div, gamma_div)
    tt_values: dict[str, list[float]] = defaultdict(list)
    target_yield: dict[tuple[str, str, int, float], float] = defaultdict(float)
    source_dat_by_key: dict[tuple[str, str, int, float], list[str]] = defaultdict(list)
    audit_rows: dict[str, dict[str, Any]] = {}
    for path in dat_files:
        tag = parse_tag(path)
        row = audit_rows.setdefault(
            tag,
            {
                "tag": tag,
                "files": 0,
                "division": divs[tag],
                "tt_files": 0,
                "tt_sum_s": 0.0,
                "tt_mean_s": 0.0,
                "tt_min_s": None,
                "tt_max_s": None,
                "target_rp_raw_total": 0.0,
                "target_rp_scaled_total": 0.0,
            },
        )
        row["files"] += 1
        cur_vn = ""
        tt_in_file: list[float] = []
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for raw in handle:
                tm = TT_RE.match(raw)
                if tm:
                    try:
                        tt_in_file.append(float(tm.group(1)))
                    except ValueError:
                        pass
                    continue
                vm = VN_RE.match(raw)
                if vm:
                    cur_vn = vm.group(1)
                    continue
                rm = RP_RE.match(raw)
                if not rm or cur_vn != TARGET_VOLUME:
                    continue
                za = int(rm.group(1))
                exc = float(rm.group(2))
                if abs(exc) < 1.0e-6:
                    exc = 0.0
                raw_count = float(rm.group(3))
                scaled = raw_count / float(divs[tag])
                key = (tag, cur_vn, za, exc)
                target_yield[key] += scaled
                source_dat_by_key[key].append(rel(path))
                row["target_rp_raw_total"] += raw_count
                row["target_rp_scaled_total"] += scaled
        if tt_in_file:
            tt = tt_in_file[-1]
            if tt > 0.0:
                tt_values[tag].append(tt)
                row["tt_files"] += 1
                row["tt_sum_s"] += tt
                row["tt_min_s"] = tt if row["tt_min_s"] is None else min(float(row["tt_min_s"]), tt)
                row["tt_max_s"] = tt if row["tt_max_s"] is None else max(float(row["tt_max_s"]), tt)

    tt_by_tag: dict[str, float] = {}
    for tag, values in tt_values.items():
        row = audit_rows[tag]
        row["tt_mean_s"] = math.fsum(values) / len(values)
        tt_by_tag[tag] = float(row["tt_mean_s"])

    problems = []
    for tag, row in sorted(audit_rows.items()):
        if int(row["tt_files"]) != int(row["files"]):
            problems.append(f"tag={tag} has TT in {row['tt_files']}/{row['files']} files")
        if tag == "gamma" and str(gamma_div).lower() == "auto" and float(row["division"]) != float(row["files"]):
            problems.append(f"gamma division mismatch: {row['division']} vs files={row['files']}")
    audit = {
        "status": "PASS" if not problems else "FAIL",
        "problems": problems,
        "non_gamma_div": float(non_gamma_div),
        "gamma_div": gamma_div,
        "rows": [audit_rows[tag] for tag in sorted(audit_rows)],
    }
    if problems:
        raise SystemExit("Step11 normalization audit failed: " + "; ".join(problems))
    return tt_by_tag, dict(target_yield), audit, source_dat_by_key


def parse_rpip_points(
    activity_by_prod_key: dict[tuple[str, str, int, float], float],
    source_dat_by_key: dict[tuple[str, str, int, float], list[str]],
    divs: dict[str, float],
) -> list[dict[str, Any]]:
    wanted = {key for key, activity in activity_by_prod_key.items() if activity > 0.0}
    dat_paths = {
        ROOT / path
        for paths in source_dat_by_key.values()
        for path in paths
    }
    sim_paths = sorted({sim_for_dat(path) for path in dat_paths})
    points: list[dict[str, Any]] = []
    for path in sim_paths:
        if not path.exists():
            raise FileNotFoundError(path)
        tag = parse_tag(path)
        wfile = 1.0 / float(divs.get(tag, 1.0))
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
            for raw in handle:
                if not raw.startswith("CC IP RP"):
                    continue
                match = IP_RE.match(raw.strip())
                if not match or match.group("vn") != TARGET_VOLUME:
                    continue
                exc = float(match.group("exc"))
                if abs(exc) < 1.0e-6:
                    exc = 0.0
                key = (tag, TARGET_VOLUME, int(match.group("za")), exc)
                if key not in wanted:
                    continue
                points.append(
                    {
                        "prod_key": key,
                        "tag": tag,
                        "VN": TARGET_VOLUME,
                        "ZA": int(match.group("za")),
                        "exc_keV": exc,
                        "x_cm": float(match.group("x")),
                        "y_cm": float(match.group("y")),
                        "z_cm": float(match.group("z")),
                        "t_s": float(match.group("t")),
                        "wfile": wfile,
                        "source_sim": rel(path),
                    }
                )
    return points


def source_header(triggers: int, n_sources: int) -> list[str]:
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
    lines.extend(f"DecayRun.Source RP_{idx:07d}" for idx in range(n_sources))
    lines.extend(["", "# True RPIP PointSource blocks for the upstream Ge proxy only"])
    return lines


def summarize_run(path: Path) -> dict[str, Any]:
    summary_path = path / "run_summary.json"
    norm_path = path / "normalization.json"
    out: dict[str, Any] = {"run_dir": rel(path), "exists": path.exists()}
    if summary_path.exists():
        rows = read_json(summary_path)
        out.update(
            {
                "jobs": len(rows),
                "pass_or_skip": sum(1 for row in rows if row.get("status") in ("PASS", "SKIP")),
                "fail": sum(1 for row in rows if row.get("status") == "FAIL"),
                "events_requested": sum(int(row.get("events") or 0) for row in rows),
                "events_generated": sum(int(row.get("generated_particles") or 0) for row in rows),
                "cpu_s": sum(float(row.get("cpu_s") or 0.0) for row in rows),
            }
        )
    if norm_path.exists():
        norm = read_json(norm_path)
        out.update(
            {
                "farfield_radius_cm": norm.get("farfield_radius_cm"),
                "farfield_area_cm2": norm.get("farfield_area_cm2"),
                "gamma_splits": norm.get("gamma_splits"),
                "non_gamma_replicas": norm.get("non_gamma_replicas"),
                "particle_families": norm.get("selected_particles"),
            }
        )
    return out


def build_source(triggers: int, non_gamma_div: float, gamma_div: str, t_flight_days: float) -> dict[str, Any]:
    dat_files = sorted(BUILDUP.glob("*.dat.inc1.dat"))
    if not dat_files:
        raise FileNotFoundError(BUILDUP)
    if not GEOMETRY.exists():
        raise FileNotFoundError(GEOMETRY)
    if not NUBASE.exists():
        raise FileNotFoundError(NUBASE)

    tt_by_tag, target_yield, normalization_audit, source_dat_by_key = parse_target_dat(
        dat_files,
        non_gamma_div,
        gamma_div,
    )
    if not target_yield:
        raise SystemExit(f"No target isotope inventory found for {TARGET_VOLUME}")
    divs = {row["tag"]: float(row["division"]) for row in normalization_audit["rows"]}
    half_lives = load_nubase_ground_half_lives(NUBASE)

    activity_rows: list[dict[str, Any]] = []
    activity_by_prod_key: dict[tuple[str, str, int, float], float] = {}
    for key, nprod in sorted(target_yield.items()):
        tag, vn, za, exc = key
        hl = half_lives.get(za)
        if exc != 0.0 or not hl:
            activity = 0.0
            reason = "skipped_excited_or_missing_half_life"
        else:
            activity = activity_after_exposure(nprod, tt_by_tag.get(tag, 0.0), float(hl["half_life_s"]), t_flight_days)
            reason = "ground_state_day15_activity"
        activity_by_prod_key[key] = activity
        activity_rows.append(
            {
                "tag": tag,
                "VN": vn,
                "ZA": za,
                "nuclide": za_to_nuclide(za),
                "exc_keV": exc,
                "scaled_production_yield": nprod,
                "tt_mean_s": tt_by_tag.get(tag),
                "half_life_s": None if not hl else ("inf" if math.isinf(float(hl["half_life_s"])) else float(hl["half_life_s"])),
                "half_life_source": None if not hl else hl["why"],
                "nubase_line": None if not hl else hl["line"],
                "activity_Bq": activity,
                "reason": reason,
                "source_dat_files": source_dat_by_key.get(key, []),
            }
        )

    points = parse_rpip_points(activity_by_prod_key, source_dat_by_key, divs)
    denom_by_key: dict[tuple[str, str, int, float], float] = defaultdict(float)
    for point in points:
        denom_by_key[point["prod_key"]] += float(point["wfile"])

    source_rows: list[dict[str, Any]] = []
    missing_support = []
    for key, activity in activity_by_prod_key.items():
        if activity <= 0.0:
            continue
        denom = denom_by_key.get(key, 0.0)
        if denom <= 0.0:
            missing_support.append(f"{key}")
            continue
        for point in [p for p in points if p["prod_key"] == key]:
            flux = activity * float(point["wfile"]) / denom
            source_rows.append({**point, "flux_Bq": flux})
    if missing_support:
        raise SystemExit("positive target activity without true RPIP support: " + "; ".join(missing_support))
    if not source_rows:
        raise SystemExit("target inventory produced zero positive delayed source rows")

    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    TRANSPORT_DIR.mkdir(parents=True, exist_ok=True)
    with WEIGHTED_TABLE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "tag",
                "VN",
                "ZA",
                "nuclide",
                "exc_keV",
                "x_cm",
                "y_cm",
                "z_cm",
                "t_s",
                "wfile",
                "flux_Bq",
                "source_sim",
            ],
        )
        writer.writeheader()
        for row in source_rows:
            writer.writerow(
                {
                    "tag": row["tag"],
                    "VN": row["VN"],
                    "ZA": row["ZA"],
                    "nuclide": za_to_nuclide(int(row["ZA"])),
                    "exc_keV": f"{row['exc_keV']:.8g}",
                    "x_cm": f"{row['x_cm']:.8g}",
                    "y_cm": f"{row['y_cm']:.8g}",
                    "z_cm": f"{row['z_cm']:.8g}",
                    "t_s": f"{row['t_s']:.8g}",
                    "wfile": f"{row['wfile']:.8g}",
                    "flux_Bq": f"{row['flux_Bq']:.12e}",
                    "source_sim": row["source_sim"],
                }
            )

    with SOURCE.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(source_header(triggers, len(source_rows))) + "\n")
        for idx, row in enumerate(source_rows):
            name = f"RP_{idx:07d}"
            handle.write(f"{name}.ParticleType {int(row['ZA'])}\n")
            handle.write(f"{name}.Beam PointSource {row['x_cm']:.6f} {row['y_cm']:.6f} {row['z_cm']:.6f}\n")
            handle.write(f"{name}.Flux {row['flux_Bq']:.8e}\n\n")

    total_activity = math.fsum(float(row["flux_Bq"]) for row in source_rows)
    manifest = {
        "status": "PASS_STEP11_GE_PROXY_EXACTPOS_DELAYED_SOURCE_READY",
        "claim_level": "UPSTREAM_GE_PROXY_DELAYED_SOURCE_READY_NOT_SELECTED_RATE",
        "source_mode": "all_positive_true_rpip_pointsource_blocks",
        "target_volume": TARGET_VOLUME,
        "source": rel(SOURCE),
        "manifest": rel(MANIFEST),
        "weighted_table": rel(WEIGHTED_TABLE),
        "geometry": rel(GEOMETRY),
        "outfile_prefix": rel(SOURCE_PREFIX),
        "triggers_requested": int(triggers),
        "t_flight_days": float(t_flight_days),
        "normalization_audit": normalization_audit,
        "activity_rows": activity_rows,
        "source_blocks": len(source_rows),
        "rpip_rows_seen_for_positive_activity": len(points),
        "total_activity_Bq": total_activity,
        "sum_flux_check_Bq": total_activity,
        "top_source_rows": sorted(
            [
                {
                    "ZA": int(row["ZA"]),
                    "nuclide": za_to_nuclide(int(row["ZA"])),
                    "flux_Bq": float(row["flux_Bq"]),
                    "source_sim": row["source_sim"],
                    "x_cm": float(row["x_cm"]),
                    "y_cm": float(row["y_cm"]),
                    "z_cm": float(row["z_cm"]),
                }
                for row in source_rows
            ],
            key=lambda item: item["flux_Bq"],
            reverse=True,
        ),
        "production_transport": summarize_run(BUILDUP),
        "boundary": [
            "Only isotope inventory produced inside the upstream Ge annulus proxy is converted here.",
            "Detector/cryostat isotope records in the combined Step11 geometry are intentionally excluded to avoid double counting the baseline detector delayed background.",
            "The source uses all positive true RPIP positions; no M-sampling approximation is used for this small upstream proxy inventory.",
            "This is still an equal-mass active-Ge proxy for the Laue crystal mass; explicit lens tile, frame, and support hardware remain a future design bracket.",
        ],
    }
    write_json(MANIFEST, manifest)
    print(json.dumps({"status": manifest["status"], "source": rel(SOURCE), "source_blocks": len(source_rows), "total_activity_Bq": total_activity}, indent=2))
    return manifest


def open_sim(path: Path):
    return gzip.open(path, "rt", encoding="utf-8", errors="ignore")


def transport_candidates() -> list[Path]:
    pattern = SOURCE_PREFIX.name + ".inc*.id1.sim.gz"
    candidates = sorted(SOURCE_PREFIX.parent.glob(pattern))

    def inc_number(path: Path) -> int:
        match = re.search(r"\.inc(\d+)\.id1\.sim\.gz$", path.name)
        return int(match.group(1)) if match else -1

    return sorted(candidates, key=inc_number)


def latest_transport_path() -> Path:
    candidates = transport_candidates()
    if candidates:
        return candidates[-1]
    return SOURCE_PREFIX.with_suffix(".inc1.id1.sim.gz")


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
    manifest = read_json(MANIFEST)
    transport = sim_info(latest_transport_path())
    problems = []
    if not transport["exists"]:
        problems.append("missing_delayed_transport_sim")
    if transport["SE"] != transport["ID"]:
        problems.append("SE_ID_mismatch")
    if int(transport["SE"]) != int(manifest.get("triggers_requested", -1)):
        problems.append("generated_event_count_mismatch")
    if transport["SE"] <= 0:
        problems.append("no_delayed_events")
    if rel(GEOMETRY) not in str(transport.get("geometry", "")):
        problems.append("transport_geometry_mismatch")
    manifest["delayed_transport"] = transport
    manifest["problems"] = problems
    if problems:
        manifest["status"] = "FAIL_STEP11_GE_PROXY_EXACTPOS_DELAYED_TRANSPORT"
    else:
        manifest["status"] = "PASS_STEP11_GE_PROXY_EXACTPOS_DELAYED_TRANSPORT"
        manifest["claim_level"] = "UPSTREAM_GE_PROXY_DELAYED_TRANSPORT_READY_NOT_SELECTED_RATE"
    write_json(MANIFEST, manifest)
    print(json.dumps({"status": manifest["status"], "problems": problems, "transport": transport}, indent=2))
    return manifest


def load_module(name: str, path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def summarize_response() -> dict[str, Any]:
    manifest = read_json(MANIFEST)
    transport = manifest.get("delayed_transport") or sim_info(latest_transport_path())
    te_s = transport.get("TE_s")
    if not te_s or float(te_s) <= 0.0:
        raise SystemExit("Delayed transport TE_s is missing; run summarize-transport first.")
    sim_path = ROOT / str(transport["path"])
    if not sim_path.exists():
        raise FileNotFoundError(sim_path)

    adr = load_module("make_complete_day15_report_ADR_step11", ROOT / "code" / "tools" / "make_complete_day15_report_ADR.py")
    step05 = load_module("build_v3p5_centerfinger_step05_l1_response_step11", ROOT / "code" / "tools" / "build_v3p5_centerfinger_step05_l1_response.py")
    adr.is_active_veto_volume = step05.is_v3p5_active_veto_volume
    adr.event_rate_for_mode = lambda path, mode, science_flux: ("delayed", "step11_ge_proxy_activation", 1.0 / float(te_s))
    cat = adr.catalog_to_arrays(adr.parse_sim_catalog((str(sim_path), "delayed", 1.0)))
    disk = step05.side_entry_disk()
    reject_policy = "keep"
    windows = {
        name: step05.summarize_window(cat, *bounds, disk=disk, reject_policy=reject_policy)
        for name, bounds in step05.WINDOWS.items()
    }
    zero_count_95_rate = -math.log(0.05) / float(te_s)
    payload = {
        "status": "PASS_STEP11_GE_PROXY_DELAYED_DETECTOR_RESPONSE",
        "claim_level": "UPSTREAM_GE_PROXY_DELAYED_SELECTED_RATE_COMPONENT",
        "source_manifest": rel(MANIFEST),
        "delayed_sim": rel(sim_path),
        "target_volume": TARGET_VOLUME,
        "total_activity_Bq": manifest.get("total_activity_Bq"),
        "delayed_time_s": float(te_s),
        "event_rate_per_generated_decay_s-1": 1.0 / float(te_s),
        "active_veto_threshold_keV": step05.ACTIVE_VETO_THRESHOLD_KEV,
        "reject_policy": reject_policy,
        "catalog": {
            "events_kept": int(len(cat["stream"])),
            "generated_events_seen": int(cat["n_generated_events_seen"]),
            "pixel_hits_kept": int(len(cat["pix_e"])),
            "tes_events": int(sum((cat["stream"] == "delayed") & (cat["tes_total_keV"] > 0))),
        },
        "windows": windows,
        "zero_count_upper_limits": {
            "confidence_level": 0.95,
            "events": -math.log(0.05),
            "rate_s-1": zero_count_95_rate,
            "applies_to": "Use when a selected stage has zero observed events in this closure batch.",
        },
        "boundary": [
            "This response file is a separate upstream Ge-proxy delayed component.",
            "It should be merged into the final hard-window background budget as an additive selected-rate component, not by replacing the baseline detector delayed rate.",
            "Prompt self-background from the upstream hardware still requires a provenance-isolated selected-rate estimate or an explicit subtraction strategy.",
        ],
    }
    RESPONSE_DIR.mkdir(parents=True, exist_ok=True)
    with RESPONSE_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["window", "stream", "stage", "events", "rate_s-1"])
        for window, item in windows.items():
            for stream, row in item["by_stream"].items():
                writer.writerow([window, stream, "raw", row["raw_events"], f"{row['raw_rate_s-1']:.12g}"])
                writer.writerow([window, stream, "active_veto_pass", row["active_veto_pass_events"], f"{row['active_veto_pass_rate_s-1']:.12g}"])
                writer.writerow([window, stream, "side_compton_fov_pass", row["side_compton_fov_pass_events"], f"{row['side_compton_fov_pass_rate_s-1']:.12g}"])
    write_json(RESPONSE_JSON, payload)
    manifest["detector_response"] = {
        "summary": rel(RESPONSE_JSON),
        "rates_csv": rel(RESPONSE_CSV),
        "status": payload["status"],
        "w2_delayed": windows["w2_510p58_511p42"]["by_stream"]["delayed"],
        "zero_count_95_rate_s-1": zero_count_95_rate,
    }
    manifest["status"] = "PASS_STEP11_GE_PROXY_DELAYED_SELECTED_RATE_COMPONENT"
    manifest["claim_level"] = "UPSTREAM_GE_PROXY_DELAYED_SELECTED_RATE_COMPONENT_PROMPT_SELF_BACKGROUND_OPEN"
    write_json(MANIFEST, manifest)
    print(json.dumps({"status": payload["status"], "summary": rel(RESPONSE_JSON), "w2_delayed": manifest["detector_response"]["w2_delayed"]}, indent=2))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    build = sub.add_parser("build-source")
    build.add_argument("--triggers", type=int, default=1_000_000)
    build.add_argument("--non-gamma-div", type=float, default=8.0)
    build.add_argument("--gamma-div", default="auto")
    build.add_argument("--t-flight-days", type=float, default=T_FLIGHT_DAYS)
    sub.add_parser("summarize-transport")
    sub.add_parser("summarize-response")
    args = parser.parse_args()

    if args.cmd == "build-source":
        build_source(args.triggers, args.non_gamma_div, args.gamma_div, args.t_flight_days)
    elif args.cmd == "summarize-transport":
        manifest = summarize_transport()
        return 0 if manifest["status"].startswith("PASS") else 1
    elif args.cmd == "summarize-response":
        summarize_response()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
