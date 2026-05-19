import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    @State private var skinManager = SkinManager.shared
    @State private var showOnboarding = false
    @State private var statsManager = StatsManager.shared
    
    private let tabs = [
        TabItem(icon: "play.circle.fill", label: "Player", tag: 0),
        TabItem(icon: "magnifyingglass", label: "Search", tag: 1),
        TabItem(icon: "antenna.radiowaves.left.and.right", label: "Radio", tag: 2),
        TabItem(icon: "square.stack.3d.up", label: "Library", tag: 3),
        TabItem(icon: "gearshape.fill", label: "Settings", tag: 4)
    ]
    
    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .bottom) {
                // Main content
                TabView(selection: $selectedTab) {
                    MainPlayerView()
                        .tag(0)
                    
                    SearchView()
                        .tag(1)
                    
                    RadioView()
                        .tag(2)
                    
                    LibraryView()
                        .tag(3)
                    
                    SettingsView()
                        .tag(4)
                }
                .tabViewStyle(.page(indexDisplayMode: .never))
                
                // Custom Tab Bar
                VStack(spacing: 0) {
                    Divider()
                        .background(skinManager.currentSkin.bezelColor.opacity(0.5))
                    
                    HStack(spacing: 0) {
                        ForEach(tabs) { tab in
                            TabButton(
                                icon: tab.icon,
                                label: tab.label,
                                isSelected: selectedTab == tab.tag,
                                accentColor: skinManager.currentSkin.accentColor,
                                textColor: skinManager.currentSkin.textColor
                            ) {
                                withAnimation(.easeInOut(duration: 0.15)) {
                                    selectedTab = tab.tag
                                }
                            }
                            .frame(maxWidth: .infinity)
                        }
                    }
                    .padding(.horizontal, 8)
                    .padding(.top, 8)
                    .padding(.bottom, max(8, geo.safeAreaInsets.bottom))
                    .background(
                        skinManager.currentSkin.backgroundColor
                            .opacity(0.95)
                            .background(.ultraThinMaterial)
                    )
                }
            }
        }
        .ignoresSafeArea(edges: .bottom)
        .onAppear {
            showOnboarding = !statsManager.currentStats.onboardingCompleted
        }
        .fullScreenCover(isPresented: $showOnboarding) {
            OnboardingView()
        }
    }
}

// MARK: - Tab Models

struct TabItem: Identifiable {
    let id = UUID()
    let icon: String
    let label: String
    let tag: Int
}

struct TabButton: View {
    let icon: String
    let label: String
    let isSelected: Bool
    let accentColor: Color
    let textColor: Color
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Image(systemName: icon)
                    .font(.system(size: isSelected ? 22 : 20, weight: isSelected ? .semibold : .regular))
                    .foregroundColor(isSelected ? accentColor : textColor.opacity(0.6))
                    .frame(height: 24)
                
                Text(label)
                    .font(.system(size: 10, weight: isSelected ? .semibold : .medium))
                    .foregroundColor(isSelected ? accentColor : textColor.opacity(0.6))
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 4)
            .contentShape(Rectangle())
        }
        .buttonStyle(PlainButtonStyle())
    }
}
