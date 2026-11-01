package com.uniquecasper.desktranslate.ocr

import android.graphics.Bitmap
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.TextRecognizer
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions

class OcrEngine : AutoCloseable {
    private val latin: TextRecognizer =
        TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
    private val japanese: TextRecognizer =
        TextRecognition.getClient(JapaneseTextRecognizerOptions.Builder().build())

    fun recognize(bitmap: Bitmap, script: String): String {
        val recognizer = if (script.equals("Japanese", ignoreCase = true)) japanese else latin
        val result = Tasks.await(recognizer.process(InputImage.fromBitmap(bitmap, 0)))
        return result.text.trim()
    }

    override fun close() {
        latin.close()
        japanese.close()
    }
}
