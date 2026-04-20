import Foundation

@Observable
@MainActor
final class WiFiViewModel {
    var state: WiFiState?
    var networks: [WiFiNetwork] = []
    var saved: [String] = []
    var isLoading: Bool = false
    var errorMessage: String?
    var connecting: Bool = false

    private let api: APIService

    init(api: APIService) {
        self.api = api
    }

    func refresh() async {
        isLoading = true
        defer { isLoading = false }
        do {
            async let st: WiFiState = api.get("api/wifi/current")
            async let nets: [WiFiNetwork] = api.get("api/wifi/networks")
            async let sv: [String] = api.get("api/wifi/saved")
            self.state = try await st
            self.networks = try await nets
            self.saved = try await sv
            self.errorMessage = nil
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    func connect(ssid: String, password: String?) async -> Bool {
        connecting = true
        defer { connecting = false }
        do {
            let req = WiFiConnectRequest(ssid: ssid, password: password)
            let _: EmptyResponse = try await api.post("api/wifi/connect", body: req)
            return true
        } catch {
            self.errorMessage = error.localizedDescription
            return false
        }
    }

    func startAP() async {
        do {
            let _: EmptyResponse = try await api.post("api/wifi/start-ap")
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    func disconnect() async {
        do {
            let _: EmptyResponse = try await api.post("api/wifi/disconnect")
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    func deleteSaved(_ ssid: String) async {
        do {
            let _: EmptyResponse = try await api.delete("api/wifi/saved/\(ssid)")
            await refresh()
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    func updateAP(ssid: String, password: String) async -> Bool {
        do {
            let _: EmptyResponse = try await api.post(
                "api/wifi/ap-settings",
                body: APSettingsRequest(ssid: ssid, password: password)
            )
            return true
        } catch {
            self.errorMessage = error.localizedDescription
            return false
        }
    }

    func rescan() async {
        do {
            let _: EmptyResponse = try await api.post("api/wifi/rescan")
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            await refresh()
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }
}
