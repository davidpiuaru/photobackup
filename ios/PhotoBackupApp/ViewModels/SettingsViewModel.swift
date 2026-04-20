import Foundation

@Observable
@MainActor
final class SettingsViewModel {
    var settings: AppSettings
    var apSSID: String = ""
    var apPassword: String = ""
    var errorMessage: String?
    var successMessage: String?

    init(settings: AppSettings) {
        self.settings = settings
    }

    func save() {
        settings.save()
    }
}
