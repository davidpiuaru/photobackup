import SwiftUI

struct WiFiConfigView: View {
    @Environment(APIService.self) private var api
    @State private var vm: WiFiViewModel?
    @State private var showingConnectSheet = false
    @State private var selectedNetwork: WiFiNetwork?
    @State private var showingTransition = false
    @State private var targetSSID: String = ""
    @State private var confirmDelete: String?

    var body: some View {
        NavigationStack {
            List {
                if let state = vm?.state {
                    Section {
                        HStack {
                            Image(systemName: state.isAP ? "wifi.router" : "wifi")
                                .foregroundStyle(state.isAP ? .phWarning : .phSuccess)
                            VStack(alignment: .leading) {
                                Text(state.isAP ? "Mod Hotspot" : "Conectat la \(state.clientSsid ?? "?")")
                                    .font(.headline)
                                if state.isAP {
                                    Text("SSID: \(state.apSsid) · IP: \(state.apIp)")
                                        .font(.caption).foregroundStyle(.secondary)
                                } else if let ip = state.clientIp {
                                    Text("IP: \(ip) · Internet: \(state.hasInternet ? "Da" : "Nu")")
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }

                if vm?.state?.isAP == true {
                    Section {
                        Label("Dispozitivul e în modul Hotspot fără internet. Conectează-l la o rețea pentru sync Google Drive.", systemImage: "info.circle")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }

                Section("Rețele disponibile") {
                    if let nets = vm?.networks, !nets.isEmpty {
                        ForEach(nets) { net in
                            Button {
                                selectedNetwork = net
                                showingConnectSheet = true
                            } label: {
                                HStack {
                                    Image(systemName: net.signalIcon).foregroundStyle(.tint)
                                    Text(net.ssid)
                                    if net.isSecured {
                                        Image(systemName: "lock.fill").font(.caption).foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    Text("\(net.signal)%").font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }
                    } else if vm?.isLoading == true {
                        ProgressView()
                    } else {
                        Text("Nicio rețea găsită").foregroundStyle(.secondary)
                    }
                }

                Section("Rețele salvate") {
                    if let saved = vm?.saved, !saved.isEmpty {
                        ForEach(saved, id: \.self) { ssid in
                            HStack {
                                Image(systemName: "bookmark.fill").foregroundStyle(.tint)
                                Text(ssid)
                                Spacer()
                                Button(role: .destructive) {
                                    confirmDelete = ssid
                                } label: {
                                    Image(systemName: "trash")
                                }
                                .buttonStyle(.plain)
                            }
                        }
                    } else {
                        Text("Nicio rețea salvată").foregroundStyle(.secondary)
                    }
                }

                Section {
                    if vm?.state?.isClient == true {
                        Button("Comută la Hotspot (AP)", systemImage: "wifi.router") {
                            Task { await vm?.startAP() }
                        }
                    }
                    Button("Rescan rețele", systemImage: "arrow.triangle.2.circlepath") {
                        Task { await vm?.rescan() }
                    }
                }
            }
            .navigationTitle("Wi-Fi")
            .refreshable { await vm?.refresh() }
            .alert("Șterge rețeaua \(confirmDelete ?? "")?", isPresented: Binding(
                get: { confirmDelete != nil },
                set: { if !$0 { confirmDelete = nil } }
            )) {
                Button("Șterge", role: .destructive) {
                    if let ssid = confirmDelete {
                        Task { await vm?.deleteSaved(ssid) }
                    }
                    confirmDelete = nil
                }
                Button("Anulează", role: .cancel) { confirmDelete = nil }
            }
        }
        .onAppear {
            if vm == nil { vm = WiFiViewModel(api: api) }
            Task { await vm?.refresh() }
        }
        .sheet(isPresented: $showingConnectSheet) {
            if let net = selectedNetwork, let vm {
                WiFiConnectSheet(network: net, vm: vm) { ssid in
                    targetSSID = ssid
                    showingConnectSheet = false
                    showingTransition = true
                }
            }
        }
        .fullScreenCover(isPresented: $showingTransition) {
            WiFiTransitionView(targetSSID: targetSSID) {
                showingTransition = false
                Task { await vm?.refresh() }
            }
        }
    }
}

struct WiFiConnectSheet: View {
    let network: WiFiNetwork
    @Bindable var vm: WiFiViewModel
    var onSubmit: (String) -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var password: String = ""
    @State private var showError: Bool = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    LabeledContent("Rețea", value: network.ssid)
                    LabeledContent("Semnal", value: "\(network.signal)%")
                    LabeledContent("Securitate", value: network.security.isEmpty ? "Deschis" : network.security)
                }
                if network.isSecured {
                    Section {
                        SecureField("Parolă", text: $password)
                            .textInputAutocapitalization(.never)
                    }
                }
                if let err = vm.errorMessage, showError {
                    Section {
                        Text(err).foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Conectare")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Anulează") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button {
                        Task {
                            // Trimitem comanda; indiferent de raspuns trecem la ecranul
                            // de tranzitie (in mod AP raspunsul poate sa nu ajunga, dar
                            // Pi-ul comuta oricum, iar tranzitia face polling de reconectare).
                            await vm.connect(ssid: network.ssid,
                                             password: network.isSecured ? password : nil)
                            onSubmit(network.ssid)
                        }
                    } label: {
                        if vm.connecting { ProgressView() } else { Text("Conectează") }
                    }
                    .disabled(vm.connecting || (network.isSecured && password.count < 8))
                }
            }
        }
    }
}
