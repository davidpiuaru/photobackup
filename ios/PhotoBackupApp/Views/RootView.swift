import SwiftUI

struct RootView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        if appState.isConnected {
            ContentView()
        } else {
            ConnectView()
        }
    }
}
