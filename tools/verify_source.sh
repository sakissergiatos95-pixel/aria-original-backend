#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
fail(){ echo "FAIL: $*" >&2; exit 1; }
pass(){ echo "PASS: $*"; }
for f in settings.gradle build.gradle gradle.properties app/build.gradle app/src/main/AndroidManifest.xml app/src/main/java/com/aria/assistant/MainActivity.java app/src/main/java/com/aria/assistant/ARIAOwnedCore.java app/src/main/java/com/aria/assistant/ARIAMemoryStore.java app/src/main/java/com/aria/assistant/ARIAAutonomyEngine.java app/src/main/java/com/aria/assistant/ApiKeyStore.java app/src/main/java/com/aria/assistant/AriaAccountClient.java app/src/main/java/com/aria/assistant/ImageEditingManager.java BACKEND/app/main.py BACKEND/render.yaml BACKEND/README_EL.md BACKEND/tests/test_owner_and_image_api.py BUILD_ARIA_ORIGINAL.sh tools/build_llama_server_android.sh; do
  [ -s "$ROOT/$f" ] || fail "Λείπει απαραίτητο αρχείο: $f"
done
bash -n BUILD_ARIA_ORIGINAL.sh || fail "Σφάλμα σύνταξης build script"
bash -n tools/build_llama_server_android.sh || fail "Σφάλμα σύνταξης native build script"
bash -n app/gradlew || fail "Σφάλμα σύνταξης Gradle wrapper"
python3 -m py_compile BACKEND/app/main.py BACKEND/tests/test_owner_and_image_api.py || fail "Σφάλμα σύνταξης backend Python"
grep -Fq "applicationId 'com.aria.original'" app/build.gradle || fail "Λάθος applicationId"
grep -Fq 'versionCode 117' app/build.gradle || fail "Λάθος versionCode"
grep -Fq "versionName '2.2.5-original'" app/build.gradle || fail "Λάθος versionName"
if command -v readelf >/dev/null 2>&1; then
  ELF_DYNAMIC="$(readelf -d app/src/main/jniLibs/arm64-v8a/libllama-server.so)"
  [[ "$ELF_DYNAMIC" == *'Library runpath: [$ORIGIN]'* ]] || fail "Το llama-server RUNPATH δεν είναι \$ORIGIN"
fi
grep -Fq 'mailto:seleniachat@gmail.com' app/src/main/java/com/aria/assistant/MainActivity.java || fail "Λείπει email υποστήριξης"
grep -Fq 'Επεξεργασία φωτογραφίας με AI' app/src/main/java/com/aria/assistant/MainActivity.java || fail "Λείπει εργαλείο επεξεργασίας φωτογραφίας"
grep -Fq 'Επιλογή τοπικού μοντέλου' app/src/main/java/com/aria/assistant/MainActivity.java || fail "Λείπει επιλογή τοπικού μοντέλου"
grep -Fq 'aria-original-backend.onrender.com' app/src/main/java/com/aria/assistant/AriaAccountClient.java || fail "Λείπει endpoint λογαριασμών ARIA"
grep -Fq 'gpt-image-1' BACKEND/render.yaml || fail "Το Render allowlist δεν περιλαμβάνει το μοντέλο εικόνας"
grep -Fq '/var/data/aria_original.sqlite3' BACKEND/render.yaml || fail "Δεν έχει οριστεί persistent database path"
grep -Fq 'upload_filename' BACKEND/app/main.py || fail "Λείπει η ασφαλής προώθηση ονόματος εικόνας"
! grep -Rni 'api.openai.com' app/src/main/java/com/aria/assistant/MainActivity.java app/src/main/java/com/aria/assistant/ImageEditingManager.java || fail "Βρέθηκε απευθείας κλήση OpenAI από APK" 
if grep -RniE 'SelfEvolutionEngine|runSelfEvolution|startSelfEvolution|com\.termux|RUN_COMMAND|SILENIA_BRIDGE|127\.0\.0\.1:8765|silenia_termux_bridge' app/src/main/java app/src/main/AndroidManifest.xml; then
  fail "Βρέθηκε ενεργός κώδικας αυτοεξέλιξης ή Termux/SILENIA Bridge"
fi
[ ! -e app/src/main/java/com/aria/assistant/SelfEvolutionEngine.java ] || fail "Παρέμεινε SelfEvolutionEngine"
[ ! -e app/src/main/java/com/aria/assistant/TermuxCommandResultService.java ] || fail "Παρέμεινε Termux callback service"
python3 - <<'PY'
import xml.etree.ElementTree as ET
ET.parse('app/src/main/AndroidManifest.xml')
print('PASS: AndroidManifest.xml XML')
PY
grep -Fq 'case LLM_ARCH_QWEN3' llama.cpp/src/llama-model.cpp || fail "Το bundled llama.cpp δεν έχει Qwen3 model dispatch"
grep -Fq 'aria_single_owner' BACKEND/app/main.py || fail "Λείπει ο atomic περιορισμός ενός OWNER"
pass "ARIA ORIGINAL source preflight"
