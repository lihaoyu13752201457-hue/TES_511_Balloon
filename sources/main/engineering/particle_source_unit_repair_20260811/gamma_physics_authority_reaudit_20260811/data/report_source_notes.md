# Gamma physics authority re-audit — report source notes

## Reporting job

- Question: does the corrected-keV gamma result establish a physically credible TES background or sensitivity, and why did 100,000 primaries produce about 100 TES-positive events?
- Audience: technical.
- Scope: the corrected-keV instant gamma batch0001 sample only; 100,000 primaries and about 1.85 s per geometry.
- Baseline: Mass_model_511 versus S3d-O8; unvetoed measured TES events versus an explicit physical active-shield diagnostic.
- Decision-useful outcome: separate source-unit correctness, gross prompt transfer, formal background selection, and mission sensitivity; identify the next authority-restoring benchmark.
- Delivery mode: one self-contained portable HTML report generated from canonical `artifact.json`.

## Required-structure mapping

1. Title: report title block.
2. Technical summary: `单位修复成立，物理权威仍未成立`.
3. Key findings with visual evidence: native grouped cutflow bar plus adjacent interpretation.
4. Scope, data, and metric definitions: explicit primary, TT, response-integral, and sensitivity denominators.
5. Methodology: SIM event parsing, deterministic response, windows, and geometry-specific active-volume whitelists.
6. Limitations, uncertainty, and robustness: threshold scan, zero-count limit, and missing Step05/full-chain closure.
7. Recommended next steps: freeze unit repair, close selection contract, run response benchmarks, then scale statistics.
8. Further questions: threshold/timing authority, environmental benchmark, and line/continuum definition.

## Evidence and authority boundaries

- The source contract proves the MeV-to-keV abscissa repair and unchanged absolute Flux; it does not prove detector-response or sensitivity authority.
- The A/B summary provides primary counts, TT, inclusive TES-positive counts, and pre-veto energy-window counts.
- The event-level re-audit provides the explicit CsI/BGO whitelist cutflow and excludes passive Kapton volumes with misleading active-shield-like names.
- The normalization audit provides FarField normalization, energy-band flux, paper-comparison framing, and Poisson upper limits.
- The official paper sources are arXiv v3 and the published DOI record. The report intentionally does not use the optics effective-area number because revisions differ; the stable comparison used here is the paper's approximately 60 Hz mass-scaled gross background estimate and its explicit detector thresholds/model shape.
- Snapshot status is `partial`: formal Step05 timing/whitelist closure and the corrected all-family prompt-to-delayed response chain are required data for a physical background or sensitivity claim.

## Chart contract and map

- Segment: active-shield cutflow.
- Analytical question: how much of the 101/99 inclusive TES-positive count survives a physically explicit same-event active-shield veto, overall and in two energy windows?
- Takeaway: gross events collapse to 12/3; all 15 strict-W2 events are shield-coincident and the diagnostic W2 survivors are zero in both geometries.
- Family/type: comparison; grouped vertical bar.
- Fields: category on x, event count on y, geometry as the visible series; TT, primary count, selection, veto state, threshold, and rate remain in the reviewed dataset/tooltips.
- Data sufficiency: 12 reviewed rows, representing six ordered stages and two geometries. This is a discrete cutflow, not a time trend.
- Palette: hard two-root categorical policy (blue/orange roots selected by the shared reader), with direct value labels and axis/legend labels so color is not the only distinction.
- Scale: absolute event counts with a zero baseline; no per-series normalization.
- Final surface: native chart inside the canonical portable HTML artifact; semantic chart-data table retained for no-script/print conversion.
- Caveat: the chart uses 80 keV for the representative physical-volume veto; the exact table shows that S3d-O8 gives the same 3/0/0 result at 50, 70, and 80 keV, and Mass gives 12/1/0 at all three thresholds in this sample.

## Exact table contract

- Grain: one geometry/gate/threshold configuration.
- Counts: inclusive measured TES-positive, measured 480–550 keV, and measured W2 `[510.58, 511.42)`.
- Response: 420 eV FWHM per pixel, 0.3 keV post-noise pixel threshold, deterministic geometry-specific seed.
- Timing boundary: no 1 microsecond association replay, Compton/FoV selection, formal Step05, activation, delayed component, or mission timeline.

## Omitted or deferred metrics

- No minimum detectable flux or 3-sigma/5-sigma sensitivity is calculated: the authoritative post-selection background and dedicated focused-signal effective area are missing.
- No focused 511-keV effective area is inferred from broadband W2 counts: off-diagonal high-energy pair-production feeddown dominates this sample.
- No geometry promotion is recommended: corrected all-family prompt/activation/delayed/response closure is incomplete.
