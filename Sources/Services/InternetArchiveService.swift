import Foundation

actor InternetArchiveService {
    static let shared = InternetArchiveService()
    
    private let session: URLSession
    private var cache: [String: [Track]] = [:]
    
    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        self.session = URLSession(configuration: config)
    }
    
    func search(query: String, limit: Int = 20) async throws -> [Track] {
        let cacheKey = "ia_search_\(query)_\(limit)"
        if let cached = cache[cacheKey] { return cached }
        
        let encodedQuery = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        let urlString = "https://archive.org/advancedsearch.php?q=title:(\(encodedQuery)) AND mediatype:audio&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=subject&fl[]=description&sort[]=downloads desc&rows=\(limit)&output=json"
        
        guard let url = URL(string: urlString) else { throw URLError(.badURL) }
        
        let (data, _) = try await session.data(from: url)
        let response = try JSONDecoder().decode(ArchiveResponse.self, from: data)
        let tracks = response.response.docs.compactMap { $0.toTrack() }
        cache[cacheKey] = tracks
        return tracks
    }
    
    func getByGenre(_ genre: MusicGenre, limit: Int = 20) async throws -> [Track] {
        guard let query = genre.archiveQuery else { return [] }
        return try await search(query: query, limit: limit)
    }
    
    func getClassicalCollection(limit: Int = 30) async throws -> [Track] {
        let cacheKey = "ia_classical_\(limit)"
        if let cached = cache[cacheKey] { return cached }
        
        let urlString = "https://archive.org/advancedsearch.php?q=collection:(classical) AND mediatype:audio&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=subject&sort[]=downloads desc&rows=\(limit)&output=json"
        
        guard let url = URL(string: urlString) else { throw URLError(.badURL) }
        
        let (data, _) = try await session.data(from: url)
        let response = try JSONDecoder().decode(ArchiveResponse.self, from: data)
        let tracks = response.response.docs.compactMap { $0.toTrack() }
        cache[cacheKey] = tracks
        return tracks
    }
    
    func getOldRecordings(limit: Int = 30) async throws -> [Track] {
        let cacheKey = "ia_old_\(limit)"
        if let cached = cache[cacheKey] { return cached }
        
        let urlString = "https://archive.org/advancedsearch.php?q=collection:(78rpm) AND mediatype:audio&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=subject&sort[]=downloads desc&rows=\(limit)&output=json"
        
        guard let url = URL(string: urlString) else { throw URLError(.badURL) }
        
        let (data, _) = try await session.data(from: url)
        let response = try JSONDecoder().decode(ArchiveResponse.self, from: data)
        let tracks = response.response.docs.compactMap { $0.toTrack() }
        cache[cacheKey] = tracks
        return tracks
    }
    
    func getLiveConcerts(limit: Int = 20) async throws -> [Track] {
        let cacheKey = "ia_live_\(limit)"
        if let cached = cache[cacheKey] { return cached }
        
        let urlString = "https://archive.org/advancedsearch.php?q=collection:(etree) AND mediatype:audio&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=subject&sort[]=downloads desc&rows=\(limit)&output=json"
        
        guard let url = URL(string: urlString) else { throw URLError(.badURL) }
        
        let (data, _) = try await session.data(from: url)
        let response = try JSONDecoder().decode(ArchiveResponse.self, from: data)
        let tracks = response.response.docs.compactMap { $0.toTrack() }
        cache[cacheKey] = tracks
        return tracks
    }
}
