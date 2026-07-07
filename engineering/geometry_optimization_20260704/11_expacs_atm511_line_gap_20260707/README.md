# EXPACS Gamma 511-keV Line Gap Evidence

This evidence package uses one local EXPACS/PARMA gamma spectrum:
`expacs_fullsphere_20bin_sources/cosima_spectra/gamma_bin00_theta18.19_pdf.dat`.

## What the table shows

For gamma angular bin00 (`theta=0.000--25.842 deg`), the EXPACS gamma PDF table has
the following local points around 511 keV:

| Energy keV | PDF keV^-1 | Status |
|---:|---:|---|
| 357.17 | 2.9376372290e-04 | EXPACS table point |
| 449.65 | 1.5142116335e-04 | EXPACS table point |
| 511.00 | 1.5994144486e-04 | linear interpolation only, not a table point |
| 566.08 | 1.6759094943e-04 | EXPACS table point |
| 712.64 | 2.9600557973e-05 | EXPACS table point |

The 511-keV atmospheric annihilation line is therefore not represented as a
line feature in this spectrum. It is only a continuum interpolation between
449.65 and 566.08 keV.

For bin00, the original EXPACS gamma source-card flux is `4.323745326736e-02`
ph cm^-2 s^-1. The interpolated continuum differential flux at 511 keV is
`6.915460747574e-06` ph cm^-2 s^-1 keV^-1, and the continuum integral over
W2 (`510.58--511.42 keV`) is `5.808987027962e-06` ph cm^-2 s^-1.

## How to supplement

Do not insert the atmospheric 511-keV line into the continuous PDF as another
linear-interpolation point unless an artificial finite line width is explicitly
being modeled. For transport, add a separate mono-energetic source per angular
bin:

```text
BalloonPrompt.Source Atm511_gamma_bin00_down

Atm511_gamma_bin00_down.ParticleType 1
Atm511_gamma_bin00_down.Beam FarFieldAreaSource 0.000 25.842 0.000 360.000
Atm511_gamma_bin00_down.Spectrum Mono 511
Atm511_gamma_bin00_down.Flux L00_PH_CM2_S
```

For all 20 bins, choose line fluxes `L_i` from an atmospheric 511-keV model such
that `sum_i L_i = F511_TOTAL`. The file
`expacs_gamma_511_interpolated_angular_weights.csv` provides one diagnostic
choice where `L_i` is distributed by the EXPACS gamma continuum angular shape at
511 keV. This is a repair heuristic, not a literature-derived angular model.

## Outputs

- `expacs_gamma_bin00_511_gap.png`
- `expacs_gamma_bin00_511_gap.svg`
- `gamma_bin00_theta18p19_excerpt_around_511.csv`
- `expacs_gamma_511_interpolated_angular_weights.csv`
- `mono511_supplement_bin00_source_snippet.source`
- `mono511_fullsphere_expacs_weighted_unit_sources.source`
