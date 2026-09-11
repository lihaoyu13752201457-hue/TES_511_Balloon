#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a compact pseudocode/logic packet for context-limited review."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OUT = ROOT / "reports" / "gptpro_review_packet_pseudocode"

SUMMARY = ROOT / "reports" / "day15_complete_report" / "complete_day15_summary.json"
ACCIDENTAL = ROOT / "reports" / "science_accidental_veto" / "science_accidental_veto_summary.json"
MANUSCRIPT_AUDIT = ROOT / "reports" / "day15_sci_manuscript" / "sci_manuscript_audit.json"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(WORKSPACE))
    except ValueError:
        return str(path)


def sci(value: float, nd: int = 3) -> str:
    if value == 0:
        return "0"
    exp = math.floor(math.log10(abs(value)))
    mant = value / (10**exp)
    return f"{mant:.{nd}f}e{exp}"


def tex_sci(value: float, nd: int = 3) -> str:
    if value == 0:
        return "0"
    exp = math.floor(math.log10(abs(value)))
    mant = value / (10**exp)
    return rf"{mant:.{nd}f}\times10^{{{exp}}}"


def write_markdown(summary: dict, acc: dict, manuscript: dict, audit: dict) -> Path:
    norm = summary["normalization"]
    rates = summary["timeline_rates_cps"]
    direct = summary["expectation_rates_cps"]
    sci_sens = summary["science_sensitivity"]
    broad_corr = acc["windows"]["broad_480_550"]["accidental_survival_correction"]
    line_corr = acc["windows"]["line_510p3_511p8"]["accidental_survival_correction"]
    broad_corr_3 = manuscript["broad_480_550"]["flux_3sigma_1Ms"] / broad_corr
    line_corr_3 = manuscript["line_window_510p3_511p8"]["flux_3sigma_1Ms"] / line_corr

    md = f"""# COSMOSRAY_BG_2605 伪代码逻辑版审阅包

这是给上下文受限模型阅读的简化版。它不摘录完整 Python/MEGAlib 代码，只保留执行逻辑、输入输出、判断条件、关键公式和最终数值。完整代码审计见 `reports/gptpro_review_packet_full_detail/`。

## 0. 当前结论

- Day-15 common timeline: raw `{rates['raw']:.6f}` cps, BGO 后 `{rates['bgo']:.6f}` cps, final `{rates['final']:.6f}` cps.
- Direct expectation cross-check final: `{direct['final']:.6f}` cps.
- Science flux reference: `{norm['science_flux_ph_cm2_s']:.1e}` ph cm^-2 s^-1.
- Science final response: `{sci_sens['science_final_response_cps_per_ph_cm-2_s-1']:.6f}` cps/(ph cm^-2 s^-1).
- Accidental survival correction: broad `{broad_corr:.6f}`, line `{line_corr:.6f}`.
- Corrected 1 Ms 3 sigma limits: broad `{sci(broad_corr_3)}`, line `{sci(line_corr_3)}` ph cm^-2 s^-1.

## 1. 总工作流伪代码

```text
main_workflow():
    read memory.md and workflow.md
    build full-sphere atmospheric particle sources
    run prompt instant Cosima production
    run activation buildup Cosima production
    parse buildup RPIP isotope-production records
    build day-15 delayed decay source
    apply W183/W180 ground-state correction
    run fixed delayed decay Cosima production
    run focused 511-keV science source Cosima production
    parse prompt, delayed, science SIM files into one event catalog
    draw Poisson common timeline for all streams
    merge events within 1 microsecond coincidence windows
    apply energy window, BGO veto, and Compton/FoV veto
    compute direct-expectation cross-check spectra
    estimate science accidental-veto loss by bootstrap
    compute corrected source sensitivity
    write PDF/CSV/JSON reports
```

## 2. 源和几何逻辑

```text
geometry_model():
    load TibetTES_v5_6layers.geo.setup
    include main mass model TibetTES_v5_6layers.geo
    include detector mapping TibetTES_v5_6layers.det
    sensitive TES volumes = TES_Pixel_L0 ... TES_Pixel_L5
    active shield volume = BGO_Shield
    science photons enter just outside Be window
    BGO veto uses actual BGO energy deposit, not source labels
```

```text
atmospheric_sources():
    particles = gamma, neutron, proton, alpha, e-, e+, mu-, mu+
    for each particle:
        read 20-bin EXPACS/PARMA spectrum in 2602-compatible units
        create 20 FarFieldAreaSource components
        assign MEGAlib ParticleType mapping
        set flux per angular bin
    output megalib_sources_fullsphere20/*.source
```

## 3. prompt / buildup 运行逻辑

```text
run_equiv2602_pipeline(mode):
    if mode == instant:
        disable activation buildup output
        output prompt SIM files
    if mode == buildup:
        enable isotope-production recording
        output SIM and DAT/RPIP records

    gamma_events = 10,000,000 split into 4 jobs
    for each non-gamma particle:
        events_per_replica = flux-matched count
        replicas = 8

    for each job:
        copy base source
        patch triggers
        patch unique deterministic seed
        run cosima
        parse log for generated particles, CPU, observation time
        store SIM/DAT/log path in manifest
```

## 4. buildup 到 delayed source 逻辑

```text
build_delayed_source():
    scan buildup SIM/DAT files
    for each isotope-production record:
        read volume name, ZA, excitation, position, production weight
        canonicalize volume names
        group by volume, isotope, excitation, z-bin
    for each group:
        build radial profile in local geometry coordinates
        resolve half-life from local NUBASE/cache
        compute day-15 activity
        emit Cosima RadialProfileBeam source block
    output activation_decay_day15.source
```

Activity model:

```text
lambda = ln(2) / half_life
production_rate = weighted_productions / prompt_equivalent_time
activity_at_day15 = production_rate * (1 - exp(-lambda * irradiation_time))
expected_decays_in_observation = activity_at_day15/lambda * (1 - exp(-lambda * observation_time))
```

## 5. W183/W180 修正逻辑

```text
fix_ground_state_source():
    read activation_decay_day15.source
    for each source block:
        parse source_name, volume, ZA, flux
        look up ground-state half-life in NUBASE
        if ground state is stable or effectively zero activity:
            remove source block
        else:
            rescale flux using ground-state half-life
    assert ParticleType 74183 and 74180 are absent from fixed source
    output activation_decay_day15_groundstate_fixed.source
```

Key result:

```text
old_total_activity = 1592.263662520241 Bq
new_total_activity = 823.9513812643273 Bq
source_blocks = 5276 -> 5156
W183/W180 residual = false / false
```

## 6. science 511 源逻辑

```text
science_source():
    physical source flux F511 is outside Cosima
    optics effective area A_opt = 50.89 cm^2
    atmosphere transmission T_atm = 0.7390423888027
    injection_rate = F511 * A_opt * T_atm
    Cosima receives post-optics photons only
    source = 511 keV monoenergetic HomogeneousBeam
    beam z = 127.66 in XZTES geometry units
    beam radius = 18.0 geometry units
    direction = toward -z through Be window
    triggers = 100,000
```

For F511 = 1e-4 ph cm^-2 s^-1:

```text
injection_rate = 0.0037609867166169403 s^-1
science final response = {sci_sens['science_final_response_cps_per_ph_cm-2_s-1']} cps/(ph cm^-2 s^-1)
```

## 7. SIM catalog 解析逻辑

```text
parse_sim_catalog(file, stream):
    for each event in .sim.gz:
        collect TES pixel hits:
            layer, pixel_id, energy_keV
        collect BGO energy deposits
        event.tes_total = sum(TES pixel energies)
        event.bgo_total = sum(BGO energies)
        event.rate_hz = stream-specific rate weight
        keep event if it has useful detector information
    return event catalog arrays
```

Rate assignment:

```text
prompt event rate = prompt MC event weight from full-sphere normalization
delayed event rate = 1 / delayed observation time per generated decay
science event rate = science injection rate / generated science triggers
```

## 8. Poisson common timeline 逻辑

```text
draw_timeline(catalog, Tobs):
    for stream in prompt, delayed, science:
        R = sum(event.rate_hz for events in stream)
        N = Poisson(R * Tobs)
        draw N event indices with probability proportional to event.rate_hz
        assign each drawn event a uniform random time in [0, Tobs]
    concatenate all streams
    sort by event time
```

Actual draw:

```text
Tobs = 1094.2 s
prompt:  lambda=16608414.476865074, drawn=16607480
delayed: lambda=579542.0, drawn=579119
science: lambda=3.87510441093405, drawn=5
```

## 9. candidate merge 和 VETO 逻辑

```text
analyze_timeline(sorted_events):
    start new candidate with first event
    for each next event:
        if next.time - previous.time <= 1e-6 s:
            add it to current candidate
        else:
            close current candidate
            start next candidate

    for each candidate:
        tes_hits = all TES hits in candidate
        bgo_total = sum(BGO deposits in candidate)
        e_tes = sum(TES energies in candidate)

        if e_tes not in selected energy window:
            reject from this spectrum
        else:
            raw_count += 1

        if bgo_total >= 50 keV:
            reject as BGO veto
        else:
            bgo_count += 1

        if classify_compton_fov(tes_hits) says veto:
            reject as Compton/FoV veto
        else:
            final_count += 1
```

Compton/FoV policy:

```text
if single-site event:
    keep
elif multi-site geometry is compatible with focused source:
    keep
elif geometry is clearly outside allowed Compton/FoV:
    veto
else:
    keep  # reject_policy = keep, conservative for background
```

## 10. direct expectation cross-check

```text
direct_expectation(catalog):
    for each event independently:
        weight = event.rate_hz
        fill raw spectrum if TES energy is in bin
        fill BGO spectrum if bgo_total < 50 keV
        fill final spectrum if BGO pass and Compton/FoV pass
    compare with Poisson timeline spectrum
```

Interpretation:

```text
direct expectation = smooth Asimov expectation without random timeline noise
common timeline = one finite realization with accidental prompt/delayed/science coincidences
```

## 11. science accidental-veto 校正逻辑

```text
estimate_science_accidental_veto():
    precompute isolated science events after normal cuts
    background_rate = prompt_rate + delayed_rate
    for trial in 1..1,000,000:
        draw one science event from science catalog
        draw accidental background cluster around it using Poisson timing model
        merge science + accidental background hits
        rerun energy window, BGO veto, Compton/FoV veto
        if isolated science passed but merged candidate fails:
            count as accidental loss
    survival_correction = 1 - loss_fraction
```

Results:

```text
background_total_rate = 15708.240245718402 Hz
P(any accidental background in window) = 0.030928110518078866
broad loss fraction = 0.016424716658774347
line loss fraction  = 0.01642586249337667
dominant loss cause = BGO accidental trigger
```

## 12. sensitivity 逻辑

```text
compute_flux_threshold(window):
    B = final background rate in window
    R = final science response per unit flux
    c = accidental survival correction
    R_corrected = R * c
    F_nsigma = n * sqrt(B * T) / (R_corrected * T)
```

For 1 Ms:

```text
480-550 keV:
    uncorrected 3 sigma = {sci(manuscript['broad_480_550']['flux_3sigma_1Ms'])}
    corrected   3 sigma = {sci(broad_corr_3)}
510.3-511.8 keV:
    uncorrected 3 sigma = {sci(manuscript['line_window_510p3_511p8']['flux_3sigma_1Ms'])}
    corrected   3 sigma = {sci(line_corr_3)}
```

## 13. 当前剩余风险

```text
known_limits():
    science optics is a simplified post-optics focused-beam model
    accidental-veto correction is catalog/bootstrap-level, not new mixed Cosima transport
    sensitivity is window-counting, not a full spatial-spectral likelihood
    delayed residual near 511 keV still deserves W187/decay-chain diagnosis
    prompt lightcurve wrapper is infrastructure; current shape values are effectively constant
```

## 14. 最小审阅路径

如果 GPT Pro 只能读少量内容，优先读：

1. 本文件的第 1、8、9、11、12 节。
2. `gptpro_pseudocode_packet_audit.json` 的数值。
3. 如需追溯真实代码，再读 full-detail PDF 或对应脚本。
"""
    path = OUT / "cosmosray_bg_2605_gptpro_pseudocode_packet.md"
    path.write_text(md, encoding="utf-8")
    return path


def latex_block(title: str, text: str) -> str:
    return rf"""
\subsection*{{{title}}}
\begin{{lstlisting}}
{text.rstrip()}
\end{{lstlisting}}
"""


def write_latex(summary: dict, acc: dict, manuscript: dict, audit: dict, md_path: Path) -> Path:
    norm = summary["normalization"]
    rates = summary["timeline_rates_cps"]
    direct = summary["expectation_rates_cps"]
    sci_sens = summary["science_sensitivity"]
    draw = summary["draw_summary"]
    broad_corr = acc["windows"]["broad_480_550"]["accidental_survival_correction"]
    line_corr = acc["windows"]["line_510p3_511p8"]["accidental_survival_correction"]
    broad_corr_3 = manuscript["broad_480_550"]["flux_3sigma_1Ms"] / broad_corr
    line_corr_3 = manuscript["line_window_510p3_511p8"]["flux_3sigma_1Ms"] / line_corr

    blocks = [
        latex_block(
            "总工作流",
            """main_workflow():
    read memory.md and workflow.md
    build full-sphere atmospheric particle sources
    run prompt instant Cosima production
    run activation buildup Cosima production
    parse buildup RPIP isotope-production records
    build day-15 delayed decay source
    apply W183/W180 ground-state correction
    run fixed delayed decay Cosima production
    run focused 511-keV science source Cosima production
    parse prompt, delayed, science SIM files into one event catalog
    draw Poisson common timeline for all streams
    merge events within 1 microsecond coincidence windows
    apply energy window, BGO veto, and Compton/FoV veto
    estimate science accidental-veto loss
    compute corrected source sensitivity""",
        ),
        latex_block(
            "源和几何",
            """geometry_model():
    load TibetTES_v5_6layers.geo.setup
    sensitive TES volumes = TES_Pixel_L0 ... TES_Pixel_L5
    active shield volume = BGO_Shield
    science photons enter just outside Be window
    BGO veto uses actual BGO energy deposit

atmospheric_sources():
    for particle in gamma,n,p,alpha,e-,e+,mu-,mu+:
        read 20-bin 2602-compatible EXPACS/PARMA spectrum
        create 20 FarFieldAreaSource components
        assign MEGAlib ParticleType and flux""",
        ),
        latex_block(
            "prompt / buildup",
            """run_equiv2602_pipeline(mode):
    gamma_events = 10,000,000 split into 4 jobs
    non_gamma_replicas = 8
    for each job:
        patch trigger count
        patch unique deterministic seed
        run cosima
        parse generated particles, CPU, observation time
    if mode == instant: output prompt SIM
    if mode == buildup: output SIM + isotope-production records""",
        ),
        latex_block(
            "delayed source 与 W183/W180 修正",
            """build_delayed_source():
    parse CC IP RP records from buildup
    group by volume, isotope, excitation, z-bin
    build radial profile for each group
    resolve half-life
    compute day-15 activity
    emit RadialProfileBeam source blocks

fix_ground_state_source():
    for each source block:
        look up NUBASE ground-state half-life
        if stable or effectively zero activity: remove block
        else: rescale flux
    assert W183/W180 source blocks are absent""",
        ),
        latex_block(
            "science 511 源",
            f"""science_source():
    F511 = {norm['science_flux_ph_cm2_s']:.1e} ph cm^-2 s^-1
    A_opt = 50.89 cm^2
    T_atm = 0.7390423888027
    injection_rate = F511 * A_opt * T_atm
                   = {norm['science_injection_rate_s^-1']:.12g} s^-1
    Cosima source = 511 keV monoenergetic HomogeneousBeam
    beam z = 127.66 in XZTES geometry units
    beam radius = 18.0 geometry units
    direction = -z through Be window
    generated triggers = 100,000""",
        ),
        latex_block(
            "SIM catalog",
            """parse_sim_catalog(file, stream):
    for each event:
        sum TES pixel hits -> tes_total
        sum BGO deposits   -> bgo_total
        assign event rate_hz from stream normalization
        store stream, tag, file, local_id, hits, totals, rate

rate rules:
    prompt  = full-sphere source normalization
    delayed = generated decays / delayed observation time
    science = science injection rate / generated science triggers""",
        ),
        latex_block(
            "Poisson 时间轴",
            f"""draw_timeline(catalog, Tobs={norm['obs_time_s']}):
    for stream in prompt, delayed, science:
        R = sum(rate_hz for stream events)
        N = Poisson(R*Tobs)
        draw N event IDs with probability proportional to rate_hz
        draw N uniform timestamps in [0,Tobs]
    sort all drawn events by time

actual draw:
    prompt  lambda={draw['prompt']['lambda']:.6f}, drawn={draw['prompt']['drawn']}
    delayed lambda={draw['delayed']['lambda']:.6f}, drawn={draw['delayed']['drawn']}
    science lambda={draw['science']['lambda']:.6f}, drawn={draw['science']['drawn']}""",
        ),
        latex_block(
            "candidate merge + VETO",
            """analyze_timeline(sorted_events):
    merge adjacent events when delta_t <= 1e-6 s
    for each candidate:
        e_tes = sum TES energy
        e_bgo = sum BGO energy
        if e_tes in analysis window: raw += 1
        if e_bgo < 50 keV: bgo += 1
        if Compton/FoV classification passes: final += 1

classify_compton_fov(hits):
    if single-site: keep
    if multi-site compatible with focused-source geometry: keep
    if clearly outside allowed geometry: veto
    otherwise: keep  # reject_policy = keep""",
        ),
        latex_block(
            "science accidental-veto",
            """estimate_science_accidental_veto():
    precompute isolated science pass/fail
    for trial in 1..1,000,000:
        draw one science event
        draw accidental background cluster around it
        merge science + background hits
        rerun energy, BGO, Compton/FoV cuts
        if isolated passed but merged failed:
            count accidental loss
    survival = 1 - loss_fraction""",
        ),
        latex_block(
            "灵敏度",
            """compute_flux_threshold(B, R, c, T, n):
    R_corrected = R * c
    F_nsigma = n * sqrt(B*T) / (R_corrected*T)

where:
    B = final background rate
    R = science response per unit flux
    c = accidental survival correction
    T = exposure time""",
        ),
    ]

    tex = rf"""
\documentclass[11pt,a4paper]{{ctexart}}
\usepackage[a4paper,margin=1.75cm]{{geometry}}
\usepackage{{fontspec,booktabs,longtable,xurl,hyperref,listings,xcolor}}
\setCJKmainfont{{Noto Serif CJK SC}}
\setmainfont{{TeX Gyre Termes}}
\hypersetup{{colorlinks=true,linkcolor=blue!50!black,urlcolor=blue!50!black}}
\lstset{{basicstyle=\ttfamily\small,breaklines=true,frame=single,columns=fullflexible,keepspaces=true}}
\title{{COSMOSRAY\_BG\_2605 伪代码逻辑版审阅包}}
\author{{Codex TES 511 simulation audit}}
\date{{2026-05-12}}
\begin{{document}}
\maketitle

\section*{{定位}}
这是给上下文受限模型阅读的简化版。它不摘录完整真实代码，只保留执行逻辑、输入输出、判断条件、关键公式和最终数值。完整代码审计见 \path{{cosmosray_bg_2605/reports/gptpro_review_packet_full_detail/cosmosray_bg_2605_gptpro_full_detail_packet.pdf}}。Markdown 版在 \path{{{rel(md_path)}}}。

\section*{{核心数值}}
\begin{{longtable}}{{ll}}
\toprule
项目 & 数值 \\
\midrule
480--550 keV raw timeline rate & {rates['raw']:.6f} cps \\
480--550 keV BGO 后 timeline rate & {rates['bgo']:.6f} cps \\
480--550 keV final timeline rate & {rates['final']:.6f} cps \\
Direct expectation final rate & {direct['final']:.6f} cps \\
Science reference flux & {norm['science_flux_ph_cm2_s']:.1e} ph cm$^{{-2}}$ s$^{{-1}}$ \\
Science final response & {sci_sens['science_final_response_cps_per_ph_cm-2_s-1']:.6f} cps/(ph cm$^{{-2}}$ s$^{{-1}}$) \\
Broad accidental survival correction & {broad_corr:.6f} \\
Line accidental survival correction & {line_corr:.6f} \\
Corrected broad 1 Ms 3$\sigma$ limit & ${tex_sci(broad_corr_3)}$ ph cm$^{{-2}}$ s$^{{-1}}$ \\
Corrected line 1 Ms 3$\sigma$ limit & ${tex_sci(line_corr_3)}$ ph cm$^{{-2}}$ s$^{{-1}}$ \\
\bottomrule
\end{{longtable}}

\section*{{伪代码}}
{''.join(blocks)}

\section*{{最小审阅路径}}
如果只能读很少内容，优先读本 PDF 的核心数值、Poisson 时间轴、candidate merge + VETO、science accidental-veto 和灵敏度部分。需要真实代码时再打开 full-detail PDF。

\section*{{产物}}
\begin{{itemize}}
\item PDF: \path{{{rel(OUT / "cosmosray_bg_2605_gptpro_pseudocode_packet.pdf")}}}
\item Markdown: \path{{{rel(md_path)}}}
\item Audit JSON: \path{{{rel(OUT / "gptpro_pseudocode_packet_audit.json")}}}
\end{{itemize}}

\end{{document}}
"""
    path = OUT / "cosmosray_bg_2605_gptpro_pseudocode_packet.tex"
    path.write_text(tex, encoding="utf-8")
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summary = load_json(SUMMARY)
    acc = load_json(ACCIDENTAL)
    manuscript = load_json(MANUSCRIPT_AUDIT)

    broad_corr = acc["windows"]["broad_480_550"]["accidental_survival_correction"]
    line_corr = acc["windows"]["line_510p3_511p8"]["accidental_survival_correction"]
    broad_corr_3 = manuscript["broad_480_550"]["flux_3sigma_1Ms"] / broad_corr
    line_corr_3 = manuscript["line_window_510p3_511p8"]["flux_3sigma_1Ms"] / line_corr
    audit = {
        "pdf": rel(OUT / "cosmosray_bg_2605_gptpro_pseudocode_packet.pdf"),
        "markdown": rel(OUT / "cosmosray_bg_2605_gptpro_pseudocode_packet.md"),
        "source_summary": rel(SUMMARY),
        "source_accidental": rel(ACCIDENTAL),
        "purpose": "context-limited pseudocode/logic version; no full code excerpts",
        "timeline_final_480_550_cps": summary["timeline_rates_cps"]["final"],
        "direct_expectation_final_480_550_cps": summary["expectation_rates_cps"]["final"],
        "broad_survival_correction": broad_corr,
        "line_survival_correction": line_corr,
        "broad_3sigma_1Ms_corrected": broad_corr_3,
        "line_3sigma_1Ms_corrected": line_corr_3,
    }
    md_path = write_markdown(summary, acc, manuscript, audit)
    tex_path = write_latex(summary, acc, manuscript, audit, md_path)
    (OUT / "gptpro_pseudocode_packet_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for _ in range(2):
        subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=OUT,
            check=True,
        )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
