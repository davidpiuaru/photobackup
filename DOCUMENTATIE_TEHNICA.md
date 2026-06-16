# PhotoBackup — Documentație tehnică (proiect de licență)

**Dispozitiv portabil de backup automat pentru fotografi, bazat pe Raspberry Pi 4,
cu aplicație iOS companion și evaluare AI a calității pozelor.**

Document generat: 2026-06-13.

---

## 1. Rezumat

PhotoBackup este un dispozitiv *headless* (fără ecran/tastatură) care:
1. detectează automat inserarea unui card SD într-un cititor USB;
2. copiază fișierele noi pe un SSD extern, cu verificare de integritate (SHA256);
3. le sincronizează pe Google Drive când are internet;
4. poate fi controlat și monitorizat de pe iPhone printr-o aplicație companion;
5. poate evalua cu un model AI calitatea fiecărei poze (1–5 stele) și scrie scorul
   direct în metadata fișierelor.

Sistemul are **trei componente**: daemon-ul Python de pe Pi, un server API REST
(FastAPI) și aplicația iOS (SwiftUI).

---

## 2. Hardware

| Componentă | Specificație | Rol |
|---|---|---|
| Placă | **Raspberry Pi 4 Model B Rev 1.2**, 4 GB RAM | Calculatorul dispozitivului |
| CPU | ARM **Cortex-A72**, 4 nuclee @ 1.5 GHz, aarch64 (64-bit) | Procesare backup + inferență AI |
| Stocare backup | **SSD SanDisk Extreme 1 TB** USB 3.0, formatat ext4 (label `BACKUP_SSD`), montat la `/mnt/backup-ssd` | Destinația copiilor |
| Cititor card | **USB SD Card Reader Genesys Logic** (USB ID `05e3:0764`) | Citire carduri SD ale camerei |
| LED-uri (opțional) | GPIO 17 (verde = idle/lucru), GPIO 27 (roșu = eroare) | Feedback vizual headless |
| Alimentare | USB-C 5V/3A | — |
| Dispozitiv companion | **iPhone 16 Pro Max** (iOS 26.5) | Aplicația de control |
| Stație de dezvoltare | Mac (macOS), Xcode 26.4.1 | Build app iOS, deploy |

**OS pe Pi:** Raspberry Pi OS / Debian GNU/Linux 13 (trixie), kernel 6.12.75 (64-bit),
hostname `photobackup`, utilizator `admin`, acces prin SSH (`ssh admin@photobackup.local`).

> Observație de robustețe: identificarea cititorului SD se face prin **vendor + model
> USB** (nu după litera `/dev/sdX`, care se poate schimba la reboot), iar cardul este
> montat **read-only** — nu se modifică niciodată conținutul original.

---

## 3. Arhitectura sistemului

```
 ┌─────────┐  plug SD  ┌──────────────┐  copy+SHA256  ┌──────────────┐  rclone  ┌──────────────┐
 │ SD card │ ────────► │ USB reader   │ ────────────► │ SSD (ext4)   │ ───────► │ Google Drive │
 │ (camera)│           │ (Genesys)    │               │ /mnt/backup- │          │ PhotoBackup/ │
 └─────────┘           └──────────────┘               │   ssd        │          └──────────────┘
                                                       └──────┬───────┘
                                                              │ status.json (IPC)
                          ┌──────────────┐  REST :8080        ▼
 ┌─────────┐  Wi-Fi/mDNS  │ FastAPI      │ ◄──────────  daemon + sync + wifi_manager
 │ iPhone  │ ───────────► │ (uvicorn)    │
 │ SwiftUI │              └──────────────┘
 └─────────┘
```

**Comunicarea între procese (IPC)** se face prin fișiere partajate pe disc:
- `/mnt/backup-ssd/status.json` — starea backup/sync/rating/SD card (scris atomic, cu
  lock `fcntl` inter-proces; citit de API);
- `/tmp/wifi_state.json` — starea Wi-Fi (mod AP/client);
- `/tmp/photobackup-wifi.cmd.d/` — coadă de comenzi Wi-Fi (fișiere JSON);
- fișiere de control pentru pauză/anulare (`/tmp/photobackup-*.control`).

---

## 4. Pașii de dezvoltare

Dezvoltarea a fost incrementală, fiecare etapă fiind un commit în Git:

1. **Scaffolding daemon** (`ea7ad04`) — structura de bază a daemon-ului Python:
   `config` (constante), `monitor` (detecție udev), `mounter` (montare),
   `copier` (copiere + SHA256 + manifest), `tracker` (deduplicare), `led`, `main`.
2. **Montare directă cu sudo** (`9aa3ae8`) — abandonarea `udisksctl` (blocat de polkit
   în context headless) în favoarea `sudo mount` direct.
3. **Sincronizare Google Drive** (`3cf90d1`) — modulul `sync` (rclone) + timer systemd
   pentru upload periodic la 10 min, sărind folderele incomplete.
4. **Documentație + arhitectură** (`605eec3`) — README cu diagrame și note de robustețe.
5. **App iOS + API + Wi-Fi manager** (`bb3dec3`) — serverul FastAPI cu toate
   endpoint-urile, aplicația SwiftUI (MVVM, 5 tab-uri), și `wifi_manager` pentru
   comutarea automată AP ↔ client prin NetworkManager.
6. **Audit de securitate/robustețe + rating AI** (`5bf4fd1`):
   - **Audit:** 17 probleme identificate și reparate (vezi §6);
   - **Rating AI:** scor 1–5 stele scris în metadata, cu model NIMA (ONNX) și fallback
     euristic; module noi `imaging`, `scoring`, `rater` + rută API.

**Etape de punere în funcțiune (deployment):**
7. Deploy pe Pi prin `rsync`, instalare dependențe (apt + pip), instalare servicii
   systemd + reguli sudoers, pornire și verificare pe hardware real.
8. Instalare aplicație pe iPhone din Xcode (semnare automată cu Apple ID, instalare
   prin `devicectl`), validare end-to-end (telefon ↔ Pi).

---

## 5. Stack tehnologic — librării și unelte publice

### 5.1 Daemon Python (`photobackup/`)

| Librărie / unealtă | Versiune | Ce este și de ce a fost folosită |
|---|---|---|
| **pyudev** | 0.24.3 | Binding Python peste `libudev` (Linux). Ascultă evenimentele kernel-ului prin *netlink* și detectează inserarea cardului SD, filtrând după vendor/model USB. Ales pentru detecție **event-driven** (fără polling). |
| **gpiozero** | 2.0.1 | Bibliotecă oficială Raspberry Pi pentru controlul pinilor GPIO. Folosită pentru LED-urile de stare. API simplu, cu „no-op" automat dacă hardware-ul lipsește. |
| **rclone** | v1.60.1 | Unealtă CLI standard pentru sincronizare cu cloud (Google Drive). Suportă reluare, paralelism, log JSON pentru progres. Configurat cu scope OAuth minim `drive.file` (vede doar fișierele create de app). |
| **NetworkManager / nmcli** | 1.52.1 | Managerul de rețea din Linux. Folosit prin `nmcli` pentru a comuta wlan0 între **client Wi-Fi** și **hotspot (AP)**, evitând configurarea manuală a `hostapd`/`dnsmasq`. |
| **mount / umount / lsblk** (util-linux) | — | Montarea **read-only** a cardului și citirea etichetei/tipului de filesystem. |
| `hashlib` (stdlib) | — | Calcul **SHA256** pe sursă și destinație pentru verificarea integrității fiecărui fișier copiat. |
| `subprocess`, `shutil`, `threading`, `fcntl`, `socket`, `json`, `pathlib`, `logging` (stdlib) | — | Rulare comenzi externe, copiere fișiere, lock inter-proces (`fcntl.flock`), test conectivitate, scriere atomică status, logging cu rotație. |

### 5.2 Server API (`api/`)

| Librărie | Versiune | Ce este și de ce a fost folosită |
|---|---|---|
| **FastAPI** | 0.136.0 | Framework web Python asincron. Oferă routing, validare automată și documentație OpenAPI. Ales pentru viteză și integrarea nativă cu type hints + Pydantic. |
| **uvicorn** | 0.44.0 | Server ASGI de mare performanță care rulează aplicația FastAPI (port 8080). |
| **Pydantic** | 2.13.2 | Validare și serializare a datelor prin modele tipate (scheme request/response). |
| **psutil** | 7.2.2 | Informații de sistem cross-platform: spațiu disc, folosit pentru statusul SSD/SD. |
| **Pillow (PIL)** | 12.2.0 | Procesare de imagini: generarea de thumbnail-uri (300px) și preview (1600px). |
| **pillow-heif** | 1.4.0 | Plugin pentru decodarea **HEIC/HEIF** (formatul pozelor de iPhone), pe care Pillow nu îl suportă nativ. |
| **rawpy** | 0.27.0 | Wrapper Python peste biblioteca **LibRaw**; decodează fișiere **RAW** (CR3/ARW/NEF etc.) pentru thumbnail-uri și pentru intrarea în modelul AI. |

### 5.3 Evaluare AI a calității (rating 1–5 stele)

| Librărie / model | Versiune | Ce este și de ce a fost folosit |
|---|---|---|
| **ONNX Runtime** | 1.26.0 | Motor de inferență pentru modele în format **ONNX**, optimizat pentru CPU. Rulează modelul de scor estetic direct pe Pi (fără GPU/cloud). |
| **NIMA** (Neural Image Assessment) | MobileNet / AVA | Rețea neuronală (bază **MobileNet**, ~3.2M parametri) antrenată pe setul **AVA** pentru **scor estetic** 1–10; media distribuției e mapată la 1–5 stele. Greutăți din *idealo/image-quality-assessment*, convertite Keras→ONNX cu **tf2onnx** (vezi `scripts/convert_nima_to_onnx.py`). Rulează pe Pi prin ONNX Runtime. |
| **numpy** | 2.4.6 | Operații pe array-uri: pre-procesarea imaginii pentru model și calculul euristic. |
| **euristică proprie** | — | Fallback când modelul lipsește: scor din **claritate** (varianța Laplacianului), **expunere** (histogramă, penalizare clipping) și **contrast**. |
| **ExifTool** | 13.25 | Standardul de facto pentru metadata foto. Scrie ratingul: `XMP:Rating` + `EXIF:Rating` încorporat în JPEG, și **sidecar `.xmp`** pentru RAW (nedistructiv — fișierul RAW nu e modificat). |

### 5.4 Aplicația iOS (`ios/PhotoBackupApp/`)

| Tehnologie | Ce este și de ce a fost folosită |
|---|---|
| **SwiftUI** | Framework UI declarativ Apple. Întreaga interfață (5 tab-uri: Dashboard, Backup, Galerie, Wi-Fi, Setări). |
| **Observation (`@Observable`)** | Sistemul modern de reactivitate Swift (iOS 17+); leagă ViewModel-urile de UI. Arhitectură **MVVM**. |
| **URLSession + async/await** | Networking HTTP către API, cu cod asincron modern. |
| **Network framework (`NWBrowser`/`NWConnection`)** | Descoperirea automată a Pi-ului în rețea prin **Bonjour/mDNS**. |
| **UserNotifications** | Notificări locale (backup gata, erori) prin polling. |
| **Codable** | Decodare JSON ↔ structuri Swift (cu conversie automată snake_case → camelCase). |
| **XcodeGen** | 2.45.4 — generează proiectul `.xcodeproj` dintr-un fișier `project.yml` declarativ (proiect reproductibil, ușor de versionat). |

### 5.5 Infrastructură și unelte de sistem

| Unealtă | Ce este și de ce a fost folosită |
|---|---|
| **systemd** | Manager de servicii Linux. 5 unit-uri: daemon backup, API, wifi_manager (root), sync (oneshot) + `.timer` la 10 min, plus serviciu Avahi. `Restart=on-failure` pentru robustețe. |
| **Avahi** | Implementarea mDNS/DNS-SD pe Linux. Publică serviciul `_photobackup._tcp` ca aplicația iOS să găsească Pi-ul la `photobackup.local`. |
| **ext4 / exfat-fuse** | Filesystem-ul SSD-ului (ext4) și suport pentru cardurile SD formatate exFAT/FAT32. |
| **sudoers** | Reguli `NOPASSWD` stricte: montare carduri + pornirea manuală a sync-ului din API (fără a rula tot ca root). |
| **Git + GitHub** | Versionarea codului (`github.com/davidpiuaru/photobackup`). |
| **rsync** | Deploy-ul codului pe Pi (transfer incremental peste SSH). |

### 5.6 Unelte de dezvoltare

- **Xcode 26.4.1** + **Swift 6.3.1** — build și semnare aplicație iOS.
- **Python 3.13.5** + `venv` (mediu virtual izolat pe Pi).
- **devicectl** (xcrun) — instalarea aplicației pe dispozitivul fizic din linia de comandă.

---

## 6. Securitate și robustețe (rezumat audit)

În urma unui audit de cod au fost reparate 17 probleme. Cele mai importante:

- **Race condition pe `status.json`** — două procese (daemon + sync) scriau fișierul
  din cache-uri separate și se suprascriau reciproc. Reparat cu **read-modify-write
  serializat printr-un lock de fișier (`fcntl.flock`)**.
- **Path traversal** la servirea thumbnail-urilor — validare strictă a căilor
  (`Path.resolve()` + verificarea apartenenței la directorul de backup).
- **Autentificare API opțională** (token partajat) + ascunderea parolei hotspotului din
  răspunsurile API.
- **Verificare integritate** — SHA256 sursă vs. destinație pentru fiecare fișier; la
  nepotrivire fișierul rămâne marcat `.incomplete`.
- **Scriere atomică** (`tmp` + `rename`) pentru toate fișierele de stare.
- **Scope OAuth minim** (`drive.file`) — dacă Pi-ul e compromis, restul Drive-ului
  rămâne protejat.

---

## 7. Statistici de performanță (măsurate pe hardware real)

Toate valorile măsurate pe Raspberry Pi 4B (4 GB), Debian 13, SSD SanDisk Extreme 1 TB.

### 7.1 Stocare și I/O
| Metric | Valoare |
|---|---|
| Citire secvențială SSD (USB 3.0, I/O direct) | **345 MB/s** |
| Spațiu SSD | 916 GB total, 29 GB folosit (4 %) |
| Throughput **backup real** SD→SSD (cu verificare SHA256) | **≈ 20 MB/s** (29.9 GB / 6566 fișiere în 1461 s ≈ 24 min) |
| Viteză SHA256 (software, A72 fără extensii cripto) | ≈ 56 MB/s |

### 7.2 Procesare imagini și rating AI
| Operație | Timp |
|---|---|
| Decodare JPEG ~24 MP + thumbnail 300px | **≈ 1.3 s / poză** (dominat de decodare) |
| Scor euristic (după decodare) | ≈ 0.19 s / poză |
| Inferență NIMA (ONNX Runtime, CPU) | ≈ 0.6 s / poză |
| **Rating complet** (decodare + scor + scriere ExifTool) | **≈ 2.4 s / poză** (euristică) · **≈ 3.0 s / poză** (NIMA) |
| Sesiune mică demo (6 poze reale) | 14.5 s (euristică) · 18.1 s (NIMA) |
| Sesiune mare (6561 poze) | ≈ ore — operație de fundal; sub I/O concurent cu rclone, ExifTool poate atinge timeout 30 s/fișier |

> Optimizare posibilă viitoare: decodare la rezoluție redusă (`Image.draft`) și scriere
> ExifTool în lot (`-csv`) pentru a reduce drastic timpul pe sesiunile mari.

### 7.3 API și sistem
| Metric | Valoare |
|---|---|
| Latență `GET /api/status` (în rețea locală) | **≈ 8 ms** |
| RAM folosit (idle) | 257 MB / 3.7 GB |
| Încărcare CPU (idle) | load average ≈ 0.15 |
| Temperatură CPU (idle) | 55 °C |

---

## 8. Statistici de cod

| Componentă | Fișiere | Linii de cod |
|---|---|---|
| Backend Python (`photobackup/` + `api/`) | 33 | **2780** |
| Aplicație iOS Swift (`ios/PhotoBackupApp/`) | 29 | **2539** |
| **Total** | 62 | **≈ 5319 linii** |

- Endpoint-uri API REST: ~25 (status, storage, wifi, backup, sync, sessions,
  thumbnails, preview, notifications, rating).
- Servicii systemd: 5 (+ 1 timer).
- Istoric Git: 6 commit-uri (etape de dezvoltare).

---

## 9. Concluzii și posibile îmbunătățiri

Dispozitivul atinge obiectivul propus: backup automat, fiabil și verificat, controlabil
de pe telefon, cu o componentă de inteligență artificială pentru trierea pozelor — toate
rulând autonom pe hardware accesibil (Raspberry Pi 4).

**Direcții viitoare:**
- Optimizarea rating-ului pentru sesiuni mari (decodare redusă + ExifTool în lot);
- Declanșarea automată a rating-ului după backup (acum e manuală din app);
- Eventuala accelerare cu un coprocesor AI (ex. Hailo / Coral) pentru inferență mai rapidă.
