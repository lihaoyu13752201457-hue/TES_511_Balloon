# 数据表语义索引

| 文件 | 粒度 | 权威含义 | 重要限制 |
|---|---|---|---|
| `geometry_volume_manifest.csv` | 3096 WRL SOLID | exact geometry name/material、Copy/母体、CSG、bbox、mesh count | WRL/world 单位 mm；Instrument bbox 单位 cm |
| `delayed_selected_event_ledger.csv` | 420 selected event | 每条 TES-selected delayed W2 事件、权重与 decay-source 点 | inventory-cell total 不能在事件行重复求和 |
| `delayed_source_point_ledger.csv` | 66 source point | 绘图点、核素、volume/material、world/IF 坐标、聚合 W2 rate | marker size 不是物理尺寸 |
| `delayed_partial_production_origin_links.csv` | 25 exact link | actual interacting projectile 与 creator process | 仅 25/420；其余必须保持 UNKNOWN |
| `prompt_events.csv` | 3 prompt event | raw/replayed energy、veto/Step05/frozen、host、TES centroid | 复合键是 `source_file + local_event_id` |
| `prompt_ia_nodes.csv` | 86 IA node | INIT/PAIR/ANNI 等 interaction DAG 和 world/IF 坐标 | IA chord 不包含边界穿越 |
| `prompt_cc_hits.csv` | 285 CC hit | Geant4 deposit sample、volume、track/parent/process | deposit sample 不是完整 step |
| `prompt_htsim_hits.csv` | 16 detector hit | detector hit 与 contributing IA IDs | 只有 type-2 TES 坐标是 fixed world pixel center |
| `prompt_ancestry_edges.csv` | 547 edge | IA origin、track parent、HTsim contributor 关系 | 三种图关系不可互相替代 |
| `prompt_track_vertices.csv` | 375 vertex | 供图使用的 IA、CC、HTsim 顶点正规化表 | `coordinate_semantics` 必须随行读取 |
| `prompt_track_segments.csv` | 262 segment | IA chord 与 CC deposit polyline | `is_complete_geant4_step_path=False` |
| `agent_background_source_summary.csv` | 101 ranked group | combined stream、delayed family/material/volume/isotope 与 prompt host 的 W2 汇总 | `fraction_of_selection` 是 detector-selected W2 份额，不是质量、活度或生产率份额 |
| `agent_verified_origin_links_summary.csv` | exact linked subset | 25/420 delayed 行中可验证的 direct production projectile/process 汇总 | 未覆盖 395 行不得由 `incident_family` 推断 |
| `agent_signal_edge_cut.csv` | 30 radial cut | official post-Be stage04 signal 的 fixed-centroid、all-pixels-inside、pixel-mask 与 L3 retention | 不含 BPE/plastic full-envelope transmission |
| `agent_background_edge_cut.csv` | 214 cut state | prompt Step05 + delayed W2 的 rate、20-day counts、Neff、(f_B) 与量子 proxy | prompt baseline 只有 2 roots；低半径为离散台阶 |
| `agent_background_edge_cut_events.csv` | 422 selected event | 每条背景事件的 fixed/deposit radius、max hit-pixel radius、layer 与 W2 weight | 用于重放切选，不是新 transport |
| `edge_pixel_fiducial_scan.csv` | 30 joined policy-radius | 同半径 signal (f_S)、background (f_B)、S20、B20、central/zero-prompt-credit F3 | `all_pixels_inside` 背景只重算 W2，未完整重跑 Step05 |
| `delayed_top5_chain_summary.csv` | 5 source volume | top-five W2、Neff、核素/family、compact ANNI/PAIR 与 exact-origin 加权覆盖 | ANNI event flag 不是完整 TES boundary crossing |
| `delayed_top5_isotope_family_matrix.csv` | 29 isotope×family group | top-five 的 parent isotope 与 activation incident-family W2 分解 | incident family 不一定是直接制核粒子 |
| `delayed_top5_exact_production_mechanisms.csv` | 18 linked mechanism | transport primary → actual interacting particle/process → residual isotope | 仅 exact-coordinate linked selected events；局部 interacting-particle 能量未保存 |
| `agent_delayed_top5_tes_chain_events.csv` | 205 selected event | raw IA/HTsim contributor 的 DECA→e+→ANNI→TES ancestry 与 CC deposit 粒子 | CC 是 deposit samples，不是完整 boundary steps |
| `agent_delayed_top5_tes_chain_summary.csv` | 67 weighted category | 每个 top-five volume 的 DECA signature、first saved TES mother、deposit particle 与 incident-family W2 | W2-selected chain 不是母核素全 branching ratio |
| `top5_delayed_volume_audit.csv` | 5 source volume | full-volume Bq、W2-linked-cell Bq、selected W2、Neff、exact-origin 行/率覆盖与 coupling proxy | full Bq 与 linked-cell Bq 分母不可混用 |
| `top5_delayed_exact_origin_links.csv` | 22 exact link | top-five 的 activation job/event、primary energy、direct particle/process | primary energy 不是局部 reaction energy |

坐标列后缀：

- `world_*_cm`：SIM world frame，厘米；二维飞行图把 `+Z` 画成 sky/up。
- `IF_*_cm`：InstrumentFrame，厘米；`x′=(X-Z)/sqrt(2)`, `z′=(X+Z)/sqrt(2)`。
- 原生/final WRL：Geant4 world frame，毫米；事件坐标写 WRL 时显式乘 10。
