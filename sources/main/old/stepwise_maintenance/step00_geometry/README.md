# Step00 Geometry

## Current Authority: DEMO2_DR_v3p5 Center-Finger Simulation Proxy

Status: simulation-layer closed for the current side-entry center-finger geometry.

This Step00 authority uses the latest `geo_refer/DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json`
design package and the MEGAlib/Cosima proxy geometry generated at:

- `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det`
- `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/geometry_proxy_validation.json`

Acceptance checks:

- source design validation: `DESIGN_PASS`
- proxy geometry validation: `PROXY_PASS`
- Cosima `CheckForOverlaps`: `PASS` at `10000` points and `0.0001 cm` tolerance
- Cosima log contains no `GeomVol1002` and no `Overlap is detected`
- beam-path proxy check: `PASS`
- detector-core check: `PASS` (`6` MDCalorimeter layers, `376` TES pixels/layer, `2256` TES pixel copies total)
- W side collimator: `2 cm` thick square-bore sleeve, `x = -18..-16 cm`
- simulation pointing: `InstrumentFrame.Rotation 0 45 0`; local side-window `-x` look axis is `45 deg` above the global zenith-frame horizon
- setup/far-field sphere: `SurroundingSphere 60 4.49012806 0 4.49012806 60`
- source components: `95`
- generated MEGAlib volumes in Step00 WRL parse: `2422`
- total source mass: `91.01274312824565 kg`
- active CsI mass: `62.83369781500205 kg`

Step00 v3p5 visualization outputs:

- 3D WRL: `stepwise_maintenance/step00_geometry/outputs/v3p5_centerfinger/DEMO2_DR_v3p5_centerfinger_step00.wrl`
- 2D schematic: `stepwise_maintenance/step00_geometry/outputs/v3p5_centerfinger/DEMO2_DR_v3p5_centerfinger_step00_2d_schematic.png`
- X-Z overview: `stepwise_maintenance/step00_geometry/outputs/v3p5_centerfinger/DEMO2_DR_v3p5_centerfinger_step00_xz_overview.png`
- closure manifest: `stepwise_maintenance/step00_geometry/outputs/v3p5_centerfinger/step00_v3p5_centerfinger_closure.json`

Rebuild command:

```bash
python3 stepwise_maintenance/step00_geometry/code/build_v3p5_centerfinger_step00.py
```

Scope note: this is a simulation proxy, not final CAD. x-axis circular parts and side holes are represented by MEGAlib-compatible BRIK/PCON proxy approximations, with explicit overlap and beam-path gates.

The 2D schematic uses the local detector design coordinates for readability.
The WRL wraps the full model in the same 45 deg `InstrumentFrame` rotation used
by Cosima.

## Legacy Geometry: DEMO2_DR_v2p2 Cu64-Fix

Status: generated from `geo_refer/DEMO2_DR_v2p1_bounds.json` with the requested Cu64 mitigation.

## Geometry Change

- Removed `TES_SampleBox_Cu` from the simulation authority.
- Removed the old outer `Cryoperm_Inner_Mag_Shield` proxy to avoid duplicate magnetic-shield material after the move.
- Added `TES_SampleBox_Cryoperm` in the former Cu sample-box envelope: `r=3.4-3.7 cm`, `z=0.25-8.7 cm`, top aperture `r=1.898 cm`.
- Added a bottom-center hole `r=0.40 cm` in that sample box.
- Added `SampleBox_Cu_ThermalFinger_50mK`, a short Cu cylinder from `z=0.25` to `0.55 cm`, touching the 50 mK/MXC cold plate at the lower face and the sample-box bottom-hole boundary at the upper face.
- Retained the thin `SampleBox_Al_Window` top foil as a low-Z aperture foil, not as part of the removed Cu box.

## Simulation Files

- `outputs/geometry/DEMO2_DR_v2p2_cu64fix/DEMO2_DR_v2p2_cu64fix.geo.setup`
- `outputs/geometry/DEMO2_DR_v2p2_cu64fix/DEMO2_DR_v2p2_cu64fix.geo`
- `outputs/geometry/DEMO2_DR_v2p2_cu64fix/DEMO2_DR_v2p2_cu64fix.det`
- `outputs/geometry/DEMO2_DR_v2p2_cu64fix/Materials_DEMO2_DR_v2p2.geo`
- `outputs/geometry/DEMO2_DR_v2p2_cu64fix/bounds.json`
- `outputs/geometry/DEMO2_DR_v2p2_cu64fix/mass_budget.csv`
- `outputs/geometry/DEMO2_DR_v2p2_cu64fix/geometry_validation.json`

## Visualization

- `stepwise_maintenance/step00_geometry/outputs/DEMO2_DR_v2p2_all_components_xz.png`

## Validation

- local design validation status: `PASS`
- design overlap problem count: `0`
- Native MEGAlib `Trigger/Veto` blocks are intentionally absent from the `.det`; active shield segments are sensitive volumes and downstream analysis should perform the summed-veto logic.

This is a Step00 geometry authority. Before Step02 production, run a Cosima/geomega overlap check on the generated `.geo.setup`.
