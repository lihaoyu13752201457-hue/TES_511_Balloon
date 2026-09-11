# LLL Not Available

Checked on 2026-05-28.

The Laue Lens Library project page is reachable, but no usable local LLL package
or exported LLL curve is present in this workspace. The project page exposes a
download link, but that link was unavailable from this environment during the
check.

Current cross-checks therefore use:

- local Python Ge(111) Darwin-Hamilton reference kernel;
- imported PyTTE perfect-crystal checks;
- generated CrystalPy perfect-crystal rocking curve;
- imported Kohnle 1998 Ge(111) endpoint benchmark.
- imported XOP/CRYSTAL Ge(111) 511 keV mosaic rocking curve;
- imported opticsim full five-ring table-driven vs online-process closure.

This is enough for the current internal cross-check package, but not enough to
claim final production validation against an independent Laue-lens oracle.

Next useful evidence to add:

- LLL package version or export provenance;
- exact input ring configuration;
- exported LLL full-lens effective area and spot metrics using
  `external_lens_observables_schema_example.csv`;
- known differences from this package's Python kernel.
