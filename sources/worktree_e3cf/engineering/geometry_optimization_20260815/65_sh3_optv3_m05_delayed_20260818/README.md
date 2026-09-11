# SH3 OptV3 M05 delayed transport

Status: execution adapter for the user-authorized OptV3 delayed campaign.

The pipeline waits for complete drainage of the 2.5-hour adaptive campaign,
then consumes every completed-round corrected-keV BUILDUP receipt.  It reuses
the accepted SG3B M05 exact-position activation adapter, the retained M05
NUBASE/state primitives, the accepted 33-shard layout, and the canonical
multi-process runner.

Scientific contract:

- geometry: `SH3_Assembly_OptV3_60cm.geo.setup`;
- normalization: per-family `sum(RP)/sum(TT)` with zero-RP DAT TT retained;
- NUBASE-2020 ground-state correction and fail-closed excited/unresolved states;
- exact `CC IP RP` support required for every transported positive ground state;
- 50,000 deterministic exact-position draws, stride 5 to 10,000 source blocks,
  with retained block flux multiplied by five;
- 33 delayed jobs and 8,000,000 triggers, exactly 1,000,000 per incident family;
- eight runner workers and a 50,000-trigger proton production canary;
- all products are non-overwriting and stored below `/mnt/data`.

Delayed transport remains separate from INSTANT and standalone PARMA511.  No
detector response or paper update is performed by this package.
