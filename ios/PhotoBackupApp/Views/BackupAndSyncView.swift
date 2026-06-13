import SwiftUI

struct BackupAndSyncView: View {
    @Environment(APIService.self) private var api
    @Environment(AppState.self) private var appState
    @Environment(\.scenePhase) private var scenePhase
    @State private var vm: BackupViewModel?
    @State private var showCancelAlert = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 18) {
                    if let b = vm?.backup {
                        BackupProgressCard(state: b, onCancel: {
                            showCancelAlert = true
                        })
                    }
                    if let s = vm?.sync {
                        SyncProgressCard(
                            state: s,
                            onStart: { Task { await vm?.startSync() } },
                            onPause: { Task { await vm?.pauseSync() } },
                            onResume: { Task { await vm?.resumeSync() } },
                            onCancel: { Task { await vm?.cancelSync() } }
                        )
                    }
                    if vm?.backup == nil && vm?.sync == nil {
                        ProgressView().padding()
                    }
                }
                .padding()
            }
            .navigationTitle("Backup & Sync")
            .refreshable { await vm?.refresh() }
        }
        .onAppear {
            if vm == nil { vm = BackupViewModel(api: api) }
            vm?.startPolling(interval: max(2, appState.settings.refreshInterval / 2))
        }
        .onDisappear { vm?.stopPolling() }
        .onChange(of: scenePhase) { _, new in
            if new == .active {
                vm?.startPolling(interval: max(2, appState.settings.refreshInterval / 2))
            } else {
                vm?.stopPolling()
            }
        }
        .alert("Anulează backup-ul?", isPresented: $showCancelAlert) {
            Button("Anulează backup", role: .destructive) {
                Task { await vm?.cancelBackup() }
            }
            Button("Nu", role: .cancel) {}
        }
    }
}

struct BackupProgressCard: View {
    let state: BackupState
    var onCancel: () -> Void

    var body: some View {
        VStack(spacing: 14) {
            HStack {
                Label("Backup SD → SSD", systemImage: "externaldrive.badge.timemachine")
                    .font(.title3.bold())
                Spacer()
                StatusIndicator(level: level, text: state.stateLabel)
            }

            CircularProgressView(progress: state.progress, tint: tint)
                .frame(height: 220)

            VStack(spacing: 6) {
                if let current = state.currentFile {
                    Text(current)
                        .font(.caption.monospaced())
                        .lineLimit(1)
                        .truncationMode(.middle)
                }
                HStack {
                    Label("\(state.filesCopied)/\(state.filesTotal)", systemImage: "doc.on.doc")
                    Spacer()
                    Text("\(state.bytesCopied.formattedBytes) / \(state.bytesTotal.formattedBytes)")
                }
                .font(.subheadline)
                HStack {
                    Label(state.speedMbps.mbpsString, systemImage: "speedometer")
                    Spacer()
                    if state.etaSeconds > 0 {
                        Label("ETA: \(state.etaSeconds.formattedDuration)", systemImage: "clock")
                    }
                }
                .font(.subheadline)
                .foregroundStyle(.secondary)
            }

            if state.isActive {
                Button(role: .destructive) {
                    onCancel()
                } label: {
                    Label("Anulează backup", systemImage: "xmark.circle.fill")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
            }
        }
        .phCard()
    }

    private var tint: Color {
        switch state.state {
        case "error": .phError
        case "cancelled": .phWarning
        case "completed": .phSuccess
        default: .phAccent
        }
    }

    private var level: StatusIndicator.Level {
        switch state.state {
        case "copying": .ok
        case "completed": .ok
        case "error": .error
        case "cancelled": .warning
        default: .inactive
        }
    }
}

struct SyncProgressCard: View {
    let state: SyncState
    var onStart: () -> Void
    var onPause: () -> Void
    var onResume: () -> Void
    var onCancel: () -> Void

    var body: some View {
        VStack(spacing: 14) {
            HStack {
                Label("Sync Google Drive", systemImage: "icloud.and.arrow.up")
                    .font(.title3.bold())
                Spacer()
                StatusIndicator(level: level, text: state.stateLabel)
            }

            if state.isActive || state.state == "completed" {
                ProgressBarView(progress: state.progress, tint: .phSuccess)
                HStack {
                    Text("\(state.filesSynced)/\(state.filesTotal) fișiere")
                    Spacer()
                    Text("\(state.bytesSynced.formattedBytes) / \(state.bytesTotal.formattedBytes)")
                }
                .font(.subheadline)
                HStack {
                    Label(state.speedMbps.mbpsString, systemImage: "speedometer")
                    Spacer()
                    if state.etaSeconds > 0 {
                        Label("ETA: \(state.etaSeconds.formattedDuration)", systemImage: "clock")
                    }
                }
                .font(.subheadline)
                .foregroundStyle(.secondary)
                if let sess = state.currentSession {
                    Text("Sesiune: \(sess)")
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .truncationMode(.middle)
                }
            } else {
                Text("Nimic în curs.")
                    .foregroundStyle(.secondary)
            }

            HStack {
                if state.state == "syncing" {
                    Button("Pauză", systemImage: "pause.fill", action: onPause)
                        .buttonStyle(.bordered)
                    Button("Anulează", systemImage: "xmark.circle", role: .destructive, action: onCancel)
                        .buttonStyle(.bordered)
                } else if state.state == "paused" {
                    Button("Continuă", systemImage: "play.fill", action: onResume)
                        .buttonStyle(.borderedProminent)
                    Button("Anulează", systemImage: "xmark.circle", role: .destructive, action: onCancel)
                        .buttonStyle(.bordered)
                } else {
                    Button("Sync acum", systemImage: "arrow.triangle.2.circlepath", action: onStart)
                        .buttonStyle(.borderedProminent)
                }
                Spacer()
            }
        }
        .phCard()
    }

    private var level: StatusIndicator.Level {
        switch state.state {
        case "syncing", "completed": .ok
        case "error": .error
        case "paused", "waiting_internet": .warning
        default: .inactive
        }
    }
}
