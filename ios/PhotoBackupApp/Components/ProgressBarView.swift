import SwiftUI

struct ProgressBarView: View {
    let progress: Double
    var tint: Color = .phAccent

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color(.systemGray5))
                RoundedRectangle(cornerRadius: 8)
                    .fill(tint)
                    .frame(width: max(0, geo.size.width * progress))
                    .animation(.easeInOut(duration: 0.3), value: progress)
            }
        }
        .frame(height: 12)
    }
}

struct CircularProgressView: View {
    let progress: Double
    var tint: Color = .phAccent
    var lineWidth: CGFloat = 14

    var body: some View {
        ZStack {
            Circle()
                .stroke(Color(.systemGray5), lineWidth: lineWidth)
            Circle()
                .trim(from: 0, to: max(0.0001, progress))
                .stroke(tint, style: StrokeStyle(lineWidth: lineWidth, lineCap: .round))
                .rotationEffect(.degrees(-90))
                .animation(.easeInOut(duration: 0.4), value: progress)
            VStack(spacing: 4) {
                Text("\(Int(progress * 100))%")
                    .font(.system(size: 42, weight: .bold, design: .rounded))
                Text("progres")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }
}
