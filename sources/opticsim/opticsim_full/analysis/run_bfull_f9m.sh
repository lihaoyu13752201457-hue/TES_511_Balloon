#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-/tmp/opticsim_full_build_g4_11_4}"
OUT_DIR="${OUT_DIR:-${ROOT}/runs/bfull_f9m_50k}"
GEANT4_DIR="${Geant4_DIR:-/home/ubuntu/software/geant4-11.4.0-install/lib/cmake/Geant4}"
N_EVENTS="${N_EVENTS:-50000}"
SEED="${SEED:-12345}"
JOBS="${JOBS:-2}"

"${ROOT}/analysis/run_with_geant4_114.sh" cmake \
  -S "${ROOT}" \
  -B "${BUILD_DIR}" \
  -DGeant4_DIR="${GEANT4_DIR}" \
  -DCMAKE_BUILD_TYPE=Release

"${ROOT}/analysis/run_with_geant4_114.sh" cmake \
  --build "${BUILD_DIR}" \
  --target laue_multiring_bfull_demo \
  -j "${JOBS}"

"${ROOT}/analysis/run_with_geant4_114.sh" "${BUILD_DIR}/laue_multiring_bfull_demo" \
  --n "${N_EVENTS}" \
  --seed "${SEED}" \
  --ring-config "${ROOT}/data/laue/ge111_balloon511_f9m_511keV_line_config.csv" \
  --efficiency-table "${ROOT}/data/laue/Ge111_480_550keV_darwin_mosaic_table.csv" \
  --rocking-curve-map "${ROOT}/data/laue/ge111_balloon511_f9m_511keV_xop_map.csv" \
  --require-rocking-curve-map \
  --focal-mm 9000 \
  --out "${OUT_DIR}"
