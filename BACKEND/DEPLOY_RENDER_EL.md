# Δημοσίευση ARIA ORIGINAL Backend στο Render

Το Blueprint βρίσκεται στο `render.yaml` στη ρίζα του repository. Το service χρησιμοποιεί `rootDir: BACKEND`, Dockerfile `BACKEND/Dockerfile`, health check `/health` και μόνιμο δίσκο SQLite στο `/var/data`.

Στο Render: New → Blueprint → σύνδεσε το repository που περιέχει το `render.yaml` στη ρίζα → Apply. Στο service συμπλήρωσε υποχρεωτικά `OPENAI_API_KEY` και `ARIA_OWNER_BOOTSTRAP_TOKEN` (τυχαίο μυστικό τουλάχιστον 20 χαρακτήρων). Τα SMTP πεδία είναι προαιρετικά μέχρι να ενεργοποιηθούν οι αναφορές email. Άφησε `ARIA_BILLING_ENABLED=false`.

Μετά το Deploy, έλεγξε `https://aria-original-backend.onrender.com/health`. Πρέπει να επιστρέφει JSON με `status: ready`. Έπειτα η εγγραφή Android χρησιμοποιεί `POST /auth/register` και μετά `POST /auth/login`. Το Online AI απαιτεί ενεργό `OPENAI_API_KEY` και λογαριασμό ARIA.

Δεν είναι δυνατό να δημοσιευτεί από το source archive: απαιτείται εξουσιοδοτημένη πρόσβαση στο Render και ο ιδιοκτήτης να καταχωρίσει τα μυστικά.
