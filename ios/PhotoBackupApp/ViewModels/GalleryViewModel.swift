import Foundation

@Observable
@MainActor
final class GalleryViewModel {
    var sessions: [BackupSession] = []
    var sessionDetail: BackupSessionDetail?
    var thumbnails: [ThumbnailEntry] = []
    var pagesLoaded: Int = 0
    var totalThumbnails: Int = 0
    var isLoadingSessions: Bool = false
    var isLoadingMore: Bool = false
    var errorMessage: String?

    private let api: APIService
    private let perPage = 50

    init(api: APIService) {
        self.api = api
    }

    func loadSessions() async {
        isLoadingSessions = true
        defer { isLoadingSessions = false }
        do {
            self.sessions = try await api.get("api/sessions")
            self.errorMessage = nil
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    func loadDetail(_ sessionId: String) async {
        do {
            self.sessionDetail = try await api.get("api/sessions/\(sessionId)")
            self.errorMessage = nil
        } catch {
            self.errorMessage = error.localizedDescription
        }
    }

    func resetThumbnails() {
        thumbnails = []
        pagesLoaded = 0
        totalThumbnails = 0
    }

    func loadMoreThumbnails(for sessionId: String) async {
        guard !isLoadingMore else { return }
        if pagesLoaded > 0 && thumbnails.count >= totalThumbnails { return }
        isLoadingMore = true
        defer { isLoadingMore = false }
        do {
            let page = pagesLoaded + 1
            let result: PaginatedThumbnails = try await api.get(
                "api/sessions/\(sessionId)/thumbnails",
                query: ["page": "\(page)", "per_page": "\(perPage)"]
            )
            thumbnails.append(contentsOf: result.items)
            pagesLoaded = page
            totalThumbnails = result.total
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
