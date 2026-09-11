# Claude R4 Recheck

Date: 2026-06-17.

Scope: independent Codex recheck of
`core_md/CLAUDE_REVIEW_TES511_BALLOON_20260616_R4.md` against the current
paper-facing manuscript, authority JSON/CSV/MD reports, and regenerated
lightweight audit products. This check did not rerun Cosima transport.

## Summary

Claude R4 is largely correct on the scientific boundary issues, but several of
its numeric statements are tied to the older CsI `M=5000` exact-position
baseline. The current paper-facing authority is
`fullstat_v2_exactpos_m50000_s260613`. After rechecking the current files, the
main physics conclusion remains closed at the rate level: the primary hard-window
chain uses the M=50000 exact-position result, and the manuscript now states the
important caveats around reconstruction policy, slant-column atmosphere,
material-specific veto thresholds, and delayed-component convergence.

Two metadata problems from R4 were still active and have now been fixed:

- `outputs/reports/v3p5_exactpos_convergence_20260614/` used
  `w2_signal_cps_at_1e_4` for a unit-area proxy value. The generator now writes
  the physical signal rate at the reference flux, the response coefficient, the
  unit-EventList pass rate, and the old unit-area proxy as a separately named
  field. The convergence and M-sampling audit reports were regenerated.
- `stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json`
  still described f10m as an embeddable candidate while f9m remained the
  published headline. The authority JSON and installer template now state that
  f10m is the current paper-facing optical authority after the downstream
  detector-coupling, source-normalization, and significance reruns.

## Item-by-item Recheck

| R4 issue | Recheck result | Action |
|---|---|---|
| Exact-position authority vs radial-profile cross-check | Valid and already handled. The current manuscript uses M=50000 exact-position as the primary row and leaves radial-profile as a comparison cross-check. | No new manuscript edit required. |
| M-sampling convergence | Valid caveat. The delayed subcomponent is not strictly plateaued by itself, but the transported sweep gives W2 total-background relative range 0.01119 and Z20d relative range 0.00551. | Manuscript already limits the convergence claim to total hard-window background and significance. Regenerated the M-sampling audit after fixing signal-field metadata. |
| BGO-vs-CsI threshold asymmetry | Valid. It is not a same-threshold material scan. The current comparison uses CsI 50 keV and BGO 70 keV by material-design threshold. | Manuscript caption and limitations already state this. Current BGO comparison is against CsI M=50000, not the older M=5000 baseline. |
| BGO authority level | Valid boundary after a second pass. The BGO material-control branch uses its transported 5000-support delayed source and has not been promoted by a BGO-specific M/seed convergence sweep. | Tightened manuscript wording so the BGO row is a material-control result, not a replacement rate authority. |
| Current BGO numbers | R4's 0.922619 / +4.541% / -4.344% ratios are historical because they used the older CsI baseline. | Current authority gives mission-mean BGO/CsI background ratio 0.915191, Z20d ratio 1.04965, and F3(20d) ratio 0.952702. |
| Keep-policy sign | Valid. Keeping reconstruction-reject events raises the baseline Z relative to rejecting them, so it is not a conservative sensitivity lower bound. | Manuscript already states that reject-kept removal would retain 59.2% signal and 66.8% background and reduce S/sqrt(B) to 0.724 of baseline. |
| Atmospheric transmission / source zenith angle | Valid boundary. The reference T_atm is a baseline pointing normalization, not a universal balloon-pointing value. | Manuscript already identifies the 45 degree LOS rows as the slant-column boundary calculation and says source-specific Galactic-center estimates need a zenith-angle mission model. |
| Convergence summary `w2_signal_cps_at_1e_4` field | Valid and previously still active. | Fixed in `code/tools/build_v3p5_exactpos_convergence_report.py`; regenerated summary/case CSV/report and refreshed `m_sampling_audit_20260616`. |
| f10m optics `science_policy` | Valid and previously still active. | Fixed in `optics_aeff_authority_f10m_a1.json` and `install_f10m_authority.py`. |
| Step11 upstream optics self-background | The current manuscript describes the Ge-proxy delayed upper limit and keeps prompt self-background outside the primary budget until provenance isolation/subtraction is done. | No new manuscript edit in this pass. The `scaled_production_yield=0.25` provenance remains a non-headline normalization hygiene item. |
| Git/outside-authority governance | Still relevant. Several paper figures, reports, tools, and PDFs remain uncommitted/untracked in the working tree. | Not committed in this pass because no git action was requested. |
| Dangling path cleanup in core docs | Still relevant as documentation hygiene, not a rate/sensitivity blocker. | Not addressed in this pass. |

## Regenerated Checks

- `outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_summary.json`
- `outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_cases.csv`
- `outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_report.md`
- `outputs/reports/m_sampling_audit_20260616/m_sampling_audit_summary.json`
- `outputs/reports/m_sampling_audit_20260616/m_sampling_audit_report.md`
- `outputs/reports/m_sampling_audit_20260616/m_sampling_audit_top20_species_deviation.csv`
- `outputs/reports/m_sampling_audit_20260616/m_sampling_audit_missed_nuclides.csv`

## Current Open Items

- Run a Revan/Mimrec or equivalent reconstruction cross-check for the retained
  multi-hit reconstruction-reject subset.
- Replace the baseline atmospheric-transmission scalar with a trajectory- and
  source-zenith-angle mission model for source-specific Galactic-center claims.
- Decide whether to add a same-threshold CsI/BGO veto scan; the current paper
  only claims a material-design-threshold control.
- Trace the Step11 `scaled_production_yield=0.25` factor for bookkeeping
  hygiene, even though the current Ge-proxy delayed selected rate is zero.
- Clean dangling paths in active core documentation and commit the current
  paper-facing authority artifacts when the user requests git.

## Post-Compile Recheck After Manuscript Refinement

The current English and Chinese drafts were recompiled after abstract and
manuscript-facing wording refinements. The abstract no longer exposes the
internal `exact-position` branch name, the 50,000 support-element construction,
or support-size terminology. Citation closure is complete in both drafts
(`24/24` cited keys have matching bibliography entries, with no uncited
`bibitem` entries).

The Claude R4 physics items are now represented in the manuscript as follows:

- The paper-facing CsI authority is the M=50000 exact-position chain, with
  `B_W2 = 0.0629804 s^-1`, `S_W2(F0=1e-4) = 0.00118117 s^-1`,
  `Z20d = 6.13039`, and `F3(20d) = 4.89365e-5 ph cm^-2 s^-1`.
- The M/seed convergence statement is limited to total hard-window background
  and significance: total background relative range `0.0111915`, `Z20d`
  relative range `0.00550844`; the delayed subcomponent relative range
  `0.187413` remains explicitly identified as a subcomponent fluctuation.
- The BGO comparison is no longer described as a same-threshold scan. The
  current report status is
  `PASS_BGO_SAMPLE_VS_CSI_EXACTPOS_M50000_COMPARISON`, with CsI/BGO active-veto
  thresholds of `50/70 keV`, BGO/CsI mission-mean W2 background ratio
  `0.915191`, Z20d ratio `1.04965`, and F3(20d) ratio `0.952702`.
- The BGO material-control row is not promoted to the same authority level as
  the CsI headline: it uses the transported 5000-support BGO delayed source and
  lacks a BGO-specific support-size/seed convergence sweep.
- The f10m optics file now states that f10m is the current paper-facing optical
  authority after the detector-coupling, source-normalization, and significance
  reruns.

Both TeX logs were scanned for fatal LaTeX errors, undefined references, and
undefined citations; no matches were found. Remaining overfull boxes are layout
warnings in the abstract first line, tables, long detector-model terms, and
reference URLs/names, not unresolved scientific-content issues.

## Follow-up Recheck After Table-Terminology Pass

A follow-up pass checked the paper-facing table resources as well as the main
manuscript files. The included workflow tables still exposed the internal
`W2` line-window label in three cells per language. These were changed to the
rendered manuscript symbol \(W_{511}\) through the existing `\wii` macro. The
main drafts and included table TeX files now have no literal `W2` or
`reject-kept` matches.

The R4 numerical checks were rerun against the current file schemas:

- Current BGO-vs-CsI comparison status:
  `PASS_BGO_SAMPLE_VS_CSI_EXACTPOS_M50000_COMPARISON`; active-veto thresholds
  are CsI/BGO `50/70 keV`, confirming that this remains a material-design
  threshold control rather than a same-threshold veto scan.
- Current BGO/CsI ratios are `0.915190777` for mission-mean line-window
  background, `1.049646589` for `Z20d`, and `0.952701615` for the 20-d
  3-sigma flux threshold.
- The M-sampling audit status is `PASS_M_SAMPLING_AUDIT`. The exact-position
  weighted table activity matches the fixed activity with relative delta
  `-1.99e-15`; the M=50000 missed-nuclide activity is `0.0574501 Bq`, or
  `6.7086e-4` of the total activity. The transported convergence ranges remain
  `0.0111915` for total line-window background, `0.00550844` for `Z20d`, and
  `0.187413` for the delayed subcomponent alone.
- The convergence authority now keeps the physical signal rate under
  `w2_signal_cps_at_1e_4 = 0.0011811656` and separates the old unit-area proxy
  as `w2_signal_unit_area_proxy_cps_at_1e_4 = 7.957466e-05`.

The English and Chinese PDFs were recompiled again after the table edit. A
fresh fatal-error/undefined-reference/undefined-citation scan was clean, and
both drafts still have closed citation sets with 24 cited keys and 24 matching
bibliography entries.

## User-Requested Recheck Against Claude R4 Current Schema

This pass reread Claude R4 and re-extracted the same risk items from the current
JSON/report schemas. The main conclusion is unchanged: Claude R4 identified real
boundary risks, but the active manuscript and authority files now use the
post-R4 M=50000 paper-facing values.

- Exact-position convergence remains closed only at the total selected
  line-window and significance level: status
  `PASS_EXACTPOS_TRANSPORT_CONVERGENCE`, recommendation
  `PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY`, with relative ranges
  `0.0111914918` for total line-window background, `0.00550844085` for `Z20d`,
  and `0.187412720` for the delayed subcomponent alone.
- The convergence summary now stores the physical reference-flux signal as
  `w2_signal_cps_at_1e_4 = 0.0011811656293957314`; the old unit-area proxy is
  separated as `w2_signal_unit_area_proxy_cps_at_1e_4 =
  7.957466258001846e-05`.
- The M-sampling audit remains `PASS_M_SAMPLING_AUDIT`: the exact-position
  weighted table activity is `85.6366958652768 Bq` versus fixed activity
  `85.63669586527698 Bq` (`-1.99e-15` relative delta), and the M=50000 missed
  nuclide activity is `0.0574501262 Bq`, or `6.7086e-4` of total activity.
- The BGO material-control comparison remains a material-design-threshold
  comparison, not a same-threshold scan: CsI uses 50 keV and BGO uses 70 keV.
  Current ratios are BGO/CsI `0.915190777` for mission-mean line-window
  background, `1.049646589` for `Z20d`, and `0.952701615` for the 20-d flux
  threshold.
- The f10m optics authority now states that f10m is the current paper-facing
  optical authority after downstream detector-coupling, source-normalization,
  and significance reruns. Recomputing the effective area from the current file
  gives `81 * diffraction_fraction * within_be_fraction = 20.08476 cm2`.
- The Step11 Ge-proxy delayed side component is still a boundary calculation:
  isolated activity `0.42567438 Bq`, `scaled_production_yield = 0.25`, zero
  selected line-window events, and a 95% zero-count upper rate
  `1.2534045848433615e-4 s^-1`. The `0.25` factor remains a bookkeeping
  provenance item, not a current headline-rate driver.
- A scan for the historical BGO ratios found them only in Claude R4 itself and
  in the 2026-06-15 historical manuscript review log. The latter was marked as
  superseded by the current M=50000 comparison so future text search does not
  mistake the older `7.738% / 4.541% / 4.344%` values for active paper wording.
- The Section 2 resource review still carried older M=5000 authority numbers
  and an obsolete LaTeX build note. It was refreshed to the current M=50000
  values: `B/S = 0.0629804/0.00118117 cps`, `Z20d = 6.13039`,
  `F3(20d) = 4.89365e-5 ph cm^-2 s^-1`, and the current XeLaTeX build path.

## Methods/Results Structure Follow-up

A final reread checked whether Claude R4's upstream-optics boundary item was
represented with clean manuscript structure. The physics boundary was already
correct, but the English and Chinese Laue-optics Methods sections still carried
the delayed Ge-proxy selected-rate result. That mixed method construction with a
result.

The selected-rate result has now been moved into a dedicated Results subsection
in both drafts. Methods defines the equal-volume/equal-mass Ge proxy, the
1060 cm source surface, the full-particle prompt and activation-production
transports, and the recorded-position delayed replay construction. Results now reports the two
isolated day-15 isotope records (`70Ga` and `73Ga`), total activity
`0.425674 Bq`, zero selected line-window events in 20,000 triggers, and the 95%
zero-count upper rate `1.25e-4 s^-1`. Discussion points back to that Results
subsection and keeps prompt optics self-background outside the primary budget
pending provenance isolation or subtraction.

English and Chinese PDFs were recompiled after this structure edit. The
fatal-error/undefined-reference/undefined-citation scan is clean, citation sets
remain closed at 24 cited keys and 24 bibliography entries in each draft, and
the only remaining overfull warning is the pre-existing 0.90143 pt requirements
table warning.

## Current Claude-R4 Recheck and Documentation Wording Pass

This pass reread the full Claude R4 review and rechecked its highest-risk items
against the current schemas. The conclusion is stable: Claude R4's science-side
warnings were mostly valid boundaries, but the active paper now uses the
post-R4 M=50000 CsI exact-position authority and paper-facing wording.

- Exact-position support-count and seed convergence remains closed at the
  total selected line-window and significance level:
  `PASS_EXACTPOS_TRANSPORT_CONVERGENCE`, with total line-window background
  relative range `0.0111914918`, `Z20d` relative range `0.00550844085`, and
  delayed-subcomponent relative range `0.187412720`.
- The signal-rate metadata issue identified by Claude R4 is fixed in the
  convergence authority: `w2_signal_cps_at_1e_4 =
  0.0011811656293957314`, while the old unit-area proxy is separately named
  `w2_signal_unit_area_proxy_cps_at_1e_4 = 7.957466258001846e-05`.
- The M-sampling audit remains `PASS_M_SAMPLING_AUDIT`; exact-position table
  activity is `85.6366958652768 Bq` versus fixed activity
  `85.63669586527698 Bq`, and the M=50000 missed-nuclide activity is
  `0.0574501262 Bq` (`6.7086e-4` of total activity).
- The current BGO comparison is a material-design-threshold control, not a
  same-threshold scan. CsI uses `50 keV`, BGO uses `70 keV`, and the current
  BGO/CsI ratios are `0.915190777` for mission-mean line-window background,
  `1.049646589` for `Z20d`, and `0.952701615` for the 20-d flux threshold.
- The f10m optics authority states that f10m is the current paper-facing
  optical authority; recomputing from the file gives `20.08476 cm2`.
- The Step11 Ge-proxy delayed side component remains a boundary calculation:
  `0.42567438 Bq`, `scaled_production_yield = 0.25`, zero selected
  line-window events, and a 95% zero-count upper rate
  `1.2534045848433615e-4 s^-1`. The `0.25` factor is still a bookkeeping
  provenance item, not a current headline-rate driver.

The main manuscripts already contain Claude R4's required wording boundaries:
retained reconstruction-reject events are not described as a conservative
sensitivity lower bound, the reference atmospheric transmission is stated as a
baseline pointing normalization rather than a universal balloon value, and the
BGO row is labeled as a material-control result with material-specific veto
thresholds.

One documentation hygiene issue was still visible in active core documents:
`README.md`, `Project_Memory.md`, and `workflow.md` used "matched" around the
BGO-vs-CsI material comparison. Those instances were changed to
material-control/corresponding comparison wording so future text searches do not
mistake the control for a same-threshold veto scan. No manuscript number,
simulation product, or PDF content changed in this wording pass.

## Current User-Requested Recheck Pass

This pass rechecked Claude R4 against the current authority schemas and active
paper text after the latest manuscript edits. The result is unchanged at the
physics level: Claude R4 found real boundary issues, but the active manuscript
now uses the post-R4 M=50000 CsI exact-position authority and carries the
necessary caveats.

- The exact-position convergence authority still reports
  `PASS_EXACTPOS_TRANSPORT_CONVERGENCE` and
  `PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY`. The transported relative ranges
  are `0.0111914918` for the total selected line-window background,
  `0.00550844085` for `Z20d`, and `0.187412720` for the delayed subcomponent
  alone. This supports the manuscript wording that convergence is claimed for
  the total hard-window rate and significance, not for the delayed subcomponent
  as an isolated plateau.
- The signal metadata issue identified by Claude R4 remains fixed:
  `w2_signal_cps_at_1e_4 = 0.0011811656293957314`, while the old unit-area
  proxy is separated as
  `w2_signal_unit_area_proxy_cps_at_1e_4 = 7.957466258001846e-05`.
- The M-sampling audit remains `PASS_M_SAMPLING_AUDIT`. The exact-position
  weighted table activity is `85.6366958652768 Bq` versus fixed activity
  `85.63669586527698 Bq` (`-1.99e-15` relative delta). For the nominal
  M=50000 source card, flux conservation relative delta is `0.0`, coordinate
  back-match fraction is `1.0`, and missed-nuclide activity is
  `0.0574501262 Bq` (`6.7086e-4` of total activity).
- The BGO comparison remains a material-design-threshold control, not a
  same-threshold veto scan. Current rows use CsI/BGO active-veto thresholds of
  `50/70 keV`. Current BGO/CsI ratios are `0.915190777` for mission-mean
  line-window background, `1.049646589` for `Z20d`, and `0.952701615` for the
  20-d flux threshold.
- The f10m optics authority still states that f10m is the current paper-facing
  optical authority; recomputing `81 * diffraction_fraction * within_be_fraction`
  gives `20.08476 cm2`.
- The Step11 upstream Ge-proxy delayed side component remains a boundary
  calculation: `0.42567438 Bq`, `scaled_production_yield = 0.25`, zero selected
  line-window events, and a 95% zero-count upper rate of
  `1.2534045848433615e-4 s^-1`. The `0.25` factor remains a bookkeeping
  provenance item rather than a current headline-rate driver.

One residual wording issue was still present outside the main manuscript:
`Bgo_sample/README.md`, four BGO smoke/provenance notes, two BGO summary JSON
files, and three BGO/Step08 generation scripts still used "matched" wording for
the BGO-vs-CsI comparison. Those have now been changed to
material-control/corresponding-comparison wording so regeneration will not
reintroduce the same ambiguity. The remaining occurrences of the historical
`0.922619 / 4.541% / 4.344% / 7.738%` values are in historical review notes or
Claude R4/recheck text where they are explicitly identified as superseded.

## Terminology and Data-Availability Follow-up

This pass used Claude R4 as a checklist for reader-facing wording. No physics
number or authority JSON value changed. The English and Chinese manuscripts and
included workflow/requirements tables were cleaned so that the paper no longer
exposes internal workflow language such as `paper-facing`, `support-count`,
literal `W2`, `reject-kept`, `EventList`, `SIM`, `sim.gz`, or source-card
terminology. The delayed-source construction now describes \(M\) as the number
of equal-activity sampled point sources / point-source samples, with convergence
phrased as an M-sampling and seed sweep. Chinese wording was also changed from
project-like "主线" language to "基准" or "主要" where appropriate.

The data and software availability statement was rewritten as a publication
archive statement: it now promises versioned geometry and source definitions,
random seeds, analysis and figure-generation scripts, LaTeX source, and derived
validation products, while treating raw transport outputs and compressed Cosima
event files as separate large-data material or reproducible by commands,
configuration files, checksums/metadata, and derived validation products.

After the wording pass, both English and Chinese PDFs were rebuilt with
XeLaTeX. The current PDFs are:

- `balloon511_nima_draft_en.pdf`, 2,984,565 bytes, 2026-06-17 04:43:15 +0800.
- `balloon511_nima_draft_zh.pdf`, 3,320,709 bytes, 2026-06-17 04:43:21 +0800.

Final checks:

- Internal-terminology scan over the main TeX files and included workflow tables:
  no matches for the targeted internal terms.
- Fatal LaTeX / undefined citation / undefined reference scan: no matches.
- Citation closure: 25 cited keys, no missing citations, no uncited bibliography
  items.
- Reference closure: no missing labels. A few section labels remain unreferenced
  by design.
- Overfull scan: only the existing 0.90143 pt requirements-table warning remains
  in each draft.
- `git diff --check`: clean.

## User-Requested Claude R4 Recheck, Requirements-Table Proxy Wording

This pass reread Claude R4 as an external-review checklist and rechecked the
current authority schemas rather than trusting the earlier follow-up notes. The
main conclusion remains stable: Claude R4 identified real boundary issues, but
the current paper-facing chain uses the post-R4 M=50000 CsI exact-position
authority and the manuscript carries the required caveats.

- Exact-position convergence remains rate-level closed only for the total
  selected line window and significance: `PASS_EXACTPOS_TRANSPORT_CONVERGENCE`,
  with relative ranges `0.0111914918` for total line-window background,
  `0.00550844085` for `Z20d`, and `0.187412720` for the delayed subcomponent
  alone.
- The signal metadata issue from Claude R4 is fixed:
  `w2_signal_cps_at_1e_4 = 0.0011811656293957314`; the old unit-area proxy is
  separately named as `w2_signal_unit_area_proxy_cps_at_1e_4 =
  7.957466258001846e-05`.
- The M-sampling audit remains `PASS_M_SAMPLING_AUDIT`. For the nominal
  `M50000_seed260613` source, the manifest contains 50,000 point-source samples,
  conserves `85.63669586527698 Bq` exactly at manifest level, has coordinate
  back-match fraction `1.0`, and misses `0.0574501262 Bq` in unsampled nuclides,
  or `6.7086e-4` of the total activity.
- The BGO comparison remains a material-design-threshold control, not a
  same-threshold veto scan. The current status is
  `PASS_BGO_SAMPLE_VS_CSI_EXACTPOS_M50000_COMPARISON`, with BGO/CsI ratios
  `0.915190777` for mission-mean line-window background, `1.049646589` for
  `Z20d`, and `0.952701615` for the 20-d flux threshold.
- The f10m optical authority still recomputes to `20.08476 cm2` and its policy
  text states that f10m is the current paper-facing authority after downstream
  detector-coupling, source-normalization, and significance reruns.
- The Step11 upstream Ge-proxy delayed side component remains a boundary
  calculation: `0.42567438 Bq`, `scaled_production_yield = 0.25`, zero selected
  line-window events, and a 95% zero-count upper rate of
  `1.2534045848433615e-4 s^-1`.

One manuscript-facing consistency issue was found in the requirements
traceability tables and discussion shorthand: the upstream optics closure was
not consistently described as the equal-volume/equal-mass active-Ge proxy used
in Methods. The English and Chinese requirements tables and discussion boundary
sentence were changed to "equal-volume/equal-mass active-Ge proxy" and
"等体积、等质量主动 Ge 代理". No rate, sensitivity, source, or transport product changed.

Final verification after this wording fix:

- English and Chinese PDFs were rebuilt with XeLaTeX:
  `balloon511_nima_draft_en.pdf` is 2,984,918 bytes and
  `balloon511_nima_draft_zh.pdf` is 3,320,190 bytes.
- Fatal LaTeX / undefined citation / undefined reference scan: no matches.
- Citation closure: 25 cited keys and 25 bibliography entries in each draft;
  no missing or uncited entries.
- Label closure: 34 labels in each draft; no missing references.
- Float-reference closure: 17 figure/table labels in each draft; all are
  referenced and the first prose reference precedes each float label.
- Targeted terminology scan over the main TeX files and included tables: no
  matches for the stale "匹配 Ge 体积" wording or the internal workflow terms
  checked in this pass.
- Overfull scan: only the existing 0.90143 pt requirements-table warning
  remains in each draft.
- `git diff --check`: clean.

## Abstract and Conclusion Rate-Layer Follow-up

This pass checked the abstract and conclusion against Claude R4's concern that
rate-level authority values must not mix incompatible layers. The Results
section already separates day-15 selected rates from mission-mean rates and
mission-folded significance. The abstract and conclusion quoted the rounded
day-15 selected rates (`B = 6.30e-2 s^-1`,
`S(F0) = 1.18e-3 s^-1`) and then immediately gave mission-folded sensitivity.
Those numbers were correct, but the prose did not explicitly identify the
rounded `B/S` pair as day-15 selected rates.

The English and Chinese abstract and conclusion now state that the `B/S` pair
is the day-15 selected rate pair, while `Z20d`, `T3sigma`, and `F3sigma` come
from the mission-time fold. No rate, sensitivity, convergence, BGO, or upstream
optics number changed. Both PDFs were recompiled after the wording edit, with
the same clean fatal-error/undefined-reference/undefined-citation status and
the same single 0.90143 pt requirements-table overfull warning.

## Narrow-Line Boundary and Figure-Flow Recheck

This pass revisited Claude R4 from a reviewer-reading perspective rather than
as a numerical audit. The current authority values remain the post-R4 M=50000
CsI exact-position values, and no rate or sensitivity number was changed.

Two manuscript-facing boundary issues were tightened:

- The hard-window sensitivity is now explicitly limited to a line whose
  intrinsic width remains small compared with the \(510.58\)--\(511.42\) keV
  analysis window after detector response. The English and Chinese selection
  sections now state that broader source lines require convolving the source
  line profile with the detector response and re-optimizing or widening the
  analysis window.
- Five figure introductions per language were moved ahead of the corresponding
  figure environments, covering the optics schematic/spot figures, the
  EXPACS/PARMA full-sphere flux figure, the delayed exact-position distribution
  figure, and the exact-position sampling-necessity figure. This was an
  editorial flow fix only; no figure file, caption, label, or numerical content
  changed.

Both PDFs were rebuilt after the edits:

- `balloon511_nima_draft_en.pdf`, 2,984,636 bytes, 2026-06-17 05:51:21 +0800.
- `balloon511_nima_draft_zh.pdf`, 3,319,516 bytes, 2026-06-17 05:51:21 +0800.

Final checks:

- Fatal LaTeX / undefined citation / undefined reference scan: no matches.
- Citation closure: 25 cited keys and 25 bibliography entries in each draft;
  no missing or uncited entries.
- Label closure: 34 labels in each draft; no missing references.
- Float-reference closure: 17 figure/table labels in each draft; all referenced,
  and each first prose reference now appears before the corresponding label in
  source order.
- Targeted internal-terminology scans over the main TeX files and included
  tables: no matches for `FREF`, `HEADLINE`, `EVENTLIST`, `reject-kept`, literal
  `W2`, `v3p5`, `center-finger`, or related audit wording.
- Chinese draft scan: no visible `day-15` or old `transition-edge sensor（TES）`
  introductory form.
- Overfull scan: only the existing 0.90143 pt requirements-table warning remains
  in each draft.
- `git diff --check`: clean.

## Current Workspace Recheck Against Claude R4

This pass re-read Claude R4 and rechecked its high-risk items against the current
workspace state. No simulation product, manuscript number, or source code was
changed in this pass.

- Exact-position convergence still supports only a total selected line-window
  and significance claim, not an isolated delayed-subcomponent plateau:
  `PASS_EXACTPOS_TRANSPORT_CONVERGENCE`, `PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY`,
  total line-window background relative range `0.0111914918`, `Z20d` relative
  range `0.00550844085`, and delayed-subcomponent relative range `0.187412720`.
- The M=50000 source-card audit remains closed at source-definition level:
  `50000` parsed point-source samples, manifest activity
  `85.63669586527698 Bq`, manifest flux relative delta `0.0`, coordinate
  back-match fraction `1.0`, and missed-nuclide activity `0.0574501262 Bq`
  (`6.7086e-4` of total activity).
- Claude R4's BGO ratios are historical because they used the older CsI
  baseline. The current BGO-vs-CsI status is
  `PASS_BGO_SAMPLE_VS_CSI_EXACTPOS_M50000_COMPARISON`; it is a
  material-design-threshold control with CsI/BGO thresholds `50/70 keV`, not a
  same-threshold veto scan. Current BGO/CsI ratios are `0.915190777` for
  mission-mean line-window background, `1.049646589` for `Z20d`, and
  `0.952701615` for the 20-d flux threshold.
- The signal metadata issue remains fixed in the convergence authority:
  `w2_signal_cps_at_1e_4 = 0.0011811656293957314`; the old unit-area proxy is
  separately named as `w2_signal_unit_area_proxy_cps_at_1e_4 =
  7.957466258001846e-05`.
- The f10m optical authority policy now states that f10m is the current optical
  authority after detector-coupling, source-normalization, and significance
  reruns. Recomputing `81 * diffraction_fraction * within_be_fraction` gives
  `20.08476 cm2`.
- The Step11 upstream Ge-proxy delayed side component remains a boundary
  calculation: isolated activity `0.42567438 Bq`, `scaled_production_yield =
  0.25`, zero selected line-window events, and a 95% zero-count upper rate
  `1.2534045848433615e-4 s^-1`. The `0.25` factor remains a bookkeeping
  provenance item, not a current headline-rate driver.
- The active English and Chinese manuscripts contain the necessary R4 boundary
  wording: retained reconstruction-reject events are not a conservative
  sensitivity lower bound; BGO is explicitly not a same-threshold veto scan; M
  convergence is limited to total selected line-window background and
  significance; and the atmospheric transmission is a baseline pointing
  normalization rather than a universal balloon-pointing value.

Residual review items are governance rather than current rate/sensitivity
closures: the working tree still has many modified or untracked paper-facing
artifacts, and the active core-document dangling-path cleanup is not finished.
`git diff --check` is clean.

## User-Requested Fresh Recheck Pass

This pass reread `core_md/CLAUDE_REVIEW_TES511_BALLOON_20260616_R4.md` and
checked its high-risk claims directly against the current JSON, manuscript, and
paper-resource files.

- Claude R4's main science-boundary findings remain valid as review pressure:
  M-sampling convergence should be claimed only for the total selected line
  window and significance, BGO-vs-CsI is a material-design-threshold control
  rather than a same-threshold veto scan, retained reconstruction rejects are
  not a conservative sensitivity lower bound, and the atmospheric transmission
  is a baseline pointing normalization.
- The current authority files still support the post-R4 M=50000 paper-facing
  chain: exact-position transport convergence status
  `PASS_EXACTPOS_TRANSPORT_CONVERGENCE`, total line-window background relative
  range `0.0111914918`, `Z20d` relative range `0.00550844085`, and delayed
  subcomponent relative range `0.187412720`.
- The current M-sampling audit is still `PASS_M_SAMPLING_AUDIT`; the nominal
  source-card case uses 50,000 point-source samples, conserves
  `85.63669586527698 Bq` at manifest level, has coordinate back-match fraction
  `1.0`, and leaves `0.0574501262 Bq` of unsampled-nuclide activity
  (`6.7086e-4` of total activity).
- The current BGO comparison schema uses rows `CsI_exactpos_m50000` and `BGO`.
  The active-veto thresholds are `50/70 keV`, and the current BGO/CsI ratios
  remain `0.915190777` for mission-mean line-window background, `1.049646589`
  for `Z20d`, and `0.952701615` for the 20-d flux threshold.
- The signal metadata issue identified by Claude R4 remains fixed:
  `w2_signal_cps_at_1e_4 = 0.0011811656293957314`, while the old unit-area
  proxy remains separated as
  `w2_signal_unit_area_proxy_cps_at_1e_4 = 7.957466258001846e-05`.
- The f10m optical authority policy still states that f10m is the current
  optical authority, and recomputation gives `20.08476 cm2`.
- The Step11 upstream active-Ge proxy delayed side component remains a boundary
  result: isolated activity `0.42567438 Bq`, `scaled_production_yield = 0.25`,
  zero selected line-window events, and a 95% zero-count upper rate
  `1.2534045848433615e-4 s^-1`. The `0.25` factor is still only a bookkeeping
  provenance item for this zero-selected-event side component.

One new stale paper-resource artifact was found during this pass:
`fig_requirements_chain.svg` and its caption still described themselves as the
"current" exact-position figure but showed the older M=5000 values
`B/S = 0.0624651 / 0.00118117 cps`, `Z20d = 6.15522`, and
`F3 = 4.87391e-5`, plus the old delayed component `0.00338234 cps`. These
files are not referenced by the current manuscript, but they are listed as
editable paper resources and could mislead a future figure pass. They were
updated to the M=50000 sampled-position values:
`B/S = 0.0629804 / 0.00118117 cps`, `Z20d = 6.13039`,
`F3 = 4.89365e-5`, and delayed component `0.00389764 cps`; the visible
internal labels `W2`, `Step07`, and `exact-position M/seed` were also replaced
with paper-facing wording.

## User-Requested Claude Review Recheck, Current Workspace

This pass reread the latest local Claude review,
`core_md/CLAUDE_REVIEW_TES511_BALLOON_20260616_R4.md`, and rechecked its
paper-facing risk items against the current JSON schemas and manuscript text.
The result remains stable: Claude R4's boundary warnings are mostly valid, but
the active manuscript now uses the post-R4 M=50000 CsI sampled-position
authority and carries the necessary caveats.

- Exact-position convergence remains closed at the total selected line-window
  and significance level, not as an isolated delayed-subcomponent plateau:
  `PASS_EXACTPOS_TRANSPORT_CONVERGENCE`,
  `PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY`, total line-window background
  relative range `0.0111914918`, `Z20d` relative range `0.00550844085`, and
  delayed-subcomponent relative range `0.187412720`.
- The signal-rate metadata issue identified by Claude remains fixed:
  `w2_signal_cps_at_1e_4 = 0.0011811656293957314`; the old unit-area proxy is
  stored separately as `w2_signal_unit_area_proxy_cps_at_1e_4 =
  7.957466258001846e-05`.
- The M=50000 source-card audit remains closed at source-definition level:
  50,000 parsed point-source blocks, manifest activity
  `85.63669586527698 Bq`, manifest flux relative delta `0.0`, coordinate
  back-match fraction `1.0`, and unsampled-nuclide activity `0.0574501262 Bq`
  (`6.7086e-4` of total activity).
- The BGO comparison remains a material-design-threshold control, not a
  same-threshold veto scan. Current rows use CsI/BGO thresholds of `50/70 keV`;
  BGO/CsI ratios are `0.915190777` for mission-mean line-window background,
  `1.049646589` for `Z20d`, and `0.952701615` for the 20-d flux threshold.
- The f10m optics authority still recomputes to `20.08476 cm2`, and its policy
  text states that f10m is the current paper-facing optical authority after
  downstream detector coupling, source normalization, and significance reruns.
- The upstream active-Ge proxy delayed component remains a boundary result:
  isolated activity `0.42567438 Bq`, `scaled_production_yield = 0.25`, zero
  selected line-window events, and a 95% zero-count upper rate
  `1.2534045848433615e-4 s^-1`. The `0.25` factor remains a bookkeeping
  provenance item for a zero-selected-event side component, not a current
  headline-rate driver.

The active English and Chinese manuscripts already reflect these boundaries:
the retained reconstruction-reject policy is not described as a conservative
sensitivity lower bound; atmospheric transmission is identified as a baseline
pointing normalization; the BGO row states the `50/70 keV` material-specific
veto thresholds; and convergence is limited to total selected line-window
background and significance. A targeted search found the older M=5000 values
only in the explicit convergence-case rows, not as the primary result.

One non-referenced paper-resource figure still carried the internal text
`Authority: Step04/Step09`. It has been changed to `Authority: optics and
detector-coupling reports`, and the footer now says `sampling-size/seed
convergence reports`. No manuscript number, simulation product, or PDF content
changed in this pass. Residual Claude R4 items remain governance/validation
items: commit the current paper-facing artifacts, clean active-doc dangling
paths, trace the upstream `0.25` factor for bookkeeping, and run a future
Revan/Mimrec or same-threshold BGO scan only if those become paper claims.
