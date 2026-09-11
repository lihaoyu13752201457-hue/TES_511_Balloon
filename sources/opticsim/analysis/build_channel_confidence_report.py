#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[1]


SOURCES = [
    {
        "label": "511-CAM arXiv/JATIS paper",
        "url": "https://arxiv.org/abs/2206.14652",
        "role": "12 m Channel mission context, four-ring geometry, 30/150 nm W/Si, 80% headline transmissivity, 50.89 cm2 effective area.",
    },
    {
        "label": "Shirazi 2020 soft gamma-ray concentrator",
        "url": "https://www.osti.gov/biblio/1716823",
        "role": "IMD reflectivity + IDL ray tracing + MEGAlib detector chain, and the R^n/open-fraction/path-absorption channel efficiency formula.",
    },
    {
        "label": "CXRO optical constants and multilayer tools",
        "url": "https://henke.lbl.gov/optical_constants/",
        "role": "Independent public x-ray optical-constants and reflectivity tooling reference.",
    },
    {
        "label": "DarpanX paper",
        "url": "https://arxiv.org/abs/2101.02571",
        "role": "Independent multilayer reflectivity code family, validated against IMD for x-ray multilayer mirrors.",
    },
    {
        "label": "Hard x-ray multilayer optical constants",
        "url": "https://authors.library.caltech.edu/records/t02w2-sz821",
        "role": "Experimental hard-x-ray optical constants for W, Si, and related multilayer materials over 35-180 keV.",
    },
]


def read_json(path: str | Path) -> Dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_text(path: str | Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def fmt(value: Any, digits: int = 5) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}g}"
    return str(value)


def pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def table(headers: List[str], rows: Iterable[Iterable[Any]]) -> str:
    head = "".join(f"<th>{esc(item)}</th>" for item in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{esc(item)}</td>" for item in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def evidence_cards(summary: Dict[str, Any]) -> str:
    blocks = [
        ("High", summary["claim"]["high_confidence"], "high"),
        ("Medium", summary["claim"]["medium_confidence"], "medium"),
        ("Open", summary["claim"]["open"], "open"),
    ]
    cards = []
    for title, items, cls in blocks:
        lis = "".join(f"<li>{esc(item)}</li>" for item in items)
        cards.append(f"<article class='evidence-card {cls}'><h3>{title}</h3><ul>{lis}</ul></article>")
    return "<div class='evidence-grid'>" + "".join(cards) + "</div>"


def bar_svg(values: List[Tuple[str, float, str]], width: int = 860, height: int = 300) -> str:
    margin_left = 190
    margin_right = 50
    margin_top = 36
    row_h = 48
    bar_w = width - margin_left - margin_right
    max_v = max(value for _, value, _ in values)
    rows = []
    for idx, (label, value, color) in enumerate(values):
        y = margin_top + idx * row_h
        w = max(2.0, bar_w * value / max_v)
        rows.append(
            f"<text x='12' y='{y + 22}'>{esc(label)}</text>"
            f"<rect x='{margin_left}' y='{y}' width='{w:.1f}' height='26' rx='3' fill='{color}'/>"
            f"<text x='{margin_left + w + 8:.1f}' y='{y + 19}'>{pct(value)}</text>"
        )
    axis_y = margin_top + len(values) * row_h + 4
    return (
        f"<svg class='metric-chart' viewBox='0 0 {width} {height}' role='img' aria-label='Channel transmissivity comparison'>"
        f"<text x='12' y='22' class='chart-title'>Transmissivity / Detection Fraction</text>"
        f"{''.join(rows)}"
        f"<line x1='{margin_left}' y1='{axis_y}' x2='{margin_left + bar_w}' y2='{axis_y}' stroke='#8a95a3'/>"
        "</svg>"
    )


def source_list() -> str:
    rows = []
    for source in SOURCES:
        rows.append(
            "<li>"
            f"<a href='{esc(source['url'])}'>{esc(source['label'])}</a>"
            f"<span>{esc(source['role'])}</span>"
            "</li>"
        )
    return "<ol class='sources'>" + "".join(rows) + "</ol>"


def build_report(args: argparse.Namespace) -> Dict[str, Any]:
    plan = read_json(args.plan_summary)
    wall = read_json(args.wallbywall_summary)
    wall_no_si = read_json(args.wallbywall_no_si_summary)
    strict = read_json(args.geant4_strict_summary)
    calibrated = read_json(args.geant4_calibrated_summary)
    detector = read_json(args.detector_summary)
    wall_contract = read_json(args.wallbywall_contract)
    detector_contract = read_json(args.detector_contract)
    per_ring_wall = read_json(args.wallbywall_per_ring)
    strict_per_ring = []
    for line in read_text(args.geant4_strict_per_ring).splitlines()[1:]:
        if not line.strip():
            continue
        cells = line.split(",")
        strict_per_ring.append(
            {
                "ring_id": int(cells[0]),
                "n_bounce": int(cells[5]),
                "theta_rad": float(cells[6]),
                "transmissivity": float(cells[12]),
                "path_survival": float(cells[13]),
                "mean_R": float(cells[14]),
            }
        )

    conservative_delta = strict["transmissivity"] - wall["transmissivity"]
    conservative_rel_delta = abs(conservative_delta) / max(1.0e-12, 0.5 * (strict["transmissivity"] + wall["transmissivity"]))
    headline_delta = calibrated["transmissivity"] - wall["transmissivity"]

    claim_rows = [
        [
            "Physics-closed conservative Channel",
            "High for current research-prototype stage",
            (
                f"Python wall-by-wall T={wall['transmissivity']:.4f}; "
                f"Geant4 strict public-parameter T={strict['transmissivity']:.4f}; "
                f"absolute delta={conservative_delta:+.4f}, relative delta={100.0 * conservative_rel_delta:.2f}%."
            ),
        ],
        [
            "511-CAM headline 80% Channel",
            "Medium / calibrated",
            (
                f"Geant4 calibrated handoff T={calibrated['transmissivity']:.4f}; "
                f"it reproduces the headline scale but remains parameterized and {headline_delta:.4f} above the public-geometry wall-by-wall run."
            ),
        ],
        [
            "Detector handoff",
            "High for interface, low for detector physics closure",
            (
                f"Wall-by-wall phase_space drives detector-only Geant4 1k smoke; "
                f"contract ok={detector_contract['ok']}, TES fraction={detector['tes_detection_fraction']:.3f}."
            ),
        ],
    ]

    ring_rows = []
    strict_by_ring = {row["ring_id"]: row for row in strict_per_ring}
    for row in per_ring_wall:
        strict_row = strict_by_ring[row["ring_id"]]
        ring_rows.append(
            [
                row["ring_id"],
                fmt(row["mean_survivor_bounces"]),
                fmt(row["mean_grazing_angle_rad"]),
                fmt(row["transmissivity"]),
                strict_row["n_bounce"],
                fmt(strict_row["theta_rad"]),
                fmt(strict_row["transmissivity"]),
                fmt(row["transmissivity"] - strict_row["transmissivity"]),
            ]
        )

    metric_rows = [
        ["Wall-by-wall + Si path", wall["n_primaries"], wall["n_survived"], fmt(wall["transmissivity"]), fmt(wall["effective_area_cm2"]), fmt(wall["mean_bounces_per_survivor"])],
        ["Wall-by-wall no Si path", wall_no_si["n_primaries"], wall_no_si["n_survived"], fmt(wall_no_si["transmissivity"]), fmt(wall_no_si["effective_area_cm2"]), fmt(wall_no_si["mean_bounces_per_survivor"])],
        ["Geant4 strict public-parameter", strict["n_primaries"], strict["n_survived"], fmt(strict["transmissivity"]), fmt(strict["effective_area_cm2"]), "parameterized"],
        ["Geant4 calibrated headline handoff", calibrated["n_primaries"], calibrated["n_survived"], fmt(calibrated["transmissivity"]), fmt(calibrated["effective_area_cm2"]), "parameterized"],
        ["Detector-only smoke from wall-by-wall", detector["n_input_photons"], detector["n_simulated"], fmt(detector["tes_detection_fraction"]), "n/a", "n/a"],
    ]

    chart = bar_svg(
        [
            ("Wall-by-wall + Si", wall["transmissivity"], "#2f6f9f"),
            ("G4 strict public", strict["transmissivity"], "#477c4b"),
            ("Wall-by-wall no Si", wall_no_si["transmissivity"], "#c47b2c"),
            ("G4 calibrated headline", calibrated["transmissivity"], "#7b5bbd"),
            ("Detector TES fraction", detector["tes_detection_fraction"], "#5e6b78"),
        ]
    )

    css = """
    :root { --ink:#17212b; --muted:#53616f; --line:#d9e0e8; --paper:#ffffff; --bg:#eef2f6; --blue:#2f6f9f; --green:#477c4b; --amber:#9b641d; --red:#9c3d35; }
    * { box-sizing: border-box; }
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC","Microsoft YaHei",Arial,sans-serif; color:var(--ink); background:var(--bg); line-height:1.55; }
    header { background:#102335; color:white; padding:34px 28px 30px; border-bottom:5px solid #5da0d2; }
    header .wrap, main { max-width:1120px; margin:0 auto; }
    h1 { margin:0 0 10px; font-size:34px; line-height:1.15; letter-spacing:0; }
    h2 { margin:0 0 14px; font-size:24px; line-height:1.25; letter-spacing:0; }
    h3 { margin:0 0 8px; font-size:17px; letter-spacing:0; }
    p { margin:0 0 12px; }
    main { padding:22px 18px 52px; }
    section { background:var(--paper); border:1px solid var(--line); border-radius:8px; margin:0 0 18px; padding:24px 26px; }
    .lede { color:#dbe7f3; max-width:980px; font-size:17px; }
    .verdict { display:grid; grid-template-columns:1.15fr .85fr; gap:18px; align-items:start; }
    .callout { border-left:5px solid var(--blue); background:#f3f8fc; padding:14px 16px; border-radius:4px; }
    .callout.warn { border-left-color:var(--amber); background:#fff8ec; }
    .evidence-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }
    .evidence-card { border:1px solid var(--line); border-radius:8px; padding:15px; background:#fbfdff; }
    .evidence-card.high { border-top:4px solid var(--green); }
    .evidence-card.medium { border-top:4px solid var(--amber); }
    .evidence-card.open { border-top:4px solid var(--red); }
    ul { padding-left:20px; margin:8px 0 0; }
    li { margin:5px 0; }
    table { width:100%; border-collapse:collapse; font-size:14px; margin:10px 0 4px; }
    th, td { border-bottom:1px solid var(--line); padding:9px 8px; text-align:left; vertical-align:top; }
    th { background:#f2f5f8; font-weight:650; }
    code { background:#eef3f7; border:1px solid #dbe4ed; padding:1px 5px; border-radius:4px; }
    .metric-chart { width:100%; min-height:280px; background:#fbfdff; border:1px solid var(--line); border-radius:8px; padding:8px; }
    .metric-chart text { font-size:14px; fill:#17212b; }
    .metric-chart .chart-title { font-weight:700; font-size:16px; }
    .sources { margin:4px 0 0; padding-left:24px; }
    .sources li { margin:8px 0; }
    .sources span { display:block; color:var(--muted); }
    .two-col { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
    .foot { color:var(--muted); font-size:13px; margin-top:12px; }
    @media (max-width: 820px) { .verdict, .two-col, .evidence-grid { grid-template-columns:1fr; } h1 { font-size:28px; } section { padding:20px 18px; } }
    """

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Channel Optics Confidence Report</title>
  <style>{css}</style>
</head>
<body>
<header>
  <div class="wrap">
    <h1>511-CAM Channel Optics：从物理原理到实现的可信度汇报</h1>
    <p class="lede">目标是把 Channel 光学推进到和 Laue 线相同类型的 research-prototype 信心：公式和公开参数可追溯，实现可重复，跨实现交叉验证通过，并且不把校准 headline 误说成 first-principles 闭合。</p>
  </div>
</header>
<main>
  <section class="verdict">
    <div>
      <h2>结论</h2>
      <div class="callout">
        <p><strong>保守物理闭合 Channel 模型已经达到接近 Laue 的当前阶段信心。</strong> 依据是 Python wall-by-wall 几何模型和 Geant4 strict public-parameter 模型独立实现后得到接近的总透过率：{wall['transmissivity']:.4f} vs {strict['transmissivity']:.4f}，相对差 {100.0 * conservative_rel_delta:.2f}%。</p>
      </div>
      <div class="callout warn">
        <p><strong>511-CAM 论文的 80% headline 仍不能按同一信心等级声称为 first-principles 结果。</strong> 当前 Geant4 calibrated handoff 可以复现 {calibrated['transmissivity']:.4f} 和 {calibrated['effective_area_cm2']:.4g} cm2，但它仍是参数化/校准模式。</p>
      </div>
    </div>
    <div>
      {chart}
    </div>
  </section>

  <section>
    <h2>物理原理</h2>
    <p>Channel optics 使用弯曲的低/高 Z 多层膜结构。入射光子进入低密度 Si spacer 后，在 W/Si 界面附近以小 grazing angle 多次全外反射，弯曲通道把逐次反射累计成较大的偏转角。标准 Geant4 gamma EM 过程可以处理探测器中的光电效应、康普顿散射、Rayleigh 和 pair production，但不会自动给出 bent multilayer channel 的相干反射和聚焦。</p>
    <p>因此本仓库采用分层实现：几何上不真实建 30 nm/150 nm 纳米层；光学上用 <code>R(E,theta), A(E,theta), T(E,theta)</code> 表和通道几何生成 boundary/reflection history；探测器再由 Geant4 EM 处理。</p>
  </section>

  <section>
    <h2>文献和公开输入</h2>
    {source_list()}
    <p class="foot">本报告使用本地已缓存的 511-CAM 和 Shirazi 2020 文本摘录，并通过联网核验了 arXiv、OSTI、CXRO、DarpanX、CaltechAUTHORS 等来源的页面。</p>
  </section>

  <section>
    <h2>从公式到可执行模型</h2>
    <div class="two-col">
      <div>
        <h3>公开公式项</h3>
        <ul>
          <li>多次反射项：<code>R^n</code></li>
          <li>路径吸收项：沿 Si channel 的指数衰减</li>
          <li>开放比例：<code>150 / (30 + 150) = {wall['open_fraction_from_geometry']:.6f}</code></li>
          <li>每次 wall hit 记录 <code>theta</code>、<code>R/A/T</code>、入射/出射方向、位置和 action</li>
        </ul>
      </div>
      <div>
        <h3>实现层</h3>
        <ul>
          <li><code>wallbywall_channel.py</code>：public geometry truth generator，不输入 calibrated bounce/theta。</li>
          <li><code>channel_4ring_multibounce_demo.cc</code>：Geant4 optics handoff，支持 calibrated 和 strict public-parameter 模式。</li>
          <li><code>detector_only_demo.cc</code>：Geant4 detector-only smoke，验证 optics phase_space 可进入 detector backend。</li>
          <li><code>io_contract.py</code>：统一验证 phase_space、optics_history、hits、event_summary。</li>
        </ul>
      </div>
    </div>
  </section>

  <section>
    <h2>核心运行结果</h2>
    {table(["run", "n/input", "survived/simulated", "transmissivity or TES fraction", "effective area cm2", "bounce evidence"], metric_rows)}
    <p class="foot">Geant4 calibrated headline handoff 的焦斑尺度仍由配置目标控制；wall-by-wall 的焦平面分布是当前几何模型自然给出的诊断，不应直接与 headline 3.6 cm 混同。</p>
  </section>

  <section>
    <h2>逐环交叉验证</h2>
    {table(["ring", "wall survivor bounces", "wall mean theta rad", "wall T", "G4 strict n", "G4 strict theta rad", "G4 strict T", "wall - G4 strict"], ring_rows)}
    <p class="foot">逐环并不完全相同，因为 Python wall-by-wall 显式求交，Geant4 strict 是公开公式项的参数化压力测试；总透过率接近是当前最重要的跨实现证据。</p>
  </section>

  <section>
    <h2>与 Laue 线的信心对齐</h2>
    {table(["对象", "信心", "证据"], claim_rows)}
    {evidence_cards(plan)}
  </section>

  <section>
    <h2>Contract 和可重复性</h2>
    <ul>
      <li>Wall-by-wall optics-only contract：<code>ok={wall_contract['ok']}</code>，phase_space rows={wall_contract['results'][0]['n_rows']}，optics_history rows={wall_contract['results'][1]['n_rows']}。</li>
      <li>Wall-by-wall to detector 1k contract：<code>ok={detector_contract['ok']}</code>，hits rows={detector_contract['results'][2]['n_rows']}，event_summary rows={detector_contract['results'][3]['n_rows']}。</li>
      <li>Detector smoke warning：{esc(detector['warning'])}</li>
    </ul>
  </section>

  <section>
    <h2>剩余开放项</h2>
    <ul>
      <li>需要原始 IDL source 或等价 path/open-area/absorption accounting，才能把 80% headline 也提升到同等级 first-principles 信心。</li>
      <li>需要独立 IMD/DarpanX/CXRO/Henke 导出表与当前 Parratt/xraydb 表比较，才能把 W/Si optical constants provenance 做到 publication-grade。</li>
      <li>需要把 detector-only scaffold 升级为审计过的 TES/BGO 质量模型和 reconstruction，才能声称 detector performance。</li>
    </ul>
  </section>
</main>
</body>
</html>
"""
    report_path = ROOT / args.out
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(html_text, encoding="utf-8")
    summary = {
        "status": "CHANNEL_CONFIDENCE_REPORT_BUILT",
        "report": display_path(report_path),
        "conservative_channel_confidence": "HIGH_CURRENT_RESEARCH_PROTOTYPE",
        "headline_80pct_confidence": "MEDIUM_CALIBRATED_NOT_FIRST_PRINCIPLES",
        "wallbywall_transmissivity": wall["transmissivity"],
        "geant4_strict_transmissivity": strict["transmissivity"],
        "strict_minus_wallbywall_abs": conservative_delta,
        "strict_vs_wallbywall_relative_delta": conservative_rel_delta,
        "geant4_calibrated_transmissivity": calibrated["transmissivity"],
        "detector_contract_ok": detector_contract["ok"],
        "wallbywall_contract_ok": wall_contract["ok"],
        "sources": SOURCES,
    }
    summary_path = ROOT / args.summary
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an HTML confidence report for Channel optics.")
    parser.add_argument("--plan-summary", default="runs/channel_optics_plan_completion/summary.json")
    parser.add_argument("--wallbywall-summary", default="runs/channel_wallbywall_rebuild/summary.json")
    parser.add_argument("--wallbywall-no-si-summary", default="runs/channel_wallbywall_rebuild_no_si_abs_smoke/summary.json")
    parser.add_argument("--geant4-strict-summary", default="runs/channel/geant4_4ring_multibounce_paper_formula_strict/summary.json")
    parser.add_argument("--geant4-calibrated-summary", default="runs/channel/geant4_4ring_multibounce_calibrated/summary.json")
    parser.add_argument("--detector-summary", default="runs/geant4_detector_wallbywall_1k/summary.json")
    parser.add_argument("--wallbywall-contract", default="runs/io_contract_validation_channel_wallbywall_rebuild/summary.json")
    parser.add_argument("--detector-contract", default="runs/io_contract_validation_channel_wallbywall_detector_1k/summary.json")
    parser.add_argument("--wallbywall-per-ring", default="runs/channel_wallbywall_rebuild/per_ring_summary.json")
    parser.add_argument("--geant4-strict-per-ring", default="runs/channel/geant4_4ring_multibounce_paper_formula_strict/per_ring_summary.csv")
    parser.add_argument("--out", default="records/2026-05-21_channel_confidence_report.html")
    parser.add_argument("--summary", default="runs/channel_confidence_report/summary.json")
    args = parser.parse_args()
    summary = build_report(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
