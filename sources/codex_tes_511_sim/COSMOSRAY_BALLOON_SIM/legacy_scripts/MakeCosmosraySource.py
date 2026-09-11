#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import numpy as np
from pathlib import Path

# ================= 配置区 =================
INPUT_DIR = "particle_source"
OUTPUT_DIR = "megalib_sources_v2"
GEO_FILE = "/home/ubuntu/cosmosray_bg_2605/XZTES/TibetTES_v5_6layers.geo.setup"

# 1. 修正后的粒子映射 (严格匹配 MCSource.cc)
PARTICLE_MAP = {
    "n": 6,          # Neutron = 6
    "p": 4,          # Proton = 4
    "alpha": 21,     # Alpha = 21
    "muplus": 8,     # MuonPlus = 8
    "muminus": 9,    # MuonMinus = 9
    "eminus": 3,     # Electron = 3
    "eplus": 2,      # Positron = 2
    "gamma": 1       # Gamma = 1
}

# 2. 角度分段配置
SAMPLING_POINTS = [19.13, 33.45, 43.63, 52.16, 59.80, 66.89, 73.62, 80.12, 86.49, 92.83]
BOUNDARIES = [
    (0.00, 27.18), (27.18, 38.82), (38.82, 48.04), (48.04, 56.07), (56.07, 63.40),
    (63.40, 70.29), (70.29, 76.89), (76.89, 83.32), (83.32, 89.66), (89.66, 96.00)
]

THETA_MAX = np.radians(96.0)
TOTAL_SOLID_ANGLE = 2 * np.pi * (1 - np.cos(THETA_MAX))
BIN_OMEGA = TOTAL_SOLID_ANGLE / 10.0

# ================= 处理逻辑 =================

def convert_to_dp_and_calc_flux(raw_path, out_dir, p_tag, bin_idx):
    points = []
    if not os.path.exists(raw_path): return None, 0
    
    with open(raw_path, "r") as f:
        for line in f:
            if not line.strip() or line.lstrip().startswith(("#", "Energy")): continue
            parts = line.split()
            if len(parts) >= 2: points.append((float(parts[0]), float(parts[1])))
    
    if not points: return None, 0
    points.sort(key=lambda x: x[0])
    
    # 能量积分计算绝对 Flux
    energy_integral = 0.0
    for i in range(len(points) - 1):
        energy_integral += (points[i][1] + points[i+1][1]) * (points[i+1][0] - points[i][0]) / 2.0
    
    abs_flux = energy_integral * BIN_OMEGA

    # 输出 DP 文件
    new_filename = f"fixed_{p_tag}_bin{bin_idx}.dat"
    new_path = Path(out_dir) / new_filename
    with open(new_path, "w", newline='\n') as w:
        w.write("IP LIN\n")
        for e, fl in points: w.write(f"DP {e:.10e} {fl:.10e}\n")
            
    return new_path.absolute(), abs_flux

def main():
    out_path = Path(OUTPUT_DIR).absolute()
    out_path.mkdir(exist_ok=True)

    for p_token, p_id in PARTICLE_MAP.items():
        source_name = f"Background_{p_token}_96deg"
        components = []
        
        for i, center_angle in enumerate(SAMPLING_POINTS):
            match_file = Path(INPUT_DIR) / f"spectrum_{p_token}_zen{center_angle:g}.dat"
            if match_file.exists():
                dat_abs, flux = convert_to_dp_and_calc_flux(match_file, out_path, p_token, i+1)
                if dat_abs: components.append((BOUNDARIES[i], dat_abs, flux, i+1))
        
        if not components: continue

        source_file = out_path / f"{source_name}.source"
        with open(source_file, "w", newline='\n') as w:
            # --- 全局参数区 ---
            w.write(f"Geometry {GEO_FILE}\n")
            w.write("PhysicsListHD qgsp-bic-hp\n") # 高精度中子物理
            w.write("PhysicsListEM LivermorePol\n")
            w.write("StoreSimulationInfo all\n")
            w.write("StoreIsotopes true\n")         # 记录核素
            w.write("DecayMode ActivationBuildUp\n") # 开启累积致活
            w.write("DetectorTimeConstant 1e-9\n")
            w.write("Seed 12345\n\n")

            w.write(f"Run {source_name}\n")
            w.write(f"{source_name}.Events 1000000\n") # 建议增加事件数
            w.write(f"{source_name}.FileName {source_name}\n")
            # 记录产生的核素文件路径
            w.write(f"{source_name}.IsotopeProductionFile {source_name}.isotopes\n\n")

            for (t1, t2), dat, flux, idx in components:
                c_id = f"C_{p_token}_{idx}"
                w.write(f"{source_name}.Source {c_id}\n")
                w.write(f"{c_id}.ParticleType {p_id}\n")
                w.write(f"{c_id}.Beam FarFieldAreaSource {t1:.2f} {t2:.2f} 0 360\n")
                w.write(f"{c_id}.Spectrum File {dat}\n")
                w.write(f"{c_id}.Flux {flux:.10e}\n\n")
        
        print(f" ✅ 已生成包含致活信息的源: {source_file.name}")

if __name__ == "__main__":
    main()
