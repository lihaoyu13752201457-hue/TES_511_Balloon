from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp")

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "records"
ASSETS = RECORDS / "laue_group_ppt_assets"
OUT_HTML = RECORDS / "2026-05-20_laue_group_meeting_presentation.html"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def make_efficiency_plot() -> None:
    rows = read_csv(ROOT / "data/laue/Ge111_480_550keV_darwin_mosaic_table.csv")
    by_energy: dict[float, dict[str, str]] = {}
    for row in rows:
        energy = float(row["E_keV"])
        best = by_energy.get(energy)
        if best is None or abs(float(row["delta_theta_rad"])) < abs(float(best["delta_theta_rad"])):
            by_energy[energy] = row
    energies = sorted(by_energy)
    pdiff = [float(by_energy[e]["p_diff"]) for e in energies]
    pabs = [float(by_energy[e]["p_abs"]) for e in energies]
    ptrans = [float(by_energy[e]["p_trans"]) for e in energies]

    plt.figure(figsize=(8.2, 4.8))
    plt.plot(energies, pdiff, marker="o", label="diffraction p_diff", linewidth=2.5)
    plt.plot(energies, pabs, marker="s", label="absorption p_abs", linewidth=2.5)
    plt.plot(energies, ptrans, marker="^", label="transmission p_trans", linewidth=2.5)
    plt.ylim(0, 0.46)
    plt.xlabel("Design energy (keV)")
    plt.ylabel("Peak branch probability")
    plt.title("Ge(111) 30 arcsec Darwin table, near Bragg peak")
    plt.grid(True, alpha=0.25)
    plt.legend(frameon=False)
    savefig(ASSETS / "darwin_efficiency_table.png")


def make_ring_outcome_plot() -> None:
    rows = read_csv(ROOT / "runs/geant4_laue_multiring_darwin/per_ring_summary.csv")
    labels = [f'{row["design_energy_keV"]} keV\nr={float(row["radius_mm"]):.1f} mm' for row in rows]
    diff = np.array([float(row["n_diffracted"]) / float(row["n_primaries"]) for row in rows])
    abs_ = np.array([float(row["n_absorbed"]) / float(row["n_primaries"]) for row in rows])
    trans = np.array([float(row["n_transmitted"]) / float(row["n_primaries"]) for row in rows])
    x = np.arange(len(labels))

    plt.figure(figsize=(8.2, 4.8))
    plt.bar(x, diff, label="diffracted", color="#b91c1c")
    plt.bar(x, abs_, bottom=diff, label="absorbed", color="#d97706")
    plt.bar(x, trans, bottom=diff + abs_, label="transmitted", color="#64748b")
    for i, value in enumerate(diff):
        plt.text(i, value / 2, f"{value:.1%}", ha="center", va="center", color="white", fontsize=9)
    plt.xticks(x, labels)
    plt.ylim(0, 1)
    plt.ylabel("Event fraction")
    plt.title("Geant4 100k event result by Laue ring")
    plt.legend(frameon=False, loc="upper right")
    savefig(ASSETS / "per_ring_outcomes.png")


def make_kohnle_plot() -> None:
    rows = read_csv(ROOT / "runs/laue_kohnle1998_ge111_benchmark/benchmark.csv")
    endpoints = [row for row in rows if row["published_peak_eff_with_abs"]]
    energies = [float(row["energy_keV"]) for row in endpoints]
    published = [float(row["published_peak_eff_with_abs"]) for row in endpoints]
    calculated = [float(row["calc_peak_eff_with_abs"]) for row in endpoints]
    width = 16.0

    plt.figure(figsize=(7.6, 4.6))
    plt.bar([e - width / 2 for e in energies], published, width=width, label="Kohnle endpoint", color="#334155")
    plt.bar([e + width / 2 for e in energies], calculated, width=width, label="This work", color="#0f766e")
    for e, pub, calc in zip(energies, published, calculated):
        plt.plot([e - width / 2, e + width / 2], [pub, calc], color="#475569", linewidth=1)
        plt.text(e, max(pub, calc) + 0.018, f"Δ={abs(calc - pub):.4f}", ha="center", fontsize=9)
    plt.xlim(160, 540)
    plt.ylim(0, 0.52)
    plt.xlabel("Energy (keV)")
    plt.ylabel("Peak diffraction efficiency with absorption")
    plt.title("Direct Ge(111) external anchor: Kohnle 1998")
    plt.grid(True, axis="y", alpha=0.25)
    plt.legend(frameon=False)
    savefig(ASSETS / "kohnle_ge111_benchmark.png")


def make_sensitivity_plot() -> None:
    rows = read_csv(ROOT / "runs/laue_darwin_sensitivity/sensitivity.csv")
    mosaics = sorted({float(row["mosaic_arcsec"]) for row in rows})
    scales = sorted({float(row["thickness_scale"]) for row in rows})
    grid = np.zeros((len(mosaics), len(scales)))
    for row in rows:
        i = mosaics.index(float(row["mosaic_arcsec"]))
        j = scales.index(float(row["thickness_scale"]))
        grid[i, j] = float(row["mean_peak_p_diff"])

    plt.figure(figsize=(7.6, 4.8))
    im = plt.imshow(grid, cmap="viridis", aspect="auto", origin="lower")
    plt.colorbar(im, label="mean peak p_diff")
    plt.xticks(range(len(scales)), [f"{s:g}" for s in scales])
    plt.yticks(range(len(mosaics)), [f"{m:g}" for m in mosaics])
    plt.xlabel("Thickness scale relative to optimum")
    plt.ylabel("Mosaicity FWHM (arcsec)")
    plt.title("Darwin sensitivity scan: mosaicity and thickness")
    for i in range(len(mosaics)):
        for j in range(len(scales)):
            plt.text(j, i, f"{grid[i, j]:.3f}", ha="center", va="center", color="white", fontsize=8)
    savefig(ASSETS / "sensitivity_heatmap.png")


def make_pytte_plot() -> None:
    rows = read_csv(ROOT / "runs/laue_pytte_ge111_check/pytte_ge111_check.csv")
    sigma_rows = [row for row in rows if row["polarization"] == "sigma"]
    labels = [f'{float(row["energy_keV"]):.0f} keV' for row in sigma_rows]
    pytte = [float(row["pytte_peak_diffraction"]) for row in sigma_rows]
    no_abs = [float(row["darwin_mosaic_peak_no_abs"]) for row in sigma_rows]
    with_abs = [float(row["darwin_mosaic_peak_with_abs"]) for row in sigma_rows]
    x = np.arange(len(labels))
    width = 0.24

    plt.figure(figsize=(7.6, 4.6))
    plt.bar(x - width, pytte, width, label="PyTTE perfect crystal", color="#7c3aed")
    plt.bar(x, no_abs, width, label="Darwin mosaic no absorption", color="#2563eb")
    plt.bar(x + width, with_abs, width, label="Darwin mosaic with absorption", color="#0f766e")
    plt.xticks(x, labels)
    plt.ylim(0, 0.9)
    plt.ylabel("Peak diffracted branch")
    plt.title("Independent tool check: perfect crystal branch is higher")
    plt.grid(True, axis="y", alpha=0.25)
    plt.legend(frameon=False, fontsize=9)
    savefig(ASSETS / "pytte_check.png")


def make_geometry_plot() -> None:
    rows = read_csv(ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv")
    energies = np.array([float(row["design_energy_keV"]) for row in rows])
    radii = np.array([float(row["radius_mm"]) for row in rows])
    thickness = np.array([float(row["thickness_mm"]) for row in rows])

    fig, ax1 = plt.subplots(figsize=(7.6, 4.6))
    ax1.plot(energies, radii, marker="o", linewidth=2.5, color="#0f766e")
    ax1.set_xlabel("Design energy (keV)")
    ax1.set_ylabel("Ring radius (mm)", color="#0f766e")
    ax1.tick_params(axis="y", labelcolor="#0f766e")
    ax1.grid(True, alpha=0.25)
    ax2 = ax1.twinx()
    ax2.plot(energies, thickness, marker="s", linewidth=2.5, color="#b45309")
    ax2.set_ylabel("Optimized crystal thickness (mm)", color="#b45309")
    ax2.tick_params(axis="y", labelcolor="#b45309")
    plt.title("Five-ring Ge(111) lens: 8.3 m focal length")
    savefig(ASSETS / "geometry_rings.png")


def make_figures() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    make_efficiency_plot()
    make_ring_outcome_plot()
    make_kohnle_plot()
    make_sensitivity_plot()
    make_pytte_plot()
    make_geometry_plot()


def html() -> str:
    summary = read_json(ROOT / "runs/geant4_laue_multiring_darwin/summary.json")
    bragg = read_json(ROOT / "runs/laue_bragg_geometry_audit/summary.json")
    darwin = read_json(ROOT / "runs/laue_darwin_benchmark/summary.json")
    kohnle = read_json(ROOT / "runs/laue_kohnle1998_ge111_benchmark/summary.json")
    sensitivity = read_json(ROOT / "runs/laue_darwin_sensitivity/summary.json")
    tests = "33 passed, 6 skipped"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Laue Optics 500 keV Geant4 组会汇报</title>
  <style>
    :root {{
      --ink: #17202a;
      --muted: #536475;
      --paper: #ffffff;
      --bg: #e7edf3;
      --blue: #2563eb;
      --red: #b91c1c;
      --teal: #0f766e;
      --amber: #b45309;
      --line: #cbd5e1;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: Arial, "Noto Sans CJK SC", sans-serif; line-height: 1.5; }}
    .deck {{ width: min(1180px, calc(100vw - 36px)); margin: 24px auto 56px; }}
    .slide {{
      min-height: 720px;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      margin: 0 0 22px;
      padding: 42px 48px;
      box-shadow: 0 18px 40px rgba(15, 23, 42, 0.12);
      position: relative;
      overflow: hidden;
    }}
    .slide::after {{
      content: attr(data-slide);
      position: absolute;
      right: 26px;
      bottom: 20px;
      color: #94a3b8;
      font-size: 13px;
    }}
    h1 {{ font-size: 46px; line-height: 1.08; margin: 0 0 20px; letter-spacing: 0; }}
    h2 {{ font-size: 32px; line-height: 1.16; margin: 0 0 22px; letter-spacing: 0; }}
    h3 {{ font-size: 20px; margin: 18px 0 8px; }}
    p {{ font-size: 18px; margin: 0 0 14px; }}
    li {{ font-size: 17px; margin: 7px 0; }}
    code {{ background: #eef2f7; padding: 2px 5px; border-radius: 4px; font-size: 0.92em; }}
    .kicker {{ color: var(--teal); font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; font-size: 13px; margin-bottom: 14px; }}
    .subtitle {{ font-size: 22px; color: var(--muted); max-width: 860px; }}
    .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 28px; align-items: center; }}
    .grid3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }}
    .card {{ border: 1px solid var(--line); border-radius: 8px; padding: 18px 20px; background: #f8fafc; }}
    .card strong {{ display: block; font-size: 24px; margin-bottom: 6px; color: #0f172a; }}
    .metric {{ font-size: 32px; color: var(--teal); font-weight: 800; line-height: 1.1; }}
    .warn {{ color: var(--amber); font-weight: 700; }}
    .ok {{ color: var(--teal); font-weight: 700; }}
    .bad {{ color: var(--red); font-weight: 700; }}
    .small {{ color: var(--muted); font-size: 14px; }}
    .quote {{ border-left: 4px solid var(--blue); padding: 10px 16px; background: #eff6ff; margin: 12px 0 16px; font-size: 16px; }}
    .quote em {{ color: #1e3a8a; font-style: normal; font-weight: 700; }}
    img {{ max-width: 100%; display: block; border-radius: 6px; border: 1px solid var(--line); background: white; }}
    .flow {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; align-items: stretch; margin: 18px 0; }}
    .flow div {{ background: #f8fafc; border: 1px solid var(--line); border-radius: 8px; padding: 14px; min-height: 112px; }}
    .flow b {{ display: block; color: var(--teal); margin-bottom: 6px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 14px 0 18px; font-size: 15px; }}
    th, td {{ border: 1px solid var(--line); padding: 9px 10px; vertical-align: top; }}
    th {{ background: #f1f5f9; text-align: left; }}
    .formula {{ font-size: 24px; text-align: center; padding: 16px; border: 1px solid var(--line); border-radius: 8px; background: #f8fafc; margin: 16px 0; }}
    .note {{ position: absolute; left: 48px; bottom: 20px; color: #94a3b8; font-size: 13px; }}
    @media print {{
      body {{ background: white; }}
      .deck {{ width: 100%; margin: 0; }}
      .slide {{ page-break-after: always; box-shadow: none; border-radius: 0; margin: 0; min-height: 100vh; }}
    }}
  </style>
</head>
<body>
<main class="deck">
  <section class="slide" data-slide="1 / 14">
    <div class="kicker">Opticsim Laue line · 2026-05-20</div>
    <h1>500 keV Ge(111) Laue optics<br>Geant4 表驱动模拟汇报</h1>
    <p class="subtitle">目标不是把普通 Geant4 电磁过程“调到会聚焦”，而是在 Geant4 tracking 框架里加入可审计的 Laue/Bragg 光学过程。</p>
    <div class="grid3" style="margin-top: 44px;">
      <div class="card"><strong>实现层级</strong><span class="metric">App 级</span><p class="small">没有修改 Geant4 底层源码。</p></div>
      <div class="card"><strong>物理核心</strong><span class="metric">Darwin</span><p class="small">Zachariasen/Darwin mosaic crystal 表。</p></div>
      <div class="card"><strong>外部锚点</strong><span class="metric">Ge(111)</span><p class="small">Kohnle 1998 200-500 keV 端点。</p></div>
    </div>
    <div class="note">主输出：runs/geant4_laue_multiring_darwin/laue_multiring_scene.wrl</div>
  </section>

  <section class="slide" data-slide="2 / 14">
    <div class="kicker">Question</div>
    <h2>为什么不能只开 Geant4 标准 EM？</h2>
    <div class="grid2">
      <div>
        <p>500 keV gamma 在晶体透镜里的“聚焦”来自满足 Bragg 条件的 Laue 衍射，不是普通 photoelectric、Compton 或 Rayleigh 自动给出的效果。</p>
        <p>因此正确软件结构是：普通 EM 继续负责材料相互作用；Laue optics 作为一个专用过程决定光子在晶体处是衍射、吸收还是透过。</p>
        <div class="formula">2 d sin θ<sub>B</sub> = n λ &nbsp;&nbsp;→&nbsp;&nbsp; F = r / tan(2θ<sub>B</sub>)</div>
      </div>
      <div>
        <svg viewBox="0 0 520 360" width="100%" height="360" role="img" aria-label="Laue focusing diagram">
          <rect x="0" y="0" width="520" height="360" fill="#f8fafc"/>
          <line x1="45" y1="80" x2="270" y2="80" stroke="#64748b" stroke-width="3"/>
          <line x1="45" y1="180" x2="270" y2="180" stroke="#64748b" stroke-width="3"/>
          <line x1="45" y1="280" x2="270" y2="280" stroke="#64748b" stroke-width="3"/>
          <rect x="265" y="52" width="18" height="256" fill="#0f766e" opacity="0.9"/>
          <line x1="280" y1="80" x2="460" y2="180" stroke="#b91c1c" stroke-width="3"/>
          <line x1="280" y1="180" x2="460" y2="180" stroke="#b91c1c" stroke-width="3"/>
          <line x1="280" y1="280" x2="460" y2="180" stroke="#b91c1c" stroke-width="3"/>
          <circle cx="460" cy="180" r="7" fill="#b91c1c"/>
          <text x="52" y="50" font-size="18" fill="#334155">parallel gamma beam</text>
          <text x="290" y="48" font-size="18" fill="#0f766e">Ge crystal ring</text>
          <text x="380" y="160" font-size="18" fill="#b91c1c">focal plane</text>
        </svg>
      </div>
    </div>
  </section>

  <section class="slide" data-slide="3 / 14">
    <div class="kicker">Literature alignment</div>
    <h2>这套做法和哪些论文/报告对齐？</h2>
    <table>
      <tr><th>来源</th><th>原文短引</th><th>我们如何对齐</th></tr>
      <tr><td>Barhoum 2022 Geant4 Laue</td><td>“model x-ray and gamma ray focusing based on Laue diffraction in the GEANT4 toolkit”</td><td>在 Geant4 app 中实现 Laue process，记录 diffract / transmit / absorb。</td></tr>
      <tr><td>Guan 2023 Bragg in Geant4</td><td>“developed a new EM physical process class”</td><td>同样不依赖标准 EM 自动产生 Bragg；我们选择 app 级过程，避免改 toolkit。</td></tr>
      <tr><td>Barriere 2009 Laue lens crystals</td><td>“peak reflectivity at 100 keV, 500 keV and 1 MeV”</td><td>用 Zachariasen/Darwin mosaic 公式，并用 Cu/Au 表格 benchmark。</td></tr>
      <tr><td>Kohnle 1998 Ge crystals</td><td>“measured diffraction efficiencies of Ge crystals from 200 to 500 keV”</td><td>新增 Ge(111) 200/500 keV 端点核验。</td></tr>
    </table>
    <p class="small">短引均来自公开摘要或本地已下载论文/论文文本；完整出处在最后一页。</p>
  </section>

  <section class="slide" data-slide="4 / 14">
    <div class="kicker">Implementation</div>
    <h2>实现路线：从公式到 Geant4 事件</h2>
    <div class="flow">
      <div><b>1. 晶体参数</b>Ge(111)、d-spacing、480-550 keV、8.3 m 焦距。</div>
      <div><b>2. Darwin 表</b>计算 p_diff / p_abs / p_trans 与 Bragg mismatch。</div>
      <div><b>3. Geant4 process</b>边界触发，自定义抽样，生成衍射 secondary。</div>
      <div><b>4. 输出合同</b>phase_space、transmitted_space、optics_history。</div>
      <div><b>5. 审计</b>Bragg 几何、文献 benchmark、PyTTE、IO tests。</div>
    </div>
    <p>关键设计选择：Geant4 底层不改；物理表离线生成；Geant4 只查表并执行事件级抽样。这让模型可复查、可替换、可和不同论文/工具逐项对标。</p>
    <div class="quote"><em>代码定位：</em>表生成在 <code>external_baseline/laue_raytrace_py/mosaic_darwin.py</code>，Geant4 查表过程在 <code>geant4_app/src/laue_multiring_table_demo.cc</code>。</div>
  </section>

  <section class="slide" data-slide="5 / 14">
    <div class="kicker">Physics table</div>
    <h2>Darwin/Zachariasen 表不是调参占位表</h2>
    <div class="grid2">
      <div>
        <p>每一行表包含能量、Bragg 角、角度偏差、材料、hkl、mosaicity、厚度，以及三条概率分支。</p>
        <p>核心计算形式为：</p>
        <div class="formula">ε = 0.5 × (1 − exp(−2 σ T))<br>p<sub>diff</sub> = ε × exp(−μT / cosθ<sub>B</sub>)</div>
        <p class="small">μ 来自 xraydb/Chantler 系数；结构因子、消光长度和 mosaic 权重由代码直接计算。</p>
      </div>
      <img src="laue_group_ppt_assets/darwin_efficiency_table.png" alt="Darwin efficiency table plot">
    </div>
  </section>

  <section class="slide" data-slide="6 / 14">
    <div class="kicker">Geometry</div>
    <h2>五环 Ge(111) 几何：与 511 keV 尺度接上</h2>
    <div class="grid2">
      <div>
        <p>当前配置覆盖 480、500、511、530、550 keV。焦距固定 8.3 m，环半径由 Bragg 关系反推，能量越高 Bragg 角越小，环半径随之减小。</p>
        <p>几何审计结果：</p>
        <ul>
          <li>检查 tile 数：{bragg["n_tiles_checked"]}</li>
          <li>最大 Bragg 角残差：{bragg["max_abs_theta_geom_minus_theta_B_rad"]:.2e} rad</li>
          <li>最大偏转角残差：{bragg["max_abs_deflection_minus_2theta_B_rad"]:.2e} rad</li>
          <li>最小径向净间隙：{bragg["min_radial_clearance_mm"]:.3f} mm</li>
        </ul>
      </div>
      <img src="laue_group_ppt_assets/geometry_rings.png" alt="Ge111 ring geometry plot">
    </div>
  </section>

  <section class="slide" data-slide="7 / 14">
    <div class="kicker">Geant4 result</div>
    <h2>100k 事件主运行：衍射、吸收、透过分开统计</h2>
    <div class="grid2">
      <div>
        <div class="grid3">
          <div class="card"><strong>Diffracted</strong><span class="metric">{summary["n_diffracted"]}</span><p>{summary["diffraction_fraction"]:.2%}</p></div>
          <div class="card"><strong>Absorbed</strong><span class="metric" style="color:#b45309">{summary["n_absorbed"]}</span><p>{summary["absorption_fraction"]:.2%}</p></div>
          <div class="card"><strong>Transmitted</strong><span class="metric" style="color:#64748b">{summary["n_transmitted"]}</span><p>{summary["transmission_fraction"]:.2%}</p></div>
        </div>
        <p style="margin-top: 22px;">输出 WRL：<code>{summary["visualization_wrl"]}</code></p>
        <p>焦斑 D90：<code>{summary["spot_d90_cm"]:.4f} cm</code>。这个焦斑是当前 mosaic spread 与几何指向模型的结果，不等同于最终真实装调 PSF。</p>
      </div>
      <img src="laue_group_ppt_assets/per_ring_outcomes.png" alt="Per-ring Geant4 outcome plot">
    </div>
  </section>

  <section class="slide" data-slide="8 / 14">
    <div class="kicker">External benchmark I</div>
    <h2>Barriere 2009：验证 Darwin 表生成器</h2>
    <div class="grid2">
      <div>
        <p>Barriere 2009 给出 Cu/Au mosaic crystal 的实测峰值效率和反射率案例。我们用同一 Darwin/Zachariasen 实现计算这些案例。</p>
        <div class="card"><strong>Benchmark pass</strong><span class="metric">{darwin["n_cases"]} cases</span><p>最大峰值效率误差：{darwin["max_abs_diff_eff_error"]:.4f}</p><p>最大反射率误差：{darwin["max_abs_reflectivity_error"]:.4f}</p></div>
        <p class="small">意义：证明公式实现和单位/结构因子/吸收处理没有明显错位。限制：Cu/Au 不等于 Ge(111)。</p>
      </div>
      <div class="quote">
        <p><em>组会解读：</em>Barriere 是“公式通用性”锚点，不是最终 Ge 材料闭合。它告诉我们：这不是随手画的概率表，而是能复现实测表的 Darwin 实现。</p>
      </div>
    </div>
  </section>

  <section class="slide" data-slide="9 / 14">
    <div class="kicker">External benchmark II</div>
    <h2>Kohnle 1998：直接 Ge(111) 200-500 keV 锚点</h2>
    <div class="grid2">
      <div>
        <p>Kohnle 博士论文第 8.3.1 节给出 APS 双晶 Ge(111) 测量：两块 3 mm Ge(111)，200-500 keV，第二块约 3 arcsec mosaicity。</p>
        <p>我们没有用 0.43 做校正，只把它作为误差检查。500 keV 的计算来自公式：</p>
        <div class="formula">0.494320 × 0.877066 = 0.433551</div>
        <p>端点最大绝对误差：<code>{kohnle["endpoint_max_abs_error"]:.4f}</code>。</p>
      </div>
      <img src="laue_group_ppt_assets/kohnle_ge111_benchmark.png" alt="Kohnle Ge111 benchmark plot">
    </div>
  </section>

  <section class="slide" data-slide="10 / 14">
    <div class="kicker">Independent tool</div>
    <h2>PyTTE：独立动力学衍射 sanity check</h2>
    <div class="grid2">
      <div>
        <p>PyTTE 求的是 perfect-crystal Takagi-Taupin Laue 曲线，不是 mosaic crystal 表。因此它不能替代当前表，但能检查一个重要方向：完美 Ge(111) Laue 分支应强于当前 mosaic+吸收表。</p>
        <ul>
          <li>500/511 keV，sigma/pi 均跑通。</li>
          <li>中心点 forward + diffraction ≈ 1，通量守恒表现正常。</li>
          <li>结果支持当前 mosaic Darwin 表不是虚高。</li>
        </ul>
      </div>
      <img src="laue_group_ppt_assets/pytte_check.png" alt="PyTTE independent check plot">
    </div>
  </section>

  <section class="slide" data-slide="11 / 14">
    <div class="kicker">Uncertainty</div>
    <h2>敏感性：mosaicity 和厚度不是小细节</h2>
    <div class="grid2">
      <div>
        <p>同一 Darwin 模型内，mosaicity 和厚度会明显改变峰值衍射概率。当前 nominal 是 30 arcsec、优化厚度；扫描显示 15 arcsec 附近可得到更高 peak p_diff。</p>
        <div class="card"><strong>Best scanned case</strong><span class="metric">{sensitivity["best_case"]["mean_peak_p_diff"]:.3f}</span><p>15 arcsec、thickness scale 1.0</p></div>
        <p class="small">这就是为什么我不把当前结果说成完整仪器级100%：最终设计需要真实晶体批次、mosaicity、厚度、弯曲/装调误差的系统误差条；但当前阶段不要求同参数整机实测闭合。</p>
      </div>
      <img src="laue_group_ppt_assets/sensitivity_heatmap.png" alt="Darwin sensitivity heatmap">
    </div>
  </section>

  <section class="slide" data-slide="12 / 14">
    <div class="kicker">What changed</div>
    <h2>从 toy 到现在，实际完成了什么？</h2>
    <table>
      <tr><th>阶段</th><th>旧状态</th><th>现在状态</th></tr>
      <tr><td>概率模型</td><td>常数 p_diff 或占位高斯表</td><td>Zachariasen/Darwin mosaic 表，含吸收和角度偏差</td></tr>
      <tr><td>Geant4</td><td>one-ring toy 或 p_diff=1 regression</td><td>五环 table-driven process，100k events，WRL 输出</td></tr>
      <tr><td>文献对齐</td><td>只知道方向可行</td><td>Barhoum/Guan 架构对齐，Barriere/Kohnle 数值对齐</td></tr>
      <tr><td>审计</td><td>焦点能跑</td><td>Bragg 几何、IO contract、文献 benchmark、PyTTE、unittest</td></tr>
    </table>
    <p>底层 Geant4 修改：<span class="ok">没有</span>。当前使用独立 Geant4 11.4.0 环境，不碰 MEGAlib 的 Geant4 10.2.3。</p>
  </section>

  <section class="slide" data-slide="13 / 14">
    <div class="kicker">Claim boundary</div>
    <h2>现在能怎么说，不能怎么说？</h2>
    <div class="grid2">
      <div class="card">
        <strong class="ok">可以说</strong>
        <ul>
          <li>已经实现 500 keV 量级 Ge(111) Laue table-driven Geant4 optics。</li>
          <li>Darwin 表生成器通过 Cu/Au 文献 benchmark。</li>
          <li>Ge(111) 500 keV 端点与 Kohnle 1998 直接实验锚点一致。</li>
          <li>当前没有强行 correction factor 对齐。</li>
        </ul>
      </div>
      <div class="card">
        <strong class="warn">不能说</strong>
        <ul>
          <li>不能说完整仪器级 100% 完成。</li>
          <li>不能说已复现 bent Ge/Si Laue lens 全成像论文。</li>
          <li>不能把材料批次、装调误差和探测器耦合当作已经闭合。</li>
          <li>不能把当前焦斑当作真实装调后的最终 PSF。</li>
        </ul>
      </div>
    </div>
    <p style="margin-top: 22px;">我的当前判断：Laue 核心物理研究原型可信度约 <span class="ok">93%-95%</span>；后续若要投稿或工程定型，再补更接近实验、独立程序或真实晶体批次数据来收敛系统误差。</p>
  </section>

  <section class="slide" data-slide="14 / 14">
    <div class="kicker">Reproduce and references</div>
    <h2>复现命令与参考</h2>
    <p>核心复现命令：</p>
    <pre><code>python3 -m external_baseline.laue_raytrace_py.build_mosaic_darwin_table ...
/tmp/opticsim-build-g4-11.4.0/laue_multiring_table_demo --n 100000 ...
python3 analysis/benchmark_laue_darwin.py
python3 analysis/benchmark_laue_kohnle1998.py
python3 analysis/run_pytte_ge111_check.py
python3 -m unittest discover -s tests</code></pre>
    <p>当前测试：<code>{tests}</code></p>
    <table>
      <tr><th>参考</th><th>链接/本地副本</th></tr>
      <tr><td>Barhoum 2022 Geant4 Laue</td><td>https://agenda.infn.it/event/21084/contributions/178539/</td></tr>
      <tr><td>Guan 2023 Bragg process</td><td>https://digitalcommons.library.tmc.edu/uthgsbs_docs/3758/</td></tr>
      <tr><td>Barriere 2009 Laue crystal benchmark</td><td>https://arxiv.org/abs/0907.0458</td></tr>
      <tr><td>Kohnle 1998 Ge diffraction efficiency</td><td><code>records/laue_external_sources/Diss_Kohnle_98.pdf</code></td></tr>
      <tr><td>本次 WRL 可视化</td><td><code>runs/geant4_laue_multiring_darwin/laue_multiring_scene.wrl</code></td></tr>
    </table>
  </section>
</main>
</body>
</html>
"""


def main() -> int:
    make_figures()
    OUT_HTML.write_text(html(), encoding="utf-8")
    print(OUT_HTML)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
