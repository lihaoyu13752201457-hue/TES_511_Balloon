# SG3B prompt TT and activation-origin audit

## Result

The SG3B INSTANT exposure used by package 58 already includes the retained base batch and the
independent extra-2x add-on.  For gamma it is 1,069,246 events / 
19.682580 s plus 2,138,492 events / 
39.422890 s, hence
**3,207,738 events / 59.105470 s**.  The event
multiplier is exactly 3.000000x and the receipt-TT multiplier is
3.002933x.  Package 58 therefore did not normalize only one copy.

For a full-sphere FarFieldAreaSource, the analytic generation rate is
`sum(Flux) * pi * R^2`.  With gamma flux 4.79966157778 cm^-2 s^-1 and
R=60.0 cm, the rate is
54282.893589 primaries/s.  The same source would make 10,000,000
gamma equivalent to **184.220 s**, while 1000 s would contain
about 54,282,894 gamma.

The remembered M05 10-million run is not present as a completed accepted authority.  Batch0003's
10-million value is a planned ceiling; its committed shard-0076 prefix is 2,001,000 events per
geometry.  The final corrected M05 accepted prompt manifest contains:

| geometry | accepted gamma | sum TT [s] | inferred TT for 10m [s] |
|---|---:|---:|---:|
| Mass_model_511 | 3,207,739 | 59.067145 | 184.139 |
| S3d_O8 | 3,207,738 | 59.096541 | 184.231 |

Thus the corrected M05 authority agrees with SG3B at about 184 s per 10 million gamma.  A 1000-s
number must belong to a different source flux/surface contract or to a historical/non-authoritative
normalization; it cannot be reproduced from these corrected-keV receipts.

## Delayed equivalent-time convention

Each family has 1,000,000 delayed triggers.  Its equivalent time is `N/A_family(day15)`, not a
single shared mission exposure:

| family | triggers | A15 [Bq] | constant-day15 equivalent time [s] |
|---|---:|---:|---:|
| p | 1,000,000 | 724.273564 | 1,380.694 |
| n | 1,000,000 | 330.021022 | 3,030.110 |
| alpha | 1,000,000 | 287.541136 | 3,477.763 |
| gamma | 1,000,000 | 6.59231051 | 151,691.884 |
| eminus | 1,000,000 | 0.667877327 | 1,497,280.951 |
| eplus | 1,000,000 | 2.95369593 | 338,558.885 |
| muminus | 1,000,000 | 0.247887655 | 4,034,085.519 |
| muplus | 1,000,000 | 1.26043077e-09 | 793,379,549,239,666.125 |

These times describe Monte Carlo sampling at the day-15 activity mixture.  The 20-day result is
obtained by the nuclide-resolved activity curves and Poisson common-time live factor; it must not be
computed by treating the delayed triggers as prompt atmospheric primaries.

## Activation-origin section

The detailed and global side sections label 35 nuclide+mother-volume groups covering all 394
delayed events that survive the final W2 response.  Sixteen nuclides are present.  Every plotted
colored point is the exact delayed source position carried by the audited source/position lineage;
the gray curves are their decay-to-TES routes, and the red curve is the sole prompt survivor.

This is deliberately a selected-background origin map.  It does not claim to show every produced
activation nucleus and does not reconstruct the earlier BUILDUP production track.  Full volume
names, coordinate ranges, event counts, day-15 rate, and 20-day contribution are in
`selected_w2_activation_origin_groups.csv`.
