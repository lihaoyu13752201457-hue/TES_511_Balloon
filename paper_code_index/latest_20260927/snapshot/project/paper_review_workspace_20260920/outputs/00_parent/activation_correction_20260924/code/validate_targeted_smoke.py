from targeted_environment import *
import gzip,collections,re,csv
p=T/'smoke_verified';f=next(p.glob('*.sim.gz'));c=collections.defaultdict(collections.Counter);events=[];eid=-1;geo=None
for l in gzip.open(f,'rt'):
    if l.startswith('Geometry '):geo=l.split(None,1)[1].strip()
    if l.startswith('ID '):eid=int(l.split()[1]);events.append(eid)
    if l.startswith('IA INIT'):c[(eid-1)//200]['init']+=1
    if l.startswith('CC Future'):c[(eid-1)//200]['future']+=1
    if l.startswith('CC HIT'):
        m=re.search(r' prim=(\S+)',l)
        if m:c[(eid-1)//200]['prim:'+m[1]]+=1
    if l.startswith('IA DECA'):
        a=l.split(';');c[(eid-1)//200]['decaying_ZA:'+a[7].strip()]+=1
        c[(eid-1)//200]['emitted_ZA:'+a[15].strip()]+=1
assert events==list(range(1,1001))
assert all(v.get('future',0)==0 for v in c.values())
# Zn62 prompt Cu62 excited transitions remain; the later Cu62 -> Ni62 beta
# is absent. This tests the actual stop boundary, not just queue text.
assert c[0].get('emitted_ZA:28062',0)==0
assert c[1].get('emitted_ZA:28062',0)>0
assert c[2].get('decaying_ZA:68158',0)>0
assert c[2].get('emitted_ZA:66158',0)==0
assert c[3].get('prim:Ho158[67.199]',0)>0
probe=list(csv.DictReader((T/'nuclear_probe.tsv').open(),delimiter='\t'))
assert sum(int(r['count']) for r in probe if r['parent']=='Er158' and r['valid']=='1')==32768
ldd=subprocess.check_output(['ldd',str(T/'cosima')],env=environment(),text=True)
assert str(T/'lib/libCosima.so') in ldd
result=dict(status='PASS',events=len(events),one_input_one_record=True,no_future_daughter_queue=True,Zn62_prompt_transitions_retained_and_Cu62_delayed_beta_excluded=True,Er158_valid_nuclear_trials=32768,Er158_delayed_Ho158_decay_excluded=True,eventlist_excited_state_keV_preserved=True,geometry=geo,groups=c,sim_sha256=sha(f),library_sha256=sha(T/'lib/libCosima.so'),validation_transport_histories_consumed=2000)
(p/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS explicit-state response tests',flush=True)
