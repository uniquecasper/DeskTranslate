package com.uniquecasper.desktranslate.ocr

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Rect
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.Text
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.TextRecognizer
import com.google.mlkit.vision.text.chinese.ChineseTextRecognizerOptions
import com.google.mlkit.vision.text.japanese.JapaneseTextRecognizerOptions
import com.google.mlkit.vision.text.korean.KoreanTextRecognizerOptions
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import java.util.concurrent.atomic.AtomicLong
import kotlin.math.max
import kotlin.math.min

/**
 * Structured, line-oriented OCR. It retains screen coordinates rather than flattening
 * the frame to a string, allowing translated lines to be drawn over their source regions.
 *
 * Architecture reference: TextGrab (AhmetCanArslan/TextGrab, MIT). This implementation
 * is independently written for DeskTranslate's capture-service contract.
 */
data class OcrTextBlock(
    val id: Long,
    val text: String,
    val bounds: Rect,
    val confidence: Float,
    val backgroundColor: Int,
    val textColor: Int,
    val lineHeightPx: Int
)

class OcrEngine : AutoCloseable {
    private val latin = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)
    private val japanese = TextRecognition.getClient(JapaneseTextRecognizerOptions.Builder().build())
    private val chinese = TextRecognition.getClient(ChineseTextRecognizerOptions.Builder().build())
    private val korean = TextRecognition.getClient(KoreanTextRecognizerOptions.Builder().build())
    private val ids = AtomicLong(System.currentTimeMillis() shl 12)

    fun recognize(bitmap: Bitmap, script: String): List<OcrTextBlock> {
        require(!bitmap.isRecycled && bitmap.width > 0 && bitmap.height > 0) {
            "OCR received an invalid screen frame"
        }
        val image = InputImage.fromBitmap(bitmap, 0)
        val candidates = recognizersFor(script).map { recognizer ->
            val result = Tasks.await(recognizer.process(image))
            score(result)
        }
        val best = candidates.maxByOrNull { it.score } ?: return emptyList()
        return best.lines
            .sortedWith(compareBy<RawLine> { it.bounds.top }.thenBy { it.bounds.left })
            .take(MAX_LINES)
            .map { line ->
                val rect = Rect(line.bounds).apply { intersect(0, 0, bitmap.width, bitmap.height) }
                if (rect.isEmpty) return@map null
                val bg = estimateBackground(bitmap, rect)
                OcrTextBlock(
                    id = ids.incrementAndGet(),
                    text = line.text,
                    bounds = rect,
                    confidence = line.confidence,
                    backgroundColor = bg,
                    textColor = if (isDark(bg)) Color.WHITE else Color.BLACK,
                    lineHeightPx = max(1, rect.height())
                )
            }
            .filterNotNull()
    }

    private fun recognizersFor(script: String): List<TextRecognizer> =
        when (script.trim().lowercase()) {
            "japanese" -> listOf(japanese)
            "chinese" -> listOf(chinese)
            "korean" -> listOf(korean)
            "auto" -> listOf(latin, japanese, chinese, korean)
            else -> listOf(latin)
        }

    private fun score(result: Text): ScoredResult {
        val lines = ArrayList<RawLine>()
        var weightedScore = 0f
        for (block in result.textBlocks) {
            for (line in block.lines) {
                val elements = line.elements.mapNotNull { element ->
                    val value = element.text.trim()
                    val confidence = element.confidence.takeIf { it > 0f } ?: 0.7f
                    val alphanumeric = value.count(Char::isLetterOrDigit)
                    if (value.isEmpty() || (alphanumeric == 0 && value.length <= 2) ||
                        (element.confidence > 0f && element.confidence < MIN_CONFIDENCE)
                    ) null else Triple(element, value, confidence)
                }
                if (elements.isEmpty()) continue

                val text = elements.joinToString(" ") { it.second }
                val box = Rect(elements.first().first.boundingBox ?: line.boundingBox ?: continue)
                elements.forEach { item ->
                    item.first.boundingBox?.let(box::union)
                    weightedScore += item.second.count(Char::isLetterOrDigit) * item.third
                }
                val confidence = elements.map { it.third }.average().toFloat()
                if (text.isNotBlank() && !box.isEmpty) lines.add(RawLine(text, box, confidence))
            }
        }
        return ScoredResult(lines, weightedScore)
    }

    private fun estimateBackground(bitmap: Bitmap, rect: Rect): Int {
        val left = (rect.left - EDGE_SAMPLE_MARGIN).coerceAtLeast(0)
        val right = (rect.right + EDGE_SAMPLE_MARGIN).coerceAtMost(bitmap.width - 1)
        val top = (rect.top - EDGE_SAMPLE_MARGIN).coerceAtLeast(0)
        val bottom = (rect.bottom + EDGE_SAMPLE_MARGIN).coerceAtMost(bitmap.height - 1)
        val samples = ArrayList<Int>()
        for (x in left..right step EDGE_SAMPLE_STEP) {
            samples.add(bitmap.getPixel(x, top))
            samples.add(bitmap.getPixel(x, bottom))
        }
        for (y in top..bottom step EDGE_SAMPLE_STEP) {
            samples.add(bitmap.getPixel(left, y))
            samples.add(bitmap.getPixel(right, y))
        }
        if (samples.isEmpty()) return DEFAULT_BACKGROUND
        return samples
            .map { it and COLOR_QUANTIZE_MASK }
            .groupingBy { it }
            .eachCount()
            .maxByOrNull { it.value }
            ?.key ?: DEFAULT_BACKGROUND
    }

    private fun isDark(color: Int): Boolean {
        val luminance = 0.299 * Color.red(color) +
            0.587 * Color.green(color) + 0.114 * Color.blue(color)
        return luminance < 145
    }

    override fun close() {
        latin.close()
        japanese.close()
        chinese.close()
        korean.close()
    }

    private data class RawLine(val text: String, val bounds: Rect, val confidence: Float)
    private data class ScoredResult(val lines: List<RawLine>, val score: Float)

    companion object {
        private const val MAX_LINES = 80
        private const val MIN_CONFIDENCE = 0.45f
        private const val EDGE_SAMPLE_MARGIN = 2
        private const val EDGE_SAMPLE_STEP = 4
        private const val COLOR_QUANTIZE_MASK = -526345
        private const val DEFAULT_BACKGROUND = 0xFF202124.toInt()
    }
}
