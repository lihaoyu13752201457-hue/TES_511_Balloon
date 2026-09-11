# Simple four-figure contract

## Decision question

Can the 530-km near-equatorial LEO proxy be compared with the corrected
38-km balloon environment in two to four figures without hiding the source
model limitations?

The compact answer uses four figures:

1. `simple_00_incident_component_spectra`: a two-panel, log-log source-level
   analogue of the supplied component-spectrum image in
   `cube_satelite/基于立方星的康普顿望远镜在轨性能模拟.docx`.  It plots prompt
   incident `dF/dE` components for LEO and balloon, with every activation or
   delayed source omitted.  It does not plot reconstructed `Counts/keV/s`.
2. `simple_01_gamma_source`: the two nominal gamma continua and five
   band-integrated gamma fluxes.  This is the primary 511-keV-context figure.
3. `simple_02_family_band_ratio`: a discrete **non-gamma** family-by-band
   matrix of `LEO / balloon` source-flux ratios.  Invalid or unavailable cells
   are `NA`, never zero.  Gamma is omitted here to avoid repeating figure 1.
4. `simple_03_readout`: a neutral authority/readiness matrix showing which
   questions the current evidence can answer.  It does not assign a numerical
   background or compute-cost result where matched transport is absent.

## Visual and numerical rules

- Blue denotes the corrected balloon source; orange denotes the LEO proxy.
- The continuous-spectrum ordinate is angular-domain integrated
  `E dF/dE` in `cm^-2 s^-1`; it is not detector count rate.
- The component-spectrum figure is the explicit exception: its ordinate is
  source-support-average incident intensity `dJ/dE` in
  `cm^-2 s^-1 sr^-1 MeV^-1`, matching the reference input-spectrum layout
  while keeping the angular and energy-density units explicit.  Its horizontal
  axis is total kinetic energy per particle in MeV.
- Different particle families are not summed into a source-level `Total`;
  such a total becomes physically meaningful only after they share a detector
  count-rate response quantity.
- The gamma delta line at 511 keV is stated only as an integrated flux.  It is
  never assigned an arbitrary continuum height.
- The 450--600 keV band is an annihilation-region proxy.  Its LEO integral
  includes the atmospheric mono-511 component; it is not a narrow-line ratio.
- Ratio-matrix color is categorical rather than a continuous rainbow:
  `<=0.1`, `0.1--0.5`, `0.5--2`, `2--10`, and `>10`.
- `NA` means outside cited support or unavailable.  It is not plotted at a
  numerical floor and does not enter a ratio.
- `*` marks the diagnostic 10-GV neutron fallback; `~` marks partial or mixed
  cited validity; dagger marks the gamma annihilation-region proxy.
- The readout uses neutral states such as `input established`, `B-level
  contrast`, `not established`, and `pilot required`.  Activation and compute
  cost must not be presented as measured quantities before matched pilots.

## Authority boundary

All four figures compare source inputs only.  They do not establish detector
background, activation, delayed response, mission sensitivity, or a
Mass_model_511/S3d-O8 geometry promotion.
