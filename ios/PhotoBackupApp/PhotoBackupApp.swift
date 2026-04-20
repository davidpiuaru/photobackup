import SwiftUI

@main
struct PhotoBackupApp: App {
    @State private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(appState)
                .environment(appState.api)
                .preferredColorScheme(nil)
        }
    }
}

@Observable
final class AppState {
    var api: APIService
    var settings: AppSettings
    var isConnected: Bool = false

    init() {
        let settings = AppSettings.load()
        self.settings = settings
        self.api = APIService(baseURL: settings.baseURL)
    }
}
