#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GenerateGeo_ADR_v4c_mkflange.py

Engineering-oriented ADR local cryostat + TES sample box + external active shield mass model, v4c mK-flange detector can revision.

UNITS
-----
All dimensions are intended as millimetres for the current project geometry convention.

WHY v4 EXISTS
-------------
v3 used continuous Nb/A4K/W inner cans too close to the 50 mK plate. That was useful as a
background mass model, but it was not a realistic assembly concept. v4c keeps the dedicated 50 mK TES sample box, removes the previously confusing internal W baffle and heat-switch block, and moves the Nb detector can outward to the 50 mK cold-plate flange radius. Its sidewall starts at the 50 mK cold-plate bottom surface, and its inner radius tracks the cold-plate outer edge with a small non-overlap clearance. The 50 mK plate is now the light-tight mounting flange for the removable can.

TOPOLOGY
--------
TES stack + Si substrates are mounted in a 3 mm OFHC-Cu-style sample box.
The sample-box bottom disk touches the 50 mK cold plate. The sample box surrounds the TES
array and has a top aperture with a thin Al window/foil placeholder.

Then:
  sample box on 50 mK cold plate
  -> open-bottom Nb superconducting detector can indexed to the 50 mK cold-plate edge/flange
  -> no internal W side baffle; W is kept only as entrance grid/collimator baseline
  -> staged plates / 4 K and 50 K thermal shields
  -> Al cryostat vacuum jacket
  -> active scintillator outside cryostat
  -> outer Al mechanical cover

PUBLIC REFERENCES USED
----------------------
1. Danaher Cryogenics / HPD Model 103 Rainier ADR: 26 cm diameter x 25 cm tall experimental
   space; two-stage ADR down to 30 mK; 1 K and 50 mK stages; 50 K and 2.7 K pulse-tube
   stages; stainless vacuum jacket; quick release flanges; electronically controlled heat
   switches; nickel-plated aluminum radiation shields at 50 K and 4 K; wiring and user ports.
   https://danahercryo.com/model-103/
2. 511-CAM: passive tungsten inside cryostat, active BGO outside, superconducting Nb and
   0.062 inch A4K magnetic shields; focal-plane simulation uses BGO 5 cm bottom / 2 cm sides
   and 70 keV threshold, while neglecting Nb/A4K for now.  This prototype keeps Nb and omits
   A4K/Cryoperm to avoid introducing an uncertain high-Ni passive-background source.
   https://scispace.com/pdf/511-cam-mission-a-pointed-511-kev-gamma-ray-telescope-with-a-2ul26yrp.pdf
3. Kurt J. Lesker: 5000/6000-series aluminum high/ultra-high-vacuum chambers; aluminum has
   low magnetic permeability, low weight, and lower residual radioactivity than ferrous material.
   https://www.lesker.com/newweb/chambers/aluminum-chambers.cfm
4. Oxford Instruments: typical vacuum-tight Be exit window around 127 microns; this motivates
   the cryostat Be window baseline, not the internal sample-box Al foil.
   https://xray.oxinst.com/learning/view/article/caring-for-the-beryllium-window-of-an-x-ray-tube
5. Advatech CeBr3: commercial CeBr3 is no-oxygen, hygroscopic, density 5.1 g/cm3, decay time
   19 ns, 60 photons/keV, low intrinsic background; used here as no-O active-shield default.
   https://www.advatech-uk.co.uk/cebr3.html

MATERIAL CARD NOTE
------------------
This script uses CeBr3 by default. If Intro_TibetTES.geo does not define CeBr3/CsI yet, use
--compat-materials for geometry/debug only (CeBr3/CsI->BGO). Do not use the compatibility
mapping for final physics.
"""

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / 'outputs' / 'geometry' / 'raw_mm'

def fmt(x: float) -> str:
    return f"{x:.6f}".rstrip('0').rstrip('.')

def write_text(path: Path, s: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding='utf-8')
    print(f"[OK] wrote {path}")

def pcon_shape_line(phi0_deg: float, dphi_deg: float, planes):
    toks = ['PCON', fmt(phi0_deg), fmt(dphi_deg), str(len(planes))]
    for z, rmin, rmax in planes:
        toks += [fmt(z), fmt(rmin), fmt(rmax)]
    return ' '.join(toks)

def volume_def(volname: str, material: str, shape_line: str, vis: int = 1) -> str:
    return (f"// Volume {volname}; material={material}\n"
            f"Volume {volname}\n"
            f"{volname}.Material {material}\n"
            f"{volname}.Visibility {vis}\n"
            f"{volname}.Shape {shape_line}\n\n")

def place(volname: str, x: float, y: float, z: float, mother: str, vis=None) -> str:
    s = f"{volname}.Position {fmt(x)} {fmt(y)} {fmt(z)}\n{volname}.Mother {mother}\n"
    if vis is not None:
        s += f"{volname}.Visibility {vis}\n"
    return s + "\n"

def pcon_cylinder_def(volname: str, material: str, rmax: float, halfz: float, vis: int = 1) -> str:
    return volume_def(volname, material, pcon_shape_line(0.0, 360.0, [(-halfz, 0.0, rmax), (halfz, 0.0, rmax)]), vis)

def brik_def(volname: str, material: str, hx: float, hy: float, hz: float, vis: int = 1) -> str:
    return volume_def(volname, material, f"BRIK {fmt(hx)} {fmt(hy)} {fmt(hz)}", vis)

def closed_shell_def(volname: str, material: str, r_in: float, r_out: float,
                     z_in_bot: float, z_in_top: float, z_out_bot: float, z_out_top: float,
                     hole_r_top: float, vis: int = 1) -> str:
    """Shell with bottom disk, sidewall, and annular top cap."""
    planes = [
        (z_out_bot, 0.0, r_out),
        (z_in_bot, 0.0, r_out),
        (z_in_bot, r_in, r_out),
        (z_in_top, r_in, r_out),
        (z_in_top, hole_r_top, r_out),
        (z_out_top, hole_r_top, r_out),
    ]
    return volume_def(volname, material, pcon_shape_line(0.0, 360.0, planes), vis)

def open_bottom_can_def(volname: str, material: str, r_in: float, r_out: float,
                        z_in_bot: float, z_in_top: float, z_out_top: float,
                        hole_r_top: float, vis: int = 1) -> str:
    """Open-bottom can: sidewall plus annular top cap, no bottom disk.

    This is closer to a removable detector/shield can mounted over the 50 mK sample box.
    """
    planes = [
        (z_in_bot, r_in, r_out),
        (z_in_top, r_in, r_out),
        (z_in_top, hole_r_top, r_out),
        (z_out_top, hole_r_top, r_out),
    ]
    return volume_def(volname, material, pcon_shape_line(0.0, 360.0, planes), vis)

def add_collimator_grid(geo, *, R, thick, hole, web, z_center, material='W', mother='WorldVolume',
                        vac_name='CollimatorVac', barx='CollBarX', bary='CollBarY', vis_vac=0, vis_bar=1):
    pitch, hz = hole + web, thick / 2.0
    vac_hx, vac_hy = R + pitch, R + pitch
    bar_len_x, bar_len_y = 2 * vac_hx, 2 * vac_hy
    geo.append(brik_def(vac_name, 'Vacuum', vac_hx, vac_hy, hz, vis=vis_vac))
    geo.append(place(vac_name, 0, 0, z_center, mother, vis=vis_vac))
    geo.append(brik_def(barx, material, bar_len_x / 2.0, web / 2.0, hz, vis=vis_bar))
    geo.append(brik_def(bary, material, web / 2.0, bar_len_y / 2.0, hz, vis=vis_bar))
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

def det_add_mdcal(det_lines, det_name, sens_vol, det_vol, pitch_xyz, offset_xyz=(0, 0, 0), thr=0.001, eres_sigma=1.0):
    px, py, pz = pitch_xyz
    ox, oy, oz = offset_xyz
    det_lines.append(
        f"MDCalorimeter {det_name}\n"
        f"{det_name}.SensitiveVolume {sens_vol}\n"
        f"{det_name}.DetectorVolume {det_vol}\n"
        f"{det_name}.StructuralPitch {fmt(px)} {fmt(py)} {fmt(pz)}\n"
        f"{det_name}.StructuralOffset {fmt(ox)} {fmt(oy)} {fmt(oz)}\n"
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outdir', type=Path, default=OUTDIR, help='Output geometry directory')
    parser.add_argument('--active-material', default='CeBr3', choices=['CeBr3', 'CsI', 'BGO'], help='Active shield material')
    parser.add_argument('--compat-materials', action='store_true', help='Map CeBr3/CsI->BGO for geometry debugging only')
    args = parser.parse_args()
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    mat_active = args.active_material
    if args.compat_materials:
        if mat_active in ('CeBr3', 'CsI'):
            mat_active = 'BGO'

    # ---------------- TES array retained ----------------
    N_LAYERS = 6
    TES_LAYER_PITCH = 12.0
    n_pix, pix_x, pix_y, pix_z = 20, 1.5, 1.5, 3.0
    gap_pix, pitch = 0.05, 1.5 + 0.05
    eff_r, sub_r, sub_h = 18.0, 22.0, 0.3
    z_sub_center0 = 10.0
    z_sub_centers = [z_sub_center0 + l * TES_LAYER_PITCH for l in range(N_LAYERS)]
    z_tes_centers_world = [zc + sub_h / 2.0 + pix_z / 2.0 for zc in z_sub_centers]
    z_tes_top = max(z_tes_centers_world) + pix_z / 2.0

    # ---------------- Staged ADR plates ----------------
    plates = [
        {'name':'ColdPlate_50mK', 'mat':'Copper', 'r':45.0, 'h':5.0, 'zc':0.0,
         'basis':'Model 103 supports 1 K and 50 mK stages; 45 mm plate radius gives margin for the 34 mm-ID sample box and mounting screws.'},
        {'name':'ColdPlate_1K', 'mat':'Copper', 'r':55.0, 'h':5.0, 'zc':-32.0,
         'basis':'1 K intercept stage, separated from 50 mK plate to leave room for heat-switch/strap envelope.'},
        {'name':'ColdPlate_4K', 'mat':'Copper', 'r':70.0, 'h':6.0, 'zc':-72.0,
         'basis':'4 K / 2.7 K pulse-tube stage analog; radius leaves routing margin.'},
        {'name':'ColdPlate_50K', 'mat':'Aluminium', 'r':85.0, 'h':6.0, 'zc':-108.0,
         'basis':'50 K interface plate aligned with commercial 50 K radiation-shield stage.'},
    ]
    z_mk_top = plates[0]['zc'] + plates[0]['h'] / 2.0
    z_mk_bottom = plates[0]['zc'] - plates[0]['h'] / 2.0

    # ---------------- TES sample box: new in v4 ----------------
    # A 3 mm OFHC-Cu-style sample box is the engineering anchor: it mounts on 50 mK plate,
    # provides thermal conduction, particle shielding, and a clear removable detector module.
    # NEW_GEO_RE step01 convention: all axial apertures and thin-window clear
    # radii are matched to the cm-fixed Be window in fix:
    # fix Win_Be radius = 1.898 cm and thickness = 0.015 cm.
    entrance_r = 18.98

    sample_box = {
        'name':'TES_SampleBox_Cu', 'mat':'Copper',
        'r_in':34.0, 'wall':3.0,
        'z_out_bot':z_mk_top, 'z_in_bot':z_mk_top + 3.0,
        'z_in_top':84.0, 'z_out_top':87.0,
        'hole':entrance_r,
        'basis':'Engineering sample box: 3 mm Cu open/apertured cylinder; bottom disk contacts 50 mK plate; surrounds TES stack and Si substrates; top has Al window/foil placeholder.'
    }
    sample_window = {
        'name':'SampleBox_Al_Window', 'mat':'Aluminium',
        'r':entrance_r, 'thick':0.05, 'zc':85.5,
        'basis':'Thin Al sample-box window/foil placeholder; radius matched to the Be cryostat-window clear radius.'
    }

    # ---------------- Removable/open-bottom shield cans ----------------
    # v4c engineering correction:
    # - The Nb can is larger and uses the 50 mK cold plate as its mounting flange.
    # - The lower lip of each can starts at the 50 mK cold-plate bottom surface, so the
    #   cold plate itself closes the side light path while the cans remain removable.
    mk_plate_r = plates[0]['r']
    can_edge_clearance = 0.05  # mm: non-overlap clearance, engineering contact/light seal in concept
    nb_r_in = mk_plate_r + can_edge_clearance
    nb_wall = 0.30
    cans = [
        {'name':'Nb_SC_Detector_Can', 'mat':'Nb', 'r_in':nb_r_in, 'wall':nb_wall, 'z_in_bot':z_mk_bottom, 'z_in_top':92.0, 'top_extra':0.30, 'hole':entrance_r,
         'basis':'Thin removable superconducting detector can indexed to the 50 mK cold-plate flange. Inner radius is just outside the plate edge, and the lower lip starts at the plate bottom surface for light-tight seating without overlap.'},
    ]

    can_windows = [
        {'name':'Win_Nb_SC_Detector_Can', 'mat':'Nb', 'parent':'Nb_SC_Detector_Can',
         'r':entrance_r, 'thick':0.05,
         'zc':cans[0]['z_in_top'] + cans[0]['top_extra'] / 2.0,
         'basis':'NEW_GEO_RE step01 update: thin Nb window/foil placeholder across the Nb superconducting detector-can aperture; radius matched to Be window.'},
    ]

    # ---------------- Radiation shields and vacuum jacket ----------------
    shells_closed = [
        {'name':'Thermal_4K_Al_Shield', 'mat':'Aluminium', 'r_in':73.0, 'wall':0.80, 'z_in_bot':-90.0, 'z_in_top':114.0, 'z_extra':0.80, 'hole':entrance_r,
         'basis':'Commercial ADRs use nickel-plated aluminum radiation shields at 50 K and 4 K; 0.8 mm is mass-model baseline.'},
        {'name':'Thermal_50K_Al_Shield', 'mat':'Aluminium', 'r_in':88.0, 'wall':0.80, 'z_in_bot':-124.0, 'z_in_top':122.0, 'z_extra':0.80, 'hole':entrance_r,
         'basis':'50 K aluminum radiation shield enclosing colder stages.'},
        {'name':'Vacuum_Jacket_Al', 'mat':'Aluminium', 'r_in':93.0, 'wall':2.50, 'z_in_bot':-132.0, 'z_in_top':126.0, 'z_extra':2.50, 'hole':entrance_r,
         'basis':'Al cryostat vacuum jacket mass model; the aperture is closed only by the Be cryostat window. 2.5 mm is not pressure-vessel certification.'},
    ]
    missing_al_windows = [
        {'name':'Win_4K_Al_Shield', 'mat':'Aluminium', 'r':entrance_r, 'thick':0.05,
         'zc':shells_closed[0]['z_in_top'] + shells_closed[0]['z_extra'] / 2.0,
         'basis':'NEW_GEO_RE step01: added missing thin Al window across the 4 K thermal-shield aperture; radius matched to Be window.'},
        {'name':'Win_50K_Al_Shield', 'mat':'Aluminium', 'r':entrance_r, 'thick':0.05,
         'zc':shells_closed[1]['z_in_top'] + shells_closed[1]['z_extra'] / 2.0,
         'basis':'NEW_GEO_RE step01: added missing thin Al window across the 50 K thermal-shield aperture; radius matched to Be window.'},
    ]

    # v4c change: remove the two confusing internal placeholder blocks that looked like baffles
    # in the schematic. Service/heat-switch space is represented by empty clearance, not by a solid
    # Cu/Al block in the mass model.
    service_blocks = []

    # ---------------- Active shield outside cryostat ----------------
    active_gap = 5.0
    vac = shells_closed[-1]
    r_active_in = vac['r_in'] + vac['wall'] + active_gap
    if args.active_material == 'CeBr3':
        active_side, active_bottom, active_top = 32.0, 75.0, 20.0
        veto_threshold_suggestion = 30.0
        threshold_scan = [10, 20, 30, 50, 70, 100]
    elif args.active_material == 'CsI':
        active_side, active_bottom, active_top = 38.0, 85.0, 25.0
        veto_threshold_suggestion = 20.0
        threshold_scan = [10, 20, 30, 50, 70, 100]
    else:
        active_side, active_bottom, active_top = 20.0, 50.0, 20.0
        veto_threshold_suggestion = 70.0
        threshold_scan = [30, 50, 70, 100, 150]
    z_active_in_bot = vac['z_in_bot'] - vac['z_extra'] - active_gap
    z_active_in_top = vac['z_in_top'] + vac['z_extra'] + active_gap
    active_shell = {'name':f'{args.active_material}_Active_Shield', 'mat':mat_active,
                    'r_in':r_active_in, 'wall':active_side,
                    'z_in_bot':z_active_in_bot, 'z_in_top':z_active_in_top,
                    'z_out_bot':z_active_in_bot - active_bottom,
                    'z_out_top':z_active_in_top + active_top,
                    'hole':entrance_r,
                    'basis':'Active scintillator outside cryostat. CeBr3 is default no-O candidate; BGO control keeps CAM511-like dimensions.'}
    outer_shell = {'name':'Outer_Al_Mech_Shell', 'mat':'Aluminium',
                   'r_in':active_shell['r_in'] + active_shell['wall'] + 2.0,
                   'wall':2.00,
                   'z_in_bot':active_shell['z_out_bot'] - 2.0,
                   'z_in_top':active_shell['z_out_top'] + 2.0,
                   'z_extra':2.00,
                   'hole':entrance_r,
                   'basis':'Outer cover outside scintillator, not the vacuum boundary; structural mass placeholder.'}

    # entrance window and collimator
    th_win_be = 0.15
    coll_thick, coll_hole, coll_web = 1.0, 1.42, 0.13
    coll_pitch = coll_hole + coll_web
    coll_r = 31.0
    z_vac_top = vac['z_in_top'] + vac['z_extra']
    z_win_be = z_vac_top - th_win_be / 2.0
    z_coll_center = outer_shell['z_in_top'] + outer_shell['z_extra'] + 2.0 + coll_thick/2.0

    pix_xy = []
    for i in range(n_pix):
        for j in range(n_pix):
            x = -((n_pix * pitch) / 2.0) + (pitch / 2.0) + i * pitch
            y = -((n_pix * pitch) / 2.0) + (pitch / 2.0) + j * pitch
            if math.hypot(x, y) < eff_r:
                pix_xy.append((x, y))

    geo = ['Include Intro_TibetTES.geo\n\n']
    geo.append('// NEW_GEO_RE ADR v4c: Be-window-matched apertures plus added thin Al windows; internal W baffle removed.\n\n')

    for p in plates:
        geo.append(pcon_cylinder_def(p['name'], p['mat'], p['r'], p['h']/2.0))
    for l in range(N_LAYERS):
        geo.append(pcon_cylinder_def(f'Substrate_L{l}', 'Silicon', sub_r, sub_h/2.0))
        geo.append(brik_def(f'TES_Pixel_L{l}', 'Ta', pix_x/2.0, pix_y/2.0, pix_z/2.0))
        geo.append(brik_def(f'TES_L{l}', 'Vacuum', 24.0, 24.0, pix_z/2.0 + 0.1, vis=0))

    geo.append(closed_shell_def(sample_box['name'], sample_box['mat'], sample_box['r_in'], sample_box['r_in']+sample_box['wall'],
                                sample_box['z_in_bot'], sample_box['z_in_top'], sample_box['z_out_bot'], sample_box['z_out_top'], sample_box['hole']))
    geo.append(pcon_cylinder_def(sample_window['name'], sample_window['mat'], sample_window['r'], sample_window['thick']/2.0))

    for c in cans:
        geo.append(open_bottom_can_def(c['name'], c['mat'], c['r_in'], c['r_in']+c['wall'], c['z_in_bot'], c['z_in_top'], c['z_in_top']+c['top_extra'], c['hole']))
    for w in can_windows:
        geo.append(pcon_cylinder_def(w['name'], w['mat'], w['r'], w['thick']/2.0))
    for s in shells_closed:
        geo.append(closed_shell_def(s['name'], s['mat'], s['r_in'], s['r_in']+s['wall'], s['z_in_bot'], s['z_in_top'], s['z_in_bot']-s['z_extra'], s['z_in_top']+s['z_extra'], s['hole']))
    for w in missing_al_windows:
        geo.append(pcon_cylinder_def(w['name'], w['mat'], w['r'], w['thick']/2.0))

    for b in service_blocks:
        geo.append(brik_def(b['name'], b['mat'], b['hx'], b['hy'], b['hz']))

    geo.append(closed_shell_def(active_shell['name'], active_shell['mat'], active_shell['r_in'], active_shell['r_in']+active_shell['wall'],
                                active_shell['z_in_bot'], active_shell['z_in_top'], active_shell['z_out_bot'], active_shell['z_out_top'], active_shell['hole']))
    geo.append(closed_shell_def(outer_shell['name'], outer_shell['mat'], outer_shell['r_in'], outer_shell['r_in']+outer_shell['wall'],
                                outer_shell['z_in_bot'], outer_shell['z_in_top'], outer_shell['z_in_bot']-outer_shell['z_extra'], outer_shell['z_in_top']+outer_shell['z_extra'], outer_shell['hole']))

    geo.append(pcon_cylinder_def('Win_Be_Cryostat', 'Be', entrance_r, th_win_be/2.0))
    add_collimator_grid(geo, R=coll_r, thick=coll_thick, hole=coll_hole, web=coll_web, z_center=z_coll_center)

    # placements
    for p in plates:
        geo.append(place(p['name'], 0, 0, p['zc'], 'WorldVolume'))
    for l in range(N_LAYERS):
        geo.append(place(f'Substrate_L{l}', 0, 0, z_sub_centers[l], 'WorldVolume'))
        geo.append(place(f'TES_L{l}', 0, 0, z_tes_centers_world[l], 'WorldVolume', vis=0))
        for idx, (xw, yw) in enumerate(pix_xy):
            geo.append(f'TES_Pixel_L{l}.Copy TP_L{l}_{idx:05d}\n')
            geo.append(place(f'TP_L{l}_{idx:05d}', xw, yw, 0, f'TES_L{l}', vis=0))
    geo.append(place(sample_box['name'], 0, 0, 0, 'WorldVolume'))
    geo.append(place(sample_window['name'], 0, 0, sample_window['zc'], 'WorldVolume'))
    for c in cans:
        geo.append(place(c['name'], 0, 0, 0, 'WorldVolume'))
    for w in can_windows:
        geo.append(place(w['name'], 0, 0, w['zc'], 'WorldVolume'))
    for s in shells_closed:
        geo.append(place(s['name'], 0, 0, 0, 'WorldVolume'))
    for w in missing_al_windows:
        geo.append(place(w['name'], 0, 0, w['zc'], 'WorldVolume'))
    for b in service_blocks:
        geo.append(place(b['name'], b['x'], b['y'], b['z'], 'WorldVolume'))
    geo.append(place(active_shell['name'], 0, 0, 0, 'WorldVolume'))
    geo.append(place(outer_shell['name'], 0, 0, 0, 'WorldVolume'))
    geo.append(place('Win_Be_Cryostat', 0, 0, z_win_be, 'WorldVolume'))

    write_text(outdir / 'TibetTES_ADR_v4c_mkflange.geo', ''.join(geo))

    det = ['// ADR v4c mK-flange detector map\n\n']
    for l in range(N_LAYERS):
        det_add_mdcal(det, f'D{l+1}', f'TES_Pixel_L{l}', f'TES_L{l}', (pitch, pitch, 1.0), thr=0.3, eres_sigma=0.14)
    for l in range(N_LAYERS):
        det_add_scint(det, f'Substrate_L{l}_SD', f'Substrate_L{l}', f'Substrate_L{l}', thr=0.001, eres_sigma=1.0)
    # record thresholds, not final veto thresholds
    det_add_scint(det, 'ActiveShield_SD', active_shell['name'], active_shell['name'], thr=0.01, eres_sigma=1.0)
    for p in plates:
        det_add_scint(det, p['name']+'_SD', p['name'], p['name'], thr=0.001, eres_sigma=1.0)
    det_add_scint(det, sample_box['name']+'_SD', sample_box['name'], sample_box['name'], thr=0.001, eres_sigma=1.0)
    det_add_scint(det, sample_window['name']+'_SD', sample_window['name'], sample_window['name'], thr=0.001, eres_sigma=1.0)
    for c in cans:
        det_add_scint(det, c['name']+'_SD', c['name'], c['name'], thr=0.001, eres_sigma=1.0)
    for w in can_windows:
        det_add_scint(det, w['name']+'_SD', w['name'], w['name'], thr=0.001, eres_sigma=1.0)
    for s in shells_closed + [outer_shell]:
        det_add_scint(det, s['name']+'_SD', s['name'], s['name'], thr=0.001, eres_sigma=1.0)
    for w in missing_al_windows:
        det_add_scint(det, w['name']+'_SD', w['name'], w['name'], thr=0.001, eres_sigma=1.0)
    for b in service_blocks:
        det_add_scint(det, b['name']+'_SD', b['name'], b['name'], thr=0.001, eres_sigma=1.0)
    det_add_scint(det, 'WinBe_SD', 'Win_Be_Cryostat', 'Win_Be_Cryostat', thr=0.001, eres_sigma=1.0)
    det_add_mdcal(det, 'CollBarX_SD', 'CollBarX', 'CollimatorVac', (coll_pitch, coll_pitch, 1.0), thr=0.001, eres_sigma=1.0)
    det_add_mdcal(det, 'CollBarY_SD', 'CollBarY', 'CollimatorVac', (coll_pitch, coll_pitch, 1.0), thr=0.001, eres_sigma=1.0)
    write_text(outdir / 'TibetTES_ADR_v4c_mkflange.det', ''.join(det))

    bounds = {
        'UNITS':'mm',
        'VERSION':'ADR_v4c_mkflange_new_geo_re_step01',
        'DESIGN_NOTE':'NEW_GEO_RE step01: ADR v4c geometry retained, but all axial aperture/window clear radii are matched to the Be cryostat-window radius; A4K is omitted, the Nb can window is retained, and the vacuum-jacket aperture is closed only by the Be window.',
        'TES_LAYERS':[{'z_center':z, 'r_max':eff_r, 'hz':pix_z/2.0} for z in z_tes_centers_world],
        'SUBSTRATES':[{'name':f'Substrate_L{l}', 'z_center':z_sub_centers[l], 'hz':sub_h/2.0, 'r_max':sub_r} for l in range(N_LAYERS)],
        'COLD_PLATES':plates,
        'SAMPLE_BOX':{**sample_box, 'r_out':sample_box['r_in']+sample_box['wall'], 'window':sample_window},
        'OPEN_BOTTOM_CANS':[
            {**c, 'r_out':c['r_in']+c['wall'], 'z_out_top':c['z_in_top']+c['top_extra'],
             'window':next((w['name'] for w in can_windows if w['parent'] == c['name']), None)}
            for c in cans
        ],
        'CRYOSTAT_SHELLS':[{**s, 'r_out':s['r_in']+s['wall'], 'z_out_bot':s['z_in_bot']-s['z_extra'], 'z_out_top':s['z_in_top']+s['z_extra']} for s in shells_closed],
        'SERVICE_BLOCKS':service_blocks,
        'ACTIVE_SHIELD':{**active_shell, 'r_out':active_shell['r_in']+active_shell['wall'], 'active_material_requested':args.active_material, 'active_material_used':mat_active, 'recommended_veto_threshold_keV':veto_threshold_suggestion, 'threshold_scan_keV':threshold_scan},
        'OUTER_MECHANICAL_SHELL':{**outer_shell, 'r_out':outer_shell['r_in']+outer_shell['wall'], 'z_out_bot':outer_shell['z_in_bot']-outer_shell['z_extra'], 'z_out_top':outer_shell['z_in_top']+outer_shell['z_extra']},
        'WINDOWS':[
            {'name':'SampleBox_Al_Window', 'material':'Aluminium', 'z_center':sample_window['zc'], 'thick':sample_window['thick'], 'r_max':sample_window['r'], 'basis':sample_window['basis']},
            *[
                {'name':w['name'], 'material':w['mat'], 'parent':w['parent'], 'z_center':w['zc'], 'thick':w['thick'], 'r_max':w['r'], 'basis':w['basis']}
                for w in can_windows
            ],
            *[
                {'name':w['name'], 'material':w['mat'], 'z_center':w['zc'], 'thick':w['thick'], 'r_max':w['r'], 'basis':w['basis']}
                for w in missing_al_windows
            ],
            {'name':'Win_Be_Cryostat', 'material':'Be', 'z_center':z_win_be, 'thick':th_win_be, 'r_max':entrance_r, 'basis':'Matched to fix/code/geometry Win_Be: radius 1.898 cm and thickness 0.015 cm after cm scaling; radius is the NEW_GEO_RE aperture reference.'},
        ],
        'COLLIMATOR':{'z_center':z_coll_center, 'r_max':coll_r, 'hz':coll_thick/2.0, 'hole':coll_hole, 'web':coll_web, 'pitch':coll_pitch, 'basis':'Project W grid retained as first collimator baseline; compare with CAM511 W aperture/passive shield.'},
        'META':{'N_LAYERS':N_LAYERS, 'TES_LAYER_PITCH':TES_LAYER_PITCH, 'n_pixels_per_layer':len(pix_xy), 'active_material_requested':args.active_material, 'active_material_used':mat_active, 'compat_materials':args.compat_materials, 'tes_top_mm':z_tes_top, 'sample_box_contact_z_mm':z_mk_top, 'mk_plate_bottom_z_mm':z_mk_bottom, 'can_bottom_seat_z_mm':z_mk_bottom, 'be_window_radius_reference_mm':entrance_r, 'all_axial_holes_match_be_window':True, 'added_can_windows':[w['name'] for w in can_windows], 'added_missing_al_windows':[w['name'] for w in missing_al_windows], 'vacuum_jacket_window_policy':'Be only', 'omitted_a4k_for_background_simplicity':True, 'can_inner_radius_basis':'50mK plate outer radius + small non-overlap clearance', 'removed_internal_w_baffle':True, 'removed_heat_switch_block':True},
    }
    write_text(outdir / 'bounds.json', json.dumps(bounds, indent=2, ensure_ascii=False))
    print('[OK] ADR v4c mK-flange sample-box geometry generation complete')

if __name__ == '__main__':
    main()
