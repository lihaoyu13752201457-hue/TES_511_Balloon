#!/usr/bin/env python3
"""Build a delayed activation source with ground-state half-lives fixed.

This is a post-processor for the existing RPIP delayed source.  It leaves the
original source and profile files untouched, parses the same RP totals used by
the original workflow, recomputes activities for exc=0 nuclei from the local
NUBASE ground-state records, and rescales/removes matching source blocks.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RPIP_DIR = ROOT / "cosmosray_buildup_rpmpia"
ORIG_OUT = RPIP_DIR / "decay_rpip_out"
DEFAULT_SOURCE = ORIG_OUT / "activation_decay_day15.source"
DEFAULT_NUBASE = ORIG_OUT / "nubase_2020.txt"
DEFAULT_OUTDIR = ROOT / "delay_fix"

TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)
VN_RE = re.compile(r"^\s*VN\s+(\S+)\s*$")
RP_RE = re.compile(r"^\s*RP\s+(\d+)\s+([-\d.]+)\s+([-\d.eE+]+)\s*$")
TT_RE = re.compile(r"^\s*TT\s+([-\d.eE+]+)\s*$")
SOURCE_LINE_RE = re.compile(r"^(?P<run>\S+)\.Source\s+(?P<name>S_\S+)\s*$")
PARTICLE_RE = re.compile(r"^(?P<name>S_\S+)\.ParticleType\s+(?P<za>\d+)\s*$")
FLUX_RE = re.compile(r"^(?P<name>S_\S+)\.Flux\s+(?P<flux>[-+0-9.eE]+)\s*$")
SOURCE_NAME_RE = re.compile(r"^S_(?P<vn>.+)_(?P<za>\d+)_z(?P<iz>\d+)$")

RE_SEG_SHIELD = re.compile(r"^(Nb_Shield|W_Shield|Cryo_Shell|BGO_Shield|Al_Shell)(?:_p\d+_z\d+)?$", re.I)
RE_TP = re.compile(r"^TP_L(?P<l>\d+)_\d+$", re.I)
RE_TESPIX = re.compile(r"^TES_Pixel_L(?P<l>\d+)$", re.I)
RE_COLLBAR = re.compile(r"^(CollBar[XY])_\d+$", re.I)

SYMS = [
    None, "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
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


def parse_tag(path: Path) -> str:
    m = TAG_RE.search(path.name)
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


def za_to_nuclide(za: int) -> str:
    z = za // 1000
    a = za % 1000
    if 0 < z < len(SYMS) and SYMS[z]:
        return f"{SYMS[z]}-{a}"
    return f"Z{za}"


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
    u = unit.strip()
    if not u:
        u = "s"
    if u in UNIT_SECONDS:
        return val * UNIT_SECONDS[u]
    ul = u.lower()
    if ul in UNIT_SECONDS:
        return val * UNIT_SECONDS[ul]
    return None


def load_nubase_ground_half_lives(path: Path) -> dict[int, dict[str, object]]:
    out: dict[int, dict[str, object]] = {}
    with path.open("r", encoding="utf-8", errors="ignore") as fh:
        for lineno, line in enumerate(fh, 1):
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
            za = 1000 * z + a
            field = line[69:78].strip()
            unit = line[78:80].strip()
            context = line[69:90]
            if "stbl" in context.lower() or "stable" in context.lower():
                hl = math.inf
                why = "nubase_ground_stable"
            else:
                hl = parse_half_life_seconds(field, unit)
                why = "nubase_ground"
            if hl is None:
                continue
            out[za] = {
                "half_life_s": hl,
                "why": why,
                "raw_value": field,
                "raw_unit": unit,
                "line": lineno,
                "raw_line": line.rstrip("\n"),
            }
    return out


def parse_rp_from_dat(dat_files: list[Path], non_gamma_div: float) -> tuple[dict[str, float], dict[tuple[str, str, int, float], float]]:
    rp: dict[tuple[str, str, int, float], float] = defaultdict(float)
    tt_by_tag: dict[str, float] = {}
    for path in dat_files:
        tag = parse_tag(path)
        div = 1.0 if tag == "gamma" else float(non_gamma_div)
        cur_vn = None
        tt_val = None
        with path.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                m = TT_RE.match(line)
                if m:
                    try:
                        tt_val = float(m.group(1))
                    except ValueError:
                        pass
                    continue
                m = VN_RE.match(line)
                if m:
                    cur_vn = canon_vn(m.group(1))
                    continue
                m = RP_RE.match(line)
                if m and cur_vn is not None:
                    za = int(m.group(1))
                    exc = float(m.group(2))
                    if abs(exc) < 1.0e-6:
                        exc = 0.0
                    rp[(tag, cur_vn, za, exc)] += float(m.group(3)) / div
        if tt_val and tt_val > 0.0:
            tt_by_tag[tag] = tt_val
    return tt_by_tag, rp


def activity_after_exposure(nprod: float, tt_s: float, half_life_s: float, t_flight_days: float) -> float:
    if nprod <= 0.0 or tt_s <= 0.0 or half_life_s <= 0.0:
        return 0.0
    if math.isinf(half_life_s):
        return 0.0
    lam = math.log(2.0) / half_life_s
    # Use expm1 so ultra-long half-lives such as W-180 ground state do not
    # round to exactly zero when lambda*T is far below double precision epsilon.
    return (nprod / tt_s) * (-math.expm1(-lam * t_flight_days * 86400.0))


def parse_source(path: Path) -> tuple[list[str], dict[str, int], dict[str, float], dict[str, tuple[str, int]]]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    name_za: dict[str, int] = {}
    name_flux: dict[str, float] = {}
    name_key: dict[str, tuple[str, int]] = {}
    for line in lines:
        m = PARTICLE_RE.match(line.strip())
        if m:
            name_za[m.group("name")] = int(m.group("za"))
            continue
        m = FLUX_RE.match(line.strip())
        if m:
            name_flux[m.group("name")] = float(m.group("flux"))
    for name, za in name_za.items():
        sm = SOURCE_NAME_RE.match(name)
        if sm:
            name_key[name] = (sm.group("vn"), za)
    return lines, name_za, name_flux, name_key


def write_fixed_source(
    lines: list[str],
    output: Path,
    name_key: dict[str, tuple[str, int]],
    name_flux: dict[str, float],
    scale_by_key: dict[tuple[str, int], float],
    min_flux_bq: float,
    outfile_prefix: str,
    geometry: Path | None,
    triggers: int | None,
) -> tuple[set[str], dict[str, float]]:
    new_flux_by_name: dict[str, float] = {}
    remove_names: set[str] = set()
    for name, key in name_key.items():
        old_flux = name_flux.get(name)
        if old_flux is None:
            continue
        new_flux = old_flux * scale_by_key.get(key, 1.0)
        new_flux_by_name[name] = new_flux
        if new_flux <= min_flux_bq:
            remove_names.add(name)

    out_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        m = SOURCE_LINE_RE.match(stripped)
        if m and m.group("name") in remove_names:
            continue
        if stripped.startswith("DecayRun.FileName "):
            out_lines.append(f"DecayRun.FileName {outfile_prefix}")
            continue
        if triggers is not None and stripped.startswith("DecayRun.Triggers "):
            out_lines.append(f"DecayRun.Triggers {int(triggers)}")
            continue
        if geometry is not None and stripped.startswith("Geometry "):
            out_lines.append(f"Geometry {geometry}")
            continue
        if ".Flux" in stripped:
            fm = FLUX_RE.match(stripped)
            if fm and fm.group("name") in new_flux_by_name:
                name = fm.group("name")
                if name in remove_names:
                    continue
                out_lines.append(f"{name}.Flux {new_flux_by_name[name]:.8e}")
                continue
        if "." in stripped:
            prefix = stripped.split(".", 1)[0]
            if prefix in remove_names:
                continue
        out_lines.append(line)

    output.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return remove_names, new_flux_by_name


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--dat-glob", default=str(RPIP_DIR / "Background_*_96deg_rep*_part*.dat.inc1.dat"))
    ap.add_argument("--nubase", type=Path, default=DEFAULT_NUBASE)
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    ap.add_argument("--outfile-prefix", default="DelayedDecayRPIPGroundStateFixed")
    ap.add_argument("--output-source-name", default="activation_decay_day15_groundstate_fixed.source")
    ap.add_argument("--triggers", type=int, default=None)
    ap.add_argument("--geometry", type=Path, default=ROOT / "XZTES/TibetTES_v5_6layers.geo.setup")
    ap.add_argument("--non-gamma-div", type=float, default=8.0)
    ap.add_argument("--t-flight-days", type=float, default=15.0)
    ap.add_argument("--min-flux-bq", type=float, default=1.0e-12)
    args = ap.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    dat_files = sorted(Path(p) for p in Path("/").glob(args.dat_glob.lstrip("/")))
    if not dat_files:
        raise SystemExit(f"No dat files matched: {args.dat_glob}")

    ground_hl = load_nubase_ground_half_lives(args.nubase)
    tt_by_tag, rp = parse_rp_from_dat(dat_files, args.non_gamma_div)
    lines, _name_za, name_flux, name_key = parse_source(args.source)

    old_activity_by_key: dict[tuple[str, int], float] = defaultdict(float)
    for name, key in name_key.items():
        old_activity_by_key[key] += name_flux.get(name, 0.0)

    new_activity_by_key: dict[tuple[str, int], float] = defaultdict(float)
    yield_by_key: dict[tuple[str, int], float] = defaultdict(float)
    has_ground_rp: set[tuple[str, int]] = set()
    for (tag, vn, za, exc), nprod in rp.items():
        if exc != 0.0:
            continue
        key = (vn, za)
        hl_info = ground_hl.get(za)
        if not hl_info:
            continue
        has_ground_rp.add(key)
        yield_by_key[key] += nprod
        new_activity_by_key[key] += activity_after_exposure(
            nprod,
            tt_by_tag.get(tag, 1.0),
            float(hl_info["half_life_s"]),
            args.t_flight_days,
        )

    scale_by_key: dict[tuple[str, int], float] = {}
    rows: list[dict[str, object]] = []
    for key, old_a in sorted(old_activity_by_key.items(), key=lambda item: item[1], reverse=True):
        vn, za = key
        hl_info = ground_hl.get(za)
        new_a = new_activity_by_key.get(key, old_a)
        if key not in has_ground_rp or not hl_info:
            scale = 1.0
            action = "kept_no_ground_recalc"
        else:
            scale = 0.0 if old_a <= 0.0 else new_a / old_a
            action = "kept_rescaled"
            if new_a <= args.min_flux_bq:
                action = "removed_negligible_or_stable"
        scale_by_key[key] = scale
        rows.append(
            {
                "VN": vn,
                "ZA": za,
                "nuclide": za_to_nuclide(za),
                "old_source_activity_Bq": old_a,
                "new_groundstate_activity_Bq": new_a,
                "scale": scale,
                "action": action,
                "RP_yield": yield_by_key.get(key, ""),
                "nubase_half_life_s": "" if not hl_info else ("inf" if math.isinf(float(hl_info["half_life_s"])) else float(hl_info["half_life_s"])),
                "nubase_why": "" if not hl_info else hl_info["why"],
                "nubase_line": "" if not hl_info else hl_info["line"],
                "nubase_raw_value": "" if not hl_info else hl_info["raw_value"],
                "nubase_raw_unit": "" if not hl_info else hl_info["raw_unit"],
            }
        )

    out_source = args.outdir / args.output_source_name
    remove_names, new_flux_by_name = write_fixed_source(
        lines,
        out_source,
        name_key,
        name_flux,
        scale_by_key,
        args.min_flux_bq,
        args.outfile_prefix,
        args.geometry,
        args.triggers,
    )

    corrections_csv = args.outdir / "groundstate_activity_corrections.csv"
    with corrections_csv.open("w", newline="", encoding="utf-8") as fh:
        fieldnames = [
            "VN",
            "ZA",
            "nuclide",
            "old_source_activity_Bq",
            "new_groundstate_activity_Bq",
            "scale",
            "action",
            "RP_yield",
            "nubase_half_life_s",
            "nubase_why",
            "nubase_line",
            "nubase_raw_value",
            "nubase_raw_unit",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    removed_csv = args.outdir / "removed_or_rescaled_sources.csv"
    with removed_csv.open("w", newline="", encoding="utf-8") as fh:
        fieldnames = ["source_name", "VN", "ZA", "nuclide", "old_flux_Bq", "new_flux_Bq", "removed"]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for name in sorted(name_key):
            key = name_key[name]
            old_flux = name_flux.get(name, 0.0)
            new_flux = new_flux_by_name.get(name, old_flux)
            if name in remove_names or abs(new_flux - old_flux) > max(1.0e-20, abs(old_flux) * 1.0e-6):
                writer.writerow(
                    {
                        "source_name": name,
                        "VN": key[0],
                        "ZA": key[1],
                        "nuclide": za_to_nuclide(key[1]),
                        "old_flux_Bq": old_flux,
                        "new_flux_Bq": new_flux,
                        "removed": name in remove_names,
                    }
                )

    summary = {
        "source_in": str(args.source),
        "source_out": str(out_source),
        "corrections_csv": str(corrections_csv),
        "removed_or_rescaled_sources_csv": str(removed_csv),
        "dat_files": len(dat_files),
        "old_total_activity_Bq": sum(name_flux.values()),
        "new_total_activity_Bq": sum(v for n, v in new_flux_by_name.items() if n not in remove_names),
        "source_blocks_in": len(name_key),
        "source_blocks_removed": len(remove_names),
        "min_flux_bq": args.min_flux_bq,
        "geometry": str(args.geometry),
        "notable_removed_or_rescaled": [
            row
            for row in rows
            if row["action"] == "removed_negligible_or_stable" or abs(float(row["scale"]) - 1.0) > 0.05
        ][:30],
    }
    summary_path = args.outdir / "source_fix_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")

    print(f"[OK] wrote {out_source}")
    print(f"[OK] wrote {corrections_csv}")
    print(f"[OK] wrote {removed_csv}")
    print(f"[OK] wrote {summary_path}")
    print(f"[INFO] old_total_activity_Bq={summary['old_total_activity_Bq']:.8e}")
    print(f"[INFO] new_total_activity_Bq={summary['new_total_activity_Bq']:.8e}")
    print(f"[INFO] source_blocks_removed={len(remove_names)}")


if __name__ == "__main__":
    main()
