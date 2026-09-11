#!/usr/bin/env bash
set -euo pipefail

review_root=/home/ubuntu/TES_511_Balloon
review_prompt="$review_root/engineering/particle_source_unit_repair_20260811/second_opinion_optimization_review_20260812/GPT56_SOL_ULTRA_PROMPT.md"
review_text=$(<"$review_prompt")

exec codex \
  -C "$review_root" \
  -m gpt-5.6-sol \
  -c 'model_reasoning_effort="ultra"' \
  -s read-only \
  -a never \
  --no-alt-screen \
  "$review_text"
