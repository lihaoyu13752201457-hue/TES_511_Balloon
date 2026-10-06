from pathlib import Path
import json,gzip,collections,re,math,sys
P=Path(__file__).resolve().parents[1];O=P.parent;sys.path.insert(0,str(O/'code'))
from decay_kernel import NuclearData
D=NuclearData();GD=Path('/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/share/Geant4-10.2.3/data/RadioactiveDecay4.3.2')
BYZA=collections.defaultdict(list)
for n,s in D.states.items():BYZA[s['za']].append(n)
CACHE={}
def rdm(za):
 if za in CACHE:return CACHE[za]
 p=GD/f'z{za//1000}.a{za%1000}';out=[];ex=0;hl=math.inf
 if p.exists():
  for l in p.read_text().splitlines():
   if l.startswith('#'):continue
   w=l.split()
   if not w:continue
   if w[0]=='P':ex=float(w[1]);hl=float(w[2])
   elif len(w)>=4:
    try:out.append(dict(mode=w[0],exc=ex,hl=hl,daughter_exc=float(w[1]),br=float(w[2]),q=float(w[3])))
    except ValueError:pass
 CACHE[za]=out;return out

def resolve(group,labels):
 za=group['za'];products=group['secondary_types'];energy=group['sum_kinetic'];names=labels.get(za,set())
 # Only branches that actually change the nuclide are inferred from Q.
 mode='BetaMinus' if 3 in products and 13 in products else 'BetaPlus' if 2 in products and 12 in products else 'EC' if 12 in products else 'Alpha' if 21 in products else 'IT'
 group['mode']=mode;matches=[]
 if mode!='IT':
  for c in rdm(za):
   if not (c['mode']==mode or mode=='EC' and c['mode'].endswith('EC')):continue
   expect=c['q']-(1021.9979 if mode=='BetaPlus' else 0)
   # Captured-electron binding can be locally deposited without an emitted track.
   residual=energy-expect
   if abs(residual)<.05 or mode=='EC' and -.1<residual<.1:matches.append(c)
  exs=sorted(set(c['exc'] for c in matches))
  if len(exs)==1:
   ex=exs[0];gname=D.name(za,ex) if any(abs(D.states[n]['exc']-ex)<.101 for n in BYZA[za]) else None
   if gname is not None:return gname,'RDM_branch_Q_closure',matches
  allowed=[]
  for n in names:
   if n not in D.states:continue
   # Exact parent identity is read from track ancestry; restricting to
   # nuclide-changing channels excludes unrelated same-ZA fast IT levels.
   if any(D.states[ch]['za']!=za for ch in D.adj[n]):allowed.append(n)
  if len(allowed)==1:return allowed[0],'unique_exact_track_parent_for_nuclide_change',matches
  if len(exs)>1:return None,'ambiguous_Q',matches
  return None,'unresolved_nuclide_change',matches
 # IT: labelled states may identify it. Defer unresolved levels explicitly.
 allowed=[n for n in names if n in D.states and D.states[n]['exc']>0]
 by_energy=[n for n in allowed if any(D.states[ch]['za']==za and abs(D.states[n]['exc']-D.states[ch]['exc']-energy)<.05 for ch in D.adj[n])]
 if len(by_energy)==1:return by_energy[0],'IT_transition_energy_closure',matches
 if len(allowed)==1:return allowed[0],'unique_exact_track_parent_IT',matches
 pe=GD.parent/'PhotonEvaporation3.2'/f'z{za//1000}.a{za%1000}'
 if pe.exists():
  transitions=[w for l in pe.read_text().splitlines() if (w:=l.split()) and not l.startswith('#') and abs(float(w[1])-energy)<.05]
  levels={float(w[0]) for w in transitions}
  if len(levels)==1:
   energy_level=next(iter(levels));ns=[n for n in BYZA[za] if abs(D.states[n]['exc']-energy_level)<.05]
   if len(ns)==1:return ns[0],'unique_photon_transition_parent_level',matches
 return None,'IT_unresolved',matches

def parse_event(lines,job,eid):
 ia={};rps=[];labels=collections.defaultdict(set);tracks={};groups=collections.defaultdict(list)
 for l in lines:
  if l.startswith('IA '):
   w=l.split(';');head=w[0].split();r=dict(id=int(head[2]),origin=int(w[1]),process=head[1],za=int(w[7]),secondary=int(w[15]),xyz=list(map(float,w[4:7])),energy=float(w[-1]),line=l);ia[r['id']]=r
   if r['process']=='DECA' and r['za']>2004:groups[(r['origin'],r['za'],tuple(r['xyz']))].append(r)
  elif l.startswith('CC IP RP '):
   w=l.split();kv=dict(x.split('=',1) for x in w[10:] if '=' in x);rps.append(dict(volume=w[3].removesuffix('_pv'),xyz=list(map(float,w[4:7])),za=int(w[7]),exc=float(w[8]),time=float(w[9]),**kv,line=l))
   if kv.get('cproc')=='RadioactiveDecay':
    n=kv.get('par');m=re.match(r'^([A-Za-z]+)(\d+)',n or '')
    if n in D.states:labels[D.states[n]['za']].add(n)
  elif l.startswith('CC HIT '):
   w=l.split();kv=dict(x.split('=',1) for x in w[3:] if '=' in x);tid=int(kv['tid']);tracks[tid]=dict(volume=w[2],**kv,line=l)
   if kv.get('cproc')=='RadioactiveDecay':
    n=kv.get('par')
    if n in D.states:labels[D.states[n]['za']].add(n)
 out=[]
 for (origin,za,xyz),rs in groups.items():
  g=dict(origin=origin,za=za,xyz=list(xyz),secondary_types=[r['secondary'] for r in rs],sum_kinetic=math.fsum(r['energy'] for r in rs),decay_ids=[r['id'] for r in rs]);name,why,match=resolve(g,labels);g.update(name=name,resolution=why,q_matches=match,labels=sorted(labels.get(za,[])))
  if name:
   g['native_tau_s']=D.tau(name);g['physical_tau_s']=D.tau(name,True)
  trace=[];i=origin;seen=set()
  while i in ia and i not in seen:
   seen.add(i);trace.append(i);i=ia[i]['origin']
  g['ancestry_ids']=trace;out.append(g)
 if not out:return None
 return dict(model=job['model'],family=job['family'],job_id=job['job_id'],event_id=eid,groups=out,RP=rps,IA=[r for r in ia.values()],track_meta=list(tracks.values()))

def run(job):
 directory=Path(job['directory']);dest=directory/'nuclear_events.json'
 if dest.exists():return json.loads((directory/'nuclear_summary.json').read_text())
 events=[];lines=[];eid=None
 with gzip.open(directory/'thin.sim.gz','rt') as f:
  for l in f:
   if l.startswith('ID '):
    if eid is not None:
     v=parse_event(lines,job,eid)
     if v:events.append(v)
    eid=int(l.split()[1]);lines=[]
   elif eid is not None:lines.append(l.strip())
 if eid is not None:
  v=parse_event(lines,job,eid)
  if v:events.append(v)
 dest.write_text(json.dumps(events)+'\n')
 summary=collections.Counter();unres=collections.Counter();longs=collections.Counter()
 for e in events:
  for g in e['groups']:
   summary[g['resolution']]+=1
   if g['name'] is None:unres[(g['za'],g['mode'])]+=1
   elif g['native_tau_s']>1e-6:longs[g['name']]+=1
 out={k:job[k] for k in ['model','family','job_id','directory']};out.update(events_with_nuclear_decay=len(events),resolution_counts=dict(summary),unresolved=[dict(za=z,mode=m,n=n) for (z,m),n in unres.items()],long_parent_groups=dict(longs));(directory/'nuclear_summary.json').write_text(json.dumps(out,indent=2)+'\n');return out
if __name__=='__main__':
 plan=json.loads((P/'data/production_plan.json').read_text());out=[]
 for j in plan:
  if not (Path(j['directory'])/'extraction.json').exists():continue
  out.append(run(j))
 (P/'data/nuclear_summary.json').write_text(json.dumps(out,indent=2)+'\n');tot=collections.Counter();un=collections.Counter();long=collections.Counter()
 for r in out:
  tot.update(r['resolution_counts']);long.update(r['long_parent_groups'])
  for u in r['unresolved']:un[(u['za'],u['mode'])]+=u['n']
 print('files',len(out),'resolved',tot,'long',long,'unresolved',un.most_common(40),flush=True)
