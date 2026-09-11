# 未复制的数据与软件环境

按用户要求，备份保留代码和小型支持文件，排除大体积数据。没有启动输运或读取大型模拟事件内容。

- 不复制 `.sim`、ROOT、NPZ/NPY、HDF5、FITS、压缩事件归档和大型事件目录。
- 不复制 `runs/` 中逐任务核素 DAT、展开后的活化位置采样卡及其他批次中间产物；少量顶层审计摘要保留。
- 不复制编译目录、可执行文件、共享库、Python 虚拟环境、Geant4 数据库或旧 `.git` 历史。
- 不复制外接数据盘中的生产数据，也不建立指向原数据盘的 Git 子模块或软链接。
- 最终稿的 16 个配图 PDF 是论文必需资源，已保留；其他生成图片通常不保留。
- 小型几何、修正源谱、配置、CSV/JSON 汇总和文档按清单保留。大 JSON、CSV/DAT 与生成源卡受大小限制；具体排除路径和原因见 `manifests/excluded_files.jsonl`。

排除清单记录的是本次遍历发现的文件，并非所有软件安装目录或外接数据盘的完整目录。被整体跳过的 build、install、环境和隐藏目录不逐文件展开。各历史工作树可能引用同一份数据，清单的逻辑字节总和不应作为本机独立数据的占用量。

要重做完整物理模拟，需要恢复原始事件/活化输入，安装原记录要求的 MEGAlib、ROOT、Geant4 和核数据库，并按 source/inventory provenance、TT、几何头、随机种子和验证记录闭合。代码快照不替代这些输入。

安装权威与历史哈希记录保存在 `sources/main/engineering/particle_source_unit_repair_20260811/m05_complete_compact_smoke_20260812/external_sources.json`：生产 Cosima 记录为 MEGAlib 4.02.00 / Geant4 10.02.p03。光学项目另有 Geant4 11.4 的启动脚本，不应将两套环境混用。PARMA 的 `input/` 系数表（包括算法读取的 `.out` 输入文件）已显式保留。通用第三方依赖按版本重新安装；已在项目树内的定制源码、补丁和 MEGAlib 源码已随快照保存。
