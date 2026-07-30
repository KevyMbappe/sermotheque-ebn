//
//  Item.swift
//  Sermothèque EBN
//
//  Created by Kevy Mbappé on 22/07/2026.
//

import Foundation
import SwiftData

@Model
final class Item {
    var timestamp: Date
    
    init(timestamp: Date) {
        self.timestamp = timestamp
    }
}
