package com.uniquecasper.desktranslate.overlay

import android.content.Context
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.provider.Settings
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * A touch-interactive, movable system overlay for the reviewed translation.
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
            // Consume touches inside the panel instead of passing them to the app below.
            isClickable = true
            isFocusable = true
        }

        val header = LinearLayout(appContext).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            contentDescription = "Hold and drag to move translation panel"
        }

        val title = TextView(appContext).apply {
            text = "DeskTranslate · Translation"
            setTextColor(Color.WHITE)
            textSize = 14f
            setTypeface(typeface, android.graphics.Typeface.BOLD)
            gravity = Gravity.CENTER_VERTICAL
            minHeight = dp(48)
        }
        val close = TextView(appContext).apply {
            text = "✕  Close"
            setTextColor(Color.rgb(220, 228, 255))
            textSize = 14f
            gravity = Gravity.CENTER
            minWidth = dp(76)
            minHeight = dp(48)
            isClickable = true
            isFocusable = true
            setBackgroundResource(android.R.drawable.list_selector_background)
            setOnClickListener { hide() }
            contentDescription = "Close translation overlay"
        }
        header.addView(title, LinearLayout.LayoutParams(0, dp(48), 1f))
        header.addView(close, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT,
            dp(48)
        ))

        val body = TextView(appContext).apply {
            text = cleanText
            setTextColor(Color.rgb(244, 246, 250))
            textSize = 16f
            setLineSpacing(dp(3).toFloat(), 1f)
            setTextIsSelectable(true)
            contentDescription = "Translated text"
        }
        val scroll = ScrollView(appContext).apply {
            isFillViewport = true
            isClickable = true
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
            (screenWidth - dp(24)).coerceAtLeast(dp(200)),
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            // Keep the window touch/focus capable. Only touches outside the panel pass through.
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
            y = dp(72)
            softInputMode = WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN
        }

        // Dragging the title area lets the user move the panel out of the way.
        var startWindowX = 0
        var startWindowY = 0
        var startTouchX = 0f
        var startTouchY = 0f
        header.setOnTouchListener { _, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    startWindowX = params.x
                    startWindowY = params.y
                    startTouchX = event.rawX
                    startTouchY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    params.x = startWindowX + (event.rawX - startTouchX).toInt()
                    params.y = (startWindowY + (event.rawY - startTouchY).toInt())
                        .coerceAtLeast(0)
                    try {
                        windowManager.updateViewLayout(card, params)
                    } catch (_: IllegalArgumentException) {
                        // The system may detach the overlay while it is being dragged.
                    }
                    true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> true
                else -> false
            }
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
