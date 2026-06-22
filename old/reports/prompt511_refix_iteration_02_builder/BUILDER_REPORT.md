# Prompt-511 Refix Iteration 02 Builder Report

Date: 2026-06-21

Scope: Subagent A builder only. Built four minimally invasive passive-metal candidates under `outputs/geometry/`. No baseline files, existing variantB files, protected layers, source normalization, or expensive MC runs were changed.

## Inputs

- Clean protected baseline: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/`
- Seed copied for scaffolding only: `outputs/geometry/DEMO2_DR_v3p5_jacket_W_liner_variantB_megalib_proxy/`
- Main geometry stem preserved in all candidates: `DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- Copied `README_VARIANTB.md` files now have iteration-02 notices, and copied variantB W-specific proxy scripts are disabled with pointers to this report's proxy JSONs.

## Candidates

| ID | Candidate directory | Added volumes | Material | Radii (cm) | Signal port |
|---|---|---:|---|---:|---|
| C | `outputs/geometry/DEMO2_DR_v3p5_jacket_Ta_liner_variantC_megalib_proxy/` | 3 | Ta | 11.90-12.80 | phi 171-189 deg, z -7.2 to -3.2 cm |
| D | `outputs/geometry/DEMO2_DR_v3p5_jacket_Pb_liner_variantD_megalib_proxy/` | 3 | Pb | 11.90-12.80 | phi 171-189 deg, z -7.2 to -3.2 cm |
| E | `outputs/geometry/DEMO2_DR_v3p5_jacket_W_liner_thick1158_1286_variantE_megalib_proxy/` | 3 | W | 11.58-12.86 | phi 171-189 deg, z -7.2 to -3.2 cm |
| F | `outputs/geometry/DEMO2_DR_v3p5_jacket_Ta_liner_thick1158_1286_variantF_megalib_proxy/` | 3 | Ta | 11.58-12.86 | phi 171-189 deg, z -7.2 to -3.2 cm |

Exact added-volume topology for each candidate:

- Main arc: `PCON 189 342`, z local `-7.0` to `7.0`, position z `-6.0`, mother `InstrumentFrame`.
- Port fill below: `PCON 171 18`, z local `-2.9` to `2.9`, position z `-10.1`, mother `InstrumentFrame`.
- Port fill above: `PCON 171 18`, z local `-2.1` to `2.1`, position z `-1.1`, mother `InstrumentFrame`.

The thicker candidates leave nominal radial clearances of 0.03 cm from `Shield_60K` outer r=11.55 and 0.04 cm from `Vacuum_Jacket` inner r=12.9.

## G0/G1 Results

All four candidates passed the hard geometry-only constraint gate:

```text
python3 code/tools/check_prompt511_constraints.py <cand.geo> <cand_dir>
added volumes: 3 | baseline modified: 0 | removed: 0
RESULT: PASS (all hard constraints satisfied)
```

All four candidates were then checked with their own updated `overlap_check.source`:

```text
cosima overlap_check.source > cosima_overlap.log 2>&1
```

G1 result: all four Cosima runs exited 0 and the fresh logs contain no `Overlap is detected`, `ERROR`, `Exception`, or `Failed` messages. `PointSource` appears only in the overlap sources, which are allowed by the contract.

`SurroundingSphere` remains unchanged in every candidate setup:

```text
SurroundingSphere 60 4.49012806 0 4.49012806 60
```

## G2 Geometric Proxy

Proxy script: `outputs/reports/prompt511_refix_iteration_02_builder/prompt511_liner_proxy.py`

Proxy records: `outputs/reports/prompt511_entry_audit_20260617/current_eplus_prompt_final_records.json`

This is a selected-tag geometric screen only. It samples the finite liner thickness and counts a ray as caught if any sampled crossing leaves the signal-port window. It does not include self-annihilation add-back, neutron production, delayed activation, signal replay, or prompt MC transport. Material attenuation is only estimated for W where the guide-provided 511-keV value is available.

| ID | Proxy JSON | Caught solid | Through port | Miss/inside | Caught fraction | Attenuation note |
|---|---|---:|---:|---:|---:|---|
| C | `proxy_variantC_Ta_r1190_1280.json` | 0.052979 cps, 78/80 | 0.000679 cps, 1/80 | 0.000679 cps, 1/80 | 97.5% | Ta attenuation not claimed |
| D | `proxy_variantD_Pb_r1190_1280.json` | 0.052979 cps, 78/80 | 0.000679 cps, 1/80 | 0.000679 cps, 1/80 | 97.5% | Pb attenuation not claimed |
| E | `proxy_variantE_W_r1158_1286.json` | 0.052979 cps, 78/80 | 0.000679 cps, 1/80 | 0.000679 cps, 1/80 | 97.5% | Simple W radial absorption 96.61%, proxy residual 0.003154 cps |
| F | `proxy_variantF_Ta_r1158_1286.json` | 0.052979 cps, 78/80 | 0.000679 cps, 1/80 | 0.000679 cps, 1/80 | 97.5% | Ta attenuation not claimed |

Important caveat: variantB already showed that this selected-tag geometric proxy can overpredict prompt performance. These candidates are G0/G1/G2 screens only, not MC successes.

## Next G2.5 Recommendation

Worth G2.5 isotope-smoke next:

- Primary: E, thicker W r=11.58-12.86. It is the only candidate with a simple prompt proxy residual improvement over variantB, but it likely has the highest neutron/delayed-risk burden.
- Primary: F, thicker Ta r=11.58-12.86. It tests the same extra thickness with a material that may be a better delayed Pareto point; prompt attenuation still needs a defensible Ta estimate or MC after G2.5.

Lower priority:

- C and D pass G0/G1/G2 geometric checks, but they are same-thickness material-only variants. Since same-thickness W variantB failed prompt MC, C/D should not advance as standalone prompt-fix candidates unless a material-specific prompt argument is added. They remain useful as material/delayed comparison controls.

No prompt, delayed, neutron, signal, or `run_equiv2602_pipeline_NEW_GEO.py` MC was run.
