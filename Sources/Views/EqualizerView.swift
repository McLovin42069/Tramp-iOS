import SwiftUI

struct EqualizerView: View {
    @State private var skinManager = SkinManager.shared
    @State private var bands: [Double] = Array(repeating: 0.5, count: 10)
    @State private var isEnabled = true
    @State private var presets = ["Flat", "Rock", "Pop", "Jazz", "Classical", "Bass", "Treble"]
    @State private var selectedPreset = "Flat"
    
    let frequencies = ["60Hz", "170Hz", "310Hz", "600Hz", "1kHz", "3kHz", "6kHz", "12kHz", "14kHz", "16kHz"]
    
    var body: some View {
        NavigationStack {
            ZStack {
                skinManager.currentSkin.backgroundColor
                RustyTexture(opacity: skinManager.currentSkin.textureOpacity)
                
                VStack(spacing: 12) {
                    // Header
                    HStack {
                        Text("Graphic Equalizer")
                            .font(.system(size: 14, weight: .bold, design: .monospaced))
                            .foregroundColor(skinManager.currentSkin.textColor)
                        
                        Spacer()
                        
                        Toggle("", isOn: $isEnabled)
                            .toggleStyle(SwitchToggleStyle(tint: skinManager.currentSkin.accentColor))
                            .frame(width: 50)
                    }
                    .padding(.horizontal, 12)
                    .padding(.top, 12)
                    
                    // Preset selector
                    Picker("Preset", selection: $selectedPreset) {
                        ForEach(presets, id: \.self) { preset in
                            Text(preset)
                                .font(.system(size: 11, design: .monospaced))
                        }
                    }
                    .pickerStyle(.menu)
                    .tint(skinManager.currentSkin.accentColor)
                    .onChange(of: selectedPreset) { _ in
                        applyPreset()
                    }
                    
                    // EQ Bands
                    HStack(spacing: 8) {
                        ForEach(0..<10, id: \.self) { index in
                            EQBand(
                                frequency: frequencies[index],
                                value: $bands[index],
                                color: skinManager.currentSkin.accentColor,
                                isEnabled: isEnabled
                            )
                        }
                    }
                    .padding(.horizontal, 8)
                    
                    Spacer()
                    
                    // Pre-amp
                    VStack(spacing: 4) {
                        Text("PREAMP")
                            .font(.system(size: 9, weight: .bold, design: .monospaced))
                            .foregroundColor(skinManager.currentSkin.textColor.opacity(0.7))
                        
                        HStack {
                            Text("-12dB")
                                .font(.system(size: 8, design: .monospaced))
                                .foregroundColor(skinManager.currentSkin.textColor.opacity(0.5))
                            
                            Slider(value: .constant(0.5), in: 0...1)
                                .tint(skinManager.currentSkin.accentColor)
                            
                            Text("+12dB")
                                .font(.system(size: 8, design: .monospaced))
                                .foregroundColor(skinManager.currentSkin.textColor.opacity(0.5))
                        }
                    }
                    .padding(.horizontal, 12)
                    .padding(.bottom, 12)
                }
            }
            .navigationBarHidden(true)
        }
    }
    
    private func applyPreset() {
        switch selectedPreset {
        case "Rock":
            bands = [0.7, 0.6, 0.5, 0.4, 0.5, 0.7, 0.8, 0.7, 0.6, 0.5]
        case "Pop":
            bands = [0.5, 0.4, 0.4, 0.5, 0.7, 0.7, 0.6, 0.5, 0.4, 0.3]
        case "Jazz":
            bands = [0.5, 0.6, 0.6, 0.5, 0.4, 0.5, 0.6, 0.7, 0.6, 0.5]
        case "Classical":
            bands = [0.6, 0.5, 0.4, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.7]
        case "Bass":
            bands = [0.9, 0.8, 0.6, 0.4, 0.3, 0.3, 0.3, 0.3, 0.3, 0.2]
        case "Treble":
            bands = [0.2, 0.3, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.9]
        default:
            bands = Array(repeating: 0.5, count: 10)
        }
    }
}

struct EQBand: View {
    let frequency: String
    @Binding var value: Double
    let color: Color
    let isEnabled: Bool
    
    var body: some View {
        VStack(spacing: 4) {
            // + label
            Text("+")
                .font(.system(size: 8, weight: .bold))
                .foregroundColor(color.opacity(isEnabled ? 0.7 : 0.3))
            
            // Slider
            GeometryReader { geo in
                ZStack(alignment: .bottom) {
                    // Background track
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color.black.opacity(0.5))
                    
                    // Fill
                    RoundedRectangle(cornerRadius: 2)
                        .fill(color.opacity(isEnabled ? 0.8 : 0.3))
                        .frame(height: CGFloat(value) * geo.size.height)
                }
                .gesture(
                    DragGesture()
                        .onChanged { gesture in
                            if isEnabled {
                                let newValue = 1.0 - (gesture.location.y / geo.size.height)
                                value = max(0, min(1, newValue))
                            }
                        }
                )
            }
            .frame(width: 20)
            
            // - label
            Text("-")
                .font(.system(size: 8, weight: .bold))
                .foregroundColor(color.opacity(isEnabled ? 0.7 : 0.3))
            
            // Frequency label
            Text(frequency)
                .font(.system(size: 7, design: .monospaced))
                .foregroundColor(Color.white.opacity(0.5))
                .rotationEffect(.degrees(-45))
                .frame(height: 20)
        }
    }
}
