"""Build a fail-closed 511-keV Ge111 reference and thickness independent rate."""
from pathlib import Path
import os,sys,json,math,re,io,subprocess,contextlib,hashlib
H=Path(__file__).resolve().parents[1];V=H.parent/'c_validation_20260920'
os.environ['MPLCONFIGDIR']=str(H/'tmp/mpl');os.environ['XDG_DATA_HOME']=str(H/'tmp/xdg');os.environ['MPLBACKEND']='Agg'
sys.path[:0]=[str(V/'external/xoppylib_source'),'/home/ubuntu/opticsim/.tools/crystalpy_base']
import numpy as np
import scipy.constants as C
import xraylib
from dabax.dabax_xraylib import DabaxXraylib
from xoppylib.crystals.tools import bragg_calc2
DROOT=Path('/home/ubuntu/opticsim/.tools/xdg_data/Dabax');DSPACE=3.266590088;E=511.;MOSAIC=30.;SIGMA=math.radians(MOSAIC/3600)/math.sqrt(8*math.log(2));LAMBDA=12.398419843320026/E;THETA=math.asin(LAMBDA/(2*DSPACE))
class Controlled(DabaxXraylib):
 def Crystal_GetCrystal(self,descriptor):
  if descriptor!='Ge':raise ValueError('reference restricted to Ge')
  d=super().Crystal_GetCrystal(descriptor);a=DSPACE*math.sqrt(3)
  for k in ['a','b','c']:d[k]=a
  d['volume']=a**3
  return d
 def FiAndFii(self,Z,energies):
  en=np.asarray(energies,dtype=float)
  # Validated reference-generation contract. Do not silently extrapolate.
  if Z!=32 or np.any((en<510)|(en>512)) or not np.isfinite(en).all():raise ValueError('unsupported atomic number or energy; no endpoint extrapolation')
  return np.vectorize(lambda e:xraylib.Fi(Z,float(e)))(en),np.vectorize(lambda e:xraylib.Fii(Z,float(e)))(en)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
out=H/'references/xop_corrected_v2';out.mkdir(exist_ok=False)
db=Controlled(dabax_repository=str(DROOT)+'/')
with (out/'preprocessor.log').open('w') as log,contextlib.redirect_stdout(log):
 b=bragg_calc2(descriptor='Ge',hh=1,kk=1,ll=1,temper=1,emin=510000,emax=512000,estep=1000,fileout=str(out/'ge111.bra'),material_constants_library=db)
# XOP's official v2 writer prints rn and d to only 6 decimals in scientific notation.
# Preserve full precision of those physical parameters; do not change the formula.
p=out/'ge111.bra';s=p.read_text();old=s.splitlines()[3];s=s.replace(old,f"{b['rn']:.16e} {b['dspacing']:.16e}",1)
lines=s.splitlines();idx=next(i for i,x in enumerate(lines) if x.startswith('# for each type of element-site, the number of f0 coefficients'))+1
lines[idx]=str(len(b['f0coeff'][0]))+' '+' '.join(f'{x:.17g}' for x in b['f0coeff'][0]);p.write_text('\n'.join(lines)+'\n')
rows=[];curves={}
for tmm in [1.,5.,10.218801,20.]:
 p=out/('t'+str(tmm).replace('.','p'));p.mkdir()
 inp=f'{out / "ge111.bra"}\n1\n1\n{MOSAIC/3600*2.35/math.sqrt(8*math.log(2)):.16g}\n{tmm/10:.16g}\n3\n511000\n3\n-120\n120\n481\n';(p/'xoppy.inp').write_text(inp)
 with (p/'xoppy.inp').open('rb') as f,(p/'run.log').open('wb') as log:subprocess.run([V/'external/xoppylib_source/xoppylib/bin/linux/diff_pat'],stdin=f,stdout=log,stderr=log,cwd=p,check=True,timeout=20)
 text=re.sub(r'(\d\.\d+)([-+]\d{3})(?=\s)',r'\1E\2',(p/'diff_pat.dat').read_text());a=np.loadtxt(io.StringIO(text));par=(p/'diff_pat.par').read_text();mu=float(re.search(r'Absorption coeff =\s*([\d.Ee+-]+)',par).group(1));path=tmm/10/math.cos(THETA);surv=math.exp(-mu*path)
 r=a[:,-2:];p0=r/surv;rate=-np.log1p(-2*p0)/(2*path);peak=240
 curves[tmm]=a
 rows.append({'thickness_mm':tmm,'mu_photo_cm_inv':mu,'path_cm':path,'R_peak':float(r[peak].mean()),'p0_peak':float(p0[peak].mean()),'rate_s_cm_inv':float(rate[peak,1]),'rate_p_cm_inv':float(rate[peak,0]),'mean_rate_cm_inv':float(rate[peak].mean())})
 np.savetxt(p/'curve.csv',np.c_[a[:,0],r.mean(axis=1),p0.mean(axis=1),rate.mean(axis=1)],delimiter=',',header='angle_arcsec,R_photo,p0,sigma_local_cm_inv',comments='')
base=rows[2];rate=base['mean_rate_cm_inv'];Q=rate*SIGMA*math.sqrt(2*math.pi)
# This independent Thomson structure-factor expression must agree with XOP-derived Q.
from dabax.common_tools import f0_xop
coeff=b['f0coeff'][0];q=1/(2*DSPACE);half=(len(coeff)-1)//2
f0=float(sum(coeff[i]*math.exp(-coeff[i+half+1]*q*q) for i in range(half))+coeff[half]);ff=complex(f0+xraylib.Fi(32,E),-xraylib.Fii(32,E));FH=complex(4,-4)*ff
re=C.physical_constants['classical electron radius'][0]*100;volume=(DSPACE*math.sqrt(3))**3*1e-24;lam=LAMBDA*1e-8
Q_thomson=(re**2*abs(FH)**2*lam**3/(volume**2*math.sin(2*THETA)))*(1+math.cos(2*THETA)**2)/2
report={'energy_keV':E,'d_spacing_A':DSPACE,'mosaic_fwhm_arcsec':MOSAIC,'mosaic_sigma_rad':SIGMA,'thetaB_rad':THETA,'rate_peak_cm_inv':rate,'Q_cm_inv':Q,'Q_thomson_cm_inv':Q_thomson,'Q_relative_difference':Q/Q_thomson-1,'thickness_scan':rows,'max_relative_rate_thickness_variation':max(abs(r['mean_rate_cm_inv']/rate-1) for r in rows),'XOP_input_FWHM_arcsec':MOSAIC*2.35/math.sqrt(8*math.log(2)),'XOP_empirical_sigma_conversion':2.35,'Fi':xraylib.Fi(32,E),'Fii':xraylib.Fii(32,E),'f0':f0,'F111_squared':abs(FH)**2,'xraylib_version':xraylib.__version__,'contract':'511 keV only; Ge111; ideal-imperfect mosaic, unit temperature factor; XOP mu excluded from runtime scattering rate; Geant4 supplies EM','sha256':{str(p):sha(p) for p in [out/'ge111.bra',V/'external/xoppylib_source/xoppylib/bin/linux/diff_pat',DROOT/'f0_InterTables.dat']}}
assert report['max_relative_rate_thickness_variation']<1e-6
assert abs(report['Q_relative_difference'])<1e-5,report['Q_relative_difference']
# Self-contained runtime file, fail-closed keys and provenance are mandatory.
values={'format_version':1,'energy_keV':E,'d_spacing_A':DSPACE,'mosaic_fwhm_arcsec':MOSAIC,'Q_cm_inv':Q,'sigma_peak_cm_inv':rate,'reference_thickness_mm':10.218801,'mu_photo_cm_inv':base['mu_photo_cm_inv']}
(H/'inputs/corrected_physics.dat').write_text(''.join(f'{k} {v:.17g}\n' for k,v in values.items()))
(H/'reports/reference_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
