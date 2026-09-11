# SH3 pure dilution-refrigerator base

## Status

This package is the non-overwriting DR-side companion to the standalone SH3
TES chimney.  It is derived from the same pinned SG3B geometry but does not
assemble or place the chimney.

- Build: `PASS__SH3_PURE_DR_BASE_BUILT`
- Static validation: `PASS__SH3_PURE_DR_BASE_STATIC`
- Cosima/Geant4 construction and overlap validation:
  `PASS__SH3_PURE_DR_BASE_OVERLAP_NO_TRANSPORT`
- The audit used 10,000 overlap samples per placement at 0.0001 cm tolerance.
  It recorded no overlap/error lines, generated particles, transport markers,
  or event records.

## Retained DR content

- MXC, 100 mK, Still, 4 K, and 60 K cold plates and their pinned 240 vacuum
  hole placements;
- DR process hardware, heat exchangers, capillaries, structural rods, G10
  supports, 300 K service lid, top service pipes, and external support cage;
- five aluminium thermal/vacuum shells and their bottom caps; and
- the original `InstrumentFrame.Rotation 0 45 0` whole-refrigerator tilt.

## Removed content

- all TES pixels, TES containers, substrates, local copper frames, old TES
  cold fingers/clamps, and all detector declarations;
- near-TES Al/Bi shielding, SQUID/readout, and SG3B aluminium cable-bundle
  proxies;
- every window/filter foil and the old 3.796 cm square side-window cuts;
- the passive W bottom plate and W multihole collimator; and
- BGO, its Kapton/mechanical enclosure, external plastic scintillator, and
  external borated-polyethylene package.

## Cold-finger interface

The five old square window cuts have been replaced with coaxial circular holes
of diameter 1.50 cm (radius 0.75 cm), centred at the former side-window level
`z'=-5.2 cm` and directed along the former local side-window axis `x'`.

The matching rear holes in the standalone SH3 chimney are also radius
0.75 cm.  The current copper cold-finger proxy remains radius 0.16 cm, leaving
0.59 cm radial assembly/insulation clearance.

No assertion is made yet that a world-vertical chimney is aligned with this
local port after the DR's 45° rotation.  The user-requested world-vertical
placement is deliberately deferred to the assembly geometry, where the two
frame transforms and the full cold-finger route can be checked together.

## Main files

- `geometry/SH3_PureDR_Base.geo`: pure DR geometry.
- `geometry/SH3_PureDR_Base.geo.setup`: standalone geometry setup.
- `code/build_sh3_dr_base.py`: deterministic extraction/rebuild and static
  validation.
- `code/run_sh3_dr_base_overlap.py`: zero-transport Cosima overlap harness.
- `data/dr_base_manifest.json`: pinned source hashes, retained-block hashes,
  exclusions, interface, and output hashes.
- `audit/dr_base_static_validation.json`: static gate.
- `audit/dr_base_overlap_validation.json`: Cosima/Geant4 gate.
- `figures/sh3_pure_dr_base_xz_section.svg`: dimensioned equal-scale local
  x'/z' section, port-stack and transverse-face details, retained shell/plate
  dimensions, coordinate audit, and a clearly marked reference-only ghost of
  the removed SG3B detector bay.
- `figures/SH3_PureDR_Base.wrl`: native Geant4 `VRML2FILE` view of the
  constructed pure-DR base, including the subtraction-defined 1.50 cm ports.

In the axial x'/z' panel, each circular x'-axis cold-finger penetration appears
as a 1.50 cm-high rectangular wall gap.  Its circular shape is shown separately
in the transverse y'/z' inset; this avoids the misleading circle-on-side-wall
convention used by the earlier schematic.

## Assembly status

The explicitly authorized non-overwriting assembly now exists at
`../assembly/`.  It aligns the chimney and port axes inside the retained
45-degree `InstrumentFrame`, continues the cold finger through all five ports,
and contacts the MXC copper plate.  Fresh static and full-assembly
zero-transport overlap checks pass.  The pure-DR base in this directory remains
unchanged and independently reusable.
