# 新终端执行提示

在 `/home/ubuntu/TES_511_Balloon` 直接工作。

先复习项目，但不要无限审计：阅读 `AGENTS.md` 指定的 corrected-keV authority；理解两条几何主线——原始 `Mass_model_511`，以及加入 BPE、正电子塑闪屏蔽和全包裹结构的 `S3d-O8`；再阅读 M05 中英文论文稿，重点掌握 source、VETO、统计、activation/delayed 和几何比较合同。把这一步限制在足以安全开工的范围内。

随后执行：

`engineering/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_20260812/README.md`

核心要求：

- 总墙钟16小时：2小时可合并 smoke、10小时七族、4小时质子。
- 前置复核最多20分钟。compact 未获独立授权就立即使用 corrected-keV rich 基线 F；不要因此停滞。
- 质子按小段轮转，边跑边调整未来 shard 大小和并发；不要中途改变物理清单、CUT、源谱或选择定义。
- 旧代码、旧 runs 和论文只读。新实现仅放在本 batch0006 工程目录；模拟数据仅放在 `runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1/`。
- 只有真正影响物理合同、数据可合并性、破坏性操作或无法继续执行的问题，才使用 `wechat` skill 的 `ask_human.py` 联系用户；问题要短，附建议选项。日常实现选择自行判断并继续。
- 遇到可恢复错误，先采用同 seed 精确重试、降低并发或发布有效 prefix，不要因过度防御一直停在 preflight。

先完成 controller、`--print-plan`、静态门和 seed/disk/RSS 检查；PASS 后直接启动。每约30分钟记录 checkpoint，最终交付 validation、ledger、实际事件数/TT/RP/磁盘/RSS和未完成 cell。不要使用旧 factor-1000 数据补统计。
