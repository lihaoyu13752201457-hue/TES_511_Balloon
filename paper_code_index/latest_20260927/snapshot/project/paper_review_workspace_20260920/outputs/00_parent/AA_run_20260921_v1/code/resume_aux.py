"""Own-run auxiliary processes share the explicitly supplied continuation deadline."""
import argparse,time
import aa_common as A
p=argparse.ArgumentParser();p.add_argument('--deadline-unix',type=float,required=True);p.add_argument('task',choices=['compact','watch']);args=p.parse_args()
if not time.time()<args.deadline_unix<=time.time()+4*3600+5:raise SystemExit('invalid continuation deadline')
A.DEADLINE=args.deadline_unix
if args.task=='compact':
    import compact_aa
    compact_aa.service(entry_script='resume_aux.py')
else:
    import deadline_watch
    deadline_watch.main()
