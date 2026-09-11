# Phrasing notes for §3.4 (mission-time trajectory fold)

Short diction patterns from COSI and related balloon/MeV instruments, collected to support the EA English draft. Paraphrases are free for reuse; do not copy long verbatim blocks into the paper without citation.

## 1. COSI (Compton Spectrometer and Imager)

**Primary anchors**

- Gallego et al., *Bottom-up Background Simulations of the 2016 COSI Balloon Flight*, ApJ 986, 116 (2025); arXiv:2503.02493.
- Kierans et al., *The 2016 Super Pressure Balloon flight of the Compton Spectrometer and Imager*, arXiv:1701.05558.
- Tomsick et al., COSI SMEX overview, arXiv:2308.12362.

**Usable phrase patterns (paraphrased)**

| Theme | Pattern |
|-------|---------|
| Background dominance | “MeV observations are background-dominated; atmospheric and activation components must be modelled as functions of the flight environment.” |
| Drivers of rate | “Background rates vary with altitude (atmospheric depth), geomagnetic cutoff / latitude, and solar activity.” |
| Altitude variation | “Nominal float altitude … with day–night altitude excursions that map to a substantial range in residual atmospheric depth.” (COSI 2016: ~33 km with drops; depth ~5–30 g cm⁻²) |
| PARMA/EXPACS | “Incident cosmic-ray and secondary fluxes are generated with PARMA/EXPACS as functions of altitude, longitude, latitude, solar activity, and cutoff.” |
| Time-dependent scaling | “Time dependence is included via light curves obtained by integrating model spectra over energy in successive time bins of the flight.” |
| Activation build-up | “Activation is accumulated over the full flight; comparison windows may start after the instrument configuration stabilizes.” |
| Validation language | “Agreement with data at the 10–20% level after accounting for residual detector-response systematics.” |
| Scope honesty | “Remaining at high altitude is preferable because atmospheric background decreases with altitude and the cosmic signal is less attenuated.” |

**Caution:** COSI papers typically **re-simulate or re-scale along a real/measured flight** (hourly altitude/lat/lon), not a purely synthetic 20 d sinusoid. Our wording should prefer *reference trajectory* / *controlled reference profile* rather than *flight forecast*.

## 2. Related balloon / atmospheric MeV context

| Project / topic | Phrase pattern |
|-----------------|----------------|
| Atmospheric MeV background (classic) | “The atmospheric MeV continuum and albedo fields set a strong, altitude-dependent floor for soft gamma-ray instruments.” (cf. Schönfelder et al. 1977 lineage) |
| INTEGRAL/SPI–style ambient field | “Geomagnetic cutoff and atmospheric overburden modulate the local particle environment that drives both prompt deposits and radioactivation.” |
| NCT → COSI pathfinder narrative | “Balloon campaigns serve as technology pathfinders and as empirical anchors for background models later used in mission design.” |

## 3. Diction for *our* analytic fold (project-specific)

| Need | Preferred phrasing |
|------|--------------------|
| Motivation | “Day-scale flights sample a continuum of depth and cutoff states; linear extrapolation of a single snapshot rate is not a substitute for a trajectory fold.” |
| Synthetic track | “We adopt a synthetic 20 d reference trajectory that encodes the amplitude of float-altitude and geomagnetic modulation expected for a mid-latitude zero-pressure-class float, not telemetry from a specific launch.” |
| Altitude | “Altitude enters through residual atmospheric depth, which drives atmospheric particle spectra and 511 keV line-of-sight transmission.” |
| Lat/lon | “Latitude and longitude enter as a *reference* geomagnetic/geographic modulation of cutoff rigidity; they are not a visibility or pointing schedule.” |
| Old scalar | “A single depth–cutoff scalar that jointly rescales prompt background and activation production is a historical proxy; multi-point transport rejects it for the prompt band.” |
| Source–response | “Prompt selected rates are predicted by folding live PARMA particle-family fluxes through detector response coefficients fixed at the day-15 reference state.” |
| Validation metric | “We report $Q=(R^{\mathrm{MC}}/R^{\mathrm{REF}})/S^{\mathrm{pred}}$ at four frozen trajectory states.” |
| Performance curve | “Cumulative counting significance is obtained by integrating the trajectory-folded selected signal and background; it is a diagnostic selected-rate metric under the reference model.” |
| Boundary | “This does not close narrow-window W2 transport validation, activation-production residuals, or delayed selected-rate history at the same points.” |

## 4. Citation hooks (bib keys if added later)

- COSI 2016 flight: Kierans et al. 2017 (arXiv:1701.05558)
- COSI background MC: Gallego et al. 2025 (ApJ / arXiv:2503.02493)
- PARMA/EXPACS: Sato 2016 (PLOS ONE)
- MEGAlib: Zoglauer et al. 2006

## 5. What *not* to copy from COSI diction

- Do not claim “10–20% agreement with flight data” for our work (we have MC-vs-analytic multi-point tests, not COSI flight residuals).
- Do not imply hourly full-flight re-simulation; we use **analytic fold + multi-point Cosima checks**.
- Do not call the synthetic track a “measured balloon flight profile.”
