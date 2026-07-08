# Strict NIM A Review — Balloon-borne 511 keV TES Laue-lens Manuscript

**Review mode:** senior NIM A reviewer + PhD supervisor  
**Manuscript reviewed:** `balloon511_nima_draft_en.md` and `balloon511_nima_draft_en.pdf`  
**Scope:** abstract/introduction rewrite, methods/simulation critique, figure/table review, publication-risk assessment, reference/context gaps, and prioritized revision plan.

> Note: The figure review is based on the figures as embedded in the PDF layout. If separate high-resolution PNG/vector figures exist, they should still be inspected before final submission.

---

## 1. Executive verdict

**Decision: not ready for submission; reject-and-resubmit level revision.** The instrument concept is appropriate for *Nuclear Instruments and Methods in Physics Research Section A*, and the idea of transporting delayed decays from recorded radionuclide-production coordinates could become a useful methodological contribution. However, the current headline sensitivity cannot yet be defended as a balloon-flight performance prediction. The calculation uses a synthetic trajectory and effectively continuous on-source exposure; atmospheric transmission is not tied to the actual target zenith angle; major prompt-background sources from the Laue lens support, optical bench, gondola and services are omitted; TES response, CsI veto timing, and multi-hit reconstruction remain idealized; delayed-activation convergence is not demonstrated at the final selected-rate level; and the significance calculation contains no background nuisance parameters. Several numerical/statistical inconsistencies further weaken credibility. A strict reviewer would likely recommend rejection in the present form rather than routine major revision.

---

## 2. Major concerns

### C1. Critical — Observation geometry, atmosphere, and on-source exposure

**Location:** Abstract; Sections 5, 8–10.

**Rationale.** The quoted 20-d sensitivity is based on a synthetic trajectory with only small sinusoidal latitude/longitude excursions and no target visibility or pointing history. The entrance direction is stated to be 45° from zenith, but the adopted transmission reference, \(T_{15}=0.739\), behaves like a vertical-column normalization rather than a slant-column target transmission.

Using the manuscript's own vertical transmission as an illustration,

\[
T(45^\circ) \simeq \exp\left[\frac{\ln(0.739)}{\cos 45^\circ}\right] \simeq 0.652,
\]

not 0.739. Near the horizon the difference would be much larger, and the plane-parallel approximation itself would eventually fail. Thus the reported 2.51 d should not be called an elapsed detection time. At most, it is the required net exposure under the adopted synthetic background and transmission history.

**Required fix.** Use a named launch site and representative/measured balloon trajectory; fold the target ephemeris, elevation limits, Earth occultation, Sun/Moon constraints where relevant, calibration intervals, repointing losses, detector dead time, and observing efficiency; compute atmospheric transmission along the target line of sight; report both elapsed flight time and net on-source live exposure. Until this is done, replace “mission sensitivity” with “reference-exposure statistical sensitivity.”

---

### C2. Critical — The hard energy window does not represent most realistic 511 keV source profiles

**Location:** Abstract; Sections 2, 5, 7, 9 and Discussion.

**Rationale.** The window 510.58–511.42 keV is exactly \(\pm3\sigma\) for a single Gaussian detector response with \(\sigma=0.14\) keV. It retains 99.73% of an intrinsically monochromatic line, but the astrophysical annihilation line is not generally a delta function. SPI analyses have reported narrow and broad components with FWHM values of roughly 1.3 keV and 5.4 keV. Under simple Gaussian convolution with the stated detector response, the fraction retained inside the current window is approximately:

| Intrinsic line FWHM | Fraction retained in 510.58–511.42 keV |
|---:|---:|
| 0 keV | 99.7% |
| 1.3 keV | 53.9% |
| 2.43 keV | 31.3% |
| 5.4 keV | 14.5% |

Therefore the quoted threshold applies only to an unresolved, accurately centred line. It is not a generic sensitivity to Galactic 511 keV emission, the broad component, or many compact pair-plasma scenarios.

For multi-pixel events, if \(\sigma=0.14\) keV is a per-pixel independent resolution, the summed event resolution scales approximately as \(\sqrt n\). The present window would retain about 96.6% of two-pixel events but only about 77.9% of six-pixel events. The manuscript does not state whether smearing is applied per pixel or to the reconstructed event sum.

**Required fix.** Provide sensitivities for at least four source models: unresolved line, 1.3 keV FWHM, 2–3 keV FWHM, and 5.4 keV FWHM. Include plausible centroid offsets or velocity shifts. Convolve each line model with \(A_{\rm eff}(E)\) and multiplicity-dependent detector response. Either optimize the analysis window for each model or use a spectral likelihood. State explicitly that the current headline threshold is an unresolved-line sensitivity.

---

### C3. Critical — The physical background budget is incomplete

**Location:** Sections 3–6, 9.4 and Discussion.

**Rationale.** The primary background result excludes prompt self-background of the Laue-lens assembly and omits explicit lens supports. The manuscript itself acknowledges that upstream prompt self-background is not included and that support hardware remains a systematic.

More importantly, the mass model is mainly a detector/cryostat proxy. A 10 m balloon telescope will include a substantial optical bench or deployable boom, lens frame, pointing system, electronics, batteries, telemetry hardware, pressure vessels, suspension hardware, cryogenic auxiliaries and gondola. These components can produce scattered 511 keV photons, neutron-capture lines, secondary positrons, and activation products. A detector-only proxy cannot support a full flight-background claim.

The external photon model also appears to omit Galactic diffuse continuum, extragalactic diffuse gamma-ray background, diffuse Galactic 511 keV emission entering the aperture, source-region continuum, and Earth occultation of celestial components. A compact-source search toward the inner Galaxy must treat diffuse 511 keV sky emission as an astrophysical foreground, not merely an instrumental background.

**Required fix.** Either extend the model to a credible full-payload mass model and include all prompt and delayed contributions, or retitle/reframe the paper as a “detector/cryostat subassembly background study” with no flight-performance claim.

---

### C4. Critical — EXPACS/PARMA use and source normalization are not reproducible

**Location:** Section 6.1; Eqs. (1), (16), (17).

**Rationale.** The manuscript uses angular differential fields but only cites the PARMA3.0/EXPACS 2015 paper. The zenith-angle extension is PARMA4.0 and should be cited explicitly: T. Sato, *PLOS ONE* 11 (2016) e0160390, DOI 10.1371/journal.pone.0160390.

Equation (1),

\[
r_{\mathrm{event},j}=\left(\sum_i \mathcal T_{ij}\right)^{-1},
\]

is too opaque to audit. It does not define whether \(\mathcal T_{ij}\) is time, geometric exposure, or integrated source weight; whether EXPACS returns intensity, planar flux, or scalar flux in the adopted usage; how the projected-area factor \(|\hat n\cdot\hat\Omega|\) is handled; how the spherical far-field source maps differential intensity to generated primaries; how energy and solid-angle bin integrals are calculated; how replicated non-photon samples are de-weighted; or whether upward/downward source surfaces can double count crossings.

The prompt time-scaling law,

\[
f_p = \exp[(X-X_0)/(30\,\mathrm{g\,cm^{-2}})](11/R_c)^{0.2},
\]

and the linear cutoff-rigidity expression appear empirical and have no reference. A single scalar cannot generally describe photons, neutrons, protons, muons, and activation production.

A sub-keV detector window also requires demonstrating that the source spectrum and interpolation preserve, or correctly omit, atmospheric annihilation structure near 511 keV.

**Required fix.** Supply the complete source-weight equation with units; archive EXPACS inputs/outputs and interpolation code; validate normalization with a simple analytical geometry; evaluate EXPACS/PARMA at representative trajectory states by species, energy and angle; show a finely binned external photon spectrum around 511 keV; add Galactic and extragalactic diffuse photon fields separately.

---

### C5. Critical — TES response, timing, and CsI veto are assumptions rather than detector models

**Location:** Sections 4 and 7.

**Rationale.** The detector response is represented by a Gaussian with \(\sigma=0.14\) keV, equivalent to 330 eV FWHM, but no calibration, prototype result, thermal model, or response matrix is provided. The 511-CAM concept projected an assembled-event resolution of about 390 eV FWHM and emphasized the difference between pixel and assembled-event resolution.

The current model does not address multiplicity-dependent energy resolution, gain drift, absolute energy-scale stability, low-energy tails, incomplete thermalization, saturation at 511 keV, non-linearity, pile-up, pulse-shape discrimination, thermal/electrical cross-talk, pixel thresholds, channel failures, finite position uncertainty, or inactive gaps.

The \(1\,\mu\mathrm{s}\) value also conflates at least two different time scales: TES event association and fast shield anticoincidence. A microcalorimeter pulse-processing window need not equal the shield veto gate.

The CsI shield is treated as an ideal deposited-energy counter with a sharp 50 keV threshold. Real performance depends on light yield, optical transport, light-collection nonuniformity, scintillation decay time, photosensor noise, energy resolution, gaps, discriminator efficiency and threshold stability.

**Required fix.** Separate: physical Geant4 energy deposits; TES channel response and event reconstruction; CsI optical/electronic response; TES coincidence association; shield veto gate and dead time. Provide a calibrated detector-effects model or a sensitivity envelope over realistic detector response parameters.

---

### C6. Critical — Activation statistics and validation are insufficient

**Location:** Sections 6.2, 8, 9.2–9.4.

**Rationale.** The delayed transport contains \(10^6\) parent decays, while the selected delayed rate is \(2.5752\times10^{-3}\,\mathrm{s^{-1}}\) from a total activity of 85.4492 Bq. This corresponds to an average selected probability

\[
\epsilon_{\rm delayed}\simeq \frac{2.5752\times10^{-3}}{85.4492}=3.01\times10^{-5}.
\]

Only about 30 selected events are expected in the delayed Monte Carlo, giving roughly 18% Poisson relative uncertainty before weighted-event and source-sampling uncertainties. Reporting the delayed rate as 0.00257520 s\(^{-1}\) is statistically unjustified. The source-card inventory checks demonstrate bookkeeping closure, not convergence of the selected rate.

Further vulnerabilities include one value of \(M=50000\), one random seed, no downstream comparison with radial or volume-averaged approximation, no pre-flight inventory/ascent/cooldown history, incomplete metastable-state treatment, no confirmation of full correlated decay cascades/internal conversion/positron transport, no physics-list or nuclear-model variation, no validation of the custom production-position hook against an independent inventory, and no selected 511 keV decomposition by isotope, material, and production particle.

The dominance of \(^{128}\)I in an iodine-containing shield is an engineering result that should trigger a CsI-versus-alternative-shield trade study.

**Required fix.** Increase delayed statistics until selected-rate uncertainty is acceptably small; run several \(M\) values and multiple independent seeds; report weighted statistical uncertainties; compare production-position sampling with volume/radial approximations after all selections; include realistic exposure history and initial conditions; tabulate leading selected isotopes/materials; validate dominant reaction channels or cite measurements where possible.

---

### C7. Major — The Compton/FoV reconstruction is not a validated event reconstruction

**Location:** Section 7 and Figure 9.

**Rationale.** The two-hit Compton relation is physically correct only under the stated ordering and full-energy-containment assumptions. For higher multiplicities, the residual

\[
Q=\sum_i\left(\cos\theta_{C,i}-\hat{\mathbf u}_{i-1,i}\cdot\hat{\mathbf u}_{i,i+1}\right)^2
\]

has no uncertainty weighting, no Doppler-broadening term, no Klein–Nishina or interaction-probability prior, no energy/position covariance, and no clearly defined index range. Calling it the “usual” residual is insufficient.

Most importantly, events with no valid sequence are labelled reconstruction rejects but retained in the baseline. This makes “Compton/FoV-pass rate” ambiguous: some reconstruction failures are counted in the baseline. For a focused telescope, the known lens phase space is stronger information than asking only whether a cone intersects the entire entrance disk.

**Required fix.** Define a reproducible baseline category: single-site, valid reconstructed multi-site, and unreconstructed. Do not call unreconstructed events FoV-passing. Validate against Revan/Mimrec or an independent implementation. Use uncertainty-weighted ARM or a source-direction likelihood. Report response/background separately by multiplicity and provide a truth-based confusion matrix.

---

### C8. Critical — Statistical significance ignores dominant background uncertainty

**Location:** Section 8 and all sensitivity claims.

**Rationale.** \(S/\sqrt B\) is acceptable only as a diagnostic in the high-count, perfectly known-background limit. It is not sufficient for a flight sensitivity claim at 511 keV, where background includes a strong line-like component and must be estimated from off-source data, control energy bands, temporal templates, or nuisance-constrained models.

From the manuscript's mission-mean rates, 20-d counts are approximately

\[
N_s = 0.00117748\times20\times86400 \simeq 2035,
\]

\[
N_b = 0.0393546\times20\times86400 \simeq 68005,
\]

so \(S/B\simeq2.99\%\). Adding only a 1% Gaussian background-normalization uncertainty through

\[
Z_{\rm approx}=\frac{N_s}{\sqrt{N_b+(\epsilon_bN_b)^2}}
\]

reduces \(Z\) from about 7.8 to about 2.8. This shows that the systematic background strategy is central, not a minor refinement.

**Required fix.** Define how the in-flight background will be measured; introduce prompt and delayed normalization/shape nuisance parameters; include atmospheric-transmission and effective-area uncertainties; report median 3σ and 5σ discovery sensitivities and upper limits; report sensitivity versus assumed background systematic floor; include trials if several positions, line centroids, or time windows are searched.

---

### C9. Major — Geant4/MEGAlib configuration is not adequately documented

**Location:** Methods.

**Rationale.** The paper does not state the minimum information needed to reproduce an activation/background simulation: Geant4 version/patch; MEGAlib/Cosima version or commit; physics list and modifications; electromagnetic model and low-energy settings; neutron high-precision treatment and data libraries; hadronic cascade model and transition energies; radioactive-decay data version; atomic de-excitation, fluorescence, Auger and internal-conversion settings; range cuts; step limits; isotope-production storage thresholds; geometry overlap checks; random-number engine and seed policy.

**Required fix.** Add a compact simulation-configuration table and archive executable input cards and relevant custom-code patches. Add the modern Geant4 reference: J. Allison et al., *Nucl. Instrum. Methods Phys. Res. A* 835 (2016) 186–225, DOI 10.1016/j.nima.2016.06.125.

---

### C10. Critical for credibility — Numerical inconsistencies, excessive precision, and internal/debug language

**Location:** Abstract; Sections 3, 8–10; Tables 1, 2, 7; PDF layout.

**Clear numerical problems.**

1. The manuscript states that the 20-d background is about \(1.09\times10^5\) counts. The mission-mean rate gives

   \[
   0.0393546\times20\times86400=6.80\times10^4
   \]

   counts. The quoted \(Z=7.80\) is consistent with \(6.80\times10^4\), not \(1.09\times10^5\).

2. Zero selected events from 20,000 decays of a 0.425674 Bq source give a one-sided 95% upper selected rate

   \[
   R_{95}=\frac{-\ln(0.05)}{20000/0.425674}=6.38\times10^{-5}\,\mathrm{s^{-1}},
   \]

   not \(1.25\times10^{-4}\,\mathrm{s^{-1}}\). The stated number corresponds to roughly 99.7% confidence, not 95%.

3. \(S/F_0\) has dimensions of area. Report it as a selected effective area, \(A_{\rm sel}=11.86\,\mathrm{cm^2}\), rather than “cps/(ph cm\(^{-2}\) s\(^{-1}\)).”

4. Flux thresholds should include photons: \(\mathrm{ph\,cm^{-2}\,s^{-1}}\), not merely \(\mathrm{cm^{-2}\,s^{-1}}\).

5. The Markdown expression `\inW_{511}` should be `\in W_{511}`.

6. Most numbers are reported with five to eight significant figures despite much larger MC and model uncertainties. Use two to three significant figures plus statistical/systematic uncertainties.

**Internal language to remove.** Examples: “current sampled-position chain,” “full-statistics,” “seed 260613,” “PASS,” “source text flux closure,” “smoke test,” “side component closed,” “manuscript-facing compression,” “archived spatial boundary calculations,” and “headline hard-window result.” Seeds and run-level closure checks belong in a reproducibility supplement.

---

## 3. Revised Abstract

> Editorial convention: the revision below defines the source flux at the top of the atmosphere. Verify this against the actual normalization code. If the code uses payload-altitude flux, the convention and quoted thresholds must be changed consistently.

**Abstract**

The 511 keV electron–positron annihilation line is an important diagnostic of Galactic positron sources and annihilation environments. Pointed observations from balloon altitude are, however, limited by atmospheric gamma rays, particle-induced instrumental background, and delayed radioactivation. We present a detector-coupled Monte Carlo estimate for a balloon-borne telescope comprising a 10 m focal-length Ge(111) Laue lens and a transition-edge-sensor microcalorimeter focal plane. Focused source photons, prompt atmospheric particles and photons, and delayed radioactive decays are transported through a common detector/cryostat mass model and subjected to the same event definition, including a CsI anticoincidence selection, a Compton/field-of-view consistency test, and a 510.58–511.42 keV energy window. Delayed decays are initiated from sampled radionuclide-production coordinates recorded during the activation simulation. For a monochromatic point source with a reference top-of-atmosphere flux of \(10^{-4}\,\mathrm{ph\,cm^{-2}\,s^{-1}}\), the selected day-15 signal and background rates are \(1.19\times10^{-3}\,\mathrm{s^{-1}}\) and \(3.92\times10^{-2}\,\mathrm{s^{-1}}\), respectively; prompt atmospheric events account for 93.4% of the selected background. Under the adopted synthetic 20-d trajectory and continuous on-source exposure, the statistical counting metric gives \(Z=7.80\), a 3σ exposure of 2.51 d, and a 20-d 3σ flux threshold of \(3.85\times10^{-5}\,\mathrm{ph\,cm^{-2}\,s^{-1}}\). These values are statistical sensitivities for an unresolved line and the present reference mass model; they do not yet include a full-payload prompt-background model or systematic uncertainties in the atmospheric field, detector response, activation calculation, and background estimation.

---

## 4. Revised Introduction/background

The 511 keV line is produced when low-energy positrons annihilate with electrons. Direct annihilation and singlet positronium, para-positronium, predominantly produce two photons near the electron rest-mass energy, whereas triplet positronium, ortho-positronium, produces a three-photon continuum below 511 keV. The line intensity, centroid, width, and associated positronium continuum therefore constrain the positron production rate, propagation history, thermalization, and physical conditions of the annihilation medium [Prantzos2011; Jean2006].

Measurements with OSSE/CGRO and INTEGRAL/SPI established that Galactic annihilation emission contains a bright bulge component and a fainter disk, although the detailed morphology depends on the sky and instrumental-background models. Recent analyses of the long SPI data set continue to refine the central, bulge, and disk components, while the 2016 COSI balloon flight provided an independent Compton-imaging detection of the Galactic signal [Siegert2016AA; Yoneda2025; Kierans2020; Siegert2020COSI]. The annihilation spectrum is not generally an unresolved line: SPI measurements have been described by a narrow component with a FWHM of approximately 1.3 keV and a broader component of approximately 5.4 keV, and spatially resolved studies have searched for centroid and width variations across the inner Galaxy [Jean2006; Siegert2019Kinematics].

The large-scale morphology does not by itself determine whether part of the emission arises from compact objects or unresolved source populations. Searches with INTEGRAL have generally found no persistent narrow 511 keV point source and have placed limits of order \(10^{-4}\,\mathrm{ph\,cm^{-2}\,s^{-1}}\), depending on position, exposure, and assumed line width [DeCesare2011; Tsygankov2010]. Transient annihilation signatures remain of interest, but individual claims require caution. For example, an annihilation-related interpretation was proposed for the 2015 outburst of V404 Cygni, whereas an independent analysis of the early outburst found no firm narrow-line detection and reported a 2σ upper limit of \(2\times10^{-4}\,\mathrm{ph\,cm^{-2}\,s^{-1}}\) [Siegert2016V404; Roques2015].

Wide-field Compton telescopes are required to map the diffuse annihilation sky. A pointed focusing telescope addresses a complementary measurement: testing a known direction for a compact or moderately extended line component and obtaining high-resolution spectroscopy of a detected feature. A Laue lens concentrates photons diffracted in transmission by mosaic crystals onto a small focal plane. This can reduce the active detector volume required for a given collecting area and thereby reduce some classes of instrumental background. The gain is obtained at the cost of a narrow field of view, target-dependent atmospheric transmission, demanding alignment and pointing requirements, and sensitivity to the mass and activation of the lens support and optical structure.

The 511-CAM concept combines such concentrating optics with stacked transition-edge-sensor microcalorimeter arrays [Shirazi2023]. TES calorimeters can, in principle, provide energy resolution of a few hundred electronvolts at 511 keV, substantially narrower than conventional MeV semiconductor spectroscopy. The published concept projects an assembled-event resolution of approximately 390 eV FWHM. This resolution corresponds to a velocity scale of a few hundred kilometres per second, but astrophysical velocity measurements also require stable absolute energy calibration, control of gain drift and line-response tails, and sufficient source counts. Multi-pixel events can additionally be tested against Compton kinematics and the known source direction, provided that the energy, position, and timing response is realistically represented.

Background control is the central instrumentation problem. Balloon-borne gamma-ray payloads are exposed to atmospheric photons and neutrons, primary and secondary charged particles, secondary radiation generated in the payload, and radioactive isotopes produced in detector, shield, cryostat, optical and gondola materials. The challenge is particularly acute at 511 keV because atmospheric and payload-generated positrons can produce annihilation photons at the same energy as the source signal. A credible calculation therefore requires a normalized directional radiation environment, a sufficiently complete mass model, prompt and delayed transport, a detector-effects model, and validation against measurements or benchmark calculations. Recent COSI studies illustrate the required level of validation: detailed payload and detector-response simulations were compared with calibration or balloon data, including activation lines and anticoincidence response [Gallego2025Balloon; Beechert2022; Ciabattoni2025ACS].

In this work, we evaluate a reference balloon-borne configuration consisting of a single-energy Ge(111) Laue-lens ring, a stacked Ta-absorber TES focal plane, passive shielding, and a segmented CsI anticoincidence system. The simulation couples the focused optical phase space to a detector/cryostat mass model and treats prompt atmospheric events and radioactive decays with common detector-level selections. A specific methodological element is the construction of delayed sources from sampled radionuclide-production coordinates rather than from a purely volume-averaged activity distribution. The primary outputs are selected signal and background rates and a statistical unresolved-line sensitivity for a defined reference exposure. The result is not intended to constitute a final flight-performance prediction until the full payload mass, target-dependent atmosphere and duty cycle, detector-effects response, event reconstruction, and background systematic uncertainties have been validated.

---

## 5. Methods/simulation critique without full rewrite

### 5.1 Must fix before submission

1. **Source-flux convention and event weights.** Define whether \(F_0\) is above the atmosphere, at balloon altitude, at the lens plane, or at the detector. Give the full conversion from differential intensity to generated-event weight, including energy, solid angle, area, and projected-area terms. For weighted samples, report \(R_{\rm sel}=\sum w_e\) and \(\sigma^2_{\rm MC}=\sum w_e^2\). Validate with an analytical geometry.

2. **Prompt atmospheric model.** Replace the single empirical mission scaling with species-, energy-, and angle-dependent EXPACS/PARMA evaluations or a justified interpolation grid. Add PARMA4.0. Show the photon spectrum around 511 keV at fine binning and include Galactic/extragalactic diffuse components.

3. **Target-specific mission fold.** Replace the sinusoidal synthetic trajectory with an actual or representative flight profile and target pointing schedule. Atmosphere, source transmission, diffuse sky, and Earth occultation must be evaluated in common time/attitude bins.

4. **Geometry and mass closure.** Provide a component-level mass table: dimensions, material, density, mass, position, and uncertainty. Quantify omitted mass and run bounding geometries.

5. **Full simulation configuration.** Add software versions, physics lists, EM/hadronic settings, decay data, cuts, step limits, isotope thresholds, overlap checks, and seed policy.

6. **Lens response and normalization.** Report \(A_{\rm eff}(E)\), diffraction efficiency, PSF, encircled-energy curve, off-axis response, energy bandpass, alignment/mosaic/tile-placement tolerances, and atmospheric/detector efficiencies separately. Clarify whether aperture gates are double-counted.

7. **TES detector-effects engine.** State whether Gaussian smearing is per pixel or per event. Include multiplicity-dependent resolution, thresholds, saturation, non-linearity, tails, cross-talk, pile-up and dead time, or provide a response uncertainty envelope.

8. **Veto timing and live factor.** Derive \(L=\exp[-(R_p+R_d)\tau]\) from the actual veto logic. A symmetric no-trigger condition over \(\pm\tau\) gives \(\exp(-2R\tau)\); a one-sided gate gives \(\exp(-R\tau)\). \(R\) should be the relevant above-threshold shield trigger rate.

9. **Activation history and decay physics.** Use \(dN_k/dt=P_k(t)-\lambda_kN_k(t)\) with stated initial inventory, ascent, float, and cooldown history. Explain how correlated cascades, positrons, internal conversion, and atomic relaxation are preserved.

10. **Position-sampling convergence.** Demonstrate convergence of final selected spectra/rates, not just total source activity. Use several \(M\) values and several random seeds.

11. **Reconstruction validation.** Define event building, ordering, sequence quality and aperture consistency mathematically. Include energy/position uncertainties and benchmark against Revan/Mimrec or a second implementation.

12. **Sensitivity likelihood and uncertainty budget.** Build a source-plus-background likelihood with prompt/delayed nuisance parameters, energy-scale uncertainty, atmospheric transmission uncertainty, and effective-area uncertainty. Keep \(S/\sqrt B\) only as a diagnostic.

### 5.2 Formula-level corrections

- `E_{\rm TES}^{(c)}\inW_{511}` → `E_{\rm TES}^{(c)}\in W_{511}`.
- Report \(S/F_0\) in cm\(^2\), as selected effective area.
- Use \(P_k\) rather than \(R_k\) for radionuclide production rate.
- State time units explicitly in all exponentials.
- State assumptions behind the two-hit Compton equation.
- Define the index range and incoming direction treatment in the multi-hit residual.
- Add weighted MC variance, not just source-card closure.
- Correct zero-event Poisson interval.

### 5.3 Should improve

- Show selected prompt, delayed, and signal spectra over 450–570 keV with a 511 keV inset.
- Decompose selected prompt background by incident species and physical origin.
- Decompose selected delayed background by isotope, material, production particle, decay mode, and rate.
- Scan CsI threshold, veto gate, W sleeve dimensions, passive shielding, TES resolution, multiplicity, and energy-window width.
- Compare CsI with alternative shield materials, because iodine activation dominates.
- Add simple benchmarks: 511 keV attenuation through window layers, bare-array efficiency, analytical crossing rates, and known radioactive-source spectra.
- Separate optimization samples from final sensitivity samples.

### 5.4 Optional clarification

- Define all coordinate frames in one schematic.
- Rename “exact-position” to “production-position-sampled delayed source.”
- Move random seeds and source-card serialization checks to an appendix/repository.
- Consider a more precise title: **Detector-coupled Monte Carlo estimate of background and unresolved-line sensitivity for a balloon-borne 511 keV Laue-lens/TES telescope.**

---

## 6. Figure and table review

### Global PDF layout

The PDF is not publication-ready. Tables 4–7 appear after the references, which is unacceptable. Table 2 is nearly unreadable because of its width and density. Several pages have excessive blank space, captions are too long, and visible hyperlink boxes remain. Use controlled float placement, vector figures, shorter captions, journal-compatible hyperlink styling, and ensure all tables appear before references.

### Figure 1 — Workflow

**Keep, but redraw.** The logic is useful, but the figure is too sparse and resembles an internal flowchart. Use consistent box sizes, arrows, typography, and explicit distinction between signal, prompt background, and activation paths. Add final outputs: response, selected spectra, likelihood.

### Tables 1 and 2 — Requirements and workflow

**Remove from main paper or merge into one short table.** These are internal traceability/project-management tables rather than scientific results. Table 2 is especially dense and unreadable.

### Figure 2 — Mass model

**Must be redrawn.** Labels are too small; the panel description is unclear; the geometry looks like a plotting-script diagnostic rather than an engineering schematic; dimensions and materials are absent; transparency makes boundaries hard to distinguish. Replace with a vector cross-section containing numbered components, dimensions, beam axis, aperture, shield thicknesses, TES layer spacing, and a mass legend.

### Table 3 — Detector parameters

**Keep and expand.** Add pixel pitch, active area, layer spacing, total absorber mass, CsI dimensions/mass, aperture diameter, W sleeve dimensions, entrance-window areal densities, response FWHM, timing-model definitions, and uncertainties.

### Figures 3 and 4 — Laue transport and focal spot

**Merge and replace the emphasis.** Figure 3 is mainly a conceptual/debug fan plot; Figure 4 is more useful but should use \(x_{\rm fp}\) and \(y_{\rm fp}\). A publication figure should include lens geometry, \(A_{\rm eff}(E)\), PSF/encircled energy, accepted focal-plane density with \(r_{50}\)/\(r_{90}\), aperture, sample size, and off-axis response. Replace “data-constrained” with “simulation-derived.”

### Figure 5 — EXPACS/PARMA fluxes

**Redraw.** Legend, bin labels, and numerical annotations are too small. Clarify whether values are differential intensity or bin-integrated planar flux and include complete units. Add a dedicated inset around 511 keV for photons.

### Figure 6 — Production-position distribution

**Move most to appendix.** Useful for source construction, but not a detector-background result. Color-bar quantity and spatial binning need units. The main text should instead show selected delayed spectra and isotope/material rate contributions.

### Figure 7 — “Necessity” of exact-position sampling

**Claim too strong.** Different incident families produce different distributions, but this does not prove that position sampling materially changes the final selected 511 keV rate or sensitivity. Add direct comparisons of selected spectra/rates for production-position, volume-uniform, and radial-profile delayed sources, or move this figure to the appendix.

### Figure 8 — Selection and mission diagnostics

**Split into two figures.** Panels A/B need MC error bars. Panel C shows raw counts from samples with different statistics/normalizations and is misleading. Panel D uses too many quantities and dual axes. “Compton/FoV pass” is inconsistent with retaining reconstruction rejects. Produce one cut-flow figure and one mission-time-fold figure.

### Figure 9 — Compton/FoV example

**Remove from main paper.** It is a toy/debug event diagram. Replace with a general 3-D geometry, cone–aperture definition, angular residual distributions, and signal/background comparisons.

### Tables 4–7

- **Table 4:** Compress; replace prose with source component, model/version, parameter range, generated number, physical exposure, effective sample size, normalization uncertainty.
- **Tables 5 and 6:** Merge into one results table with day-15 rates, mission-integrated counts, MC uncertainty, systematic assumptions, prompt/delayed subcomponents, line width, and statistical metric.
- **Table 7:** Rename and move to supplement. It is an inventory/serialization check, not convergence. A real convergence table must include \(M\), seed, transported decays, selected events, selected rate, statistical uncertainty, and deviation from reference.

---

## 7. Literature/context gaps and suggested references

### References that should be added or updated

1. **P. Jean et al.**, “Spectral analysis of the Galactic \(e^+e^-\) annihilation emission,” *Astron. Astrophys.* 445 (2006) 579–589, DOI 10.1051/0004-6361:20053765, arXiv:astro-ph/0509298. Use for narrow/broad line components and annihilation-medium interpretation.

2. **T. Siegert et al.**, “Constraints on positron annihilation kinematics in the inner Galaxy,” *Astron. Astrophys.* 627 (2019) A126, DOI 10.1051/0004-6361/201833856, arXiv:1906.00498. Use for centroid/line-width/velocity claims.

3. **G. De Cesare**, “Searching for the 511 keV annihilation line from galactic compact objects with the IBIS gamma ray telescope,” *Astron. Astrophys.* 531 (2011) A56, DOI 10.1051/0004-6361/201116516. Use for compact-source upper-limit scale.

4. **J.-P. Roques et al.**, “First INTEGRAL observations of V404 Cygni during the 2015 outburst: spectral behavior in the 20–650 keV energy range,” *Astrophys. J. Lett.* 813 (2015) L22, DOI 10.1088/2041-8205/813/1/L22, arXiv:1510.03677. Cite alongside the Nature interpretation.

5. **T. Sato**, “Analytical Model for Estimating the Zenith Angle Dependence of Terrestrial Cosmic Ray Fluxes,” *PLOS ONE* 11 (2016) e0160390, DOI 10.1371/journal.pone.0160390. Required for PARMA4.0 angular fields.

6. **S. Gallego et al.**, “Bottom-up Background Simulations of the 2016 COSI Balloon Flight,” *Astrophys. J.* 986 (2025) 116, DOI 10.3847/1538-4357/add6a0, arXiv:2503.02493. Relevant benchmark for balloon background validation.

7. **A. Ciabattoni et al.**, “Benchmarking of Geant4 simulations for the COSI Anticoincidence System,” *Experimental Astronomy* 60 (2025) 9, DOI 10.1007/s10686-025-10019-7. Relevant for scintillator/anticoincidence validation.

8. **J. Beechert et al.**, “Calibrations of the Compton Spectrometer and Imager,” *Nucl. Instrum. Methods Phys. Res. A* 1031 (2022) 166510, DOI 10.1016/j.nima.2022.166510, arXiv:2203.00695. Use instead of mission webpages for technical COSI context.

9. **C. C. Sleator et al.**, “Benchmarking simulations of the Compton Spectrometer and Imager with calibrations,” *Nucl. Instrum. Methods Phys. Res. A* 946 (2019) 162643, DOI 10.1016/j.nima.2019.162643, arXiv:1911.02992. Relevant to detector-response/reconstruction validation.

10. **H. Odaka et al.**, “Modeling of proton-induced radioactivation background in hard X-ray telescopes: Geant4-based simulation and its demonstration by Hitomi’s measurement in a low Earth orbit,” *Nucl. Instrum. Methods Phys. Res. A* 891 (2018) 92–105, DOI 10.1016/j.nima.2018.02.071, arXiv:1804.00827. Use for activation-history validation methodology.

11. **P. Cumani et al.**, “Background for a gamma-ray satellite on a low-Earth orbit,” *Experimental Astronomy* 47 (2019) 273–302, DOI 10.1007/s10686-019-09624-0, arXiv:1902.06944. Useful for environmental inventories, with orbit/balloon differences stated.

12. **G. Cowan, K. Cranmer, E. Gross, O. Vitells**, “Asymptotic formulae for likelihood-based tests of new physics,” *Eur. Phys. J. C* 71 (2011) 1554, DOI 10.1140/epjc/s10052-011-1554-0, arXiv:1007.1727. Use for profile-likelihood sensitivity with nuisance parameters.

13. **H. Yoneda, T. Siegert, S. Mittal**, “Imaging the positron annihilation line with 20 years of INTEGRAL/SPI observations,” *Astron. Astrophys.* 702 (2025) A220, DOI 10.1051/0004-6361/202555895. Replace the manuscript's arXiv-only citation if this final reference matches publisher metadata.

14. **S. Gallego et al.**, “Preflight Background Estimates for COSI,” *Astrophys. J.* (2026), DOI 10.3847/1538-4357/ae32f4, arXiv:2510.25304. Check final volume/article metadata before citation.

### References currently used but needing better placement

- Gehrels (1985) remains important but cannot be the sole basis for a modern quantitative shield/background model.
- Gottardi TES review is mainly an X-ray microcalorimeter review; use gamma-ray TES prototype/calibration literature for 511 keV response.
- Zhang et al. arXiv review should not be the main evidence for the particular Ta absorber response.
- NASA/HEASARC web pages should be replaced by peer-reviewed instrument papers for technical specifications.
- Laue-lens arXiv references should be supplemented with peer-reviewed crystal/lens prototype publications where possible.

---

## 8. Prioritized revision checklist

### Priority 0 — Required before any submission

1. Correct the \(1.09\times10^5\) count error and the zero-event Poisson upper limit.
2. Define the source-flux reference plane and rewrite the normalization derivation with units.
3. Replace the synthetic mission claim with actual/representative trajectory, target visibility, and slant-atmosphere fold.
4. Restrict headline result to unresolved-line sensitivity and calculate realistic line-width cases.
5. Include full-payload and optics-support prompt background, or reframe as subassembly analysis.
6. Provide Geant4/MEGAlib versions, physics list, decay settings, cuts, and custom-code documentation.
7. Increase delayed-decay statistics and show selected-rate convergence across multiple \(M\) values and seeds.
8. Replace ideal TES/CsI response with detector-effects model or quantified response uncertainty envelope.
9. Define and independently validate a defensible multi-hit reconstruction baseline.
10. Replace \(S/\sqrt B\) as headline result with a likelihood including background nuisance parameters.

### Priority 1 — Required for a strong NIM A paper

11. Add \(A_{\rm eff}(E)\), PSF, encircled energy, off-axis response, and lens tolerances.
12. Present selected prompt/delayed spectra and physical/isotopic decompositions.
13. Add threshold, veto-window, shielding, energy-resolution, and line-window sensitivity scans.
14. Compare CsI with at least one alternative shield material because \(^{128}\)I dominates activity.
15. Validate source normalization, attenuation, detector efficiency, and radioactive spectra with simple benchmarks.
16. Define an in-flight background estimation strategy using off-source data, control bands, or physical tracers.
17. Supply a structured statistical and engineering uncertainty budget.

### Priority 2 — Presentation and manuscript quality

18. Replace internal/debug terminology throughout.
19. Merge/remove Tables 1, 2, 5, 6, 7; move run-level validation to supplement.
20. Redraw Figures 2–9 with readable labels, physical quantities, and uncertainty bars.
21. Fix float placement so no figure/table appears after references.
22. Reduce numerical precision to match MC/model uncertainty.
23. Update bibliography: PARMA4.0, Yoneda et al., COSI background validation, final COSI preflight paper.
24. Consider revising title to identify the work as a Monte Carlo estimate and unresolved-line sensitivity study.

**Reviewer recommendation:** Do not submit the present version. Complete all Priority 0 items, rebuild the results from the revised calculation, and then regenerate the abstract, figures, and conclusions.
