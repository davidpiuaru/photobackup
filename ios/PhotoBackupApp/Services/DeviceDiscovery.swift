import Foundation
import Network

@Observable
final class DeviceDiscovery {
    var discovered: [URL] = []
    var isScanning: Bool = false
    private var browser: NWBrowser?

    func start() {
        guard browser == nil else { return }
        isScanning = true
        let params = NWParameters()
        params.includePeerToPeer = false
        let b = NWBrowser(for: .bonjour(type: "_photobackup._tcp", domain: nil), using: params)
        b.browseResultsChangedHandler = { [weak self] results, _ in
            Task { @MainActor in
                self?.handleResults(results)
            }
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
        isScanning = false
    }

    private func handleResults(_ results: Set<NWBrowser.Result>) {
        var urls: [URL] = []
        for r in results {
            if case let .service(name, _, _, _) = r.endpoint {
                let host = name.replacingOccurrences(of: " ", with: "-")
                if let url = URL(string: "http://\(host).local:8080") {
                    urls.append(url)
                }
            }
        }
        self.discovered = urls
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
