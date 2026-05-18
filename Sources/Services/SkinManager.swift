import Foundation
import SwiftUI

@Observable
final class SkinManager {
    static let shared = SkinManager()
    
    var currentSkin: Skin = .classic
    var availableSkins: [Skin] = Skin.allSkins
    
    private let defaults = UserDefaults.standard
    private let skinKey = "tramp.selectedSkin"
    private let unlockedKey = "tramp.unlockedSkins"
    
    private init() {
        loadSavedSkin()
        loadUnlockedSkins()
    }
    
    func selectSkin(_ skin: Skin) {
        currentSkin = skin
        defaults.set(skin.id, forKey: skinKey)
    }
    
    func isUnlocked(_ skin: Skin) -> Bool {
        !skin.isPremium || skin.isUnlocked
    }
    
    func unlockSkin(_ skin: Skin) {
        guard let idx = availableSkins.firstIndex(where: { $0.id == skin.id }) else { return }
        availableSkins[idx] = Skin(
            id: skin.id,
            name: skin.name,
            author: skin.author,
            description: skin.description,
            isPremium: skin.isPremium,
            isUnlocked: true,
            price: skin.price,
            backgroundColor: skin.backgroundColor,
            bezelColor: skin.bezelColor,
            buttonColor: skin.buttonColor,
            textColor: skin.textColor,
            accentColor: skin.accentColor,
            ledColor: skin.ledColor,
            displayColor: skin.displayColor,
            textureOpacity: skin.textureOpacity,
            cornerStyle: skin.cornerStyle,
            fontName: skin.fontName,
            ledFontName: skin.ledFontName,
            previewImage: skin.previewImage,
            isAnimated: skin.isAnimated
        )
        saveUnlockedSkins()
    }
    
    private func loadSavedSkin() {
        if let id = defaults.string(forKey: skinKey),
           let skin = Skin.allSkins.first(where: { $0.id == id }) {
            currentSkin = skin
        }
    }
    
    private func loadUnlockedSkins() {
        let unlocked = defaults.stringArray(forKey: unlockedKey) ?? []
        for id in unlocked {
            if let idx = availableSkins.firstIndex(where: { $0.id == id }) {
                let skin = availableSkins[idx]
                availableSkins[idx] = Skin(
                    id: skin.id,
                    name: skin.name,
                    author: skin.author,
                    description: skin.description,
                    isPremium: skin.isPremium,
                    isUnlocked: true,
                    price: skin.price,
                    backgroundColor: skin.backgroundColor,
                    bezelColor: skin.bezelColor,
                    buttonColor: skin.buttonColor,
                    textColor: skin.textColor,
                    accentColor: skin.accentColor,
                    ledColor: skin.ledColor,
                    displayColor: skin.displayColor,
                    textureOpacity: skin.textureOpacity,
                    cornerStyle: skin.cornerStyle,
                    fontName: skin.fontName,
                    ledFontName: skin.ledFontName,
                    previewImage: skin.previewImage,
                    isAnimated: skin.isAnimated
                )
            }
        }
    }
    
    private func saveUnlockedSkins() {
        let unlocked = availableSkins.filter { $0.isUnlocked }.map { $0.id }
        defaults.set(unlocked, forKey: unlockedKey)
    }
}
