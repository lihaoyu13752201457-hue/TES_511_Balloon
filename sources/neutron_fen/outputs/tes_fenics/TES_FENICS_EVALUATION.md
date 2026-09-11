# SH3 neutron-induced Si/TES pulse evaluation with FEniCS

## Result in one paragraph

Yes, an energy-only event sum can conditionally look like a 511 keV event, but
the present model does **not** support calling it indistinguishable once layer
and pixel information are retained. Candidate C gives a five-run mean TES
energy of 510.9643 keV, only 35.7 eV (0.200 detector sigma for a 420 eV FWHM)
below 511 keV. In the primary nonlinear electrothermal model its array-summed
current pulse has an 8.84% best-fit single-pixel-template residual. More
decisively, it comprises two direct L1 pixels plus a distributed L0 substrate
response: 313 channels receive nonzero Monte-Carlo weight, 15 receive at least
0.42 keV, and 10 receive at least 1 keV. Here 0.42 keV is only a reporting
threshold equal to the assumed 511-keV FWHM, not a hardware trigger threshold.
A true single-pixel 511 keV reference
has one such channel. Therefore it can be degenerate in scalar reconstructed
energy if channel identity is discarded, but it is not degenerate with the
single-pixel reference in the ideal pixel-resolved output. A calibrated readout
noise PSD and an ensemble of real 511 keV multi-site events are still required
to quote a measured rejection efficiency without signal loss.

## Data used

- Candidate C direct Ta/TES deposits: L1:P231 = 433.54379 keV and L1:P147 =
  24.847980806 keV.
- Candidate C substrate contribution: the actual energy/time/channel stream
  from five independent tuned-C G4CMP runs, averaged as alternative Monte Carlo
  estimates. Its mean L0 sensor energy is 52.572514 keV.
- Candidate C total: 510.964285 keV. The five independent reconstructed means
  are 511.386966, 511.680594, 510.714314, 510.720742, and 510.318809 keV
  (sample SD 0.554571 keV, SEM 0.248012 keV). This spread is Monte-Carlo
  uncertainty on the interface-response calculation, not TES noise.
- Strict recoil candidates A and B are tested as *counterfactual pulse shapes*:
  the nearest high-collection G4CMP channel/time patterns were scaled by
  1.024763 and 0.983991, respectively, so that their direct-plus-collected
  energy is exactly 511 keV. This does not assert that the required collection
  efficiencies occur in the physical detector.

## Ta and TES heat capacity

The current M05 manuscript specifies a `1.5 x 1.5 x 3.0 mm3` Ta absorber and
uses `5.99e-7 J kg-1 K-1` as its representative cryogenic specific heat. With
the NIST Ta density, 16.654 g/cm3, this gives

```text
Ta mass       = 112.4145 mg
Ta heat C     = 67.3362855 pJ/K
TES heat C    = 0.0400000 pJ/K       (user input)
total C       = 67.3762855 pJ/K
```

Thus the Ta absorber, not the TES film, controls the lumped heat capacity. An
instantaneous 511 keV deposition corresponds to an initial enthalpy jump of
1.2151 mK before electrothermal feedback; P231's 433.544 keV gives 1.0309 mK.

## Lumped nonlinear model

The Ta absorber and TES film are one isothermal node per pixel, as requested.
FEniCS uses one discontinuous-constant (`DG0`) computational cell to index each
independent TES pixel. The cell coordinate has no physical spatial meaning and
there is no invented lateral heat diffusion.

For every pixel, backward Euler solves the mixed nonlinear weak form of

```text
C dT/dt = I^2 R(T) - K (T^n - Tb^n) + Psignal(t)
L dI/dt = Vbias - I [Rshunt + R(T)]
```

The G4CMP hit energies are applied as enthalpy jumps at their simulated arrival
times. The primary resistance model is a phenomenological two-fluid-inspired
normal-fraction law,

```text
R/Rn = x/(1+x),   x=(T/Tc)^m,
```

where `m=142.857` is chosen so that `alpha=d ln R/d ln T=100` at
`R0=0.3 Rn`; `beta=0` because there is no explicit current dependence in
`R(T)`. A logistic-in-temperature transition is run as a cross-check.

## Explicit assumptions and stable bias point

The user supplied `Tc=100 mK`, `alpha~100`, `beta=0`, `L=1000 nH`,
`Rshunt=0.31 mOhm`, and `C_TES=0.04 pJ/K`. The missing quantities are exposed,
not fitted:

```text
Tbath             = 50 mK
Rn                = 10 mOhm
R0                = 0.3 Rn = 3 mOhm
thermal exponent  = n=3
primary G(Tc)     = 1 nW/K
```

The bias is derived from thermal equilibrium rather than independently tuned:

```text
T0                = 99.40865 mK
P0                = 28.5788 pW
I0                = 97.6026 uA
Vbias (Thevenin)  = 0.323065 uV
source Ibias      = 1.04214 mA
electrical tau    = 0.302115 ms
intrinsic C/G tau = 68.1803 ms
linear poles      = -498.61, -2399.37 per second
```

Both poles are real and negative, so the selected pulse is linearly stable and
overdamped. A 0.1 nW/K-step scan with the other assumptions fixed remains
stable through 8.0 nW/K and becomes unstable above that vicinity because the
large input inductance delays electrothermal feedback. FEniCS sensitivity runs
use stable `G(Tc)=0.5, 1, 2, 5 nW/K`.

## Primary FEniCS pulse results

Primary point: `G(Tc)=1 nW/K`, normal-fraction resistance law.

| input pattern | TES energy (keV) | nonzero channels | channels >=0.42 keV | peak sum-current deficit (uA) | peak time (ms) | pulse FWHM (ms) | best-fit 511-template residual |
|---|---:|---:|---:|---:|---:|---:|---:|
| one-pixel 511 photon | 511.000 | 1 | 1 | 52.673 | 0.640 | 4.935 | 0 |
| A, eta forced to 511 | 511.000 | 56 | 12 | 70.339 | 0.730 | 3.503 | 13.77% |
| B, eta forced to 511 | 511.000 | 45 | 8 | 67.103 | 0.720 | 3.709 | 11.58% |
| C, actual tuned-C mean | 510.964 | 313 | 15 | 63.223 | 0.720 | 3.965 | 8.84% |

The large number of nonzero C channels partly reflects weighted Monte-Carlo
tails. The counts above the explicit 0.42 and 1 keV reporting thresholds are 15
and 10, respectively; neither is claimed as the actual trigger threshold. Its
dominant channel remains L1:P231 at 433.544 keV; no individual channel contains
511 keV.

## Robustness checks

- Halving every time-step changes pulse peaks, current integrals, and template
  residuals by less than 0.3%.
- Replacing the normal-fraction law with a linear-temperature logistic law at
  the same local `R0`, `alpha`, and bias changes candidate C's residual from
  8.842% to 8.813% and its peak from 63.223 to 63.342 uA.
- Over stable `G(Tc)=0.5, 1, 2, 5 nW/K`, candidate C's template residual is
  8.24%, 8.84%, 8.84%, and 16.13%. Its FWHM is 7.613, 3.965, 2.119, and
  1.070 ms. The qualitative split-event shape difference persists.

## What “indistinguishable” means here

### Energy only

If the tuned-C mean efficiency is treated as fixed, a Gaussian response with
420 eV FWHM places its 510.9643 keV mean only 0.200 sigma from 511 keV and gives
a 97.91% probability of falling in `[510.58, 511.42)` keV. It is therefore
indistinguishable by scalar energy alone at this conditional efficiency. This
97.91% excludes the much larger uncertainty in the uncalibrated Si-to-TES
interface and is not an event-rate prediction.

### Pulse and topology

The summed nonlinear pulse is not identical to a one-pixel 511 keV template,
because splitting the energy over many voltage-biased nonlinear pixels changes
the peak and decay. More importantly, candidate C has simultaneous L1 direct
energy and an L0 distributed substrate tag. A pixel/layer-aware readout should
therefore distinguish it easily from a one-pixel full-absorption event.

This study cannot yet prove rejection against *all genuine* 511 keV events:
real 511 keV photons can Compton scatter across multiple pixels or layers, and
the present input set contains no corresponding reference ensemble. A measured
or simulated 511 keV signal library and the SQUID/readout noise covariance are
needed for an optimal-filter false-positive/false-veto matrix.

### Strict recoil candidates A and B

A and B can be made energy-degenerate only under the already identified extreme
collection requirements, approximately 97.1% and 89.9%. At the common tuned-C
interface point their reconstructed energies are only 62.36 and 63.46 keV. At
the tested high-collection point they are 499.07 and 519.31 keV. The FEniCS
energy-matched tests show what their pulses would look like *if* the interface
were tuned to exactly the required eta; they do not raise those efficiencies
from possibilities to predictions.

## Reproduction

Run the system FEniCS installation with workspace-local JIT output:

```bash
cd /home/ubuntu/neutron_fen
mkdir -p build/fenics_cache/dijitso
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 code/simulate_tes_fenics.py
```

Machine-readable model configuration, complete pulse traces, per-channel
summaries, solver diagnostics, convergence data, and input hashes are next to
this report. No file outside `/home/ubuntu/neutron_fen` is written.
