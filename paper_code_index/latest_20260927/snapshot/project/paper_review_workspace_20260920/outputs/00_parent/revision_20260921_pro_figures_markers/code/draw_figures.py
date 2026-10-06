"""Native vector reconstructions of the supplied Pro figure designs.

Small frozen geometry/catalogue inputs only. No transport, no raw-data reads.
"""
from pathlib import Path
import os, sys, re, csv, json, hashlib, types
from collections import defaultdict
sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parents[1]
WORK = OUT.parents[2]
os.environ['MPLCONFIGDIR'] = str(OUT/'validation/mpl')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from matplotlib.lines import Line2D
from matplotlib.colors import to_rgba, Normalize
import matplotlib.patheffects as pe
import aa_section

C = dict(ink='#202020', muted='#737373', cu='#B77945', cu_fill='#D9AF85',
         si='#999999', tes='#C33350', bgo='#202020', bgo_fill='#FFFFFF',
         al='#A0A0A0', al_fill='#FFFFFF', bi='#D3D3D3', w='#444444')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':14.5,
    'mathtext.fontset':'dejavusans','text.color':C['ink'],
    'axes.labelcolor':C['ink'],'xtick.color':C['ink'],'ytick.color':C['ink'],
    'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none',
    'hatch.linewidth':.7,'axes.linewidth':.8,'savefig.facecolor':'white'})
GEOS = {
 'a':WORK/'outputs/00_parent/AA_run_20260921_v1/geometry/Mass_model_AA.geo',
 'b':WORK/'outputs/02_sources_response_compton/corrected_optics_signal_20260920/geometry/b/SH3_Assembly_OptV3.geo'}
DATA = WORK/'outputs/00_parent/revision_20260921_AA_continuous/data'

class Geometry:
    def __init__(self, p):
        self.path=p; self.S=p.read_text(); self.used={}
        self.props={(n,k):v for n,k,v in re.findall(r'^(\S+)\.(\w+)\s+([^\n]+)',self.S,re.M)}
    def prop(self,n,k):
        v=self.props[n,k];self.used.setdefault(n,{})[k]=v;return v
    def xyz(self,n):return np.array(list(map(float,self.prop(n,'Position').split())))
    def shape(self,n):
        v=self.prop(n,'Shape').split();return v[0],np.array(list(map(float,v[1:])))
    def parameters(self,n):return np.array(list(map(float,self.prop(n,'Parameters').split())))

G={m:Geometry(p) for m,p in GEOS.items()}
aa_section.b=G['a']; aa_section.xyz=G['a'].xyz; aa_section.shape=G['a'].shape; aa_section.prop=G['a'].prop
G['a'].PLATES=[(n,'','') for n in ['ColdPlate_60K','ColdPlate_4K','ColdPlate_Still_0p7K','ColdPlate_MXC_100mK_SD_anchor']]
G['a'].SHIELDS=['Vacuum_Jacket_Al_266mmClass_side_port','Shield_60K_Al_side_window',
                'Shield_4K_Al_side_window','Still_Shield_Al_side_window','SG3A_Al_50mK_StillLike_Can']

def rect(ax,x,z,w,h,fc,ec=None,lw=.6,zo=2):
    if w>0 and h>0:
        p=Rectangle((x,z),w,h,facecolor=fc,edgecolor=ec or fc,lw=lw,zorder=zo)
        ax.add_patch(p);return p

def volume_box(ax,g,n,fc,ec=None,zo=4):
    p=g.xyz(n);typ,h=g.shape(n);assert typ=='BRIK'
    return rect(ax,p[0]-h[0],p[2]-h[2],2*h[0],2*h[2],fc,ec,.5,zo)

def tube_x(ax,g,n,fc,ec,zo=2):
    p=g.xyz(n);typ,s=g.shape(n);assert typ=='TUBS'
    ri,ro,h=s[:3]
    for z in [p[2]-ro,p[2]+ri]:rect(ax,p[0]-h,z,2*h,ro-ri,fc,ec,.55,zo)

def plates(ax,g,m):
    for n in ['ColdPlate_60K','ColdPlate_4K','ColdPlate_Still_0p7K',
              'ColdPlate_MXC_100mK_SD_anchor' if m=='a' else 'ColdPlate_MXC_50mK_SD_anchor']:
        p=g.xyz(n);_,v=g.shape(n)
        rect(ax,p[0]-v[5],p[2]+v[3],2*v[5],v[6]-v[3],C['cu_fill'],C['cu'],.65,5)

def model_b(ax):
    g=G['b']
    # Exact section of the ported refrigerator shells; the side branch is
    # omitted here to expose the thermal path, as in a functional cutaway.
    for n in ['MXC50mK','Still','4K','60K']:
        v=g.parameters(f'SH3_DRBase_{n}_FullSideShellShape')
        lo,ri,ro,hi=v[3:7]
        for x in [-ro,ri]:
            for a,b in ([(lo,-3.55),(-2.05,hi)] if x<0 else [(lo,hi)]):
                rect(ax,x,a,ro-ri,b-a,C['al_fill'],C['al'],.48,1)
        # The bottom-cap dimensions are frozen in each nested shell.
        name=f'SH3_DRBase_{n}_BottomCap'
        if (name,'Shape') in g.props:
            p=g.xyz(name);_,s=g.shape(name)
            if len(s)==9:rect(ax,-s[5],p[2]+s[3],2*s[5],s[6]-s[3],C['al_fill'],C['al'],.48,1)
    v=g.parameters('SH3_OptV3_DRFullSideShellShape')
    lo,ri,ro,hi=v[3:7]
    rect(ax,ri,lo,ro-ri,hi-lo,C['al_fill'],C['al'],.6,1)
    for a,b in [(lo,-9.4),(3.8,hi)]:rect(ax,-ro,a,ro-ri,b-a,C['al_fill'],C['al'],.6,1)
    s=g.parameters('SH3_OptV3_DRBottomCapShape')
    rect(ax,-s[5],s[3],2*s[5],s[6]-s[3],C['al_fill'],C['al'],.6,1)
    for i in range(1,6):
        for suffix in ['SideShell','FrontAnnulus','RearColdPortAnnulus']:
            tube_x(ax,g,f'SH3_Layer{i:02d}_{suffix}',C['al_fill'],C['al'])
    for n in ['SH3_BGO40_SideShield','SH3_BGO40_RearColdPortAnnulus']:
        tube_x(ax,g,n,C['bgo_fill'],C['bgo'],1)
    # Front BGO is a cylindrical annulus with a square 6 cm optical recess.
    p=g.xyz('SH3_BGO40_FrontOpticalAnnulus')
    s=g.parameters('SH3_OptV2_BGOFront_FullCylinderShape')
    cut=g.parameters('SH3_OptV2_BGOFront_SquareRecessCutShape')
    for z in [p[2]-s[1],p[2]+cut[1]]:
        rect(ax,p[0]-s[2],z,2*s[2],s[1]-cut[1],C['bgo_fill'],C['bgo'],.7,1)
    for n in ['SH3_OptV2_W_Frame_Top','SH3_OptV2_W_Frame_Bottom']:
        volume_box(ax,g,n,C['w'],zo=6)
    for i in range(6):
        volume_box(ax,g,f'Si_Substrate_Stack_side_entry_L{i}',C['si'],zo=7)
        p=g.xyz(f'TES_L{i}')
        rect(ax,p[0]-.15,p[2]-1.8,.30,3.6,C['tes'],C['tes'],.5,8)
        for side in ['ZP','ZM']:
            n=f'Cu_SubstrateSupport_OpenRing_L{i}_{side}_panel'
            if (n,'Shape') in g.props:volume_box(ax,g,n,C['cu_fill'],C['cu'],8)
    n='SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm';p=g.xyz(n)
    s=g.parameters(n+'_OuterShape');h=g.parameters(n+'_CenterCutShape')
    for z in [p[2]-s[2],p[2]+h[2]]:
        rect(ax,p[0]-s[0],z,2*s[0],s[2]-h[2],C['cu_fill'],C['cu'],.5,7)
    n='SH3_TES_ColdFinger_InterfaceStub';p=g.xyz(n);_,s=g.shape(n)
    rect(ax,p[0]-s[2],p[2]-s[1],2*s[2],2*s[1],C['cu_fill'],C['cu'],.55,6)
    for n in ['PortRun','InsideMXC_Dogleg','InternalRun','MXCStem']:
        volume_box(ax,g,'SH3_OptV2_Cu_ColdFinger_'+n,C['cu_fill'],C['cu'],6)
    n='SH3_OptV2_Cu_MXC_ContactPad';p=g.xyz(n);_,s=g.shape(n)
    rect(ax,p[0]-s[5],p[2]+s[3],2*s[5],s[6]-s[3],C['cu_fill'],C['cu'],.5,6)
    plates(ax,g,'b')
    n='Plate_300K_Top_Service_Lid';p=g.xyz(n);_,v=g.shape(n)
    rect(ax,p[0]-v[5],p[2]+v[3],2*v[5],v[6]-v[3],C['al_fill'],C['al'],.6,2)

def geometry(ax,m,muted=False,shift=0):
    if m=='a':
        aa_section.model_a(ax)
        remap={
            '#F1D5B5':(C['cu_fill'],C['cu']), '#E69F00':(C['cu_fill'],C['cu']),
            '#CDEBDD':(C['bgo_fill'],C['bgo']), '#A6B3C0':(C['si'],C['si']),
            '#B2182B':(C['tes'],C['tes']), '#E6EBEF':(C['al_fill'],C['al']),
            '#D5DEE4':(C['al_fill'],C['al'])}
        for p in ax.patches:
            for old,(fc,ec) in remap.items():
                if p.get_facecolor()==to_rgba(old):p.set(facecolor=fc,edgecolor=ec)
        # Passive Bi above the TES, drawn at its actual projected position.
        g=G[m]
        for n in ['SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm',
                  'SG3B_Bi_MXC_TES_UpperHalfCylinder_Aft_4p796mm']:
            p=g.xyz(n);_,v=g.shape(n)
            rect(ax,p[0]+v[3],p[2]+v[4],v[6]-v[3],v[5]-v[4],C['bi'],C['bi'],.5,4)
        # Remove an old optical-axis guide; the focused beam is drawn once.
        for line in list(ax.lines):
            if line.get_linestyle()!='-':line.remove()
    else:model_b(ax)
    # Retain the mixing chamber drawn above MXC in the Pro design.
    g=G[m];p=g.xyz('DR_MixingChamber_Cu');_,v=g.shape('DR_MixingChamber_Cu')
    rect(ax,p[0]-v[5],p[2]+v[3],2*v[5],v[6]-v[3],C['cu_fill'],C['cu'],.55,5)
    for p in ax.patches:
        p.set_x(p.get_x()-shift)
        if p.get_edgecolor()==to_rgba(C['bgo']):
            p.set(hatch='//',facecolor='white',linewidth=.8)
        elif p.get_facecolor()==to_rgba(C['bi']):p.set(edgecolor='#707070')
        if muted:
            is_tes=p.get_facecolor()==to_rgba(C['tes'])
            p.set(facecolor='none',edgecolor='#3D4650' if is_tes else '#ADB4BA',
                  linewidth=.65 if is_tes else .45,zorder=8 if is_tes else 1)
    for line in ax.lines:
        line.set_color('#999999')
        line.set_xdata(np.asarray(line.get_xdata())-shift)
        if muted:line.set(color='#ADB4BA',lw=.45,zorder=1)

def call(ax,txt,xy,at,ha='left',fs=14.5,col=None):
    ax.annotate(txt,xy=xy,xytext=at,ha=ha,va='center',fontsize=fs,color=col or C['ink'],
        arrowprops=dict(arrowstyle='-',lw=.75,color=C['muted'],shrinkA=4,shrinkB=2),
        bbox=dict(fc='white',ec='none',pad=.3),zorder=20)

def export(fig,stem):
    for ext in ['pdf','svg','png']:
        fig.savefig(OUT/'figures'/f'{stem}.{ext}',dpi=220,bbox_inches='tight',pad_inches=.08)
    plt.close(fig)


VIEW=(-52,29,-24.5,40.5)
MARKERS=['o','s','^','D','v','P']
POINT_COLORS=['#0072B2','#009E73','#7D58A5','#E69F00','#A74B45','#575757']

def canvas():
    fig=plt.figure(figsize=(10,14.5))
    axes=[fig.add_axes([.085,.557,.89,.421]),fig.add_axes([.085,.090,.89,.421])]
    for ax,m,name in zip(axes,'ab',['Under-stage','Lateral-chimney']):
        geometry(ax,m)
        ax.set(xlim=VIEW[:2],ylim=VIEW[2:],xlabel="x′ (cm)",ylabel="z′ (cm)")
        ax.set_aspect('equal');ax.spines[['top','right']].set_visible(False)
        ax.set_xticks([-40,-20,0,20]);ax.set_yticks([-20,0,20,40])
        ax.tick_params(labelsize=14.5,length=3)
        ax.set_title(f'({m})  {name}',loc='left',fontsize=16,fontweight='bold',pad=11)
        for z,label in [(29,'60 K'),(20,'4 K'),(11,'Still'),(0,'MXC')]:
            ax.text(12.5,z+1.4,label,fontsize=14.5,color=C['cu'],ha='right',va='bottom',
                    bbox=dict(fc='white',ec='none',pad=.2),zorder=15)
        if m=='a':
            ax.set_xlabel('')
            call(ax,'Cu cold plates',(-15,20),(-49,21))
            call(ax,'TES',(0,-5.2),(-12,-15.2),col=C['tes'])
            call(ax,'Cu thermal links',(6.05,-3.4),(12,-9.5),ha='center',col=C['cu'],fs=14.5)
            ax.annotate('',xy=(-3.7,-5.2),xytext=(-50,-5.2),
                        arrowprops=dict(arrowstyle='->',color=C['ink'],lw=1.4),zorder=18)
            ax.text(-49,-2.6,'Focused beam',fontsize=14.5)
        else:
            call(ax,'TES',(-35.5,-3.5),(-42,-19),col=C['tes'])
            call(ax,'Cu cold finger',(-9,-2.8),(-10,-17),col=C['cu'])
            call(ax,'Al shells',(-35,3.0),(-48,14),fs=14.5)
            ax.annotate('',xy=(-39.3,-2.8),xytext=(-51,-2.8),
                        arrowprops=dict(arrowstyle='->',color=C['ink'],lw=1.4),zorder=18)
    # Same exact geometry and coordinates are used for both figures.
    geom=[[(tuple(p.get_xy()),p.get_width(),p.get_height(),p.get_facecolor(),p.get_edgecolor(),p.get_hatch())
           for p in ax.patches] for ax in axes]
    return fig,axes,geom

def fig8():
    fig,axes,geom=canvas()
    handles=[Patch(fc=C['cu_fill'],ec=C['cu'],label='Cu'),Patch(fc=C['tes'],label='TES'),
             Patch(fc=C['si'],label='Si'),Patch(fc='white',ec=C['bgo'],hatch='//',label='BGO'),
             Patch(fc='white',ec=C['al'],label='Al'),Patch(fc=C['bi'],ec='#707070',label='Bi')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.54,.005),ncol=6,
               frameon=False,fontsize=14.5,columnspacing=1.4,handlelength=1.0)
    export(fig,'Figure08')
    return geom

def fig10(reference_geometry):
    rows={m:list(csv.DictReader((DATA/f'delayed_origins_{m}_500.csv').open())) for m in 'ab'}
    totals=defaultdict(float)
    for r in sum(rows.values(),[]):totals[r['source_parent_ZA']]+=float(r['day15_weight_cps'])
    top=sorted(totals,key=totals.get,reverse=True)[:5]
    symbols={29:'Cu',9:'F',47:'Ag'}
    labels=[r'$^{'+str(int(k)%1000)+'}$'+symbols[int(k)//1000] for k in top]+['Other']
    stats={};points=[]
    fig,axes,geom=canvas()
    assert geom==reference_geometry
    for ax,m in zip(axes,'ab'):
        sites=defaultdict(set)
        for r in rows[m]:
            pt=(float(r['xprime_cm']),float(r['zprime_cm']))
            group=top.index(r['source_parent_ZA']) if r['source_parent_ZA'] in top else 5
            sites[pt].add(group)
        assert all(len(g)==1 for g in sites.values())
        for group in range(6):
            pts=sorted(pt for pt,groups in sites.items() if group in groups)
            if pts:
                a=np.array(pts)
                # Size indicates neither rate nor activity; no coordinate jitter.
                ax.scatter(a[:,0],a[:,1],s=35,marker=MARKERS[group],
                           c=POINT_COLORS[group],edgecolors='white',linewidths=.6,zorder=24)
        w=np.array([float(r['day15_weight_cps']) for r in rows[m]])
        outside=[(x,z) for x,z in sites if not(VIEW[0]<=x<=VIEW[1] and VIEW[2]<=z<=VIEW[3])]
        assert not outside,outside
        stats[m]=dict(records=len(w),unique_xz_sites=len(sites),displayed_sites=len(sites),
                      outside_sites=outside,selected_rate_cps=float(w.sum()),
                      se_cps=float(np.sqrt(sum(w*w))))
        for (xx,zz),groups in sites.items():
            i=next(iter(groups))
            points.append(dict(model=m,xprime_cm=xx,zprime_cm=zz,
                               parent_ZA=top[i] if i<5 else 'Other'))
    handles=[Line2D([],[],ls='',marker=MARKERS[i],mfc=POINT_COLORS[i],mec='white',ms=7,
                    label=labels[i]) for i in range(6)]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.54,.005),ncol=6,
               frameon=False,fontsize=14.5,handletextpad=.4,columnspacing=1.2)
    export(fig,'Figure10')
    with (OUT/'validation/figure10_nuclide_sites.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(points[0]));writer.writeheader();writer.writerows(points)
    return dict(statistics=stats,top_parent_ZA=top,view_cm=VIEW,
                same_geometry_as_figure08=True,rate_heatmap=False,rate_component_panel=False,
                symbol_meaning='parent identity at its production coordinate; fixed display size',
                coordinate_jitter=False,rate_weights_deduplicated=False,smoothing=False)

if __name__=='__main__':
    geom=fig8();audit=fig10(geom)
    audit['inputs']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*GEOS.values(),*[DATA/f'delayed_origins_{m}_500.csv' for m in 'ab']]}
    audit['geometry_properties_read']={m:g.used for m,g in G.items()}
    audit['production_simulation_run']=False
    (OUT/'validation/FIGURE_DATA_CHECKS.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit['statistics'],indent=2))
