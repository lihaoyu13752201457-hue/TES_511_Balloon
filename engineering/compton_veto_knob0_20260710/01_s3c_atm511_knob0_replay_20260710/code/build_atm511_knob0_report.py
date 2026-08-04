#!/usr/bin/env python3
"""Build the self-contained technical HTML report for the atm511 Knob0 replay."""

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


class SourceTips:
    def __init__(self) -> None:
        self.count = 0

    def wrap(self, value: str, source: str, file_name: str) -> str:
        self.count += 1
        tip_id = f"number-source-tooltip-{self.count}"
        return (
            f'<span class="source-tooltip" tabindex="0" aria-describedby="{tip_id}">'
            f"{html.escape(value)}"
            f'<span class="source-tooltip-content" id="{tip_id}" role="tooltip">'
            '<span class="source-tooltip-heading">数据来源</span>'
            f"Source: {html.escape(source)}<br>File: {html.escape(file_name)}"
            "</span></span>"
        )


def horizontal_bar_svg(
    rows: list[dict[str, Any]],
    *,
    label_key: str,
    value_key: str,
    formatter,
    aria_label: str,
) -> str:
    width, height = 960, max(320, 88 + 54 * len(rows))
    label_x, plot_x, plot_width, value_x = 14, 270, 530, 820
    maximum = max(float(row[value_key]) for row in rows) or 1.0
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(aria_label)}">',
        f'<line x1="{plot_x}" y1="34" x2="{plot_x}" y2="{height - 32}" stroke="var(--border-strong)" />',
    ]
    for index, row in enumerate(rows):
        y = 52 + index * 54
        bar_width = float(row[value_key]) / maximum * plot_width
        parts.extend(
            [
                f'<text x="{label_x}" y="{y + 17}" fill="currentColor" font-size="13">{html.escape(str(row[label_key]))}</text>',
                f'<rect x="{plot_x}" y="{y}" width="{plot_width}" height="24" rx="5" fill="var(--surface-tertiary)" />',
                f'<rect x="{plot_x}" y="{y}" width="{bar_width:.2f}" height="24" rx="5" fill="var(--blue)" />',
                f'<text x="{value_x}" y="{y + 17}" fill="currentColor" font-size="13">{html.escape(formatter(float(row[value_key])))}</text>',
            ]
        )
    parts.append("</svg>")
    return "".join(parts)


def stacked_bar_svg(rows: list[dict[str, Any]], aria_label: str) -> str:
    width, height = 960, 370
    label_x, plot_x, plot_width, value_x = 14, 270, 530, 820
    maximum = max(float(row["total"]) for row in rows) or 1.0
    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(aria_label)}">',
        f'<line x1="{plot_x}" y1="34" x2="{plot_x}" y2="338" stroke="var(--border-strong)" />',
    ]
    for index, row in enumerate(rows):
        y = 48 + index * 54
        keep_width = float(row["retained"]) / maximum * plot_width
        reject_width = float(row["rejected"]) / maximum * plot_width
        parts.extend(
            [
                f'<text x="{label_x}" y="{y + 17}" fill="currentColor" font-size="13">{html.escape(str(row["stratum"]))}</text>',
                f'<rect x="{plot_x}" y="{y}" width="{plot_width}" height="24" rx="5" fill="var(--surface-tertiary)" />',
                f'<rect x="{plot_x}" y="{y}" width="{keep_width:.2f}" height="24" rx="4" fill="var(--blue)" />',
                f'<rect x="{plot_x + keep_width:.2f}" y="{y}" width="{reject_width:.2f}" height="24" rx="4" fill="var(--muted)" />',
                f'<text x="{value_x}" y="{y + 17}" fill="currentColor" font-size="13">保留 {int(row["retained"])} / 拒绝 {int(row["rejected"])}</text>',
            ]
        )
    parts.extend(
        [
            '<rect x="270" y="332" width="14" height="14" rx="3" fill="var(--blue)" />',
            '<text x="292" y="344" fill="currentColor" font-size="12">现行保留</text>',
            '<rect x="390" y="332" width="14" height="14" rx="3" fill="var(--muted)" />',
            '<text x="412" y="344" fill="currentColor" font-size="12">现行拒绝</text>',
            "</svg>",
        ]
    )
    return "".join(parts)


def chart_card(
    chart_id: str,
    title: str,
    subtitle: str,
    fallback: str,
    note: str,
    tooltip_id: str,
    source: str,
    file_name: str,
) -> str:
    return f"""
      <div class="wide">
        <figure class="card source-figure">
          <div class="card-head"><h3>{html.escape(title)}</h3><p>{html.escape(subtitle)}</p></div>
          <div class="chart-wrap">
            <div data-recharts-chart="{html.escape(chart_id)}">
              <div class="chart-fallback" data-recharts-fallback>{fallback}</div>
              <div data-recharts-live aria-hidden="true"></div>
            </div>
          </div>
          <figcaption class="chart-note">{html.escape(note)}</figcaption>
          <button type="button" class="source-tooltip" aria-describedby="{tooltip_id}">Source
            <span class="source-tooltip-content" id="{tooltip_id}" role="tooltip">
              <span class="source-tooltip-heading">数据来源</span>
              Source: {html.escape(source)}<br>File: {html.escape(file_name)}
            </span>
          </button>
        </figure>
      </div>"""


def build() -> tuple[Path, Path]:
    summary = load_json(DATA / "s3c_atm511_knob0_summary.json")
    audit = load_csv(DATA / "s3c_atm511_w2_event_audit.csv")
    tips = SourceTips()

    source_replay = "Retained S3c atmospheric-511 event replay"
    file_summary = "s3c_atm511_knob0_summary.json"
    file_audit = "s3c_atm511_w2_event_audit.csv"
    source_brief = "Frozen Knob0 analysis brief"
    file_brief = "KNOB0_FLUORESCENCE_ARM_STRATIFICATION_BRIEF.md"

    current = next(row for row in summary["policy_yields"] if row["policy"] == "current")
    literal = summary["decision"]["literal_k2p5"]
    monotonic = summary["decision"]["monotonic_k2p5"]
    g1 = summary["g1"]
    normalization = summary["normalization"]

    policy_rows = [
        {"policy": "现行选择", "final_events": int(current["new_final_events"])},
        {"policy": "简报字面规则（k=2.5）", "final_events": int(literal["new_final_events"])},
        {"policy": "单调冻结规则（k=2.5）", "final_events": int(monotonic["new_final_events"])},
    ]
    stratum_labels = {
        "single": "单击",
        "S0_fluorescence": "S0 Ta K 标签",
        "S1_short": "S1 短臂",
        "S2_medium": "S2 中臂",
        "S3_long": "S3 长臂",
    }
    strata_order = ["single", "S0_fluorescence", "S1_short", "S2_medium", "S3_long"]
    stratum_rows = []
    for stratum in strata_order:
        selected = [row for row in audit if row["stratum"] == stratum]
        retained = sum(int(row["current_keep"]) for row in selected)
        rejected = len(selected) - retained
        stratum_rows.append(
            {
                "stratum": stratum_labels[stratum],
                "retained": retained,
                "rejected": rejected,
                "total": len(selected),
            }
        )
    strata_long = [
        {"stratum": row["stratum"], "outcome": outcome, "events": row[field]}
        for row in stratum_rows
        for outcome, field in (("现行保留", "retained"), ("现行拒绝", "rejected"))
    ]

    policy_chart = chart_card(
        "policy-final-events",
        "W2 最终 atm511 事件数",
        "同一批主动屏蔽后事件；三个冻结 k 值的结果完全相同",
        horizontal_bar_svg(
            policy_rows,
            label_key="policy",
            value_key="final_events",
            formatter=lambda value: f"{value:.0f} events",
            aria_label="现行、简报字面和单调冻结规则的最终事件数",
        ),
        "字面规则增加一个事件；单调规则没有改变任何事件。",
        "chart-source-tooltip-policy",
        source_replay,
        "s3c_atm511_knob0_policy_yields.csv",
    )
    strata_chart = chart_card(
        "w2-strata-current-outcome",
        "W2 事例按 Knob0 分层及现行结果",
        "全部 active-pass W2 事件；灰色表示现行 FoV 已拒绝",
        stacked_bar_svg(stratum_rows, "W2 事件按 Knob0 分层的现行保留与拒绝数"),
        "S1 中已有一个短臂事件被现行算法拒绝；将 S1 一律保留会复活它。",
        "chart-source-tooltip-strata",
        source_replay,
        file_audit,
    )

    table_rows = []
    for row in audit:
        lever = "—" if not row["lever_arm_mm"] else tips.wrap(f'{float(row["lever_arm_mm"]):.3f}', source_replay, file_audit)
        residual = (
            "—"
            if not row["min_cone_to_window_residual_deg"]
            else tips.wrap(f'{float(row["min_cone_to_window_residual_deg"]):.4f}', source_replay, file_audit)
        )
        table_rows.append(
            "<tr>"
            f"<td>{tips.wrap(row['event_id'], source_replay, file_audit)}</td>"
            f"<td>{tips.wrap(row['hit_count'], source_replay, file_audit)}</td>"
            f"<td>{tips.wrap(row['hit_energies_keV'], source_replay, file_audit)}</td>"
            f"<td>{'保留' if row['current_keep'] == '1' else '拒绝'}</td>"
            f"<td>{html.escape(stratum_labels.get(row['stratum'], row['stratum']))}</td>"
            f"<td>{'是' if row['fluorescence_truth_supported'] == '1' else '否'}</td>"
            f"<td>{lever}</td><td>{residual}</td>"
            f"<td>{'保留' if row['literal_k2.5_keep'] == '1' else '拒绝'}</td>"
            f"<td>{'保留' if row['monotonic_k2.5_keep'] == '1' else '拒绝'}</td>"
            "</tr>"
        )
    audit_table = (
        "<table><thead><tr><th>事件 ID</th><th>击数</th><th>像素能量 keV</th><th>现行</th>"
        "<th>分层</th><th>IA 支持 K 线</th><th>L mm</th><th>窗残差 °</th><th>字面规则</th><th>单调规则</th>"
        "</tr></thead><tbody>" + "".join(table_rows) + "</tbody></table>"
    )

    current_rate = float(normalization["current_atm511_final_rate_cps"])
    literal_rate = float(literal["new_atm511_rate_cps"])
    long_event = next(row for row in audit if row["stratum"] == "S3_long")
    tag_event = next(row for row in audit if row["fluorescence_truth_supported"] == "1")
    short_resurrected = next(
        row for row in audit if row["current_keep"] == "0" and row["literal_k2.5_keep"] == "1"
    )
    stats = summary["decision"]["additional_statistics_if_zero_rejections_persist"]

    main = f"""
    <main data-report-audience="technical">
      <article class="reading">
        <div class="kicker">KNOB0 / S3c ATMOSPHERIC 511 EVENT REPLAY</div>
        <header data-contract-section="title"><h1>S3c atm511 的 Knob0 逐事件复核</h1></header>
        <section class="summary" data-contract-section="technical-summary">
          <div class="summary-label">技术摘要</div>
          <div class="summary-body">
            <p><strong>结论：</strong>当前样本没有观察到 atm511 本底收益。按简报字面执行会把最终事件从 {tips.wrap('6', source_replay, file_summary)} 增至 {tips.wrap('7', source_replay, file_summary)}，atm511 计数率增加 {tips.wrap('16.7%', source_replay, file_summary)}；禁止复活现行 veto 的单调版本仍为 {tips.wrap('6', source_replay, file_summary)}，净变化为 {tips.wrap('0', source_replay, file_summary)}。</p>
            <p><strong>机制测量：</strong>在 {tips.wrap('5', source_replay, file_summary)} 个 W2 多击事件中发现 {tips.wrap('1', source_replay, file_summary)} 个 Ta Kα₁ 标签，并由 IA PHOT 真值支持；但该事件原本就通过，打标不带来拒除。</p>
            <p><strong>决策：</strong>不应把简报字面规则晋级到 atm511 主线。保留现行选择；若继续研究，只允许单调规则，并先增加独立统计量。</p>
          </div>
        </section>
        <section class="metrics" aria-label="关键结果">
          <div class="metric"><div class="metric-label">现行最终事件</div><div class="metric-value">{tips.wrap('6', source_replay, file_summary)}</div><div class="metric-note">{tips.wrap('8', source_replay, file_summary)} 个 active-pass W2 事件</div></div>
          <div class="metric"><div class="metric-label">字面规则</div><div class="metric-value">{tips.wrap('7', source_replay, file_summary)}</div><div class="metric-note">本底 {tips.wrap('+16.7%', source_replay, file_summary)}</div></div>
          <div class="metric"><div class="metric-label">单调规则</div><div class="metric-value">{tips.wrap('6', source_replay, file_summary)}</div><div class="metric-note">观测收益 {tips.wrap('0', source_replay, file_summary)}</div></div>
          <div class="metric"><div class="metric-label">真值支持 Ta K</div><div class="metric-value">{tips.wrap('1 / 5', source_replay, file_summary)}</div><div class="metric-note">W2 多击样本</div></div>
        </section>
      </article>

      <section data-contract-section="key-findings">
        <article class="reading"><section class="narrative">
          <h2>字面规则会增加 atm511，而单调规则没有改变事件</h2>
          <p>现行 atm511 率为 {tips.wrap(f'{current_rate:.9f} cps', source_replay, file_summary)}。字面规则变为 {tips.wrap(f'{literal_rate:.9f} cps', source_replay, file_summary)}，在假设信号完全不变时，atm511 单分量的 S/√B 因子反而是 {tips.wrap(f'{float(literal["atm_component_sqrtB_gain_signal_unchanged"]):.4f}', source_replay, file_summary)}；小于一表示变差。单调版本保持原率，因子为 {tips.wrap('1.0000', source_replay, file_summary)}。</p>
        </section></article>
        {policy_chart}

        <article class="reading"><section class="narrative">
          <h2>负收益来自“短臂一律保留”，不是 Ta K 打标</h2>
          <p>事件 {tips.wrap(short_resurrected['event_id'], source_replay, file_audit)} 是 L={tips.wrap(f'{float(short_resurrected["lever_arm_mm"]):.3f} mm', source_replay, file_audit)} 的 S1 短臂双击，现行 FoV 已拒绝；字面规则把所有 S1 当量热型保留，因此将它复活。Ta K 事件 {tips.wrap(tag_event['event_id'], source_replay, file_audit)} 原本和新规则都保留，不贡献差值。</p>
        </section></article>
        {strata_chart}

        <article class="reading"><section class="narrative">
          <h2>唯一长臂事件是真正的侧窗相交事件</h2>
          <p>事件 {tips.wrap(long_event['event_id'], source_replay, file_audit)} 的杠杆臂为 {tips.wrap(f'{float(long_event["lever_arm_mm"]):.2f} mm', source_replay, file_audit)}，质心锥到侧窗盘的最小残差仅 {tips.wrap(f'{float(long_event["min_cone_to_window_residual_deg"]):.6f}°', source_replay, file_audit)}。即使取最紧的 k={tips.wrap('2', source_brief, file_brief)}，允许量仍为 {tips.wrap(f'{float(long_event["delta_k2_deg"]):.2f}°', source_replay, file_audit)}，所以任何预先规定的 k={tips.wrap('2–3', source_brief, file_brief)} 都会保留它。</p>
        </section></article>

        <article class="reading"><section class="card table-card">
          <div class="card-head"><h3>全部 W2 事件审计表</h3><p>同一批 active-pass 事件；“窗残差”为质心 Compton 锥到侧窗盘的最小角距离。</p></div>
          <div class="table-scroll">{audit_table}</div>
        </section></article>
      </section>

      <article class="reading">
        <section class="narrative" data-contract-section="scope-data-and-metric-definitions">
          <h2>范围、数据和指标定义</h2>
          <ul>
            <li>样本是 S3c 几何下已保留的 {tips.wrap('3,000,000', source_replay, file_summary)} 个 atmospheric-511 输运事件；本工作没有新跑输运。</li>
            <li>W2 定义为 {tips.wrap('510.58–511.42 keV', source_replay, file_summary)}，主动屏蔽阈值为 {tips.wrap('50 keV', source_replay, file_summary)}。</li>
            <li>“收益”首先指 atm511 最终加权计数率的变化；S/√B 数字都明确假设信号接受度不变，因此不是测得的总灵敏度。</li>
            <li>字面规则：S0/S1 一律量热保留、S2 保持现行宽容 OR、S3 使用收紧判据。单调规则禁止任何现行拒绝事件被重新接纳。</li>
          </ul>
        </section>

        <section class="narrative" data-contract-section="methodology">
          <h2>逐事件方法与冻结判据</h2>
          <p>分析脚本顺序读取 gzip SIM，把 CC HIT 按 TP 像素聚合为能量和能量加权位置，同时保存 IA INIT 真实方向。它调用现行 Step05 代码重现 FoV 分类，再应用简报预先规定的 Ta K 线窗（±{tips.wrap('0.534 keV', source_brief, file_brief)}）、{tips.wrap('8 mm', source_brief, file_brief)} 与 {tips.wrap('20 mm', source_brief, file_brief)} 分层，以及 k={tips.wrap('2、2.5、3', source_brief, file_brief)} 的 δ(L)。W2 的原始、active-pass、最终计数和六个最终事件 ID 均与权威摘要完全一致。</p>
        </section>

        <section class="narrative" data-contract-section="limitations-uncertainty-and-robustness-checks">
          <h2>样本支持否定当前收益，但不能精确约束真实拒除率</h2>
          <ul>
            <li>单调规则在现行 {tips.wrap('6', source_replay, file_summary)} 个 survivor 中拒绝 {tips.wrap('0', source_replay, file_summary)} 个；Wilson 95% 区间仍为 {tips.wrap('0–39.0%', source_replay, file_summary)}。因此结论是“本样本未观察到收益”，不是“真实收益严格为零”。</li>
            <li>Ta K 与长臂各只有 {tips.wrap('1 / 5', source_replay, file_summary)} 个多击事件，对应比例的 Wilson 95% 区间约 {tips.wrap('3.6–62.4%', source_replay, file_summary)}。</li>
            <li>k={tips.wrap('2、2.5、3', source_brief, file_brief)} 的事件转移完全相同；长臂事件只有在不现实的 k&lt;{tips.wrap(f'{float(g1["long_event_minimum_k_to_pass"]):.5f}', source_replay, file_summary)} 时才会被拒绝。</li>
            <li>未对 S3c focused signal 做同一重放，因此不能报告真实 ΔS 或总显著性增益。像素级聚合还可能在同像素存在额外沉积时平移 K 线能量。</li>
          </ul>
          <div class="caveat"><strong>置信判断：</strong>逐事件样本结论可复核；对真实母体拒除率应“带局限分享”。目前没有证据支持把 Knob0 当作 atm511 改进。</div>
        </section>

        <section class="narrative" data-contract-section="recommended-next-steps">
          <h2>保留现行 atm511 选择，不晋级字面 Knob0</h2>
          <ol>
            <li>停止“所有 S1 短臂一律保留”的规则；它已经在真实样本中产生反向事件转移。</li>
            <li>若继续探索，只使用单调版本，并把 Ta K 标签用于诊断或从父像素合并能量后的重建，而不是自动改变 pass/fail。</li>
            <li>若目标是把零拒除时的 Wilson 95% 上限压到 {tips.wrap('10%', source_replay, file_summary)}，按当前产额线性估算需约 {tips.wrap(f'{int(stats["approx_total_generated_atm511_events_required"]):,}', source_replay, file_summary)} 个总生成事件；压到 {tips.wrap('5%', source_replay, file_summary)} 需约 {tips.wrap(f'{int(stats["approx_total_generated_atm511_events_required_for_5pct"]):,}', source_replay, file_summary)}。只有在该精度值得额外输运成本时再启动。</li>
            <li>Knob0 更可能在 prompt/delayed 多击样本中产生价值；应与 atm511 结果分开验证，不能外推。</li>
          </ol>
        </section>

        <section class="narrative" data-contract-section="further-questions">
          <h2>仍需回答的问题</h2>
          <ul>
            <li>去掉已识别的 K 光子击、并把其能量合并回母像素后，是否能恢复三击事件的有效 Compton 序列，而不是把整个事件降级？</li>
            <li>S3c focused-signal 的逐击 SIM 若重建，单调规则的信号接受度是否严格不变？</li>
            <li>在 prompt 与 delayed 样本中，S3 长臂 survivor 是否比 atm511 更常见，且是否真的偏离侧窗？</li>
          </ul>
        </section>
      </article>
    </main>"""

    shell = SHELL_TEMPLATE.read_text(encoding="utf-8")
    shell = re.sub(r'<main\b[^>]*>.*?</main>', main, shell, count=1, flags=re.DOTALL)
    shell = shell.replace('<html lang="en">', '<html lang="zh-CN">')
    shell = shell.replace("{{TITLE}}", "S3c atm511 的 Knob0 逐事件复核")
    shell = shell.replace(
        '<div class="brand"><span class="mark" aria-hidden="true"></span>Data Analytics</div>',
        '<div class="brand"><span class="mark" aria-hidden="true"></span>Knob0 Event Analytics</div>',
    )
    shell = shell.replace("{{SOURCE_AND_DATE}}", "Retained S3c atm511 · 2026-07-10")
    shell = shell.replace("{{REPORT_AUDIENCE}}", "technical")
    shell = shell.replace(
        "</head>",
        """  <style data-knob0-responsive-overrides="true">
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
        raise RuntimeError("unresolved report-shell placeholder")

    payload = {
        "charts": [
            {
                "id": "policy-final-events",
                "height": 320,
                "type": "bar",
                "dataset": {
                    "id": "policy-final-events",
                    "title": "W2 final atmospheric-511 events",
                    "data": policy_rows,
                    "chart_spec": {
                        "id": "policy-final-events",
                        "dataset": "policy-final-events",
                        "title": "W2 final atmospheric-511 events",
                        "type": "bar",
                        "encodings": {
                            "x": {"field": "policy", "type": "nominal"},
                            "y": {"field": "final_events", "label": "Final events", "type": "quantitative"},
                            "tooltip": [
                                {"field": "policy", "type": "nominal"},
                                {"field": "final_events", "label": "Final events", "type": "quantitative"},
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
                "id": "w2-strata-current-outcome",
                "height": 370,
                "type": "bar",
                "dataset": {
                    "id": "w2-strata-current-outcome",
                    "title": "W2 Knob0 strata and current disposition",
                    "data": strata_long,
                    "chart_spec": {
                        "id": "w2-strata-current-outcome",
                        "dataset": "w2-strata-current-outcome",
                        "title": "W2 Knob0 strata and current disposition",
                        "type": "bar",
                        "encodings": {
                            "x": {"field": "stratum", "type": "nominal"},
                            "y": {"field": "events", "label": "Events", "type": "quantitative"},
                            "color": {"field": "outcome", "type": "nominal"},
                            "tooltip": [
                                {"field": "stratum", "type": "nominal"},
                                {"field": "outcome", "type": "nominal"},
                                {"field": "events", "label": "Events", "type": "quantitative"},
                            ],
                        },
                        "xAxisTitle": "",
                        "yAxisTitle": "",
                        "valueFormat": "number",
                        "settings": {"orientation": "horizontal", "groupMode": "stacked"},
                    },
                },
            },
        ]
    }
    chart_map = {
        "status": "REVIEWED_CHART_MAP",
        "charts": [
            {
                "id": "policy-final-events",
                "question": "Does frozen Knob0 reduce the final atm511 W2 yield?",
                "family": "comparison",
                "type": "horizontal bar",
                "fields": ["policy", "final_events"],
                "takeaway": "Literal Knob0 worsens 6 to 7; monotonic Knob0 stays at 6.",
                "palette": "single-root blue",
            },
            {
                "id": "w2-strata-current-outcome",
                "question": "Where do current retained and rejected events sit in the frozen strata?",
                "family": "composition/comparison",
                "type": "stacked horizontal bar",
                "fields": ["stratum", "outcome", "events"],
                "takeaway": "One S1 event is already rejected, invalidating the literal keep-all-S1 assumption.",
                "palette": "blue plus neutral gray; direct labels and stacking provide non-color distinction",
            },
        ],
        "omitted_visuals": [
            {
                "candidate": "low-hit-energy histogram",
                "reason": "Only four active two-hit events fall below 200 keV; an event table is more honest than a histogram.",
            },
            {
                "candidate": "lever-arm versus ARM scatter",
                "reason": "Only five W2 multihit events; the event audit table preserves every point without implying a distribution.",
            },
        ],
    }

    REPORT.mkdir(parents=True, exist_ok=True)
    shell_path = REPORT / "s3c_atm511_knob0_report_shell.html"
    payload_path = REPORT / "s3c_atm511_knob0_report_payload.json"
    shell_path.write_text(shell, encoding="utf-8")
    payload_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (DATA / "s3c_atm511_knob0_chart_map.json").write_text(
        json.dumps(chart_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return shell_path, payload_path


if __name__ == "__main__":
    shell_output, payload_output = build()
    print(f"PASS_KNOB0_REPORT_SHELL {shell_output}")
    print(f"PASS_KNOB0_REPORT_PAYLOAD {payload_output}")
