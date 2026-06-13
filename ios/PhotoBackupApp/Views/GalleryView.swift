import SwiftUI

struct GalleryView: View {
    @Environment(APIService.self) private var api
    @State private var vm: GalleryViewModel?

    var body: some View {
        NavigationStack {
            Group {
                if let vm {
                    if vm.isLoadingSessions && vm.sessions.isEmpty {
                        ProgressView().padding()
                    } else if vm.sessions.isEmpty {
                        ContentUnavailableView(
                            "Nicio sesiune de backup",
                            systemImage: "photo.on.rectangle.angled",
                            description: Text("Introdu un SD card în dispozitiv pentru a crea prima sesiune.")
                        )
                    } else {
                        List(vm.sessions) { session in
                            NavigationLink {
                                SessionDetailView(sessionId: session.id, sessionLabel: session.label)
                            } label: {
                                sessionRow(session)
                            }
                        }
                        .listStyle(.insetGrouped)
                    }
                }
            }
            .navigationTitle("Galerie")
            .refreshable { await vm?.loadSessions() }
        }
        .onAppear {
            if vm == nil { vm = GalleryViewModel(api: api) }
            Task { await vm?.loadSessions() }
        }
    }

    private func sessionRow(_ s: BackupSession) -> some View {
        HStack {
            Image(systemName: s.incomplete ? "exclamationmark.triangle.fill" : "folder.fill")
                .foregroundStyle(s.incomplete ? .phWarning : .phAccent)
            VStack(alignment: .leading, spacing: 4) {
                Text(s.label.isEmpty ? s.id : s.label)
                    .font(.headline)
                Text(s.timestamp.prettyTimestamp)
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
                HStack(spacing: 8) {
                    Text("\(s.filesCount) fișiere")
                    Text("·")
                    Text(s.bytesTotal.formattedBytes)
                }
                .font(.caption)
                .foregroundStyle(.secondary)
            }
            Spacer()
            if s.synced {
                Image(systemName: "checkmark.icloud.fill").foregroundStyle(.phSuccess)
            } else if s.incomplete {
                Image(systemName: "exclamationmark.icloud.fill").foregroundStyle(.phError)
            } else {
                Image(systemName: "clock.arrow.circlepath").foregroundStyle(.phWarning)
            }
        }
        .padding(.vertical, 4)
    }
}

struct SessionDetailView: View {
    let sessionId: String
    let sessionLabel: String
    @Environment(APIService.self) private var api
    @State private var vm: GalleryViewModel?
    @State private var selectedIndex: Int?

    private let columns = [
        GridItem(.flexible(), spacing: 2),
        GridItem(.flexible(), spacing: 2),
        GridItem(.flexible(), spacing: 2),
    ]

    var body: some View {
        ScrollView {
            if let vm {
                if let rs = vm.ratingStatus, rs.isActive {
                    VStack(spacing: 6) {
                        HStack {
                            Label("Evaluez cu AI…", systemImage: "sparkles")
                            Spacer()
                            Text("\(rs.filesDone)/\(rs.filesTotal)")
                        }
                        .font(.subheadline)
                        ProgressView(value: rs.progress)
                    }
                    .padding()
                }
                LazyVGrid(columns: columns, spacing: 2) {
                    ForEach(Array(vm.thumbnails.enumerated()), id: \.element.id) { idx, t in
                        Button {
                            selectedIndex = idx
                        } label: {
                            ThumbnailGridItem(
                                url: api.thumbnailURL(sessionId: sessionId, filename: t.filename),
                                rating: t.rating
                            )
                        }
                        .buttonStyle(.plain)
                        .onAppear {
                            if idx >= vm.thumbnails.count - 10 {
                                Task { await vm.loadMoreThumbnails(for: sessionId) }
                            }
                        }
                    }
                }
                if vm.isLoadingMore {
                    ProgressView().padding()
                }
                if vm.thumbnails.count >= vm.totalThumbnails && vm.totalThumbnails > 0 {
                    Text("\(vm.totalThumbnails) fișiere")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .padding()
                }
            } else {
                ProgressView().padding()
            }
        }
        .navigationTitle(sessionLabel.isEmpty ? sessionId : sessionLabel)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    if let vm { Task { await vm.rate(sessionId: sessionId) } }
                } label: {
                    if vm?.isRating == true {
                        ProgressView()
                    } else {
                        Label("Evaluează cu AI", systemImage: "sparkles")
                    }
                }
                .disabled(vm?.isRating == true)
            }
        }
        .onAppear {
            if vm == nil {
                vm = GalleryViewModel(api: api)
            }
            guard let vm, vm.thumbnails.isEmpty else { return }
            Task {
                await vm.loadDetail(sessionId)
                vm.resetThumbnails()
                await vm.loadMoreThumbnails(for: sessionId)
            }
        }
        .onDisappear { vm?.stopRatingPolling() }
        .fullScreenCover(item: Binding(
            get: { selectedIndex.map { IndexWrapper(value: $0) } },
            set: { selectedIndex = $0?.value }
        )) { wrapper in
            if let items = vm?.thumbnails {
                PhotoDetailView(
                    items: items,
                    sessionId: sessionId,
                    initialIndex: wrapper.value
                )
            }
        }
    }
}

private struct IndexWrapper: Identifiable {
    let value: Int
    var id: Int { value }
}
