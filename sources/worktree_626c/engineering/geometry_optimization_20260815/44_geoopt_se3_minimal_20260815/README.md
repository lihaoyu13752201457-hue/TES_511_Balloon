# SE3 minimal geometry (P20-port)

Status: `GEOMETRY GENERATED/VALIDATED — PHYSICS UNKNOWN`

This package is a hash-pinned, complete copy of the finished S3d-O8 authority
followed by an exact-once SE3 whitelist patch.  It is not rebuilt from S3c and
does not overwrite S3d-O8, fix5, or any other authority product.

- Geometry entry: `/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/geometry/DEMO2_DR_v3p5_SE3.geo.setup`
- Hole ledger: `/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/data/se3_hole_pattern.csv`
- Equivalent-area design summary: `/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/data/se3_equivalent_48_summary.csv`
- Exact touched-component mass ledger: `/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/data/se3_mass_ledger.csv`
- Static whitelist audit: `/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/geometry_optimization_20260815/44_geoopt_se3_minimal_20260815/audit/se3_static_diff.json`
- Accepted equivalent-area holes by plate: `{"4K": 48, "60K": 48, "CP_100mK": 48, "MXC_50mK": 48, "Still_0p7K": 48}`

The reviewed high-copy Ø4 mm pattern is represented by exactly 48 larger
through-holes on each plate.  Each plate-specific diameter preserves its
reviewed excavated area and mass; centres are selected deterministically on
the locked 6 mm grid with at least 2 mm web, edge, and projected-interface
clearance.  This reduces physical hole placements from 8,852 to 240.

The 20 mm BPE is retained with a focused port only in its side shell.  The
10 mm plastic scintillator remains continuous and uncut.  The
`InstrumentFrame.Rotation 0 45 0` convention is frozen: world +Z is sky/up,
the sky-facing optical axis is -x-prime, and incoming focused photons travel
along +x-prime.

No prompt, delayed, activation, signal, or full-eight-family transport is
launched by this builder.  Geometry validation and native WRL products are
separate, mandatory gates.
