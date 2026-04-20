import Foundation

@Observable
@MainActor
final class BackupViewModel {
    var backup: BackupState?
    var sync: SyncState?
    var errorMessage: String?

    private let api: APIService
    private var pollTask: Task<Void, Never>?

    init(api: APIService) {
        self.api = api
    }

    func startPolling(interval: TimeInterval) {
        stopPolling()
        pollTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                await self.refresh()
                try? await Task.sleep(nanoseconds: UInt64(interval * 1_000_000_000))
            }
        }
    }

    func stopPolling() {
        pollTask?.cancel()
        pollTask = nil
    }

    func refresh() async {
        do {
            async let b: BackupState = api.get("api/backup/status")
            async let s: SyncState = api.get("api/sync/status")
            self.backup = try await b
            self.sync = try await s
            self.errorMessage = nil
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    func cancelBackup() async {
        do { let _: EmptyResponse = try await api.post("api/backup/cancel") } catch {
            errorMessage = error.localizedDescription
        }
    }

    func startSync() async {
        do { let _: EmptyResponse = try await api.post("api/sync/start") } catch {
            errorMessage = error.localizedDescription
        }
    }

    func pauseSync() async {
        do { let _: EmptyResponse = try await api.post("api/sync/pause") } catch {
            errorMessage = error.localizedDescription
        }
    }

    func resumeSync() async {
        do { let _: EmptyResponse = try await api.post("api/sync/resume") } catch {
            errorMessage = error.localizedDescription
        }
    }

    func cancelSync() async {
        do { let _: EmptyResponse = try await api.post("api/sync/cancel") } catch {
            errorMessage = error.localizedDescription
        }
    }
}
