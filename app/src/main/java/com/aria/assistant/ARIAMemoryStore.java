package com.aria.assistant;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.text.Normalizer;
import java.util.Locale;

/**
 * Local, user-controlled long-term memory.
 * Facts are stored in this app's private SharedPreferences, never uploaded by this class.
 * The caller decides when a fact is explicitly remembered or forgotten.
 */
public final class ARIAMemoryStore {
    private static final String PREFS = "aria_long_term_memory";
    private static final String KEY = "facts";
    private static final String KEY_SHARE_ONLINE = "share_memory_online";
    private static final int MAX_FACTS = 80;
    private static final int MAX_FACT_LENGTH = 600;
    private static final int MAX_CONTEXT_LENGTH = 4200;

    private ARIAMemoryStore() { }

    public static synchronized boolean remember(Context context, String fact) {
        if (context == null || fact == null) return false;
        String clean = clean(fact);
        if (clean.isEmpty() || clean.length() > MAX_FACT_LENGTH) return false;
        JSONArray facts = read(context);
        String wanted = normalize(clean);
        for (int i = 0; i < facts.length(); i++) {
            JSONObject item = facts.optJSONObject(i);
            if (item != null && wanted.equals(normalize(item.optString("text", "")))) return true;
        }
        JSONArray updated = new JSONArray();
        int start = Math.max(0, facts.length() - MAX_FACTS + 1);
        for (int i = start; i < facts.length(); i++) {
            JSONObject item = facts.optJSONObject(i);
            if (item != null) updated.put(item);
        }
        JSONObject entry = new JSONObject();
        try {
            entry.put("text", clean);
            entry.put("saved_at", System.currentTimeMillis());
            updated.put(entry);
            prefs(context).edit().putString(KEY, updated.toString()).commit();
            return true;
        } catch (Exception ignored) {
            return false;
        }
    }

    public static synchronized int forget(Context context, String phrase) {
        if (context == null) return 0;
        String needle = normalize(phrase);
        if (needle.isEmpty()) return 0;
        JSONArray facts = read(context);
        JSONArray updated = new JSONArray();
        int removed = 0;
        for (int i = 0; i < facts.length(); i++) {
            JSONObject item = facts.optJSONObject(i);
            if (item == null) continue;
            String value = item.optString("text", "");
            String normalized = normalize(value);
            if (normalized.equals(needle) || normalized.contains(needle)) removed++;
            else updated.put(item);
        }
        prefs(context).edit().putString(KEY, updated.toString()).commit();
        return removed;
    }

    public static synchronized void clear(Context context) {
        if (context != null) prefs(context).edit().remove(KEY).commit();
    }

    public static synchronized boolean isOnlineSharingEnabled(Context context) {
        return context != null && prefs(context).getBoolean(KEY_SHARE_ONLINE, false);
    }

    public static synchronized void setOnlineSharingEnabled(Context context, boolean enabled) {
        if (context != null) prefs(context).edit().putBoolean(KEY_SHARE_ONLINE, enabled).commit();
    }

    /** Cloud memory is opt-in; the default is to keep personal notes on-device only. */
    public static synchronized String getCloudContext(Context context) {
        return isOnlineSharingEnabled(context) ? getContext(context) : "";
    }

    public static synchronized String getContext(Context context) {
        if (context == null) return "";
        JSONArray facts = read(context);
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < facts.length(); i++) {
            JSONObject item = facts.optJSONObject(i);
            if (item == null) continue;
            String value = clean(item.optString("text", ""));
            if (value.isEmpty()) continue;
            if (out.length() + value.length() + 4 > MAX_CONTEXT_LENGTH) break;
            out.append("• ").append(value).append('\n');
        }
        return out.toString().trim();
    }

    public static synchronized String describe(Context context) {
        String data = getContext(context);
        return data.isEmpty() ? "Δεν υπάρχουν αποθηκευμένες προσωπικές σημειώσεις."
                : "Αποθηκευμένες πληροφορίες που επέλεξες να θυμάμαι:\n" + data;
    }

    public static synchronized int count(Context context) {
        return read(context).length();
    }

    private static JSONArray read(Context context) {
        try {
            return new JSONArray(prefs(context).getString(KEY, "[]"));
        } catch (Exception ignored) {
            return new JSONArray();
        }
    }

    private static SharedPreferences prefs(Context context) {
        return context.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private static String clean(String value) {
        if (value == null) return "";
        return value.replace('\u0000', ' ').replaceAll("\\s+", " ").trim();
    }

    private static String normalize(String value) {
        if (value == null) return "";
        String lower = value.toLowerCase(new Locale("el", "GR"));
        return Normalizer.normalize(lower, Normalizer.Form.NFD)
                .replaceAll("\\p{M}+", "")
                .replaceAll("[^a-z0-9\\u0370-\\u03ff]+", " ")
                .trim();
    }
}
