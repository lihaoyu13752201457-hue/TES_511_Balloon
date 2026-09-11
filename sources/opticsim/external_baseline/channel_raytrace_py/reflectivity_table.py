from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class ReflectivityParams:
    stack_id: str
    E_keV: float
    theta_rad: float
    R: float
    A: float
    T: float
    open_fraction: float
    sigma_slope_rad: float
    sigma_rough_nm: float
    source: str

    def validate(self, tol: float = 1.0e-9) -> None:
        if self.R < 0.0 or self.A < 0.0 or self.T < 0.0:
            raise ValueError("R/A/T must be non-negative")
        if abs((self.R + self.A + self.T) - 1.0) > tol:
            raise ValueError(f"R + A + T must sum to 1, got {self.R + self.A + self.T:.12g}")
        if not (0.0 <= self.open_fraction <= 1.0):
            raise ValueError("open_fraction must be within [0, 1]")
        if self.sigma_slope_rad < 0.0 or self.sigma_rough_nm < 0.0:
            raise ValueError("roughness and slope error must be non-negative")


class ReflectivityTable:
    def __init__(self, rows: Iterable[ReflectivityParams]):
        self.rows: List[ReflectivityParams] = list(rows)
        if not self.rows:
            raise ValueError("reflectivity table is empty")
        for row in self.rows:
            row.validate()

    @classmethod
    def from_csv(cls, path: str | Path) -> "ReflectivityTable":
        rows: List[ReflectivityParams] = []
        with Path(path).open(newline="") as f:
            for row in csv.DictReader(f):
                rows.append(
                    ReflectivityParams(
                        stack_id=row["stack_id"],
                        E_keV=float(row["E_keV"]),
                        theta_rad=float(row["theta_rad"]),
                        R=float(row["R"]),
                        A=float(row["A"]),
                        T=float(row["T"]),
                        open_fraction=float(row["open_fraction"]),
                        sigma_slope_rad=float(row["sigma_slope_rad"]),
                        sigma_rough_nm=float(row["sigma_rough_nm"]),
                        source=row.get("source", ""),
                    )
                )
        return cls(rows)

    @classmethod
    def constant(
        cls,
        *,
        stack_id: str,
        E_keV: float,
        R: float,
        A: float,
        T: float,
        open_fraction: float = 1.0,
        sigma_slope_rad: float = 0.0,
        sigma_rough_nm: float = 0.0,
        source: str = "constant_toy",
    ) -> "ReflectivityTable":
        return cls(
            [
                ReflectivityParams(
                    stack_id=stack_id,
                    E_keV=E_keV,
                    theta_rad=0.0,
                    R=R,
                    A=A,
                    T=T,
                    open_fraction=open_fraction,
                    sigma_slope_rad=sigma_slope_rad,
                    sigma_rough_nm=sigma_rough_nm,
                    source=source,
                )
            ]
        )

    def lookup(self, E_keV: float, theta_rad: float, stack_id: Optional[str] = None) -> ReflectivityParams:
        candidates = [r for r in self.rows if stack_id is None or r.stack_id == stack_id]
        if not candidates:
            raise KeyError(f"no rows for stack_id={stack_id!r}")
        if len(candidates) == 1 and _is_declared_toy_or_constant(candidates[0].source):
            return candidates[0]
        E_min = min(r.E_keV for r in candidates)
        E_max = max(r.E_keV for r in candidates)
        theta_min = min(r.theta_rad for r in candidates)
        theta_max = max(r.theta_rad for r in candidates)
        tol = 1.0e-12
        if E_keV < E_min - tol or E_keV > E_max + tol:
            raise ValueError(f"E_keV={E_keV} is outside table range [{E_min}, {E_max}]")
        if theta_rad < theta_min - tol or theta_rad > theta_max + tol:
            raise ValueError(f"theta_rad={theta_rad} is outside table range [{theta_min}, {theta_max}]")
        nearest_E = min({r.E_keV for r in candidates}, key=lambda E: abs(E - E_keV))
        same_E = sorted((r for r in candidates if r.E_keV == nearest_E), key=lambda r: r.theta_rad)
        if not same_E:
            return min(candidates, key=lambda r: (abs(r.E_keV - E_keV), abs(r.theta_rad - theta_rad)))
        if len(same_E) == 1:
            return same_E[0]
        if theta_rad <= same_E[0].theta_rad + tol:
            return same_E[0]
        if theta_rad >= same_E[-1].theta_rad - tol:
            return same_E[-1]
        for lower, upper in zip(same_E[:-1], same_E[1:]):
            if lower.theta_rad <= theta_rad <= upper.theta_rad:
                return _interpolate_theta(lower, upper, theta_rad)
        return min(same_E, key=lambda r: abs(r.theta_rad - theta_rad))


def _is_declared_toy_or_constant(source: str) -> bool:
    normalized = source.lower()
    return "toy" in normalized or "constant" in normalized


def _interpolate_theta(lower: ReflectivityParams, upper: ReflectivityParams, theta_rad: float) -> ReflectivityParams:
    if upper.theta_rad == lower.theta_rad:
        return lower
    f = (theta_rad - lower.theta_rad) / (upper.theta_rad - lower.theta_rad)

    def lerp(a: float, b: float) -> float:
        return a + f * (b - a)

    R = lerp(lower.R, upper.R)
    A = lerp(lower.A, upper.A)
    T = lerp(lower.T, upper.T)
    total = R + A + T
    if total > 0.0:
        R, A, T = R / total, A / total, T / total
    return ReflectivityParams(
        stack_id=lower.stack_id,
        E_keV=lower.E_keV,
        theta_rad=theta_rad,
        R=R,
        A=A,
        T=T,
        open_fraction=lerp(lower.open_fraction, upper.open_fraction),
        sigma_slope_rad=lerp(lower.sigma_slope_rad, upper.sigma_slope_rad),
        sigma_rough_nm=lerp(lower.sigma_rough_nm, upper.sigma_rough_nm),
        source=f"{lower.source}:theta_interpolated",
    )
