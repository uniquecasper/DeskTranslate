package com.uniquecasper.desktranslate

/**
 * Prevents the initial MediaProjection frames of DeskTranslate's own settings
 * screen from being sent to a translation provider.
 */
internal object AutoTranslationPolicy {
    private val deskTranslateMarkers = listOf(
        "desktranslate",
        "screen capture",
        "provider configuration",
        "vocabulary learning",
        "start capture",
        "ocr script:",
        "save key"
    )

    fun isDeskTranslateUi(text: String): Boolean {
        val normalized = text.lowercase()
        return deskTranslateMarkers.count(normalized::contains) >= 3
    }
}
