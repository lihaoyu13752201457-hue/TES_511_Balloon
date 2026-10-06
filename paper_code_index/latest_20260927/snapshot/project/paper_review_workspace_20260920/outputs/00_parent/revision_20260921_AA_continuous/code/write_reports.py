from common import *
import re
s=(O/'paper_clean.tex').read_text();R=read(O/'data/RESULTS.json');V=read(O/'data/paper_values_500.json');A=V['a'];delay=A['compton_trajectory_veto']['delayed']['rate'];issues=[]
def issue(title,anchor,body,evidence):
 assert anchor in s,anchor
 line=s[:s.index(anchor)].count('\n')+1
 issues.append({'id':f'W{len(issues)+1:02d}','title':title,'line':line,'anchor':anchor,'finding':body,'evidence':evidence,'manuscript_wording_modified':False})
issue('条件探针文字与本轮实际三路泊松计算不一致','Accidental loss of a weak focused signal is estimated with conditional',
'正文仍写 conditional probes，以及不将信号记录与本底沉积合并；本轮实际对 signal、prompt、delayed 三路按物理率生成泊松到达，先按时间分组，再按像素合并能量并施加响应。该旧文字在 §3.3 开头、§3.3.1 末段、式 anchor_time_factors 的 N^{probe}、该式后的 conditional survival 定义、积分误差段的 signal probes、§4.5 的 focused-signal probes 均有残留。这些地方需以后统一删除/调整；本轮依照“唯一表述修改为删 24 点”的限制保留。', 'code/timeline_deferred.cpp; code/analyze.py; data/ANCHORS.csv')
issue('AA 顶部 BGO 已是留管孔的盖板，不是大孔圆环','a 30 mm bottom cap, and a 10 mm top annulus.',
'AA 顶部 BGO 厚度仍为 10 mm、外径仍为 504 mm，但中央大开口已补齐，仅保留 12 个管孔。正文 top annulus、内/外径 418/504 mm，以及主动屏蔽段的 top annulus 都对应旧模型。不能仅把 418 换一个数字来修正结构意义，因此保留原文并列出。', 'AA geometry README; Mass_model_AA.geo: AA_BGO_TopCap_12Ports_10mm / AA_TopPipeCut_12Subtraction')
issue('入口与 W 准直器文字、Figure 2 已不对应 AA','windows, a beryllium vacuum window, and a tungsten multihole collimator aligned',
'AA 是 54 mm 圆形 Al 壳体开孔、4 层 25 μm Al 薄窗及 1 层 150 μm Be 窗；W 是外 60×60 mm、净孔 54×54 mm、深 20 mm 的单孔边框。旧正文 multihole collimator aligned with TES pixels、Figure 2 的矩形薄窗和 grid 说明应复核。Figure 2 原图保持不变，未借本轮数据替换重画。', 'AA geometry README 的“与 B 统一的光学入口”; figures/fig02.pdf')
issue('Figure 2 的 BPE 及部分结构图仍是旧几何','thermal shields, BGO, and borated polyethylene (BPE).',
'AA 已物理移除 BPE、塑料、重复的中间 100 mK 盘、下方 W 挡板和 NF2 外框架，并补齐顶盖。Figure 2 图注仍明说 BPE；Figure 2、Figure 8 及 Figure 9 的浅色结构底图需要与新几何逐件比对。本轮 Figure 9 只重填 AA 来源坐标及核素，浅色背景保持原图。', 'AA geometry README 最终修改表; figures/fig02.pdf, fig08.pdf, fig09.pdf')
issue('“每个粒子族都输运一百万延迟衰变”存在 AA 例外','For each incident-particle family, each mass model\ntransports',
'AA 的 μ+ 延迟源活度为零，实际跳过；AA 延迟总量为 7,000,000，而非每个族各一百万。Table 3 的 AA μ+ 已回填为 0 / — / 0 / 0，方法段概括语暂未改。八族 prompt 仍全部存在，不应删减 prompt 族数。', 'data/aa_transport_table.json; AA_run_20260921_v1/data/baseline_transport_complete.json')
issue('“MXC 冷盘贡献最大”已被新来源排序否定','identifies the MXC copper cold plate as the largest source',
'AA 延迟本底中 TES 铜支撑板合计 41.03%，铜散热环 17.69%，MXC 铜冷盘 15.73%。旧 largest source 不能继续使用；摘要和总结中列举这些结构的顺序也应按新结论复核。本轮只回填百分比，没有改排序判断。', 'data/paper_values_500.json: a.origin_components; Figure 7')
issue('来源体积/核素对的排序仍沿用旧 A','The three leading source-volume/nuclide pairs are',
'AA 前三位是 L2 铜支撑板/62Cu、铜散热环/62Cu、L4 铜支撑板/62Cu；MXC 铜盘/62Cu 排第五。原文接着强调的 199Po 在 AA 这批最终选中事例中为零，不能将旧排序当作新结果。保留了这些文字，建议后续按原始来源表改一小段即可。', 'data/delayed_origins_a_500.csv')
issue('两块支撑板的文字不等于 Figure 7 全部支撑板分组','The two TES substrate-support copper panels (L2 and L4)',
'正文明确指 L2/L4，其数值已按这两块回填为 30.80%；AA 新样本还包含 L3、L5，Figure 7 的 TES Cu support panels 按真实部件包含四块，合计 41.03%。Figure 7 图注仍只写 L2/L4，需后续同步。未将新出现的 L3/L5 错归入 DR 硬件。', 'data/delayed_origins_a_500.csv; code/origins.py; validation/updated_figure_data.json')
issue('已删除部件仍被文字当作现存贡献项','the tungsten detector-bay bottom plate, and the BPE plus residual BGO shielding',
'这两项已回填为 0.00%，但 AA 中旧 W 下挡板和 BPE 本就不存在。新 W 准直器有 0.000273327 cps（延迟本底的 0.90%），已纳入 Figure 7 的 Other detector-bay / shields，未冒称来自旧 W 下挡板，也未新增论文解释。该句以后宜删掉不存在的部件。', 'data/paper_values_500.json: a.origin_volumes; code/origins.py')
issue('旧 4.404 MeV 逐事例案例不是 AA 新追踪证据','One traced $4.404\\MeV$ primary',
'这个完整输运链来自旧 A 的既有案例。物理机制仍可能成立，但本轮未在 AA 中重找同一案例，不能读成“这就是本次 AA 选中样本中的事例”。按用户边界保留，建议后续决定保留为机制说明还是替换为 AA 可追踪事例。', 'baseline/merged_before_this_edit.tex; AA selected-source catalog provenance')
issue('BGO 质量数字仍需按 AA 盖板重新核算','BGO mass decreases from approximately 298 kg',
'298 kg / 258 kg 的旧名义质量比较依赖原大孔顶环；AA 新盖板会改变质量。该处与旧几何结构描述绑定，本轮没有用猜测的密度或体积填一个新数。尚需按与旧比较相同的几何体积口径复核，再更新数字。AA 顶盖参数和材料库已定位；材料库 BGO 密度为 7.1 g/cm³，不能凭常见的 7.13 代入。', 'AA geometry/Materials_Mass_model_AA.geo; /home/ubuntu/MEGAlib_Install/megalib-main/resource/examples/geomega/materials/Materials.geo')
issue('“全部锚点不足 2σ”的结论不再成立','no anchor differs from the analytic direct-rate curve by',
'AA 最大偏差现为 4.54σ（第 10 天），B 为 1.47σ；前一句数字已更新，后面的“不足 2σ”和 This agreement supports… 原样保留，形成明确待改项。直接率是不含跨事例符合的基线，而三路时间叠加可以真实改变最终率，偏差不自动等于归一化错误。本轮已单独核对源率、泊松计数和筛选闭合。', 'data/ANCHORS.csv; validation/timeline_checks.json')
issue('Figure 15 泛称入口和局部 W 不同，需要收窄含义','entrances, local tungsten structures, and geometry-specific active channels\ndiffer.',
'AA 的窗口材质/厚度/层数、通光尺度和 W 边框已与 B 对齐；整体位置、周边结构及 BGO 布局仍不同。旧图注可能被读成窗口和 W 尺寸仍不同，需以后作最小澄清，本轮没有改。', 'AA geometry README; Figure 15 caption')
issue('分析圆盘与物理窗口的指代仍可能混淆','is aperture compatible if this cone intersects a circular analysis disk',
'连续算法沿用同一个分析圆盘：AA 的局部中心 (−13.1,0,−5.2) cm、半径 18.98 mm；B 半径 19 mm。它并不是直径 54 mm 的实体窗口边界。用户此前要求按注入 spot 处理，这个参数没有擅自扩为 27 mm；但全文 entrance/aperture 若被理解为真实薄窗，仍可能造成误解。连续化只改变求交算法，没有改变圆盘、像素点或信号注入口径。', 'code/common.py: recon; signal-response inputs_manifest; AA geometry README')
issue('Figure 9 原绘图规则省略了部分冷盘来源点','Parent-nuclide production sites for selected day-15 delayed events',
'沿用的绘图代码排除了 source_volume 以 ColdPlate_ 开头的记录，AA 为 34/404 条，B 为 7/116 条；剩余点还按二维坐标去重。统计、饼图和核素排行包含所有记录，Figure 9 的点图却不是全部来源的完整显示，旧图注没有讲明。此为既有绘图规则，本轮未扩大图形修改范围；后续宜决定显示全部点或收窄图注。', 'validation/geometry_figure_data.json; retained_figure_styles.py / extracted redraw_figures')
save(O/'WORDING_ISSUES.json',issues)
head='''# AA 替换与连续判定后的表述复核清单

本清单的项目均未修改论文文字。正文唯一非数值变更是删除“24 个方位角采样点及连接线段判交”的说明。论文仍沿用 Under-stage / Lateral-chimney 两个显示名称，没有新增 AA 模型介绍。

最需先处理的是 W01（三路泊松与旧探针描述）、W02–W04（结构图文）、W06–W08（来源排序与分类）、W12（2σ 结论）。**当前 PDF 是按用户范围交付的数据更新稿，不能把这些保留的旧说法当作已经核准的新模型描述。**

'''
body=[]
for r in issues:
 body.append(f"## {r['id']}　{r['title']}\n\n位置：[当前 TeX 第 {r['line']} 行]({O}/paper_clean.tex:{r['line']})。原文锚点：\n\n> "+r['anchor'].replace('\n',' ')+'\n\n'+r['finding']+'\n\n证据：'+r['evidence']+'。\n')
(O/'WORDING_REVIEW_ZH.md').write_text(head+'\n'.join(body))
checks=read(O/'validation/FINAL_CHECKS.json');ma=R['models']['a']['mission_20day'];mb=R['models']['b']['mission_20day']
text=f'''# AA 数据替换与连续圆锥判定交付

已读取用户指定任务 `01a0bfa6-2760-7803-908d-6106613f317c` 的本地会话记录，并核对 AA 输运验收、冻结几何和实际目录。AA 取代论文 Under-stage 的数值输入；Lateral-chimney 保留 B 输运数据。未把旧 A 与 AA 混池，也未新开粒子生产模拟。

## 交付

- [最新完整清稿](paper_clean.pdf) / [TeX](paper_clean.tex)
- [本轮标注稿](paper_this_edit_marked.pdf)：相对本轮前最新完整稿。
- [累计标注稿](paper_cumulative_marked.pdf)：相对 2026-08-31 原稿，旧表保存在附录。
- [15 项表述/图意待核清单](WORDING_REVIEW_ZH.md)：仅列出，尚未改写。
- [数值汇总](data/RESULTS.json)、[时间锚点](data/ANCHORS.csv)、[验证记录](validation/FINAL_CHECKS.json)。

## 本轮结果

| 量 | Under-stage（AA 输入） | Lateral-chimney |
|---|---:|---:|
| 窄窗信号：主动 veto 前/后 | 28394 / 28394 | 28568 / 28568 |
| 连续 Compton 筛选后信号 | 27426 | 28000 |
| Compton 相对主动 veto 后信号保留率 | 96.59% | 98.01% |
| 第 15 天直接最终本底 / cps | 0.0430244251 | 0.0114000168 |
| 20 d 信号计数 | {ma['Ns']:.2f} | {mb['Ns']:.2f} |
| 20 d 本底计数 | {ma['Nb']:.2f} | {mb['Nb']:.2f} |
| 20 d 3σ 通量 / ph cm⁻² s⁻¹ | ({ma['F3']*1e5:.2f}±{ma['F3_MC_SE_approx']*1e5:.2f})×10⁻⁵ | ({mb['F3']*1e5:.2f}±{mb['F3_MC_SE_approx']*1e5:.2f})×10⁻⁵ |

误差为现有输运、光学/响应模板与有限时间重放的统计误差，不含环境或几何系统误差。直接率和经过时间叠加的率是不同量，不能混用。

连续判定不使用方位角网格：对实际像素八顶点及中心构成的 81 个位置对，求圆盘上轴向余弦的连续极值范围，判断目标锥角是否在范围内；边界驻点由四次多项式求根，保留符号以区分前后方向。位置仍只由像素 ID 确定，没有用沉积真位置替代像素不确定性。

与各自 24 点版本相比，AA 的窄窗最终信号净增 2 条，B 净减 1 条；所有变更事例均与 1536 点高密度对照一致。AA/B 的 641/844 条宽窗主动 veto 后本底候选，连续与原像素判定完全相同。AA 替换旧 A 带来的较大变化主要来自新几何及新输运数据，不应归因于连续算法。

时间计算沿用此前用户确认的真实三路泊松叠加，在第 0、5、10、15、20 天各重放 200000 s，源流强不人为放大；共 10 个既有模板后处理任务。全到达时间均生成，只有必然触发 BGO 且无 TES 的记录压缩为饱和标记；低于阈值的沉积保留。信号、prompt、delayed 统一按 1 μs 相邻间隔形成组，先累加像素沉积，再应用 500 eV FWHM 响应和选窗。塑料不参加判选。信号损失按真实到达事例的身份比较；未使用单信号条件探针。信号 on−off 净计数与保留计数在本次十个锚点完全一致。

## 修改范围与验证

清稿按数值/表格回填，Figure 7、9、11–16 更新数据；Figure 1–6、8、10 保持文件哈希不变。Figure 6 连续曲线示意原已完成，本轮不重画。Figure 9 的浅色结构底图仍需按 AA 复核。环境筛选的 B 响应及转移比例未变，仅换用本轮 B 的气球灵敏度归一化。

已逐字母 token 检查：除批准删除的离散采样说明外，英文词序完全保持原稿；没有加入 AA 改模记录、额外原理说明或防御性段落。因而原稿中不成立的概括性语句也被保留，详见单列清单。几何段的旧顶环孔径和 BGO 名义质量仍待统一几何语义后复核，不以臆测值回填。

连续几何通过 180 个解析边界用例和 2496 个独立极值对照；物理事件逐项响应/权重核对通过。十个锚点的到达计数与物理率符合泊松波动；信号损失分类闭合。统计误差保持同一模板跨 81 节点的时间相关性，先积分事件权重再平方。

三份 PDF 均编译通过，无未定义引用、重复标签、缺字或超宽排版告警。清稿 {checks['pdfs']['paper_clean']['pages']} 页，本轮标注 {checks['pdfs']['paper_this_edit_marked']['pages']} 页，累计标注 {checks['pdfs']['paper_cumulative_marked']['pages']} 页。检查了结果图与主要表格的实际渲染。图中文字仍使用 DejaVu Sans；Figure 15 根号伸展符号沿用原稿 STIX 数学符号字形，不是新增正文混用字体。

## 复现与文件入口

全部新写入均在本目录，原模拟与原稿只读。

1. `code/prepare_response.py a|b`：连续信号/本底分类，沿用固定响应。
2. `code/prepare_timelines.py a|b`：独立归一化和只影响必 veto 无 TES 记录的标记压缩。
3. 编译 `code/timeline_deferred.cpp`；`code/run_timelines.py`、`code/analyze.py`：已运行的泊松后处理与逐组判选。没有要求继续扩大样本量。
4. `code/summarize.py`、`code/origins.py`、`code/auxiliary_data.py`：累计计数、原始选中来源、环境比例。
5. `code/sync_paper.py`、`code/sync_figures.py`、`code/build_marked.py`，随后 XeLaTeX / `latexmk` 和 `code/validate_delivery.py`。

详细来源及 SHA-256 见 `SOURCE_MANIFEST.json`；没有扫描整个原始数据盘。来源点提取仅根据 404 条选中 AA 延迟记录定位所需的命名任务文件，并在找到目标事件后停止，结果已缓存。
'''
(O/'README_ZH.md').write_text(text)
sourcepaths=[O/'baseline/merged_before_this_edit.tex', O.parent/'revision_20260921_compton_continuous/paper_clean.tex',AA/'CONTINUATION_FINAL_REPORT_ZH.md',AA/'CONTINUATION_FINAL_AUDIT.json',AA/'data/AA_production_freeze.json',AA/'geometry/Mass_model_AA.geo',P/'engineering/mass_model_AA_20260921/README_ZH.md',AS/'derived/merged/manifest.json',AS/'derived/merged/category_registry.json',AA/'signal_response/data/signal_aa_catalog.npz',S/'data/signal_b_catalog.npz',S/'inputs_manifest.json',O.parent/'three_stream_poisson_20260921/code/analyze.py',O.parent/'compton_continuous_evaluation_20260921/REPORT_ZH.md']
sourcepaths.append(Path('/home/ubuntu/.codex/sessions/2026/09/21/rollout-2026-09-21T00-28-52-01a0bfa6-2760-7803-908d-6106613f317c.jsonl'))
save(O/'SOURCE_MANIFEST.json',{'sources':[{'path':str(p),'sha256':sha(p)} for p in sourcepaths],'background_AA_mmaps':str(AS/'derived/merged'),'background_B':str(BC/'combined_event_catalog.npz'),'old_A_reused_as_response':False,'unit_normalization':'AA per-family independent TT / activities; atmospheric gamma continuum importance and time scaling applied once; no mono511 additive background','input_geometry_sha256':sha(geometry('a')),'source_record_extraction':{'selected_AA_delayed_events':404,'named_jobs':len(list((O/'data/a/origin_cache').glob('*.json'))),'whole_disk_scan':False}})
save(O/'MACHINE_HANDOFF.json',{'status':'COMPLETE_REQUESTED_DATA_UPDATE_WITH_WORDING_REVIEW_PENDING','request_thread':'01a0bfa6-2760-7803-908d-6106613f317c','output':str(O),'clean_pdf':str(O/'paper_clean.pdf'),'cumulative_pdf':str(O/'paper_cumulative_marked.pdf'),'this_edit_pdf':str(O/'paper_this_edit_marked.pdf'),'numerical_results':str(O/'data/RESULTS.json'),'wording_issues':str(O/'WORDING_ISSUES.json'),'allowed_prose_edit':'Remove 24-azimuth sampling and polygon-segment intersection description only','physical_models':{'Under-stage':'AA frozen 20260921 v1','Lateral-chimney':'retained B'},'continuous_method':'disk directional-cosine extrema, no angular sampling','pixel_geometry_unchanged':True,'three_actual_Poisson_streams':True,'conditional_signal_probe_used':False,'no_plastic':True,'new_particle_transport':False,'unresolved_prose_issue_count':len(issues),'figures_replaced':[7,9,11,12,13,14,15,16],'figures_not_redrawn':[1,2,3,4,5,6,8,10],'geometry_numbers_requiring_followup':['old top-annulus inner diameter','old nominal BGO mass comparison'],'validation':str(O/'validation/FINAL_CHECKS.json')})
(O/'WORK_STATE_ZH.md').write_text('本轮范围已完成。清稿/两份标注稿与数值验证均已生成。15 项表述/图意问题按用户要求仅列清单，未改写。详见 README_ZH.md、WORDING_REVIEW_ZH.md、MACHINE_HANDOFF.json。\n')
print('REPORTS WRITTEN',len(issues))
