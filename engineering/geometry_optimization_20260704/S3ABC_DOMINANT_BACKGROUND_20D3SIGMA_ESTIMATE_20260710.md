# S3a/S3b/S3c dominant-background 20d 3sigma estimate - 2026-07-10

## Claim level

This is a background-only estimate, not a regenerated Step05-08 full-chain
sensitivity product.

Assumptions:

- W2 window: `510.58-511.42 keV`.
- Formula matches the retained S3 Step05 matched-ATM511 calculation:
  `Z = S * T / sqrt(B * T)` and `F3 = F_ref * 3 / Z`.
- Exposure: `20 d`; reference flux: `1.0e-4 ph cm^-2 s^-1`.
- Science signal rate is held fixed at the S3 value because no S3a/S3b/S3c
  detector-coupled science response was rerun.
- S3 non-dominant residual background is held fixed. Only the measured
  `eplus + n + atm511` dominant subset is replaced by each variant.

## S3 anchor

Retained S3 W2 matched-4pi-ATM511 anchor:

- Full S3 background: `0.0222344226 cps`.
- S3 20d 3sigma flux: `2.85290835e-05 ph cm^-2 s^-1`.
- S3 `Z20d` at `1.0e-4 ph cm^-2 s^-1`: `10.5155849`.

Dominant-subset decomposition:

- S3 `eplus+n+atm511`: `0.0210670496 cps`.
- S3 residual non-dominant background: `0.00116737299 cps`.
- Dominant-subset fraction of S3 full background: `0.947497`.

## Relative W2 final rates versus S3

All rates are final `side_compton_fov_pass` rates.

| Component | S3 cps | S3a cps | S3a/S3 | S3b cps | S3b/S3 | S3c cps | S3c/S3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| eplus | 0.00950537 | 0.000678454 | 0.0713758 | 0.00678757 | 0.714077 | 0.00135997 | 0.143074 |
| n | 0.000678527 | 0.00271376 | 3.99949 | 0.00203630 | 3.00106 | 0.00135670 | 1.99948 |
| atm511 | 0.0108831 | 0.00174823 | 0.160636 | 0.00931889 | 0.856268 | 0.00116688 | 0.107219 |
| eplus+n+atm511 | 0.0210670 | 0.00514045 | 0.244004 | 0.0181428 | 0.861191 | 0.00388356 | 0.184343 |

## Estimated 20d 3sigma performance

Estimated background:
`B_variant_est = S3_residual_non_dominant + variant(eplus+n+atm511)`.

| Case | Estimated W2 B cps | B/S3 full | 20d 3sigma flux ph cm^-2 s^-1 | Flux/S3 | Z20d at 1e-4 | Z/S3 |
|---|---:|---:|---:|---:|---:|---:|
| S3 retained anchor | 0.0222344 | 1.00000 | 2.85291e-05 | 1.00000 | 10.5156 | 1.00000 |
| S3a estimate | 0.00630782 | 0.283696 | 1.51955e-05 | 0.532631 | 19.7427 | 1.87747 |
| S3b estimate | 0.0193101 | 0.868479 | 2.65869e-05 | 0.931922 | 11.2838 | 1.07305 |
| S3c estimate | 0.00505093 | 0.227167 | 1.35976e-05 | 0.476621 | 22.0628 | 2.09810 |

## Interpretation

Under this limited dominant-background estimate, S3c is the best candidate:
its estimated W2 20d 3sigma flux is about `0.477 x S3`, or a `2.10 x`
Z20d gain at the reference flux.

S3a is also strong at `0.533 x S3` flux and `1.88 x` Z20d, mainly because BGO
strongly suppresses `eplus` and `atm511`.

S3b is close to S3 at `0.932 x S3` flux and `1.07 x` Z20d. Its W/Al shell-only
change does not materially improve the dominant subset at the current
statistics.

The neutron selected counts are very low in all designs, so the neutron ratios
should not be treated as precision measurements. The robust driver in this
estimate is the much larger `atm511` reduction, especially for S3c and S3a.
