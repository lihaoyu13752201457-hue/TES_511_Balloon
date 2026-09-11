from __future__ import annotations

import csv
import html
import json
import math
import os
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUT_HTML = ROOT / "records" / "2026-05-20_channel_geant4_group_meeting_presentation.html"
ASSET_DIR = ROOT / "records" / "channel_group_ppt_assets"
RING_CONFIG = ROOT / "data" / "channel" / "cam511_channel_rings.csv"
REFLECTIVITY_TABLE = ROOT / "data" / "reflectivity" / "WSi_511keV_parratt_grid_dense.csv"
CAL_RUN = ROOT / "runs" / "channel" / "geant4_4ring_multibounce_calibrated"
DIAG_RUN = ROOT / "runs" / "channel" / "geant4_4ring_multibounce_paper_bend_openfraction"
STRICT_RUN = ROOT / "runs" / "channel" / "geant4_4ring_multibounce_paper_formula_strict"
IO_RUN = ROOT / "runs" / "channel" / "io_contract_validation_multibounce_calibrated"
AUDIT_RUN = ROOT / "runs" / "channel" / "physics_confidence_audit" / "summary.json"
ARXIV_URL = "https://arxiv.org/abs/2206.14652"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def f(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def png_path(name: str) -> Path:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    return ASSET_DIR / name


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_geometry(rings: list[dict[str, str]]) -> Path:
    path = png_path("channel_ring_geometry.png")
    fig, ax = plt.subplots(figsize=(7.2, 6.4))
    colors = ["#1f77b4", "#2ca02c", "#d62728", "#9467bd"]
    for i, row in enumerate(rings):
        radius = float(row["radius_cm"])
        n_tiles = int(row["n_tiles"])
        theta = [2.0 * math.pi * j / n_tiles for j in range(n_tiles)]
        xs = [radius * math.cos(t) for t in theta]
        ys = [radius * math.sin(t) for t in theta]
        ax.add_patch(plt.Circle((0, 0), radius, fill=False, color=colors[i % len(colors)], lw=1.6))
        ax.scatter(xs, ys, s=18, color=colors[i % len(colors)], label=f"Ring {row['ring_id']}: r={radius:g} cm, N={n_tiles}")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x (cm)")
    ax.set_ylabel("y (cm)")
    ax.set_title("511-CAM four-ring channel geometry")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize=8)
    savefig(path)
    return path


def plot_headline(cal: dict) -> Path:
    path = png_path("channel_headline_metrics.png")
    labels = ["Transmissivity", "Effective area", "Spot D90"]
    ours = [cal["transmissivity"], cal["effective_area_cm2"], cal["spot_d90_cm"]]
    target = [cal["target_transmissivity"], cal["target_effective_area_cm2"], cal["target_spot_d90_cm"]]
    units = ["", "cm$^2$", "cm"]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5))
    for ax, label, mine, tgt, unit in zip(axes, labels, ours, target, units):
        ax.bar([0, 1], [tgt, mine], color=["#8c8c8c", "#2a6fbb"], width=0.62)
        ax.set_xticks([0, 1], ["Paper", "Geant4"])
        ax.set_title(label)
        ax.grid(axis="y", alpha=0.25)
        ymax = max(tgt, mine) * 1.18
        ax.set_ylim(0, ymax)
        for x, y in [(0, tgt), (1, mine)]:
            text = f"{y:.3g} {unit}".strip()
            ax.text(x, y + ymax * 0.035, text, ha="center", va="bottom", fontsize=9)
    fig.suptitle("Calibrated mode vs paper-level targets")
    savefig(path)
    return path


def plot_per_ring(
    cal_rows: list[dict[str, str]],
    diag_rows: list[dict[str, str]],
    strict_rows: list[dict[str, str]],
) -> Path:
    path = png_path("channel_per_ring_transmissivity.png")
    rings = [int(row["ring_id"]) for row in cal_rows]
    cal = [float(row["transmissivity"]) for row in cal_rows]
    diag = [float(row["transmissivity"]) for row in diag_rows]
    strict = [float(row["transmissivity"]) for row in strict_rows]
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.plot(rings, cal, "o-", lw=2, label="calibrated mode")
    ax.plot(rings, diag, "s-", lw=2, label="paper_bend + paper_once")
    ax.plot(rings, strict, "^-", lw=2, label="paper formula + Si absorption")
    ax.axhline(0.8, color="#555555", ls="--", lw=1, label="paper Table 2: 80%")
    ax.set_xticks(rings)
    ax.set_xlabel("ring_id")
    ax.set_ylabel("transmissivity")
    ax.set_ylim(0.0, 0.9)
    ax.set_title("Per-ring transmissivity")
    ax.grid(True, alpha=0.25)
    ax.legend()
    savefig(path)
    return path


def plot_reflectivity(cal_rows: list[dict[str, str]], diag_rows: list[dict[str, str]]) -> Path:
    path = png_path("channel_wsi_reflectivity_curve.png")
    rows = read_csv(REFLECTIVITY_TABLE)
    theta = [float(row["theta_rad"]) for row in rows if row["stack_id"] == "WSi_30_150"]
    refl = [float(row["R"]) for row in rows if row["stack_id"] == "WSi_30_150"]
    absorb = [float(row["A"]) for row in rows if row["stack_id"] == "WSi_30_150"]
    cal_theta = [float(row["theta_rad"]) for row in cal_rows]
    diag_theta = [float(row["theta_rad"]) for row in diag_rows]
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.semilogx(theta, refl, color="#2a6fbb", lw=2, label="R")
    ax.semilogx(theta, absorb, color="#c43c39", lw=2, label="A")
    ax.axvspan(min(cal_theta), max(cal_theta), color="#2a6fbb", alpha=0.14, label="calibrated theta range")
    ax.axvspan(min(diag_theta), max(diag_theta), color="#c43c39", alpha=0.12, label="diagnostic theta range")
    ax.set_xlabel("grazing angle theta (rad)")
    ax.set_ylabel("probability per bounce")
    ax.set_ylim(-0.03, 1.03)
    ax.set_title("W/Si 30/150 nm 511 keV table-driven R/A")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend()
    savefig(path)
    return path


def plot_focal_spot() -> Path:
    path = png_path("channel_focal_spot.png")
    rows = read_csv(CAL_RUN / "phase_space.csv")
    stride = max(1, len(rows) // 8000)
    xs = [float(row["x_mm"]) / 10.0 for row in rows[::stride]]
    ys = [float(row["y_mm"]) / 10.0 for row in rows[::stride]]
    radii = sorted(math.hypot(float(row["x_mm"]), float(row["y_mm"])) for row in rows)
    d90_cm = 2.0 * radii[math.ceil(0.9 * len(radii)) - 1] / 10.0
    fig, ax = plt.subplots(figsize=(6.2, 6.2))
    ax.scatter(xs, ys, s=2, alpha=0.25, color="#2a6fbb")
    ax.add_patch(plt.Circle((0, 0), d90_cm / 2.0, fill=False, color="#c43c39", lw=2, label=f"D90={d90_cm:.2f} cm"))
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x at focal plane (cm)")
    ax.set_ylabel("y at focal plane (cm)")
    ax.set_title("12 m focal-plane phase space")
    ax.grid(True, alpha=0.25)
    ax.legend()
    savefig(path)
    return path


def write_wrl(rings: list[dict[str, str]]) -> Path:
    path = CAL_RUN / "channel_4ring_multibounce_scene.wrl"
    colors = [
        (0.12, 0.42, 0.70),
        (0.17, 0.63, 0.17),
        (0.84, 0.15, 0.16),
        (0.58, 0.40, 0.74),
    ]
    lines = [
        "#VRML V2.0 utf8",
        'WorldInfo { title "511-CAM four-ring channel optics parameterized scene" }',
        "NavigationInfo { type [\"EXAMINE\", \"ANY\"] }",
        "Background { skyColor [ 1 1 1 ] }",
        "Viewpoint { position 0 -13 12 orientation 1 0 0 0.82 description \"four-ring channel optics\" }",
    ]
    for i, row in enumerate(rings):
        radius = float(row["radius_cm"])
        n_tiles = int(row["n_tiles"])
        thickness = float(row["thickness_mm"]) / 10.0
        width = float(row["width_cm"])
        color = colors[i % len(colors)]
        for tile in range(n_tiles):
            phi = 2.0 * math.pi * tile / n_tiles
            x = radius * math.cos(phi)
            y = radius * math.sin(phi)
            lines.extend(
                [
                    f"Transform {{ translation {x:.6g} {y:.6g} 0 rotation 0 0 1 {phi:.9g}",
                    "  children [",
                    "    Shape {",
                    f"      appearance Appearance {{ material Material {{ diffuseColor {color[0]} {color[1]} {color[2]} transparency 0.18 }} }}",
                    f"      geometry Box {{ size {thickness:.6g} {width:.6g} 0.06 }}",
                    "    }",
                    "  ]",
                    "}",
                ]
            )
    lines.extend(
        [
            "Transform { translation 0 0 -0.08 children [",
            "  Shape { appearance Appearance { material Material { diffuseColor 0.2 0.2 0.2 transparency 0.65 } }",
            "    geometry Cylinder { radius 4.5 height 0.015 } }",
            "] }",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def table_html(rows: Iterable[Iterable[object]], headers: Iterable[str]) -> str:
    header_html = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def rel(path: Path) -> str:
    return html.escape(path.relative_to(OUT_HTML.parent).as_posix())


def build_html() -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    plt.rcParams["font.family"] = "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False
    rings = read_csv(RING_CONFIG)
    cal = read_json(CAL_RUN / "summary.json")
    diag = read_json(DIAG_RUN / "summary.json")
    strict = read_json(STRICT_RUN / "summary.json")
    cal_rows = read_csv(CAL_RUN / "per_ring_summary.csv")
    diag_rows = read_csv(DIAG_RUN / "per_ring_summary.csv")
    strict_rows = read_csv(STRICT_RUN / "per_ring_summary.csv")
    io = read_json(IO_RUN / "summary.json")
    audit = read_json(AUDIT_RUN)

    assets = {
        "geometry": plot_geometry(rings),
        "headline": plot_headline(cal),
        "per_ring": plot_per_ring(cal_rows, diag_rows, strict_rows),
        "reflectivity": plot_reflectivity(cal_rows, diag_rows),
        "spot": plot_focal_spot(),
    }
    wrl_path = write_wrl(rings)

    ring_table = table_html(
        (
            [
                row["ring_id"],
                row["radius_cm"],
                row["bending_angle_deg"],
                row["length_cm"],
                row["width_cm"],
                row["thickness_mm"],
                row["n_tiles"],
            ]
            for row in rings
        ),
        ["ring", "半径 cm", "弯转角 deg", "长度 cm", "宽 cm", "厚 mm", "tile数"],
    )

    cal_table = table_html(
        (
            [
                row["ring_id"],
                row["n_bounce"],
                f(float(row["theta_rad"]), 7),
                f(float(row["mean_R"]), 4),
                f(float(row["transmissivity"]), 4),
                row["n_primaries"],
            ]
            for row in cal_rows
        ),
        ["ring", "bounce", "theta rad", "mean R", "透过率", "事件数"],
    )

    diag_table = table_html(
        (
            [
                row["ring_id"],
                row["n_bounce"],
                f(float(row["theta_rad"]), 7),
                f(float(row["mean_R"]), 4),
                f(float(row["transmissivity"]), 4),
                row["n_primaries"],
            ]
            for row in diag_rows
        ),
        ["ring", "bounce", "theta rad", "mean R", "透过率", "事件数"],
    )

    strict_table = table_html(
        (
            [
                row["ring_id"],
                row["n_bounce"],
                f(float(row["theta_rad"]), 7),
                f(float(row["mean_R"]), 4),
                f(float(row["path_survival"]), 4),
                row["n_path_absorbed"],
                f(float(row["transmissivity"]), 4),
                row["n_primaries"],
            ]
            for row in strict_rows
        ),
        ["ring", "bounce", "theta rad", "mean R", "Si路径透过", "路径吸收数", "透过率", "事件数"],
    )

    headline_rows = [
        [
            "Channel 透过率",
            "80%",
            f"{cal['transmissivity'] * 100:.2f}%",
            f"{diag['transmissivity'] * 100:.2f}%",
            f"{strict['transmissivity'] * 100:.2f}%",
        ],
        [
            "9 cm optics 有效面积",
            "50.89 cm2",
            f"{cal['effective_area_cm2']:.2f} cm2",
            f"{diag['effective_area_cm2']:.2f} cm2",
            f"{strict['effective_area_cm2']:.2f} cm2",
        ],
        [
            "焦斑直径",
            "3.6 cm",
            f"{cal['spot_d90_cm']:.2f} cm",
            f"{diag['spot_d90_cm']:.2f} cm",
            f"{strict['spot_d90_cm']:.2f} cm",
        ],
        [
            "焦距",
            "12 m",
            f"{cal['focal_length_mm'] / 1000:.1f} m",
            f"{diag['focal_length_mm'] / 1000:.1f} m",
            f"{strict['focal_length_mm'] / 1000:.1f} m",
        ],
    ]
    headline_table = table_html(
        headline_rows,
        ["指标", "CAM511目标/表2", "本次校准Geant4", "弯角+open诊断", "弯角+open+Si吸收诊断"],
    )

    css = """
    :root {
      color-scheme: light;
      --ink: #17202a;
      --muted: #566573;
      --line: #d7dde5;
      --blue: #1f5f99;
      --red: #a83a32;
      --bg: #f4f6f8;
      --paper: #ffffff;
    }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans CJK SC", "Microsoft YaHei", Arial, sans-serif;
      line-height: 1.55;
    }
    .deck {
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 18px 70px;
    }
    section.slide {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 34px 42px;
      margin: 0 0 26px;
      box-shadow: 0 10px 24px rgba(31, 45, 61, 0.08);
    }
    h1, h2 {
      margin: 0 0 14px;
      line-height: 1.18;
      letter-spacing: 0;
    }
    h1 { font-size: 36px; }
    h2 { font-size: 27px; color: var(--blue); }
    h3 { margin: 22px 0 8px; font-size: 18px; }
    p { margin: 9px 0; }
    .subtitle { color: var(--muted); font-size: 18px; max-width: 900px; }
    .grid2 {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 24px;
      align-items: start;
    }
    .grid3 {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 16px;
    }
    .metric {
      border-top: 4px solid var(--blue);
      background: #f8fafc;
      padding: 14px 16px;
      border-radius: 6px;
    }
    .metric b { display: block; font-size: 24px; }
    .metric span { color: var(--muted); font-size: 14px; }
    .warn { border-left: 4px solid var(--red); padding: 10px 14px; background: #fff7f5; }
    .ok { border-left: 4px solid #2f7d45; padding: 10px 14px; background: #f4fbf6; }
    figure { margin: 16px 0 0; }
    img { max-width: 100%; border: 1px solid var(--line); border-radius: 6px; background: white; }
    figcaption { color: var(--muted); font-size: 13px; margin-top: 6px; }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0 18px;
      font-size: 14px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 8px 9px;
      text-align: left;
      vertical-align: top;
    }
    th { background: #eef3f8; }
    code {
      background: #eef1f5;
      padding: 2px 5px;
      border-radius: 4px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.92em;
    }
    .small { color: var(--muted); font-size: 13px; }
    .flow {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin-top: 16px;
    }
    .flow div {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      min-height: 92px;
      background: #fbfcfd;
    }
    .flow b { display: block; color: var(--blue); margin-bottom: 6px; }
    @media (max-width: 860px) {
      .grid2, .grid3, .flow { grid-template-columns: 1fr; }
      section.slide { padding: 26px 22px; }
      h1 { font-size: 29px; }
      h2 { font-size: 23px; }
    }
    """

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>511-CAM Channel Optics Geant4 组会报告</title>
  <style>{css}</style>
</head>
<body>
<main class="deck">
  <section class="slide">
    <h1>511-CAM Channel Optics：Geant4 多次反射实现审阅</h1>
    <p class="subtitle">目标是把 CAM511 论文中的 511 keV channeling concentrator 从纯 IDL/ray tracing 描述推进到可运行、可审计、可接 detector handoff 的 Geant4 scaffold。</p>
    <div class="grid3">
      <div class="metric"><b>{cal['transmissivity'] * 100:.2f}%</b><span>校准模式 channel 透过率，目标 80%</span></div>
      <div class="metric"><b>{cal['effective_area_cm2']:.2f} cm2</b><span>9 cm optics 有效面积，目标 50.89 cm2</span></div>
      <div class="metric"><b>{cal['spot_d90_cm']:.2f} cm</b><span>12 m 焦平面 D90，目标 3.6 cm</span></div>
    </div>
    <p class="ok">本次没有修改 Geant4 底层源码；实现位于应用层 process 和输出表。</p>
    <p class="warn">物理边界：这已经是可运行的四环、多次反射、表驱动 Channel scaffold，但性能不是100%第一性原理闭合；它仍是对CAM511 headline指标的参数化校准复现。</p>
  </section>

  <section class="slide">
    <h2>1. 和 CAM511 论文对齐的输入</h2>
    <p>论文给出的 channel optics 概念是：用弯曲 W/Si 多层膜结构，通过总外反射把 511 keV 光子汇聚到 12 m 焦平面。本文采用这些公开参数作为 Geant4 输入边界。</p>
    <p>短引公式：<code>P(E)=Reflectance × Absorption × Open Fraction</code>。这里按论文含义将 open fraction 理解为 spacer 厚度除以双层周期，W/Si 为 150/(30+150)。</p>
    {ring_table}
    <p class="small">来源：Shirazi et al., arXiv:2206.14652；本地文本与 PDF 位于 <code>records/channel_external_sources/</code>。</p>
  </section>

  <section class="slide">
    <h2>2. 几何对象：四环 lens，而不是 Laue lens</h2>
    <div class="grid2">
      <div>
        <p>Laue 和 Channel 已分成两套系统清单：<code>systems/laue/</code> 与 <code>systems/channel/</code>。Channel 的当前主线文件是 <code>geant4_app/src/channel_4ring_multibounce_demo.cc</code>。</p>
        <p>四个 ring 的半径来自论文；tile 数按 1 cm segment 宽度近似周向排布，总数为 85，接近论文表2的约 83 个 multilayers。这个差异被保留为工程离散化误差，不强行改数字。</p>
      </div>
      <figure>
        <img src="{rel(assets['geometry'])}" alt="Channel ring geometry">
        <figcaption>按当前 CSV 生成的四环几何示意。</figcaption>
      </figure>
    </div>
  </section>

  <section class="slide">
    <h2>3. Geant4 中做了什么</h2>
    <div class="flow">
      <div><b>输入</b>读取 ring CSV 和 W/Si 511 keV R/A/T 表。</div>
      <div><b>发射</b>每个 event 指向一个 channel tile 中心，保证进入 optics process。</div>
      <div><b>反射</b>在 ChannelTile 边界触发自定义离散过程，逐 bounce 查表并采样。</div>
      <div><b>记录</b>每次 BOUNCE/ABSORB/LEAK/EXIT 写入 <code>optics_history.csv</code>。</div>
      <div><b>交接</b>幸存光子写入 12 m 焦平面的 <code>phase_space.csv</code>。</div>
    </div>
    <p>这个做法的核心价值是把“透过率一个数”展开成可审核的 per-bounce provenance：事件号、ring、tile、theta、R/A/T、入射方向、出射方向和终止原因都可查。</p>
  </section>

  <section class="slide">
    <h2>4. 为什么没有改 Geant4 源码</h2>
    <p>500-511 keV 的 Channel optics 不要求改 Geant4 kernel。这里需要的是几何、边界过程、概率表和 phase-space handoff；这些都可以在用户应用层完成。</p>
    <p>当前 C++ app 只新增了一个自定义 <code>G4VDiscreteProcess</code>，在 Tile 边界执行 channel 多次反射逻辑。Geant4 负责事件循环、粒子、材料、几何边界和随机数；光学物理用我们自己的 W/Si 表驱动过程表达。</p>
    <p class="ok">审计字段 <code>geant4_bottom_code_modified=false</code> 已写入 summary。这样不会污染 MEGAlib 自带 Geant4，也不会把 11.4 环境和 MEGAlib 的 10.2.3 环境混在一起。</p>
  </section>

  <section class="slide">
    <h2>5. 结果：校准模式和论文 headline 对齐</h2>
    {headline_table}
    <figure>
      <img src="{rel(assets['headline'])}" alt="Headline metrics comparison">
      <figcaption>校准模式没有在最终有效面积上硬乘校正因子，但 theta/bounce bookkeeping 本身是为了复现论文尺度而校准的；不能把它说成完整物理预测。</figcaption>
    </figure>
  </section>

  <section class="slide">
    <h2>6. 逐环结果：能看到每一环怎么贡献</h2>
    {cal_table}
    <figure>
      <img src="{rel(assets['per_ring'])}" alt="Per ring transmissivity">
	      <figcaption>校准模式逐环稳定在 80% 附近；两个诊断模式把弯角、open fraction 和路径吸收逐项打开，显示公开参数直接组合会明显下降。</figcaption>
    </figure>
  </section>

  <section class="slide">
    <h2>7. W/Si 表和焦平面相空间</h2>
    <div class="grid2">
      <figure>
        <img src="{rel(assets['reflectivity'])}" alt="W Si reflectivity curve">
        <figcaption>每次 bounce 都使用 <code>WSi_511keV_parratt_grid_dense.csv</code> 查表。</figcaption>
      </figure>
      <figure>
        <img src="{rel(assets['spot'])}" alt="Focal spot">
        <figcaption>100k 主 run 的幸存光子焦平面分布，D90 与 3.6 cm 目标一致。</figcaption>
      </figure>
    </div>
  </section>

  <section class="slide">
	    <h2>8. 严格诊断：剩下的物理漏洞在哪里</h2>
	    <p>诊断模式把论文给出的 ring bend angle 转成多次小角反射，并额外应用一次 open fraction。这个模式不是为了“对齐”，而是为了检查如果机械使用公开参数会发生什么。</p>
	    {diag_table}
	    <p>进一步把 Si 通道长度吸收作为独立损失打开，得到下面这个“论文公式压力测试”。这里的 <code>path_absorption_policy=si_length</code> 用的是 xraydb/Si 在 511 keV 的线性衰减系数，按每环几何长度拆到每次 bounce。</p>
	    {strict_table}
	    <p class="warn">弯角+open 诊断整体透过率 {diag['transmissivity'] * 100:.2f}%，再加入 Si 路径吸收后为 {strict['transmissivity'] * 100:.2f}%。这比论文 80% / 50.89 cm2 低很多。我的判断：差异最可能来自原 IDL channel path/open-area/absorption 记账没有公开，而不是 Geant4 不能模拟 511 keV。</p>
  </section>

  <section class="slide">
    <h2>9. 追加复核：不是100%物理闭合</h2>
    <p>追加审计结论：<b>{html.escape(audit['status'])}</b>。</p>
    <p>W/Si 临界角量级检查给出 <code>{audit['critical_angle_rad']:.6g} rad</code>，校准 theta 在合理局部角度范围内；但是若按 <code>2Ntheta</code> 积累论文弯转角，四个 ring 需要约 6-13 次反射，而当前校准 bookkeeping 是 1/2/2/3 次。</p>
    <p class="warn">因此当前性能可信用于工程链路和benchmark handoff，不可信用于“从公开几何独立预测511-CAM效率”的论文级声明。</p>
    <p>详细审计：<code>records/2026-05-20_channel_physics_confidence_audit.html</code></p>
  </section>

  <section class="slide">
    <h2>10. 可复现实验和文件位置</h2>
    <p>主实现：</p>
    <p><code>geant4_app/src/channel_4ring_multibounce_demo.cc</code></p>
    <p>主运行：</p>
    <p><code>runs/channel/geant4_4ring_multibounce_calibrated</code></p>
    <p>几何审阅 WRL：</p>
    <p><code>{html.escape(wrl_path.relative_to(ROOT).as_posix())}</code></p>
	    <p>诊断运行：</p>
	    <p><code>runs/channel/geant4_4ring_multibounce_paper_bend_openfraction</code></p>
	    <p>论文公式压力测试：</p>
	    <p><code>runs/channel/geant4_4ring_multibounce_paper_formula_strict</code></p>
    <p>IO contract 校验状态：<b>{'PASS' if io['ok'] else 'FAIL'}</b>，校验表数 {io['n_tables']}。</p>
    <p>推荐运行命令：</p>
    <p><code>source /home/ubuntu/software/geant4-11.4.0-install/bin/geant4.sh</code></p>
    <p><code>/tmp/opticsim-build-g4-11.4.0/channel_4ring_multibounce_demo --n 100000 --seed 20260520 --out runs/channel/geant4_4ring_multibounce_calibrated</code></p>
  </section>

  <section class="slide">
    <h2>11. 审核结论</h2>
    <p>如果把目标定义为“在 Geant4 11.4 中建立可运行、可审计、四环、W/Si 表驱动、多次反射、可接 detector 的 Channel scaffold”，这一步已经完成。</p>
    <p>如果把目标定义为“完全复现 CAM511/IDL 的 wall-by-wall channel optics 物理”，不能宣称 100%。当前最硬的证据正是诊断模式和追加审计：公开参数直接组合时不能自然回到 80%，所以还需要原 IDL path model 或论文作者级别的几何细节。</p>
    <p class="ok">因此当前可信表述是：工程链路完成，论文 headline 指标已校准对齐；底层 Geant4 未改；剩余物理不确定性被定位到 Channel path/open-fraction 记账。</p>
    <p class="small">论文链接：<a href="{ARXIV_URL}">{ARXIV_URL}</a>。本报告由 <code>analysis/build_channel_group_meeting_ppt.py</code> 从本地 run 结果生成。</p>
  </section>
</main>
</body>
</html>
"""
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html_text, encoding="utf-8")
    print(OUT_HTML)


if __name__ == "__main__":
    build_html()
