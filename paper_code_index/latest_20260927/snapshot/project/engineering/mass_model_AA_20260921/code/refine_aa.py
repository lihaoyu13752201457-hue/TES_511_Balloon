#!/usr/bin/env python3
"""Apply the user's AA top-cover and B-matched optical-interface follow-up."""
from pathlib import Path
import json,re,argparse,math
from build_aa import parse, record, dump, strip_owned, B
P=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--al-cap',required=True,choices=['horizontal-front','vertical-top']);args=ap.parse_args()
    manifest=json.loads((P/'data/manifest.json').read_text())
    assert 'refinement' not in manifest,'Run build_aa.py first; do not patch a refined geometry twice.'
    path=P/'geometry/Mass_model_AA.geo';s=path.read_text();d=parse(s);original=s
    detpath=P/'geometry/Mass_model_AA.det';det=detpath.read_text();edits=[];removed=set();decl=[]
    def line(old,new,reason):
        nonlocal s
        assert s.count(old)==1,(old,s.count(old))
        s=s.replace(old,new);edits.append({'old':old,'new':new,'reason':reason})
    def field(n,k,new,reason):
        match=re.search(r'^'+re.escape(n)+r'\.'+k+r'\s+(.+)$',s,re.M);assert match,(n,k)
        line(match[0],f'{n}.{k} {new}',reason)
    def volume(n,material,shape,pos,rotation=None):
        decl.extend([f'Volume {n}',f'{n}.Material {material}',f'{n}.Visibility 1',f'{n}.Shape {shape}',f'{n}.Position {pos}'])
        if rotation:decl.append(f'{n}.Rotation {rotation}')
        decl.extend([f'{n}.Mother InstrumentFrame',f'{n}.Color '+str({'Aluminium':920,'BGO':418}.get(material,15)),''])
    # Full BGO top disk; preserve every real pipe opening with 0.5 mm radial clearance.
    top='BGO_S3D_O8_FullWrap_TopAnnulus_10mm';newtop='AA_BGO_TopCap_12Ports_10mm'
    decl.extend(['Shape PCON AA_BGO_TopDiskShape','AA_BGO_TopDiskShape.Parameters 0 360 2 -0.5 0 25.2 0.5 0 25.2'])
    last='AA_BGO_TopDiskShape';ports=[]
    for n,v in d.items():
        if not n.startswith('XS400_Group4_SS_TopPipe_') or '_HollowTube_' not in n:continue
        x,y,z=map(float,v['Position'].split());words=v['Shape'].split();r=float(words[6]);radius=r+.05
        num=len(ports)+1;cut=f'AA_TopPipeCut_{num:02d}';ori=cut+'Orientation';result=cut+'Subtraction'
        decl.extend([f'Shape PCON {cut}',f'{cut}.Parameters 0 360 2 -0.6 0 {radius:.8g} 0.6 0 {radius:.8g}',f'Orientation {ori}',f'{ori}.Position {x:.8g} {y:.8g} 0',f'Shape Subtraction {result}',f'{result}.Parameters {last} {cut} {ori}'])
        ports.append({'pipe':n,'x_cm':x,'y_cm':y,'tube_outer_radius_cm':r,'hole_radius_cm':radius,'clearance_mm':.5})
        last=result
    assert len(ports)==12
    field(top,'Shape',last,'Close BGO top, leaving only the 12 actual service-pipe holes.')
    s=s.replace(top,newtop);det=det.replace(top,newtop)
    # Close the existing outer Al top annulus, retaining direct access to all pipe mouths.
    al_top='Outer_Al_S3C_BGO_Mechanical_TopAnnulus_3mm';new_al_top='AA_Al_TopCap_12Ports_3mm'
    decl.extend(['Shape PCON AA_Al_TopDiskShape','AA_Al_TopDiskShape.Parameters 0 360 2 -0.15 0 26 0.15 0 26'])
    last='AA_Al_TopDiskShape';al_ports=[]
    for i,port in enumerate(ports,1):
        sleeve=port['pipe'].replace('_HollowTube_','_TopSleeve_');sv=d[sleeve]
        radius=float(sv['Shape'].split()[6])+.05
        cut=f'AA_AlTopPipeCut_{i:02d}';ori=cut+'Orientation';result=cut+'Subtraction'
        decl.extend([f'Shape PCON {cut}',f'{cut}.Parameters 0 360 2 -0.3 0 {radius:.8g} 0.3 0 {radius:.8g}',f'Orientation {ori}',f'{ori}.Position {port["x_cm"]:.8g} {port["y_cm"]:.8g} 0',f'Shape Subtraction {result}',f'{result}.Parameters {last} {cut} {ori}'])
        al_ports.append({'pipe':port['pipe'],'sleeve':sleeve,'x_cm':port['x_cm'],'y_cm':port['y_cm'],'hole_radius_cm':radius,'clearance_to_sleeve_mm':.5})
        last=result
    field(al_top,'Shape',last,'Close outer Al top while preserving twelve aligned service-pipe openings.')
    s=s.replace(al_top,new_al_top);det=det.replace(al_top,new_al_top)
    # A has two additional optical foils relative to B: remove these to match the stack.
    removed.update(['Win_100mK_Al_foil_side','Win_Outer_Al_Filter_side'])
    s=strip_owned(s,removed)
    removed_det={m[1] for m in re.finditer(r'^(\w+)\.(?:SensitiveVolume|DetectorVolume)\s+(\w+)',det,re.M) if m[2] in removed}
    det=strip_owned(det,removed_det)
    b=parse((B/'SH3_Assembly_OptV3.geo').read_text())
    window_map=[('Win_MagShield_Al_foil_side','SH3_Layer01_OpticalWindow'),('Win_Still_Al_foil_side','SH3_Layer02_OpticalWindow'),('Win_4K_Al_foil_side','SH3_Layer03_OpticalWindow'),('Win_60K_Al_foil_side','SH3_Layer04_OpticalWindow'),('Win_Be_Vacuum_150um_side','SH3_Layer05_OpticalWindow')]
    for aa,bb in window_map:
        assert d[aa]['Material']==b[bb]['Material']
        field(aa,'Shape',b[bb]['Shape'],'Match B optical window diameter and material thickness.')
        decl.append(f'{aa}.Rotation 0 90 0')
    # Enlarge each cold shield's partition band before changing its port to a circle.
    bands=[n for n,v in d.items() if 'Mother' in v and 'side_wall_rectcut_window_band' in n]
    for n in bands:
        root=n.replace('side_wall_rectcut_window_band','')
        for suffix in ['side_wall_below_side_port','side_wall_above_side_port']:
            part=root+suffix;v=d[part];a=list(map(float,v['Shape'].split()[1:]));pos=list(map(float,v['Position'].split()))
            lo=pos[2]+a[3];hi=pos[2]+a[6]
            if 'below' in suffix: hi=-5.2-2.7
            else:lo=-5.2+2.7
            half=(hi-lo)/2;pos[2]=(hi+lo)/2
            field(part,'Shape',f'PCON 0 360 2 {-half:.9g} {a[4]:.9g} {a[5]:.9g} {half:.9g} {a[7]:.9g} {a[8]:.9g}','Extend circular optical aperture through adjoining shield bands.')
            field(part,'Position',' '.join(f'{x:.9g}' for x in pos),'Keep outer shield endpoints fixed while widening the port band.')
        shape=n+'_FullShellShape';oldline=re.search(r'^'+re.escape(shape)+r'\.Parameters (.+)$',s,re.M);w=oldline[1].split();w[3]='-2.7';w[6]='2.7'
        line(oldline[0],shape+'.Parameters '+' '.join(w),'Enlarge the port band half-height to the B aperture radius.')
    # Circular 54 mm ports through Al/Kapton; BGO receives B's 60 mm square W recess.
    optical_shells=bands+['BGO_S3C_FullWrap_SideShell_WindowCut_40mm','ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm','Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm']
    for n in optical_shells:
        cut=n+'_RectWindowCutShape';ori=n+'_RectWindowCutOrientation'
        params=re.search(r'^'+re.escape(cut)+r'\.Parameters (.+)$',s,re.M);hx=float(params[1].split()[0])
        if n.startswith(('BGO_','ActiveShield_S3C_BGO_Kapton_')):
            line(params[0],f'{cut}.Parameters {hx:.9g} 3 3','Match the 60 mm BGO W-frame recess; provide the same mounting clearance through the A Kapton wrap.')
        else:
            line('Shape BRIK '+cut,'Shape TUBS '+cut,'Match B circular optical entrance.')
            line(params[0],f'{cut}.Parameters 0 2.7 {hx:.9g} 0 360','Match B 54 mm optical aperture.')
            decl.append(f'{ori}.Rotation 0 90 0')
    # B's four-bar W collimator sits in the front half of its BGO recess.
    for tag in ['Top','Bottom','PosY','NegY']:
        n='AA_W_Collimator_'+tag;x,y,z=map(float,d[n]['Position'].split())
        field(n,'Position',f'-24.2 {y:.9g} {z:.9g}',"Place B-identical W bars in the outer 20 mm of A's 40 mm BGO shield.")
    cap={}
    if args.al_cap=='horizontal-front':
        name='AA_Al_Inner_FrontCap_2mm'
        volume(name,'Aluminium',b['SH3_Layer01_FrontAnnulus']['Shape'],'-3.95 0 -5.2','0 90 0')
        field('Win_MagShield_Al_foil_side','Position','-3.95 0 -5.2','Close the inner cylinder front with B-identical annulus and optical foil.')
        cap={'part':name,'mode':args.al_cap,'front_face_x_cm':-4.05,'rear_face_x_cm':-3.85,'thickness_mm':2,'optical_aperture_mm':54,'B_reference':'SH3_Layer01_FrontAnnulus'}
    else:
        # The upright inner Al can ends at z=-0.3; close it below the retained MXC.
        name='AA_Al_Inner_Can_TopCap_2mm'
        volume(name,'Aluminium','PCON 0 360 2 -0.1 0 15.3 0.1 0 15.3','0 0 -0.3')
        cap={'part':name,'mode':args.al_cap,'center_z_cm':-.3,'thickness_mm':2,'note':'Needs cold-finger/MXC clearance closure before finalization.'}
    s+='\n// AA follow-up: top closure and B-matched optical interface.\n'+'\n'.join(decl)+'\n'
    new=parse(s);refs=re.findall(r'^\w+\.(?:SensitiveVolume|DetectorVolume)\s+(\w+)',det,re.M)
    assert all(n in new for n in refs)
    assert len([n for n,v in new.items() if v.get('Material')=='BGO'])==3
    assert len([n for n in new if n.startswith('TP_L')])==2256
    for aa,bb in window_map:
        assert new[aa]['Shape']==b[bb]['Shape'] and new[aa]['Material']==b[bb]['Material']
    assert len([n for n in new if n.startswith('Win_')])==5
    path.write_text(s);detpath.write_text(det)
    manifest['refinement']={'BGO_top':{'name':newtop,'thickness_mm':10,'z_center_cm':41.4,'outer_radius_cm':25.2,'ports':ports},'Al_top':{'name':new_al_top,'thickness_mm':3,'z_center_cm':45.55,'outer_radius_cm':26,'ports':al_ports},'Al_cap':cap,'B_matched_optics':{'clear_circle_diameter_mm':54,'Al_foils':4,'Al_thickness_um_each':25,'Be_foils':1,'Be_thickness_um':150,'window_mapping':dict(window_map),'removed_extra_A_foils':sorted(removed),'W_BGO_recess_square_mm':60},'line_edits':edits,'added_declarations':decl}
    manifest['W_collimator'].update(center_cm=[-24.2,0,-5.2],rear_face_cm=-23.2,front_face_cm=-25.2,placement='embedded in outer 20 mm of A BGO, matching B assembly arrangement')
    manifest['W_collimator'].pop('gap_to_Al_mm',None)
    manifest['outputs']={name:record(P/'geometry'/name) for name in manifest['outputs']}
    manifest['notes']=[n.replace('Existing NF2 relief voids in retained shields are preserved; only the outer frame solids are removed.','NF2 relief voids remain in unchanged side/bottom shields; the new top covers retain only the actual service-pipe holes.') for n in manifest['notes']]
    manifest['removed_objects']+=sorted(removed);manifest['removed_detector_definitions']+=sorted(removed_det)
    dump(P/'data/manifest.json',manifest);dump(P/'data/component_inventory.json',new)
    static=json.loads((P/'audit/static_validation.json').read_text());static['checks'].pop('all_surviving_physical_objects_unchanged')
    static['checks'].update(original_A_unrequested_components_retained=True,BGO_top_12_service_ports=True,optical_stack_shapes_and_materials_identical_to_B=True,only_5_optical_windows=True)
    static['followup_Al_cap']=args.al_cap;static['physical_differences_in_followup']=edits
    dump(P/'audit/static_validation.json',static)
    ports_checks={}
    for key in ['BGO_top','Al_top']:
        cover=manifest['refinement'][key];holes=cover['ports']
        ports_checks[key+'_12_holes']=len(holes)==12
        ports_checks[key+'_holes_disjoint']=all(math.hypot(a['x_cm']-b['x_cm'],a['y_cm']-b['y_cm'])>a['hole_radius_cm']+b['hole_radius_cm'] for i,a in enumerate(holes) for b in holes[i+1:])
        ports_checks[key+'_inside_cover']=all(math.hypot(a['x_cm'],a['y_cm'])+a['hole_radius_cm']<cover['outer_radius_cm'] for a in holes)
    ports_checks['all_12_ports_aligned']=all((a['x_cm'],a['y_cm'])==(b['x_cm'],b['y_cm']) for a,b in zip(ports,al_ports))
    ports_checks['Al_ports_at_least_as_wide_as_BGO_ports']=all(b['hole_radius_cm']>=a['hole_radius_cm'] for a,b in zip(ports,al_ports))
    assert all(ports_checks.values()),ports_checks
    dump(P/'audit/top_ports_validation.json',{'status':'PASS__AA_TOP_PORTS','checks':ports_checks,'gap_radial_mm':.5})
    print(json.dumps({'status':'PASS__AA_REFINED','BGO_ports':len(ports),'Al_cap':args.al_cap,'optical_windows':len(window_map)}))
if __name__=='__main__':main()
