# REMOVE-BPE + Al shield + MXC-0.375 candidate audit

Date: 2026-08-14

## Candidate definition

- Remove all three 20 mm BPE bodies.
- Keep plastic, BGO, Nb and other geometry unchanged.
- Replace the existing MuMetal sleeve and back cap by same-volume Aluminium.
- Change the MXC Cu plate from 6 mm to 3 mm, then remove 25% of the remaining plate area with uniformly distributed 4 mm through-holes. The assumed final MXC mass fraction is therefore `0.5 × 0.75 = 0.375`.

## Verdict

`ENGINEERING KILL / PHYSICS-UNSUPPORTED` as a main configuration.

The configuration has a real payload-mass advantage, but its magnetic function is not qualified, its MXC thermal/structural margins are not closed, and no candidate-specific transport demonstrates a net background reduction. Even deliberately over-generous background arithmetic does not reach the central mission target `F3 <= 3e-5 photon cm^-2 s^-1`.

## FACT — geometry, signal and mass

| Quantity | Result |
|---|---:|
| Official post-envelope `S20` proxy | 1645.387753 counts |
| Literal full-envelope `S20` proxy, BPE removed but 1 cm plastic retained | 1495.197302 counts |
| Candidate-specific literal `B20_max=(S20/10)^2` | 22356.149713 counts |
| Literal current full-panel `S20` proxy | 1242.047432 counts |
| Signal change versus literal current full panel | +20.38% |
| Signal change versus PORT-20 | -9.13% |
| BPE mass change | -33.605617 kg |
| MuMetal-to-Al mass change | -0.345456 kg |
| MXC mass change | -2.373454 kg |
| Total mass change | **-36.324526 kg** |

The 37,194 focused straight rays pass through the existing Mu back-cap central hole and do not intersect the MXC plate. MuMetal-to-Al and MXC thinning therefore receive no direct focused-ray signal credit; candidate scattering response remains unknown. The official stage04 signal starts after the outer envelope, so it cannot measure the BPE/plastic transmission penalty.

Twenty-five per cent open area in a 30 cm diameter plate requires approximately 1406–1407 ideal 4 mm holes. The equivalent pitch is about 7.09 mm on a square lattice or 7.62 mm on a triangular lattice before edge/interface exclusions.

## HYPOTHESIS — deliberately optimistic delayed scaling

Baseline delayed `D20 = 88804.862652 counts` contains:

| Existing source host | Baseline 20-day counts | Evidence quality |
|---|---:|---|
| MXC Cu plate | 27429.933127 | 57 rows; low position support |
| MuMetal exact material | 12735.445044 | 20 rows; event Neff 2.917 |
| All other delayed hosts | 48639.484481 | retained by this arithmetic |

Assume, unrealistically, that MXC selected background scales exactly with remaining mass, all observed MuMetal background disappears in Al, BPE removal has no penalty, new Al produces no selected background, and no production/coupling migration occurs. Then:

```
MXC credit       = 0.625 × 27429.933127 = 17143.708204 counts
MuMetal credit   = 12735.445044 counts
D20_linear       = 58925.709404 counts
P20 unchanged    = 55398.979434 counts
B20_linear       = 114324.688838 counts
```

| Signal scope | `F3` | Change versus official `6.92375e-5` |
|---|---:|---:|
| Invalid-for-envelope post-layer proxy | 6.16486e-5 | -10.96% |
| Literal candidate with retained plastic | **6.78411e-5** | **-2.02%** |

The second line is the relevant simple arithmetic screen. It still has `B20/B20_max = 5.11` and is not a physics prediction.

## HYPOTHESIS — known-mechanism stress proxy

- Reversing the accepted BPE direct-neutron Cu-61/62/64 current mechanism gives an illustrative `+4443.3 delayed counts`. This is not a matched W2 result.
- Removing BPE and reducing the MXC 511-keV grammage increases the already-observed frozen prompt root's analytic transmitted weight. The root-only risk band is approximately `+10160.64` to `+20183.04 prompt counts`; it is not a total-prompt prediction.

Applying only these two known-mechanism penalties to the optimistic mass-linear screen gives:

| Quantity | Range |
|---|---:|
| `B20` | 128928.628838–138951.028838 counts |
| Literal-envelope `F3` | **7.20439e-5–7.47917e-5** |
| Change versus official baseline | **+4.05% to +8.02% (worse)** |

No positive prompt credit is supported: the three final S3d roots pair first in Nb, Nb and DR Cu, not in MuMetal or MXC. Lower-Z Al can reduce conversions in the replaced shell while making photons more transparent or moving the pair/annihilation host into Nb, Cu, Ag or remaining cold mass.

## FACT — target cannot be closed by these hosts

Even the unphysical assumption `P20=0`, zero new-Al background, zero BPE penalty and mass-linear MXC suppression gives literal-envelope `F3 = 4.87052e-5`. If both the current MXC and MuMetal delayed contributions are instead deleted perfectly and prompt is also set to zero, the retained other delayed background alone gives `F3 = 4.42504e-5`. Both fail `3e-5`.

## Engineering gates

- **MAGNETIC HARD NO-GO:** normal Aluminium is not a high-permeability substitute for MuMetal. A deliberately superconducting-Al concept would be a different shield design and would still require DC/AC attenuation, cool-through-Tc, trapped-flux, seam, TES/SQUID noise and stability qualification.
- **THERMAL HARD GATE:** the simple remaining in-plane Cu section is only about 37.5% of baseline before lattice tortuosity, contacts and hole-edge effects.
- **STRUCTURAL HARD GATE:** halving thickness reduces the unperforated plate's bending-stiffness scale to about one eighth; the holes reduce it further and add stress concentration. About 1406 holes are not a sparse/simple M4 relief pattern.
- **ACTIVATION UNKNOWN:** baseline Al inventory includes Na-24, Mg-27, Al-28, F-18 and Na-22, but those Al volumes are at different positions. Their zero observed selected survivors cannot be transferred to a new near-field Al shell.

## Minimum falsification sequence

1. Reject immediately unless a 3-D magnetic model plus field-cool/TES/SQUID tests pass the existing magnetic hard gates.
2. Reject unless the 3 mm perforated plate passes thermal spreading, interface-gradient, cooldown, vibration and launch-load margins.
3. If and only if both engineering gates pass, run matched baseline/candidate n, p and alpha BUILDUP with exact-position Cu/Nb/Al production and a candidate-specific focused replay from outside the plastic.
4. Promote only if candidate upper background and lower signal satisfy `P20^U + D20^U <= (S20^L/10)^2` and both central and conservative `F3 <= 3e-5`.

