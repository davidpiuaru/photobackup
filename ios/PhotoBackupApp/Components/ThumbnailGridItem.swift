import SwiftUI

struct ThumbnailGridItem: View {
    let url: URL

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
    }
}
