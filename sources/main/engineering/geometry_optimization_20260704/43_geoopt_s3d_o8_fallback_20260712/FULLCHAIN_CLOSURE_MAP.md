# O8 full-chain closure map

Status: `PASS_O8_FULLCHAIN_PATH_CONTRACT_READY_TO_LAUNCH`

Screening promotion: `PASS_SCREENING_PROMOTION_GATE`

This is a path and gate contract. Prepared source/job cards are not transport evidence, and PENDING is never converted to zero.

| order | stage | role | gate |
| ---: | --- | --- | --- |
| 0 | `screening_promotion` | mandatory matched heavy-control/O8 promotion gate before any full-chain production | status=PASS_O8_SCREENING_PROMOTION_GATES; dominant_subset and signal evaluation_status=PASS and promotion_gate_pass=true; all required gates evaluated; no pending inputs or audit failures |
| 1 | `geometry` | single O8 geometry authority for every generated source and SIM header | static diff, independent validation, overlap/load, and frozen hashes all PASS |
| 2 | `prompt_all8` | paper-grade prompt background; the 16-job e+/n screening run is not accepted | 68 PASS/SKIP; generated=requested; one positive TT/file; every source and SIM geometry exact |
| 3 | `neutron_buildup` | eight-replica neutron ActivationBuildUp authority | 8 PASS/SKIP, generated=requested, ActivationBuildUp source and SIM geometry exact |
| 4 | `nubase_exact_position_source` | neutron-only corrected inventory and exact-position delayed source | NUBASE ground-state correction PASS, family TT guard exactly 8/8, source/inventory and exact-position provenance PASS |
| 5 | `delayed_transport` | one-million-event O8 neutron-only delayed transport | source and SIM geometry exact, source-flux closure PASS, SE=ID=1M |
| 6 | `matched_sidecar_and_signal` | screening-produced atmospheric-line and focused-signal authorities consumed read-only | atm511 SE=ID=3M and signal SE=ID=37,194; exact O8 geometry; frozen 50-keV analysis policy |
| 7 | `step05` | merge all-eight prompt, neutron delayed, atmospheric-511, and geometry-local signal | per-family 1/sum(TT), 50-keV analysis veto, native 80-keV threshold disclosed, no pending stream substituted by zero |
| 8 | `step06_step07_step08` | separate mission scalings, source-case authority, and 20-day counting projection | prompt/delayed/science/atmospheric scales remain separate; atmospheric occupancy included; central and conservative-95 results reported |

## Commands

- safe source/job preparation only (no Cosima)
  - `python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/run_o8_delayed_activation.py prepare --workers 1`
- all-eight prompt transport after final screening PASS (Cosima production)
  - `python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/run_o8_delayed_activation.py run-full-prompt --workers 8 --allow-heavy-run --confirm RUN_O8_FULL_PROMPT_ALL8`
- assemble neutron instant provenance from completed all-eight prompt (no Cosima)
  - `python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/run_o8_delayed_activation.py assemble-instant`
- neutron buildup transport after final screening PASS (Cosima production)
  - `python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/run_o8_delayed_activation.py run-buildup --workers 8 --allow-heavy-run --confirm RUN_O8_NEUTRON_BUILDUP`
- NUBASE correction and exact-position M=50,000 source build (no Cosima)
  - `python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/run_o8_delayed_activation.py prepare-delay --workers 8 --allow-heavy-run --confirm BUILD_O8_DELAYED_SOURCE_M50000`
- one-million-event delayed transport after final screening PASS (Cosima production)
  - `python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/run_o8_delayed_activation.py run-delay --allow-heavy-run --confirm RUN_O8_DELAYED_TRANSPORT_1M`
- fail-closed Step05-Step08 preflight (no Cosima)
  - `python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/run_o8_step05_08_closure.py preflight`
- pure-function and path-binding self-test (no Cosima)
  - `python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/run_o8_step05_08_closure.py self-test`
- dedicated postprocessing only after every gate PASS (no Cosima)
  - `python3 engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/code/run_o8_step05_08_closure.py all --workers 8 --allow-closure-run --confirm RUN_O8_STEP05_08_CLOSURE`

## Hard boundaries

- No full-chain production is authorized until the final O8 screening JSON and every required promotion gate are PASS.
- The completed O9 campaign is implementation context only and cannot satisfy the O8 screening gate.
- The 16-job e+/n screen is never accepted as all-eight prompt authority.
- Delayed activation is neutron-only, uses NUBASE ground-state correction and the eight-file TT division guard, and is not a full-particle inventory.
- Exact-position sampling is M=50,000 with source/inventory/RPIP provenance; visually plausible sources are not accepted.
- Every source and SIM header must resolve to the package-43 O8 geometry.
- No package-42, screening-run, retained mainline, or central stepwise product is overwritten.

## Resource floor

- Minimum free space before launch: `20 GB`.
- 8 transport workers after checking concurrent Cosima/RAM pressure.
