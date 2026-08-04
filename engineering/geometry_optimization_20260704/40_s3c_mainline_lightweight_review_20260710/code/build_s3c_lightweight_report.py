#!/usr/bin/env python3
"""Build the self-contained technical HTML report for the S3c mainline review."""

from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
REPORT = PACKAGE / "report"
SHELL_TEMPLATE = Path(
    "/home/ubuntu/.codex/plugins/cache/openai-curated-remote/data-analytics/"
    "0.2.6-d37358633e00/assets/html-report-shell.html"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class SourceTooltips:
    def __init__(self) -> None:
        self.count = 0

    def wrap(self, value: str, source: str, dataset: str) -> str:
        self.count += 1
        tooltip_id = f"number-source-tooltip-{self.count}"
        return (
            f'<span class="source-tooltip" tabindex="0" aria-describedby="{tooltip_id}">'
            f"{html.escape(value)}"
            f'<span class="source-tooltip-content" id="{tooltip_id}" role="tooltip">'
            '<span class="source-tooltip-heading">数据来源</span>'
            f"Source: {html.escape(source)}<br>Dataset: {html.escape(dataset)}"
            "</span></span>"
        )


def horizontal_bar_svg(
    rows: list[dict[str, Any]],
    *,
    label_key: str,
    value_key: str,
    formatter,
    color: str,
    aria_label: str,
) -> str:
    """Render a readable, same-data fallback for a horizontal Recharts bar."""

    width = 960
    height = max(320, 86 + 47 * len(rows))
    label_x = 14
    plot_x = 292
    plot_width = 505
    value_x = 815
    top = 52
    row_height = 47
    maximum = max(float(row[value_key]) for row in rows) or 1.0
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(aria_label)}">',
        '<line x1="292" y1="34" x2="292" y2="%d" stroke="var(--border-strong)" />'
        % (height - 34),
    ]
    for index, row in enumerate(rows):
        y = top + index * row_height
        bar_width = max(2.0, float(row[value_key]) / maximum * plot_width)
        parts.extend(
            [
                f'<text x="{label_x}" y="{y + 16}" fill="currentColor" font-size="13">'
                f'{html.escape(str(row[label_key]))}</text>',
                f'<rect x="{plot_x}" y="{y}" width="{plot_width}" height="22" rx="5" '
                'fill="var(--surface-tertiary)" />',
                f'<rect x="{plot_x}" y="{y}" width="{bar_width:.2f}" height="22" rx="5" '
                f'fill="{color}" />',
                f'<text x="{value_x}" y="{y + 16}" fill="currentColor" font-size="13" '
                f'font-variant-numeric="tabular-nums">{html.escape(formatter(float(row[value_key])))}</text>',
            ]
        )
    parts.append("</svg>")
    return "".join(parts)


def chart_card(
    *,
    chart_id: str,
    title: str,
    subtitle: str,
    fallback_svg: str,
    note: str,
    tooltip_id: str,
    source: str,
    dataset: str,
) -> str:
    return f"""
      <div class="wide">
        <figure class="card source-figure">
          <div class="card-head"><h3>{html.escape(title)}</h3><p>{html.escape(subtitle)}</p></div>
          <div class="chart-wrap">
            <div data-recharts-chart="{html.escape(chart_id)}">
              <div class="chart-fallback" data-recharts-fallback>{fallback_svg}</div>
              <div data-recharts-live aria-hidden="true"></div>
            </div>
          </div>
          <figcaption class="chart-note">{html.escape(note)}</figcaption>
          <button type="button" class="source-tooltip" aria-describedby="{tooltip_id}">Source
            <span class="source-tooltip-content" id="{tooltip_id}" role="tooltip">
              <span class="source-tooltip-heading">数据来源</span>
              Source: {html.escape(source)}<br>Dataset: {html.escape(dataset)}
            </span>
          </button>
        </figure>
      </div>"""


def numeric_or_dash(
    tips: SourceTooltips,
    raw: str,
    formatter,
    source: str,
    dataset: str,
) -> str:
    if raw == "":
        return "—"
    return tips.wrap(formatter(float(raw)), source, dataset)


def build() -> tuple[Path, Path]:
    analysis = load_json(DATA / "s3c_mainline_analysis_summary.json")
    history = load_json(PACKAGE / "retained_conclusions/historical_design_points.json")
    candidates = load_csv(DATA / "s3c_lightweight_candidates.csv")
    run_matrix = load_csv(DATA / "s3c_lightweight_run_matrix.csv")
    tips = SourceTooltips()

    background_labels = {
        "eplus": "宇宙线 e+",
        "n": "宇宙线中子",
        "atm511": "大气 511 keV",
        "retained_non_dominant_residual": "沿用 S3 的其余项",
    }
    background_rows = [
        {
            "component": background_labels[row["component"]],
            "rate_cps": float(row["rate_cps"]),
            "rate_1e3_cps": float(row["rate_cps"]) * 1000.0,
        }
        for row in analysis["background"]["component_rows"]
    ]
    activation_labels = {
        "Window package": "窗口组件",
        "Cryostat and cold structure": "低温恒温器/冷结构",
        "S3c W mechanical shell": "S3c 外层 W 壳",
        "NF2 support": "NF2 支撑",
        "S3c BGO active shell": "S3c BGO 主动壳",
        "Retained passive W/collimator": "保留的被动 W/准直器",
        "Other": "其他",
        "S3c Al mechanical shell": "S3c Al 机械壳",
    }
    activation_rows = [
        {
            "volume_class": activation_labels[row["volume_class"]],
            "activity_bq": float(row["activity_bq"]),
        }
        for row in analysis["activation"]["volume_classes"]
    ]
    mass_rows = [
        {
            "variant": row["variant"].replace(" retained", "").replace(" current", ""),
            "mass_kg": float(row["mass_kg_pre_relief"]),
        }
        for row in candidates
    ]

    background_svg = horizontal_bar_svg(
        background_rows,
        label_key="component",
        value_key="rate_1e3_cps",
        formatter=lambda value: f"{value:.3f} ×10⁻³ cps",
        color="var(--blue)",
        aria_label="S3c W2 本底各组成项的计数率",
    )
    activation_svg = horizontal_bar_svg(
        activation_rows,
        label_key="volume_class",
        value_key="activity_bq",
        formatter=lambda value: f"{value:.2f} Bq",
        color="var(--blue)",
        aria_label="S3c 中子延迟活度按体积类别分布",
    )
    mass_svg = horizontal_bar_svg(
        mass_rows,
        label_key="variant",
        value_key="mass_kg",
        formatter=lambda value: f"{value:.1f} kg",
        color="var(--blue)",
        aria_label="S3c 轻量化候选的预开孔质量",
    )

    src_analysis = "S3c retained local analysis"
    ds_analysis = "s3c_mainline_analysis_summary.json"
    src_prompt = "S3c retained prompt and atmospheric transport"
    ds_prompt = "dominant_background_summary.json + s3c_atm511_sidecar_3m_summary.json"
    src_delay = "S3c neutron-only delayed chain"
    ds_delay = "exactpos_weighted_rpip_table_m50000_s260613.csv"
    src_candidates = "S3c design-point bookkeeping"
    ds_candidates = "s3c_lightweight_candidates.csv"
    src_history = "Frozen S3/S3a/S3b/S3c conclusion snapshot"
    ds_history = "historical_design_points.json"

    bg = analysis["background"]
    activation = analysis["activation"]
    decision = analysis["mass_trade"]
    current_mass = float(candidates[0]["mass_kg_pre_relief"])
    lw1_mass = float(candidates[1]["mass_kg_pre_relief"])
    lw1_saved = float(candidates[1]["mass_saved_kg_vs_current"])
    lw1_reduction = float(candidates[1]["mass_reduction_fraction"])
    lw1_penalty = float(decision["lw1_f3_penalty_fraction_vs_current_estimate"])
    lw1_activity_reduction = float(decision["lw1_neutron_activity_reduction_fraction"])
    current_components = history["design_points"]["s3c_current"]["mass_kg_pre_relief"]
    bgo_mass = float(current_components["scintillator"])
    w_mass = float(current_components["w"])
    al_mass = float(current_components["aluminium"])
    kapton_mass = float(current_components["kapton"])
    side_events = sum(
        int(row["events"])
        for row in bg["selected_event_entry_rows"]
        if row["entry_surface"] == "side"
    )

    candidate_rows_html: list[str] = []
    for row in candidates:
        candidate_rows_html.append(
            "<tr>"
            f"<td>{html.escape(row['variant'])}</td>"
            f"<td>{html.escape(row['mechanical_shell'])}</td>"
            f"<td>{numeric_or_dash(tips, row['mass_kg_pre_relief'], lambda v: f'{v:.1f}', src_candidates, ds_candidates)}</td>"
            f"<td>{numeric_or_dash(tips, row['mass_saved_kg_vs_current'], lambda v: f'{v:.1f}', src_candidates, ds_candidates)}</td>"
            f"<td>{numeric_or_dash(tips, row['mass_reduction_fraction'], lambda v: f'{v:.1%}', src_candidates, ds_candidates)}</td>"
            f"<td>{numeric_or_dash(tips, row['dominant_subset_w2_cps'], lambda v: f'{v:.6f}', src_candidates, ds_candidates)}</td>"
            f"<td>{numeric_or_dash(tips, row['neutron_only_delayed_activity_bq'], lambda v: f'{v:.2f}', src_candidates, ds_candidates)}</td>"
            f"<td>{html.escape(row['evidence_level'])}</td>"
            "</tr>"
        )
    candidate_table = (
        "<table><thead><tr>"
        "<th>构型</th><th>机械壳</th><th>质量 kg</th><th>减重 kg</th><th>减重率</th>"
        "<th>W2 主导子集 cps</th><th>中子延迟活度 Bq</th><th>证据等级</th>"
        "</tr></thead><tbody>"
        + "".join(candidate_rows_html)
        + "</tbody></table>"
    )

    run_rows_html: list[str] = []
    for row in run_matrix:
        source_cell = lambda value: tips.wrap(value, "S3c lightweight decision program", "s3c_lightweight_run_matrix.csv")
        run_rows_html.append(
            "<tr>"
            f"<td>{source_cell(row['priority'])}</td>"
            f"<td>{html.escape(row['variant'])}</td>"
            f"<td>{html.escape(row['phase'])}</td>"
            f"<td>{html.escape(row['test'])}</td>"
            f"<td>{source_cell(row['statistics'])}</td>"
            f"<td>{source_cell(row['promotion_gate'])}</td>"
            "</tr>"
        )
    run_table = (
        "<table><thead><tr>"
        "<th>顺序</th><th>候选</th><th>阶段</th><th>试验</th><th>统计量</th><th>晋级门槛</th>"
        "</tr></thead><tbody>"
        + "".join(run_rows_html)
        + "</tbody></table>"
    )

    chart_background = chart_card(
        chart_id="s3c-background-components",
        title="W2 本底组成项计数率（×10⁻³ cps）",
        subtitle="前三项为 S3c 实测筛选；最后一项沿用 S3 余项，尚不是 S3c 全族闭合",
        fallback_svg=background_svg,
        note="相同审阅行同时驱动静态 SVG 与交互图；显示值按 10⁻³ cps 缩放。e+、中子仅各留下 2 个事件，大气 511 keV 留下 6 个事件。",
        tooltip_id="chart-source-tooltip-background",
        source=src_prompt,
        dataset=ds_prompt,
    )
    chart_activation = chart_card(
        chart_id="s3c-activation-volume-classes",
        title="中子延迟活度按体积类别分布",
        subtitle="源侧加权活度；不是经过探测器 W2 选择后的计数率",
        fallback_svg=activation_svg,
        note="总和与 8 路、TT 除数 8、M=50000、SE=ID=1000000 的 clean neutron-only 延迟链相符。",
        tooltip_id="chart-source-tooltip-activation",
        source=src_delay,
        dataset=ds_delay,
    )
    chart_mass = chart_card(
        chart_id="s3c-lightweight-mass",
        title="S3c 设计族预开孔质量",
        subtitle="C0/LW1 有输运证据；LW2–LW6 目前只是质量模型或方向性假设",
        fallback_svg=mass_svg,
        note="所有质量均为预开孔 bookkeeping，不替代结构、装配、热学或气球载荷工程审查。",
        tooltip_id="chart-source-tooltip-mass",
        source=src_candidates,
        dataset=ds_candidates,
    )

    main = f"""
    <main data-report-audience="technical">
      <article class="reading">
        <div class="kicker">S3c MAINLINE / MASS &amp; BACKGROUND REVIEW</div>
        <header data-contract-section="title"><h1>S3c 主线与轻量化设计复核</h1></header>
        <p class="deck">把 S3c 定义为设计族：C0 保留为性能基线，LW1 作为首个轻量化晋级点；先移除外层 W，再减薄 Al，最后才评估 BGO 分区减薄。</p>
        <section class="summary" data-contract-section="technical-summary">
          <div class="summary-label">技术摘要</div>
          <div class="summary-body">
            <p><strong>决策：</strong>S3c 可以成为主线，但不应把当前 C0 的重型构型冻结为唯一方案。首选 S3c-LW1：保持全包覆 {tips.wrap('40 mm', src_candidates, ds_candidates)} BGO，采用 {tips.wrap('8 mm', src_candidates, ds_candidates)} Al，移除外层 W。</p>
            <p><strong>收益：</strong>LW1 的预开孔质量为 {tips.wrap(f'{lw1_mass:.1f} kg', src_candidates, ds_candidates)}，比 C0 减少 {tips.wrap(f'{lw1_saved:.1f} kg', src_candidates, ds_candidates)}（{tips.wrap(f'{lw1_reduction:.1%}', src_candidates, ds_candidates)}）；它已有历史同统计筛选与 neutron-only 延迟输运，不只是几何猜想。</p>
            <p><strong>代价：</strong>历史估算的二十日 F3 比 C0 高 {tips.wrap(f'{lw1_penalty:.1%}', src_candidates, ds_candidates)}，但中子延迟活度低 {tips.wrap(f'{lw1_activity_reduction:.1%}', src_candidates, ds_candidates)}。因此应以匹配统计量复跑确认，而不是直接宣布优于 C0。</p>
          </div>
        </section>
        <section class="metrics" aria-label="关键基线指标">
          <div class="metric"><div class="metric-label">C0 预开孔质量</div><div class="metric-value">{tips.wrap(f'{current_mass:.1f} kg', src_candidates, ds_candidates)}</div><div class="metric-note">BGO40 + W2 + Al3</div></div>
          <div class="metric"><div class="metric-label">LW1 减重</div><div class="metric-value">{tips.wrap(f'{lw1_saved:.1f} kg', src_candidates, ds_candidates)}</div><div class="metric-note">保持 BGO40；无外层 W</div></div>
          <div class="metric"><div class="metric-label">W2 主导子集</div><div class="metric-value">{tips.wrap(f'{bg["measured_dominant_subset_cps"]:.6f}', src_prompt, ds_prompt)}</div><div class="metric-note">cps；e+ + n + atm511</div></div>
          <div class="metric"><div class="metric-label">中子延迟活度</div><div class="metric-value">{tips.wrap(f'{activation["total_activity_bq"]:.2f} Bq', src_delay, ds_delay)}</div><div class="metric-note">源侧，neutron-only</div></div>
        </section>
      </article>

      <section data-contract-section="key-findings">
        <article class="reading">
          <section class="narrative">
            <h2>当前本底不是由单一粒子族控制</h2>
            <p>S3c W2 实测主导子集由 e+、中子和大气 511 keV 近似三分。加上沿用 S3 的未重跑余项后，估算总本底为 {tips.wrap(f'{bg["estimated_total_background_cps"]:.6f} cps', src_analysis, ds_analysis)}。这最后一项是占位假设，因此不能把它当作 S3c 全 prompt-family 的闭合测量。</p>
          </section>
        </article>
        {chart_background}
        <article class="reading">
          <section class="narrative">
            <h2>轻量化优先级应从外层 W 开始，而不是直接削薄侧面 BGO</h2>
            <p>最终入选的 {tips.wrap(str(bg['selected_event_count']), src_analysis, ds_analysis)} 个事件中，有 {tips.wrap(str(side_events), src_analysis, ds_analysis)} 个从侧面进入；这只是低统计方向性代理，但足以说明第一轮不宜削弱侧面 BGO。与此同时，窗口组件贡献 {tips.wrap(f'{activation["volume_classes"][0]["fraction_of_neutron_only_activity"]:.1%}', src_delay, ds_delay)} 的 neutron-only 活度，而 S3c 外层 W 壳直接占 {tips.wrap(f'{activation["volume_classes"][2]["fraction_of_neutron_only_activity"]:.1%}', src_delay, ds_delay)}。所以“去 W”是高价值候选，但不能把 W 壳自身活度直接从总活度中相减；它还会改变整个中子场。</p>
          </section>
        </article>
        {chart_activation}
        <article class="reading">
          <section class="narrative">
            <h2>LW1 是唯一可以立即晋级的轻量化点</h2>
            <p>C0 的质量账由 BGO {tips.wrap(f'{bgo_mass:.2f} kg', src_history, ds_history)}、W {tips.wrap(f'{w_mass:.2f} kg', src_history, ds_history)}、Al {tips.wrap(f'{al_mass:.2f} kg', src_history, ds_history)} 和 Kapton {tips.wrap(f'{kapton_mass:.2f} kg', src_history, ds_history)} 构成；BGO 占 {tips.wrap(f'{bgo_mass / current_mass:.1%}', src_history, ds_history)}，是最终的大头，但 W 是第一轮最容易移除且已有对照证据的 {tips.wrap(f'{w_mass:.2f} kg', src_history, ds_history)}。LW2 与 LW3 延续“保留 BGO40、无 W、减薄 Al”的可解释路径；LW4 才开始做侧厚、底中、顶薄的分区假设。LW5/LW6 虽然质量更低，但没有相应 veto、信号接受度或延迟闭合证据，应只放在探索队列。</p>
          </section>
        </article>
        {chart_mass}
        <article class="reading">
          <section class="card table-card">
            <div class="card-head"><h3>候选设计证据表</h3><p>空白表示尚未完成对应输运；不能解读为零本底或零活度。</p></div>
            <div class="table-scroll">{candidate_table}</div>
          </section>
        </article>
      </section>

      <article class="reading">
        <section class="narrative" data-contract-section="scope-data-and-metric-definitions">
          <h2>范围、数据和指标定义</h2>
          <ul>
            <li><strong>C0：</strong>当前 S3c 基线，侧/底/顶均为 {tips.wrap('40 mm', src_candidates, ds_candidates)} BGO，外层 {tips.wrap('2 mm', src_candidates, ds_candidates)} W 与 {tips.wrap('3 mm', src_candidates, ds_candidates)} Al；质量为开孔前材料体积账。</li>
            <li><strong>W2：</strong>{tips.wrap('510.58–511.42 keV', src_prompt, ds_prompt)} 的最终筛选窗。主导子集只含 e+、中子、大气 511 keV；“估算总本底”还加了沿用 S3 的非主导余项。</li>
            <li><strong>延迟活度：</strong>clean neutron-only exact-position RPIP 的源侧 Bq；它不是探测器响应后的 W2 cps。</li>
            <li><strong>方向分布：</strong>从入选 SIM 事件的 IA INIT 初始方向推断外表面交点，只用来排序设计假设。</li>
          </ul>
        </section>

        <section class="narrative" data-contract-section="methodology">
          <h2>方法</h2>
          <p>本复核只读取保留的 S3c prompt、atm511 与 clean neutron-only 延迟产物，并用冻结的 S3/S3a/S3b 结论 JSON 做设计点比较。脚本重新汇总 W2 组成、扫描最终事件入射面、按体积与核素聚合加权活度，再用解析材料体积建立 LW2–LW6 的预开孔质量模型。所有 source card 与 SIM header 均由独立验证器核对到 S3c 几何。</p>
        </section>

        <section class="narrative" data-contract-section="limitations-uncertainty-and-robustness-checks">
          <h2>局限、不确定度与稳健性检查</h2>
          <ul>
            <li>e+ 和中子在最终窗内各只有 {tips.wrap('2', src_prompt, ds_prompt)} 个事件，对应纯计数相对一西格玛约 {tips.wrap('70.7%', src_analysis, ds_analysis)}；atm511 有 {tips.wrap('6', src_prompt, ds_prompt)} 个事件，约 {tips.wrap('40.8%', src_analysis, ds_analysis)}。图中的相近占比不代表精确排序。</li>
            <li>S3c “总本底”仍含沿用 S3 的余项；在全 prompt-family 重跑前，它只能作为决策代理。</li>
            <li>LW2–LW6 的质量不包含开孔、紧固、容差、支撑、热连接与结构裕度；也没有证明薄 Al 能承载 BGO。</li>
            <li>延迟链通过 NUBASE 基态校正、逐族 TT 除数、{tips.wrap('8', src_delay, ds_delay)} 路源文件、{tips.wrap('M=50000', src_delay, ds_delay)} 和 {tips.wrap('SE=ID=1000000', src_delay, ds_delay)} 审计；但目前只覆盖 neutron-only。</li>
          </ul>
          <div class="caveat"><strong>解释边界。</strong> 这份报告支持“下一批模拟怎么排”，不支持直接冻结飞行机械设计。任何晋级构型都必须同时通过 prompt、本底延迟、信号接受度与结构质量审计。</div>
        </section>

        <section class="narrative" data-contract-section="recommended-next-steps">
          <h2>建议的主线试验顺序</h2>
          <p>先把历史 BGO40/Al8/no-W 点按 S3c-LW1 命名重建，再以相同统计量并排筛 C0、LW1、LW2、LW3。只有通过本底门槛的候选才能进入信号与延迟链；分区 BGO 的 LW4 放在第二轮。</p>
        </section>
        <section class="card table-card">
          <div class="card-head"><h3>晋级矩阵</h3><p>顺序和门槛均固化在可机读 CSV 中。</p></div>
          <div class="table-scroll">{run_table}</div>
        </section>

        <section class="narrative" data-contract-section="further-questions">
          <h2>待回答问题</h2>
          <ul>
            <li>LW1 的 prompt 优势/劣势在统一 S3c 源卡与更高统计量下是否仍成立？</li>
            <li>去除外层 W 后，窗口 W-187 和 Al-28 的活度变化来自材料减少，还是中子谱场变化？</li>
            <li>Al5 是否能满足 BGO 安装、冲击、热收缩和气球飞行载荷；若不能，最轻可制造厚度是多少？</li>
            <li>在保持侧面 BGO40 的前提下，顶/底分区减薄对 f10m A1 最终 W2 信号接受度的影响有多大？</li>
          </ul>
        </section>
      </article>
    </main>"""

    template = SHELL_TEMPLATE.read_text(encoding="utf-8")
    shell = re.sub(r'<main\b[^>]*>.*?</main>', main, template, count=1, flags=re.DOTALL)
    shell = shell.replace('<html lang="en">', '<html lang="zh-CN">')
    shell = shell.replace("{{TITLE}}", "S3c 主线与轻量化设计复核")
    shell = shell.replace(
        '<div class="brand"><span class="mark" aria-hidden="true"></span>Data Analytics</div>',
        '<div class="brand"><span class="mark" aria-hidden="true"></span>S3c Mainline Analytics</div>',
    )
    shell = shell.replace("{{SOURCE_AND_DATE}}", "Local retained artifacts · 2026-07-10")
    shell = shell.replace("{{REPORT_AUDIENCE}}", "technical")
    shell = shell.replace(
        "</head>",
        """  <style data-s3c-report-responsive-overrides="true">
    .chart-wrap { padding-left: 132px; }
    @media (max-width: 800px) {
      .chart-wrap { overflow-x: auto; padding: 16px 24px 16px 132px; }
      [data-recharts-chart] { min-width: 720px; }
    }
  </style>
</head>""",
        1,
    )
    shell = re.sub(
        r"\s*<!-- Deliver this HTML file itself\..*?-->\s*",
        "\n  ",
        shell,
        count=1,
        flags=re.DOTALL,
    )
    if "{{" in shell or "}}" in shell:
        raise RuntimeError("Unresolved shell placeholder remains")

    payload = {
        "charts": [
            {
                "id": "s3c-background-components",
                "height": 340,
                "type": "bar",
                "dataset": {
                    "id": "s3c-background-components",
                    "title": "W2 background component rates",
                    "data": background_rows,
                    "chart_spec": {
                        "id": "s3c-background-components",
                        "dataset": "s3c-background-components",
                        "title": "W2 background component rates",
                        "type": "bar",
                        "encodings": {
                            "x": {"field": "component", "type": "nominal"},
                            "y": {"field": "rate_1e3_cps", "label": "Rate (×10⁻³ cps)", "type": "quantitative"},
                            "tooltip": [
                                {"field": "component", "type": "nominal"},
                                {"field": "rate_1e3_cps", "label": "Rate (×10⁻³ cps)", "type": "quantitative"},
                            ],
                        },
                        "xAxisTitle": "",
                        "yAxisTitle": "",
                        "valueFormat": "number",
                        "settings": {"orientation": "horizontal", "groupMode": "grouped"},
                    },
                },
            },
            {
                "id": "s3c-activation-volume-classes",
                "height": 430,
                "type": "bar",
                "dataset": {
                    "id": "s3c-activation-volume-classes",
                    "title": "Neutron-delayed activity by volume class",
                    "data": activation_rows,
                    "chart_spec": {
                        "id": "s3c-activation-volume-classes",
                        "dataset": "s3c-activation-volume-classes",
                        "title": "Neutron-delayed activity by volume class",
                        "type": "bar",
                        "encodings": {
                            "x": {"field": "volume_class", "type": "nominal"},
                            "y": {"field": "activity_bq", "label": "Activity (Bq)", "type": "quantitative"},
                            "tooltip": [
                                {"field": "volume_class", "type": "nominal"},
                                {"field": "activity_bq", "label": "Activity (Bq)", "type": "quantitative"},
                            ],
                        },
                        "xAxisTitle": "",
                        "yAxisTitle": "",
                        "valueFormat": "number",
                        "settings": {"orientation": "horizontal", "groupMode": "grouped"},
                    },
                },
            },
            {
                "id": "s3c-lightweight-mass",
                "height": 410,
                "type": "bar",
                "dataset": {
                    "id": "s3c-lightweight-mass",
                    "title": "S3c design-family pre-relief mass",
                    "data": mass_rows,
                    "chart_spec": {
                        "id": "s3c-lightweight-mass",
                        "dataset": "s3c-lightweight-mass",
                        "title": "S3c design-family pre-relief mass",
                        "type": "bar",
                        "encodings": {
                            "x": {"field": "variant", "type": "nominal"},
                            "y": {"field": "mass_kg", "label": "Mass (kg)", "type": "quantitative"},
                            "tooltip": [
                                {"field": "variant", "type": "nominal"},
                                {"field": "mass_kg", "label": "Mass (kg)", "type": "quantitative"},
                            ],
                        },
                        "xAxisTitle": "",
                        "yAxisTitle": "",
                        "valueFormat": "number",
                        "settings": {"orientation": "horizontal", "groupMode": "grouped"},
                    },
                },
            },
        ]
    }

    REPORT.mkdir(parents=True, exist_ok=True)
    shell_path = REPORT / "s3c_lightweight_report_shell.html"
    payload_path = REPORT / "s3c_lightweight_report_payload.json"
    shell_path.write_text(shell, encoding="utf-8")
    payload_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return shell_path, payload_path


if __name__ == "__main__":
    shell_output, payload_output = build()
    print(f"PASS_S3C_REPORT_SHELL {shell_output}")
    print(f"PASS_S3C_REPORT_PAYLOAD {payload_output}")
