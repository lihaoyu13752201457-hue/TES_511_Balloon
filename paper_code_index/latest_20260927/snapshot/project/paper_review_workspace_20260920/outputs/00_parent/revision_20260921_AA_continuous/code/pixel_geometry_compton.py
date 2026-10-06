"""Pixel-only Compton reconstruction for the pinned A/B geometries.

The public measurement interface deliberately has no deposition coordinates.
Sequence ranking uses physical pixel centres; cone hypotheses use physical
vertices plus centre, with the complete pinned mother-frame transform.
Kinematics, 24-azimuth sampling, two-order OR, CSR ordering and reject-policy
are inherited unchanged from the frozen reference kernel.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import hashlib
import itertools
import math
import re
import numpy as np

@dataclass(frozen=True)
class PixelMeasurement:
    pixel_uid: str
    energy_keV: float

def canonical_uid(value):
    m=re.fullmatch(r'TP_L(\d+)_(\d+)',str(value))
    if not m: raise ValueError(value)
    return f'TP_L{int(m[1])}_{int(m[2]):05d}'

def load_kernel():
    path=Path(__file__).with_name('legacy_side_compton.py')
    ns={'__name__':'frozen_compton_kernel','__file__':str(path)}
    exec(compile(path.read_text(),str(path),'exec'),ns)
    return ns

class PixelGeometry:
    """Fail-closed parser for the actual TES copy/mother paths, not all MEGAlib."""
    def __init__(self, geometry: Path):
        self.path=Path(geometry); self.files=[]; self.records={}
        def relevant(name):
            return name in ['WorldVolume','InstrumentFrame'] or bool(re.fullmatch(r'(TES_Pixel_L\d+|TES_L\d+|TP_L\d+_\d+)',name))
        def parse(path):
            if path in self.files:return
            self.files.append(path)
            for line in path.read_text().splitlines():
                text=line.split('//')[0].strip(); f=text.split()
                if not f:continue
                if f[0].lower()=='include':
                    p=(path.parent/f[1]).resolve()
                    # Material tables contain no placement information.
                    if 'material' not in p.name.lower():parse(p)
                    continue
                if f[0]=='Volume' and relevant(f[1]):self.records.setdefault(f[1],{})
                if '.' not in f[0]:continue
                name,key=f[0].rsplit('.',1)
                if not relevant(name):continue
                r=self.records.setdefault(name,{})
                if key=='Copy':
                    assert relevant(f[1]);self.records[f[1]]=dict(r)
                elif key in ['Position','Rotation']:
                    r[key]=np.array(list(map(float,f[1:])))
                elif key=='Mother':r[key]=f[1]
                elif key=='Shape':r[key]=(f[1],np.array(list(map(float,f[2:]))))
        parse(self.path)
        self.transforms={}
        def transform(name):
            if name=='0':return np.eye(3),np.zeros(3)
            if name in self.transforms:return self.transforms[name]
            r=self.records[name]
            angles=r.get('Rotation',np.zeros(3))
            if len(angles)!=3 or angles[0]!=0 or angles[2]!=0:
                raise ValueError(('unsupported rotation needs explicit review',name,angles))
            a=math.radians(float(angles[1]));c=math.cos(a);s=math.sin(a)
            rot=np.array([[c,0,s],[0,1,0],[-s,0,c]])
            parent_r,parent_t=transform(r['Mother'])
            result=parent_r@rot,parent_t+parent_r@r.get('Position',np.zeros(3))
            self.transforms[name]=result;return result
        self.centres={};self.points={};self.halves={};self.rotations={}
        for uid,r in self.records.items():
            if not uid.startswith('TP_L'):continue
            key=canonical_uid(uid);rot,centre=transform(uid)
            shape,half=r['Shape'];assert shape=='BRIK' and half.shape==(3,)
            offsets=np.array(list(itertools.product(*[(-v,v) for v in half]))+[(0,0,0)])
            self.centres[key]=centre;self.points[key]=centre+offsets@rot.T
            self.halves[key]=half;self.rotations[key]=rot
        assert len(self.centres)==2256
        assert all(sum(k.startswith(f'TP_L{i}_') for k in self.centres)==376 for i in range(6))
        for uid,points in self.points.items():
            assert points.shape==(9,3) and len(np.unique(points,axis=0))==9
            assert np.allclose(points[:8].mean(axis=0),self.centres[uid],atol=1e-12)
            recovered=(points-self.centres[uid])@self.rotations[uid]
            assert np.allclose(np.abs(recovered[:8]),self.halves[uid],atol=1e-12)
            assert np.allclose(recovered[8],0,atol=1e-12)
        self.provenance=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in self.files]

    def centred_hit(self, measurement: PixelMeasurement):
        uid=canonical_uid(measurement.pixel_uid);p=self.centres[uid]
        return SimpleNamespace(pixel_uid=uid,layer=int(uid.split('_')[1][1:]),
                               e=measurement.energy_keV,x=p[0],y=p[1],z=p[2])

    def deposition_excess_cm(self, uid, position):
        """Audit only. This method is never used by the reconstruction."""
        uid=canonical_uid(uid)
        local=(np.array(position)-self.centres[uid])@self.rotations[uid]
        return float(max(0,np.max(np.abs(local)-self.halves[uid])))

class PixelGeometryCompton:
    def __init__(self, geometry: PixelGeometry, disk, exact_vertices=True):
        self.geometry=geometry;self.disk=disk;self.kernel=load_kernel()
        if exact_vertices:
            self.kernel['representative_points_box']=lambda hit:geometry.points[canonical_uid(hit.pixel_uid)]
        self.exact_vertices=exact_vertices

    def classify(self, measurements: list[PixelMeasurement]):
        hits=[self.geometry.centred_hit(m) for m in measurements]
        return self.kernel['side_keep_from_hits'](hits,self.disk,'keep')
