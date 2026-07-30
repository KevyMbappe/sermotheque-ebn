//
//  Sermothe_que_EBNApp.swift
//  Sermothèque EBN
//
//  Created by Kevy Mbappé on 22/07/2026.
//

import SwiftUI
import SwiftData

@main
struct Sermothe_que_EBNApp: App {
    var sharedModelContainer: ModelContainer = {
        let schema = Schema([
            Item.self,
        ])
        let modelConfiguration = ModelConfiguration(schema: schema, isStoredInMemoryOnly: false)

        do {
            return try ModelContainer(for: schema, configurations: [modelConfiguration])
        } catch {
            fatalError("Could not create ModelContainer: \(error)")
        }
    }()

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .modelContainer(sharedModelContainer)
    }
}
