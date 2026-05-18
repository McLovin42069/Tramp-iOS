import Foundation
import SwiftUI

enum Constants {
    static let appName = "Tramp"
    static let appTagline = "The Traveler's Jukebox"
    
    // MARK: - Jamendo
    static let jamendoBaseURL = "https://api.jamendo.com/v3.0"
    static let jamendoClientId = "0f030c28" // Public demo key, replace with yours
    
    // MARK: - Internet Archive
    static let archiveBaseURL = "https://archive.org/advancedsearch.php"
    
    // MARK: - Pixabay (user must add their own key)
    static let pixabayBaseURL = "https://pixabay.com/api"
    static let pixabayKey = "YOUR_PIXABAY_KEY"
    
    // MARK: - Free Music Archive
    static let fmaBaseURL = "https://freemusicarchive.org/api"
    
    // MARK: - Playback
    static let defaultCrossfadeSeconds: Double = 2.0
    static let radioPrefetchCount = 3
    static let maxCacheSizeMB = 500
    
    // MARK: - Gamification
    static let streakCheckInterval: TimeInterval = 86400 // 1 day
    static let milesPerMinute: Double = 1.0
    static let maxDailyMiles: Double = 240.0 // 4 hours
}

enum TrampColor {
    static let rustOrange = Color(hex: "C75B39")
    static let rustBrown = Color(hex: "8B4513")
    static let dirtyCream = Color(hex: "F5F5DC")
    static let agedYellow = Color(hex: "F4A460")
    static let darkMetal = Color(hex: "2C2C2C")
    static let chrome = Color(hex: "D4D4D4")
    static let neonGreen = Color(hex: "39FF14")
    static let retroAmber = Color(hex: "FFBF00")
    static let ledRed = Color(hex: "FF3300")
    static let ledGreen = Color(hex: "33FF00")
    static let deepTeal = Color(hex: "008080")
}

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (255, 0, 0, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}
