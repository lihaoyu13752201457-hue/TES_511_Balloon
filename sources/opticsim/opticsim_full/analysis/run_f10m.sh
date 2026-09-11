#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-/tmp/opticsim_full_build_g4_11_4}"
GEANT4_DIR="${GEANT4_DIR:-${Geant4_DIR:-/home/ubuntu/software/geant4-11.4.0-install/lib/cmake/Geant4}}"
N_EVENTS="${N_EVENTS:-50000}"
SEED="${SEED:-12345}"
JOBS="${JOBS:-2}"
VARIANT="${VARIANT:-a1}"
VARIANT_KEY="${VARIANT,,}"
RUN_LABEL="${RUN_LABEL:-f10m_${VARIANT_KEY}_${N_EVENTS}_seed${SEED}}"
OUT_DIR="${OUT_DIR:-${ROOT}/runs/f10m_ge111_511line/${RUN_LABEL}}"
EXTRA_ARGS="${EXTRA_ARGS:-}"

case "${VARIANT_KEY}" in
  a1)
    RING_CONFIG="${ROOT}/data/laue/ge111_balloon511_f10m_511keV_line_config.csv"
    ROCKING_MAP="${ROOT}/data/laue/ge111_balloon511_f10m_511keV_xop_map.csv"
    ;;
  a2)
    RING_CONFIG="${ROOT}/data/laue/ge111_balloon511_f10m_511keV_line_config_a2.csv"
    ROCKING_MAP="${ROOT}/data/laue/ge111_balloon511_f10m_511keV_xop_map_a2.csv"
    ;;
  *)
    echo "unknown VARIANT=${VARIANT}; expected a1 or a2" >&2
    exit 2
    ;;
esac

if [[ ! -f "${RING_CONFIG}" || ! -f "${ROCKING_MAP}" ]]; then
  python3 "${ROOT}/tools/make_f10m_config.py"
fi

"${ROOT}/analysis/run_with_geant4_114.sh" cmake \
  -S "${ROOT}" \
  -B "${BUILD_DIR}" \
  -DGeant4_DIR="${GEANT4_DIR}" \
  -DCMAKE_BUILD_TYPE=Release

"${ROOT}/analysis/run_with_geant4_114.sh" cmake \
  --build "${BUILD_DIR}" \
  --target laue_multiring_bfull_demo \
  -j "${JOBS}"

extra_args=()
if [[ -n "${EXTRA_ARGS}" ]]; then
  read -r -a extra_args <<< "${EXTRA_ARGS}"
fi

run_cmd=(
  "${ROOT}/analysis/run_with_geant4_114.sh" "${BUILD_DIR}/laue_multiring_bfull_demo"
  --n "${N_EVENTS}"
  --seed "${SEED}"
  --ring-config "${RING_CONFIG}"
  --efficiency-table "${ROOT}/data/laue/Ge111_480_550keV_darwin_mosaic_table.csv"
  --rocking-curve-map "${ROCKING_MAP}"
  --require-rocking-curve-map
  --focal-mm 10000
  --out "${OUT_DIR}"
)
run_cmd+=("${extra_args[@]}")

mkdir -p "${OUT_DIR}"
{
  echo "VARIANT=${VARIANT_KEY}"
  echo "RUN_LABEL=${RUN_LABEL}"
  echo "N_EVENTS=${N_EVENTS}"
  echo "SEED=${SEED}"
  echo "EXTRA_ARGS=${EXTRA_ARGS}"
  printf "RUN_COMMAND="
  printf "%q " "${run_cmd[@]}"
  printf "\n"
} > "${OUT_DIR}/run_command.txt"

"${run_cmd[@]}"
