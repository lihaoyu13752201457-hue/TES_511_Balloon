from common import *
from analyze import frac
from collections import Counter

def trap(y):return float(np.trapezoid(y,dx=21600))
def cross(days,z,q):
 for i in range(1,len(z)):
  if z[i]>=q:return float(days[i-1]+(days[i]-days[i-1])*(q-z[i-1])/(z[i]-z[i-1]))
 return None

def main():
 days=np.arange(81)/4;nodes=[0,20,40,60,80];interp=np.column_stack([np.interp(days,np.array(nodes)/4,np.eye(5)[j]) for j in range(5)])
 result={'status':'COMPLETE','three_physical_Poisson_streams':True,'continuous_cone_disk':True,'new_transport':False,'plastic':False,'models':{}};anchors=[];checks=[]
 for m in ['a','b']:
  d=O/'data'/m;rr=[read(d/f'anchor_{n:03d}_results.json') for n in nodes];direct=rows(d/'direct_81nodes.csv');count=Counter()
  for r in rr:count.update(r['counts'])
  Bdir=np.array([float(r['background_bgo_final_rate']) for r in direct]);Sdir=np.array([float(r['isolated_signal_final_rate']) for r in direct])
  rho=np.array([r['background_bgo_final_count']/r['timeline']['T']/Bdir[n] for n,r in zip(nodes,rr)]);eta=np.array([r['retention_bgo']['value'] for r in rr]);net=np.array([r['net_signal_bgo_count']/r['counts']['isolated_final'] for r in rr]);br=interp@rho;et=interp@eta;B=Bdir*br;S=Sdir*et
  cum=lambda y:np.r_[0,np.cumsum((y[:-1]+y[1:])/2*21600)]
  cb=cum(B);cs=cum(S);csnet=cum(Sdir*(interp@net));z=np.divide(cs,np.sqrt(cb),out=np.zeros(81),where=cb>0)
  cat=dict(np.load(d/'category_sums.npz'));q1=cat['q1'];q2=cat['q2'];scales=cat['scales'];reg=read(d/'category_registry.json')['categories'];assert np.allclose(scales@q1,Bdir,rtol=1e-11)
  tw=np.full(81,21600.);tw[[0,-1]]=10800.;coeff=(tw*br)@scales;varbt=float(np.sum(q2*coeff**2));varbp=vareta=0.;zs=[]
  for j,(n,r) in enumerate(zip(nodes,rr)):
   T=r['timeline']['T'];nb=r['background_bgo_final_count'];N=r['counts']['isolated_final'];k=r['counts']['isolated_final_retained_bgo']
   cbj=trap(Bdir*interp[:,j])/Bdir[n]/T;varbp+=cbj**2*nb;csj=trap(Sdir*interp[:,j]);vareta+=csj**2*(k+.5)*(N-k+.5)/((N+1)**2*(N+2))
   zz=(nb/T-Bdir[n])/(math.sqrt(nb)/T);zs.append(zz)
   anchors.append({'model':m,'day':n/4,'T_s':T,'signal_arrivals':r['counts']['signal_events'],'isolated_selected':N,'retained_bgo':k,'eta':eta[j],'rho':rho[j],'background_pre':r['background_pre_count'],'background_active':r['background_active_count'],'background_final':nb,'direct_background_cps':Bdir[n],'direct_vs_timeline_z':zz})
   checks.append({'model':m,'node':n,'Poisson_z':[(v-rate*T)/math.sqrt(rate*T) if rate else 0 for v,rate in zip(r['timeline']['arrivals'],r['timeline']['rates'])],'signal_ancestry_closed':True})
  sig=read(d/'signal_summary.json')['conversion'];varst=(cs[-1]*sig['combined_optical_detector_SE_cm2']/sig['value_cm2'])**2
  F3=FREF*3/z[-1];F3se=F3*math.sqrt((varbt+varbp)/(4*cb[-1]**2)+(varst+vareta)/cs[-1]**2)
  components={name:float(np.dot(q1*np.array([c['component']==name for c in reg]),coeff)) for name in ['gamma_continuum','other']};assert np.isclose(sum(components.values()),cb[-1])
  mission=[{'day':days[i],'signal_isolated_rate_cps':Sdir[i],'signal_retention':et[i],'signal_final_rate_cps':S[i],'background_direct_BGO_cps':Bdir[i],'background_correction':br[i],'background_final_cps':B[i],'cumulative_signal':cs[i],'cumulative_background':cb[i],'Z':z[i],'F3_ph_cm2_s':FREF*3/z[i] if i else '', 'net_signal_cumulative_crosscheck':csnet[i],'direct_transport_sigma_cps':float(direct[i]['direct_transport_sigma_cps'])} for i in range(81)]
  write(d/'mission_81nodes.csv',mission)
  result['models'][m]={'physical_model':'AA' if m=='a' else 'B','display_name':'Under-stage' if m=='a' else 'Lateral-chimney','pooled_counts':dict(count),'pooled_retention_bgo':frac(count['isolated_final_retained_bgo'],count['isolated_final']),'pooled_active_BGO_retention':frac(count['overlaid_window_bgo_pass'],count['overlaid_window']),'eta_range':[float(eta.min()),float(eta.max())],'rho_range':[float(rho.min()),float(rho.max())],'max_direct_vs_timeline_z':float(max(map(abs,zs))),'day15':{'eta_bgo':float(eta[3]),'BGO_retention':rr[3]['active_bgo_retention_per_overlaid_window'],'signal_final_rate_cps':S[60],'direct_background_BGO_cps':Bdir[60],'timeline_background_BGO_cps':B[60]},'mission_20day':{'Ns':cs[-1],'Nb':cb[-1],'Z':z[-1],'F3':F3,'F5':F3*5/3,'F3_MC_SE_approx':F3se,'F5_MC_SE_approx':F3se*5/3,'T3_days':cross(days,z,3),'T5_days':cross(days,z,5),'Ns_net_on_minus_off':csnet[-1],'background_component_counts':components},'uncertainty':{'background_correlated_transport_SE_counts':math.sqrt(varbt),'background_timeline_SE_counts':math.sqrt(varbp),'signal_optical_plus_detector_SE_counts':math.sqrt(varst),'signal_retention_SE_counts':math.sqrt(vareta),'retention_variance':'Jeffreys beta variance; empirical fraction central estimate; no environment/geometry systematics'}}
 a=result['models']['a']['mission_20day'];b=result['models']['b']['mission_20day'];result['ratios']={'Nb_lateral_over_under':b['Nb']/a['Nb'],'Ns_lateral_over_under':b['Ns']/a['Ns'],'F3_under_over_lateral':a['F3']/b['F3']}
 save(O/'data/RESULTS.json',result);write(O/'data/ANCHORS.csv',anchors);save(O/'validation/timeline_checks.json',checks)
 assert max(abs(z) for r in checks for z in r['Poisson_z'])<6
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
