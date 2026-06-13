import Foundation
import Network

@Observable
@MainActor
final class DeviceDiscovery {
    var discovered: [URL] = []
    var isScanning: Bool = false
    private var browser: NWBrowser?
    private var resolvers: [NWConnection] = []
    private var seen: Set<String> = []

    func start() {
        guard browser == nil else { return }
        isScanning = true
        let params = NWParameters()
        params.includePeerToPeer = false
        let b = NWBrowser(for: .bonjour(type: "_photobackup._tcp", domain: nil), using: params)
        b.browseResultsChangedHandler = { [weak self] results, _ in
            Task { @MainActor in self?.handle(results) }
        }
        b.stateUpdateHandler = { [weak self] state in
            if case .failed = state {
                Task { @MainActor in self?.isScanning = false }
            }
        }
        b.start(queue: .main)
        browser = b
    }

    func stop() {
        browser?.cancel()
        browser = nil
        resolvers.forEach { $0.stateUpdateHandler = nil; $0.cancel() }
        resolvers.removeAll()
        seen.removeAll()
        isScanning = false
    }

    private func handle(_ results: Set<NWBrowser.Result>) {
        for result in results {
            // Rezolvam fiecare serviciu nou (numele instantei NU e un hostname valid;
            // trebuie sa obtinem host:port real din endpoint-ul rezolvat).
            let key = "\(result.endpoint)"
            guard !seen.contains(key) else { continue }
            seen.insert(key)
            resolve(result)
        }
    }

    private func resolve(_ result: NWBrowser.Result) {
        let conn = NWConnection(to: result.endpoint, using: .tcp)
        resolvers.append(conn)
        conn.stateUpdateHandler = { [weak self] state in
            switch state {
            case .ready:
                let url = DeviceDiscovery.url(from: conn.currentPath?.remoteEndpoint)
                Task { @MainActor in
                    if let url { self?.add(url) }
                    self?.finish(conn)
                }
            case .failed, .cancelled:
                Task { @MainActor in self?.finish(conn) }
            default:
                break
            }
        }
        conn.start(queue: .main)
    }

    private func add(_ url: URL) {
        if !discovered.contains(url) {
            discovered.append(url)
        }
    }

    /// Elibereaza conexiunea de rezolvare (rupe retain cycle-ul conn↔handler).
    private func finish(_ conn: NWConnection) {
        conn.stateUpdateHandler = nil
        conn.cancel()
        resolvers.removeAll { $0 === conn }
    }

    private nonisolated static func url(from endpoint: NWEndpoint?) -> URL? {
        guard let endpoint else { return nil }
        guard case let .hostPort(host, port) = endpoint else { return nil }
        let hostStr: String
        switch host {
        case .name(let name, _):
            hostStr = name
        case .ipv4(let addr):
            hostStr = "\(addr)"
        case .ipv6:
            // IPv6 (adesea link-local) e dificil in URL — ne bazam pe nume/IPv4 sau pe probe-ul .local
            return nil
        @unknown default:
            return nil
        }
        return URL(string: "http://\(hostStr):\(port.rawValue)")
    }

    /// Încearcă candidaturi comune (AP fallback, mDNS hostname) și returnează primul care răspunde.
    static func probe(candidates: [URL], timeout: TimeInterval = 2) async -> URL? {
        for url in candidates {
            let api = APIService(baseURL: url)
            if await api.ping(timeout: timeout) {
                return url
            }
        }
        return nil
    }
}
