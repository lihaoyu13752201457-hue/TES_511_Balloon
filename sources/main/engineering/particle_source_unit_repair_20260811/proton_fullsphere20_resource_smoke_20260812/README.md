# Corrected-keV EXPACS proton full-spectrum resource smoke

This package runs a deliberately small resource diagnostic for the two
retained geometries using the production EXPACS/PARMA proton source directly:

- full sphere, `theta=0--180 deg`, 20 equal-`mu` angular bins;
- package-owned corrected total-keV spectra, without an energy truncation or
  conditional/stratified replacement source;
- `mass_model_511` and `s3d_o8`;
- `instant` and `buildup`, 64 primaries per geometry and mode;
- one Cosima process at a time.

The transport outputs are written to
`runs/particle_source_unit_repair_20260811/proton_fullsphere20_resource_smoke_20260812`.
The runner refuses to start if that directory already exists.  It applies a
1 GiB per-file limit, a 2 GiB aggregate batch limit, a 15 minute per-job wall
limit, a 4 GiB process-group RSS limit, and an 80 GiB free-disk floor.  Failed
or stopped attempts are retained for diagnosis and are never deleted by the
controller.

This is a capacity and failure-mode diagnostic, not a mergeable production
batch, a background estimate, or geometry-promotion authority.  Its statistics
must not be pooled with another source, geometry, mode, or particle family.

## Result (2026-08-12)

All four jobs exited normally and passed the fail-closed dynamic validator.
The validator closed the frozen input hashes, deterministic source-card diff,
Cosima logs, all 256 contiguous SIM events, IA INIT seed/geometry/particle/
direction/corrected-bin energy support, isotope DAT grammar/TT, and receipt
artifact hashes.

| Geometry / mode | Primaries | CPU s | Wall s | SIM.gz bytes | Peak RSS bytes | Max initial energy |
|---|---:|---:|---:|---:|---:|---:|
| Mass / instant | 64 | 15.4780 | 47.130 | 9,109,759 | 877,895,680 | 502.662 GeV |
| S3d-O8 / instant | 64 | 11.0661 | 23.063 | 8,989,238 | 712,036,352 | 504.359 GeV |
| Mass / buildup | 64 | 2.76567 | 14.044 | 2,387,560 | 664,776,704 | 75.336 GeV |
| S3d-O8 / buildup | 64 | 10.6899 | 22.812 | 8,696,183 | 733,761,536 | 75.336 GeV |

The aggregate was 29,182,740 compressed SIM bytes, 209,285,069
uncompressed SIM bytes, 39.99967 Cosima CPU-seconds, and 107.049 serial
wall-seconds.  No resource limit fired.  The sample contains three initial
protons above 100 GeV and two above 200 GeV.  One 502.662 GeV Mass event alone
created 61,576,587 uncompressed bytes, so the heavy output tail is real even
though this slice is operationally safe.

A direct continuous-flux point projection using
`round(1,000,000 * F_p/F_gamma) = 23,398` primaries per geometry and mode is
10.669 GB of compressed SIM and 14,624 Cosima CPU-seconds across the four
cells.  This is the arithmetic stored in `resource_summary.json`, but it is
not the exact frozen batch0004 screening convention.  Batch0004 uses
`10 * round(100,000 * F_p/F_gamma) = 23,400`; after crediting the 23 validated
batch0000 primaries per cell, a matching proton production add-on needs 23,377
new primaries per cell (93,508 total).  The corresponding point projection is
10.659 GB and 14,611 CPU-seconds.  The 64-primary resource-smoke cells are
explicitly non-merge authority and cannot be credited to that target.

A projection to one million proton primaries in every cell is 455.980 GB and
624,995 CPU-seconds.  These are planning points from 64 primaries per cell,
not confidence bounds; any production continuation needs shards plus the same
hard disk/file/watchdog gates.

Authoritative machine-readable records are in `frozen_contract.json`,
`validation_report.json`, and `resource_summary.json` under the run root.

From the repository root:

```bash
python3 engineering/particle_source_unit_repair_20260811/proton_fullsphere20_resource_smoke_20260812/code/run_proton_fullsphere20_resource_smoke.py --plan
python3 engineering/particle_source_unit_repair_20260811/proton_fullsphere20_resource_smoke_20260812/code/run_proton_fullsphere20_resource_smoke.py
python3 engineering/particle_source_unit_repair_20260811/proton_fullsphere20_resource_smoke_20260812/code/validate_proton_fullsphere20_resource_smoke.py --check
```
