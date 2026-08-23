# SH3 chimney + pure-DR assembly

## Status

This is the first non-overwriting assembly of the retained SH3 chimney and the
SH3 pure-DR base.  It is geometry authority only.

- Build: `PASS__SH3_ASSEMBLY_BUILT`
- Static validation: `PASS__SH3_ASSEMBLY_STATIC`
- Full-assembly Cosima/Geant4 overlap validation:
  `PASS__SH3_ASSEMBLY_OVERLAP_NO_TRANSPORT`
- Native Geant4 WRL export:
  `PASS__SH3_ASSEMBLY_NATIVE_WRL_NO_TRANSPORT`

No source, particle transport, activation, delayed source, detector response,
Poisson time-axis construction, veto, background estimate, or sensitivity
calculation was run.

## Placement contract

All assembled parts use the pure-DR `InstrumentFrame`, whose retained parent
rotation is `0 45 0`.  The chimney local `+x'` axis is aligned with the DR
cold-finger-port `+x'` axis.  The chimney origin in DR-local coordinates is
`(-31.55, 0, -5.20) cm`.

The rear end of the chimney mechanical aluminium side shell is at
`x'=-20.65 cm`, leaving 0.05 cm clearance from the negative-`x'` tangent of
the 300 K vacuum jacket at `x'=-20.60 cm`.  The chimney and the five DR ports
share `y'=0` and `z'=-5.20 cm`.

The component was flattened directly into `InstrumentFrame`; no overlapping
vacuum `SH3_ChimneyFrame` container is present in the assembled geometry.

## Cold-finger connection

The standalone chimney radius-1.6 mm copper stub is continued by a 3.2 mm
square copper proxy:

1. a coaxial run from `x'=-24.75` to `-14.86 cm` through the open rear BGO
   annulus and all five diameter-1.50 cm DR ports;
2. a short dogleg inside the MXC can from `y'=0` to `+1.10 cm`;
3. an internal run to the retained SG3B safe landing coordinate
   `(x',y')=(6.05,1.10) cm`;
4. a vertical copper stem from `z'=-5.04` to `-0.55 cm`; and
5. a radius-0.35 cm copper contact pad spanning `z'=-0.55` to `-0.20 cm`.

The pad upper face is coplanar with the retained MXC copper plate underside at
`z'=-0.20 cm`, so the geometry contains an explicit copper-to-copper contact.
The pad edge is 1.173 cm clear of the nearest retained MXC vacuum-hole edge.
The cold-finger square corner radius is 0.226 cm, leaving 0.524 cm clearance
inside each 0.75 cm-radius port.

The added cold-finger-route density-volume proxy is 3.812 cm³ or 34.15 g of
copper.  This is not thermal sizing: conductance, parasitic heat load,
vibration, supports, intercepts, and manufacturability remain open engineering
items.

## Validation boundary

The full assembly was constructed with the actual MEGAlib/Geant4 geometry and
checked with 10,000 overlap samples per placement at 0.0001 cm tolerance.  The
receipt contains no overlap/error lines, generated particles, transport
markers, or event payload.

## Files

- `geometry/SH3_Assembly.geo`: complete flattened assembly.
- `geometry/SH3_Assembly.geo.setup`: assembly setup.
- `geometry/SH3_Assembly.det`: six TES and three BGO detector declarations.
- `geometry/Materials_SH3_Assembly.geo`: pinned SG3B material authority.
- `code/build_sh3_assembly.py`: deterministic assembly builder/static gate.
- `code/run_sh3_assembly_overlap.py`: zero-transport full-overlap harness.
- `code/export_sh3_assembly_wrl.py`: native no-transport WRL exporter.
- `data/assembly_manifest.json`: input pins, transforms, cold-finger route,
  mass proxy, output hashes, and scope.
- `audit/assembly_static_validation.json`: analytic/static receipt.
- `audit/assembly_overlap_validation.json`: full Geant4 overlap receipt.
- `audit/assembly_wrl_export_validation.json`: native WRL receipt.
- `figures/sh3_assembly_local_xz_section.svg`: dimensioned local section.
- `figures/SH3_Chimney_DR_Assembly.wrl`: constructed native geometry view.

## Next safe step

Before any transport, the user should review the section/WRL and approve the
orientation, 0.05 cm mechanical docking gap, cold-finger dogleg, and MXC
landing point.  A later physics run must be a new non-overwriting campaign and
must not inherit SG3B prompt/delayed normalization without a new source-surface
and detector-response closure.
