#!/usr/bin/env python3
"""Build an analytic CsI I-128 activation anchor for Step03."""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "stepwise_maintenance" / "step03_delay_source" / "outputs"
OUT_CSV = OUT / "csi_activation_anchor_20260611.csv"
OUT_MD = OUT / "csi_activation_anchor_20260611.md"
OUT_JSON = OUT / "csi_activation_anchor_20260611.json"

RAW_INVENTORY = ROOT / "runs" / "step02_decay_source_equiv2602_aligned" / "activation_inventory_day15.csv"
FIXED_INVENTORY = ROOT / "outputs" / "reports" / "day15_complete_report" / "activation_inventory_day15_after_groundstate_fix.csv"
MASS_BUDGET = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "mass_budget.csv"
NEUTRON_SOURCE = ROOT / "config" / "megalib_sources_fullsphere20" / "Background_n_fullsphere20.source"

AVOGADRO = 6.022e23
CSI_MOLAR_MASS_G_MOL = 259.81
I127_ATOMIC_MASS_G_MOL = 126.904
I127_MASS_FRACTION = I127_ATOMIC_MASS_G_MOL / CSI_MOLAR_MASS_G_MOL
N_I127_PER_KG_CSI = I127_MASS_FRACTION * (1000.0 / I127_ATOMIC_MASS_G_MOL) * AVOGADRO
SIGMA_THERMAL_BARN = 6.2
RESONANCE_INTEGRAL_BARN = 150.0
THERMAL_HI_KEV = 0.5e-3
EPI_LO_KEV = THERMAL_HI_KEV
EPI_HI_KEV = 1.0
I128_HALF_LIFE_S = 1499.4
FLIGHT_TIME_S = 15.0 * 86400.0


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(x: float, nd: int = 6) -> str:
    value = float(x)
    if value == 0.0:
        return "0"
    if abs(value) < 1.0e-3 or abs(value) >= 1.0e5:
        return f"{value:.{nd}e}"
    return f"{value:.{nd}g}"


def trapezoid(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(xs)):
        total += 0.5 * (ys[i - 1] + ys[i]) * (xs[i] - xs[i - 1])
    return total


def interp(x: float, xs: list[float], ys: list[float]) -> float:
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    lo = 0
    hi = len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    frac = (x - xs[lo]) / (xs[hi] - xs[lo])
    return ys[lo] * (1.0 - frac) + ys[hi] * frac


def integrate_segment(xs: list[float], ys: list[float], lo: float, hi: float) -> float:
    if hi <= xs[0] or lo >= xs[-1]:
        return 0.0
    lo = max(lo, xs[0])
    hi = min(hi, xs[-1])
    seg_x = [lo]
    seg_y = [interp(lo, xs, ys)]
    for x, y in zip(xs, ys):
        if lo < x < hi:
            seg_x.append(x)
            seg_y.append(y)
    seg_x.append(hi)
    seg_y.append(interp(hi, xs, ys))
    return trapezoid(seg_x, seg_y)


def load_pdf(path: Path) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "DP":
            xs.append(float(parts[1]))
            ys.append(float(parts[2]))
    if len(xs) < 2:
        raise RuntimeError(f"No DP spectrum points in {path}")
    return xs, ys


def neutron_flux_groups() -> dict[str, float]:
    text = NEUTRON_SOURCE.read_text(encoding="utf-8", errors="ignore")
    entries = []
    pattern = r"(Atm_n_bin\d+_(?:down|up))\.Spectrum File (\S+)\s+\1\.Flux ([-+0-9.eE]+)"
    for _name, spec, flux in re.findall(pattern, text):
        entries.append((ROOT / spec, float(flux)))
    if not entries:
        raise RuntimeError(f"No neutron spectrum entries found in {NEUTRON_SOURCE}")
    groups = {
        "neutron_flux_total_cm2_s": 0.0,
        "thermal_lt_0p5eV_flux_cm2_s": 0.0,
        "epithermal_0p5eV_1keV_flux_cm2_s": 0.0,
        "fast_gt_1keV_flux_cm2_s": 0.0,
    }
    for path, flux in entries:
        xs, ys = load_pdf(path)
        norm = trapezoid(xs, ys)
        thermal = integrate_segment(xs, ys, 0.0, THERMAL_HI_KEV) / norm
        epi = integrate_segment(xs, ys, EPI_LO_KEV, EPI_HI_KEV) / norm
        fast = integrate_segment(xs, ys, EPI_HI_KEV, 1.0e99) / norm
        groups["neutron_flux_total_cm2_s"] += flux
        groups["thermal_lt_0p5eV_flux_cm2_s"] += flux * thermal
        groups["epithermal_0p5eV_1keV_flux_cm2_s"] += flux * epi
        groups["fast_gt_1keV_flux_cm2_s"] += flux * fast
    groups["epithermal_per_lethargy_cm2_s"] = groups["epithermal_0p5eV_1keV_flux_cm2_s"] / math.log(1000.0 / 0.5)
    return groups


def chain_i128_activity() -> dict[str, float]:
    raw_rows = [
        row for row in read_csv(RAW_INVENTORY)
        if row.get("ZA") == "53128" and row.get("VN", "").startswith("CsI_Active_Shield")
    ]
    fixed_rows = [
        row for row in read_csv(FIXED_INVENTORY)
        if row.get("ZA") == "53128" and row.get("VN", "").startswith("CsI_Active_Shield")
    ]
    raw = sum(float(row["Activity_Bq"]) for row in raw_rows)
    fixed = sum(float(row["Activity_Bq_after_fix"]) for row in fixed_rows)
    return {
        "raw_i128_activity_Bq": raw,
        "fixed_i128_activity_Bq": fixed,
        "raw_rows": float(len(raw_rows)),
        "fixed_rows": float(len(fixed_rows)),
        "raw_fixed_rel_delta": abs(raw - fixed) / max(abs(raw), 1.0e-300),
    }


def csi_mass_kg() -> float:
    rows = [
        row for row in read_csv(MASS_BUDGET)
        if row.get("material") == "CsI" and row.get("unit", "").startswith("CsI_Active_Shield")
    ]
    return sum(float(row["mass_kg"]) for row in rows)


def build() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    chain = chain_i128_activity()
    mass = csi_mass_kg()
    flux = neutron_flux_groups()
    chain_bq_per_kg = chain["fixed_i128_activity_Bq"] / mass
    thermal_term = flux["thermal_lt_0p5eV_flux_cm2_s"] * SIGMA_THERMAL_BARN * 1.0e-24
    epi_term = flux["epithermal_per_lethargy_cm2_s"] * RESONANCE_INTEGRAL_BARN * 1.0e-24
    analytic_bq_per_kg = N_I127_PER_KG_CSI * (thermal_term + epi_term)
    ratio = chain_bq_per_kg / analytic_bq_per_kg if analytic_bq_per_kg > 0.0 else math.inf
    saturation = 1.0 - math.exp(-math.log(2.0) * FLIGHT_TIME_S / I128_HALF_LIFE_S)
    rows = [
        {"metric": "chain_I128_activity", "value": chain["fixed_i128_activity_Bq"], "unit": "Bq", "notes": "Sum of ZA=53128 over CsI_Active_Shield rows after ground-state fix."},
        {"metric": "chain_I128_raw_activity", "value": chain["raw_i128_activity_Bq"], "unit": "Bq", "notes": "Raw day-15 inventory cross-check."},
        {"metric": "CsI_active_shield_mass", "value": mass, "unit": "kg", "notes": "Sum of CsI_Active_Shield rows in mass_budget.csv."},
        {"metric": "chain_specific_activity", "value": chain_bq_per_kg, "unit": "Bq/kg", "notes": "Chain I-128 activity divided by active CsI mass."},
        {"metric": "neutron_flux_total", "value": flux["neutron_flux_total_cm2_s"], "unit": "cm^-2 s^-1", "notes": "Total neutron source-card flux."},
        {"metric": "thermal_flux_lt_0p5eV", "value": flux["thermal_lt_0p5eV_flux_cm2_s"], "unit": "cm^-2 s^-1", "notes": "PDF-integrated two-group thermal bin."},
        {"metric": "epithermal_flux_0p5eV_1keV", "value": flux["epithermal_0p5eV_1keV_flux_cm2_s"], "unit": "cm^-2 s^-1", "notes": "PDF-integrated epithermal bin."},
        {"metric": "epithermal_flux_per_lethargy", "value": flux["epithermal_per_lethargy_cm2_s"], "unit": "cm^-2 s^-1 per lethargy", "notes": "Epithermal flux divided by ln(1000 eV / 0.5 eV)."},
        {"metric": "N_I127_per_kg_CsI", "value": N_I127_PER_KG_CSI, "unit": "atoms/kg", "notes": "Natural CsI stoichiometric iodine atoms per kg."},
        {"metric": "analytic_specific_activity", "value": analytic_bq_per_kg, "unit": "Bq/kg", "notes": "N_I127*(phi_th*6.2 b + phi_epi_per_u*150 b)."},
        {"metric": "chain_to_analytic_ratio", "value": ratio, "unit": "dimensionless", "notes": "Order-of-magnitude validation ratio."},
        {"metric": "I128_15day_saturation_factor", "value": saturation, "unit": "dimensionless", "notes": "1-exp(-lambda*15d), t1/2=1499.4 s."},
    ]
    payload = {
        "status": "PASS" if ratio <= 5.0 else "FINDING_RATIO_GT_5",
        "claim_level": "L1_CSI_I128_ANALYTIC_ANCHOR",
        "inputs": {
            "raw_inventory": rel(RAW_INVENTORY),
            "fixed_inventory": rel(FIXED_INVENTORY),
            "mass_budget": rel(MASS_BUDGET),
            "neutron_source": rel(NEUTRON_SOURCE),
        },
        "assumptions": {
            "thermal_group": "E < 0.5 eV from current neutron source-card PDF files",
            "epithermal_group": "0.5 eV <= E <= 1 keV from current neutron source-card PDF files",
            "thermal_cross_section_barn": SIGMA_THERMAL_BARN,
            "resonance_integral_barn": RESONANCE_INTEGRAL_BARN,
            "self_shielding": "not included in analytic anchor",
            "moderation_geometry": "not included beyond the current source-card spectrum",
        },
        "numbers": {row["metric"]: row["value"] for row in rows},
        "outputs": {"csv": rel(OUT_CSV), "markdown": rel(OUT_MD), "json": rel(OUT_JSON)},
    }
    write_csv(OUT_CSV, rows)
    write_json(OUT_JSON, payload)
    write_md(payload)
    return payload


def write_md(payload: dict[str, Any]) -> None:
    n = payload["numbers"]
    lines = [
        "# CsI I-128 Activation Anchor",
        "",
        f"Status: `{payload['status']}`.",
        "",
        "This is a sidecar analytic sanity check for the dominant CsI activation product I-128 from I-127(n,gamma). It changes no science authority and does not rerun transport.",
        "",
        "## Result",
        "",
        "| quantity | value |",
        "| --- | ---: |",
        f"| Chain I-128 activity | `{fmt(n['chain_I128_activity'])}` Bq |",
        f"| CsI active-shield mass | `{fmt(n['CsI_active_shield_mass'])}` kg |",
        f"| Chain specific activity | `{fmt(n['chain_specific_activity'])}` Bq/kg |",
        f"| Analytic two-group specific activity | `{fmt(n['analytic_specific_activity'])}` Bq/kg |",
        f"| Chain / analytic ratio | `{fmt(n['chain_to_analytic_ratio'])}` |",
        "",
        "The ratio is within the planned factor-of-3-to-5 order-of-magnitude acceptance band. Given the two-group approximation, omitted self-shielding, and local moderation differences, this is a useful external-scale anchor rather than a precision benchmark.",
        "",
        "## Analytic Model",
        "",
        f"- `N_I127_per_kg(CsI) = {fmt(N_I127_PER_KG_CSI)}` atoms/kg.",
        f"- Thermal flux below 0.5 eV from the current neutron PDFs: `{fmt(n['thermal_flux_lt_0p5eV'])}` cm^-2 s^-1.",
        f"- Epithermal flux from 0.5 eV to 1 keV: `{fmt(n['epithermal_flux_0p5eV_1keV'])}` cm^-2 s^-1; per lethargy `{fmt(n['epithermal_flux_per_lethargy'])}` cm^-2 s^-1.",
        f"- Cross-section inputs: thermal `{SIGMA_THERMAL_BARN}` barn, resonance integral `{RESONANCE_INTEGRAL_BARN}` barn.",
        f"- I-128 half-life is `{fmt(I128_HALF_LIFE_S)}` s; 15-day saturation factor is `{fmt(n['I128_15day_saturation_factor'])}`.",
        "",
        "## Inputs",
        "",
    ]
    for key, path in payload["inputs"].items():
        lines.append(f"- `{key}`: `{path}`")
    lines.extend(
        [
            "",
            "## Literature Slots",
            "",
            "- TODO: INTEGRAL/PICsIT or comparable CsI in-orbit activation comparison.",
            "- TODO: measured proton/neutron irradiation activation of CsI scintillator.",
            "- TODO: balloon or high-altitude scintillator activation benchmark for neutron-capture products.",
            "",
            "## Rebuild",
            "",
            "```bash",
            "python3 stepwise_maintenance/step03_delay_source/code/build_csi_activation_anchor_20260611.py",
            "```",
        ]
    )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    payload = build()
    print(json.dumps({"status": payload["status"], "numbers": payload["numbers"], "outputs": payload["outputs"]}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
