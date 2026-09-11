# TES 511 keV 论文与代码备份 · 2026-09-11

本目录保存 2026-08-31 最终英文稿及其代码依赖快照。论文研究球载 Laue 透镜 + TES 望远镜的 511 keV 点源灵敏度、瞬发与活化本底，以及由近场材料来源分析驱动的探测器结构优化。

- **最终正文和 PDF**：[paper/](paper/)，含正文直接使用的 16 个 PDF 配图，可独立编译。
- **代码**：[sources/](sources/)，包括主项目未提交文件、15 个历史工作树的代码差异、光学程序、独立光学校验、PARMA 粒子源驱动与系数表、实际安装的 MEGAlib 源码和记录钩子；另保留 neutron_fen 后续研究代码。
- **规模**：4,188 个实际保存的程序源文件；快照源文件、配置、文档及论文合计 16,320 个文件、261.8 MiB，另有清单和备份工具。
- **溯源**：[manifests/files.jsonl](manifests/files.jsonl) 逐文件记录原路径、保存路径、SHA-256；[source_roots.json](manifests/source_roots.json) 记录各仓库原 HEAD 和工作区状态。
- **恢复**：[RESTORE.md](RESTORE.md)；**代码导航**：[CODE_MAP.md](CODE_MAP.md)；**论文主题与版本边界**：[PAPER_TOPIC.md](PAPER_TOPIC.md)。

这是独立的根提交，备份分支为 `codex/paper-code-backup-20260911`，使用原项目远端 `https://github.com/lihaoyu13752201457-hue/TES_511_Balloon.git`。原仓库工作区、分支和历史未迁移或修改。

大型 SIM、逐事件目录、NPZ/NPY、活化展开采样列表、编译产物、软件安装环境和旧 Git 历史未复制。**这是论文与代码备份；完整物理重算还需要原始数据及相应软件环境。** 小型几何、谱表、输入配置和结果摘要按清单保留，详见 [DATA_NOT_INCLUDED.md](DATA_NOT_INCLUDED.md)。

历史脚本按原字节保存，可能含原机器绝对路径。不能将不同工作树版本混合执行，也不能把历史源单位错误或旧结果恢复成当前物理依据。恢复工具先重建各自的来源目录；路径迁移须在单独工作副本中进行。

```bash
python3 tools/verify_snapshot.py
python3 tools/verify_snapshot.py --latex
```

备份验证结果：[manifests/validation.json](manifests/validation.json)。文件 SHA-256、94 个关键代码入口、16 个配图、两遍 XeLaTeX 编译和 ebb2 来源恢复后哈希检查均通过。
