# Derived outputs

Stage directories are created on demand. Raw SIM/DAT files are never copied
here.

- `00_input_audit/input_audit.json`: canonical corrected-keV selection.
- `01_prompt/`: 530-job prompt catalogs, coverage, cutflow, spectrum,
  full-band occupancy, summary and report. Status:
  `PASS__M05_CORRECTED_PROMPT_SCREENING`.
- `02_activation/`: 446-job `sum(RP)/sum(TT)` cell table, 15,022-row
  state-aware day-15 inventory, exact-position delayed-source index, summary
  and report. Status:
  `PASS__M05_CORRECTED_ACTIVATION_INVENTORY_READY__DELAYED_TRANSPORT_INCOMPLETE`.
- `03_delayed/`: 15 transported positive-ground-state cell catalogs plus the
  explicit Mass_model_511/muplus zero-source stub, 3,750,000-trigger raw
  semantic scan, parent-lineage mapping, and 50k/10k/realized source-mix QA.
  Status: `PASS__M05_CORRECTED_DELAYED_RAW_CATALOG_15_SOURCE_CELL_COMPLETE`.
- `04_common_response/`: common keyed response for prompt, delayed, and reused
  focused signal; nominal 50-keV exact veto, Step05, spectra, multiplicity,
  occupancy, PSF, and selected W2 lineage. Status:
  `PASS__M05_CORRECTED_COMMON_RESPONSE_PROMPT_DELAYED_SIGNAL_COMPLETE`.
- `05_matched_comparison/`: Mass reference W2 budget and matched Mass/S3d
  family, parent, material, volume, and detector-plane comparison tables.
  Status: `PASS__M05_CORRECTED_MATCHED_DAY15_COMPARISON__PROMOTION_DEFERRED`.
- `06_mission/`: zero-inventory forward activity from stage-02 production
  rates and dE-integrated 81-node PARMA family ratios, fixed-45-degree slant
  signal, cumulative counts, significance, crossing/extrapolation labels, and
  20-day flux thresholds. This is an analytic family-scalar scenario rather
  than corrected multipoint transport authority. Status:
  `PASS__M05_CORRECTED_81BIN_FORWARD_ANALYTIC_SCENARIO__PROMOTION_DEFERRED`.
- `07_paper_registry/`: 52 machine-readable paper-number keys and an 18-object
  M05 figure/table/claim disposition map. It retires old simulation-derived
  M05 numbers and marks mission values as analytic-scenario-only. Status:
  `PASS__M05_PAPER_NUMBER_AND_OBJECT_REGISTRY_READY__MANUSCRIPT_NOT_EDITED`.
