import Foundation
import SwiftUI
import AVFoundation

// MARK: - Time Interval Formatting
extension TimeInterval {
    func formattedTime() -> String {
        let totalSeconds = Int(self)
        let minutes = totalSeconds / 60
        let seconds = totalSeconds % 60
        return String(format: "%d:%02d", minutes, seconds)
    }
}

// MARK: - String Helpers
extension String {
    func htmlDecoded() -> String {
        guard let data = self.data(using: .utf8) else { return self }
        let options: [NSAttributedString.DocumentReadingOptionKey: Any] = [
            .documentType: NSAttributedString.DocumentType.html,
            .characterEncoding: String.Encoding.utf8.rawValue
        ]
        guard let attributed = try? NSAttributedString(data: data, options: options, documentAttributes: nil) else {
            return self
        }
        return attributed.string
    }
}

// MARK: - URL Cache Helpers
extension URL {
    func cachedFilePath() -> URL? {
        let filename = self.absoluteString.data(using: .utf8)?.base64EncodedString() ?? UUID().uuidString
        let cacheDir = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first?
            .appendingPathComponent("Tramp/AudioCache", isDirectory: true)
        try? FileManager.default.createDirectory(at: cacheDir!, withIntermediateDirectories: true)
        return cacheDir?.appendingPathComponent(filename)
    }
}

// MARK: - View Modifiers
struct RetroBezelModifier: ViewModifier {
    var isPressed: Bool = false
    var color: Color = .gray
    
    func body(content: Content) -> some View {
        content
            .background(
                ZStack {
                    // Outer shadow
                    RoundedRectangle(cornerRadius: 2)
                        .fill(color.opacity(0.3))
                        .offset(y: 1)
                    
                    // Main metallic body
                    RoundedRectangle(cornerRadius: 2)
                        .fill(
                            LinearGradient(
                                colors: [
                                    color.brightness(0.3),
                                    color,
                                    color.brightness(-0.2)
                                ],
                                startPoint: .top,
                                endPoint: .bottom
                            )
                        )
                    
                    // Top highlight
                    RoundedRectangle(cornerRadius: 2)
                        .stroke(Color.white.opacity(0.4), lineWidth: 1)
                        .padding(0.5)
                    
                    // Bottom shadow
                    RoundedRectangle(cornerRadius: 2)
                        .stroke(Color.black.opacity(0.3), lineWidth: 1)
                        .padding(0.5)
                        .offset(y: 0.5)
                }
            )
            .scaleEffect(isPressed ? 0.97 : 1.0)
            .offset(y: isPressed ? 1 : 0)
    }
}

extension View {
    func retroBezel(isPressed: Bool = false, color: Color = Color(hex: "999999")) -> some View {
        modifier(RetroBezelModifier(isPressed: isPressed, color: color))
    }
}

extension Color {
    func brightness(_ amount: Double) -> Color {
        var hue: CGFloat = 0
        var saturation: CGFloat = 0
        var brightness: CGFloat = 0
        var alpha: CGFloat = 0
        UIColor(self).getHue(&hue, saturation: &saturation, brightness: &brightness, alpha: &alpha)
        return Color(hue: Double(hue), saturation: Double(saturation), brightness: Double(brightness + amount), opacity: Double(alpha))
    }
}

// MARK: - Haptics
enum HapticFeedback {
    static func buttonPress() {
        let generator = UIImpactFeedbackGenerator(style: .light)
        generator.impactOccurred()
    }
    
    static func buttonRelease() {
        let generator = UIImpactFeedbackGenerator(style: .soft)
        generator.impactOccurred()
    }
    
    static func success() {
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.success)
    }
    
    static func error() {
        let generator = UINotificationFeedbackGenerator()
        generator.notificationOccurred(.error)
    }
}
