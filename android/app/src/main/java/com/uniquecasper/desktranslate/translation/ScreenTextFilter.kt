package com.uniquecasper.desktranslate.translation

/**
 * Drops screen lines that do not need language translation (numbers, URLs and standalone
 * handles). This follows the low-noise filtering idea used by TextGrab, independently
 * implemented for DeskTranslate's batch translator.
 */
internal object ScreenTextFilter {
    private val numericOnly = Regex(
        """^[\d\s.,:;/%$€£¥₺+\-–()×x*]*\d[\d\s.,:;/%$€£¥₺+\-–()×x*]*$""",
        RegexOption.IGNORE_CASE
    )
    private val protectedOnly = Regex(
        """^(?:https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.[\w.]+|[@#]\w+)$""",
        RegexOption.IGNORE_CASE
    )

    fun isTranslatable(line: String): Boolean {
        val value = line.trim()
        if (value.isEmpty() || value.none(Char::isLetter)) return false
        if (numericOnly.matches(value) || protectedOnly.matches(value)) return false
        return true
    }
}
