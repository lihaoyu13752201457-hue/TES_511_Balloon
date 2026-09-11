# Chart contract

The figures answer three distinct questions:

1. `gamma_source_comparison`: absolute angular-domain integrated gamma flux, plus a native-knot view around 511 keV.
2. `particle_family_source_comparison`: absolute family spectra with LEO primary and secondary components kept separate.
3. `common_support_shape_comparison`: unit-normalized spectral shape over common cited model-valid support.

Common rules:

- x-axis is total kinetic energy in keV.
- Absolute y-axis is `E dF/dE` in `cm^-2 s^-1`.
- Shape y-axis is `q(E) = E f(E) / ∫f dE`, a density per logarithmic energy interval.
- Balloon is blue; satellite components use orange/green/purple plus distinct line styles.
- Log axes exclude nonpositive values rather than replacing them by a plotting floor.
- Balloon native gamma knots are shown in the 300–800 keV view.
- The satellite delta line is annotated by integrated flux and never drawn as a continuum density.
- SAA, Galactic diffuse, unavailable muons, and invalid bands are not silently plotted as zero.
- Every figure subtitle states the angular/normalization scope and that orbit weighting or detector response is absent.

