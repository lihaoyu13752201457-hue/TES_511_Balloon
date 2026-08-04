# EA S3d existing-evidence closure

This package reconciles manuscript claims against retained Mass_model_511 and
S3d/O8 products. It does not launch Monte Carlo transport.

The first analysis reads the retained 380,872-row exact-position activation
table, reconstructs incident-family and material-category activity fractions,
and cross-checks them against the existing ground-state-corrected inventory.
It is intended to replace stale manuscript language that says the reference
material fractions or detector-selected delayed behavior have not been
evaluated.

Run:

```bash
python3 engineering/ea_s3d_existing_evidence_closure_20260713/code/analyze_mass_activation_materials.py
```

Outputs are written under `data/`. The final S3d delayed branch remains
explicitly neutron-induced; the Mass_model_511 all-family inventory is used as
the reference background-origin authority, not as an unlabelled substitute for
the final geometry.

## Result

Status: `PASS_MASS_ACTIVATION_MATERIAL_FAMILY_AUDIT`.

- The retained table contains 380,872 weighted production rows and closes to
  141.833438 Bq within `6e-9 Bq` of the retained source authority.
- Incident-family activity: neutron 94.246%, mu-minus 5.381%, and all other
  producing families 0.373% combined.
- Material activity: CsI 63.077%, outer mechanics 15.709%, cold plates 9.433%,
  passive W/collimator 5.677%, window 3.471%, other internal structures 2.572%,
  and TES volumes 0.060%.
- The neutron and mu-minus material distributions differ with
  `D_TV = 0.822756`; this supports retaining production-family/material/position
  correlations in the reference source.
- The active English and Chinese manuscripts now report these source-level
  quantities separately from the 26 response-convolved delayed records selected
  at detector level.

Validation:

```bash
python3 engineering/ea_s3d_existing_evidence_closure_20260713/code/validate_existing_evidence_manuscript_sync.py
```
