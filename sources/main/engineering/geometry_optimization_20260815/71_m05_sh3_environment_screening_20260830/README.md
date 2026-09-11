# M05 SH3 environmental screening, 2026-08-30

## Purpose

This package rebuilds the PPT0821 environment comparison for the current M05
mass-model-B paper baseline. It produces a publication figure and compact table
for a deliberately conditional comparison of:

- the 38 km balloon reference;
- a 530 km near-equatorial, non-SAA LEO proxy;
- an exposed lunar-surface proxy based on the Apollo-17 REDMoon field; and
- quiet Sun--Earth L2 at the 2009 GCR-high and 2014 GCR-low modulation
  endpoints.

The package does **not** run transport, activation, delayed decay, detector
response, or a common-time replay. Its authority is
EXPLORATORY_RESPONSE_WEIGHTED_SCREENING_NOT_ENVIRONMENT_TRANSPORT_AUTHORITY.

## Current-paper anchor

The formal mass-model-B balloon values are read from
M05_SECTION4_REFERENCE_FLUX_20260830.json:

- day-15 final background: 0.010747194310499024 s^-1;
- broadband-gamma stream: 0.005355349386222926 s^-1;
- delayed-activation stream: 0.003580537811785916 s^-1;
- seven-family prompt stream: 0.0018113071124901828 s^-1;
- formal 20 d Gaussian threshold:
  2.4356806298254965e-5 ph cm^-2 s^-1; and
- effective balloon signal factor: 0.643861064039357.

The retained package-65 transfer response contains the broadband-gamma and
delayed streams. Those two streams are re-anchored at the stream-total level to
the current values. The three current prompt survivors are positrons and do not
have a compact target-environment primary-energy response kernel in the
retained screening inputs. They account for 16.854% of the formal balloon
background. No family-resolved target rate is inferred for them. Instead, the
dimensionless index makes one explicit closure convention: the fractional
change of the complete background is represented by the mapped two-stream
ratio. Equivalently, the unmapped prompt share follows that aggregate ratio
only when the formal full-background balloon threshold is converted into the
screening index. This convention is the leading unmapped transfer systematic.

For target environment \(e\), the represented two-stream ratio is

\[
{\cal R}^{(2)}_e =
\frac{B_{\gamma,e}^{\rm re}+B_{{\rm d},e}^{\rm re}}
     {B_{\gamma,0}+B_{{\rm d},0}},
\]

and the plotted screening index is

\[
\frac{F^{\rm screen}_{3\sigma,e}}{F_{3\sigma,0}}
=
\frac{\tau_0}{\tau_e}\sqrt{{\cal R}^{(2)}_e},
\qquad
\tau_0=0.643861,\quad \tau_e=1.
\]

The non-balloon value assumes the same selected effective area, a constant
20 d continuously on-source exposure, no atmospheric attenuation, and the
full-background fractional-change closure described above. The balloon point
is defined to be the formal 81-node result. The quantity is a screening index,
not a complete target-environment sensitivity.

## Central screening values

| Scenario | \({\cal R}^{(2)}_e\) | \(F^{\rm screen}_{3\sigma,e}/F_{3\sigma,0}\) | \(F^{\rm screen}_{3\sigma,e}\) |
|---|---:|---:|---:|
| 38 km balloon | 1.0000 | 1.0000 | \(2.43568\times10^{-5}\) |
| 530 km non-SAA LEO | 0.56274 | 0.48300 | \(1.17643\times10^{-5}\) |
| exposed lunar proxy | 23.02284 | 3.08938 | \(7.52475\times10^{-5}\) |
| Sun--Earth L2, 2014 GCR-low | 5.94598 | 1.57002 | \(3.82406\times10^{-5}\) |
| Sun--Earth L2, 2009 GCR-high | 11.91772 | 2.22274 | \(5.41389\times10^{-5}\) |

Fluxes are in ph cm^-2 s^-1. The balloon number is a top-of-atmosphere
threshold; non-balloon numbers are local incident-plane screening values.

## Statistical interpretation

The output table includes
\(N_{\rm eff,w}=(\sum_i w_i)^2/\sum_iw_i^2\) only as a weight-concentration
diagnostic. It is not the formal paper total-background effective sample size
and not a confidence interval. The lunar and L2 diagnostics are only about
5--6. In addition, the L2 delayed response is strongly controlled by four
selected Cu-62 survivors sharing one activation key represented by one
1.366 GeV proton production record. Ordinary independent-event error bars
would therefore overstate the precision and are intentionally omitted from the
paper figure.

## Scope exclusions

- No target-matched prompt-to-activation-to-delayed-to-response transport.
- No target-environment Poisson/common-time veto, accidental-survival, or
  mission visibility fold.
- The same detector--cryostat model is reused; no satellite bus, lander, base,
  or complete target payload is added.
- LEO excludes SAA and trapped-particle activation, time-dependent
  geomagnetic cutoff, inclination, Earth-limb history, and attitude.
- The lunar proxy excludes local terrain, site-dependent regolith,
  lander/base/RTG/reactor structures, SEP, and HZE.
- Sun--Earth L2 excludes SEP, HZE, directional soft protons, spacecraft
  structure and attitude, and orbit-specific interruptions.
- Source fields retain their stated physical angular domains. They are not
  recast as a common isotropic \(4\pi\) field.
- The corrected broadband-gamma contract is used as supplied; no independent
  mono-511 source is introduced.

## Reproduction

    MPLCONFIGDIR=/tmp/mpl-m05-environment \
    python3 code/build_environment_screening.py \
      --current-json /path/to/M05_SECTION4_REFERENCE_FLUX_20260830.json

Outputs:

- outputs/figures/fig11_environment_transfer_en.pdf
- outputs/figures/fig11_environment_transfer_zh.pdf
- corresponding 300 dpi PNG previews
- outputs/tables/m05_sh3_environment_screening.csv
- outputs/tables/m05_sh3_environment_screening_compact.csv
- outputs/summary.json
- data/input_manifest.json
- data/validation.json

All numerical inputs are small retained tables or JSON summaries. The build
does not read SIM, NPZ, or job-catalog products.
