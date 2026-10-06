"""Evaluate actual signal/prompt/delayed coincidence groups using raw deposits."""
from common import *
import struct
from collections import Counter

def wilson(k,n):
 if n==0:return [None,None]
 p=k/n;z=1.959963984540054;den=1+z*z/n;c=(p+z*z/(2*n))/den;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den;return [max(0,c-h),min(1,c+h)]
def frac(k,n):return {'numerator':k,'denominator':n,'value':k/n if n else None,'ci95_wilson':wilson(k,n)}

class Analyzer:
 def __init__(self,model):
  self.model=model;self.d=O/'data'/model;self.meta=json.loads((self.d/'compact_metadata.json').read_text());self.nb=self.meta['background_records']
  self.a,_,_=background(model)
  self.s=dict(np.load(self.d/'signal_catalog.npz'))
  self.rec=np.memmap(self.d/'compact_records.bin',mode='r',dtype=DT);self.mapping=np.memmap(self.d/'compact_to_original.bin',mode='r',dtype='i8')
  self.pixel=recon(model)
 def evaluate(self,ids,node,serial):
  # A single template retains exactly its pinned 500-eV response.
  if len(ids)==1:
   ix=ids[0];r=self.rec[ix];f=int(r['flags'])
   return {'window':bool(f&1),'bgo_final':bool(f&2),'dual_final':bool(f&4),'bgo_pass':float(r['bgo'])<50,'plastic_pass':float(r['plastic'])<50,'energy':float(self.s['measured_total_keV'][ix-self.nb]) if ix>=self.nb else None}
  pixels={};noise={};ep=eb=0.
  for ix in ids:
   r=self.rec[ix];ep+=float(r['plastic']);eb+=float(r['bgo']);is_signal=ix>=self.nb;ar=self.s if is_signal else self.a;i=ix-self.nb if is_signal else int(self.mapping[ix])
   if i<0:continue
   start=int(ar['hit_start'][i]);end=start+int(ar['hit_count'][i])
   for h in range(start,end):
    code=int(ar['hit_code'][h]);e=float(ar['hit_energy_keV'][h]);pixels[code]=pixels.get(code,0.)+e
    # Common random numbers for the same pixel in overlaid and isolated signal.
    # Each grouped pixel still has one, not several, Gaussian noise contribution.
    if is_signal and code not in noise:noise[code]=float(ar['hit_measured_energy_keV'][h])-e
  hits=[]
  for code,e in sorted(pixels.items()):
   e+=noise.get(code,SIGMA*normal('three_stream',self.model,node,serial,code))
   if e>=.3:hits.append(PixelMeasurement(f'TP_L{code//100000}_{code%100000:05d}',e))
  total=math.fsum(h.energy_keV for h in hits);win=510.5<=total<511.5;active=eb<50
  keep=bool(self.pixel.classify(hits)[0]) if win and active else False
  return {'window':win,'bgo_pass':active,'plastic_pass':(ep<50 if not any(ix in (0,2) for ix in ids) else None),'bgo_final':win and active and keep,'dual_final':win and active and ep<50 and keep,'energy':total}
 def run(self,node):
  base=self.d/f'anchor_{node:03d}';j=json.loads(base.with_suffix('.json').read_text());bg_bgo=int(j['background_singleton_counts'][1]);bg_dual=int(j['background_singleton_counts'][2]);bg_pre=int(j['background_singleton_counts'][0]);bg_active=int(j['background_singleton_active_count']);c=Counter();rows=[];max_group=0;bg_delta_bgo=bg_delta_dual=0;signal_group_finals=0
  with base.with_suffix('.groups').open('rb') as f:
   while h:=f.read(12):
    serial,n=struct.unpack('<QI',h);ids=[];times=[];max_group=max(max_group,n)
    for _ in range(n):
     ix,t=struct.unpack('<Id',f.read(12));ids.append(ix);times.append(t)
    sig=[ix for ix in ids if ix>=self.nb]
    if not sig:
     result=self.evaluate(ids,node,serial);bg_bgo+=result['bgo_final'];bg_dual+=result['dual_final'];bg_pre+=result['window'];bg_active+=result['window'] and result['bgo_pass'];c['evaluated_background_multi_groups']+=1;continue
    result=self.evaluate(ids,node,serial);c['signal_groups']+=1;c['signal_events']+=len(sig);c['signal_multi_groups']+=n>1;c['multiple_signal_groups']+=len(sig)>1
    # Exact paired background-only realization in this same group: remove the
    # signal records and re-split at actual gaps >tau. This is a background
    # control, not a substituted signal estimator.
    chunks=[]
    for ix,t in zip(ids,times):
     if ix>=self.nb:continue
     if not chunks or t-chunks[-1][-1][1]>j['tau']:chunks.append([])
     chunks[-1].append((ix,t))
    control_bgo=control_dual=0
    for k,ch in enumerate(chunks):
     rr=self.evaluate([x[0] for x in ch],node,serial*100+k)
     control_bgo+=rr['bgo_final'];control_dual+=rr['dual_final'];bg_pre+=rr['window'];bg_active+=rr['window'] and rr['bgo_pass']
    bg_bgo+=control_bgo;bg_dual+=control_dual
    bg_delta_bgo+=int(result['bgo_final'])-control_bgo;bg_delta_dual+=int(result['dual_final'])-control_dual
    signal_group_finals+=int(result['bgo_final'])
    for ix in sig:
     i=ix-self.nb;iso=bool(self.s['narrow_final'][i]);pre=bool(self.s['narrow_pre'][i]);c['isolated_final']+=iso;c['isolated_window']+=pre
     c['overlaid_window']+=result['window'];c['overlaid_window_bgo_pass']+=result['window'] and result['bgo_pass'];c['overlaid_window_dual_pass']+=result['window'] and result['bgo_pass'] and result['plastic_pass']
     c['isolated_final_retained_bgo']+=iso and result['bgo_final'];c['isolated_final_retained_dual']+=iso and result['dual_final']
     c['window_loss']+=iso and not result['window'];c['bgo_loss_after_window']+=iso and result['window'] and not result['bgo_pass'];c['compton_loss_after_bgo']+=iso and result['window'] and result['bgo_pass'] and not result['bgo_final']
     c['bgo_reject_any']+=iso and not result['bgo_pass'];c['plastic_additional_reject_after_bgo']+=iso and result['bgo_pass'] and not result['plastic_pass'];c['gain_from_isolated_unselected']+=(not iso) and result['bgo_final']
     rows.append({'signal_index':i,'physical_time_s':times[ids.index(ix)],'group_serial':serial,'group_size':n,'signal_records_in_group':len(sig),'isolated_window':pre,'isolated_final':iso,**result,'background_only_bgo_final':control_bgo,'members':','.join(map(str,ids))})
  assert c['signal_events']==j['arrivals'][2] and c['signal_groups']==j['signal_groups']
  assert c['isolated_final']==c['isolated_final_retained_bgo']+c['window_loss']+c['bgo_loss_after_window']+c['compton_loss_after_bgo']
  assert c['multiple_signal_groups']==0,'Multiple focused events need group-count treatment in survival statistic.'
  assert bg_pre>=bg_active>=bg_bgo and bg_dual==bg_bgo
  c=dict(c);out={'model':self.model,'node':node,'day':node/4,'timeline':j,'counts':c,'retention_bgo':frac(c['isolated_final_retained_bgo'],c['isolated_final']),'retention_legacy_dual':frac(c['isolated_final_retained_dual'],c['isolated_final']),'active_bgo_retention_per_overlaid_window':frac(c['overlaid_window_bgo_pass'],c['overlaid_window']),'bgo_reject_fraction_of_isolated_selected':frac(c['bgo_reject_any'],c['isolated_final']),'background_pre_count':bg_pre,'background_active_count':bg_active,'background_bgo_final_count':bg_bgo,'background_dual_final_count':bg_dual,'net_signal_bgo_count':bg_delta_bgo,'net_signal_dual_count':bg_delta_dual,'signal_containing_selected_groups':signal_group_finals,'max_emitted_group_size':max_group,'truth_positions_used_in_reconstruction':False,'response':'One 500 eV FWHM Gaussian contribution per deposited pixel; common signal-pixel noise for the paired isolated/overlaid comparison.'}
  save(base.with_name(base.name+'_results.json'),out)
  with base.with_name(base.name+'_signal_events.csv').open('w') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  print(self.model,node,'ANALYZED',c,flush=True)
if __name__=='__main__':
 a=Analyzer(sys.argv[1]);nodes=list(map(int,sys.argv[2:])) or [0,20,40,60,80]
 for node in nodes:a.run(node)
