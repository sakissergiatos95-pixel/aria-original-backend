# Δημοσίευση ARIA ORIGINAL Backend στο Render

Το APK δεν μπορεί να δημιουργήσει λογαριασμούς όσο το Backend δεν είναι δημοσιευμένο. Το HTTP 404 που εμφανίστηκε είναι απόκριση του server URL και όχι σφάλμα στο email του χρήστη.

## Σωστή δημοσίευση

1. Άνοιξε το Render Dashboard.
2. Επίλεξε **New → Blueprint**.
3. Σύνδεσε το Git repository που περιέχει τον φάκελο `ARIA_ORIGINAL` και το αρχείο `ARIA_ORIGINAL/render.yaml` στη ρίζα του repository.
4. Μην ορίσεις ως repository root τον υποφάκελο `BACKEND`. Το Blueprint πρέπει να διαβάσει το root `render.yaml`, το οποίο δηλώνει `rootDir: BACKEND`.
5. Εφάρμοσε το Blueprint. Το service πρέπει να ονομαστεί `aria-original-backend`.
6. Όρισε τα μυστικά περιβάλλοντος:
   - `OPENAI_API_KEY`
   - `ARIA_OWNER_BOOTSTRAP_TOKEN`
   - `ARIA_OWNER_REPORT_EMAIL` (μπορεί να συμπληρωθεί όταν δοθεί η διεύθυνση αναφορών)
7. Περίμενε να ολοκληρωθεί το Deploy και η υπηρεσία να γίνει **Live**.

## Έλεγχος

Άνοιξε:
`https://aria-original-backend.onrender.com/health`

Πρέπει να επιστρέψει HTTP 200 και JSON health response. Μετά έλεγξε ότι οι διαδρομές `/auth/register` και `/auth/login` απαντούν από την ίδια υπηρεσία (το `/auth/register` είναι POST, όχι απλή επίσκεψη από browser).

Μην ενεργοποιήσεις Billing. Παραμένει OFF μέχρι να προστεθούν πραγματικός πάροχος πληρωμών, signed webhooks και reconciliation.
