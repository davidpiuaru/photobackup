import SwiftUI

struct ConnectView: View {
    @Environment(AppState.self) private var appState
    @State private var discovery = DeviceDiscovery()
    @State private var manualIP: String = ""
    @State private var isProbing: Bool = false
    @State private var statusMessage: String = "Caut dispozitivul PhotoBackup..."

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()

                Image(systemName: "externaldrive.connected.to.line.below")
                    .font(.system(size: 72))
                    .foregroundStyle(.tint)

                Text("PhotoBackup")
                    .font(.largeTitle.bold())

                Text(statusMessage)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)

                if isProbing {
                    ProgressView()
                }

                if !discovery.discovered.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Găsit pe rețea:")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        ForEach(discovery.discovered, id: \.self) { url in
                            Button {
                                connect(to: url)
                            } label: {
                                HStack {
                                    Image(systemName: "bonjour")
                                    Text(url.absoluteString)
                                    Spacer()
                                    Image(systemName: "chevron.right")
                                        .foregroundStyle(.secondary)
                                }
                                .padding()
                                .background(Color(.secondarySystemGroupedBackground))
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.horizontal)
                }

                Spacer()

                VStack(spacing: 12) {
                    Text("sau conectare manuală:")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    HStack {
                        TextField("IP sau hostname", text: $manualIP)
                            .textFieldStyle(.roundedBorder)
                            .keyboardType(.URL)
                            .autocorrectionDisabled()
                            .textInputAutocapitalization(.never)
                        Button("Conectează") {
                            connectManual()
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(manualIP.isEmpty)
                    }
                    .padding(.horizontal)
                }

                Button {
                    Task { await autoProbe() }
                } label: {
                    Label("Scan din nou", systemImage: "arrow.triangle.2.circlepath")
                }
                .buttonStyle(.bordered)

                Spacer(minLength: 24)
            }
            .navigationBarHidden(true)
        }
        .onAppear {
            discovery.start()
            Task { await autoProbe() }
        }
        .onDisappear {
            discovery.stop()
        }
    }

    private func autoProbe() async {
        isProbing = true
        defer { isProbing = false }
        statusMessage = "Încerc rețeaua locală..."
        let candidates: [URL] = [
            Constants.defaultBaseURL,              // hotspot
            appState.settings.baseURL,             // ultimul IP
            Constants.mDNSBaseURL,                 // photobackup.local
        ]
        if let url = await DeviceDiscovery.probe(candidates: candidates) {
            connect(to: url)
        } else {
            statusMessage = "Nu găsesc dispozitivul. Conectează iPhone-ul la rețeaua Pi-ului sau la hotspotul `PhotoBackup-AP`."
        }
    }

    private func connectManual() {
        var s = manualIP.trimmingCharacters(in: .whitespaces)
        if !s.hasPrefix("http") {
            s = "http://\(s)"
        }
        if !s.contains(":\(Constants.defaultPort)") && URL(string: s)?.port == nil {
            s += ":\(Constants.defaultPort)"
        }
        guard let url = URL(string: s) else { return }
        Task {
            let api = APIService(baseURL: url)
            if await api.ping(timeout: 3) {
                connect(to: url)
            } else {
                statusMessage = "Nu răspunde la \(url.absoluteString)"
            }
        }
    }

    private func connect(to url: URL) {
        appState.api.setBaseURL(url)
        appState.settings.baseURL = url
        appState.settings.save()
        appState.isConnected = true
    }
}
