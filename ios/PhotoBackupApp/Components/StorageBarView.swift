import SwiftUI

struct StorageBarView: View {
    let used: Int64
    let total: Int64
    var tint: Color = .phAccent

    private var fraction: Double {
        guard total > 0 else { return 0 }
        return min(1.0, Double(used) / Double(total))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color(.systemGray5))
                    RoundedRectangle(cornerRadius: 6)
                        .fill(tint)
                        .frame(width: max(0, geo.size.width * fraction))
                }
            }
            .frame(height: 10)
            HStack {
                Text("\(used.formattedBytes) folosit")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                Text("\(total.formattedBytes) total")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}
