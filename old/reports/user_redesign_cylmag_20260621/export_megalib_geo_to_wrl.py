#!/usr/bin/env python3
"""Export a MEGAlib proxy .geo to a faceted WRL visualization.

This exporter is intentionally narrow: it covers the BRIK, PCON, Position,
Rotation, Mother, and Copy constructs used by the DEMO2 DR v3p5 geometry. The
output is a visual mesh representation of the actual .geo proxy, not a
hand-drawn schematic.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
GEOM_DIR = ROOT / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_20260621_megalib_proxy"
INTRO = GEOM_DIR / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
GEO = GEOM_DIR / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
OUT = ROOT / "outputs/reports/user_redesign_cylmag_20260621/user_cylmag_redesign.wrl"


@dataclass
class Obj:
    name: str
    material: str = "Vacuum"
    visibility: int = 1
    shape_type: str | None = None
    shape_values: list[float] = field(default_factory=list)
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0)
    mother: str | None = None
    source: str | None = None


COLORS = {
    "Ta": (0.25, 0.25, 0.32, 0.08),
    "Silicon": (0.75, 0.72, 0.62, 0.35),
    "Copper": (0.90, 0.45, 0.18, 0.35),
    "Aluminium": (0.62, 0.70, 0.80, 0.55),
    "Nb": (0.30, 0.45, 0.90, 0.35),
    "MuMetal": (0.55, 0.30, 0.70, 0.35),
    "Cryoperm": (0.55, 0.30, 0.70, 0.35),
    "W": (0.35, 0.34, 0.28, 0.20),
    "CsI": (0.15, 0.70, 0.25, 0.55),
    "Kapton": (0.95, 0.55, 0.15, 0.62),
    "Be": (0.80, 0.90, 0.95, 0.35),
    "G10": (0.20, 0.60, 0.35, 0.45),
    "StainlessSteel": (0.55, 0.56, 0.58, 0.40),
    "CuNi": (0.55, 0.45, 0.35, 0.40),
    "NbTiCableProxy": (0.20, 0.45, 0.70, 0.45),
    "Vacuum": (0.90, 0.90, 0.90, 0.88),
}


def parse_files(paths: list[Path]) -> dict[str, Obj]:
    objs: dict[str, Obj] = {}
    current: str | None = None

    def obj(name: str) -> Obj:
        if name not in objs:
            objs[name] = Obj(name=name)
        return objs[name]

    for path in paths:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            m = re.match(r"^Volume\s+(\S+)$", line)
            if m:
                current = m.group(1)
                obj(current)
                continue
            m = re.match(r"^(\S+)\.Copy\s+(\S+)$", line)
            if m:
                source, name = m.groups()
                obj(name).source = source
                current = name
                continue
            m = re.match(r"^(\S+)\.(Material|Visibility|Shape|Position|Rotation|Mother)\s+(.+)$", line)
            if not m:
                continue
            name, key, value = m.groups()
            target = obj(name)
            if key == "Material":
                target.material = value.split()[0]
            elif key == "Visibility":
                try:
                    target.visibility = int(float(value.split()[0]))
                except ValueError:
                    target.visibility = 1
            elif key == "Shape":
                parts = value.split()
                target.shape_type = parts[0]
                target.shape_values = [float(x) for x in parts[1:]]
            elif key == "Position":
                vals = [float(x) for x in value.split()[:3]]
                target.position = (vals[0], vals[1], vals[2])
            elif key == "Rotation":
                vals = [float(x) for x in value.split()[:3]]
                target.rotation = (vals[0], vals[1], vals[2])
            elif key == "Mother":
                target.mother = value.split()[0]

    for target in list(objs.values()):
        if target.source:
            source = objs[target.source]
            target.material = source.material
            target.shape_type = source.shape_type
            target.shape_values = list(source.shape_values)
            if target.visibility == 1:
                target.visibility = source.visibility
    return objs


def mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def transform_matrix(position: tuple[float, float, float], rotation: tuple[float, float, float]) -> list[list[float]]:
    rx, ry, rz = [math.radians(v) for v in rotation]

    def rot_x(a: float) -> list[list[float]]:
        c, s = math.cos(a), math.sin(a)
        return [[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]]

    def rot_y(a: float) -> list[list[float]]:
        c, s = math.cos(a), math.sin(a)
        return [[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]]

    def rot_z(a: float) -> list[list[float]]:
        c, s = math.cos(a), math.sin(a)
        return [[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]

    t = [[1, 0, 0, position[0]], [0, 1, 0, position[1]], [0, 0, 1, position[2]], [0, 0, 0, 1]]
    # MEGAlib rotations here are used as Euler-like degree triples. This order
    # is sufficient for the v3p5 proxy conventions and exact for single-axis rotations.
    return mat_mul(t, mat_mul(rot_z(rz), mat_mul(rot_y(ry), rot_x(rx))))


def apply(m: list[list[float]], p: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = p
    return (
        m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3],
        m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3],
        m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3],
    )


def global_matrix(name: str, objs: dict[str, Obj], memo: dict[str, list[list[float]]]) -> list[list[float]]:
    if name in memo:
        return memo[name]
    o = objs[name]
    local = transform_matrix(o.position, o.rotation)
    if o.mother and o.mother in objs and o.mother != "0":
        memo[name] = mat_mul(global_matrix(o.mother, objs, memo), local)
    else:
        memo[name] = local
    return memo[name]


def brik_mesh(vals: list[float]) -> tuple[list[tuple[float, float, float]], list[list[int]]]:
    hx, hy, hz = vals[:3]
    v = [
        (-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
        (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz),
    ]
    f = [[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]]
    return v, f


def pcon_mesh(vals: list[float]) -> tuple[list[tuple[float, float, float]], list[list[int]]]:
    phi0, dphi, n = vals[0], vals[1], int(vals[2])
    planes = vals[3:]
    full = abs(dphi) >= 359.999
    segs = 64 if full else max(8, int(abs(dphi) / 6) + 1)
    count = segs if full else segs + 1
    angles = [math.radians(phi0 + dphi * i / segs) for i in range(count)]
    vertices: list[tuple[float, float, float]] = []
    for j in range(n):
        z, rmin, rmax = planes[3 * j], planes[3 * j + 1], planes[3 * j + 2]
        for r in (rmax, rmin):
            for a in angles:
                vertices.append((r * math.cos(a), r * math.sin(a), z))

    def idx(j: int, ring: int, i: int) -> int:
        return j * 2 * count + ring * count + (i % count)

    faces: list[list[int]] = []
    for j in range(n - 1):
        for i in range(segs):
            faces.append([idx(j, 0, i), idx(j, 0, i + 1), idx(j + 1, 0, i + 1), idx(j + 1, 0, i)])
            rmin0 = planes[3 * j + 1]
            rmin1 = planes[3 * (j + 1) + 1]
            if rmin0 > 0 or rmin1 > 0:
                faces.append([idx(j, 1, i + 1), idx(j, 1, i), idx(j + 1, 1, i), idx(j + 1, 1, i + 1)])

    for j in (0, n - 1):
        rmin = planes[3 * j + 1]
        for i in range(segs):
            if rmin > 0:
                face = [idx(j, 0, i), idx(j, 0, i + 1), idx(j, 1, i + 1), idx(j, 1, i)]
            else:
                face = [idx(j, 0, i), idx(j, 0, i + 1), idx(j, 1, i)]
            faces.append(face if j == 0 else list(reversed(face)))

    if not full:
        for j in range(n - 1):
            for i in (0, segs):
                faces.append([idx(j, 0, i), idx(j + 1, 0, i), idx(j + 1, 1, i), idx(j, 1, i)])
    return vertices, faces


def mesh_for(o: Obj) -> tuple[list[tuple[float, float, float]], list[list[int]]] | None:
    if o.shape_type == "BRIK":
        return brik_mesh(o.shape_values)
    if o.shape_type == "PCON":
        return pcon_mesh(o.shape_values)
    return None


def shape_record(name: str, material: str, visibility: int, vertices: list[tuple[float, float, float]], faces: list[list[int]]) -> str:
    r, g, b, transparency = COLORS.get(material, (0.70, 0.70, 0.70, 0.55))
    if visibility == 0:
        transparency = min(0.82, transparency + 0.20)
    pts = ",\n".join(f"          {x:.6g} {y:.6g} {z:.6g}" for x, y, z in vertices)
    coord = ",\n".join("          " + " ".join(str(i) for i in face) + " -1" for face in faces)
    return f"""# {name}; material={material}
Shape {{
  appearance Appearance {{ material Material {{ diffuseColor {r:g} {g:g} {b:g} transparency {transparency:g} }} }}
  geometry IndexedFaceSet {{
    solid FALSE
    coord Coordinate {{
      point [
{pts}
      ]
    }}
    coordIndex [
{coord}
    ]
  }}
}}
"""


def main() -> None:
    objs = parse_files([INTRO, GEO])
    memo: dict[str, list[list[float]]] = {}
    rendered = 0
    lines = [
        "#VRML V2.0 utf8",
        'WorldInfo { title "DEMO2 DR v3p5 user redesign exported from MEGAlib .geo" }',
        'Viewpoint { position 45 -65 45 orientation 0.72 0.31 0.62 1.12 description "overview" }',
        "# Faceted export from the actual .geo proxy. Curved PCON volumes are tessellated.",
        "",
    ]
    for name in sorted(objs):
        o = objs[name]
        if not o.shape_type or name in {"WorldVolume", "InstrumentFrame"}:
            continue
        if o.material == "Vacuum":
            continue
        if not o.source and not o.mother:
            continue
        mesh = mesh_for(o)
        if mesh is None:
            continue
        matrix = global_matrix(name, objs, memo)
        vertices = [apply(matrix, p) for p in mesh[0]]
        lines.append(shape_record(name, o.material, o.visibility, vertices, mesh[1]))
        rendered += 1
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} with {rendered} rendered visible objects")


if __name__ == "__main__":
    main()
