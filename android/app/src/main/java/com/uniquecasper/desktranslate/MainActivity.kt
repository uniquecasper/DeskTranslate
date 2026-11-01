package com.uniquecasper.desktranslate

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import android.provider.Settings
import android.media.projection.MediaProjectionManager
import android.os.Bundle
import android.os.SystemClock
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.uniquecasper.desktranslate.capture.CaptureService
import com.uniquecasper.desktranslate.learning.VocabularyEntry
import com.uniquecasper.desktranslate.learning.VocabularyStore
import com.uniquecasper.desktranslate.overlay.TranslationOverlay
import com.uniquecasper.desktranslate.security.CredentialStore
import com.uniquecasper.desktranslate.translation.ProviderClient
import com.uniquecasper.desktranslate.translation.ProviderConfig
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {
    private val recognizedText = mutableStateOf("")
    private val statusText = mutableStateOf("Ready")
    private var requestedScript = "Latin"
    private lateinit var translationOverlay: TranslationOverlay
    private var pendingOverlayText: String? = null
    private var overlayPermissionPrompted = false

    private val projectionLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val data = result.data
        if (result.resultCode == Activity.RESULT_OK && data != null) {
            val service = Intent(this, CaptureService::class.java).apply {
                action = CaptureService.ACTION_START
                putExtra(CaptureService.EXTRA_RESULT_CODE, result.resultCode)
                putExtra(CaptureService.EXTRA_RESULT_DATA, data)
                putExtra(CaptureService.EXTRA_SCRIPT, requestedScript)
            }
            startForegroundService(service)
            statusText.value = "Capture started. Switch to the app or game you want to translate."
            requestOverlayPermissionForSession()
        } else {
            statusText.value = "Screen capture permission was declined."
        }
    }

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                CaptureService.ACTION_OCR_RESULT -> {
                    recognizedText.value = intent.getStringExtra(CaptureService.EXTRA_TEXT).orEmpty()
                    statusText.value = "Text recognized locally."
                }
                CaptureService.ACTION_CAPTURE_STATUS -> {
                    statusText.value = intent.getStringExtra(CaptureService.EXTRA_TEXT).orEmpty()
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        translationOverlay = TranslationOverlay(this)
        val filter = IntentFilter().apply {
            addAction(CaptureService.ACTION_OCR_RESULT)
            addAction(CaptureService.ACTION_CAPTURE_STATUS)
        }
        ContextCompat.registerReceiver(
            this,
            receiver,
            filter,
            ContextCompat.RECEIVER_NOT_EXPORTED
        )

        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    DeskTranslateScreen(
                        recognizedText = recognizedText.value,
                        status = statusText.value,
                        onShowOverlay = { text -> showTranslationOverlay(text) },
                        onStartCapture = { script ->
                            requestedScript = script
                            val manager = getSystemService(MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
                            projectionLauncher.launch(manager.createScreenCaptureIntent())
                        },
                        onStopCapture = {
                            startService(Intent(this, CaptureService::class.java).setAction(CaptureService.ACTION_STOP))
                            statusText.value = "Capture stopped."
                        }
                    )
                }
            }
        }
    }

    private fun requestOverlayPermissionForSession() {
        if (Settings.canDrawOverlays(this) || overlayPermissionPrompted) return
        overlayPermissionPrompted = true
        statusText.value = "Grant Display over other apps so translations can appear automatically."
        val settingsIntent = Intent(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse("package:$packageName")
        )
        startActivity(settingsIntent)
    }

    private fun showTranslationOverlay(text: String) {
        if (!Settings.canDrawOverlays(this)) {
            pendingOverlayText = text
            statusText.value = "Translation is ready. Grant Display over other apps to show it automatically."
            if (!overlayPermissionPrompted) requestOverlayPermissionForSession()
            return
        }
        try {
            translationOverlay.show(text)
            pendingOverlayText = null
            statusText.value = "Floating translation updated automatically."
        } catch (error: Exception) {
            statusText.value = "Could not show overlay: " + (error.message ?: error.javaClass.simpleName)
        }
    }

    override fun onResume() {
        super.onResume()
        val pending = pendingOverlayText
        if (pending != null && Settings.canDrawOverlays(this)) {
            showTranslationOverlay(pending)
        }
    }

    override fun onDestroy() {
        translationOverlay.hide()
        unregisterReceiver(receiver)
        super.onDestroy()
    }
}

@androidx.compose.runtime.Composable
private fun DeskTranslateScreen(
    recognizedText: String,
    status: String,
    onStartCapture: (String) -> Unit,
    onStopCapture: () -> Unit,
    onShowOverlay: (String) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val credentials = remember { CredentialStore(context) }
    val vocabulary = remember { VocabularyStore(context) }

    var sourceText by remember { mutableStateOf(recognizedText) }
    var translation by remember { mutableStateOf("") }
    var sourceLanguage by remember { mutableStateOf("auto") }
    var targetLanguage by remember { mutableStateOf("tr") }
    var provider by remember { mutableStateOf("openai") }
    var endpoint by remember { mutableStateOf("https://api.openai.com/v1") }
    var model by remember { mutableStateOf("gpt-4.1-mini") }
    var apiKey by remember { mutableStateOf("") }
    var script by remember { mutableStateOf("Latin") }
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf(status) }
    var entries by remember { mutableStateOf(vocabulary.recent()) }
    var credentialRevision by remember { mutableStateOf(0) }
    var lastAutoAttemptSignature by remember { mutableStateOf("") }
    var lastAutoTranslationAt by remember { mutableStateOf(0L) }

    val providerId = provider.trim().lowercase()
    val storedKey = remember(providerId, credentialRevision) {
        if (providerId.matches(Regex("[a-z0-9_-]{1,40}"))) {
            credentials.load(providerId).orEmpty()
        } else {
            ""
        }
    }
    val effectiveApiKey = apiKey.trim().ifBlank { storedKey }

    LaunchedEffect(status) {
        message = status
    }

    suspend fun translateText(input: String, automatic: Boolean) {
        val text = input.trim().take(12000)
        if (text.isBlank()) {
            message = "There is no text to translate."
            return
        }
        if (busy) return

        val config = ProviderConfig(
            provider = providerId,
            endpoint = endpoint.trim(),
            model = model.trim(),
            apiKey = effectiveApiKey
        )
        busy = true
        message = if (automatic) {
            "New screen text detected. Translating…"
        } else {
            "Translating with the selected provider…"
        }
        try {
            val result = withContext(Dispatchers.IO) {
                ProviderClient.translate(config, text, sourceLanguage, targetLanguage)
            }
            translation = result
            if (automatic) lastAutoTranslationAt = SystemClock.elapsedRealtime()
            message = "Translation completed. Opening floating panel…"
            onShowOverlay(result)
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (error: Exception) {
            message = "Translation failed: " + (error.message ?: error.javaClass.simpleName)
        } finally {
            busy = false
        }
    }

    LaunchedEffect(
        recognizedText,
        providerId,
        endpoint,
        model,
        effectiveApiKey,
        sourceLanguage,
        targetLanguage,
        busy
    ) {
        val candidate = recognizedText.trim().take(12000)
        if (candidate.isBlank()) return@LaunchedEffect

        // MediaProjection initially captures DeskTranslate itself. Never send our
        // settings screen or floating panel text to a translation provider.
        if (AutoTranslationPolicy.isDeskTranslateUi(candidate)) {
            sourceText = ""
            message = "DeskTranslate screen detected. Switch to the game or app you want to translate."
            return@LaunchedEffect
        }

        sourceText = candidate
        val signature = listOf(
            providerId,
            endpoint.trim(),
            model.trim(),
            effectiveApiKey,
            sourceLanguage,
            targetLanguage,
            candidate
        ).joinToString("\u0000")
        if (signature == lastAutoAttemptSignature) return@LaunchedEffect

        // Let OCR settle, then wait out the cooldown without tying the network call
        // to this effect. OCR updates can cancel this effect, but must not cancel a
        // request already in progress.
        delay(1200)
        if (recognizedText.trim().take(12000) != candidate) return@LaunchedEffect

        val elapsed = SystemClock.elapsedRealtime() - lastAutoTranslationAt
        val remaining = AUTO_TRANSLATION_COOLDOWN_MS - elapsed
        if (remaining > 0) delay(remaining)
        if (recognizedText.trim().take(12000) != candidate || busy) return@LaunchedEffect

        lastAutoAttemptSignature = signature
        scope.launch {
            translateText(candidate, automatic = true)
        }
    }

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("DeskTranslate", style = MaterialTheme.typography.headlineMedium)
        Text("Android companion · on-device OCR · automatic screen translation")

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Screen capture", style = MaterialTheme.typography.titleMedium)
                Text(message, style = MaterialTheme.typography.bodySmall)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = { onStartCapture(script) }) { Text("Start capture") }
                    TextButton(onClick = onStopCapture) { Text("Stop") }
                }
                OutlinedTextField(
                    value = script,
                    onValueChange = { script = it.take(20) },
                    label = { Text("OCR script: Latin or Japanese") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                Text(
                    "After capture starts, switch to the app or game you want to translate. " +
                        "OCR reads the whole screen, including text inside DeskTranslate."
                )
                Text("New stable OCR text is translated automatically. The floating panel updates after each successful translation.")
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Translation", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = sourceText,
                    onValueChange = { sourceText = it.take(12000) },
                    label = { Text("Recognized or entered text") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 3
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(
                        value = sourceLanguage,
                        onValueChange = { sourceLanguage = it.take(20) },
                        label = { Text("Source language") },
                        modifier = Modifier.weight(1f),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = targetLanguage,
                        onValueChange = { targetLanguage = it.take(20) },
                        label = { Text("Target language") },
                        modifier = Modifier.weight(1f),
                        singleLine = true
                    )
                }
                OutlinedTextField(
                    value = translation,
                    onValueChange = { translation = it.take(20000) },
                    label = { Text("Translation") },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 3
                )
                Button(
                    enabled = !busy && sourceText.isNotBlank(),
                    onClick = { scope.launch { translateText(sourceText, automatic = false) } }
                ) { Text(if (busy) "Working…" else "Translate now") }
                Text(
                    "Manual translation is available for edited text. Screen OCR is translated automatically.",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Provider configuration", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(
                    value = provider,
                    onValueChange = { provider = it.take(40).lowercase() },
                    label = { Text("Provider: openai, ollama, anthropic, gemini") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                OutlinedTextField(
                    value = endpoint,
                    onValueChange = { endpoint = it.take(2048) },
                    label = { Text("Base endpoint") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                OutlinedTextField(
                    value = model,
                    onValueChange = { model = it.take(200) },
                    label = { Text("Model ID") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                OutlinedTextField(
                    value = apiKey,
                    onValueChange = { apiKey = it.take(4096) },
                    label = { Text("API key") },
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                Text(
                    when (providerId) {
                        "openai" -> "OpenAI requires a valid API key. Enter it here, then press Save key."
                        "anthropic" -> "Anthropic requires an API key."
                        "gemini" -> "Gemini requires an API key."
                        "ollama" -> "API key is optional for a local Ollama server."
                        else -> "Choose openai, ollama, anthropic or gemini."
                    },
                    style = MaterialTheme.typography.bodySmall
                )
                if (storedKey.isNotBlank()) {
                    Text("An encrypted key is saved on this device for $providerId.")
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        if (apiKey.isBlank()) {
                            message = "Enter an API key before saving."
                        } else if (!providerId.matches(Regex("[a-z0-9_-]{1,40}"))) {
                            message = "Provider ID is invalid."
                        } else {
                            credentials.save(providerId, apiKey.trim())
                            apiKey = ""
                            credentialRevision++
                            message = "API key encrypted and saved on this device."
                        }
                    }) { Text("Save key") }
                    TextButton(onClick = {
                        if (providerId.matches(Regex("[a-z0-9_-]{1,40}"))) {
                            credentials.delete(providerId)
                            apiKey = ""
                            credentialRevision++
                            message = "Saved API key deleted."
                        } else {
                            message = "Provider ID is invalid."
                        }
                    }) { Text("Delete key") }
                }
                Text("Supported adapters: OpenAI, Ollama, Anthropic and Gemini.")
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Vocabulary learning", style = MaterialTheme.typography.titleMedium)
                Text("Optional: save a reviewed source-text and translation pair locally.")
                Button(
                    enabled = sourceText.isNotBlank() && translation.isNotBlank(),
                    onClick = {
                        try {
                            vocabulary.save(sourceText, translation, sourceLanguage, targetLanguage)
                            entries = vocabulary.recent()
                            message = "Vocabulary entry saved locally."
                        } catch (error: Exception) {
                            message = "Could not save entry: " + error.javaClass.simpleName
                        }
                    }
                ) { Text("Save approved vocabulary") }
                Text(
                    "This section currently stores whole text/translation pairs on this device. " +
                        "Tap-a-word definitions and learned-word filtering are not implemented yet."
                )
                entries.take(30).forEach { entry ->
                    VocabularyRow(entry = entry, onDelete = {
                        vocabulary.delete(entry.id)
                        entries = vocabulary.recent()
                    })
                }
            }
        }
        Text(
            "Privacy: screenshots and OCR frames are processed in memory. Only recognized text is sent to the provider you select. " +
                "Provider keys are encrypted with Android Keystore.",
            style = MaterialTheme.typography.bodySmall
        )
    }
}

@androidx.compose.runtime.Composable
private fun VocabularyRow(entry: VocabularyEntry, onDelete: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(entry.source, style = MaterialTheme.typography.bodyMedium)
            Text(entry.translation, style = MaterialTheme.typography.bodySmall)
            Text(entry.sourceLanguage + " → " + entry.targetLanguage, style = MaterialTheme.typography.labelSmall)
        }
        TextButton(onClick = onDelete) { Text("Delete") }
    }
}

private const val AUTO_TRANSLATION_COOLDOWN_MS = 8_000L
