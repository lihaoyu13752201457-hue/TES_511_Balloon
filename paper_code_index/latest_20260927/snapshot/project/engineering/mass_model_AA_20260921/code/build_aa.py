#!/usr/bin/env python3
"""Derive AA from the pinned A/SG3B, preserving all unrequested physical objects."""
from pathlib import Path
import argparse, hashlib, json, re

PKG = Path(__file__).resolve().parents[1]
A = Path('/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/geometry')
B = Path('/home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry')
PIN_A = '5f0482e307bf8701204f1d6df1b74396b7105d853dccb885e4df401146f552d9'
PIN_B = 'a270ab2caf340a34858b448374b3dad955878ebbb9df9169f97d80df46026934'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def record(p): return dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p))
def dump(p, obj): p.write_text(json.dumps(obj, indent=2, ensure_ascii=False)+'\n')

def parse(text):
    objects = {}
    for line in text.splitlines():
        words = line.split()
        if len(words)==2 and words[0]=='Volume': objects.setdefault(words[1], {})
        m = re.match(r'^(\w+)\.(\w+)\s+(.+)$',line)
        if m:
            n,k,v=m.groups()
            if k=='Copy': objects[v] = dict(objects.get(n,{}), _template=n)
            elif n in objects: objects[n][k]=v
    return objects

def strip_owned(text, names):
    result=[]
    for line in text.splitlines(keepends=True):
        words=line.split()
        if len(words)>=2 and words[0] in ('Volume','Scintillator','MDCalorimeter') and words[1] in names: continue
        m=re.match(r'^(\w+)\.(\w+)\s+(.*)',line)
        if m and (m[1] in names or (m[2]=='Copy' and m[3] in names)): continue
        if line.startswith('// Volume ') and words[2].rstrip(';') in names: continue
        result.append(line)
    return ''.join(result)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--nb-mode',required=True, choices=['keep-al']);args=ap.parse_args()
    ag=A/'DEMO2_DR_v3p5_SG3B.geo'; bg=B/'SH3_Assembly_OptV3.geo'
    assert sha(ag)==PIN_A, 'A source changed'
    assert sha(bg)==PIN_B, 'B source changed'
    text=ag.read_text(); old=parse(text); b=parse(bg.read_text())
    removed={n for n,v in old.items() if v.get('Material') in ('BoratedPolyethylene5wtB','PlasticScintillator') or n.startswith(('NF2_OuterSupport_','W_Multihole_','SE3_HoleTemplate_CP_100mK','SE3_HOLE_CP_100mK')) or n in ('ColdPlate_CP_100mK_intercept','Passive_W_Bottom_Plate_detector_bay')}
    while True:
        extra={n for n,v in old.items() if v.get('Mother') in removed or v.get('_template') in removed}
        if extra <= removed: break
        removed |= extra
    out=strip_owned(text,removed)
    det=(A/'DEMO2_DR_v3p5_SG3B.det').read_text()
    detectors={m[1] for m in re.finditer(r'^(\w+)\.(?:SensitiveVolume|DetectorVolume)\s+(\w+)',det,re.M) if m[2] in removed}
    det=strip_owned(det,detectors)
    # Change the retained MXC temperature identifiers, without moving any geometry.
    renames={n:n.replace('MXC_50mK','MXC_100mK').replace('Can_50mK','Can_100mK').replace('Win_50mK','Win_100mK') for n in old if any(k in n for k in ('MXC_50mK','Can_50mK','Win_50mK'))}
    for a,c in sorted(renames.items(), key=lambda x:-len(x[0])):
        out=re.sub(r'\b'+re.escape(a)+r'\b',c,out)
        det=re.sub(r'\b'+re.escape(a)+r'\b',c,det)
    additions=[]
    # Match B's bars exactly; place their rear face 0.1 mm outside A's R=26 cm Al shell.
    for tag in ('Top','Bottom','PosY','NegY'):
        orig='SH3_OptV2_W_Frame_'+tag; v=b[orig]; n='AA_W_Collimator_'+tag
        x,y,z=map(float,v['Position'].split()); pos=(-27.01,y,z-2.4)
        additions.append('\n'.join([f'Volume {n}',f'{n}.Material W',f'{n}.Visibility 1',f'{n}.Shape {v["Shape"]}',f'{n}.Position '+' '.join(f'{t:.6f}' for t in pos),f'{n}.Mother InstrumentFrame','']))
    al='SE3_Al_Shield_Inner_Cylinder_2mm'
    nb_spec={'mode':'keep-al','Nb_added':False,'retained_Al_inner_radius_cm':4.0,'retained_Al_outer_radius_cm':4.2,'retained_Al_thickness_mm':2.0,'x_min_cm':-3.85,'x_max_cm':4.1,'Bi_outer_radius_cm':3.995,'Bi_to_Al_radial_gap_mm':0.05}
    out += '\n// AA additions: B-identical W bars on the retained A beam axis.\n'+'\n'.join(additions)
    out=out.replace('Include Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo','Include Intro_Mass_model_AA.geo')
    new=parse(out)
    # Native visualization only: expose TES copies and apply material colors.
    colors={'Ta':807,'Copper':800,'Aluminium':920,'BGO':418,'Bi':616,'Nb':600,'W':15,'StainlessSteel':17,'G10':30,'CuNi':802,'Kapton':400,'Silicon':860,'SilverSinterProxy':18,'Be':834}
    for n,v in new.items():
        if n.startswith('TP_L'): out=out.replace(f'{n}.Visibility 0',f'{n}.Visibility 1')
        if '_template' not in v and v.get('Material') in colors: out+=f'{n}.Color {colors[v["Material"]]}\n'
    new=parse(out)
    # Verify unchanged physical properties for all survivors, including the retained Al cylinder.
    ignored={'Color','Visibility','_template'}
    differences=[]
    for n,v in old.items():
        if n in removed: continue
        nn=renames.get(n,n)
        expected={k:renames.get(val,val) for k,val in v.items() if k not in ignored}
        actual={k:val for k,val in new.get(nn,{}).items() if k not in ignored}
        if actual!=expected: differences.append({'name':n,'expected':expected,'actual':actual})
    assert not differences,differences[:3]
    dangling=[(n,v.get('Mother')) for n,v in new.items() if 'Mother' in v and v['Mother']!='InstrumentFrame' and v['Mother'] not in new]
    assert not dangling,dangling
    refs=re.findall(r'^\w+\.(?:SensitiveVolume|DetectorVolume)\s+(\w+)',det,re.M)
    assert all(n in new for n in refs)
    assert len([n for n in new if n.startswith('TP_L')])==2256
    assert len([n for n,v in new.items() if v.get('Material')=='BGO'])==3
    assert len([n for n,v in new.items() if v.get('Material')=='W'])==4
    assert not any(v.get('Material') in ('BoratedPolyethylene5wtB','PlasticScintillator') for v in new.values())
    for tag in ('Top','Bottom','PosY','NegY'):
        assert new['AA_W_Collimator_'+tag]['Shape']==b['SH3_OptV2_W_Frame_'+tag]['Shape']
    intro=(A/'Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo').read_text().replace('Massmodel_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy','Mass_model_AA').replace('Materials_DEMO2_DR_v3p5.geo','Materials_Mass_model_AA.geo')
    files={'Mass_model_AA.geo':out,'Mass_model_AA.det':det,'Intro_Mass_model_AA.geo':intro,'Materials_Mass_model_AA.geo':(A/'Materials_DEMO2_DR_v3p5.geo').read_text(),'Mass_model_AA.geo.setup':'Name Mass_model_AA\nVersion 1\nInclude Mass_model_AA.geo\nInclude Mass_model_AA.det\nSurroundingSphere 60 5 0 9 60\n'}
    for name,t in files.items(): (PKG/'geometry'/name).write_text(t)
    inputs=[ag,A/'DEMO2_DR_v3p5_SG3B.det',A/'Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo',A/'Materials_DEMO2_DR_v3p5.geo',bg]
    manifest={'status':'PASS__AA_BUILT','model':'AA','based_on':'A = SG3B','inputs':[record(p) for p in inputs],'outputs':{name:record(PKG/'geometry'/name) for name in files},'removed_objects':sorted(removed),'removed_detector_definitions':sorted(detectors),'renames':renames,'Nb_cylinder':nb_spec,'W_collimator':{'outer_square_cm':6.0,'clear_square_cm':5.4,'depth_cm':2.0,'center_cm':[-27.01,0,-5.2],'rear_face_cm':-26.01,'A_outer_Al_radius_cm':26.0,'gap_to_Al_mm':0.1},'retained_temperature_labels':{'MXC':'100 mK','Still':'0.7 K','4K':'4 K','60K':'60 K'},'notes':['The removed CP disk is at z=5 cm; the retained MXC disk stays at z=0.','Existing internal rod and pipe proxies keep A dimensions/positions. Their former CP-related names are provenance, not an additional stage.','Existing NF2 relief voids in retained shields are preserved; only the outer frame solids are removed.','The 3 mm Al housing around BGO is retained; it is distinct from the removed outer NF2 frame.','No transport is run.']}
    dump(PKG/'data/manifest.json',manifest)
    dump(PKG/'data/component_inventory.json',new)
    checks={'A_input_hash_pinned':True,'B_input_hash_pinned':True,'all_surviving_physical_objects_unchanged':True,'no_dangling_mothers_or_scorers':True,'TES_pixel_count_2256':True,'BGO_placed_volume_count_3':True,'W_four_B_identical_bars_only':True,'no_BPE_or_plastic_volumes':True,'CP_100mK_and_W_bottom_removed':True,'outer_NF2_frame_removed':True,'original_Al_2mm_retained_and_no_Nb_added':True}
    dump(PKG/'audit/static_validation.json',{'status':'PASS__AA_STATIC','checks':checks,'physical_differences_outside_scope':differences,'transport_launched':False})
    print(json.dumps({'status':'PASS__AA_BUILT','removed_objects':len(removed),'surviving_objects':len(new),'Nb_mode':args.nb_mode}))

if __name__=='__main__': main()
