from pathlib import Path
import subprocess,csv,json,io,hashlib
import numpy as np
O=Path(__file__).resolve().parents[1];W=O.parents[2];P=W.parent
V=P/'engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/vendor/parma_cpp_official_20260810'
SRC=P/'engineering/satellite_leo530_source_comparison_20260813/outputs/tables/balloon_aggregated_spectra.csv'
old=list(csv.DictReader(SRC.open()));old=[r for r in old if r['domain']=='full']
req=[];paths=[]
for family in sorted({r['family'] for r in old}):
 p=P/'expacs_fullsphere_20bin_sources/raw_expacs'/f'spectrum_{family}_bin00_theta18.19_BHNo.dat';paths.append(p)
 a=np.loadtxt(p);scale=4000 if family=='alpha' else 1000
 for e in a[:,0]*scale:req.append((family,e))
spectra={};metadata={};closure={}
for name,lat,lon in [('reference',34,100),('antarctic',-77.85,166.67)]:
 r=subprocess.run([str(O/'code/parma_point'),str(lat),str(lon),'38','118.3'],input=''.join(f'{f} {e:.17g}\n' for f,e in req),text=True,capture_output=True,cwd=V,check=True)
 lines=r.stdout.splitlines();vals=list(map(float,lines[0].split(',')[1:]));metadata[name]=dict(zip(['lat_deg','lon_deg','altitude_km','W','Rc_GV','depth_g_cm2','line511_integrated_flux_cm2_s'],vals))
 data=list(csv.DictReader(lines[1:]));spectra[name]=data
 for d in data:
  e=float(d['energy_keV_total']);continuum=float(d['flux_20bin_cm2_s_keV']);total=continuum
  # EXPACS v4.18 workbook Secondary!P95/F95 and native bin at 0.56608 MeV.
  # Exactly one coarse annihilation bump in the total-gamma contract, not an extra source.
  if d['family']=='gamma' and abs(e-566.08)<1e-5:
   norm=continuum/float(d['flux_cm2_s_keV']);total+=vals[-1]/((10**-.2-10**-.3)*1000)*norm
  d['differential_flux_cm2_s_keV']=total
 with (O/'data'/f'{name}_native.csv').open('w') as out:
  cw=csv.DictWriter(out,fieldnames=list(data[0]));cw.writeheader();cw.writerows(data)
for f in sorted({r['family'] for r in old}):
 oo=[r for r in old if r['family']==f];xx=np.array([float(r['energy_keV_total']) for r in oo]);yy=np.array([float(r['differential_flux_cm2_s_keV']) for r in oo]);dd=[r for r in spectra['reference'] if r['family']==f];nx=np.array([float(r['energy_keV_total']) for r in dd]);ny=np.array([float(r['differential_flux_cm2_s_keV']) for r in dd]);legacy=np.interp(nx,xx,yy)
 mask=legacy>0;rat=ny[mask]/legacy[mask]
 closure[f]={'n_native':len(nx),'ratio_percentiles':np.quantile(rat,[0,.1,.5,.9,1]).tolist(),'worst_E_keV':float(nx[mask][np.argmax(abs(rat-1))])}
 print(f,closure[f])
report={'metadata':metadata,'native_reference_closure':closure,'line_treatment':'EXPACS v4.18 Secondary!P95, bin width 10^-0.2 - 10^-0.3 MeV, added at native 0.56608 MeV knot before IP LIN interpolation','geometry_g':10,'atmosphere':'US Standard Atmosphere, same column at same altitude','inputs':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [SRC,V/'subroutines.cpp',P/'expacs_fullsphere_20bin_sources/_workbook/EXPACS-eng.xlsx']+paths]}
(O/'data/native_spectra_validation.json').write_text(json.dumps(report,indent=2)+'\n')
