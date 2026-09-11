# Corrected-neutron BPE boundary diagnostic (2026-08-13)

This package measures the neutron current entering and leaving the three 20 mm,
5 wt% natural-boron polyethylene bodies in S3d-O8, using the corrected-keV
neutron source. It then folds the boundary spectra with the Geant4/G4NDL4.5
natural-copper channels that produce Cu-61, Cu-62, and Cu-64.

The accepted run is `production_attempt04`: 100,000 independent histories in
eight 12,500-event shards, scheduled with at most six workers. Seeds
`88813201`--`88813208` were passed through Cosima's command-line `-s` option.
Boundary quantities were stored with nine-digit scientific precision.

`production_attempt03` is excluded: the source-card `Seed` field is ignored by
this Cosima version, so simultaneous processes inherited duplicate time-based
seeds. It is retained only as failed-attempt provenance.

Main results and interpretation are in [REPORT.md](REPORT.md). Machine-readable
outputs are under `outputs/`; the canonical computation is
`code/analyze_boundary.py`.

This is a non-mergeable diagnostic. It tests direct BPE transport and direct Cu
activation channels; it is not a no-BPE detector-background prediction.

