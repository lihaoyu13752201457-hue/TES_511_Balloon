# Benchmarks

Imported evidence currently available in this workspace:

- `xrt_pytte/`: PyTTE 1.0 Takagi-Taupin perfect-crystal Ge(111) Laue check.
- `kohnle1998/`: Ge(111) 3-mm mosaic-crystal endpoint benchmark from Kohnle 1998.
- `crystalpy/`: CrystalPy perfect-crystal Laue rocking curve.
- `xop_crystal/`: XOP/CRYSTAL mosaic Laue rocking curve.
- `opticsim_table_lens/`: full five-ring table-driven vs online-process closure.
- `reference_outputs/`: external Laue Lens Library status.

PyTTE is not used as a direct mosaic-crystal replacement. It verifies a different
limit: perfect-crystal Laue diffraction has a higher peak diffracted branch and
near-conserved forward+diffracted flux.

`opticsim_table_lens/` is a full-lens closure check, but it remains inside
the opticsim model family and does not replace an external LLL/HEART oracle.
