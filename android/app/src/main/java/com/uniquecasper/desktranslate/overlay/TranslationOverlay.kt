package com.uniquecasper.desktranslate.overlay

import android.content.Context
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.Rect
import android.graphics.drawable.GradientDrawable
import android.provider.Settings
import android.view.Gravity
import android.view.MotionEvent
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import kotlin.math.abs

/**
 * Displays both a touch-through, coordinate-aligned translation layer and a separate
 * draggable control. The translation layer never consumes game/app touches; only the
 * small control is interactive.
 *
 * The two-window layout follows the in-place overlay pattern explored by ALSTMobile
 * (MIT). This implementation uses native Android views to avoid a separate Compose
 * lifecycle owner for background windows.
 */
class TranslationOverlay(context: Context) {
    private val appContext = context.applicationContext
    private val windowManager =
        appContext.getSystemService(Context.WINDOW_SERVICE) as WindowManager

    private var attachedView: LinearLayout? = null
    private var regionView: FrameLayout? = null
    private var fabView: TextView? = null
    private var regionParams: WindowManager.LayoutParams? = null
    private var fabParams: WindowManager.LayoutParams? = null
    private var regionsVisible = true

    private val density = appContext.resources.displayMetrics.density
    private fun dp(value: Int): Int = (value * density).toInt().coerceAtLeast(1)

    fun showFab() {
        if (fabView != null || !Settings.canDrawOverlays(appContext)) return

        val fab = TextView(appContext).apply {
            text = "DT"
            setTextColor(Color.WHITE)
            textSize = 15f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            isClickable = true
            contentDescription = "DeskTranslate translation control. Tap to hide or show translated screen lines. Drag to move."
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(Color.rgb(68, 52, 145))
                setStroke(dp(2), Color.argb(190, 225, 220, 255))
            }
            elevation = dp(8).toFloat()
        }
        val params = WindowManager.LayoutParams(
            dp(54),
            dp(54),
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.END
            x = dp(12)
            y = dp(180)
        }

        var downRawX = 0f
        var downRawY = 0f
        var startX = params.x
        var startY = params.y
        var moved = false
        fab.setOnTouchListener { _, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    downRawX = event.rawX
                    downRawY = event.rawY
                    startX = params.x
                    startY = params.y
                    moved = false
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = event.rawX - downRawX
                    val dy = event.rawY - downRawY
                    if (abs(dx) > dp(5) || abs(dy) > dp(5)) moved = true
                    if (moved) {
                        params.x = (startX - dx.toInt()).coerceAtLeast(0)
                        params.y = (startY + dy.toInt()).coerceAtLeast(0)
                        try {
                            windowManager.updateViewLayout(fab, params)
                        } catch (_: IllegalArgumentException) {
                            // The system may detach the control while it is being moved.
                        }
                    }
                    true
                }
                MotionEvent.ACTION_UP -> {
                    if (!moved) toggleRegions()
                    true
                }
                MotionEvent.ACTION_CANCEL -> true
                else -> false
            }
        }

        try {
            windowManager.addView(fab, params)
            fabView = fab
            fabParams = params
        } catch (error: WindowManager.BadTokenException) {
            fabView = null
            fabParams = null
            throw IllegalStateException("Android rejected the floating control window", error)
        } catch (error: SecurityException) {
            fabView = null
            fabParams = null
            throw IllegalStateException("DeskTranslate does not have overlay permission", error)
        }
    }

    /**
     * Draw translated text over the matching OCR line rectangles. All measurements are
     * screen pixels from MediaProjection; the overlay window is full-display and touch-through.
     */
    fun showBlocks(blocks: List<TranslatedRegion>) {
        check(Settings.canDrawOverlays(appContext)) {
            "DeskTranslate needs permission to display translations over other apps."
        }
        require(blocks.isNotEmpty()) { "There are no translated screen regions to display." }

        removeRegionView()
        val metrics = appContext.resources.displayMetrics
        val screenWidth = metrics.widthPixels
        val screenHeight = metrics.heightPixels
        val root = FrameLayout(appContext).apply {
            setBackgroundColor(Color.TRANSPARENT)
            isClickable = false
            isFocusable = false
        }

        blocks.take(MAX_REGION_COUNT).forEach { block ->
            val text = block.translatedText.trim()
            if (text.isEmpty()) return@forEach
            val bounds = Rect(block.bounds).apply {
                intersect(0, 0, screenWidth, screenHeight)
            }
            if (bounds.isEmpty) return@forEach

            val width = bounds.width().coerceAtLeast(dp(40))
                .coerceAtMost((screenWidth - bounds.left).coerceAtLeast(dp(40)))
            val height = bounds.height().coerceAtLeast(dp(22))
            val lineHeightDp = block.lineHeightPx / density
            val sizeSp = (lineHeightDp * 0.68f).coerceIn(MIN_TEXT_SP, MAX_TEXT_SP)

            val label = TextView(appContext).apply {
                this.text = text
                setTextColor(block.textColor)
                textSize = sizeSp
                includeFontPadding = false
                gravity = Gravity.CENTER_VERTICAL
                maxLines = MAX_LINES_PER_REGION
                setPadding(dp(3), dp(1), dp(3), dp(1))
                isClickable = false
                isFocusable = false
                background = GradientDrawable().apply {
                    setColor(withAlpha(block.backgroundColor, OVERLAY_ALPHA))
                    cornerRadius = dp(3).toFloat()
                    setStroke(dp(1), Color.argb(90, 255, 255, 255))
                }
            }
            val layout = FrameLayout.LayoutParams(
                width,
                height,
                Gravity.TOP or Gravity.START
            ).apply {
                leftMargin = bounds.left
                topMargin = bounds.top
            }
            root.addView(label, layout)
        }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = 0
            y = 0
        }

        windowManager.addView(root, params)
        regionView = root
        regionParams = params
        regionsVisible = true
        root.visibility = FrameLayout.VISIBLE
    }

    private fun withAlpha(color: Int, alpha: Int): Int =
        Color.argb(alpha, Color.red(color), Color.green(color), Color.blue(color))

    private fun toggleRegions() {
        val view = regionView ?: return
        regionsVisible = !regionsVisible
        view.visibility = if (regionsVisible) FrameLayout.VISIBLE else FrameLayout.GONE
    }

    fun show(translation: String) {
        val cleanText = translation.trim().take(MAX_TEXT_LENGTH)
        require(cleanText.isNotEmpty()) { "There is no translation to display." }
        check(Settings.canDrawOverlays(appContext)) {
            "DeskTranslate needs permission to display a floating translation."
        }

        hidePanel()
        val card = LinearLayout(appContext).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(12), dp(16), dp(14))
            background = GradientDrawable().apply {
                setColor(Color.rgb(27, 31, 42))
                cornerRadius = dp(18).toFloat()
                setStroke(dp(1), Color.argb(110, 185, 196, 220))
            }
            elevation = dp(12).toFloat()
            isClickable = true
            isFocusable = true
        }
        val header = LinearLayout(appContext).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val title = TextView(appContext).apply {
            text = "DeskTranslate · Translation"
            setTextColor(Color.WHITE)
            textSize = 14f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
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
            setOnClickListener { hidePanel() }
            contentDescription = "Close translation panel"
        }
        header.addView(title, LinearLayout.LayoutParams(0, dp(48), 1f))
        header.addView(close, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT, dp(48)
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
            addView(body, FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.WRAP_CONTENT
            ))
        }
        card.addView(header)
        card.addView(scroll, LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, dp(280)
        ))

        val screenWidth = appContext.resources.displayMetrics.widthPixels
        val params = WindowManager.LayoutParams(
            (screenWidth - dp(24)).coerceAtLeast(dp(200)),
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
            y = dp(72)
            softInputMode = WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN
        }

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
                    params.y = (startWindowY + (event.rawY - startTouchY).toInt()).coerceAtLeast(0)
                    try {
                        windowManager.updateViewLayout(card, params)
                    } catch (_: IllegalArgumentException) {
                        // The system may detach the panel while it is being dragged.
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

    private fun hidePanel() {
        val view = attachedView ?: return
        attachedView = null
        try {
            windowManager.removeView(view)
        } catch (_: IllegalArgumentException) {
            // The Android window may already have been detached.
        }
    }

    private fun removeRegionView() {
        val view = regionView ?: return
        regionView = null
        regionParams = null
        try {
            windowManager.removeView(view)
        } catch (_: IllegalArgumentException) {
            // The Android window may already have been detached.
        }
    }

    fun hide() {
        hidePanel()
        removeRegionView()
        val fab = fabView
        fabView = null
        fabParams = null
        if (fab != null) {
            try {
                windowManager.removeView(fab)
            } catch (_: IllegalArgumentException) {
                // The Android window may already have been detached.
            }
        }
    }

    companion object {
        private const val MAX_TEXT_LENGTH = 20_000
        private const val MAX_REGION_COUNT = 60
        private const val MAX_LINES_PER_REGION = 4
        private const val MIN_TEXT_SP = 10f
        private const val MAX_TEXT_SP = 18f
        private const val OVERLAY_ALPHA = 226
    }
}
