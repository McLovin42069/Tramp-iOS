import Foundation

struct Playlist: Identifiable, Equatable {
    let id: UUID
    var name: String
    var tracks: [Track]
    let dateCreated: Date
    var isSmartPlaylist: Bool
    var smartFilter: String?
    
    init(id: UUID = UUID(), name: String, tracks: [Track] = [], dateCreated: Date = Date(), isSmartPlaylist: Bool = false, smartFilter: String? = nil) {
        self.id = id
        self.name = name
        self.tracks = tracks
        self.dateCreated = dateCreated
        self.isSmartPlaylist = isSmartPlaylist
        self.smartFilter = smartFilter
    }
    
    var totalDuration: TimeInterval {
        tracks.reduce(0) { $0 + $1.duration }
    }
    
    var formattedDuration: String {
        totalDuration.formattedTime()
    }
    
    var uniqueArtists: [String] {
        Array(Set(tracks.map { $0.artist })).sorted()
    }
    
    mutating func addTrack(_ track: Track) {
        guard !tracks.contains(where: { $0.id == track.id }) else { return }
        tracks.append(track)
    }
    
    mutating func removeTrack(at index: Int) {
        guard index >= 0 && index < tracks.count else { return }
        tracks.remove(at: index)
    }
    
    mutating func moveTrack(from source: Int, to destination: Int) {
        guard source >= 0 && source < tracks.count else { return }
        let track = tracks.remove(at: source)
        let dest = destination > source ? destination - 1 : destination
        tracks.insert(track, at: min(dest, tracks.count))
    }
    
    mutating func shuffle() {
        tracks.shuffle()
    }
}

enum SmartPlaylistFilter: String, CaseIterable {
    case recentlyPlayed = "Recently Played"
    case mostPlayed = "Most Played"
    case neverPlayed = "Never Played"
    case longTracks = "Long Journeys"
    case favorites = "Favorites"
    case randomMix = "Random Mix"
    
    var icon: String {
        switch self {
        case .recentlyPlayed: return "clock.arrow.circlepath"
        case .mostPlayed: return "trophy.fill"
        case .neverPlayed: return "questionmark.circle.fill"
        case .longTracks: return "hourglass"
        case .favorites: return "heart.fill"
        case .randomMix: return "shuffle"
        }
    }
}
