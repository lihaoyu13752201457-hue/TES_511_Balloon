# Route-A B-FULL Laue Lens Design Rationale (2026-06-01)

## Scope

This is the review package requested by `LAUE_LENS_DESIGN_SPEC_20260601.md`: design a physically plausible Ge(111) Laue focusing mirror for 480-550 keV, run the B-FULL optical simulation, and stop before the detector full-chain integration.

## Selected Design

- Design name: `balloon511_f9m_ge111_511line`.
- Material/reflection: Ge(111), d = `3.266590088` Angstrom.
- Focal length: `9.0 m`.
- Tile size: `15.0 mm x 15.0 mm`.
- Ring z pitch: `0.0 mm`.
- Mosaicity: `30.0 arcsec`.
- Energies: `511 keV`.
- Total tiles: `27`.
- Total geometric crystal area: `60.75 cm2`.
- Exact 511-keV A_eff: `15.2993 cm2`.
- Design target A_eff(511): `16 cm2` with `0.15` fractional tolerance.
- A_eff target residual: `0.043795`.
- Sampled line-band A_eff sum: `15.2993 cm2`.
- Natural mosaic passband FWHM: `500.994-521.006 keV` (`20.0121 keV` full width).
- Ge mass estimate for active crystals only: `0.330448 kg`.
- Outer ring radius plus half tile: `74.3501 mm`.

## Physical Justification

- The optical design is now 511-line first. The 480-550 keV interval is treated as the detector analysis window for line fitting and local continuum, not as an equal-weight Laue focusing band.
- The 9 m focal length is the upper end of the 6-9 m balloon-compatible execution envelope and stays close to the 8.3 m 511-CAM Laue-lens scale obtained by scaling the CLAIRE balloon lens concept from 170 keV to 511 keV.
- The optical area is placed in a full-azimuth 511-keV ring rather than split into broad 480/550 keV endpoint rings.
- 15 mm square Ge tiles are at the upper end of the common 5-15 mm Laue-crystal scale and give near-full azimuthal fill at the 511-keV Bragg radius without chord-overlap.
- The 30 arcsec mosaicity gives the design natural FWHM passband through DeltaE/E = cot(theta_B) * mosaic_FWHM_rad. For Ge(111) at 511 keV this is about 511 +/- 10 keV.
- A tested 507-515 keV multi-ring axial stack was rejected because overlapping projected apertures caused upstream rings to shadow the 511-keV anchor ring. This baseline keeps the projected aperture honest.
- The minimum within-ring azimuthal edge gap is `0.521654 mm`.
- The 30 arcsec mosaicity is retained because it is the already validated B-FULL baseline and lies inside the 10-60 arcsec quality range quoted for Laue-lens crystals.
- The 511-keV ring uses the existing XOP/CRYSTAL rocking curve and B-FULL is run with the map required.

Public anchors used for review wording:

- CLAIRE demonstrated a balloon Laue lens using 556 Ge-Si crystals on eight rings.
- MAX/GRI/LAUE studies use mosaicities around 30 arcsec and focal lengths from about 10 m to much longer formation-flying concepts.
- 511-CAM is a 511-keV line instrument; o-Ps continuum is below 511 keV and is kept as detector-side analysis/future-prospect context rather than the Laue optical driver.

## Ring Table

| ring | E keV | z mm | radius mm | n tiles | geom area cm2 | thickness mm | analytic eff | emergent within-Be eff | A_eff cm2 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 511 | 0.000000e+00 | 66.8501 | 27 | 60.75 | 10.2188 | 0.257481 | 0.25184 | 15.2993 |

## Be-Window Focus Check

- Be radius requirement: `r99 <= 1.898 cm`.
- Diffracted focal rows: `12605`.
- Within-Be focal rows: `12592`.
- r95 all diffracted crossings: `0.219108 cm`.
- r99 all diffracted crossings: `0.29141 cm`.
- Outside-Be focal rows: `13`.
- Within-Be fraction: `0.998969`.
- Max within-Be focal radius: `1.45767 cm`.
- Max all-diffracted radius: `17.7637 cm`.
- Pass: `True`.

## Cross-Check Gate

- B-FULL run status: `RUN_AVAILABLE`.
- Rocking curve map: `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step04_opticsim/ge111_balloon511_f9m_511keV_xop_map.csv`.
- Emergent focal diffraction fraction: `0.2521`.
- Analytic reference focal diffraction fraction: `0.257481`.
- Emergent minus analytic: `-0.00538123`.
- Pass <0.04 design-stage gate: `True`.
- Strict <0.01 diagnostic gate: `True`.

## Review Boundary

Per the design spec, this package stops at the optical design review gate. It does not replace Step07, does not run detector full-chain transport, and does not add lens hardware mass to the DEMO2 background model.

## Artifacts

- Ring config: `/home/ubuntu/opticsim/data/laue/ge111_balloon511_f9m_511keV_line_config.csv`.
- Repository copy of ring config: `stepwise_maintenance/step04_opticsim/ge111_balloon511_f9m_511keV_line_config.csv`.
- Rocking-curve map: `stepwise_maintenance/step04_opticsim/ge111_balloon511_f9m_511keV_xop_map.csv`.
- A_eff authority: `stepwise_maintenance/step04_opticsim/optics_aeff_authority.json`.
- Cross-check report: `stepwise_maintenance/step04_opticsim/real_design_crosscheck_20260601.md`.
- B-FULL output directory: `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_xopmap_real`.
