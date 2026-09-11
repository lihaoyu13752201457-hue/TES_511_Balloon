# 检查与恢复

## 获取独立备份分支

```bash
git clone --single-branch --branch codex/paper-code-backup-20260911   https://github.com/lihaoyu13752201457-hue/TES_511_Balloon.git TES_511_Paper_Backup
cd TES_511_Paper_Backup
python3 tools/verify_snapshot.py
```

该分支有独立根提交；使用 single-branch 克隆可避免下载其他分支的大型历史。

## 编译最终正文

需要 XeLaTeX 和 TeX Gyre Termes 字体。正文参考文献内嵌，无需 BibTeX。

```bash
python3 tools/verify_snapshot.py --latex
```

此命令在临时目录进行两遍编译，不覆盖保留的原始 PDF。输出与原稿的逐字节一致性不作保证，因为 TeX 版本、时间戳和字体环境可能不同。

## 重建原来源目录的代码集合

```bash
python3 tools/materialize_sources.py --list
python3 tools/materialize_sources.py --root-id main --destination /tmp/tes511-restored-main
python3 tools/materialize_sources.py --root-id worktree_ebb2 --destination /tmp/tes511-restored-ebb2
python3 tools/materialize_sources.py --root-id opticsim --destination /tmp/tes511-restored-opticsim
```

恢复工具按该来源的逐文件清单解析共享副本并核对 SHA-256，只写入**新建的空目标目录**。不会将当前主目录额外文件混入旧工作树，也不会覆盖原仓库。

归档内的程序、配置保持原字节，不直接替换 `/home/ubuntu/TES_511_Balloon` 或历史工作树的绝对路径。重新执行前，在独立工作副本中按 `manifests/source_roots.json` 映射这些路径并准备数据。P70 对 ebb2/P67 的动态导入尤其需要保留来源对应关系。

备份时未执行完整模拟或改动物理代码。哈希校验、关键代码覆盖和论文编译通过，只说明备份完整性与稿件资源可用，不表示缺失的大数据输入已经恢复。

原始采集与补充脚本也保存在 `tools/`，用于说明本次取样策略；其中路径和日期是本次机器环境的固定值。日常恢复使用 `materialize_sources.py`，无需再次执行采集脚本。
