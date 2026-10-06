"""One local watchdog; wake the agent only on terminal/exception events.
Never launches simulations and never changes the original eight-hour deadline.
"""
from aa_common import *
import signal,subprocess,traceback,shutil

def terminate_owned(pid,marker,sig=signal.SIGTERM):
    proc=Path('/proc')/str(pid)/'cmdline'
    if not proc.exists():return False
    args=proc.read_bytes().replace(b'\0',b' ').decode()
    if marker not in ('campaign.py','resume_campaign.py','compact_aa.py','resume_aux.py') or str(ROOT/'code'/marker) not in args:
        event('PID_OWNERSHIP_SKIP',pid=pid,expected_script=marker);return False
    try:os.kill(pid,sig)
    except ProcessLookupError:return False
    return True

def main():
    # Only the script waits on local state; no model turns for ordinary progress.
    while time.time()<DEADLINE-10:time.sleep(min(60,max(.1,DEADLINE-10-time.time())))
    actions=[]
    for path,marker in [(ROOT/'data/campaign_launch.json','campaign.py'),(ROOT/'data/compact_service.json','compact_aa.py')]:
        if path.exists():
            d=read(path)
            if d.get('pid'):
                marker=d.get('entry_script',marker)
                stopped=terminate_owned(d['pid'],marker)
                actions.append({'pid':d['pid'],'marker':marker,'SIGTERM_sent':stopped})
    save(ROOT/'data/deadline_actions.json',{'at':utc(),'deadline_unix':DEADLINE,'actions':actions,'free_bytes':shutil.disk_usage(DISK).free})
    time.sleep(max(0,DEADLINE-time.time()))
    for item in actions:
        item['SIGKILL_at_deadline_if_still_owned']=terminate_owned(item['pid'],item['marker'],signal.SIGKILL)
    save(ROOT/'data/deadline_actions.json',{'at':utc(),'deadline_unix':DEADLINE,'actions':actions,'free_bytes':shutil.disk_usage(DISK).free})
    print(json.dumps({'event':'AA_DEADLINE','actions':actions,'deadline_unix':DEADLINE}),flush=True)
if __name__=='__main__':main()
