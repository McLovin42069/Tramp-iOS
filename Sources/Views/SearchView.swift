import SwiftUI

struct SearchView: View {
    @State private var viewModel = SearchViewModel()
    @State private var skinManager = SkinManager.shared
    @State private var playerVM = PlayerViewModel()
    
    var body: some View {
        NavigationStack {
            ZStack {
                skinManager.currentSkin.backgroundColor
                RustyTexture(opacity: skinManager.currentSkin.textureOpacity)
                
                VStack(spacing: 0) {
                    // Search Header
                    searchHeader
                    
                    // Filters
                    filterSection
                    
                    // Results
                    if viewModel.isSearching {
                        Spacer()
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle(tint: skinManager.currentSkin.accentColor))
                            .scaleEffect(1.5)
                        Spacer()
                    } else if let error = viewModel.searchError {
                        Spacer()
                        VStack(spacing: 8) {
                            Image(systemName: "exclamationmark.triangle")
                                .font(.system(size: 32))
                                .foregroundColor(skinManager.currentSkin.ledColor)
                            Text(error)
                                .font(.system(size: 12, design: .monospaced))
                                .foregroundColor(skinManager.currentSkin.textColor)
                                .multilineTextAlignment(.center)
                                .padding(.horizontal)
                        }
                        Spacer()
                    } else if viewModel.hasSearched && viewModel.searchResults.isEmpty {
                        Spacer()
                        VStack(spacing: 8) {
                            Image(systemName: "magnifyingglass")
                                .font(.system(size: 32))
                                .foregroundColor(skinManager.currentSkin.textColor.opacity(0.4))
                            Text("No tracks found")
                                .font(.system(size: 12, design: .monospaced))
                                .foregroundColor(skinManager.currentSkin.textColor.opacity(0.5))
                        }
                        Spacer()
                    } else {
                        ScrollView {
                            LazyVStack(spacing: 2) {
                                ForEach(viewModel.searchResults) { track in
                                    SearchResultRow(track: track)
                                        .onTapGesture {
                                            playerVM.play(track: track)
                                        }
                                        .contextMenu {
                                            Button(action: { playerVM.addToQueue(track) }) {
                                                Label("Add to Queue", systemImage: "plus")
                                            }
                                            Button(action: {}) {
                                                Label("Add to Playlist", systemImage: "list.bullet.rectangle")
                                            }
                                        }
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
            }
            .navigationTitle("Search")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button(action: { viewModel.clearSearch() }) {
                        Image(systemName: "xmark.circle")
                            .foregroundColor(skinManager.currentSkin.textColor)
                    }
                }
            }
        }
    }
    
    private var searchHeader: some View {
        VStack(spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(skinManager.currentSkin.textColor.opacity(0.5))
                
                TextField("Search tracks, artists...", text: $viewModel.searchQuery)
                    .font(.system(size: 14, design: .monospaced))
                    .foregroundColor(skinManager.currentSkin.textColor)
                    .submitLabel(.search)
                    .onSubmit {
                        Task { await viewModel.search() }
                    }
                
                if !viewModel.searchQuery.isEmpty {
                    Button(action: { viewModel.searchQuery = "" }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(skinManager.currentSkin.textColor.opacity(0.5))
                    }
                    .buttonStyle(PlainButtonStyle())
                }
            }
            .padding(8)
            .background(
                RoundedRectangle(cornerRadius: 4)
                    .fill(skinManager.currentSkin.displayColor)
                    .overlay(
                        RoundedRectangle(cornerRadius: 4)
                            .stroke(skinManager.currentSkin.bezelColor, lineWidth: 1)
                    )
            )
            .padding(.horizontal, 8)
            .padding(.top, 8)
            
            // Recent searches
            if !viewModel.recentSearches.isEmpty && !viewModel.hasSearched {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(viewModel.recentSearches, id: \.self) { search in
                            Button(action: {
                                viewModel.searchQuery = search
                                Task { await viewModel.search() }
                            }) {
                                Text(search)
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundColor(skinManager.currentSkin.textColor)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(
                                        RoundedRectangle(cornerRadius: 12)
                                            .fill(skinManager.currentSkin.buttonColor.opacity(0.5))
                                    )
                            }
                            .buttonStyle(PlainButtonStyle())
                        }
                        
                        Button(action: { viewModel.clearRecentSearches() }) {
                            Text("Clear")
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundColor(skinManager.currentSkin.accentColor)
                        }
                        .buttonStyle(PlainButtonStyle())
                    }
                    .padding(.horizontal, 8)
                }
            }
        }
    }
    
    private var filterSection: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                // Source filter
                Menu {
                    Button("All Sources") { viewModel.selectedSource = nil }
                    ForEach(MusicSource.allCases) { source in
                        if source.supportsSearch {
                            Button(source.rawValue) { viewModel.selectedSource = source }
                        }
                    }
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: viewModel.selectedSource?.icon ?? "globe")
                            .font(.system(size: 10))
                        Text(viewModel.selectedSource?.rawValue ?? "All Sources")
                            .font(.system(size: 10, design: .monospaced))
                    }
                    .foregroundColor(skinManager.currentSkin.textColor)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(
                        RoundedRectangle(cornerRadius: 4)
                            .fill(skinManager.currentSkin.buttonColor.opacity(0.5))
                            .overlay(
                                RoundedRectangle(cornerRadius: 4)
                                    .stroke(skinManager.currentSkin.bezelColor, lineWidth: 1)
                            )
                    )
                }
                
                // Genre filter
                Menu {
                    Button("Any Genre") { viewModel.selectedGenre = .any }
                    ForEach(MusicGenre.allCases.filter { $0 != .any }) { genre in
                        Button(genre.rawValue) { viewModel.selectedGenre = genre }
                    }
                } label: {
                    Text(viewModel.selectedGenre.rawValue)
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(skinManager.currentSkin.textColor)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(
                            RoundedRectangle(cornerRadius: 4)
                                .fill(skinManager.currentSkin.buttonColor.opacity(0.5))
                                .overlay(
                                    RoundedRectangle(cornerRadius: 4)
                                        .stroke(skinManager.currentSkin.bezelColor, lineWidth: 1)
                                )
                        )
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
        }
    }
}

struct SearchResultRow: View {
    let track: Track
    
    var body: some View {
        HStack(spacing: 10) {
            // Source icon
            ZStack {
                RoundedRectangle(cornerRadius: 2)
                    .fill(Color(hex: track.source.color).opacity(0.3))
                    .frame(width: 36, height: 36)
                
                Image(systemName: track.source.icon)
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: track.source.color))
            }
            
            VStack(alignment: .leading, spacing: 2) {
                Text(track.displayTitle)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(SkinManager.shared.currentSkin.textColor)
                    .lineLimit(1)
                
                HStack(spacing: 4) {
                    Text(track.displayArtist)
                        .font(.system(size: 11))
                        .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.6))
                        .lineLimit(1)
                    
                    Text("\u{2022}")
                        .font(.system(size: 8))
                        .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.4))
                    
                    Text(track.source.rawValue)
                        .font(.system(size: 10))
                        .foregroundColor(Color(hex: track.source.color))
                }
            }
            
            Spacer()
            
            Text(track.duration > 0 ? track.duration.formattedTime() : "")
                .font(.system(size: 10, design: .monospaced))
                .foregroundColor(SkinManager.shared.currentSkin.textColor.opacity(0.5))
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(
            Rectangle()
                .fill(Color.clear)
        )
        .contentShape(Rectangle())
    }
}
