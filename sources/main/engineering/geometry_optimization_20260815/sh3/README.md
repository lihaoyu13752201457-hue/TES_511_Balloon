# SH3 mergeable TES chimney component

## Status

`SH3` is a standalone, mergeable geometry component.  It is not yet merged
into SG3B and is not a transport, activation, response, timing, or sensitivity
result.

- Build: `PASS__SH3_COMPONENT_BUILT`
- Static checks: `PASS__SH3_COMPONENT_STATIC`
- Standalone Cosima/Geant4 overlap check:
  `PASS__SH3_STANDALONE_OVERLAP_NO_TRANSPORT`
- Native WRL export: `PASS__SH3_TWO_NATIVE_WRL_NO_TRANSPORT`
- Overlap audit: 10,000 sampled points per placement at 0.0001 cm tolerance;
  no overlap/error lines, no generated particles, and no event payload.

## System boundary

The chimney contains only:

- five generic nested local aluminium shell/window layers, named
  `Layer01` through `Layer05`;
- the pinned SG3B six-layer Ta TES stack: 376 pixels per layer and 2,256
  absorber pixels total;
- the pinned SG3B silicon substrates, intermediate copper open frames, four
  copper edge rods, and the rear TES copper heatsink ring;
- a minimal local hub/spoke completion of the TES bottom cold plate; and
- a short coaxial copper stub defining the future cold-finger merge interface;
- a 40 mm active-BGO side shield, 40 mm optical-front annulus, and 40 mm
  cold-port-rear annulus; and
- a 3 mm external mechanical aluminium side shell and optical-front annulus.

The chimney deliberately contains no main-DR cold plate or vessel.  In
particular, it contains no MXC, Still, 4 K, or 60 K plate/can.  The names
`Layer01`–`Layer05` do not imply thermal-stage ownership; thermal connections
must be assigned only during a reviewed full-DR merge.

The optical front remains open to radius 2.70 cm.  The rear BGO leaves the
0.75 cm-radius cold-finger port open, and there is deliberately no mechanical
aluminium rear end cap on that face.  Also excluded are plastic/positron veto,
passive Bi, W collimation, BGO optical coupling/readout hardware,
readout/SQUIDs, cabling, flight brackets, and the main-DR cold finger beyond
the component stub.

## Coordinate contract

- Local frame: `SH3_ChimneyFrame`.
- Optical axis: local `+x'`.
- Signal enters at the negative-`x'` front and propagates toward positive
  `x'`, the future main-DR merge side.
- The SG3B source geometry locates the TES centre at `z=-5.2 cm` in its
  `InstrumentFrame`.  The component applies one rigid translation
  `(0, 0, +5.2) cm` only to volumes directly parented by that frame, so the
  TES/support assembly is centred at local `z'=0`.  Pixel and support relative
  coordinates are unchanged.
- The production placement and rotation in SG3B remain intentionally
  undefined until the merge step.

## Current provisional envelope

The six TES layer centres are at
`x' = -3.0, -1.8, -0.6, +0.6, +1.8, +3.0 cm`.  All five local windows use a
2.70 cm clear radius, exceeding the 2.523 cm radius of a 20 cm² equivalent
circular optical footprint.

| Local layer | Front x' (cm) | Rear x' (cm) | Inner radius (cm) | Outer radius (cm) | Window |
|---|---:|---:|---:|---:|---|
| Layer01 | -3.95 | +4.15 | 4.00 | 4.20 | 25 µm Al |
| Layer02 | -4.40 | +4.60 | 4.45 | 4.75 | 25 µm Al |
| Layer03 | -4.95 | +5.15 | 5.00 | 5.30 | 25 µm Al |
| Layer04 | -5.50 | +5.70 | 5.55 | 5.85 | 25 µm Al |
| Layer05 | -6.05 | +6.25 | 6.10 | 6.60 | 150 µm Be |

The rear annular caps leave a 0.75 cm-radius (1.50 cm-diameter) coaxial service
opening.  The
local copper stub has radius 0.16 cm and spans `x'=3.595–6.800 cm`.  These
shell thicknesses, materials, and window stacks are first-pass mergeable
engineering parameters, not a finalized cryogenic design.

## BGO and external mechanical shell

The selected BGO thickness is 4.00 cm.  This retains the established SG3
40 mm side-shield baseline rather than extrapolating to a thicker unvalidated
design.  The project thinning audit found straight-ray cavity leakage ratios
of 1.1713 for 30 mm and 1.6687 for 20 mm relative to 40 mm; the retained O8
fallback therefore stayed side-dominated at 40 mm.  There is no current local
transport evidence that a 50 mm chimney shield gives enough incremental veto
benefit to offset its extra BGO mass and activation exposure.

| Part | x' extent (cm) | Radial extent/opening (cm) | Nominal mass proxy |
|---|---:|---:|---:|
| BGO side shield | -6.15 to +6.85 | R=6.70–10.70 | included below |
| BGO front annulus | -10.15 to -6.15 | R=2.70–10.70 | included below |
| BGO rear annulus | +6.85 to +10.85 | R=0.75–10.70 | included below |
| 3 mm Al side shell | -10.20 to +10.90 | R=10.75–11.05 | included below |
| 3 mm Al front annulus | -10.50 to -10.20 | R=2.70–11.05 | included below |

The combined density-volume proxy is 40.080 kg BGO and 1.462 kg mechanical
aluminium.  It excludes optical coupling, photosensors, cabling, brackets, and
the exact flight assembly, so it is not a closed mass budget.  A 0.10 cm
chimney-to-BGO assembly clearance and 0.05 cm BGO-to-Al clearance are modeled
as vacuum; no Kapton/reflector layer is asserted in this component revision.
All three BGO volumes use the pinned SG3B native 80 keV scorer definition, but
the final Poisson time-axis veto threshold/window remains a downstream analysis
choice and has not been run here.

Thickness evidence:

- `../../geometry_optimization_20260704/41_s3c_bgo_thinning_volume_audit_20260711/README.md`
- `../../geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/o8_fallback_decision_evidence.json`

## Files

- `geometry/SH3_Chimney_Component.geo`: reusable component; it defines no
  world and no `SH3_ChimneyFrame`.
- `geometry/SH3_Chimney_Standalone.geo`: validation wrapper that defines the
  world and one local frame.
- `geometry/SH3_Chimney_Standalone.geo.setup`: standalone setup.
- `geometry/SH3_Chimney.det`: six TES detector declarations plus three active
  BGO scintillator declarations.
- `geometry/Materials_SH3.geo`: pinned SG3B material table.
- `code/build_sh3_chimney.py`: deterministic builder and static validator.
- `code/run_sh3_overlap.py`: construct/load/overlap-only Cosima harness.
- `code/export_sh3_wrl.py`: native Geant4 `VRML2FILE` export for this
  standalone chimney and the companion pure-DR base; it exits interactive
  mode without starting particle transport.
- `data/component_manifest.json`: dimensions, source hashes, output hashes,
  scope, and exclusions.
- `audit/static_validation.json`: component counts and analytic clearances.
- `audit/overlap_validation.json`: zero-transport Geant4 construction audit.
- `figures/sh3_chimney_xr_cross_section.svg`: local x'/radius section.
- `figures/SH3_Chimney_Standalone.wrl`: native WRL of the constructed
  standalone chimney geometry.
- `audit/wrl_export_validation.json`: joint source-hash, native-WRL, and
  no-transport receipt for both standalone geometries.

## Assembly package

The authorized non-overwriting assembly is now under `assembly/`.  It flattens
the chimney directly into the pure-DR `InstrumentFrame`, aligns it with the
five 1.50 cm ports, and extends the copper cold finger to an explicit contact
pad on the underside of the MXC copper plate.  It passes fresh static and
full-geometry zero-transport overlap gates.  See `assembly/README.md`; this
does not yet authorize a source or transport campaign.

The raised-interface/optical cleanup is preserved under `assembly_opt_v2/`,
but its large-frustum plus small-nozzle structural concept is explicitly
superseded. Do not promote that interface.

The current geometry-review candidate is `assembly_opt_v3/`. It absorbs the
chimney side shell, its extension, the curved 300 K DR side shell, and the DR
bottom cap into one boolean-unioned aluminium solid, then subtracts the
chimney bore and main DR cavity to form a continuous saddle joint. It retains
the raised axis, diameter-6 cm support opening, four-bar W square frame, and
bent cold finger. Static, full-geometry zero-transport overlap, and native-WRL
gates pass. See `assembly_opt_v3/README.md`; earlier revisions and both
independent components remain preserved.

## Pure-DR companion base

The separate non-assembled DR-side package is under `dr_base/`.  It retains
the pinned SG3B DR cold plates, process hardware, thermal shells, top services,
and support cage while removing TES/detector content, all old windows, W,
BGO, outer plastic/BPE, and readout/harness proxies.  Its five former window
penetrations are now matching 1.50 cm-diameter cold-finger ports.  See
`dr_base/README.md` for the coordinate and validation contract.
