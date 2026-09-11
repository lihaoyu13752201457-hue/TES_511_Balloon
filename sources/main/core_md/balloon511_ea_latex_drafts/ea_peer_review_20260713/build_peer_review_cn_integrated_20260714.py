#!/usr/bin/env python3
"""Build a Chinese, self-contained PDF-comment edition of the EA peer review.

The 13 July annotated PDF deliberately used short English pop-ups and sent the
reader to a separate HTML report for the full finding and requested revision.
This builder keeps that reviewed manuscript baseline and its exact highlights,
but replaces every pop-up with a complete Chinese comment.  It also adds note
annotations for the six formal review items that had no line-level highlight,
so the PDF comments sidebar contains every formal R1/R2 finding.

The active 14 July manuscript is newer than the reviewed baseline.  We do not
silently re-anchor the old review to that changed text; the output therefore
remains an auditable review-baseline artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import runpy


HERE = Path(__file__).resolve().parent
BASE_TEX = HERE / "balloon511_ea_draft_en_peer_review_annotated.tex"
DEFINITIONS = HERE / "build_peer_review.py"
OUTPUT_TEX = HERE / "balloon511_ea_draft_en_peer_review_annotated_cn_integrated_20260714.tex"
OUTPUT_REPORT = HERE / "ea_peer_review_report_cn_integrated_20260714.md"


@dataclass(frozen=True)
class ZhReview:
    category: str
    title: str
    finding: str
    action: str
    basis: str


RESOLVED_REVIEW_IDS = {"M03"}


ZH_REVIEWS: dict[str, ZhReview] = {
    "M01": ZhReview(
        "科学范围",
        "报告的本底只覆盖探测器—低温恒温器子系统，而非完整载荷",
        "论文把几何称为质量完备、把流程称为端到端，但本底预算明确只覆盖探测器—低温恒温器分支。Laue 透镜、透镜支撑、吊舱及其他载荷质量都可能散射辐射并产生瞬发或活化产物；在输运或约束这些贡献之前，不能据此推断任务级总本底。",
        "要么在包含光学系统和主要支撑质量的载荷模型中输运全部本底族，要么给出有依据的上限。完成之前，标题、摘要、结果和结论应统一使用“探测器—低温恒温器子系统本底”。",
        "稿内范围与表述的一致性",
    ),
    "M02": ZhReview(
        "审计更正（已闭合）",
        "50 keV BGO 离线反符合的数据链完整",
        "2026-08-04 的项目数据血缘审计确认：最终定量选择只读取逐步 CC HIT 沉积，按事例累加匹配 BGO 主动体积的总沉积，并施加小于 50 keV 的后处理条件。原始 SIM 和生产目录均含低于 80 keV、包括 50–80 keV 的沉积；HTsim、原生 trigger/veto flag 及 detector map 中的 80 keV 字段均未参与最终选择。原审阅把 detector-map 字段推断为击中存储门的前提不成立。",
        "把正文中“记录与分析均为 50 keV”改成期刊化的方法描述：逐事例汇总主动屏蔽沉积，并施加 50 keV 离线沉积能反符合。无需原生阈值重跑；BGO 光学与电子学 turn-on 仍应作为独立的探测器响应局限。",
        "最终解析器与选择代码、原始 SIM 的 50–80 keV 沉积及生产 catalog 的数据血缘审计",
    ),
    "M03": ZhReview(
        "科学范围",
        "送审基线的最终延迟本底只包含中子诱发活化",
        "送审基线的方法部分明确说七个入射族的活化尚未输运且不能视为零，但摘要和结论仍使用“完整选择”“全链条”和总本底表述。入选事件的重要性未必与库存活度成比例，因此不能把遗漏项安全地视为可忽略。",
        "在分级屏蔽几何中用足够的位置样本输运全部八个活化族，或为每个遗漏族传播可辩护的界限；完成之前，所有最终速率和灵敏度都应标为“仅含中子活化的部分模型”。",
        "稿内范围与表述的一致性",
    ),
    "M04": ZhReview(
        "源模型",
        "大气 511 keV 分量给出了结果，却没有可复现的源模型方法",
        "该分量占最终本底的 26.59%，但表 1 和公共时间轴说明都未列出它；强度、谱宽、角分布、源面、曝光、权重、高度依赖和轨迹缩放均未说明。PARMA3 原始论文还报告了约 0.5 MeV 的湮没小峰，因此额外加入窄线必须明确证明没有重复计数。",
        "新增第四源流的方法小节和流程节点，给出来源、能谱、角分布、绝对归一化、生成计数、曝光、cut-flow 与轨迹规则；并说明在加入显式窄线前，PARMA/EXPACS 连续谱中的湮没特征是被移除、保留还是已证明可忽略。",
        "稿件内容与 PARMA3 原始论文",
    ),
    "M05": ZhReview(
        "科学用例",
        "当前曝光折叠并不代表一次银河中心气球观测",
        "信号响应采用轴上、北天/近天顶参考，而论文的动机目标是银河中心。轨迹为连续对源的合成轨迹，并明确忽略可见性、目标仰角、地球遮挡、重新指向、姿态抖动和离轴损失。因此曲线只是曝光缩放基准，不是飞行预报或银河中心灵敏度。",
        "将真实或参数化星历与斜程大气柱、源可见性、占空比、指向抖动和离轴响应共同折叠；否则把所有任务级说法改成“连续照射、轴上参考曝光”。",
        "稿内观测几何与结论范围的一致性",
    ),
    "M06": ZhReview(
        "科学用例",
        "标题灵敏度只适用于未分辨的单色窄线",
        "科学动机讨论约 1.3 和 5.4 keV 的本征线宽，但信号为单色并用 ±0.420 keV 窗选择。高斯估算表明，该窗口可保留假定 0.420 keV 探测器线的约 98.1%，但卷积后对本征 FWHM 为 1.3 和 5.4 keV 的线仅保留约 53% 和 14.5%。",
        "报告灵敏度随本征线宽和质心偏移的优化结果，至少包括未分辨、1.3 keV 和 5.4 keV 三种情况；完成之前，每次引用阈值都应明确写“未分辨线”或“单色线”。",
        "依据稿内线宽所作的审阅者筛查计算",
    ),
    "M07": ZhReview(
        "设计逻辑",
        "40/30/10 mm BGO 方案是被选定的，而不是被证明为最优的",
        "事件来源分解可以支持方向性屏蔽，但不能唯一确定三处厚度。稿件没有候选集合、目标函数、独立评估样本、质量—本底权衡、信号损失、功耗/读出负担或机械约束。按表 4 粗算，开孔前 BGO 约 41768 cm³；取 7.13 g cm⁻³ 时约 298 kg，实际清单质量对气球可行性至关重要。",
        "给出候选几何的设计矩阵或响应面、清单中的真实材料质量、优化目标和约束，并用独立统计量评估所选点；否则把“优化”改为“选定的分级屏蔽构型”。",
        "稿内几何筛查计算；最终需 CAD/质量清单核实",
    ),
    "M08": ZhReview(
        "光学物理",
        "自定义 Laue 衍射过程需要晶片级物理验证",
        "把目标反射率转换成衍射平均自由程，再让标准吸收过程与之竞争，并不会自动重现原始反射率。稿件也未证明 XOP 镶嵌摇摆曲线与额外高斯晶面扰动是否重复计算角展宽，或是否正确抽样衍射微晶取向。所有信号和灵敏度结果都依赖这一响应。",
        "推导竞争风险构造；在角度和能量维度把反射、透射、吸收及出射角分布与 XOP/CRYSTAL 对比；证明步长收敛，并给出晶体尺寸、环几何、入射面积、模型版本和镶嵌抽样规则。",
        "稿内光学算法与验证链",
    ),
    "M09": ZhReview(
        "归一化",
        "公共符合时间轴把单位重放信号速率称为物理速率",
        "参考通量下聚焦入口物理速率为 1.48×10⁻³ s⁻¹，但符合时间轴使用 0.987 s⁻¹ 并把三个速率都称为物理速率；表 2 又把信号行称为单位重放。若信号未从本底记账中排除，以约 660 倍物理速率注入可能影响偶然分组或混合流归因。",
        "构造不含信号的本底符合轴，或按被测试的物理通量注入信号；说明参考时长、最终全带宽速率、混合组归因规则、同流/混流计数，以及死时间/活时间因子的精确定义；单位重放图表必须醒目标注。",
        "稿内速率定义与时间轴构造",
    ),
    "M10": ZhReview(
        "探测器时序",
        "1 μs 符合窗和活时间因子缺少探测器/读出依据",
        "公共时间轴假定 1 μs 分组窗，但没有给出 TES 脉冲时长、成形时间、触发逻辑、复用带宽、逐像素死时间、饱和或堆积模型。在接近 10³ s⁻¹ 的全带宽速率下，这些假设会影响事件分组和活时间。",
        "把符合窗和反符合窗绑定到明确的探测器/读出架构，加入逐像素脉冲与死时间行为，并给出时间窗灵敏度；不要把当前偶然活时间因子解释为硬件死时间模型。",
        "稿内时序假设与硬件解释",
    ),
    "M11": ZhReview(
        "统计",
        "瞬发本底中心值只由五条最终记录支撑",
        "两条正电子和三条中子记录决定瞬发中心值；六个族最终计数为零，而零计数、高权重的光子分量主导保守结果。逐分量上端点可作为透明的压力界限，但把多个双侧 95% 端点相加没有已说明的联合 95% 覆盖率，也不是总量置信区间。",
        "增加输运统计，尤其是瞬发光子；按各模拟设计使用正确的二项/泊松似然，并在联合似然或后验中加入蒙特卡洛干扰参数；把端点和标为有意保守的有限样本界限，而不是精确总区间。",
        "稿内有限计数支持与区间定义",
    ),
    "M12": ZhReview(
        "统计",
        "S/√B 只是计数代理量，还不是发现显著性或正式通量阈值",
        "该指标假定本底精确已知，忽略控制区不确定性、线状大气本底干扰参数、搜索试验因子和物理系统误差。即使使用文中计数，泊松 Asimov 结果也与 S/√B 不同，说明该公式不是唯一的显著性定义。",
        "使用含本底干扰参数并结合预定空间/控制区信息的信号加本底似然；在此之前，把 Z 称为计数性能代理，把 F₃σ 称为基于计数的参考阈值。",
        "稿内统计定义",
    ),
    "M13": ZhReview(
        "验证",
        "轨迹折叠验证过于宽泛，且没有给出数值证据",
        "正文称正电子、中子和光子在 480–550 keV 的调制相符，但未给出各状态、计数、预测比例、Q 值、不确定性或 z 的定义。宽能带相符不能证明角谱和能谱变化时，总族通量缩放在窄 511 keV 窗内无偏。",
        "在结果中列出四状态比较，并在分析窗内或附近验证能量/角度分辨的重加权；量化未测试粒子族的偏差，不要把解析源场缩放表述成已验证的输运。",
        "稿内验证声明与展示证据",
    ),
    "M14": ZhReview(
        "可复现性",
        "关键输运与响应配置缺失",
        "稿件未给出 Geant4、MEGAlib/Cosima、XOP/xoppylib/DABAX、PHITS/EXPACS 的精确版本，也未完整说明物理列表、电磁/强子模型、产生截断、放射性衰变设置、源能限/源面和大多数随机种子；数据声明只承诺将来建立仓库。",
        "投稿时归档并引用带版本的快照，纳入配置、几何与源文件、曝光表、轨迹数组、响应与选择代码、环境锁文件、种子以及可重建全部表图的脚本。",
        "稿内可复现性信息",
    ),
    "M15": ZhReview(
        "可比性",
        "参考几何与分级屏蔽几何的总量并非同口径比较",
        "送审基线中，参考几何是在 CsI 构型下的全族延迟项，而最终 BGO 构型只含中子延迟项；大气线只在最终预算中出现，主动屏蔽阈值定义也不同。因此观测速率变化不能只归因于屏蔽设计。",
        "在两套几何中使用相同的入射流、活化族、击中存储、响应、阈值、符合逻辑和统计曝光；解释几何效应前先给出成对的分量变化。",
        "两套几何的输入与选择口径",
    ),
    "M16": ZhReview(
        "探测器响应",
        "420 eV 应明确标为预估能量分辨率",
        "当前探测器概念把 420 eV FWHM 作为逐像素高斯响应的输入；它不是探测效率，也不表述为完整阵列已经实测达到的性能。",
        "在正文中简要说明 420 eV FWHM 是响应模型采用的预估能量分辨率；具体响应实现仍在方法部分交代。",
        "稿内探测器响应定义",
    ),
    "M17": ZhReview(
        "探测器物理",
        "“探测效率”容易与系统探测效率混淆",
        "这里的单层约 49% 和六层接近 1 指 Ta 中发生相互作用的效率。",
        "仅将“探测效率”改为“相互作用效率”；本段无需追加其他效率解释。",
        "稿内探测效率术语",
    ),
    "M18": ZhReview(
        "通量约定",
        "大气透射与有效面积术语不一致",
        "顶层大气通量乘以透射率 T 得到的是载荷处通量，而不是“载荷上方通量”。文中 S/F₀=11.13 cm² 已含 T=0.739，因此是包含大气的面积；按稿件定义，仪器本身的选择后面积约为 15.1 cm²。",
        "统一定义顶层大气和载荷处通量，说明天顶/斜程大气柱与透射模型，并把仪器有效面积与大气折叠后的计数—通量换算分开。",
        "稿内通量与面积定义",
    ),
    "M19": ZhReview(
        "源归一化",
        "PARMA 模型版本与角分布/源面归一化需要分开说明",
        "源段落称 PARMA3.0，却引用与 4.0 版相关的 2016 天顶角扩展；从等 μ 分箱方向强度到远场面积源速率的换算也未完整定义，尤其缺少投影面积因子和曝光单位。",
        "区分能谱模型和角分布模型版本，公开微分通量单位与源面约定，并推导含立体角和投影面积因子的分箱积分速率。",
        "稿内模型版本和归一化定义",
    ),
    "M20": ZhReview(
        "事件选择",
        "拓扑/FoV 检验较宽松，边界处理含糊",
        "双击中事件只要 81 个亚像素组合中的任一组合、任一散射次序穿过孔径就通过；单点事件自动通过，六重以上事件不排序而保留，正文也没有说明不可重建事件是否进入最终速率。旧几何基准不能验证当前几何性能。",
        "为每种多重度定义精确布尔规则，在实际分析几何中重跑基准，展示方位角/亚像素收敛，并报告信号—本底效率或 ROC 型权衡；相关时应纳入位置/能量不确定性和多普勒展宽。",
        "稿内事件选择逻辑",
    ),
    "M21": ZhReview(
        "轨迹模型",
        "轨迹离散和活化初始条件定义不足",
        "以 0.25 d 间隔取 81 个网格点，在 20 d 内定义的是 80 个区间，而不是 81 个四分之一天时间箱；初始库存 Nₖ(0)、时间单位换算、插值/求积规则以及活时间因子的插入方式均未说明。",
        "公开 81 点数组和各区间时长，说明 Nₖ(0)、数值更新方法与单位，并定义每个活时间比例如何计算和应用。",
        "稿内轨迹离散公式",
    ),
    "M22": ZhReview(
        "不确定性",
        "最终图中缺少主导解释的不确定性",
        "瞬发结果只有五条记录支撑，速率却给到四至五位有效数字；64 个响应种子的离散只测试响应积分，不是输运计数不确定性，而且没有传播物理系统误差预算。",
        "在最终分量图和 cut-flow 中加入蒙特卡洛区间，把联合不确定带传播到曝光曲线，按证据支持的精度取舍数字，并扫描辐射场、物理列表、几何、响应、阈值、透射和指向假设。",
        "稿内不确定性展示",
    ),
    "M23": ZhReview(
        "物理解读",
        "图示 cut-flow 不支持“屏蔽控制大气线”的解释",
        "正文称主动覆盖控制大气路径，但八条大气线记录全部通过主动反符合和拓扑选择。所示屏蔽降低的是模拟瞬发与延迟符合，而不是已经通过孔径进入的线状天向分量。",
        "把屏蔽结论限制在有数据支持的瞬发/延迟分量；大气线的抑制应单独讨论孔径设计、指向调制、控制区和空间—能谱建模。",
        "最终 cut-flow 与讨论段的对应关系",
    ),
    "S01": ZhReview(
        "稿件逻辑",
        "方法与结果交叉混排，遮蔽了证据链",
        "方法部分混入信号速率、cut-flow、拓扑效率、旧基准和轨迹验证结果；屏蔽尺寸又先于支持它的选择证据出现。引言还多次重复紧致源动机和参考通量。",
        "建议顺序为：引言与目标；仪器和假设；源/响应/选择/统计方法；验证和设计协议；结果；讨论与局限；简短结论。F₀ 只定义一次，除必要归一化核查外，把结果数值移出方法。",
        "稿件结构与证据顺序",
    ),
    "S02": ZhReview(
        "写作与行文",
        "文字可理解，但过于围绕开发过程且信息压缩过度",
        "若干段落把实现、理由、公式、验证和解释塞进超过 100 词的句子；“recording hook”“process class”“preregistered”“starved continuum”等内部开发用语，以及“easy to read”“three linked views”“two columns answer”等元话语削弱期刊文体。",
        "按科学功能拆分长句，删除起草/开发者旁白，直接陈述结果；统一 event/record/group/hit、分析窗术语、FoV 与 Laue 大小写，并统一美式或英式英语。",
        "全文写作与术语一致性",
    ),
    "J01": ZhReview(
        "Experimental Astronomy 投稿规范",
        "选题适合 Experimental Astronomy，但稿件尚未达到投稿状态",
        "探测器、本底、屏蔽和分析方法与期刊仪器方向契合；但当前自定义版式、按引用顺序编号的参考文献、DOI 格式、不完整声明和将来时的数据可用性说明，不符合本轮审阅所依据的投稿要求。",
        "改用当前 Springer Nature LaTeX 模板；按期刊要求处理作者—年份、字母排序参考文献和 DOI URL；核实已发表/接收版本；补全标题页、Statements and Declarations、经费、利益冲突、作者贡献以及现在时的数据可用性声明。",
        "本轮审阅时的 Experimental Astronomy 官方范围与投稿指南",
    ),
    "J02": ZhReview(
        "摘要与图件",
        "摘要长度和关键词数量合格，但结论强度与图件仍需修改",
        "摘要处于期刊 150–250 词范围内并有六个关键词，但 BGO 与 FWHM 未定义，完整性表述过强；多幅定量图仍为栅格图，稀疏谱图的图注也缺少可独立理解的归一化和不确定性说明。",
        "采用审阅报告给出的重写思路，定义缩写，并在缺失物理完成前保留范围限制句；图尽可能提供矢量 PDF/EPS，或满足线图/组合图分辨率要求；图注应补单位、箱宽、归一化状态和统计区间。",
        "本轮审阅时的 Experimental Astronomy 投稿指南",
    ),
    "J03": ZhReview(
        "AI 使用披露",
        "大量采用 AI 生成的实质性措辞可能需要披露",
        "期刊政策区分机械校订与实质性生成式 AI 使用。若大量采用重写后的标题或摘要，这已经超出拼写修正。",
        "投稿时复核期刊最新政策；如有要求，披露工具和用途，并声明全体作者已审阅、核实且对最终科学内容负责。",
        "本轮审阅时的 Experimental Astronomy 投稿指南",
    ),
    "N01": ZhReview(
        "死时间与屏蔽计数率",
        "任务活时间因子暗示未报告的约 2–3×10⁴ s⁻¹ 时间轴速率，反符合损失随假定 1 μs 窗线性增长",
        "图 4c 定义 L=exp(−Rτ)，正文却没有。基准轴给出 R≈1.03×10³ s⁻¹、L=0.9990；任务折叠给出 L=0.97166–0.97986，若 τ=1 μs，则最终几何全带宽轴速率约为 2.0–2.9×10⁴ s⁻¹，是基准的 20–30 倍，可能主要来自 BGO 屏蔽计数。偶然反符合损失约为每微秒 2–3%，几十微秒的 TES 兼容硬件窗会成为一级任务效应。",
        "报告最终几何全带宽和屏蔽计数率，在正文定义活时间因子，把反符合窗与明确的读出时序架构绑定，并展示 1–100 μs 窗下的任务性能。该项应与 M10 同列最高优先级。",
        "图 4c 公式、稿内数值及独立通量×面积量级核查",
    ),
    "N02": ZhReview(
        "信号透射几何",
        "T=0.739 必须对应明确的剩余大气柱和视角；若把垂直柱用于 45° 侧向几何，信号约高估 12%",
        "T=0.739 对应 X≈3.5 g cm⁻² 的垂直剩余柱，这是 38.75 km 附近的典型量级；但光轴在地平线上方 45°，其斜程柱为垂直柱的 1.41 倍，对应 T≈0.65。稿件没有说明柱深、角度或衰减来源，同一 T_atm,511(t) 又乘到每个轨迹箱，错配会令整条信号曲线约降低 12%、通量阈值约升高 13%。",
        "说明 T=0.739 与 T_atm,511(t) 使用的大气柱、衰减数据源和视角；若锚点是垂直值，应按实际源仰角重算或给出理由。该项与 M05 的银河中心仰角问题直接耦合。",
        "标准大气柱与 XCOM 空气衰减的审阅者筛查计算",
    ),
    "N03": ZhReview(
        "源流记账",
        "第四个本底流缺失于源枚举、源表和公共时间轴",
        "摘要和引言承诺信号、瞬发、延迟与大气 511 keV 线四个输入共享同一选择，且大气线占最终本底 26.59%；但第 3.2 节只构造“三个源层”，表 1 只列三个，第 3.4.1 节时间轴也只有瞬发/延迟/信号。大气线似乎绕开了文档化的泊松轴、偶然符合和反符合机制，直到最终 cut-flow 才出现八条记录。",
        "把该流加入第 3.2 节、表 1 和公共时间轴，并补齐 M04 要求的来源与归一化；若它确实不经过公共轴，则必须明确解释表 5 的主动反符合和拓扑列如何生成。",
        "稿内源流枚举与 cut-flow",
    ),
    "N04": ZhReview(
        "蒙特卡洛分配",
        "抽样设计使主导保守界限的粒子族统计最贫乏",
        "第 3.2.1 节复制/去权保护了少数非光子族，使每族等效曝光约 1/(6.79×10⁻⁴)≈1.5×10³ s；光子族却只有 1/(5.43×10⁻³)≈184 s。零计数光子项随后贡献保守总量 4.77×10⁻² s⁻¹ 中的 2.0×10⁻² s⁻¹，设计在下游形成了相反的瓶颈。",
        "在权重旁报告各族等效曝光；后续输运应明显增加瞬发光子样本，必要时对线附近光子按能量和角度分层抽样。若仍为零计数，光子曝光增加十倍可把其端点量级约降十倍。",
        "表 6 事件权重的倒数核查",
    ),
    "N05": ZhReview(
        "选择物理",
        "窗内 511 keV 光子对主动反符合的 100% 存活是能量守恒恒等关系，不是抽样结果",
        "对单色 511 keV 入射光子，TES 总能量若在 510.58–511.42 keV 内，未计能量最多约 0.4 keV（另加响应展宽），远低于 50 keV 屏蔽阈值。因此窗内信号或大气线事件不可能同时带有可触发反符合的屏蔽沉积；表 2、表 5 的 100.00% 存活是结构性结果，主动反符合对该分量天然失明。",
        "在第 4.3 节明确写出这一恒等关系，并改写所有暗示主动覆盖可控制大气线的句子；可作用于该分量的是孔径/准直、指向调制和空间—能谱建模。",
        "在既定选择下的能量守恒",
    ),
    "N06": ZhReview(
        "同核异能态",
        "活化累积没有说明同核异能态的处理方式",
        "产生记录含激发能，day-15 库存又按体积、核素和激发态匹配，但半衰期只说用 NUBASE2020 基态值核对。亚稳态寿命可能与基态相差很大，因此方程（3）需要明确激发态库存如何处理。",
        "说明同核异能态采用独立衰变常数、迅速退激到基态还是排除；报告 day-15 库存中是否存在同核异能态及其活度份额。",
        "稿内激发态记录与半衰期定义",
    ),
    "N07": ZhReview(
        "引用支持",
        "SPI 的“10⁻⁴ 量级点源上限”被归给了弥散发射论文",
        "第 1.1 节原先把点状源通量上限归于弥散核球/盘分析；稿内唯一专门的紧致源检索是 INTEGRAL/IBIS（De Cesare 2011）。观测比较值还必须与蒙特卡洛归一化分开，不能把前者当成模拟输入。",
        "由 IBIS 紧致源检索单独承担观测依据：先将已发表的 2σ 上限按高斯近似线性换算为 3σ 等效上限 2.4×10⁻⁴ ph cm⁻² s⁻¹，再乘固定 45° 方向的大气透过率 0.6520，得到唯一的载荷平面观测参考通量 1.565×10⁻⁴ ph cm⁻² s⁻¹。",
        "引用范围核查；作者仍需对原始论文逐条确认",
    ),
    "N08": ZhReview(
        "摘要可比性",
        "摘要并列的参考率与最终率具有不同核算边界，不能解释为纯屏蔽增益",
        "当前两套模拟都已经完成全入射族活化输运；剩余问题是显示口径不同。参考几何数字用于瞬发加延迟的来源诊断，不含显式大气 511 keV 线；最终数字则包含瞬发、全八族延迟和大气线，并采用不同屏蔽与响应链。",
        "在摘要中明确前者是不同口径的来源诊断预算、不是同口径屏蔽增益；若要量化屏蔽增益，仍需给出相同源流、响应、阈值和选择下的成对计算。",
        "稿内摘要与方法口径",
    ),
    "N09": ZhReview(
        "参考曝光",
        "参考曝光时长和逐流实例计数没有给出",
        "7215233 个实例与 1275 个混合符合，在总轴速率 1.026×10³ s⁻¹ 下暗示 T≈7.0×10³ s；公式 2τT·ΣRₖRₗ 也可重现 1275，说明记账自洽。但正文没有报告 T、逐流实例数和组大小分布。",
        "说明 T、逐流实例计数和分组统计，并在同一段给出 M09 要求的混合组归因规则。",
        "依据稿内数字重建并核实",
    ),
    "N10": ZhReview(
        "定义",
        "W=118.3 与“2025-08-31 太阳条件”需要定义和来源",
        "W 很可能是 EXPACS/PARMA 使用的太阳活动指数，但首次出现时没有说明符号、单位、数据源及其对八个粒子族通量的影响。",
        "定义 W，给出所述日期的来源，并说明飞行时间窗内太阳条件变化对八族通量的敏感性。",
        "稿内首次定义与来源信息",
    ),
}


# Line-level comments keyed by the exact reviewed anchor.  These are placed
# before the full formal item so each highlight still explains its local edit.
PINPOINT_ZH: dict[tuple[str, str], str] = {
    ("J02", "Detector-coupled Monte Carlo estimate of background and unresolved-line sensitivity for a balloon-borne 511 keV Laue-lens TES telescope"): "本处标题过长，而且给人的灵敏度成熟度高于当前部分本底模型所能支持的程度；应缩短并明确范围。",
    ("M03", "final full chain"): "送审基线最终几何的延迟流仅含中子诱发活化，“最终全链条”夸大了完整性。",
    ("M03", "complete selection"): "事件选择可以是完整的，但送审基线的物理本底输入并不完整；摘要必须写明仅含中子延迟项。",
    ("M18", "single payload-plane observational reference flux"): "本处只定义载荷平面的观测参考通量：2.4×10⁻⁴×0.6520=1.565×10⁻⁴ ph cm⁻² s⁻¹；不再在本段引入模拟注入通量及其载荷换算值。",
    ("M17", "increasing the collecting-area-to-detector-area ratio"): "本处现准确表述聚焦收益为提高收集面积与探测器面积之比、降低探测器相关本底，并明确 Laue 透镜仍是窄视场定向光学，不再声称扩大天空覆盖。",
    ("M17", "estimated interaction efficiency of about"): "本处仅作术语替换：单层约 49% 和六层接近 1 均称为相互作用效率，不追加其他效率解释。",
    ("M16", "estimated energy resolution and simulation input"): "本处现只简要说明 420 eV FWHM 是响应模型采用的预估能量分辨率，不再由热容推导或表述为已实测系统性能。",
    ("M02", "optimized BGO transport records shield hits"): "【2026-08-04 审计更正】原始 SIM 与生产目录均保存低于 80 keV 的 CC HIT 沉积；最终选择按事例求和并离线施加 50 keV cut，因此无需原生阈值重跑。",
    ("S02", "focal-plane plane"): "删除重复词，改为 focal plane。",
    ("M08", "mosaic system is adopted to make the Monte Carlo calculation convenient"): "计算方便不是物理理由；应说明科学设计依据并验证响应。",
    ("M08", "to avoid double counting with standard photoelectric absorption"): "竞争过程构造不会自动重现目标 XOP 反射/透射/吸收；需给推导和晶片基准。",
    ("M01", "primary background budget"): "这里明确排除了光学系统和其他载荷质量，因此任务级总本底表述必须收窄，或先输运/约束遗漏贡献。",
    ("M19", "PARMA3.0"): "应区分 PARMA 能谱模型版本与所引天顶角扩展，并记录准确 EXPACS 版本。",
    ("S02", "custom recording hook"): "实现细节可以保留，但应写成可复现的科学数据采集方法，而不是开发者措辞。",
    ("M04", "source layers used"): "下表漏列后来占最终本底 26.59% 的大气 511 keV 流；需补来源、归一化、曝光及角谱定义。",
    ("M03", "is not treated as zero"): "这句限定是正确的，但会使后文“全链条”和“总本底”失效；应完成全族输运或传播界限。",
    ("M18", "surviving signal rate"): "随后由计数换算的面积已含大气透射，应另报仪器本身选择后面积。",
    ("M05", "not a flight forecast for a named launch campaign"): "固定 45° 轴已纠正斜程透过率，但仍未折叠真实源可见性、指向损失和离轴响应；该限制必须贯穿任务和灵敏度表述。",
    ("M07", "only optimized geometry"): "没有候选集合或目标函数；完成受质量约束的独立权衡前，应称“选定构型”。",
    ("M12", "counting metric"): "S/√B 在本底精确已知时只是诊断代理，并非正式发现显著性；应使用似然或改名。",
    ("M09", "streams are combined"): "0.987 s⁻¹ 的信号后来被说明为单位重放，而非参考源物理速率；构造符合前必须分开两种归一化。",
    ("M10", "candidate group"): "需从 TES 脉冲、触发、屏蔽、复用和死时间说明 1 μs 窗，并做时间窗扫描。",
    ("S02", "starved continuum"): "表述口语且含糊；根据真实含义改为“蒙特卡洛抽样稀疏的连续谱”或“物理上较弱的连续谱”。",
    ("M20", "if any of these 81 trajectories"): "“任一即通过”是刻意宽松的存在性规则，不是不确定性边缘化；需展示信号—本底权衡和亚像素敏感性。",
    ("M20", "retained without ordering"): "应明确该分支是否通过最终选择，并量化其信号/本底贡献。",
    ("M20", "Unreconstructed events remain in the baseline rate accounting"): "边界规则含糊；需明确不可重建事件是进入还是未通过 FoV 选择速率。",
    ("M20", "retained legacy geometry"): "不同几何不能直接验证当前 ARM 和排序性能；应证明等价性或在当前几何重跑。",
    ("M05", "synthetic reference profile"): "这个标签正确，应在摘要、结果、图注和结论中保持；它不是飞行预报或可见性日程。",
    ("M13", "validate the combined"): "宽带验证不能证明窄窗重加权；应给四状态数据并验证 511 keV 附近的能量—角度响应。",
    ("M04", "not present as a narrow feature in the EXPACS continuum"): "PARMA3 原始论文报告约 0.5 MeV 的湮没小峰；必须明确证明额外窄线没有重复计数。",
    ("M23", "atmospheric paths"): "最终大气线 cut-flow 为 100% 存活；屏蔽控制结论只能用于确实被降低的分量。",
    ("M07", "most important active surface"): "应报告实际 BGO 和总载荷质量；表 4 粗算开孔前约 298 kg，气球可行性、结构和死时间代价是核心约束。",
    ("M11", "five final prompt records"): "五条记录不足以支撑当前显示精度；需增加输运，优先高权重瞬发光子，并传播联合蒙特卡洛不确定性。",
    ("S02", "preregistered"): "除非存在可引用的正式预注册，否则改为“预先指定的固定种子值”。",
    ("M11", "exact upper counting endpoint"): "逐分量区间可在给定抽样下精确，但其上端点之和不是总本底的精确联合 95% 区间；应称保守界限。",
    ("S02", "two columns answer two useful questions"): "删除元话语，直接说明两列各自采用的假设。",
    ("S02", "strongest lesson"): "这是评价性措辞；应直接陈述有引用支持的本底研究比较。",
    ("M23", "failure of anticoincidence"): "避免防御性表述；中性说明该分量在当前能量和拓扑选择下不可区分。",
    ("S01", "Scope and next steps"): "改名为“局限与下一步”，并说明每项局限如何影响标题结果。",
    ("M03", "final-geometry full chain"): "送审基线遗漏七个活化族；删除“全链条”，改为有范围限定的参考曝光估计。",
    ("J01", "Before publication"): "这是内部承诺，不是数据可用性声明；投稿时应给出现有版本化归档和持久标识符。",
    ("J01", "To be completed before journal submission"): "投稿前必须补全经费、利益冲突和作者贡献，并统一放入 Statements and Declarations。",
    ("J01", "doi:10.1103/RevModPhys.83.1001"): "按期刊要求处理作者—年份、字母排序和完整 DOI URL，并核实仅有 arXiv 条目的正式版本。",
    ("N01", "live factor remains between 0.97165 and 0.97985"): "若 τ=1 μs，此活时间范围暗示未报告的 2.0–2.9×10⁴ s⁻¹ 最终轴速率。偶然反符合损失约每微秒 2–3%，需报告屏蔽速率、定义 L 并扫描 τ。",
    ("N02", "plane-parallel slant depth"): "本处现已写明 45° 平面平行斜程柱 4.895 g cm⁻² 和 T=0.6520；本条作为已完成修订的追踪保留。",
    ("N03", "require three source layers"): "摘要承诺四个流且大气线占 26.59%，这里却只有三层、表 1 只有三项、符合轴也只有瞬发/延迟/信号；需说明第四流在哪里进入以及表 5 两列如何产生。",
    ("N04", "generated with replicated samples"): "该分配在下游适得其反：非光子族每族约 1500 s 等效曝光，光子仅约 184 s，零计数光子反而主导保守界限；需报告逐族曝光并把统计资源转向瞬发光子。",
    ("N05", "can look exactly like a source photon"): "不仅是“可能相似”：窗内单色 511 keV 光子最多留下约 0.4 keV 未计能量，不可能同时产生 50 keV 屏蔽沉积；信号和大气线的 100% 存活是结构性恒等关系。",
    ("N06", "ground-state half-lives checked"): "记录按激发态匹配，却只说明核对基态半衰期；需写明同核异能态采用独立衰变常数、迅速退激还是排除，并报告其 day-15 份额。",
    ("N07", "dedicated INTEGRAL/IBIS compact-source search"): "本处以 IBIS 已发表 2σ 上限为依据，按高斯近似得到 3σ 等效上限 2.4×10⁻⁴ ph cm⁻² s⁻¹，再乘 T=0.6520，定义唯一的载荷平面观测参考通量 1.565×10⁻⁴ ph cm⁻² s⁻¹。",
    ("N08", "Complete selection gave"): "两套模拟现均为全入射族活化；剩余差别是参考预算不含显式大气线且用于来源诊断，而最终预算包含大气线并采用另一响应链。摘要须明确这不是纯屏蔽增益。",
    ("N09", "event instances yield 1275 mixed-stream coincidences"): "数字自洽但文档不完整：只有取 T≈7000 s 才能由 2τTΣRₖRₗ 重现 1275；应给参考时长、逐流实例数、组大小分布和混合组归因规则。",
    ("N10", "condition corresponding to"): "定义 W 的物理含义、单位和 2025-08-31 数据来源，并说明八族通量对飞行期太阳条件的敏感性。",
    ("Re-M02", "kept fixed throughout the final-geometry calculation"): "2026-08-04 的数据血缘审计推翻了本条第二轮推断：低于 80 keV 的 CC HIT 沉积已完整序列化，50–80 keV 事例可被 50 keV 离线 cut 正确否决。后续不得仅凭 detector-map 的 TriggerThreshold 字段推断分析记录门。",
    ("Re-M08", "each sample interaction lengths in the same competition framework"): "第二轮细化 M08：竞争框架中的首次相互作用概率为 LD/(LD+LA)×[1−exp(−(LD+LA))]；除弱吸收极限外，经 R/(1−A) 缩放后不会化为目标 R。XOP 镶嵌反射率已含微晶吸收和镶嵌宽度，额外高斯晶面扰动可能重复计算。应以 XOP 对比晶片 R/T/A 和出射角，并给出 A_inc。",
    ("Re-M09", "single detector time axis carrying the three"): "第二轮复核 M09：“三个物理速率”对信号并不成立，信号在该轴上以约 660 倍物理速率单位重放。它只占轴速率约 0.1%，对活时间影响很小；真正需要修正的是措辞、混合组归因规则，并从本底偶然符合记账中排除信号。",
}


CURRENT_STATUS_ZH = {
    "M02": "【2026-08-04 审计更正】已由代码、原始 SIM 与生产目录闭合；不需要原生 50 keV 重跑。正文仅保留 50 keV 离线沉积能反符合的方法与硬件响应局限。",
    "M16": "【7 月 14 日状态】正文已将 420 eV FWHM 简要标为预估能量分辨率和模拟响应输入，不再把它写成由热容证明的完整系统性能。",
    "M17": "【7 月 14 日状态】正文保留单层约 49% 和六层接近 1 的原有简洁表述，仅将“探测效率”改为“相互作用效率”；同时已删除扩大天空立体角的表述。",
    "M18": "【7 月 14 日状态】第 1.1 节现仅以 IBIS 的 3σ 等效上限和 T=0.6520 定义唯一的载荷平面观测参考通量 1.565×10⁻⁴ ph cm⁻² s⁻¹；本段不再引入模拟归一化数值。",
    "M15": "【7 月 14 日状态】当前工作稿已处理“最终几何仅含中子活化”的一部分可比性问题，但屏蔽材料、源流集合、阈值和统计曝光是否同口径仍需逐项核对。",
    "N02": "【7 月 14 日状态】已按固定 45° 仰角把垂直柱改为 √2 倍斜程柱：第 15 天 T=0.652034，并用同一规则重折叠全部 81 个时间箱；本条作为已实施修改的审阅追踪保留。",
    "N07": "【7 月 14 日状态】第 1.1 节以 IBIS 的 3σ 等效上限 2.4×10⁻⁴ ph cm⁻² s⁻¹ 乘 T=0.6520，得到唯一的载荷平面观测参考通量 1.565×10⁻⁴ ph cm⁻² s⁻¹；该数值不参与模拟归一化。",
    "N08": "【7 月 14 日状态】当前摘要已明确参考数值是不同口径的瞬发加延迟来源诊断预算，不作为屏蔽增益的同口径比较；当前条目只保留核算边界问题。",
}


MISSING_FORMAL_ANCHORS = {
    "M06": "detailed line-profile measurements.",
    "M14": "This section describes the full end-to-end simulation chain from source generation to flight-performance assessment.",
    "M15": "after the different source exposures have been applied.",
    "M21": "not balloon telemetry and not a source-visibility schedule.",
    "M22": "significance accumulates rather than reporting only the endpoint.",
    "J03": "\\textbf{Ethics approval and consent to participate} Not applicable.",
}


OVERVIEW_ZH = (
    "【阅读说明】本文件以当前英文工作稿为左侧正文；每次修订后重新锚定仍有效的审阅意见，并生成对应的可见中文行动侧栏。"
    "第一轮正式条目 28 项、第二轮新增正式条目 10 项；原来没有行内锚点的 M06、M14、M15、M21、M22、J03 已补为零尺寸便笺。"
    "颜色：红色为重大问题，橙色为中等问题，蓝色为结构问题，绿色为期刊问题，紫色为第二轮新增，青色为第二轮复核。"
    "已完成全入射族活化的 M03 已从当前行动侧栏删除，其四处重复标注不再显示；M02 已在 2026-08-04 依据项目数据血缘更正并闭合，带状态的批注仅作修订追踪。"
)


SEVERITY_ZH = {
    "Major": "重大",
    "Moderate": "中等",
    "Structural": "结构",
    "Journal": "期刊",
}


COLORS = {
    "Major": "1 0.48 0.48",
    "Moderate": "1 0.78 0.36",
    "Structural": "0.48 0.72 1",
    "Journal": "0.62 0.86 0.62",
}


def tex_comment_safe(text: str) -> str:
    """Keep Unicode, but remove characters special inside a TeX argument."""
    replacements = {
        "\\": "/",
        "%": "百分比",
        "&": "和",
        "#": "第",
        "_": "-",
        "{": "（",
        "}": "）",
        "$": "",
        "~": "约",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return " ".join(text.split())


def parse_braced(text: str, start: int) -> tuple[str, int]:
    if start >= len(text) or text[start] != "{":
        raise ValueError(f"Expected '{{' at offset {start}")
    depth = 0
    i = start
    while i < len(text):
        char = text[i]
        if char == "\\":
            i += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
        i += 1
    raise ValueError(f"Unclosed brace at offset {start}")


def annotation_records(text: str):
    """Yield (start, end, options, anchor, body) for pdfmarkupcomment calls."""
    cursor = 0
    token = "\\pdfmarkupcomment["
    while True:
        start = text.find(token, cursor)
        if start < 0:
            return
        option_start = start + len(token)
        option_end = text.find("]", option_start)
        if option_end < 0:
            raise ValueError(f"Unclosed option list at offset {start}")
        anchor_start = option_end + 1
        anchor, after_anchor = parse_braced(text, anchor_start)
        body, end = parse_braced(text, after_anchor)
        yield start, end, text[option_start:option_end], anchor, body
        cursor = end


def review_body(rid: str, local_note: str, reviews_by_id: dict[str, object]) -> str:
    if rid.startswith("Re-"):
        return tex_comment_safe(f"【第二轮复核】{local_note}")
    zh = ZH_REVIEWS[rid]
    meta = reviews_by_id[rid]
    status = CURRENT_STATUS_ZH.get(rid, "")
    pieces = [
        OVERVIEW_ZH if rid == "J02" and local_note.startswith("本处标题过长") else "",
        status,
        f"【本处意见】{local_note}",
        f"【正式问题】{zh.title}",
        f"【说明】{zh.finding}",
        f"【修改要求】{zh.action}",
        f"【依据】{zh.basis}",
        f"【初始审阅定位页码】{meta.pages}",
    ]
    return tex_comment_safe(" ｜ ".join(piece for piece in pieces if piece))


def replace_markup_comments(text: str, reviews_by_id: dict[str, object]) -> tuple[str, list[str]]:
    chunks: list[str] = []
    cursor = 0
    seen: list[str] = []
    for start, end, options, anchor, _old_body in annotation_records(text):
        subject_match = re.search(r"subject=\{([^}]*)\}", options)
        if not subject_match:
            raise ValueError(f"Annotation at {start} has no subject")
        rid = subject_match.group(1).split("|")[0].strip()
        key = (rid, anchor)
        if key not in PINPOINT_ZH:
            raise KeyError(f"No Chinese pinpoint translation for {key!r}")
        local = PINPOINT_ZH[key]
        if rid.startswith("Re-"):
            subject = f"{rid}｜第二轮复核"
        else:
            zh = ZH_REVIEWS[rid]
            meta = reviews_by_id[rid]
            round_label = "第二轮新增｜" if rid.startswith("N") else ""
            subject = f"{rid}｜{round_label}{SEVERITY_ZH[meta.severity]}｜{zh.category}"
        new_options = re.sub(r"author=\{[^}]*\}", "author={中文同行审阅}", options, count=1)
        new_options = re.sub(r"subject=\{[^}]*\}", f"subject={{{tex_comment_safe(subject)}}}", new_options, count=1)
        body = review_body(rid, local, reviews_by_id)
        replacement = f"\\pdfmarkupcomment[{new_options}]{{{anchor}}}{{{body}}}"
        chunks.append(text[cursor:start])
        chunks.append(replacement)
        cursor = end
        seen.append(rid)
    chunks.append(text[cursor:])
    return "".join(chunks), seen


def sticky_note(rid: str, reviews_by_id: dict[str, object]) -> str:
    zh = ZH_REVIEWS[rid]
    meta = reviews_by_id[rid]
    subject = tex_comment_safe(f"{rid}｜{SEVERITY_ZH[meta.severity]}｜{zh.category}｜补充正式条目")
    body = review_body(rid, "原标注 PDF 没有对应的行内高亮；现补充为相关位置的侧栏便笺。", reviews_by_id)
    color = COLORS[meta.severity]
    return (
        "\\vadjust{\\smash{\\hbox to 0pt{"
        "\\pdfcomment[icon=Note,"
        f"color={{{color}}},author={{中文同行审阅}},subject={{{subject}}}]"
        f"{{{body}}}"
        "\\hss}}}"
    )


def add_missing_notes(text: str, reviews_by_id: dict[str, object]) -> tuple[str, list[str]]:
    inserted: list[str] = []
    for rid, anchor in MISSING_FORMAL_ANCHORS.items():
        if text.count(anchor) != 1:
            raise ValueError(f"Expected one insertion anchor for {rid}: {anchor!r}; found {text.count(anchor)}")
        text = text.replace(anchor, anchor + sticky_note(rid, reviews_by_id), 1)
        inserted.append(rid)
    return text, inserted


def build_report(reviews_by_id: dict[str, object]) -> str:
    lines = [
        "# EA 稿件中文同行审阅（PDF 侧栏整合版）",
        "",
        "- 审阅基线：`balloon511_ea_draft_en_peer_review_annotated.pdf`（2026-07-13，24 页）",
        "- 整合日期：2026-07-14",
        "- M02 审计更正：2026-08-04（项目内部数据血缘复核）",
        "- 用途：本 Markdown 是中文批注文本的可检索底稿；实际阅读请优先使用 `balloon511_ea_draft_en_peer_review_annotated_cn_integrated_20260714.pdf`。",
        "- 版本提醒：当前英文工作稿已在 7 月 14 日继续修订，尤其已加入全入射族活化结果。这里保留原送审基线，是为了让页码、高亮和意见一一对应。",
        "",
        "## 总体结论",
        "",
        "选题与 Experimental Astronomy 的仪器和背景建模范围契合，但送审基线尚不宜投稿。M02 的 50 keV 后处理数据链已审计闭合；当前优先处理屏蔽计数率与死时间、Laue 过程验证、四源流归一化、同口径几何比较、有限统计与似然、真实观测几何，以及版本化可复现归档。",
        "",
        "## 正式审阅条目",
        "",
    ]
    ordered_ids = [f"M{i:02d}" for i in range(1, 24)] + ["S01", "S02", "J01", "J02", "J03"] + [f"N{i:02d}" for i in range(1, 11)]
    ordered_ids = [rid for rid in ordered_ids if rid not in RESOLVED_REVIEW_IDS]
    for rid in ordered_ids:
        zh = ZH_REVIEWS[rid]
        meta = reviews_by_id[rid]
        round_label = "（第二轮新增）" if rid.startswith("N") else ""
        lines.extend(
            [
                f"### {rid}{round_label}｜{SEVERITY_ZH[meta.severity]}｜{zh.category}",
                "",
                f"- 送审基线页码：{meta.pages}",
                f"- 问题标题：{zh.title}",
                f"- 说明：{zh.finding}",
                f"- 修改要求：{zh.action}",
                f"- 依据：{zh.basis}",
            ]
        )
        if rid in CURRENT_STATUS_ZH:
            lines.append(f"- 当前状态：{CURRENT_STATUS_ZH[rid]}")
        lines.append("")
    lines.extend(
        [
            "## PDF 侧栏实现说明",
            "",
            "原 PDF 含 56 条源级高亮命令，跨行后形成 72 个 Highlight 对象。当前交付由 `inject_peer_review_cn_pdf_20260714.py` 删除已解决 M03 的全部高亮，把其余批注正文改为中文，并另加总评及无行内锚点的正式便笺；M02 批注已按 2026-08-04 数据血缘审计更正。精确对象计数记录在配套 validation JSON 中。原 121 个链接、目录/命名目标、24 页正文内容流和嵌入图件保持不变。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    defs = runpy.run_path(str(DEFINITIONS), run_name="ea_peer_review_definitions")
    all_reviews = [*defs["REVIEWS"], *defs["REVIEWS_R2"]]
    reviews_by_id = {review.rid: review for review in all_reviews}
    expected_ids = set(reviews_by_id)
    if set(ZH_REVIEWS) != expected_ids:
        missing = sorted(expected_ids - set(ZH_REVIEWS))
        extra = sorted(set(ZH_REVIEWS) - expected_ids)
        raise RuntimeError(f"Chinese formal review map mismatch; missing={missing}, extra={extra}")

    expected_pinpoints = {
        *((row[0], row[2]) for row in defs["ANNOTATIONS"]),
        *((row[0], row[3]) for row in defs["ANNOTATIONS_R2"]),
    }
    if set(PINPOINT_ZH) != expected_pinpoints:
        missing = sorted(expected_pinpoints - set(PINPOINT_ZH))
        extra = sorted(set(PINPOINT_ZH) - expected_pinpoints)
        raise RuntimeError(f"Chinese pinpoint map mismatch; missing={missing}, extra={extra}")

    source = BASE_TEX.read_text(encoding="utf-8")
    source, seen = replace_markup_comments(source, reviews_by_id)
    expected_markup_annotations = sum(
        1 for row in defs["ANNOTATIONS"] if row[0] not in RESOLVED_REVIEW_IDS
    ) + len(defs["ANNOTATIONS_R2"])
    if len(seen) != expected_markup_annotations:
        raise RuntimeError(
            f"Expected {expected_markup_annotations} existing markup annotations, "
            f"found {len(seen)}"
        )
    source, inserted = add_missing_notes(source, reviews_by_id)
    if set(inserted) != set(MISSING_FORMAL_ANCHORS):
        raise RuntimeError("Missing-note insertion mismatch")

    source = source.replace(
        "% Peer-review overlay generated 13 July 2026.",
        "% Chinese integrated peer-review sidebar generated 14 July 2026.\n% Review baseline and highlight locations remain those of 13 July 2026.",
        1,
    )
    source = source.replace(
        "% Annotation IDs map to ea_peer_review_report.html.",
        "% Every annotation now contains its full Chinese finding and requested revision.\n% Searchable Chinese source: ea_peer_review_report_cn_integrated_20260714.md.",
        1,
    )
    source = source.replace("\\hypersetup{hidelinks}", "\\hypersetup{hidelinks,unicode=true}", 1)

    OUTPUT_TEX.write_text(source, encoding="utf-8")
    OUTPUT_REPORT.write_text(build_report(reviews_by_id), encoding="utf-8")
    print(f"Wrote {OUTPUT_TEX}")
    print(f"Wrote {OUTPUT_REPORT}")
    print("Active formal review items: 37 (M03 removed; M02 retained as a closed audit correction)")
    print("Generated TeX remains a historical baseline; M02 text carries the 2026-08-04 lineage correction")


if __name__ == "__main__":
    main()
