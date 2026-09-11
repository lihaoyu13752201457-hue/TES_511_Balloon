# SH3 Si-substrate SD neutron canary

This non-overwriting diagnostic package keeps the current SH3 OptV3 physical
geometry, six TES detectors, and three active BGO detectors unchanged. It adds
six independent Si-substrate scorers using the already retained 1 eV threshold
detector-map convention.

The Si channels are transport diagnostics only. Their deposited energy must not
be added to `E_TES` or interpreted as fully collected TES pulse energy. A later
phonon/thermal/TES response model is required for that mapping.

The canary reuses the current corrected-keV, 20-bin full-sphere atmospheric
neutron source and the existing guarded pilot runner. It transports 100,000
primaries with a fresh seed and stores full simulation information so that Si
energy deposits can be separated from TES and BGO deposits.

## Completed canary

- Status: PASS, 100,000 generated neutrons, 19.1897 s equivalent observation.
- Runtime: 7 min 19.64 s; peak RSS 2,605,460 KiB; compressed SIM 464,074,238 bytes.
- Si-positive events: 38; direct Si elastic-recoil events: 7 (9 recoil hit records).
- All 7 direct recoil events had group-summed BGO deposition above 50 keV; 5
  also had direct TES deposition.
- Direct elastic-recoil event deposition in Si: median 28.5714 keV, maximum
  169.4501 keV. Among the Si-positive events, neither raw Si total nor raw TES
  total fell in `[510.58, 511.42) keV`.
- One non-elastic Si-positive event had BGO below 50 keV; its direct TES total
  was 2774.83 keV, outside the 511-keV science window.

These counts establish that the scorer and event bridge work. Seven recoil
events are not enough for a background upper limit, and the transport result
still requires a phonon/thermal/TES response before it can be interpreted as a
TES pulse population.
