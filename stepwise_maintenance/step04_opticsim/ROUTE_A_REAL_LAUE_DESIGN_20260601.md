# Route-A Real Laue Lens Design Log (2026-06-01)

## Scope

This supersedes the earlier 35 m broad-band endpoint design. The updated Route-A optics package follows `FOCUSING_LENS_SCIENCE_RATIONALE_20260601.md`: the Laue optics are optimized for the 511 keV line, while 480-550 keV is treated as the TES spectral analysis window for line fitting and local continuum.

Detector full-chain transport, Step07 replacement, and detector mass-model changes are intentionally not run here.

## Selected Design

- Design: `balloon511_f8p3m_ge111_511line`
- Material/reflection: Ge(111), d = 3.266590088 Angstrom
- Optical ring energy: 511 keV
- Focal length: 8.3 m
- Tile size: 15 mm x 15 mm
- Mosaicity: 30 arcsec
- Total crystals: 24
- Total geometric crystal area: 54.0 cm2
- Active Ge crystal mass estimate: 0.294 kg
- Bragg ring radius: 61.6507 mm
- Outer active radius including half tile: 69.1507 mm

The rejected intermediate 507-515 keV stacked-ring concept produced upstream-ring shadowing in B-FULL: the 511-keV anchor A_eff dropped to 4.38 cm2 and the emergent-vs-analytic gate failed. The accepted baseline uses one full-azimuth 511-keV ring so the projected aperture is not double-counted or shadowed.

## Artifacts

- Ring config for B-FULL: `/home/ubuntu/opticsim/data/laue/ge111_balloon511_f8p3m_511keV_line_config.csv`
- Repository copy: `stepwise_maintenance/step04_opticsim/ge111_balloon511_f8p3m_511keV_line_config.csv`
- Rocking-curve map: `stepwise_maintenance/step04_opticsim/ge111_balloon511_f8p3m_511keV_xop_map.csv`
- Rationale: `stepwise_maintenance/step04_opticsim/optics_design_rationale.md`
- A_eff authority: `stepwise_maintenance/step04_opticsim/optics_aeff_authority.json`
- Cross-check report: `stepwise_maintenance/step04_opticsim/real_design_crosscheck_20260601.md`
- B-FULL run directory, not committed: `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_xopmap_real`

## B-FULL Results

- Run status: `RUN_AVAILABLE`
- Primaries: 50,000
- Diffracted focal crossings: 12,566
- Within-Be diffracted crossings: 12,552
- r99 of all diffracted focal crossings: 0.270588 cm
- Be radius gate: 1.898 cm
- Emergent focal diffraction fraction: 0.25132
- Analytic reference focal diffraction fraction: 0.257481
- Emergent minus analytic: -0.00616123
- Strict residual gate abs(delta) < 0.01: pass
- Focal/history join: 0 unmatched diffracted focal rows. Two all-diffracted focal rows have post-diffraction energy changes and are outside the Be window; within-Be science rows remain on the 511-keV source line.

## Effective Area

| E keV | geometric area cm2 | emergent within-Be efficiency | A_eff cm2 |
| ---: | ---: | ---: | ---: |
| 511 | 54.0 | 0.251040 | 13.5562 |

## Verification

- `cmake --build /tmp/opticsim-bfull-build --target laue_multiring_bfull_demo -j4`: PASS.
- B-FULL 50k run with `--focal-mm 8300` and `--require-rocking-curve-map`: PASS.
- `python3 stepwise_maintenance/step04_opticsim/code/build_real_laue_lens_design_20260601.py`: PASS, regenerated the design package from the B-FULL run.

## Review Boundary

This is the current optics stop point. Step B should use this 511-line A_eff and `focal_crossings.csv` only after accepting the 511-line-first optical concept.
