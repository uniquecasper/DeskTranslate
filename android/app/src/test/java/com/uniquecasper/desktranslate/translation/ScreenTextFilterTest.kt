package com.uniquecasper.desktranslate.translation

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ScreenTextFilterTest {
    @Test
    fun skipsNumericOnlyLines() {
        assertFalse(ScreenTextFilter.isTranslatable("20/20"))
        assertFalse(ScreenTextFilter.isTranslatable("1,250 ₺"))
    }

    @Test
    fun skipsStandaloneLinksAndHandles() {
        assertFalse(ScreenTextFilter.isTranslatable("https://example.com/path"))
        assertFalse(ScreenTextFilter.isTranslatable("@player_one"))
        assertFalse(ScreenTextFilter.isTranslatable("#dailyquest"))
    }

    @Test
    fun keepsNaturalScreenSentences() {
        assertTrue(ScreenTextFilter.isTranslatable("Quest complete. Return to the village."))
        assertTrue(ScreenTextFilter.isTranslatable("Press E to continue"))
    }
}
