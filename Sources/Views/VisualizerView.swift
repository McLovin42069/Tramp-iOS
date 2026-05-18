import SwiftUI

struct VisualizerView: View {
    @State private var viewModel = PlayerViewModel()
    @State private var skinManager = SkinManager.shared
    @State private var selectedMode: VisualizerMode = .spectrum
    @State private var isFullscreen = false
    
    enum VisualizerMode: String, CaseIterable {
        case spectrum = "Spectrum"
        case waveform = "Waveform"
        case particles = "Particles"
        case scope = "Scope"
        
        var icon: String {
            switch self {
            case .spectrum: return "waveform"
            case .waveform: return "waveform.path.ecg"
            case .particles: return "sparkles"
            case .scope: return "scope"
            }
        }
    }
    
    var body: some View {
        NavigationStack {
            ZStack {
                Color.black
                
                // Visualizer content
                switch selectedMode {
                case .spectrum:
                    SpectrumVisualizer(data: viewModel.spectrumData)
                case .waveform:
                    WaveformVisualizer(data: viewModel.spectrumData)
                case .particles:
                    ParticleVisualizer(data: viewModel.spectrumData)
                case .scope:
                    ScopeVisualizer(data: viewModel.spectrumData)
                }
                
                // Overlay controls
                VStack {
                    HStack {
                        ForEach(VisualizerMode.allCases, id: \.self) { mode in
                            Button(action: { selectedMode = mode }) {
                                VStack(spacing: 2) {
                                    Image(systemName: mode.icon)
                                        .font(.system(size: 14))
                                    Text(mode.rawValue)
                                        .font(.system(size: 8))
                                }
                                .foregroundColor(selectedMode == mode ? skinManager.currentSkin.accentColor : Color.white.opacity(0.5))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(
                                    RoundedRectangle(cornerRadius: 4)
                                        .fill(selectedMode == mode ? Color.white.opacity(0.1) : Color.clear)
                                )
                            }
                            .buttonStyle(PlainButtonStyle())
                        }
                        
                        Spacer()
                        
                        Button(action: { isFullscreen.toggle() }) {
                            Image(systemName: isFullscreen ? "arrow.down.right.and.arrow.up.left" : "arrow.up.left.and.arrow.down.right")
                                .font(.system(size: 16))
                                .foregroundColor(Color.white.opacity(0.7))
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                    .padding(.horizontal, 12)
                    .padding(.top, 12)
                    
                    Spacer()
                    
                    // Track info overlay
                    if let track = viewModel.currentTrack {
                        VStack(spacing: 2) {
                            Text(track.displayTitle)
                                .font(.system(size: 14, weight: .bold))
                                .foregroundColor(Color.white)
                            Text(track.displayArtist)
                                .font(.system(size: 12))
                                .foregroundColor(Color.white.opacity(0.7))
                        }
                        .padding(.bottom, 20)
                        .shadow(color: .black, radius: 4)
                    }
                }
            }
            .navigationBarHidden(true)
        }
    }
}

struct SpectrumVisualizer: View {
    let data: [Float]
    @State private var animationPhase = 0.0
    
    var body: some View {
        Canvas { context, size in
            let barCount = min(data.count, 64)
            let barWidth = size.width / CGFloat(barCount)
            let maxHeight = size.height * 0.8
            
            for i in 0..<barCount {
                let value = CGFloat(i < data.count ? data[i] : 0)
                let x = CGFloat(i) * barWidth
                let barHeight = value * maxHeight
                let y = size.height - barHeight
                
                let hue = Double(i) / Double(barCount)
                let color = Color(hue: hue, saturation: 0.8, brightness: 0.9)
                
                let rect = CGRect(x: x + 1, y: y, width: barWidth - 2, height: barHeight)
                let path = Path(roundedRect: rect, cornerRadius: 2)
                
                context.fill(path, with: .color(color))
                
                // Reflection
                let reflectionRect = CGRect(x: x + 1, y: size.height, width: barWidth - 2, height: barHeight * 0.3)
                let reflectionPath = Path(roundedRect: reflectionRect, cornerRadius: 2)
                context.fill(reflectionPath, with: .color(color.opacity(0.2)))
            }
        }
    }
}

struct WaveformVisualizer: View {
    let data: [Float]
    @State private var phase = 0.0
    
    let timer = Timer.publish(every: 0.05, on: .main, in: .common).autoconnect()
    
    var body: some View {
        Canvas { context, size in
            let path = Path { path in
                let midY = size.height / 2
                let step = size.width / CGFloat(max(data.count, 1))
                
                path.move(to: CGPoint(x: 0, y: midY))
                
                for i in 0..<data.count {
                    let x = CGFloat(i) * step
                    let amplitude = CGFloat(data[i]) * size.height * 0.4
                    let y = midY + sin(Double(i) * 0.2 + phase) * amplitude
                    path.addLine(to: CGPoint(x: x, y: y))
                }
            }
            
            context.stroke(path, with: .color(Color.cyan), lineWidth: 2)
            
            // Second wave
            let path2 = Path { path in
                let midY = size.height / 2
                let step = size.width / CGFloat(max(data.count, 1))
                
                path.move(to: CGPoint(x: 0, y: midY))
                
                for i in 0..<data.count {
                    let x = CGFloat(i) * step
                    let amplitude = CGFloat(data[i]) * size.height * 0.3
                    let y = midY + cos(Double(i) * 0.15 + phase * 1.3) * amplitude
                    path.addLine(to: CGPoint(x: x, y: y))
                }
            }
            
            context.stroke(path2, with: .color(Color.magenta.opacity(0.7)), lineWidth: 1.5)
        }
        .onReceive(timer) { _ in
            phase += 0.1
        }
    }
}

struct ParticleVisualizer: View {
    let data: [Float]
    @State private var particles: [Particle] = []
    let timer = Timer.publish(every: 0.05, on: .main, in: .common).autoconnect()
    
    struct Particle: Identifiable {
        let id = UUID()
        var x: CGFloat
        var y: CGFloat
        var size: CGFloat
        var hue: Double
        var speed: CGFloat
        var life: Double
    }
    
    var body: some View {
        TimelineView(.animation(minimumInterval: 1/30, paused: false)) { _ in
            Canvas { context, size in
                for particle in particles {
                    let rect = CGRect(
                        x: particle.x - particle.size/2,
                        y: particle.y - particle.size/2,
                        width: particle.size,
                        height: particle.size
                    )
                    let path = Path(ellipseIn: rect)
                    context.fill(path, with: .color(Color(hue: particle.hue, saturation: 0.8, brightness: 1.0, opacity: particle.life)))
                }
            }
        }
        .onReceive(timer) { _ in
            updateParticles()
        }
    }
    
    private func updateParticles() {
        let avg = data.reduce(0, +) / Float(data.count)
        
        // Spawn new particles based on audio intensity
        if Double(avg) > 0.3 && particles.count < 100 {
            for _ in 0..<Int(Double(avg) * 5) {
                let particle = Particle(
                    x: CGFloat.random(in: 0...UIScreen.main.bounds.width),
                    y: CGFloat.random(in: UIScreen.main.bounds.height * 0.7...UIScreen.main.bounds.height),
                    size: CGFloat.random(in: 2...8),
                    hue: Double.random(in: 0...1),
                    speed: CGFloat.random(in: 1...5),
                    life: 1.0
                )
                particles.append(particle)
            }
        }
        
        // Update existing particles
        particles = particles.map { particle in
            var p = particle
            p.y -= p.speed
            p.life -= 0.01
            p.size *= 0.99
            return p
        }.filter { $0.life > 0 && $0.y > -20 }
    }
}

struct ScopeVisualizer: View {
    let data: [Float]
    @State private var phase = 0.0
    let timer = Timer.publish(every: 0.03, on: .main, in: .common).autoconnect()
    
    var body: some View {
        Canvas { context, size in
            let centerX = size.width / 2
            let centerY = size.height / 2
            let radius = min(size.width, size.height) * 0.35
            
            // Draw circles
            for i in 0..<5 {
                let r = radius * CGFloat(i + 1) / 5
                let path = Path(ellipseIn: CGRect(
                    x: centerX - r,
                    y: centerY - r,
                    width: r * 2,
                    height: r * 2
                ))
                context.stroke(path, with: .color(Color.green.opacity(0.3)), lineWidth: 1)
            }
            
            // Draw sweep line
            let sweepX = centerX + cos(phase) * radius
            let sweepY = centerY + sin(phase) * radius
            
            let sweepPath = Path { path in
                path.move(to: CGPoint(x: centerX, y: centerY))
                path.addLine(to: CGPoint(x: sweepX, y: sweepY))
            }
            context.stroke(sweepPath, with: .color(Color.green), lineWidth: 2)
            
            // Draw blip
            let avg = data.reduce(0, +) / Float(data.count)
            if Double(avg) > 0.2 {
                let blipR = radius * CGFloat(avg)
                let blipPath = Path(ellipseIn: CGRect(
                    x: centerX + cos(phase) * blipR - 4,
                    y: centerY + sin(phase) * blipR - 4,
                    width: 8,
                    height: 8
                ))
                context.fill(blipPath, with: .color(Color.green))
            }
        }
        .onReceive(timer) { _ in
            phase += 0.05
        }
    }
}
