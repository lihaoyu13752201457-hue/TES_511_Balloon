# MEGAlib/Cosima unit contract — local authoritative evidence

Evidence snapshot: 2026-08-11. Installed version: MEGAlib `4.02.00`
(`MEGAlib/config/Version.txt:1`). The paths below are relative to
`/home/ubuntu/MEGAlib_Install/megalib-main/` and are hashed in
`../../data/evidence_hashes.csv`.

## Manual contract

- `doc/Cosima.pdf`, PDF page 27: the first `DP` value of a `Spectrum File`
  is energy in keV; the second is a differential shape per keV. Its overall
  normalization is arbitrary because `.Flux` supplies the absolute rate.
- `doc/Cosima.pdf`, pages 28–29: far-field sources require particles/cm²/s.
  `FarFieldAreaSource` uses minimum/maximum theta and phi in degrees and is
  homogeneous in the specified spherical segment.
- `doc/Cosima.pdf`, page 30: `PointSource` x/y/z are cm and its flux is
  particles/s.
- `doc/Cosima.pdf`, pages 34–35: a far-field run obeys
  `N = t × A × F`, with `A = pi × r²`; near-field obeys `N = t × F`. A
  differential intensity per energy and solid angle must be integrated before
  it is supplied as `.Flux`.
- `doc/Cosima.pdf`, page 37: an EventList row has 15 fields; time is seconds,
  position is cm, and energy is keV.
- `doc/Cosima.pdf`, page 23: `Events`, `Triggers`, and `Time` are distinct stop
  criteria; `Time` is seconds.
- `doc/Geomega.pdf`, page 6: `SurroundingSphere` radius, center, and disk
  distance are in cm.

## Source-code contract

- `src/cosima/src/MCParameterFile.cc:1033-1043`: mono source energy is
  multiplied by `keV`.
- `src/cosima/src/MCParameterFile.cc:1254-1269` dispatches a `Spectrum File`
  to `MCSource::SetEnergy`.
- `src/cosima/src/MCSource.cc:1909-1918`: file x values are scaled with
  `ScaleX(keV)` and y with `ScaleY(1/cm/cm/s/keV)`. A bare DP x value is
  therefore interpreted as a numerical number of keV.
- `src/global/misc/src/MFunction.cxx:791-813`: random sampling constructs a
  cumulative integral and samples a fraction of its total. A common y-axis
  scale cancels; it does not rescale `.Flux`.
- `src/cosima/src/MCSource.cc:2727-2729,2775-2778`: the sampled file x value is
  sent directly to `SetMonoEnergy`.
- `external/geant4_v10.02.p03/include/Geant4/G4ParticleGun.hh:44-55`: the
  particle gun accepts kinetic energy for the selected particle. Cosima has no
  special MeV-per-nucleon branch for these file spectra, so alpha must be
  converted externally to total alpha kinetic energy.
- `src/cosima/src/MCParameterFile.cc:1326-1334`: far-field area angles are
  multiplied by `deg`.
- `src/cosima/src/MCSource.cc:2818-2823`: theta is uniform in cos(theta) and
  phi is uniform in its interval, i.e. uniform in solid angle.
- `src/cosima/src/MCParameterFile.cc:2834-2846`: far-field Flux is parsed as
  `/cm/cm/s`; near-field Flux as `/s`.
- `src/cosima/src/MCSource.cc:528-532,1991-1995`: a spherical far-field start
  area is `pi × R²`, and Cosima multiplies input far-field flux by that area.
- `src/cosima/src/MCParameterFile.cc:1463-1469`: PointSource coordinates are
  multiplied by `cm`.
- `src/cosima/src/MCSource.cc:2274-2289`: EventList requires exactly 15 tokens;
  energy, position, and time are multiplied by `keV`, `cm`, and `second`.

## Evidence identity

- `doc/Cosima.pdf` SHA-256:
  `1e15aed3039b625e0bb6988b5aea912ae2292f34f2bfb95ba1117cbf7624992a`
- `src/cosima/src/MCSource.cc` SHA-256:
  `1322cb460bd0e8cd2c788e5507ec3be5de06d97d65af98f013055480d5d94b1d`
- `src/cosima/src/MCParameterFile.cc` SHA-256:
  `36ea3cdf3fd26b6ec9b9739bf2939b972281f1f19701cbf6ed4455779859f1ba`
