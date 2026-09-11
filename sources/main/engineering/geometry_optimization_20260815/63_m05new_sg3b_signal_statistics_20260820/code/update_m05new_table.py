#!/usr/bin/env python3
"""Add a source-backed SG3B baseline column to the M05NEW replacement table."""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import chi2

ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = ROOT / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820"
M05NEW = ROOT / "core_md/balloon511_ea_latex_drafts/M05NEW"
TABLE = M05NEW / "M05_PAPER_DATA_TABLE.csv"
P58 = ROOT / "engineering/geometry_optimization_20260815/58_sg3b_m05_common_time_response_20260817"
SIGNAL = PACKAGE / "outputs/01_signal/summary.json"
CATALOG = PACKAGE / "outputs/03_expanded_catalog"
TIMELINE = PACKAGE / "outputs/04_candidate_timeline"
ORIGINS = PACKAGE / "outputs/05_optv3_delayed_origins"
ACTIVATION = Path("/mnt/data/TES_Balloon_511_data/SG3/sg3b_m05_delayed_1m_v1/generated/activation/manifest.json")
GEOMETRY = Path("/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816")
FAMILIES = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def garwood(n: int, weight: float) -> tuple[float, float]:
    low = 0.0 if n == 0 else 0.5 * float(chi2.ppf(0.025, 2 * n))
    high = 0.5 * float(chi2.ppf(0.975, 2 * (n + 1)))
    return low * weight, high * weight


def interpolate_crossing(rows: list[dict[str, str]], target: float, asimov: bool) -> float:
    previous = None
    for row in rows:
        day = float(row["day_mid"])
        b = float(row["cumulative_background_counts"])
        s = float(row["cumulative_signal_counts_per_unit_flux"]) * 1.0e-4
        if b <= 0:
            z = 0.0
        elif asimov:
            z = math.sqrt(2.0 * ((s + b) * math.log1p(s / b) - s))
        else:
            z = s / math.sqrt(b)
        if previous is not None and z >= target:
            pday, pz = previous
            return pday + (target - pz) * (day - pday) / (z - pz)
        previous = (day, z)
    return math.nan


def add_ref(row: dict[str, str], ref: str) -> None:
    refs = [value for value in row["引用编号"].split(";") if value]
    if ref not in refs:
        refs.append(ref)
    row["引用编号"] = ";".join(refs)


def main() -> None:
    signal = load_json(SIGNAL)
    catalog_summary = load_json(CATALOG / "summary.json")
    timeline = load_json(TIMELINE / "summary.json")
    origin_summary = load_json(ORIGINS / "summary.json")
    if signal["status"] != "PASS" or not (
        catalog_summary["stopping_rule_met"]
        or catalog_summary.get("publication_precision_rule_met")
    ):
        raise RuntimeError("SG3B signal/gamma closure is not complete")
    if not timeline["status"].startswith("PASS__M05NEW_SG3B"):
        raise RuntimeError("SG3B candidate timeline is not complete")
    if not origin_summary["status"].startswith("PASS"):
        raise RuntimeError("OptV3 origin closure is not complete")

    semantic = read_csv(P58 / "outputs/01_common_time_response/input_job_semantic_scan.csv")
    prompt = [row for row in semantic if row["stream"] == "prompt"]
    prompt_events = {family: sum(int(row["events"]) for row in prompt if row["family"] == family) for family in FAMILIES}
    prompt_tt = {}
    for family in FAMILIES:
        weights = {float(row["event_weight_cps"]) for row in prompt if row["family"] == family}
        if len(weights) != 1:
            raise RuntimeError(f"SG3B prompt weight differs within {family}")
        prompt_tt[family] = 1.0 / weights.pop()
    prompt_events["gamma"] += int(catalog_summary["supplemental_primaries"])
    prompt_tt["gamma"] = float(catalog_summary["combined_gamma_TT_s"])

    if ACTIVATION.exists():
        activation = load_json(ACTIVATION)
        activities = {row["family"]: float(row["transported_ground_activity_Bq"]) for row in activation["source_cells"]}
    else:
        audit = load_json(P58 / "outputs/01_common_time_response/input_audit.json")
        activities = {
            family: float(value)
            for family, value in audit["delayed_day15_activity_Bq_by_family"].items()
        }
    if set(activities) != set(FAMILIES):
        raise RuntimeError("SG3B activation family closure differs")

    cutflow = read_csv(CATALOG / "expanded_direct_cutflow.csv")
    def cf(stream: str | None, family: str | None, stage: str, window: str = "w2_510p58_511p42") -> tuple[int, float, float]:
        selected = [row for row in cutflow if row["window_id"] == window and row["stage"] == stage]
        if stream is not None:
            selected = [row for row in selected if row["stream"] == stream]
        if family is not None:
            selected = [row for row in selected if row["family"] == family]
        n = sum(int(row["raw_selected"]) for row in selected)
        rate = math.fsum(float(row["weighted_rate_cps"]) for row in selected)
        variance = math.fsum(int(row["raw_selected"]) * float(row["event_weight_cps"]) ** 2 for row in selected)
        return n, rate, math.sqrt(variance)

    with np.load(CATALOG / "combined_event_catalog.npz", allow_pickle=False) as arrays:
        event_templates = len(arrays["event_category"])
        pixel_hits = len(arrays["hit_code"])
    categories = load_json(CATALOG / "category_registry.json")["categories"]
    signal_w2 = signal["effective_area"]["w2_510p58_511p42"]
    signal_broad = signal["effective_area"]["broad_480_550"]
    mission_rows = read_csv(TIMELINE / "mission_mature_flux_threshold.csv")
    day15 = next(row for row in mission_rows if int(row["time_bin_id"]) == 60)
    final = timeline["mission_final_20day"]
    b20 = float(final["cumulative_background_counts"])
    k20 = float(final["cumulative_signal_counts_per_unit_flux"])
    s20 = k20 * 1.0e-4
    z_gauss = s20 / math.sqrt(b20)
    z_asimov = math.sqrt(2.0 * ((s20 + b20) * math.log1p(s20 / b20) - s20))
    fmin = float(final["Fmin_3sigma_gaussian_ph_cm2_s"])
    fmin5 = float(final["Fmin_5sigma_gaussian_ph_cm2_s"])
    fmin_asimov = float(final["Fmin_3sigma_poisson_asimov_ph_cm2_s"])
    fmin5_asimov = float(final["Fmin_5sigma_poisson_asimov_ph_cm2_s"])
    stats = timeline["statistical_uncertainty"]
    aeff = float(signal_w2["compton_trajectory_veto"]["Aeff_cm2"])
    aeff_sigma = float(signal_w2["compton_trajectory_veto"]["Aeff_binomial_sigma_cm2"])

    n_pre_p, r_pre_p, _ = cf("prompt", None, "pre_veto")
    n_act_p, r_act_p, _ = cf("prompt", None, "combined_active_veto")
    n_final_p, r_final_p, _ = cf("prompt", None, "compton_trajectory_veto")
    n_pre_d, r_pre_d, _ = cf("delayed", None, "pre_veto")
    n_act_d, r_act_d, _ = cf("delayed", None, "combined_active_veto")
    n_final_d, r_final_d, _ = cf("delayed", None, "compton_trajectory_veto")
    n_pre, r_pre, _ = cf(None, None, "pre_veto")
    n_act, r_act, _ = cf(None, None, "combined_active_veto")
    n_final, r_final, _ = cf(None, None, "compton_trajectory_veto")

    values: dict[str, str] = {
        "P00": "同一 M05 English/Chinese 2026-08-11 稿件",
        "P01": "SG3B auditable reference baseline；与 SH3_OptV3 做同源、同响应、同任务轴比较",
        "P02": "PASS__M05NEW_SG3B_CANDIDATE_OWN_SIGNAL__PUBLICATION_PRECISION_RULE_MET",
        "I01": "同一 TES 核心：6 layers × 376 pixels = 2256 pixels；1.5×1.5×3 mm",
        "I02": "同 OptV3：FWHM=0.420 keV/pixel；threshold=0.300 keV",
        "I03": "同 OptV3：[510.58,511.42] keV",
        "I04": "3 plastic + 3 BGO active volumes；offline threshold=50 keV",
        "I05": "同一 Step05；侧入口盘为原 Step09 合同",
        "I06": "同一 20 d/81-node/45 deg/1 microsecond 任务轴；5 anchors",
        "I07": "同一 F0=1.0e-4 ph cm^-2 s^-1 与 IBIS benchmark",
        "N01": "; ".join(f"{family}={prompt_events[family]}" for family in FAMILIES),
        "N02": "; ".join(f"{family}={prompt_tt[family]:.8g}" for family in FAMILIES),
        "N03": (
            f"gamma supplement={catalog_summary['supplemental_shards']} shards/"
            f"{catalog_summary['supplemental_primaries']} primaries；combined W2-final raw="
            f"{catalog_summary['combined_gamma_W2_final_raw_survivors']}；total direct-final relative sigma="
            f"{catalog_summary['direct_final_day15']['relative_sigma']:.6%}"
        ),
        "N04": "; ".join(f"{family}={activities[family]:.9g}" for family in FAMILIES) + f"; total={math.fsum(activities.values()):.9g}",
        "N05": "1,000,000 triggers/family；8,000,000 total；weight=A_family(day15)/1e6",
        "N06": "exact production-position source_parent_ZA；max position distance <=1e-5 cm",
        "N07": f"{55 + int(catalog_summary['supplemental_shards'])} jobs；{event_templates} detector-positive templates；{pixel_hits} TES pixel hits；{len(categories)} categories",
        "G01": f"geo {sha256(GEOMETRY/'geometry/DEMO2_DR_v3p5_SG3B.geo')}; setup {sha256(GEOMETRY/'geometry/DEMO2_DR_v3p5_SG3B.geo.setup')}; det {sha256(GEOMETRY/'geometry/DEMO2_DR_v3p5_SG3B.det')}",
        "G02": "SG3B：410.30 g Bi upper half-cylinder，radial thickness=4.796 mm；Al harness proxy=235.73 g",
        "G03": "retained SG3A optical chain；37,194 focused rays intersect Bi half-cylinder 0 times",
        "G04": "3 plastic volumes + BGO side/bottom/top active volumes",
        "G05": "local center=(-13.1,0,-5.2) cm；radius=1.898 cm；rotation_y=45 deg",
        "G06": "build/static/10,000-sample overlap validation PASS",
        "Q01": f"37,194 original Step09 EventList rays；aperture=20.08476 cm2；EventList sha256={signal['provenance']['eventlist_sha256']}",
        "Q02": f"pre-veto={signal_w2['pre_veto']['count']}; combined active veto={signal_w2['combined_active_veto']['count']}; final Step05={signal_w2['compton_trajectory_veto']['count']}",
        "Q03": f"pre-veto={signal_w2['pre_veto']['Aeff_cm2']:.8g}; combined active veto={signal_w2['combined_active_veto']['Aeff_cm2']:.8g}; final={aeff:.8g} cm2",
        "Q04": f"pre-veto={signal_broad['pre_veto']['count']}/{signal_broad['pre_veto']['Aeff_cm2']:.8g} cm2；final={signal_broad['compton_trajectory_veto']['count']}/{signal_broad['compton_trajectory_veto']['Aeff_cm2']:.8g} cm2",
        "Q05": f"{float(day15['conditional_signal_kernel_cm2'])*1e-4:.10g} cps at F0",
        "Q06": f"day15 accidental survival={float(day15['conditional_signal_accidental_survival']):.8g}",
        "Q07": f"sigma_Aeff={aeff_sigma:.8g} cm2；relative={aeff_sigma/aeff:.8g}",
        "B01": f"{n_pre_p} records；{r_pre_p:.10g} cps",
        "B02": f"{n_act_p} records；{r_act_p:.10g} cps；combined plastic+BGO active-veto survival={r_act_p/r_pre_p:.6%}",
        "B03": f"{n_final_p} records；{r_final_p:.10g} cps；final background share={r_final_p/r_final:.6%}",
        "B04": f"{n_pre_d} records；{r_pre_d:.10g} cps",
        "B05": f"{n_act_d} records；{r_act_d:.10g} cps；combined active-veto survival={r_act_d/r_pre_d:.6%}",
        "B06": f"{n_final_d} records；{r_final_d:.10g} cps；topology survival={r_final_d/r_act_d:.6%}；share={r_final_d/r_final:.6%}",
        "B07": f"pre-veto={n_pre}/{r_pre:.10g} cps；after combined active veto={n_act}/{r_act:.10g} cps；final={n_final}/{r_final:.10g} cps",
        "B08": f"combined active-veto rate survival={r_act/r_pre:.6%}；Step05 survival={r_final/r_act:.6%}",
        "C21": "source-material/volume/nuclide table available；largest delayed group: Cu-62 from Cu_SubstrateSupport_OpenRing_L2_ZP_panel",
        "M01": f"day15 mature={float(day15['mature_background_W2_final_cps']):.10g} cps；direct={float(day15['direct_W2_final_no_coincidence_cps']):.10g} cps",
        "M02": f"{float(day15['conditional_signal_kernel_cm2'])*1e-4:.10g} cps；accidental survival={float(day15['conditional_signal_accidental_survival']):.8g}",
        "M03": f"{b20:.12g} counts",
        "M04": f"{s20:.12g} counts at F0；kernel={k20:.12g}",
        "M05": f"Gaussian Z={z_gauss:.8g}；Asimov Z={z_asimov:.8g}",
        "M06": f"Gaussian={interpolate_crossing(mission_rows,3.0,False):.6g} d；Asimov={interpolate_crossing(mission_rows,3.0,True):.6g} d",
        "M07": f"Gaussian={interpolate_crossing(mission_rows,5.0,False):.6g} d；Asimov={interpolate_crossing(mission_rows,5.0,True):.6g} d",
        "M08": f"Gaussian={fmin:.12g}；Asimov={fmin_asimov:.12g} ph cm^-2 s^-1",
        "M09": f"Gaussian={fmin5:.12g}；Asimov={fmin5_asimov:.12g} ph cm^-2 s^-1",
        "M10": f"{stats['Fmin_3sigma_gaussian_standard_error_ph_cm2_s']:.12g} ph cm^-2 s^-1；relative={stats['Fmin_3sigma_gaussian_relative_standard_error']:.6%}；paper form=({fmin/1e-5:.3f}±{stats['Fmin_3sigma_gaussian_standard_error_ph_cm2_s']/1e-5:.3f})e-5",
        "M11": f"background transport sigma={stats['background_transport_MC_sigma_counts']:.7g} counts；timeline sigma={stats['background_timeline_replay_sigma_counts']:.7g}；Aeff relative={stats['signal_Aeff_relative_sigma']:.6%}；Fmin relative={stats['Fmin_3sigma_gaussian_relative_standard_error']:.6%}",
        "X01": f"SG3B is the auditable reference：day15 mature final={float(day15['mature_background_W2_final_cps']):.10g} cps",
        "X02": f"CLOSED：candidate-own 37,194-ray signal；Aeff final={aeff:.8g}±{aeff_sigma:.8g} cm2；20d Fmin=({fmin/1e-5:.3f}±{stats['Fmin_3sigma_gaussian_standard_error_ph_cm2_s']/1e-5:.3f})e-5",
        "X03": "SG3B volume/material origin already closed in R17/R18；OptV3 gap now closed in R22",
        "X04": "not rerun；remove old 64-seed paragraph for both geometries",
        "X05": "旧 Mass_model_511 不再作为物理基线；由 SG3B 替代",
        "F01": "SG3B geometry figure available in package55",
        "F02": "同一三流工作流；SG3B baseline 与 OptV3 使用同源合同",
        "F03": "同一八类全空间通量 CSV",
        "F04": "SG3B five-anchor common-time data available in R21",
        "F05": "SG3B expanded compact catalog contains measured energy/category/weights/flags",
        "F06": "SG3B pre-veto/combined-veto flags available",
        "F07": "SG3B hit multiplicity/layer/energy/position available",
        "F08": "SG3B material/volume/family/nuclide origin available in R17/R18",
        "F09": "SG3B 81-node mission significance/Fmin curve available in R21",
        "T01": "same corrected-keV source model and activation definition",
        "T02": "CLOSED：SG3B background + candidate-own signal cutflow",
        "T03": "SG3B family/material/volume/nuclide budget in R17/R18/R21",
        "T04": "SG3B reference geometry values in G01–G06",
        "T05": "SG3B matched cutflow in B01–B08/Q02–Q05",
        "T06": "SG3B component precision in C01–C20",
        "T07": "SG3B matched 20d sensitivity in M01–M11",
    }
    for row_id in ("S01","S02","S03","S04","S05","S06","S07","S08"):
        values[row_id] = "与 OptV3 相同；使用同一 corrected-keV atmospheric source/mission contract"

    component_ids = {
        "C01": ("prompt", "alpha"), "C02": ("prompt", "eminus"),
        "C03": ("prompt", "eplus"), "C04": ("prompt", "gamma"),
        "C05": ("prompt", "muminus"), "C06": ("prompt", "muplus"),
        "C07": ("prompt", "n"), "C08": ("prompt", "p"),
        "C09": ("delayed", "alpha"), "C10": ("delayed", "eminus"),
        "C11": ("delayed", "eplus"), "C12": ("delayed", "gamma"),
        "C13": ("delayed", "muminus"), "C14": ("delayed", "muplus"),
        "C15": ("delayed", "n"), "C16": ("delayed", "p"),
    }
    endpoint_sums = {"prompt": 0.0, "delayed": 0.0}
    subtotal = {}
    for row_id, (stream, family) in component_ids.items():
        n, rate, _ = cf(stream, family, "compton_trajectory_veto")
        weight = (1.0 / prompt_tt[family]) if stream == "prompt" else activities[family] / 1.0e6
        low, high = garwood(n, weight)
        endpoint_sums[stream] += high
        values[row_id] = f"n={n}；weight={weight:.10g} cps；rate={rate:.10g} cps；exact 95%=[{low:.10g},{high:.10g}] cps；share={rate/r_final:.6%}"
    subtotal["prompt"] = cf("prompt", None, "compton_trajectory_veto")
    subtotal["delayed"] = cf("delayed", None, "compton_trajectory_veto")
    values["C18"] = f"n={subtotal['prompt'][0]}；central={subtotal['prompt'][1]:.10g} cps；componentwise upper sum={endpoint_sums['prompt']:.10g} cps"
    values["C19"] = f"n={subtotal['delayed'][0]}；central={subtotal['delayed'][1]:.10g} cps；componentwise upper sum={endpoint_sums['delayed']:.10g} cps"
    values["C20"] = f"n={n_final}；central={r_final:.10g} cps；componentwise upper sum={endpoint_sums['prompt']+endpoint_sums['delayed']:.10g} cps"

    rows = read_csv(TABLE)
    if len(rows) != 98 or len({row["ID"] for row in rows}) != len(rows):
        raise RuntimeError("M05NEW input table identity closure differs")
    if set(values) != {row["ID"] for row in rows}:
        missing = sorted({row["ID"] for row in rows} - set(values))
        extra = sorted(set(values) - {row["ID"] for row in rows})
        raise RuntimeError(f"SG3B table mapping differs: missing={missing}, extra={extra}")
    for row in rows:
        row["SG3B基线值"] = values[row["ID"]]
        if row["ID"] in {"X02", "X03", "T02"}:
            row["状态"] = "READY"
        if row["ID"] == "X02":
            row["M05NEW当前值"] = "CLOSED：SG3B candidate-own signal and matched sensitivity are recorded in the SG3B baseline column"
        elif row["ID"] == "X03":
            top = origin_summary["top_groups"][0]
            row["M05NEW当前值"] = (
                f"PASS exact-position volume/material closure；111 selected events；39 groups；"
                f"largest group={top['source_material']}/{top['source_volume']}/ZA{top['source_parent_ZA']}，"
                f"{top['day15_rate_cps']:.10g} cps"
            )
        elif row["ID"] == "T02":
            row["M05NEW当前值"] = "SG3B reference background and candidate-own 37,194-ray signal cutflow are both closed"
        if row["ID"].startswith("G") or row["ID"] in {"F01"}:
            add_ref(row, "R19")
        if row["ID"].startswith("Q"):
            add_ref(row, "R20")
        if row["ID"].startswith(("N", "B", "C", "M")) or row["ID"] in {"P02", "X01", "X02", "F04", "F05", "F06", "F07", "F09", "T02", "T05", "T06", "T07"}:
            add_ref(row, "R21")
        if row["ID"] in {"X03", "F08"}:
            add_ref(row, "R22")
        if row["ID"] in {"P01", "P02", "M08", "M10", "T07"}:
            add_ref(row, "R23")
    fields = ["ID", "M05位置", "数据项", "M05NEW当前值", "SG3B基线值", "单位或定义", "状态", "论文替换动作", "引用编号"]
    with TABLE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", quoting=csv.QUOTE_ALL)
        writer.writeheader(); writer.writerows(rows)
    comparison = {
        "schema_version": 1,
        "status": "PASS__M05NEW_SG3B_OPTV3_MATCHED_TABLE_READY",
        "paper_logic": "SG3B auditable baseline -> background diagnosis -> SH3 OptV3 geometry -> matched feasibility comparison",
        "SG3B": {
            "Aeff_W2_final_cm2": aeff,
            "day15_background_cps": float(day15["mature_background_W2_final_cps"]),
            "Fmin_3sigma_gaussian": fmin,
            "Fmin_3sigma_standard_error": stats["Fmin_3sigma_gaussian_standard_error_ph_cm2_s"],
        },
        "OptV3": {
            "Aeff_W2_final_cm2": 15.08544,
            "day15_background_cps": 0.009280,
            "Fmin_3sigma_gaussian": 2.229369053e-5,
            "Fmin_3sigma_standard_error": 2.086243580e-6,
        },
        "ratios_OptV3_over_SG3B": {
            "Aeff": 15.08544 / aeff,
            "day15_background": 0.009280 / float(day15["mature_background_W2_final_cps"]),
            "Fmin": 2.229369053e-5 / fmin,
        },
    }
    (M05NEW / "SG3B_OPTV3_COMPARISON.json").write_text(json.dumps(comparison, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(comparison, indent=2), flush=True)


if __name__ == "__main__":
    main()
