from run_suite import *
import pandas as pd
checks=[]
# Final changes are observation-only gamma step counters plus source formatting.
# Re-run the matched four settings, preserve all original physics outputs.
for old,step in [('combined_off0',1),('step0',0),('step0p2',.2),('step5',5)]:
 s=spec('release_'+old,step=step,seed=92029100);meta=run(s)
 same={f:sha(H/'runs'/old/f)==sha(H/'runs'/s['name']/f) for f in ['events.csv','exits.csv','focal.csv','diffractions.csv']}
 assert all(same.values()),same
 summary=json.loads((H/'runs'/s['name']/'summary.json').read_text());mx=summary['max_gamma_step_mm'];assert step==0 or mx<=step+1e-8
 checks.append({'name':s['name'],'base_run':old,'retained_CSV_bitwise_equal':same,'configured_max_gamma_step_mm':step,'observed_max_gamma_step_mm':mx,'n_gamma_crystal_steps':summary['n_gamma_crystal_steps'],'executable_sha256':meta['executable_sha256']})
# Negative configuration tests: fail before creating any run output.
exe=H/'build/laue511';base=[str(WR),str(exe),'--data',str(H/'inputs/corrected_physics.dat')]
guards=[]
for name,args in [('overlap',['--geometry','legacy25']),('nonfinite',['--thickness','nan']),('invalid_thickness',['--thickness','0']),('unknown_model',['--model','automatic'])]:
 out=H/'runs'/('must_not_exist_'+name);p=subprocess.run(base+['--out',str(out)]+args,cwd=H,capture_output=True,text=True,timeout=15);ok=p.returncode!=0 and not out.exists();assert ok
 guards.append({'case':name,'rejected':ok,'returncode':p.returncode,'stderr':p.stderr.strip()[-500:]})
bad=H/'tmp/bad_energy.dat';bad.write_text((H/'inputs/corrected_physics.dat').read_text().replace('energy_keV 511','energy_keV 100'))
out=H/'runs/must_not_exist_bad_energy';p=subprocess.run([str(WR),str(exe),'--data',str(bad),'--out',str(out)],cwd=H,capture_output=True,text=True,timeout=15);assert p.returncode!=0 and not out.exists();guards.append({'case':'unsupported_energy_reference','rejected':True,'stderr':p.stderr.strip()[-500:]})
p=subprocess.run(base+['--out',str(H/'runs/ring25cut_s0')],cwd=H,capture_output=True,text=True,timeout=15);assert p.returncode!=0;guards.append({'case':'overwrite','rejected':True})
(H/'reports/release_validation.json').write_text(json.dumps({'status':'PASS','observation_only_replays':checks,'n_replayed_primaries':200000,'replays_not_independent_new_statistics':True,'negative_config_tests':guards,'all_energy_and_step_checks_pass':True},indent=2)+'\n');print('Release checks PASS')
