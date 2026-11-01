package com.uniquecasper.desktranslate

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AutoTranslationPolicyTest {
    @Test
    fun ignoresDeskTranslateSettingsScreen() {
        val ownScreen = """
            DeskTranslate
            Screen capture
            Start capture
            OCR script: Latin
            Provider configuration
            Vocabulary learning
        """.trimIndent()

        assertTrue(AutoTranslationPolicy.isDeskTranslateUi(ownScreen))
    }

    @Test
    fun ignoresPartialCaptureOfDeskTranslateScreen() {
        val partialOwnScreen = """
            DeskTranslate
            Android companion automatic screen translation
            Screen capture
            Text recognized locally
            Start capture
            OCR script Latin
        """.trimIndent()

        assertTrue(AutoTranslationPolicy.isDeskTranslateUi(partialOwnScreen))
    }

    @Test
    fun allowsGameText() {
        val gameText = "Quest complete. Return to the village and speak with the guide."

        assertFalse(AutoTranslationPolicy.isDeskTranslateUi(gameText))
    }

    @Test
    fun doesNotIgnoreTextWithOnlyOneCommonMarker() {
        assertFalse(AutoTranslationPolicy.isDeskTranslateUi("The screen capture begins now."))
    }
}
