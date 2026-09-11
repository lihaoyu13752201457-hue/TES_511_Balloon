# Corrected-keV composite partial postprocess (2026-08-12)

This non-overwriting package combines only observed, independently validated
jobs from batch0000/1/2, the batch0003 ordinal-76 gamma prefix, the batch0004
contiguous partial authority through ordinal 97, and the batch0005 reduced-
breadth add-on. It does not require or imply a batch0004 final authority.

All 28 `geometry x mode x family` cells remain independent. Prompt uses only
instant SIM payloads and applies per-event/per-physical-pixel aggregation, the
420 eV FWHM keyed Gaussian response, 0.3 keV post-noise pixel threshold, the
exact Mass CsI or O8 BGO+plastic veto whitelist, and 480--550/W2 windows.
Buildup uses only DAT RP records and divides each volume/isotope/excitation
sum(RP) by the full cell sum(TT), including TT from zero-RP jobs.

Untransported target exposure is missing data, never a zero observation. The
result is heterogeneous reduced-statistics screening evidence only: not full
statistics, delayed transport, mission response/sensitivity, or geometry-
promotion authority.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  engineering.particle_source_unit_repair_20260811.composite_partial_postprocess_20260812.tests.test_composite_partial
python3 engineering/particle_source_unit_repair_20260811/composite_partial_postprocess_20260812/code/analyze_composite_partial.py --pin-authorities
python3 engineering/particle_source_unit_repair_20260811/composite_partial_postprocess_20260812/code/analyze_composite_partial.py --check-inputs-only
python3 engineering/particle_source_unit_repair_20260811/composite_partial_postprocess_20260812/code/analyze_composite_partial.py --run
```
