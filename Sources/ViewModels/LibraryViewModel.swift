import Foundation
import CoreData

@Observable
final class LibraryViewModel {
    var playlists: [Playlist] = []
    var importedTracks: [Track] = []
    var favoriteTracks: [Track] = []
    var recentlyPlayed: [Track] = []
    var isLoading = false
    
    var selectedTab: LibraryTab = .playlists
    
    enum LibraryTab: String, CaseIterable {
        case playlists = "Playlists"
        case tracks = "Tracks"
        case favorites = "Favorites"
        case recent = "Recent"
        
        var icon: String {
            switch self {
            case .playlists: return "list.bullet.rectangle"
            case .tracks: return "music.note.list"
            case .favorites: return "heart.fill"
            case .recent: return "clock.arrow.circlepath"
            }
        }
    }
    
    private let localFiles = LocalFileService.shared
    private let persistence = PersistenceController.shared
    
    init() {
        Task {
            await loadLibrary()
        }
    }
    
    func loadLibrary() async {
        isLoading = true
        
        async let tracks = localFiles.getImportedTracks()
        if let t = try? await tracks {
            importedTracks = t
        }
        
        await MainActor.run {
            loadPlaylistsFromCoreData()
            loadFavorites()
            loadRecentlyPlayed()
            isLoading = false
        }
    }
    
    func createPlaylist(name: String, tracks: [Track] = []) {
        let playlist = Playlist(name: name, tracks: tracks)
        playlists.append(playlist)
        savePlaylistsToCoreData()
    }
    
    func deletePlaylist(at offsets: IndexSet) {
        playlists.remove(atOffsets: offsets)
        savePlaylistsToCoreData()
    }
    
    func addTrackToPlaylist(track: Track, playlist: Playlist) {
        if let index = playlists.firstIndex(where: { $0.id == playlist.id }) {
            playlists[index].addTrack(track)
            savePlaylistsToCoreData()
        }
    }
    
    func removeTrackFromPlaylist(at index: Int, playlist: Playlist) {
        if let pIndex = playlists.firstIndex(where: { $0.id == playlist.id }) {
            playlists[pIndex].removeTrack(at: index)
            savePlaylistsToCoreData()
        }
    }
    
    func moveTrackInPlaylist(from source: IndexSet, to destination: Int, playlist: Playlist) {
        if let index = playlists.firstIndex(where: { $0.id == playlist.id }) {
            playlists[index].moveTrack(from: source.first ?? 0, to: destination)
            savePlaylistsToCoreData()
        }
    }
    
    func toggleFavorite(_ track: Track) {
        if isFavorite(track) {
            favoriteTracks.removeAll { $0.id == track.id }
        } else {
            favoriteTracks.append(track)
        }
        saveFavorites()
    }
    
    func isFavorite(_ track: Track) -> Bool {
        favoriteTracks.contains(where: { $0.id == track.id })
    }
    
    func importFiles(from urls: [URL]) async {
        let tracks = await localFiles.importFiles(from: urls)
        importedTracks.append(contentsOf: tracks)
    }
    
    private func loadPlaylistsFromCoreData() {
        let request = NSFetchRequest<PlaylistEntity>(entityName: "PlaylistEntity")
        request.sortDescriptors = [NSSortDescriptor(key: "dateCreated", ascending: false)]
        
        do {
            let entities = try persistence.container.viewContext.fetch(request)
            playlists = entities.map { entity in
                let trackIDs = entity.trackOrder.components(separatedBy: ",").filter { !$0.isEmpty }
                return Playlist(
                    id: UUID(uuidString: entity.id) ?? UUID(),
                    name: entity.name,
                    tracks: [], // Would need to resolve track IDs to Track objects
                    dateCreated: entity.dateCreated,
                    isSmartPlaylist: entity.isSmartPlaylist,
                    smartFilter: entity.smartFilter
                )
            }
        } catch {
            print("Failed to load playlists: \(error)")
        }
    }
    
    private func savePlaylistsToCoreData() {
        let context = persistence.container.viewContext
        
        // Clear existing
        let request = NSFetchRequest<NSFetchRequestResult>(entityName: "PlaylistEntity")
        let deleteRequest = NSBatchDeleteRequest(fetchRequest: request)
        _ = try? context.execute(deleteRequest)
        
        for playlist in playlists {
            let entity = PlaylistEntity(context: context)
            entity.id = playlist.id.uuidString
            entity.name = playlist.name
            entity.dateCreated = playlist.dateCreated
            entity.trackOrder = playlist.tracks.map { $0.id }.joined(separator: ",")
            entity.isSmartPlaylist = playlist.isSmartPlaylist
            entity.smartFilter = playlist.smartFilter
        }
        
        persistence.save()
    }
    
    private func loadFavorites() {
        if let data = UserDefaults.standard.data(forKey: "tramp.favorites"),
           let tracks = try? JSONDecoder().decode([Track].self, from: data) {
            favoriteTracks = tracks
        }
    }
    
    private func saveFavorites() {
        if let data = try? JSONEncoder().encode(favoriteTracks) {
            UserDefaults.standard.set(data, forKey: "tramp.favorites")
        }
    }
    
    private func loadRecentlyPlayed() {
        if let data = UserDefaults.standard.data(forKey: "tramp.recentlyPlayed"),
           let tracks = try? JSONDecoder().decode([Track].self, from: data) {
            recentlyPlayed = tracks
        }
    }
    
    func addToRecentlyPlayed(_ track: Track) {
        recentlyPlayed.removeAll { $0.id == track.id }
        recentlyPlayed.insert(track, at: 0)
        if recentlyPlayed.count > 50 {
            recentlyPlayed = Array(recentlyPlayed.prefix(50))
        }
        if let data = try? JSONEncoder().encode(recentlyPlayed) {
            UserDefaults.standard.set(data, forKey: "tramp.recentlyPlayed")
        }
    }
}
