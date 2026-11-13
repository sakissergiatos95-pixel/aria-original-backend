# ARIA ORIGINAL 2.2.0

Ανεξάρτητη έκδοση Android της ARIA με ξεχωριστή ταυτότητα εφαρμογής.

- `applicationId`: `com.aria.original`
- `versionCode`: `117`
- `versionName`: `2.2.5-original`
- Εμφανιζόμενο όνομα: ARIA ORIGINAL
- Υποστήριξη: `seleniachat@gmail.com`
- Η εγκατεστημένη ARIA V111 (`com.aria.ai`) δεν αντικαθίσταται.

## Διατηρούμενες λειτουργίες

- Ελληνική συνομιλία, αποθηκευμένο ιστορικό και μνήμη.
- Τοπικό GGUF μέσω ενσωματωμένου llama-server ARM64 και επιλογής μοντέλου.
- Online AI μέσω προσωπικού λογαριασμού ARIA και backend gateway· το provider API key παραμένει στον server.
- Φωνητική εισαγωγή και εκφώνηση απαντήσεων.
- Αναζήτηση ιστού, δημιουργία εικόνων και επεξεργασία φωτογραφιών με AI.
- Επισύναψη αρχείων και δημιουργία έργων/ZIP.
- Εκπαιδευτική, επιχειρηματική, επαγγελματική και γλωσσική βοήθεια.

## Αλλαγές ORIGINAL

- Αφαιρέθηκαν οι λειτουργίες αυτοεξέλιξης από την εφαρμογή.
- Αφαιρέθηκαν ο κώδικας και η υπηρεσία σύνδεσης SILENIA/Termux που εξυπηρετούσαν αυτοεξέλιξη και μεταφορά αρχείων.
- Προστέθηκε επικοινωνία με τον δημιουργό. Η εφαρμογή ανοίγει το πρόγραμμα email με προσυμπληρωμένο μήνυμα· ο χρήστης ελέγχει και στέλνει ο ίδιος.
- Διαφορετικό package ID ώστε να συνυπάρχει με V111.

## Build

Σε Termux ARM64 με Android SDK Platform 34, Android NDK (API 30+), Java 17 ή 21, CMake, Ninja και Gradle Wrapper 8.14.3:

```bash
bash tools/verify_source.sh
bash BUILD_ARIA_ORIGINAL.sh
```

Πριν από το Gradle, το build ξαναχτίζει υποχρεωτικά το `llama-server` από τον ενσωματωμένο llama.cpp και τοποθετεί το ARM64 εκτελέσιμο μαζί με το NDK `libc++_shared.so`. Έτσι δεν χρησιμοποιείται το παλιό εκτελέσιμο που απέρριπτε Qwen3. Το debug APK, εφόσον ολοκληρωθεί επιτυχώς το build, αποθηκεύεται στο `output/ARIA_ORIGINAL.apk`. Το script επαληθεύει ZIP integrity και παρουσία των native ARM64 βιβλιοθηκών. Η debug υπογραφή δεν είναι release signing και δεν υποκαθιστά δοκιμή σε πραγματική συσκευή.

## Online AI και λογαριασμοί

Η εφαρμογή κάνει εγγραφή/σύνδεση στο backend `https://aria-original-backend.onrender.com`. Το session token αποθηκεύεται κρυπτογραφημένο με Android Keystore. Το provider API key δεν μπαίνει στο APK· ρυθμίζεται μόνο ως `OPENAI_API_KEY` στο περιβάλλον του backend.

Για deployment, persistent database, μοναδικό OWNER bootstrap και SMTP αναφορές, ακολούθησε το `BACKEND/README_EL.md`. Το πρώτο OWNER δημιουργείται μία φορά με μυστικό bootstrap που δεν ενσωματώνεται στην εφαρμογή.

Το billing παραμένει OFF. Δεν πρέπει να ενεργοποιηθεί πριν προστεθούν checkout, signed payment webhooks και reconciliation από πραγματικό πάροχο.

## Κατάσταση επαλήθευσης

Οι στατικοί έλεγχοι πηγής και XML εκτελούνται με `tools/verify_source.sh`. Η έκδοση 117 προσθέτει υποχρεωτικό native rebuild από τον bundled llama.cpp, επιβεβαίωση Qwen3 στο source και μοναδικό OWNER με SQLite partial unique index. Σε αυτό το περιβάλλον δεν είναι εγκατεστημένα Android SDK/Gradle, επομένως δεν έχει παραχθεί ούτε δοκιμαστεί APK εδώ. Απαιτείται build και δοκιμή στη συσκευή πριν από διανομή.


## Σύστημα λογαριασμών ARIA ORIGINAL

Η εφαρμογή χρησιμοποιεί το `AriaAccountClient` για εγγραφή/σύνδεση και τις online κλήσεις μέσω του backend. Δες το `FINAL_STATUS_EL.txt` και το `BACKEND/README_EL.md` για τους ελέγχους, τη ρύθμιση OWNER και τις εκκρεμότητες. Η ενεργοποίηση πληρωμών παραμένει OFF.
