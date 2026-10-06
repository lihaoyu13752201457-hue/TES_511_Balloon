"""Update publication plots from retained compact results, without transport."""
from pathlib import Path
import ast, csv, hashlib, importlib.util, json, math, os, shutil, sys
from collections import defaultdict
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parents[1];P=O.parent;W=O.parents[2];ROOT=W.parent
os.environ['MPLCONFIGDIR']=str(O/'validation/matplotlib')
os.environ['MPLBACKEND']='Agg'
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
DATA=O/'data';FIG=O/'figures';P4=O
read=lambda p:json.loads(Path(p).read_text())
def rows(p):
    with Path(p).open() as f:return list(csv.DictReader(f))
V=read(DATA/'paper_values_corrected_current_sample.json')
for m in 'ab':
    for name,key in [('origin_components','components'),('origin_families','families'),('origin_nuclides','nuclides')]:
        V[m][name]={k:x['rate'] for k,x in V[m]['origin_statistics'][key].items()}
C=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00','#56B4E9','#8B6B4A','#6A6A6A']
NAMES={'a':'Under-stage','b':'Lateral-chimney'}
STAGES=['pre_veto','combined_active_veto','compton_trajectory_veto']
records=[]
stylepath=P/'revision_20260921_AA_continuous/code/retained_figure_styles.py'
s=stylepath.read_text();tree=ast.parse(s)
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name in ['defaults','save','tidy','donut','donuts','spectra']:
        chunk=ast.get_source_segment(s,node)
        chunk=chunk.replace("'Near-field Bi liner'","'Bi passive shield'").replace("'Residual BGO shield'","'BGO shield'")
        exec(compile(chunk,str(stylepath),'exec'),globals())

previous=read(W/'outputs/04_results_environments_conclusions/numeric_sync_20260920/data/parent_nuclide_figure_data.json')
colors={}
for m in 'ab':colors.update(previous[m]['colours_rgba'])
parent={}
for m in 'ab':
    d=V[m]['origin_nuclides'];keys=sorted(d,key=lambda k:-d[k])[:7]
    for k in keys:
        if k not in colors:colors[k]={'47106':'#17becf','81192':'#e377c2','81196':'#bcbd22','23047':'#393b79'}.get(k,C[len(colors)%len(C)])
    parent[m]=dict(top7_ZA=keys,rates_cps=[d[k] for k in keys],other_cps=sum(v for k,v in d.items() if k not in keys),colours_rgba=colors)
    q=DATA/f'timeline_{m}_500';q.mkdir(exist_ok=True)
    shutil.copy2(DATA/m/'direct_spectra.csv',q/'direct_measured_energy_day15_0p25keV.csv')
(DATA/'parent_nuclide_figure_data.json').write_text(json.dumps(parent,indent=2)+'\n')
donuts();spectra()

# Reuse exactly the accepted functional geometry. Only markers are recomputed.
geo_code=P/'revision_20260921_pro_figures_markers/code/draw_figures.py'
sys.path.insert(0,str(geo_code.parent))
spec=importlib.util.spec_from_file_location('accepted_geometry',geo_code)
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':14.5,'mathtext.fontset':'dejavusans'})
fig,axes,geometry=g.canvas()
origins={m:rows(P/f'activation_manuscript_proposal_20260926/FIG10_NEW_POSITIONS_{m}.csv') for m in 'ab'}
totals=defaultdict(float)
for rr in origins.values():
    for r in rr:totals[r['source_parent_ZA']]+=float(r['day15_weight_cps'])
top=sorted(totals,key=totals.get,reverse=True)[:5]
symbols={29:'Cu',9:'F',47:'Ag'}
labels=[r'$^{'+str(int(k)%1000)+'}$'+symbols[int(k)//1000] for k in top]+['Other']
audit={}
for ax,m in zip(axes,'ab'):
    sites=defaultdict(set)
    for r in origins[m]:
        pt=(float(r['xprime_cm']),float(r['zprime_cm']))
        group=top.index(r['source_parent_ZA']) if r['source_parent_ZA'] in top else 5
        sites[pt].add(group)
    assert not [pt for pt in sites if not(g.VIEW[0]<=pt[0]<=g.VIEW[1] and g.VIEW[2]<=pt[1]<=g.VIEW[3])]
    for group in range(6):
        pts=np.array(sorted(pt for pt,groups in sites.items() if group in groups))
        if len(pts):ax.scatter(pts[:,0],pts[:,1],s=35,marker=g.MARKERS[group],c=g.POINT_COLORS[group],edgecolors='white',linewidths=.6,zorder=24)
    weights=np.array([float(r['day15_weight_cps']) for r in origins[m]])
    assert math.isclose(weights.sum(),V[m][STAGES[-1]]['delayed']['rate'],rel_tol=1e-10)
    audit[m]=dict(records=len(weights),unique_projected_positions=len(sites),category_markers=sum(map(len,sites.values())),coincident_multiple_categories=sum(len(x)>1 for x in sites.values()),rate_cps=float(weights.sum()))
handles=[Line2D([],[],ls='',marker=g.MARKERS[i],mfc=g.POINT_COLORS[i],mec='white',ms=7,label=labels[i]) for i in range(6)]
fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.54,.005),ncol=6,frameon=False,fontsize=14.5,handletextpad=.4,columnspacing=1.2)
save(fig,9)
(O/'validation/figure10_data.json').write_text(json.dumps({'models':audit,'top_parent_ZA':top,'geometry_source':str(geo_code),'geometry_unchanged':True,'rate_heatmap':False,'jitter':False},indent=2)+'\n')

defaults()
fig,ax=plt.subplots(1,2,figsize=(6.55,3.4))
for i,m in enumerate('ab'):
    rs=rows(DATA/m/'mission_81nodes.csv');days=np.array([float(x['day']) for x in rs])
    direct=np.array([float(x['background_direct_BGO_cps']) for x in rs]);err=np.array([float(x['direct_transport_sigma_cps']) for x in rs])
    rr=[read(DATA/m/f'anchor_{n:03d}_results.json') for n in [0,20,40,60,80]]
    count=np.array([x['background_bgo_final_count'] for x in rr]);T=np.array([x['timeline']['T'] for x in rr]);rate=count/T;e=np.sqrt(count)/T;ix=[0,20,40,60,80]
    ax[0].plot(days,direct,color=C[i],ls=['-','--'][i],label=NAMES[m]);ax[0].fill_between(days,direct-err,direct+err,color=C[i],alpha=.13)
    ax[0].errorbar([0,5,10,15,20],rate,yerr=e,fmt=['o','s'][i],ms=4,mfc='white',color=C[i],capsize=2)
    ax[1].errorbar([0,5,10,15,20],rate/direct[ix],yerr=e/direct[ix],fmt=['o-','s--'][i],ms=4,color=C[i],capsize=2,label=NAMES[m])
ax[0].set(ylabel='Selected background rate (cps)',title='(a) Analytic and simulated rates')
ax[1].set(ylabel=r'Background correction $C_{\mathrm{bg},g,r}$',title='(b) Simulated / analytic rate');ax[1].axhline(1,c='grey',ls=':',lw=.9)
for a in ax:a.set_xlabel('Mission day');tidy(a);a.legend(frameon=False)
fig.subplots_adjust(left=.10,right=.98,top=.87,bottom=.17,wspace=.44);save(fig,14)
fig,ax=plt.subplots(1,2,figsize=(6.55,3.35))
for i,m in enumerate('ab'):
    rs=rows(DATA/m/'mission_81nodes.csv');d=np.array([float(r['day']) for r in rs]);bg=np.array([float(r['cumulative_background']) for r in rs]);ns=np.array([float(r['cumulative_signal']) for r in rs]);v=bg>0
    ax[0].plot(d[v],ns[v]/np.sqrt(bg[v]),color=C[i],ls=['-','--'][i],label=NAMES[m]);ax[1].plot(d[v],2.4e-4*3*np.sqrt(bg[v])/ns[v],color=C[i],ls=['-','--'][i],label=NAMES[m])
for z in [3,5]:ax[0].axhline(z,color='grey',ls=':',lw=.8)
ax[0].set(ylabel=r'Counting significance $N_s/\sqrt{N_b}$',title='(a) Reference-flux significance')
ax[1].set(ylabel=r'3σ line flux (ph cm$^{-2}$ s$^{-1}$)',yscale='log',title='(b) Top-of-atmosphere threshold')
for a in ax:a.set_xlabel('On-source exposure (d)');a.set_xlim(0,20);tidy(a);a.legend(frameon=False)
fig.subplots_adjust(left=.10,right=.98,top=.87,bottom=.18,wspace=.49);save(fig,15)
(O/'validation/updated_figure_data.json').write_text(json.dumps(records,indent=2)+'\n')
print('Updated Figures 7, 10–16 from the corrected compact results.')
