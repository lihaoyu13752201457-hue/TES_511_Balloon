"""Explicit launcher; no jobs are started unless a source and seed are supplied."""
from pathlib import Path
import argparse,sys,os
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P.parent/'code'))
from targeted_environment import environment
a=argparse.ArgumentParser(description='Independent repaired Cosima; original installation is unchanged.')
a.add_argument('--mode',choices=['production','explicit-state-response'],required=True)
a.add_argument('--seed',type=int,required=True)
a.add_argument('source',type=Path)
args=a.parse_args();assert args.source.is_file() and args.seed>0
binary=P/'runtime'/('production/cosima' if args.mode=='production' else 'cosima')
e=environment(corrected=args.mode=='explicit-state-response')
e['LD_LIBRARY_PATH']=str(binary.parent/'lib')+':'+e['LD_LIBRARY_PATH']
os.execve(binary,[str(binary),'-s',str(args.seed),'-z',str(args.source.resolve())],e)
