package com.aria.assistant;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.Key;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Stores provider credentials encrypted with an Android Keystore AES-GCM key. */
public final class ApiKeyStore {
    private static final String KEY_ALIAS = "aria.openai.api-key.v1";
    private static final String SECURE_PREFS = "aria_secure_credentials";
    private static final String CIPHER_TEXT = "openai_key_ciphertext";
    private static final String IV = "openai_key_iv";
    private static final String LEGACY_PREFS = "aria_clean_memory";
    private static final String LEGACY_KEY = "openai_api_key";

    private ApiKeyStore() { }

    public static synchronized String get(Context context) {
        Context app = context.getApplicationContext();
        SharedPreferences secure = app.getSharedPreferences(SECURE_PREFS, Context.MODE_PRIVATE);
        String cipherText = secure.getString(CIPHER_TEXT, "");
        String ivText = secure.getString(IV, "");
        if (!cipherText.isEmpty() && !ivText.isEmpty()) {
            try {
                Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
                cipher.init(Cipher.DECRYPT_MODE, getOrCreateKey(), new GCMParameterSpec(128, Base64.decode(ivText, Base64.NO_WRAP)));
                byte[] plain = cipher.doFinal(Base64.decode(cipherText, Base64.NO_WRAP));
                return new String(plain, StandardCharsets.UTF_8).trim();
            } catch (Exception failure) {
                // Do not silently fall back to an unusable or corrupt encrypted credential.
                secure.edit().remove(CIPHER_TEXT).remove(IV).apply();
                return "";
            }
        }
        // One-time migration from earlier ARIA builds which kept the key in private, but unencrypted, preferences.
        SharedPreferences legacy = app.getSharedPreferences(LEGACY_PREFS, Context.MODE_PRIVATE);
        String old = legacy.getString(LEGACY_KEY, "");
        if (old != null && !old.trim().isEmpty()) {
            if (setInternal(secure, old.trim())) {
                legacy.edit().remove(LEGACY_KEY).apply();
                return old.trim();
            }
        }
        return "";
    }

    public static synchronized boolean set(Context context, String value) {
        String clean = value == null ? "" : value.trim();
        if (clean.isEmpty()) return false;
        return setInternal(context.getApplicationContext().getSharedPreferences(SECURE_PREFS, Context.MODE_PRIVATE), clean);
    }

    public static synchronized void clear(Context context) {
        Context app = context.getApplicationContext();
        app.getSharedPreferences(SECURE_PREFS, Context.MODE_PRIVATE).edit().remove(CIPHER_TEXT).remove(IV).apply();
        app.getSharedPreferences(LEGACY_PREFS, Context.MODE_PRIVATE).edit().remove(LEGACY_KEY).apply();
    }

    private static boolean setInternal(SharedPreferences prefs, String value) {
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey());
            byte[] encrypted = cipher.doFinal(value.getBytes(StandardCharsets.UTF_8));
            return prefs.edit()
                    .putString(CIPHER_TEXT, Base64.encodeToString(encrypted, Base64.NO_WRAP))
                    .putString(IV, Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP))
                    .commit();
        } catch (Exception failure) {
            return false;
        }
    }

    private static SecretKey getOrCreateKey() throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        Key existing = store.getKey(KEY_ALIAS, null);
        if (existing instanceof SecretKey) return (SecretKey) existing;
        KeyGenerator generator = KeyGenerator.getInstance("AES", "AndroidKeyStore");
        android.security.keystore.KeyGenParameterSpec spec = new android.security.keystore.KeyGenParameterSpec.Builder(
                KEY_ALIAS, android.security.keystore.KeyProperties.PURPOSE_ENCRYPT | android.security.keystore.KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(android.security.keystore.KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(android.security.keystore.KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build();
        generator.init(spec);
        return generator.generateKey();
    }
}
