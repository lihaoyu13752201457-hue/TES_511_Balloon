"""Audit each new input history and retain only detector response, no trajectories."""
from common import *
from targeted_environment import T
import gzip,re,collections,concurrent.futures,time
BGO={'a':{'BGO_S3C_FullWrap_SideShell_WindowCut_40mm','BGO_S3D_O8_FullWrap_BottomCap_30mm','AA_BGO_TopCap_12Ports_10mm'},'b':{'SH3_BGO40_SideShield','SH3_BGO40_FrontOpticalAnnulus','SH3_BGO40_RearColdPortAnnulus'}}
HIT=re.compile(r'^CC HIT (\S+) edep_keV=([\deE+.-]+) x=([\deE+.-]+) y=([\deE+.-]+) z=([\deE+.-]+)')
UID=re.compile(r'^TP_L(\d+)_(\d+)$')

def run(r):
    d=Path(r['directory']);report=d/'compact.json'
    if report.exists() and read(report).get('decoder')=='native_HTsim_v1':return read(report)
    receipt=read(d/'receipt.json');sim=Path(receipt['sim']);N=r['events'];draw=dict(np.load(d/'draws.npz'));reg=read(T/'physical_registry.json');rates=np.load(T/'physical_rates_81nodes.npy',mmap_mode='r')
    pts=read(O/'data'/f"points_{r['model']}_{r['family']}.json")['points'];pixel=recon(r['model'])
    bg=np.zeros(N,dtype='f4');total=np.zeros(N,dtype='f4');start=np.zeros(N,dtype='i8');count=np.zeros(N,dtype='u2');final=np.zeros(N,dtype=bool);codes=[];energy=[];positions=[]
    key=lambda xyz:tuple(round(float(x),5) for x in xyz)
    centers={key(v):k for k,v in read(T/'ht_mapping.json')['centres'][r['model']].items()}
    pixels={key(v):k for k,v in pixel.geometry.centres.items()}
    event=-1;pending={};bgo=0.;ninit=0;seen=[];terminal=False;ts=None;geo=None;seed=None;maxexcess=0.;htcount=0;cccount=0
    def finish():
        nonlocal maxexcess
        if event<0:return
        assert ninit==1,(r['job'],event,ninit)
        start[event]=len(codes);count[event]=len(pending);bg[event]=bgo;hits=[]
        for code,(e,xyz) in sorted(pending.items()):
            uid=f'TP_L{code//100000}_{code%100000:05d}';codes.append(code);energy.append(e);positions.append(xyz)
            maxexcess=max(maxexcess,pixel.geometry.deposition_excess_cm(uid,xyz))
            ee=e+SIGMA*normal('targeted_activation_20260924',r['model'],r['family'],r['seed'],event+1,uid)
            if ee>=.3:hits.append(PixelMeasurement(uid,ee))
        value=math.fsum(h.energy_keV for h in hits);total[event]=value
        final[event]=480<=value<550 and bgo<50 and bool(pixel.classify(hits)[0])
    with gzip.open(sim,'rt') as f:
        for l in f:
            if l.startswith('Geometry '):geo=l.split(None,1)[1].strip()
            elif l.startswith('Seed '):seed=int(l.split()[1])
            elif l.startswith('ID '):
                finish();event=int(l.split()[1])-1;assert event==len(seen);seen.append(event);pending={};bgo=0.;ninit=0
            elif l.startswith('IA INIT'):
                ninit+=1;a=l.split(';');c=reg[int(draw['category'][event])];p=pts[int(draw['point_id'][event])]
                assert int(a[15])==c['za']
                assert np.max(np.abs(np.array(list(map(float,a[4:7])))-np.array([p[k] for k in ['x','y','z']])))<=5.1e-6
            elif l.startswith('CC Future'):raise AssertionError('unexpected daughter queue')
            elif l.startswith('CC HIT'):
                cccount+=1
                m=HIT.match(l);assert m,l[:150]
                volume=m[1];e=float(m[2]);u=UID.match(volume)
                if u:
                    code=int(u[1])*100000+int(u[2]);xyz=tuple(map(float,m.group(3,4,5)))
                    old=pending.get(code,(0.,xyz));pending[code]=(old[0]+e,old[1])
                elif volume in BGO[r['model']]:bgo+=e
            elif l.startswith('HTsim '):
                htcount+=1;a=l.split(';');kind=int(a[0].split()[1]);xyz=tuple(map(float,a[1:4]));e=float(a[4]);assert math.isfinite(e) and e>=0
                if kind==2:
                    uid=pixels.get(key(xyz))
                    if uid is None:
                        uid=min(pixel.geometry.centres,key=lambda u:np.linalg.norm(pixel.geometry.centres[u]-xyz))
                        assert np.linalg.norm(pixel.geometry.centres[uid]-xyz)<1e-5,(r['job'],xyz)
                    u=UID.match(uid);code=int(u[1])*100000+int(u[2])
                    if e>0:
                        old=pending.get(code,(0.,xyz));pending[code]=(old[0]+e,old[1])
                elif kind==4:
                    if key(xyz) in centers:bgo+=e
                else:raise AssertionError(('unexpected detector kind',kind))
            elif l.strip()=='EN':terminal=True
            elif l.startswith('TS '):ts=int(l.split()[1])
    finish();assert len(seen)==N==ts and terminal,(r['job'],len(seen),N,ts,terminal)
    assert geo==r['geometry'] and seed==r['seed'],(geo,seed,r['seed'])
    assert cccount==0,(cccount,htcount)
    assert maxexcess<1e-4,(r['job'],maxexcess)
    cat=draw['category'];bound=np.max(rates[:,cat],axis=0);base=r['proposal_sum_cps']/N/bound
    arrays=dict(event_id=np.arange(1,N+1,dtype='i4'),event_category=cat,event_base_weight_cps=base,bgo_keV=bg,measured_total_keV=total,hit_start=start,hit_count=count,hit_code=np.array(codes,dtype='i4'),hit_energy_keV=np.array(energy,dtype='f4'),hit_position_cm=np.array(positions,dtype='f8').reshape(-1,3),final=final,point_id=draw['point_id'])
    np.savez_compressed(d/'compact.npz',**arrays)
    sel=final&(total>=510.5)&(total<511.5);w=base*rates[60,cat];v=w[sel];rate=float(v.sum());var=float((v*v).sum());selected=[]
    for i in np.flatnonzero(sel):
        c=reg[int(cat[i])];p=pts[int(draw['point_id'][i])];selected.append(dict(job=r['job'],event_id=int(i)+1,category=int(cat[i]),state=c['state'],root=c['root'],point_id=p['point_id'],volume=p['volume'],day15_weight_cps=float(w[i]),measured_total_keV=float(total[i])))
    save(d/'selected.json',selected)
    result={**r,'status':'PASS','decoder':'native_HTsim_v1','HTsim_records':htcount,'events':N,'response_positive':int(np.sum((count>0)|(bg>0))),'selected':int(sel.sum()),'day15_selected_cps':rate,'sumw2':var,'fixed_N_variance':max(0.,(var-rate*rate/N)*N/(N-1)) if N>1 else var,'zero_selected_one_sided_95_bound_cps':float(-math.expm1(math.log(.05)/N)*r['proposal_sum_cps']) if not len(v) else None,'maximum_deposition_outside_pixel_cm':maxexcess,'compact_sha256':sha(d/'compact.npz'),'sim_sha256':sha(sim),'seed_verified':True,'one_init_per_event':True,'source_position_verified':True,'no_daughter_queue':True}
    save(report,result);print(r['job'],'PASS',N,'selected',len(v),'rate',rate,flush=True)
    return result
if __name__=='__main__':
    batch=sys.argv[1] if len(sys.argv)>1 else 'batch01';plan=read(T/batch/'plan.json')
    # Can run while transport continues; each file is read only after its receipt.
    pending={r['job']:r for r in plan};done=[]
    while pending:
        ready=[r for r in pending.values() if (Path(r['directory'])/'receipt.json').exists()]
        if not ready:time.sleep(2);continue
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            for result in ex.map(run,ready):done.append(result);del pending[result['job']]
    save(T/batch/'compact_summary.json',done)
    print('COMPACT COMPLETE',sum(r['events'] for r in done),flush=True)
