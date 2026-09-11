# Source provenance for recovery

## Primary session

| Field | Value |
|---|---|
| Path | `/home/ubuntu/.claude/projects/-home-ubuntu-TES-511-Balloon/9e439f14-1dc4-40e6-b2a6-e1326e236cf6.jsonl` |
| Model | `claude-fable-5` / Fable 5 |
| Project cwd | `/home/ubuntu/TES_511_Balloon` |
| Approx date | 2026-07-02 (HTML report) + continuation for revan/PPT polish |
| User task quote | “证明解析曲线是否能真实预测轨迹性能曲线…四个不同的点…后来修正正确了” + HTML PPT of three workstreams |

## Secondary evidence

- EA recovery git-status snapshots under  
  `core_md/balloon511_ea_latex_drafts/_recovery_logs/file_lists/`  
  listing `?? engineering/trajectory_transport_validation_20260626/` and  
  `?? engineering/ENGINEERING_20260627_CURVE_CHECK/`
- Codex rescue task progress (2026-07-04) reading  
  `engineering/ENGINEERING_20260627_CURVE_CHECK/outputs/…`  
  session id mentioned in chat: `019f28de-6877-7392-9010-bb42ce05cdb9`
- Still-present formula smokes (different, weaker claim):  
  `old/docs/manuscript_legacy/time_axis_smoke_audit_20260617.*`  
  `old/docs/manuscript_legacy/delayed_distribution_invariance_smoke_20260617.*`
- Unrelated early zip (not full4):  
  `/home/ubuntu/codex_tes_511_sim/time_variable_balloon_background_curves_verified.zip`

## Recovery method

1. Keyword scan of Fable5 jsonl for package names, FULL4 decision, residuals.  
2. Save tool_result fragments (FINAL_STATUS, HANDOFF, HTML, decision JSON prefix).  
3. Reconstruct structured tables/JSON from those fragments.  
4. Rebuild partial HTML body for slides that were dumped as line-numbered file content.

## Integrity statement

- Numbers in `RECONSTRUCTED_*` files are **as reported in chat**, not re-derived from raw sims.  
- Prefer original files if/when restored from backup.  
- This package must not be cited as primary experimental authority for a journal claim without re-running or restoring the transport tree.
