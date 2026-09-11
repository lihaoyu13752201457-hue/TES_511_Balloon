# SG3B — Bi upper half-cylinder plus Al harness-proxy ablation

SG3B is a strict SG3A child with two requested physical edits.  The flat
`164.08 g` passive Bi plate is replaced by a `410.30 g`, 4.796 mm radial-thick
upper half-cylinder coaxial with the existing x'-axis 2 mm Al near-field
cylinder.  It sits 0.05 mm inside the Al cylinder and is split over
`x'=[3.24,3.60] cm` to clear the retained L0 Cu heat-sink ring.  The lower
semicircle is absent.  Bi remains passive and is not a veto volume.

All five homogeneous NbTi cable proxy sectors keep their shapes and positions
but use Aluminium.  Their proxy mass changes from `567.70 g` to `235.73 g`.
This is an activation/material ablation, not proof that an aluminium harness is
thermally or electrically flight-realistic.

The deterministic reverse audit proves that no other SG3A geometry/response
bytes changed.  The static 37,194-ray check, retained MXC-origin sightline
screen, geometry-only Cosima overlap audit, and pre-transport F3 estimate live
under `audit/` and `data/`.  No transport is launched.  Final authority still
requires SG3B-own corrected prompt, inventory, actual-position delayed,
37,194-ray signal, common response/veto/Step05, and 81-node/20-day closure.

Static results:

- 37,194 focused rays intersect the Bi half-cylinder zero times; the minimum
  radial clearance to its inner surface is 1.841 cm;
- the retained seven-MXC-origin to 2,256-TES-pixel straight-sightline screen
  rises from 21.84% for the old flat plate to 87.33% for the half-cylinder;
- the 10,000-sample-per-placement Cosima/Geant4 construct/overlap audit passes
  without transport;
- conditional on unchanged signal and no new accepted prompt, the central F3
  screen is `5.22e-5 ph cm^-2 s^-1`, with an engineering range of about
  `5.09e-5` to `5.51e-5`.

The estimate does not include the prompt cost of increasing near-field passive
Bi from 164.08 g to 410.30 g or the new Al activation inventory.  It therefore
does not establish a final sensitivity or promote SG3B.
