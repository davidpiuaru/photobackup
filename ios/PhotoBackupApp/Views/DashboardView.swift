import SwiftUI

struct DashboardView: View {
    @Environment(APIService.self) private var api
    @Environment(AppState.self) private var appState
    @State private var vm: DashboardViewModel?
    @Environment(\.scenePhase) private var scenePhase

    var body: some View {
        NavigationStack {
            ScrollView {
                if let vm, let status = vm.status {
                    VStack(spacing: 14) {
                        if status.wifi.isAP {
                            hotspotBanner
                        }
                        statusGrid(status)
                        if status.backup.isActive {
                            backupCard(status.backup)
                        }
                        if status.sync.isActive {
                            syncCard(status.sync)
                        }
                        ssdCard(status.ssd)
                        sdCardCard(status.sdcard)
                        systemCard(status.system)
                    }
                    .padding()
                } else if let errorMessage = vm?.errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "wifi.exclamationmark")
                            .font(.system(size: 48))
                            .foregroundStyle(.phError)
                        Text(errorMessage)
                            .multilineTextAlignment(.center)
                        Button("Deconectează") {
                            appState.isConnected = false
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding()
                } else {
                    ProgressView().padding(40)
                }
            }
            .navigationTitle("PhotoBackup")
            .refreshable { await vm?.refresh() }
        }
        .onAppear {
            if vm == nil {
                vm = DashboardViewModel(api: api)
            }
            vm?.startPolling(interval: appState.settings.refreshInterval)
        }
        .onDisappear {
            vm?.stopPolling()
        }
        .onChange(of: scenePhase) { _, new in
            if new == .active {
                vm?.startPolling(interval: appState.settings.refreshInterval)
            } else {
                vm?.stopPolling()
            }
        }
    }

    private var hotspotBanner: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("Modul Hotspot activ", systemImage: "wifi.router")
                .font(.headline)
            Text("Dispozitivul este în modul AP — conectează-l la o rețea Wi-Fi pentru acces la internet.")
                .font(.subheadline)
            NavigationLink("Configurează Wi-Fi →") {
                WiFiConfigView()
            }
            .font(.subheadline.weight(.semibold))
        }
        .padding()
        .background(Color.phWarning.opacity(0.15))
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color.phWarning, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func statusGrid(_ s: DeviceStatus) -> some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            statusCell(title: "Internet",
                       value: s.wifi.hasInternet ? "Conectat" : "Fără internet",
                       icon: s.wifi.hasInternet ? "globe" : "globe.badge.chevron.backward",
                       level: s.wifi.hasInternet ? .ok : .warning)
            statusCell(title: "SD Card",
                       value: s.sdcard.connected ? (s.sdcard.label ?? "conectat") : "deconectat",
                       icon: "sdcard",
                       level: s.sdcard.connected ? .ok : .inactive)
            statusCell(title: "Backup",
                       value: s.backup.stateLabel,
                       icon: "arrow.down.circle",
                       level: backupLevel(s.backup.state))
            statusCell(title: "Sync",
                       value: s.sync.stateLabel,
                       icon: "arrow.triangle.2.circlepath",
                       level: syncLevel(s.sync.state))
        }
    }

    private func statusCell(title: String, value: String, icon: String, level: StatusIndicator.Level) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: icon).font(.title3)
                Spacer()
                StatusIndicator(level: level, text: "")
            }
            Text(title).font(.caption).foregroundStyle(.secondary)
            Text(value).font(.headline).lineLimit(1)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .phCard()
    }

    private func backupCard(_ b: BackupState) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("Backup în curs", systemImage: "arrow.down.circle.fill")
                    .font(.headline)
                Spacer()
                Text(b.speedMbps.mbpsString).font(.caption).foregroundStyle(.secondary)
            }
            ProgressBarView(progress: b.progress, tint: .phAccent)
            HStack {
                Text("\(b.filesCopied)/\(b.filesTotal) fișiere")
                Spacer()
                Text("\(b.bytesCopied.formattedBytes) / \(b.bytesTotal.formattedBytes)")
            }
            .font(.caption)
            .foregroundStyle(.secondary)
            if let current = b.currentFile {
                Text(current)
                    .font(.caption.monospaced())
                    .lineLimit(1)
                    .truncationMode(.middle)
            }
        }
        .phCard()
    }

    private func syncCard(_ s: SyncState) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Label("Sync Drive", systemImage: "icloud.and.arrow.up.fill")
                    .font(.headline)
                Spacer()
                Text(s.speedMbps.mbpsString).font(.caption).foregroundStyle(.secondary)
            }
            ProgressBarView(progress: s.progress, tint: .phSuccess)
            HStack {
                Text("\(s.filesSynced)/\(s.filesTotal) fișiere")
                Spacer()
                Text("\(s.bytesSynced.formattedBytes) / \(s.bytesTotal.formattedBytes)")
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
        .phCard()
    }

    private func ssdCard(_ d: DiskInfo) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("SSD", systemImage: "externaldrive.fill")
                .font(.headline)
            if d.mounted {
                StorageBarView(used: d.usedBytes, total: d.totalBytes, tint: .phAccent)
            } else {
                StatusIndicator(level: .error, text: "SSD nemontat")
            }
        }
        .phCard()
    }

    private func sdCardCard(_ sd: SDCardInfo) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("SD Card", systemImage: "sdcard.fill")
                .font(.headline)
            if sd.connected {
                HStack {
                    Text(sd.label ?? "card")
                        .font(.subheadline.weight(.semibold))
                    Spacer()
                    if let fs = sd.filesystem { Text(fs).font(.caption).foregroundStyle(.secondary) }
                }
                if sd.sizeBytes > 0 {
                    StorageBarView(used: sd.usedBytes, total: sd.sizeBytes, tint: .phWarning)
                }
            } else {
                Text("Niciun SD card detectat").foregroundStyle(.secondary)
            }
        }
        .phCard()
    }

    private func systemCard(_ s: SystemInfo) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Dispozitiv", systemImage: "cpu.fill")
                .font(.headline)
            HStack {
                Text("Uptime")
                Spacer()
                Text(s.uptimeSeconds.formattedDuration).foregroundStyle(.secondary)
            }
            .font(.subheadline)
            if let t = s.cpuTempC {
                HStack {
                    Text("CPU Temp")
                    Spacer()
                    Text(String(format: "%.1f °C", t))
                        .foregroundStyle(t > 70 ? .phError : t > 55 ? .phWarning : .secondary)
                }
                .font(.subheadline)
            }
            HStack {
                Text("Hostname")
                Spacer()
                Text(s.hostname).foregroundStyle(.secondary)
            }
            .font(.subheadline)
        }
        .phCard()
    }

    private func backupLevel(_ s: String) -> StatusIndicator.Level {
        switch s {
        case "copying": .ok
        case "completed": .ok
        case "error": .error
        case "cancelled": .warning
        default: .inactive
        }
    }

    private func syncLevel(_ s: String) -> StatusIndicator.Level {
        switch s {
        case "syncing", "completed": .ok
        case "error": .error
        case "paused", "waiting_internet": .warning
        default: .inactive
        }
    }
}
