#!/usr/bin/env python3
"""Build the peer-review HTML and annotated TeX source.

The original 13 July review read only the English manuscript TeX file.  M02 was
corrected on 4 August after a project data-lineage audit showed that the final
consumer retains sub-80-keV CC HIT deposits and applies 50 keV offline.  The
generated TeX preserves the reviewed paper text and adds PDF highlight
annotations whose identifiers match the HTML report.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from textwrap import dedent


HERE = Path(__file__).resolve().parent
MANUSCRIPT_DIR = HERE.parent
SOURCE = MANUSCRIPT_DIR / "balloon511_ea_draft_en.tex"
ANNOTATED_TEX = HERE / "balloon511_ea_draft_en_peer_review_annotated.tex"
HTML_REPORT = HERE / "ea_peer_review_report.html"

REVIEW_DATE = "13 July 2026"
BASELINE_PDF = "balloon511_ea_draft_en.pdf"
RESOLVED_REVIEW_IDS = {"M03"}

R2_REVIEW_DATE = "13 July 2026 (round 2, incremental)"

R2_REVISED_TITLE = (
    "Background-driven shield design and reference sensitivity of a "
    "balloon-borne 511 keV Laue-lens telescope with a transition-edge-sensor "
    "focal plane"
)

R2_REVISED_ABSTRACT = (
    "The sensitivity of a balloon-borne 511 keV Laue-lens telescope is limited "
    "by the instrumental background at its focal plane. We present a "
    "detector-coupled Geant4/MEGAlib background study for a "
    "transition-edge-sensor (TES) microcalorimeter array behind a Ge(111) Laue "
    "lens of 20.1 cm² on-axis effective area. The focused signal, eight prompt "
    "atmospheric particle families from EXPACS/PARMA, activation decays sampled "
    "at their simulated production positions, and an atmospheric 511 keV line "
    "component pass through a common response and event selection: a "
    "510.58–511.42 keV window, a 50 keV anticoincidence veto, and a Compton "
    "topology/field-of-view test. In the mass-complete detector–cryostat "
    "reference geometry the selected background is (4.64 ± 0.54) × 10⁻² s⁻¹, "
    "dominated by incident positrons and neutrons, and the selected activation "
    "events arise almost entirely from ⁶⁴Cu in cold copper near the detector. "
    "These origins motivate a directionally graded bismuth germanate (BGO) "
    "shield with 40, 30, and 10 mm side, bottom, and top coverage. With this "
    "shield the modeled background is 5.85 × 10⁻³ s⁻¹ and the selected signal "
    "is 1.11 × 10⁻³ s⁻¹ for a 10⁻⁴ photon cm⁻² s⁻¹ reference source. A "
    "synthetic, continuously on-source 20-day trajectory yields counting-based "
    "3σ flux thresholds of 1.6 × 10⁻⁵ (central) and 4.6 × 10⁻⁵ photon cm⁻² s⁻¹ "
    "(finite-sample conservative). These are unresolved-line, "
    "detector–cryostat-scope reference estimates: the graded-shield delayed "
    "stream contains neutron-induced activation only, and source visibility, "
    "pointing losses, and physical systematics are not included."
)

R3_REVIEW_DATE = "14 July 2026 (round 3, revision-increment review)"

# The 14 July revision replaced the neutron-only delayed stream with the
# all-eight-family calculation, so the R1/R2 recommended abstracts are
# superseded on numbers and on the delayed-scope caveat. R3 update below.
R3_REVISED_ABSTRACT = (
    "The sensitivity of a balloon-borne 511 keV Laue-lens telescope is limited "
    "by the instrumental background at its focal plane. We present a "
    "detector-coupled Geant4/MEGAlib background study for a "
    "transition-edge-sensor (TES) microcalorimeter array behind a Ge(111) Laue "
    "lens of 20.1 cm² on-axis effective area. The focused signal, eight prompt "
    "atmospheric particle families from EXPACS/PARMA, activation decays sampled "
    "at their simulated production positions for all incident families, and an "
    "atmospheric 511 keV line component pass through a common response and "
    "event selection: a 510.58–511.42 keV window, a 50 keV anticoincidence "
    "veto, and a Compton topology/field-of-view test. In the mass-complete "
    "detector–cryostat reference geometry the selected background is "
    "(4.64 ± 0.54) × 10⁻² s⁻¹, dominated by incident positrons and neutrons, "
    "with the selected activation events arising almost entirely from ⁶⁴Cu in "
    "cold copper. These origins motivate a directionally graded bismuth "
    "germanate (BGO) shield with 40, 30, and 10 mm side, bottom, and top "
    "coverage. With this shield, and a day-15 activation inventory of 36.5 Bq "
    "spanning seven incident families (no electron-induced products were "
    "observed in the finite activation sample), the modeled background is "
    "6.96 × 10⁻³ s⁻¹ against a selected signal of 1.12 × 10⁻³ s⁻¹ for a 10⁻⁴ "
    "photon cm⁻² s⁻¹ reference source. A synthetic, continuously on-source "
    "20-day trajectory yields counting-based 3σ flux thresholds of 1.7 × 10⁻⁵ "
    "(central) and 4.7 × 10⁻⁵ photon cm⁻² s⁻¹ (conditional finite-transport "
    "endpoint). These are unresolved-line, detector–cryostat-scope reference "
    "estimates; source visibility, pointing losses, and physical systematics "
    "are not included."
)

REVISED_TITLE = (
    "Detector-coupled background modeling and reference sensitivity for a "
    "balloon-borne 511 keV Laue-lens telescope"
)

REVISED_ABSTRACT = (
    "Instrumental background limits the sensitivity of balloon-borne 511 keV "
    "telescopes. We developed a detector-coupled Monte Carlo model of a Laue "
    "lens and transition-edge-sensor microcalorimeter that applies a common "
    "response and event selection to an on-axis focused signal, eight prompt "
    "atmospheric particle families, production-position-sampled activation "
    "decays, and an atmospheric 511 keV component. In a mass-complete "
    "detector–cryostat reference geometry, the selected 510.58–511.42 keV "
    "background was (4.643 ± 0.543) × 10⁻² s⁻¹. Positrons and neutrons supplied "
    "96.8% of the prompt rate, and 24 of 26 selected delayed events were ⁶⁴Cu "
    "decays in cold copper. This decomposition motivated a bismuth germanate "
    "shield with side, bottom, and top thicknesses of 40, 30, and 10 mm. For "
    "the graded-shield geometry, a 420 eV full width at half maximum response "
    "and active veto reduced the prompt rate from 2.849 × 10⁻² to 4.072 × 10⁻³ "
    "s⁻¹. The modeled background and signal rates after selection were 5.850 × "
    "10⁻³ and 1.113 × 10⁻³ s⁻¹, respectively, for a 10⁻⁴ photon cm⁻² s⁻¹ "
    "reference source. A synthetic, continuously on-source 20-day profile gave "
    "a counting-based 3σ flux threshold of 1.615 × 10⁻⁵ photon cm⁻² s⁻¹; a "
    "component-wise finite-sample calculation gave 4.627 × 10⁻⁵ photon cm⁻² "
    "s⁻¹. These are statistical reference-exposure estimates: the graded-shield "
    "delayed stream includes neutron-induced activation only, and the "
    "calculation omits realistic source visibility, pointing losses, and "
    "physical background systematics."
)


@dataclass(frozen=True)
class Review:
    rid: str
    severity: str
    category: str
    pages: str
    title: str
    finding: str
    action: str
    basis: str = "Internal manuscript consistency"


REVIEWS = [
    Review(
        "M01", "Major", "Scientific scope", "6, 21",
        "The reported background covers the detector–cryostat subsystem, not the full payload",
        "The paper calls the geometry mass-complete and the chain end-to-end, but it explicitly confines the background budget to the detector–cryostat branch. The lens, lens support, gondola, and other payload masses can scatter radiation and create prompt or activation products. A mission-scale total cannot be inferred without transporting or bounding those contributions.",
        "Either transport every background family through a payload model that includes the optics and major support masses, or quantify a defensible upper bound. Until then use ‘detector–cryostat subsystem background’ throughout the title, abstract, results, and conclusion.",
    ),
    # Post-review audit correction (2026-08-04): do not infer the analysis data
    # path from a detector-map TriggerThreshold field.  The final consumer reads
    # CC HIT deposits, retains sub-80-keV values, and applies 50 keV offline.
    Review(
        "M02", "Major", "Audit correction (closed)", "4, 18, 21",
        "The 50 keV offline BGO anticoincidence data path is complete",
        "A project data-lineage audit confirmed that the final quantitative selection reads step-level CC HIT deposits, sums the matched BGO active volumes event by event, and applies the 50 keV criterion in post-processing. Raw SIM files and production catalogs contain deposits below 80 keV, including the 50–80 keV interval; native trigger/veto flags and the detector-map 80 keV field are not consumed by the final selection. The original review premise that the field was a hard hit-storage threshold is therefore false.",
        "Describe the event-wise deposited-energy sum and 50 keV offline anticoincidence in journal language. No native-threshold rerun is required. Treat BGO light collection and electronic turn-on as a separate detector-response limitation.",
    ),
    Review(
        "M03", "Major", "Scientific scope", "1, 8, 19–21",
        "The final delayed background contains neutron-induced activation only",
        "The Methods explicitly state that activation from seven incident families was not transported and is not zero, yet the abstract and conclusion use ‘complete selection’, ‘full chain’, and total-background language. Because the selected-event importance need not follow inventory activity, the omitted term cannot safely be assumed negligible.",
        "Transport all eight activation families in the graded-shield geometry with adequate position samples, or propagate defensible bounds for each omitted family. Until then label every final rate and sensitivity as a neutron-activation-only partial model.",
    ),
    Review(
        "M04", "Major", "Source model", "8–9, 16, 19",
        "The atmospheric 511 keV component has results but no reproducible source method",
        "This component contributes 26.59% of the final background, but Table 1 and the common time-axis description omit it. Its intensity, spectral width, angular distribution, source surface, exposure, weights, altitude dependence, and trajectory scaling are not specified. In addition, the PARMA3 primary paper reports a small photon feature near 0.5 MeV from annihilation, so adding a separate line requires an explicit no-double-counting construction.",
        "Add a fourth-stream Methods subsection and workflow node; provide provenance, spectrum, angular law, absolute normalization, generated counts, exposure, cut-flow, and trajectory rule. Demonstrate whether the PARMA/EXPACS continuum’s annihilation feature was removed, retained, or shown negligible before adding the explicit line.",
        "Manuscript plus PARMA3 primary publication",
    ),
    Review(
        "M05", "Major", "Science case", "2, 9–10, 15, 20–21",
        "The exposure fold does not represent a Galactic-centre balloon observation",
        "The signal response is an on-axis north-sky/near-zenith reference, while the paper’s motivating target is the Galactic-centre region. The trajectory is synthetic, continuously on-source, and expressly omits visibility, target elevation, Earth occultation, repointing, attitude jitter, and off-axis losses. The resulting curve is therefore an exposure-scaling benchmark, not a flight forecast or Galactic-centre sensitivity.",
        "Fold a real or parameterized ephemeris with slant atmospheric depth, source visibility, duty cycle, pointing jitter, and off-axis response. Otherwise rename all mission claims as a generic continuously illuminated on-axis reference exposure.",
    ),
    Review(
        "M06", "Major", "Science case", "1–2, 9, 12, 20",
        "The headline sensitivity applies only to an unresolved monochromatic line",
        "The science motivation discusses intrinsic widths of about 1.3 and 5.4 keV, whereas the signal is monochromatic and selected in a ±0.420 keV window. Under a Gaussian screening calculation, that window retains about 98.1% of the assumed 0.420 keV detector line but only about 53% and 14.5% for 1.3 and 5.4 keV intrinsic FWHM after convolution.",
        "Report optimized sensitivity versus intrinsic width and centroid offset, including unresolved, 1.3 keV, and 5.4 keV cases. Until then use ‘unresolved-line’ or ‘monochromatic-line’ whenever quoting the threshold.",
        "Internal calculation using the widths stated in the manuscript",
    ),
    Review(
        "M07", "Major", "Design logic", "10, 17–18",
        "The exact 40/30/10 mm BGO configuration is selected, not demonstrated as optimized",
        "The event-origin decomposition motivates directional shielding but does not determine the three thicknesses. No candidate set, objective function, independent evaluation sample, mass/background trade-off, signal loss, power/readout burden, or mechanical constraint is shown. A gross shell calculation from Table 4 gives roughly 41,768 cm³ of BGO, or about 298 kg at 7.13 g cm⁻³ before aperture cuts; the actual manifest mass is essential for balloon feasibility.",
        "Provide a design matrix or response surface for candidate geometries, report actual material masses from the manifest, specify the optimization objective and constraints, and evaluate the selected point with independent statistics. Otherwise replace ‘optimized’ with ‘selected graded-shield configuration’.",
        "Internal geometry screening calculation; actual CAD/manifest mass required",
    ),
    Review(
        "M08", "Major", "Optics physics", "5–6",
        "The custom Laue diffraction process needs a slab-level physics validation",
        "Converting a target reflectivity to a diffraction mean free path and then allowing standard absorption to compete does not automatically reproduce the original reflectivity. The manuscript also does not show whether the XOP mosaic rocking curve and an additional Gaussian plane perturbation double-count angular spread or correctly sample the diffracting crystallite orientation. Every signal and sensitivity result depends on this response.",
        "Derive the competing-hazard construction, then benchmark reflection, transmission, absorption, and outgoing-angle distributions against XOP/CRYSTAL over angle and energy. Demonstrate step-size convergence and state the crystal dimensions, ring geometry, incident area, model versions, and mosaic sampling rule.",
    ),
    Review(
        "M09", "Major", "Normalization", "9, 11, 14",
        "A unit-replay signal rate is called physical on the common coincidence axis",
        "The paper gives a physical focused entrance rate of 1.48 × 10⁻³ s⁻¹ at the reference flux, but the coincidence axis uses 0.987 s⁻¹ and calls all three rates physical. Table 2 later identifies the signal rows as unit replay. Injecting signal at roughly 660 times its physical rate can bias accidental grouping or mixed-stream attribution unless the signal is excluded from background bookkeeping.",
        "Build the background coincidence axis without signal or inject signal at the tested physical flux. State the reference duration, final full-band rates, mixed-group attribution rule, same- and mixed-stream counts, and exact dead-time/live-factor definition. Label unit-replay plots and tables unmistakably.",
    ),
    Review(
        "M10", "Major", "Detector timing", "11, 20",
        "The 1 μs coincidence window and live factor lack detector/readout justification",
        "The common-axis construction assumes a 1 μs grouping window, while no TES pulse duration, shaping time, trigger logic, multiplexing bandwidth, per-pixel dead time, saturation, or pile-up model is supplied. At full-band rates near 10³ s⁻¹ these assumptions can affect both event grouping and live time.",
        "Tie the coincidence and veto windows to a specified detector/readout architecture, include per-pixel pulse and dead-time behavior, and provide sensitivity to the timing window. Do not interpret the current accidental live factor as a hardware dead-time model.",
    ),
    Review(
        "M11", "Major", "Statistics", "10, 19–20",
        "The central prompt rate is supported by only five final records",
        "Two positron and three neutron records set the prompt central value; six families have zero selected records, and the zero-count high-weight photon component dominates the conservative result. The component-wise upper endpoints are transparent stress bounds, but summing separate two-sided 95% endpoints has no stated simultaneous 95% coverage and is not a confidence interval for the total.",
        "Increase transport statistics, especially prompt photons. Use the correct binomial/Poisson likelihood for each simulation design and combine components in a joint likelihood or posterior with Monte Carlo nuisance parameters. Label the current endpoint sum as a deliberately conservative finite-sample bound, not an exact total interval.",
    ),
    Review(
        "M12", "Major", "Statistics", "10, 20",
        "S/√B is a counting proxy, not yet a detection significance or formal flux threshold",
        "The metric assumes exactly known background and omits control-region uncertainty, line-like atmospheric-background nuisance parameters, search trials, and physical systematics. Even for the stated counts, a Poisson Asimov calculation differs from S/√B, illustrating that the chosen formula is not a unique significance definition.",
        "Use a source-plus-background likelihood with background nuisance parameters and the intended spatial/control-region information. Until then call Z a counting-performance proxy and F₃σ a counting-based reference threshold.",
    ),
    Review(
        "M13", "Major", "Validation", "15–16",
        "The trajectory-fold validation is too broad and not shown numerically",
        "The text claims agreement for e⁺, neutron, and photon modulation in 480–550 keV, but supplies no table of states, counts, predicted scales, Q values, uncertainties, or z definition. Broad-band agreement does not demonstrate that total family-flux scaling is unbiased inside the narrow 511 keV window as angular and energy spectra change.",
        "Report the four-state comparison in Results and validate energy/angle-resolved reweighting in or around the analysis window. Quantify the bias for untested particle families rather than treating analytic source-field scaling as validated transport.",
    ),
    Review(
        "M14", "Major", "Reproducibility", "6–9, 22",
        "Essential transport and response configuration is missing",
        "The manuscript does not state exact Geant4, MEGAlib/Cosima, XOP/xoppylib/DABAX, and PHITS/EXPACS versions; physics lists; electromagnetic and hadronic models; production cuts; radioactive-decay settings; source energy limits/surfaces; or most random seeds. The data statement promises a repository only in the future.",
        "Archive a versioned snapshot at submission and cite it. Include configurations, geometry and source files, exposure tables, trajectory array, response and selection code, environment lockfile, seeds, and scripts that regenerate every table and figure.",
    ),
    Review(
        "M15", "Major", "Comparability", "16–19",
        "The reference and graded-shield totals are not like-for-like",
        "The reference delayed term is all-family activation in a CsI geometry, whereas the graded-shield delayed term is neutron-only in BGO. The atmospheric line is introduced only in the final budget, and the active-shield threshold definitions also differ. The observed rate change therefore cannot be attributed solely to the shield design.",
        "Run both geometries with identical incident streams, activation families, hit storage, response, thresholds, coincidence logic, and statistical exposure. Present paired component changes before interpreting the geometry effect.",
    ),
    Review(
        "M16", "Moderate", "Detector response", "3, 10, 21",
        "The 420 eV response should be identified as an estimated energy resolution",
        "The present detector concept uses 420 eV FWHM as an input to the pixel-level Gaussian response; it is not presented as a measured efficiency or as a measured end-to-end array performance.",
        "State once that 420 eV FWHM is the estimated energy resolution adopted as a simulation input, while retaining the response implementation details in the Methods.",
    ),
    Review(
        "M17", "Moderate", "Detector physics", "3",
        "Detection efficiency should be identified as interaction efficiency",
        "The 49 percent single-layer and near-unity six-layer estimates refer to interactions in Ta; calling them detection efficiencies can be confused with end-to-end system efficiency.",
        "Replace ‘detection efficiency’ with ‘interaction efficiency’; no additional efficiency discussion is needed in this paragraph.",
    ),
    Review(
        "M18", "Moderate", "Flux convention", "2, 9",
        "Atmospheric transmission and effective-area terminology are inconsistent",
        "Multiplying a top-of-atmosphere flux by T gives the flux at the payload, not an ‘above-payload’ flux. The quoted selected area S/F₀ = 11.13 cm² includes T = 0.739; it is therefore atmosphere-inclusive. The corresponding instrument-only selected area is about 15.1 cm² under the manuscript’s definitions.",
        "Define top-of-atmosphere and at-payload flux once, state the zenith/slant column and transmission model, and separate instrumental effective area from the atmosphere-folded count-to-flux conversion.",
    ),
    Review(
        "M19", "Moderate", "Source normalization", "6–7",
        "PARMA model versions and angular/source-plane normalization need separation",
        "The source paragraph calls the model PARMA3.0 while citing the 2016 zenith-angle extension associated with version 4.0. The conversion from directional intensity in equal-μ bins to a far-field area-source rate is not fully defined, including projected-area factors and exposure units.",
        "Distinguish the spectral and angular model versions, publish the differential flux units and source-surface convention, and derive the bin-integrated rate including solid-angle and projected-area factors.",
    ),
    Review(
        "M20", "Moderate", "Event selection", "13–15",
        "The topology/FoV test is permissive and has ambiguous boundary handling",
        "A two-hit event passes if any of 81 sub-pixel combinations and either scatter order intersects the aperture. Single-site events pass automatically, multiplicities above six are retained without ordering, and the text does not say whether unreconstructed events enter the final rate. A legacy-geometry benchmark does not establish current-geometry performance.",
        "Define the exact Boolean acceptance rule for every multiplicity, rerun the benchmark in the analyzed geometry, show azimuth/sub-pixel convergence, and report signal/background efficiency or an ROC-style trade-off. Include position/energy uncertainty and Doppler broadening where relevant.",
    ),
    Review(
        "M21", "Moderate", "Trajectory model", "15–16",
        "Trajectory discretization and activation initial conditions are underdefined",
        "Eighty-one grid points at 0.25-day spacing define 80 intervals over 20 days, not 81 quarter-day bins. The initial inventory Nₖ(0), time-unit conversion, interpolation/quadrature rule, and live-factor insertion are not stated.",
        "Publish the 81-point array and interval durations, state Nₖ(0), numerical update and units, and define how each live fraction is calculated and applied.",
    ),
    Review(
        "M22", "Moderate", "Uncertainty", "18–21",
        "The final figures omit the uncertainties that dominate interpretation",
        "Rates are printed to four or five significant figures despite five-record prompt support. The 64 response-seed spread tests response integration, not transport-count uncertainty, and no physical systematic budget is propagated.",
        "Add Monte Carlo intervals to the final component plot and cut-flow, propagate a joint uncertainty band to the exposure curve, round values to supported precision, and scan radiation field, physics list, geometry, response, threshold, transmission, and pointing assumptions.",
    ),
    Review(
        "M23", "Moderate", "Interpretation", "17, 19, 21",
        "The atmospheric-shield interpretation is not supported by the shown cut-flow",
        "The text says active coverage controls atmospheric paths, but all eight atmospheric-line records survive the active veto and topology selection. The shown shield reduces modeled prompt and delayed coincidences, not the line-like sky-facing component once it enters the aperture.",
        "Restrict the shield inference to supported prompt/delayed components. Discuss atmospheric-line mitigation separately through aperture design, pointing modulation, control regions, and spatial–spectral modeling.",
    ),
    Review(
        "S01", "Structural", "Manuscript logic", "2–21",
        "Methods and Results are interleaved, obscuring the evidential chain",
        "The Methods contain signal rates, cut-flow outcomes, topology efficiencies, a legacy benchmark, and trajectory-validation results, while the shield dimensions appear before the selection evidence that motivates them. The Introduction also restates the compact-source motivation and reference flux several times.",
        "Use the sequence: Introduction and objective; instrument and assumptions; source/response/selection/statistics Methods; validation and design protocol; Results; Discussion and limitations; short Conclusion. Define F₀ once and move all outcome numbers out of Methods except necessary normalization checks.",
    ),
    Review(
        "S02", "Structural", "Writing and flow", "throughout",
        "The prose is understandable but too process-centred and compressed",
        "Several paragraphs combine implementation, rationale, equations, validation, and interpretation in sentences exceeding 100 words. Internal-development register (‘recording hook’, ‘process class’, ‘preregistered’, ‘starved continuum’) and meta-commentary (‘easy to read’, ‘three linked views’, ‘two columns answer’) weaken journal tone.",
        "Split long sentences by scientific function, remove drafting/developer commentary, state results directly, and standardize event/record/group/hit, analysis-window terminology, FoV capitalization, Laue capitalization, and either US or UK English.",
    ),
    Review(
        "J01", "Journal", "Experimental Astronomy", "1, 22–24",
        "The subject fits Experimental Astronomy, but the manuscript is not submission-ready",
        "The detector, background, shielding, and analysis-method focus is well aligned with the journal’s instrumentation scope. The present custom article layout, numbered citation-order bibliography, DOI formatting, incomplete declarations, and future-tense availability statement do not satisfy the current submission expectations.",
        "Move to the current Springer Nature LaTeX template; use the journal’s author–year, alphabetized reference style with DOI URLs; verify published/accepted versions; complete the title page, Statements and Declarations, funding, competing interests, contributions, and a current Data Availability Statement.",
        "Official Experimental Astronomy aims/scope and submission guidelines",
    ),
    Review(
        "J02", "Journal", "Abstract and figures", "1, 5–20",
        "The abstract length and keyword count fit, but claims and artwork need revision",
        "The current abstract is within the journal’s 150–250-word range and has six keywords, but BGO and FWHM are undefined and the completeness claim is too strong. Several quantitative plots are raster images and sparse spectra lack self-contained normalization/uncertainty information.",
        "Use the rewritten 224-word abstract below, define abbreviations, and keep the caveat sentence until missing physics is completed. Supply plots as vector PDF/EPS where possible, or meet the journal’s line/combination-art resolution requirements; add units, bin widths, normalization status, and statistical intervals to captions.",
        "Official Experimental Astronomy submission guidelines",
    ),
    Review(
        "J03", "Journal", "AI disclosure", "submission stage",
        "Substantial adopted AI-generated wording may require disclosure",
        "The journal’s current policy distinguishes copyediting from substantive generative-AI use. A substantially adopted rewritten title or abstract is more than mechanical spelling correction.",
        "Check the policy at submission, disclose the tool and purpose if required, and state that all authors reviewed, verified, and accept responsibility for the final scientific content.",
        "Official Experimental Astronomy submission guidelines",
    ),
]


ANNOTATIONS = [
    # id, category, anchor, concise PDF popup text, optional occurrence
    ("J02", "Title/abstract", "Detector-coupled Monte Carlo estimate of background and unresolved-line sensitivity for a balloon-borne 511 keV Laue-lens TES telescope", "Title is long and implies a better-established sensitivity than the current partial background model. See the report for the recommended replacement title.", 1),
    ("M03", "Scope", "final full chain", "The graded-shield delayed stream is neutron-induced only. This phrase overstates completeness; label the result as a partial modeled background or transport all activation families.", 1),
    ("M03", "Scope", "complete selection", "Selection may be complete, but the physical background input is not. State the neutron-only delayed scope in the abstract.", 1),
    ("M18", "Flux convention", "single payload-plane observational reference flux", "Use the IBIS-based 3-sigma-equivalent upper limit and the 45-degree atmospheric transmission to define the single payload-plane observational reference flux; do not introduce separate Monte Carlo normalization values in this paragraph.", 1),
    ("M17", "Detector physics", "increasing the collecting-area-to-detector-area ratio", "Revised wording now states the actual focusing benefit and explicitly retains a narrow, optics-defined field of view rather than claiming increased sky coverage.", 1),
    ("M17", "Detector physics", "estimated interaction efficiency of about", "Only the terminology is changed: the 49 percent single-layer and near-unity six-layer estimates are called interaction efficiencies.", 1),
    ("M16", "Detector response", "estimated energy resolution and simulation input", "The 420 eV FWHM value is now stated once as an estimated detector energy resolution adopted for the response model.", 1),
    ("M02", "Audit correction", "optimized BGO transport records shield hits", "The 2026-08-04 lineage audit found sub-80-keV CC HIT deposits in the raw and cataloged data; the final selection sums them event by event and applies 50 keV offline. No native-threshold rerun is required.", 1),
    ("S02", "Language", "focal-plane plane", "Delete the repeated word: focal plane.", 1),
    ("M08", "Optics validation", "mosaic system is adopted to make the Monte Carlo calculation convenient", "Convenience is not a physical justification. State the scientific design rationale and validate the modeled response.", 1),
    ("M08", "Optics validation", "to avoid double counting with standard photoelectric absorption", "The competing-hazard construction does not automatically reproduce the target XOP reflection, transmission, and absorption. Add derivation and slab benchmarks.", 1),
    ("M01", "Modeled scope", "primary background budget", "This explicitly excludes optics and other payload masses. Mission-scale total-background language must be narrowed or omitted contributions transported/bounded.", 1),
    ("M19", "Source model", "PARMA3.0", "Distinguish the PARMA spectral-model version from the cited zenith-angle extension and document the exact EXPACS release.", 1),
    ("S02", "Language", "custom recording hook", "Implementation detail is useful, but write this as a reproducible scientific data-capture method rather than developer prose.", 1),
    ("M04", "Missing method", "source layers used", "The following source table omits the atmospheric 511 keV stream that later contributes 26.59 percent. Add it with provenance, normalization, exposure, and angular/spectral definitions.", 1),
    ("M03", "Incomplete activation", "is not treated as zero", "Correct caveat, but it invalidates later full-chain and total-background wording. Complete all-family final transport or propagate bounds.", 1),
    ("M18", "Effective area", "surviving signal rate", "The subsequent count-to-flux area includes atmospheric transmission. Report an instrument-only selected area separately from the atmosphere-folded system conversion.", 1),
    ("M05", "Observing geometry", "not a flight forecast for a named launch campaign", "This fixed-axis reference still omits source visibility, pointing losses, and off-axis response. Preserve that caveat in every mission and sensitivity claim.", 1),
    ("M07", "Design evidence", "only optimized geometry", "No candidate set or objective function is presented. Call this a selected configuration until a mass-constrained independent trade study is shown.", 1),
    ("M12", "Statistics", "counting metric", "S over square-root B is a diagnostic proxy under known-background assumptions, not a formal discovery significance. Use a likelihood or relabel the result.", 1),
    ("M09", "Normalization", "streams are combined", "The 0.987 per-second signal is later identified as unit replay, not the physical reference-source rate. Separate these normalizations before coincidence construction.", 1),
    ("M10", "Detector timing", "candidate group", "Justify the 1 microsecond window from TES pulse, trigger, shield, multiplexing, and dead-time behavior; add a timing-window sensitivity test.", 1),
    ("S02", "Language", "starved continuum", "Informal and ambiguous. Use either sparsely sampled Monte Carlo continuum or physically weak continuum, whichever is meant.", 1),
    ("M20", "Topology", "if any of these 81 trajectories", "This existential rule is deliberately permissive, not uncertainty marginalization. Provide signal/background trade-off and sensitivity to sub-pixel sampling.", 1),
    ("M20", "Topology", "retained without ordering", "Define whether this branch passes the final selection and quantify its signal/background contribution.", 1),
    ("M20", "Topology", "Unreconstructed events remain in the baseline rate accounting", "Ambiguous boundary rule: state explicitly whether unreconstructed events enter or fail the FoV-selected rate.", 1),
    ("M20", "Validation", "retained legacy geometry", "A different geometry is not a direct validation of current ARM and ordering performance. Demonstrate equivalence or rerun the benchmark.", 1),
    ("M05", "Trajectory", "synthetic reference profile", "Correct label. Preserve it in the abstract, results, figure captions, and conclusion; this is not a flight forecast or visibility schedule.", 1),
    ("M13", "Validation", "validate the combined", "Broad-band validation does not establish narrow-window reweighting. Report the four-state data and validate energy-angle response near 511 keV.", 1),
    ("M04", "Atmospheric line", "not present as a narrow feature in the EXPACS continuum", "The PARMA3 primary paper reports a small photon peak near 0.5 MeV from annihilation. Demonstrate explicitly that the added line does not double count that contribution.", 1),
    ("M23", "Interpretation", "atmospheric paths", "The final atmospheric-line cut-flow shows 100 percent survival. Restrict shield-control claims to components actually reduced by the shield.", 1),
    ("M07", "Mass feasibility", "most important active surface", "Report actual BGO and total payload mass. A gross shell estimate from Table 4 is about 298 kg before aperture cuts, so balloon feasibility and structural/dead-time costs are central.", 1),
    ("M11", "MC support", "five final prompt records", "Five records cannot support the displayed precision. Increase transport, especially the high-weight prompt-photon family, and propagate joint MC uncertainty.", 1),
    ("S02", "Language", "preregistered", "Use pre-specified fixed-seed value unless a formal preregistration exists and is cited.", 1),
    ("M11", "Intervals", "exact upper counting endpoint", "Component intervals may be exact under stated sampling, but their summed endpoints do not form an exact joint 95 percent interval for total background. Relabel as a conservative bound.", 1),
    ("S02", "Language", "two columns answer two useful questions", "Delete meta-commentary and state directly what assumptions define each column.", 1),
    ("S02", "Language", "strongest lesson", "Evaluative wording. State the supported comparison with cited background studies directly.", 1),
    ("M23", "Interpretation", "failure of anticoincidence", "Defensive phrasing. State neutrally that this component is indistinguishable under the applied energy and topology selections.", 1),
    ("S01", "Structure", "Scope and next steps", "Rename Limitations and next steps, and state the consequence of each limitation for the headline result.", 1),
    ("M03", "Conclusion scope", "final-geometry full chain", "The final delayed model omits seven activation families. Remove full-chain language and report this as a scoped reference-exposure estimate.", 1),
    ("J01", "Availability", "Before publication", "This is an internal promise, not a Data Availability Statement. Replace with a current, versioned archive and persistent identifier at submission.", 1),
    ("J01", "Declarations", "To be completed before journal submission", "Funding, competing interests, and contributions must be completed before submission. Consolidate under Statements and Declarations.", 1),
    ("J01", "References", "doi:10.1103/RevModPhys.83.1001", "Use the journal's author-year, alphabetized reference style and full DOI URLs. Verify published versions of arXiv-only entries.", 1),
]


# ======================================================================
# Round 2 (incremental review, same date). Everything below this block is
# additive: round-1 findings, annotations, and prose are unchanged.
# ======================================================================

REVIEWS_R2 = [
    Review(
        "N01", "Major", "Dead time and shield rate", "11, 19",
        "The mission live factor implies an unreported ~2–3×10⁴ s⁻¹ axis rate whose veto dead time is linear in the assumed 1 µs window",
        "Figure 4c defines the live factor as L = e^(−Rτ); the text never does. The baseline axis gives R ≈ 1.03×10³ s⁻¹ and L = 0.9990, but the mission fold quotes L = 0.97166–0.97986, which at τ = 1 µs implies a final-geometry full-band axis rate of about 2.0–2.9×10⁴ s⁻¹ — 20–30 times the baseline axis and presumably dominated by BGO shield counts (a ~1.2 m², ~300 kg shell in a ~5.7 cm⁻² s⁻¹ field gives the same order). That rate is never reported, and the accidental-veto loss scales at roughly 2–3% per microsecond of veto window: a TES-compatible hardware window of tens of microseconds would make accidental veto loss a first-order mission effect.",
        "Report the final-geometry full-band and shield counting rates, define the live factor in the text, tie the veto window to a stated readout timing architecture, and show mission performance versus veto window over 1–100 µs. This item belongs beside M10 in the priority sequence.",
        "Figure-4c formula plus manuscript numbers; independent flux×area cross-check",
    ),
    Review(
        "N02", "Major", "Signal transmission geometry", "2, 9, 15",
        "T = 0.739 must be tied to a stated residual column and viewing angle; a vertical-column value with the 45° side-entry geometry would overstate the signal by ~12%",
        "T = 0.739 corresponds to exp(−μ/ρ·X) with X ≈ 3.5 g cm⁻², a typical vertical residual column near the 38.75 km anchor (μ/ρ ≈ 0.086 cm² g⁻¹ for air at 511 keV). The instrument's optical axis, however, points 45° above the horizontal, for which the slant column is 1.41× vertical and T ≈ 0.65. Neither the column, the angle, nor the attenuation source is stated, and the same T_atm,511(t) multiplies the signal in every trajectory bin, so a mismatch shifts the whole signal curve by about −12% and the flux thresholds by about +13%.",
        "State the atmospheric column, attenuation data source, and viewing angle behind T = 0.739 and behind T_atm,511(t); if the anchor value is vertical, recompute at the actual source elevation or justify the choice. Couples to M05: a Galactic-centre elevation would lower T further.",
        "Reviewer screening calculation (standard-atmosphere column, XCOM air attenuation)",
    ),
    Review(
        "N03", "Major", "Stream accounting", "1, 6, 8, 11, 19",
        "The fourth background stream is missing from the source enumeration, the source table, and the common time axis",
        "The abstract and Introduction promise four transported inputs (signal, prompt, delayed, atmospheric 511 keV line) sharing one selection, and the line contributes 26.59% of the final background. But Section 3.2 builds exactly 'three source layers', Table 1 lists three, and the Section 3.4.1 coincidence axis carries only prompt/delayed/signal (928/97.1/0.987 s⁻¹). The line therefore appears to bypass the documented Poisson-axis, accidental-coincidence, and veto machinery; its eight records surface for the first time in the final cut-flow.",
        "Add the stream to Section 3.2 (with the provenance and normalization demanded in M04), to Table 1, and to the common-axis construction — or state explicitly how its active-veto and topology columns in Table 5 were produced without the common axis.",
    ),
    Review(
        "N04", "Moderate", "Monte Carlo allocation", "7, 19–20",
        "The sampling design starved the family that now controls the conservative bound",
        "The replication/de-weighting scheme of Section 3.2.1 protects the minority (non-photon) families, giving each an equivalent exposure of about 1/(6.79×10⁻⁴) ≈ 1.5×10³ s, while the photon family gets only 1/(5.43×10⁻³) ≈ 184 s (reciprocal Table-6 weights). The zero-count photon term then contributes 2.0×10⁻² of the 4.77×10⁻² s⁻¹ conservative total. The design decision produced the opposite bottleneck downstream.",
        "Report equivalent exposure per family next to the weights; rebalance future transport toward prompt photons (×10 photon exposure would cut the photon endpoint roughly ×10 if the selected count stays near zero); consider stratified sampling in energy and angle for photons near the line.",
        "Reciprocal event weights in Table 6",
    ),
    Review(
        "N05", "Moderate", "Selection physics", "18–19",
        "The 100% active-veto survival of in-window 511 keV photons is exact, not sampled",
        "For a monochromatic 511 keV incident photon, a summed TES energy inside 510.58–511.42 keV leaves at most ~0.4 keV (plus response smearing) unaccounted — far below the 50 keV shield threshold — so no in-window signal or atmospheric-line event can carry a vetoing shield deposit. The 100.00% survival entries in Tables 2 and 5 are structural identities, and the anticoincidence layer is by construction blind to this component; only aperture/collimation, pointing modulation, and spectral–spatial modelling act on it.",
        "State the identity in Section 4.3 — it strengthens the paper — and reword every phrase implying that active coverage controls the atmospheric line (see M23).",
        "Energy conservation within the stated selection",
    ),
    Review(
        "N06", "Moderate", "Isomeric states", "7–8",
        "Isomer handling in the activation accumulation is unspecified",
        "Production records carry excitation energy, and the day-15 population is matched 'by volume, isotope, and excitation state', but half-lives are said to be checked against NUBASE2020 for ground states only. Metastable products can decay on very different timescales from their ground states, so Equation (3) needs a defined treatment for excited-state populations.",
        "State how isomeric populations are assigned half-lives (separate λ, prompt de-excitation to ground, or exclusion), whether any isomers appear in the day-15 inventories, and their activity share.",
    ),
    Review(
        "N07", "Moderate", "Citation support", "2",
        "The SPI 'order 10⁻⁴' point-source limit is attributed to diffuse-emission papers",
        "Section 1.1 credits the point-like-source flux limit to the Siegert 2016 and Yoneda 2025 references, which are diffuse bulge/disk spectroscopy and imaging analyses; the only dedicated compact-source search cited is INTEGRAL/IBIS (De Cesare 2011), which carries the 1.6×10⁻⁴ number. As written, the SPI attribution is not visibly supported by the cited works.",
        "Use the IBIS compact-source limit as the observational basis, rescale it explicitly to the 3-sigma-equivalent above-atmosphere limit, and multiply by the stated atmospheric transmission to define one payload-plane observational reference flux independently of the Monte Carlo normalization.",
        "Cited-reference scope check (author-side verification against the primary papers still required)",
    ),
    Review(
        "N08", "Moderate", "Abstract comparability", "1",
        "The abstract invites an ×8 reading across non-comparable configurations",
        "The abstract quotes (4.643±0.543)×10⁻² s⁻¹ for the reference geometry (CsI shield, all-family delayed, no atmospheric line) and 5.850×10⁻³ s⁻¹ for the final geometry (BGO graded shield, neutron-only delayed, plus atmospheric line) in consecutive sentences without stating the scope change. This is M15's comparability gap surfacing in the abstract itself.",
        "Add the scope qualifiers to the abstract (both rewritten abstracts do this) or present a like-for-like pair.",
    ),
    Review(
        "N09", "Moderate", "Reference exposure", "11",
        "The reference-exposure duration and per-stream instance counts are never stated",
        "The 7,215,233 instances and 1275 mixed coincidences imply T ≈ 7.0×10³ s at the quoted 1.026×10³ s⁻¹ axis rate, and the expected mixed-coincidence count 2τT·Σ R_k R_l reproduces 1275 — the bookkeeping is self-consistent — but T itself, the per-stream instance counts, and the group-size distribution are absent from the text.",
        "State T, the per-stream instance counts, and the group statistics; the mixed-group attribution rule requested in M09 belongs in the same paragraph.",
        "Reviewer reconstruction from quoted numbers (verified)",
    ),
    Review(
        "N10", "Moderate", "Definitions", "6",
        "W = 118.3 and the '2025-08-31 solar condition' need definition and provenance",
        "W is presumably the solar-activity index used by EXPACS/PARMA, but the symbol, its units, its data source, and its effect on the eight family fluxes are unstated at first use.",
        "Define W, give its provenance for the quoted date, and state the sensitivity of the fluxes to the solar condition over the flight window.",
    ),
]

# Round-2 position on every round-1 finding (rendered as a table in the HTML).
R1_STANCES = [
    ("M01", "Concur",
     "The subsystem scope must govern the title, abstract, and conclusion. The lens sits ~10 m away and subtends little solid angle at the detector, but lens/gondola scattering and activation are untested, so 'transport or bound' is the right requirement."),
    ("M02", "Closed by post-review data-lineage audit",
     "The 2026-08-04 audit traced raw SIM records through catalog parsing and final masks. Sub-80-keV CC HIT deposits are retained and the quantitative selection applies the 50 keV cut offline; native trigger/veto flags are not consumed. The earlier direction-of-bias inference and native-threshold rerun request are withdrawn."),
    ("M03", "Concur",
     "The paper's own inventory shares (94.25% neutron, 5.38% μ⁻, D_TV(n,μ⁻) = 0.823) are the natural starting point for a defensible bound — but the bound must be efficiency-aware, because μ⁻ products concentrate in different materials than neutron products."),
    ("M04", "Concur",
     "Round 2 adds N03: the stream is also missing from the 'three source layers' enumeration, from Table 1, and from the common coincidence axis, so its Table-5 selection columns currently have no documented mechanism."),
    ("M05", "Concur, with a reframe",
     "Section 3.5 already labels the fold a synthetic reference profile and not a flight forecast; the primary fix is to let that label govern the abstract, results, and conclusion. The ephemeris/visibility modelling is the strengthening step, and N02 (slant transmission) couples directly to it."),
    ("M06", "Concur; fractions verified",
     "The window-retention fractions reproduce independently (98.1%, 53.1%, 14.5% for 0.42, 1.3, 5.4 keV FWHM). Added bound: the Laue ring bandpass (≈E·Δθ_mosaic/tanθ_B ≈ 20 keV for 30″ mosaic at θ_B ≈ 0.21°) does not further clip a few-keV line, so window re-optimization plus a sensitivity-versus-width curve suffices; no optics redesign is implied."),
    ("M07", "Concur; mass verified",
     "The ~298 kg shell estimate reproduces from Table 4 (≈4.18×10⁴ cm³ × 7.13 g cm⁻³, before aperture cuts). Nuance: the origin map does justify the directional pattern qualitatively; what is missing is the quantitative selection of 40/30/10 mm and the mass trade. N01 adds shield counting rate and veto dead time as a required axis of that trade study."),
    ("M08", "Concur; sharpened",
     "For competing hazards the first-interaction probability is [Λ_D/(Λ_D+Λ_A)]·[1−e^(−(Λ_D+Λ_A))], which does not reduce to the target R after the R/(1−A) rescaling except in weak-absorption limits; XOP mosaic reflectivity already folds crystallite absorption and mosaic width, so the added Gaussian plane perturbation risks double counting. A_inc of Equation (1) is also never given. See the teal PDF note."),
    ("M09", "Concur, with a magnitude note",
     "The signal is ≈0.1% of the axis rate, so the live-factor bias is negligible; the substantive problems are the 'three physical rates' wording (the signal rides the axis as unit replay at ≈660× its physical rate) and the unstated mixed-group attribution rule. Excluding signal from background accidental bookkeeping is the cleanest fix. See the teal PDF note."),
    ("M10", "Concur; stakes quantified",
     "N01 quantifies why this matters: at the Figure-4c definition L = e^(−Rτ), the mission live factor implies a ≈2–3×10⁴ s⁻¹ axis rate, so accidental-veto loss is ≈2–3% per microsecond of window. TES pulse and multiplexed-readout timing must be specified before the 1 µs window can be defended."),
    ("M11", "Concur",
     "N04 adds the equivalent-exposure view: ≈184 s for photons versus ≈1.5×10³ s per non-photon family — the family that dominates the conservative bound is the least-sampled one."),
    ("M12", "Concur, with a proportion note",
     "At the quoted counts the Gaussian proxy is numerically mild (Asimov Z ≈ 18.0 vs 18.57); the dominant omission is background/nuisance uncertainty and trials, not asymptotics. Relabel now, add the likelihood in revision."),
    ("M13", "Concur",
     "With three off-reference states and one combined-band statistic, |z| ≤ 0.51 has little power against 10–20% family-level biases; a per-family, per-state table with counts belongs in Results."),
    ("M14", "Concur",
     "Round 2 adds: SciPy 1.8.0 is the only pinned version anywhere in the paper; the live-factor definition exists only inside Figure 4; and whether the prompt and activation-production runs (each 25,210,216 primaries) share random seeds is unstated."),
    ("M15", "Concur",
     "N08 shows the same comparability gap operating inside the abstract (4.643×10⁻² vs 5.850×10⁻³ across different shields, delayed scopes, and stream sets)."),
    ("M16", "Concur; resolved by scoped wording",
     "The manuscript now labels 420 eV FWHM as an estimated energy resolution and simulation input without presenting it as a measured end-to-end detector property."),
    ("M17", "Concur; resolved by minimal terminology change",
     "The manuscript now calls the 49 percent single-layer and near-unity six-layer estimates interaction efficiencies without adding a separate efficiency discussion; it also no longer claims that Laue focusing enlarges sky coverage."),
    ("M18", "Concur; verified",
     "11.13 cm² / 0.739 = 15.1 cm² reproduces the instrument-only selected area."),
    ("M19", "Concur", "Version and normalization separation as requested."),
    ("M20", "Concur, with a design-intent nuance",
     "The permissive OR-over-81 rule is a defensible design choice and the single-site-only comparison (0.753 × S/√B) justifies keeping multi-hit events. The genuine gaps are benchmark transferability, the unreconstructed/>6-hit boundary rule, and the '10–14%' removal figure, which matches neither the baseline cut-flow (7.4% prompt, 0% delayed) nor exactly the final geometry (16.7%, 12.1%)."),
    ("M21", "Concur",
     "81 points define 80 intervals; N_k(0), time units, and the quadrature rule are unstated."),
    ("M22", "Concur",
     "The round-2 abstract deliberately rounds to supported precision; Figure 4a's six-significant-digit schematic labels are another instance of the same problem."),
    ("M23", "Concur",
     "N05 supplies the physical identity (an in-window 511 keV photon cannot leave a ≥50 keV shield deposit), so 'active coverage controls the dominant prompt and atmospheric paths' must be limited to prompt-particle paths."),
    ("S01", "Concur",
     "Clearest instances: the final shield dimensions appear in Section 3.3 before the Section 4.1 evidence; signal rates and cut-flow outcomes sit in Methods; the revan benchmark and the trajectory validation are Methods-embedded results."),
    ("S02", "Concur",
     "Round 2 adds the smaller-items list below (US/UK mixing, 'cps' versus s⁻¹ unit style, a caption fragment, schematic precision)."),
    ("J01", "Concur in part",
     "Concur on template, declarations, and availability. Caveat: the specific claim that EA uses an author–year alphabetized reference style could not be re-verified in this session (the Springer guidelines page was not reachable); authors should follow whatever the current submission system enforces — the action is unchanged."),
    ("J02", "Concur",
     "Add: the sparse spectra (Figures 5–7) should state bin width and per-bin Monte Carlo support, since many bins contain single weighted records."),
    ("J03", "Concur", "Check the policy at submission and disclose as required."),
]

# Round-2 PDF annotations: (id, kind, category, anchor, popup note).
# kind: "major" (violet), "moderate" (light violet), "response" (teal).
ANNOTATIONS_R2 = [
    ("N01", "major", "Dead time / shield rate", "live factor remains between 0.97165 and 0.97985",
     "Figure 4c defines L=exp(-R tau) but the text never does. At tau = 1 microsecond this live-factor range implies an unreported final-geometry full-band axis rate of about 20,000-29,000 s-1, 20-30x the baseline axis and presumably dominated by BGO shield counts. Accidental-veto loss then scales at 2-3 percent per microsecond of veto window, so a TES-compatible window of tens of microseconds becomes a first-order mission effect. Report the shield rate, define L in the text, and scan tau."),
    ("N02", "major", "Signal transmission", "plane-parallel slant depth",
     "T = 0.739 corresponds to a vertical column of about 3.5 g cm-2 near the 38.75 km anchor, but the optical axis points 45 degrees above the horizontal, where the slant column is 1.41x larger and T would be about 0.65 (about -12 percent signal, +13 percent on F3sigma). State the residual column, attenuation data, and viewing angle behind this value and behind T-atm,511(t)."),
    ("N03", "major", "Stream accounting", "require three source layers",
     "The abstract promises four transported streams under one selection, and the atmospheric 511 keV line is 26.59 percent of the final background, yet this section builds three source layers, Table 1 lists three, and the Section 3.4.1 coincidence axis carries only prompt/delayed/signal. State where the fourth stream enters the chain and how its veto/topology columns in Table 5 were produced."),
    ("N04", "moderate", "MC allocation", "generated with replicated samples",
     "This allocation backfired downstream: by the Table 6 weights, each non-photon family carries about 1,500 s of equivalent exposure but photons only about 184 s, and the zero-count photon term now dominates the conservative bound. Report equivalent exposure per family and rebalance transport toward prompt photons."),
    ("N05", "moderate", "Selection physics", "can look exactly like a source photon",
     "Stronger than 'can look': for a monochromatic 511 keV photon an in-window TES sum leaves at most about 0.4 keV unaccounted, so no 50 keV shield deposit can coexist. The 100 percent active-veto survival of the signal and atmospheric-line rows is exact, not sampled; the anticoincidence layer is structurally blind to this component (supports M23)."),
    ("N06", "moderate", "Isomeric states", "ground-state half-lives checked",
     "Production records carry excitation energy and matching is by excitation state, but only ground-state half-lives are said to be checked. State how isomeric populations are treated in the accumulation equation (separate decay constant, prompt de-excitation, or exclusion) and their share of the day-15 inventories."),
    ("N07", "moderate", "Citation support", "dedicated INTEGRAL/IBIS compact-source search",
     "The references cited for this point-source limit are diffuse-emission analyses; the dedicated compact-source search cited in this paragraph is IBIS. Use its Gaussian-rescaled 3-sigma-equivalent limit and fold it with the stated atmospheric transmission to define the single payload-plane observational reference flux, independently of the Monte Carlo normalization."),
    ("N08", "moderate", "Abstract comparability", "Complete selection gave",
     "These final-geometry rates follow a reference-geometry rate quoted two sentences earlier with different shield material, delayed-family scope, and stream content; as written the abstract invites reading an 8x shield improvement. Add the scope qualifiers here or present a like-for-like pair (see M15)."),
    ("N09", "moderate", "Reference exposure", "event instances yield 1275 mixed-stream coincidences",
     "Self-consistent but undocumented: 2 tau T sum(Rk Rl) reproduces 1275 only with T of about 7,000 s, which is never stated. Give the reference duration, per-stream instance counts, and the group-size distribution; the mixed-group attribution rule of M09 belongs here too."),
    ("N10", "moderate", "Definitions", "condition corresponding to",
     "Define W (solar-activity index and units), give its data source for 2025-08-31, and state how sensitive the eight family fluxes are to it across the flight window."),
    ("Re-M02", "response", "Post-review audit correction", "kept fixed throughout the final-geometry calculation",
     "The 2026-08-04 data-lineage audit overturns this round-2 inference: sub-80-keV CC HIT deposits are serialized, 50-80-keV event sums are available to the analysis, and the final mask applies 50 keV offline. Future review must trace the consuming parser and mask rather than infer a storage gate from the detector-map field."),
    ("Re-M08", "response", "Diffraction construction", "each sample interaction lengths in the same competition framework",
     "Sharpening M08: in this competition the first-interaction probability is (LD/(LD+LA)) x (1-exp(-(LD+LA))), which does not reduce to the target R after the R/(1-A) rescaling except in weak-absorption limits. XOP mosaic reflectivity already folds crystallite absorption and mosaic width, so the added Gaussian plane perturbation risks double counting. Benchmark slab R/T/A and outgoing angles against XOP, and state A-inc."),
    ("Re-M09", "response", "Axis normalization", "single detector time axis carrying the three",
     "On M09: 'the three physical rates' is wrong for the signal, which rides this axis as unit replay at about 660x its physical rate. Its share is only 0.1 percent of the axis rate, so the live factor is barely affected; the substantive fixes are the wording, the mixed-group attribution rule, and excluding signal from background accidental bookkeeping."),
]

# Smaller round-2 items (HTML only; not worth PDF clutter).
SMALLER_ITEMS_R2 = [
    ("13", "Figure 6's caption ends in a fragment ('Shape-diagnostic re-derivation on the surviving reference-detector catalogues.'). Rewrite as a full sentence stating what was re-derived and how it is normalized."),
    ("13, 15", "The topology layer is said to remove 'about 10–14% of the background', which matches neither the baseline cut-flow (7.4% prompt, 0% delayed) nor exactly the final geometry (16.7%, 12.1%). State which geometry and selection the range describes."),
    ("throughout", "US/UK spelling is mixed: 'behavior' (p. 14) vs 'behaviour' (p. 21); 'modeled' vs 'modelled'; figure axes use 'cps keV⁻¹' while the text uses s⁻¹. Adopt US English and one rate-unit convention."),
    ("11", "Figure 4a prints six-significant-digit rates (927.909, 97.1211, 0.98661 s⁻¹) on a schematic; round to supported precision (M22)."),
    ("11", "The live-factor definition L = e^(−Rτ) appears only inside the Figure 4c box; define it in the text (see N01)."),
    ("17, 21", "¹²⁸I, the dominant inventory activity, is first named in the Discussion; give the nuclide-level inventory shares in Section 4.1 where the material shares appear."),
    ("9", "'North-sky/near-zenith reference' describes a 45°-elevation axis, which is mid-sky rather than near-zenith; align the wording with the stated geometry (and with N02)."),
    ("6", "W = 118.3 is undefined at first use; define the symbol and its data source (also PDF note N10)."),
    ("1", "Abstract: 'finite-Monte-Carlo conservative calculation' should name the method — component-wise 95% counting endpoints propagated through the trajectory."),
    ("22", "'Data and software availability' is currently a promise ('should provide'); EA expects a present-tense statement with a persistent identifier at submission (J01)."),
]


LANGUAGE_EDITS = [
    ("1", "The mass-complete reference geometry locates the physical origins…", "In the mass-complete detector–cryostat reference geometry, selected events were decomposed by incident particle, parent nuclide, and production volume."),
    ("1", "This particle- and material-resolved map led to…", "These decompositions informed a BGO shield with side, bottom, and top thicknesses of 40, 30, and 10 mm."),
    ("1", "finite-Monte-Carlo conservative calculation", "conservative calculation based on finite-sample counting endpoints"),
    ("1", "The study connects…", "Replace the generic conclusion with the dominant qualification: limited prompt-photon Monte Carlo statistics."),
    ("2", "These studies show that the design question is not only…", "Shield design must account for the directions and materials that generate analysis-window events, as well as total shield mass."),
    ("2", "This order connects… in one traceable chain.", "The selected-event decomposition determines the shield design, and the selected rates determine the exposure projection."),
    ("3", "This work first considers a balloon payload…", "We evaluate the balloon payload as a precursor to a possible satellite implementation."),
    ("3", "larger solid angle can be covered…", "photons collected over the lens aperture are concentrated on a small detector area"),
    ("3", "Based on laboratory experience and by substituting…", "Using a Ta absorber heat capacity of 67.5 pJ K⁻¹ as an input assumption, we adopt a 420 eV FWHM response at 511 keV."),
    ("3", "In the current manuscript…", "The analysis uses W₅₁₁ = 510.58–511.42 keV."),
    ("4", "reaching the focal-plane plane", "reaching the focal plane"),
    ("5", "This simulation adopts a laue-lens system…", "We model a Ge(111) mosaic-crystal Laue lens with a 10 m focal length, a single ring tuned to 511 keV, and an on-axis effective area of 20.1 cm²."),
    ("5", "adopted to make the Monte Carlo calculation convenient", "Replace with the physical reason for selecting a mosaic-crystal design."),
    ("6", "preferentially given by interpolation", "We obtain R(|Δθ|) by interpolating an XOP/CRYSTAL rocking-curve table generated during preprocessing."),
    ("6", "offline library tabulation… / process class only handles…", "The transport interface is separated from the model that evaluates diffraction probability and outgoing direction."),
    ("6", "After the focusing optics have been defined…", "The calculation uses independently constructed prompt-atmospheric, accumulated-activation, atmospheric-line, and reference-source streams."),
    ("8", "Whether the production positions are worth preserving…", "We quantified the dependence of activation location on incident particle family using total-variation distance."),
    ("8", "need not deposit their activation in the same materials", "need not produce the same material-resolved activation inventory"),
    ("8", "The delayed-decay source is therefore emitted…", "Delayed decays are sampled at recorded production positions rather than from an axisymmetric distribution."),
    ("8", "It is placed in the source-model section because…", "Delete this drafting explanation."),
    ("9", "Three independent seeds… give… of which…", "Split transport count, aperture acceptance, and spot-size results into separate sentences."),
    ("10", "described by one physical question", "State the directional design criterion directly."),
    ("10", "transparent counting metric / diagnostic threshold", "counting metric / counting-based 3σ reference threshold"),
    ("11", "single detector time axis carrying the three physical rates", "Separate physical background rates from the unit-replay signal-catalogue rate."),
    ("11–12", "line-dominated, with a starved continuum", "the line dominates and the Monte Carlo continuum is sparsely sampled"),
    ("11", "The superposition is licensed by…", "The superposition assumes stationary rates over the short reference interval; day-scale evolution is handled by the trajectory fold."),
    ("12", "hard line window", "fixed 511 keV analysis window"),
    ("12", "intrinsic width, after detector response", "response-convolved source profile"),
    ("13", "i.e. whether the reconstructed arrival direction…", "that is, when the reconstructed arrival direction is consistent with entry through the aperture"),
    ("13", "8+1=9 representative points", "nine representative points—the centroid and eight corners"),
    ("14", "Unreconstructed events remain…", "State explicitly whether unreconstructed events pass or fail the final FoV selection."),
    ("14", "reducing… to 0.753 of the baseline value", "reducing S/√B to 75.3% of its baseline value"),
    ("15", "retained legacy geometry", "Name the geometry and justify transferability, or remove this benchmark from the validation claim."),
    ("16", "within 2σ (maximum |z| ≃ 0.51)", "agreed with the prediction, with maximum |z| = 0.51"),
    ("16", "These multi-point results anchor…", "These transports test e⁺, neutron, and photon modulation; the remaining families use analytic source-field reweighting."),
    ("16", "tells us / makes the prompt result easy to read", "identifies / Figure 8 shows the prompt decomposition"),
    ("17", "different source-level and detector-selected distribution", "The material distribution of the source inventory differs from that of the selected delayed events."),
    ("17–18", "keeps the optical route easy to read / three linked views", "State the beam-path and outer-shield geometry directly; delete the meta-commentary."),
    ("19", "can look exactly like a source photon", "is indistinguishable from a focused source photon under the energy and topology selections"),
    ("19", "remaining budget naturally becomes a mixture", "The remaining modeled background comprises prompt leakage, the atmospheric line, and neutron-induced activation."),
    ("19", "64 deterministic response seeds / preregistered primary value", "64 fixed response seeds / pre-specified primary seed"),
    ("20", "The two columns answer two useful questions.", "The central column uses estimated rates; the conservative column substitutes component-wise finite-sample endpoints."),
    ("20", "it shows exactly where additional…", "The separation is dominated by the zero-count, high-weight prompt-photon component."),
    ("21", "The main result is a connected physical explanation…", "Begin directly with the supported prompt-versus-delayed design distinction."),
    ("21", "responds to the first pattern / treats the second", "Repeat the nouns: prompt background and cold-copper activation."),
    ("21", "This ordering follows the strongest lesson…", "This component-based approach is consistent with the cited COSI and DIXE studies."),
    ("21", "That 26.59% residual is not a failure…", "Anticoincidence does not suppress this component because its energy and single-photon topology match those of the source."),
    ("21", "Scope and next steps", "Limitations and next steps"),
    ("22", "Before publication… should provide", "The geometry, source definitions, seeds, analysis code, and derived products are available at [versioned repository/DOI]."),
]


STRENGTHS = [
    "The paper asks an instrumentation question that fits Experimental Astronomy well: how transported prompt particles, activation, shielding, and event selection determine a 511 keV focal-plane background.",
    "The reference-geometry decomposition by incident family, isotope, and production volume is physically informative and leads to testable design hypotheses.",
    "Signal and background are generally passed through a common detector-response and selection vocabulary, and the cut-flow tables expose Monte Carlo support rather than reporting rates alone.",
    "The manuscript already acknowledges several important limitations—neutron-only final activation, a synthetic trajectory, and finite prompt statistics. The revision should promote those caveats from late qualifications to governing scope statements.",
]


PRIORITY_ACTIONS = [
    "Keep the closed M02 lineage audit fixed: the graded-shield cut-flow uses a 50 keV offline deposited-energy veto and needs no native-threshold rerun.",
    "Complete all-family activation and specify/validate the atmospheric 511 keV source without double counting.",
    "Make the detector–cryostat versus full-payload scope explicit; transport or bound omitted payload masses.",
    "Provide a mass-constrained shield trade study and the actual BGO/payload mass.",
    "Validate the Laue process against XOP/CRYSTAL and publish the transport configuration.",
    "Increase final prompt statistics and use a joint likelihood that propagates Monte Carlo and background nuisance parameters.",
    "Replace the continuously on-source synthetic fold with a visibility/slant-depth/pointing model, or present it only as a reference exposure.",
    "Reorganize the paper and complete Springer/EA formatting, references, availability, and declarations.",
]


RESTRUCTURE = [
    ("1", "Introduction", "Science gap, one quantitative objective, and a precise statement that this is a detector–cryostat concept study."),
    ("2", "Instrument concept and modeled assumptions", "Laue lens, TES absorber stack, cryostat, shield, masses, and a table distinguishing measured, calculated, and assumed inputs."),
    ("3", "Methods", "Four source streams; transport configuration; response; coincidence and veto rules; topology; normalization; statistical model; trajectory/exposure model."),
    ("4", "Validation and design protocol", "Laue slab tests, source/normalization checks, current-geometry topology benchmark, trajectory-state tests, shield candidate set and objective."),
    ("5", "Results", "Reference origin map → independent shield trade study → paired final cut-flow → uncertainty-aware reference-exposure performance."),
    ("6", "Discussion", "Comparison with prior instruments, engineering feasibility, systematic budget, applicability to the Galactic-centre science case, limitations."),
    ("7", "Conclusions", "Short numerical summary with the same scope qualifiers as the abstract."),
]


def tex_note(text: str) -> str:
    """Make a conservative PDF-comment string that is safe in a TeX argument."""
    replacements = {
        "\\": "/",
        "%": " percent",
        "&": " and ",
        "#": "number ",
        "_": "-",
        "{": "(",
        "}": ")",
        "×": "x",
        "√": "sqrt",
        "μ": "micro",
        "σ": "sigma",
        "⁻": "-",
        "¹": "1",
        "²": "2",
        "³": "3",
        "⁴": "4",
        "⁶": "6",
        "⁸": "8",
        "–": "--",
        "—": "--",
        "’": "'",
        "“": "'",
        "”": "'",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def markup(annotation_id: str, category: str, anchor: str, note: str) -> str:
    review = next(item for item in REVIEWS if item.rid == annotation_id)
    colors = {
        "Major": "1 0.48 0.48",
        "Moderate": "1 0.78 0.36",
        "Structural": "0.48 0.72 1",
        "Journal": "0.62 0.86 0.62",
    }
    color = colors[review.severity]
    subject = tex_note(f"{annotation_id} | {category}")
    body = tex_note(f"{annotation_id}. {note} Full rationale and action: HTML review report.")
    return (
        "\\pdfmarkupcomment[markup=Highlight,"
        f"color={{{color}}},author={{Peer reviewer}},subject={{{subject}}}]"
        f"{{{anchor}}}{{{body}}}"
    )


R2_COLORS = {
    "major": "0.72 0.55 0.95",      # violet: new round-2 major finding
    "moderate": "0.85 0.74 0.98",   # light violet: new round-2 moderate finding
    "response": "0.45 0.85 0.82",   # teal: round-2 response to a round-1 item
}


def markup_r2(annotation_id: str, kind: str, category: str, anchor: str, note: str) -> str:
    subject = tex_note(f"{annotation_id} | round 2 | {category}")
    body = tex_note(f"{annotation_id}. {note} Full rationale: HTML report, round-2 addendum.")
    return (
        "\\pdfmarkupcomment[markup=Highlight,"
        f"color={{{R2_COLORS[kind]}}},author={{Peer reviewer - round 2}},subject={{{subject}}}]"
        f"{{{anchor}}}{{{body}}}"
    )


def build_annotated_tex() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    package_anchor = "\\hypersetup{hidelinks}"
    if package_anchor not in source:
        raise RuntimeError("Could not locate hyperref setup for pdfcomment insertion")
    source = source.replace(
        package_anchor,
        package_anchor
        + "\n\\usepackage{pdfcomment}\n"
        + "% Highlight colours: red major, orange moderate, blue structural, green journal.\n",
        1,
    )

    failures: list[str] = []
    for annotation_id, category, anchor, note, occurrence in ANNOTATIONS:
        if annotation_id in RESOLVED_REVIEW_IDS:
            continue
        found = source.count(anchor)
        if found < occurrence:
            failures.append(f"{annotation_id}: expected occurrence {occurrence} of {anchor!r}; found {found}")
            continue
        # Replace the requested occurrence without altering earlier matches.
        start = -1
        cursor = 0
        for _ in range(occurrence):
            start = source.find(anchor, cursor)
            cursor = start + len(anchor)
        source = source[:start] + markup(annotation_id, category, anchor, note) + source[start + len(anchor):]

    if failures:
        raise RuntimeError("Annotation anchors failed:\n" + "\n".join(failures))

    r2_failures: list[str] = []
    for annotation_id, kind, category, anchor, note in ANNOTATIONS_R2:
        start = source.find(anchor)
        if start < 0:
            r2_failures.append(f"{annotation_id}: anchor not found: {anchor!r}")
            continue
        source = source[:start] + markup_r2(annotation_id, kind, category, anchor, note) + source[start + len(anchor):]

    if r2_failures:
        raise RuntimeError("Round-2 annotation anchors failed:\n" + "\n".join(r2_failures))

    header = dedent(
        f"""
        % ======================================================================
        % Peer-review overlay generated {REVIEW_DATE}.
        % Baseline: {BASELINE_PDF}
        % Manuscript text is unchanged; only PDF highlight annotations are added.
        % Annotation IDs map to ea_peer_review_report.html.
        % Round 1 colours: red major, orange moderate, blue structural, green journal.
        % Round 2 ({R2_REVIEW_DATE}): additional highlights by author
        % 'Peer reviewer - round 2'. Colours: violet new major, light violet new
        % moderate, teal response to a round-1 item. IDs N01-N10 and Re-Mxx map
        % to the round-2 addendum of the same HTML report.
        % ======================================================================
        """
    ).lstrip()
    ANNOTATED_TEX.write_text(header + source, encoding="utf-8")


def nav_link(label: str, target: str) -> str:
    return f'<a href="#{escape(target)}">{escape(label)}</a>'


def review_card(review: Review) -> str:
    sev_class = review.severity.lower()
    return f"""
    <article class="review-card {sev_class}" id="{escape(review.rid)}" data-severity="{escape(review.severity)}" data-category="{escape(review.category)}">
      <div class="review-head">
        <span class="rid">{escape(review.rid)}</span>
        <span class="pill {sev_class}">{escape(review.severity)}</span>
        <span class="category">{escape(review.category)}</span>
        <span class="pages">PDF p. {escape(review.pages)}</span>
      </div>
      <h3>{escape(review.title)}</h3>
      <p><strong>Finding.</strong> {escape(review.finding)}</p>
      <p><strong>Required revision.</strong> {escape(review.action)}</p>
      <p class="basis"><strong>Basis.</strong> {escape(review.basis)}</p>
    </article>
    """


def review_card_r2(review: Review) -> str:
    sev_class = review.severity.lower()
    return f"""
    <article class="review-card {sev_class} r2" id="{escape(review.rid)}" data-severity="{escape(review.severity)}" data-category="{escape(review.category)}">
      <div class="review-head">
        <span class="rid">{escape(review.rid)}</span>
        <span class="pill {sev_class}">{escape(review.severity)}</span>
        <span class="pill r2">Round 2</span>
        <span class="category">{escape(review.category)}</span>
        <span class="pages">PDF p. {escape(review.pages)}</span>
      </div>
      <h3>{escape(review.title)}</h3>
      <p><strong>Finding.</strong> {escape(review.finding)}</p>
      <p><strong>Required revision.</strong> {escape(review.action)}</p>
      <p class="basis"><strong>Basis.</strong> {escape(review.basis)}</p>
    </article>
    """


def build_html() -> None:
    major_count = sum(r.severity == "Major" for r in REVIEWS)
    moderate_count = sum(r.severity == "Moderate" for r in REVIEWS)
    structural_count = sum(r.severity == "Structural" for r in REVIEWS)
    journal_count = sum(r.severity == "Journal" for r in REVIEWS)

    strengths_html = "".join(f"<li>{escape(item)}</li>" for item in STRENGTHS)
    priorities_html = "".join(f"<li>{escape(item)}</li>" for item in PRIORITY_ACTIONS)
    cards_html = "\n".join(review_card(r) for r in REVIEWS)
    language_rows = "\n".join(
        f"<tr><td>{escape(page)}</td><td>{escape(anchor)}</td><td>{escape(replacement)}</td></tr>"
        for page, anchor, replacement in LANGUAGE_EDITS
    )
    restructure_rows = "\n".join(
        f"<tr><td>{escape(number)}</td><td><strong>{escape(heading)}</strong></td><td>{escape(content)}</td></tr>"
        for number, heading, content in RESTRUCTURE
    )

    r2_major_count = sum(r.severity == "Major" for r in REVIEWS_R2)
    r2_moderate_count = sum(r.severity == "Moderate" for r in REVIEWS_R2)
    r2_cards_html = "\n".join(review_card_r2(r) for r in REVIEWS_R2)

    stance_row_parts = []
    for rid, stance, note in R1_STANCES:
        cls = "nuance" if (stance.startswith("Concur,") or "in part" in stance) else "agree"
        stance_row_parts.append(
            f'<tr><td><a href="#{escape(rid)}">{escape(rid)}</a></td>'
            f'<td class="stance {cls}">{escape(stance)}</td>'
            f"<td>{escape(note)}</td></tr>"
        )
    stance_rows = "\n".join(stance_row_parts)

    smaller_rows = "\n".join(
        f"<tr><td>{escape(page)}</td><td>{escape(text)}</td></tr>"
        for page, text in SMALLER_ITEMS_R2
    )

    r2_section = f"""
      <section id="round2">
        <h2>Round 2 addendum — incremental review ({escape(REVIEW_DATE)})</h2>
        <div class="panel r2panel">
          <p><strong>Round-2 verdict: concur with major revision.</strong> The original addendum was prepared from the same English manuscript only, without project simulation products. It contributed {r2_major_count} new major and {r2_moderate_count} new moderate findings (N01–N10), three PDF-anchored responses to round-1 items (Re-M02, Re-M08, Re-M09), a position on each of the {len(R1_STANCES)} round-1 findings, and an alternative title and abstract. A later project data-lineage audit on 4 August 2026 corrected and closed M02; that correction supersedes the original M02 and Re-M02 inference.</p>
          <p><strong>Independently verified in round 2</strong> — the manuscript's arithmetic is unusually self-consistent; the review problems are scope, missing method documentation, and hardware realism, not algebra: every cut-flow product (records × weight) in Tables 2–6; the Garwood and Clopper–Pearson endpoints and their sums; Z = 18.574 and F₃σ = 1.615×10⁻⁵ from the quoted counts; the closure S = F₀·A_eff·T·ε_det with ε_det = 27901/37194 = 0.750; the 96.84% and 89.13% origin shares; the 0.753 single-site S/√B factor; the accidental-coincidence count (1275 from 2τT·ΣR_kR_l); the M06 window-retention fractions; and the M07 ≈298 kg BGO shell mass.</p>
          <p><strong>Two additions to the round-1 priority sequence:</strong></p>
          <ol>
            <li>Report the final-geometry full-band and shield counting rates, define the live factor in the text, and scan the mission result against the veto window τ (N01) — this remains independent of the closed M02 data-lineage issue.</li>
            <li>Document the atmospheric-transmission model (column, angle, data source) behind T = 0.739 and T<sub>atm,511</sub>(t), and reconcile it with the 45° viewing geometry (N02) — this belongs beside the observing-geometry item.</li>
          </ol>
          <p class="note">Round-2 PDF markings: <strong>violet</strong> = new major finding (N01–N03), <strong>light violet</strong> = new moderate finding (N04–N10), <strong>teal</strong> = round-2 response placed beside a round-1 highlight (Re-M02, Re-M08, Re-M09). PDF author field: “Peer reviewer — round 2”.</p>
        </div>

        <h3>New findings (N01–N10)</h3>
        <div id="r2Cards">{r2_cards_html}</div>

        <h3>Positions on the round-1 findings</h3>
        <p class="note">Each round-1 item was re-derived from the paper before comparison, so the concurrences below are independent confirmations rather than deference; the nuances state where round 2 reads the evidence differently.</p>
        <div class="table-wrap"><table><thead><tr><th>ID</th><th>Round-2 position</th><th>Note</th></tr></thead><tbody>{stance_rows}</tbody></table></div>

        <h3>Round-2 recommended title and abstract</h3>
        <p class="note">Differences from the round-1 proposal, for the authors to arbitrate: (i) round 2 keeps the TES focal plane in the title — it is the paper's distinguishing hardware and a term EA readers will search; (ii) round 2 rounds the abstract numbers to supported precision, which the round-1 abstract (4.643 ± 0.543, 4.072 × 10⁻³, …) does not do despite its own M22 recommendation; (iii) round 2 spends its words on the toolchain and the three named selection layers rather than the veto-stage rate pair; (iv) both versions carry the neutron-only delayed scope and the synthetic-trajectory caveat, and those must survive any merge. The round-2 abstract is ≈215 words, within the journal's 150–250 range.</p>
        <div class="rewrite">
          <div class="label">Round-2 recommended title</div>
          <h3 id="titleTextR2">{escape(R2_REVISED_TITLE)}</h3>
          <button type="button" onclick="copyText('titleTextR2', this)">Copy title</button>
        </div>
        <div class="rewrite" style="margin-top:14px">
          <div class="label">Round-2 recommended abstract</div>
          <p class="abstract" id="abstractTextR2">{escape(R2_REVISED_ABSTRACT)}</p>
          <button type="button" onclick="copyText('abstractTextR2', this)">Copy abstract</button>
        </div>

        <h3>Smaller round-2 items</h3>
        <div class="table-wrap"><table><thead><tr><th>PDF page</th><th>Item</th></tr></thead><tbody>{smaller_rows}</tbody></table></div>
      </section>
"""

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Peer-review report | Balloon-borne 511 keV Laue-lens TES manuscript</title>
  <style>
    :root {{
      --ink: #192538; --muted: #607086; --paper: #fbfcfe; --panel: #ffffff;
      --line: #dbe3ed; --navy: #153b66; --blue: #2f6fad; --red: #a8232f;
      --red-bg: #fff0f1; --orange: #98530a; --orange-bg: #fff7e8;
      --green: #2e6c47; --green-bg: #eef8f1; --struct: #315f94; --struct-bg: #eef5fd;
      --shadow: 0 10px 30px rgba(22, 44, 72, .08);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ margin: 0; color: var(--ink); background: var(--paper); font: 16px/1.62 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    a {{ color: var(--blue); text-decoration-thickness: .08em; text-underline-offset: .16em; }}
    header {{ color: white; background: linear-gradient(125deg, #0f2f52, #1e5689 58%, #39759c); padding: 54px max(24px, calc((100vw - 1180px)/2)); }}
    header .eyebrow {{ letter-spacing: .11em; text-transform: uppercase; font-size: .79rem; opacity: .82; }}
    header h1 {{ max-width: 970px; margin: .5rem 0 .8rem; font: 700 clamp(2rem, 4.3vw, 3.8rem)/1.08 Georgia, serif; }}
    header .meta {{ display: flex; flex-wrap: wrap; gap: .55rem 1.25rem; color: #deebf6; }}
    .layout {{ display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 32px; max-width: 1240px; margin: 0 auto; padding: 32px 24px 80px; }}
    aside {{ position: sticky; top: 16px; align-self: start; max-height: calc(100vh - 32px); overflow: auto; background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 18px; box-shadow: var(--shadow); }}
    aside strong {{ display: block; margin-bottom: 8px; }}
    aside a {{ display: block; padding: 6px 8px; color: #334a64; text-decoration: none; border-radius: 7px; }}
    aside a:hover {{ background: #eef4fa; }}
    main {{ min-width: 0; }}
    section {{ scroll-margin-top: 18px; margin-bottom: 34px; }}
    h2 {{ margin: 0 0 14px; color: var(--navy); font: 700 1.7rem/1.25 Georgia, serif; }}
    h3 {{ color: var(--navy); line-height: 1.3; }}
    .hero-grid, .stats {{ display: grid; gap: 16px; }}
    .hero-grid {{ grid-template-columns: 1.2fr .8fr; }}
    .stats {{ grid-template-columns: repeat(4, 1fr); margin: 16px 0; }}
    .panel, .stat, .review-card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; box-shadow: var(--shadow); }}
    .panel {{ padding: 24px; }}
    .verdict {{ border-left: 7px solid var(--red); }}
    .verdict .big {{ color: var(--red); font: 700 2rem/1.1 Georgia, serif; }}
    .stat {{ padding: 17px; text-align: center; }}
    .stat b {{ display: block; color: var(--navy); font-size: 1.65rem; }}
    .stat span {{ color: var(--muted); font-size: .84rem; }}
    .note {{ color: var(--muted); font-size: .92rem; }}
    .callout {{ border-left: 5px solid var(--blue); background: #edf6ff; padding: 16px 19px; border-radius: 8px; }}
    .rewrite {{ background: #f5f8fc; border: 1px solid #cfdbea; border-radius: 13px; padding: 19px; }}
    .rewrite .label {{ color: var(--muted); text-transform: uppercase; letter-spacing: .08em; font-size: .76rem; }}
    .rewrite h3 {{ margin: .45rem 0 .8rem; font: 700 1.35rem/1.35 Georgia, serif; }}
    .abstract {{ font-family: Georgia, serif; font-size: 1.03rem; }}
    button {{ border: 1px solid #91a8c1; background: white; color: var(--navy); border-radius: 8px; padding: 8px 11px; cursor: pointer; }}
    button:hover {{ background: #edf4fb; }}
    .toolbar {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0 18px; }}
    .toolbar button.active {{ background: var(--navy); color: white; border-color: var(--navy); }}
    .review-card {{ padding: 20px 22px; margin: 14px 0; border-left-width: 7px; }}
    .review-card.major {{ border-left-color: var(--red); }}
    .review-card.moderate {{ border-left-color: var(--orange); }}
    .review-card.structural {{ border-left-color: var(--struct); }}
    .review-card.journal {{ border-left-color: var(--green); }}
    .review-head {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; color: var(--muted); font-size: .85rem; }}
    .rid {{ font-weight: 800; color: var(--navy); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .pill {{ padding: 2px 8px; border-radius: 999px; font-weight: 700; }}
    .pill.major {{ color: var(--red); background: var(--red-bg); }}
    .pill.moderate {{ color: var(--orange); background: var(--orange-bg); }}
    .pill.structural {{ color: var(--struct); background: var(--struct-bg); }}
    .pill.journal {{ color: var(--green); background: var(--green-bg); }}
    .pill.r2 {{ color: #5b2d8e; background: #f1e8fb; }}
    .review-card.r2 {{ border-left-style: double; }}
    .r2panel {{ border-left: 7px solid #6b3fa0; }}
    .stance {{ font-weight: 700; }}
    .stance.agree {{ color: var(--green); }}
    .stance.nuance {{ color: var(--orange); }}
    .review-card h3 {{ margin: .65rem 0; font-size: 1.16rem; }}
    .review-card p {{ margin: .55rem 0; }}
    .basis {{ color: var(--muted); font-size: .89rem; }}
    table {{ width: 100%; border-collapse: collapse; background: white; font-size: .92rem; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 11px 12px; vertical-align: top; text-align: left; }}
    th {{ position: sticky; top: 0; color: white; background: var(--navy); }}
    .table-wrap {{ max-height: 720px; overflow: auto; border: 1px solid var(--line); border-radius: 12px; box-shadow: var(--shadow); }}
    code {{ background: #edf1f5; border-radius: 4px; padding: .08em .35em; }}
    footer {{ border-top: 1px solid var(--line); color: var(--muted); padding: 28px 24px 55px; text-align: center; }}
    .hidden {{ display: none; }}
    @media (max-width: 900px) {{ .layout {{ display: block; }} aside {{ position: static; max-height: none; margin-bottom: 24px; }} .hero-grid {{ grid-template-columns: 1fr; }} .stats {{ grid-template-columns: repeat(2, 1fr); }} }}
    @media (max-width: 520px) {{ .stats {{ grid-template-columns: 1fr; }} header {{ padding: 38px 20px; }} .layout {{ padding: 22px 14px 60px; }} }}
    @media print {{ header {{ padding: 26px; }} .layout {{ display: block; padding: 16px; }} aside, .toolbar, button {{ display: none !important; }} .panel, .stat, .review-card {{ box-shadow: none; break-inside: avoid; }} .table-wrap {{ max-height: none; overflow: visible; }} th {{ position: static; }} a {{ color: inherit; }} }}
  </style>
</head>
<body>
  <header>
    <div class="eyebrow">Paper-only peer review · Experimental Astronomy target</div>
    <h1>Detector-coupled 511 keV Laue-lens TES manuscript</h1>
    <div class="meta"><span>Recommendation: major revision</span><span>Baseline: {escape(BASELINE_PDF)}</span><span>{escape(REVIEW_DATE)}</span><span>English manuscript only</span><span>Round 2 addendum included</span></div>
  </header>

  <div class="layout">
    <aside aria-label="Report navigation">
      <strong>Navigate</strong>
      {nav_link("Executive verdict", "verdict")}
      {nav_link("Round 2 addendum", "round2")}
      {nav_link("Rewritten title & abstract", "rewrite")}
      {nav_link("Priority revision sequence", "priorities")}
      {nav_link("Detailed review", "detailed")}
      {nav_link("Proposed structure", "structure")}
      {nav_link("Language edit ledger", "language")}
      {nav_link("EA compliance", "journal")}
      {nav_link("Evidence & scope", "scope")}
    </aside>

    <main>
      <section id="verdict">
        <div class="hero-grid">
          <div class="panel verdict">
            <div class="big">Major revision</div>
            <p><strong>Outcome first:</strong> the topic is a strong fit for <em>Experimental Astronomy</em>, and the reference-geometry origin analysis has publishable potential. A later project audit closed the original M02 threshold concern: the final selection uses complete CC HIT deposits and a 50 keV offline veto. The remaining scope issues include atmospheric-line documentation, omitted full-payload contributions, finite statistics, detector timing, and the continuously on-axis synthetic exposure.</p>
            <p>The most important revision is therefore a correction of scientific scope and evidence, not cosmetic English polishing.</p>
          </div>
          <div class="panel">
            <h2>What already works</h2>
            <ul>{strengths_html}</ul>
          </div>
        </div>
        <div class="stats">
          <div class="stat"><b>{major_count}</b><span>major scientific issues</span></div>
          <div class="stat"><b>{moderate_count}</b><span>moderate issues</span></div>
          <div class="stat"><b>{structural_count}</b><span>structure/flow reviews</span></div>
          <div class="stat"><b>{journal_count}</b><span>journal-readiness reviews</span></div>
        </div>
        <div class="callout"><strong>How to use the files.</strong> The annotated PDF contains {len(ANNOTATIONS) + len(ANNOTATIONS_R2)} clickable highlight comments: {len(ANNOTATIONS)} from round 1 and {len(ANNOTATIONS_R2)} from round 2. Each popup begins with an identifier such as <code>M03</code> or <code>N01</code>; the same identifier opens the full rationale in the detailed-review section or in the round-2 addendum. Round 1: red = major, orange = moderate, blue = structure/language, green = journal compliance. Round 2 (author “Peer reviewer — round 2”): violet = new major, light violet = new moderate, teal = response to a round-1 finding.</div>
      </section>
{r2_section}
      <section id="rewrite">
        <h2>Rewritten title and abstract</h2>
        <p class="note">This version follows the current evidence and deliberately uses “reference sensitivity.” Replace it with “point-source sensitivity” only after completing the missing background and observing-geometry work. The abstract is unstructured, within the journal’s 150–250-word requirement, defines bismuth germanate and full width at half maximum, and carries the two scope limitations that currently govern the result.</p>
        <div class="rewrite">
          <div class="label">Recommended title</div>
          <h3 id="titleText">{escape(REVISED_TITLE)}</h3>
          <button type="button" onclick="copyText('titleText', this)">Copy title</button>
        </div>
        <div class="rewrite" style="margin-top:14px">
          <div class="label">Recommended abstract</div>
          <p class="abstract" id="abstractText">{escape(REVISED_ABSTRACT)}</p>
          <button type="button" onclick="copyText('abstractText', this)">Copy abstract</button>
        </div>
      </section>

      <section id="priorities">
        <h2>Priority revision sequence</h2>
        <div class="panel"><ol>{priorities_html}</ol></div>
      </section>

      <section id="detailed">
        <h2>Detailed review ledger</h2>
        <p>Filter the ledger by severity. All comments are retained in the page; filtering only changes the display.</p>
        <div class="toolbar" role="group" aria-label="Filter reviews">
          <button class="active" type="button" data-filter="All">All</button>
          <button type="button" data-filter="Major">Major</button>
          <button type="button" data-filter="Moderate">Moderate</button>
          <button type="button" data-filter="Structural">Structural</button>
          <button type="button" data-filter="Journal">Journal</button>
        </div>
        <div id="reviewCards">{cards_html}</div>
      </section>

      <section id="structure">
        <h2>Recommended manuscript architecture</h2>
        <p>The paper’s underlying logic is strongest when the evidence runs in one direction: source model → validated response and selection → predefined design trade → independent final result → scoped exposure projection.</p>
        <div class="table-wrap"><table><thead><tr><th>#</th><th>Section</th><th>Content and purpose</th></tr></thead><tbody>{restructure_rows}</tbody></table></div>
      </section>

      <section id="language">
        <h2>Language and flow edit ledger</h2>
        <p>These are targeted examples, not a substitute for a final line edit after the scientific structure is corrected. Apply one English convention consistently; US English is suggested here because “modeling” and “Galactic center” dominate the proposed title and science phrasing.</p>
        <div class="table-wrap"><table><thead><tr><th>PDF page</th><th>Current anchor</th><th>Recommended revision or action</th></tr></thead><tbody>{language_rows}</tbody></table></div>
      </section>

      <section id="journal">
        <h2>Experimental Astronomy readiness</h2>
        <div class="panel">
          <p><strong>Scope:</strong> strong match. The journal explicitly covers astrophysical instrumentation, detection techniques, and analysis methods across electromagnetic astronomy, including gamma rays. See the official <a href="https://link.springer.com/journal/10686/aims-and-scope">aims and scope</a>.</p>
          <p><strong>Required before submission:</strong> use the current Springer Nature LaTeX template; provide complete authors, affiliations, corresponding-author email and preferably ORCIDs; keep an unstructured abstract at 150–250 words and 4–6 keywords; use no more than three decimal heading levels; supply editable figure/source files; add a current Data Availability Statement and complete Statements and Declarations. Follow the journal’s author–year/alphabetized reference style and use full DOI links. Verify that preprints have not acquired journal versions. See the official <a href="https://link.springer.com/journal/10686/submission-guidelines">submission guidelines</a>.</p>
          <p><strong>Artwork:</strong> quantitative plots should preferably be vector PDF/EPS. If raster artwork is retained, check the journal’s current resolution requirements for line and combination art; sparse spectra also need bin widths, normalization status, and uncertainty/upper-limit treatment in each caption.</p>
          <p><strong>AI disclosure:</strong> if substantial wording from the rewritten title or abstract is adopted, check the journal’s current disclosure policy, document the tool and purpose if required, and ensure every author independently verifies and accepts responsibility for the science.</p>
        </div>
      </section>

      <section id="scope">
        <h2>Evidence, calculations, and review scope</h2>
        <div class="panel">
          <p><strong>Review boundary.</strong> The original review used the 24-page English baseline PDF and its matching English TeX source. It did not use the Chinese manuscript, engineering packages, previous review notes, retained simulation products, or project conclusions. The sole later exception is the 4 August 2026 M02 correction, which traced the raw SIM records, catalogue parser, and final 50 keV selection mask.</p>
          <p><strong>External checks were deliberately narrow.</strong> Journal-format claims use the official Springer pages above. The atmospheric-line double-counting warning uses the primary <a href="https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0144679">PARMA3 publication</a>, which reports a small photon feature near 0.5 MeV from annihilation, together with the official <a href="https://phits.jaea.go.jp/expacs/publication-eng.htm">EXPACS publication list</a> distinguishing model releases. This does not prove double counting; it establishes that the manuscript must demonstrate the separation.</p>
          <p><strong>Reviewer screening calculations.</strong> The gross BGO estimate uses the radii, lengths, and thicknesses printed in Table 4 and 7.13 g cm⁻³, before Boolean aperture cuts; it is a feasibility flag, not the actual CAD mass. The line-window fractions assume Gaussian intrinsic and detector profiles; an actual analysis should use the intended astrophysical line model and response tails.</p>
          <p><strong>Scientific statements not independently revalidated here:</strong> the astrophysical flux/morphology citations, exact EXPACS fluxes and cutoff rigidity, Ta cross sections and cryogenic heat capacity, atmospheric transmission T = 0.739, and recent/preprint bibliography metadata still require author-side verification against primary records.</p>
        </div>
      </section>
    </main>
  </div>

  <footer>Independent manuscript review prepared from the English paper only · Annotation IDs are stable between the PDF and this report.</footer>
  <script>
    function copyText(id, button) {{
      const value = document.getElementById(id).innerText;
      navigator.clipboard.writeText(value).then(() => {{
        const old = button.textContent; button.textContent = 'Copied';
        setTimeout(() => button.textContent = old, 1200);
      }});
    }}
    document.querySelectorAll('[data-filter]').forEach(button => {{
      button.addEventListener('click', () => {{
        const filter = button.dataset.filter;
        document.querySelectorAll('[data-filter]').forEach(b => b.classList.toggle('active', b === button));
        document.querySelectorAll('.review-card').forEach(card => {{
          card.classList.toggle('hidden', filter !== 'All' && card.dataset.severity !== filter);
        }});
      }});
    }});
  </script>
</body>
</html>
"""
    HTML_REPORT.write_text(html, encoding="utf-8")


def main() -> None:
    build_annotated_tex()
    build_html()
    active_round1_annotations = sum(
        1 for row in ANNOTATIONS if row[0] not in RESOLVED_REVIEW_IDS
    )
    print(f"Wrote {ANNOTATED_TEX}")
    print(f"Wrote {HTML_REPORT}")
    print(f"Round 1: reviews {len(REVIEWS)}; active PDF annotations {active_round1_annotations}; language edits {len(LANGUAGE_EDITS)}")
    print(f"Round 2: new findings {len(REVIEWS_R2)}; PDF annotations {len(ANNOTATIONS_R2)}; stances {len(R1_STANCES)}; smaller items {len(SMALLER_ITEMS_R2)}")
    print(f"Total active PDF annotations: {active_round1_annotations + len(ANNOTATIONS_R2)}")


if __name__ == "__main__":
    main()
