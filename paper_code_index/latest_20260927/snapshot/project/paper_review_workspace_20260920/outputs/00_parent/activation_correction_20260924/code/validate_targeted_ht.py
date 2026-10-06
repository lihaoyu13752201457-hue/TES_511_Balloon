"""Independent named-deposit/native-hit closure on bounded existing prefixes."""
from common import *
from targeted_environment import T
from compact_targeted import BGO,HIT,UID
import gzip,collections
result={};jobs=read(O/'data/runtime_jobs.json')
for model in ['a','b']:
    pixel=recon(model);key=lambda x:tuple(round(float(a),5) for a in x)
    centre={key(x):u for u,x in pixel.geometry.centres.items()};active={key(x):u for u,x in read(T/'ht_mapping.json')['centres'][model].items()}
    job=next(r for r in jobs if r['model']==model and r['family']=='p');cc=collections.Counter();ht=collections.Counter();event=0;largest=0.;pairs=0;pixelpairs=0
    def finish():
        global largest,pairs,pixelpairs
        for u in set(cc)|set(ht):
            diff=abs(cc[u]-ht[u]);assert diff<max(2e-4,cc[u]*3e-6),(model,event,u,cc[u],ht[u])
            largest=max(largest,diff);pairs+=1;pixelpairs+=u.startswith('TP_L')
    with gzip.open(job['sim_path'],'rt') as f:
        for l in f:
            if l.startswith('ID '):
                if event:finish()
                event+=1;cc=collections.Counter();ht=collections.Counter()
                if event>2000:break
            elif l.startswith('CC HIT'):
                m=HIT.match(l);assert m
                u=m[1]
                if UID.match(u):
                    a=UID.match(u);u=f'TP_L{int(a[1])}_{int(a[2]):05d}'
                if u in BGO[model] or u.startswith('TP_L'):cc[u]+=float(m[2])
            elif l.startswith('HTsim '):
                a=l.split(';');kind=int(a[0].split()[1]);xyz=tuple(map(float,a[1:4]));e=float(a[4]);u=None
                if kind==2:
                    u=centre.get(key(xyz))
                    if u is None:
                        u=min(pixel.geometry.centres,key=lambda u:np.linalg.norm(pixel.geometry.centres[u]-xyz));assert np.linalg.norm(pixel.geometry.centres[u]-xyz)<1e-5
                elif kind==4:u=active.get(key(xyz))
                if u:ht[u]+=e
    assert pixelpairs>0
    result[model]=dict(events=2000,volume_pixel_pairs=pairs,TES_pixel_pairs=pixelpairs,maximum_absolute_energy_difference_keV=largest,source=job['sim_path'])
save(T/'ht_decoder_validation.json',dict(status='PASS',models=result,meaning='Named raw energy sums equal native HTsim energies. Native coordinates identify physical pixel IDs only; Compton calculation uses vertices/centre from geometry.'))
print(json.dumps(result,indent=2))
