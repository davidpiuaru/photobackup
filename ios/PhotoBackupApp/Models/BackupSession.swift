import Foundation

struct BackupSession: Codable, Identifiable, Hashable {
    let id: String
    let timestamp: String
    let label: String
    let filesCount: Int
    let bytesTotal: Int64
    let synced: Bool
    let incomplete: Bool
}

struct BackupSessionDetail: Codable {
    let id: String
    let timestamp: String
    let label: String
    let filesCount: Int
    let bytesTotal: Int64
    let synced: Bool
    let incomplete: Bool
    let files: [SessionFile]
}

struct SessionFile: Codable, Hashable {
    let path: String
    let size: Int64
    let sha256: String?
    let rating: Int?
}

struct ThumbnailEntry: Codable, Identifiable, Hashable {
    let filename: String
    let url: String
    let size: Int64
    let rating: Int?

    var id: String { filename }
}

struct RatingStatus: Codable, Equatable {
    let state: String
    let sessionId: String?
    let currentFile: String?
    let filesDone: Int
    let filesTotal: Int
    let method: String?
    let startedAt: String?

    var isActive: Bool { state == "rating" }
    var progress: Double {
        guard filesTotal > 0 else { return 0 }
        return min(1.0, Double(filesDone) / Double(filesTotal))
    }
}

struct PaginatedThumbnails: Codable {
    let page: Int
    let perPage: Int
    let total: Int
    let items: [ThumbnailEntry]
}
