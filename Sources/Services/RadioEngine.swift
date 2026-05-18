import Foundation

actor RadioEngine {
    static let shared = RadioEngine()
    
    private var history: [Track] = []
    private var seedGenres: [MusicGenre] = []
    private var seedMood: MusicMood = .any
    private var isActive = false
    
    func startRadio(genres: [MusicGenre] = [.any], mood: MusicMood = .any) async -> [Track] {
        isActive = true
        seedGenres = genres.isEmpty ? [.any] : genres
        seedMood = mood
        history.removeAll()
        
        var tracks: [Track] = []
        
        // Fetch from multiple sources
        async let jamendoTracks = fetchJamendoTracks()
        async let archiveTracks = fetchArchiveTracks()
        
        let (jamendo, archive) = await (try? jamendoTracks, try? archiveTracks)
        
        if let jamendo = jamendo { tracks.append(contentsOf: jamendo) }
        if let archive = archive { tracks.append(contentsOf: archive) }
        
        // Shuffle intelligently - avoid same artist back to back
        tracks = intelligentShuffle(tracks)
        
        return tracks
    }
    
    func getNextTrack(currentQueue: [Track]) async -> Track? {
        guard isActive else { return nil }
        
        // Try to get a track that isn't recently played
        var attempts = 0
        while attempts < 10 {
            async let jamendo = fetchSingleJamendo()
            async let archive = fetchSingleArchive()
            
            if let track = await (try? jamendo) ?? (try? archive) {
                let recentlyPlayed = history.suffix(20).map { $0.id }
                if !recentlyPlayed.contains(track.id) {
                    history.append(track)
                    return track
                }
            }
            attempts += 1
        }
        
        // Fallback: repeat from queue
        return currentQueue.randomElement()
    }
    
    func stopRadio() {
        isActive = false
        history.removeAll()
    }
    
    private func fetchJamendoTracks() async throws -> [Track] {
        let genres = seedGenres.compactMap { $0.jamendoTag }
        var allTracks: [Track] = []
        
        if let firstGenre = genres.first {
            let tracks = try await JamendoService.shared.getByGenre(
                MusicGenre(rawValue: firstGenre.capitalized) ?? .any,
                limit: 15
            )
            allTracks.append(contentsOf: tracks)
        }
        
        if allTracks.isEmpty {
            let popular = try await JamendoService.shared.getPopular(limit: 20)
            allTracks.append(contentsOf: popular)
        }
        
        return allTracks
    }
    
    private func fetchArchiveTracks() async throws -> [Track] {
        if seedGenres.contains(.classical) {
            return try await InternetArchiveService.shared.getClassicalCollection(limit: 15)
        }
        return try await InternetArchiveService.shared.getOldRecordings(limit: 10)
    }
    
    private func fetchSingleJamendo() async throws -> Track {
        let tracks = try await JamendoService.shared.getPopular(limit: 50)
        guard let track = tracks.randomElement() else {
            throw RadioError.noTracksAvailable
        }
        return track
    }
    
    private func fetchSingleArchive() async throws -> Track {
        let tracks = try await InternetArchiveService.shared.getOldRecordings(limit: 30)
        guard let track = tracks.randomElement() else {
            throw RadioError.noTracksAvailable
        }
        return track
    }
    
    private func intelligentShuffle(_ tracks: [Track]) -> [Track] {
        guard tracks.count > 1 else { return tracks }
        
        var result: [Track] = []
        var remaining = tracks
        
        // Start with a random track
        if let first = remaining.randomElement(), let idx = remaining.firstIndex(where: { $0.id == first.id }) {
            result.append(first)
            remaining.remove(at: idx)
        }
        
        // Greedily select next track with different artist
        while !remaining.isEmpty {
            let lastArtist = result.last?.artist ?? ""
            
            // Find a track with different artist
            if let next = remaining.first(where: { $0.artist != lastArtist }) {
                result.append(next)
                remaining.removeAll(where: { $0.id == next.id })
            } else {
                // All remaining are same artist, just pick random
                if let next = remaining.randomElement() {
                    result.append(next)
                    remaining.removeAll(where: { $0.id == next.id })
                }
            }
        }
        
        return result
    }
    
    enum RadioError: Error {
        case noTracksAvailable
    }
}
