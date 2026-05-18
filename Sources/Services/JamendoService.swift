import Foundation

actor JamendoService {
    static let shared = JamendoService()
    
    private let baseURL = Constants.jamendoBaseURL
    private let clientId = Constants.jamendoClientId
    private let session: URLSession
    private var cache: [String: [Track]] = [:]
    
    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.requestCachePolicy = .returnCacheDataElseLoad
        self.session = URLSession(configuration: config)
    }
    
    func search(query: String, limit: Int = 20, offset: Int = 0) async throws -> [Track] {
        let cacheKey = "search_\(query)_\(limit)_\(offset)"
        if let cached = cache[cacheKey] { return cached }
        
        var components = URLComponents(string: "\(baseURL)/tracks/")!
        components.queryItems = [
            URLQueryItem(name: "client_id", value: clientId),
            URLQueryItem(name: "format", value: "json"),
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "offset", value: "\(offset)"),
            URLQueryItem(name: "search", value: query),
            URLQueryItem(name: "include", value: "musicinfo"),
            URLQueryItem(name: "audioformat", value: "mp32")
        ]
        
        guard let url = components.url else { throw URLError(.badURL) }
        
        let (data, _) = try await session.data(from: url)
        let response = try JSONDecoder().decode(JamendoResponse.self, from: data)
        let tracks = response.results.map { $0.toTrack() }
        cache[cacheKey] = tracks
        return tracks
    }
    
    func getByGenre(_ genre: MusicGenre, limit: Int = 20) async throws -> [Track] {
        guard let tag = genre.jamendoTag else { return [] }
        let cacheKey = "genre_\(tag)_\(limit)"
        if let cached = cache[cacheKey] { return cached }
        
        var components = URLComponents(string: "\(baseURL)/tracks/")!
        components.queryItems = [
            URLQueryItem(name: "client_id", value: clientId),
            URLQueryItem(name: "format", value: "json"),
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "tags", value: tag),
            URLQueryItem(name: "order", value: "popularity_week"),
            URLQueryItem(name: "audioformat", value: "mp32")
        ]
        
        guard let url = components.url else { throw URLError(.badURL) }
        
        let (data, _) = try await session.data(from: url)
        let response = try JSONDecoder().decode(JamendoResponse.self, from: data)
        let tracks = response.results.map { $0.toTrack() }
        cache[cacheKey] = tracks
        return tracks
    }
    
    func getPopular(limit: Int = 20) async throws -> [Track] {
        let cacheKey = "popular_\(limit)"
        if let cached = cache[cacheKey] { return cached }
        
        var components = URLComponents(string: "\(baseURL)/tracks/")!
        components.queryItems = [
            URLQueryItem(name: "client_id", value: clientId),
            URLQueryItem(name: "format", value: "json"),
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "order", value: "popularity_total"),
            URLQueryItem(name: "audioformat", value: "mp32")
        ]
        
        guard let url = components.url else { throw URLError(.badURL) }
        
        let (data, _) = try await session.data(from: url)
        let response = try JSONDecoder().decode(JamendoResponse.self, from: data)
        let tracks = response.results.map { $0.toTrack() }
        cache[cacheKey] = tracks
        return tracks
    }
    
    func getAlbums(limit: Int = 10) async throws -> [(String, [Track])] {
        var components = URLComponents(string: "\(baseURL)/albums/")!
        components.queryItems = [
            URLQueryItem(name: "client_id", value: clientId),
            URLQueryItem(name: "format", value: "json"),
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "order", value: "popularity_total")
        ]
        
        guard let url = components.url else { throw URLError(.badURL) }
        
        struct AlbumResult: Codable {
            let id: String
            let name: String
        }
        struct AlbumResponse: Codable {
            let results: [AlbumResult]
        }
        
        let (data, _) = try await session.data(from: url)
        let albums = try JSONDecoder().decode(AlbumResponse.self, from: data)
        
        var results: [(String, [Track])] = []
        for album in albums.results.prefix(5) {
            let tracks = try await getAlbumTracks(albumId: album.id)
            results.append((album.name, tracks))
        }
        return results
    }
    
    private func getAlbumTracks(albumId: String) async throws -> [Track] {
        var components = URLComponents(string: "\(baseURL)/tracks/")!
        components.queryItems = [
            URLQueryItem(name: "client_id", value: clientId),
            URLQueryItem(name: "format", value: "json"),
            URLQueryItem(name: "album_id", value: albumId),
            URLQueryItem(name: "audioformat", value: "mp32")
        ]
        
        guard let url = components.url else { throw URLError(.badURL) }
        let (data, _) = try await session.data(from: url)
        let response = try JSONDecoder().decode(JamendoResponse.self, from: data)
        return response.results.map { $0.toTrack() }
    }
}
