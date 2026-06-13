import Foundation

enum Constants {
    /// IP-ul fix al Pi-ului în mod hotspot.
    static let apIP = "10.42.0.1"
    static let defaultPort = 8080
    static let defaultBaseURL = URL(string: "http://\(apIP):\(defaultPort)")!
    static let mDNSBaseURL = URL(string: "http://photobackup.local:\(defaultPort)")!

    static let refreshIntervals: [TimeInterval] = [5, 10, 30]
}

struct AppSettings: Codable, Equatable {
    var baseURL: URL
    var refreshInterval: TimeInterval
    var notificationsEnabled: Bool
    /// Token API optional (gol = auth dezactivat pe Pi).
    var apiToken: String = ""

    static let defaults = AppSettings(
        baseURL: Constants.defaultBaseURL,
        refreshInterval: 5,
        notificationsEnabled: true
    )

    static func load() -> AppSettings {
        let d = UserDefaults.standard
        let token = d.string(forKey: "apiToken") ?? ""
        guard
            let urlStr = d.string(forKey: "baseURL"),
            let url = URL(string: urlStr)
        else {
            return AppSettings(baseURL: Constants.defaultBaseURL, refreshInterval: 5,
                               notificationsEnabled: true, apiToken: token)
        }
        return AppSettings(
            baseURL: url,
            refreshInterval: d.double(forKey: "refreshInterval") > 0 ? d.double(forKey: "refreshInterval") : 5,
            notificationsEnabled: (d.object(forKey: "notificationsEnabled") as? Bool) ?? true,
            apiToken: token
        )
    }

    func save() {
        let d = UserDefaults.standard
        d.set(baseURL.absoluteString, forKey: "baseURL")
        d.set(refreshInterval, forKey: "refreshInterval")
        d.set(notificationsEnabled, forKey: "notificationsEnabled")
        d.set(apiToken, forKey: "apiToken")
    }
}
