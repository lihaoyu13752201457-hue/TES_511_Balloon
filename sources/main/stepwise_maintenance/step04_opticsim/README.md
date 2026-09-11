# Step04 Opticsim Laue Audit

Status: `PASS_BFULL_XOPMAP_EVENTLIST_READY`.

This step now uses the B-FULL Laue optics model selected in the 2026-06-01 review. Channel optics is not used.

## Main Conclusion

- Nominal optical handoff: B-FULL 511-keV Ge(111) line-focused Laue lens with the external 511-keV XOP/CRYSTAL rocking-curve map.
- Implementation evidence: `/home/ubuntu/opticsim` commit `792fb9f8995275637441dcf608135a14bdbe8d3d` from `2026-06-01 23:49:09 +0800` plus local B-FULL worktree changes (`git status --short` is recorded in the audit JSON).
- B-FULL process: `G4VDiscreteProcess`, non-forced finite diffraction MFP, standard Geant4 EM enabled: `True`.
- Energy window: `511-511 keV`, focal length `9000 mm`.
- XOP-map run: `n=50000`, diffracted focal crossings `12605`, emergent focal diffraction fraction `0.2521` vs analytic/reference `0.257481`.
- Online Darwin-Hamilton cross-check: not separately required for this one-ring XOP-anchor replacement; the nominal run itself is checked against the XOP/analytic reference.
- Be-window gate (tracked diffracted): focused signal within Be `12592` rows, `r95=0.219108 cm`, `r99=0.29141 cm`, Be radius `1.898 cm`, r99 margin `1.60659 cm` (a few scattered gammas reach `rmax=17.7637 cm` and miss the TES).

## f10m A1 Embedding Profile

Status: `PASS_F10M_EMBED_READY` as a selectable candidate profile, not yet the
published headline chain.

- Profile name: `f10m_a1`.
- Optics model: `balloon511_f10m_ge111_511line_a1`.
- Authority: `stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json`.
- Phase-0 source authority copy: `stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_20260611.json`.
- Embedded focal crossings: `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_f10m_a1_r2_3seed/focal_crossings.csv`.
- A_eff(511): `20.08476 cm2` from the three-seed A1/R2 honest tile-footprint aggregate.
- EventList-ready rows within Be: `37194`.

Build the f10m Step09 EventList/source with:

```bash
STEP09_OPTICS_PROFILE=f10m_a1 python3 stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py
```

Validate the embedding with:

```bash
python3 stepwise_maintenance/step09_optics_bridge/code/validate_f10m_embed.py
```

Promotion boundary: switching the science headline from f9m to f10m still
requires the full non-smoke Step09 detector transport and a rebuild of the
detector-coupled response plus Step07/Step08 products.

## Geometry And Materials

- Optical material: Ge(111), d-spacing `3.266590088 A`.
- Rings: 1 ring at 511 keV. The 480-550 keV interval is a detector analysis window, not the optical focusing band.
- Ring radii: `66.8501-66.8501 mm`.
- Tiles: `27` tiles, `15 mm` square.
- Crystal thickness: `10.2188-10.2188 mm`.
- Detector entrance authority remains `new_geo_re`: Be window radius `1.898 cm`, Be thickness `0.015 cm`; staged Al thermal foils and W aperture stop are already in the detector mass model.

## Scope Control

- This replaces the earlier broad-band endpoint Laue package for focused photons.
- It does not add the Laue lens mechanical mass into the MEGAlib detector geometry yet.
- Prompt cosmic-ray and neutron/proton activation of the optics solid angle are therefore still a future full-chain task, not part of this Step04/Step09 focused-photon replacement.
- The lens is a compact 511-line optics baseline. A broad o-Ps/continuum measurement remains detector-side analysis or future large-lens work, not this optical baseline.

## Outputs

- Nominal B-FULL XOP-map run: `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_xopmap_real`.
- Online cross-check run: `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_xopmap_real`.
- Audit JSON: `stepwise_maintenance/step04_opticsim/outputs/step04_opticsim_audit.json`.
- WRL: `stepwise_maintenance/step04_opticsim/outputs/laue_bfull_xopmap_real_particles.wrl`.
- 2D schematic: `stepwise_maintenance/step04_opticsim/outputs/laue_bfull_xopmap_real_2d_schematic.png`.
- Stage summary: `stepwise_maintenance/step04_opticsim/outputs/laue_bfull_xopmap_stage_summary.csv`.

## Rebuild

The retained B-FULL runs were generated with Geant4 11.4 using a clean Geant4 data environment, then this audit was rebuilt with:

```bash
python3 stepwise_maintenance/step04_opticsim/code/build_step04_opticsim_audit.py
```
