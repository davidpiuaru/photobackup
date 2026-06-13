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
    var ratingStatus: RatingStatus?

    var isRating: Bool { ratingStatus?.isActive == true }

    private let api: APIService
    private let perPage = 50
    private var ratingPollTask: Task<Void, Never>?

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

    // MARK: - Rating AI

    func rate(sessionId: String) async {
        do {
            let _: EmptyResponse = try await api.post("api/sessions/\(sessionId)/rate")
            startRatingPolling(sessionId: sessionId)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func startRatingPolling(sessionId: String) {
        ratingPollTask?.cancel()
        ratingPollTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                if let s: RatingStatus = try? await self.api.get("api/rating/status") {
                    self.ratingStatus = s
                    if s.state != "rating" {
                        if s.state == "completed" {
                            // reincarca thumbnail-urile ca sa apara stelele
                            self.resetThumbnails()
                            await self.loadMoreThumbnails(for: sessionId)
                        }
                        break
                    }
                }
                try? await Task.sleep(nanoseconds: 1_500_000_000)
            }
        }
    }

    func stopRatingPolling() {
        ratingPollTask?.cancel()
        ratingPollTask = nil
    }
}
