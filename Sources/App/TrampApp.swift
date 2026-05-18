import SwiftUI
import CoreData
import AVKit

@main
struct TrampApp: App {
    let persistenceController = PersistenceController.shared
    
    init() {
        // Configure appearance
        configureAppearance()
    }
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(\.managedObjectContext, persistenceController.container.viewContext)
        }
    }
    
    private func configureAppearance() {
        // Tab bar styling
        UITabBar.appearance().backgroundColor = UIColor(Color(hex: "2A1F1D"))
        UITabBar.appearance().unselectedItemTintColor = UIColor(Color(hex: "F5F5DC")).withAlphaComponent(0.5)
        
        // Navigation bar styling
        UINavigationBar.appearance().barTintColor = UIColor(Color(hex: "2A1F1D"))
        UINavigationBar.appearance().titleTextAttributes = [
            .foregroundColor: UIColor(Color(hex: "F5F5DC")),
            .font: UIFont.monospacedSystemFont(ofSize: 17, weight: .bold)
        ]
        
        // Table view styling
        UITableView.appearance().backgroundColor = .clear
        UITableViewCell.appearance().backgroundColor = .clear
    }
}
