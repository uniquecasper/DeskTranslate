package com.uniquecasper.desktranslate

import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
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
import com.uniquecasper.desktranslate.security.CredentialStore
import com.uniquecasper.desktranslate.translation.ProviderClient
import com.uniquecasper.desktranslate.translation.ProviderConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {
    private val recognizedText = mutableStateOf("")
    private val statusText = mutableStateOf("Ready")
    private var requestedScript = "Latin"

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
            statusText.value = "Capture permission granted. Starting…"
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
        val filter = IntentFilter().apply {
            addAction(CaptureService.ACTION_OCR_RESULT)
            addAction(CaptureService.ACTION_CAPTURE_STATUS)
        }
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(receiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("DEPRECATION")
            registerReceiver(receiver, filter)
        }

        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    DeskTranslateScreen(
                        recognizedText = recognizedText.value,
                        status = statusText.value,
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

    override fun onDestroy() {
        unregisterReceiver(receiver)
        super.onDestroy()
    }
}

@androidx.compose.runtime.Composable
private fun DeskTranslateScreen(
    recognizedText: String,
    status: String,
    onStartCapture: (String) -> Unit,
    onStopCapture: () -> Unit
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

    LaunchedEffect(recognizedText) {
        if (recognizedText.isNotBlank()) sourceText = recognizedText
    }
    LaunchedEffect(status) {
        message = status
    }

    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("DeskTranslate", style = MaterialTheme.typography.headlineMedium)
        Text("Android companion · local OCR · selected translation provider")

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
                Text("Capture uses Android system consent and a visible foreground notification.")
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
                    onClick = {
                        busy = true
                        message = "Translating with the selected provider…"
                        val providerId = provider.trim().lowercase()
                        val config = ProviderConfig(
                            provider = providerId,
                            endpoint = endpoint.trim(),
                            model = model.trim(),
                            apiKey = apiKey.ifBlank { credentials.load(providerId).orEmpty() }
                        )
                        val text = sourceText
                        val source = sourceLanguage
                        val target = targetLanguage
                        scope.launch {
                            try {
                                translation = withContext(Dispatchers.IO) {
                                    ProviderClient.translate(config, text, source, target)
                                }
                                message = "Translation completed."
                            } catch (error: Exception) {
                                message = "Translation failed: " + (error.message ?: error.javaClass.simpleName)
                            } finally {
                                busy = false
                            }
                        }
                    }
                ) { Text(if (busy) "Working…" else "Translate") }
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
                    label = { Text("API key (optional for local Ollama)") },
                    visualTransformation = PasswordVisualTransformation(),
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        if (apiKey.isBlank()) {
                            message = "Enter a key before saving. Use Delete key to remove a stored key."
                        } else {
                            credentials.save(provider.trim().lowercase(), apiKey)
                            apiKey = ""
                            message = "Credential encrypted and saved for this provider."
                        }
                    }) { Text("Save key") }
                    TextButton(onClick = {
                        credentials.delete(provider.trim().lowercase())
                        apiKey = ""
                        message = "Saved credential deleted."
                    }) { Text("Delete key") }
                }
                Text("Supported adapters in this build: OpenAI, Ollama, Anthropic and Gemini.")
            }
        }

        Card(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Vocabulary learning", style = MaterialTheme.typography.titleMedium)
                Text("Save only after reviewing the source and translation.")
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
                entries.take(30).forEach { entry ->
                    VocabularyRow(entry = entry, onDelete = {
                        vocabulary.delete(entry.id)
                        entries = vocabulary.recent()
                    })
                }
            }
        }
        Text(
            "Privacy: screenshots and OCR frames are processed in memory. Only recognized text is sent to the provider you select.",
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
