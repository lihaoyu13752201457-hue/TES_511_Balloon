# SG3B prompt and activation coupling into TES

## Readout boundary

The selected sample is exactly one prompt event plus 394 delayed events, reproduced with the
package-58 keyed noise, 50 keV plastic/BGO veto, measured W2 window, and Step05 trajectory rule.
The event fold closes to 90727.336602564 live background counts
over 20 days, matching package 58 within -5.82e-11 count.

## Prompt route

The sole prompt survivor is a 4403.906 keV
atmospheric gamma.  It undergoes pair production in the passive SG3B Bi upper half-cylinder at
`x'=3.206, y'=-3.665, z'=-4.982 cm`
(`r=3.671 cm`).  The positron annihilates in the same Bi; one 510.999 keV photon
then Compton-scatters and photoabsorbs in two L5 TES pixels.  Plastic and BGO record 0 keV, so the
event is not vetoable by the present active layers.  This is direct route evidence that the Bi
half-cylinder can create a prompt W2 event.  With N=1, its rate has 100% relative MC uncertainty.

## Delayed route

Every delayed survivor contains a beta-plus decay and positron annihilation; the final TES energy
is carried by annihilation gamma interactions.  At day 15, activated Copper contributes
70.87% of delayed W2, Aluminium
15.35%, Bi
7.49%, and W
3.51%.  The SG3B Bi liner term is four
Po-199 events from proton activation: 0.00282692 cps,
with N_eff=4; its
50% single-cell MC uncertainty prevents a precise Bi rate claim.

The largest normalized source volumes are listed in `activation_by_volume.csv`.  The diagnostic
separates selected-event source location from BUILDUP production history: it does not reconstruct
the earlier atmospheric-particle track that created each nuclide.

## W collimator context

A passive focal-plane W collimator is not intrinsically required by a Laue focusing telescope.
The inherited focused-signal proxy has 4848/37194
(13.03%) rays interacting first in the W collimator, and none of
those rays pass the final signal selection.  In the SG3B delayed sample, the multihole HBar and
center VBar have 0 selected events despite 0.47142 Bq combined day-15 activity; the separate
passive W bottom plate contributes 3 selected events and 3.53% of 20-day delayed counts.  These
facts argue for a matched collimator-on/off ablation, not an unconditional keep/remove decision:
the current package does not measure how much off-axis background the collimator rejects, and the
signal result remains an unchanged-geometry SE3 proxy rather than fresh SG3B signal authority.
