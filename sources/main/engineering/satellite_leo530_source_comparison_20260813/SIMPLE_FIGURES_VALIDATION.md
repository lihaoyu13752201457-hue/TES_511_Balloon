# Simple-figure validation

Status: `PASS`

This gate validates the compact four-figure product against the already validated source-comparison tables.

## Checks

- 5 source-table hashes match both the base PASS validation and the simple manifest.
- 5 selected gamma bands close exactly to the base environment-contrast table.
- 24 non-gamma matrix cells were checked; 5 remain explicit NA.
- 8 authority/readiness rows have the expected neutral status inventory.
- 2694 prompt incident-component data rows were checked; no activation/delayed row or cross-family Total is present.
- Exactly four PNG/PDF figure pairs are present, nonblank, and above the minimum review resolution.
- Native balloon gamma knots exist around the 511-keV region; the mono line remains an integrated-flux annotation.

## Authority boundary

PASS authorizes the compact source-input visualization only. It does not establish detector background, activation, delayed response, sensitivity, resource cost, or a geometry promotion.

## Retained warnings

- Figure 0 contains prompt incident particle spectra only; activation/delayed components and a cross-family Total are deliberately omitted.
- Figure 1 compares angular-domain source inputs; 450–600 keV is a broad proxy and not a narrow-line flux ratio.
- Figure 2 is an environment contrast only. The neutron row uses a diagnostic 10-GV fallback, partial/mixed validity is marked, and missing muons remain NA.
- Figure 3 deliberately leaves detector background, activation, sensitivity, and CPU/disk cost unestablished until matched transport or pilots exist.
