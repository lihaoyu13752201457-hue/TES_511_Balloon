import sys
sys.dont_write_bytecode=True
from pathlib import Path
import importlib.util,json,math
import numpy as np
O=Path(__file__).resolve().parents[1];W=O.parents[2];Q=O
spec=importlib.util.spec_from_file_location('styles',O/'code/retained_figure_styles.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
p.DATA=O/'data';p.V=p.read(O/'data/paper_values_500.json');p.P4=O;p.O=O;p.FIG=O/'figures';p.records=[]
old=p.read(W/'outputs/04_results_environments_conclusions/numeric_sync_20260920/data/parent_nuclide_figure_data.json');colors={}
for m in 'ab':colors.update(old[m]['colours_rgba'])
parent={}
for m in 'ab':
 d=p.V[m]['origin_nuclides'];keys=sorted(d,key=lambda k:-d[k])[:7]
 for k in keys:
  if k not in colors:colors[k]={'47106':'#17becf','81192':'#e377c2','81196':'#bcbd22','23047':'#393b79'}[k]
 parent[m]={'top7_ZA':keys,'rates_cps':[d[k] for k in keys],'other_cps':sum(v for k,v in d.items() if k not in keys),'colours_rgba':colors}
(O/'data/parent_nuclide_figure_data.json').write_text(json.dumps(parent,indent=2)+'\n')
save_original=p.save
changed={7,9,11,12,13,14,15,16}
def save(fig,num):
 if num in changed:save_original(fig,num)
 else:p.plt.close(fig)
p.save=save
p.donuts();p.geometry();p.spectra();p.environment()
p.defaults();fig,ax=p.plt.subplots(1,2,figsize=(6.55,3.4))
for i,m in enumerate('ab'):
 rs=p.rows(O/f'data/timeline_{m}_500/mission.csv');days=np.array([float(r['day']) for r in rs]);direct=np.array([float(r['background_direct_BGO_cps']) for r in rs]);err=np.array([float(r['direct_transport_sigma_cps']) for r in rs]);rec=[p.read(Q/f'data/{m}/anchor_{n:03d}_results.json') for n in [0,20,40,60,80]];ix=[0,20,40,60,80];count=np.array([r['background_bgo_final_count'] for r in rec]);T=np.array([r['timeline']['T'] for r in rec]);rate=count/T;e=np.sqrt(count)/T;r=rate/direct[ix]
 ax[0].plot(days,direct,color=p.C[i],ls=['-','--'][i],label=p.NAMES[m]);ax[0].fill_between(days,direct-err,direct+err,color=p.C[i],alpha=.13);ax[0].errorbar([0,5,10,15,20],rate,yerr=e,fmt=['o','s'][i],ms=4,mfc='white',color=p.C[i],capsize=2);ax[1].errorbar([0,5,10,15,20],r,yerr=e/direct[ix],fmt=['o-','s--'][i],ms=4,color=p.C[i],capsize=2,label=p.NAMES[m])
ax[0].set(ylabel='Selected background rate (cps)',title='(a) Direct rates and event-time samples');ax[1].set(ylabel=r'Background correction $C_{\mathrm{bg},g,r}$',title='(b) Simulated / direct rate');ax[1].axhline(1,c='grey',ls=':',lw=.9)
for a in ax:a.set_xlabel('Mission day');p.tidy(a);a.legend(frameon=False)
fig.subplots_adjust(left=.10,right=.98,top=.87,bottom=.17,wspace=.44);save(fig,14)
fig,ax=p.plt.subplots(1,2,figsize=(6.55,3.35))
for i,m in enumerate('ab'):
 rs=p.rows(Q/f'data/{m}/mission_81nodes.csv');d=np.array([float(r['day']) for r in rs]);bg=np.array([float(r['cumulative_background']) for r in rs]);ns=np.array([float(r['cumulative_signal']) for r in rs]);v=bg>0
 ax[0].plot(d[v],ns[v]/np.sqrt(bg[v]),color=p.C[i],ls=['-','--'][i],label=p.NAMES[m]);ax[1].plot(d[v],2.4e-4*3*np.sqrt(bg[v])/ns[v],color=p.C[i],ls=['-','--'][i],label=p.NAMES[m])
for z in [3,5]:ax[0].axhline(z,color='grey',ls=':',lw=.8)
ax[0].set(ylabel=r'Counting significance $N_s/\sqrt{N_b}$',title='(a) Reference-flux significance');ax[1].set(ylabel=r'3σ line flux (ph cm$^{-2}$ s$^{-1}$)',yscale='log',title='(b) Top-of-atmosphere threshold')
for a in ax:a.set_xlabel('On-source exposure (d)');a.set_xlim(0,20);p.tidy(a);a.legend(frameon=False)
fig.subplots_adjust(left=.10,right=.98,top=.87,bottom=.18,wspace=.49);save(fig,15)
(O/'validation/updated_figure_data.json').write_text(json.dumps(p.records,indent=2)+'\n');print('Updated figures',sorted(changed))
