import Foundation

struct WiFiNetwork: Codable, Identifiable, Hashable {
    let ssid: String
    let signal: Int
    let security: String
    let inUse: Bool

    var id: String { ssid }
    var isSecured: Bool { !security.isEmpty && security != "OPEN" && security != "--" }

    var signalIcon: String {
        switch signal {
        case 75...: "wifi"
        case 50..<75: "wifi"
        case 25..<50: "wifi.exclamationmark"
        default: "wifi.slash"
        }
    }
}

struct WiFiState: Codable, Equatable {
    let mode: String
    let apSsid: String
    let apIp: String
    let clientSsid: String?
    let clientIp: String?
    let hasInternet: Bool
    let lastChange: String?

    var isAP: Bool { mode == "ap" }
    var isClient: Bool { mode == "client" }
}

struct WiFiConnectRequest: Codable {
    let ssid: String
    let password: String?
}

struct APSettingsRequest: Codable {
    let ssid: String
    let password: String
}
