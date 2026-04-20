import SwiftUI

struct ContentView: View {
    @Environment(AppState.self) private var appState

    var body: some View {
        TabView {
            DashboardView()
                .tabItem { Label("Dashboard", systemImage: "gauge.with.dots.needle.67percent") }

            BackupAndSyncView()
                .tabItem { Label("Backup", systemImage: "externaldrive.badge.timemachine") }

            GalleryView()
                .tabItem { Label("Galerie", systemImage: "photo.on.rectangle") }

            WiFiConfigView()
                .tabItem { Label("Wi-Fi", systemImage: "wifi") }

            SettingsView()
                .tabItem { Label("Setări", systemImage: "gear") }
        }
        .onAppear {
            NotificationService.shared.requestAuthorizationIfNeeded()
        }
    }
}
