import SwiftUI

struct MainPlayerView: View {
    @State private var viewModel = PlayerViewModel()
    @State private var skinManager = SkinManager.shared
    
    var body: some View {
        GeometryReader { geo in
            let w = geo.size.width
            let h = geo.size.height
            let isSmall = min(w, h) < 380
            
            ZStack {
                skinManager.currentSkin.backgroundColor
                RustyTexture(opacity: skinManager.currentSkin.textureOpacity)
                
                VStack(spacing: 0) {
                    // Title Bar
                    titleBar
                    
                    // Main Display — takes remaining space
                    displaySection(width: w, isSmall: isSmall)
                        .padding(.horizontal, max(12, w * 0.03))
                        .padding(.vertical, max(8, h * 0.015))
                    
                    // Spectrum Analyzer
                    SpectrumAnalyzer(
                        data: viewModel.spectrumData,
                        barColor: skinManager.currentSkin.ledColor,
                        backgroundColor: skinManager.currentSkin.displayColor
                    )
                    .frame(height: max(40, h * 0.06))
                    .padding(.horizontal, max(12, w * 0.03))
                    .overlay(
                        RoundedRectangle(cornerRadius: 2)
                            .stroke(skinManager.currentSkin.bezelColor, lineWidth: 2)
                    )
                    
                    // Controls
                    controlsSection(width: w, isSmall: isSmall)
                        .padding(.horizontal, max(12, w * 0.03))
                        .padding(.vertical, max(8, h * 0.015))
                    
                    // Seek Bar
                    seekBarSection(width: w)
                        .padding(.horizontal, max(12, w * 0.03))
                        .padding(.bottom, max(8, h * 0.015))
                    
                    // Secondary Controls
                    secondaryControls(width: w, isSmall: isSmall)
                        .padding(.horizontal, max(12, w * 0.03))
                        .padding(.bottom, max(16, h * 0.025))
                }
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
        HStack(spacing: 8) {
            Image(systemName: "train.side.front.car")
                .font(.system(size: 16, weight: .medium))
                .foregroundColor(skinManager.currentSkin.accentColor)
            
            Text(Constants.appName)
                .font(.system(size: 14, weight: .bold, design: .monospaced))
                .foregroundColor(skinManager.currentSkin.textColor)
            
            Spacer()
            
            Button(action: { viewModel.isShowingSkinSelector = true }) {
                Image(systemName: "paintbrush")
                    .font(.system(size: 14))
                    .foregroundColor(skinManager.currentSkin.textColor)
            }
            .buttonStyle(PlainButtonStyle())
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
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
    private func displaySection(width: CGFloat, isSmall: Bool) -> some View {
        let fontSizeLarge: CGFloat = isSmall ? 16 : 20
        let fontSizeSmall: CGFloat = isSmall ? 12 : 14
        let meterWidth: CGFloat = isSmall ? 16 : 20
        
        return HStack(spacing: 12) {
            // Time Display
            VStack(spacing: 4) {
                LEDDisplay(
                    text: viewModel.formattedCurrentTime,
                    fontSize: fontSizeLarge,
                    color: skinManager.currentSkin.ledColor,
                    backgroundColor: skinManager.currentSkin.displayColor
                )
                .frame(width: max(70, width * 0.18), height: 28)
                
                LEDDisplay(
                    text: viewModel.formattedDuration,
                    fontSize: fontSizeSmall,
                    color: skinManager.currentSkin.ledColor.opacity(0.7),
                    backgroundColor: skinManager.currentSkin.displayColor
                )
                .frame(width: max(70, width * 0.18), height: 20)
            }
            
            // Title / Artist Display
            VStack(alignment: .leading, spacing: 4) {
                MarqueeText(
                    text: viewModel.currentTrack?.displayTitle ?? "No Track",
                    font: .system(size: fontSizeLarge, weight: .bold, design: .monospaced),
                    color: skinManager.currentSkin.ledColor,
                    speed: 30
                )
                .frame(height: 26)
                
                MarqueeText(
                    text: viewModel.currentTrack?.displayArtist ?? "Select a track",
                    font: .system(size: fontSizeSmall, design: .monospaced),
                    color: skinManager.currentSkin.ledColor.opacity(0.8),
                    speed: 25
                )
                .frame(height: 20)
                
                HStack(spacing: 8) {
                    if viewModel.shuffleMode {
                        Image(systemName: "shuffle")
                            .font(.system(size: 10))
                            .foregroundColor(skinManager.currentSkin.accentColor)
                    }
                    if viewModel.repeatMode != .none {
                        Image(systemName: viewModel.repeatMode.icon)
                            .font(.system(size: 10))
                            .foregroundColor(skinManager.currentSkin.accentColor)
                    }
                    Spacer()
                }
            }
            .frame(maxWidth: .infinity)
            .padding(.horizontal, 8)
            .padding(.vertical, 6)
            .background(skinManager.currentSkin.displayColor)
            .overlay(
                RoundedRectangle(cornerRadius: 2)
                    .stroke(skinManager.currentSkin.bezelColor, lineWidth: 2)
            )
            
            // Peak Level Meters
            VStack(spacing: 4) {
                PeakMeter(level: viewModel.peakLevels.first ?? 0, color: skinManager.currentSkin.ledColor)
                PeakMeter(level: viewModel.peakLevels.last ?? 0, color: skinManager.currentSkin.ledColor)
            }
            .frame(width: meterWidth)
        }
        .frame(minHeight: 90)
    }
    
    // MARK: - Controls Section
    private func controlsSection(width: CGFloat, isSmall: Bool) -> some View {
        let btnSize: CGFloat = isSmall ? 44 : 56
        let playSize: CGFloat = isSmall ? 56 : 72
        let smallBtnSize: CGFloat = isSmall ? 32 : 40
        
        return HStack(spacing: max(16, width * 0.04)) {
            WinampButton(icon: "backward.fill", size: btnSize) {
                viewModel.previousTrack()
            }
            
            WinampButton(icon: viewModel.isPlaying ? "pause.fill" : "play.fill", size: playSize) {
                viewModel.togglePlayPause()
            }
            
            WinampButton(icon: "stop.fill", size: btnSize) {
                viewModel.pause()
            }
            
            WinampButton(icon: "forward.fill", size: btnSize) {
                viewModel.nextTrack()
            }
            
            Spacer(minLength: 20)
            
            WinampButton(icon: "shuffle", size: smallBtnSize) {
                viewModel.toggleShuffle()
            }
            .opacity(viewModel.shuffleMode ? 1.0 : 0.5)
            
            WinampButton(icon: viewModel.repeatMode.icon, size: smallBtnSize) {
                viewModel.toggleRepeat()
            }
            .opacity(viewModel.repeatMode != .none ? 1.0 : 0.5)
        }
    }
    
    // MARK: - Seek Bar
    private func seekBarSection(width: CGFloat) -> some View {
        VStack(spacing: 4) {
            SeekBar(
                progress: viewModel.progress,
                onSeek: { progress in
                    viewModel.seek(to: progress * viewModel.duration)
                },
                color: skinManager.currentSkin.accentColor,
                backgroundColor: skinManager.currentSkin.displayColor
            )
            .frame(height: 16)
            
            HStack {
                Text(viewModel.formattedCurrentTime)
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.7))
                
                Spacer()
                
                Text(viewModel.formattedDuration)
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.7))
            }
        }
    }
    
    // MARK: - Secondary Controls
    private func secondaryControls(width: CGFloat, isSmall: Bool) -> some View {
        let btnWidth: CGFloat = isSmall ? 50 : 70
        let btnHeight: CGFloat = isSmall ? 32 : 40
        
        return HStack(spacing: max(12, width * 0.03)) {
            // Volume
            VStack(spacing: 4) {
                Image(systemName: "speaker.wave.2")
                    .font(.system(size: 14))
                    .foregroundColor(skinManager.currentSkin.textColor)
                
                VolumeSlider(
                    value: Binding(
                        get: { viewModel.volume },
                        set: { viewModel.volume = $0 }
                    ),
                    color: skinManager.currentSkin.accentColor,
                    backgroundColor: skinManager.currentSkin.displayColor
                )
                .frame(width: max(100, width * 0.25))
            }
            
            Spacer(minLength: 20)
            
            WinampTextButton(title: "PLS", width: btnWidth, height: btnHeight) {
                viewModel.isShowingPlaylist = true
            }
            
            WinampTextButton(title: "EQ", width: btnWidth, height: btnHeight) {
                viewModel.isShowingEqualizer = true
            }
            
            WinampTextButton(title: "VIS", width: btnWidth, height: btnHeight) {
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
