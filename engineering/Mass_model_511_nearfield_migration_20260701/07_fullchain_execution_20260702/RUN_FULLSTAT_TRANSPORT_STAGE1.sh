#!/usr/bin/env bash
set -euo pipefail

# Stage 1 only: full-stat Mass_model_511 candidate prompt and buildup transport.
# This script intentionally stops before delayed source construction and Step05.
# Continue only after checking disk/runtime and confirming no other agent owns these run dirs.
MEGALIB_ENV='/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh'
if [[ ! -f "$MEGALIB_ENV" ]]; then
  echo "missing MEGAlib environment: $MEGALIB_ENV" >&2
  exit 127
fi
source "$MEGALIB_ENV"

python3 code/tools/run_equiv2602_pipeline_NEW_GEO.py --mode instant --source-dir engineering/Mass_model_511_nearfield_migration_20260701/03_source_migration/source_dirs/Mass_model_511 --outdir runs/Mass_model_511_nearfield_migration_20260701/step02_instant_candidate_Mass_model_511_fullstat_v1 --gamma-events 10000000 --gamma-splits 12 --non-gamma-replicas 8 --farfield-radius-cm 60 --workers 8 --keep-sources --allow-heavy-run
python3 code/tools/run_equiv2602_pipeline_NEW_GEO.py --mode buildup --source-dir engineering/Mass_model_511_nearfield_migration_20260701/03_source_migration/source_dirs/Mass_model_511 --outdir runs/Mass_model_511_nearfield_migration_20260701/step02_buildup_candidate_Mass_model_511_fullstat_v1 --gamma-events 10000000 --gamma-splits 12 --non-gamma-replicas 8 --farfield-radius-cm 60 --workers 8 --keep-sources --allow-heavy-run

python3 engineering/Mass_model_511_nearfield_migration_20260701/build_fullchain_execution_manifest.py
