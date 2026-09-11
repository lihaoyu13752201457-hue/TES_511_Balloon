# Input snapshot scope

`cosi_dc4_pinned/` is a hash-pinned, comparison-minimal snapshot from
`cositools/cosi-sim` commit
`eec0dbf1aaabc79fea2706946434e30f7060a59a`.

Included:

- normal-background `.source` cards;
- ten two-column continuum spectrum files;
- SAA source/spectrum/beam metadata for explicit exclusion;
- Galactic-diffuse source-card metadata for explicit exclusion;
- the upstream 1000-way parallelization script used to interpret card Flux;
- the upstream Source Library index.

Intentionally omitted:

- 531,998-point orbital light curves, because this comparison has no orbit-time weighting;
- the large Galactic diffuse direction-energy table, because it is not collapsed into a local family spectrum;
- the SAA time series, because SAA is an activation profile rather than nominal prompt exposure.

Consequently this snapshot is sufficient to reproduce the static spectra and
QA decisions in this package, but it is deliberately not a complete
transport-ready copy of the COSI source library.

