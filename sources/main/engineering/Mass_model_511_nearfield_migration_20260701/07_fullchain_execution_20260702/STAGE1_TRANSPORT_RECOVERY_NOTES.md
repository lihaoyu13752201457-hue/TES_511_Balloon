# Stage-1 Transport Recovery Notes

## 2026-07-02T13:54:51Z Attempt

Command:

```bash
script -q -f -e -c "/usr/bin/time -p bash engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/RUN_FULLSTAT_TRANSPORT_STAGE1.sh" engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/stage1_transport_20260702T135451Z.log
```

Result:

- instant stage started, buildup did not start.
- completed jobs: 68
- failed jobs: 68
- SIM outputs: 0
- DAT outputs: 0
- runner elapsed: `real 0.19`

Root cause:

```text
/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima: error while loading shared libraries: libSivan.so: cannot open shared object file: No such file or directory
```

Representative job log:

`runs/Mass_model_511_nearfield_migration_20260701/step02_instant_candidate_Mass_model_511_fullstat_v1/logs/Background_alpha_fullsphere20_rep01_part01.log`

Recovery command:

```bash
source engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration/megalib_env.sh
bash engineering/Mass_model_511_nearfield_migration_20260701/07_fullchain_execution_20260702/RUN_FULLSTAT_TRANSPORT_STAGE1.sh
```

No outputs were deleted.
