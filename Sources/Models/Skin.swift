import Foundation
import SwiftUI

struct Skin: Identifiable, Equatable {
    let id: String
    let name: String
    let author: String
    let description: String
    let isPremium: Bool
    let isUnlocked: Bool
    let price: String?
    let backgroundColor: Color
    let bezelColor: Color
    let buttonColor: Color
    let textColor: Color
    let accentColor: Color
    let ledColor: Color
    let displayColor: Color
    let textureOpacity: Double
    let cornerStyle: CornerStyle
    let fontName: String
    let ledFontName: String
    let previewImage: String
    let isAnimated: Bool
    
    enum CornerStyle: String {
        case square = "square"
        case rounded = "rounded"
        case retro = "retro"
    }
    
    static let classic = Skin(
        id: "classic",
        name: "Tramp Classic",
        author: "Tramp Team",
        description: "The default rusty traveler aesthetic. Warm oranges, aged metals, and that dusty road feel.",
        isPremium: false,
        isUnlocked: true,
        price: nil,
        backgroundColor: Color(hex: "2A1F1D"),
        bezelColor: Color(hex: "8B7355"),
        buttonColor: Color(hex: "A0522D"),
        textColor: Color(hex: "F5F5DC"),
        accentColor: Color(hex: "FF8C00"),
        ledColor: Color(hex: "FFBF00"),
        displayColor: Color(hex: "1A1A1A"),
        textureOpacity: 0.15,
        cornerStyle: .square,
        fontName: "Courier",
        ledFontName: "Courier-Bold",
        previewImage: "skin_classic",
        isAnimated: false
    )
    
    static let rustyRoad = Skin(
        id: "rusty_road",
        name: "Rusty Road",
        author: "Tramp Team",
        description: "Heavy rust, scratched metal, and corrugated iron panels. For the hard traveler.",
        isPremium: false,
        isUnlocked: true,
        price: nil,
        backgroundColor: Color(hex: "3E2723"),
        bezelColor: Color(hex: "5D4037"),
        buttonColor: Color(hex: "6D4C41"),
        textColor: Color(hex: "D7CCC8"),
        accentColor: Color(hex: "FF5722"),
        ledColor: Color(hex: "FF6F00"),
        displayColor: Color(hex: "212121"),
        textureOpacity: 0.25,
        cornerStyle: .square,
        fontName: "AmericanTypewriter",
        ledFontName: "AmericanTypewriter-Bold",
        previewImage: "skin_rusty",
        isAnimated: false
    )
    
    static let neonNights = Skin(
        id: "neon_nights",
        name: "Neon Nights",
        author: "Tramp Team",
        description: "Cyberpunk diner at 3 AM. Neon blues, magentas, and electric dreams.",
        isPremium: true,
        isUnlocked: false,
        price: "$1.99",
        backgroundColor: Color(hex: "0D0221"),
        bezelColor: Color(hex: "241663"),
        buttonColor: Color(hex: "3D1E6D"),
        textColor: Color(hex: "E0AAFF"),
        accentColor: Color(hex: "00F5D4"),
        ledColor: Color(hex: "FF00FF"),
        displayColor: Color(hex: "1A0A2E"),
        textureOpacity: 0.1,
        cornerStyle: .retro,
        fontName: "Futura",
        ledFontName: "Futura-Bold",
        previewImage: "skin_neon",
        isAnimated: true
    )
    
    static let darkBasement = Skin(
        id: "dark_basement",
        name: "Dark Basement",
        author: "Tramp Team",
        description: "Moldy concrete, flickering fluorescents, and the smell of old vinyl. Pure underground.",
        isPremium: true,
        isUnlocked: false,
        price: "$1.99",
        backgroundColor: Color(hex: "1A1A2E"),
        bezelColor: Color(hex: "16213E"),
        buttonColor: Color(hex: "0F3460"),
        textColor: Color(hex: "E94560"),
        accentColor: Color(hex: "533483"),
        ledColor: Color(hex: "00FFF5"),
        displayColor: Color(hex: "0A0A0A"),
        textureOpacity: 0.2,
        cornerStyle: .square,
        fontName: "HelveticaNeue",
        ledFontName: "HelveticaNeue-Bold",
        previewImage: "skin_dark",
        isAnimated: false
    )
    
    static let goldenSunset = Skin(
        id: "golden_sunset",
        name: "Golden Sunset",
        author: "Tramp Team",
        description: "Warm desert highways and dying light. For the eternal optimist.",
        isPremium: true,
        isUnlocked: false,
        price: "$2.99",
        backgroundColor: Color(hex: "2D132C"),
        bezelColor: Color(hex: "801336"),
        buttonColor: Color(hex: "C72C41"),
        textColor: Color(hex: "FFD700"),
        accentColor: Color(hex: "FF6B6B"),
        ledColor: Color(hex: "FFD700"),
        displayColor: Color(hex: "1A0A1A"),
        textureOpacity: 0.1,
        cornerStyle: .rounded,
        fontName: "Georgia",
        ledFontName: "Georgia-Bold",
        previewImage: "skin_golden",
        isAnimated: true
    )
    
    static let allSkins: [Skin] = [.classic, .rustyRoad, .neonNights, .darkBasement, .goldenSunset]
}
