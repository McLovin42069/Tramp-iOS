import Foundation
import CoreData

@Observable
final class StatsManager {
    static let shared = StatsManager()
    
    var currentStats = UserStats.default
    
    private let defaults = UserDefaults.standard
    private let statsKey = "tramp.userStats"
    private let persistence = PersistenceController.shared
    
    private init() {
        loadStats()
    }
    
    func loadStats() {
        if let data = defaults.data(forKey: statsKey),
           let stats = try? JSONDecoder().decode(UserStats.self, from: data) {
            currentStats = stats
        } else {
            loadFromCoreData()
        }
    }
    
    func saveStats() {
        if let data = try? JSONEncoder().encode(currentStats) {
            defaults.set(data, forKey: statsKey)
        }
        saveToCoreData()
    }
    
    func recordPlay(track: Track) {
        currentStats.totalTracksPlayed += 1
        currentStats.checkStreak()
        if let genre = track.genre {
            currentStats.favoriteGenres[genre, default: 0] += 1
        }
        saveStats()
    }
    
    func addListeningTime(_ minutes: Double) {
        currentStats.addListeningMinutes(minutes)
        saveStats()
    }
    
    func recordSearch() {
        currentStats.totalSearches += 1
        saveStats()
    }
    
    func recordRadioSession() {
        currentStats.radioSessions += 1
        saveStats()
    }
    
    func recordPlaylistCreated() {
        currentStats.playlistsCreated += 1
        saveStats()
    }
    
    func recordSkinChange() {
        currentStats.skinChanges += 1
        saveStats()
    }
    
    func completeOnboarding() {
        currentStats.onboardingCompleted = true
        saveStats()
    }
    
    func resetStats() {
        currentStats = UserStats.default
        saveStats()
    }
    
    private func loadFromCoreData() {
        let request = NSFetchRequest<UserStatsEntity>(entityName: "UserStatsEntity")
        if let entity = (try? persistence.container.viewContext.fetch(request))?.first {
            currentStats.totalListeningMinutes = entity.totalListeningMinutes
            currentStats.totalTracksPlayed = Int(entity.totalTracksPlayed)
            currentStats.currentStreakDays = Int(entity.currentStreakDays)
            currentStats.longestStreakDays = Int(entity.longestStreakDays)
            currentStats.lastListeningDate = entity.lastListeningDate
            currentStats.trampMiles = entity.trampMiles
            currentStats.level = Int(entity.level)
            currentStats.xp = entity.xp
            currentStats.totalSearches = Int(entity.totalSearches)
            currentStats.radioSessions = Int(entity.radioSessions)
            currentStats.playlistsCreated = Int(entity.playlistsCreated)
            currentStats.skinChanges = Int(entity.skinChanges)
            currentStats.onboardingCompleted = entity.onboardingCompleted
            
            if let badgeData = entity.badgesData,
               let badges = try? JSONDecoder().decode([Badge].self, from: badgeData) {
                currentStats.badges = badges
            }
            
            if let genreData = entity.favoriteGenresData,
               let genres = try? JSONDecoder().decode([String: Int].self, from: genreData) {
                currentStats.favoriteGenres = genres
            }
        }
    }
    
    private func saveToCoreData() {
        let context = persistence.container.viewContext
        let request = NSFetchRequest<NSFetchRequestResult>(entityName: "UserStatsEntity")
        let deleteRequest = NSBatchDeleteRequest(fetchRequest: request)
        _ = try? context.execute(deleteRequest)
        
        let entity = UserStatsEntity(context: context)
        entity.totalListeningMinutes = currentStats.totalListeningMinutes
        entity.totalTracksPlayed = Int32(currentStats.totalTracksPlayed)
        entity.currentStreakDays = Int32(currentStats.currentStreakDays)
        entity.longestStreakDays = Int32(currentStats.longestStreakDays)
        entity.lastListeningDate = currentStats.lastListeningDate
        entity.trampMiles = currentStats.trampMiles
        entity.level = Int32(currentStats.level)
        entity.xp = currentStats.xp
        entity.totalSearches = Int32(currentStats.totalSearches)
        entity.radioSessions = Int32(currentStats.radioSessions)
        entity.playlistsCreated = Int32(currentStats.playlistsCreated)
        entity.skinChanges = Int32(currentStats.skinChanges)
        entity.onboardingCompleted = currentStats.onboardingCompleted
        entity.badgesData = try? JSONEncoder().encode(currentStats.badges)
        entity.favoriteGenresData = try? JSONEncoder().encode(currentStats.favoriteGenres)
        
        persistence.save()
    }
}
