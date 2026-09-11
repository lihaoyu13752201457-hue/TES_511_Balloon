#!/usr/bin/env python3
"""Audit active-CsI collar isotope smoke against delayed-risk anchors.

This is intentionally not a delayed transport.  It only converts the added
collar RP records from the existing isotope-store smoke into a day-15 source
activity estimate using the same div/mean-TT convention as the RPIP source
builder, then checks local Geant4 W1/511 decay-line yields.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs" / "reports" / "prompt511_active_csi_collar_20260620"
RUN_DIR = WORK / "runs" / "active_csi_collar_buildup_isotope_g1m_r2"
NUBASE = ROOT / "inputs" / "nubase" / "nubase_2020.txt"
CURRENT_CORRECTIONS = (
    ROOT
    / "stepwise_maintenance"
    / "step02_raw_background_simulation"
    / "source_snapshots_v3p5_centerfinger_fullstat_v2"
    / "groundstate_activity_corrections.csv"
)
W1_MODULE = (
    ROOT
    / "stepwise_maintenance"
    / "step03_delay_source"
    / "code"
    / "build_step03_rpip_production_map.py"
)
OUT_JSON = WORK / "prompt511_active_csi_collar_delay_risk_audit.json"
OUT_MD = WORK / "prompt511_active_csi_collar_delay_risk_audit.md"
OUT_CSV = WORK / "prompt511_active_csi_collar_delay_risk_audit_nuclides.csv"

ADDED_PREFIX = "CsI_Active_Shield_Prompt511_Collar_"
DAY15_S = 15.0 * 86400.0

ELEMENTS = [
    "",
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
]

VN_RE = re.compile(r"^\s*VN\s+(\S+)")
RP_RE = re.compile(r"^\s*RP\s+(\d+)\s+([-\d.]+)\s+([-\d.eE+]+)")
TT_RE = re.compile(r"^\s*TT\s+([-\d.eE+]+)")
TAG_RE = re.compile(r"Background_([^_]+)_", re.IGNORECASE)


def particle_from_name(path: Path) -> str:
    match = TAG_RE.search(path.name)
    return match.group(1).lower() if match else "unknown"


def nuclide_label(za: int) -> str:
    z, a = divmod(za, 1000)
    if 0 < z < len(ELEMENTS):
        return f"{ELEMENTS[z]}-{a}"
    return f"Z{z}-{a}"


def load_w1_module():
    spec = importlib.util.spec_from_file_location("step03_w1", W1_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {W1_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_dat(path: Path) -> tuple[float, list[dict[str, object]]]:
    tt = 0.0
    volume = ""
    rows: list[dict[str, object]] = []
    particle = particle_from_name(path)
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            if match := TT_RE.match(raw):
                tt = float(match.group(1))
                continue
            if match := VN_RE.match(raw):
                volume = match.group(1)
                continue
            if match := RP_RE.match(raw):
                za = int(match.group(1))
                rows.append(
                    {
                        "particle": particle,
                        "volume": volume,
                        "za": za,
                        "nuclide": nuclide_label(za),
                        "value": float(match.group(3)),
                    }
                )
    return tt, rows


def load_rp_smoke() -> tuple[dict[str, float], Counter[tuple[str, str, int]], Counter[int], float, float]:
    dat_files = sorted(RUN_DIR.glob("*.dat.inc1.dat"))
    files_by_particle = Counter(particle_from_name(path) for path in dat_files)
    tt_by_particle: dict[str, list[float]] = defaultdict(list)
    added_raw: Counter[tuple[str, str, int]] = Counter()
    all_raw_by_za: Counter[int] = Counter()
    added_raw_total = 0.0
    all_raw_total = 0.0

    for path in dat_files:
        tt, rows = parse_dat(path)
        particle = particle_from_name(path)
        if tt > 0.0:
            tt_by_particle[particle].append(tt)
        for row in rows:
            value = float(row["value"])
            za = int(row["za"])
            all_raw_by_za[za] += value
            all_raw_total += value
            if str(row["volume"]).startswith(ADDED_PREFIX):
                key = (str(row["particle"]), str(row["volume"]), za)
                added_raw[key] += value
                added_raw_total += value

    tt_mean_by_particle = {
        particle: sum(values) / len(values)
        for particle, values in tt_by_particle.items()
        if values
    }
    # Match makedecaysourcewithplot_rpip.py: div equals file count per tag
    # for this smoke (gamma uses auto, non-gamma has two replicas).
    div_by_particle = {particle: float(count) for particle, count in files_by_particle.items()}
    scaled: Counter[tuple[str, str, int]] = Counter()
    for (particle, volume, za), value in added_raw.items():
        scaled[(particle, volume, za)] += value / div_by_particle[particle]

    return tt_mean_by_particle, scaled, all_raw_by_za, added_raw_total, all_raw_total


def seconds_from_nubase(value: str, unit: str) -> float | None:
    if not value or "stbl" in value or "stable" in value:
        return None
    try:
        number = float(value.replace("#", ""))
    except ValueError:
        return None
    factors = {
        "ys": 1.0e-24,
        "zs": 1.0e-21,
        "as": 1.0e-18,
        "fs": 1.0e-15,
        "ps": 1.0e-12,
        "ns": 1.0e-9,
        "us": 1.0e-6,
        "ms": 1.0e-3,
        "s": 1.0,
        "m": 60.0,
        "h": 3600.0,
        "d": 86400.0,
        "y": 31557600.0,
        "ky": 31557600.0e3,
        "my": 31557600.0e6,
        "gy": 31557600.0e9,
        "ty": 31557600.0e12,
    }
    return number * factors.get(unit.lower(), 1.0)


def load_nubase(zas: set[int]) -> dict[int, dict[str, object]]:
    out: dict[int, dict[str, object]] = {}
    wanted = {(za // 1000, za % 1000): za for za in zas}
    with NUBASE.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            if not raw or raw.startswith("#") or len(raw) < 120:
                continue
            try:
                a = int(raw[0:3].strip())
                z_state = raw[4:8].strip()
                z = int(z_state[:3])
                state = z_state[3:] if len(z_state) > 3 else "0"
            except ValueError:
                continue
            if state not in ("", "0"):
                continue
            za = wanted.get((z, a))
            if za is None or za in out:
                continue
            half_life_raw = raw[69:78].strip()
            half_life_unit = raw[78:80].strip()
            out[za] = {
                "half_life_s": seconds_from_nubase(half_life_raw.lower(), half_life_unit.lower()),
                "half_life_raw": half_life_raw,
                "half_life_unit": half_life_unit,
                "decay_modes": raw[119:209].strip(),
            }
    return out


def activity_after_day15(scaled_yield: float, tt_s: float, half_life_s: float | None) -> float:
    if not half_life_s or not math.isfinite(half_life_s) or half_life_s <= 0.0 or tt_s <= 0.0:
        return 0.0
    lam = math.log(2.0) / half_life_s
    production_rate = scaled_yield / tt_s
    return production_rate * (1.0 - math.exp(-lam * DAY15_S))


def load_current_anchor() -> dict[str, float]:
    total = 0.0
    csi_total = 0.0
    i128_total = 0.0
    cs134_total = 0.0
    with CURRENT_CORRECTIONS.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                activity = float(row["new_groundstate_activity_Bq"])
                za = int(row["ZA"])
            except (KeyError, ValueError):
                continue
            total += activity
            if str(row.get("VN", "")).startswith("CsI_"):
                csi_total += activity
            if za == 53128:
                i128_total += activity
            if za == 55134:
                cs134_total += activity
    return {
        "total_activity_Bq": total,
        "csi_activity_Bq": csi_total,
        "i128_activity_Bq": i128_total,
        "cs134_activity_Bq": cs134_total,
    }


def main() -> int:
    tt_by_particle, added_scaled, all_raw_by_za, added_raw_total, all_raw_total = load_rp_smoke()
    nubase = load_nubase({za for _, _, za in added_scaled})
    current_anchor = load_current_anchor()
    w1_module = load_w1_module()

    by_za: dict[int, dict[str, object]] = {}
    by_particle_za: Counter[tuple[str, int]] = Counter()
    by_volume_za: Counter[tuple[str, int]] = Counter()
    for (particle, volume, za), scaled_yield in added_scaled.items():
        by_particle_za[(particle, za)] += scaled_yield
        by_volume_za[(volume, za)] += scaled_yield
        row = by_za.setdefault(
            za,
            {
                "ZA": za,
                "nuclide": nuclide_label(za),
                "scaled_yield": 0.0,
                "day15_activity_Bq": 0.0,
            },
        )
        row["scaled_yield"] = float(row["scaled_yield"]) + scaled_yield
        hl = nubase.get(za, {}).get("half_life_s")
        row["day15_activity_Bq"] = float(row["day15_activity_Bq"]) + activity_after_day15(
            scaled_yield=scaled_yield,
            tt_s=tt_by_particle.get(particle, 0.0),
            half_life_s=float(hl) if hl is not None else None,
        )

    nuclide_rows = []
    for za, row in by_za.items():
        w1_lines = [
            {"kind": kind, "energy_keV": energy, "yield_per_decay": yield_per_decay}
            for kind, energy, yield_per_decay in w1_module.w1_decay_line_yields_for_za(za)
        ]
        w1_photons_per_decay = sum(float(item["yield_per_decay"]) for item in w1_lines)
        day15_activity = float(row["day15_activity_Bq"])
        nuclide_rows.append(
            {
                **row,
                "half_life_s": nubase.get(za, {}).get("half_life_s"),
                "half_life_raw": nubase.get(za, {}).get("half_life_raw", ""),
                "half_life_unit": nubase.get(za, {}).get("half_life_unit", ""),
                "decay_modes": nubase.get(za, {}).get("decay_modes", ""),
                "W1_photons_per_decay": w1_photons_per_decay,
                "W1_line_rate_Bq_equiv": day15_activity * w1_photons_per_decay,
                "W1_decay_lines": w1_lines,
            }
        )
    nuclide_rows.sort(key=lambda item: float(item["day15_activity_Bq"]), reverse=True)

    added_day15_activity = sum(float(row["day15_activity_Bq"]) for row in nuclide_rows)
    added_w1_rate = sum(float(row["W1_line_rate_Bq_equiv"]) for row in nuclide_rows)
    summary = {
        "status": "PASS_ACTIVE_CSI_COLLAR_DELAY_RISK_AUDIT_SMOKE_ONLY",
        "claim_level": "activity-and-decay-line audit from existing isotope-store smoke; not delayed transport or day-20 rate authority",
        "run_dir": str(RUN_DIR.relative_to(ROOT)),
        "method": {
            "rp_division": "scaled RP yield divides each particle tag by its DAT file count, matching makedecaysourcewithplot_rpip.py div/mean-TT convention for this smoke",
            "exposure_days": 15.0,
            "half_lives": str(NUBASE.relative_to(ROOT)),
            "w1_decay_lines": str(W1_MODULE.relative_to(ROOT)),
        },
        "raw_smoke": {
            "added_raw_total": added_raw_total,
            "all_raw_total": all_raw_total,
            "added_fraction_raw": added_raw_total / all_raw_total if all_raw_total else None,
        },
        "added_collar": {
            "day15_activity_Bq_estimate": added_day15_activity,
            "W1_line_rate_Bq_equiv_estimate": added_w1_rate,
            "nuclides": nuclide_rows,
        },
        "current_v3p5_anchor": current_anchor,
        "ratios_to_current_v3p5_anchor": {
            "added_activity_over_current_total": added_day15_activity / current_anchor["total_activity_Bq"],
            "added_activity_over_current_csi": added_day15_activity / current_anchor["csi_activity_Bq"],
            "added_i128_over_current_i128": (
                next((float(row["day15_activity_Bq"]) for row in nuclide_rows if row["ZA"] == 53128), 0.0)
                / current_anchor["i128_activity_Bq"]
            ),
            "added_cs134_over_current_cs134": (
                next((float(row["day15_activity_Bq"]) for row in nuclide_rows if row["ZA"] == 55134), 0.0)
                / current_anchor["cs134_activity_Bq"]
            ),
        },
        "current_w2_delayed_nuclide_context": {
            "source": "outputs/reports/v3p5_fullstat_performance_w2_closure_fullstat_v2_exactpos_20260613/tables/w2_delayed_nuclides.csv",
            "top_primary_nuclides": ["Cu64", "Cu62", "Cu61"],
            "interpretation": "Existing W2 delayed 511 table is Cu-dominated; added CsI collar isotope activity is therefore a risk screen, not direct delayed-rate evidence.",
        },
    }

    OUT_JSON.write_text(
        json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "ZA",
            "nuclide",
            "scaled_yield",
            "day15_activity_Bq",
            "half_life_s",
            "half_life_raw",
            "half_life_unit",
            "decay_modes",
            "W1_photons_per_decay",
            "W1_line_rate_Bq_equiv",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(nuclide_rows)

    lines = [
        "# Active-CsI Collar Delay-Risk Audit",
        "",
        "Status: `PASS_ACTIVE_CSI_COLLAR_DELAY_RISK_AUDIT_SMOKE_ONLY`",
        "",
        "This is an activity/decay-line audit of the existing isotope-store smoke. It is not a delayed-source rebuild, delayed transport, day-20 rate, or sensitivity authority.",
        "",
        "## Added Collar Activity Estimate",
        "",
        f"- added raw RP value: `{added_raw_total:.6g}` / all-volume `{all_raw_total:.6g}` (`{added_raw_total / all_raw_total:.3%}`)",
        f"- day-15 added-collar activity estimate: `{added_day15_activity:.6g} Bq`",
        f"- current v3p5 fullstat ground-state fixed source total: `{current_anchor['total_activity_Bq']:.6g} Bq`",
        f"- ratio to current total source activity: `{summary['ratios_to_current_v3p5_anchor']['added_activity_over_current_total']:.3%}`",
        f"- ratio to current CsI source activity: `{summary['ratios_to_current_v3p5_anchor']['added_activity_over_current_csi']:.3%}`",
        "",
        "## Added Nuclides",
        "",
        "| ZA | nuclide | scaled yield | day-15 Bq est. | half-life | W1 photons/decay | W1 line Bq-equiv | decay modes |",
        "|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in nuclide_rows:
        half_life = f"{row['half_life_raw']} {row['half_life_unit']}".strip()
        lines.append(
            f"| {row['ZA']} | {row['nuclide']} | {float(row['scaled_yield']):.6g} | "
            f"{float(row['day15_activity_Bq']):.6g} | {half_life} | "
            f"{float(row['W1_photons_per_decay']):.6g} | "
            f"{float(row['W1_line_rate_Bq_equiv']):.6g} | {row['decay_modes']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- The added collar activity estimate is small relative to the current v3p5 fixed source in this smoke normalization.",
        "- The added inventory is dominated by Cs/I activation products, while the existing W2 delayed 511 table is Cu64/Cu62/Cu61 dominated.",
        "- This supports carrying the active-CsI collar as a low-delay-risk prompt-repair candidate, but it still does not prove a final delayed rate.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(json.dumps({"json": str(OUT_JSON), "md": str(OUT_MD), "csv": str(OUT_CSV)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
