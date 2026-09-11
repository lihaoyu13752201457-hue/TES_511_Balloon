# TES-511 particle-source unit evidence audit

Audit date: 2026-08-11. Retained project inputs were read only; no retained
Mass_model_511 or geometry-optimization product was overwritten.

## Bottom line

The three retained eight-family continuum-source packages contain 480/480
`Spectrum File` references to `cosima_spectra_dp_2602units/`. Cosima interprets
the DP x coordinate as total kinetic energy in keV, while every x in that
legacy tree is exactly 0.001 times the independently reconstructed correct
value. All eight incident-particle families are therefore transported at
1/1000 of their intended total kinetic energy. Explicit Flux, angular-bin, and
R=60 cm normalization arithmetic pass locally and must not be rescaled during
the energy-axis repair.

## Primary deliverables

- `report/TES_511_particle_source_unit_evidence_20260811.pdf` — five-page A4
  Chinese technical summary with evidence chart, verdict tables, source
  locators, limitations, and repair requirements.
- `report/TES_511_particle_source_unit_evidence_20260811.html` — self-contained
  static source used to print the PDF.
- `report/artifact.json` — canonical report manifest and reviewed snapshot.
- `data/audit_summary.json` — machine-readable headline verdict and supporting
  evidence.
- `data/spectrum_family_audit.csv` — exhaustive family-level raw/correct/legacy
  comparisons.
- `data/source_package_reference_audit.csv` and
  `data/source_card_family_audit.csv` — exhaustive source-card reference,
  solid-angle, and Flux audits.
- `data/evidence_hashes.csv` — SHA-256 inventory for 525 evidence files.
- `report/evidence/MEGALIB_CONTRACT.md` and
  `report/evidence/PROJECT_SOURCE_CHAIN.md` — precise manual pages, source-code
  lines, project paths, and interpretation boundaries.

## Reproduce the evidence

Run from the repository root:

```bash
python3 engineering/particle_source_unit_audit_20260811/code/audit_particle_source_units.py
python3 engineering/particle_source_unit_audit_20260811/code/render_family_chart.py
python3 engineering/particle_source_unit_audit_20260811/code/build_report_artifact.py
node /home/ubuntu/.codex/plugins/cache/openai-curated-remote/data-analytics/0.2.8-13ceeea1f599/skills/build-report/scripts/build_portable_artifact.mjs \
  --input engineering/particle_source_unit_audit_20260811/report/artifact.json \
  --output engineering/particle_source_unit_audit_20260811/report/TES_511_particle_source_unit_evidence_20260811.html
python3 engineering/particle_source_unit_audit_20260811/code/apply_print_overrides.py
```

The final HTML is printed with the locally installed Chromium headless shell.
See `report/QA_REPORT.md` for the verified PDF properties and checks.

## Important authority boundary

- Geometry and material definitions may remain useful as structural inputs.
- Existing prompt performance, activation inventory, delayed rates, and
  simulation-derived geometry rankings are not physical authorities until the
  eight source families are repaired and the chain is rerun.
- The standalone PARMA 511-keV mono source passes at source level.
- The retained EventList passes its 15-field s/cm/keV format audit; its 1 ns
  timestamp spacing is event ordering, not balloon exposure.
