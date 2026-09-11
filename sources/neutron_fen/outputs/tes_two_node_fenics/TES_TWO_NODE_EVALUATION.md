# SH3 two-node Ta absorber / TES linear-response evaluation

## Model requested by the user

- Per-pixel TES-to-bath conductance at Tc: 0.8 nW/K.
- Per-pixel absorber-to-bath conductance at Tc: 0.2 nW/K.
- Absorber-to-TES conductance: 1000 nW/K.
- G4CMP Si-phonon sensor energy: 80% enters the TES node and 20% enters the
  absorber node, following the specified Si-contact-perimeter ratio.
- Photon and direct `TP_L...` mass-model deposits enter the Ta absorber.
- G4CMP surface absorption is an instantaneous source in this thermal model;
  no additional interface bottleneck is inserted.

The FEniCS solve is linearized about the voltage-biased operating point and
normalizes each event to 1 keV.  It therefore tests the below-saturation common-
template limit raised by the user, rather than the earlier nonlinear 511-keV
one-node response.

## Energy ledger for candidate C

The original candidate-C energy is 510.964285 keV.  Under the requested
allocation:

```text
absorber node = 468.906274 keV
TES node      = 42.058011 keV
total         = 510.964285 keV
```

Most energy remains on the photon-like absorber path because the 458.392-keV
direct `TP_L...` component enters the absorber.  Only 80% of the 52.573-keV
G4CMP substrate-phonon component enters the TES directly.

## Time scales and stability

```text
Ta--TES differential equilibration = 39.976 ns
electrical L/(R0+Rshunt)           = 302.115 us
combined intrinsic C/G            = 68.180 ms
linear poles                       = -24316144.348 s^-1, -475.716 s^-1, -2587.596 s^-1
```

All poles are negative.  The 1000-nW/K absorber--TES link removes the thermal
bottleneck as intended; the electrical inductance retains a small memory of the
brief direct-TES input.

## Small-signal pulse comparison

| event | peak per 1 keV | peak time | FWHM |
|---|---:|---:|---:|
| photon to absorber | 189.659398 nA | 800.000 us | 2.502500 ms |
| candidate C, 80/20 split | 189.674459 nA | 800.000 us | 2.510000 ms |

- Best-fit photon-template scale for C: 1.000037776.
- Time-weighted, unweighted-noise L2 shape residual: 0.602500%.
- Maximum pointwise leading-edge difference: 2.024525% of the C peak at 6.250 us.
- Doubling the time-grid resolution changes the residual to
  0.602216%.

The templates are therefore very similar in the linear, below-saturation limit.
This calculation does not establish pulse-shape rejection: a measured readout
noise PSD is required to turn the small residual into an optimal-filter
significance.  Candidate C's cross-layer and multi-pixel topology remains a
separate discriminator if those identities are preserved.

## Reproduction

```bash
cd /home/ubuntu/neutron_fen
mkdir -p build/fenics_cache/dijitso
PYTHONDONTWRITEBYTECODE=1 DIJITSO_CACHE_DIR=/home/ubuntu/neutron_fen/build/fenics_cache/dijitso \
  MPLCONFIGDIR=/home/ubuntu/neutron_fen/.matplotlib \
  /usr/bin/python3 code/simulate_tes_two_node_fenics.py
```
