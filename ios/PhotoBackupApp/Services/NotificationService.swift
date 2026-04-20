import Foundation
import UserNotifications

final class NotificationService {
    static let shared = NotificationService()

    private var lastSeenId: Int {
        get { UserDefaults.standard.integer(forKey: "lastSeenNotificationId") }
        set { UserDefaults.standard.set(newValue, forKey: "lastSeenNotificationId") }
    }

    func requestAuthorizationIfNeeded() {
        UNUserNotificationCenter.current().getNotificationSettings { settings in
            guard settings.authorizationStatus == .notDetermined else { return }
            UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { _, _ in }
        }
    }

    func processIncoming(_ notifications: [DeviceNotification], enabled: Bool) {
        guard enabled else {
            if let last = notifications.last?.id { lastSeenId = max(lastSeenId, last) }
            return
        }
        let new = notifications.filter { $0.id > lastSeenId }
        guard !new.isEmpty else { return }
        for n in new {
            present(notification: n)
        }
        if let maxId = notifications.map(\.id).max() {
            lastSeenId = maxId
        }
    }

    private func present(notification: DeviceNotification) {
        let content = UNMutableNotificationContent()
        content.title = title(for: notification.type)
        content.body = notification.message
        content.sound = .default
        let req = UNNotificationRequest(
            identifier: "photobackup-\(notification.id)",
            content: content,
            trigger: nil
        )
        UNUserNotificationCenter.current().add(req)
    }

    private func title(for type: String) -> String {
        switch type {
        case "success": "PhotoBackup — OK"
        case "warning": "PhotoBackup — atenție"
        case "error": "PhotoBackup — eroare"
        default: "PhotoBackup"
        }
    }
}
