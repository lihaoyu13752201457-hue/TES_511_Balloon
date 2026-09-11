# Gamma source-axis → TES spectrum A/B (2026-08-11)

## 结论

在每个几何、每个源版本都固定为 100,000 个 gamma primary 后，修正能轴使 TES
命中数从旧错误轴的 **1 件**提高到：

| Geometry | legacy `E/1000` | corrected keV | corrected / legacy | 480–550 keV | 510.58–511.42 keV |
|---|---:|---:|---:|---:|---:|
| Mass_model_511 | 1 / 100,000 | 101 / 100,000 | 101× | 0 → 12 | 0 → 7 |
| S3d-O8 | 1 / 100,000 | 99 / 100,000 | 99× | 0 → 9 | 0 → 8 |

表中为 420 eV FWHM、0.3 keV 像素阈值后的 measured TES 结果；本批次所有沉积都远高于阈值，
所以 raw 与 measured 的命中件数相同。旧错误轴的唯一 TES 事件分别落在约 672.39 keV
（Mass）和 133.21 keV（O8），0–2 keV 内两臂均没有 TES 事件。

## 图

- 主图：`figures/tes_gamma_axis_ab_measured.png` / `.svg`
  - 每个 `TP_L0..TP_L5` 像素先聚合同一 primary 内的全部沉积；
  - 每像素施加 420 eV FWHM Gaussian response；
  - post-noise 能量低于 0.3 keV 的像素删除；
  - 再对六层 surviving pixels 做 event sum。
- 输运 QA 图：`figures/tes_gamma_axis_ab_raw.png` / `.svg`
  - 同一 TES 像素/事件聚合，但不加 detector response。

图的纵轴保留绝对探测效率：以全部 100,000 个 primary 为分母，没有把各条曲线各自归一到 1。
两个线性 zoom 的非零 bin 给出 Garwood 95% Poisson 区间；零计数不会被连线伪造成连续谱。

## A/B 合同

- corrected arm：复用已通过 batch0001 动态验证的 instant gamma transport，Mass 与 O8 各
  `4 × 25,000 = 100,000`。
- legacy arm：本包新跑 Mass 与 O8 各 `4 × 25,000 = 100,000`，使用全新的诊断种子
  `85107922, 85115841, 85123760, 85131679`。
- 两臂保持相同的 geometry、20 个等 μ 角箱、逐箱 Flux、R=60 cm、QGSP-BIC-HP、
  LivermorePol、`StoreSimulationInfo all` 和总 gamma 模型。
- 唯一物理输入差异是 20 个 DP 谱的横轴：corrected `E_keV = 1000 × E_legacy`；PDF
  相对形状及逐角箱 Flux 不变。
- total gamma 谱已经含历史宽箱 annihilation bump，本诊断没有再叠加 mono-511。
- transport 前后均复核 Cosima、共享库、Geant4 data、递归 geometry bundle、源卡和 40 个
  gamma 谱文件的 SHA-256。

Legacy 输出状态为 `DIAGNOSTIC_ONLY__LEGACY_AXIS__NON_MERGEABLE`。它不能进入 corrected
prompt/activation/delayed ledger，也不能恢复旧源的物理权威。

## TES 与选择边界

TES 只收 SIM 中 `CC HIT TP_L0_* ... TP_L5_*` 的正 `edep_keV`；BGO、塑闪、Si substrate
和支撑结构均不计入。本图是 prompt-gamma source-to-TES transfer diagnostic，不施加 BGO/
plastic veto、Compton/FoV、1 µs coincidence 或 Step05/W2 selection。因此它不是全背景率、
Step05 或几何晋级 authority。

修正臂也只有约 100 个 TES 事件，详细谱形与 511-keV 小窗仍明显受 Poisson 涨落限制；本结果
可靠地展示数量级差异，不能据此精细拟合谱线形状。

## 可审计产物

- `data/tes_gamma_axis_ab_summary.json`：结果、TT、输入 SIM 与响应合同。
- `data/tes_gamma_axis_ab_histograms.csv`：公共 bin 的 count、per-100k、per-TT rate 与
  Garwood 95% 区间。
- `data/tes_gamma_axis_ab_detected_events.csv.gz`：所有 TES-positive event 的 raw/measured
  能量、像素数与 shard。
- `data/chart_contract.json`：问题、坐标、分面和不确定度合同。
- `data/tes_gamma_axis_ab_analysis_validation.json`：输入哈希、直方图 closure、图片可读性 QA。
- `runs/particle_source_unit_repair_20260811/gamma_tes_spectrum_ab_20260811/`
  - `legacy_axis_gamma_control_contract.json`
  - `legacy_axis_gamma_control_validation.json`
  - 两个 write-once legacy control run directories。

复现脚本：

```bash
python3 engineering/particle_source_unit_repair_20260811/gamma_tes_spectrum_ab_20260811/code/run_legacy_axis_gamma_controls.py --print-plan
python3 engineering/particle_source_unit_repair_20260811/gamma_tes_spectrum_ab_20260811/code/run_legacy_axis_gamma_controls.py
python3 engineering/particle_source_unit_repair_20260811/gamma_tes_spectrum_ab_20260811/code/build_tes_gamma_spectrum_comparison.py
```

第一条是只读 preflight。第二条为 write-once；已有输出时会拒绝覆盖，因此当前已完成目录不可直接重跑。
