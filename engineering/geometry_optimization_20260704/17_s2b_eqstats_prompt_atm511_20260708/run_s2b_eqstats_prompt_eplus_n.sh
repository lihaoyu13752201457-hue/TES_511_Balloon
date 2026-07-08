#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ubuntu/TES_511_Balloon"
source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh >/tmp/s2b_eqstats_megalib_env.log
cd "$ROOT"

python3 code/tools/run_equiv2602_pipeline_NEW_GEO.py \
  --mode instant \
  --source-dir engineering/geometry_optimization_20260704/17_s2b_eqstats_prompt_atm511_20260708/source_cards \
  --outdir runs/geometry_optimization_20260704/s2b_cryo_shell_45deg_eqstats_prompt_eplus_n_20260708 \
  --gamma-events 10000000 \
  --gamma-splits 12 \
  --non-gamma-replicas 8 \
  --farfield-radius-cm 60 \
  --particles eplus,n \
  --workers 8 \
  --keep-sources \
  --allow-heavy-run \
  --force
