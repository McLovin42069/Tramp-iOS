import Foundation

@Observable
final class SearchViewModel {
    var searchQuery = ""
    var selectedSource: MusicSource? = nil
    var selectedGenre: MusicGenre = .any
    var selectedMood: MusicMood = .any
    
    var searchResults: [Track] = []
    var isSearching = false
    var searchError: String?
    var hasSearched = false
    
    var genreResults: [Track] = []
    var isLoadingGenre = false
    
    var recentSearches: [String] {
        get { UserDefaults.standard.stringArray(forKey: "tramp.recentSearches") ?? [] }
        set { UserDefaults.standard.set(newValue, forKey: "tramp.recentSearches") }
    }
    
    private let jamendo = JamendoService.shared
    private let archive = InternetArchiveService.shared
    private let localFiles = LocalFileService.shared
    private let statsManager = StatsManager.shared
    
    func search() async {
        guard !searchQuery.isEmpty else { return }
        
        isSearching = true
        searchError = nil
        hasSearched = true
        searchResults = []
        
        saveRecentSearch(searchQuery)
        statsManager.recordSearch()
        
        var allResults: [Track] = []
        
        do {
            var errors: [String] = []
            
            // Search based on selected source or all
            // NOTE: Jamendo disabled — requires valid API key
            // if selectedSource == nil || selectedSource == .jamendo {
            //     async let jamendoResults = jamendo.search(query: searchQuery, limit: 20)
            //     do {
            //         let results = try await jamendoResults
            //         allResults.append(contentsOf: results)
            //     } catch {
            //         errors.append("Jamendo: \(error.localizedDescription)")
            //     }
            // }
            
            if selectedSource == nil || selectedSource == .internetArchive {
                async let archiveResults = archive.search(query: searchQuery, limit: 25)
                do {
                    let results = try await archiveResults
                    allResults.append(contentsOf: results)
                } catch {
                    errors.append("Internet Archive: \(error.localizedDescription)")
                }
            }
            
            if selectedSource == nil || selectedSource == .localFiles {
                async let localResults = localFiles.getImportedTracks()
                do {
                    let results = try await localResults
                    let filtered = results.filter {
                        $0.title.lowercased().contains(searchQuery.lowercased()) ||
                        $0.artist.lowercased().contains(searchQuery.lowercased())
                    }
                    allResults.append(contentsOf: filtered)
                } catch {
                    errors.append("Local files: \(error.localizedDescription)")
                }
            }
            
            // Remove duplicates by ID
            var seen = Set<String>()
            searchResults = allResults.filter { track in
                guard !seen.contains(track.id) else { return false }
                seen.insert(track.id)
                return true
            }
            
            if searchResults.isEmpty && !errors.isEmpty {
                searchError = errors.joined(separator: "\n")
            }
            
        } catch {
            searchError = "Search failed: \(error.localizedDescription)"
        }
        
        isSearching = false
    }
    
    func browseGenre(_ genre: MusicGenre) async {
        isLoadingGenre = true
        genreResults = []
        
        do {
            async let jamendoTracks = jamendo.getByGenre(genre, limit: 25)
            async let archiveTracks = archive.getByGenre(genre, limit: 15)
            
            let (jamendo, archive) = await (try? jamendoTracks, try? archiveTracks)
            
            var all: [Track] = []
            if let j = jamendo { all.append(contentsOf: j) }
            if let a = archive { all.append(contentsOf: a) }
            
            genreResults = all
        }
        
        isLoadingGenre = false
    }
    
    func clearSearch() {
        searchQuery = ""
        searchResults = []
        hasSearched = false
        searchError = nil
    }
    
    func clearRecentSearches() {
        recentSearches = []
    }
    
    private func saveRecentSearch(_ query: String) {
        var recent = recentSearches
        recent.removeAll { $0 == query }
        recent.insert(query, at: 0)
        if recent.count > 10 {
            recent = Array(recent.prefix(10))
        }
        recentSearches = recent
    }
}
