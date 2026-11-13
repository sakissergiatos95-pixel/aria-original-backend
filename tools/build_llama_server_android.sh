#!/usr/bin/env bash
# Rebuild llama.cpp from the source bundled with ARIA ORIGINAL.
# This is mandatory: never package the stale prebuilt server binary.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LLAMA="$ROOT/llama.cpp"
APP_LIB="$ROOT/app/src/main/jniLibs/arm64-v8a"
fail(){ echo "[LLAMA ANDROID BUILD] ERROR: $*" >&2; exit 1; }
pass(){ echo "[LLAMA ANDROID BUILD] $*"; }

command -v cmake >/dev/null 2>&1 || fail "CMake is required in Termux."
command -v ninja >/dev/null 2>&1 || fail "Ninja is required in Termux."
[ -s "$LLAMA/CMakeLists.txt" ] || fail "Bundled llama.cpp source is missing."
grep -q 'case LLM_ARCH_QWEN3' "$LLAMA/src/llama-model.cpp" || fail "Bundled llama.cpp source does not contain Qwen3 model dispatch."

SDK="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
[ -n "$SDK" ] || fail "Set ANDROID_SDK_ROOT to the Android SDK directory."
NDK="${ANDROID_NDK_HOME:-${ANDROID_NDK_ROOT:-}}"
if [ -z "$NDK" ]; then
  if [ -d "$SDK/ndk" ]; then
    NDK="$(find "$SDK/ndk" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -n1)"
  fi
fi
[ -n "$NDK" ] && [ -s "$NDK/build/cmake/android.toolchain.cmake" ] || fail "Android NDK with CMake toolchain not found. Install an NDK and set ANDROID_NDK_HOME."
# The official NDK host compiler is a Linux/macOS/Windows host executable,
# not an Android executable. Do not mix it with Termux Clang or NDK libc++ headers.
HOST_OS="$(uname -s 2>/dev/null || echo unknown)"
HOST_ARCH="$(uname -m 2>/dev/null || echo unknown)"
if [ "$HOST_OS" = "Linux" ] && [ "$HOST_ARCH" = "aarch64" ]; then
  PREBUILT="$NDK/toolchains/llvm/prebuilt"
  if [ -d "$PREBUILT/linux-x86_64" ] && [ ! -x "$PREBUILT/linux-aarch64/bin/clang" ]; then
    fail "Ο NDK περιέχει linux-x86_64 host compiler, αλλά το Termux είναι Android aarch64. Μην αναμειγνύεις Termux Clang με NDK libc++ headers. Εκτέλεσε το πλήρες build από το .github/workflows/android-build.yml σε Linux x86_64 runner."
  fi
fi

TOOLCHAIN="$NDK/build/cmake/android.toolchain.cmake"
BUILD="$ROOT/.build-llama-android-arm64"
API="${ARIA_ANDROID_API:-30}"
JOBS="${ARIA_BUILD_JOBS:-2}"
pass "Source: $(sed -n 's/^set(LLAMA_VERSION_BASE "\([^"]*\)").*/\1/p' "$LLAMA/CMakeLists.txt" | head -n1)"
pass "NDK: $NDK; ABI: arm64-v8a; Android API: $API"

cmake -S "$LLAMA" -B "$BUILD" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="$TOOLCHAIN" \
  -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM="android-$API" \
  -DANDROID_STL=c++_shared \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_RPATH='$ORIGIN' \
  -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
  -DLLAMA_BUILD_SERVER=ON \
  -DLLAMA_BUILD_TOOLS=ON \
  -DLLAMA_BUILD_COMMON=ON \
  -DLLAMA_BUILD_EXAMPLES=OFF \
  -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_APP=OFF \
  -DLLAMA_CURL=OFF \
  -DBUILD_SHARED_LIBS=OFF \
  -DGGML_NATIVE=OFF \
  -DGGML_OPENMP=OFF \
  -DGGML_LLAMAFILE=OFF \
  -DGGML_RPC=OFF \
  -DGGML_VULKAN=OFF \
  -DGGML_OPENCL=OFF \
  -DGGML_SYCL=OFF \
  -DGGML_CUDA=OFF \
  -DGGML_METAL=OFF \
  -DGGML_BLAS=OFF

cmake --build "$BUILD" --target llama-server --parallel "$JOBS"
SERVER="$(find "$BUILD" -type f -name llama-server -perm -u+x -print -quit)"
[ -n "$SERVER" ] && [ -s "$SERVER" ] || fail "CMake did not produce the llama-server executable."

CXX_RUNTIME="$(find "$NDK/toolchains/llvm/prebuilt" -path '*/sysroot/usr/lib/aarch64-linux-android/libc++_shared.so' -type f -print -quit)"
[ -n "$CXX_RUNTIME" ] && [ -s "$CXX_RUNTIME" ] || fail "NDK libc++_shared.so for aarch64 was not found."
mkdir -p "$APP_LIB"
install -m 0755 "$SERVER" "$APP_LIB/libllama-server.so"
install -m 0644 "$CXX_RUNTIME" "$APP_LIB/libc++_shared.so"

command -v patchelf >/dev/null 2>&1 || fail "patchelf is required."
patchelf --set-rpath '$ORIGIN' "$APP_LIB/libllama-server.so"
if command -v readelf >/dev/null 2>&1; then
  readelf -h "$APP_LIB/libllama-server.so" | grep -q 'AArch64' || fail "Built server is not AArch64."
  echo "===== ELF DYNAMIC SECTION ====="
  readelf -d "$APP_LIB/libllama-server.so" || true
  echo "===== CMAKE RPATH SETTINGS ====="
  grep -E 'CMAKE_SKIP_RPATH|CMAKE_BUILD_WITH_INSTALL_RPATH|CMAKE_INSTALL_RPATH|CMAKE_EXE_LINKER_FLAGS' "$BUILD/CMakeCache.txt" || true
  readelf -d "$APP_LIB/libllama-server.so" | grep -Eq 'Library (runpath|rpath): \[\$ORIGIN\]' || fail "Built server is missing the required \$ORIGIN RPATH/RUNPATH."
fi
strings "$APP_LIB/libllama-server.so" | grep -q 'qwen3' || fail "Built server does not contain Qwen3 support marker."
pass "Qwen3-capable ARM64 server rebuilt and staged."
sha256sum "$APP_LIB/libllama-server.so" "$APP_LIB/libc++_shared.so"
