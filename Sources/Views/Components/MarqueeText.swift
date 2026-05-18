import SwiftUI

struct MarqueeText: View {
    let text: String
    let font: Font
    let color: Color
    let speed: Double
    
    @State private var offset: CGFloat = 0
    @State private var textWidth: CGFloat = 0
    @State private var containerWidth: CGFloat = 0
    @State private var isAnimating = false
    
    var body: some View {
        GeometryReader { geo in
            Text(text)
                .font(font)
                .foregroundColor(color)
                .lineLimit(1)
                .fixedSize()
                .background(
                    GeometryReader { textGeo in
                        Color.clear
                            .onAppear {
                                textWidth = textGeo.size.width
                                containerWidth = geo.size.width
                                startAnimation()
                            }
                            .onChange(of: text) { oldValue, newValue in
                                textWidth = textGeo.size.width
                                startAnimation()
                            }
                    }
                )
                .offset(x: offset)
        }
        .frame(maxWidth: .infinity)
        .clipped()
        .onDisappear {
            isAnimating = false
        }
    }
    
    private func startAnimation() {
        guard textWidth > containerWidth else {
            offset = 0
            return
        }
        
        isAnimating = true
        let totalDistance = textWidth + containerWidth + 20
        let duration = totalDistance / CGFloat(speed)
        
        withAnimation(.linear(duration: duration).repeatForever(autoreverses: false)) {
            offset = -textWidth - 20
        }
    }
}

struct LEDDisplay: View {
    let text: String
    let fontSize: CGFloat
    let color: Color
    let backgroundColor: Color
    
    var body: some View {
        ZStack {
            backgroundColor
            
            Text(text)
                .font(.custom("Courier", size: fontSize))
                .fontWeight(.bold)
                .foregroundColor(color)
                .shadow(color: color.opacity(0.8), radius: 2, x: 0, y: 0)
                .lineLimit(1)
                .minimumScaleFactor(0.5)
        }
    }
}

struct SpectrumAnalyzer: View {
    let data: [Float]
    let barColor: Color
    let backgroundColor: Color
    let barCount: Int = 20
    
    var body: some View {
        Canvas { context, size in
            let barWidth = (size.width - CGFloat(barCount - 1) * 2) / CGFloat(barCount)
            let maxHeight = size.height
            
            // Background
            context.fill(Path(CGRect(origin: .zero, size: size)), with: .color(backgroundColor))
            
            for i in 0..<barCount {
                let value = getValue(for: i)
                let x = CGFloat(i) * (barWidth + 2)
                let barHeight = CGFloat(value) * maxHeight
                let y = size.height - barHeight
                
                let rect = CGRect(x: x, y: y, width: barWidth, height: barHeight)
                let path = Path(roundedRect: rect, cornerRadius: 1)
                
                // Gradient-like coloring based on height
                let intensity = Double(value)
                let color = barColor.opacity(0.3 + intensity * 0.7)
                context.fill(path, with: .color(color))
            }
        }
    }
    
    private func getValue(for index: Int) -> Float {
        guard !data.isEmpty else { return 0 }
        let startIndex = (index * data.count) / barCount
        let endIndex = min(((index + 1) * data.count) / barCount, data.count)
        guard startIndex < endIndex else { return 0 }
        let slice = data[startIndex..<endIndex]
        return slice.reduce(0, +) / Float(slice.count)
    }
}

struct VolumeSlider: View {
    @Binding var value: Float
    let color: Color
    let backgroundColor: Color
    
    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                // Background track
                RoundedRectangle(cornerRadius: 2)
                    .fill(backgroundColor)
                
                // Filled track
                RoundedRectangle(cornerRadius: 2)
                    .fill(color)
                    .frame(width: CGFloat(value) * geo.size.width)
                
                // Knob
                Circle()
                    .fill(Color.white)
                    .frame(width: 12, height: 12)
                    .shadow(radius: 2)
                    .offset(x: CGFloat(value) * geo.size.width - 6)
            }
            .frame(height: 8)
            .gesture(
                DragGesture()
                    .onChanged { gesture in
                        let newValue = Float(gesture.location.x / geo.size.width)
                        value = max(0, min(1, newValue))
                    }
            )
        }
        .frame(height: 20)
    }
}

struct SeekBar: View {
    let progress: Double
    let onSeek: (Double) -> Void
    let color: Color
    let backgroundColor: Color
    
    @State private var isDragging = false
    @State private var dragProgress: Double = 0
    
    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                RoundedRectangle(cornerRadius: 1)
                    .fill(backgroundColor)
                
                RoundedRectangle(cornerRadius: 1)
                    .fill(color)
                    .frame(width: CGFloat(displayProgress) * geo.size.width)
                
                // Position indicator
                Rectangle()
                    .fill(Color.white)
                    .frame(width: 2, height: 12)
                    .offset(x: CGFloat(displayProgress) * geo.size.width - 1)
                    .shadow(color: .black.opacity(0.5), radius: 1)
            }
            .frame(height: 6)
            .gesture(
                DragGesture()
                    .onChanged { gesture in
                        isDragging = true
                        dragProgress = Double(gesture.location.x / geo.size.width)
                    }
                    .onEnded { gesture in
                        let finalProgress = Double(gesture.location.x / geo.size.width)
                        onSeek(max(0, min(1, finalProgress)))
                        isDragging = false
                    }
            )
        }
        .frame(height: 20)
    }
    
    private var displayProgress: Double {
        isDragging ? dragProgress : progress
    }
}
