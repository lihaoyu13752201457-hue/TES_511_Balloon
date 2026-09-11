# M06 data-authority and replacement matrix

> **DRAFT — NOT_PUBLICATION_AUTHORITY.** M06 reports only the corrected-keV
> non-full prompt-gamma diagnostic and validated transport-exposure metadata.
> The inherited M05 Methods/Results/Discussion block is enclosed in
> `\iffalse ... \fi` in both TeX files and is not part of the active document.

## Authority classes

- `INTERIM_PASS`: hashes and machine validation pass for the stated, restricted
  diagnostic.
- `PARTIAL_PASS`: a contiguous or reduced-breadth merge authority passes, but
  required scope is absent.
- `BLOCKED`: no corrected-keV physical result may be stated.
- `PUBLICATION_AUTHORITY`: unavailable in M06.

## Evidence matrix

| Evidence stream | Authority and SHA-256 | State | Active M06 use | Explicitly forbidden use |
|---|---|---|---|---|
| Corrected eight-family source contract | `engineering/particle_source_unit_repair_20260811/data/source_contract_manifest.json`; `5424eeca35b20affb153c0e07c31a6582e575f511922bf55f40a5a0f77ab4326` | INTERIM_PASS | Energy-axis equations, 160 spectra, 24 cards, 480 corrected references, zero legacy references | Static generation alone is not transport authority |
| Corrected gamma instant prefix | batch0003 prefix ledger `3519c39d…16fc`; validation `5d2784c9…9813` | PARTIAL_PASS | 2,001,000 primaries and 81 jobs per geometry; TT provenance | Calling it the planned 5M/10M checkpoint or a full gamma authority |
| Gamma TES/veto post-processing | summary `08e43171…ad2`; validation `8012f103…a7f` | INTERIM_PASS | Counts, rates, Garwood/Wilson intervals by geometry, selection, and window; validated TES/veto figures | Activation, delayed, Step05/FoV, total-background, sensitivity, or geometry-promotion claims |
| Batch0004 partial checkpoint | umbrella ledger `b4de513e…ba0`; validation `3d29449d…291` | PARTIAL_PASS | 194 jobs, 2,235,468 new events, per-stage/per-geometry TT and RP exposure metadata | Treating missing stages as zero; a seven-family total; canonical batch0004 final |
| Batch0005 reduced-breadth add-on | final ledger `670bc6f1…1a0`; validation `d100985b…cee` | PARTIAL_PASS | 16 jobs, 27,340 events, seven reduced-breadth stage pairs, TT/RP exposure metadata | Relabelling as 1M-equivalent, batch0004 final, or seven-family completion |
| Proton weighted coverage | no accepted M06 input | BLOCKED | State that proton closure is absent | Eight-family total or removal of untransported energy bands without a closure test |
| Activity-normalized isotope inventory | corrected BUILDUP tallies exist, but no accepted inventory build | BLOCKED | RP record counts and sums only, labelled as raw production tallies | Writing RP as Bq, accumulated inventory, or delayed count rate |
| Delayed-decay transport | no corrected-keV delayed chain | BLOCKED | State the missing gate | Any inherited M05 delayed number, isotope ranking, or delayed spectrum |
| Common detector-response closure | gamma-only response diagnostic passes; all-stream closure absent | BLOCKED | Gamma-only keyed response definition | Full prompt-plus-delayed background or signal/background comparison |
| Geometry comparison/promotion | only corrected gamma is selected; other streams incomplete | BLOCKED | Descriptive gamma-only contrast with exact intervals | S3d-O8 promotion, total shield gain, or final design claim |
| Mission fold, significance, sensitivity | upstream gates are open | BLOCKED | State that no corrected value is reported | Any inherited M05 mission counts, significance, or flux threshold |

## Active numerical mapping

All exact values are stored in `manuscript_numbers.json` rather than copied
from terminal output.

| Registry object | English locations | Chinese locations |
|---|---|---|
| `source_contract` | corrected-keV Methods | 更正 keV 方法 |
| `gamma_cutflow_by_geometry_selection_window` | `tab:m06_gamma_cutflow`; prompt-gamma Results | `tab:m06_gamma_cutflow_zh`; 瞬发 gamma 结果 |
| `transport_exposure_by_batch_stage_geometry` | `tab:m06_transport_exposure`; continuation Methods/Results | `tab:m06_transport_exposure_zh`; 补充输运方法/结果 |
| `blocked_claims` | mission block, limitations, conclusion | 任务闭合限制、适用范围、结论 |

## Interpretation guardrails

1. Gamma rates use `count / sum(positive matching ledger TT)` inside one
   geometry and stream. Rate intervals are exact two-sided 95% Garwood
   intervals divided by the same TT; efficiencies use Wilson intervals.
2. S3d-O8 veto rows combine the listed BGO threshold with a fixed 50 keV
   plastic threshold. Mass_model_511 rows use the physical CsI volumes.
3. The gamma figures are non-full prompt diagnostics. They are not an
   eight-family background spectrum.
4. RP records and `sum_RP` are kept only to document BUILDUP support. They have
   no activity or delayed-rate unit.
5. Batch0004 and batch0005 remain separate authorities. Their events are not
   silently pooled into a completed seven-family estimate.
6. The `unit_only_total_gamma` profile receives no added mono-511 stream.
7. Publication remains blocked until proton, activation/delayed, common
   response, mission normalization, and independent bilingual review close.
