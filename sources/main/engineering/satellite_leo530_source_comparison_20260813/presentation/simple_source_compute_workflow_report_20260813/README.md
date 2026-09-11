# 气球到近地轨道：简化报告

本目录保存一份 7 页、白底、以图片和短文字为主的简报，面向约 5–7 分钟口头汇报。

## 交付文件

- `TES511_balloon_to_LEO_source_compute_workflow_brief_20260813.pptx`：可编辑 PowerPoint 主文件。
- `report_preview.pdf`：同一内容的 7 页快速预览版。
- `index.html`：可用方向键翻页的交互式预览，浏览器控制台可显示每页讲稿。
- `preview_overview.png`：全部 7 页缩略图。
- `speaker_notes.md`：逐页简短讲稿。
- `pptx_validation.json`：PPTX 页数、尺寸、图像、备注、越界、外链和文案边界校验。
- `preview_validation.json`：HTML/PDF 预览的渲染校验。

## 报告逻辑

1. 38 km 气球入射源与 530 km 近赤道 LEO 代理源的组成和能带差异。
2. 单状态 prompt 与完整轨道任务链的计算负担差异。
3. 当前的短分片、自适应调度、逐片验收、分层存储与轻量派生分析。
4. 早期批处理方式与当前可恢复数据链的简要对比。

源谱页只展示入射源，明确排除活化和延迟分量，也不把它解释为探测器计数谱。530 km、0°只是一个正常科学状态代理，不是最终任务轨道。

## 关键数字的使用边界

- `976 jobs / 13,777,092 primary histories / 77.6 GB` 是当前最终分析选择中的 976 个压缩 SIM 文件及其总规模。
- `6,149,560 validated primaries / 488 validated receipts` 是其中一个已验证生产批次，不能与前一项相加。
- `62.8 MB` 是当前活跃派生输出树；原始输运文件继续保存在 `runs/` 中。
- `77.6 GB` 与 `62.8 MB` 表示输运层和派生工作层分开保存，不代表物理输运本身获得同等倍率的速度提升。
- 轨道任务的真实计算倍率尚未测定；报告建议先对代表轨道状态做 pilot。

## 图与事实来源

- 入射组件谱：`../../outputs/simple/figures/simple_00_incident_component_spectra.png`
- 关键 gamma 能带：`../../outputs/simple/figures/simple_01_gamma_source.png`
- 源比较验证：`../../data/simple_figures_validation.json`
- 当前重分析流程：`../../../particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/README.md`
- 分片生产与验证合同：`../../../particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_20260812/README.md`
- 生产终态：`../../../../runs/particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1/recovery0008_current_attempt_disk_admission/final_validation.json`

## 重建与校验

从仓库根目录运行：

```bash
python3 engineering/satellite_leo530_source_comparison_20260813/presentation/simple_source_compute_workflow_report_20260813/code/build_pptx.py
python3 engineering/satellite_leo530_source_comparison_20260813/presentation/simple_source_compute_workflow_report_20260813/code/validate_pptx.py
python3 engineering/satellite_leo530_source_comparison_20260813/presentation/simple_source_compute_workflow_report_20260813/code/build_html_preview.py
python3 engineering/satellite_leo530_source_comparison_20260813/presentation/simple_source_compute_workflow_report_20260813/code/render_html_preview.py
```

当前环境已对 PPTX 做结构和内容校验，并对同源 HTML/PDF 预览做逐页渲染与目视检查。当前环境没有 PowerPoint/LibreOffice 渲染器，因此 PDF 是 companion 预览，不是由 PPTX 本体转换得到。
