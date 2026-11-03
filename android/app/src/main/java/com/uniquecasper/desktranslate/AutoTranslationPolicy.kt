package com.uniquecasper.desktranslate

/**
 * Prevents DeskTranslate's own settings screen from being sent to a translation provider.
 * OCR can return only the visible portion of the screen, so the brand plus one UI marker
 * is enough to identify our own app even when lower settings cards are not in the frame.
 */
internal object AutoTranslationPolicy {
    private val deskTranslateMarkers = listOf(
        "screencapture",
        "providerconfiguration",
        "vocabularylearning",
        "startcapture",
        "ocrscrip",
        "savekey"
    )

    fun isDeskTranslateUi(text: String): Boolean {
        val compact = text.lowercase().filter(Char::isLetterOrDigit)
        val markerCount = deskTranslateMarkers.count(compact::contains)
        val containsBrand = compact.contains("desktranslate")
        return (containsBrand && markerCount >= 1) || markerCount >= 3
    }
}
