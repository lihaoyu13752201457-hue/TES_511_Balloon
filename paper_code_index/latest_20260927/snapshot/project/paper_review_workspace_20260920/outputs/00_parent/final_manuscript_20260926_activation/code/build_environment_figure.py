from pathlib import Path
import os,sys,importlib.util,json,csv
O=Path(__file__).resolve().parents[1];W=O.parents[2];P=W.parent;A=O.parent/'antarctic_environment_20260924'
sys.dont_write_bytecode=True
os.environ['MPLCONFIGDIR']=str(O/'validation/matplotlib');os.environ['MPLBACKEND']='Agg'
import numpy as np
import matplotlib.pyplot as plt
p=P/'engineering/geometry_optimization_20260815/71_m05_sh3_environment_screening_20260830/code/build_environment_screening.py'
spec=importlib.util.spec_from_file_location('environment_figure_only',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
models=m.load_models_module().CompleteL2Models()
report=json.loads((O/'data/environment_results.json').read_text());rr=list(csv.DictReader((A/'data/antarctic_native.csv').open()))
a='antarctic';envs=[m.ENVIRONMENTS[0],a,*m.ENVIRONMENTS[1:]]
colors={**m.COLOR,a:'#7B3294'};styles={**m.STYLE,a:(0,(4,1.5))}
labels={**m.LABEL_EN,'balloon_38km':'Balloon reference',a:'Antarctic balloon','lunar_surface_proxy':'Lunar surface','leo530_quiet_proxy':'530 km LEO (non-SAA)','sun_earth_l2_solar_max_2014':'L2, solar maximum','sun_earth_l2_quiet_1au_proxy':'L2, solar minimum'}
ticks=['Balloon\nreference','Antarctic\nballoon','LEO\n(non-SAA)','Lunar\nsurface','L2\nsolar max.','L2\nsolar min.']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.labelsize':9,'axes.titlesize':10,'xtick.labelsize':8.5,'ytick.labelsize':8.5,'legend.fontsize':8.5,'mathtext.fontset':'dejavusans','pdf.fonttype':42})
fig=plt.figure(figsize=(7.0,6.3));gs=fig.add_gridspec(3,2,height_ratios=[2.3,.48,1.8]);axes=[fig.add_subplot(gs[0,0]),fig.add_subplot(gs[0,1]),fig.add_subplot(gs[2,:])];leg=fig.add_subplot(gs[1,:]);leg.axis('off')
for ax,f,x,scale,key in [(axes[0],'gamma',np.logspace(-1.2,5,700),1e3,'prompt/gamma'),(axes[1],'p',np.logspace(-2,3,700),1e6,'delayed/p')]:
 native=[r for r in rr if r['family']==f];xx=np.array([float(r['energy_keV_total']) for r in native]);yy=np.array([float(r['differential_flux_cm2_s_keV']) for r in native])
 for e in envs:
  E=x*scale
  y=np.interp(E,xx,yy,left=0,right=0) if e==a else np.array([models.target_flux(e,f,z) for z in E])
  ax.plot(x,np.where(y>0,E*y,np.nan),color=colors[e],ls=styles[e],lw=1.25,label=labels[e])
 band=next(r for r in report['primary_energy_bands'] if r['stream']+'/'+r['family']==key);lo,hi=band['energy_p10_MeV'],band['energy_p90_MeV'];bscale=1 if f=='gamma' else .001
 ax.axvspan(lo*bscale,hi*bscale,color='#E69F00',alpha=.14)
 ax.set(xscale='log',yscale='log');ax.text(.025,.025,f'{lo*bscale:.3g}–{hi*bscale:.3g} '+('MeV' if f=='gamma' else 'GeV'),transform=ax.transAxes,fontsize=8.5)
axes[0].set(xlim=(.07,1e5),ylim=(1e-10,3e3),xlabel='Primary photon energy (MeV)',ylabel=r'$E\,d\Phi/dE$ (cm$^{-2}$ s$^{-1}$)',title='(a) Photon fields')
axes[1].set(xlim=(.01,1e3),ylim=(1e-9,3e3),xlabel='Primary proton energy (GeV)',ylabel=r'$E\,d\Phi/dE$ (cm$^{-2}$ s$^{-1}$)',title='(b) Proton fields')
leg.legend(*axes[0].get_legend_handles_labels(),loc='center',ncol=3,frameon=False,handlelength=2,columnspacing=1.2)
by={r['environment']:r['F3'] for r in report['screening']};vals=[]
for i,e in enumerate(envs):
 y=by[e]*1e5;vals.append(y);axes[2].scatter(i,y,s=42,facecolor='white',edgecolor=colors[e],linewidth=1.4,zorder=3);axes[2].text(i,y+.25,f'{y:.2f}',ha='center',fontsize=9,color=colors[e])
axes[2].axhline(vals[0],color='grey',ls='--',lw=.8);axes[2].plot([4,5],vals[-2:],color='grey',lw=1)
axes[2].set(xticks=range(6),xticklabels=ticks,ylim=(0,8.9),xlim=(-.5,5.5),ylabel=r'3σ flux ($10^{-5}$ ph cm$^{-2}$ s$^{-1}$)',title='(c) Estimated minimum detectable line flux (20 d)')
for ax in axes:
 ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.18);ax.set_axisbelow(True)
axes[2].grid(False,axis='x')
fig.subplots_adjust(left=.10,right=.98,top=.95,bottom=.09,wspace=.40,hspace=.46)
fig.savefig(O/'figures/fig16.pdf',bbox_inches='tight',pad_inches=.07);fig.savefig(O/'validation/figure17.png',dpi=170,bbox_inches='tight',pad_inches=.07)
(O/'data/figure17_values.json').write_text(json.dumps({'environments':envs,'F3_units_1em5':vals,'reference_results_source':str(O/'data/environment_results.json'),'antarctic_results_source':str(O/'data/environment_results.json')},indent=2)+'\n')
print('Figure17 generated; F3 x1e5:',vals)
