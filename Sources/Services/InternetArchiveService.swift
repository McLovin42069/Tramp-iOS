import Foundation

actor InternetArchiveService {
    static let shared = InternetArchiveService()
    
    private let session: URLSession
    private var cache: [String: [Track]] = [:]
    private var metadataCache: [String: ArchiveMetadata] = [:]
    
    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        self.session = URLSession(configuration: config)
    }
    
    // MARK: - Search
    
    func search(query: String, limit: Int = 20) async throws -> [Track] {
        let cacheKey = "ia_search_\(query)_\(limit)"
        if let cached = cache[cacheKey] { return cached }
        
        let encodedQuery = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? query
        let urlString = "https://archive.org/advancedsearch.php?q=title:(\(encodedQuery)) AND mediatype:audio&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=subject&fl[]=description&sort[]=downloads desc&rows=\(limit)&output=json"
        
        guard let url = URL(string: urlString) else { throw URLError(.badURL) }
        
        let (data, _) = try await session.data(from: url)
        let response = try JSONDecoder().decode(ArchiveResponse.self, from: data)
        
        // Fetch metadata for each doc to get direct audio URLs
        var tracks: [Track] = []
        for doc in response.response.docs {
            if let track = await try? trackFromDoc(doc) {
                tracks.append(track)
            }
        }
        
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
        
        var tracks: [Track] = []
        for doc in response.response.docs {
            if let track = await try? trackFromDoc(doc) {
                tracks.append(track)
            }
        }
        
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
        
        var tracks: [Track] = []
        for doc in response.response.docs {
            if let track = await try? trackFromDoc(doc) {
                tracks.append(track)
            }
        }
        
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
        
        var tracks: [Track] = []
        for doc in response.response.docs {
            if let track = await try? trackFromDoc(doc) {
                tracks.append(track)
            }
        }
        
        cache[cacheKey] = tracks
        return tracks
    }
    
    // MARK: - Metadata Resolution
    
    private func trackFromDoc(_ doc: ArchiveDoc) async throws -> Track {
        guard let title = doc.title else {
            throw ArchiveError.missingTitle
        }
        
        // Try cached metadata first
        if let metadata = metadataCache[doc.identifier] {
            return try buildTrack(from: doc, metadata: metadata)
        }
        
        // Fetch metadata to find actual audio files
        let metadata = try await fetchMetadata(identifier: doc.identifier)
        metadataCache[doc.identifier] = metadata
        
        return try buildTrack(from: doc, metadata: metadata)
    }
    
    private func fetchMetadata(identifier: String) async throws -> ArchiveMetadata {
        let urlString = "https://archive.org/metadata/\(identifier)"
        guard let url = URL(string: urlString) else {
            throw URLError(.badURL)
        }
        
        let (data, _) = try await session.data(from: url)
        return try JSONDecoder().decode(ArchiveMetadata.self, from: data)
    }
    
    private func buildTrack(from doc: ArchiveDoc, metadata: ArchiveMetadata) throws -> Track {
        // Find the best audio file
        let audioFile = metadata.files.first { file in
            let name = file.name.lowercased()
            return name.hasSuffix(".mp3") || name.hasSuffix(".ogg") || name.hasSuffix(".m4a") || name.hasSuffix(".flac")
        }
        
        guard let audioFile = audioFile else {
            throw ArchiveError.noAudioFiles
        }
        
        // Build direct download URL
        let encodedName = audioFile.name.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? audioFile.name
        let streamURL = URL(string: "https://archive.org/download/\(doc.identifier)/\(encodedName)")
        let imgURL = URL(string: "https://archive.org/services/img/\(doc.identifier)")
        
        // Parse duration from metadata if available
        let duration = TimeInterval(audioFile.length ?? "0") ?? 0
        
        return Track(
            id: "archive_\(doc.identifier)",
            title: doc.title ?? "Unknown",
            artist: doc.creator?.first ?? "Internet Archive",
            album: nil,
            duration: duration,
            streamURL: streamURL,
            downloadURL: streamURL,
            artworkURL: imgURL,
            source: .internetArchive,
            genre: doc.subject?.first,
            license: "Public Domain / Creative Commons",
            sourceID: doc.identifier,
            localFilePath: nil
        )
    }
    
    enum ArchiveError: Error {
        case missingTitle
        case noAudioFiles
    }
}

// MARK: - Response Models

struct ArchiveResponse: Codable {
    let response: ArchiveDocs
}

struct ArchiveDocs: Codable {
    let docs: [ArchiveDoc]
}

struct ArchiveDoc: Codable {
    let identifier: String
    let title: String?
    let creator: [String]?
    let subject: [String]?
    let description: String?
}

struct ArchiveMetadata: Codable {
    let files: [ArchiveFile]
}

struct ArchiveFile: Codable {
    let name: String
    let format: String?
    let length: String?
}
