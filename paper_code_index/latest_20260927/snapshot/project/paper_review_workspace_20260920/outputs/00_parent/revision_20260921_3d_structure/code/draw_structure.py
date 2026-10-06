"""Orthographic, opaque cutaway drawing from retained geometry; no transport.

Faces are shaded and depth-sorted in an orthographic camera, then written as
native vector polygons. Dense service-hole arrays are intentionally not drawn.
"""
from pathlib import Path
import os, re, json, hashlib, itertools
O=Path(__file__).resolve().parents[1]; W=O.parents[2]; ROOT=W.parent
os.environ['MPLCONFIGDIR']=str(O/'validation/matplotlib')
os.environ['MPLBACKEND']='Agg'
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb
from matplotlib.patches import Rectangle, ConnectionPatch

GEO=ROOT/'engineering/geometry_optimization_20260815/68_sg3_minimal_sd_prompt_supplement_20260823/geometry/DEMO2_DR_v3p5_SG3B.geo'
S=GEO.read_text()
C=dict(ink='#26343E',cu='#BD8658',mxc='#5594B6',al='#B8C8D2',vac='#D3DDE3',
       bgo='#5BA78D',bpe='#B7C48A',ta='#CB3148',bi='#AD83AF',beam='#D87820')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9.2,'text.color':C['ink'],
                     'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none'})
used={}
def prop(n,k):
    m=re.search(r'^'+re.escape(n)+r'\.'+k+r'\s+(.+)$',S,re.M)
    if not m: raise KeyError((n,k))
    used.setdefault(n,{})[k]=m[1];return m[1]
def xyz(n):return np.array([float(v) for v in prop(n,'Position').split()])
def shape(n):
    v=prop(n,'Shape').split();return v[0],np.array([float(x) for x in v[1:]])

class Scene:
    def __init__(self,eye=(-.45,-1,.38)):
        self.eye=np.array(eye,float);self.eye/=np.linalg.norm(self.eye)
        self.right=np.cross([0,0,1],self.eye);self.right/=np.linalg.norm(self.right)
        self.up=np.cross(self.eye,self.right)
        self.faces=[];self.colors=[]
    def project(self,pts):
        p=np.asarray(pts);return np.stack((p@self.right,p@self.up),axis=-1)
    def face(self,p,c):self.faces.append(np.array(p,float));self.colors.append(c)
    def box(self,center,half,c):
        x,y,z=np.array(center);a,b,d=np.array(half)
        v=np.array([[x-a,y-b,z-d],[x+a,y-b,z-d],[x+a,y+b,z-d],[x-a,y+b,z-d],
                    [x-a,y-b,z+d],[x+a,y-b,z+d],[x+a,y+b,z+d],[x-a,y+b,z+d]])
        for f in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:self.face(v[list(f)],c)
    def tube(self,ri,ro,lo,hi,c,start=0,end=180,axis='z',center=(0,0,0),step=3):
        theta=np.deg2rad(np.linspace(start,end,max(2,int((end-start)/step)+1)))
        def point(r,t,z):
            p=np.array([r*np.cos(t),r*np.sin(t),z])
            if axis=='x':p=np.array([z,p[0],p[1]])
            return p+center
        zs=np.linspace(lo,hi,max(2,int(abs(hi-lo)/2.5)+1))
        for a,b in zip(theta[:-1],theta[1:]):
            for z0,z1 in zip(zs[:-1],zs[1:]):
                self.face([point(ro,a,z0),point(ro,b,z0),point(ro,b,z1),point(ro,a,z1)],c)
                if ri>0:self.face([point(ri,b,z0),point(ri,a,z0),point(ri,a,z1),point(ri,b,z1)],c)
            for z,reverse in [(lo,True),(hi,False)]:
                p=[point(ri,a,z),point(ro,a,z),point(ro,b,z),point(ri,b,z)]
                self.face(p[::-1] if reverse else p,c)
        if end-start<359:
            for t in [theta[0],theta[-1]]:
                for z0,z1 in zip(zs[:-1],zs[1:]):self.face([point(ri,t,z0),point(ro,t,z0),point(ro,t,z1),point(ri,t,z1)],c)
    def volume(self,n,c):
        typ,s=shape(n);p=xyz(n)
        if typ=='BRIK':self.box(p,s,c)
        elif typ=='PCON':self.tube(s[4],s[5],p[2]+s[3],p[2]+s[6],c,start=0,end=360,center=(p[0],p[1],0))
        else:raise ValueError((n,typ))
    def draw(self,ax):
        light=np.array([-.6,-.8,1.8]);light/=np.linalg.norm(light)
        order=np.argsort([p.mean(0)@self.eye for p in self.faces])
        polys=[];colors=[];edges=[];widths=[]
        for i in order:
            p=self.faces[i];normal=np.cross(p[1]-p[0],p[2]-p[0]);length=np.linalg.norm(normal)
            if length<1e-10:normal=np.cross(p[2]-p[1],p[3]-p[1]);length=np.linalg.norm(normal)
            normal=normal/length if length>0 else np.array([0,0,1])
            if normal@self.eye<0:normal=-normal
            shade=.76+.24*max(0,normal@light)
            polys.append(self.project(p));colors.append(np.array(to_rgb(self.colors[i]))*shade)
            pixel=self.colors[i]==C['ta']
            edges.append(colors[-1]*.72+np.ones(3)*.28 if pixel else colors[-1])
            widths.append(.10 if pixel else .12)
        ax.add_collection(PolyCollection(polys,facecolors=colors,edgecolors=edges,linewidths=widths,zorder=2))
        ax.set_aspect('equal');ax.axis('off')
    def label(self,ax,text,target,at,ha='left',size=9.2):
        ax.annotate(text,xy=self.project(target),xytext=at,ha=ha,va='center',fontsize=size,
            arrowprops={'arrowstyle':'-','lw':.65,'color':C['ink'],'shrinkA':2,'shrinkB':0},
            bbox=dict(fc='white',ec='none',pad=.4),zorder=8)
    def beam(self,ax,start,end):
        ax.annotate('',xy=self.project(end),xytext=self.project(start),
                    arrowprops={'arrowstyle':'-|>','color':C['beam'],'lw':1.5},zorder=7)

PLATES=[('Plate_300K_Top_Service_Lid','300 K lid',C['al']),
        ('ColdPlate_60K','60 K',C['al']),('ColdPlate_4K','4 K',C['cu']),
        ('ColdPlate_Still_0p7K','Still (0.7 K)',C['cu']),
        ('ColdPlate_MXC_50mK_SD_anchor','MXC',C['mxc'])]
SHIELDS=['Vacuum_Jacket_Al_266mmClass_side_port','Shield_60K_Al_side_window',
         'Shield_4K_Al_side_window','Still_Shield_Al_side_window','SG3A_Al_50mK_StillLike_Can']

def cold_end(sc,individual=False):
    # Local cylindrical shield, axis along the optical beam; front half cut away.
    n='SE3_Al_Shield_Inner_Cylinder_2mm';_,s=shape(n);p=xyz(n)
    sc.tube(s[4],s[5],s[3],s[6],C['al'],start=-90,end=90,axis='x',center=p)
    # The upper Bi half-cylinder has its front quarter removed in this cutaway.
    for part in ['Main','Aft']:
        n=f'SG3B_Bi_MXC_TES_UpperHalfCylinder_{part}_4p796mm';_,s=shape(n);p=xyz(n)
        sc.tube(s[4],s[5],s[3],s[6],C['bi'],start=0,end=90,axis='x',center=p)
    pix=np.array([xyz(m[1]) for m in re.finditer(r'^TES_Pixel_L0.Copy (\S+)$',S,re.M)])
    for i in range(6):
        p=xyz(f'TES_L{i}')
        if individual:
            for q in pix:sc.box(p+q,[.15,.075,.075],C['ta'])
        else:sc.box(p,[.15,1.8,1.8],C['ta'])
        for side in ['ZP','ZM','YP','YM']:
            n=f'Cu_SubstrateSupport_OpenRing_L{i}_{side}_panel'
            # The original template L0 has no independently named support panel.
            if re.search(r'^'+re.escape(n)+r'\.Shape',S,re.M):sc.volume(n,C['cu'])
    for n in ['Cu_SubstrateSupport_EdgeRod_'+str(i) for i in range(1,5)]:sc.volume(n,C['cu'])
    for y in ['YP','YM']:
        for z in ['ZP','ZM']:
            sc.volume(f'Cu_ColdFinger_OffAxis_{y}_{z}_from_Disk_to_Stem',C['cu'])
            sc.volume(f'Cu_ColdFinger_Stem_{y}_{z}_to_MXC',C['cu'])
    n='SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm';p=xyz(n)
    out=np.array([float(x) for x in prop(n+'_OuterShape','Parameters').split()])
    inside=np.array([float(x) for x in prop(n+'_CenterCutShape','Parameters').split()])
    t=(out[1]-inside[1])/2;mid=(out[1]+inside[1])/2
    for sign in [-1,1]:
        sc.box(p+[0,sign*mid,0],(out[0],t,out[2]),C['cu'])
        sc.box(p+[0,0,sign*mid],(out[0],inside[1],t),C['cu'])
    return pix

def overview():
    sc=Scene()
    sc.tube(27,29,-24.5,46,C['bpe']);sc.tube(0,29,-26.5,-24.5,C['bpe']);sc.tube(0,29,46,48,C['bpe'])
    sc.tube(21.2,25.2,-19.4,40.9,C['bgo']);sc.tube(0,25.2,-22.4,-19.4,C['bgo']);sc.tube(20.9,25.2,40.9,41.9,C['bgo'])
    for i,n in enumerate(SHIELDS):
        _,s=shape(n+'_side_wall_above_side_port');p=xyz(n+'_side_wall_above_side_port')
        cap=n+'_bottom_cap'+('_2mm' if n.startswith('SG3A') else '')
        _,v=shape(cap);q=xyz(cap);col=C['vac'] if i==0 else C['al']
        sc.tube(s[4],s[5],q[2]+v[6],p[2]+s[6],col)
        sc.tube(0,s[5],q[2]+v[3],q[2]+v[6],col)
    for n,label,c in PLATES:
        _,s=shape(n);p=xyz(n);sc.tube(0,s[5],p[2]+s[3],p[2]+s[6],c)
    cold_end(sc)
    return sc

def main():
    fig=plt.figure(figsize=(7.25,6.10))
    a=fig.add_axes([.005,.095,.56,.83]);a.set(xlim=(-44,43),ylim=(-32,62));a.set_anchor('N')
    a.text(0,1.055,'(a)  Under-stage: 3D cutaway',transform=a.transAxes,fontsize=10.3,weight='bold')
    sc=overview();sc.draw(a)
    for n,lab,col in PLATES:
        p=xyz(n);_,s=shape(n);target=(s[5]*.70,0,p[2]+s[6]);xy=sc.project(target)
        sc.label(a,lab,target,(26,xy[1]+.2))
    sc.label(a,'BPE shield',(-28,0,41),(-43,52))
    sc.label(a,'BGO veto',(-23.2,0,25),(-43,37))
    sc.label(a,'Vacuum\njacket',(-20.4,0,16),(-43,23))
    sc.label(a,'Al thermal\nshields',(-17.85,0,3),(-43,10))
    sc.beam(a,(-39,0,-5.2),(-4.5,0,-5.2))
    a.text(-42,-12,'511 keV',color=C['beam'],fontsize=9.0)
    sc.label(a,'TES array',(0,-1.8,-5.2),(13,-14))
    # Cold-end region, and a matched colour around the enlargement.
    q=sc.project(list(itertools.product([-5,8],[-4.2,4.2],[-9.5,.2])));lo=q.min(0)-[.7,.7];hi=q.max(0)+[.7,.7]
    a.add_patch(Rectangle(lo,*(hi-lo),fill=False,ec='#546E80',lw=.8,ls=(0,(3,2)),zorder=6))
    a.text(hi[0]+1,hi[1],'b',fontsize=9.5,weight='bold')
    a.plot([-31,-21],[-29,-29],c=C['ink'],lw=1.2);a.plot([-31,-31,-21,-21],[-28.3,-29.7,-29.7,-28.3],c=C['ink'],lw=.6)
    a.text(-26,-33,'10 cm',ha='center',fontsize=8.7)

    b=fig.add_axes([.56,.43,.435,.485]);b.set(xlim=(-10.3,13.5),ylim=(-11.8,5.5));b.set_anchor('N')
    b.text(0,1.08,'(b)  TES mounting and cold link',transform=b.transAxes,fontsize=10.3,weight='bold')
    sb=Scene((-.65,-1,.50))
    # A rectangular local crop of the same single circular MXC plate.
    sb.box((1.2,1.8,0),(6.4,1.8,.2),C['mxc'])
    pix=cold_end(sb,individual=True);sb.draw(b)
    sb.label(b,'MXC Cu plate',(5.0,0,.2),(-7.5,4.15))
    sb.label(b,'Bi liner',(-1.5,0,-1.50),(-10.0,2.1))
    sb.label(b,'Cu links',(6.85,-1.1,-2.0),(8.1,1.1))
    sb.label(b,'Cu heat sink',(3.42,-2.8,-6.7),(8.1,-5.7))
    sb.label(b,'Cu supports',(-1.45,-2.025,-5.2),(-10.1,-7.6))
    sb.label(b,'Local Al shield',(-1.3,2.5,-8.5),(1.7,-11))
    sb.beam(b,(-9,0,-5.2),(-4.5,0,-5.2))
    sb.label(b,'Six TES layers',(-2.65,-.5,-5.2),(-9.8,-10.5))

    c=fig.add_axes([.585,.105,.40,.235]);c.set(xlim=(-.2,12.8),ylim=(-3.4,4.1));c.axis('off')
    c.text(0,1.06,'(c)  Optical entrance',transform=c.transAxes,fontsize=10.3,weight='bold')
    c.add_patch(Rectangle((-.1,-.18),12.4,.36,fc='#FBEBD9',ec='none'))
    xs=[.8,2.15,3.5,5.,6.35,7.7,9.05,10.4];labels=['W','Al','Be','60 K','4 K','Still','MXC','Local']
    for i,(x,lab) in enumerate(zip(xs,labels)):
        color='#485662' if i==0 else '#168496' if i==2 else '#98ACB9'
        c.add_patch(Rectangle((x-.09,-1.0),.18,2.,fc=color,ec='none'))
        if i==0:
            for y in [-.66,0,.66]:c.add_patch(Rectangle((x-.10,y-.06),.20,.12,fc='white',ec='none'))
        y=1.7 if i%2 else 2.65
        c.text(x,y,lab,ha='center',fontsize=8.8);c.plot([x,x],[1.05,y-.25],c=C['ink'],lw=.55)
    c.add_patch(Rectangle((11.6,-.9),.28,1.8,fc=C['ta'],ec='none'))
    c.text(11.85,2.65,'TES',ha='center',fontsize=8.8)
    c.annotate('',xy=(12.25,0),xytext=(-.15,0),arrowprops=dict(arrowstyle='-|>',lw=1.2,color=C['beam']))
    c.text(.1,-1.85,'W collimator',fontsize=8.7)
    c.plot([5,5,10.4,10.4],[-1.2,-1.6,-1.6,-1.2],c=C['ink'],lw=.6)
    c.text(7.7,-2.45,'Al windows',ha='center',fontsize=8.7)
    c.text(6.1,-3.30,'Separations enlarged',ha='center',fontsize=8.6)
    fig.text(.02,.025,'Dense hole arrays in the cold plates are omitted for clarity.',fontsize=9.2,color=C['ink'])
    for ext in ['pdf','svg','png']:
        fig.savefig(O/'figures'/('fig02.'+ext),dpi=220,bbox_inches='tight',pad_inches=.06)
    plt.close(fig)
    manifest=dict(geometry_source=str(GEO),geometry_sha256=hashlib.sha256(GEO.read_bytes()).hexdigest(),
        plotted_geometry_properties=used,projection='orthographic, depth-sorted opaque vector surfaces',
        user_requested_hole_arrays='omitted in drawing only; geometry unchanged',
        visible_plates=[n for n,_,_ in PLATES],single_MXC=True,plastic_drawn=False,
        display_cuts=['front half of cylindrical shields and stage plates','front quarter of upper Bi liner',
                      'front half of local Al shield','local crop of MXC plate in panel b'],
        pixels_per_layer=len(pix),layers=6,individual_pixels_in_detail=2256,
        simulation_run=False,numerical_results_changed=False)
    (O/'validation/geometry_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Figure 2 written; opaque cutaway; dense cold-plate holes omitted.')

if __name__=='__main__':main()
