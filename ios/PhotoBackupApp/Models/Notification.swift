import Foundation

struct DeviceNotification: Codable, Identifiable, Hashable {
    let id: Int
    let type: String
    let message: String
    let timestamp: String

    var sfSymbol: String {
        switch type {
        case "success": "checkmark.circle.fill"
        case "warning": "exclamationmark.triangle.fill"
        case "error": "xmark.octagon.fill"
        default: "info.circle.fill"
        }
    }
}
