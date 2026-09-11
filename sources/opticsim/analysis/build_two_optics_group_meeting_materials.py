#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import random
from pathlib import Path
from typing import Any, Iterable


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
    --bg: #0d0f0c;
    --panel: #151812;
    --panel2: #1e2419;
    --ink: #f3f1e8;
    --muted: #b8b7a8;
    --line: #3d4633;
    --teal: #49c4b1;
    --amber: #f0b35a;
    --lime: #a7d96c;
    --red: #e06c62;
    --steel: #8aa7b2;
    --slide-padding: clamp(1rem, 3vw, 3rem);
}
* { box-sizing: border-box; }
body {
    margin: 0;
    background:
      radial-gradient(circle at 12% 18%, rgba(73,196,177,.14), transparent 26%),
      radial-gradient(circle at 86% 72%, rgba(240,179,90,.12), transparent 28%),
      linear-gradient(135deg, #0d0f0c 0%, #171b14 52%, #0a0c0b 100%);
    color: var(--ink);
    font-family: "Aptos", "Noto Sans CJK SC", "Microsoft YaHei", "Segoe UI", sans-serif;
}
.deck { width: 100vw; min-height: 100vh; }
.slide { display: none; }
.slide.active { display: flex; }
.slide::before {
    content: "";
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
    background-size: 46px 46px;
    mask-image: linear-gradient(to bottom, rgba(0,0,0,.8), rgba(0,0,0,.35));
    pointer-events: none;
}
.slide-content { position: relative; z-index: 1; gap: clamp(.7rem, 1.6vh, 1.4rem); }
.eyebrow {
    color: var(--amber);
    font-size: clamp(.66rem, 1vw, .92rem);
    letter-spacing: .12em;
    text-transform: uppercase;
    font-weight: 800;
}
h1, h2, h3, p { margin: 0; }
h1 {
    font-family: Georgia, "Noto Serif CJK SC", serif;
    font-size: clamp(2.2rem, 7vw, 6rem);
    line-height: .95;
    letter-spacing: 0;
    max-width: 13ch;
}
h2 {
    font-family: Georgia, "Noto Serif CJK SC", serif;
    font-size: clamp(1.65rem, 4vw, 3.7rem);
    line-height: 1.02;
    letter-spacing: 0;
}
h3 {
    color: var(--amber);
    font-size: clamp(.95rem, 1.55vw, 1.28rem);
    letter-spacing: 0;
}
.subtitle {
    font-size: clamp(1rem, 1.8vw, 1.45rem);
    line-height: 1.4;
    color: var(--muted);
    max-width: 72ch;
}
.split {
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(0, .95fr);
    gap: clamp(1rem, 2vw, 2rem);
    align-items: stretch;
}
.cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: clamp(.65rem, 1.25vw, 1rem);
}
.cards.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.cards.four { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.card, .metric, .claim, .source {
    border: 1px solid var(--line);
    background: linear-gradient(180deg, rgba(255,255,255,.055), rgba(255,255,255,.025));
    border-radius: 8px;
    padding: clamp(.72rem, 1.4vw, 1.1rem);
    box-shadow: 0 12px 32px rgba(0,0,0,.22);
}
.card p, .claim p, .source p {
    color: var(--muted);
    font-size: clamp(.76rem, 1.15vw, .98rem);
    line-height: 1.38;
    margin-top: .35rem;
}
.metric b {
    display: block;
    font-size: clamp(1.25rem, 3.2vw, 2.65rem);
    color: var(--lime);
    font-family: Georgia, serif;
    line-height: 1;
}
.metric span {
    display: block;
    color: var(--muted);
    font-size: clamp(.68rem, 1vw, .88rem);
    margin-top: .35rem;
    line-height: 1.3;
}
.claim {
    border-left: 5px solid var(--teal);
}
.claim.warn { border-left-color: var(--amber); }
.claim.risk { border-left-color: var(--red); }
table {
    width: 100%;
    border-collapse: collapse;
    font-size: clamp(.62rem, .92vw, .84rem);
    line-height: 1.22;
    overflow: hidden;
    border-radius: 8px;
}
th, td {
    border-bottom: 1px solid var(--line);
    padding: clamp(.32rem, .65vw, .55rem);
    text-align: left;
    vertical-align: top;
}
th { color: var(--amber); background: rgba(255,255,255,.045); }
code, .mono {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
    color: #d8f8ef;
}
.tagrow { display: flex; flex-wrap: wrap; gap: .45rem; }
.tag {
    display: inline-flex;
    align-items: center;
    min-height: 1.6rem;
    border: 1px solid var(--line);
    color: var(--ink);
    border-radius: 999px;
    padding: .16rem .55rem;
    font-size: clamp(.62rem, .9vw, .82rem);
    background: rgba(255,255,255,.04);
}
.diagram {
    min-height: min(48vh, 430px);
    border: 1px solid var(--line);
    border-radius: 8px;
    background: rgba(0,0,0,.18);
    padding: clamp(.6rem, 1vw, .9rem);
}
svg { width: 100%; height: 100%; max-height: min(52vh, 460px); }
.bar text, .flow text { font-family: "Aptos", "Noto Sans CJK SC", sans-serif; }
.footer {
    position: absolute;
    left: var(--slide-padding);
    right: var(--slide-padding);
    bottom: clamp(.45rem, 1vh, .9rem);
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    color: #858b7e;
    font-size: clamp(.58rem, .85vw, .76rem);
    z-index: 2;
}
.controls {
    position: fixed;
    right: clamp(.6rem, 1.5vw, 1.4rem);
    bottom: clamp(.6rem, 1.5vw, 1.4rem);
    z-index: 9;
    display: flex;
    gap: .4rem;
}
.controls button {
    border: 1px solid var(--line);
    background: rgba(21,24,18,.86);
    color: var(--ink);
    border-radius: 7px;
    min-width: 2rem;
    min-height: 2rem;
    cursor: pointer;
}
.progress {
    position: fixed;
    left: 0;
    top: 0;
    height: 4px;
    background: linear-gradient(90deg, var(--teal), var(--amber), var(--lime));
    z-index: 10;
    width: 0;
}
.small { font-size: clamp(.66rem, .94vw, .82rem); color: var(--muted); line-height: 1.32; }
.quote {
    font-family: Georgia, "Noto Serif CJK SC", serif;
    font-size: clamp(1.15rem, 2.4vw, 2.2rem);
    line-height: 1.2;
    color: #fff7df;
    max-width: 29ch;
}
.compact-list {
    margin: 0;
    padding-left: 1.1rem;
    color: var(--muted);
    font-size: clamp(.72rem, 1.05vw, .92rem);
    line-height: 1.34;
}
.compact-list li { margin: .2rem 0; }
@media (max-width: 900px) {
    .split, .cards.two { grid-template-columns: 1fr; }
    .cards, .cards.four { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
    .cards, .cards.four { grid-template-columns: 1fr; }
    .footer { display: none; }
}
"""


def read_json(relative: str) -> dict[str, Any]:
    with (ROOT / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def pct(value: float, digits: int = 1) -> str:
    return f"{100.0 * value:.{digits}f}%"


def num(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}"


def cards(items: Iterable[tuple[str, str]], columns: str = "") -> str:
    body = []
    for title, text in items:
        body.append(f"<div class='card'><h3>{esc(title)}</h3><p>{text}</p></div>")
    cls = f"cards {columns}".strip()
    return f"<div class='{cls}'>" + "".join(body) + "</div>"


def metrics(items: Iterable[tuple[str, str]]) -> str:
    return "<div class='cards four'>" + "".join(
        f"<div class='metric'><b>{value}</b><span>{esc(label)}</span></div>" for label, value in items
    ) + "</div>"


def table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{esc(item)}</th>" for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def claim(text: str, kind: str = "") -> str:
    return f"<div class='claim {kind}'><p>{text}</p></div>"


def phase_space_spot_metrics(relative_csv: str, fov_radius_arcmin: float, seed: int = 20260521) -> dict[str, float]:
    points: list[tuple[float, float]] = []
    with (ROOT / relative_csv).open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            points.append((float(row["x_mm"]), float(row["y_mm"])))
    if not points:
        raise ValueError(f"no phase-space rows in {relative_csv}")

    def diameters(samples: list[tuple[float, float]]) -> dict[str, float]:
        radii = sorted(math.hypot(x, y) for x, y in samples)
        out: dict[str, float] = {}
        for label, frac in (("d50_cm", 0.50), ("d90_cm", 0.90), ("d95_cm", 0.95), ("d99_cm", 0.99)):
            idx = max(0, min(len(radii) - 1, math.ceil(frac * len(radii)) - 1))
            out[label] = 2.0 * radii[idx] / 10.0
        out["full_extent_cm"] = 2.0 * radii[-1] / 10.0
        return out

    rng = random.Random(seed)
    focal_length_mm = 12000.0
    fov_radius_rad = math.radians(fov_radius_arcmin / 60.0)
    fov_points = []
    for x_mm, y_mm in points:
        r = math.sqrt(rng.random()) * fov_radius_rad
        phi = 2.0 * math.pi * rng.random()
        fov_points.append((x_mm + focal_length_mm * math.tan(r * math.cos(phi)),
                           y_mm + focal_length_mm * math.tan(r * math.sin(phi))))
    out = {f"on_axis_{key}": value for key, value in diameters(points).items()}
    out.update({f"fov_{key}": value for key, value in diameters(fov_points).items()})
    out["geometric_fov_diameter_cm"] = 2.0 * focal_length_mm * math.tan(fov_radius_rad) / 10.0
    return out


def throughput_bar(channel: dict[str, Any], laue: dict[str, Any]) -> str:
    rows = [
        ("CAM511 headline", 0.800, "#f0b35a"),
        ("Channel 1 nm no Si path", channel["literature_roughness_1nm_no_si_variant"]["transmissivity"], "#49c4b1"),
        ("Channel ideal no Si path", channel["best_no_fudge_variant"]["transmissivity"], "#a7d96c"),
        ("Laue Ge(111) multiring", laue["diffraction_fraction"], "#8aa7b2"),
    ]
    y0 = 54
    row_h = 50
    pieces = [
        "<svg class='bar' viewBox='0 0 860 300' role='img' aria-label='Optics throughput comparison'>",
        "<text x='18' y='28' fill='#f3f1e8' font-size='18' font-weight='700'>效率/衍射分支对照</text>",
    ]
    for idx, (label, value, color) in enumerate(rows):
        y = y0 + idx * row_h
        width = max(2, 520 * value)
        pieces.append(f"<text x='18' y='{y+18}' fill='#b8b7a8' font-size='14'>{esc(label)}</text>")
        pieces.append(f"<rect x='240' y='{y}' width='{width:.1f}' height='24' rx='4' fill='{color}'/>")
        pieces.append(f"<text x='{252+width:.1f}' y='{y+18}' fill='#f3f1e8' font-size='14'>{100*value:.1f}%</text>")
    pieces.append("<text x='18' y='270' fill='#858b7e' font-size='12'>Channel 是透过率；Laue 是 diffracted branch fraction，物理含义不同，不能直接当同一效率排名。</text>")
    pieces.append("</svg>")
    return "<div class='diagram'>" + "".join(pieces) + "</div>"


def flow_svg(labels: list[str], title: str) -> str:
    width = 900
    y = 125
    box_w = 158
    gap = 36
    x0 = 28
    pieces = [
        f"<svg class='flow' viewBox='0 0 {width} 260' role='img' aria-label='{esc(title)}'>",
        f"<text x='24' y='30' fill='#f3f1e8' font-size='19' font-weight='700'>{esc(title)}</text>",
    ]
    for idx, label in enumerate(labels):
        x = x0 + idx * (box_w + gap)
        color = "#49c4b1" if idx % 3 == 0 else "#f0b35a" if idx % 3 == 1 else "#a7d96c"
        pieces.append(f"<rect x='{x}' y='{y-42}' width='{box_w}' height='84' rx='8' fill='rgba(255,255,255,.055)' stroke='{color}'/>")
        pieces.append(f"<text x='{x+12}' y='{y-8}' fill='#f3f1e8' font-size='14'>{esc(label[:18])}</text>")
        if len(label) > 18:
            pieces.append(f"<text x='{x+12}' y='{y+13}' fill='#b8b7a8' font-size='12'>{esc(label[18:38])}</text>")
        if idx < len(labels) - 1:
            ax = x + box_w + 7
            pieces.append(f"<line x1='{ax}' y1='{y}' x2='{ax+gap-14}' y2='{y}' stroke='#8aa7b2' stroke-width='2'/>")
            pieces.append(f"<path d='M {ax+gap-14} {y} l -8 -5 v 10 z' fill='#8aa7b2'/>")
    pieces.append("</svg>")
    return "<div class='diagram'>" + "".join(pieces) + "</div>"


def title_slide(title: str, subtitle: str, tag: str) -> dict[str, str]:
    return {
        "tag": tag,
        "html": f"""
        <div class='eyebrow'>{esc(tag)}</div>
        <h1>{esc(title)}</h1>
        <p class='subtitle'>{subtitle}</p>
        <div class='tagrow'>
          <span class='tag'>Channel: W/Si multilayer reflection</span>
          <span class='tag'>Laue: Ge(111) diffraction</span>
          <span class='tag'>Geant4: detector + activation</span>
        </div>
        """,
        "notes": "Deck is intentionally long and usable as a material library for group meeting preparation.",
    }


def build_slides(channel: dict[str, Any], laue_audit: dict[str, Any], laue_run: dict[str, Any],
                 activation: dict[str, Any], detector: dict[str, Any], io_contract: dict[str, Any],
                 spot: dict[str, float]) -> list[dict[str, str]]:
    ch_best = channel["best_no_fudge_variant"]
    ch_1nm = channel["literature_roughness_1nm_no_si_variant"]
    ch_1nm_si = channel["literature_roughness_1nm_with_si_variant"]
    bragg = laue_audit["bragg_audit"]
    kohnle = laue_audit["kohnle"]
    barriere = laue_audit["barriere"]
    pytte_case = laue_audit["pytte"]["cases"][2]

    slides: list[dict[str, str]] = [
        title_slide(
            "511 keV 两套光学模拟材料库",
            "用于组会备讲：Channel optics 与 Laue lens 的物理原理、实现证据、Geant4 协同和风险边界。文件是备材料，不是精简演讲版。",
            "Opticsim group meeting packet / 2026-05-21",
        ),
        {
            "tag": "How to use",
            "html": f"""
            <div class='eyebrow'>material library</div><h2>这份 HTML 怎么用</h2>
            {cards([
                ("先讲结论", "第 3-7 页给出核心判断、可信度和两套方案的分工。"),
                ("再选一条线", "Channel 和 Laue 各有完整证据链，可按老师问题临场选页。"),
                ("最后讲协同", "Geant4 不负责 nm 膜相干反射，但负责 detector、mass、activation。"),
            ])}
            {claim("建议正式组会只取 12-16 页；其余页作为答疑材料。")}
            """,
            "notes": "The user said they probably will not use the deck directly, so the deck is organized as reusable material.",
        },
        {
            "tag": "One-line conclusion",
            "html": f"""
            <div class='eyebrow'>executive conclusion</div><h2>当前最稳妥的总表述</h2>
            <p class='quote'>两套光学都已经做到公开物理模型层面的可审计模拟；Channel 更接近 511-CAM headline，Laue 更接近 Geant4 内生光学过程。</p>
            <div class='cards two'>
              <div class='claim'><h3>可以说</h3><p>公开几何、关键物理、表驱动概率、phase-space 交接和验证记录都已经建立。</p></div>
              <div class='claim risk'><h3>不要说</h3><p>不要说已经逐项复刻未公开 IDL/IMD 或已经完成 production-quality activation background。</p></div>
            </div>
            """,
            "notes": "This is the safest short answer for a supervisor asking whether the work is credible.",
        },
        {
            "tag": "Confidence",
            "html": f"""
            <div class='eyebrow'>confidence ladder</div><h2>事实信心分层</h2>
            {cards([
                ("高: Laue 几何/表驱动", "Bragg 几何、5-ring Ge(111) table、Barriere/Kohnle/PyTTE 交叉检查均有本地证据。"),
                ("中高: Channel 公开物理", "30/150 nm W/Si、open fraction、Parratt recursion 和 wall-by-wall 路径已经闭合。"),
                ("中: CAM511 精确复刻", "原始 IDL ray tracing 与 3.6 cm 光斑口径未完全公开，只能做公开信息层面复现。"),
            ])}
            {claim("总口径：当前足够支持组会中的物理合理性论证，但不把它包装成原论文代码复刻。", "warn")}
            """,
            "notes": "Separates evidence-backed claims from exact reproduction claims.",
        },
        {
            "tag": "Two optics",
            "html": f"""
            <div class='eyebrow'>comparison</div><h2>两套光学不是互相替代</h2>
            {table(["维度", "Channel optics", "Laue lens"], [
                ["核心物理", "W/Si 多层膜 total external reflection，多次 channeling", "Ge(111) Bragg/Laue diffraction，mosaic-crystal efficiency"],
                ["511 keV 结果", f"no-fudge T={ch_1nm['transmissivity']:.4f}-{ch_best['transmissivity']:.4f}，CAM511 为 0.80", f"diffracted fraction={laue_run['diffraction_fraction']:.4f}，480-550 keV 多环"],
                ["Geant4角色", "Detector/mass/activation 强项；光学反射由表驱动外部模型给 phase_space", "可在 Geant4 process 里直接执行 table-driven diffraction"],
                ["主要风险", "IDL/IMD 原始路径记账未公开", "Ge(111) 500 keV 同晶体实测闭合仍是未来项"],
            ])}
            """,
            "notes": "Use this when asked why both routes exist.",
        },
        {
            "tag": "Architecture",
            "html": f"""
            <div class='eyebrow'>system architecture</div><h2>推荐协同结构</h2>
            {flow_svg(["Optics physics model", "phase_space.csv", "Geant4 detector", "prompt inventory", "delayed decay"], "光学与 Geant4 的边界")}
            {claim("原则：不要让 Geant4 直接几何化 nm 多层膜；用 Geant4 做它擅长的宏观输运、探测器、活化和衰变。")}
            """,
            "notes": "This slide defends the IDL/Python plus Geant4 architecture.",
        },
        {
            "tag": "Headline metrics",
            "html": f"""
            <div class='eyebrow'>numbers to remember</div><h2>组会上最容易被问到的数字</h2>
            {metrics([
                ("Channel public no-fudge, 1 nm/no Si path", pct(ch_1nm["transmissivity"])),
                ("Channel best ideal/no Si path", pct(ch_best["transmissivity"])),
                ("CAM511 reported optics T", "80.0%"),
                ("Laue multiring diffracted branch", pct(laue_run["diffraction_fraction"])),
            ])}
            {throughput_bar(channel, laue_run)}
            """,
            "notes": "Channel throughput and Laue diffracted fraction are not identical physical quantities.",
        },
        {
            "tag": "Channel principle",
            "html": f"""
            <div class='eyebrow'>channel optics</div><h2>Channel 的物理原理</h2>
            {cards([
                ("低密度通道", "光子在 Si spacer 内沿弯曲通道前进，遇到 W/Si 边界。"),
                ("小掠入射角", "511 keV 下反射只在非常小的 grazing angle 范围有效。"),
                ("多次反射累积", "一个幸存光子自然经历约 19-21 次 wall bounce，不是人为固定次数。"),
            ])}
            {claim("现在的 wall-by-wall 实现让路径自己产生 bounce count 和 grazing angle。")}
            """,
            "notes": "Physical origin of channeling: total external reflection in bent multilayer spacers.",
        },
        {
            "tag": "Channel public geometry",
            "html": f"""
            <div class='eyebrow'>channel public inputs</div><h2>公开几何已经对齐 CAM511</h2>
            {table(["参数", "公开值 / 本地配置"], [
                ["能量 / 焦距", "511 keV / 12 m"],
                ["环半径", "2.25, 3.0, 3.75, 4.5 cm"],
                ["弯曲角", "0.11, 0.14, 0.18, 0.22 deg"],
                ["段长度", "2.1, 2.7, 3.5, 4.6 cm"],
                ["多层膜", "30 nm W + 150 nm Si，总厚 5.4 um"],
                ["open fraction", "150 / (30 + 150) = 0.8333"],
            ])}
            """,
            "notes": "Source: 511-CAM arXiv/JATIS and config/cam511_channel_baseline.yaml.",
        },
        {
            "tag": "Channel closure",
            "html": f"""
            <div class='eyebrow'>independent closure</div><h2>Channel 的独立闭合包</h2>
            {cards([
                ("光学常数", "30 keV Henke/CXRO-range 与 xraydb/Chantler 差异约 0.03%-1.30%；511 keV electron-density delta 差异约 0.14%-1.07%。"),
                ("反射率算法", "manual Parratt recursion 与 xraydb multilayer reflectivity 逐点一致，max |ΔR| = 0。"),
                ("无校正预测", "不乘额外校正因子；只改变 roughness 与是否显式计 Si path absorption 的物理口径。"),
            ])}
            {claim("结论：反射率 provenance 已经不是主要 blocker；剩余问题是原始 IDL 的路径/吸收/光斑口径。")}
            """,
            "notes": "Generated by analysis/build_channel_independent_closure.py.",
        },
        {
            "tag": "Channel no-fudge results",
            "html": f"""
            <div class='eyebrow'>throughput</div><h2>不引入校正因子的 Channel 结果</h2>
            {table(["变体", "T", "Aeff cm2", "mean bounces", "相对 CAM511"], [
                ["1 nm roughness, no Si path", f"{ch_1nm['transmissivity']:.4f}", f"{ch_1nm['effective_area_cm2']:.2f}", f"{ch_1nm['mean_bounces_per_survivor']:.2f}", "-0.0631"],
                ["0 nm ideal, no Si path", f"{ch_best['transmissivity']:.4f}", f"{ch_best['effective_area_cm2']:.2f}", f"{ch_best['mean_bounces_per_survivor']:.2f}", "-0.0385"],
                ["1 nm roughness, with Si path", f"{ch_1nm_si['transmissivity']:.4f}", f"{ch_1nm_si['effective_area_cm2']:.2f}", f"{ch_1nm_si['mean_bounces_per_survivor']:.2f}", "-0.4341"],
            ])}
            {claim("推荐讲法：公开信息层面复现到 0.74-0.76，对 CAM511 0.80 已是同量级且接近。", "warn")}
            """,
            "notes": "The with-Si-path row is a pressure test, not the preferred headline.",
        },
        {
            "tag": "Channel spot",
            "html": f"""
            <div class='eyebrow'>spot interpretation</div><h2>为什么 spot 一开始看起来偏小</h2>
            {table(["口径", "直径指标", "解释"], [
                ["on-axis point source", f"D90={spot['on_axis_d90_cm']:.2f} cm; full={spot['on_axis_full_extent_cm']:.2f} cm", "严格平行点源，本征光斑"],
                ["CAM511 FOV radius", "4.47 arcmin", "公开字段，投到 12 m 为约 3.12 cm 几何直径"],
                ["FOV-enveloped", f"D90={spot['fov_d90_cm']:.2f} cm; D95={spot['fov_d95_cm']:.2f} cm", "把公开视场包络投到焦平面，接近 3.5-3.6 cm"],
            ])}
            {claim("3.6 cm 更像全斑/近全包络口径，不是论文中明确写出的 FWHM。")}
            """,
            "notes": "This uses existing phase_space and the paper's FOV radius; it is not a fitted scale factor.",
        },
        {
            "tag": "Channel Geant4",
            "html": f"""
            <div class='eyebrow'>geant4 handoff</div><h2>Channel 与 Geant4 的协同边界</h2>
            {cards([
                ("光学外部完成", "Parratt/wall-by-wall 负责 R/A/T、bounce history 和 focal-plane phase_space。"),
                ("Geant4 接 phase_space", f"wall-by-wall detector smoke: input 1000 events, TES detected fraction {detector['tes_detection_fraction']:.3f}。"),
                ("合同验证", f"phase_space/optics_history/hits/event_summary 共 {io_contract['n_tables']} 张表，ok={str(io_contract['ok']).lower()}。"),
            ])}
            {claim("Channel 的 Geant4 当前不是 nm 多层膜物理求解器，而是 detector/mass/background 协同层。")}
            """,
            "notes": "Source: runs/geant4_detector_wallbywall_1k and IO validation summary.",
        },
        {
            "tag": "Channel source chain",
            "html": f"""
            <div class='eyebrow'>evidence map</div><h2>Channel 证据链文件</h2>
            {table(["用途", "文件"], [
                ["独立闭合包", "<span class='mono'>analysis/build_channel_independent_closure.py</span>"],
                ["HTML 报告", "<span class='mono'>records/2026-05-21_channel_independent_closure.html</span>"],
                ["wall-by-wall runner", "<span class='mono'>analysis/run_channel_wallbywall_rebuild.py</span>"],
                ["核心模型", "<span class='mono'>external_baseline/channel_raytrace_py/wallbywall_channel.py</span>"],
                ["公开文献文本", "<span class='mono'>records/channel_external_sources/*.txt</span>"],
            ])}
            """,
            "notes": "File map for future edits or supervisor questions.",
        },
        {
            "tag": "Laue principle",
            "html": f"""
            <div class='eyebrow'>laue lens</div><h2>Laue 的物理原理</h2>
            {cards([
                ("Bragg 条件", "不同能量由不同环半径满足 2d sinθ = nλ，衍射方向指向焦平面。"),
                ("Mosaic crystal", "用 mosaic spread 和厚度控制 diffracted / absorbed / transmitted 分支。"),
                ("Geant4 process", "在 Geant4 中对命中晶体的 gamma 按表采样 diffraction，不是简单 p=1 toy。"),
            ])}
            {claim("Laue 更适合做 Geant4 内部光学过程，因为尺度是晶体块/环，不是 nm 多层膜相干堆栈。")}
            """,
            "notes": "Laue route is closer to Geant4-native optics.",
        },
        {
            "tag": "Laue geometry",
            "html": f"""
            <div class='eyebrow'>laue geometry</div><h2>5-ring Ge(111) 配置</h2>
            {table(["ring", "E keV", "radius mm", "tiles", "thickness mm"], [
                ["0", "480", "65.644", "72", "9.452"],
                ["1", "500", "63.018", "72", "9.947"],
                ["2", "511", "61.662", "72", "10.219"],
                ["3", "530", "59.451", "72", "10.686"],
                ["4", "550", "57.289", "72", "11.176"],
            ])}
            {claim(f"Bragg audit: n_rings={bragg['n_rings']}，checked tiles={bragg['n_tiles_checked']}，ok={str(bragg['ok']).lower()}。")}
            """,
            "notes": "Source: data/laue/ge111_480_550keV_multiring_darwin_config.csv.",
        },
        {
            "tag": "Laue implementation",
            "html": f"""
            <div class='eyebrow'>geant4 laue implementation</div><h2>table-driven Geant4 Laue 主结果</h2>
            {metrics([
                ("primaries", f"{laue_run['n_primaries']:,}"),
                ("diffracted", pct(laue_run["diffraction_fraction"])),
                ("absorbed", pct(laue_run["absorption_fraction"])),
                ("transmitted", pct(laue_run["transmission_fraction"])),
            ])}
            {claim(f"spot D90={laue_run['spot_d90_cm']:.3f} cm；table rows={laue_run['efficiency_table_rows']}；energy range={laue_run['energy_min_keV']}-{laue_run['energy_max_keV']} keV。")}
            """,
            "notes": "Source: runs/geant4_laue_multiring_darwin/summary.json.",
        },
        {
            "tag": "Laue benchmarks",
            "html": f"""
            <div class='eyebrow'>validation</div><h2>Laue 不是只靠自写公式</h2>
            {cards([
                ("Barriere 2009", f"6 cases, max diffraction-efficiency error {barriere['max_abs_diff_eff_error']:.4f}, reflectivity error {barriere['max_abs_reflectivity_error']:.4f}。"),
                ("Kohnle 1998", f"7 Ge(111) cases, endpoint max abs error {kohnle['endpoint_max_abs_error']:.4f}；本地 PDF 已归档。"),
                ("PyTTE", f"511 keV perfect-crystal check: peak diffraction {pytte_case['pytte_peak_diffraction']:.3f}, flux sum {pytte_case['pytte_center_flux_sum']:.6f}。"),
            ])}
            """,
            "notes": "Benchmarks support the current-stage confidence for Laue.",
        },
        {
            "tag": "Laue confidence",
            "html": f"""
            <div class='eyebrow'>confidence boundary</div><h2>Laue 的强项和未闭合项</h2>
            {cards([
                ("强项", "Bragg geometry 与 table-driven Geant4 process 已经完整跑通，且有多源 benchmark。"),
                ("当前缺口", "Ge(111) 500 keV 同晶体/同厚度实测效率闭合仍不是公开完全闭合。"),
                ("可用结论", "可作为 511 keV 附近 Laue 透镜 Geant4 方案的高可信研究原型。"),
            ])}
            {claim("不要把 Laue 旧 p_diff=1 toy 当成主结果；主结果是 multiring Darwin mosaic table。", "warn")}
            """,
            "notes": "Clear distinction from old toy implementation.",
        },
        {
            "tag": "Activation",
            "html": f"""
            <div class='eyebrow'>activation workflow</div><h2>活化分析为什么仍然要 Geant4</h2>
            {flow_svg(["far-field particles", "Geant4 mass transport", "activation inventory", "day-N source builder", "RadioactiveDecay"], "activation path")}
            {claim(f"当前 synthetic Al-28 day15 decay focal run: n={activation['n_simulated']}，secondary crossings={activation['n_secondary_crossings']}；它证明工作流，不代表最终本底率。")}
            """,
            "notes": "Geant4 is valuable even if optical reflection is external.",
        },
        {
            "tag": "Detector",
            "html": f"""
            <div class='eyebrow'>detector handoff</div><h2>optics 到 detector 的接口已经稳定</h2>
            {table(["表", "当前证据"], [
                ["phase_space.csv", "光学输出焦平面 gamma，作为 detector source"],
                ["optics_history.csv", "记录反射/衍射/吸收历史，便于审计"],
                ["hits.csv", "Geant4 detector hit 输出"],
                ["event_summary.csv", "detector event-level 合同输出"],
                ["IO contract", f"ok={str(io_contract['ok']).lower()}，n_tables={io_contract['n_tables']}"],
            ])}
            """,
            "notes": "This is useful when asked whether optics can feed the later detector model.",
        },
        {
            "tag": "Why not pure Geant4 channel",
            "html": f"""
            <div class='eyebrow'>method choice</div><h2>为什么 Channel 不强行纯 Geant4</h2>
            {cards([
                ("物理尺度不匹配", "nm W/Si multilayer 的相干反射属于光学常数/传输矩阵问题，不是常规 G4 边界散射。"),
                ("计算语义不匹配", "几何化每一层会得到大量边界步进，但不会自动产生 IMD/Parratt coherent reflectivity。"),
                ("更合理做法", "Geant4 建宏观有效 wall/surface，物理上查 R/A/T 表并记录 history。"),
            ])}
            {claim("这不是逃避 Geant4，而是把物理模型放在正确层级。")}
            """,
            "notes": "Use this as a defense against pure-Geant4 objections.",
        },
        {
            "tag": "Talking script",
            "html": f"""
            <div class='eyebrow'>copy-ready wording</div><h2>可以直接拿去说的版本</h2>
            <div class='claim'><p>Channel optics 方面，我们按公开 CAM511/Shirazi 几何和 W/Si 30/150 nm 结构重建了 wall-by-wall 光线追踪，并用独立 Parratt/IMD-equivalent 反射率闭合。无额外校正因子时，透过率约 0.74-0.76，接近 CAM511 报告的 0.80。</p></div>
            <div class='claim'><p>Laue 方面，我们实现了 Ge(111) 480-550 keV multiring table-driven Geant4 process，Bragg 几何、Barriere/Kohnle/PyTTE benchmark 均通过，当前主结果为 100k primaries 下 diffracted fraction 约 0.246。</p></div>
            """,
            "notes": "Copy-ready short narrative.",
        },
        {
            "tag": "What not to claim",
            "html": f"""
            <div class='eyebrow'>risk control</div><h2>这些话不要说过头</h2>
            {cards([
                ("不要说", "Channel 已经完全复刻原始 CAM511 IDL/IMD。"),
                ("不要说", "Geant4 已经直接模拟了 nm 多层膜相干反射。"),
                ("不要说", "Activation background 已经是可发表最终本底率。"),
                ("可以说", "公开物理模型层面已闭合，剩余是 unpublished implementation / production statistics。"),
            ], "four")}
            """,
            "notes": "Risk boundary slide.",
        },
        {
            "tag": "Likely Q&A",
            "html": f"""
            <div class='eyebrow'>defense notes</div><h2>可能被问到的问题</h2>
            {table(["问题", "建议回答"], [
                ["Channel 的 80% 是不是调出来的？", "不是。无校正 public geometry 得到 0.74-0.76；80% 仍标注为 CAM511 headline，不硬说完全推出。"],
                ["spot 为什么一开始只有 1 cm？", "那是 on-axis D90。论文 3.6 cm 未定义 FWHM/D90；用公开 FOV 半径得到 D90-D95 约 3.3-3.5 cm。"],
                ["Laue 是否比 Channel 更可信？", "Laue 的 Geant4 process 更直接；Channel 的 CAM511 目标更接近任务概念。两者用途不同。"],
            ])}
            """,
            "notes": "Prepared answers for group meeting.",
        },
        {
            "tag": "Next checks",
            "html": f"""
            <div class='eyebrow'>next work</div><h2>最能继续提高信心的三件事</h2>
            {cards([
                ("Channel off-axis physical trace", "把 4.47 arcmin 入射角真正放进 wall-by-wall 初始方向，而不只是焦平面后处理。"),
                ("Channel Geant4 surface process", "用 effective curved wall + R/A/T lookup，做到与 Python wall-by-wall 一致的 history。"),
                ("Laue material closure", "寻找或生成 Ge(111) 500 keV 同厚度实验/高保真理论对照。"),
            ])}
            """,
            "notes": "Prioritized next checks.",
        },
        {
            "tag": "Source links",
            "html": f"""
            <div class='eyebrow'>sources</div><h2>报告用主要来源</h2>
            {table(["来源", "用途"], [
                ["511-CAM arXiv/JATIS", "CAM511 geometry, 80%, 50.89 cm2, FOV 4.47 arcmin"],
                ["Shirazi 2020 OSTI/JATIS", "IMD + IDL + MEGAlib formula, 1 nm roughness, 17-38 reflections"],
                ["DarpanX / IMD family", "transfer-matrix reflectivity provenance"],
                ["Barriere 2009 / Kohnle 1998 / PyTTE", "Laue diffraction benchmark chain"],
                ["NIST XCOM / xraydb / Henke", "attenuation and optical-constant cross-checks"],
            ])}
            """,
            "notes": "Source list for citation slide.",
        },
        {
            "tag": "File map",
            "html": f"""
            <div class='eyebrow'>repository map</div><h2>材料对应的仓库文件</h2>
            {table(["模块", "文件/目录"], [
                ["Channel report", "<span class='mono'>records/2026-05-21_channel_independent_closure.html</span>"],
                ["Channel summary", "<span class='mono'>runs/channel_independent_closure/summary.json</span>"],
                ["Laue report", "<span class='mono'>records/2026-05-20_laue_physics_confidence_audit.html</span>"],
                ["Laue summary", "<span class='mono'>runs/laue_physics_confidence_audit/summary.json</span>"],
                ["Activation", "<span class='mono'>geant4_app/src/activation_decay_focal_demo.cc</span>"],
            ])}
            """,
            "notes": "Quick repository navigation.",
        },
        {
            "tag": "Closing",
            "html": f"""
            <div class='eyebrow'>bottom line</div><h2>最终收束</h2>
            <p class='quote'>Channel 用公开 CAM511 物理复现性能量级；Laue 用 Geant4 表驱动给出独立光学路线；Geant4 的核心价值在 detector、mass 和 activation。</p>
            <div class='tagrow'>
              <span class='tag'>No correction factor</span>
              <span class='tag'>Evidence-backed</span>
              <span class='tag'>Original unpublished details named</span>
            </div>
            """,
            "notes": "Final slide.",
        },
    ]
    return slides


def write_deck(slides: list[dict[str, str]], out_path: Path) -> None:
    notes = {idx: slide.get("notes", "") for idx, slide in enumerate(slides)}
    slide_html = []
    total = len(slides)
    for idx, slide in enumerate(slides):
        active = " active" if idx == 0 else ""
        slide_html.append(
            f"""
            <div class="slide{active}" data-slide="{idx}">
              <div class="slide-content">
                {slide["html"]}
              </div>
              <div class="footer"><span>{esc(slide.get("tag", ""))}</span><span>{idx + 1} / {total}</span></div>
            </div>
            """
        )

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
      slides.forEach((s, i) => s.classList.toggle('active', i === current));
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
  <title>511 keV 两套光学模拟组会材料库</title>
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
    channel = read_json("runs/channel_independent_closure/summary.json")
    laue_audit = read_json("runs/laue_physics_confidence_audit/summary.json")
    laue_run = read_json("runs/geant4_laue_multiring_darwin/summary.json")
    activation = read_json("runs/activation/synthetic_al28_day15/focal_transport_no_neutrino/summary.json")
    detector = read_json("runs/geant4_detector_wallbywall_1k/summary.json")
    io_contract = read_json("runs/io_contract_validation_channel_wallbywall_detector_1k/summary.json")
    spot = phase_space_spot_metrics("runs/channel_wallbywall_rebuild_no_si_abs_smoke/phase_space.csv", 4.47)
    slides = build_slides(channel, laue_audit, laue_run, activation, detector, io_contract, spot)
    write_deck(slides, out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a long-form HTML slide material library for Channel and Laue optics.")
    parser.add_argument("--out", default="records/2026-05-21_two_optics_group_meeting_materials.html")
    args = parser.parse_args()
    build(ROOT / args.out)
    print(ROOT / args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
