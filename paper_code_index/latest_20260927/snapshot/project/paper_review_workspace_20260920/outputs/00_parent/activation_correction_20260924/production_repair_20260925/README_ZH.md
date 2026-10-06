# 活化生产时差索引修复与重算

本目录是2026年9月25日用户“修复吧那”授权后的独立修复包。原项目、安装程序、保留模拟文件及论文未覆盖。

首先阅读 `REPAIR_REVIEW_ZH.md`；机器入口为 `MACHINE_HANDOFF.json`。

- `runtime/production_timing_fix.patch`：针对原安装源码的最小补丁。
- `runtime/production/cosima`：只修正时间索引，保留原来的子体排队和源解析行为，供普通生产模式使用。本轮没有运行新的大气粒子生产。
- `runtime/cosima`：逐核态响应补算程序，子体积累由独立解析库存负责，不再排队重复注入。不能把它当作普通完整衰变链程序使用。
- `code/run_repaired_cosima.py`：显式选择上述模式，必须提供源卡及独立种子；通过命令行传种子。仅在直接调用时启动运行。
- `data/corrected_production_inventory.csv`：按构型、粒子族、体积、核态列出的修复生产库存及各自等效曝光。
- `data/repair_ledger.json`、`data/remove_RP.json`：母核恢复及后代移除的逐条证据，保留祖先相互作用。
- `data/restored_registry.json`、`data/restored_rates_81nodes.npy`：恢复源的位置、核态及81个任务时间节点的物理率。
- `responses/plan.json`：本轮16万次有效响应的独立归一化计划。
- `final/data/RESULTS.json`：修复后20天积分结果；两构型子目录同时包含直接率、五个时间锚点、81节点结果和选后来源。
- `data/final_validation.json`：生产台账、11条旧遗漏、几何、种子、响应增量及只读边界检查。
- `data/response_uncertainty.json`、`data/combined_zero_statistics.json`：零选中补算分层的统计上限。
- `data/W176_bounds.json`：代入修复后目录率的已知低能级分支影响界限。

所有旧“final”目录保留为历史快照；本目录的 `final/` 才是这次修复的结果入口。尚未把数值和方法改动写入论文。
