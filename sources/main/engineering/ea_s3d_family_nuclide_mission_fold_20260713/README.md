# S3d family/nuclide mission-fold closure

Status: `PASS_S3D_EXISTING_DATA_FAMILY_NUCLIDE_MISSION_CLOSURE`

This package performs no new Monte Carlo transport. It rebuilds only the
81-bin mission-time analysis from retained S3d detector-response events,
retained NUBASE-corrected neutron inventory, and live-PARMA analytic fluxes.

## Closed implementation

- Prompt: all eight day-15 S3d family response coefficients are modulated
  independently by their live-PARMA trajectory flux ratios.
- Delayed: each nuclide inventory is advanced with the neutron driver and
  converted to a selected rate with its day-15 event response.
- Atmospheric 511 and focused signal retain independent line-flux and
  transmission scales; family-resolved prompt occupancy enters the live factor.
- The primary response seed selects 24 Cu-64, 5 Cu-62 in the final delayed stream.

## Headline

- 20 d source counts: `1865.08682117`
- 20 d background counts: `10082.9351771`
- central Z20: `18.5740053275`
- finite-count conservative Z20: `6.48443197766`
- central 3-sigma flux: `1.61516051444e-05` ph cm^-2 s^-1
- conservative 3-sigma flux: `4.62646537173e-05` ph cm^-2 s^-1

The direct trajectory transports validate the e+, neutron, and gamma
environmental modulation in the 480--550 keV diagnostic band. The final
510.58--511.42 keV response coefficients remain the retained day-15 S3d
selection; this package changes the time modulation, not the transport.
