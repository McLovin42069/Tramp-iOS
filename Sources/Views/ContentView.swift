import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    @State private var skinManager = SkinManager.shared
    @State private var showOnboarding = false
    @State private var statsManager = StatsManager.shared
    
    var body: some View {
        TabView(selection: $selectedTab) {
            MainPlayerView()
                .tabItem {
                    Image(systemName: "play.circle.fill")
                    Text("Player")
                }
                .tag(0)
            
            SearchView()
                .tabItem {
                    Image(systemName: "magnifyingglass")
                    Text("Search")
                }
                .tag(1)
            
            RadioView()
                .tabItem {
                    Image(systemName: "antenna.radiowaves.left.and.right")
                    Text("Radio")
                }
                .tag(2)
            
            LibraryView()
                .tabItem {
                    Image(systemName: "square.stack.3d.up")
                    Text("Library")
                }
                .tag(3)
            
            SettingsView()
                .tabItem {
                    Image(systemName: "gearshape.fill")
                    Text("Settings")
                }
                .tag(4)
        }
        .tint(skinManager.currentSkin.accentColor)
        .onAppear {
            // Check if onboarding is needed
            showOnboarding = !statsManager.currentStats.onboardingCompleted
        }
        .fullScreenCover(isPresented: $showOnboarding) {
            OnboardingView()
        }
    }
}
