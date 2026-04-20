import SwiftUI

extension Int64 {
    var formattedBytes: String {
        ByteCountFormatter.string(fromByteCount: self, countStyle: .file)
    }
}

extension Int {
    var formattedBytes: String {
        Int64(self).formattedBytes
    }

    var formattedDuration: String {
        let h = self / 3600
        let m = (self % 3600) / 60
        let s = self % 60
        if h > 0 {
            return String(format: "%dh %dm", h, m)
        } else if m > 0 {
            return String(format: "%dm %ds", m, s)
        } else {
            return "\(s)s"
        }
    }
}

extension Double {
    var mbpsString: String {
        String(format: "%.1f MB/s", self)
    }
}

extension Color {
    static let phAccent = Color.blue
    static let phSuccess = Color.green
    static let phWarning = Color.orange
    static let phError = Color.red
}

extension ShapeStyle where Self == Color {
    static var phAccent: Color { .phAccent }
    static var phSuccess: Color { .phSuccess }
    static var phWarning: Color { .phWarning }
    static var phError: Color { .phError }
}

extension View {
    @ViewBuilder
    func phCard() -> some View {
        self
            .padding()
            .background(Color(.secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 14))
    }
}

extension String {
    var prettyTimestamp: String {
        // "2026-04-19_14-30-00_label" -> "2026-04-19 14:30:00"
        let parts = self.split(separator: "_")
        guard parts.count >= 2 else { return self }
        let date = parts[0]
        let time = parts[1].replacingOccurrences(of: "-", with: ":")
        return "\(date) \(time)"
    }
}
