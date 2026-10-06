"""Human-readable review package; never writes a manuscript file."""
from common import *

old = read(ORIGINAL/'data/RESULTS.json')
new = read(O/'data/RESULTS.json')
ov = read(ORIGINAL/'data/paper_values_500.json')
nv = read(O/'data/paper_values_corrected_current_sample.json')
lines = ['# 两构型活化重算及待审核修改', '',
         'AA 数据盘已恢复；两构型的现有输运样本重筛选、五个时间点的三路泊松叠加和 81 节点积分均已完成。论文、原始数据和原模拟安装未修改。', '',
         '**以下是现有样本和原核库下的修正结果。缺少响应的子体，以及旧核库中确认异常的 EC 衰变，尚未补齐；不能把本表称为全部物理问题修复后的最终投稿数值。**', '',
         '## 1. 主要数值前后对比', '',
         '| 量 | Under-stage 原值 → 重算值 | Lateral-chimney 原值 → 重算值 |',
         '|---|---:|---:|']
quantities = [
    ('日 15 延迟本底记录/组数', lambda v,r: v['compton_trajectory_veto']['delayed']['n'], '.0f'),
    ('日 15 延迟本底率 / s⁻¹', lambda v,r: v['compton_trajectory_veto']['delayed']['rate'], '.7f'),
    ('日 15 总本底率 / s⁻¹', lambda v,r: v['compton_trajectory_veto']['total']['rate'], '.7f'),
    ('延迟本底样本统计误差 / s⁻¹', lambda v,r: v['compton_trajectory_veto']['delayed']['sigma'], '.7f'),
    ('延迟本底有效样本数', lambda v,r: v['compton_trajectory_veto']['delayed']['neff'], '.2f'),
    ('20 d 本底计数', lambda v,r: r['mission_20day']['Nb'], '.2f'),
    ('20 d 信号计数', lambda v,r: r['mission_20day']['Ns'], '.2f'),
    ('20 d 计数显著性', lambda v,r: r['mission_20day']['Z'], '.3f'),
    ('20 d、3σ 通量阈值 / (10⁻⁵ ph cm⁻² s⁻¹)', lambda v,r: r['mission_20day']['F3']*1e5, '.4f'),
    ('上述通量阈值的样本统计误差 / 10⁻⁵', lambda v,r: r['mission_20day']['F3_MC_SE_approx']*1e5, '.4f'),
    ('达到 3σ 的时间 / d', lambda v,r: r['mission_20day']['T3_days'], '.3f'),
    ('达到 5σ 的时间 / d', lambda v,r: r['mission_20day']['T5_days'], '.3f'),
]
for title, getter, fmt in quantities:
    values = []
    for model in ['a', 'b']:
        values.append(f'{getter(ov[model],old["models"][model]):{fmt}} → {getter(nv[model],new["models"][model]):{fmt}}')
    lines.append('| '+title+' | '+' | '.join(values)+' |')
ratio_old = ov['a']['compton_trajectory_veto']['delayed']['rate']/ov['b']['compton_trajectory_veto']['delayed']['rate']
ratio_new = nv['a']['compton_trajectory_veto']['delayed']['rate']/nv['b']['compton_trajectory_veto']['delayed']['rate']
total_old = ov['a']['compton_trajectory_veto']['total']['rate']/ov['b']['compton_trajectory_veto']['total']['rate']
total_new = nv['a']['compton_trajectory_veto']['total']['rate']/nv['b']['compton_trajectory_veto']['total']['rate']
lines += ['', f'日 15 延迟本底的降低倍数：**{ratio_old:.3f} → {ratio_new:.3f}**；总本底的降低倍数：**{total_old:.3f} → {total_new:.3f}**；20 d 通量阈值的改善倍数：**{old["ratios"]["F3_under_over_lateral"]:.3f} → {new["ratios"]["F3_under_over_lateral"]:.3f}**。三个指标分别描述不同量。', '',
          '在当前样本计算中，“侧置构型约改善两倍灵敏度”的结论仍成立；这是当前样本的数值比较，不是未抽样分量无影响的证明。', '',
          'AA 原选中 404 条记录均保留，1371 个可能合并后新增入选的候选组中没有新增入选。侧置构型的 116 条旧记录中，3 条因合并后能量/BGO 改变被排除，另有 2 个合并组新入选，得到 115 组。', '',
          '## 2. 来源比例也需同步更新', '',
          '| 比例 | Under-stage 原值 → 重算值 | Lateral-chimney 原值 → 重算值 |',
          '|---|---:|---:|']
for title, getter in [
    ('铜材料占延迟本底', lambda v: v['origin_statistics']['materials']['Copper']['share']),
    ('TES 铜支撑板与热沉环合计', lambda v: sum(v['origin_statistics']['components'][k]['share'] for k in ['tes_substrate_cu_panels','tes_cu_heat_sink'])),
    ('MXC 铜冷盘', lambda v: v['origin_statistics']['components']['mxc_50mk_cu_plate']['share']),
    ('DR/MXC 与分级冷盘空间区域', lambda v: v['origin_statistics']['regions']['DR/MXC and cold plates']['share']),
    ('质子起始粒子', lambda v: v['origin_statistics']['families']['p']['share']),
]:
    values = [f'{getter(ov[m])*100:.2f}% → {getter(nv[m])*100:.2f}%' for m in ['a','b']]
    lines.append('| '+title+' | '+' | '.join(values)+' |')
lines += ['',
          '核素图需区分“最初生产的母核”与“实际衰变核素”。侧置构型现在有 4 个最终选中组来自后续子体；实际衰变核素分别包括 Pm-141、Cu-62 和 Ho-156。空间来源仍归于各自的原产生位置，不能把产生位置随核素名称更换。', '',
          '侧置构型的一条 Ho-156 记录贡献现有样本延迟率的 15.85%；其来源位于 W 结构。因此 W 来源比例上升、有效样本数下降，但这一排序受单条记录支配，不宜据此立即提出新的确定性结构结论。', '',
          '完整筛选表、来源材料/部件/粒子族/核素分解和任务积分前后值见 `data/NUMERIC_COMPARISON_TWO_MODELS.csv`；新来源表同时保留初始母核和实际衰变核素两个字段。', '',
          '## 3. 已确认需要修正的实现', '',
          '1. 原始追加子体事件参与了初级源活动的统一记录数分母，造成归一化偏差。应按真实抽样过程及各核态的抽样曝光赋权。',
          '2. 子体不能沿用初始母核的单一活度时间曲线。需要包含母核馈入的生成—衰变演化。',
          '3. 同一链内、间隔不超过 1 μs 的相关记录应先合并原始像素沉积，再作能窗、BGO 和连续康普顿筛选。', '',
          '时间叠加仍使用实际信号、瞬时本底、延迟本底三路泊松事例；保持 500 eV 单像素响应、1 μs 窗、无塑料闪烁体、像素几何顶点和信号 spot 判定。', '',
          '## 4. 尚不能仅靠旧样本消除的问题', '',
          '- 零样本子体分量需要其对应位置与核态的探测器响应。已有核态、能量、材料清单已定位范围；源活度不是选后背景率。',
          '- W-176 与本轮补查的 Er-158 在旧核库中被作为低于正电子阈值的 BetaPlus 通道处理，实际调用各 32768 次均无有效衰变产物；NUBASE2020 将二者列为 EC=100%。仅重赋权无法生成缺失的辐射和后续响应。',
          '- 对照 CERN 官方数据包：RadioactiveDecay 6.1.2 的 Er-158 已改为分壳层 EC；W-176 文件仍列 BetaPlus。该对照只用于核查，未安装或混入本次结果，不能假定换一个数据包就全部解决。', '',
          '这些已具体定位的问题会影响“完整最终结果”的可证明范围。当前两构型重算已完成，但补齐缺失响应仍需另行定向衰变输运；没有必要重跑原始全部大气粒子生产。', '',
          '## 5. 文字审核入口', '',
          '`WORDING_PROPOSAL_ZH.md` 给出方法原文与拟改文案的中英文；`WORDING_RESULTS_ZH.md` 给出对应结果段的中英文前后对照。所有文案仅供审核，未写入论文。', '',
          '官方核数据出处：[Geant4 数据说明](https://geant4.web.cern.ch/download/data_files_citations)。所取两个官方数据包的 URL、校验值及对照文件保存在 `data/reference_rdm_5_1/` 和 `data/reference_rdm_6_1_2/`。']
(O/'TWO_MODEL_RESULTS_REVIEW_ZH.md').write_text('\n'.join(lines)+'\n')
print('Wrote TWO_MODEL_RESULTS_REVIEW_ZH.md')
