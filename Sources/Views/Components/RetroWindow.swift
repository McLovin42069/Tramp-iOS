import SwiftUI

struct RetroWindow<Content: View>: View {
    let title: String
    let isDraggable: Bool
    let onClose: (() -> Void)?
    @ViewBuilder let content: Content
    
    var body: some View {
        VStack(spacing: 0) {
            // Title bar
            HStack(spacing: 4) {
                // Window controls
                if let onClose = onClose {
                    Button(action: onClose) {
                        Image(systemName: "xmark")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(SkinManager.shared.currentSkin.textColor)
                            .frame(width: 16, height: 16)
                            .background(
                                RoundedRectangle(cornerRadius: 1)
                                    .fill(Color.red.opacity(0.8))
                            )
                    }
                    .buttonStyle(PlainButtonStyle())
                }
                
                Spacer()
                
                Text(title)
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .foregroundColor(SkinManager.shared.currentSkin.textColor)
                
                Spacer()
                
                // Fake window controls for symmetry
                if onClose != nil {
                    Rectangle()
                        .fill(Color.clear)
                        .frame(width: 16, height: 16)
                }
            }
            .padding(.horizontal, 6)
            .padding(.vertical, 4)
            .background(
                LinearGradient(
                    colors: [
                        SkinManager.shared.currentSkin.bezelColor.brightness(0.2),
                        SkinManager.shared.currentSkin.bezelColor
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
            
            // Content
            content
                .padding(8)
                .background(SkinManager.shared.currentSkin.backgroundColor)
        }
        .cornerRadius(2)
        .overlay(
            RoundedRectangle(cornerRadius: 2)
                .stroke(SkinManager.shared.currentSkin.bezelColor, lineWidth: 2)
        )
        .shadow(color: Color.black.opacity(0.5), radius: 4, x: 2, y: 2)
    }
}

struct RustyTexture: View {
    var opacity: Double = 0.15
    
    var body: some View {
        Canvas { context, size in
            // Draw noise texture
            let rect = CGRect(origin: .zero, size: size)
            
            // Base rust color
            context.fill(Path(rect), with: .color(.clear))
            
            // Random scratches and rust spots
            for _ in 0..<200 {
                let x = CGFloat.random(in: 0...size.width)
                let y = CGFloat.random(in: 0...size.height)
                let w = CGFloat.random(in: 1...50)
                let h = CGFloat.random(in: 0.5...2)
                
                let path = Path(CGRect(x: x, y: y, width: w, height: h))
                let alpha = Double.random(in: 0.1...0.4)
                context.fill(path, with: .color(Color.brown.opacity(alpha * opacity * 4)))
            }
            
            // Corrosion spots
            for _ in 0..<30 {
                let x = CGFloat.random(in: 0...size.width)
                let y = CGFloat.random(in: 0...size.height)
                let r = CGFloat.random(in: 2...15)
                
                let path = Path(ellipseIn: CGRect(x: x-r, y: y-r, width: r*2, height: r*2))
                let alpha = Double.random(in: 0.05...0.2)
                context.fill(path, with: .color(Color.orange.opacity(alpha * opacity * 3)))
            }
        }
    }
}

struct MetallicBezel: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(4)
            .background(
                ZStack {
                    SkinManager.shared.currentSkin.bezelColor
                    
                    // Inner highlight
                    RoundedRectangle(cornerRadius: 1)
                        .stroke(Color.white.opacity(0.2), lineWidth: 1)
                        .padding(1)
                    
                    // Outer shadow
                    RoundedRectangle(cornerRadius: 1)
                        .stroke(Color.black.opacity(0.3), lineWidth: 1)
                }
            )
    }
}

extension View {
    func metallicBezel() -> some View {
        modifier(MetallicBezel())
    }
}
