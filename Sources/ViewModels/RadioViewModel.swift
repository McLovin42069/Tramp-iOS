import Foundation

@Observable
final class RadioViewModel {
    var isPlaying = false
    var currentTrack: Track?
    var queue: [Track] = []
    var history: [Track] = []
    var selectedGenres: [MusicGenre] = [.any]
    var selectedMood: MusicMood = .any
    var isLoading = false
    var stationName = "Tramp Radio"
    var crossfadeEnabled = true
    var crossfadeSeconds: Double = 2.0
    
    private let radioEngine = RadioEngine.shared
    private let playerVM = PlayerViewModel()
    private let statsManager = StatsManager.shared
    private var prefetchTask: Task<Void, Never>?
    
    func startRadio() async {
        isLoading = true
        
        let tracks = await radioEngine.startRadio(
            genres: selectedGenres,
            mood: selectedMood
        )
        
        queue = tracks
        isLoading = false
        
        if let first = tracks.first {
            playTrack(first)
        }
        
        statsManager.recordRadioSession()
    }
    
    func stopRadio() {
        Task {
            await radioEngine.stopRadio()
        }
        isPlaying = false
        currentTrack = nil
    }
    
    func skipTrack() {
        Task {
            if let next = await radioEngine.getNextTrack(currentQueue: queue) {
                await MainActor.run {
                    if let current = currentTrack {
                        history.append(current)
                    }
                    playTrack(next)
                    queue.append(next)
                }
            }
        }
    }
    
    func thumbsUp() {
        guard let track = currentTrack else { return }
        // Could add to favorites / similar track fetching
        HapticFeedback.success()
    }
    
    func thumbsDown() {
        skipTrack()
        HapticFeedback.error()
    }
    
    private func playTrack(_ track: Track) {
        currentTrack = track
        playerVM.play(track: track, queue: queue)
        isPlaying = true
    }
    
    var currentGenreLabel: String {
        if selectedGenres.contains(.any) || selectedGenres.isEmpty {
            return "All Genres"
        }
        return selectedGenres.map { $0.rawValue }.joined(separator: ", ")
    }
    
    var currentMoodLabel: String {
        selectedMood == .any ? "Any Mood" : selectedMood.rawValue
    }
}
