#!/usr/bin/env python3
"""Package the v3p5 full-stat performance and W2 background closure report."""

from __future__ import annotations

import csv
import html
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LABEL = "fullstat_v2"
OUT = ROOT / "outputs" / "reports" / "v3p5_fullstat_performance_w2_closure_20260612"

STEP02 = (
    ROOT
    / "stepwise_maintenance"
    / "step02_raw_background_simulation"
    / "outputs_v3p5_centerfinger_fullstat_v2"
    / "step02_v3p5_centerfinger_fullstat_v2_summary.json"
)
STEP05 = (
    ROOT
    / "stepwise_maintenance"
    / "step05_veto_time_axis"
    / "outputs_v3p5_centerfinger_fullstat_v2_l1"
    / "step05_v3p5_centerfinger_l1_response_summary.json"
)
STEP06 = (
    ROOT
    / "stepwise_maintenance"
    / "step06_mission_time_variation"
    / "outputs_v3p5_centerfinger_fullstat_v2"
    / "step06_v3p5_centerfinger_fullstat_v2_summary.json"
)
STEP07 = (
    ROOT
    / "stepwise_maintenance"
    / "step07_source_cases"
    / "outputs_v3p5_centerfinger_fullstat_v2"
    / "source_case_summary.json"
)
STEP08 = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / "outputs_v3p5_centerfinger_fullstat_v2"
    / "step08_v3p5_centerfinger_time_dependent_summary.json"
)
PERF = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / "outputs"
    / "performance_curve_comparison_1Ms"
    / "performance_curve_comparison_1Ms_summary.json"
)
W2_BREAKDOWN = (
    ROOT
    / "stepwise_maintenance"
    / "step08_significance"
    / "outputs_v3p5_centerfinger_fullstat_v2"
    / "w2_background_source_breakdown"
    / "w2_background_source_breakdown_summary.json"
)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(value: Any, ndigits: int = 6) -> str:
    if value is None or value == "":
        return ""
    val = float(value)
    if val == 0.0:
        return "0"
    if abs(val) < 1.0e-3 or abs(val) >= 1.0e5:
        return f"{val:.{ndigits}e}"
    return f"{val:.{ndigits}g}"


def pct(value: Any) -> str:
    return f"{100.0 * float(value):.1f}%"


def expect_pass(name: str, payload: dict[str, Any], problems: list[str]) -> None:
    status = str(payload.get("status", ""))
    if not status.startswith("PASS"):
        problems.append(f"{name} status is not PASS: {status}")


def expect_label(name: str, payload: dict[str, Any], problems: list[str]) -> None:
    label = payload.get("statistics_label")
    if label != LABEL:
        problems.append(f"{name} statistics_label is {label!r}, expected {LABEL!r}")


def copy_file(src: Path, dst: Path, copied: list[dict[str, str]]) -> None:
    if not src.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.append({"source": rel(src), "report_copy": rel(dst)})


def collect_artifacts(payload: dict[str, Any]) -> list[dict[str, str]]:
    copied: list[dict[str, str]] = []
    assets = OUT / "assets"
    summaries = OUT / "summaries"
    tables = OUT / "tables"

    for src in [
        STEP02,
        STEP02.with_suffix(".md"),
        STEP05,
        STEP05.with_suffix(".md"),
        STEP06,
        STEP06.parent / "README.md",
        STEP07,
        STEP07.parent / "README.md",
        STEP08,
        STEP08.parent / "step08_v3p5_centerfinger_time_dependent.md",
        PERF,
        PERF.parent / "performance_curve_comparison_1Ms.md",
        W2_BREAKDOWN,
        W2_BREAKDOWN.parent / "w2_background_source_breakdown.md",
    ]:
        copy_file(src, summaries / src.name, copied)

    for src in [
        PERF.parent / "performance_curve_comparison_1Ms.png",
        W2_BREAKDOWN.parent / "w2_background_source_breakdown.png",
    ]:
        copy_file(src, assets / src.name, copied)

    for src in [
        PERF.parent / "performance_curve_comparison_1Ms.csv",
        PERF.parent / "cam511_fig11_digitized_points.csv",
        W2_BREAKDOWN.parent / "w2_background_components.csv",
        W2_BREAKDOWN.parent / "w2_background_streams.csv",
        W2_BREAKDOWN.parent / "w2_delayed_nuclides.csv",
        W2_BREAKDOWN.parent / "w2_delayed_source_volumes.csv",
        W2_BREAKDOWN.parent / "w2_background_selected_events.csv",
        STEP05.parent / "step05_v3p5_centerfinger_l1_rates.csv",
        STEP06.parent / "background_time_variation.csv",
        STEP07.parent / "source_case_rates.csv",
        STEP08.parent / "cumulative_significance_by_case.csv",
        STEP08.parent / "t3_t5_summary.csv",
    ]:
        copy_file(src, tables / src.name, copied)

    payload["copied_artifacts"] = copied
    return copied


def row_for_case(rows: list[dict[str, str]], case_id: str, exposure_s: float = 1.0e6) -> dict[str, str]:
    for row in rows:
        if row.get("case_id") == case_id and abs(float(row.get("exposure_s", 0.0)) - exposure_s) < 1.0e-6:
            return row
    return {}


def build_payload() -> dict[str, Any]:
    step02 = load_json(STEP02)
    step05 = load_json(STEP05)
    step06 = load_json(STEP06)
    step07 = load_json(STEP07)
    step08 = load_json(STEP08)
    perf = load_json(PERF)
    w2_breakdown = load_json(W2_BREAKDOWN)
    perf_rows = read_csv(PERF.parent / "performance_curve_comparison_1Ms.csv")
    delayed_nuclide_rows = read_csv(W2_BREAKDOWN.parent / "w2_delayed_nuclides.csv")
    stream_rows = read_csv(W2_BREAKDOWN.parent / "w2_background_streams.csv")

    problems: list[str] = []
    for name, item in [
        ("Step02", step02),
        ("Step05", step05),
        ("Step06", step06),
        ("Step07", step07),
        ("Step08", step08),
        ("performance comparison", perf),
        ("W2 source breakdown", w2_breakdown),
    ]:
        expect_pass(name, item, problems)
    for name, item in [("Step02", step02), ("Step05", step05), ("Step06", step06), ("W2 source breakdown", w2_breakdown)]:
        expect_label(name, item, problems)

    if step02["instant_transport"]["passes"] != step02["instant_transport"]["jobs"]:
        problems.append("instant transport has failed jobs")
    if step02["buildup_transport"]["passes"] != step02["buildup_transport"]["jobs"]:
        problems.append("buildup transport has failed jobs")
    delayed = step02["delayed_transport"]
    if int(delayed["SE"]) != int(delayed["ID"]):
        problems.append("delayed transport SE and ID counts differ")
    if int(delayed["SE"]) < 1_000_000:
        problems.append(f"delayed transport has only {delayed['SE']} events; expected at least 1000000")

    step05_w2 = step05["windows"]["w2_510p58_511p42"]
    w2_phys = step05_w2["physical_reference_flux"]
    step06_checks = step06["checks"]
    step07_checks = step07["checks"]
    step08_checks = step08["checks"]

    breakdown_rate = float(w2_breakdown["total_rate_hz"])
    step05_background = float(w2_phys["background_cps"])
    if abs(breakdown_rate - step05_background) > max(1.0e-10, 1.0e-6 * step05_background):
        problems.append(
            f"W2 breakdown total {breakdown_rate:.12g} cps does not match Step05 background {step05_background:.12g} cps"
        )

    for key in ["511CAM_Fig11_digitized_511keV", "SPI_511keV_1Ms_public", "COSI_SMEX_scaled_to_1Ms", "v3p5_W2"]:
        if key not in perf.get("one_Ms", {}):
            problems.append(f"performance comparison is missing {key}")

    top_components = w2_breakdown.get("top_components", [])
    perf_1ms = {
        "v3p5_W2": row_for_case(perf_rows, "v3p5_W2"),
        "DEMO2_W2_spot_r90": row_for_case(perf_rows, "DEMO2_W2_spot_r90"),
        "DEMO2_W2_line": row_for_case(perf_rows, "DEMO2_W2_line"),
        "511CAM": row_for_case(perf_rows, "511CAM_Fig11_digitized_511keV"),
        "SPI": row_for_case(perf_rows, "SPI_511keV_1Ms_public"),
        "COSI": row_for_case(perf_rows, "COSI_SMEX_scaled_to_1Ms"),
    }

    payload: dict[str, Any] = {
        "status": "PASS_V3P5_FULLSTAT_PERFORMANCE_W2_CLOSURE" if not problems else "FAIL_V3P5_FULLSTAT_PERFORMANCE_W2_CLOSURE",
        "statistics_label": LABEL,
        "claim_level": "full-stat v3p5 center-finger L1 rate-level closure with external 1 Ms benchmark markers",
        "problems": problems,
        "headline": {
            "step02_instant_generated": step02["instant_transport"]["events_generated"],
            "step02_buildup_generated": step02["buildup_transport"]["events_generated"],
            "step02_delayed_SE": delayed["SE"],
            "step02_delayed_TE_s": delayed["TE_s"],
            "fixed_source_activity_Bq": step02["fixed_decay_source"]["total_activity_Bq"],
            "w2_step05_background_cps": step05_background,
            "w2_step05_signal_cps_at_1e_4": w2_phys["signal_cps_at_reference_flux"],
            "w2_step05_final_background_events": w2_phys["low_stat_final_background_events"],
            "w2_step06_mission_mean_background_cps": step06_checks["w2_dt_weighted_background_final_cps"],
            "w2_step06_mission_mean_signal_cps_at_1e_4": step06_checks["w2_dt_weighted_science_final_cps_at_ref_flux"],
            "w2_step07_response_cps_per_ph_cm2_s": step07_checks["w2_response_cps_per_ph_cm2_s"],
            "w2_step08_Z20d_at_1e_4": step08_checks["A_reference_w2_Z20d_time_dependent"],
            "w2_step08_T3_day": step08_checks["A_reference_w2_T3_day"],
            "w2_step08_flux_3sigma_20d_ph_cm2_s": step08_checks["A_reference_w2_flux_3sigma_20d_ph_cm2_s"],
            "w2_flux_3sigma_1Ms_ph_cm2_s": float(perf_1ms["v3p5_W2"].get("flux_3sigma_ph_cm2_s", "nan")),
            "w2_top_background_component": top_components[0] if top_components else {},
            "w2_stream_split": stream_rows,
            "w2_delayed_top_nuclide": delayed_nuclide_rows[0] if delayed_nuclide_rows else {},
        },
        "performance_1Ms": perf_1ms,
        "external_benchmarks": {
            "511CAM": {
                "source": "511-CAM paper Fig.11; local rendered /tmp/511cam_page16-16.png; figure-derived digitization",
                "url": "https://arxiv.org/abs/2206.14652",
            },
            "SPI": {
                "source": "published SPI 3sigma 1e6 s 511 keV narrow-line sensitivity marker",
                "url": "https://arxiv.org/abs/astro-ph/0310793",
            },
            "COSI": {
                "source": "Tomsick et al. 2023 COSI mission paper; 2-year narrow-line sensitivity sqrt-time scaled to 1 Ms",
                "url": "https://arxiv.org/abs/2308.12362",
            },
        },
        "inputs": {
            "step02": rel(STEP02),
            "step05": rel(STEP05),
            "step06": rel(STEP06),
            "step07": rel(STEP07),
            "step08": rel(STEP08),
            "performance": rel(PERF),
            "w2_breakdown": rel(W2_BREAKDOWN),
        },
        "chart_map": [
            {
                "section": "1 Ms performance comparison",
                "artifact": "assets/performance_curve_comparison_1Ms.png",
                "family": "uncertainty and benchmark / log exposure curve",
            "supported_claim": "v3p5 W2 full-stat sensitivity is compared against legacy pre-fix DEMO2, 511-CAM, SPI, and COSI 1 Ms markers.",
            },
            {
                "section": "W2 background source mix",
                "artifact": "assets/w2_background_source_breakdown.png",
                "family": "composition / ranked bars",
                "supported_claim": "W2 final background is decomposed by selected-event stream, delayed nuclide, and source-volume metadata.",
            },
        ],
        "outputs": {
            "report_markdown": rel(OUT / "v3p5_fullstat_performance_w2_closure_report.md"),
            "report_html": rel(OUT / "report.html"),
            "summary_json": rel(OUT / "v3p5_fullstat_performance_w2_closure_summary.json"),
        },
        "limitations": [
            "This is an L1 rate-level full-stat closure; it is not a profile-likelihood or final paper-facing spatial analysis.",
            "The delayed source still uses the legacy axisymmetric RadialProfileBeam compression for v3p5.",
            "511-CAM is figure-derived from Fig.11; COSI is sqrt-time scaled from a published 2-year sensitivity and is a benchmark marker, not an observing-strategy equivalence.",
            "Flux limits use Gaussian S/sqrt(B)=3 scaling for comparison consistency.",
        ],
    }
    collect_artifacts(payload)
    return payload


def markdown(payload: dict[str, Any]) -> str:
    h = payload["headline"]
    perf = payload["performance_1Ms"]
    top = h["w2_top_background_component"]
    delayed_top = h["w2_delayed_top_nuclide"]
    lines = [
        "# v3p5 Full-Stat Performance and W2 Background Closure",
        "",
        f"Status: `{payload['status']}`.",
        "",
        f"Claim level: {payload['claim_level']}.",
        "",
        "## Technical Summary",
        "",
        f"- Full-stat Step02 prompt and buildup transport each generated `{h['step02_instant_generated']}` / `{h['step02_buildup_generated']}` particles; delayed transport stored `SE={h['step02_delayed_SE']}` over `TE={fmt(h['step02_delayed_TE_s'])} s`.",
        f"- W2 final background is `{fmt(h['w2_step05_background_cps'])} cps` with signal `{fmt(h['w2_step05_signal_cps_at_1e_4'])} cps` at `1e-4 ph cm^-2 s^-1`; the mission-mean Step06 fold is `{fmt(h['w2_step06_mission_mean_background_cps'])}` / `{fmt(h['w2_step06_mission_mean_signal_cps_at_1e_4'])} cps`.",
        f"- The Step08 time-dependent W2 result is `Z20d={fmt(h['w2_step08_Z20d_at_1e_4'])}`, `T3={fmt(h['w2_step08_T3_day'])} day`, and `F_3sigma(20d)={fmt(h['w2_step08_flux_3sigma_20d_ph_cm2_s'])} ph cm^-2 s^-1`.",
        f"- The 1 Ms comparison gives v3p5 W2 `F_3sigma={fmt(h['w2_flux_3sigma_1Ms_ph_cm2_s'])} ph cm^-2 s^-1`; external markers are included for 511-CAM, SPI, and COSI with source notes in the JSON.",
        "",
        "## Key Findings With Visual Evidence",
        "",
        "The performance curve places the full-stat v3p5 W2 point against legacy pre-fix DEMO2 headline cases and public instrument markers at 1 Ms. The DEMO2 points are historical markers under review after the reproduced x8.0116 delayed-source normalization issue; the external points are benchmarks with different assumptions.",
        "",
        "![1 Ms performance comparison](assets/performance_curve_comparison_1Ms.png)",
        "",
        "| case | 1 Ms 3sigma flux ph cm^-2 s^-1 | method |",
        "| --- | ---: | --- |",
    ]
    for key in ["v3p5_W2", "DEMO2_W2_spot_r90", "DEMO2_W2_line", "511CAM", "SPI", "COSI"]:
        row = perf.get(key, {})
        lines.append(f"| {row.get('label', key)} | {fmt(row.get('flux_3sigma_ph_cm2_s', ''))} | {row.get('method', '')} |")
    lines.extend(
        [
            "",
            "## Benchmark Sources",
            "",
            "- DEMO2/new_geo_re comparison values come from legacy pre-fix `core_md/README.md` and `core_md/VALIDATION.md` records. They are retained as provenance only after the reproduced x8.0116 delayed-source normalization issue; the legacy `stepwise_3sigma_headline_results.png` file named in older notes is not present in this checkout.",
            "- 511-CAM is digitized from Fig.11 of arXiv:2206.14652 and treated as a figure-derived 1 Ms marker.",
            "- INTEGRAL/SPI uses the published 3sigma, 10^6 s, 511 keV narrow-line sensitivity from arXiv:astro-ph/0310793.",
            "- COSI uses the published 2-year 3sigma narrow-line sensitivity from arXiv:2308.12362, sqrt-time scaled to 1 Ms for this benchmark plot.",
            "",
            "The W2 background-source breakdown reuses the same Step05 W2, active-veto, and side-entry Compton/FoV selection. The rate total is checked against the Step05 W2 background, so the decomposition is tied to the sensitivity calculation rather than a separate event filter.",
            "",
            "![W2 background source breakdown](assets/w2_background_source_breakdown.png)",
            "",
            "## W2 Background Driver",
            "",
            f"The largest selected component is `{top.get('component', 'n/a')}` with `{top.get('events', '')}` selected events, `{fmt(top.get('rate_hz', ''))} cps`, and `{pct(top.get('fraction', 0.0)) if top else ''}` of the W2 final background rate.",
            f"The delayed slice is small; within delayed-only W2 events, `{delayed_top.get('primary', 'n/a')}` is the largest nuclide with `{delayed_top.get('events', '')}` events and `{pct(delayed_top.get('fraction', 0.0)) if delayed_top else ''}` of delayed W2 events.",
            "",
            "## Scope, Data, And Metric Definitions",
            "",
            "- W2 is `510.58-511.42 keV`, i.e. `511 +/- 420 eV`.",
            "- Reference flux is `1e-4 ph cm^-2 s^-1` unless a row explicitly reports a 3sigma flux limit.",
            "- Full-stat label is `fullstat_v2`.",
            "- 1 Ms means `1,000,000 s` exposure.",
            "- Background and signal rates are Step05 L1 side-entry Compton/FoV selected rates, folded through Step06/07/08 for mission-time significance.",
            "",
            "## Methodology",
            "",
            "Step02 produces the full-stat prompt, buildup, fixed delayed source, and delayed transport. Step05 parses prompt, delayed, and focused EventList detector outputs with the v3p5 active-veto and side-entry Compton/FoV selection. Step06 applies the mission time axis; Step07 builds source cases; Step08 computes time-dependent counting significance with analytic accidental-live factors. The performance comparison converts the Step08 cumulative significance to 3sigma flux limits at fixed exposures and adds public 1 Ms markers.",
            "",
            "## Limitations And Robustness Checks",
            "",
        ]
    )
    for item in payload["limitations"]:
        lines.append(f"- {item}")
    if payload["problems"]:
        lines.extend(["", "## Audit Problems", ""])
        for item in payload["problems"]:
            lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Recommended Next Steps",
            "",
            "- Replace the delayed-source RadialProfileBeam compression with exact-position sampling for paper-facing v3p5 numbers.",
            "- Promote the comparison to a spatial/profile-likelihood analysis once selection-consistent spatial cuts are available.",
            "- Re-digitize or table-source external benchmark curves before any publication figure.",
            "",
            "## Further Questions",
            "",
            "- How much does exact-position delayed sampling move the W2 background mix?",
            "- Does a selection-consistent spatial cut improve v3p5 W2 beyond the current L1 rate-level estimate?",
            "- Which external benchmark definitions should be normalized for field of view, line width, and observing strategy in a publication table?",
            "",
            "## Artifact Index",
            "",
            f"- summary JSON: `{payload['outputs']['summary_json']}`",
            f"- HTML report: `{payload['outputs']['report_html']}`",
            "- copied summaries: `summaries/`",
            "- copied tables: `tables/`",
            "- copied figures: `assets/`",
            "",
        ]
    )
    return "\n".join(lines)


def html_table(rows: list[list[str]]) -> str:
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>")
    return "\n".join(body)


def html_report(payload: dict[str, Any]) -> str:
    h = payload["headline"]
    top = h["w2_top_background_component"]
    delayed_top = h["w2_delayed_top_nuclide"]
    perf = payload["performance_1Ms"]
    perf_rows = [
        [perf.get(key, {}).get("label", key), fmt(perf.get(key, {}).get("flux_3sigma_ph_cm2_s", "")), perf.get(key, {}).get("method", "")]
        for key in ["v3p5_W2", "DEMO2_W2_spot_r90", "DEMO2_W2_line", "511CAM", "SPI", "COSI"]
    ]
    limitation_items = "\n".join(f"<li>{html.escape(item)}</li>" for item in payload["limitations"])
    problem_block = ""
    if payload["problems"]:
        problems = "\n".join(f"<li>{html.escape(item)}</li>" for item in payload["problems"])
        problem_block = f"<section><h2>Audit Problems</h2><ul>{problems}</ul></section>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>v3p5 Full-Stat Performance and W2 Background Closure</title>
  <style>
    :root {{
      --ink: #1f2430;
      --muted: #667085;
      --line: #d9dee8;
      --panel: #ffffff;
      --bg: #f7f8fb;
      --blue: #2e4780;
      --gold: #736422;
    }}
    body {{
      margin: 0;
      font-family: Inter, Segoe UI, Arial, sans-serif;
      color: var(--ink);
      background: var(--bg);
      line-height: 1.55;
    }}
    main {{
      max-width: 1040px;
      margin: 0 auto;
      padding: 36px 24px 56px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 30px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    h2 {{
      margin-top: 34px;
      padding-top: 18px;
      border-top: 1px solid var(--line);
      font-size: 20px;
      letter-spacing: 0;
    }}
    p, li {{
      font-size: 15px;
    }}
    .status {{
      color: var(--muted);
      font-family: SFMono-Regular, Consolas, monospace;
      font-size: 13px;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 22px 0 8px;
    }}
    .metric {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 5px;
    }}
    .metric strong {{
      font-size: 18px;
      font-family: SFMono-Regular, Consolas, monospace;
    }}
    figure {{
      margin: 22px 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    figure img {{
      width: 100%;
      height: auto;
      display: block;
    }}
    figcaption {{
      color: var(--muted);
      font-size: 13px;
      margin-top: 10px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
      margin: 16px 0;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 10px;
      text-align: left;
      vertical-align: top;
      font-size: 13px;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
    }}
    a {{
      color: var(--blue);
    }}
    code {{
      font-family: SFMono-Regular, Consolas, monospace;
      font-size: 0.95em;
    }}
    @media (max-width: 760px) {{
      main {{ padding: 24px 14px 40px; }}
      .metric-grid {{ grid-template-columns: 1fr 1fr; }}
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
<main>
  <h1>v3p5 Full-Stat Performance and W2 Background Closure</h1>
  <div class="status">{html.escape(payload['status'])} | {html.escape(payload['statistics_label'])}</div>

  <section>
    <h2>Technical Summary</h2>
    <p>The full-stat v3p5 center-finger chain closes through Step02, Step05, Step06, Step07, Step08, the 1 Ms benchmark comparison, and the W2 background-source decomposition. This is an L1 rate-level result: it is suitable for branch comparison and next-step planning, but still carries the delayed-source compression and non-profile-likelihood limitations.</p>
    <div class="metric-grid">
      <div class="metric"><span>W2 background</span><strong>{fmt(h['w2_step05_background_cps'])}</strong> cps</div>
      <div class="metric"><span>W2 signal at 1e-4</span><strong>{fmt(h['w2_step05_signal_cps_at_1e_4'])}</strong> cps</div>
      <div class="metric"><span>Step08 Z20d</span><strong>{fmt(h['w2_step08_Z20d_at_1e_4'])}</strong></div>
      <div class="metric"><span>1 Ms F3sigma</span><strong>{fmt(h['w2_flux_3sigma_1Ms_ph_cm2_s'])}</strong></div>
    </div>
  </section>

  <section>
    <h2>1 Ms Performance Comparison</h2>
    <p>The chart compares the full-stat v3p5 W2 curve with legacy pre-fix DEMO2 cases and public benchmark markers. The DEMO2 markers are retained as historical provenance after the reproduced x8.0116 delayed-source normalization issue. The 511-CAM point is figure-derived, SPI is a published 1e6 s marker, and COSI is sqrt-time scaled from a published 2-year sensitivity.</p>
    <figure>
      <img src="assets/performance_curve_comparison_1Ms.png" alt="1 Ms 3sigma performance comparison">
      <figcaption>Gaussian S/sqrt(B)=3 flux limits; external points are comparison markers, not identical observing strategies.</figcaption>
    </figure>
    <table>
      <thead><tr><th>Case</th><th>1 Ms 3sigma flux</th><th>Method</th></tr></thead>
      <tbody>{html_table(perf_rows)}</tbody>
    </table>
  </section>

  <section>
    <h2>W2 Background Source Mix</h2>
    <p>The decomposition recomputes the same W2 active-veto and side-entry Compton/FoV selection used by Step05. The leading selected component is <code>{html.escape(str(top.get('component', 'n/a')))}</code>, with {html.escape(str(top.get('events', '')))} events and {fmt(top.get('rate_hz', ''))} cps. The delayed slice is small; within delayed-only W2 events, <code>{html.escape(str(delayed_top.get('primary', 'n/a')))}</code> is the largest nuclide.</p>
    <figure>
      <img src="assets/w2_background_source_breakdown.png" alt="W2 background source breakdown">
      <figcaption>The total decomposition rate is checked against the Step05 W2 background rate.</figcaption>
    </figure>
  </section>

  <section>
    <h2>Scope, Data, And Method</h2>
    <p>W2 is <code>510.58-511.42 keV</code>; the reference flux is <code>1e-4 ph cm^-2 s^-1</code>; 1 Ms is <code>1,000,000 s</code>. Step02 produces the full-stat prompt, buildup, delayed source, and delayed transport; Step05 applies detector selection; Step06-08 fold mission time and counting significance.</p>
  </section>

  <section>
    <h2>Limitations And Robustness Checks</h2>
    <ul>{limitation_items}</ul>
  </section>
  {problem_block}
  <section>
    <h2>Sources And Artifacts</h2>
    <p>Primary repo artifacts are copied into <code>summaries/</code>, <code>tables/</code>, and <code>assets/</code>. DEMO2/new_geo_re comparison values come from legacy pre-fix <code>core_md/README.md</code> and <code>core_md/VALIDATION.md</code> records; they are not current authority after the reproduced x8.0116 delayed-source normalization issue. The legacy <code>stepwise_3sigma_headline_results.png</code> file named in older notes is absent in this checkout. External benchmark sources: <a href="https://arxiv.org/abs/2206.14652">511-CAM</a>, <a href="https://arxiv.org/abs/astro-ph/0310793">SPI</a>, and <a href="https://arxiv.org/abs/2308.12362">COSI</a>.</p>
  </section>
</main>
</body>
</html>
"""


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    report_md = OUT / "v3p5_fullstat_performance_w2_closure_report.md"
    report_html = OUT / "report.html"
    summary_json = OUT / "v3p5_fullstat_performance_w2_closure_summary.json"
    report_md.write_text(markdown(payload), encoding="utf-8")
    report_html.write_text(html_report(payload), encoding="utf-8")
    write_json(summary_json, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "report": rel(report_md),
                "html": rel(report_html),
                "summary": rel(summary_json),
                "problems": payload["problems"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if not payload["problems"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
