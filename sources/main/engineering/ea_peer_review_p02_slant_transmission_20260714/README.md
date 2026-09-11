# EA peer-review P02 slant-transmission correction

This package answers review item P02-02 without overwriting the retained S3d-O8
all-eight-family mission product.  The retained atmosphere curve used the
vertical residual column.  The paper geometry instead fixes the optical axis at
45 degrees elevation (45 degrees zenith angle), so this package applies the
plane-parallel slant factor

\[
X_{45}=X_{\rm vertical}/\cos 45^\circ=\sqrt{2}\,X_{\rm vertical},
\qquad
T_{45}=\exp[-(\mu/\rho)X_{45}].
\]

At the day-15 anchor, the retained atmosphere authority gives
`X_vertical = 3.461468972 g cm^-2`, `mu_eff = 0.087361754 cm^2 g^-1`, and
`T_vertical = 0.739042389`.  The corrected fixed-axis transmission is
`T_45 = 0.652034254`.  The effective coefficient is inherited from the retained
vertical closure and is consistent with the NIST XCOM dry-air attenuation
coefficient near 511 keV.

Only the celestial focused-signal rate and its transport-counting lower endpoint
are rescaled.  Prompt, delayed, atmospheric-line background, occupancy, live
factor, and all transported samples remain unchanged.  The reference source
flux is defined at the top of the atmosphere.

Run:

```bash
python3 engineering/ea_peer_review_p02_slant_transmission_20260714/code/build_slant45_signal_refold.py
```

The builder emits an 81-bin corrected timeline, a machine-readable summary, and
a validation record under `outputs/` and `data/`.
