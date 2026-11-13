package com.aria.assistant;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.widget.ImageView;
import android.view.View;
import java.io.InputStream;

/**
 * ARIA portrait presenter (V95).
 * Displays the user-approved reference portrait as a static image.
 * The legacy method surface is retained so MainActivity's voice/state callbacks remain compatible.
 */
public final class AriaLive3DAvatarView extends ImageView {
    public AriaLive3DAvatarView(Context context) {
        super(context);
        setScaleType(ScaleType.CENTER_CROP);
        setAdjustViewBounds(false);
        setFocusable(false);
        setContentDescription("Η εικόνα της ARIA");
        try (InputStream in = context.getAssets().open("aria_portrait.jpg")) {
            Bitmap bitmap = BitmapFactory.decodeStream(in);
            if (bitmap != null) setImageBitmap(bitmap);
            else setVisibility(View.INVISIBLE);
        } catch (Exception e) {
            setVisibility(View.INVISIBLE);
        }
    }

    // Compatibility callbacks: the selected presentation is intentionally a still image.
    public void setSpeaking(boolean speaking) { }
    public void setSpeechText(String text) { }
    public void setSpeechRange(int start, int end) { }
    public void setListening(boolean listening) { }
    public void setThinking(boolean thinking) { }
    public void onPause() { }
    public void onResume() { }
}
