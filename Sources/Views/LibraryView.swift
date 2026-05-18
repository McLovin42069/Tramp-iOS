import SwiftUI

struct LibraryView: View {
    @State private var viewModel = LibraryViewModel()
    @State private var skinManager = SkinManager.shared
    @State private var playerVM = PlayerViewModel()
    @State private var showImportPicker = false
    @State private var showCreatePlaylist = false
    @State private var newPlaylistName = ""
    
    var body: some View {
        NavigationStack {
            ZStack {
                skinManager.currentSkin.backgroundColor
                RustyTexture(opacity: skinManager.currentSkin.textureOpacity)
                
                VStack(spacing: 0) {
                    // Tab selector
                    HStack(spacing: 0) {
                        ForEach(LibraryViewModel.LibraryTab.allCases, id: \.self) { tab in
                            Button(action: { viewModel.selectedTab = tab }) {
                                VStack(spacing: 2) {
                                    Image(systemName: tab.icon)
                                        .font(.system(size: 14))
                                    Text(tab.rawValue)
                                        .font(.system(size: 9, weight: .medium, design: .monospaced))
                                }
                                .foregroundColor(viewModel.selectedTab == tab ? skinManager.currentSkin.accentColor : skinManager.currentSkin.textColor.opacity(0.5))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 8)
                                .background(
                                    viewModel.selectedTab == tab
                                    ? skinManager.currentSkin.accentColor.opacity(0.1)
                                    : Color.clear
                                )
                            }
                            .buttonStyle(PlainButtonStyle())
                        }
                    }
                    .background(
                        LinearGradient(
                            colors: [
                                skinManager.currentSkin.bezelColor.brightness(0.1),
                                skinManager.currentSkin.bezelColor
                            ],
                            startPoint: .top,
                            endPoint: .bottom
                        )
                    )
                    
                    // Content
                    switch viewModel.selectedTab {
                    case .playlists:
                        playlistsTab
                    case .tracks:
                        tracksTab
                    case .favorites:
                        favoritesTab
                    case .recent:
                        recentTab
                    }
                }
            }
            .navigationTitle("Library")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: { showImportPicker = true }) {
                        Image(systemName: "plus")
                            .foregroundColor(skinManager.currentSkin.textColor)
                    }
                }
            }
            .sheet(isPresented: $showImportPicker) {
                DocumentPicker { urls in
                    Task {
                        await viewModel.importFiles(from: urls)
                    }
                }
            }
            .alert("New Playlist", isPresented: $showCreatePlaylist) {
                TextField("Playlist name", text: $newPlaylistName)
                Button("Cancel", role: .cancel) {}
                Button("Create") {
                    if !newPlaylistName.isEmpty {
                        viewModel.createPlaylist(name: newPlaylistName)
                        newPlaylistName = ""
                    }
                }
            }
        }
    }
    
    private var playlistsTab: some View {
        List {
            Button(action: { showCreatePlaylist = true }) {
                HStack {
                    Image(systemName: "plus.circle")
                        .font(.system(size: 18))
                        .foregroundColor(skinManager.currentSkin.accentColor)
                    Text("Create Playlist")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(skinManager.currentSkin.accentColor)
                    Spacer()
                }
            }
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
            
            ForEach(viewModel.playlists) { playlist in
                PlaylistListRow(playlist: playlist)
                    .onTapGesture {
                        playerVM.playQueue(playlist.tracks)
                    }
            }
            .onDelete(perform: viewModel.deletePlaylist)
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
    }
    
    private var tracksTab: some View {
        List {
            ForEach(viewModel.importedTracks) { track in
                SearchResultRow(track: track)
                    .onTapGesture {
                        playerVM.play(track: track)
                    }
                    .swipeActions(edge: .trailing) {
                        Button(role: .destructive) {
                            // Remove track
                        } label: {
                            Label("Delete", systemImage: "trash")
                        }
                        
                        Button {
                            viewModel.toggleFavorite(track)
                        } label: {
                            Label(viewModel.isFavorite(track) ? "Unfavorite" : "Favorite",
                                  systemImage: viewModel.isFavorite(track) ? "heart.slash" : "heart")
                        }
                        .tint(.pink)
                    }
            }
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
    }
    
    private var favoritesTab: some View {
        List {
            ForEach(viewModel.favoriteTracks) { track in
                SearchResultRow(track: track)
                    .onTapGesture {
                        playerVM.play(track: track)
                    }
                    .swipeActions(edge: .trailing) {
                        Button {
                            viewModel.toggleFavorite(track)
                        } label: {
                            Label("Remove", systemImage: "heart.slash")
                        }
                        .tint(.pink)
                    }
            }
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .overlay {
            if viewModel.favoriteTracks.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "heart")
                        .font(.system(size: 32))
                        .foregroundColor(skinManager.currentSkin.textColor.opacity(0.3))
                    Text("No favorites yet")
                        .font(.system(size: 12))
                        .foregroundColor(skinManager.currentSkin.textColor.opacity(0.5))
                }
            }
        }
    }
    
    private var recentTab: some View {
        List {
            ForEach(viewModel.recentlyPlayed) { track in
                SearchResultRow(track: track)
                    .onTapGesture {
                        playerVM.play(track: track)
                    }
            }
            .listRowBackground(Color.clear)
            .listRowSeparator(.hidden)
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .overlay {
            if viewModel.recentlyPlayed.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "clock")
                        .font(.system(size: 32))
                        .foregroundColor(skinManager.currentSkin.textColor.opacity(0.3))
                    Text("No recent tracks")
                        .font(.system(size: 12))
                        .foregroundColor(skinManager.currentSkin.textColor.opacity(0.5))
                }
            }
        }
    }
}

struct PlaylistListRow: View {
    let playlist: Playlist
    
    var body: some View {
        HStack(spacing: 10) {
            ZStack {
                RoundedRectangle(cornerRadius: 4)
                    .fill(SkinManager.shared.currentSkin.buttonColor.opacity(0.5))
                    .frame(width: 50, height: 50)
                
                Image(systemName: "list.bullet.rectangle")
                    .font(.system(size: 20))
                    .foregroundColor(SkinManager.shared.currentSkin.accentColor)
            }
            
            VStack(alignment: .leading, spacing: 2) {
                Text(playlist.name)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(SkinManager.shared.currentSkin.textColor)
                
                Text("\(playlist.tracks.count) tracks \u{2022} \(playlist.formattedDuration)")
                    .font(.system(size: 11))
                    .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.6))
                
                Text(playlist.uniqueArtists.prefix(3).joined(separator: ", "))
                    .font(.system(size: 10))
                    .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.4))
                    .lineLimit(1)
            }
            
            Spacer()
            
            Image(systemName: "chevron.right")
                .font(.system(size: 12))
                .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.4))
        }
        .padding(.vertical, 4)
        .contentShape(Rectangle())
    }
}

// MARK: - Document Picker
struct DocumentPicker: UIViewControllerRepresentable {
    let onPick: ([URL]) -> Void
    
    func makeUIViewController(context: Context) -> UIDocumentPickerViewController {
        let picker = UIDocumentPickerViewController(forOpeningContentTypes: [
            .mp3, .mpeg4Audio, .audio, .wav, .data
        ], asCopy: true)
        picker.allowsMultipleSelection = true
        picker.delegate = context.coordinator
        return picker
    }
    
    func updateUIViewController(_ uiViewController: UIDocumentPickerViewController, context: Context) {}
    
    func makeCoordinator() -> Coordinator {
        Coordinator(onPick: onPick)
    }
    
    class Coordinator: NSObject, UIDocumentPickerDelegate {
        let onPick: ([URL]) -> Void
        
        init(onPick: @escaping ([URL]) -> Void) {
            self.onPick = onPick
        }
        
        func documentPicker(_ controller: UIDocumentPickerViewController, didPickDocumentsAt urls: [URL]) {
            onPick(urls)
        }
    }
}
