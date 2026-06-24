# Native Activator Merge Audit

status: `PASS`

Verdict: `DO_NOT_USE_SINGLE_ALL_TAG_ACTIVATOR`.

Installed-code evidence:
- `MCParameterFile.cc:636-642` lets an Activator accept multiple `IsotopeProductionFile` entries.
- `MCActivator.cc:175-188` adds each file's `TT` into `TotalTime`, merges counts, then scales the merged store by `1/TotalTime`.
- This is exposure-homogeneous within a production tag, but it is not a valid all-tag merge because alpha, proton, neutron, muon, and positron source normalizations are separate physical source families.

Safe native raw oracle plan:
- Run native Activator per `production_tag`.
- Merge only files that share the same tag exposure semantics.
- Sum per-tag activation outputs and compare parent/daughter feeding against source-v2 direct inventory.

This WP05 run uses the tag-aware path for native parent-feeding inventory comparison.
