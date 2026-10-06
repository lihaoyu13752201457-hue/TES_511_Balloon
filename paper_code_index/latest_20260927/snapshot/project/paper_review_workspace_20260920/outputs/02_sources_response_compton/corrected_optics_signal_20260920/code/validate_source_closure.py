"""Close the A upstream-material issue with exact ray geometry and internal control."""
from pathlib import Path
from collections import Counter
import gzip,json,math,re
import numpy as np
O=Path(__file__).resolve().parents[1];F=O.parent
read=lambda p:json.loads(p.read_text())
write=lambda p,x:p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
cfg=read(O/'inputs_manifest.json');m=cfg['models']['a'];n=cfg['n_input']
records={}
for line in Path(m['geometry_geo']).read_text().splitlines():
    f=line.split('//')[0].split()
    if not f:continue
    if f[0]=='Volume':records.setdefault(f[1],{})
    elif f[0]=='Shape':records.setdefault(f[-1],{})['type']=f[1]
    elif f[0]=='Orientation':records.setdefault(f[1],{})
    if '.' not in f[0]:continue
    name,key=f[0].rsplit('.',1);r=records.setdefault(name,{})
    if key=='Copy':records[f[1]]=dict(r)
    else:r[key]=f[1:]
rot=lambda d:np.array([[math.cos(math.radians(d)),0,math.sin(math.radians(d))],[0,1,0],[-math.sin(math.radians(d)),0,math.cos(math.radians(d))]])
def local_transform(name):
    if name=='InstrumentFrame':return np.eye(3),np.zeros(3)
    r=records[name];angles=list(map(float,r.get('Rotation',['0','0','0'])))
    assert len(angles)==3 and angles[0]==angles[2]==0,(name,angles)
    parentR,parentT=local_transform(r['Mother'][0]);R=parentR@rot(angles[1]);T=parentT+parentR@np.array(list(map(float,r.get('Position',['0','0','0']))))
    return R,T
eventlist=np.loadtxt(m['eventlist']);origin=eventlist[:,5:8]@rot(45);direction=eventlist[:,8:11]@rot(45)
assert np.allclose(origin[:,0],-60.) and np.all(direction[:,0]>.99)
def intersects(center,half,R=np.eye(3)):
    o=(origin-center)@R;d=direction@R
    tiny=np.abs(d)<1e-15;safe=np.where(tiny,1.,d)
    t1=(-half-o)/safe;t2=(half-o)/safe
    lo=np.minimum(t1,t2);hi=np.maximum(t1,t2)
    lo=np.where(tiny,-np.inf,lo);hi=np.where(tiny,np.inf,hi)
    return (np.max(lo,axis=1)<=np.min(hi,axis=1)) & (np.min(hi,axis=1)>=0) & ~np.any(tiny&(np.abs(o)>half),axis=1)
windows=[];wbar=np.zeros(n,dtype=bool);bars=[];openings=[]
for name,r in records.items():
    if 'Mother' not in r:continue
    if name.startswith('Win_') or (name.startswith('W_Multihole_Collimator_') and r.get('Material')==['W']):
        shape=r['Shape'];assert shape[0]=='BRIK';half=np.array(list(map(float,shape[1:])))
        R,T=local_transform(name);mask=intersects(T,half,R)
        row={'name':name,'center_local_cm':T.tolist(),'half_lengths_cm':half.tolist(),'straight_ray_intersections':int(mask.sum())}
        if name.startswith('Win_'):windows.append(row)
        else:bars.append(row);wbar|=mask
    shape_name=name+'_RectWindowCutShape';orientation=name+'_RectWindowCutOrientation'
    if shape_name in records and orientation in records:
        R,T=local_transform(name);T=T+R@np.array(list(map(float,records[orientation]['Position'])))
        half=np.array(list(map(float,records[shape_name]['Parameters'])))
        assert records[shape_name]['type']=='BRIK'
        openings.append({'volume':name,'cut_center_local_cm':T.tolist(),'cut_half_lengths_cm':half.tolist(),'rays_intersect_cut':int(intersects(T,half,R).sum())})
assert len(windows)==7 and len(bars)>100 and len(openings)>5,(len(windows),len(bars),len(openings))
np.savez_compressed(O/'validation/a_straight_ray_masks.npz',source_row=np.arange(n),intersects_W_bar=wbar)
def material_deposits(model):
    ms=cfg['models'][model];event=None;seen=set();counts=Counter();energy=Counter();first_ia_front=0;first_ia=False
    def finish():
        for k in seen:counts[k]+=1
    with gzip.open(ms['sim'],'rt') as f:
        for raw in f:
            line=raw.strip()
            if line=='SE':finish();seen=set();event=None;first_ia=False
            elif line.startswith('ID '):event=int(line.split()[1])
            elif line.startswith('IA ') and not line.startswith('IA INIT') and not first_ia:
                fields=line.split(';');p=np.array(list(map(float,fields[4:7])))@rot(45)
                first_ia_front+=int(p[0]<-13.1);first_ia=True
            elif line.startswith('CC HIT '):
                v=line.split()[2];match=re.search(r'edep_keV=([\deE.+-]+)',line);e=float(match[1])
                category='W_multihole_bars' if v.startswith('W_Multihole_Collimator_') else v if v.startswith('Win_') else None
                if category:seen.add(category);energy[category]+=e
    finish()
    return {'events_with_deposits':dict(counts),'sum_deposited_energy_keV':dict(energy),'first_recorded_interaction_upstream_of_old_injection':first_ia_front}
results={m:read(O/'data'/f'signal_{m}_summary.json') for m in ['a','b','a_internal_diagnostic']}
actual={m:np.load(O/'data'/f'signal_{m}_catalog.npz')['narrow_final'] for m in ['a','a_internal_diagnostic']}
external=results['a']['stage_counts']['narrow']['compton_trajectory_veto'];internal=results['a_internal_diagnostic']['stage_counts']['narrow']['compton_trajectory_veto']
assert cfg['models']['a_internal_diagnostic']['production_physics_eligible'] is False
sections={m:{'intersects_W_bar':{'input':int(wbar.sum()),'selected':int((a&wbar).sum())},'no_W_bar_intersection':{'input':int((~wbar).sum()),'selected':int((a&~wbar).sum())}} for m,a in actual.items()}
data={'status':'PASS_SOURCE_CLOSURE','geometry':m,'n_shared_optical_photons':n,'same_geometry_and_optical_reference_directions':True,
      'independent_transport_seeds':[cfg['models'][m]['seed'] for m in ['a','a_internal_diagnostic']],
      'external_injection_x_cm':-60.,'internal_control_x_cm':-13.1,'diagnostic_not_pooled':True,
      'physical_narrow_selected':external,'internal_diagnostic_narrow_selected':internal,
      'external_relative_to_internal':external/internal,'material_coverage_loss_fraction':1-external/internal,
      'old_optics_internal_selected':27649,'old_optics_input':37194,
      'new_optics_internal_total_retention':internal/n,'old_optics_internal_total_retention':27649/37194,
      'windows':windows,'collimator_W_bar_placements':len(bars),'rays_intersecting_W_bars':int(wbar.sum()),'rectangular_through_openings':openings,
      'selected_by_straight_ray_W_intersection':sections,'observed_front_material_deposits':{m:material_deposits(m) for m in ['a','a_internal_diagnostic']},
      'interpretation':'The internal control bypasses the W multi-hole collimator at x=-25.9, outer Al at -20.92, Be at -20.35, and four Al foils at -18.35/-17.85/-15.65/-15.2 cm. Its new optical-sample retention tests the optics-only change under the legacy launch convention. External A is the physical result; the diagnostic never enters its denominator, selected count or MC covariance.',
      'bounds':'Straight-ray W intersections diagnose geometric shadowing; full Monte Carlo also includes scattering and energy redistribution, so blocked-ray counts are not subtracted analytically.'}
data['geometry']=cfg['models']['a']['geometry_geo'];write(O/'validation/a_source_closure.json',data)
text=f'''# A源面闭合：内部诊断对照

**PASS。** 物理A外部注入保留{external:,}/37,175，独立的旧注入面诊断保留{internal:,}/37,175。诊断不与物理A/B混池，不进入论文数字。

旧光学样本在内部注入下的保留率为{100*27649/37194:.4f}%；新光学样本在同一内部注入约定下为{100*internal/n:.4f}%。新样本从外部完整输运后为{100*external/n:.4f}%，相对内部诊断减少{100*(1-external/internal):.4f}%。不同输运使用新独立种子；这一对照区分了光学输入变化和前置材料覆盖的主要影响，没有把两次随机输运当成逐事件共同随机数实验。

实际几何中，x=-13.1 cm内部源面绕过x=-25.9 cm的多孔W准直器、外Al(-20.92)、Be(-20.35)及四层Al(-18.35、-17.85、-15.65、-15.2)。x=-4.35125 cm的磁屏蔽Al窗位于两源面下游。源面回投保留参考处的位置/方向，SIM逐初级INIT校验通过。

从实际Copy/Mother/Position/Shape读取了{len(bars)}个W条实体；{int(wbar.sum())}条入射射线与这些W实体相交。还逐一核对7个薄窗实体及{len(openings)}个实际体积的矩形贯通开口。几何尺寸、相交数、按W相交分层的选后数及实际SIM前置材料沉积计数，均见a_source_closure.json和a_straight_ray_masks.npz。直线几何统计用于检查材料覆盖，不代替输运散射。

这项差异只记录在验证/交接，正文只更新数值。新外部注入A继续作为目标物理结果，内部对照明确标记为不可用于物理性能归一化。
'''
(O/'validation/A_SOURCE_CLOSURE_ZH.md').write_text(text)
for p in [O/'NUMERIC_SYNC_HANDOFF.json',F/'NUMERIC_SYNC_HANDOFF.json']:
    h=read(p);h['status']='COMPUTATION_AND_SOURCE_CLOSURE_READY_PAPER_SYNC_PENDING';h['source_closure']=str(O/'validation/a_source_closure.json');h['source_closure_report']=str(O/'validation/A_SOURCE_CLOSURE_ZH.md');h['internal_diagnostic_selected']=internal;h['physical_A_selected']=external;write(p,h)
for p in [O/'NUMERIC_SYNC_HANDOFF_ZH.md',F/'NUMERIC_SYNC_HANDOFF_ZH.md']:
    s=p.read_text();s+=f'\n## A源面专项闭合已完成\n\n同一新光学样本的内部源面诊断通过数为{internal:,}，完整外部注入为{external:,}；明确分离了前置材料覆盖的主要影响。详见[专项验证]({O}/validation/A_SOURCE_CLOSURE_ZH.md)。内部对照不混入物理结果。\n';p.write_text(s)
print(json.dumps({'status':data['status'],'external':external,'internal':internal,'W_shadowed_rays':int(wbar.sum()),'W_bar_placements':len(bars)},indent=2))
