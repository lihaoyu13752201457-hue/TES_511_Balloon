"""Publish A/B isolated signal interfaces and joint Monte Carlo uncertainty."""
from pathlib import Path
import hashlib,json,math
import numpy as np
O=Path(__file__).resolve().parents[1];F=O.parent;W=F.parents[1]
read=lambda p:json.loads(p.read_text())
write=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
cfg=read(O/'inputs_manifest.json')
models={m:read(O/'data'/f'signal_{m}_summary.json') for m in ['a','b']}
assert all(x['status']=='PASS' for x in models.values())
arrays={m:np.load(O/'data'/f'signal_{m}_catalog.npz') for m in ['a','b']}
assert np.array_equal(arrays['a']['optical_event_id'],arrays['b']['optical_event_id'])
n=cfg['n_input'];N=cfg['optical_manifest']['n_incident'];A=cfg['optical_manifest']['sampled_crystal_area_cm2'];Aopt=cfg['optical_manifest']['Aeff_opt_cm2'];sopt=cfg['optical_manifest']['Aeff_MC_SE_cm2']
y=np.array([arrays[m]['narrow_final'].astype(float) for m in ['a','b']]);eps=y.mean(axis=1)
conditional=(y@y.T/n-np.outer(eps,eps))/n
p=eps*n/N;binomial_cov=A*A*(y@y.T/N-np.outer(p,p))/N
decomp_opt=sopt*sopt*np.outer(eps,eps);decomp_det=Aopt*Aopt*conditional
cov=decomp_opt+decomp_det
# Retain the supplied optical MC SE, including its finite-sample convention.
# It differs by 4.2 ppm from the pooled binomial plug-in SE.
assert np.allclose(binomial_cov,cov,rtol=1e-4,atol=1e-12)
for i,m in enumerate(['a','b']):
    assert math.isclose(math.sqrt(binomial_cov[i,i]),models[m]['isolated_signal_count_conversion'].get('pooled_binomial_crosscheck_SE_cm2',models[m]['isolated_signal_count_conversion']['mc_standard_error_cm2']),rel_tol=1e-12)
    assert np.max(arrays[m]['true_total_keV']+arrays[m]['plastic_keV']+arrays[m]['bgo_keV'])<511.01
    models[m]['isolated_signal_count_conversion']['pooled_binomial_crosscheck_SE_cm2']=float(math.sqrt(binomial_cov[i,i]))
    models[m]['isolated_signal_count_conversion']['mc_standard_error_cm2']=float(math.sqrt(cov[i,i]))
    models[m]['uncertainty_decomposition_cm2']={'optical_MC_contribution_SE':float(math.sqrt(decomp_opt[i,i])),'conditional_detector_MC_contribution_SE':float(math.sqrt(decomp_det[i,i])),'combined_SE':float(math.sqrt(cov[i,i]))}
    for window in models[m]['retention'].values():
        for item in window.values():
            q=item['fraction'];nn=item['denominator'];z=1.959963984540054
            center=(q+z*z/(2*nn))/(1+z*z/nn);half=z*math.sqrt(q*(1-q)/nn+z*z/(4*nn*nn))/(1+z*z/nn)
            item['confidence_interval_95_wilson']=[max(0.,center-half),min(1.,center+half)]
for model in ['a','b']: write(O/'data'/f'signal_{model}_summary.json',models[model])
joint={'model_order':['a','b'],'same_optical_input_photons':True,'distinct_transport_seeds':[cfg['models'][m]['seed'] for m in ['a','b']],
       'n_input':n,'n_both_selected':int(np.sum(y[0]*y[1])),'conditional_retention_covariance':conditional.tolist(),
       'optical_area_times_retention_covariance_cm4':cov.tolist(),'shared_optical_covariance_component_cm4':decomp_opt.tolist(),'conditional_detector_covariance_component_cm4':decomp_det.tolist(),
       'correlation':float(cov[0,1]/math.sqrt(cov[0,0]*cov[1,1])),
       'formula':'C_g=A_opt*epsilon_g; Cov(C_g,C_h)=epsilon_g*epsilon_h*Var(A_opt)+A_opt^2*Cov(epsilon_g,epsilon_h). Conditional covariance=(K_both/N_fp-epsilon_g*epsilon_h)/N_fp. The supplied optical MC SE is retained.',
       'pooled_binomial_crosscheck_covariance_cm4':binomial_cov.tolist(),
       'uncertainty_scope':'Monte Carlo sampling only; no optical/geometry/calibration systematic errors. One detector transport and one noise draw per accepted focal photon and model.'}
oldbg=read(F/'a_geometry_comparison_20260920/data/summary.json')
background={m:oldbg['models'][m]['background']['narrow']['policies']['pixel_geometry'] for m in ['a','b']}
optics=read(W/'outputs/01_intro_geometry_optics/c_response_sync_20260920/optical_source_numeric_summary.json')
assert optics['total_accepted']==n
summary={'status':'PASS_ISOLATED_SIGNAL','n_optical_primaries':N,'n_focal_photons':n,'optical_area_cm2':Aopt,'optical_area_MC_SE_cm2':sopt,'models':models,'joint_uncertainty':joint,
         'optical_numeric_summary':optics,'unchanged_day15_isolated_background':background,
         'mission_time_replay_done':False,'new_background_production':False,
         'physics_runtime':{'cosima':'/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima','EM':'LivermorePol','HD':'qgsp-bic-hp'}}
summary['physics_runtime']['sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path('/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima'),Path('/home/ubuntu/MEGAlib_Install/megalib-main/lib/libCosima.so')]}
write(O/'data/summary.json',summary)
handoff={'status':'COMPUTATION_READY_PAPER_NUMERIC_SYNC_PENDING','package':str(O),'summary':str(O/'data/summary.json'),'source_manifest':str(O/'inputs_manifest.json'),
    'n_optical_primaries':N,'n_focal_photons':n,'optical_area_cm2':Aopt,'optical_area_MC_SE_cm2':sopt,'models':models,'joint_uncertainty':joint,
    'source_interface_issue':cfg['source_interface_issue'],
    'only_numeric_manuscript_edits_authorized':True,'mission_time_replay_done':False,'new_background_production':False,
    'downstream_background_entry':str(F/'a_geometry_comparison_20260920/data/summary.json'),
    'next_owner':'Fork03: combine this raw/selected signal interface with the retained background and pixel-geometry reconstruction; establish eta/mission integration. Fork04: consume Fork03 final outputs.',
    'non_numeric_issues_not_applied':[
        'The source paragraph identifies the selection radius/reference plane as the physical Be entrance; A physical Be is at local x=-20.35, while the retained reconstruction reference plane is -13.1. Rays were back-propagated to -60 for complete physical transport, with the reference phase space preserved.',
        'A prose lists the BGO condition; the retained computation applies plastic<50 keV AND BGO<50 keV. B has no plastic layer.',
        'Existing background-only signal_probe does not sample signal deposits; reusing its eta and replacing it with a signal-dependent grouping estimate are different procedures. This handoff does not claim either has been rerun.'
    ]}
for p in [O/'NUMERIC_SYNC_HANDOFF.json',F/'NUMERIC_SYNC_HANDOFF.json']:write(p,handoff)
lines=['# 新光学样本的A/B信号数值交接','', '**计算已完成，稿件数字同步进行中。** 输入为Fork01的37,175个焦面光子，两模型各输运一次；没有扩大光学样本或运行本底生产。','',
'| 模型 | 窄窗计数 | 主动通过 | 康普顿通过 | 康普顿步骤保留率 | 总信号保留率 | A_opt × ε_sig (cm²) | 合并MC标准误 (cm²) |','|---|---:|---:|---:|---:|---:|---:|---:|']
for m in ['a','b']:
    x=models[m];c=x['stage_counts']['narrow'];r=x['retention']['narrow'];z=x['isolated_signal_count_conversion']
    lines.append(f"| {m.upper()} | {c['pre_veto']} | {c['combined_active_veto']} | {c['compton_trajectory_veto']} | {100*r['compton_per_active']['fraction']:.4f}% | {100*r['total_per_focal_photon']['fraction']:.4f}% | {z['value_cm2']:.9f} | {z['mc_standard_error_cm2']:.9f} |")
lines+=['','## 统计口径','',f'光学有效面积为{Aopt:.12f}±{sopt:.12f} cm²。总信号保留率以37,175为分母，步骤保留率以进入该步骤的计数为分母。各比例及二项标准误见JSON。',
'计数换算因子为A_opt×ε_sig=A_inc×K/150000。标准误合并Fork01提供的光学MC方差与条件探测器MC方差，另用150000个初级的最终通过二项统计交叉核对；有限样本约定的微小差别保留在JSON，未沿用旧误差。误差只含MC抽样。',
f'A/B共用焦面样本而使用不同输运种子，选后换算因子的MC相关系数为{joint["correlation"]:.6f}。JSON给出2×2协方差、光学共用项与条件探测器项，几何间比较不能把两者完全独立相加。','',
'## 给Fork03的逐事件接口','',f'- [机器交接]({F}/NUMERIC_SYNC_HANDOFF.json)；[完整摘要]({O}/data/summary.json)。',
f'- 各模型`data/signal_{{a,b}}_catalog.npz`含全部37,175个事件及未阈值化的像素沉积，另有500 eV测得能量、窄/宽窗与最终布尔标志。`source_row`及`optical_event_id`在A/B一一对应。',
'- `hit_start/hit_count`定位原始像素；`hit_uid/hit_code/hit_layer`提供几何编号，`hit_energy_keV`为未加噪能量。`plastic_keV/bgo_keV`为各自主动体积原始总沉积。',
'- `signal_{a,b}_deposits.npz`和对应volumes.json保留每次TES/主动沉积的相对时间与体积。原SIM完整保留。人工EventList时刻仅用于逐个输运，不能当作任务事件到达率。',
'- 合组重放应先合并原始像素能量、累计主动沉积，再对每个组内像素施加一次响应；不要把孤立事件已经展宽的能量再展宽。重建代码保持既有九点实现，真值沉积坐标仅用于包含性审计。','',
'## 几何与源核查','',
'A/B几何及全部本地Include已逐字节冻结在geometry/；安装库材料按原路径只读并记录哈希。源卡与SIM头的几何、seed、INIT位置/方向、每条初级、37175条终止记录和gzip CRC均验证通过。',
'A的旧注入x=-13.1 cm已经在实际Be窗(-20.35 cm)、外铝滤膜(-20.92 cm)及数层薄膜之后。本次将该参考面上的每条射线回推到x=-60 cm，再穿过完整现有材料；返回参考面的坐标误差小于2×10⁻¹⁴ cm，保持方向与焦面分布。B保持x=-46 cm、z=-2.8 cm入口。原判选参考盘位置未修改。',
'因此A新旧结果差异同时包括新光学输入及源注入材料覆盖的修正，不能标成纯光学面积缩放。正文只换数字，不添加这段修改历史。','',
'## 未执行项与非数字问题','',
'未执行背景生产、偶然重合/η或任务时间积分；后者交Fork03。本底孤立九点结果沿用本路此前已经核验的记录，不能由本次信号运行推断其时间结果。',
'原文将参考面称为铍入口、A主动判据未列plastic，以及旧background-only条件探针如何接入新样本，均已在JSON单列。没有为这些问题自动更改正文词句。光学源数字采用Fork01的三种子衍射束口径，不混用孔径内分位数。']
text='\n'.join(lines)+'\n'
for p in [O/'NUMERIC_SYNC_HANDOFF_ZH.md',F/'NUMERIC_SYNC_HANDOFF_ZH.md']:p.write_text(text)
ledger=read(O/'seed_ledger.json');ledger['status']='BOTH_TRANSPORT_AND_RESPONSE_VALIDATED';write(O/'seed_ledger.json',ledger)
print(json.dumps({'status':'READY_FOR_FORK03','summary':str(O/'data/summary.json'),'selected':{m:models[m]['stage_counts']['narrow']['compton_trajectory_veto'] for m in ['a','b']},'correlation':joint['correlation']},indent=2))
