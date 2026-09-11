#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Step04 source-model explainer HTML and conceptual WRL.

This is a documentation/visualization generator only.  It does not run Cosima
or opticsim transport.
"""

from __future__ import annotations

import csv
import html
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STEP = ROOT / "stepwise_maintenance" / "step04_opticsim"
OUT = STEP / "outputs"
HTML = STEP / "SOURCE_MODEL_EXPLAINER.html"
SVG_SKY = OUT / "source_model_sky_to_detector.svg"
SVG_FLOW = OUT / "source_model_pipeline.svg"
WRL = OUT / "source_model_smoke.wrl"
AUDIT = OUT / "source_model_explainer_audit.json"

SOURCE_CASES = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs" / "configs" / "source_cases_511_ABC.yaml"
ANCHORS = ROOT / "stepwise_maintenance" / "step07_source_cases" / "outputs" / "configs" / "literature_flux_anchors.yaml"
FLIGHT_PROFILE = ROOT / "particle_sources" / "configs" / "astro_source_cases" / "flight_profile_phase2_reference.csv"
SCIENCE_SUMMARY = ROOT / "outputs" / "reports" / "science_511_ADR_100k" / "science_511_100k_summary.json"
SCIENCE_LEDGER = ROOT / "config" / "science_511_onaxis_source" / "metadata" / "science_rate_ledger.csv"
LAUE_WRL = STEP / "outputs" / "opticsim_laue_bfull_xopmap_real" / "laue_multiring_scene.wrl"
LAUE_PNG = STEP / "outputs" / "laue_bfull_xopmap_real_2d_schematic.png"
LAUE_SUMMARY = STEP / "outputs" / "opticsim_laue_bfull_xopmap_real" / "summary.json"
AEFF_AUTHORITY = STEP / "optics_aeff_authority.json"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def read_json(path: Path) -> dict:
    return json.loads(read_text(path)) if path.exists() else {}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def file_record(path: Path) -> dict:
    return {"path": rel(path), "exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else None}


def polyline(points: list[tuple[float, float]], color: str, width: float = 3.0, dash: str | None = None) -> str:
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"{dash_attr}/>'


def write_sky_svg(path: Path, facts: dict) -> None:
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="720" viewBox="0 0 1200 720" role="img" aria-label="Sky source to detector model">
<defs>
  <marker id="arrow-blue" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#2563eb"/></marker>
  <marker id="arrow-red" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#dc2626"/></marker>
  <marker id="arrow-green" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#059669"/></marker>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#0f172a" flood-opacity="0.18"/></filter>
</defs>
<rect width="1200" height="720" fill="#f8fafc"/>
<rect x="0" y="0" width="1200" height="120" fill="#111827"/>
<text x="48" y="54" font-family="Arial, sans-serif" font-size="30" font-weight="700" fill="#ffffff">Step04 source model: sky, optics, detector</text>
<text x="48" y="88" font-family="Arial, sans-serif" font-size="16" fill="#cbd5e1">Point source is angularly narrow; diffuse source is a sky intensity map; prompt/delayed backgrounds need the optics mass model.</text>

<circle cx="145" cy="250" r="6" fill="#f97316"/>
<text x="70" y="222" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">V404 / compact point</text>
<text x="52" y="278" font-family="Arial, sans-serif" font-size="13" fill="#334155">one sky direction</text>
<text x="52" y="298" font-family="Arial, sans-serif" font-size="13" fill="#334155">optional morphology scan</text>

<ellipse cx="145" cy="455" rx="92" ry="55" fill="#bfdbfe" stroke="#2563eb" stroke-width="2" opacity="0.8"/>
<ellipse cx="145" cy="455" rx="45" ry="24" fill="#60a5fa" opacity="0.55"/>
<text x="56" y="548" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">Diffuse 511 sky</text>
<text x="52" y="574" font-family="Arial, sans-serif" font-size="13" fill="#334155">bulge/disk map over solid angle</text>

<line x1="260" y1="250" x2="500" y2="250" stroke="#2563eb" stroke-width="3" marker-end="url(#arrow-blue)"/>
<line x1="260" y1="430" x2="500" y2="320" stroke="#2563eb" stroke-width="2.5" marker-end="url(#arrow-blue)" opacity="0.75"/>
<line x1="260" y1="475" x2="500" y2="400" stroke="#2563eb" stroke-width="2.5" marker-end="url(#arrow-blue)" opacity="0.75"/>
<line x1="260" y1="520" x2="500" y2="485" stroke="#2563eb" stroke-width="2.5" marker-end="url(#arrow-blue)" opacity="0.75"/>

<g filter="url(#shadow)">
  <rect x="505" y="185" width="220" height="360" rx="8" fill="#ffffff" stroke="#cbd5e1"/>
  <circle cx="615" cy="365" r="95" fill="none" stroke="#64748b" stroke-width="14"/>
  <circle cx="615" cy="365" r="70" fill="none" stroke="#94a3b8" stroke-width="10"/>
  <circle cx="615" cy="365" r="43" fill="none" stroke="#cbd5e1" stroke-width="8"/>
  <text x="548" y="585" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">511-keV Laue lens</text>
  <text x="538" y="610" font-family="Arial, sans-serif" font-size="13" fill="#334155">crystals + mount should be in prompt/delayed models</text>
</g>

<line x1="730" y1="365" x2="970" y2="365" stroke="#059669" stroke-width="3" marker-end="url(#arrow-green)"/>
<line x1="500" y1="155" x2="740" y2="250" stroke="#dc2626" stroke-width="2.6" marker-end="url(#arrow-red)"/>
<line x1="730" y1="250" x2="985" y2="415" stroke="#dc2626" stroke-width="2.6" marker-end="url(#arrow-red)" stroke-dasharray="7 6"/>
<text x="420" y="145" font-family="Arial, sans-serif" font-size="16" font-weight="700" fill="#dc2626">prompt cosmic / atmospheric gamma</text>
<text x="750" y="245" font-family="Arial, sans-serif" font-size="13" fill="#7f1d1d">may scatter, activate, or occasionally diffract if geometry allows</text>

<g filter="url(#shadow)">
  <rect x="978" y="286" width="125" height="155" rx="8" fill="#ffffff" stroke="#cbd5e1"/>
  <rect x="1000" y="330" width="82" height="70" fill="#111827" rx="4"/>
  <rect x="1010" y="340" width="62" height="50" fill="#38bdf8" opacity="0.8"/>
  <text x="986" y="475" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">TES + BGO</text>
  <text x="968" y="500" font-family="Arial, sans-serif" font-size="13" fill="#334155">time-axis veto chain after transport</text>
</g>

<path d="M600 540 C650 615 800 610 935 500" fill="none" stroke="#f59e0b" stroke-width="3" marker-end="url(#arrow-green)" stroke-dasharray="6 5"/>
<text x="560" y="655" font-family="Arial, sans-serif" font-size="15" font-weight="700" fill="#92400e">delayed activation from lens/support mass can become local background</text>

<rect x="44" y="630" width="300" height="48" fill="#ffffff" stroke="#e2e8f0" rx="6"/>
<text x="58" y="650" font-family="Arial, sans-serif" font-size="12" fill="#334155">Local evidence: A_eff(511)={facts['A_eff_cm2']:.2f} cm2, ledger T_atm={facts['ledger_T_atm']:.3f}, T_atm profile {facts['T_atm_range_text']}</text>
<text x="58" y="668" font-family="Arial, sans-serif" font-size="12" fill="#334155">B-FULL run: {facts['n_primaries']} primaries, {facts['n_diffracted']} diffracted interactions, {facts['diffracted_focal_rows']} diffracted focal rows</text>
</svg>
'''
    path.write_text(svg, encoding="utf-8")


def write_flow_svg(path: Path) -> None:
    boxes = [
        (40, 88, "Sky model", "point / diffuse intensity"),
        (275, 88, "Atmosphere", "T_atm(E, zenith, altitude)"),
        (510, 88, "Laue optics", "Aeff, PSF, phase space"),
        (745, 88, "Cosima detector", "EventList or Be-plane beam"),
        (980, 88, "Timeline analysis", "Poisson A/B/C + veto"),
        (40, 340, "Prompt cosmic", "PARMA full-sphere source"),
        (275, 340, "Optics mass", "crystals + support in geometry"),
        (510, 340, "Activation", "delayed local decays"),
        (745, 340, "BGO veto", "time-window shield sum"),
        (980, 340, "Compton/FoV", "Be-window disk consistency"),
    ]
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="560" viewBox="0 0 1200 560">']
    svg.append('<defs><marker id="arrow" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 Z" fill="#0f172a"/></marker></defs>')
    svg.append('<rect width="1200" height="560" fill="#ffffff"/>')
    svg.append('<text x="40" y="45" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#111827">Simulation/source pipeline decision</text>')
    for x, y, title, desc in boxes:
        svg.append(f'<rect x="{x}" y="{y}" width="175" height="96" rx="8" fill="#f8fafc" stroke="#cbd5e1"/>')
        svg.append(f'<text x="{x+16}" y="{y+36}" font-family="Arial, sans-serif" font-size="18" font-weight="700" fill="#111827">{html.escape(title)}</text>')
        svg.append(f'<text x="{x+16}" y="{y+66}" font-family="Arial, sans-serif" font-size="13" fill="#475569">{html.escape(desc)}</text>')
    for x1, y1, x2, y2 in [(215,136,275,136),(450,136,510,136),(685,136,745,136),(920,136,980,136),(215,388,275,388),(450,388,510,388),(685,388,745,388),(920,388,980,388)]:
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#0f172a" stroke-width="2.5" marker-end="url(#arrow)"/>')
    svg.append('<path d="M600 184 C625 260 610 300 598 340" fill="none" stroke="#2563eb" stroke-width="2.5" marker-end="url(#arrow)"/>')
    svg.append('<path d="M362 340 C390 265 470 230 548 184" fill="none" stroke="#dc2626" stroke-width="2.5" marker-end="url(#arrow)" stroke-dasharray="7 6"/>')
    svg.append('<text x="86" y="506" font-family="Arial, sans-serif" font-size="14" fill="#334155">Decision: point/diffuse science sources fold through atmosphere + optics response; prompt/delayed backgrounds require optics mass in transport/activation geometry.</text>')
    svg.append('</svg>')
    path.write_text("\n".join(svg), encoding="utf-8")


def write_wrl(path: Path) -> None:
    def shape_line(name: str, color: tuple[float, float, float], coords: list[tuple[float, float, float]], idx: list[tuple[int, int]]) -> str:
        pts = ",\n          ".join(f"{x:.3f} {y:.3f} {z:.3f}" for x, y, z in coords)
        coord_idx = ",\n          ".join(f"{a}, {b}, -1" for a, b in idx)
        return f'''DEF {name} Shape {{
  appearance Appearance {{ material Material {{ diffuseColor {color[0]:.3f} {color[1]:.3f} {color[2]:.3f} emissiveColor {0.25*color[0]:.3f} {0.25*color[1]:.3f} {0.25*color[2]:.3f} }} }}
  geometry IndexedLineSet {{
    coord Coordinate {{ point [
          {pts}
    ] }}
    coordIndex [
          {coord_idx}
    ]
  }}
}}'''

    coords: list[tuple[float, float, float]] = []
    idx: list[tuple[int, int]] = []

    def add_line(a: tuple[float, float, float], b: tuple[float, float, float]) -> None:
        n = len(coords)
        coords.extend([a, b])
        idx.append((n, n + 1))

    # Point-source parallel rays from the sky to the lens and then to focus.
    for y in [-1.5, -0.75, 0.0, 0.75, 1.5]:
        add_line((-8, y, -8), (-2.2, y, -1.2))
        add_line((-2.2, y, -1.2), (4.5, 0.2 * y, 4.0))

    point_shape = shape_line("POINT_SOURCE_RAYS", (0.12, 0.38, 0.95), coords, idx)

    coords = []
    idx = []
    # Diffuse rays from several sky angles to different focal-plane positions.
    starts = [(-8, -3, -8), (-8, -1, -8), (-8, 1, -8), (-8, 3, -8), (-8, 0, -6)]
    stops = [(4.5, -1.4, 4.0), (4.5, -0.5, 4.0), (4.5, 0.7, 4.0), (4.5, 1.5, 4.0), (4.5, 0.0, 4.0)]
    for a, b in zip(starts, stops):
        add_line(a, (-2.0, b[1] * 0.8, -1.0))
        add_line((-2.0, b[1] * 0.8, -1.0), b)
    diffuse_shape = shape_line("DIFFUSE_SKY_RAYS", (0.12, 0.65, 0.85), coords, idx)

    coords = []
    idx = []
    # Prompt cosmic rays crossing lens mass.
    for x in [-3.2, -1.6, 0.0, 1.6, 3.2]:
        add_line((x, -4.5, -5.0), (x * 0.55, 0.0, 0.0))
        add_line((x * 0.55, 0.0, 0.0), (x * 0.25, 3.8, 4.5))
    prompt_shape = shape_line("PROMPT_COSMIC_RAYS", (0.88, 0.18, 0.14), coords, idx)

    coords = []
    idx = []
    # Local delayed photons from lens mass to detector.
    for angle in [0, 60, 120, 180, 240, 300]:
        r = 2.4
        x = r * math.cos(math.radians(angle))
        y = r * math.sin(math.radians(angle))
        add_line((x, y, 0.0), (4.5, 0.0, 4.0))
    delayed_shape = shape_line("DELAYED_LOCAL_BACKGROUND", (0.95, 0.62, 0.10), coords, idx)

    # Lens and detector guides.
    ring_coords = []
    ring_idx = []
    for radius in [2.2]:
        base = len(ring_coords)
        for i in range(24):
            a = 2.0 * math.pi * i / 24
            ring_coords.append((radius * math.cos(a), radius * math.sin(a), 0.0))
        for i in range(24):
            ring_idx.append((base + i, base + ((i + 1) % 24)))
    ring_shape = shape_line("LAUE_RING_GUIDES", (0.05, 0.45, 0.32), ring_coords, ring_idx)
    detector_shape = '''DEF DETECTOR_GUIDE Transform {
  translation 4.5 0 4.0
  children [
    Shape {
      appearance Appearance { material Material { diffuseColor 0.08 0.12 0.18 transparency 0.15 } }
      geometry Box { size 0.35 3.4 2.2 }
    }
  ]
}'''
    text = f'''#VRML V2.0 utf8
WorldInfo {{
  title "Step04 source model conceptual smoke"
  info [
    "Documentation-only WRL: no transport was run"
    "Blue=point source, cyan=diffuse sky, red=prompt cosmic, amber=delayed local background"
  ]
}}
NavigationInfo {{ type ["EXAMINE", "ANY"] }}
Viewpoint {{ position 8 -12 9 orientation 0.78 0.52 0.35 0.95 description "source model overview" }}
Background {{ skyColor [0.97 0.98 1.0] }}
{ring_shape}
{detector_shape}
{point_shape}
{diffuse_shape}
{prompt_shape}
{delayed_shape}
'''
    path.write_text(text, encoding="utf-8")


def html_page(facts: dict) -> str:
    refs = [
        ("511-CAM line-focused science and Laue-lens scale", "JATIS 2023 / arXiv:2206.14652", "https://arxiv.org/abs/2206.14652"),
        ("V404 Cyg transient positron-annihilation feature", "Siegert et al. 2016, Nature 531, 341-343 / arXiv:1603.01169", "https://arxiv.org/abs/1603.01169"),
        ("Galactic 511-keV bulge/disk/central-component flux anchors", "Siegert et al. 2016, A&A 586 A84 / arXiv:1512.00325", "https://arxiv.org/abs/1512.00325"),
        ("Laue-lens balloon precedent", "CLAIRE first light: Laue lens + active shield + balloon gondola", "https://www.sciencedirect.com/science/article/abs/pii/S1387647303003129"),
        ("Photon attenuation reference", "NIST XCOM photon cross-section database", "https://www.nist.gov/pml/xcom-photon-cross-sections-database"),
    ]
    ref_items = "\n".join(f'<li><a href="{url}">{html.escape(title)}</a><span>{html.escape(desc)}</span></li>' for title, desc, url in refs)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Step04 Source Model Explainer</title>
<style>
  :root {{
    color-scheme: light;
    --ink:#111827; --muted:#475569; --line:#cbd5e1; --panel:#f8fafc;
    --blue:#2563eb; --red:#dc2626; --green:#059669; --amber:#d97706;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family: Arial, "Noto Sans CJK SC", sans-serif; color:var(--ink); background:#ffffff; line-height:1.55; }}
  header {{ padding:32px 44px 22px; background:#111827; color:white; }}
  header h1 {{ margin:0 0 8px; font-size:32px; letter-spacing:0; }}
  header p {{ margin:0; max-width:1040px; color:#cbd5e1; font-size:16px; }}
  main {{ max-width:1180px; margin:0 auto; padding:28px 28px 56px; }}
  section {{ margin:28px 0; }}
  h2 {{ margin:0 0 12px; font-size:24px; }}
  h3 {{ margin:18px 0 8px; font-size:18px; }}
  p {{ margin:8px 0; }}
  .grid {{ display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:14px; }}
  .two {{ display:grid; grid-template-columns: 1.1fr .9fr; gap:18px; align-items:start; }}
  .card {{ border:1px solid var(--line); border-radius:8px; padding:16px; background:var(--panel); min-height:146px; }}
  .card strong {{ display:block; margin-bottom:8px; font-size:17px; }}
  .tag {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; font-weight:700; background:#e0f2fe; color:#075985; margin-right:6px; }}
  .warn {{ background:#fff7ed; border-color:#fed7aa; }}
  .ok {{ background:#ecfdf5; border-color:#bbf7d0; }}
  figure {{ margin:0; border:1px solid var(--line); border-radius:8px; overflow:hidden; background:white; }}
  figure img {{ display:block; width:100%; height:auto; }}
  figcaption {{ padding:10px 14px; color:var(--muted); font-size:13px; border-top:1px solid #e2e8f0; }}
  table {{ width:100%; border-collapse:collapse; margin-top:10px; font-size:14px; }}
  th, td {{ border:1px solid #e2e8f0; padding:8px 10px; text-align:left; vertical-align:top; }}
  th {{ background:#f1f5f9; }}
  code {{ background:#f1f5f9; padding:1px 5px; border-radius:4px; }}
  ul {{ margin-top:8px; }}
  li {{ margin:6px 0; }}
  .refs li span {{ display:block; color:var(--muted); font-size:13px; }}
  .links a {{ display:inline-block; margin:0 10px 10px 0; padding:8px 10px; border:1px solid var(--line); border-radius:6px; color:#0f172a; text-decoration:none; background:#ffffff; }}
  .decision {{ border-left:4px solid var(--green); padding:12px 14px; background:#f0fdf4; }}
  @media (max-width: 860px) {{ .grid, .two {{ grid-template-columns:1fr; }} header {{ padding:24px 20px; }} main {{ padding:20px; }} }}
</style>
</head>
<body>
<header>
  <h1>Step04 source model explainer</h1>
  <p>Purpose: answer which source classes should be simulated, what "point" and "diffuse" mean for a focused 511 keV balloon telescope, and where atmosphere, optics mass, delayed activation, and veto analysis enter.</p>
</header>
<main>
  <section class="grid">
    <div class="card ok"><strong>Current decision</strong>Use Be-window/FoV Compton veto for Step05. For Step04 source design, include the Laue lens mass in prompt and delayed-background studies before claiming a production source.</div>
    <div class="card"><strong>Point source</strong>V404 or a compact GC proxy is a sky direction. The far-field start sphere is a sampling surface, not a physical angular size.</div>
    <div class="card"><strong>Diffuse source</strong>Diffuse means a sky intensity distribution over solid angle, such as bulge/disk 511 keV emission; it is not intrinsically "random over the whole downward plane".</div>
  </section>

  <section class="two">
    <figure>
      <img src="outputs/source_model_sky_to_detector.svg" alt="source model sky to detector schematic">
      <figcaption>Conceptual source-to-detector geometry. Blue/cyan are astrophysical source classes; red/amber are instrumental backgrounds that require the optics mass model.</figcaption>
    </figure>
    <div>
      <h2>Answers to the specific questions</h2>
      <h3>1. Should the focusing-lens mass be in prompt cosmic and delayed background?</h3>
      <p>Yes. Even if the mass model is not final, the production plan should treat lens crystals, support, and nearby structures as background-producing material. Prompt cosmic rays can interact in that mass, prompt atmospheric gamma rays can scatter or occasionally satisfy diffraction geometry, and activation produced in the lens/support can later decay toward the detector.</p>
      <h3>2. Can prompt and delayed backgrounds be "focused"?</h3>
      <p>Prompt atmospheric gamma rays are not the science beam, but photons in the right energy/direction range can be affected by the same crystals. Charged particles are not focused; they create prompt hits and activation. Delayed activation is local radiation from instrument material, not a far-field sky signal, but its photons can still scatter or propagate through the optics/detector geometry.</p>
      <h3>3. Does a point source have solid-angle width on the far-field sphere?</h3>
      <p>No for the baseline point source. A distant point source is one incident direction. MEGAlib far-field or an opticsim entrance plane can spread particle start positions across an aperture for sampling, but that is not the source's angular extent. Add angular radius only for an explicit morphology scan, pointing jitter, or finite source-size test.</p>
      <h3>4. What is a diffuse source?</h3>
      <p>Diffuse source means sky brightness distributed over directions. The local config uses Galactic bulge/disk proxies. In a detector-only approximation one may sample a plane, but the physical model is an angular sky map folded through atmosphere, pointing, optics effective area, and PSF.</p>
    </div>
  </section>

  <section>
    <h2>Pipeline distinction</h2>
    <figure>
      <img src="outputs/source_model_pipeline.svg" alt="source model pipeline">
      <figcaption>The science source path and instrumental-background path should remain conceptually separate until they meet at the event/timeline analysis.</figcaption>
    </figure>
  </section>

  <section>
    <h2>Local facts used</h2>
    <table>
      <tr><th>Item</th><th>Current evidence</th><th>Interpretation</th></tr>
      <tr><td>V404 source case</td><td><code>{html.escape(rel(SOURCE_CASES))}</code></td><td>Marked as <code>transient_point_source_with_Aeff_E</code>, benchmark only.</td></tr>
      <tr><td>Old V404 implementation</td><td><code>HomogeneousBeam 0.0 0.0 127.66 ... 18.0</code></td><td>Post-optics detector beam, stale 10x convention, not a current sky-to-Laue production source.</td></tr>
      <tr><td>Science detector smoke</td><td><code>{facts['science_beam']}</code></td><td>Current detector-response authority is a Be-plane focused beam smoke, not a complete sky/Laue bridge.</td></tr>
      <tr><td>B-FULL 511-line optics</td><td>{facts['n_primaries']} primaries; {facts['n_diffracted']} diffracted interactions; {facts['diffracted_focal_rows']} diffracted focal crossings; {facts['energy_min_keV']:.0f}-{facts['energy_max_keV']:.0f} keV optical band</td><td>Current Step04/Step09 focused-photon handoff; optics hardware mass is still not in the detector geometry.</td></tr>
      <tr><td>Atmosphere</td><td>Ledger <code>T_atm={facts['ledger_T_atm']:.6g}</code>; profile <code>{html.escape(facts['T_atm_range_text'])}</code></td><td>Atmosphere is already included in rate folding, not inside the fixed-trigger Cosima source card.</td></tr>
      <tr><td>Rate formula</td><td><code>R = F_511 * A_opt * T_atm</code>, with current optics <code>A_opt(511)={facts['A_eff_cm2']:.4g} cm2</code></td><td>Science flux is normalized after transport; triggers are Monte Carlo sampling, not physical flux by themselves.</td></tr>
    </table>
  </section>

  <section class="grid">
    <div class="card"><strong>Point source baseline</strong><span class="tag">V404</span><span class="tag">compact GC proxy</span><p>Use one sky direction. Use a flux/time grid from literature. Generate optics phase space, then replay into Cosima as EventList.</p></div>
    <div class="card"><strong>Diffuse source baseline</strong><span class="tag">bulge</span><span class="tag">disk</span><p>Sample sky directions from a map or analytic morphology. Fold through atmosphere and optics response. It should not be treated as a single focal spot.</p></div>
    <div class="card warn"><strong>Prompt/delayed baseline</strong><span class="tag">mass model</span><span class="tag">activation</span><p>Add lens/support material to background geometry when the mass model is ready enough for a first smoke. Do not wait for final optimization to recognize this requirement.</p></div>
  </section>

  <section>
    <h2>Atmospheric transmission</h2>
    <p>Yes, the current workflow considers atmospheric transmission. In the existing ledger, the detector injection rate is computed as <code>F_511 * A_opt * T_atm</code>. The phase2 profile also stores time-dependent <code>T_atm_511</code> values driven by altitude and source zenith angle. The current implementation uses an attenuation-style factor and local validation checks the ledger arithmetic.</p>
    <p>For final astrophysical claims, the atmosphere should be tied to the actual flight pointing and altitude profile. For this Step04 explainer, the important decision is that atmosphere belongs in source-rate folding before the detector timeline, not as an arbitrary change to Cosima trigger count.</p>
  </section>

  <section>
    <h2>References and anchors</h2>
    <ul class="refs">
      {ref_items}
    </ul>
  </section>

  <section>
    <h2>Artifacts</h2>
    <p class="links">
      <a href="outputs/source_model_smoke.wrl">Conceptual source-model WRL smoke</a>
      <a href="outputs/opticsim_laue_bfull_xopmap_real/laue_multiring_scene.wrl">Current B-FULL XOP-map WRL</a>
      <a href="outputs/source_model_sky_to_detector.svg">Source geometry SVG</a>
      <a href="outputs/source_model_pipeline.svg">Pipeline SVG</a>
      <a href="outputs/source_model_explainer_audit.json">Audit JSON</a>
    </p>
    <div class="decision">Next production move: build a current EventList bridge from the latest opticsim phase space, then use the same source taxonomy to decide which point/diffuse cases are worth detector smoke tests.</div>
  </section>
</main>
</body>
</html>
'''


def build_facts() -> dict:
    summary = read_json(LAUE_SUMMARY)
    aeff = read_json(AEFF_AUTHORITY)
    science = read_json(SCIENCE_SUMMARY)
    ledger = read_csv(SCIENCE_LEDGER)
    profile = read_csv(FLIGHT_PROFILE)
    ledger_row = ledger[0] if ledger else {}
    tvals = [float(r["T_atm_511"]) for r in profile if r.get("T_atm_511")]
    focal = aeff.get("focal_stats", {})
    t_atm_range_text = f"{min(tvals):.6g}-{max(tvals):.6g}" if tvals else "profile not present"
    return {
        "A_eff_cm2": float(aeff.get("aeff_511_cm2") or ledger_row.get("A_opt_cm2", 50.89)),
        "ledger_T_atm": float(ledger_row.get("T_atm", 0.7390423888027)),
        "T_atm_min": min(tvals) if tvals else 0.0,
        "T_atm_max": max(tvals) if tvals else 0.0,
        "T_atm_range_text": t_atm_range_text,
        "science_beam": science.get("sim_summary", {}).get("beam_type_in_sim", "unknown"),
        "n_primaries": int(summary.get("n_primaries", 0)),
        "n_diffracted": int(summary.get("n_diffracted", 0)),
        "n_absorbed": int(summary.get("n_absorbed", 0)),
        "n_transmitted": int(summary.get("n_transmitted", 0)),
        "diffracted_focal_rows": int(summary.get("laue_diffracted_focal_crossings", 0)),
        "within_be_rows": int(focal.get("within_be_rows", 0)),
        "energy_min_keV": float(summary.get("energy_min_keV", 0)),
        "energy_max_keV": float(summary.get("energy_max_keV", 0)),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    facts = build_facts()
    write_sky_svg(SVG_SKY, facts)
    write_flow_svg(SVG_FLOW)
    write_wrl(WRL)
    HTML.write_text(html_page(facts), encoding="utf-8")
    audit = {
        "status": "PASS",
        "purpose": "Step04 source-model explainer documentation; no transport run",
        "outputs": {
            "html": file_record(HTML),
            "source_sky_svg": file_record(SVG_SKY),
            "pipeline_svg": file_record(SVG_FLOW),
            "source_model_wrl": file_record(WRL),
            "current_laue_wrl": file_record(LAUE_WRL),
            "current_laue_png": file_record(LAUE_PNG),
        },
        "inputs": {
            "source_cases": file_record(SOURCE_CASES),
            "literature_anchors": file_record(ANCHORS),
            "flight_profile": file_record(FLIGHT_PROFILE),
            "science_summary": file_record(SCIENCE_SUMMARY),
            "science_ledger": file_record(SCIENCE_LEDGER),
            "laue_summary": file_record(LAUE_SUMMARY),
        },
        "facts": facts,
        "external_references": [
            "https://arxiv.org/abs/1603.01169",
            "https://arxiv.org/abs/1512.00325",
            "https://arxiv.org/abs/2206.14652",
            "https://www.sciencedirect.com/science/article/abs/pii/S1387647303003129",
            "https://www.nist.gov/pml/xcom-photon-cross-sections-database",
        ],
    }
    AUDIT.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(HTML)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
