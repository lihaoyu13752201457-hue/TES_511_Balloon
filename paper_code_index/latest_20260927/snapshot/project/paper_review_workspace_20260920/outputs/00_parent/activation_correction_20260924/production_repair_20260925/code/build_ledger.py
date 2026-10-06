from pathlib import Path
import sys,json,collections,math,re
P=Path(__file__).resolve().parents[1];O=P.parent;sys.path.insert(0,str(P/'code'))
from analyze_production import D,rdm,resolve
from prune_events import prune
# Particle codes used in the native IA format.
ptypes={'gamma':1,'e+':2,'e-':3,'proton':4,'anti_proton':5,'neutron':6,'mu+':8,'mu-':9,'alpha':21,'pi+':22,'pi-':23,'pi0':24}
def code(n):return D.states[n]['za'] if n in D.states else ptypes.get(n)
plan=json.loads((P/'data/production_plan.json').read_text());TT=collections.Counter()
for j in plan:TT[j['model'],j['family']]+=j['TT_s']
records=[];unresolved=[];group_tot=collections.Counter();remove=[];normal_rp=[];files=[]
for j in plan:
 p=Path(j['directory'])/'nuclear_events.json'
 if not p.exists() or not (p.parent/'nuclear_summary.json').exists():continue
 files.append(j['job_id'])
 for e in json.loads(p.read_text()):
  e=prune(e);ia={r['id']:r for r in e['IA']};groups=e['groups'];long=[]
  for g in groups:
   name=g['name']
   if name is None:
    name,why,m=resolve(g,{g['za']:set(g['labels'])});g.update(name=name,resolution=why,q_matches=m)
   if name is None:
    # Explicit RDM tables can rule out a long-lived state for light resonances.
    path=Path('/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/share/Geant4-10.2.3/data/RadioactiveDecay4.3.2')/f'z{g["za"]//1000}.a{g["za"]%1000}'
    hl=[float(l.split()[2]) for l in path.read_text().splitlines() if l.startswith('P ')] if path.exists() else []
    possible=[n for n in g['labels'] if n in D.states]
    pe=path.parent.parent/'PhotonEvaporation3.2'/path.name
    transitions=[list(map(float,(w[0],w[1],w[4]))) for l in pe.read_text().splitlines() if (w:=l.split()) and not l.startswith('#')] if pe.exists() else []
    matched=[r for r in transitions if abs(r[1]-g['sum_kinetic'])<.05]
    if possible and all(D.tau(n)<1e-6 for n in possible):g['resolution']='all_labelled_states_prompt'
    elif hl and max(hl)<1e-9:g['resolution']='only_short_lived_RDM_states'
    elif g['mode']=='IT' and matched and all(0<=r[2]<1e-10 for r in matched):g['resolution']='photon_transition_energy_and_short_lifetime';g['photon_matches']=matched
    else:unresolved.append({k:e[k] for k in ('model','family','job_id','event_id')}|{'group':g});continue
   group_tot[g['resolution']]+=1
   if name and D.tau(name)>=1e-6:long.append(g)
  earliest=[g for g in long if not any(set(g['ancestry_ids'])&set(h['decay_ids']) for h in long if h is not g)]
  for g in earliest:
   rid=len(records);removed=[];uncertain=[];children=set(g['decay_ids'])
   for i,r in enumerate(e['RP']):
    mom=code(r.get('par',''));cands=[v for v in ia.values() if v['secondary']==r['za'] and (mom is None or v['za']==mom)]
    if r.get('cproc')=='RadioactiveDecay':cands=[v for v in cands if v['process']=='DECA']
    def below(v):
     seen=set();k=v['id']
     while k in ia and k not in seen:
      if k in children:return True
      seen.add(k);k=ia[k]['origin']
     return False
    bad=[v for v in cands if below(v)]
    if not bad:continue
    good=[v for v in cands if not below(v)]
    dist=lambda v:math.dist(v['xyz'],r['xyz'])
    if not good or min(map(dist,bad))+1e-4<min(map(dist,good)):
     assert min(map(dist,bad))<.05,(j['job_id'],e['event_id'],r,bad)
     removed.append({**r,'ledger_id':rid,'model':j['model'],'family':j['family'],'job_id':j['job_id'],'event_id':e['event_id'],'rp_index_in_event':i,'minimum_creation_distance_cm':min(map(dist,bad))})
    else:uncertain.append(dict(rp=r,bad_candidates=bad,other_candidates=good))
   records.append(dict(ledger_id=rid,model=j['model'],family=j['family'],job_id=j['job_id'],event_id=e['event_id'],parent=g['name'],za=g['za'],exc_keV=D.states[g['name']]['exc'],native_tau_s=D.tau(g['name']),physical_tau_s=D.tau(g['name'],True),x=g['xyz'][0],y=g['xyz'][1],z=g['xyz'][2],production_rate_cps=1/TT[j['model'],j['family']],source_family_TT_s=TT[j['model'],j['family']],resolution=g['resolution'],IA_group=g,ancestor_IA=[ia[k] for k in g['ancestry_ids']],decay_IA=[ia[k] for k in g['decay_ids']],removed_RP=removed,uncertain_RP=uncertain))
   remove.extend(removed)
# A stored descendant must be removed only once.
keys=[(r['model'],r['job_id'],r['event_id'],r['rp_index_in_event']) for r in remove];assert len(keys)==len(set(keys))
(P/'data/repair_ledger.json').write_text(json.dumps(records,indent=2)+'\n');(P/'data/remove_RP.json').write_text(json.dumps(remove,indent=2)+'\n');(P/'data/unresolved_groups.json').write_text(json.dumps(unresolved,indent=2)+'\n')
summary={'files_processed':len(files),'production_files':len(plan),'earliest_restored_parents':len(records),'removed_stored_descendants':len(remove),'uncertain_descendant_joins':sum(len(r['uncertain_RP']) for r in records),'unresolved_groups':len(unresolved),'resolution_counts':dict(group_tot),'parent_counts':dict(collections.Counter(r['parent'] for r in records))};(P/'data/repair_ledger_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
