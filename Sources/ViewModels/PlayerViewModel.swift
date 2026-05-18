import Foundation
import SwiftUI
import Combine

@Observable
final class PlayerViewModel {
    var isShowingPlaylist = false
    var isShowingEqualizer = false
    var isShowingVisualizer = false
    var isShowingSkinSelector = false
    
    var currentTrack: Track? { audioEngine.currentTrack }
    var isPlaying: Bool { audioEngine.isPlaying }
    var currentTime: TimeInterval { audioEngine.currentTime }
    var duration: TimeInterval { audioEngine.duration }
    var volume: Float {
        get { audioEngine.volume }
        set { audioEngine.volume = newValue }
    }
    var queue: [Track] { audioEngine.queue }
    var currentIndex: Int { audioEngine.currentIndex }
    var repeatMode: AudioEngine.RepeatMode { audioEngine.repeatMode }
    var shuffleMode: Bool { audioEngine.shuffleMode }
    var spectrumData: [Float] { audioEngine.spectrumData }
    var peakLevels: [Float] { audioEngine.peakLevels }
    
    private let audioEngine = AudioEngine.shared
    private let statsManager = StatsManager.shared
    private var timer: Timer?
    private var startTime: Date?
    
    init() {
        startListeningTimer()
    }
    
    func play(track: Track, queue: [Track]? = nil) {
        audioEngine.load(track: track, queue: queue)
        statsManager.recordPlay(track: track)
        startTime = Date()
    }
    
    func togglePlayPause() {
        audioEngine.togglePlayPause()
        if isPlaying {
            startTime = Date()
        } else {
            recordListeningTime()
        }
    }
    
    func pause() {
        recordListeningTime()
        audioEngine.pause()
    }
    
    func nextTrack() {
        recordListeningTime()
        audioEngine.nextTrack()
        if let track = audioEngine.currentTrack {
            statsManager.recordPlay(track: track)
        }
        startTime = Date()
    }
    
    func previousTrack() {
        recordListeningTime()
        audioEngine.previousTrack()
        if let track = audioEngine.currentTrack {
            statsManager.recordPlay(track: track)
        }
        startTime = Date()
    }
    
    func seek(to time: TimeInterval) {
        audioEngine.seek(to: time)
    }
    
    func toggleRepeat() {
        audioEngine.toggleRepeat()
    }
    
    func toggleShuffle() {
        audioEngine.toggleShuffle()
    }
    
    func playQueue(_ tracks: [Track], startingAt index: Int = 0) {
        guard index >= 0 && index < tracks.count else { return }
        audioEngine.load(track: tracks[index], queue: tracks)
        statsManager.recordPlay(track: tracks[index])
        startTime = Date()
    }
    
    func addToQueue(_ track: Track) {
        var newQueue = audioEngine.queue
        newQueue.append(track)
        audioEngine.queue = newQueue
    }
    
    func removeFromQueue(at index: Int) {
        guard index >= 0 && index < audioEngine.queue.count else { return }
        audioEngine.queue.remove(at: index)
        if index < audioEngine.currentIndex {
            audioEngine.currentIndex -= 1
        }
    }
    
    func moveQueueItem(from source: IndexSet, to destination: Int) {
        audioEngine.queue.move(fromOffsets: source, toOffset: destination)
    }
    
    func clearQueue() {
        audioEngine.queue.removeAll()
        audioEngine.currentIndex = 0
    }
    
    var progress: Double {
        guard duration > 0 else { return 0 }
        return currentTime / duration
    }
    
    var formattedCurrentTime: String {
        currentTime.formattedTime()
    }
    
    var formattedDuration: String {
        duration.formattedTime()
    }
    
    private func startListeningTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { [weak self] _ in
            if self?.isPlaying == true {
                self?.recordListeningTime()
                self?.startTime = Date()
            }
        }
    }
    
    private func recordListeningTime() {
        guard let start = startTime else { return }
        let elapsed = Date().timeIntervalSince(start)
        if elapsed > 0 {
            statsManager.addListeningTime(elapsed / 60)
        }
    }
}
