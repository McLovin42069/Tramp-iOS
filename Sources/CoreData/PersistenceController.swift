import CoreData
import Foundation

struct PersistenceController {
    static let shared = PersistenceController()
    
    let container: NSPersistentContainer
    
    init(inMemory: Bool = false) {
        // Create model programmatically
        let model = Self.createModel()
        
        container = NSPersistentContainer(name: "TrampModel", managedObjectModel: model)
        
        if inMemory {
            container.persistentStoreDescriptions.first?.url = URL(fileURLWithPath: "/dev/null")
        }
        
        container.loadPersistentStores { description, error in
            if let error = error as NSError? {
                print("Core Data load error: \(error), \(error.userInfo)")
            }
        }
        
        container.viewContext.automaticallyMergesChangesFromParent = true
        container.viewContext.mergePolicy = NSMergeByPropertyObjectTrumpMergePolicy
    }
    
    func save() {
        let context = container.viewContext
        if context.hasChanges {
            do {
                try context.save()
            } catch {
                print("Core Data save error: \(error)")
            }
        }
    }
    
    private static func createModel() -> NSManagedObjectModel {
        let model = NSManagedObjectModel()
        
        // CachedTrackEntity
        let trackEntity = NSEntityDescription()
        trackEntity.name = "CachedTrackEntity"
        trackEntity.managedObjectClassName = "CachedTrackEntity"
        
        let trackAttributes: [(String, NSAttributeType, Bool)] = [
            ("id", .stringAttributeType, false),
            ("title", .stringAttributeType, false),
            ("artist", .stringAttributeType, false),
            ("album", .stringAttributeType, true),
            ("duration", .doubleAttributeType, false),
            ("streamURL", .stringAttributeType, true),
            ("artworkURL", .stringAttributeType, true),
            ("sourceRaw", .stringAttributeType, false),
            ("genre", .stringAttributeType, true),
            ("dateAdded", .dateAttributeType, false),
            ("playCount", .integer32AttributeType, false),
            ("lastPlayed", .dateAttributeType, true),
            ("isOfflineAvailable", .booleanAttributeType, false),
            ("localPath", .stringAttributeType, true),
            ("sourceID", .stringAttributeType, false)
        ]
        
        trackEntity.properties = trackAttributes.map { name, type, optional in
            let attr = NSAttributeDescription()
            attr.name = name
            attr.attributeType = type
            attr.isOptional = optional
            if type == .integer32AttributeType {
                attr.defaultValue = 0
            } else if type == .booleanAttributeType {
                attr.defaultValue = false
            } else if type == .doubleAttributeType {
                attr.defaultValue = 0.0
            }
            return attr
        }
        
        // PlaylistEntity
        let playlistEntity = NSEntityDescription()
        playlistEntity.name = "PlaylistEntity"
        playlistEntity.managedObjectClassName = "PlaylistEntity"
        
        let playlistAttributes: [(String, NSAttributeType, Bool)] = [
            ("id", .stringAttributeType, false),
            ("name", .stringAttributeType, false),
            ("dateCreated", .dateAttributeType, false),
            ("trackOrder", .stringAttributeType, false),
            ("isSmartPlaylist", .booleanAttributeType, false),
            ("smartFilter", .stringAttributeType, true)
        ]
        
        playlistEntity.properties = playlistAttributes.map { name, type, optional in
            let attr = NSAttributeDescription()
            attr.name = name
            attr.attributeType = type
            attr.isOptional = optional
            if type == .booleanAttributeType {
                attr.defaultValue = false
            }
            return attr
        }
        
        // UserStatsEntity
        let statsEntity = NSEntityDescription()
        statsEntity.name = "UserStatsEntity"
        statsEntity.managedObjectClassName = "UserStatsEntity"
        
        let statsAttributes: [(String, NSAttributeType, Bool, Any?)] = [
            ("totalListeningMinutes", .doubleAttributeType, false, 0.0),
            ("totalTracksPlayed", .integer32AttributeType, false, 0),
            ("currentStreakDays", .integer32AttributeType, false, 0),
            ("longestStreakDays", .integer32AttributeType, false, 0),
            ("lastListeningDate", .dateAttributeType, true, nil),
            ("trampMiles", .doubleAttributeType, false, 0.0),
            ("level", .integer32AttributeType, false, 1),
            ("xp", .doubleAttributeType, false, 0.0),
            ("badgesData", .binaryDataAttributeType, true, nil),
            ("favoriteGenresData", .binaryDataAttributeType, true, nil),
            ("totalSearches", .integer32AttributeType, false, 0),
            ("radioSessions", .integer32AttributeType, false, 0),
            ("playlistsCreated", .integer32AttributeType, false, 0),
            ("skinChanges", .integer32AttributeType, false, 0),
            ("onboardingCompleted", .booleanAttributeType, false, false)
        ]
        
        statsEntity.properties = statsAttributes.map { name, type, optional, defaultVal in
            let attr = NSAttributeDescription()
            attr.name = name
            attr.attributeType = type
            attr.isOptional = optional
            if let defaultVal = defaultVal {
                attr.defaultValue = defaultVal
            }
            return attr
        }
        
        model.entities = [trackEntity, playlistEntity, statsEntity]
        return model
    }
}

// MARK: - Core Data Entities

@objc(CachedTrackEntity)
public class CachedTrackEntity: NSManagedObject {
    @NSManaged public var id: String
    @NSManaged public var title: String
    @NSManaged public var artist: String
    @NSManaged public var album: String?
    @NSManaged public var duration: Double
    @NSManaged public var streamURL: String?
    @NSManaged public var artworkURL: String?
    @NSManaged public var sourceRaw: String
    @NSManaged public var genre: String?
    @NSManaged public var dateAdded: Date
    @NSManaged public var playCount: Int32
    @NSManaged public var lastPlayed: Date?
    @NSManaged public var isOfflineAvailable: Bool
    @NSManaged public var localPath: String?
    @NSManaged public var sourceID: String
}

@objc(PlaylistEntity)
public class PlaylistEntity: NSManagedObject {
    @NSManaged public var id: String
    @NSManaged public var name: String
    @NSManaged public var dateCreated: Date
    @NSManaged public var trackOrder: String
    @NSManaged public var isSmartPlaylist: Bool
    @NSManaged public var smartFilter: String?
}

@objc(UserStatsEntity)
public class UserStatsEntity: NSManagedObject {
    @NSManaged public var totalListeningMinutes: Double
    @NSManaged public var totalTracksPlayed: Int32
    @NSManaged public var currentStreakDays: Int32
    @NSManaged public var longestStreakDays: Int32
    @NSManaged public var lastListeningDate: Date?
    @NSManaged public var trampMiles: Double
    @NSManaged public var level: Int32
    @NSManaged public var xp: Double
    @NSManaged public var badgesData: Data?
    @NSManaged public var favoriteGenresData: Data?
    @NSManaged public var totalSearches: Int32
    @NSManaged public var radioSessions: Int32
    @NSManaged public var playlistsCreated: Int32
    @NSManaged public var skinChanges: Int32
    @NSManaged public var onboardingCompleted: Bool
}

// MARK: - Helpers

extension CachedTrackEntity {
    func toTrack() -> Track {
        Track(
            id: id,
            title: title,
            artist: artist,
            album: album,
            duration: duration,
            streamURL: streamURL.flatMap { URL(string: $0) },
            downloadURL: nil,
            artworkURL: artworkURL.flatMap { URL(string: $0) },
            source: MusicSource(rawValue: sourceRaw) ?? .jamendo,
            genre: genre,
            license: nil,
            sourceID: sourceID,
            localFilePath: localPath.flatMap { URL(fileURLWithPath: $0) }
        )
    }
    
    static func fromTrack(_ track: Track, context: NSManagedObjectContext) -> CachedTrackEntity {
        let entity = CachedTrackEntity(context: context)
        entity.id = track.id
        entity.title = track.title
        entity.artist = track.artist
        entity.album = track.album
        entity.duration = track.duration
        entity.streamURL = track.streamURL?.absoluteString
        entity.artworkURL = track.artworkURL?.absoluteString
        entity.sourceRaw = track.source.rawValue
        entity.genre = track.genre
        entity.dateAdded = Date()
        entity.playCount = 0
        entity.isOfflineAvailable = false
        entity.localPath = track.localFilePath?.path
        entity.sourceID = track.sourceID
        return entity
    }
}
