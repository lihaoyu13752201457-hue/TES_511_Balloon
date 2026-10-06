#!/usr/bin/env python3
"""Draw true sections of Geant4's native AA mesh, plus a readable cutaway WRL.

VRML coordinates are native global mm; plots use InstrumentFrame-local cm.
No solids are rebuilt from sketches. Vacuum daughters are drawn over their
parent material to represent the retained perforated cold plates.
"""
from pathlib import Path
import json, re, math, hashlib
import numpy as np
import pyvista as pv
import vtk
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, LineCollection
from matplotlib.patches import Patch
from matplotlib.font_manager import FontProperties, fontManager
from matplotlib.backends.backend_pdf import PdfPages
from scipy.spatial.transform import Rotation

P=Path(__file__).resolve().parents[1]
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
fontManager.addfont(FONT)
plt.rcParams.update({'font.family':FontProperties(fname=FONT).get_name(),'font.size':11,'axes.unicode_minus':False,'pdf.fonttype':42,'svg.fonttype':'path','axes.titleweight':'regular'})
COL={'Aluminium':'#91b6d3','Copper':'#cd853e','Ta':'#bc3f43','Bi':'#9958a1','BGO':'#55aa87','W':'#344b67','Silicon':'#6b76aa','StainlessSteel':'#77868d','CuNi':'#a16c50','G10':'#b5ba73','Kapton':'#d4b45f','Be':'#80c4c0','SilverSinterProxy':'#b7b9c5','CharcoalProxy':'#505356','Vacuum':'#ffffff'}
ROT=np.array([[1/math.sqrt(2),0,1/math.sqrt(2)],[0,1,0],[-1/math.sqrt(2),0,1/math.sqrt(2)]])

def load_meshes():
    inventory=json.loads((P/'data/component_inventory.json').read_text())
    text=(P/'figures/Mass_model_AA_native.wrl').read_text()
    meshes=[]
    for block in re.split(r'#---------- SOLID: ',text)[1:]:
        name=block.splitlines()[0].strip().rsplit('.',1)[0]
        if name not in inventory: continue
        v=inventory[name]
        m=re.search(r'point\s*\[([^]]+)\]',block,re.S);f=re.search(r'coordIndex\s*\[([^]]+)\]',block,re.S)
        if not m or not f: continue
        pts=np.fromstring(m[1].replace(',',' '),sep=' ').reshape(-1,3)@ROT/10.
        indices=np.fromstring(f[1].replace(',',' '),sep=' ',dtype=int)
        faces=[];start=0
        for end in np.flatnonzero(indices==-1):
            face=indices[start:end];faces.extend([len(face),*face]);start=end+1
        mesh=pv.PolyData(pts,np.array(faces))
        meshes.append((name,v,mesh))
    pixel_count=sum(n.startswith('TP_L') for n,v,m in meshes)
    assert pixel_count==2256, f'Incomplete native TES export: {pixel_count}'
    # Sanity-check rotation and units against exact AA W placement.
    top=next(m for n,v,m in meshes if n=='AA_W_Collimator_Top')
    assert np.allclose(top.center,(-24.2,0,-2.35),atol=0.002),top.center
    meshes.sort(key=lambda x:x[1].get('Material')=='Vacuum')
    return meshes

def section(mesh, axis, value):
    normal=np.eye(3)[axis];origin=normal*value
    bounds=np.array(mesh.bounds).reshape(3,2)
    if value<bounds[axis,0]-1e-5 or value>bounds[axis,1]+1e-5: return None,None
    cut=mesh.slice(normal=normal,origin=origin)
    if not cut.n_points: return None,None
    tri=vtk.vtkContourTriangulator();tri.SetInputData(cut);tri.Update()
    cap=pv.wrap(tri.GetOutput()).triangulate()
    dims=[i for i in range(3) if i!=axis]
    triangles=cap.points[cap.faces.reshape(-1,4)[:,1:]][:,:,dims] if cap.n_faces_strict else []
    seg=[];lines=cut.lines;i=0
    while i<len(lines):
        n=int(lines[i]);ids=lines[i+1:i+1+n];i+=n+1
        if len(ids)>1: seg.append(cut.points[ids][:,dims])
    return triangles,seg

def draw_section(ax, meshes, axis, value, bounds):
    for name,v,mesh in meshes:
        material=v.get('Material','Vacuum')
        if material=='Vacuum' and not name.startswith('SE3_HOLE_'): continue
        triangles,segments=section(mesh,axis,value)
        if triangles is None: continue
        color=COL.get(material,'#888888')
        if len(triangles): ax.add_collection(PolyCollection(triangles,facecolors=color,edgecolors='none',antialiased=False,rasterized=False,zorder=3 if material=='Vacuum' else 2))
        if segments: ax.add_collection(LineCollection(segments,colors='#ffffff' if material=='Vacuum' else color,linewidths=0.6,zorder=4 if material=='Vacuum' else 2))
    ax.set_xlim(*bounds[:2]);ax.set_ylim(*bounds[2:]);ax.set_aspect('equal');ax.grid(alpha=.15,zorder=0)
    dims=[i for i in range(3) if i!=axis];labels=['x′ / cm','y′ / cm','z′ / cm']
    ax.set_xlabel(labels[dims[0]]);ax.set_ylabel(labels[dims[1]])
    for sp in ax.spines.values(): sp.set_color('#c4ccd3')

def note(ax,text,xy,xytext,ha='left',color='#243449',size=10):
    return ax.annotate(text,xy=xy,xytext=xytext,ha=ha,va='center',fontsize=size,color=color,arrowprops={'arrowstyle':'-','color':color,'lw':.85},bbox={'boxstyle':'round,pad=.18','fc':'white','ec':'none','alpha':.9},zorder=10)

def dim(ax,p,q,text,offset=(0,0),size=10):
    p=np.array(p);q=np.array(q);ax.annotate('',xy=p,xytext=q,arrowprops={'arrowstyle':'<->','lw':.8,'color':'#344457'})
    mid=(p+q)/2+offset;ax.text(*mid,text,ha='center',va='center',fontsize=size,bbox={'fc':'white','ec':'none','pad':1},zorder=20)

def main_figure(meshes):
    fig=plt.figure(figsize=(19,13),facecolor='white')
    gs=fig.add_gridspec(2,3,width_ratios=[1.15,1,1],height_ratios=[1,1],left=.055,right=.985,bottom=.13,top=.88,wspace=.28,hspace=.40)
    ax=fig.add_subplot(gs[:,0]);draw_section(ax,meshes,1,0,(-33,33,-27,49));ax.set_title('A  整机纵剖面｜y′ = 0',loc='left',pad=14,fontsize=15)
    for z,txt,xend in [(38,'300 K 顶盖',17),(29,'60 K 冷盘',14),(20,'4 K 冷盘',14),(11,'Still 0.7 K',12),(0,'MXC 100 mK',12)]: note(ax,txt,(xend,z),(29,z+2),ha='right',size=10)
    note(ax,'BGO 侧屏蔽\n厚 40 mm',(23.3,6),(31,-9),ha='right')
    note(ax,'BGO 底屏蔽\n厚 30 mm',(2,-20.9),(14,-25.0),ha='center')
    note(ax,'W 准直器',(-24.2,-2.35),(-31,7),size=10)
    note(ax,'Al 顶盖 3 mm',(-7,45.55),(-31,48),size=10)
    note(ax,'BGO 顶盖 10 mm',(-7,41.4),(-31,43.5),size=10)
    ax.annotate('',xy=(-5,-5.2),xytext=(-32,-5.2),arrowprops={'arrowstyle':'->','color':'#b4453e','lw':1.2});ax.text(-31,-8.7,'入射方向 +x′',fontsize=9,color='#b4453e')
    ax.plot([-5.8,8,8,-5.8,-5.8],[-10.3,-10.3,1,1,-10.3],ls='--',lw=.8,color='#697887')
    b=fig.add_subplot(gs[0,1:]);draw_section(b,meshes,1,0,(-6.6,8.4,-11,1.9));b.set_title('B  TES 与近场屏蔽纵剖面｜y′ = 0',loc='left',pad=14,fontsize=15)
    b.axhline(-5.2,color='#aab2bc',ls='--',lw=.65,zorder=1)
    note(b,'唯一 MXC 冷盘：100 mK',(0,0),(-5.8,1.25),size=11)
    note(b,'Bi 上半筒（Bi 伞）\n径向厚 4.796 mm',(-1,-1.45),(-5.8,-1.3),size=11)
    note(b,'Al 横向筒：厚 2 mm\n内径 80 mm，外径 84 mm',(1,-9.35),(-5.8,-10.4),size=11)
    note(b,'6 层 Ta / TES 阵列',(0.6,-5.2),(1.6,-7.9),size=11)
    note(b,'Cu 散热环',(3.42,-3.0),(7.9,.8),ha='right',size=10)
    note(b,'Al 后端盖',(4.2,-7.8),(7.9,-9.6),ha='right',size=10)
    note(b,'Al 入光端盖\n厚 2 mm',(-3.95,-8.5),(-6.1,-7.7),size=10)
    c=fig.add_subplot(gs[1,1]);draw_section(c,meshes,0,-.6,(-5.3,5.3,-10.5,.2));c.set_title('C  横截面｜x′ = −0.6 cm',loc='left',pad=14,fontsize=14)
    note(c,'Bi 上半筒',(2.5,-2.4),(4.7,-.55),ha='right',size=10)
    note(c,'Al 闭合圆筒',(-3.2,-7.9),(-4.9,-10),size=10)
    note(c,'Ta / TES 像素',(0,-5.2),(4.8,-9.1),ha='right',size=10)
    d=fig.add_subplot(gs[1,2]);draw_section(d,meshes,0,-24.2,(-4.1,4.1,-9.3,-1.1));d.set_title('D  W 准直器正截面（BGO 内）',loc='left',pad=14,fontsize=14)
    dim(d,(-3,-1.9),(3,-1.9),'外边长 60 mm',offset=(0,.28))
    dim(d,(-2.7,-5.2),(2.7,-5.2),'净孔 54 × 54 mm',offset=(0,.38))
    d.text(0,-8.85,'轴向长度 20 mm；边框宽 3 mm',ha='center',fontsize=10)
    fig.text(.055,.962,'质量模型 AA｜详细二维剖面',fontsize=25,color='#20364b')
    fig.text(.055,.927,'由 Geant4 构建几何的原生网格截取；局部坐标 x′ 为入射方向，整体安装倾角保留 45°。',fontsize=12,color='#526373')
    legend=[Patch(facecolor=COL[m],label=label) for m,label in [('Aluminium','Al'),('Copper','Cu'),('Ta','Ta / TES'),('Bi','Bi'),('BGO','BGO'),('W','W'),('StainlessSteel','不锈钢'),('CuNi','CuNi'),('Silicon','Si')]]
    fig.legend(handles=legend,loc='lower left',bbox_to_anchor=(.055,.055),ncol=9,frameon=False,fontsize=11)
    fig.text(.055,.035,'保留原 2 mm Al 筒；未新增 Nb。剖面按实际比例绘制；极薄窗膜请见入射通道详图。',fontsize=11,color='#526373')
    return fig

def beam_figure(meshes):
    fig,axs=plt.subplots(2,1,figsize=(16,10),gridspec_kw={'height_ratios':[1,1]},layout='constrained')
    fig.suptitle('质量模型 AA｜入射通道与冷端细节',fontsize=21)
    ax=axs[0];draw_section(ax,meshes,1,0,(-29,9,-11,1))
    ax.set_title('沿入射轴的实际纵剖面（y′ = 0）',loc='left')
    ax.axhline(-5.2,color='#68798a',ls='--',lw=.7)
    note(ax,'W 方框\n净孔 54 mm',(-24.2,-2.35),(-23,.4),size=10)
    note(ax,'外壳圆孔\n直径 54 mm',(-26,-2.5),(-28,.4),size=10)
    note(ax,'150 μm Be 窗',(-20.35,-4),(-16,.4),size=10)
    note(ax,'2 mm Al 筒',(-1,-9.4),(-5,-10.7),ha='center',size=10)
    ax=axs[1];draw_section(ax,meshes,1,0,(-5,8,-10.2,1))
    ax.set_title('冷端局部放大；Bi 伞在 Cu 散热环处沿轴向分段避让',loc='left')
    note(ax,'Bi 主段：x′ = −3.80…3.24 cm',(1,-1.4),(-4.8,.6),size=10)
    note(ax,'Bi 后段：x′ = 3.60…4.00 cm',(3.8,-1.4),(7.7,.6),ha='right',size=10)
    note(ax,'原 Al 筒完整保留\n轴向 x′ = −3.85…4.10 cm',(-1,-9.3),(-4.8,-7.8),size=10)
    note(ax,'Al 后盖：2 mm',(4.2,-8),(7.7,-9.6),ha='right',size=10)
    note(ax,'Al 入光端盖：2 mm\n圆孔 54 mm + 25 μm Al 薄窗',(-3.95,-2),(-4.8,-3),size=10)
    return fig

def top_figure(meshes):
    fig,axes=plt.subplots(1,2,figsize=(16,10))
    fig.subplots_adjust(left=.06,right=.97,top=.83,bottom=.25,wspace=.21)
    manifest=json.loads((P/'data/manifest.json').read_text())['refinement']
    for ax,key,title,z in [(axes[0],'BGO_top','BGO 顶盖｜厚 10 mm',41.4),(axes[1],'Al_top','Al 顶盖｜厚 3 mm',45.55)]:
        # Show each actual cover alone to make its through-holes clear.
        selected=[item for item in meshes if item[0]==manifest[key]['name']]
        draw_section(ax,selected,2,z,(-28,28,-28,28));ax.set_title(title,loc='left',fontsize=15,pad=12)
        for i,port in enumerate(manifest[key]['ports'],1):
            ax.annotate(str(i),(port['x_cm'],port['y_cm']),xytext=(0,7),textcoords='offset points',ha='center',fontsize=9,color='#26384b',bbox={'facecolor':'white','edgecolor':'none','pad':.2})
    fig.suptitle('质量模型 AA｜顶部盖与 12 个管路通孔',fontsize=22,y=.94)
    fig.text(.06,.88,'顶盖孔与现有管路同轴；BGO 孔按管身外径避让，Al 孔按顶部套筒外径避让，径向间隙均为 0.5 mm。',fontsize=12,color='#526373')
    fig.text(.06,.16,'01 回气管   02 泵送/充气管   03 真空服务管   04–12 微型线缆/气路管',fontsize=12)
    bdiam=[round(p['hole_radius_cm']*20,2) for p in manifest['BGO_top']['ports']]
    adiam=[round(p['hole_radius_cm']*20,2) for p in manifest['Al_top']['ports']]
    fig.text(.06,.11,f'BGO 孔径（mm）：01 = {bdiam[0]:g}，02 = {bdiam[1]:g}，03 = {bdiam[2]:g}，04–12 = {bdiam[3]:g}',fontsize=11)
    fig.text(.06,.065,f'Al 孔径（mm）：01 = {adiam[0]:g}，02 = {adiam[1]:g}，03 = {adiam[2]:g}，04–12 = {adiam[3]:g}',fontsize=11)
    return fig

def physical_meshes(meshes):
    """Subtract vacuum daughter holes from plate display meshes using VTK contours.

    Geant4 exports mothers and daughters separately. A colored WRL needs an
    explicit perforated display surface; otherwise hiding vacuum draws solid
    disks. Reuse the actual native contours, and check the resulting volume.
    """
    result=[];checks=[]
    for name,v,mesh in meshes:
        if v.get('Material')=='Vacuum': continue
        children=[m for n,w,m in meshes if w.get('Mother')==name and w.get('Material')=='Vacuum']
        if children:
            z0,z1=mesh.bounds[4:6];z=(z0+z1)/2
            append=vtk.vtkAppendPolyData()
            for part in [mesh,*children]: append.AddInputData(part.slice(normal=(0,0,1),origin=(0,0,z)))
            append.Update()
            tri=vtk.vtkContourTriangulator();tri.SetInputConnection(append.GetOutputPort());tri.Update()
            cap=pv.wrap(tri.GetOutput()).clean().triangulate();cap.points[:,2]=z0
            # Orient every planar triangle before extrusion. The legacy native
            # mesh can contain mixed face winding; VTK's extrusion propagates it.
            from collections import Counter
            tris=cap.faces.reshape(-1,4)[:,1:].copy()
            xy=cap.points[:,:2]
            for t in tris:
                a,b,c=xy[t];cross=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                if cross<0: t[1],t[2]=t[2],t[1]
            edges=[(int(t[i]),int(t[(i+1)%3])) for t in tris for i in range(3)]
            counts=Counter(tuple(sorted(e)) for e in edges)
            verts=np.vstack([cap.points,cap.points+[0,0,z1-z0]]);count=cap.n_points
            faces=[]
            for t in tris: faces.extend([3,*t[::-1],3,*(t+count)])
            for a,b in edges:
                if counts[tuple(sorted((a,b)))]==1: faces.extend([4,a,b,b+count,a+count])
            perforated=pv.PolyData(verts,np.array(faces)).triangulate()
            expected=mesh.volume-sum(m.volume for m in children)
            err=abs(perforated.volume-expected)/expected
            assert err<0.001,(name,perforated.volume,expected,err)
            checks.append({'name':name,'vacuum_holes':len(children),'native_parent_minus_daughters_volume_cm3':expected,'perforated_display_volume_cm3':perforated.volume,'relative_error':err})
            mesh=perforated
        result.append((name,v,mesh))
    (P/'audit/perforated_display_validation.json').write_text(json.dumps({'status':'PASS','plates':checks},indent=2)+'\n')
    return result

def write_wrl(meshes,path,cut=False):
    # Same actual native meshes, recolored; an additional local-y half cut exposes internals.
    eye=np.array([90.,-125.,85.]);target=np.array([8.,0.,10.]);back=eye-target;back/=np.linalg.norm(back)
    right=np.cross([0,0,1.],back);right/=np.linalg.norm(right);up=np.cross(back,right)
    rv=Rotation.from_matrix(np.column_stack([right,up,back])).as_rotvec();ang=np.linalg.norm(rv);axis=rv/ang
    camera=' '.join(f'{v:.7g}' for v in [*axis,ang])
    lines=['#VRML V2.0 utf8','# AA: geometry from native Geant4 export; coordinates in cm, global orientation retained.','WorldInfo { title "Mass model AA'+(' - cutaway' if cut else '')+'" }','Background { skyColor [1 1 1] }','NavigationInfo { type ["EXAMINE", "ANY"] headlight TRUE }',f'Viewpoint {{ description "AA overview" position 90 -125 85 orientation {camera} }}']
    count=0
    for name,v,mesh in meshes:
        material=v.get('Material','Vacuum')
        if material=='Vacuum': continue
        m=mesh.triangulate()
        if cut:
            # Keep all TES pixels, cold fingers, and W frame for useful identification;
            # section surrounding shells, plates and umbrella at y=0.
            protected=name.startswith(('TP_L','AA_W_Collimator_','Cu_ColdFinger_'))
            if not protected: m=m.clip(normal=(0,1,0),origin=(0,0,0),invert=False)
        if not m.n_points or not m.n_cells: continue
        m=m.triangulate()
        pts=m.points@ROT.T
        faces=m.faces;i=0;indices=[]
        while i<len(faces):
            n=int(faces[i]);indices.append(', '.join(map(str,faces[i+1:i+1+n]))+', -1,');i+=n+1
        color=matplotlib.colors.to_rgb(COL.get(material,'#888888'))
        alpha=0.0
        if not cut and (material in ('Aluminium','BGO','Kapton') and ('Shield' in name or 'Shell' in name or 'Jacket' in name or 'Wrap' in name or 'Can_' in name)): alpha=.7
        lines += [f'# {name}', 'Shape { appearance Appearance { material Material { diffuseColor '+' '.join(f'{c:.4f}' for c in color)+f' transparency {alpha}'+' } } geometry IndexedFaceSet { solid FALSE convex FALSE coord Coordinate { point [', *[' '.join(f'{p:.7g}' for p in row)+',' for row in pts],'] } coordIndex [',*indices,'] } }']
        count+=1
    path.write_text('\n'.join(lines)+'\n')
    return count

def main():
    meshes=load_meshes();fig=main_figure(meshes);detail=beam_figure(meshes);tops=top_figure(meshes)
    for f,name in [(fig,'AA_detailed_sections'),(detail,'AA_beam_and_cold_end'),(tops,'AA_top_covers')]:
        f.savefig(P/'figures'/f'{name}.png',dpi=180,facecolor='white')
        f.savefig(P/'figures'/f'{name}.svg',facecolor='white')
    with PdfPages(P/'figures/AA_detailed_sections.pdf') as pdf: pdf.savefig(fig);pdf.savefig(detail);pdf.savefig(tops)
    display=physical_meshes(meshes)
    counts={'full':write_wrl(display,P/'figures/Mass_model_AA.wrl'),'cutaway':write_wrl(display,P/'figures/Mass_model_AA_cutaway.wrl',True)}
    inputs=P/'figures/Mass_model_AA_native.wrl'
    (P/'audit/render_validation.json').write_text(json.dumps({'status':'PASS__AA_RENDERED','native_mesh_sha256':hashlib.sha256(inputs.read_bytes()).hexdigest(),'native_export_mesh_count':len(meshes),'TES_pixel_meshes':2256,'global_native_length_unit':'mm','plot_length_unit':'cm','cutaway_is_visualization_only':True,'colored_wrl_length_unit':'cm','rendered_wrl_solid_counts':counts,'font':FONT,'source':'Geant4 native polyhedral meshes; curved surfaces are tessellated.'},indent=2)+'\n')
    print('AA sections and WRL views rendered',counts)

if __name__=='__main__': main()
