# SF3: SE3 plus a passive near-field windowed W enclosure

Status: `GEOMETRY GENERATED/VALIDATED — PHYSICS UNKNOWN`

SF3 is a strict, non-overwriting child of the frozen SE3 geometry.  It keeps
SE3 byte-for-byte after removal of one explicitly delimited additive block and
adds exactly three passive tungsten volumes around the TES near field:

- 2.9 mm side sleeve;
- 2.9 mm front plate with a 3.8 cm square focused-photon window;
- 2.9 mm rear annulus for the cold-finger service path.

The three parts have 50 micrometre clearance to the closest inherited solids.
Their total W volume is `98.1713854234 cm3` and their mass is
`1.8947077387 kg`.  A nominal 3.0 mm concentric shell is intentionally not
used because it overlaps the inherited Cu 50 mK bottom cap by about 0.5 mm.

Geometry entry:

`/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/geometry_optimization_20260815/48_geoopt_sf3_windowed_w_nearfield_20260816/geometry/DEMO2_DR_v3p5_SF3.geo.setup`

The coordinate convention is inherited, not redefined:

- `InstrumentFrame.Rotation 0 45 0` remains exact;
- world `+Z` is sky/up;
- the sky-facing optical axis is `-xprime`, 45 degrees upward;
- focused photons arrive along `+xprime`;
- the new PCON volumes use only `Rotation 0 90 0` inside the already rotated
  `InstrumentFrame` to align their cylinder axis with `xprime`.

W is passive.  The `.det` file is byte-identical to SE3, and the three
`SF3_W_*` volumes must never be added to the six existing BGO/plastic active
veto roles.  `StoreIsotopes true` still records activation in passive volumes,
so SF3 must run its own buildup, inventory, actual-position delayed source,
and delayed transport.

Validation authorities:

- `audit/sf3_geometry_validation.json`: pinned parent and exact additive diff;
- `audit/sf3_mesh_clearance_prefilter.json`: inherited-mesh and 37,194-ray
  analytic prefilter;
- `audit/sf3_overlap_validation.json`: Cosima/Geant4 construction with 10,000
  overlap samples per placement and no beamOn;
- `audit/sf3_native_navigation_audit.json`: native SE3/SF3 full-path material
  comparison, zero added-W chord for all focused rays, and three positive W
  thickness witnesses.

The only simulation entry is
`SF3_ONE_THIRD_TRANSPORT_HANDOFF_20260816.md`.  Geometry validation is not a
background or sensitivity result.
