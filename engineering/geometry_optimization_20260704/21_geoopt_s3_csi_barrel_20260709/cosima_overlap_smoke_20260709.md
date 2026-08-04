# S3 CsI Full-Wrap Cosima Overlap Smoke

Date: 2026-07-09

Geometry:
`engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`

Command:

```bash
/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/geometry/overlap_check_s3.source
```

Result:

- Final run exit code: `0`.
- Final run loaded all nine S3 replacement detector volumes.
- Final run reported no `GeomVol1002` overlap warnings.

Repair history:

- Initial full-wrap draft loaded but reported overlap warnings with
  `DR_Still_PumpLine_SS_to_300K_top` and `NF2_OuterSupport_G10_Rod_01/06`.
- The builder now subtracts S2b-style NF2 support-rod reliefs from all S3
  replacement volumes and subtracts a local pump-line relief from the CsI side
  shell.

Boundary:

This is only a geometry load/overlap smoke check.  It is not a signal,
atmospheric-511, e+/n, or delayed-activation transport validation.
