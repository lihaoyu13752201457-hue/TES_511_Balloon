"""Freeze the corrected optical sample and construct auditable A/B sources."""
from pathlib import Path
import csv, hashlib, json, math, shutil
import numpy as np

O = Path(__file__).resolve().parents[1]
F = O.parent
W = F.parents[1]
P = Path('/home/ubuntu/TES_511_Balloon')
OPT = W / 'outputs/01_intro_geometry_optics/c_repair_20260920/paper_ready'
ORIGINAL = {
    'a': Path('/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/geometry/DEMO2_DR_v3p5_SG3B.geo.setup'),
    'b': Path('/home/ubuntu/.codex/worktrees/e3cf/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly_opt_v3/geometry/SH3_Assembly_OptV3_60cm.geo.setup'),
}
SEEDS = {'a': 1952092001, 'b': 1952092002}
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
write = lambda p, x: p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')

def main():
    for d in ['inputs', 'data', 'validation', 'eventlists', 'configs', 'runs/a', 'runs/b', 'geometry/a', 'geometry/b']:
        (O/d).mkdir(parents=True, exist_ok=True)
    for name in ['focal_crossings_corrected.csv', 'focus_export_manifest.json']:
        dest=O/'inputs'/name
        if dest.exists(): assert sha(dest)==sha(OPT/name)
        else: shutil.copyfile(OPT/name,dest)
    meta=json.loads((O/'inputs/focus_export_manifest.json').read_text())
    csvpath=O/'inputs/focal_crossings_corrected.csv'
    assert sha(csvpath)==meta['phase_space_sha256']=='c1ab040274b69927c8153518e3f15e455e40c535ea3c12758895761ec982f1d6'
    rows=list(csv.DictReader(csvpath.open()))
    n=len(rows); assert n==meta['n_selected']==37175
    e=np.array([float(r['E_keV']) for r in rows]); assert np.all(e==511.)
    optpos=np.array([[float(r[k]) for k in ['x_mm','y_mm','z_mm']] for r in rows])
    optdir=np.array([[float(r[k]) for k in ['ux','uy','uz']] for r in rows])
    assert np.allclose(np.linalg.norm(optdir,axis=1),1.,atol=1e-12)
    assert np.all(optpos[:,2]==10000.) and np.all(optdir[:,2]>0.)
    assert all(float(r['weight'])==1 and r['source_tag']=='laue_bfull_diffracted' for r in rows)
    optical_ids=np.array([int(r['event_id']) for r in rows]); assert len(np.unique(optical_ids))==n
    radii=np.hypot(optpos[:,0],optpos[:,1])*.1; assert np.max(radii)<=1.898+1e-12
    c=math.sqrt(.5); rot=np.array([[c,0,c],[0,1,0],[-c,0,c]])
    localdir=optdir[:,[2,0,1]]; worlddir=localdir@rot.T
    cfg={'schema_version':1,'status':'INPUTS_VALIDATED','n_input':n,'optical_manifest':meta,
         'optical_source':str(csvpath),'optical_source_sha256':sha(csvpath),
         'optical_reference_plane_z_mm':10000.,'rotation_y_deg':45.,
         'direction_mapping':'(optical uz,ux,uy) in detector-local axes, then Ry(45 deg)',
         'response':{'fwhm_keV_per_pixel':.5,'pixel_threshold_keV':.3,'active_threshold_keV':50.,'windows_keV':{'narrow':[510.5,511.5],'broad':[480.,550.]}},
         'focus_radius_cm':{str(q):float(np.sort(radii)[math.ceil(q*n)-1]) for q in [.5,.9,.95,.99]},
         'models':{},'seed_audit':{'new_seeds':SEEDS,'registered_metadata_search':'No matches in original engineering/runs/DEEPSEEK modified *.source, *ledger*.json, *manifest*.json, *seed*.json; performed before registration.'}}
    for model,srcsetup in ORIGINAL.items():
        destdir=O/'geometry'/model; provenance=[]; seen=set()
        def freeze(src):
            src=src.resolve()
            if src in seen:return
            seen.add(src)
            external=str(src).startswith('/home/ubuntu/MEGAlib_Install/')
            dest=src if external else destdir/src.name
            if dest.exists(): assert sha(dest)==sha(src)
            else:shutil.copyfile(src,dest)
            provenance.append({'original':str(src),'snapshot':str(dest),'sha256':sha(src),'bytes':src.stat().st_size,'external_read_only':external})
            for line in src.read_text().splitlines():
                f=line.split('//')[0].split()
                if f and f[0].lower()=='include':
                    assert len(f)==2,line
                    include=f[1].replace('$(MEGALIB)','/home/ubuntu/MEGAlib_Install/megalib-main')
                    assert '$' not in include,include
                    freeze(src.parent/include)
        freeze(srcsetup)
        setup=destdir/srcsetup.name
        geo=destdir/('DEMO2_DR_v3p5_SG3B.geo' if model=='a' else 'SH3_Assembly_OptV3.geo')
        tx,tz=(-13.1,-5.2) if model=='a' else (-46.,-2.8)
        # Preserve the existing reconstruction/reference plane. Back-project A
        # before its physical windows and shielding instead of starting inside.
        launch_x=-60. if model=='a' else -46.
        reference=np.column_stack([np.full(n,tx),optpos[:,0]*.1,optpos[:,1]*.1+tz])
        distance=(launch_x-tx)/localdir[:,0]
        launch=reference+distance[:,None]*localdir
        worldpos=launch@rot.T
        restored=launch+((tx-launch[:,0])/localdir[:,0])[:,None]*localdir
        assert np.max(np.abs(restored-reference))<2e-14
        assert np.allclose(worldpos@rot,launch,atol=2e-14)
        # EventList transport remains inside the pinned surrounding sphere.
        sphere_dist=np.linalg.norm(worldpos-np.array([5.,0.,9.]),axis=1)
        assert np.max(sphere_dist)<60.,(model,np.max(sphere_dist))
        eventlist=O/'eventlists'/f'signal_{model}_37175.dat'
        with eventlist.open('w') as f:
            for i,(pos,direction,energy) in enumerate(zip(worldpos,worlddir,e)):
                values=[str(i),'0','1','0',f'{i*1e-9:.12e}',*[f'{v:.15g}' for v in pos],*[f'{v:.15g}' for v in direction],'0','0','0',f'{energy:.15g}']
                f.write(' '.join(values)+'\n')
        serialized=np.loadtxt(eventlist)
        assert serialized.shape==(n,15) and np.max(np.abs(serialized[:,5:8]-worldpos))<1e-12
        name=f'CorrectedOptics_{model.upper()}_Signal37175'
        prefix=O/'runs'/model/name
        card=O/'configs'/f'signal_{model}.source'
        card.write_text(f'''# Corrected optical sample; geometry and seeds pinned in inputs_manifest.json.
Version 1
Geometry {setup}
PhysicsListEM LivermorePol
PhysicsListHD qgsp-bic-hp
StoreSimulationInfo all
DiscretizeHits true
DetectorTimeConstant 1e-9
Seed {SEEDS[model]}

Run {name}
{name}.FileName {prefix}
{name}.Triggers {n}
{name}.Source {name}_PhaseSpace
{name}_PhaseSpace.EventList {eventlist}
''')
        assert 'cosima_spectra_dp_2602units' not in card.read_text()
        bcfg=json.loads((P/'DEEPSEEK_CODE/modified/analysis_inputs_optv3_B.json').read_text())
        plastic=['GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm','GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm','GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm'] if model=='a' else []
        bgo=['BGO_S3C_FullWrap_SideShell_WindowCut_40mm','BGO_S3D_O8_FullWrap_BottomCap_30mm','BGO_S3D_O8_FullWrap_TopAnnulus_10mm'] if model=='a' else bcfg['active_veto']['bgo_active_scintillator_volumes']
        for volume in plastic+bgo:assert f'Volume {volume}\n' in geo.read_text(),volume
        cfg['models'][model]={'geometry_setup':str(setup),'geometry_geo':str(geo),'geometry_provenance':provenance,'seed':SEEDS[model],
            'source_card':str(card),'source_card_sha256':sha(card),'eventlist':str(eventlist),'eventlist_sha256':sha(eventlist),
            'sim':str(prefix)+'.inc1.id1.sim.gz','log':str(O/'runs'/model/'cosima.log'),
            'reference_plane_local_cm':[tx,0.,tz],'launch_plane_local_x_cm':launch_x,
            'aperture_radius_cm':1.898 if model=='a' else 1.9,'max_reference_plane_roundtrip_error_cm':float(np.max(np.abs(restored-reference))),
            'max_launch_distance_from_surrounding_sphere_center_cm':float(np.max(sphere_dist)),
            'plastic_volumes':plastic,'bgo_volumes':bgo}
    np.savez_compressed(O/'data/optical_identity.npz',source_row=np.arange(n),optical_event_id=optical_ids,optical_position_mm=optpos,optical_direction=optdir,energy_keV=e)
    for name in ['pixel_geometry_compton.py','legacy_side_compton.py']:
        src=F/'a_geometry_comparison_20260920/code'/name;dst=O/'code'/name
        if dst.exists():assert sha(dst)==sha(src)
        else:shutil.copyfile(src,dst)
    cfg['reconstruction_code']=[{'file':str(O/'code'/name),'sha256':sha(O/'code'/name)} for name in ['pixel_geometry_compton.py','legacy_side_compton.py']]
    cfg['source_interface_issue']={'model':'a','legacy_launch_x_cm':-13.1,'physical_Be_center_x_cm':-20.35,
       'physical_outer_Al_filter_x_cm':-20.92,'new_launch_x_cm':-60.,
       'resolution':'Back-project each ray from the retained -13.1 cm phase-space reference plane to -60 cm; no re-filtering, remapping of focus or direction averaging.',
       'paper_wording_issue':'Existing statement identifying the focal selection plane with the physical Be entrance is not exact for current A geometry. No nonnumeric prose change authorized.'}
    write(O/'inputs_manifest.json',cfg)
    write(O/'seed_ledger.json',{'status':'REGISTERED_NOT_YET_TRANSPORTED','jobs':[{k:cfg['models'][m][k] for k in ['seed','source_card','geometry_setup','eventlist']} for m in ['a','b']]})
    print(json.dumps({'status':'PASS','n':n,'radii_cm':cfg['focus_radius_cm'],'models':{m:{k:cfg['models'][m][k] for k in ['reference_plane_local_cm','launch_plane_local_x_cm','max_reference_plane_roundtrip_error_cm']} for m in ['a','b']}},indent=2))

if __name__=='__main__': main()
