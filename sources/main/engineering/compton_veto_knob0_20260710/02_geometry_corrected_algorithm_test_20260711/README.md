# Geometry-corrected Knob0 algorithm test

Status: `PASS_GEOMETRY_CORRECTED_KNOB0_TEST_VALIDATION`  
Date: 2026-07-11  
Decision: `NO_OBSERVED_KNOB0_ALGORITHM_BENEFIT`

## Recorded disposition

The concise review record, including the separation between the negative
algorithm decision and the not-yet-authoritative geometry repair, is in
[`FINDINGS_RECORD_20260711.md`](FINDINGS_RECORD_20260711.md).

## Answer

The tested Knob0 algorithms do **not** improve the retained data.

- Geometry correction is required as a reconstruction-correctness repair, but
  it is not a sensitivity gain: relative to the corrected baseline, the old
  implementation has a nearly identical prompt+delayed `S/sqrt(B)` proxy
  (`x1.00118`).
- The geometry-corrected Mass_model_511 prompt and delayed W2 survivors contain
  **zero** `L >= 20 mm` long-arm events. The focused signal contains `934`.
  Long-arm tightening therefore has no background target population.
- Fluorescence merging rejects `0` prompt/delayed events and rejects `43`
  focused-signal events (`S x0.998527`, `B x1`, relative `S/sqrt(B) x0.998527`).
- Tightening at `k=2` rejects `0` prompt/delayed events and `5` signal events
  (relative `S/sqrt(B) x0.999829`). `k=2.5` and `k=3` are no-ops.
- On the S3c 3M atmospheric-511 sample, geometry correction changes the current
  baseline from `6` to `7` by retaining event `30621`; every monotonic Knob0
  candidate remains `7 -> 7`.

Do not promote fluorescence merging or long-arm tightening into either the
Mass_model_511 or S3c W2 selection chain. Retain Knob0 as a documented negative
result. Treat the pixel-position correction as a separate maintenance task that
requires response-level closure before replacing Step05 authority.

## Test design

No new transport was run. The replay uses:

- the retained Mass_model_511 Step05 event catalog (`1,765,451` catalog events;
  `30,404` W2 active-pass events tested);
- all eight retained S3c atmospheric-511 W2 active-pass events;
- the exact TES pixel centers and local pixel dimensions parsed from each
  geometry;
- the retained `InstrumentFrame.Rotation 0 45 0` transform;
- the existing side-window disk and current Compton ordering implementation.

Four policy families were evaluated symmetrically on prompt, delayed, and
focused signal:

1. `legacy_current`: energy-weighted CC-HIT position plus the old axis-aligned
   representative box.
2. `geometry_current`: pixel UID center plus all eight corners of the actual
   rotated `3.0 x 1.5 x 1.5 mm` absorber.
3. `geometry_fluorescence_merge`: relative to `geometry_current`, tag a runtime
   Ta K-line hit only when a same-layer parent is within `3.2 mm`; merge the
   satellite energy into the nearest parent, conserve total event energy, and
   reconstruct. The policy is monotonic and never resurrects a veto.
4. Geometry-corrected long-arm tightening, with and without fluorescence
   merging, for frozen `k=2, 2.5, 3`. The event-specific position uncertainty is
   propagated from the rotated voxel covariance; the assumed Doppler sigma is
   `3 deg` and the detector energy sigma is `0.14 keV`.

The runtime MC tag centers were frozen from the independent S3c IA-PHOT audit:
`56.402`, `57.686`, `65.381`, and `67.523 keV`, each with a `+/-0.42 keV`
window. These values were not tuned on the Mass_model W2 result.

## Mass_model_511 result

| Policy | Signal rate | Prompt+delayed rate | Relative `S/sqrt(B)` vs corrected |
|---|---:|---:|---:|
| legacy current | 0.798166 | 0.0480735 | 1.001181 |
| geometry current | 0.784696 | 0.0465745 | 1.000000 |
| fluorescence merge | 0.783540 | 0.0465745 | 0.998527 |
| tight `k=2` | 0.784562 | 0.0465745 | 0.999829 |
| tight `k=2.5` | 0.784696 | 0.0465745 | 1.000000 |
| tight `k=3` | 0.784696 | 0.0465745 | 1.000000 |
| merge + tight `k=2` | 0.783433 | 0.0465745 | 0.998390 |

The `S/sqrt(B)` values are a comparison proxy for the retained Mass_model
prompt+delayed streams only. Atmospheric-511 belongs to the separate S3c
geometry sample and is intentionally not mixed into this number.

### Geometry-corrected survivor strata

| Stream | Single | S1 `<8 mm` | S2 `8-20 mm` | S3 `>=20 mm` |
|---|---:|---:|---:|---:|
| prompt | 43 | 19 | 1 | **0** |
| delayed | 20 | 6 | 1 | **0** |
| focused signal | 17589 | 8088 | 2575 | **934** |

This is the decisive mechanism test: an S3-only cut cannot reduce the measured
prompt/delayed W2 background because there are no S3 background survivors.

## Geometry correction diagnostic

The legacy implementation is reproduced exactly:

| Stream | Legacy authority | Geometry-corrected diagnostic |
|---|---:|---:|
| Mass prompt | 65 | 63 |
| Mass delayed | 28 | 27 |
| Mass signal | 29687 | 29186 |
| S3c atm511 | 6 | 7 |

Across Mass_model_511, geometry correction changes four prompt decisions, one
delayed decision, and 745 signal decisions. S3c event `30621` is also changed.
The large paired movement confirms that the old truth-position/axis-aligned-box
implementation is not a harmless coordinate convention. It does **not** show
that the corrected implementation improves sensitivity; it must be validated
as a baseline repair on an independent detector-response chain.

## Data-quality and interpretation boundary

- All Mass catalog field lengths and pixel spans agree; all `2,256` TES pixel
  UIDs map to the geometry; composite `(stream, source file, event ID)` keys
  have zero duplicates.
- The old Mass final counts (`65/28/29687`) and old S3c final count (`6`) are
  independently reproduced before applying any correction.
- All candidate policies pass the monotonic invariant: zero corrected-baseline
  vetoes are resurrected.
- Fluorescence merging conserves total energy and reduces the hit count for
  every merged event.
- The event catalog stores unsmeared CC-HIT energies. Consequently, the
  fluorescence test is optimistic about line identification and is not a full
  detector-response convolution. Since even this optimistic test rejects no
  background, adding realistic smearing cannot support a positive promotion
  claim without new contrary evidence.
- The cached Mass focused-signal catalog is retained, but its original SIM path
  is no longer present. This test is reproducible from the transformed cache;
  a future authority replacement still needs a raw-SIM or independent-response
  closure.
- Background counts remain small. This package reports an observed negative
  result, not a universal theorem that every future geometry has zero algorithm
  opportunity.

## Artifacts

- `data/geometry_corrected_knob0_test_summary.json`: definitions, provenance,
  QA, policy yields, strata, and decision.
- `data/mass_model_511_w2_event_audit.csv`: all `30,404` Mass W2 active events.
- `data/s3c_atm511_w2_event_audit.csv`: all eight S3c atmospheric-511 events.
- `data/tagged_event_audit.csv`: K-tagged or merge-eligible subset.
- `data/policy_yields.csv`: event and weighted-rate yields by stream/policy.
- `data/mass_model_511_significance_proxy.csv`: symmetric signal/background
  comparison.
- `data/geometry_current_strata.csv`: corrected survivor topology distribution.
- `data/policy_transitions.csv`: paired transition counts.
- `data/validation_result.json`: independent validator output.

## Reproduce

```bash
python3 code/run_geometry_corrected_knob0_test.py
python3 code/validate_geometry_corrected_knob0_test.py
```

The replay is read-only and normally completes in about one minute. All new
outputs remain inside this dated package.
