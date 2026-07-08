#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ubuntu/TES_511_Balloon"
WORK="$ROOT/engineering/geometry_optimization_20260704/17_s2b_eqstats_prompt_atm511_20260708"
RUN_DIR="$ROOT/runs/geometry_optimization_20260704/s2b_cryo_shell_45deg_atm511_sidecar_3m_20260708"
RUN_NAME="Atm511SidecarS2bCryoShell3M"

source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh >/tmp/s2b_atm511_megalib_env.log
cd "$ROOT"

python3 "$WORK/build_s2b_atm511_sidecar.py"
mkdir -p "$RUN_DIR"
cosima -s 26070817 "$RUN_DIR/$RUN_NAME.source" > "$RUN_DIR/cosima_$RUN_NAME.log" 2>&1
python3 "$WORK/build_s2b_atm511_sidecar.py"
