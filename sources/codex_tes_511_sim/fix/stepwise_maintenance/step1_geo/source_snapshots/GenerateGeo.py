#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""generategeosd2_all_sd.py

在你现有 generategeosd2.py 的基础上“只做添加、不删除不改动核心几何数值/放置逻辑”，
增强两件事：

1) det 文件里给更多体积添加 SD（尤其是 Cryo_Shell、Substrate、TES_L 容器、Windows、CollimatorVac），
   这样后续在 .sim/.dat 里更容易做 VN/RP/IA 的对齐、也更容易做 sanity/debug。

2) bounds：除了终端 print GEOM_BOUNDS 外，额外把同一份 bounds 写入 OUTDIR/bounds.json，
   并补充 WINDOWS/SUBSTRATES 等解析条件，便于后处理脚本直接加载。

注意：
- 这里仍然保持你原有参数与几何构造方式；
- 设计参数沿用历史 mm-like 数值；输出给 MEGAlib/Cosima 的所有长度统一换算为 cm；
- 只新增 detector 定义与 bounds 字段，不删除任何已有条目。
"""

import math
import json
from pathlib import Path

OUTDIR = Path(__file__).resolve().parent
LENGTH_SCALE_TO_CM = 0.1
SOURCE_TOP_Z_DESIGN = 127.66
SOURCE_RADIUS_DESIGN = 18.0


def to_cm(x: float) -> float:
    return float(x) * LENGTH_SCALE_TO_CM


def fmt(x: float) -> str:
    return f"{x:.6f}".rstrip("0").rstrip(".")


def write_text(path: Path, s: str):
    path.write_text(s, encoding="utf-8")
    print(f"[OK] wrote {path}")


# --- 几何定义辅助函数 (保持原样) ---

def pcon_shape_line(phi0_deg: float, dphi_deg: float, planes):
    toks = ["PCON", fmt(phi0_deg), fmt(dphi_deg), str(len(planes))]
    for (z, rmin, rmax) in planes:
        toks += [fmt(to_cm(z)), fmt(to_cm(rmin)), fmt(to_cm(rmax))]
    return " ".join(toks)


def volume_def(volname: str, material: str, shape_line: str, vis: int = 1) -> str:
    return (
        f"Volume {volname}\n"
        f"{volname}.Material {material}\n"
        f"{volname}.Visibility {vis}\n"
        f"{volname}.Shape {shape_line}\n\n"
    )


def place(volname: str, x: float, y: float, z: float, mother: str, vis=None) -> str:
    s = (
        f"{volname}.Position {fmt(to_cm(x))} {fmt(to_cm(y))} {fmt(to_cm(z))}\n"
        f"{volname}.Mother {mother}\n"
    )
    if vis is not None:
        s += f"{volname}.Visibility {vis}\n"
    return s + "\n"


def pcon_cylinder_def(volname: str, material: str, rmax: float, halfz: float, vis: int = 1) -> str:
    planes = [(-halfz, 0.0, rmax), (halfz, 0.0, rmax)]
    return volume_def(volname, material, pcon_shape_line(0.0, 360.0, planes), vis)


def brik_def(volname: str, material: str, hx: float, hy: float, hz: float, vis: int = 1) -> str:
    return volume_def(volname, material, f"BRIK {fmt(to_cm(hx))} {fmt(to_cm(hy))} {fmt(to_cm(hz))}", vis)


def polycone_shell_def(
    volname: str,
    material: str,
    r_out: float,
    z_out_bot: float,
    z_out_top: float,
    r_in: float,
    z_in_bot: float,
    z_in_top: float,
    hole_r_top: float,
    vis: int = 1,
) -> str:
    z_planes = [z_out_bot, z_in_bot, z_in_bot, z_in_top, z_in_top, z_out_top]
    rmin = [0.0, 0.0, r_in, r_in, hole_r_top, hole_r_top]
    rmax = [r_out] * len(z_planes)
    planes = list(zip(z_planes, rmin, rmax))
    return volume_def(volname, material, pcon_shape_line(0.0, 360.0, planes), vis)


def polycone_shell_w_topseat_def(
    volname: str,
    material: str,
    r_out: float,
    z_out_bot: float,
    z_out_top: float,
    r_in: float,
    z_in_bot: float,
    z_in_top: float,
    hole_r_top: float,
    seat_h: float,
    vis: int = 1,
) -> str:
    seat_h = max(0.0, float(seat_h))
    z_cone_start = z_out_top - seat_h
    if z_cone_start <= z_in_top + 1e-6:
        z_cone_start = z_out_top
    z_planes = [z_out_bot, z_in_bot, z_in_bot, z_in_top, z_cone_start, z_out_top]
    rmin = [0.0, 0.0, r_in, r_in, hole_r_top, hole_r_top]
    rmax = [r_out] * len(z_planes)
    planes = list(zip(z_planes, rmin, rmax))
    return volume_def(volname, material, pcon_shape_line(0.0, 360.0, planes), vis)


def add_collimator_grid(
    geo,
    *,
    R,
    thick,
    hole,
    web,
    z_center,
    mother="WorldVolume",
    vac_name="CollimatorVac",
    barx="CollBarX",
    bary="CollBarY",
    vis_vac=0,
    vis_bar=1,
):
    pitch, hz = hole + web, thick / 2.0
    vac_hx, vac_hy = R + pitch, R + pitch
    bar_len_x, bar_len_y = 2 * vac_hx, 2 * vac_hy
    geo.append(brik_def(vac_name, "Vacuum", vac_hx, vac_hy, hz, vis=vis_vac))
    geo.append(place(vac_name, 0, 0, z_center, mother, vis=vis_vac))
    geo.append(brik_def(barx, "W", bar_len_x / 2.0, web / 2.0, hz, vis=vis_bar))
    geo.append(brik_def(bary, "W", web / 2.0, bar_len_y / 2.0, hz, vis=vis_bar))
    n, idx = int(math.ceil(R / pitch)) + 2, 0
    for k in range(-n, n + 1):
        pos = (k + 0.5) * pitch
        if abs(pos) > R:
            continue
        geo.append(f"{barx}.Copy {barx}_{idx:04d}\n")
        geo.append(place(f"{barx}_{idx:04d}", 0, pos, 0, vac_name, vis=vis_bar))
        geo.append(f"{bary}.Copy {bary}_{idx:04d}\n")
        geo.append(place(f"{bary}_{idx:04d}", pos, 0, 0, vac_name, vis=vis_bar))
        idx += 1


def det_add_mdcal(
    det_lines,
    det_name,
    sens_vol,
    det_vol,
    pitch_xyz,
    offset_xyz=(0, 0, 0),
    thr=0.001,
    eres_sigma=1.0,
):
    px, py, pz = pitch_xyz
    ox, oy, oz = offset_xyz
    det_lines.append(
        f"MDCalorimeter {det_name}\n"
        f"{det_name}.SensitiveVolume {sens_vol}\n"
        f"{det_name}.DetectorVolume {det_vol}\n"
        f"{det_name}.StructuralPitch {fmt(to_cm(px))} {fmt(to_cm(py))} {fmt(to_cm(pz))}\n"
        f"{det_name}.StructuralOffset {fmt(to_cm(ox))} {fmt(to_cm(oy))} {fmt(to_cm(oz))}\n"
        f"{det_name}.TriggerThreshold {fmt(thr)} 0.0\n"
        f"{det_name}.EnergyResolution Gauss {fmt(thr)} {fmt(thr)} {fmt(eres_sigma)}\n"
        f"{det_name}.EnergyResolution Gauss 3000 3000 {fmt(eres_sigma)}\n\n"
    )


def det_add_scint(det_lines, det_name, sens_vol, det_vol, thr=0.001, eres_sigma=1.0):
    det_lines.append(
        f"Scintillator {det_name}\n"
        f"{det_name}.SensitiveVolume {sens_vol}\n"
        f"{det_name}.DetectorVolume {det_vol}\n"
        f"{det_name}.TriggerThreshold {fmt(thr)}\n"
        f"{det_name}.EnergyResolution Gauss {fmt(thr)} {fmt(thr)} {fmt(eres_sigma)}\n"
        f"{det_name}.EnergyResolution Gauss 3000 3000 {fmt(eres_sigma)}\n\n"
    )


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    # ---------- Parameters (完全复刻你的数值) ----------
    W_TOP_CONE_SEAT_H, COLL_CLEARANCE, CONTACT_GAP, POLE_R, RAD_EPS, N_LAYERS = (
        2.0,
        0.8,
        0.01,
        2.0,
        0.02,
        6,
    )
    cu_h, sub_h = 5.0, 0.3
    eff_r, sub_r, hole_r = 18.0, 19.0, 19.0
    n_pix, pix_x, pix_y, pix_z = 20, 1.5, 1.5, 3.0
    gap_pix, pitch = 0.05, 1.5 + 0.05
    coll_thick, coll_hole, coll_web = 1.0, 1.42, 0.13
    coll_pitch = coll_hole + coll_web
    gap, r_cu = 1.0, 30.0
    nb_wall, w_wall, cryo_wall = 3.0, 5.0, 2.0
    bgo_side_wall, bgo_bot_wall, bgo_top_wall = 20.0, 50.0, 20.0
    shell_wall = 2.0
    th_win_nb, th_win_w, th_win_cryo, th_win_be = 0.01, 0.01, 0.01, 0.15
    TES_LAYER_PITCH = 12.0

    z_cu_top, z_sub_center0 = 0.0, 10.0
    z_sub_centers = [z_sub_center0 + l * TES_LAYER_PITCH for l in range(N_LAYERS)]
    z_tes_centers_world = [zc + sub_h / 2.0 + pix_z / 2.0 for zc in z_sub_centers]
    z_internal_top, z_cu_bot = max(z_tes_centers_world) + 20.0, 0.0 - cu_h

    # 坐标链路定义 (用于边界提取)
    z_nb_in_bot, z_nb_in_top = z_cu_bot - 2.0, z_internal_top
    z_nb_out_bot, z_nb_out_top = z_nb_in_bot - nb_wall, z_nb_in_top + nb_wall
    z_w_in_bot, z_w_in_top = z_nb_out_bot - gap, z_nb_out_top + gap
    z_w_out_bot, z_w_out_top = z_w_in_bot - w_wall, z_w_in_top + w_wall
    z_cryo_in_bot, z_cryo_in_top = z_w_out_bot - gap, z_w_out_top + gap
    z_cryo_out_bot, z_cryo_out_top = z_cryo_in_bot - cryo_wall, z_cryo_in_top + cryo_wall
    z_bgo_in_bot, z_bgo_in_top = z_cryo_out_bot - gap, z_cryo_out_top + gap
    z_bgo_out_bot, z_bgo_out_top = z_bgo_in_bot - bgo_bot_wall, z_bgo_in_top + bgo_top_wall
    z_shell_in_bot, z_shell_in_top = z_bgo_out_bot - gap, z_bgo_out_top + gap
    z_shell_out_bot, z_shell_out_top = z_shell_in_bot - shell_wall, z_shell_in_top + shell_wall

    r_nb_in, r_nb_out = r_cu + 1.0, r_cu + 1.0 + nb_wall
    r_w_in, r_w_out = r_nb_out + gap, r_nb_out + gap + w_wall
    r_cryo_in, r_cryo_out = r_w_out + gap, r_w_out + gap + cryo_wall
    r_bgo_in, r_bgo_out = r_cryo_out + gap, r_cryo_out + gap + bgo_side_wall
    r_shell_in, r_shell_out = r_bgo_out + gap, r_bgo_out + gap + shell_wall

    # --- Cu support pole (center copper pole) ---
    pole_bot_z = z_cu_top + CONTACT_GAP
    pole_top_z = (z_sub_centers[0] - sub_h / 2.0) - CONTACT_GAP
    pole_h = pole_top_z - pole_bot_z
    if pole_h <= 0:
        # should not happen with current geometry, but keep it safe
        pole_h = 0.01

    z_coll_center = z_shell_out_top - th_win_be - COLL_CLEARANCE - coll_thick / 2.0
    pix_xy = [
        (
            -((20 * pitch) / 2.0) + (pitch / 2.0) + i * pitch,
            -((20 * pitch) / 2.0) + (pitch / 2.0) + j * pitch,
        )
        for i in range(20)
        for j in range(20)
        if math.hypot(
            -((20 * pitch) / 2.0) + (pitch / 2.0) + i * pitch,
            -((20 * pitch) / 2.0) + (pitch / 2.0) + j * pitch,
        )
        < eff_r
    ]

    # =========================
    # 生成几何内容 (完全保留复刻)
    # =========================
    geo = ["Include Intro_TibetTES.geo\n\n"]
    geo.append(
        polycone_shell_def(
            "Nb_Shield",
            "Nb",
            r_nb_out,
            z_nb_out_bot,
            z_nb_out_top,
            r_nb_in,
            z_nb_in_bot,
            z_nb_in_top,
            hole_r,
        )
    )
    geo.append(
        polycone_shell_w_topseat_def(
            "W_Shield",
            "W",
            r_w_out,
            z_w_out_bot,
            z_w_out_top,
            r_w_in,
            z_w_in_bot,
            z_w_in_top,
            hole_r,
            W_TOP_CONE_SEAT_H,
        )
    )
    geo.append(
        polycone_shell_def(
            "Cryo_Shell",
            "Aluminium",
            r_cryo_out,
            z_cryo_out_bot,
            z_cryo_out_top,
            r_cryo_in,
            z_cryo_in_bot,
            z_cryo_in_top,
            hole_r,
        )
    )
    geo.append(
        polycone_shell_def(
            "BGO_Shield",
            "BGO",
            r_bgo_out,
            z_bgo_out_bot,
            z_bgo_out_top,
            r_bgo_in,
            z_bgo_in_bot,
            z_bgo_in_top,
            hole_r,
        )
    )
    geo.append(
        polycone_shell_def(
            "Al_Shell",
            "Aluminium",
            r_shell_out,
            z_shell_out_bot,
            z_shell_out_top,
            r_shell_in,
            z_shell_in_bot,
            z_shell_in_top,
            hole_r,
        )
    )
    geo.append(pcon_cylinder_def("Cu_Base", "Copper", r_cu, cu_h / 2.0))
    geo.append(pcon_cylinder_def("Cu_SupportPole", "Copper", POLE_R, pole_h / 2.0))
    for l in range(N_LAYERS):
        geo.append(pcon_cylinder_def(f"Substrate_L{l}", "Silicon", sub_r, sub_h / 2.0))
        geo.append(brik_def(f"TES_Pixel_L{l}", "Ta", 1.5 / 2.0, 1.5 / 2.0, 3.0 / 2.0))
        geo.append(brik_def(f"TES_L{l}", "Vacuum", 39.0, 39.0, 3.0 / 2.0 + 0.1))
    add_collimator_grid(
        geo,
        R=hole_r - RAD_EPS,
        thick=coll_thick,
        hole=coll_hole,
        web=coll_web,
        z_center=z_coll_center,
    )

    # placements（保持你当前版本的精简放置段；若你本地脚本有更多放置，也可直接替换过来）
    geo.append(place("Nb_Shield", 0, 0, 0, "WorldVolume"))
    geo.append(place("W_Shield", 0, 0, 0, "WorldVolume"))
    geo.append(place("Cryo_Shell", 0, 0, 0, "WorldVolume"))
    geo.append(place("BGO_Shield", 0, 0, 0, "WorldVolume"))
    geo.append(place("Al_Shell", 0, 0, 0, "WorldVolume"))
    geo.append(place("Cu_Base", 0, 0, z_cu_bot + cu_h / 2.0, "WorldVolume"))
    geo.append(place("Cu_SupportPole", 0, 0, pole_bot_z + pole_h / 2.0, "WorldVolume"))
    for l in range(N_LAYERS):
        geo.append(place(f"Substrate_L{l}", 0, 0, z_sub_centers[l], "WorldVolume"))
        geo.append(place(f"TES_L{l}", 0, 0, z_tes_centers_world[l], "WorldVolume"))
        for idx, (xw, yw) in enumerate(pix_xy):
            geo.append(f"TES_Pixel_L{l}.Copy TP_L{l}_{idx:05d}\n")
            geo.append(place(f"TP_L{l}_{idx:05d}", xw, yw, 0, f"TES_L{l}", vis=0))

    # Windows (4 layers)  --- 必须先定义 Volume，否则 det 里 SensitiveVolume 会找不到
    geo.append(pcon_cylinder_def("Win_Nb",   "Aluminium",        hole_r - RAD_EPS, th_win_nb/2.0))  
    geo.append(pcon_cylinder_def("Win_W",    "Aluminium",         hole_r - RAD_EPS, th_win_w/2.0))
    geo.append(pcon_cylinder_def("Win_Cryo", "Aluminium", hole_r - RAD_EPS, th_win_cryo/2.0))
    geo.append(pcon_cylinder_def("Win_Be",   "Be",        hole_r - RAD_EPS, th_win_be/2.0))

    geo.append(place("Win_Nb", 0, 0, z_nb_out_top - th_win_nb / 2.0, "WorldVolume"))
    geo.append(place("Win_W", 0, 0, z_w_out_top - th_win_w / 2.0, "WorldVolume"))
    geo.append(place("Win_Cryo", 0, 0, z_cryo_out_top - th_win_cryo / 2.0, "WorldVolume"))
    geo.append(place("Win_Be", 0, 0, z_shell_out_top - th_win_be / 2.0, "WorldVolume"))

    write_text(OUTDIR / "TibetTES_v5_6layers.geo", "".join(geo))

    setup = (
        "Name TibetTES\n"
        "Version 1\n"
        "Include TibetTES_v5_6layers.geo\n"
        "Include TibetTES_v5_6layers.det\n"
        f"SurroundingSphere {fmt(to_cm(150.0))} 0 0 {fmt(to_cm(19.0))} {fmt(to_cm(150.0))}\n"
    )
    write_text(OUTDIR / "TibetTES_v5_6layers.geo.setup", setup)

    # =========================
    # 生成探测器内容（只做添加）
    # =========================
    det = ["// Boundary-Driven SD Map (ALL volumes instrumented)\n\n"]

    # (A) TES pixels：保持你原先的 MDCalorimeter
    for l in range(N_LAYERS):
        det_add_mdcal(
            det,
            f"D{l+1}",
            f"TES_Pixel_L{l}",
            f"TES_L{l}",
            (pitch, pitch, 1.0),
            thr=0.3,
            eres_sigma=0.14,
        )

    # (B) 屏蔽层：补齐 Cryo_Shell（你说过它之前没 SD）
    shields_sd = [
        ("BGO_SD", "BGO_Shield"),
        ("Nb_SD", "Nb_Shield"),
        ("W_SD", "W_Shield"),
        ("Cryo_SD", "Cryo_Shell"),
        ("Al_SD", "Al_Shell"),
        ("CuBase_SD", "Cu_Base"),
        ("CuPole_SD", "Cu_SupportPole"),
    ]
    for dname, vname in shields_sd:
        det_add_scint(det, dname, vname, vname, thr=0.01, eres_sigma=1.0)

    # (C) Collimator：保持你原先的 X/Y bar SD
    det_add_mdcal(det, "CollBarX_SD", "CollBarX", "CollimatorVac", (coll_pitch, coll_pitch, 1.0), thr=0.001, eres_sigma=1.0)
    det_add_mdcal(det, "CollBarY_SD", "CollBarY", "CollimatorVac", (coll_pitch, coll_pitch, 1.0), thr=0.001, eres_sigma=1.0)

    # (D) 新增：把容器/衬底/窗口也加 SD（方便 IA/HT 与 RP(VN) 对齐；阈值给得更低一点）
    # 1) Substrate_L*
    for l in range(N_LAYERS):
        det_add_scint(det, f"Sub_L{l}_SD", f"Substrate_L{l}", f"Substrate_L{l}", thr=0.001, eres_sigma=1.0)

    # 2) TES_L* 真空容器（本身材料是 Vacuum，通常不会产生能量沉积，但加上不坏事；
    #    关键是让后续如果你把 TES_L 当作 VN 对齐对象时不会“det 文件缺失体积”）
    for l in range(N_LAYERS):
        det_add_scint(det, f"TESL{l}_SD", f"TES_L{l}", f"TES_L{l}", thr=0.001, eres_sigma=1.0)

    # 3) CollimatorVac（同理，Vacuum）
    det_add_scint(det, "CollVac_SD", "CollimatorVac", "CollimatorVac", thr=0.001, eres_sigma=1.0)

    # 4) Windows（体积定义如果在 Intro_TibetTES.geo：这几条会正常生效；如果你未来移除 window 体积，记得同步删）
    det_add_scint(det, "WinNb_SD", "Win_Nb", "Win_Nb", thr=0.001, eres_sigma=1.0)
    det_add_scint(det, "WinW_SD", "Win_W", "Win_W", thr=0.001, eres_sigma=1.0)
    det_add_scint(det, "WinCryo_SD", "Win_Cryo", "Win_Cryo", thr=0.001, eres_sigma=1.0)
    det_add_scint(det, "WinBe_SD", "Win_Be", "Win_Be", thr=0.001, eres_sigma=1.0)

    write_text(OUTDIR / "TibetTES_v5_6layers.det", "".join(det))

    # ==========================================
    # 重要：生成边界判定字典（只做添加：WINDOWS/SUBSTRATES/META，并写 bounds.json）
    # ==========================================
    def scale_bounds_lengths(obj, key=None):
        if isinstance(obj, dict):
            return {k: scale_bounds_lengths(v, k) for k, v in obj.items()}
        if isinstance(obj, list):
            return [scale_bounds_lengths(v, key) for v in obj]
        if isinstance(obj, (int, float)) and key != "N_LAYERS":
            return to_cm(obj)
        return obj

    def export_boundary_dict():
        raw_bounds = {
            # 原有：TES 层（用 z_center + r_max + hz 判定）
            "TES_LAYERS": [{"z_center": z, "r_max": 18.0, "hz": 1.5} for z in z_tes_centers_world],

            # 原有：准直器整体包络
            "COLLIMATOR": {"z_center": z_coll_center, "r_max": hole_r - RAD_EPS, "hz": coll_thick / 2.0},

            # 原有：多层屏蔽（polycone shell 近似字段）
            "SHIELDS": {
                "Nb_Shield": {
                    "r_out": r_nb_out,
                    "r_in": r_nb_in,
                    "z_out_bot": z_nb_out_bot,
                    "z_out_top": z_nb_out_top,
                    "z_in_bot": z_nb_in_bot,
                    "z_in_top": z_nb_in_top,
                    "hole_r": hole_r,
                },
                "W_Shield": {
                    "r_out": r_w_out,
                    "r_in": r_w_in,
                    "z_out_bot": z_w_out_bot,
                    "z_out_top": z_w_out_top,
                    "z_in_bot": z_w_in_bot,
                    "z_in_top": z_w_in_top,
                    "hole_r": hole_r,
                },
                "Cryo_Shell": {
                    "r_out": r_cryo_out,
                    "r_in": r_cryo_in,
                    "z_out_bot": z_cryo_out_bot,
                    "z_out_top": z_cryo_out_top,
                    "z_in_bot": z_cryo_in_bot,
                    "z_in_top": z_cryo_in_top,
                    "hole_r": hole_r,
                },
                "BGO_Shield": {
                    "r_out": r_bgo_out,
                    "r_in": r_bgo_in,
                    "z_out_bot": z_bgo_out_bot,
                    "z_out_top": z_bgo_out_top,
                    "z_in_bot": z_bgo_in_bot,
                    "z_in_top": z_bgo_in_top,
                    "hole_r": hole_r,
                },
                "Al_Shell": {
                    "r_out": r_shell_out,
                    "r_in": r_shell_in,
                    "z_out_bot": z_shell_out_bot,
                    "z_out_top": z_shell_out_top,
                    "z_in_bot": z_shell_in_bot,
                    "z_in_top": z_shell_in_top,
                    "hole_r": hole_r,
                },
            },

            # 原有：Cu base
            "CU_BASE": {"z_bot": z_cu_bot, "z_top": z_cu_top, "r_max": r_cu},
            # Cu support pole bounds (cylinder)
            "CU_SUPPORT": {"z_bot": pole_bot_z, "z_top": pole_top_z, "r_max": POLE_R},

            # 新增：Substrate（你后处理如果想区分 substrate vs TES_L 可以用这个）
            "SUBSTRATES": [
                {"name": f"Substrate_L{l}", "z_center": z_sub_centers[l], "hz": sub_h / 2.0, "r_max": sub_r}
                for l in range(N_LAYERS)
            ],

            # 新增：Windows（只给 z_center/thick/r_max；r_max 用 hole_r 或更大取决于你 Intro 里怎么定义）
            "WINDOWS": [
                {"name": "Win_Nb", "z_center": z_nb_out_top - th_win_nb / 2.0, "thick": th_win_nb, "r_max": hole_r},
                {"name": "Win_W", "z_center": z_w_out_top - th_win_w / 2.0, "thick": th_win_w, "r_max": hole_r},
                {"name": "Win_Cryo", "z_center": z_cryo_out_top - th_win_cryo / 2.0, "thick": th_win_cryo, "r_max": hole_r},
                {"name": "Win_Be", "z_center": z_shell_out_top - th_win_be / 2.0, "thick": th_win_be, "r_max": hole_r},
            ],

            # 新增：META（把关键几何参数写进 bounds，方便你在分析脚本里做一致性检查）
            "META": {
                "POLE_R": POLE_R,
                "pole_bot_z": pole_bot_z,
                "pole_top_z": pole_top_z,

                "N_LAYERS": N_LAYERS,
                "TES_LAYER_PITCH": TES_LAYER_PITCH,
                "sub_h": sub_h,
                "sub_r": sub_r,
                "pix_z": pix_z,
                "eff_r": eff_r,
                "coll_thick": coll_thick,
                "coll_hole": coll_hole,
                "coll_web": coll_web,
                "coll_pitch": coll_pitch,
                "hole_r": hole_r,
                "RAD_EPS": RAD_EPS,
                "POLE_R": POLE_R,
            },
        }
        bounds = scale_bounds_lengths(raw_bounds)
        bounds["META"].update(
            {
                "length_unit": "cm",
                "source_design_unit": "legacy_mm_like",
                "length_scale_to_cm": LENGTH_SCALE_TO_CM,
                "tes_pixel_thickness_cm": to_cm(pix_z),
                "science_beam_z_cm": to_cm(SOURCE_TOP_Z_DESIGN),
                "science_beam_radius_cm": to_cm(SOURCE_RADIUS_DESIGN),
            }
        )

        # (1) 终端打印（保持你原有风格）
        print("\n" + "=" * 50)
        print("COPY THE FOLLOWING DICTIONARY TO YOUR ANALYSIS SCRIPT:")
        print("=" * 50)
        print(f"GEOM_BOUNDS = {json.dumps(bounds, indent=4)}")
        print("=" * 50 + "\n")

        # (2) 新增：写入 bounds.json（后处理脚本可直接 --bounds_json code/geometry/bounds.json）
        write_text(OUTDIR / "bounds.json", json.dumps(bounds, indent=2))

    export_boundary_dict()


if __name__ == "__main__":
    main()
