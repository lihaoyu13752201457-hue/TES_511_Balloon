#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


VIEWPORT_BASE_CSS = """
/* ===========================================
   VIEWPORT FITTING: MANDATORY BASE STYLES
   Include this ENTIRE file in every presentation.
   These styles ensure slides fit exactly in the viewport.
   =========================================== */

html, body {
    height: 100%;
    overflow-x: hidden;
}

html {
    scroll-snap-type: y mandatory;
    scroll-behavior: smooth;
}

.slide {
    width: 100vw;
    height: 100vh;
    height: 100dvh;
    overflow: hidden;
    scroll-snap-align: start;
    display: flex;
    flex-direction: column;
    position: relative;
}

.slide-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    max-height: 100%;
    overflow: hidden;
    padding: var(--slide-padding);
}

:root {
    --title-size: clamp(1.5rem, 5vw, 4rem);
    --h2-size: clamp(1.25rem, 3.5vw, 2.5rem);
    --h3-size: clamp(1rem, 2.5vw, 1.75rem);
    --body-size: clamp(0.75rem, 1.5vw, 1.125rem);
    --small-size: clamp(0.65rem, 1vw, 0.875rem);
    --slide-padding: clamp(1rem, 4vw, 4rem);
    --content-gap: clamp(0.5rem, 2vw, 2rem);
    --element-gap: clamp(0.25rem, 1vw, 1rem);
}

.card, .container, .content-box {
    max-width: min(90vw, 1000px);
    max-height: min(80vh, 700px);
}

.feature-list, .bullet-list {
    gap: clamp(0.4rem, 1vh, 1rem);
}

.feature-list li, .bullet-list li {
    font-size: var(--body-size);
    line-height: 1.4;
}

.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 250px), 1fr));
    gap: clamp(0.5rem, 1.5vw, 1rem);
}

img, .image-container {
    max-width: 100%;
    max-height: min(50vh, 400px);
    object-fit: contain;
}

@media (max-height: 700px) {
    :root {
        --slide-padding: clamp(0.75rem, 3vw, 2rem);
        --content-gap: clamp(0.4rem, 1.5vw, 1rem);
        --title-size: clamp(1.25rem, 4.5vw, 2.5rem);
        --h2-size: clamp(1rem, 3vw, 1.75rem);
    }
}

@media (max-height: 600px) {
    :root {
        --slide-padding: clamp(0.5rem, 2.5vw, 1.5rem);
        --content-gap: clamp(0.3rem, 1vw, 0.75rem);
        --title-size: clamp(1.1rem, 4vw, 2rem);
        --body-size: clamp(0.7rem, 1.2vw, 0.95rem);
    }

    .nav-dots, .keyboard-hint, .decorative {
        display: none;
    }
}

@media (max-height: 500px) {
    :root {
        --slide-padding: clamp(0.4rem, 2vw, 1rem);
        --title-size: clamp(1rem, 3.5vw, 1.5rem);
        --h2-size: clamp(0.9rem, 2.5vw, 1.25rem);
        --body-size: clamp(0.65rem, 1vw, 0.85rem);
    }
}

@media (max-width: 600px) {
    :root {
        --title-size: clamp(1.25rem, 7vw, 2.5rem);
    }

    .grid {
        grid-template-columns: 1fr;
    }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation-duration: 0.01ms !important;
        transition-duration: 0.2s !important;
    }

    html {
        scroll-behavior: auto;
    }
}
"""


CUSTOM_CSS = """
:root {
    --bg: #0f1110;
    --panel: #171b18;
    --panel-soft: #20251f;
    --ink: #f5f0df;
    --muted: #c3bfae;
    --quiet: #8d9387;
    --line: #3d443b;
    --teal: #49c7b1;
    --amber: #f2b45c;
    --lime: #a6d56d;
    --red: #e37163;
    --steel: #8bb3c1;
    --violet: #c1a3ff;
    --slide-padding: clamp(1rem, 3vw, 3rem);
}

* { box-sizing: border-box; }

body {
    margin: 0;
    background:
      radial-gradient(circle at 14% 16%, rgba(73,199,177,.14), transparent 28%),
      radial-gradient(circle at 86% 78%, rgba(242,180,92,.12), transparent 30%),
      linear-gradient(135deg, #0f1110 0%, #171b18 54%, #0a0c0c 100%);
    color: var(--ink);
    font-family: "Aptos", "Noto Sans CJK SC", "Microsoft YaHei", "Segoe UI", sans-serif;
}

a { color: var(--teal); text-decoration: none; }
code { color: var(--lime); font-family: "Cascadia Code", "SFMono-Regular", Consolas, monospace; }
.deck { width: 100vw; min-height: 100vh; }
.slide { display: none; }
.slide.active { display: flex; }
.slide::before {
    content: "";
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.024) 1px, transparent 1px);
    background-size: 44px 44px;
    mask-image: linear-gradient(to bottom, rgba(0,0,0,.9), rgba(0,0,0,.28));
    pointer-events: none;
}
.slide-content { position: relative; z-index: 1; gap: clamp(.72rem, 1.7vh, 1.5rem); }
.eyebrow {
    color: var(--amber);
    font-size: clamp(.66rem, .95vw, .9rem);
    letter-spacing: .13em;
    text-transform: uppercase;
    font-weight: 800;
}
h1, h2, h3, p { margin: 0; }
h1 {
    font-family: Georgia, "Noto Serif CJK SC", serif;
    font-size: clamp(2.15rem, 6.5vw, 5.7rem);
    line-height: .96;
    letter-spacing: 0;
    max-width: 13.5ch;
}
h2 {
    font-family: Georgia, "Noto Serif CJK SC", serif;
    font-size: clamp(1.62rem, 3.8vw, 3.45rem);
    line-height: 1.04;
    letter-spacing: 0;
}
h3 {
    color: var(--amber);
    font-size: clamp(.95rem, 1.45vw, 1.24rem);
    letter-spacing: 0;
}
.subtitle {
    font-size: clamp(.96rem, 1.75vw, 1.42rem);
    line-height: 1.4;
    color: var(--muted);
    max-width: 74ch;
}
.small {
    color: var(--muted);
    font-size: clamp(.68rem, 1.05vw, .9rem);
    line-height: 1.38;
}
.micro {
    color: var(--quiet);
    font-size: clamp(.6rem, .86vw, .76rem);
    line-height: 1.34;
}
.split {
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(0, .95fr);
    gap: clamp(.9rem, 1.8vw, 1.7rem);
    align-items: stretch;
}
.split.wide-left { grid-template-columns: minmax(0, 1.22fr) minmax(0, .78fr); }
.cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: clamp(.62rem, 1.15vw, .95rem);
}
.cards.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.cards.four { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.card, .metric, .claim, .source, .codecard, .diagram {
    border: 1px solid var(--line);
    background: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.023));
    border-radius: 8px;
    padding: clamp(.68rem, 1.25vw, 1.05rem);
    box-shadow: 0 13px 34px rgba(0,0,0,.23);
}
.card p, .claim p, .source p {
    color: var(--muted);
    font-size: clamp(.72rem, 1.06vw, .9rem);
    line-height: 1.36;
    margin-top: .35rem;
}
.metric b {
    display: block;
    font-size: clamp(1.2rem, 3vw, 2.42rem);
    color: var(--lime);
    font-family: Georgia, serif;
    line-height: 1;
}
.metric span {
    display: block;
    color: var(--muted);
    font-size: clamp(.66rem, .95vw, .84rem);
    margin-top: .35rem;
    line-height: 1.3;
}
.claim { border-left: 5px solid var(--teal); }
.claim.warn { border-left-color: var(--amber); }
.claim.no { border-left-color: var(--red); }
.ribbon {
    display: inline-flex;
    gap: .45rem;
    align-items: center;
    width: fit-content;
    border: 1px solid rgba(73,199,177,.42);
    background: rgba(73,199,177,.11);
    color: var(--teal);
    border-radius: 999px;
    padding: .32rem .72rem;
    font-size: clamp(.62rem, .95vw, .82rem);
    font-weight: 800;
}
.flow {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: clamp(.45rem, 1vw, .75rem);
}
.step {
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: clamp(.58rem, 1vw, .82rem);
    background: rgba(255,255,255,.04);
    min-height: clamp(5.6rem, 13vh, 7.2rem);
}
.step b {
    display: block;
    color: var(--amber);
    font-size: clamp(.76rem, 1vw, .94rem);
    margin-bottom: .3rem;
}
.step span {
    color: var(--muted);
    font-size: clamp(.66rem, .93vw, .8rem);
    line-height: 1.3;
}
.branch {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: clamp(.55rem, 1vw, .85rem);
}
.branch .card { min-height: clamp(7rem, 19vh, 9.4rem); }
.table {
    width: 100%;
    border-collapse: collapse;
    font-size: clamp(.66rem, .95vw, .82rem);
}
.table th, .table td {
    border: 1px solid var(--line);
    padding: clamp(.34rem, .72vw, .54rem);
    vertical-align: top;
    text-align: left;
}
.table th {
    color: var(--amber);
    background: rgba(242,180,92,.08);
}
.formula {
    font-family: Georgia, "Noto Serif CJK SC", serif;
    font-size: clamp(1rem, 2.15vw, 1.86rem);
    line-height: 1.22;
    text-align: center;
    padding: clamp(.7rem, 1.5vw, 1rem);
    border-radius: 8px;
    border: 1px solid rgba(166,213,109,.32);
    background: rgba(166,213,109,.08);
}
.codecard pre {
    margin: 0;
    white-space: pre-wrap;
    font-size: clamp(.62rem, .9vw, .78rem);
    line-height: 1.35;
    color: #dfe8d7;
}
.legend {
    display: flex;
    flex-wrap: wrap;
    gap: .55rem;
    color: var(--muted);
    font-size: clamp(.62rem, .9vw, .78rem);
}
.dot {
    width: .8em;
    height: .8em;
    border-radius: 50%;
    display: inline-block;
    margin-right: .28rem;
}
.progress {
    position: fixed;
    z-index: 9;
    left: 0;
    top: 0;
    height: 4px;
    width: 0;
    background: linear-gradient(90deg, var(--teal), var(--amber));
}
.controls {
    position: fixed;
    z-index: 10;
    right: clamp(.6rem, 1.2vw, 1rem);
    bottom: clamp(.6rem, 1.2vw, 1rem);
    display: flex;
    gap: .35rem;
    align-items: center;
}
.controls button {
    border: 1px solid var(--line);
    color: var(--ink);
    background: rgba(15,17,16,.86);
    border-radius: 8px;
    padding: .42rem .58rem;
    cursor: pointer;
    font: inherit;
}
svg { max-width: 100%; height: auto; }
.diagram svg { max-height: min(50vh, 390px); display: block; margin: 0 auto; }
ul {
    margin: 0;
    padding-left: 1.1rem;
    color: var(--muted);
    font-size: clamp(.72rem, 1.08vw, .94rem);
    line-height: 1.42;
}
li + li { margin-top: .22rem; }

@media (max-width: 820px) {
    .split, .split.wide-left, .cards, .cards.two, .cards.four, .branch, .flow {
        grid-template-columns: 1fr;
    }
    .flow { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-height: 650px) {
    .micro { display: none; }
    .card, .metric, .claim, .source, .codecard, .diagram { padding: clamp(.48rem, .9vw, .74rem); }
    .step { min-height: auto; }
}
"""


@dataclass(frozen=True)
class Slide:
    title: str
    body: str
    note: str


def read_json(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_rings() -> list[dict[str, str]]:
    with (ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def near_bragg_511() -> dict[str, str]:
    with (ROOT / "data/laue/Ge111_480_550keV_darwin_mosaic_table.csv").open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if float(row["E_keV"]) == 511.0]
    return min(rows, key=lambda row: abs(float(row["delta_theta_rad"])))


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def lens_svg(rings: list[dict[str, str]]) -> str:
    labels = "".join(
        f'<text x="150" y="{74 + i * 28}" fill="#c3bfae" font-size="12">'
        f'{esc(row["design_energy_keV"])} keV  r={float(row["radius_mm"]):.2f} mm</text>'
        for i, row in enumerate(rings)
    )
    circles = "".join(
        f'<circle cx="175" cy="175" r="{float(row["radius_mm"]) * 1.9:.1f}" '
        f'fill="none" stroke="{color}" stroke-width="3" opacity=".9"/>'
        for row, color in zip(rings, ["#49c7b1", "#f2b45c", "#a6d56d", "#8bb3c1", "#e37163"])
    )
    return f"""
    <svg viewBox="0 0 520 350" role="img" aria-label="Five Ge111 Laue lens rings">
      <rect width="520" height="350" fill="#111512" rx="10"/>
      <g transform="translate(0,0)">
        {circles}
        <circle cx="175" cy="175" r="5" fill="#f5f0df"/>
        <line x1="175" y1="175" x2="440" y2="175" stroke="#3d443b" stroke-width="2"/>
        <circle cx="440" cy="175" r="8" fill="#f2b45c"/>
        <text x="374" y="156" fill="#f2b45c" font-size="15">focus</text>
        <text x="34" y="30" fill="#49c7b1" font-size="16" font-weight="700">Ge(111) multiring layout</text>
        {labels}
      </g>
    </svg>
    """


def process_svg() -> str:
    return """
    <svg viewBox="0 0 720 360" role="img" aria-label="Barhoum style Geant4 Laue process flow">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#c3bfae"/>
        </marker>
      </defs>
      <rect width="720" height="360" rx="10" fill="#111512"/>
      <g fill="none" stroke="#c3bfae" stroke-width="3" marker-end="url(#arrow)">
        <path d="M60 180 H180"/>
        <path d="M330 180 H445"/>
        <path d="M515 145 C570 90 630 80 680 80"/>
        <path d="M515 180 H680"/>
        <path d="M515 215 C570 270 630 280 680 280"/>
      </g>
      <rect x="185" y="130" width="145" height="100" rx="8" fill="#1b211d" stroke="#49c7b1"/>
      <text x="206" y="170" fill="#f5f0df" font-size="17" font-weight="700">Geant4 step</text>
      <text x="205" y="198" fill="#c3bfae" font-size="13">fGeomBoundary</text>
      <rect x="445" y="105" width="92" height="150" rx="8" fill="#20251f" stroke="#f2b45c"/>
      <text x="465" y="154" fill="#f5f0df" font-size="16" font-weight="700">Laue</text>
      <text x="461" y="180" fill="#c3bfae" font-size="13">process</text>
      <text x="43" y="170" fill="#8bb3c1" font-size="15">gamma</text>
      <text x="608" y="68" fill="#49c7b1" font-size="15">diffract</text>
      <text x="610" y="170" fill="#f2b45c" font-size="15">absorb</text>
      <text x="604" y="304" fill="#8bb3c1" font-size="15">transmit</text>
      <text x="86" y="322" fill="#8d9387" font-size="13">Mean free path is effectively not the physics; PostStepDoIt performs the branch decision.</text>
    </svg>
    """


def branch_svg(diff: float, absorb: float, trans: float) -> str:
    total = diff + absorb + trans
    diff_w = 520 * diff / total
    absorb_w = 520 * absorb / total
    trans_w = 520 * trans / total
    return f"""
    <svg viewBox="0 0 620 180" role="img" aria-label="Laue branching fractions">
      <rect width="620" height="180" rx="10" fill="#111512"/>
      <text x="32" y="38" fill="#f5f0df" font-size="18" font-weight="700">100k event branch statistics</text>
      <rect x="50" y="76" width="{diff_w:.2f}" height="40" fill="#49c7b1"/>
      <rect x="{50 + diff_w:.2f}" y="76" width="{absorb_w:.2f}" height="40" fill="#f2b45c"/>
      <rect x="{50 + diff_w + absorb_w:.2f}" y="76" width="{trans_w:.2f}" height="40" fill="#8bb3c1"/>
      <rect x="50" y="76" width="520" height="40" fill="none" stroke="#3d443b"/>
      <text x="50" y="145" fill="#49c7b1" font-size="14">diffract {pct(diff)}</text>
      <text x="250" y="145" fill="#f2b45c" font-size="14">absorb {pct(absorb)}</text>
      <text x="442" y="145" fill="#8bb3c1" font-size="14">transmit {pct(trans)}</text>
    </svg>
    """


def build_slides() -> list[Slide]:
    run = read_json("runs/geant4_laue_multiring_darwin/summary.json")
    audit = read_json("runs/laue_physics_confidence_audit/summary.json")
    rings = read_rings()
    table_511 = near_bragg_511()
    bragg = audit["bragg_audit"]
    barriere = audit["barriere"]
    kohnle = audit["kohnle"]
    pytte = audit["pytte"]

    slides = [
        Slide(
            "Barhoum Laue Lens Work and Our Implementation",
            f"""
            <div class="slide-content">
              <div class="eyebrow">Geant4 Laue optics · source-backed walkthrough</div>
              <h1>Barhoum 的工作<br>和我们的做法</h1>
              <p class="subtitle">这份 HTML 明确区分两件事：Barhoum 2022 给我们的是 Geant4 Laue process 的实现架构参考；我们的数值光学概率来自 Zachariasen/Darwin mosaic-crystal 表和本地 benchmark。</p>
              <div class="cards">
                <div class="metric"><b>2022</b><span>Barhoum 等在 Geant4 用户会上报告 Laue lens advanced example。</span></div>
                <div class="metric"><b>{run["n_primaries"]:,}</b><span>本仓库 multiring Darwin 主运行事件数。</span></div>
                <div class="metric"><b>{pct(run["diffraction_fraction"])}</b><span>当前 Ge(111) 480-550 keV 表驱动衍射分支。</span></div>
              </div>
            </div>
            """,
            "开场：把文献架构、我们的物理表、Geant4 事件实现分开讲。",
        ),
        Slide(
            "为什么 Barhoum 重要",
            """
            <div class="slide-content">
              <div class="eyebrow">Problem statement</div>
              <h2>Laue 聚焦不是 Geant4 标准 EM 自动给出的结果</h2>
              <div class="split">
                <div class="claim">
                  <h3>Barhoum 2022 解决的软件缺口</h3>
                  <p>报告摘要把动机说得很清楚：Laue 透镜实验制造与对准困难，因此需要在 Geant4 这样的高能粒子 Monte Carlo 环境里做可重复模拟；但 Laue diffraction process 当时不是通用平台里的现成过程。</p>
                </div>
                <div class="diagram">
                  <svg viewBox="0 0 520 300" role="img" aria-label="Laue physics gap diagram">
                    <rect width="520" height="300" rx="10" fill="#111512"/>
                    <rect x="36" y="62" width="150" height="86" rx="8" fill="#1b211d" stroke="#8bb3c1"/>
                    <text x="60" y="95" fill="#f5f0df" font-size="17" font-weight="700">standard EM</text>
                    <text x="56" y="123" fill="#c3bfae" font-size="12">Compton / photoelectric</text>
                    <rect x="334" y="62" width="150" height="86" rx="8" fill="#1b211d" stroke="#49c7b1"/>
                    <text x="361" y="95" fill="#f5f0df" font-size="17" font-weight="700">Laue optics</text>
                    <text x="356" y="123" fill="#c3bfae" font-size="12">Bragg diffraction focus</text>
                    <path d="M196 105 H323" stroke="#e37163" stroke-width="5" stroke-dasharray="12 9"/>
                    <text x="227" y="93" fill="#e37163" font-size="13">missing process</text>
                    <text x="54" y="225" fill="#8d9387" font-size="13">Barhoum 的贡献点：把 Laue lens focusing 放进 Geant4 tracking workflow。</text>
                  </svg>
                </div>
              </div>
              <p class="micro">公开证据：Indico contribution, Oct 24 2022；conference abstract PDF；Talk_04_Barhoum.pdf。</p>
            </div>
            """,
            "强调 Barhoum 的贡献是 Geant4 中缺 Laue diffraction/focusing 过程这个软件缺口。",
        ),
        Slide(
            "Barhoum 2022 的工作画像",
            """
            <div class="slide-content">
              <div class="eyebrow">What they built</div>
              <h2>一个早期的 Geant4 Laue lens advanced example</h2>
              <div class="cards">
                <div class="card"><h3>目标</h3><p>在 Geant4 toolkit 里模拟 X-ray / gamma ray 经 Laue diffraction 聚焦到探测器平面的过程。</p></div>
                <div class="card"><h3>事件分支</h3><p>光子与 lens volume 相交后，算法决定三类结果：diffracted、transmitted、absorbed。</p></div>
                <div class="card"><h3>验证意图</h3><p>报告中提到用真实 Laue lens medical-imaging 数据、Mathematica 工具和 MATLAB tracking code 做早期验证。</p></div>
              </div>
              <div class="source">
                <h3>出处</h3>
                <p>Barhoum, Camattari, Guatelli, Tahtali, “GEANT4-Gamma Diffraction Code Based on Laue lens Modelling...”, IV Geant4 International User Conference, Napoli, 24 Oct 2022.</p>
              </div>
            </div>
            """,
            "用一句话定位 Barhoum：早期 advanced example，不是一个我们直接复制数值表的公开库。",
        ),
        Slide(
            "Barhoum 的 Geant4 架构要点",
            f"""
            <div class="slide-content">
              <div class="eyebrow">Architecture pattern</div>
              <h2>核心不是 mean free path，而是 PostStepDoIt 的分支逻辑</h2>
              <div class="split">
                <div>
                  <div class="codecard"><pre><code>GetMeanFreePath(..., condition) {{
  *condition = StronglyForced;
  return DBL_MAX;
}}

PostStepDoIt(track, step) {{
  if photon intersects Laue lens:
    sample absorb / transmit / diffract
}}</code></pre></div>
                  <p class="small">Talk_04_Barhoum.pdf 说明他们把 mean free path 设成很大值，真正的交互判断放在 <code>PostStepDoIt</code>。这就是我们参考的“过程架构”。</p>
                </div>
                <div class="diagram">{process_svg()}</div>
              </div>
            </div>
            """,
            "这是和我们代码最直接对齐的一页：G4VDiscreteProcess、StronglyForced、DBL_MAX、PostStepDoIt。",
        ),
        Slide(
            "Barhoum 模型的工程简化",
            """
            <div class="slide-content">
              <div class="eyebrow">Limits we should not hide</div>
              <h2>Barhoum advanced example 是架构原型，不是完整晶体仪器闭合</h2>
              <div class="cards">
                <div class="claim warn"><h3>几何简化</h3><p>报告中说明为降低复杂度，把多环 lens 行为简化成 tube 的内外半径，没有把环间空白和支撑结构完整展开。</p></div>
                <div class="claim warn"><h3>早期阶段</h3><p>conference abstract 和 talk 都把这项工作称为 early conception / early version；所以不能把它当成最终数值 benchmark。</p></div>
                <div class="claim warn"><h3>我们的引用边界</h3><p>它支持“在 Geant4 中扩充 Laue process 这条路合理”，不等于给出了我们 Ge(111) 511 keV 概率表。</p></div>
              </div>
            </div>
            """,
            "这页是防误读：Barhoum 不应该被写成我们概率模型的来源。",
        ),
        Slide(
            "我们的总路线",
            """
            <div class="slide-content">
              <div class="eyebrow">Our decision</div>
              <h2>我们继承 Barhoum 的软件架构，但把数值物理单独闭合</h2>
              <div class="flow">
                <div class="step"><b>1. 文献架构</b><span>自定义 Geant4 discrete process，边界强制触发。</span></div>
                <div class="step"><b>2. Bragg 几何</b><span>由 d-spacing、能量和焦距反推环半径。</span></div>
                <div class="step"><b>3. Darwin 表</b><span>离线生成 p_diff / p_abs / p_trans。</span></div>
                <div class="step"><b>4. Geant4 抽样</b><span>按表查概率，生成 secondary 或 kill track。</span></div>
                <div class="step"><b>5. 审计</b><span>几何、benchmark、PyTTE、IO 合同测试。</span></div>
              </div>
              <p class="subtitle">这样做的好处是：Geant4 负责 event loop、geometry boundary、secondary 管理；Laue diffraction 的概率来源可以被独立复查和替换。</p>
            </div>
            """,
            "概览我们的做法：Barhoum 架构 + 自己的 Darwin table。",
        ),
        Slide(
            "我们的 Laue 物理表",
            f"""
            <div class="slide-content">
              <div class="eyebrow">Physics source</div>
              <h2>概率不是校正因子：来自 Zachariasen/Darwin mosaic-crystal 计算</h2>
              <div class="split wide-left">
                <div>
                  <div class="formula">p<sub>diff</sub> = 0.5(1 - exp(-2σT)) · exp(-μT/cosθ<sub>B</sub>)</div>
                  <div class="cards">
                    <div class="metric"><b>{float(table_511["theta_B_rad"]):.6f}</b><span>511 keV Ge(111) Bragg angle, rad</span></div>
                    <div class="metric"><b>{float(table_511["p_diff"]):.3f}</b><span>表内 511 keV near-Bragg p_diff</span></div>
                    <div class="metric"><b>{float(table_511["p_abs"]):.3f}</b><span>表内 511 keV absorption branch</span></div>
                  </div>
                </div>
                <div class="card">
                  <h3>表字段</h3>
                  <p><code>E_keV</code>, <code>theta_B_rad</code>, <code>delta_theta_rad</code>, material, hkl, mosaic FWHM, thickness, <code>p_diff</code>, <code>p_abs</code>, <code>p_trans</code>。</p>
                  <p>默认表：<code>data/laue/Ge111_480_550keV_darwin_mosaic_table.csv</code>，共 {run["efficiency_table_rows"]} 行。</p>
                </div>
              </div>
            </div>
            """,
            "物理概率来自本地 Darwin/Zachariasen 实现，不是 Barhoum 的参数。",
        ),
        Slide(
            "我们的 Geant4 过程",
            f"""
            <div class="slide-content">
              <div class="eyebrow">Code map</div>
              <h2><code>MultiRingProcess</code> 是 Barhoum 架构在本仓库里的落点</h2>
              <div class="split">
                <div class="codecard"><pre><code>class MultiRingProcess : public G4VDiscreteProcess
GetMeanFreePath:
  *condition = StronglyForced
  return DBL_MAX

PostStepDoIt:
  require gamma + primary + geometry boundary
  require LaueCrystal volume
  infer ring/tile from copy number
  table.Lookup(E, deltaTheta, material, hkl)
  sample ABSORB / TRANSMIT / DIFFRACT</code></pre></div>
                <div class="branch">
                  <div class="card"><h3>ABSORB</h3><p>记录 optics history，停止原 track。</p></div>
                  <div class="card"><h3>TRANSMIT</h3><p>方向保持原入射方向，停止原 track 并写 transmitted output。</p></div>
                  <div class="card"><h3>DIFFRACT</h3><p>按焦点方向生成 secondary gamma，并叠加 mosaic spread。</p></div>
                </div>
              </div>
              <p class="micro">代码：geant4_app/src/laue_multiring_table_demo.cc；查表类：geant4_app/include/optics/LaueEfficiencyTable.hh。</p>
            </div>
            """,
            "具体实现页：G4 process 如何做三分支。",
        ),
        Slide(
            "多环 Ge(111) 几何",
            f"""
            <div class="slide-content">
              <div class="eyebrow">Geometry</div>
              <h2>480-550 keV 五环设计覆盖 511 keV</h2>
              <div class="split">
                <div class="diagram">{lens_svg(rings)}</div>
                <div>
                  <table class="table">
                    <tr><th>Energy</th><th>Radius</th><th>Thickness</th></tr>
                    {''.join(f'<tr><td>{esc(row["design_energy_keV"])} keV</td><td>{float(row["radius_mm"]):.2f} mm</td><td>{float(row["thickness_mm"]):.2f} mm</td></tr>' for row in rings)}
                  </table>
                  <div class="claim">
                    <h3>Bragg geometry audit</h3>
                    <p>{bragg["n_tiles_checked"]} tiles checked; max θ geometry residual {bragg["max_abs_theta_geom_minus_theta_B_rad"]:.2e} rad; minimum radial clearance {bragg["min_radial_clearance_mm"]:.3f} mm.</p>
                  </div>
                </div>
              </div>
            </div>
            """,
            "展示我们的具体几何与 Bragg audit。",
        ),
        Slide(
            "主运行结果",
            f"""
            <div class="slide-content">
              <div class="eyebrow">Current run</div>
              <h2>Geant4 事件层给出三分支和焦斑输出</h2>
              <div class="split">
                <div class="diagram">{branch_svg(run["diffraction_fraction"], run["absorption_fraction"], run["transmission_fraction"])}</div>
                <div class="cards two">
                  <div class="metric"><b>{run["n_diffracted"]:,}</b><span>diffracted photons</span></div>
                  <div class="metric"><b>{run["n_absorbed"]:,}</b><span>absorbed photons</span></div>
                  <div class="metric"><b>{run["n_transmitted"]:,}</b><span>transmitted photons</span></div>
                  <div class="metric"><b>{run["spot_d90_cm"]:.4f} cm</b><span>current focal-plane D90</span></div>
                </div>
              </div>
              <p class="micro">主运行 summary：runs/geant4_laue_multiring_darwin/summary.json；模型：{esc(run["model"])}。</p>
            </div>
            """,
            "用本地 summary 生成的主结果，不夸大为最终仪器 PSF。",
        ),
        Slide(
            "验证链条",
            f"""
            <div class="slide-content">
              <div class="eyebrow">Evidence chain</div>
              <h2>我们没有把 Barhoum 当 benchmark，而是另建数值闭合链</h2>
              <div class="cards">
                <div class="claim"><h3>Barriere 2009</h3><p>Cu/Au mosaic crystal benchmark: max diffraction-efficiency error {barriere["max_abs_diff_eff_error"]:.4f}; max reflectivity error {barriere["max_abs_reflectivity_error"]:.4f}; {barriere["n_cases"]} cases。</p></div>
                <div class="claim"><h3>Kohnle 1998 Ge(111)</h3><p>200-500 keV endpoint check: max endpoint error {kohnle["endpoint_max_abs_error"]:.4f}; context includes two 3-mm Ge(111) crystals and measured double/single ratios。</p></div>
                <div class="claim"><h3>PyTTE</h3><p>{pytte["n_cases"]} perfect-crystal Takagi-Taupin checks; warning count {pytte["max_warning_count"]}; confirms perfect-crystal branch is stronger than our mosaic+absorption table。</p></div>
              </div>
              <p class="small">这些验证支持“当前阶段高可信研究原型”，但不声称已经替代真实晶体批次、装调误差和同参数整机实测。</p>
            </div>
            """,
            "关键可信度页：Barhoum 是架构，Barriere/Kohnle/PyTTE 是数值验证链。",
        ),
        Slide(
            "相同点和不同点",
            """
            <div class="slide-content">
              <div class="eyebrow">Comparison</div>
              <h2>与 Barhoum 对齐的是 process pattern，不是每个模型细节</h2>
              <table class="table">
                <tr><th>维度</th><th>Barhoum 2022</th><th>本仓库做法</th></tr>
                <tr><td>Geant4 入口</td><td>Laue lens advanced example，使用自定义 process 思路。</td><td>App-level <code>G4VDiscreteProcess</code>，不改 Geant4 底层源码。</td></tr>
                <tr><td>触发机制</td><td><code>StronglyForced</code> + very large mean free path + <code>PostStepDoIt</code> 分支。</td><td>同一类结构：boundary 命中 <code>LaueCrystal</code> 后查表并抽样。</td></tr>
                <tr><td>几何</td><td>早期模型含 tube/ring 简化。</td><td>显式 5 rings × 72 tiles，带 Bragg 几何审计。</td></tr>
                <tr><td>概率来源</td><td>公开 talk 主要介绍框架和早期验证。</td><td>Zachariasen/Darwin mosaic 表，外加 Barriere/Kohnle/PyTTE checks。</td></tr>
              </table>
            </div>
            """,
            "这页回答用户之前的问题：是不是这么参考 Barhoum？是架构级参考。",
        ),
        Slide(
            "为什么还要 Geant4",
            """
            <div class="slide-content">
              <div class="eyebrow">Geant4 role</div>
              <h2>光学概率可以离线闭合，但 detector / shielding / activation 仍需要 Geant4</h2>
              <div class="cards">
                <div class="card"><h3>事件一致性</h3><p>Geant4 保留每个 photon 的 track、secondary、材料边界、随机抽样和输出合同。</p></div>
                <div class="card"><h3>仪器背景</h3><p>晶体、支撑、屏蔽、探测器材料中的 Compton、photoelectric、pair production 仍由标准 physics list 处理。</p></div>
                <div class="card"><h3>活化路线</h3><p>同一 phase-space 可接 detector/activation workflow，输出 isotope candidates、decay source 和 delayed focal transport。</p></div>
              </div>
              <div class="claim warn"><h3>边界</h3><p>Laue diffraction 本身不是让标准 EM“自然发生”；它是我们显式加入的光学过程。Geant4 的价值在于把这个过程放回完整粒子输运和探测器环境中。</p></div>
            </div>
            """,
            "回答为什么既然离线有表还要 Geant4：事件、材料、探测器和活化。",
        ),
        Slide(
            "当前事实信心",
            f"""
            <div class="slide-content">
              <div class="eyebrow">Confidence boundary</div>
              <h2>可以高信心地说什么，不能说什么</h2>
              <div class="cards two">
                <div class="claim"><h3>高信心</h3><p>Barhoum 2022 支持 Geant4 Laue process extension 这条软件路线；我们的实现结构与其关键 process pattern 对齐。</p></div>
                <div class="claim"><h3>高信心</h3><p>当前几何由 Bragg law 推出并通过 audit；概率表不是手动校正因子，而是公式驱动并有相邻文献/工具交叉检查。</p></div>
                <div class="claim warn"><h3>中高信心</h3><p>当前 480-550 keV Ge(111) multiring prototype 足够做组会和下一步方案比较。</p></div>
                <div class="claim no"><h3>不能声称</h3><p>还不能说已经复现 Barhoum 未公开代码、真实晶体批次误差、完整 medical imaging 系统，或 publication-grade same-lens closure。</p></div>
              </div>
              <p class="micro">本地审计状态：{esc(audit["status"])}；audit warning: {esc(run["warning"])}</p>
            </div>
            """,
            "结论页：信心高，但边界明确。",
        ),
        Slide(
            "公开资料和本地文件地图",
            """
            <div class="slide-content">
              <div class="eyebrow">Sources and artifacts</div>
              <h2>这份材料的证据来源</h2>
              <div class="cards two">
                <div class="source"><h3>Barhoum 2022</h3><p><a href="https://agenda.infn.it/event/21084/contributions/178539/">Indico contribution page</a><br><a href="https://agenda.infn.it/event/21084/contributions/178539/attachments/95641/136257/Talk_04_Barhoum.pdf">Talk_04_Barhoum.pdf</a><br><a href="https://agenda.infn.it/event/21084/contributions/178539/attachments/95641/131523/GEANT4%20Gamma%20Diffraction%20Code%20Based%20on%20Laue%20lens%20Modelling%20Design%20Foundation%20and%20Implementation%20of%20the%20First%20Set%20of%20Models%20in%20GEANT4.pdf">conference abstract PDF</a></p></div>
                <div class="source"><h3>Related Geant4 crystal work</h3><p><a href="https://digitalcommons.library.tmc.edu/uthgsbs_docs/3758/">Guan et al. 2023, G4CrystalBraggReflection</a><br><a href="https://pubmed.ncbi.nlm.nih.gov/40246994/">Barhoum et al. 2025, multi-Laue SPECT</a></p></div>
                <div class="source"><h3>本地实现</h3><p><code>geant4_app/src/laue_multiring_table_demo.cc</code><br><code>geant4_app/include/optics/LaueEfficiencyTable.hh</code><br><code>external_baseline/laue_raytrace_py/mosaic_darwin.py</code></p></div>
                <div class="source"><h3>本地结果</h3><p><code>runs/geant4_laue_multiring_darwin/summary.json</code><br><code>runs/laue_physics_confidence_audit/summary.json</code><br><code>data/laue/Ge111_480_550keV_darwin_mosaic_table.csv</code></p></div>
              </div>
            </div>
            """,
            "最后给出处和本地文件，方便组会上追溯。",
        ),
    ]
    return slides


def write_deck(slides: list[Slide], out_path: Path) -> None:
    slide_html: list[str] = []
    notes: list[dict[str, str]] = []
    for index, slide in enumerate(slides):
        active = " active" if index == 0 else ""
        slide_html.append(f'<div class="slide{active}" data-slide="{index}">{slide.body}</div>')
        notes.append({"slide": str(index), "title": slide.title, "notes": slide.note})

    script = """
    const slides = Array.from(document.querySelectorAll('.slide'));
    let current = 0;
    function updateProgress() {
      const bar = document.getElementById('progress');
      bar.style.width = ((current + 1) / slides.length * 100).toFixed(2) + '%';
      document.getElementById('counter').textContent = (current + 1) + ' / ' + slides.length;
    }
    function goTo(index) {
      current = Math.max(0, Math.min(slides.length - 1, index));
      slides.forEach((slide, i) => slide.classList.toggle('active', i === current));
      updateProgress();
    }
    function next() { goTo(current + 1); }
    function prev() { goTo(current - 1); }
    window.goTo = goTo;
    window.next = next;
    window.prev = prev;
    document.addEventListener('keydown', (event) => {
      if (event.key === 'ArrowRight' || event.key === 'PageDown' || event.key === ' ') next();
      if (event.key === 'ArrowLeft' || event.key === 'PageUp') prev();
      if (event.key === 'Home') goTo(0);
      if (event.key === 'End') goTo(slides.length - 1);
    });
    updateProgress();
    """

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="generator" content="html-slides v0.9.4">
  <title>Barhoum Laue Lens Work and Our Geant4-Darwin Implementation</title>
  <style>{VIEWPORT_BASE_CSS}\n{CUSTOM_CSS}</style>
</head>
<body>
  <div class="progress" id="progress"></div>
  <div class="deck" id="deck">
    {''.join(slide_html)}
  </div>
  <div class="controls" aria-label="slide navigation">
    <button onclick="prev()" title="Previous slide">‹</button>
    <button onclick="next()" title="Next slide">›</button>
    <button id="counter" onclick="goTo(0)" title="Back to first slide">1 / {len(slides)}</button>
  </div>
  <script class="slide-notes" type="application/json">{json.dumps(notes, ensure_ascii=False)}</script>
  <script>{script}</script>
</body>
</html>
"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_text, encoding="utf-8")


def build(out_path: Path) -> None:
    write_deck(build_slides(), out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an HTML slide deck introducing Barhoum 2022 and this repository's Laue implementation.")
    parser.add_argument("--out", default="records/2026-05-21_barhoum_laue_work_and_our_method.html")
    args = parser.parse_args()
    output = Path(args.out)
    if not output.is_absolute():
        output = ROOT / output
    build(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
