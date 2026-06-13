import SwiftUI

struct SettingsView: View {
    @Environment(AppState.self) private var appState
    @Environment(APIService.self) private var api
    @State private var baseURLText: String = ""
    @State private var refreshInterval: TimeInterval = 5
    @State private var notificationsEnabled: Bool = true
    @State private var apSSID: String = ""
    @State private var apPassword: String = ""
    @State private var apSavedMessage: String?
    @State private var apErrorMessage: String?
    @State private var currentHostname: String = ""
    @State private var apiToken: String = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Conexiune dispozitiv") {
                    TextField("Base URL", text: $baseURLText)
                        .keyboardType(.URL)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                    SecureField("Token API (opțional)", text: $apiToken)
                        .textInputAutocapitalization(.never)
                    Button("Salvează & verifică") {
                        Task { await applyBaseURL() }
                    }
                    Button("Deconectează", role: .destructive) {
                        appState.isConnected = false
                    }
                }

                Section("Refresh dashboard") {
                    Picker("Interval", selection: $refreshInterval) {
                        ForEach(Constants.refreshIntervals, id: \.self) { v in
                            Text("\(Int(v))s").tag(v)
                        }
                    }
                    .pickerStyle(.segmented)
                }

                Section("Notificări") {
                    Toggle("Notificări locale", isOn: $notificationsEnabled)
                }

                Section("Hotspot Pi (AP)") {
                    TextField("SSID hotspot", text: $apSSID)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                    SecureField("Parolă hotspot (min 8)", text: $apPassword)
                    Button("Aplică pe dispozitiv") {
                        Task { await saveAP() }
                    }
                    .disabled(apSSID.isEmpty || apPassword.count < 8)
                    if let msg = apSavedMessage { Text(msg).foregroundStyle(.green).font(.caption) }
                    if let err = apErrorMessage { Text(err).foregroundStyle(.red).font(.caption) }
                }

                Section("Despre") {
                    LabeledContent("Versiune app", value: "1.0")
                    LabeledContent("Hostname Pi", value: currentHostname.isEmpty ? "—" : currentHostname)
                }
            }
            .navigationTitle("Setări")
            .onAppear(perform: loadInitial)
            .onChange(of: refreshInterval) { _, new in
                appState.settings.refreshInterval = new
                appState.settings.save()
            }
            .onChange(of: notificationsEnabled) { _, new in
                appState.settings.notificationsEnabled = new
                appState.settings.save()
                if new {
                    NotificationService.shared.requestAuthorizationIfNeeded()
                }
            }
        }
    }

    private func loadInitial() {
        baseURLText = appState.settings.baseURL.absoluteString
        refreshInterval = appState.settings.refreshInterval
        notificationsEnabled = appState.settings.notificationsEnabled
        apiToken = appState.settings.apiToken
        Task {
            if let status: DeviceStatus = try? await api.get("api/status") {
                currentHostname = status.system.hostname
            }
            if let state: WiFiState = try? await api.get("api/wifi/current") {
                apSSID = state.apSsid
                // Parola AP nu mai e expusa de API (secret); ramane goala —
                // introdu una noua (min 8) doar daca vrei sa o schimbi.
            }
        }
    }

    private func applyBaseURL() async {
        guard let url = URL(string: baseURLText) else { return }
        let testApi = APIService(baseURL: url)
        if await testApi.ping(timeout: 3) {
            api.setBaseURL(url)
            api.token = apiToken
            appState.settings.baseURL = url
            appState.settings.apiToken = apiToken
            appState.settings.save()
        } else {
            apErrorMessage = "Nu răspunde la \(url.absoluteString)"
        }
    }

    private func saveAP() async {
        do {
            let req = APSettingsRequest(ssid: apSSID, password: apPassword)
            let _: EmptyResponse = try await api.post("api/wifi/ap-settings", body: req)
            apSavedMessage = "Aplicat. Se va activa la următoarea pornire AP."
            apErrorMessage = nil
        } catch {
            apErrorMessage = error.localizedDescription
            apSavedMessage = nil
        }
    }
}
