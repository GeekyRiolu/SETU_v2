package ai.setu.sdk

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * SETU mobile SDK (Android) — stub.
 *
 * Same contract as every SETU front-end: one entry point, `translate(text,
 * srcLang, tgtLang)`, backed by the shared InferenceEngine. Two backends are
 * planned; both keep user text on-device:
 *
 *  1. On-device ONNX Runtime Mobile loading the quantised student (the real
 *     offline path — see setu.inference.onnx_engine). TODO: wire ORT-Mobile.
 *  2. Local REST engine on the same device/host (this stub), useful for dev.
 *
 * No user text leaves the device: the default baseUrl is loopback.
 */
data class TranslationResult(
    val translatedText: String,
    val srcLang: String,
    val tgtLang: String,
    val latencyMs: Double? = null,
)

class SetuTranslator(private val baseUrl: String = "http://127.0.0.1:8000") {

    /** Translate [text] from [srcLang] to [tgtLang] (ISO codes, e.g. "hi","en"). */
    fun translate(text: String, srcLang: String, tgtLang: String): TranslationResult {
        // TODO(offline): replace with on-device ONNX Runtime Mobile inference.
        val payload = JSONObject()
            .put("source_lang", srcLang)
            .put("target_lang", tgtLang)
            .put("text", text)
            .toString()

        val conn = (URL("$baseUrl/translate").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        conn.outputStream.use { it.write(payload.toByteArray()) }
        val body = conn.inputStream.bufferedReader().use { it.readText() }
        val json = JSONObject(body)
        return TranslationResult(
            translatedText = json.getString("translated_text"),
            srcLang = json.getString("src_lang"),
            tgtLang = json.getString("tgt_lang"),
            latencyMs = if (json.isNull("latency_ms")) null else json.getDouble("latency_ms"),
        )
    }
}
