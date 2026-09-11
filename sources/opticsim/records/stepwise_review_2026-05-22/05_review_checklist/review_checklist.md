# 05 Review checklist

![risk matrix](review_attention_matrix.png)

## Step-by-step bug review

| step | first things to check | current pass condition |
|---|---|---|
| 01 Laue baseline | ring radii, energy band, Darwin table rows, branch fractions | `summary.json` and `per_ring_summary.json` agree with the generated figures. |
| 02 Guan process | app-level process registration, process/model split, online Darwin-Hamilton backend | mean `p_diff` delta by ring is near zero without reading the 01 probability table; branch deltas remain Monte Carlo scale. |
| 03 Channel | wall-by-wall exit logic, roughness, Si path absorption, open fraction | no calibration multiplier is used; CAM511 gap is explicitly reported. |
| 04 Detector bridge | phase-space schema, detector event IDs, hit/event crosslinks | contract summary is `ok: true`; subset-run warning is understood. |
| 04 Activation bridge | true-position inventory, source rows, neutrino handling | synthetic source and focal transport run with documented scaffold limits. |

## Anti-hallucination checks

- Do not call the Guan-style result a Guan/Reiazi source-code port.
- Do not call the Channel result the original CAM511 IDL/IMD model.
- Do not turn the 0.7615 no-fudge Channel transmissivity into the CAM511 0.80 number by adding a hidden multiplier.
- Do not quote detector or activation smoke results as final sensitivity.

## Single next confidence raiser

The highest-value next check is a production-statistics run that uses the same stepwise record format: optics phase space, detector replay, prompt inventory, delayed source, and mixed timeline, all with linked summaries and figures.
