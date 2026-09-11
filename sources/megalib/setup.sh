#!/bin/bash

# MEGAlib Forced Offline Setup - Absolute Path Version
TIMESTART=$(date +%s)

# --- 1. 强制使用绝对路径 ---
MEGALIB_ROOT_PATH=$(cd "$(dirname "$0")"; pwd)
export MEGALIB="${MEGALIB_ROOT_PATH}" 

EXTERNAL_PATH="${MEGALIB_ROOT_PATH}/external"
MAXTHREADS=4
PATCH="on"

echo " "
echo "Setting up MEGAlib (Forced Absolute Path Mode)"
echo "=================================================="
echo " * MEGAlib Home: ${MEGALIB_ROOT_PATH}"
echo " * External Path: ${EXTERNAL_PATH}"
echo " "

# --- 2. 准备工作目录 ---
mkdir -p "${EXTERNAL_PATH}"

# --- 3. 编译 ROOT ---
# 脚本会自动检测，如果已安装会像刚才那样直接跳过
echo "(3) Building ROOT..."
ROOT_FILE="root_v6.36.04.source.tar.gz"

if [ -f "${EXTERNAL_PATH}/${ROOT_FILE}" ]; then
    echo "Found ROOT tarball. Starting build..."
    cd "${EXTERNAL_PATH}"
    MEGALIB="${MEGALIB_ROOT_PATH}" bash "${MEGALIB_ROOT_PATH}/config/build-root.sh" --tarball="${ROOT_FILE}" --patch=${PATCH} --maxthreads=${MAXTHREADS} --keepenvironmentasis=on
else
    echo "ERROR: File NOT FOUND at ${EXTERNAL_PATH}/${ROOT_FILE}"
    exit 1
fi

# --- 4. 编译 Geant4 (版本已修正为 10.02.p03) ---
echo " "
echo "(4) Building Geant4..."
# 注意：这里改成了你下载的 10.02.p03 文件名
GEANT4_FILE="geant4.10.02.p03.tar.gz"

if [ -f "${EXTERNAL_PATH}/${GEANT4_FILE}" ]; then
    echo "Found Geant4 tarball: ${GEANT4_FILE}. Starting build..."
    cd "${EXTERNAL_PATH}"
    MEGALIB="${MEGALIB_ROOT_PATH}" bash "${MEGALIB_ROOT_PATH}/config/build-geant4.sh" --tarball="${GEANT4_FILE}" --patch=${PATCH} --maxthreads=${MAXTHREADS} --keepenvironmentasis=on
    if [ "$?" != "0" ]; then echo "ERROR: Geant4 build failed."; exit 1; fi
else
    echo "ERROR: File NOT FOUND at ${EXTERNAL_PATH}/${GEANT4_FILE}"
    echo "请确保 geant4.10.02.p03.tar.gz 已存放在 ${EXTERNAL_PATH} 目录下"
    exit 1
fi

# --- 5. 编译 MEGAlib 本体 ---
echo " "
echo "(5) Final Setup: Compiling MEGAlib"
cd "${MEGALIB_ROOT_PATH}"

# 1. 彻底屏蔽 Conda 和系统自带的旧 ROOT 路径
# 我们手动构造一个干净的 PATH，只保留系统基本工具和你刚编好的新 ROOT
NEW_ROOT_BIN="${EXTERNAL_PATH}/root_v6.36.6/bin"

if [ -d "$NEW_ROOT_BIN" ]; then
    echo "Pointing to new ROOT: $NEW_ROOT_BIN"
    # 将新 ROOT 路径放在 PATH 的最前面
    export PATH="${NEW_ROOT_BIN}:${PATH}"
    # 加载新 ROOT 的完整环境
    source "${NEW_ROOT_BIN}/thisroot.sh"
    export ROOTSYS="${EXTERNAL_PATH}/root_v6.36.6-install"
else
    echo "ERROR: New ROOT installation not found at $NEW_ROOT_BIN"
    exit 1
fi

# 2. 运行配置。注意：不带任何 --root 参数，让它自学成才
# 我们只带上你 Help 里看到的合法参数
bash configure --os=linux --optimization=strong --debug=off --updates=off

# 3. 开始编译
echo "Starting make..."
make -j${MAXTHREADS}

if [ "$?" == "0" ]; then
    echo "SUCCESS: MEGAlib installed!"
    echo "=================================================="
    echo "物理环境已就绪。每次开启新终端，请运行："
    echo "source ${MEGALIB_ROOT_PATH}/bin/source-megalib.sh"
else
    echo "ERROR: MEGAlib compilation failed."
    exit 1
fi
