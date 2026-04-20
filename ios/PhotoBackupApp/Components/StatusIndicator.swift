import SwiftUI

struct StatusIndicator: View {
    enum Level { case ok, warning, error, inactive }
    let level: Level
    let text: String
    let systemImage: String?

    init(level: Level, text: String, systemImage: String? = nil) {
        self.level = level
        self.text = text
        self.systemImage = systemImage
    }

    private var color: Color {
        switch level {
        case .ok: .phSuccess
        case .warning: .phWarning
        case .error: .phError
        case .inactive: .secondary
        }
    }

    var body: some View {
        HStack(spacing: 6) {
            if let systemImage {
                Image(systemName: systemImage)
                    .foregroundStyle(color)
            } else {
                Circle()
                    .fill(color)
                    .frame(width: 10, height: 10)
            }
            Text(text)
                .font(.subheadline)
        }
    }
}
