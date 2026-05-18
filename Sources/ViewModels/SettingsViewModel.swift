import Foundation
import SwiftUI

@Observable
final class SettingsViewModel {
    var stats = UserStats.default
    var currentSkin: Skin = SkinManager.shared.currentSkin
    var notificationsEnabled = true
    var backgroundPlaybackEnabled = true
    var crossfadeEnabled = true
    var crossfadeDuration: Double = 2.0
    var autoCacheEnabled = true
    var cacheSizeMB: Double = 0
    var showDonationReminder = false
    
    private let statsManager = StatsManager.shared
    private let skinManager = SkinManager.shared
    
    init() {
        stats = statsManager.currentStats
        loadSettings()
    }
    
    func refreshStats() {
        stats = statsManager.currentStats
    }
    
    func resetStats() {
        statsManager.resetStats()
        stats = UserStats.default
    }
    
    func clearCache() {
        let cacheDir = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first?
            .appendingPathComponent("Tramp/AudioCache", isDirectory: true)
        if let dir = cacheDir {
            try? FileManager.default.removeItem(at: dir)
            try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        }
        cacheSizeMB = 0
    }
    
    func calculateCacheSize() {
        let cacheDir = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first?
            .appendingPathComponent("Tramp/AudioCache", isDirectory: true)
        guard let dir = cacheDir else { return }
        
        var size: UInt64 = 0
        if let files = try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: [.fileSizeKey]) {
            for file in files {
                if let attrs = try? FileManager.default.attributesOfItem(atPath: file.path),
                   let fileSize = attrs[.size] as? UInt64 {
                    size += fileSize
                }
            }
        }
        cacheSizeMB = Double(size) / (1024 * 1024)
    }
    
    var formattedTotalTime: String {
        let hours = Int(stats.totalListeningMinutes / 60)
        let minutes = Int(stats.totalListeningMinutes) % 60
        if hours > 0 {
            return "\(hours)h \(minutes)m"
        }
        return "\(minutes)m"
    }
    
    var formattedMiles: String {
        String(format: "%.1f", stats.trampMiles)
    }
    
    var nextLevelProgress: Double {
        stats.progressToNextLevel
    }
    
    var nextLevelXP: Double {
        Double(stats.level) * 1000
    }
    
    private func loadSettings() {
        let defaults = UserDefaults.standard
        notificationsEnabled = defaults.bool(forKey: "tramp.notifications", defaultValue: true)
        backgroundPlaybackEnabled = defaults.bool(forKey: "tramp.backgroundPlayback", defaultValue: true)
        crossfadeEnabled = defaults.bool(forKey: "tramp.crossfade", defaultValue: true)
        crossfadeDuration = defaults.double(forKey: "tramp.crossfadeDuration")
        if crossfadeDuration == 0 { crossfadeDuration = 2.0 }
        autoCacheEnabled = defaults.bool(forKey: "tramp.autoCache", defaultValue: true)
    }
    
    func saveSettings() {
        let defaults = UserDefaults.standard
        defaults.set(notificationsEnabled, forKey: "tramp.notifications")
        defaults.set(backgroundPlaybackEnabled, forKey: "tramp.backgroundPlayback")
        defaults.set(crossfadeEnabled, forKey: "tramp.crossfade")
        defaults.set(crossfadeDuration, forKey: "tramp.crossfadeDuration")
        defaults.set(autoCacheEnabled, forKey: "tramp.autoCache")
    }
}

extension UserDefaults {
    func bool(forKey key: String, defaultValue: Bool) -> Bool {
        if object(forKey: key) == nil {
            return defaultValue
        }
        return bool(forKey: key)
    }
}
