from pathlib import Path
p=Path(__file__).parent
s=(p/'timeline_deferred.cpp').read_text().replace('nsig=0;vector','nsig=0,single_active=0;vector').replace('singles[2]+=bool(f&4);','singles[2]+=bool(f&4);single_active+=bool(f&8);').replace('if(sig||(ids.size()>1&&eb<50))','if(sig||ids.size()>1)').replace('<<last<<', '<<last<<')
needle='<<"],\\\"last_time\\\":"<<last'
assert needle in s
s=s.replace(needle,'<<"],\\\"background_singleton_active_count\\\":"<<single_active<<",\\\"last_time\\\":"<<last')
(p/'timeline_deferred.cpp').write_text(s)
s=(p/'original_analyze.py').read_text()
a=s.index('import sys');b=s.index('def wilson')
s=s[:a]+'from common import *\nimport struct\nfrom collections import Counter\n\n'+s[b:]
a=s.index('  cat=P/');b=s.index(' def evaluate(',a)
s=s[:a]+'''  self.a,_,_=background(model)
  self.s=dict(np.load(self.d/'signal_catalog.npz'))
  self.rec=np.memmap(self.d/'compact_records.bin',mode='r',dtype=DT);self.mapping=np.memmap(self.d/'compact_to_original.bin',mode='r',dtype='i8')
  self.pixel=recon(model)
'''+s[b:]
s=s.replace("bg_dual=int(j['background_singleton_counts'][2]);c=Counter()", "bg_dual=int(j['background_singleton_counts'][2]);bg_pre=int(j['background_singleton_counts'][0]);bg_active=int(j['background_singleton_active_count']);c=Counter()")
s=s.replace("bg_dual+=result['dual_final'];c['evaluated", "bg_dual+=result['dual_final'];bg_pre+=result['window'];bg_active+=result['window'] and result['bgo_pass'];c['evaluated")
s=s.replace("control_dual+=rr['dual_final']", "control_dual+=rr['dual_final'];bg_pre+=rr['window'];bg_active+=rr['window'] and rr['bgo_pass']")
s=s.replace("'background_bgo_final_count':bg_bgo", "'background_pre_count':bg_pre,'background_active_count':bg_active,'background_bgo_final_count':bg_bgo")
s=s.replace("  c=dict(c);out=", "  assert bg_pre>=bg_active>=bg_bgo and bg_dual==bg_bgo\n  c=dict(c);out=")
(p/'analyze.py').write_text(s)
