# EA statistics and shield-design rewrite audit — 2026-07-12

## Status

**PASS — active English and Chinese manuscripts rebuilt, compiled, and reconciled to the retained simulation authorities.**

The active sources are `balloon511_ea_draft_en.tex` and
`balloon511_ea_draft_zh.tex`. Their root-level PDFs are the current reading
copies. The files under `recovered_compile_ready/` remain frozen recovery
mirrors and were not synchronized by this revision.

## Scope of this revision

This pass rebuilt the design-comparison/statistical-analysis method and the
corresponding Results section from the evidence chain. Outside that scope, it
rewrote only the English and Chinese abstracts and the final Conclusions
subsections. It did not intentionally revise the Introduction, detector and
cryostat description, source generation, event-selection implementation,
mission-fold derivation, Discussion body, limitations, or bibliography.

The Chinese keyword line was retained in its pre-revision form. It contains
seven terms; reducing it to the journal's requested four to six keywords is a
separate submission-metadata edit, not part of this scoped text revision.

## Evidence hierarchy and public comparison language

The manuscript now separates three roles that had previously been conflated:

1. The retained Mass_model_511 detector calculation is the **reference
   detector**. It establishes the complete selected-background budget and the
   physical channels that motivate optimization. It is not a mass denominator.
2. The matched BGO/W configuration with 40/40/40 mm BGO, 2 mm external W,
   3 mm Al, and Kapton is the **full-coverage design control**. This is the only
   mass comparator in the paper.
3. The retained optimized result is the **directionally graded design**:
   40/30/10 mm side/bottom/top BGO, no external W, 3 mm Al, and Kapton.

The manuscript also names the failed design descriptively as the
**uniform-thinning trial**. Project-internal geometry and campaign labels are
absent from both active manuscripts. The audit script explicitly rejects
`S3c`, `S3d`, numbered optimization aliases, maintenance-stage labels, and
recovery terminology.

## Rebuilt design logic

The public argument now runs in the following order:

1. Decompose the reference primary-window background by incident family,
   delayed origin, rate share, and Monte Carlo precision.
2. Use the observed dominance of incident positrons and neutrons, together
   with the spectrally inseparable atmospheric 511 keV line, to define the
   matched screening subset.
3. Freeze the background and focused-acceptance gates before comparing designs.
4. Test uniform active-shield thinning first. Its lower mass is rejected because
   the matched rate exceeds the gate and 17 of 18 atmospheric survivors enter
   through the side proxy.
5. Restore side coverage while retaining lower-exposure end-cap thinning and
   removing external tungsten. The directionally graded design passes both
   frozen gates.
6. Promote only the passing design to the all-eight-family prompt,
   neutron-induced delayed, atmospheric-line, focused-signal, and 20-day fold.
7. Report the optimized full chain as an absolute result, not as the isolated
   effect of mass reduction, because a matched all-family/delayed control chain
   does not exist.

This mirrors the useful reporting pattern in the DIXE non-X-ray-background
study and COSI bottom-up balloon-background work: component decomposition,
physical-origin diagnosis, environment or geometry response, external or
mission-level comparison, and explicit claim boundaries.

## Statistical content now exposed

| Analysis block | Quantities reported | Precision treatment |
|---|---|---|
| Reference background | selected records, component rates, weighted Monte Carlo standard errors, relative errors, rate fractions, selected-event origins | weighted-rate counting precision |
| Matched shield screen | component counts/rates, matched-subset rate, entry-direction proxy, signal acceptance, mass components, frozen decision | component Garwood intervals, exact conditional Poisson rate-ratio intervals, Wilson acceptance intervals, Katz acceptance-ratio intervals, paired signal pass/fail counts |
| Optimized cut-flow | pre-veto, active-veto, and final records; active/topology survival; rate and composition | stream-by-stream audit counts |
| Optimized final background | all eight prompt families including zero-count rows, delayed and atmospheric components, unequal event weights | two-sided 95% Garwood intervals and summed conservative upper endpoints |
| Mission projection | day-15 rates, expected counts, T3, T5, Z20d, and 3-sigma flux threshold | central projection plus component-wise Garwood / signal Clopper–Pearson conservative counting envelope |

The paired signal rows use the order both pass / control only / trial only /
neither. Counts are 23,899 / 5,804 / 5,923 / 1,568 for the uniform-thinning
trial and 24,412 / 5,291 / 5,186 / 2,305 for the directionally graded design.

## Audited headline values

- Reference detector background: `(4.80735 ± 0.55202) × 10^-2 s^-1`.
- Reference prompt fraction: `91.71%`; incident positron plus neutron share:
  `96.94%` of prompt and `88.91%` of total selected background.
- Full-coverage control shield-package mass: `391.198847 kg`.
- Directionally graded shield-package mass: `309.776767 kg`.
- Mass reduction relative to that explicit control: `81.422081 kg` or
  `20.8135%`.
- Matched graded-design rate: `4.463791 × 10^-3 s^-1`, below the frozen
  `5.2 × 10^-3 s^-1` gate.
- Focused-acceptance ratio: `0.996465`, Katz 95% interval
  `[0.989267, 1.003715]`.
- Optimized day-15 total background and reference-flux signal:
  `6.106080 × 10^-3 s^-1` and `1.181206 × 10^-3 s^-1`.
- Central 20-day result: `Z = 19.2558`, `F3σ = 1.55797 × 10^-5 ph cm^-2 s^-1`.
- Conservative finite-count envelope: `Z = 6.87834`,
  `F3σ = 4.36152 × 10^-5 ph cm^-2 s^-1`.

## Claim boundaries retained in the paper

- The shield mass is an axisymmetric, pre-window/pre-relief analytic package
  ledger, not payload mass or structural qualification.
- The matched screen is the causal geometry comparison; the optimized full
  chain is an absolute performance calculation.
- Optimized delayed transport covers neutron-induced activation only.
- Native BGO recording and analysis-veto thresholds remain 80 and 50 keV.
- No matched all-eight-prompt plus delayed full-chain control exists.
- The mission result is a rate-level 81-bin fold, not a fresh transport at every
  trajectory bin.
- The finite-count envelope is not a detector, radiation-field, cross-section,
  or reconstruction systematic-uncertainty envelope.
- No flight-qualified sensitivity improvement is claimed.

## Literature and journal-style references consulted

- [Experimental Astronomy submission guidelines](https://link.springer.com/journal/10686/submission-guidelines)
- [Simulation of non X-ray background for the DIffuse X-ray Explorer mission](https://arxiv.org/abs/2604.13569)
- [Bottom-up background simulations of the 2016 COSI balloon flight](https://arxiv.org/abs/2503.02493)

The English abstract contains 205 words after LaTeX stripping, within the
journal's 150–250-word range. Its logic is background problem → common method →
dominant components → constrained design result → final performance → claim
boundary. The Chinese abstract follows the same order.

## Verification

- `latexmk -pdfxe -interaction=nonstopmode -halt-on-error balloon511_ea_draft_en.tex`: PASS, 27 pages.
- `latexmk -pdfxe -interaction=nonstopmode -halt-on-error balloon511_ea_draft_zh.tex`: PASS, 25 pages.
- No LaTeX error, undefined reference/citation, fatal stop, or overfull box is
  present in either current log.
- Visual inspection of the new English and Chinese result pages found no table
  clipping or margin overflow.
- Internal-label scan of both manuscripts: zero hits.
- `validate_o8_manuscript_sync.py`: `PASS_O8_EA_MANUSCRIPT_SYNC`, with
  authority-derived numeric tokens, forbidden-term scan, logs, PDFs, and hashes
  all passing.

The machine-readable validation record is
`engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_manuscript_sync_validation.json`.
