import SwiftUI

struct RadioView: View {
    @State private var viewModel = RadioViewModel()
    @State private var skinManager = SkinManager.shared
    @State private var playerVM = PlayerViewModel()
    @State private var showGenrePicker = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                skinManager.currentSkin.backgroundColor
                RustyTexture(opacity: skinManager.currentSkin.textureOpacity)
                
                VStack(spacing: 0) {
                    // Radio Header
                    radioHeader
                    
                    // Main Radio Display
                    mainDisplay
                        .padding(.horizontal, 12)
                        .padding(.vertical, 16)
                    
                    // Genre / Mood Selector
                    genreSelector
                        .padding(.horizontal, 12)
                    
                    Spacer()
                    
                    // Controls
                    controlsSection
                        .padding(.horizontal, 12)
                        .padding(.bottom, 20)
                }
            }
            .navigationTitle("Tramp Radio")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
    
    private var radioHeader: some View {
        HStack {
            Image(systemName: "antenna.radiowaves.left.and.right")
                .font(.system(size: 16))
                .foregroundColor(skinManager.currentSkin.accentColor)
            
            Text("Tramp Radio")
                .font(.system(size: 14, weight: .bold, design: .monospaced))
                .foregroundColor(skinManager.currentSkin.textColor)
            
            Spacer()
            
            if viewModel.isLoading {
                ProgressView()
                    .progressViewStyle(CircularProgressViewStyle(tint: skinManager.currentSkin.accentColor))
                    .scaleEffect(0.8)
            }
            
            if viewModel.isPlaying {
                // Animated "LIVE" indicator
                LiveIndicator()
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(
            LinearGradient(
                colors: [
                    skinManager.currentSkin.bezelColor.brightness(0.2),
                    skinManager.currentSkin.bezelColor
                ],
                startPoint: .top,
                endPoint: .bottom
            )
        )
    }
    
    private var mainDisplay: some View {
        VStack(spacing: 16) {
            // Big radio dial visualization
            ZStack {
                Circle()
                    .stroke(skinManager.currentSkin.bezelColor, lineWidth: 4)
                    .frame(width: 180, height: 180)
                
                Circle()
                    .fill(skinManager.currentSkin.displayColor)
                    .frame(width: 170, height: 170)
                
                // Frequency markers
                ForEach(0..<12) { i in
                    let angle = Double(i) * .pi / 6
                    Rectangle()
                        .fill(skinManager.currentSkin.ledColor.opacity(0.5))
                        .frame(width: 2, height: 10)
                        .offset(
                            x: cos(angle) * 75,
                            y: sin(angle) * 75
                        )
                }
                
                // Needle
                Rectangle()
                    .fill(skinManager.currentSkin.accentColor)
                    .frame(width: 2, height: 60)
                    .offset(y: -30)
                    .rotationEffect(.degrees(viewModel.isPlaying ? Double.random(in: -30...30) : 0))
                    .animation(.easeInOut(duration: 2), value: viewModel.isPlaying)
                
                // Center knob
                Circle()
                    .fill(skinManager.currentSkin.buttonColor)
                    .frame(width: 24, height: 24)
                    .overlay(
                        Circle()
                            .stroke(skinManager.currentSkin.bezelColor, lineWidth: 2)
                    )
            }
            
            // Track info
            if let track = viewModel.currentTrack {
                VStack(spacing: 4) {
                    MarqueeText(
                        text: track.displayTitle,
                        font: .system(size: 16, weight: .bold, design: .monospaced),
                        color: skinManager.currentSkin.ledColor,
                        speed: 30
                    )
                    .frame(height: 22)
                    
                    Text(track.displayArtist)
                        .font(.system(size: 12))
                        .foregroundColor(skinManager.currentSkin.textColor.opacity(0.7))
                }
            } else {
                VStack(spacing: 4) {
                    Text("Tramp Radio")
                        .font(.system(size: 16, weight: .bold, design: .monospaced))
                        .foregroundColor(skinManager.currentSkin.ledColor)
                    
                    Text("Endless free music")
                        .font(.system(size: 12))
                        .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                }
            }
            
            // Source badge
            HStack(spacing: 8) {
                if let track = viewModel.currentTrack {
                    HStack(spacing: 4) {
                        Image(systemName: track.source.icon)
                            .font(.system(size: 8))
                        Text(track.source.rawValue)
                            .font(.system(size: 9))
                    }
                    .foregroundColor(Color(hex: track.source.color))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(
                        Capsule()
                            .fill(Color(hex: track.source.color).opacity(0.15))
                    )
                }
                
                Text(viewModel.currentGenreLabel)
                    .font(.system(size: 9, design: .monospaced))
                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.5))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(
                        Capsule()
                            .fill(skinManager.currentSkin.buttonColor.opacity(0.3))
                    )
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 4)
                .fill(skinManager.currentSkin.displayColor.opacity(0.5))
                .overlay(
                    RoundedRectangle(cornerRadius: 4)
                        .stroke(skinManager.currentSkin.bezelColor, lineWidth: 2)
                )
        )
    }
    
    private var genreSelector: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("GENRES")
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
            
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(MusicGenre.allCases) { genre in
                        let isSelected = viewModel.selectedGenres.contains(genre)
                        Button(action: {
                            if genre == .any {
                                viewModel.selectedGenres = [.any]
                            } else {
                                viewModel.selectedGenres.removeAll { $0 == .any }
                                if isSelected {
                                    viewModel.selectedGenres.removeAll { $0 == genre }
                                    if viewModel.selectedGenres.isEmpty {
                                        viewModel.selectedGenres = [.any]
                                    }
                                } else {
                                    viewModel.selectedGenres.append(genre)
                                }
                            }
                        }) {
                            Text(genre.rawValue)
                                .font(.system(size: 11, weight: isSelected ? .bold : .medium))
                                .foregroundColor(isSelected ? skinManager.currentSkin.backgroundColor : skinManager.currentSkin.textColor)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(
                                    RoundedRectangle(cornerRadius: 4)
                                        .fill(isSelected ? skinManager.currentSkin.accentColor : skinManager.currentSkin.buttonColor.opacity(0.3))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 4)
                                                .stroke(isSelected ? skinManager.currentSkin.accentColor : skinManager.currentSkin.bezelColor, lineWidth: 1)
                                        )
                                )
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
            }
            
            Text("MOOD")
                .font(.system(size: 10, weight: .bold, design: .monospaced))
                .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                .padding(.top, 4)
            
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(MusicMood.allCases) { mood in
                        let isSelected = viewModel.selectedMood == mood
                        Button(action: { viewModel.selectedMood = mood }) {
                            Text(mood.rawValue)
                                .font(.system(size: 11, weight: isSelected ? .bold : .medium))
                                .foregroundColor(isSelected ? skinManager.currentSkin.backgroundColor : skinManager.currentSkin.textColor)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 6)
                                .background(
                                    RoundedRectangle(cornerRadius: 4)
                                        .fill(isSelected ? skinManager.currentSkin.accentColor : skinManager.currentSkin.buttonColor.opacity(0.3))
                                )
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                }
            }
        }
    }
    
    private var controlsSection: some View {
        HStack(spacing: 20) {
            // Thumbs down
            WinampButton(icon: "hand.thumbsdown", size: 40) {
                viewModel.thumbsDown()
            }
            
            // Play / Pause
            WinampButton(icon: viewModel.isPlaying ? "pause.fill" : "play.fill", size: 56) {
                if viewModel.isPlaying {
                    viewModel.stopRadio()
                } else {
                    Task { await viewModel.startRadio() }
                }
            }
            
            // Thumbs up
            WinampButton(icon: "hand.thumbsup", size: 40) {
                viewModel.thumbsUp()
            }
            
            // Skip
            WinampButton(icon: "forward.end.fill", size: 36) {
                viewModel.skipTrack()
            }
        }
        .padding(.vertical, 12)
        .background(
            RoundedRectangle(cornerRadius: 4)
                .fill(skinManager.currentSkin.bezelColor.opacity(0.5))
        )
    }
}

struct LiveIndicator: View {
    @State private var isVisible = true
    let timer = Timer.publish(every: 0.8, on: .main, in: .common).autoconnect()
    
    var body: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(Color.red)
                .frame(width: 6, height: 6)
                .opacity(isVisible ? 1 : 0.3)
            
            Text("LIVE")
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .foregroundColor(Color.red)
                .opacity(isVisible ? 1 : 0.5)
        }
        .onReceive(timer) { _ in
            isVisible.toggle()
        }
    }
}
