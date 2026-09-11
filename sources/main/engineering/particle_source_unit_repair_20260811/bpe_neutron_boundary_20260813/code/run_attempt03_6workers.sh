#!/usr/bin/env bash
set -u

source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh

repo=/home/ubuntu/TES_511_Balloon
cosima=/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima
base=engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813
run=runs/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/production_attempt03

cd "$repo" || exit 1

run_shard() {
  i="$1"
  "$cosima" -z -v 0 "$base/source_cards/attempt03/shard${i}.source" > "$run/shard${i}/cosima.log" 2>&1
  code="$?"
  printf '%s %s\n' "$i" "$code" > "$run/shard${i}/exit_status.txt"
  return "$code"
}

export -f run_shard
export cosima base run
printf '%s\n' 01 02 03 04 05 06 07 08 | xargs -n 1 -P 6 bash -c 'run_shard "$1"' _

