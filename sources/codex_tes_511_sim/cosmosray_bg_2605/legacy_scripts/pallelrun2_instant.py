#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import subprocess
from pathlib import Path
from multiprocessing import Pool
import datetime
import re
from typing import Dict, Tuple, List

# ================= 配置区 =================
SOURCE_DIR = "megalib_sources_v2"                 # 每个粒子一个 .source
OUT_DIR = Path("mixed_parallel_instant")  # 新目录避免覆盖
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 并行 worker（你说 20）
N_WORKERS = 20

# gamma 基准
GAMMA_EVENTS = 10_000_000
GAMMA_SPLITS = 4          # gamma 拆 4 份 -> 每份 2,000,000

# 非伽马：做 8 个 replica（每个 replica 的 TT 与 gamma 相同）
NON_GAMMA_REPLICAS = 8

# 日志：只给一个 job 写 log（默认 gamma 的第 1 份）
LOG_ONLY_TAG = "gamma"
LOG_ONLY_REP = 1
LOG_ONLY_PART = 1
SILENT_OTHERS = True

# 输出 isotope 文件（build-up 模式下通常会有 TT/RP/VN 等）
# 注意：是否真的写出 RP/VN 取决于你的 cosima/源文件开关
FORCE_STORE_ISOTOPES = True
WRITE_ISOTOPE_FILE = True

# =========================================

TT_RE = re.compile(r"^\s*TT\s+([-\d.]+)\s*$")

def get_source_total_flux(file_path: str) -> float:
    """
    统计 .source 里所有 '.Flux' 行的和（你之前就是这么做的）
    """
    total_flux = 0.0
    with open(file_path, "r") as f:
        for line in f:
            if ".Flux" in line:
                try:
                    total_flux += float(line.split()[-1])
                except Exception:
                    continue
    return total_flux

def get_particle_tag_from_filename(sf: str) -> str:
    # Background_gamma_96deg.source -> gamma
    stem = Path(sf).stem
    parts = stem.split("_")
    return parts[1] if len(parts) >= 2 else stem

def split_events(total: int, n_parts: int) -> List[int]:
    n_parts = max(1, int(n_parts))
    base = total // n_parts
    rem = total % n_parts
    chunks = [base + (1 if i < rem else 0) for i in range(n_parts)]
    return [c for c in chunks if c > 0]

def patch_source_for_job(src_path: str, dst_path: Path, events: int,
                         file_prefix_abs: str, iso_prefix_abs: str):
    """
    修改后的功能：
    - 改 .Events
    - 改 .FileName
    - 改 .IsotopeProductionFile
    - **删除 DecayMode 行以关闭实时衰变**
    """
    seen_store_isotopes = False
    seen_isofile = False
    run_name = None

    with open(src_path, "r") as f0:
        for l in f0:
            s = l.strip()
            if s.startswith("Run "):
                toks = s.split()
                if len(toks) >= 2:
                    run_name = toks[1]
                break

    with open(src_path, "r") as fin, open(dst_path, "w", newline="\n") as fout:
        for line in fin:
            s = line.strip()

            # --- 关键修改：跳过（删除）DecayMode 行 ---
            if s.startswith("DecayMode"):
                continue 

            # 强制 StoreIsotopes (保留这个可以让你在 .dat 里看到产率 RP，但不会在模拟中衰变)
            if s.startswith("StoreIsotopes"):
                seen_store_isotopes = True
                if FORCE_STORE_ISOTOPES:
                    fout.write("StoreIsotopes true\n")
                else:
                    fout.write(line)
                continue

            # patch RunName.Events
            if ".Events" in line:
                prefix = line.split(".Events")[0].strip()
                fout.write(f"{prefix}.Events {int(events)}\n")
                continue

            # patch RunName.FileName
            if ".FileName" in line:
                prefix = line.split(".FileName")[0].strip()
                fout.write(f"{prefix}.FileName {file_prefix_abs}\n")
                continue

            # patch RunName.IsotopeProductionFile
            if ".IsotopeProductionFile" in line:
                seen_isofile = True
                if WRITE_ISOTOPE_FILE:
                    prefix = line.split(".IsotopeProductionFile")[0].strip()
                    fout.write(f"{prefix}.IsotopeProductionFile {iso_prefix_abs}\n")
                continue

            fout.write(line)

        if FORCE_STORE_ISOTOPES and (not seen_store_isotopes):
            fout.write("\nStoreIsotopes true\n")
        if WRITE_ISOTOPE_FILE and (not seen_isofile) and (run_name is not None):
            fout.write(f"{run_name}.IsotopeProductionFile {iso_prefix_abs}\n")
def run_cosima_worker(args):
    """
    args = (source_file_abs, events, tag, rep_index, part_index)
    """
    source_file, events, tag, rep_index, part_index = args
    if events <= 0:
        return

    job_name = f"{Path(source_file).stem}_rep{rep_index:02d}_part{part_index:02d}"
    sim_prefix = str((OUT_DIR / job_name).absolute())
    iso_prefix = str((OUT_DIR / (job_name + ".dat")).absolute())

    temp_source = OUT_DIR / f"temp_{tag}_rep{rep_index:02d}_part{part_index:02d}.source"
    patch_source_for_job(source_file, temp_source, events, sim_prefix, iso_prefix)

    cmd = ["cosima", str(temp_source.absolute())]

    do_log = (tag == LOG_ONLY_TAG and rep_index == LOG_ONLY_REP and part_index == LOG_ONLY_PART)
    log_file_path = OUT_DIR / f"log_{tag}_rep{rep_index:02d}_part{part_index:02d}.txt"

    if do_log:
        print(f"🧵 [RUN] {tag:8} rep={rep_index:02d} part={part_index:02d} events={events:,}  (log={log_file_path.name})")
        with open(log_file_path, "w") as logf:
            logf.write(f"=== Simulation Started at {datetime.datetime.now()} ===\n")
            logf.write(f"Source: {source_file}\n")
            logf.write(f"Allocated Events: {events}\n")
            logf.write(f"JobName: {job_name}\n")
            logf.write(f"FORCE_STORE_ISOTOPES={FORCE_STORE_ISOTOPES}  WRITE_ISOTOPE_FILE={WRITE_ISOTOPE_FILE}\n")
            logf.write("-" * 70 + "\n\n")
            subprocess.run(cmd, cwd=str(OUT_DIR), stdout=logf, stderr=subprocess.STDOUT)
            logf.write("\n" + "-" * 70 + "\n")
            logf.write(f"=== Simulation Finished at {datetime.datetime.now()} ===\n")
    else:
        if SILENT_OTHERS:
            with open(os.devnull, "w") as dn:
                subprocess.run(cmd, cwd=str(OUT_DIR), stdout=dn, stderr=subprocess.STDOUT)
        else:
            subprocess.run(cmd, cwd=str(OUT_DIR))

    try:
        temp_source.unlink()
    except Exception:
        pass

def main():
    
    source_files = glob.glob(f"{SOURCE_DIR}/*.source")
    if not source_files:
        print(f"❌ 错误：在 {SOURCE_DIR} 中没有找到 .source 文件！")
        return

    # tag -> (sf_abs, flux)
    flux_map: Dict[str, Tuple[str, float]] = {}
    for sf in source_files:
        tag = get_particle_tag_from_filename(sf)
        flux_map[tag] = (os.path.abspath(sf), get_source_total_flux(sf))

    if "gamma" not in flux_map:
        print("❌ 错误：没找到 gamma 的 .source（形如 Background_gamma_96deg.source）")
        print("   现有 tag：", sorted(flux_map.keys()))
        return

    gamma_sf, gamma_flux = flux_map["gamma"]
       # === 在 main() 结尾添加以下代码 ===
    
    # 1. 计算伽马的归一化系数 (Counts -> Counts/s)
    # 逻辑：Factor = Flux / Total_Events
    gamma_factor = gamma_flux / GAMMA_EVENTS
    
    # 2. 考虑非伽马粒子的副本 (Replica) 影响
    # 因为非伽马粒子跑了 NON_GAMMA_REPLICAS 次实验，
    # 如果你把所有 .sim.gz 放在一起算，等效时间增加了，系数就要除以副本数。
    non_gamma_factor = gamma_factor / NON_GAMMA_REPLICAS

    print("\n" + "="*60)
    print("📊 [归一化系数报告 / Normalization Report]")
    print(f"  伽马通量 (Gamma Flux):      {gamma_flux:.6e} s^-1")
    print(f"  伽马总事件 (Gamma Events):  {GAMMA_EVENTS:,}")
    print("-" * 30)
    print(f"  ⭐ 归一化系数 (适用单个文件/单一实验):")
    print(f"     Norm Factor = {gamma_factor:.6e}")
    print("")
    print(f"  ⭐ 归一化系数 (如果你合并了所有 {NON_GAMMA_REPLICAS} 个非伽马副本进行分析):")
    print(f"     Non-Gamma Combined Factor = {non_gamma_factor:.6e}")
    print("\n  用法提示：")
    print("  物理计数率 (Counts/s) = 模拟得到的计数 * Norm Factor")
    print("="*60)

    if gamma_flux <= 0:
        print("❌ 错误：gamma 总通量为 0，检查 .source 里是否有 .Flux 行。")
        return

    # 关键：每个非伽马“单次试验”的 events 只做 TT 对齐，不乘 8
    base_events_map: Dict[str, int] = {"gamma": GAMMA_EVENTS}
    for tag, (_, flux) in flux_map.items():
        if tag == "gamma":
            continue
        if flux <= 0:
            base_events_map[tag] = 0
        else:
            base_events_map[tag] = int(round((flux / gamma_flux) * GAMMA_EVENTS))

    # 生成 jobs：
    jobs = []

    # gamma -> 4 份，rep=1（只做一次）
    gamma_chunks = split_events(GAMMA_EVENTS, GAMMA_SPLITS)
    for i, ev in enumerate(gamma_chunks, start=1):
        jobs.append((gamma_sf, ev, "gamma", 1, i))

    # non-gamma -> 每个 tag 做 8 个 replica，每个 replica 1 份（你要的“一个线程一个权重/一次实验”）
    for tag, (sf, _) in flux_map.items():
        if tag == "gamma":
            continue
        ev_base = base_events_map.get(tag, 0)
        if ev_base <= 0:
            continue
        for rep in range(1, NON_GAMMA_REPLICAS + 1):
            jobs.append((sf, ev_base, tag, rep, 1))

    # 打印计划
    print("\n📊 事件数计划（buildup 保留；非伽马用 replica=8 代替 ×8 权重）")
    print(f" - gamma: total={GAMMA_EVENTS:,} splits={GAMMA_SPLITS} -> {gamma_chunks}")
    for tag in sorted(base_events_map.keys()):
        if tag == "gamma":
            continue
        evb = base_events_map[tag]
        if evb > 0:
            rel = flux_map[tag][1] / gamma_flux
            print(f" - {tag:8}: base_events(replica)= {evb:,}  rel_flux={rel:.6f}  replicas={NON_GAMMA_REPLICAS}  total={evb*NON_GAMMA_REPLICAS:,}")

    print(f"\n✅ jobs={len(jobs)}  workers={N_WORKERS}  OUT={OUT_DIR}/")
    print("🚀 启动并行 cosima ...")

    with Pool(processes=N_WORKERS) as p:
        list(p.imap_unordered(run_cosima_worker, jobs))

    print("\n✅ 全部完成。你会得到：")
    print("   - *.sim.gz（含 IA/HTsim 等）")
    if WRITE_ISOTOPE_FILE:
        print("   - *.dat（isotope store：TT/RP/VN 等——具体字段取决于你的 cosima/源文件开关）")
 
if __name__ == "__main__":
    main()
