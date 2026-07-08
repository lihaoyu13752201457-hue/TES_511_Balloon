# Balloon Project Background Survey For Delayed/Prompt Tension

Date: 2026-06-23

Scope: read-only literature and local-ratio discussion. No geometry, source
card, SIM, Step05, v3p5, fix5, or old `new_geo_re` authority output was
modified.

## Bottom Line

The public balloon literature does not support a universal rule that delayed
activation must exceed prompt background in every final analysis selection.
It supports a narrower and more important statement:

1. In MeV gamma instruments, especially high-resolution Ge spectrometers and
   wide-field line instruments, activation is often a major or dominant
   measured-background component.
2. In instruments with strong event topology, Compton kinematic cuts, active
   vetoes, narrow fields of view, or low-Z detector media, the final selected
   background can instead be dominated by atmospheric/cosmic photons, prompt
   charged/neutral secondaries, or neutron-induced prompt-like events.
3. Therefore the relevant question for this project is not whether activation
   is real. It is whether activation decays couple efficiently into the final
   `W2 510.58-511.42 keV + active veto + side/FoV` TES selection.

For the current fix5 exact-position result, the answer appears to be no:
activation source activity is not negligible, but its final selected W2
acceptance is small.

Current fix5 W2 final local numbers:

| quantity | value |
|---|---:|
| prompt W2 final | `54 events`, `0.0366410230297 cps` |
| delayed W2 final | `30 events`, `0.00257520348894 cps` |
| delayed / prompt | `0.0703` |
| delayed / total background | `0.0657` |
| prompt eplus component | `47 events`, `0.0318897456148 cps`, `87.0%` of prompt |
| fixed delayed source activity | `85.4492025388 Bq` |
| W/collimator selected delayed | `0 events`, `0 cps` |

This result is in tension with a naive reading of "balloon MeV instruments are
activation dominated", but it is not in direct contradiction with the broader
balloon literature once final selection and detector coupling are separated
from gross background spectra.

## Project Survey

| project / source | instrument class | public background conclusion | delayed/prompt relevance to this project |
|---|---|---|---|
| COSI 2016 balloon | HPGe Compton telescope, 0.2-5 MeV, wide field | MeV observations are dominated by background, especially activation of detector materials; activation lines are reproduced in bottom-up simulations. | Strongest cautionary analogue. It says activation matters a lot in balloon Ge line spectroscopy, but COSI activation is in Ge detector material and broad Compton data space, not in a TES line-window selection with an active CsI shield. |
| COSI 511 keV papers | HPGe balloon 511 analysis | The 511 keV background has both atmospheric and activation contributions; absolute physical background modelling is hard and empirical modelling is needed. | Directly relevant to 511 keV balloon analysis. It warns us not to dismiss activation. It still does not give a transferable final delayed/prompt ratio for our optics/TES/veto selection. |
| NCT | HPGe compact Compton telescope | Background has real photons, particles, and instrumental radioactivity, but instrumental events are effectively eliminated by Compton kinematic discrimination; remaining background is dominated by atmospheric/cosmic photons and atmospheric 511 keV photons. | Important counterexample: even a Ge balloon Compton instrument can have final analysis background dominated by real atmospheric/cosmic photons after CKD. |
| LXeGRIT | LXeTPC Compton telescope | Charged-particle trigger rate is large but rejected; neutron-induced background is marginal; local instrumental background is negligible; atmospheric plus cosmic diffuse gamma background dominates the gamma-ray background comparison. | Supports the possibility that final gamma selections need not be activation dominated when topology/material/rejection differ. |
| SMILE-2+ | ETCC balloon Compton camera | Background below 400 keV comes from atmospheric gamma, cosmic-ray/secondary particles, and accidental events; activation is considered, but GSO activation is estimated negligible for the reported balloon contribution; neutron processes dominate some higher-energy residuals. | Supports event-selection-dependent background composition. Activation exists, but is not automatically the dominant final selected component. |
| SMILE-I / SMILE-2+ observation papers | ETCC balloon observations | Final reconstructed event samples can contain large atmospheric/cosmic gamma fractions; electron-tracking and Compton kinematics improve S/N. | Supports the "final selected sample" distinction. |
| X-Calibur / XL-Calibur | focused hard-X-ray polarimeter with BGO veto and W/CZT materials | Residual shield leakage is dominated by atmospheric high-energy neutrons and MeV gamma rays; the shield paper explicitly warns that activation decays outside the anticoincidence window can be irreducible delayed background. Flight veto reduces 20-40 keV 1-hit rate from `8.2 Hz` to `0.5 Hz`. | Very relevant to veto and W/CZT-style materials. It warns activation can leak, but its published rates are hard-X-ray 15-80 keV or 20-40 keV, not a 511 keV TES W2 delayed/prompt split. |
| 511-CAM concept | Laue/channeling optics plus TES microcalorimeter focal plane | Gross background estimate scales XL-Calibur cosmic/atmospheric background by mass to `>15 keV` rate of `60 Hz`; MEGAlib model uses active BGO and highlights narrow 511 keV resolution and background rejection by single-pixel and optics/Compton consistency. | Closest conceptually, but the `60 Hz` is not a delayed activation rate and not a W2 final selected delayed/prompt ratio. It supports serious background modelling, not delayed dominance. |
| PoGOLite / PoGOLino | hard-X-ray polarimeter with plastic/BGO and polyethylene | Main background for PoGOLite stems from high-energy atmospheric neutrons. PoGOLino was built to measure neutron flux; even with heavy polyethylene, neutron background can be comparable to Crab signal. | Another counterexample to delayed dominance: the public concern is neutron prompt-like false triggers, not activation decays. |
| GRAPE | balloon Compton polarimeter, 50-500 keV | Balloon background dominates observations; simulations include gammas, protons, electrons/positrons, neutrons. The largest simulated components are gammas, neutrons, and atmospheric positrons; PCA is used to estimate flight background. | Supports the same taxonomy as our prompt stream: atmospheric positrons and neutrons can dominate final background handling. It is not a delayed/prompt activation ratio. |
| GRAMS concept | LArTPC balloon MeV gamma + antimatter mission | Balloon sensitivity assumes atmospheric photon background; neutrons can contribute, but LAr pulse shape can distinguish gamma rays from neutrons; low-Z LAr may avoid many activation lines compared with INTEGRAL/SPI. | Material dependence matters. Low-Z detector medium can reduce activation-line dominance. |
| CdZnTe balloon background / EXITE2 piggyback | CdZnTe with BGO anticoincidence at balloon altitude | BGO shield reduced background by a factor of 6 at 100 keV; non-vetoed background was compared with GEANT within factor 2. | Useful active-shield benchmark. It addresses shield leakage/local production/neutron interactions, not delayed/prompt dominance. |
| GRIS / classic Ge balloon spectroscopy | balloon Ge line spectrometer with NaI anticoincidence | Historically successful 511/nuclear-line balloon spectroscopy with large Ge detector mass and active shielding. | Relevant as historical Ge-line context, but public summaries do not provide a clean delayed/prompt final-selection ratio. |

## Interpretation By Instrument Class

### Activation-heavy class

COSI, SPI-like Ge spectroscopy, and classic Ge balloon line instruments are the
class most likely to conflict with a low-delayed conclusion. Their science
detectors are themselves high-resolution Ge volumes; activation lines are
created in material that is also the signal detector. For that class, delayed
activation is not a small correction. It is part of the main measured spectrum.

This class tells us:

- do not claim "activation is negligible" from first principles;
- do not use an activation source without auditable build-up, half-life, and
  activity normalization;
- do not expect a purely prompt atmospheric model to explain a 511 keV balloon
  line spectrum.

### Selection-rejected or prompt-dominated class

NCT, LXeGRIT, SMILE, PoGOLite/PoGOLino, GRAPE, X/XL-Calibur, and CdZnTe shield
tests all show cases where the final background problem is not simply
"delayed activation dominates". Depending on detector media and cuts, the
limiting background can be:

- atmospheric gamma rays;
- atmospheric 511 keV photons;
- atmospheric positrons/electrons;
- high-energy neutrons;
- shield leakage;
- accidental or non-correlated events;
- prompt instrumental interactions.

This class tells us a low final delayed fraction is physically possible if the
analysis cuts reject activated shield events and leave atmospheric/prompt
components.

## Why Our Low Delayed Fraction Can Be Plausible

The current source activity is not small: `85.45 Bq` fixed delayed source
activity is present in the model. The low W2 delayed rate is therefore a
coupling/selection statement, not a no-activation statement.

The local mechanism is:

1. The final W2 prompt stream is mostly prompt `eplus` (`87%` of prompt),
   consistent with atmospheric positron/annihilation-like prompt backgrounds
   being a real balloon component.
2. The delayed source is sampled at exact positions. Dominant shield/outer-volume
   activation no longer starts on the central axis. This removes the old
   artificial geometric coupling into the TES.
3. The active veto and side/FoV selection suppress many shield-origin decays.
4. The selected delayed W2 events in the current audit come from Cu-62/Cu-64
   near cold/support structures, not from W/collimator and not from the dominant
   old CsI/I-128 axis-collapsed component.

This is consistent with the NCT/LXeGRIT/SMILE lesson: final event topology can
make atmospheric/cosmic prompt components dominate even when activation exists
in the instrument.

## What Still Remains A Real Concern

The low delayed fraction should not be oversold. The current W2 delayed result
has only `30` selected delayed events. A factor-level uncertainty from final
selection support, rare paths, and seed statistics is still plausible.

The strongest remaining checks are:

1. Rebuild old `new_geo_re` delayed with both fixes applied: divide-by-8
   non-gamma normalization and exact-position PointSource sampling. This is the
   clean old/current discriminator.
2. Run an independent current delayed replay or seed split to test the final
   selected W2 support. The source-level `M=50000` audit is good, but final W2
   support is still only 30 events.
3. Report broad-window and W2-window delayed/prompt ratios separately. If a
   paper only states "delayed is 6-7% of final background", readers may assume
   activation was absent; the correct wording is that activation source strength
   exists but is rejected by the final event selection.
4. In the manuscript, compare against COSI as a cautionary Ge-line benchmark,
   and against NCT/LXeGRIT/SMILE/PoGOLite as evidence that final selected
   balloon backgrounds are instrument- and cut-dependent.

## Practical Wording For This Project

Do not write:

> Activation is negligible in balloon 511 keV observations.

Write instead:

> Activation is included with audited isotope build-up, half-life handling, and
> exact-position decay sampling. In the current TES-Laue `W2` final selection,
> the selected delayed component is small (`0.00258 cps`, about `6.6%` of the
> selected background), while the selected prompt component is dominated by
> prompt positron events. This is a selection-conditional result and should be
> interpreted with the low-count delayed support caveat.

## Sources

- COSI bottom-up balloon background simulation: https://arxiv.org/abs/2503.02493
- COSI 511 keV detection: https://arxiv.org/abs/1912.00110
- COSI 511 keV imaging/background modelling: https://arxiv.org/abs/2005.10950
- COSI 2016 super-pressure balloon overview: https://arxiv.org/abs/1701.05558
- Nuclear Compton Telescope Crab balloon analysis: https://arxiv.org/abs/1106.0323
- LXeGRIT balloon background: https://arxiv.org/abs/astro-ph/0211584
- SMILE-2+ background contributions: https://arxiv.org/abs/2306.02700
- SMILE-2+ balloon observation: https://arxiv.org/abs/2107.00180
- SMILE-I balloon background: https://arxiv.org/abs/1103.3436
- XL-Calibur shield design/performance: https://arxiv.org/abs/2212.04139
- XL-Calibur mission paper: https://arxiv.org/abs/2010.10608
- 511-CAM mission paper: https://arxiv.org/abs/2206.14652
- PoGOLite hard-X-ray polarimetry: https://arxiv.org/abs/1211.5094
- PoGOLino high-latitude atmospheric neutron measurement: https://arxiv.org/abs/1311.5531
- PoGOLino scintillator neutron detector paper: https://arxiv.org/abs/1410.2377
- GRAPE balloon Compton polarimeter analysis: https://arxiv.org/abs/2012.12939
- GRAPE instrument concept: https://arxiv.org/abs/astro-ph/0508314
- GRAMS concept: https://arxiv.org/abs/1901.03430
- CdZnTe balloon background measurement: https://arxiv.org/abs/astro-ph/9808241
- Atmospheric response for balloon MeV gamma rays: https://arxiv.org/abs/2406.03534

## Local Inputs

- `stepwise_maintenance/step05_veto_time_axis/outputs_fix5_fullstat_v2_exactpos_m50000_s260613_l1/step05_fix5_fullstat_v2_exactpos_m50000_s260613_l1_rates.csv`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_delayed_source_exactpos_summary.json`
- `outputs/reports/fix5_fullstat_v2_exactpos_m50000_s260613/fix5_w_activation_selected_w2_audit.json`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_delay_processing_reaudit_3agent/08_fix5_prompt_tag_tally.csv`
- `core_md/balloon511_nima_latex_drafts/revision_harness_runs/20260623_delay_processing_reaudit_3agent/08_literature_and_ratio_reanalysis.md`
