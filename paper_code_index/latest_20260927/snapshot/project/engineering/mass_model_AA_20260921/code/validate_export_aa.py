#!/usr/bin/env python3
"""Reuse the project's Geant4 overlap and native VRML exporters, with AA inputs."""
from pathlib import Path
import importlib.util, json, sys

P=Path(__file__).resolve().parents[1]
SHARED=Path('/home/ubuntu/TES_511_Balloon/engineering/geometry_optimization_20260815/sh3/assembly/code')

def load(kind):
    file=SHARED/('run_sh3_assembly_overlap.py' if kind=='overlap' else 'export_sh3_assembly_wrl.py')
    spec=importlib.util.spec_from_file_location('aa_'+kind,file);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    mod.PACKAGE=P;mod.GEOMETRY=P/'geometry';mod.AUDIT=P/'audit';mod.DATA=P/'data';mod.FIGURES=P/'figures'
    mod.SETUP=mod.GEOMETRY/'Mass_model_AA.geo.setup';mod.GEO=mod.GEOMETRY/'Mass_model_AA.geo';mod.DET=mod.GEOMETRY/'Mass_model_AA.det';mod.MATERIALS=mod.GEOMETRY/'Materials_Mass_model_AA.geo'
    mod.MANIFEST=P/'data/manifest.json';mod.STATIC=P/'audit/static_validation.json';mod.OVERLAP=P/'audit/overlap_validation.json'
    mod.LOG=P/'audit'/f'{kind}_cosima.log'
    report=P/'audit'/f'{kind}_validation.json'
    mod.OUTPUT=report if kind=='overlap' else P/'figures/Mass_model_AA_native.wrl'
    mod.REPORT=report
    def verify():
        manifest=json.loads(mod.MANIFEST.read_text());static=json.loads(mod.STATIC.read_text())
        assert manifest['status']=='PASS__AA_BUILT' and static['status']=='PASS__AA_STATIC'
        records={}
        for name,expected in manifest['outputs'].items():
            path=P/'geometry'/name;digest=mod.sha256(path);assert digest==expected['sha256'],f'Stale AA input {name}'
            records[name]={'path':str(path),'bytes':path.stat().st_size,'sha256':digest}
        if kind=='wrl':
            overlap=json.loads(mod.OVERLAP.read_text());assert overlap['status']=='PASS__AA_OVERLAP_NO_TRANSPORT'
            assert all(overlap['source_authority'][n]['sha256']==r['sha256'] for n,r in records.items())
        return records
    mod.verify_authority=verify
    return mod,report,file

def main():
    kinds=sys.argv[1:] or ['overlap','wrl']
    for kind in kinds:
        assert kind in ('overlap','wrl')
        mod,path,shared=load(kind);result=mod.main();report=json.loads(path.read_text())
        report['component_identity']='Mass_model_AA';report['shared_harness']={'path':str(shared),'sha256':mod.sha256(shared)}
        if result==0: report['status']='PASS__AA_'+('OVERLAP_NO_TRANSPORT' if kind=='overlap' else 'NATIVE_WRL_NO_TRANSPORT')
        path.write_text(json.dumps(report,indent=2)+'\n')
        print(report['status'],flush=True)
        if result: return result
    return 0

if __name__=='__main__': raise SystemExit(main())
