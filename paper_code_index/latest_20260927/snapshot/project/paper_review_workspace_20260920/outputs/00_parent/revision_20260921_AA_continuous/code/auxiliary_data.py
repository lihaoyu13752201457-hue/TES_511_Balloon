from common import *
manifest=read(AS/'derived/merged/manifest.json');done=read(AA/'data/baseline_transport_complete.json');inv=read(done['delayed']['inventory_manifest']);activities={c['family']:c['transported_ground_activity_Bq'] for c in inv['source_cells']};out=[]
for r in read(O/'data/a/family_transport.json'):
 f=r['family'];stream=r['stream'];r=r.copy()
 if stream=='prompt':
  r['transported']=sum(done['coverage'][s]['by_family'][f] for s in ['instant_full','instant_minimal']);r['Teq_s']=manifest['prompt_TT_s'][f]
 else:
  r['transported']=done['coverage']['delayed_epoch0']['by_family'][f];r['Teq_s']=r['transported']/activities[f] if activities[f] else None
 out.append(r)
save(O/'data/aa_transport_table.json',out)
p=W/'outputs/04_results_environments_conclusions/numeric_sync_20260920/data/environment_kernel_500.json';x=read(p);new=read(O/'data/RESULTS.json')['models']['b']['mission_20day']['F3'];old=next(r['F3_screening_ph_cm2_s'] for r in x['screening'] if r['environment']=='balloon_reference') if any(r['environment']=='balloon_reference' for r in x['screening']) else x['screening'][0]['F3_screening_ph_cm2_s']
for r in x['screening']:r['F3_screening_ph_cm2_s']*=new/old
x['numeric_update']={'old_balloon_F3':old,'new_balloon_F3':new,'background_response_unchanged':True,'method':'Preserve existing environment transfer ratios; replace common balloon F3 normalization.'}
save(O/'data/environment_kernel_500.json',x)
print('Environment',old,new,[r['environment'] for r in x['screening']])
