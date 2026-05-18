# Tramp — The Traveler's Jukebox

A 100% free, nostalgic Winamp-style music player for iOS. Built with SwiftUI and fueled by millions of legal free tracks from across the internet.

## Features

- **Unified Music Search** — Search across Jamendo, Internet Archive, Pixabay, and your local files simultaneously
- **Tramp Radio** — Endless intelligent mixing across all sources with genre/mood filtering
- **Nostalgic Winamp UI** — Pixel-perfect retro aesthetic with metallic bezels, LED displays, and real-time spectrum analyzer
- **Visualizer** — Multiple visualizer modes: Spectrum, Waveform, Particles, and Scope
- **Skins** — Tramp Classic, Rusty Road (free) + Neon Nights, Dark Basement, Golden Sunset (premium)
- **Gamification** — Listening streaks, Tramp Miles, levels, and badges
- **Background Playback** — Keep the music going while using other apps
- **No Ads, No Subscriptions** — Completely free with optional tips

## Music Sources

| Source | Type | Notes |
|--------|------|-------|
| Jamendo | Indie, Electronic | Full API v3.0 integration |
| Internet Archive | Classical, Old Recordings | Public domain & live concerts |
| Pixabay | Royalty-Free | High quality tracks |
| Free Music Archive | Curated CC Music | Where API works |
| Local Files | Your Collection | Import from Files app |

## Setup

1. Open Xcode 15+ and create a new iOS project
2. Copy all files from this directory into the project
3. Add the `Info.plist` to your target
4. Set Deployment Target to iOS 17.0+
5. Build and run!

### API Keys (Optional)

- **Jamendo**: Uses demo key by default. Replace `Constants.jamendoClientId` with your own at [Jamendo](https://developer.jamendo.com/)
- **Pixabay**: Replace `Constants.pixabayKey` with your key at [Pixabay](https://pixabay.com/api/docs/)

## Monetization

- No ads ever
- Optional donations via Apple Tip Jar
- Premium skins available as one-time cosmetic IAPs ($1.99–$2.99)

## Tech Stack

- SwiftUI + MVVM
- iOS 17+ (uses `@Observable` macro)
- AVPlayer + AVAudioEngine
- Core Data (programmatic model)
- Accelerate framework (FFT for visualizer)

## License

Tramp is free software. All music respects the licenses of their respective sources.
