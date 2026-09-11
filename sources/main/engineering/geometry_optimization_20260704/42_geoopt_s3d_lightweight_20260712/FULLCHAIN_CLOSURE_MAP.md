# S3d-O9 full-chain closure map

Status: `PASS_S3D_O9_FULLCHAIN_PATH_CONTRACT`

This is a path/gate contract. A listed output can still be pending; the contract never promotes a prepared source or manifest into measured transport evidence.

| order | stage | role | gate |
| ---: | --- | --- | --- |
| 1 | `geometry` | single geometry authority for every source and SIM header | all static/independent/overlap checks PASS and geometry hash frozen |
| 2 | `prompt_all8` | paper-grade prompt background; the e+/n screen is not accepted here | 68 PASS/SKIP, generated=requested, 68 SIM+DAT files, one TT/file, all source and SIM geometry headers exact |
| 3 | `atm511_sidecar` | semiempirical atmospheric 511-keV line, never relabeled as native EXPACS | SE=ID=3M, exact geometry, 50-keV analysis veto, W/Al excluded, W2/broad rates and total catalog occupancy reported |
| 4 | `neutron_delayed` | neutron-only activation inventory and exact-position delayed transport | NUBASE ground-state PASS, exact support/provenance PASS, source flux closure PASS, delayed geometry/SE/ID PASS |
| 5 | `focused_signal` | full 37,194-row f10m-A1 EventList replay through the same geometry | EventList hash/row provenance, exact source/SIM geometry, SE=ID=37,194 |
| 6 | `step05_core_and_atm_merge` | one selection implementation for prompt, delayed, signal, and atmospheric-line sidecar | 50-keV analysis veto frozen; native BGO detector threshold (80 keV) disclosed as a systematic; final background=8-family prompt+neutron delayed+atm511; signal geometry-local |
| 7 | `step06` | mission time fold | prompt, delayed activity, science transmission, and atm511 phi_4pi scales kept separate; atm angular-transfer constancy disclosed |
| 8 | `step07` | source-case rate authority | focused signal manifest supplies 37,194 rows; no Mass_model/fix5 signal substitution |
| 9 | `step08` | 20-day time-dependent counting significance | atm511 occupancy included when available; never silently set pending occupancy to zero; compare central and uncertainty-aware F3 against S3c C0 |

## Commands

- lightweight source/job preflight (safe now) (lightweight)
  - `python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/run_s3d_delayed_activation.py prepare --workers 1`
- all-eight-family prompt production (heavy)
  - `python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/run_s3d_delayed_activation.py run-full-prompt --workers 8 --allow-heavy-run`
- assemble neutron instant provenance from the all-eight-family run (lightweight)
  - `python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/run_s3d_delayed_activation.py assemble-instant`
- neutron ActivationBuildUp production (heavy)
  - `python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/run_s3d_delayed_activation.py run-buildup --workers 8 --allow-heavy-run`
- RPIP raw source, NUBASE fix, and exact-position M=50k source (heavy)
  - `python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/run_s3d_delayed_activation.py prepare-delay --workers 8 --allow-heavy-run`
- one-million-event delayed transport (heavy)
  - `python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/run_s3d_delayed_activation.py run-delay --allow-heavy-run`
- prepare/audit atmospheric source without transport (lightweight)
  - `python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/prepare_s3d_atm511_replay.py`
- atmospheric 3M production (explicit confirmation token) (heavy)
  - `python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/prepare_s3d_atm511_replay.py --execute --confirm Atm511SidecarS3dO9_3M`
- Step05-Step08 fail-closed preflight (writes PENDING while production is incomplete) (lightweight)
  - `python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/run_s3d_step05_08_closure.py preflight`
- Step05-Step08 pure-function lightweight self-test (lightweight)
  - `python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/run_s3d_step05_08_closure.py self-test`
- Step05-Step08 postprocessing after every transport gate is PASS (lightweight)
  - `python3 engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/code/run_s3d_step05_08_closure.py all --workers 8`

## Boundaries

- The 16-job e+/n screening run is never accepted as all-family Step05 prompt authority.
- The atmospheric line is a semiempirical sidecar, not a native EXPACS 511-keV prediction.
- The delayed result is neutron-only and must be described as such; it is not a full-particle activation inventory.
- Every source and SIM header must resolve to the S3d geometry above.
- No retained S3c, Mass_model, fix5, or central stepwise output is overwritten.
- Internal design labels are engineering provenance and must be replaced by descriptive configuration names in the manuscript.

## Resources

- `all8_prompt_disk`: 6.7 GB (retained Mass_model full-stat analog)
- `neutron_eplus_screen_disk`: 5.3 GB (retained S3c e+/n analog)
- `neutron_buildup_disk`: 4.0 GB (retained S3c analog)
- `delayed_1m_disk`: 0.78 GB (retained S3c analog)
- `atm511_3m_disk`: 1.1 GB (retained S3c analog)
- `focused_signal_disk`: 0.032 GB (retained geo-opt analog)
- minimum free space before launch: `20 GB`
- workers: 8 transport workers is the normal launch point; reduce if RAM pressure or concurrent Cosima work exists

## Step05-Step08 implementation status

- The dedicated run_s3d_step05_08_closure.py postprocessor is present and lightweight-tested; it remains PENDING until every production input passes its fail-closed preflight.
- Step05 explicitly merges all-eight-family prompt, neutron-only delayed, atmospheric-511, and geometry-local focused signal using the retained selection at a 50-keV analysis veto.
- Step06 keeps prompt, delayed activity, science transmission, and atmospheric phi_4pi scales separate and discloses the fixed day-15 atmospheric angular-transfer approximation.
- Step08 includes atmospheric detector-catalog occupancy in the accidental live factor and never substitutes a pending occupancy with zero.
- The runner emits a matched heavy-control screening comparison for the isolated mass-reduction question and a separate full-chain comparison to the paper reference detector; manuscript display names omit internal engineering labels.
- Direct use of the retained generic Step06-Step08 scripts with an arbitrary S3d label remains non-authoritative.
