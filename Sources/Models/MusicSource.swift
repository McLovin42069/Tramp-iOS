import Foundation

enum MusicSource: String, CaseIterable, Identifiable, Codable {
    case jamendo = "Jamendo"
    case soundcloud = "SoundCloud"
    case internetArchive = "Internet Archive"
    case freeMusicArchive = "Free Music Archive"
    case pixabay = "Pixabay"
    case localFiles = "My Collection"
    
    var id: String { rawValue }
    
    var icon: String {
        switch self {
        case .jamendo: return "music.note.house"
        case .soundcloud: return "cloud.fill"
        case .internetArchive: return "archivebox.fill"
        case .freeMusicArchive: return "folder.fill"
        case .pixabay: return "photo.fill"
        case .localFiles: return "iphone"
        }
    }
    
    var color: String {
        switch self {
        case .jamendo: return "FF6B35"
        case .soundcloud: return "FF5500"
        case .internetArchive: return "F4A460"
        case .freeMusicArchive: return "4A90E2"
        case .pixabay: return "50C878"
        case .localFiles: return "D4D4D4"
        }
    }
    
    var description: String {
        switch self {
        case .jamendo:
            return "Independent music from artists worldwide. Free to stream and download."
        case .soundcloud:
            return "Creative Commons tracks from SoundCloud's vast independent catalog."
        case .internetArchive:
            return "Public domain classical, old recordings, and live concerts."
        case .freeMusicArchive:
            return "Curated Creative Commons music from WFMU."
        case .pixabay:
            return "High-quality royalty-free music for any use."
        case .localFiles:
            return "Your own music files imported from the Files app."
        }
    }
    
    var supportsSearch: Bool {
        switch self {
        case .soundcloud:
            return false // CC search requires complex OAuth
        default:
            return true
        }
    }
}

enum MusicGenre: String, CaseIterable, Identifiable {
    case rock = "Rock"
    case electronic = "Electronic"
    case jazz = "Jazz"
    case classical = "Classical"
    case hipHop = "Hip Hop"
    case ambient = "Ambient"
    case folk = "Folk"
    case blues = "Blues"
    case punk = "Punk"
    case indie = "Indie"
    case metal = "Metal"
    case pop = "Pop"
    case reggae = "Reggae"
    case soul = "Soul"
    case any = "Any Genre"
    
    var id: String { rawValue }
    
    var jamendoTag: String? {
        switch self {
        case .rock: return "rock"
        case .electronic: return "electronic"
        case .jazz: return "jazz"
        case .classical: return "classical"
        case .hipHop: return "hiphop"
        case .ambient: return "ambient"
        case .folk: return "folk"
        case .blues: return "blues"
        case .punk: return "punk"
        case .indie: return "indie"
        case .metal: return "metal"
        case .pop: return "pop"
        case .reggae: return "reggae"
        case .soul: return "soul"
        case .any: return nil
        }
    }
    
    var archiveQuery: String? {
        switch self {
        case .classical: return "classical music"
        case .jazz: return "jazz music"
        case .rock: return "rock music"
        case .blues: return "blues music"
        case .folk: return "folk music"
        default: return nil
        }
    }
}

enum MusicMood: String, CaseIterable, Identifiable {
    case chill = "Chill"
    case energetic = "Energetic"
    case dark = "Dark"
    case happy = "Happy"
    case focused = "Focused"
    case nostalgic = "Nostalgic"
    case roadTrip = "Road Trip"
    case lonely = "Lonely"
    case hopeful = "Hopeful"
    case any = "Any Mood"
    
    var id: String { rawValue }
}
