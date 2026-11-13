package com.aria.assistant;

import java.io.File;
import java.io.IOException;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Bounded autonomy coordinator.
 * It plans work and validates the only shell workflow exposed here: building
 * an already-approved ARIA workspace through an external build environment.
 * It does not expose arbitrary shell execution.
 */
public final class ARIAAutonomyEngine {
    public enum Approval { NOT_REQUIRED, REQUIRED }

    public static final class Plan {
        public final String title;
        public final List<String> steps;
        public final Approval approval;
        public final boolean externalSideEffects;

        private Plan(String title, List<String> steps, Approval approval, boolean externalSideEffects) {
            this.title = title;
            this.steps = steps;
            this.approval = approval;
            this.externalSideEffects = externalSideEffects;
        }

        public String render() {
            StringBuilder out = new StringBuilder(title).append('\n');
            for (int i = 0; i < steps.size(); i++) {
                out.append(i + 1).append(". ").append(steps.get(i)).append('\n');
            }
            out.append(approval == Approval.REQUIRED
                    ? "Απαιτείται ρητή έγκριση πριν από εξωτερική ενέργεια."
                    : "Δεν απαιτείται εξωτερική ενέργεια.");
            return out.toString();
        }
    }

    private ARIAAutonomyEngine() { }

    public static Plan plan(String request) {
        String p = normalize(request);
        List<String> steps = new ArrayList<>();
        if (contains(p, "build apk", "φτιαξε εφαρμογη", "δημιουργησε εφαρμογη", "κατασκευασε παιχνιδι", "δημιουργησε παιχνιδι")) {
            steps.add("Κατανόηση απαιτήσεων και καταγραφή παραδοτέων.");
            steps.add("Δημιουργία απομονωμένου χώρου έργου.");
            steps.add("Έλεγχος αρχείων, εξαρτήσεων και διαδρομών.");
            steps.add("Παρουσίαση των ενεργειών πριν από build ή εγκατάσταση.");
            steps.add("Εκτέλεση build μόνο μετά από έγκριση και επαλήθευση του APK.");
            return new Plan("Σχέδιο δημιουργίας έργου", steps, Approval.REQUIRED, true);
        }

        if (contains(p, "εκτελεσε εντολη", "build")) {
            steps.add("Έλεγχος αν η ενέργεια υποστηρίζεται από την ενσωματωμένη ροή.");
            steps.add("Επιβεβαίωση δικαιωμάτων και στόχου.");
            steps.add("Εκτέλεση μόνο προκαθορισμένης και εγκεκριμένης εργασίας.");
            steps.add("Έλεγχος πραγματικού exit code και αρχείων αποτελέσματος.");
            return new Plan("Σχέδιο εργασίας συστήματος", steps, Approval.REQUIRED, true);
        }
        ARIAOwnedCore.Task task = ARIAOwnedCore.classify(request);
        if (task == ARIAOwnedCore.Task.CODING) {
            steps.add("Αποσαφήνιση απαιτήσεων, πλατφόρμας και περιορισμών.");
            steps.add("Σχεδιασμός λύσης και απαραίτητων αρχείων.");
            steps.add("Παραγωγή συνεκτικού κώδικα και εξαρτήσεων.");
            steps.add("Παροχή δοκιμών και εντολών επαλήθευσης· build μόνο μετά από έγκριση.");
            return new Plan("Σχέδιο προγραμματισμού", steps, Approval.NOT_REQUIRED, false);
        }
        if (task == ARIAOwnedCore.Task.RESEARCH) {
            steps.add("Διατύπωση συγκεκριμένων ερωτημάτων αναζήτησης.");
            steps.add("Συλλογή πραγματικών αποτελεσμάτων και πηγών.");
            steps.add("Διασταύρωση ημερομηνιών και βασικών ισχυρισμών.");
            steps.add("Σύνθεση συμπερασμάτων με σαφή αναφορά αβεβαιότητας.");
            return new Plan("Σχέδιο έρευνας", steps, Approval.NOT_REQUIRED, false);
        }
        if (task == ARIAOwnedCore.Task.DEVICE_ACTION) {
            steps.add("Έλεγχος αν η ενέργεια υποστηρίζεται από Android.");
            steps.add("Έλεγχος απαραίτητων δικαιωμάτων και εφαρμογής προορισμού.");
            steps.add("Ζήτηση έγκρισης πριν από ενέργεια που αλλάζει ρυθμίσεις ή δεδομένα.");
            steps.add("Επιβεβαίωση πραγματικού αποτελέσματος.");
            return new Plan("Σχέδιο ενέργειας συσκευής", steps, Approval.REQUIRED, true);
        }
        if (task == ARIAOwnedCore.Task.REASONING) {
            steps.add("Καθορισμός ερωτήματος και βασικών παραδοχών.");
            steps.add("Εξέταση εναλλακτικών και συνεπειών.");
            steps.add("Διατύπωση τεκμηριωμένου συμπεράσματος και ορίων.");
            return new Plan("Σχέδιο ανάλυσης", steps, Approval.NOT_REQUIRED, false);
        }
        steps.add("Κατανόηση αιτήματος και σχεδιασμός βημάτων.");
        steps.add("Χρήση μόνο διαθέσιμων εργαλείων.");
        steps.add("Έλεγχος αποτελέσματος και σαφής αναφορά περιορισμών.");
        return new Plan("Σχέδιο εργασίας ARIA", steps, Approval.NOT_REQUIRED, false);
    }

    public static void validateBuildWorkspace(File workspace) throws IOException {
        if (workspace == null || !workspace.isDirectory()) throw new IOException("Δεν υπάρχει έγκυρος χώρος εργασίας.");
        File canonical = workspace.getCanonicalFile();
        File script = new File(canonical, "BUILD_ARIA_CLEAN.sh");
        File gradle = new File(canonical, "app/build.gradle");
        File manifest = new File(canonical, "app/src/main/AndroidManifest.xml");
        if (!script.isFile() || script.length() == 0) throw new IOException("Λείπει το BUILD_ARIA_CLEAN.sh.");
        if (!gradle.isFile() || gradle.length() == 0) throw new IOException("Λείπει το app/build.gradle.");
        if (!manifest.isFile() || manifest.length() == 0) throw new IOException("Λείπει το AndroidManifest.xml.");
        if (!script.getCanonicalPath().startsWith(canonical.getPath() + File.separator))
            throw new IOException("Το build script βρίσκεται εκτός του workspace.");
    }

    public static String quoteShellPath(String path) {
        if (path == null || path.trim().isEmpty() || path.indexOf('\u0000') >= 0)
            throw new IllegalArgumentException("Μη έγκυρη διαδρομή.");
        return "'" + path.replace("'", "'\\''") + "'";
    }

    private static boolean contains(String value, String... terms) {
        for (String term : terms) if (value.contains(normalize(term))) return true;
        return false;
    }

    private static String normalize(String value) {
        if (value == null) return "";
        return Normalizer.normalize(value.toLowerCase(new Locale("el", "GR")), Normalizer.Form.NFD)
                .replaceAll("\\p{M}+", "").replaceAll("[^a-z0-9\\u0370-\\u03ff]+", " ").trim();
    }
}
