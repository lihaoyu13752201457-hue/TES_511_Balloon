from __future__ import annotations

import csv
import json
from pathlib import Path

from .phase_space import direction_columns


def convert_phase_space_csv(
    input_path: str | Path,
    output_path: str | Path,
    sidecar_path: str | Path | None = None,
    history_path: str | Path | None = None,
) -> dict[str, object]:
    input_path = Path(input_path)
    output_path = Path(output_path)
    if sidecar_path is None:
        sidecar_path = output_path.with_suffix(output_path.suffix + ".sidecar.json")
    sidecar_path = Path(sidecar_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    dcols = direction_columns(rows[0])
    history = _load_history(history_path)
    provenance = []
    matched_history = 0
    with output_path.open("w", encoding="utf-8") as out:
        out.write("# Laue511 phase-space EventList bridge\n")
        out.write("# event_id photon_id E_keV x_mm y_mm z_mm dx dy dz time_s weight\n")
        for row in rows:
            event_id = int(float(row["event_id"]))
            photon_id = int(float(row.get("photon_id") or row.get("track_id") or event_id))
            time_s = float(row.get("time_s") or 0.0)
            branch = _phase_branch(row)
            joined = _history_match(history, event_id, photon_id, branch)
            if joined is not None:
                matched_history += 1
            out.write(
                "EVENT "
                f"{event_id} {photon_id} {float(row['E_keV']):.12g} "
                f"{float(row['x_mm']):.12g} {float(row['y_mm']):.12g} {float(row['z_mm']):.12g} "
                f"{float(row[dcols[0]]):.12g} {float(row[dcols[1]]):.12g} {float(row[dcols[2]]):.12g} "
                f"{time_s:.12g} {float(row['weight']):.12g}\n"
            )
            provenance.append(
                {
                    "event_id": event_id,
                    "photon_id": photon_id,
                    "ring_id": _optional_int(row.get("ring_id")) if row.get("ring_id") not in (None, "") else _joined_int(joined, "ring_id"),
                    "tile_id": _optional_int(row.get("tile_id")) if row.get("tile_id") not in (None, "") else _joined_int(joined, "tile_id"),
                    "branch": branch,
                    "source_tag": row.get("source_tag", ""),
                    "offaxis_x_rad": _optional_float(row.get("offaxis_x_rad")),
                    "offaxis_y_rad": _optional_float(row.get("offaxis_y_rad")),
                    "history_joined": joined is not None,
                }
            )
    sidecar = {
        "source_csv": str(input_path),
        "eventlist": str(output_path),
        "n_rows": len(rows),
        "preserved": ["event_id", "photon_id", "E_keV", "position", "direction", "time_s", "weight", "ring_id", "tile_id", "branch", "source_tag"],
        "history_join": {
            "history_csv": str(history_path) if history_path is not None else None,
            "matched_rows": matched_history,
            "missing_rows": len(rows) - matched_history if history_path is not None else None,
        },
        "provenance": provenance,
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sidecar


def _optional_int(value: str | None) -> int | None:
    return None if value in (None, "") else int(float(value))


def _optional_float(value: str | None) -> float | None:
    return None if value in (None, "") else float(value)


def _phase_branch(row: dict[str, str]) -> str:
    if row.get("branch"):
        return row["branch"]
    if row.get("stage"):
        return row["stage"]
    if "transmitted" in row.get("source_tag", "").lower():
        return "TRANSMIT"
    return "DIFFRACT"


def _load_history(history_path: str | Path | None) -> dict[tuple[int, int, str], dict[str, str]]:
    if history_path is None:
        return {}
    lookup = {}
    with Path(history_path).open(newline="") as handle:
        for row in csv.DictReader(handle):
            if not row.get("event_id") or not row.get("track_id"):
                continue
            key = (int(float(row["event_id"])), int(float(row["track_id"])), row.get("stage", ""))
            lookup[key] = row
    return lookup


def _history_match(
    history: dict[tuple[int, int, str], dict[str, str]],
    event_id: int,
    photon_id: int,
    branch: str,
) -> dict[str, str] | None:
    if not history:
        return None
    matched = history.get((event_id, photon_id, branch))
    if matched is not None:
        return matched
    for stage in ("DIFFRACT", "TRANSMIT", "ABSORB"):
        matched = history.get((event_id, photon_id, stage))
        if matched is not None:
            return matched
    return None


def _joined_int(row: dict[str, str] | None, key: str) -> int | None:
    if row is None:
        return None
    return _optional_int(row.get(key))
