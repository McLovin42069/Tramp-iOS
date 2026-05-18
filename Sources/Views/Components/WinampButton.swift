import SwiftUI

struct WinampButton: View {
    let icon: String
    let size: CGFloat
    let action: () -> Void
    
    @State private var isPressed = false
    
    var body: some View {
        Button(action: {
            HapticFeedback.buttonPress()
            action()
        }) {
            Image(systemName: icon)
                .font(.system(size: size * 0.5, weight: .bold))
                .foregroundColor(SkinManager.shared.currentSkin.textColor)
                .frame(width: size, height: size)
                .background(
                    ZStack {
                        // Outer shadow
                        RoundedRectangle(cornerRadius: 2)
                            .fill(Color.black.opacity(0.3))
                            .offset(y: isPressed ? 0 : 1)
                        
                        // Main button face
                        RoundedRectangle(cornerRadius: 2)
                            .fill(
                                LinearGradient(
                                    colors: [
                                        SkinManager.shared.currentSkin.buttonColor.brightness(0.3),
                                        SkinManager.shared.currentSkin.buttonColor,
                                        SkinManager.shared.currentSkin.buttonColor.brightness(-0.2)
                                    ],
                                    startPoint: .top,
                                    endPoint: .bottom
                                )
                            )
                        
                        // Top highlight
                        RoundedRectangle(cornerRadius: 2)
                            .stroke(Color.white.opacity(0.3), lineWidth: 1)
                            .padding(0.5)
                        
                        // Inner shadow when pressed
                        if isPressed {
                            RoundedRectangle(cornerRadius: 2)
                                .fill(Color.black.opacity(0.2))
                        }
                    }
                )
                .scaleEffect(isPressed ? 0.95 : 1.0)
        }
        .buttonStyle(PlainButtonStyle())
        .pressEvents {
            withAnimation(.easeInOut(duration: 0.05)) {
                isPressed = true
            }
        } onRelease: {
            withAnimation(.easeInOut(duration: 0.05)) {
                isPressed = false
            }
        }
    }
}

struct WinampTextButton: View {
    let title: String
    let width: CGFloat
    let height: CGFloat
    let action: () -> Void
    
    @State private var isPressed = false
    
    var body: some View {
        Button(action: {
            HapticFeedback.buttonPress()
            action()
        }) {
            Text(title)
                .font(.system(size: 11, weight: .bold, design: .monospaced))
                .foregroundColor(SkinManager.shared.currentSkin.textColor)
                .frame(width: width, height: height)
                .background(
                    ZStack {
                        RoundedRectangle(cornerRadius: 2)
                            .fill(Color.black.opacity(0.3))
                            .offset(y: isPressed ? 0 : 1)
                        
                        RoundedRectangle(cornerRadius: 2)
                            .fill(
                                LinearGradient(
                                    colors: [
                                        SkinManager.shared.currentSkin.buttonColor.brightness(0.3),
                                        SkinManager.shared.currentSkin.buttonColor,
                                        SkinManager.shared.currentSkin.buttonColor.brightness(-0.2)
                                    ],
                                    startPoint: .top,
                                    endPoint: .bottom
                                )
                            )
                        
                        RoundedRectangle(cornerRadius: 2)
                            .stroke(Color.white.opacity(0.3), lineWidth: 1)
                            .padding(0.5)
                        
                        if isPressed {
                            RoundedRectangle(cornerRadius: 2)
                                .fill(Color.black.opacity(0.2))
                        }
                    }
                )
                .scaleEffect(isPressed ? 0.95 : 1.0)
        }
        .buttonStyle(PlainButtonStyle())
        .pressEvents {
            withAnimation(.easeInOut(duration: 0.05)) {
                isPressed = true
            }
        } onRelease: {
            withAnimation(.easeInOut(duration: 0.05)) {
                isPressed = false
            }
        }
    }
}

// MARK: - Press Events Modifier
struct PressEventsModifier: ViewModifier {
    var onPress: () -> Void
    var onRelease: () -> Void
    
    func body(content: Content) -> some View {
        content
            .simultaneousGesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { _ in
                        onPress()
                    }
                    .onEnded { _ in
                        onRelease()
                    }
            )
    }
}

extension View {
    func pressEvents(onPress: @escaping () -> Void, onRelease: @escaping () -> Void) -> some View {
        modifier(PressEventsModifier(onPress: onPress, onRelease: onRelease))
    }
}
