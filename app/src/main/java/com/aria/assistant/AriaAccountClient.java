package com.aria.assistant;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import android.util.Base64;
import java.security.Key;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import java.nio.charset.StandardCharsets;

/** First-party ARIA account client. The backend URL is public; no provider secrets are stored here. */
public final class AriaAccountClient {
    public static final String BASE_URL = "https://aria-original-backend.onrender.com";
    private static final String PREFS = "aria_account_session";
    private static final String TOKEN = "session_token_cipher";
    private static final String IV = "session_token_iv";
    private static final String KEY_ALIAS = "aria.account.session.v1";
    private AriaAccountClient() {}
    public static synchronized String token(Context c) {
        SharedPreferences p=c.getSharedPreferences(PREFS,Context.MODE_PRIVATE);
        String encrypted=p.getString(TOKEN,""), iv=p.getString(IV,"");
        if(encrypted.isEmpty() || iv.isEmpty()) return "";
        try {
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,Base64.decode(iv,Base64.NO_WRAP)));
            return new String(cipher.doFinal(Base64.decode(encrypted,Base64.NO_WRAP)),StandardCharsets.UTF_8);
        } catch(Exception e) { clear(c); return ""; }
    }
    public static synchronized void saveToken(Context c, String value) {
        try {
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE,key());
            byte[] encrypted=cipher.doFinal(value.getBytes(StandardCharsets.UTF_8));
            c.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit()
                .putString(TOKEN,Base64.encodeToString(encrypted,Base64.NO_WRAP))
                .putString(IV,Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP)).commit();
        } catch(Exception e) { throw new IllegalStateException("Δεν ήταν δυνατή η ασφαλής αποθήκευση συνεδρίας.",e); }
    }
    public static synchronized void clear(Context c) {
        c.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().remove(TOKEN).remove(IV).commit();
    }
    private static SecretKey key() throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore"); store.load(null);
        Key existing=store.getKey(KEY_ALIAS,null);
        if(existing instanceof SecretKey) return (SecretKey)existing;
        KeyGenerator gen=KeyGenerator.getInstance("AES","AndroidKeyStore");
        gen.init(new android.security.keystore.KeyGenParameterSpec.Builder(KEY_ALIAS,
            android.security.keystore.KeyProperties.PURPOSE_ENCRYPT | android.security.keystore.KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(android.security.keystore.KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(android.security.keystore.KeyProperties.ENCRYPTION_PADDING_NONE)
            .setRandomizedEncryptionRequired(true).build());
        return gen.generateKey();
    }
    public static JSONObject request(Context c, String method, String path, JSONObject body, boolean auth) throws Exception {
        HttpURLConnection conn = null;
        try {
            conn = (HttpURLConnection)new URL(BASE_URL + path).openConnection();
            conn.setRequestMethod(method);
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(60000);
            conn.setRequestProperty("Accept", "application/json");
            if (auth) {
                String t = token(c);
                if (t.isEmpty()) throw new IOException("Δεν είσαι συνδεδεμένος στον λογαριασμό ARIA.");
                conn.setRequestProperty("Authorization", "Bearer " + t);
            }
            if (body != null) {
                conn.setDoOutput(true);
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                try (OutputStream out = conn.getOutputStream()) {
                    out.write(body.toString().getBytes(StandardCharsets.UTF_8));
                }
            }
            int code = conn.getResponseCode();
            InputStream in = code >= 200 && code < 300 ? conn.getInputStream() : conn.getErrorStream();
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            if (in != null) {
                byte[] buf = new byte[8192]; int n;
                while ((n = in.read(buf)) != -1) bytes.write(buf, 0, n);
            }
            String responseText = bytes.toString("UTF-8");
            JSONObject result;
            try { result = responseText.trim().startsWith("{") ? new JSONObject(responseText) : new JSONObject(); }
            catch (Exception malformed) { result = new JSONObject(); }
            if (code < 200 || code >= 300) {
                String detail = result.optString("detail", "");
                if (detail.isEmpty()) detail = result.optString("message", "");
                if (code == 404) {
                    throw new IOException("Το ARIA Backend επέστρεψε HTTP 404 στη διαδρομή " + path
                            + ". Το Render δεν εξυπηρετεί ακόμη το σωστό Backend. Δημοσίευσε το Blueprint από το αρχείο render.yaml στη ρίζα του repository και περίμενε να γίνει Live η υπηρεσία aria-original-backend.");
                }
                if (detail.isEmpty()) detail = "Σφάλμα υπηρεσίας: HTTP " + code;
                throw new IOException(detail);
            }
            if (responseText.trim().isEmpty()) throw new IOException("Ο server επέστρεψε κενή απάντηση.");
            return result;
        } finally { if (conn != null) conn.disconnect(); }
    }
}
