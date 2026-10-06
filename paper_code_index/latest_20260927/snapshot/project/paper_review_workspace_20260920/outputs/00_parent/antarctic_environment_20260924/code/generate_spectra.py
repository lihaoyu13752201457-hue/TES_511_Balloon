from pathlib import Path
import subprocess,csv,json,hashlib,io,math
import numpy as np
O=Path(__file__).resolve().parents[1];W=O.parents[2];P=W.parent
V=P/'engineering/m04_validation_geometry_handoff_20260810/02_parma_atm511_repair_20260810/vendor/parma_cpp_official_20260810'
SRC=P/'engineering/satellite_leo530_source_comparison_20260813/outputs/tables/balloon_aggregated_spectra.csv'
rows=[r for r in csv.DictReader(SRC.open()) if r['domain']=='full']
requests=''.join(f"{r['family']} {float(r['energy_keV_total']):.17g}\n" for r in rows)
all_spectra={};meta={}
for name,lat,lon in [('reference',34,100),('antarctic',-77.85,166.67)]:
    result=subprocess.run([str(O/'code/parma_point'),str(lat),str(lon),'38','118.3'],input=requests,text=True,capture_output=True,cwd=V,check=True)
    assert not result.stderr,result.stderr
    (O/'data'/f'{name}_raw.csv').write_text(result.stdout)
    lines=result.stdout.splitlines();m=lines[0].split(',');meta[name]=dict(zip(['latitude_deg','longitude_deg','altitude_km','W_index','cutoff_rigidity_GV','depth_g_cm2'],map(float,m[1:])))
    data=list(csv.DictReader(lines[1:]));assert len(data)==len(rows)
    all_spectra[name]=data
checks={}
for family in sorted({r['family'] for r in rows}):
    rr=[(float(old['differential_flux_cm2_s_keV']),float(ref['flux_20bin_cm2_s_keV']),float(ref['flux_cm2_s_keV'])) for old,ref in zip(rows,all_spectra['reference']) if old['family']==family and float(old['differential_flux_cm2_s_keV'])>0]
    a=np.array(rr)
    checks[family]={'n':len(rr),'ratio_20bin_percentiles':np.quantile(a[:,1]/a[:,0],[0,.1,.5,.9,1]).tolist(),'ratio_integrated_percentiles':np.quantile(a[:,2]/a[:,0],[0,.1,.5,.9,1]).tolist()}
report={'model':'unmodified archived official PARMA C++','W_index_fixed':118.3,'geometry_g':10,'atmosphere_implementation':'getdcpp uses iMSIS=0: US standard atmosphere, independent of latitude','source':str(SRC),'vendor':str(V),'metadata':meta,'reference_comparison':checks,'n_spectrum_points':len(rows),'transport_run':False}
(O/'data/spectra_generation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
