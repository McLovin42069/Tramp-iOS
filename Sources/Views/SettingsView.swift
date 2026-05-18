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
                
                List {
                    // Stats Section
                    Section {
                        statsHeader
                    }
                    .listRowBackground(skinManager.currentSkin.displayColor.opacity(0.3))
                    
                    // Playback Settings
                    Section(header: sectionHeader("Playback")) {
                        Toggle("Background Playback", isOn: $viewModel.backgroundPlaybackEnabled)
                            .onChange(of: viewModel.backgroundPlaybackEnabled) { oldValue, newValue in viewModel.saveSettings() }
                        
                        Toggle("Crossfade", isOn: $viewModel.crossfadeEnabled)
                            .onChange(of: viewModel.crossfadeEnabled) { oldValue, newValue in viewModel.saveSettings() }
                        
                        if viewModel.crossfadeEnabled {
                            HStack {
                                Text("Crossfade Duration")
                                Spacer()
                                Text("\(Int(viewModel.crossfadeDuration))s")
                                    .font(.system(size: 12, design: .monospaced))
                                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                            }
                            
                            Slider(value: $viewModel.crossfadeDuration, in: 0.5...5, step: 0.5)
                                .tint(skinManager.currentSkin.accentColor)
                                .onChange(of: viewModel.crossfadeDuration) { oldValue, newValue in viewModel.saveSettings() }
                        }
                        
                        Toggle("Auto-Cache Streams", isOn: $viewModel.autoCacheEnabled)
                            .onChange(of: viewModel.autoCacheEnabled) { oldValue, newValue in viewModel.saveSettings() }
                        
                        HStack {
                            Text("Cache Size")
                            Spacer()
                            Text(String(format: "%.1f MB", viewModel.cacheSizeMB))
                                .font(.system(size: 12, design: .monospaced))
                                .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                        }
                        
                        Button("Clear Cache") {
                            viewModel.clearCache()
                        }
                        .foregroundColor(skinManager.currentSkin.accentColor)
                    }
                    .listRowBackground(skinManager.currentSkin.displayColor.opacity(0.3))
                    
                    // Appearance
                    Section(header: sectionHeader("Appearance")) {
                        Button(action: { skinManager.selectSkin(.classic) }) {
                            skinRow(skin: .classic)
                        }
                        .buttonStyle(PlainButtonStyle())
                        
                        Button(action: { skinManager.selectSkin(.rustyRoad) }) {
                            skinRow(skin: .rustyRoad)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                    .listRowBackground(skinManager.currentSkin.displayColor.opacity(0.3))
                    
                    // Premium Skins
                    Section(header: sectionHeader("Premium Skins")) {
                        ForEach(Skin.allSkins.filter { $0.isPremium }) { skin in
                            Button(action: {
                                if skinManager.isUnlocked(skin) {
                                    skinManager.selectSkin(skin)
                                } else {
                                    // Trigger purchase
                                }
                            }) {
                                premiumSkinRow(skin: skin)
                            }
                            .buttonStyle(PlainButtonStyle())
                        }
                    }
                    .listRowBackground(skinManager.currentSkin.displayColor.opacity(0.3))
                    
                    // Support
                    Section(header: sectionHeader("Support Tramp")) {
                        Text("Tramp will always stay 100% free. No ads, no subscriptions. If you enjoy it, feel free to support development.")
                            .font(.system(size: 11))
                            .foregroundColor(skinManager.currentSkin.textColor.opacity(0.7))
                            .padding(.vertical, 4)
                        
                        Button("Tip via Apple") {
                            showDonationSheet = true
                        }
                        .foregroundColor(skinManager.currentSkin.accentColor)
                        
                        Link("Buy Me a Coffee", destination: URL(string: "https://buymeacoffee.com/tramp")!)
                            .foregroundColor(skinManager.currentSkin.accentColor)
                        
                        Link("Ko-fi", destination: URL(string: "https://ko-fi.com/tramp")!)
                            .foregroundColor(skinManager.currentSkin.accentColor)
                    }
                    .listRowBackground(skinManager.currentSkin.displayColor.opacity(0.3))
                    
                    // About
                    Section(header: sectionHeader("About")) {
                        HStack {
                            Text("Version")
                            Spacer()
                            Text("1.0.0")
                                .font(.system(size: 12, design: .monospaced))
                                .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                        }
                        
                        Link("Privacy Policy", destination: URL(string: "https://tramp.app/privacy")!)
                            .foregroundColor(skinManager.currentSkin.accentColor)
                        
                        Link("Open Source Licenses", destination: URL(string: "https://tramp.app/licenses")!)
                            .foregroundColor(skinManager.currentSkin.accentColor)
                    }
                    .listRowBackground(skinManager.currentSkin.displayColor.opacity(0.3))
                    
                    // Danger Zone
                    Section(header: sectionHeader("Danger Zone")) {
                        Button("Reset All Stats") {
                            showResetConfirmation = true
                        }
                        .foregroundColor(.red)
                    }
                    .listRowBackground(skinManager.currentSkin.displayColor.opacity(0.3))
                }
                .listStyle(.insetGrouped)
                .scrollContentBackground(.hidden)
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
    
    private func sectionHeader(_ title: String) -> some View {
        Text(title)
            .font(.system(size: 11, weight: .bold, design: .monospaced))
            .foregroundColor(skinManager.currentSkin.accentColor)
            .textCase(.uppercase)
    }
    
    private var statsHeader: some View {
        VStack(spacing: 12) {
            HStack(spacing: 16) {
                VStack(spacing: 2) {
                    Text("\(viewModel.stats.level)")
                        .font(.system(size: 28, weight: .bold, design: .monospaced))
                        .foregroundColor(skinManager.currentSkin.ledColor)
                    Text(viewModel.stats.levelTitle)
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(skinManager.currentSkin.accentColor)
                }
                .frame(width: 80)
                
                VStack(alignment: .leading, spacing: 4) {
                    Text("Level \(viewModel.stats.level)")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(skinManager.currentSkin.textColor)
                    
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            RoundedRectangle(cornerRadius: 2)
                                .fill(skinManager.currentSkin.displayColor)
                                .frame(height: 8)
                            
                            RoundedRectangle(cornerRadius: 2)
                                .fill(skinManager.currentSkin.accentColor)
                                .frame(width: CGFloat(viewModel.nextLevelProgress) * geo.size.width, height: 8)
                        }
                    }
                    .frame(height: 8)
                    
                    Text("\(Int(viewModel.stats.xp)) / \(Int(viewModel.nextLevelXP)) XP")
                        .font(.system(size: 9, design: .monospaced))
                        .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                }
            }
            
            HStack(spacing: 16) {
                StatBadge(icon: "clock", value: viewModel.formattedTotalTime, label: "Listened")
                StatBadge(icon: "speedometer", value: viewModel.formattedMiles, label: "Miles")
                StatBadge(icon: "flame", value: "\(viewModel.stats.currentStreakDays)d", label: "Streak")
            }
            
            if !viewModel.stats.badges.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(viewModel.stats.badges.prefix(5)) { badge in
                            VStack(spacing: 2) {
                                Image(systemName: badge.icon)
                                    .font(.system(size: 16))
                                    .foregroundColor(skinManager.currentSkin.accentColor)
                                Text(badge.name)
                                    .font(.system(size: 8))
                                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.7))
                            }
                            .frame(width: 56)
                            .padding(.vertical, 6)
                            .background(
                                RoundedRectangle(cornerRadius: 4)
                                    .fill(skinManager.currentSkin.buttonColor.opacity(0.3))
                            )
                        }
                    }
                }
            }
        }
        .padding(.vertical, 8)
    }
    
    private func skinRow(skin: Skin) -> some View {
        HStack {
            RoundedRectangle(cornerRadius: 4)
                .fill(skin.backgroundColor)
                .frame(width: 40, height: 40)
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
                Image(systemName: "checkmark")
                    .foregroundColor(skinManager.currentSkin.accentColor)
            }
        }
    }
    
    private func premiumSkinRow(skin: Skin) -> some View {
        HStack {
            RoundedRectangle(cornerRadius: 4)
                .fill(skin.backgroundColor)
                .frame(width: 40, height: 40)
                .overlay(
                    RoundedRectangle(cornerRadius: 4)
                        .stroke(skin.bezelColor, lineWidth: 2)
                )
            
            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 4) {
                    Text(skin.name)
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(skinManager.currentSkin.textColor)
                    
                    if skin.isPremium && !skinManager.isUnlocked(skin) {
                        Text("PREMIUM")
                            .font(.system(size: 8, weight: .bold))
                            .foregroundColor(skinManager.currentSkin.backgroundColor)
                            .padding(.horizontal, 4)
                            .padding(.vertical, 1)
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
                    Image(systemName: "checkmark")
                        .foregroundColor(skinManager.currentSkin.accentColor)
                } else {
                    Text("Unlocked")
                        .font(.system(size: 10))
                        .foregroundColor(skinManager.currentSkin.accentColor)
                }
            } else {
                Text(skin.price ?? "")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(skinManager.currentSkin.accentColor)
            }
        }
    }
}

struct StatBadge: View {
    let icon: String
    let value: String
    let label: String
    
    var body: some View {
        VStack(spacing: 2) {
            Image(systemName: icon)
                .font(.system(size: 14))
                .foregroundColor(SkinManager.shared.currentSkin.accentColor)
            Text(value)
                .font(.system(size: 12, weight: .bold, design: .monospaced))
                .foregroundColor(SkinManager.shared.currentSkin.textColor)
            Text(label)
                .font(.system(size: 9))
                .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.6))
        }
        .frame(maxWidth: .infinity)
    }
}

struct DonationView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var selectedAmount: Double? = nil
    let amounts = [1.99, 4.99, 9.99, 19.99]
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Image(systemName: "heart.fill")
                    .font(.system(size: 48))
                    .foregroundColor(.red)
                    .padding(.top, 20)
                
                Text("Support Tramp")
                    .font(.system(size: 22, weight: .bold))
                
                Text("Tramp will always be free. Your tip helps keep the lights on and the music flowing.")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)
                
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
                .padding(.horizontal)
                
                Spacer()
                
                Button("Maybe Later") {
                    dismiss()
                }
                .foregroundColor(.secondary)
                .padding(.bottom)
            }
            .navigationBarHidden(true)
        }
    }
}
