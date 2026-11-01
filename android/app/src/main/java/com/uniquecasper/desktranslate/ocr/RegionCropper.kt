package com.uniquecasper.desktranslate.ocr

import android.graphics.Bitmap
import android.graphics.Rect
import kotlin.math.max

/**
 * Creates a bounded context crop around an OCR target. This is used only for a small
 * number of low-confidence lines, so retry OCR focuses on the relevant pixels instead
 * of repeatedly processing the full display.
 *
 * Design reference: TargetCrop in AidanPark/screen-translator at Apache-2.0 commit 8717cf0.
 * This is an independent DeskTranslate implementation, not copied source.
 */
object RegionCropper {
    data class Crop(
        val bitmap: Bitmap,
        val sourceBounds: Rect,
        val scale: Float
    ) : AutoCloseable {
        override fun close() {
            if (!bitmap.isRecycled) bitmap.recycle()
        }

        fun toScreenBounds(cropBounds: Rect): Rect {
            val inverse = if (scale > 0f) 1f / scale else 1f
            return Rect(
                sourceBounds.left + (cropBounds.left * inverse).toInt(),
                sourceBounds.top + (cropBounds.top * inverse).toInt(),
                sourceBounds.left + (cropBounds.right * inverse).toInt(),
                sourceBounds.top + (cropBounds.bottom * inverse).toInt()
            )
        }
    }

    fun around(
        source: Bitmap,
        target: Rect,
        minimumMarginPx: Int = 32,
        maxDimensionPx: Int = 768
    ): Crop? {
        if (source.isRecycled || source.width <= 0 || source.height <= 0) return null
        if (minimumMarginPx < 0 || maxDimensionPx < 64) return null

        val marginX = max(minimumMarginPx, (target.width() * 0.2f).toInt())
        val marginY = max(minimumMarginPx, (target.height() * 0.2f).toInt())
        val bounds = Rect(target).apply {
            inset(-marginX, -marginY)
            intersect(0, 0, source.width, source.height)
        }
        if (bounds.width() <= 0 || bounds.height() <= 0) return null

        val scale = minOf(
            1f,
            maxDimensionPx.toFloat() / maxOf(bounds.width(), bounds.height())
        )
        val crop = try {
            Bitmap.createBitmap(source, bounds.left, bounds.top, bounds.width(), bounds.height())
        } catch (_: IllegalArgumentException) {
            return null
        }
        val output = if (scale < 1f) {
            val scaled = Bitmap.createScaledBitmap(
                crop,
                (crop.width * scale).toInt().coerceAtLeast(1),
                (crop.height * scale).toInt().coerceAtLeast(1),
                true
            )
            if (scaled !== crop) crop.recycle()
            scaled
        } else {
            crop
        }
        return Crop(output, bounds, scale)
    }
}
