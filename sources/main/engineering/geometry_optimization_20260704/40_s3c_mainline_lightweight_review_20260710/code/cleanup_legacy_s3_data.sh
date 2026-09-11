#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
MODE="${1:---dry-run}"
if [[ "$MODE" != "--dry-run" && "$MODE" != "--execute" ]]; then
  echo "usage: $0 [--dry-run|--execute]" >&2
  exit 2
fi

RUN_TARGETS=(
  runs/geometry_optimization_20260704/s3a_bgo_barrel_atm511_sidecar_3m_20260709
  runs/geometry_optimization_20260704/s3a_bgo_barrel_eqstats_prompt_eplus_n_20260709
  runs/geometry_optimization_20260704/s3b_w2mm_al3mm_shell_atm511_sidecar_3m_20260709
  runs/geometry_optimization_20260704/s3b_w2mm_al3mm_shell_eqstats_prompt_eplus_n_20260709
  runs/geometry_optimization_20260704/s3_csi_barrel_atm511_sidecar_3m_20260709
  runs/geometry_optimization_20260704/s3_csi_barrel_eqstats_prompt_eplus_n_20260709
  runs/geometry_optimization_20260704/s3_csi_barrel_eqstats_prompt_other_20260709
  runs/geometry_optimization_20260704/s3_csi_barrel_eqstats_prompt_other_emup_20260709
  runs/geometry_optimization_20260704/step02_buildup_s3a_bgo_barrel_neutron_delay_m50000_20260710
  runs/geometry_optimization_20260704/step02_buildup_s3a_bgo_barrel_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_buildup_s3b_w2mm_al3mm_shell_neutron_delay_m50000_20260710
  runs/geometry_optimization_20260704/step02_buildup_s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_buildup_s3_csi_barrel_fullstat_v1_20260709
  runs/geometry_optimization_20260704/step02_decay_source_s3a_bgo_barrel_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_decay_source_s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_decay_source_s3_csi_barrel_fullstat_v1_20260709
  runs/geometry_optimization_20260704/step02_delayed_transport_s3a_bgo_barrel_neutron_delay_m50000_20260710
  runs/geometry_optimization_20260704/step02_delayed_transport_s3a_bgo_barrel_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_delayed_transport_s3b_w2mm_al3mm_shell_neutron_delay_m50000_20260710
  runs/geometry_optimization_20260704/step02_delayed_transport_s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_delayed_transport_s3_csi_barrel_fullstat_v1_20260709
  runs/geometry_optimization_20260704/step02_delay_exactpos_s3a_bgo_barrel_neutron_delay_m50000_20260710
  runs/geometry_optimization_20260704/step02_delay_exactpos_s3a_bgo_barrel_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_delay_exactpos_s3b_w2mm_al3mm_shell_neutron_delay_m50000_20260710
  runs/geometry_optimization_20260704/step02_delay_exactpos_s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_delay_exactpos_s3_csi_barrel_fullstat_v1_20260709
  runs/geometry_optimization_20260704/step02_delay_fix_s3a_bgo_barrel_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_delay_fix_s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_delay_fix_s3_csi_barrel_fullstat_v1_20260709
  runs/geometry_optimization_20260704/step02_instant_s3a_bgo_barrel_neutron_delay_m50000_20260710
  runs/geometry_optimization_20260704/step02_instant_s3a_bgo_barrel_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_instant_s3b_w2mm_al3mm_shell_neutron_delay_m50000_20260710
  runs/geometry_optimization_20260704/step02_instant_s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710
  runs/geometry_optimization_20260704/step02_instant_s3_csi_barrel_fullstat_v1_20260709
  runs/geometry_optimization_20260704/step09_focus_s3_csi_barrel_fullstat_v1_20260709
  stepwise_maintenance/step05_veto_time_axis/outputs_s3_csi_barrel_fullstat_v1_20260709_l1
)

REMOVE_ENGINEERING_DIRS=(
  engineering/geometry_optimization_20260704/33_s3a_neutron_delayed_chain_m50000_20260710
  engineering/geometry_optimization_20260704/34_s3b_neutron_delayed_chain_m50000_20260710
)

PRUNE_ENGINEERING_DIRS=(
  engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709
  engineering/geometry_optimization_20260704/22_s3_eqstats_prompt_atm511_20260709
  engineering/geometry_optimization_20260704/23_s3_delayed_chain_m50000_20260709
  engineering/geometry_optimization_20260704/24_s3_vs_mass511_step05_sensitivity_20260709
  engineering/geometry_optimization_20260704/25_s3_vs_mass511_with_atm511_20260709
  engineering/geometry_optimization_20260704/26_s3_mass511_gpt_pro_background_packet_20260709
  engineering/geometry_optimization_20260704/27_geoopt_s3a_bgo_barrel_20260709
  engineering/geometry_optimization_20260704/28_geoopt_s3b_w2mm_al3mm_shell_20260709
  engineering/geometry_optimization_20260704/30_s3a_dominant_backgrounds_20260709
  engineering/geometry_optimization_20260704/31_s3b_dominant_backgrounds_20260709
  engineering/geometry_optimization_20260704/36_s3a_neutron_delayed_chain_m50000_clean_20260710
  engineering/geometry_optimization_20260704/37_s3b_neutron_delayed_chain_m50000_clean_20260710
)

ROOT_FILES_TO_DELETE=(
  engineering/geometry_optimization_20260704/build_s3abc_full_visuals_20260709.py
  engineering/geometry_optimization_20260704/build_s3abc_geometry_variants_20260709.py
  engineering/geometry_optimization_20260704/run_s3abc_neutron_delayed_chain_20260710.py
  engineering/geometry_optimization_20260704/validate_s3abc_dominant_backgrounds_20260709.py
  engineering/geometry_optimization_20260704/validate_s3abc_neutron_delayed_20260710.py
  engineering/geometry_optimization_20260704/S3ABC_DOMINANT_BACKGROUND_RUN_PLAN_20260709.md
  engineering/geometry_optimization_20260704/S3ABC_NEUTRON_DELAYED_RUN_PLAN_20260710.md
)

declare -A KEEP
while IFS= read -r path; do
  KEEP["$path"]=1
done <<'EOF'
engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/README.md
engineering/geometry_optimization_20260704/21_geoopt_s3_csi_barrel_20260709/cosima_overlap_smoke_20260709.md
engineering/geometry_optimization_20260704/22_s3_eqstats_prompt_atm511_20260709/README.md
engineering/geometry_optimization_20260704/22_s3_eqstats_prompt_atm511_20260709/plastic20_legacy50_s3_prompt_all.md
engineering/geometry_optimization_20260704/22_s3_eqstats_prompt_atm511_20260709/plastic20_legacy50_s3_vs_s2b_summary.md
engineering/geometry_optimization_20260704/22_s3_eqstats_prompt_atm511_20260709/s3_atm511_sidecar_3m_summary.md
engineering/geometry_optimization_20260704/22_s3_eqstats_prompt_atm511_20260709/s3_eqstats_prompt_all.md
engineering/geometry_optimization_20260704/22_s3_eqstats_prompt_atm511_20260709/s3_vs_s2b_eqstats_background_comparison.md
engineering/geometry_optimization_20260704/23_s3_delayed_chain_m50000_20260709/delayed_source/delayed_source_exactpos_summary.md
engineering/geometry_optimization_20260704/23_s3_delayed_chain_m50000_20260709/s3_csi_barrel_fullstat_v1_20260709_campaign_manifest.md
engineering/geometry_optimization_20260704/24_s3_vs_mass511_step05_sensitivity_20260709/s3_vs_mass511_20d3sigma_comparison.md
engineering/geometry_optimization_20260704/25_s3_vs_mass511_with_atm511_20260709/mass511_atm511_4pi_sidecar_3m_summary.md
engineering/geometry_optimization_20260704/25_s3_vs_mass511_with_atm511_20260709/s3_vs_mass511_20d3sigma_with_atm511_sidecar.md
engineering/geometry_optimization_20260704/25_s3_vs_mass511_with_atm511_20260709/s3_vs_mass511_20d3sigma_with_matched_4pi_atm511_sidecar.md
engineering/geometry_optimization_20260704/26_s3_mass511_gpt_pro_background_packet_20260709/README_GPT_PRO.md
engineering/geometry_optimization_20260704/26_s3_mass511_gpt_pro_background_packet_20260709/geometry_key_differences_s3_vs_mass511.md
engineering/geometry_optimization_20260704/27_geoopt_s3a_bgo_barrel_20260709/README.md
engineering/geometry_optimization_20260704/28_geoopt_s3b_w2mm_al3mm_shell_20260709/README.md
engineering/geometry_optimization_20260704/30_s3a_dominant_backgrounds_20260709/dominant_background_summary.md
engineering/geometry_optimization_20260704/30_s3a_dominant_backgrounds_20260709/s3a_atm511_sidecar_3m_summary.md
engineering/geometry_optimization_20260704/31_s3b_dominant_backgrounds_20260709/README.md
engineering/geometry_optimization_20260704/31_s3b_dominant_backgrounds_20260709/dominant_background_summary.md
engineering/geometry_optimization_20260704/31_s3b_dominant_backgrounds_20260709/s3b_atm511_sidecar_3m_summary.md
engineering/geometry_optimization_20260704/36_s3a_neutron_delayed_chain_m50000_clean_20260710/delayed_source/delayed_source_exactpos_summary.md
engineering/geometry_optimization_20260704/36_s3a_neutron_delayed_chain_m50000_clean_20260710/s3a_bgo_barrel_neutron_delay_m50000_clean_20260710_campaign_manifest.md
engineering/geometry_optimization_20260704/37_s3b_neutron_delayed_chain_m50000_clean_20260710/delayed_source/delayed_source_exactpos_summary.md
engineering/geometry_optimization_20260704/37_s3b_neutron_delayed_chain_m50000_clean_20260710/s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710_campaign_manifest.md
EOF

assert_safe() {
  local target="$1"
  if [[ "$target" == *s3c* || "$target" == /* || "$target" == *".."* ]]; then
    echo "unsafe cleanup target: $target" >&2
    exit 3
  fi
}

delete_dir() {
  local target="$1"
  assert_safe "$target"
  [[ -e "$ROOT/$target" ]] || return 0
  echo "DELETE_DIR $target"
  if [[ "$MODE" == "--execute" ]]; then
    rm -rf -- "$ROOT/$target"
  fi
}

delete_file() {
  local target="$1"
  assert_safe "$target"
  [[ -e "$ROOT/$target" ]] || return 0
  echo "DELETE_FILE $target"
  if [[ "$MODE" == "--execute" ]]; then
    rm -f -- "$ROOT/$target"
  fi
}

for target in "${RUN_TARGETS[@]}" "${REMOVE_ENGINEERING_DIRS[@]}"; do
  delete_dir "$target"
done

for target in "${ROOT_FILES_TO_DELETE[@]}"; do
  delete_file "$target"
done

for directory in "${PRUNE_ENGINEERING_DIRS[@]}"; do
  [[ -d "$ROOT/$directory" ]] || continue
  while IFS= read -r -d '' file; do
    relative="${file#"$ROOT/"}"
    if [[ -z "${KEEP[$relative]+x}" ]]; then
      delete_file "$relative"
    fi
  done < <(find "$ROOT/$directory" -type f -print0)
  if [[ "$MODE" == "--execute" ]]; then
    find "$ROOT/$directory" -depth -type d -empty -delete
  fi
done

echo "CLEANUP_MODE $MODE"
echo "S3C_TARGETS 0"
