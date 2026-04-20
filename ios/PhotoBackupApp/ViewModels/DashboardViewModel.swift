import Foundation

@Observable
@MainActor
final class DashboardViewModel {
    var status: DeviceStatus?
    var errorMessage: String?
    var isLoading: Bool = false
    var notifications: [DeviceNotification] = []

    private let api: APIService
    private var pollTask: Task<Void, Never>?
    private var lastNotificationId: Int = 0

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
            let status: DeviceStatus = try await api.get("api/status")
            self.status = status
            self.errorMessage = nil
            // Fetch notificări (delta)
            let notifs: [DeviceNotification] = try await api.get(
                "api/notifications",
                query: ["since_id": "\(lastNotificationId)"]
            )
            if !notifs.isEmpty {
                self.notifications.append(contentsOf: notifs)
                self.lastNotificationId = notifs.map(\.id).max() ?? lastNotificationId
                let settings = AppSettings.load()
                NotificationService.shared.processIncoming(notifs, enabled: settings.notificationsEnabled)
            }
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }
}
