package com.uniquecasper.desktranslate.overlay

import android.graphics.Rect

/**
 * One OCR line and its translated text, with the screen-space box returned by capture.
 * The id is a request identity, not the source string; this prevents old network results
 * from being applied to a newer screen frame.
 *
 * Coordinate-overlay model inspired by the MIT-licensed ALSTMobile project.
 */
data class TranslatedRegion(
    val id: Long,
    val sourceText: String,
    val translatedText: String,
    val bounds: Rect,
    val backgroundColor: Int,
    val textColor: Int,
    val lineHeightPx: Int
)
