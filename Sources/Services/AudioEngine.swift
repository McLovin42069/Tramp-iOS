import Foundation
import AVFoundation
import Combine
import Accelerate
import MediaPlayer

@Observable
final class AudioEngine: NSObject {
    static let shared = AudioEngine()
    
    // MARK: - Playback State
    var isPlaying = false
    var isBuffering = false
    var currentTime: TimeInterval = 0
    var duration: TimeInterval = 0
    var volume: Float = 0.8 {
        didSet { player?.volume = volume }
    }
    var playbackRate: Float = 1.0 {
        didSet { player?.rate = isPlaying ? playbackRate : 0 }
    }
    var currentTrack: Track?
    var queue: [Track] = []
    var currentIndex = 0
    var repeatMode: RepeatMode = .none
    var shuffleMode: Bool = false
    
    // MARK: - Spectrum Data for Visualizer
    var spectrumData: [Float] = Array(repeating: 0.0, count: 64)
    var peakLevels: [Float] = Array(repeating: 0.0, count: 2)
    
    // MARK: - Private
    private var player: AVPlayer?
    private var playerItem: AVPlayerItem?
    private var timeObserver: Any?
    private var audioEngine = AVAudioEngine()
    private var audioPlayerNode = AVAudioPlayerNode()
    private var tapQueue = DispatchQueue(label: "tramp.audio.tap")
    private var cancellables = Set<AnyCancellable>()
    
    enum RepeatMode: String, CaseIterable {
        case none = "None"
        case one = "One"
        case all = "All"
        
        var icon: String {
            switch self {
            case .none: return "repeat"
            case .one: return "repeat.1"
            case .all: return "repeat"
            }
        }
    }
    
    override init() {
        super.init()
        setupAudioSession()
        setupVisualizerTap()
        setupRemoteCommands()
    }
    
    deinit {
        if let observer = timeObserver {
            player?.removeTimeObserver(observer)
        }
    }
    
    // MARK: - Audio Session
    private func setupAudioSession() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [.allowAirPlay, .allowBluetooth])
            try session.setActive(true)
        } catch {
            print("Audio session setup failed: \(error)")
        }
    }
    
    // MARK: - Visualizer
    private var visualizerTimer: Timer?
    private var beatPhase: Double = 0
    
    private func setupVisualizerTap() {
        // AVPlayer doesn't expose audio buffers easily.
        // We use a synthetic spectrum generator for the retro visualizer effect.
        startVisualizerTimer()
    }
    
    private func startVisualizerTimer() {
        visualizerTimer?.invalidate()
        visualizerTimer = Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) { [weak self] _ in
            self?.generateSyntheticSpectrum()
        }
    }
    
    private func generateSyntheticSpectrum() {
        guard isPlaying else {
            // Decay to zero when paused
            spectrumData = spectrumData.map { max($0 - 0.05, 0) }
            peakLevels = peakLevels.map { max($0 - 0.05, 0) }
            return
        }
        
        beatPhase += 0.15
        let beat = sin(beatPhase) * 0.5 + 0.5
        let secondaryBeat = sin(beatPhase * 1.7) * 0.3 + 0.3
        
        var newSpectrum = [Float](repeating: 0, count: 64)
        for i in 0..<64 {
            let freq = Double(i) / 64.0
            // Bass emphasis on left, treble on right
            let bass = exp(-freq * 4) * beat
            let mid = exp(-pow(freq - 0.3, 2) * 20) * secondaryBeat
            let treble = exp(-pow(freq - 0.8, 2) * 30) * (1 - beat) * 0.5
            
            let value = bass + mid + treble + Double.random(in: 0...0.05)
            let smoothed = Double(spectrumData[i]) * 0.7 + value * 0.3
            newSpectrum[i] = Float(min(smoothed, 1.0))
        }
        
        spectrumData = newSpectrum
        
        // Simulate peak meters
        let leftPeak = Float(beat * 0.8 + Double.random(in: 0...0.2))
        let rightPeak = Float(secondaryBeat * 0.8 + Double.random(in: 0...0.2))
        peakLevels = [leftPeak, rightPeak]
    }
    
    // MARK: - Remote Commands
    private func setupRemoteCommands() {
        let center = MPRemoteCommandCenter.shared()
        
        center.playCommand.addTarget { [weak self] _ in
            self?.play()
            return .success
        }
        
        center.pauseCommand.addTarget { [weak self] _ in
            self?.pause()
            return .success
        }
        
        center.nextTrackCommand.addTarget { [weak self] _ in
            self?.nextTrack()
            return .success
        }
        
        center.previousTrackCommand.addTarget { [weak self] _ in
            self?.previousTrack()
            return .success
        }
        
        center.changePlaybackPositionCommand.addTarget { [weak self] event in
            if let positionEvent = event as? MPChangePlaybackPositionCommandEvent {
                self?.seek(to: positionEvent.positionTime)
            }
            return .success
        }
    }
    
    // MARK: - Playback Control
    func load(track: Track, queue: [Track]? = nil) {
        currentTrack = track
        if let queue = queue {
            self.queue = queue
            self.currentIndex = queue.firstIndex(where: { $0.id == track.id }) ?? 0
        }
        
        guard let url = track.streamURL else { return }
        
        let asset = AVAsset(url: url)
        playerItem = AVPlayerItem(asset: asset)
        player = AVPlayer(playerItem: playerItem)
        player?.volume = volume
        
        // Observe duration
        playerItem?.publisher(for: \.duration)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] duration in
                if duration.isNumeric {
                    self?.duration = CMTimeGetSeconds(duration)
                }
            }
            .store(in: &cancellables)
        
        // Observe status
        playerItem?.publisher(for: \.status)
            .receive(on: DispatchQueue.main)
            .sink { [weak self] status in
                self?.isBuffering = status == .unknown
            }
            .store(in: &cancellables)
        
        // Time observer
        if let observer = timeObserver {
            player?.removeTimeObserver(observer)
        }
        
        timeObserver = player?.addPeriodicTimeObserver(forInterval: CMTime(seconds: 0.5, preferredTimescale: 1000), queue: .main) { [weak self] time in
            self?.currentTime = CMTimeGetSeconds(time)
        }
        
        updateNowPlayingInfo()
        play()
    }
    
    func play() {
        player?.play()
        player?.rate = playbackRate
        isPlaying = true
        updateNowPlayingInfo()
    }
    
    func pause() {
        player?.pause()
        isPlaying = false
        updateNowPlayingInfo()
    }
    
    func togglePlayPause() {
        isPlaying ? pause() : play()
    }
    
    func seek(to time: TimeInterval) {
        let cmTime = CMTime(seconds: time, preferredTimescale: 1000)
        player?.seek(to: cmTime)
    }
    
    func nextTrack() {
        guard !queue.isEmpty else { return }
        
        if shuffleMode {
            currentIndex = Int.random(in: 0..<queue.count)
        } else {
            currentIndex = (currentIndex + 1) % queue.count
        }
        
        load(track: queue[currentIndex])
    }
    
    func previousTrack() {
        guard !queue.isEmpty else { return }
        
        if currentTime > 3 {
            seek(to: 0)
        } else {
            currentIndex = (currentIndex - 1 + queue.count) % queue.count
            load(track: queue[currentIndex])
        }
    }
    
    func toggleRepeat() {
        let modes = RepeatMode.allCases
        if let currentIdx = modes.firstIndex(of: repeatMode) {
            repeatMode = modes[(currentIdx + 1) % modes.count]
        }
    }
    
    func toggleShuffle() {
        shuffleMode.toggle()
    }
    
    // MARK: - Now Playing Info
    private func updateNowPlayingInfo() {
        var info: [String: Any] = [
            MPMediaItemPropertyPlaybackDuration: duration,
            MPNowPlayingInfoPropertyElapsedPlaybackTime: currentTime,
            MPNowPlayingInfoPropertyPlaybackRate: isPlaying ? playbackRate : 0
        ]
        
        if let track = currentTrack {
            info[MPMediaItemPropertyTitle] = track.displayTitle
            info[MPMediaItemPropertyArtist] = track.displayArtist
            info[MPMediaItemPropertyAlbumTitle] = track.displayAlbum
        }
        
        MPNowPlayingInfoCenter.default().nowPlayingInfo = info
    }
}
