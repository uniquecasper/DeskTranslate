package com.uniquecasper.desktranslate.translation

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class ProviderClientTest {
    @Test
    fun acceptsHttpsProviderEndpoint() {
        assertEquals(
            "https://api.openai.com/v1",
            ProviderClient.validateEndpoint("https://api.openai.com/v1/")
        )
    }

    @Test
    fun allowsHttpOnlyForLoopback() {
        assertEquals("http://localhost:11434", ProviderClient.validateEndpoint("http://localhost:11434/"))
        assertThrows(IllegalArgumentException::class.java) {
            ProviderClient.validateEndpoint("http://192.168.1.20:11434")
        }
    }

    @Test
    fun rejectsEmbeddedCredentialsAndFragments() {
        assertThrows(IllegalArgumentException::class.java) {
            ProviderClient.validateEndpoint("https://user:pass@example.com/v1")
        }
        assertThrows(IllegalArgumentException::class.java) {
            ProviderClient.validateEndpoint("https://example.com/v1#token")
        }
    }

    @Test
    fun promptTreatsRecognizedTextAsUntrustedContent() {
        val prompt = ProviderClient.buildPrompt("Japanese", "Turkish")
        assert(prompt.contains("untrusted content"))
        assert(prompt.contains("Japanese"))
        assert(prompt.contains("Turkish"))
    }

    @Test
    fun openAiRequiresAnApiKeyBeforeNetworkRequest() {
        val error = assertThrows(IllegalArgumentException::class.java) {
            ProviderClient.validateCredentials(ProviderConfig("openai", "https://api.openai.com/v1", "gpt-4.1-mini", ""))
        }
        assertTrue(error.message.orEmpty().contains("requires an API key"))
    }

    @Test
    fun localOllamaDoesNotRequireAnApiKey() {
        ProviderClient.validateCredentials(ProviderConfig("ollama", "http://localhost:11434", "llama3.2", ""))
    }

    @Test
    fun authenticationErrorExplains401AndRedactsKey() {
        val key = "sk-test-verysecretkeyvalue"
        val message = ProviderClient.describeHttpError(
            401,
            """{"error":{"message":"Incorrect API key provided: $key"}}""",
            key
        )
        assertTrue(message.contains("HTTP 401"))
        assertTrue(message.contains("Incorrect API key"))
        assertFalse(message.contains(key))
        assertTrue(message.contains("[redacted]"))
    }
}
