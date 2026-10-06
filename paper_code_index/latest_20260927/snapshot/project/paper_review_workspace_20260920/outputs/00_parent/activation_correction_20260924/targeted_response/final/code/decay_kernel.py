"""Lineage response kernels, with nuclear data from the installed Geant4.

This module does not change a transport file, source, or manuscript. It keeps
the original directly-produced ancestor as a spatial/production label while
computing a separate time kernel for each actually decaying state.
"""
from pathlib import Path
import csv,collections,math,re,json
import numpy as np
from scipy.linalg import expm
O=Path(__file__).resolve().parents[1];D=O/'data'
def nubase_ground():
 units={'ys':1e-24,'zs':1e-21,'as':1e-18,'fs':1e-15,'ps':1e-12,'ns':1e-9,'us':1e-6,'ms':.001,'s':1,'m':60,'h':3600,'d':86400,'y':365.25*86400,'ky':365.25*86400*1e3,'My':365.25*86400*1e6,'Gy':365.25*86400*1e9,'Ty':365.25*86400*1e12,'Py':365.25*86400*1e15,'Ey':365.25*86400*1e18,'Zy':365.25*86400*1e21,'Yy':365.25*86400*1e24}
 out={}
 p=Path('/home/ubuntu/TES_511_Balloon/inputs/nubase/nubase_2020.txt')
 for i,line in enumerate(p.read_text().splitlines(),1):
  if line.startswith('#') or len(line)<90:continue
  try:
   a=int(line[:3]);zs=line[4:8];z=int(zs[:3]);state=zs[3:]
  except ValueError:continue
  if state not in ['','0']:continue
  if 'stbl' in line[69:90].lower():hl=math.inf
  else:
   try:hl=float(re.sub(r'[#?><~*&]','',line[69:78]).strip())*units[line[78:80].strip()]
   except (KeyError,ValueError):continue
  out[z*1000+a]=(hl,i)
 return out
class NuclearData:
 def __init__(self,prefix='geant4_native_ground'):
  self.prefix=prefix
  self.states={r['name']:dict(za=int(r['za']),exc=float(r['exc_keV']),tau=float(r['lifetime_s']),stable=int(r['stable']),channels=int(r['n_channels'])) for r in csv.DictReader((D/(prefix+'_states.tsv')).open(),delimiter='\t')}
  self.bykey={(s['za'],round(s['exc'],3)):n for n,s in self.states.items() if s['exc']==0 or round(s['exc'],3)!=0}
  self.adj=collections.defaultdict(collections.Counter);self.dropped=[]
  for r in csv.DictReader((D/(prefix+'_channels.tsv')).open(),delimiter='\t'):
   if int(r['daughter_za'])<=2004:continue # emitted alpha/p/n, not residual ion
   n=r['parent'];d=r['daughter'];p=float(r['br'])
   if n==d:self.dropped.append((n,'self_loop',p));continue
   self.adj[n][d]+=p
  self.nubase=nubase_ground()
  self.valid=collections.Counter()
  for r in csv.DictReader((D/(prefix+'_outcomes.tsv')).open(),delimiter='\t'):
   self.valid[r['parent']]+=float(r['probability'])*int(r['valid'])
 def name(self,za,exc=0):
  k=(int(za),round(float(exc),3))
  if k in self.bykey:return self.bykey[k]
  choices=[(abs(s['exc']-exc),n) for n,s in self.states.items() if s['za']==za]
  d,n=min(choices)
  if d>.101:raise KeyError(k)
  return n
 def tau(self,n,physical=False):
  s=self.states[n]
  if physical and s['exc']<.001 and s['za'] in self.nubase and self.name(s['za'])==n:return self.nubase[s['za']][0]/math.log(2)
  return (math.inf if s['exc']==0 else 0.) if s['stable'] or s['tau']<0 else s['tau']
class LineageKernel:
 def __init__(self,data,root,fast_cut_s=1e-4):
  self.data=data;self.root=root;self.fast_cut=fast_cut_s;self.unresolved=[]
  reachable=set();pending=[root]
  while pending:
   n=pending.pop()
   if n in reachable:continue
   reachable.add(n)
   if data.states[n]['channels'] and sum(data.adj[n].values())<.9999:self.unresolved.append((n,sum(data.adj[n].values())))
   pending.extend(data.adj[n])
  # Nondecaying residuals are sinks. Excited fast levels are eliminated from
  # the ODE, while their emission multiplicities remain explicit outputs.
  self.slow=[root]+sorted(n for n in reachable if n!=root and data.adj[n] and data.tau(n)>=fast_cut_s and math.isfinite(data.tau(n)))
  self.fast=sorted(n for n in reachable if n not in self.slow and data.adj[n] and data.tau(n)<fast_cut_s)
  self.sidx={n:i for i,n in enumerate(self.slow)};self.fidx={n:i for i,n in enumerate(self.fast)}
  self.names=self.slow+self.fast;self.idx={n:i for i,n in enumerate(self.names)}
  self.B,self.F=self.collapse(False)
  self.native_B,self.native_F=self.collapse(True)
  assert np.all(self.B[0]==0),(root,self.B[0])
 def pretrial_factor(self,n):
  # Cosima first lets a secondary attempt a decay, then queues it only if
  # products were produced and the sampled lifetime exceeded 1 ns. The
  # queued ion decays anew. A one-product RDM termination never gets queued.
  if n==self.root:return 1.
  tau=self.data.tau(n)
  p=math.exp(-1e-9/tau) if 0<tau<math.inf else 0
  return 1-p+p*self.data.valid[n]
 def collapse(self,native):
  ns=len(self.slow);nf=len(self.fast);B=np.zeros((ns,ns));F=np.zeros((nf,ns));memo={};data=self.data
  def collapse(n,stack=()):
   if n in memo:return memo[n]
   if n in stack:raise ValueError(('decay_cycle',stack,n))
   v=np.zeros(ns);f=np.zeros(nf)
   if n in self.sidx:v[self.sidx[n]]=1
   elif n in self.fidx:
    f[self.fidx[n]]=1
    for d,p in data.adj[n].items():
     a,b=collapse(d,stack+(n,));q=self.pretrial_factor(n) if native else 1.;v+=p*q*a;f+=p*q*b
   memo[n]=(v,f);return v,f
  for j,n in enumerate(self.slow):
   for d,p in data.adj[n].items():
    a,b=collapse(d);B[:,j]+=p*a;F[:,j]+=p*b
  return B,F
 def matrices(self,physical=False,coincidence_s=1e-9):
  tau=np.array([self.data.tau(n,physical) for n in self.slow]);lam=np.divide(1.,tau,out=np.zeros_like(tau),where=tau>0)
  assert np.all(np.isfinite(lam))
  B,F=(self.B,self.F) if physical else (self.native_B,self.native_F)
  q=np.ones(len(tau)) if physical else np.array([self.pretrial_factor(n) for n in self.slow])
  Q=(B*q[None,:]-np.eye(len(tau)))*lam[None,:]
  C=np.vstack([np.eye(len(tau)),F*q[None,:]])*lam[None,:]
  # A source ancestor starts an event unconditionally. A subsequent state
  # starts a separate event only if its sampled lifetime exceeds the cut.
  for j,n in enumerate(self.names[1:],1):
   native=self.data.tau(n);survival=math.exp(-coincidence_s/native) if 0<native<math.inf else 0
   C[j]*=survival*(1. if physical else self.data.valid[n])
  return Q,C
 def finite_counts(self,T,coincidence_s=1e-9):
  """Expected records by state per unit constant ancestor decay rate [s]."""
  Q,C=self.matrices(False,coincidence_s);ns=len(self.slow)
  # Root activity is an externally fixed rate, not a decaying inventory here.
  A=np.zeros((ns+1,ns+1));A[1:ns,1:ns]=Q[1:,1:]
  A[1:ns,ns]=self.native_B[1:,0];A[:ns,0]=0
  # Integrate slow state populations by a second block, with a constant drive.
  M=np.zeros((2*ns+1,2*ns+1));M[:ns,:ns]=A[:ns,:ns];M[:ns,-1]=A[:ns,ns];M[ns:2*ns,:ns]=np.eye(ns)
  v=np.zeros(2*ns+1);v[-1]=1;y=expm(M*T)@v
  counts=C@y[ns:2*ns]
  # Primary emissions and their instant-cascade offspring are not in N_root.
  rootout=np.r_[np.eye(ns)[:,0],self.native_F[:,0]]
  for j,n in enumerate(self.names[1:],1):
   tau=self.data.tau(n);rootout[j]*=(math.exp(-coincidence_s/tau) if 0<tau<math.inf else 0)*self.data.valid[n]
  counts+=T*rootout
  return counts
 def mission(self,times_s,scales,coincidence_s=1e-9):
  """Rates by state for unit reference production and linear source scaling."""
  Q,C=self.matrices(True,coincidence_s);n=len(self.slow);N=np.zeros(n);out=[C@N];transitions={}
  for k in range(1,len(times_s)):
   dt=times_s[k]-times_s[k-1];M=np.zeros((n+2,n+2));M[:n,:n]=Q;M[0,n]=1;M[n,n+1]=1
   v=np.r_[N,scales[k-1],(scales[k]-scales[k-1])/dt]
   if dt not in transitions:transitions[dt]=expm(M*dt)
   N=(transitions[dt]@v)[:n];out.append(C@N)
  return np.array(out)
if __name__=='__main__':
 data=NuclearData();k=LineageKernel(data,'Zn62');print(k.names,k.B,k.unresolved)
 c=k.finite_counts(131.337);print('finite',dict(zip(k.names,c)))
 m=k.mission([0,15*86400],[1,1]);print('mission',dict(zip(k.names,m[-1])))
 expected=131.337-data.tau('Cu62')*(-math.expm1(-131.337/data.tau('Cu62')))
 assert abs(c[k.idx['Cu62']]/expected-1)<1e-5
 assert abs(m[-1,k.idx['Cu62']]-1)<1e-7
 print('Zn62 -> Cu62 analytical checks passed')
