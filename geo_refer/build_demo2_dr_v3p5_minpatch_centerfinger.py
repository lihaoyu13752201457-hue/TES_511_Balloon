#!/usr/bin/env python3
"""Build DEMO2 DR_v3p5 minimal patch with off-axis Cu cold fingers.

This script starts from DEMO2_DR_v3p5_minpatch_three_fixes_bounds.json and changes
only the user-requested thermal-finger implementation:

  * The deepest support disk is moved downstream to clear the final Si
    substrate.
  * The former centerline Cu finger is replaced by four symmetric off-axis
    fingers and stems.
  * C016/C017/C018 local sample-can shields receive declared CSG feedthrough
    holes/slots for the off-axis fingers/stems.
  * The side-entry CsI aperture is declared on both adjacent side segments so
    the beam is not placed on a one-sided segment boundary cut.
  * The side-entry W sleeve/collimator is shortened from 4 cm to 2 cm because
    it is a local square-bore leakage suppressor, not a long pixel collimator.

All other v3p5-minpatch geometry is intentionally retained.
"""
from __future__ import annotations

import base64
import csv
import html
import json
import math
import shutil
import zipfile
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch

ROOT = Path('/mnt/data') if Path('/mnt/data').exists() else Path.cwd()
ASSET = ROOT / 'v3p5_centerfinger_assets'
ASSET.mkdir(exist_ok=True)

BASE_JSON = ROOT / 'DEMO2_DR_v3p5_minpatch_three_fixes_bounds.json'
VERSION = 'DEMO2_DR_v3p5_minpatch_centerfinger'

DENSITY = {
    'Vacuum': 0.0, 'Copper': 8.96, 'Aluminium': 2.70, 'Silicon': 2.329, 'Ta': 16.69,
    'Nb': 8.57, 'W': 19.30, 'Be': 1.85, 'CsI': 4.51, 'Cryoperm': 8.70,
    'StainlessSteel': 8.00, 'CuNi': 8.90, 'SilverSinterProxy': 5.00, 'CharcoalProxy': 1.20,
    'G10': 1.85, 'NbTiCableProxy': 6.50, 'Kapton': 1.42,
}
COLORS = {
    'Ta': '#d62728', 'Silicon': '#222222', 'Copper': '#c47c28', 'Aluminium': '#b7b7b7',
    'Nb': '#62c8df', 'Cryoperm': '#4b64a1', 'W': '#333333', 'Be': '#56b4e9', 'CsI': '#6fa8dc',
    'StainlessSteel': '#7f7f7f', 'CuNi': '#8c6d31', 'SilverSinterProxy': '#c0c0c0',
    'CharcoalProxy': '#6b4f3a', 'G10': '#70ad47', 'NbTiCableProxy': '#9467bd', 'Kapton': '#f2c744',
    'Vacuum': '#ffffff',
}
BEAM_Z = -5.2
BEAM_R = 1.898
PORT_R = 2.05
SUPPORT_DISK_CLEARANCE_CM = 0.05
OFFAXIS_FINGER_R_CM = 0.16
OFFAXIS_PAD_R_CM = 0.35
OFFAXIS_FINGER_OFFSET_CM = 1.10
OFFAXIS_STEM_X_SPLIT_CM = 0.80
W_COLLIMATOR_X0_CM = -18.0
W_COLLIMATOR_THICKNESS_CM = 2.0


def cyl(r: float, h: float, f: float = 1.0) -> float:
    return f * math.pi * r * r * h


def ann(ri: float, ro: float, h: float, f: float = 1.0) -> float:
    return f * math.pi * (ro * ro - ri * ri) * h


def comp_mass(c: dict[str, Any]) -> None:
    c['mass_kg'] = DENSITY[c['material']] * c['volume_cm3'] / 1000.0


def next_cid(comps: list[dict[str, Any]]) -> int:
    return max(int(c.get('cid', 'C000')[1:]) for c in comps) + 1


def make_component(
    cid_i: int,
    name: str,
    category: str,
    material: str,
    shape: str,
    params: dict[str, Any],
    volume_cm3: float,
    install: str,
    why_for_sim: str,
    size_basis: str,
    source_tag: str,
) -> dict[str, Any]:
    c = {
        'cid': f'C{cid_i:03d}',
        'name': name,
        'category': category,
        'material': material,
        'shape': shape,
        'params': params,
        'volume_cm3': volume_cm3,
        'mass_kg': 0.0,
        'install': install,
        'why_for_sim': why_for_sim,
        'size_basis': size_basis,
        'source_tag': source_tag,
    }
    comp_mass(c)
    return c


def load_and_patch() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    bounds = json.loads(BASE_JSON.read_text(encoding='utf-8'))
    comps: list[dict[str, Any]] = bounds['COMPONENTS']

    # Locate the deepest Cu support disk and old bridge/stem.
    substrate = next(c for c in comps if c['name'] == 'Si_Substrate_Stack_side_entry')
    disk = next(c for c in comps if c['name'] == 'Cu_SubstrateSupport_SolidDisk_L0_deepest')
    bridge = next(c for c in comps if c['name'] == 'Cu_ColdFinger_Bridge_to_Stem')
    stem = next(c for c in comps if c['name'] == 'Cu_ColdFinger_Stem_to_MXC_minimal')
    pad = next(c for c in comps if c['name'] == 'Cu_MXC_Clamp_Pad_for_MinimalStem')

    last_substrate_x = max(substrate['params']['x_centers_cm'])
    last_substrate_end = last_substrate_x + substrate['params']['disc_t_cm'] / 2.0
    disk_half = disk['params']['thickness_cm'] / 2.0
    disk_x = max(
        disk['params']['x_center_cm'],
        last_substrate_end + SUPPORT_DISK_CLEARANCE_CM + disk_half,
    )
    disk['params']['x_center_cm'] = disk_x
    disk['params']['clearance_to_last_substrate_cm'] = SUPPORT_DISK_CLEARANCE_CM
    disk['params']['last_substrate_downstream_face_cm'] = last_substrate_end
    disk['install'] = (
        'Single solid Cu disk behind the deepest/downstream substrate only; shifted downstream to keep an explicit '
        '0.5 mm gap to the final Si substrate.'
    )
    disk['size_basis'] = (
        '3.5 mm disk follows the requested 3-4 mm support disk; downstream face clearance to the last substrate is '
        f'{SUPPORT_DISK_CLEARANCE_CM:.2f} cm.'
    )
    disk_r = disk['params']['r_cm']
    disk_z = disk['params']['axis_z_cm']
    stem_x = stem['params']['x_center_cm']
    finger_r = OFFAXIS_FINGER_R_CM
    pad_r = OFFAXIS_PAD_R_CM
    off = OFFAXIS_FINGER_OFFSET_CM
    finger_sites = [
        {'tag': 'YP_ZP', 'y_cm': off, 'z_cm': disk_z + off, 'stem_x_cm': stem_x - OFFAXIS_STEM_X_SPLIT_CM},
        {'tag': 'YM_ZP', 'y_cm': -off, 'z_cm': disk_z + off, 'stem_x_cm': stem_x - OFFAXIS_STEM_X_SPLIT_CM},
        {'tag': 'YP_ZM', 'y_cm': off, 'z_cm': disk_z - off, 'stem_x_cm': stem_x},
        {'tag': 'YM_ZM', 'y_cm': -off, 'z_cm': disk_z - off, 'stem_x_cm': stem_x},
    ]

    # Replace the old single bridge/stem/pad with four off-axis fingers, stems,
    # and compact clamp pads.  Their total Cu cross-section is kept close to the
    # old one-rod design: 4 * 0.16^2 ~= 0.32^2.
    for old in (bridge, stem, pad):
        comps.remove(old)
    insert_at = next(i for i, c in enumerate(comps) if c['name'] == 'Nb_SideEntry_Sample_Can_with_side_aperture')
    new_cid = next_cid(comps)
    new_thermal: list[dict[str, Any]] = []
    for site in finger_sites:
        suffix = site['tag']
        y = site['y_cm']
        z = site['z_cm']
        new_thermal.append(
            make_component(
                new_cid,
                f'Cu_ColdFinger_OffAxis_{suffix}_from_Disk_to_Stem',
                'thermal_link',
                'Copper',
                'x_cylinder_offaxis',
                {
                    'r_cm': finger_r,
                    'x0_cm': disk_x,
                    'x1_cm': site['stem_x_cm'],
                    'y_center_cm': y,
                    'z_center_cm': z,
                    'radial_offset_from_beam_axis_cm': math.hypot(y, z - disk_z),
                    'connects': 'deepest support disk to its matching off-axis vertical stem',
                    'passes_through_sample_box': True,
                    'required_feedthroughs': ['Nb +x thermal feedthrough', 'Cryoperm +x thermal feedthrough', 'Al 50mK +x thermal feedthrough'],
                },
                cyl(finger_r, site['stem_x_cm'] - disk_x),
                'One of four symmetric off-axis Cu thermal fingers from the downstream support disk to a matching vertical stem.',
                'Provides thermal conductance without placing a Cu finger on the 511 keV beam axis.',
                'Four 1.6 mm radius fingers give nearly the same total cross-section as the previous single 3.2 mm radius center finger; radial offset is large enough to clear the beam axis but remains inside the 2.2 cm support disk.',
                'User requested four symmetric edge-biased but not edge-clipped thermal fingers + Cu-64 mitigation',
            )
        )
        new_cid += 1
    for site in finger_sites:
        suffix = site['tag']
        y = site['y_cm']
        z = site['z_cm']
        new_thermal.append(
            make_component(
                new_cid,
                f'Cu_ColdFinger_Stem_{suffix}_to_MXC',
                'thermal_link',
                'Copper',
                'z_cylinder_offaxis',
                {
                    'r_cm': finger_r,
                    'x_center_cm': site['stem_x_cm'],
                    'y_center_cm': y,
                    'z0_cm': z,
                    'z1_cm': -0.30,
                    'connects': 'off-axis thermal finger to MXC plate bottom / clamp pad',
                    'passes_through_50mK_can_top_slot': True,
                },
                cyl(finger_r, -0.30 - z),
                'One of four off-axis vertical Cu stems connecting a thermal finger to the MXC clamp region.',
                'Completes the thermal path to the MXC while keeping all stems away from the beam axis.',
                'Stem radius matches the off-axis finger radius; each stem terminates at the MXC bottom interface.',
                'User requested four symmetric off-axis thermal stems',
            )
        )
        new_cid += 1
    for site in finger_sites:
        suffix = site['tag']
        y = site['y_cm']
        new_thermal.append(
            make_component(
                new_cid,
                f'Cu_MXC_Clamp_Pad_{suffix}_for_OffAxisStem',
                'thermal_link',
                'Copper',
                'z_cylinder_offaxis',
                {
                    'r_cm': pad_r,
                    'x_center_cm': site['stem_x_cm'],
                    'y_center_cm': y,
                    'z0_cm': -0.5,
                    'z1_cm': -0.3,
                    'connects': 'matching off-axis stem to the MXC plate bottom',
                },
                cyl(pad_r, 0.20),
                'Compact Cu clamp pad for one off-axis thermal stem at the MXC interface.',
                'Adds a local contact pad without recreating a large Cu sample box.',
                '7 mm diameter, 2 mm thick pad, matched to the smaller off-axis stem bundle.',
                'Engineering proxy',
            )
        )
        new_cid += 1
    comps[insert_at:insert_at] = new_thermal

    # Declare required holes/slots in the sample-box replacement shells only.
    feedthroughs = [
        {
            'for_component': f'Cu_ColdFinger_OffAxis_{site["tag"]}_from_Disk_to_Stem',
            'axis_y_cm': site['y_cm'],
            'axis_z_cm': site['z_cm'],
            'clear_radius_cm': finger_r + 0.08,
            'note': 'Required hole/slot in the +x cap so this off-axis copper finger passes through the sample-box replacement shell.',
        }
        for site in finger_sites
    ]
    stem_slots = [
        {
            'for_component': f'Cu_ColdFinger_Stem_{site["tag"]}_to_MXC',
            'x_center_cm': site['stem_x_cm'],
            'y_center_cm': site['y_cm'],
            'clear_radius_cm': finger_r + 0.08,
            'note': 'Required upper slot so this vertical stem reaches the MXC clamp pad.',
        }
        for site in finger_sites
    ]
    for nm in ['Nb_SideEntry_Sample_Can_with_side_aperture', 'Cryoperm_Horizontal_Sleeve_1p2mm']:
        c = next(x for x in comps if x['name'] == nm)
        c['params'].pop('plus_x_centerhub_feedthrough', None)
        c['params']['plus_x_thermal_finger_feedthroughs'] = feedthroughs
        c['install'] += ' The +x cap includes four declared off-axis thermal-finger feedthroughs.'
    c = next(x for x in comps if x['name'] == 'Al_50mK_Local_Can_side_entry')
    c['params'].pop('plus_x_centerhub_feedthrough', None)
    c['params'].pop('top_stem_slot', None)
    c['params']['plus_x_thermal_finger_feedthroughs'] = feedthroughs
    c['params']['top_stem_slots'] = stem_slots
    c['install'] += ' The +x cap and upper wall include four declared off-axis thermal-finger feedthroughs and stem slots.'

    # The side-entry beam lies at azimuth 180 deg, exactly on the nominal
    # boundary between side segments 03 and 04.  Declare the same aperture on
    # both segments so the final CSG implementation cannot leave one edge half
    # blocked by an adjacent CsI segment.
    for nm in ['CsI_Side_Segment_03', 'CsI_Side_Segment_04']:
        c = next(x for x in comps if x['name'] == nm)
        c['params']['side_hole'] = {'azimuth_deg': 180, 'z_cm': BEAM_Z, 'r_cm': 2.6}
        c['params']['side_port_csg_authority'] = True
        c['params']['side_port_radius_cm'] = 2.6
        c['params']['side_port_axis'] = '-x_to_+x, centered at y=0,z=-5.2; shared by adjacent CsI segments 03/04'
        if 'shared side beam aperture' not in c['install']:
            c['install'] += ' This segment shares the side beam aperture cut because the beam azimuth lies on the 03/04 segment boundary.'

    w_col = next(c for c in comps if c['name'] == 'W_Side_Aperture_Sleeve_collimator')
    w_col['params']['x0_cm'] = W_COLLIMATOR_X0_CM
    w_col['params']['x1_cm'] = W_COLLIMATOR_X0_CM + W_COLLIMATOR_THICKNESS_CM
    w_col['params']['thickness_cm'] = W_COLLIMATOR_THICKNESS_CM
    w_col['volume_cm3'] = ann(
        w_col['params']['r_in_cm'],
        w_col['params']['r_out_cm'],
        W_COLLIMATOR_THICKNESS_CM,
    )
    comp_mass(w_col)
    w_col['install'] = (
        '2 cm thick W sleeve through the side aperture of the CsI veto, aligned with the Laue focus beam. '
        'Side port is an explicit CSG aperture in this minimal patch.'
    )
    w_col['size_basis'] = (
        'Inner radius follows 1.95 cm shield hole; outer radius leaves 0.5 mm clearance inside the 2.60 cm '
        'CsI side hole; axial thickness reduced from 4 cm to 2 cm because the side-entry sleeve is a local '
        'leakage suppressor rather than a long high-aspect-ratio pixel collimator.'
    )

    # Update version / bookkeeping.
    for i, c in enumerate(comps, 1):
        c['cid'] = f'C{i:03d}'
    total = sum(c['mass_kg'] for c in comps)
    active = sum(c['mass_kg'] for c in comps if c['material'] == 'CsI')
    by_cat: dict[str, float] = {}
    by_mat: dict[str, float] = {}
    for c in comps:
        by_cat[c['category']] = by_cat.get(c['category'], 0.0) + c['mass_kg']
        by_mat[c['material']] = by_mat.get(c['material'], 0.0) + c['mass_kg']

    bounds['VERSION'] = VERSION
    finger_names = [c['name'] for c in new_thermal if c['shape'] == 'x_cylinder_offaxis']
    stem_names = [c['name'] for c in new_thermal if c['name'].startswith('Cu_ColdFinger_Stem_')]
    pad_names = [c['name'] for c in new_thermal if 'Clamp_Pad' in c['name']]
    bounds['DESIGN_NOTE'] = bounds.get('DESIGN_NOTE', '') + (
        '\n\nOFF-AXIS FOUR-FINGER PATCH: based on v3p5_minpatch_three_fixes; the downstream support disk is shifted clear of '
        'the final Si substrate, the centerline thermal finger is replaced by four symmetric off-axis fingers/stems, and '
        'the CsI side aperture is declared on both adjacent side segments. The W side sleeve/collimator is shortened '
        'from 4 cm to 2 cm as a local square-bore leakage suppressor.'
    )
    bounds['META']['version'] = VERSION
    bounds['META']['total_mass_kg'] = total
    bounds['META']['active_csi_mass_kg'] = active
    bounds['META']['non_active_mass_kg'] = total - active
    bounds['META']['offaxis_four_finger_patch'] = {
        'scope': 'Shift support disk for substrate clearance; replace centerline Cu finger with four symmetric off-axis fingers/stems; share the CsI side port across segments 03/04.',
        'support_disk': disk['name'],
        'support_disk_center_x_cm': disk_x,
        'support_disk_clearance_to_last_substrate_cm': SUPPORT_DISK_CLEARANCE_CM,
        'finger_names': finger_names,
        'stem_names': stem_names,
        'pad_names': pad_names,
        'finger_radius_cm': finger_r,
        'finger_site_offsets_yz_cm': [{'y_cm': s['y_cm'], 'z_cm': s['z_cm']} for s in finger_sites],
        'finger_radial_offset_from_beam_axis_cm': math.hypot(off, off),
        'stem_x_rows_cm': {
            'ZP': stem_x - OFFAXIS_STEM_X_SPLIT_CM,
            'ZM': stem_x,
        },
        'stem_sites_xy_cm': [{'x_cm': s['stem_x_cm'], 'y_cm': s['y_cm']} for s in finger_sites],
        'stem_x_split_cm': OFFAXIS_STEM_X_SPLIT_CM,
        'feedthrough_clear_radius_cm': finger_r + 0.08,
        'shared_csi_side_aperture_segments': ['CsI_Side_Segment_03', 'CsI_Side_Segment_04'],
    }
    bounds['COMPONENTS'] = comps
    bounds['MASS_BY_CATEGORY'] = by_cat
    bounds['MASS_BY_MATERIAL'] = by_mat

    disk_start = disk_x - disk_half
    substrate_clearance = disk_start - last_substrate_end
    finger_radial_offsets = [
        math.hypot(c['params']['y_center_cm'], c['params']['z_center_cm'] - disk_z)
        for c in new_thermal
        if c['shape'] == 'x_cylinder_offaxis'
    ]
    centerline_finger_residue = [
        c['name']
        for c in new_thermal
        if c['shape'] == 'x_cylinder_offaxis'
        and abs(c['params']['y_center_cm']) < 1e-9
        and abs(c['params']['z_center_cm'] - disk_z) < 1e-9
    ]
    side_segments_with_hole = [
        c['name']
        for c in comps
        if c['name'] in {'CsI_Side_Segment_03', 'CsI_Side_Segment_04'}
        and c['params'].get('side_port_csg_authority')
    ]
    w_col = next(c for c in comps if c['name'] == 'W_Side_Aperture_Sleeve_collimator')
    w_col_thickness = w_col['params']['x1_cm'] - w_col['params']['x0_cm']
    stem_sites_xy = [
        (round(c['params']['x_center_cm'], 9), round(c['params']['y_center_cm'], 9))
        for c in new_thermal
        if c['name'].startswith('Cu_ColdFinger_Stem_')
    ]
    pad_sites_xy = [
        (c['params']['x_center_cm'], c['params']['y_center_cm'])
        for c in new_thermal
        if c['name'].startswith('Cu_MXC_Clamp_Pad_')
    ]
    pad_min_xy_separation = min(
        math.hypot(x0 - x1, y0 - y1)
        for i, (x0, y0) in enumerate(pad_sites_xy)
        for x1, y1 in pad_sites_xy[i + 1:]
    )
    problems: list[str] = []
    if substrate_clearance < SUPPORT_DISK_CLEARANCE_CM - 1e-9:
        problems.append(f'support disk clearance {substrate_clearance:.6g} cm is below required {SUPPORT_DISK_CLEARANCE_CM:.6g} cm')
    if len(finger_radial_offsets) != 4:
        problems.append(f'expected 4 off-axis fingers, found {len(finger_radial_offsets)}')
    if centerline_finger_residue:
        problems.append('centerline thermal finger residue: ' + ', '.join(centerline_finger_residue))
    if len(side_segments_with_hole) != 2:
        problems.append('side aperture is not declared on both adjacent CsI side segments')
    if abs(w_col_thickness - W_COLLIMATOR_THICKNESS_CM) > 1e-9:
        problems.append(f'W side collimator thickness {w_col_thickness:.6g} cm is not {W_COLLIMATOR_THICKNESS_CM:.6g} cm')
    if len(set(stem_sites_xy)) != 4:
        problems.append(f'off-axis stems do not occupy four unique MXC x/y sites: {stem_sites_xy}')
    if pad_min_xy_separation < 2.0 * pad_r - 1e-9:
        problems.append(
            f'off-axis MXC clamp pads overlap: minimum center separation {pad_min_xy_separation:.6g} cm '
            f'is below {2.0 * pad_r:.6g} cm'
        )
    validation = {
        'status': 'DESIGN_PASS' if not problems else 'DESIGN_REVIEW_REQUIRED',
        'problems': problems,
        'checks': {
            'base_model': 'DEMO2_DR_v3p5_minpatch_three_fixes',
            'patch_policy': 'support_disk_clearance_plus_four_symmetric_offaxis_fingers_plus_shared_csi_side_port',
            'support_disk_clearance_to_last_substrate_cm': substrate_clearance,
            'support_disk_clearance_required_cm': SUPPORT_DISK_CLEARANCE_CM,
            'offaxis_finger_count': len(finger_radial_offsets),
            'offaxis_finger_radius_cm': finger_r,
            'offaxis_finger_radial_offsets_cm': finger_radial_offsets,
            'offaxis_stem_unique_xy_site_count': len(set(stem_sites_xy)),
            'offaxis_stem_xy_sites_cm': [{'x_cm': x, 'y_cm': y} for x, y in stem_sites_xy],
            'offaxis_pad_min_xy_separation_cm': pad_min_xy_separation,
            'offaxis_pad_min_required_separation_cm': 2.0 * pad_r,
            'centerline_finger_residue': centerline_finger_residue,
            'sample_box_replacement_shells_declare_feedthroughs': all(
                'plus_x_thermal_finger_feedthroughs' in next(c for c in comps if c['name'] == nm)['params']
                for nm in ['Nb_SideEntry_Sample_Can_with_side_aperture', 'Cryoperm_Horizontal_Sleeve_1p2mm', 'Al_50mK_Local_Can_side_entry']
            ),
            'shared_csi_side_aperture_segments': side_segments_with_hole,
            'w_side_collimator_thickness_cm': w_col_thickness,
            'w_side_collimator_expected_thickness_cm': W_COLLIMATOR_THICKNESS_CM,
            'w_side_collimator_x_range_cm': [w_col['params']['x0_cm'], w_col['params']['x1_cm']],
            'feedthrough_clear_radius_cm': finger_r + 0.08,
            'total_mass_kg': total,
            'active_csi_mass_kg': active,
            'non_active_mass_kg': total - active,
            'note': 'Design-level patch with explicit local checks. Final MEGAlib/Cosima CSG must implement the feedthrough holes/slots and run overlap/beam-path checks.'
        }
    }
    return bounds, comps, validation


def draw_rect(ax, x0, z0, x1, z1, mat, alpha=0.5, label=None, lw=0.35):
    ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0,
                           fc=COLORS.get(mat, '#cccccc'), ec='k', lw=lw, alpha=alpha))
    if label:
        ax.text((x0 + x1) / 2, (z0 + z1) / 2, label, fontsize=5.0, ha='center', va='center')


def draw_xz(comps: list[dict[str, Any]], path: Path, zoom: bool = False) -> None:
    fig, ax = plt.subplots(figsize=(12, 15) if not zoom else (12, 7))
    for c in comps:
        p, m, shape, cid = c['params'], c['material'], c['shape'], c['cid']
        if shape == 'z_cylinder':
            draw_rect(ax, -p['r_cm'], p['z_center_cm'] - p['h_cm']/2, p['r_cm'], p['z_center_cm'] + p['h_cm']/2, m, 0.58, cid)
        elif shape == 'z_cylinder_offaxis':
            draw_rect(ax, p['x_center_cm'] - p['r_cm'], p['z0_cm'], p['x_center_cm'] + p['r_cm'], p['z1_cm'], m, 0.75, cid)
        elif shape in ('z_annulus', 'z_annulus_phi', 'z_annulus_phi_segment'):
            for s in (-1, 1):
                draw_rect(ax, s*p['r_in_cm'], p.get('z0_cm', BEAM_Z-1), s*p['r_out_cm'], p.get('z1_cm', BEAM_Z+1), m, 0.35, cid if s == 1 else None, 0.25)
        elif shape == 'z_can_open_top':
            for s in (-1, 1):
                draw_rect(ax, s*p['r_in_cm'], p['z_in_bot_cm'], s*p['r_out_cm'], p['z_top_cm'], m, 0.30, cid if s == 1 else None)
            draw_rect(ax, -p['r_out_cm'], p['z_out_bot_cm'], p['r_out_cm'], p['z_in_bot_cm'], m, 0.22)
        elif shape == 'z_shell_top_annulus':
            for s in (-1, 1):
                draw_rect(ax, s*p['r_in_cm'], p['z_in_bot_cm'], s*p['r_out_cm'], p['z_top_cm'], m, 0.30, cid if s == 1 else None)
                draw_rect(ax, s*p['top_hole_r_cm'], p['top_ann_z0_cm'], s*p['r_out_cm'], p['top_ann_z1_cm'], m, 0.30)
            draw_rect(ax, -p['r_out_cm'], p['z_out_bot_cm'], p['r_out_cm'], p['z_in_bot_cm'], m, 0.20)
        elif shape in ('x_can', 'x_tube'):
            r = p['r_out_cm']; zc = p.get('axis_z_cm', BEAM_Z)
            draw_rect(ax, p['x0_cm'], zc - r, p['x1_cm'], zc + r, m, 0.14, cid)
            if 'plus_x_centerhub_feedthrough' in p:
                ft = p['plus_x_centerhub_feedthrough']; rr = ft['clear_radius_cm']; zz = ft['axis_z_cm']
                ax.add_patch(Rectangle((p['x1_cm'] - 0.18, zz - rr), 0.36, 2*rr, fill=False, ec='limegreen', lw=1.2))
            for ft in p.get('plus_x_thermal_finger_feedthroughs', []):
                rr = ft['clear_radius_cm']; zz = ft['axis_z_cm']
                ax.add_patch(Rectangle((p['x1_cm'] - 0.18, zz - rr), 0.36, 2*rr, fill=False, ec='limegreen', lw=1.0))
        elif shape == 'x_disc':
            t = max(p.get('thickness_cm', p.get('disc_t_cm', 0.03))/2, 0.03)
            draw_rect(ax, p['x_center_cm'] - t, p['axis_z_cm'] - p['r_cm'], p['x_center_cm'] + t, p['axis_z_cm'] + p['r_cm'], m, 0.85, cid)
        elif shape == 'x_annulus':
            t = max(p.get('thickness_cm', 0.30)/2, 0.05)
            draw_rect(ax, p['x_center_cm'] - t, p['axis_z_cm'] - p['r_out_cm'], p['x_center_cm'] + t, p['axis_z_cm'] + p['r_out_cm'], m, 0.72, cid)
            draw_rect(ax, p['x_center_cm'] - t, p['axis_z_cm'] - p['r_in_cm'], p['x_center_cm'] + t, p['axis_z_cm'] + p['r_in_cm'], 'Vacuum', 1.0)
        elif shape == 'x_cylinder_offaxis':
            draw_rect(ax, p['x0_cm'], p['z_center_cm'] - p['r_cm'], p['x1_cm'], p['z_center_cm'] + p['r_cm'], m, 0.85, cid)
        elif shape == 'x_disc_stack':
            for x in p['x_centers_cm']:
                draw_rect(ax, x - p['disc_t_cm']/2, p['axis_z_cm'] - p['disc_r_cm'], x + p['disc_t_cm']/2, p['axis_z_cm'] + p['disc_r_cm'], m, 0.85, cid)
        elif shape == 'box':
            if 'x0_cm' in p:
                draw_rect(ax, p['x0_cm'], p['z0_cm'], p['x1_cm'], p['z1_cm'], m, 0.75, cid)
            else:
                draw_rect(ax, p['x_cm'] - p['hx_cm'], p['z0_cm'], p['x_cm'] + p['hx_cm'], p['z1_cm'], m, 0.65, cid)
    ax.axhline(BEAM_Z, color='red', ls='--', lw=0.8, alpha=0.7)
    ax.annotate('511 keV photons from Laue lens\nside entry (-x → +x)',
                xy=(-18.2, BEAM_Z), xytext=(-27, BEAM_Z + 3),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.6), color='red', fontsize=9)
    ax.annotate('four off-axis Cu fingers\nsymmetric stems → MXC',
                xy=(4.8, BEAM_Z + OFFAXIS_FINGER_OFFSET_CM), xytext=(7.8, BEAM_Z + 3.5),
                arrowprops=dict(arrowstyle='->', color='limegreen', lw=1.6), color='green', fontsize=9)
    if zoom:
        ax.set_xlim(-15, 10); ax.set_ylim(-10.5, 2.8)
        ax.set_title('Off-axis four-finger patch zoom: support disk clears substrate; four Cu stems run to MXC')
    else:
        ax.set_xlim(-28, 21); ax.set_ylim(-22, 40)
        ax.set_title('DEMO2 DR_v3p5 minpatch + off-axis four-finger patch\nSupport disk clearance, four thermal fingers, and shared CsI side aperture updated')
    ax.set_aspect('equal'); ax.set_xlabel('X / cm'); ax.set_ylabel('Z / cm')
    handles = [Patch(fc=COLORS[m], ec='k', label=m) for m in ['CsI','W','Aluminium','Copper','Nb','Cryoperm','Ta','Silicon','CuNi','G10','Kapton']]
    ax.legend(handles=handles, loc='upper right', fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=200); plt.close(fig)


def write_csv(comps: list[dict[str, Any]], path: Path) -> None:
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['cid','name','category','material','shape','volume_cm3','mass_kg','install','why_for_sim','size_basis','source_tag','params'])
        for c in comps:
            w.writerow([c['cid'], c['name'], c['category'], c['material'], c['shape'], c['volume_cm3'], c['mass_kg'], c['install'], c['why_for_sim'], c['size_basis'], c['source_tag'], json.dumps(c['params'], ensure_ascii=False)])


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode('ascii')


def write_html(bounds: dict[str, Any], comps: list[dict[str, Any]], validation: dict[str, Any], html_path: Path, fig_xz: Path, fig_zoom: Path) -> None:
    rows = []
    for c in comps:
        rows.append(f"""
<tr><td>{c['cid']}</td><td><code>{html.escape(c['name'])}</code></td><td>{html.escape(c['category'])}</td><td>{html.escape(c['material'])}</td><td>{c['mass_kg']:.4f}</td><td><code>{html.escape(c['shape'])}</code></td><td>{html.escape(c['install'])}</td><td>{html.escape(c['why_for_sim'])}</td><td>{html.escape(c['size_basis'])}</td><td>{html.escape(c['source_tag'])}</td></tr>""")
    html_text = f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><title>{VERSION}</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,'Noto Sans SC',sans-serif;background:#f8fafc;color:#111827;margin:0;line-height:1.55}}main{{max-width:1500px;margin:auto;padding:24px}}section{{background:white;border:1px solid #d1d5db;border-radius:12px;padding:20px;margin:18px 0}}img{{max-width:100%;border:1px solid #ddd;border-radius:8px}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border:1px solid #ddd;padding:7px;vertical-align:top}}th{{background:#f3f4f6}}code{{background:#f3f4f6;padding:1px 4px;border-radius:4px}}</style></head>
<body><main>
<section><h1>DEMO2 DR v3p5 minpatch + off-axis four-finger patch</h1>
<p><b>Policy:</b> 以 <code>DEMO2_DR_v3p5_minpatch_three_fixes</code> 为准，修复支撑盘间隙、将中心热指改为四根对称 off-axis 热指，把 CsI 侧孔声明到相邻两个扇区，并将 W 侧入射准直 sleeve 缩短为 2 cm。</p>
<ol><li><b>Support disk</b> 后移，和最后一层 Si substrate 保留 0.5 mm 间隙。</li><li><b>Four Cu fingers</b> 位于光轴四象限对称位置，不再沿 <code>y=0,z=-5.2 cm</code> 中心光轴布置。</li><li><b>Nb/Cryoperm/Al sample-box replacement shells</b> 声明四个 +x thermal feedthrough 和 top stem slots；最终 MEGAlib/Cosima CSG 必须显式切孔。</li><li><b>CsI side aperture</b> 同时声明在 segment 03/04，避免光孔落在单侧扇区边界。</li><li><b>W side collimator</b> 为 2 cm 厚方孔 sleeve，作为局部漏光抑制，不作为 376 孔长准直器。</li></ol>
<p><b>Total mass:</b> {bounds['META']['total_mass_kg']:.3f} kg; <b>CsI:</b> {bounds['META']['active_csi_mass_kg']:.3f} kg; <b>non-active:</b> {bounds['META']['non_active_mass_kg']:.3f} kg.</p></section>
<section><h2>Global X-Z</h2><img src='data:image/png;base64,{b64(fig_xz)}'></section>
<section><h2>Detector bay zoom</h2><img src='data:image/png;base64,{b64(fig_zoom)}'></section>
<section><h2>Validation</h2><pre>{html.escape(json.dumps(validation,indent=2,ensure_ascii=False))}</pre></section>
<section><h2>Full component list</h2><table><thead><tr><th>CID</th><th>Name</th><th>Category</th><th>Material</th><th>Mass kg</th><th>Shape</th><th>Install</th><th>Why needed</th><th>Size basis</th><th>Source/basis</th></tr></thead><tbody>{''.join(rows)}</tbody></table></section>
</main></body></html>"""
    html_path.write_text(html_text, encoding='utf-8')


def write_megalib_guide(path: Path) -> None:
    path.write_text(f"""# MEGAlib / Cosima implementation guide for `{VERSION}`

## Geometry authority
Use `DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json` as the source of truth.  The CSV is a convenience mass table only.

This model is intentionally a **proxy mass model**, not final CAD.  The changes relative to `DEMO2_DR_v3p5_minpatch_three_fixes` are the downstream support-disk clearance, four symmetric off-axis Cu cold fingers/stems, the shared CsI side-port declaration, and a 2 cm side-entry W sleeve/collimator.

## Coordinate convention

- Units are cm.
- The 511 keV optical beam travels along `-x -> +x`.
- Beam axis is `y = 0`, `z = -5.2 cm`.
- The DR remains upright: 300 K service side is on top; MXC is at the bottom.

## Components that require explicit CSG holes

The following are **not optional annotations**.  In the MEGAlib `.geo`, implement them either by splitting the shell into PCON/BRIK panels around the hole or by using the project's supported Boolean/subtraction equivalent.

### Side optical port chain

For each side-window shell or liner, cut a side aperture centered at `y = 0`, `z = -5.2 cm`, with the radius listed in the component parameters:

- `Nb_SideEntry_Sample_Can_with_side_aperture`
- `Cryoperm_Horizontal_Sleeve_1p2mm`
- `Al_50mK_Local_Can_side_entry`
- `Still_Shield_Al_side_window`
- `Shield_4K_Al_side_window`
- `Shield_60K_Al_side_window`
- `Vacuum_Jacket_Al_266mmClass_side_port`
- `Passive_Cu_Liner_detector_bay`
- `Passive_W_Liner_detector_bay`
- `CsI_Side_Segment_03`
- `CsI_Side_Segment_04`
- `ActiveShield_Al_Backplane_detector_bay`
- `ActiveShield_Flex_Kapton_detector_bay`
- `Outer_Al_Mechanical_Shell_detector_bay`

Window/filter discs are separate volumes aligned to this port:

- `Win_50mK_Al_foil_side`
- `Win_Still_Al_foil_side`
- `Win_4K_Al_foil_side`
- `Win_60K_Al_foil_side`
- `Win_Be_Vacuum_150um_side`
- `Win_Outer_Al_Filter_side`

### Off-axis thermal-finger feedthroughs

The four-finger patch adds four symmetric off-axis thermal paths:

- four `Cu_ColdFinger_OffAxis_*_from_Disk_to_Stem` x-axis fingers;
- four `Cu_ColdFinger_Stem_*_to_MXC` vertical stems;
- four `Cu_MXC_Clamp_Pad_*_for_OffAxisStem` clamp pads.

Implement the following declared feedthroughs:

1. In `Nb_SideEntry_Sample_Can_with_side_aperture`, cut all holes listed in `plus_x_thermal_finger_feedthroughs`.
2. In `Cryoperm_Horizontal_Sleeve_1p2mm`, cut the same four +x cap feedthroughs.
3. In `Al_50mK_Local_Can_side_entry`, cut the four +x feedthroughs plus all `top_stem_slots` so each vertical stem reaches the MXC plate bottom.

Do **not** leave thermal fingers/stems overlapping closed end caps; the feedthroughs and stem slots are part of the geometry definition.

## Suggested MEGAlib shape mapping

- `z_cylinder`: PCON cylinder or TUBE aligned with z.
- `z_annulus`: PCON annular cylinder.
- `z_annulus_phi` / `z_annulus_phi_segment`: PCON with phi start/delta or split BRIK/sector approximations if needed.
- `x_disc`: PCON/TUBE rotated by 90° so its axis is x; if rotation is inconvenient, use a thin BRIK proxy only for a systematic check.
- `x_annulus`: rotated annular PCON/TUBE.  The support rings are physically important because the center must remain open.
- `x_cylinder_offaxis`: rotated cylinder; used for the Cu support rods and off-axis thermal fingers.
- `z_cylinder_offaxis`: cylinder aligned with z at an offset x/y; used for off-axis stems and clamp pads.
- `x_can`: implement as a hollow shell with end-cap panels and declared openings, not as a solid filled box.

## Mother / daughter hierarchy recommendation

A robust first MEGAlib implementation is:

1. World
2. Detector-bay vacuum jacket / cryostat volume
3. Thermal shields as daughters or siblings with non-overlapping shells
4. Magnetic sample can / Cryoperm / Nb shells
5. TES / substrates and Cu support frame inside the hollow sample-can region
6. Active CsI and outer package outside the cryostat, not inside it

## Validation steps before production transport

1. Generate `.geo` and `.det` from the JSON.
2. Run MEGAlib/Cosima overlap check.
3. Confirm that the beam path along `y=0, z=-5.2` intersects only the intended windows/filters and the TES stack, not closed shell material.
4. Confirm that the four off-axis fingers/stems touch or overlap only through declared feedthrough / union regions.
5. Recompute mass by material and compare to `DEMO2_DR_v3p5_minpatch_centerfinger_mass_budget.csv`.

## Physics/systematic follow-up

The main nominal choice left for simulation is not this feedthrough detail but material systematics:

- MXC copper plate vs Au-plated Al substitute for Cu-64 risk.
- Cryoperm 1.2 mm vs thicker magnetic-shield systematic.
- CsI side thickness 4/6/8 cm.
- Remote PT / compressor / open-cycle DR platform alternatives.
""", encoding='utf-8')


def main() -> None:
    bounds, comps, validation = load_and_patch()
    prefix = VERSION
    out_bounds = ROOT / f'{prefix}_bounds.json'
    out_csv = ROOT / f'{prefix}_mass_budget.csv'
    out_val = ROOT / f'{prefix}_validation.json'
    out_html = ROOT / f'{prefix}_review.html'
    out_md = ROOT / f'{prefix}_MEGAlib_implementation_guide.md'
    fig_xz = ASSET / f'{prefix}_xz.png'
    fig_zoom = ASSET / f'{prefix}_zoom.png'
    zip_path = ROOT / f'{prefix}_package.zip'

    out_bounds.write_text(json.dumps(bounds, indent=2, ensure_ascii=False), encoding='utf-8')
    write_csv(comps, out_csv)
    out_val.write_text(json.dumps(validation, indent=2, ensure_ascii=False), encoding='utf-8')
    draw_xz(comps, fig_xz, zoom=False)
    draw_xz(comps, fig_zoom, zoom=True)
    write_html(bounds, comps, validation, out_html, fig_xz, fig_zoom)
    write_megalib_guide(out_md)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in [Path(__file__), out_bounds, out_csv, out_val, out_html, out_md, fig_xz, fig_zoom, BASE_JSON]:
            z.write(p, arcname=p.name if p.parent == ROOT else f'{p.parent.name}/{p.name}')
    print(json.dumps({'version': prefix, 'total_kg': bounds['META']['total_mass_kg'], 'zip': str(zip_path)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
