import Foundation

struct DeviceStatus: Codable, Equatable {
    let backup: BackupState
    let sync: SyncState
    let sdcard: SDCardInfo
    let ssd: DiskInfo
    let wifi: WiFiState
    let system: SystemInfo
}

struct BackupState: Codable, Equatable {
    let state: String
    let currentFile: String?
    let filesCopied: Int
    let filesTotal: Int
    let bytesCopied: Int64
    let bytesTotal: Int64
    let speedMbps: Double
    let etaSeconds: Int
    let startedAt: String?
    let sessionId: String?

    var progress: Double {
        guard bytesTotal > 0 else { return 0 }
        return min(1.0, Double(bytesCopied) / Double(bytesTotal))
    }

    var isActive: Bool { state == "copying" }
}

struct SyncState: Codable, Equatable {
    let state: String
    let filesSynced: Int
    let filesTotal: Int
    let bytesSynced: Int64
    let bytesTotal: Int64
    let speedMbps: Double
    let etaSeconds: Int
    let currentSession: String?

    var progress: Double {
        guard bytesTotal > 0 else { return 0 }
        return min(1.0, Double(bytesSynced) / Double(bytesTotal))
    }

    var isActive: Bool { state == "syncing" || state == "paused" }
}

struct SDCardInfo: Codable, Equatable {
    let connected: Bool
    let label: String?
    let filesystem: String?
    let sizeBytes: Int64
    let usedBytes: Int64
    let mountPoint: String?
}

struct DiskInfo: Codable, Equatable {
    let totalBytes: Int64
    let usedBytes: Int64
    let freeBytes: Int64
    let mounted: Bool
}

struct SystemInfo: Codable, Equatable {
    let uptimeSeconds: Int
    let cpuTempC: Double?
    let hostname: String
}
