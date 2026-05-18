import SwiftUI

struct PlaylistWindowView: View {
    @State private var viewModel = PlayerViewModel()
    @State private var skinManager = SkinManager.shared
    @State private var editingPlaylist = false
    
    var body: some View {
        NavigationStack {
            ZStack {
                skinManager.currentSkin.backgroundColor
                RustyTexture(opacity: skinManager.currentSkin.textureOpacity)
                
                VStack(spacing: 0) {
                    // Header
                    HStack {
                        Text("Playlist")
                            .font(.system(size: 14, weight: .bold, design: .monospaced))
                            .foregroundColor(skinManager.currentSkin.textColor)
                        
                        Spacer()
                        
                        Text("\(viewModel.queue.count) tracks")
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundColor(skinManager.currentSkin.textColor.opacity(0.6))
                        
                        Button(action: { editingPlaylist.toggle() }) {
                            Image(systemName: editingPlaylist ? "checkmark" : "slider.horizontal.3")
                                .font(.system(size: 12))
                                .foregroundColor(skinManager.currentSkin.textColor)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(
                        LinearGradient(
                            colors: [
                                skinManager.currentSkin.bezelColor.brightness(0.2),
                                skinManager.currentSkin.bezelColor
                            ],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    
                    // Track List
                    List {
                        ForEach(Array(viewModel.queue.enumerated()), id: \.element.id) { index, track in
                            PlaylistRow(
                                track: track,
                                isPlaying: viewModel.currentIndex == index && viewModel.isPlaying,
                                index: index + 1
                            )
                            .listRowBackground(
                                viewModel.currentIndex == index
                                ? skinManager.currentSkin.accentColor.opacity(0.2)
                                : Color.clear
                            )
                            .listRowSeparator(.hidden)
                            .listRowInsets(EdgeInsets(top: 2, leading: 8, bottom: 2, trailing: 8))
                            .onTapGesture {
                                viewModel.playQueue(viewModel.queue, startingAt: index)
                            }
                        }
                        .onDelete { indexSet in
                            for index in indexSet.sorted(by: >) {
                                viewModel.removeFromQueue(at: index)
                            }
                        }
                        .onMove { source, destination in
                            viewModel.moveQueueItem(from: source, to: destination)
                        }
                    }
                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                    .environment(\.editMode, .constant(editingPlaylist ? .active : .inactive))
                    
                    // Bottom controls
                    HStack(spacing: 12) {
                        WinampButton(icon: "shuffle", size: 32) {
                            viewModel.toggleShuffle()
                        }
                        .opacity(viewModel.shuffleMode ? 1.0 : 0.5)
                        
                        Spacer()
                        
                        WinampTextButton(title: "CLEAR", width: 60, height: 28) {
                            viewModel.clearQueue()
                        }
                        
                        WinampTextButton(title: "SAVE", width: 60, height: 28) {
                            // Save playlist
                        }
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(
                        LinearGradient(
                            colors: [
                                skinManager.currentSkin.bezelColor,
                                skinManager.currentSkin.bezelColor.brightness(-0.1)
                            ],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                }
            }
            .navigationBarHidden(true)
        }
    }
}

struct PlaylistRow: View {
    let track: Track
    let isPlaying: Bool
    let index: Int
    
    var body: some View {
        HStack(spacing: 8) {
            Text("\(index)")
                .font(.system(size: 10, design: .monospaced))
                .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.5))
                .frame(width: 24, alignment: .trailing)
            
            if isPlaying {
                Image(systemName: "speaker.wave.2")
                    .font(.system(size: 10))
                    .foregroundColor(SkinManager.shared.currentSkin.accentColor)
            }
            
            VStack(alignment: .leading, spacing: 1) {
                Text(track.displayTitle)
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(isPlaying ? SkinManager.shared.currentSkin.accentColor : SkinManager.shared.currentSkin.textColor)
                    .lineLimit(1)
                
                Text(track.displayArtist)
                    .font(.system(size: 10))
                    .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.6))
                    .lineLimit(1)
            }
            
            Spacer()
            
            Text(track.duration.formattedTime())
                .font(.system(size: 10, design: .monospaced))
                .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.5))
        }
        .padding(.vertical, 4)
        .contentShape(Rectangle())
    }
}
