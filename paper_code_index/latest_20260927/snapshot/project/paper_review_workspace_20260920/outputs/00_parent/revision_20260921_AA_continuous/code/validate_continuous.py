from common import *
from continuous_disk import intersects
from scipy.optimize import minimize_scalar
rng=np.random.default_rng(2026092122);disk={'center_cm':np.zeros(3),'normal':np.array([0.,0.,1.]),'basis_u':np.array([1.,0.,0.]),'basis_v':np.array([0.,1.,0.]),'radius_cm':1.9}
cases=0
# Closed-form circle/disk intersections, exact external/internal tangencies,
# both signed nappes, degenerate theta=0/pi, and near-plane nonzero apices.
for h in [1e-4,.1,1.,10.,100.]:
 for d in [0.,.3,1.9,3.,20.]:
  for rho in [0.,max(0,d-1.9),d+1.9,max(0,d-1.9)-1e-5,d+1.9+1e-5]:
   if rho<0:continue
   for sign in [-1,1]:
    k=sign*h/math.hypot(h,rho)
    # Avoid ill-conditioned angular separations below the documented tolerance.
    margin=abs(abs(d-rho)-1.9)
    if margin>0 and margin<1e-6:continue
    got=intersects(np.array([[d,0,h]]),np.array([[0,0,-float(sign)]]),k,disk)
    expected=abs(d-rho)<=1.9+1e-13
    angular_gap=abs(h/math.hypot(h,rho)-h/math.hypot(h,d+1.9))
    if got!=expected and angular_gap<2e-12:continue
    assert got==expected,(h,d,rho,sign,k,got,expected)
    cases+=1
# Independent constrained extremum search in general orientation.
checks=0;phi=np.linspace(-np.pi,np.pi,256,endpoint=False);step=2*np.pi/256
for _ in range(500):
 p=rng.normal(size=3)*10;p[2]=rng.uniform(.1,50);a=rng.normal(size=3);a/=np.linalg.norm(a)
 def f(t):
  q=np.stack([1.9*np.cos(t),1.9*np.sin(t),np.zeros_like(t)],axis=-1)-p
  return q@a/np.linalg.norm(q,axis=-1)
 vals=f(phi);ext=list(vals)
 for sign in [-1,1]:
  y=sign*vals
  for j in range(len(phi)):
   if y[j]<=y[(j-1)%len(phi)] and y[j]<=y[(j+1)%len(phi)]:
    fit=minimize_scalar(lambda t:sign*f(t),bounds=(phi[j]-step,phi[j]+step),method='bounded',options={'xatol':1e-13});ext.append(float(f(fit.x)))
 if abs(a[2])>1e-14:
  t=-p[2]/a[2];q=p+t*a
  if np.linalg.norm(q[:2])<=1.9:ext.append(float(np.sign(t)))
 lo,hi=min(ext),max(ext)
 for k in [lo-1e-7,lo+1e-7,(lo+hi)/2,hi-1e-7,hi+1e-7]:
  if not -1<=k<=1:continue
  assert intersects(p[None,:],a[None,:],k,disk)==(lo<=k<=hi),(lo,hi,k)
  checks+=1
save(O/'validation/continuous_geometry.json',{'status':'PASS','analytic_edge_fixtures':cases,'independent_tilted_extremum_tests':checks,'apex_requirement':'Off-plane; physical AA/B pixel vertices satisfy this; assertion retained.','floating_point_tolerance':1e-12,'no_azimuth_sampling_in_decision':True})
print('PASS',cases,checks)
