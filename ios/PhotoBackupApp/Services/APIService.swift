import Foundation

@Observable
final class APIService {
    var baseURL: URL
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder

    init(baseURL: URL) {
        self.baseURL = baseURL
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 10
        config.timeoutIntervalForResource = 30
        config.waitsForConnectivity = false
        self.session = URLSession(configuration: config)

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        self.decoder = decoder
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        self.encoder = encoder
    }

    func setBaseURL(_ url: URL) {
        self.baseURL = url
    }

    // MARK: - Generic

    func get<T: Decodable>(_ path: String, query: [String: String] = [:]) async throws -> T {
        var comps = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: false)!
        if !query.isEmpty {
            comps.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        var req = URLRequest(url: comps.url!)
        req.httpMethod = "GET"
        return try await perform(req)
    }

    @discardableResult
    func post<T: Decodable>(_ path: String, body: Encodable? = nil) async throws -> T {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let body {
            req.httpBody = try encoder.encode(AnyEncodable(body))
        }
        return try await perform(req)
    }

    @discardableResult
    func delete<T: Decodable>(_ path: String) async throws -> T {
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = "DELETE"
        return try await perform(req)
    }

    func thumbnailURL(sessionId: String, filename: String) -> URL {
        // encoding: path param :path in FastAPI permite slash-uri
        let encoded = filename.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? filename
        return baseURL.appendingPathComponent("api/thumbnails/\(sessionId)/\(encoded)")
    }

    // MARK: - Helpers

    private func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw APIError.invalidResponse }
        guard (200..<300).contains(http.statusCode) else {
            let msg = String(data: data, encoding: .utf8) ?? "status \(http.statusCode)"
            throw APIError.httpError(status: http.statusCode, message: msg)
        }
        if T.self == EmptyResponse.self {
            return EmptyResponse() as! T
        }
        if data.isEmpty, let empty = EmptyResponse() as? T {
            return empty
        }
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingError(error)
        }
    }

    /// Ping cu timeout custom — folosit pentru discovery/reconectare
    func ping(timeout: TimeInterval = 2.0) async -> Bool {
        var req = URLRequest(url: baseURL.appendingPathComponent("api/ping"))
        req.timeoutInterval = timeout
        do {
            let (_, resp) = try await session.data(for: req)
            return (resp as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }
}

enum APIError: LocalizedError {
    case invalidResponse
    case httpError(status: Int, message: String)
    case decodingError(Error)
    case urlError(URLError)

    var errorDescription: String? {
        switch self {
        case .invalidResponse: "Răspuns invalid de la server"
        case .httpError(let status, let msg): "HTTP \(status): \(msg)"
        case .decodingError(let err): "Decodare JSON eșuată: \(err.localizedDescription)"
        case .urlError(let err): err.localizedDescription
        }
    }
}

struct EmptyResponse: Codable {}

// Helper pentru a encoda orice Encodable prin encoder-ul nostru
private struct AnyEncodable: Encodable {
    let value: Encodable
    init(_ value: Encodable) { self.value = value }
    func encode(to encoder: Encoder) throws { try value.encode(to: encoder) }
}
