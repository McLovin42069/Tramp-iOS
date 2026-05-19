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
        
        // Fetch from Internet Archive (no API key needed)
        do {
            let archiveTracks = try await fetchArchiveTracks()
            tracks.append(contentsOf: archiveTracks)
        } catch {
            print("[RadioEngine] Archive fetch failed: \(error)")
        }
        
        // Fallback to classical or old recordings if nothing found
        if tracks.isEmpty {
            do {
                let classical = try await InternetArchiveService.shared.getClassicalCollection(limit: 15)
                tracks.append(contentsOf: classical)
            } catch {
                print("[RadioEngine] Classical fallback failed: \(error)")
            }
        }
        
        if tracks.isEmpty {
            do {
                let old = try await InternetArchiveService.shared.getOldRecordings(limit: 15)
                tracks.append(contentsOf: old)
            } catch {
                print("[RadioEngine] Old recordings fallback failed: \(error)")
            }
        }
        
        // Shuffle intelligently - avoid same artist back to back
        tracks = intelligentShuffle(tracks)
        
        return tracks
    }
    
    func getNextTrack(currentQueue: [Track]) async -> Track? {
        guard isActive else { return nil }
        
        // Try to get a track that isn't recently played
        var attempts = 0
        while attempts < 10 {
            do {
                let track = try await fetchSingleArchive()
                let recentlyPlayed = history.suffix(20).map { $0.id }
                if !recentlyPlayed.contains(track.id) {
                    history.append(track)
                    return track
                }
            } catch {
                print("[RadioEngine] Fetch next track failed: \(error)")
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
    
    private func fetchArchiveTracks() async throws -> [Track] {
        if seedGenres.contains(.classical) {
            return try await InternetArchiveService.shared.getClassicalCollection(limit: 15)
        }
        if seedGenres.contains(.jazz) {
            return try await InternetArchiveService.shared.search(query: "jazz", limit: 15)
        }
        if seedGenres.contains(.blues) {
            return try await InternetArchiveService.shared.search(query: "blues", limit: 15)
        }
        if seedGenres.contains(.rock) {
            return try await InternetArchiveService.shared.search(query: "rock", limit: 15)
        }
        return try await InternetArchiveService.shared.getOldRecordings(limit: 20)
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
