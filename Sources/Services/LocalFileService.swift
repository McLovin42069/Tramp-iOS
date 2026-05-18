import Foundation
import AVFoundation

actor LocalFileService {
    static let shared = LocalFileService()
    
    func importFiles(from urls: [URL]) async -> [Track] {
        var tracks: [Track] = []
        let documentsDir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let musicDir = documentsDir.appendingPathComponent("TrampMusic", isDirectory: true)
        try? FileManager.default.createDirectory(at: musicDir, withIntermediateDirectories: true)
        
        for url in urls {
            guard url.startAccessingSecurityScopedResource() else { continue }
            defer { url.stopAccessingSecurityScopedResource() }
            
            let destination = musicDir.appendingPathComponent(url.lastPathComponent)
            
            do {
                if FileManager.default.fileExists(atPath: destination.path) {
                    try FileManager.default.removeItem(at: destination)
                }
                try FileManager.default.copyItem(at: url, to: destination)
                
                let asset = AVAsset(url: destination)
                let duration = try await asset.load(.duration)
                let metadata = try await asset.loadMetadata(for: .id3)
                
                var title = url.deletingPathExtension().lastPathComponent
                var artist = "Unknown Artist"
                var album: String? = nil
                
                for item in metadata {
                    if let key = item.commonKey?.rawValue {
                        switch key {
                        case "title": title = item.stringValue ?? title
                        case "artist": artist = item.stringValue ?? artist
                        case "albumName": album = item.stringValue
                        default: break
                        }
                    }
                }
                
                let track = Track(
                    id: "local_\(destination.lastPathComponent)",
                    title: title,
                    artist: artist,
                    album: album,
                    duration: CMTimeGetSeconds(duration),
                    streamURL: destination,
                    downloadURL: nil,
                    artworkURL: nil,
                    source: .localFiles,
                    genre: nil,
                    license: "Personal",
                    sourceID: destination.lastPathComponent,
                    localFilePath: destination
                )
                tracks.append(track)
            } catch {
                print("Import error: \(error)")
            }
        }
        
        return tracks
    }
    
    func getImportedTracks() async -> [Track] {
        let documentsDir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        let musicDir = documentsDir.appendingPathComponent("TrampMusic", isDirectory: true)
        
        guard let files = try? FileManager.default.contentsOfDirectory(at: musicDir, includingPropertiesForKeys: nil) else {
            return []
        }
        
        let supportedExtensions = ["mp3", "m4a", "aac", "wav", "flac", "ogg"]
        let audioFiles = files.filter { supportedExtensions.contains($0.pathExtension.lowercased()) }
        
        var tracks: [Track] = []
        for file in audioFiles {
            let track = Track(
                id: "local_\(file.lastPathComponent)",
                title: file.deletingPathExtension().lastPathComponent,
                artist: "Unknown Artist",
                album: nil,
                duration: 0,
                streamURL: file,
                downloadURL: nil,
                artworkURL: nil,
                source: .localFiles,
                genre: nil,
                license: "Personal",
                sourceID: file.lastPathComponent,
                localFilePath: file
            )
            tracks.append(track)
        }
        
        return tracks
    }
}
