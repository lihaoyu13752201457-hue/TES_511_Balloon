# Physics Assumptions

## Current Channel Baseline

The first implementation is a calibrated, axisymmetric effective channel
model. It is designed to validate geometry, outputs, phase-space handoff, and
benchmark bookkeeping before importing a physical multilayer reflectivity
table.

- The aperture is a 9 cm diameter disk.
- Photon survival is sampled with `raytrace.total_transmissivity`.
- `open_fraction` is not multiplied again.
- Surviving photons are directed to the 12 m focal plane with a Gaussian
  angular spread calibrated so the 90% containment diameter is about 3.6 cm.
- Absorbed and leaked events are separated by `loss_absorb_fraction`.

This is a toy/calibrated optics model, not a 511 keV W/Si transfer-matrix
calculation.

## Staged Optics/Detector Interface

The main research line is focusing optics. The optics and TES/BGO detector do
not need to live in one continuous Geant4 mass model. They can remain separate
simulations connected by a phase-space handoff, which is more practical for long
instrument baselines and independent validation. Detector outputs are retained
as interface regression guards, not as the current physics-refinement priority.

The stable handoff tables are:

- `phase_space.csv` for post-optics primaries at the detector plane;
- `optics_history.csv` for channel/Laue process provenance and losses;
- `hits.csv` for detector raw hits;
- `event_summary.csv` for detector-level event aggregation.

The minimum `phase_space.csv` contract remains
`event_id,E_keV,x_mm,y_mm,z_mm,ux,uy,uz,weight,source_tag`. The recommended
Geant4 channel/Laue writers now append
`particle_name,pdg_encoding,track_id,parent_id` so the same handoff can carry
particle identity. In the science channel and Laue executables those fields are
still `gamma,22,...` because those apps are science-photon optics scaffolds, not
all-particle optics-background models.

For prompt cosmic-ray optics backgrounds, use the same EXPACS/PARMA full-sphere
environment as the detector background chain. The builder
`analysis/build_expacs_farfield_source.py` parses the Cosima
`FarFieldAreaSource` components and writes an opticsim far-field source
configuration plus optional primary CSV samples. The source disk convention is:
sample a direction from the EXPACS theta/phi bin, place the primary on a disk
perpendicular to that direction at `-source_distance_mm * direction`, and launch
the particle toward the optics origin. This is the correct source-level
definition for prompt all-particle optics transport; radioactive delayed
activation remains a material-volume isotope/decay source, not a far-field
source. When the builder writes a finite-duration primary CSV, each row's
`weight` is the dimensionless expected number of physical primaries represented
by that sampled row, `total_rate_hz * duration_s / n`; without a fixed duration
the sampled Poisson sequence uses unit row weights. `source_distance_mm` is only
the upstream sampling-plane distance from the optics origin; for a 20 m world
with a detector/focal plane 12 m downstream of the optics, choose a source-plane
distance that fits the remaining upstream world, such as 8 m, or enlarge the
world. The source flux/rate normalization is set by the source disk area, not by
that arbitrary sampling-plane distance.

`geant4_app/src/all_particle_farfield_demo.cc` is the first Geant4 11.4
connection for this source. It reads the sampled primary CSV, uses `FTFP_BERT`
to define and transport all listed particle species, loads the existing
channel/Laue optics mass scaffolds by default, and records focal-plane crossings
as the same `phase_space.csv` contract with
`particle_name,pdg_encoding,track_id,parent_id,creator_process,source_particle_name,source_pdg_encoding,time_s`.
The `--optics-mass` option can select `none`, `channel_4ring`,
`laue_multiring`, or `both`.
This corrects the earlier vacuum-only handoff scaffold: prompt all-particle
transport now sees the existing Si channel-tile and Ge Laue-crystal masses.
Those masses are still the current simplified optics scaffolds, not a
publication-grade full optical-assembly/support/activation model, so rates from
this path should be treated as interface-level prompt-background estimates until
the final mass model is refined.

The focal-plane scorer records any track crossing the plane during the prompt
Geant4 event, including prompt secondaries from interactions in the Si/Ge mass
scaffold. The same run also writes `activation_inventory.csv` with secondary
ion/isotope candidates produced during prompt transport, including true
production position, `Z`, `A`, excitation, stability flag, lifetime, volume, and
creator process. `analysis/build_optics_activation_decay_source.py` converts
radioactive entries in that inventory into a day-N decay-ion source using the
same continuous-production activity formula as the detector day-15 workflow,
and can optionally integrate a time-variable activation-driver profile.
`geant4_app/src/activation_decay_focal_demo.cc` then decays those ions at their
recorded positions with Geant4 RadioactiveDecay and records detector-relevant
focal-plane crossing particles. This is the optics-side analogue of the RPIP
position-preserving delayed source, but the present rates remain scaffold-level
until the optics mass and activation statistics are production quality.

`analysis/validate_io_contract.py` validates these schemas and detector
crosslinks. Future Geant4 optics or Geant4 detector-only apps should match the
same contracts rather than requiring a direct optics-to-TES geometry coupling.

## W/Si Reflectivity Candidate

`data/reflectivity/generate_wsi_parratt_table.py` uses
`xraydb.multilayer_reflectivity` to generate a first W/Si 30/150 nm, 30-period
candidate table at 511 keV. The generated table is useful for replacing the
constant toy survival model, but it does not by itself solve the channel
geometry problem: the grazing angle used for lookup must be physically tied to
the effective channel path.

With the original coarse 511 keV W/Si table, a fixed grazing angle near
`1.496e-4 rad` gave about 80% multi-bounce transmissivity. A later audit found
that this table was too coarse near the critical-angle drop. The current
Channel mainline therefore uses
`data/reflectivity/WSi_511keV_parratt_grid_dense.csv` and dense-table
ring-calibrated angles in `data/channel/cam511_channel_rings.csv`. Using the much
larger `ring_bending_per_bounce` diagnostic angle gives essentially zero
transmission, which is a useful warning against confusing total bending angle
with local grazing angle.

The explicit four-ring diagnostic writes `per_ring_summary.csv/json`. A
ring-calibrated mode can choose one effective grazing angle per ring so each
ring has about 80% survival after its estimated number of bounces. This is still
an effective model, but it is a better four-ring benchmark target than using one
shared angle for rings with different bounce counts.

`analysis/crosscheck_wsi_parratt.py` independently recomputes the W/Si table
with a local s-polarization Parratt recursion using xraydb only for material
optical constants. This cross-check does not call
`xraydb.multilayer_reflectivity`; it validates the table-generation arithmetic
and provenance, but it is still based on the same Chantler optical constants.

## Geant4 Boundary Prototype

`GammaChannelReflection` now supports constant toy `R/A/T` and has a minimal
two-wall demo. The reflection branch kills the boundary-primary and emits a
secondary with the reflected momentum to avoid repeated re-triggering on the
same boundary in Geant4 10.2.

`GammaChannelReflection` also supports CSV table-driven W/Si `R/A/T` lookup via
`optics::ReflectivityTable`. The first validation executable,
`channel_two_wall_table_demo`, uses a micron-scale two-wall geometry whose
incoming direction has a controlled grazing angle. It writes
`optics_history.csv` with one row per boundary action, including the looked-up
R/A/T, grazing angle, pre/post directions, position, and action. At
`theta=1.5e-4 rad` with the current W/Si table, the expected two-bounce
survival is close to `R^2`; this is the per-bounce Geant4 nucleus for the next
curved-channel implementation.

`channel_single_curved_demo` is the first segmented curved-wall geometry v0. It
places rotated wall segments along a single curved channel and uses the same
`GammaChannelReflection` table/constant process. With `R=1` it produces
boundary histories and phase-space output, so the Geant4 geometry/process/output
path is now proven beyond the straight two-wall case. It is still diagnostic:
after fixing a wall-center placement bug, a low bend angle around `3e-4 rad`
gives local grazing angle near `1e-4 rad` and high W/Si table survival, but the
12 m focusing bend estimate `46 mm / 12 m = 3.83e-3 rad` gives local grazing
angle near `3.65e-3 rad` and table-driven survival of zero. This should be
treated as a real optics-geometry/focusing issue to debug, not tuned away.

`analysis/scan_single_curved_geometry.py` automates this bend-angle and
segment-count diagnostic and writes `runs/geant4_channel_single_curved_scan`.

`analysis/scan_single_curved_gap.py` extends the diagnostic by scanning channel
half-gap at both a low bend angle and the simple 46 mm / 12 m focusing-bend
estimate. With 128 segments, shrinking the half-gap from 1 um to 0.05 um does
not rescue the 12 m interpretation: table-driven W/Si survival remains zero and
the constant-R geometry still reports milliradian-scale mean grazing angles.
The same scan also shows that smaller gaps can add extra bounces and destroy
the otherwise high-survival low-bend case, so the gap cannot be used as a free
tuning knob.

`analysis/estimate_channel_geometry_constraints.py` adds a paraxial/specular
consistency estimate for the four 511-CAM rings. If each small-angle reflection
changes the photon direction by roughly `2 theta`, the configured ring
deflections require about 6-13 reflections at the calibrated
`theta ~ 1.5e-4 rad`, whereas the current effective model uses 1-3 bounce
bookkeeping. This does not prove the final channel geometry, but it explains
why directly interpreting the configured bend as a simple single-channel
curvature is inconsistent with the W/Si table.

After this diagnostic, the OSTI accepted manuscript for Shirazi et al. 2020 was
downloaded and text-searched for channel ray-tracing details. Its 122 keV
strawman soft gamma-ray concentrator is not identical to 511-CAM, but it says
the parallel-beam ray tracing has 17-38 reflections depending on ring length and
radius. That external clue is consistent with the analytic estimate above and
raises confidence that the next missing piece is the original many-bounce
channel path, not a small code fix in the current single-curved demo.

`analysis/reconcile_channel_bounce_path.py` turns that conclusion into a
small audit artifact. It compares three levels in one table: current 1-3
effective bounces, the 6-13 bounces required if the configured 511-CAM bends
are accumulated as `2Ntheta` at the calibrated W/Si angle, and the 17-38
reflection lineage clue from Shirazi/Bloser. Applied only as a bracket, the
17-38 range implies local grazing angles around `2.5e-5` to `1.13e-4 rad` for
the configured 511-CAM ring bends, i.e. below the current calibrated
`~1.5e-4 rad` scale. This does not solve the geometry, but it narrows the next
work item to recovering the original IDL/path model before constructing a
four-ring wall-by-wall Geant4 implementation.

## Detector-Only TES/BGO Prototype

`external_baseline/detector_response_py` consumes optics `phase_space.csv` and
implements a calibrated probabilistic detector-only benchmark. It is intended to
exercise the detector interface and post-processing tables before a full Geant4
TES/BGO mass model is connected.

- Geometry follows the guide-level 511-CAM reference: Bi absorber, 8 layers,
  20x20 pixels, 1.45 x 1.45 x 2.0 mm pixels, and a BGO shield.
- Photons are propagated to the configured detector plane, mapped to TES pixels,
  and sampled with an 8-layer cumulative stack efficiency.
- TES hits are written as raw hit rows; event summaries aggregate single-hit,
  multi-hit, BGO veto, reconstructed energy, and the 510.3-511.8 keV line-window
  selection.
- The current default uses a calibrated 65% stack efficiency, 390 eV
  reconstructed FWHM at 511 keV, 93% full-energy peak fraction, 10% multihit
  fraction, and 1% signal self-veto probability.

This is not a Geant4 energy-deposition calculation. It is a detector-response
scaffold and regression target for the future detector-only Geant4 migration.

## Geant4 Detector-Only Prototype

`geant4_app/src/detector_only_demo.cc` is a standalone detector-only Geant4
prototype. It reads the staged `phase_space.csv`, starts photons at a local
detector entrance plane, builds a minimal 8-layer Bi 20x20 TES pixel stack plus
side/bottom BGO, and writes the same `hits.csv` / `event_summary.csv` contract
as the Python detector backend.

This prototype uses Geant4 10.2 `G4EmStandardPhysics` raw energy deposition. It
is useful for proving the source reader, geometry scaffold, sensitive detector,
and output schema. It is not yet a validated TES/BGO flight mass model or
electronics response.

## Geant4 Optics Scaffolds

`geant4_app/src/laue_multiring_table_demo.cc` is now the recommended Laue
Geant4 optics scaffold. It places a five-ring Ge(111) lens and reads
energy/angle/material-dependent diffraction probabilities from
`data/laue/Ge111_480_550keV_darwin_mosaic_table.csv`.

The table is generated by
`external_baseline/laue_raytrace_py/build_mosaic_darwin_table.py` from the
Zachariasen/Darwin mosaic-crystal formula. The formula implementation is
benchmarked against Barriere et al. 2009 Cu/Au measurements in
`runs/laue_darwin_benchmark`, and against the direct Ge(111) 200-500 keV APS
measurement summary in Kohnle 1998 in
`runs/laue_kohnle1998_ge111_benchmark`. The older one-ring
constant-probability demo remains only as a regression scaffold.

`geant4_app/src/channel_4ring_effective_demo.cc` implements a four-ring channel
effective boundary process. It places four rings of channel tiles, samples the
ring-calibrated survival probabilities, and points surviving photons to the
12 m focal plane with the same benchmark spot width as the Python calibrated
model. It is not a wall-by-wall curved-channel geometry; it is the Geant4-side
effective optics scaffold for downstream detector handoff.

`geant4_app/src/channel_4ring_multibounce_demo.cc` is now the recommended
Channel Geant4 scaffold. It uses the four 511-CAM channel rings from
`data/channel/cam511_channel_rings.csv`, records a sequence of per-bounce
`BOUNCE` rows, samples `ABSORB`/`LEAK` from the W/Si 511 keV reflectivity table,
and writes surviving photons to the 12 m focal plane as standard
`phase_space.csv`.

The default `theta-policy=ring_calibrated` mode is a benchmark reproduction
mode: the local grazing angle and bounce count are the calibrated effective
values that reproduce the paper-level channel transmissivity target of about
80%. It is useful for Geant4 event bookkeeping, per-bounce provenance, detector
handoff, and regression tests, but it should not be described as an independent
wall-by-wall recovery of the original IDL ray trace.

`analysis/audit_channel_physics_confidence.py` is the current confidence audit.
It estimates the 511 keV W/Si critical angle at about `1.64e-4 rad`, so the
calibrated theta values have a plausible local-angle scale. The same audit also
shows that accumulating the public ring bend angles as `2Ntheta` would require
about 6-13 bounces, not the current calibrated 1/2/2/3 bookkeeping. The current
focal spot D90 is likewise imposed by a configured Gaussian target rather than
being produced by wall-by-wall channel geometry. Therefore the headline
performance remains a calibrated benchmark reproduction, not a first-principles
prediction.

The same audit now also decomposes a paper-formula pressure test into `R^N`,
`R^N * open_fraction`, and `R^N * open_fraction * Si_length_transmission`.
This is a useful improvement because it makes the absorption/open-area ambiguity
explicit instead of hiding it inside one tuned transmissivity number.

The diagnostic `theta-policy=paper_bend` plus
`open-fraction-policy=paper_once` mode is deliberately stricter. It derives the
number of small-angle bounces from the tabulated ring bend angles and applies
the Si/W open fraction as a separate one-time acceptance. With the current
W/Si table, this mode gives about 56% transmissivity rather than 80%. That
mismatch is a useful audit result: it shows that the remaining uncertainty is
the original channel path model and open-area accounting, not a need to modify
Geant4 source code.

`channel_4ring_multibounce_demo` also has
`path-absorption-policy=si_length`. This stricter diagnostic applies
`exp(-mu_Si * length_cm)` as a path-loss term split over the bounce segments and
records losses as `si_path_absorption` rows in `optics_history.csv`. It is not
the default model because the public 511-CAM paper does not expose the exact
IDL path/open-area bookkeeping; it is a conservative pressure test that keeps
that ambiguity visible.

## Current Laue Baseline

The current Laue baseline is a benchmarked table-driven mosaic-crystal model:

- Bragg geometry is computed from `n lambda = 2 d sin(theta_B)`.
- Ring radius and focal length are checked with `F = r / tan(2 theta_B)`.
- The recommended Ge(111) table covers 480, 500, 511, 530, and 550 keV.
- Mosaic diffraction uses the Zachariasen/Darwin formula with 30 arcsec
  mosaicity, 5 um crystallite thickness, and per-energy optimum crystal
  thickness.
- Output includes diffracted `phase_space.csv`, transmitted `transmitted_space.csv`,
  full `optics_history.csv`, per-ring summaries, and WRL visualization.

Remaining limitation: the Kohnle 1998 check validates the direct Ge(111)
few-arcsecond, 3-mm crystal endpoint near 500 keV. The present lens table uses
30 arcsec mosaicity and optimized thickness near 10 mm, so a digitized
material-specific figure/table for that exact regime would still be needed for
publication-level uncertainty bounds.
