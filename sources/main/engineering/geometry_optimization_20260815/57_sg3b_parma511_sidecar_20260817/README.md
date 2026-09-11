# SG3B PARMA atmospheric 511-keV sidecar

This package adapts the retained PARMA day-15 atmospheric annihilation-line
module to the SG3B geometry.  The production card is monoenergetic at
510.99895 keV, uses the retained 80-bin equal-mu angular grid, and preserves
the physical full-sphere flux of 0.16651547160226118 ph cm^-2 s^-1.

The run is 3,000,000 transport events split into 13 independently seeded
shards (50,000-event canary, eleven 250,000-event shards, and one 200,000-event
shard) for eight-worker execution.  Outputs are prepared under
`/mnt/data/TES_Balloon_511_data/SG3/sg3b_parma511_sidecar_3m_v1`.

This is a standalone line-only sidecar.  It excludes the broadband continuum.
It must not be added directly to the repaired `unit_only_total_gamma` result,
which already contains an annihilation bump, unless a separate flux-closed
de-duplication and recomposition contract is established.
