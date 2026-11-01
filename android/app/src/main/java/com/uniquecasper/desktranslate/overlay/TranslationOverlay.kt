package com.uniquecasper.desktranslate.overlay

import android.content.Context
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.provider.Settings
import android.view.Gravity
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * A small, dismissible system overlay for the reviewed translation.
 *
 * The user must explicitly grant Android's "Display over other apps" permission.
 * The overlay only displays text supplied by the user-triggered translation flow.
 */
class TranslationOverlay(context: Context) {
    private val appContext = context.applicationContext
    private val windowManager =
        appContext.getSystemService(Context.WINDOW_SERVICE) as WindowManager

    private var attachedView: LinearLayout? = null

    fun show(translation: String) {
        val cleanText = translation.trim().take(MAX_TEXT_LENGTH)
        require(cleanText.isNotEmpty()) { "There is no translation to display." }
        check(Settings.canDrawOverlays(appContext)) {
            "DeskTranslate needs permission to display a floating translation."
        }

        hide()

        val density = appContext.resources.displayMetrics.density
        fun dp(value: Int): Int = (value * density).toInt()

        val card = LinearLayout(appContext).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(12), dp(16), dp(14))
            background = GradientDrawable().apply {
                setColor(Color.rgb(27, 31, 42))
                cornerRadius = dp(18).toFloat()
                setStroke(dp(1), Color.argb(110, 185, 196, 220))
            }
            elevation = dp(12).toFloat()
        }

        val header = LinearLayout(appContext).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }

        val title = TextView(appContext).apply {
            text = "DeskTranslate · Translation"
            setTextColor(Color.WHITE)
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
        }
        val close = TextView(appContext).apply {
            text = "Close"
            setTextColor(Color.rgb(190, 205, 255))
            textSize = 13f
            setPadding(dp(12), dp(8), 0, dp(8))
            setOnClickListener { hide() }
            contentDescription = "Close translation overlay"
        }
        header.addView(title, LinearLayout.LayoutParams(0, dp(40), 1f))
        header.addView(close, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT,
            dp(40)
        ))

        val body = TextView(appContext).apply {
            text = cleanText
            setTextColor(Color.rgb(244, 246, 250))
            textSize = 16f
            setLineSpacing(dp(3).toFloat(), 1f)
            setTextIsSelectable(true)
        }
        val scroll = ScrollView(appContext).apply {
            isFillViewport = true
            addView(body, android.widget.FrameLayout.LayoutParams(
                android.widget.FrameLayout.LayoutParams.MATCH_PARENT,
                android.widget.FrameLayout.LayoutParams.WRAP_CONTENT
            ))
        }

        card.addView(header, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ))
        card.addView(scroll, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            dp(280)
        ))

        val screenWidth = appContext.resources.displayMetrics.widthPixels
        val params = WindowManager.LayoutParams(
            (screenWidth - dp(24)).coerceAtLeast(dp(240)),
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
            y = dp(72)
        }

        windowManager.addView(card, params)
        attachedView = card
    }

    fun hide() {
        val view = attachedView ?: return
        attachedView = null
        try {
            windowManager.removeView(view)
        } catch (_: IllegalArgumentException) {
            // The Android window may already have been detached by the system.
        }
    }

    companion object {
        private const val MAX_TEXT_LENGTH = 20_000
    }
}
