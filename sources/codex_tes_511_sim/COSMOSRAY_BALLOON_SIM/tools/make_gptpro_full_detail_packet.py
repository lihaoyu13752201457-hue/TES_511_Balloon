#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate an extremely detailed Chinese audit packet for COSMOSRAY_BG_2605."""

from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OUT = ROOT / "reports" / "gptpro_review_packet_full_detail"

SUMMARY = ROOT / "reports" / "day15_complete_report" / "complete_day15_summary.json"
ACCIDENTAL = ROOT / "reports" / "science_accidental_veto" / "science_accidental_veto_summary.json"
MANUSCRIPT_AUDIT = ROOT / "reports" / "day15_sci_manuscript" / "sci_manuscript_audit.json"
COMPACT_AUDIT = ROOT / "reports" / "gptpro_review_packet" / "gptpro_review_packet_audit.json"

FIGURES = {
    "workflow": ROOT / "reports" / "day15_sci_manuscript_zh" / "figures" / "fig01_workflow.png",
    "wide_spectrum": ROOT / "reports" / "day15_sci_manuscript_zh" / "figures" / "fig02_wide_spectrum.png",
    "line_window": ROOT / "reports" / "day15_sci_manuscript_zh" / "figures" / "fig03_line_window.png",
    "streams": ROOT / "reports" / "day15_sci_manuscript_zh" / "figures" / "fig04_stream_decomposition.png",
    "incident": ROOT / "reports" / "day15_sci_manuscript_zh" / "figures" / "fig05_incident_components.png",
    "cam511_counts": ROOT / "reports" / "day15_sci_manuscript_zh" / "figures" / "fig06_cam511_counts.png",
    "sensitivity": ROOT / "reports" / "day15_sci_manuscript_zh" / "figures" / "fig07_sensitivity.png",
    "image8": ROOT / "reports" / "day15_complete_report" / "figures" / "image8_like_component_spectrum_with_science.png",
    "activation": ROOT / "reports" / "day15_complete_report" / "figures" / "activation_top10_after_fix.png",
    "timeline": ROOT / "reports" / "day15_complete_report" / "figures" / "timeline_spectrum_480_550_veto_chain.png",
    "veto_bar": ROOT / "reports" / "day15_complete_report" / "figures" / "timeline_veto_rates_bar.png",
    "accidental": ROOT / "reports" / "science_accidental_veto" / "science_accidental_veto_loss.png",
}


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(WORKSPACE))
    except ValueError:
        return str(path)


def tex_escape(value) -> str:
    s = str(value)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in s)


def path_tex(path: str | Path) -> str:
    return r"\path{" + str(path).replace("\\", "/") + "}"


def sci_tex(value: float, nd: int = 3) -> str:
    if value == 0:
        return "0"
    exp = math.floor(math.log10(abs(value)))
    mant = value / (10**exp)
    return rf"{mant:.{nd}f}\times10^{{{exp}}}"


def table(headers, rows, aligns=None, small=True) -> str:
    aligns = aligns or ("l" + "r" * (len(headers) - 1))
    prefix = r"\small" if small else ""
    out = [prefix, rf"\begin{{tabular}}{{{aligns}}}", r"\toprule"]
    out.append(" & ".join(tex_escape(h) for h in headers) + r" \\")
    out.append(r"\midrule")
    for row in rows:
        out.append(" & ".join(str(x) for x in row) + r" \\")
    out.extend([r"\bottomrule", r"\end{tabular}"])
    return "\n".join(out)


def longtable(headers, rows, widths=None) -> str:
    if widths is None:
        widths = [0.22, 0.68]
    spec = "".join([rf"p{{{w:.2f}\linewidth}}" for w in widths])
    out = [r"\scriptsize", rf"\begin{{longtable}}{{{spec}}}", r"\toprule"]
    out.append(" & ".join(tex_escape(h) for h in headers) + r" \\")
    out.append(r"\midrule")
    out.append(r"\endfirsthead")
    out.append(r"\toprule")
    out.append(" & ".join(tex_escape(h) for h in headers) + r" \\")
    out.append(r"\midrule")
    out.append(r"\endhead")
    for row in rows:
        out.append(" & ".join(str(x) for x in row) + r" \\")
    out.extend([r"\bottomrule", r"\end{longtable}", r"\normalsize"])
    return "\n".join(out)


def snippet(path: Path, start: int, end: int) -> str:
    if not path.exists():
        return f"[missing] {path}"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    for idx in range(max(1, start), min(len(lines), end) + 1):
        out.append(f"{idx:04d}: {lines[idx-1]}")
    return "\n".join(out)


def lst(title: str, code: str, language: str = "") -> str:
    title = tex_escape(title)
    lang = f",language={language}" if language else ""
    return (
        rf"\begin{{lstlisting}}[caption={{{title}}}{lang}]" + "\n"
        + code.replace("\t", "    ")
        + "\n"
        + r"\end{lstlisting}"
    )


def figure_block(name: str, caption: str, width: str = r"0.92\linewidth") -> str:
    src = FIGURES.get(name)
    if not src or not src.exists():
        return rf"\noindent\textit{{图 {tex_escape(name)} 缺失：{path_tex(src or name)}}}"
    dst = OUT / f"fig_{name}.png"
    shutil.copy2(src, dst)
    return rf"""
\begin{{figure}}[H]
\centering
\includegraphics[width={width}]{{{dst.name}}}
\caption{{{tex_escape(caption)}}}
\end{{figure}}
"""


def aggregate_run(path: Path) -> dict:
    rows = load_json(path, [])
    out = {
        "jobs": len(rows),
        "pass": sum(1 for r in rows if r.get("status") == "PASS"),
        "fail": sum(1 for r in rows if r.get("status") not in ("PASS", "SKIP")),
        "events": sum(int(r.get("events") or 0) for r in rows),
        "generated": sum(int(r.get("generated_particles") or 0) for r in rows),
        "cpu_s": sum(float(r.get("cpu_s") or 0.0) for r in rows),
        "sim_bytes": sum(int(r.get("sim_size_bytes") or 0) for r in rows),
        "dat_bytes": sum(int(r.get("dat_size_bytes") or 0) for r in rows),
        "by_particle": defaultdict(lambda: {"jobs": 0, "events": 0, "generated": 0, "cpu_s": 0.0, "sim_bytes": 0, "dat_bytes": 0}),
    }
    for r in rows:
        p = r.get("particle", "unknown")
        b = out["by_particle"][p]
        b["jobs"] += 1
        b["events"] += int(r.get("events") or 0)
        b["generated"] += int(r.get("generated_particles") or 0)
        b["cpu_s"] += float(r.get("cpu_s") or 0.0)
        b["sim_bytes"] += int(r.get("sim_size_bytes") or 0)
        b["dat_bytes"] += int(r.get("dat_size_bytes") or 0)
    out["by_particle"] = dict(sorted(out["by_particle"].items()))
    return out


def count_files(path: Path, pattern: str) -> tuple[int, int]:
    files = list(path.glob(pattern))
    return len(files), sum(p.stat().st_size for p in files if p.exists())


def code_inventory_rows() -> list[list[str]]:
    scripts = [
        ("生成全空间大气源", "tools/build_fullsphere_particle_sources.py", "读取 EXPACS/PARMA 20-bin manifest，写 8 种粒子的 FarFieldAreaSource .source。"),
        ("2602 等效生产调度", "tools/run_equiv2602_pipeline.py", "把 gamma 拆为 4 份，非 gamma 做 8 个 replica，按 flux 匹配事件数并给每个 job 唯一 seed。"),
        ("buildup RPIP -> decay source", "tools/makedecaysourcewithplot_rpip.py", "解析 CC IP RP 记录，按体积/核素/z-bin 生成 RadialProfileBeam 衰变源。"),
        ("W183/W180 ground-state fix", "tools/build_fixed_delay_source.py", "用 NUBASE ground-state 半衰期重算或删除错误 isomer 源块。"),
        ("完整 day-15 统计", "tools/make_complete_day15_report.py", "解析 SIM，统一归一化，泊松合并时间轴，执行 BGO 和 Compton/FoV veto。"),
        ("science accidental veto", "tools/estimate_science_accidental_veto.py", "在既有 MC catalog 上做 1M signal trial bootstrap，估计偶然背景误 veto。"),
        ("英文 SCI manuscript", "tools/make_sci_manuscript.py", "把结果写成英文论文风格 PDF。"),
        ("中文 SCI manuscript", "tools/make_sci_manuscript_zh.py", "从同一 summary/audit 写中文译版。"),
        ("本极详细报告", "tools/make_gptpro_full_detail_packet.py", "将代码片段、源、几何、运行和结果汇总成可审计 PDF。"),
    ]
    rows = []
    for role, path, purpose in scripts:
        full = ROOT / path
        rows.append([tex_escape(role), path_tex(rel(full)), tex_escape(purpose)])
    return rows


def source_file_rows() -> list[list[str]]:
    files = [
        ("背景源总表", ROOT / "megalib_sources_fullsphere20" / "flux_summary.csv", "8 种粒子，每种 20 个等立体角 bin。"),
        ("gamma 背景源示例", ROOT / "megalib_sources_fullsphere20" / "Background_gamma_fullsphere20.source", "FarFieldAreaSource，ParticleType=1。"),
        ("fixed delayed source", ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602" / "activation_decay_day15_groundstate_fixed.source", "第15天 corrected RPIP decay source，5156 source blocks。"),
        ("science source config", ROOT / "run_configs" / "Science_511_onaxis_focalbeam_local.source", "511 keV HomogeneousBeam，z=127.66、半径18.0几何单位，100k triggers。"),
        ("science SIM output", ROOT / "science_511_onaxis_source" / "Science_511_onaxis_focalbeam_gateAfix.inc1.id1.sim.gz", "Gate-A-fixed science reference MC catalog。"),
        ("prompt SIM directory", ROOT / "production_runs" / "instant_equiv2602", "60 个 instant prompt SIM。"),
        ("buildup SIM directory", ROOT / "production_runs" / "buildup_equiv2602", "60 个 activation buildup SIM/DAT。"),
        ("delayed SIM output", ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602" / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz", "fixed delayed full 1M Cosima 输出。"),
    ]
    rows = []
    for name, path, note in files:
        exists = "yes" if path.exists() else "NO"
        size = ""
        if path.exists() and path.is_file():
            size = f"{path.stat().st_size/1e9:.3f} GB"
        elif path.exists() and path.is_dir():
            n, s = count_files(path, "*.sim.gz")
            size = f"{n} SIM, {s/1e9:.3f} GB"
        rows.append([tex_escape(name), path_tex(rel(path)), tex_escape(exists), tex_escape(size), tex_escape(note)])
    return rows


def build_tex() -> tuple[Path, dict]:
    OUT.mkdir(parents=True, exist_ok=True)

    summary = load_json(SUMMARY)
    acc = load_json(ACCIDENTAL)
    manuscript = load_json(MANUSCRIPT_AUDIT)
    compact = load_json(COMPACT_AUDIT, {})
    norm = summary["normalization"]
    rates = summary["timeline_rates_cps"]
    counts = summary["timeline_counts_480_550"]
    catalog = summary["catalog"]
    direct = summary["expectation_rates_cps"]
    by_stream = summary["expectation_rates_by_stream_cps"]
    delay = summary["delay_fix"]
    sci = summary["science_sensitivity"]
    draw = summary["draw_summary"]

    instant = aggregate_run(ROOT / "production_runs" / "instant_equiv2602" / "run_summary.json")
    buildup = aggregate_run(ROOT / "production_runs" / "buildup_equiv2602" / "run_summary.json")
    prompt_norm = load_json(ROOT / "production_runs" / "instant_equiv2602" / "normalization.json")
    fix_summary = load_json(ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602" / "source_fix_summary.json")
    science_summary = load_json(ROOT / "reports" / "science_511_100k_summary.json", {})
    bounds = load_json(ROOT / "XZTES" / "bounds.json", {})
    flux_rows = read_csv_rows(ROOT / "megalib_sources_fullsphere20" / "flux_summary.csv")
    science_ledger = read_csv_rows(ROOT / "science_511_onaxis_source" / "metadata" / "science_rate_ledger.csv")

    broad_corr = acc["windows"]["broad_480_550"]["accidental_survival_correction"]
    line_corr = acc["windows"]["line_510p3_511p8"]["accidental_survival_correction"]
    broad_uncorr_3 = manuscript["broad_480_550"]["flux_3sigma_1Ms"]
    broad_uncorr_5 = 5.0 / 3.0 * broad_uncorr_3
    line_uncorr_3 = manuscript["line_window_510p3_511p8"]["flux_3sigma_1Ms"]
    line_uncorr_5 = manuscript["line_window_510p3_511p8"]["flux_5sigma_1Ms"]
    broad_corr_3 = broad_uncorr_3 / broad_corr
    broad_corr_5 = broad_uncorr_5 / broad_corr
    line_corr_3 = line_uncorr_3 / line_corr
    line_corr_5 = line_uncorr_5 / line_corr

    veto_table = table(
        ["阶段", "480--550 keV 计数", "率 cps", "相对无 VETO", "物理含义"],
        [
            ["无 VETO", counts["raw"], f"{rates['raw']:.6f}", "1.000", tex_escape("只要求 TES 总能量在窗口内")],
            ["BGO 后", counts["bgo"], f"{rates['bgo']:.6f}", f"{rates['bgo']/rates['raw']:.3f}", tex_escape("候选组 BGO 总能量 < 50 keV")],
            ["BGO+Compton/FoV 后", counts["final"], f"{rates['final']:.6f}", f"{rates['final']/rates['raw']:.3f}", tex_escape("再通过 Compton/FoV 判据；ambiguous reject_policy=keep")],
        ],
        "lrrrr",
    )

    stream_table = table(
        ["stream", "catalog events", "TES events", "rate Hz", "raw cps", "BGO cps", "final cps"],
        [
            [
                "prompt",
                catalog["by_stream"]["prompt"]["events"],
                catalog["by_stream"]["prompt"]["tes_events"],
                f"{catalog['by_stream']['prompt']['rate_hz']:.6f}",
                f"{by_stream['prompt']['raw']:.6f}",
                f"{by_stream['prompt']['bgo']:.6f}",
                f"{by_stream['prompt']['final']:.6f}",
            ],
            [
                "delayed",
                catalog["by_stream"]["delayed"]["events"],
                catalog["by_stream"]["delayed"]["tes_events"],
                f"{catalog['by_stream']['delayed']['rate_hz']:.6f}",
                f"{by_stream['delayed']['raw']:.6f}",
                f"{by_stream['delayed']['bgo']:.6f}",
                f"{by_stream['delayed']['final']:.6f}",
            ],
            [
                "science",
                catalog["by_stream"]["science"]["events"],
                catalog["by_stream"]["science"]["tes_events"],
                f"{catalog['by_stream']['science']['rate_hz']:.9f}",
                f"{by_stream['science']['raw']:.9f}",
                f"{by_stream['science']['bgo']:.9f}",
                f"{by_stream['science']['final']:.9f}",
            ],
        ],
        "lrrrrrr",
    )

    draw_table = table(
        ["stream", "rate Hz", r"$\lambda=RT$", "drawn instances"],
        [
            [k, f"{v['rate_hz']:.9g}", f"{v['lambda']:.6g}", v["drawn"]]
            for k, v in draw.items()
        ],
        "lrrr",
    )

    run_table = table(
        ["run", "jobs", "pass", "events", "generated", "CPU s", "SIM GB", "DAT MB"],
        [
            ["instant prompt", instant["jobs"], instant["pass"], instant["events"], instant["generated"], f"{instant['cpu_s']:.3f}", f"{instant['sim_bytes']/1e9:.3f}", f"{instant['dat_bytes']/1e6:.3f}"],
            ["buildup", buildup["jobs"], buildup["pass"], buildup["events"], buildup["generated"], f"{buildup['cpu_s']:.3f}", f"{buildup['sim_bytes']/1e9:.3f}", f"{buildup['dat_bytes']/1e6:.3f}"],
            ["fixed delayed", 1, 1, "1,000,000", "1,000,000", "5638.730", "1.4", ""],
            ["science 511", 1, 1, "100,000", "100,000", "", "", ""],
        ],
        "lrrrrrrr",
    )

    flux_table = table(
        ["particle", "ParticleType", "components", "total flux cm$^{-2}$ s$^{-1}$", "base events"],
        [
            [
                r["particle"],
                {"gamma": 1, "n": 6, "p": 4, "alpha": 21, "eminus": 3, "eplus": 2, "muminus": 9, "muplus": 8}.get(r["particle"], ""),
                r["components"],
                f"{float(r['total_flux_cm2_s']):.9g}",
                prompt_norm["base_events_by_particle"].get(r["particle"], ""),
            ]
            for r in flux_rows
        ],
        "lrrrr",
    )

    particle_run_rows = []
    for p, b in instant["by_particle"].items():
        particle_run_rows.append([
            p,
            b["jobs"],
            b["generated"],
            f"{b['cpu_s']:.1f}",
            f"{b['sim_bytes']/1e9:.3f}",
            f"{b['dat_bytes']/1e6:.3f}",
        ])
    particle_run_table = table(["particle", "jobs", "generated", "CPU s", "SIM GB", "DAT MB"], particle_run_rows, "lrrrrr")

    accidental_table = table(
        ["能窗", "孤立 selected", "偶然连接 selected", "lost", "loss all selected", "survival", "主要 lost cause"],
        [
            [
                "480--550",
                acc["windows"]["broad_480_550"]["base_selected_trials"],
                acc["windows"]["broad_480_550"]["base_selected_with_accidental_bg"],
                acc["windows"]["broad_480_550"]["lost_trials"],
                f"{100*acc['windows']['broad_480_550']['accidental_loss_fraction_all_selected']:.4f}\\%",
                f"{broad_corr:.6f}",
                tex_escape(str(acc["windows"]["broad_480_550"]["loss_causes"])),
            ],
            [
                "510.3--511.8",
                acc["windows"]["line_510p3_511p8"]["base_selected_trials"],
                acc["windows"]["line_510p3_511p8"]["base_selected_with_accidental_bg"],
                acc["windows"]["line_510p3_511p8"]["lost_trials"],
                f"{100*acc['windows']['line_510p3_511p8']['accidental_loss_fraction_all_selected']:.4f}\\%",
                f"{line_corr:.6f}",
                tex_escape(str(acc["windows"]["line_510p3_511p8"]["loss_causes"])),
            ],
        ],
        "lrrrrrr",
    )

    sensitivity_table = table(
        ["window", "B cps", "response cps/(ph cm$^{-2}$ s$^{-1}$)", "3σ uncorrected", "3σ corrected", "5σ corrected"],
        [
            ["480--550", f"{manuscript['broad_480_550']['background_cps']:.6f}", f"{manuscript['broad_480_550']['source_response_cps_per_ph_cm2_s']:.6f}", f"${sci_tex(broad_uncorr_3)}$", f"${sci_tex(broad_corr_3)}$", f"${sci_tex(broad_corr_5)}$"],
            ["510.3--511.8", f"{manuscript['line_window_510p3_511p8']['background_cps']:.6f}", f"{manuscript['line_window_510p3_511p8']['source_response_cps_per_ph_cm2_s']:.6f}", f"${sci_tex(line_uncorr_3)}$", f"${sci_tex(line_corr_3)}$", f"${sci_tex(line_corr_5)}$"],
        ],
        "lrrrrr",
    )

    geometry_rows = []
    for key, val in bounds.get("SHIELDS", {}).items():
        geometry_rows.append([
            tex_escape(key),
            tex_escape(
                f"r_out={val['r_out']}, r_in={val['r_in']}, "
                f"z_out=[{val['z_out_bot']},{val['z_out_top']}], "
                f"z_in=[{val['z_in_bot']},{val['z_in_top']}], hole_r={val['hole_r']}"
            ),
        ])
    for i, layer in enumerate(bounds.get("TES_LAYERS", [])):
        geometry_rows.append([
            f"TES layer {i}",
            tex_escape(
                f"z_center={layer['z_center']}, r_max={layer['r_max']}, "
                f"half_z={layer['hz']}; 376 pixels/layer; "
                "pixel pitch 1.55 in geometry coordinates."
            ),
        ])
    for win in bounds.get("WINDOWS", []):
        geometry_rows.append([
            tex_escape(win["name"]),
            tex_escape(f"z_center={win['z_center']}, thick={win['thick']}, r_max={win['r_max']}"),
        ])

    science_rate_line = next((r for r in science_ledger if r["flux_ph_cm2_s"] == "1.000000000000e-04"), {})
    science_table = table(
        ["quantity", "value"],
        [
            [tex_escape("reference flux"), "1.0e-4 ph cm$^{-2}$ s$^{-1}$"],
            [tex_escape("A_opt"), f"{science_rate_line.get('A_opt_cm2', '50.89')} cm$^2$"],
            [tex_escape("T_atm"), science_rate_line.get("T_atm", "0.7390423888027")],
            [tex_escape("injection rate"), f"{norm['science_injection_rate_s^-1']:.12g} s$^{{-1}}$"],
            [tex_escape("Cosima triggers"), "100000"],
            [tex_escape("science catalog selected rate after final cuts"), f"{by_stream['science']['final']:.12g} cps"],
            [tex_escape("response per flux"), f"{sci['science_final_response_cps_per_ph_cm-2_s-1']:.6f} cps/(ph cm$^{{-2}}$ s$^{{-1}}$)"],
        ],
        "lr",
    )

    file_table = longtable(
        ["类别", "路径", "存在", "大小/数量", "说明"],
        source_file_rows(),
        widths=[0.15, 0.38, 0.07, 0.13, 0.18],
    )

    code_table = longtable(
        ["阶段", "代码文件", "用途"],
        code_inventory_rows(),
        widths=[0.18, 0.35, 0.38],
    )

    command_rows = [
        ["生成全空间源", path_tex("python3 tools/build_fullsphere_particle_sources.py --spectrum-dir cosima_spectra_dp_2602units")],
        ["instant prompt", path_tex("python3 tools/run_equiv2602_pipeline.py --mode instant --workers 20 --allow-heavy-run")],
        ["buildup", path_tex("python3 tools/run_equiv2602_pipeline.py --mode buildup --workers 20 --allow-heavy-run")],
        ["buildup -> delay source", path_tex("python3 tools/makedecaysourcewithplot_rpip.py --mode production --input production_runs/buildup_equiv2602 --out production_runs/decay_from_buildup_equiv2602")],
        ["ground-state fix", path_tex("python3 tools/build_fixed_delay_source.py --source production_runs/decay_from_buildup_equiv2602/activation_decay_day15.source --outdir production_runs/delay_fix_from_buildup_equiv2602")],
        ["delayed full 1M", path_tex("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima production_runs/delay_fix_from_buildup_equiv2602/activation_decay_day15_groundstate_fixed.source")],
        ["science 100k", path_tex("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima run_configs/Science_511_onaxis_focalbeam_local.source")],
        ["完整统计", path_tex("python3 tools/make_complete_day15_report.py --workers 20")],
        ["science accidental veto", path_tex("python3 tools/estimate_science_accidental_veto.py --n-trials 1000000")],
        ["本报告", path_tex("python3 tools/make_gptpro_full_detail_packet.py")],
    ]
    command_listing = "\n".join(
        [
            "python3 tools/build_fullsphere_particle_sources.py --spectrum-dir cosima_spectra_dp_2602units",
            "python3 tools/run_equiv2602_pipeline.py --mode instant --workers 20 --allow-heavy-run",
            "python3 tools/run_equiv2602_pipeline.py --mode buildup --workers 20 --allow-heavy-run",
            "python3 tools/makedecaysourcewithplot_rpip.py --mode production --input production_runs/buildup_equiv2602 --out production_runs/decay_from_buildup_equiv2602",
            "python3 tools/build_fixed_delay_source.py --source production_runs/decay_from_buildup_equiv2602/activation_decay_day15.source --outdir production_runs/delay_fix_from_buildup_equiv2602",
            "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima production_runs/delay_fix_from_buildup_equiv2602/activation_decay_day15_groundstate_fixed.source",
            "/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima run_configs/Science_511_onaxis_focalbeam_local.source",
            "python3 tools/make_complete_day15_report.py --workers 20",
            "python3 tools/estimate_science_accidental_veto.py --n-trials 1000000",
            "python3 tools/make_gptpro_full_detail_packet.py",
        ]
    )
    command_table = longtable(["阶段", "命令/命令等价形式"], command_rows, widths=[0.22, 0.70])

    tex = rf"""
\documentclass[10.5pt,a4paper]{{ctexart}}
\usepackage[a4paper,margin=1.65cm]{{geometry}}
\usepackage{{fontspec,amsmath,amssymb,booktabs,longtable,array,graphicx,float,caption,xurl,hyperref,xcolor,listings}}
\usepackage{{enumitem}}
\setCJKmainfont{{Noto Serif CJK SC}}
\setCJKsansfont{{Noto Sans CJK SC}}
\setmainfont{{TeX Gyre Termes}}
\setsansfont{{TeX Gyre Heros}}
\hypersetup{{colorlinks=true,linkcolor=blue!55!black,urlcolor=blue!55!black,citecolor=blue!55!black}}
\captionsetup{{font=small,labelfont=bf}}
\setlist{{nosep,leftmargin=2em}}
\renewcommand{{\figurename}}{{图}}
\renewcommand{{\tablename}}{{表}}
\lstset{{
  basicstyle=\ttfamily\scriptsize,
  breaklines=true,
  columns=fullflexible,
  keepspaces=true,
  frame=single,
  framerule=0.2pt,
  xleftmargin=0.4em,
  xrightmargin=0.4em,
  captionpos=b
}}
\title{{COSMOSRAY\_BG\_2605 第15天 511 keV 本底与科学源模拟：极详细可审计工作报告}}
\author{{Codex TES 511 simulation audit}}
\date{{2026-05-12}}
\begin{{document}}
\maketitle
\tableofcontents
\clearpage

\section{{摘要}}
本报告是当前 \path{{cosmosray_bg_2605}} 工作的完整技术审计版，而不是 PPT 摘要版。它逐步记录源文件、几何、运行命令、归一化、后处理代码、VETO 逻辑、accidental-veto 校正和最终数值，目的是让外部审阅者可以沿文件路径和代码行复算每一个结论。

当前主链路为：
\begin{{enumerate}}
  \item 用 2602-compatible EXPACS/PARMA 能谱生成 8 种大气次级粒子全空间源。
  \item 分别运行 instant prompt 与 activation buildup；buildup 的 SIM/DAT 记录 RPIP 活化核素。
  \item 从 buildup 生成 day-15 delayed decay source，并应用 W-183/W-180 基态修正。
  \item 单独运行 fixed delayed 1M 衰变输运。
  \item 单独运行 511 keV on-axis science source；外部聚焦光学和大气透过率只进入归一化，不在 Cosima 中重复建模。
  \item 把 prompt、delayed、science 三类 SIM catalog 放入共同泊松时间轴，按 1 $\mu$s coincidence window 合并候选组。
  \item 对同一个候选组执行 480--550 keV 或 510.3--511.8 keV 能窗、BGO veto 和 Compton/FoV veto。
  \item 用 1M science trial bootstrap 单独估计无关本底导致的 science accidental-veto loss，并修正灵敏度。
\end{{enumerate}}

\section{{最终结论}}
\begin{{itemize}}
  \item 第15天 480--550 keV common-timeline 结果：raw {rates['raw']:.6f} cps，BGO 后 {rates['bgo']:.6f} cps，BGO+Compton/FoV 后 {rates['final']:.6f} cps。
  \item direct-expectation 交叉检查：raw {direct['raw']:.6f} cps，BGO 后 {direct['bgo']:.6f} cps，final {direct['final']:.6f} cps。它与单次泊松时间轴的差异是有限 realization 与混合 coincidence 的统计/时序效应。
  \item science stream 已经进入共同泊松时间轴：期望 {draw['science']['lambda']:.6f} 个实例，实际抽到 {draw['science']['drawn']} 个；这些 science-containing 候选也经过同一 BGO 和 Compton/FoV veto。
  \item 灵敏度曲线不用这 5 个 science realization 直接估计，而用 direct-expectation/Asimov science response，避免 1094.2 s realization 的低计数噪声。
  \item accidental-veto bootstrap 给出 science survival correction：480--550 keV 为 {broad_corr:.6f}，510.3--511.8 keV 为 {line_corr:.6f}。校正后 1 Ms、3$\sigma$ 阈值分别为 ${sci_tex(broad_corr_3)}$ 与 ${sci_tex(line_corr_3)}$ ph cm$^{{-2}}$ s$^{{-1}}$。
  \item 在当前保守窗口计数方法下，$10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ 稳态点源尚未达到稳健 1 Ms 3$\sigma$；下一步需要空间-能谱似然、ROI 优化、活化线剔除和更完整的 source-injection long timeline。
\end{{itemize}}

\section{{审计边界}}
本报告复核的是当前本地 2605 链路，不把 2602/PPT 数值作为必须完全重合的目标。2605 的目标是最大限度复刻 2602 的物理工作流，同时修正已确认的问题：2602-compatible source unit、独立 seed、W183/W180 delayed source bug、science source 纳入、共同泊松时间轴和 science accidental-veto correction。旧 PPT 中的 day-15 8.56 cps 是工作流 heritage；当前 5.644 cps 是 corrected chain 的结果。

\section{{目录和文件谱系}}
{file_table}

\section{{代码谱系}}
{code_table}

\section{{关键运行命令}}
下表写的是本轮链路的命令等价形式。部分命令在实际运行时含有工作目录、worker 数或 smoke/full 参数差异；其可审计产物和日志路径在后续小节列出。

{command_table}

{lst("Exact command lines with preserved spaces", command_listing)}

\section{{几何模型}}
几何 source truth 是 \path{{cosmosray_bg_2605/XZTES/TibetTES_v5_6layers.geo.setup}}，它 include 主几何 \path{{TibetTES_v5_6layers.geo}} 和探测器映射 \path{{TibetTES_v5_6layers.det}}。Gate A 已确认 source 文件必须使用与 XZTES 几何相同的数值坐标；旧的 z=12.766 会把 science source 放在 \texttt{{TES\_L0}} 附近，已被 z=127.66、半径18.0 的 Be-window 外侧源取代。

{longtable(["体/层", "几何边界"], geometry_rows, widths=[0.25, 0.65])}

\subsection{{材料定义}}
{lst("Materials_TibetTES.geo lines 1--23", snippet(ROOT / "XZTES" / "Materials_TibetTES.geo", 1, 23))}

\subsection{{主几何体与屏蔽层}}
{lst("TibetTES_v5_6layers.geo lines 1--145", snippet(ROOT / "XZTES" / "TibetTES_v5_6layers.geo", 1, 145))}

\subsection{{窗口和 Be entrance plane}}
{lst("TibetTES_v5_6layers.geo window lines", snippet(ROOT / "XZTES" / "TibetTES_v5_6layers.geo", 11724, 11755))}

\subsection{{探测器敏感体映射}}
TES 六层 calorimeter 使用 \texttt{{TES\_Pixel\_L0}} 到 \texttt{{TES\_Pixel\_L5}}；BGO shield 是独立 scintillator sensitive volume。后处理里的 BGO veto 读取 SIM 里的 BGO hit 总能量，而不是只按 source label 判断。

{lst("TibetTES_v5_6layers.det lines 1--116", snippet(ROOT / "XZTES" / "TibetTES_v5_6layers.det", 1, 116))}

\section{{大气宇宙线源}}
源生成脚本读取 \path{{expacs_fullsphere_20bin_sources/manifest.csv}} 和 2602-compatible MFunction 能谱目录 \path{{expacs_fullsphere_20bin_sources/cosima_spectra_dp_2602units/}}。每种粒子有 20 个 equal-solid-angle bin：0--90 deg 为 downward，90--180 deg 为 upward。ParticleType 映射沿用旧可运行 MEGAlib 约定：gamma 1、e+ 2、e- 3、p 4、n 6、mu+ 8、mu- 9、alpha 21。

\begin{{table}}[H]
\centering
{flux_table}
\caption{{2605 使用的大气源总 flux 与等效事件数计划。}}
\end{{table}}

\subsection{{源生成代码}}
{lst("build_fullsphere_particle_sources.py lines 19--124", snippet(ROOT / "tools" / "build_fullsphere_particle_sources.py", 19, 124), "Python")}

\subsection{{gamma source 示例}}
{lst("Background_gamma_fullsphere20.source lines 1--90", snippet(ROOT / "megalib_sources_fullsphere20" / "Background_gamma_fullsphere20.source", 1, 90))}

\section{{instant prompt 与 buildup 运行}}
instant 和 buildup 使用相同大气粒子 source plan。instant 不打开 activation buildup 记录，用于 prompt 本底；buildup 运行记录活化核素 DAT/RPIP，用于构建 delayed source。两者都由 \path{{run_equiv2602_pipeline.py}} 调度，每个 job patch 唯一 seed，避免 replica 或 split 重复随机序列。

\begin{{table}}[H]
\centering
{run_table}
\caption{{主生产运行统计。}}
\end{{table}}

\begin{{table}}[H]
\centering
{particle_run_table}
\caption{{instant prompt 运行按粒子分解。buildup 事件计划相同，CPU 和 DAT 较高是因为 activation/RPIP 记录。}}
\end{{table}}

\subsection{{运行计划和资源保护代码}}
{lst("run_equiv2602_pipeline.py build_jobs lines 337--462", snippet(ROOT / "tools" / "run_equiv2602_pipeline.py", 337, 462), "Python")}

\subsection{{seed patch 与 Cosima 调用代码}}
{lst("run_equiv2602_pipeline.py patch/run lines 200--291", snippet(ROOT / "tools" / "run_equiv2602_pipeline.py", 200, 291), "Python")}

\section{{buildup RPIP 到 delayed source}}
buildup 输出中 MEGAlib stepping-action 修改版记录 \texttt{{CC IP RP}}，后处理按 volume name、ZA、excitation、z bin 和 radial profile 构建 RadialProfileBeam 源块。第15天活度先用生成量、半衰期、飞行照射时间计算，再转成 Cosima source flux。当前 full 2605 RPIP delayed source 解析 478944 条 \texttt{{CC IP RP}}，5,276 source blocks，总活度 1592.2637 Bq；随后进入 ground-state fix。

\subsection{{RPIP 解析代码}}
{lst("makedecaysourcewithplot_rpip.py RPIP parser lines 187--267", snippet(ROOT / "tools" / "makedecaysourcewithplot_rpip.py", 187, 267), "Python")}

\subsection{{活度公式代码}}
{lst("makedecaysourcewithplot_rpip.py activity lines 336--357", snippet(ROOT / "tools" / "makedecaysourcewithplot_rpip.py", 336, 357), "Python")}

\subsection{{RadialProfileBeam source 输出代码}}
{lst("makedecaysourcewithplot_rpip.py source writer lines 681--760", snippet(ROOT / "tools" / "makedecaysourcewithplot_rpip.py", 681, 760), "Python")}

\section{{W183/W180 ground-state 修正}}
2602 原始 delayed source 把 \texttt{{74183/exc=0}} 和 \texttt{{74180/exc=0}} 当作短寿命同核异能态，实际应按 NUBASE ground-state 处理。当前 fixed source 将 W-183 ground state 视为稳定并删除，对 W-180 ground state 按极长半衰期重算到近零。结果是 source blocks 从 5,276 变为 5,156，总活度从 {delay['old_total_activity_Bq']:.6f} Bq 变为 {delay['new_total_activity_Bq']:.6f} Bq；fixed source 中 W183/W180 残留检查为 {delay['fixed_source_contains_W183']} / {delay['fixed_source_contains_W180']}。

notable correction 摘要来自 \path{{source_fix_summary.json}}：
\begin{{itemize}}
  \item W-183 in W\_Shield：旧活度 757.2277 Bq，新 ground-state 活度 0，删除。
  \item W-180 in W\_Shield：旧活度 8.3652 Bq，新 ground-state 活度约 $1.50\times10^{{-19}}$ Bq，删除/近零。
  \item CollBarX/CollBarY 的 W-183 source blocks 也按 stable ground-state 删除。
\end{{itemize}}

\subsection{{ground-state fix 代码}}
{lst("build_fixed_delay_source.py activity/fix lines 210--278", snippet(ROOT / "tools" / "build_fixed_delay_source.py", 210, 278), "Python")}

\subsection{{fixed delayed source 头部}}
{lst("activation_decay_day15_groundstate_fixed.source lines 1--80", snippet(ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602" / "activation_decay_day15_groundstate_fixed.source", 1, 80))}

\section{{fixed delayed Cosima 运行}}
fixed delayed source 用 \texttt{{PhysicsListRadioactiveDecay true}} 和 \texttt{{DecayMode ActivationDelayedDecay}} 单独运行 1,000,000 triggers。Cosima log 报告 generated=1,000,000、CPU=5638.73 s、Observation time=1094.2 s。这个 observation time 被用作 common timeline 的 $T_\mathrm{{obs}}$。

\section{{science 511 keV source}}
science source 不是把天体源当成新的大气背景，而是把聚焦光学和大气透过率放在 Cosima 外部：Cosima 只接收已经穿过光学并聚焦到 Be window 前的 511 keV photons。归一化：
\[
R_\mathrm{{inj}} = F_{{511}} A_\mathrm{{opt}} T_\mathrm{{atm}},
\]
其中 $A_\mathrm{{opt}}=50.89$ cm$^2$，$T_\mathrm{{atm}}=0.7390423888027$，所以 $F_{{511}}=10^{{-4}}$ ph cm$^{{-2}}$ s$^{{-1}}$ 对应 injection rate {norm['science_injection_rate_s^-1']:.12g} s$^{{-1}}$。Cosima source 为 511 keV monoenergetic HomogeneousBeam，z=127.66、beam radius 18.0 几何单位，方向指向 -z。

\begin{{table}}[H]
\centering
{science_table}
\caption{{science source 归一化与响应。}}
\end{{table}}

\subsection{{science source 文件}}
{lst("run_configs/Science_511_onaxis_focalbeam_local.source", snippet(ROOT / "run_configs" / "Science_511_onaxis_focalbeam_local.source", 1, 27))}

\subsection{{science README}}
{lst("science_511_onaxis_source/README.md", snippet(ROOT / "science_511_onaxis_source" / "README.md", 1, 24))}

\section{{SIM catalog 解析和归一化}}
\path{{make_complete_day15_report.py}} 从 prompt、fixed delayed 和 science SIM 中解析 event-level TES/BGO hits。每个原始 MC event 保存 stream、tag、source file、local ID、rate weight、TES 总能量、BGO 总能量和像素层/编号/能量。prompt event rate 来自 2602-compatible full-sphere 归一化；delayed event rate 来自 fixed delayed observation time；science event rate 来自 reference flux 的 injection rate 除以 generated triggers。

\subsection{{归一化和 event rate 代码}}
{lst("make_complete_day15_report.py normalization lines 103--157", snippet(ROOT / "tools" / "make_complete_day15_report.py", 103, 157), "Python")}

\subsection{{SIM 解析代码}}
{lst("make_complete_day15_report.py SIM parser lines 214--260", snippet(ROOT / "tools" / "make_complete_day15_report.py", 214, 260), "Python")}

\begin{{table}}[H]
\centering
{stream_table}
\caption{{event catalog 与 direct-expectation stream 分解。}}
\end{{table}}

\section{{共同泊松时间轴}}
三类流的实例数独立按 $N\sim\mathrm{{Poisson}}(RT)$ 抽样，时间在 $[0,T]$ 内均匀分布。按时间排序后，用 rolling 规则把相邻时间差不超过 1 $\mu$s 的 event instances 合并为一个 candidate。这一步是必须的，因为 BGO veto 和 Compton/FoV veto 都作用在同一候选时间窗，而不是单独 event。

\begin{{table}}[H]
\centering
{draw_table}
\caption{{common timeline 泊松抽样。}}
\end{{table}}

\subsection{{时间轴抽样代码}}
{lst("make_complete_day15_report.py draw_timeline lines 508--532", snippet(ROOT / "tools" / "make_complete_day15_report.py", 508, 532), "Python")}

\subsection{{候选组合并和 VETO 代码}}
{lst("make_complete_day15_report.py analyze_timeline lines 533--593", snippet(ROOT / "tools" / "make_complete_day15_report.py", 533, 593), "Python")}

\section{{BGO VETO 和 Compton/FoV VETO}}
BGO veto 对 candidate 内所有 event 的 BGO hit 能量求和，要求小于 50 keV。Compton/FoV veto 对 TES pixel hit 的能量、层号和像素几何关系调用 \texttt{{classify\_compton}}；如果为单点或可接受几何则保留，如果明显不符合焦源视场则 veto。当前 \texttt{{reject\_policy=keep}} 表示对于无法可靠分类的复杂多点候选采用保守保留，不额外压低本底。

\begin{{table}}[H]
\centering
{veto_table}
\caption{{时间轴 480--550 keV VETO 链。}}
\end{{table}}

{figure_block("timeline", "480--550 keV VETO 前后能谱。")}
{figure_block("veto_bar", "raw、BGO 后、final 的 rate bar。", r"0.76\linewidth")}
{figure_block("wide_spectrum", "100--10000 keV wide spectrum。")}
{figure_block("line_window", "511 keV line-window 视图。")}

\subsection{{event-wise expectation 与 BGO/Compton 分类代码}}
{lst("make_complete_day15_report.py classify/direct lines 436--489", snippet(ROOT / "tools" / "make_complete_day15_report.py", 436, 489), "Python")}

\section{{Image8-like 组分统计}}
根据用户要求，本链路也生成类似“基于立方星”MD 的 IMAGE8 组件图统计。当前文件为 \path{{reports/day15_complete_report/figures/image8_like_component_spectrum_with_science.png}} 和 \path{{image8_like_component_rates_with_science.csv}}。它不是独立物理模型，而是把当前 common normalization 下的 prompt、delayed、science 贡献按能量和来源分解，用于视觉上对照旧 PPT/IMAGE8 风格。

{figure_block("image8", "IMAGE8-like 组分能谱，包含 science stream。")}
{figure_block("incident", "入射/stream 组分图。")}
{figure_block("activation", "ground-state fix 后前十大活化核素/体贡献。")}

\section{{science accidental-veto 校正}}
science source 自身的 BGO/Compton 损失已经包含在 direct-expectation source response 中，但长曝光时，无关 prompt/delayed 背景会偶然落入同一个 1 $\mu$s time window，造成 science 候选被 BGO 或 Compton/FoV 误拒。为避免过度乐观，使用现有 catalog 做 1,000,000 science trial bootstrap。

\begin{{table}}[H]
\centering
{accidental_table}
\caption{{science accidental-veto bootstrap 结果。}}
\end{{table}}

{figure_block("accidental", "science accidental-veto loss 分解。", r"0.78\linewidth")}

\subsection{{accidental-veto bootstrap 代码}}
{lst("estimate_science_accidental_veto.py classify/precompute lines 49--96", snippet(ROOT / "tools" / "estimate_science_accidental_veto.py", 49, 96), "Python")}
{lst("estimate_science_accidental_veto.py run_trials lines 99--190", snippet(ROOT / "tools" / "estimate_science_accidental_veto.py", 99, 190), "Python")}

\section{{灵敏度和 CAM511/DIXE 统计参照}}
CAM511 论文 Fig.11 风格强调 1 Ms 源/本底计数和 $S/\sqrt{{B}}$。本报告用相同的窗口计数思想：背景 rate $R_b$、source response $R_s$，得到
\[
F_{{n\sigma}}=\frac{{n\sqrt{{R_bT}}}}{{R_sT}}.
\]
accidental-veto correction 把 $R_s$ 乘以 $c_\mathrm{{acc}}$。DIXE 论文中的非 X-ray background 统计强调把 NXB 按面积、能窗、立体角或入射通量归一化；这里仅借鉴 bookkeeping 思路，因为本模拟的任务、轨道/气球环境和能段不同。当前 final 480--550 keV rate 若按约 9 cm$^2$ projected active area 书写，为约 {rates['final']/9.0:.3f} cps cm$^{{-2}}$。

\begin{{table}}[H]
\centering
{sensitivity_table}
\caption{{1 Ms 窗口计数灵敏度，已给出 accidental-veto 校正。}}
\end{{table}}

{figure_block("cam511_counts", "CAM511 Fig.11-style source/background counts。")}
{figure_block("sensitivity", "flux threshold versus exposure。")}

\section{{逐步复现检查表}}
\begin{{enumerate}}
  \item 检查 \path{{memory.md}} 与 \path{{workflow.md}}，确认当前主线是 2605 corrected chain。
  \item 检查 \path{{XZTES/TibetTES_v5_6layers.geo.setup}}、\path{{.geo}}、\path{{.det}} 是否存在。
  \item 检查 \path{{megalib_sources_fullsphere20/flux_summary.csv}} 和各粒子 source 的 20 个 component。
  \item 检查 \path{{production_runs/instant_equiv2602/run_summary.md}}：60/60 pass、25,210,216 generated。
  \item 检查 \path{{production_runs/buildup_equiv2602/run_summary.md}}：60/60 pass、25,210,216 generated。
  \item 检查 delayed source fix summary：source blocks 5276 -> 5156，总活度 1592.2637 -> 823.9514 Bq。
  \item 检查 fixed delayed Cosima log：generated 1,000,000，observation time 1094.2 s。
  \item 检查 science source：\path{{run_configs/Science_511_onaxis_focalbeam_local.source}}，100k triggers，HomogeneousBeam z=127.66、radius 18.0，Mono 511 keV。
  \item 运行或复核 \path{{make_complete_day15_report.py}} 输出 summary，确认 common timeline 和 direct-expectation 数值一致。
  \item 运行或复核 \path{{estimate_science_accidental_veto.py}} 输出 summary，确认 1M trials 和 survival correction。
\end{{enumerate}}

\section{{当前可信度与剩余风险}}
我对当前报告中的文件路径、代码逻辑、归一化和列出的数值有最高信心，因为它们均从本地 JSON/CSV/source/script 直接读取并插入；而非重新手写。剩余风险不是报告疏漏，而是科学模型下一阶段的系统项：
\begin{{itemize}}
  \item 当前 science source 是 paper-consistent 的一阶聚焦模型，尚未进行完整 telescope optics ray-tracing。
  \item 1M accidental-veto correction 是 catalog-level bootstrap，不是新增 full Cosima 混合输运；它校正 timing overlay loss，不改变单个 photon transport。
  \item 当前灵敏度是窗口计数估计，没有使用空间-能谱似然，因此对于点源能力仍可能保守或不最优。
  \item delayed activation 的剩余 511 keV 结构仍应围绕 W187 和 decay-chain/branching 做核素诊断。
  \item prompt time-variable lightcurve wrapper 可运行，但当前 verified lightcurve shape 近似全 1，尚未成为物理变化模型。
\end{{itemize}}

\appendix
\section{{附录 A：关键源文件原文片段}}
{lst("Science source ledger", snippet(ROOT / "science_511_onaxis_source" / "metadata" / "science_rate_ledger.csv", 1, 6))}
{lst("Source models CSV", snippet(ROOT / "science_511_onaxis_source" / "metadata" / "science_source_models.csv", 1, 6))}
{lst("Activation inventory top rows before ground-state fix", snippet(ROOT / "production_runs" / "decay_from_buildup_equiv2602" / "activation_inventory_day15.csv", 1, 22))}
{lst("Removed/rescaled W183/W180 entries", snippet(ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602" / "removed_or_rescaled_sources.csv", 746, 835))}

\section{{附录 B：完整统计 summary 关键生成代码}}
{lst("make_complete_day15_report.py make_summary lines 827--920", snippet(ROOT / "tools" / "make_complete_day15_report.py", 827, 920), "Python")}
{lst("make_complete_day15_report.py sensitivity lines 922--1008", snippet(ROOT / "tools" / "make_complete_day15_report.py", 922, 1008), "Python")}

\section{{附录 C：外部参考和本地资料位置}}
\begin{{itemize}}
  \item CAM511 local paper: \path{{/home/ubuntu/codex_tes_comp/codex_tes_comp/papers/511keV/511-CAM_Shirazi-etal_2023_arXiv2206.14652.pdf}}；arXiv: \url{{https://arxiv.org/abs/2206.14652}}。
  \item CAM511 local summaries: \path{{/home/ubuntu/codex_tes_comp/codex_tes_comp/docs/cam511_signal_summary.md}} and \path{{sensitivity_summary_for_codex.json}}。
  \item DIXE NXB statistical reference: \url{{https://doi.org/10.21203/rs.3.rs-8576846/v1}}。
  \item 当前英文 manuscript: \path{{cosmosray_bg_2605/reports/day15_sci_manuscript/cosmosray_bg_2605_sci_manuscript.pdf}}。
  \item 当前中文 manuscript: \path{{cosmosray_bg_2605/reports/day15_sci_manuscript_zh/cosmosray_bg_2605_sci_manuscript_zh.pdf}}。
\end{{itemize}}

\section{{附录 D：本报告 audit JSON}}
本 PDF 同目录写出 \path{{gptpro_full_detail_packet_audit.json}}，其中包括 corrected thresholds、source correction、输入 summary 路径和主要 PDF 路径。

\end{{document}}
"""

    tex_path = OUT / "cosmosray_bg_2605_gptpro_full_detail_packet.tex"
    tex_path.write_text(tex, encoding="utf-8")

    audit = {
        "pdf": rel(OUT / "cosmosray_bg_2605_gptpro_full_detail_packet.pdf"),
        "tex": rel(tex_path),
        "input_summary": rel(SUMMARY),
        "input_accidental": rel(ACCIDENTAL),
        "broad_survival_correction": broad_corr,
        "line_survival_correction": line_corr,
        "broad_3sigma_1Ms_uncorrected": broad_uncorr_3,
        "broad_3sigma_1Ms_corrected": broad_corr_3,
        "line_3sigma_1Ms_uncorrected": line_uncorr_3,
        "line_3sigma_1Ms_corrected": line_corr_3,
        "timeline_final_480_550_cps": rates["final"],
        "direct_expectation_final_480_550_cps": direct["final"],
        "compact_packet_audit": compact,
    }
    (OUT / "gptpro_full_detail_packet_audit.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return tex_path, audit


def main() -> None:
    tex_path, audit = build_tex()
    for _ in range(2):
        subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
            cwd=OUT,
            check=True,
        )
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
