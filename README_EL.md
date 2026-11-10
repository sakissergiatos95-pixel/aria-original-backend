# ARIA ORIGINAL Backend

Αρχικό backend proxy για OpenAI.

Το OPENAI_API_KEY μπαίνει μόνο στα Environment Secrets του Render.
Δεν ανεβαίνει στο GitHub ή στο APK.

Endpoints:
- GET /health
- POST /v1/chat/completions
- POST /v1/images/generations

ΠΡΟΣΟΧΗ:
Αυτό είναι starter και όχι production-ready δημόσια υπηρεσία.
Απαιτούνται authentication, quotas ανά χρήστη, όρια δαπάνης,
monitoring και έλεγχοι κατάχρησης πριν από δημόσια κυκλοφορία.
