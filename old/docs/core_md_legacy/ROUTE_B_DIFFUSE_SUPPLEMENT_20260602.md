# Route B Diffuse Supplement (2026-06-02)

2026-06-12 review hold: this supplement uses legacy DEMO2/mainline W2
background values (`0.184347` and `0.0551005 cps`) from the pre-fix delayed
activation chain. That chain is reproduced as over-normalized by `x8.0116` for
I-128, so the comparison table is provenance only until the div-corrected
mainline Step05+ chain is rerun.

## Decision

Route B is useful as a comparison/null foreground, but it is not worth turning into a focal-spot Cosima source for the current focused-detector chain. A diffuse bulge/disk model must be treated as sky brightness over solid angle; after the 7.25 arcmin focal aperture and atmospheric transmission, the signal is far below the Route-A compact point-source case.

## Physical Input Chain

- Sky flux anchors: bulge `9.600000e-04` ph cm-2 s-1 and disk `0.00166` ph cm-2 s-1 from `Siegert et al. 2016, A&A 586 A84 / arXiv:1512.00325`.
- Sky morphology: circular Gaussian bulge stress/default cases plus an elliptical thick-disk proxy. The 8-deg bulge is the default extended-bulge comparison; 3-deg and 12-deg cases bracket compact/broad alternatives rather than claiming a unique morphology.
- Focal aperture: Be radius `1.898` cm, focal length `900` cm, angular radius `7.24982` arcmin.
- Input solid angle: Omega = `2*pi*(1-cos(atan(r/f))) = 1.397191e-05` sr, plane small-angle area `0.0458671` deg2.
- Atmosphere: Step06 day-15 reference transmission `T_atm_ref = 0.739042`. The detector-plane photon rate is `F_fov * A_eff(511) * T_atm_ref`.
- Current optics/detector authority: `A_eff(511) = 15.2993` cm2; W2 final response `8.98288` cps per ph cm-2 s-1.

## Route B Results

- Default Route B (8-deg bulge + thick disk) FoV flux: `6.262377e-07` ph cm-2 s-1, only `0.00626238` of the Route-A `1e-4` point-source reference.
- Default Route B W2 final signal: `5.625417e-06` cps; W2 20-day counting Z: `0.017223`.
- Even the compact 3-deg bulge stress case gives FoV flux `4.308134e-06` ph cm-2 s-1 and W2 20-day Z `0.118484`.
- Route A point-source W2 no-spatial Z is `2.75023`; with the valid point-source `spot_r90` cut it is `4.52748`.

The point-source spot cut should not be applied as a gain to Route B. For an aperture-filling diffuse signal, the spot cut also removes signal area; the included uniform-aperture sanity row gives a lower Z, not a stronger detection.

## Component Table

| model | total flux | FWHM l | FWHM b | FoV flux | FoV fraction | plane cps | W2 cps | W2 Z20d |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bulge_gaussian_fwhm_3deg | 9.600000e-04 | 3 | 3 | 4.308134e-06 | 0.00448764 | 4.871128e-05 | 3.869945e-05 | 0.118484 |
| bulge_gaussian_fwhm_8deg | 9.600000e-04 | 8 | 8 | 6.070029e-07 | 6.322947e-04 | 6.863270e-06 | 5.452633e-06 | 0.016694 |
| bulge_gaussian_fwhm_12deg | 9.600000e-04 | 12 | 12 | 2.698265e-07 | 2.810692e-04 | 3.050878e-06 | 2.423818e-06 | 0.00742085 |
| disk_thick_gaussian | 0.00166 | 141.289 | 24.7256 | 1.923486e-08 | 1.158726e-05 | 2.174850e-07 | 1.727844e-07 | 5.290029e-04 |

## Route A / Route B Comparison

| case | source/FoV flux | W2 signal cps | background cps | Z20d | T3 day | spatial policy |
| --- | --- | --- | --- | --- | --- | --- |
| Route_A_point_ref_W2_no_spatial | 1.000000e-04 | 8.982878e-04 | 0.184347 | 2.75023 | 23.7977 | no spot cut |
| Route_A_point_ref_W2_spot_r90 | 1.000000e-04 | 8.084679e-04 | 0.0551005 | 4.52748 | 20 | valid for compact focused source |
| Route_B_compact_bulge3deg_W2_no_spatial | 4.308134e-06 | 3.869945e-05 | 0.184347 | 0.118484 | 12822 | aperture/rate fold only |
| Route_B_default_bulge8deg_plus_disk_W2_no_spatial | 6.262377e-07 | 5.625417e-06 | 0.184347 | 0.017223 | 6.068143e+05 | aperture/rate fold only |
| Route_B_default_uniform_spot_r90_sanity | 4.767590e-08 | 4.282668e-07 | 0.0551005 | 0.00239833 | 3.129359e+07 | not a detection claim; uniform-aperture area fraction 0.0761307 |

## Checks

- Max relative delta against existing Step07 `diffuse_aperture_foreground.csv`: `0.819663`.
- Solid-angle exact area vs small-angle plane area relative delta: `3.706105e-07`.
- Generated report outputs are under `outputs/reports/route_b_diffuse_supplement_20260602` and are ignored by Git policy.

## References

- Siegert et al. 2016, A&A 586 A84 / arXiv:1512.00325: https://arxiv.org/abs/1512.00325 (Milky Way 511-keV bulge/disk line-flux anchors used by Step07.)
- Knodlseder et al. 2003, A&A 411 L457-L460 / arXiv:astro-ph/0309442: https://arxiv.org/abs/astro-ph/0309442 (Early SPI morphology context for an extended bulge-scale 511-keV source.)

## Figures

- `outputs/reports/route_b_diffuse_supplement_20260602/figures/route_a_b_w2_z20_comparison.png`
- `outputs/reports/route_b_diffuse_supplement_20260602/figures/route_b_diffuse_fov_fraction.png`
