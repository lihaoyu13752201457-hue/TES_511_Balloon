# Prompt 511 Spatial ROI Smoke

Status: `PASS_PROMPT511_SPATIAL_ROI_DIAGNOSTIC_WITHDRAWN_AS_STRATEGY`.

This report records a detector-coordinate spatial ROI diagnostic around the focused 511 keV spot. It is withdrawn as a prompt-suppression strategy: the old/current prompt-entry audit shows the root issue is the current side-port/side-wall geometry and source-surface normalization, not the absence of an ROI.

## Headline

- Current hard-window authority: `fullstat_v2_exactpos_m50000_s260613`; W2 prompt/delayed/signal = `0.0590827` / `0.00389764` / `0.00118117` cps.
- Best counting ROI in this scan: `spot_r90` at `1.05164` cm.
- The scan rows are spatial-table ROI rows; `full_aperture_1p8` is not identical to the hard-window authority because its signal support is `0.89938` of the current hard-window W2 signal.
- `spot_r90` prompt falls to `0.0190174` cps, a `3.10677x` prompt reduction versus the current hard window.
- `spot_r90` keeps `0.900004` of the spatial-table focused spot, or `0.809445` of the current hard-window W2 signal.
- With current exactpos delayed normalization rescaled by spatial fraction, `spot_r90` gives B=`0.0202037` cps, Z20d=`8.76095`, F3(20d)=`3.424286e-05`.
- Fixed-template annular likelihood with the same rescaled delayed normalization gives Z20d=`9.04372`, F3(20d)=`3.317220e-05`; this is an analysis sidecar, not a prompt-rate cut.

## Cut Scan

| cut | radius cm | prompt cps | prompt keep | signal keep vs hard W2 | B cps | Z20d | F3(20d) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| spot_r50 | 0.720711 | 0.00882979 | 0.149448 | 0.449707 | 0.00924954 | 7.19282 | 4.170826e-05 |
| spot_r68 | 0.849486 | 0.0149427 | 0.252912 | 0.611582 | 0.0156977 | 7.5089 | 3.995261e-05 |
| spot_r90 | 1.05164 | 0.0190174 | 0.321878 | 0.809445 | 0.0202037 | 8.76095 | 3.424286e-05 |
| spot_r95 | 1.13764 | 0.0237719 | 0.40235 | 0.854429 | 0.025193 | 8.28146 | 3.622548e-05 |
| spot_r99 | 1.30967 | 0.0339595 | 0.574779 | 0.890417 | 0.0359592 | 7.22364 | 4.153033e-05 |
| spot_rmax | 1.71427 | 0.0584035 | 0.988504 | 0.89938 | 0.0622137 | 5.54739 | 5.407950e-05 |
| full_aperture_1p8 | 1.8 | 0.0590827 | 1 | 0.89938 | 0.0629804 | 5.51355 | 5.441138e-05 |

## Interpretation

- `spot_r90` remains useful as a diagnostic showing that surviving prompt is more spatially diffuse than the focused signal.
- Tighter cuts such as `spot_r50` lower prompt further, but they give worse total significance because signal loss outruns the extra prompt rejection.
- The outer annuli are prompt-rich and signal-poor; annular likelihood can use this information, but that is an analysis diagnostic rather than a hardware prompt fix.
- Do not use this report to recommend ROI before hardware shielding. The prompt-fix direction is local side-port/side-wall geometry closure, with MC/CAD validation and delayed-activation cost accounting.

## Boundary

- This smoke does not modify the current hard-window authority or manuscript headline.
- This smoke is withdrawn as a prompt-suppression strategy; it is retained only for diagnostic traceability.
- `full_aperture_1p8` in the cut table is the spatial-table support aperture, not a synonym for the hard-window authority.
- Delayed spatial fractions are inherited from the existing spatial cut table and rescaled to the current exactpos delayed total. A fully selection-consistent exactpos spatial table would be the next stronger check.
- The current authority hard-window fold is reproduced by this script within the validation tolerance recorded in the summary JSON.

## Outputs

- summary JSON: `outputs/reports/prompt511_spatial_roi_smoke_20260618/prompt511_spatial_roi_smoke_summary.json`
- cut CSV: `outputs/reports/prompt511_spatial_roi_smoke_20260618/prompt511_spatial_roi_smoke_cuts.csv`
- annuli CSV: `outputs/reports/prompt511_spatial_roi_smoke_20260618/prompt511_spatial_roi_smoke_annuli.csv`
