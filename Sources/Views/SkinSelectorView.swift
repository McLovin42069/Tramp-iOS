import SwiftUI

struct SkinSelectorView: View {
    @State private var skinManager = SkinManager.shared
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationStack {
            ZStack {
                skinManager.currentSkin.backgroundColor
                
                ScrollView {
                    LazyVStack(spacing: 16) {
                        ForEach(Skin.allSkins) { skin in
                            SkinCard(skin: skin)
                                .onTapGesture {
                                    if skinManager.isUnlocked(skin) {
                                        skinManager.selectSkin(skin)
                                        HapticFeedback.success()
                                    }
                                }
                        }
                    }
                    .padding(.vertical, 16)
                }
            }
            .navigationTitle("Skins")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                    .foregroundColor(skinManager.currentSkin.textColor)
                }
            }
        }
    }
}

struct SkinCard: View {
    let skin: Skin
    @State private var skinManager = SkinManager.shared
    
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Preview
            ZStack {
                skin.backgroundColor
                
                // Fake player chrome
                VStack(spacing: 4) {
                    HStack {
                        Text(Constants.appName)
                            .font(.system(size: 8, weight: .bold))
                            .foregroundColor(skin.textColor)
                        Spacer()
                    }
                    .padding(.horizontal, 8)
                    .padding(.top, 4)
                    
                    HStack {
                        Rectangle()
                            .fill(skin.displayColor)
                            .frame(width: 80, height: 24)
                        
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Track Title")
                                .font(.system(size: 8, weight: .bold))
                                .foregroundColor(skin.ledColor)
                            Text("Artist Name")
                                .font(.system(size: 7))
                                .foregroundColor(skin.ledColor.opacity(0.7))
                        }
                        
                        Spacer()
                    }
                    .padding(.horizontal, 8)
                    
                    HStack(spacing: 8) {
                        Circle()
                            .fill(skin.buttonColor)
                            .frame(width: 16, height: 16)
                        Circle()
                            .fill(skin.buttonColor)
                            .frame(width: 16, height: 16)
                        Circle()
                            .fill(skin.buttonColor)
                            .frame(width: 16, height: 16)
                        
                        Spacer()
                    }
                    .padding(.horizontal, 8)
                    
                    Spacer()
                }
                
                if skin.isPremium && !skinManager.isUnlocked(skin) {
                    Rectangle()
                        .fill(Color.black.opacity(0.5))
                    
                    Image(systemName: "lock.fill")
                        .font(.system(size: 24))
                        .foregroundColor(.white)
                }
            }
            .frame(height: 120)
            .clipShape(RoundedRectangle(cornerRadius: 8, style: .continuous))
            .overlay(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .stroke(skinManager.currentSkin.id == skin.id ? skinManager.currentSkin.accentColor : skin.bezelColor, lineWidth: skinManager.currentSkin.id == skin.id ? 3 : 1)
            )
            
            // Info
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    HStack(spacing: 4) {
                        Text(skin.name)
                            .font(.system(size: 14, weight: .bold))
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
                        .lineLimit(2)
                    
                    Text("by \(skin.author)")
                        .font(.system(size: 10))
                        .foregroundColor(skinManager.currentSkin.textColor.opacity(0.4))
                }
                
                Spacer()
                
                if skinManager.currentSkin.id == skin.id {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 24))
                        .foregroundColor(skinManager.currentSkin.accentColor)
                } else if skin.isPremium && !skinManager.isUnlocked(skin) {
                    Button(action: {}) {
                        Text(skin.price ?? "")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.white)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(
                                Capsule()
                                    .fill(skinManager.currentSkin.accentColor)
                            )
                    }
                    .buttonStyle(PlainButtonStyle())
                }
            }
            .padding(.top, 8)
        }
        .padding(.horizontal, 16)
    }
}
