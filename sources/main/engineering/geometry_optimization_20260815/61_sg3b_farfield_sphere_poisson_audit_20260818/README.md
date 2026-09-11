# SG3B far-field sphere and common-time audit

This is a non-overwriting, no-transport audit of two normalization boundaries:

1. the actual MEGAlib `FarFieldAreaSource` launch-area semantics and the SG3B
   `SurroundingSphere` relationship to the retained mass-model envelope;
2. the distinction between the package-58 analytic superposition of independent
   Poisson rates and a literal event/deposit overlay on a detector time axis.

The package reads only geometry/source text, the retained compact geometry mesh,
receipt-derived CSV/JSON products, and implementation source code. It does not
open a SIM payload, run Cosima, rerun detector response, or modify the paper.

Run:

```bash
python3 engineering/geometry_optimization_20260815/61_sg3b_farfield_sphere_poisson_audit_20260818/code/build_audit.py
```

