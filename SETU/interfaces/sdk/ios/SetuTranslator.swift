import Foundation

/// SETU mobile SDK (iOS) — stub.
///
/// Same contract as every SETU front-end: one entry point,
/// `translate(text:srcLang:tgtLang:)`, backed by the shared InferenceEngine.
/// Two backends are planned; both keep user text on-device:
///  1. On-device ONNX Runtime (the real offline path). TODO: wire ORT.
///  2. Local REST engine on loopback (this stub), useful for development.
///
/// No user text leaves the device: the default baseURL is loopback.
public struct TranslationResult: Codable {
    public let translatedText: String
    public let srcLang: String
    public let tgtLang: String
    public let latencyMs: Double?

    enum CodingKeys: String, CodingKey {
        case translatedText = "translated_text"
        case srcLang = "src_lang"
        case tgtLang = "tgt_lang"
        case latencyMs = "latency_ms"
    }
}

public final class SetuTranslator {
    private let baseURL: URL

    public init(baseURL: URL = URL(string: "http://127.0.0.1:8000")!) {
        self.baseURL = baseURL
    }

    /// Translate `text` from `srcLang` to `tgtLang` (ISO codes, e.g. "hi", "en").
    public func translate(
        text: String, srcLang: String, tgtLang: String,
        completion: @escaping (Result<TranslationResult, Error>) -> Void
    ) {
        // TODO(offline): replace with on-device ONNX Runtime inference.
        var request = URLRequest(url: baseURL.appendingPathComponent("translate"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: [
            "source_lang": srcLang, "target_lang": tgtLang, "text": text,
        ])

        URLSession.shared.dataTask(with: request) { data, _, error in
            if let error = error { return completion(.failure(error)) }
            guard let data = data else {
                return completion(.failure(URLError(.badServerResponse)))
            }
            do {
                let result = try JSONDecoder().decode(TranslationResult.self, from: data)
                completion(.success(result))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
}
