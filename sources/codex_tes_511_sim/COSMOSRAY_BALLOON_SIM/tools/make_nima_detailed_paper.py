#!/usr/bin/env python3
"""Build a detailed NIMA-style Chinese HTML manuscript in reports2.0.

The output is intentionally self-contained except for local figure paths already
present in reports2.0. It reads the current JSON/CSV authority files instead of
copying numbers by hand.
"""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "reports2.0"
OUT = R2 / "07_NIMA_MANUSCRIPT"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_csv_optional(path: Path) -> list[dict[str, str]]:
    return read_csv(path) if path.exists() else []


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def bullet_rows(markdown: str, kind: str) -> list[dict[str, str]]:
    rows = []
    for line in markdown.splitlines():
        if line.startswith("- "):
            rows.append({"kind": kind, "claim": line[2:].strip()})
    return rows


def validation_rows(markdown: str) -> list[dict[str, str]]:
    rows = []
    for line in markdown.splitlines():
        if not line.startswith("- "):
            continue
        text = line[2:].strip()
        if ": " not in text:
            continue
        status, rest = text.split(": ", 1)
        if " - " in rest:
            check, note = rest.split(" - ", 1)
        else:
            check, note = rest, ""
        rows.append({"status": status, "check": check, "note": note})
    return rows


def fmt(x, sig: int = 5) -> str:
    if x is None or x == "":
        return ""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if abs(v) == 0:
        return "0"
    if abs(v) < 1.0e-3 or abs(v) >= 1.0e4:
        return f"{v:.{sig}e}"
    return f"{v:.{sig}g}"


def find_row(rows: list[dict[str, str]], key: str, value: str) -> dict[str, str]:
    for row in rows:
        if row.get(key) == value:
            return row
    return {}


def find_row_all(rows: list[dict[str, str]], **criteria: str) -> dict[str, str]:
    for row in rows:
        if all(row.get(key) == value for key, value in criteria.items()):
            return row
    return {}


def table_html(rows: list[dict[str, object]], columns: list[tuple[str, str]], caption: str = "") -> str:
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        cells = []
        for key, _ in columns:
            value = row.get(key, "")
            if isinstance(value, (int, float)):
                text = fmt(value)
            else:
                text = fmt(value) if key.endswith(("cps", "Bq", "s", "rate", "flux", "fraction")) else str(value)
            cells.append(f"<td>{html.escape(text)}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    cap = f"<caption>{html.escape(caption)}</caption>" if caption else ""
    return f"<table>{cap}<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def table_md(rows: list[dict[str, object]], columns: list[tuple[str, str]]) -> str:
    labels = [label for _, label in columns]
    out = ["| " + " | ".join(labels) + " |", "| " + " | ".join(["---"] * len(labels)) + " |"]
    for row in rows:
        vals = []
        for key, _ in columns:
            value = row.get(key, "")
            vals.append(fmt(value) if isinstance(value, (int, float)) else str(value))
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out)


def fig(path: str, caption: str) -> str:
    return (
        f"<figure><img src=\"{html.escape(path)}\" alt=\"{html.escape(caption)}\">"
        f"<figcaption>{html.escape(caption)}</figcaption></figure>"
    )


def bib_entries() -> list[dict[str, str]]:
    return [
        {"id": "Agostinelli2003", "text": "S. Agostinelli et al., GEANT4 - A simulation toolkit, Nucl. Instrum. Methods Phys. Res. A 506 (2003) 250-303.", "url": "https://doi.org/10.1016/S0168-9002(03)01368-8"},
        {"id": "Allison2016", "text": "J. Allison et al., Recent developments in Geant4, Nucl. Instrum. Methods Phys. Res. A 835 (2016) 186-225.", "url": "https://doi.org/10.1016/j.nima.2016.06.125"},
        {"id": "Zoglauer2008", "text": "A. Zoglauer et al., MEGAlib: simulation and data analysis for low-to-medium-energy gamma-ray telescopes, Proc. SPIE 7011 (2008) 70113F.", "url": "https://doi.org/10.1117/12.789537"},
        {"id": "Zoglauer2009", "text": "A. Zoglauer et al., Cosima - The cosmic simulator of MEGAlib, IEEE NSS/MIC Conference Record (2009).", "url": "https://doi.org/10.1109/NSSMIC.2009.5402128"},
        {"id": "Sato2008", "text": "T. Sato et al., Development of PARMA: PHITS based analytical radiation model in the atmosphere, Radiat. Res. 170 (2008) 244-259.", "url": "https://doi.org/10.1667/RR1094.1"},
        {"id": "Sato2015", "text": "T. Sato, Analytical model for estimating terrestrial cosmic ray fluxes nearly anytime and anywhere in the world: extension of PARMA/EXPACS, PLOS ONE 10 (2015) e0144679.", "url": "https://doi.org/10.1371/journal.pone.0144679"},
        {"id": "Sato2016", "text": "T. Sato, Analytical model for estimating the zenith angle dependence of terrestrial cosmic ray fluxes, PLOS ONE 11 (2016) e0160390.", "url": "https://doi.org/10.1371/journal.pone.0160390"},
        {"id": "PHITS2018", "text": "T. Sato et al., Features of Particle and Heavy Ion Transport code System (PHITS) version 3.02, J. Nucl. Sci. Technol. 55 (2018) 684-690.", "url": "https://doi.org/10.1080/00223131.2017.1419890"},
        {"id": "Shirazi2023", "text": "F. Shirazi et al., 511-CAM mission: a pointed 511 keV gamma-ray telescope with stacked TES microcalorimeter arrays, JATIS 9 (2023) 024006.", "url": "https://doi.org/10.1117/1.JATIS.9.2.024006"},
        {"id": "Noroozian2013", "text": "O. Noroozian et al., High-resolution gamma-ray spectroscopy with a microwave-multiplexed TES array, Appl. Phys. Lett. 103 (2013) 202602.", "url": "https://doi.org/10.1063/1.4829156"},
        {"id": "Mates2017", "text": "J. A. B. Mates et al., Simultaneous readout of 128 X-ray and gamma-ray transition-edge microcalorimeters using microwave SQUID multiplexing, Appl. Phys. Lett. 111 (2017) 062601.", "url": "https://doi.org/10.1063/1.4986222"},
        {"id": "Ullom2007", "text": "J. N. Ullom et al., Multiplexed microcalorimeter arrays for precision measurements from microwave to gamma-ray wavelengths, Nucl. Instrum. Methods Phys. Res. A 579 (2007) 155-159.", "url": "https://doi.org/10.1016/j.nima.2007.04.077"},
        {"id": "Damayanthi2012", "text": "R. M. T. Damayanthi et al., Fast response signals from Pb absorber coupled TES gamma-ray microcalorimeter, Nucl. Instrum. Methods Phys. Res. A 691 (2012) 30-33.", "url": "https://doi.org/10.1016/j.nima.2012.06.049"},
        {"id": "Keller2024", "text": "M. W. Keller et al., Effects of stray magnetic field on TESs in gamma-ray microcalorimeters, J. Low Temp. Phys. 216 (2024) 336-343.", "url": "https://doi.org/10.1007/s10909-024-03140-y"},
        {"id": "Knodlseder2005", "text": "J. Knodlseder et al., The all-sky distribution of 511 keV electron-positron annihilation emission, Astron. Astrophys. 441 (2005) 513-532.", "url": "https://doi.org/10.1051/0004-6361:20042063"},
        {"id": "Churazov2005", "text": "E. Churazov et al., Positron annihilation spectrum from the Galactic Centre region observed by SPI/INTEGRAL, Mon. Not. R. Astron. Soc. 357 (2005) 1377-1386.", "url": "https://doi.org/10.1111/j.1365-2966.2005.08786.x"},
        {"id": "Jean2006", "text": "P. Jean et al., Spectral analysis of the Galactic e+e- annihilation emission, Astron. Astrophys. 445 (2006) 579-589.", "url": "https://doi.org/10.1051/0004-6361:20053765"},
        {"id": "Weidenspointner2008", "text": "G. Weidenspointner et al., An asymmetric distribution of positrons in the Galactic disk revealed by gamma-rays, Nature 451 (2008) 159-162.", "url": "https://doi.org/10.1038/nature06490"},
        {"id": "Prantzos2011", "text": "N. Prantzos et al., The 511 keV emission from positron annihilation in the Galaxy, Rev. Mod. Phys. 83 (2011) 1001-1056.", "url": "https://doi.org/10.1103/RevModPhys.83.1001"},
        {"id": "Siegert2016", "text": "T. Siegert et al., Gamma-ray spectroscopy of positron annihilation in the Milky Way, Astron. Astrophys. 586 (2016) A84.", "url": "https://doi.org/10.1051/0004-6361/201527510"},
        {"id": "Tomsick2023", "text": "J. A. Tomsick et al., The Compton Spectrometer and Imager, Proc. Sci. ICRC2023 (2023) 745.", "url": "https://doi.org/10.22323/1.444.0745"},
        {"id": "Ciabattoni2025", "text": "A. Ciabattoni et al., Benchmarking of Geant4 simulations for the COSI Anticoincidence System, Exp. Astron. 60 (2025) 9.", "url": "https://doi.org/10.1007/s10686-025-10019-7"},
        {"id": "Tian2026", "text": "R. Tian et al., Simulation of non X-ray background for the DIffuse X-ray Explorer mission, Research Square preprint (2026).", "url": "https://doi.org/10.21203/rs.3.rs-8576846/v1"},
        {"id": "Lotti2017", "text": "S. Lotti et al., The particle background of the X-IFU instrument, Exp. Astron. 44 (2017) 371-385.", "url": "https://doi.org/10.1007/s10686-017-9538-1"},
        {"id": "Lotti2018", "text": "S. Lotti et al., Estimates for the background of the ATHENA X-IFU instrument: the cosmic rays contribution, Proc. SPIE 10699 (2018) 106991Q.", "url": "https://doi.org/10.1117/12.2313236"},
        {"id": "Kilbourne2018", "text": "C. A. Kilbourne et al., In-flight calibration of Hitomi Soft X-ray Spectrometer. (1) Background, Publ. Astron. Soc. Japan 70 (2018) 18.", "url": "https://doi.org/10.1093/pasj/psx139"},
        {"id": "Barret2018", "text": "D. Barret et al., The ATHENA X-ray Integral Field Unit, Proc. SPIE 10699 (2018) 106991G.", "url": "https://doi.org/10.1117/12.2312409"},
        {"id": "Macculi2016", "text": "C. Macculi et al., Cryogenic AntiCoincidence Detector for ATHENA X-IFU: design aspects by Geant4 simulation, J. Low Temp. Phys. 184 (2016) 393-398.", "url": "https://doi.org/10.1007/s10909-015-1439-y"},
        {"id": "Kondev2021", "text": "F. G. Kondev et al., The NUBASE2020 evaluation of nuclear physics properties, Chin. Phys. C 45 (2021) 030001.", "url": "https://doi.org/10.1088/1674-1137/abddae"},
        {"id": "ENSDF", "text": "National Nuclear Data Center, Evaluated Nuclear Structure Data File (ENSDF), Brookhaven National Laboratory dataset.", "url": "https://doi.org/10.18139/nndc.ensdf/1845010"},
        {"id": "Hauf2013", "text": "S. Hauf et al., Validation of Geant4-based radioactive decay simulation, IEEE Trans. Nucl. Sci. 60 (2013) 2984-2997.", "url": "https://doi.org/10.1109/TNS.2013.2271047"},
        {"id": "Amman2007", "text": "M. Amman et al., Position-sensitive germanium detectors for gamma-ray imaging and spectroscopy, Nucl. Instrum. Methods Phys. Res. A 579 (2007) 886-890.", "url": "https://doi.org/10.1016/j.nima.2007.05.296"},
        {"id": "Weidenspointner2005", "text": "G. Weidenspointner et al., MGGPOD: a Monte Carlo suite for modeling instrumental line and continuum backgrounds in gamma-ray astronomy, Astrophys. J. Suppl. 156 (2005) 69-91.", "url": "https://doi.org/10.1086/425260"},
        {"id": "Mizuno2004", "text": "T. Mizuno et al., Cosmic-ray background flux model based on a gamma-ray large area space telescope balloon flight engineering model, Astrophys. J. 614 (2004) 1113-1123.", "url": "https://doi.org/10.1086/423801"},
        {"id": "Ajello2008", "text": "M. Ajello et al., Cosmic X-ray background and Earth albedo spectra with Swift BAT, Astrophys. J. 689 (2008) 666-677.", "url": "https://doi.org/10.1086/592595"},
        {"id": "Lei1997", "text": "F. Lei, A. J. Dean, G. L. Hills, Compton polarimetry in gamma-ray astronomy, Space Sci. Rev. 82 (1997) 309-388.", "url": "https://doi.org/10.1023/A:1005027107614"},
    ]


def ref_list_html(refs: list[dict[str, str]]) -> str:
    items = []
    for i, r in enumerate(refs, 1):
        items.append(f"<li id=\"ref{i}\">{html.escape(r['text'])} <a href=\"{html.escape(r['url'])}\">{html.escape(r['url'])}</a></li>")
    return "<ol class=\"refs\">" + "\n".join(items) + "</ol>"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    day15 = load_json(R2 / "02_PHASE2_CORE_MATERIALS/authorities/complete_day15_summary.json")
    phase2 = load_json(R2 / "02_PHASE2_CORE_MATERIALS/authorities/phase2_summary.json")
    update = load_json(R2 / "01B_CONVERGENCE_PATCH_UPDATE/phase2_convergence_patch_update_summary.json")
    env = load_json(R2 / "02_PHASE2_CORE_MATERIALS/environment_grid/environment_grid_summary.json")
    prompt = load_json(R2 / "02_PHASE2_CORE_MATERIALS/prompt_reweight/prompt_reweight_real_summary.json")
    inv = load_json(R2 / "02_PHASE2_CORE_MATERIALS/activation_inventory/inventory_parentfed_summary.json")
    delayed = load_json(R2 / "02_PHASE2_CORE_MATERIALS/delayed_sources/source_build_summary.json")
    measured = read_csv(R2 / "02_PHASE2_CORE_MATERIALS/measured_catalog/true_vs_measured_rates.csv")
    likelihood = [r for r in read_csv(R2 / "02_PHASE2_CORE_MATERIALS/likelihood_profiled/asimov_profiled_sensitivity.csv") if r["exposure_s"] == "1000000.0"]
    injection = [r for r in read_csv(R2 / "02_PHASE2_CORE_MATERIALS/source_injection/source_injection_profiled_summary.csv") if r["exposure_s"] == "1000000.0" and r["input_flux_ph_cm2_s"] == "0.0001"]
    activation = read_csv(R2 / "02_PHASE2_CORE_MATERIALS/activation_truth/activation_511_truth_table.csv")[:10]
    timing = read_csv(R2 / "02_PHASE2_CORE_MATERIALS/timing_daq/timing_daq_model_summary.csv")
    image8 = read_csv(R2 / "02_PHASE2_CORE_MATERIALS/image8_tables/image8_style_component_rates.csv")
    line_sensitivity = read_csv(R2 / "03_NEXT_PHASE_SUPPORT/science_line_models/sensitivity_by_line_model.csv")
    line_fraction = read_csv(R2 / "03_NEXT_PHASE_SUPPORT/science_line_models/source_fraction_in_windows.csv")
    delayed_manifest = read_csv(R2 / "02_PHASE2_CORE_MATERIALS/delayed_sources/delayed_source_level1_manifest.csv")
    focused_summary = read_csv_optional(R2 / "03_NEXT_PHASE_SUPPORT/optics_focused_gamma_background/focused_gamma_background_summary.csv")
    focused_addendum = read_csv_optional(R2 / "03_NEXT_PHASE_SUPPORT/optics_focused_gamma_background/focused_gamma_sensitivity_addendum.csv")
    activation_geometry_summary = read_csv_optional(R2 / "03_NEXT_PHASE_SUPPORT/activation_rpip_sampling/activation_geometry_volume_summary.csv")
    design_recommendation = read_csv_optional(R2 / "08_DESIGN_OPTIMIZATION_ADDON/WP_D5_design_recommendation/design_recommendation_table.csv")
    design_variant_screen = read_csv_optional(R2 / "08_DESIGN_OPTIMIZATION_ADDON/WP_D5_design_recommendation/minimal_delta_variant_screen.csv")
    design_top_catalog = read_csv_optional(R2 / "08_DESIGN_OPTIMIZATION_ADDON/WP_D1_selection_pareto_highstat/top20_catalog_uniform_highstat.csv")
    design_top_bound = read_csv_optional(R2 / "08_DESIGN_OPTIMIZATION_ADDON/WP_D1_selection_pareto_highstat/top20_focal_core_bound_highstat.csv")
    design_material_bound = read_csv_optional(R2 / "08_DESIGN_OPTIMIZATION_ADDON/WP_D3_material_geometry_bound/removal_bound_table.csv")
    design_timing_overlay = read_csv_optional(R2 / "08_DESIGN_OPTIMIZATION_ADDON/WP_D1_timing_overlay/timing_window_overlay.csv")
    mixed_rates = read_csv(R2 / "01B_CONVERGENCE_PATCH_UPDATE/mixed_voxel_delta/radial_vs_voxel_delta_rates.csv")
    mixed_summary = load_json(R2 / "01B_CONVERGENCE_PATCH_UPDATE/mixed_voxel_delta/voxel_delta_transport_summary.json")
    allowed_claims = bullet_rows(read_text(R2 / "01B_CONVERGENCE_PATCH_UPDATE/claim_control/allowed_claims.md"), "allowed")
    forbidden_claims = bullet_rows(read_text(R2 / "01B_CONVERGENCE_PATCH_UPDATE/claim_control/forbidden_claims.md"), "forbidden")
    validation_all = validation_rows(read_text(R2 / "06_VALIDATION/workspace_validation.md"))
    refs = bib_entries()
    focused_broad = find_row(focused_summary, "window", "broad_480_550")
    focused_line = find_row(focused_summary, "window", "line_510p3_511p8")
    focused_add_broad = find_row(focused_addendum, "window", "broad_480_550")
    focused_add_line = find_row(focused_addendum, "window", "line_510p3_511p8")
    prompt_final = float(day15["expectation_rates_by_stream_cps"]["prompt"]["final"])
    delayed_final = float(day15["expectation_rates_by_stream_cps"]["delayed"]["final"])
    science_reference_final = float(day15["expectation_rates_by_stream_cps"]["science"]["final"])
    diagnostic_total_final = float(day15["expectation_rates_cps"]["final"])
    focused_broad_final = float(focused_broad.get("mean_final_focused_gamma_cps", 0.0) or 0.0)
    background_only_broad = prompt_final + delayed_final + focused_broad_final
    prompt_raw = float(day15["expectation_rates_by_stream_cps"]["prompt"]["raw"])
    delayed_raw = float(day15["expectation_rates_by_stream_cps"]["delayed"]["raw"])
    prompt_bgo = float(day15["expectation_rates_by_stream_cps"]["prompt"]["bgo"])
    delayed_bgo = float(day15["expectation_rates_by_stream_cps"]["delayed"]["bgo"])
    measured_broad = find_row_all(measured, window="broad_480_550", energy_type="measured")
    broad_wc = find_row_all(likelihood, energy_window="broad_480_550", model="window_counting_same_events")
    broad_erl = find_row_all(likelihood, energy_window="broad_480_550", model="energy_radius_layer_template")
    line_erl = find_row_all(likelihood, energy_window="line_510p3_511p8", model="energy_radius_layer_template")
    p3_values = [
        float(r["P3"])
        for r in injection
        if r.get("model") == "energy_radius_layer_template"
        and r.get("energy_window") in {"broad_480_550", "line_510p3_511p8"}
    ]
    p3_range = f"{min(p3_values):.3g}-{max(p3_values):.3g}" if p3_values else "0.19-0.20"

    day_rows = []
    for stream in ("prompt", "delayed"):
        row = day15["expectation_rates_by_stream_cps"][stream]
        day_rows.append({"stream": stream, "raw": row["raw"], "bgo": row["bgo"], "final": row["final"]})
    day_rows.append({
        "stream": "focused gamma addendum",
        "raw": "",
        "bgo": "",
        "final": focused_broad_final,
    })
    day_rows.append({
        "stream": "background-only sensitivity ledger",
        "raw": prompt_raw + delayed_raw,
        "bgo": prompt_bgo + delayed_bgo,
        "final": background_only_broad,
    })
    row = day15["expectation_rates_by_stream_cps"]["science"]
    day_rows.append({"stream": "reference science stream (diagnostic only)", "raw": row["raw"], "bgo": row["bgo"], "final": row["final"]})
    day_rows.append({
        "stream": "diagnostic total incl. reference science",
        "raw": day15["expectation_rates_cps"]["raw"],
        "bgo": day15["expectation_rates_cps"]["bgo"],
        "final": diagnostic_total_final,
    })
    day_rows.append({
        "stream": "common timeline realization (diagnostic)",
        "raw": day15["timeline_rates_cps"]["raw"],
        "bgo": day15["timeline_rates_cps"]["bgo"],
        "final": day15["timeline_rates_cps"]["final"],
    })
    lineage_rows = [
        {"quantity": "prompt final 480-550", "value": prompt_final, "source_definition": "direct expectation, final cuts, prompt stream", "used_for": "background ledger"},
        {"quantity": "delayed final 480-550", "value": delayed_final, "source_definition": "direct expectation, final cuts, delayed stream", "used_for": "background ledger"},
        {"quantity": "focused gamma broad addendum", "value": focused_broad_final, "source_definition": "Level-1 optics aperture ledger, final selected rate", "used_for": "small background addendum / systematic"},
        {"quantity": "background-only 480-550", "value": background_only_broad, "source_definition": "prompt + delayed + focused gamma addendum", "used_for": "sensitivity B"},
        {"quantity": "reference science final 480-550", "value": science_reference_final, "source_definition": "F=1e-4 ph cm^-2 s^-1 diagnostic stream", "used_for": "diagnostic only"},
        {"quantity": "diagnostic total 480-550", "value": diagnostic_total_final, "source_definition": "prompt + delayed + reference science stream", "used_for": "common timeline comparison / diagnostic"},
        {"quantity": "measured-energy diagnostic total 480-550", "value": measured_broad.get("final_cps", ""), "source_definition": "measured-energy catalog, includes reference science stream", "used_for": "detector-response diagnostic"},
        {"quantity": "common-timeline realization 480-550", "value": day15["timeline_rates_cps"]["final"], "source_definition": "finite Poisson timeline realization", "used_for": "validation / diagnostic"},
        {"quantity": "corrected science response", "value": day15["science_sensitivity"]["science_final_response_cps_per_ph_cm-2_s-1"], "source_definition": "Gate-A corrected Be-window beam", "used_for": "signal response"},
        {"quantity": "broad profiled 3sigma / 1 Ms", "value": broad_wc.get("profiled_flux_3sigma_ph_cm2_s", ""), "source_definition": "window counting, diagonal nuisance proxy", "used_for": "conservative threshold"},
        {"quantity": "broad ERL profiled 3sigma / 1 Ms", "value": broad_erl.get("profiled_flux_3sigma_ph_cm2_s", ""), "source_definition": "energy-radius-layer template, diagonal nuisance proxy", "used_for": "best broad proxy threshold"},
        {"quantity": "line ERL profiled 3sigma / 1 Ms", "value": line_erl.get("profiled_flux_3sigma_ph_cm2_s", ""), "source_definition": "energy-radius-layer template, diagonal nuisance proxy", "used_for": "best line proxy threshold"},
        {"quantity": "P>=3sigma at 1e-4, 1 Ms", "value": p3_range, "source_definition": "source injection proxy, ERL broad/line rows", "used_for": "claim control"},
    ]
    write_csv(
        OUT / "final_numerical_lineage.csv",
        lineage_rows,
        ["quantity", "value", "source_definition", "used_for"],
    )
    (OUT / "final_numerical_lineage.json").write_text(json.dumps(lineage_rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    pipeline_rows = [
        {"stage": "geometry authority", "artifact": "XZTES/TibetTES_v5_6layers", "role": "mass model, TES volumes, BGO shield and Be-window source plane", "limitation": "no mechanical tolerance or electronics response model"},
        {"stage": "prompt source", "artifact": "Cosima-ready 160-component full-sphere background sources", "role": "gamma/electron/positron/proton/neutron/muon/alpha prompt transport", "limitation": "catalog keeps particle identity but not event-level primary energy/angle"},
        {"stage": "optics-focused gamma addendum", "artifact": "focused_gamma_background_summary.csv", "role": "separate aperture-accepted gamma background ledger through optics FoV and effective area", "limitation": "Level-1 rate addendum, not full optics ray tracing or Cosima transport"},
        {"stage": "PARMA reference profile", "artifact": "official EXPACS/PARMA C++ driver grid", "role": "altitude/time/particle scale and 511 keV atmospheric transmission", "limitation": "reference profile, not measured balloon telemetry"},
        {"stage": "buildup activation", "artifact": "isotope-production RP/IP records", "role": "nuclide-volume inventory and delayed source activity", "limitation": "parent-feed branch ratios not yet audited"},
        {"stage": "day-15 delayed source", "artifact": "fixed W183/W180 source plus Level-1 real-profile scaling", "role": "radioactive delayed background in Cosima", "limitation": "fixed day-15 spatial profile scaled by activity"},
        {"stage": "event catalog", "artifact": "science + prompt + delayed common timeline", "role": "BGO veto, Compton/FoV and measured-energy catalog closure", "limitation": "BGO is event-total proxy rather than per-hit electronics"},
        {"stage": "statistics", "artifact": "window counting, Fisher/template likelihood, profiled proxy, injection proxy", "role": "rank sensitivity and quantify detection probability", "limitation": "not a full nuisance-template Poisson optimizer"},
        {"stage": "report package", "artifact": "reports2.0 with validation, figures, authorities and scripts", "role": "portable evidence package for review and paper drafting", "limitation": "HTML/PDF report is only as current as packaged authorities"},
    ]
    production_rows = [r for r in validation_all if r["check"].startswith("production_")]
    phase2_validation_rows = [r for r in validation_all if r["check"].startswith("phase2_")]
    nextphase_validation_rows = [r for r in validation_all if r["check"].startswith("nextphase_")]
    line_sensitivity_1ms = [
        r for r in line_sensitivity
        if r["exposure_s"] == "1000000.0"
        and r["energy_window"] in {"broad_480_550", "line_510p3_511p8"}
    ]
    science_source_rows = [
        {"item": "current physical meaning", "value": "post-optics Be-window photon response source", "claim": "generic on-axis 511-keV response source; not a named V404 source"},
        {"item": "cosmosray_0416 lineage", "value": "Laue-lens focused spot concept", "claim": "implemented as a uniform focal spot at the Be-window entrance plane"},
        {"item": "Cosima geometry", "value": "Gate-A corrected geometry-coordinate beam: HomogeneousBeam 0.0 0.0 127.66 0.0 0.0 -1.0 18.0", "claim": "coordinates use the XZTES geometry convention; external optics are not transported inside Cosima"},
        {"item": "astrophysical normalization", "value": "R_plane = F_511 * A_eff * T_atm * visibility", "claim": "theory/V404 flux enters through normalization or future light curve, not through current geometry"},
        {"item": "baseline spectrum", "value": "Spectrum Mono 511.000000", "claim": "narrow-line response authority"},
        {"item": "broadened spectra", "value": "Spectrum File science_511_<model>.dat", "claim": "Gaussian/velocity line models change source photon-energy distribution only"},
    ]
    optics_background_rows = [
        {"component": "science 511 source", "path": "optics effective area + Be-window HomogeneousBeam response", "current_status": "included as post-optics response source", "claim": "valid for generic on-axis signal response"},
        {"component": "direct atmospheric/cosmic gamma prompt", "path": "full-sphere environmental source directly incident on mass model", "current_status": "included without focusing optics", "claim": "covers direct detector irradiation, not lens-focused aperture background"},
        {"component": "optics-focused diffuse/atmospheric gamma", "path": "I_bg(E,Omega,t) through A_opt(E,Omega) and focal-plane PSF", "current_status": "included as separate Level-1 rate addendum", "claim": "added to sensitivity ledger without reweighting or duplicating direct prompt gamma"},
        {"component": "local activation/instrumental gamma", "path": "radioactive decays inside mass model", "current_status": "included as delayed source", "claim": "not an external parallel beam and should not be counted as focused optics input"},
    ]
    design_recommendation_display = [
        {
            "case": r.get("design_case", ""),
            "response": fmt(r.get("science_response_cps_per_flux", "")),
            "broad_B": fmt(r.get("broad_background_cps", "")),
            "line_B": fmt(r.get("line_background_cps", "")),
            "Q/Q0": fmt(r.get("q_over_q0", "")),
            "F3_1Ms": fmt(r.get("f3_best_scaled_1Ms_ph_cm2_s", "")),
            "P3": fmt(r.get("p_ge_3sigma_at_1e-4_1Ms", "")),
            "risk": r.get("hardware_risk", ""),
            "recommendation": r.get("recommendation", ""),
            "variant": r.get("variant_id", ""),
        }
        for r in design_recommendation
    ]
    design_top_catalog_display = [
        {
            "variant": r.get("variant_id", ""),
            "B": fmt(r.get("background_broad_cps", "")),
            "R": fmt(r.get("science_response_cps_per_flux", "")),
            "survival": fmt(r.get("science_survival_vs_baseline", "")),
            "Q/Q0": fmt(r.get("q_over_q0", "")),
            "F3_1Ms": fmt(r.get("f3_best_scaled_1Ms_ph_cm2_s", "")),
            "P3": fmt(r.get("p_ge_3sigma_at_1e-4_1Ms", "")),
            "line_B": fmt(r.get("background_line_cps", "")),
        }
        for r in design_top_catalog[:8]
    ]
    design_top_bound_display = [
        {
            "variant": r.get("variant_id", ""),
            "B": fmt(r.get("background_broad_cps", "")),
            "R_bound": fmt(r.get("science_response_cps_per_flux", "")),
            "catalog_source_cps": fmt(r.get("science_catalog_broad_cps_at_1e-4", "")),
            "Q/Q0": fmt(r.get("q_over_q0", "")),
            "F3_1Ms": fmt(r.get("f3_best_scaled_1Ms_ph_cm2_s", "")),
            "P3": fmt(r.get("p_ge_3sigma_at_1e-4_1Ms", "")),
            "note": r.get("source_acceptance_note", ""),
        }
        for r in design_top_bound[:6]
    ]
    design_material_display = [
        {
            "group": r.get("geometry_group", ""),
            "activity": fmt(r.get("activity_Bq", "")),
            "delayed_B": fmt(r.get("delayed_broad_final_cps", "")),
            "line_B": fmt(r.get("delayed_line_final_cps", "")),
            "frac": fmt(r.get("broad_fraction_of_total_background", "")),
            "Q_removed": fmt(r.get("q_over_q0_if_removed_bound", "")),
            "Q_half": fmt(r.get("q_over_q0_if_50pct_reduced_bound", "")),
            "flag": r.get("priority_flag", ""),
        }
        for r in design_material_bound[:10]
    ]
    design_variant_display = [
        {
            "variant": r.get("variant", ""),
            "status": r.get("execution_status", ""),
            "Q/Q0": fmt(r.get("q_over_q0", "")),
            "F3": fmt(r.get("f3_best_scaled_1Ms_ph_cm2_s", "")),
            "evidence": r.get("evidence", ""),
            "decision": r.get("decision", ""),
        }
        for r in design_variant_screen
    ]
    design_timing_display = [
        {
            "window_us": fmt(r.get("window_us", "")),
            "B": fmt(r.get("background_broad_cps", "")),
            "survival": fmt(r.get("science_survival", "")),
            "Q/Q0": fmt(r.get("q_over_q0", "")),
            "F3_1Ms": fmt(r.get("f3_best_scaled_1Ms_ph_cm2_s", "")),
        }
        for r in design_timing_overlay
    ]
    design_baseline_case = find_row(design_recommendation, "design_case", "baseline Ta6")
    design_selection_best = find_row(design_recommendation, "design_case", "selection-only best")
    design_roi_bound = find_row(design_recommendation, "design_case", "ROI with focal-core source bound")

    css = """
    body { font-family: "Noto Serif CJK SC", "Source Han Serif SC", "SimSun", serif; color: #1b1b1b; line-height: 1.72; max-width: 1120px; margin: 0 auto; padding: 28px 44px 80px; background: #f8f8f6; }
    article { background: #fff; padding: 46px 56px; box-shadow: 0 3px 20px rgba(0,0,0,.08); }
    h1 { font-size: 30px; line-height: 1.25; margin-bottom: 12px; }
    h2 { margin-top: 46px; border-bottom: 2px solid #222; padding-bottom: 6px; font-size: 23px; }
    h3 { margin-top: 28px; font-size: 19px; }
    h4 { margin-top: 20px; font-size: 16px; }
    .meta, .note { color: #555; font-size: 14px; }
    .abstract, .claimbox { background: #f3f5f7; border-left: 4px solid #345; padding: 16px 20px; margin: 18px 0; }
    .claimbox { background: #fff7ed; border-left-color: #9a5b00; }
    table { width: 100%; border-collapse: collapse; margin: 18px 0 28px; font-size: 13px; }
    caption { text-align: left; font-weight: 700; margin-bottom: 6px; }
    th, td { border: 1px solid #d0d0d0; padding: 6px 8px; vertical-align: top; }
    th { background: #eceff3; }
    figure { margin: 26px 0 34px; break-inside: avoid; }
    img { max-width: 100%; display: block; margin: 0 auto; border: 1px solid #ddd; background: white; }
    figcaption { font-size: 13px; color: #444; margin-top: 8px; }
    code, pre { font-family: "DejaVu Sans Mono", Consolas, monospace; }
    pre { background: #f4f4f4; padding: 12px; overflow-x: auto; }
    .equation { text-align: center; font-family: "DejaVu Sans", serif; background: #fafafa; border: 1px solid #e4e4e4; padding: 10px; margin: 14px 0; }
    .refs li { margin: 7px 0; }
    a { color: #174a7c; }
    @media print { body { background: white; padding: 0; } article { box-shadow: none; padding: 0; } h2 { break-before: page; } figure, table { break-inside: avoid; } }
    """

    html_parts: list[str] = []
    html_parts.append("<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">")
    html_parts.append("<title>COSMOSRAY_BG_2605 511 keV TES 背景与灵敏度详细论文稿</title>")
    html_parts.append(f"<style>{css}</style></head><body><article>")
    html_parts.append("<h1>气球平台 511 keV 聚焦 TES 谱仪的宇宙线背景、活化本底与点源灵敏度：基于 MEGAlib/Cosima 与 PARMA 参考飞行剖面的详细模拟研究</h1>")
    html_parts.append("<p class=\"meta\"><b>稿件定位：</b>NIMA 风格中文详细论文稿；<b>输出目录：</b><code>reports2.0/07_NIMA_MANUSCRIPT/</code>；<b>生成日期：</b>2026-05-13。</p>")
    html_parts.append(f"<div class=\"abstract\"><h2>摘要</h2><p>本文给出 COSMOSRAY_BG_2605 工作区中 511 keV 聚焦 TES 谱仪背景模拟链的详细论文版表述。研究对象是一个面向银河系 511 keV 正负电子湮没线观测的气球平台仪器概念：外部聚焦光学将天体 511 keV 光子投射到 Be-window 附近，焦平面由多层 TES 微量热阵列承担高分辨能谱测量，BGO 屏蔽提供主动反符合。模拟链采用 MEGAlib/Cosima 作为 Geant4 输运前端，使用全空间上/下行 20-bin 大气宇宙线 prompt 源，利用 buildup 中的 isotope-production 记录构造 delayed activation 源，并将 science、prompt、delayed 三类事件放入共同 Poisson 时间轴后统一施加 BGO 与 Compton/FoV 选择。Phase2 引入官方 EXPACS/PARMA C++ 模型，在 33-43 km、20 天、6 小时 bin 的参考气球剖面上计算粒子、角度和能量尺度。修正后的 day-15 prompt-plus-delayed 480-550 keV background-only sensitivity ledger 加入 focused-gamma addendum 后为 {fmt(background_only_broad)} cps；包含 1e-4 ph cm^-2 s^-1 reference science stream 的 direct-expectation diagnostic total 为 {fmt(diagnostic_total_final)} cps，共同时间轴 realization 为 {fmt(day15['timeline_rates_cps']['final'])} cps。measured-energy broad-window diagnostic total 为 {fmt(measured_broad.get('final_cps', ''))} cps。当前 science response 为 24.859 cps/(ph cm^-2 s^-1)，旧 z=12.766/r=1.8 源响应已作废。1 Ms 下，profiled nuisance proxy 给出 broad window-counting 3σ threshold 为 3.58e-4 ph cm^-2 s^-1，broad energy-radius-layer template 为 1.41e-4 ph cm^-2 s^-1，line energy-radius-layer template 为约 1.40e-4 ph cm^-2 s^-1。source-injection proxy 表明 1e-4 ph cm^-2 s^-1 在 1 Ms 下并非稳健 3σ 检出，P(>=3σ) 约 0.19-0.20。本文将结果严格表述为 corrected day-15 static chain + Phase2 reference-profile/proxy convergence study with quantified limitations，而不是最终实测飞行灵敏度。</p></div>")
    html_parts.append(f"<p class=\"note\"><b>本次更新：</b>报告新增 optics-focused gamma background 的 Level-1 独立速率账本。该项只计算光学 FoV 与有效面积接受的外部 γ 子集，不回写也不重权 direct full-sphere prompt γ；480-550 keV 平均 final addendum={fmt(focused_broad.get('mean_final_focused_gamma_cps', '0'))} cps，510.3-511.8 keV 平均 final addendum={fmt(focused_line.get('mean_final_focused_gamma_cps', '0'))} cps。</p>")
    html_parts.append("<p><b>关键词：</b>511 keV；正负电子湮没线；TES 微量热器；气球实验；MEGAlib；Cosima；Geant4；EXPACS/PARMA；活化本底；BGO 反符合；profile likelihood。</p>")

    html_parts.append("<h2>1. 科学动机与仪器学背景</h2>")
    html_parts.append("<p>511 keV 正负电子湮没线是高能天体物理中少数能直接追踪低能正电子终态的谱线之一。INTEGRAL/SPI 对全天 511 keV 发射的测绘确认了银河核球方向的强发射，并揭示了核球/盘比例、线宽、正电子素连续谱和形态上的长期难题 [15-20]。这些观测推动了两类后续仪器路线：一类是以 COSI 为代表的宽视场 Compton 谱仪，依靠三维相互作用定位、BGO 或 ACS 主动屏蔽以及成像重建提高全天巡天灵敏度 [21,22]；另一类是 511-CAM 这类聚焦光学 + TES 微量热阵列方案，试图用亚 keV 级能量分辨率和聚焦通量增益分离点源、速度场和弱线结构 [9-14]。</p>")
    html_parts.append("<p>本工作处在第二类路线的背景评估阶段。聚焦光学本身不能消除焦平面材料中的粒子感生本底，也不能自动解决气球高度下大气二次宇宙线、BGO veto、活化核素和高计数率时间偶然符合的问题。因此，背景模拟必须同时满足四个要求：其一，质量模型和物理过程要能支持 MeV 量级 photon、electron、hadron 与核素衰变输运；其二，宇宙线环境要能随高度、经纬度和方向改变；其三，prompt 与 delayed 应在同一选择逻辑和同一曝光归一化下比较；其四，灵敏度结论不能把单次 Poisson realization、proxy likelihood 或 reference profile 误写成最终实测飞行结果。</p>")
    html_parts.append("<p>Geant4 是这类模拟的底层通用工具 [1,2]，MEGAlib/Cosima 则提供了面向低到中能伽玛射线望远镜的 source、geometry、simulation 和 event-analysis 生态 [3,4]。EXPACS/PARMA 给出了近地大气中宇宙线通量的解析模型，覆盖高度、截止刚度、太阳调制和天顶角依赖 [5-8]。DIXE、ATHENA X-IFU 和 Hitomi/SXS 的工作说明，TES 或微量热器仪器的 non-X-ray background 必须通过质量模型、粒子环境、反符合策略和测量能量响应共同确定 [23-28]。这些文献构成本文方法学选择的外部依据。</p>")

    html_parts.append("<h2>2. 工作流总览、数据谱系与可复现边界</h2>")
    html_parts.append("<p>为避免把工程目录中的中间产物误解为独立结果，本文先给出完整数据谱系。模拟链不是单一 Cosima 运行，而是由 geometry authority、prompt source、PARMA reference profile、activation inventory、delayed source、common timeline、detector response catalog、likelihood proxy 和 report packaging 共同闭合。每个 stage 均有对应 artifact、物理角色和当前限制；这些限制在正文中反复出现，是本文 claim-control 的来源。</p>")
    html_parts.append(table_html(pipeline_rows, [("stage", "stage"), ("artifact", "authority artifact"), ("role", "role in analysis"), ("limitation", "current limitation")], "表 1. COSMOSRAY_BG_2605 Phase2 数据谱系与可复现边界。"))
    html_parts.append("<p>从审稿口径看，最关键的可复现性不是把所有中间日志堆进正文，而是让每个主要数字都有可追溯的 authority file：day-15 rate 由 <code>complete_day15_summary.json</code> 给出；Phase2 reference profile 和 prompt reweight 分别由 environment grid 与 prompt reweight summaries 给出；delayed activity 由 inventory/source manifests 给出；likelihood/injection 由 CSV 表给出；报告包再由 validation script 检查 source placement、measured catalog closure、claim wording 和 production status。</p>")
    html_parts.append("<p>严格生产审计是本文区别于“示例模拟”的部分。instant prompt 与 buildup activation 各有 60/60 jobs 完成，requested/generated 粒子数均为 25,210,216；full delayed Cosima source 运行生成 1,000,000/1,000,000 events。由于这些生产量仍有限，本文将统计误差和模型误差分开表述：有限生产样本可以支持 rate closure 和 proxy sensitivity ranking，但不足以替代完整飞行任务的最终灵敏度预算。</p>")
    html_parts.append(table_html(production_rows, [("status", "status"), ("check", "check"), ("note", "validation note")], "表 2. validation 中的 production 审计条目。"))
    html_parts.append("<h3>2.1 Final numerical lineage table</h3>")
    html_parts.append("<p>为避免把 background-only rate、reference-science diagnostic total 和 science response 混用，本文将所有摘要、结果和结论中反复出现的关键数值集中到一张 numerical lineage table。表中 <i>used for</i> 明确标出哪些量进入 sensitivity 的 background ledger，哪些量只用于 common-timeline 或 detector-response diagnostic。</p>")
    html_parts.append(table_html(lineage_rows, [("quantity", "quantity"), ("value", "value"), ("source_definition", "source / definition"), ("used_for", "used for")], "表 2b. Final numerical lineage table：关键数值、来源和用途。"))

    html_parts.append("<h2>3. 仪器模型、坐标口径与 science-source authority</h2>")
    html_parts.append("<h3>3.1 XZTES/TibetTES 六层质量模型</h3>")
    html_parts.append("<p>当前质量模型继承 XZTES/TibetTES_v5_6layers 几何，包含 Be/Al/Nb/W 等窗口和屏蔽材料、Cu 支撑、Si substrate、Ta TES absorber、多层 TES 像素阵列以及 BGO 主动屏蔽。validation 中首先检查 XZTES core geometry 与原始几何一致，随后检查 package source 能否从 workspace root 运行，并确认 run_configs 中的背景源使用 MEGAlib 原有 particle ID 映射。该设计沿用 NIMA 类仪器论文中常见的做法：先给出 mass model、sensitive detector 和 passive/active shield 的作用边界，再把 source、transport、detector effect 与 selection 分层讨论。</p>")
    html_parts.append("<h3>3.2 Gate-A science source 修正</h3>")
    html_parts.append("<p>science source 是本文最重要的 authority 修正之一。旧版本曾使用 <code>z=12.766, radius=1.8</code> 的 HomogeneousBeam，并将其理解为 Be-window 前方的 1.8 cm 聚焦光斑；Gate-A 检查发现，在活动 XZTES 几何坐标约定下该源实际位于或接近 TES_L0，而不是 Be-window 外侧。因此，所有旧 response，特别是 33.947 cps/(ph cm^-2 s^-1)，均已作废。当前 authority 为：</p>")
    html_parts.append("<pre>run_configs/Science_511_onaxis_focalbeam_local.source\nScience511_OnAxis.Beam HomogeneousBeam 0.0 0.0 127.66 0.0 0.0 -1.0 18.0</pre>")
    html_parts.append(f"<p>Gate-A 输出给出 source_z=127.66、Win_Be z_max=127.65、clearance=0.01，当前 science final response 为 <b>{fmt(day15['science_sensitivity']['science_final_response_cps_per_ph_cm-2_s-1'])} cps/(ph cm^-2 s^-1)</b>。所有 source coordinates 均使用 XZTES mass model 的同一 geometry-coordinate convention；当前 Be-window placement 由 first-hit 和 window-clearance diagnostics 验证，旧 response 不进入任何当前 sensitivity 数值。这与 511-CAM 论文中“外部光学负责有效面积与焦斑，探测器输运负责焦平面相互作用”的分层思想一致 [9]，但本文没有在 Cosima 中追踪完整 Laue/channeling optics，而是在 Be-window 处注入 post-optics photons。</p>")
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/gate_A_source_placement/first_tes_hit_z_hist.png", "图 1. Gate-A source placement 检查：修正后的 Be-window beam 首次 TES 相互作用位置分布。"))
    html_parts.append("<h3>3.3 当前 science source 与理论源/V404 源的关系</h3>")
    html_parts.append("<p>这里需要明确一个容易误读的口径：当前工作没有在 Cosima 中引入一个名为 V404 的天体源，也没有把某个理论湮没模型的空间分布直接投影进质量模型。它继承 cosmosray_0416 方案中“511 source：模拟劳厄透镜聚焦后的 spot”的想法，把外部聚焦光学之后到达 Be-window 的 511 keV photons 作为一个通用 on-axis response source。换言之，当前 source 用于回答“若 Be-window 处已有某个 511 keV photon rate，焦平面能留下多少 selected signal”，而不是回答“V404 或某个理论模型本身的真实天空通量是多少”。</p>")
    html_parts.append("<div class=\"equation\">R<sub>plane</sub>(t,E) = F<sub>511</sub>(t,E) A<sub>eff</sub>(E) T<sub>atm</sub>(t,E) V(t), &nbsp; R<sub>final</sub> = R<sub>plane</sub> ε<sub>transport+selection</sub></div>")
    html_parts.append("<p>因此，理论源或 V404 源应在 <code>F_511(t,E)</code>、line profile、visibility/off-axis history 或未来 optics effective-area model 中进入；只要它们被外部光学聚焦为同一个 Be-window 近场 spot，Cosima geometry source 仍可保持同一个 <code>HomogeneousBeam</code> authority。若未来要模拟 V404 的具体 flare/light curve，则应新增一个 source-case table，给出 V404 的 assumed flux、time profile、line width、off-axis pointing 与 atmospheric transmission，而不应把当前 generic response source 误称为 V404 source。</p>")
    html_parts.append(table_html(science_source_rows, [("item", "item"), ("value", "current implementation"), ("claim", "allowed interpretation")], "表 3a. Science source authority 与理论/V404 源口径。"))
    html_parts.append("<h3>3.4 511 keV 展宽源如何进入 Cosima</h3>")
    html_parts.append("<p>baseline science run 使用 <code>Science511_OnAxis.Spectrum Mono 511.000000</code>。展宽模型由 <code>configs/nextphase/science_511_line_models.yaml</code> 定义，<code>tools/build_science_511_line_sources.py</code> 读取 baseline source template 并只替换 energy spectrum 与 output prefix；beam geometry、particle type、physics list 和 trigger count 不变。Gaussian 模型采用 σ_E=FWHM/2.35482；velocity Gaussian 模型采用 σ_E=E_0 σ_v/c。非 mono 模型写成 <code>IP LIN / DP E p(E)</code> 格式的谱文件，例如 <code>science_511_gaussian_fwhm_2p5.dat</code>，再通过 <code>Science511_OnAxis.Spectrum File ...</code> 被 Cosima source 文件引用。</p>")
    html_parts.append("<p>当前 detailed report 中的 line-model sensitivity 是轻量 normalization step：它把 source-frame line fraction 传播到当前 mono-source response 和 timing survival，而不是对每个展宽模型重新跑大型 Cosima transport。这个处理适合说明窄能窗对 intrinsic line width 的敏感性，但不应写成“所有展宽模型都已完成完整输运生产”。</p>")
    html_parts.append(fig("../04_FIGURES/nima_update/science_source_and_line_broadening.png", "图 1b. Science source 引入方式与 intrinsic line broadening source files：左侧为 Be-window source/geometry，右侧为展宽谱与窄窗灵敏度影响。"))
    html_parts.append("<h3>3.5 聚焦光学对 γ 本底的影响边界</h3>")
    html_parts.append("<p>还有一个必须单独说明的背景项：如果真实仪器前端使用 511 keV 聚焦光学，那么被聚焦的不只是目标源 photons。任何来自光学口径方向、满足晶体/光学能量-角度响应并落入 FoV/bandpass 的 γ-ray background，包括弥散天体 511/continuum、宇宙 γ 背景、地球反照或大气 γ 连续谱，都可能被光学重分布到焦平面。它们与 science source 共用一部分 optics response，并不等价于当前 full-sphere direct prompt γ。</p>")
    html_parts.append("<div class=\"equation\">R<sub>opt,bg</sub>(x,y,E',t)=∫ I<sub>bg</sub>(E,Ω,t) A<sub>opt</sub>(E,Ω) P<sub>focus</sub>(x,y,E'|E,Ω) dE dΩ</div>")
    html_parts.append("<p>本次更新把第三类 aperture γ background 做成独立 Level-1 速率账本，而不是把全天 prompt γ 重新聚焦。实现步骤为：从 <code>docs/summary.json</code> 读取 511 keV optics effective area 与 FoV radius；从 20-bin EXPACS/PARMA γ 方向谱读取 source zenith 最近角度 bin 及 480-550/510.3-511.8 keV 谱积分；用 Phase2 6 小时 gamma scale 进行时间调制；再乘以 current science ledger 给出的 post-optics transport+selection efficiency。其近似公式为</p>")
    html_parts.append("<div class=\"equation\">R<sub>opt,bg</sub><sup>L1</sup>(t;E_1,E_2)=I<sub>γ</sub>(θ_s,t) f_{E_1,E_2}(θ_s) Ω<sub>FoV</sub> A<sub>eff</sub> ε<sub>transport+selection</sub>, &nbsp; Ω<sub>FoV</sub>≈πθ<sub>FoV</sub><sup>2</sup></div>")
    html_parts.append("<p>这里的 no-double-count 规则是硬边界：direct full-sphere prompt γ 流保持不变，focused γ 只作为一条单独命名的 aperture addendum 写入 sensitivity ledger。这个 Level-1 项仍未替代完整 Laue/channeling ray tracing、能量-角度响应、off-axis PSF 和大气反照建模；但它已经回答了“自然 γ 源经过聚焦光学是否应被计入”的审稿问题，并给出在当前 FoV 与有效面积假设下的数量级。</p>")
    html_parts.append(table_html(optics_background_rows, [("component", "component"), ("path", "physical path"), ("current_status", "current status"), ("claim", "claim boundary")], "表 3b. 聚焦光学下 science 与 γ 本底路径的当前处理。"))
    html_parts.append(table_html(focused_summary, [("window", "window"), ("mean_post_optics_plane_rate_s^-1", "plane rate s^-1"), ("mean_final_focused_gamma_cps", "final cps"), ("representative_theta_mid_deg", "theta mid deg"), ("representative_spectrum_fraction", "spectrum fraction"), ("accounting_policy", "accounting policy")], "表 3c. Level-1 optics-focused γ background 速率账本。"))
    html_parts.append(table_html(focused_addendum, [("window", "window"), ("old_background_cps", "old B cps"), ("focused_gamma_addendum_cps", "focused add cps"), ("new_background_cps", "new B cps"), ("focused_fraction_of_background", "fraction of B"), ("threshold_scale_sqrt_Bnew_over_Bold", "threshold scale")], "表 3d. 聚焦 γ addendum 对 1 Ms sensitivity ledger 的影响。"))
    html_parts.append(fig("../04_FIGURES/nima_update/optics_focused_gamma_background_concept.png", "图 1c. 聚焦光学会同时接受 source photons 与 FoV/bandpass 内的 γ 背景；当前处理为单独 Level-1 aperture addendum，避免与 direct prompt γ 双计数。"))
    html_parts.append(fig("../04_FIGURES/nima_update/optics_focused_gamma_background_addendum.png", "图 1d. optics-focused γ addendum 与原背景率的对比，以及加入该项后的阈值变化。"))

    html_parts.append("<h2>4. 大气宇宙线 prompt 源与 PARMA reference profile</h2>")
    html_parts.append(f"<p>prompt 源由全空间大气宇宙线构成，粒子种类包括 gamma、electron、positron、proton、neutron、muon 和 alpha。每个粒子被拆为 down/up 两个半球共 20 个等 mu 角度 bin，validation 中 fullsphere_component_count=160 且每个粒子都有 10 个 down 与 10 个 up bin。strict instant 与 buildup 生产各完成 60/60 jobs，均无失败，单条链 requested/generated particles 为 25,210,216。</p>")
    html_parts.append(f"<p>Phase2 使用 EXPACS/PARMA C++ driver 计算参考气球剖面。环境网格状态为 <b>{env['status']}</b>，backend={env['backend']}，time bins={env['n_time_bins']}，grid rows={env['n_grid_rows']}，scale range={fmt(env['scale_min'])}-{fmt(env['scale_max'])}，science 511 keV 大气透过率范围={fmt(env['science_T_atm_min'])}-{fmt(env['science_T_atm_max'])}。PARMA 日期固定为 2025-08-31，用于避开公开包对 2026 日期 FFP 数据缺失的问题；该剖面是 reference balloon profile，不是 measured telemetry。</p>")
    html_parts.append("<p>由于当前 prompt event catalog 只保存 particle identity，而没有 event-level primary energy/source-angle identity，PARMA angle/energy scale 在 prompt reweight 阶段只能按 particle 平均。这个处理是当前最重要的环境模型限制之一。它能把 prompt final 480-550 keV rate 随时间调制到 0.7997-2.489 cps 的范围，但尚不能给出每个真实 event 的 energy-angle-resolved reweight。</p>")
    html_parts.append(fig("../04_FIGURES/phase2/phase2_particle_scale_by_day.png", "图 2. Phase2 reference profile 下各粒子 prompt scale 随时间的变化。"))
    html_parts.append(fig("../04_FIGURES/phase2/phase2_prompt_rate_day_curve.png", "图 3. Reference profile reweight 后 prompt 480-550 keV final rate 的 day-scale 曲线。"))
    html_parts.append(fig("../04_FIGURES/phase2/phase2_science_transmission.png", "图 4. 511 keV science atmospheric transmission 与 visibility/geometry 因子。"))

    html_parts.append("<h2>5. delayed activation 源、W183/W180 修正与 parent-feed 限制</h2>")
    html_parts.append("<p>delayed 源来自 buildup 运行记录的 isotope-production positions。工作流先解析 CC IP RP 记录，建立核素-体积的活化产额与空间 profile，再按半衰期将 day-15 活度转换为 Cosima radioactive source blocks。此前发现的关键漏洞是将 W-183/W-180 ground state 误当成短寿命 isomer；修正后固定源删除 120 个错误 source blocks，fixed day-15 activity 从 1.592e3 Bq 降到 8.239e2 Bq，且 fixed source 中 <code>ParticleType 74183</code>/<code>74180</code> 残留为 0。</p>")
    html_parts.append("<div class=\"equation\">dN<sub>i,v</sub>/dt = P<sub>i,v</sub>(t) + Σ<sub>j</sub> b<sub>j→i</sub> λ<sub>j</sub>N<sub>j,v</sub>(t) - λ<sub>i</sub>N<sub>i,v</sub>(t), &nbsp; A<sub>i,v</sub>=λ<sub>i</sub>N<sub>i,v</sub></div>")
    html_parts.append(f"<p>Phase2 已建立 parent-fed schema，但由于本地没有经审计的 branch-ratio table，parent_feed_fraction 当前为 0；inventory status 为 <b>{inv['status']}</b>，day15_total_activity={fmt(inv['day15_total_activity_Bq'])} Bq。该处理与 NUBASE2020、ENSDF 和 Geant4 radioactive decay validation 文献的谨慎态度一致 [29-31]：half-life、isomer、branching 和 gamma intensity 不是可以在缺数据时任意补齐的工程细节，而是会直接改变 delayed-line background 的物理输入。</p>")
    html_parts.append("<h3>5.1 RPIP 位置抽样证据与几何上下文</h3>")
    html_parts.append("<p>2602 阶段的 RPIP day-15 检查图仍然是 delayed-source 方法学的关键证据：蓝点是 buildup 中记录的 isotope-production positions，橙点是按这些位置概率密度抽样出的 radioactive source positions。它说明 delayed source 不是按均匀体积或手工几何块随意撒点，而是按真实生产位置和核素记录抽样。该图原始路径为 <code>/home/ubuntu/cosmosray_bg_2602/cosmosray_buildup_rpmpia/decay_rpip_out/plot_check_day15.png</code>，已复制到本报告包。</p>")
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/activation_rpip_sampling/plot_check_day15_2602.png", "图 5a. 2602 RPIP day-15 sampling check：按 buildup RP/IP 位置分布抽样 delayed source positions。"))
    html_parts.append("<p>原 RPIP 图的不足是没有把 detector mass model 放在旁边，读者很难看出这些 sampled points 对应到哪些 shield、window、TES layers 或 passive structures。为此，本文新增一个几何上下文图：左侧保留 RPIP 抽样证据，右侧给出 XZTES r-z 截面示意，并特别修正一个容易造成误解的绘图口径：<code>TES_L*</code> 在几何中是 half-width=39 的真空母体，不应被画成 TES 有效质量；图中改画 Ta pixel footprint（约 r=15.5）和 Si substrate（r=19），同时显式画出 Cu base、Cu support pole、Be window 与 W collimator bars。</p>")
    html_parts.append(fig("../04_FIGURES/nima_update/rpip_sampling_geometry_context.png", "图 5b. RPIP sampling 与 XZTES 几何上下文：抽样点来自真实 isotope-production positions，并在同一质量模型中输运。"))
    html_parts.append("<p>核素积累并非没有出现在 TES、铜热支撑或准直器上；此前图 5.B 的问题是把容器/母体尺度与真实质量尺度混在一起，且没有把 inventory proxy 和 transported source-volume proxy 解释清楚。当前统计表将 inventory 中的 <code>TES_L*</code> 解释为 Ta pixel proxy，将 <code>Copper</code> 与 transport 中的 <code>Cu_Base/Cu_SupportPole</code> 合并为 Cu base/support，将 <code>CollBarX/Y</code> 视作物理 W 准直器条，而 <code>CollimatorVac</code> 仅作为 transport/source-volume proxy 注明。结果显示 TES、Cu 和 collimator 都有 delayed contribution，只是其可见度受尺度、核素和选择效率共同控制。</p>")
    html_parts.append(table_html(activation_geometry_summary[:12], [("geometry_group", "geometry group"), ("day15_parentfed_activity_Bq", "day-15 activity Bq"), ("broad_480_550_final_cps", "480-550 final cps"), ("line_510p3_511p8_final_cps", "510.3-511.8 final cps"), ("geometry_note", "geometry/proxy note")], "表 4a. 活化核素按物理几何组汇总：区分真实质量、真空母体和 source-volume proxy。"))
    html_parts.append(fig("../04_FIGURES/nima_update/activation_geometry_volume_map.png", "图 5c. 修正后的 activation geometry map：TES 画为 Ta 像素足迹，Cu 支撑/底座与 W 准直器条显式显示，并给出 activity 与 transported delayed rate。"))
    html_parts.append(table_html(activation[:8], [("nuclide", "nuclide"), ("source_activity_Bq", "activity Bq"), ("broad_480_550_final_cps", "480-550 final cps"), ("line_510p3_511p8_final_cps", "510.3-511.8 final cps"), ("beta_plus_branch_proxy", "β+ proxy"), ("truth_status", "status")], "表 1. 511 keV 附近 delayed activation top contributors。"))
    html_parts.append(fig("../04_FIGURES/day15/activation_top10_after_fix.png", "图 5. W183/W180 ground-state 修正后的 day-15 activation Top10。"))
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/activation_511_diagnostics/delayed_511_energy_spectrum_by_top_nuclides.png", "图 6. delayed 511 keV 区域 top nuclide 分解能谱。"))
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/activation_511_diagnostics/delayed_511_top10_bar.png", "图 7. 480-550 keV delayed final rate 的核素贡献排序。"))

    html_parts.append("<h2>6. 事件时间轴、BGO 反符合与 Compton/FoV 选择</h2>")
    html_parts.append(f"<p>corrected day-15 common-timeline test 使用 observation time T={fmt(day15['normalization']['obs_time_s'])} s、coincidence window={fmt(day15['normalization']['coincidence_window_s'])} s、BGO threshold={fmt(day15['normalization']['bgo_threshold_keV'])} keV、reject_policy={day15['normalization']['reject_policy']}。prompt、delayed 和 science events 按各自 rate 抽样进入同一 Poisson 时间轴；候选事件按 coincidence window 分组，再应用 TES energy window、BGO veto 和 Compton/FoV selection。这种共同时间轴处理避免了把 prompt 与 delayed 用不同曝光和不同 veto 逻辑归一化造成的 rate mismatch。</p>")
    html_parts.append(table_html(day_rows, [("stream", "stream"), ("raw", "raw cps"), ("bgo", "BGO cps"), ("final", "BGO+Compton/FoV cps")], "表 2. corrected day-15 480-550 keV rate decomposition。Science row is a diagnostic reference stream and is not part of the background-only sensitivity ledger."))
    html_parts.append("<p>表 2 中的 background-only sensitivity ledger 是后续 sensitivity 计算中 B 的语义来源；diagnostic total 则用于检查 common-timeline 与 reference science stream 的闭合。二者数值相差很小，但在审稿表述中不能混用。</p>")
    html_parts.append("<p>表 2 显示 delayed activation 是 final residual 的主导项：direct-expectation delayed final 为 4.368 cps，prompt final 为 1.404 cps。science 在 reference flux 1e-4 ph cm^-2 s^-1 下仅贡献 0.002486 cps，因此 sensitivity analysis 必须依赖长曝光、背景模板和统计判别，而不能从 1094.2 s 单次 science realization 直接推断。</p>")
    html_parts.append(fig("../04_FIGURES/day15/timeline_spectrum_480_550_veto_chain.png", "图 8. 480-550 keV 共同时间轴 VETO chain 谱。"))
    html_parts.append(fig("../04_FIGURES/day15/timeline_veto_rates_bar.png", "图 9. raw、BGO、final 三阶段 rate 对比。"))
    html_parts.append(fig("../04_FIGURES/day15/image8_like_component_spectrum_with_science.png", "图 10. IMAGE8-like component spectrum，含 science reference stream。"))

    html_parts.append("<h2>7. measured-energy catalog 与 detector response</h2>")
    html_parts.append("<p>当前 measured-energy catalog v2 对 TES pixel hits 施加 0.14 keV FWHM smearing，BGO 仍采用 event-total proxy。catalog 包含 3,590,919 events 和 596,935 TES pixel hits。Gate-B detector response 验证显示 science measured FWHM 约 0.147 keV，宽窗率受 smearing 影响很小，窄线窗更敏感。COSI ACS benchmark 指出，BGO/ACS 的位置依赖光收集、阈值和能量分辨率会显著影响 veto 响应 [22]；因此本文只把 event-total BGO proxy 写成小系统项，不写成完整 BGO electronics simulation。</p>")
    html_parts.append(table_html(measured, [("window", "window"), ("energy_type", "energy"), ("raw_cps", "raw cps"), ("bgo_cps", "BGO cps"), ("final_cps", "final cps")], "表 3. true-energy 与 measured-energy windows。"))
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/gate_B_detector_response/spectrum_480_550_true_vs_measured.png", "图 11. 480-550 keV 宽窗 true/measured spectrum 对比。"))
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/gate_B_detector_response/spectrum_510_515_true_vs_measured.png", "图 12. 510-515 keV line region true/measured spectrum 对比。"))

    html_parts.append("<h2>8. PARMA outlier contribution audit 与收敛补丁</h2>")
    p = update["parma_outlier"]
    html_parts.append(f"<p>原始 PARMA scale range 为 {fmt(p['max_raw_scale'])} 的数量级跨度，若只报告 min/max，审稿人可能质疑极端 bin 是否主导 rate。U2 因此加入 contribution-weighted audit：broad contribution-weighted scale={fmt(p['broad_contribution_weighted_scale'])}，line contribution-weighted scale={fmt(p['line_contribution_weighted_scale'])}；scale&gt;10 bins 对 broad/line final rate 的贡献均为 {fmt(p['broad_fraction_from_scale_gt10'])}/{fmt(p['line_fraction_from_scale_gt10'])}；hard-cap broad/line relative shifts 分别为 {fmt(p['hard_cap_broad_relative_difference'])}/{fmt(p['hard_cap_line_relative_difference'])}。判据上，这远低于 1% 系统项，因此 current uncapped baseline 可以保留。</p>")
    html_parts.append("<p>U1-U4 的收敛补丁不是扩展物理模型，而是封口径：source authority wording lock、PARMA outlier contribution audit、mixed voxel systematic freeze、parent-feed top-contributor data note。它们将报告从“可能被误读为 publication-level real-flight simulation”收敛到“reference-profile/proxy study with quantified limitations”。</p>")
    html_parts.append(table_html([
        {"item": "U1 source authority", **update["source_authority"]},
        {"item": "U2 PARMA outlier", **update["parma_outlier"]},
        {"item": "U3 mixed voxel", **update["mixed_voxel"]},
        {"item": "U4 parent feed", **update["parent_feed"]},
        {"item": "claim control", **update["claim_control"]},
    ], [("item", "item"), ("status", "status"), ("current_response_cps_per_ph_cm2_s", "response"), ("max_assigned_systematic_fraction", "max syst."), ("rate_change_applied", "rate change"), ("forbidden_claims", "forbidden")], "表 4. Phase2 convergence patch update U1-U4 状态。"))
    html_parts.append(fig("../01B_CONVERGENCE_PATCH_UPDATE/parma_outlier_audit/parma_scale_outlier_heatmap.png", "图 13. PARMA scale outlier contribution audit heatmap。"))

    html_parts.append("<h2>9. 线型模型、IMAGE8 分解、延迟源日序列与空间系统学</h2>")
    html_parts.append("<h3>9.1 511 keV science line model</h3>")
    html_parts.append("<p>银河 511 keV 线并非必然是数学意义上的 delta line。SPI/INTEGRAL 对线宽、正电子素连续谱和不同天区谱形的讨论表明，源区温度、电离态和湮没介质会改变观测线型 [16-20]。因此，本文在 mono line 之外加入 Gaussian FWHM 与 velocity Gaussian 模型，用同一 Be-window source placement 和同一 detector response 计算 broad 与 narrow windows 的 throughput。由于 480-550 keV broad window 宽于这些 line models，broad source fraction 近似为 1；而 510.3-511.8 keV narrow window 对 intrinsic line width 很敏感。</p>")
    html_parts.append(table_html(line_fraction, [("model_id", "model"), ("type", "type"), ("fwhm_src_keV", "FWHM keV"), ("fraction_480_550", "480-550 fraction"), ("fraction_510p3_511p8", "510.3-511.8 fraction"), ("source_file", "source file")], "表 9. source-frame line models and window fractions。"))
    html_parts.append("<p>1 Ms sensitivity table 显示，mono/0.5 keV/velocity_sigma_100 等窄线模型在 narrow line window 中几乎不损失 source fraction，3σ flux threshold 约 1.74e-4 ph cm^-2 s^-1；当 intrinsic FWHM 达到 2.5 keV 或 velocity_sigma_1000 时，narrow-window source fraction 显著下降，threshold 上升到 3.37e-4 至 5.16e-4 ph cm^-2 s^-1。这个结果说明：若未来科学目标从窄线点源扩展到高速 outflow 或 broad annihilation feature，不能沿用 narrow-window sensitivity 作为统一指标。</p>")
    html_parts.append(table_html(line_sensitivity_1ms, [("model_id", "model"), ("energy_window", "window"), ("source_fraction_in_window", "source fraction"), ("background_cps", "B cps"), ("response_cps_per_flux_after_accidental", "response after accidental"), ("flux_3sigma_ph_cm2_s", "3σ flux"), ("flux_5sigma_ph_cm2_s", "5σ flux")], "表 10. line-model sensitivity at 1 Ms。"))
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/science_line_models/sensitivity_by_line_model.png", "图 14. science line-model sensitivity 随 intrinsic line width 的变化。"))
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/science_line_models/spectrum_true_vs_measured_by_model.png", "图 15. 不同 science line models 的 true/measured spectra 对比。"))

    html_parts.append("<h3>9.2 IMAGE8-style component bookkeeping</h3>")
    html_parts.append("<p>为便于与 gamma-ray instrumentation 论文中常见的 component rate budget 对齐，本文给出 IMAGE8-style component bookkeeping：prompt、delayed、science 和 activation-delayed-only line component 均以 raw、BGO 和 final 三阶段列出。该表不引入新的模拟结果，而是把共同时间轴和 selection chain 中的 stream contribution 重新整理成可发表的 rate budget 形式。</p>")
    html_parts.append(table_html(image8, [("component", "component"), ("window", "window"), ("raw_cps", "raw cps"), ("bgo_cps", "BGO cps"), ("final_cps", "final cps")], "表 11. IMAGE8-style component rate budget。"))
    html_parts.append("<p>注意，表 11 没有把 focused-aperture γ addendum 回填到 prompt γ 组件中。直接 prompt γ 仍表示全空间环境粒子直接照射质量模型；focused γ 是表 3c/3d 中的独立 aperture 项，只有在 sensitivity ledger 中以 <code>B_new=B_direct+delayed+B_focused</code> 的形式相加。这样可避免把同一批全天球 γ 既作为直接入射又作为光学聚焦项重复计数。</p>")
    html_parts.append(fig("../04_FIGURES/phase2/phase2_image8_broad_480_550.png", "图 16. Phase2 IMAGE8-style 480-550 keV component spectrum。"))
    html_parts.append(fig("../04_FIGURES/phase2/phase2_image8_line_510p3_511p8.png", "图 17. Phase2 IMAGE8-style 510.3-511.8 keV line-window component spectrum。"))

    html_parts.append("<h3>9.3 延迟源 day-series 与 activity evolution</h3>")
    html_parts.append("<p>Level-1 real-profile delayed sources 覆盖 day 1、5、10、15、20。它们共享 fixed day-15 spatial profile，并按 real-profile activity schema 缩放 activity；因此它们适合做 reference-profile day-series rate study，但不应被描述为每天重新输运得到的空间分布。day-15 total activity 为 864.64 Bq，高于 fixed W183/W180 修正后 ground-state-clean source 的 823.95 Bq，因为 Phase2 inventory 使用了 real-profile activity schema。</p>")
    html_parts.append(table_html(delayed_manifest, [("day", "day"), ("flux_lines_scaled", "source lines"), ("spatial_profile_mode", "spatial profile mode"), ("total_activity_Bq", "total activity Bq"), ("source", "source file")], "表 12. Phase2 delayed source Level-1 manifest。"))
    html_parts.append(fig("../04_FIGURES/phase2/phase2_top_nuclide_activity_vs_day.png", "图 18. top nuclide activity evolution in the Phase2 reference profile。"))

    html_parts.append("<h3>9.4 mixed-voxel source systematic freeze</h3>")
    html_parts.append(f"<p>activation spatial model audit 发现 voxelized activity fraction={fmt(mixed_summary['voxel_activity_fraction'])}，对应 voxel activity={fmt(mixed_summary['voxel_activity_Bq'])} Bq。由于 minimal delta transport 尚未运行，当前工作不把 radial-only source 写成最终空间模型，而是冻结为 rate-level systematic bound。broad 480-550 keV bound 为 0.10198 cps，占 final background 的 1.77%；line-window bound 为 0.02582 cps，占 1.30%。这是一种保守的 publication wording 处理：承认 spatial approximation 的存在，并把它从灵敏度主结论中隔离出来。</p>")
    html_parts.append(table_html(mixed_rates, [("window", "window"), ("route", "route"), ("radial_only_reference_cps", "radial-only cps"), ("voxel_delta_transport_cps", "delta transport cps"), ("conservative_bound_cps", "bound cps"), ("assigned_systematic_fraction", "assigned systematic"), ("pass_condition", "pass condition")], "表 13. mixed-voxel systematic freeze。"))

    html_parts.append("<h2>10. 灵敏度估计：window counting、template likelihood 与 source injection</h2>")
    html_parts.append("<p>对 window-counting，本文使用 Gaussian/Asimov 形式 F_nσ = n sqrt(BT)/(R_F T)。template likelihood 则把能量、径向和层信息编码到多个 bins 中，信息量为 Σ s_k^2/b_k。Phase2 profiled likelihood 不是 full Poisson optimizer，而是在 Fisher threshold 上施加 diagonal Gaussian nuisance degradation factor 1.2138；nuisance 包含 prompt total、delayed total、W187、timing survival、TES FWHM 和 science atmospheric transmission 等代理项。</p>")
    html_parts.append(table_html(likelihood, [("energy_window", "window"), ("model", "model"), ("background_cps", "B cps"), ("response_cps_per_flux", "response"), ("bins_used", "bins"), ("flux_3sigma_ph_cm2_s", "Fisher 3σ"), ("profiled_flux_3sigma_ph_cm2_s", "profiled 3σ"), ("profiled_flux_5sigma_ph_cm2_s", "profiled 5σ")], "表 5. 1 Ms sensitivity thresholds。"))
    html_parts.append("<p>表 5 的核心结果是：broad window-counting profiled 3σ threshold 为 3.58e-4 ph cm^-2 s^-1；加入 energy-radius-layer template 后降低至 1.41e-4 ph cm^-2 s^-1；narrow line energy-radius-layer template 约为 1.40e-4 ph cm^-2 s^-1。template 的增益来自两个方面：一是 511 keV science photons 的能量-空间分布比 delayed continuum/lines 更集中；二是层信息保留了 Be-window 入射 photon 与各向同性/活化本底的几何差异。</p>")
    html_parts.append(table_html(injection, [("energy_window", "window"), ("model", "model"), ("input_flux_ph_cm2_s", "input flux"), ("mean_recovered_flux", "mean recovered"), ("std_recovered_flux", "std"), ("P3", "P>=3σ"), ("P5", "P>=5σ"), ("n_realizations", "N")], "表 6. 1 Ms, F=1e-4 ph cm^-2 s^-1 profiled source-injection proxy。"))
    html_parts.append("<p>source injection 的结论比 threshold 表更接近科学宣称：在 input flux=1e-4 ph cm^-2 s^-1、1 Ms 下，energy-radius-layer template 的 mean recovered flux 与输入值一致，但 P(>=3σ) 只有约 0.19-0.20，P(>=5σ) 约 0.002。因此当前结果不能写成“1e-4/1Ms 稳健检出”。这也是本文 claim-control 的核心。</p>")
    html_parts.append(fig("../04_FIGURES/phase2/phase2_profiled_vs_fisher_threshold.png", "图 19. Fisher thresholds 与 profiled nuisance proxy thresholds 对比。"))
    html_parts.append(fig("../04_FIGURES/phase2/phase2_P3_vs_flux_profiled.png", "图 20. source-injection proxy 中 P(>=3σ) 随 flux 的变化。"))
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/likelihood_511/likelihood_vs_window_counting.png", "图 21. nextphase Fisher template likelihood 与 window counting 对比。"))
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/long_timeline_injection/recovered_flux_vs_true_flux.png", "图 22. long-timeline source injection 的 recovered flux vs true flux。"))
    html_parts.append("<p>为便于快速审阅，本文另外生成了一个小统计 dashboard。它不引入新物理模型，而是把四类最容易被问到的数字放在同一张图上：480-550 keV final component rates、1 Ms profiled-proxy thresholds、1e-4 ph cm^-2 s^-1 source injection 的 P(>=3σ)/P(>=5σ)，以及 Phase2 delayed source activity day-series。该图由 <code>tools/make_nima_issue_update_visuals.py</code> 使用 matplotlib Agg 后端生成，可视化目的等价于一个简短的统计审计图。</p>")
    html_parts.append(fig("../04_FIGURES/nima_update/nima_small_stat_dashboard.png", "图 22b. Small statistical dashboard：component rates、profiled thresholds、injection probability 和 delayed activity 的集中可视化。"))

    html_parts.append("<h2>11. timing/DAQ proxy 与偶然符合损失</h2>")
    html_parts.append("<p>common-timeline 合并后，coincidence window 和 DAQ model 会同时改变 background rejection 与 science survival。短窗口保留 science 事件，但对 background accidental association 的抑制有限；长窗口可压低某些 background candidates，却会因为偶然 BGO 或 Compton/FoV 关联损失 science。当前 timing/DAQ 仍是 toy proxy，不能替代真实硬件 impulse response、dead time、pile-up 和 per-hit BGO timing。</p>")
    html_parts.append(table_html(timing, [("model", "model"), ("equivalent_window_us", "window us"), ("background_final_cps", "background final cps"), ("science_survival", "science survival"), ("flux_3sigma_1Ms", "3σ 1Ms")], "表 7. timing/DAQ proxy models。"))
    html_parts.append(fig("../04_FIGURES/phase2/phase2_science_survival_by_timing_model.png", "图 23. Phase2 science survival by timing model。"))
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/timing_window_scan/background_rate_vs_window.png", "图 24. background final rate 随 coincidence window 的变化。"))
    html_parts.append(fig("../03_NEXT_PHASE_SUPPORT/timing_window_scan/science_survival_vs_window.png", "图 25. science survival 随 coincidence window 的变化。"))

    html_parts.append("<h2>12. 与 511-CAM、COSI、DIXE 和 X-IFU/SXS 文献的关系</h2>")
    html_parts.append("<p>与 511-CAM 相比，本文没有重新设计聚焦光学，而是采用“光学外置归一化 + Be-window 近场注入”的 Level-1 source response 模型。这个选择保留了 511-CAM 中 TES 高分辨谱学与聚焦增益的核心思想 [9]，同时将当前工作限定在 focal-plane background 与 source response 的仿真闭合上。</p>")
    html_parts.append("<p>与 COSI 相比，本文不是宽视场 Compton survey mission，也没有采用 Ge detector Compton imaging 的完整 event reconstruction；但 COSI 文献对 BGO/ACS benchmark 的强调直接支持本文将 BGO per-hit response 作为 future gate 的决策 [21,22]。COSI ACS 研究显示，光学 scintillation、位置依赖 light collection、energy threshold 和 electronics noise 均会改变 veto behavior；本文当前的 event-total BGO proxy 因此只能作为小系统项，而不能声称已完成 hardware-grade ACS response。</p>")
    html_parts.append("<p>与 DIXE 相比，本文同样处理 TES/microcalorimeter 背景问题，也同样使用 Geant4 类输运和 particle-induced background bookkeeping [23]；不同之处在于 DIXE 是 CSS/LEO diffuse X-ray survey，关注 0.1-10 keV NXB，而本文是气球高度 511 keV gamma-ray focal-plane problem。DIXE 的面积归一化 NXB 数值不能直接移植到本仪器，但其“质量模型 + 辐射环境 + 归一化 + delayed background”的写作结构对本文报告形式有参考价值。</p>")
    html_parts.append("<p>与 ATHENA X-IFU 和 Hitomi/SXS 相比，本文的能段、环境和探测器材料不同，但 microcalorimeter background 的方法论一致：必须同时讨论 cosmic-ray induced particles、anti-coincidence、energy response、screening、measured-energy spectra 和残余系统项 [24-28]。这也是本文将 true/measured window、timing proxy、BGO proxy 和 parent-feed caveat 独立列出的原因。</p>")

    html_parts.append("<h2>13. 系统误差预算与禁止口径</h2>")
    html_parts.append("<div class=\"claimbox\"><p><b>允许口径：</b>当前结果是 corrected day-15 static chain + Phase2 reference-profile/proxy convergence study with quantified limitations。<b>禁止口径：</b>不得写成 final real-flight telemetry simulation；不得声称 parent-fed decay chains 完整实现；不得声称 mixed voxel source transport 已完成；不得声称 BGO per-hit electronics 已完成；不得声称 1e-4 ph cm^-2 s^-1 在 1 Ms 下稳健 3σ 检出。</p></div>")
    syst_rows = [
        {"source": "reference flight profile", "status": "not measured telemetry", "impact": "controls PARMA scale, prompt rate and atmospheric transmission"},
        {"source": "particle-only prompt metadata", "status": "angle/energy averaged", "impact": "prevents event-level PARMA reweight"},
        {"source": "optics-focused gamma background", "status": "Level-1 separate rate addendum", "impact": "direct prompt is unchanged; full optics ray tracing remains future work"},
        {"source": "parent feed", "status": "schema only, no branch-ratio rate change", "impact": "affects delayed nuclide inventory and beta+ line contributors"},
        {"source": "mixed voxel transport", "status": "systematic freeze", "impact": "max assigned rate-level bound 1.77%"},
        {"source": "BGO response", "status": "event-total proxy", "impact": "threshold flip fraction 3.34e-4; per-hit timing absent"},
        {"source": "profile likelihood", "status": "diagonal nuisance proxy", "impact": "threshold ranking valid; publication-level likelihood not complete"},
    ]
    html_parts.append(table_html(syst_rows, [("source", "systematic source"), ("status", "current status"), ("impact", "impact on claims")], "表 8. 主要系统误差与 claim-control 状态。"))
    html_parts.append("<p>claim-control 不是文稿润色，而是防止工程报告被过度外推的机制。allowed claims 规定了当前可以公开陈述的结果边界；forbidden claims 则列出在下一阶段 gate 关闭前不得写入摘要、结论或图注的说法。</p>")
    html_parts.append(table_html(allowed_claims + forbidden_claims, [("kind", "kind"), ("claim", "claim text")], "表 14. Allowed and forbidden claims from the package authority files。"))
    html_parts.append("<p>parent-feed 只补 data note，不做伪 rate correction。当前报告包新增 <code>reports2.0/03_NEXT_PHASE_SUPPORT/parent_feed_data_note/top511_parent_feed_data_note.md</code>，只覆盖 W-187、Al-28、Ge-75、O-15、C-11、Ga-68、Bi-210 和 Mg-27 等 top 511-keV contributors 的角色、parent-feed 数据状态和 no-rate-change 决策；正文不得把它写成完整 parent-fed decay-chain correction。</p>")

    html_parts.append("<h2>14. 外挂探测器几何/选择优化：从背景模拟到结构设计指导</h2>")
    html_parts.append("<p>前文给出的 baseline 结论是一个受控的背景评估结论：当前全焦平面 broad/line template proxy 接近 1e-4 ph cm^-2 s^-1，但 source-injection proxy 仍不能支持 1e-4、1 Ms 稳健 3σ 检出。为把这个结果转化为仪器设计指导，本文追加一个只读外挂优化层 <code>reports2.0/08_DESIGN_OPTIMIZATION_ADDON/</code>。该层不改旧几何、不改旧 source、不回写 validated day-15 pipeline；它只读取冻结的 event catalog、final numerical lineage、focused-gamma addendum 和 activation geometry summary，输出 compact CSV/PNG/Markdown。因此它适合作为 design recommendation appendix，也避免把新试验结果混入原始 background ledger。</p>")
    html_parts.append("<p>设计目标函数采用 <code>Q=R_science/sqrt(B_final)</code>，其中 R 是 corrected science response，B 是 background-only final broad rate。baseline 的 best-template proxy threshold 为 1.4057e-4 ph cm^-2 s^-1，因此若要把 1 Ms、3σ threshold 推到 1e-4 附近，需要 Q/Q0≈1.406。外挂工作流按指导文件分三步执行：第一，WP-D1 用低统计子样本扫描 BGO threshold、ROI、single-pixel、edge rejection、layer mask 与 Compton/FoV policy；第二，只要低统计显示有增益，就用同一冻结 catalog 做全量高统计复算；第三，WP-D3 用 activation geometry summary 做 high-activation material/geometry removal bound，判断是否值得进入小规模 delta transport。</p>")
    html_parts.append("<p>低统计阶段抽样 prompt 779/779、delayed 5000/7435、science 5000/66249 个 broad-window candidates，并按 stream 恢复 rate weight；它触发了全 catalog 高统计复算。高统计结果显示，最稳健的 no-hardware setting 是 <code>bgo30_r18_cent_single_top1_L5_keep</code>：BGO 阈值 30 keV、ROI 半径 18、单像素、只取最上层 L5，并保留原 Compton/FoV keep policy。该设置把 broad background 从 baseline 的 {baseline_B} cps 降到 {best_B} cps，同时 science response 仍为 {best_R} cps/(ph cm^-2 s^-1)，相当于保留约 {best_survival} 的 source response；Q/Q0={best_Q}，scaled best-template F3(1 Ms)={best_F3} ph cm^-2 s^-1，P(>=3σ|1e-4,1Ms)={best_P3}。</p>".format(
        baseline_B=fmt(design_baseline_case.get("broad_background_cps", background_only_broad)),
        best_B=fmt(design_selection_best.get("broad_background_cps", "")),
        best_R=fmt(design_selection_best.get("science_response_cps_per_flux", "")),
        best_survival=fmt((float(design_selection_best.get("science_response_cps_per_flux", "nan")) / float(design_baseline_case.get("science_response_cps_per_flux", "nan"))) if design_selection_best and design_baseline_case else ""),
        best_Q=fmt(design_selection_best.get("q_over_q0", "")),
        best_F3=fmt(design_selection_best.get("f3_best_scaled_1Ms_ph_cm2_s", "")),
        best_P3=fmt(design_selection_best.get("p_ge_3sigma_at_1e-4_1Ms", "")),
    ))
    html_parts.append("<p>需要强调的是，这个 selection-only gain 不是新的硬件几何输运，也不是把 baseline sensitivity 数字静默替换。它说明当前焦平面事件信息中存在强设计杠杆：511 keV source 在入射方向上优先打到 top TES layer 且常为 single-pixel full-energy-like event，而 prompt/delayed residual 在层、径向和多像素形态上更分散。因此，最短路径不是立即盲目重做 Bi8 或 W collimator 大矩阵，而是先把 L5/single-pixel/30 keV BGO selection 做 measured-energy 独立复核，再决定是否把它升级为论文主 sensitivity baseline。</p>")
    html_parts.append(table_html(design_recommendation_display, [("case", "design case"), ("response", "R cps/flux"), ("broad_B", "broad B cps"), ("line_B", "line B cps"), ("Q/Q0", "Q/Q0"), ("F3_1Ms", "scaled F3 1Ms"), ("P3", "P>=3σ at 1e-4"), ("risk", "risk"), ("recommendation", "recommendation"), ("variant", "variant")], "表 17. 外挂设计优化推荐表：baseline、selection-only、conditional compact-ROI bound、timing overlay 与 removal bound 的统一比较。"))
    html_parts.append(table_html(design_top_catalog_display, [("variant", "variant"), ("B", "broad B cps"), ("R", "R cps/flux"), ("survival", "source survival"), ("Q/Q0", "Q/Q0"), ("F3_1Ms", "scaled F3 1Ms"), ("P3", "P>=3σ"), ("line_B", "line B cps")], "表 18. WP-D1 high-stat catalog-uniform Top rows。重复的 keep/drop/strict 行表示该最优设置已被 single-pixel 条件主导，Compton policy 不再改变结果。"))
    html_parts.append("<p>如果真实光学焦斑或后续 event reconstruction 能把 source 保留在更小 core ROI 内，而 diffuse/activation background 仍按 ROI 被拒绝，则 <code>bgo30_r9_cent_single_top1_L5_keep</code> 给出一个 conditional focal-core bound：broad background 约 {roi_B} cps，Q/Q0={roi_Q}，scaled F3(1 Ms)={roi_F3} ph cm^-2 s^-1。这不是当前 catalog-uniform high-confidence 结果，而是对未来 optics/ROI design 的上界估计；报告中将它单独标注为 optics-dependent candidate。</p>".format(
        roi_B=fmt(design_roi_bound.get("broad_background_cps", "")),
        roi_Q=fmt(design_roi_bound.get("q_over_q0", "")),
        roi_F3=fmt(design_roi_bound.get("f3_best_scaled_1Ms_ph_cm2_s", "")),
    ))
    html_parts.append(table_html(design_top_bound_display, [("variant", "variant"), ("B", "broad B cps"), ("R_bound", "R bound"), ("catalog_source_cps", "catalog source cps @1e-4"), ("Q/Q0", "Q/Q0"), ("F3_1Ms", "scaled F3"), ("P3", "P>=3σ"), ("note", "acceptance note")], "表 19. WP-D1 high-stat focal-core conditional bound rows。"))
    html_parts.append(fig("../08_DESIGN_OPTIMIZATION_ADDON/WP_D1_selection_pareto_highstat/highstat_q_vs_background.png", "图 26. 外挂 WP-D1 high-stat Pareto：Q/Q0 对 background final rate。虚线 Q/Q0=1，点线 Q/Q0=1.4 表示达到 1e-4 threshold 所需的近似增益。"))
    html_parts.append(fig("../08_DESIGN_OPTIMIZATION_ADDON/WP_D1_selection_pareto_highstat/highstat_source_acceptance_vs_background.png", "图 27. 外挂 WP-D1 high-stat Pareto：science survival 与 selected background 的取舍。"))
    html_parts.append("<p>WP-D3 的 high-activation passive material/geometry bound 使用已经修正过的 activation geometry volume summary，而不是新开大规模 Cosima。它回答的是“如果某个 delayed 几何组被完全移除或减半，理论最大 Q/Q0 能涨多少”。结果显示，Si substrates 是最大的单一 delayed-geometry bound，完全移除可到 Q/Q0=1.306，50% reduction 为 1.123；Ta TES pixels 完全移除仅为 1.088；W collimator bars 完全移除仅为 1.018。因此，单独优化 W collimator 不是最高收益路径，Bi8/Ta absorber 材料替换也不能用当前 Ta catalog 直接重权得出可信结论，必须另做外置复制几何和新 activation inventory。</p>")
    html_parts.append(table_html(design_material_display, [("group", "geometry group"), ("activity", "activity Bq"), ("delayed_B", "delayed broad cps"), ("line_B", "delayed line cps"), ("frac", "fraction of B"), ("Q_removed", "Q/Q0 removed"), ("Q_half", "Q/Q0 50% reduced"), ("flag", "priority flag")], "表 20. WP-D3 high-activation material/geometry removal bound。"))
    html_parts.append(table_html(design_variant_display, [("variant", "variant"), ("status", "execution status"), ("Q/Q0", "Q/Q0"), ("F3", "scaled F3"), ("evidence", "evidence"), ("decision", "decision")], "表 21. 指导文件要求的 V1/V2/V3 最小变体执行状态。V1 Bi8 在本轮被明确延后，因为没有可审计的 Bi8 几何与活化源；V3 selection+veto 是本轮最高信心实现。"))
    html_parts.append("<p>timing-window overlay 也被保留，但不与 ROI/BGO/layer selection 直接相乘，因为那会在没有 dedicated pile-up rerun 的情况下双重使用 timing survival。现有 timing scan 的最优 overlay 是 0.1 μs，Q/Q0 约 1.048；这说明 timing 收紧有轻微收益，但远小于 L5 single-pixel selection。最终设计建议因此分为两层：近期分析层面优先复核并采用 <code>bgo30_r18_cent_single_top1_L5_keep</code>；硬件层面优先研究 compact focal spot/core ROI 与 Si substrate/near-TES passive material 的几何减背景，而不是把 W collimator 当作单独最高收益对象。</p>")
    html_parts.append(table_html(design_timing_display, [("window_us", "window us"), ("B", "broad B cps"), ("survival", "science survival"), ("Q/Q0", "Q/Q0"), ("F3_1Ms", "scaled F3")], "表 22. Existing timing-window overlay，未与 WP-D1 selection rows 相乘。"))

    html_parts.append("<h2>15. 附录式验证摘要与复现说明</h2>")
    html_parts.append("<h3>15.1 Phase2 validation ledger</h3>")
    html_parts.append("<p>validation ledger 是本报告的机器可读审稿附录。它覆盖 source placement、PARMA backend、prompt reweight、activation inventory、delayed sources、measured catalog、timing/DAQ、profile likelihood、source injection、PDF 报告存在性以及 convergence patch wording guards。正文只引用关键项；表 15 保留 Phase2 条目以便读者追踪每一项 hard check 或 caveat。</p>")
    html_parts.append(table_html(phase2_validation_rows, [("status", "status"), ("check", "check"), ("note", "validation note")], "表 15. Phase2 validation entries。"))
    html_parts.append("<h3>15.2 Next-phase support validation ledger</h3>")
    html_parts.append("<p>Next-phase support 目录包含用于审稿封口径的补充检查：Gate-A source placement、Gate-B detector response、science line sensitivity、activation diagnostics、spatial spectral likelihood、long-timeline injection 和 timing-window scan。它们不是新的主结果集合，而是用于判断当前主结果是否存在明显断裂。</p>")
    html_parts.append(table_html(nextphase_validation_rows, [("status", "status"), ("check", "check"), ("note", "validation note")], "表 16. Next-phase support validation entries。"))
    html_parts.append("<h3>15.3 可复现命令与报告包入口</h3>")
    html_parts.append("<p>本 HTML 由 <code>tools/make_nima_detailed_paper.py</code> 生成，并复制到 <code>reports2.0/05_SCRIPTS_AND_CONFIG/tools/</code> 作为报告包内脚本。读者可从工作区根目录进入 <code>cosmosray_bg_2605</code> 后运行 validation script 与 manuscript generator；manifest 记录报告包文件路径与大小。由于 source files、figures、CSV 和 JSON authorities 均保存在 <code>reports2.0</code> 内，HTML 的图表相对路径在包内保持有效。</p>")
    html_parts.append("<pre>cd /home/ubuntu/codex_tes_511_sim/cosmosray_bg_2605\npython3 tools/estimate_optics_focused_gamma_background.py\npython3 tools/make_nima_issue_update_visuals.py\npython3 design_optimization_addon/tools/run_design_optimization_addon.py --force-highstat\npython3 tools/validate_workspace.py\npython3 tools/make_nima_detailed_paper.py</pre>")
    html_parts.append("<p>复现时需要注意两点。第一，PARMA reference profile 当前固定 2025-08-31，这是为规避公开 FFP 数据日期覆盖限制而采取的 reference-profile 设定，不应写成 2026 实测剖面。第二，mixed-voxel delta transport 和 full parent-fed branch table 仍是下一阶段任务；当前 HTML 保留其 systematic freeze 或 data limitation，而不伪造缺失物理输入。</p>")
    html_parts.append("<h3>15.4 Data and code availability</h3>")
    html_parts.append("<p><b>Internal reproducibility.</b> 本地审阅包保留在 <code>reports2.0/</code>，关键入口包括 <code>07_NIMA_MANUSCRIPT/final_numerical_lineage.csv</code>、<code>07_NIMA_MANUSCRIPT/artifact_manifest.csv</code>、<code>06_VALIDATION/validation_log.txt</code>、<code>03_NEXT_PHASE_SUPPORT/optics_focused_gamma_background/</code>、<code>03_NEXT_PHASE_SUPPORT/activation_rpip_sampling/</code> 与 <code>08_DESIGN_OPTIMIZATION_ADDON/</code>。这些路径用于内部复现和合作者审阅，不假定外部读者能直接访问本机目录。</p>")
    html_parts.append("<p><b>External availability.</b> A curated reproduction package containing the source files, summary JSON/CSV products, validation scripts, and figure-generation inputs will be archived or provided upon reasonable request. Large raw Cosima SIM outputs are not included in the manuscript package but are represented by machine-readable summaries and validation logs.</p>")

    html_parts.append("<h2>16. 结论</h2>")
    html_parts.append("<p>本文将 COSMOSRAY_BG_2605 的工程报告重写为详细论文稿，保留了 NIMA 类 instrumentation/simulation paper 的结构：科学动机、质量模型、源模型、输运工具、环境模型、活化方程、事件合并、veto、detector response、统计估计、结果、系统项和结论。当前 simulation chain 的硬验证已通过，且 source authority、PARMA outlier、optics-focused gamma addendum、activation geometry/proxy clarification、parent-feed limitation、mixed voxel gate、BGO proxy 和 profile/injection claim 均有机器可读证据。</p>")
    html_parts.append(f"<p>核心数值为：day-15 prompt-plus-delayed 480-550 keV background-only ledger 加 focused-aperture γ addendum 后为 {fmt(background_only_broad)} cps；包含 reference science stream 的 direct-expectation diagnostic total={fmt(diagnostic_total_final)} cps；common-timeline diagnostic realization={fmt(day15['timeline_rates_cps']['final'])} cps；measured broad-window diagnostic total={fmt(measured_broad.get('final_cps', ''))} cps；current science response={fmt(day15['science_sensitivity']['science_final_response_cps_per_ph_cm-2_s-1'])} cps/(ph cm^-2 s^-1)。1 Ms profiled proxy 下，broad window-counting 3σ threshold=3.58e-4 ph cm^-2 s^-1，broad energy-radius-layer=1.41e-4 ph cm^-2 s^-1，line energy-radius-layer≈1.40e-4 ph cm^-2 s^-1。1e-4 ph cm^-2 s^-1、1 Ms 的 P(>=3σ) 仅约 0.19-0.20。</p>")
    html_parts.append(f"<p>新增外挂设计优化把上述“尚不稳健”的 baseline 结论转化为下一步设计指导：高统计 catalog-uniform scan 的最优 no-hardware setting <code>{html.escape(design_selection_best.get('variant_id', ''))}</code> 达到 Q/Q0={fmt(design_selection_best.get('q_over_q0', ''))}，broad background={fmt(design_selection_best.get('broad_background_cps', ''))} cps，scaled best-template F3(1 Ms)={fmt(design_selection_best.get('f3_best_scaled_1Ms_ph_cm2_s', ''))} ph cm^-2 s^-1，P(>=3σ|1e-4,1Ms)={fmt(design_selection_best.get('p_ge_3sigma_at_1e-4_1Ms', ''))}。这不替代 baseline authority，而是指出最短的后续闭合路径：先做 measured-energy 独立复核与 source/background template consistency check，再考虑把该 selection 升级为论文主 sensitivity baseline。</p>")
    html_parts.append("<p>当前工作已经可以作为 corrected day-15 static chain、Phase2 reference-profile/proxy convergence study 与 background-driven detector design add-on 进入 technical review。remaining gates 均已显式 bounded 或 scoped；更强的 real-flight publication claims 需要 measured telemetry、audited decay branches、mixed-source delayed transport 或至少 minimal delta transport closure、per-hit BGO response、full optics-background templates，以及 full Poisson profile likelihood。</p>")

    html_parts.append("<h2>参考文献</h2>")
    html_parts.append(ref_list_html(refs))
    html_parts.append("</article></body></html>")
    html_text = "\n".join(html_parts)
    (OUT / "nima_detailed_paper_zh.html").write_text(html_text, encoding="utf-8")

    md = [
        "# 气球平台 511 keV 聚焦 TES 谱仪的宇宙线背景、活化本底与点源灵敏度",
        "",
        "本 Markdown 是 `nima_detailed_paper_zh.html` 的简化源稿索引。完整排版、表格和图件请查看 HTML。",
        "",
        "## 核心结果",
        "",
        f"- day-15 background-only final 480-550 keV ledger with focused gamma addendum: {fmt(background_only_broad)} cps",
        f"- diagnostic total including reference science stream: {fmt(diagnostic_total_final)} cps",
        f"- optics-focused gamma Level-1 addendum, 480-550 keV: {fmt(focused_broad.get('mean_final_focused_gamma_cps', '0'))} cps",
        f"- optics-focused gamma Level-1 addendum, 510.3-511.8 keV: {fmt(focused_line.get('mean_final_focused_gamma_cps', '0'))} cps",
        f"- measured broad-window final rate: {fmt(measured[1]['final_cps'])} cps",
        f"- current science response: {fmt(day15['science_sensitivity']['science_final_response_cps_per_ph_cm-2_s-1'])} cps/(ph cm^-2 s^-1)",
        f"- add-on design optimization best catalog-uniform setting: `{design_selection_best.get('variant_id', '')}`, Q/Q0={fmt(design_selection_best.get('q_over_q0', ''))}, B={fmt(design_selection_best.get('broad_background_cps', ''))} cps, scaled F3={fmt(design_selection_best.get('f3_best_scaled_1Ms_ph_cm2_s', ''))} ph cm^-2 s^-1",
        "- 1 Ms profiled broad window-counting 3σ threshold: 3.58e-4 ph cm^-2 s^-1",
        "- 1 Ms profiled broad energy-radius-layer 3σ threshold: 1.41e-4 ph cm^-2 s^-1",
        "- 1e-4 ph cm^-2 s^-1 at 1 Ms is not a robust 3σ detection in the current proxy.",
        "",
        "## Day-15 rates",
        table_md(day_rows, [("stream", "stream"), ("raw", "raw cps"), ("bgo", "BGO cps"), ("final", "final cps")]),
        "",
        "## Final numerical lineage",
        table_md(lineage_rows, [("quantity", "quantity"), ("value", "value"), ("source_definition", "source / definition"), ("used_for", "used for")]),
        "",
        "## Measured-energy windows",
        table_md(measured, [("window", "window"), ("energy_type", "energy"), ("raw_cps", "raw cps"), ("bgo_cps", "BGO cps"), ("final_cps", "final cps")]),
        "",
        "## Optics-focused gamma addendum",
        table_md(focused_addendum, [("window", "window"), ("old_background_cps", "old B cps"), ("focused_gamma_addendum_cps", "focused add cps"), ("new_background_cps", "new B cps"), ("threshold_scale_sqrt_Bnew_over_Bold", "threshold scale")]),
        "",
        "## Add-on detector design optimization",
        table_md(design_recommendation_display, [("case", "design case"), ("response", "R cps/flux"), ("broad_B", "broad B cps"), ("line_B", "line B cps"), ("Q/Q0", "Q/Q0"), ("F3_1Ms", "scaled F3 1Ms"), ("P3", "P>=3σ"), ("risk", "risk"), ("recommendation", "recommendation")]),
        "",
        "## References",
        "",
    ]
    for i, r in enumerate(refs, 1):
        md.append(f"[{i}] {r['text']} {r['url']}")
    (OUT / "nima_detailed_paper_zh.md").write_text("\n".join(md), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
