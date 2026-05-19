import SwiftUI
import StoreKit

struct SettingsView: View {
    @State private var viewModel = SettingsViewModel()
    @State private var skinManager = SkinManager.shared
    @State private var showResetConfirmation = false
    @State private var showDonationSheet = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                skinManager.currentSkin.backgroundColor
                RustyTexture(opacity: skinManager.currentSkin.textureOpacity)
                
                ScrollView {
                    VStack(spacing: 20) {
                        // Stats Section
                        statsSection
                        
                        // Playback Section
                        settingsSection(title: "Playback") {
                            ToggleRow(icon: "play.circle", title: "Background Playback", isOn: $viewModel.backgroundPlaybackEnabled)
                            ToggleRow(icon: "arrow.left.arrow.right", title: "Crossfade", isOn: $viewModel.crossfadeEnabled)
                            
                            if viewModel.crossfadeEnabled {
                                VStack(alignment: .leading, spacing: 8) {
                                    HStack {
                                        Text("Crossfade Duration")
                                            .font(.system(size: 14))
                                            .foregroundColor(skinManager.currentSkin.textColor)
                                        Spacer()
                                        Text("\(Int(viewModel.crossfadeDuration))s")
                                            .font(.system(size: 13, design: .monospaced))
                                            .foregroundColor(skinManager.currentSkin.accentColor)
                                    }
                                    Slider(value: $viewModel.crossfadeDuration, in: 0.5...5, step: 0.5)
                                        .tint(skinManager.currentSkin.accentColor)
                                }
                                .padding(.leading, 32)
                            }
                            
                            ToggleRow(icon: "arrow.down.circle", title: "Auto-Cache Streams", isOn: $viewModel.autoCacheEnabled)
                            
                            HStack {
                                Text("Cache Size")
                                    .font(.system(size: 14))
                                    .foregroundColor(skinManager.currentSkin.textColor)
                                Spacer()
                                Text(String(format: "%.1f MB", viewModel.cacheSizeMB))
                                    .font(.system(size: 13, design: .monospaced))
                                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                            }
                            
                            Button(action: { viewModel.clearCache() }) {
                                HStack {
                                    Image(systemName: "trash")
                                        .font(.system(size: 14))
                                    Text("Clear Cache")
                                        .font(.system(size: 14))
                                    Spacer()
                                }
                                .foregroundColor(skinManager.currentSkin.accentColor)
                            }
                        }
                        
                        // Appearance Section
                        settingsSection(title: "Appearance") {
                            skinRow(skin: .classic)
                            skinRow(skin: .rustyRoad)
                        }
                        
                        // Premium Skins
                        if !Skin.allSkins.filter({ $0.isPremium }).isEmpty {
                            settingsSection(title: "Premium Skins") {
                                ForEach(Skin.allSkins.filter { $0.isPremium }) { skin in
                                    premiumSkinRow(skin: skin)
                                }
                            }
                        }
                        
                        // Support Section
                        settingsSection(title: "Support Tramp") {
                            Text("Tramp will always stay 100% free. No ads, no subscriptions. If you enjoy it, feel free to support development.")
                                .font(.system(size: 12))
                                .foregroundColor(skinManager.currentSkin.textColor.opacity(0.7))
                                .padding(.bottom, 4)
                            
                            supportButton(icon: "heart.fill", title: "Tip via Apple", color: .red) {
                                showDonationSheet = true
                            }
                            
                            supportButton(icon: "cup.and.saucer.fill", title: "Buy Me a Coffee", color: Color(hex: "FFDD00")) {
                                if let url = URL(string: "https://buymeacoffee.com/tramp") {
                                    UIApplication.shared.open(url)
                                }
                            }
                            
                            supportButton(icon: "mug.fill", title: "Ko-fi", color: Color(hex: "FF5E5B")) {
                                if let url = URL(string: "https://ko-fi.com/tramp") {
                                    UIApplication.shared.open(url)
                                }
                            }
                        }
                        
                        // About Section
                        settingsSection(title: "About") {
                            HStack {
                                Text("Version")
                                    .font(.system(size: 14))
                                    .foregroundColor(skinManager.currentSkin.textColor)
                                Spacer()
                                Text("1.0.0")
                                    .font(.system(size: 13, design: .monospaced))
                                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                            }
                            
                            Button(action: {
                                if let url = URL(string: "https://tramp.app/privacy") {
                                    UIApplication.shared.open(url)
                                }
                            }) {
                                HStack {
                                    Text("Privacy Policy")
                                        .font(.system(size: 14))
                                    Spacer()
                                    Image(systemName: "arrow.up.right")
                                        .font(.system(size: 12))
                                }
                                .foregroundColor(skinManager.currentSkin.accentColor)
                            }
                            
                            Button(action: {
                                if let url = URL(string: "https://tramp.app/licenses") {
                                    UIApplication.shared.open(url)
                                }
                            }) {
                                HStack {
                                    Text("Open Source Licenses")
                                        .font(.system(size: 14))
                                    Spacer()
                                    Image(systemName: "arrow.up.right")
                                        .font(.system(size: 12))
                                }
                                .foregroundColor(skinManager.currentSkin.accentColor)
                            }
                        }
                        
                        // Danger Zone
                        settingsSection(title: "Danger Zone") {
                            Button(action: { showResetConfirmation = true }) {
                                HStack {
                                    Image(systemName: "exclamationmark.triangle.fill")
                                        .font(.system(size: 14))
                                    Text("Reset All Stats")
                                        .font(.system(size: 14))
                                    Spacer()
                                }
                                .foregroundColor(.red)
                            }
                        }
                        
                        Spacer(minLength: 40)
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 16)
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .onAppear {
                viewModel.refreshStats()
                viewModel.calculateCacheSize()
            }
            .confirmationDialog("Reset Stats?", isPresented: $showResetConfirmation, titleVisibility: .visible) {
                Button("Reset", role: .destructive) {
                    viewModel.resetStats()
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This will erase all your listening stats, streaks, and badges. This cannot be undone.")
            }
            .sheet(isPresented: $showDonationSheet) {
                DonationView()
            }
        }
    }
    
    // MARK: - Sections
    
    private func settingsSection<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.system(size: 13, weight: .bold, design: .monospaced))
                .foregroundColor(skinManager.currentSkin.accentColor)
                .textCase(.uppercase)
            
            VStack(spacing: 0) {
                content()
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(skinManager.currentSkin.displayColor.opacity(0.3))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(skinManager.currentSkin.bezelColor.opacity(0.3), lineWidth: 1)
                    )
            )
        }
    }
    
    // MARK: - Stats Section
    
    private var statsSection: some View {
        VStack(spacing: 16) {
            HStack(spacing: 20) {
                VStack(spacing: 4) {
                    Text("\(viewModel.stats.level)")
                        .font(.system(size: 36, weight: .bold, design: .monospaced))
                        .foregroundColor(skinManager.currentSkin.ledColor)
                    Text(viewModel.stats.levelTitle)
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(skinManager.currentSkin.accentColor)
                }
                .frame(width: 90)
                
                VStack(alignment: .leading, spacing: 6) {
                    Text("Level \(viewModel.stats.level)")
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(skinManager.currentSkin.textColor)
                    
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            RoundedRectangle(cornerRadius: 3)
                                .fill(skinManager.currentSkin.displayColor)
                                .frame(height: 10)
                            
                            RoundedRectangle(cornerRadius: 3)
                                .fill(skinManager.currentSkin.accentColor)
                                .frame(width: max(4, CGFloat(viewModel.nextLevelProgress) * geo.size.width), height: 10)
                        }
                    }
                    .frame(height: 10)
                    
                    Text("\(Int(viewModel.stats.xp)) / \(Int(viewModel.nextLevelXP)) XP")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                }
            }
            
            HStack(spacing: 20) {
                StatBadge(icon: "clock", value: viewModel.formattedTotalTime, label: "Listened")
                StatBadge(icon: "speedometer", value: viewModel.formattedMiles, label: "Miles")
                StatBadge(icon: "flame", value: "\(viewModel.stats.currentStreakDays)d", label: "Streak")
            }
            
            if !viewModel.stats.badges.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 10) {
                        ForEach(viewModel.stats.badges.prefix(5)) { badge in
                            VStack(spacing: 4) {
                                Image(systemName: badge.icon)
                                    .font(.system(size: 18))
                                    .foregroundColor(skinManager.currentSkin.accentColor)
                                Text(badge.name)
                                    .font(.system(size: 9))
                                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.7))
                            }
                            .frame(width: 64, height: 64)
                            .background(
                                RoundedRectangle(cornerRadius: 6)
                                    .fill(skinManager.currentSkin.buttonColor.opacity(0.3))
                            )
                        }
                    }
                }
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(skinManager.currentSkin.displayColor.opacity(0.3))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(skinManager.currentSkin.bezelColor.opacity(0.3), lineWidth: 1)
                )
        )
    }
    
    // MARK: - Skin Rows
    
    private func skinRow(skin: Skin) -> some View {
        Button(action: { skinManager.selectSkin(skin) }) {
            HStack(spacing: 12) {
                RoundedRectangle(cornerRadius: 4)
                    .fill(skin.backgroundColor)
                    .frame(width: 32, height: 32)
                    .overlay(
                        RoundedRectangle(cornerRadius: 4)
                            .stroke(skin.bezelColor, lineWidth: 2)
                    )
                
                VStack(alignment: .leading, spacing: 2) {
                    Text(skin.name)
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(skinManager.currentSkin.textColor)
                    Text(skin.description)
                        .font(.system(size: 11))
                        .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                        .lineLimit(1)
                }
                
                Spacer()
                
                if skinManager.currentSkin.id == skin.id {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 18))
                        .foregroundColor(skinManager.currentSkin.accentColor)
                }
            }
            .padding(.vertical, 6)
        }
        .buttonStyle(PlainButtonStyle())
    }
    
    private func premiumSkinRow(skin: Skin) -> some View {
        Button(action: {
            if skinManager.isUnlocked(skin) {
                skinManager.selectSkin(skin)
            }
        }) {
            HStack(spacing: 12) {
                RoundedRectangle(cornerRadius: 4)
                    .fill(skin.backgroundColor)
                    .frame(width: 32, height: 32)
                    .overlay(
                        RoundedRectangle(cornerRadius: 4)
                            .stroke(skin.bezelColor, lineWidth: 2)
                    )
                
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 6) {
                        Text(skin.name)
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(skinManager.currentSkin.textColor)
                        
                        if skin.isPremium && !skinManager.isUnlocked(skin) {
                            Text("PREMIUM")
                                .font(.system(size: 8, weight: .bold))
                                .foregroundColor(skinManager.currentSkin.backgroundColor)
                                .padding(.horizontal, 5)
                                .padding(.vertical, 2)
                                .background(
                                    Capsule()
                                        .fill(skinManager.currentSkin.accentColor)
                                )
                        }
                    }
                    
                    Text(skin.description)
                        .font(.system(size: 11))
                        .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                        .lineLimit(1)
                }
                
                Spacer()
                
                if skinManager.isUnlocked(skin) {
                    if skinManager.currentSkin.id == skin.id {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(skinManager.currentSkin.accentColor)
                    } else {
                        Text("Unlocked")
                            .font(.system(size: 11))
                            .foregroundColor(skinManager.currentSkin.accentColor)
                    }
                } else {
                    Text(skin.price ?? "")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundColor(skinManager.currentSkin.accentColor)
                }
            }
            .padding(.vertical, 6)
        }
        .buttonStyle(PlainButtonStyle())
    }
    
    // MARK: - Support Button
    
    private func supportButton(icon: String, title: String, color: Color, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                    .foregroundColor(color)
                Text(title)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(skinManager.currentSkin.textColor)
                Spacer()
                Image(systemName: "arrow.up.right")
                    .font(.system(size: 12))
                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.4))
            }
            .padding(.vertical, 6)
        }
        .buttonStyle(PlainButtonStyle())
    }
}

// MARK: - Toggle Row

struct ToggleRow: View {
    let icon: String
    let title: String
    @Binding var isOn: Bool
    
    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 14))
                .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.7))
                .frame(width: 22)
            
            Text(title)
                .font(.system(size: 14))
                .foregroundColor(SkinManager.shared.currentSkin.textColor)
            
            Spacer()
            
            Toggle("", isOn: $isOn)
                .labelsHidden()
                .tint(SkinManager.shared.currentSkin.accentColor)
        }
        .padding(.vertical, 6)
    }
}

// MARK: - Stat Badge

struct StatBadge: View {
    let icon: String
    let value: String
    let label: String
    
    var body: some View {
        VStack(spacing: 4) {
            Image(systemName: icon)
                .font(.system(size: 16))
                .foregroundColor(SkinManager.shared.currentSkin.accentColor)
            Text(value)
                .font(.system(size: 13, weight: .bold, design: .monospaced))
                .foregroundColor(SkinManager.shared.currentSkin.textColor)
            Text(label)
                .font(.system(size: 10))
                .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.6))
        }
        .frame(maxWidth: .infinity)
    }
}

// MARK: - Donation View

struct DonationView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var selectedAmount: Double? = nil
    let amounts = [1.99, 4.99, 9.99, 19.99]
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Image(systemName: "heart.fill")
                    .font(.system(size: 48))
                    .foregroundColor(.red)
                    .padding(.top, 24)
                
                Text("Support Tramp")
                    .font(.system(size: 22, weight: .bold))
                
                Text("Tramp will always be free. Your tip helps keep the lights on and the music flowing.")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 24)
                
                VStack(spacing: 12) {
                    ForEach(amounts, id: \.self) { amount in
                        Button(action: { selectedAmount = amount }) {
                            HStack {
                                Text("Tip \(String(format: "%.2f", amount))")
                                    .font(.system(size: 16, weight: .medium))
                                Spacer()
                                if selectedAmount == amount {
                                    Image(systemName: "checkmark.circle.fill")
                                        .foregroundColor(.green)
                                }
                            }
                            .padding()
                            .background(
                                RoundedRectangle(cornerRadius: 8)
                                    .fill(selectedAmount == amount ? Color.green.opacity(0.1) : Color.gray.opacity(0.1))
                                    .overlay(
                                        RoundedRectangle(cornerRadius: 8)
                                            .stroke(selectedAmount == amount ? Color.green : Color.gray.opacity(0.3), lineWidth: 1)
                                    )
                            )
                        }
                        .buttonStyle(PlainButtonStyle())
                        .foregroundColor(.primary)
                    }
                }
                .padding(.horizontal, 24)
                
                Spacer()
                
                Button("Maybe Later") {
                    dismiss()
                }
                .foregroundColor(.secondary)
                .padding(.bottom, 16)
            }
            .navigationBarHidden(true)
        }
    }
}
