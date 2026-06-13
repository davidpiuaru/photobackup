import SwiftUI

struct ThumbnailGridItem: View {
    let url: URL
    var rating: Int? = nil

    var body: some View {
        AsyncImage(url: url) { phase in
            switch phase {
            case .empty:
                Color(.systemGray5)
                    .overlay(ProgressView())
            case .success(let image):
                image.resizable().scaledToFill()
            case .failure:
                Color(.systemGray5)
                    .overlay(Image(systemName: "photo").foregroundStyle(.secondary))
            @unknown default:
                Color(.systemGray5)
            }
        }
        .aspectRatio(1, contentMode: .fill)
        .clipped()
        .overlay(alignment: .bottomLeading) {
            if let rating, rating > 0 {
                StarsView(rating: rating, size: 9)
                    .padding(.horizontal, 5)
                    .padding(.vertical, 3)
                    .background(.black.opacity(0.45), in: Capsule())
                    .padding(4)
            }
        }
    }
}

/// Afișaj reutilizabil de stele (1-5).
struct StarsView: View {
    let rating: Int
    var size: CGFloat = 12

    var body: some View {
        HStack(spacing: 1) {
            ForEach(1...5, id: \.self) { i in
                Image(systemName: i <= rating ? "star.fill" : "star")
                    .font(.system(size: size))
                    .foregroundStyle(i <= rating ? Color.yellow : Color.white.opacity(0.5))
            }
        }
    }
}
