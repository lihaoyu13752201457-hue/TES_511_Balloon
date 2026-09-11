# TES_511_Balloon Optics/Bridge Copy Index

Date: 2026-06-12

This file records the focusing-optics and Opticsim-to-MEGAlib bridge package
copied from:

`/home/ubuntu/codex_tes_511_sim/new_geo_re`

to:

`/home/ubuntu/TES_511_Balloon`

## Copied Directories

1. `stepwise_maintenance/step04_opticsim/`
   - Step04 Laue focusing optics code.
   - f9m reference optics authority and configs.
   - f10m A1 candidate profile:
     - `ge111_balloon511_f10m_511keV_design_summary.json`
     - `ge111_balloon511_f10m_511keV_line_config.csv`
     - `ge111_balloon511_f10m_511keV_xop_map.csv`
     - `optics_aeff_authority_f10m_20260611.json`
     - `optics_aeff_authority_f10m_a1.json`
     - `outputs/opticsim_laue_bfull_f10m_a1_r2_3seed/`

2. `stepwise_maintenance/step09_optics_bridge/`
   - EventList bridge builder:
     - `code/build_step09_optics_bridge.py`
   - detector-coupled focus response builder:
     - `code/build_detector_coupled_focus_response.py`
   - f10m embedding validator:
     - `code/validate_f10m_embed.py`
   - f9m bridge outputs:
     - `outputs/`
   - f10m A1 bridge outputs:
     - `outputs_f10m_a1/`

3. `runs/step09_optics_bridge/`
   - copied lightweight/full Step09 simulation products already available in
     `new_geo_re`, including the f10m A1 smoke run.

## Rebuild Commands

Default f9m bridge:

```bash
python3 stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py
```

f10m A1 bridge:

```bash
STEP09_OPTICS_PROFILE=f10m_a1 python3 stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py
```

f10m A1 embedding validation:

```bash
python3 stepwise_maintenance/step09_optics_bridge/code/validate_f10m_embed.py
```

## Current Technical Boundary

The copied bridge code still uses the `new_geo_re` geometry binding:

```python
BOUNDS = outputs/geometry/XZTES_ADR_v4c_mkflange_cm/bounds.json
GEOMETRY = outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup
```

The current `TES_511_Balloon` geometry products are under `outputs/geometry/DEMO2_DR_*`.
Before running new TES simulations from this bridge, update the bridge geometry
binding or add a geometry adapter so the injection plane, Be-window radius, and
`.geo.setup` path match the active TES geometry.

## Claim Boundary

The f10m A1 profile is copied as an embeddable candidate profile. It is not yet
the promoted science headline. Promotion still requires full non-smoke Step09
transport, detector-coupled response rebuild, and downstream Step07/Step08
rebuilds against the active TES geometry.
