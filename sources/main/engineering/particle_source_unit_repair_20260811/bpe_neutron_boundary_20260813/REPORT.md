# BPE corrected-neutron boundary and copper-activation screening

## Result

The 20 mm BPE layer has a **modest positive direct effect**, not an observed
direct penalty, for the copper activation channels that dominate the current
neutron-delayed W2 sample. The central output/input reaction-current indices
are 0.885 for Cu-61, 0.842 for Cu-62, and 0.897 for Cu-64. Cu-62 suppression is
the clearest result. Cu-64 is favorable in the central value, including its
capture channel, but its roughly 10% Monte Carlo uncertainty does not yet
exclude a neutral effect.

This answers the direct mechanism question. It does **not** by itself prove the
net change in final detector background, because bypass trajectories,
greater-than-100-MeV cascades, activation position, delayed transport, and
detector cuts are outside this boundary fold.

## Accepted simulation

- Geometry: retained S3d-O8, with the side, bottom, and top 20 mm BPE bodies
  watched at their outer and inner nominal surfaces.
- Source: corrected-keV, 20 equal-mu-bin atmospheric neutron source; no legacy
  `cosima_spectra_dp_2602units` reference.
- Physics: `qgsp-bic-hp` plus `LivermorePol`.
- Exposure: 100,000 histories, eight independent 12,500-event shards,
  `TT=19.21636 s`, seeds 88813201--88813208, at most six concurrent workers.
- Storage: native Cosima `ENTR/EXIT`, nine-digit scientific precision. This is
  needed because the default 0.001-keV text precision censors thermal neutrons
  and changes the Cu-64 capture conclusion.

The first launch with card-only seeds is excluded. Cosima accepts the random
seed through CLI `-s`; six same-second jobs in that launch were byte-identical,
and the final two formed another duplicate pair. The accepted run uses CLI
seeds and eight unique SIM headers.

## What 2 cm of BPE does to corrected neutrons

Of 34,031 primary histories that first contacted a nominal BPE outer surface,
22,988 later reached a nominal inner surface: conditional transmission is
67.55%. The remaining 32.45% were absorbed, reflected outward, or otherwise did
not reach the inner boundary.

Among the transmitted histories:

- 33.59% lost measurable kinetic energy;
- 28.18% lost at least 10%;
- 12.35% lost at least a factor of ten;
- 66.40% were unchanged within one part per million.

The result is strongly energy-dependent:

| Incident energy | Histories entering | Reached inner surface | Transmission |
|---|---:|---:|---:|
| <=0.5 eV | 685 | 11 | 1.61% |
| 0.5 eV--100 keV | 5,735 | 1,595 | 27.81% |
| 0.1--1 MeV | 4,818 | 2,888 | 59.94% |
| 1--10 MeV | 8,751 | 6,659 | 76.09% |
| 10--20 MeV | 1,946 | 1,573 | 80.83% |
| 20--39 MeV | 2,030 | 1,651 | 81.33% |
| >=39 MeV | 10,066 | 8,611 | 85.55% |

Thus, corrected fast neutrons mostly cross 2 cm of BPE; the layer is effective
against slow neutrons and provides partial moderation rather than complete
moderation of the main MeV population.

For all inward boundary crossings, including secondary neutrons and repeated
crossings, the median energy shifts from 1.320 MeV outside to 0.358 MeV inside.
The fractions above 10, 20, and 39 MeV change from 31.14%, 26.69%, and 22.11%
to 25.62%, 22.18%, and 18.48%. Total inward crossings rise from 46,673 to
50,032 because the inner current contains BPE-born secondaries and recrossings;
that count increase is not an energy gain or a one-particle transfer ratio.

## Natural-copper cross-section fold

The fold uses natural abundances 0.6915 for Cu-63 and 0.3085 for Cu-65 and the
local G4NDL4.5 tables. The common evaluated interval is `0 < E <= 100 MeV`;
higher-energy crossings remain in the spectrum but are excluded from this
direct-channel fold.

| Product | Principal direct channels | Output/input current index | Jackknife SE | Output/input 1/mu flux proxy | Jackknife SE |
|---|---|---:|---:|---:|---:|
| Cu-61 | Cu-63(n,3n), Cu-65(n,5n) | 0.8848 | 0.0127 | 1.0031 | 0.1136 |
| Cu-62 | Cu-63(n,2n), Cu-65(n,4n) | 0.8421 | 0.0103 | 0.8611 | 0.0372 |
| Cu-64 | Cu-63(n,gamma), Cu-65(n,2n) | 0.8966 | 0.0971 | 0.8358 | 0.0968 |

The Cu-64 total is dominated by Cu-63(n,gamma) in this boundary fold. Its
capture-only current ratio is 0.9021 +/- 0.1063; its Cu-65(n,2n) ratio is
0.8369 +/- 0.0082. Therefore the present sample does not show the feared
capture increase at the inner boundary, but capture resonances leave the
central 9.8% reduction statistically weak. The 1/mu quantity is only an
angular scalar-flux proxy and is especially noisy for grazing Cu-61 crossings;
the integrated crossing-current index is the primary boundary metric.

## Relevance to the present W2 background

The corrected S3d-O8 neutron-delayed final-W2 sample contains 17 selected MC
events at 0.0236791 cps. Cu-61, Cu-62, and Cu-64 contribute 2, 6, and 5 events,
or 13/17 = 76.47% of that sample. Their rates are 0.00278578, 0.00835733, and
0.00696444 cps, respectively.

Weighting the three boundary indices only by those observed Cu-event shares
gives a central screening index of about 0.870 for crossing current and 0.873
for the angular proxy: roughly a 13% favorable direct-Cu tendency. This is a
mechanism-ranking number, not a predicted no-BPE W2 rate; the detector sample
has only 13 Cu events and the boundary ratio cannot be inverted into a final
background rate.

## Interpretation relative to the factor-1000 error

The old neutron energy axis was lower by 1000. It therefore made 20 mm BPE look
well matched to the source: the old flux-weighted median was about 3.0 keV,
whereas the corrected median is about 3.0 MeV. The corrected calculation shows
that the layer still removes/moderates part of the current and lowers the
central direct Cu indices, but the benefit is only modest for the fast
population. Any old claim of near-complete neutron absorption or a large BPE
gain must remain retired.

## Remaining closure

A final net-benefit claim requires one minimal matched comparison: retain the
entire S3d-O8 geometry and source contract, change only BPE thickness (first
0 versus 20 mm), then rerun corrected neutron BUILDUP and the existing
activation/delayed/common-response chain. That comparison captures paths that
miss the nominal BPE bodies, greater-than-100-MeV and secondary hadronic
cascades (some Cu-62 is produced through secondary particles), spatial
coupling to the TES, and active-veto/Compton-FoV survival. The present boundary
diagnostic is sufficient to say that direct copper activation is not showing a
net central penalty from BPE; it is not sufficient to promote 20 mm as the
final optimum thickness.

