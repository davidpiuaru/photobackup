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
}

struct ThumbnailEntry: Codable, Identifiable, Hashable {
    let filename: String
    let url: String
    let size: Int64

    var id: String { filename }
}

struct PaginatedThumbnails: Codable {
    let page: Int
    let perPage: Int
    let total: Int
    let items: [ThumbnailEntry]
}
