"""Independent continuous cone/disk diagnostic, not a production replacement.

For each apex p and unit axis a, the disk intersects the cone iff
min_disk a.(q-p)/|q-p| <= cos(theta) <= max_disk a.(q-p)/|q-p|.
The disk excludes the apex. Interior extrema are axial rays (+/-1);
boundary extrema solve a quartic obtained by t=tan(phi/2).
No angular grid is used. Roots and comparisons are floating point.
"""
import numpy as np

def intersects(p, a, k, disk):
    c=np.asarray(disk['center_cm']);u=np.asarray(disk['basis_u']);v=np.asarray(disk['basis_v'])
    normal=np.asarray(disk['normal']);r=float(disk['radius_cm']);w=c-p
    dist=np.linalg.norm(w,axis=1)
    assert np.all(np.abs(w@normal)>1e-8), 'This diagnostic requires an off-plane apex.'
    # Conservative angular bounds from the sphere enclosing the disk.
    alpha=np.arccos(np.clip(np.sum(a*w,axis=1)/dist,-1,1))
    beta=np.arcsin(np.minimum(1,r/dist))
    candidate=(k>=np.cos(np.minimum(np.pi,alpha+beta))-1e-12)&(k<=np.cos(np.maximum(0,alpha-beta))+1e-12)
    candidate |= dist<=r # enclosing sphere then gives no directional exclusion
    if not np.any(candidate):return False
    p=p[candidate];a=a[candidate];w=w[candidate]
    A=np.sum(a*w,axis=1);B=r*(a@u);C=r*(a@v)
    D=np.sum(w*w,axis=1)+r*r;E=2*r*(w@u);F=2*r*(w@v)
    # A few exact points prove intersection immediately if they straddle k.
    vals=np.stack([A/np.linalg.norm(w,axis=1),
                   (A+B)/np.sqrt(D+E),(A-B)/np.sqrt(D-E),
                   (A+C)/np.sqrt(D+F),(A-C)/np.sqrt(D-F)],axis=1)
    low=vals.min(axis=1);high=vals.max(axis=1)
    # Interior stationary points have q-p parallel or antiparallel to a.
    den=a@normal
    t=np.divide(w@normal,den,out=np.full_like(den,np.nan),where=np.abs(den)>1e-14)
    off=t[:,None]*a-w
    inside=np.isfinite(t)&(np.sum(off*off,axis=1)<=r*r+1e-12)
    high=np.where(inside&(t>0),1,high);low=np.where(inside&(t<0),-1,low)
    if np.any((low<=k+1e-12)&(high>=k-1e-12)):return True
    co=np.stack([2*A*F-2*B*F-4*C*D+4*C*E,
                 4*A*E-8*B*D+4*B*E-4*C*F,
                 -12*B*F,
                 4*A*E-8*B*D-4*B*E+4*C*F,
                 -2*A*F-2*B*F+4*C*D+4*C*E],axis=1)
    for i,poly in enumerate(co):
        scale=np.max(np.abs(poly))
        if scale<1e-25:continue # constant boundary function; cardinal points suffice
        poly=poly/scale
        nz=np.flatnonzero(np.abs(poly)>1e-14)
        roots=np.roots(poly[nz[0]:])
        real=roots.real[np.abs(roots.imag)<=1e-8*(1+np.abs(roots.real))]
        phi=2*np.arctan(real);cs=np.cos(phi);sn=np.sin(phi)
        f=(A[i]+B[i]*cs+C[i]*sn)/np.sqrt(D[i]+E[i]*cs+F[i]*sn)
        lo=min(low[i],np.min(f,initial=np.inf));hi=max(high[i],np.max(f,initial=-np.inf))
        if lo<=k+1e-12 and hi>=k-1e-12:return True
    return False

def make_kernel(ns):
    def continuous(hit1,hit2,e_first,e_second,disk):
        k=ns['compton_cos_theta'](e_first,e_second)
        if not np.isfinite(k) or not -1<=k<=1:return False,False
        r1=ns['representative_points_box'](hit1);r2=ns['representative_points_box'](hit2)
        p=np.repeat(r1,len(r2),axis=0);q=np.tile(r2,(len(r1),1));a=p-q;norm=np.linalg.norm(a,axis=1)
        valid=norm>1e-12
        if not np.any(valid):return True,False
        return True,intersects(p[valid],a[valid]/norm[valid,None],k,disk)
    return continuous
