package com.aria.assistant;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

/** Uploads a user-selected image to the ARIA ORIGINAL image-edit gateway and decodes the result. */
public final class ImageEditingManager {
    private static final String ENDPOINT = "https://aria-original-backend.onrender.com/v1/images/edits";
    private static final String MODEL = "gpt-image-2.5-flare";
    private static final long MAX_INPUT_BYTES = 50L * 1024L * 1024L;
    private static final int MAX_RESPONSE_CHARS = 100 * 1024 * 1024;

    private ImageEditingManager() { }

    public static Bitmap edit(Context context, Uri imageUri, String prompt, String apiKey) throws Exception {
        if (context == null || imageUri == null) throw new IllegalArgumentException("Δεν επιλέχθηκε φωτογραφία.");
        if (prompt == null || prompt.trim().isEmpty()) throw new IllegalArgumentException("Η περιγραφή αλλαγών είναι κενή.");
        if (apiKey == null || apiKey.trim().isEmpty()) throw new IllegalArgumentException("Δεν υπάρχει σύνδεση σε λογαριασμό ARIA.");

        String mime = context.getContentResolver().getType(imageUri);
        if (mime == null) mime = "image/jpeg";
        String extension;
        if ("image/png".equalsIgnoreCase(mime)) extension = "png";
        else if ("image/webp".equalsIgnoreCase(mime)) extension = "webp";
        else if ("image/jpeg".equalsIgnoreCase(mime) || "image/jpg".equalsIgnoreCase(mime)) {
            mime = "image/jpeg"; extension = "jpg";
        } else throw new IllegalArgumentException("Υποστηρίζονται μόνο JPG, PNG και WebP φωτογραφίες.");

        HttpURLConnection connection = null;
        String boundary = "----ARIAImageEdit" + UUID.randomUUID().toString().replace("-", "");
        try {
            connection = (HttpURLConnection) new URL(ENDPOINT).openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(20000);
            connection.setReadTimeout(300000);
            connection.setDoOutput(true);
            connection.setUseCaches(false);
            connection.setRequestProperty("Authorization", "Bearer " + apiKey.trim());
            connection.setRequestProperty("Content-Type", "multipart/form-data; boundary=" + boundary);
            connection.setChunkedStreamingMode(64 * 1024);

            try (OutputStream out = connection.getOutputStream()) {
                writeField(out, boundary, "model", MODEL);
                writeField(out, boundary, "prompt", prompt.trim());
                writeField(out, boundary, "quality", "medium");
                writeField(out, boundary, "output_format", "png");
                writeAscii(out, "--" + boundary + "\r\n");
                writeAscii(out, "Content-Disposition: form-data; name=\"image\"; filename=\"source." + extension + "\"\r\n");
                writeAscii(out, "Content-Type: " + mime + "\r\n\r\n");
                long total = 0;
                try (InputStream in = context.getContentResolver().openInputStream(imageUri)) {
                    if (in == null) throw new Exception("Δεν ήταν δυνατή η ανάγνωση της επιλεγμένης φωτογραφίας.");
                    byte[] buffer = new byte[64 * 1024];
                    int count;
                    while ((count = in.read(buffer)) != -1) {
                        total += count;
                        if (total > MAX_INPUT_BYTES) throw new Exception("Η φωτογραφία ξεπερνά το όριο των 50 MB.");
                        out.write(buffer, 0, count);
                    }
                }
                if (total == 0) throw new Exception("Η επιλεγμένη φωτογραφία είναι κενή.");
                writeAscii(out, "\r\n");
                writeAscii(out, "--" + boundary + "--\r\n");
                out.flush();
            }

            int code = connection.getResponseCode();
            InputStream response = code >= 200 && code < 300 ? connection.getInputStream() : connection.getErrorStream();
            StringBuilder body = new StringBuilder();
            if (response != null) {
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(response, StandardCharsets.UTF_8))) {
                    char[] buffer = new char[8192];
                    int count;
                    while ((count = reader.read(buffer)) != -1) {
                        if (body.length() + count > MAX_RESPONSE_CHARS) throw new Exception("Η απάντηση εικόνας ξεπέρασε το ασφαλές όριο.");
                        body.append(buffer, 0, count);
                    }
                }
            }
            if (code < 200 || code >= 300) {
                String detail = "HTTP " + code;
                try {
                    JSONObject error = new JSONObject(body.toString()).optJSONObject("error");
                    if (error != null) detail = error.optString("message", detail);
                } catch (Exception ignored) { }
                throw new Exception("Το AI δεν ολοκλήρωσε την επεξεργασία: " + detail);
            }
            JSONObject json = new JSONObject(body.toString());
            JSONArray data = json.optJSONArray("data");
            if (data == null || data.length() == 0) throw new Exception("Το AI δεν επέστρεψε επεξεργασμένη εικόνα.");
            String encoded = data.getJSONObject(0).optString("b64_json", "");
            if (encoded.isEmpty()) throw new Exception("Η απάντηση δεν περιείχε δεδομένα εικόνας.");
            byte[] bytes = android.util.Base64.decode(encoded, android.util.Base64.DEFAULT);
            Bitmap bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.length);
            if (bitmap == null) throw new Exception("Το AI επέστρεψε μη έγκυρη εικόνα.");
            return bitmap;
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static void writeField(OutputStream out, String boundary, String name, String value) throws Exception {
        writeAscii(out, "--" + boundary + "\r\n");
        writeAscii(out, "Content-Disposition: form-data; name=\"" + name + "\"\r\n\r\n");
        out.write(value.getBytes(StandardCharsets.UTF_8));
        writeAscii(out, "\r\n");
    }

    private static void writeAscii(OutputStream out, String value) throws Exception {
        out.write(value.getBytes(StandardCharsets.US_ASCII));
    }
}
