ARIA ORIGINAL V114 — ΠΑΚΕΤΟ ΤΕΛΙΚΟΥ SOURCE ΓΙΑ BUILD ΣΤΟ TERMUX
Ημερομηνία ελέγχου: 11/11/2026

ΤΑΥΤΟΤΗΤΑ ΕΦΑΡΜΟΓΗΣ
- applicationId: com.aria.original
- versionCode: 112
- versionName: 2.2.2-original
- compileSdk: 34
- minSdk: 30
- Native ABI: arm64-v8a

ΔΙΟΡΘΩΣΕΙΣ ΣΤΟ SOURCE
1. Διορθώθηκε η προώθηση αρχείων στο backend image-edit (bytes, filename, MIME type).
2. Το image-edit επικυρώνει quality/output_format και δέχεται φωτογραφίες έως 50 MiB.
3. Ευθυγραμμίστηκε το Render service name με το hostname της εφαρμογής.
4. Προστέθηκε persistent disk για SQLite στο /var/data/aria_original.sqlite3.
5. Το Render allowlist περιλαμβάνει το μοντέλο εικόνας που ζητά η εφαρμογή.
6. Το build script εντοπίζει SDK σε συνήθεις διαδρομές Termux και χρησιμοποιεί το ενσωματωμένο Gradle Wrapper 8.14.3.
7. Διορθώθηκε η διαχείριση SQLite: κάθε σύνδεση κλείνει και οι συναλλαγές γίνονται commit/rollback σωστά.
8. Το launcher label είναι ARIA ORIGINAL.
9. Περιλαμβάνονται οδηγίες deployment, OWNER bootstrap και regression test.

ΕΛΕΓΧΟΙ ΠΟΥ ΠΕΡΑΣΑΝ ΣΤΟ ΠΕΡΙΒΑΛΛΟΝ ΕΛΕΓΧΟΥ
- tools/verify_source.sh: PASS
- bash -n BUILD_ARIA_ORIGINAL.sh: PASS
- bash -n app/gradlew: PASS
- AndroidManifest.xml XML parse: PASS
- Backend Python compile: PASS
- Backend integration test με ResourceWarning ως error: PASS
  * εγγραφή χρήστη
  * απαγόρευση admin πρόσβασης σε απλό χρήστη (403)
  * μοναδικό OWNER bootstrap
  * απόρριψη δεύτερου OWNER bootstrap (409)
  * δωρεάν PREMIUM grant και χωριστή καταμέτρηση
  * απόρριψη paid PREMIUM όσο το billing είναι OFF
  * image-edit multipart προωθεί filename, bytes, MIME, quality και output_format
- Οι ενσωματωμένες native βιβλιοθήκες llama-server και libc++ είναι ELF AArch64.
- Το τελικό ZIP ελέγχθηκε για ακεραιότητα.

BUILD ΣΤΟ TERMUX
Μετά την αποσυμπίεση:
  cd ARIA_ORIGINAL
  bash BUILD_ARIA_ORIGINAL.sh

Το script παράγει:
  output/ARIA_ORIGINAL.apk
  output/ARIA_ORIGINAL.sha256

Απαιτούνται Java, Python 3, Android SDK Platform 34 και σύνδεση Internet για την πρώτη λήψη Gradle/dependencies. Το παραγόμενο APK είναι debug build για εγκατάσταση/δοκιμή. Για δημόσια διάθεση απαιτείται release signing.

ΕΞΩΤΕΡΙΚΕΣ ΡΥΘΜΙΣΕΙΣ ΠΟΥ ΔΕΝ ΜΠΟΡΟΥΝ ΝΑ ΓΙΝΟΥΝ ΜΕΣΑ ΑΠΟ ΑΥΤΟ ΤΟ SOURCE BUILD
- Το backend πρέπει να γίνει deploy στο Render από τον ιδιοκτήτη του λογαριασμού.
- Απαιτούνται OPENAI_API_KEY και ARIA_OWNER_BOOTSTRAP_TOKEN στο Render.
- Ο OWNER δημιουργείται μία φορά μετά το deployment.
- Για email reports απαιτούνται OWNER_REPORT_EMAIL και SMTP credentials.
- Το billing παραμένει OFF μέχρι να συνδεθεί πραγματικός πάροχος πληρωμών με signed webhooks.

ΣΗΜΑΝΤΙΚΟ
Αυτό είναι το τελικό διορθωμένο πακέτο πηγαίου κώδικα που προορίζεται για το Build από τον χρήστη. Δεν δηλώνεται ότι έχει ήδη παραχθεί APK, γίνει deployment, δημιουργηθεί OWNER ή δοκιμαστεί σε πραγματική συσκευή.
