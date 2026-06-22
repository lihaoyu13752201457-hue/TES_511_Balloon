# Step01 Geometry

Step01 creates the clean `new_geo_re` geometry checkpoint.

## Authority

- DEMO2 source generator: `tmp_mass_model_review_bundle/DEMO2/build_demo2_mass_model.py`
- Installed compatibility path: `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/`
- Legacy v4c generator/provenance file:
  `code/geometry/GenerateGeo_ADR_v4c_mkflange.py`
- Cm output: `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/`
- Schematic: `records/00_geometry/geo.png`
- WRL visualization: `stepwise_maintenance/step01_geo/outputs/TibetTES_ADR_v4c_mkflange_step01.wrl`
- Step01 2D schematic copy: `stepwise_maintenance/step01_geo/outputs/TibetTES_ADR_v4c_mkflange_step01_2d_schematic.png`
- Consolidated stepwise visual outputs: `stepwise_maintenance/outputs/geometry/`
- Cavity/window z audit: `stepwise_maintenance/step01_geo/outputs/cavity_window_z_audit.md`

## Fix Be-Window Reference

The aperture reference is the cm-fixed `fix` Be window:

- `fix/stepwise_maintenance/step1_geo/source_snapshots/TibetTES_v5_6layers.geo`
- `Win_Be.Shape PCON ... -0.0075 0 1.898 0.0075 0 1.898`
- Radius: `1.898 cm`
- Thickness: `0.015 cm`

In the DEMO2 source generator this is represented directly in cm:

- `entrance_r = 1.898`
- `Win_Be_Cryostat.thick = 0.015`

## Geometry Changes

The ADR v4c envelope is kept close to `new_geo`. DEMO2 is the detector-layout
reference, but this is an engineering background mass model rather than a final
DEMO2 CAD reproduction. Step01 changes are limited to the aperture/window model:

- `TES_SampleBox_Cu.hole = 1.898 cm`
- `Nb_SC_Detector_Can.hole = 1.898 cm`
- `Thermal_50mK_Al_Shield.hole = 1.898 cm`
- `Thermal_1K_Al_Shield.hole = 1.898 cm`
- `Thermal_4K_Al_Shield.hole = 1.898 cm`
- `Thermal_60K_Al_Shield.hole = 1.898 cm`
- `Vacuum_Jacket_Al.hole = 1.898 cm`
- `CsI_Active_Shield.hole = 1.898 cm`
- `Outer_Al_Mech_Shell.hole = 1.898 cm`

Added thin Al windows:

- `Win_50mK_Al_Shield`
- `Win_1K_Al_Shield`
- `Win_4K_Al_Shield`
- `Win_60K_Al_Shield`
- `Win_Vacuum_Al_Filter`

Removed simplifications:

- `A4K_Mag_Can` and `Win_A4K_Mag_Can` are omitted from the gamma-background prototype.
- A continuous Nb detector-can window is not retained in the current cm
  authority; the Nb can is represented as an open-bottom can with matched top
  aperture.
- The vacuum-jacket aperture is represented by `Win_Be_Cryostat` plus the thin
  `Win_Vacuum_Al_Filter` proxy.

All window radii are `1.898 cm`.

## ADR / Passive Proxy Labels

The 2D schematic labels the current `bounds.json` proxy structures, so it can
be read as a mass-model map instead of only a detector sketch:

- `Cryoperm_Inner_Mag_Shield`: simplified Ni-rich magnetic shield around the Nb
  detector can.
- `ADR_Magnet_Coil_Cu`: copper-equivalent ADR magnet/coil mass.
- `ADR_Magnet_Yoke_Fe`: low-carbon steel return-yoke activation/scattering
  proxy.
- `ADR_SaltPill_Proxy` and `ADR_SaltPill_Cu_Can`: GGG-like paramagnetic
  salt-pill/regenerator proxy plus copper can/collar.
- `Thermal_Bus_Cu`, `ADR_HeatSwitch_Stainless_Link`, and
  `PulseTube_ColdHead_Interface_Cu`: thermal bus, heat-switch/link, and
  cold-head interface masses.
- `Passive_Cu_Inner_Liner`, `Passive_W_Outer_Liner`,
  `Passive_Bottom_W_Shield`, and `Passive_Top_W_Aperture_Annulus`: Cu/W
  passive shielding outside the dewar and around the entrance aperture.

The full A4K/Cryoperm shield stack is not modeled; the current geometry includes
only the single simplified `Cryoperm_Inner_Mag_Shield` proxy.

## Reference Basis

The geometry is constrained by DEMO2-like detector layout and the following
recorded public/existing references:

- Danaher Cryogenics / HPD Model 103 Rainier ADR: staged ADR/cold-plate,
  vacuum-jacket, radiation-shield, heat-switch, and experimental-space scale.
- 511-CAM mission paper: 511 keV telescope focal-plane context, active shield
  outside cryostat, passive tungsten shielding, and Nb/A4K magnetic-shield
  discussion.
- Kurt J. Lesker aluminum chamber public note: Al vacuum-jacket/outer-shell
  material motivation.
- Oxford Instruments Be-window public note: order-of-magnitude Be window
  thickness motivation.
- Existing `fix` geometry: Be-window clear radius and aperture convention
  (`1.898 cm`).

## Rebuild

For the current DEMO2 authority, do not regenerate from
`code/geometry/GenerateGeo_ADR_v4c_mkflange.py` unless that legacy generator has
first been reconciled with the installed DEMO2 `bounds.json`. To refresh the
maintenance visual/audit artifacts from the installed authority:

```bash
python3 records/00_geometry/make_geo_2d_schematic.py
python3 stepwise_maintenance/step01_geo/code/build_step01_geo.py
```

The DEMO2 source generator is retained at
`tmp_mass_model_review_bundle/DEMO2/build_demo2_mass_model.py`; the mainline
transport chain uses its output after installation into the legacy
`outputs/geometry/XZTES_ADR_v4c_mkflange_cm/` path.

## Verification Snapshot

The generated `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/bounds.json` reports:

- units: `cm`
- Be window: radius `1.898 cm`, thickness `0.015 cm`
- windows: `7`
- Al/windows stack: `SampleBox_Al_Window`, `Win_50mK_Al_Shield`,
  `Win_1K_Al_Shield`, `Win_4K_Al_Shield`, `Win_60K_Al_Shield`,
  `Win_Vacuum_Al_Filter`
- TES pixel thickness: `0.3 cm`
- z audit: every assigned cavity-closure window has its center inside the corresponding top-cap z interval; active shield and outer mechanical shell remain open apertures with Be-matched radius.

`source_snapshots/` contains the Step01 generator and generated lightweight geometry files. No `.sim.gz` or `.dat` simulation products are stored here.
