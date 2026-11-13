# ARIA ORIGINAL — Backend εγκατάσταση

## Έλεγχος backend

Από τον φάκελο `BACKEND` εκτέλεσε `python3 -m unittest discover -s tests -v` για τα regression tests OWNER και image-edit.

## 1. Deployment

Στο Render δημιούργησε **Blueprint** από το repository που περιέχει αυτό το project και επίλεξε το `BACKEND/render.yaml` (αν το Blueprint ζητά root directory, χρησιμοποίησε `BACKEND`). Έλεγξε ότι το service δημιουργείται με όνομα `aria-original-backend` και ότι το persistent disk είναι προσαρτημένο στο `/var/data`, ώστε λογαριασμοί και συνεδρίες να μη χάνονται σε restart.

Μετά το πρώτο deploy, έλεγξε ότι το `https://aria-original-backend.onrender.com/health` επιστρέφει επιτυχία πριν δημιουργήσεις OWNER.

Ρύθμισε στο hosting τα μυστικά:
- `OPENAI_API_KEY`: μυστικό API key του παρόχου AI.
- `ARIA_OWNER_BOOTSTRAP_TOKEN`: τυχαίο μυστικό τουλάχιστον 32 χαρακτήρων.
- `ARIA_OWNER_REPORT_EMAIL`: email στο οποίο θα στέλνονται οι αναφορές.
- `ARIA_SMTP_HOST`, `ARIA_SMTP_PORT`, `ARIA_SMTP_USER`, `ARIA_SMTP_PASSWORD`, `ARIA_SMTP_FROM`: SMTP αποστολή αναφορών.

Το `ARIA_BILLING_ENABLED` πρέπει να παραμείνει `false`. Δεν υπάρχει ακόμη checkout ή επαλήθευση πληρωμών με signed webhooks.

## 2. Δημιουργία μοναδικού OWNER

Μετά το deployment, κάλεσε ΜΙΑ φορά το `POST /owner/bootstrap` με το ίδιο `ARIA_OWNER_BOOTSTRAP_TOKEN` που όρισες στο hosting. Το endpoint κλειδώνει οριστικά μετά τη δημιουργία του πρώτου OWNER. Μην ενσωματώσεις το token στο APK και μην το κοινοποιήσεις.

Παράδειγμα (βάλε τις τιμές μόνο στο τοπικό shell, όχι σε δημόσιο αρχείο):

```bash
export ARIA_API_BASE='https://aria-original-backend.onrender.com'
read -r -p 'Email OWNER: ' OWNER_EMAIL
read -r -s -p 'Κωδικός OWNER: ' OWNER_PASSWORD; echo
read -r -s -p 'Bootstrap token: ' OWNER_BOOTSTRAP_TOKEN; echo
export OWNER_EMAIL OWNER_PASSWORD OWNER_BOOTSTRAP_TOKEN
python3 - <<'PY'
import json, os, urllib.request
url=os.environ['ARIA_API_BASE'].rstrip('/')+'/owner/bootstrap'
data=json.dumps({
  'email':os.environ['OWNER_EMAIL'],
  'password':os.environ['OWNER_PASSWORD'],
  'bootstrap_token':os.environ['OWNER_BOOTSTRAP_TOKEN']
}).encode()
req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(req,timeout=30) as r:
    print(r.read().decode())
PY
unset OWNER_EMAIL OWNER_PASSWORD OWNER_BOOTSTRAP_TOKEN
```

Η εφαρμογή συνδέεται κατόπιν από το «Λογαριασμός ARIA» με το email και τον κωδικό OWNER.

## 3. Αναφορές email

Οι αναφορές απαιτούν λειτουργικό SMTP και `ARIA_OWNER_REPORT_EMAIL`. Το OWNER panel στέλνει χωριστά:
- πλήθος FREE,
- πληρωμένο PREMIUM,
- δωρεάν PREMIUM που παραχώρησε ο OWNER.

## 4. Περιορισμοί που παραμένουν

- Η πληρωμή συνδρομών δεν είναι ενεργή. Δεν πρέπει να δηλωθεί πληρωμένο PREMIUM χωρίς πραγματικό πάροχο και επιβεβαιωμένα webhooks.
- Δεν έχουν υλοποιηθεί ακόμη επιβεβαίωση email και επαναφορά κωδικού.
- Πριν από δημόσια διάθεση απαιτούνται rate limiting σε επίπεδο proxy/hosting, monitoring, backups και δοκιμές φόρτου.
