"""Deterministic reference checks; no transport, fitting, or curve renormalization."""
from pathlib import Path
import json,math,re,io,hashlib
import numpy as np
from scipy import integrate
H=Path(__file__).resolve().parents[1]
r=json.loads((H/'reports/reference_validation.json').read_text())
eta=r['mosaic_sigma_rad'];theta=r['thetaB_rad'];peak=r['rate_peak_cm_inv'];Q=r['Q_cm_inv']
rows=[]
for s in r['thickness_scan']:
 t=s['thickness_mm'];d=H/'references/xop_corrected_v2'/('t'+str(t).replace('.','p'))
 a=np.loadtxt(d/'curve.csv',delimiter=',',skiprows=1);delta=np.radians(a[:,0]/3600)
 analytic=peak*np.exp(-.5*(delta/eta)**2);gaussian_relative=float(np.max(abs(a[:,3]/analytic-1)))
 x=np.cos(theta)*np.cos(theta+delta)/eta**2
 exact=Q*np.cos(theta)/eta**2*np.exp(-2*np.sin(delta/2)**2/eta**2)*(1+1/(8*x)+9/(128*x*x))/np.sqrt(2*np.pi*x)
 text=re.sub(r'(\d\.\d+)([-+]\d{3})(?=\s)',r'\1E\2',(d/'diff_pat.dat').read_text())
 polarized=np.loadtxt(io.StringIO(text))[:,-2:];p0=polarized/np.exp(-s['mu_photo_cm_inv']*s['path_cm']);sigma=-np.log1p(-2*p0)/(2*s['path_cm'])
 Ravg=p0.mean(axis=1);Rusingmean=.5*(-np.expm1(-2*sigma.mean(axis=1)*s['path_cm']))
 # Midpoint interpolation is an input-grid diagnostic; the new runtime evaluates an analytic rate.
 mid=(delta[:-1]+delta[1:])/2;linear=(a[:-1,3]+a[1:,3])/2;truth=peak*np.exp(-.5*(mid/eta)**2)
 rows.append({'thickness_mm':t,'gaussian_max_relative_residual_full_grid':gaussian_relative,'sphere_vs_XOP_max_absolute_rate_difference_over_peak':float(np.max(abs(exact-a[:,3]))/peak),'polarization_mean_rate_max_absolute_R_error':float(np.max(abs(Rusingmean-Ravg))),'linear_grid_max_absolute_midpoint_rate_error_over_peak':float(np.max(abs(linear-truth))/peak)})
# Independent quadrature of the unnormalised Bragg-cone density in scaled coordinates.
cone=[]
for off in [-60,-30,0,18,60]:
 d=math.radians(off/3600);b=math.cos(theta)*math.cos(theta+d);k=b/eta**2
 integral=integrate.quad(lambda z:math.exp(-2*k*math.sin(z/(2*math.sqrt(k)))**2),-12,12,epsabs=1e-12,epsrel=1e-12)[0]/math.sqrt(k)
 numerical=Q*math.cos(theta)/(2*math.pi*eta**2)*math.exp(-2*math.sin(d/2)**2/eta**2)*integral
 closed=Q*math.cos(theta)/eta**2*math.exp(-2*math.sin(d/2)**2/eta**2)*(1+1/(8*k)+9/(128*k*k))/math.sqrt(2*math.pi*k)
 cone.append({'offset_arcsec':off,'quadrature_rate_cm_inv':numerical,'closed_form_relative_difference':closed/numerical-1})
maxshape=max(x['gaussian_max_relative_residual_full_grid'] for x in rows)
maxpol=max(x['polarization_mean_rate_max_absolute_R_error'] for x in rows)
assert maxshape<1e-5 and maxpol<1e-8
obj={'status':'PASS','reference_grid_rows_per_thickness':481,'grid_angles_arcsec':[-120,120],'rows':rows,'independent_cone_quadrature':cone,'runtime_has_no_rocking_curve_interpolation':True,'interpretation':'Q agreement and thickness invariance are in reference_validation.json; residuals here quantify finite XOP output precision, mean-polarization approximation, and narrow-angle sphere correction. No Monte Carlo or fitted constants.'}
(H/'reports/reference_shape_validation.json').write_text(json.dumps(obj,indent=2)+'\n')
print(json.dumps(obj,indent=2))
