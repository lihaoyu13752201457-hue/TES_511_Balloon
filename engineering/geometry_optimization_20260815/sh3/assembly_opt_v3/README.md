# SH3 OptV3 boolean-welded chimney/DR assembly

## Status

OptV3 supersedes the OptV2 frustum/nozzle interface with a continuous
boolean-welded aluminium saddle joint. It is the current geometry-review
candidate; OptV1 and OptV2 remain preserved as historical, non-overwritten
revisions.

- Build: `PASS__SH3_ASSEMBLY_OPT_V3_BUILT`
- Static validation: `PASS__SH3_ASSEMBLY_OPT_V3_STATIC`
- Full Cosima/Geant4 construction and overlap validation:
  `PASS__SH3_ASSEMBLY_OPT_V3_OVERLAP_NO_TRANSPORT`
- Native Geant4 WRL export:
  `PASS__SH3_ASSEMBLY_OPT_V3_NATIVE_WRL_NO_TRANSPORT`

The full assembly passed 10,000 overlap samples per placement at 0.0001 cm
tolerance. No transport, particle event, activation, response, veto, timing,
background, or sensitivity calculation was run.

## Interface correction

OptV2 incorrectly reduced the load path to a large frustum followed by a small
diameter-2.10 cm nozzle. That geometry was continuous in CSG but was not a
credible structural representation of a large chimney attached to a DR vessel.
It is rejected as the mechanical-interface concept.

OptV3 models the requested welded branch directly in the outermost 300 K
aluminium shell. The formerly separate chimney side shell is absorbed into the
DR vacuum-jacket solid. The formerly separate DR bottom cap is absorbed into
the same solid as well. The final CSG formula is:

```text
((DR side shell UNION DR bottom cap) UNION chimney/extension outer solid)
MINUS chimney inner bore
MINUS DR main vacuum cavity
```

The last subtraction trims the extended branch at the curved inner surface of
the DR vessel. The resulting branch/DR intersection is therefore a continuous
saddle-shaped aluminium joint rather than a flat plane contact. There is no
OptV2 frustum and no small interface nozzle.

## Dimensions and retained geometry

- chimney aluminium shell: inner/outer radius 10.75/11.05 cm, 3 mm radial
  thickness;
- common raised axis: `y'=0`, `z'=-2.80 cm`;
- chimney bottom: `z'=-13.85 cm`;
- retained DR bottom: `z'=-14.10 cm`;
- vertical bottom clearance: 0.25 cm;
- MXC, Still, 4 K, and 60 K cold-finger ports: diameter 1.50 cm;
- upper-support optical cut: diameter 6.00 cm;
- W collimator: four-bar 6.00 cm outer square, 5.40 cm inner clear square,
  2.00 cm axial depth;
- retained six TES layers and three active BGO declarations;
- retained bent copper cold finger and MXC contact pad.

## Mechanical boundary

The geometry now provides a continuous material/load path suitable for a
reviewable welded-vessel concept. It does not prove that a bare 3 mm saddle is
flight-qualified. Weld bead profile, local doubler/fillet, flange strategy,
pressure loading, fatigue, vibration, buckling, thermal contraction, and FEA
remain open. A later mechanical refinement may add a saddle doubler without
changing the optical or cold-stage-port layout.

## SG3B minimal-change audit boundary

The compact comparison against the actually simulated SG3B authority is
recorded in `audit/SG3B_MINIMAL_CHANGE_AUDIT_20260818.md` and
`audit/sg3b_minimal_change_audit.json`. The strengthened audit also compares
all 168 shared declared-volume attribute blocks: 130 are identical, 37 share
the required `(-35.55, 0, +2.40) cm` core translation into the chimney, and
one NF2 top mount has the required optical cutout; no unexpected shared-volume
attribute drift remains. All geometry-only deletions are
classified and all 2,496 common copy-placement blocks are byte-identical, but
the audit status is
`REVIEW_REQUIRED__NOT_OPT_V3_PRODUCTION_AUTHORITY`.

Before corrected-keV equal-statistics production, the project must close the
56 omitted retained-volume diagnostic scorers, the missing SQUID/cable mass
proxies, the Bi/plastic design decision, and the source-surface mismatch
(`SurroundingSphere 95 0 0 8 95` here versus `60 5 0 9 60` in SG3B). Equal
raw histories on different source surfaces are not equal physical exposure.
The W frame also has zero analytic envelope margin: its inner square half-width
is exactly 2.70 cm, tangent to the declared `r=2.70 cm` optical circle. A frozen
37,194-ray full-envelope signal run and a dedicated W-intercept/aperture receipt
are therefore production gates; the opening must be enlarged if any accepted
ray touches W or positive mechanical tolerance is required.

The independent `gpt-5.6-sol / high` read-only review and the exact SG3B-cell
production proposal are retained in
`OPT_V3_EQUAL_SG3B_SIMULATION_PLAN_20260818.md`. Its status is
`PLAN_ONLY__PRODUCTION_NOT_AUTHORIZED`; it does not authorize a transport run.

## Files

- `geometry/SH3_Assembly_OptV3.geo`: complete boolean-welded assembly.
- `geometry/SH3_Assembly_OptV3.geo.setup`: assembly setup.
- `geometry/SH3_Assembly_OptV3.det`: retained TES/BGO detector declarations.
- `code/build_sh3_assembly_opt_v3.py`: deterministic builder/static gate.
- `code/run_sh3_assembly_opt_v3_overlap.py`: zero-transport overlap harness.
- `code/export_sh3_assembly_opt_v3_wrl.py`: native WRL exporter.
- `data/assembly_opt_v3_manifest.json`: CSG contract, input/output hashes, and
  scope.
- `audit/assembly_opt_v3_static_validation.json`: analytic/static receipt.
- `audit/assembly_opt_v3_overlap_validation.json`: Geant4 overlap receipt.
- `audit/assembly_opt_v3_wrl_export_validation.json`: native WRL receipt.
- `figures/sh3_assembly_opt_v3_welded_saddle_detail.svg`: section and CSG
  construction diagram.
- `figures/SH3_Chimney_DR_Assembly_OptV3.wrl`: native constructed geometry.
