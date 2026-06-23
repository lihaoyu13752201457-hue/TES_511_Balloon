# Literature And Ratio Reanalysis

Date: 2026-06-23

Scope: read-only analysis. No geometry, source card, SIM, Step05, v3p5, fix5, or
old `new_geo_re` authority output was modified. This note supersedes the
literature/local interpretation in
`../20260623_background_composition_audit/11_gatekeeper_verdict.md` where it
conflicts with the later divide-by-8 finding in
`07_final_normalization_and_sampling_verdict.md`.

## Bottom Line

The user's normalization suspicion is correct. The old `new_geo_re` delayed
authority has a missing non-gamma divide-by-8 bug. After that correction, old
delayed source activity is about `78.03 Bq`, not `624.27 Bq`, and is close to the
current fix5 exact-position source activity `85.45 Bq`.

The remaining issue is not a current fix5 half-life, activity, TE, or
M-sampling loss. The remaining old/current W2 delayed-rate gap is most likely
dominated by old source placement / detector-coupling differences: old dominant
CsI/I-128 decays were emitted on the central axis, while current exact-position
decays start in the actual CsI volumes and mostly self-veto or miss the TES.

Public literature supports the sanity concern that delayed/activation
background is often important in MeV gamma-ray instruments. It does not provide
a transferable universal delayed/prompt ratio for this narrow 511 keV
TES-Laue final selection. The correct conclusion is therefore:

1. old `new_geo_re` high delayed is invalid as a benchmark until rebuilt with
   divide-by-8 and exact-position source sampling;
2. current fix5 low delayed fraction is not physically impossible, but it needs
   to be reported with the local audit chain and low-count caveat;
3. the decisive discriminator is a corrected old exact-position delayed replay.

## External Literature Evidence

### X-Calibur / XL-Calibur

Relevant sources:

- XL-Calibur mission paper: https://arxiv.org/abs/2010.10608
- XL-Calibur anticoincidence shield paper: https://arxiv.org/abs/2212.04139

What transfers:

- XL-Calibur is a balloon hard-X-ray polarimeter with an active
  anticoincidence shield. Its simulation inputs include atmospheric electrons,
  neutrons, photons, protons, and primary protons; its Geant4 mass model includes
  the CZT, anticoincidence shield, W collimator, and nearby materials.
- The mission paper reports simulated `15-80 keV` background rates for design
  variants: X-Calibur-like `2 mm CZT + CsI` has `4.93 +/- 0.10 Hz` at a `100 keV`
  veto threshold; the compact BGO/0.8-mm-CZT XL-Calibur configuration is
  `0.51 +/- 0.02 Hz`. It also says the residual background is mainly atmospheric
  high-energy neutrons and MeV gamma rays after the shield.
- The shield paper explicitly states the important delayed caveat: neutron
  reactions can create activated isotopes near the shield/polarimeter, and
  decays outside the anticoincidence window can yield delayed gamma rays that
  cannot be vetoed.
- The same shield paper also shows how strong the veto can be: passive BGO
  shielding reduces a few-hundred-Hz polarimeter background to about `30 Hz`, and
  active veto reduces it to about `0.5 Hz`; flight data show `8.2 Hz` veto-off
  versus `0.5 Hz` veto-on for 20-40 keV 1-hit CZT events.

What does not transfer:

- These are hard-X-ray `15-80 keV` or `20-40 keV` rates, not a 511 keV
  narrow-line TES final selection.
- The papers do not publish a clean delayed/prompt activation ratio for a
  511 keV line window.

### 511-CAM / CAM511 Context

Relevant source:

- 511-CAM mission paper: https://arxiv.org/abs/2206.14652

Important distinction:

- 511-CAM does scale the cosmic-ray and atmospheric background measured with
  XL-Calibur by detector mass, expecting a `>15 keV` background rate of `60 Hz`.
- But that number is a gross telemetry/background estimate, not a delayed
  activation inventory and not a final 511 keV selected delayed/prompt ratio.
- In the same paper, the 511-CAM detector performance is evaluated with MEGAlib,
  an active BGO shield, a `390 eV` 511-keV FWHM, and a reconstructed 511-keV
  interval of `510.3-511.8 keV`; it also notes that X-Calibur single-pixel
  selection removes more than `99%` of background, and that Compton/optics
  consistency can reject events not compatible with the gamma-ray optics.

Implication for this project:

- The CAM511/X-Calibur mass-scaling context supports doing a serious background
  estimate. It does not prove that the final selected 511 keV rate must be
  delayed dominated.

### SPI

Relevant sources:

- SPI background modelling: https://arxiv.org/abs/1903.01096
- SPI response/background characteristics: https://arxiv.org/abs/1710.10139

What transfers:

- SPI data are dominated by instrumental gamma-ray background over 20 keV to
  8 MeV.
- SPI explicitly separates prompt cosmic-ray excitation/instant de-excitation
  from delayed radioactive decays/build-up on isotope half-life time scales.
- Even with anticoincidence, non-vetoed Ge detector events include delayed
  background and possible celestial triggers; background lines and continuum
  need empirical modelling.

What does not transfer:

- SPI is a space coded-mask Ge spectrometer. Activation in or near the Ge camera
  is exactly in the science detector response. Its delayed/prompt behavior is a
  strong warning, but not an absolute-rate constraint for a pointed balloon
  TES-Laue focal-plane selection with different materials, geometry, and veto.

### COSI And Balloon 511 keV Papers

Relevant sources:

- COSI 511-keV detection: https://arxiv.org/abs/1912.00110
- COSI 511-keV imaging: https://arxiv.org/abs/2005.10950
- COSI 2016 bottom-up background simulation: https://arxiv.org/abs/2503.02493

What transfers:

- COSI explicitly says the 511 keV background line has both activation and
  atmospheric contributions.
- COSI imaging describes soft gamma-ray instrumental background as a mix of
  prompt nuclear de-excitation and delayed activation/radioactive build-up, and
  says instrumental background is the dominant measured count-rate contributor.
- COSI estimates instrumental background near 511 keV to be about `100x` the sky
  signal, motivating empirical/semi-empirical background modelling.
- The 2025 bottom-up COSI balloon simulation uses MEGAlib/Cosima and separates
  atmospheric photons, internal particle-induced components, diffuse photons,
  and activation effects. Figure 14 shows PE total rates of order tens of Hz and
  particle/atmospheric components at Hz-to-tens-of-Hz scale.

What does not transfer:

- COSI is a wide-field Ge Compton telescope. Much of its activation is in Ge
  detector material and appears directly in the measured spectrum. Our dominant
  current source activity is CsI/I-128 in active-shield volumes, which is a very
  different coupling problem.
- COSI component curves are not a clean delayed/prompt fraction. Each incident
  particle component can include both prompt interactions and activation decays.

## Current Project Ratios

### Current fix5 W2 final selection

From
`stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv`:

| stream | final W2 events | final W2 cps |
|---|---:|---:|
| prompt | 54 | `0.0366410230297` |
| delayed | 30 | `0.00257520348894` |
| total background | 84 | `0.0392162265186` |

Therefore:

- delayed/prompt = `0.0703`;
- delayed/total = `0.0657`;
- prompt/total = `0.9343`.

Prompt tag tally recomputed from the Step05 event catalog with the existing
`side_keep_from_hits` logic:

- eplus: 47 events, `0.0318897456148 cps`, `87.0%` of final prompt;
- neutron: 7 events, `0.00475127741487 cps`, `13.0%` of final prompt.

This supports the existing method note that the final W2 background is still
prompt-eplus dominated after fix5, though fix5 lowers the prompt rate relative
to v3p5.

### Current v3p5 authority

From `core_md/fix5_benchmarks.json` and the v3p5 source-breakdown outputs:

- W2 prompt = `0.0590827246325 cps`;
- W2 delayed = `0.00389763720735 cps`;
- delayed/total = `6.19%`;
- prompt eplus alone = `0.0543377485018 cps`, `86.28%` of total selected
  background.

This is important: low delayed fraction is not new to fix5. It is already the
current exact-position v3p5 authority behavior.

### Old new_geo_re before and after the divide-by-8 correction

Old reported/inspected W2:

- prompt = `0.0322340047953 cps`;
- delayed = `0.152113172691 cps`;
- delayed/prompt = `4.72`;
- delayed/total = `82.5%`.

After the missing non-gamma divide-by-8 correction:

- corrected delayed = `0.0190141465864 cps`;
- corrected delayed/prompt = `0.590`;
- corrected delayed/total = `37.1%`;
- corrected old/current fix5 delayed rate ratio =
  `0.0190141465864 / 0.00257520348894 = 7.38`.

So the user's `8x` normalization hypothesis explains the large source-activity
discrepancy and most of the old delayed excess. It does not alone explain the
remaining `~7.4x` W2 selected-rate difference.

## Chain-Axis Audit

### Sampling

Current fix5:

- exact-position delayed source uses `M=50000` equal-flux `PointSource` blocks;
- activity is conserved: source activity `85.44920253876245 Bq`, summed source
  flux delta `0`;
- missed nuclide activity fraction is `0.000146`;
- top sampled species are CsI/I-128 in real CsI side/bottom volumes.

Old `new_geo_re`:

- old source builder compressed RPIP points to `RadialProfileBeam`;
- emitted source blocks used `x_cm=0`, `y_cm=0`, and z-bin centers;
- SIM-level sample shows old I-128 starts collapsed at `r=0`, while current
  fix5 I-128 starts at real CsI segment coordinates.

The old/current I-128 TES-hit fraction in the 20k-event sample differs by about
`450x`: old `0.1762`, current `0.0003916`. This is a credible mechanism for the
remaining old/current detector-coupling gap.

### Delay Processing And Half-Life

Current fix5:

- per-family division audit passes: non-gamma families divide by `8`, gamma by
  `12`;
- prompt normalization audit passes: each prompt tag has
  `rate_hz_per_event * tt_sum_s = 1`;
- NUBASE ground-state half-life audit has zero line/unit mismatches;
- Step05 delayed selected cps is exactly selected events divided by SIM
  `TE_s`: `30 / 11649.564832 = 0.00257520348894 cps`;
- the small `TE_s` versus source-activity offset is percent-level and increases,
  not suppresses, the current delayed cps.

Old `new_geo_re`:

- old inventory/source used raw non-gamma RP yields;
- raw/scaled I-128 ratio from `.dat` files is exactly `8.0`;
- old fixed source was `624.27 Bq`; corrected divide-by-8 value is
  `78.03 Bq`.

Half-life is therefore not the main suspect for the factor-of-8 discrepancy.
The main bug is missing non-gamma production division; the main remaining
coupling suspect is old source placement.

### Activation Statistics And W

Current fix5 delayed source activity:

- fixed total = `85.4492 Bq`;
- W/collimator source activity = `0.9861 Bq`, about `1.15%` of fixed source;
- selected W/collimator-origin W2 delayed events = `0 / 30`;
- final selected delayed events are Cu isotopes near cold/copper structures:
  `Cu64` (`ZA=29064`) has 24 events, `0.00206016 cps`; `Cu62` (`ZA=29062`) has
  6 events, `0.000515041 cps`.

This means the large CsI/I-128 source activity is not what survives the final
TES W2 selection. Exact-position placement puts it in the active shield, where it
mostly self-vetoes or does not reach the TES.

## Interpretation

The external literature makes the original low-delay result suspicious enough to
audit. It especially rules out any casual claim that activation can be ignored.
However, the literature does not override the local selection physics:

- SPI/COSI delayed dominance is tied to Ge detector/instrument activation and
  wide-field line spectroscopy.
- X/XL-Calibur and 511-CAM show strong active-veto and event-topology rejection,
  but do not provide delayed/prompt line-window fractions.
- Our final W2 selection is narrow, vetoed, and side-entry/FoV filtered.
- Our current delayed activity is dominated by active-shield CsI/I-128, not by
  detector-internal Ge-like activation.
- The selected current delayed events are mostly Cu near the cold detector
  structure, while the current prompt is dominated by side-entry prompt eplus
  annihilation 511.

Therefore current fix5 delayed being only `~6.6%` of final W2 selected
background is plausible under the current exact-position/veto model, but it
should be presented as a locally audited result, not a generic expectation.

## Remaining Required Discriminator

Before making any strong old/current delayed physics claim, rebuild old
`new_geo_re` delayed with the corrected rules:

1. recompute old inventory with explicit per-family raw/scaled RP totals and
   non-gamma `division=8`;
2. emit old exact-position `PointSource` blocks from old RPIP points, not
   axis-collapsed `RadialProfileBeam` blocks;
3. verify SIM `IA INIT` positions match RPIP coordinates and no longer collapse
   to `r=0`;
4. rerun the same W2 Step05 selection and compare selected `cps/Bq` with current
   fix5/v3p5.

Expected outcome to test:

- If corrected old exact-position W2 delayed drops toward current fix5/v3p5,
  old delayed dominance was mostly a normalization plus source-placement
  artifact.
- If it remains high after correction, then the remaining difference is a real
  geometry/material/selection coupling effect and should be investigated as
  physics rather than normalization.
