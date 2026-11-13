#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
fail(){ printf 'ERROR: %s\n' "$*" >&2; exit 1; }
pass(){ printf '[ARIA ORIGINAL] %s\n' "$*"; }

for tool in java python3 cmake ninja; do command -v "$tool" >/dev/null 2>&1 || fail "Λείπει το εργαλείο: $tool"; done
if [ ! -s "$ROOT/app/gradlew" ] && ! command -v gradle >/dev/null 2>&1; then
  fail "Λείπει το Gradle wrapper και δεν υπάρχει εγκατεστημένο Gradle."
fi
SDK="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
if [ -z "$SDK" ]; then
  for candidate in "$HOME/android-sdk" "$HOME/Android/Sdk" "${PREFIX:-/nonexistent}/share/android-sdk"; do
    if [ -s "$candidate/platforms/android-34/android.jar" ]; then SDK="$candidate"; break; fi
  done
fi
[ -n "$SDK" ] || fail "Δεν ορίστηκε Android SDK. Ρύθμισε ANDROID_SDK_ROOT στο Termux."
[ -s "$SDK/platforms/android-34/android.jar" ] || fail "Δεν βρέθηκε Android SDK Platform 34 στο $SDK"
pass "Android SDK: $SDK"
# Rebuild native runtime from the bundled llama.cpp source on every build.
# This prevents shipping the old binary that rejected Qwen3 GGUF files.
bash tools/build_llama_server_android.sh
[ -s app/src/main/jniLibs/arm64-v8a/libllama-server.so ] || fail "Λείπει το νέο llama-server ARM64"
[ -s app/src/main/jniLibs/arm64-v8a/libc++_shared.so ] || fail "Λείπει libc++_shared.so ARM64"
if command -v readelf >/dev/null 2>&1; then
  ELF_HEADER="$(readelf -h app/src/main/jniLibs/arm64-v8a/libllama-server.so)"
  [[ "$ELF_HEADER" == *AArch64* ]] || fail "Το llama-server δεν είναι ARM64"
  ELF_DYNAMIC="$(readelf -d app/src/main/jniLibs/arm64-v8a/libllama-server.so)"
  [[ "$ELF_DYNAMIC" == *'Library runpath: [$ORIGIN]'* ]] || fail "Το llama-server έχει μη φορητό RUNPATH. Αναμένεται \$ORIGIN ώστε να βρίσκει το libc++_shared.so δίπλα του."
  pass "Επιβεβαιώθηκε ELF ARM64 και φορητό RUNPATH \$ORIGIN"
fi
bash tools/verify_source.sh
# Run backend integration tests from BACKEND so its app package resolves correctly.
if python3 -c 'import pytest' >/dev/null 2>&1; then
  (cd BACKEND && python3 -m pytest -q tests)
else
  fail "Λείπει το pytest. Εγκατάστησε τις εξαρτήσεις BACKEND/requirements.txt και pytest."
fi
export ANDROID_HOME="$SDK" ANDROID_SDK_ROOT="$SDK"
pass "Εκκίνηση Gradle assembleDebug — package com.aria.original.v117"
if [ -s "$ROOT/app/gradlew" ] && [ -s "$ROOT/app/gradle/wrapper/gradle-wrapper.jar" ]; then
  chmod +x "$ROOT/app/gradlew"
  bash "$ROOT/app/gradlew" --no-daemon --stacktrace assembleDebug
else
  gradle --no-daemon --stacktrace assembleDebug
fi
APK="$ROOT/app/build/outputs/apk/debug/app-debug.apk"
[ -s "$APK" ] || fail "Το Gradle δεν παρήγαγε APK"
mkdir -p "$ROOT/output"
cp -f "$APK" "$ROOT/output/ARIA_ORIGINAL.apk"
sha256sum "$ROOT/output/ARIA_ORIGINAL.apk" | tee "$ROOT/output/ARIA_ORIGINAL.sha256"
python3 - "$ROOT/output/ARIA_ORIGINAL.apk" <<'PY'
import sys, zipfile
p=sys.argv[1]
with zipfile.ZipFile(p) as z:
    bad=z.testzip()
    if bad: raise SystemExit('APK ZIP integrity failure: '+bad)
    names=set(z.namelist())
    if 'lib/arm64-v8a/libllama-server.so' not in names: raise SystemExit('Missing llama-server ARM64 in APK')
    if 'lib/arm64-v8a/libc++_shared.so' not in names: raise SystemExit('Missing libc++_shared ARM64 in APK')
print('PASS: APK ZIP integrity and ARM64 native payload')
PY
pass "APK δημιουργήθηκε και αντιγράφηκε στο output/ARIA_ORIGINAL.apk"
