import SwiftUI

struct OnboardingView: View {
    @State private var currentPage = 0
    @State private var statsManager = StatsManager.shared
    @Environment(\.dismiss) private var dismiss
    
    let pages = [
        OnboardingPage(
            icon: "train.side.front.car",
            title: "Welcome to Tramp",
            description: "The traveler's jukebox. Free music from all corners of the internet, wrapped in nostalgic Winamp style.",
            color: TrampColor.rustOrange
        ),
        OnboardingPage(
            icon: "globe",
            title: "Millions of Free Tracks",
            description: "Jamendo, Internet Archive, Pixabay, and more. All legal, all free, all in one place.",
            color: TrampColor.agedYellow
        ),
        OnboardingPage(
            icon: "radio",
            title: "Tramp Radio",
            description: "Endless intelligent mixing across all sources. Pick your genres and moods, we'll handle the rest.",
            color: TrampColor.neonGreen
        ),
        OnboardingPage(
            icon: "paintbrush",
            title: "Make It Yours",
            description: "Classic skins, visualizers, and that rusty traveler aesthetic. Tramp feels like 1998 but works like 2025.",
            color: TrampColor.deepTeal
        ),
        OnboardingPage(
            icon: "heart",
            title: "Always Free",
            description: "Tramp will always stay 100% free. No ads, no subscriptions. If you enjoy it, feel free to support development.",
            color: TrampColor.retroAmber
        )
    ]
    
    var body: some View {
        ZStack {
            Color(hex: "1A1A2E")
            
            VStack(spacing: 0) {
                Spacer()
                
                // Page content
                VStack(spacing: 24) {
                    ZStack {
                        Circle()
                            .fill(pages[currentPage].color.opacity(0.2))
                            .frame(width: 120, height: 120)
                        
                        Circle()
                            .fill(pages[currentPage].color.opacity(0.1))
                            .frame(width: 160, height: 160)
                        
                        Image(systemName: pages[currentPage].icon)
                            .font(.system(size: 48))
                            .foregroundColor(pages[currentPage].color)
                    }
                    
                    Text(pages[currentPage].title)
                        .font(.system(size: 24, weight: .bold, design: .monospaced))
                        .foregroundColor(.white)
                        .multilineTextAlignment(.center)
                    
                    Text(pages[currentPage].description)
                        .font(.system(size: 15))
                        .foregroundColor(.white.opacity(0.7))
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 32)
                        .frame(height: 80)
                }
                
                Spacer()
                
                // Page indicators
                HStack(spacing: 8) {
                    ForEach(0..<pages.count, id: \.self) { index in
                        Circle()
                            .fill(currentPage == index ? pages[currentPage].color : Color.white.opacity(0.3))
                            .frame(width: currentPage == index ? 10 : 8, height: currentPage == index ? 10 : 8)
                            .animation(.easeInOut, value: currentPage)
                    }
                }
                .padding(.bottom, 24)
                
                // Button
                Button(action: {
                    if currentPage < pages.count - 1 {
                        withAnimation {
                            currentPage += 1
                        }
                    } else {
                        statsManager.completeOnboarding()
                        dismiss()
                    }
                }) {
                    Text(currentPage < pages.count - 1 ? "Next" : "Start Listening")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                        .background(
                            LinearGradient(
                                colors: [pages[currentPage].color, pages[currentPage].color.opacity(0.7)],
                                startPoint: .leading,
                                endPoint: .trailing
                            )
                        )
                        .cornerRadius(8)
                }
                .padding(.horizontal, 32)
                .padding(.bottom, 40)
            }
        }
        .ignoresSafeArea()
    }
}

struct OnboardingPage {
    let icon: String
    let title: String
    let description: String
    let color: Color
}
