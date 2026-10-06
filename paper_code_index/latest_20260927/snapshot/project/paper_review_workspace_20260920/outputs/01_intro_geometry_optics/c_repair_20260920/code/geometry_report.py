from pathlib import Path
import os,json,math
H=Path(__file__).resolve().parents[1];os.environ['MPLCONFIGDIR']=str(H/'tmp/mpl');os.environ['MPLBACKEND']='Agg'
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon,Circle
R=74.277928547;N=25;GAP=.2
square=np.array([[-9.,-9.],[9.,-9.],[9.,9.],[-9.,9.]])
def clip(p,f):
 out=[]
 for a,b in zip(p,np.roll(p,-1,axis=0)):
  fa,fb=f(a),f(b)
  if fa<=1e-12:out.append(a)
  if fa*fb<0:out.append(a+fa/(fa-fb)*(b-a))
 return np.array(out)
def poly(gap,n=N):
 p=square.copy();alpha=math.pi/n
 for sign in [-1,1]:p=clip(p,lambda v:sign*v[1]*math.cos(alpha)-(R+v[0])*math.sin(alpha)+gap/2)
 return p
def area(p):return abs(float(np.sum(np.cross(p,np.roll(p,-1,axis=0))))/2) if len(p)>=3 else 0.
def transform(p,i,n,rotate=True):
 phi=2*math.pi*i/n;c,s=math.cos(phi),math.sin(phi);matrix=np.array([[c,-s],[s,c]]) if rotate else np.eye(2);return p@matrix.T+np.array([R*c,R*s])
def intersect(a,b):
 p=a.copy()
 for v,w in zip(b,np.roll(b,-1,axis=0)):
  edge=w-v;p=clip(p,lambda x:-np.cross(edge,x-v))
  if len(p)<3:return np.empty((0,2))
 return p
chosen=poly(GAP);polys=[transform(chosen,i,N) for i in range(N)];overlap=[]
for i in range(N):
 for j in range(i+1,N):
  a=area(intersect(polys[i],polys[j]))
  if a>1e-9:overlap.append([i,j,a])
assert not overlap
old=[transform(square,i,N,False) for i in range(N)];oldpairs=[]
for i in range(N):
 for j in range(i+1,N):
  a=area(intersect(old[i],old[j]))
  if a>1e-9:oldpairs.append([i,j,a])
alt=[transform(square,i,22) for i in range(22)];assert all(area(intersect(a,b))<1e-9 for i,a in enumerate(alt) for b in alt[i+1:])
alpha=math.pi/N;inner_y=(R-9)*math.tan(alpha)-GAP/(2*math.cos(alpha));cut_x=(9*math.cos(alpha)+GAP/2)/math.sin(alpha)-R
obj={'status':'PASS','scope':'maximal polygon within each 18x18 mm radial/tangential square envelope and its separated 2pi/25 sector; not a global optimization over tile count/focal length/material','n_tiles':N,'radius_mm':R,'thickness_mm':10.218801,'gap_between_sector_planes_mm':GAP,'local_polygon_vertices_mm':chosen.tolist(),'inner_edge_full_width_mm':2*inner_y,'cut_starts_at_local_radial_x_mm':cut_x,'single_area_mm2':area(chosen),'total_area_cm2':N*area(chosen)/100,'retained_fraction_of_81cm2':area(chosen)/324,'trimmed_area_percent':100*(1-area(chosen)/324),'positive_overlap_pairs':overlap,'legacy_positive_overlap_pairs':oldpairs,'alternative_22_area_cm2':22*324/100,'gap_sensitivity':[{'gap_mm':g,'total_area_cm2':N*area(poly(g))/100} for g in [0,.1,.2,.5]],'proof':'Any admissible tile is a subset of square intersect sector half-planes, hence cannot have greater area than their full convex intersection. Rotated copies occupy disjoint sectors separated by the specified gap.'}
su=json.loads((H/'runs/ring25cut_s0/summary.json').read_text());assert abs(su['incident_area_cm2']-obj['total_area_cm2'])<1e-10
(H/'reports/geometry_validation.json').write_text(json.dumps(obj,indent=2)+'\n')
fig,ax=plt.subplots(1,3,figsize=(14,4.8),constrained_layout=True)
for a,pp,title,color in [(ax[0],old,'Retained placement: 16 overlapping pairs','#d15b57'),(ax[1],polys,'Proposed: 25 clipped tiles, 0.2 mm gap','#268b88')]:
 for p in pp:a.add_patch(Polygon(p,facecolor=color,edgecolor='black',alpha=.4,lw=.65))
 a.add_patch(Circle((0,0),R,fill=False,ls=':',lw=.7,color='grey'));a.set_xlim(-90,90);a.set_ylim(-90,90);a.set_aspect('equal');a.set_title(title,fontsize=10);a.set_xlabel('x (mm)');a.set_ylabel('y (mm)')
ax[2].add_patch(Polygon(square,facecolor='#f2d4d1',edgecolor='#c34343',ls='--'));ax[2].add_patch(Polygon(chosen,facecolor='#92d1cb',edgecolor='#176c68'));ax[2].set_xlim(-11,11);ax[2].set_ylim(-11,11);ax[2].set_aspect('equal');ax[2].set_xlabel('Radial coordinate relative to tile centre (mm)');ax[2].set_ylabel('Tangential coordinate (mm)');ax[2].set_title(f'One tile: {area(chosen):.3f} / 324 mm² retained',fontsize=10);ax[2].text(-8.7,0,'towards\nring centre',fontsize=8,ha='left');
fig.savefig(H/'figures/crystal_layout.png',dpi=200);fig.savefig(H/'figures/crystal_layout.pdf');plt.close(fig)
print(json.dumps(obj,indent=2))
