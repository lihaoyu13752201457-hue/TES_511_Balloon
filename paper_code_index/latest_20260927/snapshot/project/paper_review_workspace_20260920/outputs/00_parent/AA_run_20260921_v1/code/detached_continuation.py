"""Keep authorized transport independent from the tool observation lifetime."""
from aa_common import *
import subprocess,fcntl,argparse
ap=argparse.ArgumentParser();ap.add_argument('--launch',action='store_true');args=ap.parse_args()
deadline=1789977484.7260895
receipt=ROOT/'data/detached_continuation_exit.json'
log=ROOT/'detached_continuation.log'
if args.launch:
    assert time.time()<deadline-120
    lock=(ROOT/'campaign.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if receipt.exists():raise RuntimeError('detached exit receipt already exists: explicit review needed')
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
        except OSError:continue
        if str(ROOT/'code/resume_campaign.py') in cmd and 'python' in cmd:raise RuntimeError('existing owned controller: '+proc.name)
    lock.close()
    with log.open('xb') as out:
        p=subprocess.Popen([sys.executable,str(Path(__file__).resolve())],stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,start_new_session=True,cwd=WORKSPACE)
    save(ROOT/'data/detached_continuation_launch.json',{'at':utc(),'supervisor_pid':p.pid,'log':str(log),'deadline_unix':deadline,'transport_physics_changed':False})
    print(json.dumps({'status':'DETACHED_SUPERVISOR_LAUNCHED','pid':p.pid,'log':str(log)}),flush=True)
else:
    p=subprocess.Popen([sys.executable,'-u',str(ROOT/'code/resume_campaign.py'),'--deadline-unix',str(deadline)],stdin=subprocess.DEVNULL,cwd=WORKSPACE)
    code=p.wait()
    result={'event':'PROCESS_EXIT','exit_code':code,'at':utc(),'controller_pid':p.pid,'deadline_unix':deadline}
    save(receipt,result);print(json.dumps(result),flush=True)
