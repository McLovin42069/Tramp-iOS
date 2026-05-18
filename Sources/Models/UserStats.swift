import Foundation

struct UserStats: Codable {
    var totalListeningMinutes: Double
    var totalTracksPlayed: Int
    var currentStreakDays: Int
    var longestStreakDays: Int
    var lastListeningDate: Date?
    var trampMiles: Double
    var level: Int
    var xp: Double
    var badges: [Badge]
    var favoriteGenres: [String: Int]
    var totalSearches: Int
    var radioSessions: Int
    var playlistsCreated: Int
    var skinChanges: Int
    var onboardingCompleted: Bool
    var donationShownCount: Int
    
    static let `default` = UserStats(
        totalListeningMinutes: 0,
        totalTracksPlayed: 0,
        currentStreakDays: 0,
        longestStreakDays: 0,
        lastListeningDate: nil,
        trampMiles: 0,
        level: 1,
        xp: 0,
        badges: [],
        favoriteGenres: [:],
        totalSearches: 0,
        radioSessions: 0,
        playlistsCreated: 0,
        skinChanges: 0,
        onboardingCompleted: false,
        donationShownCount: 0
    )
    
    mutating func addListeningMinutes(_ minutes: Double) {
        totalListeningMinutes += minutes
        trampMiles += minutes * Constants.milesPerMinute
        xp += minutes * 10
        checkLevelUp()
        checkBadges()
    }
    
    mutating func checkStreak() {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        
        if let last = lastListeningDate {
            let lastDay = calendar.startOfDay(for: last)
            let daysBetween = calendar.dateComponents([.day], from: lastDay, to: today).day ?? 0
            
            if daysBetween == 1 {
                currentStreakDays += 1
                if currentStreakDays > longestStreakDays {
                    longestStreakDays = currentStreakDays
                }
            } else if daysBetween > 1 {
                currentStreakDays = 1
            }
        } else {
            currentStreakDays = 1
        }
        
        lastListeningDate = Date()
    }
    
    mutating func checkLevelUp() {
        let newLevel = Int(xp / 1000) + 1
        if newLevel > level {
            level = newLevel
        }
    }
    
    mutating func checkBadges() {
        let allBadges = Badge.allBadges
        for badge in allBadges where !badges.contains(where: { $0.id == badge.id }) {
            if badge.requirement.isUnlocked(stats: self) {
                badges.append(badge)
            }
        }
    }
    
    var levelTitle: String {
        switch level {
        case 1: return "Hobo"
        case 2: return "Wanderer"
        case 3: return "Traveler"
        case 4: return "Vagabond"
        case 5...9: return "Road Warrior"
        case 10...14: return "Highway King"
        case 15...19: return "Rail Rider"
        case 20...29: return "Dust Bowl Legend"
        case 30...49: return "Boxcar Mystic"
        case 50...99: return "Eternal Tramp"
        default: return "Myth"
        }
    }
    
    var progressToNextLevel: Double {
        let currentLevelXP = Double(level - 1) * 1000
        let nextLevelXP = Double(level) * 1000
        return (xp - currentLevelXP) / (nextLevelXP - currentLevelXP)
    }
}

struct Badge: Codable, Identifiable, Equatable {
    let id: String
    let name: String
    let description: String
    let icon: String
    let requirement: BadgeRequirement
    
    enum BadgeRequirement {
        case minutes(Double)
        case tracks(Int)
        case streak(Int)
        case miles(Double)
        case searches(Int)
        case radioSessions(Int)
        case playlists(Int)
        case level(Int)
        
        func isUnlocked(stats: UserStats) -> Bool {
            switch self {
            case .minutes(let m): return stats.totalListeningMinutes >= m
            case .tracks(let t): return stats.totalTracksPlayed >= t
            case .streak(let s): return stats.currentStreakDays >= s
            case .miles(let m): return stats.trampMiles >= m
            case .searches(let s): return stats.totalSearches >= s
            case .radioSessions(let r): return stats.radioSessions >= r
            case .playlists(let p): return stats.playlistsCreated >= p
            case .level(let l): return stats.level >= l
            }
        }
    }
    
    static let allBadges: [Badge] = [
        Badge(id: "first_steps", name: "First Steps", description: "Listen to your first track", icon: "shoe.fill", requirement: .tracks(1)),
        Badge(id: "wanderer", name: "Wanderer", description: "Listen for 1 hour total", icon: "figure.walk", requirement: .minutes(60)),
        Badge(id: "road_dog", name: "Road Dog", description: "3-day listening streak", icon: "flame.fill", requirement: .streak(3)),
        Badge(id: "explorer", name: "Explorer", description: "Search 50 times", icon: "magnifyingglass.circle.fill", requirement: .searches(50)),
        Badge(id: "radio_head", name: "Radio Head", description: "10 radio sessions", icon: "antenna.radiowaves.left.and.right", requirement: .radioSessions(10)),
        Badge(id: "curator", name: "Curator", description: "Create 5 playlists", icon: "list.bullet.rectangle.fill", requirement: .playlists(5)),
        Badge(id: "hundred_miles", name: "Century", description: "Travel 100 Tramp Miles", icon: "speedometer", requirement: .miles(100)),
        Badge(id: "veteran", name: "Veteran", description: "Reach level 10", icon: "star.circle.fill", requirement: .level(10)),
        Badge(id: "master", name: "Tramp Master", description: "Reach level 50", icon: "crown.fill", requirement: .level(50)),
    ]
    
    static func == (lhs: Badge, rhs: Badge) -> Bool {
        lhs.id == rhs.id
    }
}

// Codable conformance for BadgeRequirement
extension Badge.BadgeRequirement: Codable {
    private enum CodingKeys: String, CodingKey {
        case type, value
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .minutes(let v): try container.encode("minutes", forKey: .type); try container.encode(v, forKey: .value)
        case .tracks(let v): try container.encode("tracks", forKey: .type); try container.encode(v, forKey: .value)
        case .streak(let v): try container.encode("streak", forKey: .type); try container.encode(v, forKey: .value)
        case .miles(let v): try container.encode("miles", forKey: .type); try container.encode(v, forKey: .value)
        case .searches(let v): try container.encode("searches", forKey: .type); try container.encode(v, forKey: .value)
        case .radioSessions(let v): try container.encode("radio", forKey: .type); try container.encode(v, forKey: .value)
        case .playlists(let v): try container.encode("playlists", forKey: .type); try container.encode(v, forKey: .value)
        case .level(let v): try container.encode("level", forKey: .type); try container.encode(v, forKey: .value)
        }
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)
        switch type {
        case "minutes": self = .minutes(try container.decode(Double.self, forKey: .value))
        case "tracks": self = .tracks(try container.decode(Int.self, forKey: .value))
        case "streak": self = .streak(try container.decode(Int.self, forKey: .value))
        case "miles": self = .miles(try container.decode(Double.self, forKey: .value))
        case "searches": self = .searches(try container.decode(Int.self, forKey: .value))
        case "radio": self = .radioSessions(try container.decode(Int.self, forKey: .value))
        case "playlists": self = .playlists(try container.decode(Int.self, forKey: .value))
        case "level": self = .level(try container.decode(Int.self, forKey: .value))
        default: self = .tracks(0)
        }
    }
}
