#!/usr/bin/env python3
"""Plot per-pixel and event-summed energy spectra for the 86 SH3 neutron events.

The script never reads the large SIM files.  It combines the already extracted
direct Ta/TES channel deposits with the accepted all-86 G4CMP comparison run.
For candidate C only, the G4CMP channel allocation is replaced by the mean of
the five dedicated 8192-packet replicates (zeros are included in the mean).
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MPL_CACHE = ROOT / ".matplotlib_cache"
MPL_CACHE.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CACHE))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import Patch


OUT = ROOT / "outputs" / "neutron_energy_band"
EVENT_HITS = ROOT / "outputs" / "unvetoed_events.csv"
DIRECT = OUT / "direct_tes_channels_all86.csv"
ALL86_CHANNELS = ROOT / "runs" / "staircase" / "04_all86" / "tuned_c_area0p12" / "channels.csv"
ALL86_EVENTS = ROOT / "runs" / "staircase" / "04_all86" / "tuned_c_area0p12" / "events.csv"
REPLICATE_CHANNELS = [
    ROOT / "runs" / "staircase" / "02c_candidate_C_replicates" / f"rep{i}" / "channels.csv"
    for i in range(1, 6)
]
STRICT_RECOILS = ROOT / "input_snapshot" / "results" / "strict_si_elastic_recoil_events_10m.csv"

ROI_LOW = 510.58
ROI_HIGH = 511.42
ZOOM_LOW = 480.0
ZOOM_HIGH = 550.0
REPORTING_THRESHOLD_KEV = 0.42
GAUSSIAN_FWHM_KEV = 0.42
SAMPLE_LIVETIME_S = 1911.8824


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=float), q))


def gaussian_roi_probability(mean_keV: float) -> float:
    sigma = GAUSSIAN_FWHM_KEV / 2.354820045
    normal_cdf = lambda x: 0.5 * (1.0 + math.erf((x - mean_keV) / (sigma * math.sqrt(2.0))))
    return max(0.0, normal_cdf(ROI_HIGH) - normal_cdf(ROI_LOW))


def fmt_channel(layer: str | int, pixel: str | int) -> str:
    return f"L{int(layer)}:P{int(pixel)}"


def configure_plotting() -> None:
    cjk_path = Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    if not cjk_path.is_file():
        raise RuntimeError(f"Required plotting font not found: {cjk_path}")
    font_manager.fontManager.addfont(str(cjk_path))
    cjk = font_manager.FontProperties(fname=cjk_path).get_name()
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [cjk, "DejaVu Sans"],
            "axes.unicode_minus": False,
            "figure.dpi": 150,
            "savefig.dpi": 240,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.7,
        }
    )


def load_event_metadata() -> dict[int, dict[str, object]]:
    events: dict[int, dict[str, object]] = {}
    for row in read_csv(EVENT_HITS):
        order = int(row["event_order"])
        candidate = row["candidate"].strip()
        item = {
            "event_order": order,
            "sample_id": row["sample_id"],
            "job_id": row["job_id"],
            "event_id": int(row["event_id"]),
            "candidate": candidate,
            "strict_recoil_event": bool(int(row["strict_recoil_event"])),
            "si_total_keV": float(row["si_total_keV"]),
            "si_elastic_recoil_keV": float(row["si_elastic_recoil_keV"]),
            "direct_tes_catalog_keV": float(row["tes_total_keV"]),
            "bgo_total_keV": float(row["bgo_total_keV"]),
        }
        if order in events:
            for key, value in item.items():
                if events[order][key] != value:
                    raise RuntimeError(f"Inconsistent event metadata for event_order={order}, field={key}")
        else:
            events[order] = item
    if sorted(events) != list(range(1, 87)):
        raise RuntimeError(f"Expected event_order 1..86, got {sorted(events)}")
    return events


def load_channel_components(events: dict[int, dict[str, object]]):
    direct: dict[tuple[int, str], float] = defaultdict(float)
    sensor: dict[tuple[int, str], float] = defaultdict(float)

    for row in read_csv(DIRECT):
        order = int(row["event_order"])
        channel = fmt_channel(row["layer"], row["pixel_id"])
        direct[(order, channel)] += float(row["direct_tes_energy_keV"])

    for row in read_csv(ALL86_CHANNELS):
        order = int(row["source_event_order"])
        channel = fmt_channel(row["layer"], row["pixel_id"])
        sensor[(order, channel)] += float(row["sensor_energy_keV"])

    c_orders = [order for order, item in events.items() if item["candidate"] == "C"]
    if len(c_orders) != 1:
        raise RuntimeError(f"Expected exactly one candidate C, got {c_orders}")
    c_order = c_orders[0]

    # Replace candidate C's one-run channel realization by a five-run mean.
    for key in [key for key in sensor if key[0] == c_order]:
        del sensor[key]
    replicate_maps: list[dict[str, float]] = []
    for path in REPLICATE_CHANNELS:
        one: dict[str, float] = defaultdict(float)
        for row in read_csv(path):
            if int(row["source_event_order"]) != c_order:
                raise RuntimeError(f"Unexpected event in {path}")
            one[fmt_channel(row["layer"], row["pixel_id"])] += float(row["sensor_energy_keV"])
        replicate_maps.append(one)
    for channel in sorted(set().union(*(one.keys() for one in replicate_maps))):
        sensor[(c_order, channel)] = sum(one.get(channel, 0.0) for one in replicate_maps) / len(replicate_maps)

    # Validate the independent direct-channel extraction against the compact catalog.
    for order, item in events.items():
        channel_sum = sum(value for (event_order, _), value in direct.items() if event_order == order)
        if not math.isclose(channel_sum, float(item["direct_tes_catalog_keV"]), rel_tol=0.0, abs_tol=2e-6):
            raise RuntimeError(
                f"Direct TES mismatch for event {order}: channels={channel_sum}, "
                f"catalog={item['direct_tes_catalog_keV']}"
            )
    return direct, sensor, c_order


def make_rows(events, direct, sensor, c_order):
    channel_rows: list[dict[str, object]] = []
    event_rows: list[dict[str, object]] = []
    by_event: dict[int, list[dict[str, object]]] = defaultdict(list)
    all_keys = sorted(set(direct) | set(sensor))
    for order, channel in all_keys:
        item = events[order]
        d = direct.get((order, channel), 0.0)
        s = sensor.get((order, channel), 0.0)
        total = d + s
        layer, pixel = channel.split(":P")
        row = {
            "event_order": order,
            "sample_id": item["sample_id"],
            "job_id": item["job_id"],
            "event_id": item["event_id"],
            "candidate": item["candidate"],
            "strict_recoil_event": int(bool(item["strict_recoil_event"])),
            "layer": int(layer[1:]),
            "pixel_id": int(pixel),
            "channel": channel,
            "direct_tes_keV": d,
            "g4cmp_sensor_keV": s,
            "combined_channel_keV": total,
            "sensor_source": "candidate_C_mean_of_5x8192_packets" if order == c_order else "all86_tuned_c_area0p12",
        }
        channel_rows.append(row)
        by_event[order].append(row)

    for order, item in events.items():
        allocation = sorted(by_event[order], key=lambda row: float(row["combined_channel_keV"]), reverse=True)
        total = sum(float(row["combined_channel_keV"]) for row in allocation)
        direct_total = sum(float(row["direct_tes_keV"]) for row in allocation)
        sensor_total = sum(float(row["g4cmp_sensor_keV"]) for row in allocation)
        dominant = allocation[0]
        allocation_text = "; ".join(
            f"{row['channel']}={float(row['combined_channel_keV']):.9f}" for row in allocation
        )
        event_rows.append(
            {
                "event_order": order,
                "sample_id": item["sample_id"],
                "job_id": item["job_id"],
                "event_id": item["event_id"],
                "candidate": item["candidate"],
                "strict_recoil_event": int(bool(item["strict_recoil_event"])),
                "si_total_keV": item["si_total_keV"],
                "si_elastic_recoil_keV": item["si_elastic_recoil_keV"],
                "direct_tes_keV": direct_total,
                "g4cmp_sensor_keV": sensor_total,
                "event_sum_keV": total,
                "positive_channel_count": len(allocation),
                "channels_ge_0p42keV": sum(
                    float(row["combined_channel_keV"]) >= REPORTING_THRESHOLD_KEV for row in allocation
                ),
                "dominant_channel": dominant["channel"],
                "dominant_channel_keV": dominant["combined_channel_keV"],
                "pixel_allocation_descending_keV": allocation_text,
                "sensor_source": "candidate_C_mean_of_5x8192_packets" if order == c_order else "all86_tuned_c_area0p12",
            }
        )
    return channel_rows, event_rows, by_event


def validate_against_all86_reference(event_rows, c_order: int) -> dict[str, float | int]:
    reference = {
        int(row["source_event_order"]): float(row["reconstructed_mean_keV"])
        for row in read_csv(ALL86_EVENTS)
    }
    observed = {int(row["event_order"]): float(row["event_sum_keV"]) for row in event_rows}
    if set(reference) != set(observed):
        raise RuntimeError("Event keys do not match the accepted all86 reference")
    differences = [abs(observed[order] - reference[order]) for order in observed if order != c_order]
    max_difference = max(differences)
    if max_difference > 1e-8:
        raise RuntimeError(f"Non-C event-sum closure failed: max difference={max_difference} keV")
    return {
        "validated_non_C_event_count": len(differences),
        "max_abs_difference_keV": max_difference,
        "candidate_C_five_replicate_mean_keV": observed[c_order],
        "candidate_C_single_all86_realization_keV": reference[c_order],
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def event_label(row: dict[str, object]) -> str:
    candidate = f" / {row['candidate']}" if row["candidate"] else ""
    return f"E{row['event_order']}{candidate}"


STRICT_COLOR = "#D55E00"
OTHER_COLOR = "#4C78A8"
ROI_COLOR = "#E69F00"


def add_roi(ax, label: bool = True) -> None:
    ax.axvspan(ROI_LOW, ROI_HIGH, color=ROI_COLOR, alpha=0.24, zorder=0, label="511 keV ROI" if label else None)
    ax.axvline(511.0, color="#8C5A00", lw=1.0, ls="--", zorder=1)


def plot_single_pixel(event_rows, channel_rows, path_stem: Path) -> dict[str, object]:
    strict_max = [float(row["dominant_channel_keV"]) for row in event_rows if int(row["strict_recoil_event"])]
    other_max = [float(row["dominant_channel_keV"]) for row in event_rows if not int(row["strict_recoil_event"])]
    all_max = strict_max + other_max
    zoom = [row for row in channel_rows if ZOOM_LOW <= float(row["combined_channel_keV"]) <= ZOOM_HIGH]
    zoom.sort(key=lambda row: float(row["combined_channel_keV"]))
    roi = [row for row in channel_rows if ROI_LOW <= float(row["combined_channel_keV"]) < ROI_HIGH]
    gaussian_expected_roi = sum(
        gaussian_roi_probability(float(row["combined_channel_keV"])) for row in channel_rows
    )

    fig = plt.figure(figsize=(14.2, 6.4), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=(1.12, 1.0))
    ax = fig.add_subplot(gs[0, 0])
    axz = fig.add_subplot(gs[0, 1])

    positive = [value for value in all_max if value > 0]
    lo = max(1e-3, min(positive) * 0.7)
    hi = max(1e4, max(positive) * 1.25)
    bins = np.geomspace(lo, hi, 35)
    ax.hist(other_max, bins=bins, histtype="stepfilled", alpha=0.38, color=OTHER_COLOR, label=f"其他 Si 发热事例 (n={len(other_max)})")
    ax.hist(strict_max, bins=bins, histtype="step", lw=2.0, color=STRICT_COLOR, label=f"严格 Si 弹性反冲 (n={len(strict_max)})")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lo, hi)
    ax.set_xlabel("每个中子事例中最大单像素输入能量 (keV)")
    ax.set_ylabel("事例数 / 对数能量区间")
    ax.set_title("A  单像素实际读出：每事例只取能量最大的 TES 通道", loc="left", fontweight="bold")
    ax.axvline(REPORTING_THRESHOLD_KEV, color="#666666", lw=1.0, ls=":")
    ax.text(REPORTING_THRESHOLD_KEV * 1.08, 0.75, "0.42 keV\n制图报告阈值", color="#555555", fontsize=9)
    add_roi(ax)
    ax.legend(frameon=False, loc="upper left")
    ax.text(
        0.03,
        0.04,
        "这里的横坐标不是 Si 总沉积，\n而是一个实际 TES 像素收到的能量。",
        transform=ax.transAxes,
        va="bottom",
        fontsize=10,
        color="#333333",
    )

    add_roi(axz)
    for index, row in enumerate(zoom):
        value = float(row["combined_channel_keV"])
        strict = bool(int(row["strict_recoil_event"]))
        color = STRICT_COLOR if strict else OTHER_COLOR
        axz.scatter(value, index, s=60, color=color, edgecolor="white", linewidth=0.8, zorder=3)
        axz.annotate(
            f"{event_label(row)}  {row['channel']}\n{value:.3f} keV",
            (value, index),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=9.2,
            color="#222222",
        )
    axz.set_xlim(ZOOM_LOW, ZOOM_HIGH)
    axz.set_ylim(-0.8, max(3.7, len(zoom) - 0.2))
    axz.set_yticks([])
    axz.set_xlabel("单个 TES 通道输入能量 (keV)")
    axz.set_title("B  511 keV 邻域逐通道放大（直接标出层号:像素号）", loc="left", fontweight="bold")
    status = "没有单像素真值落入 ROI" if not roi else f"有 {len(roi)} 个单像素真值落入 ROI"
    axz.text(
        0.04,
        0.96,
        f"黄色窄带：[510.58, 511.42) keV\n结果：{status}\n"
        f"加 0.42 keV FWHM 高斯展宽：期望泄漏 {gaussian_expected_roi:.2e}",
        transform=axz.transAxes,
        fontsize=10.5,
        va="top",
        bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "boxstyle": "round,pad=0.35", "alpha": 0.92},
    )

    fig.suptitle(
        "SH3 中子事例的单像素能量分布（86 个 BGO<50 keV 且 Si>0 事例）\n"
        "输入能量 = Ta/TES 直接沉积 + G4CMP 到达该通道的声子能量",
        fontsize=15,
        fontweight="bold",
    )
    for suffix in ("png", "pdf"):
        fig.savefig(path_stem.with_suffix(f".{suffix}"), bbox_inches="tight")
    plt.close(fig)
    return {
        "strict_dominant_pixel_keV": {"q50": percentile(strict_max, 50), "q90": percentile(strict_max, 90), "q99": percentile(strict_max, 99), "max": max(strict_max)},
        "all86_dominant_pixel_keV": {"q50": percentile(all_max, 50), "q90": percentile(all_max, 90), "q99": percentile(all_max, 99), "max": max(all_max)},
        "single_channels_in_480_550": len(zoom),
        "single_channels_in_roi": len(roi),
        "gaussian_fwhm_keV": GAUSSIAN_FWHM_KEV,
        "gaussian_expected_roi_count_for_86_events": gaussian_expected_roi,
        "zoom_channels": [
            {"event_order": int(row["event_order"]), "channel": row["channel"], "energy_keV": float(row["combined_channel_keV"]), "strict": bool(int(row["strict_recoil_event"]))}
            for row in zoom
        ],
    }


def compact_allocation(rows: list[dict[str, object]], keep: int = 6):
    allocation = sorted(rows, key=lambda row: float(row["combined_channel_keV"]), reverse=True)
    head = allocation[:keep]
    tail = allocation[keep:]
    tail_energy = sum(float(row["combined_channel_keV"]) for row in tail)
    return head, tail, tail_energy


def plot_event_sum(event_rows, by_event, path_stem: Path) -> dict[str, object]:
    strict_sum = [float(row["event_sum_keV"]) for row in event_rows if int(row["strict_recoil_event"])]
    other_sum = [float(row["event_sum_keV"]) for row in event_rows if not int(row["strict_recoil_event"])]
    all_sum = strict_sum + other_sum
    zoom = [row for row in event_rows if ZOOM_LOW <= float(row["event_sum_keV"]) <= ZOOM_HIGH]
    zoom.sort(key=lambda row: float(row["event_sum_keV"]))
    roi = [row for row in event_rows if ROI_LOW <= float(row["event_sum_keV"]) < ROI_HIGH]

    fig = plt.figure(figsize=(14.5, 10.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=(1.0, 1.12), width_ratios=(1.1, 1.0))
    ax = fig.add_subplot(gs[0, 0])
    axz = fig.add_subplot(gs[0, 1])
    axb = fig.add_subplot(gs[1, :])

    positive = [value for value in all_sum if value > 0]
    lo = max(1e-3, min(positive) * 0.7)
    hi = max(1e4, max(positive) * 1.25)
    bins = np.geomspace(lo, hi, 35)
    ax.hist(other_sum, bins=bins, histtype="stepfilled", alpha=0.38, color=OTHER_COLOR, label=f"其他 Si 发热事例 (n={len(other_sum)})")
    ax.hist(strict_sum, bins=bins, histtype="step", lw=2.0, color=STRICT_COLOR, label=f"严格 Si 弹性反冲 (n={len(strict_sum)})")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(lo, hi)
    ax.set_xlabel("同一中子事例的跨像素离线能量和 (keV)")
    ax.set_ylabel("事例数 / 对数能量区间")
    ax.set_title("A  多像素离线求和能谱", loc="left", fontweight="bold")
    add_roi(ax)
    ax.legend(frameon=False, loc="upper left")
    ax.text(
        0.03,
        0.04,
        "该能量和用于事后关联与反巧合；\n它不是任意一个 TES 的单脉冲幅度。",
        transform=ax.transAxes,
        va="bottom",
        fontsize=10,
        color="#333333",
    )

    add_roi(axz)
    for index, row in enumerate(zoom):
        value = float(row["event_sum_keV"])
        strict = bool(int(row["strict_recoil_event"]))
        color = STRICT_COLOR if strict else OTHER_COLOR
        axz.scatter(value, index, s=65, color=color, edgecolor="white", linewidth=0.8, zorder=3)
        axz.annotate(
            f"{event_label(row)}  Σ={value:.3f} keV\n主像素 {row['dominant_channel']}={float(row['dominant_channel_keV']):.3f}",
            (value, index),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=9.0,
        )
    axz.set_xlim(ZOOM_LOW, ZOOM_HIGH)
    axz.set_ylim(-0.8, max(3.7, len(zoom) - 0.2))
    axz.set_yticks([])
    axz.set_xlabel("跨像素离线能量和 (keV)")
    axz.set_title("B  511 keV 邻域逐事例放大", loc="left", fontweight="bold")
    axz.text(
        0.04,
        0.05,
        f"黄色窄带：[510.58, 511.42) keV\n落入 ROI 的离线和：{len(roi)} 个事例",
        transform=axz.transAxes,
        fontsize=10.5,
        va="bottom",
        bbox={"facecolor": "white", "edgecolor": "#BBBBBB", "boxstyle": "round,pad=0.35", "alpha": 0.92},
    )

    # Stacked allocation for every event in the diagnostic band.  The six largest
    # channels are explicit; the rest remain exactly enumerated in the output CSV.
    palette = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#B279A2"]
    y_positions = np.arange(len(zoom))
    for y, row in zip(y_positions, zoom):
        head, tail, tail_energy = compact_allocation(by_event[int(row["event_order"])], keep=6)
        left = 0.0
        for rank, component in enumerate(head):
            width = float(component["combined_channel_keV"])
            axb.barh(y, width, left=left, height=0.56, color=palette[rank], edgecolor="white", linewidth=0.7)
            if width >= 16:
                axb.text(left + width / 2, y, str(component["channel"]), ha="center", va="center", fontsize=8.5, color="white", fontweight="bold")
            left += width
        if tail_energy > 0:
            axb.barh(y, tail_energy, left=left, height=0.56, color="#B8B8B8", edgecolor="white", linewidth=0.7)

        allocation_lines = [f"{component['channel']} {float(component['combined_channel_keV']):.3f}" for component in head]
        if tail:
            allocation_lines.append(f"其余 {len(tail)} 像素 {tail_energy:.3f}")
        axb.text(
            560,
            y,
            "  |  ".join(allocation_lines),
            ha="left",
            va="center",
            fontsize=8.2,
            color="#222222",
        )
    axb.axvline(511.0, color="#8C5A00", lw=1.0, ls="--")
    axb.set_xlim(0, 980)
    axb.set_yticks(y_positions, [f"{event_label(row)}\nΣ={float(row['event_sum_keV']):.3f}" for row in zoom])
    axb.invert_yaxis()
    axb.set_xlabel("像素能量堆叠 (keV)；右侧列出前 6 个层号:像素号及其能量")
    axb.set_title("C  480–550 keV 离线和事例的像素分配", loc="left", fontweight="bold")
    axb.text(
        0.99,
        0.03,
        "灰色 = 其余小分量；全部像素号见 single_pixel_combined_all86.csv",
        transform=axb.transAxes,
        ha="right",
        va="bottom",
        fontsize=9,
        color="#555555",
    )

    fig.suptitle(
        "SH3 中子事例的多像素离线能量和（86 个 BGO<50 keV 且 Si>0 事例）\n"
        "候选 C 的声子通道分配采用 5×8192 packet 均值；这不是单像素触发能量",
        fontsize=15,
        fontweight="bold",
    )
    for suffix in ("png", "pdf"):
        fig.savefig(path_stem.with_suffix(f".{suffix}"), bbox_inches="tight")
    plt.close(fig)
    return {
        "strict_event_sum_keV": {"q50": percentile(strict_sum, 50), "q90": percentile(strict_sum, 90), "q99": percentile(strict_sum, 99), "max": max(strict_sum)},
        "all86_event_sum_keV": {"q50": percentile(all_sum, 50), "q90": percentile(all_sum, 90), "q99": percentile(all_sum, 99), "max": max(all_sum)},
        "events_in_480_550": len(zoom),
        "events_in_roi": len(roi),
        "zoom_events": [
            {
                "event_order": int(row["event_order"]),
                "candidate": row["candidate"],
                "event_sum_keV": float(row["event_sum_keV"]),
                "dominant_channel": row["dominant_channel"],
                "dominant_channel_keV": float(row["dominant_channel_keV"]),
                "strict": bool(int(row["strict_recoil_event"])),
            }
            for row in zoom
        ],
    }


def strict_recoil_stats() -> dict[str, float | int]:
    values = [float(row["si_elastic_recoil_keV"]) for row in read_csv(STRICT_RECOILS)]
    return {
        "count": len(values),
        "min": min(values),
        "q50": percentile(values, 50),
        "q90": percentile(values, 90),
        "q99": percentile(values, 99),
        "max": max(values),
    }


def write_report(manifest: dict[str, object]) -> None:
    raw = manifest["strict_recoil_spectrum_10m"]
    single = manifest["single_pixel"]
    summed = manifest["multipixel_event_sum"]
    single_zoom = single["zoom_channels"]
    event_zoom = summed["zoom_events"]

    lines = [
        "# SH3 中子反冲主要影响能段：单像素与多像素求和",
        "",
        "## 一句话结论",
        "",
        "中子当然能在本探测器中产生可见 TES 信号，但 **本次 10^7 入射样本没有一个实际单像素输入落入 `[510.58, 511.42)` keV 的 511 keV 窄窗**。唯一落入该窄窗的是候选 C 的 **跨像素、跨层离线能量和**；它由多个独立 TES 通道组成，不能当作一个 511 keV 单像素热脉冲。",
        "",
        "## 1. 上游严格 Si 弹性反冲本身的能段",
        "",
        f"10^7 中子输运中有 {raw['count']} 个严格 Si 弹性反冲事例。Si 弹性反冲能量：最小 {raw['min']:.3f} keV，中位数 {raw['q50']:.3f} keV，90% 分位 {raw['q90']:.3f} keV，99% 分位 {raw['q99']:.3f} keV，最大 {raw['max']:.3f} keV。",
        "",
        "因此主要影响低能至百 keV 区间；约 1% 的长尾可以延伸到 0.5 MeV 以上。这回答的是材料中的反冲能谱，还不是单个 TES 的读出能量。",
        "",
        "## 2. 单像素统计",
        "",
        "口径：对 86 个 BGO<50 keV 且 Si>0 的事例，将同一 `Lx:Py` 中的 Ta/TES 直接沉积与 G4CMP 收集声子相加；每个事例取最大的一个实际 TES 通道。",
        "",
        f"严格反冲 51 事例的最大单像素能量中位数为 {single['strict_dominant_pixel_keV']['q50']:.3f} keV，90% 分位 {single['strict_dominant_pixel_keV']['q90']:.3f} keV，99% 分位 {single['strict_dominant_pixel_keV']['q99']:.3f} keV。全部 86 事例中有 {single['single_channels_in_480_550']} 个独立像素位于 480–550 keV，但 511 keV 窄窗内为 {single['single_channels_in_roi']}。即使额外施加 0.42 keV FWHM 的理想高斯读出展宽，86 个事例的 ROI 期望泄漏也只有 {single['gaussian_expected_roi_count_for_86_events']:.3e}，几乎全部来自 `E20 / L4:P104 = 509.989 keV`。",
        "",
        "480–550 keV 的独立像素：",
        "",
        "| 事例 | 严格反冲 | 像素 | 单像素能量 (keV) |",
        "|---:|:---:|:---:|---:|",
    ]
    for row in single_zoom:
        lines.append(f"| E{row['event_order']} | {'是' if row['strict'] else '否'} | {row['channel']} | {row['energy_keV']:.6f} |")
    lines += [
        "",
        "## 3. 多像素离线求和",
        "",
        "口径：把同一中子事例的所有 `Lx:Py` 通道相加。这个量可用于事后事件关联、跨层拓扑和反巧合研究，**不是一个 TES 像素会产生的脉冲能量**。",
        "",
        f"严格反冲 51 事例的离线和中位数为 {summed['strict_event_sum_keV']['q50']:.3f} keV，90% 分位 {summed['strict_event_sum_keV']['q90']:.3f} keV，99% 分位 {summed['strict_event_sum_keV']['q99']:.3f} keV。480–550 keV 有 {summed['events_in_480_550']} 个事例；511 keV 窄窗有 {summed['events_in_roi']} 个。",
        "",
        "| 事例 | 候选 | 严格反冲 | 离线和 (keV) | 最大像素 | 最大像素能量 (keV) |",
        "|---:|:---:|:---:|---:|:---:|---:|",
    ]
    for row in event_zoom:
        lines.append(
            f"| E{row['event_order']} | {row['candidate'] or '—'} | {'是' if row['strict'] else '否'} | "
            f"{row['event_sum_keV']:.6f} | {row['dominant_channel']} | {row['dominant_channel_keV']:.6f} |"
        )
    lines += [
        "",
        "候选 C 的总和接近 511 keV，是因为 `L1:P231=433.544 keV`、`L1:P147=24.848 keV` 与 L0 上许多声子收集通道相加；其中任何一个单像素都不在 511 keV 窄窗。",
        "",
        "## 4. 模型边界",
        "",
        "- G4CMP 端点采用 `tuned_c_area0p12` 比较性场景（sensor area scale 0.12、sensor absorption 0.3、bath absorption 0.1、diffuse、62 meV packet）。它尚未用实测界面参数标定，因此只用于通道分配与敏感性判断，不是绝对探测效率预测。",
        "- 候选 C 使用 5 次独立的 8192 packet 运行之通道均值；其他 85 个事例使用一次全 86 运行。",
        "- 图中 0.42 keV 是制图报告阈值（等于当前采用的 511 keV FWHM），不是宣称的硬件触发阈值。CSV 保留全部正能量通道。",
        "- 本结论只针对当前 10^7 入射统计量；零个单像素 ROI 事件不等于严格数学上的零概率。",
        "",
        "## 5. 可复现产物",
        "",
        "- `sh3_neutron_single_pixel_spectrum.png/.pdf`：单像素能谱及 ROI 放大。",
        "- `sh3_neutron_multipixel_sum_spectrum.png/.pdf`：跨像素离线和及像素分配。",
        "- `single_pixel_combined_all86.csv`：全部通道的直接沉积、G4CMP 声子与合计。",
        "- `multipixel_event_sums_all86.csv`：逐事例离线和与完整像素分配字符串。",
        "- `NEUTRON_ENERGY_BAND_EVALUATION.json`：输入哈希、统计量和绘图口径。",
        "",
    ]
    (OUT / "NEUTRON_ENERGY_BAND_EVALUATION.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    configure_plotting()
    events = load_event_metadata()
    direct, sensor, c_order = load_channel_components(events)
    channel_rows, event_rows, by_event = make_rows(events, direct, sensor, c_order)
    reference_validation = validate_against_all86_reference(event_rows, c_order)

    channel_csv = OUT / "single_pixel_combined_all86.csv"
    event_csv = OUT / "multipixel_event_sums_all86.csv"
    write_csv(channel_csv, channel_rows)
    write_csv(event_csv, event_rows)

    single = plot_single_pixel(event_rows, channel_rows, OUT / "sh3_neutron_single_pixel_spectrum")
    summed = plot_event_sum(event_rows, by_event, OUT / "sh3_neutron_multipixel_sum_spectrum")
    manifest = {
        "schema_version": 1,
        "scope": "86 BGO<50 keV, Si-positive SH3 neutron events from 10^7 incident-neutron transport",
        "sample_livetime_s": SAMPLE_LIVETIME_S,
        "roi_keV": {"low_inclusive": ROI_LOW, "high_exclusive": ROI_HIGH},
        "diagnostic_band_keV": [ZOOM_LOW, ZOOM_HIGH],
        "reporting_threshold_keV_not_hardware_trigger": REPORTING_THRESHOLD_KEV,
        "strict_recoil_spectrum_10m": strict_recoil_stats(),
        "single_pixel": single,
        "multipixel_event_sum": summed,
        "candidate_C_event_order": c_order,
        "all86_event_sum_reference_validation": reference_validation,
        "g4cmp_model": {
            "status": "comparative uncalibrated endpoint; not an absolute detector-efficiency prediction",
            "all86_scenario": "tuned_c_area0p12",
            "candidate_C_sensor_allocation": "arithmetic mean of five independent 8192-packet replicates, including zeros",
            "other_85_sensor_allocation": "single accepted all86 run",
        },
        "inputs": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in [EVENT_HITS, DIRECT, ALL86_CHANNELS, ALL86_EVENTS, STRICT_RECOILS, *REPLICATE_CHANNELS]
        },
        "plotting_code_sha256": sha256(Path(__file__)),
        "outputs": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in [
                channel_csv,
                event_csv,
                OUT / "sh3_neutron_single_pixel_spectrum.png",
                OUT / "sh3_neutron_single_pixel_spectrum.pdf",
                OUT / "sh3_neutron_multipixel_sum_spectrum.png",
                OUT / "sh3_neutron_multipixel_sum_spectrum.pdf",
            ]
        },
    }
    manifest_path = OUT / "NEUTRON_ENERGY_BAND_EVALUATION.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_report(manifest)

    print(json.dumps({
        "single_pixel": single,
        "multipixel_event_sum": summed,
        "strict_recoil_spectrum_10m": manifest["strict_recoil_spectrum_10m"],
        "candidate_C_event_order": c_order,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
