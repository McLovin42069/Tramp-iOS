import SwiftUI

struct MainPlayerView: View {
    @State private var viewModel = PlayerViewModel()
    @State private var skinManager = SkinManager.shared
    
    var body: some View {
        ZStack {
            skinManager.currentSkin.backgroundColor
            
            RustyTexture(opacity: skinManager.currentSkin.textureOpacity)
            
            VStack(spacing: 0) {
                // Title Bar
                titleBar
                
                // Main Display
                displaySection
                    .padding(.horizontal, 8)
                    .padding(.vertical, 6)
                
                // Spectrum Analyzer
                SpectrumAnalyzer(
                    data: viewModel.spectrumData,
                    barColor: skinManager.currentSkin.ledColor,
                    backgroundColor: skinManager.currentSkin.displayColor
                )
                .frame(height: 30)
                .padding(.horizontal, 8)
                .overlay(
                    RoundedRectangle(cornerRadius: 1)
                        .stroke(skinManager.currentSkin.bezelColor, lineWidth: 2)
                )
                
                // Controls
                controlsSection
                    .padding(.horizontal, 8)
                    .padding(.vertical, 6)
                
                // Seek Bar
                seekBarSection
                    .padding(.horizontal, 8)
                    .padding(.bottom, 6)
                
                // Secondary Controls
                secondaryControls
                    .padding(.horizontal, 8)
                    .padding(.bottom, 8)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .sheet(isPresented: $viewModel.isShowingPlaylist) {
            PlaylistWindowView()
        }
        .sheet(isPresented: $viewModel.isShowingEqualizer) {
            EqualizerView()
        }
        .sheet(isPresented: $viewModel.isShowingVisualizer) {
            VisualizerView()
        }
        .sheet(isPresented: $viewModel.isShowingSkinSelector) {
            SkinSelectorView()
        }
    }
    
    // MARK: - Title Bar
    private var titleBar: some View {
        HStack(spacing: 4) {
            Image(systemName: "train.side.front.car")
                .font(.system(size: 14))
                .foregroundColor(skinManager.currentSkin.accentColor)
            
            Text(Constants.appName)
                .font(.system(size: 12, weight: .bold, design: .monospaced))
                .foregroundColor(skinManager.currentSkin.textColor)
            
            Spacer()
            
            Button(action: { viewModel.isShowingSkinSelector = true }) {
                Image(systemName: "paintbrush")
                    .font(.system(size: 12))
                    .foregroundColor(skinManager.currentSkin.textColor)
            }
            .buttonStyle(PlainButtonStyle())
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(
            LinearGradient(
                colors: [
                    skinManager.currentSkin.bezelColor.brightness(0.3),
                    skinManager.currentSkin.bezelColor
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        )
        .overlay(
            Rectangle()
                .frame(height: 1)
                .foregroundColor(Color.black.opacity(0.3)),
            alignment: .bottom
        )
    }
    
    // MARK: - Display Section
    private var displaySection: some View {
        HStack(spacing: 8) {
            // Time Display
            VStack(spacing: 2) {
                LEDDisplay(
                    text: viewModel.formattedCurrentTime,
                    fontSize: 14,
                    color: skinManager.currentSkin.ledColor,
                    backgroundColor: skinManager.currentSkin.displayColor
                )
                .frame(width: 60, height: 20)
                
                LEDDisplay(
                    text: viewModel.formattedDuration,
                    fontSize: 10,
                    color: skinManager.currentSkin.ledColor.opacity(0.7),
                    backgroundColor: skinManager.currentSkin.displayColor
                )
                .frame(width: 60, height: 14)
            }
            
            // Title / Artist Display
            VStack(alignment: .leading, spacing: 2) {
                MarqueeText(
                    text: viewModel.currentTrack?.displayTitle ?? "No Track",
                    font: .system(size: 12, weight: .bold, design: .monospaced),
                    color: skinManager.currentSkin.ledColor,
                    speed: 30
                )
                .frame(height: 18)
                
                MarqueeText(
                    text: viewModel.currentTrack?.displayArtist ?? "Select a track",
                    font: .system(size: 10, design: .monospaced),
                    color: skinManager.currentSkin.ledColor.opacity(0.8),
                    speed: 25
                )
                .frame(height: 14)
                
                HStack(spacing: 4) {
                    if viewModel.shuffleMode {
                        Image(systemName: "shuffle")
                            .font(.system(size: 8))
                            .foregroundColor(skinManager.currentSkin.accentColor)
                    }
                    if viewModel.repeatMode != .none {
                        Image(systemName: viewModel.repeatMode.icon)
                            .font(.system(size: 8))
                            .foregroundColor(skinManager.currentSkin.accentColor)
                    }
                    Spacer()
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.horizontal, 4)
            .background(skinManager.currentSkin.displayColor)
            .overlay(
                RoundedRectangle(cornerRadius: 1)
                    .stroke(skinManager.currentSkin.bezelColor, lineWidth: 2)
            )
            
            // Peak Level Meters
            VStack(spacing: 2) {
                PeakMeter(level: viewModel.peakLevels.first ?? 0, color: skinManager.currentSkin.ledColor)
                PeakMeter(level: viewModel.peakLevels.last ?? 0, color: skinManager.currentSkin.ledColor)
            }
            .frame(width: 12)
        }
        .frame(height: 70)
    }
    
    // MARK: - Controls Section
    private var controlsSection: some View {
        HStack(spacing: 12) {
            // Prev
            WinampButton(icon: "backward.fill", size: 36) {
                viewModel.previousTrack()
            }
            
            // Play / Pause
            WinampButton(icon: viewModel.isPlaying ? "pause.fill" : "play.fill", size: 44) {
                viewModel.togglePlayPause()
            }
            
            // Stop
            WinampButton(icon: "stop.fill", size: 36) {
                viewModel.pause()
            }
            
            // Next
            WinampButton(icon: "forward.fill", size: 36) {
                viewModel.nextTrack()
            }
            
            Spacer()
            
            // Shuffle
            WinampButton(icon: "shuffle", size: 28) {
                viewModel.toggleShuffle()
            }
            .opacity(viewModel.shuffleMode ? 1.0 : 0.5)
            
            // Repeat
            WinampButton(icon: viewModel.repeatMode.icon, size: 28) {
                viewModel.toggleRepeat()
            }
            .opacity(viewModel.repeatMode != .none ? 1.0 : 0.5)
        }
    }
    
    // MARK: - Seek Bar
    private var seekBarSection: some View {
        VStack(spacing: 2) {
            SeekBar(
                progress: viewModel.progress,
                onSeek: { progress in
                    viewModel.seek(to: progress * viewModel.duration)
                },
                color: skinManager.currentSkin.accentColor,
                backgroundColor: skinManager.currentSkin.displayColor
            )
            
            HStack {
                Text(viewModel.formattedCurrentTime)
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.7))
                
                Spacer()
                
                Text(viewModel.formattedDuration)
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.7))
            }
        }
    }
    
    // MARK: - Secondary Controls
    private var secondaryControls: some View {
        HStack(spacing: 8) {
            // Volume
            VStack(spacing: 2) {
                Image(systemName: "speaker.wave.2")
                    .font(.system(size: 10))
                    .foregroundColor(skinManager.currentSkin.textColor)
                
                VolumeSlider(
                    value: Binding(
                        get: { viewModel.volume },
                        set: { viewModel.volume = $0 }
                    ),
                    color: skinManager.currentSkin.accentColor,
                    backgroundColor: skinManager.currentSkin.displayColor
                )
                .frame(width: 80)
            }
            
            Spacer()
            
            // Playlist Button
            WinampTextButton(title: "PLS", width: 40, height: 24) {
                viewModel.isShowingPlaylist = true
            }
            
            // EQ Button
            WinampTextButton(title: "EQ", width: 40, height: 24) {
                viewModel.isShowingEqualizer = true
            }
            
            // Visualizer Button
            WinampTextButton(title: "VIS", width: 40, height: 24) {
                viewModel.isShowingVisualizer = true
            }
        }
    }
}

struct PeakMeter: View {
    let level: Float
    let color: Color
    
    var body: some View {
        Canvas { context, size in
            let segmentHeight = (size.height - 11) / 12
            
            for i in 0..<12 {
                let threshold = Float(i) / 12.0
                let isActive = level > threshold
                let isRed = i > 9
                let y = size.height - CGFloat(i + 1) * (segmentHeight + 1)
                
                let rect = CGRect(x: 0, y: y, width: size.width, height: segmentHeight)
                let path = Path(rect)
                
                let fillColor = isActive
                    ? (isRed ? Color.red : color)
                    : Color.black.opacity(0.5)
                
                context.fill(path, with: .color(fillColor))
            }
        }
    }
}
