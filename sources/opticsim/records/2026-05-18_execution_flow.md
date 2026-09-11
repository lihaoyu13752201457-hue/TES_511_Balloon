# 2026-05-18 实现与运行流程记录

这份记录说明本轮最后实际实现了哪些代码、按什么顺序运行了哪些命令、哪些步骤是并发检查。它不是物理结论汇总，而是方便复查的执行流程账本。

## 1. 总体流程图

```text
读取现有项目状态
  -> 新增 bounce/path 诊断脚本
  -> 运行诊断脚本生成结果
  -> 把诊断接入审计、PDF、review packet、文档
  -> 语法检查和局部运行
  -> 跑完整项目审计
      -> 发现 /tmp/opticsim-build 缺失
      -> 重新 CMake 配置和构建 Geant4 targets
      -> 重跑完整项目审计 PASS
  -> 重建汇总 PDF 和 GPT Pro review packet
  -> 渲染检查 PDF 页面
  -> 生成 records 中文记录和 PDF
```

## 2. 读取项目状态

执行方式：并发读取。

目的：先确认当前主线、已有报告、审计状态、baseline 指标和现有脚本结构。

代表性读取命令：

```bash
sed -n '1,260p' README.md
sed -n '1,620p' memory.md
sed -n '1,260p' reports/project_audit/audit_report.md
sed -n '1,260p' reports/baseline/baseline_report.md
sed -n '1,260p' docs/validation_matrix.md
sed -n '1,260p' analysis/estimate_channel_geometry_constraints.py
sed -n '1,320p' reports/build_progress_pdf.py
sed -n '1,260p' analysis/run_project_audit.py
sed -n '1,260p' analysis/build_gpt_pro_review_packet.py
```

判断结果：

```text
当前 blocker 不是 detector，而是 channel path / bounce model。
已有证据包括：
- simple 12 m curved interpretation W/Si survival 为 0
- gap scan 不能救回 survival
- 6-13 bounce analytic constraint
- Shirazi/Bloser lineage 17-38 reflections 文献线索
```

## 3. 新增核心诊断脚本

执行方式：顺序实现。

新增文件：

```text
analysis/reconcile_channel_bounce_path.py
```

实现内容：

1. 读取 `config/cam511_channel_baseline.yaml`。
2. 读取 `runs/channel_4ring_calibrated_v2/ring_theta_calibration.json`。
3. 对每个 ring 计算：
   - configured bend angle；
   - calibrated theta；
   - 当前 effective bounces；
   - 如果用 `2 * N * theta` 承接总偏转，需要多少 bounces；
   - 如果只用 `17-38` reflections 作为 many-bounce bracket，反推 theta 区间；
   - 对应的简化 half-gap 量级。
4. 输出 CSV、Markdown、PNG 和 summary JSON。

输出目录：

```text
runs/channel_bounce_path_reconciliation/
```

## 4. 首次运行新诊断脚本

执行方式：顺序运行。

命令：

```bash
python3 analysis/reconcile_channel_bounce_path.py \
  --out runs/channel_bounce_path_reconciliation
```

生成文件：

```text
runs/channel_bounce_path_reconciliation/summary.json
runs/channel_bounce_path_reconciliation/channel_bounce_path_reconciliation.csv
runs/channel_bounce_path_reconciliation/channel_bounce_path_reconciliation.md
runs/channel_bounce_path_reconciliation/channel_bounce_path_reconciliation.png
```

关键输出：

```text
effective_model_bounce_range: 1-3
required_bounce_range_at_calibrated_theta: 6.3805-12.8741
literature_reflection_range: 17-38
theta_range_if_literature_reflections_rad: 2.526e-5 to 1.129e-4
half_gap_range_if_literature_reflections_um: 0.00698 to 0.15279
```

## 5. 把新诊断接入项目链路

执行方式：顺序修改文件。

修改文件：

```text
analysis/run_project_audit.py
reports/build_progress_pdf.py
analysis/build_gpt_pro_review_packet.py
analysis/freeze_baseline.py
README.md
docs/validation_matrix.md
docs/physics_assumptions.md
docs/literature_notes.md
```

每个文件的作用：

```text
analysis/run_project_audit.py
  新增 audit check: channel_bounce_path_reconciliation

reports/build_progress_pdf.py
  新增 PDF 页面: Channel Bounce/Path Reconciliation
  最终审计页改为显示 23 checks

analysis/build_gpt_pro_review_packet.py
  把新 summary、新脚本、新 records 纳入 review packet 和 hash manifest

analysis/freeze_baseline.py
  把新脚本加入 baseline hash 保护

README.md
  增加运行命令和当前 scope 说明

docs/validation_matrix.md
  增加一行验证矩阵

docs/physics_assumptions.md
  增加物理假设和边界说明

docs/literature_notes.md
  记录 17-38 reflections 只作为 lineage clue
```

## 6. 语法检查和局部复核

执行方式：并发运行。

同一轮并发执行了三类检查：

```bash
python3 -m py_compile \
  analysis/reconcile_channel_bounce_path.py \
  analysis/run_project_audit.py \
  analysis/build_gpt_pro_review_packet.py \
  reports/build_progress_pdf.py \
  analysis/freeze_baseline.py
```

```bash
python3 analysis/reconcile_channel_bounce_path.py \
  --out runs/channel_bounce_path_reconciliation
```

```bash
sed -n '1,80p' \
  runs/channel_bounce_path_reconciliation/channel_bounce_path_reconciliation.md
```

结果：

```text
Python 语法检查通过。
新诊断脚本可重复运行。
Markdown 摘要输出可读。
```

## 7. 第一次完整项目审计

执行方式：顺序运行。

命令：

```bash
python3 analysis/run_project_audit.py --out reports/project_audit
```

结果：

```text
FAIL
n_commands: 23
```

失败原因：

```text
/tmp/opticsim-build is not a directory
```

这说明 Geant4 的临时 CMake build 目录不存在。失败不是新代码逻辑导致的，而是 `/tmp` 下构建目录被清理了。

## 8. 定位审计失败原因

执行方式：并发读取。

命令：

```bash
python3 - <<'PY'
import json
from pathlib import Path
p=Path('reports/project_audit/audit_summary.json')
data=json.loads(p.read_text())
for row in data['commands']:
    if not row['ok']:
        print(row['name'], row['returncode'], row['must_contain'])
        print(row['stdout_tail'])
PY
```

```bash
sed -n '1,120p' reports/project_audit/audit_report.md
```

确认结果：

```text
cmake_build 失败。
所有依赖 /tmp/opticsim-build 下 Geant4 executable 的 smoke test 失败。
Python-only checks 和新 bounce/path reconciliation check 已经通过。
```

## 9. 查找本地 Geant4 配置

执行方式：并发查找。

命令：

```bash
which geant4-config || true
find /home/ubuntu/MEGAlib_Install -path '*geant4-config' -type f 2>/dev/null | head -20
find /home/ubuntu/MEGAlib_Install -path '*Geant4Config.cmake' -type f 2>/dev/null | head -20
```

找到的关键路径：

```text
/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/bin/geant4-config
/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/lib/Geant4-10.2.3/Geant4Config.cmake
```

## 10. 重新配置和构建 Geant4 targets

执行方式：顺序运行。

配置命令：

```bash
cmake -S . -B /tmp/opticsim-build \
  -DGeant4_DIR=/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/lib/Geant4-10.2.3
```

构建命令：

```bash
cmake --build /tmp/opticsim-build
```

构建出的 targets：

```text
gamma_optics_geant4
channel_two_wall_demo
channel_two_wall_table_demo
channel_single_curved_demo
detector_only_demo
laue_one_ring_demo
channel_4ring_effective_demo
```

## 11. 第二次完整项目审计

执行方式：顺序运行。

命令：

```bash
python3 analysis/run_project_audit.py --out reports/project_audit
```

结果：

```text
PASS
duration_s: 69.321
n_commands: 23
```

新增审计项也通过：

```text
channel_bounce_path_reconciliation: PASS
```

## 12. 重建汇总 PDF 和 review packet

执行方式：先并发，后补一次顺序刷新。

并发运行：

```bash
python3 reports/build_progress_pdf.py
```

```bash
python3 analysis/build_gpt_pro_review_packet.py
```

因为 review packet 需要包含最终 PDF 的 hash，所以 PDF 生成结束后又顺序运行了一次：

```bash
python3 analysis/build_gpt_pro_review_packet.py
```

产出：

```text
reports/opticsim_progress_report.pdf
reports/gpt_pro_review_packet.md
reports/gpt_pro_review_manifest.json
```

PDF 状态：

```text
Pages: 19
CreationDate: Mon May 18 15:10:20 2026 CST
File size: 1779777 bytes
```

## 13. 渲染检查汇总 PDF

执行方式：顺序检查关键页面。

命令：

```bash
pdftoppm -f 10 -l 10 -png -r 140 \
  reports/opticsim_progress_report.pdf /tmp/opticsim_bounce_page
```

```bash
pdftoppm -f 19 -l 19 -png -r 140 \
  reports/opticsim_progress_report.pdf /tmp/opticsim_audit_page
```

检查内容：

```text
page 10: 新增 Channel Bounce/Path Reconciliation 页面正常渲染。
page 19: GPT Pro 审核页正常渲染，显示 23 checks PASS。
```

## 14. 新建 records 记录

执行方式：顺序实现。

先生成英文/中英混合记录，随后按用户要求改成中文：

```text
records/2026-05-18_bounce_path_reconciliation.md
```

然后新增 PDF 生成脚本：

```text
records/build_bounce_path_record_pdf.py
```

运行：

```bash
python3 records/build_bounce_path_record_pdf.py
```

产出：

```text
records/2026-05-18_bounce_path_reconciliation.pdf
```

验证：

```bash
pdfinfo records/2026-05-18_bounce_path_reconciliation.pdf
```

结果：

```text
Pages: 7
CreationDate: Mon May 18 18:12:17 2026 CST
File size: 320988 bytes
```

## 15. 渲染检查 records PDF

执行方式：并发渲染，再人工查看图片。

命令：

```bash
pdftoppm -f 1 -l 1 -png -r 140 \
  records/2026-05-18_bounce_path_reconciliation.pdf /tmp/bounce_record_page1
```

```bash
pdftoppm -f 7 -l 7 -png -r 140 \
  records/2026-05-18_bounce_path_reconciliation.pdf /tmp/bounce_record_page7
```

检查结果：

```text
第一页中文正文渲染正常。
第七页附图渲染正常。
```

## 16. 本轮最终产物

新增核心代码：

```text
analysis/reconcile_channel_bounce_path.py
```

新增诊断输出：

```text
runs/channel_bounce_path_reconciliation/summary.json
runs/channel_bounce_path_reconciliation/channel_bounce_path_reconciliation.csv
runs/channel_bounce_path_reconciliation/channel_bounce_path_reconciliation.md
runs/channel_bounce_path_reconciliation/channel_bounce_path_reconciliation.png
```

更新后的项目报告：

```text
reports/opticsim_progress_report.pdf
reports/project_audit/audit_report.md
reports/gpt_pro_review_packet.md
reports/gpt_pro_review_manifest.json
```

records 下给用户查验的文件：

```text
records/2026-05-18_bounce_path_reconciliation.md
records/2026-05-18_bounce_path_reconciliation.pdf
records/build_bounce_path_record_pdf.py
records/2026-05-18_execution_flow.md
```

## 17. 一句话复盘

这轮工作的真实执行顺序是：先读现状，再写新诊断脚本，运行脚本拿到数据，然后把它接入审计和 PDF；第一次审计因为 `/tmp/opticsim-build` 丢失失败，于是重建 Geant4 build，再重跑审计通过；最后重建总 PDF、review packet，并生成 records 目录下的中文查验记录和 PDF。
