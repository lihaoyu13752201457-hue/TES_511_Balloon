# SH3 OptV3 60 cm adaptive INSTANT campaign

This package is a non-overwriting transport variant.  It retains the reviewed
OptV3 `.geo` and nine-definition detector map, while replacing the inherited
95 cm source surface with the SG3B contract:

`SurroundingSphere 60 5 0 9 60`

The native WRL envelope has a maximum non-container material radius of
58.0284 cm about `(5, 0, 9) cm`.  Invisible geometry is limited to the vacuum
containers and the TES pixel hierarchy, which lies inside the visible BGO and
cryostat envelope.  `validate_surface.py` writes the machine-readable receipt.

`adaptive_campaign.py` prepares a small smoke or runs a two-profile adaptive
full transport round. Corrected-keV broadband and the standalone PARMA511 line
remain separate profiles and ledgers. Each full round contains the canonical
accepted INSTANT and BUILDUP matrix plus the independent 3 M PARMA511 sidecar.
The first round uses the full accepted statistics; if it completes before the
2.5 h campaign deadline, a fresh-seed repeat is scaled from the measured full
round wall time. The allocation is six canonical runner workers for corrected
transport and two workers for PARMA511. Delayed-decay transport remains a
sequential downstream stage because its source must first be rebuilt from the
new round's BUILDUP `CC IP RP` inventory.

All transport output is required to live below `/mnt/data`.
