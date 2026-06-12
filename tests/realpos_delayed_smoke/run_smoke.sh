#!/usr/bin/env bash
# Real-position delayed-source smoke test orchestrator.
#
#   1. build the exact-position PointSource .source
#   2. run cosima on it (small trigger budget)
#   3. verify the .sim output (events produced + emitted positions == exact input)
#
# Usage: bash tests/realpos_delayed_smoke/run_smoke.sh [N_DECAYS] [TRIGGERS]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
N_DECAYS="${1:-2000}"
TRIGGERS="${2:-2000}"
SEED=260609

MEGALIB="${MEGALIB:-/home/ubuntu/MEGAlib_Install/megalib-main}"
# shellcheck disable=SC1091
source "$MEGALIB/bin/source-megalib.sh"
COSIMA="$MEGALIB/bin/cosima"

export MPLCONFIGDIR=/tmp/matplotlib-newgeo
export PYTHONDONTWRITEBYTECODE=1

echo "==> [1/3] build exact-position PointSource source (M=$N_DECAYS)"
python3 -u "$HERE/build_realpos_smoke_source.py" build \
    --n-decays "$N_DECAYS" --triggers "$TRIGGERS" --seed "$SEED"

SRC="$HERE/outputs/realpos_delayed_smoke.source"
echo
echo "==> [2/3] cosima smoke run"
rm -f "$HERE"/outputs/realpos_delayed_smoke.inc1.id1.sim* 2>/dev/null || true
cd "$ROOT"
time "$COSIMA" -s "$SEED" "$SRC"

echo
echo "==> [3/3] verify sim output"
python3 -u "$HERE/build_realpos_smoke_source.py" verify \
    --n-decays "$N_DECAYS" --seed "$SEED"

echo
echo "==> smoke test complete"
