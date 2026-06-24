#!/usr/bin/env python3
"""WP01 raw state-resolved activation inventory ledger.

The inventory is built directly from Cosima universal isotope-store `.dat`
files. Legacy delayed sources are not read.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, getcontext
from pathlib import Path
from typing import Any


getcontext().prec = 28

PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "01_raw_inventory"

BUILDUP = ROOT / "runs/step02_buildup_fix5_fullstat_v2"
NUBASE = ROOT / "inputs/nubase/nubase_2020.txt"
RUN_MANIFEST = BUILDUP / "run_manifest.csv"
NORMALIZATION = BUILDUP / "normalization.json"

DAY15_SECONDS = Decimal(15) * Decimal(86400)

TAG_RE = re.compile(r"Background_(?P<tag>[^_]+)_", re.IGNORECASE)
VN_RE = re.compile(r"^\s*VN\s+(\S+)\s*$")
RP_RE = re.compile(r"^\s*RP\s+(\d+)\s+([-\d.]+)\s+([-\d.eE+]+)\s*$")
TT_RE = re.compile(r"^\s*TT\s+([-\d.eE+]+)\s*$")

RE_SEG_SHIELD = re.compile(r"^(Nb_Shield|W_Shield|Cryo_Shell|BGO_Shield|Al_Shell)(?:_p\d+_z\d+)?$", re.I)
RE_TP = re.compile(r"^TP_L(?P<l>\d+)_\d+$", re.I)
RE_TESPIX = re.compile(r"^TES_Pixel_L(?P<l>\d+)$", re.I)
RE_COLLBAR = re.compile(r"^(CollBar[XY])_\d+$", re.I)

UNIT_SECONDS = {
    "ys": Decimal("1e-24"),
    "zs": Decimal("1e-21"),
    "as": Decimal("1e-18"),
    "fs": Decimal("1e-15"),
    "ps": Decimal("1e-12"),
    "ns": Decimal("1e-9"),
    "us": Decimal("1e-6"),
    "ms": Decimal("1e-3"),
    "s": Decimal("1"),
    "m": Decimal("60"),
    "h": Decimal("3600"),
    "d": Decimal("86400"),
    "y": Decimal("31557600"),
    "ky": Decimal("1e3") * Decimal("31557600"),
    "My": Decimal("1e6") * Decimal("31557600"),
    "Gy": Decimal("1e9") * Decimal("31557600"),
    "Ty": Decimal("1e12") * Decimal("31557600"),
    "Py": Decimal("1e15") * Decimal("31557600"),
    "Ey": Decimal("1e18") * Decimal("31557600"),
    "Zy": Decimal("1e21") * Decimal("31557600"),
    "Yy": Decimal("1e24") * Decimal("31557600"),
}

SYMS = [
    None, "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
    "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
    "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
    "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
    "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
]


@dataclass(frozen=True)
class RawRecord:
    source_file: str
    line_no: int
    production_tag: str
    raw_volume: str
    za: int
    exc_raw_token: str
    exc_norm: str
    count_raw: Decimal
    tt_file_s: Decimal | None


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def dec_to_str(value: Decimal | None) -> str:
    if value is None:
        return ""
    if value.is_infinite():
        return "inf"
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def dec_to_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    if value.is_infinite():
        return math.inf
    return float(value)


def normalize_decimal_token(token: str) -> str:
    try:
        value = Decimal(token.strip())
    except InvalidOperation:
        return token.strip()
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def parse_tag(path: Path) -> str:
    match = TAG_RE.search(path.name)
    return match.group("tag").lower() if match else "unknown"


def za_to_nuclide(za: int) -> str:
    z = za // 1000
    a = za % 1000
    if 0 < z < len(SYMS) and SYMS[z]:
        return f"{SYMS[z]}-{a}"
    return f"Z{za}"


def canon_vn(vn: str) -> str:
    if not vn:
        return "Other"
    match = RE_SEG_SHIELD.match(vn)
    if match:
        return match.group(1)
    match = RE_TESPIX.match(vn)
    if match:
        return f"TES_L{int(match.group('l'))}"
    if vn.startswith("TES_L"):
        return vn
    match = RE_TP.match(vn)
    if match:
        return f"TES_L{int(match.group('l'))}"
    match = RE_COLLBAR.match(vn)
    if match:
        return match.group(1)
    if vn in ("Cu_Base", "Cu_SupportPole", "CU_BASE", "CU_SUPPORT", "Copper"):
        return "Copper"
    if vn in ("Collimator", "CollimatorVac", "CollimatorEnvelope"):
        return "CollimatorVac"
    if "window" in vn.lower() or vn.lower().startswith("win"):
        return "Window"
    return vn


def parse_half_life_seconds(value: str, unit: str) -> Decimal | None:
    txt = value.strip()
    context = f"{value} {unit}".lower()
    if "stbl" in context or "stable" in context:
        return Decimal("Infinity")
    if "p-unst" in context:
        return None
    txt = re.sub(r"[#?><~*&]", "", txt).strip()
    if not txt:
        return None
    try:
        val = Decimal(txt)
    except InvalidOperation:
        return None
    u = unit.strip() or "s"
    if u in UNIT_SECONDS:
        return val * UNIT_SECONDS[u]
    ul = u.lower()
    if ul in UNIT_SECONDS:
        return val * UNIT_SECONDS[ul]
    return None


def parse_nubase_states(path: Path) -> tuple[dict[int, dict[str, dict[str, Any]]], list[dict[str, Any]]]:
    states: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    duplicates: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for lineno, line in enumerate(handle, 1):
            if len(line) < 90 or line.startswith("#"):
                continue
            try:
                a = int(line[0:3].strip())
                zstate = line[4:8].strip()
                z = int(zstate[:3])
                state_code = zstate[3:] if len(zstate) > 3 else "0"
            except ValueError:
                continue
            za = 1000 * z + a
            exc_text = line[42:54].strip()
            exc_norm = "0" if not exc_text else normalize_decimal_token(exc_text)
            state_label = line[16:17].strip()
            if exc_norm == "0":
                state_id = "gs"
            else:
                safe_exc = exc_norm.replace("-", "m").replace(".", "p")
                state_id = f"nubase_{state_code or '0'}_{state_label or 'state'}_exc_{safe_exc}keV"
            hl_field = line[69:78].strip()
            hl_unit = line[78:80].strip()
            context = line[69:90]
            hl = Decimal("Infinity") if "stbl" in context.lower() else parse_half_life_seconds(hl_field, hl_unit)
            row = {
                "za": za,
                "nuclide": za_to_nuclide(za),
                "state_id": state_id,
                "nubase_state_code": state_code or "0",
                "nubase_state_label": state_label,
                "exc_norm": exc_norm,
                "half_life_s": hl,
                "half_life_raw_value": hl_field,
                "half_life_raw_unit": hl_unit,
                "line_no": lineno,
                "raw_line": line.rstrip("\n"),
            }
            if exc_norm in states[za]:
                duplicates.append(
                    {
                        "za": za,
                        "exc_norm": exc_norm,
                        "existing_line": states[za][exc_norm]["line_no"],
                        "duplicate_line": lineno,
                    }
                )
            else:
                states[za][exc_norm] = row
    return states, duplicates


def load_run_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    out: dict[str, dict[str, str]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            dat_path = Path(row["dat_path"]).name
            out[dat_path] = row
    return out


def parse_dat_file(path: Path, manifest_rows: dict[str, dict[str, str]]) -> tuple[list[RawRecord], list[Decimal], Decimal]:
    tag = manifest_rows.get(path.name, {}).get("particle") or parse_tag(path)
    records: list[RawRecord] = []
    tt_values: list[Decimal] = []
    current_vn = ""
    tt_current: Decimal | None = None
    raw_total = Decimal("0")
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        for line_no, raw in enumerate(handle, 1):
            stripped = raw.strip()
            m_tt = TT_RE.match(stripped)
            if m_tt:
                tt_current = Decimal(m_tt.group(1))
                tt_values.append(tt_current)
                continue
            m_vn = VN_RE.match(stripped)
            if m_vn:
                current_vn = m_vn.group(1)
                continue
            m_rp = RP_RE.match(stripped)
            if m_rp:
                count = Decimal(m_rp.group(3))
                raw_total += count
                records.append(
                    RawRecord(
                        source_file=rel(path),
                        line_no=line_no,
                        production_tag=tag,
                        raw_volume=current_vn,
                        za=int(m_rp.group(1)),
                        exc_raw_token=m_rp.group(2),
                        exc_norm=normalize_decimal_token(m_rp.group(2)),
                        count_raw=count,
                        tt_file_s=tt_current,
                    )
                )
    return records, tt_values, raw_total


def activity_after_exposure(production_rate_s: Decimal, half_life_s: Decimal) -> Decimal:
    if production_rate_s <= 0:
        return Decimal("0")
    if half_life_s.is_infinite():
        return Decimal("0")
    if half_life_s <= 0:
        return Decimal("0")
    lam = Decimal(str(math.log(2.0))) / half_life_s
    exponent = -float(lam * DAY15_SECONDS)
    return production_rate_s * Decimal(str(1.0 - math.exp(exponent)))


def resolve_state(za: int, exc_norm: str, nubase: dict[int, dict[str, dict[str, Any]]]) -> tuple[str, dict[str, Any] | None]:
    by_exc = nubase.get(za, {})
    if exc_norm in by_exc:
        return "MATCHED", by_exc[exc_norm]
    return "UNKNOWN_STATE", None


def classify(count_raw: Decimal, state_status: str, state: dict[str, Any] | None) -> str:
    if count_raw <= 0:
        return "ZERO_OR_NEGATIVE_YIELD"
    if state_status != "MATCHED" or state is None:
        return "UNKNOWN_HALF_LIFE"
    hl = state.get("half_life_s")
    if hl is None:
        return "UNKNOWN_HALF_LIFE"
    if isinstance(hl, Decimal) and hl.is_infinite():
        return "STABLE"
    return "EMITTED_CANDIDATE"


def aggregate_records(records: list[RawRecord]) -> dict[tuple[str, str, int, str], dict[str, Any]]:
    agg: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    for rec in records:
        key = (rec.production_tag, rec.raw_volume, rec.za, rec.exc_norm)
        row = agg.setdefault(
            key,
            {
                "production_tag": rec.production_tag,
                "raw_volume": rec.raw_volume,
                "canonical_volume_for_reporting_only": canon_vn(rec.raw_volume),
                "ZA": rec.za,
                "nuclide": za_to_nuclide(rec.za),
                "exc_raw_tokens": Counter(),
                "exc_keV_decimal": rec.exc_norm,
                "production_count_raw": Decimal("0"),
                "source_files": set(),
                "source_rows": 0,
                "tt_file_values": set(),
            },
        )
        row["production_count_raw"] += rec.count_raw
        row["exc_raw_tokens"][rec.exc_raw_token] += 1
        row["source_files"].add(rec.source_file)
        row["source_rows"] += 1
        if rec.tt_file_s is not None:
            row["tt_file_values"].add(rec.tt_file_s)
    return agg


def read_csv_activity_sum(path: Path) -> Decimal:
    total = Decimal("0")
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            total += Decimal(row["activity_day15_direct_Bq"])
    return total


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def run_synthetic_tests() -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        gamma_a = tmp / "Background_gamma_fullsphere20_rep01_part01.dat.inc1.dat"
        gamma_b = tmp / "Background_gamma_fullsphere20_rep01_part02.dat.inc1.dat"
        neutron_a = tmp / "Background_n_fullsphere20_rep01_part01.dat.inc1.dat"
        neutron_b = tmp / "Background_n_fullsphere20_rep02_part01.dat.inc1.dat"
        neutron_c = tmp / "Background_n_fullsphere20_rep03_part01.dat.inc1.dat"
        for path, tt, count in [
            (gamma_a, "5", "10"),
            (gamma_b, "5", "30"),
            (neutron_a, "10", "10"),
            (neutron_b, "10", "10"),
            (neutron_c, "10", "10"),
        ]:
            path.write_text(f"TT {tt}\nVN V\nRP 29064 0.00 {count}\nEN\n", encoding="utf-8")
        manifest: dict[str, dict[str, str]] = {}
        all_records: list[RawRecord] = []
        tt_by_tag: dict[str, Decimal] = defaultdict(Decimal)
        for path in [gamma_a, gamma_b, neutron_a, neutron_b, neutron_c]:
            recs, tts, _raw = parse_dat_file(path, manifest)
            all_records.extend(recs)
            tt_by_tag[parse_tag(path)] += sum(tts, Decimal("0"))
        agg = aggregate_records(all_records)
        gamma_count = agg[("gamma", "V", 29064, "0")]["production_count_raw"]
        neutron_count = agg[("n", "V", 29064, "0")]["production_count_raw"]
        gamma_rate = gamma_count / tt_by_tag["gamma"]
        neutron_rate = neutron_count / tt_by_tag["n"]
        assert gamma_rate == Decimal("4"), gamma_rate
        assert neutron_rate == Decimal("1"), neutron_rate
    print("synthetic tests PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-tests", action="store_true")
    args = parser.parse_args()
    if args.run_tests:
        run_synthetic_tests()
        return

    OUT.mkdir(parents=True, exist_ok=True)

    dat_files = sorted(BUILDUP.glob("*.dat.inc1.dat"))
    if not dat_files:
        summary = {
            "status": "BLOCKED_RAW_ACTIVATION_PRODUCTS_MISSING",
            "inputs": [],
            "outputs": [],
            "findings": ["no raw buildup .dat files found"],
            "claim_impact": ["No v2 inventory can be built."],
            "next_gate": "provide raw activation products",
            "user_decision_required": True,
        }
        write_json(OUT / "summary.json", summary)
        raise SystemExit("BLOCKED_RAW_ACTIVATION_PRODUCTS_MISSING")

    manifest_rows = load_run_manifest(RUN_MANIFEST)
    norm = json.loads(NORMALIZATION.read_text(encoding="utf-8"))
    nubase_states, duplicate_states = parse_nubase_states(NUBASE)

    all_records: list[RawRecord] = []
    dat_manifest_rows: list[dict[str, Any]] = []
    tt_by_tag: dict[str, Decimal] = defaultdict(Decimal)
    file_count_by_tag: Counter[str] = Counter()
    raw_total_by_tag: dict[str, Decimal] = defaultdict(Decimal)
    tt_line_count = 0
    tt_file_problem_count = 0

    for path in dat_files:
        records, tt_values, raw_total = parse_dat_file(path, manifest_rows)
        tag = manifest_rows.get(path.name, {}).get("particle") or parse_tag(path)
        file_count_by_tag[tag] += 1
        all_records.extend(records)
        tt_sum_file = sum(tt_values, Decimal("0"))
        tt_by_tag[tag] += tt_sum_file
        raw_total_by_tag[tag] += raw_total
        tt_line_count += len(tt_values)
        if len(tt_values) != 1:
            tt_file_problem_count += 1
        man_row = manifest_rows.get(path.name, {})
        dat_manifest_rows.append(
            {
                "source_file": rel(path),
                "production_tag": tag,
                "manifest_job_name": man_row.get("job_name", ""),
                "manifest_events": man_row.get("events", ""),
                "manifest_rep": man_row.get("rep", ""),
                "manifest_part": man_row.get("part", ""),
                "TT_file_s": dec_to_str(tt_sum_file),
                "TT_line_count": len(tt_values),
                "raw_rp_rows": len(records),
                "raw_rp_total": dec_to_str(raw_total),
            }
        )

    agg = aggregate_records(all_records)
    inventory_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    ledger_rows: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    total_activity = Decimal("0")
    total_raw = Decimal("0")
    unclassified = 0
    unknown_positive_count = 0

    state_cache: dict[tuple[int, str], tuple[str, dict[str, Any] | None]] = {}

    for key, row in sorted(agg.items()):
        tag, raw_volume, za, exc_norm = key
        state_status, state = resolve_state(za, exc_norm, nubase_states)
        state_cache[(za, exc_norm)] = (state_status, state)
        classification = classify(row["production_count_raw"], state_status, state)
        class_counts[classification] += 1
        if classification == "UNKNOWN_HALF_LIFE" and row["production_count_raw"] > 0:
            unknown_positive_count += 1
        tt_tag_sum = tt_by_tag[tag]
        production_rate = row["production_count_raw"] / tt_tag_sum if tt_tag_sum > 0 else Decimal("0")
        hl = state.get("half_life_s") if state else None
        activity = activity_after_exposure(production_rate, hl) if classification == "EMITTED_CANDIDATE" else Decimal("0")
        total_activity += activity
        total_raw += row["production_count_raw"]
        source_files_sorted = sorted(row["source_files"])
        tt_values = sorted(row["tt_file_values"])
        source_file_value = source_files_sorted[0] if len(source_files_sorted) == 1 else f"MULTIPLE:{len(source_files_sorted)}"
        tt_file_value = tt_values[0] if len(tt_values) == 1 else None
        inventory_rows.append(
            {
                "production_tag": tag,
                "source_file": source_file_value,
                "source_files_count": len(source_files_sorted),
                "source_files": ";".join(source_files_sorted),
                "raw_volume": raw_volume,
                "canonical_volume_for_reporting_only": row["canonical_volume_for_reporting_only"],
                "ZA": za,
                "nuclide": row["nuclide"],
                "exc_raw_token": ";".join(sorted(row["exc_raw_tokens"])),
                "exc_keV_decimal": exc_norm,
                "state_id": state["state_id"] if state else f"UNMATCHED_EXC_{exc_norm}",
                "nubase_line": state["line_no"] if state else "",
                "production_count_raw": dec_to_str(row["production_count_raw"]),
                "TT_file_s": dec_to_str(tt_file_value),
                "TT_tag_sum_s": dec_to_str(tt_tag_sum),
                "production_rate_s-1": dec_to_str(production_rate),
                "half_life_s": dec_to_str(hl),
                "half_life_authority": "NUBASE2020_STATE" if state else "MISSING_NUBASE_STATE",
                "activity_day15_direct_Bq": dec_to_str(activity),
                "state_class": classification,
                "source_row_count": row["source_rows"],
            }
        )

    for rec in all_records:
        state_status, state = state_cache.get((rec.za, rec.exc_norm), resolve_state(rec.za, rec.exc_norm, nubase_states))
        classification = classify(rec.count_raw, state_status, state)
        if not classification:
            unclassified += 1
            classification = "OTHER_BLOCKING_REASON"
        ledger_rows.append(
            {
                "source_file": rec.source_file,
                "line_no": rec.line_no,
                "production_tag": rec.production_tag,
                "raw_volume": rec.raw_volume,
                "canonical_volume_for_reporting_only": canon_vn(rec.raw_volume),
                "ZA": rec.za,
                "nuclide": za_to_nuclide(rec.za),
                "exc_raw_token": rec.exc_raw_token,
                "exc_keV_decimal": rec.exc_norm,
                "state_id": state["state_id"] if state else f"UNMATCHED_EXC_{rec.exc_norm}",
                "production_count_raw": dec_to_str(rec.count_raw),
                "TT_file_s": dec_to_str(rec.tt_file_s),
                "classification": classification,
                "reason": classification,
            }
        )
        source_rows.append(
            {
                "production_tag": rec.production_tag,
                "source_file": rec.source_file,
                "line_no": rec.line_no,
                "raw_volume": rec.raw_volume,
                "canonical_volume_for_reporting_only": canon_vn(rec.raw_volume),
                "ZA": rec.za,
                "nuclide": za_to_nuclide(rec.za),
                "exc_raw_token": rec.exc_raw_token,
                "exc_keV_decimal": rec.exc_norm,
                "production_count_raw": dec_to_str(rec.count_raw),
                "TT_file_s": dec_to_str(rec.tt_file_s),
            }
        )

    exposure_rows = []
    for tag in sorted(file_count_by_tag):
        exposure_rows.append(
            {
                "production_tag": tag,
                "file_count": file_count_by_tag[tag],
                "TT_tag_sum_s": dec_to_str(tt_by_tag[tag]),
                "TT_mean_file_s": dec_to_str(tt_by_tag[tag] / Decimal(file_count_by_tag[tag])),
                "raw_rp_total": dec_to_str(raw_total_by_tag[tag]),
                "base_events_by_particle": norm.get("base_events_by_particle", {}).get(tag, ""),
            }
        )

    relevant_state_keys = {(rec.za, rec.exc_norm) for rec in all_records}
    relevant_duplicate_states = [
        row for row in duplicate_states if (int(row["za"]), str(row["exc_norm"])) in relevant_state_keys
    ]
    duplicate_rows = [
        {
            "ZA": row["za"],
            "nuclide": za_to_nuclide(int(row["za"])),
            "exc_keV_decimal": row["exc_norm"],
            "existing_nubase_line": row["existing_line"],
            "duplicate_nubase_line": row["duplicate_line"],
            "scope": "RELEVANT_TO_RAW_DAT" if row in relevant_duplicate_states else "NUBASE_GLOBAL_NOT_IN_RAW_DAT",
        }
        for row in duplicate_states
    ]

    write_csv(
        OUT / "dat_file_manifest.csv",
        dat_manifest_rows,
        [
            "source_file",
            "production_tag",
            "manifest_job_name",
            "manifest_events",
            "manifest_rep",
            "manifest_part",
            "TT_file_s",
            "TT_line_count",
            "raw_rp_rows",
            "raw_rp_total",
        ],
    )
    write_csv(
        OUT / "dat_exposure_by_tag.csv",
        exposure_rows,
        ["production_tag", "file_count", "TT_tag_sum_s", "TT_mean_file_s", "raw_rp_total", "base_events_by_particle"],
    )
    inv_fields = [
        "production_tag",
        "source_file",
        "source_files_count",
        "source_files",
        "raw_volume",
        "canonical_volume_for_reporting_only",
        "ZA",
        "nuclide",
        "exc_raw_token",
        "exc_keV_decimal",
        "state_id",
        "nubase_line",
        "production_count_raw",
        "TT_file_s",
        "TT_tag_sum_s",
        "production_rate_s-1",
        "half_life_s",
        "half_life_authority",
        "activity_day15_direct_Bq",
        "state_class",
        "source_row_count",
    ]
    write_csv(OUT / "raw_inventory_all_states.csv", inventory_rows, inv_fields)
    write_csv(
        OUT / "raw_inventory_source_rows.csv",
        source_rows,
        [
            "production_tag",
            "source_file",
            "line_no",
            "raw_volume",
            "canonical_volume_for_reporting_only",
            "ZA",
            "nuclide",
            "exc_raw_token",
            "exc_keV_decimal",
            "production_count_raw",
            "TT_file_s",
        ],
    )
    write_csv(
        OUT / "activity_omission_ledger.csv",
        ledger_rows,
        [
            "source_file",
            "line_no",
            "production_tag",
            "raw_volume",
            "canonical_volume_for_reporting_only",
            "ZA",
            "nuclide",
            "exc_raw_token",
            "exc_keV_decimal",
            "state_id",
            "production_count_raw",
            "TT_file_s",
            "classification",
            "reason",
        ],
    )
    write_csv(
        OUT / "duplicate_state_audit.csv",
        duplicate_rows,
        ["ZA", "nuclide", "exc_keV_decimal", "existing_nubase_line", "duplicate_nubase_line", "scope"],
    )

    csv_total = read_csv_activity_sum(OUT / "raw_inventory_all_states.csv")
    closure_abs = abs(csv_total - total_activity)
    closure_rel = Decimal("0") if total_activity == 0 else closure_abs / total_activity
    closure = {
        "status": "PASS" if closure_rel <= Decimal("1e-10") else "FAIL",
        "activity_sum_from_builder_Bq": dec_to_str(total_activity),
        "activity_sum_from_csv_Bq": dec_to_str(csv_total),
        "absolute_delta_Bq": dec_to_str(closure_abs),
        "relative_delta": dec_to_str(closure_rel),
        "raw_rp_rows_seen": len(all_records),
        "ledger_rows": len(ledger_rows),
        "unclassified_rows": unclassified,
        "duplicate_nubase_state_rows_global": len(duplicate_states),
        "duplicate_nubase_state_rows_relevant_to_raw_dat": len(relevant_duplicate_states),
    }
    write_json(OUT / "inventory_closure.json", closure)

    status = "PASS"
    findings = [
        f"Parsed {len(dat_files)} .dat files and {len(all_records)} raw RP rows.",
        f"Direct day-15 activity sum: {dec_to_str(total_activity)} Bq.",
        f"Classification counts: {dict(sorted(class_counts.items()))}.",
    ]
    if tt_file_problem_count:
        status = "FAIL_INVENTORY_CLOSURE"
        findings.append(f"{tt_file_problem_count} files did not have exactly one TT line.")
    if relevant_duplicate_states:
        status = "BLOCKED_AMBIGUOUS_EXCITATION_STATE"
        findings.append(f"{len(relevant_duplicate_states)} duplicate NUBASE excitation-state rows are relevant to raw .dat keys.")
    elif duplicate_states:
        findings.append(
            f"{len(duplicate_states)} duplicate NUBASE excitation-state rows exist globally but none match raw .dat keys."
        )
    if unclassified:
        status = "FAIL_INVENTORY_CLOSURE"
        findings.append(f"{unclassified} raw RP rows were unclassified.")
    if closure["status"] != "PASS":
        status = "FAIL_INVENTORY_CLOSURE"
        findings.append(f"CSV activity closure relative delta {closure['relative_delta']}.")
    if unknown_positive_count and status == "PASS":
        status = "WARN"
        findings.append(f"{unknown_positive_count} positive activity keys have unknown half-life/state and are omitted explicitly.")

    raw_summary = {
        "artifact_type": "raw_inventory_summary",
        "status": status,
        "dat_file_count": len(dat_files),
        "tt_line_count": tt_line_count,
        "tt_file_problem_count": tt_file_problem_count,
        "raw_rp_rows_seen": len(all_records),
        "aggregated_full_keys": len(inventory_rows),
        "classification_counts": dict(sorted(class_counts.items())),
        "direct_activity_day15_Bq": dec_to_str(total_activity),
        "duplicate_nubase_state_rows_global": len(duplicate_states),
        "duplicate_nubase_state_rows_relevant_to_raw_dat": len(relevant_duplicate_states),
        "legacy_85p449203_Bq_is_comparator_only": True,
        "physical_key": "(production_tag, raw_logical_volume, ZA, excitation_state_id)",
        "production_rate_formula": "sum(raw RP counts for tag/key) / sum(TT for production_tag)",
        "canonical_volume_policy": "reporting only; never used for physical activity key",
        "inventory_closure": closure,
    }
    write_json(OUT / "raw_inventory_summary.json", raw_summary)

    summary = {
        "status": status,
        "inputs": [
            rel(RUN_MANIFEST),
            rel(NORMALIZATION),
            rel(NUBASE),
            f"{rel(BUILDUP)}/*.dat.inc1.dat",
        ],
        "outputs": [
            rel(OUT / "dat_file_manifest.csv"),
            rel(OUT / "dat_exposure_by_tag.csv"),
            rel(OUT / "raw_inventory_all_states.csv"),
            rel(OUT / "raw_inventory_source_rows.csv"),
            rel(OUT / "raw_inventory_summary.json"),
            rel(OUT / "raw_inventory_summary.md"),
            rel(OUT / "activity_omission_ledger.csv"),
            rel(OUT / "duplicate_state_audit.csv"),
            rel(OUT / "inventory_closure.json"),
        ],
        "findings": findings,
        "claim_impact": [
            "This is a direct-production inventory ledger, not a promoted delayed-rate authority.",
            "Legacy delayed selected rates remain comparator-only until RPIP/source/native/timing/transport gates pass.",
        ],
        "next_gate": "G2 RPIP alignment by production_tag/raw_volume/ZA/state",
        "user_decision_required": False,
    }
    write_json(OUT / "summary.json", summary)

    md = [
        "# WP01 Raw Inventory Ledger",
        "",
        f"status: `{status}`",
        f"dat files: `{len(dat_files)}`",
        f"raw RP rows: `{len(all_records)}`",
        f"aggregated full keys: `{len(inventory_rows)}`",
        f"direct day-15 activity: `{dec_to_str(total_activity)}` Bq",
        "",
        "## Formula",
        "`production_rate = sum(raw RP counts for tag/key) / sum(TT for production_tag)`",
        "",
        "## Classification Counts",
    ]
    md.extend(f"- `{k}`: `{v}`" for k, v in sorted(class_counts.items()))
    md.extend(["", "## Findings"])
    md.extend(f"- {item}" for item in findings)
    (OUT / "raw_inventory_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"WP01 {status}: wrote {rel(OUT / 'raw_inventory_summary.json')}")


if __name__ == "__main__":
    main()
