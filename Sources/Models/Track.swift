import Foundation

struct Track: Identifiable, Codable, Equatable, Hashable {
    let id: String
    let title: String
    let artist: String
    let album: String?
    let duration: TimeInterval
    let streamURL: URL?
    let downloadURL: URL?
    let artworkURL: URL?
    let source: MusicSource
    let genre: String?
    let license: String?
    let sourceID: String
    let localFilePath: URL?
    
    var isLocal: Bool { localFilePath != nil }
    
    var displayTitle: String {
        title.isEmpty ? "Unknown Track" : title
    }
    
    var displayArtist: String {
        artist.isEmpty ? "Unknown Artist" : artist
    }
    
    var displayAlbum: String {
        album ?? "Unknown Album"
    }
    
    static func == (lhs: Track, rhs: Track) -> Bool {
        lhs.id == rhs.id
    }
    
    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}

// MARK: - Jamendo Response
struct JamendoResponse: Codable {
    let results: [JamendoTrack]
}

struct JamendoTrack: Codable {
    let id: String
    let name: String
    let artist_name: String
    let album_name: String?
    let duration: Int
    let audio: String
    let audiodownload: String?
    let image: String?
    let musicinfo: JamendoMusicInfo?
    let license_ccurl: String?
    
    func toTrack() -> Track {
        Track(
            id: "jamendo_\(id)",
            title: name,
            artist: artist_name,
            album: album_name,
            duration: TimeInterval(duration),
            streamURL: URL(string: audio),
            downloadURL: URL(string: audiodownload ?? ""),
            artworkURL: URL(string: image ?? ""),
            source: .jamendo,
            genre: musicinfo?.tags?.first,
            license: license_ccurl,
            sourceID: id,
            localFilePath: nil
        )
    }
}

struct JamendoMusicInfo: Codable {
    let tags: [String]?
}

// MARK: - Internet Archive Response
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
    
    func toTrack() -> Track? {
        guard let title = title else { return nil }
        let m3u = "https://archive.org/download/\(identifier)/\(identifier)_vbr.m3u"
        let img = "https://archive.org/services/img/\(identifier)"
        
        return Track(
            id: "archive_\(identifier)",
            title: title,
            artist: creator?.first ?? "Internet Archive",
            album: nil,
            duration: 0,
            streamURL: URL(string: m3u),
            downloadURL: nil,
            artworkURL: URL(string: img),
            source: .internetArchive,
            genre: subject?.first,
            license: "Public Domain",
            sourceID: identifier,
            localFilePath: nil
        )
    }
}

// MARK: - Pixabay Response
struct PixabayMusicResponse: Codable {
    let hits: [PixabayTrack]
}

struct PixabayTrack: Codable {
    let id: Int
    let tags: String
    let user: String
    let pageURL: String
    let previewURL: String?
    
    func toTrack() -> Track {
        let firstTag = tags.components(separatedBy: ",").first?.trimmingCharacters(in: .whitespaces) ?? "Unknown"
        return Track(
            id: "pixabay_\(id)",
            title: firstTag,
            artist: user,
            album: nil,
            duration: 0,
            streamURL: URL(string: previewURL ?? ""),
            downloadURL: URL(string: pageURL),
            artworkURL: nil,
            source: .pixabay,
            genre: firstTag,
            license: "Royalty Free",
            sourceID: "\(id)",
            localFilePath: nil
        )
    }
}
