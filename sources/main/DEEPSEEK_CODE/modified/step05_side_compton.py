#!/usr/bin/env python3
"""SH3 OptV3 Step05 side-entry Compton/FoV veto — ported from
old/code/tools/build_v3p5_centerfinger_step05_l1_response.py (2026-08-19).

Faithful copy of the pure cone/side-disk logic.  The only adaptation is that
side_entry_disk() is built from an explicit parameter block instead of the
Step09 bridge, so the OptV3 design-B beam entrance (local x=-46.0, y=0,
z=-2.8, radius 1.9 cm, rotation 45 deg) can be supplied.

Original semantics (unchanged):
  - <=1 measured hit  -> "single"                 (kept)
  - 2 hits            -> dual-order back-projected Compton cone vs side disk
  - 3..6 hits         -> CSR best-sequence enumeration + cone test
  - >6 hits           -> "reject" -> reject_kept under reject_policy="keep"
"""
from __future__ import annotations

import itertools
import math
from typing import Any

import numpy as np

ME_KEV = 511.0
PIX_HALF_X_CM = 0.075
PIX_HALF_Y_CM = 0.075
PIX_HALF_Z_CM = 0.150
N_CONE_SAMPLES = 24
MAX_ENUM_HITS = 6


def unit(v: np.ndarray) -> np.ndarray | None:
    n = float(np.linalg.norm(v))
    return None if n <= 0.0 else v / n


def rotate_y(values, angle_deg: float) -> np.ndarray:
    x, y, z = values
    a = math.radians(angle_deg)
    c = math.cos(a)
    s = math.sin(a)
    return np.asarray([c * x + s * z, y, -s * x + c * z], dtype=float)


def side_entry_disk(local_center_cm, radius_cm: float, rotation_y_deg: float) -> dict[str, Any]:
    """Build the side-entry disk from explicit parameters.

    local_center_cm: (x_plane, axis_y, axis_z) in the instrument frame.
    """
    center = rotate_y(local_center_cm, rotation_y_deg)
    normal = unit(rotate_y((1.0, 0.0, 0.0), rotation_y_deg))
    if normal is None:
        raise ValueError("bad side-entry disk normal")
    ref = np.asarray([0.0, 0.0, 1.0], dtype=float)
    if abs(float(np.dot(normal, ref))) > 0.9:
        ref = np.asarray([0.0, 1.0, 0.0], dtype=float)
    u = unit(np.cross(normal, ref))
    if u is None:
        raise ValueError("bad side-entry disk basis")
    v = unit(np.cross(normal, u))
    if v is None:
        raise ValueError("bad side-entry disk basis")
    return {
        "center_cm": center,
        "normal": normal,
        "basis_u": u,
        "basis_v": v,
        "radius_cm": float(radius_cm),
        "local_center_cm": tuple(float(x) for x in local_center_cm),
        "rotation_y_deg": float(rotation_y_deg),
    }


def representative_points_box(hit) -> np.ndarray:
    pts = []
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            for sz in (-1.0, 1.0):
                pts.append([hit.x + sx * PIX_HALF_X_CM, hit.y + sy * PIX_HALF_Y_CM, hit.z + sz * PIX_HALF_Z_CM])
    pts.append([hit.x, hit.y, hit.z])
    return np.asarray(pts, dtype=float)


def orthonormal_basis_batch(axis_hat: np.ndarray):
    ref = np.zeros_like(axis_hat)
    mask = np.abs(axis_hat[:, 2]) < 0.9
    ref[mask] = np.asarray([0.0, 0.0, 1.0])
    ref[~mask] = np.asarray([1.0, 0.0, 0.0])
    e1 = np.cross(axis_hat, ref)
    n1 = np.linalg.norm(e1, axis=1)
    valid1 = n1 > 1.0e-12
    e1[valid1] /= n1[valid1, None]
    e2 = np.cross(axis_hat, e1)
    n2 = np.linalg.norm(e2, axis=1)
    valid2 = n2 > 1.0e-12
    e2[valid2] /= n2[valid2, None]
    return e1, e2, valid1 & valid2


def compton_cos_theta(e_first: float, e_second: float) -> float:
    e0 = e_first + e_second
    ep = e_second
    if e0 <= 0 or ep <= 0:
        return float("nan")
    return 1.0 - ME_KEV * (1.0 / ep - 1.0 / e0)


def segments_intersect_disk_2d(segments: np.ndarray, radius: float) -> bool:
    if segments is None or len(segments) == 0:
        return False
    p0 = segments[:, 0, :]
    p1 = segments[:, 1, :]
    d = p1 - p0
    a = np.sum(d * d, axis=1)
    t = np.zeros(len(segments), dtype=float)
    nz = a > 1.0e-18
    if np.any(nz):
        t[nz] = -np.sum(p0[nz] * d[nz], axis=1) / a[nz]
        t[nz] = np.clip(t[nz], 0.0, 1.0)
    closest = p0 + t[:, None] * d
    r2 = np.sum(closest * closest, axis=1)
    return bool(np.any(r2 <= radius * radius))


def sample_cone_side_disk(hit1, hit2, e_first: float, e_second: float, disk: dict[str, Any]) -> tuple[bool, bool]:
    ctheta = compton_cos_theta(e_first, e_second)
    if (not np.isfinite(ctheta)) or ctheta < -1.0 or ctheta > 1.0:
        return False, False
    theta = math.acos(float(np.clip(ctheta, -1.0, 1.0)))
    reps1 = representative_points_box(hit1)
    reps2 = representative_points_box(hit2)
    p1 = np.repeat(reps1, len(reps2), axis=0)
    p2 = np.tile(reps2, (len(reps1), 1))
    axis_vec = p1 - p2
    norms = np.linalg.norm(axis_vec, axis=1)
    valid_norm = norms > 1.0e-12
    if not np.any(valid_norm):
        return True, False
    p1 = p1[valid_norm]
    axis_hat = axis_vec[valid_norm] / norms[valid_norm, None]
    e1, e2, valid_basis = orthonormal_basis_batch(axis_hat)
    if not np.any(valid_basis):
        return True, False
    p1 = p1[valid_basis]
    axis_hat = axis_hat[valid_basis]
    e1 = e1[valid_basis]
    e2 = e2[valid_basis]

    phis = np.linspace(0.0, 2.0 * math.pi, N_CONE_SAMPLES, endpoint=False)
    dirs = (
        math.cos(theta) * axis_hat[:, None, :]
        + math.sin(theta)
        * (np.cos(phis)[None, :, None] * e1[:, None, :] + np.sin(phis)[None, :, None] * e2[:, None, :])
    )
    center = np.asarray(disk["center_cm"], dtype=float)
    normal = np.asarray(disk["normal"], dtype=float)
    u = np.asarray(disk["basis_u"], dtype=float)
    v = np.asarray(disk["basis_v"], dtype=float)
    denom = np.tensordot(dirs, normal, axes=([2], [0]))
    numer = np.dot(center, normal) - np.dot(p1, normal)
    t = np.full(denom.shape, np.nan, dtype=float)
    valid_denom = np.abs(denom) > 1.0e-12
    numer_grid = np.broadcast_to(numer[:, None], denom.shape)
    t[valid_denom] = numer_grid[valid_denom] / denom[valid_denom]
    valid = valid_denom & (t > 0.0) & np.isfinite(t)
    if not np.any(valid):
        return True, False

    points = p1[:, None, :] + np.where(valid, t, 0.0)[:, :, None] * dirs
    relp = points - center
    coords = np.stack([np.tensordot(relp, u, axes=([2], [0])), np.tensordot(relp, v, axes=([2], [0]))], axis=2)
    r2 = np.sum(coords * coords, axis=2)
    if bool(np.any(valid & (r2 <= float(disk["radius_cm"]) ** 2))):
        return True, True

    segs = []
    for i in range(coords.shape[0]):
        valid_i = valid[i]
        seg_mask = valid_i & np.roll(valid_i, -1)
        idx = np.where(seg_mask)[0]
        if len(idx):
            segs.append(np.stack([coords[i, idx], coords[i, (idx + 1) % coords.shape[1]]], axis=1))
    flat_segments = np.concatenate(segs, axis=0) if segs else np.empty((0, 2, 2), dtype=float)
    return True, segments_intersect_disk_2d(flat_segments, float(disk["radius_cm"]))


def sequence_metrics(ordered: list[Any]) -> dict[str, float] | None:
    n = len(ordered)
    energies = np.asarray([h.e for h in ordered], dtype=float)
    positions = np.asarray([[h.x, h.y, h.z] for h in ordered], dtype=float)
    if np.any(~np.isfinite(energies)) or np.any(energies <= 0):
        return None
    total_e = float(np.sum(energies))
    rem_after = total_e - np.cumsum(energies)
    cos_kin = []
    theta1 = None
    for i in range(n - 1):
        if rem_after[i] <= 0:
            return None
        c = compton_cos_theta(float(energies[i]), float(rem_after[i]))
        if (not np.isfinite(c)) or c < -1.0 or c > 1.0:
            return None
        cos_kin.append(float(c))
        if i == 0:
            theta1 = math.degrees(math.acos(float(np.clip(c, -1.0, 1.0))))
    qf_terms = []
    for i in range(1, n - 1):
        u_prev = unit(positions[i] - positions[i - 1])
        u_next = unit(positions[i + 1] - positions[i])
        if u_prev is None or u_next is None:
            return None
        qf_terms.append((cos_kin[i] - float(np.dot(u_prev, u_next))) ** 2)
    return {
        "qf": float(np.sum(qf_terms)) if qf_terms else 0.0,
        "first_lever_arm": float(np.linalg.norm(positions[1] - positions[0])),
        "e_first": float(energies[0]),
        "e_after1": float(rem_after[0]),
        "theta1": float(theta1) if theta1 is not None else float("nan"),
    }


def classify_side_compton(hits: list[Any], disk: dict[str, Any], reject_policy: str) -> str:
    if len(hits) <= 1:
        return "single"
    if len(hits) == 2:
        decisions = []
        for a, b in ((hits[0], hits[1]), (hits[1], hits[0])):
            ok, intersects = sample_cone_side_disk(a, b, a.e, b.e, disk)
            if ok:
                decisions.append(intersects)
        cls = "reject" if not decisions else ("keep" if any(decisions) else "veto")
    else:
        if len(hits) > MAX_ENUM_HITS:
            cls = "reject"
        else:
            valid = []
            for perm in itertools.permutations(range(len(hits))):
                ordered = [hits[i] for i in perm]
                metrics = sequence_metrics(ordered)
                if metrics is None:
                    continue
                valid.append((metrics["qf"], -metrics["first_lever_arm"], ordered, metrics))
            if not valid:
                cls = "reject"
            else:
                _, _, ordered, metrics = sorted(valid, key=lambda x: (x[0], x[1]))[0]
                ok, intersects = sample_cone_side_disk(ordered[0], ordered[1], metrics["e_first"], metrics["e_after1"], disk)
                cls = "reject" if not ok else ("keep" if intersects else "veto")
    if cls == "reject" and reject_policy == "keep":
        return "reject_kept"
    return cls


def side_keep_from_hits(hits: list[Any], disk: dict[str, Any], reject_policy: str) -> tuple[bool, str]:
    cls = classify_side_compton(hits, disk, reject_policy)
    return cls in ("single", "keep", "reject_kept"), cls