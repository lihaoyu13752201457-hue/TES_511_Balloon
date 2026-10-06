"""Update three current owned blocks using numeric tokens only."""
from pathlib import Path
import json,re,hashlib
O=Path(__file__).resolve().parents[1];F=O.parent;M=F/'integrated_pixel_retention_20260920'
read=lambda p:json.loads(p.read_text())
s=read(O/'data/summary.json');b={x['id']:x for x in read(M/'translation/current_zh_blocks.json')}
assert read(O/'validation/a_source_closure.json')['status']=='PASS_SOURCE_CLOSURE'
n=s['n_focal_photons'];a=s['models']['a'];bb=s['models']['b']
replacements={
 'C027':[(r'1.5\times10^5',r'5.0\times10^4'),('37,256','37,236'),('37{,}194','37{,}175'),('1.03','0.99'),('1.25','1.17'),('3.54','3.40'),('4.30','4.02')],
 'C028':[('20.08',f"{s['optical_area_cm2']:.2f}")],
 'C058':[('28,612',f"{a['stage_counts']['narrow']['pre_veto']:,}"),('28,435',f"{bb['stage_counts']['narrow']['pre_veto']:,}"),('27,649',f"{a['stage_counts']['narrow']['compton_trajectory_veto']:,}"),('27,776',f"{bb['stage_counts']['narrow']['compton_trajectory_veto']:,}"),('96.63',f"{100*a['retention']['narrow']['compton_per_active']['fraction']:.2f}"),('97.68',f"{100*bb['retention']['narrow']['compton_per_active']['fraction']:.2f}"),('37,194',f'{n:,}'),('74.34',f"{100*a['retention']['narrow']['total_per_focal_photon']['fraction']:.2f}"),('74.68',f"{100*bb['retention']['narrow']['total_per_focal_photon']['fraction']:.2f}")]
}
strip=lambda t:re.sub(r'\d+(?:[.,]\d+)*','<NUM>',t)
patches=[];translate=(M/'code/translate_owned.py').read_text();builder=(M/'code/revise_english.py').read_text()
for i,(k,pairs) in enumerate(replacements.items(),1):
    old=b[k]['en'];new=old;zold=b[k]['zh'];znew=zold
    for x,y in pairs:
        assert new.count(x)==znew.count(x)==1,(k,x)
        new=new.replace(x,y,1);znew=znew.replace(x,y,1)
    assert strip(new)==strip(old) and strip(znew)==strip(zold)
    assert translate.count(zold)==1;translate=translate.replace(zold,znew,1)
    patches.append({'id':f'F02-N01-{i:02}','block':k,'old':old,'new':new,'old_zh':zold,'new_zh':znew,'numeric_only':True,'authority':str(O/'data/summary.json')})
assert 'F02-N01-01' not in builder
insert='# User-authorized numeric synchronization from new optical signal transport.\n'
for p in patches:
    insert+=f"change({p['id']!r},{p['old']!r},{p['new']!r},'新光学样本及已验证A/B输运、500 eV响应、像素九点判选的纯数值同步；非数字字串保持不变。')\n"
    insert+="changes[-1]['authorization']='USER-VIA-FORK01-20260920-numeric-only-signal-sync'\nchanges[-1]['numeric_only']=True\n"
anchor='base=BASE.read_text();assert';assert builder.count(anchor)==1
(M/'code/revise_english.py').write_text(builder.replace(anchor,insert+anchor));(M/'code/translate_owned.py').write_text(translate)
# O033 previously reused the unchanged current source paragraph; keep its old
# numbers in the historical translation used by the cumulative comparison.
original={x['id']:x['zh'] for x in read(M/'translation/original_zh_blocks.json')}
p=M/'code/translate_original.py';t=p.read_text();anchor='assert set(T)==set(D)';assert t.count(anchor)==1
t=t.replace(anchor,"# Preserve the historical optical source numbers.\nT.update("+repr({'O033':original['O033']})+")\n"+anchor);p.write_text(t)
(O/'data/MANUSCRIPT_NUMERIC_CHANGES.json').write_text(json.dumps(patches,ensure_ascii=False,indent=2)+'\n')
print('Prepared three numeric-only English/Chinese updates; historical original unchanged.')
