# v3p5 Fullstat Spatial Line Proxy

Status: `PASS_V3P5_FULLSTAT_SPATIAL_LINE_PROXY`.

This sidecar applies detector-coupled focused-spot spatial cuts to the v3p5 fullstat W2 line response and folds the day-15 rates through the Step06 time axis.

## Headline

- `spot_r90` radius: `1.05164` cm; signal PSF fraction `0.900004`.
- `spot_r90` background: `0.023251` cps (`prompt=0.0189662`, `delayed=0.00428481`).
- `spot_r90` time-dependent Z20d: `8.17566`; T3 `2.23643` day.
- `spot_r90` 20-day 3-sigma flux: `3.669426e-05` ph cm^-2 s^-1.
- Gain vs current v3p5 W2 counting authority: `1.43377`.

## Cut Table

| cut | radius cm | signal frac | background cps | Z20d const | Z20d time | T3 time day | F3sigma20d time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| spot_r50 | 0.720711 | 0.500019 | 0.0103221 | 6.8727 | 6.81496 | 3.59227 | 4.402083e-05 |
| spot_r68 | 0.849486 | 0.680004 | 0.0176296 | 7.15182 | 7.0922 | 3.1857 | 4.230001e-05 |
| spot_r90 | 1.05164 | 0.900004 | 0.023251 | 8.24231 | 8.17566 | 2.23643 | 3.669426e-05 |
| spot_r95 | 1.13764 | 0.950021 | 0.0288407 | 7.81188 | 7.7483 | 2.52617 | 3.871816e-05 |
| spot_r99 | 1.30967 | 0.990034 | 0.0410909 | 6.82029 | 6.76466 | 3.66816 | 4.434814e-05 |
| spot_rmax | 1.71427 | 1 | 0.0720086 | 5.20396 | 5.16218 | 6.45949 | 5.811496e-05 |
| full_aperture_1p8 | 1.8 | 1 | 0.0730017 | 5.16844 | 5.12702 | 6.53381 | 5.851348e-05 |

## Boundaries

- This is a sidecar, not a replacement for the current hard-window W2 authority.
- No spatial/profile likelihood gain is applied.
- Exact-position delayed-source sampling remains pending.

## Rebuild

```bash
python3 stepwise_maintenance/step08_significance/code/build_v3p5_spatial_line_proxy.py
```
