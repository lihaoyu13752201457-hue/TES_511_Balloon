#!/usr/bin/env bash
set -u

source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh

repo=/home/ubuntu/TES_511_Balloon
cosima=/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima
base=engineering/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813
run=runs/particle_source_unit_repair_20260811/bpe_neutron_boundary_20260813/production_attempt02

cd "$repo" || exit 1
for i in 01 02 03 04 05 06 07 08; do
  "$cosima" -z -v 0 "$base/source_cards/attempt02/shard${i}.source" > "$run/shard${i}/cosima.log" 2>&1 &
done
wait
