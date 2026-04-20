# PhotoBackup iOS App

Aplicație companion SwiftUI pentru dispozitivul PhotoBackup (Raspberry Pi).

## Cerințe
- macOS cu Xcode 15+
- iOS 17+ pe simulator sau device
- [XcodeGen](https://github.com/yonaskolb/XcodeGen) — `brew install xcodegen`

## Generare proiect Xcode

```bash
cd ios/
xcodegen generate
open PhotoBackup.xcodeproj
```

Apoi Build & Run (⌘R) pe iPhone 15 Simulator (sau device real).

## Configurare inițială

La primul launch aplicația încearcă:
1. `10.42.0.1:8080` (dacă iPhone-ul e conectat la hotspot-ul `PhotoBackup-AP`)
2. Bonjour `_photobackup._tcp` pe rețea
3. `photobackup.local:8080` (mDNS fallback)
4. Manual: setezi IP-ul din ConnectView

## Arhitectură

- SwiftUI + `@Observable` (iOS 17 Observation framework)
- Polling periodic (5s / 10s / 30s, configurabil) pe `/api/status`
- `URLSession.shared` + `async/await` + `JSONDecoder(.convertFromSnakeCase)`
- Bonjour prin `NWBrowser`
- Notificări locale prin `UNUserNotificationCenter`

## Structură

```
PhotoBackupApp/
├── PhotoBackupApp.swift
├── Info.plist (generat de XcodeGen, inclus aici ca referință)
├── Models/       — Codable DTOs
├── Services/     — APIService, DeviceDiscovery, NotificationService
├── ViewModels/   — @Observable per tab
├── Views/        — ContentView (TabView) + ecrane per tab
├── Components/   — reutilizabile (StorageBarView, ProgressBarView, ...)
└── Utils/        — Extensions + Constants
```
