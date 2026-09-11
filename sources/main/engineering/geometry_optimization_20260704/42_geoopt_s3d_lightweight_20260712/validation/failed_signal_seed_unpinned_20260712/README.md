# Quarantined matched-signal attempt

The first fresh S3c-C0 signal branch completed 37,194 events, but Cosima was
invoked without the command-line `-s` option.  Although the source card stated
seed `260616`, the SIM header recorded wall-clock seed `1783844871`.

The fail-closed header audit stopped before the S3d branch.  The invalid C0 SIM
and its log are retained here as debugging evidence and are excluded from all
acceptance comparisons.  The replay helper was corrected to pass the pinned
seed explicitly before restarting the matched pair.
