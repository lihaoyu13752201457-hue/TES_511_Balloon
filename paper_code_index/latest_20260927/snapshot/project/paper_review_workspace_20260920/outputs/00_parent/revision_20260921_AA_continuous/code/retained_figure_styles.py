"""Publication graphics from compact retained tables; no particle simulation."""
import ast,csv,hashlib,importlib.util,json,math,os,re,sys,types
from pathlib import Path
O=Path(__file__).resolve().parents[1];W=O.parents[2];ROOT=W.parent
sys.dont_write_bytecode=True
os.environ['MPLCONFIGDIR']=str(O/'validation/matplotlib');os.environ['MPLBACKEND']='Agg'
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.text import Text
from matplotlib.patches import FancyBboxPatch,Rectangle,Patch
from matplotlib.lines import Line2D
sys.path.insert(0,str(W/'outputs/00_parent/latest_manuscript_audit_20260920/_deps'))
import pymupdf as fitz
DATA=W/'outputs/03_mission_baseline_design/numeric_sync_20260920/data'
P4=W/'outputs/04_results_environments_conclusions/numeric_sync_20260920'
FIG=O/'figures'
V=json.loads((DATA/'paper_values_500.json').read_text())
C=['#0072B2','#D55E00','#009E73','#CC79A7','#E69F00','#56B4E9','#8B6B4A','#6A6A6A']
NAMES={'a':'Under-stage','b':'Lateral-chimney'}
STAGES=['pre_veto','combined_active_veto','compton_trajectory_veto']
records=[]
def rows(p):
    with Path(p).open() as f:return list(csv.DictReader(f))
def read(p):return json.loads(Path(p).read_text())
def funcs(p):
    s=Path(p).read_text()
    return {n.name:ast.get_source_segment(s,n) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def defaults():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.labelsize':9,'axes.titlesize':10,'xtick.labelsize':8.5,'ytick.labelsize':8.5,'legend.fontsize':8.5,'mathtext.fontset':'dejavusans','pdf.fonttype':42,'savefig.facecolor':'white'})
def save(fig,number):
    fig.savefig(FIG/f'fig{number:02}.pdf',bbox_inches='tight',pad_inches=.07)
    fig.savefig(O/'validation'/f'fig{number:02}.png',dpi=150,bbox_inches='tight',pad_inches=.07)
    plt.close(fig)
def tidy(ax):
    ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.18);ax.set_axisbelow(True)

def cryostat():
    p=W/'inputs/latest/code/build_figures.py';s=p.read_text()
    s=s[:s.index('def main():')]
    s=s.replace('ROOT = HERE.parents[2]',f'ROOT = Path({str(ROOT)!r})')
    s=s.replace("OUT = HERE / 'figures/revised_r5'",f'OUT = Path({str(FIG)!r})')
    s=s.replace("'Reference cryostat: model A'","'Under-stage cryostat'")
    for line in ["    shell_section(a,29,30,-26.5,48,C['plastic'],'#F0EDF5',cap=1,port=False,lw=.75,z=1)\n", "    rect(a,-30,48,60,1,'#F0EDF5',C['plastic'],lw=.75,z=1)\n", "    label(a,'Plastic',(29.5,46),(20,52),ha='center',size=8.4)\n"]:
        assert line in s;s=s.replace(line,'')
    s=s.replace('for j,(x,txt) in enumerate(zip(positions,labels)):',"for j,(x,txt) in enumerate(zip(positions,labels)):\n        if txt=='Plastic':continue")
    g={'__file__':str(p)};exec(compile(s,str(p),'exec'),g)
    def output(fig,name):
        for t in fig.findobj(Text):
            if t.get_fontsize()<8.8:t.set_fontsize(8.8)
        save(fig,2)
    g['save']=output;g['cryostat_figure']()

def workflow():
    p=Path('/home/ubuntu/paper_new/figures/manuscript/fig02_workflow_en_threebranch_20260830.pdf')
    doc=fitz.open(p);page=doc[0];xref=page.get_contents()[0];raw=doc.xref_stream(xref).decode('latin1')
    a=raw.index(' q  0.47247 0.51718 0.56189 RG  0.81694 w')
    b=raw.index(' q  0.31483 0.34541 0.37599 RG  0.94646 w',a)
    old=raw[a:b]
    new=' q  0.31483 0.34541 0.37599 RG  0.94646 w  [] 0 d 157.19356 -89.29227 m 166.0 -89.29227 l 167.657 -89.29227 169.0 -87.94927 169.0 -86.29227 c 169.0 -76.1348 l 169.0 -74.4778 170.343 -73.1348 172.0 -73.1348 c S q 0.31483 0.34541 0.37599 rg 1 0 0 1 168.38307 -73.1348 cm q [] 0 d 0 j 7.37239 0 m 1.58377 2.06886 l 3.4976 0 l 1.58377 -2.06886 l h B Q Q Q '
    doc.update_stream(xref,(raw[:a]+new+raw[b:]).encode('latin1'))
    # Keep every line and every box of the requested diagram; harmonize fonts.
    spans=[]
    for block in page.get_text('dict')['blocks']:
        if block['type']!=0:continue
        for line in block['lines']:
            t=dict(line['spans'][0]);t['text']=''.join(x['text'] for x in line['spans']);t['bbox']=line['bbox'];spans.append(t)
    boxes=[d['rect'] for d in page.get_drawings() if d['fill'] and d['rect'].height>15]
    from matplotlib import font_manager
    normal=font_manager.findfont('DejaVu Sans');bold=font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans',weight='bold'))
    for t in spans:page.add_redact_annot(fitz.Rect(t['bbox']),fill=False,cross_out=False)
    page.apply_redactions(images=0,graphics=0,text=0)
    page.insert_font(fontname='UnifiedSans',fontfile=normal);page.insert_font(fontname='UnifiedSansBold',fontfile=bold)
    fontobjects={False:fitz.Font(fontfile=normal),True:fitz.Font(fontfile=bold)}
    for t in spans:
        isbold='Bold' in t['font'];font=fontobjects[isbold];size=t['size']
        if t['color']==16777215:size=max(size,10.42)
        w=font.text_length(t['text'],fontsize=size);box=fitz.Rect(t['bbox'])
        centre=fitz.Point((box.x0+box.x1)/2,(box.y0+box.y1)/2)
        containers=[r for r in boxes if centre in r]
        available=min(containers,key=lambda r:r.get_area()).width-4 if containers else box.width
        stretch=min(1,available/w)
        x=(box.x0+box.x1-w*stretch)/2
        col=t['color'];color=((col>>16&255)/255,(col>>8&255)/255,(col&255)/255)
        origin=fitz.Point(x,t['origin'][1])
        page.insert_text(origin,t['text'],fontsize=size,fontname='UnifiedSansBold' if isbold else 'UnifiedSans',color=color,morph=(origin,fitz.Matrix(stretch,1)))
    doc.save(FIG/'fig03.pdf',garbage=4,deflate=True)
    page.get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(str(O/'validation/fig03.png'))
    (O/'validation/workflow_edit.json').write_text(json.dumps({'source':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'arrow':'Independent Laue-optics mass model → Laue-optics transport','arrow_old_pdf_commands':old,'arrow_new_pdf_commands':new,'text_lines_before':[t['text'] for t in spans],'text_lines_after':page.get_text().splitlines(),'content_and_layout_preserved':True,'font_substitution':'Noto Sans CJK → DejaVu Sans; original line breaks, centres and baselines retained'},ensure_ascii=False,indent=2))

def source_flux():
    defaults();data=rows(ROOT/'expacs_fullsphere_20bin_sources/manifest.csv')
    fam=['gamma','n','eminus','eplus','p','alpha','muminus','muplus'];labels=[r'$\gamma$',r'$n$',r'$e^-$',r'$e^+$',r'$p$',r'$\alpha$',r'$\mu^-$',r'$\mu^+$']
    fig,ax=plt.subplots(1,2,figsize=(6.55,3.05),gridspec_kw={'width_ratios':[1,1.25]})
    for i,(f,l) in enumerate(zip(fam,labels)):
        rs=sorted([r for r in data if r['particle']==f],key=lambda r:int(r['bin_id']));y=np.array([float(r['flux_cm2_s']) for r in rs]);x=[float(r['theta_mid_deg']) for r in rs]
        ax[0].bar(i,sum(y[:10]),color=C[0],label='Down-going' if i==0 else None);ax[0].bar(i,sum(y[10:]),bottom=sum(y[:10]),color=C[1],label='Up-going' if i==0 else None)
        ax[1].plot(x,y,color=C[i],marker=['o','s','^','v','D','P','<','>'][i],markersize=3,lw=1,label=l)
    ax[0].set(xticks=range(8),xticklabels=labels,yscale='log',ylabel=r'Flux (cm$^{-2}$ s$^{-1}$)',title='(a) Hemisphere totals');ax[0].legend(frameon=False,fontsize=8.5)
    ax[1].set(yscale='log',xlabel=r'Zenith-bin centre $\theta$ (deg)',ylabel=r'Bin flux (cm$^{-2}$ s$^{-1}$)',title=r'(b) Twenty equal-$\mu$ bins');ax[1].axvline(90,color='grey',ls='--',lw=.8)
    ax[1].legend(loc='lower center',bbox_to_anchor=(.5,1.16),ncol=4,frameon=False,columnspacing=.65,handlelength=1.3)
    for a in ax:tidy(a)
    fig.subplots_adjust(left=.10,right=.98,wspace=.44,top=.74,bottom=.17);save(fig,4)

def poisson():
    defaults();fig,ax=plt.subplots(figsize=(6.65,5.65));ax.set(xlim=(0,10),ylim=(0,9));ax.axis('off')
    def box(x,y,w,h,text,color='#576570',fc='#F6F8FA'):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.08',ec=color,fc=fc,lw=.9));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=9)
    def arrow(a,b):ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'#52606B','lw':1})
    ax.text(0,8.8,'(a) Rate normalization and independent sampling',weight='bold',fontsize=10)
    box(.1,7.2,3.5,1.0,'Prompt families\nPer-record rates '+r'$r_{km}$',C[0]);box(.1,5.8,3.5,1.0,'Delayed families and parents\nPer-record rates '+r'$r_{km}$',C[1])
    box(4.8,6.3,4.6,1.5,r'$R_k=\sum_m r_{km}$'+'\n'+r'$N_k\sim\mathrm{Pois}(R_kT)$'+'\nRecords sampled with weights '+r'$r_{km}/R_k$'+'\nArrival times uniform in [0, T]')
    arrow((3.7,7.7),(4.7,7.35));arrow((3.7,6.3),(4.7,6.7))
    ax.text(0,5.3,'(b) Merge arrivals and group before response',weight='bold',fontsize=10)
    ax.annotate('',xy=(9.5,4.65),xytext=(.3,4.65),arrowprops={'arrowstyle':'->','lw':1})
    for x,c in [(1,C[0]),(2.3,C[1]),(2.65,C[0]),(4.1,C[0]),(6.4,C[1]),(6.7,C[0]),(7.05,C[1]),(8.45,C[0])]:ax.plot([x,x],[4.45,4.85],c=c,lw=2)
    for x,w in [(2.12,.72),(6.22,1.04)]:ax.add_patch(Rectangle((x,4.32),w,.67,fc='#E7E9EC',ec='#8D979E',alpha=.45))
    ax.text(5,3.9,r'Consecutive gaps $\leq\tau=1\,\mu$s link one group',ha='center',fontsize=9)
    box(.7,2.92,8.2,.55,'Pixel sums → 500 eV response → energy window → active veto → Compton test')
    arrow((5,3.73),(5,3.53))
    ax.text(0,2.34,'(c) Conditional weak-signal survival',weight='bold',fontsize=10)
    box(.1,.66,3.1,1.25,'Sample neighbouring\nbackground chains\non both sides',C[2]);arrow((3.3,1.28),(4.05,1.28))
    box(4.15,.53,5.35,1.54,'Reject if any neighbour deposits energy in TES\nor the active-shield sum reaches threshold\n'+r'$\widehat\eta_{g,r}=N_{\rm pass}/N_{\rm probe}$',C[2])
    ax.text(5,.10,'The signal probe is separate from the background Poisson streams.',ha='center',fontsize=8.8)
    fig.tight_layout(pad=.1);save(fig,5)

def geometry():
    # Extract only the reviewed plot function. Do not execute document writers.
    p=W/'outputs/03_mission_baseline_design/revision_20260920_bgo_zh/code/build_english.py';s=funcs(p)['redraw_figures']
    a=s.index('    # Materialize');b=s.index("    geo=",a);s=s[:a]+"    target=FIG\n"+s[b:]
    s=s.replace("src/f'data/delayed_origins_{m}_500.csv'","DATA/f'delayed_origins_{m}_500.csv'").replace("src/'data/paper_values_500.json'","DATA/'paper_values_500.json'")
    s=s.replace("comp['w_bottom_plate']+comp['bpe_bgo_shielding']","comp.get('w_bottom_plate',0)+comp.get('bpe_bgo_shielding',0)+comp.get('other_detector_bay',0)").replace("symbols={6:'C'","symbols={47:'Ag',81:'Tl',23:'V',6:'C'")
    a=s.index('    def save(');b=s.index('    def call(',a)
    s=s[:a]+"    def save(fig,name):\n        if name=='fig_origins_a':plt.close(fig);return\n        globals()['save'](fig,{'fig_geometry_origins_500':8,'fig_activation_positions_500':9}[name])\n"+s[b:]
    s=s.replace("'Under-stage A'","'Under-stage'").replace("'Lateral-chimney B'","'Lateral-chimney'")
    s=s.replace("('A' if m=='a' else 'B')","('Under-stage' if m=='a' else 'Lateral-chimney')")
    s=s.replace("' — TES neighbourhood'","'\\nTES neighbourhood'").replace("' — focal plane'","'\\nfocal plane'").replace("' — overview'","'\\noverview'").replace("' — parent sites'","'\\nparent sites'")
    s=s.replace("'xtick.labelsize':9,'ytick.labelsize':9","'xtick.labelsize':10.8,'ytick.labelsize':10.8")
    s=s.replace('(-49,10)','(-50,10)').replace('(-35,10)','(-33.8,10)')
    s=s.replace('fontsize=8.8','fontsize=10.5').replace('size=9.8','size=10.8').replace('fontsize=10,','fontsize=10.8,')
    g=dict(globals(),HERE=O);exec(compile(s,str(p),'exec'),g);info=g['redraw_figures']()
    (O/'validation/geometry_figure_data.json').write_text(json.dumps(info,indent=2))

def donut(ax,values,labels,colors,title):
    total=sum(values);wedges,_=ax.pie(values,colors=colors,startangle=90,counterclock=False,wedgeprops={'width':.34,'edgecolor':'white','linewidth':.7})
    ax.text(0,.08,f'{total*1e3:.3f}',ha='center',va='center',fontsize=11);ax.text(0,-.17,r'$\times10^{-3}$ cps',ha='center',va='center',fontsize=9.5)
    ax.set_title(title,fontsize=10,pad=10)
    ax.legend(wedges,[f'{l} ({100*v/total:.2f}%)' for l,v in zip(labels,values)],loc='upper center',bbox_to_anchor=(.5,-.05),frameon=False,fontsize=8.6,handlelength=1.2,labelspacing=.4)
def donuts():
    defaults();styles=read(ROOT/'core_md/balloon511_ea_latex_drafts/meeting_revision_20260918_mxc/data/donut_styles.json')
    for m,n in [('a',7),('b',10)]:
        st=styles[m];comp=V[m]['origin_components'];fam=V[m]['origin_families']
        if m=='a':
            keys=st['COMPONENT_ORDER'][:6];cv=[comp.get(k,0) for k in keys]+[comp.get('w_bottom_plate',0)+comp.get('bpe_bgo_shielding',0)+comp.get('other_detector_bay',0)]
            cl=['MXC Cu cold plate','TES Cu support panels','Al cryostat / shields','TES Cu heat-sink ring','Near-field Bi liner','Remaining DR hardware','Other detector-bay / shields'];cc=st['COMPONENT_COLORS'][:6]+['#80858A']
        else:
            cv=[comp[k] for k in st['COMPONENT_ORDER']]
            cl=['TES Cu support panels','TES Cu heat-sink ring','Al chimney / cryostat','W focal-plane frame','TES bottom Cu spokes','MXC Cu cold plate','Cold link: Cu finger / SS rod','TES Ta pixels','Residual BGO shield'];cc=st['COMPONENT_COLORS']
        fv=[fam.get(k,0) if k not in ['leptons','electron_positron'] else sum(fam.get(f,0) for f in ['eminus','eplus','muminus','muplus']) for k in st['FAMILY_ORDER']]
        assert math.isclose(sum(cv),sum(comp.values()),rel_tol=1e-12)
        fig,ax=plt.subplots(1,2,figsize=(6.55,4.8));fig.subplots_adjust(top=.91,bottom=.43,wspace=.27)
        donut(ax[0],cv,cl,cc,'(a) Production component');donut(ax[1],fv,st['FAMILY_LABELS'],st['FAMILY_COLORS'],'(b) Initiating particle');save(fig,n)
        records.append({'figure':n,'component_values':cv,'labels':cl,'colors':cc,'family_values':fv})
    parent=read(P4/'data/parent_nuclide_figure_data.json');symbols={23:'V',47:'Ag',81:'Tl',57:'La',6:'C',7:'N',8:'O',9:'F',12:'Mg',13:'Al',21:'Sc',24:'Cr',25:'Mn',26:'Fe',27:'Co',29:'Cu',30:'Zn',32:'Ge',36:'Kr',42:'Mo',62:'Sm',66:'Dy',68:'Er',71:'Lu',73:'Ta',74:'W',75:'Re',79:'Au',82:'Pb',83:'Bi',84:'Po'}
    fig,ax=plt.subplots(1,2,figsize=(6.55,4.5));fig.subplots_adjust(top=.90,bottom=.38,wspace=.27)
    for i,m in enumerate('ab'):
        p=parent[m];keys=p['top7_ZA'];vals=p['rates_cps']+[p['other_cps']];labs=[rf'$^{{{int(k)%1000}}}${symbols[int(k)//1000]}' for k in keys]+['Other']
        cols=[p['colours_rgba'][k] for k in keys]+['#AAAAAA'];donut(ax[i],vals,labs,cols,f'({chr(97+i)}) {NAMES[m]}')
    save(fig,11)
    fig,ax=plt.subplots(1,2,figsize=(6.55,3.4));fig.subplots_adjust(top=.89,bottom=.32,wspace=.27)
    for i,m in enumerate('ab'):donut(ax[i],[V[m][STAGES[-1]][k]['rate'] for k in ['gamma','delayed','non_gamma']],['Atmospheric γ','Delayed activation','Non-γ prompt'],C[:3],f'({chr(97+i)}) {NAMES[m]}')
    save(fig,12)

def spectra():
    defaults();fig,ax=plt.subplots(1,2,figsize=(6.55,3.3),sharey=True)
    allrecords=[];floor=1e-5;ceiling=1e2
    for k,m in enumerate('ab'):
        data=rows(DATA/f'timeline_{m}_500/direct_measured_energy_day15_0p25keV.csv')
        for i,stage in enumerate(STAGES):
            rs=[r for r in data if r['stage']==stage and r['stream']=='all' and r['component']=='all' and 508<=float(r['energy_low_keV'])<514];rs.sort(key=lambda r:float(r['energy_low_keV']))
            x=np.array([float(r['energy_low_keV'])+.125 for r in rs]);y=np.array([float(r['sumw_cps'])/.25 for r in rs]);err=np.array([float(r['sqrt_sumw2_cps'])/.25 for r in rs]);valid=y>=floor
            col=['#444444',C[0],C[1]][i]
            ax[k].errorbar(x[valid],y[valid],yerr=err[valid],fmt=['o','s','^'][i],linestyle='none',ms=3.5,capsize=2,lw=.8,color=col,label=['Pre-veto','Active veto','Final Compton selection'][i])
            low=(y>0)&(y<floor)
            ax[k].scatter(x[low],np.full(sum(low),floor*1.05),marker='v',s=17,color=col,clip_on=False,zorder=4)
            allrecords.append(dict(model=m,stage=stage,centres=x.tolist(),rates=y.tolist(),errors=err.tolist(),positive_below_display_floor=int(sum(low)),nonpositive_error_lower_end=int(sum((y>0)&(y-err<=0)))))
        ax[k].axvspan(510.5,511.5,color='#E69F00',alpha=.12)
        ax[k].set(xlabel='Measured TES energy (keV)',yscale='log',ylim=(floor,ceiling),title=f'({chr(97+k)}) {NAMES[m]}',xlim=(508,514));tidy(ax[k])
    ax[0].set_ylabel(r'Count rate (cps keV$^{-1}$)');fig.legend(*ax[0].get_legend_handles_labels(),loc='upper center',ncol=3,frameon=False,columnspacing=1.0)
    fig.subplots_adjust(left=.12,right=.99,top=.78,bottom=.18,wspace=.14);save(fig,13)
    (O/'validation/spectrum_display.json').write_text(json.dumps({'floor':floor,'ceiling':ceiling,'data':allrecords},indent=2))

def time_plots():
    defaults();fig,ax=plt.subplots(1,2,figsize=(6.55,3.4))
    for i,m in enumerate('ab'):
        rs=rows(DATA/f'timeline_{m}_500/mission_timeline_81nodes.csv');days=np.array([float(r['day_mid']) for r in rs]);direct=np.array([float(r['direct_W2_final_no_coincidence_cps']) for r in rs]);err=np.array([float(r['direct_transport_sigma_cps']) for r in rs]);rec=[read(DATA/f'timeline_{m}_500/receipts/anchor_{n:03d}.json') for n in [0,20,40,60,80]]
        r=np.array([v['final_timeline_to_direct_ratio'] for v in rec]);e=np.array([v['final_timeline_to_direct_ratio_standard_error'] for v in rec]);anchors=direct[[0,20,40,60,80]]
        ax[0].plot(days,direct,color=C[i],ls=['-','--'][i],label=NAMES[m]);ax[0].fill_between(days,direct-err,direct+err,color=C[i],alpha=.13)
        ax[0].errorbar([0,5,10,15,20],anchors*r,yerr=anchors*e,fmt=['o','s'][i],ms=4,mfc='white',color=C[i],capsize=2)
        ax[1].errorbar([0,5,10,15,20],r,yerr=e,fmt=['o-','s--'][i],ms=4,color=C[i],capsize=2,label=NAMES[m])
    ax[0].set(ylabel='Selected background rate (cps)',title='(a) Direct rates and event-time samples');ax[1].set(ylabel=r'Background correction $C_{\mathrm{bg},g,r}$',title='(b) Simulated / direct rate');ax[1].axhline(1,c='grey',ls=':',lw=.9)
    for a in ax:a.set_xlabel('Mission day');tidy(a);a.legend(frameon=False)
    fig.subplots_adjust(left=.10,right=.98,top=.87,bottom=.17,wspace=.44);save(fig,14)
    fig,ax=plt.subplots(1,2,figsize=(6.55,3.35))
    for i,m in enumerate('ab'):
        rs=rows(DATA/f'timeline_{m}_500/mission_timeline_81nodes.csv');d=np.array([float(r['day_mid']) for r in rs]);bg=np.array([float(r['cumulative_background_counts']) for r in rs]);ker=np.array([float(r['cumulative_signal_counts_per_unit_flux']) for r in rs]);v=bg>0
        ax[0].plot(d[v],2.4e-4*ker[v]/np.sqrt(bg[v]),color=C[i],ls=['-','--'][i],label=NAMES[m]);ax[1].plot(d[v],3*np.sqrt(bg[v])/ker[v],color=C[i],ls=['-','--'][i],label=NAMES[m])
    for z in (3,5):ax[0].axhline(z,color='grey',ls=':',lw=.8)
    ax[0].set(ylabel=r'Counting significance $N_s/\sqrt{N_b}$',title='(a) Reference-flux significance');ax[1].set(ylabel=r'3σ line flux (ph cm$^{-2}$ s$^{-1}$)',yscale='log',title='(b) Top-of-atmosphere threshold')
    for a in ax:a.set_xlabel('On-source exposure (d)');a.set_xlim(0,20);tidy(a);a.legend(frameon=False)
    fig.subplots_adjust(left=.10,right=.98,top=.87,bottom=.18,wspace=.49);save(fig,15)

def environment():
    p=ROOT/'engineering/geometry_optimization_20260815/71_m05_sh3_environment_screening_20260830/code/build_environment_screening.py'
    spec=importlib.util.spec_from_file_location('environment_figure_only',p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    models=mod.load_models_module().CompleteL2Models()
    report=read(P4/'data/environment_kernel_500.json');bands={tuple(k.split('/')):tuple(v) for k,v in report['response_bands_MeV'].items()}
    defaults();fig=plt.figure(figsize=(6.55,6.3));gs=fig.add_gridspec(2,2,height_ratios=[1.15,1]);ax=[fig.add_subplot(gs[0,0]),fig.add_subplot(gs[0,1]),fig.add_subplot(gs[1,:])]
    eg=np.logspace(-1.2,5,700);ep=np.logspace(-2,3,700);envs=mod.ENVIRONMENTS
    for env in envs:
        label=mod.LABEL_EN[env].replace('\n',' ')
        for a,x,keV,fam in [(ax[0],eg,eg*1e3,'gamma'),(ax[1],ep,ep*1e6,'p')]:
            if fam=='gamma' and env=='sun_earth_l2_solar_max_2014':continue
            y=keV*np.asarray(models.target_flux(env,fam,keV),float);y=np.where(y>0,y,np.nan)
            a.plot(x,y,c=mod.COLOR[env],ls=mod.STYLE[env],lw=1.2,label=label)
    for a,key,scale in [(ax[0],('prompt','gamma'),1),(ax[1],('delayed','p'),1e-3)]:
        lo,_,hi=bands[key];a.axvspan(lo*scale,hi*scale,color='#E69F00',alpha=.14)
        a.set(xscale='log',yscale='log');tidy(a);a.text(.03,.04,f'{lo*scale:.3g}–{hi*scale:.3g} '+('MeV' if scale==1 else 'GeV'),transform=a.transAxes,fontsize=9)
    ax[0].set(xlim=(.07,1e5),ylim=(1e-10,3e3),xlabel='Primary photon energy (MeV)',ylabel=r'$E\,d\Phi/dE$ (cm$^{-2}$ s$^{-1}$)',title='(a) Photon fields / prompt response')
    ax[1].set(xlim=(.01,1e3),ylim=(1e-9,3e3),xlabel='Primary proton energy (GeV)',ylabel=r'$E\,d\Phi/dE$ (cm$^{-2}$ s$^{-1}$)',title='(b) Proton fields / activation')
    by={r['environment']:r for r in report['screening']};vals=[]
    for i,env in enumerate(envs):
        y=by[env]['F3_screening_ph_cm2_s']/1e-5;vals.append(y);ax[2].scatter(i,y,s=38,facecolor='white',edgecolor=mod.COLOR[env],lw=1.4);ax[2].text(i,y+.25,f'{y:.2f}',ha='center',fontsize=9,color=mod.COLOR[env])
    ax[2].plot([3,4],vals[-2:],color='grey',lw=1);ax[2].axhline(vals[0],c='grey',ls='--',lw=.8)
    ax[2].set(xticks=range(5),xticklabels=[mod.LABEL_EN[e] for e in envs],ylim=(0,8.7),xlim=(-.5,4.5),ylabel=r'20 d 3σ flux ($10^{-5}$ ph cm$^{-2}$ s$^{-1}$)',title='(c) Environmental screening flux');tidy(ax[2]);ax[2].grid(False,axis='x')
    fig.subplots_adjust(left=.105,right=.985,top=.95,bottom=.09,wspace=.42,hspace=.78)
    fig.legend(*ax[1].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.54,.525),ncol=2,frameon=False,fontsize=8.5,handlelength=1.5,columnspacing=1.5)
    save(fig,16)
    records.append({'figure':16,'environment_order':list(envs),'F3_units_1em5':vals,'source':str(P4/'data/environment_kernel_500.json')})

if __name__=='__main__':
    for fn in [cryostat,workflow,source_flux,poisson,geometry,donuts,spectra,time_plots,environment]:
        print(fn.__name__,flush=True);fn()
    (O/'validation/figure_data.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
