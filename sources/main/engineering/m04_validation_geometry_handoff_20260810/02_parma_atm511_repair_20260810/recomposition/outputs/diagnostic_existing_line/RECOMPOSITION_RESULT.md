# Atmospheric-511 modular recomposition result

Status: `DIAGNOSTIC_ONLY_MODULAR_RECOMPOSITION__NOT_PAPER_AUTHORITY`

This is an offline W2 recomposition. No Cosima/transport, continuum, other-particle,
M-sampling, geometry, detector-response, selection, or signal run was launched.

Day 15 keeps prompt `0.00339303151412` cps, delayed
`0.00201657067387` cps, and the 45-degree slant signal
`0.000986227890904` cps. It removes the legacy sidecar
`0.00155526135195` cps and adds the corrected PARMA
line `0.00417489551561` cps. The recomposed background is
`0.0095844977036` cps.

The selected-rate de-dup delta remains exactly zero in W2 and Broad480-550.
Separately, the active-only/TES-zero misplaced prompt-gamma line contributes to
accidental occupancy, so day 15 removes
`737.844505176` Hz from retained
prompt occupancy using `prompt_scale_gamma`. Prompt occupancy changes from
`23733.994097` to
`22996.1495918` Hz, and the live factor
changes from the pre-fix `0.975888384844`
to `0.976608704435`. The legacy sidecar occupancy is
omitted separately once; it is not subtracted from the prompt term.

The 20-day central fold gives S=`1650.79217224`,
B=`16014.9666334`, and Z=`13.0445584106`.
Relative to the pre-fix recomposition, the occupancy correction changes these by
`1.21703758089` source counts,
`12.1188242375` background
counts, and `0.00468233742615` in Z.
The supplied line-response grade is `DIAGNOSTIC_ONLY_FAILS_PARMA511_RATE_STATISTICS`.

These numbers are not publication authority. In particular, the legacy prompt-gamma
axis has the factor-1000 energy-abscissa blocker, and the frozen selection's
`ACTIVE_SHIELD` substring includes passive `ActiveShield_S3C_BGO_Kapton_*` scorers.
Both historical implementations are preserved here; neither is repaired or rerun.
